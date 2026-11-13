#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <iterator>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace expert_robot::math::continuum {

// The first laboratory fixes two real-valued channels per point.  It does not
// silently identify an arbitrary pair with a complex number.
struct StatePair {
    double first{0.0};
    double second{0.0};
};

inline bool finite(const StatePair& value) noexcept {
    return std::isfinite(value.first) && std::isfinite(value.second);
}

inline bool near(const StatePair& lhs, const StatePair& rhs,
                 double tolerance = 1e-9) noexcept {
    return std::abs(lhs.first - rhs.first) <= tolerance &&
           std::abs(lhs.second - rhs.second) <= tolerance;
}

inline StatePair interpolate(const StatePair& lhs, const StatePair& rhs,
                             double t) noexcept {
    return {lhs.first + (rhs.first - lhs.first) * t,
            lhs.second + (rhs.second - lhs.second) * t};
}

struct EdgeSample {
    double parameter{0.0};
    StatePair state{};
};

class EdgeField {
public:
    explicit EdgeField(std::vector<EdgeSample> samples)
        : samples_(std::move(samples)) {
        validate();
    }

    [[nodiscard]] const std::vector<EdgeSample>& samples() const noexcept {
        return samples_;
    }

    [[nodiscard]] const StatePair& start() const noexcept {
        return samples_.front().state;
    }

    [[nodiscard]] const StatePair& end() const noexcept {
        return samples_.back().state;
    }

    [[nodiscard]] StatePair evaluate(double t) const {
        if (!std::isfinite(t) || t < 0.0 || t > 1.0) {
            throw std::out_of_range("edge parameter must be finite and in [0, 1]");
        }
        const auto upper = std::lower_bound(
            samples_.begin(), samples_.end(), t,
            [](const EdgeSample& sample, double value) {
                return sample.parameter < value;
            });
        if (upper == samples_.begin()) return upper->state;
        if (upper == samples_.end()) return samples_.back().state;
        if (upper->parameter == t) return upper->state;
        const auto lower = std::prev(upper);
        const double width = upper->parameter - lower->parameter;
        const double local_t = (t - lower->parameter) / width;
        return interpolate(lower->state, upper->state, local_t);
    }

    [[nodiscard]] bool is_affine_trace(double tolerance = 1e-9) const noexcept {
        const StatePair& first = start();
        const StatePair& last = end();
        return std::all_of(samples_.begin(), samples_.end(),
            [&](const EdgeSample& sample) {
                return near(sample.state,
                            interpolate(first, last, sample.parameter), tolerance);
            });
    }

private:
    void validate() const {
        if (samples_.size() < 2) {
            throw std::invalid_argument("an edge field requires at least two samples");
        }
        if (std::abs(samples_.front().parameter) > 1e-12 ||
            std::abs(samples_.back().parameter - 1.0) > 1e-12) {
            throw std::invalid_argument("edge samples must include parameters 0 and 1");
        }
        double previous = -1.0;
        for (const auto& sample : samples_) {
            if (!std::isfinite(sample.parameter) ||
                sample.parameter < 0.0 || sample.parameter > 1.0 ||
                sample.parameter <= previous || !finite(sample.state)) {
                throw std::invalid_argument(
                    "edge samples must be finite, strictly ordered, and lie in [0, 1]");
            }
            previous = sample.parameter;
        }
    }

    std::vector<EdgeSample> samples_;
};

enum class TriangleEdge { AB, BC, CA };
enum class ExtensionClass {
    VertexIncompatible,
    AffineExtension,
    RequiresHigherOrderOrDifferentExtension
};

struct VertexCompatibility {
    bool compatible{false};
    bool at_a{false};
    bool at_b{false};
    bool at_c{false};
};

class TriangleBoundary {
public:
    TriangleBoundary(EdgeField ab, EdgeField bc, EdgeField ca)
        : ab_(std::move(ab)), bc_(std::move(bc)), ca_(std::move(ca)) {}

    [[nodiscard]] const EdgeField& edge(TriangleEdge id) const noexcept {
        switch (id) {
            case TriangleEdge::AB: return ab_;
            case TriangleEdge::BC: return bc_;
            case TriangleEdge::CA: return ca_;
        }
        return ab_;
    }

    // Orientation convention: AB is A->B, BC is B->C, CA is C->A.
    [[nodiscard]] VertexCompatibility vertex_compatibility(
        double tolerance = 1e-9) const noexcept {
        VertexCompatibility result;
        result.at_a = near(ca_.end(), ab_.start(), tolerance);
        result.at_b = near(ab_.end(), bc_.start(), tolerance);
        result.at_c = near(bc_.end(), ca_.start(), tolerance);
        result.compatible = result.at_a && result.at_b && result.at_c;
        return result;
    }

    // This classifies only the affine barycentric extension. A non-affine
    // trace is not proof that no continuous or higher-order extension exists.
    [[nodiscard]] ExtensionClass classify_affine_extension(
        double tolerance = 1e-9) const noexcept {
        if (!vertex_compatibility(tolerance).compatible) {
            return ExtensionClass::VertexIncompatible;
        }
        if (ab_.is_affine_trace(tolerance) &&
            bc_.is_affine_trace(tolerance) &&
            ca_.is_affine_trace(tolerance)) {
            return ExtensionClass::AffineExtension;
        }
        return ExtensionClass::RequiresHigherOrderOrDifferentExtension;
    }

    // Barycentric coordinates are ordered (A,B,C), nonnegative, and sum to 1.
    // This is valid as the boundary-matching extension only when the classifier
    // returns AffineExtension.
    [[nodiscard]] StatePair evaluate_affine(
        const std::array<double, 3>& barycentric) const {
        constexpr double sum_tolerance = 1e-9;
        for (double value : barycentric) {
            if (!std::isfinite(value) || value < -sum_tolerance) {
                throw std::out_of_range("barycentric coordinates must be finite and nonnegative");
            }
        }
        const double sum = barycentric[0] + barycentric[1] + barycentric[2];
        if (std::abs(sum - 1.0) > sum_tolerance) {
            throw std::invalid_argument("barycentric coordinates must sum to one");
        }
        if (classify_affine_extension() != ExtensionClass::AffineExtension) {
            throw std::logic_error("boundary is not compatible with an affine extension");
        }
        const StatePair a = ab_.start();
        const StatePair b = ab_.end();
        const StatePair c = bc_.end();
        return {
            barycentric[0] * a.first + barycentric[1] * b.first +
                barycentric[2] * c.first,
            barycentric[0] * a.second + barycentric[1] * b.second +
                barycentric[2] * c.second
        };
    }

private:
    EdgeField ab_;
    EdgeField bc_;
    EdgeField ca_;
};

struct Matrix2 {
    double m00{1.0};
    double m01{0.0};
    double m10{0.0};
    double m11{1.0};

    [[nodiscard]] StatePair apply(const StatePair& value) const noexcept {
        return {m00 * value.first + m01 * value.second,
                m10 * value.first + m11 * value.second};
    }

    [[nodiscard]] double determinant() const noexcept {
        return m00 * m11 - m01 * m10;
    }

    [[nodiscard]] bool invertible(double tolerance = 1e-12) const noexcept {
        return std::isfinite(determinant()) &&
               std::abs(determinant()) > tolerance;
    }

    [[nodiscard]] Matrix2 then(const Matrix2& next) const noexcept {
        // Apply *this first*, then next: result = next * this.
        return {
            next.m00 * m00 + next.m01 * m10,
            next.m00 * m01 + next.m01 * m11,
            next.m10 * m00 + next.m11 * m10,
            next.m10 * m01 + next.m11 * m11
        };
    }

    [[nodiscard]] static Matrix2 identity() noexcept { return {}; }
};


// Dimension-aware linear algebra for heterogeneous state carriers. Matrix2
// remains the compact two-channel convenience type above; this generic form
// is the canonical path for maps R^m -> R^n.
class DenseMatrix {
public:
    explicit DenseMatrix(std::vector<std::vector<double>> rows)
        : rows_(std::move(rows)) {
        if (rows_.empty() || rows_.front().empty()) {
            throw std::invalid_argument("a linear map matrix must be non-empty");
        }
        const std::size_t width = rows_.front().size();
        for (const auto& row : rows_) {
            if (row.size() != width ||
                !std::all_of(row.begin(), row.end(),
                             [](double value) { return std::isfinite(value); })) {
                throw std::invalid_argument(
                    "matrix rows must have equal width and finite entries");
            }
        }
    }

    [[nodiscard]] std::size_t row_count() const noexcept { return rows_.size(); }
    [[nodiscard]] std::size_t column_count() const noexcept {
        return rows_.front().size();
    }
    [[nodiscard]] const std::vector<std::vector<double>>& rows() const noexcept {
        return rows_;
    }

    [[nodiscard]] std::vector<double> apply(
        const std::vector<double>& value) const {
        if (value.size() != column_count()) {
            throw std::invalid_argument("matrix input dimension does not match source carrier");
        }
        std::vector<double> result(row_count(), 0.0);
        for (std::size_t i = 0; i < row_count(); ++i) {
            for (std::size_t j = 0; j < column_count(); ++j) {
                result[i] += rows_[i][j] * value[j];
            }
        }
        return result;
    }

    [[nodiscard]] DenseMatrix then(const DenseMatrix& next) const {
        if (row_count() != next.column_count()) {
            throw std::invalid_argument("matrix composition dimensions do not match");
        }
        std::vector<std::vector<double>> product(
            next.row_count(), std::vector<double>(column_count(), 0.0));
        // Apply this matrix first, then next: product = next * this.
        for (std::size_t i = 0; i < next.row_count(); ++i) {
            for (std::size_t k = 0; k < row_count(); ++k) {
                for (std::size_t j = 0; j < column_count(); ++j) {
                    product[i][j] += next.rows_[i][k] * rows_[k][j];
                }
            }
        }
        return DenseMatrix(std::move(product));
    }

private:
    std::vector<std::vector<double>> rows_;
};

class LinearStateMap {
public:
    LinearStateMap(std::string id, std::string source_state_space_id,
                   std::string target_state_space_id, DenseMatrix matrix)
        : id_(std::move(id)),
          source_(std::move(source_state_space_id)),
          target_(std::move(target_state_space_id)),
          matrix_(std::move(matrix)) {
        if (id_.empty() || source_.empty() || target_.empty()) {
            throw std::invalid_argument("linear map identity and carrier IDs must be non-empty");
        }
    }

    [[nodiscard]] const std::string& id() const noexcept { return id_; }
    [[nodiscard]] const std::string& source() const noexcept { return source_; }
    [[nodiscard]] const std::string& target() const noexcept { return target_; }
    [[nodiscard]] const DenseMatrix& matrix() const noexcept { return matrix_; }

    [[nodiscard]] std::vector<double> apply(
        const std::vector<double>& value) const {
        return matrix_.apply(value);
    }

    [[nodiscard]] LinearStateMap then(const LinearStateMap& next) const {
        if (target_ != next.source_) {
            throw std::invalid_argument(
                "linear map composition requires matching intermediate state-space IDs");
        }
        return LinearStateMap(
            id_ + ";" + next.id_, source_, next.target_,
            matrix_.then(next.matrix_));
    }

private:
    std::string id_;
    std::string source_;
    std::string target_;
    DenseMatrix matrix_;
};

struct NAlitySignature {
    std::size_t geometric_dimension{2};
    std::size_t state_dimension{2};
    std::size_t logical_channels{2};
    std::size_t temporal_parameters{1};
};

} // namespace expert_robot::math::continuum
