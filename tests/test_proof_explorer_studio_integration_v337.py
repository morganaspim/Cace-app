from __future__ import annotations

import ast
from pathlib import Path


def test_app_uses_integrated_studio_window():
    source = Path("cace_studio/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "gui.studio_window"
    ]
    assert imports
    imported = {alias.name for node in imports for alias in node.names}
    assert "StudioMainWindow" in imported
    assert "StudioMainWindow(build_registry(), StudioSettings.load())" in source


def test_studio_window_keeps_proof_explorer_read_only_by_construction():
    source = Path("cace_studio/gui/studio_window.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "proof_explorer"
    ]
    called = {node.func.attr for node in calls}
    assert called <= {"show_all_claims", "show_module"}
    assert "_refresh_proof_explorer" in source
    assert "runtime_records=records" in source
