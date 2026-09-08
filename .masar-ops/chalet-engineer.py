"""A visible-UI engineer acceptance on the client's generated chalet, not the stock demo."""
import json,os,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['MASAR_AUDIT_URL'].rstrip('/');COMMIT=os.environ['MASAR_AUDIT_COMMIT']
assert BASE=='https://masar-quality-preview.onrender.com'
ROOT=Path(__file__).resolve().parents[1]/'masar-studio'
OUT=Path(os.environ.get('MASAR_ENGINEER_OUT','engineer-evidence'));OUT.mkdir(parents=True,exist_ok=True)
prompt=(ROOT/'tests/fixtures/chalet-client-20x25.txt').read_text();checks=[];errors=[]
report={'url':BASE,'expectedCommit':COMMIT,'scope':'Visible engineering review of conceptual geometry; not regulatory approval'}
def must(value,message):
    if not value:raise AssertionError(message)
    checks.append(message);print('PASS '+message,flush=True)
def history(v):
    if isinstance(v,dict):
        if 'revisions' in v and 'cursor' in v:return v
        for x in v.values():
            h=history(x)
            if h:return h
    return None
def action(name):page.locator('button[data-action="'+name+'"]:visible').first.click()
def close():page.locator('#modal button[data-action="close-modal"]').first.click();expect(page.locator('#modal')).not_to_be_visible()
def read_model(name):
    action('export')
    with page.expect_download() as pending:page.locator('#modal [data-action="download"][data-kind="json"]').click()
    p=OUT/(name+'.json');pending.value.save_as(p);h=history(json.loads(p.read_text()));assert h
    close();return h['revisions'][h['cursor']]['model']
def geometry(m):return {'site':m['site'],'levels':m['levels']}
try:
 with sync_playwright() as pw:
    browser=pw.chromium.launch(args=['--use-angle=swiftshader','--enable-unsafe-swiftshader']);context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=context.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)))
    v=context.request.get(BASE+'/api/version',timeout=60000);must(v.status==200 and v.json()['commit']==COMMIT,'Verified published application commit')
    page.goto(BASE,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=45000)
    action('new');page.locator('#new-prompt').fill(prompt);page.locator('#new-form [type="submit"]').click();page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form [type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
    initial=read_model('Chalet-20x25-Original-Generated');rooms=[r for l in initial['levels'] for r in l['rooms']];guest=next(r for r in rooms if r['kind']=='majlis')
    must(initial['brief']['prompt']==prompt and sum(r['kind']=='bedroom' for r in rooms)==3,'Original client description produces the inspected three-bedroom project')
    page.locator('.tree-room[data-id="'+guest['id']+'"]').click();form=page.locator('#properties-form')
    must(abs(float(form.locator('[name="w"]').input_value())-guest['w'])<.001 and abs(float(form.locator('[name="d"]').input_value())-guest['d'])<.001,'Visible width and depth agree with actual exported room coordinates')
    form.locator('[name="name"]').fill('مجلس مراجعة الجودة');form.locator('[type="submit"]').click();expect(page.locator('#preview-banner')).to_be_visible();expect(page.locator('[data-action="commit-preview"]')).to_be_enabled()
    must('مجلس مراجعة الجودة' in page.locator('#preview-banner').inner_text(),'Local room edit shows its explicit preview before commit')
    action('cancel-preview');must(form.locator('[name="name"]').input_value()==guest['name'],'Cancelling preview keeps the original room unchanged')
    form.locator('[name="name"]').fill('مجلس مراجعة الجودة');form.locator('[type="submit"]').click();action('commit-preview');must(form.locator('[name="name"]').input_value()=='مجلس مراجعة الجودة','Explicit commit applies the room edit')
    action('undo');must(form.locator('[name="name"]').input_value()==guest['name'],'Undo restores the original room name');action('redo');must(form.locator('[name="name"]').input_value()=='مجلس مراجعة الجودة','Redo restores the approved edit');action('undo')
    form.locator('[name="w"]').fill('15');form.locator('[type="submit"]').click();expect(page.locator('#preview-banner')).to_be_visible();must(page.locator('[data-action="commit-preview"]').is_disabled(),'An overlapping and oversized room cannot be committed');action('cancel-preview')
    unchanged=read_model('Chalet-20x25-After-Cancel');must(geometry(unchanged)==geometry(initial),'Rejected resize and cancelled edits preserve original exported geometry')
    action('brief');text=page.locator('#modal-content').inner_text();must(all(s in text for s in ['بانترى','غرفة ملابس','برجولة','مراجعة بشرية']),'Unimplemented detailed programme is retained for human review, not marked automatically fulfilled');close()
    page.locator('[data-action="view"][data-view="2d"]').click();page.screenshot(path=str(OUT/'generated-plan-desktop.png'),full_page=True)
    action('render-center');must(page.locator('#render-start').is_disabled(),'Option A never enables paid cloud Blender processing')
    page.locator('#render-pbr').click();expect(page.locator('#render-canvas')).to_have_attribute('data-ready','true');must(page.locator('#render-canvas').get_attribute('data-renderer')=='three-pbr','Generated client chalet also opens in the material viewer')
    with page.expect_download() as pending:page.locator('#render-local').click()
    pending.value.save_as(OUT/'Chalet-20x25-Blender-Scene.json');scene=json.loads((OUT/'Chalet-20x25-Blender-Scene.json').read_text());must(scene['units']=='m' and scene['schema']=='masar-render-scene-1' and len(scene['objects'])>0 and 'Modern Resort Style' not in json.dumps(scene),'Client Blender scene is metre-based and excludes the private original description')
    page.screenshot(path=str(OUT/'chalet-materials-desktop.png'),full_page=True);close();final=read_model('Chalet-20x25-After-Material-Preview');must(geometry(final)==geometry(initial),'Material inspection does not mutate architectural geometry')
    must(not errors,'No uncaught JavaScript errors in engineer journey');report.update(status='PASS',passed=len(checks),failed=0,checks=checks,pageErrors=errors,conceptualFloorArea=sum(r['w']*r['d'] for r in rooms));browser.close()
except Exception:
    report.update(status='FAIL',passed=len(checks),failed=1,checks=checks,error=traceback.format_exc(),pageErrors=errors)
    try:page.screenshot(path=str(OUT/'engineer-failure.png'),full_page=True)
    except Exception:pass
finally:
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
raise SystemExit(0 if report['status']=='PASS' else 1)
