# Math Coin + Conway Heartbeat Economic City

Status: research/economic-system design. Not a live token, exchange, investment product, or proof/evidence mechanism.

Date: 2026-09-19

## 1. Purpose

Math Coin (ticker placeholder: MATH) is a scarce external **compute-right token** for CACE's Conway-heartbeat economic city.

It is deliberately separate from the existing internal heartbeat compute credits:

- internal credits are non-monetary scheduler state;
- MATH is a scarce market-facing compute-right;
- neither can alter scientific verification, theorem status, or proof evidence.

The economic city is a visual and executable simulation/market layer in which user agents, AI agents, compute providers, resource pools, and markets interact through heartbeat ticks.

## 2. Fixed supply

Constitutional supply invariant:

```
MAX_SUPPLY = 500_000_000_000 MATH
```

Rules:

1. all 500 billion MATH are accounted for at genesis;
2. runtime cannot mint above the fixed cap;
3. there is no mining reward;
4. there is no staking/block reward;
5. there is no heartbeat-per-tick issuance;
6. ordinary compute activity cannot create new MATH.

Supply states are therefore only:

```
vaulted + circulating + escrowed + burned = 500_000_000_000
```

Burned MATH is permanently outside spendable supply.

## 3. Decade vault

Most genesis MATH begins in an immutable long-horizon vault.

Minimum invariant:

```
initial_vault_balance > 250_000_000_000 MATH
```

Release policy:

- releases happen only at explicit 10-year boundaries;
- each authorized release is one discrete all-at-once tranche;
- no continuous emission curve;
- no AI-selected release timing;
- no emergency inflation path hidden in ordinary runtime code;
- tranche amounts are explicit versioned constitutional parameters.

A production design should commit the complete release table in advance, for example:

```
epoch 0  -> genesis circulating tranche
epoch 10 -> tranche A, released atomically
epoch 20 -> tranche B, released atomically
...
```

The user's idea fixes the cadence and fixed supply but does not yet specify exact tranche quantities, so CACE should not invent them.

## 4. Burn-to-compute

The core use rule is:

```
MATH reserve -> metered compute -> settlement -> irrevocable burn
```

A user/AI cannot simply declare that compute happened.

Safe sequence:

1. quote a compute job;
2. reserve the required MATH in escrow;
3. execute through a bounded compute provider;
4. measure actual eligible computation using host/provider telemetry;
5. verify the settlement record;
6. burn the settled MATH;
7. release any unused reserved amount;
8. issue a content-addressed burn receipt.

Cancelled or failed work does not produce a valid completed-compute burn receipt.

### Burn receipt

Each burn receipt should bind:

- job/task ID;
- payer capability/wallet ID;
- provider ID;
- quoted and settled compute units;
- unit-price rule/version;
- reserved MATH;
- burned MATH;
- refunded remainder;
- real-crypto settlement reference if used;
- exact software/model/resource identity where relevant;
- heartbeat tick/city district;
- timestamps/sequence;
- transaction/burn identity;
- content hash/signature.

Burn receipts are economic provenance, **not scientific proof**.

## 5. Why provider settlement is separate

If the buyer's MATH is burned, the same MATH cannot also be transferred to a compute seller.

Therefore use two legs:

```
buyer -> burn MATH for compute right
market/buyer -> compensate provider using allowed settlement asset
```

Possible settlement assets could include ordinary fiat rails, a supported real cryptocurrency, or another explicitly configured asset.

This preserves the user's burn rule without making compute providers work for zero compensation.

## 6. AI marketplace

AI agents may participate in the economic city, but they do not receive raw wallet keys.

Conceptual flow:

```
AI proposal
   |
capability policy
   |
budget / asset / exposure checks
   |
trade broker
   |
market / exchange adapter
   |
settlement
```

Mandatory controls:

- no private keys in model context;
- no arbitrary exchange API credentials in the scientific worker;
- per-agent MATH budget;
- per-agent real-crypto exposure ceiling;
- asset allowlist;
- venue/provider allowlist;
- rate limit;
- daily/epoch loss limit;
- explicit human-configurable kill switch;
- append-only decision and transaction log;
- deterministic request IDs;
- stale-price and replay rejection;
- AI cannot edit its own limits.

High-capability/superintelligence-class admission remains a separate gate. Enabling that gate must not automatically enable trading.

## 7. Conway heartbeat economic city

Each city tick can update several separate layers.

### Scientific layer

- canvas state;
- dependencies;
- experiments;
- proof/evidence state.

### Compute layer

- CPU/GPU/storage headroom;
- internal compute credits;
- job queues;
- compute providers;
- utilization.

### Economic layer

- MATH wallets;
- escrow;
- burn rate;
- vault state;
- order books/quotes;
- real-crypto settlement balances;
- provider revenue;
- compute demand.

### Agent layer

- research-interest heartbeat;
- bids;
- offers;
- compute requests;
- market proposals;
- strategy performance.

The layers may inform scheduling, but only the scientific verification system can determine scientific evidence status.

## 8. Economic gameplay

The city can make spare resources into an explicit strategy game:

- compute districts advertise spare capacity;
- AI/research agents bid for experiments;
- scarce MATH forces opportunity-cost decisions;
- successful compute consumes/burns the right;
- providers compete on latency, reliability, energy/resource cost, and available capacity;
- agents can rebalance between holding MATH, buying MATH, or postponing jobs;
- decade vault unlocks become rare macroeconomic events.

Research mode can simulate city economics with fake assets before any live-market adapter is enabled.

## 9. Supply observability

GUI should expose:

- max supply;
- vaulted;
- circulating;
- escrowed;
- burned;
- next decade release boundary;
- next tranche amount when constitutionally specified;
- compute burn per hour/day/epoch;
- cumulative compute purchased;
- average MATH per compute unit;
- provider settlement volume.

Conservation must be machine-checked:

```
vaulted + circulating + escrowed + burned == 500_000_000_000
```

Every economic state transition should fail closed if that invariant would be violated.

## 10. Market integrity research

Before live value is enabled, test the city under:

- sybil agents;
- wash trading;
- spoofed compute completion;
- fake providers;
- price manipulation;
- stale price feeds;
- oracle/provider failure;
- wallet/broker compromise;
- double-spend/replay;
- runaway recursive AI spending;
- collusion;
- decade-unlock liquidity shock;
- extreme burn-rate scenarios.

Run these first with simulated assets and adversarial agents.

## 11. Relationship to internal heartbeat credits

Internal CACE credits remain the fast scheduler.

A possible bridge is:

```
spare host resource
   -> internal credits
   -> local research scheduling

external/market compute demand
   -> MATH reserve
   -> purchased compute
   -> MATH burn
```

Do not automatically convert internal credits into MATH. That would accidentally turn an internal scheduler score into money issuance.

## 12. First implementation path

1. pure simulation ledger with fixed 500B conservation invariant;
2. immutable decade-vault schedule object;
3. escrow + burn receipt state machine;
4. fake-asset city exchange;
5. compute-provider marketplace simulator;
6. AI capability/budget broker using fake assets only;
7. adversarial market and runaway-spend tests;
8. GUI economic-city view;
9. independent security/accounting review;
10. only then consider optional real-crypto settlement adapters behind explicit user enablement.

No live token issuance or real-asset trading is required for the research simulator.
