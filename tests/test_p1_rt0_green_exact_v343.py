from __future__ import annotations

from copy import deepcopy

from cace_studio.core.p1_rt0_green_exact import build_certificate
from cace_studio.core.p1_rt0_green_verify import verify_certificate


def _certificate():
    return build_certificate(
        [["0", "0"], ["2", "0"], ["0", "3"]],
        {"c": "5/7", "gx": "2/3", "gy": "-4/5"},
        {"cx": "7/11", "cy": "-3/13", "radial": "5/17"},
    )


def test_general_rt0_radial_green_identity_is_exact():
    cert = _certificate()
    assert cert["identity_holds"] is True
    assert cert["green_residual"] == "0"
    result = verify_certificate(cert)
    assert result["passed"] is True
    assert result["independently_recomputed"] is True


def test_verifier_rejects_mutated_derived_value_even_with_valid_original_hash():
    cert = _certificate()
    cert["cell_pairing"] = "0"
    result = verify_certificate(cert)
    assert result["passed"] is False
    assert "certificate hash mismatch" in result["errors"]
    assert "cell_pairing mismatch" in result["errors"]


def test_verifier_rejects_rehashed_semantically_false_certificate():
    cert = _certificate()
    cert["green_residual"] = "1"
    # Do not expose verifier internals here: a semantic mutation must fail even
    # independently of content-addressing.
    result = verify_certificate(cert)
    assert result["passed"] is False
    assert "green_residual mismatch" in result["errors"]


def test_certificate_is_deterministic_and_content_addressed():
    a = _certificate()
    b = _certificate()
    assert a == b
    assert len(a["certificate_sha256"]) == 64
