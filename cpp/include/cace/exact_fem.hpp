#pragma once

#include <array>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace cace::exact {

class Rational {
public:
    constexpr Rational() noexcept : num_(0), den_(1) {}

    Rational(std::int64_t numerator, std::int64_t denominator = 1) {
        assign(numerator, denominator);
    }

    static Rational parse(const std::string& text) {
        if (text.empty() || text.find_first_of(" \t\r\n") != std::string::npos) {
            throw std::invalid_argument("exact rational must be a nonempty whitespace-free string");
        }
        const auto slash = text.find('/');
        if (slash == std::string::npos) {
            return Rational(parse_i64(text), 1);
        }
        if (text.find('/', slash + 1) != std::string::npos) {
            throw std::invalid_argument("exact rational contains multiple '/' characters");
        }
        return Rational(parse_i64(text.substr(0, slash)), parse_i64(text.substr(slash + 1)));
    }

    std::int64_t numerator() const noexcept { return num_; }
    std::int64_t denominator() const noexcept { return den_; }

    std::string str() const {
        if (den_ == 1) return std::to_string(num_);
        return std::to_string(num_) + "/" + std::to_string(den_);
    }

    friend Rational operator+(const Rational& a, const Rational& b) {
        const std::int64_t g = std::gcd(a.den_, b.den_);
        const __int128 left_scale = b.den_ / g;
        const __int128 right_scale = a.den_ / g;
        const __int128 n =
            static_cast<__int128>(a.num_) * left_scale +
            static_cast<__int128>(b.num_) * right_scale;
        const __int128 d = static_cast<__int128>(a.den_) * left_scale;
        return from_i128(n, d);
    }

    friend Rational operator-(const Rational& a, const Rational& b) {
        return a + (-b);
    }

    friend Rational operator-(const Rational& a) {
        if (a.num_ == std::numeric_limits<std::int64_t>::min()) {
            throw std::overflow_error("exact rational negation overflow");
        }
        return Rational(-a.num_, a.den_);
    }

    friend Rational operator*(const Rational& a, const Rational& b) {
        const std::int64_t g1 = gcd_abs(a.num_, b.den_);
        const std::int64_t g2 = gcd_abs(b.num_, a.den_);
        const __int128 an = a.num_ / g1;
        const __int128 bd = b.den_ / g1;
        const __int128 bn = b.num_ / g2;
        const __int128 ad = a.den_ / g2;
        return from_i128(an * bn, ad * bd);
    }

    friend Rational operator/(const Rational& a, const Rational& b) {
        if (b.num_ == 0) throw std::domain_error("exact rational division by zero");
        Rational reciprocal(b.den_, b.num_);
        return a * reciprocal;
    }

    Rational& operator+=(const Rational& other) {
        *this = *this + other;
        return *this;
    }

    friend bool operator==(const Rational& a, const Rational& b) noexcept {
        return a.num_ == b.num_ && a.den_ == b.den_;
    }

    friend bool operator!=(const Rational& a, const Rational& b) noexcept {
        return !(a == b);
    }

    friend bool operator<(const Rational& a, const Rational& b) noexcept {
        return static_cast<__int128>(a.num_) * b.den_
            < static_cast<__int128>(b.num_) * a.den_;
    }

    friend bool operator>(const Rational& a, const Rational& b) noexcept { return b < a; }
    friend bool operator<=(const Rational& a, const Rational& b) noexcept { return !(b < a); }
    friend bool operator>=(const Rational& a, const Rational& b) noexcept { return !(a < b); }

private:
    std::int64_t num_;
    std::int64_t den_;

    static std::int64_t parse_i64(const std::string& text) {
        if (text.empty()) throw std::invalid_argument("empty integer in exact rational");
        std::size_t used = 0;
        long long value = 0;
        try {
            value = std::stoll(text, &used, 10);
        } catch (const std::exception&) {
            throw std::invalid_argument("invalid exact integer: " + text);
        }
        if (used != text.size()) throw std::invalid_argument("invalid exact integer: " + text);
        return static_cast<std::int64_t>(value);
    }

    static std::uint64_t abs_u64(std::int64_t value) noexcept {
        if (value >= 0) return static_cast<std::uint64_t>(value);
        return static_cast<std::uint64_t>(-(value + 1)) + 1;
    }

    static std::int64_t gcd_abs(std::int64_t a, std::int64_t b) {
        const std::uint64_t g = std::gcd(abs_u64(a), abs_u64(b));
        if (g > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())) {
            throw std::overflow_error("exact rational gcd exceeds signed range");
        }
        return static_cast<std::int64_t>(g == 0 ? 1 : g);
    }

    static std::int64_t checked_i64(__int128 value) {
        if (value < static_cast<__int128>(std::numeric_limits<std::int64_t>::min()) ||
            value > static_cast<__int128>(std::numeric_limits<std::int64_t>::max())) {
            throw std::overflow_error("exact rational arithmetic exceeded int64 range");
        }
        return static_cast<std::int64_t>(value);
    }

    static Rational from_i128(__int128 numerator, __int128 denominator) {
        return Rational(checked_i64(numerator), checked_i64(denominator));
    }

    void assign(std::int64_t numerator, std::int64_t denominator) {
        if (denominator == 0) throw std::domain_error("exact rational denominator is zero");

        __int128 n = numerator;
        __int128 d = denominator;
        if (d < 0) {
            n = -n;
            d = -d;
        }

        const std::uint64_t an =
            n < 0 ? static_cast<std::uint64_t>(-(n + 1)) + 1 : static_cast<std::uint64_t>(n);
        const std::uint64_t ad = static_cast<std::uint64_t>(d);
        const std::uint64_t g = std::gcd(an, ad);

        n /= static_cast<__int128>(g == 0 ? 1 : g);
        d /= static_cast<__int128>(g == 0 ? 1 : g);
        num_ = checked_i64(n);
        den_ = checked_i64(d);
    }
};

struct Point2 {
    Rational x;
    Rational y;

    friend bool operator==(const Point2&, const Point2&) = default;
};

struct Triangle {
    Point2 p0;
    Point2 p1;
    Point2 p2;

    Rational determinant() const {
        return (p1.x - p0.x) * (p2.y - p0.y) -
               (p1.y - p0.y) * (p2.x - p0.x);
    }
};

struct P1Affine {
    Rational c;
    Rational gx;
    Rational gy;

    Rational eval(const Point2& p) const {
        return c + gx * p.x + gy * p.y;
    }
};

struct RT0Affine {
    Rational cx;
    Rational cy;
    Rational radial;

    Rational eval_x(const Point2& p) const { return cx + radial * p.x; }
    Rational eval_y(const Point2& p) const { return cy + radial * p.y; }
    Rational divergence() const { return Rational(2) * radial; }

    Rational dot_grad(const P1Affine& v, const Point2& p) const {
        return eval_x(p) * v.gx + eval_y(p) * v.gy;
    }
};

inline Rational cell_pairing(const Triangle& triangle, const P1Affine& v, const RT0Affine& q) {
    return triangle.determinant() / Rational(6) *
        (q.dot_grad(v, triangle.p0) +
         q.dot_grad(v, triangle.p1) +
         q.dot_grad(v, triangle.p2));
}

inline Rational cell_divergence(const Triangle& triangle, const P1Affine& v, const RT0Affine& q) {
    return -(triangle.determinant() / Rational(6) * q.divergence() *
        (v.eval(triangle.p0) + v.eval(triangle.p1) + v.eval(triangle.p2)));
}

inline Rational edge_normal_x(const Point2& a, const Point2& b) {
    return b.y - a.y;
}

inline Rational edge_normal_y(const Point2& a, const Point2& b) {
    return -(b.x - a.x);
}

inline Rational edge_flux(const RT0Affine& q, const Point2& a, const Point2& b, const Point2& p) {
    return q.eval_x(p) * edge_normal_x(a, b) + q.eval_y(p) * edge_normal_y(a, b);
}

inline Rational edge_pairing(const P1Affine& v, const RT0Affine& q, const Point2& a, const Point2& b) {
    const Rational va = v.eval(a);
    const Rational vb = v.eval(b);
    const Rational ga = edge_flux(q, a, b, a);
    const Rational gb = edge_flux(q, a, b, b);
    return (Rational(2) * va * ga + va * gb + vb * ga + Rational(2) * vb * gb) / Rational(6);
}

inline Rational local_face_pairing(
    const Triangle& triangle,
    const P1Affine& v,
    const RT0Affine& q,
    std::size_t slot) {
    switch (slot) {
        case 0: return edge_pairing(v, q, triangle.p0, triangle.p1);
        case 1: return edge_pairing(v, q, triangle.p1, triangle.p2);
        case 2: return edge_pairing(v, q, triangle.p2, triangle.p0);
        default: throw std::out_of_range("local face slot must be 0, 1, or 2");
    }
}

inline Rational cell_face_pairing(const Triangle& triangle, const P1Affine& v, const RT0Affine& q) {
    return local_face_pairing(triangle, v, q, 0) +
           local_face_pairing(triangle, v, q, 1) +
           local_face_pairing(triangle, v, q, 2);
}

inline bool local_green_identity_holds(
    const Triangle& triangle,
    const P1Affine& v,
    const RT0Affine& q) {
    return cell_pairing(triangle, v, q) ==
           cell_divergence(triangle, v, q) + cell_face_pairing(triangle, v, q);
}

enum class OrientationSign { positive, negative };

struct EdgeOccurrence {
    std::size_t cell = 0;
    std::size_t slot = 0;
    OrientationSign sign = OrientationSign::positive;
};

struct EdgeRecord {
    std::size_t id = 0;
    std::array<std::size_t, 2> vertices{};
    bool interior = false;
    std::vector<EdgeOccurrence> owners;
    std::string boundary_label;
};

struct ExactMesh {
    std::vector<Point2> vertices;
    std::vector<std::array<std::size_t, 3>> triangles;
    std::vector<Rational> signed_jacobians;
    std::vector<EdgeRecord> edges;
    std::vector<std::array<std::size_t, 3>> local_edge_ids;
    std::vector<std::array<OrientationSign, 3>> local_signs;
    std::vector<std::size_t> interior_edge_ids;
    std::vector<std::size_t> boundary_edge_ids;

    Triangle triangle(std::size_t cell) const {
        const auto& ids = triangles.at(cell);
        return Triangle{vertices.at(ids[0]), vertices.at(ids[1]), vertices.at(ids[2])};
    }
};

using BoundaryLabels = std::map<std::pair<std::size_t, std::size_t>, std::string>;

inline std::pair<std::size_t, std::size_t> canonical_edge(std::size_t a, std::size_t b) {
    return a < b ? std::make_pair(a, b) : std::make_pair(b, a);
}

inline ExactMesh build_mesh(
    std::vector<Point2> vertices,
    std::vector<std::array<std::size_t, 3>> triangles,
    const BoundaryLabels& labels = {}) {

    if (vertices.size() < 3) throw std::invalid_argument("exact mesh needs at least three vertices");
    if (triangles.empty()) throw std::invalid_argument("exact mesh needs at least one triangle");

    ExactMesh mesh;
    mesh.vertices = std::move(vertices);
    mesh.triangles = std::move(triangles);
    mesh.signed_jacobians.reserve(mesh.triangles.size());

    using Key = std::pair<std::size_t, std::size_t>;
    std::map<Key, std::vector<EdgeOccurrence>> occurrences;

    for (std::size_t cell = 0; cell < mesh.triangles.size(); ++cell) {
        const auto tri = mesh.triangles[cell];
        if (tri[0] == tri[1] || tri[1] == tri[2] || tri[2] == tri[0]) {
            throw std::invalid_argument("triangle repeats a vertex");
        }
        for (const auto v : tri) {
            if (v >= mesh.vertices.size()) throw std::out_of_range("triangle vertex id is out of range");
        }

        const Rational det = mesh.triangle(cell).determinant();
        if (!(det > Rational(0))) {
            throw std::invalid_argument("all exact mesh triangles must be strictly counter-clockwise");
        }
        mesh.signed_jacobians.push_back(det);

        const std::array<std::pair<std::size_t, std::size_t>, 3> directed{{
            {tri[0], tri[1]}, {tri[1], tri[2]}, {tri[2], tri[0]}
        }};
        for (std::size_t slot = 0; slot < 3; ++slot) {
            const auto edge = canonical_edge(directed[slot].first, directed[slot].second);
            const auto sign = directed[slot] == edge
                ? OrientationSign::positive
                : OrientationSign::negative;
            occurrences[edge].push_back(EdgeOccurrence{cell, slot, sign});
        }
    }

    mesh.local_edge_ids.resize(mesh.triangles.size());
    mesh.local_signs.resize(mesh.triangles.size());

    std::size_t edge_id = 0;
    for (const auto& [edge, owners] : occurrences) {
        if (owners.size() != 1 && owners.size() != 2) {
            throw std::invalid_argument("non-manifold edge must have one or two owners");
        }

        EdgeRecord record;
        record.id = edge_id;
        record.vertices = {edge.first, edge.second};
        record.owners = owners;
        record.interior = owners.size() == 2;

        if (record.interior) {
            if (owners[0].sign == owners[1].sign) {
                throw std::invalid_argument("interior edge owners must have opposite local orientation");
            }
            mesh.interior_edge_ids.push_back(edge_id);
        } else {
            const auto it = labels.find(edge);
            record.boundary_label = it == labels.end()
                ? "boundary"
                : it->second;
            if (record.boundary_label.empty()) {
                throw std::invalid_argument("boundary label must be nonempty");
            }
            mesh.boundary_edge_ids.push_back(edge_id);
        }

        for (const auto& owner : owners) {
            mesh.local_edge_ids.at(owner.cell).at(owner.slot) = edge_id;
            mesh.local_signs.at(owner.cell).at(owner.slot) = owner.sign;
        }

        mesh.edges.push_back(std::move(record));
        ++edge_id;
    }

    for (const auto& [edge, label] : labels) {
        if (label.empty()) throw std::invalid_argument("boundary label must be nonempty");
        const auto it = occurrences.find(edge);
        if (it == occurrences.end() || it->second.size() != 1) {
            throw std::invalid_argument("boundary label references an absent or interior edge");
        }
        if (edge.first >= edge.second) {
            throw std::invalid_argument("boundary-label edge keys must be canonical ascending pairs");
        }
    }

    return mesh;
}

inline void validate_fields(
    const ExactMesh& mesh,
    const std::vector<P1Affine>& primal,
    const std::vector<RT0Affine>& flux) {
    if (primal.size() != mesh.triangles.size()) {
        throw std::invalid_argument("P1 field must contain exactly one affine cell record per triangle");
    }
    if (flux.size() != mesh.triangles.size()) {
        throw std::invalid_argument("RT0 field must contain exactly one affine cell record per triangle");
    }
}

struct AssemblyObligations {
    std::vector<Rational> cell_pairings;
    std::vector<Rational> cell_divergences;
    std::vector<std::array<Rational, 3>> local_face_pairings;
    std::vector<bool> equilibrium;
    std::vector<bool> boundary_admissible;
    std::vector<bool> interior_cancellation;
    bool all_local_green = false;
    bool ready_for_lean_assembly = false;
};

inline AssemblyObligations exact_assembly_obligations(
    const ExactMesh& mesh,
    const std::vector<P1Affine>& primal,
    const std::vector<RT0Affine>& flux) {

    validate_fields(mesh, primal, flux);

    AssemblyObligations out;
    out.cell_pairings.reserve(mesh.triangles.size());
    out.cell_divergences.reserve(mesh.triangles.size());
    out.local_face_pairings.resize(mesh.triangles.size());
    out.equilibrium.reserve(mesh.triangles.size());

    bool local_green = true;
    for (std::size_t cell = 0; cell < mesh.triangles.size(); ++cell) {
        const auto triangle = mesh.triangle(cell);
        out.cell_pairings.push_back(cell_pairing(triangle, primal[cell], flux[cell]));
        out.cell_divergences.push_back(cell_divergence(triangle, primal[cell], flux[cell]));
        for (std::size_t slot = 0; slot < 3; ++slot) {
            out.local_face_pairings[cell][slot] =
                local_face_pairing(triangle, primal[cell], flux[cell], slot);
        }
        out.equilibrium.push_back(out.cell_divergences.back() == Rational(0));
        local_green = local_green && local_green_identity_holds(triangle, primal[cell], flux[cell]);
    }
    out.all_local_green = local_green;

    for (const auto edge_id : mesh.boundary_edge_ids) {
        const auto& edge = mesh.edges.at(edge_id);
        const auto& owner = edge.owners.at(0);
        out.boundary_admissible.push_back(
            out.local_face_pairings.at(owner.cell).at(owner.slot) == Rational(0));
    }

    for (const auto edge_id : mesh.interior_edge_ids) {
        const auto& edge = mesh.edges.at(edge_id);
        const auto& left = edge.owners.at(0);
        const auto& right = edge.owners.at(1);
        out.interior_cancellation.push_back(
            out.local_face_pairings.at(left.cell).at(left.slot) +
            out.local_face_pairings.at(right.cell).at(right.slot) == Rational(0));
    }

    const auto all_true = [](const std::vector<bool>& values) {
        for (const bool value : values) if (!value) return false;
        return true;
    };
    out.ready_for_lean_assembly =
        out.all_local_green &&
        all_true(out.equilibrium) &&
        all_true(out.boundary_admissible) &&
        all_true(out.interior_cancellation);

    return out;
}

inline std::string canonical_packet_text(
    const ExactMesh& mesh,
    const std::vector<P1Affine>& primal,
    const std::vector<RT0Affine>& flux) {

    validate_fields(mesh, primal, flux);
    std::string out = "cace-exact-fem-packet-v1\n";
    out += "vertices=" + std::to_string(mesh.vertices.size()) + "\n";
    for (std::size_t i = 0; i < mesh.vertices.size(); ++i) {
        out += "v:" + std::to_string(i) + ":" +
            mesh.vertices[i].x.str() + ":" + mesh.vertices[i].y.str() + "\n";
    }
    out += "triangles=" + std::to_string(mesh.triangles.size()) + "\n";
    for (std::size_t i = 0; i < mesh.triangles.size(); ++i) {
        const auto& t = mesh.triangles[i];
        out += "t:" + std::to_string(i) + ":" +
            std::to_string(t[0]) + ":" + std::to_string(t[1]) + ":" + std::to_string(t[2]) +
            ":det=" + mesh.signed_jacobians[i].str() + "\n";
        const auto& p = primal[i];
        const auto& q = flux[i];
        out += "p1:" + std::to_string(i) + ":" +
            p.c.str() + ":" + p.gx.str() + ":" + p.gy.str() + "\n";
        out += "rt0:" + std::to_string(i) + ":" +
            q.cx.str() + ":" + q.cy.str() + ":" + q.radial.str() + "\n";
    }
    for (const auto& edge : mesh.edges) {
        out += "e:" + std::to_string(edge.id) + ":" +
            std::to_string(edge.vertices[0]) + ":" + std::to_string(edge.vertices[1]) + ":" +
            (edge.interior ? "interior" : "boundary") + ":" +
            (edge.interior ? "" : edge.boundary_label) + "\n";
        for (const auto& owner : edge.owners) {
            out += "owner:" + std::to_string(edge.id) + ":" +
                std::to_string(owner.cell) + ":" + std::to_string(owner.slot) + ":" +
                (owner.sign == OrientationSign::positive ? "pos" : "neg") + "\n";
        }
    }
    return out;
}

} // namespace cace::exact
