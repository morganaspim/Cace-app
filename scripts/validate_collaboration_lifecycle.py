#!/usr/bin/env python3
"""Cross-record lifecycle checks for CACE AI coordination.

This validates coordination structure only; it never promotes proof authority.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

TERMINAL = {"CLOSED"}


def load_records(directory: Path) -> list[dict]:
    records = []
    for path in sorted(directory.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        value["__path"] = str(path)
        records.append(value)
    return records


def validate(records: list[dict]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, dict] = {}
    leases_by_head: dict[str, list[dict]] = defaultdict(list)
    superseded: set[str] = set()

    for record in records:
        rid = record.get("record_id")
        if not isinstance(rid, str):
            errors.append(f"{record.get('__path')}: missing record_id")
            continue
        if rid in by_id:
            errors.append(f"duplicate record_id: {rid}")
        by_id[rid] = record
        if record.get("record_type") == "TASK_LEASE":
            leases_by_head[str(record.get("head_sha"))].append(record)
        prior = record.get("supersedes")
        if isinstance(prior, str):
            superseded.add(prior)

    for record in records:
        rid = record.get("record_id")
        prior = record.get("supersedes")
        if prior is not None:
            if prior == rid:
                errors.append(f"{rid}: cannot supersede itself")
            elif prior not in by_id:
                errors.append(f"{rid}: supersedes unknown record {prior}")
        for field in ("discovery_refs", "evidence_refs"):
            refs = record.get(field, [])
            if refs is not None and (not isinstance(refs, list) or not all(isinstance(x, str) and x for x in refs)):
                errors.append(f"{rid}: {field} must be a list of nonempty strings")

    # One live task lease owner per exact head. A later record may explicitly
    # supersede an earlier lease to hand ownership over without rewriting history.
    for head, leases in leases_by_head.items():
        live = [r for r in leases if r.get("record_id") not in superseded]
        owners = {str(r.get("sender")) for r in live}
        if len(live) > 1 and len(owners) > 1:
            errors.append(f"conflicting live TASK_LEASE owners at {head}: {', '.join(sorted(owners))}")

    # HANDOFF must point to a prior task/lease record through supersedes.
    for record in records:
        if record.get("record_type") == "HANDOFF":
            rid = str(record.get("record_id"))
            prior = record.get("supersedes")
            if not isinstance(prior, str):
                errors.append(f"{rid}: HANDOFF requires supersedes")
            elif by_id.get(prior, {}).get("record_type") not in {"TASK_LEASE", "HANDOFF"}:
                errors.append(f"{rid}: HANDOFF must supersede TASK_LEASE or HANDOFF")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("collaboration/records"))
    args = parser.parse_args()
    records = load_records(args.records)
    errors = validate(records)
    print(json.dumps({"schema": "cace-collaboration-lifecycle-v1", "records_checked": len(records), "errors": errors}, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
