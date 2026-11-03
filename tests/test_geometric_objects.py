from __future__ import annotations

from cace_studio.app import build_registry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node


def test_shape_toolbox_builds_2d_3d_and_nd_geometric_objects():
    registry = build_registry()
    ids = {
        "geometry.circle",
        "geometry.parabola",
        "geometry.conic",
        "geometry.hyperbola",
        "geometry.sphere",
        "geometry.hypercube",
        "chemistry.atom",
        "chemistry.bond",
        "geometry.affine_transform_object",
    }
    assert ids <= {cls.metadata.module_id for cls in registry.classes()}

    exp = Experiment(
        name="shape toolbox",
        nodes=[
            Node("circle", "geometry.circle", {"radius": 2.0}),
            Node("parabola", "geometry.parabola", {"a": 0.5}),
            Node("conic", "geometry.conic"),
            Node("hyperbola", "geometry.hyperbola"),
            Node("sphere", "geometry.sphere", {"radius": 1.5}),
            Node("cube4", "geometry.hypercube", {"dimension": 4, "half_extent": 1.0}),
        ],
    )
    result = GraphExecutor(registry).run(exp)
    assert result.completed is True
    assert result.outputs["circle"]["object"]["geometry_kind"] == "circle"
    assert result.outputs["sphere"]["object"]["dimension"] == 3
    assert result.outputs["cube4"]["object"]["dimension"] == 4
    assert len(result.outputs["cube4"]["object"]["points"]) == 16


def test_atoms_can_form_geometric_molecule_and_be_transformed():
    registry = build_registry()
    exp = Experiment(
        name="geometric molecule",
        nodes=[
            Node(
                "c",
                "chemistry.atom",
                {"atomic_number": 6, "symbol": "C", "x": 0.0, "y": 0.0, "z": 0.0},
            ),
            Node(
                "o",
                "chemistry.atom",
                {"atomic_number": 8, "symbol": "O", "x": 1.2, "y": 0.0, "z": 0.0},
            ),
            Node("bond", "chemistry.bond", {"bond_order": 2.0}),
            Node(
                "move",
                "geometry.affine_transform_object",
                {
                    "matrix_json": "[[1,0,0],[0,1,0],[0,0,1]]",
                    "translation_json": "[0,2,0]",
                },
            ),
        ],
        edges=[
            Edge("c", "object", "bond", "left"),
            Edge("o", "object", "bond", "right"),
            Edge("bond", "object", "move", "object"),
        ],
    )
    result = GraphExecutor(registry).run(exp)
    molecule = result.outputs["bond"]["object"]
    moved = result.outputs["move"]["object"]

    assert molecule["object_type"] == "molecule"
    assert len(molecule["atoms"]) == 2
    assert molecule["bonds"][-1]["order"] == 2.0
    assert molecule["model_scope"].startswith("geometric molecular graph only")
    assert moved["atoms"][0]["position"] == [0.0, 2.0, 0.0]
    assert moved["atoms"][1]["position"] == [1.2, 2.0, 0.0]
    assert moved["proof_effect"] == "none"


def test_circle_affine_transform_preserves_geometric_object_envelope():
    registry = build_registry()
    exp = Experiment(
        name="circle transform",
        nodes=[
            Node("circle", "geometry.circle", {"radius": 1.0}),
            Node(
                "move",
                "geometry.affine_transform_object",
                {
                    "matrix_json": "[[1,0],[0,1]]",
                    "translation_json": "[3,-2]",
                },
            ),
        ],
        edges=[Edge("circle", "object", "move", "object")],
    )
    result = GraphExecutor(registry).run(exp)
    obj = result.outputs["move"]["object"]
    assert obj["schema"] == "cace-geometric-object-v1"
    assert obj["geometry_kind"] == "affine_transform(circle)"
    assert obj["transforms"][-1]["translation"] == [3.0, -2.0]
