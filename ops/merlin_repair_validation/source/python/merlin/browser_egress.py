"""Public HTTP(S) mediator for an isolated real browser.

The renderer has no direct external network route. This separate broker resolves
every destination, rejects every nonpublic answer, and connects to the checked
numeric address while retaining the original HTTP host and TLS server name.
No Authorization, cookies, proxy credentials, inherited environment proxy or
client certificate is accepted. Existing accounts are neither used nor changed.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import http.client
import json
import os
from pathlib import Path
import queue
import re
import socket
import ssl
import stat
import struct
import threading
import time
from urllib.parse import urlsplit, urljoin

from .browser_policy import BrowserLimits, BrowserPolicyError, public_ip, public_url

SAFE_HEADERS = frozenset(('accept', 'accept-language', 'user-agent', 'range'))
DROP_RESPONSE_HEADERS = frozenset(('connection', 'transfer-encoding', 'content-length', 'keep-alive',
    'proxy-authenticate', 'proxy-authorization', 'upgrade', 'alt-svc', 'set-cookie'))
MAX_REQUEST_ENVELOPE = 16384


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def unique_json(raw):
    def pairs(values):
        answer = {}
        for name, value in values:
            if name in answer:
                raise BrowserPolicyError('duplicate protocol field')
            answer[name] = value
        return answer
    return json.loads(raw, object_pairs_hook=pairs)


def response_headers(value):
    if not isinstance(value, dict) or len(value) > 128:
        raise BrowserPolicyError('invalid response headers')
    if sum(len(str(k))+len(str(v)) for k,v in value.items()) > 32768:
        raise BrowserPolicyError('response header budget exceeded')
    for name, content in value.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z0-9!#$%&\x27*+.^_`|~-]+', name)
                or name in DROP_RESPONSE_HEADERS or not isinstance(content, str)
                or any(c in content for c in '\r\n\x00')):
            raise BrowserPolicyError('invalid response header')
    return value


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    headers: dict
    body: bytes
    peer_ip: str
    tls_verified: bool

    def envelope(self):
        return {'schema': 'merlin-browser-response/1', 'url': self.url, 'status': self.status,
                'headers': self.headers, 'body_base64': base64.b64encode(self.body).decode(),
                'body_sha256': hashlib.sha256(self.body).hexdigest(), 'body_bytes': len(self.body),
                'peer_ip': self.peer_ip, 'tls_verified': self.tls_verified}


class PublicHTTPTransport:
    """One bounded request; redirects return to the browser and are checked anew."""
    def __init__(self, limits=None, *, resolver=socket.getaddrinfo, connector=None, clock=time.monotonic):
        self.limits = limits or BrowserLimits()
        self.resolver = resolver
        self.connector = connector or self._connect
        self.clock = clock
        self.started = clock()
        self.requests = 0
        self.bytes = 0
        self.failed_deadline = False

    def _resolve(self, host, port, deadline):
        # getaddrinfo has no timeout API. A timed-out resolver ends this broker's
        # ability to issue requests; a daemon thread cannot keep the process up.
        answers = queue.Queue(maxsize=1)
        def run():
            try: answers.put((True, self.resolver(host, port, type=socket.SOCK_STREAM)))
            except Exception as error: answers.put((False, error))
        threading.Thread(target=run, daemon=True).start()
        try: ok, value = answers.get(timeout=max(0.001, deadline-self.clock()))
        except queue.Empty:
            self.failed_deadline = True
            raise BrowserPolicyError('DNS deadline reached') from None
        if not ok: raise value
        return value

    @staticmethod
    def _connect(host, address, port, secure, timeout):
        family = socket.AF_INET6 if ':' in address else socket.AF_INET
        channel = socket.socket(family, socket.SOCK_STREAM)
        channel.settimeout(timeout)
        try:
            channel.connect((address, port))
            if secure:
                channel = ssl.create_default_context().wrap_socket(channel, server_hostname=host)
            connection = http.client.HTTPConnection(host, port, timeout=timeout)
            connection.sock = channel
            return connection
        except BaseException:
            channel.close()
            raise

    def fetch(self, url, method='GET', headers=None):
        url = public_url(url)
        if method not in ('GET', 'HEAD'):
            raise BrowserPolicyError('public browser only reads GET/HEAD')
        if (self.failed_deadline or self.requests >= self.limits.max_requests
                or self.bytes >= self.limits.max_network_bytes or self.clock()-self.started >= self.limits.wall_seconds):
            raise BrowserPolicyError('episode request budget exhausted')
        self.requests += 1
        deadline = min(self.started+self.limits.wall_seconds, self.clock()+self.limits.request_seconds)
        parsed = urlsplit(url)
        secure = parsed.scheme == 'https'
        port = 443 if secure else 80
        answers = self._resolve(parsed.hostname, port, deadline)
        if not answers or len(answers) > 32:
            raise BrowserPolicyError('bounded public DNS answers required')
        addresses = list(dict.fromkeys(public_ip(answer[4][0]) for answer in answers))
        # No second name resolution: a DNS change cannot redirect this connect.
        address = addresses[0]
        outbound = {'user-agent': 'MerlinPublicResearch/1.0', 'accept': '*/*', 'accept-encoding': 'identity'}
        if headers is not None:
            if not isinstance(headers, dict) or len(headers) > 16:
                raise BrowserPolicyError('bounded request headers required')
            for name, value in headers.items():
                if not isinstance(name,str) or name.lower() not in SAFE_HEADERS:
                    raise BrowserPolicyError('credential or unsupported request header')
                if not isinstance(value, str) or len(value) > 4096 or any(c in value for c in '\r\n\x00'):
                    raise BrowserPolicyError('invalid request header')
                outbound[name.lower()] = value
        remaining = deadline-self.clock()
        if remaining <= 0:
            raise BrowserPolicyError('episode deadline reached')
        connection = self.connector(parsed.hostname, address, port, secure, min(self.limits.request_seconds, remaining))
        try:
            target = parsed.path + ('?'+parsed.query if parsed.query else '')
            connection.request(method, target, headers=outbound)
            response = connection.getresponse()
            pairs = response.getheaders()
            if sum(len(k)+len(v) for k,v in pairs) > 32768:
                raise BrowserPolicyError('response header budget exceeded')
            incoming = {}; lengths = []
            for name,value in pairs:
                key = name.lower()
                if key == 'content-length': lengths.append(value)
                if key == 'content-length' and (not value.isdecimal() or int(value)>self.limits.max_resource_bytes):
                    raise BrowserPolicyError('resource byte budget exceeded')
                if key not in DROP_RESPONSE_HEADERS:
                    if key in incoming:
                        if key in ('content-type','content-encoding','location'):
                            raise BrowserPolicyError('ambiguous duplicate response header')
                        incoming[key] += ', ' + value
                    else: incoming[key] = value
            if len(lengths)>1: raise BrowserPolicyError('ambiguous content length')
            response_headers(incoming)
            if 300 <= response.status < 400 and 'location' in incoming:
                incoming['location'] = public_url(urljoin(url, incoming['location']))
            available = min(self.limits.max_resource_bytes, self.limits.max_network_bytes-self.bytes)
            if available < 1:
                raise BrowserPolicyError('episode network byte budget exhausted')
            pieces=[]; read=0
            while read <= available:
                remaining=deadline-self.clock()
                if remaining<=0: raise BrowserPolicyError('request deadline reached')
                if connection.sock is not None: connection.sock.settimeout(remaining)
                try: part=response.read1(min(65536,available+1-read))
                except http.client.IncompleteRead as error:
                    # Bytes consumed before protocol failure still spend budget.
                    self.bytes += len(error.partial)
                    raise
                if not part: break
                pieces.append(part);read+=len(part);self.bytes+=len(part)
            body=b''.join(pieces)
            if len(body)>available:
                raise BrowserPolicyError('resource or episode byte budget exceeded')
            has_body=method!='HEAD' and response.status not in (204,304) and response.status>=200
            if has_body and lengths and len(body)!=int(lengths[0]):
                raise BrowserPolicyError('incomplete declared response body')
            if not has_body and body:
                raise BrowserPolicyError('unexpected response body')
            if self.clock() >= deadline:
                raise BrowserPolicyError('episode deadline reached')
            return FetchResult(url, response.status, incoming, body, address, secure)
        finally:
            connection.close()


def recv_frame(channel, maximum):
    def exact(count):
        pieces=[]
        while count:
            part=channel.recv(min(count,65536))
            if not part: raise BrowserPolicyError('truncated broker frame')
            pieces.append(part);count-=len(part)
        return b''.join(pieces)
    size=struct.unpack('!I', exact(4))[0]
    if not 1<=size<=maximum: raise BrowserPolicyError('broker frame budget exceeded')
    return exact(size)


def send_frame(channel, raw):
    channel.sendall(struct.pack('!I',len(raw))+raw)


class UnixBrokerClient:
    def __init__(self, path, expected_uid, limits=None):
        self.path=str(path);self.expected_uid=expected_uid;self.limits=limits or BrowserLimits()
        self.requests=0;self.bytes=0
        if type(expected_uid) is not int or expected_uid < 0:
            raise BrowserPolicyError('explicit broker UID required')

    def fetch(self,url,method='GET',headers=None):
        url=public_url(url)
        request=canonical({'schema':'merlin-browser-request/1','url':url,'method':method,'headers':headers or {}})
        if len(request)>MAX_REQUEST_ENVELOPE: raise BrowserPolicyError('request envelope budget exceeded')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
            channel.settimeout(self.limits.request_seconds+1)
            channel.connect(self.path)
            _,uid,_=struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid != self.expected_uid: raise BrowserPolicyError('broker peer identity differs')
            send_frame(channel,request)
            value=unique_json(recv_frame(channel,4*self.limits.max_resource_bytes//3+65536))
        if not isinstance(value,dict): raise BrowserPolicyError('invalid broker response')
        budget=value.get('budget')
        if (not isinstance(budget,dict) or set(budget)!={'requests','response_body_bytes'}
                or type(budget['requests']) is not int or not self.requests<=budget['requests']<=self.limits.max_requests
                or type(budget['response_body_bytes']) is not int or not self.bytes<=budget['response_body_bytes']<=self.limits.max_network_bytes+1):
            raise BrowserPolicyError('broker budget evidence differs')
        self.requests=budget['requests'];self.bytes=budget['response_body_bytes']
        if value.get('schema')=='merlin-browser-denial/1':
            if set(value)!={'schema','reason','budget'}: raise BrowserPolicyError('invalid broker denial')
            raise BrowserPolicyError(value.get('reason','broker denied'))
        fields={'schema','url','status','headers','body_base64','body_sha256','body_bytes','peer_ip','tls_verified','budget'}
        if set(value)!=fields or value['schema']!='merlin-browser-response/1' or value['url']!=url:
            raise BrowserPolicyError('broker response identity differs')
        raw=base64.b64decode(value['body_base64'],validate=True)
        if (len(raw)!=value['body_bytes'] or len(raw)>self.limits.max_resource_bytes
                or hashlib.sha256(raw).hexdigest()!=value['body_sha256']
                or type(value['status']) is not int or not 100<=value['status']<=599
                or value['tls_verified'] is not (urlsplit(url).scheme=='https')):
            raise BrowserPolicyError('broker response bytes or TLS binding differ')
        public_ip(value['peer_ip'])
        response_headers(value['headers'])
        return FetchResult(url,value['status'],value['headers'],raw,value['peer_ip'],value['tls_verified'])


def serve_broker(path, allowed_uid, limits=None):
    limits=limits or BrowserLimits()
    if type(allowed_uid) is not int or allowed_uid<1 or os.geteuid()==0:
        raise BrowserPolicyError('dedicated nonroot broker and browser UID required')
    path=Path(path)
    if path.exists() or path.is_symlink(): raise BrowserPolicyError('broker socket already exists')
    transport=PublicHTTPTransport(limits)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(path));os.chmod(path,0o600);server.listen(1);server.settimeout(0.5)
        try:
            while time.monotonic()-transport.started<limits.wall_seconds:
                try: channel,_=server.accept()
                except socket.timeout: continue
                with channel:
                    channel.settimeout(limits.request_seconds)
                    try:
                        _,uid,_=struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                        if uid!=allowed_uid: raise BrowserPolicyError('browser peer identity differs')
                        request=unique_json(recv_frame(channel,MAX_REQUEST_ENVELOPE))
                        if not isinstance(request,dict) or set(request)!={'schema','url','method','headers'} or request['schema']!='merlin-browser-request/1':
                            raise BrowserPolicyError('invalid browser request envelope')
                        result=transport.fetch(request['url'],request['method'],request['headers']).envelope()
                    except (BrowserPolicyError,ValueError,KeyError,TypeError,OSError,http.client.HTTPException) as error:
                        reason=str(error) if isinstance(error,BrowserPolicyError) else type(error).__name__
                        result={'schema':'merlin-browser-denial/1','reason':reason[:200]}
                    result['budget']={'requests':transport.requests,'response_body_bytes':transport.bytes}
                    try: send_frame(channel,canonical(result))
                    except OSError: pass  # Disconnected callers do not reset episode limits.
        finally:
            try:
                if stat.S_ISSOCK(path.lstat().st_mode): path.unlink()
            except FileNotFoundError: pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket',required=True);parser.add_argument('--browser-uid',type=int,required=True)
    parser.add_argument('--limits',required=True,type=Path)
    args=parser.parse_args()
    serve_broker(args.socket,args.browser_uid,BrowserLimits(**unique_json(args.limits.read_bytes())))


if __name__=='__main__': main()
