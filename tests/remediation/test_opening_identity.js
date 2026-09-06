/* Runs against the shipped JS in Node and in Playwright-managed Chromium. */
(function(){
  let passed=0,failed=0;
  const check=(name,ok)=>{if(ok){passed++;console.log('  ✓ '+name);}else{failed++;console.log('  ✗ '+name);}};
  const fixture=()=>({site:{w:10,d:10},floor_height:4,wall_h:4,wall_t:0.2,
    levels:[{index:0,template:'g'},{index:1,template:'g'}],floors:{g:{rooms:[
      {id:'r',rect:[0,0,10,10],doors:[{edge:'N',offset:2,width:1,height:2.1},
        {edge:'S',offset:7,width:1,height:2.1}],windows:[
        {edge:'E',offset:2,width:1,height:1,sill:1},{edge:'W',offset:7,width:1,height:1,sill:1}]}]}}});
  const room=m=>m.floors.g.rooms[0];
  const command=(type,target,parameters)=>({type:type,target_id:target,parameters:parameters||{}});
  function commit(p,cmd){
    const v=auValidateTransaction(p,[cmd]);
    const r=auCommitTransaction(p,[cmd],{confirm:v.transaction.confirmation_digest,
      acknowledge_warnings:true,actor_id:'test-user',created_at:'2026-09-06T00:00:00Z'});
    if(!r.committed) throw new Error(JSON.stringify(r.issues));
    return r.project;
  }
  for(const kind of ['DOOR','WINDOW']){
    const p=commit(auCreateProject(fixture()),command('DELETE_'+kind,'bld_0.g.r.'+kind.toLowerCase()+'_0'));
    check(kind+' deleted reference is not retargeted',auResolveTarget(p.model,'bld_0.g.r.'+kind.toLowerCase()+'_0').kind===null);
    check(kind+' survivor keeps its identity',auResolveTarget(p.model,'bld_0.g.r.'+kind.toLowerCase()+'_1').opening_index===0);
  }
  const m=fixture(), geom=JSON.stringify(compileArchitecture(m));
  check('migration records paths',auStabiliseOpeningIds(m).length>0);
  check('migration is idempotent',auStabiliseOpeningIds(m).length===0);
  check('migration leaves compiled geometry unchanged',JSON.stringify(compileArchitecture(m))===geom);
  room(m).doors.reverse();
  check('reorder preserves source identity',auResolveTarget(m,'bld_0.g.r.door_0').opening_index===1);
  check('valid template instance resolves',auResolveTarget(m,'bld_0.g.r.door_1@1').opening_index===0);
  check('invalid template instance rejected',auResolveTarget(m,'bld_0.g.r.door_1@99').kind===null);
  check('distance lookup survives reorder',_viaDoor('bld_0.g.r.door_0',_dsRooms(m,'bld_0'))[1]===1);
  for(const id of ['bld_0.g.r.door_0','bld_0.g.r','bld_0.flr_0','__proto__']){
    const bad=fixture();room(bad).windows[0].id=id;
    check('duplicate/reserved rejected: '+id,auOpeningIdentityIssues(bad).some(i=>i.code==='ID_COLLISION'));
  }
  for(const id of [null,'',[],12,'door@0','door\nscript','x'.repeat(257),'<svg/onload=1>']){
    const bad=fixture();room(bad).doors[0].id=id;
    check('invalid identity rejected',auOpeningIdentityIssues(bad).length>0);
  }
  const missing=fixture();auStabiliseOpeningIds(missing);delete room(missing).doors[0].id;
  check('missing migrated ID rejected',auOpeningIdentityIssues(missing).length>0);
  const invalidProject=auCreateProject(missing);
  check('import rejects broken migrated identity',!auLoadProject(auSerialiseProject(invalidProject)).valid);
  check('export rejects broken migrated identity',!bxBuildExchange(invalidProject).valid);
  check('missing distance reference is not a legacy door',
    _viaDoor(undefined,{r:{doors:[{edge:'N'}]}})[0]===null);
  const locked=fixture();auStabiliseOpeningIds(locked);
  locked._authoring_locks={'bld_0.g.r.door_1':{reason:'USER_LOCKED'}};
  const lockResult=auPreviewCommand(locked,command('MOVE_DOOR','bld_0.g.r.door_1@0',{offset:6}));
  check('level suffix cannot bypass source lock',!lockResult.valid&&lockResult.issues.some(i=>i.code==='TARGET_LOCKED'));

  const p=auCreateProject(fixture()), before=JSON.stringify(p);
  const first=commit(p,command('DELETE_DOOR','bld_0.g.r.door_0'));
  check('original project/history preserved',JSON.stringify(p)===before);
  check('migration belongs to same revision',first.audit_log[0].changed_paths.includes('_opening_identity'));
  const added=commit(first,command('ADD_DOOR','bld_0.g.r',{edge:'E',offset:4,width:1,height:2.1}));
  const aid=room(added.model).doors.slice(-1)[0].id;
  const moved=commit(added,command('MOVE_DOOR',aid,{edge:'E',offset:5}));
  const undone=auUndo(moved).project, redone=auRedo(undone).project;
  const loaded=auLoadProject(JSON.parse(JSON.stringify(auSerialiseProject(redone,true,true)))).project;
  check('save/undo/redo retain new ID',room(loaded.model).doors.slice(-1)[0].id===aid);
  check('redo restores geometry',room(loaded.model).doors.slice(-1)[0].offset===5);
  const arch=compileArchitecture(loaded.model), exchange=bxBuildExchange(loaded).exchange;
  check('compiler retains source reference',arch.openings.some(o=>o.opening_ref===aid));
  check('exchange retains instance ID',exchange.doors.some(o=>o.canonical_id===aid+'@0'));
  const again=commit(commit(loaded,command('DELETE_DOOR',aid)),command('ADD_DOOR','bld_0.g.r',{edge:'E',offset:4,width:1,height:2.1}));
  check('new ID not reused after deletion',room(again.model).doors.slice(-1)[0].id!==aid);
  const relations=_wsRelationships(loaded.model,auResolveTarget(loaded.model,aid),arch,'bld_0');
  check('inspector resolves exact opening host',relations.find(r=>r.relation==='HOSTED_BY_WALL').target_id===
    arch.openings.find(o=>o.opening_ref===aid).host_wall_id);
  const out={model:loaded.model,hash:loaded.model_hash,history:loaded.history,audit:loaded.audit_log,
    arch:arch,tree:wsProjectTree(loaded,arch,null,'en'),exchange:exchange,
    relationships:buildRelationships(loaded.model),
    deleted:auResolveTarget(loaded.model,'bld_0.g.r.door_0'),
    surviving:auResolveTarget(loaded.model,'bld_0.g.r.door_1'),new_id:aid};
  if(typeof document==='undefined'&&process.env.ACS_OPENING_IDENTITY_PARITY)
    require('fs').writeFileSync(process.env.ACS_OPENING_IDENTITY_PARITY,JSON.stringify(out));
  console.log('OPENING IDENTITY: '+passed+' passed, '+failed+' failed');
  if(typeof document!=='undefined') console.log('OPENING IDENTITY: executed in browser');
  if(failed) process.exit(1);
})();
