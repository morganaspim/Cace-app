from __future__ import annotations

from cace_studio.core.compute_economy import (
    ComputeBid,
    ComputeCreditEconomy,
    HostMeasuredOutcome,
    ResourceHeadroom,
)


def test_spare_capacity_mints_non_monetary_credits_and_allocates_deterministically():
    a = ComputeCreditEconomy(mint_rate=10.0)
    b = ComputeCreditEconomy(mint_rate=10.0)
    headroom = ResourceHeadroom(1.0, 0.0, 1.0)
    bids = (
        ComputeBid("t-low", "n1", 1.0, 0.2, 0.0, "s1"),
        ComputeBid("t-high", "n1", 1.0, 1.0, 0.5, "s1"),
    )
    left = a.tick(("n1",), headroom, bids)
    right = b.tick(("n1",), headroom, bids)
    assert left == right
    assert left.minted > 0
    assert left.allocations
    assert left.allocations[0].task_id == "t-high"
    assert "non-monetary" in left.note


def test_no_spare_capacity_mints_no_new_credit():
    economy = ComputeCreditEconomy()
    tick = economy.tick(("n1",), ResourceHeadroom(0.0, 0.0, 0.0))
    assert tick.minted == 0.0
    assert tick.wallet_credits["n1"] == 0.0


def test_ai_self_report_cannot_settle_strategy():
    try:
        HostMeasuredOutcome("t", "s", 1.0, 1.0, 1.0, True, source="ai-self-report")
    except ValueError as exc:
        assert "host executor" in str(exc)
    else:
        raise AssertionError("AI self-report must not enter scheduling reward statistics")


def test_host_outcomes_rank_measured_strategy_efficiency_only():
    economy = ComputeCreditEconomy()
    economy.settle(HostMeasuredOutcome("a", "fast", 1.0, 2.0, 0.1, True))
    economy.settle(HostMeasuredOutcome("b", "slow", 1.0, 1.0, 10.0, True))
    assert economy.strategy_ranking()[0][0] == "fast"
    assert "verification" in economy.snapshot()["role"]
