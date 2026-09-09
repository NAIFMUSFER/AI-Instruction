"""Apply proposed client-only downloads; tests must pass before committing runtime."""
from pathlib import Path
import subprocess,hashlib,json
root=Path('masar-studio');stage=Path('.masar-ops/material-downloads-20260909')
blobs={'src/three-viewer.mjs':'2b56d68ab110b96ae85c4ec83dcadfaa762037a3','src/render-ui.js':'0c0959c5bed5f37caa26777cf6bd3433d6adde03','render-viewer/runtime-entry.mjs':'488528925beb2bf6e80c3718480717882df57b65','render-viewer/package-viewer.mjs':'33055a6b96917f10e2f8b3bb29db937314ee9b3a'}
for name,sha in blobs.items():assert subprocess.check_output(['git','hash-object',str(root/name)],text=True).strip()==sha,'Changed source: '+name
def replace(name,old,new):
    p=root/name;s=p.read_text();assert s.count(old)==1,(name,old,s.count(old));p.write_text(s.replace(old,new))
for name,destination in [('material-downloads.js','src/material-downloads.js'),('material-downloads.test.mjs','tests/material-downloads.test.mjs'),('material_downloads_browser.py','tests/material_downloads_browser.py'),('material_glb_blender.py','tests/material_glb_blender.py')]:
    assert not (root/destination).exists();(root/destination).write_bytes((stage/name).read_bytes())
loader="import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';"
replace('src/three-viewer.mjs',loader,loader+"\nimport { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';")
replace('src/three-viewer.mjs','let root=null,disposed=false,selection=null,originals=new Map();','let root=null,disposed=false,selection=null,currentSpec=null,originals=new Map();')
replace('src/three-viewer.mjs','        setScene(spec){','        setScene(spec){\n            if(disposed)throw Error(\'المعاينة مغلقة.\');\n            currentSpec=structuredClone(spec);')
replace('src/three-viewer.mjs',"            install(gltf.scene);canvas.dataset.source='blender-glb';","            install(gltf.scene);currentSpec=null;canvas.dataset.source='blender-glb';")
replace('src/three-viewer.mjs','        select:highlight,',(stage/'viewer-methods.txt').read_text()+'        select:highlight,')
p=root/'render-viewer/runtime-entry.mjs';p.write_text(p.read_text()+"export {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';\n")
replace('render-viewer/package-viewer.mjs','"'+loader+'"','"'+loader+'", "import { GLTFExporter } from \'three/addons/exporters/GLTFExporter.js\';"')
replace('render-viewer/package-viewer.mjs','{THREE,OrbitControls,GLTFLoader}','{THREE,OrbitControls,GLTFLoader,GLTFExporter}')
p=root/'src/render-ui.js';p.write_text("import { attachMaterialDownloads } from './material-downloads.js';\n"+p.read_text())
replace('src/render-ui.js','let disposed=false,busy=false,viewer=null,poll=null,capabilities=', 'let downloads=null,previewBusy=false;let disposed=false,busy=false,viewer=null,poll=null,capabilities=')
replace('src/render-ui.js','disposed=true;clearTimeout(poll);viewer?.dispose();','disposed=true;clearTimeout(poll);downloads?.dispose();viewer?.dispose();')
replace('src/render-ui.js','    async function ensureViewer(){','    downloads=attachMaterialDownloads({host,getViewer:()=>viewer,getSnapshot:snapshot,isAlive:alive,reportError});\n    async function ensureViewer(){')
old="""    $('#render-pbr').addEventListener('click',execute(async()=>{const s=snapshot(),v=await ensureViewer();v?.setScene(s);v?.cutaway($('#render-cutaway').checked);
        if(alive()){$('#render-canvas').dataset.sourceModel=s.source.modelId;$('#render-canvas').dataset.sourceRevision=s.source.revisionId;}}));"""
new="""    $('#render-pbr').addEventListener('click',execute(async()=>{
        if(previewBusy)return;previewBusy=true;$('#render-pbr').disabled=true;downloads.invalidate();
        try {const s=snapshot(),v=await ensureViewer();if(!v||!alive())return;v.setScene(s);v.cutaway($('#render-cutaway').checked);
            $('#render-canvas').dataset.sourceModel=s.source.modelId;$('#render-canvas').dataset.sourceRevision=s.source.revisionId;downloads.setSource(s);
        } finally {previewBusy=false;if(alive())$('#render-pbr').disabled=false;}
    }));"""
replace('src/render-ui.js',old,new)
replace('src/render-ui.js',"if(action==='glb'){if(job.stale", "if(action==='glb'){downloads.invalidate();if(job.stale")
replace('tools/build.mjs',"'src/render-ui.js'","'src/material-downloads.js','src/render-ui.js'")
replace('public/sw.js','masar-4.1.0-shell-v8-room-review','masar-4.1.0-shell-v9-visual-downloads')
replace('public/sw.js',"'/src/render-ui.js'","'/src/material-downloads.js','/src/render-ui.js'")
replace('tests/browser_http.py',"'/src/render-ui.js'","'/src/material-downloads.js', '/src/render-ui.js'")
for name in ['material_downloads_browser.py','material_glb_blender.py']:compile((root/'tests'/name).read_text(),name,'exec')
out=root/'test-output/material-downloads';out.mkdir(parents=True,exist_ok=True)
changed=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()
(out/'source-hashes.json').write_text(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in changed},indent=2))
print('Applied candidate; no runtime commit or deployment before all acceptance gates.')
