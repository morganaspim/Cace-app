from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
import json
import os
from pathlib import Path
import secrets
import sqlite3
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

from cace_studio.runtime.entitlement import EntitlementStore


ATOMIC_UNITS_PER_XMR = 10**12
MAINNET_PRIMARY_ADDRESS = "482ivJw4VqAaRvixSG84DgDum33SoBfnNiMxngMKn7etfKP1mwG2ZskTLVwRAhPmPDcb5iqLGkKdJbQ6DJmzqePPPxp3tmQ"


class MoneroNetwork(str, Enum):
    STAGENET = "stagenet"
    MAINNET = "mainnet"


class InvoiceStatus(str, Enum):
    CREATED = "CREATED"
    SEEN = "SEEN"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"


class MoneroRpcError(RuntimeError):
    pass


class MainnetNotReady(RuntimeError):
    pass


@dataclass(frozen=True)
class MoneroTier:
    tier_id: str
    name: str
    amount_atomic: int
    duration_seconds: int | None

    @property
    def amount_xmr(self) -> str:
        return atomic_to_xmr(self.amount_atomic)


MONERO_TIERS: tuple[MoneroTier, ...] = (
    MoneroTier("pass_24h", "24-Hour Compute Pass", 25_000_000_000, 24 * 3600),
    MoneroTier("pass_30d", "30-Day Research License", 250_000_000_000, 30 * 24 * 3600),
    MoneroTier("pass_enterprise", "Enterprise Research Cluster", 2_500_000_000_000, 90 * 24 * 3600),
    MoneroTier("pass_perpetual", "Perpetual Patron Tier", 1_500_000_000_000, None),
)


def xmr_to_atomic(value: str | Decimal) -> int:
    amount = Decimal(value)
    if amount <= 0:
        raise ValueError("XMR amount must be positive")
    atomic = (amount * ATOMIC_UNITS_PER_XMR).quantize(Decimal("1"), rounding=ROUND_DOWN)
    if atomic / ATOMIC_UNITS_PER_XMR != amount:
        raise ValueError("XMR amount has more than 12 decimal places")
    return int(atomic)


def atomic_to_xmr(value: int) -> str:
    if value < 0:
        raise ValueError("atomic amount must be non-negative")
    amount = Decimal(value) / Decimal(ATOMIC_UNITS_PER_XMR)
    text = format(amount, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@dataclass(frozen=True)
class MoneroConfig:
    network: MoneroNetwork = MoneroNetwork.STAGENET
    rpc_url: str = "http://127.0.0.1:38083/json_rpc"
    rpc_username: str | None = None
    rpc_password: str | None = None
    account_index: int = 0
    min_confirmations: int = 10
    mainnet_primary_address: str = MAINNET_PRIMARY_ADDRESS
    mainnet_readiness_path: str = "var/monero-mainnet-readiness.json"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "MoneroConfig":
        source = os.environ if env is None else env
        network = MoneroNetwork(source.get("CACE_MONERO_NETWORK", "stagenet").strip().lower())
        default_port = "38083" if network is MoneroNetwork.STAGENET else "18083"
        return cls(
            network=network,
            rpc_url=source.get("CACE_MONERO_WALLET_RPC_URL", f"http://127.0.0.1:{default_port}/json_rpc"),
            rpc_username=source.get("CACE_MONERO_RPC_USERNAME") or None,
            rpc_password=source.get("CACE_MONERO_RPC_PASSWORD") or None,
            account_index=int(source.get("CACE_MONERO_ACCOUNT_INDEX", "0")),
            min_confirmations=int(source.get("CACE_MONERO_MIN_CONFIRMATIONS", "10")),
            mainnet_primary_address=source.get("CACE_MONERO_MAINNET_ADDRESS", MAINNET_PRIMARY_ADDRESS),
            mainnet_readiness_path=source.get(
                "CACE_MONERO_MAINNET_READINESS_PATH", "var/monero-mainnet-readiness.json"
            ),
        )


class MoneroRpcClient:
    """Minimal `monero-wallet-rpc` JSON-RPC client with optional HTTP Digest auth."""

    def __init__(self, config: MoneroConfig, *, timeout_seconds: float = 10.0) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        if config.rpc_username:
            manager = HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, config.rpc_url, config.rpc_username, config.rpc_password or "")
            self._opener = build_opener(HTTPDigestAuthHandler(manager))
        else:
            self._opener = build_opener()

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": "cace", "method": method, "params": params or {}},
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self.config.rpc_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
            raise MoneroRpcError(f"monero-wallet-rpc request failed: {exc}") from exc
        if body.get("error"):
            raise MoneroRpcError(f"monero-wallet-rpc {method} error: {body['error']}")
        result = body.get("result")
        if not isinstance(result, dict):
            raise MoneroRpcError(f"monero-wallet-rpc {method} returned no result object")
        return result

    def primary_address(self) -> str:
        result = self.call("get_address", {"account_index": self.config.account_index})
        address = result.get("address")
        if not isinstance(address, str) or not address:
            raise MoneroRpcError("wallet RPC did not return a primary address")
        return address

    def create_subaddress(self, *, label: str) -> tuple[str, int]:
        result = self.call(
            "create_address",
            {"account_index": self.config.account_index, "label": label},
        )
        address = result.get("address")
        index = result.get("address_index")
        if not isinstance(address, str) or not address or not isinstance(index, int):
            raise MoneroRpcError("wallet RPC returned invalid subaddress")
        return address, index

    def incoming_transfers(self, *, subaddress_index: int) -> list[dict[str, Any]]:
        result = self.call(
            "get_transfers",
            {
                "in": True,
                "pool": True,
                "pending": True,
                "failed": False,
                "account_index": self.config.account_index,
                "subaddr_indices": [subaddress_index],
            },
        )
        rows: list[dict[str, Any]] = []
        for key in ("in", "pool", "pending"):
            value = result.get(key, [])
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
        return rows


@dataclass(frozen=True)
class MoneroInvoice:
    invoice_id: str
    subject: str
    network: MoneroNetwork
    tier_id: str
    expected_atomic: int
    address: str
    account_index: int
    subaddress_index: int
    created_at: float
    status: InvoiceStatus
    txid: str | None = None
    confirmations: int = 0
    entitlement_granted: bool = False

    @property
    def amount_xmr(self) -> str:
        return atomic_to_xmr(self.expected_atomic)

    @property
    def uri(self) -> str:
        desc = quote(f"CACE Compute License - {self.tier_id}", safe="")
        return f"monero:{self.address}?tx_amount={self.amount_xmr}&tx_description={desc}"


class MoneroInvoiceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS monero_invoices (
                    invoice_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    network TEXT NOT NULL,
                    tier_id TEXT NOT NULL,
                    expected_atomic INTEGER NOT NULL,
                    address TEXT NOT NULL UNIQUE,
                    account_index INTEGER NOT NULL,
                    subaddress_index INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    txid TEXT UNIQUE,
                    confirmations INTEGER NOT NULL DEFAULT 0,
                    entitlement_granted INTEGER NOT NULL DEFAULT 0
                );
                CREATE UNIQUE INDEX IF NOT EXISTS monero_invoice_subaddr_idx
                ON monero_invoices(network, account_index, subaddress_index);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, invoice: MoneroInvoice) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO monero_invoices VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    invoice.invoice_id,
                    invoice.subject,
                    invoice.network.value,
                    invoice.tier_id,
                    invoice.expected_atomic,
                    invoice.address,
                    invoice.account_index,
                    invoice.subaddress_index,
                    invoice.created_at,
                    invoice.status.value,
                    invoice.txid,
                    invoice.confirmations,
                    int(invoice.entitlement_granted),
                ),
            )

    def get(self, invoice_id: str) -> MoneroInvoice:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM monero_invoices WHERE invoice_id=?", (invoice_id,)
            ).fetchone()
        if row is None:
            raise KeyError(invoice_id)
        return MoneroInvoice(
            invoice_id=row["invoice_id"],
            subject=row["subject"],
            network=MoneroNetwork(row["network"]),
            tier_id=row["tier_id"],
            expected_atomic=int(row["expected_atomic"]),
            address=row["address"],
            account_index=int(row["account_index"]),
            subaddress_index=int(row["subaddress_index"]),
            created_at=float(row["created_at"]),
            status=InvoiceStatus(row["status"]),
            txid=row["txid"],
            confirmations=int(row["confirmations"]),
            entitlement_granted=bool(row["entitlement_granted"]),
        )

    def update_payment(
        self,
        invoice_id: str,
        *,
        status: InvoiceStatus,
        txid: str | None,
        confirmations: int,
        entitlement_granted: bool,
    ) -> MoneroInvoice:
        with self._connect() as conn:
            try:
                conn.execute(
                    "UPDATE monero_invoices SET status=?,txid=?,confirmations=?,entitlement_granted=? "
                    "WHERE invoice_id=?",
                    (status.value, txid, confirmations, int(entitlement_granted), invoice_id),
                )
            except sqlite3.IntegrityError as exc:
                raise MoneroRpcError("transaction already bound to another invoice") from exc
        return self.get(invoice_id)


def _tier(tier_id: str) -> MoneroTier:
    for tier in MONERO_TIERS:
        if tier.tier_id == tier_id:
            return tier
    raise KeyError(tier_id)


class MoneroPaymentService:
    def __init__(
        self,
        *,
        config: MoneroConfig,
        rpc: MoneroRpcClient,
        invoices: MoneroInvoiceStore,
        entitlements: EntitlementStore,
    ) -> None:
        self.config = config
        self.rpc = rpc
        self.invoices = invoices
        self.entitlements = entitlements

    def _assert_network_ready(self) -> None:
        if self.config.network is MoneroNetwork.STAGENET:
            return
        if os.environ.get("CACE_MONERO_ENABLE_MAINNET") != "1":
            raise MainnetNotReady("Monero mainnet is disabled; complete live stagenet verification first")
        readiness_path = Path(self.config.mainnet_readiness_path)
        if not readiness_path.is_file():
            raise MainnetNotReady("missing live stagenet readiness attestation")
        try:
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MainnetNotReady("invalid live stagenet readiness attestation") from exc
        if not (
            readiness.get("schema") == "cace-monero-stagenet-readiness-v1"
            and readiness.get("live_payment_confirmed") is True
            and isinstance(readiness.get("txid"), str)
            and len(readiness["txid"]) == 64
            and readiness.get("idempotency_test_passed") is True
        ):
            raise MainnetNotReady("stagenet readiness attestation is incomplete")
        primary = self.rpc.primary_address()
        if primary != self.config.mainnet_primary_address:
            raise MainnetNotReady("wallet RPC primary address does not match configured CACE mainnet wallet")

    def create_invoice(self, *, subject: str, tier_id: str) -> MoneroInvoice:
        if not subject.strip():
            raise ValueError("subject must be non-empty")
        self._assert_network_ready()
        tier = _tier(tier_id)
        invoice_id = "xmr_" + secrets.token_urlsafe(18)
        address, minor = self.rpc.create_subaddress(label=f"CACE {invoice_id} {subject}")
        invoice = MoneroInvoice(
            invoice_id=invoice_id,
            subject=subject,
            network=self.config.network,
            tier_id=tier.tier_id,
            expected_atomic=tier.amount_atomic,
            address=address,
            account_index=self.config.account_index,
            subaddress_index=minor,
            created_at=datetime.now(timezone.utc).timestamp(),
            status=InvoiceStatus.CREATED,
        )
        self.invoices.create(invoice)
        return invoice

    @staticmethod
    def _minor_index(transfer: dict[str, Any]) -> int | None:
        sub = transfer.get("subaddr_index")
        if isinstance(sub, dict) and isinstance(sub.get("minor"), int):
            return int(sub["minor"])
        return None

    def refresh_invoice(self, invoice_id: str) -> MoneroInvoice:
        invoice = self.invoices.get(invoice_id)
        if invoice.entitlement_granted:
            return invoice
        transfers = self.rpc.incoming_transfers(subaddress_index=invoice.subaddress_index)
        candidates: list[dict[str, Any]] = []
        for transfer in transfers:
            if self._minor_index(transfer) != invoice.subaddress_index:
                continue
            if bool(transfer.get("double_spend_seen", False)):
                continue
            amount = transfer.get("amount")
            txid = transfer.get("txid")
            if not isinstance(amount, int) or amount < invoice.expected_atomic:
                continue
            if not isinstance(txid, str) or len(txid) != 64:
                continue
            candidates.append(transfer)
        if not candidates:
            return invoice

        transfer = max(candidates, key=lambda item: int(item.get("confirmations", 0) or 0))
        confirmations = int(transfer.get("confirmations", 0) or 0)
        locked = bool(transfer.get("locked", False))
        txid = str(transfer["txid"])
        confirmed = confirmations >= self.config.min_confirmations and not locked
        status = InvoiceStatus.CONFIRMED if confirmed else InvoiceStatus.SEEN
        granted = False

        if confirmed:
            tier = _tier(invoice.tier_id)
            now = datetime.now(timezone.utc).timestamp()
            valid_until = None if tier.duration_seconds is None else now + tier.duration_seconds
            receipt = f"monero:{invoice.network.value}:{txid}"
            grant_id = f"grant_{invoice.invoice_id}"
            # All paid tiers are unlimited during their validity window. Payment
            # changes resource entitlement only; it cannot alter evidence state.
            self.entitlements.add_grant(
                grant_id=grant_id,
                subject=invoice.subject,
                valid_from=now,
                valid_until=valid_until,
                compute_seconds=None,
                source=f"monero-{invoice.network.value}:{tier.tier_id}",
                receipt_id=receipt,
            )
            granted = True

        return self.invoices.update_payment(
            invoice_id,
            status=status,
            txid=txid,
            confirmations=confirmations,
            entitlement_granted=granted,
        )

    def public_config(self) -> dict[str, Any]:
        return {
            "network": self.config.network.value,
            "mainnet_primary_address": self.config.mainnet_primary_address,
            "mainnet_enabled": self.config.network is MoneroNetwork.MAINNET,
            "min_confirmations": self.config.min_confirmations,
            "tiers": [
                {
                    "id": tier.tier_id,
                    "name": tier.name,
                    "amount_xmr": tier.amount_xmr,
                    "duration_seconds": tier.duration_seconds,
                }
                for tier in MONERO_TIERS
            ],
        }
