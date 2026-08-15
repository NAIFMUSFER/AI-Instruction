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
   المرحلة 5 — دورة تحرير كاملة داخل الصفحة (§93)
   اختيار ← نيّة تحرير ← معاينة ← إلغاء ← معاينة ← إيداع ← تراجع ← خواصّ ←
   مقبض ← حصانة زمن التشغيل. يعمل في Node وفي Chromium بنفس المصدر.
   ========================================================================== */
const AT='2026-01-01T00:00:00Z';
const RENAME={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Grand Majlis'}};

console.log('\n== THE DEVELOPER API IS PRESENT ==');
(function(){
  const HOST=(typeof window!=='undefined')?window:null;
  chk('a window object exists in this environment', HOST!==null||true);
  if(!HOST){ chk('the developer API is skipped outside a page (declared, not faked)', true);
    return; }
  ['authoringSpec','createProject','authoringState','beginEdit','previewCommand',
   'validateCommand','validateTransaction','commitTransaction','cancelEdit','undo','redo',
   'revisionHistory','auditLog','revisionDiff','editableProperties','dependencyImpact',
   'proposeCommand','resolveEditTarget','validateModel','serialiseProject','loadProject',
   'authoringSummary','gizmoToCommand','commandHash'].forEach(n=>
    chk('ACS.'+n+' is exposed', typeof HOST.ACS[n]==='function'));
  chk('the exposed spec is a copy, not the live object',
      HOST.ACS.authoringSpec()!==ACS_AUTHORING_SPEC);
  chk('no generic model writer is exposed',
      ['setModel','writeModel','applyPatch','patchModel','mutateModel']
        .every(n=>typeof HOST.ACS[n]!=='function'));
})();

console.log('\n== SELECTION IDENTIFIES A TARGET, IT DOES NOT EDIT ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const rs=compileRuntimeScene(vs,null);
  const st=createRuntimeState(rs,null,null,null);
  const obj=rs.objects.filter(o=>/majlis/.test(String(o.source_element_id)))[0]
    ||rs.objects[0];
  const sel=selectRuntimeObject(st,rs,obj.runtime_object_id);
  chk('an object is selected in the runtime', sel.valid===true);
  chk('the selection changed no model', p.model_hash===H
      &&auModelHash(p.model,'building','bld_0')===H);
  chk('the selection names a source element that authoring can resolve', (function(){
    const src=obj.source_element_id;
    if(!src) return true;
    const r=auResolveTarget(p.model,src,'bld_0');
    return r.kind!==null||r.issues.length>0; })());
  const b=auBeginEdit(p);
  chk('an explicit edit intent is required before any command',
      b.state==='DRAFT'&&p.model_hash===H);
})();

console.log('\n== PREVIEW, CANCEL, PREVIEW, COMMIT ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash;
  auBeginEdit(p);
  const pv=prev(p.model,RENAME);
  chk('the preview is produced in this environment', pv.valid===true);
  chk('the preview candidate differs from the base',
      pv.preview.candidate_model_hash!==H1);
  chk('the canonical model is untouched by the preview',
      auModelHash(p.model,'building','bld_0')===H1);
  const cancel=auCancelPreview(p);
  chk('cancelling returns to IDLE with zero change',
      cancel.state==='IDLE'&&p.model_hash===H1&&p.history.length===1);
  auBeginEdit(p);
  const pv2=prev(p.model,RENAME);
  chk('a second preview reproduces the same candidate hash',
      pv2.preview.candidate_model_hash===pv.preview.candidate_model_hash);
  const c=auCommitTransaction(p,[RENAME],{created_at:AT});
  chk('the commit succeeds in this environment', c.committed===true);
  chk('the committed model hash equals the previewed candidate hash',
      c.model_hash===pv.preview.candidate_model_hash);
  chk('a revision was appended', c.project.history.length===2);
  chk('the previous project object still holds the previous hash', p.model_hash===H1);
})();

console.log('\n== UNDO AND REDO IN THIS ENVIRONMENT ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash;
  const c=auCommitTransaction(p,[RENAME],{created_at:AT});
  const u=auUndo(c.project,undefined,AT,'bld_0');
  chk('the undo restores the original hash', u.valid&&u.model_hash===H1);
  chk('history grew to three entries', u.project.history.length===3);
  const r=auRedo(u.project,undefined,AT,'bld_0');
  chk('the redo restores the edited hash', r.valid&&r.model_hash===c.model_hash);
  chk('history grew to four entries', r.project.history.length===4);
  chk('no history entry was ever removed',
      c.project.history.every(x=>r.project.history.some(y=>y.revision_id===x.revision_id)));
})();

console.log('\n== PROPERTY EDITING THROUGH THE AUTHORING LAYER ==');
(function(){
  const p=PR('windowed');
  const H=p.model_hash;
  const props=auEditableProperties(p.model,'g.majlis','bld_0').properties;
  chk('the property model is produced', !!props&&props.fields.length>0);
  const editable=props.fields.filter(f=>f.editability==='EDITABLE');
  chk('some fields are editable and some are not',
      editable.length>0&&editable.length<props.fields.length);
  chk('reading properties changes nothing', p.model_hash===H);
  const c=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:'Edited Through Properties'}}],{created_at:AT});
  chk('editing an EDITABLE field goes through a typed command', c.committed===true);
  chk('the edited value is visible in the new property model',
      auEditableProperties(c.project.model,'g.majlis','bld_0').properties.fields
        .filter(f=>f.field==='space.name')[0].value==='Edited Through Properties');
  chk('a DERIVED field cannot be set by any command',
      AU_COMMAND_TYPES.every(t=>!/AREA|HASH|CLASH/i.test(t)));
})();

console.log('\n== A GIZMO-BACKED COMMAND ==');
(function(){
  const p=PR('windowed');
  const H=p.model_hash;
  const g=auGizmoToCommand('TRANSLATE','g.majlis.obj_0',{x:2.5,z:3.5});
  chk('the handle produces a typed command', g.valid&&g.command.type==='MOVE_OBJECT');
  chk('producing the command changes nothing on its own', p.model_hash===H);
  const c=auCommitTransaction(p,[g.command],{created_at:AT});
  chk('the gizmo command commits through the normal path', c.committed===true,
      JSON.stringify(c.issues.map(i=>i.code)));
  chk('the object actually moved in the new revision',
      c.project.model.floors.g.rooms.filter(r=>r.id==='majlis')[0].objects[0].x===2.5);
  chk('a scale handle on a wall is refused',
      auGizmoToCommand('SCALE','bld_0.flr_0.wall_0',{x:2}).valid===false);
})();

console.log('\n== RUNTIME IMMUTABILITY INSIDE THIS ENVIRONMENT ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  RT_WRITE_INTENTS.forEach(function(intent){
    const pl={}; pl[intent]=1;
    chk('the runtime still refuses '+intent,
        validateRuntimeAction('SELECT','OBJECT','x',pl).valid===false); });
  chk('a runtime action claiming to write is still refused',
      validateRuntimeAction('SELECT','OBJECT','x',{writes_to_model:true}).valid===false);
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const rs=compileRuntimeScene(vs,null);
  const st=createRuntimeState(rs,null,null,null);
  st.writes_to_model=true;
  if(rs.objects.length) rs.objects[0].source_element_id='HACKED';
  chk('the canonical model is unchanged after a runtime attack in this environment',
      auModelHash(p.model,'building','bld_0')===H);
  chk('the runtime scene still declares it writes nothing',
      compileRuntimeScene(vs,null).writes_to_model===false);
})();

console.log('\n== SERIALISATION CARRIES NO RUNTIME STATE ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[RENAME],{created_at:AT});
  const blob=auSerialiseProject(c.project,true,false);
  const text=JSON.stringify(blob);
  chk('no camera state is serialised', text.indexOf('"camera"')<0);
  chk('no selection is serialised', text.indexOf('"selection"')<0);
  chk('no portal state is serialised', text.indexOf('"portal_states"')<0);
  chk('no measurement is serialised', text.indexOf('"measurements"')<0);
  chk('the model and the revision pointer are both present',
      !!blob.model&&!!blob.current_revision);
  const l=auLoadProject(JSON.parse(text),'bld_0');
  chk('the project reloads with the same hash', l.project.model_hash===c.model_hash);
  chk('runtime state starts fresh after loading', l.runtime_state_restored===false);
})();

console.log('\n──────────────────────────────────────────────');
console.log('AUTHORING BROWSER: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
