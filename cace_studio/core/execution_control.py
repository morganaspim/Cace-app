from __future__ import annotations

from threading import Condition


class ExecutionControl:
    """Thread-safe cooperative pause/cancel control for graph execution.

    Checkpoints occur between modules. CACE deliberately does not attempt unsafe
    thread interruption inside an arbitrary scientific module. Pause/cancel
    requests therefore take effect at the next executor checkpoint.
    """

    def __init__(self) -> None:
        self._condition = Condition()
        self._paused = False
        self._cancelled = False

    @property
    def paused(self) -> bool:
        with self._condition:
            return self._paused

    @property
    def cancelled(self) -> bool:
        with self._condition:
            return self._cancelled

    def pause(self) -> bool:
        """Request a pause at the next module boundary.

        Returns false when cancellation has already made pausing meaningless.
        """
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

    def cancel(self) -> bool:
        """Cancel at the next module boundary and wake paused executors."""
        with self._condition:
            if self._cancelled:
                return False
            self._cancelled = True
            self._paused = False
            self._condition.notify_all()
            return True

    def wait_until_runnable(self) -> bool:
        """Block while paused; return false when cancellation is requested."""
        with self._condition:
            while self._paused and not self._cancelled:
                self._condition.wait()
            return not self._cancelled
