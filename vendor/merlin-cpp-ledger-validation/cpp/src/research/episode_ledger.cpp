#include "expert_robot/research/episode_ledger.hpp"

#include "expert_robot/sha256.hpp"

#include <sqlite3.h>

#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace expert_robot::research {
namespace {

constexpr int kSchemaVersion = 1;
constexpr std::size_t kMaxPayloadBytes = 1024U * 1024U;

void check(
    int code,
    sqlite3* db,
    const char* context) {
    if (code != SQLITE_OK &&
        code != SQLITE_DONE &&
        code != SQLITE_ROW) {
        throw std::runtime_error(
            std::string(context) + ": " +
            (db ? sqlite3_errmsg(db) : "sqlite error"));
    }
}

void exec_sql(
    sqlite3* db,
    const char* sql) {
    char* error = nullptr;
    const int rc =
        sqlite3_exec(
            db,
            sql,
            nullptr,
            nullptr,
            &error);
    if (rc != SQLITE_OK) {
        const std::string message =
            error ? error : "sqlite exec failed";
        sqlite3_free(error);
        throw std::runtime_error(message);
    }
}

class Statement {
public:
    Statement(sqlite3* db, const char* sql)
        : db_(db) {
        check(
            sqlite3_prepare_v2(
                db_, sql, -1, &stmt_, nullptr),
            db_,
            "prepare research episode statement");
    }

    ~Statement() {
        if (stmt_) sqlite3_finalize(stmt_);
    }

    sqlite3_stmt* get() const noexcept {
        return stmt_;
    }

private:
    sqlite3* db_{nullptr};
    sqlite3_stmt* stmt_{nullptr};
};

void bind_text(
    sqlite3* db,
    sqlite3_stmt* stmt,
    int index,
    std::string_view value) {
    check(
        sqlite3_bind_text(
            stmt,
            index,
            value.data(),
            static_cast<int>(value.size()),
            SQLITE_TRANSIENT),
        db,
        "bind research episode text");
}

std::string text_column(
    sqlite3_stmt* stmt,
    int index) {
    const auto* raw =
        reinterpret_cast<const char*>(
            sqlite3_column_text(stmt, index));
    return raw ? std::string(raw) : std::string{};
}

std::string event_hash_material(
    std::string_view episode_id,
    long long sequence,
    std::string_view event_type,
    std::string_view payload_sha256,
    std::string_view previous_event_hash) {
    std::ostringstream out;
    out
        << "episode=" << episode_id << "\n"
        << "sequence=" << sequence << "\n"
        << "type=" << event_type << "\n"
        << "payload_sha256=" << payload_sha256 << "\n"
        << "previous_event_hash=" << previous_event_hash << "\n";
    return out.str();
}

EpisodeEvent row_to_event(
    sqlite3_stmt* stmt) {
    return EpisodeEvent{
        .episode_id = text_column(stmt, 0),
        .sequence = sqlite3_column_int64(stmt, 1),
        .event_type = text_column(stmt, 2),
        .payload = text_column(stmt, 3),
        .payload_sha256 = text_column(stmt, 4),
        .previous_event_hash = text_column(stmt, 5),
        .event_hash = text_column(stmt, 6),
    };
}

} // namespace

ResearchEpisodeLedger::ResearchEpisodeLedger(
    std::filesystem::path path)
    : path_(std::move(path)) {
    if (!path_.parent_path().empty()) {
        std::filesystem::create_directories(
            path_.parent_path());
    }

    const int rc =
        sqlite3_open(
            path_.string().c_str(),
            &db_);
    if (rc != SQLITE_OK) {
        const std::string message =
            db_ ? sqlite3_errmsg(db_) : "sqlite open failed";
        if (db_) sqlite3_close(db_);
        db_ = nullptr;
        throw std::runtime_error(message);
    }

    exec_sql(db_, "PRAGMA foreign_keys = ON;");
    initialize();
}

ResearchEpisodeLedger::~ResearchEpisodeLedger() {
    if (db_) sqlite3_close(db_);
}

void ResearchEpisodeLedger::initialize() {
    exec_sql(
        db_,
        R"SQL(
        CREATE TABLE IF NOT EXISTS research_episode_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS research_episode_events (
            episode_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            previous_event_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(episode_id, sequence),
            UNIQUE(event_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_research_episode
            ON research_episode_events(episode_id, sequence);

        CREATE TRIGGER IF NOT EXISTS research_episode_events_no_update
        BEFORE UPDATE ON research_episode_events
        BEGIN
            SELECT RAISE(ABORT, 'append-only research episode ledger');
        END;

        CREATE TRIGGER IF NOT EXISTS research_episode_events_no_delete
        BEFORE DELETE ON research_episode_events
        BEGIN
            SELECT RAISE(ABORT, 'append-only research episode ledger');
        END;
        )SQL");

    Statement query(
        db_,
        "SELECT value FROM research_episode_metadata "
        "WHERE key='schema_version';");

    const int rc = sqlite3_step(query.get());
    check(rc, db_, "read research episode schema");

    if (rc == SQLITE_DONE) {
        Statement insert(
            db_,
            "INSERT INTO research_episode_metadata(key,value) "
            "VALUES('schema_version','1');");
        check(
            sqlite3_step(insert.get()),
            db_,
            "insert research episode schema");
    } else {
        const auto* raw =
            reinterpret_cast<const char*>(
                sqlite3_column_text(query.get(), 0));
        if (!raw ||
            std::string(raw) !=
                std::to_string(kSchemaVersion)) {
            throw std::runtime_error(
                "unsupported research episode schema");
        }
    }
}

EpisodeEvent ResearchEpisodeLedger::append(
    std::string_view episode_id,
    std::string_view event_type,
    std::string_view payload) {
    if (episode_id.empty() ||
        event_type.empty()) {
        throw std::invalid_argument(
            "episode_id and event_type must be non-empty");
    }
    if (payload.size() > kMaxPayloadBytes) {
        throw std::invalid_argument(
            "research episode payload exceeds size limit");
    }

    exec_sql(db_, "BEGIN IMMEDIATE;");

    try {
        long long sequence = 0;
        std::string previous_hash;

        {
            Statement last(
                db_,
                "SELECT sequence,event_hash "
                "FROM research_episode_events "
                "WHERE episode_id=? "
                "ORDER BY sequence DESC LIMIT 1;");
            bind_text(
                db_,
                last.get(),
                1,
                episode_id);

            const int rc =
                sqlite3_step(last.get());
            check(
                rc,
                db_,
                "read previous episode event");

            if (rc == SQLITE_ROW) {
                sequence =
                    sqlite3_column_int64(
                        last.get(),
                        0) + 1;
                previous_hash =
                    text_column(
                        last.get(),
                        1);
            }
        }

        const std::string payload_hash =
            sha256_hex(payload);

        const std::string event_hash =
            sha256_hex(
                event_hash_material(
                    episode_id,
                    sequence,
                    event_type,
                    payload_hash,
                    previous_hash));

        Statement insert(
            db_,
            R"SQL(
            INSERT INTO research_episode_events(
                episode_id,sequence,event_type,payload,
                payload_sha256,previous_event_hash,event_hash
            ) VALUES (?,?,?,?,?,?,?);
            )SQL");

        bind_text(db_, insert.get(), 1, episode_id);
        check(
            sqlite3_bind_int64(
                insert.get(),
                2,
                sequence),
            db_,
            "bind episode sequence");
        bind_text(db_, insert.get(), 3, event_type);
        bind_text(db_, insert.get(), 4, payload);
        bind_text(db_, insert.get(), 5, payload_hash);
        bind_text(db_, insert.get(), 6, previous_hash);
        bind_text(db_, insert.get(), 7, event_hash);

        check(
            sqlite3_step(insert.get()),
            db_,
            "insert research episode event");

        exec_sql(db_, "COMMIT;");

        return EpisodeEvent{
            .episode_id = std::string(episode_id),
            .sequence = sequence,
            .event_type = std::string(event_type),
            .payload = std::string(payload),
            .payload_sha256 = payload_hash,
            .previous_event_hash = previous_hash,
            .event_hash = event_hash,
        };
    } catch (...) {
        exec_sql(db_, "ROLLBACK;");
        throw;
    }
}

EpisodeEvent ResearchEpisodeLedger::append_transition(
    std::string_view episode_id,
    const ResearchTransition& t,
    const ResearchState& state) {
    std::ostringstream payload;
    payload
        << "from=" << research_phase_name(t.from) << "\n"
        << "to=" << research_phase_name(t.to) << "\n"
        << "action=" << research_action_name(t.action) << "\n"
        << "reason=" << t.reason << "\n"
        << "cycles=" << state.usage.cycles << "\n"
        << "model_calls=" << state.usage.model_calls << "\n"
        << "proof_attempts=" << state.usage.proof_attempts << "\n"
        << "generated_ideas=" << state.usage.generated_ideas << "\n"
        << "generated_lemmas=" << state.usage.generated_lemmas << "\n"
        << "any_lean_verified="
        << (state.any_lean_verified ? "true" : "false")
        << "\n";

    return append(
        episode_id,
        "research_transition",
        payload.str());
}

std::vector<EpisodeEvent>
ResearchEpisodeLedger::events(
    std::string_view episode_id) const {
    if (episode_id.empty()) {
        throw std::invalid_argument(
            "episode_id must be non-empty");
    }

    Statement stmt(
        db_,
        "SELECT episode_id,sequence,event_type,payload,"
        "payload_sha256,previous_event_hash,event_hash "
        "FROM research_episode_events "
        "WHERE episode_id=? ORDER BY sequence;");

    bind_text(
        db_,
        stmt.get(),
        1,
        episode_id);

    std::vector<EpisodeEvent> result;

    while (true) {
        const int rc = sqlite3_step(stmt.get());
        check(rc, db_, "read research episode events");
        if (rc == SQLITE_DONE) break;
        result.push_back(
            row_to_event(stmt.get()));
    }

    return result;
}

EpisodeVerification
ResearchEpisodeLedger::verify(
    std::string_view episode_id) const {
    const auto all = events(episode_id);

    EpisodeVerification result;
    result.event_count =
        static_cast<long long>(all.size());

    std::string expected_previous;

    for (std::size_t i = 0;
         i < all.size();
         ++i) {
        const auto& event = all[i];
        const long long expected_sequence =
            static_cast<long long>(i);

        if (event.sequence != expected_sequence) {
            result.valid = false;
            result.first_invalid_sequence =
                event.sequence;
            result.reason =
                "non-contiguous event sequence";
            return result;
        }

        if (event.previous_event_hash !=
            expected_previous) {
            result.valid = false;
            result.first_invalid_sequence =
                event.sequence;
            result.reason =
                "previous-event hash mismatch";
            return result;
        }

        const std::string payload_hash =
            sha256_hex(event.payload);

        if (payload_hash !=
            event.payload_sha256) {
            result.valid = false;
            result.first_invalid_sequence =
                event.sequence;
            result.reason =
                "payload hash mismatch";
            return result;
        }

        const std::string recomputed =
            sha256_hex(
                event_hash_material(
                    event.episode_id,
                    event.sequence,
                    event.event_type,
                    event.payload_sha256,
                    event.previous_event_hash));

        if (recomputed !=
            event.event_hash) {
            result.valid = false;
            result.first_invalid_sequence =
                event.sequence;
            result.reason =
                "event hash mismatch";
            return result;
        }

        expected_previous =
            event.event_hash;
    }

    result.root_hash =
        expected_previous;
    return result;
}

} // namespace expert_robot::research
