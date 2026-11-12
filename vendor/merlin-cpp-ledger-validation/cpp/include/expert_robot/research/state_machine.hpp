#pragma once

#include "expert_robot/cognition/personality.hpp"

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace expert_robot::research {

enum class ResearchPhase {
    Intake,
    RetrieveKnown,
    DirectProof,
    Imagine,
    Decompose,
    VerifyCandidate,
    RetryParent,
    Consolidate,
    Complete,
    Exhausted,
};

enum class ResearchAction {
    Retrieve,
    AttemptDirectProof,
    RunImagination,
    RunLemmaFactory,
    VerifyCandidate,
    RetryParentProof,
    ConsolidateVerifiedKnowledge,
    StopComplete,
    StopExhausted,
};

struct ResearchBudget {
    std::size_t max_cycles{32};
    std::size_t max_model_calls{64};
    std::size_t max_proof_attempts{128};
    std::size_t max_generated_ideas{64};
    std::size_t max_generated_lemmas{64};
};

struct ResearchUsage {
    std::size_t cycles{0};
    std::size_t model_calls{0};
    std::size_t proof_attempts{0};
    std::size_t generated_ideas{0};
    std::size_t generated_lemmas{0};
};

struct ResearchObservation {
    bool retrieval_complete{false};

    bool lean_verified{false};
    bool direct_proof_failed{false};

    bool imagination_complete{false};
    std::size_t shortlisted_candidates{0};

    bool decomposition_complete{false};
    std::size_t proven_child_lemmas{0};

    std::size_t verified_candidate_lemmas{0};
    bool candidate_verification_failed{false};
    bool parent_retry_failed{false};

    double resource_pressure{0.0};

    cognition::CognitiveAction cognitive_action{
        cognition::CognitiveAction::ContinueCurrentRoute};

    ResearchUsage usage_delta;
};

struct ResearchTransition {
    ResearchPhase from{ResearchPhase::Intake};
    ResearchPhase to{ResearchPhase::Intake};
    ResearchAction action{ResearchAction::Retrieve};
    std::string reason;
};

struct ResearchState {
    ResearchPhase phase{ResearchPhase::Intake};
    ResearchUsage usage;
    bool any_lean_verified{false};
    bool completed{false};
    bool exhausted{false};
    std::vector<ResearchTransition> history;
};

void validate_research_budget(const ResearchBudget& budget);
void validate_research_observation(const ResearchObservation& observation);

[[nodiscard]] std::string_view research_phase_name(
    ResearchPhase phase);

[[nodiscard]] std::string_view research_action_name(
    ResearchAction action);

class ResearchStateMachine {
public:
    explicit ResearchStateMachine(
        ResearchBudget budget = {});

    [[nodiscard]] const ResearchState& state() const noexcept;
    [[nodiscard]] const ResearchBudget& budget() const noexcept;

    [[nodiscard]] ResearchTransition step(
        const ResearchObservation& observation);

    void reset();

private:
    [[nodiscard]] bool budget_exhausted() const noexcept;

    [[nodiscard]] ResearchTransition transition(
        ResearchPhase to,
        ResearchAction action,
        std::string reason);

    ResearchBudget budget_;
    ResearchState state_;
};

} // namespace expert_robot::research
