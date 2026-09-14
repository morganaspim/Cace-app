#!/usr/bin/env bash
set -euo pipefail
URL='https://github.com/leanprover/lean4/releases/download/v4.32.1/lean-4.32.1-linux.tar.zst'
SHA='57d5c062a6b4bae6fba511a1704aa124dff461c37d0fc94585637fbb7d951b50'
DEST="${1:-/tmp/lean-4.32.1-linux.tar.zst}"
curl -L "$URL" -o "$DEST"
echo "$SHA  $DEST" | sha256sum -c -
echo "$DEST"
