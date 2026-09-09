"""Browser-only visual outputs from the real customer journey; no injected model state."""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request,struct,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from PIL import Image,ImageStat
ROOT=Path(__file__).resolve().parents[1];ENGINE=os.environ.get('MASAR_BROWSER','chromium');BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
OUT=ROOT/'test-output/material-downloads'/ENGINE;OUT.mkdir(parents=True,exist_ok=True)
PROMPT=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text();checks=[];errors=[];requests=[];server=None

def passed(name):checks.append({'name':name,'status':'pass'});print('VISUAL_DOWNLOAD_PASS '+name,flush=True)
def parse_glb(path,spec):
    raw=path.read_bytes();magic,version,size,jlen,jtype=struct.unpack('<5I',raw[:20]);assert magic==0x46546c67 and version==2 and size==len(raw) and jtype==0x4e4f534a
    doc=json.loads(raw[20:20+jlen]);nodes=[n for n in doc['nodes'] if 'mesh' in n]
    assert len(nodes)==len(spec['objects'])
    root=next(n for n in doc['nodes'] if n.get('extras',{}).get('schema')=='masar-browser-visual-1')
    assert root['extras']['modelId']==spec['source']['modelId'] and root['extras']['revisionId']==spec['source']['revisionId']
    assert root['extras']['roof']=='included' and root['extras']['finish']==spec['settings']['finish'] and root['extras']['furniture']==spec['settings']['furniture']
    expected={o['id']:o for o in spec['objects']};assert set(n['extras']['objectId'] for n in nodes)==set(expected)
    for n in nodes:
        o=expected[n['extras']['objectId']];matrix=n.get('matrix');p=[matrix[i] for i in [12,13,14]] if matrix else n.get('translation',[0,0,0])
        target=[o['min'][0]+o['size'][0]/2,o['min'][2]+o['size'][2]/2,-o['min'][1]-o['size'][1]/2]
        assert max(abs(a-b) for a,b in zip(p,target))<1e-4,(o['id'],p,target)
        for primitive in doc['meshes'][n['mesh']]['primitives']:
            acc=doc['accessors'][primitive['attributes']['POSITION']];size=[b-a for a,b in zip(acc['min'],acc['max'])]
            target_size=[o['size'][0],o['size'][2],o['size'][1]];assert max(abs(a-b) for a,b in zip(size,target_size))<1e-4,(o['id'],size,target_size)
    assert any(n['extras'].get('category')=='roof' for n in nodes)
    assert not any(x.get('uri') for key in ['buffers','images'] for x in doc.get(key,[]));assert not doc.get('extensionsRequired')
    serialized=json.dumps(doc,ensure_ascii=False);assert PROMPT[:60] not in serialized and 'PRIVATE_MARKER' not in serialized
    return doc
with tempfile.TemporaryDirectory(prefix='masar-visual-downloads-') as tmp:
    try:
        if not BASE:
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}';env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/db.sqlite','PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
            for _ in range(100):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as r:assert r.status==200
                    break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('server did not start')
        with sync_playwright() as pw:
            options={'headless':True}
            if ENGINE=='chromium':options['args']=['--use-angle=swiftshader','--enable-unsafe-swiftshader']
            browser=getattr(pw,ENGINE).launch(**options);context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
            page=context.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append((r.method,r.url)))
            def action(name):
                scope=page.locator('#modal') if page.locator('#modal').evaluate('e=>e.open') else page
                scope.locator(f'button[data-action="{name}"]').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').first.click()
            def download(selector,name):
                with page.expect_download(timeout=30000) as d:page.locator(selector).click()
                path=OUT/name;d.value.save_as(str(path));assert path.stat().st_size>0;return path
            def history(name):
                action('export');path=download('[data-kind="json"]',name);close();return json.loads(path.read_text())['history']
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            action('new');page.locator('#new-prompt').fill(PROMPT);page.locator('#new-form [type="submit"]').click();page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form [type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
            before=history('before-project.json');passed('exact original customer description generates before visual downloads')
            action('render-center');expect(page.locator('#render-start')).to_be_disabled();expect(page.locator('#render-save-png')).to_be_disabled();expect(page.locator('#render-save-glb')).to_be_disabled();passed('cloud rendering stays disabled and local exports require an actual rendered scene')
            expect(page.locator('#material-downloads')).to_contain_text('ليس ملف MASAR');passed('visual GLB and PNG are explicitly distinguished from source projects and Blender renders')
            if ENGINE=='chromium':
                page.locator('#render-pbr').click();expect(page.locator('#render-canvas')).to_have_attribute('data-export-ready','true');expect(page.locator('#render-save-glb')).to_be_enabled();page.locator('#render-cutaway').check()
                spec=json.loads(download('#render-local','warm-scene.json').read_text());passed('export controls activate only for the current canonical source')
                box_before=page.locator('#render-canvas').bounding_box();png=download('#render-save-png','preview.png');im=Image.open(png);assert im.size==(640,480);assert max(ImageStat.Stat(im.crop((0,0,640,436)).convert('RGB')).stddev)>5
                assert page.locator('#render-canvas').bounding_box()==box_before;passed('PNG contains nonblank current-view pixels and restores canvas dimensions')
                glb=download('#render-save-glb','warm-model.glb');warm=parse_glb(glb,spec);passed('GLB has every source object with actual dimensions identities and full roof while cutaway is on')
                canvas=page.locator('#render-canvas');box=canvas.bounding_box();picked=False
                for fy in [.5,.4,.6,.3,.7]:
                    for fx in [.5,.4,.6,.3,.7]:
                        canvas.click(position={'x':box['width']*fx,'y':box['height']*fy})
                        if 'تم تحديد المساحة' in page.locator('#render-selection').inner_text():picked=True;break
                    if picked:break
                assert picked,'could not select an actual room'
                selected=parse_glb(download('#render-save-glb','selected-model.glb'),spec)
                assert warm['materials']==selected['materials'];passed('room-selection highlighting never leaks into exported GLB materials')
                page.locator('#render-finish').select_option('slate');expect(page.locator('#render-save-png')).to_be_disabled();expect(page.locator('#render-save-glb')).to_be_disabled();expect(page.locator('#render-download-state')).to_contain_text('تغيّرت');passed('changing finishes marks exports stale instead of downloading outdated output')
                page.locator('#render-quality').select_option('standard');page.locator('#render-furniture').uncheck();page.locator('#render-pbr').click();expect(page.locator('#render-save-glb')).to_be_enabled()
                slate_spec=json.loads(download('#render-local','slate-scene.json').read_text());slate=parse_glb(download('#render-save-glb','slate-model.glb'),slate_spec)
                assert warm['materials']!=slate['materials'];assert not any(n.get('extras',{}).get('category')=='furniture' for n in slate['nodes']);passed('regenerated GLB follows selected finishes and omitted furniture without altering architecture')
                im=Image.open(download('#render-save-png','standard.png'));assert im.size==(1280,960);passed('higher-resolution local PNG is an actual 1280 by 960 image')
                for width in [320,390,768]:
                    page.set_viewport_size({'width':width,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert page.locator('#modal').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                page.set_viewport_size({'width':390,'height':844});page.locator('#material-downloads').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'downloads-mobile.png'),full_page=True);passed('download controls remain usable without clipping at 320 390 and 768 pixels')
            else:
                # Linux WebKit does not establish physical iPhone/WebGL2 support here.
                spec=json.loads(download('#render-local','webkit-scene.json').read_text());assert spec['schema']=='masar-render-scene-1';passed('WebKit retains account-free JSON scene download without requiring PBR support')
            close();assert history('after-project.json')==before;passed('visual downloads and settings preserve the complete original geometry and revision history')
            action('render-center');expect(page.locator('#render-save-glb')).to_be_disabled();close();passed('reopening the dialog cannot export an earlier disposed viewer as the current preview')
            page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000);assert history('reloaded-project.json')==before;passed('original project survives reload after local export activity')
            assert not any(method=='POST' and '/api/renders' in url for method,url in requests);assert not any(url.startswith(('https:','http:')) and not url.startswith(BASE+'/') for _,url in requests);assert not errors;passed('no render jobs account writes third-party runtime calls or unhandled JavaScript errors')
            browser.close()
    except Exception as e:
        checks.append({'name':'visual download failure','status':'fail','error':str(e),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
    finally:
        if server:server.terminate();server.wait(timeout=10)
        report={'engine':ENGINE,'origin':BASE,'passed':sum(x['status']=='pass' for x in checks),'failed':sum(x['status']=='fail' for x in checks),'checks':checks,'pageErrors':errors,'scope':'Chromium software-WebGL local output; WebKit UI/JSON/history only, not physical iPhone or cloud rendering'}
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VISUAL_DOWNLOAD_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
if report['failed']:raise SystemExit(1)
