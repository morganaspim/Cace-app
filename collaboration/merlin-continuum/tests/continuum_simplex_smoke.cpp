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
