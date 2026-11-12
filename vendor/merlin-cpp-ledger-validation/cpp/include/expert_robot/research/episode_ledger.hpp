#pragma once

#include "expert_robot/research/state_machine.hpp"

#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

struct sqlite3;

namespace expert_robot::research {

struct EpisodeEvent {
    std::string episode_id;
    long long sequence{0};
    std::string event_type;
    std::string payload;
    std::string payload_sha256;
    std::string previous_event_hash;
    std::string event_hash;
};

struct EpisodeVerification {
    bool valid{true};
    long long event_count{0};
    long long first_invalid_sequence{-1};
    std::string reason;
    std::string root_hash;
};

class ResearchEpisodeLedger {
public:
    explicit ResearchEpisodeLedger(
        std::filesystem::path path);
    ~ResearchEpisodeLedger();

    ResearchEpisodeLedger(
        const ResearchEpisodeLedger&) = delete;
    ResearchEpisodeLedger& operator=(
        const ResearchEpisodeLedger&) = delete;

    [[nodiscard]] EpisodeEvent append(
        std::string_view episode_id,
        std::string_view event_type,
        std::string_view payload);

    [[nodiscard]] EpisodeEvent append_transition(
        std::string_view episode_id,
        const ResearchTransition& transition,
        const ResearchState& state);

    [[nodiscard]] std::vector<EpisodeEvent> events(
        std::string_view episode_id) const;

    [[nodiscard]] EpisodeVerification verify(
        std::string_view episode_id) const;

private:
    void initialize();

    std::filesystem::path path_;
    sqlite3* db_{nullptr};
};

} // namespace expert_robot::research
