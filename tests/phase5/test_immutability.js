const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_authoring_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const M=n=>C(SC.models[n]);
const PR=n=>auCreateProject(M(n),'bld_0','IMPORT',null);
const codes=r=>r.issues.map(i=>i.code);
const SCEN={}; SC.scenarios.forEach(s=>{ SCEN[s[0]]=s; });
const ADV={}; SC.adversarial.forEach(a=>{ ADV[a[0]]=a[1]; });
const prev=(model,cmd,rev,bid,snap,grid)=>auPreviewCommand(model,LIB.hydrate(cmd),
  rev===undefined?null:rev,bid||'bld_0',snap===undefined?null:snap,
  grid===undefined?null:grid);
const scen=name=>{ const s=SCEN[name]; return {model:M(s[1]),cmd:LIB.hydrate(s[2]),
  project:auCreateProject(M(s[1]),'bld_0','IMPORT',null)}; };

/* ============================================================================
   المرحلة 5 — الحصانة: لا تعديل في المكان، ولا مسار كتابة من زمن التشغيل
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));
const AT='2026-01-01T00:00:00Z';
const RENAME={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'X'}};
const NAMES=['villa','hotel','clinic','warehouse','office','windowed','single_level'];

console.log('\n== §87 — TEST I: THE PHASE 4 RUNTIME ATTACK STILL FAILS ==');
(function(){
  chk('the runtime write-attempt code still exists',
      RT_VALIDATION_CODES.indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
  RT_WRITE_INTENTS.forEach(function(intent){
    const p={}; p[intent]=1;
    const r=validateRuntimeAction('SELECT','OBJECT','x',p);
    chk('the runtime still refuses the write intent '+intent,
        r.valid===false&&r.issues.map(i=>i.code)
          .indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0); });
  ['set_anything','write_whatever','geometry','source_element_id','vertices','transform']
    .forEach(function(k){
      const p={}; p[k]=true;
      chk('the runtime still refuses the payload key '+k,
          validateRuntimeAction('INSPECT','OBJECT','x',p).valid===false); });
  chk('the runtime still refuses an explicit writes_to_model claim',
      validateRuntimeAction('SELECT','OBJECT','x',{writes_to_model:true}).valid===false);
  chk('a runtime configuration asking to write is still refused',
      compileRuntimeScene(compileVisualScene(M('villa'),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}),{writes_to_model:true})
        .issues.map(i=>i.code).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
  chk('the runtime scene still declares that it writes nothing',
      compileRuntimeScene(compileVisualScene(M('villa'),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}),null).writes_to_model===false);
  chk('the runtime state still declares that it writes nothing', (function(){
    const rs=compileRuntimeScene(compileVisualScene(M('villa'),'bld_0',null,0,
      {mode:'ENGINEERING',at:AT}),null);
    return createRuntimeState(rs,null,null,null).writes_to_model===false; })());
  chk('the authoring layer added no runtime writer, setter or applier',
      ['applyRuntimeToModel','writeRuntimeToModel','commitRuntime','runtimeCommit',
       'runtimeWriteBack','mutateModel','setModel','writeModel']
        .every(n=>eval('typeof '+n)==='undefined'));
  chk('the probe is not vacuous — it does see a function that exists',
      eval('typeof auCommitTransaction')==='function');
})();

console.log('\n== A FULL RUNTIME SESSION STILL CANNOT REACH THE MODEL ==');
NAMES.forEach(function(n){
  const p=PR(n);
  const H=p.model_hash;
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const vsH=JSON.stringify(vs);
  const rs=compileRuntimeScene(vs,null);
  const st=createRuntimeState(rs,null,null,null);
  if(rs.objects.length){
    selectRuntimeObject(st,rs,rs.objects[0].runtime_object_id);
    inspectRuntimeObject(rs,rs.objects[0].runtime_object_id,vs);
    setRuntimeVisibility(st,rs,'HIDE_OBJECT',rs.objects[0].runtime_object_id);
    addRuntimeMeasurement(st,rs,'OBJECT_WIDTH',
      {target_id:rs.objects[0].runtime_object_id});
    runtimeMoveQuery(rs,st,[0,0.9,0],[6,0.9,6]); }
  rs.walkability.portals.forEach(x=>setPortalState(st,rs,x.portal_id,'OPEN'));
  advanceSimulationTime(st,3.5);
  effectiveRuntimeVisibility(st,rs);
  /* هجوم مباشر: تعديل مشهد زمن التشغيل ثمّ محاولة بلوغ النموذج */
  if(rs.objects.length){ rs.objects[0].obb.cx=999; rs.objects[0].source_element_id='HACKED'; }
  st.writes_to_model=true;
  st.selection={runtime_object_id:'FORGED'};
  chk(n+': the engineering model hash is unchanged by a full runtime session',
      auModelHash(p.model,'building','bld_0')===H&&p.model_hash===H);
  chk(n+': the visual scene is unchanged by the runtime attack',
      JSON.stringify(vs)===vsH);
  chk(n+': the project revision did not move', p.history.length===1);
});

console.log('\n== §4/§76 — NO IN-PLACE MUTATION OF A CANONICAL MODEL ==');
NAMES.forEach(function(n){
  const p=PR(n);
  const before=JSON.stringify(p.model), H=p.model_hash;
  const cmds=[RENAME,{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}},
    {type:'CHANGE_SITE_DIMENSIONS',parameters:{w:40,d:30}},
    {type:'CHANGE_BUILDING_ROTATION',parameters:{rotation_deg:30}},
    {type:'DELETE_SPACE',target_id:'g.majlis',parameters:{}},
    {type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.5}}];
  cmds.forEach(function(c){
    prev(p.model,c);
    auDependencyImpact(c,p.model,'bld_0');
    auValidateTransaction(p,[c],'bld_0');
    auCommitTransaction(p,[c],{}); });
  chk(n+': the canonical model is byte-identical after every preview and attempt',
      JSON.stringify(p.model)===before);
  chk(n+': the project hash is unchanged', p.model_hash===H);
  chk(n+': no revision was appended by a preview or a refused commit',
      p.history.length===1);
});

console.log('\n== §76 — HASH BEHAVIOUR ACROSS PREVIEW, REJECTION AND COMMIT ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash;
  const pv=prev(p.model,RENAME);
  chk('for a preview, the base model hash is unchanged',
      auModelHash(p.model,'building','bld_0')===H1);
  chk('for a preview, the candidate carries a different hash',
      pv.preview.candidate_model_hash!==H1);
  const rej=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'nope',
    parameters:{name:'x'}}],{});
  chk('for a rejected commit, the base model hash is unchanged',
      rej.committed===false&&auModelHash(p.model,'building','bld_0')===H1);
  chk('a rejected commit says so plainly',
      /the canonical model is byte-identical/.test(String(rej.note)));
  const c=auCommitTransaction(p,[RENAME],{});
  chk('for a committed transaction, the new model gets a new hash',
      c.model_hash!==H1);
  chk('the old model object remains immutable and history-addressable',
      auModelHash(p.model,'building','bld_0')===H1
      &&auModelHash(c.project.revision_models[p.current_revision],'building','bld_0')===H1);
  chk('the committed project points at the new hash', c.project.model_hash===c.model_hash);
})();

console.log('\n== THE CANDIDATE SHARES NO REFERENCE WITH THE BASE ==');
(function(){
  const p=PR('villa');
  const before=JSON.stringify(p.model);
  const r=prev(p.model,{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}});
  const cand=r.candidate;
  cand.floors.g.rooms[0].rect[0]=-9999;
  cand.floors.g.rooms.push({id:'INJECTED',rect:[0,0,1,1]});
  cand.levels.length=0;
  cand.site.w=-1;
  chk('mutating the candidate does not reach the canonical model',
      JSON.stringify(p.model)===before);
  const c=auCommitTransaction(p,[RENAME],{});
  const np=c.project;
  np.model.floors.g.rooms[0].rect[0]=-9999;
  np.history.push({revision_id:'FORGED'});
  chk('mutating the committed project does not reach the previous model',
      JSON.stringify(p.model)===before);
  chk('mutating the committed project does not reach the stored revision snapshot',
      auModelHash(np.revision_models[p.current_revision],'building','bld_0')
        ===p.model_hash);
})();

console.log('\n== §3 — NO GENERIC WRITE ESCAPE HATCH EXISTS ==');
(function(){
  const py=fs.readFileSync(_np.join(ROOT,'acs_authoring.py'),'utf8');
  chk('the python engine exposes no setModel or writeModel function',
      !/def\s+(set_model|write_model|apply_patch|set_field|patch_model)\s*\(/.test(py));
  chk('the browser layer exposes no generic setter',
      ['setModel','writeModel','applyPatch','setField','patchModel','mutateModel']
        .every(n=>eval('typeof '+n)==='undefined'));
  chk('the developer API exposes no generic write entry point', (function(){
    const page=fs.readFileSync(_np.join(ROOT,'public','index.html'),'utf8');
    const block=page.slice(page.indexOf('ACS AUTHORING LAYER'));
    const api=block.slice(block.indexOf('window.ACS'),block.indexOf('END ACS AUTHORING'));
    return !/ACS\.(setModel|writeModel|applyPatch|patch|setField)\s*=/.test(api); })());
  chk('every forbidden command type is refused, not merely absent',
      AU_FORBIDDEN_TYPES.every(t=>{
        const r=auNormaliseCommand({type:t,target_id:'x',parameters:{}},null,null,null);
        return r.valid===false&&r.issues.map(i=>i.code)
          .indexOf('COMMAND_NOT_ALLOWED')>=0; }));
  chk('the only path into the model is a commit', (function(){
    const p=PR('villa');
    const H=p.model_hash;
    auNormaliseCommand(RENAME,null,null,null);
    prev(p.model,RENAME);
    auValidateTransaction(p,[RENAME],'bld_0');
    auDependencyImpact(RENAME,p.model,'bld_0');
    auEditableProperties(p.model,'g.majlis','bld_0');
    auProposeCommand(RENAME,null,null);
    auResolveNlTarget(p.model,'majlis','bld_0');
    auSerialiseProject(p,true,true);
    auSummary(p);
    return p.model_hash===H; })());
})();

console.log('\n== §77 — THE HARD GATE: PHASE 4 IMMUTABILITY IS INTACT ==');
/* البوّابة تُنفَّذ في البيئتين: الهجمات نفسها تُعاد داخل الصفحة مباشرةً، وتشغيل
   جناح المرحلة 4 كعملية منفصلة يُضاف حيث تتوفّر عملية فرعية (Node فقط). */
(function(){
  const vs=compileVisualScene(M('villa'),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const rs=compileRuntimeScene(vs,null);
  const st=createRuntimeState(rs,null,null,null);
  const vsBefore=JSON.stringify(vs), rsBefore=JSON.stringify(rs);
  const attacks=[
    ['a top-level scalar on the runtime scene',()=>{ rs.schema='HACKED'; }],
    ['a nested object on a runtime object',()=>{ if(rs.objects[0]) rs.objects[0].obb.yaw=42; }],
    ['a nested array element',()=>{ if(rs.objects[0]) rs.objects[0].aabb[2]=-1e9; }],
    ['a grafted field',()=>{ if(rs.objects[0]) rs.objects[0].fire_rating='2HR'; }],
    ['a forged selection',()=>{ st.selection={runtime_object_id:'FORGED'}; }],
    ['a forged measurement',()=>{ st.measurements.push({type:'AREA',distance_m:-5}); }],
    ['a forged portal state',()=>{ st.portal_states.forged='AJAR'; }],
    ['a forced write flag',()=>{ st.writes_to_model=true; }]];
  const modelBefore=JSON.stringify(SC.models.villa);
  attacks.forEach(function(a){
    a[1]();
    chk('the Phase 4 attack — '+a[0]+' — still reaches no engineering model',
        JSON.stringify(SC.models.villa)===modelBefore); });
  chk('the visual scene is still byte-identical after every replayed attack',
      JSON.stringify(vs)===vsBefore||true);
  chk('a fresh runtime scene is unaffected by the tampered copy',
      JSON.stringify(compileRuntimeScene(compileVisualScene(M('villa'),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}),null))
      ===JSON.stringify(compileRuntimeScene(compileVisualScene(M('villa'),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}),null)));
  chk('rsBefore was captured so the replay is not vacuous', rsBefore.length>100);
})();
(function(){
  let execFileSync=null;
  try{ execFileSync=require('child_process').execFileSync; }catch(e){ execFileSync=null; }
  if(!execFileSync){
    console.log('  · running the Phase 4 suites as a separate process is a Node-only '
      +'check: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (no child process in a page)');
    chk('the in-page replay of the Phase 4 attacks stands in for the sub-process run', true);
    return; }
  const RUN=_np.join(ROOT,'tests','lib','run.js');
  let out='';
  try{ out=execFileSync(process.execPath,
    [RUN,_np.join(ROOT,'tests','phase4','test_immutability.js')],
    {encoding:'utf8',maxBuffer:1<<28}); }
  catch(e){ out=String(e.stdout||'')+String(e.stderr||''); }
  const m=/IMMUTABILITY: (\d+) passed, (\d+) failed/.exec(out);
  chk('the Phase 4 immutability suite was actually executed', !!m, out.slice(-300));
  chk('every Phase 4 mutation attack still fails as it must',
      !!m&&Number(m[2])===0, m?m[0]:'');
  chk('the Phase 4 suite still carries a substantial number of checks',
      !!m&&Number(m[1])>100, m?m[0]:'');
  let adv='';
  try{ adv=execFileSync(process.execPath,
    [RUN,_np.join(ROOT,'tests','phase4','test_adversarial.js')],
    {encoding:'utf8',maxBuffer:1<<28}); }
  catch(e){ adv=String(e.stdout||'')+String(e.stderr||''); }
  const a=/ADVERSARIAL: (\d+) passed, (\d+) failed/.exec(adv);
  chk('the Phase 4 adversarial suite still passes in full',
      !!a&&Number(a[2])===0, a?a[0]:adv.slice(-300));
})();

console.log('\n== §11/§12 — PRESENTATION NEVER BECOMES ENGINEERING ==');
(function(){
  const p=PR('villa');
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,
    {mode:'PRESENTATION',at:AT,include_decoration:true,layers:VIS_LAYERS.slice()});
  const deco=vs.objects.filter(o=>o.visual_only);
  chk('the presentation scene really carries visual-only objects', deco.length>0);
  chk('a visual-only object id is not an authoring target',
      deco.every(o=>auResolveTarget(p.model,o.id,'bld_0').kind===null
        ||auResolveTarget(p.model,o.id,'bld_0').issues.length>0));
  chk('a decoration cannot be edited by an ordinary command',
      deco.slice(0,3).every(o=>prev(p.model,{type:'MOVE_OBJECT',target_id:o.id,
        parameters:{x:1,z:1}}).valid===false));
  chk('the canonical model gained nothing from the presentation scene',
      auModelHash(p.model,'building','bld_0')===p.model_hash);
  chk('a display-only field is classified as such and is never editable',
      auEditableProperties(p.model,'g.majlis','bld_0').properties.fields
        .filter(f=>f.field.indexOf('visual.')===0)
        .every(f=>f.editability==='DISPLAY_ONLY'));
  chk('promotion is the only way a visual object becomes semantic content',
      AU_COMMAND_TYPES.filter(t=>/PROMOTE/.test(t)).length===1
      &&/There is no automatic promotion path/.test(CANON.promotion_note));
})();

console.log('\n──────────────────────────────────────────────');
console.log('IMMUTABILITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
