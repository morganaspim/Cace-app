#!/usr/bin/env python3
"""Actual Studio, persisted offline conversation and Chromium in a private netns.

A rootless setup process activates ONLY the new namespace's loopback, then
execs this test as UID1000 with all effective caps dropped and no-new-privs.
Reject if provenance or permissions differ. No model calls or host mutations.
"""
from __future__ import annotations
import fcntl
import hashlib
import http.client
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import signal
import socket
import struct
import struct
import subprocess
import sys
import time

SCHEMA = "merlin-studio-isolated-offline-recovery/1"

def require(condition, why):
    if not condition:
        raise RuntimeError(why)

class StudioDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = self.composer = self.editor = False
        self.banner_hidden = self.setup_visible = self.help_visible = False
        self.label = self.shortcut = self.network = ""
        self.capture = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        ident = d.get("id")
        if tag == "h1" and ident == "welcome-title": self.heading = True
        if tag == "form" and ident == "composer": self.composer = True
        if tag == "textarea" and ident == "message-input": self.editor = True
        if ident == "connection-banner": self.banner_hidden = "hidden" in d
        if ident == "setup-banner": self.setup_visible = "hidden" not in d
        if ident == "offline-help": self.help_visible = "hidden" not in d
        if ident == "server-label": self.capture = "label"
        if ident == "capability-network": self.capture = "network"
        if tag == "span" and "new-shortcut" in d.get("class", "").split():
            self.capture = "shortcut"

    def handle_endtag(self, tag):
        if tag == "span": self.capture = None

    def handle_data(self, text):
        if self.capture == "label": self.label += text
        if self.capture == "shortcut": self.shortcut += text
        if self.capture == "network": self.network += text

def get(path):
    connection = http.client.HTTPConnection("127.0.0.1", 18771, timeout=2)
    try:
        connection.request("GET", path, headers={"Host": "127.0.0.1:18771"})
        response = connection.getresponse()
        body = response.read(128 * 1024 + 1)
        require(response.status == 200 and len(body) <= 128 * 1024,
                "local Studio API request rejected")
        return json.loads(body)
    finally:
        connection.close()

def post(path, value, token):
    body = json.dumps(value, ensure_ascii=False).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", 18771, timeout=3)
    try:
        connection.request("POST", path, body=body, headers={
            "Host": "127.0.0.1:18771", "X-Merlin-Token": token,
            "Content-Type": "application/json"})
        response = connection.getresponse()
        data = response.read(128 * 1024 + 1)
        require(len(data) <= 128 * 1024, "bounded POST response exceeded")
        return response.status, json.loads(data)
    finally:
        connection.close()

def isolated_interfaces():
    """Query live interfaces in this network namespace, never inherited sysfs."""
    entries = socket.if_nameindex()
    require(isinstance(entries, list) and len(entries) > 0,
            "network interface enumeration unavailable")
    indexes = [index for index, name in entries]
    names = [name for index, name in entries]
    require(all(type(index) is int and index > 0 for index in indexes)
            and all(isinstance(name, str) and name for name in names)
            and len(indexes) == len(set(indexes))
            and len(names) == len(set(names)),
            "network link identities are ambiguous")
    return sorted(names)


def require_private_network_namespace(ev):
    # Never attempt to bring up interfaces here. Only the earlier rootless
    # setup process has CAP_NET_ADMIN, and only in this fresh network ns.
    current = os.stat("/proc/self/ns/net").st_ino
    external = int(os.environ["MERLIN_PARENT_NETNS_INODE"])
    require(current != external, "network namespace is not isolated")
    mapping = Path("/proc/self/uid_map").read_text().split()
    require(mapping == ["1000", "1000", "1"], "wrong user namespace UID mapping")
    flags = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if ":" in line:
            name, value = line.split(":", 1)
            if name in ("CapEff", "NoNewPrivs"):
                flags[name] = value.strip()
    require(flags.get("CapEff") == "0000000000000000",
            "browser controller still has effective capabilities")
    require(flags.get("NoNewPrivs") == "1",
            "browser controller does not have no-new-privileges")
    # sysfs may have been mounted in the parent network namespace.
    interfaces = isolated_interfaces()
    require(interfaces == ["lo"], "network namespace has unexpected interface")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        data = struct.pack("16sH14s", b"lo", 0, b"")
        name, flags_value, pad = struct.unpack(
            "16sH14s", fcntl.ioctl(sock.fileno(), 0x8913, data))
        require(name.rstrip(b"\0") == b"lo" and (flags_value & 1),
                "isolated loopback interface is not UP")
    # Only loopback must exist; no default route is allowed.
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    require(all(not (len(row.split()) > 1 and row.split()[1] == "00000000")
                for row in routes), "unexpected network default route")
    proof = {
        "schema": "merlin-oci-rootless-netns-boundary/1",
        "parent_netns_inode": external, "child_netns_inode": current,
        "distinct_netns": True, "uid_mapping": mapping,
        "effective_capabilities_zero": True, "no_new_privs": True,
        "interfaces": interfaces,
        "interface_source": "socket.if_nameindex/current_netns",
        "only_loopback_up": True,
        "no_default_route": True, "host_network_mutation": False,
        "model_calls": 0, "production_qualified": False}
    (ev / "network-namespace-proof.json").write_text(
        json.dumps(proof, sort_keys=True, indent=2))
    return proof

def run(py, product, root, ev):
    py, product, root, ev = map(Path, (py, product, root, ev))
    require(os.geteuid() != 0 and py.is_file() and product.is_dir() and ev.is_dir(),
            "unprivileged private Studio source missing")
    # Confirm isolated network + dropped privileges before creating any state.
    require_private_network_namespace(ev)
    state = root / "studio-live-ui-state"
    state.mkdir(mode=0o700, exist_ok=False)
    profile = root / "studio-live-ui-profile"
    profile.mkdir(mode=0o700, exist_ok=False)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "HOME": str(profile), "XDG_CONFIG_HOME": str(profile),
           "XDG_CACHE_HOME": str(profile), "XDG_DATA_HOME": str(profile),
           "TMPDIR": str(root), "PYTHONDONTWRITEBYTECODE": "1",
           "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    # -I deliberately omits the script directory from sys.path; explicitly
    # bind the verified Studio package root rather than dropping isolation.
    studio_dir = product / "portable/merlin_studio"
    bootstrap = ("import sys;sys.path.insert(0,%r);"
                 "from server import main;main()" % str(studio_dir))
    def launch_server():
        return subprocess.Popen(
            [str(py), "-I", "-B", "-c", bootstrap,
             "--port", "18771", "--data-dir", str(state)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, cwd="/", start_new_session=True)
    server = launch_server()
    try:
        healthy = False
        for _ in range(55):
            require(server.poll() is None, "Studio server exited early")
            try:
                health = get("/api/health")
                healthy = health.get("ready") is True and health.get("service") == "merlin-studio"
                if healthy: break
            except (OSError, ValueError, RuntimeError): pass
            time.sleep(0.15)
        require(healthy, "Studio server did not become ready")
        status = get("/api/status")
        # Disable optional network, Python and desktop tools in this private
        # state directory before opening a browser. The token is never logged.
        settings_body = json.dumps({"network_enabled": False, "python_enabled": False,
                                    "desktop_enabled": False}).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", 18771, timeout=3)
        try:
            conn.request("POST", "/api/settings", body=settings_body, headers={
                "Host": "127.0.0.1:18771", "X-Merlin-Token": status["session_token"],
                "Content-Type": "application/json"})
            update = conn.getresponse()
            raw_settings = update.read(128 * 1024 + 1)
            require(update.status == 200 and len(raw_settings) <= 128 * 1024,
                    "isolated Studio settings hardening rejected")
        finally:
            conn.close()
        status = get("/api/status")
        require(status.get("capabilities", {}).get("network") is False,
                "Studio network tool was not disabled")
        require(status.get("version") == "0.2.0"
                and status.get("model", {}).get("configured") is False,
                "Studio backend is not the required offline configuration")
        require(isinstance(status.get("session_token"), str)
                and len(status["session_token"]) >= 32, "session token unavailable")
        require(any(x.startswith("/help") for x in status.get("offline_commands", [])),
                "offline help not available")
        # Never retain the per-launch session token in the evidence.
        (ev / "connected-backend.json").write_text(json.dumps({
            "schema": SCHEMA, "healthy": True, "version": "0.2.0",
            "token_present_but_not_retained": True, "offline_help_available": True,
            "model_configured": False, "network_tool_disabled": True,
            "external_network_isolation_verified": True,
            "production_qualified": False}, sort_keys=True, indent=2))
        # Apply actual offline commands through authenticated Studio API.
        # This uses a real, persistent conversation but no model or browser account.
        old_token = status["session_token"]
        code, created = post("/api/conversations",
                             {"title": "OCI offline replay"}, old_token)
        require(code == 201 and isinstance(created.get("conversation"), dict),
                "cannot create genuine Studio conversation")
        conversation_id = created["conversation"]["id"]
        def command(message):
            code, new_run = post("/api/chat",
                                 {"conversation_id": conversation_id,
                                  "message": message}, old_token)
            require(code == 202 and isinstance(new_run.get("run_id"), str),
                    "offline chat submission rejected")
            run_id = new_run["run_id"]
            for _ in range(100):
                data = get("/api/runs/" + run_id)
                stage = data["run"]["status"]
                if stage in ("completed", "failed", "cancelled", "interrupted"):
                    require(stage == "completed", "offline command not completed")
                    return data
                time.sleep(0.05)
            raise RuntimeError("offline command did not finish within budget")
        reference = "OCI persisted offline checkpoint"
        help_run = command("/help")
        require("Merlin Studio is ready" in json.dumps(help_run["conversation"]),
                "offline /help reply missing")
        write_run = command("/write notes/progress.txt\n" + reference)
        read_run = command("/read notes/progress.txt")
        require(reference in json.dumps(read_run["conversation"]),
                "offline read did not return the written file")
        prior = get("/api/conversations/" + conversation_id)["conversation"]
        before_count = len(prior["messages"])
        require(before_count == 6, "expected three full persisted exchanges")
        # Perform an actual backend restart, rather than merely re-opening a new client.
        server.terminate()
        try:
            prior_stdout, prior_stderr = server.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            prior_stdout, prior_stderr = server.communicate(timeout=5)
        (ev / "server-before-restart.stdout").write_bytes(prior_stdout[:65536])
        (ev / "server-before-restart.stderr").write_bytes(prior_stderr[:65536])
        require(server.poll() is not None, "old Studio server survived restart")
        server = launch_server()
        ready_after = False
        for _ in range(55):
            require(server.poll() is None, "restarted Studio server exited")
            try:
                health = get("/api/health")
                if health.get("ready") is True:
                    ready_after = True
                    break
            except (OSError, ValueError, RuntimeError):
                pass
            time.sleep(0.15)
        require(ready_after, "Studio did not start after restart")
        new_status = get("/api/status")
        new_token = new_status["session_token"]
        require(new_token != old_token, "session token did not rotate on restart")
        code, rejection = post("/api/conversations",
                               {"title": "unapproved stale token"}, old_token)
        require(code == 403, "old session credential incorrectly remained authorized")
        after = get("/api/conversations/" + conversation_id)["conversation"]
        require(len(after["messages"]) == before_count
                and reference in json.dumps(after["messages"]),
                "offline conversation history was not restored")
        code, file_result = post("/api/tool",
                                 {"tool": "read_file",
                                  "args": {"path": "notes/progress.txt"}}, new_token)
        require(code == 200
                and file_result.get("result", {}).get("content") == reference,
                "saved workspace file did not survive backend restart")
        require(new_status.get("capabilities", {}).get("network") is False
                and new_status.get("capabilities", {}).get("python") is False
                and new_status.get("capabilities", {}).get("desktop") is False,
                "disabled tool authority changed after restart")
        (ev / "offline-restart-result.json").write_text(json.dumps({
            "schema": "merlin-studio-oci-offline-restart/1", "status": "passed",
            "offline_commands_completed": 3,
            "persisted_messages": before_count, "conversation_restored": True,
            "file_restored": True, "stale_session_token_rejected": True,
            "session_token_rotated_not_retained": True,
            "optional_network_python_desktop_tools_disabled": True,
            "real_model_generation": False, "network_namespaced": True,
            "production_qualified": False,
            "test_content_sha256": hashlib.sha256(reference.encode()).hexdigest()
        }, sort_keys=True, indent=2))
        screenshot = ev / "studio-live.png"
        args = ["/usr/lib64/chromium-browser/headless_shell", "--headless",
                "--disable-gpu", "--disable-extensions", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking",
                "--disable-sync", "--disable-component-update", "--disable-dev-shm-usage",
                "--hide-scrollbars", "--window-size=1200,800",
                "--proxy-server=http=127.0.0.1:9;https=127.0.0.1:9",
                "--virtual-time-budget=5500", "--user-data-dir=" + str(profile),
                "--screenshot=" + str(screenshot), "--dump-dom",
                "http://127.0.0.1:18771/studio/"]
        child = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd="/", env=env, start_new_session=True)
        expired = False
        try:
            dom, error = child.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            expired = True
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            dom, error = child.communicate(timeout=5)
        (ev / "connected-browser.stderr").write_bytes(error[:256 * 1024])
        require(not expired and child.returncode == 0 and len(dom) < 256 * 1024
                and len(error) < 256 * 1024, "Chromium failed or exceeded limits")
        require(dom.lstrip().lower().startswith((b"<!doctype html", b"<html")),
                "Chromium did not return a DOM")
        parsed = StudioDOM()
        parsed.feed(dom.decode("utf-8", "strict"))
        require(parsed.heading and parsed.composer and parsed.editor,
                "rendered Studio interface is incomplete")
        require(parsed.banner_hidden and parsed.setup_visible and parsed.help_visible
                and "Studio 0.2.0" in parsed.label,
                "Studio did not reach the connected offline browser state")
        require("Ctrl K" in parsed.shortcut, "Studio JavaScript did not initialize")
        require("Network off" in parsed.network, "offline capability did not render")
        require(b"OCI offline replay" in dom,
                "real browser did not render the restarted conversation in the sidebar")
        require(screenshot.is_file() and 1000 < screenshot.stat().st_size < 3 * 1024 * 1024,
                "Studio screenshot missing or invalid")
        with screenshot.open("rb") as f: header = f.read(24)
        require(header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR",
                "Studio screenshot is not PNG")
        width, height = struct.unpack(">II", header[16:24])
        require(1000 <= width <= 1400 and 700 <= height <= 1000,
                "Studio screenshot dimensions differ")
        (ev / "studio-live-dom.html").write_bytes(dom)
        result = {"schema": "merlin-studio-offline-recovery-isolated/1",
                  "status": "passed_isolated_offline_restart",
                  "real_local_http_backend": True, "real_chromium_render": True,
                  "client_javascript_observed": True, "connected_server_state": True,
                  "offline_commands_completed": 3,
                  "conversation_restored_after_restart": True,
                  "saved_file_restored_after_restart": True,
                  "stale_token_rejected_after_restart": True,
                  "browser_rendered_persisted_conversation": True,
                  "offline_help_visible": True, "model_generation_calls": 0,
                  "model_configured": False, "network_namespaced": True,
                  "host_network_egress_blocked": True,
                  "network_tool_disabled": True, "fixed_browser_origin": "http://127.0.0.1:18771/studio/",
                  "browser_general_network_qualified": False,
                  "host_process_capabilities_dropped": True,
                  "network_namespace_only_loopback": True,
                  "chrome_sandbox_disabled": False, "host_installation": False,
                  "production_qualified": False, "screenshot_width": width,
                  "screenshot_height": height,
                  "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()}
        (ev / "studio-connected-result.json").write_text(json.dumps(
            result, sort_keys=True, indent=2))
        # Separate native Chromium CDP acceptance uses actual mouse and text
        # input in the same private lo-only namespace after persisted recovery.
        gui_script = Path(__file__).with_name("studio_cdp_gui.py")
        require(gui_script.is_file() and not gui_script.is_symlink(),
                "pinned CDP input controller missing")
        gui_env = dict(env)
        gui_env["MERLIN_PARENT_NETNS_INODE"] = os.environ["MERLIN_PARENT_NETNS_INODE"]
        gui = subprocess.run(
            ["/usr/bin/python3", "-I", "-B", str(gui_script), str(profile), str(ev)],
            cwd="/", env=gui_env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=72)
        (ev / "studio-cdp-wrapper.stdout").write_text(gui.stdout[:16384])
        (ev / "studio-cdp-wrapper.stderr").write_text(gui.stderr[:16384])
        require(gui.returncode == 0, "isolated Chromium CDP input test failed")
        cdp_result = json.loads((ev / "studio-cdp-gui-result.json").read_text())
        require(cdp_result.get("status") == "passed"
                and cdp_result.get("real_chromium_cdp") is True
                and cdp_result.get("real_client_input_text") == "/help"
                and cdp_result.get("offline_help_visible_after_submission") is True
                and cdp_result.get("mobile_sidebar_opened") is True
                and cdp_result.get("effective_capabilities_zero") is True
                and cdp_result.get("model_generation_calls") == 0,
                "CDP GUI receipt failed independent input requirements")
        # Verify that UI-driven submit persisted a *new* real conversation,
        # rather than accepting a fabricated DOM/fixture-only visual.
        conversations = get("/api/conversations")["conversations"]
        require(isinstance(conversations, list), "Studio conversation list missing")
        matching = [row for row in conversations if
                    isinstance(row, dict) and row.get("title") == "/help"]
        require(len(matching) == 1, "exact UI-composed conversation not stored")
        submitted = get("/api/conversations/" + matching[0]["id"])["conversation"]
        messages = submitted.get("messages", [])
        require(len(messages) == 2 and messages[0].get("role") == "user"
                and messages[0].get("content") == "/help"
                and messages[1].get("role") == "assistant"
                and "Merlin Studio is ready" in messages[1].get("content", ""),
                "backend did not persist the native Chromium UI exchange")
        result["native_cdp_real_input_gate_passed"] = True
        result["browser_gui_submit_persisted"] = True
        result["browser_mobile_sidebar_verified"] = True
        result["gui_extra_messages"] = len(messages)
        (ev / "studio-connected-result.json").write_text(
            json.dumps(result, sort_keys=True, indent=2))
        print(json.dumps({"status": "passed_isolated_offline_restart_and_cdp_gui",
                          "connected": True, "native_gui_input": True,
                          "gui_messages": len(messages), "model_calls": 0},
                         sort_keys=True))
    finally:
        if server.poll() is None: server.terminate()
        try:
            stdout, stderr = server.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            try: os.killpg(server.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            stdout, stderr = server.communicate(timeout=5)
        (ev / "studio-server.stdout").write_bytes(stdout[:65536])
        (ev / "studio-server.stderr").write_bytes(stderr[:65536])
        require(server.poll() is not None, "Studio server survived cleanup")

def main():
    if len(sys.argv) != 5:
        raise SystemExit("expected four fixed paths")
    try:
        run(*sys.argv[1:])
        return 0
    except Exception as exc:
        p = Path(sys.argv[4])
        p.mkdir(mode=0o700, exist_ok=True)
        (p / "studio-connected-failure.json").write_text(json.dumps({
            "schema": "merlin-studio-offline-recovery-isolated/1",
            "status": "blocked", "error_type": type(exc).__name__,
            "error": str(exc)[:200], "model_calls": 0,
            "production_qualified": False}, sort_keys=True, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
