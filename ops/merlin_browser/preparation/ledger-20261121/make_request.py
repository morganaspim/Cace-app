"""Create one fixed request locally after independent review and host preflight.

This program neither publishes the file nor dispatches GitHub Actions.
"""
import argparse
import datetime
import json
from pathlib import Path
import uuid


def request_document(request_id, created_at):
    if not isinstance(request_id, str) or str(uuid.UUID(request_id)) != request_id:
        raise ValueError('canonical fresh UUID required')
    if request_id in ('18106dfc-0a56-4b68-9d30-5d334d7d6a69',
                       '4e9b1d59-f966-44ed-a2c1-329aa77aa22e',
                       '04d38719-4c94-4059-988b-9081375fd209'):
        raise ValueError('predecessor request must not be replayed')
    stamp = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
    if stamp.strftime('%Y-%m-%dT%H:%M:%SZ') != created_at:
        raise ValueError('canonical UTC timestamp required')
    return {'schema': 'merlin-browser-runtime-request/1', 'operation': 'complete-ledger-44946846703',
            'request_id': request_id, 'created_at': created_at}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--created-at', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = request_document(args.request_id, args.created_at)
    if args.output.name != args.request_id + '.json':
        raise ValueError('request file basename must be the exact UUID')
    with args.output.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode())
    print(json.dumps({'request': value, 'local_path': str(args.output.absolute()),
                      'remote_publication': False, 'dispatch': False}, sort_keys=True))


if __name__ == '__main__':
    main()
