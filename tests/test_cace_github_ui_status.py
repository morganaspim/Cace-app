from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


live = _load("cace_github_live_check_test", SCRIPTS / "cace_github_live_check.py")
heartbeat = _load("cace_run_with_heartbeat_test", SCRIPTS / "cace_run_with_heartbeat.py")


def test_live_summary_reports_dynamic_lake_progress_without_claiming_fixed_total():
    text = live.build_summary(
        phase="h1-graph-converse",
        runner_state="running",
        run_id="123",
        run_attempt="2",
        git_commit="a" * 40,
        progress_current=2441,
        progress_total=2452,
        elapsed_seconds=5400.0,
        idle_seconds=1.0,
        last_line="[2441/2452] Building CACEFormal.H1GraphConverse",
        note=None,
    )
    assert "[2441/2452]" in text
    assert "currently discovered tasks" in text
    assert "99.6%" in text
    assert "cannot create or upgrade formal-proof qualification" in text


def test_job_status_mapping_is_fail_closed_for_display_conclusions():
    assert live._map_job_status("success") == ("completed", "success")
    assert live._map_job_status("failure") == ("completed", "failure")
    assert live._map_job_status("cancelled") == ("completed", "cancelled")
    assert live._map_job_status("timed_out") == ("completed", "timed_out")
    assert live._map_job_status("running") == ("in_progress", None)


def test_heartbeat_progress_parser_and_notice_buckets():
    match = heartbeat._PROGRESS_RE.search("[1410/1416] Building dependency")
    assert match is not None
    assert (int(match.group(1)), int(match.group(2))) == (1410, 1416)
    assert heartbeat._progress_bucket(1410, 1416) == 95
    assert heartbeat._progress_bucket(None, None) is None
    assert heartbeat._escape_workflow_command("a%\nb") == "a%25%0Ab"


def test_publish_creates_then_updates_single_check_run(tmp_path, monkeypatch):
    monkeypatch.setenv("CACE_GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")

    calls = []

    def fake_request(method, url, token, payload):
        calls.append((method, url, token, payload))
        return {"id": 456}

    monkeypatch.setattr(live, "_request", fake_request)

    assert live.publish(
        status_dir=tmp_path,
        phase="h1",
        runner_state="running",
        progress_current=10,
        progress_total=20,
    )
    assert calls[-1][0] == "POST"

    assert live.publish(
        status_dir=tmp_path,
        phase="h1",
        runner_state="running",
        progress_current=11,
        progress_total=21,
    )
    assert calls[-1][0] == "PATCH"
    assert calls[-1][1].endswith("/check-runs/456")
