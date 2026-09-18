from __future__ import annotations

"""Independent verifier for cace.p1_rt0_green_exact.v1 certificates.

This deliberately recomputes the polynomial identity from certificate inputs
instead of trusting the certificate's derived fields.  Passing this verifier is
engineering/certificate evidence, not a substitute for Lean kernel checking.
"""

from fractions import Fraction
import hashlib
import json
from typing import Any

SCHEMA = "cace.p1_rt0_green_exact.v1"


def _f(x: Any) -> Fraction:
    return Fraction(str(x))


def _sha(body: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def verify_certificate(cert: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if cert.get("schema") != SCHEMA:
        errors.append("schema mismatch")
        return {"passed": False, "errors": errors}

    body = dict(cert)
    claimed_sha = body.pop("certificate_sha256", None)
    actual_sha = _sha(body)
    if claimed_sha != actual_sha:
        errors.append("certificate hash mismatch")

    try:
        pts = [tuple(_f(v) for v in p) for p in cert["triangle"]]
        if len(pts) != 3 or any(len(p) != 2 for p in pts):
            raise ValueError("triangle shape")
        c = _f(cert["primal"]["c"])
        gx = _f(cert["primal"]["gx"])
        gy = _f(cert["primal"]["gy"])
        cx = _f(cert["flux"]["cx"])
        cy = _f(cert["flux"]["cy"])
        r = _f(cert["flux"]["radial"])

        def v(p):
            return c + gx * p[0] + gy * p[1]

        def qdotg(p):
            return (cx + r * p[0]) * gx + (cy + r * p[1]) * gy

        def boundary_term(a, b):
            # Direct endpoint product integration on t in [0,1].
            nx, ny = b[1] - a[1], -(b[0] - a[0])
            va, vb = v(a), v(b)
            fa = (cx + r * a[0]) * nx + (cy + r * a[1]) * ny
            fb = (cx + r * b[0]) * nx + (cy + r * b[1]) * ny
            return (2 * va * fa + va * fb + vb * fa + 2 * vb * fb) / 6

        p0, p1, p2 = pts
        det = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        lhs = det * sum((qdotg(p) for p in pts), Fraction(0)) / 6
        div_term = -(det * (2 * r) * sum((v(p) for p in pts), Fraction(0)) / 6)
        faces = [boundary_term(p0, p1), boundary_term(p1, p2), boundary_term(p2, p0)]
        face_sum = sum(faces, Fraction(0))
        residual = lhs - div_term - face_sum

        expected = {
            "det": det,
            "cell_pairing": lhs,
            "cell_divergence": div_term,
            "cell_face_pairing": face_sum,
            "green_residual": residual,
        }
        for key, value in expected.items():
            if _f(cert[key]) != value:
                errors.append(f"{key} mismatch")
        if [_f(x) for x in cert["local_face_pairings"]] != faces:
            errors.append("local_face_pairings mismatch")
        if cert.get("identity_holds") is not (residual == 0):
            errors.append("identity_holds mismatch")
        if residual != 0:
            errors.append(f"exact Green residual is nonzero: {residual}")
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        errors.append(f"invalid certificate: {exc}")

    return {
        "passed": not errors,
        "errors": errors,
        "certificate_sha256": actual_sha,
        "independently_recomputed": True,
        "evidence_class": "exact-runtime-certificate-verification",
    }
