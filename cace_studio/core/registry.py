from __future__ import annotations

from .module import Module


class ModuleRegistry:
    def __init__(self) -> None:
        self._types: dict[str, type[Module]] = {}

    def register(self, cls: type[Module]) -> None:
        if not isinstance(cls, type) or not issubclass(cls, Module):
            raise TypeError("registered module must be a Module subclass")
        metadata = getattr(cls, "metadata", None)
        module_id = getattr(metadata, "module_id", None)
        if not isinstance(module_id, str) or not module_id.strip():
            raise ValueError("registered module must declare a non-empty metadata.module_id")
        if module_id != module_id.strip():
            raise ValueError("module id must not contain leading or trailing whitespace")
        if module_id in self._types:
            raise ValueError(f"duplicate module id: {module_id}")
        self._types[module_id] = cls

    def create(self, module_id: str) -> Module:
        try:
            return self._types[module_id]()
        except KeyError as e:
            raise KeyError(f"unknown module: {module_id}") from e

    def classes(self) -> list[type[Module]]:
        return list(self._types.values())

    def contains(self, module_id: str) -> bool:
        return module_id in self._types
