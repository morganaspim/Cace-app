#include "cace/exact_fem.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using cace::exact::BoundaryLabels;
using cace::exact::P1Affine;
using cace::exact::Point2;
using cace::exact::RT0Affine;
using cace::exact::Rational;

static int fail(int code, const std::string& message) {
    std::cerr << "FAIL " << code << ": " << message << "\n";
    return code;
}

int main() {
    try {
        if (Rational::parse("2/4") != Rational(1, 2)) return fail(2, "rational normalization");
        if (Rational::parse("-6/-8") != Rational(3, 4)) return fail(3, "sign normalization");
        if (Rational(1, 3) + Rational(1, 6) != Rational(1, 2)) return fail(4, "exact addition");
        if (Rational(7, 9) * Rational(27, 14) != Rational(3, 2)) return fail(5, "exact multiplication");

        bool rejected_bad_rational = false;
        try {
            (void)Rational::parse("0.5");
        } catch (const std::invalid_argument&) {
            rejected_bad_rational = true;
        }
        if (!rejected_bad_rational) return fail(6, "decimal text must not be silently treated as exact rational");

        std::vector<Point2> vertices{
            {Rational(0), Rational(0)},
            {Rational(1), Rational(0)},
            {Rational(1), Rational(1)},
            {Rational(0), Rational(1)},
            {Rational(1, 2), Rational(1, 2)},
        };
        std::vector<std::array<std::size_t, 3>> triangles{
            {0, 1, 4},
            {1, 2, 4},
            {2, 3, 4},
            {3, 0, 4},
        };
        BoundaryLabels labels{
            {{0, 1}, "bottom"},
            {{1, 2}, "right"},
            {{2, 3}, "top"},
            {{0, 3}, "left"},
        };

        const auto mesh = cace::exact::build_mesh(vertices, triangles, labels);
        if (mesh.vertices.size() != 5 || mesh.triangles.size() != 4 || mesh.edges.size() != 8) {
            return fail(7, "mesh counts");
        }
        if (mesh.interior_edge_ids.size() != 4 || mesh.boundary_edge_ids.size() != 4) {
            return fail(8, "edge ownership counts");
        }
        for (const auto& det : mesh.signed_jacobians) {
            if (det != Rational(1, 2)) return fail(9, "signed Jacobian");
        }

        std::vector<P1Affine> primal{
            {Rational(0), Rational(0), Rational(2)},
            {Rational(2), Rational(-2), Rational(0)},
            {Rational(2), Rational(0), Rational(-2)},
            {Rational(0), Rational(2), Rational(0)},
        };
        std::vector<RT0Affine> flux(4, RT0Affine{Rational(1), Rational(0), Rational(0)});

        const auto obligations = cace::exact::exact_assembly_obligations(mesh, primal, flux);
        const std::vector<Rational> expected{
            Rational(0), Rational(-1, 2), Rational(0), Rational(1, 2)
        };
        if (obligations.cell_pairings != expected) {
            return fail(10, "P1/RT0 cell pairing values differ from Lean fixture");
        }
        if (!obligations.all_local_green) return fail(11, "local Green identity");
        if (!obligations.orthogonality_sum_zero) return fail(12, "global orthogonality sum");
        if (obligations.global_pairing_sum != Rational(0)) return fail(13, "global pairing exact value");
        if (!obligations.ready_for_lean_assembly) return fail(14, "exact assembly admissibility");

        auto changed_flux = flux;
        changed_flux[0].radial = Rational(1);
        const auto changed = cace::exact::exact_assembly_obligations(mesh, primal, changed_flux);
        if (changed.ready_for_lean_assembly) {
            return fail(15, "changed RT0 field must not inherit assembly admissibility");
        }

        const auto packet_a = cace::exact::canonical_packet_text(mesh, primal, flux);
        const auto packet_b = cace::exact::canonical_packet_text(mesh, primal, flux);
        if (packet_a != packet_b) return fail(16, "canonical packet determinism");
        const auto changed_packet = cace::exact::canonical_packet_text(mesh, primal, changed_flux);
        if (packet_a == changed_packet) return fail(17, "mathematical field change must change canonical packet");

        bool rejected_clockwise = false;
        try {
            auto bad_triangles = triangles;
            bad_triangles[0] = {1, 0, 4};
            (void)cace::exact::build_mesh(vertices, bad_triangles, labels);
        } catch (const std::invalid_argument&) {
            rejected_clockwise = true;
        }
        if (!rejected_clockwise) return fail(18, "clockwise triangle rejection");

        bool rejected_nonmanifold = false;
        try {
            std::vector<Point2> nm_vertices{
                {Rational(0), Rational(0)},
                {Rational(1), Rational(0)},
                {Rational(0), Rational(1)},
                {Rational(1), Rational(-1)},
                {Rational(2), Rational(1)},
            };
            std::vector<std::array<std::size_t, 3>> nm_triangles{
                {0, 1, 2},
                {1, 0, 3},
                {0, 1, 4},
            };
            (void)cace::exact::build_mesh(nm_vertices, nm_triangles);
        } catch (const std::invalid_argument&) {
            rejected_nonmanifold = true;
        }
        if (!rejected_nonmanifold) return fail(19, "non-manifold edge rejection");

        std::cout << "cace-exact-fem FSL-0..6 kernel PASS\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "UNEXPECTED: " << exc.what() << "\n";
        return 99;
    }
}
