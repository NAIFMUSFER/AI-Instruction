"""Package only reviewed tracked release inputs; never traverse the working tree.

The manifest hashes the exact worktree bytes (including reviewed modifications),
while Git determines membership. A release must commit new files before packaging.
Vendored public assets are explicitly admitted from the build vendor manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ALLOWED_DIRS = {'public', 'tools', 'tests', 'supabase', 'docs', '.github', 'assets'}
ALLOWED_ROOT_SUFFIXES = {'.py','.js','.mjs','.json','.toml','.txt','.lock','.in','.md','.yaml','.yml','.sh'}
DENIED_PARTS = {'.git','.env','.venv','venv','node_modules','__pycache__','outputs','captures','screenshots','logs','.aws','.ssh','.config'}
DENIED_SUFFIXES = {'.pem','.key','.p12','.pfx','.sqlite','.sqlite3','.db','.log','.zip','.tar','.gz','.pyc'}


def admitted(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:return False
    if any(part.lower() in DENIED_PARTS or part.lower().startswith('.env') for part in p.parts):return False
    if p.suffix.lower() in DENIED_SUFFIXES:return False
    if any(word in p.name.lower() for word in ('credential','secret','private-key','private_key','id_rsa','id_ed25519')):return False
    return p.parts[0] in ALLOWED_DIRS or (len(p.parts)==1 and (p.suffix in ALLOWED_ROOT_SUFFIXES or p.name in {'Dockerfile','Makefile','LICENSE'}))


def package(root, output):
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode('utf-8').split('\0')
    names=sorted({name for name in tracked if name and admitted(name)})
    # tools/vendor.sh builds ignored browser dependencies. Only its own manifest
    # entries may supplement tracked inputs, and only beneath public/vendor/.
    manifest_path=root/'public/vendor/manifest.json'
    if manifest_path.exists():
        vendor=json.loads(manifest_path.read_text())
        rows=vendor.get('files', []) if isinstance(vendor,dict) else []
        for row in rows:
            name=row.get('path') if isinstance(row,dict) else row
            if isinstance(name,str):
                name=name if name.startswith('public/vendor/') else 'public/vendor/'+name.lstrip('/')
                if not name.startswith('public/vendor/') or not admitted(name):raise ValueError('RELEASE_VENDOR_PATH_REJECTED')
                if not isinstance(row,dict) or hashlib.sha256((root/name).read_bytes()).hexdigest()!=row.get('sha256'):raise ValueError('RELEASE_VENDOR_HASH_MISMATCH')
                names.append(name)
    if manifest_path.exists():names.append('public/vendor/manifest.json')
    names=sorted(set(names))
    records=[]
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            file=root/name
            if file.is_symlink():raise ValueError('RELEASE_SYMLINK_REJECTED: '+name)
            if not file.is_file():raise ValueError('RELEASE_TRACKED_FILE_MISSING: '+name)
            data=file.read_bytes();archive.writestr(name,data)
            records.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        archive.writestr('RELEASE-MANIFEST.json',json.dumps({'schema':'acs-release-manifest/1.0','source':'git tracked release inputs + explicit vendor manifest','files':records},indent=2)+'\n')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--output',required=True);args=parser.parse_args()
    records=package(Path(args.root).resolve(),Path(args.output).resolve())
    print('Packaged %d allowlisted files with SHA-256 manifest' % len(records))
