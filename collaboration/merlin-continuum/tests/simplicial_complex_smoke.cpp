#include "expert_robot/math/simplicial_complex.hpp"

#include <cassert>
#include <iostream>
#include <stdexcept>

using expert_robot::math::continuum::IntegerChain;
using expert_robot::math::continuum::OrientedSimplex;
using expert_robot::math::continuum::boundary;
using expert_robot::math::continuum::boundary_squared;
using expert_robot::math::continuum::is_zero_chain;

int main() {
    const OrientedSimplex triangle{{"A", "B", "C"}};
    const auto triangle_boundary = boundary(triangle);
    assert(triangle_boundary.size() == 3);
    assert(is_zero_chain(boundary_squared(triangle)));

    const OrientedSimplex tetrahedron{{"A", "B", "C", "D"}};
    const auto tetrahedron_boundary = boundary(tetrahedron);
    assert(tetrahedron_boundary.size() == 4);
    assert(is_zero_chain(boundary_squared(tetrahedron)));

    const OrientedSimplex reversed_triangle{{"B", "A", "C"}};
    const auto reversed_boundary = boundary(reversed_triangle);
    for (const auto& [face, coefficient] : triangle_boundary) {
        const auto found = reversed_boundary.find(face);
        assert(found != reversed_boundary.end());
        assert(found->second == -coefficient);
    }

    bool rejected_duplicate_vertex = false;
    try {
        (void)boundary(OrientedSimplex{{"A", "B", "A"}});
    } catch (const std::invalid_argument&) {
        rejected_duplicate_vertex = true;
    }
    assert(rejected_duplicate_vertex);

    bool rejected_zero_simplex_boundary = false;
    try {
        (void)boundary(OrientedSimplex{{"A"}});
    } catch (const std::invalid_argument&) {
        rejected_zero_simplex_boundary = true;
    }
    assert(rejected_zero_simplex_boundary);

    bool rejected_noncanonical_chain = false;
    try {
        const IntegerChain malformed{{{"B", "A"}, 1}};
        (void)boundary(malformed);
    } catch (const std::invalid_argument&) {
        rejected_noncanonical_chain = true;
    }
    assert(rejected_noncanonical_chain);

    std::cout << "simplicial boundary smoke: PASS\n";
    return 0;
}
