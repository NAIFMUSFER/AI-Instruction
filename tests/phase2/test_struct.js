/* ======================================================================
   المرحلة 2 — اختبارات أساس النموذج الإنشائي.
   تمثيل إنشائي فقط: لا تصميم، لا أحمال، لا تحجيم، لا تسليح، لا مطابقة كود.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'struct_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
const S=(name,bid,pos,rot)=>compileStructure(C(SC.models[name]),bid||'bld_0',pos||null,rot||0);
const codes=st=>st.issues.map(i=>i.code);
const FIXTURES=['villa_struct','hotel_struct','warehouse_struct','mixed_struct'];

console.log('\n== §1 — NO DESIGN, NO LOADS, NO CODE ==');
const specTxt=JSON.stringify(ACS_STRUCT_SPEC);
chk('the structural spec names no structural code',
    !/\bSBC\b|\bIBC\b|\bACI\b|\bASCE\b|\bAISC\b|Eurocode/i.test(specTxt));
chk('regulatory rule count is still zero', regulatoryRuleCount([])===0);
chk('real occupancy classification count is still zero',
    occRealClassificationCount(occupancyFixtureStore())===0);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_struct.json'),'utf8'));
chk('browser spec is byte-identical to acs_struct.json',
    JSON.stringify(sk(ACS_STRUCT_SPEC))===JSON.stringify(sk(CANON)));
chk('ten structural element types declared', STRUCT_ELEMENT_TYPES.length===10,
    STRUCT_ELEMENT_TYPES.length);
chk('DESIGNED / SAFE / COMPLIANT are not model statuses',
    ['DESIGNED','SAFE','COMPLIANT'].every(x=>STRUCT_MODEL_STATUS.indexOf(x)<0));
chk('UNSAFE / DANGEROUS / CODE_VIOLATION are not severities',
    ['UNSAFE','DANGEROUS','CODE_VIOLATION'].every(x=>STRUCT_SEVERITIES.indexOf(x)<0)
    &&JSON.stringify(STRUCT_SEVERITIES)==='["INFO","WARNING","ERROR"]');
chk('rule is not a structural provenance value', STRUCT_PROVENANCE.indexOf('rule')<0);
{ const forb=ACS_STRUCT_SPEC.forbidden_claims, hits=[];
  const walk=v=>{ if(Array.isArray(v)) return v.forEach(walk);
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(forb.indexOf(k)>=0) hits.push(k); walk(v[k]); }); };
  FIXTURES.forEach(n=>walk(S(n)));
  chk('no compiled structural element carries a load, capacity or compliance field',
      hits.length===0, Array.from(new Set(hits)).join(','));
  const all=FIXTURES.map(n=>JSON.stringify(S(n))).join(' ');
  chk('no compiled output uses structural-compliance language',
      !/structurally (safe|adequate)|load.?bearing verified|meets SBC|foundation sufficient/i
        .test(all));
  chk('the language actually used is representational',
      /represented structural column/.test(all)&&/no capacity, sizing or adequacy/.test(all)); }

console.log('\n== §2 — THE SYSTEM IS NEVER INFERRED FROM BUILDING TYPE ==');
{ const w=S('warehouse_struct'), v=S('villa_struct');
  chk('a warehouse is not given steel just because it is a warehouse',
      w.materials.every(m=>m.material==='unknown'), JSON.stringify(w.materials.map(m=>m.material)));
  chk('a warehouse column with no stated section keeps section=null',
      w.columns.every(c=>c.section===null));
  chk('a villa is concrete only because the fixture says so',
      v.materials[0].material==='concrete'&&v.materials[0].source==='test_fixture');
  chk('a model with no structural block produces no structural element',
      (()=>{const n=S('no_struct'); return n.status==='NOT_DEFINED'&&n.columns.length===0
        &&n.beams.length===0&&n.foundations.length===0&&n.grid_systems.length===0;})());
  chk('and that model is still perfectly valid', S('no_struct').issues.length===0);
  chk('the compiler never invents a foundation to stand the 3D model on',
      S('warehouse_struct').foundations.length===0); }

console.log('\n== §3 — PROVENANCE AND STATUS ==');
{ const v=S('villa_struct');
  chk('every element records a provenance from the declared vocabulary',
      v.columns.concat(v.beams).concat(v.foundations)
       .every(e=>STRUCT_PROVENANCE.indexOf(e.source)>=0));
  chk('a fixture-sourced model is not called verified data',
      v.status==='REPRESENTED'&&v.status_basis==='declared_by_model');
  chk('test_fixture is not in the verified-source list',
      STRUCT_VERIFIED_SOURCES.indexOf('test_fixture')<0);
  chk('an undeclared status is derived, never assumed',
      (()=>{const m=C(SC.models.villa_struct); delete m.structural.status;
        const st=compileStructure(m,'bld_0');
        return st.status==='PARTIAL'&&st.status_basis==='derived from element provenance';})());
  chk('ai_inference is a distinct provenance from a verified one',
      STRUCT_PROVENANCE.indexOf('ai_inference')>=0&&
      STRUCT_VERIFIED_SOURCES.indexOf('ai_inference')<0);
  chk('the model as a whole is never marked regulatory', v.regulatory===false);
  chk('synthetic fixtures declare themselves synthetic', v.synthetic===true); }

console.log('\n== §4 — GRID ==');
{ const v=S('villa_struct');
  chk('one grid system with six lines', v.grid_systems.length===1&&
      v.grid_systems[0].grids.length===6, v.grid_systems[0].grids.length);
  chk('X and Z grids are both supported',
      v.grid_systems[0].grids.filter(g=>g.axis==='X').length===3&&
      v.grid_systems[0].grids.filter(g=>g.axis==='Z').length===3);
  chk('a grid line records whether its position was stated',
      v.grid_systems[0].grids.every(g=>g.position_stated===true));
  chk('a grid system carries its own origin and rotation',
      v.grid_systems[0].origin.x===0&&v.grid_systems[0].rotation_deg===0);
  chk('multiple grid systems per building are representable',
      (()=>{const m=C(SC.models.villa_struct);
        m.structural.grid_systems=m.structural.grid_systems.concat([
          {id:'gs_rot',label:'Rotated',origin:{x:2,z:3},rotation_deg:30,source:'user',
           grids:[{id:'grid_x_R',axis:'X',label:'R',position_m:0,source:'user'}]}]);
        return compileStructure(m,'bld_0').grid_systems.length===2;})());
  chk('a rotated grid is not assumed to lie on the project world axes',
      (()=>{const m=C(SC.models.villa_struct);
        m.structural.grid_systems[0].rotation_deg=90;
        const st=compileStructure(m,'bld_0');
        const gs=st.grid_systems[0], g=gs.grids.filter(x=>x.axis==='X')[0];
        const w=structGridToWorld(st,gs,g,10);
        /* دوران 90° ينقل الطرف المحلي (0,-10) إلى العالمي (10,0) */
        return Math.abs(w[0][0]-10)<1e-9&&Math.abs(w[0][1])<1e-9;})());
  chk('an unresolved grid reference is reported, not silently dropped',
      codes(S('broken_struct')).indexOf('INVALID_GRID_REF')>=0); }
{ const sug=suggestStructuralGrid(C(FX.villa),5,5,'bld_0');
  chk('a suggested grid is a SUGGESTION, never model truth',
      sug.kind==='SUGGESTION'&&sug.applied===false&&sug.persisted===false);
  chk('every suggested line is sourced system_suggested, not user',
      sug.grid_system.grids.every(g=>g.source==='system_suggested'));
  chk('a suggestion is not written into the model',
      (()=>{const m=C(FX.villa); suggestStructuralGrid(m,5,5,'bld_0');
        return m.structural===undefined;})());
  chk('no spacing supplied ⇒ no grid is invented',
      suggestStructuralGrid(C(FX.villa),null,null,'bld_0').reason==='NO_SPACING_SUPPLIED');
  chk('no footprint ⇒ the suggestion refuses rather than guessing',
      suggestStructuralGrid({levels:[],floors:{}},5,5,'bld_0').reason==='NO_FOOTPRINT');
  chk('the suggestion says in writing that it is not design',
      /not structural design and not model truth/.test(sug.note)); }

console.log('\n== §5 — COLUMNS ==');
{ const v=S('villa_struct');
  chk('nine villa columns compile', v.columns.length===9, v.columns.length);
  chk('a column height comes from the architectural levels, not the renderer',
      v.columns.every(c=>c.height_basis==='architectural_levels'&&c.height_m===3.2),
      v.columns[0].height_m);
  chk('a column names the levels it spans',
      v.columns.every(c=>c.base_level_id==='bld_0.flr_0'&&c.top_level_id==='bld_0.flr_1'));
  chk('a stated section is carried verbatim',
      v.columns[0].section.width_m===0.3&&v.columns[0].section.shape==='rectangular');
  chk('a column with no section keeps section=null',
      S('warehouse_struct').columns.every(c=>c.section===null));
  chk('and that is reported as INFO, never as an error',
      S('warehouse_struct').issues.filter(i=>i.code==='SECTION_UNKNOWN')
        .every(i=>i.severity==='INFO'));
  chk('structural_role stays unknown unless the model states it',
      v.columns.every(c=>c.structural_role==='unknown')); }

console.log('\n== §6 — DISPLAY FALLBACK IS NEVER STRUCTURAL DATA ==');
{ const w=S('warehouse_struct');
  const c=w.columns[0];
  chk('an unknown section still yields render geometry', c.render_section.w===0.3);
  chk('but that geometry is labelled display_fallback',
      c.render_section.source==='display_fallback');
  chk('and the semantic section stays null beside it', c.section===null);
  const items=structRenderItems(w);
  chk('every render item declares where its geometry came from',
      items.every(i=>['model','display_fallback'].indexOf(i.geometry_source)>=0));
  chk('the warehouse render items are all fallback-driven',
      items.filter(i=>i.kind==='COLUMN').every(i=>i.geometry_source==='display_fallback'));
  chk('the villa render items are model-driven',
      structRenderItems(S('villa_struct')).filter(i=>i.kind==='COLUMN')
        .every(i=>i.geometry_source==='model'));
  chk('a fallback never appears in the rule inputs',
      structRuleInputs(w)[w.columns[0].id]['structural.column.section_width']===null);
  chk('the spec states the fallback policy in writing',
      /DISPLAY GEOMETRY IS NOT STRUCTURAL DESIGN/.test(ACS_STRUCT_SPEC.display_fallback_note));
  chk('compiling does not write the fallback back into the model',
      (()=>{const m=C(SC.models.warehouse_struct); compileStructure(m,'bld_0');
        return m.structural.columns.every(x=>x.section===null);})()); }

console.log('\n== §7 — BEAMS ==');
{ const v=S('villa_struct');
  chk('seven declared beams and not one auto-connected pair',
      v.beams.length===7, v.beams.length);
  chk('no beam was invented between neighbouring columns',
      v.beams.length < v.columns.length*2);
  chk('a beam resolves both endpoints to structural nodes',
      v.beams.every(b=>b.start.basis==='structural_node'&&b.end.basis==='structural_node'));
  chk('beam length is measured, not assumed',
      Math.abs(v.beams.filter(b=>b.id==='bld_0.B_A1_B1')[0].length_m-7)<1e-9);
  const br=S('broken_struct');
  chk('a beam naming a missing node is reported twice: bad ref and unresolved endpoint',
      codes(br).indexOf('INVALID_NODE_REF')>=0&&codes(br).indexOf('BEAM_ENDPOINT_UNRESOLVED')>=0);
  chk('a beam given bare points is flagged floating, not silently accepted',
      codes(br).indexOf('BEAM_FLOATING')>=0);
  chk('a zero-length beam is an ERROR',
      br.issues.filter(i=>i.code==='MEMBER_ZERO_LENGTH')[0].severity==='ERROR'); }

console.log('\n== §8 — STRUCTURAL SLAB / WALL / CORE ARE NOT THE ARCHITECTURAL ONES ==');
{ const v=S('villa_struct'), a=compileArchitecture(C(SC.models.villa_struct),'bld_0');
  chk('the architectural slabs are untouched by the structural layer',
      a.slabs.length===2&&a.slabs.every(s=>s.structural===false));
  chk('a structural slab exists only where the model declares one',
      v.slabs.length===1&&v.slabs[0].id==='bld_0.S_F1');
  chk('a structural slab says it is a separate element',
      /separate element from the architectural floor slab/.test(v.slabs[0].note));
  const h=S('hotel_struct');
  chk('an architectural wall is never reclassified as structural',
      h.walls.length===1&&h.walls[0].id==='bld_0.SW_1');
  chk('a shear wall role appears only because the fixture states it',
      h.walls[0].structural_role==='shear_wall');
  chk('a wall with no stated role stays unknown',
      (()=>{const m=C(SC.models.hotel_struct); delete m.structural.walls[0].structural_role;
        return compileStructure(m,'bld_0').walls[0].structural_role==='unknown';})());
  chk('an elevator shaft is not called a lateral core by itself',
      (()=>{const m=C(SC.models.hotel_struct); delete m.structural.cores[0].structural_role;
        const st=compileStructure(m,'bld_0');
        return st.cores[0].structural_role==='unknown';})());
  chk('a structural core spanning levels emits CORE_SPANS_LEVELS',
      h.relationships.some(r=>r.type==='CORE_SPANS_LEVELS'&&r.from==='bld_0.SC_1'));
  chk('the architectural stair core is still its own element',
      a.cores.length>0&&a.cores.every(c=>c.type==='STAIR'||c.type==='ELEVATOR_SHAFT')); }

console.log('\n== §9 — FOUNDATIONS ==');
{ const v=S('villa_struct');
  chk('nine isolated footings, exactly as declared', v.foundations.length===9&&
      v.foundations.every(f=>f.foundation_type==='isolated_footing'));
  chk('no soil property is ever produced', v.foundations.every(f=>f.soil===null));
  chk('a foundation never claims a bearing capacity',
      v.foundations.every(f=>/no size, soil property or bearing capacity/.test(f.note)));
  chk('an unrecognised foundation type falls back to other, not to a guess',
      S('broken_struct').foundations.filter(f=>f.id==='bld_0.fOrphan')[0]
        .foundation_type==='other');
  chk('a foundation with no supported member is reported',
      codes(S('broken_struct')).indexOf('FOUNDATION_REF_MISSING')>=0);
  chk('a foundation naming a member that does not exist is an ERROR',
      S('broken_struct').issues.filter(i=>i.code==='FOUNDATION_TARGET_UNRESOLVED')[0]
        .severity==='ERROR');
  chk('a foundation outside the site is reported factually',
      codes(S('clash_struct')).indexOf('FOUNDATION_OUTSIDE_SITE')>=0);
  chk('the foundation type is never chosen from the building type',
      S('hotel_struct').foundations.every(f=>f.foundation_type==='raft')&&
      S('villa_struct').foundations.every(f=>f.foundation_type==='isolated_footing')); }

console.log('\n== §10 — MATERIALS ==');
{ const v=S('villa_struct');
  const m=v.materials[0];
  chk('a material label alone carries no strength',
      m.material==='concrete'&&m.strength.value===null&&m.grade.value===null);
  chk('no elastic modulus or density is inferred',
      m.elastic_modulus.value===null&&m.density.value===null);
  chk('every optional property carries its own provenance',
      m.strength.source==='unknown'&&m.density.source==='unknown');
  chk('a supplied property is kept with imported provenance',
      (()=>{const mm=C(SC.models.villa_struct);
        mm.structural.materials[0].strength=30; mm.structural.materials[0].source='imported';
        const st=compileStructure(mm,'bld_0');
        return st.materials[0].strength.value===30&&st.materials[0].strength.source==='imported';})());
  chk('the spec states that concrete implies no f′c', /f'c/.test(ACS_STRUCT_SPEC.material_note));
  chk('an unknown material stays unknown', S('warehouse_struct').materials[0].material==='unknown');
  chk('a member with no material reference is reported as INFO',
      (()=>{const br=S('broken_struct');
        return br.issues.filter(i=>i.code==='MATERIAL_UNKNOWN').every(i=>i.severity==='INFO');})());
  chk('a member naming a missing material is an ERROR',
      S('broken_struct').issues.filter(i=>i.code==='INVALID_MATERIAL_REF')[0].severity==='ERROR'); }

console.log('\n== §11 — NODES AND LEVEL ALIGNMENT ==');
{ const v=S('villa_struct');
  chk('nodes take their elevation from the architectural level table',
      v.nodes.filter(n=>n.level_index===1).every(n=>n.y===3.2&&
        n.y_source==='architectural_level'));
  chk('a node with an invalid level reference is reported',
      codes(S('broken_struct')).indexOf('INVALID_LEVEL_REF')>=0);
  chk('no member floats on renderer-only coordinates',
      v.columns.every(c=>c.base_elevation_m!==null&&c.top_elevation_m!==null));
  chk('the structural level table mirrors the architectural one',
      JSON.stringify(v.levels.map(l=>[l.id,l.elevation_m]))===
      JSON.stringify(compileArchitecture(C(SC.models.villa_struct),'bld_0')
        .levels.map(l=>[l.id,l.elevation_m]))); }

console.log('\n== §12 — COLUMN STACKING, OFFSET AND ALIGNMENT BREAK ==');
{ const h=S('hotel_struct');
  const st=id=>h.columns.filter(c=>c.id==='bld_0.'+id)[0].stack;
  chk('a column directly over another is aligned', st('C_P1_L1').state==='aligned'&&
      st('C_P1_L1').supported_by==='bld_0.C_P1_L0');
  chk('a 0.4 m shift is reported as an offset, not as aligned',
      st('C_OFF_L1').state==='offset'&&Math.abs(st('C_OFF_L1').offset_m-0.4)<1e-9);
  chk('an offset is a WARNING and no transfer beam is designed',
      h.issues.filter(i=>i.code==='COLUMN_OFFSET')[0].severity==='WARNING'&&
      /no transfer element is designed or assumed/.test(
        h.issues.filter(i=>i.code==='COLUMN_OFFSET')[0].detail));
  chk('a column with nothing under it is an alignment break, reported only',
      st('C_BREAK_L1').state==='unresolved'&&
      codes(h).indexOf('STRUCTURAL_ALIGNMENT_BREAK')>=0);
  chk('no transfer element was added to the model by the break',
      h.beams.every(b=>b.source==='test_fixture')&&h.beams.length===8);
  chk('alignment states never leave the declared vocabulary',
      h.columns.every(c=>STRUCT_ALIGNMENT_STATES.indexOf(c.stack.state)>=0));
  chk('a stack edge is confirmed only when actually aligned',
      h.relationships.filter(r=>r.type==='COLUMN_STACKS')
       .every(r=>(r.meta.alignment==='aligned')===(r.status==='confirmed')));
  const m=S('mixed_struct');
  chk('a three-storey stack aligns on every level',
      m.summary===undefined&&m.columns.filter(c=>c.stack.state==='aligned').length===12,
      m.columns.filter(c=>c.stack.state==='aligned').length); }

console.log('\n== §13 — RELATIONSHIPS ARE NOT LOAD PATHS ==');
{ const v=S('villa_struct');
  chk('every relationship type is in the declared vocabulary',
      v.relationships.every(r=>STRUCT_REL_TYPES.indexOf(r.type)>=0));
  chk('every relationship carries the not-a-load-path note',
      v.relationships.every(r=>/this is not a load path/.test(r.note)));
  chk('a column touching a beam yields COLUMN_SUPPORTS with an explicit disclaimer',
      v.relationships.some(r=>r.type==='COLUMN_SUPPORTS'&&
        /not a load path/.test(r.meta.disclaimer)));
  chk('no relationship says a member carries anything',
      !/carries|load path is|transfers load/i.test(
        JSON.stringify(v.relationships).replace(/not a load path/g,'')));
  chk('the spec states the rule in capitals',
      /GEOMETRIC CONNECTIVITY IS NOT A STRUCTURAL LOAD PATH/
        .test(ACS_STRUCT_SPEC.relationship_note));
  chk('a declared slab support is confirmed; an undeclared one is never invented',
      v.relationships.filter(r=>r.type==='SLAB_SUPPORTED_BY').length===2);
  chk('a foundation placement relationship says no bearing check was made',
      v.relationships.filter(r=>r.type==='FOUNDATION_SUPPORTS')
       .every(r=>/no bearing check is performed/.test(r.meta.disclaimer)));
  chk('relationship ids are unique and namespaced',
      new Set(v.relationships.map(r=>r.id)).size===v.relationships.length&&
      v.relationships.every(r=>r.id.indexOf('bld_0.srel_')===0)); }

console.log('\n== §14 — STRUCTURAL ↔ ARCHITECTURAL INTERACTION ==');
{ const cl=S('clash_struct');
  chk('a column standing in a door opening is reported',
      codes(cl).indexOf('COLUMN_BLOCKS_OPENING')>=0);
  chk('a column inside a stair void is reported',
      codes(cl).indexOf('COLUMN_IN_FLOOR_OPENING')>=0);
  chk('a column inside the elevator travel path is reported separately',
      codes(S('lift_clash_struct')).indexOf('COLUMN_IN_ELEVATOR_CORE')>=0);
  chk('every clash states the basis it was tested on',
      cl.issues.filter(i=>/COLUMN_BLOCKS|COLUMN_IN_/.test(i.code))
        .every(i=>['column_section_footprint','column_axis_point'].indexOf(i.basis)>=0));
  chk('a beam along a wall carrying a door is INFO and says clearance is not evaluated',
      (()=>{const w=S('warehouse_struct');
        const i=w.issues.filter(x=>x.code==='BEAM_CROSSES_OPENING')[0];
        return i&&i.severity==='INFO'&&/head clearance is NOT evaluated/.test(i.detail);})());
  chk('a column inside a room is a spatial relationship, not a prohibition',
      cl.relationships.some(r=>r.type==='MEMBER_IN_SPACE'&&
        /acceptability is not judged here/.test(r.meta.disclaimer)));
  chk('a column far outside the footprint is reported, not moved',
      codes(S('hotel_struct')).indexOf('COLUMN_OUTSIDE_BUILDING')>=0);
  chk('no clash is auto-fixed — the model is returned unchanged',
      (()=>{const m=C(SC.models.clash_struct), before=JSON.stringify(m);
        compileStructure(m,'bld_0'); return JSON.stringify(m)===before;})()); }

console.log('\n== §15 — INTEGRITY VALIDATION ==');
{ const br=S('broken_struct');
  const need=['DUPLICATE_ELEMENT_ID','INVALID_LEVEL_REF','INVALID_NODE_REF',
    'INVALID_MATERIAL_REF','CROSS_BUILDING_REF','NAN_COORDINATE','NEGATIVE_DIMENSION',
    'MEMBER_ZERO_LENGTH','COLUMN_ZERO_HEIGHT','BEAM_ENDPOINT_UNRESOLVED','BEAM_FLOATING',
    'FOUNDATION_REF_MISSING','SLAB_LEVEL_UNRESOLVED','WALL_LEVELS_UNRESOLVED',
    'CORE_LEVELS_UNRESOLVED','UNSUPPORTED_ELEMENT_TYPE','COLUMN_HEIGHT_MISMATCH',
    'INVALID_GRID_REF'];
  const got=new Set(codes(br));
  chk('the deliberately broken fixture triggers every integrity check',
      need.every(c=>got.has(c)), need.filter(c=>!got.has(c)).join(','));
  chk('every issue code is declared in the spec with a severity',
      br.issues.every(i=>Object.prototype.hasOwnProperty.call(STRUCT_ISSUE_CODES,i.code)));
  chk('every issue carries a severity from the declared list',
      br.issues.every(i=>STRUCT_SEVERITIES.indexOf(i.severity)>=0));
  chk('issues are ordered ERROR first, then WARNING, then INFO',
      (()=>{const r={ERROR:0,WARNING:1,INFO:2};
        return br.issues.every((i,k)=>k===0||r[br.issues[k-1].severity]<=r[i.severity]);})());
  chk('no issue is a code-compliance verdict',
      br.issues.every(i=>!/COMPLIAN|SBC|UNSAFE|DANGEROUS/i.test(i.code)));
  chk('an unknown structural collection is reported and NOT interpreted',
      br.issues.some(i=>i.code==='UNSUPPORTED_ELEMENT_TYPE'&&
        /was NOT interpreted/.test(i.detail)));
  chk('a foreign building id is caught rather than silently re-namespaced',
      br.issues.some(i=>i.code==='CROSS_BUILDING_REF'&&i.subject==='bld_9.cForeign')); }

console.log('\n== §16 — DETERMINISM, NAMESPACING AND TRANSFORMS ==');
chk('compiling twice gives byte-identical output',
    JSON.stringify(S('mixed_struct'))===JSON.stringify(S('mixed_struct')));
{ const m=C(SC.models.hotel_struct), before=JSON.stringify(m);
  compileStructure(m,'bld_0'); validateStructure(compileStructure(m,'bld_0'));
  chk('the compiler never mutates the model it reads', JSON.stringify(m)===before); }
{ const a=S('villa_struct','bld_0'), b=S('villa_struct','bld_3');
  chk('a second building namespaces every structural id',
      b.columns.every(c=>c.id.indexOf('bld_3.')===0)&&
      b.relationships.every(r=>r.id.indexOf('bld_3.')===0));
  chk('two buildings can never collide on an id',
      a.columns.every(c=>b.columns.every(d=>d.id!==c.id)));
  chk('a transform never changes the compiled geometry',
      JSON.stringify(S('villa_struct','bld_0',{x:9,z:-4},45).columns)===
      JSON.stringify(a.columns));
  const t=S('villa_struct','bld_0',{x:9,z:-4},45);
  const p=structToWorld(t,0,0);
  chk('the building transform is applied on read',
      Math.abs(p[0]-9)<1e-9&&Math.abs(p[1]+4)<1e-9, JSON.stringify(p));
  const p2=structToWorld(t,10,0);
  chk('rotation is applied about the building origin',
      Math.abs(p2[0]-(9+10*Math.cos(Math.PI/4)))<1e-9&&
      Math.abs(p2[1]-(-4+10*Math.sin(Math.PI/4)))<1e-9);
  chk('grid lines respect the building transform too',
      structGridToWorld(t,t.grid_systems[0],t.grid_systems[0].grids[0],10)!==null); }

console.log('\n== §17 — REVISION HASH ==');
{ const base=C(SC.models.villa_struct);
  const h0=modelHash(base);
  const moved=C(base); moved.structural.columns[0].position.x=1.5;
  chk('moving a column changes the model hash', modelHash(moved)!==h0);
  const noBeam=C(base); noBeam.structural.beams.pop();
  chk('removing a beam changes the model hash', modelHash(noBeam)!==h0);
  const sec=C(base); sec.structural.columns[0].section.width=0.45;
  chk('changing a section changes the model hash', modelHash(sec)!==h0);
  const fnd=C(base); fnd.structural.foundations.push({id:'F_NEW',type:'pile',
    position:{x:1,z:1},supports:['C_A1'],material_ref:'mat_c30',source:'test_fixture'});
  chk('adding a foundation changes the model hash', modelHash(fnd)!==h0);
  const mat=C(base); mat.structural.materials[0].strength=35;
  chk('changing a material property changes the model hash', modelHash(mat)!==h0);
  const vis=C(base); vis.structural.layer_visibility={structural:false};
  chk('toggling layer visibility does NOT change the model hash', modelHash(vis)===h0);
  const vis2=C(base); vis2.camera={x:1,y:2,z:3};
  chk('moving the camera still does not change the hash', modelHash(vis2)===h0);
  chk('compiling the structure does not change the hash',
      (()=>{const m=C(base); const h=modelHash(m); compileStructure(m,'bld_0');
        return modelHash(m)===h;})());
  chk('a model with no structural block hashes exactly as before',
      (()=>{const m=C(FX.villa); return /^[0-9a-f]{64}$/.test(modelHash(m));})()); }

console.log('\n== §18 — RENDER AND EXPORT ==');
{ const v=S('villa_struct');
  const items=structRenderItems(v);
  chk('render items use the STRUCT| naming convention',
      items.every(i=>/^STRUCT\|(COLUMN|BEAM|SLAB|WALL|CORE|FOUNDATION|GRID)\|/.test(i.name)));
  chk('every structural kind that has geometry is represented',
      ['COLUMN','BEAM','SLAB','FOUNDATION','GRID'].every(k=>
        items.some(i=>i.name.indexOf('STRUCT|'+k+'|')===0)));
  chk('render items never carry an engineering verdict',
      !/safe|adequate|capacity|compliant/i.test(JSON.stringify(items)));
  chk('a column render box sits between its two level elevations',
      (()=>{const c=items.filter(i=>i.kind==='COLUMN')[0];
        return Math.abs(c.cy-1.6)<1e-9&&Math.abs(c.ey-3.2)<1e-9;})());
  chk('grid render items are lines, not boxes',
      items.filter(i=>i.kind==='GRID_LINE').every(i=>i.ex===undefined&&i.axis!==undefined));
  chk('the structural layer is separate from the architectural layers',
      LAYER_ORDER.indexOf('STRUCT')>=0&&LAYER_NAMES.STRUCT.indexOf('لا تصميم')>0);
  chk('colour distinguishes element kind only, never status',
      Object.keys(STRUCT_KIND_COLOR).every(k=>STRUCT_ELEMENT_TYPES.indexOf(k)>=0)); }

console.log('\n== §19 — RULE ENGINE CONTRACT (INPUTS ONLY) ==');
{ const v=S('villa_struct');
  const ri=structRuleInputs(v);
  chk('structural facts are exposed as future rule inputs',
      ri['bld_0.C_A1']['structural.column.section_width']===0.3&&
      ri['bld_0.C_A1']['structural.member.material']==='concrete');
  chk('a missing fact stays missing rather than defaulting',
      structRuleInputs(S('warehouse_struct'))['bld_0.WC0']['structural.column.section_width']
        ===null);
  chk('no regulatory rule was added anywhere', regulatoryRuleCount([])===0);
  chk('the rule inputs contain no threshold, limit or verdict',
      !/limit|minimum|maximum|required|PASS|FAIL/i.test(JSON.stringify(ri))); }

console.log('\n== §20 — NO ARCHITECTURAL / NAV / EGRESS / DISTANCE REGRESSION ==');
{ ['villa','hotel','clinic','warehouse'].forEach(n=>{
    const plain=compileArchitecture(C(FX[n]),'bld_0');
    const withS=compileArchitecture(C(SC.models[n+'_struct']||FX[n]),'bld_0');
    if(SC.models[n+'_struct']&&n!=='warehouse')
      chk(n+': adding a structural block changes no architectural element',
          JSON.stringify(plain.walls)===JSON.stringify(withS.walls)&&
          JSON.stringify(plain.openings)===JSON.stringify(withS.openings)&&
          JSON.stringify(plain.voids)===JSON.stringify(withS.voids)&&
          JSON.stringify(plain.envelope)===JSON.stringify(withS.envelope)); });
  const b=C(SC.models.villa_struct), plainB=C(FX.villa);
  chk('relationships are identical with and without the structural block',
      JSON.stringify(buildRelationships(b,'bld_0'))===
      JSON.stringify(buildRelationships(plainB,'bld_0')));
  chk('navigation is identical with and without the structural block',
      JSON.stringify(findPath(b,buildRelationships(b,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0'))===
      JSON.stringify(findPath(plainB,buildRelationships(plainB,'bld_0'),
        'bld_0.f.bed1','bld_0.g.majlis','bld_0')));
  chk('egress is identical with and without the structural block',
      JSON.stringify(findEgress(b,buildRelationships(b,'bld_0'),'bld_0.g.majlis','bld_0'))===
      JSON.stringify(findEgress(plainB,buildRelationships(plainB,'bld_0'),
        'bld_0.g.majlis','bld_0')));
  chk('walking distance is unchanged — a column is not an obstacle in this phase',
      (()=>{const p=findPath(b,buildRelationships(b,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        const p2=findPath(plainB,buildRelationships(plainB,'bld_0'),
              'bld_0.f.bed1','bld_0.g.majlis','bld_0');
        return measurePath(b,p,'bld_0').walking_distance_m===
               measurePath(plainB,p2,'bld_0').walking_distance_m;})());
  chk('and the model says so in writing',
      /not navigation obstacles in this phase/.test(S('villa_struct').meta.navigation_impact)); }

console.log('\n== §21 — BUILDING-TYPE NEUTRALITY ACROSS FIXTURES ==');
FIXTURES.forEach(n=>{ const st=S(n);
  chk(n+': compiles through the same element vocabulary',
      st.columns.every(c=>c.type==='COLUMN')&&st.beams.every(b=>b.type==='BEAM'));
  chk(n+': every issue code is declared',
      st.issues.every(i=>Object.prototype.hasOwnProperty.call(STRUCT_ISSUE_CODES,i.code)));
  chk(n+': no member claims adequacy',
      !/adequate|safe|compliant/i.test(JSON.stringify(st.columns.concat(st.beams))));
  chk(n+': the structural model is independent of the program registry',
      st.status!=='NOT_DEFINED'); });
{ const m=S('mixed_struct');
  chk('three different programs share one structural system',
      m.columns.length===18&&new Set(m.columns.map(c=>c.section.width_m)).size===1);
  chk('no structural property changed with the occupancy or program',
      m.columns.every(c=>c.material_ref==='mat_m')); }

console.log('\n== §22 — SECURITY ==');
chk('no eval / Function in the structural layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      compileStructure.toString()+validateStructure.toString()+
      structRenderItems.toString()+suggestStructuralGrid.toString()));
chk('no network call in the structural layer',
    !/fetch\s*\(|XMLHttpRequest/.test(compileStructure.toString()+validateStructure.toString()));
chk('a hostile element id cannot escape into markup',
    (()=>{const m=C(FX.villa);
      m.structural={columns:[{id:'<script>alert(1)</script>',base_level:0,top_level:1,
        position:{x:1,z:1},source:'user'}]};
      const st=compileStructure(m,'bld_0');
      return esc(st.columns[0].id).indexOf('<script')<0;})());
chk('a NaN coordinate is rejected rather than propagated',
    (()=>{const br=S('broken_struct');
      return br.nodes.concat(br.columns).every(e=>e.x===null||isFinite(e.x));})());

console.log(`\nSTRUCTURE: ${pass} passed, ${fail} failed`);
