from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any, Mapping
from uuid import uuid4


PAIRING_CAPABILITIES = (
    "economy.market_discovery",
    "economy.compute_bid",
    "economy.compute_offer",
    "heartbeat.resource_summary",
    "settlement.receipt_metadata",
)
CODE_LIFETIME_SECONDS = 10 * 60


def _now() -> float:
    return time.time()


def _code(prefix: str) -> str:
    return prefix + secrets.token_urlsafe(24)


def _hash_code(value: str) -> str:
    return sha256(str(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PairingCodes:
    instance_id: str
    receive_code: str
    outgoing_code: str
    expires_at: float
    capabilities: tuple[str, ...] = PAIRING_CAPABILITIES

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EconomyLink:
    link_id: str
    source_instance_id: str
    target_instance_id: str
    source_account_id: str
    target_account_id: str
    capabilities: tuple[str, ...]
    created_at: float
    active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NetworkPairingService:
    """One-time directional pairing for local-AI economy links.

    A directed A -> B link consumes A's outgoing code and B's receive code.
    Bidirectional links require an explicit reverse pairing. Only the fixed
    economy/heartbeat capabilities above are granted.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

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
                CREATE TABLE IF NOT EXISTS network_instances (
                    instance_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pairing_codes (
                    code_hash TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES network_instances(instance_id) ON DELETE CASCADE,
                    direction TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_at REAL,
                    revoked_at REAL
                );

                CREATE TABLE IF NOT EXISTS economy_links (
                    link_id TEXT PRIMARY KEY,
                    source_instance_id TEXT NOT NULL REFERENCES network_instances(instance_id),
                    target_instance_id TEXT NOT NULL REFERENCES network_instances(instance_id),
                    source_account_id TEXT NOT NULL,
                    target_account_id TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    disabled_at REAL,
                    UNIQUE(source_instance_id, target_instance_id)
                );

                CREATE TABLE IF NOT EXISTS network_audit_events (
                    event_id TEXT PRIMARY KEY,
                    instance_id TEXT,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    def _audit(
        self,
        db: sqlite3.Connection,
        instance_id: str | None,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        db.execute(
            """
            INSERT INTO network_audit_events(
                event_id, instance_id, event_type, event_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                instance_id,
                event_type,
                json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str),
                _now(),
            ),
        )

    def _require_instance(
        self,
        db: sqlite3.Connection,
        *,
        account_id: str,
        instance_id: str,
        require_enabled: bool = False,
    ) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM network_instances WHERE instance_id = ? AND account_id = ?",
            (instance_id, account_id),
        ).fetchone()
        if row is None:
            raise PermissionError("unknown network instance for this account")
        if require_enabled and not bool(row["enabled"]):
            raise PermissionError("network is disabled for this instance")
        return row

    def _revoke_unused(
        self,
        db: sqlite3.Connection,
        instance_id: str,
        direction: str | None = None,
    ) -> None:
        query = """
            UPDATE pairing_codes
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE instance_id = ?
              AND consumed_at IS NULL
              AND revoked_at IS NULL
        """
        params: list[Any] = [_now(), instance_id]
        if direction is not None:
            query += " AND direction = ?"
            params.append(direction)
        db.execute(query, tuple(params))

    def _issue(
        self,
        db: sqlite3.Connection,
        instance_id: str,
        direction: str,
        *,
        lifetime_seconds: float = CODE_LIFETIME_SECONDS,
    ) -> tuple[str, float]:
        if direction not in {"receive", "outgoing"}:
            raise ValueError("invalid pairing-code direction")
        lifetime = float(lifetime_seconds)
        if not 60 <= lifetime <= 3600:
            raise ValueError("pairing-code lifetime must be between 60 and 3600 seconds")
        raw = _code("CACE-RCV-" if direction == "receive" else "CACE-OUT-")
        now = _now()
        db.execute(
            """
            INSERT INTO pairing_codes(
                code_hash, instance_id, direction, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (_hash_code(raw), instance_id, direction, now, now + lifetime),
        )
        return raw, now + lifetime

    def enable(
        self,
        account_id: str,
        *,
        instance_id: str | None = None,
        lifetime_seconds: float = CODE_LIFETIME_SECONDS,
    ) -> PairingCodes:
        instance_id = str(instance_id or f"instance_{uuid4().hex}")
        now = _now()
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM network_instances WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
            if row is None:
                db.execute(
                    """
                    INSERT INTO network_instances(
                        instance_id, account_id, enabled, created_at, updated_at
                    ) VALUES (?, ?, 1, ?, ?)
                    """,
                    (instance_id, account_id, now, now),
                )
            else:
                if str(row["account_id"]) != account_id:
                    raise PermissionError("network instance belongs to another account")
                db.execute(
                    "UPDATE network_instances SET enabled = 1, updated_at = ? WHERE instance_id = ?",
                    (now, instance_id),
                )
            self._revoke_unused(db, instance_id)
            receive_code, receive_exp = self._issue(
                db, instance_id, "receive", lifetime_seconds=lifetime_seconds
            )
            outgoing_code, outgoing_exp = self._issue(
                db, instance_id, "outgoing", lifetime_seconds=lifetime_seconds
            )
            self._audit(
                db,
                instance_id,
                "network.enabled",
                {
                    "account_id": account_id,
                    "capabilities": list(PAIRING_CAPABILITIES),
                    "plaintext_codes_persisted": False,
                },
            )
        return PairingCodes(
            instance_id=instance_id,
            receive_code=receive_code,
            outgoing_code=outgoing_code,
            expires_at=min(receive_exp, outgoing_exp),
        )

    def disable(self, account_id: str, instance_id: str) -> None:
        with self._connect() as db:
            self._require_instance(
                db,
                account_id=account_id,
                instance_id=instance_id,
            )
            now = _now()
            db.execute(
                "UPDATE network_instances SET enabled = 0, updated_at = ? WHERE instance_id = ?",
                (now, instance_id),
            )
            self._revoke_unused(db, instance_id)
            db.execute(
                """
                UPDATE economy_links
                SET disabled_at = COALESCE(disabled_at, ?)
                WHERE source_instance_id = ? OR target_instance_id = ?
                """,
                (now, instance_id, instance_id),
            )
            self._audit(db, instance_id, "network.disabled", {})

    def rotate(
        self,
        account_id: str,
        instance_id: str,
        direction: str,
        *,
        lifetime_seconds: float = CODE_LIFETIME_SECONDS,
    ) -> dict[str, Any]:
        with self._connect() as db:
            self._require_instance(
                db,
                account_id=account_id,
                instance_id=instance_id,
                require_enabled=True,
            )
            self._revoke_unused(db, instance_id, direction)
            code, expires_at = self._issue(
                db,
                instance_id,
                direction,
                lifetime_seconds=lifetime_seconds,
            )
            self._audit(
                db,
                instance_id,
                "pairing_code.rotated",
                {"direction": direction, "expires_at": expires_at},
            )
        return {
            "instance_id": instance_id,
            "direction": direction,
            "code": code,
            "expires_at": expires_at,
        }

    def _owned_active_code(
        self,
        db: sqlite3.Connection,
        instance_id: str,
        direction: str,
    ) -> sqlite3.Row:
        row = db.execute(
            """
            SELECT *
            FROM pairing_codes
            WHERE instance_id = ?
              AND direction = ?
              AND consumed_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (instance_id, direction, _now()),
        ).fetchone()
        if row is None:
            raise PermissionError(f"no active {direction} code; rotate a new code")
        return row

    def _peer_code(
        self,
        db: sqlite3.Connection,
        raw_code: str,
        direction: str,
    ) -> sqlite3.Row:
        row = db.execute(
            """
            SELECT c.*, i.account_id, i.enabled
            FROM pairing_codes c
            JOIN network_instances i ON i.instance_id = c.instance_id
            WHERE c.code_hash = ?
              AND c.direction = ?
              AND c.consumed_at IS NULL
              AND c.revoked_at IS NULL
              AND c.expires_at > ?
            """,
            (_hash_code(raw_code), direction, _now()),
        ).fetchone()
        if row is None or not bool(row["enabled"]):
            raise PermissionError(
                f"peer {direction} code is invalid, expired, used, or disabled"
            )
        return row

    def _link(
        self,
        db: sqlite3.Connection,
        outgoing: sqlite3.Row,
        receive: sqlite3.Row,
    ) -> EconomyLink:
        source_instance = str(outgoing["instance_id"])
        target_instance = str(receive["instance_id"])
        if source_instance == target_instance:
            raise PermissionError("cannot pair an instance to itself")

        source_account = db.execute(
            "SELECT account_id FROM network_instances WHERE instance_id = ?",
            (source_instance,),
        ).fetchone()
        target_account = db.execute(
            "SELECT account_id FROM network_instances WHERE instance_id = ?",
            (target_instance,),
        ).fetchone()
        if source_account is None or target_account is None:
            raise PermissionError("pairing instance no longer exists")

        existing = db.execute(
            """
            SELECT *
            FROM economy_links
            WHERE source_instance_id = ? AND target_instance_id = ?
            """,
            (source_instance, target_instance),
        ).fetchone()
        now = _now()
        if existing is None:
            link_id = f"link_{uuid4().hex}"
            created_at = now
            db.execute(
                """
                INSERT INTO economy_links(
                    link_id, source_instance_id, target_instance_id,
                    source_account_id, target_account_id,
                    capabilities_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link_id,
                    source_instance,
                    target_instance,
                    str(source_account["account_id"]),
                    str(target_account["account_id"]),
                    json.dumps(list(PAIRING_CAPABILITIES), separators=(",", ":")),
                    now,
                ),
            )
        else:
            link_id = str(existing["link_id"])
            created_at = float(existing["created_at"])
            db.execute(
                "UPDATE economy_links SET disabled_at = NULL WHERE link_id = ?",
                (link_id,),
            )

        db.execute(
            "UPDATE pairing_codes SET consumed_at = ? WHERE code_hash IN (?, ?)",
            (now, str(outgoing["code_hash"]), str(receive["code_hash"])),
        )
        self._audit(
            db,
            source_instance,
            "economy_link.created",
            {
                "link_id": link_id,
                "target_instance_id": target_instance,
                "capabilities": list(PAIRING_CAPABILITIES),
            },
        )
        return EconomyLink(
            link_id=link_id,
            source_instance_id=source_instance,
            target_instance_id=target_instance,
            source_account_id=str(source_account["account_id"]),
            target_account_id=str(target_account["account_id"]),
            capabilities=PAIRING_CAPABILITIES,
            created_at=created_at,
            active=True,
        )

    def connect_outgoing(
        self,
        account_id: str,
        instance_id: str,
        peer_receive_code: str,
    ) -> tuple[EconomyLink, dict[str, Any]]:
        with self._connect() as db:
            self._require_instance(
                db,
                account_id=account_id,
                instance_id=instance_id,
                require_enabled=True,
            )
            outgoing = self._owned_active_code(db, instance_id, "outgoing")
            receive = self._peer_code(db, peer_receive_code.strip(), "receive")
            link = self._link(db, outgoing, receive)
            replacement, expires_at = self._issue(db, instance_id, "outgoing")
        return link, {
            "direction": "outgoing",
            "replacement_code": replacement,
            "expires_at": expires_at,
        }

    def accept_incoming(
        self,
        account_id: str,
        instance_id: str,
        peer_outgoing_code: str,
    ) -> tuple[EconomyLink, dict[str, Any]]:
        with self._connect() as db:
            self._require_instance(
                db,
                account_id=account_id,
                instance_id=instance_id,
                require_enabled=True,
            )
            receive = self._owned_active_code(db, instance_id, "receive")
            outgoing = self._peer_code(db, peer_outgoing_code.strip(), "outgoing")
            link = self._link(db, outgoing, receive)
            replacement, expires_at = self._issue(db, instance_id, "receive")
        return link, {
            "direction": "receive",
            "replacement_code": replacement,
            "expires_at": expires_at,
        }

    def status(self, account_id: str, instance_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require_instance(
                db,
                account_id=account_id,
                instance_id=instance_id,
            )
            links = db.execute(
                """
                SELECT *
                FROM economy_links
                WHERE (source_instance_id = ? OR target_instance_id = ?)
                  AND disabled_at IS NULL
                ORDER BY created_at, link_id
                """,
                (instance_id, instance_id),
            ).fetchall()
        return {
            "instance_id": instance_id,
            "enabled": bool(row["enabled"]),
            "capabilities": list(PAIRING_CAPABILITIES),
            "links": [
                {
                    "link_id": str(item["link_id"]),
                    "source_instance_id": str(item["source_instance_id"]),
                    "target_instance_id": str(item["target_instance_id"]),
                    "outgoing": str(item["source_instance_id"]) == instance_id,
                    "created_at": float(item["created_at"]),
                }
                for item in links
            ],
        }
