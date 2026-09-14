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

@dataclass(frozen=True)
class PortSpec:
    name: str
    type_name: str = "any"
    required: bool = True

@dataclass(frozen=True)
class ParameterSpec:
    name: str
    type_name: str
    default: Any = None
    description: str = ""

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
