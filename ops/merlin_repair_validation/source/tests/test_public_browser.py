"""Contract/integrity regressions. Fake pages do not establish native rendering."""
import base64
from dataclasses import replace
import http.client
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from dot_ai_os.bridge import DotContextBridge

from merlin.browser_egress import FetchResult, PublicHTTPTransport, canonical, recv_frame, unique_json
from merlin.browser_ingest import publish_episode, validate_episode
from merlin.browser_policy import BrowserLimits, BrowserPolicyError, public_ip, public_url, search_url, utf8_range
from merlin.browser_service import BrowserService, validate_request
from merlin.project_registry import MerlinRegistry
from merlin.public_browser import BrowserController, EpisodeRecorder, renderer_isolation, run_episode, validate_action

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=')
ENGINE={'name':'chromium','chromium_sandbox':True,'browser_version':'synthetic-unit-fixture-not-native-proof'}
ISOLATION={'uid':982,'euid':982,'interfaces':['lo'],'effective_capabilities':0,'no_new_privileges':True,'direct_external_network':False}


class WireSocket:
    def __init__(self,wire): self.wire=wire
    def makefile(self,*args,**kwargs): return io.BytesIO(self.wire)
    def settimeout(self,value): pass


class Connection:
    def __init__(self,wire):
        self.sock=WireSocket(wire);self.response=http.client.HTTPResponse(self.sock);self.response.begin()
        self.headers=None;self.closed=False
    def request(self,method,target,headers): self.headers=headers;self.method=method;self.target=target
    def getresponse(self): return self.response
    def close(self): self.closed=True


def dns(ip='93.184.216.34'):
    return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))]


class PolicyTests(unittest.TestCase):
    def test_private_metadata_credentials_and_chatgpt_urls_are_denied(self):
        for value in ('http://127.0.0.1/','http://10.2.3.4/','http://169.254.169.254/opc/v2/',
                      'http://[::1]/','http://[::ffff:127.0.0.1]/','http://localhost/',
                      'https://user:secret@example.org/','https://chatgpt.com/','https://foo.chatgpt.com/',
                      'https://chat.openai.com/','https://chat.com/','file:///etc/passwd',
                      'javascript:alert(1)','https://example.org:8443/','https://example.org\\@127.0.0.1/'):
            with self.subTest(value=value),self.assertRaises(BrowserPolicyError): public_url(value)

    def test_general_public_sources_and_query_identity_are_preserved(self):
        for value in ('https://github.com/python/cpython','https://pubmed.ncbi.nlm.nih.gov/?term=browser',
                      'https://news.un.org/en/','http://example.org/a?b=2','https://docs.openai.com/'):
            self.assertEqual(public_url(value),value)
        self.assertEqual(public_url('https://example.org/search?q=梅林&x=%2F'),
                         'https://example.org/search?q=%E6%A2%85%E6%9E%97&x=%2F')

    def test_ipv6_multicast_reserved_translation_and_mixed_public_are_denied(self):
        for value in ('ff02::1','ff0e::1','4000::1','64:ff9b::a00:1','2002:7f00:1::','100.64.0.1'):
            with self.subTest(value=value),self.assertRaises(BrowserPolicyError): public_ip(value)
        self.assertEqual(public_ip('2606:4700:4700::1111'),'2606:4700:4700::1111')

    def test_search_is_general_bounded_get_template(self):
        self.assertEqual(search_url('exact rank','https://example.org/?q={query}'),
                         'https://example.org/?q=exact%20rank')
        for template in ('https://chatgpt.com/?q={query}','https://example.org/{query}/{query}'):
            with self.assertRaises(BrowserPolicyError): search_url('test',template)

    def test_invalid_limits_and_unsafe_actions_fail(self):
        for kwargs in ({'max_actions':True},{'wall_seconds':61},{'max_evidence_bytes':131071},
                       {'request_seconds':10,'action_seconds':5}):
            with self.assertRaises(BrowserPolicyError): BrowserLimits(**kwargs)
        for action in ({'action':'evaluate','code':'arbitrary'},{'action':'open','url':'https://example.org/','cookies':[]},
                       {'action':'scroll','delta_y':True},{'action':'read','start_byte':-1}):
            with self.assertRaises(BrowserPolicyError): validate_action(action)

    def test_duplicate_protocol_fields_and_oversized_frame_fail(self):
        with self.assertRaises(BrowserPolicyError): unique_json(b'{"x":1,"x":2}')
        channel=SimpleNamespace(recv=io.BytesIO(b'\x00\x01\x00\x00').read)
        with self.assertRaises(BrowserPolicyError): recv_frame(channel,100)

    def test_utf8_range_never_moves_backwards_or_stalls(self):
        raw='字X'.encode()
        with self.assertRaises(BrowserPolicyError): utf8_range(raw,0,1)
        self.assertEqual(utf8_range(raw,1,1),(3,4,b'X'))
        self.assertEqual(utf8_range(raw,0,3),(0,3,'字'.encode()))


class TransportTests(unittest.TestCase):
    def build(self,wire,limits=None,resolver=None):
        connection=Connection(wire);calls=[]
        def connect(*args): calls.append(args);return connection
        transport=PublicHTTPTransport(limits,resolver=resolver or (lambda *a,**k:dns()),connector=connect)
        return transport,connection,calls

    def test_dns_is_checked_once_and_exact_numeric_address_is_connected(self):
        resolutions=[]
        def resolver(*args,**kwargs): resolutions.append(args);return dns()
        transport,connection,calls=self.build(b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc',resolver=resolver)
        result=transport.fetch('https://example.org/hello?q=x')
        self.assertEqual(result.body,b'abc');self.assertEqual(len(resolutions),1)
        self.assertEqual(calls[0][:4],('example.org','93.184.216.34',443,True))
        self.assertEqual(connection.target,'/hello?q=x');self.assertTrue(connection.closed)

    def test_mixed_dns_answers_private_redirect_and_non_get_fail(self):
        transport,_,calls=self.build(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n',resolver=lambda *a,**k:dns()+dns('10.0.0.1'))
        with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/')
        self.assertEqual(calls,[])
        transport,connection,_=self.build(b'HTTP/1.1 302 Found\r\nLocation: http://169.254.169.254/\r\nContent-Length: 0\r\n\r\n')
        with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/')
        self.assertTrue(connection.closed)
        with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/','POST')

    def test_truncated_content_length_is_not_a_successful_capture(self):
        transport,connection,_=self.build(b'HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\nabc')
        with self.assertRaisesRegex(BrowserPolicyError,'incomplete declared'): transport.fetch('https://example.org/')
        self.assertEqual(transport.bytes,3);self.assertTrue(connection.closed)

    def test_partial_chunked_failures_spend_persistent_episode_budget(self):
        wire=b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n6\r\n'
        connections=[]
        def connector(*args):
            item=Connection(wire);connections.append(item);return item
        transport=PublicHTTPTransport(replace(BrowserLimits(),max_network_bytes=4),
            resolver=lambda *a,**k:dns(),connector=connector)
        with self.assertRaises(http.client.IncompleteRead): transport.fetch('https://example.org/')
        self.assertEqual(transport.bytes,3)
        with self.assertRaises((http.client.IncompleteRead,BrowserPolicyError)): transport.fetch('https://example.org/')
        self.assertEqual(transport.bytes,5)  # One bounded detection byte, never refunded.
        with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/')
        self.assertEqual(len(connections),2)

    def test_secret_headers_and_duplicate_identity_headers_do_not_escape(self):
        for header in ('Authorization','Cookie','Proxy-Authorization','X-API-Key'):
            transport,_,calls=self.build(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
            with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/',headers={header:'synthetic'})
            self.assertEqual(calls,[])
        transport,connection,_=self.build(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nSet-Cookie: secret=synthetic\r\n\r\n')
        result=transport.fetch('https://example.org/',headers={'user-agent':'fixture','accept':'text/html'})
        self.assertEqual(connection.headers,{'user-agent':'fixture','accept':'text/html','accept-encoding':'identity'})
        self.assertNotIn('set-cookie',result.headers)

    def test_overlarge_response_and_duplicate_lengths_fail_closed(self):
        for wire in (b'HTTP/1.1 200 OK\r\nContent-Length: 9000000\r\n\r\n',
                     b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n'):
            transport,connection,_=self.build(wire)
            with self.assertRaises(BrowserPolicyError): transport.fetch('https://example.org/')
            self.assertTrue(connection.closed)


class FakeTransport:
    def __init__(self): self.bytes=0;self.requests=0
    def fetch(self,url,method='GET',headers=None):
        raw=b'<!doctype html><title>Unit fixture</title><body>source text</body>'
        self.bytes+=len(raw);self.requests+=1
        return FetchResult(url,200,{'content-type':'text/html'},raw,'93.184.216.34',url.startswith('https:'))


class FakeContext:
    def route(self,pattern,callback): self.callback=callback
    def route_web_socket(self,*args): pass
    def on(self,*args): pass


class FakeRoute:
    def __init__(self,page,url,*,failure=False,main=True):
        self.request=SimpleNamespace(url=url,method='GET',headers={},resource_type='document' if main else 'image',
                                     frame=page.main_frame,is_navigation_request=lambda:main)
        self.aborted=False;self.failure=failure
    def fulfill(self,**kwargs):
        if self.failure: raise RuntimeError('synthetic fulfill failure')
        self.status=kwargs['status']
    def abort(self,*args): self.aborted=True


class FakePage:
    def __init__(self,context):
        self.context=context;self.main_frame=object();self.url='about:blank';self.history=[];self.text='source text 梅林';self.links=None;self.failure=False;self.title='Unit fixture'
    def on(self,*args): pass
    def set_default_timeout(self,*args): pass
    def goto(self,url,**kwargs):
        route=FakeRoute(self,url,failure=self.failure);self.context.callback(route)
        if route.aborted: raise RuntimeError('navigation blocked')
        self.url=url;self.history.append(url)
        return SimpleNamespace(url=url,status=route.status)
    def go_back(self,**kwargs):
        if len(self.history)>1: self.history.pop();self.url=self.history[-1]
        return None
    def wait_for_timeout(self,*args): pass
    def evaluate(self,script,args):
        if not isinstance(args,dict): return None
        return {'title':self.title,'text':self.text[:args['textLimit']],'textClipped':len(self.text)>args['textLimit'],
                'dom':'<html><body>source text</body></html>','domClipped':False,
                'links':self.links if self.links is not None else [{'url':'https://example.net/next','text':'Next'}],
                'linksClipped':False,'scroll':{'x':0,'y':0},'viewport':{'width':1280,'height':720}}
    def screenshot(self,**kwargs): return PNG


class ReentrantRoute(FakeRoute):
    """Synchronous fixture for callbacks delivered inside Playwright completion."""
    def __init__(self,*args,on_fulfill=None,on_abort=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.on_fulfill=on_fulfill;self.on_abort=on_abort
    def fulfill(self,**kwargs):
        callback,self.on_fulfill=self.on_fulfill,None
        if callback: callback()
        super().fulfill(**kwargs)
    def abort(self,*args):
        callback,self.on_abort=self.on_abort,None
        if callback: callback()
        super().abort(*args)


class ScriptedTransport:
    """Explicit body sizes and failures; independent expected byte totals."""
    def __init__(self,steps):
        self.steps=iter(steps);self.bytes=0;self.requests=0
    def fetch(self,url,method='GET',headers=None):
        size,error=next(self.steps);self.bytes+=size;self.requests+=1
        raw=b'x'*size
        if error: raise error
        return FetchResult(url,200,{'content-type':'text/html'},raw,'93.184.216.34',url.startswith('https:'))


def fixture(directory,episode='fixture',actions=None,limits=None,configure=None):
    recorder=EpisodeRecorder(directory,episode,limits or BrowserLimits())
    context=FakeContext();page=FakePage(context);controller=BrowserController(page,context,FakeTransport(),recorder)
    if configure: configure(page,controller)
    recorder.event({'kind':'browser_started','engine':ENGINE,'isolation':ISOLATION})
    results=[]
    for action in actions or [{'action':'open','url':'https://example.org/source'}]: results.append(controller.act(action))
    status='completed' if all(item['status']=='succeeded' for item in results) else 'completed_with_failures'
    recorder.finish(status=status,engine=ENGINE,isolation=ISOLATION,observations=controller.observations,
        actions=controller.actions,requests=controller.requests,network_bytes=controller.network_bytes)
    return results,controller


class RouteAccountingTests(unittest.TestCase):
    def build(self,directory,steps,limits=None):
        recorder=EpisodeRecorder(directory,'reentrant',limits or BrowserLimits())
        context=FakeContext();page=FakePage(context);transport=ScriptedTransport(steps)
        controller=BrowserController(page,context,transport,recorder)
        recorder.event({'kind':'browser_started','engine':ENGINE,'isolation':ISOLATION})
        return recorder,page,controller

    def finish(self,recorder,controller,status='completed_with_failures'):
        recorder.finish(status=status,engine=ENGINE,isolation=ISOLATION,observations=controller.observations,
            actions=controller.actions,requests=controller.requests,network_bytes=controller.network_bytes)
        return validate_episode(recorder.directory)

    def events(self,recorder):
        return [unique_json((recorder.directory/ref['path']).read_bytes())['event'] for ref in recorder.events]

    def test_nested_fulfillment_preserves_fetch_intervals_order_and_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);recorder,page,controller=self.build(root/'episode',[(5,None),(7,None),(11,None),(13,None)])
            completion=[]
            def leaf(name):
                controller.route(FakeRoute(page,'https://example.org/'+name,main=False));completion.append(name)
            def children():
                controller.route(ReentrantRoute(page,'https://example.org/child',main=False,on_fulfill=lambda:leaf('grandchild')))
                completion.append('child');leaf('sibling')
            def goto(url,**kwargs):
                route=ReentrantRoute(page,url,on_fulfill=children);controller.route(route)
                completion.append('document');page.url=url
                return SimpleNamespace(url=url,status=route.status)
            page.goto=goto
            self.assertEqual(controller.act({'action':'open','url':'https://example.org/source'})['status'],'succeeded')
            self.assertEqual(completion,['grandchild','child','sibling','document'])
            resources=[event for event in self.events(recorder) if event['kind']=='resource']
            self.assertEqual({item['resource_id']:(item['consumed_body_bytes'],item['episode_response_body_bytes'])
                for item in resources},{'r0001':(5,5),'r0002':(7,12),'r0003':(11,23),'r0004':(13,36)})
            self.assertEqual([item['resource_id'] for item in resources],['r0001','r0002','r0003','r0004'])
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[5,7,11,13])
            self.assertEqual([item['episode_response_body_bytes'] for item in resources],[5,12,23,36])
            self.assertEqual((controller.requests,controller.network_bytes),(4,36))
            checked=self.finish(recorder,controller,'completed')
            self.assertEqual(checked['observations'][0]['document_resource_id'],'r0001')
            published=publish_episode(root/'episode',MerlinRegistry(root/'registry'))
            reopened=MerlinRegistry(root/'registry')
            self.assertEqual(reopened.read_artifact_ref(published['sources'][0]['source_ref'])['content'],page.text.encode())
            self.assertEqual(publish_episode(root/'episode',reopened),published)

    def test_reentrant_abort_preserves_partial_failed_fetch_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',[(3,http.client.IncompleteRead(b'xxx',5)),(7,None)])
            route=ReentrantRoute(page,'https://example.org/partial',main=False,
                on_abort=lambda:controller.route(FakeRoute(page,'https://example.org/child',main=False)))
            controller.route(route)
            checked=self.finish(recorder,controller)
            resources=[event for event in checked['events'] if event['kind']=='resource']
            self.assertEqual([item['outcome'] for item in resources],['denied','fulfilled'])
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[3,7])
            self.assertEqual([item['episode_response_body_bytes'] for item in resources],[3,10])
            self.assertEqual(resources[0]['error_type'],'IncompleteRead')
            self.assertTrue(route.aborted);self.assertEqual(controller.network_bytes,10)

    def test_reentrant_fulfill_failure_keeps_spent_bytes_and_denied_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',[(5,None),(7,None)])
            route=ReentrantRoute(page,'https://example.org/failing-document',failure=True,
                on_fulfill=lambda:controller.route(FakeRoute(page,'https://example.org/child',main=False)))
            controller.route(route)
            checked=self.finish(recorder,controller)
            resources=[event for event in checked['events'] if event['kind']=='resource']
            self.assertEqual([item['outcome'] for item in resources],['denied','fulfilled'])
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[5,7])
            self.assertEqual(resources[0]['error_type'],'RuntimeError')
            self.assertEqual(controller.documents,{})
            self.assertEqual(controller.network_bytes,12);self.assertTrue(route.aborted)

    def test_policy_denial_has_zero_bytes_before_reentrant_abort_fetch(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',[(7,None)])
            route=ReentrantRoute(page,'http://127.0.0.1/private',main=False,
                on_abort=lambda:controller.route(FakeRoute(page,'https://example.org/child',main=False)))
            controller.route(route)
            checked=self.finish(recorder,controller)
            resources=[event for event in checked['events'] if event['kind']=='resource']
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[0,7])
            self.assertEqual([item['episode_response_body_bytes'] for item in resources],[0,7])
            self.assertEqual(controller.transport.requests,1)

    def test_request_budget_latches_inside_reentrant_fulfillment(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',[(5,None)],replace(BrowserLimits(),max_requests=1))
            child=FakeRoute(page,'https://example.org/child',main=False)
            controller.route(ReentrantRoute(page,'https://example.org/source',on_fulfill=lambda:controller.route(child)))
            ignored=FakeRoute(page,'https://example.org/after-limit',main=False);controller.route(ignored)
            checked=self.finish(recorder,controller,'failed')
            resources=[event for event in checked['events'] if event['kind']=='resource']
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[5,0])
            self.assertEqual([item['outcome'] for item in resources],['fulfilled','denied'])
            self.assertEqual((controller.requests,controller.transport.requests,controller.network_bytes),(2,1,5))
            self.assertEqual(controller.fatal_error,'request_count_exhausted')
            self.assertTrue(child.aborted and ignored.aborted)

    def test_network_budget_detection_byte_is_not_refunded_during_reentry(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',
                [(2,None),(3,BrowserPolicyError('network byte budget exhausted'))],
                replace(BrowserLimits(),max_network_bytes=4))
            controller.route(ReentrantRoute(page,'https://example.org/source',on_fulfill=lambda:
                controller.route(FakeRoute(page,'https://example.org/partial',main=False))))
            checked=self.finish(recorder,controller,'failed')
            resources=[event for event in checked['events'] if event['kind']=='resource']
            self.assertEqual([item['consumed_body_bytes'] for item in resources],[2,3])
            self.assertEqual([item['episode_response_body_bytes'] for item in resources],[2,5])
            self.assertEqual(resources[1]['outcome'],'denied')
            self.assertEqual(controller.network_bytes,5)  # Includes the broker's one detection byte.

    def test_evidence_budget_gap_retains_actual_multiple_inflight_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder,page,controller=self.build(Path(temp)/'episode',[(5,None),(7,None)])
            recorder_event=recorder.event
            def exhausted(event,**kwargs):
                if event['kind']=='resource': raise BrowserPolicyError('synthetic evidence byte budget exhausted')
                return recorder_event(event,**kwargs)
            recorder.event=exhausted
            controller.route(ReentrantRoute(page,'https://example.org/source',on_fulfill=lambda:
                controller.route(FakeRoute(page,'https://example.org/child',main=False))))
            ignored=FakeRoute(page,'https://example.org/after-limit',main=False);controller.route(ignored)
            markers=[event for event in self.events(recorder) if event['kind']=='resource_trace_budget_exhausted']
            self.assertEqual(len(markers),1)
            self.assertEqual(markers[0]['resource_id'],'r0001')
            self.assertEqual(markers[0]['episode_response_body_bytes'],12)
            self.assertEqual((controller.requests,controller.network_bytes),(2,12))
            self.assertTrue(ignored.aborted)
            recorder.finish(status='failed',engine=ENGINE,isolation=ISOLATION,observations=controller.observations,
                actions=controller.actions,requests=controller.requests,network_bytes=controller.network_bytes)
            # The old importer represents one missing record only. Keep a raw
            # failed capture, not fabricated lower counts to satisfy that schema.
            with self.assertRaisesRegex(BrowserPolicyError,'final resource counts differ'):
                validate_episode(recorder.directory)

    def test_teardown_cannot_report_completion_with_missing_resource_or_late_fatal(self):
        for mode in ('missing_completion','late_fatal'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);executable=root/'chromium-fixture';executable.write_bytes(b'fixture');executable.chmod(0o700)
                context=FakeContext();page=FakePage(context);context.new_page=lambda:page
                def close():
                    controller=context.callback.__self__
                    if mode=='missing_completion': controller.requests+=1
                    else: controller.fatal_error='synthetic late callback exhaustion'
                browser=SimpleNamespace(version='synthetic-unit-fixture-not-native-proof',
                    new_context=lambda **kwargs:context,close=close)
                class Driver:
                    def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs:browser))
                    def __exit__(self,*args): return False
                module=ModuleType('playwright.sync_api');module.sync_playwright=lambda:Driver()
                with patch.dict(sys.modules,{'playwright':ModuleType('playwright'),'playwright.sync_api':module}), \
                     patch('merlin.public_browser.renderer_isolation',return_value=ISOLATION), \
                     patch('merlin.public_browser.version',return_value='synthetic-unit-fixture'), \
                     patch('merlin.public_browser.UnixBrokerClient',return_value=FakeTransport()):
                    result=run_episode(episode_id='teardown-ledger',output=root/'episode',executable=executable,
                        broker_socket='/not-used',broker_uid=982,limits=BrowserLimits(),
                        stream=io.StringIO('{"action":"open","url":"https://example.org/"}\n'),emit=lambda value:None)
                self.assertEqual(result['actions'][0]['status'],'succeeded')
                self.assertEqual(result['status'],'failed')
                self.assertEqual(result['error_type'],'BrowserPolicyError')
                if mode=='missing_completion':
                    with self.assertRaisesRegex(BrowserPolicyError,'final resource counts differ'):
                        validate_episode(root/'episode')
                else: self.assertEqual(validate_episode(root/'episode')['manifest']['status'],'failed')


class EpisodeTests(unittest.TestCase):
    def test_open_follow_back_read_preserve_exact_bytes_and_navigation_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            actions=[{'action':'open','url':'https://example.org/source'},
                     {'action':'follow','observation_id':'o0001','link_id':'o0001:l001'},
                     {'action':'back'},{'action':'read','start_byte':0,'length_bytes':12}]
            results,_=fixture(Path(temp)/'episode',actions=actions)
            checked=validate_episode(Path(temp)/'episode')
            self.assertEqual(len(checked['observations']),4)
            self.assertEqual(checked['observations'][1]['document_url'],'https://example.net/next')
            self.assertEqual(checked['observations'][2]['document_url'],'https://example.org/source')
            self.assertEqual(results[-1]['text_page']['text'],'source text ')
            self.assertEqual(checked['manifest']['model_calls'],0)

    def test_stale_link_identity_is_rejected_and_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            results,_=fixture(Path(temp)/'episode',actions=[{'action':'open','url':'https://example.org/'},
                {'action':'read'},{'action':'follow','observation_id':'o0001','link_id':'o0001:l001'}])
            checked=validate_episode(Path(temp)/'episode')
            self.assertEqual(results[-1]['status'],'failed')
            self.assertEqual(checked['manifest']['status'],'completed_with_failures')

    def test_fulfill_failure_never_binds_old_visible_page_to_new_response(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder=EpisodeRecorder(Path(temp)/'episode','failure',BrowserLimits());context=FakeContext();page=FakePage(context)
            controller=BrowserController(page,context,FakeTransport(),recorder)
            self.assertEqual(controller.act({'action':'open','url':'https://example.org/a'})['status'],'succeeded')
            page.failure=True
            self.assertEqual(controller.act({'action':'open','url':'https://example.org/b'})['status'],'failed')
            self.assertIsNone(controller.document)
            self.assertEqual(controller.act({'action':'read'})['status'],'failed')

    def test_request_storm_latches_and_still_finalizes(self):
        with tempfile.TemporaryDirectory() as temp:
            limits=replace(BrowserLimits(),max_requests=1)
            recorder=EpisodeRecorder(Path(temp)/'episode','storm',limits);context=FakeContext();page=FakePage(context)
            controller=BrowserController(page,context,FakeTransport(),recorder)
            controller.act({'action':'open','url':'https://example.org/'})
            for _ in range(700): controller.route(FakeRoute(page,'https://example.net/image',main=False))
            recorder.finish(status='failed',engine=ENGINE,isolation=ISOLATION,observations=controller.observations,
                actions=controller.actions,requests=controller.requests,network_bytes=controller.network_bytes)
            checked=validate_episode(Path(temp)/'episode')
            self.assertEqual(checked['manifest']['counts']['requests'],2)
            self.assertLess(len(checked['events']),20)

    def test_large_link_metadata_hits_evidence_bound_but_final_manifest_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            limits=replace(BrowserLimits(),max_evidence_bytes=262144)
            def configure(page,controller):
                page.links=[{'url':'https://example.org/'+str(i)+'?'+'q='+'x'*8000,'text':'link'} for i in range(100)]
            results,_=fixture(Path(temp)/'episode',limits=limits,configure=configure)
            checked=validate_episode(Path(temp)/'episode')
            self.assertEqual(results[0]['status'],'failed')
            self.assertEqual(checked['manifest']['status'],'completed_with_failures')
            self.assertLess((Path(temp)/'episode'/'episode.json').stat().st_size,131072)

    def test_unisolated_worker_records_failure_without_starting_playwright(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('merlin.public_browser.renderer_isolation',side_effect=BrowserPolicyError('not isolated')):
                result=run_episode(episode_id='no-isolation',output=Path(temp)/'episode',executable='/not-used',
                    broker_socket='/not-used',broker_uid=1000,limits=BrowserLimits(),stream=io.StringIO(''),emit=lambda value:None)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(validate_episode(Path(temp)/'episode')['observations'],[])

    def test_browser_teardown_failure_cannot_claim_successful_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);executable=root/'chromium-fixture';executable.write_bytes(b'synthetic executable');executable.chmod(0o700)
            context=FakeContext();page=FakePage(context);context.new_page=lambda:page
            class Browser:
                version='synthetic-unit-fixture-not-native-proof'
                def new_context(self,**kwargs): return context
                def close(self): raise RuntimeError('synthetic teardown failure')
            browser=Browser()
            def launch(**kwargs):
                self.assertIs(kwargs['chromium_sandbox'],True)
                self.assertNotIn('SYNTHETIC_SECRET',kwargs['env'])
                self.assertNotIn('SYNTHETIC_SECRET',__import__('os').environ)
                return browser
            class Driver:
                def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=launch))
                def __exit__(self,*args): return False
            module=ModuleType('playwright.sync_api');module.sync_playwright=lambda:Driver()
            with patch.dict(sys.modules,{'playwright':ModuleType('playwright'),'playwright.sync_api':module}), \
                 patch('merlin.public_browser.renderer_isolation',return_value=ISOLATION), \
                 patch('merlin.public_browser.version',return_value='synthetic-unit-fixture'), \
                 patch('merlin.public_browser.UnixBrokerClient',return_value=FakeTransport()), \
                 patch.dict('os.environ',{'SYNTHETIC_SECRET':'fixture-only'}):
                result=run_episode(episode_id='teardown',output=root/'episode',executable=executable,
                    broker_socket='/not-used',broker_uid=982,limits=BrowserLimits(),
                    stream=io.StringIO('{"action":"open","url":"https://example.org/"}\n'),emit=lambda value:None)
            self.assertEqual(result['actions'][0]['status'],'succeeded')
            self.assertEqual(result['status'],'failed');self.assertEqual(result['error_type'],'RuntimeError')
            self.assertEqual(validate_episode(root/'episode')['manifest']['status'],'failed')


class CanonicalTests(unittest.TestCase):
    def test_context_capacity_does_not_destroy_canonical_browser_publication(self):
        class SmallBridge(DotContextBridge):
            def __init__(self,*args,**kwargs): super().__init__(*args,max_records=1,**kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root/'episode',actions=[{'action':'open','url':'https://example.org/a'},
                                                          {'action':'open','url':'https://example.org/b'}])
            with patch('merlin.browser_ingest.DotContextBridge',SmallBridge):
                result=publish_episode(root/'episode',MerlinRegistry(root/'registry'))
            self.assertEqual([item['context_intake'] for item in result['sources']],['source_snapshot','context_capacity_exhausted'])
            self.assertIsNotNone(result['sources'][1]['artifacts']['text'])
            self.assertIsNotNone(result['handoff_ref'])

    def test_publish_restart_read_is_exact_and_context_url_contract_is_honest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);episode=root/'episode';store=root/'registry'
            fixture(episode,actions=[{'action':'open','url':'https://example.org/a'},
                                     {'action':'open','url':'https://example.org/search?q=rank'},
                                     {'action':'open','url':'http://example.org/data'}])
            result=publish_episode(episode,MerlinRegistry(store))
            self.assertEqual([item['context_intake'] for item in result['sources']],
                             ['source_snapshot','ineligible_url_contract','ineligible_url_contract'])
            self.assertEqual([item['acquisition_url'] for item in result['sources']],
                             ['https://example.org/a','https://example.org/search?q=rank','http://example.org/data'])
            reopened=MerlinRegistry(store)
            source=result['sources'][0]['source_ref']
            self.assertEqual(reopened.read_artifact_ref(source)['content'],'source text 梅林'.encode())
            self.assertEqual(publish_episode(episode,reopened),result)
            self.assertIsNotNone(result['context_handoff_ref'])
            self.assertFalse(result['qualification']);self.assertFalse(result['promotion_authority'])

    def test_modified_unlisted_symlink_or_rehashed_wrong_source_cannot_publish(self):
        for mode in ('changed','unlisted','symlink','wrong_source'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'episode';fixture(root)
                if mode=='changed': (root/'observations/o0001/text.txt').write_text('forged')
                elif mode=='unlisted': (root/'extra').write_text('extra')
                elif mode=='symlink': (root/'outside').symlink_to('/etc/hosts')
                else:
                    path=root/'episode.json';value=unique_json(path.read_bytes())
                    value['observations'][0]['action_id']='a9999';path.write_bytes(canonical(value))
                with self.assertRaises((BrowserPolicyError,FileNotFoundError)): validate_episode(root)

    def test_empty_text_is_not_ingested(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root/'episode',configure=lambda page,controller:setattr(page,'text',''))
            result=publish_episode(root/'episode',MerlinRegistry(root/'registry'))
            self.assertEqual(result['sources'][0]['context_intake'],'empty_rendered_text')
            self.assertIsNone(result['context_handoff_ref'])
            self.assertIsNotNone(result['handoff_ref'])

    def test_empty_title_gets_explicit_nonempty_source_label(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root/'episode',configure=lambda page,controller:setattr(page,'title',''))
            registry=MerlinRegistry(root/'registry');result=publish_episode(root/'episode',registry)
            record=unique_json(registry.read_artifact_ref(result['sources'][0]['record_ref'])['content'])
            self.assertEqual(record['title'],'Public source example.org')

    def test_rehashed_action_cannot_claim_another_actions_observation(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'episode';fixture(root,actions=[{'action':'open','url':'https://example.org/a'},{'action':'read'}])
            manifest=unique_json((root/'episode.json').read_bytes());manifest['actions'][1]['observation_id']='o0001'
            chain='0'*64;new_refs={}
            for ref in manifest['events']:
                value=unique_json((root/ref['path']).read_bytes())
                if value['event']['kind']=='action_finished' and value['event']['id']=='a0002': value['event']['observation_id']='o0001'
                value['previous_sha256']=chain
                chain=hashlib.sha256(canonical({key:item for key,item in value.items() if key!='event_sha256'})).hexdigest()
                value['event_sha256']=chain;raw=canonical(value);(root/ref['path']).write_bytes(raw)
                new_refs[ref['path']]={**ref,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            manifest['events']=[new_refs[ref['path']] for ref in manifest['events']]
            manifest['files']=[new_refs.get(ref['path'],ref) for ref in manifest['files']]
            for index in manifest['observations']: index['event_ref']=new_refs[index['event_ref']['path']]
            manifest['event_chain_head']=chain;manifest['counts']['artifact_bytes']=sum(ref['bytes'] for ref in manifest['files'])
            (root/'episode.json').write_bytes(canonical(manifest))
            with self.assertRaisesRegex(BrowserPolicyError,'own observation'): validate_episode(root)


class ServiceTests(unittest.TestCase):
    def setup_service(self,temp):
        root=Path(temp);episodes=root/'episodes';episodes.mkdir()
        config={'registry_root':str(root/'registry'),'project_id':'merlin-browser-research',
                'episodes_root':str(episodes),'limits':BrowserLimits().to_dict(),'launcher':'/fixed-test-launcher',
                'launch_timeout_seconds':75,'allowed_uids':[0,982]}
        calls=[]
        def launch(path,episode,timeout):
            calls.append(episode);directory=episodes/episode
            actions=unique_json((directory/'request/actions.json').read_bytes())
            fixture(directory/'result',episode=episode,actions=actions)
            return {'schema':'merlin-browser-launch-observation/1','return_code':0,'error_type':None},b'synthetic launcher fixture'
        return BrowserService(config,launch=launch),config,calls

    def test_authorized_submit_durable_read_and_reuse_does_not_repeat_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp)
            request={'schema':'merlin-browser-request-api/1','operation':'submit','episode_id':'caller-test',
                     'actions':[{'action':'open','url':'https://example.org/source'}]}
            result=service.handle(request,982);self.assertEqual(result['status'],'completed');self.assertEqual(calls,['caller-test'])
            restarted=BrowserService(config,launch=lambda *args: self.fail('read must not launch'))
            read={'schema':'merlin-browser-request-api/1','operation':'read','episode_id':'caller-test','observation_id':'o0001',
                  'kind':'text','start_byte':0,'length_bytes':16384,'link_start':0,'link_limit':20}
            content=restarted.handle(read,982)
            self.assertEqual(content['content'],'source text 梅林');self.assertEqual(content['links'][0]['text'],'Next')
            with self.assertRaises(BrowserPolicyError): service.handle(request,982)
            self.assertEqual(len(calls),1)

    def test_wrong_peer_unsafe_plan_and_cross_scope_read_fail_before_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            service,_,calls=self.setup_service(temp)
            request={'schema':'merlin-browser-request-api/1','operation':'submit','episode_id':'safe',
                     'actions':[{'action':'open','url':'https://example.org/'}]}
            with self.assertRaises(BrowserPolicyError): service.handle(request,1000)
            with self.assertRaises(BrowserPolicyError): service.handle({**request,'launcher':'/bin/sh'},982)
            with self.assertRaises(BrowserPolicyError): service.handle({**request,'episode_id':'../private'},982)
            with self.assertRaises(BrowserPolicyError): service.handle({**request,'episode_id':'-launcher-reject'},982)
            with self.assertRaises(BrowserPolicyError): service.handle({**request,'actions':[{'action':'open','url':'http://169.254.169.254/'}]},982)
            self.assertEqual(calls,[])
            with self.assertRaises(BrowserPolicyError): service._read_ref({'project_id':'dot-production-docs','logical_path':'secrets'})

    def test_low_disk_denies_before_launch_and_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp);existing=Path(config['episodes_root'])/'old-evidence'
            existing.write_bytes(b'retain')
            request={'schema':'merlin-browser-request-api/1','operation':'submit','episode_id':'low-disk',
                     'actions':[{'action':'open','url':'https://example.org/'}]}
            with patch('merlin.browser_service.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
                with self.assertRaisesRegex(BrowserPolicyError,'disk headroom'): service.handle(request,982)
            self.assertEqual(calls,[]);self.assertEqual(existing.read_bytes(),b'retain')
            self.assertFalse((Path(config['episodes_root'])/'low-disk').exists())

    def test_launch_start_failure_is_durable_and_never_implicitly_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp)
            def missing(*args): raise FileNotFoundError('synthetic missing fixed launcher')
            service.launch=missing
            request={'schema':'merlin-browser-request-api/1','operation':'submit','episode_id':'launch-failure',
                     'actions':[{'action':'open','url':'https://example.org/'}]}
            result=service.handle(request,982);self.assertEqual(result['status'],'failed')
            restarted=BrowserService(config,launch=lambda *args:self.fail('failure status must not retry'))
            status=restarted.handle({'schema':'merlin-browser-request-api/1','operation':'status','episode_id':'launch-failure'},982)
            self.assertEqual(status['failure']['error_type'],'FileNotFoundError')
            with self.assertRaises(BrowserPolicyError): restarted.handle(request,982)

    def test_well_formed_failed_worker_episode_is_canonical_even_with_nonzero_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp)
            def failed_launcher(path,episode,timeout):
                directory=Path(config['episodes_root'])/episode
                actions=unique_json((directory/'request/actions.json').read_bytes())
                fixture(directory/'result',episode=episode,actions=actions)
                return {'schema':'merlin-browser-launch-observation/1','return_code':1,'error_type':None},b'synthetic retained failure'
            service.launch=failed_launcher
            request={'schema':'merlin-browser-request-api/1','operation':'submit','episode_id':'controlled-failure',
                     'actions':[{'action':'open','url':'https://example.org/'},
                                {'action':'follow','observation_id':'o0001','link_id':'o0001:l999'}]}
            result=service.handle(request,982)
            self.assertEqual(result['status'],'completed_with_failures')
            self.assertIsNotNone(result['publication']['handoff_ref'])

    def test_interrupted_request_is_reported_as_reconciliation_needed(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp)
            (Path(config['episodes_root'])/'interrupted').mkdir()
            service._artifact('interrupted','request.json',canonical({'synthetic':'retained before process exit'}))
            status=service.handle({'schema':'merlin-browser-request-api/1','operation':'status','episode_id':'interrupted'},982)
            self.assertEqual(status['status'],'reconciliation_needed');self.assertFalse(status['execution_retried']);self.assertEqual(calls,[])

    def test_service_read_too_short_utf8_rejects_and_continuation_advances(self):
        with tempfile.TemporaryDirectory() as temp:
            service,config,calls=self.setup_service(temp)
            episode='unicode';directory=Path(config['episodes_root'])/episode;directory.mkdir()
            fixture(directory/'result',episode=episode,configure=lambda page,controller:setattr(page,'text','字X'))
            publish_episode(directory/'result',service.registry)
            read={'schema':'merlin-browser-request-api/1','operation':'read','episode_id':episode,'observation_id':'o0001',
                  'kind':'text','start_byte':0,'length_bytes':1,'link_start':0,'link_limit':20}
            with self.assertRaises(BrowserPolicyError): service.handle(read,982)
            result=service.handle({**read,'start_byte':1},982)
            self.assertEqual((result['start_byte'],result['end_byte'],result['content']),(3,4,'X'))
            self.assertIsNone(result['next_start_byte'])


if __name__=='__main__': unittest.main()
