from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cace_studio.core.qualification_drift import assert_no_qualification_drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a current CACE formal qualification has drifted on sensitive paths."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        results = assert_no_qualification_drift(args.repo_root, head=args.head)
        payload = {
            "schema_version": 1,
            "status": "PASS",
            "qualified_claims_checked": len(results),
            "results": [result.to_dict() for result in results],
        }
        code = 0
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        code = 1

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
