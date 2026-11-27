'use strict';
// The owner's "upload my own plan" path in the shipped page, on a phone and on
// a desktop: a 12 MP phone photo, a file that is not a plan, a two-page PDF
// mapped to two floors, the scale and north questions, the paid
// confirmation, the read's review beside its original, and delete.
// Actual workspace routes with the CI-only identity and controlled provider of
// connected_workspace_browser_server.py; no live account or provider.
//   PYTHON=<venv python> node tests/remediation/test_plan_upload_browser.cjs
// ACS_UPLOAD_UI_PORT picks the loopback port; ACS_UPLOAD_UI_SHOTS, a folder
// for phone screenshots (deviceScaleFactor 1).
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn,execFileSync}=require('node:child_process');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
// Sign-in works only on the official site's origin (any other is a preview copy).
const ORIGIN=/OFFICIAL_ORIGIN\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(PUB,'app','boot','api-base.js'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const PY=process.env.PYTHON||'python',PORT=Number(process.env.ACS_UPLOAD_UI_PORT||8893),SHOTS=process.env.ACS_UPLOAD_UI_SHOTS||'';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let checks=0;const ok=(value,label)=>{assert.ok(value,label);checks++;};

function inputs(dir){
  execFileSync(PY,['-c',`import sys, io
from PIL import Image, ImageDraw
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
d=sys.argv[1]
# A 12 MP phone photo of a plan, with camera and GPS metadata.
im=Image.new('RGB',(3024,4032),(236,232,222)); g=ImageDraw.Draw(im)
for i in range(0,3024,180): g.line([(i,0),(i+40,4032)],fill=(40,40,52),width=6)
for j in range(0,4032,220): g.line([(0,j),(3024,j+30)],fill=(40,40,52),width=6)
ex=Image.Exif(); ex[0x010F]='ExamplePhone'; ex[0x8825]={1:'N',2:(24.0,42.0,0.0)}
im.save(d+'/phone_12mp.jpg','JPEG',quality=85,exif=ex)
# Not a plan: a colourful photo-like picture.
im=Image.new('RGB',(1200,900)); px=im.load()
import math
for y in range(900):
  for x in range(1200): px[x,y]=(int(128+120*math.sin(x/37+y/53)),int(128+120*math.sin(x/23-y/41)),int(128+120*math.cos((x+y)/61)))
im.save(d+'/not_a_plan.jpg','JPEG',quality=85)
# A two-page vector PDF, one floor drawn per page.
w=PdfWriter()
for x in (20,100):
  p=w.add_blank_page(width=300,height=300); s=DecodedStreamObject()
  s.set_data(('0 0 0 RG 2 w %s 20 80 100 re S 20 20 260 260 re S 20 150 m 280 150 l S' % x).encode())
  p[NameObject('/Contents')]=w._add_object(s)
w.write(d+'/two_floors.pdf')`,dir]);
}

async function stats(){return (await (await fetch('http://127.0.0.1:'+PORT+'/test-stats')).json());}
async function objects(){return (await (await fetch('http://127.0.0.1:'+PORT+'/test-source-objects')).json());}
async function shot(page,name){if(!SHOTS)return;fs.mkdirSync(SHOTS,{recursive:true});await page.screenshot({path:path.join(SHOTS,name+'.png'),fullPage:false});}
async function status(page,text){await page.waitForFunction(t=>document.querySelector('#cwSourceStatus')?.textContent.includes(t)||document.querySelector('#cwStatus')?.textContent.includes(t),text,{timeout:20000});}

async function run(browser,dir,width){
  const phone=width<600;
  const context=await browser.newContext({viewport:{width,height:phone?852:900},deviceScaleFactor:1,acceptDownloads:true});
  const page=await context.newPage(),errors=[],bodies=[];
  const snap=name=>shot(page,(phone?'phone-':'desktop-')+name);
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.hostname==='acs-engine.onrender.com'){
      if(req.method()==='POST'&&url.pathname.endsWith('/workspace'))bodies.push(req.postDataJSON());
      return route.fulfill({response:await route.fetch({url:'http://127.0.0.1:'+PORT+url.pathname+url.search})});
    }
    if(url.origin!==ORIGIN)return route.abort();
    const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream','content-security-policy':CSP},body:fs.readFileSync(f)});
  });
  await page.goto(ORIGIN+'/?signin=1');
  await page.locator('#acsAuthEmailToggle').click();await page.locator('#lgEmail').fill('fixture@example.test');await page.locator('#lgPassword').fill('fixture-password');await page.locator('#lgGo').click();
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
  await page.locator('#cwNewProject').click();await page.locator('#cwProjectName').fill('قراءة مخطط '+width);
  await Promise.all([page.waitForEvent('framenavigated',frame=>frame===page.mainFrame()),page.locator('#cwNewProjectForm button[type=submit]').click()]);
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
  await page.locator('#cwType').selectOption('residential');
  await page.locator('#cwBrief').fill('قراءة مخطط فيلا سكنية من دورين من ملفي.');
  await page.locator('#cwWidth').fill('20');await page.locator('#cwDepth').fill('25');await page.locator('#cwLevels').fill('1');
  await page.locator('#cwStartMode').selectOption('upload');
  ok(await page.locator('#cwPlot').isHidden(),'U8: the plot section is hidden in upload mode');
  ok((await page.locator('#cwPlotNote').textContent()).includes('أخفينا قسم الأرض'),'U8: the page says why');

  // U2: a 12 MP phone photo is reduced on the device and saved without its metadata.
  const generationBefore=(await stats()).generation;
  await page.locator('#cwPlanFile').setInputFiles(path.join(dir,'phone_12mp.jpg'));
  await status(page,'صغّرنا الصورة من 3024×4032 إلى 1932×2576');
  ok(await page.locator('#cwNotPlan').isHidden(),'U10: a photographed plan passes the plan check');
  await page.locator('#cwSourceStatus').scrollIntoViewIfNeeded();await snap('01-12mp-photo-reduced');
  await page.locator('#cwSaveSource').click();await status(page,'حُفظ الأصل');
  let stored=await objects();
  const originals=stored.filter(o=>o.key.endsWith('/original'));
  ok(originals.length>=1&&originals.every(o=>!o.exif&&o.bytes<=5*1024*1024),'U2/U12: stored photo has no EXIF and fits 5 MB');
  ok(!(await page.locator('#cwStatus').getAttribute('class')||'').includes('bad'),'no red error after the save');

  // U10: a picture that is not a plan needs the owner's confirmation before saving.
  await page.locator('#cwPlanFile').setInputFiles(path.join(dir,'not_a_plan.jpg'));
  await page.locator('#cwNotPlan').waitFor({state:'visible'});
  ok(await page.locator('#cwSaveSource').isDisabled(),'U10: saving waits for the confirmation');
  await snap('02-not-a-plan-warning');
  await page.locator('#cwNotPlanConfirm').check();
  ok(await page.locator('#cwSaveSource').isEnabled(),'U10: the owner can still save after confirming');

  // U4: two floors confirmed -> map one page of the PDF to each floor.
  await page.locator('#cwLevels').fill('2');
  await page.locator('#cwFloorMap').waitFor({state:'visible'});
  await page.locator('#cwPlanFile').setInputFiles(path.join(dir,'two_floors.pdf'));
  await page.locator('#cwSaveAllPages').waitFor({state:'visible'});
  const preview=await page.locator('#cwSourcePreview').evaluate(img=>new Promise(r=>{const i=new Image();i.onload=()=>r(Math.max(i.naturalWidth,i.naturalHeight));i.src=img.src;}));
  ok(preview===2576,'U6: a PDF page is rendered at the 2576 px read size, got '+preview);
  await page.locator('#cwSaveAllPages').click();await status(page,'حُفظت صفحتان ورُبطت بالأدوار بالترتيب');
  const floorIds=[await page.locator('#cwFloorSource0').inputValue(),await page.locator('#cwFloorSource1').inputValue()];
  ok(floorIds[0]&&floorIds[1]&&floorIds[0]!==floorIds[1],'U4: each floor has its own saved page');
  ok((await page.locator('#cwFloorSource1 option:checked').textContent()).includes('الصفحة 2 من 2'),'U4: the upper floor is page 2');
  stored=await objects();
  const pdfOriginals=stored.filter(o=>o.key.endsWith('/original')&&o.bytes<200000&&o.bytes>500).length;
  const previews=stored.filter(o=>o.key.endsWith('/preview')).length;
  ok(previews===originals.length+2&&stored.filter(o=>o.key.endsWith('/original')).length===originals.length+1,
     'U12: the PDF is stored once for its two pages ('+JSON.stringify(stored.map(o=>o.key.split('/').slice(1).join('/')))+')');
  void pdfOriginals;

  // U5: the read asks how the drawing is scaled and where north is.
  await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('اختر كيف نضبط مقياس الرسم'));
  ok(true,'U5: the scale question is required');
  await page.locator('#cwSourceScale').selectOption('known');await page.locator('#cwScaleKnown').waitFor({state:'visible'});
  await page.locator('#cwScaleLabel').fill('عرض المجلس');await page.locator('#cwScaleMeters').fill('٥٫٥');
  await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('أين الشمال'));
  ok(true,'U5: the north question is required');
  await page.locator('#cwSourceNorth').selectOption('arrow');
  await page.locator('#cwSourceAxes').scrollIntoViewIfNeeded();await snap('03-floor-map-scale-north');
  await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();

  // U13: step 2 and the paid confirmation speak of a read, one per floor.
  await page.locator('#cwGenerateSource').waitFor({state:'visible'});
  ok((await page.locator('[data-step-panel="2"] .cw-card h2').first().textContent())==='قراءة مخططك','U13: step 2 title');
  ok((await page.locator('#cwGenerateSource').textContent())==='قراءة المخطط وحفظ مسودة','U13: step 2 button');
  await snap('04-step2-read');
  await page.locator('#cwGenerateSource').click();await page.locator('#cwPaidConfirm').waitFor({state:'visible'});
  const dialog=await page.locator('#cwPaidConfirm').textContent();
  ok(dialog.includes('قراءة مخططك بالذكاء الاصطناعي؟')&&dialog.includes('سيُقرأ دوران: قراءة واحدة لكل دور (قراءتان)')&&dialog.includes('من 20 إلى 30 ثانية')&&dialog.includes('سنتات'),'U13: confirmation names reads, time and cost: '+dialog);
  await snap('05-paid-confirm');
  await page.locator('#cwCancelGenerate').click();
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('لم تبدأ القراءة'));
  ok((await stats()).generation===generationBefore,'cancel starts nothing');
  await page.locator('#cwGenerateSource').click();await page.locator('#cwConfirmGenerate').click();
  await page.locator('#cwReviewContent').waitFor({state:'visible',timeout:45000});
  const sent=bodies.find(b=>b.action==='generate');
  ok(sent.source_id===floorIds[0]&&JSON.stringify(sent.source_read.floors)===JSON.stringify([{source_id:floorIds[0],level:0},{source_id:floorIds[1],level:1}]),'U4: one request maps both floors');
  ok(JSON.stringify(sent.source_read.scale)===JSON.stringify({kind:'known',label:'عرض المجلس',meters:5.5})&&sent.source_read.north==='arrow','U5: answers are sent');
  ok(sent.max_provider_calls===4,'U4: at most two reads per floor');
  ok((await stats()).generation===generationBefore+1,'one paid job');
  // U13: the read is reviewed beside its original, named as a read.
  await page.locator('#cwSourceOriginal img').waitFor({state:'visible',timeout:20000});
  ok((await page.locator('#cwSourceOriginal figcaption').textContent()).includes('الأصل من ملفك'),'U13: original beside the draft');
  ok((await page.locator('#cwRevision option:checked').textContent()).includes('مقروء من ملفك')||(await page.locator('#cwRevision').textContent()).includes('مقروء من ملفك'),'U13: version name');
  await page.locator('#cwSourceOriginal').scrollIntoViewIfNeeded();await snap('06-review-original-beside-draft');
  ok(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth<=innerWidth),'no horizontal scroll at '+width);

  // U12: the uploader deletes a saved file (two taps).
  await page.locator('[data-step="1"]').click();
  await page.locator('#cwSavedSource').selectOption(floorIds[1]);
  await page.locator('#cwDeleteSource').click();await status(page,'سيُحذف الملف');
  await page.locator('#cwDeleteSource').click();await status(page,'حُذف الملف من المشروع');
  ok(!(await page.locator('#cwSavedSource option').allTextContents()).some(t=>t.includes('الصفحة 2 من 2')),'U12: the page is gone from the list');
  ok(errors.length===0,'no page errors: '+errors.join(' | '));
  await context.close();
}

(async()=>{
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'acs-upload-ui-'));
  inputs(tmp);
  const child=spawn(PY,['tests/remediation/connected_workspace_browser_server.py','--port',String(PORT),'--database',path.join(tmp,'plans.sqlite3')],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
  let log='';child.stdout.on('data',b=>log=(log+b).slice(-8000));child.stderr.on('data',b=>log=(log+b).slice(-8000));
  let browser;
  try{
    let ready=false;for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:'+PORT+'/health')).ok){ready=true;break;}}catch(e){}await delay(250);}
    assert.ok(ready,'fixture backend did not start: '+log);
    browser=await PW.launch();
    for(const width of [393,1280])await run(browser,tmp,width);
    console.log('plan upload browser: '+checks+' checks passed');
  }catch(e){console.error(e);console.error(log.slice(-3000));process.exitCode=1;}
  finally{await browser?.close();child.kill();fs.rmSync(tmp,{recursive:true,force:true});}
})();
