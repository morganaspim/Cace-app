# CACE-KSEE Conway Economic City

Status: federated collaboration/orchestration contract. It is not proof,
verification, payment, banking, investment, or cryptocurrency authority.

## Activation rule

The Conway Economic City exists only when **two or more workspaces are explicitly
linked through an authorized collaboration link** and their local agents are
allowed to exchange bounded heartbeat packets.

A standalone workspace remains a local heartbeat field and does not enter the
city.

```text
Workspace A heartbeat ----\
                            -> linked collaboration -> Conway Economic City
Workspace B heartbeat ----/
```

## City metaphor

The city maps CACE orchestration concepts into a visible spatial/economic model:

- workspace / agent / module state -> cells/buildings;
- collaboration edges -> roads/contracts;
- heartbeat ticks -> clocks/activity;
- hashes -> identities;
- caches/artifacts -> warehouses;
- CPU/GPU capacity -> compute/electricity;
- bandwidth/latency -> transport pressure;
- uncertainty/error budgets -> risk/quality pressure;
- proof obligations -> permits that the economy cannot manufacture;
- scheduler -> traffic/resource controller;
- research interest -> exploratory activity gradients.

The visualization may be Conway/Life-inspired and emergent while remaining
deterministic/replayable from the heartbeat/resource event stream.

## Heartbeat federation

Canonical implementation:
`cace_studio/agent_runtime/conway_city.py`.

Each workspace sends a bounded envelope containing:

- workspace ID;
- collaboration-link ID;
- monotonic heartbeat sequence;
- existing CACE `AgentPerceptionPacket`;
- bounded resource state;
- collaboration role.

The city accepts a packet only when:

- the workspace belongs to the explicit collaboration link;
- the packet is newer than the previous packet from that workspace;
- the agent network mode is not `LOCAL_ZERO_CONTACT`.

A linked workspace cannot use the city to reach unrelated workspaces.

## Internal scheduler credits

Spare compute may produce bounded **scheduler credits**.

These are:

- internal;
- non-transferable outside the scheduling simulation;
- non-monetary;
- not cryptocurrency;
- not user balance or subscription credit;
- not proof/evidence currency;
- not permission or entitlement authority.

They exist only to model resource contribution and scheduling preferences inside
the Conway city.

The initial invariant is:

```text
0 <= scheduler_credits <= configured_cap
```

A high credit balance cannot turn an invalid graph into a valid graph, change a
failed verifier to PASS, promote a theorem, or grant a role.

## Scheduling

The city may recommend which **already-valid** work receives resources next,
using signals such as:

- unmet compute demand;
- resource pressure;
- research interest;
- latency/bandwidth pressure;
- available spare compute;
- bounded internal scheduler credits.

The recommendation is advisory/orchestration state only.

Scientific execution still passes through:

```text
Qualified Capability Registry
  -> typed graph validation
  -> CACE execution
  -> canonical verifiers/proof gates
```

## AI-to-AI heartbeat behavior

When connected workspaces opt into collaboration, local assistants may consume
the shared city heartbeat field as bounded context.

They may:

- notice that another workspace is active/blocked/stale;
- suggest complementary experiments;
- avoid duplicated expensive work;
- offer spare compute through the scheduler;
- share research-interest gradients;
- coordinate Grow exploration;
- animate cross-workspace activity in the city view.

They may not:

- exchange arbitrary shell access;
- bypass workspace membership roles;
- expose proprietary source merely because workspaces are linked;
- inherit another workspace's proof authority;
- mark another agent's claim verified;
- silently mutate another workspace;
- use the city as a payment or financial-trading mechanism.

## UI

When a collaboration link has at least two live heartbeat participants, expose a
**City** view/tab.

The view can animate:

- cells/buildings activating;
- roads brightening as heartbeat traffic flows;
- blocked/stale districts;
- verification activity;
- resource congestion;
- compute supply/demand;
- cache/warehouse activity;
- research-interest diffusion;
- Grow paths;
- collaborator presence.

The normal experiment canvas remains available. The city is an additional
orchestration view, not a replacement for the scientific graph.

## Security

Federated packets should contain only the bounded typed heartbeat/resource
contract required for coordination.

Do not federate:

- source files;
- private model weights unless explicitly shared;
- secrets/tokens;
- raw filesystem paths;
- arbitrary logs;
- proof-development internals;
- user data unrelated to the shared workspace.

Production transport follows `security/network_transport_policy.json`.

## Evidence rule

Every city snapshot carries:

```text
evidence_authority = false
proof_effect = none
promotion_authority = false
real_money_or_crypto_authority = false
```

This boundary is permanent unless a completely separate reviewed subsystem is
designed for another purpose.
