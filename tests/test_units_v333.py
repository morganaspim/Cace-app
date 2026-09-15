import pytest

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import registry_contract_fingerprint
from cace_studio.core.types import (
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    port_connection_error,
    units_compatible,
)


class MeterSource(Module):
    metadata = ModuleMetadata(
        "test.units.meter_source",
        "Meter Source",
        "1.0.0",
        "Tests",
        "Unit-aware source.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("x", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {"x": 1.0}


class MeterSink(Module):
    metadata = ModuleMetadata(
        "test.units.meter_sink",
        "Meter Sink",
        "1.0.0",
        "Tests",
        "Matching unit sink.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number", unit="m"),)
    outputs = (PortSpec("y", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {"y": inputs["x"]}


class SecondSink(Module):
    metadata = ModuleMetadata(
        "test.units.second_sink",
        "Second Sink",
        "1.0.0",
        "Tests",
        "Mismatched unit sink.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number", unit="s"),)

    def execute(self, inputs, params, ctx):
        return {}


class LegacySink(Module):
    metadata = ModuleMetadata(
        "test.units.legacy_sink",
        "Legacy Sink",
        "1.0.0",
        "Tests",
        "Legacy unspecified-unit sink.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number"),)

    def execute(self, inputs, params, ctx):
        return {}


def _registry(*classes):
    registry = ModuleRegistry()
    for cls in classes:
        registry.register(cls)
    return registry


def _connected(source_cls, sink_cls):
    return Experiment(
        name="unit-test",
        nodes=[
            Node("source", source_cls.metadata.module_id),
            Node("sink", sink_cls.metadata.module_id),
        ],
        edges=[Edge("source", "x", "sink", "x")],
    )


def test_unit_contract_validation_and_compatibility():
    assert units_compatible(None, None) is True
    assert units_compatible("m", "m") is True
    assert units_compatible("m", "s") is False
    assert units_compatible("m", None) is False
    assert units_compatible(None, "m") is False

    assert port_connection_error(PortSpec("x", "number", unit="m"), PortSpec("x", "number", unit="m")) is None
    assert "unit mismatch" in port_connection_error(
        PortSpec("x", "number", unit="m"),
        PortSpec("x", "number", unit="s"),
    )
    assert "type mismatch" in port_connection_error(
        PortSpec("x", "number", unit="m"),
        PortSpec("x", "text", unit="m"),
    )


@pytest.mark.parametrize("unit", ["", " m", "m ", "m\n"])
def test_units_must_be_canonical_strings(unit):
    with pytest.raises(ValueError):
        PortSpec("x", "number", unit=unit)
    with pytest.raises(ValueError):
        ParameterSpec("p", "number", unit=unit)


def test_matching_unit_graph_executes():
    registry = _registry(MeterSource, MeterSink)
    result = GraphExecutor(registry).run(_connected(MeterSource, MeterSink))
    assert result.outputs["sink"]["y"] == 1.0


def test_mismatched_unit_graph_fails_before_execution():
    registry = _registry(MeterSource, SecondSink)
    with pytest.raises(ValidationError, match="unit mismatch: m -> s"):
        GraphExecutor(registry).run(_connected(MeterSource, SecondSink))


def test_explicit_unit_to_legacy_unspecified_unit_fails_closed():
    registry = _registry(MeterSource, LegacySink)
    with pytest.raises(ValidationError, match="unit mismatch: m -> <unspecified>"):
        GraphExecutor(registry).run(_connected(MeterSource, LegacySink))


def test_unit_metadata_changes_module_contract_fingerprint():
    class Unitless(Module):
        metadata = ModuleMetadata(
            "test.units.contract",
            "Contract",
            "1.0.0",
            "Tests",
            "Contract fingerprint test.",
            Maturity.EXPERIMENTAL,
        )
        outputs = (PortSpec("x", "number"),)
        parameters = (ParameterSpec("scale", "number", 1.0),)

        def execute(self, inputs, params, ctx):
            return {"x": params["scale"]}

    class Unitful(Unitless):
        outputs = (PortSpec("x", "number", unit="m"),)
        parameters = (ParameterSpec("scale", "number", 1.0, unit="m"),)

    left = _registry(Unitless)
    right = _registry(Unitful)
    assert registry_contract_fingerprint(left) != registry_contract_fingerprint(right)
