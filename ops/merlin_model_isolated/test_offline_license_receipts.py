"""Local synthetic controls for immutable upstream license receipt binding.

This test never downloads licenses, models or vendor code.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_offline_native_bundle as release


class FakeReply:
    def __init__(self, url, raw):
        self.url = url
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, maximum):
        return self.raw[:maximum]


class ImmutableLicenseContract(unittest.TestCase):
    def setUp(self):
        self.url = "https://huggingface.co/example/LICENSE"
        self.good = ("Apache License\n" + "permission granted\n" * 20).encode()
        self.expected = hashlib.sha256(self.good).hexdigest()

    def test_exact_digest_and_trusted_origin_accepted(self):
        with patch.object(release.urllib.request, "urlopen",
                          return_value=FakeReply(self.url, self.good)):
            self.assertEqual(release.public_license(
                self.url, "huggingface.co", "Apache License",
                expected_sha256=self.expected), self.good)

    def test_changed_upstream_license_cannot_be_accepted_by_marker_alone(self):
        altered = self.good + b"another condition appended"
        with patch.object(release.urllib.request, "urlopen",
                          return_value=FakeReply(self.url, altered)):
            with self.assertRaisesRegex(RuntimeError, "license.*digest"):
                release.public_license(self.url, "huggingface.co", "Apache License",
                                       expected_sha256=self.expected)

    def test_empty_or_unpinned_digest_rejected(self):
        for val in ("", "z" * 64, self.expected.upper(), None):
            with self.subTest(val=val):
                with patch.object(release.urllib.request, "urlopen",
                                  return_value=FakeReply(self.url, self.good)):
                    with self.assertRaises(RuntimeError):
                        release.public_license(self.url, "huggingface.co",
                                               "Apache License", expected_sha256=val)

    def test_cross_host_redirect_rejected(self):
        with patch.object(release.urllib.request, "urlopen",
                          return_value=FakeReply("https://other.example/LICENSE", self.good)):
            with self.assertRaisesRegex(RuntimeError, "redirected"):
                release.public_license(self.url, "huggingface.co", "Apache License",
                                       expected_sha256=self.expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
