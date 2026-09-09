"""Real UI floor isolation and camera presets. Temporary profiles, no account/data writes.
Chromium exercises WebGL output; WebKit covers honest disabled state and source JSON.
"""
import json,os,socket,subprocess,tempfile,time,traceback,urllib.request,struct
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from PIL import Image,ImageChops,ImageStat,ImageDraw
import math
ROOT=Path(__file__).resolve().parents[1];ENGINE=os.environ.get('MASAR_BROWSER','chromium');BASE=os.environ.get('MASAR_ACCEPTANCE_URL')
OUT=ROOT/'test-output'/'view-controls'/ENGINE;OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];requests=[];server=None
PROMPT=(ROOT/'tests/fixtures/customer-chalet-ar.txt').read_text()
def passed(name):checks.append({'name':name,'status':'pass'});print('VIEW_PASS '+name,flush=True)
def glb_document(path):
    raw=path.read_bytes();magic,version,size,jlen,jtype=struct.unpack('<5I',raw[:20])
    assert magic==0x46546c67 and version==2 and size==len(raw) and jtype==0x4e4f534a
    return json.loads(raw[20:20+jlen])
def check_image_framing(path, radius):
    image=Image.open(path).convert('RGB')
    background=Image.new('RGB',image.size,max(image.getcolors(image.width*image.height),key=lambda item:item[0])[1])
    diff=ImageChops.difference(image,background)
    # Threshold anti-aliasing/shadow noise; actual geometry must not touch the frame.
    mask=diff.convert('L').point(lambda v:255 if v>12 else 0)
    # Element screenshots contain CSS-rounded white corners and up to one pixel
    # of subpixel capture padding; these are not objects in the WebGL scene.
    aperture=Image.new('L',image.size,0)
    ImageDraw.Draw(aperture).rounded_rectangle((1,1,image.width-2,image.height-2),radius=math.ceil(radius)+1,fill=255)
    mask=ImageChops.multiply(mask,aperture)
    box=mask.getbbox();assert box and box[2]-box[0]>20 and box[3]-box[1]>20,(str(path),box)
    assert box[0]>1 and box[1]>1 and box[2]<image.width-1 and box[3]<image.height-1,(str(path),box,image.size)
def capture_frame(canvas, path):
    # Native sticky dialog headers may overlap a locator screenshot when the
    # previous preset/select scrolled only its own control into view.
    canvas.evaluate("""async e=>{e.scrollIntoView({block:'center',inline:'nearest'});
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}""")
    canvas.screenshot(path=str(path))
with tempfile.TemporaryDirectory(prefix='masar-view-controls-') as tmp:
    try:
        if not BASE:
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            BASE=f'http://127.0.0.1:{port}'
            env={**os.environ,'NODE_ENV':'development','HOST':'127.0.0.1','PORT':str(port),'PUBLIC_ORIGIN':BASE,'DB_PATH':tmp+'/db.sqlite','PERSISTENCE_CLASS':'ephemeral','BLENDER_RENDER_ENABLED':'false'}
            server=subprocess.Popen(['node','server/server.mjs'],cwd=ROOT,env=env,stdout=open(OUT/'server.log','w'),stderr=subprocess.STDOUT)
            for _ in range(100):
                try:
                    with urllib.request.urlopen(BASE+'/api/health',timeout=1) as r:assert r.status==200
                    break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('local server failed to start')
        with sync_playwright() as pw:
            options={'headless':True}
            if ENGINE=='chromium':
                options['args']=['--use-angle=swiftshader','--enable-unsafe-swiftshader']
                if os.environ.get('MASAR_CHROMIUM_PATH'):options['executable_path']=os.environ['MASAR_CHROMIUM_PATH']
            browser=getattr(pw,ENGINE).launch(**options)
            context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
            page=context.new_page();page.set_default_timeout(20000)
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append((r.method,r.url)))
            def action(name):
                scope=page.locator('#modal') if page.locator('#modal').evaluate('e=>e.open') else page
                scope.locator(f'button[data-action="{name}"]').first.click()
            def close():page.locator('#modal button[data-action="close-modal"]').first.click()
            def download(selector,name):
                with page.expect_download(timeout=30000) as d:page.locator(selector).click()
                path=OUT/name;d.value.save_as(str(path));assert path.stat().st_size>0;return path
            def history(name):
                action('export');path=download('[data-kind="json"]',name);close();return json.loads(path.read_text())['history']
            def generate(text):
                action('new');page.locator('#new-prompt').fill(text);page.locator('#new-form [type="submit"]').click()
                page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form [type="submit"]').click();expect(page.locator('#modal')).not_to_be_visible()
            def build_view():
                page.locator('#render-pbr').click();expect(page.locator('#render-canvas')).to_have_attribute('data-export-ready','true')
                expect(page.locator('#render-view-level')).to_be_enabled()
            page.goto(BASE,wait_until='domcontentloaded',timeout=120000);page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=60000)
            generate(PROMPT);before=history('chalet-before.json')
            passed('exact original long chalet brief generates unchanged before camera review')
            action('render-center');expect(page.locator('#render-start')).to_be_disabled()
            for id in ['#render-view-level','#render-view-angle','#render-view-fit']:expect(page.locator(id)).to_be_disabled()
            passed('floor and camera actions stay unavailable until an actual viewer exists; no cloud render is enabled')
            expect(page.locator('#render-canvas-host')).to_contain_text('GLB يبقى كاملًا')
            expect(page.locator('#render-canvas-host')).to_contain_text('ليست تحديدًا لجهة الشارع')
            spec=json.loads(download('#render-local','chalet-scene.json').read_text())
            assert spec['source']['modelId']==before['revisions'][before['cursor']]['model']['id']
            passed('source scene identity and clear visual-only floor compass and export limits are retained')
            if ENGINE=='chromium':
                build_view();canvas=page.locator('#render-canvas')
                page.locator('#render-cutaway').check()
                for width in [320,390,768,1280]:
                    page.set_viewport_size({'width':width,'height':844})
                    for preset in ['iso','top','north','south','east','west']:
                        page.locator('#render-view-angle').select_option(preset)
                        expect(canvas).to_have_attribute('data-view-preset',preset)
                        image=OUT/f'chalet-{width}-{preset}.png';capture_frame(canvas,image);check_image_framing(image,float(canvas.evaluate('e=>parseFloat(getComputedStyle(e).borderTopLeftRadius)||0')))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert page.locator('#modal').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                passed('all six real camera presets frame the whole visible scene at 320 390 768 and 1280 pixels without clipping')
                page.set_viewport_size({'width':390,'height':844});page.locator('#render-view-angle').select_option('iso')
                page.locator('#render-view-level').select_option(before['revisions'][before['cursor']]['model']['levels'][0]['id'])
                png=download('#render-save-png','chalet-floor.png');assert Image.open(png).size==(640,480)
                passed('single-floor PNG contains its actual visible scene and preserves existing bounded resolution')
                page.locator('#render-finish').select_option('slate')
                for id in ['#render-view-level','#render-view-angle','#render-view-fit','#render-save-glb']:expect(page.locator(id)).to_be_disabled()
                build_view();expect(page.locator('#render-view-level')).to_have_value('');expect(page.locator('#render-view-angle')).to_have_value('iso')
                passed('changing scene settings invalidates old view controls and regeneration resets visual scope to all floors')
            close();assert history('chalet-after.json')==before
            passed('camera controls material options and captures leave complete original history unchanged')
            generate('فيلا على أرض 20×25 ثلاثة أدوار إجمالاً وخمس غرف نوم بدون مسبح')
            original=history('multifloor-before.json');model=original['revisions'][original['cursor']]['model'];assert len(model['levels'])==3
            action('render-center')
            options=page.locator('#render-view-level option').evaluate_all('nodes=>nodes.map(n=>({id:n.value,label:n.textContent}))')
            assert [o['id'] for o in options]==['']+[l['id'] for l in model['levels']]
            for level in model['levels']:assert any(o['id']==level['id'] and level['name'] in o['label'] for o in options)
            scene=json.loads(download('#render-local','multifloor-scene.json').read_text())
            passed('all three canonical floor identities and names populate the actual selector in elevation order')
            if ENGINE=='chromium':
                build_view();canvas=page.locator('#render-canvas');page.locator('#render-cutaway').check()
                for index,level in enumerate(model['levels']):
                    page.locator('#render-view-level').select_option(level['id'])
                    page.locator('#render-view-angle').select_option('top')
                    expected=[o for o in scene['objects'] if o.get('levelId')==level['id'] and o.get('category') not in ['roof','ceiling']]
                    expect(canvas).to_have_attribute('data-view-level',level['id'])
                    expect(canvas).to_have_attribute('data-visible-objects',str(len(expected)))
                    expect(page.locator('#render-view-state')).to_contain_text(level['name'])
                    image=OUT/f'floor-{index+1}.png';capture_frame(canvas,image);check_image_framing(image,float(canvas.evaluate('e=>parseFloat(getComputedStyle(e).borderTopLeftRadius)||0')))
                    rooms={r['id'] for r in level['rooms']};picked=False
                    box=canvas.bounding_box()
                    for fy in [.5,.4,.6,.3,.7,.2,.8]:
                        for fx in [.5,.4,.6,.3,.7,.2,.8]:
                            canvas.click(position={'x':box['width']*fx,'y':box['height']*fy})
                            text=page.locator('#render-selection').inner_text()
                            if 'تم تحديد المساحة' in text:
                                assert any(r['name'] in text for r in level['rooms']),text
                                picked=True;break
                        if picked:break
                    assert picked,'no visible room was selectable on floor '+level['name']
                passed('each isolated floor renders only its own real objects and permits room picking without hidden-floor hits')
                isolated=glb_document(download('#render-save-glb','isolated-full-model.glb'))
                nodes=[n for n in isolated['nodes'] if 'mesh' in n]
                assert len(nodes)==len(scene['objects'])
                assert {n['extras'].get('levelId') for n in nodes if n['extras'].get('levelId')}=={l['id'] for l in model['levels']}
                assert sum(n['extras'].get('category')=='roof' for n in nodes)==sum(o['category']=='roof' for o in scene['objects'])
                passed('GLB exported from an isolated floor retains every floor and roof in the canonical contract')
                page.locator('#render-view-level').select_option('')
                expect(canvas).to_have_attribute('data-visible-objects',str(sum(o.get('category') not in ['roof','ceiling'] for o in scene['objects'])))
                page.locator('#render-cutaway').uncheck();expect(canvas).to_have_attribute('data-visible-objects',str(len(scene['objects'])))
                full=glb_document(download('#render-save-glb','all-floors-model.glb'))
                assert isolated==full
                passed('all-floors reset restores site roofs and exact object count; visual isolation never changes complete GLB contents')
                page.locator('#render-view-level').select_option(model['levels'][1]['id'])
                page.locator('#render-view-angle').select_option('iso');page.locator('#render-cutaway').check()
                canvas.screenshot(path=str(OUT/'multifloor-selected.png'))
                image=download('#render-save-png','selected-floor.png');assert Image.open(image).size==(640,480)
                beforeBox=canvas.bounding_box()
                page.locator('#render-view-fit').click()
                assert all(canvas.bounding_box()[k]==beforeBox[k] for k in ['width','height'])
                page.screenshot(path=str(OUT/'view-controls-mobile.png'),full_page=True)
                passed('selected-floor PNG and refit leave the user viewport size intact')
            close();assert history('multifloor-after.json')==original
            page.reload(wait_until='domcontentloaded');page.locator('#scene[data-ready="true"]').wait_for(state='attached',timeout=30000)
            assert history('multifloor-reload.json')==original
            passed('full multifloor source history survives display navigation downloads close and reload byte-for-byte')
            action('render-center')
            for id in ['#render-view-level','#render-view-angle','#render-view-fit']:expect(page.locator(id)).to_be_disabled()
            close();passed('reopening a dialog never reuses controls from the disposed viewer')
            assert not errors,errors
            assert not [(m,u) for m,u in requests if m not in ['GET','HEAD'] or u.startswith(('https:','http:')) and not u.startswith(BASE+'/')],requests
            passed('no unhandled errors external requests render jobs or account writes')
            # A standalone viewer harness tests real Three.js visibility/picking, without
            # injecting model state into the product. Deliberately overlapping test boxes.
            if ENGINE=='chromium':
                unit=context.new_page();unit.goto(BASE,wait_until='domcontentloaded')
                result=unit.evaluate("""async()=>{const {createViewer}=await import('/public/render-viewer.js');
                    const c=document.createElement('canvas');c.width=400;c.height=400;c.style.width='400px';c.style.height='400px';document.body.replaceChildren(c);
                    const spec={source:{modelId:'unit',revisionId:'unit'},materials:{wall:{color:'#aaaaaa',roughness:.8,metallic:0}},proofs:{rooms:[{levelId:'G',elevation:0},{levelId:'U',elevation:3}]},objects:[
                        {id:'visible',shape:'box',min:[0,0,0],size:[2,2,2],material:'wall',levelId:'G',roomId:'visible-room',category:'wall'},
                        {id:'hidden',shape:'box',min:[0,-1,0],size:[2,2,2],material:'wall',levelId:'U',roomId:'hidden-room',category:'wall'}]};
                    window.picked=[];window.v=createViewer(c,id=>window.picked.push(id));v.setScene(spec);v.setView({levelId:'G',preset:'south'});
                    return v.viewState();}""")
                assert result['visibleObjectIds']==['visible']
                unit.locator('canvas').click(position={'x':200,'y':200});assert unit.evaluate('picked.at(-1)')=='visible-room'
                unit.evaluate('v.dispose()');unit.close()
                passed('independent real Three.js harness rejects a nearer invisible mesh instead of selecting a hidden floor')
            browser.close()
    except Exception as error:
        checks.append({'name':'view controls failed','status':'fail','error':str(error),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
    finally:
        if server:server.terminate();server.wait(timeout=10)
        report={'engine':ENGINE,'origin':BASE,'passed':sum(c['status']=='pass' for c in checks),'failed':sum(c['status']=='fail' for c in checks),'checks':checks,'pageErrors':errors,'scope':'Chromium real software-WebGL floors cameras PNG GLB; WebKit UI/source only. No physical phone test or geometric/model redesign.'}
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VIEW_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
if report['failed']:raise SystemExit(1)
