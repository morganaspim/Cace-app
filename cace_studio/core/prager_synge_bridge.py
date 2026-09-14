from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
from typing import Any


def invoke_prager_synge_checker(artifact: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    """Run the independent exact checker in a fresh subprocess.

    The invocation is deliberately independent of the caller's current working directory.
    For a source-tree checkout, the project root is injected into PYTHONPATH and used as
    the subprocess cwd. In an installed package this is harmless and the module import
    resolves through the normal environment.
    """
    project_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    old_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(project_root) + (os.pathsep + old_pythonpath if old_pythonpath else "")

    with tempfile.TemporaryDirectory(prefix="cace-ps-proof-") as td:
        p = Path(td) / "artifact.json"
        p.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n\n")
        proc = subprocess.run(
            [sys.executable, "-m", "cace_studio.formal_checker_prager_synge", "--artifact", str(p)],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        try:
            out = json.loads(proc.stdout.strip())
        except Exception:
            out = {
                "passed": False,
                "errors": ["checker did not emit valid JSON"],
                "stdout": proc.stdout,
            }
        out["process_returncode"] = proc.returncode
        out["invocation"] = "independent-subprocess"
        out["cwd_independent"] = True
        out["checker_project_root"] = str(project_root)
        out["stderr"] = proc.stderr
        return out
