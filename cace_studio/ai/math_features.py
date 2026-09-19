from __future__ import annotations

from collections.abc import Iterable, Sequence
import hashlib
import math
import re

import numpy as np


_TOKEN_RE = re.compile(r"[A-Za-z0-9_+\-*/^.=<>:]+", re.ASCII)


def _hash_u64(value: str, seed: int = 0) -> int:
    payload = seed.to_bytes(8, "little", signed=True) + value.encode("utf-8", errors="replace")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "little")


def normalize(vector: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Return an L2-normalized float64 copy, or zeros for a near-zero vector."""
    x = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(x))
    if not math.isfinite(norm):
        raise ValueError("feature vector contains non-finite values")
    if norm <= eps:
        return np.zeros_like(x, dtype=np.float64)
    return x / norm


def signed_hash_sketch(
    features: Iterable[str | tuple[str, float]],
    *,
    dim: int = 128,
    seed: int = 0,
) -> np.ndarray:
    """CountSketch-like signed hashing with fixed memory and no learned embedding model."""
    if dim <= 0:
        raise ValueError("dim must be positive")
    out = np.zeros(dim, dtype=np.float64)
    for item in features:
        if isinstance(item, tuple):
            name, weight = item
            weight = float(weight)
        else:
            name, weight = item, 1.0
        if not math.isfinite(weight):
            raise ValueError("feature weights must be finite")
        h = _hash_u64(str(name), seed)
        out[h % dim] += 1.0 if ((h >> 63) & 1) == 0 else -1.0
        if weight != 1.0:
            out[h % dim] += (1.0 if ((h >> 63) & 1) == 0 else -1.0) * (weight - 1.0)
    return normalize(out)


def hashed_text_sketch(
    text: str,
    *,
    dim: int = 128,
    seed: int = 0,
    include_bigrams: bool = True,
) -> np.ndarray:
    """Cheap deterministic text sketch using token and optional token-bigram hashing."""
    tokens = [tok.lower() for tok in _TOKEN_RE.findall(text)]
    features: list[str | tuple[str, float]] = [f"tok:{token}" for token in tokens]
    if include_bigrams:
        features.extend((f"bi:{a}|{b}", 0.5) for a, b in zip(tokens, tokens[1:]))
    if not features:
        features.append("<empty>")
    return signed_hash_sketch(features, dim=dim, seed=seed)


def fast_walsh_hadamard(vector: np.ndarray) -> np.ndarray:
    """Normalized Walsh-Hadamard transform for power-of-two lengths."""
    x = np.asarray(vector, dtype=np.float64).copy()
    n = x.size
    if n == 0 or n & (n - 1):
        raise ValueError("Walsh-Hadamard length must be a nonzero power of two")
    h = 1
    while h < n:
        for start in range(0, n, h * 2):
            a = x[start : start + h].copy()
            b = x[start + h : start + 2 * h].copy()
            x[start : start + h] = a + b
            x[start + h : start + 2 * h] = a - b
        h *= 2
    return x / math.sqrt(n)


def deterministic_hadamard_mix(vector: np.ndarray, *, seed: int = 0) -> np.ndarray:
    """Random-sign + Hadamard mixing with deterministic signs."""
    x = np.asarray(vector, dtype=np.float64)
    if x.size == 0 or x.size & (x.size - 1):
        raise ValueError("mixed feature length must be a nonzero power of two")
    signs = np.empty(x.size, dtype=np.float64)
    for index in range(x.size):
        signs[index] = 1.0 if (_hash_u64(f"hadamard:{index}", seed) & 1) == 0 else -1.0
    return fast_walsh_hadamard(x * signs)


def combine_sketches(vectors: Sequence[np.ndarray]) -> np.ndarray:
    """Compact additive + all-pairs interaction summary in O(k*d).

    The pairwise elementwise interaction uses
      sum_(i<j) v_i*v_j = ((sum_i v_i)^2 - sum_i(v_i^2))/2.
    """
    if not vectors:
        raise ValueError("at least one sketch is required")
    first = np.asarray(vectors[0], dtype=np.float64)
    if first.ndim != 1 or first.size == 0:
        raise ValueError("sketches must be nonempty one-dimensional vectors")
    total = np.zeros_like(first)
    square_total = np.zeros_like(first)
    for vector in vectors:
        x = np.asarray(vector, dtype=np.float64)
        if x.shape != first.shape:
            raise ValueError("all sketches must have identical shape")
        if not np.all(np.isfinite(x)):
            raise ValueError("sketches must be finite")
        total += x
        square_total += x * x

    mean = normalize(total)
    pair = normalize(0.5 * (total * total - square_total))
    return np.concatenate((mean, pair))


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a = normalize(np.asarray(left, dtype=np.float64))
    b = normalize(np.asarray(right, dtype=np.float64))
    if a.shape != b.shape:
        raise ValueError("cosine vectors must have identical shape")
    return float(np.dot(a, b))
