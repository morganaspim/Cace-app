/* Minimal declaration-only SQLite C API shim for the Merlin OCI test profile.
 * The runner has the SQLite runtime library but not development headers.
 * This file declares only the stable ABI functions used by the pinned tests.
 * It contains no SQLite implementation; linking uses the runner's system
 * libsqlite3.so.0. It is test infrastructure, not a production SDK header.
 */
#ifndef MERLIN_TEST_SQLITE3_H
#define MERLIN_TEST_SQLITE3_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct sqlite3 sqlite3;
typedef struct sqlite3_stmt sqlite3_stmt;
typedef long long sqlite3_int64;
typedef unsigned long long sqlite3_uint64;
typedef void (*sqlite3_destructor_type)(void *);

#define SQLITE_OK 0
#define SQLITE_ERROR 1
#define SQLITE_INTERNAL 2
#define SQLITE_PERM 3
#define SQLITE_ABORT 4
#define SQLITE_BUSY 5
#define SQLITE_LOCKED 6
#define SQLITE_NOMEM 7
#define SQLITE_READONLY 8
#define SQLITE_INTERRUPT 9
#define SQLITE_IOERR 10
#define SQLITE_CORRUPT 11
#define SQLITE_NOTFOUND 12
#define SQLITE_FULL 13
#define SQLITE_CANTOPEN 14
#define SQLITE_PROTOCOL 15
#define SQLITE_EMPTY 16
#define SQLITE_SCHEMA 17
#define SQLITE_TOOBIG 18
#define SQLITE_CONSTRAINT 19
#define SQLITE_MISMATCH 20
#define SQLITE_MISUSE 21
#define SQLITE_NOLFS 22
#define SQLITE_AUTH 23
#define SQLITE_FORMAT 24
#define SQLITE_RANGE 25
#define SQLITE_NOTADB 26
#define SQLITE_NOTICE 27
#define SQLITE_WARNING 28
#define SQLITE_ROW 100
#define SQLITE_DONE 101

#define SQLITE_TRANSIENT ((sqlite3_destructor_type)-1)

int sqlite3_open(const char *filename, sqlite3 **database);
int sqlite3_close(sqlite3 *database);
int sqlite3_exec(sqlite3 *database, const char *sql,
                 int (*callback)(void *, int, char **, char **),
                 void *callback_arg, char **error_message);
void sqlite3_free(void *memory);
const char *sqlite3_errmsg(sqlite3 *database);
int sqlite3_prepare_v2(sqlite3 *database, const char *sql, int byte_count,
                       sqlite3_stmt **statement, const char **tail);
int sqlite3_step(sqlite3_stmt *statement);
int sqlite3_finalize(sqlite3_stmt *statement);
int sqlite3_bind_text(sqlite3_stmt *statement, int index, const char *value,
                      int byte_count, sqlite3_destructor_type destructor);
int sqlite3_bind_int(sqlite3_stmt *statement, int index, int value);
int sqlite3_bind_int64(sqlite3_stmt *statement, int index, sqlite3_int64 value);
int sqlite3_bind_double(sqlite3_stmt *statement, int index, double value);
int sqlite3_column_int(sqlite3_stmt *statement, int column);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt *statement, int column);
double sqlite3_column_double(sqlite3_stmt *statement, int column);
const unsigned char *sqlite3_column_text(sqlite3_stmt *statement, int column);
sqlite3_int64 sqlite3_last_insert_rowid(sqlite3 *database);

#ifdef __cplusplus
}
#endif

#endif
