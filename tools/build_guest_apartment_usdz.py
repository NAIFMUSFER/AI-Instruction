"""Build and verify the named Quick Look asset. Netlify only needs --install (stdlib)."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = 'assets/guest/apartment-20x25.usdz.gz'
MANIFEST = 'assets/guest/apartment-20x25.usdz.json'
PUBLIC = 'public/guest-plans/apartment-20x25.usdz'


def inspect_archive(blob):
    """Verify the stored, self-contained USDZ layout independently of the exporter."""
    with zipfile.ZipFile(io.BytesIO(blob)) as package:
        files = package.infolist()
        if not files or files[0].filename != 'model.usda' or package.testzip() is not None:
            raise ValueError('Invalid USDZ root layer or member CRC')
        if len({f.filename for f in files}) != len(files):
            raise ValueError('Duplicate USDZ member')
        for f in files:
            if f.compress_type != zipfile.ZIP_STORED or f.flag_bits & 1 or not f.filename.endswith('.usda'):
                raise ValueError('Quick Look sample requires local, unencrypted, stored USD layers')
            path_length, extra_length = struct.unpack_from('<HH', blob, f.header_offset + 26)
            if (f.header_offset + 30 + path_length + extra_length) % 64:
                raise ValueError('USDZ layer is not aligned on a 64-byte boundary')
            if not package.read(f).startswith(b'#usda 1.0\n'):
                raise ValueError('Invalid USD layer')
        stage = package.read(files[0]).decode()
        if 'metersPerUnit = 1' not in stage or 'upAxis = "Y"' not in stage:
            raise ValueError('USD stage has unexpected units/axis')
        for other in files[1:]:
            if f'@./{other.filename}@' not in stage:
                raise ValueError('USD stage does not reference a packed mesh')


def verified_payload(root=ROOT):
    for name in (PAYLOAD, MANIFEST):
        if (root / name).is_symlink():
            raise ValueError('Quick Look sources must be regular tracked files')
    manifest = json.loads((root / MANIFEST).read_text())
    expected = manifest['bytes']
    if not isinstance(expected, int) or not 0 < expected < 16_000_000:
        raise ValueError('USDZ size is outside the display sample limit')
    with gzip.open(root / PAYLOAD, 'rb') as source:
        blob = source.read(expected + 1)
    if len(blob) != expected or hashlib.sha256(blob).hexdigest() != manifest['sha256']:
        raise ValueError('Quick Look asset differs from its tracked manifest')
    inspect_archive(blob)
    return blob


def install(root=ROOT):
    blob = verified_payload(root)
    dest = root / PUBLIC
    dest.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=dest.parent, delete=False) as temp:
        temp.write(blob)
    os.chmod(temp.name, 0o644)
    os.replace(temp.name, dest)
    return dest


def from_canonical():
    sys.path.insert(0, str(ROOT))
    from acs_compiler import compile_building
    from acs_context_details import with_context_details
    from acs_roof import with_default_roof
    from acs_stairs import with_default_stairs
    script = """import {apartmentSample} from './public/app/core/local-apartment.mjs';
                console.log(JSON.stringify(apartmentSample()));"""
    model = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], cwd=ROOT))
    for derive in (with_default_stairs, with_default_roof, with_context_details):
        model, _, error = derive(model)
        if error:
            raise ValueError(error)
    with TemporaryDirectory() as tmp:
        source, target = Path(tmp) / 'apartment.gltf', Path(tmp) / 'apartment.usdz'
        compile_building(model, source)
        report = subprocess.check_output(['node', str(ROOT / 'tools/guest_apartment_usdz.mjs'),
                                         str(source), str(target)], cwd=ROOT)
        blob = target.read_bytes()
    inspect_archive(blob)
    return blob, json.loads(report)


def build(check):
    blob, stats = from_canonical()
    if check:
        if blob != verified_payload():
            raise ValueError('Stale Quick Look asset. Rebuild with --refresh.')
        if stats != json.loads((ROOT / MANIFEST).read_text())['verification']:
            raise ValueError('Stale Quick Look geometry evidence')
        return
    (ROOT / PAYLOAD).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / PAYLOAD).open('wb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', compresslevel=9, mtime=0) as stream:
            stream.write(blob)
    manifest = {'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob), 'verification': stats}
    (ROOT / MANIFEST).write_text(json.dumps(manifest, indent=2)+'\n')
    install()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--install', action='store_true', help='Materialize the verified stored asset at its published URL.')
    action.add_argument('--refresh', action='store_true', help='Compile the current public sample and update its compressed source.')
    action.add_argument('--check', action='store_true', help='Independently decode and compare the current sample to the tracked asset.')
    args = parser.parse_args()
    if args.install:
        install()
    else:
        build(args.check)
    print('Verified apartment Quick Look USDZ')
