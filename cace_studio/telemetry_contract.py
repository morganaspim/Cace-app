from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping


class TelemetryContractError(ValueError):
    pass


ESSENTIAL_EVENT_TYPES = {
    "instance.heartbeat",
    "service.health",
    "job.summary",
    "proof.status_summary",
    "error.summary",
    "queue.summary",
}

ESSENTIAL_ALLOWED_KEYS = {
    "release",
    "service",
    "health",
    "online",
    "resource_bucket",
    "queue_depth_bucket",
    "job_count",
    "retry_count",
    "latency_bucket",
    "error_code",
    "error_fingerprint",
    "proof_pass_count",
    "proof_fail_count",
    "proof_not_run_count",
    "feature_heartbeat_counts",
    "timestamp_bucket",
}

PRODUCT_ANALYTICS_EVENT_TYPES = {
    "feature.usage",
    "module_category.usage",
    "canvas.size_bucket",
    "session.duration_bucket",
    "heartbeat.aggregate",
    "trial.conversion",
    "compute.class",
}

PRODUCT_ALLOWED_KEYS = {
    "feature_id",
    "module_category",
    "count",
    "size_bucket",
    "duration_bucket",
    "activity_bucket",
    "compute_class",
    "latency_bucket",
    "conversion_stage",
    "country_code",
    "region_code",
    "cohort",
}

FORBIDDEN_ANY_KEYS = {
    "proof_text",
    "theorem_text",
    "equation",
    "equations",
    "prompt",
    "response",
    "protein_sequence",
    "protein_coordinates",
    "file_path",
    "filename",
    "private_key",
    "seed_phrase",
    "wallet_seed",
    "precise_location",
    "latitude",
    "longitude",
}

MAX_EVENT_BYTES = 16_384


@dataclass(frozen=True)
class TelemetryEvent:
    lane: str
    event_type: str
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }


def _validate_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, Mapping):
        return all(
            isinstance(k, str) and _validate_scalar(v)
            for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return len(value) <= 128 and all(_validate_scalar(v) for v in value)
    return False


def validate_telemetry_event(event: TelemetryEvent) -> None:
    lane = str(event.lane)
    event_type = str(event.event_type)
    payload = dict(event.payload)

    forbidden = FORBIDDEN_ANY_KEYS.intersection(payload)
    if forbidden:
        raise TelemetryContractError(
            f"telemetry payload contains forbidden fields: {sorted(forbidden)}"
        )

    if not _validate_scalar(payload):
        raise TelemetryContractError("telemetry payload must use bounded JSON-like values")

    if lane == "essential_operations":
        if event_type not in ESSENTIAL_EVENT_TYPES:
            raise TelemetryContractError("unsupported essential telemetry event type")
        unknown = set(payload) - ESSENTIAL_ALLOWED_KEYS
        if unknown:
            raise TelemetryContractError(
                f"essential telemetry contains non-allowlisted keys: {sorted(unknown)}"
            )
    elif lane == "product_analytics":
        if event_type not in PRODUCT_ANALYTICS_EVENT_TYPES:
            raise TelemetryContractError("unsupported product analytics event type")
        unknown = set(payload) - PRODUCT_ALLOWED_KEYS
        if unknown:
            raise TelemetryContractError(
                f"product analytics contains non-allowlisted keys: {sorted(unknown)}"
            )
    elif lane == "proof_research_contribution":
        raise TelemetryContractError(
            "proof/research contribution content uses a separate explicit-consent upload contract"
        )
    else:
        raise TelemetryContractError("unknown telemetry lane")

    encoded = json.dumps(
        event.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise TelemetryContractError("telemetry event exceeds maximum size")


def essential_heartbeat(
    *,
    release: str,
    health: str,
    online: bool,
    resource_bucket: str,
    job_count: int,
    feature_heartbeat_counts: Mapping[str, int] | None = None,
) -> TelemetryEvent:
    event = TelemetryEvent(
        lane="essential_operations",
        event_type="instance.heartbeat",
        payload={
            "release": str(release),
            "health": str(health),
            "online": bool(online),
            "resource_bucket": str(resource_bucket),
            "job_count": int(job_count),
            "feature_heartbeat_counts": dict(feature_heartbeat_counts or {}),
        },
    )
    validate_telemetry_event(event)
    return event


def proof_status_summary(
    *,
    passed: int,
    failed: int,
    not_run: int,
    release: str,
) -> TelemetryEvent:
    event = TelemetryEvent(
        lane="essential_operations",
        event_type="proof.status_summary",
        payload={
            "release": str(release),
            "proof_pass_count": int(passed),
            "proof_fail_count": int(failed),
            "proof_not_run_count": int(not_run),
        },
    )
    validate_telemetry_event(event)
    return event
