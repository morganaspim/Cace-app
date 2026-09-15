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

## Entrypoint

The manifest entrypoint must be a Python file inside the plugin directory and define:

```python
def register(registry):
    registry.register(MyModule)
```

The SDK rejects entrypoints that escape the plugin directory, missing register hooks and plugins that register no new module IDs. Duplicate module IDs are rejected by the core registry.

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
