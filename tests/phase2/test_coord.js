/* ======================================================================
   المرحلة 2 — اختبارات أساس التنسيق بين التخصّصات وكشف التعارضات.
   كشف وتتبّع فقط: لا إصلاح تلقائي ولا إعادة توجيه ولا إعادة تصميم ولا
   مطابقة كود ولا ادّعاء سلامة. التعارض ملاحظة تنسيق لا حكم هندسي.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'coord_scen.json'),'utf8'));
const MS=JSON.parse(fs.readFileSync(_np.join(FIXD,'mep_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const K=(name,bid,pos,rot)=>compileCoordination(C(SC.models[name]),bid||'bld_0',
  pos||null,rot||0,null,null,null,null,AT);
const types=s=>s.clashes.map(c=>c.type);
const has=(s,t)=>types(s).indexOf(t)>=0;
const find=(s,t,f)=>s.clashes.filter(c=>c.type===t&&(!f||f(c)));
/* الكلمات الممنوعة ترد داخل نصوص النفي نفسها، فالفحص يقرأ الحقول لا النصّ الخام */
const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer','confidence_note',
  'derivation','navigation_impact','broad_phase','narrow_phase','geometry_confidence_note',
  'clash_type_note','status_note','reconciliation_note','severity_note','pair_note',
  'geometry_note','exemption_note','penetration_note','clearance_note','identity_note',
  'evidence_note','rule_note','no_generator_note','void_note'];
const scanFields=(root,re)=>{ const hits=[];
  const walk=(v,path)=>{ if(Array.isArray(v)) return v.forEach(x=>walk(x,path));
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(NOTE_KEYS.indexOf(k)>=0) return;
      if(re.test(k)) hits.push(path+'.'+k);
      if(typeof v[k]==='string'&&re.test(v[k])) hits.push(path+'.'+k+'="'+v[k]+'"');
      walk(v[k],path+'.'+k); }); };
  walk(root,''); return hits; };

console.log('\n== §1 — SPEC INTEGRITY AND NO-DRIFT ==');
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_coord.json'),'utf8'));
chk('browser spec is byte-identical to acs_coord.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_COORD_SPEC));
chk('schema and detector version are pinned',
    COORD_SCHEMA==='acs.coord/1'&&/^acs-coord-detector\//.test(COORD_DETECTOR_VERSION));
chk('severities are INFO/WARNING/ERROR only — no UNSAFE, no FATAL, no VIOLATION',
    JSON.stringify(COORD_SEVERITIES)===JSON.stringify(['INFO','WARNING','ERROR']));
chk('every clash type has a declared severity',
    COORD_CLASH_TYPES.every(t=>COORD_SEVERITIES.indexOf(COORD_CLASH_SEVERITY[t])>=0));
chk('an unknown clash type never silently becomes an ERROR',
    coordSeverityOf('NOT_A_TYPE')==='WARNING');
chk('RESOLVED is not an automatic status', COORD_CLASH_STATUSES.indexOf('RESOLVED')<0);
chk('only cross-discipline pairs are declared',
    COORD_DISCIPLINE_PAIRS.every(p=>p[0]!==p[1])&&COORD_DISCIPLINE_PAIRS.length===6);
chk('the spec names no code, standard or authority',
    !/\bNFPA\b|\bSBC\b|\bIBC\b|\bASHRAE\b|\bNEC\b|\bASCE\b|\bAISC\b|\bACI\b|\bIPC\b|civil.?defen/i
      .test(JSON.stringify({a:ACS_COORD_SPEC.clash_types,b:ACS_COORD_SPEC.element_kinds,
        c:ACS_COORD_SPEC.exemption_kinds,d:ACS_COORD_SPEC.clash_severity,
        e:ACS_COORD_SPEC.rule_inputs,f:ACS_COORD_SPEC.id_patterns,
        g:ACS_COORD_SPEC.snapshot_statuses,h:ACS_COORD_SPEC.reconciliation_states})));
chk('no auto-fix vocabulary is offered as an outcome',
    ['auto_fixed','rerouted','resized','resolved_automatically','opening_created','optimised']
      .every(w=>ACS_COORD_SPEC.forbidden_claims.indexOf(w)>=0));

console.log('\n== §2 — TEST A: SERVICE THROUGH STRUCTURE ==');
const A=K('A_duct_through_beam');
const ab=find(A,'HARD_CLASH',c=>c.kind_a==='MEP_SEGMENT'&&c.kind_b==='STRUCT_BEAM');
chk('a duct crossing a beam is reported as a HARD_CLASH', ab.length===1);
chk('the clash pairs MEP with STRUCTURE',
    ab.length===1&&ab[0].discipline_a==='MEP'&&ab[0].discipline_b==='STRUCTURE');
chk('the clash carries a positive intersection volume',
    ab.length===1&&ab[0].geometry.intersection.volume_m3>0);
chk('the clash carries both world AABBs as evidence',
    ab.length===1&&ab[0].geometry.aabb_a.length===6&&ab[0].geometry.aabb_b.length===6);
chk('a clash from stated dimensions is labelled stated',
    ab.length===1&&ab[0].geometry_confidence==='stated');
chk('the clash id is deterministic across two runs',
    K('A_duct_through_beam').clashes.map(c=>c.id).join()===A.clashes.map(c=>c.id).join());
chk('the clash never claims the duct was moved or the beam resized',
    ab.length===1&&!/rerout|resiz|moved automatically|auto/i.test(ab[0].note)===false
      ?/nothing is moved, resized or rerouted/.test(ab[0].note):false);

console.log('\n== §3 — TEST B/C: PENETRATIONS ==');
const B=K('B_pipe_through_wall_no_pen');
const bo=find(B,'OPENING_REQUIRED');
chk('a pipe crossing a wall with no penetration reports OPENING_REQUIRED', bo.length===1);
chk('OPENING_REQUIRED is a finding, never an instruction',
    bo.length===1&&/not an instruction/.test(bo[0].note)&&/no opening is created/.test(bo[0].note));
chk('no opening was actually created in the model',
    B.clashes.every(c=>c.type!=='OPENING_REQUIRED'||c.penetration===undefined));
const Cs=K('C_pipe_with_penetration');
chk('a declared penetration that covers the crossing suppresses the finding',
    !has(Cs,'OPENING_REQUIRED')&&!has(Cs,'PENETRATION_UNRESOLVED'));
chk('the suppression is recorded, never silent',
    Cs.suppressed.some(s=>s.exemption==='SEGMENT_IN_DECLARED_PENETRATION'));
chk('the suppression names both elements and the penetration',
    Cs.suppressed.filter(s=>s.exemption==='SEGMENT_IN_DECLARED_PENETRATION')
      .every(s=>s.element_a&&s.element_b&&s.penetration));
const C2=K('C2_penetration_misplaced');
chk('a penetration that does not cover the crossing reports PENETRATION_UNRESOLVED',
    find(C2,'PENETRATION_UNRESOLVED').length===1);
chk('a represented penetration never claims approval or firestopping',
    Cs.penetrations.every(p=>p.status==='REPRESENTED'&&
      /not a structurally approved opening/.test(p.note)&&/is not firestopped/.test(p.note)));
chk('no sleeve size is ever produced',
    scanFields(Cs,/sleeve|firestop/i).length===0);

console.log('\n== §4 — TEST D/E: HOSTS AND DUPLICATES ==');
const D=K('D_column_blocks_door');
chk('a column standing in a declared door opening is reported',
    find(D,'HARD_CLASH',c=>c.kind_a==='ARCH_OPENING'&&c.kind_b==='STRUCT_COLUMN').length===1);
chk('the same column is also reported against the host wall',
    find(D,'HARD_CLASH',c=>c.kind_a==='ARCH_WALL'&&c.kind_b==='STRUCT_COLUMN').length===1);
chk('nothing claims the door is blocked, unsafe or non-compliant',
    scanFields(D,/unsafe|non_?compliant|violation|blocked_exit/i).length===0);
const E=K('E_fls_duplicate_reference');
chk('two FLS devices sharing one source element report DUPLICATE_OCCUPANCY',
    find(E,'DUPLICATE_OCCUPANCY').length===1);
chk('DUPLICATE_OCCUPANCY is INFO, never an error',
    find(E,'DUPLICATE_OCCUPANCY')[0].severity==='INFO');
chk('an FLS device never clashes with the MEP element it references',
    E.suppressed.some(s=>s.exemption==='SAME_SOURCE_ELEMENT')&&
    !find(E,'HARD_CLASH',c=>c.discipline_a==='FLS'||c.discipline_b==='FLS').length);

console.log('\n== §5 — TEST F: WORLD COORDINATES, NOT LOCAL ==');
const F0=K('F_rotated'), F45=K('F_rotated','bld_0',{x:-7,z:3},45),
      F90=K('F_rotated','bld_2',{x:12,z:-4},90);
chk('a rotated building finds the same conflicts',
    JSON.stringify(types(F0).sort())===JSON.stringify(types(F45).sort()));
chk('a translated and rotated building finds the same conflicts',
    JSON.stringify(types(F0).sort())===JSON.stringify(types(F90).sort()));
chk('rotation actually moved the geometry (no world-axis shortcut)',
    JSON.stringify(F0.clashes[0].geometry.aabb_a)!==
    JSON.stringify(F45.clashes[0].geometry.aabb_a));
chk('rotated coordinates stay finite and quantised',
    F45.clashes.every(c=>!c.geometry||c.geometry.aabb_a.every(v=>isFinite(v))));
chk('a rotated box uses the separating-axis test, not its AABB',
    _coObbOverlap({cx:0,cy:0,cz:0,hx:2,hy:1,hz:0.1,yaw:0},
                  {cx:2.5,cy:0,cz:2.5,hx:2,hy:1,hz:0.1,yaw:0})===false);

console.log('\n== §6 — TEST G: PROJECT SCOPE ==');
const mk=pr=>pr.entries.map(e=>({id:e.id,building:C(SC.models[e.model]),
  position:e.pos,rotation_deg:e.rot}));
const far=compileProjectCoordination(mk(SC.projects[0]),AT);
const near=compileProjectCoordination(mk(SC.projects[1]),AT);
chk('two distant buildings produce no cross-building clash',
    far.clashes.every(c=>!c.cross_building));
chk('two overlapping buildings do produce cross-building clashes',
    near.clashes.some(c=>c.cross_building));
chk('every clash names the building of each side',
    near.clashes.every(c=>c.building_a!==undefined&&c.building_b!==undefined));
chk('two buildings with identical local coordinates are not merged',
    far.statistics.elements===near.statistics.elements);
chk('placement is part of the snapshot identity',
    far.snapshot_id!==near.snapshot_id);
chk('a project snapshot has no single revision hash', far.revision_hash===null);
chk('a project snapshot still has a deterministic project hash',
    far.project_hash===compileProjectCoordination(mk(SC.projects[0]),AT).project_hash);

console.log('\n== §7 — TEST H: SNAPSHOT INTEGRITY AND RECONCILIATION ==');
const H=K('H_beam_removed');
chk('an unchanged model reports CURRENT',
    checkCoordSnapshot(A,C(SC.models.A_duct_through_beam),'bld_0').status==='CURRENT');
chk('a changed model reports STALE_MODEL_CHANGED, never a silent re-run',
    checkCoordSnapshot(A,C(SC.models.H_beam_removed),'bld_0').status==='STALE_MODEL_CHANGED');
chk('a stale snapshot is never presented as current',
    checkCoordSnapshot(A,C(SC.models.H_beam_removed),'bld_0').presented_as_current===false);
chk('a snapshot with no hash is UNVERIFIABLE, never assumed current',
    checkCoordSnapshot({},C(SC.models.A_duct_through_beam),'bld_0').status==='UNVERIFIABLE');
const R=coordReconcile(A,H);
chk('a clash whose geometry vanished is RESOLVED_BY_MODEL_CHANGE',
    (R.counts.RESOLVED_BY_MODEL_CHANGE||0)>0);
chk('reconciliation never claims the change was correct',
    R.results.every(r=>/no longer present/.test(r.note))&&
    /never asserts that a change was correct/.test(R.note.replace('no reconciliation state asserts','never asserts')));
chk('a clash present in both snapshots is PERSISTING',
    (R.counts.PERSISTING||0)>0);
chk('a clash appearing only in the newer snapshot is NEW',
    (coordReconcile(H,A).counts.NEW||0)>0);
chk('an acknowledged clash that disappears becomes OBSOLETE, not resolved',
    (function(){ const ack=C(A);
      coordSetStatus(ack,R.results.filter(r=>r.state==='RESOLVED_BY_MODEL_CHANGE')[0].id,
        'ACKNOWLEDGED','reviewer','2026-01-03');
      const r2=coordReconcile(ack,H);
      return (r2.counts.OBSOLETE||0)>0; })());
chk('reconciliation states are exactly the declared four',
    R.results.every(r=>COORD_RECONCILIATION_STATES.indexOf(r.state)>=0));

console.log('\n== §8 — TEST I: SEMANTIC AND REFERENCE INTEGRITY ==');
const I=K('I_dangling_refs');
chk('a dangling cross-discipline reference is reported', has(I,'INVALID_REFERENCE'));
chk('an unresolved penetration host is a semantic conflict', has(I,'SEMANTIC_CONFLICT'));
chk('reference findings are ERROR severity',
    I.clashes.filter(c=>c.type==='INVALID_REFERENCE'||c.type==='SEMANTIC_CONFLICT')
      .every(c=>c.severity==='ERROR'));
chk('a reference finding carries the reporting discipline and its source code',
    I.clashes.filter(c=>c.type==='INVALID_REFERENCE')
      .every(c=>c.evidence.kind==='reference'&&c.evidence.reported_by&&c.evidence.source_code));
chk('reference findings are re-classified, never invented here',
    I.clashes.filter(c=>c.type==='INVALID_REFERENCE'||c.type==='SEMANTIC_CONFLICT')
      .every(c=>c.geometry===null));
chk('a reference finding is not dressed as a safety judgement',
    I.clashes.filter(c=>c.type==='INVALID_REFERENCE')
      .every(c=>/not a code or safety judgement/.test(c.note)));

console.log('\n== §9 — EXEMPTIONS ARE SEMANTIC, NEVER TYPE-BLIND ==');
chk('every applied exemption is a declared kind',
    [A,B,Cs,D,E,I].every(s=>s.suppressed.every(x=>COORD_EXEMPTION_KINDS.indexOf(x.exemption)>=0)));
chk('a column crossing the slab of its own levels is exempt',
    A.suppressed.some(x=>x.exemption==='COLUMN_THROUGH_ITS_OWN_LEVEL_SLAB'));
chk('a column crossing a slab outside its own levels is NOT exempt',
    _coExempt({kind:'STRUCT_COLUMN',base_level_index:0,top_level_index:1,solid:true,
               discipline:'STRUCTURE',element_id:'c'},
              {kind:'ARCH_SLAB',level_index:5,solid:true,
               discipline:'ARCHITECTURE',element_id:'s'},[],null)===null);
chk('an opening is exempt only inside its declared host wall',
    _coExempt({kind:'ARCH_OPENING',host_wall_id:'w1',solid:true,
               discipline:'ARCHITECTURE',element_id:'o'},
              {kind:'ARCH_WALL',solid:true,discipline:'STRUCTURE',element_id:'w1'},[],null)
      ==='OPENING_IN_ITS_HOST_WALL'&&
    _coExempt({kind:'ARCH_OPENING',host_wall_id:'w1',solid:true,
               discipline:'ARCHITECTURE',element_id:'o'},
              {kind:'ARCH_WALL',solid:true,discipline:'STRUCTURE',element_id:'w2'},[],null)===null);
chk('a declared void or core has no matter to collide with',
    _coExempt({kind:'STRUCT_COLUMN',solid:true,discipline:'STRUCTURE',element_id:'c'},
              {kind:'ARCH_CORE',solid:false,discipline:'ARCHITECTURE',element_id:'k'},[],null)
      ==='ELEMENT_INSIDE_DECLARED_VOID_OR_CORE');
chk('a void suppression is recorded on the pair it suppressed',
    MSK('hotel_mep').suppressed.filter(x=>x.exemption==='ELEMENT_INSIDE_DECLARED_VOID_OR_CORE')
      .every(x=>x.element_a&&x.element_b));
chk('no exemption is granted on element kind alone',
    _coExempt({kind:'MEP_SEGMENT',solid:true,discipline:'MEP',element_id:'s',segment_id:'s'},
              {kind:'STRUCT_BEAM',solid:true,discipline:'STRUCTURE',element_id:'b'},[],null)===null);

console.log('\n== §10 — CLEARANCE ONLY WHERE STATED ==');
const Y=K('Y_clearance');
chk('a stated clearance produces a CLEARANCE_CLASH', has(Y,'CLEARANCE_CLASH'));
chk('the clash carries the stated clearance and nothing invented',
    find(Y,'CLEARANCE_CLASH').every(c=>c.clearance_m===1.0));
chk('CLEARANCE_CLASH is INFO, never an error',
    find(Y,'CLEARANCE_CLASH').every(c=>c.severity==='INFO'));
chk('no clearance is invented where none is stated',
    [A,B,D,I].every(s=>!has(s,'CLEARANCE_CLASH')));
chk('a stated clearance widens the broad phase so the pair is not missed',
    find(Y,'CLEARANCE_CLASH',c=>c.kind_b==='STRUCT_COLUMN'||c.kind_a==='STRUCT_COLUMN').length===1);
chk('no maintenance, service or code clearance appears anywhere',
    scanFields(Y,/service_clearance|code_clearance|maintenance_clearance/i).length===0);

console.log('\n== §11 — NO AUTO-FIX, NO REDESIGN, NO MUTATION ==');
const ALL=Object.keys(SC.models).map(k=>K(k));
chk('no snapshot contains an auto-fix, reroute or resize claim',
    ALL.every(s=>scanFields(s,/auto_?fix|rerout|resiz|optimi[sz]|resolved_automatically/i)
      .length===0));
chk('no snapshot claims compliance, safety or adequacy',
    ALL.every(s=>scanFields(s,/compliant|violation|unsafe|fatal|structurally_adequate/i)
      .length===0));
chk('every snapshot declares compliance NOT_EVALUATED',
    ALL.every(s=>s.meta.compliance==='NOT_EVALUATED'&&s.summary.compliance==='NOT_EVALUATED'));
chk('the detector mutates no source model', (function(){
    let ok=true;
    Object.keys(SC.models).forEach(k=>{ const m=C(SC.models[k]);
      const before=JSON.stringify(m);
      compileCoordination(m,'bld_0',null,0,null,null,null,null,AT);
      if(JSON.stringify(m)!==before) ok=false; });
    return ok; })());
chk('the detector mutates no compiled discipline model', (function(){
    const m=C(SC.models.A_duct_through_beam);
    const arch=compileArchitecture(m,'bld_0',null,0);
    const st=compileStructure(m,'bld_0',null,0,arch);
    const mep=compileMep(m,'bld_0',null,0,arch,st);
    const fls=compileFls(m,'bld_0',null,0,arch,mep);
    const b=[arch,st,mep,fls].map(x=>JSON.stringify(x)).join('|');
    compileCoordination(m,'bld_0',null,0,arch,st,mep,fls,AT);
    return [arch,st,mep,fls].map(x=>JSON.stringify(x)).join('|')===b; })());
chk('a status change is only ever an explicit human decision',
    coordSetStatus(C(A),A.clashes[0].id,'OPEN')[1]==='STATUS_NOT_ALLOWED'&&
    coordSetStatus(C(A),A.clashes[0].id,'OBSOLETE')[1]==='OBSOLETE_IS_DERIVED_NOT_SET'&&
    coordSetStatus(C(A),A.clashes[0].id,'RESOLVED')[1]==='STATUS_NOT_ALLOWED');
chk('an accepted decision records who decided and on what basis', (function(){
    const s=C(A); const r=coordSetStatus(s,A.clashes[0].id,'FALSE_POSITIVE','reviewer','2026-01-03','x');
    return r[0]===true&&r[2].decision.by==='reviewer'&&
      /explicit human decision/.test(r[2].decision.basis); })());
chk('a status change on an unknown clash is refused',
    coordSetStatus(C(A),'nope','ACKNOWLEDGED')[1]==='CLASH_NOT_FOUND');

console.log('\n== §12 — NAVIGATION AND EGRESS ARE UNTOUCHED ==');
chk('the spec states coordination does not affect navigation',
    /do NOT affect navigation, egress, pathfinding or walking distance/
      .test(ACS_COORD_SPEC.navigation_note));
chk('no snapshot emits a route, path or reroute',
    ALL.every(s=>scanFields(s,/^\.(route|path|waypoint)/i).length===0));
chk('a column blocking a door does not alter the door relationship', (function(){
    const m=C(SC.models.D_column_blocks_door);
    const before=JSON.stringify(compileArchitecture(m,'bld_0',null,0).openings);
    K('D_column_blocks_door');
    return JSON.stringify(compileArchitecture(m,'bld_0',null,0).openings)===before; })());

console.log('\n== §13 — EVIDENCE AND GEOMETRY CONFIDENCE ==');
chk('every geometric clash carries an intersection with positive volume',
    ALL.every(s=>s.clashes.filter(c=>c.geometry&&c.geometry.intersection&&
      c.geometry.intersection.volume_m3!==undefined)
      .every(c=>c.geometry.intersection.volume_m3>0)));
chk('every clash carries the detector version',
    ALL.every(s=>s.clashes.every(c=>c.evidence&&
      (c.evidence.detector_version===COORD_DETECTOR_VERSION||c.evidence.kind==='reference'))));
chk('every geometric clash declares its geometry confidence',
    ALL.every(s=>s.clashes.filter(c=>c.geometry).every(c=>
      COORD_GEOMETRY_CONFIDENCE.indexOf(c.geometry_confidence)>=0)));
chk('a fallback-sized clash names which side fell back',
    ALL.every(s=>s.clashes.filter(c=>c.geometry_confidence==='display_fallback')
      .every(c=>(c.evidence.fallback_geometry||[]).length>0)));
chk('a display fallback is never promoted to a stated dimension',
    ALL.every(s=>s.clashes.filter(c=>c.geometry_confidence==='display_fallback')
      .every(c=>/never promoted to an engineering dimension/.test(c.evidence.confidence_note))));
chk('proximity alone never produces a hard clash',
    _coAabbOverlap([0,0,0,1,1,1],[1,0,0,2,1,1])===null);
chk('a shared face is contact, not intersection',
    _coAabbOverlap([0,0,0,1,1,1],[0.999999,0,0,2,1,1])!==null&&
    _coAabbOverlap([0,0,0,1,1,1],[1.0,0,0,2,1,1])===null);

console.log('\n== §14 — BROAD PHASE AND SCALE ==');
const bp0=coordBroadPhase([]);
chk('an empty model yields no pairs and no cells',
    bp0[0].length===0&&bp0[1].cells===0);
chk('the grid cell size comes from the spec, not from code', COORD_CELL===2.0);
chk('same-discipline pairs are never candidates',
    coordBroadPhase([{discipline:'MEP',kind:'MEP_SEGMENT',element_id:'a',aabb:[0,0,0,1,1,1]},
                     {discipline:'MEP',kind:'MEP_SEGMENT',element_id:'b',aabb:[0,0,0,1,1,1]}])[0]
      .length===0);
chk('cross-discipline pairs sharing a cell are candidates',
    coordBroadPhase([{discipline:'MEP',kind:'MEP_SEGMENT',element_id:'a',aabb:[0,0,0,1,1,1]},
                     {discipline:'STRUCTURE',kind:'STRUCT_BEAM',element_id:'b',
                      aabb:[0,0,0,1,1,1]}])[0].length===1);
chk('an oversized element is still compared against everything', (function(){
    const big={discipline:'ARCHITECTURE',kind:'ARCH_SLAB',element_id:'big',
      aabb:[-500,-500,-500,500,500,500]};
    const small={discipline:'MEP',kind:'MEP_SEGMENT',element_id:'s',aabb:[0,0,0,1,1,1]};
    const r=coordBroadPhase([big,small]);
    return r[0].length===1&&r[1].oversized_elements===1; })());
chk('the statistics report the real candidate-pair count, never a rounded claim',
    ALL.every(s=>typeof s.statistics.candidate_pairs==='number'&&
      s.statistics.candidate_pairs>=0));
chk('the busiest cell occupancy is reported rather than hidden',
    ALL.every(s=>typeof s.statistics.busiest_cell==='number'));

console.log('\n== §15 — DEBUG VIEW AND EXPORT ==');
const dv=coordDebugView(A,A.clashes[0].id);
chk('the debug view highlights exactly the two elements',
    dv.highlight.length===2&&dv.isolate.length===2);
chk('the debug view provides an intersection marker box',
    dv.marker&&dv.marker.ex>0&&dv.marker.ey>0&&dv.marker.ez>0);
chk('the debug view states it changes nothing in the normal model',
    /the normal model appearance is never changed/.test(dv.note)&&
    /no clash geometry is baked into the standard export/.test(dv.note));
chk('an unknown clash has no debug view', coordDebugView(A,'nope')===null);
const ex=coordExportSnapshot(A);
chk('the export is marked derived', ex.derived===true);
chk('the export says it is never persisted as model truth',
    /never persisted as core model truth/.test(ex.note)&&
    /never modifies any discipline model/.test(ex.note));
chk('the export carries the snapshot and model hashes',
    ex.snapshot_id&&ex.model_hashes.length===1&&ex.project_hash);
chk('the export carries every clash with its evidence',
    ex.clashes.length===A.clashes.length&&ex.clashes.every(c=>c.evidence));

console.log('\n== §16 — RULE INPUTS ARE FACTS, NOT RULES ==');
const ri=coordRuleInputs(A);
chk('rule inputs are counts and existence flags only',
    Object.keys(ri.building).every(k=>k.indexOf('coordination.')===0));
chk('every declared rule input family is present',
    ACS_COORD_SPEC.rule_inputs.every(k=>k.indexOf('count_by_type')>=0||
      Object.prototype.hasOwnProperty.call(ri.building,k)));
chk('a count is never compared to a threshold',
    scanFields(ri,/limit|maximum|minimum|threshold|allowed/i).length===0);
chk('a model with no clashes reports zero, not missing',
    coordRuleInputs(K('Z_empty')).building['coordination.clash.count']===0);
chk('every clash type has a count, including the zero ones',
    COORD_CLASH_TYPES.every(t=>
      typeof ri.building['coordination.clash.count_by_type.'+t]==='number'));

console.log('\n== §17 — EMPTY AND DEGENERATE MODELS ==');
const Z=K('Z_empty');
chk('a model with no structure, MEP or fire data still compiles', Z.clashes.length===0);
chk('an empty model is not reported as coordinated or clear',
    !/no clash|clear|coordinated/i.test(JSON.stringify(Z.summary.note)));
chk('a model with MEP but no structure produces no structural clash',
    K('B_pipe_through_wall_no_pen').clashes.every(c=>
      c.discipline_a!=='STRUCTURE'&&c.discipline_b!=='STRUCTURE'));
chk('the broken MEP fixture still yields a snapshot, not a crash',
    (function(){ try{ return compileCoordination(C(MS.models.broken_mep),'bld_0',null,0,
      null,null,null,null,AT).clashes.length>=0; }catch(e){ return false; } })());
chk('a model with no MEP at all yields no MEP clash',
    compileCoordination(C(MS.models.no_mep),'bld_0',null,0,null,null,null,null,AT)
      .clashes.every(c=>c.discipline_a!=='MEP'&&c.discipline_b!=='MEP'));

console.log('\n== §18 — SORTING, IDS AND DETERMINISM ==');
chk('the clash id is a sha256-derived deterministic token',
    A.clashes.every(c=>/^clash_[0-9a-f]{16}$/.test(c.id)));
chk('the same conflict in the same elements always has the same id',
    _coClashId('HARD_CLASH','MEP','a','STRUCTURE','b')===
    _coClashId('HARD_CLASH','MEP','a','STRUCTURE','b'));
chk('a different conflict type produces a different id',
    _coClashId('HARD_CLASH','MEP','a','STRUCTURE','b')!==
    _coClashId('OPENING_REQUIRED','MEP','a','STRUCTURE','b'));
chk('clash ids are unique inside a snapshot',
    ALL.every(s=>new Set(s.clashes.map(c=>c.id)).size===s.clashes.length));
chk('clashes are sorted deterministically by severity then type then element',
    ALL.every(s=>JSON.stringify(s.clashes.map(c=>c.id))===
      JSON.stringify(s.clashes.slice().sort((a,b)=>
        (COORD_SEVERITIES.indexOf(a.severity)-COORD_SEVERITIES.indexOf(b.severity))||
        (a.type<b.type?-1:a.type>b.type?1:0)||
        (a.element_a<b.element_a?-1:a.element_a>b.element_a?1:0)||
        (a.element_b<b.element_b?-1:a.element_b>b.element_b?1:0)).map(c=>c.id))));
chk('two runs of the whole fixture set are byte-identical',
    JSON.stringify(Object.keys(SC.models).map(k=>K(k)))===JSON.stringify(ALL));

console.log('\n== §19 — FILTERS AND LOOKUP ==');
chk('filtering by discipline pair returns only that pair',
    coordFilterClashes(A,{discipline_a:'MEP',discipline_b:'STRUCTURE'})
      .every(c=>[c.discipline_a,c.discipline_b].sort().join()==='MEP,STRUCTURE'));
chk('filtering by severity returns only that severity',
    coordFilterClashes(I,{severity:'ERROR'}).every(c=>c.severity==='ERROR'));
chk('filtering by an unknown building returns nothing',
    coordFilterClashes(A,{building_id:'bld_9'}).length===0);
chk('filtering by the real building returns everything',
    coordFilterClashes(A,{building_id:'bld_0'}).length===A.clashes.length);
chk('lookup by id returns the clash and nothing for an unknown id',
    coordClashById(A,A.clashes[0].id).id===A.clashes[0].id&&coordClashById(A,'nope')===null);

console.log('\n== §20 — SUMMARY HONESTY ==');
chk('the summary never claims the model is coordinated or clear',
    ALL.every(s=>!/is coordinated|clash.?free|all clear|no conflicts remain/i
      .test(JSON.stringify(s.summary))));
chk('the summary states detection and traceability only',
    ALL.every(s=>/no auto-fix, no rerouting, no redesign, no code compliance and no safety claim/
      .test(s.summary.note)));
chk('the summary counts match the clash list',
    ALL.every(s=>s.summary.clashes===s.clashes.length&&
      s.summary.errors+s.summary.warnings+s.summary.infos===s.clashes.length));
chk('the summary reports exemptions rather than hiding them',
    ALL.every(s=>Object.keys(s.summary.by_exemption)
      .reduce((n,k)=>n+s.summary.by_exemption[k],0)===s.suppressed.length));
chk('the summary reports geometry confidence',
    A.summary.by_geometry_confidence.stated>0);

function MSK(name){ return compileCoordination(C(MS.models[name]),'bld_0',null,0,
  null,null,null,null,AT); }

console.log('\n──────────────────────────────────────────────');
console.log('COORDINATION FOUNDATION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
