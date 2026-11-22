#!/usr/bin/env python3
"""Bounded CDP user-input test of real Merlin Studio on offline private loopback.

Only for a reviewed, already-running /studio/ service in a separate netns.
Chromium is network confined to lo with zero Linux effective capabilities.
The script never reads or emits the Studio session token, authorizes a tool,
opens an external page, contacts a model provider or installs software.
"""
from __future__ import annotations
import base64
import binascii
import zlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import struct
import subprocess
import sys
import time

CHROME = Path("/usr/lib64/chromium-browser/headless_shell")
CHROME_SHA = "22870374b6f2acfa00ac7c54a09eb30aacb1cdac932aba97e654e3dff458318f"
STUDIO = "http://127.0.0.1:18771/studio/"
PORT = 18779
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 4 * 1024 * 1024


def require(value, why):
    if not value:
        raise RuntimeError(why)



def mobile_png_sample(data, coordinates):
    """Read RGB pixels from the exact 390x844 CDP screenshot, no Pillow/network.

    Enforce PNG CRC, geometry, 8-bit RGB(A), no interlace, decompression limits,
    all five PNG row filters, and bounded pixel positions before evaluating
    a raster-contrast acceptance gate. This is visual evidence, not DOM text.
    """
    require(type(data) is bytes and len(data) <= 3 * 1024 * 1024
            and data[:8] == b"\x89PNG\r\n\x1a\n", "invalid mobile PNG bytes")
    require(type(coordinates) is tuple and 1 <= len(coordinates) <= 8,
            "invalid raster sample count")
    pos, head, chunks, ended, count = 8, None, [], False, 0
    while pos < len(data):
        require(pos + 12 <= len(data), "truncated PNG chunk header")
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        require(n <= 3 * 1024 * 1024 and pos + 12 + n <= len(data),
                "PNG chunk size rejected")
        blob = data[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0]
        require(binascii.crc32(tag + blob) & 0xffffffff == crc,
                "PNG CRC rejected")
        pos += 12 + n
        count += 1
        require(count <= 128, "PNG chunk count exceeded")
        if tag == b"IHDR":
            require(head is None and len(blob) == 13, "duplicate PNG IHDR")
            width, height, bits, color, comp, flt, interlace = struct.unpack(
                ">IIBBBBB", blob)
            require((width, height) == (390, 844) and bits == 8
                    and color in (2, 6) and comp == 0 and flt == 0
                    and interlace == 0, "unsupported mobile raster")
            head = (width, height, 3 if color == 2 else 4)
        elif tag == b"IDAT":
            require(head is not None, "PNG IDAT before IHDR")
            chunks.append(blob)
        elif tag == b"IEND":
            require(not ended and not blob and pos == len(data),
                    "invalid PNG IEND")
            ended = True
        else:
            require(tag and tag[0] & 32 != 0, "unexpected critical PNG chunk")
    require(ended and head is not None and chunks, "PNG not complete")
    width, height, bpp = head
    require(all(type(x) is int and type(y) is int and
                0 <= x < width and 0 <= y < height for x, y in coordinates),
            "raster coordinate outside screenshot")
    stride = width * bpp
    target_size = (stride + 1) * height
    inflate = zlib.decompressobj()
    raw = inflate.decompress(b"".join(chunks), target_size + 1)
    require(len(raw) == target_size and inflate.eof
            and not inflate.unused_data and not inflate.unconsumed_tail,
            "PNG decompression rejected")
    prev = bytearray(stride)
    picked = {}
    max_y = max(y for _, y in coordinates)
    for row in range(max_y + 1):
        offset = row * (stride + 1)
        mode = raw[offset]
        current = bytearray(raw[offset + 1:offset + 1 + stride])
        require(mode in (0, 1, 2, 3, 4), "PNG row filter rejected")
        if mode:
            for k in range(stride):
                left = current[k - bpp] if k >= bpp else 0
                above = prev[k]
                upperleft = prev[k - bpp] if k >= bpp else 0
                if mode == 1: predictor = left
                elif mode == 2: predictor = above
                elif mode == 3: predictor = (left + above) // 2
                else:
                    p = left + above - upperleft
                    da, db, dc = abs(p - left), abs(p - above), abs(p - upperleft)
                    predictor = (left if da <= db and da <= dc
                                 else (above if db <= dc else upperleft))
                current[k] = (current[k] + predictor) & 255
        for x, y in coordinates:
            if y == row:
                picked[(x, y)] = tuple(current[x * bpp:x * bpp + 3])
        prev = current
    return picked


def mobile_sidebar_raster_invariant(data):
    """Real visible sidebar should be brighter than its dimmed backdrop."""
    points = ((60, 430), (300, 430), (60, 600), (300, 600))
    samples = mobile_png_sample(data, points)
    contrast = [
        sum(samples[(60, row)]) - sum(samples[(300, row)])
        for row in (430, 600)
    ]
    # Exact pinned Studio CSS: sidebar #141612 stays undimmed; scrim #0008
    # darkens the page outside x=256. Earlier falsely green screenshot had
    # two negative values, while correctly rendered screenshot had +24 each.
    require(min(contrast) >= 15,
            "mobile screenshot lacks visible undimmed sidebar contrast")
    return {"schema": "merlin-oci-mobile-sidebar-raster/1",
            "samples": [{"x": x, "y": y, "rgb": list(samples[(x, y)])}
                        for x, y in points],
            "rgb_sum_contrast_by_row": contrast,
            "minimum_required_contrast": 15,
            "visible_sidebar_raster_passed": True}


def read_exact(sock, amount):
    require(0 <= amount <= MAX_FRAME, "invalid CDP read limit")
    chunks = bytearray()
    while len(chunks) < amount:
        more = sock.recv(amount - len(chunks))
        require(more, "CDP channel closed before complete message")
        chunks.extend(more)
    return bytes(chunks)


def masked_frame(payload, opcode=1):
    require(type(payload) is bytes and len(payload) <= 64 * 1024,
            "outgoing CDP payload exceeds limit")
    header = bytearray([0x80 | opcode])
    if len(payload) < 126:
        header.append(0x80 | len(payload))
    else:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", len(payload)))
    mask = os.urandom(4)
    return bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


class CDP:
    def __init__(self, sock):
        self.sock = sock
        self.next_id = 0
        self.notifications = 0

    @classmethod
    def connect(cls, ws_url):
        prefix = "ws://127.0.0.1:%d/devtools/page/" % PORT
        require(isinstance(ws_url, str) and ws_url.startswith(prefix)
                and re.fullmatch(r"[a-zA-Z0-9-]{8,128}", ws_url[len(prefix):]),
                "CDP advertised a nonlocal or unsupported endpoint")
        sock = socket.create_connection(("127.0.0.1", PORT), timeout=3)
        try:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = ("GET " + ws_url[len("ws://127.0.0.1:%d" % PORT):]
                       + " HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n" % PORT
                       + "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                       + "Sec-WebSocket-Key: " + key + "\r\nSec-WebSocket-Version: 13\r\n"
                       + "Origin: http://127.0.0.1:%d\r\n\r\n" % PORT)
            sock.sendall(request.encode("ascii"))
            header = bytearray()
            while b"\r\n\r\n" not in header and len(header) < 8192:
                data = sock.recv(2048)
                require(data, "CDP WebSocket upgrade closed")
                header.extend(data)
            require(b"\r\n\r\n" in header and len(header) < 8192,
                    "CDP upgrade response incomplete")
            lines = bytes(header).split(b"\r\n")
            require(lines[0].startswith(b"HTTP/1.1 101 "), "CDP WebSocket upgrade denied")
            fields = {}
            for line in lines[1:]:
                if b":" in line:
                    name, val = line.split(b":", 1)
                    fields[name.lower().strip()] = val.strip()
            expected = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest())
            require(fields.get(b"sec-websocket-accept") == expected,
                    "CDP WebSocket accept proof failed")
            require(bytes(header).endswith(b"\r\n\r\n"), "unexpected extra upgrade response")
            return cls(sock)
        except BaseException:
            sock.close()
            raise

    def recv_message(self):
        while True:
            first, second = read_exact(self.sock, 2)
            opcode = first & 0x0f
            require((first & 0x80) and not (first & 0x70),
                    "fragmented or reserved WebSocket frame rejected")
            size = second & 0x7f
            if size == 126:
                size = struct.unpack("!H", read_exact(self.sock, 2))[0]
            elif size == 127:
                size = struct.unpack("!Q", read_exact(self.sock, 8))[0]
            require(size <= MAX_FRAME and not (second & 0x80),
                    "invalid masked or oversized server WebSocket frame")
            body = read_exact(self.sock, size)
            if opcode == 9:
                self.sock.sendall(masked_frame(body, opcode=10))
                continue
            require(opcode == 1, "unsupported CDP server WebSocket frame")
            return json.loads(body.decode("utf-8"))

    def call(self, method, params=None, seconds=7):
        require(isinstance(method, str) and method in {
            "Page.enable", "Runtime.enable", "Runtime.evaluate",
            "Input.dispatchMouseEvent", "Input.insertText",
            "Emulation.setDeviceMetricsOverride", "Emulation.setTouchEmulationEnabled",
            "Input.dispatchTouchEvent", "Page.captureScreenshot",
        }, "CDP method not allowlisted")
        self.next_id += 1
        ident = self.next_id
        command = json.dumps({"id": ident, "method": method, "params": params or {}},
                             separators=(",", ":")).encode("utf-8")
        self.sock.sendall(masked_frame(command))
        deadline = time.monotonic() + seconds
        for _ in range(200):
            remaining = deadline - time.monotonic()
            require(remaining > 0, "CDP command expired")
            self.sock.settimeout(remaining)
            reply = self.recv_message()
            if reply.get("id") != ident:
                self.notifications += 1
                continue
            require("error" not in reply, "CDP command rejected: " + method)
            return reply.get("result", {})
        raise RuntimeError("CDP notification ceiling exceeded")

    def evaluate(self, expression):
        out = self.call("Runtime.evaluate", {"expression": expression,
                                             "returnByValue": True}, seconds=7)
        require("exceptionDetails" not in out, "browser JavaScript evaluation failed")
        return out.get("result", {}).get("value")

    def click(self, selector):
        js = "(function(){const e=document.querySelector(" + json.dumps(selector) + ");" \
             "if(!e)return null;const r=e.getBoundingClientRect();" \
             "return {x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height," \
             "hidden:getComputedStyle(e).display==='none'};})()"
        p = self.evaluate(js)
        require(isinstance(p, dict) and p["w"] > 2 and p["h"] > 2
                and not p["hidden"] and 0 <= p["x"] < 1250 and 0 <= p["y"] < 950,
                "CDP click target not visible: " + selector)
        for action in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", {"type": action, "x": p["x"],
                    "y": p["y"], "button": "left", "clickCount": 1})

    def tap(self, selector, observation_path):
        # Mobile emulation is not a physical mouse: emit a real CDP
        # touchscreen press/release at a previously hit-tested DOM control.
        target = self.evaluate("""(function(){const e=document.querySelector(""" +
          json.dumps(selector) + """);if(!e)return null;
          const r=e.getBoundingClientRect();
          const x=r.left+r.width/2,y=r.top+r.height/2;
          const at=document.elementFromPoint(x,y);
          return {x,y,w:r.width,h:r.height,
                  topButtonId:at?.closest('button')?.id??null};})()""")
        # Save a bounded coordinate/hit-test record even when blocked.
        # It contains no DOM text, storage, cookies, credentials or model data.
        safe = ({k: target.get(k) for k in ("x", "y", "w", "h", "topButtonId")}
                if isinstance(target, dict) else {"missing_target": True})
        Path(observation_path).write_text(json.dumps(safe, sort_keys=True, indent=2))
        require(isinstance(target, dict)
                and target.get("topButtonId") == selector.lstrip("#")
                and target.get("w", 0) > 2 and target.get("h", 0) > 2
                and 0 <= target.get("x", -1) < 390
                and 0 <= target.get("y", -1) < 844,
                "mobile tap target is obscured or outside viewport")
        self.call("Emulation.setTouchEmulationEnabled",
                  {"enabled": True, "maxTouchPoints": 1})
        point = {"x": target["x"], "y": target["y"], "id": 1,
                 "radiusX": 1, "radiusY": 1, "force": 1}
        self.call("Input.dispatchTouchEvent", {
            "type": "touchStart", "touchPoints": [point]})
        self.call("Input.dispatchTouchEvent", {
            "type": "touchEnd", "touchPoints": []})
        return target

    def screenshot(self, path, expected_size):
        response = self.call("Page.captureScreenshot",
                             {"format": "png", "captureBeyondViewport": False}, seconds=12)
        data = base64.b64decode(response["data"], validate=True)
        require(1000 < len(data) <= 3 * 1024 * 1024
                and data[:8] == b"\x89PNG\r\n\x1a\n"
                and data[12:16] == b"IHDR", "invalid CDP screenshot")
        width, height = struct.unpack(">II", data[16:24])
        require((width, height) == expected_size,
                "actual Chromium screenshot dimensions differ")
        path.write_bytes(data)
        return {"bytes": len(data), "width": width, "height": height,
                "sha256": hashlib.sha256(data).hexdigest()}

    def close(self):
        self.sock.close()


def list_page():
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=2)
    try:
        connection.request("GET", "/json/list", headers={"Host": "127.0.0.1:%d" % PORT})
        resp = connection.getresponse()
        body = resp.read(64 * 1024 + 1)
        require(resp.status == 200 and len(body) <= 64 * 1024,
                "CDP loopback discovery rejected")
        tabs = json.loads(body)
        require(isinstance(tabs, list) and len(tabs) < 10, "invalid CDP tab list")
        matches = [tab for tab in tabs if tab.get("type") == "page"
                   and tab.get("url") == STUDIO]
        require(len(matches) == 1, "exact local Merlin Studio page not found")
        return matches[0]["webSocketDebuggerUrl"]
    finally:
        connection.close()


def wait_for(client, expression, seconds=16, stage="unspecified"):
    end = time.monotonic() + seconds
    last_result = None
    while time.monotonic() < end:
        last_result = client.evaluate(expression)
        if last_result is True:
            return
        time.sleep(0.25)
    raise RuntimeError("browser did not reach expected DOM state: " + stage
                       + "; last_boolean=" + str(last_result is True))


def run(profile_parent, evidence):
    profile_parent, evidence = Path(profile_parent), Path(evidence)
    require(profile_parent.is_dir() and evidence.is_dir()
            and not profile_parent.is_symlink() and not evidence.is_symlink(),
            "fixed scratch and evidence folders required")
    require(os.geteuid() == 1000, "browser must be unprivileged UID 1000")
    parent_inum = int(os.environ["MERLIN_PARENT_NETNS_INODE"])
    require(os.stat("/proc/self/ns/net").st_ino != parent_inum,
            "browser must be inside distinct private network namespace")
    caps = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines()
                if ":" in line)
    require(caps.get("CapEff", "").strip() == "0000000000000000"
            and caps.get("NoNewPrivs", "").strip() == "1",
            "browser must have zero effective capabilities and no-new-privs")
    require(sorted(name for _, name in socket.if_nameindex()) == ["lo"],
            "browser has an unexpected current-namespace network interface")
    meta = CHROME.stat()
    # UID 1000 is mapped 1:1; host UID 0 is unmapped and appears as
    # overflowuid 65534 inside this rootless user namespace. Do not assert
    # host ownership against the remapped st_uid, or relax byte identity.
    uid_map = Path("/proc/self/uid_map").read_text().split()
    require(uid_map == ["1000", "1000", "1"],
            "unexpected Chromium user namespace owner mapping")
    require(CHROME.is_file() and not CHROME.is_symlink()
            and meta.st_uid == 65534 and stat.S_IMODE(meta.st_mode) == 0o755
            and meta.st_size == 221959928, "fixed Chromium executable identity differs")
    h = hashlib.sha256()
    with CHROME.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    require(h.hexdigest() == CHROME_SHA, "Chromium executable SHA-256 changed")
    profile = profile_parent / "cdp-profile"
    profile.mkdir(mode=0o700, exist_ok=False)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "HOME": str(profile), "XDG_CACHE_HOME": str(profile),
           "XDG_CONFIG_HOME": str(profile), "XDG_DATA_HOME": str(profile),
           "TMPDIR": str(profile), "PYTHONDONTWRITEBYTECODE": "1"}
    args = [str(CHROME), "--headless", "--disable-gpu", "--disable-extensions",
            "--no-first-run", "--no-default-browser-check",
            "--disable-background-networking", "--disable-sync",
            "--disable-component-update", "--disable-dev-shm-usage",
            "--hide-scrollbars", "--window-size=1200,800",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=%d" % PORT,
            "--remote-allow-origins=http://127.0.0.1:%d" % PORT,
            "--user-data-dir=" + str(profile), STUDIO]
    require(not any("--no-sandbox" in a or "--disable-web-security" in a for a in args),
            "sandbox weakening forbidden")
    stderr_file = evidence / "chromium-cdp.stderr.txt"
    with stderr_file.open("wb") as stderr:
        child = subprocess.Popen(args, cwd="/", env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=stderr,
                                 start_new_session=True)
    client = None
    try:
        ws = None
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            require(child.poll() is None, "CDP Chromium process exited before connecting")
            try:
                ws = list_page()
                break
            except (OSError, ValueError, RuntimeError, KeyError):
                time.sleep(0.2)
        require(ws is not None, "CDP Chromium loopback endpoint unavailable")
        client = CDP.connect(ws)
        client.call("Page.enable")
        client.call("Runtime.enable")
        ready = """document.getElementById('server-label')?.textContent.includes('Studio 0.2.0')===true &&
          document.getElementById('connection-banner')?.hidden===true &&
          document.getElementById('message-input')!==null"""
        wait_for(client, ready)
        client.click("#new-chat")
        client.click("#message-input")
        client.call("Input.insertText", {"text": "/help"})
        wait_for(client, "document.getElementById('message-input').value==='/help' && !document.getElementById('send-button').disabled", 5)
        client.click("#send-button")
        wait_for(client, """(function(){const m=document.getElementById('messages');
             return !!m && m.textContent.includes('/help') &&
               m.textContent.includes('Merlin Studio is ready');})()""", 18)
        # Mouse-click settings and workspace controls, not direct DOM mutations.
        client.click("#settings-nav")
        wait_for(client, "document.getElementById('settings-backdrop').hidden===false", 6)
        client.click("[data-close='settings']")
        wait_for(client, "document.getElementById('settings-backdrop').hidden===true", 5)
        client.click("#workspace-nav")
        wait_for(client, "document.getElementById('workspace-backdrop').hidden===false", 6)
        client.click("[data-close='workspace']")
        wait_for(client, "document.getElementById('workspace-backdrop').hidden===true", 5)
        desktop = client.screenshot(evidence / "studio-gui-desktop.png", (1200, 800))
        client.call("Emulation.setDeviceMetricsOverride",
                    {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        # Record only public CSS/viewport facts, not tokens or workspace data.
        metrics = client.evaluate("""(function(){const e=document.getElementById('menu-toggle');
          return {innerWidth:window.innerWidth,outerWidth:window.outerWidth,
            devicePixelRatio:window.devicePixelRatio,
            visualWidth:window.visualViewport?.width??null,
            screenWidth:screen.width,
            computedDisplay:getComputedStyle(e).display,
            cssMobileMatch:matchMedia('(max-width:760px)').matches};})()""")
        (evidence / "studio-mobile-viewport-metrics.json").write_text(
            json.dumps(metrics, sort_keys=True, indent=2))
        wait_for(client, """(function(){const e=document.getElementById('menu-toggle');
          return getComputedStyle(e).display!=='none' && window.innerWidth===390;})()""",
          5, "emulated 390px CSS viewport")
        # Desktop->mobile CSS applies a 180ms slide-out transition to the
        # sidebar. Even with the 390px media query active, this temporary
        # sidebar overlay can intercept a real mouse/touch event. Wait for a
        # DOM hit-test, not a fragile fixed sleep or synthetic JS click.
        wait_for(client, """(function(){
          const e=document.getElementById('menu-toggle');
          const r=e.getBoundingClientRect();
          const top=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
          return top?.closest('button')?.id==='menu-toggle' &&
                 !document.getElementById('sidebar').classList.contains('open');
        })()""", 5, "desktop-to-mobile sidebar transform completed")
        client.screenshot(evidence / "studio-gui-mobile-precheck.png", (390, 844))
        tapped = client.tap("#menu-toggle", evidence / "studio-mobile-tap-target.json")
        # After touch, the backdrop appears immediately but the sidebar
        # slides in for 180ms. Wait for its *visual* bounding box, not only
        # the 'open' class, before publishing the mobile screenshot.
        wait_for(client, """(function(){
          const e=document.getElementById('sidebar');
          const r=e.getBoundingClientRect();
          const hit=document.elementFromPoint(50,100);
          return e.classList.contains('open') && Math.abs(r.left)<1
                 && r.width>=250 && hit?.closest('aside')?.id==='sidebar';
        })()""", 5, "mobile sidebar visually settled and hit-testable")
        # The DOM can report the settled CSS transform before the
        # headless renderer has composited a new frame. Await two actual
        # animation frames before capturing the user-visible screenshot.
        painted = client.call("Runtime.evaluate", {
            "expression": "new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))",
            "awaitPromise": True, "returnByValue": True}, seconds=8)
        require("exceptionDetails" not in painted
                and painted.get("result", {}).get("value") is True,
                "mobile sidebar did not complete two compositor frame ticks")
        mobile = client.screenshot(evidence / "studio-gui-mobile.png", (390, 844))
        raster = mobile_sidebar_raster_invariant(
            (evidence / "studio-gui-mobile.png").read_bytes())
        raster["screenshot_sha256"] = mobile["sha256"]
        (evidence / "studio-mobile-raster-proof.json").write_text(
            json.dumps(raster, sort_keys=True, indent=2))
        result = {"schema": "merlin-oci-studio-cdp-gui/1",
                  "status": "passed", "source_page": STUDIO,
                  "real_chromium_cdp": True, "cdp_loopback_only": True,
                  "network_namespace_only_loopback": True,
                  "effective_capabilities_zero": True, "no_new_privs": True,
                  "real_client_input_text": "/help",
                  "input_method": "CDP Input.insertText, mousePressed/mouseReleased",
                  "offline_help_visible_after_submission": True,
                  "settings_dialog_open_close": True,
                  "workspace_dialog_open_close": True,
                  "mobile_sidebar_opened": True,
                  "mobile_sidebar_visual_settled": True,
                  "mobile_sidebar_raster_verified": True,
                  "mobile_input_method": "CDP Input.dispatchTouchEvent",
                  "desktop_screenshot": desktop, "mobile_screenshot": mobile,
                  "token_in_evidence": False, "model_generation_calls": 0,
                  "system_installation": False, "production_qualified": False}
        (evidence / "studio-cdp-gui-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True))
        print(json.dumps({"status": result["status"],
                          "offline_help_from_gui": True, "screenshots": 2,
                          "model_calls": 0}, sort_keys=True))
    finally:
        if client is not None:
            client.close()
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=5)
        require(child.poll() is not None, "CDP browser survived cleanup")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("exact parent profile and evidence path required")
    try:
        run(sys.argv[1], sys.argv[2])
    except BaseException as exc:
        ev = Path(sys.argv[2])
        if ev.is_dir() and not ev.is_symlink():
            (ev / "studio-cdp-gui-failure.json").write_text(json.dumps({
                "schema": "merlin-oci-studio-cdp-gui-failure/1", "status": "blocked",
                "error_type": type(exc).__name__, "message": str(exc)[:350],
                "model_calls": 0, "production_qualified": False}, sort_keys=True))
        print("studio CDP GUI blocked: " + type(exc).__name__ + ": " + str(exc),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
