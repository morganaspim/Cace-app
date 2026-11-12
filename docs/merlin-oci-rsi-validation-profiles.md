# Merlin RSI validation profiles for the OCI gateway

This branch extends the bounded OCI job gateway from PR #86. It preserves the
existing rsi_validation profile and adds two fixed profiles:
cace_rsi_bundle_contract and merlin_cpp_ledger_tests.

## Security and execution boundary

- Requests are JSON files under merlin/oci-requests/<UUID>.json.
- Each operation has an exact field allowlist. Unknown fields and operations fail closed.
- Repository, commit, and every source-file Git blob SHA are pinned.
- The gateway executes only the hard-coded profile for the selected operation.
  It does not accept shell commands, scripts, arbitrary paths, or package lists.
- The runner uses unique per-run temporary directories and refuses to overwrite
  an existing artifact directory.
- No packages or system libraries are installed. No OCI provisioning, restart,
  cache cleanup, or host configuration changes are performed.
- Every run uploads a bounded receipt and runner inventory.

## Fixed profiles

| Operation | What it checks | What it does not prove |
|---|---|---|
| rsi_validation | Pinned Python source compiles; frozen five-domain manifest has 25 cases; unit suite passes | It does not execute all 25 benchmark prompts against a production model |
| cace_rsi_bundle_contract | Merlin's canonical evidence-bundle digest matches the pinned CACE EvidenceBundle implementation | It does not sign or independently verify a real candidate artifact |
| merlin_cpp_ledger_tests | C++ generation/research ledger smoke tests compile and pass; Python-written episode is verified by C++ | It does not authorize candidate promotion |

The C++ test profile uses a small declaration-only SQLite ABI header in the
isolated test workspace because the OCI image has the SQLite runtime library
but no development header. It links to the preinstalled libsqlite3.so.0.
This shim is test infrastructure only, not a production SQLite SDK header.

## OCI verification results

All three final profiles were executed on cace-oci-a1 (ARM64, Oracle Linux
Server 9.8) against the exact Expert Robot source commit
a538bf074874403fe8a3a8ece53311763d585a0c.

| Profile | GitHub Actions run | Result |
|---|---:|---|
| merlin_cpp_ledger_tests | 43124266542 | Passed |
| cace_rsi_bundle_contract | 43124488674 | Matched |
| rsi_validation | 43124666656 | 15/15 tests |

### RSI validation

- Python 3.9.25; cryptography 36.0.1 already present on runner.
- 15 tests passed, 0 failed.
- The 25-case manifest covers mathematics, Lean, research, coding, and engineering.
- Manifest SHA-256: 543dbb105d6baf62dbfee54cdd8c7e483f2a9ab799e651dddda8066ce0f5a36f.
- The tests include authenticated Hermes failure ingestion, signed worker
  acknowledgements, idempotent dispatch, CACE trust-store digest checks,
  separate approval, Crossref/arXiv cache behavior, rate limits, and
  append-only ledger mutation rejection.

### CACE EvidenceBundle contract

- Pinned CACE source blobs:
  - graph.py: cffb146a6be9becc45f0c6789707766b7c8e4222
  - reproducibility.py: 8c6e7cfe7204ee557a112091a9d451e300e43210
  - evidence_ledger.py: 25104f432bb50339d980754a58cbc4a004f504ec
- Expected and actual bundle SHA-256:
  e9a3bbb6fdc91429a2b56efa158f0d8c5b5bb2460973ad248e3bb726c5915198.

### C++ ledger and cross-language verification

- GCC 11.5.0 compiled and ran both C++ smoke tests.
- Python AppendOnlyLedger wrote an episode that C++ ResearchEpisodeLedger
  independently verified.
- Verified episode root:
  698d66bd34fde44650268c53663096cf0295bfc1ffdb648dca85a6a3cb534792.
- No system package installation; approximately 449 MB remained free after
  the C++ profile.

## Artifact identities

| Run | Artifact ID | Artifact SHA-256 |
|---|---:|---|
| 43124266542 | 13902485891 | 89798e2727984242b7986ab15cca5bc096aa18fa0a6c8b2f08c741b1bbb0a59a |
| 43124488674 | 13901384198 | bd5c5cf36c591d286f4ee2e6e18f2ec815a551f4de14b52a02e44007c32cce22 |
| 43124666656 | 13902756602 | 4928f01f24eba90deace7e4c0eae57ebaeb93ba1bd7afa4670a733eea591834f |

The request files and failed diagnostic attempts are retained in this branch
as an audit trail. Corrected runs are identified above; no failed attempt is
represented as a passing qualification.

## Production limitations

- The CACE bundle operation is an identity comparison, not a CACE signature.
- Unit tests use ephemeral test keypairs; production trust anchors and the
  live Hermes worker transport still require reviewed deployment configuration.
- The 25-case manifest is frozen, but a full blind benchmark executor and
  independently implemented per-domain scoring remain future work.
- GEPA/Inspect remain disabled unless paired held-out measurements show a
  statistically credible gain.
- No candidate was promoted by these tests. A real candidate still needs a
  separate CACE-signed receipt, a passing held-out evaluation, and a distinct
  approval receipt.

