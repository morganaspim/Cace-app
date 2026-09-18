from dataclasses import replace
import json
import pytest

from cace_studio.payments.monero import (
    MAINNET_PRIMARY_ADDRESS,
    MainnetNotReady,
    MoneroConfig,
    MoneroInvoiceStore,
    MoneroNetwork,
    MoneroPaymentService,
)
from cace_studio.runtime.entitlement import EntitlementStore


class FakeRpc:
    def __init__(self, config, *, primary="stagenet-primary"):
        self.config = config
        self.primary = primary
        self.transfers = []
        self.created = 0

    def primary_address(self):
        return self.primary

    def create_subaddress(self, *, label):
        self.created += 1
        return f"stagenet-subaddress-{self.created}", self.created

    def incoming_transfers(self, *, subaddress_index):
        return list(self.transfers)


def _service(tmp_path, config=None, rpc=None):
    config = config or MoneroConfig(network=MoneroNetwork.STAGENET, min_confirmations=3)
    rpc = rpc or FakeRpc(config)
    entitlements = EntitlementStore(tmp_path / "entitlements.sqlite3")
    invoices = MoneroInvoiceStore(tmp_path / "invoices.sqlite3")
    return MoneroPaymentService(
        config=config,
        rpc=rpc,
        invoices=invoices,
        entitlements=entitlements,
    ), rpc, entitlements


def test_stagenet_invoice_uses_unique_subaddress_and_only_rpc_observation_unlocks(tmp_path):
    service, rpc, entitlements = _service(tmp_path)
    invoice = service.create_invoice(subject="alice", tier_id="pass_24h")
    assert invoice.network is MoneroNetwork.STAGENET
    assert invoice.address.startswith("stagenet-subaddress-")
    assert "tx_amount=0.025" in invoice.uri
    assert entitlements.status("alice", daily_free_seconds=0).allowed is False

    rpc.transfers = [{
        "amount": invoice.expected_atomic,
        "txid": "a" * 64,
        "confirmations": 2,
        "locked": False,
        "double_spend_seen": False,
        "subaddr_index": {"major": 0, "minor": invoice.subaddress_index},
    }]
    seen = service.refresh_invoice(invoice.invoice_id)
    assert seen.status.value == "SEEN"
    assert not seen.entitlement_granted

    rpc.transfers[0]["confirmations"] = 3
    confirmed = service.refresh_invoice(invoice.invoice_id)
    assert confirmed.status.value == "CONFIRMED"
    assert confirmed.entitlement_granted
    assert entitlements.status("alice", daily_free_seconds=0).unlimited

    # Re-reading a confirmed invoice is idempotent and cannot mint a second grant.
    again = service.refresh_invoice(invoice.invoice_id)
    assert again == confirmed


def test_wrong_amount_wrong_subaddress_and_double_spend_do_not_unlock(tmp_path):
    service, rpc, entitlements = _service(tmp_path)
    invoice = service.create_invoice(subject="bob", tier_id="pass_30d")
    rpc.transfers = [
        {
            "amount": invoice.expected_atomic - 1,
            "txid": "b" * 64,
            "confirmations": 100,
            "locked": False,
            "double_spend_seen": False,
            "subaddr_index": {"major": 0, "minor": invoice.subaddress_index},
        },
        {
            "amount": invoice.expected_atomic,
            "txid": "c" * 64,
            "confirmations": 100,
            "locked": False,
            "double_spend_seen": False,
            "subaddr_index": {"major": 0, "minor": invoice.subaddress_index + 1},
        },
        {
            "amount": invoice.expected_atomic,
            "txid": "d" * 64,
            "confirmations": 100,
            "locked": False,
            "double_spend_seen": True,
            "subaddr_index": {"major": 0, "minor": invoice.subaddress_index},
        },
    ]
    assert service.refresh_invoice(invoice.invoice_id).status.value == "CREATED"
    assert not entitlements.status("bob", daily_free_seconds=0).allowed


def test_mainnet_remains_disabled_without_live_stagenet_attestation(tmp_path, monkeypatch):
    config = MoneroConfig(
        network=MoneroNetwork.MAINNET,
        min_confirmations=3,
        mainnet_primary_address=MAINNET_PRIMARY_ADDRESS,
        mainnet_readiness_path=str(tmp_path / "missing.json"),
    )
    rpc = FakeRpc(config, primary=MAINNET_PRIMARY_ADDRESS)
    service, _, _ = _service(tmp_path, config=config, rpc=rpc)
    monkeypatch.setenv("CACE_MONERO_ENABLE_MAINNET", "1")
    with pytest.raises(MainnetNotReady):
        service.create_invoice(subject="alice", tier_id="pass_24h")


def test_mainnet_gate_requires_exact_wallet_after_readiness(tmp_path, monkeypatch):
    readiness = tmp_path / "ready.json"
    readiness.write_text(json.dumps({
        "schema": "cace-monero-stagenet-readiness-v1",
        "live_payment_confirmed": True,
        "idempotency_test_passed": True,
        "txid": "e" * 64,
    }), encoding="utf-8")
    config = MoneroConfig(
        network=MoneroNetwork.MAINNET,
        min_confirmations=3,
        mainnet_primary_address=MAINNET_PRIMARY_ADDRESS,
        mainnet_readiness_path=str(readiness),
    )
    service, _, _ = _service(tmp_path, config=config, rpc=FakeRpc(config, primary="wrong-wallet"))
    monkeypatch.setenv("CACE_MONERO_ENABLE_MAINNET", "1")
    with pytest.raises(MainnetNotReady, match="primary address"):
        service.create_invoice(subject="alice", tier_id="pass_24h")
