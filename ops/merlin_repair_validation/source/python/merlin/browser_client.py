"""Merlin caller for the fixed public browser Unix submit/read capability."""
from __future__ import annotations

import argparse
from pathlib import Path
import socket
import struct

from .browser_egress import canonical, recv_frame, send_frame, unique_json
from .browser_policy import BrowserLimits, BrowserPolicyError
from .browser_service import MAX_REQUEST, MAX_RESPONSE, SOCKET_PATH, validate_request


def request_browser(request, *, socket_path=SOCKET_PATH, expected_uid=0):
    validate_request(request,BrowserLimits())
    raw=canonical(request)
    if len(raw)>MAX_REQUEST: raise BrowserPolicyError('browser request byte budget exceeded')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
        channel.settimeout(85);channel.connect(str(socket_path))
        _,uid,_=struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=expected_uid: raise BrowserPolicyError('browser supervisor peer differs')
        send_frame(channel,raw);result=unique_json(recv_frame(channel,MAX_RESPONSE))
    if not isinstance(result,dict) or result.get('schema')!='merlin-browser-service-result/1':
        raise BrowserPolicyError('browser service response schema differs')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket',default=SOCKET_PATH)
    commands=parser.add_subparsers(dest='operation',required=True)
    submit=commands.add_parser('submit');submit.add_argument('--episode',required=True);submit.add_argument('--actions',required=True,type=Path)
    status=commands.add_parser('status');status.add_argument('--episode',required=True)
    read=commands.add_parser('read');read.add_argument('--episode',required=True);read.add_argument('--observation',required=True)
    read.add_argument('--kind',choices=('text','dom','screenshot','response_body'),default='text')
    read.add_argument('--start-byte',type=int,default=0);read.add_argument('--length-bytes',type=int,default=16384)
    read.add_argument('--link-start',type=int,default=0);read.add_argument('--link-limit',type=int,default=20)
    args=parser.parse_args()
    request={'schema':'merlin-browser-request-api/1','operation':args.operation,'episode_id':args.episode}
    if args.operation=='submit':
        if args.actions.stat().st_size>MAX_REQUEST: raise BrowserPolicyError('action plan byte budget exceeded')
        request['actions']=unique_json(args.actions.read_bytes())
    elif args.operation=='read':
        request.update(observation_id=args.observation,kind=args.kind,start_byte=args.start_byte,
                       length_bytes=args.length_bytes,link_start=args.link_start,link_limit=args.link_limit)
    result=request_browser(request,socket_path=args.socket)
    print(canonical(result).decode())
    return 0 if result.get('status') not in ('denied','failed','completed_with_failures') else 1


if __name__=='__main__': raise SystemExit(main())
