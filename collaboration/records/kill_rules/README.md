# Kill-rule registry

Pre-registered falsifiers for claims made in this repo.

A claim enters this lane only with one named falsifier: the single observable
statement that, if true, makes the claim false. If that sentence cannot be
written, the claim is not falsifiable and does not get registered.

This is coordination evidence, not proof evidence. It cannot raise a claim's
evidence class, and registering a rule is not verification.

## Files

- `*.json` here are validated by `ci/kill_rule_check.py` on every push to a
  `sui/**` branch, on the `[self-hosted, cace, oci, aarch64]` runner.
- Shape: `collaboration/schema/cace-kill-rule.schema.json`.
- A rule whose bands include `SURVIVES_BOUNDED` must carry a `cost_stack`.
  A rule that can only die or survive, with no stated cost stack, is incomplete.

## What the check enforces

- every rule has a non-placeholder `falsifier`
- `head_sha` is exact lowercase 40-hex (no cross-head reuse)
- observable, test, and verdict bands are well formed
- `SURVIVES_BOUNDED` implies a declared cost stack
- `EXECUTED`/`CLOSED` rules carry an outcome and evidence class

The job is read-only: no writes, no secrets, no outbound network from the
check itself. It exits non-zero on any violation.

## Status

Empty. No rule is registered until a claim in this repo has a falsifier worth
pre-registering. The check passes vacuously until then, which is honest.
