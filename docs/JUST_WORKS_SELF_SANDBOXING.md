# CACE "Just Works" Production Experience and Self-Sandboxing Runtime

Status: required production architecture.

## Product expectation

A production build should feel like a complete mathematics/sciences playground rather than a developer toolkit.

For an ordinary supported deployment:

1. install/start CACE;
2. CACE performs a local preflight;
3. required account/data directories and databases are initialized safely;
4. hardened private services are started with least privilege;
5. only the web gateway is exposed to the client;
6. available CPU/GPU/AI/scientific backends are detected;
7. optional unavailable backends are reported clearly instead of breaking unrelated features;
8. the webapp opens and the user can immediately create/import an experiment.

## Self-sandboxing

Where the host platform supports it, startup should apply the strongest available practical sandbox controls automatically:

- private loopback/Unix-socket service binding;
- default-deny public listeners;
- separate service identities/processes where practical;
- read-only runtime roots and explicit writable data/work directories;
- no-new-privileges/capability dropping;
- resource/time/process/file limits;
- restrictive egress for scientific/proof workers;
- secrets supplied only server-side;
- typed bounded IPC.

If a requested privileged/networked feature cannot be hardened to the required policy on the current platform, that feature must fail closed or remain disabled. CACE should not silently weaken its security boundary in order to appear functional.

## Graceful degradation

"Just works" does not mean "pretend everything is available."

Examples:

- no GPU: run supported CPU path or mark GPU-only capability unavailable;
- no local AI: scientific runtime still works, AI controls report disabled;
- no network permission: offline experiments still work, network features remain disabled;
- no formal backend/qualification artifact: formal status remains unqualified/not-run rather than inferred.

## Builder rule

Base44, Gemini AI Studio, Codex, or another code builder must build the complete production user experience, preserve the hardened backend architecture, and use CACE Build Lite plus regression/security/proof gates before declaring completion.
