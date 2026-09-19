# Accounts, Entitlements, Enterprise Proof Commerce, and Customer IP

Status: product/security/commercial architecture. This document defines the intended trust boundaries and commercial model. It is not legal advice and does not state that every component is already implemented.

## 1. Account service is separate from the proof runner

The GitHub/OCI proof runner must not authenticate end users and must never receive plaintext passwords, password hashes, payment credentials, Monero wallet spend keys, or general database credentials.

Preferred architecture:

```
Browser / Local CACE
        |
        v
Account + Entitlement API
        |
        +---- PostgreSQL/account database
        +---- Payment verifier / Monero invoice service
        +---- Contract service
        +---- Outbound mail service
        |
        +---- signed proof-job request ---> isolated proof runner
                                         |
                                         +---- signed result/artifact manifest
                                                  |
                                                  v
                                      internal evidence queue/object store
                                                  |
                                                  v
                                     Account/Delivery services
```

The proof runner may publish only narrowly scoped signed job events and artifact metadata.

## 2. Login and password storage

Users may create an account with email + password or an approved federated identity provider.

Password requirements:

- never store plaintext passwords;
- never encrypt passwords reversibly for later recovery;
- hash with Argon2id using a unique random salt per account;
- store hash algorithm/version/work-factor metadata so parameters can be upgraded;
- optionally apply a server-side pepper stored outside the account database;
- use TLS/authenticated channels for credential submission;
- support email verification, password reset, session revocation, and MFA/passkeys later.

OWASP currently recommends Argon2id for password storage; deployment parameters should be benchmarked and upgraded over time.

## 3. Core database records

Recommended durable tables/entities:

### users
- user_id
- email_normalized
- email_verified_at
- password_hash
- password_scheme
- password_parameters
- created_at
- disabled_at
- account_tier
- organization_id nullable

### organizations
- organization_id
- legal_name
- billing_name/address
- enterprise_verified_at
- contract_signer/contact
- tax/compliance metadata as required

### entitlements
- entitlement_id
- user_id / organization_id
- tier
- duration
- begins_at
- expires_at
- source: free_trial / payment / admin / enterprise_contract
- signed_token_id
- revoked_at

### free_trial_claims
- user_id
- tier
- claimed_at
- granted_seconds
- anti-abuse/device/account metadata

A user should not be able to repeatedly create the same first-time trial through ordinary account changes. Anti-abuse rules should be transparent and privacy-conscious.

### payment_invoices
- invoice_id
- user_id / organization_id
- tier
- pass_duration
- fiat_currency
- fiat_price
- quoted_xmr
- quote_expires_at
- receive_subaddress or invoice address
- state

### payment_events
Append-only ledger:
- event_id
- invoice_id
- event_type
- observed_at
- tx_hash/reference
- block_height where applicable
- confirmations
- received_xmr
- verifier identity/version

The application should keep a durable record that a payment was observed and which entitlement it created.

### proof_orders
- proof_order_id
- organization_id
- requesting_user_id
- canvas_snapshot_hash
- theorem/request summary
- quote
- statement_of_work_id
- contract_id
- IP option
- state
- created_at
- accepted_at
- paid_at

### proof_artifacts
- proof_order_id
- exact source/canvas hashes
- formal proof commit/run IDs
- kernel/axiom audit hashes
- PDF hash
- machine-readable manifest hash
- generated_at
- delivered_at
- recipient list

### audit_events
Append-only security/commercial trail for login, entitlement, payment, contract, proof-job, artifact, and delivery events.

## 4. Account tiers

Account tier determines allowed use, free introductory time, pass pricing, and commercial rights.

### Basic

Intended for personal learning, evaluation, and noncommercial exploration.

First-time introductory allowance:

- **24 hours once per eligible user**

Initial target pass pricing:

| Pass | Basic target |
| --- | ---: |
| 1 day | **$4.99** |
| 1 week | **$14.99** |
| 1 month | **$39** |
| 1 year | **$199** |

Basic is the lowest-price tier.

### Researcher

Intended for academic, nonprofit, independent scientific research, and other noncommercial research activity under the applicable license.

First-time introductory allowance:

- **48 hours once per eligible user**

Initial target pass pricing:

| Pass | Researcher target |
| --- | ---: |
| 1 day | **$14.99** |
| 1 week | **$49** |
| 1 month | **$149** |
| 1 year | **$999** |

Researcher is the middle-price tier.

Institutional academic licensing can later use seat/site quotes rather than only individual passes.

### Enterprise

Required for business/commercial use of CACE for engineering, product development, commercial scientific discovery, client work, or revenue-generating activity.

Initial target pass pricing per named user/seat:

| Pass | Enterprise target |
| --- | ---: |
| 1 day | **$99** |
| 1 week | **$399** |
| 1 month | **$1,499** |
| 1 year | **$9,999** |

Enterprise is the highest-price tier.

Enterprise compute, private relay/storage, dedicated support, private deployment, and large seat counts may be quoted separately.

There is no automatic first-time Enterprise free allowance specified here. Enterprise evaluation may be issued under a separate sales/evaluation entitlement.

All values above are launch targets rather than qualification-sensitive constants. Prices must live in a signed commercial policy and may be changed prospectively.

## 4.1 Compute capability entitlements

Compute acceleration is an account capability, separate from mathematical proof status.

### GPU / CUDA controls — all account tiers

Basic, Researcher, and Enterprise users receive an explicit **GPU Acceleration** ON/OFF control.

Behavior:

- OFF forces the supported CPU execution path.
- ON permits CACE to use an available supported GPU backend.
- A separate **CUDA** option is shown/enabled only when a compatible NVIDIA CUDA backend is actually detected.
- On non-NVIDIA hardware, CACE may expose another supported GPU backend under the generic GPU control; it must never label a non-CUDA device as CUDA.
- If GPU/CUDA was requested but unavailable, CACE must either fail explicitly or fall back according to the user's configured policy and record the fallback.
- The GUI should show the detected device/backend before execution.

GPU/CUDA availability is included for all three account tiers. It is not a paid Basic add-on.

### CPU multithreading

Researcher and Enterprise include the **Multithread CPU** ON/OFF control.

Basic is single-threaded by default, but a Basic account may purchase a one-time permanent **Multithread Unlock** for **USD $15**.

The Basic multithread unlock:

- is a durable account-level feature entitlement, not a time pass;
- survives expiration of an individual day/week/month/year pass;
- becomes usable whenever the account has an otherwise valid Basic usage entitlement;
- must be restored after login on another authorized local instance according to the licensing/device policy;
- cannot be created by browser/localStorage state alone;
- is recorded in the payment/entitlement audit trail.

Suggested entitlement identifier:

`feature.cpu_multithread.basic.perpetual.v1`

Researcher and Enterprise do not need this add-on because multithreading is included with those tiers.

### Provenance and rigor

Acceleration controls do not change theorem truth or proof status.

For numerical/scientific runs CACE should record:

- requested execution mode;
- actual CPU/GPU backend;
- CUDA runtime/device identifier when used;
- GPU model/device capability where available;
- requested and actual CPU thread count;
- deterministic/nondeterministic kernel mode;
- fallback reason if the requested backend was unavailable.

Execution-backend identity belongs in the run/evidence provenance because floating-point ordering or parallel execution can affect numerical results.

Formal mathematical qualification remains governed by its own pinned proof pipeline; purchasing or enabling GPU/multithreading cannot promote evidence or bypass proof gates.

## 5. Free-trial accounting

The free allowance is a real entitlement record, not a browser timer.

Basic:
- one first-time 24-hour entitlement.

Researcher:
- one first-time 48-hour entitlement.

The server/account service records:
- when the allowance is claimed;
- when usage starts/stops;
- consumed compute/application time according to the product policy;
- entitlement expiration;
- any administrative adjustment.

The scientific runtime receives only a signed entitlement token. It does not receive account passwords or payment database access.

## 6. Enterprise-only full-rigor proof purchase

Enterprise users may request a separate commercial deliverable for a result found in an Enterprise workspace.

Suggested UI:

**Request Full-Rigor Proof Package**

A proof order should capture an immutable snapshot of:

- relevant canvas;
- parameters and data identifiers;
- customer-authored assumptions;
- requested theorem/result;
- current CACE version;
- proof-contract/version identifiers;
- hashes of all customer-visible inputs.

The customer first receives a **contingent quote** based on the frozen request. CACE then performs the required internal proof/qualification work **before the customer is asked to sign or pay**.

The commercial rule is: **prove first, sell second**.

Before purchase, CACE must establish that the requested result can actually be delivered at the promised rigor. That pre-sale proof-ready gate includes, as applicable:

- exact theorem/request scope frozen and hashed;
- assumptions reviewed and made explicit;
- formal proof work completed for the requested result;
- Lean/kernel validation;
- axiom audit;
- exact theorem metadata;
- source/contract binding;
- qualification/provenance attestation;
- artifact-integrity verification;
- proprietary Background-IP disclosure review confirming that a customer-facing package can be produced without exposing protected internals.

Only after this gate is green does the order move to statement of work, signature, and payment.

## 7. Proof package contents

A purchased package may contain:

1. executive statement of the result;
2. exact customer-specific assumptions;
3. novel customer-specific equations/formulas derived for the engagement;
4. full readable LaTeX derivation;
5. rigorous proof steps required to justify the customer-specific conclusion;
6. explicit limitations/nonclaims;
7. machine-verifiable theorem names and proof-artifact hashes where applicable;
8. exact qualification/provenance manifest;
9. signed PDF hash/manifests;
10. optional implementation appendix.

The customer-facing package should **not reveal CACE proprietary background theorem source or proprietary reusable proof machinery** unless a separate agreement explicitly purchases those rights.

The PDF can cite internal CACE lemmas by opaque stable certificate identifiers and include sufficient independently reviewable customer-specific reasoning without disclosing proprietary source code or unrelated base-theorem internals.

## 8. Enterprise proof order and delivery architecture

The proof runner should not directly send customer email.

Required order of operations:

1. **Request + frozen scope** — Enterprise user selects the result; CACE freezes/hashes the canvas, inputs, assumptions, requested conclusion, and relevant software/proof versions.
2. **Contingent quote** — customer receives an estimated commercial quote and scope description, clearly marked subject to proof-ready qualification.
3. **Pre-sale proof-ready qualification** — CACE performs the necessary proof work and the normal kernel/axiom/metadata/provenance/integrity pipeline. The customer has not yet purchased the proof.
4. **Internal deliverability review** — CACE verifies that the qualified result can be expressed in a customer-facing package without disclosing protected Background IP. Status becomes `PROOF_READY_FOR_SALE` only after this succeeds.
5. **Statement of work + IP schedule** — the exact qualified result, deliverables, exclusions, ownership terms, price, support, and delivery format are written into the agreement.
6. **Customer signature** — authorized customer signer accepts the agreement.
7. **Payment / credit approval** — commercial entitlement to the proof package is created only after the payment/credit gate is satisfied.
8. **Customer-document rendering** — a separate document service renders the approved LaTeX/PDF **from the already-qualified proof artifact**, not by re-solving the theorem after purchase.
9. **Trade-secret disclosure review** — automated and human review verifies that the customer document contains the agreed customer-specific derivation but not proprietary Background-IP source, hidden theorem bodies, internal proof strategies, secrets, or unrelated reusable machinery.
10. **Final artifact binding** — PDF, source excerpt if any, contract ID, qualified proof artifact, and manifest are hashed and cross-bound.
11. **Delivery** — an outbound mail/delivery service sends the customer the permitted PDF/secure link.
12. **Audit closeout** — delivery, recipient, hashes, contract, payment, qualification IDs, and disclosure-review result are written to the append-only audit trail.

This sequence ensures the customer is not asked to purchase a bespoke proof package until CACE has already demonstrated that the requested rigorous result is available.

It also keeps email/API credentials away from the proof runner and preserves zero-egress scientific/proof isolation.

## 9. Customer attribution and IP contract structure

Enterprise proof purchase should use an executed agreement before transferring rights.

Recommended contract split:

### CACE Background IP — retained by CACE

Includes, unless expressly sold separately:

- pre-existing CACE source;
- proprietary base theorems and internal lemmas;
- theorem libraries;
- proof strategies;
- reusable abstractions;
- formalization infrastructure;
- compiler/runtime techniques;
- reusable templates;
- generic improvements;
- confidential methods and know-how.

These remain CACE property and may be protected as copyrightable software/expression, contract rights, and/or trade secrets where legally applicable.

### Customer Foreground Deliverable

May include:

- customer-specific report and LaTeX exposition;
- customer-specific formal statements/proof artifacts;
- customer-specific implementation/code created under the order;
- customer-specific applied inventions or engineering designs;
- customer-specific data and models.

For an exclusive package, the contract may assign to the customer, after full payment, all transferable rights in the agreed foreground deliverables **to the extent those rights legally exist**, while CACE retains all Background IP.

A safer contract phrase is not simply "the equation belongs to Company X." It should define:

- Background IP;
- Foreground IP;
- assigned deliverables;
- excluded reusable CACE technology;
- confidentiality;
- publication rights;
- patent prosecution/cooperation if relevant;
- attribution;
- permitted internal references to CACE certificates;
- whether CACE retains a license to generic/non-customer-specific improvements.

## 10. Important U.S. IP limitation for mathematics

A contract can allocate ownership and confidentiality of deliverables, but it cannot create statutory IP rights where the law does not provide them.

Under U.S. Copyright Office guidance, ideas, methods, mathematical principles, formulas, and algorithms are not protected by copyright as such. Copyright can protect the original text, diagrams, software, and other expression of a proof/report.

USPTO guidance treats mathematical formulas/equations and calculations as abstract mathematical concepts for patent-eligibility analysis; a pure formula is not automatically patentable. A customer-specific applied invention may potentially be patentable if it satisfies the full legal requirements.

Therefore Enterprise marketing should say:

> Customer receives the contractually assigned customer-specific deliverables and all transferable foreground IP rights specified in the agreement, while CACE retains its proprietary Background IP.

Do not promise that a novel mathematical identity by itself becomes exclusive statutory IP merely because the customer paid for it.

## 11. Protecting proprietary base theorems

The base theorem system should be treated as confidential CACE Background IP and, where the legal requirements are met, protected as trade-secret material.

The project should continuously use concrete **reasonable secrecy measures**, not merely a confidentiality label.

### Repository and source controls

- keep proprietary theorem repositories private;
- separate customer-visible/public theorem interfaces from private theorem implementations;
- never put secret theorem bodies, proprietary proof strategies, or reusable internal lemmas into public GitHub Actions artifacts;
- do not publish complete private theorem source in customer PDFs, public documentation, examples, logs, crash reports, telemetry, or support bundles;
- use stable opaque theorem/certificate identifiers at customer-facing boundaries;
- mark files/modules by disclosure class, for example `PUBLIC`, `CUSTOMER_DELIVERABLE`, `CACE_CONFIDENTIAL`, and `CACE_TRADE_SECRET`;
- keep customer-export tooling incapable of traversing into trade-secret source directories by default.

### Access controls

- least-privilege role-based access to proprietary theorem repositories;
- separate production, proof-runner, document-rendering, support, and customer-delivery identities;
- no customer, collaboration relay, browser client, local AI, or plugin receives raw proprietary theorem-source access;
- require MFA/passkeys for privileged human accounts;
- remove access promptly when personnel or contractor roles end;
- periodically review who can read/export private theorem material;
- use just-in-time/temporary elevated access where practical.

### Cryptographic and infrastructure controls

- encrypt proprietary repositories, backups, object-store copies, and sensitive proof artifacts at rest;
- use TLS/authenticated channels in transit;
- keep signing/encryption secrets in managed secret storage/KMS/HSM-equivalent systems where practical;
- keep proof runners isolated from public Internet ingress and from unrelated customer/account databases;
- separate confidential proof artifacts from publicly downloadable CI artifacts;
- maintain independently retained, content-addressed logs without putting theorem source into logs unnecessarily.

### Personnel and contractual controls

- confidentiality/NDA obligations for employees, contractors, reviewers, and vendors who may access proprietary theorem material;
- invention-assignment/IP agreements appropriate to the role;
- explicit return/destruction obligations on termination where appropriate;
- vendor/data-processing agreements for any service that can access confidential proof artifacts;
- customer agreements expressly state that no license to CACE Background IP is granted except as specifically listed.

### Monitoring, audit, and export controls

- append-only audit events for access to/export of designated trade-secret modules;
- log repository clones/downloads and privileged artifact exports where technically practical;
- alert on unusual bulk export/access patterns;
- require an explicit disclosure-review gate before any Enterprise PDF/source bundle is released;
- maintain a record of exactly which proprietary certificate identifiers were referenced in each customer deliverable;
- watermark or uniquely identify confidential review copies where appropriate.

### Customer-facing disclosure minimization

The customer should receive enough rigorous material to evaluate and use the purchased **customer-specific result**, but CACE should disclose no more reusable internal machinery than the contract requires.

A customer PDF may include:

- the customer's exact assumptions;
- the customer-specific theorem;
- the customer-specific derivation/proof;
- independently checkable consequences;
- qualification/provenance identifiers;
- opaque references to CACE Background certificates.

It should exclude, unless separately licensed:

- unrelated base theorem bodies;
- reusable internal lemmas;
- proprietary theorem-generation methods;
- hidden proof-search strategies;
- private source code;
- internal training/research corpora;
- secret system prompts/models/weights;
- infrastructure credentials or operational details that create security risk.

### Trade-secret continuity

The repository should preserve evidence that reasonable secrecy measures were actually used over time: access policies, private-repository settings, disclosure reviews, confidentiality agreements, audit logs, incident handling, and periodic access reviews.

A secrecy failure should trigger an incident review and remediation; CACE should not silently continue calling material confidential if it has intentionally been published without restriction.

## 11.1 Customer-release source-secrecy gate

Every Enterprise proof package and any customer software bundle must also pass the CACE source-secrecy gate.

Customer deliverables must not contain private theorem source, reusable proof-search machinery, debug/source-map material, private CI/proof-runner scripts, or unapproved protected-core source.

The final artifact is scanned, hashed, disclosure-reviewed, and bound to the delivery manifest before release.

See `docs/SOURCE_SECRECY_AND_ANTI_REVERSE_ENGINEERING.md`.

## 12. Enterprise proof pricing

There is no universal maximum price for bespoke mathematical/formal verification. Price depends on scope, economic value, exclusivity, liability/risk allocation, turnaround, required domain experts, compute, and whether customer ownership/exclusivity is transferred.

Initial commercial bands:

| Proof engagement | Suggested quote band |
| --- | ---: |
| Focused proof/report, narrow scope | **$15,000–$50,000** |
| Complex rigorous proof package with formal artifacts | **$50,000–$150,000** |
| High-value exclusive customer-specific proof/IP assignment | **$150,000–$500,000** |
| Mission-critical multi-theorem verification/R&D program | **$500,000–$2,000,000+** |

For unusually valuable engineering or scientific IP, high assurance, short deadlines, exclusivity, or material liability, value-based pricing can exceed these ranges.

A single proof should not be priced at a seven-figure amount merely because it is mathematically difficult. Seven-figure pricing is most defensible when the engagement is a broader high-value R&D/verification program or when the result protects/creates very substantial commercial value.

## 13. Market anchors

Public 2026 comparables useful for positioning:

- Runtime Verification publicly lists formal-verification consulting at **$30,000/month** for one dedicated engineer and outsourced formal verification at **$50,000/month** for two verification engineers.
- Chainscore Labs publicly lists formal verification engagements starting at **$15,000** for an audit/report and **$50,000** for integration support, with enterprise work quoted.
- MathWorks' March 2026 Standard annual list price is **$1,050** for an individual MATLAB license and **$4,205** for concurrent MATLAB; specialized toolboxes can add thousands to tens of thousands per year.
- COMSOL commercial term licensing has a **12-month minimum** and uses commercial license options/quotes for larger configurations.
- Large formal-methods/proof-engineering R&D programs can be much larger than individual proof engagements; they should not be represented as per-proof comparables.

These anchors support a product model where ordinary CACE access is software-priced, while bespoke exclusive formal proof work is consulting/R&D-priced.

## 14. Proof-order gates

### Pre-purchase proof-ready gate

Before CACE asks the customer to sign/pay for the bespoke proof package:

- exact customer request is frozen and hashed;
- theorem assumptions are explicit;
- requested result has been proved to the required scope;
- formal work passes the required kernel/axiom/metadata/provenance qualification pipeline;
- artifact integrity passes;
- result is internally classified `PROOF_READY_FOR_SALE`;
- a disclosure review confirms that a rigorous customer package can be produced without exposing protected CACE Background IP.

If this pre-purchase gate fails, the customer must not be sold the proof as a completed rigorous result. CACE may instead revise the scope/quote or decline the order.

### Post-purchase delivery gate

After contract/signature/payment:

- customer-IP schedule matches the exact qualified result;
- PDF is rendered from and cryptographically bound to the qualified artifact;
- proprietary Background-IP redaction/disclosure review passes again on the final document;
- final PDF and manifest are hashed;
- permitted recipients are verified;
- delivery is audit logged.

Payment does not lower the proof standard and cannot cause an unqualified theorem to be labeled rigorous.

## 15. Commercial security tests

Add negative tests proving:

- runner cannot query users/password hashes;
- runner has no mail provider credential;
- account service cannot inject Lean/source into the isolated proof runtime outside the approved job bundle;
- changing browser tier does not create an entitlement;
- creating another account does not trivially reset a first-time allowance under anti-abuse policy;
- payment ledger is append-only at the application layer;
- unsigned payment events cannot create entitlements;
- an Enterprise proof cannot be delivered before contract/payment gates;
- artifact/PDF hash mismatch blocks delivery;
- customer PDF cannot accidentally include files marked CACE Background IP;
- a customer foreground assignment does not mutate ownership metadata for CACE Background IP.


## Canonical Monero receive wallet

CACE already has an existing Monero wallet selected in earlier application
assets. Production builders must reuse that wallet and must not generate a
replacement wallet merely because a new frontend/backend/payment integration is
being generated.

Canonical public XMR receive address:

`482ivJw4VqAaRvixSG84DgDum33SoBfnNiMxngMKn7etfKP1mwG2ZskTLVwRAhPmPDcb5iqLGkKdJbQ6DJmzqePPPxp3tmQ`

The same value is machine-readable in `CACE_PAYMENT_POLICY.json`.

Operational rules:

- the public address may appear in server configuration and payment QR payloads;
- Monero seed/spend key/view key/wallet-RPC credentials remain secret and must
  never be committed, emitted to browser JavaScript, or exposed to AI context;
- where unique invoice/subaddress handling is used, those invoice addresses must
  be issued by the same existing wallet custody;
- Base44, Gemini AI Studio, Codex, and other coding agents must not bootstrap a
  new Monero wallet as part of deployment or account creation;
- the account-scoped local-AI Math Coin wallet identity is separate from this
  XMR receive wallet;
- XMR payment/settlement state has no scientific evidence authority.
