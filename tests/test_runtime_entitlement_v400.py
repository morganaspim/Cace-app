from datetime import datetime, timezone
import pytest

from cace_studio.runtime.entitlement import (
    EntitlementExpired,
    EntitlementService,
    EntitlementStore,
    InvalidLease,
    LeaseSigner,
)


def test_daily_quota_is_server_authoritative_and_fail_closed(tmp_path):
    store = EntitlementStore(tmp_path / "entitlements.sqlite3")
    signer = LeaseSigner(b"x" * 32)
    service = EntitlementService(store, signer, daily_free_seconds=10.0, max_lease_seconds=5.0)
    subject = "user-1"
    assert service.status(subject).remaining_seconds == 10.0
    store.charge(subject, 10.0, daily_free_seconds=10.0)
    assert service.status(subject).allowed is False
    with pytest.raises(EntitlementExpired):
        service.issue_lease(subject)


def test_paid_grant_is_idempotent_and_lease_is_tamper_evident(tmp_path):
    store = EntitlementStore(tmp_path / "entitlements.sqlite3")
    signer = LeaseSigner(b"y" * 32)
    service = EntitlementService(store, signer, daily_free_seconds=0.0)
    now = datetime.now(timezone.utc).timestamp()
    assert store.add_grant(
        grant_id="g1",
        subject="u",
        valid_from=now - 1,
        valid_until=now + 3600,
        compute_seconds=None,
        source="monero-stagenet:pass_24h",
        receipt_id="monero:stagenet:" + "a" * 64,
    )
    assert not store.add_grant(
        grant_id="g2",
        subject="u",
        valid_from=now - 1,
        valid_until=now + 3600,
        compute_seconds=None,
        source="monero-stagenet:pass_24h",
        receipt_id="monero:stagenet:" + "a" * 64,
    )
    token = service.issue_lease("u", requested_seconds=3)
    assert signer.verify(token).subject == "u"
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(InvalidLease):
        signer.verify(bad)
