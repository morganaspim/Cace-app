import importlib.util
from pathlib import Path
import subprocess
import sys


def test_declared_dependencies_have_license_policy_entries(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "audit_third_party_licenses.py"), "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
