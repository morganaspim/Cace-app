from cace_studio.runtime.math_object import (
    CliffordSignature,
    DisplayState,
    DisplayViewKind,
    MathObject,
    SparseMultivector,
    project_xy,
)


def test_display_coordinate_system_never_changes_math_identity():
    sig = CliffordSignature(3, 0, 0)
    mv = SparseMultivector.from_pairs(sig, [(1, 1.0), (2, 2.0), (4, -0.5)])
    obj = MathObject("m1", "point", mv, units="m")
    identity = obj.semantic_sha256()

    views = [
        DisplayViewKind.CARTESIAN,
        DisplayViewKind.POLAR,
        DisplayViewKind.HEX_AXIAL,
        DisplayViewKind.HONEYCOMB,
        DisplayViewKind.EISENSTEIN,
        DisplayViewKind.PROJECTIVE,
        DisplayViewKind.CONFORMAL,
    ]
    projected = [project_xy(3.0, 2.0, DisplayState(view=view)) for view in views]

    assert len(set(projected)) >= 3
    assert obj.semantic_sha256() == identity


def test_sparse_multivector_canonicalizes_duplicate_blades():
    sig = CliffordSignature(2, 0, 0)
    mv = SparseMultivector.from_pairs(sig, [(1, 2.0), (1, -0.5), (2, 0.0)])
    assert [(term.blade_mask, term.coefficient) for term in mv.terms] == [(1, 1.5)]
