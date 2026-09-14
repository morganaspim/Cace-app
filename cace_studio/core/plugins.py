from __future__ import annotations
from importlib import import_module
from pathlib import Path
import sys
from .registry import ModuleRegistry

def discover_plugins(registry: ModuleRegistry, root: str | Path) -> list[str]:
    root = Path(root); loaded: list[str] = []
    if not root.exists(): return loaded
    sys.path.insert(0, str(root.parent))
    try:
        for folder in sorted(root.iterdir()):
            if folder.is_dir() and (folder / "__init__.py").exists():
                mod = import_module(f"{root.name}.{folder.name}")
                register = getattr(mod, "register", None)
                if callable(register):
                    register(registry); loaded.append(folder.name)
    finally:
        try: sys.path.remove(str(root.parent))
        except ValueError: pass
    return loaded
