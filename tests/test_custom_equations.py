from __future__ import annotations

import math

import numpy as np
import pytest

from cace_studio.app import build_registry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.expression_math import (
    MathExpressionError,
    equation_features,
    evaluate_expression,
    parse_equation,
)
from cace_studio.core.graph import Edge, Experiment, Node


def test_friendly_equation_input_normalizes_and_renders_latex():
    parsed = parse_equation("y = 2x^2 + sin(x) + π")
    assert parsed.equation_kind == "explicit"
    assert parsed.dependent_variable == "y"
    assert parsed.free_symbols == ("x",)
    assert "**" in parsed.normalized
    assert "2 * x" in parsed.normalized
    assert r"\pi" in parsed.display_latex
    assert r"\sin" in parsed.display_latex


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').system('echo nope')",
        "(1).__class__",
        "[x for x in [1,2,3]]",
        "open('secret')",
        "x[0]",
        "lambda x: x",
    ],
)
def test_expression_language_rejects_python_escape_hatches(text):
    with pytest.raises(MathExpressionError):
        parse_equation(text)


def test_safe_expression_evaluator_supports_vector_math():
    x = np.linspace(-math.pi, math.pi, 9)
    result = evaluate_expression("sin(x)^2 + cos(x)^2", {"x": x})
    assert np.allclose(result, 1.0)


def test_equation_features_describe_graphability_without_claiming_proof():
    obj = parse_equation("x^2 + y^2 = 4").to_dict()
    features = equation_features(obj)
    assert features["equation_kind"] == "implicit"
    assert features["graphability"]["implicit_2d"] is True
    assert features["evidence_authority"] is False
    assert features["proof_effect"] == "none"


def test_custom_equation_to_feature_and_2d_graph_workflow_executes():
    registry = build_registry()
    exp = Experiment(
        name="custom equation 2D",
        nodes=[
            Node("eq", "math.custom_equation", {"equation": "y = sin(x)"}),
            Node("features", "math.equation_features", {}),
            Node(
                "graph",
                "math.graph_equation_2d",
                {
                    "x_min": -math.pi,
                    "x_max": math.pi,
                    "y_min": -2.0,
                    "y_max": 2.0,
                    "samples": 129,
                },
            ),
        ],
        edges=[
            Edge("eq", "equation", "features", "equation"),
            Edge("eq", "equation", "graph", "equation"),
        ],
    )
    result = GraphExecutor(registry).run(exp)
    assert result.completed is True
    assert result.outputs["features"]["features"]["graphability"]["explicit_2d"] is True
    graph = result.outputs["graph"]["graph"]
    assert graph["schema"] == "cace-equation-plot-2d-v1"
    assert graph["mode"] == "explicit"
    assert len(graph["points"]) == 129
    assert graph["proof_effect"] == "none"


def test_implicit_circle_graph_outputs_zero_contour_residual_grid():
    registry = build_registry()
    exp = Experiment(
        name="implicit circle",
        nodes=[
            Node("eq", "math.custom_equation", {"equation": "x^2 + y^2 = 4"}),
            Node(
                "graph",
                "math.graph_equation_2d",
                {
                    "x_min": -3.0,
                    "x_max": 3.0,
                    "y_min": -3.0,
                    "y_max": 3.0,
                    "samples": 64,
                },
            ),
        ],
        edges=[Edge("eq", "equation", "graph", "equation")],
    )
    result = GraphExecutor(registry).run(exp)
    graph = result.outputs["graph"]["graph"]
    assert graph["mode"] == "implicit_contour"
    assert graph["contour_level"] == 0.0
    assert len(graph["x"]) == 64
    assert len(graph["y"]) == 64


def test_custom_equation_to_3d_surface_workflow_executes():
    registry = build_registry()
    exp = Experiment(
        name="custom equation 3D",
        nodes=[
            Node("eq", "math.custom_equation", {"equation": "z = sin(x) * cos(y)"}),
            Node(
                "surface",
                "math.graph_equation_3d",
                {
                    "x_min": -2.0,
                    "x_max": 2.0,
                    "y_min": -2.0,
                    "y_max": 2.0,
                    "samples": 33,
                },
            ),
        ],
        edges=[Edge("eq", "equation", "surface", "equation")],
    )
    result = GraphExecutor(registry).run(exp)
    surface = result.outputs["surface"]["surface"]
    assert surface["schema"] == "cace-equation-plot-3d-v1"
    assert surface["dependent_variable"] == "z"
    assert set(surface["independent_variables"]) == {"x", "y"}
    assert len(surface["coordinates"]["z"]) == 33
    assert len(surface["coordinates"]["z"][0]) == 33
    assert surface["proof_effect"] == "none"


def test_equation_module_rejects_unsafe_payload_through_executor():
    registry = build_registry()
    exp = Experiment(
        name="unsafe equation",
        nodes=[
            Node(
                "eq",
                "math.custom_equation",
                {"equation": "__import__('os').system('id')"},
            )
        ],
    )
    with pytest.raises(Exception, match="unsupported|function|syntax"):
        GraphExecutor(registry).run(exp)



def test_parameterized_equation_graph_uses_numeric_parameter_values():
    registry = build_registry()
    exp = Experiment(
        name="parameterized equation",
        nodes=[
            Node("eq", "math.custom_equation", {"equation": "y = a*x^2 + b"}),
            Node(
                "graph",
                "math.graph_equation_2d",
                {
                    "x_min": -2.0,
                    "x_max": 2.0,
                    "y_min": -10.0,
                    "y_max": 10.0,
                    "samples": 65,
                    "parameters_json": '{"a":2,"b":1}',
                },
            ),
        ],
        edges=[Edge("eq", "equation", "graph", "equation")],
    )
    result = GraphExecutor(registry).run(exp)
    graph = result.outputs["graph"]["graph"]
    assert graph["parameter_values"] == {"a": 2.0, "b": 1.0}
    midpoint = graph["points"][32]
    assert midpoint[0] == pytest.approx(0.0)
    assert midpoint[1] == pytest.approx(1.0)


def test_parameterized_equation_requires_all_parameter_values():
    registry = build_registry()
    exp = Experiment(
        name="missing parameter",
        nodes=[
            Node("eq", "math.custom_equation", {"equation": "y = a*x"}),
            Node(
                "graph",
                "math.graph_equation_2d",
                {"parameters_json": "{}"},
            ),
        ],
        edges=[Edge("eq", "equation", "graph", "equation")],
    )
    with pytest.raises(Exception, match="missing numeric parameter values"):
        GraphExecutor(registry).run(exp)
