from __future__ import annotations
from .core.registry import ModuleRegistry
from .core.settings import StudioSettings
from .modules import register_all
from .modules.formal_v322 import register_formal_v322
from .modules.formal_v325 import register_formal_v325
from .modules.formal_hypothesis_bridges import register_formal_hypothesis_bridges
from .modules.p1_rt0_formal_bridges import register_p1_rt0_formal_bridges
from .modules.research_dynamics import register_research_dynamics
from .modules.research_geometry import register_research_geometry


def build_registry() -> ModuleRegistry:
    r = ModuleRegistry()
    register_all(r)
    if not r.contains("formal322.concrete_mesh_certificate_prager_synge"):
        register_formal_v322(r)
    if not r.contains("formal325.mesh_certificate_generator"):
        register_formal_v325(r)
    if not r.contains("formal_bridge.zero_boundary_trace_zero"):
        register_formal_hypothesis_bridges(r)
    if not r.contains("formal_bridge.p1_rt0_runtime_packet"):
        register_p1_rt0_formal_bridges(r)
    if not r.contains("research.growth_rotation_walk"):
        register_research_dynamics(r)
    if not r.contains("research.dyadic_prefix_cell"):
        register_research_geometry(r)
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
