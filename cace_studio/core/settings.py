from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

AI_MODES = ("hints", "teacher", "researcher", "autonomous")


def _default_settings_path() -> Path:
    override = os.environ.get("CACE_SETTINGS_PATH")
    return Path(override).expanduser() if override else Path.home() / ".cace" / "settings.json"


@dataclass
class StudioSettings:
    ai_enabled: bool = False
    gpu_enabled: bool = False
    assistant_mode: str = "researcher"
    ai_provider: str = "ollama"
    ai_endpoint: str = "http://127.0.0.1:11434"
    ai_model: str = ""
    ai_generally_useful: bool = False

    @classmethod
    def load(cls, path: str | Path | None = None) -> "StudioSettings":
        target = Path(path).expanduser() if path is not None else _default_settings_path()
        if not target.exists():
            return cls()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        allowed = {field.name for field in fields(cls)}
        values = {key: value for key, value in raw.items() if key in allowed}
        settings = cls(**values)
        if settings.assistant_mode not in AI_MODES:
            settings.assistant_mode = "researcher"
        return settings

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path).expanduser() if path is not None else _default_settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(target)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return target
