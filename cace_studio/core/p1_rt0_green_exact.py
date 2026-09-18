from __future__ import annotations

"""Exact P1/RT0 element Green certificate.

This runtime certificate mirrors the algebraic statement proved in
CACEFormal.P1RT0Element, but it is not formal-proof evidence.  All arithmetic is
fractions and the certificate records both sides of the element identity.
"""

from fractions import Fraction
import hashlib
import json
from typing import Any

SCHEMA = "cace.p1_rt0_green_exact.v1"


def _f(x: Any) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(str(x))


def _point(p: Any) -> tuple[Fraction, Fraction]:
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        raise ValueError("point must have two coordinates")
    return _f(p[0]), _f(p[1])


def _canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def build_certificate(
    triangle: list[list[Any]],
    primal: dict[str, Any],
    flux: dict[str, Any],
) -> dict[str, Any]:
    if len(triangle) != 3:
        raise ValueError("triangle must contain three points")
    p = [_point(x) for x in triangle]
    c, gx, gy = _f(primal["c"]), _f(primal["gx"]), _f(primal["gy"])
    cx, cy, radial = _f(flux["cx"]), _f(flux["cy"]), _f(flux["radial"])

    def veval(a):
        x, y = a
        return c + gx * x + gy * y

    def qeval(a):
        x, y = a
        return cx + radial * x, cy + radial * y

    def dot_grad(a):
        qx, qy = qeval(a)
        return qx * gx + qy * gy

    def edge_pairing(a, b):
        ax, ay = a
        bx, by = b
        nx, ny = by - ay, -(bx - ax)
        qa, qb = qeval(a), qeval(b)
        ga = qa[0] * nx + qa[1] * ny
        gb = qb[0] * nx + qb[1] * ny
        va, vb = veval(a), veval(b)
        return (2 * va * ga + va * gb + vb * ga + 2 * vb * gb) / 6

    (x0, y0), (x1, y1), (x2, y2) = p
    det = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    pairing = det / 6 * sum((dot_grad(a) for a in p), Fraction(0))
    divergence = 2 * radial
    cell_div = -(det / 6 * divergence * sum((veval(a) for a in p), Fraction(0)))
    faces = [edge_pairing(p[0], p[1]), edge_pairing(p[1], p[2]), edge_pairing(p[2], p[0])]
    face_sum = sum(faces, Fraction(0))
    residual = pairing - cell_div - face_sum

    body = {
        "schema": SCHEMA,
        "triangle": [[str(x), str(y)] for x, y in p],
        "primal": {"c": str(c), "gx": str(gx), "gy": str(gy)},
        "flux": {"cx": str(cx), "cy": str(cy), "radial": str(radial)},
        "det": str(det),
        "cell_pairing": str(pairing),
        "cell_divergence": str(cell_div),
        "local_face_pairings": [str(x) for x in faces],
        "cell_face_pairing": str(face_sum),
        "green_residual": str(residual),
        "identity_holds": residual == 0,
        "evidence_class": "exact-runtime-certificate",
        "formal_theorem": "CACEFormal.P1RT0Element.local_green_identity",
    }
    return {**body, "certificate_sha256": _canonical_sha(body)}
