from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.check_trial_account_policy import (
    TrialAccountPolicyError,
    load_policy,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return load_policy(ROOT / "CACE_TRIAL_ACCOUNT_POLICY.json")


def test_trial_account_policy_is_valid():
    validate_policy(_policy())


def test_trial_cannot_be_reset_by_new_account():
    policy = deepcopy(_policy())
    policy["trial"]["reset_by_new_account"] = True
    with pytest.raises(TrialAccountPolicyError, match="must not reset"):
        validate_policy(policy)


def test_ransomware_like_expiry_fails_closed():
    policy = deepcopy(_policy())
    policy["expiry_behavior"]["encrypt_user_files"] = True
    with pytest.raises(TrialAccountPolicyError, match="must remain false"):
        validate_policy(policy)


def test_export_and_delete_rights_must_survive_expiry():
    policy = deepcopy(_policy())
    policy["expiry_behavior"]["allowed_after_expiry"].remove(
        "export/download owned data"
    )
    with pytest.raises(TrialAccountPolicyError, match="missing required user rights"):
        validate_policy(policy)
