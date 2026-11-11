from __future__ import annotations

import pytest

from ops.oci_mcp.inventory_policy import (
    InventoryLimits,
    is_sensitive_relative_path,
    validate_inventory_entry,
    validate_page_request,
    validate_relative_path,
    validate_transfer_destination,
)


def test_relative_path_rejects_traversal_and_absolute_paths():
    assert validate_relative_path("actions-runner/_work/job/log.txt") == "actions-runner/_work/job/log.txt"
    for value in ("../etc/passwd", "/etc/passwd", "a/../../b", "a\\b", ""):
        with pytest.raises(ValueError):
            validate_relative_path(value)


def test_sensitive_paths_are_excluded():
    for value in (
        ".ssh/id_ed25519",
        ".oci/config",
        "repo/.env",
        "repo/secrets/prod.json",
        "repo/private-key.pem",
        "repo/api-token.txt",
        "repo/client.p12",
    ):
        assert is_sensitive_relative_path(value)
    assert not is_sensitive_relative_path("repo/README.md")


def test_inventory_entry_enforces_symlink_depth_and_size():
    assert validate_inventory_entry("repo/README.md", depth=2, size_bytes=100) == "repo/README.md"
    with pytest.raises(PermissionError):
        validate_inventory_entry("repo/link", depth=2, size_bytes=10, is_symlink=True)
    with pytest.raises(PermissionError):
        validate_inventory_entry("repo/.env", depth=2, size_bytes=10)
    with pytest.raises(ValueError):
        validate_inventory_entry("repo/deep/file", depth=9, size_bytes=10)
    with pytest.raises(ValueError):
        validate_inventory_entry("repo/large.bin", depth=2, size_bytes=300_000)


def test_limits_cannot_be_increased_beyond_policy_caps():
    assert InventoryLimits(max_entries=10).max_entries == 10
    with pytest.raises(ValueError):
        InventoryLimits(max_entries=501)
    with pytest.raises(ValueError):
        InventoryLimits(max_total_bytes=3 * 1024 * 1024)


def test_pagination_is_bounded():
    assert validate_page_request(limit=100, cursor="opaque") == "opaque"
    with pytest.raises(ValueError):
        validate_page_request(limit=501)
    with pytest.raises(ValueError):
        validate_page_request(limit=1, cursor="x" * 513)


def test_transfer_never_overwrites_existing_destination():
    assert validate_transfer_destination("inventory/manifest.json", destination_exists=False) == "inventory/manifest.json"
    with pytest.raises(FileExistsError):
        validate_transfer_destination("inventory/manifest.json", destination_exists=True)
    with pytest.raises(PermissionError):
        validate_transfer_destination("inventory/.env", destination_exists=False)
