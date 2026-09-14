#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FORMAL="$ROOT/formal/cace_formal"

find_local_bin() {
  local candidates=(
    "$ROOT/formal/toolchain/bin"
    "$ROOT/formal/lean/bin"
    "/mnt/data/lean/bin"
    "/mnt/data/lean4/bin"
  )
  shopt -s nullglob
  candidates+=(/mnt/data/*lean*/bin)
  candidates+=(/mnt/data/*lean*/build/release/stage1/bin)
  candidates+=(/mnt/data/*lean*/build/release/stage0/bin)
  candidates+=(/mnt/data/*/build/release/stage1/bin)
  candidates+=(/mnt/data/*/build/release/stage0/bin)
  shopt -u nullglob
  for b in "${candidates[@]}"; do
    if [[ -x "$b/lean" && -x "$b/lake" ]]; then
      printf '%s\n' "$b"
      return 0
    fi
  done
  return 1
}

if command -v lean >/dev/null && command -v lake >/dev/null; then
  :
elif b="$(find_local_bin)"; then
  export PATH="$b:$PATH"
  echo "Using local Lean toolchain: $b"
elif command -v elan >/dev/null; then
  echo "Using elan-managed Lean toolchain."
else
  echo "No runnable Lean 4 toolchain found." >&2
  echo "CACE searched PATH and canonical uploaded stage0/stage1 build paths." >&2
  echo "Source PDFs, lean-toolchain selectors, and lakefile fragments are not executable toolchains." >&2
  exit 77
fi

cd "$FORMAL"
lake update
lake exe cache get
lake build
