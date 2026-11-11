#include "expert_robot/growth/generation_lineage.hpp"

#include "expert_robot/sha256.hpp"

#include <sqlite3.h>

#include <cmath>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace expert_robot::growth {
namespace {

constexpr int kSchemaVersion = 1;

void check_sql(
    int code,
    sqlite3* db,
    const char* context) {
    if (code != SQLITE_OK &&
        code != SQLITE_DONE &&
        code != SQLITE_ROW) {
        throw std::runtime_error(
            std::string(context) +
            ": " +
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
    Statement(
        sqlite3* db,
        const char* sql)
        : db_(db) {
        check_sql(
            sqlite3_prepare_v2(
                db_,
                sql,
                -1,
                &stmt_,
                nullptr),
            db_,
            "prepare lineage statement");
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
    const std::string& value) {
    check_sql(
        sqlite3_bind_text(
            stmt,
            index,
            value.c_str(),
            static_cast<int>(value.size()),
            SQLITE_TRANSIENT),
        db,
        "bind lineage text");
}

std::string column_text(
    sqlite3_stmt* stmt,
    int index) {
    const auto* raw =
        reinterpret_cast<const char*>(
            sqlite3_column_text(
                stmt,
                index));
    return raw ? std::string(raw) : std::string{};
}

void validate_hash(
    const std::string& value,
    const char* label) {
    if (value.size() != 64U) {
        throw std::invalid_argument(
            std::string(label) +
            " must be a 64-character SHA-256 hex string");
    }
    for (const unsigned char ch : value) {
        const bool digit =
            ch >= '0' && ch <= '9';
        const bool lower =
            ch >= 'a' && ch <= 'f';
        if (!digit && !lower) {
            throw std::invalid_argument(
                std::string(label) +
                " must be lowercase SHA-256 hex");
        }
    }
}

void validate_candidate(
    const GenerationCandidate& c) {
    if (c.generation_id.empty()) {
        throw std::invalid_argument(
            "generation_id must be non-empty");
    }
    validate_hash(
        c.source_tree_hash,
        "source_tree_hash");
    validate_hash(
        c.model_manifest_hash,
        "model_manifest_hash");
    validate_hash(
        c.config_hash,
        "config_hash");
}

std::string candidate_lineage_hash(
    const GenerationCandidate& c,
    std::string_view parent_lineage_hash) {
    std::ostringstream canonical;
    canonical
        << "generation_id=" << c.generation_id << "\n"
        << "parent_generation_id="
        << c.parent_generation_id << "\n"
        << "parent_lineage_hash="
        << parent_lineage_hash << "\n"
        << "source_tree_hash="
        << c.source_tree_hash << "\n"
        << "model_manifest_hash="
        << c.model_manifest_hash << "\n"
        << "config_hash="
        << c.config_hash << "\n"
        << "rationale="
        << c.rationale;
    return sha256_hex(
        canonical.str());
}

GenerationRecord generation_from_row(
    sqlite3_stmt* stmt) {
    return GenerationRecord{
        .candidate =
            GenerationCandidate{
                .generation_id =
                    column_text(stmt, 0),
                .parent_generation_id =
                    column_text(stmt, 1),
                .source_tree_hash =
                    column_text(stmt, 2),
                .model_manifest_hash =
                    column_text(stmt, 3),
                .config_hash =
                    column_text(stmt, 4),
                .rationale =
                    column_text(stmt, 5),
            },
        .parent_lineage_hash =
            column_text(stmt, 6),
        .lineage_hash =
            column_text(stmt, 7),
    };
}

} // namespace

GenerationLineageStore::GenerationLineageStore(
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

    exec_sql(
        db_,
        "PRAGMA foreign_keys = ON;");
    initialize();
}

GenerationLineageStore::~GenerationLineageStore() {
    if (db_) sqlite3_close(db_);
}

void GenerationLineageStore::initialize() {
    exec_sql(
        db_,
        R"SQL(
        CREATE TABLE IF NOT EXISTS generation_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS generations (
            generation_id TEXT PRIMARY KEY,
            parent_generation_id TEXT NOT NULL,
            source_tree_hash TEXT NOT NULL,
            model_manifest_hash TEXT NOT NULL,
            config_hash TEXT NOT NULL,
            rationale TEXT NOT NULL,
            parent_lineage_hash TEXT NOT NULL,
            lineage_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generation_evaluations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_id TEXT NOT NULL,
            evaluator TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            recommend_keep INTEGER NOT NULL,
            verification_ok INTEGER NOT NULL,
            efficiency_ok INTEGER NOT NULL,
            diversity_ok INTEGER NOT NULL,
            verified_rate_delta REAL NOT NULL,
            cost_per_verified_ratio REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(generation_id)
                REFERENCES generations(generation_id)
        );

        CREATE TABLE IF NOT EXISTS promotion_decisions (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            approved INTEGER NOT NULL,
            reason TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(generation_id)
                REFERENCES generations(generation_id)
        );

        CREATE TRIGGER IF NOT EXISTS generations_no_update
        BEFORE UPDATE ON generations
        BEGIN
            SELECT RAISE(ABORT, 'append-only generation lineage');
        END;
        CREATE TRIGGER IF NOT EXISTS generations_no_delete
        BEFORE DELETE ON generations
        BEGIN
            SELECT RAISE(ABORT, 'append-only generation lineage');
        END;

        CREATE TRIGGER IF NOT EXISTS generation_evaluations_no_update
        BEFORE UPDATE ON generation_evaluations
        BEGIN
            SELECT RAISE(ABORT, 'append-only generation evaluations');
        END;
        CREATE TRIGGER IF NOT EXISTS generation_evaluations_no_delete
        BEFORE DELETE ON generation_evaluations
        BEGIN
            SELECT RAISE(ABORT, 'append-only generation evaluations');
        END;

        CREATE TRIGGER IF NOT EXISTS promotion_decisions_no_update
        BEFORE UPDATE ON promotion_decisions
        BEGIN
            SELECT RAISE(ABORT, 'append-only promotion decisions');
        END;
        CREATE TRIGGER IF NOT EXISTS promotion_decisions_no_delete
        BEFORE DELETE ON promotion_decisions
        BEGIN
            SELECT RAISE(ABORT, 'append-only promotion decisions');
        END;
        )SQL");

    Statement select(
        db_,
        "SELECT value FROM generation_metadata "
        "WHERE key='schema_version';");

    const int rc =
        sqlite3_step(select.get());
    check_sql(
        rc,
        db_,
        "read lineage schema");

    if (rc == SQLITE_DONE) {
        Statement insert(
            db_,
            "INSERT INTO generation_metadata(key,value) "
            "VALUES('schema_version', ?);");
        check_sql(
            sqlite3_bind_text(
                insert.get(),
                1,
                "1",
                -1,
                SQLITE_STATIC),
            db_,
            "bind lineage schema");
        check_sql(
            sqlite3_step(insert.get()),
            db_,
            "insert lineage schema");
    } else {
        const auto value =
            column_text(select.get(), 0);
        if (value !=
            std::to_string(kSchemaVersion)) {
            throw std::runtime_error(
                "unsupported generation lineage schema");
        }
    }
}

GenerationRecord
GenerationLineageStore::record_candidate(
    GenerationCandidate candidate) {
    validate_candidate(candidate);

    std::string parent_hash;
    if (!candidate.parent_generation_id.empty()) {
        const auto parent =
            generation(
                candidate.parent_generation_id);
        parent_hash =
            parent.lineage_hash;
    }

    const std::string lineage_hash =
        candidate_lineage_hash(
            candidate,
            parent_hash);

    Statement insert(
        db_,
        R"SQL(
        INSERT INTO generations(
            generation_id,
            parent_generation_id,
            source_tree_hash,
            model_manifest_hash,
            config_hash,
            rationale,
            parent_lineage_hash,
            lineage_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        )SQL");

    bind_text(db_, insert.get(), 1, candidate.generation_id);
    bind_text(db_, insert.get(), 2, candidate.parent_generation_id);
    bind_text(db_, insert.get(), 3, candidate.source_tree_hash);
    bind_text(db_, insert.get(), 4, candidate.model_manifest_hash);
    bind_text(db_, insert.get(), 5, candidate.config_hash);
    bind_text(db_, insert.get(), 6, candidate.rationale);
    bind_text(db_, insert.get(), 7, parent_hash);
    bind_text(db_, insert.get(), 8, lineage_hash);

    check_sql(
        sqlite3_step(insert.get()),
        db_,
        "insert generation candidate");

    return GenerationRecord{
        .candidate = std::move(candidate),
        .parent_lineage_hash =
            std::move(parent_hash),
        .lineage_hash =
            lineage_hash,
    };
}

EvaluationRecord
GenerationLineageStore::record_evaluation(
    EvaluationRecord evaluation) {
    (void)generation(
        evaluation.generation_id);

    if (evaluation.evaluator.empty()) {
        throw std::invalid_argument(
            "evaluation evaluator must be non-empty");
    }
    validate_hash(
        evaluation.evidence_hash,
        "evaluation evidence_hash");

    if (!std::isfinite(
            evaluation.verified_rate_delta) ||
        !std::isfinite(
            evaluation.cost_per_verified_ratio) ||
        evaluation.cost_per_verified_ratio < 0.0) {
        throw std::invalid_argument(
            "evaluation metrics must be finite and cost ratio nonnegative");
    }

    Statement insert(
        db_,
        R"SQL(
        INSERT INTO generation_evaluations(
            generation_id,
            evaluator,
            evidence_hash,
            recommend_keep,
            verification_ok,
            efficiency_ok,
            diversity_ok,
            verified_rate_delta,
            cost_per_verified_ratio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        )SQL");

    bind_text(db_, insert.get(), 1, evaluation.generation_id);
    bind_text(db_, insert.get(), 2, evaluation.evaluator);
    bind_text(db_, insert.get(), 3, evaluation.evidence_hash);
    check_sql(
        sqlite3_bind_int(
            insert.get(),
            4,
            evaluation.recommend_keep ? 1 : 0),
        db_,
        "bind recommend_keep");
    check_sql(
        sqlite3_bind_int(
            insert.get(),
            5,
            evaluation.verification_ok ? 1 : 0),
        db_,
        "bind verification_ok");
    check_sql(
        sqlite3_bind_int(
            insert.get(),
            6,
            evaluation.efficiency_ok ? 1 : 0),
        db_,
        "bind efficiency_ok");
    check_sql(
        sqlite3_bind_int(
            insert.get(),
            7,
            evaluation.diversity_ok ? 1 : 0),
        db_,
        "bind diversity_ok");
    check_sql(
        sqlite3_bind_double(
            insert.get(),
            8,
            evaluation.verified_rate_delta),
        db_,
        "bind verified rate delta");
    check_sql(
        sqlite3_bind_double(
            insert.get(),
            9,
            evaluation.cost_per_verified_ratio),
        db_,
        "bind cost ratio");

    check_sql(
        sqlite3_step(insert.get()),
        db_,
        "insert generation evaluation");

    evaluation.sequence =
        sqlite3_last_insert_rowid(db_);
    return evaluation;
}

PromotionDecision
GenerationLineageStore::record_promotion_decision(
    PromotionDecision decision) {
    (void)generation(
        decision.generation_id);

    if (decision.actor.empty()) {
        throw std::invalid_argument(
            "promotion actor must be supplied by the external authority boundary");
    }
    if (decision.reason.empty()) {
        throw std::invalid_argument(
            "promotion reason must be non-empty");
    }
    validate_hash(
        decision.evidence_hash,
        "promotion evidence_hash");

    Statement insert(
        db_,
        R"SQL(
        INSERT INTO promotion_decisions(
            generation_id,
            actor,
            approved,
            reason,
            evidence_hash
        ) VALUES (?, ?, ?, ?, ?);
        )SQL");

    bind_text(db_, insert.get(), 1, decision.generation_id);
    bind_text(db_, insert.get(), 2, decision.actor);
    check_sql(
        sqlite3_bind_int(
            insert.get(),
            3,
            decision.approved ? 1 : 0),
        db_,
        "bind promotion approval");
    bind_text(db_, insert.get(), 4, decision.reason);
    bind_text(db_, insert.get(), 5, decision.evidence_hash);

    check_sql(
        sqlite3_step(insert.get()),
        db_,
        "insert promotion decision");

    decision.sequence =
        sqlite3_last_insert_rowid(db_);
    return decision;
}

GenerationRecord
GenerationLineageStore::generation(
    std::string_view generation_id) const {
    Statement query(
        db_,
        R"SQL(
        SELECT
            generation_id,
            parent_generation_id,
            source_tree_hash,
            model_manifest_hash,
            config_hash,
            rationale,
            parent_lineage_hash,
            lineage_hash
        FROM generations
        WHERE generation_id = ?;
        )SQL");

    bind_text(
        db_,
        query.get(),
        1,
        std::string(generation_id));

    const int rc =
        sqlite3_step(query.get());
    check_sql(
        rc,
        db_,
        "read generation");

    if (rc != SQLITE_ROW) {
        throw std::out_of_range(
            "unknown generation: " +
            std::string(generation_id));
    }

    return generation_from_row(
        query.get());
}

std::vector<GenerationRecord>
GenerationLineageStore::generations() const {
    Statement query(
        db_,
        R"SQL(
        SELECT
            generation_id,
            parent_generation_id,
            source_tree_hash,
            model_manifest_hash,
            config_hash,
            rationale,
            parent_lineage_hash,
            lineage_hash
        FROM generations
        ORDER BY created_at, rowid;
        )SQL");

    std::vector<GenerationRecord> result;
    while (true) {
        const int rc =
            sqlite3_step(query.get());
        check_sql(
            rc,
            db_,
            "list generations");
        if (rc == SQLITE_DONE) break;
        result.push_back(
            generation_from_row(
                query.get()));
    }
    return result;
}

std::vector<EvaluationRecord>
GenerationLineageStore::evaluations(
    std::string_view generation_id) const {
    Statement query(
        db_,
        R"SQL(
        SELECT
            sequence,
            generation_id,
            evaluator,
            evidence_hash,
            recommend_keep,
            verification_ok,
            efficiency_ok,
            diversity_ok,
            verified_rate_delta,
            cost_per_verified_ratio
        FROM generation_evaluations
        WHERE generation_id = ?
        ORDER BY sequence;
        )SQL");

    bind_text(
        db_,
        query.get(),
        1,
        std::string(generation_id));

    std::vector<EvaluationRecord> result;
    while (true) {
        const int rc =
            sqlite3_step(query.get());
        check_sql(
            rc,
            db_,
            "list evaluations");
        if (rc == SQLITE_DONE) break;

        result.push_back(
            EvaluationRecord{
                .sequence =
                    sqlite3_column_int64(
                        query.get(),
                        0),
                .generation_id =
                    column_text(
                        query.get(),
                        1),
                .evaluator =
                    column_text(
                        query.get(),
                        2),
                .evidence_hash =
                    column_text(
                        query.get(),
                        3),
                .recommend_keep =
                    sqlite3_column_int(
                        query.get(),
                        4) != 0,
                .verification_ok =
                    sqlite3_column_int(
                        query.get(),
                        5) != 0,
                .efficiency_ok =
                    sqlite3_column_int(
                        query.get(),
                        6) != 0,
                .diversity_ok =
                    sqlite3_column_int(
                        query.get(),
                        7) != 0,
                .verified_rate_delta =
                    sqlite3_column_double(
                        query.get(),
                        8),
                .cost_per_verified_ratio =
                    sqlite3_column_double(
                        query.get(),
                        9),
            });
    }
    return result;
}

std::vector<PromotionDecision>
GenerationLineageStore::promotion_decisions(
    std::string_view generation_id) const {
    Statement query(
        db_,
        R"SQL(
        SELECT
            sequence,
            generation_id,
            actor,
            approved,
            reason,
            evidence_hash
        FROM promotion_decisions
        WHERE generation_id = ?
        ORDER BY sequence;
        )SQL");

    bind_text(
        db_,
        query.get(),
        1,
        std::string(generation_id));

    std::vector<PromotionDecision> result;
    while (true) {
        const int rc =
            sqlite3_step(query.get());
        check_sql(
            rc,
            db_,
            "list promotion decisions");
        if (rc == SQLITE_DONE) break;

        result.push_back(
            PromotionDecision{
                .sequence =
                    sqlite3_column_int64(
                        query.get(),
                        0),
                .generation_id =
                    column_text(
                        query.get(),
                        1),
                .actor =
                    column_text(
                        query.get(),
                        2),
                .approved =
                    sqlite3_column_int(
                        query.get(),
                        3) != 0,
                .reason =
                    column_text(
                        query.get(),
                        4),
                .evidence_hash =
                    column_text(
                        query.get(),
                        5),
            });
    }
    return result;
}

PromotionReadiness
GenerationLineageStore::readiness(
    std::string_view generation_id) const {
    PromotionReadiness result;

    for (const auto& evaluation :
         evaluations(generation_id)) {
        if (evaluation.recommend_keep) {
            result.has_positive_evaluation =
                true;
            result.verification_ok =
                result.verification_ok ||
                evaluation.verification_ok;
            result.efficiency_ok =
                result.efficiency_ok ||
                evaluation.efficiency_ok;
            result.diversity_ok =
                result.diversity_ok ||
                evaluation.diversity_ok;
        }
    }

    for (const auto& decision :
         promotion_decisions(generation_id)) {
        if (decision.approved) {
            result.externally_approved =
                true;
        }
    }

    return result;
}

LineageVerification
GenerationLineageStore::verify() const {
    const auto records =
        generations();

    for (const auto& record : records) {
        std::string expected_parent_hash;

        if (!record.candidate.
                parent_generation_id.empty()) {
            try {
                const auto parent =
                    generation(
                        record.candidate.
                            parent_generation_id);
                expected_parent_hash =
                    parent.lineage_hash;
            } catch (...) {
                return {
                    .valid = false,
                    .generations =
                        static_cast<long long>(
                            records.size()),
                    .reason =
                        "parent generation missing",
                    .first_invalid_generation =
                        record.candidate.
                            generation_id,
                };
            }
        }

        if (expected_parent_hash !=
            record.parent_lineage_hash) {
            return {
                .valid = false,
                .generations =
                    static_cast<long long>(
                        records.size()),
                .reason =
                    "parent lineage hash mismatch",
                .first_invalid_generation =
                    record.candidate.
                        generation_id,
            };
        }

        const std::string expected =
            candidate_lineage_hash(
                record.candidate,
                expected_parent_hash);

        if (expected !=
            record.lineage_hash) {
            return {
                .valid = false,
                .generations =
                    static_cast<long long>(
                        records.size()),
                .reason =
                    "generation lineage hash mismatch",
                .first_invalid_generation =
                    record.candidate.
                        generation_id,
            };
        }
    }

    return {
        .valid = true,
        .generations =
            static_cast<long long>(
                records.size()),
        .reason = "",
        .first_invalid_generation = "",
    };
}

} // namespace expert_robot::growth
