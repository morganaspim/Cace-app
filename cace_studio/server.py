from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cace_studio.runtime.canvas_bridge import compile_canvas_heartbeat
from cace_studio.runtime.hashing import HashBackendUnavailable

from cace_studio.payments.monero import (
    MainnetNotReady,
    MoneroConfig,
    MoneroInvoiceStore,
    MoneroPaymentService,
    MoneroRpcClient,
    MoneroRpcError,
)
from cace_studio.runtime.entitlement import (
    EntitlementExpired,
    EntitlementService,
    EntitlementStore,
    LeaseSigner,
)


class InvoiceRequest(BaseModel):
    tier_id: str


class LeaseRequest(BaseModel):
    requested_seconds: float = 30.0


class HeartbeatGraphRequest(BaseModel):
    experiment: dict


def _default_subject_resolver(x_cace_subject: str | None = Header(default=None)) -> str:
    fixed = os.environ.get("CACE_SINGLE_USER_SUBJECT")
    if fixed:
        return fixed
    if os.environ.get("CACE_TRUST_SUBJECT_HEADER") == "1" and x_cace_subject:
        return x_cace_subject
    raise HTTPException(
        status_code=401,
        detail=(
            "No authenticated CACE subject. Configure CACE_SINGLE_USER_SUBJECT for a "
            "single-user deployment or have a trusted auth proxy set X-CACE-Subject and "
            "enable CACE_TRUST_SUBJECT_HEADER=1."
        ),
    )


def create_app(
    *,
    state_dir: str | Path | None = None,
    subject_resolver: Callable[..., str] | None = None,
    signer: LeaseSigner | None = None,
    monero_config: MoneroConfig | None = None,
    monero_rpc: MoneroRpcClient | None = None,
) -> FastAPI:
    root = Path(state_dir or os.environ.get("CACE_STATE_DIR", "var/cace")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    entitlement_store = EntitlementStore(root / "entitlements.sqlite3")
    lease_signer = signer or LeaseSigner.from_env()
    entitlement_service = EntitlementService(entitlement_store, lease_signer)
    config = monero_config or MoneroConfig.from_env()
    rpc = monero_rpc or MoneroRpcClient(config)
    invoice_store = MoneroInvoiceStore(root / "monero-invoices.sqlite3")
    payments = MoneroPaymentService(
        config=config,
        rpc=rpc,
        invoices=invoice_store,
        entitlements=entitlement_store,
    )

    app = FastAPI(title="CACE Runtime Control Plane", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get("CACE_WEB_ORIGIN", "http://127.0.0.1:3000")],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CACE-Subject"],
    )
    resolve_subject = subject_resolver or _default_subject_resolver

    app.state.cace_entitlements = entitlement_service
    app.state.cace_payments = payments

    @app.get("/api/runtime/status")
    def runtime_status(subject: str = Depends(resolve_subject)) -> dict:
        status = entitlement_service.status(subject)
        payload = asdict(status)
        payload["free_remaining_seconds"] = status.free_remaining_seconds
        payload["remaining_seconds"] = None if status.unlimited else status.remaining_seconds
        payload["payment_network"] = config.network.value
        payload["evidence_effect"] = "NONE"
        return payload

    @app.post("/api/entitlement/lease")
    def issue_lease(request: LeaseRequest, subject: str = Depends(resolve_subject)) -> dict:
        try:
            token = entitlement_service.issue_lease(
                subject,
                requested_seconds=request.requested_seconds,
            )
        except EntitlementExpired as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        return {"lease": token, "evidence_effect": "NONE"}

    @app.post("/api/runtime/heartbeat/graph")
    def heartbeat_graph(request: HeartbeatGraphRequest, _: str = Depends(resolve_subject)) -> dict:
        algorithm = os.environ.get("CACE_HEARTBEAT_HASH", "blake3")
        try:
            _, summary = compile_canvas_heartbeat(
                request.experiment,
                master_seed=os.environ.get("CACE_HEARTBEAT_MASTER_SEED", "cace-default-seed"),
                hash_algorithm=algorithm,
            )
        except HashBackendUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        summary["evidence_effect"] = "NONE"
        return summary

    @app.get("/api/payments/monero/config")
    def payment_config(_: str = Depends(resolve_subject)) -> dict:
        return payments.public_config()

    @app.post("/api/payments/monero/invoices")
    def create_invoice(request: InvoiceRequest, subject: str = Depends(resolve_subject)) -> dict:
        try:
            invoice = payments.create_invoice(subject=subject, tier_id=request.tier_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="unknown Monero tier") from exc
        except (MainnetNotReady, MoneroRpcError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "invoice_id": invoice.invoice_id,
            "network": invoice.network.value,
            "tier_id": invoice.tier_id,
            "amount_xmr": invoice.amount_xmr,
            "address": invoice.address,
            "uri": invoice.uri,
            "status": invoice.status.value,
            "confirmations": invoice.confirmations,
        }

    @app.get("/api/payments/monero/invoices/{invoice_id}")
    def refresh_invoice(invoice_id: str, subject: str = Depends(resolve_subject)) -> dict:
        try:
            invoice = invoice_store.get(invoice_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="invoice not found") from exc
        if invoice.subject != subject:
            raise HTTPException(status_code=404, detail="invoice not found")
        try:
            invoice = payments.refresh_invoice(invoice_id)
        except MoneroRpcError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "invoice_id": invoice.invoice_id,
            "network": invoice.network.value,
            "tier_id": invoice.tier_id,
            "amount_xmr": invoice.amount_xmr,
            "address": invoice.address,
            "uri": invoice.uri,
            "status": invoice.status.value,
            "txid": invoice.txid,
            "confirmations": invoice.confirmations,
            "entitlement_granted": invoice.entitlement_granted,
            "evidence_effect": "NONE",
        }

    return app


def app_from_env() -> FastAPI:
    return create_app()
