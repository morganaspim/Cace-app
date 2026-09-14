#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v lean >/dev/null 2>&1 || ! command -v lake >/dev/null 2>&1; then
  echo 'FORMAL_GATE=NOT_RUN: lean/lake unavailable' >&2
  exit 77
fi
lake update
lake exe cache get
lake build
printf '%s\n' 'FORMAL_GATE=PASS'
