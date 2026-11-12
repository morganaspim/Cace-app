from pathlib import Path
from types import SimpleNamespace

from ops.oci_mcp.runner_inventory import (
    _memory_total_bytes,
    _os_release,
    _proc_listener_state,
    collect_runner_status,
)


def test_runner_inventory_is_read_only_and_reports_local_mcp_state(tmp_path):
    (tmp_path / ".runner").write_text("registration metadata", encoding="utf-8")
    (tmp_path / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    tcp_table = tmp_path / "tcp"
    tcp6_table = tmp_path / "tcp6"
    tcp_table.write_text(
        "sl local_address rem_address st\n"
        "0: 0100007F:223D 00000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 1\n",
        encoding="ascii",
    )
    tcp6_table.write_text("sl local_address rem_address st\n", encoding="ascii")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("pgrep"):
            return SimpleNamespace(returncode=0, stdout="123\n", stderr="")
        if argv[0].endswith("systemctl") and argv[1] == "is-active":
            return SimpleNamespace(returncode=0, stdout="active\n", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "actions.runner.org-repo.host.service loaded active running Runner\n"
                "cace-oci-mcp.service loaded active running CACE MCP\n"
                "other.service loaded active running Other\n"
            ),
            stderr="",
        )

    result = collect_runner_status(
        tmp_path, run=fake_run, tcp_table=tcp_table, tcp6_table=tcp6_table
    )

    assert result["schema"] == "cace-oci-runner-inventory-v1"
    assert result["collected_at_utc"].endswith("+00:00")
    assert result["host"]["os"]
    assert result["host"]["architecture"]
    assert result["host"]["cpu_count"] >= 1
    assert result["directory_present"] is True
    assert result["registration_metadata_present"] is True
    assert result["listener_script_present"] is True
    assert result["credential_file_contents_read"] is False
    assert result["listener_process"] == "running"
    assert result["oci_mcp_service"] == "active"
    assert result["oci_mcp_listener"] == "loopback"
    assert result["github_online"] == "not_observed"
    assert result["service_units"] == [
        {
            "unit": "actions.runner.org-repo.host.service",
            "load": "loaded",
            "active": "active",
            "sub": "running",
        },
        {
            "unit": "cace-oci-mcp.service",
            "load": "loaded",
            "active": "active",
            "sub": "running",
        },
    ]
    assert calls == [
        ["/usr/bin/pgrep", "-x", "Runner.Listener"],
        ["/usr/bin/systemctl", "is-active", "--quiet", "cace-oci-mcp"],
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
    tcp_table = tmp_path / "tcp"
    tcp6_table = tmp_path / "tcp6"
    tcp_table.write_text("sl local_address rem_address st\n", encoding="ascii")
    tcp6_table.write_text("sl local_address rem_address st\n", encoding="ascii")

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    result = collect_runner_status(
        missing, run=fake_run, tcp_table=tcp_table, tcp6_table=tcp6_table
    )

    assert result["directory_present"] is False
    assert result["registration_metadata_present"] is False
    assert result["listener_process"] == "not_running"
    assert result["oci_mcp_service"] == "not_active"
    assert result["oci_mcp_listener"] == "not_listening"
    assert result["service_units"] == []
    assert result["github_online"] == "not_observed"


def test_runner_inventory_never_reads_credentials(tmp_path):
    (tmp_path / ".credentials").write_text("DO NOT READ", encoding="utf-8")

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    result = collect_runner_status(Path(tmp_path), run=fake_run)

    assert result["credential_file_contents_read"] is False
    assert "DO NOT READ" not in repr(result)


def test_host_inventory_reads_only_allowlisted_os_fields_and_aggregate_memory(tmp_path):
    release = tmp_path / "os-release"
    release.write_text(
        'ID="oracle"\nVERSION_ID="8"\nPRETTY_NAME="Oracle Linux 8"\nSECRET_TOKEN="never-return"\n',
        encoding="utf-8",
    )
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:       1024 kB\nMemFree:         128 kB\n", encoding="ascii")

    assert _os_release(release) == {
        "id": "oracle",
        "version_id": "8",
        "pretty_name": "Oracle Linux 8",
    }
    assert _memory_total_bytes(meminfo) == 1024 * 1024
    assert "never-return" not in repr(_os_release(release))


def test_host_inventory_handles_unavailable_proc_files(tmp_path):
    assert _memory_total_bytes(tmp_path / "missing") is None
    assert _os_release(tmp_path / "missing") == {}


def test_proc_listener_probe_distinguishes_non_loopback_and_loopback(tmp_path):
    tcp = tmp_path / "tcp"
    tcp6 = tmp_path / "tcp6"
    tcp.write_text(
        "sl local_address rem_address st\n"
        "0: 00000000:223D 00000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 1\n",
        encoding="ascii",
    )
    tcp6.write_text("sl local_address rem_address st\n", encoding="ascii")
    assert _proc_listener_state(tcp, tcp6) == "non_loopback"

    tcp.write_text(
        "sl local_address rem_address st\n"
        "0: 0100007F:223D 00000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 1\n",
        encoding="ascii",
    )
    assert _proc_listener_state(tcp, tcp6) == "loopback"


def test_proc_listener_probe_handles_ipv6_loopback(tmp_path):
    tcp = tmp_path / "tcp"
    tcp6 = tmp_path / "tcp6"
    tcp.write_text("sl local_address rem_address st\n", encoding="ascii")
    tcp6.write_text(
        "sl local_address rem_address st\n"
        "0: 00000000000000000000000001000000:223D 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 1\n",
        encoding="ascii",
    )
    assert _proc_listener_state(tcp, tcp6) == "loopback"


def test_proc_listener_probe_reports_unavailable_when_tables_cannot_be_read(tmp_path):
    assert _proc_listener_state(tmp_path / "missing-tcp", tmp_path / "missing-tcp6") == "unavailable"
