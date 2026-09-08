"""Real UI acceptance for measured alternatives, cancel/apply/undo and source binding.
No injected application state. Temporary local DB, or non-account live browser use.
"""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
ENGINE=os.environ.get('MASAR_BROWSER','chromium')
BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
OUT=ROOT/'test-output'/'layout-quality-ui'/ENGINE;OUT.mkdir(parents=True,exist_ok=True)
PROMPT=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text()
checks=[];errors=[];external=[];server=None;page=None

def passed(name):
    checks.append({'name':name,'status':'pass'});print('LAYOUT_QUALITY_PASS '+name,flush=True)
def history(payload):
    return payload['history']
def model(payload):
    h=history(payload);return h['revisions'][h['cursor']]['model']
with tempfile.TemporaryDirectory(prefix='masar-layout-quality-') as tmp:
    try:
        if not BASE:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}'
            env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/test.sqlite','PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
            for _ in range(80):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as r:assert r.status==200
                    break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('Local server did not start')
        with sync_playwright() as pw:
            launch={'headless':True}
            if ENGINE=='chromium':
                launch['args']=['--use-angle=swiftshader','--enable-unsafe-swiftshader']
                if os.environ.get('MASAR_CHROMIUM_PATH'):launch['executable_path']=os.environ['MASAR_CHROMIUM_PATH']
            browser=getattr(pw,ENGINE).launch(**launch)
            ctx=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True,accept_downloads=True)
            page=ctx.new_page();page.set_default_timeout(20000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(BASE+'/') else None)
            def action(name):page.locator(f'button[data-action="{name}"]:visible').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').click()
            def export_project(tag):
                action('export')
                with page.expect_download() as dl:page.locator('#modal [data-action="download"][data-kind="json"]').click()
                path=OUT/(tag+'.json');dl.value.save_as(str(path));value=json.loads(path.read_text());close();return value
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            action('new');page.locator('#new-prompt').fill(PROMPT);page.locator('#new-form button[type="submit"]').click();page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form button[type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
            before=export_project('before');original=model(before);assert original['brief']['prompt']==PROMPT
            passed('unchanged original description generates the stable baseline before optional improvement')
            action('quality-review');expect(page.locator('#modal-title')).to_have_text('جودة التوزيع والمقايضات')
            expect(page.locator('[data-quality-current="longestHallExtentM"]')).to_contain_text('10.4');expect(page.locator('[data-quality-next="longestHallExtentM"]')).to_contain_text('5.4')
            expect(page.locator('.quality-room .source-tag.warn')).to_contain_text('يحتاج مراجعة')
            passed('review exposes the actual long hall and narrow master rather than bbox-based approval')
            expect(page.locator('#quality-tradeoffs')).to_contain_text('تصغر غرفتا النوم');expect(page.locator('#quality-tradeoffs')).to_contain_text('من الجانب')
            page.locator('.quality-room-changes summary').click();expect(page.locator('.quality-room-changes tbody tr')).to_have_count(17)
            passed('side entrance and smaller rooms are disclosed with all 17 before and after areas')
            for width in [320,390,768]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('#modal').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'review-mobile.png'),full_page=True)
            passed('review and tradeoffs reflow at 320, 390 and 768 pixels without clipping')
            with page.expect_download() as dl:action('download-quality')
            path=OUT/'layout-review-before.json';dl.value.save_as(str(path));report=json.loads(path.read_text())
            assert report['source']['modelId']==original['id'] and not report['source']['uncommittedPreview'];assert report['review']['longestHallExtentM']==10.419
            passed('downloaded quality JSON identifies the current canonical project and not a stock model')
            page.locator('#quality-preview').click();expect(page.locator('#preview-banner')).to_be_visible();expect(page.locator('.quality-preview-notice')).to_contain_text('إعادة توزيع شاملة')
            action('cancel-preview');cancelled=export_project('cancelled');assert history(cancelled)==history(before)
            passed('preview cancellation preserves full original history and geometry byte for byte')
            action('quality-review');page.locator('#quality-preview').click();action('commit-preview');expect(page.locator('#preview-banner')).not_to_be_visible()
            after=export_project('after');mh=model(after);h=history(after)
            assert len(h['revisions'])==2 and h['revisions'][0]['model']==original
            assert mh['design']['layoutStrategy']=='compact-short-circulation-v2'
            assert mh['id']==original['id'] and mh['brief']==original['brief'] and mh['requirements']==original['requirements'] and mh['site']==original['site']
            assert len(mh['levels'][0]['rooms'])==17 and sum(r['kind']=='bedroom' for r in mh['levels'][0]['rooms'])==3
            passed('explicit acceptance adds one revision while retaining original model, plot, features and requirements')
            action('undo');undone=export_project('undo');assert model(undone)==original
            action('redo');redone=export_project('redo');assert model(redone)==mh
            passed('undo and redo restore exact old and improved geometry, not regenerated approximations')
            page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=40000)
            restored=export_project('reloaded');assert model(restored)==mh
            passed('improved revision survives actual IndexedDB reload')
            action('quality-review');expect(page.locator('[data-quality-current="longestHallExtentM"]')).to_contain_text('5.4');expect(page.locator('#quality-preview')).to_have_count(0);expect(page.locator('.quality-room .source-tag.warn')).to_have_count(0)
            passed('improved plan has no misleading repeat-optimization button and all illustrative bed checks pass')
            close();page.set_viewport_size({'width':1440,'height':1000});page.locator('#plan-host').screenshot(path=str(OUT/'improved-plan.png'))
            if ENGINE=='chromium':
                action('render-center');page.locator('#render-pbr').click();canvas=page.locator('#render-canvas');expect(canvas).to_have_attribute('data-ready','true');expect(canvas).to_have_attribute('data-renderer','three-pbr')
                assert canvas.get_attribute('data-source-model')==mh['id'];assert canvas.get_attribute('data-source-revision')==h['revisions'][h['cursor']]['id']
                page.locator('#render-cutaway').check();canvas.screenshot(path=str(OUT/'improved-material.png'))
                with page.expect_download() as dl:page.locator('#render-local').click()
                scene_path=OUT/'improved-blender-scene.json';dl.value.save_as(str(scene_path));scene=json.loads(scene_path.read_text())
                assert scene['source']['modelId']==mh['id'] and scene['source']['revisionId']==canvas.get_attribute('data-source-revision') and len(scene['proofs']['rooms'])==17
                passed('actual material viewer and Blender scene reference the accepted improved revision')
                close()
            # Restore the old revision through the real UI, then respect a user room lock.
            action('undo');page.locator('#plan-host [data-room-id="l0-bed2"]').first.click();action('lock')
            action('quality-review');expect(page.locator('#quality-preview')).to_have_count(0);expect(page.locator('#modal-content')).to_contain_text('مثبتة')
            passed('real UI room locking prevents whole-layout replanning without overriding a decision')
            close();action('lock');action('quality-review');expect(page.locator('#quality-preview')).to_be_visible();close()
            passed('explicit unlock restores eligibility without losing the original layout')
            # The alternative gallery must have a real new option, and unchanged cards must be disabled.
            action('alternatives');cards=page.locator('.alternate-card');assert cards.count()>=4
            improved=cards.filter(has_text='حركة أقصر وغرفة رئيسية أوضح');assert improved.count()==1;expect(improved.locator('[data-action="use-alternative"]')).to_be_enabled()
            for card in cards.all():
                if 'لا تغيير هندسي فعلي' in card.inner_text():expect(card.locator('[data-action="use-alternative"]')).to_be_disabled()
            improved.locator('[data-action="use-alternative"]').click();expect(page.locator('.quality-preview-notice')).to_be_visible();action('cancel-preview')
            passed('alternative gallery distinguishes actual changes and opens the same non-destructive preview')
            assert not errors and not external,(errors,external);passed('no unhandled JavaScript errors or third-party runtime requests')
            browser.close()
    except Exception as e:
        checks.append({'name':'acceptance failure','status':'fail','error':str(e),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
        if page:
            try:page.screenshot(path=str(OUT/'failure.png'),full_page=True)
            except Exception:pass
    finally:
        if server:server.terminate();server.wait(timeout=10)
        result={'engine':ENGINE,'origin':BASE,'passed':sum(c['status']=='pass' for c in checks),'failed':sum(c['status']=='fail' for c in checks),'pageErrors':errors,'externalRequests':external,'checks':checks,'scope':'Browser software test of optional concept planning; no physical-device or architectural/code approval'}
        (OUT/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('LAYOUT_QUALITY_REPORT '+json.dumps(result,ensure_ascii=False),flush=True)
if any(c['status']=='fail' for c in checks):raise SystemExit(1)
