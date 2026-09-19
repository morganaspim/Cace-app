from __future__ import annotations

from pathlib import Path

from scripts.check_lean_source_sanity import (
    EXIT_CLEAN,
    EXIT_INPUT_ERROR,
    EXIT_SCAN_GUARD_FAILURE,
    EXIT_SOURCE_ISSUES,
    run_self_test,
    scan_paths,
    scan_text,
)


def _kinds(text: str) -> set[str]:
    return {item["kind"] for item in scan_text(Path("Fixture.lean"), text)}


def test_valid_source_and_nested_regular_comments_pass() -> None:
    text = """
/-- A normal doc comment. -/
theorem ok : True := by
  /- ordinary /- nested -/ comment -/
  trivial
def literal : String := "/-- not a comment inside a string"
"""
    assert scan_text(Path("Fixture.lean"), text) == []


def test_unterminated_block_comment_is_rejected() -> None:
    assert "unterminated-block-comment" in _kinds(
        "/-- broken\ntheorem x : True := by trivial\n"
    )


def test_nested_doc_comment_seam_is_rejected() -> None:
    kinds = _kinds(
        "/-- first /-- accidental second -/ theorem x : True := by trivial\n"
    )
    assert "nested-doc-comment" in kinds
    assert "unterminated-block-comment" in kinds


def test_glued_declaration_keyword_is_rejected() -> None:
    assert "glued-declaration-keyword" in _kinds(
        "noncomputable def foo : Nat := 0\n"
        "Barnoncomputable def baz : Nat := 1\n"
    )


def test_duplicate_declaration_fragment_is_rejected() -> None:
    assert "duplicated-declaration-fragment" in _kinds(
        "noncomputable def foo noncomputable def foo : Nat := 0\n"
    )


def test_mathlib_style_identifiers_are_not_false_positives() -> None:
    text = """
theorem ok : True := by
  rw [MeasureTheory.L2.inner_def]
  have h := fderiv_comp
  trivial
"""
    assert scan_text(Path("Fixture.lean"), text) == []


def test_reserved_rcases_identifier_is_rejected() -> None:
    assert "reserved-rcases-identifier" in _kinds(
        "theorem bad (p : Nat × Nat) : True := by\n"
        "  rcases p with ⟨x, by⟩\n"
        "  trivial\n"
    )


def test_escaped_safe_coordinate_name_is_not_rejected() -> None:
    text = """
theorem ok2 (p : Nat × Nat) : True := by
  rcases p with ⟨x, by_⟩
  trivial
"""
    assert scan_text(Path("Fixture.lean"), text) == []


def test_scan_paths_rejects_empty_directory(tmp_path: Path) -> None:
    report, code = scan_paths([tmp_path])
    assert code == EXIT_SCAN_GUARD_FAILURE
    assert report["status"] == "SCAN_GUARD_FAILURE"
    assert report["file_count"] == 0
    assert report["source_bundle_sha256"] is None


def test_scan_paths_rejects_missing_input_distinctly(tmp_path: Path) -> None:
    report, code = scan_paths([tmp_path / "does-not-exist"])
    assert code == EXIT_INPUT_ERROR
    assert report["status"] == "INPUT_ERROR"
    assert "not found or unsupported" in report["error"]


def test_scan_paths_requires_sentinel_membership(tmp_path: Path) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    (root / "Other.lean").write_text(
        "theorem ok : True := by trivial\n",
        encoding="utf-8",
    )
    sentinel = root / "CACEFormal.lean"
    report, code = scan_paths([root], required_sentinels=[sentinel])
    assert code == EXIT_SCAN_GUARD_FAILURE
    assert report["status"] == "SCAN_GUARD_FAILURE"
    assert sentinel.as_posix() in report["missing_sentinels"]


def test_scan_paths_clean_tree_reports_file_count_and_digest(tmp_path: Path) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    sentinel = root / "CACEFormal.lean"
    sentinel.write_text(
        "theorem root_ok : True := by trivial\n",
        encoding="utf-8",
    )
    nested = root / "Nested"
    nested.mkdir()
    (nested / "Other.lean").write_text(
        "theorem other_ok : True := by trivial\n",
        encoding="utf-8",
    )
    report, code = scan_paths([root], required_sentinels=[sentinel])
    assert code == EXIT_CLEAN
    assert report["status"] == "PASS"
    assert report["file_count"] == 2
    assert len(report["source_bundle_sha256"]) == 64
    assert report["issues"] == []


def test_scan_paths_malformed_source_has_distinct_exit_code(tmp_path: Path) -> None:
    path = tmp_path / "Broken.lean"
    path.write_text(
        "Barnoncomputable def broken : Nat := 0\n",
        encoding="utf-8",
    )
    report, code = scan_paths([path])
    assert code == EXIT_SOURCE_ISSUES
    assert report["status"] == "SOURCE_ISSUES"
    assert report["issues"]


def test_dependency_free_self_test_exercises_fail_closed_modes() -> None:
    report, code = run_self_test()
    assert code == EXIT_CLEAN
    assert report["status"] == "PASS"
    assert report["checks"]
    assert all(report["checks"].values())
