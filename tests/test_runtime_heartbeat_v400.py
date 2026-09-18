from cace_studio.runtime.heartbeat import (
    CellState,
    HeartbeatCell,
    HeartbeatEdge,
    HeartbeatMode,
    HeartbeatPolicy,
    HeartbeatScheduler,
)


def _scheduler():
    scheduler = HeartbeatScheduler(master_seed="test-seed", hash_algorithm="sha256")
    scheduler.add_cell(HeartbeatCell("a", HeartbeatPolicy(HeartbeatMode.PERIODIC, period_ticks=2), state=CellState.READY))
    scheduler.add_cell(HeartbeatCell("b", HeartbeatPolicy(HeartbeatMode.EVENT), state=CellState.PASS))
    scheduler.add_cell(HeartbeatCell("c", HeartbeatPolicy(HeartbeatMode.CONDITIONAL, condition_name="stable"), state=CellState.PASS))
    scheduler.add_edge(HeartbeatEdge("a", "b"))
    scheduler.add_edge(HeartbeatEdge("b", "c"))
    scheduler.assert_acyclic()
    return scheduler


def test_hash_bounded_propagation_stops_when_output_hash_is_equal():
    scheduler = _scheduler()
    first = scheduler.mark_output("a", {"invariant": 7}, tick=2)
    assert first.changed is True
    assert first.stale_cells == ("b", "c")

    scheduler.set_state("b", CellState.PASS)
    scheduler.set_state("c", CellState.PASS)
    second = scheduler.mark_output("a", {"invariant": 7}, tick=4)
    assert second.changed is False
    assert second.suppressed_by_equal_hash is True
    assert scheduler.cells["b"].state is CellState.PASS
    assert scheduler.cells["c"].state is CellState.PASS


def test_multirate_modes_respect_dependencies_and_event_queue():
    scheduler = _scheduler()
    assert scheduler.due_cells(tick=2) == ("a",)
    scheduler.mark_output("a", {"x": 1}, tick=2)
    scheduler.set_state("b", CellState.READY)
    # event from a can make b runnable because a is valid
    assert scheduler.due_cells(tick=3) == ("b",)
    scheduler.mark_output("b", {"x": 2}, tick=3)
    scheduler.set_state("c", CellState.READY)
    assert scheduler.due_cells(tick=3, conditions={"stable": True}) == ("c",)
