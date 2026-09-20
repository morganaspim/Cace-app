#pragma once

#include "cace/math/exterior.hpp"
#include "cace/math/geometry.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

[[nodiscard]] inline std::uint64_t binomial_checked(std::size_t n, std::size_t k) {
    if (k > n) return 0U;
    k = std::min(k, n - k);
    __uint128_t value = 1U;
    for (std::size_t i = 1; i <= k; ++i) {
        value = (value * static_cast<__uint128_t>(n - k + i)) / static_cast<__uint128_t>(i);
        if (value > std::numeric_limits<std::uint64_t>::max()) {
            throw std::overflow_error("binomial coefficient exceeds uint64 range");
        }
    }
    return static_cast<std::uint64_t>(value);
}

[[nodiscard]] inline std::vector<std::vector<std::size_t>> combinations(
    std::size_t n,
    std::size_t k,
    std::size_t max_results = 100000U) {
    const auto count = binomial_checked(n, k);
    if (count > max_results) throw std::length_error("combination enumeration exceeds configured bound");
    std::vector<std::vector<std::size_t>> out;
    if (k > n) return out;
    if (k == 0U) {
        out.push_back({});
        return out;
    }
    std::vector<std::size_t> current(k);
    for (std::size_t i = 0; i < k; ++i) current[i] = i;
    while (true) {
        out.push_back(current);
        std::size_t i = k;
        while (i > 0U) {
            --i;
            if (current[i] != i + n - k) break;
        }
        if (current[0] == n - k && i == 0U) break;
        ++current[i];
        for (std::size_t j = i + 1; j < k; ++j) current[j] = current[j - 1] + 1U;
    }
    return out;
}

class ExactPermutation {
public:
    ExactPermutation() = default;
    explicit ExactPermutation(std::vector<std::size_t> image) : image_(std::move(image)) {
        validate();
    }

    [[nodiscard]] static ExactPermutation identity(std::size_t degree) {
        std::vector<std::size_t> image(degree);
        for (std::size_t i = 0; i < degree; ++i) image[i] = i;
        return ExactPermutation(std::move(image));
    }

    [[nodiscard]] std::size_t degree() const noexcept { return image_.size(); }
    [[nodiscard]] const std::vector<std::size_t>& image() const noexcept { return image_; }

    [[nodiscard]] std::size_t apply_index(std::size_t index) const {
        if (index >= degree()) throw std::out_of_range("permutation index out of range");
        return image_[index];
    }

    [[nodiscard]] ExactPermutation compose(const ExactPermutation& inner) const {
        require_same_degree(inner);
        std::vector<std::size_t> out(degree());
        for (std::size_t i = 0; i < degree(); ++i) out[i] = image_[inner.image_[i]];
        return ExactPermutation(std::move(out));
    }

    [[nodiscard]] ExactPermutation inverse() const {
        std::vector<std::size_t> out(degree());
        for (std::size_t i = 0; i < degree(); ++i) out[image_[i]] = i;
        return ExactPermutation(std::move(out));
    }

    [[nodiscard]] int parity() const noexcept {
        std::size_t inversions = 0U;
        for (std::size_t i = 0; i < degree(); ++i) {
            for (std::size_t j = i + 1; j < degree(); ++j) {
                if (image_[i] > image_[j]) ++inversions;
            }
        }
        return (inversions % 2U == 0U) ? 1 : -1;
    }

    [[nodiscard]] ExactVector act_coordinates(const ExactVector& vector) const {
        if (vector.size() != degree()) throw std::invalid_argument("permutation/vector dimension mismatch");
        std::vector<Rational> out(degree());
        for (std::size_t i = 0; i < degree(); ++i) out[image_[i]] = vector.at(i);
        return ExactVector(std::move(out));
    }

    [[nodiscard]] ExactMatrix permutation_matrix() const {
        ExactMatrix out(degree(), degree());
        for (std::size_t i = 0; i < degree(); ++i) out.at(image_[i], i) = Rational(1);
        return out;
    }

    [[nodiscard]] ExactMatrix conjugate_square_matrix(const ExactMatrix& matrix) const {
        if (matrix.rows() != degree() || matrix.cols() != degree()) {
            throw std::invalid_argument("permutation/matrix dimension mismatch");
        }
        const ExactMatrix p = permutation_matrix();
        const ExactMatrix pinv = inverse().permutation_matrix();
        return p.matmul(matrix).matmul(pinv);
    }

    [[nodiscard]] ExactAffineMap act_affine_coordinates(const ExactAffineMap& affine) const {
        if (affine.input_dimension() != degree() || affine.output_dimension() != degree()) {
            throw std::invalid_argument("permutation/affine dimension mismatch");
        }
        return ExactAffineMap(
            conjugate_square_matrix(affine.linear()),
            act_coordinates(affine.translation()));
    }

    [[nodiscard]] ExactExterior act_exterior(const ExactExterior& value) const {
        if (value.dimension() != degree()) throw std::invalid_argument("permutation/exterior dimension mismatch");
        std::map<ExactExterior::Mask, Rational> terms;
        for (const auto& [mask, coefficient] : value.terms()) {
            std::vector<std::size_t> images;
            ExactExterior::Mask new_mask = 0U;
            for (std::size_t i = 0; i < degree(); ++i) {
                if ((mask & (ExactExterior::Mask(1) << i)) == 0U) continue;
                images.push_back(image_[i]);
                new_mask |= ExactExterior::Mask(1) << image_[i];
            }
            std::size_t inversions = 0U;
            for (std::size_t i = 0; i < images.size(); ++i) {
                for (std::size_t j = i + 1; j < images.size(); ++j) {
                    if (images[i] > images[j]) ++inversions;
                }
            }
            const Rational signed_coefficient = (inversions % 2U == 0U) ? coefficient : -coefficient;
            auto [it, inserted] = terms.emplace(new_mask, signed_coefficient);
            if (!inserted) {
                it->second += signed_coefficient;
                if (it->second.is_zero()) terms.erase(it);
            }
        }
        return ExactExterior(degree(), std::move(terms));
    }

    [[nodiscard]] ExactSimplex act_simplex_vertices(const ExactSimplex& simplex) const {
        if (degree() != simplex.vertices().size()) {
            throw std::invalid_argument("permutation/simplex vertex-count mismatch");
        }
        std::vector<ExactVector> vertices(degree());
        for (std::size_t i = 0; i < degree(); ++i) vertices[image_[i]] = simplex.vertices()[i];
        return ExactSimplex(std::move(vertices));
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "perm:[";
        for (std::size_t i = 0; i < image_.size(); ++i) {
            if (i != 0) out.push_back(',');
            out += std::to_string(image_[i]);
        }
        out.push_back(']');
        return out;
    }

    friend bool operator==(const ExactPermutation&, const ExactPermutation&) = default;
    friend bool operator<(const ExactPermutation& lhs, const ExactPermutation& rhs) noexcept {
        return lhs.image_ < rhs.image_;
    }

private:
    std::vector<std::size_t> image_;

    void validate() const {
        std::vector<bool> seen(image_.size(), false);
        for (const auto value : image_) {
            if (value >= image_.size() || seen[value]) {
                throw std::invalid_argument("permutation image must be a bijection");
            }
            seen[value] = true;
        }
    }

    void require_same_degree(const ExactPermutation& rhs) const {
        if (degree() != rhs.degree()) throw std::invalid_argument("permutation degree mismatch");
    }
};

class FinitePermutationGroup {
public:
    FinitePermutationGroup(
        std::size_t degree,
        std::vector<ExactPermutation> generators,
        std::size_t max_elements = 4096U)
        : degree_(degree), generators_(std::move(generators)), max_elements_(max_elements) {
        if (max_elements_ == 0U) throw std::invalid_argument("group max_elements must be positive");
        for (const auto& generator : generators_) {
            if (generator.degree() != degree_) throw std::invalid_argument("group generator degree mismatch");
        }
        enumerate_closure();
    }

    [[nodiscard]] std::size_t degree() const noexcept { return degree_; }
    [[nodiscard]] std::size_t size() const noexcept { return elements_.size(); }
    [[nodiscard]] const std::vector<ExactPermutation>& generators() const noexcept { return generators_; }
    [[nodiscard]] const std::vector<ExactPermutation>& elements() const noexcept { return elements_; }

    [[nodiscard]] std::vector<std::size_t> orbit(std::size_t point) const {
        if (point >= degree_) throw std::out_of_range("group orbit point out of range");
        std::set<std::size_t> values;
        for (const auto& element : elements_) values.insert(element.apply_index(point));
        return std::vector<std::size_t>(values.begin(), values.end());
    }

    [[nodiscard]] std::vector<ExactPermutation> stabilizer(std::size_t point) const {
        if (point >= degree_) throw std::out_of_range("group stabilizer point out of range");
        std::vector<ExactPermutation> out;
        for (const auto& element : elements_) {
            if (element.apply_index(point) == point) out.push_back(element);
        }
        return out;
    }

    [[nodiscard]] ExactVector canonical_coordinate_representative(const ExactVector& value) const {
        if (value.size() != degree_) throw std::invalid_argument("group/vector dimension mismatch");
        ExactVector best = value;
        std::string best_text = best.canonical_text();
        for (const auto& element : elements_) {
            const ExactVector candidate = element.act_coordinates(value);
            const std::string text = candidate.canonical_text();
            if (text < best_text) {
                best = candidate;
                best_text = text;
            }
        }
        return best;
    }

    [[nodiscard]] ExactExterior canonical_exterior_representative(const ExactExterior& value) const {
        if (value.dimension() != degree_) throw std::invalid_argument("group/exterior dimension mismatch");
        ExactExterior best = value;
        std::string best_text = best.canonical_text();
        for (const auto& element : elements_) {
            const ExactExterior candidate = element.act_exterior(value);
            const std::string text = candidate.canonical_text();
            if (text < best_text) {
                best = candidate;
                best_text = text;
            }
        }
        return best;
    }

    [[nodiscard]] std::vector<ExactPermutation> cayley_neighbors(const ExactPermutation& element) const {
        if (element.degree() != degree_) throw std::invalid_argument("Cayley element degree mismatch");
        std::vector<ExactPermutation> out;
        out.reserve(generators_.size());
        for (const auto& generator : generators_) out.push_back(generator.compose(element));
        return out;
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "perm_group:degree=" + std::to_string(degree_) + ":[";
        for (std::size_t i = 0; i < elements_.size(); ++i) {
            if (i != 0) out.push_back(';');
            out += elements_[i].canonical_text();
        }
        out.push_back(']');
        return out;
    }

private:
    std::size_t degree_ = 0;
    std::vector<ExactPermutation> generators_;
    std::size_t max_elements_ = 0;
    std::vector<ExactPermutation> elements_;

    void enumerate_closure() {
        std::vector<ExactPermutation> moves = generators_;
        for (const auto& generator : generators_) moves.push_back(generator.inverse());

        std::set<ExactPermutation> seen;
        std::vector<ExactPermutation> queue;
        const auto identity = ExactPermutation::identity(degree_);
        seen.insert(identity);
        queue.push_back(identity);

        for (std::size_t cursor = 0; cursor < queue.size(); ++cursor) {
            const ExactPermutation current = queue[cursor];
            for (const auto& move : moves) {
                ExactPermutation next = move.compose(current);
                if (seen.insert(next).second) {
                    if (seen.size() > max_elements_) {
                        throw std::length_error("finite permutation group exceeds configured closure bound");
                    }
                    queue.push_back(std::move(next));
                }
            }
        }
        elements_.assign(seen.begin(), seen.end());
    }
};

} // namespace cace::math
