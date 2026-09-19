from __future__ import annotations

from pathlib import Path

from scripts.check_lean_source_sanity import scan_text


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
    assert "unterminated-block-comment" in _kinds("/-- broken\ntheorem x : True := by trivial\n")


def test_nested_doc_comment_seam_is_rejected() -> None:
    kinds = _kinds("/-- first /-- accidental second -/ theorem x : True := by trivial\n")
    assert "nested-doc-comment" in kinds
    assert "unterminated-block-comment" in kinds


def test_glued_declaration_keyword_is_rejected() -> None:
    assert "glued-declaration-keyword" in _kinds(
        "noncomputable def foo : Nat := 0\nBarnoncomputable def baz : Nat := 1\n"
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
