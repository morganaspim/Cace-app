# CACE Webapp Gateway + Hardened Local Layer

Status: required production architecture.

## Client view

A customer/client sees only the browser webapp served through the CACE Web
Gateway.

The client does **not** see or connect directly to:

- Python scientific workers;
- C++/GPU workers;
- local AI/model servers;
- account/protein databases;
- directional AI-network transport;
- Math Coin services;
- Monero wallet RPC/custody;
- filesystem/export workers;
- evidence/provenance stores;
- Lean/formal qualification workers.

## Topology

```
Internet / client browser
        |
     HTTPS/WSS
        |
+-----------------------+
| CACE Web Gateway      |  only public CACE app surface
| static UI + API proxy |
+-----------------------+
        |
  typed authenticated IPC
        |
+--------------------------------------------------+
| Hardened Local / Private CACE Service Plane      |
|                                                  |
| orchestrator                                     |
| scientific Python runtime                        |
| C++ / GPU workers                                |
| local-AI capability broker                       |
| account/profile/protein store                    |
| AI-network pairing broker                        |
| heartbeat / compute economy / Math Coin broker   |
| canonical Monero wallet broker                   |
| durable experiment/evidence/provenance storage   |
| isolated Lean qualification dispatcher/runner    |
+--------------------------------------------------+
```

## Gateway responsibilities

The public gateway may:

- serve bundled client assets;
- terminate or sit behind TLS;
- authenticate sessions;
- perform authorization;
- enforce CSRF/CORS/CSP;
- validate typed requests;
- enforce request/body/upload/rate limits;
- issue correlation/request IDs;
- proxy only approved typed operations into the private orchestrator;
- stream bounded job/progress/result events back to the browser.

It must not become the scientific runtime or proof/wallet authority.

## Local layer hardening

Protected services should use, where supported:

- Unix-domain sockets or private loopback/service networking;
- firewall default-deny public ingress;
- no general egress for scientific/proof workers;
- explicit endpoint allowlists for necessary network brokers;
- one service identity per privilege class;
- read-only root/package filesystems;
- explicit writable work/data directories;
- `no_new_privs`, dropped Linux capabilities and seccomp/AppArmor/systemd or
  container sandbox controls;
- bounded CPU, RAM, processes, open files, uploads and job duration;
- typed/versioned/size-bounded IPC;
- peer/service authentication;
- server-side secret injection;
- append-only privileged-operation audit logs;
- pinned/locked dependencies, SBOM and vulnerability/secret scans.

## Browser rules

The browser:

- connects only to the gateway/same origin;
- never receives wallet keys, DB credentials, proof-runner credentials or raw
  backend secrets;
- never talks directly to Ollama/model servers, wallet RPC, SQLite/Postgres,
  scientific workers or proof runners;
- never chooses arbitrary local filesystem paths for the server;
- never supplies evidence/proof status as trusted state;
- never loads scientific/runtime code from third-party URLs.

A restrictive CSP should make these rules visible and enforceable.

## Generated-app builders

Base44, Gemini AI Studio and equivalent builders may implement:

- responsive browser UI;
- authentication screens;
- account/profile settings;
- canvas presentation;
- gateway handlers/adapters;
- progress/result views.

They must call the canonical CACE private backend contracts rather than
reimplementing scientific/proof semantics in generated JavaScript/server code.

## Production verification

Before calling a deployment production hardened:

1. external port scan: only intended web ports exposed;
2. local listener scan: every protected service non-public;
3. firewall policy test;
4. CSP/connect-src negative tests;
5. authn/authz/CSRF/CORS negative tests;
6. rate/body/upload/decompression limits;
7. direct protected-service browser-access tests must fail;
8. secret/frontend-artifact scan;
9. wallet/AI/proof privilege-negative tests;
10. sandbox/resource-limit fault tests;
11. backup/recovery/audit tests;
12. normal scientific/evidence regression;
13. formal qualification only where the exposed claims require it.

This is an engineering/security assurance architecture. It does not itself prove
mathematical claims.
