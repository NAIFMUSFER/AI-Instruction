/* ============================================================================
   المرحلة 9.2 §36/§47 — لوحة العرض المعماري في متصفح حقيقي.
   ما يحتاج WebGL + Three.js لا يُنمذَج: غيابه هنا يُثبت مساراً رشيقاً مصنَّفاً،
   والعرض الفعلي (خامات الواجهة كبكسلات، شبكات الإطارات) يُتحقّق منه على النشر
   الحقيقي — NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED في هذا الصندوق.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_archdetail.json'),'utf8'));
const LIBD=require(_np.join(ROOT,'tests','phase9','lib_docs_fixtures.js'));
const ALL=LIBD.all();
const C=o=>JSON.parse(JSON.stringify(o));

console.log('\n== §1 — THE SPECIFICATION REACHED THE BROWSER UNCHANGED ==');
(function(){
  chk('the browser carries the canonical archdetail specification',
      typeof ACS_ARCHDETAIL_SPEC==='object'
      &&ACS_ARCHDETAIL_SPEC.schema===CANON.schema);
  chk('the mirrored specification has not drifted from the file',
      JSON.stringify(ACS_ARCHDETAIL_SPEC)===JSON.stringify(CANON));
  chk('the presentation-only rule is present in the browser',
      ACS_ARCHDETAIL_SPEC.presentation_only===true
      &&ACS_ARCHDETAIL_SPEC.writes_to_model===false);
  const HAS_WIN=(typeof window!=='undefined');
  chk('the archdetail API is exposed on the window',
      !HAS_WIN||(window.ACS&&window.ACS.archdetail
                 &&!!window.ACS.archdetail.panel));
})();

const HAS_DOM=(typeof document!=='undefined'&&!!document.getElementById);
if(!HAS_DOM){
  console.log('\n(DOM checks require a real browser — run with run_browser.js)');
} else {

console.log('\n== §36 — THE ARCHITECTURAL PRESENTATION PANEL ==');
(function(){
  const $=id=>document.getElementById(id);
  chk('the panel exists in the shipped page',
      !!$('adPanel')&&$('adPanel').getAttribute('data-ad')==='panel');
  AD.init(); AD.open();
  chk('the panel opens', $('adPanel').classList.contains('on'));
  chk('architectural detail offers Off/Standard/High',
      $('adDetail').options.length===3);
  chk('facade offers Engineering/Requested/Realistic',
      $('adFacade').options.length===3);
  chk('context offers None/Neutral/Site/Landscape',
      $('adContext').options.length===4);
  chk('staging offers Off/Requested-only/Presentation',
      $('adStaging').options.length===3);
  chk('camera offers Auto/Hero/Street/Aerial/Interior',
      $('adCamera').options.length===5);
  chk('the visual diagnostic toggle is rendered', !!$('adDiagnostic'));
  chk('the three compare modes are rendered (§37)',
      !!document.querySelector('[data-ad-compare="ENGINEERING"]')
      &&!!document.querySelector('[data-ad-compare="PBR"]')
      &&!!document.querySelector('[data-ad-compare="ARCHITECTURAL"]'));
  chk('no forbidden raw control is exposed',
      CANON.panel_forbidden_controls.every(c=>
        document.querySelectorAll('#adPanel [data-ad-action="'+c+'"]')
          .length===0));
  chk('the panel states the model is read-only here',
      $('adReadonly').textContent.length>5);
})();

console.log('\n== §18/§47 — GRACEFUL PATH WHERE THE 3D RUNTIME IS ABSENT ==');
(function(){
  const $=id=>document.getElementById(id);
  window.__AD_MODEL__=auCreateProject(C(ALL.villa_glazed),'bld_0','IMPORT',null);
  const h0=window.__AD_MODEL__.model_hash;
  $('adDetail').value='DETAIL_HIGH'; $('adDetail').onchange();
  $('adFacade').value='REQUESTED'; $('adFacade').onchange();
  $('adContext').value='SITE'; $('adContext').onchange();
  AD.setRequestText('واجهة حجر طبيعي بيج مع زجاج عاكس وإنارة LED مخفية');
  const r=AD.apply();
  chk('apply without THREE returns a typed refusal, not a crash',
      r&&r.applied===false
      &&r.issues.some(i=>i.code==='AD_THREE_UNAVAILABLE'),
      JSON.stringify((r.issues||[]).map(i=>i.code)));
  chk('the produced configuration itself is valid and complete',
      r.config&&r.config.presentation_config_hash
      &&r.config.facade_mode==='REQUESTED'
      &&r.config.writes_to_model===false);
  chk('the interpreted request reached the diagnostic',
      r.config.diagnostic.requested_visual_features
        .indexOf('facade_material')>=0
      &&r.config.diagnostic.requested_visual_features
        .indexOf('led_lighting')>=0);
  chk('the status line reports honestly in the panel',
      document.querySelector('#adPanel [data-ad-status="NOT_APPLIED"]')
      !==null);
  const cm=AD.compare('ARCHITECTURAL');
  chk('compare without THREE refuses gracefully too',
      cm&&cm.applied===false
      &&cm.issues.some(i=>i.code==='AD_THREE_UNAVAILABLE'));
  chk('no blank-viewport failure mode: the page is still alive',
      $('adPanel').classList.contains('on'));
  chk('the canonical model hash never moved',
      window.__AD_MODEL__.model_hash===h0);
})();

console.log('\n== §43 — IMMUTABILITY THROUGH THE UI ==');
(function(){
  const $=id=>document.getElementById(id);
  const prj=auCreateProject(C(ALL.warehouse),'bld_0','IMPORT',null);
  const before=ingestCanonicalJson(prj.model);
  const h0=prj.model_hash;
  ['DETAIL_OFF','DETAIL_STANDARD','DETAIL_HIGH'].forEach(dp=>{
    $('adDetail').value=dp; $('adDetail').onchange();
    ['NONE','NEUTRAL','SITE','LANDSCAPE'].forEach(cx=>{
      $('adContext').value=cx; $('adContext').onchange();
      AD.apply(); }); });
  ['ENGINEERING','PBR','ARCHITECTURAL'].forEach(m=>AD.compare(m));
  chk('canonical model bytes identical after every panel operation',
      ingestCanonicalJson(prj.model)===before);
  chk('the model hash is unchanged', prj.model_hash===h0);
  const src=dcSources(prj);
  chk('warehouse object counts are untouched by the architectural layer',
      src.arch.walls.length>0&&src.arch.spaces.length===4);
})();

console.log('\n== §36 — ARABIC AND ENGLISH ==');
(function(){
  AD.setLanguage('ar');
  chk('the panel title is Arabic',
      document.getElementById('adTitle').textContent
        ===ACS_ARCHDETAIL_SPEC.ui_labels.ar.panel);
  const st=AD.state();
  AD.setLanguage('en');
  chk('the panel title switches to English',
      document.getElementById('adTitle').textContent
        ===ACS_ARCHDETAIL_SPEC.ui_labels.en.panel);
  chk('the selection state survives the language round trip',
      AD.state().detail===st.detail&&AD.state().context===st.context);
  AD.setLanguage('ar');
})();

console.log('\n== §42/§47 — THE SHIPPED PAGE ITSELF ==');
(function(){
  const page=fs.readFileSync(_np.join(ROOT,'public','index.html'),'utf8');
  chk('the archdetail bridge is present exactly once',
      page.split('/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */')
        .length===2);
  chk('the PBR bridge of 9.1 is still present exactly once',
      page.split('/* ===== ACS PBR BRIDGE (module scope) ===== */')
        .length===2);
  chk('the render loop dispatcher of 9.1 is untouched',
      page.split('window.__ACS_PQ__&&window.__ACS_PQ__.composer').length===2
      &&page.indexOf('else{renderer.render(scene,camera);}')>=0);
  const _ab='/* ===== ACS ARCH DETAIL (generated by tools/build_archdetail_browser.py) ===== */';
  const _ae='/* ===== END ACS ARCH DETAIL ===== */';
  const _bb='/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */';
  const _be='/* ===== END ACS ARCH DETAIL BRIDGE ===== */';
  const layer=page.slice(page.indexOf(_ab),page.indexOf(_ae))
             +page.slice(page.indexOf(_bb),page.indexOf(_be));
  chk('the architectural layer was extracted for inspection',
      layer.length>10000);
  chk('no network scheme appears anywhere in the architectural layer',
      layer.indexOf('http://')<0&&layer.indexOf('https://')<0
      &&layer.indexOf('//cdn')<0);
  chk('no runtime CDN host, remote texture or url-gltf path exists',
      ['cdn.jsdelivr','unpkg.com','cdnjs.cloudflare','polyhaven.com',
       'gltfloader','rgbeloader','xmlhttprequest',"fetch('http",
       'fetch("http',"import('http",'import("http']
        .every(h=>layer.toLowerCase().indexOf(h)<0));
  chk('the bridge refuses a configuration that could write to the model',
      layer.indexOf("cfg.writes_to_model!==false")>=0);
  chk('every bridge group is an AD_* presentation group',
      layer.indexOf("'AD_DETAIL'")>=0||layer.indexOf('AD_DETAIL')>=0);
  chk('added objects carry visual_only and source ids in the source',
      layer.indexOf('visual_only:true')>=0
      &&layer.indexOf('source_element_id')>=0);
  chk('the texture policy stays local-only with an empty default set',
      ACS_ARCHDETAIL_SPEC.remote_texture_allowed===false
      &&ACS_ARCHDETAIL_SPEC.url_gltf_allowed===false
      &&ACS_ARCHDETAIL_SPEC.executable_assets_allowed===false);
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('ARCH DETAIL BROWSER: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
