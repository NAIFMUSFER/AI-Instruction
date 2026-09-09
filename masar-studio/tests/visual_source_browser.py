"""Real UI acceptance for screenshot ambiguity, compact defaults and nondestructive recovery.
No account is used; local projects are created/imported through visible UI only.
"""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
ENGINE=os.environ.get('MASAR_BROWSER','chromium')
BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
OUT=ROOT/'test-output'/'visual-source'/ENGINE
OUT.mkdir(parents=True,exist_ok=True)
full=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text()
legacy=json.loads((ROOT/'tests/fixtures/legacy-chalet-source.json').read_text())
def current(payload):
    h=payload['history']
    return h['revisions'][h['cursor']]['model'],h['revisions'][h['cursor']]['id']
results=[];errors=[];external=[];server=None;page=None
def passed(name):
    results.append({'name':name,'status':'pass'});print('VISUAL_SOURCE_PASS '+name,flush=True)
with tempfile.TemporaryDirectory(prefix='masar-visual-source-') as tmp:
    try:
        if not BASE:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}'
            env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),
                 'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/visual.sqlite','PERSISTENCE_CLASS':'ephemeral',
                 'BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,
                                    stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
            for _ in range(80):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as r:assert r.status==200
                    break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('Server did not start')
        with sync_playwright() as pw:
            opts={'headless':True}
            if ENGINE=='chromium':opts['args']=['--use-angle=swiftshader','--enable-unsafe-swiftshader']
            bt=getattr(pw,ENGINE)
            browser=bt.launch(**opts)
            context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
            page=context.new_page();page.set_default_timeout(20000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(BASE+'/') else None)
            def action(name):page.locator('button[data-action="'+name+'"]').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').click()
            def export(tag):
                action('export')
                with page.expect_download() as dl:page.locator('#modal [data-kind="json"]').click()
                path=OUT/(tag+'.json');dl.value.save_as(str(path));close()
                return json.loads(path.read_text())
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000)
            page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            action('render-center')
            expect(page.locator('#render-source')).to_contain_text('مثال توضيحي — ليس مشروعك')
            passed('fresh demo cannot be mistaken for a client design in the material panel')
            page.locator('#render-source button[data-action="new"]').click()
            page.locator('[data-template="chalet"]').click()
            page.locator('#new-form [type="submit"]').click()
            expect(page.locator('#area-assumption')).to_be_visible()
            expect(page.locator('#area-assumption')).to_contain_text('ليس رقمًا ورد في وصفك')
            expect(page.locator('[name="areaMin"]')).to_have_value('120')
            expect(page.locator('[name="areaMax"]')).to_have_value('160')
            passed('built-in chalet presents the compact area as an editable assumption before generation')
            page.locator('[name="confirm"]').check();page.locator('#brief-form [type="submit"]').click()
            expect(page.locator('#modal')).not_to_be_visible()
            model,rev=current(export('template-project'))
            assert model['design']['layoutStrategy']=='compact-three-bedroom-v1'
            assert sum(r['kind']=='bedroom' for r in model['levels'][0]['rooms'])==3
            assert not any(r['kind']=='stairs' for r in model['levels'][0]['rooms'])
            passed('built-in chalet no longer falls through to the large generic layout with a staircase')
            action('render-center')
            expect(page.locator('#render-source')).to_contain_text('18 × 25')
            expect(page.locator('#render-source')).to_contain_text(rev)
            expect(page.locator('#render-source-warning')).to_have_count(0)
            passed('material panel identifies the exact project revision, site and measured area')
            expect(page.locator('#render-start')).to_be_disabled()
            expect(page.locator('#render-capability')).to_contain_text('تسجيل الدخول لا يفعّله')
            passed('option A clearly states that login cannot activate cloud Blender rendering')
            if ENGINE=='chromium':
                page.locator('#render-pbr').click()
                canvas=page.locator('#render-canvas')
                expect(canvas).to_have_attribute('data-ready','true')
                expect(canvas).to_have_attribute('data-renderer','three-pbr')
                expect(canvas).to_have_attribute('data-source-model',model['id'])
                expect(canvas).to_have_attribute('data-source-revision',rev)
                page.locator('#render-cutaway').check()
                with page.expect_download() as dl:page.locator('#render-local').click()
                file=OUT/'template-blender-scene.json';dl.value.save_as(str(file))
                scene=json.loads(file.read_text())
                assert scene['source']['modelId']==model['id'] and scene['source']['revisionId']==rev
                assert len(scene['proofs']['rooms'])==len(model['levels'][0]['rooms'])
                canvas.screenshot(path=str(OUT/'compact-material.png'))
                passed('actual PBR and downloaded Blender scene reference the same canonical model, not a demo')
            close()
            # Import a genuine previously generated generic layout, then restore it on reload.
            page.locator('#import-input').set_input_files(str(ROOT/'tests/fixtures/legacy-chalet-source.json'))
            expect(page.locator('#project-title')).to_have_text('شاليه محفوظ قبل الإصلاح')
            old,_=current(export('legacy-before'))
            expected_old,_=current(legacy)
            assert old==expected_old
            page.reload(wait_until='domcontentloaded')
            page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=30000)
            action('render-center')
            expect(page.locator('#render-source-warning')).to_be_visible()
            expect(page.locator('#render-source-warning')).to_contain_text('توزيع شاليه عام')
            expect(page.locator('#render-source')).to_contain_text('273.98')
            passed('a restored legacy project remains unchanged and carries a visible generic-layout warning')
            action('regenerate-brief')
            expect(page.locator('#rebuild-disclosure')).to_contain_text('المشروع السابق محفوظ دون تغيير')
            expect(page.locator('#area-assumption')).to_be_visible()
            page.screenshot(path=str(OUT/'rebuild-confirmation.png'),full_page=True)
            close()
            retained,_=current(export('legacy-after-cancel'))
            assert retained==old
            passed('cancelled re-evaluation never changes old geometry, original prompt or project identity')
            action('render-center');action('regenerate-brief')
            page.locator('[name="confirm"]').check();page.locator('#brief-form [type="submit"]').click()
            expect(page.locator('#modal')).not_to_be_visible()
            new,new_revision=current(export('legacy-rebuilt'))
            assert new['id']!=old['id'] and new['brief']['prompt']==old['brief']['prompt']
            assert new['design']['layoutStrategy']=='compact-three-bedroom-v1'
            passed('approved re-evaluation produces a separate compact project from the same unchanged brief')
            action('projects')
            old_button=page.locator('[data-action="open-local"][data-id="'+old['id']+'"]')
            expect(old_button).to_be_visible();old_button.click()
            saved,_=current(export('legacy-still-saved'))
            assert saved==old
            passed('original project and complete geometry remain retrievable after creating the replacement')
            # Exact long text missing only its budget paragraph must not reproduce the screenshot fallback.
            action('new')
            text=full[:full.rfind('\n\n')]
            page.locator('#new-prompt').fill(text);page.locator('#new-form [type="submit"]').click()
            expect(page.locator('#area-assumption')).to_be_visible()
            page.locator('[name="confirm"]').check();page.locator('#brief-form [type="submit"]').click()
            expect(page.locator('#modal')).not_to_be_visible()
            m,r=current(export('full-without-area'))
            assert m['brief']['prompt']==text and m['design']['layoutStrategy']=='compact-three-bedroom-v1'
            passed('long description without the final numeric range cannot silently become the generic grid')
            # Original full text still travels through exact acceptance path.
            action('new');page.locator('#new-prompt').fill(full);page.locator('#new-form [type="submit"]').click()
            expect(page.locator('#area-assumption')).to_have_count(0)
            page.locator('[name="confirm"]').check();page.locator('#brief-form [type="submit"]').click()
            expect(page.locator('#modal')).not_to_be_visible()
            final,final_rev=current(export('original-full'))
            assert final['brief']['prompt']==full
            action('render-center')
            expect(page.locator('#render-source')).to_contain_text(final_rev)
            expect(page.locator('#render-source')).to_contain_text('150.73')
            expect(page.locator('#render-source-warning')).to_have_count(0)
            passed('full original brief remains explicit with the measured 150.73 m2 model')
            for width in [320,390,768]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('#modal').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            page.set_viewport_size({'width':390,'height':844})
            page.locator('#render-source').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT/'source-mobile.png'),full_page=True)
            passed('source warnings and controls fit 320, 390 and 768 pixel viewports without horizontal overflow')
            close();action('render-center')
            expect(page.locator('#render-source')).to_be_visible()
            passed('closing and reopening the material panel keeps the source identity visible')
            assert not errors and not external
            passed('no unhandled page errors and no third-party runtime requests')
            browser.close()
    except Exception as e:
        results.append({'name':'visual-source acceptance failure','status':'fail','error':str(e),'traceback':traceback.format_exc()})
        print(traceback.format_exc(),flush=True)
        if page:
            try:page.screenshot(path=str(OUT/'failure.png'),full_page=True)
            except Exception:pass
    finally:
        if server:server.terminate();server.wait(timeout=10)
        report={'engine':ENGINE,'origin':BASE,'passed':sum(x['status']=='pass' for x in results),
                'failed':sum(x['status']=='fail' for x in results),'pageErrors':errors,'externalRequests':external,
                'checks':results,'scope':'software-browser conceptual UX, not physical iPhone or architectural approval'}
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('VISUAL_SOURCE_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
if report['failed']:raise SystemExit(1)
