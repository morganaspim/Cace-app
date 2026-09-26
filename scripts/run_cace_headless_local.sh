#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  CACE_MODEL_GGUF=/abs/path/model.gguf [CACE_LLAMA_SERVER_BIN=/abs/path/llama-server] \
    scripts/run_cace_headless_local.sh

Optional environment:
  CACE_LLM_CTX_SIZE      default 8192
  CACE_LLM_THREADS       default: detected CPU count, capped at 8
  CACE_HEADLESS_LOG_DIR  default runtime/headless

The launcher never downloads model/runtime files. Both services bind to loopback.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

model="${CACE_MODEL_GGUF:-}"
if [[ -z "$model" ]]; then
  echo "CACE_MODEL_GGUF is required and must point to the pre-provisioned GGUF." >&2
  exit 2
fi
if [[ "$model" != /* ]]; then
  echo "CACE_MODEL_GGUF must be an absolute path." >&2
  exit 2
fi
if [[ ! -f "$model" ]]; then
  echo "CACE model file not found: $model" >&2
  exit 2
fi

llama_bin="${CACE_LLAMA_SERVER_BIN:-}"
if [[ -z "$llama_bin" ]]; then
  llama_bin="$(command -v llama-server || true)"
fi
if [[ -z "$llama_bin" || ! -x "$llama_bin" ]]; then
  echo "llama-server not found. Set CACE_LLAMA_SERVER_BIN to the pinned local binary." >&2
  exit 2
fi

ctx="${CACE_LLM_CTX_SIZE:-8192}"
if ! [[ "$ctx" =~ ^[0-9]+$ ]] || [[ "$ctx" -lt 512 ]]; then
  echo "CACE_LLM_CTX_SIZE must be an integer >= 512." >&2
  exit 2
fi

detected_threads="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
if [[ "$detected_threads" -gt 8 ]]; then detected_threads=8; fi
if [[ "$detected_threads" -lt 1 ]]; then detected_threads=1; fi
threads="${CACE_LLM_THREADS:-$detected_threads}"
if ! [[ "$threads" =~ ^[0-9]+$ ]] || [[ "$threads" -lt 1 || "$threads" -gt 64 ]]; then
  echo "CACE_LLM_THREADS must be an integer between 1 and 64." >&2
  exit 2
fi

log_dir="${CACE_HEADLESS_LOG_DIR:-runtime/headless}"
mkdir -p "$log_dir"
model_sha="$(sha256sum "$model" | awk '{print $1}')"
printf '%s\n' "$model_sha" > "$log_dir/model.sha256"

llama_args=(
  -m "$model"
  --host 127.0.0.1
  --port 8080
  --alias Qwen/Qwen3.5-4B
  -c "$ctx"
  -t "$threads"
)

# Do not enable llama.cpp agent/file-access features. The local model is an
# untrusted planner; CACE's typed API remains the execution boundary.
"$llama_bin" "${llama_args[@]}" >"$log_dir/llama-server.log" 2>&1 &
llama_pid=$!

cleanup() {
  if kill -0 "$llama_pid" >/dev/null 2>&1; then
    kill "$llama_pid" >/dev/null 2>&1 || true
    wait "$llama_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python3 - <<'PY'
from __future__ import annotations
import json
import time
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = build_opener(ProxyHandler({}), NoRedirect())
url = "http://127.0.0.1:8080/v1/models"
deadline = time.monotonic() + 120.0
last = None
while time.monotonic() < deadline:
    try:
        with opener.open(Request(url, headers={"Accept": "application/json"}), timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data", []) if isinstance(payload, dict) else []
        if data:
            print("local llama.cpp model ready:", data[0].get("id"))
            raise SystemExit(0)
    except Exception as exc:
        last = exc
        time.sleep(1.0)
raise SystemExit(f"local llama.cpp server did not become ready: {last}")
PY

# CACE already has a browser-independent FastAPI execution surface. Binding it
# only to loopback makes that surface usable by Expert Robot without exposing
# the research assistant or CACE executor on the LAN/public network.
exec python3 -m uvicorn api.index:app \
  --host 127.0.0.1 \
  --port 8765 \
  --log-level info
