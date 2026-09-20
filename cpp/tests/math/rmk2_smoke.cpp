#include "cace/math/exact_linalg.hpp"
#include "cace/math/packet.hpp"
#include "cace/math/sparse_matrix.hpp"

#include <iostream>
#include <stdexcept>
#include <tuple>
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
    using cace::math::ExactMatrix;
    using cace::math::ExactSparseMatrix;
    using cace::math::ExactVector;
    using cace::math::MathPacket;
    using cace::math::Rational;
    using cace::math::determinant;
    using cace::math::inverse_nonsingular;
    using cace::math::is_negative_definite;
    using cace::math::is_positive_definite;
    using cace::math::nullspace;
    using cace::math::rank;
    using cace::math::rref;
    using cace::math::solve_nonsingular;
    using cace::math::verify_inverse;
    using cace::math::verify_solution;

    ExactMatrix a(2, 2, {
        Rational(2), Rational(1),
        Rational(1), Rational(1)
    });

    if (!(determinant(a) == Rational(1))) return 10;
    if (rank(a) != 2) return 11;

    ExactVector b{Rational(5), Rational(3)};
    const ExactVector x = solve_nonsingular(a, b);
    if (!(x == ExactVector{Rational(2), Rational(1)})) return 12;
    if (!verify_solution(a, x, b)) return 13;

    const ExactMatrix inv = inverse_nonsingular(a);
    if (!verify_inverse(a, inv)) return 14;
    if (!(inv == ExactMatrix(2, 2, {
        Rational(1), Rational(-1),
        Rational(-1), Rational(2)
    }))) return 15;

    ExactMatrix singular(2, 2, {
        Rational(1), Rational(2),
        Rational(2), Rational(4)
    });
    if (rank(singular) != 1) return 20;
    if (!(determinant(singular) == Rational())) return 21;
    if (!throws_as<std::domain_error>([&] {
            (void)solve_nonsingular(singular, ExactVector{Rational(1), Rational(2)});
        })) return 22;
    if (!throws_as<std::domain_error>([&] { (void)inverse_nonsingular(singular); })) return 23;

    ExactMatrix wide(2, 3, {
        Rational(1), Rational(2), Rational(3),
        Rational(2), Rational(4), Rational(6)
    });
    const auto rr = rref(wide);
    if (rr.pivot_columns != std::vector<std::size_t>{0}) return 30;
    if (!(rr.matrix == ExactMatrix(2, 3, {
        Rational(1), Rational(2), Rational(3),
        Rational(), Rational(), Rational()
    }))) return 31;

    const auto ns = nullspace(wide);
    if (ns.size() != 2) return 32;
    for (const auto& v : ns) {
        if (!(wide.matvec(v) == ExactVector{Rational(), Rational()})) return 33;
    }

    std::vector<std::tuple<std::size_t, std::size_t, Rational>> triplets{
        {0, 0, Rational(1)},
        {0, 0, Rational(2)},
        {0, 1, Rational(4)},
        {0, 1, Rational(-4)},
        {1, 0, Rational(5)},
        {1, 1, Rational(6)}
    };
    ExactSparseMatrix s = ExactSparseMatrix::from_triplets(2, 2, triplets);
    if (s.nnz() != 3) return 40;
    if (!(s.at(0, 0) == Rational(3))) return 41;
    if (!(s.at(0, 1) == Rational())) return 42;
    if (!(s.matvec(ExactVector{Rational(2), Rational(1)}) ==
          ExactVector{Rational(6), Rational(16)})) return 43;

    const auto st = s.transpose();
    if (!(st.at(0, 1) == Rational(5))) return 44;
    if (!(st.at(1, 1) == Rational(6))) return 45;

    const auto product = s.matmul(st);
    const ExactMatrix expected_product(2, 2, {
        Rational(9), Rational(15),
        Rational(15), Rational(61)
    });
    if (!(product.to_dense() == expected_product)) return 46;

    const auto rp = s.row_permuted({1, 0});
    if (!(rp.at(0, 0) == Rational(5) && rp.at(1, 0) == Rational(3))) return 47;
    const auto cp = s.col_permuted({1, 0});
    if (!(cp.at(1, 0) == Rational(6) && cp.at(1, 1) == Rational(5))) return 48;

    if (!throws_as<std::invalid_argument>([&] { (void)s.row_permuted({0, 0}); })) return 49;
    if (!throws_as<std::invalid_argument>([] {
            (void)ExactSparseMatrix::from_triplets(
                2, 2, {{2, 0, Rational(1)}});
        })) return 50;

    const MathPacket dense_packet = MathPacket::exact_matrix(a);
    const MathPacket sparse_packet = MathPacket::exact_sparse_matrix(s);
    if (dense_packet.semantic_hash().size() != 64U) return 60;
    if (sparse_packet.semantic_hash().size() != 64U) return 61;
    if (MathPacket::exact_sparse_matrix(s).canonical_serialize() !=
        MathPacket::exact_sparse_matrix(
            ExactSparseMatrix::from_triplets(2, 2, {
                {1, 1, Rational(6)},
                {0, 0, Rational(3)},
                {1, 0, Rational(5)}
            })).canonical_serialize()) return 62;

    ExactMatrix spd(2, 2, {
        Rational(2), Rational(1),
        Rational(1), Rational(2)
    });
    if (!is_positive_definite(spd)) return 70;

    ExactMatrix nd(2, 2, {
        Rational(-2), Rational(-1),
        Rational(-1), Rational(-2)
    });
    if (!is_negative_definite(nd)) return 71;

    ExactMatrix nonsymmetric(2, 2, {
        Rational(1), Rational(2),
        Rational(0), Rational(1)
    });
    if (is_positive_definite(nonsymmetric)) return 72;

    const ExactMatrix id3 = ExactMatrix::identity(3);
    if (rank(id3) != 3 || determinant(id3) != Rational(1)) return 80;
    if (!(id3.matmul(id3) == id3)) return 81;

    std::cout << "cace-rmk2-smoke PASS\n";
    return 0;
}
