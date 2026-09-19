# CACE Source-Secrecy and Anti-Reverse-Engineering Architecture

Status: target security architecture plus release-gate requirements. This document does not claim that software running on customer-controlled hardware can be made impossible to reverse engineer.

## 1. Security objective

CACE should make theft of proprietary implementation materially harder while preserving inexpensive local computation.

The core rule is:

> **Do not rely on encryption or obfuscation to protect material that never needed to be shipped.**

Use four layers in order:

1. **Do not ship crown-jewel material.**
2. **Minimize the sensitive material that must execute locally.**
3. **Seal and harden the local sensitive components.**
4. **Continuously verify release artifacts and runtime boundaries.**

The highest-value CACE material—proprietary base-theorem source, private theorem bodies, proof-search methods, reusable formal strategies, customer-independent proof-generation machinery, signing keys, and enterprise proof infrastructure—should remain on controlled CACE systems whenever the offline product does not strictly need it.

## 2. Honest limitation

If executable logic must run on a CPU/GPU controlled by an adversarial user, that user can eventually observe machine instructions, memory, buffers, timings, and outputs with sufficient privilege and effort.

Therefore:

- local encryption protects data **at rest** and across boundaries;
- compilation/stripping/obfuscation raises reverse-engineering cost;
- process isolation reduces accidental leakage;
- buffer minimization reduces exposed information;
- none of these makes locally executed proprietary logic mathematically unrecoverable.

CACE should measure success as **risk reduction and economic deterrence**, not impossible secrecy.

## 3. Information classification

Every release-relevant component should have a disclosure class:

- `PUBLIC` — safe for public/customer distribution.
- `CUSTOMER_DELIVERABLE` — may be included only in the specified customer's package.
- `CACE_CONFIDENTIAL` — internal operational information; never distributed by default.
- `CACE_TRADE_SECRET` — crown-jewel implementation/theorem material; client release prohibited unless an explicit security/design exception is approved.

Classification should apply to:

- source modules;
- theorem source;
- generated proof artifacts;
- model weights;
- kernels;
- configuration;
- logs;
- source maps/debug information;
- test fixtures;
- customer data;
- internal documentation.

## 4. Gate architecture

A release is allowed only if all applicable gates pass.

### Gate 0 — Classification completeness

Fail if a release dependency is not classified when policy requires classification.

Evidence:

- classification manifest;
- source path;
- owner;
- allowed release surfaces.

### Gate 1 — Dependency-boundary gate

The customer-facing application may depend only on approved client interfaces.

Fail if browser/local client code imports, links, bundles, or dynamically loads a `CACE_TRADE_SECRET` source path.

The browser layer should contain presentation/UI logic only. Proprietary scientific algorithms must not be implemented directly in downloadable JavaScript/TypeScript bundles if secrecy matters.

### Gate 2 — Browser-bundle gate

Production browser bundle must reject:

- source maps;
- embedded original source;
- development-only comments containing implementation notes;
- private API schemas;
- internal filesystem paths;
- theorem-source excerpts;
- secrets/tokens;
- remote dynamic code loading.

Recommended production behavior:

- source maps disabled;
- minified production bundle;
- CSP restricts code to signed/local assets;
- no `eval`/dynamic remote module loader;
- only opaque IDs cross the browser boundary for protected internals.

Minification is not a secrecy boundary by itself.

### Gate 3 — Protected local-core gate

Python is easy to inspect. Crown-jewel algorithms should not be shipped as plain `.py` source if secrecy is important.

Preferred shape:

`thin Python orchestration -> narrow stable ABI -> compiled native protected core`

Hardening for protected native modules:

- ahead-of-time compilation;
- remove debug information from customer build;
- strip symbols where compatible with diagnostics;
- avoid embedding internal file paths and developer names;
- use link-time optimization where appropriate;
- keep exported symbols to a minimal stable ABI;
- use opaque identifiers rather than descriptive private theorem/function names at the customer boundary;
- separate crash-symbol files and keep them internally;
- sign/hash binaries.

Compilation/obfuscation is defense-in-depth, not proof against disassembly.

### Gate 4 — Encrypted-asset gate

Sensitive local data that does not need to be human-readable should be encrypted at rest using authenticated encryption.

Recommended inexpensive choices:

- AES-256-GCM when hardware AES acceleration is available;
- XChaCha20-Poly1305 where it provides a simpler/efficient portable path.

Rules:

- use a vetted crypto library; do not invent encryption;
- random nonce/IV per object as required by the chosen construction;
- authenticate ciphertext and associated metadata;
- derive per-artifact keys from a master key using a standard KDF such as HKDF;
- master keys are not hard-coded in binaries;
- unwrap/store local keys using OS keystore/TPM/keychain facilities where available;
- license/session tokens may authorize key unwrapping, but are not themselves raw encryption keys;
- rotate keys when compromise is suspected.

Encryption should be applied only where the confidentiality benefit justifies the small CPU cost; do not encrypt every transient numerical array merely for appearance.

## 5. CPU-memory exposure policy

The CPU must eventually see plaintext instructions/data that it executes.

Reduce exposure by:

- keep crown-jewel theorem source off the client entirely;
- keep decrypted sensitive assets only for the shortest useful lifetime;
- decrypt on demand rather than at startup;
- use bounded native buffers for sensitive material where practical;
- best-effort wipe native sensitive buffers after use;
- never put private source/theorem text into logs, exceptions, telemetry, crash reports, or UI error strings;
- do not serialize decrypted protected objects to temporary files;
- prohibit arbitrary debugger/introspection endpoints in production;
- keep internal symbol maps on CACE infrastructure only.

Python objects cannot guarantee secure zeroization; do not place long-lived secret material in Python strings when avoidable.

## 6. GPU/CUDA exposure policy

GPU acceleration must not become a side channel for proprietary source.

The GPU interface should receive only what the kernel needs, ideally:

- numerical tensors/arrays;
- indices;
- dimensions;
- public coefficients;
- opaque operation IDs.

Do not send to GPU memory:

- theorem source;
- proof scripts;
- source-code strings;
- account/license secrets;
- signing keys;
- proprietary natural-language design notes;
- unnecessary model metadata.

For proprietary GPU kernels that must ship locally:

- prefer precompiled device binaries rather than source at runtime;
- omit debug/line information in customer builds;
- avoid embedding PTX/source fallback when the portability tradeoff is acceptable;
- keep kernel names/export metadata minimal;
- strip unnecessary symbols/metadata;
- package signed/hash-verified kernels.

A user with administrator/device-debug access can still inspect GPU binaries and buffers. The strongest protection for a crown-jewel GPU algorithm is not to ship it.

## 7. CPU/GPU buffer-schema gate

Every protected accelerator call should have a small schema declaring:

- operation ID;
- input buffer types/shapes;
- output buffer types/shapes;
- whether contents are public/customer data/confidential;
- maximum sizes;
- allowed backend;
- deterministic/nondeterministic behavior.

The runtime should reject unexpected buffers or metadata.

This prevents a compromised UI/plugin/collaboration broker from using the accelerator path as a general-purpose data-exfiltration interface.

## 8. Release-secrecy gate

Before any customer build is signed/published, inspect the final artifact—not just the source tree.

Fail if the artifact contains forbidden material such as:

- `formal/` proof-development source unless explicitly approved for that release;
- private proof roadmaps/failure ledgers;
- `.github/`, `ci/`, internal runner scripts, or operational tooling not intended for customers;
- tests/fixtures exposing private internals;
- source maps;
- PDB/dSYM/DWARF/debug files;
- private symbol tables/maps;
- `CACE_TRADE_SECRET` markers;
- developer filesystem paths;
- secrets/private keys/tokens;
- private customer data;
- unapproved plain source for protected-core modules.

Produce:

- exact source commit;
- release policy version/hash;
- artifact file list;
- rejected-entry report;
- binary/text marker scan;
- artifact SHA-256;
- PASS/FAIL result;
- signed release manifest where enabled.

## 9. Runtime-integrity gate

At startup:

- verify protected binary/asset hashes or signatures;
- verify signed entitlement;
- verify configuration policy version;
- fail closed for protected features when integrity verification fails;
- do not silently load replacement libraries from writable/search-path directories.

Use fixed/controlled library search paths and avoid DLL/shared-library preloading/hijacking risks.

Integrity verification protects against accidental/tampered binaries but cannot prevent a determined local administrator from patching all checks; server-side proof/payment authority must never trust a locally reported integrity PASS without independent verification.

## 10. Collaboration/import isolation

The collaboration broker remains a typed operation relay, not a file/code import channel.

Remote collaborators cannot send:

- executables;
- plugins;
- Python/JS/Lean;
- GPU kernels;
- native libraries;
- encrypted opaque blobs that the core will execute after decryption.

Canvas messages reference approved operation IDs/modules already installed in the signed local release.

## 11. Enterprise proof isolation

Enterprise proof work uses the private theorem corpus only inside controlled CACE proof infrastructure.

Customer systems receive:

- customer-specific theorem statement;
- customer-specific derivation/report;
- agreed formal artifacts/certificates;
- opaque stable internal certificate IDs;
- qualification/provenance manifest.

They do not receive reusable base-theorem source or proof-search machinery.

## 12. Cheap-encryption performance policy

Security must not defeat CACE's low-cost computation goals.

Use encryption at boundaries and at rest, not indiscriminately inside hot numerical loops.

Recommended policy:

- encrypt protected assets on disk;
- decrypt once into bounded memory for the active operation;
- numerical CPU/GPU buffers stay ordinary numeric memory unless the threat model specifically requires confidential-computing hardware;
- hash large immutable assets instead of repeatedly encrypting/decrypting them when confidentiality is not needed;
- benchmark crypto overhead and record it independently from scientific compute;
- prefer hardware-accelerated AES-GCM where it is materially cheaper; otherwise use a well-supported ChaCha/XChaCha AEAD implementation.

## 13. Build hardening

Release builds should be separate from developer builds.

Developer build may contain:

- symbols;
- source maps;
- assertions;
- diagnostics.

Customer release must have a dedicated hardening profile:

- optimization enabled;
- source maps disabled;
- debug symbols split/removed from distributed binaries;
- internal paths normalized/removed;
- no test/dev dependencies;
- no private CI scripts;
- no private theorem corpus;
- signed/hash-locked assets;
- package allowlist, not a broad repository copy.

## 14. Reverse-engineering regression sweep

Treat every leakage defect like a bug-flush class.

When leakage is found:

1. reproduce extraction;
2. identify leakage class;
3. remove root cause;
4. sweep every release artifact for siblings;
5. add a permanent scanner rule/test;
6. rebuild final customer artifact;
7. rerun secrecy gate;
8. record incident/remediation.

Examples of permanent rules:

- source map found -> ban `*.map` in client artifacts;
- internal path found -> add path-pattern scanner;
- protected `.py` found -> classify and ban that path from customer package;
- theorem text found in GPU metadata -> add buffer/binary string test;
- private symbol found -> add symbol allowlist.

## 15. Adversarial release testing

Before production release, test the final artifact as an attacker would:

- unzip/extract wheel/installer/archive;
- enumerate strings;
- inspect exported symbols;
- inspect embedded resources;
- inspect browser bundle and DevTools;
- search for source-map references;
- search for local developer/runner paths;
- inspect GPU binary metadata;
- capture normal accelerator buffers and confirm only intended numeric data appears;
- verify collaboration messages cannot request raw protected files;
- verify crash/error paths do not dump proprietary source;
- verify customer export cannot traverse private paths.

The goal is to continuously raise the cost of extraction and catch accidental leakage.

## 16. Confidential-computing future option

For customers whose hardware/platform supports it, future Enterprise deployments may optionally use confidential-computing features such as hardware-backed isolated VMs/enclaves.

This can reduce host/operator exposure for selected workloads, but:

- hardware support varies;
- GPU confidential computing is platform-specific;
- it adds operational cost;
- it should remain an optional high-assurance tier rather than a dependency for ordinary CACE performance.

## 17. What not to do

Do not:

- invent custom encryption;
- embed one universal decryption key in the executable;
- claim minification prevents reverse engineering;
- put crown-jewel logic in browser JavaScript and rely on obfuscation;
- send private theorem source to GPU memory;
- ship debug symbols/source maps beside release binaries;
- trust locally reported anti-tamper status as proof;
- make scientific correctness depend on obfuscation;
- encrypt hot numeric loops with no confidentiality benefit;
- expose source/decryption through support, crash, or collaboration channels.

## 18. Assurance separation

Source secrecy is its own assurance dimension.

A release may be:

- mathematically qualified but secrecy-unsafe;
- secrecy-hardened but mathematically unqualified;
- both;
- neither.

CACE must gate and report these independently.
