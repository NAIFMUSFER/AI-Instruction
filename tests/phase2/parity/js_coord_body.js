const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_coord.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'coord_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const s=compileCoordination(m,q.bid,q.pos,q.rot,null,null,null,null,AT);
  if(JSON.stringify(m)!==before) throw new Error('detector mutated the model: '+q.n);
  out[q.n]={snapshot:s, summary:coordSummary(s), rule_inputs:coordRuleInputs(s),
    export:coordExportSnapshot(s),
    check:checkCoordSnapshot(s,C(S.models[q.m]),q.bid)};
});
S.projects.forEach(pr=>{
  const ents=pr.entries.map(e=>({id:e.id,building:C(S.models[e.model]),
    position:e.pos,rotation_deg:e.rot}));
  const s=compileProjectCoordination(ents,AT);
  out['project:'+pr.n]={snapshot:s, summary:coordSummary(s),
    check:checkProjectSnapshot(s,ents),
    moved:checkProjectSnapshot(s,ents.map(e=>({id:e.id,building:e.building,
      position:{x:((e.position||{}).x||0)+5,z:((e.position||{}).z||0)},
      rotation_deg:e.rotation_deg})))};
});
const A=compileCoordination(C(S.models.A_duct_through_beam),'bld_0',null,0,null,null,null,null,AT);
const H=compileCoordination(C(S.models.H_beam_removed),'bld_0',null,0,null,null,null,null,
  '2026-01-02T00:00:00Z');
out['__ops__']={reconcile:coordReconcile(A,H),
  reconcile_reverse:coordReconcile(H,A),
  byId:coordClashById(A,A.clashes[0].id), none:coordClashById(A,'nope'),
  debug:coordDebugView(A,A.clashes[0].id), debug_missing:coordDebugView(A,'nope'),
  filter_pair:coordFilterClashes(A,{discipline_a:'MEP',discipline_b:'STRUCTURE'}),
  filter_level:coordFilterClashes(A,{level_index:1}),
  filter_building:coordFilterClashes(A,{building_id:'bld_0'}).length,
  filter_other_building:coordFilterClashes(A,{building_id:'bld_9'}).length,
  filter_severity:coordFilterClashes(A,{severity:'ERROR'}).length,
  set_open:coordSetStatus(C(A),A.clashes[0].id,'OPEN'),
  set_obsolete:coordSetStatus(C(A),A.clashes[0].id,'OBSOLETE'),
  set_bogus:coordSetStatus(C(A),A.clashes[0].id,'RESOLVED'),
  set_missing:coordSetStatus(C(A),'nope','ACKNOWLEDGED'),
  broad:(function(){ const r=coordBroadPhase([]); return [r[0],r[1]]; })(),
  severity_unknown:coordSeverityOf('NOT_A_TYPE'),
  stale:checkCoordSnapshot(A,C(S.models.B_pipe_through_wall_no_pen),'bld_0')};
const ack=C(A);
coordSetStatus(ack,ack.clashes[0].id,'ACKNOWLEDGED','reviewer','2026-01-03','reviewed');
out['__ack__']={snapshot:ack, reconcile:coordReconcile(ack,H)};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js coord scenarios:', Object.keys(out).length);
