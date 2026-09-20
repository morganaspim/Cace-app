#pragma once

#include "cace/math/exact_linalg.hpp"

#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

class ExactAffineMap {
public:
    ExactAffineMap() = default;

    ExactAffineMap(ExactMatrix linear, ExactVector translation)
        : linear_(std::move(linear)), translation_(std::move(translation)) {
        if (linear_.rows() != translation_.size()) {
            throw std::invalid_argument("affine translation/output dimension mismatch");
        }
    }

    [[nodiscard]] static ExactAffineMap identity(std::size_t dimension) {
        return ExactAffineMap(ExactMatrix::identity(dimension), ExactVector(std::vector<Rational>(dimension)));
    }

    [[nodiscard]] std::size_t input_dimension() const noexcept { return linear_.cols(); }
    [[nodiscard]] std::size_t output_dimension() const noexcept { return linear_.rows(); }
    [[nodiscard]] const ExactMatrix& linear() const noexcept { return linear_; }
    [[nodiscard]] const ExactVector& translation() const noexcept { return translation_; }

    [[nodiscard]] ExactVector apply(const ExactVector& point) const {
        if (point.size() != input_dimension()) throw std::invalid_argument("affine input dimension mismatch");
        return linear_.matvec(point) + translation_;
    }

    [[nodiscard]] ExactAffineMap compose(const ExactAffineMap& inner) const {
        if (inner.output_dimension() != input_dimension()) {
            throw std::invalid_argument("affine composition dimension mismatch");
        }
        return ExactAffineMap(
            linear_.matmul(inner.linear_),
            linear_.matvec(inner.translation_) + translation_);
    }

    [[nodiscard]] ExactAffineMap inverse() const {
        if (input_dimension() != output_dimension()) {
            throw std::invalid_argument("affine inverse requires square linear part");
        }
        const ExactMatrix inv = inverse_nonsingular(linear_);
        return ExactAffineMap(inv, inv.matvec(translation_).scaled(Rational(-1)));
    }

    [[nodiscard]] Rational jacobian_determinant() const {
        if (input_dimension() != output_dimension()) {
            throw std::invalid_argument("affine Jacobian determinant requires square linear part");
        }
        return determinant(linear_);
    }

    [[nodiscard]] std::string canonical_text() const {
        return "affine:{linear=" + linear_.canonical_text() + ";translation=" +
               translation_.canonical_text() + "}";
    }

    friend bool operator==(const ExactAffineMap&, const ExactAffineMap&) = default;

private:
    ExactMatrix linear_;
    ExactVector translation_;
};

} // namespace cace::math
