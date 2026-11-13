#include "expert_robot/math/continuum_simplex.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

using expert_robot::math::continuum::EdgeField;
using expert_robot::math::continuum::EdgeSample;
using expert_robot::math::continuum::ExtensionClass;
using expert_robot::math::continuum::Matrix2;
using expert_robot::math::continuum::StatePair;
using expert_robot::math::continuum::TriangleBoundary;
using expert_robot::math::continuum::TriangleEdge;

namespace {

bool close(double lhs, double rhs, double tolerance = 1e-9) {
    return std::abs(lhs - rhs) <= tolerance;
}

EdgeField affine_edge(StatePair start, StatePair end) {
    return EdgeField({
        {0.0, start},
        {0.5, {0.5 * (start.first + end.first),
               0.5 * (start.second + end.second)}},
        {1.0, end}
    });
}

} // namespace

int main() {
    const StatePair a{0.0, 1.0};
    const StatePair b{1.0, 0.0};
    const StatePair c{1.0, 1.0};

    TriangleBoundary boundary(
        affine_edge(a, b),
        affine_edge(b, c),
        affine_edge(c, a));

    const auto compatibility = boundary.vertex_compatibility();
    assert(compatibility.compatible);
    assert(compatibility.at_a && compatibility.at_b && compatibility.at_c);
    assert(boundary.classify_affine_extension() == ExtensionClass::AffineExtension);

    const StatePair interior = boundary.evaluate_affine({0.2, 0.3, 0.5});
    assert(close(interior.first, 0.8));
    assert(close(interior.second, 0.7));

    const StatePair edge_midpoint = boundary.edge(TriangleEdge::AB).evaluate(0.5);
    assert(close(edge_midpoint.first, 0.5));
    assert(close(edge_midpoint.second, 0.5));

    TriangleBoundary curved_trace(
        EdgeField({{0.0, a}, {0.5, {0.75, 0.25}}, {1.0, b}}),
        affine_edge(b, c),
        affine_edge(c, a));
    assert(curved_trace.vertex_compatibility().compatible);
    assert(curved_trace.classify_affine_extension() ==
           ExtensionClass::RequiresHigherOrderOrDifferentExtension);
    bool rejected_affine_claim = false;
    try {
        (void)curved_trace.evaluate_affine({1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0});
    } catch (const std::logic_error&) {
        rejected_affine_claim = true;
    }
    assert(rejected_affine_claim);

    TriangleBoundary incompatible(
        affine_edge(a, b),
        affine_edge(b, c),
        affine_edge(c, {0.0, 2.0}));
    assert(!incompatible.vertex_compatibility().compatible);
    assert(incompatible.classify_affine_extension() ==
           ExtensionClass::VertexIncompatible);

    const Matrix2 scale{2.0, 0.0, 0.0, 1.0};
    const Matrix2 shear{1.0, 1.0, 0.0, 1.0};
    const Matrix2 composed = scale.then(shear);
    const StatePair transformed = composed.apply({1.0, 2.0});
    assert(close(transformed.first, 4.0));
    assert(close(transformed.second, 2.0));
    assert(composed.invertible());
    assert(!(Matrix2{1.0, 0.0, 0.0, 0.0}.invertible()));


    // Heterogeneous linear maps carry explicit source/target state-space IDs.
    // R2 -> R3 -> R1 composes to a rectangular R2 -> R1 map.
    using expert_robot::math::continuum::DenseMatrix;
    using expert_robot::math::continuum::LinearStateMap;
    const LinearStateMap embed(
        "embed-R2-R3", "R2", "R3",
        DenseMatrix({{1.0, 0.0}, {0.0, 1.0}, {1.0, 1.0}}));
    const LinearStateMap collapse(
        "collapse-R3-R1", "R3", "R1",
        DenseMatrix({{1.0, 1.0, 0.0}}));
    const auto composed_map = embed.then(collapse);
    assert(composed_map.source() == "R2");
    assert(composed_map.target() == "R1");
    const auto composed_value = composed_map.apply({2.0, 3.0});
    assert(composed_value.size() == 1);
    assert(close(composed_value[0], 5.0));

    // The collapse is non-injective: distinct source states share one image.
    assert(close(collapse.apply(embed.apply({2.0, 3.0}))[0],
                 collapse.apply(embed.apply({4.0, 1.0}))[0]));

    const LinearStateMap identity(
        "identity-R2", "R2", "R2",
        DenseMatrix({{1.0, 0.0}, {0.0, 1.0}}));
    const auto identity_composed = identity.then(embed);
    const auto identity_value = identity_composed.apply({2.0, 3.0});
    const auto direct_value = embed.apply({2.0, 3.0});
    assert(identity_value == direct_value);

    bool rejected_wrong_source_dimension = false;
    try {
        (void)embed.apply({1.0});
    } catch (const std::invalid_argument&) {
        rejected_wrong_source_dimension = true;
    }
    assert(rejected_wrong_source_dimension);

    bool rejected_wrong_intermediate_carrier = false;
    try {
        (void)embed.then(identity);
    } catch (const std::invalid_argument&) {
        rejected_wrong_intermediate_carrier = true;
    }
    assert(rejected_wrong_intermediate_carrier);

    bool rejected_ragged_matrix = false;
    try {
        (void)DenseMatrix({{1.0, 0.0}, {0.0}});
    } catch (const std::invalid_argument&) {
        rejected_ragged_matrix = true;
    }
    assert(rejected_ragged_matrix);

    bool rejected_bad_samples = false;
    try {
        (void)EdgeField({{0.0, a}, {0.7, b}, {0.6, c}, {1.0, a}});
    } catch (const std::invalid_argument&) {
        rejected_bad_samples = true;
    }
    assert(rejected_bad_samples);

    std::cout << "continuum simplex smoke: PASS\n";
    return 0;
}
