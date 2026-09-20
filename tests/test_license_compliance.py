from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_license_audit_passes_source_contract():
    audit = _load_script("audit_license_compliance.py")
    errors, _warnings = audit.audit_repository(ROOT)
    assert errors == []


def test_direct_dependency_policy_covers_runtime_and_optional_dependencies():
    audit = _load_script("audit_license_compliance.py")
    policy = json.loads((ROOT / "ops" / "license_compliance_policy.json").read_text())
    known = set(policy["python_direct_dependencies"])

    import tomllib
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = list(pyproject["project"].get("dependencies", []))
    for group in pyproject["project"].get("optional-dependencies", {}).values():
        dependencies.extend(group)

    actual = {
        audit.requirement_name(req)
        for req in dependencies
        if audit.requirement_name(req) != "cace-studio"
    }
    assert actual <= known


def test_release_generator_marks_pyside6_for_manual_review():
    generator = _load_script("generate_third_party_notices.py")
    assert (
        generator._license_risk("PySide6", "LGPL-3.0-only OR GPL-3.0-only")
        == "MANUAL_REVIEW_REQUIRED"
    )
    assert generator._license_risk("FastAPI", "MIT") == "NOTICE_REQUIRED"
    assert generator._license_risk("numpy", "BSD-3-Clause") == "NOTICE_REQUIRED"


def test_proprietary_package_legal_files_are_declared():
    import tomllib
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["license"] == "LicenseRef-CACE-Proprietary"
    assert {
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
    } <= set(pyproject["project"]["license-files"])
