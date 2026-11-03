# Oracle Always Free Resource Policy for CACE

Status: deployment/resource policy. Not a guarantee of Oracle availability.

Last checked: 2026-09-20.

Oracle's Always Free documentation currently describes Ampere A1 Compute free allocation equivalent to **2 OCPUs and 12 GB memory total** for Always Free tenancies, plus **200 GB total Always Free block-volume storage** in the home region.

Oracle also documents reclamation risk for idle Always Free compute instances.

CACE therefore treats the Oracle VM as a constrained scientific server, not unlimited cloud infrastructure.

## Deployment objective

Prefer one primary A1 VM using the available free allocation where capacity permits.

CACE must remain configurable for smaller allocations.

## Default CACE budget

Machine-readable defaults live in `ops/oracle_always_free_budget.json`.

Recommended starting operating envelope:

- reserve RAM for OS/reverse proxy/service overhead;
- no more than one heavy autonomous science worker concurrently by default;
- lightweight API/UI orchestration may coexist;
- Lean canonical qualification remains deliberately scheduled rather than competing with scientific workers;
- use cgroup/worker limits rather than relying on host-wide exhaustion.

## Memory policy

On a 12 GB A1 allocation, do not allocate all RAM to science workers.

Recommended initial partition:

- host/API/reverse proxy/cache reserve: ~3 GB;
- primary science worker hard ceiling: ~6 GB;
- remaining headroom: ~3 GB for process spikes, filesystem cache, and recovery.

Actual limits should be tightened by measured workload.

## CPU policy

With 2 OCPUs total:

- default heavy-science concurrency: 1;
- default worker CPU ceiling: approximately 1.5 cores;
- retain CPU for API, watchdog, reverse proxy, recovery, and OS;
- avoid concurrent Lean build + heavy scientific run unless explicitly scheduled.

## Storage policy

Always Free block storage is finite and includes boot volumes.

CACE should:

- keep repository/build caches bounded;
- rotate ordinary runtime logs;
- content-address and deduplicate scientific artifacts;
- retain proof artifacts according to proof/provenance policy;
- warn before storage pressure becomes critical;
- prefer external/versioned archival only when it remains within selected free-tier policy.

Suggested storage pressure zones for the CACE-managed data area:

- GREEN < 60%;
- YELLOW 60–75%;
- RED 75–85%;
- HARD STOP for optional artifact growth > 85%.

Proof/evidence integrity must never be silently deleted to recover space.

## Free-tier protection

Do not automatically create paid OCI resources.

Do not silently:

- resize to paid shapes;
- add paid block volumes;
- enable paid managed services;
- provision extra workers outside free quotas.

Any paid-resource transition requires explicit operator action.

## Idle/reclamation awareness

Oracle documents that Always Free compute can be reclaimed when it meets its idle criteria over a sustained period.

CACE must therefore:

- persist source and important artifacts outside ephemeral process state;
- make VM recreation reproducible;
- keep deployment configuration in Git;
- expose health/readiness checks;
- treat VM disappearance as recoverable infrastructure failure, not scientific evidence loss.

CACE must not generate fake load merely to evade provider policy.

## Sources

- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm
