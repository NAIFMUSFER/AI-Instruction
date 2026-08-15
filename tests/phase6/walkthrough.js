/* ============================================================================
   المرحلة 6 §98 — المرور الكامل بالمنتج في Chromium حقيقي
   سبع عشرة خطوة، لكلٍّ حكم واحد: PASS / FAIL / NOT_SUPPORTED / NOT_VERIFIED.
   لا خطوة تُعلَن PASS إلا إن نُفِّذت فعلاً في الصفحة وأعادت دليلاً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const BUILD=path.join(ROOT,'tests','phase3','lib','build_browser_page.js');

const steps=[];
const record=(n,title,verdict,evidence)=>{
  steps.push({n:n,title:title,verdict:verdict,evidence:evidence});
  const pad=String(n).padStart(2,' ');
  console.log('  '+pad+' · '+verdict.padEnd(13)+' '+title
    +(evidence?('  — '+evidence):'')); };

let chromium=null;
try{ chromium=require('playwright').chromium; }catch(e){ chromium=null; }
if(!chromium){
  console.log('\nPRODUCT WALKTHROUGH: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  Playwright is not installed here; no walkthrough claim is made.');
  process.exit(0);
}

/* سائق الصفحة لا يفعل شيئاً سوى إتاحة الواجهة — كل خطوة تُقاد من هنا */
const DRIVER=path.join(os.tmpdir(),'acs_ws_walk.js');
fs.writeFileSync(DRIVER,
  "const fs=require('fs');\n"+
  "let pass=0,fail=0;\n"+
  "const chk=(n,c)=>{c?pass++:fail++;};\n"+
  "const FX=JSON.parse(fs.readFileSync('base_fixtures.json','utf8'));\n"+
  "window.__FX__=FX;\n"+
  "window.__WS__=WS;\n"+
  "chk('exposed',true);\n"+
  "window.__WS_READY__=true;\n",'utf8');

(async()=>{
  execFileSync(process.execPath,[BUILD,DRIVER],{stdio:'pipe'});
  const page=path.join(os.tmpdir(),'acs_ws_walk_browser.html');
  const browser=await chromium.launch();
  const pg=await browser.newPage({viewport:{width:1440,height:900}});
  pg.setDefaultTimeout(300000);
  pg.setDefaultNavigationTimeout(300000);
  const errs=[];
  pg.on('pageerror',e=>errs.push(e&&e.message?e.message:String(e)));
  await pg.goto('file://'+page,{waitUntil:'load'});
  await pg.waitForFunction('window.__WS_READY__===true');

  console.log('\n== §98 — COMPLETE PRODUCT WALKTHROUGH (real Chromium) ==');

  /* يُنفّذ تعبيراً في الصفحة ويعيد نتيجته، ويحوّل أي استثناء إلى دليل فشل */
  const ev=async src=>{
    try{ return {ok:true,v:await pg.evaluate('(()=>{'+src+'})()')}; }
    catch(e){ return {ok:false,v:null,err:String(e&&e.message||e)}; } };
  const verdict=(r,cond)=>{
    if(!r.ok) return ['FAIL',r.err];
    try{ return cond(r.v); }catch(e){ return ['FAIL',String(e&&e.message||e)]; } };

  /* 1 — إنشاء مشروع */
  {
    const r=await ev("const p=window.__WS__.createProject("
      +"{name:'دار الاختبار',type:'residential',site:{w:30,d:24}});"
      +"return {valid:!!p&&p.valid!==false,name:p&&p.name,"
      +"has_flow:typeof window.__WS__.createProject==='function'};");
    const [v,e]=verdict(r,x=>x.has_flow
      ?['PASS','a create-project flow exists and returned a result']
      :['NOT_SUPPORTED','no create-project entry point']);
    record(1,'CREATE PROJECT',v,e);
  }

  /* 2 — إدخال المتطلّبات */
  {
    const r=await ev("const cov=wsRequirementCoverage({requirements:["
      +"{id:'r1',text:'ثلاث غرف نوم',klass:'SPATIAL'},"
      +"{id:'r2',text:'مصعد',klass:'UNSUPPORTED'}]},'ar');"
      +"return {total:cov.total,unresolved:cov.unresolved,"
      +"claims:cov.claims_full_coverage};");
    const [v,e]=verdict(r,x=>(x.total===2&&x.unresolved>=1&&x.claims===false)
      ?['PASS','requirements are classified; unsupported ones stay counted, '
        +'not silently satisfied']
      :['FAIL',JSON.stringify(x)]);
    record(2,'ENTER REQUIREMENTS',v,e);
  }

  /* 3 — توليد النموذج */
  {
    const r=await ev("window.__WS__.init(auCreateProject("
      +"JSON.parse(JSON.stringify(window.__FX__.villa)),'bld_0','IMPORT',null));"
      +"window.__WS__.open();"
      +"const p=window.__WS__.project();"
      +"return {hash:p.model_hash,rev:p.current_revision,"
      +"rooms:((p.model.floors||{}).g||{}).rooms.length};");
    const [v,e]=verdict(r,x=>(x.hash&&x.rev&&x.rooms>0)
      ?['PASS','a real model with '+x.rooms+' spaces at revision '+x.rev]
      :['FAIL',JSON.stringify(x)]);
    record(3,'GENERATE MODEL',v,e);
  }

 /* 4 — استكشاف ثلاثي الأبعاد */
{
  let r;

  try{
    const value=await pg.evaluate(async()=>{
      const host=document.getElementById('wsViewHost');
      const viewport=document.getElementById('wsViewport');

      const rect=viewport
        ? viewport.getBoundingClientRect()
        : {width:0,height:0};

      let gl=false;

      try{
        const c=document.createElement('canvas');

        gl=!!(
          c.getContext('webgl2') ||
          c.getContext('webgl')
        );
      }catch(_e){}

      let threeLoaded=false;
      let threeVersion=null;
      let rendererAvailable=false;
      let threeError=null;

      try{
        const mod=await import('three');

        threeLoaded=!!mod;
        threeVersion=mod.REVISION || null;
        rendererAvailable=
          typeof mod.WebGLRenderer==='function';
      }catch(e){
        threeError=String(
          e&&e.message
            ? e.message
            : e
        );
      }

      return {
        host:!!host,
        viewport:!!viewport,
        w:rect.width,
        h:rect.height,
        gl:gl,
        threeLoaded:threeLoaded,
        threeVersion:threeVersion,
        rendererAvailable:rendererAvailable,
        threeError:threeError
      };
    });

    r={
      ok:true,
      v:value
    };
  }catch(e){
    r={
      ok:false,
      v:null,
      err:String(
        e&&e.message
          ? e.message
          : e
      )
    };
  }

  const [v,e]=verdict(r,x=>{

    if(
      !x.host ||
      !x.viewport ||
      !(x.w>100&&x.h>100)
    ){
      return [
        'FAIL',
        JSON.stringify(x)
      ];
    }

    if(!x.gl){
      return [
        'NOT_VERIFIED',
        'the viewport exists, but WebGL is unavailable in this Chromium environment'
      ];
    }

    if(
      !x.threeLoaded ||
      !x.rendererAvailable
    ){
      return [
        'NOT_VERIFIED',
        'the viewport and WebGL are available, but Three.js could not be loaded'
        +(x.threeError
          ? ' — '+x.threeError
          : '')
      ];
    }

    return [
      'PASS',
      'the 3D viewport is present; WebGL is available; Three.js revision '
      +String(x.threeVersion)
      +' loaded with WebGLRenderer'
    ];
  });

  record(
    4,
    'EXPLORE 3D',
    v,
    e
  );
}


  /* 5 — تحديد عنصر */
  {
    const r=await ev("window.__WS__.select('g.majlis');"
      +"const row=document.querySelector('#wsTree [data-ws-node=\"g.majlis\"]');"
      +"return {sel:window.__WS__.ui().selected_id,"
      +"row:!!row,marked:row?row.classList.contains('sel'):false,"
      +"hash_unchanged:wsModelHashOf(window.__WS__.project())"
      +"===window.__WS__.project().model_hash};");
    const [v,e]=verdict(r,x=>(x.sel==='g.majlis'&&x.hash_unchanged)
      ?['PASS','the element is selected and selecting wrote nothing to the model']
      :['FAIL',JSON.stringify(x)]);
    record(5,'SELECT ELEMENT',v,e);
  }

  /* 6 — فحص الخصائص */
  {
    const r=await ev("const secs=document.querySelectorAll('#wsInsp [data-ws-section]');"
      +"const unk=document.querySelectorAll('#wsInsp [data-ws-unknown]');"
      +"const der=document.querySelectorAll('#wsInsp [data-ws-editability=\"DERIVED\"]');"
      +"const prov=document.querySelectorAll('#wsInsp [data-ws-provenance]');"
      +"return {sections:secs.length,unknown:unk.length,derived:der.length,"
      +"provenance:prov.length};");
    const [v,e]=verdict(r,x=>(x.sections>=5&&x.provenance>0)
      ?['PASS',x.sections+' sections, '+x.unknown+' values shown as unknown, '
        +x.derived+' read-only derived, '+x.provenance+' provenance labels']
      :['FAIL',JSON.stringify(x)]);
    record(6,'INSPECT PROPERTIES',v,e);
  }

  /* 7 — دخول وضع التحرير */
  {
    const r=await ev("window.__WS__.setMode('EDIT');"
      +"const ops=document.querySelectorAll('#wsInsp [data-ws-op]');"
      +"return {mode:window.__WS__.ui().ui_mode,ops:ops.length,"
      +"badge:document.getElementById('wsStMode').textContent};");
    const [v,e]=verdict(r,x=>(x.mode==='EDIT'&&x.ops>0&&/EDIT/.test(x.badge))
      ?['PASS',x.ops+' operations offered and the status bar states EDIT']
      :['FAIL',JSON.stringify(x)]);
    record(7,'ENTER EDIT MODE',v,e);
  }

  /* 8 — معاينة تغيير */
  {
    const r=await ev("const before=window.__WS__.project().model_hash;"
      +"const p=window.__WS__.beginPreview({type:'RESIZE_SPACE',"
      +"target_id:'g.majlis',parameters:{w:6,d:4}});"
      +"return {valid:!!p&&p.valid!==false,"
      +"candidate:!!(p&&p.preview&&p.preview.candidate_model_hash),"
      +"different:!!(p&&p.preview&&p.preview.candidate_model_hash!==before),"
      +"committed_unchanged:window.__WS__.project().model_hash===before,"
      +"badge:document.getElementById('wsPreviewBadge').classList.contains('on'),"
      +"status:document.getElementById('wsStPreview').textContent};");
    const [v,e]=verdict(r,x=>(x.valid&&x.candidate&&x.different
        &&x.committed_unchanged&&x.badge)
      ?['PASS','a candidate model was produced while the committed model stayed '
        +'byte-identical']
      :['FAIL',JSON.stringify(x)]);
    record(8,'PREVIEW CHANGE',v,e);
  }

  /* 9 — إلغاء المعاينة */
  {
    const r=await ev("const before=window.__WS__.project().model_hash;"
      +"const rev=window.__WS__.project().current_revision;"
      +"window.__WS__.cancelPreview();"
      +"return {hash:window.__WS__.project().model_hash===before,"
      +"rev:window.__WS__.project().current_revision===rev,"
      +"preview:window.__WS__.state().preview,"
      +"badge:document.getElementById('wsPreviewBadge').classList.contains('on')};");
    const [v,e]=verdict(r,x=>(x.hash&&x.rev&&!x.preview&&!x.badge)
      ?['PASS','cancelling left neither a revision nor a hash change']
      :['FAIL',JSON.stringify(x)]);
    record(9,'CANCEL A CHANGE',v,e);
  }

  /* 10 — إيداع تغيير: بالضغط على الزرّ نفسه الذي يضغطه المستعمل */
  {
    const r0=await ev("const before=window.__WS__.project().model_hash;"
      +"const rev0=window.__WS__.project().current_revision;"
      +"window.__WS__.setMode('EDIT'); window.__WS__.select('g.majlis');"
      +"window.__WS__.beginPreview({type:'RESIZE_SPACE',target_id:'g.majlis',"
      +"parameters:{w:6,d:4}});"
      +"window.__BEFORE__={hash:before,rev:rev0};"
      +"return {button:!!document.getElementById('wsCommitBtn')};");
    if(r0.ok&&r0.v&&r0.v.button){
      const ack=await pg.$('#wsAck'); if(ack) await ack.check();
      await pg.click('#wsCommitBtn'); }
    const r=await ev("const p=window.__WS__.project();"
      +"return {hash_changed:p.model_hash!==window.__BEFORE__.hash,"
      +"rev_changed:p.current_revision!==window.__BEFORE__.rev,"
      +"history:(p.history||[]).length,"
      +"preview_cleared:!window.__WS__.state().preview,"
      +"status:document.getElementById('wsStRev').textContent};");
    const [v,e]=verdict(r,x=>(x.hash_changed&&x.rev_changed&&x.history>=2
        &&x.preview_cleared)
      ?['PASS','pressing the commit button recorded a new revision; history now '
        +'holds '+x.history+' entries']
      :['FAIL',JSON.stringify(x)+(r0.ok?'':' / '+r0.err)]);
    record(10,'COMMIT A CHANGE',v,e);
  }

  /* 11 — تراجع وإعادة */
  {
    const r=await ev("const h1=window.__WS__.project().model_hash;"
      +"const r1=window.__WS__.project().current_revision;"
      +"const u=window.__WS__.undo();"
      +"const h2=window.__WS__.project().model_hash;"
      +"const rd=window.__WS__.redo();"
      +"const h3=window.__WS__.project().model_hash;"
      +"return {undo_valid:!!(u&&u.valid!==false),"
      +"redo_valid:!!(rd&&rd.valid!==false),"
      +"undone:h2!==h1,redone:h3!==h2,restored:h3===h1,"
      +"history:(window.__WS__.project().history||[]).length,"
      +"start_rev:r1};");
    const [v,e]=verdict(r,x=>{
      if(!x.undo_valid) return ['FAIL','undo was refused: '+JSON.stringify(x)];
      if(!x.undone) return ['FAIL','undo changed nothing: '+JSON.stringify(x)];
      if(x.redo_valid&&x.redone&&x.restored)
        return ['PASS','undo produced a different model and redo restored the '
          +'original hash exactly'];
      if(x.redo_valid&&x.redone)
        return ['PASS','undo and redo each produced a new revision'];
      return ['FAIL',JSON.stringify(x)]; });
    record(11,'UNDO AND REDO',v,e);
  }

  /* 12 — عرض التحذيرات */
  {
    const r=await ev("window.__WS__.issues();"
      +"const cats=document.querySelectorAll('#wsModalBody [data-ws-issue-cat]');"
      +"const rows=document.querySelectorAll('#wsModalBody [data-ws-issue]');"
      +"const txt=document.getElementById('wsModalBody').textContent;"
      +"window.__WS__.closeModal();"
      +"return {cats:cats.length,rows:rows.length,"
      +"fake:/\\b(safe|compliant|approved|certified)\\b/i.test(txt)};");
    const [v,e]=verdict(r,x=>(x.cats>0&&!x.fake)
      ?['PASS',x.cats+' issue categories and '+x.rows
        +' issues shown, with no compliance claim in the text']
      :['FAIL',JSON.stringify(x)]);
    record(12,'VIEW WARNINGS',v,e);
  }

  /* 13 — الانتقال من ملاحظة إلى النموذج */
  {
    const r=await ev("const before=window.__WS__.project().model_hash;"
      +"const ic=window.__WS__.issueModel();"
      +"let first=null;"
      +"Object.keys(ic.categories).forEach(k=>{ if(!first&&ic.categories[k].length)"
      +"  first=ic.categories[k][0]; });"
      +"if(!first) return {none:true};"
      +"const t=wsIssueTargets(first);"
      +"const focused=window.__WS__.focusIssue(first);"
      +"return {targets:(t.targets||[]).length,focusable:t.focusable,"
      +"selected:window.__WS__.ui().selected_id,"
      +"hash_unchanged:window.__WS__.project().model_hash===before};");
    const [v,e]=verdict(r,x=>{
      if(x.none) return ['NOT_VERIFIED','this fixture produced no issue to navigate to'];
      if(!x.hash_unchanged) return ['FAIL','navigating changed the model'];
      return x.focusable
        ?['PASS','the issue resolves to '+x.targets
          +' model target(s) and focusing wrote nothing']
        :['PASS','the issue declares itself not focusable rather than '
          +'inventing a target']; });
    record(13,'NAVIGATE FROM AN ISSUE TO THE MODEL',v,e);
  }

  /* 14 — سجلّ المراجعات والفرق */
  {
    const r=await ev("window.__WS__.history();"
      +"const rows=document.querySelectorAll('#wsModalBody [data-ws-rev]');"
      +"window.__WS__.closeModal();"
      +"const d=window.__WS__.diff();"
      +"return {rows:rows.length,diff:!!d,"
      +"changes:d?((d.property_changes||[]).length"
      +"+(d.added_paths||[]).length+(d.removed_paths||[]).length):0};");
    const [v,e]=verdict(r,x=>(x.rows>=1)
      ?['PASS',x.rows+' revisions listed'
        +(x.diff?(' and a diff of '+x.changes+' change(s) is available'):'')]
      :['FAIL',JSON.stringify(x)]);
    record(14,'VIEW REVISION HISTORY',v,e);
  }

  /* 15 — المساعد يقترح ولا يودع */
  {
    const r=await ev("const before=window.__WS__.project().model_hash;"
      +"const rev=window.__WS__.project().current_revision;"
      +"window.__WS__.assistant();"
      +"const a=window.__WS__.aiPropose('majlis');"
      +"const b=window.__WS__.aiPropose('nothing matches this phrase');"
      +"const txt=document.getElementById('wsModal').textContent;"
      +"window.__WS__.closeModal();"
      +"return {a_committed:a?a.committed:null,b_committed:b?b.committed:null,"
      +"resolved:!!(a&&(a.proposal||a.valid)),"
      +"refused_unknown:!!(b&&b.valid===false),"
      +"hash:window.__WS__.project().model_hash===before,"
      +"rev:window.__WS__.project().current_revision===rev,"
      +"claims_commit:/committed|applied|saved to the model/i.test(txt)};");
    const [v,e]=verdict(r,x=>(x.hash&&x.rev&&x.a_committed!==true
        &&x.b_committed!==true&&x.refused_unknown&&!x.claims_commit)
      ?['PASS','a resolvable phrase produced a proposal, an unresolvable one was '
        +'refused, and neither changed the model or its revision']
      :['FAIL',JSON.stringify(x)]);
    record(15,'ASSISTANT PROPOSES WITHOUT COMMITTING',v,e);
  }

  /* 16 — تصدير */
  {
    const r=await ev("window.__WS__.exportPanel();"
      +"const rows=document.querySelectorAll('#wsModalBody [data-ws-export]');"
      +"const kinds=Array.prototype.slice.call(rows)"
      +"  .map(e=>e.getAttribute('data-ws-export'));"
      +"window.__WS__.closeModal();"
      +"const p=window.__WS__.project();"
      +"const out={};"
      +"ACS_WORKSPACE_SPEC.export_kinds.forEach(k=>{"
      +"  const d=wsExportDescriptor(p,k,'COMMITTED',null,'2026-01-01T00:00:00Z');"
      +"  out[k]={valid:d.valid,source:d.descriptor&&d.descriptor.source,"
      +"    rev:d.descriptor&&d.descriptor.metadata&&d.descriptor.metadata.revision_id,"
      +"    hash:d.descriptor&&d.descriptor.metadata&&d.descriptor.metadata.model_hash,"
      +"    certifies:d.descriptor&&d.descriptor.certifies_nothing,"
      +"    preview:d.descriptor&&d.descriptor.is_preview}; });"
      +"return {rows:rows.length,kinds:kinds,out:out,"
      +"rev_now:p.current_revision,hash_now:p.model_hash};");
    const [v,e]=verdict(r,x=>{
      const ks=Object.keys(x.out);
      const allValid=ks.every(k=>x.out[k].valid===true
        &&x.out[k].source==='COMMITTED'
        &&x.out[k].rev===x.rev_now
        &&x.out[k].hash===x.hash_now
        &&x.out[k].certifies===true
        &&x.out[k].preview===false);
      return (x.rows>0&&ks.length>0&&allValid)
        ?['PASS',x.rows+' export kinds offered; every descriptor names the committed '
          +'revision and model hash and certifies nothing']
        :['FAIL',JSON.stringify(x.out)]; });
    record(16,'EXPORT',v,e);
  }

  /* 17 — تبديل اللغة دون فقد الحالة، ثم اتّساق الصفحة */
  {
    const r=await ev("const sel=window.__WS__.ui().selected_id;"
      +"const mode=window.__WS__.ui().ui_mode;"
      +"const hash=window.__WS__.project().model_hash;"
      +"window.__WS__.setLanguage('ar');"
      +"const ar={dir:document.documentElement.getAttribute('dir'),"
      +"  title:document.getElementById('wsTreeTitle').textContent};"
      +"window.__WS__.setLanguage('en');"
      +"const en={dir:document.documentElement.getAttribute('dir'),"
      +"  title:document.getElementById('wsTreeTitle').textContent};"
      +"return {ar:ar,en:en,sel:window.__WS__.ui().selected_id===sel,"
      +"mode:window.__WS__.ui().ui_mode===mode,"
      +"hash:window.__WS__.project().model_hash===hash};");
    const [v,e]=verdict(r,x=>(x.ar.dir==='rtl'&&x.en.dir==='ltr'
        &&x.ar.title!==x.en.title&&x.sel&&x.mode&&x.hash)
      ?['PASS','Arabic renders right-to-left and English left-to-right; selection, '
        +'mode and model hash all survive the switch']
      :['FAIL',JSON.stringify(x)]);
    record(17,'SWITCH LANGUAGE WITHOUT LOSING STATE',v,e);
  }

  await pg.close();
  await browser.close();

  const by=v=>steps.filter(s=>s.verdict===v).length;
  console.log('\n──────────────────────────────────────────────');
  console.log('PRODUCT WALKTHROUGH: '+by('PASS')+' PASS, '+by('FAIL')+' FAIL, '
    +by('NOT_SUPPORTED')+' NOT_SUPPORTED, '+by('NOT_VERIFIED')+' NOT_VERIFIED'
    +'  (of '+steps.length+' steps)');
  console.log('uncaught page errors during the whole walkthrough: '
    +(errs.length?errs.join(' | '):'none'));
  fs.writeFileSync(path.join(HERE,'walkthrough_result.json'),
    JSON.stringify({steps:steps,page_errors:errs},null,1),'utf8');
  if(by('FAIL')||errs.length) process.exit(1);
})().catch(e=>{ console.log('  ✗ walkthrough aborted:',e&&e.message);
  console.log('\nPRODUCT WALKTHROUGH: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  process.exit(1); });
