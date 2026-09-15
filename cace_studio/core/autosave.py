from __future__ import annotations

import os
from pathlib import Path

from .graph import Experiment
from .serialization import load_experiment, save_experiment


def default_autosave_path() -> Path:
    override = os.environ.get("CACE_AUTOSAVE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cace" / "autosave.cace"


def write_autosave(experiment: Experiment, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else default_autosave_path()
    target = target.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    save_experiment(experiment, temporary)
    temporary.replace(target)
    return target


def read_autosave(path: str | Path | None = None) -> Experiment:
    target = Path(path) if path is not None else default_autosave_path()
    return load_experiment(target.expanduser())


def autosave_exists(path: str | Path | None = None) -> bool:
    target = Path(path) if path is not None else default_autosave_path()
    return target.expanduser().is_file()
