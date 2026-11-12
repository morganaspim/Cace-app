#pragma once

#include <cstddef>

namespace expert_robot::cognition {

struct CognitiveSignals {
    double verified_progress{0.0};
    double reward_prediction_error{0.0};
    double surprise{0.0};
    double uncertainty{0.0};
    double novelty{0.0};
    double attention_demand{0.0};
    double stagnation{0.0};
    double route_repetition{0.0};
    double resource_pressure{0.0};
    double goal_persistence{0.5};
};

struct NeuromodulatorState {
    double dopamine_like{0.20};
    double norepinephrine_like{0.20};
    double acetylcholine_like{0.20};
    double serotonin_like{0.20};
    std::size_t step{0};
};

struct NeuromodulationConfig {
    double smoothing{0.25};

    double dopamine_baseline{0.20};
    double norepinephrine_baseline{0.20};
    double acetylcholine_baseline{0.20};
    double serotonin_baseline{0.20};

    double breakthrough_stagnation_threshold{0.65};
    double breakthrough_switch_threshold{0.60};
};

struct ExecutiveBias {
    double exploration_drive{0.0};
    double persistence_drive{0.0};
    double attention_allocation{0.0};
    double strategy_switch_pressure{0.0};
    double compute_conservation{0.0};

    bool breakthrough_mode{false};

    double verification_rigor_multiplier{1.0};
    double authority_delta{0.0};
};

void validate_signals(const CognitiveSignals& signals);
void validate_config(const NeuromodulationConfig& config);

class SoftwareNeuromodulators {
public:
    explicit SoftwareNeuromodulators(
        NeuromodulationConfig config = {},
        NeuromodulatorState initial = {});

    [[nodiscard]] const NeuromodulatorState& state() const noexcept;
    [[nodiscard]] const NeuromodulationConfig& config() const noexcept;

    [[nodiscard]] ExecutiveBias update(const CognitiveSignals& signals);

    void reset(NeuromodulatorState state = {});

private:
    NeuromodulationConfig config_;
    NeuromodulatorState state_;
};

} // namespace expert_robot::cognition
