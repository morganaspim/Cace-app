#!/usr/bin/env bash
# Portable CACE v3.30 formal qualification for Linux/WSL.
#
# This is the authoritative runner-independent equivalent of the v3.30 formal
# Actions workflow. It does not require a GitHub runner. It deliberately fails
# closed on a dirty tree, dependency drift, unfinished proof tokens, build
# failure, missing theorem axiom reports, or non-whitelisted axioms.
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
MATHLIB_COMMIT="520045ab14e26149ee970e2e617ca04b09bde5d6"
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

printf 'CACE portable qualification\ncommit=%s\nsystem=%s\nrun_id=%s\noutput=%s\n' \
  "$COMMIT" "$QUALIFICATION_SYSTEM" "$RUN_ID" "$OUTPUT_ROOT"

# The three governance tests are intentionally isolated from the full software
# regression. Full Python/native regression remains a separate release gate.
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install 'pytest>=8,<9'
PYTHONPATH="$ROOT" "$VENV/bin/python" -m pytest -q \
  tests/test_claim_promotion_v330.py \
  tests/test_claim_registry_v331.py \
  tests/test_qualification_drift_v331.py

# Isolated elan/Lean installation. Existing machine-wide elan state is ignored.
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
timeout 900 lake env lean --run .lake/packages/mathlib/Cache/Main.lean \
  get CACEFormal/V330AxiomAudit.lean
# The transfer cache is disposable after the imported oleans are extracted.
find "$XDG_CACHE_HOME" -mindepth 1 -depth -delete || true

cd "$ROOT"
PROOF_FILES=(
  formal/cace_formal/CACEFormal/SmoothBoxGreenAuto.lean
  formal/cace_formal/CACEFormal/RegularizationClosure.lean
  formal/cace_formal/CACEFormal/GraphRegularizationCriterion.lean
  formal/cace_formal/CACEFormal/RealGraphRegularizationCriterion.lean
  formal/cace_formal/CACEFormal/H1DomainBridge.lean
  formal/cace_formal/CACEFormal/H1BesselRieszReduction.lean
  formal/cace_formal/CACEFormal/DistributionalGraphRepresentatives.lean
  formal/cace_formal/CACEFormal/V330AxiomAudit.lean
)
if grep -nE '\bsorry\b|\badmit\b|OPEN OBLIGATION' "${PROOF_FILES[@]}"; then
  echo "Unclosed v3.30 proof obligation found." >&2
  exit 1
fi

cd "$FORMAL_DIR"
timeout 1200 lake build CACEFormal.V330AxiomAudit
lake env lean CACEFormal/V330AxiomAudit.lean 2>&1 | tee "$AXIOM_AUDIT"

cd "$ROOT"
"$VENV/bin/python" scripts/audit_v330_axioms.py "$AXIOM_AUDIT"
"$VENV/bin/python" scripts/write_v330_qualification_attestation.py \
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

cat <<EOF

Qualification PASS.
Artifacts: $OUTPUT_ROOT
Important: this proves only the exact audited Lean scope recorded in the attestation.
It does not establish production readiness or broaden any theorem hypothesis.
EOF
