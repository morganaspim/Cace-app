from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class DeviceSelection:
    requested: str
    actual: str
    backend: str
    gpu_available: bool
    reason: str = ""

class DeviceManager:
    """Selects CPU/GPU without making GPU a correctness dependency."""
    @staticmethod
    def gpu_available() -> bool:
        try:
            import cupy as cp
            return cp.cuda.runtime.getDeviceCount() > 0
        except Exception:
            return False

    @classmethod
    def select(cls, gpu_enabled: bool, supports_gpu: bool) -> DeviceSelection:
        available = cls.gpu_available()
        if gpu_enabled and supports_gpu and available:
            return DeviceSelection("gpu", "gpu", "cupy", True)
        if gpu_enabled and not supports_gpu:
            return DeviceSelection("gpu", "cpu", "numpy", available, "module does not advertise GPU support")
        if gpu_enabled and not available:
            return DeviceSelection("gpu", "cpu", "numpy", False, "GPU backend unavailable; deterministic CPU fallback")
        return DeviceSelection("cpu", "cpu", "numpy", available)

    @staticmethod
    def array_module(selection: DeviceSelection):
        if selection.actual == "gpu":
            import cupy
            return cupy
        import numpy
        return numpy

    @staticmethod
    def to_host(value: Any) -> Any:
        try:
            import cupy as cp
            if isinstance(value, cp.ndarray):
                return cp.asnumpy(value)
            if isinstance(value, cp.generic):
                return value.item()
        except Exception:
            pass
        return value
