from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_recurring_promotion_calendar_and_prices() -> None:
    promo = _load("ops/pass_promotion_policy.json")
    assert promo["schema"] == "cace-recurring-pass-promotion-v5"
    assert promo["timezone"] == "America/Phoenix"

    tue = promo["schedule"]["tuesday"]
    assert tue["cadence"] == "weekly"
    assert tue["available_durations"] == ["day"]
    assert tue["discount_percent"] == {
        "Basic": 75,
        "Researcher": 75,
        "Enterprise": 75,
    }
    assert promo["sale_prices_usd"]["tuesday_day"] == {
        "Basic": 1.25,
        "Researcher": 3.75,
        "Enterprise": 24.75,
    }

    sat = promo["schedule"]["saturday"]
    assert sat["cadence"] == "every_14_days"
    assert sat["anchor_sale_date"] == "2026-09-26"
    assert sat["available_durations"] == ["week"]
    assert sat["discount_percent"] == {
        "Basic": 50,
        "Researcher": 60,
        "Enterprise": 75,
    }
    assert promo["sale_prices_usd"]["alternating_saturday_week"] == {
        "Basic": 7.50,
        "Researcher": 19.60,
        "Enterprise": 99.75,
    }

    month = promo["schedule"]["quarterly_month"]
    assert month["cadence"] == "every_3_months"
    assert month["anchor_sale_date"] == "2026-12-20"
    assert month["available_durations"] == ["month"]
    assert month["discount_percent"] == {
        "Basic": 45,
        "Researcher": 45,
        "Enterprise": 45,
    }
    assert promo["sale_prices_usd"]["quarterly_month"] == {
        "Basic": 21.45,
        "Researcher": 81.95,
        "Enterprise": 824.45,
    }

    year = promo["schedule"]["triennial_year"]
    assert year["cadence"] == "every_3_years"
    assert year["anchor_sale_date"] == "2027-01-01"
    assert year["available_durations"] == ["year"]
    assert year["discount_percent"] == {
        "Basic": 50,
        "Researcher": 50,
        "Enterprise": 50,
    }
    assert year["active_local_window"] == {
        "start": "00:00:00",
        "end": "23:59:59.999",
    }
    assert promo["sale_prices_usd"]["triennial_year"] == {
        "Basic": 99.50,
        "Researcher": 499.50,
        "Enterprise": 4999.50,
    }
    assert "first verified payment sighting" in year["purchase_window_rule"]


def test_base44_tier_manifest_uses_same_promotion_policy() -> None:
    tiers = _load("ops/base44_account_tiers.json")
    policy = tiers["recurring_pass_promotion"]
    assert (
        policy["policy_id"]
        == "tuesday_day_alt_saturday_week_quarterly_month_triennial_year_v5"
    )
    assert policy["tuesday"]["discount_percent_by_tier"] == {
        "Basic": 75,
        "Researcher": 75,
        "Enterprise": 75,
    }
    assert policy["quarterly_month"]["discount_percent_by_tier"] == {
        "Basic": 45,
        "Researcher": 45,
        "Enterprise": 45,
    }
    assert policy["triennial_year"]["discount_percent_by_tier"] == {
        "Basic": 50,
        "Researcher": 50,
        "Enterprise": 50,
    }


def test_monero_payment_unlock_is_server_verified_and_non_custodial() -> None:
    payment = _load("ops/monero_payment_policy.json")
    assert payment["asset"] == "XMR"
    assert payment["cloud_run"]["wallet_seed_allowed"] is False
    assert payment["cloud_run"]["wallet_spend_key_allowed"] is False
    assert payment["cloud_run"]["monero_wallet_files_allowed"] is False
    assert payment["verifier"]["minimum_confirmations_default"] == 10
    assert payment["fulfillment"]["infer_product_from_amount"] is False
    assert payment["fulfillment"]["overpayment_upgrades_tier"] is False
    assert payment["fulfillment"]["underpayment_unlocks"] is False
    assert (
        payment["quote"]["catalog_rule"]["triennial_year"]["anchor_sale_date"]
        == "2027-01-01"
    )
    assert (
        payment["entitlement_grant"]["private_key_holder"]
        == "Cloud Run payment service secret only"
    )
    assert "Oracle/CACE entitlement verifier" in payment[
        "entitlement_grant"
    ]["public_key_consumers"]


def test_cloud_run_payment_use_remains_cost_capped() -> None:
    cost = _load("ops/cloud_run_cost_guard.json")
    payment_exception = cost["payment_exception"]
    assert payment_exception["classification"] == "MONERO_PAYMENT_CRITICAL"
    assert payment_exception["permitted"] is True
    assert payment_exception["still_requires_explicit_production_enable"] is True
    assert payment_exception["still_requires_monthly_budget"] is True
    assert payment_exception["min_instances"] == 0
    assert payment_exception["max_instances"] == 1
    assert payment_exception["wallet_custody"] is False
    assert cost["traffic_policy"]["only_payment_routes_allowed"] is True
    assert cost["traffic_policy"]["general_cace_routes_allowed"] is False

    service = _load("ops/cloud_run_payment_service_policy.json")
    assert service["sole_production_responsibility"] == "MONERO_PAYMENT_COORDINATION"
    assert service["wallet_custody"]["wallet_seed_allowed"] is False
    assert service["wallet_custody"]["wallet_spend_key_allowed"] is False
    assert service["wallet_custody"]["persistent_wallet_files_allowed"] is False
    assert service["cost_guard"]["min_instances"] == 0
    assert service["cost_guard"]["max_instances"] == 1
    assert service["cost_guard"]["gpu"] is False

    tombstone = _load("ops/cloud_run_edge_policy.json")
    assert tombstone["status"] == "DEPRECATED_COMPATIBILITY_ALIAS"
    assert tombstone["canonical_policy"] == "ops/cloud_run_payment_service_policy.json"
    assert "web hosting" in tombstone["disabled_uses"]


def test_payment_entitlement_schema_is_narrow() -> None:
    schema = _load("schema/cace-payment-entitlement-grant.schema.json")
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {
        "grant_id",
        "principal_id",
        "order_id",
        "payment_id",
        "sku",
        "tier",
        "features",
        "valid_from",
        "issued_at",
        "policy_version",
    }.issubset(required)
