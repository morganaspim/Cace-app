#include "cace/math/affine.hpp"
#include "cace/math/geometry.hpp"
#include "cace/math/packet.hpp"
#include "cace/math/polynomial.hpp"

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
    using cace::math::ExactMatrix;
    using cace::math::ExactPolynomial;
    using cace::math::ExactSimplex;
    using cace::math::ExactVector;
    using cace::math::MathPacket;
    using cace::math::Rational;

    using E = ExactPolynomial::Exponents;

    ExactPolynomial p(2, {
        {E{2, 1}, Rational(2)},
        {E{0, 1}, Rational(-3)},
        {E{0, 0}, Rational(1)}
    });
    const ExactVector q{Rational(2), Rational(3)};

    if (p.total_degree() != 3U) return 10;
    if (!(p.evaluate(q) == Rational(16))) return 11;
    if (!(p.derivative(0).evaluate(q) == Rational(24))) return 12;
    if (!(p.derivative(1).evaluate(q) == Rational(5))) return 13;

    const auto gradient = p.gradient();
    if (gradient.size() != 2U) return 14;
    const auto hessian = p.hessian();
    if (!(hessian.at(0).at(1).evaluate(q) == Rational(8))) return 15;

    const auto x = ExactPolynomial::variable(2, 0);
    const auto y = ExactPolynomial::variable(2, 1);
    const auto square = (x + y) * (x + y);
    if (!(square.evaluate(ExactVector{Rational(2), Rational(3)}) == Rational(25))) return 16;

    const auto shifted = p.compose({
        x + ExactPolynomial::constant(2, Rational(1)),
        y
    });
    if (!(shifted.evaluate(ExactVector{Rational(1), Rational(3)}) == p.evaluate(q))) return 17;

    ExactPolynomial duplicate_terms(2, {
        {E{1, 0}, Rational(4)},
        {E{1, 0}, Rational(-4)},
        {E{0, 0}, Rational(2)}
    });
    if (duplicate_terms.term_count() != 1U) return 18;
    if (!(duplicate_terms.evaluate(q) == Rational(2))) return 19;

    if (!throws_as<std::invalid_argument>([&] {
            (void)p.evaluate(ExactVector{Rational(1)});
        })) return 20;
    if (!throws_as<std::invalid_argument>([&] {
            (void)p.derivative(2);
        })) return 21;
    if (!throws_as<std::invalid_argument>([] {
            (void)ExactPolynomial(2, {{E{1}, Rational(1)}});
        })) return 22;

    ExactAffineMap affine(
        ExactMatrix(2, 2, {
            Rational(2), Rational(),
            Rational(), Rational(3)
        }),
        ExactVector{Rational(1), Rational(-1)}
    );

    const ExactVector point{Rational(2), Rational(4)};
    const ExactVector mapped = affine.apply(point);
    if (!(mapped == ExactVector{Rational(5), Rational(11)})) return 30;
    if (!(affine.inverse().apply(mapped) == point)) return 31;
    if (!(affine.jacobian_determinant() == Rational(6))) return 32;
    if (!(affine.compose(ExactAffineMap::identity(2)).apply(point) == mapped)) return 33;

    ExactAffineMap translate(
        ExactMatrix::identity(2),
        ExactVector{Rational(3), Rational(5)}
    );
    const auto composed = affine.compose(translate);
    if (!(composed.apply(point) == affine.apply(translate.apply(point)))) return 34;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactAffineMap(
                ExactMatrix(2, 3),
                ExactVector{Rational(1)}
            );
        })) return 35;
    if (!throws_as<std::domain_error>([] {
            ExactAffineMap singular(
                ExactMatrix(2, 2, {
                    Rational(1), Rational(2),
                    Rational(2), Rational(4)
                }),
                ExactVector{Rational(), Rational()}
            );
            (void)singular.inverse();
        })) return 36;

    ExactSimplex triangle({
        ExactVector{Rational(0), Rational(0)},
        ExactVector{Rational(2), Rational(0)},
        ExactVector{Rational(0), Rational(3)}
    });

    if (!(triangle.signed_jacobian() == Rational(6))) return 40;
    if (!(triangle.volume() == Rational(3))) return 41;
    if (triangle.orientation() != 1) return 42;

    const ExactVector sample{Rational(1, 2), Rational(3, 4)};
    const ExactVector bary = triangle.barycentric_coordinates(sample);
    if (!(bary == ExactVector{Rational(1, 2), Rational(1, 4), Rational(1, 4)})) return 43;
    if (!(triangle.from_barycentric(bary) == sample)) return 44;
    if (!triangle.contains_closed(sample)) return 45;
    if (triangle.contains_closed(ExactVector{Rational(3), Rational(3)})) return 46;
    if (!(triangle.reference_map().apply(ExactVector{Rational(1, 4), Rational(1, 4)}) == sample)) return 47;

    ExactSimplex flipped({
        ExactVector{Rational(0), Rational(0)},
        ExactVector{Rational(0), Rational(3)},
        ExactVector{Rational(2), Rational(0)}
    });
    if (flipped.orientation() != -1) return 48;
    if (!(flipped.signed_volume() == Rational(-3))) return 49;

    ExactSimplex tetrahedron({
        ExactVector{Rational(0), Rational(0), Rational(0)},
        ExactVector{Rational(1), Rational(0), Rational(0)},
        ExactVector{Rational(0), Rational(1), Rational(0)},
        ExactVector{Rational(0), Rational(0), Rational(1)}
    });
    if (!(tetrahedron.volume() == Rational(1, 6))) return 50;

    if (!throws_as<std::domain_error>([] {
            ExactSimplex degenerate({
                ExactVector{Rational(0), Rational(0)},
                ExactVector{Rational(1), Rational(0)},
                ExactVector{Rational(2), Rational(0)}
            });
            (void)degenerate.barycentric_coordinates(ExactVector{Rational(1), Rational(0)});
        })) return 51;

    if (!throws_as<std::invalid_argument>([&] {
            (void)triangle.from_barycentric(
                ExactVector{Rational(1), Rational(1), Rational(1)});
        })) return 52;

    const auto poly_packet = MathPacket::exact_polynomial(p);
    const auto affine_packet = MathPacket::exact_affine_map(affine);
    const auto simplex_packet = MathPacket::exact_simplex(triangle);
    if (poly_packet.semantic_hash().size() != 64U) return 60;
    if (affine_packet.semantic_hash().size() != 64U) return 61;
    if (simplex_packet.semantic_hash().size() != 64U) return 62;

    if (MathPacket::exact_polynomial(p).canonical_serialize() !=
        MathPacket::exact_polynomial(
            ExactPolynomial(2, {
                {E{0, 0}, Rational(1)},
                {E{0, 1}, Rational(-3)},
                {E{2, 1}, Rational(2)}
            })
        ).canonical_serialize()) return 63;

    std::cout << "cace-rmk3-smoke PASS\n";
    return 0;
}
