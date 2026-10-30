# M.E.R.L.I.N. v25 — Host-Authenticated Research Worker

**Status:** Review branch engineering prototype. NOT live, merged, formally qualified, production-authenticated, OS-sandboxed or privacy-certified.

## Implemented

- cace_studio/ai/process_snapshot_service.py starts a separate Python process with a fixed JSON IPC protocol, host-approved session grants and source-owned in-memory scalar snapshots.
- Privileged host callback resolves supplied credentials separately on token issuance and consumption. Real CACE authentication has NOT been connected; tests use intentionally fake credentials.
- Every issue, consume, revoke and stop command requires HMAC-SHA256 over its canonical content using a private parent-worker secret. Raw IPC session spoofing is denied.
- One-shot token, TTL, access rights and record provenance remain controlled by v24 HostSnapshotAuthority and SnapshotBroker.
- Optional immutable per-session owner filters and finite per-session aggregate-query issue budget operate inside the worker. This does NOT provide formal differential privacy.
- Typed scalar keys survive JSON serialization for grouped observations. All outputs retain ADVISORY_SNAPSHOT_ONLY, evidence_authority=False, proof_status=NOT_RUN.

## Local test-driven development receipts

- Baseline v24 scoped suite: 48 tests passed.
- RED: missing process_snapshot_service import; GREEN: 14 initial process-worker tests passed.
- RED: missing owner-row and aggregate budgets; GREEN: 18 process tests passed.
- RED: direct _rpc issue could impersonate approved session without credential; GREEN: all 19 process tests passed after signing every privileged command.
- Final selected pytest: 67 passed across investigation, snapshot, host authority and process service.
- Source Git blob: 49b00cf677e77e91710a0fd2d8b21e2147f32876; test Git blob: 097998d7dce4e18e5f9407f7502680976f38506f.
- Offline M.E.R.L.I.N. council experiment: six roles, twelve simulated messages, six proposed hypotheses, all advisory and not evidence of autonomous model learning.

## Threat and acceptance boundaries

Separate Python processes are not a privilege sandbox: both inherit ordinary host OS permissions without seccomp, explicit network denial, dedicated UID, CPU/memory enforcement or verified parent memory removal.
An attacker with arbitrary Python execution and access to the privileged façade may read the HMAC key; this scheme protects only a narrow IPC boundary, not a compromised host process. Never expose the façade as a model tool.
Host callback cannot be replaced by a model-supplied session string. Dynamic tenant/resource rights and logout require integration with CACE's real authenticated account service.
Repeated permitted counts can reveal small-group information despite the aggregate issue cap. Deny sensitive aggregation by default and use independent privacy review.
Source ID and SHA prove declared byte identity only; a synthetic sample is not a physical measurement, and no AI result may create scientific/formal PASS.

## Next ranked gates

1. Exact final-head CACE Collaboration Coordination Validation with new test file, plus canonical bug sweep.
2. Complete CACE full Python/native regression and qualification-drift audit, independently of Lean pinned exact formal qualification.
3. Replace test callback with CACE real user/session authentication and tenant-owned immutable row/field permission resolution.
4. Run worker in OS-enforced low-privilege no-egress environment with untrusted-client penetration tests and source secrecy inspection.
5. Integrate typed provenance-aware source observations into canonical Research Notebook and M.E.R.L.I.N. council, with revision and source-family independence.
6. Benchmark council+Ideonomy/fuzzy reasoning against baseline, then math kernel, classical/quantum frames and device-local iPhone agent on measured hardware.

Security reference: NIST SP 1800-35 (2025) and OWASP API Security Top 10 2023, particularly object/property-level authorization.
