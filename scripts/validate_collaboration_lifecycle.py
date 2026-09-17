#!/usr/bin/env python3
"""Cross-record lifecycle and authorization checks.

Coordination structure is engineering evidence, not proof authority.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LEASE_TYPES = {"TASK_LEASE", "HANDOFF"}
MESSAGE_TYPES = {"PROPOSAL", "REVIEW", "DECISION", "CLOSED"}
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
ORDERED_FILENAME_RE = re.compile(r"^(?P<ordinal>[0-9]{8})-.+\.json$")


def load_records(directory: Path):
    records = []
    for path in sorted(directory.glob("*.json")):
        record = json.loads(path.read_text())
        record["__path"] = str(path)
        records.append(record)
    return records


def lease_owner(record):
    """Return the effective owner of a lease-chain record."""
    if record.get("record_type") == "HANDOFF":
        return record.get("target")
    return record.get("sender")


def _parse_created_at(record):
    stamp = record.get("created_at")
    if not isinstance(stamp, str):
        return None
    try:
        value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return None
    return value


def _validate_canonical_order(records):
    """Enforce deterministic append order for records loaded from disk."""
    errors = []
    previous_ordinal = None
    previous_time = None
    previous_id = None
    for record in records:
        path_text = record.get("__path")
        if isinstance(path_text, str):
            name = Path(path_text).name
            match = ORDERED_FILENAME_RE.fullmatch(name)
            if match is None:
                errors.append(
                    f"{name}: record filename must start with an 8-digit ordinal and '-'"
                )
            else:
                ordinal = int(match.group("ordinal"))
                if previous_ordinal is not None and ordinal <= previous_ordinal:
                    errors.append(
                        f"{name}: filename ordinal must increase monotonically"
                    )
                previous_ordinal = ordinal

        created_at = _parse_created_at(record)
        if created_at is not None:
            if previous_time is not None and created_at < previous_time:
                errors.append(
                    f"{record.get('record_id')}: created_at regresses behind "
                    f"{previous_id}"
                )
            previous_time = created_at
            previous_id = record.get("record_id")
    return errors


def _index_records(records):
    errors = []
    by_id = {}
    index = {}
    for i, record in enumerate(records):
        record_id = record.get("record_id")
        if not isinstance(record_id, str):
            errors.append(f"{record.get('__path')}: missing record_id")
            continue
        if record_id in by_id:
            errors.append(f"duplicate record_id: {record_id}")
        by_id[record_id] = record
        index[record_id] = i
    return errors, by_id, index


def _valid_supersessions(records, by_id, index, errors):
    """Validate append-only correction links and lease-chain transitions.

    Lease/handoff supersession changes live ownership. Non-lease supersession is
    a same-type correction relation only; it never changes lease liveness.
    """
    lease_superseders = {}
    message_superseders = {}
    superseding_record_for = {}

    for record in records:
        record_id = record.get("record_id")
        prior_id = record.get("supersedes")
        if prior_id is None:
            continue
        if prior_id == record_id:
            errors.append(f"{record_id}: cannot supersede itself")
            continue

        old = by_id.get(prior_id)
        if old is None:
            errors.append(f"{record_id}: supersedes unknown record {prior_id}")
            continue
        if index.get(prior_id, 10**9) >= index.get(record_id, -1):
            errors.append(f"{record_id}: supersedes must reference an earlier record")
            continue
        if record.get("head_sha") != old.get("head_sha"):
            errors.append(f"{record_id}: cross-head supersession forbidden")
            continue
        if prior_id in superseding_record_for:
            errors.append(
                f"{record_id}: {prior_id} already superseded by "
                f"{superseding_record_for[prior_id]}"
            )
            continue

        old_type = old.get("record_type")
        new_type = record.get("record_type")
        old_is_lease = old_type in LEASE_TYPES
        new_is_lease = new_type in LEASE_TYPES

        if old_is_lease or new_is_lease:
            if not (old_is_lease and new_is_lease):
                errors.append(
                    f"{record_id}: only TASK_LEASE/HANDOFF may supersede "
                    "a lease/handoff"
                )
                continue

            old_owner = lease_owner(old)
            if new_type == "HANDOFF":
                if record.get("sender") != old_owner:
                    errors.append(
                        f"{record_id}: HANDOFF sender must be current owner "
                        f"{old_owner!r}"
                    )
                    continue
                new_owner = record.get("target")
                if not isinstance(new_owner, str) or not new_owner:
                    errors.append(
                        f"{record_id}: HANDOFF target must name the new owner"
                    )
                    continue
                if new_owner == old_owner:
                    errors.append(
                        f"{record_id}: HANDOFF target must change owner"
                    )
                    continue
            else:
                if record.get("sender") != old_owner:
                    errors.append(
                        f"{record_id}: owner change requires HANDOFF; "
                        f"current owner is {old_owner!r}"
                    )
                    continue

            lease_superseders[prior_id] = record_id
        else:
            if new_type not in MESSAGE_TYPES or old_type not in MESSAGE_TYPES:
                errors.append(f"{record_id}: unsupported non-lease supersession")
                continue
            if new_type != old_type:
                errors.append(
                    f"{record_id}: non-lease correction must preserve record_type "
                    f"{old_type!r}"
                )
                continue
            if record.get("sender") != old.get("sender"):
                errors.append(
                    f"{record_id}: non-lease correction must preserve sender "
                    f"{old.get('sender')!r}"
                )
                continue
            message_superseders[prior_id] = record_id

        superseding_record_for[prior_id] = record_id

    return lease_superseders, message_superseders


def live_leases(records, lease_superseders):
    by_head = defaultdict(list)
    for record in records:
        if record.get("record_type") not in LEASE_TYPES:
            continue
        if record.get("record_id") in lease_superseders:
            continue
        by_head[record.get("head_sha")].append(record)
    return by_head


def _effective_messages(records, message_superseders):
    return [
        record
        for record in records
        if record.get("record_type") in MESSAGE_TYPES
        and record.get("record_id") not in message_superseders
    ]


def _validate_lifecycle_order(records, message_superseders):
    errors = []
    records_by_head = defaultdict(list)
    for record in records:
        records_by_head[record.get("head_sha")].append(record)

    effective_messages = {
        record.get("record_id")
        for record in _effective_messages(records, message_superseders)
    }

    for head, head_records in records_by_head.items():
        types = [record.get("record_type") for record in head_records]
        lease_positions = [
            i for i, record_type in enumerate(types) if record_type in LEASE_TYPES
        ]
        decision_positions = [
            i for i, record_type in enumerate(types) if record_type == "DECISION"
        ]
        closed_positions = [
            i for i, record_type in enumerate(types) if record_type == "CLOSED"
        ]

        for i, record in enumerate(head_records):
            record_type = record.get("record_type")
            record_id = record.get("record_id")
            is_correction = record.get("supersedes") is not None

            if (
                record_type in MESSAGE_TYPES
                and not any(position < i for position in lease_positions)
            ):
                errors.append(
                    f"{record_id}: {record_type} requires an earlier lease on "
                    "the same head"
                )

            if record_type == "CLOSED" and not any(
                position < i for position in decision_positions
            ):
                errors.append(
                    f"{record_id}: CLOSED requires an earlier DECISION on the same head"
                )

            if record_type in {"TASK_LEASE", "HANDOFF", "PROPOSAL", "REVIEW"}:
                if any(position < i for position in decision_positions):
                    errors.append(
                        f"{record_id}: {record_type} cannot occur after DECISION"
                    )

            if any(position < i for position in closed_positions):
                if not (
                    is_correction
                    and record_type in MESSAGE_TYPES
                    and record.get("supersedes")
                    in {
                        prior.get("record_id")
                        for prior in head_records[:i]
                        if prior.get("record_type") == record_type
                    }
                ):
                    errors.append(
                        f"{record_id}: {record_type} cannot occur after CLOSED "
                        "unless it is a same-type correction"
                    )

        effective_decisions = [
            record
            for record in head_records
            if record.get("record_type") == "DECISION"
            and record.get("record_id") in effective_messages
        ]
        if len(effective_decisions) > 1:
            errors.append(
                f"{head}: multiple effective DECISION records: "
                + ", ".join(r.get("record_id") for r in effective_decisions)
            )

        effective_closed = [
            record
            for record in head_records
            if record.get("record_type") == "CLOSED"
            and record.get("record_id") in effective_messages
        ]
        if len(effective_closed) > 1:
            errors.append(
                f"{head}: multiple effective CLOSED records: "
                + ", ".join(r.get("record_id") for r in effective_closed)
            )

    return errors


def validate(records):
    errors = _validate_canonical_order(records)
    index_errors, by_id, index = _index_records(records)
    errors.extend(index_errors)
    lease_superseders, message_superseders = _valid_supersessions(
        records, by_id, index, errors
    )

    live_by_head = live_leases(records, lease_superseders)
    for head, live in live_by_head.items():
        if len(live) > 1:
            descriptions = ", ".join(
                f"{r.get('record_id')} owner={lease_owner(r)!r}" for r in live
            )
            errors.append(f"multiple live lease chains at {head}: {descriptions}")

    errors.extend(_validate_lifecycle_order(records, message_superseders))

    for record in records:
        for field in ("discovery_refs", "evidence_refs"):
            value = record.get(field, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item for item in value
            ):
                errors.append(
                    f"{record.get('record_id')}: {field} must be a list of "
                    "nonempty strings"
                )

    return errors


def validate_authorization(records, head_sha: str, actor: str | None = None):
    """Validate source mutation/dispatch authorization for one exact source SHA."""
    errors = validate(records)
    if not isinstance(head_sha, str) or SHA40_RE.fullmatch(head_sha) is None:
        errors.append("authorization head must be an exact lowercase 40-hex SHA")
        return errors

    _, by_id, index = _index_records(records)
    supersession_errors = []
    lease_superseders, message_superseders = _valid_supersessions(
        records, by_id, index, supersession_errors
    )
    live = live_leases(records, lease_superseders).get(head_sha, [])
    if len(live) != 1:
        errors.append(
            f"authorization for {head_sha} requires exactly one live "
            f"task lease/handoff; found {len(live)}"
        )
        return errors

    effective_messages = [
        record
        for record in _effective_messages(records, message_superseders)
        if record.get("head_sha") == head_sha
    ]
    if any(record.get("record_type") == "CLOSED" for record in effective_messages):
        errors.append(f"authorization for {head_sha} rejected: task is CLOSED")
        return errors
    if any(record.get("record_type") == "DECISION" for record in effective_messages):
        errors.append(
            f"authorization for {head_sha} rejected: task already has a DECISION"
        )
        return errors

    owner = lease_owner(live[0])
    if actor is not None and actor != owner:
        errors.append(
            f"authorization actor {actor!r} is not live owner {owner!r} "
            f"for {head_sha}"
        )
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--records", type=Path, default=Path("collaboration/records")
    )
    parser.add_argument(
        "--authorization-head",
        help="Require an exact live lease/handoff for this source SHA.",
    )
    parser.add_argument(
        "--actor",
        help="When authorizing, require this actor to be the effective live owner.",
    )
    args = parser.parse_args()
    if args.actor and not args.authorization_head:
        parser.error("--actor requires --authorization-head")

    records = load_records(args.records)
    if args.authorization_head:
        errors = validate_authorization(records, args.authorization_head, args.actor)
    else:
        errors = validate(records)

    print(
        json.dumps(
            {
                "schema": "cace-collaboration-lifecycle-v1",
                "records_checked": len(records),
                "authorization_head": args.authorization_head,
                "actor": args.actor,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
