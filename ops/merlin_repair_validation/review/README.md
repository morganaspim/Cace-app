# Merlin native repair fixture package

This package defines one **unprivileged test-only operation** on the existing OCI runner. It is prepared for review; it does not publish, submit a request, install software, or change a running application.

The package addresses two measured production blockers: a CPython archive inspector incorrectly requiring explicit directory headers, and browser shutdown leaving its owned Unix socket behind. The original failed native evidence remains unchanged. Product fixes and installation/deployment are separate from this fixture operation.

## Exact scope

| Frozen suite | Required cases | Scope |
| --- | ---: | --- |
| Python static inspector | 35 | Synthetic archive/transport/process controls; no acquisition |
| Existing browser product contracts | 41 | Injected transport and fake renderer; no live browsing |
| Browser lifecycle | 13 | Real Unix sockets and signals in new private temporary directories; root admission/chown are test doubles |
| Browser lifecycle controls | 12 | Socket-free ownership/signal/process controls |
| Total executions | 101 | Every suite must have its exact count, with no skips, expected failures or unexpected successes |

These are fixture executions, including existing regressions. They are not 101 new product capabilities, native rendering, real-model qualification or production acceptance. The current local environment denies creating Unix sockets; the thirteen native lifecycle cases therefore remain unrun successfully here. This package does not attempt to bypass that restriction.

Only exact reviewed source snapshots are copied from private `Mannyspiro/expert-robot` work into private `morganaspim/Cace-app`, under `ops/merlin_repair_validation/`. Existing frozen acquisition, browser-inspection, service, provider and application definitions are untouched. No downloaded interpreter archive is included.

## Execution contract

`REQUEST_CONTRACT.json` fixes the repository, branch, operation, request fields, UID1000, Python3.9, runner labels and counts. The workflow uses the existing `merlin-dot-oci-operations` serialization group and accepts only a new one-file additive request commit, first attempt only. A definitions-only publication does not run it. The supplied package contains no dispatch request.

The coordinator retrieves exact-commit files from the private GitHub API, verifies byte lengths, SHA256 and Git blob identities, and records the workflow identity. Fixture children receive a clean environment without the GitHub credential, ambient proxy or user configuration. Private per-suite temporary directories have explicit mode0700; short `/tmp/merlin-rv-*` paths keep Unix socket names within the native address limit. Tests clean only their own temporary fixtures. Unexpected residue is preserved and makes validation fail.

Each suite has a maximum90-second deadline and8MiB output ceiling, inside a360-second fixture budget and10-minute job. The coordinator enables Linux child-subreaper behavior for its own process, requires pidfd support, and reaps its suite process plus newly adopted children with UID/parent/start-time checks and identity-bound signalling. Cleanup failure blocks success. It does not find processes by name, target preexisting services, or signal unrelated host processes. This is reviewed fixture orchestration, not a general-purpose sandbox.

The only network use in the operation definition is exact private GitHub source/request retrieval and Actions artifact upload. The pinned tests use synthetic/injected transports and inert local launchers; no browser engine, public source acquisition or model call is invoked. The coordinator is not claimed to establish kernel network isolation.

## Review and reproduction

`SOURCE_PINS.json` binds all executable source and the generated workflow. Regenerate locally with:

```bash
python3 build_workflow.py
python3 validate_package.py
```

The structural validator does not run browser fixtures or make a network request. It checks the embedded Python3.9 syntax, complete source pins, exact suite counts, fixed request behavior, no-skips handling and cleanup identity branches using explicit test doubles. This local surface does not expose its own procfs child list, so actual coordinator descendant cleanup remains unverified until OCI execution. Generated workflow output must be byte-identical on regeneration.

The native operation is complete only after its raw artifact is retrieved and every exact suite receipt, source identity and cleanup result is reviewed. A successful workflow state alone is insufficient.

## Preserved boundaries

No root escalation, service-manager operation, browser/provider/interpreter installation, existing production socket cleanup, browser acceptance replay, original archive-member execution, paid call, model call, merge or promotion is included. The operation does not authorize itself. Publishing this new source snapshot and executing the fixed test-only request are separate reviewable actions.
