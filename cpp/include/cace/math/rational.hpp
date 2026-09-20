#pragma once

#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>

namespace cace::math {

class Rational {
public:
    using rep = std::int64_t;

    constexpr Rational() noexcept = default;
    explicit constexpr Rational(rep integer) noexcept : num_(integer), den_(1) {}

    Rational(rep numerator, rep denominator) {
        assign_wide(static_cast<wide>(numerator), static_cast<wide>(denominator));
    }

    [[nodiscard]] constexpr rep numerator() const noexcept { return num_; }
    [[nodiscard]] constexpr rep denominator() const noexcept { return den_; }
    [[nodiscard]] constexpr bool is_zero() const noexcept { return num_ == 0; }
    [[nodiscard]] constexpr bool is_integer() const noexcept { return den_ == 1; }

    [[nodiscard]] rep integer_exact() const {
        if (den_ != 1) throw std::domain_error("rational is not an integer");
        return num_;
    }

    [[nodiscard]] std::string canonical_text() const {
        return std::to_string(num_) + "/" + std::to_string(den_);
    }

    [[nodiscard]] long double to_long_double() const noexcept {
        return static_cast<long double>(num_) / static_cast<long double>(den_);
    }

    Rational& operator+=(const Rational& rhs) { *this = *this + rhs; return *this; }
    Rational& operator-=(const Rational& rhs) { *this = *this - rhs; return *this; }
    Rational& operator*=(const Rational& rhs) { *this = *this * rhs; return *this; }
    Rational& operator/=(const Rational& rhs) { *this = *this / rhs; return *this; }

    friend Rational operator+(const Rational& lhs, const Rational& rhs) {
        return from_wide(static_cast<wide>(lhs.num_) * rhs.den_ + static_cast<wide>(rhs.num_) * lhs.den_,
                         static_cast<wide>(lhs.den_) * rhs.den_);
    }

    friend Rational operator-(const Rational& lhs, const Rational& rhs) {
        return from_wide(static_cast<wide>(lhs.num_) * rhs.den_ - static_cast<wide>(rhs.num_) * lhs.den_,
                         static_cast<wide>(lhs.den_) * rhs.den_);
    }

    friend Rational operator*(const Rational& lhs, const Rational& rhs) {
        return from_wide(static_cast<wide>(lhs.num_) * rhs.num_,
                         static_cast<wide>(lhs.den_) * rhs.den_);
    }

    friend Rational operator/(const Rational& lhs, const Rational& rhs) {
        if (rhs.num_ == 0) throw std::domain_error("division by zero rational");
        return from_wide(static_cast<wide>(lhs.num_) * rhs.den_,
                         static_cast<wide>(lhs.den_) * rhs.num_);
    }

    friend Rational operator-(const Rational& value) {
        return from_wide(-static_cast<wide>(value.num_), static_cast<wide>(value.den_));
    }

    friend bool operator==(const Rational&, const Rational&) = default;

    friend bool operator<(const Rational& lhs, const Rational& rhs) noexcept {
        return static_cast<wide>(lhs.num_) * rhs.den_ < static_cast<wide>(rhs.num_) * lhs.den_;
    }
    friend bool operator>(const Rational& lhs, const Rational& rhs) noexcept { return rhs < lhs; }
    friend bool operator<=(const Rational& lhs, const Rational& rhs) noexcept { return !(rhs < lhs); }
    friend bool operator>=(const Rational& lhs, const Rational& rhs) noexcept { return !(lhs < rhs); }

private:
    using wide = __int128_t;
    using uwide = __uint128_t;

    rep num_ = 0;
    rep den_ = 1;

    static constexpr uwide magnitude(wide x) noexcept {
        return x < 0 ? static_cast<uwide>(-(x + 1)) + 1 : static_cast<uwide>(x);
    }

    static constexpr uwide gcd_wide(uwide a, uwide b) noexcept {
        while (b != 0) {
            const uwide r = a % b;
            a = b;
            b = r;
        }
        return a;
    }

    static rep checked_rep(wide value) {
        constexpr wide lo = static_cast<wide>(std::numeric_limits<rep>::min());
        constexpr wide hi = static_cast<wide>(std::numeric_limits<rep>::max());
        if (value < lo || value > hi) throw std::overflow_error("rational component exceeds int64 range");
        return static_cast<rep>(value);
    }

    void assign_wide(wide numerator, wide denominator) {
        if (denominator == 0) throw std::invalid_argument("rational denominator must be nonzero");
        if (numerator == 0) {
            num_ = 0;
            den_ = 1;
            return;
        }
        const uwide g = gcd_wide(magnitude(numerator), magnitude(denominator));
        numerator /= static_cast<wide>(g);
        denominator /= static_cast<wide>(g);
        if (denominator < 0) {
            numerator = -numerator;
            denominator = -denominator;
        }
        num_ = checked_rep(numerator);
        den_ = checked_rep(denominator);
        if (den_ <= 0) throw std::overflow_error("normalized rational denominator is not representable");
    }

    static Rational from_wide(wide numerator, wide denominator) {
        Rational out;
        out.assign_wide(numerator, denominator);
        return out;
    }
};

} // namespace cace::math
