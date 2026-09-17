"""Lightweight Vercel web boundary for CACE Studio.

The desktop application remains in ``cace_studio.app``. Heavy C++ computation,
Lean qualification, and attestation runners stay outside the serverless request
lifecycle.
"""

from fastapi import FastAPI


app = FastAPI(title="CACE Studio")


@app.get("/api")
def home() -> dict[str, str]:
    return {
        "service": "CACE Studio",
        "status": "ok",
        "surface": "vercel",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "CACE Studio",
        "status": "ok",
    }
