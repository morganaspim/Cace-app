#!/usr/bin/env bash
# Tier-1 CACE conformance: repo in, PASS/FAIL/REFUSED out. No Lean, no network, no install.
set -uo pipefail
REPO="${1:-.}"; OUT="${2:-qualification_report.json}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/qualify.py" --repo "$REPO" --json > "$OUT"
code=$?
python3 "$HERE/qualify.py" --repo "$REPO" || true
echo "report: $OUT"
[ "$code" -eq 0 ] || echo "NON-PASS: $code"
exit "$code"
