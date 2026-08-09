const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_workspace_fixtures.js'));
const FX=LIB.models(), MEPF=LIB.mep();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const PR=n=>auCreateProject(C(FX[n]||MEPF[n]),'bld_0','IMPORT',null);
const ARCH=p=>compileArchitecture(C(p.model),'bld_0',null,0);
const codes=r=>r.issues.map(i=>i.code);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_workspace.json'),'utf8'));

/* ============================================================================
   المرحلة 6 — عقد مساحة العمل: الحدود، الشجرة، الفاحص، الملاحظات
   ========================================================================== */
console.log('\n== §72 — SPEC INTEGRITY AND STATE BOUNDARIES ==');
chk('the browser spec is byte-identical to acs_workspace.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_WORKSPACE_SPEC));
chk('the schema and ui version are pinned',
    WS_SCHEMA==='acs.workspace/1'&&/^acs-workspace-ui\//
      .test(ACS_WORKSPACE_SPEC.compiler_version));
chk('the six state classes are declared',
    JSON.stringify(WS_STATE_CLASSES)===JSON.stringify(
      ['UI_STATE','RUNTIME_STATE','AUTHORING_STATE','ENGINEERING_MODEL',
       'DERIVED_ANALYSIS','PRESENTATION_OUTPUT']));
chk('every ownership entry names a declared class',
    Object.keys(WS_STATE_OWNERSHIP).every(k=>
      WS_STATE_CLASSES.indexOf(WS_STATE_OWNERSHIP[k])>=0));
['selected_id','hovered_id','tree_expanded','active_panel','language','theme',
 'ui_mode','level_filter','discipline_filter','issue_filter'].forEach(k=>
  chk('the key '+k+' is owned by UI_STATE', wsClassifyStateKey(k)==='UI_STATE'));
['camera','navigation_mode','visibility','portal_states','measurements']
  .forEach(k=>chk('the key '+k+' is owned by RUNTIME_STATE',
    wsClassifyStateKey(k)==='RUNTIME_STATE'));
['model','model_hash','current_revision','history'].forEach(k=>
  chk('the key '+k+' is owned by ENGINEERING_MODEL',
      wsClassifyStateKey(k)==='ENGINEERING_MODEL'));
['visual_reference','visual_intent','snapshot','glb'].forEach(k=>
  chk('the key '+k+' is owned by PRESENTATION_OUTPUT',
      wsClassifyStateKey(k)==='PRESENTATION_OUTPUT'));
chk('only the canonical model feeds the model hash',
    JSON.stringify(CANON.model_hash_inputs)===JSON.stringify(['model']));

console.log('\n== §91 — TEST N: UI STATE CANNOT ENTER THE MODEL HASH ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const ui=wsUiStateDefault();
  ui.selected_id='g.majlis'; ui.active_panel='HISTORY'; ui.language='en';
  ui.theme='light'; ui.ui_mode='EDIT'; ui.tree_expanded=['project','site'];
  ui.discipline_filter=['MEP']; ui.level_filter=1; ui.display_unit='IMPERIAL_FT';
  const r=wsAssertUiStateExcluded(p,ui);
  chk('changing every UI key leaves the model hash unchanged', r.unchanged);
  chk('no UI key leaked into the canonical model', r.leaked_keys.length===0,
      JSON.stringify(r.leaked_keys));
  chk('the boundary check reports clean', r.clean===true);
  chk('the model hash is still the original', wsModelHashOf(p)===H);
  const st=createRuntimeState(compileRuntimeScene(compileVisualScene(C(p.model),
    'bld_0',null,0,{mode:'ENGINEERING',at:AT}),null),null,null,null);
  st.camera.position=[9,9,9]; st.navigation_mode='WALK';
  st.visibility.hidden_object_ids.push('x'); st.simulation_time=42;
  chk('changing every runtime key leaves the model hash unchanged',
      wsModelHashOf(p)===H);
  chk('no revision was created by any UI or runtime change', p.history.length===1);
  chk('the workspace summary states it writes nothing to the model',
      wsWorkspaceSummary(p,ui,null,null).ui_writes_to_model===false
      &&wsWorkspaceSummary(p,ui,null,null).runtime_writes_to_model===false);
})();

console.log('\n== §4 — PROJECT TREE IS BUILT FROM REAL MODEL DATA ==');
(function(){
  const p=PR('villa'); const arch=ARCH(p);
  const t=wsProjectTree(p,arch,null,'en');
  chk('the tree is produced', !!t.root&&t.node_count>10);
  chk('the root is the project', t.root.kind==='PROJECT');
  chk('the project contains a site', t.root.children[0].kind==='SITE');
  chk('the site contains a building', t.root.children[0].children[0].kind==='BUILDING');
  const bld=t.root.children[0].children[0];
  const levels=bld.children.filter(c=>c.kind==='LEVEL');
  chk('every model level appears in the tree',
      levels.length===(p.model.levels||[]).length, levels.length+'');
  chk('every tree node kind is declared',
      (function walk(n){ return WS_TREE_KINDS.indexOf(n.kind)>=0
        &&n.children.every(walk); })(t.root));
  chk('every space node id resolves in the canonical model', (function(){
    const ids=[];
    (function walk(n){ if(n.kind==='SPACE') ids.push(n.node_id);
      n.children.forEach(walk); })(t.root);
    return ids.length>0&&ids.every(id=>
      auResolveTarget(p.model,id,'bld_0').kind==='SPACE'); })());
  chk('every door node id resolves to a door', (function(){
    const ids=[];
    (function walk(n){ if(n.kind==='DOOR') ids.push(n.node_id);
      n.children.forEach(walk); })(t.root);
    return ids.length>0&&ids.every(id=>
      auResolveTarget(p.model,id,'bld_0').kind==='DOOR'); })());
  chk('every object node id resolves to an object', (function(){
    const ids=[];
    (function walk(n){ if(n.kind==='OBJECT') ids.push(n.node_id);
      n.children.forEach(walk); })(t.root);
    return ids.length===0||ids.every(id=>
      auResolveTarget(p.model,id,'bld_0').kind==='OBJECT'); })());
  chk('there is no placeholder or invented node', (function(){
    let bad=false;
    (function walk(n){ if(/placeholder|example|lorem|TODO|dummy/i.test(n.name)) bad=true;
      n.children.forEach(walk); })(t.root);
    return !bad; })());
  chk('the space count in the tree equals the model space count', (function(){
    let n=0; (function walk(x){ if(x.kind==='SPACE') n++; x.children.forEach(walk); })(t.root);
    return n===_auAllRooms(p.model).length; })());
  chk('building the tree writes nothing to the model', t.writes_to_model===false);
  const mep=auCreateProject(C(MEPF.clash_mep),'bld_0','IMPORT',null);
  const tm=wsProjectTree(mep,ARCH(mep),null,'en');
  chk('a model carrying MEP shows an MEP group',
      JSON.stringify(tm).indexOf('MEP_GROUP')>=0);
  chk('a model carrying structure shows a structure group',
      JSON.stringify(tm).indexOf('STRUCTURE_GROUP')>=0);
  chk('a model with no MEP shows no MEP group',
      JSON.stringify(t).indexOf('MEP_GROUP')<0);
})();

console.log('\n== §5/§76 — FILTERS AFFECT DISPLAY ONLY ==');
(function(){
  const p=PR('villa'); const t=wsProjectTree(p,ARCH(p),null,'en');
  const H=p.model_hash;
  const all=wsFlattenTree(t,['project','site','bld_0'],[],null);
  const filtered=wsFlattenTree(t,['project','site','bld_0'],['MEP'],null);
  chk('a discipline filter changes what is listed',
      filtered.row_count<=all.row_count);
  chk('filtering writes nothing to the model',
      wsModelHashOf(p)===H&&filtered.writes_to_model===false);
  const lvl=wsFlattenTree(t,['project','site','bld_0','bld_0.flr_0'],[],0);
  chk('a level filter is display state only', wsModelHashOf(p)===H);
  chk('expanding a node reveals its children',
      wsFlattenTree(t,['project','site','bld_0'],[],null).row_count
        >wsFlattenTree(t,[],[],null).row_count);
  chk('the tree declares when it needs virtualising',
      typeof t.virtualise==='boolean');
  chk('a large project asks for virtualisation', (function(){
    const rooms=[];
    for(let i=0;i<500;i++) rooms.push({id:'sp_'+i,rect:[(i%20)*6,Math.floor(i/20)*5,6,5]});
    const big=auCreateProject({meta:{type:'office',name:'big'},wall_h:3,wall_t:0.2,
      floor_height:3.2,site:{w:200,d:200},levels:[{index:0,template:'g'}],
      floors:{g:{rooms:rooms}}},'bld_0','IMPORT',null);
    return wsProjectTree(big,null,null,'en').virtualise===true; })());
})();

console.log('\n== §8/§9/§10/§11 — INSPECTOR CONTRACT ==');
(function(){
  const p=PR('villa'); const arch=ARCH(p);
  const m=wsInspectorModel(p,'g.majlis',arch,null,null,'en');
  chk('the inspector resolves a space', m.valid===true);
  ['IDENTITY','GEOMETRY','PROPERTIES','RELATIONSHIPS','ISSUES','PROVENANCE']
    .forEach(s=>chk('the inspector exposes the section '+s, s in m.sections));
  chk('identity carries the id, kind, discipline and level',
      m.identity.id==='g.majlis'&&m.identity.kind==='SPACE'
      &&m.identity.discipline==='ARCHITECTURE'&&m.identity.level===0);
  const all=(m.sections.GEOMETRY||[]).concat(m.sections.PROPERTIES||[]);
  chk('every field declares a declared editability class',
      all.every(f=>WS_EDITABILITY.indexOf(f.editability)>=0));
  chk('some fields are editable and some are not',
      m.editable_count>0&&m.editable_count<all.length);
  chk('a derived field is never editable',
      all.filter(f=>f.editability==='DERIVED').every(f=>f.editable===false));
  chk('a display-only field is never editable',
      all.filter(f=>f.editability==='DISPLAY_ONLY').every(f=>f.editable===false));
  chk('a read-only field is never editable',
      all.filter(f=>f.editability==='READ_ONLY').every(f=>f.editable===false));
  chk('reading the inspector writes nothing', m.writes_to_model===false);
  chk('the inspector claims no compliance', m.compliance==='NOT_EVALUATED');
  chk('relationships name real hosted openings',
      (m.sections.RELATIONSHIPS||[]).some(r=>r.relation==='HOSTS_DOOR'));
  chk('every provenance entry carries a declared label',
      (m.sections.PROVENANCE||[]).every(x=>
        Object.keys(WS_PROVENANCE).some(k=>WS_PROVENANCE[k].en===x.label
          ||WS_PROVENANCE[k].ar===x.label)));
  chk('no provenance label claims a regulation',
      (m.sections.PROVENANCE||[]).every(x=>!wsIsForbiddenLabel(x.label)));
  chk('the forbidden-label check is not vacuous',
      wsIsForbiddenLabel('Required by SBC')&&wsIsForbiddenLabel('Compliant'));
  chk('a forbidden source can never produce a compliance label',
      ['code_required','sbc','compliant','approved'].every(s=>
        !wsIsForbiddenLabel(wsResolveProvenanceLabel(s,'en'))));
})();

console.log('\n== §86 — TEST I: UNKNOWN VALUES STAY UNKNOWN ==');
(function(){
  const p=PR('villa'); const arch=ARCH(p);
  const m=wsInspectorModel(p,'bld_0.g.majlis.door_0',arch,null,null,'en');
  chk('the door inspects', m.valid===true);
  const all=(m.sections.GEOMETRY||[]).concat(m.sections.PROPERTIES||[]);
  const clear=all.filter(f=>f.field==='opening.clear_width_m')[0];
  chk('a door with no clear width exposes the field', !!clear);
  chk('the clear width is classified UNKNOWN', clear.editability==='UNKNOWN');
  chk('the clear width displays as Not specified in English',
      clear.display.text==='Not specified'&&clear.display.known===false);
  const ar=wsInspectorModel(p,'bld_0.g.majlis.door_0',arch,null,null,'ar');
  const clearAr=(ar.sections.GEOMETRY||[]).concat(ar.sections.PROPERTIES||[])
    .filter(f=>f.field==='opening.clear_width_m')[0];
  chk('the clear width displays as غير محدد in Arabic',
      clearAr.display.text==='غير محدد');
  chk('an unknown value is never shown as zero',
      clear.display.text!=='0'&&clear.display.raw===null);
  chk('an unknown value is never shown as a default or an estimate',
      !/default|estimated|assumed|typical/i.test(clear.display.text));
  chk('every unknown field in the whole inspector behaves the same',
      all.filter(f=>f.editability==='UNKNOWN').every(f=>
        f.display.known===false&&f.display.raw===null
        &&(f.display.text==='Not specified'||f.display.text==='غير محدد')));
  chk('a known value is still shown as its real value',
      all.filter(f=>f.field==='opening.width_m')[0].display.known===true);
  chk('display formatting never rewrites the stored value', (function(){
    const before=JSON.stringify(p.model);
    wsInspectorModel(p,'bld_0.g.majlis.door_0',arch,null,null,'ar');
    wsDisplayValue(0.9000004,'EDITABLE','en');
    return JSON.stringify(p.model)===before; })());
})();

console.log('\n== §65/§66 — NUMBERS AND UNITS ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  chk('the canonical unit is the metre', WS_CANONICAL_UNIT==='METRIC_M');
  const m=wsConvertDisplay(2.5,'METRIC_CM');
  chk('a display conversion produces a converted value', m.value===250&&m.converted);
  chk('a display conversion keeps the canonical value beside it', m.canonical_m===2.5);
  chk('a display conversion never writes to the model',
      m.writes_to_model===false&&wsModelHashOf(p)===H);
  chk('the metre conversion is the identity',
      wsConvertDisplay(2.5,'METRIC_M').converted===false);
  chk('an unknown unit converts nothing',
      wsConvertDisplay(2.5,'PARSEC').value===null);
  chk('display rounding does not alter the underlying precision', (function(){
    const d=wsDisplayValue(4.123456789,'EDITABLE','en');
    return d.text==='4.12'&&d.raw===4.123456789; })());
})();

console.log('\n== §24/§25 — ISSUE CENTER KEEPS CATEGORIES APART ==');
(function(){
  const p=auCreateProject(C(MEPF.clash_mep),'bld_0','IMPORT',null);
  const arch=ARCH(p);
  const st=compileStructure(C(p.model),'bld_0',null,0,arch);
  const mep=compileMep(C(p.model),'bld_0',null,0,arch);
  const fls=compileFls(C(p.model),'bld_0',null,0,arch,mep);
  const co=compileCoordination(C(p.model),'bld_0',null,0,arch,st,mep,fls,null);
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const rs=compileRuntimeScene(vs,null);
  const ic=wsIssueCenter(p,arch,co,rs,null,'bld_0');
  chk('every declared category exists in the result',
      WS_ISSUE_CATEGORIES.every(c=>Array.isArray(ic.categories[c])));
  chk('coordination findings land in the coordination category',
      ic.categories.COORDINATION.length>0);
  chk('coordination findings are not merged into model integrity',
      ic.categories.MODEL_INTEGRITY.every(i=>i.code!=='HARD_CLASH'));
  chk('each category has its own counts',
      WS_ISSUE_CATEGORIES.every(c=>typeof ic.counts[c].total==='number'));
  chk('the counts per severity are separate',
      WS_ISSUE_CATEGORIES.every(c=>WS_ISSUE_SEVERITIES.every(s=>
        typeof ic.counts[c][s]==='number')));
  chk('the total equals the sum of the categories',
      ic.total===WS_ISSUE_CATEGORIES.reduce((s,c)=>s+ic.categories[c].length,0));
  chk('every issue carries a declared severity',
      WS_ISSUE_CATEGORIES.every(c=>ic.categories[c].every(i=>
        WS_ISSUE_SEVERITIES.indexOf(i.severity)>=0)));
  chk('regulatory status is a separate axis from severity',
      ic.rule_evaluation_status==='NOT_EVALUATED'&&ic.compliance==='NOT_EVALUATED');
  chk('a rule result keeps its own status vocabulary', (function(){
    const withRules=wsIssueCenter(p,arch,co,rs,
      [{rule_id:'R1',status:'INSUFFICIENT_DATA',note:'n',targets:[]}],'bld_0');
    return withRules.categories.RULE_EVALUATION[0].rule_status==='INSUFFICIENT_DATA'; })());
  chk('an unknown rule status falls back to NOT_EVALUATED, never to PASS', (function(){
    const withRules=wsIssueCenter(p,arch,co,rs,
      [{rule_id:'R2',status:'DEFINITELY_FINE',note:'n',targets:[]}],'bld_0');
    return withRules.categories.RULE_EVALUATION[0].rule_status==='NOT_EVALUATED'; })());
  /* الكلمات الممنوعة ترد داخل نصّ النفي نفسه، فالفحص يقرأ الحقول لا النصّ الخام */
  const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer'];
  const scanFields=(root,re)=>{ const hits=[];
    const walk=(v,p)=>{ if(Array.isArray(v)) return v.forEach((x,i)=>walk(x,p+'['+i+']'));
      if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
        if(NOTE_KEYS.indexOf(k)>=0) return;
        if(re.test(k)) hits.push(p+'.'+k);
        if(typeof v[k]==='string'&&re.test(v[k])) hits.push(p+'.'+k+'="'+v[k]+'"');
        walk(v[k],p+'.'+k); }); };
    walk(root,''); return hits; };
  const STATUS_RE=new RegExp(WS_FORBIDDEN_STATUS.map(w=>
    String(w).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|'),'i');
  chk('no status field or value claims safety or compliance', (function(){
    const hits=scanFields(ic,STATUS_RE);
    if(hits.length) console.log('     hits:',JSON.stringify(hits.slice(0,3)));
    return hits.length===0; })());
  chk('the only mention of those words is the explicit denial',
      /no status here means safe, compliant or approved/.test(ic.note));
  chk('the forbidden status probe is not vacuous',
      scanFields({status:'COMPLIANT'},STATUS_RE).length>0
      &&scanFields({verdict:'APPROVED'},STATUS_RE).length>0);
  chk('reading issues writes nothing', ic.writes_to_model===false);
})();

console.log('\n== §26 — ISSUE TO MODEL NAVIGATION ==');
(function(){
  const p=auCreateProject(C(MEPF.clash_mep),'bld_0','IMPORT',null);
  const arch=ARCH(p);
  const st=compileStructure(C(p.model),'bld_0',null,0,arch);
  const mep=compileMep(C(p.model),'bld_0',null,0,arch);
  const fls=compileFls(C(p.model),'bld_0',null,0,arch,mep);
  const co=compileCoordination(C(p.model),'bld_0',null,0,arch,st,mep,fls,null);
  const ic=wsIssueCenter(p,arch,co,null,null,'bld_0');
  const clash=ic.categories.COORDINATION[0];
  const tg=wsIssueTargets(clash);
  chk('a coordination issue names both elements', tg.targets.length===2);
  chk('a coordination issue is focusable', tg.focusable===true);
  chk('focusing writes nothing', tg.writes_to_model===false);
  const noTarget=wsIssueTargets({code:'X',targets:[]});
  chk('an issue with no geometric target says it is not focusable',
      noTarget.focusable===false);
  chk('a clash records which two disciplines meet',
      Array.isArray(clash.discipline_pair)&&clash.discipline_pair.length===2);
  const H=p.model_hash;
  wsIssueTargets(clash);
  chk('reading targets leaves the model hash unchanged', wsModelHashOf(p)===H);
})();

console.log('\n──────────────────────────────────────────────');
console.log('WORKSPACE CONTRACT: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
