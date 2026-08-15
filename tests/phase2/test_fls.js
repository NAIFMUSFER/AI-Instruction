/* ======================================================================
   المرحلة 2 — اختبارات أساس نموذج بيانات الحريق وسلامة الأرواح.
   تمثيل وطوبولوجيا فقط: لا تصميم حريق ولا محاكاة ولا تغطية ولا هيدروليك ولا
   مطابقة كود ولا قيم NFPA/SBC/IBC/دفاع مدني. الغياب ليس مخالفة.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'fls_scen.json'),'utf8'));
const MS=JSON.parse(fs.readFileSync(_np.join(FIXD,'mep_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
const F=(name,bid,pos,rot)=>compileFls(C(SC.models[name]),bid||'bld_0',pos||null,rot||0);
const codes=f=>f.issues.map(i=>i.code);
const FIXTURES=['villa_fls','hotel_fls','clinic_fls','warehouse_fls','mixed_fls'];
/* الكلمات الممنوعة ترد في نصوص التبرئة نفسها، فالفحص يقرأ الحقول لا النصّ الخام */
const NOTE_KEYS=['note','notes','fire_note','detail','disclaimer','basis','status_basis','name',
  'semantics','sources_of_truth','navigation_impact','distance_impact','occupancy_note'];
const scanFields=(root,re)=>{ const hits=[];
  const walk=(v,path)=>{ if(Array.isArray(v)) return v.forEach(x=>walk(x,path));
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(NOTE_KEYS.indexOf(k)>=0) return;
      if(re.test(k)) hits.push(path+'.'+k);
      if(typeof v[k]==='string'&&re.test(v[k])) hits.push(path+'.'+k+'="'+v[k]+'"');
      walk(v[k],path+'.'+k); }); };
  walk(root,''); return hits; };

console.log('\n== §1 — NO FIRE DESIGN, NO SIMULATION, NO CODE ==');
const specTxt=JSON.stringify(ACS_FLS_SPEC);
/* أسماء الأكواد ترد في قوائم المنع وفي نصّ النفي — نجرّدها قبل الفحص
   لأنّ وجودها هناك رفضٌ لها لا تطبيقٌ لقيمها */
chk('the FLS spec implements no fire code value',
    !/\bNFPA\b|\bSBC\b|\bIBC\b|civil.?defen/i.test(
      JSON.stringify({a:ACS_FLS_SPEC.issue_codes,b:ACS_FLS_SPEC.device_types,
        c:ACS_FLS_SPEC.barrier_types,d:ACS_FLS_SPEC.opening_types,
        e:ACS_FLS_SPEC.relationship_types,f:ACS_FLS_SPEC.display_fallbacks,
        g:ACS_FLS_SPEC.model_status,h:ACS_FLS_SPEC.provenance_values,
        i:ACS_FLS_SPEC.device_categories,j:ACS_FLS_SPEC.protection_statuses,
        k:ACS_FLS_SPEC.smoke_control_kinds,l:ACS_FLS_SPEC.render_layers})));
chk('the spec states in writing that there is no Fire / Life-Safety engine',
    /There is no Fire \/ Life-Safety engine/.test(ACS_FLS_SPEC.fire_note)&&
    /There is no Fire \/ Life-Safety engine/.test(F('villa_fls').meta.fire_note));
chk('the only mentions of a fire code are in the forbidden lists and the denial text',
    ACS_FLS_SPEC.forbidden_provenance.indexOf('nfpa')>=0&&
    ACS_FLS_SPEC.forbidden_claims.indexOf('meets_nfpa')>=0&&
    /implements NO NFPA, SBC, IBC or Civil Defense rule value/.test(ACS_FLS_SPEC.note));
chk('regulatory rule count is still zero', regulatoryRuleCount([])===0);
chk('real occupancy classification count is still zero',
    occRealClassificationCount(occupancyFixtureStore())===0);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_fls.json'),'utf8'));
chk('browser spec is byte-identical to acs_fls.json',
    JSON.stringify(sk(ACS_FLS_SPEC))===JSON.stringify(sk(CANON)));
chk('twelve FLS element types declared', FLS_ELEMENT_TYPES.length===12,
    FLS_ELEMENT_TYPES.length);
chk('twenty-two device types declared', FLS_DEVICE_TYPES.length===22, FLS_DEVICE_TYPES.length);
chk('COMPLIANT / SAFE / APPROVED / CERTIFIED / DESIGNED are not model statuses',
    ['COMPLIANT','SAFE','APPROVED','CERTIFIED','DESIGNED']
      .every(x=>FLS_MODEL_STATUS.indexOf(x)<0));
chk('UNSAFE / CODE_VIOLATION / FIRE_VIOLATION are not severities',
    JSON.stringify(FLS_SEVERITIES)==='["INFO","WARNING","ERROR"]');
{ const forb=ACS_FLS_SPEC.forbidden_claims, hits=[];
  const walk=v=>{ if(Array.isArray(v)) return v.forEach(walk);
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(forb.indexOf(k)>=0) hits.push(k); walk(v[k]); }); };
  FIXTURES.forEach(n=>walk(F(n)));
  chk('no compiled FLS element carries a coverage, hydraulic or compliance field',
      hits.length===0, Array.from(new Set(hits)).join(','));
  chk('no invented K-factor, density, candela, audibility or travel limit appears in any field',
      scanFields(FIXTURES.map(n=>F(n)),
        /k_factor|density|candela|audib|sound_level|coverage|spacing|hydraul|travel_distance/i)
        .length===0);
  chk('the language actually used is representational',
      FIXTURES.map(n=>JSON.stringify(F(n))).join(' ')
        .indexOf('is not coverage, protection or compliance')>=0); }

console.log('\n== §2 — CODE_REQUIRED GATE ==');
chk('code_required and rule are not provenance values',
    FLS_PROVENANCE.indexOf('code_required')<0&&FLS_PROVENANCE.indexOf('rule')<0);
chk('they are named explicitly as forbidden provenance',
    ['code_required','rule','nfpa','sbc','civil_defense']
      .every(x=>FLS_FORBIDDEN_PROVENANCE.indexOf(x)>=0));
chk('a model claiming code_required provenance is neutralised, not obeyed',
    (()=>{const m=C(FX.villa);
      m.fire_life_safety={devices:[{id:'d',type:'SMOKE_DETECTOR',x:1,z:1,level:0,
        source:'code_required'}]};
      const f=compileFls(m,'bld_0');
      return f.devices[0].source==='unknown';})());
chk('every audit reports code_required as exactly zero',
    FIXTURES.every(n=>flsAudit(F(n)).code_required===0));
chk('a system-added Phase 1 smoke detector stays system_default through two adapters',
    (()=>{const f=F('phase1_fls');
      const sd=f.devices.filter(d=>d.device_type==='SMOKE_DETECTOR');
      return sd.length===2&&sd.some(d=>d.original_source==='system_default')&&
             sd.every(d=>d.source==='phase1_adapter');})());
chk('a user-supplied Phase 1 point keeps its user provenance',
    F('phase1_fls').devices.some(d=>d.original_source==='user'));
chk('the string code_required does not appear in the compiled models at all',
    !/code_required/i.test(JSON.stringify(FIXTURES.map(n=>F(n)))));

console.log('\n== §3 — ADAPTERS DO NOT DUPLICATE ==');
{ const f=F('villa_fls');
  chk('exits come from the egress foundation, not a second inference engine',
      f.exits.every(x=>x.origin==='egress_adapter'||x.origin==='model')&&
      f.exits.some(x=>x.origin==='egress_adapter'));
  chk('an adapted exit references the egress exit id',
      f.exits.filter(x=>x.origin==='egress_adapter')
        .every(x=>x.exit_resolved&&!!x.exit_ref));
  chk('the FLS exit list matches the egress exit list exactly',
      (()=>{const eg=extractExits(C(SC.models.villa_fls),
              buildRelationships(C(SC.models.villa_fls),'bld_0'),'bld_0');
        return f.exits.filter(x=>x.origin==='egress_adapter').length===eg.length;})());
  chk('stairs are referenced from the architectural cores',
      f.stairs.every(s=>s.origin==='arch_adapter'||s.origin==='model'));
  chk('an adapted stair creates no geometry, only a reference',
      f.stairs.filter(s=>s.origin==='arch_adapter').every(s=>s.core_resolved&&!!s.core_id));
  chk('the render layer marks referenced devices as referenced, not emitted',
      flsRenderItems(F('phase1_fls')).filter(i=>i.kind==='DEVICE')
        .every(i=>i.render_mode==='referenced'));
  chk('an FLS-declared device IS emitted, because nothing else draws it',
      flsRenderItems(f).filter(i=>i.kind==='DEVICE')
        .every(i=>i.render_mode==='emitted'));
  chk('the spec states the no-duplication rule in writing',
      /does not duplicate semantic objects or geometry/.test(ACS_FLS_SPEC.adapter_note)); }
{ const h=F('hotel_fls');
  chk('MEP fire systems are referenced, not re-modelled',
      h.systems.every(s=>!!s.mep_system_id));
  chk('the MEP model stays the source of truth for topology',
      /MEP model remains the source of truth/.test(
        h.systems.filter(s=>s.origin==='mep_adapter').map(s=>s.note).join(' '))||
      h.systems.every(s=>s.origin==='model'));
  chk('no FLS element maintains a sprinkler pipe network',
      !/polyline|from_node|to_node/.test(JSON.stringify(h.devices))); }

console.log('\n== §4 — DEVICE PRESENT IS NOT COVERAGE ==');
{ const f=F('single_detector');
  chk('one declared detector yields exactly one represented device',
      flsAudit(f).devices_total===1&&flsAudit(f).smoke_detectors===1);
  chk('the audit reports coverage and compliance as NOT_EVALUATED',
      flsAudit(f).coverage==='NOT_EVALUATED'&&flsAudit(f).compliance==='NOT_EVALUATED');
  chk('nothing anywhere says the room is protected or covered',
      scanFields(f,/protected|covered|coverage_confirmed/i).length===0);
  chk('the DEVICE_IN_SPACE edge carries an explicit non-coverage disclaimer',
      f.relationships.some(r=>r.type==='DEVICE_IN_SPACE'&&
        /is not coverage or protection of that space/.test(r.meta.disclaimer)));
  chk('every relationship repeats that it is factual only',
      f.relationships.every(r=>/never coverage, protection, adequacy or compliance/
        .test(r.note)));
  chk('the four semantic distinctions are declared structurally',
      ACS_FLS_SPEC.semantics.length===6&&
      ACS_FLS_SPEC.semantics.indexOf('DEVICE_PRESENT is not COVERAGE_CONFIRMED')>=0&&
      ACS_FLS_SPEC.semantics.indexOf('SYSTEM_PRESENT is not SYSTEM_ADEQUATE')>=0&&
      ACS_FLS_SPEC.semantics.indexOf('EXIT_PRESENT is not EGRESS_COMPLIANT')>=0&&
      ACS_FLS_SPEC.semantics.indexOf(
        'BARRIER_PRESENT is not FIRE_SEPARATION_COMPLIANT')>=0);
  chk('and the compiled model carries them', f.meta.semantics.length===6); }

console.log('\n== §5 — ABSENCE IS NOT A VIOLATION ==');
{ const n=F('no_fls');
  chk('a building with no FLS data is NOT_DEFINED', n.status==='NOT_DEFINED');
  chk('and has zero issues caused merely by absence', n.issues.length===0, n.issues.length);
  chk('no fire device was added automatically', flsAudit(n).devices_total===0);
  chk('the status basis explains that only references exist',
      /no fire or life-safety element is declared/.test(n.status_basis));
  chk('a warehouse gets no sprinkler or hydrant just for being a warehouse',
      flsAudit(F('warehouse_fls')).sprinklers===0&&
      F('warehouse_fls').devices.every(d=>d.device_type!=='HYDRANT'));
  chk('a villa fixture without sprinklers reports zero, not a deficiency',
      flsAudit(F('villa_fls')).sprinklers===0&&
      codes(F('villa_fls')).every(c=>!/MISSING_SPRINKLER|NO_ALARM|DEFICIEN/i.test(c)));
  chk('no issue code implies a missing element is a fault',
      Object.keys(FLS_ISSUE_CODES).every(c=>!/MISSING_(SPRINKLER|ALARM|EXTINGUISH)|REQUIRED/
        .test(c)));
  chk('the spec states it plainly',
      /absence is not a violation without a verified rule/.test(ACS_FLS_SPEC.severity_note)); }

console.log('\n== §6 — FIRE DOOR ONLY WHEN DECLARED ==');
{ const plain=F('door_plain'), fire=F('door_fire');
  chk('the same architectural door yields no fire door without metadata',
      flsAudit(plain).fire_doors===0&&plain.openings.length===0);
  chk('the architectural door itself still exists untouched',
      compileArchitecture(C(SC.models.door_plain),'bld_0').openings.length>0);
  chk('declaring it explicitly creates exactly one FLS reference',
      flsAudit(fire).fire_doors===1&&fire.openings.length===1);
  chk('the reference resolves to the real architectural opening',
      fire.openings[0].arch_opening_resolved===true&&
      !!fire.openings[0].resolved_opening_id);
  chk('its rating is carried, never inferred',
      fire.openings[0].rating_minutes.value===60&&
      fire.openings[0].rating_minutes.source==='imported');
  chk('an unstated rating stays null with an explicit note',
      (()=>{const m=C(SC.models.door_fire);
        delete m.fire_life_safety.openings[0].rating_minutes;
        const f=compileFls(m,'bld_0');
        return f.openings[0].rating_minutes.value===null&&
          /never inferred from a material/.test(f.openings[0].rating_minutes.note);})());
  chk('the spec says a normal door is not a fire door',
      /a normal architectural door is NOT a fire door/.test(ACS_FLS_SPEC.opening_note)); }

console.log('\n== §7 — BARRIER ONLY WHEN DECLARED ==');
{ const plain=F('door_plain'), fire=F('door_fire');
  const arch=compileArchitecture(C(FX.villa),'bld_0');
  chk('the villa has real shared architectural walls',
      arch.walls.filter(w=>w.shared).length>0);
  chk('but none of them is a fire barrier without metadata',
      flsAudit(plain).barriers===0);
  chk('declaring one explicitly creates exactly one barrier referencing its host wall',
      flsAudit(fire).barriers===1&&fire.barriers[0].hosts_resolved===true);
  chk('a structural wall is never promoted to a barrier either',
      (()=>{const m=C(SC.models.door_plain);
        m.structural={walls:[{id:'sw',levels:[0],start:{x:0,z:0},end:{x:0,z:5},
          structural_role:'shear_wall',source:'user'}]};
        return flsAudit(compileFls(m,'bld_0')).barriers===0;})());
  chk('a barrier with no stated rating reports a data gap, not a violation',
      (()=>{const b=F('broken_fls').issues.filter(i=>i.code==='RATING_UNKNOWN');
        return b.length>0&&b.every(i=>i.severity==='INFO'&&
          /not a violation/.test(i.detail));})());
  chk('the spec says an architectural wall is not a fire barrier',
      /an architectural wall is not a fire barrier/.test(ACS_FLS_SPEC.barrier_note)); }

console.log('\n== §8 — STAIRS AND SHAFTS ARE NOT PROTECTED BY DEFAULT ==');
{ const f=F('villa_fls');
  chk('an adapted stair has protection_status unknown',
      f.stairs.filter(s=>s.origin==='arch_adapter').every(s=>s.protection_status==='unknown'));
  chk('and it is never called a protected stair',
      scanFields(f.stairs,/protected/i).length===0);
  const h=F('hotel_fls');
  chk('a declared protected stair says so explicitly',
      h.stairs.some(s=>s.protection_status==='declared_protected'));
  chk('a declared shaft protection is carried, never assumed',
      h.shafts.length===1&&h.shafts[0].protection_status==='declared_protected');
  chk('an MEP riser is not a fire shaft by itself',
      (()=>{const m=C(MS.models.hotel_mep);
        return compileFls(m,'bld_0').shafts.length===0;})());
  chk('the audit counts only declared protected stairs',
      flsAudit(h).protected_stairs_declared===1&&flsAudit(f).protected_stairs_declared===0);
  chk('the spec states the rule',
      /never classified as a protected stair automatically/.test(
        ACS_FLS_SPEC.protection_note)); }

console.log('\n== §9 — ZONES ARE NEVER INFERRED ==');
{ const f=F('villa_fls');
  chk('no zone exists without explicit data', flsAudit(f).zones===0);
  chk('rooms are never turned into compartments',
      f.zones.length===0&&compileArchitecture(C(SC.models.villa_fls),'bld_0').spaces.length>0);
  const h=F('hotel_fls');
  chk('a declared zone compiles and resolves its spaces',
      h.zones.length===1&&h.zones[0].spaces_resolved===true);
  chk('it produces ZONE_CONTAINS_SPACE edges for exactly its declared spaces',
      h.relationships.filter(r=>r.type==='ZONE_CONTAINS_SPACE').length===
      h.zones[0].resolved_space_ids.length);
  chk('a zone with no spaces is reported as a data gap, not populated by inference',
      F('broken_fls').issues.some(i=>i.code==='ZONE_WITHOUT_SPACES'&&i.severity==='INFO'));
  chk('the spec states the rule',
      /never inferred from room boundaries/.test(h.zones[0].note)); }

console.log('\n== §10 — DETECTION, ALARM, SUPPRESSION, FIRE WATER ==');
{ const h=F('hotel_fls');
  chk('devices map to declared categories',
      h.devices.every(d=>FLS_DEVICE_CATEGORIES.indexOf(d.device_category)>=0));
  chk('a smoke detector is DETECTION and a sounder is ALARM',
      h.devices.filter(d=>d.device_type==='SMOKE_DETECTOR')
        .every(d=>d.device_category==='DETECTION')&&
      FLS_DEVICE_CATEGORY.SOUNDER_STROBE==='ALARM');
  chk('a declared loop membership is represented, never designed',
      h.relationships.some(r=>r.type==='DEVICE_CONNECTED_TO_LOOP'&&
        /loops are never designed automatically/.test(r.meta.disclaimer)));
  chk('a declared alarm zone is represented, never derived from floors',
      h.relationships.some(r=>r.type==='DEVICE_IN_ALARM_ZONE'&&
        /never derived from floors or rooms/.test(r.meta.disclaimer)));
  chk('a panel-controls-device edge exists only where declared',
      h.relationships.filter(r=>r.type==='PANEL_CONTROLS_DEVICE').length===3);
  chk('sprinkler heads are represented with no spacing, coverage or K-factor',
      h.devices.filter(d=>d.device_type==='SPRINKLER_HEAD').length===3&&
      scanFields(h.devices.filter(d=>d.device_type==='SPRINKLER_HEAD'),
        /spacing|coverage|k_factor|density/i).length===0);
  chk('an MEP sprinkler terminal is referenced rather than re-created',
      (()=>{const m=C(MS.models.villa_mep);
        m.mep.terminals.push({id:'t_spr',system_id:'sys_cw',type:'sprinkler_head',
          x:3,z:3,level:0,source:'test_fixture'});
        const f=compileFls(m,'bld_0');
        const sp=f.devices.filter(d=>d.device_type==='SPRINKLER_HEAD');
        return sp.length===1&&sp[0].origin==='mep_adapter'&&
          sp[0].mep_element_id==='bld_0.mep.t_spr';})());
  chk('a fire pump in MEP equipment is referenced as a FIRE_WATER device',
      (()=>{const m=C(MS.models.villa_mep);
        m.mep.equipment.push({id:'eq_fp',system_id:'sys_cw',type:'fire_pump',x:1,z:1,
          level:0,source:'test_fixture'});
        const f=compileFls(m,'bld_0');
        return f.devices.some(d=>d.device_type==='FIRE_PUMP'&&
          d.device_category==='FIRE_WATER'&&d.origin==='mep_adapter');})());
  chk('extinguishers and hose reels are represented without quantity or travel analysis',
      flsAudit(F('clinic_fls')).extinguishers===1&&
      flsAudit(F('clinic_fls')).hose_reels===1); }

console.log('\n== §11 — SIGNAGE AND EMERGENCY LIGHTING ==');
{ const f=F('villa_fls');
  chk('an exit sign references a real exit', f.signs.length===1&&
      f.signs[0].target_resolved===true);
  chk('SIGN_INDICATES_EXIT is emitted for it',
      f.relationships.some(r=>r.type==='SIGN_INDICATES_EXIT'&&r.status==='confirmed'));
  chk('whether signage is required or adequate is never determined',
      /never determined here/.test(f.signs[0].note)&&
      scanFields(f.signs,/required|adequate/i).length===0);
  const b=F('broken_fls');
  chk('a sign pointing at a nonexistent exit is a model-integrity ERROR',
      b.issues.some(i=>i.code==='SIGN_TARGET_MISSING'&&i.severity==='ERROR'));
  chk('and the target is never invented',
      b.relationships.some(r=>r.type==='SIGN_INDICATES_EXIT'&&r.to===null&&
        r.status==='unresolved'));
  chk('emergency lights are represented with no lux or autonomy',
      F('hotel_fls').devices.filter(d=>d.device_type==='EMERGENCY_LIGHT').length===3&&
      scanFields(F('hotel_fls').devices.filter(d=>d.device_type==='EMERGENCY_LIGHT'),
        /lux|lumen|autonomy|battery|duration/i).length===0); }

console.log('\n== §12 — ASSEMBLY POINTS, REFUGE, SMOKE CONTROL ==');
{ const h=F('hotel_fls');
  chk('an assembly point is represented at site scope',
      h.assembly_points.length===1&&h.assembly_points[0].scope==='site');
  chk('no path from an exit to it is created',
      h.relationships.filter(r=>r.type==='ASSEMBLY_POINT_ON_SITE')
        .every(r=>/no path from a building exit to an assembly point exists/
          .test(r.meta.disclaimer)));
  chk('an assembly point inside the footprint is reported as a data problem',
      F('broken_fls').issues.some(i=>i.code==='ASSEMBLY_POINT_INSIDE_BUILDING'));
  chk('a refuge area exists only where declared',
      h.refuge_areas.length===1&&F('villa_fls').refuge_areas.length===0);
  chk('a lobby, landing or corridor never becomes a refuge area',
      F('no_fls').refuge_areas.length===0);
  chk('accessibility is never evaluated for a refuge area',
      /accessibility is never evaluated/.test(h.refuge_areas[0].note));
  chk('smoke control entries are data placeholders only',
      h.smoke_control.length===1&&
      /no smoke modelling, airflow or pressurisation/.test(h.smoke_control[0].note));
  chk('no smoke or airflow field is produced',
      scanFields(h.smoke_control,/airflow|velocity|pressure_pa|smoke_layer/i).length===0); }

console.log('\n== §13 — EGRESS, DISTANCE AND OCCUPANCY INTEGRATION ==');
{ const b=C(SC.models.villa_fls);
  const facts=flsEgressFacts(b,'bld_0','bld_0.g.majlis');
  chk('a measured egress result can be quoted as factual data',
      !!facts&&facts.status==='FOUND'&&typeof facts.walking_distance_m==='number');
  chk('it is never compared to a code travel-distance limit',
      facts.compliance==='NOT_EVALUATED'&&
      /never compared to any code travel-distance limit/.test(facts.note));
  chk('no travel-distance limit exists anywhere in the layer',
      scanFields(F('hotel_fls'),/travel_distance|max_travel|limit/i).length===0);
  chk('a missing space yields no fabricated egress fact',
      (()=>{const x=flsEgressFacts(b,'bld_0','nope');
        return x===null||x.status!=='FOUND';})());
  chk('the building programme is never used as a fire occupancy classification',
      /a building programme is NOT a fire occupancy classification/
        .test(ACS_FLS_SPEC.occupancy_note));
  chk('the verified regulatory occupancy count is still zero',
      occRealClassificationCount(occupancyFixtureStore())===0); }

console.log('\n== §14 — MODEL INTEGRITY VALIDATION ==');
{ const b=F('broken_fls');
  const need=['DUPLICATE_ELEMENT_ID','UNSUPPORTED_ELEMENT_TYPE','UNKNOWN_DEVICE_TYPE',
    'UNKNOWN_BARRIER_TYPE','UNKNOWN_OPENING_TYPE','INVALID_SYSTEM_REF',
    'INVALID_MEP_ELEMENT_REF','INVALID_LEVEL_REF','INVALID_SPACE_REF','INVALID_EXIT_REF',
    'INVALID_HOST_WALL_REF','INVALID_HOST_OPENING_REF','INVALID_CORE_REF',
    'INVALID_ZONE_SPACE_REF','INVALID_BARRIER_REF','INVALID_RATING_VALUE',
    'CROSS_BUILDING_REF','NAN_COORDINATE','DEVICE_OUTSIDE_SPACE','SIGN_TARGET_MISSING',
    'FIRE_DOOR_NOT_HOSTED','BARRIER_WITHOUT_HOST','ASSEMBLY_POINT_INSIDE_BUILDING',
    'RATING_UNKNOWN','ZONE_WITHOUT_SPACES'];
  const got=new Set(codes(b));
  chk('the deliberately broken fixture triggers every integrity check',
      need.every(c=>got.has(c)), need.filter(c=>!got.has(c)).join(','));
  chk('every issue code is declared in the spec with a severity',
      b.issues.every(i=>Object.prototype.hasOwnProperty.call(FLS_ISSUE_CODES,i.code)));
  chk('issues are ordered ERROR first, then WARNING, then INFO',
      (()=>{const r={ERROR:0,WARNING:1,INFO:2};
        return b.issues.every((i,k)=>k===0||r[b.issues[k-1].severity]<=r[i.severity]);})());
  chk('no issue is a code or fire-compliance verdict',
      b.issues.every(i=>!/COMPLIAN|NFPA|SBC|UNSAFE|VIOLATION|FIRE_CODE/i.test(i.code)));
  chk('an unknown FLS collection is reported and NOT interpreted',
      b.issues.some(i=>i.code==='UNSUPPORTED_ELEMENT_TYPE'&&
        /was NOT interpreted/.test(i.detail)));
  chk('a foreign building id is caught rather than silently re-namespaced',
      b.issues.some(i=>i.code==='CROSS_BUILDING_REF'&&i.subject==='bld_9.d_foreign'));
  chk('a NaN coordinate is rejected rather than propagated',
      b.devices.concat(b.signs).every(e=>e.x===null||isFinite(e.x)));
  chk('a device located inside a stair void is reported as a fact, not a fault',
      b.issues.some(i=>i.code==='DEVICE_IN_FLOOR_OPENING'&&i.severity==='INFO'&&
        /not as a fault/.test(i.detail))); }

console.log('\n== §15 — DETERMINISM, NAMESPACING AND TRANSFORMS ==');
chk('compiling twice gives byte-identical output',
    JSON.stringify(F('hotel_fls'))===JSON.stringify(F('hotel_fls')));
{ const m=C(SC.models.hotel_fls), before=JSON.stringify(m);
  compileFls(m,'bld_0'); validateFls(compileFls(m,'bld_0'));
  chk('the compiler never mutates the model it reads', JSON.stringify(m)===before); }
{ const a=F('villa_fls','bld_0'), b=F('villa_fls','bld_6');
  chk('a second building namespaces every FLS id',
      b.devices.every(d=>d.id.indexOf('bld_6.fls.')===0)&&
      b.relationships.every(r=>r.id.indexOf('bld_6.fls.')===0));
  chk('two buildings can never collide on an id',
      a.devices.every(d=>b.devices.every(e=>e.id!==d.id)));
  const t=F('villa_fls','bld_0',{x:8,z:-3},25);
  chk('a transform never changes the compiled data',
      JSON.stringify(t.devices)===JSON.stringify(a.devices));
  const p=flsToWorld(t,0,0);
  chk('the building transform is applied on read',
      Math.abs(p[0]-8)<1e-9&&Math.abs(p[1]+3)<1e-9, JSON.stringify(p));
  const p2=flsToWorld(t,10,0);
  chk('rotation is applied about the building origin',
      Math.abs(p2[0]-(8+10*Math.cos(25*Math.PI/180)))<1e-9&&
      Math.abs(p2[1]-(-3+10*Math.sin(25*Math.PI/180)))<1e-9); }

console.log('\n== §16 — REVISION HASH ==');
{ const base=C(SC.models.hotel_fls);
  const h0=modelHash(base);
  const moved=C(base); moved.fire_life_safety.devices[0].x=9.9;
  chk('moving a detector changes the model hash', modelHash(moved)!==h0);
  const noSpr=C(base);
  noSpr.fire_life_safety.devices=noSpr.fire_life_safety.devices
    .filter(d=>d.type!=='SPRINKLER_HEAD');
  chk('removing a sprinkler changes the model hash', modelHash(noSpr)!==h0);
  const rating=C(base); rating.fire_life_safety.openings[0].rating_minutes=90;
  chk('changing a fire-door rating changes the model hash', modelHash(rating)!==h0);
  const zone=C(base); zone.fire_life_safety.zones[0].spaces=['bld_0.g.lobby@0'];
  chk('changing zone membership changes the model hash', modelHash(zone)!==h0);
  const sign=C(base); sign.fire_life_safety.signs[0].indicates_exit='bld_0.exit_2';
  chk('changing an exit-sign target changes the model hash', modelHash(sign)!==h0);
  const sys=C(base); sys.fire_life_safety.systems[0].mep_system_id='sys_san';
  chk('changing a fire system reference changes the model hash', modelHash(sys)!==h0);
  const vis=C(base); vis.fire_life_safety.layer_visibility={detection:false};
  chk('toggling layer visibility does NOT change the model hash', modelHash(vis)===h0);
  const cam=C(base); cam.camera={x:1,y:2,z:3};
  chk('moving the camera still does not change the hash', modelHash(cam)===h0);
  chk('compiling the FLS model does not change the hash',
      (()=>{const m=C(base); const h=modelHash(m); compileFls(m,'bld_0');
        return modelHash(m)===h;})()); }

console.log('\n== §17 — RENDER AND EXPORT ==');
{ const f=F('villa_fls');
  const items=flsRenderItems(f);
  chk('render items use the FLS| naming convention',
      items.every(i=>/^FLS\|[A-Z_]+\|bld_0\.fls\./.test(i.name)));
  chk('every requested debug layer exists',
      ['FLS_DETECTION','FLS_ALARM','FLS_SUPPRESSION','FLS_FIRE_WATER',
       'FLS_EMERGENCY_LIGHTING','FLS_SIGNAGE','FLS_BARRIER','FLS_FIRE_DOOR','FLS_ZONE']
        .every(k=>LAYER_ORDER.indexOf(k)>=0&&!!LAYER_NAMES[k]));
  chk('layer labels say data only, never compliance',
      /بيانات/.test(LAYER_NAMES.FLS_DETECTION)&&/بيانات/.test(LAYER_NAMES.FLS_SUPPRESSION));
  chk('every render item declares its geometry is a display fallback',
      items.every(i=>i.geometry_source==='display_fallback'));
  chk('render items never carry an engineering or compliance verdict',
      !/protected|adequate|compliant|coverage/i.test(JSON.stringify(items)));
  chk('colour marks the element type only, never a state',
      Object.keys(FLS_LAYER_COLOR).every(k=>FLS_RENDER_LAYERS.indexOf(k)>=0));
  chk('no red-means-violation logic exists',
      /No colour in this layer means safe, failed, compliant or non-compliant/
        .test(ACS_FLS_SPEC.colour_note)); }

console.log('\n== §18 — RULE ENGINE CONTRACT (INPUTS ONLY) ==');
{ const f=F('hotel_fls');
  const ri=flsRuleInputs(f);
  chk('device existence and counts are exposed as factual inputs',
      ri.building['fls.device.exists.SMOKE_DETECTOR']===true&&
      ri.building['fls.device.count.SPRINKLER_HEAD']===3);
  chk('an absent device type is exposed as false, not as a deficiency',
      ri.building['fls.device.exists.HYDRANT']===false&&
      ri.building['fls.device.count.HYDRANT']===0);
  chk('exit and zone counts are exposed',
      ri.building['fls.exit.count']>=1&&ri.building['fls.zone.exists']===true);
  chk('fire-door and barrier ratings are exposed only when real',
      Object.keys(ri).some(k=>ri[k]['fls.fire_door.rating']===60));
  chk('no regulatory rule was added anywhere', regulatoryRuleCount([])===0);
  chk('the rule inputs contain no threshold, limit or verdict',
      !/limit|minimum|maximum|required|PASS|FAIL|compliant/i.test(JSON.stringify(ri))); }

console.log('\n== §19 — NO ARCH / STRUCT / MEP / NAV / EGRESS / DISTANCE REGRESSION ==');
{ const plain=C(MS.models.villa_mep), withFls=C(SC.models.villa_fls);
  chk('adding an FLS block changes no architectural element',
      JSON.stringify(compileArchitecture(plain,'bld_0'))===
      JSON.stringify(compileArchitecture(withFls,'bld_0')));
  chk('adding an FLS block changes no structural element',
      JSON.stringify(compileStructure(plain,'bld_0'))===
      JSON.stringify(compileStructure(withFls,'bld_0')));
  chk('adding an FLS block changes no MEP element',
      JSON.stringify(compileMep(plain,'bld_0'))===
      JSON.stringify(compileMep(withFls,'bld_0')));
  chk('compiling FLS does not mutate the MEP model',
      (()=>{const m=C(SC.models.villa_fls);
        const before=JSON.stringify(compileMep(C(m),'bld_0'));
        compileFls(m,'bld_0');
        return JSON.stringify(compileMep(C(m),'bld_0'))===before;})());
  chk('relationships are identical with and without the FLS block',
      JSON.stringify(buildRelationships(withFls,'bld_0'))===
      JSON.stringify(buildRelationships(plain,'bld_0')));
  chk('navigation is identical with and without the FLS block',
      JSON.stringify(findPath(withFls,buildRelationships(withFls,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0'))===
      JSON.stringify(findPath(plain,buildRelationships(plain,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0')));
  chk('egress selection and routing are identical',
      JSON.stringify(findEgress(withFls,buildRelationships(withFls,'bld_0'),
        'bld_0.g.majlis','bld_0'))===
      JSON.stringify(findEgress(plain,buildRelationships(plain,'bld_0'),
        'bld_0.g.majlis','bld_0')));
  chk('walking distance is unchanged — no barrier or device reroutes anything',
      (()=>{const p1=findPath(withFls,buildRelationships(withFls,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        const p2=findPath(plain,buildRelationships(plain,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        return measurePath(withFls,p1,'bld_0').walking_distance_m===
               measurePath(plain,p2,'bld_0').walking_distance_m;})());
  chk('and the model says so in writing',
      /NOT navigation obstacles/.test(F('villa_fls').meta.navigation_impact)); }

console.log('\n== §20 — PROGRAMME NEUTRALITY AND AUDIT ==');
FIXTURES.forEach(n=>{ const f=F(n);
  chk(n+': compiles through the same element vocabulary',
      f.devices.every(d=>d.type==='FLS_DEVICE')&&f.exits.every(x=>x.type==='FLS_EXIT'));
  chk(n+': every issue code is declared',
      f.issues.every(i=>Object.prototype.hasOwnProperty.call(FLS_ISSUE_CODES,i.code)));
  chk(n+': the audit reports compliance as NOT_EVALUATED',
      flsAudit(f).compliance==='NOT_EVALUATED'&&flsAudit(f).code_required===0); });
{ const m=F('mixed_fls');
  chk('three different programmes share one unchanged FLS model',
      flsAudit(m).smoke_detectors===6, flsAudit(m).smoke_detectors);
  chk('half are declared and half are referenced from MEP — never duplicated geometry',
      m.devices.filter(d=>d.origin==='model').length===3&&
      m.devices.filter(d=>d.origin==='mep_adapter').length===3&&
      flsRenderItems(m).filter(i=>i.render_mode==='emitted').length===3);
  chk('no FLS property changed with the occupancy or programme',
      m.devices.every(d=>d.device_type==='SMOKE_DETECTOR'));
  chk('a clinic gets no healthcare-specific requirement',
      !/healthcare|HTM|hospital/i.test(JSON.stringify(F('clinic_fls')))); }

console.log('\n== §21 — SECURITY ==');
chk('no eval / Function in the FLS layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      compileFls.toString()+validateFls.toString()+flsRenderItems.toString()+
      flsAudit.toString()));
chk('no network call in the FLS layer',
    !/fetch\s*\(|XMLHttpRequest/.test(compileFls.toString()+validateFls.toString()));
chk('a hostile element id cannot escape into markup',
    (()=>{const m=C(FX.villa);
      m.fire_life_safety={devices:[{id:'<script>alert(1)</script>',type:'SMOKE_DETECTOR',
        x:1,z:1,level:0,source:'user'}]};
      const f=compileFls(m,'bld_0');
      return esc(f.devices[0].id).indexOf('<script')<0;})());

console.log(`\nFLS: ${pass} passed, ${fail} failed`);
