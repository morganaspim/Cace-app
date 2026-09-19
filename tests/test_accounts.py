from __future__ import annotations

import pytest

from cace_studio.accounts import LocalAccountStore


def test_account_creation_assigns_separate_math_wallet_identity(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    account = store.create_account(
        display_name="Research User",
        user_type="researcher",
        declared_location="Arizona",
        location_scope="region",
        protein_library_enabled=True,
    )
    assert account.user_type == "researcher"
    assert account.declared_location == "Arizona"
    assert account.location_scope == "region"
    assert account.protein_library_enabled is True
    assert account.local_ai_math_wallet_id.startswith("MATH-AI-")
    assert "482ivJw4" not in account.local_ai_math_wallet_id


def test_location_is_optional_and_none_scope_discards_value(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    account = store.create_account(
        display_name="Basic",
        declared_location="should not persist",
        location_scope="none",
    )
    assert account.declared_location == ""


def test_session_round_trip_and_revoke(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    account = store.create_account(display_name="A")
    session = store.create_session(account.account_id, lifetime_seconds=600)
    assert store.authenticate_session(session).account_id == account.account_id
    store.revoke_session(session)
    with pytest.raises(PermissionError):
        store.authenticate_session(session)


def test_protein_storage_requires_explicit_opt_in(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    account = store.create_account(display_name="A", protein_library_enabled=False)
    protein = {
        "schema": "cace.protein-structure.v1",
        "sequence": "AG",
        "residues": [{"index": 0}, {"index": 1}],
    }
    with pytest.raises(PermissionError, match="disabled"):
        store.store_protein(account.account_id, protein)

    account = store.set_protein_library_enabled(account.account_id, True)
    assert account.protein_library_enabled is True
    saved = store.store_protein(
        account.account_id,
        protein,
        source="AlphaFold DB",
        license_id="CC-BY-4.0",
        attribution="AlphaFold Protein Structure Database",
    )
    assert saved.license_id == "CC-BY-4.0"
    listed = store.list_proteins(account.account_id)
    assert len(listed) == 1
    assert listed[0]["semantic_sha256"] == saved.semantic_sha256


def test_duplicate_email_rejected(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    store.create_account(display_name="A", email="x@example.com")
    with pytest.raises(ValueError, match="already uses"):
        store.create_account(display_name="B", email="X@example.com")


def test_invalid_location_scope_rejected(tmp_path):
    store = LocalAccountStore(tmp_path / "accounts.db")
    with pytest.raises(ValueError, match="location_scope"):
        store.create_account(
            display_name="A",
            location_scope="planet",
            declared_location="Earth",
        )
