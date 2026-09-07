"""Real same-origin full-stack browser test. Never uses a live customer database.
Runs in CI with Chromium / Firefox / WebKit. It starts its own Node process and
private temporary SQLite/profile directories, then removes them after verification.
"""
import json, os, shutil, socket, subprocess, tempfile, time, traceback, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
ENGINE=os.environ.get('MASAR_BROWSER','chromium')
OUT=ROOT/'test-output'/('browser-http-'+ENGINE);OUT.mkdir(parents=True,exist_ok=True)
results=[];errors=[];requests_failed=[]
def assert_true(value,detail="assertion failed"):
    if not value:raise AssertionError(detail)
def check(name,fn):
    try:fn();results.append({'name':name,'status':'PASS'})
    except Exception:
        results.append({'name':name,'status':'FAIL','error':traceback.format_exc()})
        raise
    finally:print(json.dumps(results[-1],ensure_ascii=False),flush=True)
def action(page,name):page.locator('button[data-action="'+name+'"]').first.click()
def close(page):
    if page.locator('#modal').evaluate('(e)=>e.open'):action(page,'close-modal')
def ready(page):
    page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=20000)
    page.locator('#toasts').evaluate('(e)=>e.innerHTML=""')
def register(page,email):
    action(page,'account');page.locator('[data-action="auth-mode"][data-mode="register"]').click()
    page.locator('#auth-form [name="name"]').fill('مستخدم اختبار '+ENGINE)
    page.locator('#auth-form [name="email"]').fill(email)
    page.locator('#auth-form [name="password"]').fill('Fixture-password-2026!')
    page.locator('#auth-form [type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
def login(page,email,password='Fixture-password-2026!'):
    action(page,'account');page.locator('#auth-form [name="email"]').fill(email);page.locator('#auth-form [name="password"]').fill(password);page.locator('#auth-form [type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
def rename_room(page,name):
    page.locator('#properties-form [name="name"]').fill(name);page.locator('#properties-form [type="submit"]').click();action(page,'commit-preview');expect(page.locator('#properties-form [name="name"]')).to_have_value(name)
def cloud_save(page):
    action(page,'account');action(page,'save-cloud');expect(page.locator('#modal')).not_to_be_visible();expect(page.locator('#save-status')).to_contain_text('محفوظ على الخادم')
def open_cloud(page):
    action(page,'projects');page.locator('[data-action="open-cloud"]').first.click();expect(page.locator('#modal')).not_to_be_visible()
def read_history(page):
    action(page,'export')
    with page.expect_download() as event:page.locator('[data-action="download"][data-kind="json"]').click()
    file=event.value.path();value=json.loads(Path(file).read_text());close(page);return value
with tempfile.TemporaryDirectory(prefix='masar-http-') as tmp:
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    base=f'http://127.0.0.1:{port}';env={**os.environ,'HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':base,'NODE_ENV':'test','ALLOW_REGISTRATION':'true','PERSISTENCE_CLASS':'ephemeral','DB_PATH':str(Path(tmp)/'test.sqlite')}
    for key in ['ANTHROPIC_API_KEY','ANTHROPIC_MODEL','BOOTSTRAP_EMAIL','BOOTSTRAP_PASSWORD']:env.pop(key,None)
    log=open(OUT/'server.log','w');server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=log,stderr=log)
    started=False
    try:
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('Test server exited before readiness')
            try:
                with urllib.request.urlopen(base+'/api/ready',timeout=.3) as response:
                    started=response.status==200
                if started:break
            except Exception:time.sleep(.1)
        assert started,'Test server did not become ready'
        with sync_playwright() as pw:
            bt=getattr(pw,ENGINE);launch={'headless':True}
            if ENGINE=='chromium':launch['args']=['--no-sandbox']
            profile=str(Path(tmp)/'owner-profile')
            context=bt.launch_persistent_context(profile,viewport={'width':1512,'height':982},accept_downloads=True,**launch)
            page=context.pages[0];page.set_default_timeout(12000)
            def observe(p):p.on('pageerror',lambda e:errors.append(str(e)))
            observe(page);page.goto(base,wait_until='networkidle');ready(page)
            check('real HTTP shell, database capability and persistent staging warning',lambda:(expect(page.locator('#persistence-warning')).to_be_visible(),expect(page.locator('#persistence-warning')).to_contain_text('مؤقت'),expect(page.locator('#plan-host svg')).to_be_visible()))
            check('real browser has no horizontal overflow',lambda:assert_true(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
            # Real renderer is recorded, never assumed to be hardware accelerated.
            renderer=page.locator('#scene').get_attribute('data-renderer')
            email='owner-'+ENGINE+'@example.test';check('register account through UI with server session',lambda:register(page,email))
            cookies=context.cookies();check('session cookie is HttpOnly and Strict SameSite',lambda:assert_true(any(c['name']=='masar_session' and c['httpOnly'] and c['sameSite']=='Strict' for c in cookies)))
            title='اختبار الحفظ '+ENGINE
            def rename_project():
                action(page,'rename-project');page.locator('#rename-form [name="title"]').fill(title);page.locator('#rename-form [type="submit"]').click();expect(page.locator('#project-title')).to_have_text(title);expect(page.locator('#save-status')).to_contain_text('محفوظ على هذا الجهاز')
            check('edit is persisted in actual IndexedDB',rename_project)
            check('save history to authenticated server account',lambda:cloud_save(page))
            project=context.request.get(base+'/api/projects').json()['projects'][0];pid=project['id']
            before=context.request.get(base+'/api/projects/'+pid).json();assert before['history']['projectId']==pid
            check('private account response is never cached',lambda:assert_true(context.request.get(base+'/api/projects').headers.get('cache-control')=='no-store'))
            def reload_save():
                page.reload(wait_until='networkidle');ready(page);expect(page.locator('#project-title')).to_have_text(title);rename_room(page,'مجلس محفوظ بعد التحديث');cloud_save(page)
                assert context.request.get(base+'/api/projects/'+pid).json()['version']==before['version']+1
            check('reload retains cloud base version and saves without blind overwrite',reload_save)
            # A second tab captures the same cloud version, then becomes stale.
            second=context.new_page();second.set_default_timeout(12000);observe(second);second.goto(base,wait_until='networkidle');ready(second);open_cloud(second)
            rename_room(page,'تعديل أحدث من النافذة الأولى');cloud_save(page)
            def conflict():
                rename_room(second,'عمل قديم لا يجوز أن يستبدل الأحدث');action(second,'account');action(second,'save-cloud');expect(second.locator('#modal-title')).to_have_text('توجد نسخة أحدث على الخادم');expect(second.locator('#properties-form [name="name"]')).to_have_value('عمل قديم لا يجوز أن يستبدل الأحدث')
                stored=context.request.get(base+'/api/projects/'+pid).json()['history'];assert 'تعديل أحدث من النافذة الأولى' in json.dumps(stored,ensure_ascii=False)
            check('stale browser tab gets conflict choices without overwriting either document',conflict)
            second.close()
            share_url=None
            def make_share():
                action(page,'share');page.locator('#share-form [name="consent"]').check();page.locator('#share-form [type="submit"]').click();page.locator('#shared-url').wait_for(state='visible')
            check('explicit consent creates immutable review URL',make_share);share_url=page.locator('#shared-url').input_value();close(page)
            visitor=bt.launch(**launch);guest=visitor.new_context(accept_downloads=True);review=guest.new_page();review.set_default_timeout(12000);observe(review);review.goto(share_url,wait_until='networkidle');ready(review)
            check('anonymous review displays snapshot but disables geometry edits',lambda:(expect(review.locator('#project-type')).to_contain_text('للقراءة فقط'),expect(review.locator('#properties-form [name="w"]')).to_be_disabled()))
            def reviewer_comment():
                action(review,'comments');review.locator('#review-comment-form [name="author"]').fill('مراجع اختبار');review.locator('#review-comment-form [name="text"]').fill('راجع النافذة الشرقية');review.locator('#review-comment-form [type="submit"]').click();expect(review.locator('#modal-content')).to_contain_text('راجع النافذة الشرقية');close(review)
            check('guest comment is posted to real review store',reviewer_comment)
            v_before=context.request.get(base+'/api/projects/'+pid).json()['version']
            def owner_review():
                action(page,'share');action(page,'review-center');expect(page.locator('#modal-content')).to_contain_text('راجع النافذة الشرقية');action(page,'resolve-review-comment');expect(page.locator('.comment-item small').first).to_contain_text('مغلق');close(page)
                assert context.request.get(base+'/api/projects/'+pid).json()['version']==v_before
            check('owner resolves review without modifying project version',owner_review)
            def revoke():
                action(page,'share');action(page,'revoke-share');close(page);review.reload(wait_until='networkidle');expect(review.locator('#modal-title')).to_have_text('رابط المراجعة غير متاح');expect(review.locator('#app')).not_to_be_visible()
            check('revoked review fails closed instead of showing another local project',revoke)
            guest.close();visitor.close()
            # Separate account and separate browser profile, not a simulated auth mock.
            outsider=bt.launch(**launch);oc=outsider.new_context();op=oc.new_page();op.set_default_timeout(12000);observe(op);op.goto(base,wait_until='networkidle');ready(op)
            def isolation():
                register(op,'other-'+ENGINE+'@example.test');assert oc.request.get(base+'/api/projects').json()['projects']==[];assert oc.request.get(base+'/api/projects/'+pid).status==404
            check('separate real account cannot read owner project',isolation);oc.close();outsider.close()
            def export_ifc():
                action(page,'export')
                with page.expect_download() as event:page.locator('[data-action="download"][data-kind="ifc"]').click()
                event.value.save_as(str(OUT/'browser-export.ifc'));assert (OUT/'browser-export.ifc').read_text().startswith('ISO-10303-21;');close(page)
            check('IFC download contains actual STEP model',export_ifc)
            def import_preview():
                original=page.locator('#project-title').inner_text();page.locator('#import-input').set_input_files(str(OUT/'browser-export.ifc'));expect(page.locator('#modal-title')).to_contain_text('معاينة IFC');expect(page.locator('#project-title')).to_have_text(original);close(page);expect(page.locator('#project-title')).to_have_text(original)
            check('IFC import preview and cancel preserve committed project',import_preview)
            def wall_preview():
                action(page,'wall-types');field=page.locator('#wall-types-form input').first;field.fill(str(int(field.input_value())+1));page.locator('#wall-types-form [type="submit"]').click();expect(page.locator('#preview-banner')).to_be_visible();assert 'NaN' not in page.locator('#plan-host').inner_html();action(page,'cancel-preview')
            check('wall type edit previews safely without fabricated room bounding boxes',wall_preview)
            check('all application scripts have no executable inline handlers',lambda:assert_true(page.evaluate("!Array.from(document.querySelectorAll('*')).some(e=>Array.from(e.attributes).some(a=>/^on/i.test(a.name)))")))
            page.locator('#toasts').evaluate('(e)=>e.innerHTML=""');page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            for width in [390,320,768]:
                page.set_viewport_size({'width':width,'height':844});page.wait_for_timeout(100)
                check(str(width)+'px actual HTTP UI stays within document width',lambda:assert_true(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
                if width<720:
                    for panel in ['project','inspector','workspace']:page.locator(f'[data-action="mobile"][data-panel="{panel}"]').click()
                if width==390:page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
            page.set_viewport_size({'width':1512,'height':982})
            # Service worker and offline persistence are verified on a real secure localhost origin.
            def sw_scope():
                page.evaluate('navigator.serviceWorker.ready');page.wait_for_function('navigator.serviceWorker.controller!==null');assert page.evaluate('(async()=>{const r=await navigator.serviceWorker.ready;return r.scope})()')==base+'/'
                keys=page.evaluate('(async()=>{const names=await caches.keys();let urls=[];for(const n of names)urls.push(...(await (await caches.open(n)).keys()).map(r=>r.url));return urls})()');assert all('/api/' not in k and '?share=' not in k for k in keys)
            check('root-scoped PWA excludes private APIs and review-token URLs from caches',sw_scope)
            current_title=page.locator('#project-title').inner_text();context.close()
            context=bt.launch_persistent_context(profile,viewport={'width':1512,'height':982},accept_downloads=True,**launch);page=context.pages[0];page.set_default_timeout(15000);observe(page)
            def reopen():
                page.goto(base,wait_until='networkidle');ready(page);expect(page.locator('#project-title')).to_have_text(current_title)
            check('IndexedDB project survives complete browser/profile restart',reopen)
            def offline():
                context.set_offline(True);page.reload(wait_until='domcontentloaded');ready(page);expect(page.locator('#project-title')).to_have_text(current_title);action(page,'account');expect(page.locator('#modal-title')).to_contain_text('تحتاج تشغيل الخادم');close(page);context.set_offline(False)
            check('offline PWA reload restores local project without claiming cloud connectivity',offline)
            context.close();check('all network UI scenarios have no uncaught JavaScript errors',lambda:assert_true(not errors,str(errors)))
    except Exception:
        if not results or results[-1]['status']!='FAIL':results.append({'name':'harness','status':'FAIL','error':traceback.format_exc()})
    finally:
        server.terminate()
        try:server.wait(timeout=8)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
        report={'engine':ENGINE,'renderer':locals().get('renderer','not-reached'),'transport':'real HTTP + real SQLite + real IndexedDB; not mocks','passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']=='FAIL' for r in results),'pageErrors':errors,'results':results}
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False),flush=True)
        raise SystemExit(1 if report['failed'] else 0)
