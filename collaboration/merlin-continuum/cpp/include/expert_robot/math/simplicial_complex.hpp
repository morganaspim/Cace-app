#pragma once

#include <algorithm>
#include <cstddef>
#include <map>
#include <stdexcept>
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

} // namespace expert_robot::math::continuum
