"""Bounded public-web policy shared by the renderer and its egress broker.

This is a public source-reading capability. It neither imports account sessions
nor grants research promotion, installation, code execution or repository writes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import ipaddress
import re
from urllib.parse import quote, urlsplit, urlunsplit


class BrowserPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class BrowserLimits:
    wall_seconds: int = 60
    action_seconds: int = 15
    request_seconds: int = 10
    max_actions: int = 8
    max_requests: int = 64
    max_resource_bytes: int = 1024 * 1024
    max_network_bytes: int = 8 * 1024 * 1024
    max_text_bytes: int = 256 * 1024
    max_dom_bytes: int = 512 * 1024
    max_screenshot_bytes: int = 1024 * 1024
    max_evidence_bytes: int = 12 * 1024 * 1024
    max_links: int = 100

    def __post_init__(self):
        ceilings = dict(wall_seconds=60, action_seconds=20, request_seconds=10,
                        max_actions=12, max_requests=96, max_resource_bytes=2*1024*1024,
                        max_network_bytes=12*1024*1024, max_text_bytes=512*1024,
                        max_dom_bytes=1024*1024, max_screenshot_bytes=2*1024*1024,
                        max_evidence_bytes=24*1024*1024, max_links=200)
        for name, limit in ceilings.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= limit:
                raise BrowserPolicyError('invalid fixed browser budget: ' + name)
        if self.request_seconds > self.action_seconds or self.action_seconds > self.wall_seconds:
            raise BrowserPolicyError('browser timeout budgets must be nested')
        if self.max_evidence_bytes < 262144:
            raise BrowserPolicyError('evidence budget must reserve durable finalization space')

    def to_dict(self):
        return asdict(self)


EXCLUDED_DOMAINS = ('chatgpt.com', 'chat.openai.com', 'chat.com')
DENIED_V4 = tuple(ipaddress.ip_network(value) for value in (
    '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8', '169.254.0.0/16',
    '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24', '192.88.99.0/24',
    '192.168.0.0/16', '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24',
    '224.0.0.0/4', '240.0.0.0/4'))
DENIED_V6 = tuple(ipaddress.ip_network(value) for value in (
    '::/96', '::ffff:0:0/96', '64:ff9b::/96', '64:ff9b:1::/48', '2001::/32', '2002::/16'))


def public_ip(value: str) -> str:
    if not isinstance(value, str) or '%' in value:
        raise BrowserPolicyError('nonpublic address')
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise BrowserPolicyError('invalid address') from None
    denied = DENIED_V4 if address.version == 4 else DENIED_V6
    if (not address.is_global or address.is_multicast or address.is_reserved
            or address.is_unspecified or address.is_loopback or address.is_link_local
            or any(address in network for network in denied)):
        raise BrowserPolicyError('nonpublic address')
    return str(address)


def public_url(value: str) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 8192
            or any(ord(c) < 33 or ord(c) == 127 for c in value) or '\\' in value):
        raise BrowserPolicyError('invalid public URL')
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
        if parsed.scheme not in ('http', 'https') or not hostname or parsed.username is not None or parsed.password is not None:
            raise BrowserPolicyError('HTTP(S) without embedded credentials required')
        hostname = hostname.rstrip('.').encode('idna').decode('ascii').lower()
        if '%' in hostname or any(hostname == name or hostname.endswith('.'+name) for name in EXCLUDED_DOMAINS):
            raise BrowserPolicyError('excluded source')
        if port not in (None, 80 if parsed.scheme == 'http' else 443):
            raise BrowserPolicyError('public web standard port required')
        try:
            public_ip(hostname)
        except BrowserPolicyError:
            try:
                ipaddress.ip_address(hostname)
            except ValueError:
                if (not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', hostname)
                        or '.' not in hostname or '..' in hostname
                        or hostname.endswith(('.localhost', '.local', '.internal', '.test', '.invalid'))):
                    raise BrowserPolicyError('public DNS hostname required')
            else:
                raise
        netloc = '['+hostname+']' if ':' in hostname else hostname
        path = quote(parsed.path or '/', safe="/%:@!$&'()*+,;=-._~")
        query = quote(parsed.query, safe="%/:?@!$&'()*+,;=-._~")
        return urlunsplit((parsed.scheme, netloc, path, query, ''))
    except (UnicodeError, ValueError) as error:
        if isinstance(error, BrowserPolicyError):
            raise
        raise BrowserPolicyError('invalid public URL') from None


def search_url(query: str, template: str = 'https://www.bing.com/search?q={query}') -> str:
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise BrowserPolicyError('bounded nonempty search query required')
    if not isinstance(template, str) or template.count('{query}') != 1:
        raise BrowserPolicyError('one query placeholder required')
    return public_url(template.replace('{query}', quote(query, safe='')))


def bounded_utf8(value: str, limit: int):
    raw = value.encode('utf-8')
    if len(raw) <= limit:
        return raw, False
    return raw[:limit].decode('utf-8', errors='ignore').encode('utf-8'), True


def utf8_range(raw: bytes, start: int, length: int):
    if type(start) is not int or type(length) is not int or start<0 or start>len(raw) or length<1:
        raise BrowserPolicyError('invalid captured text byte range')
    while start<len(raw) and raw[start]&0xc0==0x80: start+=1
    end=min(len(raw),start+length)
    while end<len(raw) and raw[end]&0xc0==0x80: end-=1
    if end==start and start<len(raw):
        raise BrowserPolicyError('text range is too short for the next UTF-8 character')
    return start,end,raw[start:end]
