from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Mapping


class EvidenceKind(str, Enum):
    EXPERIMENTAL = "experimental"
    NUMERICAL = "numerical"
    SYMBOLIC = "symbolic"
    INTERVAL = "interval-certified"
    FORMAL = "formally-verified"


class Maturity(str, Enum):
    PROTOTYPE = "prototype"
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    PRODUCTION = "production"


def validate_unit(unit: str | None) -> str | None:
    """Validate canonical opaque unit metadata.

    CACE v3.33 does not perform automatic unit conversion. A non-null unit is a
    contract identifier (for example ``m``, ``s``, ``m/s`` or ``1``) and must be
    already canonical: non-empty, no leading/trailing whitespace, no controls.
    """
    if unit is None:
        return None
    if not isinstance(unit, str):
        raise TypeError("unit must be a string or None")
    if not unit or unit != unit.strip():
        raise ValueError("unit must be a non-empty canonical string without edge whitespace")
    if any(ord(char) < 32 or ord(char) == 127 for char in unit):
        raise ValueError("unit must not contain control characters")
    return unit


def units_compatible(source_unit: str | None, target_unit: str | None) -> bool:
    """Return whether a connection has an established exact unit match.

    Two legacy unspecified-unit ports remain compatible. Once either side opts
    into explicit units, both sides must declare the same canonical unit. This
    deliberately avoids implicit conversions or assumptions about an unknown
    legacy unit.
    """
    source = validate_unit(source_unit)
    target = validate_unit(target_unit)
    if source is None and target is None:
        return True
    return source is not None and source == target


@dataclass(frozen=True)
class PortSpec:
    name: str
    type_name: str = "any"
    required: bool = True
    unit: str | None = None

    def __post_init__(self) -> None:
        validate_unit(self.unit)


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    type_name: str
    default: Any = None
    description: str = ""
    unit: str | None = None

    def __post_init__(self) -> None:
        validate_unit(self.unit)


@dataclass
class ProofStatus:
    evidence: set[EvidenceKind] = field(default_factory=set)
    unit_tests: bool = False
    property_tests: bool = False
    regression_tests: bool = False
    documentation: bool = False
    benchmarked: bool = False
    formal_artifact: str | None = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = sorted(x.value for x in self.evidence)
        return d


@dataclass(frozen=True)
class ModuleMetadata:
    module_id: str
    name: str
    version: str
    category: str
    description: str
    maturity: Maturity = Maturity.PROTOTYPE
    assumptions: tuple[str, ...] = ()
