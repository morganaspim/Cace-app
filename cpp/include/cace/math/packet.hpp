#pragma once

#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"
#include "cace/math/sparse_matrix.hpp"
#include "cace/math/polynomial.hpp"
#include "cace/math/geometry.hpp"
#include "cace/math/exterior.hpp"
#include "cace/math/combinatorics.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace cace::math {

namespace detail {

inline constexpr std::array<std::uint32_t, 64> sha256_k{
    0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
    0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
    0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
    0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
    0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
    0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
    0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
    0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U
};

inline constexpr std::uint32_t rotr(std::uint32_t x, std::uint32_t n) noexcept {
    return (x >> n) | (x << (32U - n));
}

inline std::string sha256_hex(std::string_view input) {
    std::vector<std::uint8_t> bytes(input.begin(), input.end());
    const std::uint64_t bit_len = static_cast<std::uint64_t>(bytes.size()) * 8U;
    bytes.push_back(0x80U);
    while ((bytes.size() % 64U) != 56U) bytes.push_back(0U);
    for (int shift = 56; shift >= 0; shift -= 8) bytes.push_back(static_cast<std::uint8_t>((bit_len >> shift) & 0xffU));

    std::array<std::uint32_t, 8> h{
        0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,
        0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U
    };

    for (std::size_t offset = 0; offset < bytes.size(); offset += 64U) {
        std::array<std::uint32_t, 64> w{};
        for (std::size_t i = 0; i < 16; ++i) {
            const std::size_t j = offset + i * 4U;
            w[i] = (static_cast<std::uint32_t>(bytes[j]) << 24U)
                 | (static_cast<std::uint32_t>(bytes[j + 1]) << 16U)
                 | (static_cast<std::uint32_t>(bytes[j + 2]) << 8U)
                 | static_cast<std::uint32_t>(bytes[j + 3]);
        }
        for (std::size_t i = 16; i < 64; ++i) {
            const std::uint32_t s0 = rotr(w[i - 15], 7U) ^ rotr(w[i - 15], 18U) ^ (w[i - 15] >> 3U);
            const std::uint32_t s1 = rotr(w[i - 2], 17U) ^ rotr(w[i - 2], 19U) ^ (w[i - 2] >> 10U);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }

        auto [a,b,c,d,e,f,g,hh] = h;
        for (std::size_t i = 0; i < 64; ++i) {
            const std::uint32_t s1 = rotr(e, 6U) ^ rotr(e, 11U) ^ rotr(e, 25U);
            const std::uint32_t ch = (e & f) ^ ((~e) & g);
            const std::uint32_t temp1 = hh + s1 + ch + sha256_k[i] + w[i];
            const std::uint32_t s0 = rotr(a, 2U) ^ rotr(a, 13U) ^ rotr(a, 22U);
            const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            const std::uint32_t temp2 = s0 + maj;
            hh = g; g = f; f = e; e = d + temp1; d = c; c = b; b = a; a = temp1 + temp2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d;
        h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }

    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (const auto word : h) out << std::setw(8) << word;
    return out.str();
}

inline void append_len_prefixed(std::string& out, std::string_view value) {
    out += std::to_string(value.size());
    out.push_back(':');
    out.append(value.data(), value.size());
}

} // namespace detail

inline std::string semantic_sha256(std::string_view canonical_bytes) {
    return detail::sha256_hex(canonical_bytes);
}

class MathPacket {
public:
    std::string schema_version = "cace.math.packet.v1";
    std::string type_id;
    std::string exact_payload;
    std::map<std::string, std::string> conventions;
    std::string source_module = "cace.rmk";
    std::string source_version = "1";
    std::vector<std::string> dependency_hashes;

    [[nodiscard]] std::string canonical_serialize() const {
        if (schema_version.empty()) throw std::invalid_argument("math packet schema_version must be nonempty");
        if (type_id.empty()) throw std::invalid_argument("math packet type_id must be nonempty");
        if (source_module.empty()) throw std::invalid_argument("math packet source_module must be nonempty");
        if (source_version.empty()) throw std::invalid_argument("math packet source_version must be nonempty");

        auto deps = dependency_hashes;
        std::sort(deps.begin(), deps.end());
        deps.erase(std::unique(deps.begin(), deps.end()), deps.end());
        for (const auto& dep : deps) {
            if (dep.size() != 64U || !std::all_of(dep.begin(), dep.end(), [](unsigned char c) {
                    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                })) {
                throw std::invalid_argument("dependency hash must be lowercase SHA-256 hex");
            }
        }

        std::string out = "CACE-MATH-PACKET\n";
        const auto field = [&out](std::string_view key, std::string_view value) {
            detail::append_len_prefixed(out, key);
            out.push_back('=');
            detail::append_len_prefixed(out, value);
            out.push_back('\n');
        };
        field("schema", schema_version);
        field("type", type_id);
        field("payload", exact_payload);
        field("source_module", source_module);
        field("source_version", source_version);
        field("convention_count", std::to_string(conventions.size()));
        for (const auto& [key, value] : conventions) {
            field("convention_key", key);
            field("convention_value", value);
        }
        field("dependency_count", std::to_string(deps.size()));
        for (const auto& dep : deps) field("dependency", dep);
        return out;
    }

    [[nodiscard]] std::string semantic_hash() const {
        return semantic_sha256(canonical_serialize());
    }

    static MathPacket rational(const Rational& value) {
        MathPacket packet;
        packet.type_id = "math.exact.rational";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("normalization", "gcd-reduced-positive-denominator");
        return packet;
    }

    static MathPacket exact_vector(const ExactVector& value) {
        MathPacket packet;
        packet.type_id = "math.exact.vector";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("ordering", "index-ascending");
        return packet;
    }

    static MathPacket exact_matrix(const ExactMatrix& value) {
        MathPacket packet;
        packet.type_id = "math.exact.matrix";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("storage", "dense-row-major-canonical-text");
        return packet;
    }

    static MathPacket exact_sparse_matrix(const ExactSparseMatrix& value) {
        MathPacket packet;
        packet.type_id = "math.exact.sparse_matrix";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("storage", "csr-canonical");
        return packet;
    }

    static MathPacket exact_polynomial(const ExactPolynomial& value) {
        MathPacket packet;
        packet.type_id = "math.exact.polynomial";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("monomial_order", "lexicographic-exponent-vector");
        return packet;
    }

    static MathPacket exact_affine_map(const ExactAffineMap& value) {
        MathPacket packet;
        packet.type_id = "math.exact.affine_map";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("action", "column-vector-Ax-plus-b");
        return packet;
    }

    static MathPacket exact_simplex(const ExactSimplex& value) {
        MathPacket packet;
        packet.type_id = "math.exact.simplex";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("orientation", "vertex-order-determinant");
        return packet;
    }

    static MathPacket exact_exterior(const ExactExterior& value) {
        MathPacket packet;
        packet.type_id = "math.exact.exterior";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("basis", "ordered-orthonormal-e0-eN");
        packet.conventions.emplace("blade_encoding", "uint64-bitmask");
        return packet;
    }

    static MathPacket exact_plane_rotor(const ExactPlaneRotor& value) {
        MathPacket packet;
        packet.type_id = "math.exact.plane_rotor";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("scalar", "math.exact.rational");
        packet.conventions.emplace("orientation", "right-handed-plane-action");
        return packet;
    }

    static MathPacket exact_permutation(const ExactPermutation& value) {
        MathPacket packet;
        packet.type_id = "math.exact.permutation";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("action", "basis-index-image");
        packet.conventions.emplace("composition", "outer-after-inner");
        return packet;
    }

    static MathPacket finite_permutation_group(const FinitePermutationGroup& value) {
        MathPacket packet;
        packet.type_id = "math.exact.finite_permutation_group";
        packet.exact_payload = value.canonical_text();
        packet.conventions.emplace("enumeration", "lexicographic-closure");
        packet.conventions.emplace("identity", "explicit-degree");
        return packet;
    }
};

} // namespace cace::math
