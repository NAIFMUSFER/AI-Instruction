"""Customer acceptance: real UI, no injected application state and no customer accounts."""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-output'/'customer-ui';OUT.mkdir(parents=True,exist_ok=True)
PROMPT=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text()
ENGINE=os.environ.get('MASAR_BROWSER','chromium')
BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
results=[];errors=[]
def check(name,fn):
    fn();results.append({'name':name,'status':'pass'});print('CUSTOMER_PASS '+name,flush=True)
def assert_that(condition,message='assertion failed'):
    assert condition,message
def model_in(value):
    if isinstance(value,dict):
        if 'levels' in value and 'site' in value and 'schemaVersion' in value:return value
        for child in value.values():
            found=model_in(child)
            if found:return found
    if isinstance(value,list):
        for child in value:
            found=model_in(child)
            if found:return found
    return None
server=None
with tempfile.TemporaryDirectory(prefix='masar-journey-') as tmp:
    try:
        if not BASE:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}'
            env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/test.sqlite','PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/(ENGINE+'-server.log'),'w'),stderr=subprocess.STDOUT)
            for _ in range(80):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as response:assert response.status==200
                    break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('Test server did not start')
        with sync_playwright() as p:
            browser=getattr(p,ENGINE).launch(headless=True)
            context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True,accept_downloads=True)
            page=context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000)
            page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            def action(name):page.locator(f'button[data-action="{name}"]').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').first.click()
            action('new');page.locator('#new-prompt').fill(PROMPT);page.locator('#new-form button[type="submit"]').click()
            form=page.locator('#brief-form')
            check('same full brief understood as chalet, three bedrooms and 20x25 plot',lambda:(expect(form.locator('[name="projectType"]')).to_have_value('chalet'),expect(form.locator('[name="bedrooms"]')).to_have_value('3'),expect(form.locator('[name="width"]')).to_have_value('20'),expect(form.locator('[name="depth"]')).to_have_value('25')))
            check('requested 120-160 building budget is visible, not silently ignored',lambda:(expect(form.locator('[name="areaMin"]')).to_have_value('120'),expect(form.locator('[name="areaMax"]')).to_have_value('160')))
            form.locator('button[data-action="new"]').click();check('Back preserves every character of the brief',lambda:expect(page.locator('#new-prompt')).to_have_value(PROMPT))
            page.locator('#new-form button[type="submit"]').click();form=page.locator('#brief-form');form.locator('[name="confirm"]').check()
            form.locator('[name="projectType"]').select_option('warehouse');form.locator('[name="bedrooms"]').fill('0');form.locator('[name="projectType"]').select_option('chalet')
            check('changing project type cannot leave a residential project at zero bedrooms',lambda:expect(form.locator('[name="bedrooms"]')).to_have_value('3'))
            form.locator('[name="areaMin"]').fill('200');form.locator('button[type="submit"]').click()
            check('invalid range returns visible in-dialog error and retains input',lambda:(expect(page.locator('#modal-error')).to_be_visible(),expect(page.locator('#modal-error')).to_contain_text('حدًا أعلى'),expect(form.locator('[name="areaMin"]')).to_have_value('200')))
            page.screenshot(path=str(OUT/(ENGINE+'-visible-error.png')),full_page=True)
            form.locator('[name="areaMin"]').fill('80');form.locator('[name="areaMax"]').fill('100');form.locator('button[type="submit"]').click()
            check('infeasible area stops with an actionable message rather than an oversized building',lambda:(expect(page.locator('#modal-error')).to_contain_text('140'),expect(form).to_be_visible()))
            form.locator('[name="areaMin"]').fill('120');form.locator('[name="areaMax"]').fill('160')
            form.locator('[name="width"]').fill('10');form.locator('button[type="submit"]').click()
            check('native invalid-field errors are also visible inside the modal',lambda:expect(page.locator('#modal-error')).to_contain_text('عرض الأرض'))
            form.locator('[name="width"]').fill('20');form.locator('button[type="submit"]').click()
            check('exact original brief generates a project without shortening or losing content',lambda:(expect(page.locator('#modal')).not_to_be_visible(),expect(page.locator('#project-title')).to_have_text('شاليه الفناء'),expect(page.locator('#plan-host svg')).to_be_visible()))
            check('mobile page does not horizontally overflow',lambda:assert_that(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
            page.screenshot(path=str(OUT/(ENGINE+'-generated-mobile.png')),full_page=True)
            action('export')
            with page.expect_download(timeout=20000) as dl:page.locator('#modal [data-action="download"][data-kind="json"]').click()
            file=OUT/(ENGINE+'-customer-project.json');dl.value.save_as(str(file));m=model_in(json.loads(file.read_text()));assert m
            rooms=m['levels'][0]['rooms']
            check('downloaded project retains text, bedrooms, programme and measured area requirement',lambda:(assert_that(m['brief']['prompt']==PROMPT),assert_that(sum(r['kind']=='bedroom' for r in rooms)==3),assert_that(not any(r['kind']=='stairs' for r in rooms)),assert_that(any(r['type']=='building-area' and r['value']==[120,160] for r in m['requirements'])),assert_that(m['design']['projectType']=='chalet')))
            close();page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=30000)
            check('generated project survives reload via actual IndexedDB',lambda:expect(page.locator('#project-title')).to_have_text('شاليه الفناء'))
            page.set_viewport_size({'width':1440,'height':1000});action('fit');page.screenshot(path=str(OUT/(ENGINE+'-generated-desktop.png')),full_page=True)
            for width in [320,768]:
                page.set_viewport_size({'width':width,'height':900});check(f'layout at {width}px has no horizontal overflow',lambda:assert_that(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
            check('no unhandled JavaScript errors',lambda:assert_that(errors==[],str(errors)))
            browser.close()
    except Exception as e:
        results.append({'name':'acceptance failure','status':'fail','error':str(e),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
    finally:
        if server:server.terminate();server.wait(timeout=10)
        report={'engine':ENGINE,'origin':BASE,'promptCharacters':len(PROMPT),'passed':sum(r['status']=='pass' for r in results),'failed':sum(r['status']=='fail' for r in results),'pageErrors':errors,'checks':results}
        (OUT/(ENGINE+'-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print('CUSTOMER_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
if any(r['status']=='fail' for r in results):raise SystemExit(1)
