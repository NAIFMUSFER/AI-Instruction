from pathlib import Path
import subprocess,json,hashlib,zipfile,shutil,re
root=Path('masar-studio');dest=Path('delivery');dest.mkdir(exist_ok=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
paths={p for p in subprocess.check_output(['git','ls-files','masar-studio'],text=True).splitlines() if Path(p).is_file()}
paths.update('masar-studio/'+p for p in ['dist/index.html','dist/app.bundle.js','public/render-engine.js','public/render-viewer.js','public/render-viewer-integrity.json'])
paths={p for p in paths if not any(x in Path(p).parts for x in ['node_modules','test-output','.git','fonts']) and Path(p).suffix.lower() not in ['.woff','.woff2','.ttf','.otf','.eot','.sqlite','.db'] and Path(p).name!='.env'}
manifest={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(paths)}
with zipfile.ZipFile(dest/'MASAR-View-Controls-Source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(paths):archive.write(p,p)
    archive.writestr('VIEW-CONTROLS-MANIFEST.json',json.dumps({'sourceCommit':commit,'sha256':manifest},indent=2))
shutil.copy(root/'dist/index.html',dest/'MASAR-View-Controls-Standalone.html')
checks=[]
for engine in ['chromium','webkit']:
    for suite in ['view-controls','material-downloads','room-review','plan-inspection','layout-quality-ui']:
        p=root/'test-output'/suite/engine/'report.json'
        result=json.loads(p.read_text());assert result['failed']==0
        checks.append({'suite':suite,'engine':engine,'passed':result['passed'],'failed':result['failed']})
for p in sorted((root/'test-output/customer-ui').glob('*report.json')):
    result=json.loads(p.read_text());assert result['failed']==0
    checks.append({'suite':'exact-customer-request','engine':result.get('engine',p.name),'passed':result['passed'],'failed':result['failed']})
for p,name in [('chalet-floor.png','MASAR-Chalet-Floor-View.png'),('multifloor-selected.png','MASAR-Selected-Floor-View.png'),('view-controls-mobile.png','MASAR-View-Controls-Mobile.png'),('isolated-full-model.glb','MASAR-Three-Floors-Complete.glb'),('multifloor-before.json','MASAR-Three-Floors-Project.json')]:
    shutil.copy(root/'test-output/view-controls/chromium'/p,dest/name)
shutil.copy(root/'test-output/view-controls/chromium/chalet-390-top.png',dest/'MASAR-Chalet-Top-View.png')
(dest/'BROWSER-SUMMARY.json').write_text(json.dumps(checks,indent=2))
(dest/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(dest.iterdir()) if p.is_file()))
