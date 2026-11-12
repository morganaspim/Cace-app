#pragma once

#include "expert_robot/cognition/neuromodulation.hpp"

#include <cstddef>

namespace expert_robot::cognition {

/**
 * Observable internal telemetry. Unless noted otherwise, normalized fields are
 * in [0,1]. These values come from runtime/proof/search instrumentation, not
 * language-model self-report.
 */
struct InteroceptiveSensors {
    // Machine/resource state.
    double cpu_load{0.0};
    double gpu_load{0.0};
    double ram_pressure{0.0};
    double vram_pressure{0.0};
    double context_utilization{0.0};
    double work_queue_pressure{0.0};

    // Mathematical/search state.
    double recent_proof_success_rate{0.0};
    double verified_progress{0.0};
    double expected_verified_progress{0.0};
    double theorem_novelty{0.0};
    double theorem_graph_coverage{0.0};
    double route_repetition{0.0};
    double uncertainty{0.0};
    double contradiction_rate{0.0};

    // Discrete stagnation indicators.
    std::size_t consecutive_failures{0};
    std::size_t attempts_since_verified_progress{0};
    double seconds_since_verified_progress{0.0};

    // Task priority supplied by the executive layer.
    double goal_persistence{0.5};
};

struct InteroceptionConfig {
    double smoothing{0.20};

    // Homeostatic resource set-points. Pressure rises primarily above these.
    double cpu_setpoint{0.70};
    double gpu_setpoint{0.80};
    double ram_setpoint{0.75};
    double vram_setpoint{0.80};
    double context_setpoint{0.75};
    double queue_setpoint{0.70};

    // Stagnation horizons.
    std::size_t failure_horizon{8};
    std::size_t attempt_horizon{12};
    double time_horizon_seconds{120.0};

    // Relative contribution to aggregate resource pressure.
    double cpu_weight{0.10};
    double gpu_weight{0.15};
    double ram_weight{0.20};
    double vram_weight{0.20};
    double context_weight{0.25};
    double queue_weight{0.10};
};

struct InteroceptiveState {
    double resource_pressure{0.0};
    double cognitive_strain{0.0};
    double stagnation{0.0};
    double novelty{0.0};
    double surprise{0.0};
    double uncertainty{0.0};
    double attention_demand{0.0};
    double route_repetition{0.0};
    double reward_prediction_error{0.0};
    double verified_progress{0.0};
    double goal_persistence{0.5};

    // Running baselines used for change detection.
    double progress_baseline{0.0};
    double success_rate_baseline{0.0};
    double resource_baseline{0.0};

    std::size_t step{0};
};

struct InteroceptiveReading {
    InteroceptiveState state;
    CognitiveSignals cognitive_signals;
};

void validate_interoceptive_sensors(const InteroceptiveSensors& sensors);
void validate_interoception_config(const InteroceptionConfig& config);

/**
 * Converts objective internal telemetry into bounded metacognitive signals.
 *
 * This is an artificial interoceptive controller, not a biological simulation.
 * It cannot alter authority, verification rules, or proof status.
 */
class ArtificialInteroception {
public:
    explicit ArtificialInteroception(
        InteroceptionConfig config = {},
        InteroceptiveState initial = {});

    [[nodiscard]] const InteroceptiveState& state() const noexcept;
    [[nodiscard]] const InteroceptionConfig& config() const noexcept;

    [[nodiscard]] InteroceptiveReading observe(const InteroceptiveSensors& sensors);

    void reset(InteroceptiveState state = {});

private:
    InteroceptionConfig config_;
    InteroceptiveState state_;
};

} // namespace expert_robot::cognition
