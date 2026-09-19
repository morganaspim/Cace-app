from __future__ import annotations

import json
from pathlib import Path


class TrialAccountPolicyError(ValueError):
    pass


def load_policy(path: str | Path = "CACE_TRIAL_ACCOUNT_POLICY.json") -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TrialAccountPolicyError("trial account policy must be an object")
    return raw


def validate_policy(policy: dict) -> None:
    if policy.get("schema") != "cace.trial-account-policy.v1":
        raise TrialAccountPolicyError("unexpected trial-account policy schema")

    identity = policy.get("identity")
    trial = policy.get("trial")
    expiry = policy.get("expiry_behavior")
    anti_abuse = policy.get("anti_abuse")
    safety = policy.get("safety")
    if not all(isinstance(item, dict) for item in (identity, trial, expiry, anti_abuse, safety)):
        raise TrialAccountPolicyError("trial policy sections are incomplete")

    if identity.get("no_credit_card_required") is not True:
        raise TrialAccountPolicyError("free trial must not require a credit card")
    if trial.get("reset_by_new_account") is not False:
        raise TrialAccountPolicyError("new accounts must not reset the trial")
    if trial.get("reset_by_account_deletion") is not False:
        raise TrialAccountPolicyError("account deletion must not reset the trial")
    if trial.get("expiry_mode") != "limited":
        raise TrialAccountPolicyError("expired unlicensed trial must use limited mode")

    for field in (
        "ransomware_like_behavior",
        "encrypt_user_files",
        "delete_user_files",
        "corrupt_user_files",
        "hold_export_hostage",
        "lock_account_recovery",
    ):
        if expiry.get(field) is not False:
            raise TrialAccountPolicyError(f"{field} must remain false")

    allowed = set(expiry.get("allowed_after_expiry", []))
    required = {
        "sign in",
        "view owned experiments/results",
        "export/download owned data",
        "delete owned data",
        "account recovery/merge",
        "view help/documentation",
        "manage subscription/license",
    }
    if not required.issubset(allowed):
        raise TrialAccountPolicyError(
            f"post-trial limited mode is missing required user rights: {sorted(required-allowed)}"
        )

    if anti_abuse.get("server_side_enforcement") is not True:
        raise TrialAccountPolicyError("trial/account uniqueness must be server-side")
    if anti_abuse.get("trial_ledger_separate_from_account_row") is not True:
        raise TrialAccountPolicyError("trial ledger must be separate from account row")
    if safety.get("evidence_rule") is None:
        raise TrialAccountPolicyError("scientific evidence separation rule is required")


def main() -> int:
    validate_policy(load_policy())
    print("CACE_TRIAL_ACCOUNT_POLICY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
