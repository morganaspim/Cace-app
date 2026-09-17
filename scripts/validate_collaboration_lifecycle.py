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
from pathlib import Path

LEASE_TYPES = {"TASK_LEASE", "HANDOFF"}
MESSAGE_TYPES = {"PROPOSAL", "REVIEW", "DECISION", "CLOSED"}
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


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
    valid_superseders = {}
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
        if record.get("record_type") not in LEASE_TYPES or old.get("record_type") not in LEASE_TYPES:
            errors.append(f"{record_id}: only TASK_LEASE/HANDOFF may supersede a lease/handoff")
            continue
        if prior_id in superseding_record_for:
            errors.append(
                f"{record_id}: {prior_id} already superseded by "
                f"{superseding_record_for[prior_id]}"
            )
            continue

        old_owner = lease_owner(old)
        record_type = record.get("record_type")
        if record_type == "HANDOFF":
            if record.get("sender") != old_owner:
                errors.append(
                    f"{record_id}: HANDOFF sender must be current owner {old_owner!r}"
                )
                continue
            new_owner = record.get("target")
            if not isinstance(new_owner, str) or not new_owner:
                errors.append(f"{record_id}: HANDOFF target must name the new owner")
                continue
            if new_owner == old_owner:
                errors.append(f"{record_id}: HANDOFF target must change owner")
                continue
        else:
            if record.get("sender") != old_owner:
                errors.append(
                    f"{record_id}: owner change requires HANDOFF; "
                    f"current owner is {old_owner!r}"
                )
                continue

        valid_superseders[prior_id] = record_id
        superseding_record_for[prior_id] = record_id
    return valid_superseders


def live_leases(records, valid_superseders):
    by_head = defaultdict(list)
    for record in records:
        if record.get("record_type") not in LEASE_TYPES:
            continue
        if record.get("record_id") in valid_superseders:
            continue
        by_head[record.get("head_sha")].append(record)
    return by_head


def validate(records):
    errors, by_id, index = _index_records(records)
    valid_superseders = _valid_supersessions(records, by_id, index, errors)

    live_by_head = live_leases(records, valid_superseders)
    for head, live in live_by_head.items():
        if len(live) > 1:
            descriptions = ", ".join(
                f"{r.get('record_id')} owner={lease_owner(r)!r}" for r in live
            )
            errors.append(f"multiple live lease chains at {head}: {descriptions}")

    records_by_head = defaultdict(list)
    for record in records:
        records_by_head[record.get("head_sha")].append(record)

    for head, head_records in records_by_head.items():
        types = [record.get("record_type") for record in head_records]
        lease_positions = [
            i for i, record_type in enumerate(types) if record_type in LEASE_TYPES
        ]
        for i, record_type in enumerate(types):
            record_id = head_records[i].get("record_id")
            if (
                record_type in MESSAGE_TYPES
                and not any(position < i for position in lease_positions)
            ):
                errors.append(
                    f"{record_id}: {record_type} requires an earlier lease on the same head"
                )
            if record_type == "CLOSED" and "DECISION" not in types[:i]:
                errors.append(
                    f"{record_id}: CLOSED requires an earlier DECISION on the same head"
                )

    for record in records:
        for field in ("discovery_refs", "evidence_refs"):
            value = record.get(field, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item for item in value
            ):
                errors.append(
                    f"{record.get('record_id')}: {field} must be a list of nonempty strings"
                )

    return errors


def validate_authorization(records, head_sha: str, actor: str | None = None):
    """Validate mutation/dispatch authorization for one exact source SHA."""
    errors = validate(records)
    if not isinstance(head_sha, str) or SHA40_RE.fullmatch(head_sha) is None:
        errors.append("authorization head must be an exact lowercase 40-hex SHA")
        return errors

    _, by_id, index = _index_records(records)
    supersession_errors = []
    valid_superseders = _valid_supersessions(
        records, by_id, index, supersession_errors
    )
    live = live_leases(records, valid_superseders).get(head_sha, [])
    if len(live) != 1:
        errors.append(
            f"authorization for {head_sha} requires exactly one live task lease/handoff; "
            f"found {len(live)}"
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
