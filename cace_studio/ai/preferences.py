from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


AI_RESEARCH_MODES = ("hints", "teacher", "researcher", "general", "autonomous")


def _default_preferences_path() -> Path:
    override = os.environ.get("CACE_AI_RESEARCH_PREFS_PATH")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".cace" / "ai_research_preferences.json"
    )


@dataclass
class AIResearchPreferences:
    """Preferences for experimental/local AI research features.

    This file deliberately lives outside cace_studio.core.settings so UI/AI
    preference changes do not alter the formally qualified core surface.
    """

    assistant_mode: str = ""
    embedding_model: str = ""
    growth_chaos: float = 0.18
    growth_budget: int = 10
    growth_max_group_size: int = 4

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AIResearchPreferences":
        target = (
            Path(path).expanduser()
            if path is not None
            else _default_preferences_path()
        )
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
        preferences = cls(**values)
        if preferences.assistant_mode not in ("", *AI_RESEARCH_MODES):
            preferences.assistant_mode = ""
        preferences.embedding_model = str(preferences.embedding_model).strip()
        try:
            preferences.growth_chaos = min(
                0.85, max(0.0, float(preferences.growth_chaos))
            )
        except (TypeError, ValueError):
            preferences.growth_chaos = 0.18
        try:
            preferences.growth_budget = min(
                32, max(1, int(preferences.growth_budget))
            )
        except (TypeError, ValueError):
            preferences.growth_budget = 10
        try:
            preferences.growth_max_group_size = min(
                4, max(2, int(preferences.growth_max_group_size))
            )
        except (TypeError, ValueError):
            preferences.growth_max_group_size = 4
        return preferences

    def effective_mode(self, fallback: str = "researcher") -> str:
        mode = self.assistant_mode or str(fallback)
        return mode if mode in AI_RESEARCH_MODES else "researcher"

    def save(self, path: str | Path | None = None) -> Path:
        target = (
            Path(path).expanduser()
            if path is not None
            else _default_preferences_path()
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp.replace(target)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return target
