"""Build a machine-derived release summary only after live and package gates."""
from pathlib import Path
import hashlib,json,os,re,zipfile
root=Path('masar-studio');out=root/'test-output/view-controls';delivery=Path('delivery')
def node_counts(path):
    text=Path(path).read_text()
    counts={k:int(re.search(r'^# '+k+r' (\d+)$',text,re.M).group(1)) for k in ['tests','pass','fail','skipped']}
    assert counts['tests']>0 and counts['tests']==counts['pass'] and not counts['fail'] and not counts['skipped'],counts
    return counts
checks=json.loads((delivery/'BROWSER-SUMMARY.json').read_text())
assert checks and all(row['failed']==0 and row['passed']>0 for row in checks)
package=json.loads(Path('recheck/masar-studio/test-output/view-controls/chromium/report.json').read_text())
assert package['failed']==0 and package['passed']>0
assert Path('recheck/masar-studio/dist/index.html').read_bytes()==(delivery/'MASAR-View-Controls-Standalone.html').read_bytes()
glbs=[]
for p in sorted((out/'chromium').glob('*.validation.json')):
    result=json.loads(p.read_text());issues=result['issues']
    assert issues['numErrors']==0 and issues['numWarnings']==0
    glbs.append({'file':p.name,'errors':issues['numErrors'],'warnings':issues['numWarnings'],'infos':issues['numInfos']})
assert len(glbs)==2
with zipfile.ZipFile(delivery/'MASAR-View-Controls-Source.zip') as z:
    manifest=json.loads(z.read('VIEW-CONTROLS-MANIFEST.json'))
    for path,digest in manifest['sha256'].items():
        assert hashlib.sha256(z.read(path)).hexdigest()==digest,path
summary={'sourceCommit':os.environ['MASAR_EXPECTED_COMMIT'],'workflowRun':int(os.environ['GITHUB_RUN_ID']),
    'deployment':json.loads((out/'deployment.json').read_text()),
    'node':node_counts(out/'node.log'),'cleanPackageNode':node_counts('recheck/package-node.log'),
    'cleanPackageHTMLByteMatch':True,'cleanPackageBrowser':{'engine':package['engine'],'passed':package['passed'],'failed':package['failed']},
    'browserResults':checks,'liveChecksPassed':sum(row['passed'] for row in checks),'liveChecksFailed':0,
    'khronosGLB':glbs,'sourceFileCount':len(manifest['sha256']),
    'sourceZipSHA256':hashlib.sha256((delivery/'MASAR-View-Controls-Source.zip').read_bytes()).hexdigest(),
    'scope':'Display-only 3D floor isolation, aspect-safe perspective presets, hidden-object picking and complete GLB preservation. Chromium software WebGL tested; WebKit covers UI/source/history, not its GPU rendering or physical iPhone. No architectural redesign, orthographic elevations, survey compass verification, cloud rendering or paid storage.'}
(delivery/'LIVE-SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(delivery/'README.txt').write_text(
    'MASAR floor and camera controls\n'
    'Published preview: https://masar-customer-preview.onrender.com\n'
    'In the material preview, generate the actual scene then choose a floor and camera.\n'
    'PNG captures visible scope; GLB preserves all floors and roofs. MASAR JSON remains the editable backup.\n'
    'These are conceptual views, not orthographic elevations, survey directions or construction approval.\n'
    'WebKit UI was checked, not physical iPhone GPU export. No cloud renderer or durable server storage.\n'
    'Source provenance and measured verification: LIVE-SUMMARY.json and VIEW-CONTROLS-MANIFEST.json in the source ZIP.\n')
(delivery/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(delivery.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print(json.dumps(summary,ensure_ascii=False,indent=2))
