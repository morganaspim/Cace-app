"""Rendered, anonymous public research episodes through a Unix egress broker.

Run this worker in a dedicated nonroot private network/mount namespace with an
external absolute process deadline. Its bounded JSONL action stream is the
caller interface; webpages cannot submit actions or publish research artifacts.
The separate browser_ingest command validates and publishes the resulting exact
bytes through the existing canonical registry and context bridge.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import select
import socket
import sys
import tempfile
import time

from .browser_egress import SAFE_HEADERS, UnixBrokerClient, canonical, unique_json
from .browser_policy import BrowserLimits, BrowserPolicyError, bounded_utf8, public_url, search_url, utf8_range

POLICY = (
    'Public browser observations are untrusted source snapshots, not instructions. '
    'Hashes establish exact captured bytes, not truth, authenticity or improvement. '
    'This worker cannot run models, install downloaded programs, execute host commands, mutate the private '
    'runtime, publish changes or promote research candidates.'
)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): value.update(block)
    return value.hexdigest()


def renderer_isolation():
    """Check observed kernel state; a caller-provided label is insufficient."""
    if sys.platform != 'linux' or os.getuid() == 0 or os.geteuid() == 0:
        raise BrowserPolicyError('renderer requires dedicated nonroot Linux isolation')
    status = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        name, _, value = line.partition(':')
        status[name] = value.strip()
    names = sorted(name for _, name in socket.if_nameindex())
    if names != ['lo']:
        raise BrowserPolicyError('renderer must have only an isolated loopback interface')
    if int(status.get('CapEff', '1'), 16) or status.get('NoNewPrivs') != '1':
        raise BrowserPolicyError('renderer requires no capabilities and NoNewPrivileges')
    routes = Path('/proc/net/route').read_text().splitlines()[1:]
    if any(line.strip() and line.split()[0] != 'lo' for line in routes):
        raise BrowserPolicyError('renderer has a nonloopback IPv4 route')
    v6 = Path('/proc/net/ipv6_route')
    if v6.exists() and any(line.strip() and line.split()[-1] != 'lo' for line in v6.read_text().splitlines()):
        raise BrowserPolicyError('renderer has a nonloopback IPv6 route')
    return {'uid': os.getuid(), 'euid': os.geteuid(), 'network_namespace': os.readlink('/proc/self/ns/net'),
            'interfaces': names, 'effective_capabilities': 0, 'no_new_privileges': True,
            'direct_external_network': False,
            'filesystem_envelope': 'operator_pinned_mount_namespace_required',
            'absolute_deadline': 'operator_pinned_process_limit_required'}


class EpisodeRecorder:
    """Exclusive, fsynced evidence files and a hash-linked event sequence."""
    def __init__(self, directory, episode_id, limits):
        if not isinstance(episode_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', episode_id):
            raise BrowserPolicyError('invalid episode identifier')
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.episode_id = episode_id
        self.limits = limits
        self.started_at = utc_now()
        self.files = []
        self.events = []
        self.bytes = 0
        self.chain = '0'*64
        self.closed = False

    def write(self, name, raw, media_type, *, metadata=False):
        if self.closed or not isinstance(raw, bytes):
            raise BrowserPolicyError('episode is closed or artifact is not bytes')
        if not re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+', name) or '..' in Path(name).parts:
            raise BrowserPolicyError('invalid evidence filename')
        # Reserve space for bounded denial/startup/finalization records.
        bound = self.limits.max_evidence_bytes if metadata else self.limits.max_evidence_bytes-131072
        if self.bytes+len(raw) > bound:
            raise BrowserPolicyError('episode evidence byte budget exhausted')
        path = self.directory / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(str(path), os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        ref = {'path': name, 'sha256': sha256(raw), 'bytes': len(raw), 'media_type': media_type}
        self.files.append(ref);self.bytes += len(raw)
        return ref

    def event(self, event, *, terminal=False):
        if len(self.events) >= 512:
            raise BrowserPolicyError('episode event count exhausted')
        body = {'sequence': len(self.events)+1, 'previous_sha256': self.chain,
                'recorded_at': utc_now(), 'event': event}
        next_chain = sha256(canonical(body))
        ref = self.write('events/%04d.json' % body['sequence'],
                         canonical({**body, 'event_sha256': next_chain}), 'application/json', metadata=terminal)
        self.chain=next_chain
        self.events.append(ref)
        return body['sequence']

    def finish(self, *, status, engine, isolation, observations, actions, requests, network_bytes, error_type=None):
        self.event({'kind': 'episode_finished', 'status': status, 'error_type': error_type},terminal=True)
        observation_index=[{'id':item['id'],'action_id':item['action_id'],'event_ref':item['event_ref']}
                           for item in observations]
        value = {'schema': 'merlin-public-browser-episode/1', 'episode_id': self.episode_id,
                 'started_at': self.started_at, 'completed_at': utc_now(), 'status': status,
                 'engine': engine, 'isolation': isolation, 'limits': self.limits.to_dict(),
                 'observations': observation_index, 'actions': actions, 'files': list(self.files),
                 'events': list(self.events), 'event_chain_head': self.chain,
                 'counts': {'actions': len(actions), 'requests': requests,
                            'response_body_bytes': network_bytes, 'artifact_bytes': self.bytes},
                 'model_calls': 0, 'external_model_cost_usd': 0,
                 'qualification': False, 'promotion_authority': False,
                 'policy': POLICY, 'error_type': error_type}
        raw = canonical(value)
        if self.bytes+len(raw) > self.limits.max_evidence_bytes:
            raise BrowserPolicyError('final evidence byte budget exhausted')
        # The manifest does not include its own digest; the external receipt does.
        self.write('episode.json', raw, 'application/json', metadata=True)
        self.closed = True
        return value


# This fixed script extracts text/DOM/anchors; callers cannot supply JavaScript,
# selectors, file paths or form submissions. Character bounds precede IPC and
# UTF-8 byte bounds are enforced again in the trusted worker.
CAPTURE_SCRIPT = r'''({textLimit, domLimit, linkLimit}) => {
  const text = document.body ? document.body.innerText : '';
  const dom = document.documentElement ? document.documentElement.outerHTML : '';
  const links = [];
  const anchors = document.getElementsByTagName('a');
  const count = Math.min(anchors.length, 10000);
  for (let i=0; i<count && links.length<linkLimit; i++) {
    const a=anchors[i], href=a.href;
    if (!href || href.length>8192 || !/^https?:\/\//i.test(href)) continue;
    links.push({url:href, text:(a.innerText || a.textContent || '').slice(0,500)});
  }
  return {title:document.title.slice(0,500), text:text.slice(0,textLimit),
    textClipped:text.length>textLimit, dom:dom.slice(0,domLimit),
    domClipped:dom.length>domLimit, links,
    linksClipped:anchors.length>count || links.length>=linkLimit,
    scroll:{x:window.scrollX,y:window.scrollY},
    viewport:{width:window.innerWidth,height:window.innerHeight}};
}'''


def validate_action(value):
    if not isinstance(value, dict) or not isinstance(value.get('action'), str):
        raise BrowserPolicyError('one JSON object with an action is required')
    action = value['action']
    allowed = {'open': {'action','url'}, 'search': {'action','query','template'},
               'follow': {'action','observation_id','link_id'}, 'back': {'action'},
               'scroll': {'action','delta_y'}, 'read': {'action','start_byte','length_bytes'}}
    if action not in allowed or set(value)-allowed[action]:
        raise BrowserPolicyError('unsupported action or fields')
    if action == 'open':
        return {'action':action,'url':public_url(value.get('url'))}
    if action == 'search':
        query = value.get('query')
        template = value.get('template','https://www.bing.com/search?q={query}')
        return {'action':action,'query':query,'template':template,'url':search_url(query,template)}
    if action == 'follow':
        for field in ('observation_id','link_id'):
            if not isinstance(value.get(field),str) or not re.fullmatch(r'[a-z0-9:_-]{1,100}',value[field]):
                raise BrowserPolicyError('observed link identity required')
    if action == 'scroll' and (type(value.get('delta_y')) is not int or not -1440 <= value['delta_y'] <= 1440):
        raise BrowserPolicyError('bounded vertical scroll required')
    if action == 'read':
        for field,default,low,high in (('start_byte',0,0,512*1024),('length_bytes',16384,1,16384)):
            item=value.get(field,default)
            if type(item) is not int or not low<=item<=high: raise BrowserPolicyError('bounded source byte range required')
            value={**value,field:item}
    return value.copy()


class BrowserController:
    """Bounded controller used by the real worker; no publisher or model client."""
    def __init__(self, page, context, transport, recorder, *, clock=time.monotonic):
        self.page=page;self.context=context;self.transport=transport;self.recorder=recorder
        self.limits=recorder.limits;self.clock=clock;self.started=clock()
        self.actions=[];self.observations=[];self.requests=0;self.network_bytes=0
        self.last=None;self.document=None;self.documents={};self.active_action=None;self.action_deadline=None
        self.fatal_error=None
        self.pending_resource_records={};self.next_resource_record=1;self.resource_trace_exhausted=False
        context.route('**/*',self.route)
        context.route_web_socket('**/*',lambda route: route.close(code=1008,reason='public research HTTP only'))
        context.on('page',lambda opened: opened.close() if opened != page else None)
        page.on('dialog',lambda dialog: dialog.dismiss())
        page.on('download',lambda download: download.cancel())

    def remaining_ms(self):
        end=self.started+self.limits.wall_seconds
        if self.action_deadline is not None: end=min(end,self.action_deadline)
        remaining=int((end-self.clock())*1000)
        if remaining<=0: raise BrowserPolicyError('browser action or episode deadline reached')
        return remaining

    def route(self, route):
        request=route.request
        raw_url=request.url
        if self.fatal_error:
            try: route.abort('blockedbyclient')
            except Exception: pass
            return
        self.requests+=1
        resource_number=self.requests
        spent_before=getattr(self.transport,'bytes',self.network_bytes)
        record={'kind':'resource','resource_id':'r%04d'%resource_number,
                'action_id':self.active_action,'url':raw_url[:8192],
                'url_sha256':sha256(raw_url.encode()),'url_truncated':len(raw_url)>8192,
                'method':request.method,'resource_type':request.resource_type,
                'main_document':False,'outcome':'denied',
                'consumed_body_bytes':0,'episode_response_body_bytes':spent_before}
        try:
            self.remaining_ms()
            if self.requests>self.limits.max_requests:
                self.fatal_error='request_count_exhausted'
                raise BrowserPolicyError('request count exhausted')
            url=public_url(raw_url)
            if request.method not in ('GET','HEAD'): raise BrowserPolicyError('mutating request denied')
            headers={k:v for k,v in request.headers.items() if k.lower() in SAFE_HEADERS}
            result=None
            try:
                result=self.transport.fetch(url,request.method,headers)
            finally:
                # The synchronous broker call does not yield to Playwright.
                # Fulfill/abort can reenter this handler for other resources,
                # so bind this fetch's byte interval before either call.
                spent_after=getattr(self.transport,'bytes',spent_before+(len(result.body) if result is not None else 0))
                self.network_bytes=max(self.network_bytes,spent_after)
                record['consumed_body_bytes']=max(0,spent_after-spent_before)
                record['episode_response_body_bytes']=spent_after
            if self.network_bytes>self.limits.max_network_bytes: raise BrowserPolicyError('network byte budget exhausted')
            self.remaining_ms()
            record.update(outcome='fulfilled',url=url,status=result.status,body_sha256=sha256(result.body),
                          body_bytes=len(result.body),peer_ip=result.peer_ip,tls_verified=result.tls_verified)
            record['main_document']=request.is_navigation_request() and request.frame == self.page.main_frame
            if record['main_document']:
                record['body_ref']=self.recorder.write('network/'+record['resource_id']+'.body',result.body,'application/octet-stream')
                record['response_headers']=result.headers
            route.fulfill(status=result.status,headers=result.headers,body=result.body)
            if record['main_document']:
                self.documents[url]=record.copy()
        except Exception as error:
            record['outcome']='denied';record['error_type']=type(error).__name__
            if isinstance(error,BrowserPolicyError): record['reason']=str(error)[:200]
            try: route.abort('blockedbyclient')
            except Exception: pass
        # A later request can finish while an earlier fulfill is suspended.
        # Preserve reserved request order without borrowing another fetch's
        # counters or claiming fulfillment before the actual call returns.
        self.pending_resource_records[resource_number]=record
        while self.next_resource_record in self.pending_resource_records:
            completed=self.pending_resource_records.pop(self.next_resource_record)
            self.next_resource_record+=1
            if self.resource_trace_exhausted:
                continue
            try: self.recorder.event(completed)
            except BrowserPolicyError:
                self.fatal_error='evidence_budget_exhausted'
                self.resource_trace_exhausted=True
                # One truthful gap marker; actual counters are never reduced
                # to make incomplete in-flight evidence appear importable.
                self.recorder.event({'kind':'resource_trace_budget_exhausted','resource_id':completed['resource_id'],
                                     'episode_response_body_bytes':self.network_bytes},terminal=True)

    def capture(self, action_id):
        self.remaining_ms()
        if self.fatal_error: raise BrowserPolicyError(self.fatal_error)
        url=public_url(self.page.url)
        if not self.document or self.document['outcome']!='fulfilled':
            raise BrowserPolicyError('no broker-bound main document was rendered')
        if url != self.document['url']:
            raise BrowserPolicyError('rendered URL lacks an exact committed document binding; reopen it')
        values=self.page.evaluate(CAPTURE_SCRIPT,{'textLimit':self.limits.max_text_bytes,
                                  'domLimit':self.limits.max_dom_bytes,'linkLimit':self.limits.max_links})
        text,text_clip=bounded_utf8(values['text'],self.limits.max_text_bytes)
        dom,dom_clip=bounded_utf8(values['dom'],self.limits.max_dom_bytes)
        screenshot=self.page.screenshot(type='png',full_page=False,timeout=self.remaining_ms())
        if len(screenshot)>self.limits.max_screenshot_bytes:
            raise BrowserPolicyError('viewport screenshot byte budget exhausted')
        identifier='o%04d'%(len(self.observations)+1)
        prefix='observations/'+identifier+'/'
        files={'text':self.recorder.write(prefix+'text.txt',text,'text/plain; charset=utf-8'),
               'dom':self.recorder.write(prefix+'dom.html',dom,'text/html; charset=utf-8'),
               'screenshot':self.recorder.write(prefix+'viewport.png',screenshot,'image/png'),
               'response_body':self.document['body_ref']}
        links=[]
        for item in values['links']:
            try: target=public_url(item['url'])
            except BrowserPolicyError: continue
            links.append({'id':identifier+':l%03d'%(len(links)+1),'url':target,'text':item['text'][:500]})
        observation={'id':identifier,'action_id':action_id,'url':url,
            'document_url':self.document['url'],'document_resource_id':self.document['resource_id'],
            'document_status':self.document['status'],'document_tls_verified':self.document['tls_verified'],
            'title':values['title'],'captured_at':utc_now(),'artifacts':files,'links':links,
            'truncated':{'text':text_clip or values['textClipped'],'dom':dom_clip or values['domClipped'],
                         'links':values['linksClipped']},'viewport':values['viewport'],'scroll':values['scroll'],
            'resource_events_through':len(self.recorder.events),
            'epistemic':'source_snapshot','qualification':False}
        self.recorder.event({'kind':'observation','observation':observation})
        observation['event_ref']=self.recorder.events[-1]
        self.observations.append(observation);self.last=observation
        self.remaining_ms()
        return observation

    def act(self, raw):
        if len(self.actions)>=self.limits.max_actions:
            raise BrowserPolicyError('episode action count exhausted')
        self.remaining_ms()
        identifier='a%04d'%(len(self.actions)+1)
        self.active_action=identifier
        self.action_deadline=min(self.started+self.limits.wall_seconds,self.clock()+self.limits.action_seconds)
        # The exact submitted JSON value is retained, including rejected fields.
        request_ref=self.recorder.write('actions/'+identifier+'.json',canonical(raw),'application/json')
        result={'id':identifier,'request_ref':request_ref,'status':'failed','observation_id':None}
        self.actions.append(result)
        try:
            self.recorder.event({'kind':'action_started','action_id':identifier,'request_ref':request_ref})
            action=validate_action(raw)
            name=action['action']
            self.page.set_default_timeout(self.remaining_ms())
            if name in ('open','search'):
                self.document=None
                response=self.page.goto(action['url'],wait_until='domcontentloaded',timeout=self.remaining_ms())
                if response is not None: self.document=self.documents.get(public_url(response.url))
            elif name=='follow':
                if not self.last or action['observation_id']!=self.last['id']:
                    raise BrowserPolicyError('follow requires the latest observation')
                choices={item['id']:item['url'] for item in self.last['links']}
                if action['link_id'] not in choices: raise BrowserPolicyError('link was not observed')
                self.document=None
                response=self.page.goto(choices[action['link_id']],wait_until='domcontentloaded',timeout=self.remaining_ms())
                if response is not None: self.document=self.documents.get(public_url(response.url))
            elif name=='back':
                if self.last is None: raise BrowserPolicyError('no browser history')
                self.document=None
                response=self.page.go_back(wait_until='domcontentloaded',timeout=self.remaining_ms())
                self.document=self.documents.get(public_url(response.url if response is not None else self.page.url))
            elif name=='scroll':
                if self.last is None: raise BrowserPolicyError('open a source before scrolling')
                self.page.evaluate('(dy) => window.scrollBy(0,dy)',action['delta_y'])
            elif name=='read' and self.last is None:
                raise BrowserPolicyError('open a source before reading')
            # Small bounded rendering opportunity; long-lived streams do not
            # become an unbounded networkidle wait.
            self.page.wait_for_timeout(min(150,self.remaining_ms()))
            observation=self.capture(identifier)
            text=(self.recorder.directory/observation['artifacts']['text']['path']).read_bytes()
            start=action.get('start_byte',0);length=action.get('length_bytes',16384)
            start,end,excerpt=utf8_range(text,start,length)
            result.update(status='succeeded',observation_id=observation['id'])
            return {'schema':'merlin-browser-action-result/1','action_id':identifier,
                    'status':'succeeded','observation':observation,
                    'text_page':{'text':excerpt.decode(),'start_byte':start,'end_byte':end,
                                 'total_bytes':len(text),'next_start_byte':end if end<len(text) else None,
                                 'excerpt_sha256':sha256(excerpt)},'policy':POLICY}
        except Exception as error:
            result['error_type']=type(error).__name__
            return {'schema':'merlin-browser-action-result/1','action_id':identifier,
                    'status':'failed','error_type':type(error).__name__,'policy':POLICY}
        finally:
            self.recorder.event({'kind':'action_finished',**result},terminal=True)
            self.active_action=None;self.action_deadline=None


def clean_environment(home):
    # Playwright's Node driver is sanitized too, not only its Chromium child.
    return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
            'HOME':str(home),'TMPDIR':str(home),'XDG_CONFIG_HOME':str(home/'config'),
            'XDG_CACHE_HOME':str(home/'cache'),'XDG_DATA_HOME':str(home/'data')}


def action_lines(stream, deadline):
    """An idle or partial-line caller cannot keep an episode alive indefinitely."""
    try: descriptor=stream.fileno()
    except (AttributeError,OSError):
        for raw in stream:
            if time.monotonic()>=deadline: raise BrowserPolicyError('action input deadline reached')
            yield raw
        return
    pending=b''
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0 or not select.select([descriptor],[],[],remaining)[0]:
            raise BrowserPolicyError('action input deadline reached')
        raw=os.read(descriptor,4096)
        if not raw:
            if pending: yield pending
            return
        pending+=raw
        while b'\n' in pending:
            line,pending=pending.split(b'\n',1)
            if len(line)>16384: raise BrowserPolicyError('action JSON line byte budget exceeded')
            yield line
        if len(pending)>16384: raise BrowserPolicyError('action JSON line byte budget exceeded')


def run_episode(*, episode_id, output, executable, broker_socket, broker_uid, limits, stream, emit):
    recorder=EpisodeRecorder(output,episode_id,limits)
    engine={};isolation={};controller=None;error_type=None;status='failed'
    started=time.monotonic()
    try:
        isolation=renderer_isolation()
        executable=Path(executable).resolve(strict=True)
        if not executable.is_file() or not os.access(str(executable),os.X_OK):
            raise BrowserPolicyError('explicit executable Chromium required')
        from playwright.sync_api import sync_playwright
        engine={'name':'chromium','playwright_version':version('playwright'),
                'executable_path':str(executable),'executable_sha256':file_sha256(executable),
                'chromium_sandbox':True,'session':'fresh_anonymous_ephemeral',
                'service_workers':'blocked','websockets':'blocked','downloads':'cancelled',
                'browser_version':None}
        with tempfile.TemporaryDirectory(prefix='merlin-public-browser-') as directory:
            clean=clean_environment(Path(directory))
            previous=dict(os.environ)
            os.environ.clear();os.environ.update(clean)
            try:
                with sync_playwright() as playwright:
                    browser=playwright.chromium.launch(executable_path=str(executable),headless=True,
                        chromium_sandbox=True,env=clean,timeout=limits.action_seconds*1000,
                        args=['--disable-extensions','--disable-quic',
                              '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
                    try:
                        engine['browser_version']=browser.version
                        context=browser.new_context(viewport={'width':1280,'height':720},
                            accept_downloads=False,service_workers='block',permissions=[],
                            java_script_enabled=True,ignore_https_errors=False)
                        page=context.new_page()
                        controller=BrowserController(page,context,UnixBrokerClient(broker_socket,broker_uid,limits),recorder)
                        # Launch time consumes the same externally bounded episode.
                        controller.started=started
                        recorder.event({'kind':'browser_started','engine':engine,'isolation':isolation})
                        for raw in action_lines(stream,started+limits.wall_seconds-0.25):
                            if len(raw.encode() if isinstance(raw,str) else raw)>16384:
                                raise BrowserPolicyError('action JSON line byte budget exceeded')
                            value=unique_json(raw)
                            emit(controller.act(value))
                        status=('completed' if controller.actions and all(item['status']=='succeeded' for item in controller.actions)
                                else 'completed_with_failures')
                    finally: browser.close()
                    if (controller.fatal_error or controller.pending_resource_records
                            or controller.next_resource_record != controller.requests+1):
                        raise BrowserPolicyError(controller.fatal_error or 'resource completion trace incomplete')
            finally:
                os.environ.clear();os.environ.update(previous)
    except Exception as error:
        status='failed';error_type=type(error).__name__
        recorder.event({'kind':'episode_error','error_type':error_type},terminal=True)
    result=recorder.finish(status=status,engine=engine,isolation=isolation,
        observations=[] if controller is None else controller.observations,
        actions=[] if controller is None else controller.actions,
        requests=0 if controller is None else controller.requests,
        network_bytes=0 if controller is None else controller.network_bytes,error_type=error_type)
    emit({'schema':'merlin-browser-episode-result/1','episode_id':episode_id,'status':status,
          'manifest':'episode.json','manifest_sha256':sha256((Path(output)/'episode.json').read_bytes()),
          'model_calls':0,'error_type':error_type})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',required=True);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--broker-socket',required=True);parser.add_argument('--broker-uid',required=True,type=int)
    parser.add_argument('--executable',required=True);parser.add_argument('--limits',required=True,type=Path)
    args=parser.parse_args()
    def emit(value):
        print(canonical(value).decode(),flush=True)
    result=run_episode(episode_id=args.episode,output=args.output,executable=args.executable,
        broker_socket=args.broker_socket,broker_uid=args.broker_uid,
        limits=BrowserLimits(**unique_json(args.limits.read_bytes())),stream=sys.stdin,emit=emit)
    return 0 if result['status']=='completed' else 1


if __name__=='__main__': raise SystemExit(main())
