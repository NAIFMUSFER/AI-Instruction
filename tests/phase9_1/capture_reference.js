/* ============================================================================
   المرحلة 9.1 §25 — لقطات مرجعية قبل/بعد لثمانية مشاهد محدَّدة.

   هذا الملف يعمل على جهاز متّصل بالشبكة بعد تعبئة public/vendor
   (sh tools/vendor.sh) — أي بعد أن يوجد Three.js فعلاً. في صندوق بلا شبكة
   يتوقف مبكّراً بتصنيف صريح ولا يُنتج أي صورة مُفبركة:
       NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
   الصور — لا التوكيدات — هي دليل الجودة البصرية؛ لا شيء هنا يدّعي
   واقعية فوتوغرافية (§30).

   usage:  node tests/phase9_1/capture_reference.js
   output: tests/phase9_1/outputs/reference/{scene}_{before|after}.png + metadata
   ========================================================================== */
const fs=require('fs'), path=require('path'), http=require('http');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const PUB=path.join(ROOT,'public');
const OUT=path.join(HERE,'outputs','reference');
const CANON=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_pbr.json'),'utf8'));

/* المشاهد الثمانية: كل مشهد = إعداد كاميرا معلَن + إضاءة معلَنة + جودة معلَنة.
   كلها من acs_pbr.json — لا مشهد مخترَع خارج المواصفة. */
const SCENES=[
  {id:'exterior_hero',     camera:'EXTERIOR_HERO',      lighting:'CLEAR_NOON',       profile:'HIGH'},
  {id:'exterior_golden',   camera:'EXTERIOR_CORNER',    lighting:'GOLDEN_HOUR',      profile:'HIGH'},
  {id:'eye_level',         camera:'EYE_LEVEL',          lighting:'STUDIO_DAY',       profile:'HIGH'},
  {id:'aerial_overcast',   camera:'AERIAL',             lighting:'OVERCAST',         profile:'BALANCED'},
  {id:'interior_day',      camera:'INTERIOR_WIDE',      lighting:'INTERIOR_DAY',     profile:'HIGH'},
  {id:'interior_night',    camera:'INTERIOR_EYE_LEVEL', lighting:'INTERIOR_NIGHT',   profile:'HIGH'},
  {id:'warehouse',         camera:'WAREHOUSE_OVERVIEW', lighting:'WAREHOUSE',        profile:'BALANCED'},
  {id:'dollhouse',         camera:'DOLLHOUSE',          lighting:'PRESENTATION_SOFT',profile:'HIGH'},
];

/* ------------------------------------------------------------ preflight -- */
function preflight(){
  const missing=[];
  const three=path.join(PUB,'vendor','three@0.160.0','build','three.module.js');
  if(!fs.existsSync(three)||fs.statSync(three).size<100000)
    missing.push('vendor Three.js (run: sh tools/vendor.sh on a networked machine)');
  for(const m of CANON.post_processing_modules){
    const p=path.join(PUB,'vendor','three@0.160.0','examples','jsm',m);
    if(!fs.existsSync(p)||fs.statSync(p).size===0) missing.push('vendor '+m);
  }
  try{ require.resolve('playwright'); }
  catch(e){ missing.push('playwright (npm i playwright)'); }
  for(const s of SCENES){
    if(!(s.camera in CANON.camera_presets))
      missing.push('camera preset '+s.camera+' absent from acs_pbr.json');
    if(!(s.lighting in CANON.lighting_presets))
      missing.push('lighting preset '+s.lighting+' absent from acs_pbr.json');
  }
  return missing;
}

/* ------------------------------------------------- خادم ملفات ثابت محلي -- */
function serve(){
  const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript',
              '.css':'text/css','.json':'application/json','.png':'image/png',
              '.jpg':'image/jpeg','.svg':'image/svg+xml','.hdr':'application/octet-stream'};
  return new Promise(res=>{
    const srv=http.createServer((rq,rs)=>{
      const u=decodeURIComponent(rq.url.split('?')[0]);
      let p=path.normalize(path.join(PUB,u==='/'?'index.html':u));
      if(!p.startsWith(PUB)||!fs.existsSync(p)||fs.statSync(p).isDirectory()){
        rs.writeHead(404); rs.end('not found'); return; }
      rs.writeHead(200,{'Content-Type':MIME[path.extname(p)]||'application/octet-stream'});
      fs.createReadStream(p).pipe(rs);
    });
    srv.listen(0,'127.0.0.1',()=>res(srv));
  });
}

/* ----------------------------------------------------------------- main -- */
(async()=>{
  const missing=preflight();
  if(missing.length){
    console.log('§25 REFERENCE CAPTURE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
    missing.forEach(m=>console.log('  needs: '+m));
    console.log('no screenshot was produced and none is claimed. Run this file '
      +'on a networked machine after vendoring Three.js; the 8 before/after '
      +'pairs land in tests/phase9_1/outputs/reference/.');
    process.exit(2);   /* رمز مميّز: بيئة ناقصة، لا فشل اختبار ولا نجاح مزيَّف */
  }
  const {chromium}=require('playwright');
  fs.mkdirSync(OUT,{recursive:true});
  const srv=await serve();
  const base='http://127.0.0.1:'+srv.address().port;
  const b=await chromium.launch();
  const pg=await b.newPage({viewport:{width:1600,height:900},deviceScaleFactor:1});
  const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto(base+'/index.html',{waitUntil:'load'});
  await pg.waitForFunction(
    '!!(window.ACS&&window.ACS.pbrApply&&window.ACS.pbrCameraPreset)',
    null,{timeout:60000});
  /* استقرار حتمي: انتظار إطارين بعد كل تغيير بدل مهلة زمنية اعتباطية */
  const settle=()=>pg.evaluate(()=>new Promise(r=>
    requestAnimationFrame(()=>requestAnimationFrame(r))));
  const meta={generated_for:'phase 9.1 §25', viewport:'1600x900',
              note:'before = engineering default appearance; after = the same '
                  +'canonical geometry under the declared presentation config, '
                  +'same camera. Canonical-model BYTE immutability is proven by '
                  +'the phase 9.1 suites; this harness additionally asserts the '
                  +'canonical scene bounds are identical around every pair. '
                  +'No photorealism is claimed; these images are the visual '
                  +'evidence, the assertions are not.',
              scenes:[]};
  /* حدود المشهد القانوني (تستثني PQ_CONTEXT/VISUAL_ONLY) كشاهد على أن الطبقة
     لم تحرّك ولم تُغيّر حجم أي عنصر هندسي */
  const bounds=()=>pg.evaluate(
    'JSON.stringify(window.ACS.pbrBounds?window.ACS.pbrBounds():null)');
  for(const s of SCENES){
    const b0=await bounds();
    /* قبل: المظهر الهندسي الافتراضي بكاميرا المشهد نفسها — فرق الصورة يعود
       للطبقة العرضية وحدها لا لاختلاف زاوية النظر */
    await pg.evaluate(p=>{ window.ACS.pbrRestore&&window.ACS.pbrRestore();
                           window.ACS.pbrCameraPreset(p); },s.camera);
    await settle();
    await pg.screenshot({path:path.join(OUT,s.id+'_before.png')});
    const r=await pg.evaluate(sc=>{
      const cfg=window.ACS.pbr.config(sc.profile,sc.lighting,'REALISTIC','SKY',
        null,null,window.ACS.pbrCaps?window.ACS.pbrCaps():null,
        window.ACS.pbrBounds?window.ACS.pbrBounds():null);
      if(!cfg.valid) return {applied:false,issues:cfg.issues};
      const a=window.ACS.pbrApply(cfg.config);
      window.ACS.pbrCameraPreset(sc.camera);
      return {applied:!!(a&&a.applied!==false),
              hash:cfg.config.presentation_config_hash};
    },s);
    await settle();
    await pg.screenshot({path:path.join(OUT,s.id+'_after.png')});
    const b1=await bounds();
    meta.scenes.push({scene:s.id,camera:s.camera,lighting:s.lighting,
      profile:s.profile,applied:r.applied,
      presentation_config_hash:r.hash||null,
      canonical_bounds_before:JSON.parse(b0),
      canonical_bounds_after:JSON.parse(b1),
      canonical_bounds_unchanged:(b0===b1)});
    if(b0!==b1){
      console.log('  ✗ '+s.id+': canonical scene bounds moved — '
        +'IMMUTABILITY VIOLATION');
      process.exitCode=1;
    } else console.log('  ✓ '+s.id+' before/after captured, canonical bounds unchanged');
  }
  fs.writeFileSync(path.join(OUT,'reference_metadata.json'),
                   JSON.stringify(meta,null,1));
  console.log('\n8 scene pairs in tests/phase9_1/outputs/reference/'
    +(errs.length?'  page errors: '+errs.join(' | '):''));
  await b.close(); srv.close();
  if(errs.length) process.exitCode=1;
})();
