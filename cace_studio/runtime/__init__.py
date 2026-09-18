"""CACE runtime architecture: coordinateless objects, heartbeats, sandboxes, and entitlements.

These modules are runtime/control infrastructure. They do not emit FORMAL evidence and
must not be treated as part of the Lean qualification boundary.
"""

from .math_object import (
    CliffordSignature,
    DisplayState,
    DisplayViewKind,
    MathObject,
    RepresentationEnvelope,
    RepresentationKind,
    SparseMultivector,
    SparseTerm,
)
from .heartbeat import (
    CellState,
    HeartbeatEdge,
    HeartbeatMode,
    HeartbeatPolicy,
    HeartbeatScheduler,
)
from .entitlement import (
    EntitlementExpired,
    EntitlementService,
    EntitlementStatus,
    EntitlementStore,
    LeaseSigner,
)

__all__ = [
    "CliffordSignature",
    "DisplayState",
    "DisplayViewKind",
    "MathObject",
    "RepresentationEnvelope",
    "RepresentationKind",
    "SparseMultivector",
    "SparseTerm",
    "CellState",
    "HeartbeatEdge",
    "HeartbeatMode",
    "HeartbeatPolicy",
    "HeartbeatScheduler",
    "EntitlementExpired",
    "EntitlementService",
    "EntitlementStatus",
    "EntitlementStore",
    "LeaseSigner",
]
