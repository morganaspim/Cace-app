from __future__ import annotations

import pytest

from cace_studio.core.geometric_animation import (
    CoordinateViewRegistry,
    GeometricActionEvent,
    GeometricAnimationError,
    GeometricPoint,
    animation_stream,
)


EXPECTED_VIEWS = {
    "cartesian.2d",
    "cartesian.3d",
    "projected.nd_3d",
    "hex.eisenstein",
    "complex.i",
    "complex.omega",
    "fractal.quadtree",
    "fractal.morton",
    "fractal.base_2i_minus_1",
    "fractal.base_omega_minus_2",
    "aperiodic.einstein_hat",
}


def _event2():
    return GeometricActionEvent(
        event_id="geo-step-1",
        sequence=1,
        action="rotate",
        points=(GeometricPoint((1.0, 0.0)), GeometricPoint((0.0, 1.0))),
        matrix=((0.0, -1.0), (1.0, 0.0)),
        labels=("source", "target"),
        metadata={"operator_id": "math.geometry.affine.apply"},
        source="local-ai",
    )


def _event3():
    return GeometricActionEvent(
        event_id="geo-step-3d",
        sequence=1,
        action="translate",
        points=(GeometricPoint((1.0, 0.0, 0.0)),),
        translation=(0.0, 1.0, 2.0),
        source="cace",
    )


def test_requested_coordinate_views_are_preserved_in_registry():
    registry = CoordinateViewRegistry()
    assert EXPECTED_VIEWS <= set(registry.view_ids())
    assert registry.descriptor("aperiodic.einstein_hat")["projection"] == "einstein_hat_tile_mesh"
    assert registry.descriptor("fractal.base_2i_minus_1")["base"] == "2i-1"
    assert registry.descriptor("fractal.base_omega_minus_2")["base"] == "omega-2"
    assert registry.descriptor("cartesian.3d")["dimension"] == 3
    assert registry.descriptor("projected.nd_3d")["dimension"] == "any"


@pytest.mark.parametrize(
    "view_id",
    sorted(EXPECTED_VIEWS - {"cartesian.3d"}),
)
def test_same_2d_semantic_action_can_be_animated_in_compatible_registered_views(view_id):
    registry = CoordinateViewRegistry()
    event = _event2()
    rendered = registry.render_event(event, view_id=view_id)

    assert rendered["coordinate_view_id"] == view_id
    assert rendered["semantic_sha256"] == event.semantic_sha256()
    assert rendered["canonical_points"] == [[1.0, 0.0], [0.0, 1.0]]
    assert rendered["presentation_only"] is True
    assert rendered["evidence_authority"] is False
    assert rendered["proof_effect"] == "none"
    assert rendered["promotion_authority"] is False


def test_3d_event_works_in_cartesian_3d_and_nd_projection():
    registry = CoordinateViewRegistry()
    event = _event3()
    for view_id in ("cartesian.3d", "projected.nd_3d"):
        rendered = registry.render_event(event, view_id=view_id)
        assert rendered["semantic_sha256"] == event.semantic_sha256()
        assert rendered["canonical_points"] == [[1.0, 0.0, 0.0]]


def test_switching_compatible_view_does_not_change_semantic_identity():
    registry = CoordinateViewRegistry()
    event = _event2()
    compatible = EXPECTED_VIEWS - {"cartesian.3d"}
    identities = {
        registry.render_event(event, view_id=view_id)["semantic_sha256"]
        for view_id in compatible
    }
    assert identities == {event.semantic_sha256()}


def test_dimension_mismatch_fails_closed():
    registry = CoordinateViewRegistry()
    with pytest.raises(GeometricAnimationError, match="dimension"):
        registry.render_event(_event2(), view_id="cartesian.3d")


def test_animation_stream_requires_monotonic_sequence():
    first = GeometricActionEvent(
        event_id="a",
        sequence=2,
        action="select_point",
        points=(GeometricPoint((0.0, 0.0)),),
    )
    second = GeometricActionEvent(
        event_id="b",
        sequence=1,
        action="select_point",
        points=(GeometricPoint((1.0, 1.0)),),
    )
    with pytest.raises(GeometricAnimationError, match="strictly increasing"):
        animation_stream([first, second], view_id="cartesian.2d")


def test_unknown_view_fails_closed():
    with pytest.raises(GeometricAnimationError, match="unknown coordinate view"):
        CoordinateViewRegistry().render_event(_event2(), view_id="invented.view")
