"""Local-only transport fixture. No provider, key, real customer data or 3D claim."""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
import uvicorn
import acs_async_jobs as J

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI()
calls = 0

@app.post('/v1/understand')
async def generate(request: Request):
    global calls
    calls += 1
    await request.json()
    await asyncio.sleep(3)
    return {'ok':True,'building':{'meta':{'type':'villa'},'levels':[],'floors':{}}, 'rooms':1, 'levels':1}

@app.get('/counts')
def counts(): return {'calls':calls}

@app.get('/')
def index():
    return HTMLResponse('<!doctype html><html lang="ar"><head><script src="/client.js" defer></script></head>'
        '<body><button id="genLLM">Generate</button><div id="status"></div><div id="acsLiveRegion"></div></body></html>')

@app.get('/client.js')
def script():
    transport = (ROOT/'public/app/ui/workspace-ui-wiring.js').read_text()
    transport = transport[transport.index('const ACS_NET={'):transport.index('function srvPill(')]
    jobs = (ROOT/'public/app/ui/generation-jobs.js').read_text()
    jobs = '\n'.join(line for line in jobs.splitlines() if not line.startswith('import '))
    shim = '''const __ACS_SHARED = {};
const statusEl = document.getElementById('status');
function srvPill(cls, text) {statusEl.textContent=text;}
function srvURL() {return location.origin;}
function apiURL(path) {return location.origin+path;}
window.ACS_API = {base:()=>location.origin};
let current=null;
window.ACS = {exportModel:()=>current, trust:{modelReviewSummary:()=> 'fixture - no engineering claim'}};
function acsApplyTicket(){return 1;}
function acsApplyBuilding(b){current=b;window.applied=b;return {ok:true};}
function acsApplyFirstFrame(){return {ok:true};}
function showReport(){}
'''
    bootstrap = '''\nwindow.startGeneration=async()=>{window.result=await __ACS_SHARED.acsFetchJSON('/v1/understand',
 {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'synthetic test fixture'})},900000);return window.result;};
document.getElementById('genLLM').onclick=()=>{window.pending=window.startGeneration();};
'''
    return Response(shim+transport+jobs+bootstrap,media_type='text/javascript')

app.add_middleware(J.AsyncGenerationMiddleware, store=J.JobStore())
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]), access_log=False, log_level='warning')
