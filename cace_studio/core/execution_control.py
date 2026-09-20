from __future__ import annotations

from dataclasses import dataclass
import json
from threading import Condition
import time
from typing import Any, Callable


@dataclass(frozen=True)
class ExecutionLimits:
    """Cooperative executor limits enforced at module boundaries."""

    max_wall_seconds: float | None = None
    max_nodes: int | None = None
    max_output_bytes: int | None = None
    poll_seconds: float = 0.1

    def __post_init__(self) -> None:
        if self.max_wall_seconds is not None and self.max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be positive or None")
        if self.max_nodes is not None and self.max_nodes <= 0:
            raise ValueError("max_nodes must be positive or None")
        if self.max_output_bytes is not None and self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive or None")
        if self.poll_seconds <= 0:
            raise ValueError("poll_seconds must be positive")


ExternalStateProvider = Callable[[], str]


class ExecutionControl:
    """Thread-safe cooperative pause/cancel/budget control for graph execution.

    Checkpoints occur between modules. CACE deliberately does not attempt unsafe
    thread interruption inside an arbitrary scientific module. Pause/cancel and
    resource limits therefore take effect at the next executor checkpoint.
    """

    def __init__(
        self,
        *,
        limits: ExecutionLimits | None = None,
        external_state_provider: ExternalStateProvider | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._condition = Condition()
        self._paused = False
        self._cancelled = False
        self._stop_reason = ""
        self._limits = limits or ExecutionLimits()
        self._external_state_provider = external_state_provider
        self._clock = clock
        self._started = float(clock())
        self._nodes_completed = 0
        self._output_bytes = 0

    @property
    def paused(self) -> bool:
        with self._condition:
            return self._paused

    @property
    def cancelled(self) -> bool:
        with self._condition:
            return self._cancelled

    @property
    def stop_reason(self) -> str:
        with self._condition:
            return self._stop_reason

    @property
    def nodes_completed(self) -> int:
        with self._condition:
            return self._nodes_completed

    @property
    def output_bytes(self) -> int:
        with self._condition:
            return self._output_bytes

    def pause(self) -> bool:
        """Request a pause at the next module boundary."""
        with self._condition:
            if self._cancelled:
                return False
            self._paused = True
            return True

    def resume(self) -> bool:
        """Resume a paused run. Returns false after cancellation."""
        with self._condition:
            if self._cancelled:
                return False
            was_paused = self._paused
            self._paused = False
            self._condition.notify_all()
            return was_paused

    def cancel(self, reason: str = "cancelled") -> bool:
        """Cancel at the next module boundary and wake paused executors."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("cancel reason must be non-empty text")
        with self._condition:
            if self._cancelled:
                return False
            self._cancelled = True
            self._stop_reason = reason.strip()
            self._paused = False
            self._condition.notify_all()
            return True

    def _external_state(self) -> str:
        if self._external_state_provider is None:
            return "running"
        state = self._external_state_provider()
        if not isinstance(state, str):
            raise TypeError("external execution-control state must be text")
        normalized = state.strip().lower()
        if normalized not in {"running", "paused", "cancelled"}:
            raise ValueError(
                "external execution-control state must be running, paused, or cancelled"
            )
        return normalized

    def _check_limits_locked(self, *, include_node_limit: bool = True) -> None:
        if self._cancelled:
            return
        limits = self._limits
        if (
            limits.max_wall_seconds is not None
            and float(self._clock()) - self._started >= limits.max_wall_seconds
        ):
            self._cancelled = True
            self._stop_reason = "wall-time-budget"
        elif (
            include_node_limit
            and limits.max_nodes is not None
            and self._nodes_completed >= limits.max_nodes
        ):
            self._cancelled = True
            self._stop_reason = "node-budget"
        elif (
            limits.max_output_bytes is not None
            and self._output_bytes > limits.max_output_bytes
        ):
            self._cancelled = True
            self._stop_reason = "output-byte-budget"

    def wait_until_runnable(self) -> bool:
        """Wait through pause state and enforce external control/budgets."""
        with self._condition:
            while True:
                self._check_limits_locked()
                if self._cancelled:
                    return False
                state = self._external_state()
                if state == "cancelled":
                    self._cancelled = True
                    self._stop_reason = "externally-cancelled"
                    return False
                if not self._paused and state != "paused":
                    return True
                self._condition.wait(timeout=self._limits.poll_seconds)

    def record_node_output(self, output: Any) -> None:
        """Record one completed node and a deterministic JSON-size estimate."""
        try:
            encoded = json.dumps(
                output,
                sort_keys=True,
                separators=(",", ":"),
                default=repr,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            self.cancel("output-budget-accounting-failed")
            raise ValueError(
                "node output cannot be safely accounted for resource limits"
            ) from exc
        with self._condition:
            self._nodes_completed += 1
            self._output_bytes += len(encoded)
            self._check_limits_locked(include_node_limit=False)
            if self._cancelled:
                self._condition.notify_all()

    def interruption_reason(self, phase: str, node_id: str) -> str:
        with self._condition:
            reason = self._stop_reason or "cancelled"
        return f"{reason}-{phase}-node:{node_id}"
