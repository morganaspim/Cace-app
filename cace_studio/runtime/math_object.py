from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Iterable

from .hashing import stable_hash


@dataclass(frozen=True, order=True)
class CliffordSignature:
    """Signature Cl(p,q,r) for the canonical geometric-algebra domain."""

    p: int
    q: int
    r: int = 0

    def __post_init__(self) -> None:
        if any(not isinstance(v, int) or v < 0 for v in (self.p, self.q, self.r)):
            raise ValueError("Clifford signature entries must be non-negative integers")
        if self.p + self.q + self.r <= 0:
            raise ValueError("Clifford algebra must have positive dimension")

    @property
    def dimension(self) -> int:
        return self.p + self.q + self.r


@dataclass(frozen=True, order=True)
class SparseTerm:
    """One sparse multivector coefficient keyed by a canonical blade bit-mask."""

    blade_mask: int
    coefficient: float

    def __post_init__(self) -> None:
        if not isinstance(self.blade_mask, int) or self.blade_mask < 0:
            raise ValueError("blade_mask must be a non-negative integer")
        if not math.isfinite(float(self.coefficient)):
            raise ValueError("multivector coefficients must be finite")


@dataclass(frozen=True)
class SparseMultivector:
    signature: CliffordSignature
    terms: tuple[SparseTerm, ...] = ()

    def __post_init__(self) -> None:
        limit = 1 << self.signature.dimension
        if any(term.blade_mask >= limit for term in self.terms):
            raise ValueError("blade mask exceeds Clifford algebra dimension")
        merged: dict[int, float] = {}
        for term in self.terms:
            merged[term.blade_mask] = merged.get(term.blade_mask, 0.0) + float(term.coefficient)
        canonical = tuple(
            SparseTerm(mask, coefficient)
            for mask, coefficient in sorted(merged.items())
            if coefficient != 0.0
        )
        object.__setattr__(self, "terms", canonical)

    @classmethod
    def from_pairs(
        cls,
        signature: CliffordSignature,
        pairs: Iterable[tuple[int, float]],
    ) -> "SparseMultivector":
        return cls(signature=signature, terms=tuple(SparseTerm(mask, coeff) for mask, coeff in pairs))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "signature": [self.signature.p, self.signature.q, self.signature.r],
            "terms": [[term.blade_mask, term.coefficient] for term in self.terms],
        }


class RepresentationKind(str, Enum):
    SPARSE_MULTIVECTOR = "sparse_multivector"
    GA_ROTOR = "ga_rotor"
    MATRIX_SO3 = "matrix_so3"
    QUATERNION_H1 = "quaternion_h1"
    SPINOR = "spinor"


class DisplayViewKind(str, Enum):
    CARTESIAN = "cartesian"
    POLAR = "polar"
    HEX_AXIAL = "hex_axial"
    HONEYCOMB = "honeycomb"
    EISENSTEIN = "eisenstein_omega"
    PROJECTIVE = "projective"
    CONFORMAL = "conformal"


@dataclass(frozen=True)
class DisplayState:
    """Pure presentation state.

    It is intentionally excluded from MathObject.semantic_sha256(). Changing
    Cartesian/honeycomb/etc. views therefore cannot mutate mathematical identity.
    """

    view: DisplayViewKind = DisplayViewKind.CARTESIAN
    scale: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError("display scale must be finite and positive")
        if not math.isfinite(self.origin_x) or not math.isfinite(self.origin_y):
            raise ValueError("display origin must be finite")


@dataclass(frozen=True)
class MathObject:
    """Canonical coordinateless mathematical object.

    `canonical` is the semantic sparse geometric-algebra value. Canvas position,
    view basis, zoom, and other display coordinates live outside this object.
    """

    object_id: str
    kind: str
    canonical: SparseMultivector
    units: str = "dimensionless"
    semantic_metadata: tuple[tuple[str, str], ...] = ()
    provenance_parent_hashes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.object_id or self.object_id != self.object_id.strip():
            raise ValueError("object_id must be a non-empty canonical string")
        if not self.kind or not self.kind.strip():
            raise ValueError("kind must be non-empty")
        if not self.units or not self.units.strip():
            raise ValueError("units must be non-empty")
        if len({key for key, _ in self.semantic_metadata}) != len(self.semantic_metadata):
            raise ValueError("semantic_metadata keys must be unique")

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "schema": "cace-math-object-v1",
            "object_id": self.object_id,
            "kind": self.kind,
            "canonical": self.canonical.canonical_payload(),
            "units": self.units,
            "semantic_metadata": list(sorted(self.semantic_metadata)),
            "provenance_parent_hashes": list(self.provenance_parent_hashes),
        }

    def semantic_sha256(self) -> str:
        return stable_hash(self.semantic_payload(), algorithm="sha256")


@dataclass(frozen=True)
class RepresentationEnvelope:
    """A computational representation bound to one immutable MathObject identity."""

    math_object_sha256: str
    kind: RepresentationKind
    payload: Any
    validation_sha256: str | None = None

    def __post_init__(self) -> None:
        if len(self.math_object_sha256) != 64:
            raise ValueError("math_object_sha256 must be a SHA-256 hex digest")


def project_xy(x: float, y: float, display: DisplayState) -> tuple[float, float]:
    """Project a 2-D Euclidean render adapter into the selected display basis.

    This function changes only presentation coordinates. The underlying MathObject
    is never passed to or mutated by it.
    """

    if not all(math.isfinite(v) for v in (x, y)):
        raise ValueError("render adapter coordinates must be finite")
    x = (x - display.origin_x) / display.scale
    y = (y - display.origin_y) / display.scale

    if display.view in {DisplayViewKind.CARTESIAN, DisplayViewKind.PROJECTIVE, DisplayViewKind.CONFORMAL}:
        return x, y
    if display.view is DisplayViewKind.POLAR:
        return math.hypot(x, y), math.atan2(y, x)
    if display.view in {DisplayViewKind.HEX_AXIAL, DisplayViewKind.HONEYCOMB}:
        # Continuous axial coordinates; snapping/tiling is a separate view operation.
        q = (math.sqrt(3.0) / 3.0) * x - (1.0 / 3.0) * y
        r = (2.0 / 3.0) * y
        return q, r
    if display.view is DisplayViewKind.EISENSTEIN:
        # z = a + b*omega, omega = -1/2 + i*sqrt(3)/2
        b = 2.0 * y / math.sqrt(3.0)
        a = x + 0.5 * b
        return a, b
    raise ValueError(f"unsupported display view: {display.view}")
