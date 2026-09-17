#!/usr/bin/env python3
"""Fail-closed repository sweep for recurring bug classes and contract drift.

This is intentionally complementary to pytest. It catches structural failure
patterns before runtime tests, validates canonical registries against one
another, and turns confirmed bug families into permanent repository-wide guards.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PATTERN_REGISTRY = ROOT / "quality" / "bug_patterns.json"
BUG_CLASS_REGISTRY = ROOT / "quality" / "bug_classes.json"
ACTIVE_CONTRACT_GLOBS = (
    "cace_studio/**/*.py",
    "cace_studio/data/*.json",
    "scripts/**/*.py",
    "tests/**/*.py",
)
PYTHON_ROOTS = ("cace_studio", "scripts", "tests")
JSON_ROOTS = ("cace_studio/data", "schema", "quality")
V330_CLAIM_ID = "cace.v330.continuum-proof-strengthening"


def _iter_globs(patterns: Iterable[str]) -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_file():
                found[path.relative_to(ROOT).as_posix()] = path
    return [found[key] for key in sorted(found)]


def _location(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    prior = text.rfind("\n", 0, offset)
    column = offset + 1 if prior < 0 else offset - prior
    return line, column


def _is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(
        c in "0123456789abcdef" for c in value.lower()
    )


def _canonical_bug_class_digest(item: dict) -> str:
    payload = {key: value for key, value in item.items() if key != "fingerprint_sha256"}
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _check_python_syntax(errors: list[str], summary: dict[str, int]) -> None:
    checked = 0
    for root_name in PYTHON_ROOTS:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(part in {"__pycache__", "build", "dist", ".pytest_cache"} for part in path.parts):
                continue
            checked += 1
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except Exception as exc:
                rel = path.relative_to(ROOT).as_posix()
                errors.append(f"python-syntax:{rel}: {type(exc).__name__}: {exc}")
    summary["python_files_syntax_checked"] = checked


def _check_json_parse(errors: list[str], summary: dict[str, int]) -> None:
    checked = 0
    for root_name in JSON_ROOTS:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            checked += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                rel = path.relative_to(ROOT).as_posix()
                errors.append(f"json-parse:{rel}: {type(exc).__name__}: {exc}")
    summary["json_files_parsed"] = checked


def _check_pattern_registry(errors: list[str], summary: dict[str, int]) -> None:
    try:
        raw = json.loads(PATTERN_REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"bug-pattern-registry: cannot load: {type(exc).__name__}: {exc}")
        return
    if raw.get("schema_version") != 1:
        errors.append("bug-pattern-registry: schema_version must be 1")
        return
    patterns = raw.get("patterns")
    if not isinstance(patterns, list):
        errors.append("bug-pattern-registry: patterns must be an array")
        return
    seen: set[str] = set()
    files_checked = 0
    for item in patterns:
        if not isinstance(item, dict):
            errors.append("bug-pattern-registry: every pattern must be an object")
            continue
        pattern_id = str(item.get("id", "")).strip()
        if not pattern_id:
            errors.append("bug-pattern-registry: pattern id must be non-empty")
            continue
        if pattern_id in seen:
            errors.append(f"bug-pattern-registry: duplicate id {pattern_id!r}")
            continue
        seen.add(pattern_id)
        includes = item.get("include")
        excludes = item.get("exclude", [])
        expression = item.get("forbid_regex")
        if not isinstance(includes, list) or not includes or not all(isinstance(x, str) and x for x in includes):
            errors.append(f"bug-pattern-registry:{pattern_id}: include must be a non-empty string array")
            continue
        if not isinstance(excludes, list) or not all(isinstance(x, str) and x for x in excludes):
            errors.append(f"bug-pattern-registry:{pattern_id}: exclude must be a string array")
            continue
        if not isinstance(expression, str) or not expression:
            errors.append(f"bug-pattern-registry:{pattern_id}: forbid_regex must be non-empty")
            continue
        try:
            regex = re.compile(expression)
        except re.error as exc:
            errors.append(f"bug-pattern-registry:{pattern_id}: invalid regex: {exc}")
            continue
        for path in _iter_globs(includes):
            rel = path.relative_to(ROOT).as_posix()
            if any(fnmatch.fnmatch(rel, excluded) for excluded in excludes):
                continue
            files_checked += 1
            text = path.read_text(encoding="utf-8")
            for match in regex.finditer(text):
                line, column = _location(text, match.start())
                errors.append(
                    f"bug-pattern:{pattern_id}:{rel}:{line}:{column}: forbidden recurring bug pattern {match.group(0)!r}"
                )
    summary["bug_patterns_checked"] = len(seen)
    summary["bug_pattern_file_checks"] = files_checked


def _check_bug_class_ref(
    *,
    class_id: str,
    kind: str,
    raw_ref: object,
    errors: list[str],
) -> None:
    if not isinstance(raw_ref, dict):
        errors.append(f"bug-class-registry:{class_id}:{kind}: reference must be an object")
        return
    rel = raw_ref.get("path")
    needle = raw_ref.get("contains")
    if not isinstance(rel, str) or not rel or not isinstance(needle, str) or not needle:
        errors.append(
            f"bug-class-registry:{class_id}:{kind}: reference requires non-empty path and contains"
        )
        return
    path = ROOT / rel
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"bug-class-registry:{class_id}:{kind}: path escapes repository: {rel!r}")
        return
    if not path.is_file():
        errors.append(f"bug-class-registry:{class_id}:{kind}: missing guard/reproducer file {rel!r}")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(
            f"bug-class-registry:{class_id}:{kind}: cannot read {rel!r}: {type(exc).__name__}: {exc}"
        )
        return
    if needle not in text:
        errors.append(
            f"bug-class-registry:{class_id}:{kind}: {rel!r} no longer contains required hook {needle!r}"
        )


def _check_bug_class_registry(errors: list[str], summary: dict[str, int]) -> None:
    try:
        raw = json.loads(BUG_CLASS_REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"bug-class-registry: cannot load: {type(exc).__name__}: {exc}")
        return
    if raw.get("schema_version") != 1:
        errors.append("bug-class-registry: schema_version must be 1")
        return
    classes = raw.get("classes")
    if not isinstance(classes, list):
        errors.append("bug-class-registry: classes must be an array")
        return

    seen: set[str] = set()
    guarded = 0
    refs_checked = 0
    for item in classes:
        if not isinstance(item, dict):
            errors.append("bug-class-registry: every class must be an object")
            continue
        class_id = str(item.get("id", "")).strip()
        if not class_id:
            errors.append("bug-class-registry: class id must be non-empty")
            continue
        if class_id in seen:
            errors.append(f"bug-class-registry: duplicate id {class_id!r}")
            continue
        seen.add(class_id)

        if item.get("status") != "GUARDED":
            errors.append(f"bug-class-registry:{class_id}: status must be GUARDED before CI can pass")
        else:
            guarded += 1
        for field in ("description", "root_cause", "closure_rule"):
            if not isinstance(item.get(field), str) or not str(item[field]).strip():
                errors.append(f"bug-class-registry:{class_id}: {field} must be non-empty")

        observed = item.get("first_observed")
        if not isinstance(observed, dict):
            errors.append(f"bug-class-registry:{class_id}: first_observed must be an object")
        else:
            if not isinstance(observed.get("workflow_run_id"), int) or observed["workflow_run_id"] <= 0:
                errors.append(f"bug-class-registry:{class_id}: workflow_run_id must be positive")
            if not _is_hex(observed.get("head_sha"), 40):
                errors.append(f"bug-class-registry:{class_id}: head_sha must be 40-hex")
            if not isinstance(observed.get("signature"), str) or not observed["signature"].strip():
                errors.append(f"bug-class-registry:{class_id}: failure signature must be non-empty")

        expected = item.get("fingerprint_sha256")
        actual = _canonical_bug_class_digest(item)
        if not _is_hex(expected, 64):
            errors.append(f"bug-class-registry:{class_id}: fingerprint_sha256 must be 64-hex")
        elif expected.lower() != actual:
            errors.append(
                f"bug-class-registry:{class_id}: fingerprint mismatch {expected.lower()} != {actual}"
            )

        for kind in ("reproducer_refs", "guard_refs"):
            refs = item.get(kind)
            if not isinstance(refs, list) or not refs:
                errors.append(f"bug-class-registry:{class_id}: {kind} must be a non-empty array")
                continue
            for ref in refs:
                refs_checked += 1
                _check_bug_class_ref(
                    class_id=class_id,
                    kind=kind,
                    raw_ref=ref,
                    errors=errors,
                )

    summary["bug_classes_checked"] = len(seen)
    summary["bug_classes_guarded"] = guarded
    summary["bug_class_refs_checked"] = refs_checked


def _check_canonical_contract_links(errors: list[str], summary: dict[str, int]) -> None:
    from cace_studio.core.claim_registry import ClaimRegistry
    from cace_studio.core.proof_contract import ProofContractRegistry
    from cace_studio.core.proof_explorer import ProofExplorer
    from cace_studio.core.proof_ledger import ProofLedger

    claims = ClaimRegistry.load_default()
    contracts = ProofContractRegistry.load_default()
    ledger = ProofLedger.load_default()

    for contract in contracts.contracts:
        claim = claims.by_id(contract.claim_id)
        if claim is None:
            errors.append(
                f"canonical-link: proof contract {contract.contract_id!r} references missing claim {contract.claim_id!r}"
            )
        elif claim.proof_contract_id != contract.contract_id:
            errors.append(
                f"canonical-link: claim {claim.claim_id!r} binds {claim.proof_contract_id!r}, expected {contract.contract_id!r}"
            )

    for claim in claims.claims:
        if claim.proof_contract_id:
            contract = contracts.by_id(claim.proof_contract_id)
            if contract is None:
                errors.append(
                    f"canonical-link: claim {claim.claim_id!r} references missing proof contract {claim.proof_contract_id!r}"
                )
            elif contract.claim_id != claim.claim_id:
                errors.append(
                    f"canonical-link: proof contract {contract.contract_id!r} is bound to {contract.claim_id!r}, not {claim.claim_id!r}"
                )

    for entry in ledger.entries:
        missing = [claim_id for claim_id in entry.claim_ids if claims.by_id(claim_id) is None]
        if missing:
            errors.append(
                f"canonical-link: ledger release {entry.release!r} references missing claims {missing!r}"
            )
        if entry.proof_contract_id:
            contract = contracts.by_id(entry.proof_contract_id)
            if contract is None:
                errors.append(
                    f"canonical-link: ledger release {entry.release!r} references missing contract {entry.proof_contract_id!r}"
                )
            elif contract.claim_id not in entry.claim_ids:
                errors.append(
                    f"canonical-link: ledger release {entry.release!r} contract claim {contract.claim_id!r} is absent from entry claim_ids"
                )

    explorer = ProofExplorer(claims, ledger, contracts)
    conflicts = 0
    for claim in claims.claims:
        view = explorer.claim_view(claim.claim_id)
        if view.qualification_state == "CONFLICT":
            conflicts += 1
            errors.append(
                f"canonical-link: claim {claim.claim_id!r} is in CONFLICT state: {'; '.join(view.blockers)}"
            )

    summary["canonical_claims_checked"] = len(claims.claims)
    summary["proof_contracts_checked"] = len(contracts.contracts)
    summary["proof_ledger_entries_checked"] = len(ledger.entries)
    summary["qualification_conflicts"] = conflicts

    current = contracts.for_claim(V330_CLAIM_ID)
    if current is None:
        errors.append(f"canonical-link: missing authoritative contract for {V330_CLAIM_ID!r}")
        return
    match = re.fullmatch(r"(.+)\.v(\d+)", current.contract_id)
    if match is None:
        errors.append(
            f"canonical-link: current v330 contract id has no terminal version suffix: {current.contract_id!r}"
        )
        return
    prefix = match.group(1)
    version_re = re.compile(re.escape(prefix) + r"\.v\d+\b")
    stale_refs = 0
    for path in _iter_globs(ACTIVE_CONTRACT_GLOBS):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        for ref in version_re.finditer(text):
            value = ref.group(0)
            if value != current.contract_id:
                stale_refs += 1
                line, column = _location(text, ref.start())
                errors.append(
                    f"stale-contract-ref:{rel}:{line}:{column}: {value!r} != authoritative {current.contract_id!r}"
                )
    summary["stale_authoritative_contract_refs"] = stale_refs


def run_sweep() -> dict:
    errors: list[str] = []
    summary: dict[str, int] = {}
    checks = (
        ("python-syntax", _check_python_syntax),
        ("json-parse", _check_json_parse),
        ("bug-pattern-registry", _check_pattern_registry),
        ("bug-class-registry", _check_bug_class_registry),
        ("canonical-contract-links", _check_canonical_contract_links),
    )
    completed: list[str] = []
    for name, check in checks:
        try:
            check(errors, summary)
        except Exception as exc:
            errors.append(f"{name}: unexpected {type(exc).__name__}: {exc}")
        completed.append(name)
    return {
        "schema_version": 2,
        "status": "PASS" if not errors else "FAIL",
        "checks_completed": completed,
        "summary": summary,
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = run_sweep()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
