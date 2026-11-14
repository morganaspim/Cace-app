from __future__ import annotations

import os
from pathlib import Path

from scripts.cace_runner_data_inventory import inventory_root


def test_inventory_counts_files_without_reading_contents(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    (root / "mathlib" / "Nested").mkdir(parents=True)
    (root / "mathlib" / "Nested" / "one.olean").write_bytes(b"abc")
    (root / "elan").mkdir()
    (root / "elan" / "lean").write_bytes(b"12345")

    result = inventory_root(root)

    assert result["exists"] is True
    assert result["file_count"] == 2
    assert result["total_bytes"] == 8
    assert result["top_level"]["mathlib"]["bytes"] == 3
    assert result["top_level"]["elan"]["bytes"] == 5
    assert result["truncated"] is False


def test_inventory_excludes_secret_named_paths(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    (root / "mathlib").mkdir(parents=True)
    (root / "mathlib" / "ok.olean").write_bytes(b"ok")
    (root / "credentials").mkdir()
    (root / "credentials" / "token.txt").write_text("must-not-be-in-inventory")

    result = inventory_root(root)

    assert result["file_count"] == 1
    assert result["total_bytes"] == 2
    assert all("credential" not in item["path"].lower() for item in result["largest_files"])


def test_inventory_does_not_follow_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "private.bin").write_bytes(b"outside")
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        return

    result = inventory_root(root)

    assert result["file_count"] == 0
    assert result["total_bytes"] == 0
    assert result["symlink_count"] == 1


def test_inventory_marks_truncated_walk(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    for index in range(5):
        (root / f"{index}.bin").write_bytes(b"x")

    result = inventory_root(root, max_entries=2)

    assert result["truncated"] is True
    assert any("entry limit reached" in warning for warning in result["warnings"])
