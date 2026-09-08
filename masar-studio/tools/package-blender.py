"""Package only app source, the compiled MIT viewer and validation evidence.
No Blender installation, credentials, databases, font files or node_modules.
"""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1] if len(sys.argv)>1 else root/'delivery-blender').resolve();out.mkdir(parents=True,exist_ok=True)
allowed={'shared','src','server','public','tools','tests','render-worker','render-viewer','docs','dist'}
files=[]
for p in root.rglob('*'):
    rel=p.relative_to(root)
    if not p.is_file() or p.is_symlink() or any(x in rel.parts for x in ['node_modules','.git','__pycache__','test-output']):continue
    if rel.parts[0] not in allowed and str(rel) not in ['package.json','package-lock.json','Dockerfile','compose.yaml','.dockerignore','.gitignore','.node-version','.env.example','start.sh','start-windows.cmd']:continue
    if p.suffix.lower() in ['.woff','.woff2','.ttf','.otf','.sqlite','.db','.blend','.pyc']:continue
    if rel.parts[0]=='docs' and p.suffix!='.md':continue
    files.append((rel,p.read_bytes()))
try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
except Exception:commit=None
manifest={'product':'MASAR Blender Integration candidate v1','base':'580e0e11434adf9ff9e08cc5d9bf867dd0f4443b','sourceCommit':commit,'files':{str(n):hashlib.sha256(b).hexdigest() for n,b in files},'warning':'Not a deployed cloud Blender worker or architectural approval. See docs/BLENDER-INTEGRATION.md.'}
files.append((Path('BLENDER-RELEASE-MANIFEST.json'),json.dumps(manifest,indent=2).encode()))
files.append((Path('README.md'),(root/'docs/BLENDER-INTEGRATION.md').read_bytes()))
zip_path=out/'Masar-Blender-Integration-v1-Source.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files):
        info=zipfile.ZipInfo('masar-studio/'+str(name),(2026,9,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
(out/'Masar-Blender-Integration-v1.html').write_bytes((root/'dist/index.html').read_bytes())
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print(json.dumps({'source':str(zip_path),'files':len(files),'bytes':zip_path.stat().st_size,'sourceCommit':commit}))
