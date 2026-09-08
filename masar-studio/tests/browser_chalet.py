"""Client acceptance journey, using visible UI and exported files, never internal state mutation."""
import argparse,json,os,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--base');parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
OUT=ROOT/'test-output'/'chalet-acceptance';OUT.mkdir(parents=True,exist_ok=True)
prompt=(ROOT/'tests/fixtures/chalet-client-20x25.txt').read_text();results=[];all_errors=[]
def history_from(payload):
    if isinstance(payload,dict):
        if 'revisions' in payload and 'cursor' in payload:return payload
        for v in payload.values():
            h=history_from(v)
            if h:return h
    return None
server=None
with tempfile.TemporaryDirectory(prefix='masar-chalet-') as tmp:
    base=args.base
    if not base:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        env={**os.environ,'NODE_ENV':'development','PUBLIC_ORIGIN':base,'HOST':'127.0.0.1','PORT':str(port),'DB_PATH':str(Path(tmp)/'db.sqlite'),'PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
        server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
        for i in range(80):
            try:
                if urllib.request.urlopen(base+'/api/ready',timeout=2).status==200:break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Isolated application did not start')
    try:
        with sync_playwright() as p:
            engines=os.environ.get('MASAR_CHALET_ENGINES','chromium,webkit').split(',')
            for engine in engines:
                for width,height in [(390,844),(1440,1000)]:
                    browser=getattr(p,engine).launch();ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<500 if engine!='firefox' else None,has_touch=width<500,accept_downloads=True);page=ctx.new_page();page.set_default_timeout(20000);errors=[];console=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console.append(m.text));tag=f'{engine}-{width}';case={'engine':engine,'width':width,'base':base,'checks':[]}
                    def check(name,value=True):
                        assert value,name
                        case['checks'].append(name)
                    def fresh():
                        page.locator('button[data-action="new"]:visible').first.click();page.locator('#new-prompt').fill(prompt);page.locator('#new-form button[type="submit"]').click();page.locator('#brief-form').wait_for()
                    def export_model():
                        page.locator('button[data-action="export"]:visible').first.click()
                        with page.expect_download() as info:page.locator('#modal button[data-action="download"][data-kind="json"]').click()
                        payload=json.loads(Path(info.value.path()).read_text());h=history_from(payload);assert h,'Missing actual exported history';page.locator('#modal button[data-action="close-modal"]').first.click();return h
                    try:
                        page.goto(base,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=45000);fresh()
                        if args.baseline:
                            page.locator('#brief-form select[name="projectType"]').select_option('chalet');page.locator('#brief-form input[name="confirm"]').check();page.locator('#brief-form button[type="submit"]').click();page.wait_for_timeout(500)
                            case.update({'modalOpen':page.locator('#modal').evaluate('(e)=>e.open'),'toasts':page.locator('#toasts').inner_text(),'dialogError':page.locator('#modal').inner_text(),'bedrooms':page.locator('#brief-form input[name="bedrooms"]').input_value(),'console':console})
                            page.screenshot(path=str(OUT/(tag+'-baseline.png')),full_page=True)
                        else:
                            f=page.locator('#brief-form');check('original long description recognised as chalet',f.locator('[name="projectType"]').input_value()=='chalet');check('three requested bedrooms retained',f.locator('[name="bedrooms"]').input_value()=='3');check('land 20 by 25',f.locator('[name="width"]').input_value()=='20' and f.locator('[name="depth"]').input_value()=='25');check('area interval retained',f.locator('[name="buildingAreaMin"]').input_value()=='120' and f.locator('[name="buildingAreaMax"]').input_value()=='160')
                            f.locator('input[name="confirm"]').check();f.locator('button[type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible();page.locator('#plan-host svg').wait_for();check('full prompt generates through customer submit button')
                            h=export_model();m=h['revisions'][h['cursor']]['model'];rooms=[r for l in m['levels'] for r in l['rooms']];area=sum(r['w']*r['d'] for r in rooms);check('exported geometry within requested area',120<=area<=160);check('exported three bedrooms',sum(r['kind']=='bedroom' for r in rooms)==3);check('no unrequested single-storey staircase',not any(r['kind']=='stairs' for r in rooms));check('exact description preserved in exported model',m['brief']['prompt']==prompt);case['projectSummary']={'area':round(area,3),'bedrooms':3,'id':m['id'],'rooms':[{'name':r['name'],'w':r['w'],'d':r['d']} for r in rooms]}
                            page.screenshot(path=str(OUT/(tag+'-generated.png')),full_page=True)
                            page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached');restored=export_model();check('generated project restored from local storage after reload',restored['projectId']==h['projectId'])
                            fresh();f=page.locator('#brief-form');f.locator('[name="buildingAreaMin"]').fill('180');f.locator('[name="buildingAreaMax"]').fill('120');f.locator('[name="confirm"]').check();f.locator('button[type="submit"]').click();expect(page.locator('#modal-error')).to_be_visible();expect(page.locator('#modal-error')).to_contain_text('مساحة');check('invalid range explained inside the modal, not behind backdrop');check('failed generation retains original long description',page.locator('#brief-form .original-prompt').inner_text()==prompt)
                            box=page.locator('#modal-error');check('error is actually in topmost hit-test layer',box.evaluate('(e)=>{const r=e.getBoundingClientRect();const p=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===p||e.contains(p)}'))
                            page.screenshot(path=str(OUT/(tag+'-error-visible.png')),full_page=True)
                            f.locator('[name="buildingAreaMin"]').fill('120');f.locator('[name="buildingAreaMax"]').fill('160');f.locator('button[type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible();check('recovery after correcting invalid values creates project')
                            fresh();page.locator('#brief-form button[data-action="new"]').click();expect(page.locator('#new-prompt')).to_have_value(prompt);check('Back preserves the entire customer description');page.locator('#modal button[data-action="close-modal"]').first.click();check('no horizontal page overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'));check('no uncaught JavaScript errors',not errors)
                    except Exception as e:
                        case['failure']=str(e);page.screenshot(path=str(OUT/(tag+'-failed.png')),full_page=True)
                    case['pageErrors']=errors;case['console']=console;results.append(case);print('CHALET_RESULT '+json.dumps(case,ensure_ascii=False),flush=True);ctx.close();browser.close()
    finally:
        if server:server.terminate();server.wait(timeout=10)
(OUT/'report.json').write_text(json.dumps({'baseline':args.baseline,'cases':results,'passedChecks':sum(len(r['checks']) for r in results),'failures':sum('failure' in r for r in results)},ensure_ascii=False,indent=2))
raise SystemExit(1 if any('failure' in r for r in results) else 0)
