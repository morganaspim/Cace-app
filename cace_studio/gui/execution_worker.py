from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QRunnable, Signal
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc


class ExecutionWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class ExecutionWorker(QRunnable):
    """Run one already-snapshotted CACE execution away from the GUI thread."""

    def __init__(self, execute_callable) -> None:
        super().__init__()
        self.execute_callable = execute_callable
        self.signals = ExecutionWorkerSignals()

    def run(self) -> None:  # pragma: no cover - exercised through GUI integration
        try:
            result = self.execute_callable()
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)
