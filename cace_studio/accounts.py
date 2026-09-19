from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Any, Mapping
from uuid import uuid4


USER_TYPES = ("basic", "researcher", "enterprise")
LOCATION_SCOPES = ("none", "country", "region", "city", "custom")
MAX_PROTEIN_OBJECT_BYTES = 8 * 1024 * 1024
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _now() -> float:
    return time.time()


def _token(prefix: str, bytes_count: int = 32) -> str:
    return prefix + secrets.token_urlsafe(bytes_count)


def _hash_token(value: str) -> str:
    return sha256(str(value).encode("utf-8")).hexdigest()


def _clean(
    value: Any,
    *,
    field: str,
    max_chars: int,
    allow_empty: bool = False,
) -> str:
    text = str(value or "").strip()
    if not text and not allow_empty:
        raise ValueError(f"{field} is required")
    if len(text) > max_chars:
        raise ValueError(f"{field} exceeds {max_chars} characters")
    if any(ord(ch) < 32 and ch not in "\t\n" for ch in text):
        raise ValueError(f"{field} contains control characters")
    return text


@dataclass(frozen=True)
class LocalAccount:
    account_id: str
    display_name: str
    email_normalized: str
    user_type: str
    declared_location: str
    location_scope: str
    protein_library_enabled: bool
    local_ai_math_wallet_id: str
    created_at: float
    disabled_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StoredProtein:
    object_id: str
    account_id: str
    semantic_sha256: str
    source: str
    license_id: str
    attribution: str
    created_at: float
    object_json: str

    def to_dict(self, *, include_object: bool = True) -> dict[str, Any]:
        payload = {
            "object_id": self.object_id,
            "account_id": self.account_id,
            "semantic_sha256": self.semantic_sha256,
            "source": self.source,
            "license_id": self.license_id,
            "attribution": self.attribution,
            "created_at": self.created_at,
        }
        if include_object:
            payload["object"] = json.loads(self.object_json)
        return payload


class LocalAccountStore:
    """Local profile/protein state.

    This store never contains Monero or Math Coin private keys. The Math Coin
    value is an account-scoped wallet identity/capability handle only.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email_normalized TEXT NOT NULL DEFAULT '',
                    user_type TEXT NOT NULL,
                    declared_location TEXT NOT NULL DEFAULT '',
                    location_scope TEXT NOT NULL DEFAULT 'none',
                    protein_library_enabled INTEGER NOT NULL DEFAULT 0,
                    local_ai_math_wallet_id TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL,
                    disabled_at REAL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS accounts_email_unique
                ON accounts(email_normalized)
                WHERE email_normalized <> '';

                CREATE TABLE IF NOT EXISTS account_sessions (
                    session_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    revoked_at REAL
                );

                CREATE TABLE IF NOT EXISTS protein_objects (
                    object_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                    semantic_sha256 TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT '',
                    license_id TEXT NOT NULL DEFAULT '',
                    attribution TEXT NOT NULL DEFAULT '',
                    object_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(account_id, semantic_sha256)
                );

                CREATE TABLE IF NOT EXISTS account_audit_events (
                    event_id TEXT PRIMARY KEY,
                    account_id TEXT REFERENCES accounts(account_id) ON DELETE SET NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _row_to_account(row: sqlite3.Row) -> LocalAccount:
        return LocalAccount(
            account_id=str(row["account_id"]),
            display_name=str(row["display_name"]),
            email_normalized=str(row["email_normalized"]),
            user_type=str(row["user_type"]),
            declared_location=str(row["declared_location"]),
            location_scope=str(row["location_scope"]),
            protein_library_enabled=bool(row["protein_library_enabled"]),
            local_ai_math_wallet_id=str(row["local_ai_math_wallet_id"]),
            created_at=float(row["created_at"]),
            disabled_at=None if row["disabled_at"] is None else float(row["disabled_at"]),
        )

    def _audit(
        self,
        db: sqlite3.Connection,
        account_id: str | None,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        db.execute(
            """
            INSERT INTO account_audit_events(
                event_id, account_id, event_type, event_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                account_id,
                event_type,
                json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str),
                _now(),
            ),
        )

    def create_account(
        self,
        *,
        display_name: str,
        user_type: str = "basic",
        email: str = "",
        declared_location: str = "",
        location_scope: str = "none",
        protein_library_enabled: bool = False,
    ) -> LocalAccount:
        display_name = _clean(display_name, field="display_name", max_chars=120)
        user_type = str(user_type).strip().lower()
        if user_type not in USER_TYPES:
            raise ValueError(f"user_type must be one of {USER_TYPES}")
        location_scope = str(location_scope).strip().lower()
        if location_scope not in LOCATION_SCOPES:
            raise ValueError(f"location_scope must be one of {LOCATION_SCOPES}")
        declared_location = _clean(
            declared_location,
            field="declared_location",
            max_chars=240,
            allow_empty=True,
        )
        if location_scope == "none":
            declared_location = ""
        elif not declared_location:
            raise ValueError("declared_location is required for this location_scope")

        email_normalized = str(email or "").strip().casefold()
        if email_normalized and (
            len(email_normalized) > 320
            or _EMAIL_RE.fullmatch(email_normalized) is None
        ):
            raise ValueError("email is not valid")

        account_id = f"acct_{uuid4().hex}"
        wallet_id = _token("MATH-AI-", 18)
        created_at = _now()
        with self._connect() as db:
            try:
                db.execute(
                    """
                    INSERT INTO accounts(
                        account_id, display_name, email_normalized, user_type,
                        declared_location, location_scope, protein_library_enabled,
                        local_ai_math_wallet_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        display_name,
                        email_normalized,
                        user_type,
                        declared_location,
                        location_scope,
                        1 if protein_library_enabled else 0,
                        wallet_id,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if email_normalized:
                    raise ValueError("an account already uses this email") from exc
                raise
            self._audit(
                db,
                account_id,
                "account.created",
                {
                    "user_type": user_type,
                    "location_scope": location_scope,
                    "protein_library_enabled": bool(protein_library_enabled),
                    "local_ai_math_wallet_id": wallet_id,
                    "private_key_stored": False,
                },
            )
        return self.get_account(account_id)

    def get_account(self, account_id: str) -> LocalAccount:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM accounts WHERE account_id = ?",
                (str(account_id),),
            ).fetchone()
        if row is None:
            raise KeyError("unknown account")
        return self._row_to_account(row)

    def create_session(
        self,
        account_id: str,
        *,
        lifetime_seconds: float = 30 * 24 * 3600,
    ) -> str:
        account = self.get_account(account_id)
        if account.disabled_at is not None:
            raise PermissionError("account is disabled")
        lifetime = float(lifetime_seconds)
        if not 300 <= lifetime <= 365 * 24 * 3600:
            raise ValueError("session lifetime must be between 5 minutes and 1 year")
        raw = _token("CACE-SESSION-", 32)
        now = _now()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO account_sessions(
                    session_hash, account_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (_hash_token(raw), account_id, now, now + lifetime),
            )
            self._audit(db, account_id, "session.created", {"expires_at": now + lifetime})
        return raw

    def authenticate_session(self, raw_token: str) -> LocalAccount:
        token = str(raw_token or "").strip()
        if not token.startswith("CACE-SESSION-"):
            raise PermissionError("invalid session")
        with self._connect() as db:
            row = db.execute(
                """
                SELECT a.*
                FROM account_sessions s
                JOIN accounts a ON a.account_id = s.account_id
                WHERE s.session_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > ?
                  AND a.disabled_at IS NULL
                """,
                (_hash_token(token), _now()),
            ).fetchone()
        if row is None:
            raise PermissionError("invalid or expired session")
        return self._row_to_account(row)

    def revoke_session(self, raw_token: str) -> None:
        token_hash = _hash_token(str(raw_token or ""))
        with self._connect() as db:
            row = db.execute(
                "SELECT account_id FROM account_sessions WHERE session_hash = ?",
                (token_hash,),
            ).fetchone()
            db.execute(
                "UPDATE account_sessions SET revoked_at = COALESCE(revoked_at, ?) WHERE session_hash = ?",
                (_now(), token_hash),
            )
            if row is not None:
                self._audit(db, str(row["account_id"]), "session.revoked", {})

    def set_protein_library_enabled(
        self,
        account_id: str,
        enabled: bool,
    ) -> LocalAccount:
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE accounts
                SET protein_library_enabled = ?
                WHERE account_id = ? AND disabled_at IS NULL
                """,
                (1 if enabled else 0, account_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("unknown or disabled account")
            self._audit(
                db,
                account_id,
                "protein_library.preference",
                {"enabled": bool(enabled)},
            )
        return self.get_account(account_id)

    def store_protein(
        self,
        account_id: str,
        protein_object: Mapping[str, Any],
        *,
        source: str = "",
        license_id: str = "",
        attribution: str = "",
    ) -> StoredProtein:
        account = self.get_account(account_id)
        if not account.protein_library_enabled:
            raise PermissionError("protein library storage is disabled for this account")
        if not isinstance(protein_object, Mapping):
            raise ValueError("protein_object must be an object")
        object_json = json.dumps(
            dict(protein_object),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        encoded = object_json.encode("utf-8")
        if len(encoded) > MAX_PROTEIN_OBJECT_BYTES:
            raise ValueError("protein object exceeds local database size limit")
        digest = sha256(encoded).hexdigest()
        object_id = f"protein_{uuid4().hex}"
        created_at = _now()
        with self._connect() as db:
            existing = db.execute(
                "SELECT * FROM protein_objects WHERE account_id = ? AND semantic_sha256 = ?",
                (account_id, digest),
            ).fetchone()
            if existing is not None:
                return self._row_to_protein(existing)
            db.execute(
                """
                INSERT INTO protein_objects(
                    object_id, account_id, semantic_sha256, source, license_id,
                    attribution, object_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    object_id,
                    account_id,
                    digest,
                    _clean(source, field="source", max_chars=2000, allow_empty=True),
                    _clean(license_id, field="license_id", max_chars=160, allow_empty=True),
                    _clean(attribution, field="attribution", max_chars=4000, allow_empty=True),
                    object_json,
                    created_at,
                ),
            )
            self._audit(
                db,
                account_id,
                "protein.stored",
                {
                    "object_id": object_id,
                    "semantic_sha256": digest,
                    "source": source,
                    "license_id": license_id,
                },
            )
        return self.get_protein(account_id, object_id)

    @staticmethod
    def _row_to_protein(row: sqlite3.Row) -> StoredProtein:
        return StoredProtein(
            object_id=str(row["object_id"]),
            account_id=str(row["account_id"]),
            semantic_sha256=str(row["semantic_sha256"]),
            source=str(row["source"]),
            license_id=str(row["license_id"]),
            attribution=str(row["attribution"]),
            created_at=float(row["created_at"]),
            object_json=str(row["object_json"]),
        )

    def get_protein(self, account_id: str, object_id: str) -> StoredProtein:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM protein_objects WHERE account_id = ? AND object_id = ?",
                (account_id, object_id),
            ).fetchone()
        if row is None:
            raise KeyError("unknown protein object")
        return self._row_to_protein(row)

    def list_proteins(
        self,
        account_id: str,
        *,
        include_object: bool = False,
    ) -> tuple[dict[str, Any], ...]:
        account = self.get_account(account_id)
        if not account.protein_library_enabled:
            return ()
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM protein_objects WHERE account_id = ? ORDER BY created_at DESC, object_id",
                (account_id,),
            ).fetchall()
        return tuple(
            self._row_to_protein(row).to_dict(include_object=include_object)
            for row in rows
        )
