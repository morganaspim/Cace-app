#!/usr/bin/env bash
# Portable CACE v3.30 formal qualification for Linux/WSL.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

for cmd in git curl python3 grep timeout; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Missing required command: $cmd" >&2
    exit 2
  }
done

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing formal qualification from a dirty working tree." >&2
  exit 2
fi

COMMIT="$(git rev-parse HEAD)"
RUN_ID="${CACE_QUALIFICATION_RUN_ID:-portable-$(date -u +%Y%m%dT%H%M%SZ)-${COMMIT:0:12}}"
QUALIFICATION_SYSTEM="${CACE_QUALIFICATION_SYSTEM:-portable-local}"
OUTPUT_ROOT="${CACE_QUALIFICATION_OUTPUT:-$HOME/.cace/qualification/$RUN_ID}"
WORK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cace-formal.XXXXXXXX")"
FORMAL_DIR="$WORK_ROOT/formal"
ELAN_HOME="$WORK_ROOT/elan"
XDG_CACHE_HOME="$WORK_ROOT/cache"
VENV="$WORK_ROOT/venv"
AXIOM_AUDIT="$WORK_ROOT/v330-axioms.txt"
export ELAN_HOME XDG_CACHE_HOME
trap 'rm -rf -- "$WORK_ROOT"' EXIT

mkdir -p "$FORMAL_DIR" "$ELAN_HOME" "$XDG_CACHE_HOME" "$OUTPUT_ROOT"
cp -a formal/cace_formal/. "$FORMAL_DIR/"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install 'pytest>=8,<9'

# Load all static formal scope from the canonical proof contract.
readarray -t CONTRACT_VALUES < <(
  PYTHONPATH="$ROOT" "$VENV/bin/python" - <<'PY'
from cace_studio.core.proof_contract import ProofContractRegistry
c = ProofContractRegistry.load_default().for_claim("cace.v330.continuum-proof-strengthening")
if c is None:
    raise SystemExit("missing canonical v3.30 proof contract")
print(c.contract_id)
print(c.contract_sha256)
print(c.dependency_pins.get("mathlib_commit", ""))
print(c.build_target)
PY
)
PROOF_CONTRACT_ID="${CONTRACT_VALUES[0]}"
PROOF_CONTRACT_SHA256="${CONTRACT_VALUES[1]}"
MATHLIB_COMMIT="${CONTRACT_VALUES[2]}"
BUILD_TARGET="${CONTRACT_VALUES[3]}"
if [[ -z "$MATHLIB_COMMIT" || -z "$BUILD_TARGET" ]]; then
  echo "Proof contract is missing required Mathlib/build-target data." >&2
  exit 2
fi
AUDIT_LEAN_FILE="${BUILD_TARGET//./\/}.lean"

printf 'CACE portable qualification\ncommit=%s\nsystem=%s\nrun_id=%s\ncontract=%s\ncontract_sha256=%s\noutput=%s\n' \
  "$COMMIT" "$QUALIFICATION_SYSTEM" "$RUN_ID" "$PROOF_CONTRACT_ID" \
  "$PROOF_CONTRACT_SHA256" "$OUTPUT_ROOT"

PYTHONPATH="$ROOT" "$VENV/bin/python" -m pytest -q \
  tests/test_claim_promotion_v330.py \
  tests/test_claim_registry_v331.py \
  tests/test_proof_contract_v336.py \
  tests/test_qualification_drift_v331.py

curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
  -o "$WORK_ROOT/elan-init.sh"
sh "$WORK_ROOT/elan-init.sh" -y --default-toolchain none
export PATH="$ELAN_HOME/bin:$VENV/bin:$PATH"

cd "$FORMAL_DIR"
TOOLCHAIN="$(cat lean-toolchain)"
elan toolchain install "$TOOLCHAIN"
elan default "$TOOLCHAIN"
lean --version
lake --version

MATHLIB_NO_CACHE_ON_UPDATE=1 lake update
ACTUAL_MATHLIB="$(git -C .lake/packages/mathlib rev-parse HEAD)"
if [[ "$ACTUAL_MATHLIB" != "$MATHLIB_COMMIT" ]]; then
  echo "Mathlib mismatch: expected $MATHLIB_COMMIT, got $ACTUAL_MATHLIB" >&2
  exit 1
fi

lake build +Cache.Main
timeout 900 lake env lean --run .lake/packages/mathlib/Cache/Main.lean get "$AUDIT_LEAN_FILE"
find "$XDG_CACHE_HOME" -mindepth 1 -depth -delete || true

cd "$ROOT"
mapfile -t PROOF_FILES < <(
  PYTHONPATH="$ROOT" "$VENV/bin/python" - <<'PY'
from cace_studio.core.proof_contract import ProofContractRegistry
c = ProofContractRegistry.load_default().for_claim("cace.v330.continuum-proof-strengthening")
if c is None:
    raise SystemExit("missing canonical v3.30 proof contract")
for source in c.audited_source_files:
    print("formal/cace_formal/" + source)
PY
)
if [[ "${#PROOF_FILES[@]}" -eq 0 ]]; then
  echo "Proof contract has no audited source files." >&2
  exit 2
fi
if grep -nE '\bsorry\b|\badmit\b|OPEN OBLIGATION' "${PROOF_FILES[@]}"; then
  echo "Unclosed proof obligation found in contract-audited source." >&2
  exit 1
fi

cd "$FORMAL_DIR"
timeout 1200 lake build "$BUILD_TARGET"
lake env lean "$AUDIT_LEAN_FILE" 2>&1 | tee "$AXIOM_AUDIT"

cd "$ROOT"
PYTHONPATH="$ROOT" "$VENV/bin/python" scripts/audit_v330_axioms.py "$AXIOM_AUDIT"
PYTHONPATH="$ROOT" "$VENV/bin/python" scripts/write_v330_qualification_attestation.py \
  --repo-root "$ROOT" \
  --formal-dir "$FORMAL_DIR" \
  --qualification-system "$QUALIFICATION_SYSTEM" \
  --qualification-run-id "$RUN_ID" \
  --axiom-audit "$AXIOM_AUDIT" \
  --output-dir "$OUTPUT_ROOT"

cp "$FORMAL_DIR/lake-manifest.json" "$OUTPUT_ROOT/lake-manifest.json"
cp "$AXIOM_AUDIT" "$OUTPUT_ROOT/v330-axioms.txt"
printf '%s\n' "$COMMIT" > "$OUTPUT_ROOT/commit.txt"
printf '%s\n' "$QUALIFICATION_SYSTEM" > "$OUTPUT_ROOT/qualification-system.txt"
printf '%s\n' "$RUN_ID" > "$OUTPUT_ROOT/qualification-run-id.txt"
printf '%s\n' "$PROOF_CONTRACT_ID" > "$OUTPUT_ROOT/proof-contract-id.txt"
printf '%s\n' "$PROOF_CONTRACT_SHA256" > "$OUTPUT_ROOT/proof-contract-sha256.txt"

cat <<EOF

Qualification PASS.
Artifacts: $OUTPUT_ROOT
Proof contract: $PROOF_CONTRACT_ID@$PROOF_CONTRACT_SHA256
Important: this proves only the exact audited Lean scope recorded in the proof contract and artifact.
It does not establish production readiness or broaden any theorem hypothesis.
EOF
