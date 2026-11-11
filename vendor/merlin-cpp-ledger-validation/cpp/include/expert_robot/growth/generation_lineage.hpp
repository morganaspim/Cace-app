#pragma once

#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

struct sqlite3;

namespace expert_robot::growth {

struct GenerationCandidate {
    std::string generation_id;
    std::string parent_generation_id;

    std::string source_tree_hash;
    std::string model_manifest_hash;
    std::string config_hash;

    std::string rationale;
};

struct GenerationRecord {
    GenerationCandidate candidate;
    std::string parent_lineage_hash;
    std::string lineage_hash;
};

struct EvaluationRecord {
    long long sequence{0};
    std::string generation_id;
    std::string evaluator;
    std::string evidence_hash;

    bool recommend_keep{false};
    bool verification_ok{false};
    bool efficiency_ok{false};
    bool diversity_ok{false};

    double verified_rate_delta{0.0};
    double cost_per_verified_ratio{0.0};
};

struct PromotionDecision {
    long long sequence{0};
    std::string generation_id;
    std::string actor;
    bool approved{false};
    std::string reason;
    std::string evidence_hash;
};

struct PromotionReadiness {
    bool has_positive_evaluation{false};
    bool verification_ok{false};
    bool efficiency_ok{false};
    bool diversity_ok{false};
    bool externally_approved{false};

    [[nodiscard]] bool promotable() const noexcept {
        return
            has_positive_evaluation &&
            verification_ok &&
            efficiency_ok &&
            diversity_ok &&
            externally_approved;
    }
};

struct LineageVerification {
    bool valid{true};
    long long generations{0};
    std::string reason;
    std::string first_invalid_generation;
};

class GenerationLineageStore {
public:
    explicit GenerationLineageStore(
        std::filesystem::path path);
    ~GenerationLineageStore();

    GenerationLineageStore(
        const GenerationLineageStore&) = delete;
    GenerationLineageStore& operator=(
        const GenerationLineageStore&) = delete;

    [[nodiscard]] GenerationRecord record_candidate(
        GenerationCandidate candidate);

    [[nodiscard]] EvaluationRecord record_evaluation(
        EvaluationRecord evaluation);

    /**
     * Records an external promotion/rejection decision.
     *
     * This function does not manufacture authority. The caller must supply an
     * actor and evidence hash from the external owner/policy approval boundary.
     */
    [[nodiscard]] PromotionDecision record_promotion_decision(
        PromotionDecision decision);

    [[nodiscard]] GenerationRecord generation(
        std::string_view generation_id) const;

    [[nodiscard]] std::vector<GenerationRecord> generations() const;

    [[nodiscard]] std::vector<EvaluationRecord> evaluations(
        std::string_view generation_id) const;

    [[nodiscard]] std::vector<PromotionDecision> promotion_decisions(
        std::string_view generation_id) const;

    [[nodiscard]] PromotionReadiness readiness(
        std::string_view generation_id) const;

    [[nodiscard]] LineageVerification verify() const;

private:
    void initialize();

    std::filesystem::path path_;
    sqlite3* db_{nullptr};
};

} // namespace expert_robot::growth
