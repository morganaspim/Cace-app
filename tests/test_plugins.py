from cace_studio.app import build_registry
from cace_studio.core.plugins import discover_plugins
from pathlib import Path
import cace_studio

def test_example_plugin_loads():
    r = build_registry(); root = Path(cace_studio.__file__).parent / "plugins"
    loaded = discover_plugins(r, root)
    assert "example_plugin" in loaded and r.contains("example.negate")
