"""Real new Blender UI over an isolated API fixture owned by blender-e2e.mjs.
Never contact the public deployment. No credentials, project inputs or network mocks.
"""
import json,sys,os,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/blender';OUT.mkdir(parents=True,exist_ok=True)
config=json.loads(sys.stdin.read());base=config['base'];assert urlsplit(base).hostname in ['127.0.0.1','localhost']
checks=[];errors=[];external=[]
def check(name,fn):
    fn();checks.append(name);print(name,flush=True)
def action(name):page.locator('button[data-action="'+name+'"]').first.click()
def close():action('close-modal')
def truth(value):assert value
try:
 with sync_playwright() as pw:
    executable=os.environ.get('MASAR_CHROMIUM_PATH')
    launch={'headless':True,'args':['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if executable:launch['executable_path']=executable
    browser=pw.chromium.launch(**launch);context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page=context.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(base+'/') else None)
    page.goto(base,wait_until='networkidle');page.locator('#scene[data-ready="true"]').wait_for(state='attached')
    action('account');page.locator('#auth-form [name="email"]').fill(config['email']);page.locator('#auth-form [name="password"]').fill(config['password']);page.locator('#auth-form button[type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
    action('projects');page.locator('[data-action="open-cloud"][data-id="'+config['projectId']+'"]').click();expect(page.locator('#modal')).not_to_be_visible()
    check('real owner logs in and opens server-saved project',lambda:expect(page.locator('#plan-host svg')).to_be_visible())
    action('render-center');check('render center exposes actual server result',lambda:expect(page.locator('.render-job')).to_have_count(1))
    check('render job states current revision explicitly',lambda:expect(page.locator('.render-job')).to_contain_text('لنفس نسخة التصميم'))
    def export_scene():
        with page.expect_download() as event:page.locator('#render-local').click()
        scene=json.loads(Path(event.value.path()).read_text());expected=json.loads((OUT/'scene.json').read_text());assert scene==expected
    check('UI downloads exact immutable sanitized Blender contract',export_scene)
    page.locator('#render-pbr').click();canvas=page.locator('#render-canvas');expect(canvas).to_have_attribute('data-ready','true');expect(canvas).to_have_attribute('data-renderer','three-pbr')
    check('real Three.js WebGL2 PBR renderer displays snapshot',lambda:truth(int(canvas.get_attribute('data-objects'))>100))
    page.locator('[data-render-job-action="glb"]').click()
    # A source marker is set only when actual GLB parsing has completed.
    expect(canvas).to_have_attribute('data-source','blender-glb')
    check('real GLB from Blender parsed without external runtime URLs',lambda:truth(int(canvas.get_attribute('data-objects'))==len(json.loads((OUT/'scene.json').read_text())['objects'])))
    page.locator('#render-cutaway').check();canvas.scroll_into_view_if_needed();rect=canvas.bounding_box()
    for fy in [.5,.6,.4,.7,.3,.8]:
        for fx in [.5,.4,.6,.3,.7,.2,.8]:
            canvas.click(position={'x':rect['width']*fx,'y':rect['height']*fy})
            if 'تم تحديد' in page.locator('#render-selection').inner_text():break
        if 'تم تحديد' in page.locator('#render-selection').inner_text():break
    check('picking Blender mesh selects its linked MASAR room',lambda:expect(page.locator('#render-selection')).to_contain_text('تم تحديد المساحة'))
    canvas.screenshot(path=str(OUT/'viewer-pbr.png'))
    page.locator('[data-render-job-action="view"]').click()
    for image in page.locator('#render-gallery img').all():
        image.scroll_into_view_if_needed();expect(image).to_be_visible();image.evaluate('(img)=>img.decode()');assert image.evaluate('(img)=>img.naturalWidth')==640
    check('both actual Cycles images load behind owner authentication',lambda:expect(page.locator('#render-gallery img')).to_have_count(2))
    with page.expect_download() as event:page.locator('a[download]').filter(has_text='model.blend').click()
    check('generated .blend downloads through UI',lambda:truth(Path(event.value.path()).read_bytes().startswith(b'BLENDER')))
    page.screenshot(path=str(OUT/'render-desktop.png'),full_page=True)
    for width in [320,390,768]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('#modal').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'),str(width)
    check('render panel has no horizontal overflow at 320,390,768 pixels',lambda:None)
    page.set_viewport_size({'width':390,'height':844});page.locator('#render-studio').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'render-mobile.png'),full_page=True)
    close();check('closing enhanced viewer preserves original editor',lambda:expect(page.locator('#plan-host svg')).to_be_visible())
    action('render-center');page.locator('#render-pbr').click();expect(page.locator('#render-canvas')).to_have_attribute('data-ready','true');close()
    check('enhanced viewer disposes and can be opened again',lambda:expect(page.locator('#plan-host svg')).to_be_visible())
    check('no uncaught JavaScript exceptions',lambda:truth(not errors));check('no third-party network dependencies',lambda:truth(not external))
    browser.close()
 report={'status':'PASS','passed':len(checks),'failed':0,'checks':checks,'pageErrors':errors,'externalRequests':external,'scope':'Actual local HTTP and Blender GLB with software WebGL2; no physical iPhone or cloud GPU claimed'}
except Exception:
 report={'status':'FAIL','passed':len(checks),'failed':1,'checks':checks,'pageErrors':errors,'error':traceback.format_exc()}
finally:(OUT/'browser-render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False));sys.exit(0 if report['status']=='PASS' else 1)
