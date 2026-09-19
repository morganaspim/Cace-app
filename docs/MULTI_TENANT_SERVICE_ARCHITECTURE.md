# CACE Multi-User / Multi-Tenant Production Service Architecture

Status: required production architecture.

## Recommended architecture

### Rank 1 — Shared control plane + isolated per-user/tenant sandboxes

This is the preferred design.

Each person/account owns a **durable logical CACE instance**, but CACE does not
copy the repository or maintain a different source tree for every person.
Instead, all tenants run the same reviewed, immutable CACE release image.

The platform is split into:

1. **public/stateless web plane** — load-balanced HTTPS/WSS gateways;
2. **tenant control plane** — accounts, instance registry, scheduling, routing,
   quotas and sandbox lifecycle;
3. **private execution plane** — isolated tenant/job sandboxes running canonical
   CACE science/AI/native workloads;
4. **durable data plane** — tenant-scoped databases/object storage/evidence;
5. **isolated proof plane** — exact-head formal qualification separate from
   ordinary customer workers.

This gives the user an instance that feels continuously available while allowing
compute to scale, move, restart, or hibernate behind the scenes.

## Ranked alternatives

### Rank 2 — Per-tenant container namespace / pod set

Good for larger Researcher/Enterprise tenants that need more continuously warm
services and stronger network/resource isolation. Costs more idle capacity than
Rank 1.

### Rank 3 — Per-tenant microVM

Use a microVM-like boundary for higher-risk native/AI workloads or an enterprise
isolation tier. Stronger kernel separation, but more expensive and operationally
complex.

### Rank 4 — Shared worker pool with hard per-job sandbox

Best density for short batch work. Useful as one execution class inside Rank 1,
but should not be the only isolation boundary for every workload.

### Rank 5 — Full always-on VM per user

Strong isolation and simple to reason about, but too expensive/inefficient as
the default. Keep as an optional enterprise/dedicated deployment tier.

## Logical instance rather than source clone

Per-user cloning of the application source should be avoided.

A user instance is represented by a durable instance manifest containing things
such as:

- account/profile and entitlement;
- experiments/canvas state;
- results/evidence/provenance;
- optional protein library;
- local-AI pairings;
- Math Coin wallet identity/capabilities;
- feature flags, quotas and preferences;
- research ideas.

The executable CACE code comes from one immutable release identity. This keeps
every user on a known version and allows safe rolling upgrades.

## User network / local AI connectivity

Users may have CACE/local-AI instances on their own home, lab or office networks.

Those local instances should initiate an **outbound** authenticated connection
to the CACE gateway/broker. CACE should not require the customer to expose an
inbound port through their router/firewall.

Flow:

```
Local AI / local CACE
       |
       | outbound authenticated connection
       v
CACE public gateway / pairing broker
       |
       | tenant-authorized private routing
       v
user's durable CACE instance / economy services
```

The existing directional Receive/Outgoing pairing-code design binds the local
agent to the user's tenant. Reconnect/resume heartbeats keep the link persistent.

## Always-up behavior

"Always up" should describe the **logical service**, not necessarily a dedicated
CPU/GPU process consuming resources forever.

Persistent:

- account/session/entitlement;
- experiment and canvas state;
- saved proteins/data;
- result/evidence/provenance;
- job state;
- local-AI link identity;
- user settings/help.

Elastic:

- CPU workers;
- GPU workers;
- local/model workers;
- rendering workers;
- large scientific jobs.

For interactive users a warm sandbox can stay ready. Idle sandboxes may suspend
or be replaced and then restore state on demand.

## Load balancing and fairness

Recommended request/job model:

- stateless web/API replicas behind a load balancer;
- authenticated tenant context injected server-side;
- durable tenant-aware queues;
- separate interactive and batch queues;
- weighted fair scheduling / starvation prevention;
- per-tenant CPU/GPU/job concurrency quotas;
- backpressure rather than unlimited queue growth;
- resource-class placement for CPU/GPU/high-memory/formal jobs;
- idempotent dispatch and resumable jobs where practical.

A heavy user must not be able to starve all other tenants.

## Tenant data isolation

Every tenant-owned object must carry an authoritative tenant identity.

Required controls:

- database row-level/tenant-filter enforcement server-side;
- tenant-scoped object storage prefixes/capabilities;
- tenant-scoped ephemeral worker credentials;
- cache keys that cannot expose private data across tenants;
- separate workspaces/mount namespaces;
- no client-selected arbitrary storage paths;
- backup/restore/export/delete scoped to the tenant;
- explicit collaboration is the only normal way to cross tenant boundaries.

Enterprise deployments may optionally move a tenant to dedicated database,
microVM or worker resources without changing CACE scientific semantics.

## Failure/recovery model

The service should survive:

- gateway replica loss;
- worker crash;
- node replacement;
- queue-worker restart;
- ordinary deploy/rolling upgrade;
- local-agent disconnect/reconnect.

Durable state belongs in replicated persistent stores rather than worker memory.
Workers should be replaceable.

## Production validation

Before calling multi-user support production grade, test:

1. many simultaneous browser/API users;
2. cross-tenant read/write attacks;
3. cache/storage namespace leaks;
4. sandbox/network escape attempts;
5. one tenant flooding CPU/GPU/queue;
6. worker destruction mid-job;
7. idle suspend/resume;
8. local-agent reconnect without inbound firewall access;
9. rolling release upgrade;
10. tenant backup/export/delete;
11. account/trial uniqueness under concurrent signup attempts;
12. identical scientific/evidence behavior before and after load balancing.

Machine-readable policy: `CACE_MULTI_TENANT_POLICY.json`.
