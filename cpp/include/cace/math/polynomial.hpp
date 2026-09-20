#pragma once

#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cace::math {

class ExactPolynomial {
public:
    using Exponents = std::vector<std::uint32_t>;
    using Term = std::pair<Exponents, Rational>;

    ExactPolynomial() = default;
    explicit ExactPolynomial(std::size_t variables) : variables_(variables) {}

    ExactPolynomial(std::size_t variables, std::vector<Term> terms)
        : variables_(variables) {
        for (auto& [powers, coefficient] : terms) add_term(std::move(powers), coefficient);
    }

    [[nodiscard]] static ExactPolynomial constant(std::size_t variables, const Rational& value) {
        ExactPolynomial out(variables);
        if (!value.is_zero()) out.terms_.emplace(Exponents(variables, 0U), value);
        return out;
    }

    [[nodiscard]] static ExactPolynomial variable(std::size_t variables, std::size_t index) {
        if (index >= variables) throw std::invalid_argument("polynomial variable index out of range");
        Exponents powers(variables, 0U);
        powers[index] = 1U;
        return ExactPolynomial(variables, {{std::move(powers), Rational(1)}});
    }

    [[nodiscard]] std::size_t variables() const noexcept { return variables_; }
    [[nodiscard]] std::size_t term_count() const noexcept { return terms_.size(); }
    [[nodiscard]] bool is_zero() const noexcept { return terms_.empty(); }
    [[nodiscard]] const std::map<Exponents, Rational>& terms() const noexcept { return terms_; }

    [[nodiscard]] std::uint32_t total_degree() const noexcept {
        std::uint32_t degree = 0;
        for (const auto& [powers, coefficient] : terms_) {
            (void)coefficient;
            std::uint32_t sum = 0;
            for (const auto p : powers) sum += p;
            degree = std::max(degree, sum);
        }
        return degree;
    }

    [[nodiscard]] Rational evaluate(const ExactVector& point) const {
        if (point.size() != variables_) throw std::invalid_argument("polynomial evaluation dimension mismatch");
        Rational sum;
        for (const auto& [powers, coefficient] : terms_) {
            Rational value = coefficient;
            for (std::size_t i = 0; i < variables_; ++i) {
                value *= rational_pow(point.at(i), powers[i]);
            }
            sum += value;
        }
        return sum;
    }

    [[nodiscard]] ExactPolynomial derivative(std::size_t variable_index) const {
        if (variable_index >= variables_) throw std::invalid_argument("polynomial derivative index out of range");
        ExactPolynomial out(variables_);
        for (const auto& [powers, coefficient] : terms_) {
            if (powers[variable_index] == 0U) continue;
            Exponents next = powers;
            const auto exponent = next[variable_index];
            --next[variable_index];
            out.add_term(std::move(next), coefficient * Rational(static_cast<Rational::rep>(exponent)));
        }
        return out;
    }

    [[nodiscard]] std::vector<ExactPolynomial> gradient() const {
        std::vector<ExactPolynomial> out;
        out.reserve(variables_);
        for (std::size_t i = 0; i < variables_; ++i) out.push_back(derivative(i));
        return out;
    }

    [[nodiscard]] std::vector<std::vector<ExactPolynomial>> hessian() const {
        std::vector<std::vector<ExactPolynomial>> out;
        out.reserve(variables_);
        for (std::size_t i = 0; i < variables_; ++i) {
            std::vector<ExactPolynomial> row;
            row.reserve(variables_);
            const auto di = derivative(i);
            for (std::size_t j = 0; j < variables_; ++j) row.push_back(di.derivative(j));
            out.push_back(std::move(row));
        }
        return out;
    }

    [[nodiscard]] ExactPolynomial scaled(const Rational& factor) const {
        if (factor.is_zero()) return ExactPolynomial(variables_);
        ExactPolynomial out(variables_);
        for (const auto& [powers, coefficient] : terms_) out.terms_.emplace(powers, coefficient * factor);
        return out;
    }

    [[nodiscard]] ExactPolynomial compose(const std::vector<ExactPolynomial>& substitutions) const {
        if (substitutions.size() != variables_) {
            throw std::invalid_argument("polynomial composition substitution count mismatch");
        }
        const std::size_t output_variables = substitutions.empty() ? 0U : substitutions.front().variables_;
        for (const auto& substitution : substitutions) {
            if (substitution.variables_ != output_variables) {
                throw std::invalid_argument("polynomial composition variable-space mismatch");
            }
        }

        ExactPolynomial out = ExactPolynomial::constant(output_variables, Rational());
        for (const auto& [powers, coefficient] : terms_) {
            ExactPolynomial term = ExactPolynomial::constant(output_variables, coefficient);
            for (std::size_t i = 0; i < variables_; ++i) {
                term = term * polynomial_pow(substitutions[i], powers[i]);
            }
            out = out + term;
        }
        return out;
    }

    [[nodiscard]] std::string canonical_text() const {
        std::string out = "vars=" + std::to_string(variables_) + ":[";
        bool first_term = true;
        for (const auto& [powers, coefficient] : terms_) {
            if (!first_term) out.push_back(';');
            first_term = false;
            out += coefficient.canonical_text();
            out.push_back('@');
            for (std::size_t i = 0; i < powers.size(); ++i) {
                if (i != 0) out.push_back(',');
                out += std::to_string(powers[i]);
            }
        }
        out.push_back(']');
        return out;
    }

    friend ExactPolynomial operator+(const ExactPolynomial& lhs, const ExactPolynomial& rhs) {
        lhs.require_same_variables(rhs);
        ExactPolynomial out = lhs;
        for (const auto& [powers, coefficient] : rhs.terms_) out.add_term(powers, coefficient);
        return out;
    }

    friend ExactPolynomial operator-(const ExactPolynomial& lhs, const ExactPolynomial& rhs) {
        lhs.require_same_variables(rhs);
        ExactPolynomial out = lhs;
        for (const auto& [powers, coefficient] : rhs.terms_) out.add_term(powers, -coefficient);
        return out;
    }

    friend ExactPolynomial operator*(const ExactPolynomial& lhs, const ExactPolynomial& rhs) {
        lhs.require_same_variables(rhs);
        ExactPolynomial out(lhs.variables_);
        for (const auto& [lp, lc] : lhs.terms_) {
            for (const auto& [rp, rc] : rhs.terms_) {
                Exponents powers(lhs.variables_, 0U);
                for (std::size_t i = 0; i < lhs.variables_; ++i) powers[i] = lp[i] + rp[i];
                out.add_term(std::move(powers), lc * rc);
            }
        }
        return out;
    }

    friend ExactPolynomial operator-(const ExactPolynomial& value) {
        return value.scaled(Rational(-1));
    }

    friend bool operator==(const ExactPolynomial&, const ExactPolynomial&) = default;

private:
    std::size_t variables_ = 0;
    std::map<Exponents, Rational> terms_;

    void add_term(Exponents powers, const Rational& coefficient) {
        if (powers.size() != variables_) throw std::invalid_argument("polynomial exponent dimension mismatch");
        if (coefficient.is_zero()) return;
        auto [it, inserted] = terms_.emplace(std::move(powers), coefficient);
        if (!inserted) {
            it->second += coefficient;
            if (it->second.is_zero()) terms_.erase(it);
        }
    }

    void require_same_variables(const ExactPolynomial& rhs) const {
        if (variables_ != rhs.variables_) throw std::invalid_argument("polynomial variable-space mismatch");
    }

    [[nodiscard]] static Rational rational_pow(Rational base, std::uint32_t exponent) {
        Rational result(1);
        while (exponent != 0U) {
            if ((exponent & 1U) != 0U) result *= base;
            exponent >>= 1U;
            if (exponent != 0U) base *= base;
        }
        return result;
    }

    [[nodiscard]] static ExactPolynomial polynomial_pow(ExactPolynomial base, std::uint32_t exponent) {
        ExactPolynomial result = ExactPolynomial::constant(base.variables_, Rational(1));
        while (exponent != 0U) {
            if ((exponent & 1U) != 0U) result = result * base;
            exponent >>= 1U;
            if (exponent != 0U) base = base * base;
        }
        return result;
    }
};

} // namespace cace::math
