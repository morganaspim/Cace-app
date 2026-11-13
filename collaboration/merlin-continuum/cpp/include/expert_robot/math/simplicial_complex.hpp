#pragma once

#include "expert_robot/sha256.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <map>
#include <limits>
#include <iterator>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace expert_robot::math::continuum {

using SimplexKey = std::vector<std::string>;
using IntegerChain = std::map<SimplexKey, int>;

struct OrientedSimplex {
    // Vertex order carries orientation. Reordering vertices can change sign.
    SimplexKey vertices;
};

inline void validate_simplex(const OrientedSimplex& simplex) {
    if (simplex.vertices.size() < 2) {
        throw std::invalid_argument("a boundary operator requires a simplex of dimension >= 1");
    }
    SimplexKey sorted = simplex.vertices;
    for (const auto& vertex : sorted) {
        if (vertex.empty()) {
            throw std::invalid_argument("simplex vertex identifiers must be non-empty");
        }
    }
    std::sort(sorted.begin(), sorted.end());
    if (std::adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) {
        throw std::invalid_argument("simplex vertex identifiers must be unique");
    }
}

// Return the lexicographically ordered key and the sign of the permutation
// from the supplied orientation to that canonical orientation.
inline std::pair<SimplexKey, int> canonical_orientation(SimplexKey vertices) {
    SimplexKey sorted = vertices;
    std::sort(sorted.begin(), sorted.end());
    int inversions = 0;
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        for (std::size_t j = i + 1; j < vertices.size(); ++j) {
            if (vertices[i] > vertices[j]) ++inversions;
        }
    }
    return {std::move(sorted), (inversions % 2 == 0) ? 1 : -1};
}

inline void add_chain_coefficient(IntegerChain& chain,
                                  const SimplexKey& key,
                                  int coefficient) {
    if (coefficient == 0) return;
    int& total = chain[key];
    total += coefficient;
    if (total == 0) chain.erase(key);
}

// Alternating face sum: d[v0,...,vn] = sum_i (-1)^i
// [v0,...,v(i-1),v(i+1),...,vn].
inline IntegerChain boundary(const OrientedSimplex& simplex) {
    validate_simplex(simplex);
    IntegerChain result;
    for (std::size_t omitted = 0; omitted < simplex.vertices.size(); ++omitted) {
        SimplexKey face;
        face.reserve(simplex.vertices.size() - 1);
        for (std::size_t i = 0; i < simplex.vertices.size(); ++i) {
            if (i != omitted) face.push_back(simplex.vertices[i]);
        }
        auto [key, orientation_sign] = canonical_orientation(std::move(face));
        const int alternating_sign = (omitted % 2 == 0) ? 1 : -1;
        add_chain_coefficient(result, key, alternating_sign * orientation_sign);
    }
    return result;
}

// Extend the boundary operator linearly to a finite integer chain. Chain keys
// are canonical orientations, so their coefficient signs are already encoded.
inline IntegerChain boundary(const IntegerChain& chain) {
    IntegerChain result;
    for (const auto& [vertices, coefficient] : chain) {
        if (vertices.size() < 2) {
            throw std::invalid_argument("cannot take the boundary of a 0-chain");
        }
        if (!std::is_sorted(vertices.begin(), vertices.end()) ||
            std::adjacent_find(vertices.begin(), vertices.end()) != vertices.end() ||
            std::any_of(vertices.begin(), vertices.end(),
                        [](const std::string& vertex) { return vertex.empty(); })) {
            throw std::invalid_argument("chain keys must be valid canonical simplex orientations");
        }
        const IntegerChain faces = boundary(OrientedSimplex{vertices});
        for (const auto& [face, face_coefficient] : faces) {
            add_chain_coefficient(result, face, coefficient * face_coefficient);
        }
    }
    return result;
}

inline IntegerChain boundary_squared(const OrientedSimplex& simplex) {
    if (simplex.vertices.size() < 3) {
        throw std::invalid_argument("boundary squared requires a simplex of dimension >= 2");
    }
    return boundary(boundary(simplex));
}

inline bool is_zero_chain(const IntegerChain& chain) noexcept {
    return chain.empty();
}


// A degree-indexed finite simplicial chain. Every basis simplex in C_n has
// exactly n+1 vertices; the boundary map returns an element of C_(n-1).
class SimplicialChain {
public:
    SimplicialChain(std::size_t degree, IntegerChain terms)
        : degree_(degree), terms_(std::move(terms)) {
        for (const auto& [vertices, coefficient] : terms_) {
            if (coefficient == 0 || vertices.size() != degree_ + 1 ||
                !std::is_sorted(vertices.begin(), vertices.end()) ||
                std::adjacent_find(vertices.begin(), vertices.end()) != vertices.end() ||
                std::any_of(vertices.begin(), vertices.end(),
                            [](const std::string& vertex) { return vertex.empty(); })) {
                throw std::invalid_argument(
                    "chain terms must be nonzero canonical simplices of the declared degree");
            }
        }
    }

    [[nodiscard]] std::size_t degree() const noexcept { return degree_; }
    [[nodiscard]] const IntegerChain& terms() const noexcept { return terms_; }

private:
    std::size_t degree_;
    IntegerChain terms_;
};

inline SimplicialChain boundary(const SimplicialChain& chain) {
    if (chain.degree() == 0) {
        throw std::invalid_argument("the boundary of a 0-chain is not defined in this chain model");
    }
    return SimplicialChain(chain.degree() - 1, boundary(chain.terms()));
}

inline SimplicialChain boundary_squared(const SimplicialChain& chain) {
    if (chain.degree() < 2) {
        throw std::invalid_argument("boundary squared requires a chain in degree >= 2");
    }
    return boundary(boundary(chain));
}


// A vertex map induces a degree-preserving map on normalized simplicial
// chains. A simplex whose image repeats a vertex is degenerate and maps to
// zero; otherwise its image orientation is canonicalized with the appropriate
// permutation sign. The caller is responsible for ensuring that nondegenerate
// image simplices belong to the intended target complex.
class SimplicialVertexMap {
public:
    explicit SimplicialVertexMap(std::map<std::string, std::string> images)
        : images_(std::move(images)) {
        for (const auto& [source, target] : images_) {
            if (source.empty() || target.empty()) {
                throw std::invalid_argument("vertex-map identifiers must be non-empty");
            }
        }
    }

    [[nodiscard]] const std::map<std::string, std::string>& images() const noexcept {
        return images_;
    }

    [[nodiscard]] std::string operator()(const std::string& source_vertex) const {
        const auto found = images_.find(source_vertex);
        if (found == images_.end()) {
            throw std::invalid_argument("vertex map is undefined on a source vertex");
        }
        return found->second;
    }

    [[nodiscard]] SimplicialChain apply(const SimplicialChain& chain) const {
        IntegerChain mapped;
        for (const auto& [vertices, coefficient] : chain.terms()) {
            SimplexKey image_vertices;
            image_vertices.reserve(vertices.size());
            for (const auto& vertex : vertices) {
                image_vertices.push_back((*this)(vertex));
            }

            SimplexKey distinct = image_vertices;
            std::sort(distinct.begin(), distinct.end());
            if (std::adjacent_find(distinct.begin(), distinct.end()) != distinct.end()) {
                // Degenerate simplex: zero in the normalized chain group.
                continue;
            }

            auto [key, orientation_sign] = canonical_orientation(std::move(image_vertices));
            add_chain_coefficient(mapped, key, coefficient * orientation_sign);
        }
        return SimplicialChain(chain.degree(), std::move(mapped));
    }

    // For positive-degree chains, verify the chain-map identity
    // boundary(f(c)) = f(boundary(c)).
    [[nodiscard]] bool commutes_with_boundary(const SimplicialChain& chain) const {
        if (chain.degree() == 0) {
            throw std::invalid_argument(
                "chain-map boundary check requires a chain in positive degree");
        }
        return boundary(apply(chain)).terms() == apply(boundary(chain)).terms();
    }

private:
    std::map<std::string, std::string> images_;
};


// A finite abstract simplicial complex represented by its complete set of
// non-empty faces. Construction accepts maximal simplices and closes them
// under taking non-empty subsets.
class FiniteSimplicialComplex {
public:
    FiniteSimplicialComplex(std::string id, std::vector<SimplexKey> maximal_simplices)
        : id_(std::move(id)) {
        if (id_.empty()) {
            throw std::invalid_argument("simplicial-complex identifier must be non-empty");
        }
        if (maximal_simplices.empty()) {
            throw std::invalid_argument("a finite complex needs at least one non-empty simplex");
        }
        for (auto& simplex : maximal_simplices) {
            if (simplex.empty() ||
                std::any_of(simplex.begin(), simplex.end(),
                            [](const std::string& vertex) { return vertex.empty(); })) {
                throw std::invalid_argument("maximal simplices need non-empty vertex identifiers");
            }
            auto sorted = simplex;
            std::sort(sorted.begin(), sorted.end());
            if (std::adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) {
                throw std::invalid_argument("maximal simplex contains a repeated vertex");
            }
            add_faces(sorted, 0, {});
        }
    }

    [[nodiscard]] const std::string& id() const noexcept { return id_; }
    [[nodiscard]] bool contains(const SimplexKey& simplex) const {
        auto key = simplex;
        std::sort(key.begin(), key.end());
        return !key.empty() &&
            std::adjacent_find(key.begin(), key.end()) == key.end() &&
            simplices_.count(key) != 0;
    }
    [[nodiscard]] const std::map<SimplexKey, bool>& simplices() const noexcept {
        return simplices_;
    }

private:
    void add_faces(const SimplexKey& vertices, std::size_t index, SimplexKey selected) {
        if (index == vertices.size()) {
            if (!selected.empty()) simplices_.emplace(std::move(selected), true);
            return;
        }
        add_faces(vertices, index + 1, selected);
        selected.push_back(vertices[index]);
        add_faces(vertices, index + 1, std::move(selected));
    }

    std::string id_;
    std::map<SimplexKey, bool> simplices_;
};


// A checked simplicial chain map between named finite complexes. Its vertex
// assignment must send every source simplex to a target simplex or to a
// degenerate simplex (which is zero in normalized chains).
class SimplicialChainMap {
public:
    SimplicialChainMap(FiniteSimplicialComplex source,
                       FiniteSimplicialComplex target,
                       SimplicialVertexMap vertex_map)
        : source_(std::move(source)), target_(std::move(target)),
          vertex_map_(std::move(vertex_map)) {
        for (const auto& [simplex, present] : source_.simplices()) {
            (void)present;
            IntegerChain singleton{{simplex, 1}};
            const auto image = vertex_map_.apply(SimplicialChain(simplex.size() - 1,
                                                                  std::move(singleton)));
            for (const auto& [image_simplex, coefficient] : image.terms()) {
                (void)coefficient;
                if (!target_.contains(image_simplex)) {
                    throw std::invalid_argument(
                        "vertex map sends a source simplex outside the target complex");
                }
            }
        }
    }

    [[nodiscard]] const std::string& source_id() const noexcept { return source_.id(); }
    [[nodiscard]] const std::string& target_id() const noexcept { return target_.id(); }

    [[nodiscard]] bool source_contains(const SimplexKey& simplex) const {
        return source_.contains(simplex);
    }
    [[nodiscard]] bool target_contains(const SimplexKey& simplex) const {
        return target_.contains(simplex);
    }
    [[nodiscard]] const std::map<SimplexKey, bool>& source_simplices() const noexcept {
        return source_.simplices();
    }
    [[nodiscard]] const std::map<SimplexKey, bool>& target_simplices() const noexcept {
        return target_.simplices();
    }

    [[nodiscard]] SimplicialChain apply(const SimplicialChain& chain) const {
        for (const auto& [simplex, coefficient] : chain.terms()) {
            (void)coefficient;
            if (!source_.contains(simplex)) {
                throw std::invalid_argument("chain contains a simplex outside the source complex");
            }
        }
        auto image = vertex_map_.apply(chain);
        for (const auto& [simplex, coefficient] : image.terms()) {
            (void)coefficient;
            if (!target_.contains(simplex)) {
                throw std::logic_error("validated chain map produced a simplex outside its target");
            }
        }
        return image;
    }

    [[nodiscard]] bool commutes_with_boundary(const SimplicialChain& chain) const {
        if (chain.degree() == 0) {
            throw std::invalid_argument("boundary commutation requires positive degree");
        }
        return boundary(apply(chain)).terms() == apply(boundary(chain)).terms();
    }

    // Compose this map A -> B with next map B -> C.
    [[nodiscard]] SimplicialChainMap then(const SimplicialChainMap& next) const {
        if (target_.id() != next.source_.id()) {
            throw std::invalid_argument("chain-map composition has mismatched intermediate complexes");
        }
        std::map<std::string, std::string> composed;
        for (const auto& [source_vertex, ignored] : vertex_map_.images()) {
            (void)ignored;
            composed.emplace(source_vertex, next.vertex_map_(vertex_map_(source_vertex)));
        }
        return SimplicialChainMap(source_, next.target_, SimplicialVertexMap(std::move(composed)));
    }

private:
    FiniteSimplicialComplex source_;
    FiniteSimplicialComplex target_;
    SimplicialVertexMap vertex_map_;
};


// Add an integer multiple of one finite chain to another, removing zero
// coefficients so equality is representation-independent.
inline void add_scaled_chain(IntegerChain& destination,
                             const IntegerChain& source,
                             int scale) {
    for (const auto& [simplex, coefficient] : source) {
        add_chain_coefficient(destination, simplex, scale * coefficient);
    }
}


// A degree +1 chain homotopy H between two chain maps f,g : C -> D.
// Values are supplied on source basis simplices; omitted values are zero.
// The defining equation is f - g = boundary o H + H o boundary.
class SimplicialChainHomotopy {
public:
    SimplicialChainHomotopy(
        const SimplicialChainMap& f,
        const SimplicialChainMap& g,
        std::map<SimplexKey, IntegerChain> values)
        : source_id_(f.source_id()), target_id_(f.target_id()),
          source_simplices_(f.source_simplices()),
          target_simplices_(f.target_simplices()), values_(std::move(values)) {
        if (f.source_id() != g.source_id() || f.target_id() != g.target_id()) {
            throw std::invalid_argument(
                "chain homotopy requires maps with identical source and target complexes");
        }
        for (const auto& [source_simplex, image] : values_) {
            if (!f.source_contains(source_simplex) ||
                !std::is_sorted(source_simplex.begin(), source_simplex.end()) ||
                std::adjacent_find(source_simplex.begin(), source_simplex.end()) != source_simplex.end()) {
                throw std::invalid_argument("homotopy key must be a canonical simplex in the source");
            }
            const std::size_t expected_degree = source_simplex.size();
            for (const auto& [target_simplex, coefficient] : image) {
                if (coefficient == 0 || target_simplex.size() != expected_degree + 1 ||
                    !std::is_sorted(target_simplex.begin(), target_simplex.end()) ||
                    std::adjacent_find(target_simplex.begin(), target_simplex.end()) != target_simplex.end() ||
                    !f.target_contains(target_simplex)) {
                    throw std::invalid_argument(
                        "homotopy values must be nonzero target simplices one degree higher");
                }
            }
        }
    }

    [[nodiscard]] const std::string& source_id() const noexcept { return source_id_; }
    [[nodiscard]] const std::string& target_id() const noexcept { return target_id_; }

    [[nodiscard]] SimplicialChain apply(const SimplicialChain& chain) const {
        IntegerChain result;
        for (const auto& [simplex, coefficient] : chain.terms()) {
            if (source_simplices_.count(simplex) == 0) {
                throw std::invalid_argument("homotopy input contains a simplex outside the source");
            }
            const auto found = values_.find(simplex);
            if (found == values_.end()) continue;
            add_scaled_chain(result, found->second, coefficient);
        }
        for (const auto& [simplex, coefficient] : result) {
            (void)coefficient;
            if (target_simplices_.count(simplex) == 0) {
                throw std::logic_error("homotopy output contains a simplex outside the target");
            }
        }
        return SimplicialChain(chain.degree() + 1, std::move(result));
    }

    // Check f(c)-g(c) = dH(c)+H(dc) for every basis simplex in the
    // finite source complex. Checking basis simplices suffices by linearity.
    [[nodiscard]] bool verifies(const SimplicialChainMap& f,
                                const SimplicialChainMap& g) const {
        if (f.source_id() != source_id_ || g.source_id() != source_id_ ||
            f.target_id() != target_id_ || g.target_id() != target_id_) {
            return false;
        }
        for (const auto& [simplex, present] : f.source_simplices()) {
            (void)present;
            const std::size_t degree = simplex.size() - 1;
            const SimplicialChain basis(degree, IntegerChain{{simplex, 1}});
            IntegerChain lhs = f.apply(basis).terms();
            add_scaled_chain(lhs, g.apply(basis).terms(), -1);

            const auto h_basis = apply(basis);
            IntegerChain rhs = boundary(h_basis).terms();
            if (degree > 0) {
                const auto h_boundary = apply(boundary(basis));
                add_scaled_chain(rhs, h_boundary.terms(), 1);
            }
            if (lhs != rhs) return false;
        }
        return true;
    }

private:
    std::string source_id_;
    std::string target_id_;
    std::map<SimplexKey, bool> source_simplices_;
    std::map<SimplexKey, bool> target_simplices_;
    std::map<SimplexKey, IntegerChain> values_;
};


// Compute matrix rank over the field F_2. Boundary coefficients +1 and -1
// both become 1, so this gives exact homology over F_2 without floating-point
// tolerances or integer-overflow assumptions.
inline std::size_t rank_mod2(std::vector<std::vector<unsigned char>> matrix) {
    if (matrix.empty()) return 0;
    const std::size_t row_count = matrix.size();
    const std::size_t column_count = matrix.front().size();
    for (const auto& row : matrix) {
        if (row.size() != column_count) {
            throw std::invalid_argument("boundary matrix must be rectangular");
        }
    }

    std::size_t pivot_row = 0;
    for (std::size_t column = 0;
         column < column_count && pivot_row < row_count; ++column) {
        std::size_t selected = pivot_row;
        while (selected < row_count && (matrix[selected][column] & 1U) == 0U) {
            ++selected;
        }
        if (selected == row_count) continue;
        std::swap(matrix[pivot_row], matrix[selected]);

        for (std::size_t row = pivot_row + 1; row < row_count; ++row) {
            if ((matrix[row][column] & 1U) == 0U) continue;
            for (std::size_t c = column; c < column_count; ++c) {
                matrix[row][c] =
                    static_cast<unsigned char>((matrix[row][c] ^ matrix[pivot_row][c]) & 1U);
            }
        }
        ++pivot_row;
    }
    return pivot_row;
}


// Construct the degree-n simplicial boundary matrix over F_2. Rows are
// (n-1)-simplices and columns are n-simplices, both in canonical key order.
inline std::vector<std::vector<unsigned char>> boundary_matrix_mod2(
    const FiniteSimplicialComplex& complex, std::size_t degree) {
    if (degree == 0) return {};
    std::vector<SimplexKey> columns;
    std::vector<SimplexKey> rows;
    for (const auto& [simplex, present] : complex.simplices()) {
        (void)present;
        if (simplex.size() == degree + 1) columns.push_back(simplex);
        if (simplex.size() == degree) rows.push_back(simplex);
    }

    std::map<SimplexKey, std::size_t> row_index;
    for (std::size_t i = 0; i < rows.size(); ++i) row_index.emplace(rows[i], i);
    std::vector<std::vector<unsigned char>> matrix(
        rows.size(), std::vector<unsigned char>(columns.size(), 0));
    for (std::size_t column = 0; column < columns.size(); ++column) {
        const auto faces = boundary(OrientedSimplex{columns[column]});
        for (const auto& [face, coefficient] : faces) {
            (void)coefficient;
            const auto found = row_index.find(face);
            if (found == row_index.end()) {
                throw std::logic_error("finite complex is missing a face of one of its simplices");
            }
            matrix[found->second][column] ^= 1U;
        }
    }
    return matrix;
}


struct F2HomologyGroup {
    std::size_t degree = 0;
    std::size_t chain_dimension = 0;
    std::size_t boundary_rank = 0;
    std::size_t coboundary_rank = 0;
    std::size_t betti_number = 0;
};


// Betti numbers over F_2: dim H_n = dim C_n - rank(d_n) - rank(d_(n+1)).
// This intentionally computes field homology, not integral torsion data.
inline std::vector<F2HomologyGroup> compute_f2_homology(
    const FiniteSimplicialComplex& complex) {
    std::size_t maximum_degree = 0;
    for (const auto& [simplex, present] : complex.simplices()) {
        (void)present;
        maximum_degree = std::max(maximum_degree, simplex.size() - 1);
    }

    std::vector<F2HomologyGroup> result;
    result.reserve(maximum_degree + 1);
    for (std::size_t degree = 0; degree <= maximum_degree; ++degree) {
        std::size_t chain_dimension = 0;
        for (const auto& [simplex, present] : complex.simplices()) {
            (void)present;
            if (simplex.size() == degree + 1) ++chain_dimension;
        }
        const auto lower = boundary_matrix_mod2(complex, degree);
        const auto upper = boundary_matrix_mod2(complex, degree + 1);
        const std::size_t boundary_rank = rank_mod2(lower);
        const std::size_t coboundary_rank = rank_mod2(upper);
        if (boundary_rank + coboundary_rank > chain_dimension) {
            throw std::logic_error("boundary ranks violate the chain-complex dimension identity");
        }
        result.push_back(F2HomologyGroup{
            degree, chain_dimension, boundary_rank, coboundary_rank,
            chain_dimension - boundary_rank - coboundary_rank
        });
    }
    return result;
}


// Return a basis for the nullspace of a matrix over F_2. The caller supplies
// the column count so matrices with zero rows still retain their domain size.
inline std::vector<std::vector<unsigned char>> nullspace_basis_mod2(
    std::vector<std::vector<unsigned char>> matrix, std::size_t column_count) {
    for (const auto& row : matrix) {
        if (row.size() != column_count) {
            throw std::invalid_argument("nullspace matrix has inconsistent row width");
        }
    }
    const std::size_t row_count = matrix.size();
    std::vector<std::size_t> pivot_columns;
    std::size_t pivot_row = 0;
    for (std::size_t column = 0;
         column < column_count && pivot_row < row_count; ++column) {
        std::size_t selected = pivot_row;
        while (selected < row_count && (matrix[selected][column] & 1U) == 0U) ++selected;
        if (selected == row_count) continue;
        std::swap(matrix[pivot_row], matrix[selected]);
        for (std::size_t row = 0; row < row_count; ++row) {
            if (row == pivot_row || (matrix[row][column] & 1U) == 0U) continue;
            for (std::size_t c = column; c < column_count; ++c) {
                matrix[row][c] = static_cast<unsigned char>(
                    (matrix[row][c] ^ matrix[pivot_row][c]) & 1U);
            }
        }
        pivot_columns.push_back(column);
        ++pivot_row;
    }

    std::vector<bool> is_pivot(column_count, false);
    for (const auto column : pivot_columns) is_pivot[column] = true;
    std::vector<std::vector<unsigned char>> basis;
    for (std::size_t free_column = 0; free_column < column_count; ++free_column) {
        if (is_pivot[free_column]) continue;
        std::vector<unsigned char> vector(column_count, 0);
        vector[free_column] = 1;
        for (std::size_t row = 0; row < pivot_columns.size(); ++row) {
            vector[pivot_columns[row]] = matrix[row][free_column] & 1U;
        }
        basis.push_back(std::move(vector));
    }
    return basis;
}


// Rank of a list of F_2 vectors, each represented in the same coordinate
// space. Empty input has rank zero.
inline std::size_t vector_rank_mod2(
    const std::vector<std::vector<unsigned char>>& vectors,
    std::size_t coordinate_count) {
    std::vector<std::vector<unsigned char>> matrix(
        coordinate_count, std::vector<unsigned char>(vectors.size(), 0));
    for (std::size_t column = 0; column < vectors.size(); ++column) {
        if (vectors[column].size() != coordinate_count) {
            throw std::invalid_argument("F2 vectors have inconsistent coordinate dimensions");
        }
        for (std::size_t row = 0; row < coordinate_count; ++row) {
            matrix[row][column] = vectors[column][row] & 1U;
        }
    }
    return rank_mod2(std::move(matrix));
}


struct F2HomologyRepresentatives {
    std::size_t degree = 0;
    std::vector<SimplexKey> basis_simplices;
    // Each representative is a cycle chain, and the classes form a basis
    // modulo boundaries. Coefficients are 0/1 in F_2.
    std::vector<IntegerChain> representatives;
};


// Compute explicit cycle representatives for a basis of H_n(K; F_2).
// Boundaries are inserted into the span first; a cycle is retained exactly
// when it contributes a new independent class modulo that span.
inline std::vector<F2HomologyRepresentatives> compute_f2_homology_representatives(
    const FiniteSimplicialComplex& complex) {
    std::size_t maximum_degree = 0;
    for (const auto& [simplex, present] : complex.simplices()) {
        (void)present;
        maximum_degree = std::max(maximum_degree, simplex.size() - 1);
    }

    std::vector<F2HomologyRepresentatives> result;
    result.reserve(maximum_degree + 1);
    for (std::size_t degree = 0; degree <= maximum_degree; ++degree) {
        std::vector<SimplexKey> basis_simplices;
        for (const auto& [simplex, present] : complex.simplices()) {
            (void)present;
            if (simplex.size() == degree + 1) basis_simplices.push_back(simplex);
        }
        const std::size_t dimension = basis_simplices.size();
        const auto cycles = nullspace_basis_mod2(
            boundary_matrix_mod2(complex, degree), dimension);
        const auto upper = boundary_matrix_mod2(complex, degree + 1);

        std::vector<std::vector<unsigned char>> span;
        if (!upper.empty()) {
            for (std::size_t column = 0; column < upper.front().size(); ++column) {
                std::vector<unsigned char> boundary_vector(dimension, 0);
                for (std::size_t row = 0; row < dimension; ++row) {
                    boundary_vector[row] = upper[row][column] & 1U;
                }
                span.push_back(std::move(boundary_vector));
            }
        }

        std::size_t current_rank = vector_rank_mod2(span, dimension);
        F2HomologyRepresentatives group;
        group.degree = degree;
        group.basis_simplices = basis_simplices;
        for (const auto& cycle : cycles) {
            auto candidate_span = span;
            candidate_span.push_back(cycle);
            const std::size_t next_rank = vector_rank_mod2(candidate_span, dimension);
            if (next_rank == current_rank) continue;

            IntegerChain representative;
            for (std::size_t i = 0; i < dimension; ++i) {
                if ((cycle[i] & 1U) != 0U) add_chain_coefficient(representative, basis_simplices[i], 1);
            }
            group.representatives.push_back(std::move(representative));
            span.push_back(cycle);
            current_rank = next_rank;
        }
        result.push_back(std::move(group));
    }
    return result;
}


// Exact integer matrices with explicit dimensions (including 0-by-n maps).
using Integer = std::int64_t;
struct IntegerMatrix {
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::vector<std::vector<Integer>> values;

    IntegerMatrix() = default;
    IntegerMatrix(std::size_t row_count, std::size_t column_count)
        : rows(row_count), columns(column_count),
          values(row_count, std::vector<Integer>(column_count, 0)) {}
};

inline Integer checked_integer(__int128 value) {
    if (value < static_cast<__int128>(std::numeric_limits<Integer>::min()) ||
        value > static_cast<__int128>(std::numeric_limits<Integer>::max())) {
        throw std::overflow_error("integer Smith reduction overflow");
    }
    return static_cast<Integer>(value);
}

inline IntegerMatrix integer_boundary_matrix(
    const FiniteSimplicialComplex& complex, std::size_t degree) {
    std::vector<SimplexKey> columns;
    std::vector<SimplexKey> rows;
    for (const auto& [simplex, present] : complex.simplices()) {
        (void)present;
        if (simplex.size() == degree + 1) columns.push_back(simplex);
        if (degree > 0 && simplex.size() == degree) rows.push_back(simplex);
    }
    IntegerMatrix matrix(rows.size(), columns.size());
    std::map<SimplexKey, std::size_t> row_index;
    for (std::size_t i = 0; i < rows.size(); ++i) row_index.emplace(rows[i], i);
    if (degree == 0) return matrix;
    for (std::size_t column = 0; column < columns.size(); ++column) {
        const auto faces = boundary(OrientedSimplex{columns[column]});
        for (const auto& [face, coefficient] : faces) {
            const auto found = row_index.find(face);
            if (found == row_index.end()) {
                throw std::logic_error("finite complex is missing a face of one of its simplices");
            }
            matrix.values[found->second][column] = checked_integer(
                static_cast<__int128>(matrix.values[found->second][column]) + coefficient);
        }
    }
    return matrix;
}


struct SmithNormalForm {
    IntegerMatrix diagonal;
    IntegerMatrix right_transform;
    IntegerMatrix right_transform_inverse;
    std::size_t rank = 0;
    std::vector<Integer> invariant_factors;
};

// Euclidean row/column reduction. The right transformations are retained so
// kernels and quotient groups can be computed, not merely matrix rank.
inline SmithNormalForm smith_normal_form(IntegerMatrix input) {
    if (input.values.size() != input.rows) {
        throw std::invalid_argument("integer matrix row count is inconsistent");
    }
    for (const auto& row : input.values) {
        if (row.size() != input.columns) {
            throw std::invalid_argument("integer matrix is ragged");
        }
    }
    IntegerMatrix right(input.columns, input.columns);
    IntegerMatrix inverse(input.columns, input.columns);
    for (std::size_t i = 0; i < input.columns; ++i) {
        right.values[i][i] = 1;
        inverse.values[i][i] = 1;
    }
    const auto swap_rows = [](IntegerMatrix& matrix, std::size_t a, std::size_t b) {
        if (a != b) std::swap(matrix.values[a], matrix.values[b]);
    };
    const auto swap_columns = [](IntegerMatrix& matrix, std::size_t a, std::size_t b) {
        if (a != b) for (auto& row : matrix.values) std::swap(row[a], row[b]);
    };
    const auto add_row_multiple = [](IntegerMatrix& matrix, std::size_t target,
                                     std::size_t source, Integer factor) {
        for (std::size_t j = 0; j < matrix.columns; ++j) {
            matrix.values[target][j] = checked_integer(
                static_cast<__int128>(matrix.values[target][j]) +
                static_cast<__int128>(factor) * matrix.values[source][j]);
        }
    };
    const auto add_column_multiple = [](IntegerMatrix& matrix, std::size_t target,
                                        std::size_t source, Integer factor) {
        for (std::size_t i = 0; i < matrix.rows; ++i) {
            matrix.values[i][target] = checked_integer(
                static_cast<__int128>(matrix.values[i][target]) +
                static_cast<__int128>(factor) * matrix.values[i][source]);
        }
    };

    const std::size_t limit = std::min(input.rows, input.columns);
    std::size_t pivot = 0;
    while (pivot < limit) {
        std::size_t selected_row = input.rows;
        std::size_t selected_column = input.columns;
        for (std::size_t i = pivot; i < input.rows; ++i) {
            for (std::size_t j = pivot; j < input.columns; ++j) {
                if (input.values[i][j] == 0) continue;
                const auto magnitude = [](Integer value) -> __int128 {
                    const __int128 wide = value;
                    return wide < 0 ? -wide : wide;
                };
                if (selected_row == input.rows ||
                    magnitude(input.values[i][j]) <
                    magnitude(input.values[selected_row][selected_column])) {
                    selected_row = i;
                    selected_column = j;
                }
            }
        }
        if (selected_row == input.rows) break;
        swap_rows(input, pivot, selected_row);
        swap_columns(input, pivot, selected_column);
        swap_columns(right, pivot, selected_column);
        swap_rows(inverse, pivot, selected_column);

        for (;;) {
            bool restart = false;
            for (std::size_t i = pivot + 1; i < input.rows; ++i) {
                if (input.values[i][pivot] == 0) continue;
                const Integer q = checked_integer(
                    static_cast<__int128>(input.values[i][pivot]) /
                    static_cast<__int128>(input.values[pivot][pivot]));
                add_row_multiple(input, i, pivot,
                    checked_integer(-static_cast<__int128>(q)));
                if (input.values[i][pivot] != 0) {
                    swap_rows(input, i, pivot);
                }
                restart = true;
                break;
            }
            if (restart) continue;

            for (std::size_t j = pivot + 1; j < input.columns; ++j) {
                if (input.values[pivot][j] == 0) continue;
                const Integer q = checked_integer(
                    static_cast<__int128>(input.values[pivot][j]) /
                    static_cast<__int128>(input.values[pivot][pivot]));
                const Integer negative_q = checked_integer(-static_cast<__int128>(q));
                add_column_multiple(input, j, pivot, negative_q);
                add_column_multiple(right, j, pivot, negative_q);
                // (V E)^-1 = E^-1 V^-1 for E: col_j -= q col_pivot.
                add_row_multiple(inverse, pivot, j, q);
                if (input.values[pivot][j] != 0) {
                    swap_columns(input, j, pivot);
                    swap_columns(right, j, pivot);
                    swap_rows(inverse, j, pivot);
                }
                restart = true;
                break;
            }
            if (restart) continue;

            std::size_t bad_row = input.rows;
            for (std::size_t i = pivot + 1; i < input.rows && bad_row == input.rows; ++i) {
                for (std::size_t j = pivot + 1; j < input.columns; ++j) {
                    if (static_cast<__int128>(input.values[i][j]) %
                        static_cast<__int128>(input.values[pivot][pivot]) != 0) {
                        bad_row = i;
                        break;
                    }
                }
            }
            if (bad_row != input.rows) {
                // Bring a non-divisible submatrix entry into the pivot row;
                // the next Euclidean column pass strictly reduces the pivot.
                add_row_multiple(input, pivot, bad_row, 1);
                continue;
            }
            break;
        }
        if (input.values[pivot][pivot] < 0) {
            for (std::size_t j = 0; j < input.columns; ++j) {
                input.values[pivot][j] = checked_integer(-static_cast<__int128>(input.values[pivot][j]));
            }
        }
        ++pivot;
    }

    SmithNormalForm result;
    result.diagonal = std::move(input);
    result.right_transform = std::move(right);
    result.right_transform_inverse = std::move(inverse);
    for (std::size_t i = 0; i < limit; ++i) {
        const Integer value = result.diagonal.values[i][i];
        if (value == 0) break;
        if (value < 0 || (i > 0 && value % result.invariant_factors.back() != 0)) {
            throw std::logic_error("Smith reduction failed the positive divisibility-chain invariant");
        }
        result.invariant_factors.push_back(value);
    }
    result.rank = result.invariant_factors.size();
    return result;
}

struct IntegralHomologyGroup {
    std::size_t degree = 0;
    std::size_t free_rank = 0;
    std::vector<Integer> torsion_invariant_factors; // factors > 1; units are omitted
};

// Compute H_n for a finite free chain complex from consecutive boundary maps.
// boundary_n has shape dim(C_(n-1)) x dim(C_n); boundary_next has shape
// dim(C_n) x dim(C_(n+1)). The chain identity d_n*d_(n+1)=0 is checked.
inline IntegralHomologyGroup compute_integral_homology_group(
    std::size_t degree,
    const IntegerMatrix& boundary_n,
    const IntegerMatrix& boundary_next) {
    if (boundary_n.columns != boundary_next.rows) {
        throw std::invalid_argument("consecutive boundary maps have incompatible dimensions");
    }
    const std::size_t chain_dimension = boundary_n.columns;
    if (boundary_n.values.size() != boundary_n.rows ||
        boundary_next.values.size() != boundary_next.rows) {
        throw std::invalid_argument("boundary matrix dimensions are inconsistent");
    }
    for (const auto& row : boundary_n.values) if (row.size() != boundary_n.columns)
        throw std::invalid_argument("boundary_n is ragged");
    for (const auto& row : boundary_next.values) if (row.size() != boundary_next.columns)
        throw std::invalid_argument("boundary_next is ragged");

    for (std::size_t i = 0; i < boundary_n.rows; ++i) {
        for (std::size_t j = 0; j < boundary_next.columns; ++j) {
            __int128 sum = 0;
            for (std::size_t k = 0; k < chain_dimension; ++k) {
                sum += static_cast<__int128>(boundary_n.values[i][k]) *
                       boundary_next.values[k][j];
            }
            if (sum != 0) throw std::invalid_argument("boundary composition is not zero");
        }
    }

    const auto snf_n = smith_normal_form(boundary_n);
    const std::size_t kernel_rank = chain_dimension - snf_n.rank;
    // Express im(d_(n+1)) in the unimodular basis that splits off im(d_n).
    IntegerMatrix coordinates(chain_dimension, boundary_next.columns);
    for (std::size_t i = 0; i < chain_dimension; ++i) {
        for (std::size_t j = 0; j < boundary_next.columns; ++j) {
            __int128 sum = 0;
            for (std::size_t k = 0; k < chain_dimension; ++k) {
                sum += static_cast<__int128>(snf_n.right_transform_inverse.values[i][k]) *
                       boundary_next.values[k][j];
            }
            coordinates.values[i][j] = checked_integer(sum);
        }
    }
    for (std::size_t i = 0; i < snf_n.rank; ++i) {
        for (std::size_t j = 0; j < coordinates.columns; ++j) {
            if (coordinates.values[i][j] != 0) {
                throw std::logic_error("boundary image does not lie in the computed kernel lattice");
            }
        }
    }
    IntegerMatrix restricted(kernel_rank, boundary_next.columns);
    for (std::size_t i = 0; i < kernel_rank; ++i) {
        for (std::size_t j = 0; j < boundary_next.columns; ++j) {
            restricted.values[i][j] = coordinates.values[snf_n.rank + i][j];
        }
    }
    const auto snf_next = smith_normal_form(std::move(restricted));
    IntegralHomologyGroup group;
    group.degree = degree;
    group.free_rank = kernel_rank - snf_next.rank;
    for (const Integer factor : snf_next.invariant_factors) {
        if (factor > 1) group.torsion_invariant_factors.push_back(factor);
    }
    return group;
}

inline IntegralHomologyGroup compute_integral_homology(
    const FiniteSimplicialComplex& complex, std::size_t degree) {
    return compute_integral_homology_group(
        degree, integer_boundary_matrix(complex, degree),
        integer_boundary_matrix(complex, degree + 1));
}

// Cellular RP^2 has C_2 --(2)--> C_1 --(0)--> C_0.
// This helper exposes the standard discriminating chain complex as matrices;
// its H_1 is Z/2, unlike its F_2 Betti number alone.
inline IntegralHomologyGroup real_projective_plane_h1() {
    IntegerMatrix d1(1, 1);
    IntegerMatrix d2(1, 1);
    d2.values[0][0] = 2;
    return compute_integral_homology_group(1, d1, d2);
}



// The minimal six-vertex triangulation of RP^2 (10 facets). Unlike the
// cellular fixture above, this is a genuine abstract simplicial complex;
// homology is computed from its oriented simplicial boundary matrices.
inline FiniteSimplicialComplex triangulated_real_projective_plane() {
    return FiniteSimplicialComplex("triangulated-real-projective-plane", {
        {"0", "1", "2"}, {"0", "1", "3"}, {"0", "2", "4"},
        {"0", "3", "5"}, {"0", "4", "5"}, {"1", "2", "5"},
        {"1", "3", "4"}, {"1", "4", "5"}, {"2", "3", "4"},
        {"2", "3", "5"}
    });
}

// A finite filtered complex assigns a nondecreasing filtration value to every
// simplex: each face must appear no later than its cofaces. Persistent homology
// is computed over F_2 by standard left-to-right boundary-matrix reduction.
struct FilteredSimplex {
    SimplexKey simplex;
    double filtration = 0.0;
};

struct F2PersistenceInterval {
    std::size_t degree = 0;
    double birth = 0.0;
    double death = std::numeric_limits<double>::infinity();
    SimplexKey birth_simplex;
    SimplexKey death_simplex;
    // A cycle representative in C_degree at the birth parameter, over F_2.
    // Its class is the interval's generator until the recorded death.
    IntegerChain birth_cycle;
    [[nodiscard]] bool essential() const noexcept {
        return !std::isfinite(death);
    }
};

// Column reduction tracks both R = D V and the change-of-basis columns V.
// If R_j is zero, V_j is an actual cycle representative born at simplex j.
inline std::vector<F2PersistenceInterval> compute_f2_persistent_homology(
    const std::vector<FilteredSimplex>& filtration) {
    if (filtration.empty()) return {};
    std::map<SimplexKey, double> values;
    for (const auto& item : filtration) {
        if (item.simplex.empty() || !std::isfinite(item.filtration) ||
            std::any_of(item.simplex.begin(), item.simplex.end(),
                        [](const std::string& vertex) { return vertex.empty(); })) {
            throw std::invalid_argument("filtered simplices need valid vertices and finite filtration values");
        }
        auto [key, sign] = canonical_orientation(item.simplex);
        (void)sign;
        if (!values.emplace(std::move(key), item.filtration).second) {
            throw std::invalid_argument("filtered complex contains a duplicate simplex");
        }
    }
    for (const auto& [simplex, value] : values) {
        if (simplex.size() <= 1) continue;
        const auto faces = boundary(OrientedSimplex{simplex});
        for (const auto& [face, coefficient] : faces) {
            (void)coefficient;
            const auto found = values.find(face);
            if (found == values.end() || found->second > value) {
                throw std::invalid_argument("filtration is not closed under faces");
            }
        }
    }

    std::vector<SimplexKey> ordered;
    ordered.reserve(values.size());
    for (const auto& [simplex, value] : values) {
        (void)value;
        ordered.push_back(simplex);
    }
    std::sort(ordered.begin(), ordered.end(), [&](const SimplexKey& a, const SimplexKey& b) {
        if (values.at(a) != values.at(b)) return values.at(a) < values.at(b);
        if (a.size() != b.size()) return a.size() < b.size();
        return a < b;
    });
    std::map<SimplexKey, std::size_t> index;
    for (std::size_t i = 0; i < ordered.size(); ++i) index.emplace(ordered[i], i);

    std::map<std::size_t, std::size_t> pivot_to_column;
    std::vector<std::set<std::size_t>> reduced_columns;
    std::vector<std::set<std::size_t>> change_columns;
    std::vector<bool> creates_class(ordered.size(), false);
    std::vector<F2PersistenceInterval> intervals;
    for (std::size_t column = 0; column < ordered.size(); ++column) {
        std::set<std::size_t> reduced;
        if (ordered[column].size() > 1) {
            const auto faces = boundary(OrientedSimplex{ordered[column]});
            for (const auto& [face, coefficient] : faces) {
                (void)coefficient;
                reduced.insert(index.at(face));
            }
        }
        std::set<std::size_t> change{column};
        while (!reduced.empty()) {
            const std::size_t low = *reduced.rbegin();
            const auto paired = pivot_to_column.find(low);
            if (paired == pivot_to_column.end()) break;
            const auto& other_reduced = reduced_columns[paired->second];
            std::set<std::size_t> merged_reduced;
            std::set_symmetric_difference(reduced.begin(), reduced.end(),
                other_reduced.begin(), other_reduced.end(),
                std::inserter(merged_reduced, merged_reduced.begin()));
            reduced = std::move(merged_reduced);

            const auto& other_change = change_columns[paired->second];
            std::set<std::size_t> merged_change;
            std::set_symmetric_difference(change.begin(), change.end(),
                other_change.begin(), other_change.end(),
                std::inserter(merged_change, merged_change.begin()));
            change = std::move(merged_change);
        }
        if (reduced.empty()) {
            creates_class[column] = true;
        } else {
            const std::size_t low = *reduced.rbegin();
            pivot_to_column.emplace(low, column);
            const std::size_t degree = ordered[low].size() - 1;
            IntegerChain cycle;
            for (const std::size_t term : change_columns[low]) {
                if (ordered[term].size() != degree + 1) {
                    throw std::logic_error("persistence change-of-basis column mixes degrees");
                }
                add_chain_coefficient(cycle, ordered[term], 1);
            }
            intervals.push_back(F2PersistenceInterval{
                degree, values.at(ordered[low]), values.at(ordered[column]),
                ordered[low], ordered[column], std::move(cycle)});
        }
        reduced_columns.push_back(std::move(reduced));
        change_columns.push_back(std::move(change));
    }
    for (std::size_t i = 0; i < ordered.size(); ++i) {
        if (creates_class[i] && pivot_to_column.count(i) == 0) {
            IntegerChain cycle;
            const std::size_t degree = ordered[i].size() - 1;
            for (const std::size_t term : change_columns[i]) {
                if (ordered[term].size() != degree + 1) {
                    throw std::logic_error("essential persistence cycle mixes degrees");
                }
                add_chain_coefficient(cycle, ordered[term], 1);
            }
            intervals.push_back(F2PersistenceInterval{
                degree, values.at(ordered[i]),
                std::numeric_limits<double>::infinity(), ordered[i], {},
                std::move(cycle)});
        }
    }
    std::sort(intervals.begin(), intervals.end(), [](const auto& a, const auto& b) {
        if (a.degree != b.degree) return a.degree < b.degree;
        if (a.birth != b.birth) return a.birth < b.birth;
        if (a.death != b.death) return a.death < b.death;
        return a.birth_simplex < b.birth_simplex;
    });
    return intervals;
}

// A paired state at one sampled point on a named continuum edge.
struct PairedContinuumSample {
    std::string edge_id;
    std::string sample_id;
    double parameter = 0.0;
    double first = 0.0;
    double second = 0.0;
    std::vector<std::string> assumptions;
};

// A simplex is explicitly declared as a maximal relation among sample IDs.
// No 2-simplex is inferred merely because three edge samples form a picture.
struct ContinuumStateSimplex {
    SimplexKey sample_ids;
    std::vector<std::string> assumptions;
};

// A shared endpoint is a named geometric/state-space vertex represented by
// an endpoint sample on each incident edge. Parameters are explicit (normally
// 0 or 1); no endpoint is inferred from coincident floating-point coordinates.
struct ContinuumEndpointBinding {
    std::string edge_id;
    std::string sample_id;
    double endpoint_parameter = 0.0;
};

struct ContinuumEndpointConstraint {
    std::string endpoint_id;
    std::vector<ContinuumEndpointBinding> bindings;
    double tolerance = 0.0;
    std::vector<std::string> provenance;
};

struct ResolvedContinuumEndpoint {
    std::string endpoint_id;
    double first = 0.0;
    double second = 0.0;
    std::vector<std::string> incident_edges;
    std::vector<std::string> sample_ids;
    std::vector<std::string> provenance;
};


struct ContinuumStateFiltration {
    std::vector<FilteredSimplex> filtration;
    std::map<SimplexKey, std::vector<std::string>> provenance;
    std::map<SimplexKey, std::vector<double>> paired_state_values;
    std::vector<ResolvedContinuumEndpoint> endpoint_gluing;
    double threshold = 0.0;
};

// Vertex score is max(|x|,|y|); a simplex enters at the maximum score of
// its vertices. This upper-star rule guarantees faces enter no later.
inline std::string canonical_double(double value) {
    if (!std::isfinite(value)) throw std::invalid_argument("canonical persistence values must be finite");
    std::ostringstream stream;
    stream << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return stream.str();
}

inline std::vector<ResolvedContinuumEndpoint> validate_continuum_gluing(
    const std::vector<PairedContinuumSample>& samples,
    const std::vector<ContinuumEndpointConstraint>& constraints);

inline ContinuumStateFiltration build_paired_state_filtration(
    const std::vector<PairedContinuumSample>& samples,
    const std::vector<ContinuumStateSimplex>& maximal_cells,
    double threshold,
    const std::vector<ContinuumEndpointConstraint>& endpoint_constraints = {}) {
    if (!std::isfinite(threshold) || samples.empty() || maximal_cells.empty()) {
        throw std::invalid_argument("continuum filtration needs finite threshold, samples and cells");
    }
    std::map<std::string, const PairedContinuumSample*> by_id;
    for (const auto& sample : samples) {
        if (sample.edge_id.empty() || sample.sample_id.empty() ||
            !std::isfinite(sample.parameter) || !std::isfinite(sample.first) ||
            !std::isfinite(sample.second) ||
            !by_id.emplace(sample.sample_id, &sample).second) {
            throw std::invalid_argument("continuum samples need unique IDs and finite state coordinates");
        }
    }
    std::map<SimplexKey, double> scores;
    ContinuumStateFiltration result;
    result.threshold = threshold;
    result.endpoint_gluing = validate_continuum_gluing(samples, endpoint_constraints);
    std::map<std::string, std::vector<std::string>> endpoint_provenance;
    for (const auto& endpoint : result.endpoint_gluing) {
        for (const auto& sample_id : endpoint.sample_ids) {
            auto& origins = endpoint_provenance[sample_id];
            origins.push_back("endpoint:" + endpoint.endpoint_id);
            origins.insert(origins.end(), endpoint.provenance.begin(), endpoint.provenance.end());
        }
    }
    for (const auto& cell : maximal_cells) {
        if (cell.sample_ids.empty()) throw std::invalid_argument("continuum cell cannot be empty");
        auto vertices = cell.sample_ids;
        std::sort(vertices.begin(), vertices.end());
        if (std::adjacent_find(vertices.begin(), vertices.end()) != vertices.end()) {
            throw std::invalid_argument("continuum cell repeats a sample ID");
        }
        for (const auto& vertex : vertices) {
            if (by_id.count(vertex) == 0) {
                throw std::invalid_argument("continuum cell references an unknown sample");
            }
        }
        // Enumerate all nonempty faces; all receive the same max-vertex score
        // only if they contain the maximizing vertex, otherwise their own max.
        std::vector<SimplexKey> faces;
        const auto enumerate = [&](const auto& self, std::size_t at, SimplexKey selected) -> void {
            if (at == vertices.size()) {
                if (!selected.empty()) faces.push_back(std::move(selected));
                return;
            }
            self(self, at + 1, selected);
            selected.push_back(vertices[at]);
            self(self, at + 1, std::move(selected));
        };
        enumerate(enumerate, 0, {});
        for (const auto& face : faces) {
            double score = 0.0;
            std::vector<std::string> origins = cell.assumptions;
            std::vector<double> states;
            for (const auto& id : face) {
                const auto& sample = *by_id.at(id);
                score = std::max(score, std::max(std::abs(sample.first), std::abs(sample.second)));
                states.push_back(sample.first);
                states.push_back(sample.second);
                origins.push_back("edge:" + sample.edge_id);
                origins.push_back("sample:" + sample.sample_id);
                origins.push_back("parameter:" + canonical_double(sample.parameter));
                origins.insert(origins.end(), sample.assumptions.begin(), sample.assumptions.end());
                const auto glued = endpoint_provenance.find(id);
                if (glued != endpoint_provenance.end()) {
                    origins.insert(origins.end(), glued->second.begin(), glued->second.end());
                }
            }
            auto [key, sign] = canonical_orientation(face);
            (void)sign;
            auto found = scores.find(key);
            if (found == scores.end() || score < found->second) scores[key] = score;
            auto& provenance = result.provenance[key];
            provenance.insert(provenance.end(), origins.begin(), origins.end());
            auto& values_for_face = result.paired_state_values[key];
            values_for_face.insert(values_for_face.end(), states.begin(), states.end());
        }
    }
    for (const auto& endpoint : result.endpoint_gluing) {
        for (const auto& sample_id : endpoint.sample_ids) {
            if (scores.count(SimplexKey{sample_id}) == 0) {
                throw std::invalid_argument("glued endpoint sample must occur in an explicit filtration cell");
            }
        }
    }
    for (auto& [simplex, origins] : result.provenance) {
        std::sort(origins.begin(), origins.end());
        origins.erase(std::unique(origins.begin(), origins.end()), origins.end());
        if (scores.at(simplex) <= threshold) {
            result.filtration.push_back(FilteredSimplex{simplex, scores.at(simplex)});
        }
    }
    return result;
}


// Resolve shared endpoints only when the caller supplies an explicit
// compatibility constraint. The first binding is the reference state;
// every other incident edge must agree within the declared tolerance.
inline std::vector<ResolvedContinuumEndpoint> validate_continuum_gluing(
    const std::vector<PairedContinuumSample>& samples,
    const std::vector<ContinuumEndpointConstraint>& constraints) {
    std::map<std::string, const PairedContinuumSample*> by_id;
    for (const auto& sample : samples) {
        if (sample.sample_id.empty() || sample.edge_id.empty() ||
            !std::isfinite(sample.parameter) || !std::isfinite(sample.first) ||
            !std::isfinite(sample.second) ||
            !by_id.emplace(sample.sample_id, &sample).second) {
            throw std::invalid_argument("continuum gluing requires unique, named samples and finite edge/state coordinates");
        }
    }
    std::set<std::string> endpoint_ids;
    std::vector<ResolvedContinuumEndpoint> resolved;
    for (const auto& constraint : constraints) {
        if (constraint.endpoint_id.empty() || !endpoint_ids.insert(constraint.endpoint_id).second ||
            constraint.bindings.size() < 2 || !std::isfinite(constraint.tolerance) ||
            constraint.tolerance < 0.0) {
            throw std::invalid_argument("endpoint constraints need unique IDs, two bindings and finite nonnegative tolerance");
        }
        const auto& reference_binding = constraint.bindings.front();
        const auto reference = by_id.find(reference_binding.sample_id);
        if (reference == by_id.end() || reference->second->edge_id != reference_binding.edge_id ||
            !std::isfinite(reference_binding.endpoint_parameter) ||
            std::abs(reference->second->parameter - reference_binding.endpoint_parameter) > 1e-12 ||
            (std::abs(reference_binding.endpoint_parameter) > 1e-12 &&
             std::abs(reference_binding.endpoint_parameter - 1.0) > 1e-12)) {
            throw std::invalid_argument("endpoint reference binding does not identify its declared edge endpoint");
        }
        ResolvedContinuumEndpoint item;
        item.endpoint_id = constraint.endpoint_id;
        item.first = reference->second->first;
        item.second = reference->second->second;
        item.provenance = constraint.provenance;
        item.provenance.push_back("endpoint:" + constraint.endpoint_id);
        item.provenance.push_back("tolerance:" + canonical_double(constraint.tolerance));
        std::set<std::string> bound_edges;
        std::set<std::string> bound_samples;
        for (const auto& binding : constraint.bindings) {
            if (!bound_edges.insert(binding.edge_id).second ||
                !bound_samples.insert(binding.sample_id).second) {
                throw std::invalid_argument("an endpoint constraint cannot bind the same edge or sample twice");
            }
            const auto found = by_id.find(binding.sample_id);
            if (found == by_id.end() || found->second->edge_id != binding.edge_id ||
                !std::isfinite(binding.endpoint_parameter) ||
                (std::abs(binding.endpoint_parameter) > 1e-12 &&
                 std::abs(binding.endpoint_parameter - 1.0) > 1e-12) ||
                std::abs(found->second->parameter - binding.endpoint_parameter) > 1e-12) {
                throw std::invalid_argument("endpoint binding does not match an explicit sample at edge parameter 0 or 1");
            }
            if (std::abs(found->second->first - item.first) > constraint.tolerance ||
                std::abs(found->second->second - item.second) > constraint.tolerance) {
                throw std::invalid_argument("shared endpoint paired states violate compatibility tolerance");
            }
            item.incident_edges.push_back(binding.edge_id);
            item.sample_ids.push_back(binding.sample_id);
            item.provenance.push_back("endpoint:" + constraint.endpoint_id);
            item.provenance.push_back("edge:" + binding.edge_id);
            item.provenance.push_back("sample:" + binding.sample_id);
            item.provenance.push_back("parameter:" + canonical_double(binding.endpoint_parameter));
            item.provenance.insert(item.provenance.end(), found->second->assumptions.begin(),
                                   found->second->assumptions.end());
        }
        std::sort(item.provenance.begin(), item.provenance.end());
        item.provenance.erase(std::unique(item.provenance.begin(), item.provenance.end()),
                              item.provenance.end());
        resolved.push_back(std::move(item));
    }
    return resolved;
}

struct PersistenceEvidence {
    std::string algorithm_version = "merlin-persistence-f2-v2";
    std::string input_digest;
    std::string filtration_parameters;
    std::string output_digest;
    std::string reproducibility_metadata;
    // This is a computational record, not a CACE verification receipt.
};

inline std::string canonical_persistence_input(
    const std::vector<FilteredSimplex>& filtration) {
    auto ordered = filtration;
    std::sort(ordered.begin(), ordered.end(), [](const auto& a, const auto& b) {
        if (a.simplex != b.simplex) return a.simplex < b.simplex;
        return a.filtration < b.filtration;
    });
    std::string canonical;
    for (const auto& item : ordered) {
        for (const auto& vertex : item.simplex) {
            canonical += std::to_string(vertex.size()) + ":" + vertex + ";";
        }
        canonical += "@" + canonical_double(item.filtration) + "\n";
    }
    return canonical;
}

inline std::string canonical_persistence_output(
    const std::vector<F2PersistenceInterval>& intervals) {
    std::string canonical;
    for (const auto& interval : intervals) {
        canonical += std::to_string(interval.degree) + "|" +
            canonical_double(interval.birth) + "|" +
            (interval.essential() ? "inf" : canonical_double(interval.death)) + "|birth:";
        for (const auto& vertex : interval.birth_simplex) {
            canonical += std::to_string(vertex.size()) + ":" + vertex + ";";
        }
        canonical += "|death:";
        for (const auto& vertex : interval.death_simplex) {
            canonical += std::to_string(vertex.size()) + ":" + vertex + ";";
        }
        canonical += "|cycle:";
        for (const auto& [simplex, coefficient] : interval.birth_cycle) {
            for (const auto& vertex : simplex) {
                canonical += std::to_string(vertex.size()) + ":" + vertex + ";";
            }
            canonical += "=" + std::to_string(coefficient) + ",";
        }
        canonical += "\n";
    }
    return canonical;
}

inline PersistenceEvidence make_persistence_evidence(
    const std::vector<FilteredSimplex>& filtration,
    const std::vector<F2PersistenceInterval>& intervals,
    std::string filtration_parameters,
    std::string reproducibility_metadata) {
    PersistenceEvidence evidence;
    evidence.input_digest = expert_robot::sha256_hex(canonical_persistence_input(filtration));
    evidence.output_digest = expert_robot::sha256_hex(canonical_persistence_output(intervals));
    evidence.filtration_parameters = std::move(filtration_parameters);
    evidence.reproducibility_metadata = std::move(reproducibility_metadata);
    return evidence;
}

inline std::string canonical_continuum_filtration_input(
    const ContinuumStateFiltration& state_filtration) {
    std::string canonical = "threshold=" + canonical_double(state_filtration.threshold) + "\n";
    canonical += canonical_persistence_input(state_filtration.filtration);
    for (const auto& [simplex, origins] : state_filtration.provenance) {
        canonical += "simplex:";
        for (const auto& vertex : simplex) {
            canonical += std::to_string(vertex.size()) + ":" + vertex + ";";
        }
        canonical += "\norigins:";
        for (const auto& origin : origins) {
            canonical += std::to_string(origin.size()) + ":" + origin + ";";
        }
        canonical += "\nstates:";
        const auto values = state_filtration.paired_state_values.find(simplex);
        if (values != state_filtration.paired_state_values.end()) {
            for (const double value : values->second) canonical += canonical_double(value) + ",";
        }
        canonical += "\n";
    }
    return canonical;
}

inline PersistenceEvidence make_persistence_evidence(
    const ContinuumStateFiltration& state_filtration,
    const std::vector<F2PersistenceInterval>& intervals,
    std::string filtration_parameters,
    std::string reproducibility_metadata) {
    PersistenceEvidence evidence;
    evidence.input_digest = expert_robot::sha256_hex(
        canonical_continuum_filtration_input(state_filtration));
    evidence.output_digest = expert_robot::sha256_hex(canonical_persistence_output(intervals));
    evidence.filtration_parameters = std::move(filtration_parameters);
    evidence.reproducibility_metadata = std::move(reproducibility_metadata);
    return evidence;
}



// Transport-ready evidence envelope. It binds a run to immutable source and
// result identities; it is a request/record for CACE, not a CACE signature or
// a claim that independent verification has occurred.
struct PersistenceEvidenceEnvelope {
    std::string source_commit;
    std::string algorithm_version;
    std::string input_digest;
    std::string output_digest;
    std::string runner_identity;
    std::string runner_execution_id;
    std::string environment;
    std::string reproducibility_receipt_digest;
};

inline bool is_lower_hex_digest(const std::string& value) {
    return value.size() == 64 &&
        std::all_of(value.begin(), value.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
}

inline std::string canonical_persistence_evidence_envelope(
    const PersistenceEvidenceEnvelope& envelope) {
    if (envelope.source_commit.size() != 40 ||
        !std::all_of(envelope.source_commit.begin(), envelope.source_commit.end(),
                     [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
        envelope.algorithm_version.empty() || envelope.runner_identity.empty() ||
        envelope.runner_execution_id.empty() || envelope.environment.empty() ||
        !is_lower_hex_digest(envelope.input_digest) ||
        !is_lower_hex_digest(envelope.output_digest) ||
        !is_lower_hex_digest(envelope.reproducibility_receipt_digest)) {
        throw std::invalid_argument("evidence envelope is missing exact source, runner or digest identity");
    }
    const auto field = [](const std::string& name, const std::string& value) {
        return name + "=" + std::to_string(value.size()) + ":" + value + "\n";
    };
    return field("source_commit", envelope.source_commit) +
        field("algorithm_version", envelope.algorithm_version) +
        field("input_digest", envelope.input_digest) +
        field("output_digest", envelope.output_digest) +
        field("runner_identity", envelope.runner_identity) +
        field("runner_execution_id", envelope.runner_execution_id) +
        field("environment", envelope.environment) +
        field("reproducibility_receipt_digest", envelope.reproducibility_receipt_digest);
}

inline std::string persistence_evidence_envelope_digest(
    const PersistenceEvidenceEnvelope& envelope) {
    return expert_robot::sha256_hex(canonical_persistence_evidence_envelope(envelope));
}

// CACE's eventual response must bind this exact envelope digest. Signature
// verification and issuer trust remain responsibilities of the CACE verifier.
struct CaceReceiptBinding {
    std::string envelope_digest;
    std::string receipt_id;
    std::string issuer_key_id;
    std::string signature;
    std::string verifier_version;
};

inline void validate_cace_receipt_binding(
    const PersistenceEvidenceEnvelope& envelope,
    const CaceReceiptBinding& receipt) {
    if (receipt.envelope_digest != persistence_evidence_envelope_digest(envelope) ||
        receipt.receipt_id.empty() || receipt.issuer_key_id.empty() ||
        receipt.signature.empty() || receipt.verifier_version.empty()) {
        throw std::invalid_argument("CACE receipt binding is incomplete or targets different evidence bytes");
    }
}

inline std::vector<std::vector<unsigned char>> induced_f2_homology_map(
    const SimplicialChainMap& map,
    const F2HomologyRepresentatives& source_basis,
    const F2HomologyRepresentatives& target_basis) {
    if (source_basis.degree != target_basis.degree) {
        throw std::invalid_argument("induced homology map requires equal degrees");
    }
    const std::size_t degree = source_basis.degree;
    std::vector<SimplexKey> target_simplices;
    for (const auto& [simplex, present] : map.target_simplices()) {
        (void)present;
        if (simplex.size() == degree + 1) target_simplices.push_back(simplex);
    }
    if (target_simplices != target_basis.basis_simplices) {
        throw std::invalid_argument("target homology basis belongs to a different simplex ordering");
    }
    for (const auto& simplex : source_basis.basis_simplices) {
        if (!map.source_contains(simplex)) {
            throw std::invalid_argument("source homology basis contains a simplex outside the map domain");
        }
    }

    const std::size_t rows = target_simplices.size();
    std::map<SimplexKey, std::size_t> row_index;
    for (std::size_t i = 0; i < rows; ++i) row_index.emplace(target_simplices[i], i);
    std::vector<std::vector<unsigned char>> columns;
    for (const auto& [simplex, present] : map.target_simplices()) {
        (void)present;
        if (simplex.size() != degree + 2) continue;
        const auto faces = boundary(OrientedSimplex{simplex});
        std::vector<unsigned char> vector(rows, 0);
        for (const auto& [face, coefficient] : faces) {
            (void)coefficient;
            vector[row_index.at(face)] ^= 1U;
        }
        columns.push_back(std::move(vector));
    }
    const std::size_t boundary_columns = columns.size();
    for (const auto& representative : target_basis.representatives) {
        std::vector<unsigned char> vector(rows, 0);
        for (const auto& [simplex, coefficient] : representative) {
            const auto found = row_index.find(simplex);
            if (found == row_index.end()) {
                throw std::invalid_argument("target representative is outside target chain group");
            }
            vector[found->second] ^= static_cast<unsigned char>(coefficient & 1);
        }
        columns.push_back(std::move(vector));
    }

    std::vector<std::vector<unsigned char>> result(
        target_basis.representatives.size(),
        std::vector<unsigned char>(source_basis.representatives.size(), 0));
    for (std::size_t source_column = 0;
         source_column < source_basis.representatives.size(); ++source_column) {
        IntegerChain image_chain;
        for (const auto& [simplex, coefficient] : source_basis.representatives[source_column]) {
            add_chain_coefficient(image_chain, simplex, coefficient);
        }
        const SimplicialChain image = map.apply(SimplicialChain(degree, image_chain));
        std::vector<unsigned char> rhs(rows, 0);
        for (const auto& [simplex, coefficient] : image.terms()) {
            const auto found = row_index.find(simplex);
            if (found == row_index.end()) {
                throw std::logic_error("chain map image has wrong degree or leaves target chain group");
            }
            rhs[found->second] ^= static_cast<unsigned char>(coefficient & 1);
        }

        const std::size_t unknowns = columns.size();
        std::vector<std::vector<unsigned char>> augmented(
            rows, std::vector<unsigned char>(unknowns + 1, 0));
        for (std::size_t row = 0; row < rows; ++row) {
            for (std::size_t col = 0; col < unknowns; ++col) augmented[row][col] = columns[col][row];
            augmented[row][unknowns] = rhs[row];
        }
        std::vector<std::size_t> pivot_columns;
        std::size_t pivot_row = 0;
        for (std::size_t col = 0; col < unknowns && pivot_row < rows; ++col) {
            std::size_t selected = pivot_row;
            while (selected < rows && augmented[selected][col] == 0) ++selected;
            if (selected == rows) continue;
            std::swap(augmented[pivot_row], augmented[selected]);
            for (std::size_t row = 0; row < rows; ++row) {
                if (row == pivot_row || augmented[row][col] == 0) continue;
                for (std::size_t j = col; j <= unknowns; ++j) augmented[row][j] ^= augmented[pivot_row][j];
            }
            pivot_columns.push_back(col);
            ++pivot_row;
        }
        for (std::size_t row = pivot_row; row < rows; ++row) {
            bool zero = true;
            for (std::size_t col = 0; col < unknowns; ++col) zero = zero && augmented[row][col] == 0;
            if (zero && augmented[row][unknowns] != 0) {
                throw std::logic_error("mapped cycle is outside target boundaries plus homology span");
            }
        }
        std::vector<unsigned char> solution(unknowns, 0);
        for (std::size_t row = 0; row < pivot_columns.size(); ++row) {
            solution[pivot_columns[row]] = augmented[row][unknowns];
        }
        for (std::size_t target_column = 0;
             target_column < target_basis.representatives.size(); ++target_column) {
            result[target_column][source_column] = solution[boundary_columns + target_column];
        }
    }
    return result;
}

} // namespace expert_robot::math::continuum
