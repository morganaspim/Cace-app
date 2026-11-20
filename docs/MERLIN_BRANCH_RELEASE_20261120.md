# Merlin additive library release - November 20, 2026

The user authorized push, merge and deploy. This branch prepares the exact scheduler repair from Expert Robot PR 183, source 5d5ecfbe2ed4bb29d7e5c0c86607e73780fd599f. It does not merge unrelated draft platform code or claim full production acceptance.

The current research runtime archive is preserved byte-for-byte at the file level. Only branch_research.py and its two focused test files are added. Unit, grants, seed data and private stores are not edited. No new remote tool is exposed. A deterministic manifest/package binds the additions separately from the canonical runtime base.

The existing installer archive verifier, root-owned service guards, upgrade lock, private socket probes and prior validation receipt verifier are reused by exact blob identity. The isolated branch workflow requires one additive fixed request per execution; deployment must reference a successful same-workflow validation receipt and unchanged live profile. Source pin mismatches, altered existing files, unexpected additions and prior attempts fail closed. Activation retains the old release; failures trigger checked rollback.

Local controller checks: 13 tests, including injected probe and post-rename failures, pass using fake service controls and isolated files. Local scheduler checks: 21 pass. These are not OCI or independent verification results; exact cloud evidence will be in operation artifacts. The workflow runs baseline plus exactly 21 new tests and all 13 controller checks before any activation.

Operations: validate; deploy with exact validation_run_id and validation_commit; inspect after activation. Always retain failures. Do not use Avrea before December 1, 2026. Do not weaken branch protection or forge status checks. The merged source and live release must be checked separately. External effects remain at-least-once without additional idempotency; callbacks are trusted in-process code. CACE verification, scientific qualification, remote execution and full platform integration remain outside this release.
