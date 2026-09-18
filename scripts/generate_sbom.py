#!/usr/bin/env python3
from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import re
import tomllib

from audit_third_party_licenses import declared_dependencies


def installed_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--policy", default="third_party_policy.json")
    parser.add_argument("--spdx", default="SBOM.spdx.json")
    parser.add_argument("--cyclonedx", default="SBOM.cyclonedx.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    policy = json.loads((root / args.policy).read_text(encoding="utf-8"))
    entries = policy["components"]
    names = sorted(declared_dependencies(root), key=str.casefold)

    packages = []
    components = []
    for index, name in enumerate(names, start=1):
        entry = entries[name]
        version = installed_version(name) or "declared-unresolved"
        spdx_id = "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", name)
        packages.append(
            {
                "SPDXID": spdx_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": entry["license"],
                "licenseDeclared": entry["license"],
                "copyrightText": "NOASSERTION",
                "comment": entry.get("obligation", entry.get("status", "")),
            }
        )
        components.append(
            {
                "type": "library",
                "bom-ref": f"pkg:cace-third-party/{name}@{version}",
                "name": name,
                "version": version,
                "licenses": [{"expression": entry["license"]}],
                "properties": [
                    {"name": "cace:policy-status", "value": entry["status"]},
                    {"name": "cace:role", "value": entry.get("role", "unknown")},
                ],
            }
        )

    spdx = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "CACE Studio dependency SBOM",
        "documentNamespace": "https://cace.local/sbom/runtime-v1",
        "creationInfo": {"creators": ["Tool: CACE scripts/generate_sbom.py"]},
        "packages": packages,
    }
    cyclone = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "cace-studio"}},
        "components": components,
    }
    (root / args.spdx).write_text(json.dumps(spdx, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / args.cyclonedx).write_text(json.dumps(cyclone, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
