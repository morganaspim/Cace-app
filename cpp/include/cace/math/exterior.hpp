#pragma once

#include "cace/math/sparse_matrix.hpp"

#include <bit>
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

class ExactExterior {
public:
    using Mask = std::uint64_t;

    ExactExterior() = default;
    explicit ExactExterior(std::size_t dimension) : dimension_(checked_dimension(dimension)) {}

    ExactExterior(std::size_t dimension, std::map<Mask, Rational> terms)
        : dimension_(checked_dimension(dimension)) {
        const Mask valid = full_mask(dimension_);
        for (auto& [mask, coefficient] : terms) {
            if ((mask & ~valid) != 0U) throw std::invalid_argument("exterior blade mask exceeds dimension");
            if (!coefficient.is_zero()) terms_.emplace(mask, coefficient);
        }
    }

    [[nodiscard]] static ExactExterior scalar(std::size_t dimension, const Rational& value) {
        if (value.is_zero()) return ExactExterior(dimension);
        return ExactExterior(dimension, {{0U, value}});
    }

    [[nodiscard]] static ExactExterior basis_vector(std::size_t dimension, std::size_t index) {
        if (index >= dimension) throw std::invalid_argument("basis vector index out of range");
        return ExactExterior(dimension, {{Mask(1) << index, Rational(1)}});
    }

    [[nodiscard]] static ExactExterior basis_blade(
        std::size_t dimension,
        Mask mask,
        const Rational& coefficient = Rational(1)) {
        return ExactExterior(dimension, {{mask, coefficient}});
    }

    [[nodiscard]] std::size_t dimension() const noexcept { return dimension_; }
    [[nodiscard]] std::size_t term_count() const noexcept { return terms_.size(); }
    [[nodiscard]] bool is_zero() const noexcept { return terms_.empty(); }
    [[nodiscard]] const std::map<Mask, Rational>& terms() const noexcept { return terms_; }

    [[nodiscard]] Rational coefficient(Mask mask) const {
        const auto it = terms_.find(mask);
        return it == terms_.end() ? Rational() : it->second;
    }

    [[nodiscard]] static std::size_t grade_of(Mask mask) noexcept {
        return static_cast<std::size_t>(std::popcount(mask));
    }

    [[nodiscard]] ExactExterior grade(std::size_t target_grade) const {
        std::map<Mask, Rational> out;
        for (const auto& [mask, coefficient] : terms_) {
            if (grade_of(mask) == target_grade) out.emplace(mask, coefficient);
        }
        return ExactExterior(dimension_, std::move(out));
    }

    [[nodiscard]] bool is_homogeneous(std::size_t target_grade) const noexcept {
        for (const auto& [mask, coefficient] : terms_) {
            (void)coefficient;
            if (grade_of(mask) != target_grade) return false;
        }
        return true;
    }

    [[nodiscard]] ExactExterior scaled(const Rational& factor) const {
        if (factor.is_zero()) return ExactExterior(dimension_);
        std::map<Mask, Rational> out;
        for (const auto& [mask, coefficient] : terms_) out.emplace(mask, coefficient * factor);
        return ExactExterior(dimension_, std::move(out));
    }

    [[nodiscard]] ExactExterior wedge(const ExactExterior& rhs) const {
        require_same_dimension(rhs);
        ExactExterior out(dimension_);
        for (const auto& [a, ca] : terms_) {
            for (const auto& [b, cb] : rhs.terms_) {
                if ((a & b) != 0U) continue;
                const int sign = wedge_sign(a, b);
                out.add_term(a | b, sign > 0 ? ca * cb : -(ca * cb));
            }
        }
        return out;
    }

    [[nodiscard]] ExactExterior left_contraction(const ExactExterior& rhs) const {
        require_same_dimension(rhs);
        ExactExterior out(dimension_);
        for (const auto& [a, ca] : terms_) {
            const auto ga = grade_of(a);
            for (const auto& [b, cb] : rhs.terms_) {
                const auto gb = grade_of(b);
                if (ga > gb || (a & b) != a) continue;
                const Mask remainder = b ^ a;
                const int sign = wedge_sign(a, remainder);
                out.add_term(remainder, sign > 0 ? ca * cb : -(ca * cb));
            }
        }
        return out;
    }

    [[nodiscard]] ExactExterior hodge_dual() const {
        ExactExterior out(dimension_);
        const Mask full = full_mask(dimension_);
        for (const auto& [mask, coefficient] : terms_) {
            const Mask complement = full ^ mask;
            const int sign = wedge_sign(mask, complement);
            out.add_term(complement, sign > 0 ? coefficient : -coefficient);
        }
        return out;
    }

    [[nodiscard]] ExactExterior pushforward(const ExactMatrix& linear) const {
        if (linear.cols() != dimension_) {
            throw std::invalid_argument("exterior pushforward input dimension mismatch");
        }
        if (linear.rows() > 63U) {
            throw std::invalid_argument("exterior pushforward output dimension exceeds mask capacity");
        }
        ExactExterior result(linear.rows());

        std::vector<ExactExterior> images;
        images.reserve(dimension_);
        for (std::size_t c = 0; c < dimension_; ++c) {
            ExactExterior image(linear.rows());
            for (std::size_t r = 0; r < linear.rows(); ++r) {
                if (!linear.at(r, c).is_zero()) image.add_term(Mask(1) << r, linear.at(r, c));
            }
            images.push_back(std::move(image));
        }

        for (const auto& [mask, coefficient] : terms_) {
            ExactExterior term = ExactExterior::scalar(linear.rows(), coefficient);
            for (std::size_t i = 0; i < dimension_; ++i) {
                if ((mask & (Mask(1) << i)) != 0U) term = term.wedge(images[i]);
            }
            result = result + term;
        }
        return result;
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "exterior:n=" + std::to_string(dimension_) + ":[";
        bool first = true;
        for (const auto& [mask, coefficient] : terms_) {
            if (!first) out.push_back(';');
            first = false;
            out += std::to_string(mask);
            out.push_back('=');
            out += coefficient.canonical_text();
        }
        out.push_back(']');
        return out;
    }

    friend ExactExterior operator+(const ExactExterior& lhs, const ExactExterior& rhs) {
        lhs.require_same_dimension(rhs);
        ExactExterior out = lhs;
        for (const auto& [mask, coefficient] : rhs.terms_) out.add_term(mask, coefficient);
        return out;
    }

    friend ExactExterior operator-(const ExactExterior& lhs, const ExactExterior& rhs) {
        lhs.require_same_dimension(rhs);
        ExactExterior out = lhs;
        for (const auto& [mask, coefficient] : rhs.terms_) out.add_term(mask, -coefficient);
        return out;
    }

    friend ExactExterior operator-(const ExactExterior& value) {
        return value.scaled(Rational(-1));
    }

    friend bool operator==(const ExactExterior&, const ExactExterior&) = default;

private:
    std::size_t dimension_ = 0;
    std::map<Mask, Rational> terms_;

    static std::size_t checked_dimension(std::size_t dimension) {
        if (dimension > 63U) {
            throw std::invalid_argument("exterior dimension exceeds 63-bit basis mask capacity");
        }
        return dimension;
    }

    [[nodiscard]] static Mask full_mask(std::size_t dimension) noexcept {
        return dimension == 0U ? 0U : ((Mask(1) << dimension) - 1U);
    }

    [[nodiscard]] static int wedge_sign(Mask a, Mask b) noexcept {
        unsigned parity = 0U;
        while (a != 0U) {
            const unsigned i = static_cast<unsigned>(std::countr_zero(a));
            const Mask lower = i == 0U ? 0U : ((Mask(1) << i) - 1U);
            parity ^= (std::popcount(b & lower) & 1U);
            a &= a - 1U;
        }
        return parity == 0U ? 1 : -1;
    }

    void add_term(Mask mask, const Rational& coefficient) {
        if (coefficient.is_zero()) return;
        auto [it, inserted] = terms_.emplace(mask, coefficient);
        if (!inserted) {
            it->second += coefficient;
            if (it->second.is_zero()) terms_.erase(it);
        }
    }

    void require_same_dimension(const ExactExterior& rhs) const {
        if (dimension_ != rhs.dimension_) {
            throw std::invalid_argument("exterior dimension mismatch");
        }
    }
};

class ExactPlaneRotor {
public:
    ExactPlaneRotor(
        std::size_t dimension,
        std::size_t i,
        std::size_t j,
        Rational cosine,
        Rational sine)
        : dimension_(dimension),
          i_(i),
          j_(j),
          cosine_(std::move(cosine)),
          sine_(std::move(sine)) {
        if (dimension_ == 0U || i_ >= dimension_ || j_ >= dimension_ || i_ == j_) {
            throw std::invalid_argument("invalid rotor plane");
        }
        if (!(cosine_ * cosine_ + sine_ * sine_ == Rational(1))) {
            throw std::invalid_argument("exact plane rotor requires c^2+s^2=1");
        }
    }

    [[nodiscard]] std::size_t dimension() const noexcept { return dimension_; }
    [[nodiscard]] std::size_t first_axis() const noexcept { return i_; }
    [[nodiscard]] std::size_t second_axis() const noexcept { return j_; }
    [[nodiscard]] const Rational& cosine() const noexcept { return cosine_; }
    [[nodiscard]] const Rational& sine() const noexcept { return sine_; }

    [[nodiscard]] ExactVector apply(const ExactVector& vector) const {
        if (vector.size() != dimension_) {
            throw std::invalid_argument("rotor/vector dimension mismatch");
        }
        std::vector<Rational> out = vector.values();
        const Rational xi = vector.at(i_);
        const Rational xj = vector.at(j_);
        out[i_] = cosine_ * xi - sine_ * xj;
        out[j_] = sine_ * xi + cosine_ * xj;
        return ExactVector(std::move(out));
    }

    [[nodiscard]] ExactMatrix matrix() const {
        ExactMatrix out = ExactMatrix::identity(dimension_);
        out.at(i_, i_) = cosine_;
        out.at(i_, j_) = -sine_;
        out.at(j_, i_) = sine_;
        out.at(j_, j_) = cosine_;
        return out;
    }

    [[nodiscard]] ExactPlaneRotor inverse() const {
        return ExactPlaneRotor(dimension_, i_, j_, cosine_, -sine_);
    }

    [[nodiscard]] ExactPlaneRotor compose_same_plane(const ExactPlaneRotor& inner) const {
        if (dimension_ != inner.dimension_ || i_ != inner.i_ || j_ != inner.j_) {
            throw std::invalid_argument("rotor composition requires identical plane");
        }
        return ExactPlaneRotor(
            dimension_,
            i_,
            j_,
            cosine_ * inner.cosine_ - sine_ * inner.sine_,
            sine_ * inner.cosine_ + cosine_ * inner.sine_);
    }

    [[nodiscard]] std::string canonical_text() const {
        return "rotor:n=" + std::to_string(dimension_) +
               ";plane=" + std::to_string(i_) + "," + std::to_string(j_) +
               ";c=" + cosine_.canonical_text() +
               ";s=" + sine_.canonical_text();
    }

    friend bool operator==(const ExactPlaneRotor&, const ExactPlaneRotor&) = default;

private:
    std::size_t dimension_ = 0;
    std::size_t i_ = 0;
    std::size_t j_ = 0;
    Rational cosine_;
    Rational sine_;
};

} // namespace cace::math
