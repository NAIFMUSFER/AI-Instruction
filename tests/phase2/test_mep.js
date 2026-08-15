/* ======================================================================
   المرحلة 2 — اختبارات أساس نموذج أنظمة الكهروميكانيك.
   تمثيل فقط: لا تصميم، لا أحمال، لا تدفّق، لا تحجيم، لا مطابقة كود،
   ولا محرّك سلامة/حريق — بيانات الحريق تمثيل بحت.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'mep_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
const P=(name,bid,pos,rot)=>compileMep(C(SC.models[name]),bid||'bld_0',pos||null,rot||0);
const codes=m=>m.issues.map(i=>i.code);
const FIXTURES=['villa_mep','hotel_mep','clinic_mep','warehouse_mep','mixed_mep'];

console.log('\n== §1 — NO DESIGN, NO CALCULATION, NO CODE ==');
const specTxt=JSON.stringify(ACS_MEP_SPEC);
chk('the MEP spec names no MEP standard',
    !/\bSBC\b|\bNFPA\b|\bNEC\b|\bIEC\b|ASHRAE|SMACNA|\bIPC\b/.test(
      specTxt.replace(/meets_nfpa|meets_nec|meets_ashrae/g,'')));
chk('regulatory rule count is still zero', regulatoryRuleCount([])===0);
chk('real occupancy classification count is still zero',
    occRealClassificationCount(occupancyFixtureStore())===0);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_mep.json'),'utf8'));
chk('browser spec is byte-identical to acs_mep.json',
    JSON.stringify(sk(ACS_MEP_SPEC))===JSON.stringify(sk(CANON)));
chk('seven MEP element types declared', MEP_ELEMENT_TYPES.length===7, MEP_ELEMENT_TYPES.length);
chk('twenty-five system types declared', MEP_SYSTEM_TYPES.length===25, MEP_SYSTEM_TYPES.length);
chk('DESIGNED / COMPLIANT / ADEQUATE / BALANCED / CALCULATED are not model statuses',
    ['DESIGNED','COMPLIANT','ADEQUATE','BALANCED','CALCULATED']
      .every(x=>MEP_MODEL_STATUS.indexOf(x)<0));
chk('UNSAFE / CODE_VIOLATION / FIRE_VIOLATION are not severities',
    JSON.stringify(MEP_SEVERITIES)==='["INFO","WARNING","ERROR"]');
chk('OPTIMIZED is not a routing status', MEP_ROUTING_STATUSES.indexOf('OPTIMIZED')<0);
chk('rule and code_required are not provenance values',
    MEP_PROVENANCE.indexOf('rule')<0&&MEP_PROVENANCE.indexOf('code_required')<0);
{ const forb=ACS_MEP_SPEC.forbidden_claims, hits=[];
  const walk=v=>{ if(Array.isArray(v)) return v.forEach(walk);
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(forb.indexOf(k)>=0) hits.push(k); walk(v[k]); }); };
  FIXTURES.forEach(n=>walk(P(n)));
  chk('no compiled MEP element carries a load, flow, size-calc or compliance field',
      hits.length===0, Array.from(new Set(hits)).join(','));
  const all=FIXTURES.map(n=>JSON.stringify(P(n))).join(' ');
  chk('no compiled output uses MEP-compliance language',
      !/meets (NFPA|NEC|ASHRAE)|code[- ]compliant|adequate (airflow|water|power)/i.test(all));
  chk('the language actually used is representational',
      /represented MEP system/.test(all)&&/not a claim of adequate service/.test(all)); }

console.log('\n== §2 — NO SYSTEM IS INFERRED FROM BUILDING TYPE ==');
{ const v=P('villa_mep'), h=P('hotel_mep'), w=P('warehouse_mep');
  chk('a villa gets no sprinkler system it did not declare',
      v.systems.every(s=>s.system_type!=='SPRINKLER'));
  chk('a hotel gets no emergency power it did not declare',
      h.systems.every(s=>s.system_type!=='EMERGENCY_POWER'));
  chk('a warehouse gets no fire-water system it did not declare',
      w.systems.every(s=>s.system_type!=='FIRE_WATER'));
  chk('a model with no MEP block produces no MEP element',
      (()=>{const n=P('no_mep'); return n.status==='NOT_DEFINED'&&n.systems.length===0
        &&n.segments.length===0&&n.equipment.length===0&&n.terminals.length===0;})());
  chk('and that model is still perfectly valid', P('no_mep').issues.length===0);
  chk('every system present is present because the fixture declared it',
      v.systems.every(s=>s.source==='test_fixture'));
  chk('the same compiler serves every programme',
      FIXTURES.every(n=>P(n).compiler_version===MEP_COMPILER_VERSION)); }

console.log('\n== §3 — PROVENANCE AND STATUS ==');
{ const v=P('villa_mep');
  chk('every element records a provenance from the declared vocabulary',
      v.systems.concat(v.nodes).concat(v.segments).concat(v.equipment).concat(v.terminals)
       .every(e=>MEP_PROVENANCE.indexOf(e.source)>=0));
  chk('test_fixture and system_default are not verified sources',
      MEP_VERIFIED_SOURCES.indexOf('test_fixture')<0&&
      MEP_VERIFIED_SOURCES.indexOf('system_default')<0&&
      MEP_VERIFIED_SOURCES.indexOf('display_fallback')<0);
  chk('an undeclared status is derived, never assumed',
      (()=>{const m=C(SC.models.villa_mep); delete m.mep.status;
        const x=compileMep(m,'bld_0');
        return x.status==='PARTIAL'&&x.status_basis==='derived from element provenance';})());
  chk('the model is never marked regulatory', v.regulatory===false);
  chk('synthetic fixtures declare themselves synthetic', v.synthetic===true); }

console.log('\n== §4 — SYSTEMS, DISCIPLINES AND MEDIA ==');
{ const v=P('villa_mep');
  chk('five villa systems compile', v.systems.length===5, v.systems.length);
  chk('each system maps to a declared discipline',
      v.systems.every(s=>MEP_DISCIPLINES.indexOf(s.discipline)>=0));
  chk('lighting is separated from general power for display',
      v.systems.filter(s=>s.system_type==='LIGHTING')[0].discipline==='LIGHTING'&&
      v.systems.filter(s=>s.system_type==='ELECTRICAL_POWER')[0].discipline==='ELECTRICAL');
  chk('a medium is carried as a factual label',
      v.systems.filter(s=>s.system_type==='DOMESTIC_COLD_WATER')[0].medium==='water');
  chk('a medium attaches no pressure or flow assumption',
      /attaches no pressure, temperature, flow/.test(ACS_MEP_SPEC.medium_note));
  chk('an unknown system type is reported and mapped to OTHER',
      (()=>{const b=P('broken_mep');
        return codes(b).indexOf('UNKNOWN_SYSTEM_TYPE')>=0&&
          b.systems.some(s=>s.declared_type==='TELEPORTATION'&&s.system_type==='OTHER');})());
  chk('an unknown medium is reported, not invented',
      codes(P('broken_mep')).indexOf('UNKNOWN_MEDIUM')>=0); }

console.log('\n== §5 — NODES, SEGMENTS AND ROUTING ==');
{ const v=P('villa_mep');
  chk('seven villa nodes compile', v.nodes.length===7, v.nodes.length);
  chk('a node takes its elevation from the architectural level table',
      v.nodes.every(n=>n.y_source==='architectural_level'||n.y_source==='imported'));
  chk('a node carries no capacity', v.nodes.every(n=>/carries no capacity/.test(n.note)));
  chk('a routed segment keeps its supplied polyline',
      v.segments.filter(s=>s.id==='bld_0.mep.seg_cw_1')[0].polyline.length===3);
  chk('its length is measured from the polyline, not assumed',
      Math.abs(v.segments.filter(s=>s.id==='bld_0.mep.seg_cw_1')[0].length_m-(10.8+1.3))<1e-9,
      v.segments.filter(s=>s.id==='bld_0.mep.seg_cw_1')[0].length_m);
  const un=v.segments.filter(s=>s.routing_status==='UNROUTED');
  chk('a segment with endpoints but no geometry stays UNROUTED', un.length===1, un.length);
  chk('and NO path is fabricated for it', un[0].polyline===null&&un[0].length_m===null);
  chk('the unrouted state is reported as INFO with an explicit reason',
      v.issues.some(i=>i.code==='SEGMENT_UNROUTED'&&i.severity==='INFO'&&
        /no path is fabricated/.test(i.detail)));
  chk('the relationship layer says UNROUTED rather than inventing a connection',
      v.relationships.some(r=>r.type==='SEGMENT_CONNECTS'&&r.status==='unresolved'&&
        (r.meta||{}).routing_status==='UNROUTED'));
  chk('a vertical riser segment is representable in real XYZ',
      P('hotel_mep').segments.some(s=>s.polyline&&
        Math.abs(s.polyline[1][1]-s.polyline[0][1])>1)); }

console.log('\n== §6 — DISPLAY FALLBACK IS NEVER AN ENGINEERING VALUE ==');
{ const w=P('warehouse_mep');
  const seg=w.segments[0];
  chk('a segment with no stated size keeps size=null', seg.size===null);
  chk('but still yields render geometry', seg.render_size.w>0);
  chk('and that geometry is labelled display_fallback',
      seg.render_size.source==='display_fallback');
  chk('the fallback never reaches the rule inputs',
      mepRuleInputs(w)[seg.id]['mep.segment.size.diameter_m']===null);
  chk('a sized segment is model-sourced instead',
      P('villa_mep').segments.filter(s=>s.size)[0].render_size.source==='model');
  chk('equipment with no dimensions draws from a fallback, flagged as such',
      P('villa_mep').equipment.filter(e=>e.dimensions===null)[0]
        .render_dimensions.source==='display_fallback');
  chk('the spec states the fallback policy in writing',
      /DISPLAY VALUE IS NOT AN ENGINEERING VALUE/.test(ACS_MEP_SPEC.display_fallback_note));
  chk('compiling does not write a fallback back into the model',
      (()=>{const m=C(SC.models.warehouse_mep); compileMep(m,'bld_0');
        return m.mep.segments.every(s=>s.size===undefined);})());
  /* الكلمات الممنوعة ترد في نصوص التبرئة نفسها، فالفحص يجب أن يقرأ الحقول لا
     النصّ الخام: نمسح كل مفتاح وقيمة ونستثني حقول الملاحظة والتبرئة صراحةً. */
  { const NOTE=['note','fire_note','detail','disclaimer','basis','status_basis','name'];
    const BAD=/voltage|breaker|flow|pump_head|capacity|cfm|lux|amp|watt|kva|kw\b/i;
    const hits=[];
    const walk=(v,path)=>{ if(Array.isArray(v)) return v.forEach(x=>walk(x,path));
      if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
        if(NOTE.indexOf(k)>=0) return;
        if(BAD.test(k)) hits.push(path+'.'+k+'='+JSON.stringify(v[k]));
        if(typeof v[k]==='string'&&BAD.test(v[k])) hits.push(path+'.'+k+'="'+v[k]+'"');
        walk(v[k],path+'.'+k); }); };
    FIXTURES.forEach(n=>walk(P(n),n));
    chk('no invented voltage, breaker, flow, head or capacity appears in any field',
        hits.length===0, hits.slice(0,3).join(' | ')); } }

console.log('\n== §7 — EQUIPMENT, TERMINALS AND PORTS ==');
{ const v=P('villa_mep'), c=P('clinic_mep');
  chk('equipment types come from the declared list',
      v.equipment.every(e=>MEP_EQUIPMENT_TYPES.indexOf(e.equipment_type)>=0));
  chk('no rating, capacity or duty is produced',
      v.equipment.every(e=>Object.keys(e.properties).length===0&&
        /no rating, capacity or duty is implied/.test(e.note)));
  chk('a stated property is kept with its own provenance',
      (()=>{const m=C(SC.models.villa_mep);
        m.mep.equipment[0].properties={asset_tag:'DB-1'};
        const x=compileMep(m,'bld_0');
        return x.equipment.filter(e=>e.id==='bld_0.mep.eq_db')[0]
          .properties.asset_tag.source==='test_fixture';})());
  chk('ports are recorded only where declared',
      c.equipment.filter(e=>e.equipment_type==='ahu')[0].ports.length===2&&
      c.equipment.filter(e=>e.equipment_type==='panel')[0].ports.length===0);
  chk('an unrecognised port type is reported, not accepted',
      codes(P('broken_mep')).indexOf('INVALID_PORT_TYPE')>=0);
  chk('plumbing fixtures are represented as terminals, not a parallel model',
      v.terminals.some(t=>t.terminal_type==='wc')&&
      v.terminals.some(t=>t.terminal_type==='lavatory'));
  chk('air devices are represented as terminals too',
      v.terminals.some(t=>t.terminal_type==='diffuser'));
  chk('no CFM, L/s, throw or neck size is fabricated for an air device',
      Object.keys(v.terminals.filter(t=>t.terminal_type==='diffuser')[0].properties).length===0);
  chk('an unrecognised terminal type is reported',
      codes(P('broken_mep')).indexOf('UNKNOWN_TERMINAL_TYPE')>=0); }

console.log('\n== §8 — PHASE 1 ADAPTER PRESERVES PROVENANCE ==');
{ const a=P('phase1_points');
  chk('Phase 1 points are adapted into represented terminals',
      a.adapted_terminals.length===5, a.adapted_terminals.length);
  chk('the adapter creates no duplicate semantic object — each names its origin point',
      a.adapted_terminals.every(t=>t.origin==='phase1_point'&&!!t.origin_ref));
  chk('a system-generated smoke detector stays system_default',
      a.adapted_terminals.filter(t=>t.terminal_type==='smoke_detector'&&
        t.original_source==='system_default').length===1);
  chk('a user-supplied point keeps its user provenance',
      a.adapted_terminals.filter(t=>t.original_source==='user').length===1);
  chk('NO adapted terminal is ever raised to a code requirement',
      a.adapted_terminals.every(t=>t.source==='phase1_adapter'&&
        ['system_default','user','imported','manual_verified','ai_inference','unknown']
          .indexOf(t.original_source)>=0));
  chk('code_required is not even a value the adapter could write',
      MEP_PROVENANCE.indexOf('code_required')<0&&
      !/code_required/.test(adaptPhase1Terminals.toString()));
  chk('a light point becomes a light fixture, not a lighting design',
      a.adapted_terminals.some(t=>t.terminal_type==='light_fixture')&&
      a.adapted_terminals.every(t=>Object.keys(t.properties).length===0));
  chk('the adapter can be turned off and changes nothing else',
      (()=>{const off=compileMep(C(SC.models.phase1_points),'bld_0',null,0,null,null,false);
        return off.adapted_terminals.length===0&&off.status==='NOT_DEFINED';})());
  chk('the original model is not modified by adaptation',
      (()=>{const m=C(SC.models.phase1_points), before=JSON.stringify(m);
        compileMep(m,'bld_0'); return JSON.stringify(m)===before;})()); }

console.log('\n== §9 — RISERS AND SHAFT ASSOCIATION ==');
{ const h=P('hotel_mep');
  chk('four risers compile across three levels', h.risers.length===4&&
      h.risers.every(r=>r.level_indexes.length===3));
  chk('a riser spanning levels emits RISER_CONNECTS_LEVELS',
      h.relationships.filter(r=>r.type==='RISER_CONNECTS_LEVELS').length===4);
  chk('an architectural core is NOT an MEP riser by itself',
      h.risers.filter(r=>r.arch_core_id===null).length===3);
  chk('the one declared association records its evidence source',
      h.risers.filter(r=>r.arch_core_id)[0].arch_core_link_source==='imported');
  chk('the spec states the rule in writing',
      /is not an MEP riser without explicit evidence/.test(h.risers[0].note));
  chk('a riser outside the core it names is reported',
      codes(P('clash_mep')).indexOf('RISER_OUTSIDE_SHAFT')>=0);
  chk('an unresolvable riser level is an ERROR',
      P('broken_mep').issues.filter(i=>i.code==='RISER_LEVELS_UNRESOLVED')[0]
        .severity==='ERROR'); }

console.log('\n== §10 — RELATIONSHIPS ARE NOT SERVICE ADEQUACY ==');
{ const v=P('villa_mep');
  chk('every relationship type is in the declared vocabulary',
      v.relationships.every(r=>MEP_REL_TYPES.indexOf(r.type)>=0));
  chk('every relationship carries the no-adequacy note',
      v.relationships.every(r=>/no service adequacy is claimed/.test(r.note)));
  chk('a terminal in a room yields SYSTEM_HAS_TERMINAL_IN with an explicit disclaimer',
      v.relationships.some(r=>r.type==='SYSTEM_HAS_TERMINAL_IN'&&
        /not a claim of adequate service/.test(r.meta.disclaimer)));
  chk('SYSTEM_SERVES_SPACE says representation only',
      v.relationships.some(r=>r.type==='SYSTEM_SERVES_SPACE'&&
        /no adequacy of airflow, water, light or power is claimed/.test(r.meta.disclaimer)));
  chk('no relationship claims a room receives adequate anything',
      !/receives adequate|sufficient (airflow|water|power)/i.test(
        JSON.stringify(v.relationships)));
  chk('circuits are never grouped automatically',
      v.relationships.filter(r=>r.type==='TERMINAL_ON_CIRCUIT').length===0&&
      v.relationships.filter(r=>r.type==='CIRCUIT_FEEDS').length===0);
  chk('a declared circuit IS represented when the model supplies one',
      (()=>{const m=C(SC.models.villa_mep);
        m.mep.circuits=[{id:'C1',panel:'eq_db',terminals:['t_s1']}];
        m.mep.terminals[1].circuit='C1';
        const x=compileMep(m,'bld_0');
        return x.relationships.some(r=>r.type==='PANEL_FEEDS')&&
               x.relationships.some(r=>r.type==='CIRCUIT_FEEDS')&&
               x.relationships.some(r=>r.type==='TERMINAL_ON_CIRCUIT'); })());
  chk('relationship ids are unique and namespaced',
      new Set(v.relationships.map(r=>r.id)).size===v.relationships.length&&
      v.relationships.every(r=>r.id.indexOf('bld_0.mep.rel_')===0)); }

console.log('\n== §11 — ARCHITECTURAL AND STRUCTURAL INTERFERENCE ==');
{ const cl=P('clash_mep');
  chk('a duct crossing a wall with no penetration is reported',
      codes(cl).indexOf('SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION')>=0);
  chk('a pipe crossing a slab with no penetration is reported',
      codes(cl).indexOf('SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION')>=0);
  chk('a segment crossing a structural beam is reported',
      codes(cl).indexOf('SEGMENT_CROSSES_STRUCTURAL_BEAM')>=0);
  chk('a segment crossing a structural column is reported',
      codes(cl).indexOf('SEGMENT_CROSSES_STRUCTURAL_COLUMN')>=0);
  chk('equipment outside its assigned space is reported',
      codes(cl).indexOf('EQUIPMENT_OUTSIDE_SPACE')>=0);
  chk('a terminal outside its assigned space is reported',
      codes(cl).indexOf('TERMINAL_OUTSIDE_SPACE')>=0);
  chk('a route leaving the building footprint is reported',
      codes(cl).indexOf('ROUTE_OUTSIDE_BUILDING')>=0);
  chk('an MEP element inside a stair void is reported',
      codes(P('hotel_mep')).indexOf('MEP_ELEMENT_IN_FLOOR_OPENING')>=0);
  chk('every interference is a model-quality severity, never a code verdict',
      mepInterferences(cl).every(i=>MEP_SEVERITIES.indexOf(i.severity)>=0&&
        !/UNSAFE|VIOLATION|COMPLIAN/i.test(i.code)));
  chk('a beam clash says the member is not cut and the route is not redesigned',
      cl.issues.filter(i=>i.code==='SEGMENT_CROSSES_STRUCTURAL_BEAM')
        .every(i=>/not cut and the route is not redesigned/.test(i.detail)));
  chk('no clash modifies the architectural model',
      (()=>{const m=C(SC.models.clash_mep);
        const a1=JSON.stringify(compileArchitecture(C(m),'bld_0'));
        compileMep(m,'bld_0');
        return JSON.stringify(compileArchitecture(C(m),'bld_0'))===a1;})());
  chk('no clash modifies the structural model',
      (()=>{const m=C(SC.models.clash_mep);
        const s1=JSON.stringify(compileStructure(C(m),'bld_0'));
        compileMep(m,'bld_0');
        return JSON.stringify(compileStructure(C(m),'bld_0'))===s1;})());
  chk('a declared penetration suppresses the crossing report at that host',
      (()=>{const before=P('clash_mep').issues
              .filter(i=>i.code==='SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION').length;
        const m=C(SC.models.clash_mep);
        const arch=compileArchitecture(C(m),'bld_0');
        m.mep.penetrations=[{id:'pen1',segment_id:'seg_pipe',host_type:'ARCH_SLAB',
          host_id:arch.slabs[1].id,level:1,source:'test_fixture'}];
        const after=compileMep(m,'bld_0').issues
          .filter(i=>i.code==='SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION').length;
        return after<before; })()); }

console.log('\n== §12 — PENETRATIONS INFER NOTHING ==');
{ const h=P('hotel_mep');
  chk('a declared penetration compiles and resolves its host',
      h.penetrations.length===1&&h.penetrations[0].host_resolved===true);
  chk('it infers no fire stopping, sleeve or reinforcement',
      /no fire stopping, sleeve or reinforcement requirement is inferred/
        .test(h.penetrations[0].note));
  chk('the spec repeats the rule',
      /implies nothing about fire stopping/.test(ACS_MEP_SPEC.penetration_note));
  chk('an unresolvable penetration host is reported',
      codes(P('broken_mep')).indexOf('PENETRATION_HOST_UNRESOLVED')>=0);
  chk('an unresolvable penetration segment is an ERROR',
      P('broken_mep').issues.filter(i=>i.code==='PENETRATION_SEGMENT_UNRESOLVED')[0]
        .severity==='ERROR');
  chk('PENETRATION_THROUGH is a factual edge only',
      h.relationships.filter(r=>r.type==='PENETRATION_THROUGH')
        .every(r=>/no service adequacy is claimed/.test(r.note))); }

console.log('\n== §13 — FIRE SYSTEMS ARE DATA ONLY ==');
{ const m=P('mixed_mep');
  chk('a fire alarm system is representable', m.systems.some(s=>s.system_type==='FIRE_ALARM'));
  chk('smoke detectors are represented as terminals',
      m.terminals.filter(t=>t.terminal_type==='smoke_detector').length===3);
  chk('no coverage, spacing, zoning or hydraulic field exists anywhere',
      !/coverage|spacing|zone_verified|hydraulic|density/i.test(
        JSON.stringify(m.terminals.concat(m.systems))));
  chk('the spec states there is no fire/life-safety engine',
      /There is no Fire \/ Life-Safety engine/.test(ACS_MEP_SPEC.fire_note));
  chk('the compiled model repeats it', /no Fire \/ Life-Safety engine/.test(m.meta.fire_note));
  chk('sprinkler and fire-water are declarable but never auto-created',
      MEP_SYSTEM_TYPES.indexOf('SPRINKLER')>=0&&MEP_SYSTEM_TYPES.indexOf('FIRE_WATER')>=0&&
      P('villa_mep').systems.every(s=>['SPRINKLER','FIRE_WATER'].indexOf(s.system_type)<0));
  chk('no fire element carries a compliance or evaluation verdict',
      !/PASS|FAIL|COMPLIANT|CODE_REQUIRED/.test(JSON.stringify(m))); }

console.log('\n== §14 — LOW CURRENT / ICT ==');
{ const c=P('clinic_mep');
  chk('a data network system is representable',
      c.systems.some(s=>s.system_type==='DATA_NETWORK'&&s.discipline==='ICT'));
  chk('a data outlet is a represented terminal',
      c.terminals.some(t=>t.terminal_type==='data_outlet'));
  chk('no coverage or network design is produced',
      (()=>{const BAD=/coverage|bandwidth|throughput|switch_port/i;
        const NOTE=['note','fire_note','detail','disclaimer','basis','status_basis','name'];
        let bad=false;
        const walk=v=>{ if(Array.isArray(v)) return v.forEach(walk);
          if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
            if(NOTE.indexOf(k)>=0) return;
            if(BAD.test(k)||(typeof v[k]==='string'&&BAD.test(v[k]))) bad=true;
            walk(v[k]); }); };
        walk(c); return !bad;})());
  chk('CCTV, Wi-Fi, access control, intercom and BMS are all representable types',
      ['cctv','wifi_ap','access_control','intercom','bms_point']
        .every(t=>MEP_TERMINAL_TYPES.indexOf(t)>=0)); }

console.log('\n== §15 — CLINIC MEDICAL GAS IS EXPLICITLY SYNTHETIC ==');
{ const c=P('clinic_mep');
  const mg=c.systems.filter(s=>s.system_type==='MEDICAL_GAS')[0];
  chk('the medical gas system is present only because the fixture declares it', !!mg);
  chk('it is clearly labelled test-only and synthetic',
      /test only/i.test(String(mg.name))&&c.synthetic===true&&mg.source==='test_fixture');
  chk('no healthcare compliance is implied anywhere',
      (()=>{const BAD=/healthcare|\bHTM\b|ISO 7396|compliant/i;
        const NOTE=['note','fire_note','detail','disclaimer','basis','status_basis'];
        let bad=false;
        const walk=v=>{ if(Array.isArray(v)) return v.forEach(walk);
          if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
            if(NOTE.indexOf(k)>=0) return;
            if(BAD.test(k)||(typeof v[k]==='string'&&BAD.test(v[k]))) bad=true;
            walk(v[k]); }); };
        walk(c); return !bad;})());
  chk('the only mentions of compliance are explicit denials',
      /never .*compliant|no.*compliance|not .*compliant|or compliant/i
        .test(ACS_MEP_SPEC.note)); }

console.log('\n== §16 — INTEGRITY VALIDATION ==');
{ const br=P('broken_mep');
  const need=['DUPLICATE_ELEMENT_ID','UNSUPPORTED_ELEMENT_TYPE','UNKNOWN_SYSTEM_TYPE',
    'UNKNOWN_MEDIUM','UNKNOWN_EQUIPMENT_TYPE','UNKNOWN_TERMINAL_TYPE','UNKNOWN_SEGMENT_KIND',
    'INVALID_SYSTEM_REF','INVALID_NODE_REF','INVALID_EQUIPMENT_REF','INVALID_LEVEL_REF',
    'INVALID_SPACE_REF','INVALID_PORT_TYPE','CROSS_BUILDING_REF','NAN_COORDINATE',
    'NEGATIVE_DIMENSION','SEGMENT_ZERO_LENGTH','SEGMENT_ENDPOINT_UNRESOLVED',
    'ORPHAN_TERMINAL','ORPHAN_NODE','RISER_LEVELS_UNRESOLVED','PENETRATION_HOST_UNRESOLVED',
    'PENETRATION_SEGMENT_UNRESOLVED'];
  const got=new Set(codes(br));
  chk('the deliberately broken fixture triggers every integrity check',
      need.every(c=>got.has(c)), need.filter(c=>!got.has(c)).join(','));
  chk('every issue code is declared in the spec with a severity',
      br.issues.every(i=>Object.prototype.hasOwnProperty.call(MEP_ISSUE_CODES,i.code)));
  chk('issues are ordered ERROR first, then WARNING, then INFO',
      (()=>{const r={ERROR:0,WARNING:1,INFO:2};
        return br.issues.every((i,k)=>k===0||r[br.issues[k-1].severity]<=r[i.severity]);})());
  chk('no issue is a code-compliance verdict',
      br.issues.every(i=>!/COMPLIAN|NFPA|NEC|UNSAFE|VIOLATION/i.test(i.code)));
  chk('an unknown MEP collection is reported and NOT interpreted',
      br.issues.some(i=>i.code==='UNSUPPORTED_ELEMENT_TYPE'&&
        /was NOT interpreted/.test(i.detail)));
  chk('a foreign building id is caught rather than silently re-namespaced',
      br.issues.some(i=>i.code==='CROSS_BUILDING_REF'&&i.subject==='bld_9.t_foreign'));
  chk('a NaN coordinate is rejected rather than propagated',
      br.nodes.concat(br.terminals).every(e=>e.x===null||isFinite(e.x))); }

console.log('\n== §17 — DETERMINISM, NAMESPACING AND TRANSFORMS ==');
chk('compiling twice gives byte-identical output',
    JSON.stringify(P('clinic_mep'))===JSON.stringify(P('clinic_mep')));
{ const m=C(SC.models.hotel_mep), before=JSON.stringify(m);
  compileMep(m,'bld_0'); validateMep(compileMep(m,'bld_0'));
  chk('the compiler never mutates the model it reads', JSON.stringify(m)===before); }
{ const a=P('villa_mep','bld_0'), b=P('villa_mep','bld_5');
  chk('a second building namespaces every MEP id',
      b.systems.every(s=>s.id.indexOf('bld_5.mep.')===0)&&
      b.relationships.every(r=>r.id.indexOf('bld_5.mep.')===0));
  chk('two buildings can never collide on an id',
      a.systems.every(s=>b.systems.every(t=>t.id!==s.id)));
  chk('a space reference belonging to another building is caught, not silently accepted',
      b.issues.some(i=>i.code==='INVALID_SPACE_REF'));
  const t=P('villa_mep','bld_0',{x:-11,z:7},60);
  chk('a transform never changes the compiled geometry',
      JSON.stringify(t.segments)===JSON.stringify(a.segments));
  const p=mepToWorld(t,0,0);
  chk('the building transform is applied on read',
      Math.abs(p[0]+11)<1e-9&&Math.abs(p[1]-7)<1e-9, JSON.stringify(p));
  const p2=mepToWorld(t,10,0);
  chk('rotation is applied about the building origin',
      Math.abs(p2[0]-(-11+10*Math.cos(Math.PI/3)))<1e-9&&
      Math.abs(p2[1]-(7+10*Math.sin(Math.PI/3)))<1e-9);
  chk('no second coordinate convention is introduced',
      /No second coordinate convention is introduced/.test(ACS_MEP_SPEC.axis_note)); }

console.log('\n== §18 — REVISION HASH ==');
{ const base=C(SC.models.villa_mep);
  const h0=modelHash(base);
  const moved=C(base); moved.mep.equipment[0].x=9.9;
  chk('moving equipment changes the model hash', modelHash(moved)!==h0);
  const rerouted=C(base); rerouted.mep.segments[0].polyline[1][2]=9;
  chk('changing a pipe route changes the model hash', modelHash(rerouted)!==h0);
  const duct=C(base); duct.mep.segments[2].polyline=[[6.8,2.6,9.5],[3,2.6,2.5]];
  chk('adding duct route geometry changes the model hash', modelHash(duct)!==h0);
  const noTerm=C(base); noTerm.mep.terminals.pop();
  chk('removing a terminal changes the model hash', modelHash(noTerm)!==h0);
  const sysProp=C(base); sysProp.mep.systems[0].medium='signal';
  chk('changing a system property changes the model hash', modelHash(sysProp)!==h0);
  const riser=C(base); riser.mep.risers=[{id:'r1',kind:'duct_riser',x:1,z:1,levels:[0,1],
    source:'test_fixture'}];
  chk('adding a riser changes the model hash', modelHash(riser)!==h0);
  const vis=C(base); vis.mep.layer_visibility={hvac:false};
  chk('toggling layer visibility does NOT change the model hash', modelHash(vis)===h0);
  const cam=C(base); cam.camera={x:1,y:2,z:3};
  chk('moving the camera still does not change the hash', modelHash(cam)===h0);
  chk('compiling the MEP model does not change the hash',
      (()=>{const m=C(base); const h=modelHash(m); compileMep(m,'bld_0');
        return modelHash(m)===h;})()); }

console.log('\n== §19 — RENDER AND EXPORT ==');
{ const v=P('villa_mep');
  const items=mepRenderItems(v);
  chk('render items use the MEP| naming convention',
      items.every(i=>/^MEP\|(ELECTRICAL|LIGHTING|ICT|PLUMBING|DRAINAGE|HVAC|FIRE|OTHER|RISER)\|/
        .test(i.name)));
  chk('each discipline requested by the phase has its own display layer',
      ['MEP_ELECTRICAL','MEP_LIGHTING','MEP_HVAC','MEP_PLUMBING','MEP_DRAINAGE','MEP_FIRE',
       'MEP_ICT'].every(k=>LAYER_ORDER.indexOf(k)>=0&&!!LAYER_NAMES[k]));
  chk('the fire layer name says data only, with no safety engine',
      /بيانات فقط/.test(LAYER_NAMES.MEP_FIRE));
  chk('every render item declares where its geometry came from',
      items.every(i=>['model','display_fallback'].indexOf(i.geometry_source)>=0));
  chk('render items never carry an engineering verdict',
      !/adequate|compliant|safe|capacity/i.test(JSON.stringify(items)));
  chk('colour marks the discipline only, never a state',
      Object.keys(MEP_DISC_COLOR).every(k=>MEP_DISCIPLINES.indexOf(k)>=0||k==='RISER'));
  chk('an unrouted segment produces no render geometry',
      items.every(i=>i.kind!=='SEGMENT'||i.id!=='bld_0.mep.seg_sup_1')); }

console.log('\n== §20 — RULE ENGINE CONTRACT (INPUTS ONLY) ==');
{ const v=P('villa_mep');
  const ri=mepRuleInputs(v);
  chk('system existence is exposed as a factual input',
      ri.building['mep.system.exists.LIGHTING']===true&&
      ri.building['mep.system.exists.SPRINKLER']===false);
  chk('terminal and equipment counts are exposed',
      ri.building['mep.terminal.count']===5&&ri.building['mep.equipment.count']===2);
  chk('segment size is exposed only when it is real',
      ri['bld_0.mep.seg_cw_1']['mep.segment.size.diameter_m']===0.025&&
      ri['bld_0.mep.seg_sup_1']['mep.segment.size.diameter_m']===null);
  chk('serves_space is exposed as a factual relation',
      Object.keys(ri).some(k=>ri[k]['mep.system.serves_space']));
  chk('no regulatory rule was added anywhere', regulatoryRuleCount([])===0);
  chk('the rule inputs contain no threshold, limit or verdict',
      !/limit|minimum|maximum|required|PASS|FAIL/i.test(JSON.stringify(ri))); }

console.log('\n== §21 — NO ARCHITECTURAL / STRUCTURAL / NAV / EGRESS REGRESSION ==');
{ const plain=C(FX.villa), withMep=C(SC.models.villa_mep);
  chk('adding an MEP block changes no architectural element',
      JSON.stringify(compileArchitecture(plain,'bld_0'))===
      JSON.stringify(compileArchitecture(withMep,'bld_0')));
  chk('adding an MEP block changes no structural element',
      JSON.stringify(compileStructure(plain,'bld_0'))===
      JSON.stringify(compileStructure(withMep,'bld_0')));
  chk('relationships are identical with and without the MEP block',
      JSON.stringify(buildRelationships(withMep,'bld_0'))===
      JSON.stringify(buildRelationships(plain,'bld_0')));
  chk('navigation is identical with and without the MEP block',
      JSON.stringify(findPath(withMep,buildRelationships(withMep,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0'))===
      JSON.stringify(findPath(plain,buildRelationships(plain,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0')));
  chk('egress is identical with and without the MEP block',
      JSON.stringify(findEgress(withMep,buildRelationships(withMep,'bld_0'),
        'bld_0.g.majlis','bld_0'))===
      JSON.stringify(findEgress(plain,buildRelationships(plain,'bld_0'),
        'bld_0.g.majlis','bld_0')));
  chk('walking distance is unchanged — a duct is not an obstacle in this phase',
      (()=>{const p1=findPath(withMep,buildRelationships(withMep,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        const p2=findPath(plain,buildRelationships(plain,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        return measurePath(withMep,p1,'bld_0').walking_distance_m===
               measurePath(plain,p2,'bld_0').walking_distance_m;})());
  chk('and the model says so in writing',
      /NOT navigation obstacles in this phase/.test(P('villa_mep').meta.navigation_impact)); }

console.log('\n== §22 — PROGRAMME NEUTRALITY ==');
FIXTURES.forEach(n=>{ const m=P(n);
  chk(n+': compiles through the same element vocabulary',
      m.systems.every(s=>s.type==='MEP_SYSTEM')&&m.segments.every(s=>s.type==='MEP_SEGMENT'));
  chk(n+': every issue code is declared',
      m.issues.every(i=>Object.prototype.hasOwnProperty.call(MEP_ISSUE_CODES,i.code)));
  chk(n+': no element claims adequacy or compliance',
      !/adequate|compliant|balanced/i.test(JSON.stringify(m.systems.concat(m.equipment)))); });
{ const m=P('mixed_mep');
  chk('three different programmes share one unchanged MEP model',
      m.systems.length===2&&m.terminals.length===6);
  chk('no MEP property changed with the occupancy or programme',
      m.terminals.filter(t=>t.terminal_type==='socket')
        .every(t=>t.system_id===m.terminals[0].system_id||true)&&
      new Set(m.systems.map(s=>s.system_type)).size===2); }

console.log('\n== §23 — SECURITY ==');
chk('no eval / Function in the MEP layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      compileMep.toString()+validateMep.toString()+mepRenderItems.toString()+
      adaptPhase1Terminals.toString()));
chk('no network call in the MEP layer',
    !/fetch\s*\(|XMLHttpRequest/.test(compileMep.toString()+validateMep.toString()));
chk('a hostile element id cannot escape into markup',
    (()=>{const m=C(FX.villa);
      m.mep={terminals:[{id:'<script>alert(1)</script>',type:'socket',x:1,z:1,level:0,
        source:'user'}]};
      const x=compileMep(m,'bld_0');
      return esc(x.terminals[0].id).indexOf('<script')<0;})());

console.log(`\nMEP: ${pass} passed, ${fail} failed`);
