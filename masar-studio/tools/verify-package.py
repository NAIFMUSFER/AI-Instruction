"""Verify an unpacked release inventory, including no added/omitted files."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);manifest=json.loads((root/'RELEASE-MANIFEST.json').read_text())
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-{'RELEASE-MANIFEST.json'}
assert actual==set(manifest['files']),{'extra':sorted(actual-set(manifest['files'])),'missing':sorted(set(manifest['files'])-actual)}
for name,record in manifest['files'].items():
    file=(root/name).resolve();assert file.is_relative_to(root.resolve());data=file.read_bytes();assert len(data)==record['bytes'];assert hashlib.sha256(data).hexdigest()==record['sha256'],name
print(json.dumps({'manifest':'PASS','release':manifest['release'],'commit':manifest['commit'],'files':len(actual)}))
