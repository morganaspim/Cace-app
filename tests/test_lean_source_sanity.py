from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts.check_lean_source_sanity import scan_text


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_lean_source_sanity.py"


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


def test_cli_self_test_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--self-test"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"status": "PASS"' in proc.stdout


def test_cli_require_sentinel_accepts_file_inside_scan(tmp_path: Path) -> None:
    root = tmp_path / "formal"
    root.mkdir()
    sentinel = root / "Sentinel.lean"
    sentinel.write_text("theorem ok : True := by trivial\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--require-sentinel",
            str(sentinel),
            str(root),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cli_require_sentinel_rejects_file_outside_scan(tmp_path: Path) -> None:
    scanned = tmp_path / "scanned"
    outside = tmp_path / "outside"
    scanned.mkdir()
    outside.mkdir()
    (scanned / "Inside.lean").write_text(
        "theorem inside : True := by trivial\n",
        encoding="utf-8",
    )
    sentinel = outside / "Sentinel.lean"
    sentinel.write_text("theorem outside : True := by trivial\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--require-sentinel",
            str(sentinel),
            str(scanned),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "missing-required-sentinel" in proc.stdout
