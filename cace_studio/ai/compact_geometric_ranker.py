from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


FEATURE_NAMES = (
    "user_relevance",
    "workflow_coverage",
    "typed_connection_fraction",
    "invariant_preservation",
    "symmetry_reduction",
    "geometric_structure",
    "novelty",
    "mastery_frontier",
    "proof_alignment",
    "resource_headroom",
    "sparsity",
    "composition_depth_fit",
)


@dataclass(frozen=True)
class GeometricCandidateFeatures:
    """Small normalized feature vector for advisory experiment ranking.

    Values are expected in [0, 1].  The ranker has no evidence authority and
    never creates scientific/proof status.
    """

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.values) != len(FEATURE_NAMES):
            raise ValueError(
                f"expected {len(FEATURE_NAMES)} features, got {len(self.values)}"
            )
        for value in self.values:
            if not np.isfinite(value) or not 0.0 <= float(value) <= 1.0:
                raise ValueError("ranker features must be finite values in [0,1]")

    @classmethod
    def from_mapping(cls, mapping: dict[str, float]) -> "GeometricCandidateFeatures":
        unknown = sorted(set(mapping) - set(FEATURE_NAMES))
        missing = sorted(set(FEATURE_NAMES) - set(mapping))
        if unknown or missing:
            raise ValueError(f"feature keys mismatch missing={missing} extra={unknown}")
        return cls(tuple(float(mapping[name]) for name in FEATURE_NAMES))

    def array(self) -> np.ndarray:
        return np.asarray(self.values, dtype=np.float32)


class CompactGeometricRanker:
    """Tiny local MLP used to rank already-valid experiment candidates.

    Architecture: 12 -> 16 -> 8 -> 4 -> 1 with tanh activations.
    The model is intentionally tiny (~385 scalar parameters) so the local LLM
    remains the language/planning component while this network cheaply learns
    geometric/curriculum ranking preferences.

    It is advisory only. Candidate graphs must still pass the Qualified
    Capability Registry and canonical GraphExecutor validation.
    """

    layer_sizes = (len(FEATURE_NAMES), 16, 8, 4, 1)

    def __init__(self, *, seed: int = 2026) -> None:
        rng = np.random.default_rng(seed)
        self.weights: list[np.ndarray] = []
        self.biases: list[np.ndarray] = []
        for fan_in, fan_out in zip(self.layer_sizes, self.layer_sizes[1:]):
            scale = np.sqrt(2.0 / max(1, fan_in + fan_out))
            self.weights.append(
                rng.normal(0.0, scale, size=(fan_out, fan_in)).astype(np.float32)
            )
            self.biases.append(np.zeros((fan_out,), dtype=np.float32))

    @property
    def parameter_count(self) -> int:
        return int(
            sum(weight.size for weight in self.weights)
            + sum(bias.size for bias in self.biases)
        )

    @property
    def float32_size_bytes(self) -> int:
        return self.parameter_count * 4

    def _forward(self, x: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
        if x.ndim == 1:
            x = x.reshape(1, -1)
        if x.shape[1] != self.layer_sizes[0]:
            raise ValueError("unexpected ranker feature width")

        activations = [x.astype(np.float32, copy=False)]
        preactivations: list[np.ndarray] = []
        current = activations[0]
        for index, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            z = current @ weight.T + bias
            preactivations.append(z)
            if index == len(self.weights) - 1:
                current = z
            else:
                current = np.tanh(z)
            activations.append(current)
        return activations, preactivations

    def score_many(
        self,
        candidates: Sequence[GeometricCandidateFeatures],
    ) -> np.ndarray:
        if not candidates:
            return np.zeros((0,), dtype=np.float32)
        x = np.stack([candidate.array() for candidate in candidates], axis=0)
        activations, _ = self._forward(x)
        return activations[-1][:, 0].astype(np.float32)

    def score(self, candidate: GeometricCandidateFeatures) -> float:
        return float(self.score_many([candidate])[0])

    def rank(
        self,
        candidates: Sequence[GeometricCandidateFeatures],
    ) -> tuple[int, ...]:
        scores = self.score_many(candidates)
        return tuple(
            int(index)
            for index in sorted(
                range(len(scores)),
                key=lambda idx: (-float(scores[idx]), idx),
            )
        )

    def fit_pairwise(
        self,
        preferred: Sequence[GeometricCandidateFeatures],
        rejected: Sequence[GeometricCandidateFeatures],
        *,
        epochs: int = 80,
        learning_rate: float = 0.015,
        l2: float = 1e-4,
    ) -> list[float]:
        """Train with pairwise logistic loss using tiny full-batch gradients.

        Each preferred[i] should outrank rejected[i]. This is intended for local
        curriculum/feedback training, not proof/evidence creation.
        """
        if len(preferred) != len(rejected) or not preferred:
            raise ValueError("preferred and rejected must be equal non-zero length")
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if l2 < 0:
            raise ValueError("l2 must be non-negative")

        x_pos = np.stack([item.array() for item in preferred], axis=0)
        x_neg = np.stack([item.array() for item in rejected], axis=0)
        history: list[float] = []

        for _ in range(epochs):
            a_pos, z_pos = self._forward(x_pos)
            a_neg, z_neg = self._forward(x_neg)
            s_pos = a_pos[-1][:, 0]
            s_neg = a_neg[-1][:, 0]
            diff = s_pos - s_neg

            # softplus(-diff)
            loss = np.logaddexp(0.0, -diff).mean()
            loss += 0.5 * l2 * sum(float(np.sum(w * w)) for w in self.weights)
            history.append(float(loss))

            # dL/ddiff = -sigmoid(-diff) / n
            grad_diff = (-1.0 / (1.0 + np.exp(diff))) / len(diff)
            grad_pos = grad_diff.reshape(-1, 1).astype(np.float32)
            grad_neg = (-grad_diff).reshape(-1, 1).astype(np.float32)

            gw = [np.zeros_like(w) for w in self.weights]
            gb = [np.zeros_like(b) for b in self.biases]

            def backprop(
                activations: list[np.ndarray],
                preactivations: list[np.ndarray],
                grad: np.ndarray,
            ) -> None:
                current_grad = grad
                for layer in range(len(self.weights) - 1, -1, -1):
                    gw[layer][...] += current_grad.T @ activations[layer]
                    gb[layer][...] += current_grad.sum(axis=0)
                    if layer:
                        propagated = current_grad @ self.weights[layer]
                        tanh_z = np.tanh(preactivations[layer - 1])
                        current_grad = propagated * (1.0 - tanh_z * tanh_z)

            backprop(a_pos, z_pos, grad_pos)
            backprop(a_neg, z_neg, grad_neg)

            for index in range(len(self.weights)):
                gw[index] += l2 * self.weights[index]
                self.weights[index] -= learning_rate * gw[index]
                self.biases[index] -= learning_rate * gb[index]

        return history

    def to_dict(self) -> dict:
        return {
            "schema": "cace-compact-geometric-ranker-v1",
            "feature_names": list(FEATURE_NAMES),
            "layer_sizes": list(self.layer_sizes),
            "parameter_count": self.parameter_count,
            "float32_size_bytes": self.float32_size_bytes,
            "weights": [weight.tolist() for weight in self.weights],
            "biases": [bias.tolist() for bias in self.biases],
            "evidence_authority": False,
            "proof_effect": "none",
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CompactGeometricRanker":
        if payload.get("schema") != "cace-compact-geometric-ranker-v1":
            raise ValueError("unsupported ranker schema")
        if tuple(payload.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("ranker feature contract mismatch")
        if tuple(payload.get("layer_sizes", ())) != cls.layer_sizes:
            raise ValueError("ranker layer contract mismatch")
        model = cls(seed=0)
        weights = [np.asarray(item, dtype=np.float32) for item in payload["weights"]]
        biases = [np.asarray(item, dtype=np.float32) for item in payload["biases"]]
        if [tuple(x.shape) for x in weights] != [tuple(x.shape) for x in model.weights]:
            raise ValueError("ranker weight shapes mismatch")
        if [tuple(x.shape) for x in biases] != [tuple(x.shape) for x in model.biases]:
            raise ValueError("ranker bias shapes mismatch")
        model.weights = weights
        model.biases = biases
        return model

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), separators=(",", ":")), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "CompactGeometricRanker":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
