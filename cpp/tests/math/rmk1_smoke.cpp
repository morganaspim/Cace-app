#include "cace/math/packet.hpp"
#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

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
    using cace::math::ExactFixedVector;
    using cace::math::ExactVector;
    using cace::math::MathPacket;
    using cace::math::Rational;
    using cace::math::semantic_sha256;

    if (!(Rational(2, 4) == Rational(1, 2))) return 10;
    if (!(Rational(-2, -4) == Rational(1, 2))) return 11;
    if (!(Rational(0, -9) == Rational(0, 1))) return 12;
    if (!(Rational(1, 6) + Rational(1, 3) == Rational(1, 2))) return 13;
    if (!(Rational(7, 9) - Rational(1, 9) == Rational(2, 3))) return 14;
    if (!(Rational(3, 7) * Rational(14, 9) == Rational(2, 3))) return 15;
    if (!(Rational(2, 3) / Rational(4, 5) == Rational(5, 6))) return 16;
    if (!(Rational(-1, 3) < Rational(0))) return 17;
    if (Rational(3, 1).integer_exact() != 3) return 18;
    if (!throws_as<std::domain_error>([] { (void)Rational(1, 2).integer_exact(); })) return 19;
    if (!throws_as<std::invalid_argument>([] { (void)Rational(1, 0); })) return 20;
    if (!throws_as<std::domain_error>([] { (void)(Rational(1, 2) / Rational(0)); })) return 21;

    const auto max = std::numeric_limits<std::int64_t>::max();
    if (!throws_as<std::overflow_error>([&] { (void)(Rational(max) + Rational(1)); })) return 22;
    if (!(Rational(max, 2) * Rational(2, max) == Rational(1))) return 23;

    ExactVector a{Rational(1, 2), Rational(1, 3)};
    ExactVector b{Rational(2), Rational(3)};
    if (!(a.dot(b) == Rational(2))) return 30;
    if (!(a.squared_l2_norm() == Rational(13, 36))) return 31;
    if (!(a.scaled(Rational(6)).canonical_text() == "[3/1,2/1]")) return 32;
    if (!throws_as<std::invalid_argument>([&] { (void)a.dot(ExactVector{Rational(1)}); })) return 33;

    ExactFixedVector<2> fixed(std::array<Rational, 2>{Rational(1, 2), Rational(3, 2)});
    if (!(fixed.dot(fixed) == Rational(5, 2))) return 34;

    if (semantic_sha256("abc") != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") return 40;

    MathPacket p1 = MathPacket::exact_vector(a);
    p1.dependency_hashes = {
        semantic_sha256("dep-b"),
        semantic_sha256("dep-a"),
        semantic_sha256("dep-b")
    };
    MathPacket p2 = p1;
    p2.dependency_hashes = {
        semantic_sha256("dep-a"),
        semantic_sha256("dep-b")
    };
    if (p1.canonical_serialize() != p2.canonical_serialize()) return 41;
    if (p1.semantic_hash() != p2.semantic_hash()) return 42;
    if (p1.semantic_hash().size() != 64U) return 43;

    MathPacket bad = MathPacket::rational(Rational(1, 2));
    bad.dependency_hashes = {"ABC"};
    if (!throws_as<std::invalid_argument>([&] { (void)bad.canonical_serialize(); })) return 44;

    std::cout << "cace-rmk1-smoke PASS\n";
    return 0;
}
