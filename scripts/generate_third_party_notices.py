#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import re
import shutil
from collections import deque
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "ops" / "license_compliance_policy.json").read_text())
_REQ_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
_LICENSE_BASENAMES = ("license", "copying", "notice", "authors", "copyright")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = _REQ_NAME.match(requirement.strip())
    if not match:
        raise ValueError(f"cannot parse requirement name: {requirement!r}")
    return normalize_name(match.group(0))


def _is_extra_only(requirement: str) -> bool:
    marker = requirement.split(";", 1)[1] if ";" in requirement else ""
    return bool(re.search(r"\bextra\s*(==|!=|in|not in)", marker))


def _license_risk(name: str, expression: str) -> str:
    direct = POLICY.get("python_direct_dependencies", {}).get(normalize_name(name))
    if direct and direct.get("decision") == "manual_review_required":
        return "MANUAL_REVIEW_REQUIRED"
    text = expression or ""
    for marker in POLICY["release_license_classification"]["review_markers"]:
        if marker.lower() in text.lower():
            return "MANUAL_REVIEW_REQUIRED"
    if not text.strip():
        return "METADATA_REVIEW"
    return "NOTICE_REQUIRED"


def _license_files(dist: metadata.Distribution) -> list[Path]:
    found: list[Path] = []
    for item in dist.files or ():
        base = Path(str(item)).name.lower()
        parts = [part.lower() for part in Path(str(item)).parts]
        is_license_dir = "licenses" in parts and any(part.endswith(".dist-info") for part in parts)
        is_license_named = base.startswith(_LICENSE_BASENAMES)
        if not (is_license_dir or is_license_named):
            continue
        path = Path(dist.locate_file(item))
        if path.is_file() and path.stat().st_size <= 5_000_000:
            found.append(path)
    unique: dict[str, Path] = {}
    for path in found:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        unique[digest] = path
    return list(unique.values())


def _dependencies(dist: metadata.Distribution) -> Iterable[str]:
    for requirement in dist.requires or ():
        if _is_extra_only(requirement):
            continue
        yield requirement


def collect(roots: list[str]) -> tuple[list[dict], list[str]]:
    queue = deque(normalize_name(root) for root in roots)
    seen: set[str] = set()
    records: list[dict] = []
    errors: list[str] = []

    while queue:
        requested = queue.popleft()
        if requested in seen:
            continue
        seen.add(requested)
        try:
            dist = metadata.distribution(requested)
        except metadata.PackageNotFoundError:
            errors.append(f"required distribution is not installed: {requested}")
            continue

        canonical = normalize_name(dist.metadata.get("Name", requested))
        expression = (dist.metadata.get("License-Expression") or dist.metadata.get("License") or "").strip()
        files = _license_files(dist)

        is_first_party = canonical == "cace-studio"
        risk = "FIRST_PARTY" if is_first_party else _license_risk(canonical, expression)
        if not is_first_party and not files:
            risk = "MISSING_LICENSE_FILE"
            errors.append(f"{canonical} {dist.version} has no discoverable packaged license/notice file")
        if risk == "MANUAL_REVIEW_REQUIRED":
            errors.append(
                f"{canonical} {dist.version} requires explicit distribution review ({expression or 'no expression'})"
            )

        records.append({
            "name": dist.metadata.get("Name", canonical),
            "normalized_name": canonical,
            "version": dist.version,
            "license_expression_or_legacy_text": expression or None,
            "risk": risk,
            "license_files": [str(path) for path in files],
        })

        for requirement in _dependencies(dist):
            child = requirement_name(requirement)
            try:
                metadata.distribution(child)
            except metadata.PackageNotFoundError:
                if ";" in requirement:
                    continue
                errors.append(
                    f"{canonical} requires {child}, but it is not installed in the release environment"
                )
                continue
            queue.append(child)

    records.sort(key=lambda item: item["normalized_name"])
    return records, errors


def write_bundle(records: list[dict], output_dir: Path) -> None:
    licenses_dir = output_dir / "THIRD_PARTY_LICENSES"
    licenses_dir.mkdir(parents=True, exist_ok=True)

    public_records = []
    for record in records:
        copied = []
        if record["normalized_name"] != "cace-studio":
            package_dir = licenses_dir / record["normalized_name"]
            package_dir.mkdir(parents=True, exist_ok=True)
            used_names: set[str] = set()
            for source_text in record["license_files"]:
                source = Path(source_text)
                name = source.name
                if name in used_names:
                    stem, suffix = source.stem, source.suffix
                    index = 2
                    while f"{stem}-{index}{suffix}" in used_names:
                        index += 1
                    name = f"{stem}-{index}{suffix}"
                used_names.add(name)
                target = package_dir / name
                shutil.copyfile(source, target)
                copied.append({
                    "path": str(target.relative_to(output_dir)),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                })

        item = dict(record)
        item.pop("license_files", None)
        item["copied_license_files"] = copied
        public_records.append(item)

    (output_dir / "third_party_inventory.json").write_text(
        json.dumps(
            {
                "schema": "cace-third-party-artifact-inventory-v1",
                "artifact_rule": "Generated from the exact installed release environment; not proof evidence.",
                "packages": public_records,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    rows = [
        "# Generated Third-Party License Inventory",
        "",
        "Generated from the exact Python environment supplied to the release-license tool.",
        "The accompanying THIRD_PARTY_LICENSES/ directory contains copied license/notice files.",
        "",
        "| Package | Version | License metadata | Gate |",
        "|---|---:|---|---|",
    ]
    for record in public_records:
        if record["normalized_name"] == "cace-studio":
            continue
        expr = (record["license_expression_or_legacy_text"] or "UNKNOWN").replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {record['name']} | {record['version']} | {expr} | {record['risk']} |")
    rows += [
        "",
        "If a package is marked MANUAL_REVIEW_REQUIRED or lacks copied license files, the release is blocked.",
        "",
    ]
    (output_dir / "THIRD_PARTY_LICENSES.md").write_text("\n".join(rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        default=None,
        help="Installed root distribution to include. Repeat for additional release-profile roots.",
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    roots = args.roots or ["cace-studio"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records, errors = collect(roots)
    write_bundle(records, output_dir)

    for error in errors:
        print(f"THIRD_PARTY_NOTICE_ERROR {error}")
    print(
        "CACE_THIRD_PARTY_NOTICE_BUNDLE="
        + ("FAIL" if errors else "PASS")
        + f" packages={len(records)} roots={','.join(roots)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
