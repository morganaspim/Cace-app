from __future__ import annotations
from .core.registry import ModuleRegistry
from .core.settings import StudioSettings
from .modules import register_all
from .modules.formal_v322 import register_formal_v322
from .modules.formal_v325 import register_formal_v325
from .modules.research_dynamics import register_research_dynamics


def build_registry() -> ModuleRegistry:
    r = ModuleRegistry()
    register_all(r)
    if not r.contains("formal322.concrete_mesh_certificate_prager_synge"):
        register_formal_v322(r)
    if not r.contains("formal325.mesh_certificate_generator"):
        register_formal_v325(r)
    if not r.contains("research.growth_rotation_walk"):
        register_research_dynamics(r)
    return r


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from .gui.studio_window import StudioMainWindow

    app = QApplication([])
    window = StudioMainWindow(build_registry(), StudioSettings.load())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())