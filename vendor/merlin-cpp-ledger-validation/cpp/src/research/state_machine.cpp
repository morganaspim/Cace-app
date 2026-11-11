#include "expert_robot/research/state_machine.hpp"

#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

namespace expert_robot::research {
namespace {

void checked_add(
    std::size_t& target,
    std::size_t delta) {
    if (delta >
        static_cast<std::size_t>(-1) - target) {
        throw std::overflow_error(
            "research usage counter overflow");
    }
    target += delta;
}

} // namespace

void validate_research_budget(
    const ResearchBudget& b) {
    if (b.max_cycles == 0U ||
        b.max_model_calls == 0U ||
        b.max_proof_attempts == 0U ||
        b.max_generated_ideas == 0U ||
        b.max_generated_lemmas == 0U) {
        throw std::invalid_argument(
            "research budgets must be positive");
    }
}

void validate_research_observation(
    const ResearchObservation& o) {
    if (!std::isfinite(o.resource_pressure) ||
        o.resource_pressure < 0.0 ||
        o.resource_pressure > 1.0) {
        throw std::invalid_argument(
            "research resource_pressure must be in [0,1]");
    }

    if (o.lean_verified &&
        (o.direct_proof_failed ||
         o.candidate_verification_failed ||
         o.parent_retry_failed)) {
        throw std::invalid_argument(
            "Lean verification success conflicts with failure flags");
    }
}

std::string_view research_phase_name(
    ResearchPhase phase) {
    switch (phase) {
        case ResearchPhase::Intake: return "intake";
        case ResearchPhase::RetrieveKnown: return "retrieve_known";
        case ResearchPhase::DirectProof: return "direct_proof";
        case ResearchPhase::Imagine: return "imagine";
        case ResearchPhase::Decompose: return "decompose";
        case ResearchPhase::VerifyCandidate: return "verify_candidate";
        case ResearchPhase::RetryParent: return "retry_parent";
        case ResearchPhase::Consolidate: return "consolidate";
        case ResearchPhase::Complete: return "complete";
        case ResearchPhase::Exhausted: return "exhausted";
    }
    return "unknown";
}

std::string_view research_action_name(
    ResearchAction action) {
    switch (action) {
        case ResearchAction::Retrieve: return "retrieve";
        case ResearchAction::AttemptDirectProof: return "attempt_direct_proof";
        case ResearchAction::RunImagination: return "run_imagination";
        case ResearchAction::RunLemmaFactory: return "run_lemma_factory";
        case ResearchAction::VerifyCandidate: return "verify_candidate";
        case ResearchAction::RetryParentProof: return "retry_parent_proof";
        case ResearchAction::ConsolidateVerifiedKnowledge: return "consolidate_verified_knowledge";
        case ResearchAction::StopComplete: return "stop_complete";
        case ResearchAction::StopExhausted: return "stop_exhausted";
    }
    return "unknown";
}

ResearchStateMachine::ResearchStateMachine(
    ResearchBudget budget)
    : budget_(budget) {
    validate_research_budget(budget_);
}

const ResearchState&
ResearchStateMachine::state() const noexcept {
    return state_;
}

const ResearchBudget&
ResearchStateMachine::budget() const noexcept {
    return budget_;
}

void ResearchStateMachine::reset() {
    state_ = ResearchState{};
}

bool ResearchStateMachine::budget_exhausted() const noexcept {
    return
        state_.usage.cycles >= budget_.max_cycles ||
        state_.usage.model_calls >= budget_.max_model_calls ||
        state_.usage.proof_attempts >= budget_.max_proof_attempts ||
        state_.usage.generated_ideas >= budget_.max_generated_ideas ||
        state_.usage.generated_lemmas >= budget_.max_generated_lemmas;
}

ResearchTransition ResearchStateMachine::transition(
    ResearchPhase to,
    ResearchAction action,
    std::string reason) {
    const ResearchTransition t{
        .from = state_.phase,
        .to = to,
        .action = action,
        .reason = std::move(reason),
    };

    state_.phase = to;
    state_.history.push_back(t);

    if (to == ResearchPhase::Complete) {
        state_.completed = true;
    }
    if (to == ResearchPhase::Exhausted) {
        state_.exhausted = true;
    }

    return t;
}

ResearchTransition ResearchStateMachine::step(
    const ResearchObservation& o) {
    validate_research_observation(o);

    if (state_.completed ||
        state_.exhausted) {
        throw std::logic_error(
            "research state machine cannot step after terminal state");
    }

    checked_add(
        state_.usage.cycles,
        1U);
    checked_add(
        state_.usage.model_calls,
        o.usage_delta.model_calls);
    checked_add(
        state_.usage.proof_attempts,
        o.usage_delta.proof_attempts);
    checked_add(
        state_.usage.generated_ideas,
        o.usage_delta.generated_ideas);
    checked_add(
        state_.usage.generated_lemmas,
        o.usage_delta.generated_lemmas);

    if (o.lean_verified) {
        state_.any_lean_verified = true;
        return transition(
            ResearchPhase::Consolidate,
            ResearchAction::ConsolidateVerifiedKnowledge,
            "Lean accepted the target; consolidate verified knowledge");
    }

    if (state_.phase == ResearchPhase::Consolidate &&
        state_.any_lean_verified) {
        return transition(
            ResearchPhase::Complete,
            ResearchAction::StopComplete,
            "verified target knowledge consolidated");
    }

    if (budget_exhausted()) {
        return transition(
            ResearchPhase::Exhausted,
            ResearchAction::StopExhausted,
            "research budget exhausted before Lean verification");
    }

    if (o.resource_pressure >= 0.95) {
        return transition(
            ResearchPhase::Exhausted,
            ResearchAction::StopExhausted,
            "resource pressure reached hard research cutoff");
    }

    switch (state_.phase) {
        case ResearchPhase::Intake:
            return transition(
                ResearchPhase::RetrieveKnown,
                ResearchAction::Retrieve,
                "begin with theorem/proof/idea memory retrieval");

        case ResearchPhase::RetrieveKnown:
            if (!o.retrieval_complete) {
                return transition(
                    ResearchPhase::RetrieveKnown,
                    ResearchAction::Retrieve,
                    "retrieval is not complete");
            }
            return transition(
                ResearchPhase::DirectProof,
                ResearchAction::AttemptDirectProof,
                "try the cheapest verified proof route before exploration");

        case ResearchPhase::DirectProof:
            if (!o.direct_proof_failed) {
                return transition(
                    ResearchPhase::DirectProof,
                    ResearchAction::AttemptDirectProof,
                    "direct proof search has not reported failure or Lean success");
            }

            switch (o.cognitive_action) {
                case cognition::CognitiveAction::DecomposeProblem:
                    return transition(
                        ResearchPhase::Decompose,
                        ResearchAction::RunLemmaFactory,
                        "cognition selected decomposition after direct proof failure");

                case cognition::CognitiveAction::SeekCounterexample:
                case cognition::CognitiveAction::ExploreNovelRoute:
                case cognition::CognitiveAction::AbstractGeneralize:
                case cognition::CognitiveAction::SwitchRepresentation:
                case cognition::CognitiveAction::CompressSimplify:
                    return transition(
                        ResearchPhase::Imagine,
                        ResearchAction::RunImagination,
                        "cognition selected exploratory route after direct proof failure");

                case cognition::CognitiveAction::IntensifyVerification:
                case cognition::CognitiveAction::ContinueCurrentRoute:
                    return transition(
                        ResearchPhase::DirectProof,
                        ResearchAction::AttemptDirectProof,
                        "cognition requests another bounded direct-proof attempt");

                case cognition::CognitiveAction::ConserveCompute:
                    return transition(
                        ResearchPhase::Decompose,
                        ResearchAction::RunLemmaFactory,
                        "prefer structured decomposition over broad exploration under compute pressure");

                case cognition::CognitiveAction::Count:
                    break;
            }
            throw std::logic_error(
                "unsupported cognitive action in direct proof phase");

        case ResearchPhase::Imagine:
            if (!o.imagination_complete) {
                return transition(
                    ResearchPhase::Imagine,
                    ResearchAction::RunImagination,
                    "imagination cycle is not complete");
            }

            if (o.shortlisted_candidates > 0U) {
                return transition(
                    ResearchPhase::VerifyCandidate,
                    ResearchAction::VerifyCandidate,
                    "skeptic-approved candidates are available");
            }

            return transition(
                ResearchPhase::Decompose,
                ResearchAction::RunLemmaFactory,
                "no imagination candidate survived; decompose the goal");

        case ResearchPhase::Decompose:
            if (!o.decomposition_complete) {
                return transition(
                    ResearchPhase::Decompose,
                    ResearchAction::RunLemmaFactory,
                    "recursive lemma decomposition is not complete");
            }

            if (o.proven_child_lemmas > 0U) {
                return transition(
                    ResearchPhase::RetryParent,
                    ResearchAction::RetryParentProof,
                    "Lean-proven child lemmas are available for parent retry");
            }

            return transition(
                ResearchPhase::Imagine,
                ResearchAction::RunImagination,
                "decomposition produced no proven child lemmas; broaden search");

        case ResearchPhase::VerifyCandidate:
            if (o.verified_candidate_lemmas > 0U) {
                return transition(
                    ResearchPhase::RetryParent,
                    ResearchAction::RetryParentProof,
                    "Lean-verified helper candidates are available for parent retry");
            }

            if (!o.candidate_verification_failed) {
                return transition(
                    ResearchPhase::VerifyCandidate,
                    ResearchAction::VerifyCandidate,
                    "candidate verification has not resolved");
            }

            return transition(
                ResearchPhase::Decompose,
                ResearchAction::RunLemmaFactory,
                "candidate helpers failed Lean verification; extract smaller obligations");

        case ResearchPhase::RetryParent:
            if (!o.parent_retry_failed) {
                return transition(
                    ResearchPhase::RetryParent,
                    ResearchAction::RetryParentProof,
                    "parent retry has not resolved");
            }

            return transition(
                ResearchPhase::Imagine,
                ResearchAction::RunImagination,
                "parent retry failed after proven children; search a new representation");

        case ResearchPhase::Consolidate:
            if (!state_.any_lean_verified) {
                throw std::logic_error(
                    "cannot consolidate without prior Lean verification");
            }
            return transition(
                ResearchPhase::Complete,
                ResearchAction::StopComplete,
                "verified knowledge consolidated");

        case ResearchPhase::Complete:
        case ResearchPhase::Exhausted:
            break;
    }

    throw std::logic_error(
        "unreachable research state");
}

} // namespace expert_robot::research
