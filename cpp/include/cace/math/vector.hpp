#pragma once

#include "cace/math/rational.hpp"

#include <array>
#include <cstddef>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

class ExactVector {
public:
    ExactVector() = default;
    explicit ExactVector(std::vector<Rational> values) : values_(std::move(values)) {}
    ExactVector(std::initializer_list<Rational> values) : values_(values) {}

    [[nodiscard]] std::size_t size() const noexcept { return values_.size(); }
    [[nodiscard]] bool empty() const noexcept { return values_.empty(); }
    [[nodiscard]] const Rational& at(std::size_t i) const { return values_.at(i); }
    [[nodiscard]] Rational& at(std::size_t i) { return values_.at(i); }
    [[nodiscard]] const std::vector<Rational>& values() const noexcept { return values_; }

    [[nodiscard]] Rational dot(const ExactVector& rhs) const {
        require_same_size(rhs);
        Rational sum;
        for (std::size_t i = 0; i < values_.size(); ++i) sum += values_[i] * rhs.values_[i];
        return sum;
    }

    [[nodiscard]] Rational squared_l2_norm() const { return dot(*this); }

    [[nodiscard]] ExactVector scaled(const Rational& factor) const {
        std::vector<Rational> out;
        out.reserve(values_.size());
        for (const auto& v : values_) out.push_back(v * factor);
        return ExactVector(std::move(out));
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "[";
        for (std::size_t i = 0; i < values_.size(); ++i) {
            if (i != 0) out.push_back(',');
            out += values_[i].canonical_text();
        }
        out.push_back(']');
        return out;
    }

    friend ExactVector operator+(const ExactVector& lhs, const ExactVector& rhs) {
        lhs.require_same_size(rhs);
        std::vector<Rational> out;
        out.reserve(lhs.size());
        for (std::size_t i = 0; i < lhs.size(); ++i) out.push_back(lhs.values_[i] + rhs.values_[i]);
        return ExactVector(std::move(out));
    }

    friend ExactVector operator-(const ExactVector& lhs, const ExactVector& rhs) {
        lhs.require_same_size(rhs);
        std::vector<Rational> out;
        out.reserve(lhs.size());
        for (std::size_t i = 0; i < lhs.size(); ++i) out.push_back(lhs.values_[i] - rhs.values_[i]);
        return ExactVector(std::move(out));
    }

    friend bool operator==(const ExactVector&, const ExactVector&) = default;

private:
    std::vector<Rational> values_;

    void require_same_size(const ExactVector& rhs) const {
        if (values_.size() != rhs.values_.size()) throw std::invalid_argument("exact vector size mismatch");
    }
};

template <std::size_t N>
class ExactFixedVector {
public:
    ExactFixedVector() = default;
    explicit ExactFixedVector(std::array<Rational, N> values) : values_(std::move(values)) {}

    [[nodiscard]] static constexpr std::size_t size() noexcept { return N; }
    [[nodiscard]] const Rational& at(std::size_t i) const { return values_.at(i); }
    [[nodiscard]] const std::array<Rational, N>& values() const noexcept { return values_; }

    [[nodiscard]] Rational dot(const ExactFixedVector& rhs) const {
        Rational sum;
        for (std::size_t i = 0; i < N; ++i) sum += values_[i] * rhs.values_[i];
        return sum;
    }

    [[nodiscard]] ExactVector dynamic() const {
        return ExactVector(std::vector<Rational>(values_.begin(), values_.end()));
    }

    friend bool operator==(const ExactFixedVector&, const ExactFixedVector&) = default;

private:
    std::array<Rational, N> values_{};
};

} // namespace cace::math
