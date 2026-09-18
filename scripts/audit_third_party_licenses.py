#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tomllib


def _requirement_name(raw: str) -> str:
    text = raw.split(";", 1)[0].strip()
    text = text.split("[", 1)[0]
    return re.split(r"[<>=!~ ]", text, maxsplit=1)[0].strip()


def declared_dependencies(root: Path) -> set[str]:
    names: set[str] = set()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project", {})
        for raw in project.get("dependencies", []):
            names.add(_requirement_name(raw))
        for values in project.get("optional-dependencies", {}).values():
            for raw in values:
                name = _requirement_name(raw)
                if name != "cace-studio":
                    names.add(name)
    runtime = root / "requirements-runtime.txt"
    if runtime.is_file():
        for line in runtime.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                names.add(_requirement_name(line))
    for package_json in (root / "web" / "package.json", root / "package.json"):
        if not package_json.is_file():
            continue
        data = json.loads(package_json.read_text(encoding="utf-8"))
        for section in ("dependencies", "devDependencies"):
            names.update(data.get(section, {}).keys())
        if package_json.parent == root / "web":
            break
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--policy", default="third_party_policy.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    policy_path = root / args.policy
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    components = policy.get("components", {})
    dependencies = sorted(declared_dependencies(root), key=str.casefold)
    missing = [name for name in dependencies if name not in components]
    blocked = [
        name
        for name in dependencies
        if components.get(name, {}).get("status") in {"BLOCK", "REJECTED"}
    ]
    report = {
        "schema": "cace-license-audit-v1",
        "declared_dependencies": dependencies,
        "missing_policy_entries": missing,
        "blocked_dependencies": blocked,
        "passed": not missing and not blocked,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
