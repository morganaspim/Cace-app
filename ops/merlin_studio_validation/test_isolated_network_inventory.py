#!/usr/bin/env python3
"""Regression controls for namespace-aware interface checks in OCI Studio."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
MODULES = ("prepare_isolated_loopback", "connected_browser_offline_recovery_isolated")


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    if spec is None or spec.loader is None:
        raise AssertionError("fixed isolation source not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NamespaceInterfaceRegression(unittest.TestCase):
    def setUp(self):
        self.modules = [load(name) for name in MODULES]

    def test_host_sysfs_is_not_consulted_when_only_lo_is_present(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with patch.object(module.socket, "if_nameindex", return_value=[(1, "lo")]), \
                     patch.object(module.os, "listdir", side_effect=AssertionError("host-mounted sysfs consulted")):
                    self.assertEqual(module.isolated_interfaces(), ["lo"])

    def test_extra_namespace_link_is_not_suppressed(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with patch.object(module.socket, "if_nameindex", return_value=[(2, "eth0"), (1, "lo")]):
                    self.assertEqual(module.isolated_interfaces(), ["eth0", "lo"])
                    with self.assertRaisesRegex(RuntimeError, "unexpected network interface"):
                        module.require(module.isolated_interfaces() == ["lo"],
                                       "new namespace has unexpected network interface")

    def test_duplicate_names_are_rejected(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with patch.object(module.socket, "if_nameindex", return_value=[(1, "lo"), (2, "lo")]):
                    with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                        module.isolated_interfaces()

    def test_duplicate_indexes_are_rejected(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with patch.object(module.socket, "if_nameindex", return_value=[(1, "lo"), (1, "test0")]):
                    with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                        module.isolated_interfaces()

    def test_no_namespace_links_is_rejected(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with patch.object(module.socket, "if_nameindex", return_value=[]):
                    with self.assertRaisesRegex(RuntimeError, "unavailable"):
                        module.isolated_interfaces()

    def test_invalid_interface_identifiers_fail_closed(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                for bad in [[(0, "lo")], [(1, "")], [(True, "lo")]]:
                    with patch.object(module.socket, "if_nameindex", return_value=bad):
                        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                            module.isolated_interfaces()


if __name__ == "__main__":
    unittest.main()
