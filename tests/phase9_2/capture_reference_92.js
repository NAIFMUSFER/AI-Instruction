/* ============================================================================
   المرحلة 9.2 §48 — لقطات مرجعية قبل/بعد للطبقة المعمارية.

   يعمل على جهاز متّصل بالشبكة بعد تعبئة public/vendor (sh tools/vendor.sh).
   في صندوق بلا Three.js يتوقف مبكّراً بتصنيف صريح ولا يُنتج صورة مُفبركة:
       NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
   «قبل» = وضع PBR للمرحلة 9.1 بنفس الكاميرا؛ «بعد» = الوضع المعماري الكامل.
   حدود المشهد القانوني تُقارَن حول كل زوج — أي حركة = خرق حصانة.

   usage:  node tests/phase9_2/capture_reference_92.js
   output: tests/phase9_2/outputs/reference/{scene}_{before|after}.png
   ========================================================================== */
const fs=require('fs'), path=require('path'), http=require('http');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const PUB=path.join(ROOT,'public');
const OUT=path.join(HERE,'outputs','reference');
const CANON=JSON.parse(fs.readFileSync(
  path.join(ROOT,'acs_archdetail.json'),'utf8'));
const PQ=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_pbr.json'),'utf8'));
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js):
   النداء المباشر chromium.launch() يطلب البناء الذي تتوقّعه نسخة
   Playwright بالرقم، فينجح حيث جرى `playwright install` ويفشل حيث
   تحمل الصورة بناءً آخر. المُحدِّد يجيب السؤال مرّة واحدة لكل بيئة. */
const PW=require(path.join(ROOT,'tools','pw_chromium.js'));

/* §48: المشاهد المطلوبة — النموذج يبدّله المشغّل في الواجهة قبل كل زوج؛
   هذا الملف يضبط الكاميرا والإضاءة والتفصيل ويلتقط الزوج باسم المشهد. */
const SCENES=[
  {id:'villa',     camera:'EXTERIOR_HERO_CORNER', lighting:'CLEAR_NOON',
   env:'CLEAR_SKY', detail:'DETAIL_HIGH', context:'SITE'},
  {id:'apartment', camera:'EXTERIOR_HERO_FRONT',  lighting:'GOLDEN_HOUR',
   env:'SUNSET_SKY', detail:'DETAIL_HIGH', context:'SITE'},
  {id:'warehouse', camera:'WAREHOUSE_OVERVIEW_92',lighting:'WAREHOUSE',
   env:'NEUTRAL_STUDIO', detail:'DETAIL_STANDARD', context:'NEUTRAL'},
  {id:'hotel',     camera:'EXTERIOR_HERO_CORNER', lighting:'GOLDEN_HOUR',
   env:'CLEAR_SKY', detail:'DETAIL_HIGH', context:'LANDSCAPE'},
  {id:'clinic',    camera:'EXTERIOR_HERO_FRONT',  lighting:'STUDIO_DAY',
   env:'NEUTRAL_STUDIO', detail:'DETAIL_STANDARD', context:'NEUTRAL'},
  {id:'interior',  camera:'INTERIOR_LIVING',      lighting:'INTERIOR_DAY',
   env:'NEUTRAL_STUDIO', detail:'DETAIL_HIGH', context:'NONE'},
  {id:'dollhouse', camera:'DOLLHOUSE_HERO',       lighting:'PRESENTATION_SOFT',
   env:'NEUTRAL_STUDIO', detail:'DETAIL_STANDARD', context:'NONE'},
];

function preflight(){
  const missing=[];
  const three=path.join(PUB,'vendor','three@0.160.0','build',
    'three.module.js');
  if(!fs.existsSync(three)||fs.statSync(three).size<100000)
    missing.push('vendor Three.js (run: sh tools/vendor.sh on a networked '
      +'machine)');
  try{ require.resolve('playwright'); }
  catch(e){ missing.push('playwright (npm i playwright)'); }
  SCENES.forEach(s=>{
    if(!(s.camera in CANON.camera_presets_arch)
       &&!(s.camera in PQ.camera_presets))
      missing.push('camera preset '+s.camera+' not declared');
    if(!(s.lighting in PQ.lighting_presets))
      missing.push('lighting preset '+s.lighting+' not declared');
    if(!(s.env in CANON.environment_presets))
      missing.push('environment preset '+s.env+' not declared'); });
  return missing;
}

function serve(){
  const MIME={'.html':'text/html','.js':'text/javascript',
    '.mjs':'text/javascript','.css':'text/css','.json':'application/json',
    '.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
  return new Promise(res=>{
    const srv=http.createServer((rq,rs)=>{
      const u=decodeURIComponent(rq.url.split('?')[0]);
      let p=path.normalize(path.join(PUB,u==='/'?'index.html':u));
      if(!p.startsWith(PUB)||!fs.existsSync(p)
         ||fs.statSync(p).isDirectory()){
        rs.writeHead(404); rs.end('not found'); return; }
      rs.writeHead(200,{'Content-Type':
        MIME[path.extname(p)]||'application/octet-stream'});
      fs.createReadStream(p).pipe(rs); });
    srv.listen(0,'127.0.0.1',()=>res(srv)); });
}

(async()=>{
  const missing=preflight();
  if(missing.length){
    console.log('§48 REFERENCE CAPTURE: NOT VERIFIED — EXTERNAL '
      +'ENVIRONMENT REQUIRED');
    missing.forEach(m=>console.log('  needs: '+m));
    console.log('no screenshot was produced and none is claimed. Run this '
      +'file on a networked machine after vendoring Three.js; the pairs '
      +'land in tests/phase9_2/outputs/reference/.');
    process.exit(2);
  }
  require('playwright');
  fs.mkdirSync(OUT,{recursive:true});
  const srv=await serve();
  const base='http://127.0.0.1:'+srv.address().port;
  const b=await PW.launch();
  const pg=await b.newPage({viewport:{width:1600,height:900},
    deviceScaleFactor:1});
  const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto(base+'/index.html',{waitUntil:'load'});
  await pg.waitForFunction(
    '!!(window.ACS&&window.ACS.adApply&&window.ACS.pbrApply'
    +'&&window.ACS.pbrCameraPreset)',null,{timeout:60000});
  const settle=()=>pg.evaluate(()=>new Promise(r=>
    requestAnimationFrame(()=>requestAnimationFrame(r))));
  const bounds=()=>pg.evaluate(
    'JSON.stringify(window.ACS.pbrBounds?window.ACS.pbrBounds():null)');
  const meta={generated_for:'phase 9.2 §48',viewport:'1600x900',
    note:'before = the Phase 9.1 PBR presentation; after = the same '
      +'canonical geometry with the architectural detail layer, same '
      +'camera. Canonical byte-immutability is proven by the suites; '
      +'this harness additionally asserts the canonical scene bounds are '
      +'identical around every pair. No photorealism is claimed.',
    scenes:[]};
  for(const s of SCENES){
    const b0=await bounds();
    await pg.evaluate(sc=>{
      window.ACS.adMode('PBR');
      const pq=window.ACS.pbr.config('HIGH',sc.lighting,'REALISTIC','SKY',
        null,null,window.ACS.pbrCaps(),window.ACS.pbrBounds());
      if(pq.valid) window.ACS.pbrApply(pq.config);
      const cam=window.ACS.archdetail.camera(sc.camera,
        window.ACS.pbrBounds());
      window.ACS.pbrCameraPreset&&cam.valid
        &&window.ACS.pbrCameraPreset(sc.camera in
          window.ACS.pbr.spec().camera_presets?sc.camera:null);
    },s);
    await settle();
    await pg.screenshot({path:path.join(OUT,s.id+'_before.png')});
    const r=await pg.evaluate(sc=>{
      const cfg=window.ACS.archdetail.config(sc.detail,'REQUESTED',
        sc.context,'STAGING_REQUESTED_ONLY',sc.camera,sc.env,null,false,
        window.ACS.archdetail.interpret(
          'واجهة حجر طبيعي بيج مع زجاج عاكس وإنارة LED مخفية').intents,
        window.ACS.adModelSummary());
      if(!cfg.valid) return {applied:false,issues:cfg.issues};
      const a=window.ACS.adApply(cfg.config);
      return {applied:!!(a&&a.applied!==false),
        hash:cfg.config.presentation_config_hash,added:a&&a.added};
    },s);
    await settle();
    await pg.screenshot({path:path.join(OUT,s.id+'_after.png')});
    const b1=await bounds();
    meta.scenes.push({scene:s.id,camera:s.camera,lighting:s.lighting,
      environment:s.env,detail:s.detail,context:s.context,
      applied:r.applied,presentation_config_hash:r.hash||null,
      added:r.added||null,canonical_bounds_unchanged:(b0===b1)});
    if(b0!==b1){
      console.log('  ✗ '+s.id+': canonical scene bounds moved — '
        +'IMMUTABILITY VIOLATION');
      process.exitCode=1;
    } else console.log('  ✓ '+s.id
      +' before/after captured, canonical bounds unchanged');
  }
  fs.writeFileSync(path.join(OUT,'reference_metadata_92.json'),
    JSON.stringify(meta,null,1));
  console.log('\npairs in tests/phase9_2/outputs/reference/'
    +(errs.length?'  page errors: '+errs.join(' | '):''));
  await b.close(); srv.close();
  if(errs.length) process.exitCode=1;
})();
