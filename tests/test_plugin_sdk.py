from __future__ import annotations

from pathlib import Path

import pytest

from cace_studio.core.registry import ModuleRegistry
from cace_studio.plugins.sdk import (
    PLUGIN_API_VERSION,
    PluginError,
    PluginTrust,
    load_manifest,
    load_plugin_directory,
)


def test_builtin_example_plugin_manifest_and_registration() -> None:
    root = Path(__file__).resolve().parents[1]
    plugin_dir = root / "cace_studio/plugins/example_plugin"
    manifest = load_manifest(plugin_dir)
    assert manifest.api_version == PLUGIN_API_VERSION
    assert manifest.trust is PluginTrust.BUILTIN
    registry = ModuleRegistry()
    result = load_plugin_directory(plugin_dir, registry)
    assert result.module_ids == ("example.negate",)
    assert registry.contains("example.negate")


def test_manifest_rejects_unsupported_api_version(tmp_path) -> None:
    plugin_dir = tmp_path / "bad-version"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.toml").write_text(
        """[plugin]\nid='vendor.bad'\nname='Bad'\nversion='1.0'\napi_version='99.0'\nentrypoint='plugin.py'\n""",
        encoding="utf-8",
    )
    with pytest.raises(PluginError, match="targets API 99.0"):
        load_manifest(plugin_dir)


def test_untrusted_plugin_is_not_executed_by_default(tmp_path) -> None:
    plugin_dir = tmp_path / "untrusted"
    plugin_dir.mkdir()
    marker = tmp_path / "executed.txt"
    (plugin_dir / "plugin.toml").write_text(
        """[plugin]\nid='vendor.untrusted'\nname='Untrusted'\nversion='1.0'\napi_version='1.0'\nentrypoint='plugin.py'\ntrust='untrusted'\n""",
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\ndef register(registry): pass\n",
        encoding="utf-8",
    )
    with pytest.raises(PluginError, match="trust=untrusted is not allowed"):
        load_plugin_directory(plugin_dir, ModuleRegistry())
    assert not marker.exists()


def test_entrypoint_cannot_escape_plugin_directory(tmp_path) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("def register(registry): pass\n", encoding="utf-8")
    plugin_dir = tmp_path / "escape"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.toml").write_text(
        """[plugin]\nid='vendor.escape'\nname='Escape'\nversion='1.0'\napi_version='1.0'\nentrypoint='../outside.py'\ntrust='trusted'\n""",
        encoding="utf-8",
    )
    with pytest.raises(PluginError, match="entrypoint escapes plugin directory"):
        load_plugin_directory(plugin_dir, ModuleRegistry())


def test_plugin_must_register_at_least_one_module(tmp_path) -> None:
    plugin_dir = tmp_path / "empty"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.toml").write_text(
        """[plugin]\nid='vendor.empty'\nname='Empty'\nversion='1.0'\napi_version='1.0'\nentrypoint='plugin.py'\ntrust='trusted'\n""",
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text("def register(registry):\n    return None\n", encoding="utf-8")
    with pytest.raises(PluginError, match="registered no modules"):
        load_plugin_directory(plugin_dir, ModuleRegistry())


def test_failed_plugin_registration_is_transactional(tmp_path) -> None:
    plugin_dir = tmp_path / "partial"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.toml").write_text(
        """[plugin]\nid='vendor.partial'\nname='Partial'\nversion='1.0'\napi_version='1.0'\nentrypoint='plugin.py'\ntrust='trusted'\n""",
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        """from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, Maturity

class Partial(Module):
    metadata = ModuleMetadata('vendor.partial.module', 'Partial', '1.0.0', 'Test', 'Partial registration test.', Maturity.EXPERIMENTAL)
    def execute(self, inputs, params, ctx):
        return {}

def register(registry):
    registry.register(Partial)
    raise RuntimeError('boom after partial registration')
""",
        encoding="utf-8",
    )
    registry = ModuleRegistry()
    with pytest.raises(PluginError, match="registration failed"):
        load_plugin_directory(plugin_dir, registry)
    assert not registry.contains("vendor.partial.module")
    assert registry.classes() == []
