# Rootless network namespace link inspection defect (2026-11-22)

## Scope and evidence

An OCI aarch64 UID 1000 integration run [45017735251](https://github.com/morganaspim/Cace-app/actions/runs/45017735251) completed the 112 pinned native Studio tests but did **not** complete a fully isolated browser/server replay. Its `isolated-setup-result.json` reported `new namespace has unexpected network interface`; cleanup succeeded, but isolation acceptance remained false. The error occurred before browser and server testing in the isolated namespace, not as evidence of successful isolation.

A separately scoped rootless probe [45018076018](https://github.com/morganaspim/Cace-app/actions/runs/45018076018) measured `interfaces: ["lo"]` inside the child namespace, while an inherited `/sys/class/net` directory listed `["enp0s6","lo"]`. It also observed a private loopback socket round trip after dropping effective Linux capabilities to zero. This supports the narrow diagnosis: sysfs had not been remounted into the newly created network namespace. The raw sysfs list was not a valid current-namespace link enumeration. It does not establish unrestricted browser security, prevent every host access path, or qualify production.

## Root-cause repair and prevention

The two pinned scripts `ops/merlin_studio_validation/prepare_isolated_loopback.py` and `connected_browser_offline_recovery_isolated.py` now use `socket.if_nameindex()`, which queries link identities for the calling process's current network namespace. They still reject all names except `lo`, require distinct parent/child netns inode identities and the pinned UID map, verify the private `lo` interface is UP, and require zero effective capabilities, no-new-privileges, and no default IPv4 route. There is no permission weakening, installation, host network mutation or model inference.

Six additive, pinned `test_isolated_network_inventory.py` controls cover a misleading host-mounted sysfs directory, an extra in-namespace link, duplicate link names, duplicate indexes, missing links and invalid identifiers. [Run 45018170673](https://github.com/morganaspim/Cace-app/actions/runs/45018170673) **passed all six** of these controls, and left no installation, but separately failed a pre-existing synthetic-supervisor recovery case. Consequently that run is blocked, not a network-isolation acceptance.

The unrelated synthetic-supervisor test uses a 150 ms request timeout. The run expected `recovered` but recorded `escalate` for `test_hang_stops_then_next_health_check_restarts`, after 25 recovery and 9 protocol tests had passed. Earlier full 112-case runs passed. Hypothesis: cold-worker start / scheduler pressure competes with the shared 150 ms deadline. This is *not* yet established as root cause; preserve the failure and independently inspect timing before changing production logic or test expectations.

## Discriminating next gate

Run a fresh pinned 112-case native acceptance plus six interface controls, then start a private rootless `--user --map-current-user --net --keep-caps` namespace; activate only `lo` in that child; drop capabilities and set `no_new_privs`; demonstrate **genuine** Studio HTTP, three offline commands, preserved file/conversation, stale-token rejection after restart, and Chromium connected DOM/PNG with zero model calls. Verify cleanup. Any nonzero native failure, extra namespace interface, default route, privilege leak, missing UI/restart evidence or altered source pin must block.

This document records observations and the open gate, **not** approval to install, merge, deploy, call models, or promote Merlin production. The canonical Merlin master v6 retains its existing 45-task scope; applicable tasks remain open until original acceptance checks pass.
