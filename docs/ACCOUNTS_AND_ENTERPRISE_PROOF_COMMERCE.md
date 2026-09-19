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

The customer receives a quote and statement of work before expensive bespoke proof work begins.

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

## 8. Delivery architecture

The proof runner should not directly send customer email.

Preferred flow:

1. isolated runner finishes the proof job;
2. runner signs/publishes artifact metadata to an internal queue/object store;
3. account service verifies the result and contract/payment state;
4. a separate document service renders the approved LaTeX/PDF;
5. PDF and manifest are hashed and stored;
6. an outbound mail service sends a download link or the permitted attachment;
7. delivery event is written to the audit ledger.

This keeps email/API credentials away from the proof runner and preserves zero-egress scientific/proof isolation.

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

The base theorem system should be treated as confidential Background IP/trade-secret material where appropriate.

Controls:

- keep full proprietary theorem source out of customer PDFs;
- use stable opaque theorem/certificate identifiers;
- reveal only the assumptions/consequences necessary for the purchased result;
- restrict employees/contractors by confidentiality and invention-assignment agreements;
- least-privilege access to theorem repositories;
- log access/export;
- avoid publishing secret theorem source in public artifacts;
- separate public verification statements from private proof implementation;
- apply reasonable trade-secret protection measures continuously.

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

## 14. Proof-order acceptance gates

Before a paid enterprise proof is marked delivered:

- contract signed;
- payment/credit approval satisfied;
- exact customer request frozen and hashed;
- theorem assumptions explicitly recorded;
- formal work passes the required CACE proof pipeline;
- PDF matches the qualified artifact;
- proprietary Background IP redaction/review passes;
- customer-IP schedule matches the contract;
- final PDF and manifest are hashed;
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
