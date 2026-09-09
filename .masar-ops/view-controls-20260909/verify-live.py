"""Read-only deployment verification. Never creates accounts or changes server state."""
from pathlib import Path
import hashlib,json,os,subprocess,time,urllib.request
origin='https://masar-customer-preview.onrender.com'
expected=os.environ['MASAR_EXPECTED_COMMIT']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==expected
root=Path('masar-studio');out=root/'test-output/view-controls';out.mkdir(parents=True,exist_ok=True)
def get(path):
    request=urllib.request.Request(origin+path,headers={'Cache-Control':'no-cache','User-Agent':'MASAR-ReadOnly-Acceptance'})
    with urllib.request.urlopen(request,timeout=90) as response:
        assert response.status==200,(path,response.status)
        return response.read(),dict(response.headers)
last=None
for attempt in range(4):
    try:
        body,headers=get('/api/version');version=json.loads(body)
        assert version['commit']==expected,version
        break
    except Exception as exc:
        last=exc
        if attempt==3:raise
        time.sleep(5)
health=json.loads(get('/api/health')[0]);ready=json.loads(get('/api/ready')[0]);renders=json.loads(get('/api/renders/capabilities')[0])
assert health['ok'] and ready['ready']
assert health['persistenceClass']=='ephemeral' and ready['persistenceClass']=='ephemeral'
assert health['aiConfigured'] is False
assert renders['enabled'] is False and renders['workerOnline'] is False
hashes={}
for path in ['shared/view-navigation.js','src/render-ui.js','src/material-downloads.js','src/app.js','src/room-review.js','src/plan-inspection.js','shared/model.js','src/style.css','public/sw.js','public/render-viewer.js','public/render-engine.js']:
    actual,_=get('/'+path);local=(root/path).read_bytes()
    assert actual==local,'Different public source: '+path
    hashes[path]=hashlib.sha256(actual).hexdigest()
_,response_headers=get('/')
h={k.lower():v for k,v in response_headers.items()}
assert "script-src 'self'" in h.get('content-security-policy','')
assert "frame-ancestors 'none'" in h.get('content-security-policy','')
assert 'max-age=' in h.get('strict-transport-security','')
result={'origin':origin,'expectedCommit':expected,'version':version,'health':health,'ready':ready,'render':renders,'moduleHashes':hashes,'security':{'csp':h.get('content-security-policy'),'hsts':h.get('strict-transport-security')}}
(out/'deployment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
