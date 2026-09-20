from __future__ import annotations

import copy

from cace_studio.core.formal_runtime_packet import build_p1_rt0_runtime_packet
from cace_studio.core.p1_rt0_exact_semantics import (
    exact_p1_rt0_assembly_semantics,
    verify_exact_p1_rt0_assembly_semantics,
)


def square_center_mesh():
    return {
        "vertices": [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"], ["1/2", "1/2"]],
        "triangles": [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
        "boundary_labels": {
            "0-1": "bottom",
            "1-2": "right",
            "2-3": "top",
            "0-3": "left",
        },
    }


def arbitrary_packet():
    return build_p1_rt0_runtime_packet(
        square_center_mesh(),
        [
            {"c": "0", "gx": "1", "gy": "0"},
            {"c": "1", "gx": "0", "gy": "1"},
            {"c": "2", "gx": "-1", "gy": "0"},
            {"c": "1", "gx": "0", "gy": "-1"},
        ],
        [
            {"cx": "0", "cy": "0", "radial": "1/2"},
            {"cx": "1", "cy": "0", "radial": "1/3"},
            {"cx": "0", "cy": "1", "radial": "-1/4"},
            {"cx": "-1", "cy": "0", "radial": "2"},
        ],
    )


def admissible_packet():
    # Continuous P1 tent: zero on the square boundary, value one at the center.
    # Global constant q=(1,0) is an RT0 field with zero divergence and matching
    # normal traces.  This is nontrivial: cell gradients/pairings are nonzero,
    # but the assembled global pairing cancels exactly.
    return build_p1_rt0_runtime_packet(
        square_center_mesh(),
        [
            {"c": "0", "gx": "0", "gy": "2"},
            {"c": "2", "gx": "-2", "gy": "0"},
            {"c": "2", "gx": "0", "gy": "-2"},
            {"c": "0", "gx": "2", "gy": "0"},
        ],
        [
            {"cx": "1", "cy": "0", "radial": "0"},
            {"cx": "1", "cy": "0", "radial": "0"},
            {"cx": "1", "cy": "0", "radial": "0"},
            {"cx": "1", "cy": "0", "radial": "0"},
        ],
    )


def test_exact_local_green_holds_for_arbitrary_bound_packet():
    cert = exact_p1_rt0_assembly_semantics(arbitrary_packet())
    assert cert["summary"]["local_green_all"] is True
    assert cert["summary"]["global_green_identity"] is True
    assert cert["fsl_status"]["FSL-5"] == "EXACT_CHECK_PASS"
    assert cert["formal_claim"] is False
    assert cert["fsl_status"]["FSL-7"] == "UNRESOLVED"


def test_admissible_nontrivial_packet_derives_exact_orthogonality():
    cert = exact_p1_rt0_assembly_semantics(admissible_packet())
    summary = cert["summary"]
    assert summary["local_green_all"] is True
    assert summary["assembly_equilibrium_all"] is True
    assert summary["boundary_admissibility_all"] is True
    assert summary["interior_cancellation_all"] is True
    assert summary["global_green_identity"] is True
    assert summary["global_pairing"] == "0"
    assert summary["exact_orthogonality_derived"] is True
    assert cert["fsl_status"]["FSL-6"] == "EXACT_CHECK_PASS"
    assert any(row["cell_pairing"] != "0" for row in cert["cells"])


def test_nonzero_rt0_radial_fails_assembly_equilibrium_for_tent_fixture():
    packet = admissible_packet()
    data = copy.deepcopy(packet)
    # Rebuild rather than tamper with the content-addressed packet.
    source = data["mesh_certificate"]["source"]
    rt0 = copy.deepcopy(data["rt0_cells"])
    rt0[0]["radial"] = "1"
    rebuilt = build_p1_rt0_runtime_packet(
        {
            "vertices": source["vertices"],
            "triangles": source["triangles"],
            "boundary_labels": source["boundary_labels"],
        },
        data["p1_cells"],
        rt0,
    )
    cert = exact_p1_rt0_assembly_semantics(rebuilt)
    assert cert["summary"]["assembly_equilibrium_all"] is False
    assert cert["summary"]["exact_orthogonality_derived"] is False
    assert cert["fsl_status"]["FSL-6"] == "EXACT_CHECK_FAIL"


def test_broken_flux_match_fails_interior_cancellation():
    packet = admissible_packet()
    source = packet["mesh_certificate"]["source"]
    rt0 = copy.deepcopy(packet["rt0_cells"])
    rt0[1]["cx"] = "2"
    rebuilt = build_p1_rt0_runtime_packet(
        {
            "vertices": source["vertices"],
            "triangles": source["triangles"],
            "boundary_labels": source["boundary_labels"],
        },
        packet["p1_cells"],
        rt0,
    )
    cert = exact_p1_rt0_assembly_semantics(rebuilt)
    assert cert["summary"]["interior_cancellation_all"] is False
    assert cert["summary"]["exact_orthogonality_derived"] is False


def test_exact_semantics_certificate_is_tamper_evident():
    packet = admissible_packet()
    cert = exact_p1_rt0_assembly_semantics(packet)
    assert verify_exact_p1_rt0_assembly_semantics(packet, cert)["passed"] is True
    bad = copy.deepcopy(cert)
    bad["summary"]["global_pairing"] = "1"
    check = verify_exact_p1_rt0_assembly_semantics(packet, bad)
    assert check["passed"] is False
    assert any("SHA-256" in item or "differs" in item for item in check["errors"])
