from dataclasses import dataclass

@dataclass
class StudioSettings:
    ai_enabled: bool = True
    gpu_enabled: bool = False
    assistant_mode: str = "research"
