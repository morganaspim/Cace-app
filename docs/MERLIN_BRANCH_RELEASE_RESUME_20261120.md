# Reconciled additive release resume

Parent deployment run 44825544345 (3114e4fd8c1c0876a3e715f14da7abcd8b253186) returned rollback_failed after both post-restart tool probes failed. The root result SHA-256 is e87341332fd0f787c164e141e6dc010fb5428e4bc99ac5e51dde3840e6183085. Its command-only truncated errors do not establish the original exception cause.

Subsequent read-only diagnostic run 44825819133 confirms current points to the old efe57bada5cd86f45118cac0036faf497f9aa60972508e036aed09f7b8cf04db release, active/running, exact original config/unit hashes, no private database reads. Journal timing is consistent with a socket-readiness race, but not conclusive. The operation must test real authenticated health before switching anything again.

This narrow repair waits only for missing/refused startup sockets within ten seconds. Permission, identity, health contract and actual tool errors fail without retries. Full original tool and write-denial probes remain unchanged. Root-owned prior failure evidence, both release manifests, original configuration and fixed package identity are rechecked under the existing lock. One append-only resume attempt is permitted; original records/releases are never removed or overwritten. Fresh exact-workflow validation is required.

The runtime package remains d4fa47482b94c8f086b87d2c2e532a64a5874124b31283d834bc9be8350c3365. No application code, grants, unit, seed or private state is changed by this repair. Source PR 183 is merged as 89d04145d4afd0fa8cf634e989f73c80b6f74c8e; compare to tested source returns no file changes.

Local controls: 13 original plus 14 new tests pass (27 total), including bounded readiness, refusal to retry permission/health failures, preservation of stderr, pre-mutation health failure, prior-attempt mismatch, unexpected package rejection, post-switch failure and successful rollback using isolated fake service fixtures. These are not live fault injection. Exact OCI validation, successful resume and later readback remain required before a deployment success claim.
