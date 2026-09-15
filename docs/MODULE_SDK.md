# CACE Module and Plugin SDK

Status: development SDK contract for the v3.35 line. Plugin metadata and tests do not establish mathematical evidence for the modules a plugin registers.

## Core module contract

Scientific capabilities should subclass `cace_studio.core.module.Module` and declare:

- stable `ModuleMetadata` with unique `module_id`, name, version, category, description, maturity and assumptions;
- typed input/output `PortSpec` declarations;
- typed `ParameterSpec` declarations;
- explicit `ProofStatus` capabilities and limitations;
- deterministic `execute(...)` behavior where the science permits it; and
- `verify(...)` records only for verifiers that actually ran.

A module must never convert missing verification into success. Module-local `FORMAL + PASS` is still subject to the canonical claim/proof promotion gate.

## Plugin manifest

Every loadable plugin directory must contain `plugin.toml`:

```toml
[plugin]
id = "vendor.example"
name = "Example Plugin"
version = "1.0.0"
api_version = "1.0"
entrypoint = "plugin.py"
description = "What the plugin provides."
trust = "untrusted"
capabilities = ["module-registration"]
```

The current plugin API version is `1.0`. Unsupported API versions fail closed.

## Trust model

Python plugins can execute arbitrary code at import time. CACE therefore does **not** automatically scan and execute external plugin directories.

Manifest trust levels are:

- `builtin`: shipped with the CACE source tree;
- `trusted`: explicitly reviewed/approved by the user or deployment policy;
- `untrusted`: metadata may be inspected, but code execution is refused unless a caller explicitly opts into that trust level.

The trust label is policy metadata, not a sandbox. A future production plugin manager may add signing, isolated processes and capability enforcement, but callers must not assume those controls exist today.

## Entrypoint and transactional registration

The manifest entrypoint must be a Python file inside the plugin directory and define:

```python
def register(registry):
    registry.register(MyModule)
```

The SDK rejects entrypoints that escape the plugin directory, missing register hooks and plugins that register no new module IDs. Duplicate module IDs are rejected by the core registry.

Registration is staged transactionally. CACE first snapshots the existing module classes into an isolated staging registry, executes `register(staging_registry)`, verifies that existing module identities were not replaced/removed, and only then commits the newly registered module classes to the live registry. If plugin registration raises after adding only part of its modules, the live registry remains unchanged.

This transaction protects CACE registry consistency; it is **not** process isolation. Importing or executing an approved Python plugin can still perform arbitrary file/network/process actions with the host process permissions.

## Current v1.0 limitations

The v1.0 SDK is deliberately narrow. Before production-grade third-party plugin distribution, remaining work includes:

- a stricter plugin-version compatibility policy beyond a non-empty version string;
- enforceable capability declarations rather than descriptive capability metadata;
- plugin signing/publisher identity policy where appropriate;
- isolated-process or similarly strong containment for untrusted/high-risk plugins;
- resource/time limits and crash containment;
- automated admission evidence for plugin compatibility/security tests; and
- migration/deprecation rules for future plugin API revisions.

None of these limitations changes the rule that untrusted plugins are refused by default.

## Evidence boundary

A plugin can register a module that implements numerical, symbolic, interval or formal verifiers, but plugin trust is not scientific evidence. Formal public evidence still requires the canonical claim registry/proof ledger and exact qualification state. AI plugins or AI-assisted modules are likewise outside the verification trusted computing base unless a separately audited deterministic checker establishes the actual claim.

## Testing expectations

A production candidate plugin should include:

- manifest validation tests;
- module contract/unit tests;
- malformed-input and negative verification tests;
- serialization/replay tests when applicable;
- compatibility tests against the declared plugin API version;
- explicit tests proving unavailable optional backends report `NOT_RUN` rather than success; and
- security review appropriate to any file/network/process capabilities it requests.

The built-in `cace_studio/plugins/example_plugin/` is a minimal registration example, not a scientific production module.
