import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

import install_private as installer


def bundle(contents=None, *, manifest=None, extra_entries=()):
    contents = contents if contents is not None else {"python/tool.py": b"print('synthetic fixture')\n"}
    if manifest is None:
        manifest = {"schema": "merlin-dot-release/1",
                    "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()},
                    "source_repository": "example/engineering-fixture", "source_base_commit": "a" * 40}
    raw = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        warnings.simplefilter("ignore", UserWarning)
        for name, content in contents.items():
            archive.writestr(name, content)
        for entry, content in extra_entries:
            archive.writestr(entry, content)
        archive.writestr("manifest.json", json.dumps(manifest).encode())
    return raw.getvalue()


class UnpackVerifiedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / "release"

    def unpack(self, raw, expected=None):
        return installer.unpack_verified(raw, expected or hashlib.sha256(raw).hexdigest(), self.destination)

    def reject(self, raw, expected=None):
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.unpack(raw, expected)
        self.assertFalse(self.destination.exists(), "validation must complete before destination creation")

    def test_valid_bundle_has_exact_bytes_and_manifest(self):
        contents = {"python/tool.py": b"fixture code\n", "docs/synthetic.md": b"engineering fixture\n"}
        manifest = self.unpack(bundle(contents))
        self.assertEqual(manifest["source_repository"], "example/engineering-fixture")
        for path, raw in contents.items():
            self.assertEqual((self.destination / path).read_bytes(), raw)
        self.assertEqual(stat.S_IMODE((self.destination / "python/tool.py").stat().st_mode), 0o644)

    def test_whole_bundle_digest_mismatch_precedes_extraction(self):
        self.reject(bundle(), "f" * 64)

    def test_internal_file_tamper_precedes_extraction(self):
        manifest = {"schema": "merlin-dot-release/1", "files": {"python/tool.py": "f" * 64},
                    "source_repository": "example/fixture", "source_base_commit": "a" * 40}
        self.reject(bundle({"python/tool.py": b"changed bytes"}, manifest=manifest))

    def test_path_traversal_aliases_and_component_bounds_rejected(self):
        paths = ["../escape", "/absolute", "python/../escape", "python//tool.py",
                 "python/./tool.py", "python\\tool.py", "python/tool\n.py", "a" * 256,
                 "/".join(["deep"] * 13)]
        for path in paths:
            with self.subTest(path=path):
                self.reject(bundle({path: b"fixture"}))

    def test_file_directory_prefix_conflict_precedes_extraction(self):
        self.reject(bundle({"python": b"file", "python/tool.py": b"nested file"}))

    def test_symlink_and_fifo_entries_rejected(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO):
            info = zipfile.ZipInfo("unsafe")
            info.create_system = 3
            info.external_attr = (kind | 0o777) << 16
            manifest = {"schema": "merlin-dot-release/1", "files": {
                "python/tool.py": hashlib.sha256(b"fixture").hexdigest(),
                "unsafe": hashlib.sha256(b"target").hexdigest()},
                "source_repository": "example/fixture", "source_base_commit": "a" * 40}
            with self.subTest(kind=kind):
                self.reject(bundle({"python/tool.py": b"fixture"}, manifest=manifest,
                                   extra_entries=[(info, b"target")]))

    def test_duplicate_member_and_missing_manifest_files_rejected(self):
        raw = bundle(extra_entries=[("python/tool.py", b"duplicate")])
        self.reject(raw)
        manifest = {"schema": "merlin-dot-release/1", "files": {},
                    "source_repository": "example/fixture", "source_base_commit": "a" * 40}
        self.reject(bundle(manifest=manifest))

    def test_manifest_structure_provenance_and_digest_schema_checked(self):
        good = {"schema": "merlin-dot-release/1", "files": {"python/tool.py": "a" * 64},
                "source_repository": "example/fixture", "source_base_commit": "a" * 40}
        variants = [[], {**good, "source_base_commit": "main"},
                    {**good, "source_repository": "https://example.org/repo"},
                    {**good, "files": []}, {**good, "files": {"python/tool.py": True}},
                    {**good, "files": {"manifest.json": "a" * 64}}]
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.reject(bundle(manifest=manifest))

    def test_archive_entry_and_expansion_limits_checked(self):
        self.reject(bundle({"file%d" % i: b"x" for i in range(50)}))
        self.reject(bundle({"expanded": b"x" * (installer.MAX_EXPANDED_BYTES + 1)}))

    def test_existing_destination_never_overwritten(self):
        self.destination.mkdir()
        sentinel = self.destination / "sentinel"
        sentinel.write_text("preserve")
        with self.assertRaises(FileExistsError):
            self.unpack(bundle())
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_directory_permissions_are_independent_of_root_umask(self):
        original = os.umask(0o077)
        try:
            self.unpack(bundle({"python/nested/tool.py": b"fixture"}))
        finally:
            os.umask(original)
        for path in (self.destination, self.destination / "python", self.destination / "python/nested"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)

    def test_bounded_regular_bundle_read_and_symlink_rejection(self):
        path = self.root / "bundle.zip"
        raw = bundle()
        path.write_bytes(raw)
        self.assertEqual(installer.read_bundle(path), raw)
        link = self.root / "bundle-link.zip"
        link.symlink_to(path)
        with self.assertRaises(OSError):
            installer.read_bundle(link)
        with path.open("wb") as stream:
            stream.truncate(installer.MAX_ARCHIVE_BYTES + 1)
        with self.assertRaises(ValueError):
            installer.read_bundle(path)


if __name__ == "__main__":
    unittest.main()
