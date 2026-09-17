from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_bug_sweep_standalone_bootstraps_repository_import_root():
    """The repository sweep must not depend on an installed CACE package or PYTHONPATH."""
    proc = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "check_bug_sweep.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert "ModuleNotFoundError" not in proc.stdout + proc.stderr
    assert proc.stdout.strip(), proc.stderr
    payload = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload["status"] == "PASS"
    assert payload["error_count"] == 0
