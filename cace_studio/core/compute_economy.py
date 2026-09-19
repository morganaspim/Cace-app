from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import os
from typing import Iterable, Sequence


def _unit_interval(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite in [0,1]")
    return value


@dataclass(frozen=True)
class ResourceHeadroom:
    cpu_idle_fraction: float
    gpu_idle_fraction: float = 0.0
    memory_free_fraction: float = 1.0
    measurement_note: str = ""

    def __post_init__(self) -> None:
        _unit_interval(self.cpu_idle_fraction, "cpu_idle_fraction")
        _unit_interval(self.gpu_idle_fraction, "gpu_idle_fraction")
        _unit_interval(self.memory_free_fraction, "memory_free_fraction")


def sample_host_headroom() -> ResourceHeadroom:
    """Best-effort, fail-closed host headroom estimate."""
    cpu_count = max(1, int(os.cpu_count() or 1))
    try:
        load1 = float(os.getloadavg()[0])
    except (AttributeError, OSError):
        return ResourceHeadroom(0.0, 0.0, 1.0, "CPU load unavailable; no research credits minted")
    cpu_idle = max(0.0, min(1.0, 1.0 - load1 / cpu_count))
    return ResourceHeadroom(
        cpu_idle_fraction=cpu_idle,
        gpu_idle_fraction=0.0,
        memory_free_fraction=1.0,
        measurement_note="1-minute host load estimate; GPU headroom unmeasured",
    )


@dataclass
class ComputeWallet:
    node_id: str
    credits: float = 0.0
    lifetime_earned: float = 0.0
    lifetime_spent: float = 0.0

    def credit(self, amount: float, *, cap: float) -> float:
        amount = max(0.0, float(amount))
        accepted = min(amount, max(0.0, float(cap) - self.credits))
        self.credits += accepted
        self.lifetime_earned += accepted
        return accepted

    def spend(self, amount: float) -> bool:
        amount = float(amount)
        if not isfinite(amount) or amount < 0.0:
            raise ValueError("credit spend must be finite and non-negative")
        if self.credits + 1e-12 < amount:
            return False
        self.credits -= amount
        self.lifetime_spent += amount
        return True


@dataclass(frozen=True)
class ComputeBid:
    task_id: str
    node_id: str
    cost: float
    utility: float
    urgency: float = 0.0
    strategy: str = "default"

    def __post_init__(self) -> None:
        for field_name in ("task_id", "node_id", "strategy"):
            value = str(getattr(self, field_name))
            if not value or value != value.strip():
                raise ValueError(f"{field_name} must be a non-empty canonical string")
        if not isfinite(float(self.cost)) or float(self.cost) <= 0.0:
            raise ValueError("bid cost must be finite and positive")
        if not isfinite(float(self.utility)) or float(self.utility) < 0.0:
            raise ValueError("bid utility must be finite and non-negative")
        _unit_interval(self.urgency, "urgency")


@dataclass(frozen=True)
class ComputeAllocation:
    task_id: str
    node_id: str
    strategy: str
    credits_spent: float
    rank_score: float


@dataclass(frozen=True)
class HostMeasuredOutcome:
    task_id: str
    strategy: str
    credits_spent: float
    useful_work: float
    latency_seconds: float
    completed: bool
    source: str = "host-executor"

    def __post_init__(self) -> None:
        if self.source != "host-executor":
            raise ValueError("economy outcomes must come from the host executor")
        if not isfinite(float(self.credits_spent)) or self.credits_spent < 0.0:
            raise ValueError("credits_spent must be finite and non-negative")
        if not isfinite(float(self.useful_work)) or self.useful_work < 0.0:
            raise ValueError("useful_work must be finite and non-negative")
        if not isfinite(float(self.latency_seconds)) or self.latency_seconds < 0.0:
            raise ValueError("latency_seconds must be finite and non-negative")


@dataclass
class StrategyStats:
    samples: int = 0
    completed: int = 0
    useful_work: float = 0.0
    credits_spent: float = 0.0
    latency_seconds: float = 0.0

    def record(self, outcome: HostMeasuredOutcome) -> None:
        self.samples += 1
        self.completed += int(outcome.completed)
        self.useful_work += outcome.useful_work
        self.credits_spent += outcome.credits_spent
        self.latency_seconds += outcome.latency_seconds

    @property
    def efficiency(self) -> float:
        if self.samples == 0 or self.credits_spent <= 0.0:
            return 0.0
        latency_penalty = 1.0 + self.latency_seconds / max(1.0, self.samples)
        completion_factor = self.completed / self.samples
        return completion_factor * self.useful_work / (self.credits_spent * latency_penalty)


@dataclass(frozen=True)
class EconomyTick:
    minted: float
    treasury: float
    allocations: tuple[ComputeAllocation, ...]
    wallet_credits: dict[str, float]
    note: str = "internal non-monetary research scheduling only; never verification evidence"


class ComputeCreditEconomy:
    """Bounded internal compute-credit game for autonomous research tasks."""

    def __init__(
        self,
        *,
        mint_rate: float = 8.0,
        max_treasury: float = 100.0,
        max_wallet: float = 20.0,
        stipend_fraction: float = 0.5,
    ) -> None:
        if mint_rate < 0 or max_treasury <= 0 or max_wallet <= 0:
            raise ValueError("economy limits must be positive")
        if not 0.0 <= stipend_fraction <= 1.0:
            raise ValueError("stipend_fraction must be in [0,1]")
        self.mint_rate = float(mint_rate)
        self.max_treasury = float(max_treasury)
        self.max_wallet = float(max_wallet)
        self.stipend_fraction = float(stipend_fraction)
        self.treasury = 0.0
        self.wallets: dict[str, ComputeWallet] = {}
        self.strategy_stats: dict[str, StrategyStats] = {}

    def register_nodes(self, node_ids: Iterable[str]) -> None:
        for node_id in sorted(set(str(value) for value in node_ids)):
            if node_id:
                self.wallets.setdefault(node_id, ComputeWallet(node_id))

    def _mint(self, headroom: ResourceHeadroom) -> float:
        weighted = (
            0.70 * headroom.cpu_idle_fraction
            + 0.20 * headroom.gpu_idle_fraction
            + 0.10 * headroom.memory_free_fraction
        )
        requested = self.mint_rate * weighted
        minted = min(requested, max(0.0, self.max_treasury - self.treasury))
        self.treasury += minted
        return minted

    def _distribute_stipend(self, minted: float) -> None:
        if not self.wallets or minted <= 0.0 or self.treasury <= 0.0:
            return
        pool = min(self.treasury, minted * self.stipend_fraction)
        per_wallet = pool / len(self.wallets)
        spent = 0.0
        for node_id in sorted(self.wallets):
            spent += self.wallets[node_id].credit(per_wallet, cap=self.max_wallet)
        self.treasury = max(0.0, self.treasury - spent)

    def _strategy_multiplier(self, strategy: str) -> float:
        stats = self.strategy_stats.get(strategy)
        if stats is None or stats.samples == 0:
            return 1.0
        return min(1.5, max(0.75, 1.0 + 0.25 * stats.efficiency))

    def tick(
        self,
        node_ids: Iterable[str],
        headroom: ResourceHeadroom,
        bids: Sequence[ComputeBid] = (),
    ) -> EconomyTick:
        self.register_nodes(node_ids)
        minted = self._mint(headroom)
        self._distribute_stipend(minted)
        ranked = []
        for bid in bids:
            if bid.node_id not in self.wallets:
                continue
            base = (bid.utility * (1.0 + 0.5 * bid.urgency)) / bid.cost
            ranked.append((base * self._strategy_multiplier(bid.strategy), bid))
        ranked.sort(key=lambda item: (-item[0], item[1].task_id, item[1].node_id))
        allocations = []
        seen_tasks = set()
        for score, bid in ranked:
            if bid.task_id in seen_tasks:
                continue
            if not self.wallets[bid.node_id].spend(bid.cost):
                continue
            seen_tasks.add(bid.task_id)
            allocations.append(
                ComputeAllocation(
                    task_id=bid.task_id,
                    node_id=bid.node_id,
                    strategy=bid.strategy,
                    credits_spent=float(bid.cost),
                    rank_score=float(score),
                )
            )
        return EconomyTick(
            minted=minted,
            treasury=self.treasury,
            allocations=tuple(allocations),
            wallet_credits={node_id: self.wallets[node_id].credits for node_id in sorted(self.wallets)},
        )

    def settle(self, outcome: HostMeasuredOutcome) -> None:
        self.strategy_stats.setdefault(outcome.strategy, StrategyStats()).record(outcome)

    def strategy_ranking(self) -> tuple[tuple[str, float], ...]:
        rows = [(name, stats.efficiency) for name, stats in self.strategy_stats.items()]
        rows.sort(key=lambda item: (-item[1], item[0]))
        return tuple(rows)

    def snapshot(self) -> dict:
        return {
            "schema": "cace.compute-economy.v1",
            "role": "internal non-monetary research scheduling only; never verification evidence",
            "treasury": self.treasury,
            "wallets": {
                node_id: {
                    "credits": wallet.credits,
                    "lifetime_earned": wallet.lifetime_earned,
                    "lifetime_spent": wallet.lifetime_spent,
                }
                for node_id, wallet in sorted(self.wallets.items())
            },
            "strategies": {
                name: {
                    "samples": stats.samples,
                    "completed": stats.completed,
                    "efficiency": stats.efficiency,
                }
                for name, stats in sorted(self.strategy_stats.items())
            },
        }
