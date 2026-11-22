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
                            ("POST","/api/unapproved"),
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

    def test_model_chat_endpoint_enforces_token_and_run_id(self):
        con=FakeConnection(202,b'{"run_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}')
        with patch.object(studio.http.client,"HTTPConnection",return_value=con):
            code,result=studio.request("POST","/api/chat",
                {"conversation_id":"b"*32,"message":studio.REFERENCE_PROMPT},"t"*40)
        self.assertEqual(code,202)
        self.assertEqual(result["run_id"],"a"*32)
        self.assertEqual(con.arguments[0][1]["headers"]["X-Merlin-Token"],"t"*40)
        with self.assertRaises(RuntimeError):
            studio.request("POST","/api/chat",{"message":"6*7"})
        get=FakeConnection(200,b'{"run":{"status":"running"}}')
        with patch.object(studio.http.client,"HTTPConnection",return_value=get):
            code,result=studio.request("GET","/api/runs/"+"a"*32)
        self.assertEqual(code,200)
        self.assertEqual(result["run"]["status"],"running")
        with self.assertRaises(ValueError):
            studio.request("GET","/api/runs/../secret")

    def test_chat_evidence_requires_model_request_and_durable_answer(self):
        from hashlib import sha256
        import copy
        run_id="a"*32
        cid="b"*32
        reply={"run":{"id":run_id,"conversation_id":cid,"status":"completed",
                      "error":None,"events":[
                          {"type":"started"},{"type":"model_request","step":1},
                          {"type":"completed"}]},
               "conversation":{"id":cid,"messages":[
                   {"role":"user","content":studio.REFERENCE_PROMPT},
                   {"role":"assistant","content":"42"}]}}
        verdict=studio.assess_chat_evidence(reply,run_id,cid)
        self.assertTrue(verdict["model_chat_model_request_seen"])
        self.assertTrue(verdict["model_chat_answer_exact_42"])
        self.assertEqual(verdict["model_chat_response_sha256"],sha256(b"42").hexdigest())
        self.assertNotIn("content",verdict)
        for corrupt in (
            lambda d: d["run"].update(status="failed"),
            lambda d: d["run"].update(error="unreported failure"),
            lambda d: d["run"].update(id="c"*32),
            lambda d: d["run"].update(events=[{"type":"started"}]),
            lambda d: d["conversation"].update(id="c"*32),
            lambda d: d["conversation"]["messages"].pop(),
            lambda d: d["conversation"]["messages"][0].update(content="other"),
            lambda d: d["conversation"]["messages"][1].update(content=""),
        ):
            wrong=copy.deepcopy(reply)
            corrupt(wrong)
            with self.subTest(corrupt=repr(corrupt)):
                with self.assertRaises((ValueError,RuntimeError)):
                    studio.assess_chat_evidence(wrong,run_id,cid)
        verbose=copy.deepcopy(reply)
        verbose["conversation"]["messages"][1]["content"]="The answer is 42"
        self.assertFalse(studio.assess_chat_evidence(verbose,run_id,cid)["model_chat_answer_exact_42"])

    def test_bootstrap_model_start_is_explicit_bounded_opt_in(self):
        source=Path("/tmp/verified/Merlin_Studio")
        state=Path("/tmp/private-state")
        original=studio.build_bootstrap(source,state)
        self.assertIn("start_bundled=False",original)
        enabled=studio.build_bootstrap(source,state,start_bundled=True)
        self.assertIn("start_bundled=True",enabled)
        self.assertIn("network_enabled':False",enabled)
        self.assertIn("browser_enabled':False",enabled)
        self.assertIn("model_timeout_seconds':120",enabled)
        self.assertNotIn("PosixPath(",enabled)
        compile(enabled,"<packaged-real-chat-bootstrap>","exec")
        with self.assertRaises((ValueError,RuntimeError)):
            studio.build_bootstrap(source,state,start_bundled="yes")

    def test_private_practice_probe_detects_actual_gain_and_regression(self):
        expected=[
            ("arith.holdout.1","91"),
            ("bytes.holdout.1","12288"),
            ("titan.holdout.1","no"),
        ]
        calls=[]
        def model(text):
            calls.append(text)
            idx=(len(calls)-1)//2
            self.assertIn("New question: ",text) if len(calls)%2==0 else self.assertNotIn("Reference answer:",text)
            return "wrong" if len(calls)%2 else expected[idx][1]
        evidence=studio.practice_probe(model)
        self.assertEqual(evidence["model_calls"],6)
        self.assertEqual(evidence["baseline_correct"],0)
        self.assertEqual(evidence["guided_correct"],3)
        self.assertEqual(evidence["improved_count"],3)
        self.assertEqual(evidence["regressed_count"],0)
        self.assertFalse(evidence["model_weights_updated"])
        self.assertFalse(evidence["production_qualified"])
        bad=studio.practice_probe(lambda text:"wrong")
        self.assertEqual(bad["delta_correct"],0)
        self.assertEqual(bad["improved_count"],0)
        self.assertEqual(bad["regressed_count"],0)
        with self.assertRaises(RuntimeError):
            studio.practice_probe(lambda text:"")

    def test_private_practice_inference_uses_fixed_localhost_without_tools(self):
        reply=FakeConnection(200,b'{"choices":[{"message":{"content":"91"}}]}')
        with patch.object(studio.http.client,"HTTPConnection",return_value=reply) as conn:
            answer=studio.query_packaged_model("Compute 7 times 13")
        self.assertEqual(answer,"91")
        self.assertEqual(conn.call_args.args[:2],("127.0.0.1",8772))
        args,kwargs=reply.arguments[0]
        self.assertEqual(args[0],"POST")
        self.assertEqual(args[1],"/v1/chat/completions")
        body=json.loads(kwargs["body"])
        self.assertEqual(body["stream"],False)
        self.assertEqual(body["max_tokens"],64)
        self.assertNotIn("tools",body)
        malformed=FakeConnection(200,b'{"choices":[]}')
        with patch.object(studio.http.client,"HTTPConnection",return_value=malformed):
            with self.assertRaises(RuntimeError):
                studio.query_packaged_model("invalid response control")

    def test_report_identity_never_claims_production(self):
        self.assertEqual(studio.SCHEMA,"merlin-packaged-studio-ui-restart/1")
        self.assertEqual(studio.PORT,18793)
        self.assertNotIn("GITHUB_TOKEN",studio.ENV)
        self.assertNotIn("PYTHONPATH",studio.ENV)


if __name__=="__main__":
    unittest.main(verbosity=2)
