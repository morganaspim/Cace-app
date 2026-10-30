# M.E.R.L.I.N. v24 — Host-Owned Snapshot Capability Gate

**Status:** Review branch engineering prototype; not deployed; not OS sandbox; not formal evidence.

## Implemented source
- cace_studio/ai/host_snapshot_authority.py: privileged host constructor creates source-scoped session rights. Only host code may issue a random 256-bit one-shot query token to an approved fixed select/count/group_count request.
- Session grants include operations, projected fields, filter fields and row limits; each token binds to exact serialized query and SHA-256 snapshot identity. Clock uses monotonic time; token TTL <=300s; session revocation and pending token quota enforced.
- cace_studio/ai/snapshot_broker.py: snapshot_sha256(source) and explicit null/missing equality filter distinction.
- tests/test_host_snapshot_authority_v24.py: 17 adversarial tests for denial, expiry, replay, cross-session, mutation, source identity, quota and no proof promotion.
- Scoped PR CI includes this test file alongside investigation, previous snapshot, classical-frame and pre-PR checks.

## Critical trust boundary
The host MUST authenticate the principal/session and supply the dataset grants, sources and clock from a trusted service. Never expose the issuer object or its issuance method to a model or execute untrusted Python in the same interpreter. The `EngineeringSpec.permissions` strings are a planner hint only. Tokens are bearer references; do not log or transmit them to untrusted prompt/model contexts. The provided `authorized_tool_for_snapshot` is an adapter for host-registered use only.

The broker's in-memory Python data and handler callable are NOT an isolation sandbox. Operation limits, single-use requests and group suppression do NOT imply differential privacy. Arbitrarily repeated host-approved aggregate queries can reveal individual data. Do not permit unrestricted authorization or arbitrary grouping over sensitive records; production needs dedicated broker process, authenticated service entrypoint, query policy, isolation, adversarial privacy tests and secret-independent logging.

Synthetic/source-kind labels are host declarations. SHA-256 verifies byte identity, NOT sensor truth, independent corroboration, mathematical proof or calibration. All outputs remain ADVISORY_SNAPSHOT_ONLY; proof_status=NOT_RUN, evidence_authority=False.

## Local TDD evidence
A RED test first failed because the module did not exist. After creating the host authority and fixing missing-vs-null, 48 scoped tests passed including 17 new tests and 31 earlier targeted investigator/broker tests. Twenty-four inherited v13 intent-agent tests passed separately. Source SHA-256 of locally tested files: host authority 1e64cf7d55c7bba2640185f0c59925b402c162bf7fbfed2e71c2f500ecf4a20f; host tests 0128ad08f8bb3e71a04b6df2a7dbf0dc15ca0232ca5b984aae8722278aff5481; broker 6e5d00188f94b9c50caff12419d0359b0d53478de5b6888c8b0391f4abaa5240.

## Next acceptance gates
1. Verify exact review-head GitHub CI tests and bug sweep, and compare uploaded code/source hashes with local tested artifacts.
2. Implement privileged service-side session authentication and process-isolated fixed-query broker. Test bypass, tampering and runtime resource limits; do not assume model string permission.
3. Return typed source observations to the Research Notebook, with explicit source class, lineage and measurement model and no proof promotion.
4. Compare the minimal baseline on genuinely held-out investigations, copied-source contradictions, false certainty and privacy leakage; separate capability from correctness.
5. Run FULL CACE native/Python regression, qualification-drift audit and pinned Lean qualification only through approved release pipeline; no automatic merge/deploy.

## Bug-clearing follow-up — malformed filter broadens request
In a second TDD cycle, `HostQuery.where=[]` was observed to be incorrectly normalized to an empty dict by `query.where or {}`, silently broadening access. A failing regression reproduced the defect; switching to an explicit None check made it pass. Another regression rejects non-hashable query fields/operations with `AccessDenied` rather than leaking an unexpected Python TypeError. These are input-boundary bug-family guards; local 48 focused tests and 24 inherited intent tests pass. Update tested-source SHAs by exact blob from this commit; earlier SHA values above are historical.
