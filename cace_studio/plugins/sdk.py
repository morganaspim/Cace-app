from __future__ import annotations

import importlib.util
import re
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Iterable

from cace_studio.core.registry import ModuleRegistry

PLUGIN_API_VERSION = "1.0"
_PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class PluginError(RuntimeError):
    pass


class PluginTrust(str, Enum):
    BUILTIN = "builtin"
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    api_version: str
    entrypoint: str
    description: str = ""
    trust: PluginTrust = PluginTrust.UNTRUSTED
    capabilities: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict) -> "PluginManifest":
        section = raw.get("plugin")
        if not isinstance(section, dict):
            raise PluginError("plugin.toml must contain a [plugin] table")
        required = ("id", "name", "version", "api_version", "entrypoint")
        missing = [key for key in required if not str(section.get(key, "")).strip()]
        if missing:
            raise PluginError(f"plugin manifest missing required fields: {', '.join(missing)}")
        plugin_id = str(section["id"]).strip()
        if not _PLUGIN_ID_RE.fullmatch(plugin_id):
            raise PluginError(f"invalid plugin id: {plugin_id!r}")
        api_version = str(section["api_version"]).strip()
        if api_version != PLUGIN_API_VERSION:
            raise PluginError(
                f"plugin {plugin_id} targets API {api_version}; CACE supports {PLUGIN_API_VERSION}"
            )
        try:
            trust = PluginTrust(str(section.get("trust", "untrusted")).strip().lower())
        except ValueError as exc:
            raise PluginError(f"invalid plugin trust level: {section.get('trust')!r}") from exc
        capabilities_raw = section.get("capabilities", [])
        if not isinstance(capabilities_raw, list) or not all(isinstance(item, str) for item in capabilities_raw):
            raise PluginError("plugin capabilities must be an array of strings")
        return cls(
            plugin_id=plugin_id,
            name=str(section["name"]).strip(),
            version=str(section["version"]).strip(),
            api_version=api_version,
            entrypoint=str(section["entrypoint"]).strip(),
            description=str(section.get("description", "")).strip(),
            trust=trust,
            capabilities=tuple(sorted(set(capabilities_raw))),
        )


@dataclass(frozen=True)
class PluginLoadResult:
    manifest: PluginManifest
    module_ids: tuple[str, ...]


def load_manifest(path: str | Path) -> PluginManifest:
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "plugin.toml"
    try:
        raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PluginError(f"plugin manifest not found: {manifest_path}") from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PluginError(f"cannot read plugin manifest {manifest_path}: {exc}") from exc
    return PluginManifest.from_dict(raw)


def _load_python_entrypoint(plugin_dir: Path, manifest: PluginManifest) -> ModuleType:
    entrypoint = (plugin_dir / manifest.entrypoint).resolve()
    root = plugin_dir.resolve()
    try:
        entrypoint.relative_to(root)
    except ValueError as exc:
        raise PluginError("plugin entrypoint escapes plugin directory") from exc
    if not entrypoint.is_file() or entrypoint.suffix != ".py":
        raise PluginError(f"plugin entrypoint must be an existing Python file: {entrypoint}")
    module_name = "cace_external_plugin_" + re.sub(r"[^a-zA-Z0-9_]", "_", manifest.plugin_id)
    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if spec is None or spec.loader is None:
        raise PluginError(f"cannot import plugin entrypoint: {entrypoint}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _staging_registry(registry) -> tuple[ModuleRegistry, dict[str, type]]:
    """Create an isolated registry snapshot for all-or-nothing plugin registration."""
    before = {cls.metadata.module_id: cls for cls in registry.classes()}
    staging = ModuleRegistry()
    for cls in before.values():
        staging.register(cls)
    return staging, before


def load_plugin_directory(
    path: str | Path,
    registry,
    *,
    allow_trust: Iterable[PluginTrust] = (PluginTrust.BUILTIN, PluginTrust.TRUSTED),
) -> PluginLoadResult:
    """Load one explicitly selected plugin directory transactionally.

    Python plugins execute arbitrary code at import time. This function therefore
    refuses manifests whose trust level is not explicitly allowed by the caller.
    There is intentionally no automatic scanning/import of untrusted directories.

    Registration runs against an isolated staging registry first. The caller's
    live registry is changed only after registration completes and the staging
    registry is validated, so an exception cannot leave a half-registered plugin.
    This is transactional registry behavior, not a sandbox: trusted Python plugin
    code can still perform arbitrary process-level actions when imported/executed.
    """
    plugin_dir = Path(path)
    manifest = load_manifest(plugin_dir)
    allowed = set(allow_trust)
    if manifest.trust not in allowed:
        raise PluginError(
            f"refusing plugin {manifest.plugin_id}: trust={manifest.trust.value} is not allowed"
        )

    module = _load_python_entrypoint(plugin_dir, manifest)
    register = getattr(module, "register", None)
    if not callable(register):
        raise PluginError(f"plugin {manifest.plugin_id} entrypoint must define register(registry)")

    staging, before = _staging_registry(registry)
    try:
        register(staging)
    except Exception as exc:
        raise PluginError(f"plugin {manifest.plugin_id} registration failed: {exc}") from exc

    after = {cls.metadata.module_id: cls for cls in staging.classes()}
    for module_id, cls in before.items():
        if after.get(module_id) is not cls:
            raise PluginError(
                f"plugin {manifest.plugin_id} attempted to replace or remove existing module {module_id}"
            )

    added_ids = tuple(sorted(set(after) - set(before)))
    if not added_ids:
        raise PluginError(f"plugin {manifest.plugin_id} registered no modules")

    # Preflight the live registry before committing the staged additions. In the
    # normal single-threaded Studio/plugin-loading path these checks make the
    # subsequent register calls deterministic and non-failing.
    conflicts = [module_id for module_id in added_ids if registry.contains(module_id)]
    if conflicts:
        raise PluginError(
            f"plugin {manifest.plugin_id} conflicts with existing module ids: {', '.join(conflicts)}"
        )

    for module_id in added_ids:
        registry.register(after[module_id])

    return PluginLoadResult(manifest, added_ids)
