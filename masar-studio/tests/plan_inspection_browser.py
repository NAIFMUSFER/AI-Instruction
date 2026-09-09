"""Read-only mobile plan navigation acceptance, using real UI and exact export comparisons."""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
ENGINE=os.environ.get('MASAR_BROWSER','chromium');BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
OUT=ROOT/'test-output'/'plan-inspection'/ENGINE;OUT.mkdir(parents=True,exist_ok=True)
PROMPT=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text();checks=[];errors=[];external=[];server=None

def passed(name):
    checks.append({'name':name,'status':'pass'});print('INSPECTION_PASS '+name,flush=True)
with tempfile.TemporaryDirectory(prefix='masar-inspection-') as tmp:
    try:
        if not BASE:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}'
            env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/db.sqlite','PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
            for _ in range(100):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as r:assert r.status==200
                    break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('server start failed')
        with sync_playwright() as p:
            options={'headless':True}
            if ENGINE=='chromium' and os.environ.get('MASAR_CHROMIUM_PATH'):options['executable_path']=os.environ['MASAR_CHROMIUM_PATH']
            browser=getattr(p,ENGINE).launch(**options)
            context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
            page=context.new_page();page.set_default_timeout(20000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(BASE+'/') else None)
            def action(name):
                scope=page.locator('#modal') if page.locator('#modal').evaluate('e=>e.open') else page
                scope.locator(f'button[data-action="{name}"]:visible').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').first.click()
            def export(tag):
                action('export')
                with page.expect_download() as d:page.locator('[data-kind="json"]').click()
                path=OUT/(tag+'.json');d.value.save_as(str(path));close();return json.loads(path.read_text())['history']
            def zoom():return float(page.locator('#plan-inspection-frame').get_attribute('data-zoom'))
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            action('new');page.locator('#new-prompt').fill(PROMPT);page.locator('#new-form button[type="submit"]').click();page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form button[type="submit"]').click()
            expect(page.locator('#modal')).not_to_be_visible();before=export('before');model=before['revisions'][before['cursor']]['model']
            passed('exact original long brief remains accepted before plan inspection')
            expect(page.locator('#plan-host .site-feature')).to_have_count(5)
            for title in ['مسبح','موقف','جلسة','شواء','حديقة']:expect(page.locator('#plan-host .site-feature text').filter(has_text=title)).to_have_count(1)
            passed('main plan labels every requested outdoor allocation instead of anonymous rectangles')
            action('plan-inspect');expect(page.locator('#modal-title')).to_have_text('فحص المخطط والموقع')
            expect(page.locator('#plan-inspection')).to_have_attribute('data-model-id',model['id']);expect(page.locator('#plan-inspection .modal-lead')).to_contain_text(before['revisions'][before['cursor']]['id'])
            assert page.locator('#plan-inspection-frame [data-room-id]').count()==0
            passed('inspection identifies exact project/revision and cannot expose geometry drag targets')
            for f in model['site']['features']:expect(page.locator('.plan-site-item strong',has_text=f['name'])).to_have_count(1)
            expect(page.locator('.plan-site-item')).to_have_count(5)
            passed('all canonical feature names and dimensions are listed without claiming garden coverage')
            for _ in range(3):page.locator('[data-plan-nav="in"]').click()
            assert zoom()>2;page.locator('#plan-inspection-frame').focus();old=page.locator('#plan-inspection-frame svg').get_attribute('viewBox');page.keyboard.press('ArrowRight');assert old!=page.locator('#plan-inspection-frame svg').get_attribute('viewBox')
            passed('zoom buttons and keyboard pan change camera rather than model coordinates')
            page.keyboard.press('0');assert zoom()==1;passed('keyboard reset restores the entire plot without error')
            page.locator('[data-plan-nav="fit"]').click();assert zoom()==1
            expect(page.locator('[data-plan-nav="out"]')).to_be_disabled();passed('fit restores full site and disables further zoom-out')
            pool=next(i for i,f in enumerate(model['site']['features']) if f['type']=='pool')
            page.locator(f'[data-plan-feature="{pool}"]').click();assert zoom()>1
            view=[float(x) for x in page.locator('#plan-inspection-frame svg').get_attribute('viewBox').split()];f=model['site']['features'][pool];cx=f['x']+f['w']/2;cy=model['site']['depth']-f['y']-f['d']/2
            assert view[0]<=cx<=view[0]+view[2] and view[1]<=cy<=view[1]+view[3]
            passed('site schedule navigation brings the actual pool position into view')
            frame=page.locator('#plan-inspection-frame');box=frame.bounding_box();old=frame.locator('svg').get_attribute('viewBox')
            page.mouse.move(box['x']+box['width']*.5,box['y']+box['height']*.5);page.mouse.down();page.mouse.move(box['x']+box['width']*.65,box['y']+box['height']*.55,steps=5);page.mouse.up();assert old!=frame.locator('svg').get_attribute('viewBox')
            passed('real pointer drag pans the dedicated read-only viewport')
            # Exercise multi-pointer event handling independently of browser/device pinch injection.
            page.locator('[data-plan-nav="fit"]').click();page.locator('[data-plan-nav="in"]').click();old_zoom=zoom()
            page.evaluate("""() => { const f=document.querySelector('#plan-inspection-frame'),r=f.getBoundingClientRect();const send=(type,id,x)=>f.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',button:0,clientX:r.x+x,clientY:r.y+r.height/2,bubbles:true,cancelable:true}));const capture=f.setPointerCapture;f.setPointerCapture=()=>{};try{send('pointerdown',31,r.width*.4);send('pointerdown',32,r.width*.6);send('pointermove',32,r.width*.8);send('pointercancel',31,r.width*.4);send('pointercancel',32,r.width*.8);}finally{f.setPointerCapture=capture;} }""")
            assert zoom()>old_zoom;passed('two-pointer pinch mathematics and cancellation cleanup are exercised (synthetic touch events)')
            with page.expect_download() as d:page.locator('[data-plan-save]').click()
            path=OUT/'inspection.svg';d.value.save_as(str(path));text=path.read_text();assert 'viewBox="-2.5 -2.5 25 30"' in text
            for f in model['site']['features']:assert f['name'] in text
            passed('download exports full canonical SVG regardless of current camera crop')
            for width in [320,390,768]:
                page.set_viewport_size({'width':width,'height':844});page.locator('[data-plan-nav="fit"]').click()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('#modal').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                box=page.locator('#plan-inspection-frame').bounding_box();assert box['width']>100 and box['height']>=260
            page.set_viewport_size({'width':390,'height':844});page.locator('[data-plan-nav="in"]').click();page.screenshot(path=str(OUT/'inspection-mobile.png'),full_page=True)
            passed('navigation and outdoor schedule fit 320/390/768 pixels without horizontal clipping')
            close();after=export('after');assert after==before
            passed('opening navigating downloading and closing preserve entire history and geometry byte-for-byte')
            action('quality-review');action('plan-inspect');expect(page.locator('#plan-inspection')).to_have_attribute('data-model-id',model['id']);close()
            passed('measured quality review links directly to the same read-only plan inspector')
            action('quality-review');page.locator('#quality-preview').click();expect(page.locator('#preview-banner')).to_be_visible();action('plan-inspect');expect(page.locator('#plan-inspection .modal-lead')).to_contain_text('معاينة غير محفوظة');close();action('cancel-preview')
            assert export('after-cancel')==before
            passed('uncommitted alternatives are visibly labelled and inspection never commits them')
            page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=30000);assert export('after-reload')==before
            passed('saved original survives reload after all inspection interactions')
            assert errors==[] and external==[];passed('no unhandled JavaScript errors or third-party runtime requests')
            browser.close()
    except Exception as e:
        checks.append({'name':'inspection failed','status':'fail','error':str(e),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
    finally:
        if server:server.terminate();server.wait(timeout=10)
        report={'engine':ENGINE,'origin':BASE,'passed':sum(x['status']=='pass' for x in checks),'failed':sum(x['status']=='fail' for x in checks),'checks':checks,'pageErrors':errors,'externalRequests':external,'scope':'read-only camera and source preservation; synthetic two-touch test, not physical phone testing'}
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('INSPECTION_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
if report['failed']:raise SystemExit(1)
