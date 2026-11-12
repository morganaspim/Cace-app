#pragma once

#include "expert_robot/cognition/interoception.hpp"
#include "expert_robot/cognition/neuromodulation.hpp"

#include <array>
#include <cstddef>
#include <string_view>

namespace expert_robot::cognition {

/**
 * Stable executive temperament.
 *
 * Personality is deliberately separated from transient interoception and
 * neuromodulation. Profiles are immutable inside PersonalityExecutive; changing
 * a profile requires constructing/promoting a new executive configuration.
 */
struct PersonalityProfile {
    double openness{0.90};
    double conscientiousness{0.98};
    double persistence{0.90};
    double skepticism{0.98};
    double novelty_seeking{0.80};
    double risk_tolerance{0.55};
    double abstraction_bias{0.70};
    double compression_drive{0.85};
};

/**
 * Objective route-level logical assessment.
 *
 * These fields are expected to come from theorem/proof/search/benchmark
 * machinery rather than language-model self-report.
 */
struct LogicalAssessment {
    double evidence_strength{0.0};
    double expected_success{0.0};
    double expected_information_gain{0.0};
    double contradiction_risk{0.0};

    double decomposition_value{0.0};
    double counterexample_value{0.0};
    double abstraction_value{0.0};
    double compression_value{0.0};
    double representation_switch_value{0.0};

    double current_route_progress{0.0};
    double branch_cost{0.0};
};

enum class CognitiveAction : std::size_t {
    ContinueCurrentRoute = 0,
    ExploreNovelRoute,
    DecomposeProblem,
    SeekCounterexample,
    AbstractGeneralize,
    CompressSimplify,
    SwitchRepresentation,
    IntensifyVerification,
    ConserveCompute,
    Count
};

struct ExecutiveDecision {
    CognitiveAction action{CognitiveAction::ContinueCurrentRoute};

    double continue_score{0.0};
    double explore_score{0.0};
    double decompose_score{0.0};
    double counterexample_score{0.0};
    double abstract_score{0.0};
    double compress_score{0.0};
    double switch_score{0.0};
    double verification_score{0.0};
    double conserve_score{0.0};
    double abandon_pressure{0.0};

    bool breakthrough_mode{false};

    // Hard invariants: personality/emotion may alter search, never truth/authority.
    double verification_rigor_multiplier{1.0};
    double authority_delta{0.0};
};

void validate_personality(const PersonalityProfile& profile);
void validate_logical_assessment(const LogicalAssessment& assessment);

[[nodiscard]] PersonalityProfile math_researcher_personality();
[[nodiscard]] std::string_view cognitive_action_name(CognitiveAction action);

/**
 * Deterministic executive that combines:
 *   personality (stable)
 * + logic assessment (task/route evidence)
 * + interoceptive state (internal measurements)
 * + neuromodulator-derived biases (transient control)
 *
 * It chooses a search action only. It cannot change theorem status, proof
 * qualification, permissions, or generation promotion.
 */
class PersonalityExecutive {
public:
    explicit PersonalityExecutive(PersonalityProfile profile = math_researcher_personality());

    [[nodiscard]] const PersonalityProfile& profile() const noexcept;

    [[nodiscard]] ExecutiveDecision decide(
        const LogicalAssessment& logic,
        const InteroceptiveState& interoception,
        const ExecutiveBias& affect) const;

private:
    PersonalityProfile profile_;
};

} // namespace expert_robot::cognition
