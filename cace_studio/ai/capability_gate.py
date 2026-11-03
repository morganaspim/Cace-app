from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class CapabilityTier(str, Enum):
    BOUNDED = "bounded"
    ADVANCED = "advanced"
    SUPERINTELLIGENCE_CLASS = "superintelligence-class"


@dataclass(frozen=True)
class AICapabilityManifest:
    provider_id: str
    model_id: str
    tier: CapabilityTier = CapabilityTier.BOUNDED
    requests_network: bool = False
    requests_self_modification: bool = False
    requests_worker_spawn: bool = False
    requests_evidence_mutation: bool = False
    requested_compute_credits: float = 0.0
    hidden_layers_exposed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id is required")
        if not isfinite(float(self.requested_compute_credits)) or self.requested_compute_credits < 0.0:
            raise ValueError("requested_compute_credits must be finite and non-negative")


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    reasons: tuple[str, ...]

    def require(self) -> None:
        if not self.allowed:
            raise PermissionError("; ".join(self.reasons))


@dataclass(frozen=True)
class AICapabilityPolicy:
    allow_superintelligence_class: bool = False
    allow_network: bool = False
    allow_self_modification: bool = False
    allow_worker_spawn: bool = False
    max_compute_credits: float = 20.0

    @classmethod
    def from_settings(cls, settings) -> "AICapabilityPolicy":
        return cls(
            allow_superintelligence_class=bool(
                getattr(settings, "allow_superintelligence_class_ai", False)
            ),
            allow_network=False,
            allow_self_modification=False,
            allow_worker_spawn=False,
            max_compute_credits=float(getattr(settings, "ai_max_compute_credits", 20.0)),
        )

    def admit(self, manifest: AICapabilityManifest) -> CapabilityDecision:
        reasons = []
        if (
            manifest.tier is CapabilityTier.SUPERINTELLIGENCE_CLASS
            and not self.allow_superintelligence_class
        ):
            reasons.append("superintelligence-class AI is disabled by the user capability gate")
        if manifest.requests_network and not self.allow_network:
            reasons.append("network authority is not allowed")
        if manifest.requests_self_modification and not self.allow_self_modification:
            reasons.append("self-modification is not allowed")
        if manifest.requests_worker_spawn and not self.allow_worker_spawn:
            reasons.append("worker spawning is not allowed")
        if manifest.requests_evidence_mutation:
            reasons.append("AI evidence/proof mutation is never allowed")
        if manifest.requested_compute_credits > self.max_compute_credits:
            reasons.append("requested AI compute budget exceeds the policy limit")
        return CapabilityDecision(not reasons, tuple(reasons))

    @property
    def interpretation(self) -> str:
        return (
            "This policy controls capabilities/resources and declared provider tiers. "
            "It is not a mathematical detector or proof of whether a model is superintelligent."
        )
