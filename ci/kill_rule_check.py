#!/usr/bin/env python3
"""Pre-registered falsifier check.

Read-only, offline, stdlib only. No network, no writes.

Every registered claim must carry one named falsifier: the single observable
statement that, if true, makes the claim false. A claim with no named way to
die is not evidence, it is a mood, and this job exits non-zero on it.

Scanned (relative to repo root, overridable with --root):
  collaboration/records/kill_rules/**/*.json   registry files (shape = cace-kill-rule.schema.json)
  collaboration/claims/**/*.json               claim files, each item needs a falsifier

Exit codes: 0 all clean, 1 at least one violation, 2 bad invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
BANDS = {"DIES", "SURVIVES_BOUNDED", "SURVIVES"}
EVIDENCE = {"AI_PROPOSAL", "ENGINEERING_VERIFIED", "CERTIFIED_NUMERICAL", "PROVED"}
COMPARISONS = {"<", "<=", "==", ">=", ">", "!="}
# A falsifier that is only a placeholder is the same as no falsifier.
PLACEHOLDERS = {
    "", "tbd", "todo", "n/a", "na", "none", "later", "?", "???",
    "to be determined", "unknown", "fixme",
}

violations: list[str] = []


def bad(path: str, where: str, msg: str) -> None:
    violations.append(f"{path}: {where}: {msg}")


def real_falsifier(value) -> bool:
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDERS


def check_rule(path: str, idx: int, rule) -> None:
    where = f"kill_rules[{idx}]"
    if not isinstance(rule, dict):
        bad(path, where, "not an object")
        return

    for key in (
        "kill_rule_id", "claim_id", "head_sha", "falsifier", "observable",
        "test", "verdict_bands", "pre_registered_at", "status",
    ):
        if key not in rule:
            bad(path, where, f"missing required key {key!r}")

    if not real_falsifier(rule.get("falsifier")):
        bad(path, where, "no named falsifier: claim has no way to die")

    sha = rule.get("head_sha")
    if not (isinstance(sha, str) and HEX40.match(sha)):
        bad(path, where, "head_sha must be lowercase 40-hex")

    obs = rule.get("observable")
    if isinstance(obs, dict):
        if not obs.get("metric"):
            bad(path, where, "observable.metric empty")
        if obs.get("comparison") not in COMPARISONS:
            bad(path, where, "observable.comparison invalid")
        if not isinstance(obs.get("threshold"), (int, float)) or isinstance(obs.get("threshold"), bool):
            bad(path, where, "observable.threshold must be a number")
    elif obs is not None:
        bad(path, where, "observable must be an object")

    test = rule.get("test")
    if isinstance(test, dict):
        if not test.get("procedure"):
            bad(path, where, "test.procedure empty")
        if test.get("required_evidence_class") not in EVIDENCE:
            bad(path, where, "test.required_evidence_class invalid")
    elif test is not None:
        bad(path, where, "test must be an object")

    bands = rule.get("verdict_bands")
    if isinstance(bands, list) and bands:
        band_names = []
        for j, b in enumerate(bands):
            if not isinstance(b, dict) or b.get("band") not in BANDS:
                bad(path, f"{where}.verdict_bands[{j}]", "invalid band")
                continue
            band_names.append(b["band"])
            if not b.get("condition"):
                bad(path, f"{where}.verdict_bands[{j}]", "empty condition")
        if "SURVIVES_BOUNDED" in band_names:
            cs = rule.get("cost_stack")
            if not isinstance(cs, dict):
                bad(path, where, "SURVIVES_BOUNDED band requires a cost_stack")
            elif not cs.get("description") or not cs.get("cost_model"):
                bad(path, where, "cost_stack must name description and cost_model")
    else:
        bad(path, where, "verdict_bands must be a non-empty array")

    status = rule.get("status")
    if status not in {"PRE_REGISTERED", "EXECUTED", "CLOSED"}:
        bad(path, where, f"invalid status {status!r}")
    if status in {"EXECUTED", "CLOSED"}:
        if not rule.get("executed_at"):
            bad(path, where, "executed/closed rule missing executed_at")
        out = rule.get("outcome")
        if not isinstance(out, dict):
            bad(path, where, "executed/closed rule missing outcome")
        else:
            if out.get("band") not in BANDS:
                bad(path, where, "outcome.band invalid")
            if out.get("evidence_class") not in EVIDENCE:
                bad(path, where, "outcome.evidence_class invalid")
            h = out.get("artifact_sha256")
            if h is not None and not HEX64.match(str(h)):
                bad(path, where, "outcome.artifact_sha256 must be 64-hex")


def check_registry(path: str, doc) -> None:
    if not isinstance(doc, dict):
        bad(path, "<root>", "registry must be an object")
        return
    if not isinstance(doc.get("schema_version"), int):
        bad(path, "<root>", "missing integer schema_version")
    rules = doc.get("kill_rules")
    if not isinstance(rules, list):
        bad(path, "<root>", "kill_rules must be an array")
        return
    for i, r in enumerate(rules):
        check_rule(path, i, r)


def check_claims(path: str, doc) -> None:
    claims = doc.get("claims") if isinstance(doc, dict) else None
    if not isinstance(claims, list):
        bad(path, "<root>", "claims file must contain a 'claims' array")
        return
    for i, c in enumerate(claims):
        where = f"claims[{i}]"
        if not isinstance(c, dict):
            bad(path, where, "not an object")
            continue
        if not c.get("claim_id"):
            bad(path, where, "missing claim_id")
        if not real_falsifier(c.get("falsifier")):
            bad(path, where, "no named falsifier: claim has no way to die")


def collect(root: str) -> list[str]:
    hits = []
    for sub in ("collaboration/records/kill_rules", "collaboration/claims"):
        base = os.path.join(root, sub)
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if name.endswith(".json"):
                    hits.append(os.path.join(dirpath, name))
    return sorted(hits)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check every claim has a named falsifier.")
    ap.add_argument("--root", default=".", help="repo root to scan (default: .)")
    args = ap.parse_args()

    root = args.root
    if not os.path.isdir(root):
        print(f"kill-rule check: root not found: {root}", file=sys.stderr)
        return 2

    files = collect(root)
    for path in files:
        rel = os.path.relpath(path, root)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            bad(rel, "<file>", f"unreadable or invalid JSON: {exc}")
            continue
        if "kill_rules" in doc if isinstance(doc, dict) else False:
            check_registry(rel, doc)
        elif "claims" in doc if isinstance(doc, dict) else False:
            check_claims(rel, doc)
        else:
            bad(rel, "<root>", "not a kill-rule registry or claims file")

    if violations:
        print(f"kill-rule check: {len(violations)} violation(s)")
        for v in violations:
            print(f"  FAIL {v}")
        return 1

    print(f"kill-rule check: clean ({len(files)} file(s) scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
