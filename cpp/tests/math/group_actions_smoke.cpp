#include "cace/math/combinatorics.hpp"
#include "cace/math/packet.hpp"

#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

template <class Exception, class Fn>
bool throws_as(Fn&& fn) {
    try { fn(); }
    catch (const Exception&) { return true; }
    catch (...) { return false; }
    return false;
}

} // namespace

int main() {
    using cace::math::ExactAffineMap;
    using cace::math::ExactExterior;
    using cace::math::ExactMatrix;
    using cace::math::ExactPermutation;
    using cace::math::ExactSimplex;
    using cace::math::ExactVector;
    using cace::math::FinitePermutationGroup;
    using cace::math::MathPacket;
    using cace::math::Rational;
    using cace::math::binomial_checked;
    using cace::math::combinations;

    if (binomial_checked(5, 2) != 10U) return 10;
    if (binomial_checked(8, 0) != 1U) return 11;
    if (binomial_checked(3, 4) != 0U) return 12;

    const auto combos = combinations(5, 2);
    if (combos.size() != 10U) return 13;
    if (combos.front() != std::vector<std::size_t>{0, 1}) return 14;
    if (combos.back() != std::vector<std::size_t>{3, 4}) return 15;

    if (!throws_as<std::length_error>([] {
            (void)combinations(10, 5, 10);
        })) return 16;

    const ExactPermutation swap01({1, 0, 2});
    const ExactPermutation swap12({0, 2, 1});
    if (swap01.parity() != -1) return 20;
    if (!(swap01.inverse() == swap01)) return 21;

    const auto cycle = swap12.compose(swap01);
    if (cycle.apply_index(0) != 2U ||
        cycle.apply_index(1) != 0U ||
        cycle.apply_index(2) != 1U) return 22;

    const ExactVector v{Rational(10), Rational(20), Rational(30)};
    if (!(swap01.act_coordinates(v) ==
          ExactVector{Rational(20), Rational(10), Rational(30)})) return 23;

    if (!(cycle.act_coordinates(v) ==
          swap12.act_coordinates(swap01.act_coordinates(v)))) return 24;

    const ExactMatrix diag(3, 3, {
        Rational(1), Rational(), Rational(),
        Rational(), Rational(2), Rational(),
        Rational(), Rational(), Rational(3)
    });
    const auto conjugated = swap01.conjugate_square_matrix(diag);
    if (!(conjugated.at(0, 0) == Rational(2))) return 25;
    if (!(conjugated.at(1, 1) == Rational(1))) return 26;
    if (!(conjugated.at(2, 2) == Rational(3))) return 27;

    const ExactAffineMap affine(
        diag,
        ExactVector{Rational(1), Rational(2), Rational(3)});
    const auto permuted_affine = swap01.act_affine_coordinates(affine);
    const auto pv = swap01.act_coordinates(v);
    if (!(permuted_affine.apply(pv) ==
          swap01.act_coordinates(affine.apply(v)))) return 28;

    const auto e0 = ExactExterior::basis_vector(3, 0);
    const auto e1 = ExactExterior::basis_vector(3, 1);
    const auto e01 = e0.wedge(e1);
    if (!(swap01.act_exterior(e01) == -e01)) return 30;

    FinitePermutationGroup s3(3, {swap01, swap12});
    if (s3.size() != 6U) return 31;
    if (s3.orbit(0) != std::vector<std::size_t>{0, 1, 2}) return 32;
    if (s3.stabilizer(0).size() != 2U) return 33;

    const auto canonical = s3.canonical_coordinate_representative(
        ExactVector{Rational(3), Rational(1), Rational(2)});
    if (!(canonical == ExactVector{Rational(1), Rational(2), Rational(3)})) return 34;

    const auto exterior_canonical = s3.canonical_exterior_representative(e0 + e1);
    if (exterior_canonical.term_count() != 2U) return 35;

    const auto neighbors = s3.cayley_neighbors(ExactPermutation::identity(3));
    if (neighbors.size() != 2U) return 36;

    ExactSimplex triangle({
        ExactVector{Rational(0), Rational(0)},
        ExactVector{Rational(2), Rational(0)},
        ExactVector{Rational(0), Rational(3)}
    });
    const ExactPermutation swap_vertices({1, 0, 2});
    const auto swapped_triangle = swap_vertices.act_simplex_vertices(triangle);
    if (swapped_triangle.orientation() != -triangle.orientation()) return 40;

    if (!throws_as<std::length_error>([&] {
            (void)FinitePermutationGroup(3, {swap01, swap12}, 5);
        })) return 41;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactPermutation({0, 0});
        })) return 42;

    if (!throws_as<std::invalid_argument>([&] {
            (void)swap01.act_coordinates(ExactVector{Rational(1), Rational(2)});
        })) return 43;

    const auto permutation_packet = MathPacket::exact_permutation(swap01);
    const auto group_packet = MathPacket::finite_permutation_group(s3);
    if (permutation_packet.semantic_hash().size() != 64U) return 50;
    if (group_packet.semantic_hash().size() != 64U) return 51;

    FinitePermutationGroup s3_reordered(3, {swap12, swap01});
    if (MathPacket::finite_permutation_group(s3).canonical_serialize() !=
        MathPacket::finite_permutation_group(s3_reordered).canonical_serialize()) return 52;

    std::cout << "cace-group-actions-smoke PASS\n";
    return 0;
}
