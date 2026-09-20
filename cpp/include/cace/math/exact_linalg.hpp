#pragma once

#include "cace/math/sparse_matrix.hpp"

#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cace::math {

struct RrefResult {
    ExactMatrix matrix;
    std::vector<std::size_t> pivot_columns;
};

inline void swap_rows(ExactMatrix& matrix, std::size_t a, std::size_t b) {
    if (a == b) return;
    for (std::size_t c = 0; c < matrix.cols(); ++c) {
        std::swap(matrix.at(a, c), matrix.at(b, c));
    }
}

[[nodiscard]] inline RrefResult rref(const ExactMatrix& input) {
    ExactMatrix out = input;
    std::vector<std::size_t> pivots;
    std::size_t pivot_row = 0;

    for (std::size_t col = 0; col < out.cols() && pivot_row < out.rows(); ++col) {
        std::size_t candidate = pivot_row;
        while (candidate < out.rows() && out.at(candidate, col).is_zero()) ++candidate;
        if (candidate == out.rows()) continue;

        swap_rows(out, candidate, pivot_row);

        const Rational pivot = out.at(pivot_row, col);
        for (std::size_t c = col; c < out.cols(); ++c) out.at(pivot_row, c) /= pivot;

        for (std::size_t r = 0; r < out.rows(); ++r) {
            if (r == pivot_row) continue;
            const Rational factor = out.at(r, col);
            if (factor.is_zero()) continue;
            for (std::size_t c = col; c < out.cols(); ++c) {
                out.at(r, c) -= factor * out.at(pivot_row, c);
            }
        }

        pivots.push_back(col);
        ++pivot_row;
    }

    return {std::move(out), std::move(pivots)};
}

[[nodiscard]] inline std::size_t rank(const ExactMatrix& matrix) {
    return rref(matrix).pivot_columns.size();
}

[[nodiscard]] inline Rational determinant(const ExactMatrix& input) {
    if (input.rows() != input.cols()) throw std::invalid_argument("determinant requires square matrix");
    const std::size_t n = input.rows();
    if (n == 0) return Rational(1);

    ExactMatrix a = input;
    Rational det(1);
    bool negate = false;

    for (std::size_t col = 0; col < n; ++col) {
        std::size_t pivot = col;
        while (pivot < n && a.at(pivot, col).is_zero()) ++pivot;
        if (pivot == n) return Rational();

        if (pivot != col) {
            swap_rows(a, pivot, col);
            negate = !negate;
        }

        const Rational p = a.at(col, col);
        det *= p;

        for (std::size_t r = col + 1; r < n; ++r) {
            if (a.at(r, col).is_zero()) continue;
            const Rational factor = a.at(r, col) / p;
            a.at(r, col) = Rational();
            for (std::size_t c = col + 1; c < n; ++c) {
                a.at(r, c) -= factor * a.at(col, c);
            }
        }
    }

    return negate ? -det : det;
}

[[nodiscard]] inline std::vector<ExactVector> nullspace(const ExactMatrix& matrix) {
    const auto reduced = rref(matrix);
    std::vector<bool> is_pivot(matrix.cols(), false);
    for (const auto c : reduced.pivot_columns) is_pivot[c] = true;

    std::vector<ExactVector> basis;
    for (std::size_t free_col = 0; free_col < matrix.cols(); ++free_col) {
        if (is_pivot[free_col]) continue;

        std::vector<Rational> v(matrix.cols());
        v[free_col] = Rational(1);

        for (std::size_t pivot_row = 0; pivot_row < reduced.pivot_columns.size(); ++pivot_row) {
            const std::size_t pivot_col = reduced.pivot_columns[pivot_row];
            v[pivot_col] = -reduced.matrix.at(pivot_row, free_col);
        }
        basis.emplace_back(std::move(v));
    }
    return basis;
}

[[nodiscard]] inline ExactVector solve_nonsingular(const ExactMatrix& a, const ExactVector& b) {
    if (a.rows() != a.cols()) throw std::invalid_argument("exact solve requires square matrix");
    if (b.size() != a.rows()) throw std::invalid_argument("exact solve right-hand side shape mismatch");

    const std::size_t n = a.rows();
    ExactMatrix augmented(n, n + 1);
    for (std::size_t r = 0; r < n; ++r) {
        for (std::size_t c = 0; c < n; ++c) augmented.at(r, c) = a.at(r, c);
        augmented.at(r, n) = b.at(r);
    }

    const auto reduced = rref(augmented);
    if (reduced.pivot_columns.size() < n) throw std::domain_error("exact solve matrix is singular");
    for (std::size_t i = 0; i < n; ++i) {
        if (reduced.pivot_columns[i] != i) throw std::domain_error("exact solve matrix is singular");
    }

    std::vector<Rational> x(n);
    for (std::size_t r = 0; r < n; ++r) x[r] = reduced.matrix.at(r, n);
    return ExactVector(std::move(x));
}

[[nodiscard]] inline ExactMatrix inverse_nonsingular(const ExactMatrix& a) {
    if (a.rows() != a.cols()) throw std::invalid_argument("inverse requires square matrix");
    const std::size_t n = a.rows();

    ExactMatrix augmented(n, 2 * n);
    for (std::size_t r = 0; r < n; ++r) {
        for (std::size_t c = 0; c < n; ++c) augmented.at(r, c) = a.at(r, c);
        augmented.at(r, n + r) = Rational(1);
    }

    const auto reduced = rref(augmented);
    if (reduced.pivot_columns.size() < n) throw std::domain_error("inverse matrix is singular");
    for (std::size_t i = 0; i < n; ++i) {
        if (reduced.pivot_columns[i] != i) throw std::domain_error("inverse matrix is singular");
    }

    ExactMatrix inverse(n, n);
    for (std::size_t r = 0; r < n; ++r) {
        for (std::size_t c = 0; c < n; ++c) inverse.at(r, c) = reduced.matrix.at(r, n + c);
    }
    return inverse;
}

[[nodiscard]] inline bool verify_solution(
    const ExactMatrix& a,
    const ExactVector& x,
    const ExactVector& b) {
    if (a.cols() != x.size() || a.rows() != b.size()) return false;
    return a.matvec(x) == b;
}

[[nodiscard]] inline bool verify_inverse(const ExactMatrix& a, const ExactMatrix& candidate) {
    if (a.rows() != a.cols() || candidate.rows() != candidate.cols() ||
        a.rows() != candidate.rows()) return false;
    const auto id = ExactMatrix::identity(a.rows());
    return a.matmul(candidate) == id && candidate.matmul(a) == id;
}

[[nodiscard]] inline ExactMatrix leading_principal(const ExactMatrix& a, std::size_t k) {
    if (a.rows() != a.cols() || k == 0 || k > a.rows()) {
        throw std::invalid_argument("invalid leading principal minor size");
    }
    ExactMatrix out(k, k);
    for (std::size_t r = 0; r < k; ++r) {
        for (std::size_t c = 0; c < k; ++c) out.at(r, c) = a.at(r, c);
    }
    return out;
}

[[nodiscard]] inline bool is_symmetric(const ExactMatrix& a) {
    if (a.rows() != a.cols()) return false;
    for (std::size_t r = 0; r < a.rows(); ++r) {
        for (std::size_t c = r + 1; c < a.cols(); ++c) {
            if (!(a.at(r, c) == a.at(c, r))) return false;
        }
    }
    return true;
}

[[nodiscard]] inline bool is_positive_definite(const ExactMatrix& a) {
    if (!is_symmetric(a)) return false;
    for (std::size_t k = 1; k <= a.rows(); ++k) {
        if (!(determinant(leading_principal(a, k)) > Rational())) return false;
    }
    return true;
}

[[nodiscard]] inline bool is_negative_definite(const ExactMatrix& a) {
    if (!is_symmetric(a)) return false;
    for (std::size_t k = 1; k <= a.rows(); ++k) {
        Rational d = determinant(leading_principal(a, k));
        if ((k % 2 == 1 && !(d < Rational())) || (k % 2 == 0 && !(d > Rational()))) return false;
    }
    return true;
}

} // namespace cace::math
