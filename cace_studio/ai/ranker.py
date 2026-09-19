from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np


@dataclass(frozen=True)
class RankerConfig:
    input_dim: int
    hidden_dim: int = 32
    learning_rate: float = 0.01
    l2: float = 1e-5
    seed: int = 0


class TinyResidualRanker:
    """Small two-hidden-layer residual MLP implemented with NumPy only."""

    def __init__(self, config: RankerConfig):
        if config.input_dim <= 0 or config.hidden_dim <= 0:
            raise ValueError("ranker dimensions must be positive")
        self.config = config
        rng = np.random.default_rng(config.seed)
        s1 = 1.0 / math.sqrt(config.input_dim)
        s2 = 1.0 / math.sqrt(config.hidden_dim)
        self.w1 = rng.normal(0.0, s1, (config.hidden_dim, config.input_dim))
        self.b1 = np.zeros(config.hidden_dim, dtype=np.float64)
        self.w2 = rng.normal(0.0, s2, (config.hidden_dim, config.hidden_dim))
        self.b2 = np.zeros(config.hidden_dim, dtype=np.float64)
        # Start neutral: before any CACE feedback the neural term contributes
        # exactly 0.5 rather than injecting arbitrary random ranking noise.
        self.w3 = np.zeros(config.hidden_dim, dtype=np.float64)
        self.b3 = 0.0

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0.0:
            z = math.exp(-value)
            return 1.0 / (1.0 + z)
        z = math.exp(value)
        return z / (1.0 + z)

    def _forward(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        x = np.asarray(features, dtype=np.float64)
        if x.shape != (self.config.input_dim,):
            raise ValueError(f"expected feature shape {(self.config.input_dim,)}, got {x.shape}")
        if not np.all(np.isfinite(x)):
            raise ValueError("ranker features must be finite")
        h1 = np.tanh(self.w1 @ x + self.b1)
        h2 = np.tanh(self.w2 @ h1 + self.b2)
        logit = float(self.w3 @ (h1 + h2) + self.b3)
        return x, h1, h2, logit

    def predict(self, features: np.ndarray) -> float:
        """Return a bounded utility score."""
        *_unused, logit = self._forward(features)
        return self._sigmoid(logit)

    def update(self, features: np.ndarray, target: float, *, weight: float = 1.0) -> float:
        """Perform one online weighted binary-cross-entropy update."""
        y = float(target)
        sample_weight = float(weight)
        if not 0.0 <= y <= 1.0:
            raise ValueError("target must be in [0,1]")
        if not math.isfinite(sample_weight) or sample_weight <= 0.0:
            raise ValueError("weight must be finite and positive")

        x, h1, h2, logit = self._forward(features)
        prediction = self._sigmoid(logit)
        eps = 1e-12
        loss = -sample_weight * (
            y * math.log(max(prediction, eps))
            + (1.0 - y) * math.log(max(1.0 - prediction, eps))
        )

        dlogit = sample_weight * (prediction - y)
        grad_w3 = dlogit * (h1 + h2) + self.config.l2 * self.w3
        grad_b3 = dlogit

        dresidual = dlogit * self.w3
        dz2 = dresidual * (1.0 - h2 * h2)
        grad_w2 = np.outer(dz2, h1) + self.config.l2 * self.w2
        grad_b2 = dz2

        dh1 = dresidual + self.w2.T @ dz2
        dz1 = dh1 * (1.0 - h1 * h1)
        grad_w1 = np.outer(dz1, x) + self.config.l2 * self.w1
        grad_b1 = dz1

        lr = self.config.learning_rate
        self.w3 -= lr * grad_w3
        self.b3 -= lr * grad_b3
        self.w2 -= lr * grad_w2
        self.b2 -= lr * grad_b2
        self.w1 -= lr * grad_w1
        self.b1 -= lr * grad_b1
        return float(loss)

    def save(self, path: str | Path) -> None:
        np.savez_compressed(
            Path(path),
            input_dim=self.config.input_dim,
            hidden_dim=self.config.hidden_dim,
            learning_rate=self.config.learning_rate,
            l2=self.config.l2,
            seed=self.config.seed,
            w1=self.w1,
            b1=self.b1,
            w2=self.w2,
            b2=self.b2,
            w3=self.w3,
            b3=np.asarray(self.b3),
        )

    @classmethod
    def load(cls, path: str | Path) -> "TinyResidualRanker":
        with np.load(Path(path), allow_pickle=False) as payload:
            config = RankerConfig(
                input_dim=int(payload["input_dim"]),
                hidden_dim=int(payload["hidden_dim"]),
                learning_rate=float(payload["learning_rate"]),
                l2=float(payload["l2"]),
                seed=int(payload["seed"]),
            )
            ranker = cls(config)
            ranker.w1 = np.asarray(payload["w1"], dtype=np.float64)
            ranker.b1 = np.asarray(payload["b1"], dtype=np.float64)
            ranker.w2 = np.asarray(payload["w2"], dtype=np.float64)
            ranker.b2 = np.asarray(payload["b2"], dtype=np.float64)
            ranker.w3 = np.asarray(payload["w3"], dtype=np.float64)
            ranker.b3 = float(payload["b3"])
        return ranker
