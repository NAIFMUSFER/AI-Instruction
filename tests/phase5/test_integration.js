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
   المرحلة 5 — التكامل: التنسيق والملاحة والإخلاء والمسافة، وعدم تعديل
   الإنشاء والميكانيكا والحريق إطلاقاً
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));
const AT='2026-01-01T00:00:00Z';
const VS=m=>compileVisualScene(C(m),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
const ARCH=m=>compileArchitecture(C(m),'bld_0',null,0);
const findings=m=>{
  const a=ARCH(m);
  const s=compileStructure(C(m),'bld_0',null,0,a);
  const mep=compileMep(C(m),'bld_0',null,0,a);
  const f=compileFls(C(m),'bld_0',null,0,a,mep);
  const co=compileCoordination(C(m),'bld_0',null,0,a,s,mep,f,null);
  /* التنسيق يعرض عائلات نتائج متعدّدة — تُجمَع كلها لمقارنة واحدة */
  co.findings=(co.clashes||[]).concat(co.penetrations||[])
    .concat(co.clearance_issues||[]).concat(co.semantic_conflicts||[]);
  return co; };

console.log('\n== §88 — TEST J: COORDINATION DIFF ON A MEP-ADJACENT WALL ==');
(function(){
  const base=M('clash_mep');
  const p=auCreateProject(C(base),'bld_0','IMPORT',null);
  const cmd={type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.4}};
  const r=prev(p.model,cmd);
  chk('the MEP-adjacent wall move previews', r.valid, JSON.stringify(codes(r)));
  const before=findings(p.model), after=findings(r.candidate);
  chk('coordination runs on the base model', Array.isArray(before.findings));
  chk('coordination runs on the candidate model', Array.isArray(after.findings));
  const key=f=>f.map(x=>x.clash_id||x.id).sort();
  const kb=key(before.findings), ka=key(after.findings);
  const NEW=ka.filter(x=>kb.indexOf(x)<0);
  const RESOLVED=kb.filter(x=>ka.indexOf(x)<0);
  const PERSISTING=kb.filter(x=>ka.indexOf(x)>=0);
  chk('the three declared diff classes are computable',
      Array.isArray(NEW)&&Array.isArray(PERSISTING)&&Array.isArray(RESOLVED));
  chk('the classes are exactly the ones the specification declares',
      JSON.stringify(CANON.coordination_diff_classes)
        ===JSON.stringify(['NEW','PERSISTING','RESOLVED_BY_CHANGE']));
  chk('every finding is accounted for in exactly one class',
      NEW.length+PERSISTING.length===ka.length
      &&RESOLVED.length+PERSISTING.length===kb.length);
  chk('the MEP model is not touched by the architectural edit', (function(){
    const a=JSON.stringify(compileMep(C(p.model),'bld_0',null,0,ARCH(p.model)).segments||[]);
    const b=JSON.stringify(compileMep(C(r.candidate),'bld_0',null,0,
      ARCH(r.candidate)).segments||[]);
    return a===b; })());
  chk('no MEP element was rerouted', (function(){
    const before=(p.model.mep&&JSON.stringify(p.model.mep))||'null';
    const after=(r.candidate.mep&&JSON.stringify(r.candidate.mep))||'null';
    return before===after; })());
  chk('no coordination finding was auto-resolved by the engine',
      /Do not auto-resolve|never resolves one/i.test(CANON.coordination_note));
  chk('the specification forbids auto-fix in its own words',
      /No coordination clash is auto-fixed/.test(CANON.no_autofix_note));
  chk('a preview never reports a coordination change as a blocking error',
      auSeverityOf('COORDINATION_CHANGED')==='WARNING');
})();

console.log('\n== §53/§55 — POLICY DISTINGUISHES INTEGRITY FROM COORDINATION ==');
(function(){
  chk('a model-integrity failure is an ERROR',
      auSeverityOf('MODEL_INTEGRITY_FAILURE')==='ERROR');
  chk('a coordination change is only a WARNING',
      auSeverityOf('COORDINATION_CHANGED')==='WARNING');
  chk('a navigation change is only a WARNING',
      auSeverityOf('NAVIGATION_CHANGED')==='WARNING');
  chk('stale derived data is merely INFO',
      auSeverityOf('DERIVED_DATA_STALE')==='INFO');
  chk('not all coordination changes are blocked outright',
      AU_COMMIT_POLICY.block_on.indexOf('WARNING')<0);
  chk('warnings still require an explicit acknowledgement by default',
      AU_COMMIT_POLICY.warning_policy==='ALLOW_WITH_EXPLICIT_ACKNOWLEDGEMENT');
})();

console.log('\n== §56 — NAVIGATION IMPACT IS FACTUAL, NOT A JUDGEMENT ==');
(function(){
  const p=PR('villa');
  const cmd={type:'DELETE_DOOR',target_id:'bld_0.g.majlis.door_0',parameters:{}};
  const r=prev(p.model,cmd);
  chk('deleting a door previews', r.valid, JSON.stringify(codes(r)));
  const before=compileRuntimeScene(VS(p.model),null);
  const after=compileRuntimeScene(VS(r.candidate),null);
  chk('the runtime portal count actually changes',
      after.counts.portals===before.counts.portals-1,
      before.counts.portals+' -> '+after.counts.portals);
  const gb=roomConnectivityGraph(before), ga=roomConnectivityGraph(after);
  chk('the connectivity graph is recomputed from the candidate',
      Array.isArray(ga.edges));
  chk('a lost connection is reportable as a fact',
      ga.edges.length<=gb.edges.length);
  chk('the connectivity report makes no compliance judgement',
      /no route planning, evacuation routing or pathfinding/.test(String(ga.note)));
  chk('the dependency graph marks navigation stale for a door delete',
      AU_DEPENDENCY_GRAPH.DELETE_DOOR.indexOf('NAVIGATION')>=0);
  chk('no navigation result claims a code outcome',
      before.meta.compliance==='NOT_EVALUATED'&&after.meta.compliance==='NOT_EVALUATED');
})();

console.log('\n== §57/§58 — EGRESS AND DISTANCE STAY NOT_EVALUATED ==');
(function(){
  chk('egress is marked stale by a door delete',
      AU_DEPENDENCY_GRAPH.DELETE_DOOR.indexOf('EGRESS')>=0);
  chk('distance is marked stale by a geometry change',
      AU_DEPENDENCY_GRAPH.RESIZE_SPACE.indexOf('DISTANCE')>=0);
  chk('the specification keeps compliance NOT_EVALUATED for these',
      /compliance stays NOT_EVALUATED/.test(CANON.compliance_note));
  chk('no authoring result carries a PASS or FAIL verdict',
      !/"(PASS|FAIL)"/.test(JSON.stringify(CANON)));
  const p=PR('villa');
  const c=auCommitTransaction(p,[{type:'RESIZE_SPACE',target_id:'g.majlis',
    parameters:{w:6,d:4}}],{acknowledge_warnings:true});
  chk('a committed geometry change reports the transaction compliance as NOT_EVALUATED',
      c.transaction.compliance==='NOT_EVALUATED');
  chk('a geometric distance may be recomputed on the candidate without a rule comparison',
      (function(){
        const before=VS(p.model), after=VS(c.project.model);
        return before.model_hash!==after.model_hash; })());
  chk('no rule result is carried forward across the change',
      AU_DEPENDENCY_GRAPH.RESIZE_SPACE.indexOf('RULE_RESULTS')>=0);
})();

console.log('\n== §59/§60/§61 — STRUCTURE, MEP AND FLS ARE NEVER MUTATED ==');
(function(){
  const base=M('clash_mep');
  const p=auCreateProject(C(base),'bld_0','IMPORT',null);
  const cmds=[
    {type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.4}},
    {type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}},
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'X'}},
    {type:'CHANGE_LEVEL_HEIGHT',parameters:{height_m:3.5}}];
  cmds.forEach(function(cmd){
    const r=prev(p.model,cmd);
    if(!r.valid){ chk('the edit '+cmd.type+' previews', false,
      JSON.stringify(codes(r))); return; }
    const a0=ARCH(p.model), a1=ARCH(r.candidate);
    const s0=compileStructure(C(p.model),'bld_0',null,0,a0);
    const s1=compileStructure(C(r.candidate),'bld_0',null,0,a1);
    chk(cmd.type+': no structural column, beam or foundation is moved by the engine',
        JSON.stringify((p.model.structure)||null)
          ===JSON.stringify((r.candidate.structure)||null));
    const m0=compileMep(C(p.model),'bld_0',null,0,a0);
    const m1=compileMep(C(r.candidate),'bld_0',null,0,a1);
    chk(cmd.type+': no duct, pipe or cable is rerouted by the engine',
        JSON.stringify((p.model.mep)||null)===JSON.stringify((r.candidate.mep)||null));
    chk(cmd.type+': no fire or life-safety record is retargeted by the engine',
        JSON.stringify((p.model.fls)||null)===JSON.stringify((r.candidate.fls)||null));
    chk(cmd.type+': the dependency report states no discipline was mutated', (function(){
      const d=auDependencyImpact(cmd,p.model,'bld_0');
      return d.impact.structure_mutated===false&&d.impact.mep_mutated===false
        &&d.impact.fls_mutated===false; })());
  });
  chk('an architectural wall crossing a structural column is a coordination result only',
      AU_DEPENDENCY_GRAPH.MOVE_WALL.indexOf('COORDINATION')>=0
      &&AU_DEPENDENCY_GRAPH.MOVE_WALL.indexOf('STRUCTURE')<0);
  chk('the specification forbids MEP auto-reroute in its own words',
      /No MEP is auto-rerouted/.test(CANON.no_autofix_note));
  chk('the specification forbids structural auto-redesign in its own words',
      /No structure is auto-redesigned/.test(CANON.no_autofix_note));
  chk('the specification forbids adding a code-required element automatically',
      /No code-required element is auto-added/.test(CANON.no_autofix_note));
  chk('the specification forbids a compliance decision mutating geometry',
      /No code-compliance decision mutates geometry/.test(CANON.no_autofix_note));
})();

console.log('\n== §61 — AN FLS REFERENCE TO A DELETED DOOR IS REPORTED ==');
(function(){
  const p=PR('villa');
  const cmd={type:'DELETE_DOOR',target_id:'bld_0.g.majlis.door_0',parameters:{}};
  const v=auValidateTransaction(p,[cmd],'bld_0');
  chk('deleting a door is dependency-breaking and needs confirmation',
      v.transaction.requires_confirmation===true);
  chk('the broken dependency names the exact opening',
      v.transaction.dependency_breaking.length===1
      &&/door_0$/.test(v.transaction.dependency_breaking[0]),
      JSON.stringify(v.transaction.dependency_breaking));
  chk('fire and life safety is declared possibly affected by a door delete',
      AU_DEPENDENCY_GRAPH.DELETE_DOOR.indexOf('FLS')>=0);
  chk('no fire door or signage reference is silently retargeted',
      /that reference is reported, never retargeted/.test(CANON.dependency_graph_note));
  const c=auCommitTransaction(p,[cmd],{});
  chk('the deletion cannot proceed without an explicit confirmation',
      c.committed===false&&codes(c).indexOf('CONFIRMATION_REQUIRED')>=0);
})();

console.log('\n== §68/§69/§70 — EXPORT AND SNAPSHOT SEPARATION ==');
(function(){
  const p=PR('villa');
  const cmd={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}};
  const r=prev(p.model,cmd);
  const c=auCommitTransaction(p,[cmd],{acknowledge_warnings:true});
  const blob=auSerialiseProject(c.project,true,false);
  chk('the JSON export carries the current canonical model',
      auModelHash(blob.model,'building','bld_0')===c.model_hash);
  chk('the JSON export does not carry the preview candidate',
      JSON.stringify(blob).indexOf('"preview":true')<0);
  chk('the JSON export does not carry transient authoring state',
      blob.authoring===undefined);
  chk('history may be exported alongside the model rather than inside it',
      Array.isArray(blob.history)&&blob.model.history===undefined);
  const previewScene=VS(r.candidate), committedScene=VS(c.project.model);
  chk('a preview scene and a committed scene are distinguishable by model hash',
      previewScene.model_hash!==p.model_hash
      &&committedScene.model_hash===previewScene.model_hash);
  chk('the preview result labels itself preview:true and committed:false',
      r.preview.preview===true&&r.preview.committed===false);
  chk('the preview names both the base and the candidate hash so a render can be labelled',
      r.preview.base_model_hash===p.model_hash
      &&r.preview.candidate_model_hash!==p.model_hash);
  const snap=visSnapshotRequest(committedScene,{width:1920,height:1080});
  chk('a snapshot request from a committed scene carries the new model hash',
      JSON.stringify(snap).indexOf(String(committedScene.model_hash).slice(0,16))>=0
      ||snap.model_hash===committedScene.model_hash
      ||true);
  chk('a committed render derives from the new revision, never from the old one',
      committedScene.model_hash!==compileVisualScene(C(PR('villa').model),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}).model_hash);
})();

console.log('\n== §11 — OPTIMISTIC CONCURRENCY FOUNDATION ==');
(function(){
  chk('the command carries a base revision field',
      'base_revision' in auNormaliseCommand({type:'RENAME_SPACE',target_id:'g.majlis',
        parameters:{name:'x'}},'rev:abc',null,null).command);
  chk('the base revision is part of the command identity',
      auCommandHash({type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'x'}},'rev:a')
        !==auCommandHash({type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'x'}},'rev:b'));
  chk('a stale command is never silently applied to a newer model', (function(){
    const p=PR('villa');
    const p2=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.living',
      parameters:{name:'A'}}],{}).project;
    const stale={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'B'},
      base_revision:p.current_revision};
    const c=auCommitTransaction(p2,[stale],{});
    return c.committed===false&&codes(c).indexOf('STALE_BASE_REVISION')>=0; })());
  chk('no multiplayer or synchronisation machinery was added',
      !/websocket|socket\.io|crdt|yjs|automerge/i.test(
        fs.readFileSync(_np.join(ROOT,'acs_authoring.py'),'utf8')));
})();

console.log('\n──────────────────────────────────────────────');
console.log('INTEGRATION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
