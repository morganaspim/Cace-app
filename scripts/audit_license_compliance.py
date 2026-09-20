#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
_REQ_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = _REQ_NAME.match(requirement.strip())
    if not match:
        raise ValueError(f"cannot parse requirement name: {requirement!r}")
    return normalize_name(match.group(0))


def _tracked_files(root: Path) -> list[Path]:
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
        )
        return [root / item.decode("utf-8") for item in raw.split(b"\0") if item]
    except Exception:
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def _iter_direct_requirements(pyproject: dict) -> Iterable[tuple[str, str]]:
    project = pyproject["project"]
    for requirement in project.get("dependencies", []):
        yield "runtime", requirement
    for scope, requirements in project.get("optional-dependencies", {}).items():
        for requirement in requirements:
            if requirement_name(requirement) == "cace-studio":
                continue
            yield scope, requirement


def audit_repository(root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    policy = json.loads((root / "ops" / "license_compliance_policy.json").read_text())
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())

    project = pyproject.get("project", {})
    if project.get("license") != "LicenseRef-CACE-Proprietary":
        errors.append("pyproject project.license must be LicenseRef-CACE-Proprietary")

    expected_legal = {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}
    declared = set(project.get("license-files", []))
    missing_legal = sorted(expected_legal - declared)
    if missing_legal:
        errors.append(f"pyproject license-files missing: {missing_legal}")

    build_requires = pyproject.get("build-system", {}).get("requires", [])
    if not any(req.startswith("setuptools>=77") for req in build_requires):
        errors.append("build-system must require setuptools>=77 for PEP 639 license metadata")

    declared_deps = policy.get("python_direct_dependencies", {})
    actual_by_name: dict[str, set[str]] = {}
    for scope, requirement in _iter_direct_requirements(pyproject):
        name = requirement_name(requirement)
        actual_by_name.setdefault(name, set()).add(scope)
        if name not in declared_deps:
            errors.append(
                f"direct dependency {name!r} ({scope}) is missing from ops/license_compliance_policy.json"
            )

    for name, record in declared_deps.items():
        normalized = normalize_name(name)
        if normalized not in actual_by_name:
            warnings.append(f"policy dependency {name!r} is not currently a direct pyproject dependency")
            continue
        policy_scopes = set(record.get("scopes", []))
        actual_scopes = actual_by_name[normalized]
        if not actual_scopes.issubset(policy_scopes):
            errors.append(f"policy scopes for {name!r} omit {sorted(actual_scopes - policy_scopes)}")

    notice = (root / "NOTICE").read_text()
    if "THIRD_PARTY_NOTICES.md" not in notice:
        errors.append("NOTICE must point to THIRD_PARTY_NOTICES.md")

    for required in expected_legal | {"docs/LICENSE_COMPLIANCE.md", "ops/license_compliance_policy.json"}:
        if not (root / required).is_file():
            errors.append(f"required legal/compliance file missing: {required}")

    tracked = _tracked_files(root)
    reviewed = {
        str((root / path).resolve())
        for path in policy.get("bundled_material_gate", {}).get("reviewed_files", [])
    }
    flagged_exts = {
        ext.lower()
        for ext in policy.get("bundled_material_gate", {}).get("unreviewed_extensions", [])
    }
    for path in tracked:
        if path.suffix.lower() in flagged_exts and str(path.resolve()) not in reviewed:
            errors.append(
                "unreviewed bundled material requires provenance/license review: "
                + str(path.relative_to(root))
            )

    attribution_surfaces = [
        "README.md",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "docs/GOAL_REGISTRY.json",
        "docs/CHAT_IDEA_LEDGER.md",
        "docs/MASTER_BUILD_SPEC.md",
        "GEMINI_CONNECTION_MANIFEST.json",
    ]
    for relative in attribution_surfaces:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"sophonic", text, flags=re.IGNORECASE):
            errors.append(
                "voluntary Sophonic attribution remains in production attribution surface: "
                + relative
            )

    webapp_pkg = root / "webapp" / "package.json"
    if webapp_pkg.is_file():
        lock_candidates = [
            root / "webapp" / "package-lock.json",
            root / "webapp" / "pnpm-lock.yaml",
            root / "webapp" / "yarn.lock",
        ]
        if not any(p.is_file() for p in lock_candidates):
            errors.append("webapp package.json exists without a dependency lockfile")
        if not (root / "webapp" / "THIRD_PARTY_LICENSES.json").is_file():
            errors.append("webapp dependency tree exists but webapp/THIRD_PARTY_LICENSES.json is missing")

    return errors, warnings


def main() -> int:
    errors, warnings = audit_repository()
    for warning in warnings:
        print(f"LICENSE_AUDIT_WARNING {warning}")
    for error in errors:
        print(f"LICENSE_AUDIT_ERROR {error}")
    if errors:
        print(f"CACE_LICENSE_AUDIT=FAIL errors={len(errors)} warnings={len(warnings)}")
        return 1
    print(f"CACE_LICENSE_AUDIT=PASS warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
