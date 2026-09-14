# ADR-0003 — Run evidence is generated, never inferred from metadata

**Status:** Accepted

A module may advertise verification capabilities in `ProofStatus`, but those declarations are not run evidence. `RunCertificate.evidence` is populated only from `VerificationRecord` objects produced during that specific execution and marked PASS.

This prevents a module from becoming "verified" merely by declaring a badge. Failed checks remain in the run result and report for investigation.
