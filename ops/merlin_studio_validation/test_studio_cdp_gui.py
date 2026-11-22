#!/usr/bin/env python3
"""Offline regressions for the bounded, loopback-only Merlin Chromium CDP client."""
import importlib.util
import binascii
import zlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

PATH = Path(__file__).with_name("studio_cdp_gui.py")
spec = importlib.util.spec_from_file_location("merlin_oci_cdp_gui_under_test", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeSocket:
    def __init__(self, data=b""):
        self.data = data
        self.sent = []
        self.timeout = 0
    def recv(self, n):
        out = self.data[:n]
        self.data = self.data[n:]
        return out
    def sendall(self, b):
        self.sent.append(b)
    def settimeout(self, v):
        self.timeout = v
    def close(self):
        pass


class CDPProtocolControls(unittest.TestCase):
    def test_client_json_frame_is_masked_and_decodable(self):
        payload = b'{"id":1,"method":"Page.enable"}'
        frame = module.masked_frame(payload)
        self.assertEqual(frame[0], 0x81)
        self.assertTrue(frame[1] & 0x80)
        self.assertEqual(frame[1] & 127, len(payload))
        mask = frame[2:6]
        self.assertEqual(bytes(ch ^ mask[i % 4] for i, ch in enumerate(frame[6:])), payload)

    def test_client_extended_length_is_bounded(self):
        payload = b"x" * 500
        frame = module.masked_frame(payload)
        self.assertEqual(frame[1], 0x80 | 126)
        self.assertEqual(struct.unpack("!H", frame[2:4])[0], len(payload))
        with self.assertRaisesRegex(RuntimeError, "exceeds limit"):
            module.masked_frame(b"x" * 65537)

    def test_server_rejects_masked_frames(self):
        wire = bytes([0x81, 0x80])
        with self.assertRaisesRegex(RuntimeError, "masked"):
            module.CDP(FakeSocket(wire)).recv_message()

    def test_server_rejects_oversized_frame_before_payload(self):
        wire = bytes([0x81, 127]) + struct.pack("!Q", module.MAX_FRAME + 1)
        with self.assertRaisesRegex(RuntimeError, "oversized"):
            module.CDP(FakeSocket(wire)).recv_message()

    def test_server_rejects_fragmentation(self):
        wire = b"\x01\x03hey"
        with self.assertRaisesRegex(RuntimeError, "fragmented"):
            module.CDP(FakeSocket(wire)).recv_message()

    def test_ping_is_answered_with_masked_pong(self):
        pong = b"\x89\x04ping"
        reply = b'\x81\x08{"id":1}'  # 8 bytes
        sock = FakeSocket(pong + reply)
        value = module.CDP(sock).recv_message()
        self.assertEqual(value, {"id": 1})
        self.assertEqual(len(sock.sent), 1)
        self.assertEqual(sock.sent[0][0], 0x8A)
        self.assertTrue(sock.sent[0][1] & 0x80)

    def test_only_documented_methods_are_allowed(self):
        client = module.CDP(FakeSocket())
        with self.assertRaisesRegex(RuntimeError, "not allowlisted"):
            client.call("Network.enable")
        with self.assertRaisesRegex(RuntimeError, "not allowlisted"):
            client.call("Browser.setPermission")

    def test_external_debug_url_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "nonlocal"):
            module.CDP.connect("ws://198.51.100.11:18779/devtools/page/12345678")
        with self.assertRaisesRegex(RuntimeError, "nonlocal"):
            module.CDP.connect("ws://127.0.0.1:18780/devtools/page/12345678")


    @staticmethod
    def mobile_png(left=(20, 22, 18), outside=(12, 13, 11), width=390, height=844):
        # Independent synthetic raster with CRC and unfiltered scanlines.
        def chunk(tag, body):
            return (struct.pack(">I", len(body)) + tag + body +
                    struct.pack(">I", binascii.crc32(tag + body) & 0xffffffff))
        header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        row = (b"\x00" + bytes(left) * 256 +
               bytes(outside) * (width - 256))
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(row * height, 6))
                + chunk(b"IEND", b""))

    def test_real_mobile_sidebar_raster_passes(self):
        result = module.mobile_sidebar_raster_invariant(self.mobile_png())
        self.assertTrue(result["visible_sidebar_raster_passed"])
        self.assertEqual(result["rgb_sum_contrast_by_row"], [24, 24])

    def test_mobile_backdrop_without_sidebar_is_rejected(self):
        dark = self.mobile_png(left=(11, 12, 10), outside=(12, 13, 11))
        with self.assertRaisesRegex(RuntimeError, "lacks visible"):
            module.mobile_sidebar_raster_invariant(dark)

    def test_mobile_png_crc_mutation_is_rejected(self):
        data = bytearray(self.mobile_png())
        data[30] ^= 1
        with self.assertRaisesRegex(RuntimeError, "CRC"):
            module.mobile_sidebar_raster_invariant(bytes(data))

    def test_mobile_png_wrong_geometry_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unsupported mobile raster"):
            module.mobile_sidebar_raster_invariant(self.mobile_png(width=391))



if __name__ == "__main__":
    unittest.main()
