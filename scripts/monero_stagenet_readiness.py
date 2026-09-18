#!/usr/bin/env python3
"""Create the mainnet-enablement attestation after a REAL stagenet payment.

This command does not fabricate readiness. It asks the configured stagenet wallet
RPC to refresh an existing invoice and writes the readiness file only after that
invoice is actually confirmed and entitlement idempotency has been exercised.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from cace_studio.payments.monero import (
    MoneroConfig,
    MoneroInvoiceStore,
    MoneroNetwork,
    MoneroPaymentService,
    MoneroRpcClient,
)
from cace_studio.runtime.entitlement import EntitlementStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("invoice_id")
    parser.add_argument("--state-dir", default="var/cace")
    parser.add_argument("--output", default="var/monero-mainnet-readiness.json")
    args = parser.parse_args()

    config = MoneroConfig.from_env()
    if config.network is not MoneroNetwork.STAGENET:
        parser.error("readiness must be established on stagenet")
    root = Path(args.state_dir)
    entitlement_store = EntitlementStore(root / "entitlements.sqlite3")
    invoices = MoneroInvoiceStore(root / "monero-invoices.sqlite3")
    service = MoneroPaymentService(
        config=config,
        rpc=MoneroRpcClient(config),
        invoices=invoices,
        entitlements=entitlement_store,
    )
    invoice = service.refresh_invoice(args.invoice_id)
    if not invoice.entitlement_granted or invoice.status.value != "CONFIRMED" or not invoice.txid:
        raise SystemExit("invoice is not confirmed on stagenet; refusing readiness attestation")

    # Second refresh must not mint a second entitlement grant.
    before = entitlement_store.status(invoice.subject)
    again = service.refresh_invoice(args.invoice_id)
    after = entitlement_store.status(invoice.subject)
    if not again.entitlement_granted or before != after:
        raise SystemExit("idempotency check failed; refusing readiness attestation")

    payload = {
        "schema": "cace-monero-stagenet-readiness-v1",
        "live_payment_confirmed": True,
        "idempotency_test_passed": True,
        "invoice_id": invoice.invoice_id,
        "txid": invoice.txid,
        "confirmations": invoice.confirmations,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
