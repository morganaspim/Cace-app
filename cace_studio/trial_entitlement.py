from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
import time
from typing import Any


class TrialEntitlementError(ValueError):
    pass


class DuplicatePersonAccountError(PermissionError):
    pass


@dataclass(frozen=True)
class TrialEntitlement:
    person_key: str
    account_id: str
    trial_started_at: float
    trial_expires_at: float
    licensed: bool
    licensed_at: float | None
    disabled_at: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.current_mode()
        return payload

    def current_mode(self, now: float | None = None) -> str:
        now_value = time.time() if now is None else float(now)
        if self.disabled_at is not None:
            return "disabled"
        if self.licensed:
            return "licensed"
        if now_value < self.trial_expires_at:
            return "trial"
        return "limited"


class TrialEntitlementStore:
    """Server-side one-person/one-trial entitlement ledger.

    person_key must already be an opaque, stable server-derived key supplied
    by the production authentication layer. Raw identity documents, provider
    tokens, wallet secrets, or payment credentials do not belong here.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS trial_entitlements (
                    person_key TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL UNIQUE,
                    trial_started_at REAL NOT NULL,
                    trial_expires_at REAL NOT NULL,
                    licensed INTEGER NOT NULL DEFAULT 0,
                    licensed_at REAL,
                    disabled_at REAL
                );

                CREATE TABLE IF NOT EXISTS trial_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_key TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _validate_person_key(person_key: str) -> str:
        key = str(person_key or "").strip()
        if len(key) < 24 or len(key) > 256:
            raise TrialEntitlementError(
                "person_key must be an opaque stable server-derived key"
            )
        if any(char.isspace() for char in key):
            raise TrialEntitlementError("person_key must not contain whitespace")
        return key

    @staticmethod
    def _validate_account_id(account_id: str) -> str:
        value = str(account_id or "").strip()
        if not value or len(value) > 160 or any(char.isspace() for char in value):
            raise TrialEntitlementError("account_id must be a canonical identifier")
        return value

    @staticmethod
    def _row(row: sqlite3.Row) -> TrialEntitlement:
        return TrialEntitlement(
            person_key=str(row["person_key"]),
            account_id=str(row["account_id"]),
            trial_started_at=float(row["trial_started_at"]),
            trial_expires_at=float(row["trial_expires_at"]),
            licensed=bool(row["licensed"]),
            licensed_at=None if row["licensed_at"] is None else float(row["licensed_at"]),
            disabled_at=None if row["disabled_at"] is None else float(row["disabled_at"]),
        )

    def claim_trial(
        self,
        *,
        person_key: str,
        account_id: str,
        trial_seconds: float,
        now: float | None = None,
    ) -> TrialEntitlement:
        person_key = self._validate_person_key(person_key)
        account_id = self._validate_account_id(account_id)
        duration = float(trial_seconds)
        if not 3600 <= duration <= 365 * 24 * 3600:
            raise TrialEntitlementError(
                "trial_seconds must be between 1 hour and 1 year"
            )
        now_value = time.time() if now is None else float(now)
        expires = now_value + duration

        with self._connect() as db:
            existing = db.execute(
                "SELECT * FROM trial_entitlements WHERE person_key = ?",
                (person_key,),
            ).fetchone()
            if existing is not None:
                entitlement = self._row(existing)
                if entitlement.account_id != account_id:
                    raise DuplicatePersonAccountError(
                        "this verified person already has an account/trial; recover or merge the existing account"
                    )
                return entitlement

            account_existing = db.execute(
                "SELECT * FROM trial_entitlements WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if account_existing is not None:
                raise DuplicatePersonAccountError(
                    "this account is already bound to another verified person key"
                )

            db.execute(
                """
                INSERT INTO trial_entitlements(
                    person_key, account_id, trial_started_at, trial_expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (person_key, account_id, now_value, expires),
            )
            db.execute(
                """
                INSERT INTO trial_audit(
                    person_key, account_id, event_type, created_at
                ) VALUES (?, ?, 'trial.claimed', ?)
                """,
                (person_key, account_id, now_value),
            )
        return self.get(person_key)

    def get(self, person_key: str) -> TrialEntitlement:
        person_key = self._validate_person_key(person_key)
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM trial_entitlements WHERE person_key = ?",
                (person_key,),
            ).fetchone()
        if row is None:
            raise KeyError("no trial entitlement for person key")
        return self._row(row)

    def bind_recovered_account(
        self,
        *,
        person_key: str,
        existing_account_id: str,
        recovered_account_id: str,
    ) -> TrialEntitlement:
        person_key = self._validate_person_key(person_key)
        existing_account_id = self._validate_account_id(existing_account_id)
        recovered_account_id = self._validate_account_id(recovered_account_id)
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM trial_entitlements WHERE person_key = ?",
                (person_key,),
            ).fetchone()
            if row is None:
                raise KeyError("no trial entitlement for person key")
            entitlement = self._row(row)
            if entitlement.account_id != existing_account_id:
                raise PermissionError("existing account does not match entitlement")
            collision = db.execute(
                "SELECT person_key FROM trial_entitlements WHERE account_id = ?",
                (recovered_account_id,),
            ).fetchone()
            if collision is not None and str(collision["person_key"]) != person_key:
                raise DuplicatePersonAccountError(
                    "recovered account is already bound to another person"
                )
            db.execute(
                "UPDATE trial_entitlements SET account_id = ? WHERE person_key = ?",
                (recovered_account_id, person_key),
            )
            db.execute(
                """
                INSERT INTO trial_audit(
                    person_key, account_id, event_type, created_at
                ) VALUES (?, ?, 'account.recovered_or_merged', ?)
                """,
                (person_key, recovered_account_id, time.time()),
            )
        return self.get(person_key)

    def activate_license(
        self,
        *,
        person_key: str,
        now: float | None = None,
    ) -> TrialEntitlement:
        person_key = self._validate_person_key(person_key)
        now_value = time.time() if now is None else float(now)
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE trial_entitlements
                SET licensed = 1,
                    licensed_at = COALESCE(licensed_at, ?)
                WHERE person_key = ? AND disabled_at IS NULL
                """,
                (now_value, person_key),
            )
            if cursor.rowcount != 1:
                raise KeyError("no active entitlement for person key")
            account = db.execute(
                "SELECT account_id FROM trial_entitlements WHERE person_key = ?",
                (person_key,),
            ).fetchone()
            db.execute(
                """
                INSERT INTO trial_audit(
                    person_key, account_id, event_type, created_at
                ) VALUES (?, ?, 'license.activated', ?)
                """,
                (person_key, str(account["account_id"]), now_value),
            )
        return self.get(person_key)

    def permissions(
        self,
        person_key: str,
        *,
        now: float | None = None,
    ) -> dict[str, Any]:
        entitlement = self.get(person_key)
        mode = entitlement.current_mode(now)

        base = {
            "sign_in": True,
            "view_owned_data": True,
            "export_owned_data": True,
            "delete_owned_data": True,
            "account_recovery": True,
            "help": True,
            "manage_license": True,
        }
        premium = {
            "scientific_execution": mode in {"trial", "licensed"},
            "network_ai_economy": mode in {"trial", "licensed"},
            "premium_local_ai": mode in {"trial", "licensed"},
            "math_coin_market_actions": mode in {"trial", "licensed"},
            "premium_compute": mode in {"trial", "licensed"},
            "enterprise_collaboration": mode == "licensed",
        }
        return {
            "mode": mode,
            "permissions": {**base, **premium},
            "non_destructive": True,
        }
