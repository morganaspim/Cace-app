#!/usr/bin/env python3
"""One-shot actual Studio HTTP + Chromium smoke inside a fresh network namespace.

No account access, model generation, system install or production promotion.
The caller is responsible for creating the namespace and pinning this source.
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
import subprocess
import sys
import time

SCHEMA = "merlin-studio-connected-browser/1"

def require(condition, why):
    if not condition:
        raise RuntimeError(why)

class StudioDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = self.composer = self.editor = False
        self.banner_hidden = self.setup_visible = self.help_visible = False
        self.label = self.shortcut = ""
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
        if tag == "span" and "new-shortcut" in d.get("class", "").split():
            self.capture = "shortcut"

    def handle_endtag(self, tag):
        if tag == "span": self.capture = None

    def handle_data(self, text):
        if self.capture == "label": self.label += text
        if self.capture == "shortcut": self.shortcut += text

def get(path):
    connection = http.client.HTTPConnection("127.0.0.1", 8771, timeout=2)
    try:
        connection.request("GET", path, headers={"Host": "127.0.0.1:8771"})
        response = connection.getresponse()
        body = response.read(128 * 1024 + 1)
        require(response.status == 200 and len(body) <= 128 * 1024,
                "local Studio API request rejected")
        return json.loads(body)
    finally:
        connection.close()

def network_namespace_loopback():
    # This code runs only after unshare --user --map-current-user --net --fork.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        name, flags, tail = struct.unpack("16sH14s",
                                          fcntl.ioctl(sock.fileno(), 0x8913, request))
        require(name.rstrip(b"\0") == b"lo", "network namespace loopback differs")
        fcntl.ioctl(sock.fileno(), 0x8914,
                    struct.pack("16sH14s", b"lo", flags | 1, tail))

def run(py, product, root, ev):
    py, product, root, ev = map(Path, (py, product, root, ev))
    require(os.geteuid() != 0 and py.is_file() and product.is_dir() and ev.is_dir(),
            "unprivileged private Studio source missing")
    network_namespace_loopback()
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
    server = subprocess.Popen(
        [str(py), "-I", "-B", "-c", bootstrap,
         "--port", "8771", "--data-dir", str(state)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, cwd="/", start_new_session=True)
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
            "model_configured": False, "external_network": False,
            "production_qualified": False}, sort_keys=True, indent=2))
        screenshot = ev / "studio-live.png"
        args = ["/usr/lib64/chromium-browser/headless_shell", "--headless",
                "--disable-gpu", "--disable-extensions", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking",
                "--disable-sync", "--disable-component-update", "--disable-dev-shm-usage",
                "--hide-scrollbars", "--window-size=1200,800",
                "--virtual-time-budget=5500", "--user-data-dir=" + str(profile),
                "--screenshot=" + str(screenshot), "--dump-dom",
                "http://127.0.0.1:8771/studio/"]
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
        require(screenshot.is_file() and 1000 < screenshot.stat().st_size < 3 * 1024 * 1024,
                "Studio screenshot missing or invalid")
        with screenshot.open("rb") as f: header = f.read(24)
        require(header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR",
                "Studio screenshot is not PNG")
        width, height = struct.unpack(">II", header[16:24])
        require(1000 <= width <= 1400 and 700 <= height <= 1000,
                "Studio screenshot dimensions differ")
        (ev / "studio-live-dom.html").write_bytes(dom)
        result = {"schema": SCHEMA, "status": "passed",
                  "real_local_http_backend": True, "real_chromium_render": True,
                  "client_javascript_observed": True, "connected_server_state": True,
                  "offline_help_visible": True, "model_generation_calls": 0,
                  "model_configured": False, "network_namespaced": True,
                  "chrome_sandbox_disabled": False, "host_installation": False,
                  "production_qualified": False, "screenshot_width": width,
                  "screenshot_height": height,
                  "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()}
        (ev / "studio-connected-result.json").write_text(json.dumps(
            result, sort_keys=True, indent=2))
        print(json.dumps({"status": "passed", "connected": True,
                          "model_calls": 0}, sort_keys=True))
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
            "schema": SCHEMA, "status": "blocked", "error_type": type(exc).__name__,
            "error": str(exc)[:200], "model_calls": 0,
            "production_qualified": False}, sort_keys=True, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
