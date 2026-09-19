# Public CACE Service, Global Signup, and Privacy-Preserving Improvement Loop

Status: required production architecture.

## Public service

CACE should have one stable HTTPS URL where eligible users can:

1. open the public webapp;
2. create/recover an account;
3. claim the allowed free trial;
4. receive their own durable logical CACE instance;
5. reconnect later from any ordinary supported browser;
6. optionally pair local CACE/local-AI instances from their own networks.

The production domain is deployment configuration. Builders must not invent or
hard-code an unowned domain.

## Country access policy

Requested product policy:

- default: service available;
- block country code **CN**;
- block country code **KP**.

Enforce this before tenant provisioning at the CDN/edge or trusted reverse
proxy, and repeat the check for signup/session/broker-registration paths.

Country GeoIP is an access-control signal, not perfect proof of physical
location. Keep sanctions/export/end-user compliance as a separate layer.

## Per-user instance

Successful signup creates or restores one durable logical tenant instance under
the multi-tenant policy. The browser sees only the global web gateway; tenant
compute/data remains behind the hardened private service plane.

## Improvement loop

CACE should improve from real-world usage without quietly collecting customers'
scientific work.

### Lane 1 — Essential operational heartbeat

Hosted instances report a minimal service heartbeat such as:

- version/release;
- online/health state;
- resource/queue buckets;
- error/retry counts;
- job counts;
- proof qualification **status/counter metadata only**.

This lane excludes scientific payloads, theorem/proof text, AI conversations,
protein content and wallet secrets.

### Lane 2 — Product analytics

With the appropriate notice/consent/legal basis, collect privacy-minimized
aggregate signals such as:

- feature adoption;
- module-category usage;
- canvas/graph size buckets;
- heartbeat activity counts;
- performance/compute class;
- trial conversion;
- aggregate regional trends.

Use these to prioritize features, capacity, documentation, customer success and
internal sales strategy. Prefer aggregate cohorts rather than analyst access to
named customer activity.

### Lane 3 — Voluntary proof/research contribution

Actual proof artifacts, theorem statements, proof failure traces, benchmark
inputs or research examples are **not** silently uploaded.

Provide a separate opt-in such as:

**Contribute selected proofs/research to improve CACE**

with project/account controls, contribution/IP terms, preview/redaction and a
content-addressed receipt.

This lets CACE build a high-quality proof/research corpus without appropriating
private customer science.

## Feedback architecture

```
Tenant instance
  |
  +--> essential health/heartbeat metadata
  |       -> reliability/capacity/security
  |
  +--> opted/approved product analytics
  |       -> aggregate product + sales insights
  |
  +--> explicitly donated proof/research artifacts
          -> reviewed improvement corpus
          -> testing/training/research pipeline
```

None of these telemetry paths can set PASS/VERIFIED, modify formal
qualification, change wallet balances, or alter user scientific data.

Machine-readable policies:

- `CACE_PUBLIC_SERVICE_POLICY.json`
- `CACE_TELEMETRY_PRIVACY_POLICY.json`
- `CACE_MULTI_TENANT_POLICY.json`
- `CACE_DEPLOYMENT_BOUNDARY.json`
