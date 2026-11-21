"""Deterministically build a fixture-only definition; never publish or dispatch."""
import hashlib
import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "ops/merlin_repair_validation"


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()}


def main():
    pins = {str(path.relative_to(PAYLOAD)): identity(path)
            for path in sorted(PAYLOAD.rglob("*.py"))}
    controller = (PAYLOAD / "controller.py").read_text()
    body = controller + "\nsys.exit(main(" + repr(pins) + "))\n"
    header = '''name: Merlin unprivileged repair fixtures

"on":
  push:
    branches: ["merlin/browser-operations-20261121"]
    paths: ["merlin/repair-validation-requests/**"]

permissions:
  contents: read

concurrency:
  group: merlin-dot-oci-operations
  cancel-in-progress: false

jobs:
  fixed-repair-fixtures:
    runs-on: [self-hosted, cace, oci, aarch64]
    timeout-minutes: 10
    steps:
      - name: Verify frozen sources and run isolated fixtures as UID1000
        shell: bash
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 - <<'PYCODE'
'''
    footer = '''          PYCODE
      - name: Preserve fixture logs and all failure receipts
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: merlin-repair-validation-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ runner.temp }}/merlin-repair-validation-${{ github.run_id }}-${{ github.run_attempt }}/
          include-hidden-files: true
          retention-days: 30
          if-no-files-found: warn
'''
    workflow = ROOT / ".github/workflows/merlin-repair-validation.yml"
    workflow.write_text(header + textwrap.indent(body, "          ") + footer)
    sources = {"schema": "merlin-repair-validation-source-pins/1", "sources": pins,
        "workflow": identity(workflow), "fixture_total": 101,
        "source_transfer": "Reviewed private Merlin repair sources copied to a private Cace-app test-only namespace.",
        "native_execution": False, "publication": "not_attempted"}
    (ROOT / "SOURCE_PINS.json").write_text(json.dumps(sources, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"pinned_sources": len(pins), "workflow": identity(workflow), "native_execution": False}))


if __name__ == "__main__":
    main()
