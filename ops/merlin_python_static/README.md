# Fixed CPython acquisition and static inspection — review package

**Prepared locally for review. No archive has been downloaded, no native run has
occurred, and this package cannot install or activate Python.** The existing
seven-file interpreter proposal remains unchanged. This package makes only its
next acquisition/static-inspection step executable and reviewable.

## Exact proposed operation

The new workflow accepts one new first-attempt request for
`inspect-cpython-3.11.18-20261110-aarch64`. It uses the existing UID1000
GNU/Linux aarch64 runner and its installed Python 3.9, under the shared
`merlin-dot-oci-operations` concurrency group. Its trigger is exclusively
`merlin/python-static-inspection-requests/**` on
`merlin/browser-operations-20261121` in private `morganaspim/Cace-app`.
The trigger commit must add exactly one correctly named request and change
nothing else. It does not trigger the source, browser-acceptance or model routes.

The workflow pins the controller and its focused tests by bytes, SHA256 and Git
blob. After the focused controls pass, it embeds the verified controller bytes
in an isolated unprivileged Python invocation. It does not run git or check out
ambient repository scripts. Its GitHub source-fetch credential is excluded from
the controller environment and is never sent to the archive server.

| Publisher identity | Fixed expected value |
| --- | --- |
| Repository | `astral-sh/python-build-standalone` |
| Release / asset IDs | `441136779` / `733710616` |
| Release / CPython version | `20261110` / `3.11.18` |
| Target / flavor | `aarch64-unknown-linux-gnu` / `install_only` |
| Archive bytes | **49,469,868**, publisher-reported; not locally measured |
| Archive SHA256 | `623a370be4489d8c35c7a274be02f3007a030618cda29025780beb416c6c8861` |
| Build-source commit | `9244801782b78e4c4afc5c82a4524aa2101d3298` |

The immutable publisher metadata is already published in
[the product evidence record](https://github.com/Mannyspiro/expert-robot/blob/cb09f176f6d3574d444590d693d8681d8f05a56a/docs/evidence/merlin-native-acceptance-20261121/interpreter-proposal-20261121/PUBLISHER_ASSET_METADATA.json).
It is a reference-only dependency in this package's manifest, not a new payload
or newly measured archive. The fixed public download URL is in the controller
and request contract. The earlier bounded metadata lookup established
no available supported download route through the current connected Actions
artifact tool. This proposed future native job has **not** established that its
direct HTTPS transfer succeeds; failure remains an expected, recorded outcome.

## Bounded transfer

The operation makes one logical acquisition with **zero retries**. It starts at
the exact pinned GitHub release URL. At most two redirects may lead only to
`https://release-assets.githubusercontent.com`; credentials, alternate ports,
fragments, control characters and other origins are rejected. The client uses
direct verified HTTPS, with no proxy environment, cookies or authentication.
Only hop origins and HTTP statuses are recorded. Signed redirect URLs, query
strings, response bodies and exception messages are excluded from receipts and
logs.

The final response must be HTTP 200 with one exact Content-Length equal to the
publisher's expected byte count. Transfer-Encoding, transformed content,
duplicate framing headers, truncated bodies, excess bytes and digest mismatches
fail. The compressed ceiling is 64 MiB in addition to the exact size/hash checks.
The acquisition worker has a **180-second absolute parent-enforced deadline**,
including DNS, TLS and slow body reads, followed by at most four seconds of
termination grace. A partial or missing worker receipt remains unconfirmed.

## Static inspection and its limits

Only verified archive bytes reach inspection. The controller copies them into
an immutable process-local snapshot, then verifies gzip integrity while writing
at most **512 MiB** to one private, non-executable tar-data file. Tar metadata is
parsed only after this decompression bound has been enforced. Archive files are
read as data; no member is extracted into a filesystem runtime tree.

The inspection records member names, kinds, sizes, modes and content hashes;
exact bounded candidate license/notice bytes in base64; and bounded ELF header, loader,
DT_NEEDED, RPATH and RUNPATH observations. It rejects unsafe or duplicate paths,
unknown/special files, sparse members, setuid/setgid bits, hardlinks, missing or
non-directory ancestors, escaping/dangling/cyclic symlinks, oversized members,
missing tar terminators and nonzero trailing tar content. The expected
`python/bin/python3.11` ELF and GNU aarch64 loader must be observed. An unexpected
layout stops this definition; it does not authorize a parser or layout fallback.

Inspection ceilings are **20,000 members**, **64 MiB per member**, **256 KiB per
captured notice**, and **4 MiB of notice bytes total**. Each of the three JSONL
inventories is capped at 32 MiB; receipt files are bounded. The static worker has
a **120-second absolute deadline**, four seconds of termination grace, and a
1 GiB address-space limit. Workers stay in the workflow child's process group;
the outer 340-second controller deadline can terminate the complete group.

Candidate notices are selected by fixed license/notice/copyright filenames and
license-directory names. Discovery completeness is unverified; the full member
inventory and original archive remain available for subsequent notice review.
ELF observations cover ordinary ELF members, not recursive inspection of static
libraries or nested archives.

The parser is a bounded static observer. It does not resolve ELF dependencies on
the host, execute version probes, establish ABI compatibility, grant license
clearance, or qualify an installer. License and dependency review remain open
even if all structural checks pass. These conservative limits are policy
ceilings; actual archive contents and compatibility remain unmeasured until the
future approved run returns evidence.

## Effects and retained evidence

The operation writes only a newly created private runner evidence directory.
Archive and decompressed tar files use mode 0600, with no executable permission.
The workflow preserves the pinned source, fixture log, request/execution
identities, archive/data inventories and all available partial/failure evidence.
The original archive plus the decompressed tar may account for most of the
artifact size; their maxima are 64 MiB and 512 MiB respectively. No fetched data
is imported or executed. No sudo, root helper, package manager, interpreter
installation, symlink activation, cleanup, service change, provider action,
private-corpus read, browser acquisition or model request is present.

Every complete or failed receipt retains **`installation_allowed: false`**.
Static completion means the specified observations were produced. It does not
satisfy the native source gate: the previously blocked **111 product cases
remain unexecuted**, and the model gate remains held. The new focused controls
are separate diagnostic controls, not additions to product acceptance counts.

Before any future installation request, review actual archive/notice/link/ELF
identities and prepare a separate fixed root file-operation controller and
rollback. That future controller must install from immutable verified bytes,
preserve system Python and the provider, and create only an absent versioned
prefix/entrypoint. This package supplies no such installer or authority.

## Review and publication boundary

`publication-manifest.json` identifies the exact proposed definition files and
modes. The request contract is documentation, not a live request. Local fixtures
use synthetic archive/HTTP data and make no real download. Their logs and an
independent review are retained under `evidence/`.

The final **23 focused local controls passed**, with zero failures, errors or
skips, using the exact generated workflow discovery code and `/usr/bin/python3
-I -B` flags. This preparation environment was Linux x86_64 with Python 3.13.5;
the future native Python 3.9 run remains unperformed. The modules and generated
program also receive a Python 3.9 grammar check. The final proof is
`evidence/fixture-controls-final.json`; the earlier 22-control result is retained
as historical evidence. The two original-accepts/corrected-rejects archive
regressions overlap the suite and do not add test cases.

The optional `build_workflow.py` is a local review/reproduction aid. It consumes
the already published browser workflow baseline at its pinned SHA256 to reuse
only the bounded unprivileged child-runner logic. That baseline is declared as
a reference-only dependency; it is not copied into the new review payload and
is never invoked by the proposed workflow. The generated definition is complete
and does not run the builder during native execution.

Publishing the prepared definitions and one new fixed request, running this
unprivileged acquisition/inspection on the named private operations repository,
and returning its scoped receipts to private `Mannyspiro/expert-robot` require the
new explicit scope decision. No publication or dispatch has been attempted for
this package. Installation, cleanup and service changes remain excluded.
