#pragma once

#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"

#include <algorithm>
#include <cstddef>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace cace::math {

class ExactMatrix {
public:
    ExactMatrix() = default;

    ExactMatrix(std::size_t rows, std::size_t cols)
        : rows_(rows), cols_(cols), data_(rows * cols) {}

    ExactMatrix(std::size_t rows, std::size_t cols, std::vector<Rational> data)
        : rows_(rows), cols_(cols), data_(std::move(data)) {
        if (data_.size() != rows_ * cols_) {
            throw std::invalid_argument("exact matrix data size mismatch");
        }
    }

    [[nodiscard]] std::size_t rows() const noexcept { return rows_; }
    [[nodiscard]] std::size_t cols() const noexcept { return cols_; }
    [[nodiscard]] bool empty() const noexcept { return rows_ == 0 || cols_ == 0; }

    [[nodiscard]] const Rational& at(std::size_t row, std::size_t col) const {
        check_index(row, col);
        return data_[row * cols_ + col];
    }

    [[nodiscard]] Rational& at(std::size_t row, std::size_t col) {
        check_index(row, col);
        return data_[row * cols_ + col];
    }

    [[nodiscard]] const std::vector<Rational>& data() const noexcept { return data_; }

    [[nodiscard]] static ExactMatrix identity(std::size_t n) {
        ExactMatrix out(n, n);
        for (std::size_t i = 0; i < n; ++i) out.at(i, i) = Rational(1);
        return out;
    }

    [[nodiscard]] ExactMatrix transpose() const {
        ExactMatrix out(cols_, rows_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t c = 0; c < cols_; ++c) out.at(c, r) = at(r, c);
        }
        return out;
    }

    [[nodiscard]] ExactVector matvec(const ExactVector& x) const {
        if (x.size() != cols_) throw std::invalid_argument("exact matrix/vector shape mismatch");
        std::vector<Rational> out(rows_);
        for (std::size_t r = 0; r < rows_; ++r) {
            Rational sum;
            for (std::size_t c = 0; c < cols_; ++c) sum += at(r, c) * x.at(c);
            out[r] = sum;
        }
        return ExactVector(std::move(out));
    }

    [[nodiscard]] ExactMatrix matmul(const ExactMatrix& rhs) const {
        if (cols_ != rhs.rows_) throw std::invalid_argument("exact matrix multiply shape mismatch");
        ExactMatrix out(rows_, rhs.cols_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t k = 0; k < cols_; ++k) {
                const Rational a = at(r, k);
                if (a.is_zero()) continue;
                for (std::size_t c = 0; c < rhs.cols_; ++c) {
                    const Rational b = rhs.at(k, c);
                    if (!b.is_zero()) out.at(r, c) += a * b;
                }
            }
        }
        return out;
    }

    [[nodiscard]] ExactMatrix row_permuted(const std::vector<std::size_t>& permutation) const {
        validate_permutation(permutation, rows_, "row");
        ExactMatrix out(rows_, cols_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t c = 0; c < cols_; ++c) out.at(r, c) = at(permutation[r], c);
        }
        return out;
    }

    [[nodiscard]] ExactMatrix col_permuted(const std::vector<std::size_t>& permutation) const {
        validate_permutation(permutation, cols_, "column");
        ExactMatrix out(rows_, cols_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t c = 0; c < cols_; ++c) out.at(r, c) = at(r, permutation[c]);
        }
        return out;
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = std::to_string(rows_) + "x" + std::to_string(cols_) + ":[";
        for (std::size_t r = 0; r < rows_; ++r) {
            if (r != 0) out.push_back(';');
            for (std::size_t c = 0; c < cols_; ++c) {
                if (c != 0) out.push_back(',');
                out += at(r, c).canonical_text();
            }
        }
        out.push_back(']');
        return out;
    }

    friend bool operator==(const ExactMatrix&, const ExactMatrix&) = default;

private:
    std::size_t rows_ = 0;
    std::size_t cols_ = 0;
    std::vector<Rational> data_;

    void check_index(std::size_t row, std::size_t col) const {
        if (row >= rows_ || col >= cols_) throw std::out_of_range("exact matrix index out of range");
    }

    static void validate_permutation(
        const std::vector<std::size_t>& permutation,
        std::size_t expected,
        const char* label) {
        if (permutation.size() != expected) {
            throw std::invalid_argument(std::string(label) + " permutation size mismatch");
        }
        std::vector<bool> seen(expected, false);
        for (const auto i : permutation) {
            if (i >= expected || seen[i]) {
                throw std::invalid_argument(std::string(label) + " permutation is not bijective");
            }
            seen[i] = true;
        }
    }
};

class ExactSparseMatrix {
public:
    struct Entry {
        std::size_t row = 0;
        std::size_t col = 0;
        Rational value;

        friend bool operator==(const Entry&, const Entry&) = default;
    };

    ExactSparseMatrix() = default;

    ExactSparseMatrix(std::size_t rows, std::size_t cols, std::vector<Entry> entries)
        : rows_(rows), cols_(cols) {
        canonicalize(std::move(entries));
    }

    [[nodiscard]] static ExactSparseMatrix from_triplets(
        std::size_t rows,
        std::size_t cols,
        const std::vector<std::tuple<std::size_t, std::size_t, Rational>>& triplets) {
        std::vector<Entry> entries;
        entries.reserve(triplets.size());
        for (const auto& [r, c, value] : triplets) entries.push_back({r, c, value});
        return ExactSparseMatrix(rows, cols, std::move(entries));
    }

    [[nodiscard]] static ExactSparseMatrix from_dense(const ExactMatrix& dense) {
        std::vector<Entry> entries;
        for (std::size_t r = 0; r < dense.rows(); ++r) {
            for (std::size_t c = 0; c < dense.cols(); ++c) {
                if (!dense.at(r, c).is_zero()) entries.push_back({r, c, dense.at(r, c)});
            }
        }
        return ExactSparseMatrix(dense.rows(), dense.cols(), std::move(entries));
    }

    [[nodiscard]] std::size_t rows() const noexcept { return rows_; }
    [[nodiscard]] std::size_t cols() const noexcept { return cols_; }
    [[nodiscard]] std::size_t nnz() const noexcept { return values_.size(); }
    [[nodiscard]] const std::vector<std::size_t>& row_ptr() const noexcept { return row_ptr_; }
    [[nodiscard]] const std::vector<std::size_t>& col_idx() const noexcept { return col_idx_; }
    [[nodiscard]] const std::vector<Rational>& values() const noexcept { return values_; }

    [[nodiscard]] Rational at(std::size_t row, std::size_t col) const {
        if (row >= rows_ || col >= cols_) throw std::out_of_range("sparse matrix index out of range");
        const auto begin = row_ptr_[row];
        const auto end = row_ptr_[row + 1];
        const auto it = std::lower_bound(col_idx_.begin() + static_cast<std::ptrdiff_t>(begin),
                                         col_idx_.begin() + static_cast<std::ptrdiff_t>(end),
                                         col);
        if (it == col_idx_.begin() + static_cast<std::ptrdiff_t>(end) || *it != col) return Rational();
        return values_[static_cast<std::size_t>(std::distance(col_idx_.begin(), it))];
    }

    [[nodiscard]] ExactMatrix to_dense() const {
        ExactMatrix out(rows_, cols_);
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t k = row_ptr_[r]; k < row_ptr_[r + 1]; ++k) {
                out.at(r, col_idx_[k]) = values_[k];
            }
        }
        return out;
    }

    [[nodiscard]] ExactVector matvec(const ExactVector& x) const {
        if (x.size() != cols_) throw std::invalid_argument("sparse matrix/vector shape mismatch");
        std::vector<Rational> out(rows_);
        for (std::size_t r = 0; r < rows_; ++r) {
            Rational sum;
            for (std::size_t k = row_ptr_[r]; k < row_ptr_[r + 1]; ++k) {
                sum += values_[k] * x.at(col_idx_[k]);
            }
            out[r] = sum;
        }
        return ExactVector(std::move(out));
    }

    [[nodiscard]] ExactSparseMatrix transpose() const {
        std::vector<Entry> entries;
        entries.reserve(nnz());
        for (std::size_t r = 0; r < rows_; ++r) {
            for (std::size_t k = row_ptr_[r]; k < row_ptr_[r + 1]; ++k) {
                entries.push_back({col_idx_[k], r, values_[k]});
            }
        }
        return ExactSparseMatrix(cols_, rows_, std::move(entries));
    }

    [[nodiscard]] ExactSparseMatrix matmul(const ExactSparseMatrix& rhs) const {
        if (cols_ != rhs.rows_) throw std::invalid_argument("sparse matrix multiply shape mismatch");
        std::vector<Entry> entries;
        for (std::size_t r = 0; r < rows_; ++r) {
            std::map<std::size_t, Rational> accum;
            for (std::size_t ka = row_ptr_[r]; ka < row_ptr_[r + 1]; ++ka) {
                const std::size_t inner = col_idx_[ka];
                const Rational a = values_[ka];
                for (std::size_t kb = rhs.row_ptr_[inner]; kb < rhs.row_ptr_[inner + 1]; ++kb) {
                    accum[rhs.col_idx_[kb]] += a * rhs.values_[kb];
                }
            }
            for (const auto& [c, value] : accum) {
                if (!value.is_zero()) entries.push_back({r, c, value});
            }
        }
        return ExactSparseMatrix(rows_, rhs.cols_, std::move(entries));
    }

    [[nodiscard]] ExactSparseMatrix row_permuted(const std::vector<std::size_t>& permutation) const {
        return from_dense(to_dense().row_permuted(permutation));
    }

    [[nodiscard]] ExactSparseMatrix col_permuted(const std::vector<std::size_t>& permutation) const {
        return from_dense(to_dense().col_permuted(permutation));
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = std::to_string(rows_) + "x" + std::to_string(cols_) + ":csr:[";
        for (std::size_t i = 0; i < row_ptr_.size(); ++i) {
            if (i != 0) out.push_back(',');
            out += std::to_string(row_ptr_[i]);
        }
        out += "]:[";
        for (std::size_t i = 0; i < col_idx_.size(); ++i) {
            if (i != 0) out.push_back(',');
            out += std::to_string(col_idx_[i]);
        }
        out += "]:[";
        for (std::size_t i = 0; i < values_.size(); ++i) {
            if (i != 0) out.push_back(',');
            out += values_[i].canonical_text();
        }
        out.push_back(']');
        return out;
    }

    friend bool operator==(const ExactSparseMatrix&, const ExactSparseMatrix&) = default;

private:
    std::size_t rows_ = 0;
    std::size_t cols_ = 0;
    std::vector<std::size_t> row_ptr_{0};
    std::vector<std::size_t> col_idx_;
    std::vector<Rational> values_;

    void canonicalize(std::vector<Entry> entries) {
        for (const auto& entry : entries) {
            if (entry.row >= rows_ || entry.col >= cols_) {
                throw std::invalid_argument("sparse entry index out of range");
            }
        }

        std::sort(entries.begin(), entries.end(), [](const Entry& a, const Entry& b) {
            return std::tie(a.row, a.col) < std::tie(b.row, b.col);
        });

        std::vector<Entry> merged;
        for (const auto& entry : entries) {
            if (!merged.empty() && merged.back().row == entry.row && merged.back().col == entry.col) {
                merged.back().value += entry.value;
            } else {
                merged.push_back(entry);
            }
        }
        merged.erase(std::remove_if(merged.begin(), merged.end(), [](const Entry& e) {
            return e.value.is_zero();
        }), merged.end());

        row_ptr_.assign(rows_ + 1, 0);
        col_idx_.clear();
        values_.clear();
        col_idx_.reserve(merged.size());
        values_.reserve(merged.size());

        std::size_t cursor = 0;
        for (std::size_t r = 0; r < rows_; ++r) {
            while (cursor < merged.size() && merged[cursor].row == r) {
                col_idx_.push_back(merged[cursor].col);
                values_.push_back(merged[cursor].value);
                ++cursor;
            }
            row_ptr_[r + 1] = values_.size();
        }
    }
};

} // namespace cace::math
