#include "expert_robot/growth/generation_lineage.hpp"
#include "expert_robot/sha256.hpp"

#include <sqlite3.h>

#include <cassert>
#include <filesystem>
#include <stdexcept>

int main() {
    using namespace expert_robot;
    using namespace expert_robot::growth;

    const auto db =
        std::filesystem::temp_directory_path() /
        "expert-robot-generation-lineage.sqlite3";
    std::filesystem::remove(db);

    GenerationLineageStore store(db);

    const std::string h1 = sha256_hex("root-source");
    const std::string h2 = sha256_hex("root-models");
    const std::string h3 = sha256_hex("root-config");

    const auto root =
        store.record_candidate(
            GenerationCandidate{
                .generation_id = "generation-0000",
                .parent_generation_id = "",
                .source_tree_hash = h1,
                .model_manifest_hash = h2,
                .config_hash = h3,
                .rationale = "initial qualified baseline"
            });

    assert(root.parent_lineage_hash.empty());
    assert(root.lineage_hash.size() == 64);

    const auto child =
        store.record_candidate(
            GenerationCandidate{
                .generation_id = "generation-0001",
                .parent_generation_id = "generation-0000",
                .source_tree_hash =
                    sha256_hex("child-source"),
                .model_manifest_hash =
                    sha256_hex("child-models"),
                .config_hash =
                    sha256_hex("child-config"),
                .rationale =
                    "candidate route-planning improvement"
            });

    assert(
        child.parent_lineage_hash ==
        root.lineage_hash);
    assert(
        child.lineage_hash !=
        root.lineage_hash);

    auto readiness =
        store.readiness("generation-0001");
    assert(!readiness.promotable());

    const auto eval =
        store.record_evaluation(
            EvaluationRecord{
                .generation_id =
                    "generation-0001",
                .evaluator =
                    "math_ablation_suite_v1",
                .evidence_hash =
                    sha256_hex("eval-evidence"),
                .recommend_keep = true,
                .verification_ok = true,
                .efficiency_ok = true,
                .diversity_ok = true,
                .verified_rate_delta = 0.08,
                .cost_per_verified_ratio = 0.91
            });

    assert(eval.sequence > 0);

    readiness =
        store.readiness("generation-0001");
    assert(
        readiness.has_positive_evaluation);
    assert(
        readiness.verification_ok);
    assert(
        readiness.efficiency_ok);
    assert(
        readiness.diversity_ok);
    assert(
        !readiness.externally_approved);
    assert(
        !readiness.promotable());

    const auto rejected =
        store.record_promotion_decision(
            PromotionDecision{
                .generation_id =
                    "generation-0001",
                .actor =
                    "owner-policy-boundary",
                .approved = false,
                .reason =
                    "hold for another benchmark batch",
                .evidence_hash =
                    sha256_hex("owner-hold")
            });

    assert(rejected.sequence > 0);
    assert(
        !store.readiness(
            "generation-0001").
            promotable());

    const auto approved =
        store.record_promotion_decision(
            PromotionDecision{
                .generation_id =
                    "generation-0001",
                .actor =
                    "owner-policy-boundary",
                .approved = true,
                .reason =
                    "evaluation evidence accepted",
                .evidence_hash =
                    sha256_hex("owner-approval")
            });

    assert(approved.sequence > rejected.sequence);

    readiness =
        store.readiness("generation-0001");
    assert(readiness.externally_approved);
    assert(readiness.promotable());

    const auto verification =
        store.verify();
    assert(verification.valid);
    assert(verification.generations == 2);

    bool missing_parent_rejected = false;
    try {
        (void)store.record_candidate(
            GenerationCandidate{
                .generation_id =
                    "generation-bad-parent",
                .parent_generation_id =
                    "generation-does-not-exist",
                .source_tree_hash =
                    sha256_hex("x"),
                .model_manifest_hash =
                    sha256_hex("y"),
                .config_hash =
                    sha256_hex("z"),
                .rationale = "invalid"
            });
    } catch (const std::out_of_range&) {
        missing_parent_rejected = true;
    }
    assert(missing_parent_rejected);

    bool invalid_hash_rejected = false;
    try {
        (void)store.record_candidate(
            GenerationCandidate{
                .generation_id =
                    "generation-bad-hash",
                .parent_generation_id = "",
                .source_tree_hash = "not-a-hash",
                .model_manifest_hash =
                    sha256_hex("m"),
                .config_hash =
                    sha256_hex("c"),
                .rationale = "invalid"
            });
    } catch (const std::invalid_argument&) {
        invalid_hash_rejected = true;
    }
    assert(invalid_hash_rejected);

    // An external approval cannot compensate for missing positive evaluation.
    (void)store.record_candidate(
        GenerationCandidate{
            .generation_id = "generation-0002",
            .parent_generation_id = "generation-0001",
            .source_tree_hash =
                sha256_hex("g2-source"),
            .model_manifest_hash =
                sha256_hex("g2-model"),
            .config_hash =
                sha256_hex("g2-config"),
            .rationale = "unevaluated candidate"
        });

    (void)store.record_promotion_decision(
        PromotionDecision{
            .generation_id = "generation-0002",
            .actor = "owner-policy-boundary",
            .approved = true,
            .reason =
                "approval recorded before eval for test",
            .evidence_hash =
                sha256_hex("premature-approval")
        });

    assert(
        !store.readiness(
            "generation-0002").
            promotable());

    // Candidate, evaluation, and promotion history are immutable at the DB boundary.
    sqlite3* raw = nullptr;
    assert(sqlite3_open(db.string().c_str(), &raw) == SQLITE_OK);
    char* error = nullptr;
    const int generation_update = sqlite3_exec(
        raw,
        "UPDATE generations SET rationale='tampered' "
        "WHERE generation_id='generation-0000';",
        nullptr, nullptr, &error);
    if (error != nullptr) { sqlite3_free(error); error = nullptr; }
    assert(generation_update == SQLITE_CONSTRAINT);

    const int evaluation_delete = sqlite3_exec(
        raw,
        "DELETE FROM generation_evaluations WHERE generation_id='generation-0001';",
        nullptr, nullptr, &error);
    if (error != nullptr) { sqlite3_free(error); error = nullptr; }
    assert(evaluation_delete == SQLITE_CONSTRAINT);

    const int promotion_update = sqlite3_exec(
        raw,
        "UPDATE promotion_decisions SET approved=0 "
        "WHERE generation_id='generation-0001';",
        nullptr, nullptr, &error);
    if (error != nullptr) { sqlite3_free(error); error = nullptr; }
    assert(promotion_update == SQLITE_CONSTRAINT);
    sqlite3_close(raw);

    std::filesystem::remove(db);
    return 0;
}
