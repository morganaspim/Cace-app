"""One deterministic real-Chromium fixture inside the production envelope."""
import argparse
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import sys
import socket

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--executable',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output);out.mkdir(mode=0o700,exist_ok=False)
    sys.path.insert(0,'/runtime/python')
    from merlin.public_browser import renderer_isolation, BrowserController, EpisodeRecorder
    from merlin.browser_policy import BrowserLimits, BrowserPolicyError
    from merlin.browser_egress import FetchResult, PublicHTTPTransport
    isolation=renderer_isolation()
    forbidden=('/root','/home/opc','/etc/merlin-dot-private','/var/lib/merlin-dot-private',
               '/opt/merlin-model-provider','/run/merlin-dot-private','/var/lib/merlin-public-browser')
    visible=[path for path in forbidden if Path(path).exists()]
    if visible: raise RuntimeError('forbidden host state visible')
    from importlib.metadata import version
    from playwright.sync_api import sync_playwright
    with sync_playwright() as driver:
        browser=driver.chromium.launch(executable_path=args.executable,headless=True,
            chromium_sandbox=True,env={'PATH':'/usr/bin','HOME':'/tmp','LANG':'C.UTF-8'},
            args=['--disable-background-networking','--disable-component-update','--disable-sync'])
        context=browser.new_context(service_workers='block',accept_downloads=False,viewport={'width':960,'height':640})
        context.route('**/*',lambda route:route.abort())
        page=context.new_page()
        page.set_content('<!doctype html><title>Merlin fixture</title><h1 id="v">pending</h1><script>document.getElementById("v").textContent="renderer-js-42"</script>')
        observed=page.locator('#v').inner_text()
        if observed!='renderer-js-42': raise RuntimeError('real JavaScript rendering failed')
        shot=page.screenshot(type='png',full_page=False)
        (out/'screenshot.png').write_bytes(shot)
        dom=page.content().encode();text=observed.encode()
        (out/'dom.html').write_bytes(dom);(out/'text.txt').write_bytes(text)
        value={'schema':'merlin-native-browser-fixture/1','status':'succeeded','isolation':isolation,
               'playwright':version('playwright'),'chromium':browser.version,'chromium_sandbox':True,
               'observed_text':observed,'screenshot_sha256':hashlib.sha256(shot).hexdigest(),
               'dom_sha256':hashlib.sha256(dom).hexdigest(),'text_sha256':hashlib.sha256(text).hexdigest(),
               'forbidden_host_paths_visible':visible,'public_network_requests':0,
               'model_calls':0,'qualification':False,'promotion_authority':False}
        context.close()
        # These bytes are deliberately injected controlled fixtures. They are
        # never labelled public acquisitions or placed in the public-source
        # registry. Real Chromium and the production typed controller execute.
        class MemorySocket:
            def __init__(self,raw): self.raw=raw
            def makefile(self,*args,**kwargs): return io.BytesIO(self.raw)
            def settimeout(self,value): pass
        class MemoryConnection:
            def __init__(self,raw): self.sock=MemorySocket(raw)
            def request(self,*args,**kwargs): pass
            def getresponse(self):
                response=http.client.HTTPResponse(self.sock);response.begin();return response
            def close(self): pass
        (out/'fixtures').mkdir()
        failing_responses={
            'oversize':b'HTTP/1.1 200 OK\r\nContent-Length: 1048577\r\nContent-Type: text/html\r\n\r\n',
            'truncated':b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\nContent-Type: text/html\r\n\r\npartial body'}
        for name,raw in failing_responses.items(): (out/'fixtures'/(name+'-response.bin')).write_bytes(raw)
        class FixtureTransport:
            bytes=0
            def fetch(self,url,method='GET',headers=None):
                negative=url.rsplit('/',1)[-1]
                if negative in failing_responses:
                    wire=failing_responses[negative]
                    actual_guard=PublicHTTPTransport(BrowserLimits(),
                        resolver=lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))],
                        connector=lambda *args:MemoryConnection(wire))
                    try: return actual_guard.fetch(url,method,headers)
                    finally: self.bytes+=actual_guard.bytes
                if url not in ('https://example.org/fixture','https://example.org/next'):
                    raise BrowserPolicyError('fixture has no such source')
                body=(b'<!doctype html><title>Merlin typed fixture</title><h1>renderer-js-42</h1>'
                      b'<a href="https://example.org/next">Observed next page</a>'
                      b'<div style="height:1600px">Fixture scroll body</div>')
                if url.endswith('/next'): body=b'<!doctype html><title>Next fixture</title><h1>Observed link target</h1>'
                self.bytes+=len(body)
                return FetchResult(url,200,{'content-type':'text/html'},body,'0.0.0.0',False)
        limits=BrowserLimits();recorder=EpisodeRecorder(out/'controller','native-controlled-fixture',limits)
        context=browser.new_context(service_workers='block',accept_downloads=False,viewport={'width':960,'height':640})
        page=context.new_page();transport=FixtureTransport();controller=BrowserController(page,context,transport,recorder)
        outcomes=[]
        first=controller.act({'action':'open','url':'https://example.org/fixture'});outcomes.append(first)
        if first['status']!='succeeded' or not first['observation']['links']: raise RuntimeError('typed fixture open/link failed')
        observation=first['observation']
        plans=[{'action':'follow','observation_id':observation['id'],'link_id':observation['links'][0]['id']},
               {'action':'back'},{'action':'scroll','delta_y':720},
               {'action':'read','start_byte':0,'length_bytes':80},
               {'action':'open','url':'https://example.org/oversize'},
               {'action':'open','url':'https://example.org/truncated'},
               {'action':'open','url':'https://chatgpt.com/'}]
        outcomes.extend(controller.act(action) for action in plans)
        if [item['status'] for item in outcomes]!=['succeeded']*5+['failed']*3:
            raise RuntimeError('typed interaction/negative fixture outcomes differ')
        if (outcomes[1]['observation']['url']!='https://example.org/next'
            or outcomes[2]['observation']['url']!='https://example.org/fixture'
            or outcomes[3]['observation']['scroll']['y']<=0
            or len(outcomes[4]['text_page']['text'].encode())>80):
            raise RuntimeError('typed follow/back/scroll/read observations differ')
        recorder.finish(status='completed_with_failures',engine={'name':'chromium','browser_version':browser.version,
                'fixture':True,'network_transport':'injected_fixed_fixture','public_acquisition':False},
            isolation=isolation,observations=controller.observations,actions=controller.actions,
            requests=controller.requests,network_bytes=controller.network_bytes)
        (out/'controlled-results.json').write_text(json.dumps(outcomes,sort_keys=True,indent=2)+'\n')
        value['typed_fixture']={'label':'injected controlled bytes; actual Chromium/controller; no real network',
            'actions':8,'expected_successes':5,'expected_failures':3,'observed_statuses':[item['status'] for item in outcomes],
            'observed_link_follow':True,'back_scroll_read':True,'excluded_chatgpt_denied':True,
            'oversize_and_truncated_fixture_failures_retained':True}
        (out/'fixture.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
        browser.close();print(json.dumps(value,sort_keys=True))

if __name__=='__main__':main()
