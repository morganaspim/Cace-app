from __future__ import annotations
from .core.registry import ModuleRegistry
from .core.settings import StudioSettings
from .modules import register_all

def build_registry() -> ModuleRegistry:
    r=ModuleRegistry(); register_all(r); return r

def main() -> int:
    from PySide6.QtWidgets import QApplication
    from .gui.main_window import MainWindow
    app=QApplication([]); window=MainWindow(build_registry(),StudioSettings()); window.show(); return app.exec()

if __name__ == "__main__": raise SystemExit(main())
