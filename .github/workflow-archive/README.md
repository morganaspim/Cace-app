# Archived GitHub Actions workflows

These workflow definitions are preserved byte-for-byte from their last active versions but are intentionally stored outside `.github/workflows/`, so GitHub Actions does not register or dispatch them.

Reason: CACE uses a single serialized Actions lane. Historical formal gates, OCI provisioning/cutover utilities, probes, diagnostics, and regression workflows created independent automatic/manual dispatch surfaces that could race with canonical qualification or collaboration validation.

Active workflows are intentionally limited to:

- `.github/workflows/cace-collaboration-validation.yml`
- `.github/workflows/cace-formal-v336-theorem-metadata.yml`

Restoring an archived workflow to `.github/workflows/` requires a serialization-policy review first. Its triggers and concurrency policy must be reconciled with the active CACE lane before it is executable again.

Archiving is an engineering coordination change only. It does not alter, strengthen, weaken, or replace any previously produced Lean/kernel proof evidence or exact-head qualification artifact.
