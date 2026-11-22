"""Non-network acceptance contracts for actual GGUF inference from extracted ZIP."""
from __future__ import annotations
import hashlib
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_packaged_model_from_zip as packaged


def elf(cpu=183):
    raw = bytearray(64)
    raw[:6] = b"\x7fELF\x02\x01"
    raw[18:20] = struct.pack("<H", cpu)
    return bytes(raw)


class PackagedModelContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "Merlin_Studio"
        (self.archive / "bin").mkdir(parents=True)
        (self.archive / "models").mkdir()
        self.binary = self.archive / "bin/llama-server"
        self.binary.write_bytes(elf())
        self.binary.chmod(0o755)
        self.model = self.archive / "models/merlin-local.gguf"
        self.model.write_bytes(b"GGUF" + b"\x00" * 60)
        self.model.chmod(0o644)
        self.binary_sha = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        self.model_sha = hashlib.sha256(self.model.read_bytes()).hexdigest()

    def check(self, **kwargs):
        params = dict(root=self.archive, binary_sha=self.binary_sha,
                      model_sha=self.model_sha, binary_size=64,
                      model_size=64)
        params.update(kwargs)
        return packaged.verify_packaged_assets(**params)

    def test_child_diagnostic_accepts_only_typed_bounded_failure(self):
        import json
        event={"status":"blocked","error_type":"RuntimeError",
               "reason":"new network namespace UID mapping differs",
               "production_qualified":False}
        raw=(json.dumps(event)+"\n").encode()
        text=packaged.failure_diagnostic(raw)
        self.assertIn("RuntimeError",text)
        self.assertIn("UID mapping",text)
        for invalid in (b"",b"secret token text",b"x"*4200,
                        b'{"status":"passed","reason":"ok"}',
                        b'{"status":"blocked","error_type":"ValueError","reason":"a","reason":"b","production_qualified":false}'):
            with self.subTest(invalid=invalid[:35]):
                self.assertEqual(packaged.failure_diagnostic(invalid),
                                 "no typed child failure evidence")

    def test_exact_packed_binary_and_model_members(self):
        report = self.check()
        self.assertEqual(report["binary"]["sha256"],self.binary_sha)
        self.assertEqual(report["model"]["sha256"],self.model_sha)
        self.assertFalse(report["model_inference_executed"])

    def test_binary_architecture_and_checksum_negative(self):
        for raw in (elf(cpu=62), b"x" * 64):
            with self.subTest(raw=raw[:6]):
                self.binary.write_bytes(raw)
                with self.assertRaises(ValueError):
                    self.check()

    def test_model_digest_and_magic_negative(self):
        for raw in (b"GGUF" + b"changed"*10, b"NOPE" + b"\x00"*60):
            with self.subTest(raw=raw[:4]):
                self.model.write_bytes(raw)
                with self.assertRaises(ValueError):
                    self.check()

    def test_link_and_writable_inputs_are_rejected(self):
        self.model.chmod(0o666)
        with self.assertRaises(ValueError):
            self.check()
        self.model.chmod(0o644)
        self.binary.unlink()
        self.binary.symlink_to(self.archive / "models/merlin-local.gguf")
        with self.assertRaises(ValueError):
            self.check()

    def test_fixed_command_only_namespaced_loopback(self):
        argv = packaged.model_argv(self.archive)
        self.assertEqual(argv[0],str(self.archive/"bin/llama-server"))
        self.assertEqual(argv[argv.index("--model")+1],
                         str(self.archive/"models/merlin-local.gguf"))
        self.assertEqual(argv[argv.index("--host")+1],"127.0.0.1")
        self.assertIn("--offline",argv)
        self.assertIn("--no-webui",argv)
        self.assertEqual(argv[argv.index("--parallel")+1],"1")
        self.assertNotIn("--no-sandbox",argv)

    def test_genuine_model_chat_shape_and_nonempty_answer(self):
        message = {"choices":[{"message":{"content":"42"}}]}
        report = packaged.assess_model_reply(message)
        self.assertTrue(report["model_inference_executed"])
        self.assertEqual(report["answer_exact_42"],True)
        self.assertEqual(report["answer_sha256"],hashlib.sha256(b"42").hexdigest())
        self.assertNotIn("answer",report)
        for malformed in ({}, {"choices":[]},
                          {"choices":[{"message":{"content":""}}]},
                          {"choices":[{"message":{"content":123}}]}):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    packaged.assess_model_reply(malformed)

    def test_no_default_route_and_loopback_only(self):
        self.assertTrue(packaged.no_default_route("Iface Destination Gateway\n"))
        self.assertTrue(packaged.no_default_route("Iface Destination Gateway\nlo 00000000 00000000\n"))
        self.assertFalse(packaged.no_default_route("Iface Destination Gateway\neth0 00000000 01020304\n"))
        self.assertFalse(packaged.no_default_route(""))
        self.assertFalse(packaged.no_default_route("not a route table"))


if __name__=="__main__":
    unittest.main(verbosity=2)
