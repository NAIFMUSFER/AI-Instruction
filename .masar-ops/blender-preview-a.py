"""Live acceptance for approved option A. No render worker or paid infrastructure.
Only a new disposable account is created/deleted. No customer data is read.
"""
import hashlib,json,os,secrets,time,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
BASE='https://masar-blender-preview.onrender.com'
COMMIT='23bf68db1eba2dbb8863642b54c5c0c83613cc00'
OUT=Path(os.environ.get('MASAR_EVIDENCE_DIR','preview-a-evidence'));OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];external=[];unexpected_posts=[]
report={'scope':'Published option A: browser PBR and local scene export; cloud Blender rendering is disabled','url':BASE,'expectedCommit':COMMIT}
def require(value,message='assertion failed'):
    if not value:raise AssertionError(message)
def check(name,fn):
    fn();checks.append(name);print('PASS: '+name,flush=True)
def digest(value):return hashlib.sha256(value).hexdigest()
def action(name):page.locator('button[data-action="'+name+'"]').first.click()
def close():action('close-modal');expect(page.locator('#modal')).not_to_be_visible()
def download_scene(name):
    with page.expect_download(timeout=20000) as event:page.locator('#render-local').click()
    target=OUT/(name+'.json');event.value.save_as(target)
    require(event.value.suggested_filename=='MASAR-Blender-Scene.json')
    return json.loads(target.read_text())
def geometry(value):
    return [{k:o.get(k) for k in ['id','elementId','roomId','roomIds','category','min','size']} for o in value['objects']]
def export_project(name):
    action('export')
    with page.expect_download(timeout=20000) as event:page.locator('[data-action="download"][data-kind="json"]').click()
    target=OUT/(name+'.json');event.value.save_as(target);close()
    return json.loads(target.read_text())
def body(url):
    r=context.request.get(BASE+url,timeout=30000)
    require(r.status==200,url+': '+str(r.status));return r.json()
cleanup=None
try:
 with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    last=''
    for attempt in range(8):
        try:
            r=context.request.get(BASE+'/api/version',timeout=15000)
            if r.status==200 and r.json().get('commit')==COMMIT:break
            last=str(r.status)
        except Exception as e:last=type(e).__name__
        time.sleep(5)
    else:raise RuntimeError('Preview did not report tested commit: '+last)
    version=body('/api/version');report['version']=version
    check('published service is the exact verified feature commit',lambda:require(version['commit']==COMMIT and version['product']=='MASAR Studio'))
    health=body('/api/health');report['health']=health
    check('API discloses ephemeral storage and does not claim external AI',lambda:require(health['ok'] and health['persistenceClass']=='ephemeral' and not health['aiConfigured']))
    ready=body('/api/ready')
    check('SQLite readiness is healthy without a durability claim',lambda:require(ready['ready'] and ready['persistenceClass']=='ephemeral'))
    capability=body('/api/renders/capabilities');report['renderCapabilities']=capability
    check('option A keeps cloud rendering and worker availability disabled',lambda:require(capability['enabled'] is False and capability['workerOnline'] is False and capability['pipeline']=='blender-bridge-1.0.0'))
    expected={'render-engine.js':'8872b53929e5fee62e73daea14407087a9b8c5f7b5762171c1fa709825edf3f9','render-viewer.js':'1e256a355a5a9d5383b29599e70a227c8b190525fd56394867c6586b24cfffe1'}
    report['assets']={}
    for name,sha in expected.items():
        r=context.request.get(BASE+'/public/'+name)
        require(r.status==200 and digest(r.body())==sha,name+' differs from verified build')
        report['assets'][name]={'bytes':len(r.body()),'sha256':sha}
    check('self-hosted Three.js assets match the tested build byte-for-byte',lambda:require(len(report['assets'])==2))
    shell=context.request.get(BASE+'/')
    check('published HTTPS shell has CSP, HSTS and no framing',lambda:require("script-src 'self'" in shell.headers.get('content-security-policy','') and shell.headers.get('x-frame-options')=='DENY' and 'max-age=' in shell.headers.get('strict-transport-security','')))
    for path in ['/server/server.mjs','/data/masar.sqlite','/.env','/render-worker/build_scene.py']:require(context.request.get(BASE+path).status==404,path)
    check('private server code, data and configuration are not publicly served',lambda:None)
    require(context.request.get(BASE+'/api/renders').status==401)
    check('anonymous visitors cannot enumerate private render jobs',lambda:None)
    page=context.new_page();page.set_default_timeout(20000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    def request_seen(r):
        if r.url.startswith(('https:','http:')) and urlsplit(r.url).netloc!=urlsplit(BASE).netloc:external.append(r.url)
        if r.method=='POST' and ('/api/renders' in r.url or '/api/render-worker/' in r.url):unexpected_posts.append(r.url)
    page.on('request',request_seen)
    page.goto(BASE,wait_until='networkidle',timeout=60000)
    page.locator('#scene[data-ready="true"]').wait_for(state='attached')
    check('published editor renders a real 2D plan and original 3D view',lambda:expect(page.locator('#plan-host svg')).to_be_visible())
    check('temporary server storage warning is visible',lambda:expect(page.locator('#persistence-warning')).to_be_visible())
    before=export_project('project-before')
    action('render-center');expect(page.locator('#render-capability')).to_contain_text('غير مفعّل')
    check('Blender panel clearly states rendering is not enabled',lambda:expect(page.locator('#render-start')).to_be_disabled())
    base_scene=download_scene('scene-warm')
    require(base_scene['schema']=='masar-render-scene-1' and base_scene['units']=='m' and base_scene['source']['revisionId'])
    require(len(base_scene['objects'])>100)
    require(not any(key in base_scene for key in ['prompt','comments','references','account','user']))
    check('guest exports a revision-bound metre-based scene without private brief data',lambda:None)
    page.locator('#render-pbr').click();canvas=page.locator('#render-canvas')
    expect(canvas).to_have_attribute('data-ready','true');expect(canvas).to_have_attribute('data-renderer','three-pbr');expect(canvas).to_have_attribute('data-source','masar-snapshot')
    check('actual Three.js WebGL2 material preview loads the scene',lambda:require(int(canvas.get_attribute('data-objects'))==len(base_scene['objects'])))
    canvas.screenshot(path=str(OUT/'materials-warm.png'))
    from PIL import Image,ImageStat
    im=Image.open(OUT/'materials-warm.png').convert('RGB')
    check('PBR canvas contains rendered pixels rather than a blank image',lambda:require(max(ImageStat.Stat(im).stddev)>8))
    for finish in ['white','slate']:
        page.locator('#render-finish').select_option(finish);scene=download_scene('scene-'+finish)
        require(scene['settings']['finish']==finish and scene['materials']!=base_scene['materials'])
        require(geometry(scene)==geometry(base_scene),'finish altered geometry')
        page.locator('#render-pbr').click();expect(canvas).to_have_attribute('data-ready','true')
        canvas.screenshot(path=str(OUT/('materials-'+finish+'.png')))
    check('all three material presets change finishes without changing geometry',lambda:None)
    page.locator('#render-quality').select_option('standard');high=download_scene('scene-standard')
    check('higher image settings export honestly without starting cloud render',lambda:require(high['resolution']['width']==1280 and high['resolution']['height']==960 and geometry(high)==geometry(base_scene)))
    chosen=page.locator('#render-room option').all()[1].get_attribute('value');page.locator('#render-room').select_option(chosen);specific=download_scene('scene-room')
    check('selected interior room is preserved in camera contract',lambda:require(specific['cameras']['interior']['roomId']==chosen and geometry(specific)==geometry(base_scene)))
    page.locator('#render-furniture').uncheck();unfurnished=download_scene('scene-unfurnished')
    check('schematic furniture can be excluded from the exported scene',lambda:require(unfurnished['settings']['furniture'] is False and len(unfurnished['objects'])<len(base_scene['objects'])))
    page.locator('#render-cutaway').check();canvas.scroll_into_view_if_needed();rect=canvas.bounding_box();picked=False
    for fy in [.5,.6,.4,.7,.3,.8]:
        for fx in [.5,.4,.6,.3,.7,.2,.8]:
            canvas.click(position={'x':rect['width']*fx,'y':rect['height']*fy})
            if 'تم تحديد المساحة' in page.locator('#render-selection').inner_text():picked=True;break
        if picked:break
    check('clicking the material model selects its linked MASAR room',lambda:require(picked))
    page.screenshot(path=str(OUT/'blender-desktop.png'),full_page=True)
    for width in [320,390,768]:
        page.set_viewport_size({'width':width,'height':900});require(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),str(width));require(page.locator('#modal').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'),str(width))
    check('Blender panel fits 320,390,768px screens without horizontal overflow',lambda:None)
    page.set_viewport_size({'width':390,'height':844});page.locator('#render-studio').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'blender-mobile.png'),full_page=True)
    close();page.set_viewport_size({'width':1440,'height':1000});after=export_project('project-after');report['projectExportKeys']=list(before)
    if 'history' in before:require(before['history']==after['history'],'render settings changed project history')
    else:
        def stable_project(value):return {k:v for k,v in value.items() if k not in ['exportedAt','exported','generatedAt']}
        require(stable_project(before)==stable_project(after),'render settings changed project document')
    check('material, quality and camera changes leave canonical project history intact',lambda:None)
    action('render-center');page.locator('#render-pbr').click();expect(page.locator('#render-canvas')).to_have_attribute('data-ready','true');close()
    check('material viewer closes and reopens without breaking editor',lambda:expect(page.locator('#plan-host svg')).to_be_visible())
    check('guest UI never queues a cloud Blender job',lambda:require(not unexpected_posts))
    check('preview has no uncaught JavaScript errors or third-party runtime requests',lambda:require(not errors and not external))
    # Prove that an authenticated caller cannot bypass the disabled cloud-render button.
    password=secrets.token_urlsafe(26);email='preview-a-'+secrets.token_hex(8)+'@example.test'
    r=context.request.post(BASE+'/api/auth/register',headers={'Origin':BASE},data={'name':'Disposable preview verification','email':email,'password':password})
    require(r.status==201,'temporary account registration');session=r.json();cleanup={'password':password,'csrf':session['csrf']}
    cookie=next(c for c in context.cookies() if c['name']=='masar_session')
    check('production account cookie remains Secure and HttpOnly',lambda:require(cookie['secure'] and cookie['httpOnly']))
    r=context.request.post(BASE+'/api/renders',headers={'Origin':BASE,'X-CSRF-Token':cleanup['csrf']},data={})
    check('authenticated API refuses cloud rendering while option A is enabled',lambda:require(r.status==503))
    require(body('/api/renders')['jobs']==[]);check('disabled rendering creates no queued or fabricated successful jobs',lambda:None)
    r=context.request.delete(BASE+'/api/auth/account',headers={'Origin':BASE,'X-CSRF-Token':cleanup['csrf']},data={'password':password})
    require(r.status==200);cleanup=None
    check('disposable test account and its server session are removed',lambda:require(body('/api/auth/me')['user'] is None))
    report.update(status='PASS',passed=len(checks),failed=0,checks=checks,pageErrors=errors,externalRequests=external)
    browser.close()
except Exception:
    report.update(status='FAIL',passed=len(checks),failed=1,checks=checks,error=traceback.format_exc(),pageErrors=errors,externalRequests=external)
    try:page.screenshot(path=str(OUT/'failure.png'),full_page=True)
    except Exception:pass
    if cleanup:
        try:
            r=context.request.delete(BASE+'/api/auth/account',headers={'Origin':BASE,'X-CSRF-Token':cleanup['csrf']},data={'password':cleanup['password']});report['cleanupSuccessful']=r.status==200
        except Exception:report['cleanupSuccessful']=False
finally:
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
raise SystemExit(0 if report['status']=='PASS' else 1)
