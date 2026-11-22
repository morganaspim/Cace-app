"""Synthetic negative/positive contracts for isolated packaged Studio UI acceptance.

No model, download, namespace or host service is started by these tests.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_packaged_studio_smoke as studio


class FakeReply:
    def __init__(self,status,body,kind="application/json"):
        self.status=status
        self.body=body
        self.kind=kind
    def read(self,n):return self.body[:n]
    def getheader(self,name,default=""):
        return self.kind if name=="Content-Type" else default


class FakeConnection:
    def __init__(self,status=200,body=b'{"ready":true}',kind="application/json"):
        self.arguments=[]
        self.reply=FakeReply(status,body,kind)
    def request(self,*args,**kwargs):
        self.arguments.append((args,kwargs))
    def getresponse(self):return self.reply
    def close(self):pass


class PackagedStudioUIContracts(unittest.TestCase):
    def test_private_route_table_requires_only_loopback(self):
        for text in ("Iface Destination Gateway\n",
                     "Iface\tDestination\tGateway\tFlags\nlo 00000000 00000000 0001\n"):
            self.assertTrue(studio.no_external_route(text))
        for text in ("", "not a route table", "Iface Destination\n",
                     "Iface Destination Gateway\neth0 00000000 01010101\n",
                     "Iface Destination Gateway\nlo 00000000 00000000\neth0 00000000 0\n",
                     "Iface Destination Gateway\nlo\n"):
            with self.subTest(text=text):
                self.assertFalse(studio.no_external_route(text))

    def test_only_fixed_offline_api_endpoints(self):
        for method,path in (("GET","http://external.example"),
                            ("POST","/api/tool"),
                            ("POST","/api/chat"),
                            ("GET","/api/settings"),
                            ("GET","/api/conversations/../../etc/passwd")):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    studio.request(method,path)

    def test_post_requires_explicit_private_session_token(self):
        with self.assertRaises(RuntimeError):
            studio.request("POST","/api/conversations",{"title":"test"})
        with self.assertRaises(RuntimeError):
            studio.request("POST","/api/conversations",{"title":"test"},"short")

    def test_private_host_only_and_bounded_body(self):
        connection=FakeConnection()
        with patch.object(studio.http.client,"HTTPConnection",return_value=connection) as mocked:
            code,body=studio.request("GET","/api/health")
            self.assertEqual(code,200)
            self.assertEqual(body,{"ready":True})
            self.assertEqual(mocked.call_args.args[:2],("127.0.0.1",studio.PORT))
            self.assertEqual(connection.arguments[0][1]["headers"]["Host"],
                             f"127.0.0.1:{studio.PORT}")
        with self.assertRaises(RuntimeError):
            studio.request("POST","/api/conversations",{"title":"X"*3000},"x"*35)

    def test_stale_token_http_403_is_preserved(self):
        con=FakeConnection(403,b'{"error":"Reload Studio"}')
        with patch.object(studio.http.client,"HTTPConnection",return_value=con):
            code,response=studio.request("POST","/api/conversations",
                {"title":"must fail"},"z"*35)
        self.assertEqual(code,403)
        self.assertIn("error",response)

    def test_private_setup_can_observe_empty_preloopback_routes_only(self):
        self.assertFalse(studio.no_external_route(""))
        self.assertTrue(studio.no_external_route("", before_loopback=True))
        self.assertFalse(studio.no_external_route("", before_loopback=1))
        self.assertFalse(studio.no_external_route(
            "Iface Destination Gateway\neth0 00000000 01010101\n",
            before_loopback=True))

    def test_studio_mapping_root_is_only_host_uid1000(self):
        self.assertTrue(studio.rootless_uid_mapping(0,["0","1000","1"]))
        for uid,mapping in ((1000,["1000","1000","1"]),
                            (0,["0","0","1"]),
                            (0,["0","1000","2"]),
                            (True,["0","1000","1"])):
            with self.subTest(uid=uid,mapping=mapping):
                self.assertFalse(studio.rootless_uid_mapping(uid,mapping))
        cmd=studio.namespace_argv("/trusted/runner","/private/extract",
                                  "/private/scratch","/private/evidence",123)
        self.assertEqual(cmd[:4],["/usr/bin/unshare","--user","--map-root-user","--net"])
        self.assertNotIn("--map-current-user",cmd)

    def test_ui_html_still_requires_actual_html_content_type(self):
        good=FakeConnection(200,b"<html>"+b"Merlin"*300+b"</html>","text/html")
        with patch.object(studio.http.client,"HTTPConnection",return_value=good):
            code,html=studio.request("GET","/studio/")
        self.assertEqual(code,200)
        self.assertIn(b"Merlin",html)
        wrong=FakeConnection(200,b"Merlin","application/json")
        with patch.object(studio.http.client,"HTTPConnection",return_value=wrong):
            with self.assertRaises(RuntimeError):
                studio.request("GET","/studio/")

    def test_isolated_bootstrap_contains_plain_path_literals_not_posixpath_repr(self):
        # A Path substituted with %r produces PosixPath(...) which is not
        # defined in the standalone -I -S Python process.
        source=Path("/tmp/verified/Merlin_Studio")
        state=Path("/tmp/isolated-state")
        script=studio.build_bootstrap(source,state)
        self.assertIn("data_dir='/tmp/isolated-state'",script)
        self.assertNotIn("PosixPath(",script)
        self.assertNotIn("WindowsPath(",script)
        self.assertIn("network_enabled':False",script)
        self.assertIn("python_enabled':False",script)
        self.assertIn("desktop_enabled':False",script)
        self.assertIn("browser_enabled':False",script)
        compile(script,"<packaged-studio-bootstrap>","exec")

    def test_report_identity_never_claims_production(self):
        self.assertEqual(studio.SCHEMA,"merlin-packaged-studio-ui-restart/1")
        self.assertEqual(studio.PORT,18793)
        self.assertNotIn("GITHUB_TOKEN",studio.ENV)
        self.assertNotIn("PYTHONPATH",studio.ENV)


if __name__=="__main__":
    unittest.main(verbosity=2)
