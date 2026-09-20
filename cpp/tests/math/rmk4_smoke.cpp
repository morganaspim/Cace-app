#include "cace/math/exact_linalg.hpp"
#include "cace/math/exterior.hpp"
#include "cace/math/packet.hpp"

#include <iostream>
#include <stdexcept>

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
    using cace::math::ExactExterior;
    using cace::math::ExactMatrix;
    using cace::math::ExactPlaneRotor;
    using cace::math::ExactVector;
    using cace::math::MathPacket;
    using cace::math::Rational;
    using cace::math::determinant;

    using Mask = ExactExterior::Mask;

    const auto e0 = ExactExterior::basis_vector(3, 0);
    const auto e1 = ExactExterior::basis_vector(3, 1);
    const auto e2 = ExactExterior::basis_vector(3, 2);

    const auto e01 = e0.wedge(e1);
    if (!(e01.coefficient(Mask(3)) == Rational(1))) return 10;
    if (!(e1.wedge(e0).coefficient(Mask(3)) == Rational(-1))) return 11;
    if (!e0.wedge(e0).is_zero()) return 12;

    if (!((e0.wedge(e1)).wedge(e2) == e0.wedge(e1.wedge(e2)))) return 13;

    if (!(e0.left_contraction(e01) == e1)) return 20;
    if (!(e1.left_contraction(e01) == -e0)) return 21;

    if (!(e0.hodge_dual() == e1.wedge(e2))) return 22;
    if (!(e1.hodge_dual() == -(e0.wedge(e2)))) return 23;

    const auto mixed = e0 + e01 + e2;
    if (!(mixed.grade(1) == e0 + e2)) return 24;
    if (!(mixed.grade(2) == e01)) return 25;
    if (!e01.is_homogeneous(2)) return 26;
    if (mixed.is_homogeneous(1)) return 27;

    ExactMatrix a(2, 2, {
        Rational(2), Rational(1),
        Rational(1), Rational(1)
    });
    const auto top = ExactExterior::basis_blade(2, Mask(3));
    const auto pushed = top.pushforward(a);
    if (!(pushed.coefficient(Mask(3)) == determinant(a))) return 30;

    const auto v = ExactExterior::basis_vector(2, 0);
    const auto pushed_v = v.pushforward(a);
    if (!(pushed_v.coefficient(Mask(1)) == Rational(2))) return 31;
    if (!(pushed_v.coefficient(Mask(2)) == Rational(1))) return 32;

    if (!throws_as<std::invalid_argument>([&] {
            (void)e0.wedge(ExactExterior::basis_vector(2, 0));
        })) return 33;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactExterior::basis_vector(3, 3);
        })) return 34;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactExterior::basis_blade(2, Mask(4));
        })) return 35;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactExterior(64);
        })) return 36;

    ExactPlaneRotor rotor(2, 0, 1, Rational(3, 5), Rational(4, 5));
    const ExactVector x{Rational(1), Rational(0)};
    const ExactVector y = rotor.apply(x);
    if (!(y == ExactVector{Rational(3, 5), Rational(4, 5)})) return 40;
    if (!(rotor.inverse().apply(y) == x)) return 41;

    const auto identity_rotor = rotor.compose_same_plane(rotor.inverse());
    if (!(identity_rotor.apply(x) == x)) return 42;
    if (!(determinant(rotor.matrix()) == Rational(1))) return 43;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactPlaneRotor(2, 0, 1, Rational(1), Rational(1));
        })) return 44;

    if (!throws_as<std::invalid_argument>([] {
            (void)ExactPlaneRotor(2, 0, 0, Rational(1), Rational(0));
        })) return 45;

    const auto exterior_packet = MathPacket::exact_exterior(mixed);
    const auto rotor_packet = MathPacket::exact_plane_rotor(rotor);
    if (exterior_packet.semantic_hash().size() != 64U) return 50;
    if (rotor_packet.semantic_hash().size() != 64U) return 51;

    if (MathPacket::exact_exterior(e0 + e2).canonical_serialize() !=
        MathPacket::exact_exterior(
            ExactExterior(3, {
                {Mask(4), Rational(1)},
                {Mask(1), Rational(1)}
            })
        ).canonical_serialize()) return 52;

    std::cout << "cace-rmk4-smoke PASS\n";
    return 0;
}
