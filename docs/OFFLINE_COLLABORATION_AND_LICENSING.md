# Offline Core, Collaboration, Sandboxing, and Monero Licensing

Status: target product/security/licensing architecture. This document is implementation intent, not a statement that every control is already implemented or security-audited.

## 1. Core principle: zero-egress scientific runtime

CACE's scientific runtime should not have general Internet access.

The preferred architecture is:

```
                 controlled external network
                           |
             +-------------+-------------+
             |                           |
     Collaboration Broker         Licensing Broker
             |                           |
             +-------------+-------------+
                           |
                    narrow local IPC
                           |
                CACE Scientific Sandbox
                           |
              Python / C++ / Lean interfaces
```

The scientific sandbox itself gets **no general outbound Internet route**.

Network-facing brokers are separate processes with separate credentials and minimal capabilities. They must not be able to inject executable content into the scientific runtime.

The practical security goal is **zero arbitrary network import**, not pretending that collaboration messages do not contain data at all.

## 2. What the sandbox may and may not receive

Allowed through narrow, schema-validated channels:

- signed license capability tokens;
- collaboration room/session capabilities;
- typed canvas operations;
- typed parameter values;
- presence/cursor/selection state;
- chat/research-note text if enabled;
- proof/evidence artifact digests and metadata references that are independently verified locally;
- signed broker status/error responses.

Forbidden from network brokers:

- Python source;
- JavaScript source;
- dynamically loadable libraries;
- packages or dependency updates;
- Lean source modules;
- plugins;
- arbitrary ZIP/archive import;
- executable files;
- shell commands;
- unrestricted filesystem paths;
- arbitrary URLs for the core to fetch;
- serialized objects that can trigger code execution;
- opaque binary payloads outside an explicitly versioned, bounded schema.

No network message may directly set a verification state to trusted PASS. Received evidence claims must be independently checked under the normal CACE evidence rules.

## 3. Browser/webapp network policy

The browser-facing UI should be packaged so it does not fetch application code, libraries, fonts, scripts, modules, models, or scientific data from third-party Internet origins at runtime.

Production target:

- bundle all required frontend assets into the signed release;
- Content Security Policy with `default-src 'self'`;
- no remote `script-src`, `style-src`, font CDN, or dynamic module import;
- `connect-src` limited to the local CACE API and explicitly configured local collaboration/licensing brokers;
- disable arbitrary remote URL imports;
- no service-worker behavior that fetches third-party code;
- no remote package manager in the running product;
- dependency updates occur only through a separately reviewed/signed release process.

For a localhost deployment, the UI may talk to local services over loopback or Unix-socket-backed API bridges while those services enforce the actual network isolation.

For a remotely hosted deployment, the same principle becomes: the browser talks only to the CACE origin; the server-side scientific worker remains zero-egress and network brokers remain separate.

## 4. Local-instance sandbox

Each local scientific instance should run with an operating-system-enforced sandbox.

Target controls:

- dedicated unprivileged user/UID;
- no-new-privileges;
- read-only program/runtime image;
- separate writable project/workspace directory;
- no execution permission from user workspace where practical;
- no general outbound network interface in the scientific worker;
- explicit IPC endpoints only;
- CPU, RAM, process-count, disk, and wall/compute-time quotas;
- bounded child-process creation;
- restricted device access;
- no cloud credentials;
- no SSH keys;
- no host Docker socket;
- no package-manager authority;
- no arbitrary shell exposed to browser, plugins, collaborators, or AI;
- seccomp/AppArmor/SELinux/container policy where supported;
- auditable sandbox start/stop/resource events.

The local AI sandbox should be equal or stricter.

## 5. Shared-canvas collaboration

CACE should support an **Invite Collaborator** action without giving the scientific core general network access.

### 5.1 Invite flow

1. Owner clicks **Collaborate / Invite**.
2. CACE generates:
   - random room/session ID;
   - one-time or bounded capability;
   - owner/room public-key material;
   - requested role: viewer/editor.
3. The collaboration broker creates or joins the network room.
4. CACE shows an invite link and/or QR code.
5. The collaborator accepts and obtains only the room capability granted by the owner.
6. The scientific sandboxes continue to communicate only through their local brokers.

### 5.2 Collaboration protocol

Prefer a small, versioned operation protocol or CRDT/OT layer.

Allowed operations should be explicit, for example:

- `node.add`;
- `node.move`;
- `node.delete`;
- `parameter.set`;
- `edge.connect`;
- `edge.disconnect`;
- `group.create`;
- `research_note.edit`;
- `view.cursor`;
- `view.selection`.

Every operation should carry:

- schema version;
- room/session ID;
- sender identity/key;
- monotonic/causal sequence information;
- operation ID;
- typed payload;
- timestamp or logical clock;
- integrity/authentication tag or signature.

No `eval`, executable source, package identifier, arbitrary file path, or arbitrary object deserialization is permitted.

### 5.3 End-to-end security

Target properties:

- end-to-end encrypted room content;
- authenticated participants;
- relay sees ciphertext where practical;
- room capability can be revoked;
- owner can kick participants;
- viewer/editor roles;
- rate and size limits;
- replay protection;
- deterministic conflict resolution;
- hash-chained or otherwise auditable operation history;
- local snapshots and recovery;
- offline-first local continuation when relay connectivity disappears.

A simple relay is preferable to a complex peer-to-peer stack if it is easier to audit. Peer-to-peer transport may be added later behind the same fixed collaboration protocol.

### 5.4 Scientific evidence under collaboration

Collaboration edits change the experiment normally and therefore invalidate/recompute affected evidence.

Remote participants may share evidence references, but:

- peer-reported PASS is not trusted automatically;
- theorem/proof artifacts must be locally verified or pass the canonical claim gate;
- visual camera/coordinate state remains presentation-only;
- network presence does not change mathematical rigor.

## 6. Time-limited local licensing

CACE may provide a configurable standard/free allowance and paid passes.

The existing prototype used a 10-hour/day standard quota. Production policy should be signed/configurable data rather than trusted browser JavaScript.

Required paid durations:

- 1 day;
- 1 week;
- 1 month;
- 1 year.

When the active allowance/pass expires:

- running scientific jobs should reach a safe cooperative checkpoint where practical;
- new compute launches are blocked;
- save/export/read-only inspection remains available unless a different explicit product policy is chosen;
- the UI opens the licensing panel and payment QR;
- no scientific evidence is deleted or downgraded merely because a license expires.

## 7. Monero payment architecture

### 7.1 Current candidate receive address

The latest supplied CACE prototype contains this Monero receive address:

`482ivJw4VqAaRvixSG84DgDum33SoBfnNiMxngMKn7etfKP1mwG2ZskTLVwRAhPmPDcb5iqLGkKdJbQ6DJmzqePPPxp3tmQ`

Before production release, the receive address must be confirmed by the owner and bound into a signed release/payment policy so a compromised UI cannot substitute another address.

The spend key and private wallet credentials must never be shipped with the application.

### 7.2 Payment QR

When a user selects a pass, show:

- plan name;
- exact duration;
- USD-denominated reference price;
- quoted XMR amount;
- quote timestamp/expiry if dynamic;
- canonical receive address or invoice subaddress;
- Monero URI QR;
- text copy of the address and amount;
- payment-status/activation instructions.

Prefer unique subaddresses/invoices from the external licensing broker where available.

### 7.3 Do not trust browser-side payment state

Production CACE must not unlock because:

- localStorage says paid;
- the user entered an arbitrary transaction hash;
- browser JavaScript generated a fake transaction identifier;
- a UI variable was edited;
- a local clock alone says the pass is valid.

Those mechanisms are prototypes only.

### 7.4 Signed offline license token

After the licensing broker verifies payment, it issues a signed capability token.

Suggested fields:

- schema/policy version;
- license ID;
- plan ID;
- issued-at;
- not-before;
- expires-at;
- entitlements;
- optional seat/device binding;
- optional remote-compute quota;
- transaction/invoice reference hash;
- nonce;
- issuer key ID;
- signature.

Recommended signature: a modern audited public-key signature such as Ed25519.

The CACE sandbox contains only the verification public key. The signing private key remains outside the sandbox, preferably in a hardened licensing service/HSM or equivalent protected host.

This token is the only network-derived object the license verifier needs, and it is fixed-schema data, not executable content.

### 7.5 Fully offline activation option

If the CACE machine has no network broker at all:

1. CACE displays the Monero payment QR plus a local activation request/challenge.
2. The user pays using another device.
3. A licensing service verifies the payment externally.
4. The service returns a signed activation code or activation QR.
5. The user transfers only that signed token into CACE.
6. CACE verifies the signature locally.

This preserves an offline scientific machine.

### 7.6 Time rollback and local tampering

Offline commercial enforcement cannot be made mathematically unbreakable on hardware controlled by the user.

Mitigations may include:

- OS secure storage/keychain;
- monotonic last-seen timestamp/counter;
- signed lease renewal state;
- tamper-evident local usage log;
- native license verifier;
- optional device binding;
- periodic broker renewal for longer passes.

These controls are commercial/license enforcement, not scientific evidence.

## 8. Pricing architecture

Pricing should be denominated in USD (or a stable policy currency) and converted to XMR at purchase time by the external licensing broker. Do not hard-code a long-lived XMR amount as the economic price because XMR is volatile.

### 8.1 Market benchmark

As of September 2026:

- MathWorks lists a Standard annual MATLAB individual license around **USD 1,050/year** in its March 2026 standard price list; many engineering/scientific toolboxes add roughly USD 526–600/year each.
- COMSOL commercial term licenses use a **12-month minimum** and quote-based pricing.
- Maplesoft offers annual/perpetual engineering-math licensing and quote-based multi-user configurations.

These products are not identical to CACE, but they establish that professional engineering/scientific software commonly supports annual pricing around the high hundreds to thousands of dollars, often before add-ons or multi-user/compute costs.

### 8.2 Initial target pricing band

A reasonable initial professional single-user target, subject to actual operating-cost and market validation:

| Pass | Target USD price | Purpose |
| --- | ---: | --- |
| 1 day | $12 | short burst / proof or simulation day |
| 1 week | $49 | project sprint |
| 1 month | $149 | active research month |
| 1 year | $999 | primary professional plan |

The annual target is intentionally in the same broad market class as a base professional MATLAB license while remaining below its cited 2026 list price.

Short passes carry a convenience premium rather than being linear slices of the annual price.

These are target launch prices, not irreversible constants. Production pricing should live in a signed policy file and be reviewable without changing scientific source.

### 8.3 Compute-cost separation

Do not promise unlimited project-funded cloud/OCI/GPU/proof compute merely because local application time is unlocked.

Recommended separation:

- pass unlocks local CACE application/compute time;
- a fair-use remote proof/compute allocation may be bundled;
- heavy remote compute is capped, queued, or metered separately;
- UI displays local entitlement separately from project-funded remote compute.

This prevents one user from turning a low-cost monthly pass into unbounded cloud expense.


## 8.1 Account tiers and enterprise proof commerce

CACE account/login, first-time allowances, payment ledgers, tiered pass pricing, enterprise proof orders, customer-specific PDF delivery, and Background-IP/Foreground-IP separation are specified in `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`.

Hard trust-boundary rule: the proof runner does **not** authenticate users, store password hashes, process customer email, or hold payment/database credentials. It receives only signed proof-job requests and emits signed result/artifact metadata.

## 9. R&D funding policy

The licensing UI may state that fees support:

- CACE research and development;
- maintenance;
- proof infrastructure;
- hosted collaboration relay;
- object/evidence storage;
- optional remote compute;
- security/qualification work.

Avoid claiming that a payment buys mathematical certainty or a particular research outcome.

## 10. Licensing and consumer safeguards

Before commercial launch, define:

- terms of service/license;
- refund/cancellation policy;
- tax/VAT handling;
- privacy policy;
- data retention;
- sanctions/export/payment compliance appropriate to deployment jurisdictions;
- support expectations;
- what happens during relay/payment outages;
- recovery path if a license token is lost;
- enterprise/multi-seat policy.

Cryptocurrency payment should be one licensing/payment mechanism, not part of the scientific evidence architecture.

## 11. Negative security tests

Add tests proving that:

- scientific worker cannot resolve/connect to arbitrary Internet hosts;
- browser CSP rejects third-party script/module/data origins;
- collaboration broker cannot send executable payloads;
- malformed/oversize collaboration operations fail closed;
- collaborator cannot elevate viewer to editor;
- collaborator cannot set formal PASS;
- replayed operations are rejected;
- payment address cannot be changed by unsigned remote data;
- arbitrary tx hash does not unlock;
- unsigned/expired/wrong-key license tokens are rejected;
- local clock rollback does not silently extend a lease when monotonic state is available;
- licensing broker has no access to scientific workspace beyond its narrow IPC;
- collaboration broker has no package/plugin installation authority.

## 12. Relationship to proof rigor

Networking, licensing, payment, and collaboration remain outside the mathematical trusted-computing base.

A paid pass does not strengthen evidence.

An expired pass does not invalidate a theorem.

A collaborator cannot confer proof status.

The exact same canonical proof/evidence rules apply whether CACE is offline, collaborating, free, paid, or enterprise.
