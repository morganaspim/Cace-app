from __future__ import annotations

import pytest

from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import Maturity, ModuleMetadata


class _GoodModule(Module):
    metadata = ModuleMetadata(
        "test.registry.good",
        "Good",
        "1.0.0",
        "Test",
        "Valid registry fixture.",
        Maturity.EXPERIMENTAL,
    )

    def execute(self, inputs, params, ctx):
        return {}


class _BlankIdModule(Module):
    metadata = ModuleMetadata(
        "",
        "Blank",
        "1.0.0",
        "Test",
        "Invalid registry fixture.",
        Maturity.EXPERIMENTAL,
    )

    def execute(self, inputs, params, ctx):
        return {}


class _WhitespaceIdModule(Module):
    metadata = ModuleMetadata(
        " test.registry.space ",
        "Whitespace",
        "1.0.0",
        "Test",
        "Invalid registry fixture.",
        Maturity.EXPERIMENTAL,
    )

    def execute(self, inputs, params, ctx):
        return {}


def test_registry_accepts_module_subclass_once():
    registry = ModuleRegistry()
    registry.register(_GoodModule)
    assert registry.contains("test.registry.good")
    assert isinstance(registry.create("test.registry.good"), _GoodModule)
    with pytest.raises(ValueError, match="duplicate module id"):
        registry.register(_GoodModule)


def test_registry_rejects_non_module_class_before_mutation():
    registry = ModuleRegistry()

    class NotAModule:
        metadata = ModuleMetadata(
            "test.registry.bad",
            "Bad",
            "1.0.0",
            "Test",
            "Not a Module subclass.",
            Maturity.EXPERIMENTAL,
        )

    with pytest.raises(TypeError, match="Module subclass"):
        registry.register(NotAModule)  # type: ignore[arg-type]
    assert registry.classes() == []


def test_registry_rejects_blank_or_whitespace_module_ids():
    registry = ModuleRegistry()
    with pytest.raises(ValueError, match="non-empty"):
        registry.register(_BlankIdModule)
    with pytest.raises(ValueError, match="whitespace"):
        registry.register(_WhitespaceIdModule)
    assert registry.classes() == []
