"""Synthetic exact-source safety controls for packaged ARM64 inference executable."""
from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_offline_native_bundle import probe_packaged_llama


def synthetic_elf(cpu=183):
    buffer = bytearray(64)
    buffer[:6] = b"\x7fELF\x02\x01"
    buffer[18:20] = struct.pack("<H", cpu)
    return bytes(buffer)


class PackagedExecutableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        directory = self.root / "Merlin_Studio/bin"
        directory.mkdir(parents=True)
        self.binary = directory / "llama-server"
        self.binary.write_bytes(synthetic_elf())
        self.binary.chmod(0o755)
        self.digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()

    def probe(self, **override):
        args = {
            "archive_root": self.root / "Merlin_Studio",
            "expected_sha256": self.digest,
            "expected_bytes": 64,
            "runner": lambda argv, **kwargs: b"llama version synthetic\n",
        }
        args.update(override)
        return probe_packaged_llama(**args)

    def test_exact_pinned_aarch64_executable_invocation(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv,kwargs))
            return b"llama version synthetic\n"
        report = self.probe(runner=runner)
        self.assertTrue(report["native_llama_binary_started"])
        self.assertFalse(report["model_inference_executed"])
        self.assertEqual(report["llama_sha256"],self.digest)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],[str(self.binary), "--version"])
        self.assertEqual(calls[0][1]["timeout"],20)

    def test_binary_mutated_or_architecture_wrong_rejected_before_launch(self):
        called = []
        for value in (synthetic_elf(cpu=62), b"not-elf" + b"x" * 57):
            with self.subTest(value=value[:8]):
                self.binary.write_bytes(value)
                self.binary.chmod(0o755)
                with self.assertRaises(ValueError):
                    self.probe(runner=lambda *a,**k: called.append(True))
        self.assertEqual(called,[])

    def test_symlink_and_unsafe_mode_rejected_before_launch(self):
        self.binary.unlink()
        other = self.root / "other"
        other.write_bytes(synthetic_elf())
        self.binary.symlink_to(other)
        with self.assertRaises(ValueError):
            self.probe()
        self.binary.unlink()
        self.binary.write_bytes(synthetic_elf())
        self.binary.chmod(0o777)
        with self.assertRaises(ValueError):
            self.probe()

    def test_empty_version_output_is_not_a_success(self):
        with self.assertRaises(ValueError):
            self.probe(runner=lambda argv,**kwargs: b"")

    def test_nonstandard_archive_root_does_not_escape(self):
        with self.assertRaises(ValueError):
            self.probe(archive_root=self.root)


if __name__=="__main__":
    unittest.main(verbosity=2)
