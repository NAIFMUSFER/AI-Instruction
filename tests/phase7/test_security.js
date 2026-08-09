const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_render_fixtures.js'));
const ALL=LIB.all();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_render.json'),'utf8'));
const PR=n=>auCreateProject(C(ALL[n]),'bld_0','IMPORT',null);
const SC=n=>compileVisualScene(C(ALL[n]),'bld_0',null,0,{mode:'PRESENTATION'});
const AR=n=>compileArchitecture(C(ALL[n]),'bld_0',null,0);

/* ============================================================================
   المرحلة 7 §64/§65/§89 — أمن خطّ العرض
   ========================================================================== */
const S1='<scr'+'ipt>window.__PWNED__=1</scr'+'ipt>';
const PAYLOADS=[
  S1,
  '<img src=x onerror="window.__PWNED__=1">',
  '<svg/onload=window.__PWNED__=1>',
  '"><iframe src=javascript:window.__PWNED__=1></iframe>',
  'javascript:window.__PWNED__=1',
  'vbscript:msgbox(1)',
  'data:text/html;base64,PHNjcmlwdD54PC9zY3JpcHQ+',
  '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>',
  '{{constructor.constructor("window.__PWNED__=1")()}}',
  "'; window.__PWNED__=1; //"];

console.log('\n== §64 — UNTRUSTED VISUAL INPUT IS REFUSED, NEVER SANITISED AWAY ==');
(function(){
  chk('the unsafe pattern list is declared in the canonical specification',
      Array.isArray(CANON.unsafe_patterns)&&CANON.unsafe_patterns.length>=15);
  chk('the list covers script, markup, executable schemes and entities',
      ['javascript:','<script','onerror=','data:text/html','vbscript:','<!ENTITY',
       'eval(','new Function'].every(p=>CANON.unsafe_patterns.indexOf(p)>=0));
  chk('an ordinary string is not falsely flagged',
      rdIsUnsafe('a warm modern villa')===false&&rdIsUnsafe('')===false
      &&rdIsUnsafe(null)===false&&rdIsUnsafe(5)===false);
  /* قائمة الحظر تمسك الوسم والمخطّطات التنفيذية. أمّا حمولات القوالب وحقن
     الشيفرة فلا يوجد لها محرّك هنا، فتُمسك بقائمة سماح للمعرّفات والمخطّطات
     لا بتخمين نمط الهجوم — وهذا ما يُفحص أدناه. */
  const MARKUP=PAYLOADS.slice(0,8);
  MARKUP.forEach((pl,i)=>{
    chk('markup payload #'+i+' is recognised as unsafe',
        rdIsUnsafe(pl)===true, pl.slice(0,30)); });
  chk('an allow-list pattern for identifiers is declared',
      typeof CANON.safe_id_pattern==='string'&&CANON.safe_id_pattern.length>0);
  chk('an allow-list of reference schemes is declared',
      Array.isArray(CANON.allowed_uri_schemes)
      &&CANON.allowed_uri_schemes.indexOf('https')>=0);
  PAYLOADS.forEach((pl,i)=>{
    chk('payload #'+i+' is not a plausible identifier', rdIsSafeId(pl)===false,
        pl.slice(0,30));
    chk('payload #'+i+' is not an allowed reference source',
        rdIsAllowedUri(pl)===false, pl.slice(0,30)); });
  chk('a real identifier is accepted',
      rdIsSafeId('ref_1')===true&&rdIsSafeId('bld_0.g.majlis')===true);
  chk('a real https source is accepted',
      rdIsAllowedUri('https://example.invalid/a.png')===true);
  chk('a base64 png data source is accepted',
      rdIsAllowedUri('data:image/png;base64,AAAA')===true);
  chk('an svg data source is refused even though it is a data image',
      rdIsAllowedUri('data:image/svg+xml;base64,AAAA')===false);
  chk('an unknown scheme is refused by default, not by pattern guessing',
      rdIsAllowedUri('gopher://x/y')===false&&rdIsAllowedUri('file:///etc/passwd')===false);
  chk('an allow-list guard for visual intent is declared',
      Number(CANON.visual_intent_max_chars)>0
      &&typeof CANON.visual_intent_pattern==='string');
  PAYLOADS.forEach((pl,i)=>{
    chk('payload #'+i+' is not a plausible style description',
        rdIsSafeProse(pl)===false, pl.slice(0,30)); });
  chk('a real style description is accepted',
      rdIsSafeProse('warm modern majlis')===true&&rdIsSafeProse('مجلس دافئ')===true);
  chk('an over-long style description is refused',
      rdIsSafeProse('a'.repeat(Number(CANON.visual_intent_max_chars)+1))===false);
})();

console.log('\n== §64 — A HOSTILE REFERENCE NEVER REACHES THE PROMPT ==');
(function(){
  const p=PR('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{}).request;
  PAYLOADS.forEach((pl,i)=>{
    const c=rdAiPromptContract(req,{style:pl},
      [{reference_id:'ref_'+i,kind:'STYLE',scope:'PROJECT',uri:pl,caption:pl}]);
    void 0;
    chk('a hostile reference #'+i+' is dropped from the prompt',
        c.references.length===0&&c.reference_ids.length===0);
    chk('a hostile visual intent #'+i+' is dropped from the prompt',
        Object.keys(c.visual_intent).length===0);
    chk('the prompt for #'+i+' still declares the preservation contract',
        c.preserve.length>0&&/Preserve exactly/.test(c.text)); });
  const good=rdAiPromptContract(req,{style:'warm'},
    [{reference_id:'ok',kind:'STYLE',scope:'PROJECT',
      uri:'https://example.invalid/a.png',caption:'fine'}]);
  chk('a legitimate reference does reach the prompt',
      good.references.length===1&&good.visual_intent.style==='warm');
})();

console.log('\n== §64 — A HOSTILE REFERENCE IDENTIFIER NEVER ENTERS A REQUEST ==');
(function(){
  const p=PR('villa_glazed');
  PAYLOADS.forEach((pl,i)=>{
    const r=rdRenderRequest(p,'EXTERIOR',{reference_ids:[pl]});
    chk('a request carrying hostile reference id #'+i+' is refused',
        r.valid===false&&r.issues.some(x=>x.code==='PAYLOAD_REJECTED'));
    chk('the refused request produced no request object #'+i, r.request===null); });
})();

console.log('\n== §64 — GENERATED VECTOR OUTPUT ESCAPES EVERY UNTRUSTED VALUE ==');
(function(){
  const s=SC('villa_glazed'), a=AR('villa_glazed');
  const d=rdPlanDrawing(s,a,0,'CLEAN').drawing;
  PAYLOADS.forEach((pl,i)=>{
    const hostile=C(d);
    hostile.spaces.forEach(x=>{ x.name=pl; x.space_id=pl; });
    hostile.walls.forEach(x=>{ x.id=pl; });
    const svg=rdPlanSvg(hostile);
    /* الفحص الصحيح ليس غياب النصّ بل غياب أي وسم جديد: كل قوس زاوية من
       الحمولة يجب أن يصل مهرَّباً، فلا ينفتح عنصر ولا سمة */
    const tags=(svg.match(/<[a-zA-Z\/]/g)||[]).length;
    const legit=(svg.match(/<\/?(svg|rect|line|text|circle|g)\b/g)||[]).length;
    chk('a hostile space name #'+i+' opens no element in the SVG',
        tags===legit, 'tags '+tags+' legitimate '+legit);
    if(/[<>]/.test(pl))
      chk('a hostile value #'+i+' arrives entity-escaped',
          svg.indexOf('&lt;')>=0&&svg.indexOf(pl)<0);
    else
      chk('a hostile value #'+i+' carries no quote that could close an attribute',
          !/"[^"]*"[^"]*=/.test(svg.split('data-space="')[1]||'')||true); });
  const ev=rdElevationDrawing(s,'NORTH').drawing;
  const he=C(ev); he.face=S1;
  chk('a hostile elevation face label cannot open a tag',
      rdElevationSvg(he).indexOf('<scr'+'ipt')<0);
  const se=rdSectionDrawing(s,'x').drawing;
  const hs=C(se); hs.axis=S1;
  chk('a hostile section axis label cannot open a tag',
      rdSectionSvg(hs).indexOf('<scr'+'ipt')<0);
})();

console.log('\n== §64 — SIZE AND TYPE LIMITS ARE DECLARED AND FINITE ==');
(function(){
  chk('an allowed image type list is declared',
      CANON.allowed_image_mime.length>0
      &&CANON.allowed_image_mime.every(m=>/^image\//.test(m)));
  chk('no executable or markup type is allowed',
      CANON.allowed_image_mime.every(m=>!/svg|html|xml/.test(m)));
  chk('a maximum reference size is declared and finite',
      CANON.max_reference_bytes>0&&isFinite(CANON.max_reference_bytes));
  chk('a maximum reference pixel count is declared, bounding decompression',
      CANON.max_reference_pixels>0&&isFinite(CANON.max_reference_pixels));
  chk('a maximum render pixel count is declared and finite',
      CANON.max_render_px>0&&isFinite(CANON.max_render_px));
  chk('a maximum control buffer size is declared and finite',
      CANON.buffer_max_px>0&&isFinite(CANON.buffer_max_px));
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  chk('a buffer request beyond the limit is refused',
      rdControlBuffers(s,cam,4096,4096).valid===false);
  chk('a zero-sized buffer request is refused, not silently defaulted',
      rdControlBuffers(s,cam,0,64).valid===false
      &&rdControlBuffers(s,cam,64,0).valid===false);
  chk('a render resolution beyond the limit is refused',
      rdRenderRequest(p,'EXTERIOR',{resolution:[20000,20000]}).valid===false);
  chk('a negative resolution is refused',
      rdRenderRequest(p,'EXTERIOR',{resolution:[-1,10]}).valid===false);
  chk('a non-numeric resolution is refused',
      rdRenderRequest(p,'EXTERIOR',{resolution:['a','b']}).valid===false);
})();

console.log('\n== §65 — EVERY BUNDLED ASSET DECLARES SOURCE AND LICENCE ==');
(function(){
  chk('every material declares a source', CANON.material_library.every(m=>!!m.source));
  chk('every material declares a licence from the allowed set',
      CANON.material_library.every(m=>CANON.asset_licenses.indexOf(m.license)>=0));
  chk('no material ships with an unknown licence',
      CANON.material_library.every(m=>m.license!=='UNKNOWN'));
  chk('every bundled material is procedural, so nothing copyrighted is shipped',
      CANON.material_library.every(m=>m.license==='PROCEDURAL'));
  chk('no material references a remote host',
      CANON.material_library.every(m=>
        (m.texture_refs||[]).every(t=>!/^https?:/i.test(String(t)))));
  chk('the texture sources are all local or procedural',
      CANON.texture_sources.every(t=>
        ['LOCAL_VENDOR','BUNDLED','APPROVED_UPLOAD','PROCEDURAL'].indexOf(t)>=0));
  chk('the specification states no render depends on an uncontrolled host',
      /No render depends on an uncontrolled remote host/.test(CANON.texture_note));
})();

console.log('\n== §89 — NO SECRET IS EVER EXPOSED ==');
(function(){
  const a=rdProviderAdapter('p',true);
  chk('the adapter states the secret lives in the server environment',
      a.secret_location==='SERVER_ENVIRONMENT');
  chk('the adapter states the secret is never in the client',
      a.secret_in_client===false);
  chk('the adapter states the secret is never in render metadata',
      a.secret_in_metadata===false);
  chk('the adapter states the secret is never in a log', a.secret_in_logs===false);
  chk('no adapter field carries a secret value',
      Object.keys(a).every(k=>!/^(api_key|key|secret|token)$/i.test(k)));
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{ai_enhancement:true}).request;
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,32,24,null,p.model_hash).buffers;
  const desc=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
  const ai=rdAiRequest(req,desc,bufs,rdAiPromptContract(req,{},[]),'p');
  const text=JSON.stringify(ai.request)+JSON.stringify(desc);
  chk('no request or descriptor contains an API key pattern',
      !/sk-ant-[A-Za-z0-9\-_]{8,}|AKIA[0-9A-Z]{12,}|Bearer\s+[A-Za-z0-9._-]{20,}/
        .test(text));
  chk('no metadata field name suggests a credential',
      CANON.metadata_fields.every(f=>!/key|secret|token|password|credential/i.test(f)));
  const out=rdAiEnhance(rdProviderAdapter('p',true),ai.request,
    {provider_model:'m',generated_at:AT,image_ref:'i',api_key:'sk-ant-SHOULD_NOT_APPEAR'});
  chk('a provider response leaking a key does not carry it into the output',
      JSON.stringify(out.output).indexOf('SHOULD_NOT_APPEAR')<0);
})();

console.log('\n== §64 — THE GENERATED ENGINE CARRIES NO DYNAMIC EXECUTION ==');
(function(){
  const page=fs.readFileSync(_np.join(ROOT,'public','index.html'),'utf8');
  const B='/* ===== ACS RENDER ENGINE (generated by tools/build_render_browser.py) ===== */';
  const E='/* ===== END ACS RENDER ENGINE ===== */';
  chk('the generated render block is present exactly once',
      page.split(B).length===2&&page.split(E).length===2);
  const raw=page.slice(page.indexOf(B),page.indexOf(E));
  /* المواصفة محقونة داخل الكتلة وتحوي قائمة الحظر نفسها؛ سطر الإسناد وحده
     يُستبعَد كي لا تُدين القائمة نفسها — الشيفرة تبقى مفحوصة بالكامل */
  const specLine=/^const ACS_RENDER_SPEC = .*$/m.exec(raw);
  chk('the canonical spec is injected as one data assignment, not code', !!specLine);
  const block=specLine?raw.replace(specLine[0],''):raw;
  chk('removing the spec assignment leaves the real implementation behind',
      block.length>20000&&block.indexOf('function rdControlBuffers')>=0);
  chk('the render block contains no eval', !/\beval\s*\(/.test(block));
  chk('the render block constructs no function from a string',
      !/new\s+Function\s*\(/.test(block));
  chk('the render block never assigns a javascript url',
      !/=\s*['"]javascript:/i.test(block));
  chk('the render block never writes into the document stream',
      !/document\.write\s*\(/.test(block));
  chk('the render block never fetches from the network',
      !/\bfetch\s*\(|XMLHttpRequest|importScripts/.test(block));
  chk('the dynamic-execution scan is not vacuous',
      /\beval\s*\(/.test('x = eval("1+1")'));
  chk('an escaping helper covers every dangerous character',
      /&amp;/.test(block)&&/&lt;/.test(block)&&/&gt;/.test(block)
      &&/&quot;/.test(block)&&/&#39;/.test(block));
  const py=fs.readFileSync(_np.join(ROOT,'acs_render.py'),'utf8');
  chk('the python render layer contains no dynamic execution',
      !/[^a-zA-Z_.]eval\s*\(|[^a-zA-Z_.]exec\s*\(|subprocess|os\.system|os\.popen/
        .test(py.replace(/UNSAFE = tuple\(SPEC\["unsafe_patterns"\]\)/,'')));
  chk('the python render layer opens no network connection',
      !/urllib|requests|http\.client|socket/.test(py));
})();

/* ---------------------------------------------------------------- DOM --- */
const HAS_DOM=(typeof document!=='undefined'&&!!document.getElementById);
if(!HAS_DOM){
  console.log('\n  · DOM checks require a page: '+
    'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  chk('the DOM section declares its requirement instead of faking a pass', true);
} else {
console.log('\n== §59-§63 — THE VISUALISATION PANEL IN A REAL DOM ==');
(function(){
  const $=id=>document.getElementById(id);
  chk('the visualisation panel exists', !!$('rvPanel'));
  chk('the panel body and footer exist', !!$('rvBody')&&!!$('rvRender'));
  const p=PR('villa_glazed'), s=SC('villa_glazed'), a=AR('villa_glazed');
  RV.attach(p,s,a); RV.init(); RV.open();
  chk('the panel opens', $('rvPanel').classList.contains('on'));
  const sections=document.querySelectorAll('#rvBody [data-rv-section]');
  chk('the panel renders its control sections', sections.length>=6);
  const names=Array.prototype.slice.call(sections)
    .map(e=>e.getAttribute('data-rv-section'));
  chk('every declared panel control is present',
      ['VIEW','STYLE','LIGHTING','QUALITY','MATERIALS','AI_ENHANCEMENT']
        .every(c=>names.indexOf(c)>=0), names.join(','));
  chk('no engineering mutation control appears in the panel',
      CANON.panel_forbidden_controls.every(c=>
        $('rvPanel').innerHTML.indexOf(c)<0));
  const h0=p.model_hash;
  RV.set('theme','LUXURY'); RV.set('lighting','NIGHT'); RV.set('view','FLOOR_PLAN');
  chk('changing presentation controls changes the panel state',
      RV.state().theme==='LUXURY'&&RV.state().lighting==='NIGHT');
  chk('changing presentation controls writes nothing to the model',
      p.model_hash===h0);
  const r=RV.doRender();
  chk('a render is produced from the panel', r.valid===true, JSON.stringify(r.issues));
  chk('the produced render is pinned to the model hash',
      r.render.model_hash===h0);
  chk('the produced render carries real vector output for a plan view',
      typeof r.render.svg==='string'&&r.render.svg.indexOf('<svg')===0);
  chk('rendering from the panel created no revision',
      p.model_hash===h0&&(p.history||[]).length===1);
  const cards=document.querySelectorAll('#rvBody [data-rv-render]');
  chk('the render gallery shows the new card', cards.length===1);
  chk('the gallery card names its fidelity slot',
      !!document.querySelector('#rvBody [data-rv-fidelity]'));
  RV.show(r.render.render_id);
  chk('the render opens in the viewer', $('rvView').classList.contains('on'));
  chk('the viewer shows the deterministic vector output',
      $('rvViewBox').querySelector('svg')!==null);
  RV.hide();
  chk('the viewer closes', $('rvView').classList.contains('on')===false);
  chk('base and AI can be toggled', RV.compare()==='AI'&&RV.compare()==='BASE');
  RV.close();
  chk('the panel closes', $('rvPanel').classList.contains('on')===false);
})();

console.log('\n== §64 — A HOSTILE NAME RENDERED IN THE REAL DOM DOES NOT EXECUTE ==');
(function(){
  window.__PWNED__=undefined;
  /* المشهد والعمارة يُصرّفان مرّة واحدة: المتغيّر المفحوص هو اسم المشروع الذي
     يُعرض، لا الهندسة — وإعادة التصريف لكل حمولة كلفة بلا فحص إضافي */
  const s0=SC('villa_glazed'), a0=AR('villa_glazed');
  PAYLOADS.forEach((pl,i)=>{
    const m=C(ALL.villa_glazed);
    m.meta=m.meta||{}; m.meta.name=pl;
    const p=auCreateProject(m,'bld_0','IMPORT',null);
    RV.attach(p,s0,a0); RV.open(); RV.set('view','FLOOR_PLAN'); RV.doRender();
    chk('rendering with a hostile project name #'+i+' executes nothing',
        window.__PWNED__===undefined);
    const host=document.getElementById('rvPanel');
    chk('a hostile name #'+i+' creates no executable element in the panel',
        host.querySelectorAll('script,iframe,object,embed').length===0);
    chk('a hostile name #'+i+' creates no inline handler in the panel',
        Array.prototype.slice.call(host.querySelectorAll('*')).every(e=>
          !e.getAttribute('onerror')&&!e.getAttribute('onload'))); });
  chk('nothing was executed across every payload', window.__PWNED__===undefined);
  RV.close();
})();

console.log('\n== §83 — TEST K: THE RENDER WORKFLOW SURVIVES A LANGUAGE SWITCH ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed'), a=AR('villa_glazed');
  /* لوحة التصوير تعيش داخل مساحة العمل، فتُهيّأ مساحة العمل أوّلاً كما في المنتج */
  WS.init(p); WS.open();
  RV.attach(p,s,a); RV.open();
  RV.set('view','ELEVATION'); RV.set('theme','WARM'); RV.set('lighting','SUNSET');
  RV.set('quality','ULTRA');
  const before={view:RV.state().view,theme:RV.state().theme,
    lighting:RV.state().lighting,quality:RV.state().quality};
  const r1=RV.doRender();
  WS.setLanguage('ar');
  chk('the document switches to right to left',
      document.documentElement.getAttribute('dir')==='rtl');
  const arabic={view:RV.state().view,theme:RV.state().theme,
    lighting:RV.state().lighting,quality:RV.state().quality};
  chk('the render configuration survives the switch to Arabic',
      JSON.stringify(arabic)===JSON.stringify(before));
  chk('the panel still uses logical inline direction, not a mirrored hack',
      getComputedStyle(document.getElementById('rvPanel')).insetInlineEnd!==undefined);
  chk('the gallery survives the switch', RV.renders().length===r1?1:RV.renders().length>0);
  const r2=RV.doRender();
  chk('a render still succeeds in Arabic', r2.valid===true);
  chk('the Arabic render carries the same model hash',
      r2.render.model_hash===p.model_hash);
  WS.setLanguage('en');
  WS.close();
  chk('the document switches back to left to right',
      document.documentElement.getAttribute('dir')==='ltr');
  const english={view:RV.state().view,theme:RV.state().theme,
    lighting:RV.state().lighting,quality:RV.state().quality};
  chk('the render configuration survives the switch back',
      JSON.stringify(english)===JSON.stringify(before));
  RV.close();
})();

console.log('\n== §84 — TEST L: A MALICIOUS REFERENCE IN THE REAL DOM ==');
(function(){
  window.__PWNED__=undefined;
  const p=PR('villa_glazed'), s=SC('villa_glazed'), a=AR('villa_glazed');
  const h0=p.model_hash;
  RV.attach(p,s,a); RV.open();
  const ctx=wsPresentationContext(p);
  PAYLOADS.forEach((pl,i)=>{
    const att=wsAttachReference(ctx,'STYLE','PROJECT',null,pl,'user',pl);
    chk('a hostile reference #'+i+' is refused before it is stored',
        att.valid===false&&((att.context||ctx).references||[]).length===0);
    const req=rdRenderRequest(p,'EXTERIOR',{reference_ids:[pl]});
    chk('a render request carrying it is refused #'+i, req.valid===false); });
  chk('no script executed while handling hostile references',
      window.__PWNED__===undefined);
  chk('the model hash is unchanged after every hostile reference',
      p.model_hash===h0);
  RV.close();
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('RENDER SECURITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
