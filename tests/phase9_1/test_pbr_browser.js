/* ============================================================================
   المرحلة 9.1 §19/§24 — لوحة الجودة البصرية في متصفّح حقيقي
   ما يحتاج WebGL + Three.js لا يُنمذَج: غيابه هنا يُثبت مساراً رشيقاً مصنَّفاً،
   والعرض الفعلي يُتحقّق منه على النشر الحقيقي لا في هذا الصندوق.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_pbr.json'),'utf8'));
const LIBD=require(_np.join(ROOT,'tests','phase9','lib_docs_fixtures.js'));
const ALL=LIBD.all();
const C=o=>JSON.parse(JSON.stringify(o));

console.log('\n== §1 — THE SPECIFICATION REACHED THE BROWSER UNCHANGED ==');
(function(){
  chk('the browser carries the canonical quality specification',
      typeof ACS_PBR_SPEC==='object'&&ACS_PBR_SPEC.schema===CANON.schema);
  chk('the mirrored specification has not drifted from the file',
      JSON.stringify(ACS_PBR_SPEC)===JSON.stringify(CANON));
  chk('the presentation-only rule is present in the browser',
      ACS_PBR_SPEC.presentation_only===true
      &&ACS_PBR_SPEC.writes_to_model===false);
  const HAS_WIN=(typeof window!=='undefined');
  chk('the quality API is exposed on the window',
      !HAS_WIN||(window.ACS&&window.ACS.pbr&&!!window.ACS.pbr.panel));
})();

const HAS_DOM=(typeof document!=='undefined'&&!!document.getElementById);
if(!HAS_DOM){
  console.log('\n(DOM checks require a real browser — run with run_browser.js)');
} else {

console.log('\n== §19 — THE SETTINGS PANEL ==');
(function(){
  const $=id=>document.getElementById(id);
  chk('the panel exists in the shipped page',
      !!$('pqPanel')&&$('pqPanel').getAttribute('data-pq')==='panel');
  PQ.init(); PQ.open();
  chk('the panel opens', $('pqPanel').classList.contains('on'));
  ['pqQuality','pqLighting','pqMaterials','pqEnvironment','pqShadows',
   'pqAo','pqExposure'].forEach(id=>{
    chk('control '+id+' is rendered', !!$(id)); });
  chk('the quality select offers the four declared profiles',
      $('pqQuality').options.length===4);
  chk('the lighting select offers the eight declared presets',
      $('pqLighting').options.length===8);
  chk('the materials select offers engineering and realistic only',
      $('pqMaterials').options.length===2);
  chk('the exposure range is clamped to the declared bounds',
      $('pqExposure').min===String(CANON.exposure_min)
      &&$('pqExposure').max===String(CANON.exposure_max));
  chk('no raw developer parameter is exposed outside the declared controls',
      CANON.panel_forbidden_controls.every(c=>
        document.querySelectorAll('#pqPanel [data-pq-action="'+c+'"]').length===0));
  chk('the panel states the model is read-only here',
      $('pqBody').textContent.indexOf('read-only')>=0);
})();

console.log('\n== §18 — GRACEFUL PATH WHERE THE 3D RUNTIME IS ABSENT ==');
(function(){
  window.__PQ_MODEL__=auCreateProject(C(ALL.villa_glazed),'bld_0','IMPORT',null);
  const h0=window.__PQ_MODEL__.model_hash;
  document.getElementById('pqMaterials').value='REALISTIC';
  document.getElementById('pqMaterials').onchange();
  document.getElementById('pqQuality').value='ULTRA';
  document.getElementById('pqQuality').onchange();
  const r=PQ.apply();
  chk('apply without THREE returns a typed refusal, not a crash',
      r&&r.applied===false
      &&r.issues.some(i=>i.code==='PQ_THREE_UNAVAILABLE'),
      JSON.stringify((r.issues||[]).map(i=>i.code)));
  chk('the produced configuration itself is valid and complete',
      r.config&&r.config.presentation_config_hash
      &&r.config.materials_mode==='REALISTIC'
      &&r.config.writes_to_model===false);
  chk('the status line reports honestly in the panel',
      document.querySelector('#pqBody [data-pq-status="NOT_APPLIED"]')!==null);
  const cap=PQ.capture();
  chk('capture without THREE refuses gracefully too',
      cap&&cap.captured===false
      &&cap.issues.some(i=>i.code==='PQ_THREE_UNAVAILABLE'));
  chk('no blank-viewport failure mode: the page is still alive',
      document.getElementById('pqPanel').classList.contains('on'));
  chk('the canonical model hash never moved',
      window.__PQ_MODEL__.model_hash===h0);
})();

console.log('\n== §21 — IMMUTABILITY THROUGH THE UI ==');
(function(){
  const prj=auCreateProject(C(ALL.warehouse),'bld_0','IMPORT',null);
  const before=ingestCanonicalJson(prj.model);
  const h0=prj.model_hash;
  ['PERFORMANCE','BALANCED','HIGH','ULTRA'].forEach(q=>{
    document.getElementById('pqQuality').value=q;
    document.getElementById('pqQuality').onchange();
    Object.keys(ACS_PBR_SPEC.lighting_presets).forEach(l=>{
      document.getElementById('pqLighting').value=l;
      document.getElementById('pqLighting').onchange();
      PQ.apply(); }); });
  PQ.capture();
  chk('canonical model bytes identical after every panel operation',
      ingestCanonicalJson(prj.model)===before);
  chk('the model hash is unchanged', prj.model_hash===h0);
  const src=dcSources(prj);
  chk('warehouse object counts are untouched by the visual layer',
      src.arch.walls.length>0&&src.arch.spaces.length===4);
})();

console.log('\n== §19 — ARABIC AND ENGLISH ==');
(function(){
  PQ.setLanguage('ar');
  chk('the panel title is Arabic',
      document.getElementById('pqTitle').textContent
        ===ACS_PBR_SPEC.ui_labels.ar.panel);
  chk('the quality options are localised',
      document.getElementById('pqQuality').options[0].textContent
        ===ACS_PBR_SPEC.ui_labels.ar.performance);
  const st=PQ.state();
  PQ.setLanguage('en');
  chk('the panel title returns to English',
      document.getElementById('pqTitle').textContent
        ===ACS_PBR_SPEC.ui_labels.en.panel);
  chk('the selection state survives the language round trip',
      PQ.state().profile===st.profile&&PQ.state().lighting===st.lighting);
})();

console.log('\n== §11/§22 — THE SHIPPED PAGE ITSELF ==');
(function(){
  const page=fs.readFileSync(_np.join(ROOT,'public','index.html'),'utf8');
  chk('the module-scope bridge is present exactly once',
      page.split('/* ===== ACS PBR BRIDGE (module scope) ===== */').length===2);
  chk('the render loop dispatcher is present exactly once with a fallback',
      page.split('window.__ACS_PQ__&&window.__ACS_PQ__.composer').length===2
      &&page.indexOf('else{renderer.render(scene,camera);}')>=0);
  chk('post-processing imports are same-origin addon modules only',
      page.indexOf("import('three/addons/postprocessing/EffectComposer.js')")>=0
      &&page.indexOf("import('http")<0&&page.indexOf('import("http')<0);
  chk('the bridge marks every added object visual-only',
      page.indexOf("name='PQ_CONTEXT'")>=0&&page.indexOf("name='PQ_FILL'")>=0);
  /* §22 — العبرة بجُمل التحميل الفعلية لا بذكر السياسة نثراً: تُستخرج كتلتا
     الجودة والجسر وتُفحصان على أي مخطط شبكة أو مضيف CDN حقيقي داخلهما. */
  const _qb='/* ===== ACS PBR QUALITY (generated by tools/build_pbr_browser.py) ===== */';
  const _qe='/* ===== END ACS PBR QUALITY ===== */';
  const _bb='/* ===== ACS PBR BRIDGE (module scope) ===== */';
  const _be='/* ===== END ACS PBR BRIDGE ===== */';
  const qlayer=page.slice(page.indexOf(_qb),page.indexOf(_qe))
              +page.slice(page.indexOf(_bb),page.indexOf(_be));
  chk('the quality layer was extracted for inspection', qlayer.length>10000);
  chk('no network scheme appears anywhere in the quality layer',
      qlayer.indexOf('http://')<0&&qlayer.indexOf('https://')<0
      &&qlayer.indexOf('//cdn')<0,
      'schemes');
  chk('no runtime CDN host appears in the quality layer',
      ['cdn.jsdelivr','unpkg.com','cdnjs.cloudflare','polyhaven.com',
       'rgbeloader','xmlhttprequest']
        .every(h=>qlayer.toLowerCase().indexOf(h)<0),
      'checked hosts');
  chk('the quality layer never opens a fetch to a remote URL',
      qlayer.indexOf("fetch('http")<0&&qlayer.indexOf('fetch("http')<0
      &&qlayer.indexOf("import('http")<0&&qlayer.indexOf('import("http')<0);
  /* وجود ملفَي README على القرص يتحقّق منه verify_deploy.py في بيئة Node
     الحقيقية؛ هنا داخل المتصفّح يُثبَت جوهر السياسة نفسها من المواصفة المشحونة. */
  chk('the shipped texture policy is local-only with an empty default set',
      ACS_PBR_SPEC.texture_policy.local_only===true
      &&ACS_PBR_SPEC.texture_policy.remote_texture_allowed===false
      &&ACS_PBR_SPEC.texture_policy.allowed_schemes.length===0
      &&ACS_PBR_SPEC.texture_policy.local_texture_sets.length===0);
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('PBR BROWSER: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
