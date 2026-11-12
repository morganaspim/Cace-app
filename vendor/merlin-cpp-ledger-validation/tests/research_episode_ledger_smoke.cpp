#include "expert_robot/research/episode_ledger.hpp"
#include "expert_robot/research/state_machine.hpp"

#include <sqlite3.h>

#include <cassert>
#include <filesystem>
#include <string>

int main() {
    using namespace expert_robot::research;

    const auto db =
        std::filesystem::temp_directory_path() /
        "expert-robot-research-episode.sqlite3";
    std::filesystem::remove(db);

    ResearchEpisodeLedger ledger(db);
    ResearchStateMachine machine;

    const std::string episode =
        "episode-001";

    const auto intake_event =
        ledger.append(
            episode,
            "episode_started",
            "goal=prove target theorem");
    assert(intake_event.sequence == 0);
    assert(intake_event.previous_event_hash.empty());
    assert(!intake_event.event_hash.empty());

    auto transition =
        machine.step(
            ResearchObservation{});
    const auto transition_event =
        ledger.append_transition(
            episode,
            transition,
            machine.state());
    assert(transition_event.sequence == 1);
    assert(
        transition_event.previous_event_hash ==
        intake_event.event_hash);

    ResearchObservation retrieved;
    retrieved.retrieval_complete = true;
    transition =
        machine.step(retrieved);
    const auto direct_event =
        ledger.append_transition(
            episode,
            transition,
            machine.state());
    assert(direct_event.sequence == 2);

    const auto verified =
        ledger.verify(episode);
    assert(verified.valid);
    assert(verified.event_count == 3);
    assert(verified.first_invalid_sequence == -1);
    assert(
        verified.root_hash ==
        direct_event.event_hash);

    const auto events =
        ledger.events(episode);
    assert(events.size() == 3);
    assert(events[0].sequence == 0);
    assert(events[1].sequence == 1);
    assert(events[2].sequence == 2);

    // Separate episodes have separate chains.
    const auto other =
        ledger.append(
            "episode-002",
            "episode_started",
            "goal=another theorem");
    assert(other.sequence == 0);
    assert(other.previous_event_hash.empty());
    const auto other_verified =
        ledger.verify("episode-002");
    assert(other_verified.valid);
    assert(other_verified.event_count == 1);
    assert(other_verified.root_hash == other.event_hash);

    // Simulate an out-of-band edit of immutable history.
    sqlite3* raw = nullptr;
    assert(
        sqlite3_open(
            db.string().c_str(),
            &raw) == SQLITE_OK);

    char* error = nullptr;
    const int update_blocked =
        sqlite3_exec(
            raw,
            "UPDATE research_episode_events "
            "SET payload='tampered payload' "
            "WHERE episode_id='episode-001' "
            "AND sequence=1;",
            nullptr,
            nullptr,
            &error);
    if (error != nullptr) {
        sqlite3_free(error);
        error = nullptr;
    }
    assert(update_blocked == SQLITE_CONSTRAINT);

    const int delete_blocked =
        sqlite3_exec(
            raw,
            "DELETE FROM research_episode_events "
            "WHERE episode_id='episode-001' AND sequence=1;",
            nullptr,
            nullptr,
            &error);
    if (error != nullptr) {
        sqlite3_free(error);
        error = nullptr;
    }
    assert(delete_blocked == SQLITE_CONSTRAINT);

    // Even if an out-of-band actor removes the guard, the hash chain detects edits.
    assert(sqlite3_exec(
        raw,
        "DROP TRIGGER research_episode_events_no_update;",
        nullptr,
        nullptr,
        &error) == SQLITE_OK);
    if (error != nullptr) {
        sqlite3_free(error);
        error = nullptr;
    }
    const int rc =
        sqlite3_exec(
            raw,
            "UPDATE research_episode_events "
            "SET payload='tampered payload' "
            "WHERE episode_id='episode-001' "
            "AND sequence=1;",
            nullptr,
            nullptr,
            &error);
    if (error != nullptr) {
        sqlite3_free(error);
    }
    assert(rc == SQLITE_OK);
    sqlite3_close(raw);

    const auto tampered =
        ledger.verify(episode);
    assert(!tampered.valid);
    assert(tampered.first_invalid_sequence == 1);
    assert(tampered.reason == "payload hash mismatch");

    std::filesystem::remove(db);
    return 0;
}
