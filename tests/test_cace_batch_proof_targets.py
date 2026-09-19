from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cace_batch_proof_targets.py"


def _module():
    spec = importlib.util.spec_from_file_location("cace_batch_proof_targets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_parser_accepts_newline_comma_and_semicolon() -> None:
    mod = _module()
    assert mod._parse(
        "CACEFormal/A.lean\nCACEFormal/B.lean, CACEFormal/C.lean;CACEFormal/D.lean"
    ) == [
        "CACEFormal/A.lean",
        "CACEFormal/B.lean",
        "CACEFormal/C.lean",
        "CACEFormal/D.lean",
    ]


def test_batch_parser_rejects_duplicate() -> None:
    mod = _module()
    with pytest.raises(Exception, match="duplicate batch target"):
        mod._parse("CACEFormal/A.lean,CACEFormal/A.lean")


def test_batch_parser_rejects_non_cace_path() -> None:
    mod = _module()
    with pytest.raises(Exception, match=r"CACEFormal/\*\.lean"):
        mod._parse("../Secret.lean")


def test_batch_manifest_requires_quarantined_standalone(monkeypatch, tmp_path: Path) -> None:
    mod = _module()
    target = tmp_path / "CACEFormal" / "Example.lean"
    target.parent.mkdir(parents=True)
    target.write_text("theorem example : True := by trivial\n", encoding="utf-8")

    monkeypatch.setattr(mod, "MODULE_ROOT", tmp_path)
    monkeypatch.setattr(mod.guard, "load_config", lambda: {})
    monkeypatch.setattr(mod.guard, "validate", lambda _config, emit=False: None)
    monkeypatch.setattr(
        mod.guard,
        "classify_target",
        lambda *_args, **_kwargs: "audited-root",
    )

    with pytest.raises(Exception, match="quarantined-standalone"):
        mod.build_manifest("CACEFormal/Example.lean")


def test_batch_manifest_content_addresses_targets(monkeypatch, tmp_path: Path) -> None:
    mod = _module()
    target = tmp_path / "CACEFormal" / "Example.lean"
    target.parent.mkdir(parents=True)
    target.write_text("theorem example : True := by trivial\n", encoding="utf-8")

    monkeypatch.setattr(mod, "MODULE_ROOT", tmp_path)
    monkeypatch.setattr(mod.guard, "load_config", lambda: {})
    monkeypatch.setattr(mod.guard, "validate", lambda _config, emit=False: None)
    monkeypatch.setattr(
        mod.guard,
        "classify_target",
        lambda *_args, **_kwargs: "quarantined-standalone",
    )

    manifest = mod.build_manifest("CACEFormal/Example.lean")
    assert manifest["target_count"] == 1
    assert manifest["targets"][0]["module"] == "CACEFormal.Example"
    assert len(manifest["targets"][0]["source_sha256"]) == 64
    assert len(manifest["targets_sha256"]) == 64
    assert manifest["qualification"] is False
