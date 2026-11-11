from pathlib import Path
from types import SimpleNamespace

from ops.oci_mcp.runner_inventory import collect_runner_status


def test_runner_inventory_is_read_only_and_reports_unobserved_github_state(tmp_path):
    (tmp_path / ".runner").write_text("registration metadata", encoding="utf-8")
    (tmp_path / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("pgrep"):
            return SimpleNamespace(returncode=0, stdout="123\n", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout="actions.runner.org-repo.host.service loaded active running Runner\nother.service loaded active running Other\n",
            stderr="",
        )

    result = collect_runner_status(tmp_path, run=fake_run)

    assert result["directory_present"] is True
    assert result["registration_metadata_present"] is True
    assert result["listener_script_present"] is True
    assert result["credential_file_contents_read"] is False
    assert result["listener_process"] == "running"
    assert result["github_online"] == "not_observed"
    assert result["service_units"] == [
        {
            "unit": "actions.runner.org-repo.host.service",
            "load": "loaded",
            "active": "active",
            "sub": "running",
        }
    ]
    assert calls == [
        ["/usr/bin/pgrep", "-x", "Runner.Listener"],
        [
            "/usr/bin/systemctl",
            "list-units",
            "--all",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ],
    ]


def test_runner_inventory_handles_missing_directory_and_probe_failures(tmp_path):
    missing = tmp_path / "absent"

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    result = collect_runner_status(missing, run=fake_run)

    assert result["directory_present"] is False
    assert result["registration_metadata_present"] is False
    assert result["listener_process"] == "not_running"
    assert result["service_units"] == []
    assert result["github_online"] == "not_observed"


def test_runner_inventory_never_reads_credentials(tmp_path):
    (tmp_path / ".credentials").write_text("DO NOT READ", encoding="utf-8")

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    result = collect_runner_status(Path(tmp_path), run=fake_run)

    assert result["credential_file_contents_read"] is False
    assert "DO NOT READ" not in repr(result)
