"""Create a source + independently built standalone release, never include private databases."""
import argparse,hashlib,json,os,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',default='../delivery');p.add_argument('--evidence');args=p.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
version=json.loads((ROOT/'package.json').read_text())['version'];commit=os.environ.get('GITHUB_SHA') or os.environ.get('GIT_COMMIT') or None
ignore={'.git','node_modules','data','backups','test-output','__pycache__','dist'}
files={}
for file in ROOT.rglob('*'):
    rel=file.relative_to(ROOT)
    if not file.is_file() or any(part in ignore for part in rel.parts):continue
    if file.name=='.env' or (file.name.startswith('.env.') and file.name!='.env.example') or file.suffix in {'.zip','.sqlite','.db','.pyc','.png'} or '.sqlite-' in file.name:continue
    files[str(rel)]=file.read_bytes()
for name in ['index.html','app.bundle.js']:
    files['dist/'+name]=(ROOT/'dist'/name).read_bytes()
if args.evidence:
    evidence=Path(args.evidence)
    for file in evidence.rglob('*'):
        if file.is_file() and file.suffix.lower() in {'.json','.md','.log','.txt','.png','.ifc'}:
            files['docs/verification/'+str(file.relative_to(evidence))]=file.read_bytes()
manifest={'release':version,'commit':commit,'scope':'Full-stack conceptual architectural studio. No regulatory approval or public deployment implied.','files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in sorted(files.items())}}
files['RELEASE-MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
archive=out/f'Masar-Studio-{version}-Source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files.items()):
        info=zipfile.ZipInfo('masar-studio/'+name,date_time=(2026,9,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o644<<16);z.writestr(info,data)
html=out/f'Masar-Studio-{version}.html';html.write_bytes(files['dist/index.html'])
sha={archive.name:hashlib.sha256(archive.read_bytes()).hexdigest(),html.name:hashlib.sha256(html.read_bytes()).hexdigest()}
(out/'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name,digest in sha.items()))
(out/'release.json').write_text(json.dumps({'release':version,'commit':commit,'fileCount':len(files),'artifacts':sha,'verification':'See separate clean-unpack verification job and included machine-readable reports.'},indent=2))
print(json.dumps({'release':version,'files':len(files),'artifacts':sha}))
