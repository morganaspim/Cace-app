from __future__ import annotations

import pytest

from cace_studio.trial_entitlement import (
    DuplicatePersonAccountError,
    TrialEntitlementStore,
)


PERSON = "person_opaque_1234567890abcdef1234567890"


def test_one_person_cannot_claim_second_trial_account(tmp_path):
    store = TrialEntitlementStore(tmp_path / "trial.db")
    first = store.claim_trial(
        person_key=PERSON,
        account_id="acct-a",
        trial_seconds=7 * 24 * 3600,
        now=100.0,
    )
    assert first.account_id == "acct-a"
    with pytest.raises(DuplicatePersonAccountError, match="recover or merge"):
        store.claim_trial(
            person_key=PERSON,
            account_id="acct-b",
            trial_seconds=7 * 24 * 3600,
            now=200.0,
        )


def test_reclaim_same_account_does_not_reset_trial_clock(tmp_path):
    store = TrialEntitlementStore(tmp_path / "trial.db")
    first = store.claim_trial(
        person_key=PERSON,
        account_id="acct-a",
        trial_seconds=3600,
        now=100.0,
    )
    second = store.claim_trial(
        person_key=PERSON,
        account_id="acct-a",
        trial_seconds=3600,
        now=999.0,
    )
    assert second.trial_started_at == first.trial_started_at
    assert second.trial_expires_at == first.trial_expires_at


def test_expired_trial_is_non_destructive_limited_mode(tmp_path):
    store = TrialEntitlementStore(tmp_path / "trial.db")
    store.claim_trial(
        person_key=PERSON,
        account_id="acct-a",
        trial_seconds=3600,
        now=100.0,
    )
    result = store.permissions(PERSON, now=4000.0)
    assert result["mode"] == "limited"
    assert result["non_destructive"] is True
    assert result["permissions"]["view_owned_data"] is True
    assert result["permissions"]["export_owned_data"] is True
    assert result["permissions"]["delete_owned_data"] is True
    assert result["permissions"]["account_recovery"] is True
    assert result["permissions"]["scientific_execution"] is False
    assert result["permissions"]["network_ai_economy"] is False


def test_license_reenables_execution_without_new_account(tmp_path):
    store = TrialEntitlementStore(tmp_path / "trial.db")
    store.claim_trial(
        person_key=PERSON,
        account_id="acct-a",
        trial_seconds=3600,
        now=100.0,
    )
    store.activate_license(person_key=PERSON, now=5000.0)
    result = store.permissions(PERSON, now=6000.0)
    assert result["mode"] == "licensed"
    assert result["permissions"]["scientific_execution"] is True
    assert result["permissions"]["network_ai_economy"] is True


def test_account_recovery_moves_entitlement_without_new_trial(tmp_path):
    store = TrialEntitlementStore(tmp_path / "trial.db")
    first = store.claim_trial(
        person_key=PERSON,
        account_id="acct-old",
        trial_seconds=3600,
        now=100.0,
    )
    recovered = store.bind_recovered_account(
        person_key=PERSON,
        existing_account_id="acct-old",
        recovered_account_id="acct-recovered",
    )
    assert recovered.account_id == "acct-recovered"
    assert recovered.trial_started_at == first.trial_started_at
    assert recovered.trial_expires_at == first.trial_expires_at
