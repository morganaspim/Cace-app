# Merlin native retained-source research handoff

## Purpose and release state

This fixed coordinator connects an accepted saved browser episode to the published
Merlin research protocol. It resolves the original canonical ArtifactRefs,
measures retained byte integrity and capture coverage, and records a typed plan,
measurement and review in the **same `merlin-browser-research` project**. The final
receipt is read again in a separate Python process. These records can be consumed
by the existing recurring research task as evidence for a later domain plan.

The source-preparation checkpoint has 24 local coordinator controls and 13 local
workflow-generator controls. The published product has its separate 23-test gate.
Local tests and Python 3.9 syntax parsing do not establish native execution. At
this checkpoint native browser acceptance remains pending; no installed pin file
or runnable handoff workflow has been generated.

The coordinator does not acquire sources, run Chromium, contact a provider, call
a model, install software, restart a service or execute a domain experiment. It
does not qualify a hypothesis or promote a change. `domain_execution` remains
`not_run`; source integrity and capture coverage are the only new measured claims.

## Source and data bindings

The product source comes from `Mannyspiro/expert-robot` commit
`bc8a9b64638323791b761d26d1b7093203405626`:

| Source | SHA-256 |
| --- | --- |
| `python/merlin/browser_research_handoff.py` | `d2bcfd849c40412479861f855378d40acfeb7f627ab3277a468b672c7c94c960` |
| `tests/test_browser_research_handoff.py` | `f49202a7e70a90cddf8bced9118aabc671b89b6c653fb96fe2bccf3ae32981b7` |
| `config/merlin/research-program.json` | `f8f312e4ff968028385a636dcc15b1eec93659a4973b0a7c900d36c4cd27c49c` |

`ops/merlin_research/handoff_product_pins.json` binds these files and the seven
already installed private dependency files. The dependency release is
`ef5c8d65782e8b746d3002d1f407596b4d9c765059ec46271d446d4e9bc63f82`, with manifest
`c0b810e801e9a9c5dbed428bd3c5733b53ed0f11a515db536a25f17972ad0a9d`.
The coordinator reads that exact existing release and verifies every dependency
before importing it. It does not replace either the browser or private runtime.

The compact `merlin/browser-handoff-source.zip` transports only the exact new
module, its tests, the existing program and their manifest. It contains no private
dependency copy. This is a deployment transport for reviewed repository source,
not an independently maintained second source tree.

The only registry is `/var/lib/merlin-public-browser/registry`; the original
private state at `/var/lib/merlin-dot-private/state` is not an input or write
target. HTTP and query URLs remain exact in the captured records. There is no
rewrite to satisfy the narrower legacy bridge URL contract.

## Request contract

An authorized repository operation adds exactly one file at
`merlin/browser-handoff-requests/<canonical-UUID>.json` on
`morganaspim/Cace-app` branch `merlin/browser-operations-20261121`. The generated
workflow has `contents: read` and accepts only the following exact envelope:

| Field | Contract |
| --- | --- |
| `schema` | `merlin-browser-handoff-operation-request/1` |
| `request_id` | Canonical lowercase UUID equal to the request filename |
| `created_at` | UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form |
| `operation` | `submit` or `status` |
| `arguments` | Exact operation-specific fields below |

A `submit` has `episode_id`, `publication_ref` and
`launch_receipt_sha256`. The publication must be version one at
`browser/episodes/<episode_id>/publication.json` in the fixed browser project.
The outer request UUID becomes the product handoff UUID. No URL, browser action,
shell command, registry path, source pin, budget or provider field is accepted.

A `status` has only `handoff_request_id`, naming the original submit UUID. Its
outer request uses a new UUID. The original admitted request and actual saved
source are rechecked, and the product receives read-only authorization.

The caller can use a source publication retained by bootstrap acceptance or the
separate fixed browser episode route. A successful launch receipt, stopped broker
and renderer, unmounted scratch, exact root-owned episode manifest and canonical
publication must all agree. Fixture-only output and failed episodes are rejected.

## Execution and interruption behavior

The workflow retrieves its exact pinned controller/helper/tests and source bundle
through the GitHub API. It verifies SHA-256, Git object identities and Python 3.9
syntax before starting the fixed controller. The runner executes the 24
coordinator controls without privilege. The native controller then performs these
steps:

1. Verify actual installed browser pins, its active supervisor, the seven private
   dependency bytes and the live controller resource envelope.
2. Copy the three exact public source files into immutable root-owned staging.
   Run the 23 published handoff tests as UID 1000 in a fresh process.
3. Recheck the private sources and import the fixed handoff module by hash. Admit
   the accepted stopped browser output and its exact same-project publication.
4. Persist a durable outer intent. A first submit may call the published product's
   `submit` once; an existing intent changes every subsequent submission to
   `status`. An incomplete request directory is retained for reconciliation.
5. Resolve and measure retained bytes through the existing canonical registry and
   research APIs. Read a completed result in a separate root Python process with
   read-only authorization, and compare the exact result and ArtifactRef.
6. Verify browser configuration/service identity and private source pins again.
   Preserve the operation receipt, original admitted source bytes, native test
   output, fresh-process readback and canonical plan/measurement/review bytes.

The fixed transient unit has a 150-second wall deadline, a 15-second stop grace,
512 MiB memory ceiling, no swap, 50% CPU quota and 64 tasks. It has a private
network namespace, `NoNewPrivileges=yes` and only `AF_UNIX` sockets. The root
Python process has an earlier 130-second alarm. Evidence admission reserves at
least 1 GiB plus 84 MiB of free disk. Existing records are never deleted to make
space. Journal transport avoids forwarding caller file descriptors through
systemd.

The outer intent/outcome ledger is under
`/var/lib/merlin-public-browser/handoff-operations/requests/<request-UUID>`.
Product records remain in the canonical project after process or service restart.
An interrupted or contradictory retained result is reported for reconciliation;
there is no implicit remeasurement or browser retry. The separate status process
rehashes retained records before it can return completion.

Root-owned evidence is copied through an anchored directory descriptor into the
runner's bounded artifact directory. Symlink replacement and parent renaming
fail delivery. The exact root copy remains retained. The Actions artifact uses
30-day retention; a release evidence append must preserve the accepted native
receipt and raw source/test/readback data in the repository for longer retention.

## Preparing and generating the workflow

Source transport can be prepared before installation acceptance:

```sh
python build_handoff_workflow.py \
  --prepare-only \
  --product-source /path/to/exact-published-product \
  --program /path/to/exact-research-program.json
```

This writes the deterministic source ZIP and its pin, and emits no YAML. For a
runnable workflow, the coordinating release process supplies the actual accepted
installation pin file, exact primary artifact ZIP, and saved GitHub run/jobs/
artifact responses:

```sh
python build_handoff_workflow.py \
  --product-source /path/to/exact-published-product \
  --program /path/to/exact-research-program.json \
  --installed-pins /path/to/accepted-installed-pins.json \
  --acceptance-artifact /path/to/accepted-native-artifact.zip \
  --acceptance-api /path/to/accepted-native-api-evidence.json
```

The gate requires a completed successful native run, complete successful jobs and
one exact nonexpired artifact. It checks native sandboxed rendering, all three
UID 982 public-source cases, the denied UID 1000 peer, unchanged readback after
supervisor restart and unchanged private/model snapshots. It hashes the actual
receipt-bound runtime ZIP and its manifest, then derives the producer's canonical
host configuration from the exact release, account and executable fields. Altered
valid-shaped host or manifest digests are rejected before YAML generation.

Only after those checks does it write
`.github/workflows/merlin-browser-handoff.yml` and
`workflow-publication-manifest.json`. It performs no remote write or dispatch.
The saved API responses are supplied by the coordinating release process; this
generator does not independently fetch their authenticity. The coordinator
rechecks all actual host pins immediately before use.

## Focused local verification

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=ops/merlin_research \
  python -m unittest test_handoff_request test_build_handoff_workflow -v
```

The 37 local tests cover typed requests, exact project/reference identity,
stopped-source admission, replay control, native-test and child-process result
validation, absolute cleanup after the direct child exits, anchored publication,
and actual acceptance-gate failures. Generator fixtures are explicitly synthetic
and never write dispatchable YAML. The generated Python wrapper and actual
composed root argument are parsed in memory as Python 3.9 and checked against the
platform argument-size bound. Actual Oracle Linux ARM64 execution, the native
23-test result and the separate-process retained readback remain release checks,
not conclusions of local tests.
