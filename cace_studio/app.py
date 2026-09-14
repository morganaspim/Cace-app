from __future__ import annotations
from .core.registry import ModuleRegistry
from .core.settings import StudioSettings
from .modules import register_all
from .modules.formal_v322 import register_formal_v322
from .modules.formal_v325 import register_formal_v325

def build_registry() -> ModuleRegistry:
    r=ModuleRegistry(); register_all(r)
    if not r.contains("formal322.concrete_mesh_certificate_prager_synge"):
        register_formal_v322(r)
    if not r.contains("formal325.mesh_certificate_generator"):
        register_formal_v325(r)
    return r

def main() -> int:
    from PySide6.QtWidgets import QApplication
    from .gui.main_window import MainWindow
    app=QApplication([]); window=MainWindow(build_registry(),StudioSettings()); window.show(); return app.exec()

if __name__ == "__main__": raise SystemExit(main())
