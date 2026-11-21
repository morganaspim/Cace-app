"""Reproduce a two-member derivative of the exact installed browser runtime.

This file performs no native execution, extraction into a host runtime,
network acquisition, package installation, or remote mutation.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
BASE = Path('/workspace/scratch/abed42219434/browser-operations')
REPAIR = Path('/workspace/scratch/abed42219434/browser-ledger-successor')
PRODUCT_COMMIT = '74bd09166f338172f4af3854a124c12b5b07081a'
ORIGINAL_SHA256 = '5b967b6364bb8d3213c357e148c43073c309ab45d13338fe577d13565f8d0e9d'
ORIGINAL_MANIFEST = 'ea5ea521f055273cd6d82c8a164f6e713172ecf0db51bddefc915a3548ff1ef6'
REPLACEMENTS = {
    'python/merlin/public_browser.py': {
        'source_path': 'python/merlin/public_browser.py',
        'bytes': 29083,
        'sha256': '9bddbc4343b5c6acb88c9d5b12f869290056f1913b93a2203774129d8975e884',
        'git_blob': 'c05e2299652698eb6b1003f71b15d8bfb8badd47',
    },
    'python/tests/test_public_browser.py': {
        'source_path': 'tests/test_public_browser.py',
        'bytes': 46706,
        'sha256': '4e3c7fb0a708dd838d2305a4e185bd3e3d508f0ee4780e4bf848a5644642d269',
        'git_blob': 'e6593fb87528b04d1104f2183c29ea6c3d7a4da6',
    },
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def render(infos, members, comment):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.comment = comment
        for info in infos:
            archive.writestr(copy.copy(info), members[info.filename],
                             compress_type=info.compress_type, compresslevel=6)
    return output.getvalue()


def build(original, replacements):
    if len(original) != 66202 or sha(original) != ORIGINAL_SHA256:
        raise ValueError('exact installed runtime archive required')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        infos = archive.infolist()
        comment = archive.comment
        if len(infos) != 15 or len({info.filename for info in infos}) != 15:
            raise ValueError('exact installed member set required')
        old = {info.filename: archive.read(info) for info in infos}
    if sha(old['manifest.json']) != ORIGINAL_MANIFEST:
        raise ValueError('exact installed manifest required')
    manifest = json.loads(old['manifest.json'])
    if (manifest.get('schema') != 'merlin-browser-runtime/1'
            or len(manifest.get('files', [])) != 14
            or set(old) != {'manifest.json'} | {row['path'] for row in manifest['files']}):
        raise ValueError('installed manifest closure differs')
    for row in manifest['files']:
        raw = old[row['path']]
        if (len(raw), sha(raw), blob(raw)) != (row['bytes'], row['sha256'], row['git_blob']):
            raise ValueError('installed runtime member differs')
    if render(infos, old, comment) != original:
        raise ValueError('installed deterministic ZIP settings differ')
    if set(replacements) != set(REPLACEMENTS):
        raise ValueError('only producer and its regression file may change')
    members = dict(old)
    for name, pin in REPLACEMENTS.items():
        raw = replacements[name]
        if (len(raw), sha(raw), blob(raw)) != (pin['bytes'], pin['sha256'], pin['git_blob']):
            raise ValueError('published successor source identity differs')
        ast.parse(raw, feature_version=(3, 9))
        members[name] = raw
    for row in manifest['files']:
        name = row['path']
        if name in REPLACEMENTS:
            pin = REPLACEMENTS[name]
            row.update(bytes=pin['bytes'], sha256=pin['sha256'], git_blob=pin['git_blob'])
            row['origin'] = {'repository': 'Mannyspiro/expert-robot',
                             'commit': PRODUCT_COMMIT, 'path': pin['source_path']}
    # Preserve the original product identity for unchanged members. Each changed
    # member has its own immutable new source; this is an explicitly mixed
    # derivative, not a claim that every old payload was rebuilt from new HEAD.
    manifest['derivation'] = {
        'kind': 'resource-accounting-producer-and-regression-successor',
        'parent_runtime_sha256': ORIGINAL_SHA256,
        'parent_manifest_sha256': ORIGINAL_MANIFEST,
        'successor_product_commit': PRODUCT_COMMIT,
        'changed_payloads': sorted(REPLACEMENTS),
    }
    members['manifest.json'] = canonical(manifest)
    payload = render(infos, members, comment)
    unchanged = sorted(set(old) - set(REPLACEMENTS) - {'manifest.json'})
    if len(unchanged) != 12 or any(old[name] != members[name] for name in unchanged):
        raise ValueError('an unrelated installed payload changed')
    pin = {'bytes': len(payload), 'sha256': sha(payload), 'git_blob': blob(payload),
           'expert_source_commit': manifest['expert_source_commit']}
    report = {
        'schema': 'merlin-browser-ledger-runtime-derivation/1',
        'parent_runtime_sha256': ORIGINAL_SHA256,
        'parent_manifest_sha256': ORIGINAL_MANIFEST,
        'successor_product_commit': PRODUCT_COMMIT,
        'runtime': pin,
        'runtime_manifest_sha256': sha(members['manifest.json']),
        'changed_members': sorted(REPLACEMENTS) + ['manifest.json'],
        'unchanged_payload_members': unchanged,
        'unchanged_payload_count': len(unchanged),
        'zipinfo_metadata_and_member_order_preserved': True,
        'original_archive_reconstructed_exactly': True,
        'source_pins': REPLACEMENTS,
        'native_execution': False, 'package_installs': 0,
        'new_browser_acquisitions': 0, 'model_calls': 0,
    }
    return payload, members['manifest.json'], pin, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, default=BASE / 'runtime-loader-44944977868/merlin-browser-runtime.zip')
    parser.add_argument('--producer', type=Path, default=REPAIR / 'python/merlin/public_browser.py')
    parser.add_argument('--tests', type=Path, default=REPAIR / 'tests/test_public_browser.py')
    parser.add_argument('--output', type=Path, default=ROOT / 'runtime')
    args = parser.parse_args()
    old = args.original.read_bytes()
    replacements = {'python/merlin/public_browser.py': args.producer.read_bytes(),
                    'python/tests/test_public_browser.py': args.tests.read_bytes()}
    payload, manifest, pin, report = build(old, replacements)
    target = args.output
    target.mkdir(mode=0o700, exist_ok=False)
    for name, raw in (
        ('merlin-browser-runtime.zip', payload), ('manifest.json', manifest),
        ('runtime-pins.json', canonical(pin)), ('package-verification.json', canonical(report)),
    ):
        with (target / name).open('xb') as stream:
            stream.write(raw)
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
