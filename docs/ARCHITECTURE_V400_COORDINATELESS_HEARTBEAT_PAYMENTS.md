# CACE v4.00 Runtime Architecture Contract

Status: runtime architecture implementation; **not a new formal-proof qualification**.

The qualified Lean proof boundary remains separate. Nothing in this runtime architecture can
promote numerical, symbolic, AI-generated, or paid output to FORMAL evidence.

## 1. Canvas integration

The React/Vite canvas is materialized from the exact content-addressed source archive with SHA-256
`1999b810a8c2a8d86013a8c311a9d66de36fe98ff292b6ddf43e156145478d99`.
The build refuses to extract if the archive hash or exact 14-file manifest differs.

## 2. Canonical coordinateless objects

`cace_studio.runtime.math_object.MathObject` owns semantic identity. Its canonical value is a sparse
multivector in an explicit Clifford signature. Representation envelopes (rotor, quaternion, matrix,
spinor) and display views are subordinate projections of that identity.

Display state is intentionally excluded from `MathObject.semantic_sha256()`. Cartesian, polar,
hex-axial/honeycomb, Eisenstein, projective, conformal, and 3-D canvas controls therefore cannot
change a mathematical object's semantic hash merely by changing the view.

## 3. Conway-inspired heartbeat control plane

The runtime is not Conway's literal Game of Life. Canvas nodes become autonomous scientific cells
and canvas dependency edges become typed heartbeat edges. Supported heartbeat policies are
PERIODIC, EVENT, CONDITIONAL, BATCH, and ON_DEMAND.

The heartbeat layer decides **when valid computation may run**. It does not decide whether an
unproved statement is proved. Evidence promotion remains outside the heartbeat scheduler.

## 4. Hash-bounded propagation

A cell output is content-addressed. When a recomputation produces the same output hash, downstream
EVENT propagation is suppressed. When it differs, the dependency closure becomes STALE. A maximum
propagation generation and DAG validation fail closed against uncontrolled cycles.

BLAKE3 is the paper-spec runtime backend. If BLAKE3 is requested but unavailable, CACE raises a
backend error instead of silently labeling a different digest as BLAKE3. SHA-256 remains available
for public/provenance identities and explicit test/development use.

## 5. Growth Sandbox, Watchdog, and Airlock

Untrusted growth candidates may execute only through `GrowthSandbox`, which requires Podman or
Docker and has no bare-host subprocess fallback. The default policy denies networking, drops Linux
capabilities, enables `no-new-privileges`, uses a read-only root, bounds CPU/memory/PIDs/time, and
provides only declared input/output mounts.

The Airlock hashes and validates the exact candidate output manifest. A human authorization must
bind to that exact manifest hash. Airlock passage does not raise evidence strength.

## 6. Server-authoritative entitlement leases

Compute access is controlled by a server-side SQLite ledger and short-lived HMAC-SHA256
`ExecutionLease` capabilities. Browser localStorage, wall-clock changes, pasted transaction IDs,
or client-reported elapsed time are not authority. Actual executor time is charged using a
monotonic clock.

Payments affect resource entitlement only. They have `evidence_effect = NONE`.

## 7. Monero stagenet payment verification

Stagenet is the default payment network. Each invoice obtains a unique subaddress from
`monero-wallet-rpc`. Unlock occurs only when wallet RPC observes the exact invoice amount on the
expected subaddress with the configured confirmation count and without a double-spend flag.
Receipts are idempotent and cannot mint duplicate entitlement grants.

The proprietary GUI's configured production wallet address is retained as the expected **mainnet
wallet identity**, but it is never used as a stagenet destination. Stagenet and mainnet addresses
are network-specific.

## 8. Mainnet gate

Mainnet is disabled unless all of the following hold:

1. `CACE_MONERO_ENABLE_MAINNET=1` is explicitly configured.
2. A real stagenet invoice was paid and wallet-RPC confirmed.
3. Re-processing that paid invoice proved idempotent.
4. The stagenet readiness attestation contains the real confirmed transaction ID.
5. The mainnet wallet RPC's primary address exactly matches CACE's configured production address.

Mock tests alone can never satisfy this live readiness gate.

## 9. License and SBOM gate

`third_party_policy.json` is the allow/obligation policy. `scripts/audit_third_party_licenses.py`
fails on undeclared or blocked dependencies. Release metadata includes SPDX and CycloneDX SBOMs
and `THIRD_PARTY_NOTICES.md`.

Components with distribution obligations (notably Qt/PySide6, TeX Live aggregates, and CUDA if
redistributed) remain explicit release-review items rather than being hidden by CACE's proprietary
license.

## 10. Autonomous growth gate

AI/VAE proposals remain `RESEARCH_CANDIDATE`. Autonomous mode is disabled by default and requires
all runtime prerequisites plus explicit `CACE_ENABLE_AUTONOMOUS_GROWTH=1`. Even in autonomous
proposal mode, a candidate cannot enter the primary experiment graph until the rigor gate passes
and a human authorizes the exact Airlock manifest.

This gate intentionally prevents an AI, payment event, heartbeat, hash, or successful simulation
from manufacturing FORMAL evidence.
