# CACE Accounts and Directional AI Economy Pairing

Status: first executable core slice; GUI/API production wiring remains pending.

## 1. Account profile

The local account contract stores:

- display name;
- optional normalized email;
- user type: Basic, Researcher, or Enterprise;
- optional user-declared location and explicit location scope;
- protein-library opt-in;
- local-AI Math Coin wallet identity/capability handle;
- creation/disable metadata.

The profile database stores **no wallet private key**.

The Math Coin wallet identity is not a Monero wallet and does not replace the
canonical CACE XMR receive wallet declared in `CACE_PAYMENT_POLICY.json`.

## 2. Declared location

Location is user-declared rather than silently inferred.

Scopes:

- none;
- country;
- region;
- city;
- custom.

When scope is `none`, no location string is persisted. Production hosted
builders can add stricter policy/consent requirements without changing this
core data contract.

## 3. Protein library consent

Protein persistence is opt-in per account.

When disabled:

- attempts to persist protein objects fail closed;
- listing returns no saved library state.

When enabled:

- protein objects are serialized deterministically;
- semantic SHA-256 is recorded;
- source/license/attribution metadata are retained;
- duplicate account+content objects are deduplicated.

This is scientific-object storage, not proof evidence.

## 4. Network default-off rule

A CACE network instance starts with networking disabled.

Enabling networking creates:

- a **Receive Code**;
- a distinct **Outgoing Code**.

Both are high-entropy, direction-specific, single-use and short-lived.

Only the code hash is stored. Plaintext exists only at issuance/rotation so the
user can copy it to the peer instance.

## 5. Directional link

To create A -> B:

```
A outgoing code + B receive code -> directed economy link A -> B
```

A reverse B -> A link requires a second explicit pairing.

This makes inbound and outbound authorization independently visible instead of
turning one pairing event into silent bidirectional trust.

## 6. Pairing capability set

The first capability set is intentionally narrow:

- economy market discovery;
- economy compute bid;
- economy compute offer;
- heartbeat resource summary;
- settlement receipt metadata.

Pairing must never implicitly grant:

- arbitrary shell;
- filesystem authority;
- proof/claim mutation;
- scientific evidence mutation;
- wallet private keys;
- model-control APIs;
- plugin/tool installation.

## 7. Hosted builders

Base44, Gemini AI Studio, or another production builder may map a hosted
authenticated identity to this account/profile contract.

The hosted service may use a stronger production identity/session backend, but
it must preserve:

- user/profile ownership boundaries;
- protein storage consent;
- wallet-key secrecy;
- directional network capability rules;
- CACE scientific/evidence semantics.

## 8. Next implementation slice

1. authenticated API endpoints around account/profile/protein storage;
2. account-creation GUI including type, declared-location scope and protein opt-in;
3. network OFF/ON GUI;
4. receive/outgoing code display and rotate controls;
5. separate fields for entering a peer receive code and peer outgoing code;
6. linked-instance list and disconnect/revoke controls;
7. brokered heartbeat/economy transport using the stored link capabilities;
8. hosted database/auth adapter for the selected production builder;
9. rate limits, CSRF/session hardening and deployment security tests.
