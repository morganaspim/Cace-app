from __future__ import annotations

import argparse
from pathlib import Path

from cace_studio.public_help import write_public_help


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate customer-safe CACE feature/module help from public contracts."
    )
    parser.add_argument(
        "--markdown",
        default="docs/help/generated/CACE_PUBLIC_HELP.md",
        help="Customer-facing Markdown output path.",
    )
    parser.add_argument(
        "--json",
        default="docs/help/generated/cace_public_help.json",
        help="Machine-readable public help output path.",
    )
    args = parser.parse_args()
    markdown, payload = write_public_help(args.markdown, args.json)
    print(f"CACE_PUBLIC_HELP_GENERATED markdown={markdown} json={payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
