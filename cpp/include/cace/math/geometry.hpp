#pragma once

#include "cace/math/affine.hpp"

#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

class ExactSimplex {
public:
    explicit ExactSimplex(std::vector<ExactVector> vertices)
        : vertices_(std::move(vertices)) {
        if (vertices_.size() < 2U) throw std::invalid_argument("simplex requires dimension at least one");
        dimension_ = vertices_.size() - 1U;
        for (const auto& vertex : vertices_) {
            if (vertex.size() != dimension_) {
                throw std::invalid_argument("simplex must have d+1 vertices in d dimensions");
            }
        }
    }

    [[nodiscard]] std::size_t dimension() const noexcept { return dimension_; }
    [[nodiscard]] const std::vector<ExactVector>& vertices() const noexcept { return vertices_; }

    [[nodiscard]] ExactMatrix edge_matrix() const {
        ExactMatrix out(dimension_, dimension_);
        for (std::size_t c = 0; c < dimension_; ++c) {
            const ExactVector edge = vertices_[c + 1] - vertices_[0];
            for (std::size_t r = 0; r < dimension_; ++r) out.at(r, c) = edge.at(r);
        }
        return out;
    }

    [[nodiscard]] Rational signed_jacobian() const { return determinant(edge_matrix()); }

    [[nodiscard]] int orientation() const {
        const Rational d = signed_jacobian();
        if (d > Rational()) return 1;
        if (d < Rational()) return -1;
        return 0;
    }

    [[nodiscard]] Rational signed_volume() const {
        return signed_jacobian() / Rational(checked_factorial(dimension_));
    }

    [[nodiscard]] Rational volume() const {
        const Rational v = signed_volume();
        return v < Rational() ? -v : v;
    }

    [[nodiscard]] ExactVector barycentric_coordinates(const ExactVector& point) const {
        if (point.size() != dimension_) throw std::invalid_argument("barycentric point dimension mismatch");
        const ExactVector tail = solve_nonsingular(edge_matrix(), point - vertices_[0]);
        std::vector<Rational> lambda(dimension_ + 1U);
        Rational sum;
        for (std::size_t i = 0; i < dimension_; ++i) {
            lambda[i + 1U] = tail.at(i);
            sum += tail.at(i);
        }
        lambda[0] = Rational(1) - sum;
        return ExactVector(std::move(lambda));
    }

    [[nodiscard]] ExactVector from_barycentric(const ExactVector& lambda) const {
        if (lambda.size() != dimension_ + 1U) throw std::invalid_argument("barycentric coordinate count mismatch");
        Rational sum;
        for (std::size_t i = 0; i < lambda.size(); ++i) sum += lambda.at(i);
        if (!(sum == Rational(1))) throw std::invalid_argument("barycentric coordinates must sum exactly to one");

        std::vector<Rational> point(dimension_);
        for (std::size_t i = 0; i < vertices_.size(); ++i) {
            for (std::size_t d = 0; d < dimension_; ++d) point[d] += lambda.at(i) * vertices_[i].at(d);
        }
        return ExactVector(std::move(point));
    }

    [[nodiscard]] bool contains_closed(const ExactVector& point) const {
        const ExactVector lambda = barycentric_coordinates(point);
        for (std::size_t i = 0; i < lambda.size(); ++i) {
            if (lambda.at(i) < Rational()) return false;
        }
        return true;
    }

    [[nodiscard]] ExactAffineMap reference_map() const {
        return ExactAffineMap(edge_matrix(), vertices_[0]);
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "simplex:d=" + std::to_string(dimension_) + ":[";
        for (std::size_t i = 0; i < vertices_.size(); ++i) {
            if (i != 0) out.push_back(';');
            out += vertices_[i].canonical_text();
        }
        out.push_back(']');
        return out;
    }

    friend bool operator==(const ExactSimplex&, const ExactSimplex&) = default;

private:
    std::size_t dimension_ = 0;
    std::vector<ExactVector> vertices_;

    [[nodiscard]] static Rational::rep checked_factorial(std::size_t n) {
        Rational::rep value = 1;
        const auto max = std::numeric_limits<Rational::rep>::max();
        for (std::size_t i = 2; i <= n; ++i) {
            if (i > static_cast<std::size_t>(max) || value > max / static_cast<Rational::rep>(i)) {
                throw std::overflow_error("simplex factorial exceeds exact scalar range");
            }
            value *= static_cast<Rational::rep>(i);
        }
        return value;
    }
};

} // namespace cace::math
