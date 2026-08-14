/* ============================================================
   public/app/core/disciplines.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { ARCH_COMPILER_VERSION, ARCH_DEFAULTS, ARCH_SCHEMA, _A_EPS, _aBbox, _aClassifyExposure, _aCores, _aHost, _aLevels, _aOpeningsOf, _aRect, _aRoomsOf, _aShapeSupported, _aVal, _aWallSegments, _aq, _pyT, _scmp } from './standards.js';
import { _pyRound, buildRelationships, extractExits, findEgress } from './viewer.js';

function compileArchitecture(building,buildingId,position,rotationDeg){
  const bid=buildingId||'bld_0';
  const levels=_aLevels(building,bid);
  const wallT=(building.wall_t===undefined)?null:building.wall_t;
  const wallTSrc=_pyT(building.wall_t_source)?building.wall_t_source
    :((wallT!==null&&wallT!==undefined)?'system_default':'unknown');
  const thickness=_aVal(wallT,ARCH_DEFAULTS.wall_thickness_m,wallTSrc);
  const wallHDefault=(building.wall_h===undefined)?null:building.wall_h;
  const out={schema:ARCH_SCHEMA, compiler_version:ARCH_COMPILER_VERSION, building_id:bid,
    transform:{position:position||{x:0.0,z:0.0}, rotation_deg:Number(rotationDeg||0.0),
      applied:'local coordinates; world transform is applied on read'},
    levels:levels, walls:[], openings:[], slabs:[], voids:[],
    ceilings:[], roofs:[], cores:[], spaces:[], envelope:null,
    approximations:[], issues:[]};
  levels.forEach(lvl=>{
    const rooms=_aRoomsOf(building,lvl.template,bid);
    const rects=[], unsupported=[], allRects=[];
    rooms.forEach(tr=>{ const sid=tr[0], room=tr[1];
      const rc=_aRect(room);
      const supported=(rc!==null)&&_aShapeSupported(room);
      const statedH=(room.wall_h===null||room.wall_h===undefined)?null:room.wall_h;
      /* هوية النسخة الفيزيائية = هوية عقدة الملاحة نفسها (space@level):
         قالب دور واحد على مستويين هو غرفتان حقيقيتان لا غرفة واحدة. */
      out.spaces.push({id:sid+'@'+lvl.index, space_id:sid,
        level_id:lvl.id, level_index:lvl.index,
        name:(room.id===undefined)?null:room.id, rect:rc,
        boundary_basis:supported?'rectangle_edges':'unsupported_shape',
        area_m2:rc?(rc[2]*rc[3]):null,
        wall_height_m:_aVal(statedH!==null?statedH:wallHDefault,ARCH_DEFAULTS.wall_height_m,
          statedH!==null?'imported'
          :((wallHDefault!==null&&wallHDefault!==undefined)?'imported':'unknown'))});
      if(rc!==null){ allRects.push(rc); if(supported) rects.push(rc); else unsupported.push(rc); }
      if(!supported&&rc!==null){
        out.approximations.push({space_id:sid, reason:'SPACE_SHAPE_UNSUPPORTED',
          detail:'a non-rectangular outline is present; it was NOT approximated as a rectangle'});
        out.issues.push({code:'SPACE_SHAPE_UNSUPPORTED', subject:sid}); } });
    const bbox=_aBbox(allRects);
    const segs=_aWallSegments(rooms);
    const lvlWalls=[];
    segs.forEach((s,n)=>{
      let cls=_aClassifyExposure(s,rects,unsupported,bbox);
      let exposure=cls[0], status=cls[1], basis=cls[2];
      /* إعلان الفراغ الخارجي لا يُبطل جداراً يفصل فراغين — الحقيقة الهندسية أقوى */
      if(s.spaces.length===1){
        let room=null;
        for(const tr of rooms){ if(tr[0]===s.spaces[0]){ room=tr[1]; break; } }
        if(room!==null&&room.exterior===true){
          exposure='exterior'; status='confirmed'; basis='declared_by_model'; } }
      const h=(s.height_stated!==null&&s.height_stated!==undefined)?s.height_stated:wallHDefault;
      const w={id:lvl.id+'.wall_'+n, type:'WALL', building_id:bid,
        level_id:lvl.id, level_index:lvl.index,
        axis:s.axis, fixed:s.fixed, u0:s.u0, u1:s.u1, length_m:s.u1-s.u0,
        start:(s.axis==='x')?{x:s.u0,z:s.fixed}:{x:s.fixed,z:s.u0},
        end:(s.axis==='x')?{x:s.u1,z:s.fixed}:{x:s.fixed,z:s.u1},
        height_m:_aVal(h,ARCH_DEFAULTS.wall_height_m,
          (h!==null&&h!==undefined)?'imported':'unknown'),
        thickness_m:{value:thickness.value,render_fallback:thickness.render_fallback,
          source:thickness.source},
        spaces:s.spaces, shared:s.spaces.length>1,
        exposure:exposure, exposure_status:status, exposure_basis:basis,
        openings:[]};
      lvlWalls.push(w); out.walls.push(w); });
    rooms.forEach(tr=>{ const sid=tr[0], room=tr[1];
      ['door','window'].forEach(kind=>{
        _aOpeningsOf(room,sid,kind).forEach(op=>{
          op.building_id=bid; op.level_id=lvl.id; op.level_index=lvl.index;
          /* opening_ref هو المرجع الدلالي الذي تستعمله العلاقات (via) */
          op.opening_ref=op.id; op.id=op.id+'@'+lvl.index;
          const r=_aHost(op,lvlWalls);
          op.host_wall_id=r[0]?r[0].id:null;
          op.host_status=r[1]; op.host_note=r[2];
          if(r[0]) r[0].openings.push(op.id);
          out.openings.push(op); }); }); });
    if(bbox){
      const slabT=(building.slab_t===undefined)?null:building.slab_t;
      out.slabs.push({id:lvl.id+'.slab', type:'FLOOR_SLAB', building_id:bid,
        level_id:lvl.id, level_index:lvl.index,
        outline:[bbox[0],bbox[1],bbox[2]-bbox[0],bbox[3]-bbox[1]],
        outline_basis:'bounding_box_of_spaces',
        elevation_m:lvl.elevation_m, elevation_source:lvl.elevation_source,
        thickness_m:_aVal(slabT,ARCH_DEFAULTS.slab_thickness_m,
          (slabT!==null&&slabT!==undefined)?'imported':'system_default'),
        structural:false, note:'architectural slab only — not a structural design'});
      const covered=rects.reduce((s,r)=>s+r[2]*r[3],0);
      if(covered<(bbox[2]-bbox[0])*(bbox[3]-bbox[1])-1e-6)
        out.approximations.push({level_id:lvl.id, reason:'SLAB_OUTLINE_IS_BOUNDING_BOX',
          detail:'spaces do not tile the level footprint; the slab outline is their '
                +'bounding box and is reported as an approximation'}); }
    if(lvl.kind==='roof'){
      out.roofs.push({id:lvl.id+'.roof', type:'ROOF', building_id:bid,
        level_id:lvl.id, level_index:lvl.index, form:'flat',
        outline:out.slabs.length?out.slabs[out.slabs.length-1].outline:null,
        elevation_m:lvl.elevation_m,
        source:lvl.auto_added?'system_default':'imported',
        occupied_floor:false, note:'a roof level is never an occupied floor'}); }
    else {
      rooms.forEach(tr=>{ const sid=tr[0], room=tr[1];
        const rc=_aRect(room);
        if(rc===null) return;
        const statedH=(room.wall_h===null||room.wall_h===undefined)?null:room.wall_h;
        const h=statedH!==null?statedH:wallHDefault;
        out.ceilings.push({id:lvl.id+'.ceiling_'+(_pyT(room.id)?room.id:sid.split('.').slice(-1)[0]),
          type:'CEILING', building_id:bid, level_id:lvl.id, space_id:sid, outline:rc,
          elevation_m:(lvl.elevation_m!==null&&h!==null&&h!==undefined)
            ?(lvl.elevation_m+Number(h)):null,
          thickness_m:{value:null,render_fallback:0.05,source:'unknown'}}); }); } });
  out.cores=_aCores(building,bid,levels);
  /* فراغ في البلاطة عند كل مستوى تخترقه نواة — الدرج لا يمرّ عبر بلاطة صمّاء */
  let vn=0;
  out.cores.forEach(core=>{
    const served=core.served_levels;
    if(!served.length){
      out.issues.push({code:'CORE_WITHOUT_SERVED_LEVELS', subject:core.id});
      return; }
    const fw=core.footprint_w_m.value||core.footprint_w_m.render_fallback;
    const fd=core.footprint_d_m.value||core.footprint_d_m.render_fallback;
    const lo=Math.min.apply(null,served), hi=Math.max.apply(null,served);
    levels.forEach(lvl=>{
      if(lvl.index<=lo||lvl.index>hi) return;
      out.voids.push({id:lvl.id+'.void_'+vn, type:'FLOOR_OPENING', building_id:bid,
        level_id:lvl.id, level_index:lvl.index, core_id:core.id, core_type:core.type,
        rect:[core.x-fw/2.0, core.z-fd/2.0, fw, fd],
        footprint_source:core.position_source,
        note:'architectural void only — no structural framing implied'});
      vn+=1; });
    if(core.position_source!=='imported')
      out.issues.push({code:'CORE_POSITION_NOT_STATED', subject:core.id}); });
  const ext=out.walls.filter(w=>w.exposure==='exterior');
  const extOpen=out.openings.filter(o=>ext.some(w=>w.openings.indexOf(o.id)>=0));
  out.envelope={id:bid+'.envelope', type:'ENVELOPE', building_id:bid,
    exterior_walls:ext.map(w=>w.id),
    unresolved_walls:out.walls.filter(w=>w.exposure==='unresolved').map(w=>w.id),
    external_openings:extOpen.map(o=>o.id),
    roof_boundary:out.roofs.length?out.roofs[out.roofs.length-1].outline
      :(out.slabs.length?out.slabs[out.slabs.length-1].outline:null),
    ground_interface:out.slabs.length?out.slabs[0].outline:null,
    note:'derived envelope for later facade/exposure work — no analysis is performed here'};
  validateArchitecture(out).forEach(i=>out.issues.push(i));
  return out; }
/* ------------------------------------------------------------ التحقّق --- */
/* فحوص سلامة نموذج معماري — ليست فحوص كود بناء إطلاقاً */
function validateArchitecture(arch){
  const issues=[];
  (arch.walls||[]).forEach(w=>{
    if(w.length_m<=_A_EPS) issues.push({code:'WALL_ZERO_LENGTH', subject:w.id});
    const t=w.thickness_m.value;
    if(t!==null&&t!==undefined&&t<=0)
      issues.push({code:'WALL_NEGATIVE_THICKNESS', subject:w.id}); });
  const seen=new Map();
  (arch.walls||[]).forEach(w=>{
    const k=[w.level_id,w.axis,_aq(w.fixed),_aq(w.u0),_aq(w.u1)].join('|');
    if(seen.has(k)) issues.push({code:'WALL_DUPLICATE_OVERLAP', subject:w.id, other:seen.get(k)});
    seen.set(k,w.id); });
  const walls={}; (arch.walls||[]).forEach(w=>{walls[w.id]=w;});
  (arch.openings||[]).forEach(o=>{
    if(o.host_status==='unresolved'){
      issues.push({code:'OPENING_HOST_UNRESOLVED', subject:o.id}); return; }
    const host=walls[o.host_wall_id];
    if(host===undefined){
      issues.push({code:'OPENING_HOST_UNRESOLVED', subject:o.id}); return; }
    const w=o.width_m.value||o.width_m.render_fallback;
    const a=o.u_center-w/2.0, b=o.u_center+w/2.0;
    if(a<host.u0-_A_EPS||b>host.u1+_A_EPS){
      /* أعرض من مضيفه شيء، ومنزاح عن طرفه شيء آخر — لا نخلط بينهما */
      const wider=w>(host.u1-host.u0)+_A_EPS;
      issues.push({code:wider?'OPENING_WIDER_THAN_HOST':'OPENING_OUTSIDE_HOST',
        subject:o.id, host:host.id}); }
    const wh=host.height_m.value||host.height_m.render_fallback;
    const oh=o.height_m.value||o.height_m.render_fallback;
    if(o.type==='WINDOW'){
      const sill=(o.sill_m.value!==null&&o.sill_m.value!==undefined)
        ?o.sill_m.value:o.sill_m.render_fallback;
      if(sill<-_A_EPS) issues.push({code:'WINDOW_BELOW_FLOOR', subject:o.id});
      if(sill+oh>wh+_A_EPS) issues.push({code:'WINDOW_ABOVE_WALL_HEIGHT', subject:o.id}); }
    else if(oh>wh+_A_EPS) issues.push({code:'DOOR_TALLER_THAN_WALL', subject:o.id}); });
  const byLevel=new Map();
  (arch.spaces||[]).forEach(s=>{
    if(!byLevel.has(s.level_id)) byLevel.set(s.level_id,[]);
    byLevel.get(s.level_id).push(s); });
  byLevel.forEach(spaces=>{
    for(let i=0;i<spaces.length;i++){
      for(let j=i+1;j<spaces.length;j++){
        const a=spaces[i].rect, b=spaces[j].rect;
        if(!a||!b) continue;
        const ox=Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0]);
        const oz=Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1]);
        if(ox>1e-3&&oz>1e-3){
          const inside=((a[0]>=b[0]-_A_EPS&&a[1]>=b[1]-_A_EPS
                         &&a[0]+a[2]<=b[0]+b[2]+_A_EPS&&a[1]+a[3]<=b[1]+b[3]+_A_EPS)
                      ||(b[0]>=a[0]-_A_EPS&&b[1]>=a[1]-_A_EPS
                         &&b[0]+b[2]<=a[0]+a[2]+_A_EPS&&b[1]+b[3]<=a[1]+a[3]+_A_EPS));
          /* احتواء كامل نمط تخطيط مشروع (منطقة داخل غلاف)، لا تداخل خاطئ */
          issues.push({code:inside?'SPACE_CONTAINED':'SPACE_OVERLAP',
            subject:spaces[i].id, other:spaces[j].id, overlap_m2:_pyRound(ox*oz,6)}); } } } });
  const lv=(arch.levels||[]).filter(l=>l.elevation_m!==null&&l.elevation_m!==undefined)
    .slice().sort((a,b)=>a.index-b.index);
  for(let i=0;i+1<lv.length;i++){
    const a=lv[i], b=lv[i+1];
    if(b.elevation_m<=a.elevation_m+_A_EPS)
      issues.push({code:'LEVEL_ELEVATION_INCONSISTENT', subject:b.id, below:a.id}); }
  const voided=new Set((arch.voids||[]).map(v=>v.core_id));
  (arch.cores||[]).forEach(c=>{
    if(c.served_levels.length>1&&!voided.has(c.id))
      issues.push({code:'VOID_MISSING_FOR_CORE', subject:c.id}); });
  return issues; }
/* ------------------------------------------------------------- خدمات --- */
function archElementById(arch,eid){
  const keys=['walls','openings','slabs','voids','ceilings','roofs','cores','spaces'];
  for(const key of keys)
    for(const el of (arch[key]||[]))
      if(el.id===eid) return el;
  if((arch.envelope||{}).id===eid) return arch.envelope;
  return null; }
/* يقبل الهوية الكاملة (ref@level) أو المرجع الدلالي (ref) كما تستعمله العلاقات.
   بلا مستوى محدّد: أوّل نسخة بترتيب المستويات — الهندسة نفسها في كل نسخ القالب */
function archOpeningByRef(arch,ref,levelIndex){
  if(ref===null||ref===undefined) return null;
  const li=(levelIndex===undefined)?null:levelIndex;
  for(const op of (arch.openings||[]))
    if(op.id===ref&&(li===null||op.level_index===li)) return op;
  for(const op of (arch.openings||[]))
    if(op.opening_ref===ref&&(li===null||op.level_index===li)) return op;
  return null; }
/* مرساة الفتحة من هندسة الجدار المضيف — أدقّ مصدر متاح لقياس المسافة */
function archOpeningAnchor(arch,openingId,levelIndex){
  const op=archOpeningByRef(arch,openingId,levelIndex);
  if(op===null||(op.type!=='DOOR'&&op.type!=='WINDOW')) return null;
  if(op.axis==='x') return [op.u_center,op.fixed];
  return [op.fixed,op.u_center]; }
function archSharedWallBetween(arch,a,b){
  for(const w of (arch.walls||[]))
    if(w.shared&&w.spaces.indexOf(a)>=0&&w.spaces.indexOf(b)>=0) return w;
  return null; }
/* باب مستضاف على جدار يفصل فراغين بالضبط = دليل اتصال مؤكَّد.
   يبقى null لأي حالة أقلّ من ذلك — الاستنتاج الهندسي القديم لا يُستبدل به */
function archDoorConnectsConfirmed(arch,openingId,levelIndex){
  const op=archOpeningByRef(arch,openingId,levelIndex);
  if(op===null||op.type!=='DOOR'||op.host_status!=='resolved') return null;
  const host=archElementById(arch,op.host_wall_id);
  if(host===null||!host.shared||host.spaces.length!==2) return null;
  return {wall_id:host.id, spaces:host.spaces.slice(),
    opening_id:op.id, opening_ref:(op.opening_ref===undefined)?null:op.opening_ref,
    level_id:(op.level_id===undefined)?null:op.level_id,
    level_index:(op.level_index===undefined)?null:op.level_index,
    basis:'door_hosted_on_a_wall_shared_by_exactly_two_spaces'}; }
/* تحويل محلي→عالمي: إزاحة المبنى ودورانه داخل إحداثيات الموقع */
function archToWorld(arch,x,z){
  const t=arch.transform||{};
  const rot=(Number(t.rotation_deg||0.0))*Math.PI/180;
  const px=Number((t.position||{}).x||0.0), pz=Number((t.position||{}).z||0.0);
  const ca=Math.cos(rot), sa=Math.sin(rot);
  return [px+x*ca-z*sa, pz+x*sa+z*ca]; }
function archSummary(arch){
  return {building_id:arch.building_id, compiler_version:arch.compiler_version,
    levels:(arch.levels||[]).length, spaces:(arch.spaces||[]).length,
    walls:(arch.walls||[]).length,
    shared_walls:(arch.walls||[]).filter(w=>w.shared).length,
    exterior_walls:(arch.walls||[]).filter(w=>w.exposure==='exterior').length,
    unresolved_walls:(arch.walls||[]).filter(w=>w.exposure==='unresolved').length,
    openings:(arch.openings||[]).length,
    unresolved_openings:(arch.openings||[]).filter(o=>o.host_status==='unresolved').length,
    slabs:(arch.slabs||[]).length, voids:(arch.voids||[]).length,
    ceilings:(arch.ceilings||[]).length, roofs:(arch.roofs||[]).length,
    cores:(arch.cores||[]).length,
    approximations:(arch.approximations||[]).length,
    issues:(arch.issues||[]).length,
    note:'architectural geometry only — no structural, MEP, fire or code content'}; }
/* ==================================================================
   المرحلة 2 — أساس النموذج الإنشائي (نسخة مطابقة لـ acs_struct.py).
   تمثيل فقط: لا تصميم ولا أحمال ولا تحجيم ولا تسليح ولا أساسات ولا مطابقة كود •
   النظام الإنشائي لا يُستنتج من نوع المبنى • احتياط العرض ليس بياناً إنشائياً •
   الاتصال الهندسي ليس مسار حمل • الجدار المعماري ليس جداراً إنشائياً.
   ================================================================== */
const ACS_STRUCT_SPEC = {
 "schema": "acs.struct/1",
 "compiler_version": "acs-struct-compiler/1.0.0",
 "note": "STRUCTURAL REPRESENTATION ONLY. This layer stores and normalises structural elements that were supplied to it. It performs NO structural design, NO load calculation (dead, live, wind, seismic), NO member sizing, NO reinforcement design, NO foundation design, NO capacity or deflection or shear or moment calculation, NO soil assessment and NO code compliance. Nothing here may be read as evidence that any member is adequate, safe or compliant.",
 "element_types": [
  "GRID_SYSTEM",
  "GRID_LINE",
  "STRUCTURAL_NODE",
  "COLUMN",
  "BEAM",
  "STRUCTURAL_SLAB",
  "STRUCTURAL_WALL",
  "FOUNDATION",
  "STRUCTURAL_CORE",
  "MATERIAL"
 ],
 "model_status": [
  "NOT_DEFINED",
  "PARTIAL",
  "REPRESENTED",
  "IMPORTED",
  "VERIFIED_DATA"
 ],
 "status_note": "DESIGNED / SAFE / COMPLIANT are deliberately absent. No engine in this platform can justify them.",
 "provenance_values": [
  "user",
  "imported",
  "ai_inference",
  "system_suggested",
  "system_default",
  "manual_verified",
  "test_fixture",
  "display_fallback",
  "unknown"
 ],
 "provenance_note": "ai_inference and system_suggested are proposals, never verified structural data. display_fallback exists only so a renderer can draw something; it must never be promoted into the semantic model. rule is intentionally NOT a provenance value here because no verified structural rule evidence exists.",
 "verified_sources": [
  "user",
  "imported",
  "manual_verified"
 ],
 "materials": [
  "concrete",
  "steel",
  "timber",
  "masonry",
  "composite",
  "other",
  "unknown"
 ],
 "material_note": "a material label carries no strength, grade, fire rating, elastic modulus or capacity. concrete does not imply an f'c and steel does not imply an Fy. Every optional property must be supplied explicitly and carries its own provenance.",
 "material_properties": [
  "grade",
  "strength",
  "density",
  "elastic_modulus"
 ],
 "section_shapes": [
  "rectangular",
  "circular",
  "square",
  "i_section",
  "hollow_rectangular",
  "hollow_circular",
  "other",
  "unknown"
 ],
 "foundation_types": [
  "isolated_footing",
  "strip_footing",
  "raft",
  "pile",
  "pile_cap",
  "other",
  "unknown"
 ],
 "structural_roles": [
  "unknown",
  "gravity",
  "lateral",
  "shear_wall",
  "retaining",
  "non_structural"
 ],
 "role_note": "structural_role stays unknown unless the model states it. An architectural wall is not a structural wall, and an architectural stair or elevator core is not a lateral core, without explicit evidence.",
 "alignment_states": [
  "aligned",
  "offset",
  "unresolved"
 ],
 "relationship_types": [
  "COLUMN_SUPPORTS",
  "BEAM_CONNECTS",
  "SLAB_SUPPORTED_BY",
  "WALL_SUPPORTED_BY",
  "FOUNDATION_SUPPORTS",
  "CORE_SPANS_LEVELS",
  "COLUMN_STACKS",
  "MEMBER_IN_SPACE"
 ],
 "relationship_statuses": [
  "confirmed",
  "inferred",
  "unresolved"
 ],
 "relationship_note": "these edges record model topology and geometric connectivity only. GEOMETRIC CONNECTIVITY IS NOT A STRUCTURAL LOAD PATH. No edge here states that a member carries anything.",
 "issue_severities": [
  "INFO",
  "WARNING",
  "ERROR"
 ],
 "severity_note": "these are model-quality severities. UNSAFE / DANGEROUS / CODE VIOLATION are deliberately absent and are never justified by this layer.",
 "issue_codes": {
  "DUPLICATE_ELEMENT_ID": "ERROR",
  "UNSUPPORTED_ELEMENT_TYPE": "WARNING",
  "INVALID_LEVEL_REF": "ERROR",
  "INVALID_NODE_REF": "ERROR",
  "INVALID_MATERIAL_REF": "ERROR",
  "INVALID_GRID_REF": "WARNING",
  "CROSS_BUILDING_REF": "ERROR",
  "NAN_COORDINATE": "ERROR",
  "NEGATIVE_DIMENSION": "ERROR",
  "MEMBER_ZERO_LENGTH": "ERROR",
  "COLUMN_ZERO_HEIGHT": "ERROR",
  "COLUMN_HEIGHT_MISMATCH": "WARNING",
  "COLUMN_OUTSIDE_BUILDING": "WARNING",
  "BEAM_ENDPOINT_UNRESOLVED": "ERROR",
  "BEAM_FLOATING": "WARNING",
  "STRUCTURAL_ALIGNMENT_BREAK": "WARNING",
  "COLUMN_OFFSET": "WARNING",
  "FOUNDATION_REF_MISSING": "WARNING",
  "FOUNDATION_TARGET_UNRESOLVED": "ERROR",
  "FOUNDATION_OUTSIDE_SITE": "WARNING",
  "SLAB_LEVEL_UNRESOLVED": "ERROR",
  "WALL_LEVELS_UNRESOLVED": "ERROR",
  "CORE_LEVELS_UNRESOLVED": "ERROR",
  "SECTION_UNKNOWN": "INFO",
  "MATERIAL_UNKNOWN": "INFO",
  "COLUMN_BLOCKS_OPENING": "WARNING",
  "COLUMN_IN_FLOOR_OPENING": "WARNING",
  "COLUMN_IN_ELEVATOR_CORE": "WARNING",
  "BEAM_CROSSES_OPENING": "INFO"
 },
 "display_fallbacks": {
  "column_width_m": 0.3,
  "column_depth_m": 0.3,
  "column_diameter_m": 0.35,
  "beam_width_m": 0.25,
  "beam_depth_m": 0.5,
  "structural_slab_thickness_m": 0.2,
  "structural_wall_thickness_m": 0.25,
  "foundation_width_m": 1.2,
  "foundation_depth_m": 1.2,
  "foundation_thickness_m": 0.5,
  "foundation_embedment_m": 1.0
 },
 "display_fallback_note": "DISPLAY GEOMETRY IS NOT STRUCTURAL DESIGN. When a section, thickness or footprint is not supplied the semantic field stays null and the renderer reads these numbers instead, tagged source=display_fallback. A fallback is never written back into the model, never exported as engineering metadata and never used as an input to any rule.",
 "forbidden_claims": [
  "structurally_safe",
  "structurally_adequate",
  "load_bearing_verified",
  "capacity",
  "utilisation",
  "design_load",
  "dead_load",
  "live_load",
  "wind_load",
  "seismic_load",
  "reinforcement",
  "rebar",
  "deflection",
  "shear_capacity",
  "bending_moment",
  "axial_capacity",
  "punching_shear",
  "soil_bearing_capacity",
  "compliant",
  "code_required",
  "meets_sbc"
 ],
 "id_patterns": {
  "grid_system": "<bid>.gs_<n>",
  "grid_line": "<bid>.grid_<axis>_<label>",
  "node": "<bid>.node_<n>",
  "column": "<bid>.col_<n>",
  "beam": "<bid>.beam_<n>",
  "slab": "<bid>.sslab_<n>",
  "wall": "<bid>.swall_<n>",
  "foundation": "<bid>.fnd_<n>",
  "core": "<bid>.score_<n>",
  "material": "<bid>.mat_<n>",
  "relationship": "<bid>.srel_<n>"
 },
 "id_note": "an id supplied by the model is kept and namespaced with the building id; an id that is absent is generated from the element's canonical sort position, so the same model always yields the same ids. Two buildings can never collide.",
 "source_of_truth": "the structural model lives alongside the architectural model and never replaces it. Levels come from the architectural level table so structural members cannot float on renderer-only coordinates. Architectural walls, slabs and cores are never reclassified as structural by this layer.",
 "axis_note": "structural members carry local coordinates and the building transform (position + rotation) is applied on read, exactly as in the architectural layer. A grid system may additionally carry its own rotation and origin, so a rotated grid inside a rotated building is expressed without assuming project world axes.",
 "no_generator_note": "this phase deliberately ships NO automatic structural system generator. suggest_structural_grid is the only proposal helper, it is optional, its output is a SUGGESTION object marked persisted=false, and nothing in the compiler writes it into the model."
};
const STRUCT_SCHEMA = ACS_STRUCT_SPEC.schema;
const STRUCT_COMPILER_VERSION = ACS_STRUCT_SPEC.compiler_version;
const STRUCT_ELEMENT_TYPES = ACS_STRUCT_SPEC.element_types;
const STRUCT_MODEL_STATUS = ACS_STRUCT_SPEC.model_status;
const STRUCT_PROVENANCE = ACS_STRUCT_SPEC.provenance_values;
const STRUCT_VERIFIED_SOURCES = ACS_STRUCT_SPEC.verified_sources;
const STRUCT_MATERIALS = ACS_STRUCT_SPEC.materials;
const STRUCT_SECTION_SHAPES = ACS_STRUCT_SPEC.section_shapes;
const STRUCT_FOUNDATION_TYPES = ACS_STRUCT_SPEC.foundation_types;
const STRUCT_ROLES = ACS_STRUCT_SPEC.structural_roles;
const STRUCT_ALIGNMENT_STATES = ACS_STRUCT_SPEC.alignment_states;
const STRUCT_REL_TYPES = ACS_STRUCT_SPEC.relationship_types;
const STRUCT_REL_STATUSES = ACS_STRUCT_SPEC.relationship_statuses;
const STRUCT_SEVERITIES = ACS_STRUCT_SPEC.issue_severities;
const STRUCT_ISSUE_CODES = ACS_STRUCT_SPEC.issue_codes;
const STRUCT_FALLBACKS = ACS_STRUCT_SPEC.display_fallbacks;
const _S_EPS = 1e-6;
const _S_POS_TOL = 0.01;     /* تسامح تطابق الموضع بين مستويين (م) */
const _S_OFFSET_TOL = 1.00;  /* ما دون هذا إزاحة، وما فوقه انقطاع محور (م) */

function structSeverityOf(code){
  return Object.prototype.hasOwnProperty.call(STRUCT_ISSUE_CODES,code)
    ?STRUCT_ISSUE_CODES[code]:'WARNING'; }
/* رقم حقيقي أو null — NaN/inf/نص غير رقمي لا تمرّ بصمت (مطابق لـ float() في بايثون) */
function _snum(v){
  if(v===null||v===undefined||typeof v==='boolean') return null;
  if(typeof v==='number') return (isFinite(v)?v:null);
  if(typeof v!=='string') return null;
  const t=v.trim();
  if(!/^[+-]?((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?|0[xX][0-9a-fA-F]+)$/.test(t)) return null;
  const n=Number(t);
  return isFinite(n)?n:null; }
function _sBadNumber(v){
  return v!==null&&v!==undefined&&typeof v!=='boolean'&&_snum(v)===null; }
function _ssrc(v,dflt){
  const s=(v===null||v===undefined)?(dflt||'unknown'):String(v).toLowerCase();
  return STRUCT_PROVENANCE.indexOf(s)>=0?s:'unknown'; }
/* خاصية اختيارية: قيمة + مصدرها. الغياب يبقى غياباً */
function _sprop(stated,source){
  const n=_snum(stated);
  if(n===null) return {value:null,source:'unknown'};
  return {value:n,source:_ssrc(source,'imported')}; }
/* قيمة دلالية + احتياط عرض منفصل. الاحتياط ليس حقيقة إنشائية أبداً */
function _sfallback(value,key){
  const n=_snum(value);
  if(n===null) return {value:null,render_fallback:STRUCT_FALLBACKS[key],
    source:'unknown',render_source:'display_fallback'};
  return {value:n,render_fallback:STRUCT_FALLBACKS[key],
    source:'imported',render_source:'model'}; }
function _sraw(building){
  const st=building.structural;
  return (st&&typeof st==='object'&&!Array.isArray(st))?st:{}; }
function _sLevelsIndex(building,bid){
  const idx=new Map();
  _aLevels(building,bid).forEach(l=>{ idx.set('#'+l.index,l); idx.set('$'+String(l.id),l); });
  return idx; }
function _sLevelOf(idx,ref){
  if(ref===null||ref===undefined||typeof ref==='boolean') return null;
  if(typeof ref==='number') return idx.get('#'+Math.trunc(ref))||null;
  return idx.get('$'+String(ref))||null; }
function _snid(bid,given,prefix,n){
  if(_pyT(given)){
    const s=String(given);
    if(s.indexOf(bid+'.')===0) return s;
    /* معرّف يحمل بادئة مبنى آخر يُترك كما هو ليكشفه التحقّق بدل أن نخفيه */
    const head=s.split('.')[0];
    if(head.indexOf('bld_')===0&&head!==bid) return s;
    return bid+'.'+s; }
  return bid+'.'+prefix+'_'+n; }
function _sSortNum(a,b){ return a<b?-1:(a>b?1:0); }
/* ترتيب مركّب على نمط بايثون: رقم قبل نصّ قبل غياب */
function _sKey(v){
  if(v===null||v===undefined) return [2,0,''];
  if(typeof v==='string') return [1,0,v];
  return [0,Number(v),'']; }
function _sKeyCmp(a,b){
  for(let i=0;i<Math.min(a.length,b.length);i++){
    const x=_sKey(a[i]), y=_sKey(b[i]);
    if(x[0]!==y[0]) return x[0]-y[0];
    if(x[0]===0&&x[1]!==y[1]) return x[1]<y[1]?-1:1;
    if(x[0]===1&&x[2]!==y[2]) return _scmp(x[2],y[2]); }
  return 0; }
const _byId=(a,b)=>_scmp(String(a.id),String(b.id));
/* ------------------------------------------------------------- المواد --- */
function _sMaterials(raw,bid){
  const out=[];
  (_pyT(raw.materials)?raw.materials:[]).forEach((m,n)=>{
    const mat=String(_pyT(m.material)?m.material:'unknown').toLowerCase();
    const known=STRUCT_MATERIALS.indexOf(mat)>=0;
    out.push({id:_snid(bid,m.id,'mat',n), type:'MATERIAL', building_id:bid,
      material:known?mat:'other',
      declared_material:(m.material===undefined)?null:m.material,
      material_recognised:known,
      /* التسمية وحدها لا تحمل مقاومة ولا معايرة: كل خاصية تُذكر صراحةً */
      grade:(m.grade===null||m.grade===undefined)?{value:null,source:'unknown'}
            :{value:m.grade,source:_ssrc(m.source,'imported')},
      strength:_sprop(m.strength,m.source),
      density:_sprop(m.density,m.source),
      elastic_modulus:_sprop(m.elastic_modulus,m.source),
      source:_ssrc(m.source),
      note:'a material label implies no strength, grade, modulus or capacity'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ الشبكات --- */
function _sGrids(raw,bid){
  let systems=raw.grid_systems;
  if(!_pyT(systems)){
    const flat=_pyT(raw.grids)?raw.grids:[];
    systems=flat.length?[{id:'gs_0',label:null,grids:flat}]:[]; }
  const out=[];
  systems.forEach((gs,n)=>{
    const lines=[];
    (_pyT(gs.grids)?gs.grids:[]).forEach((g,k)=>{
      let axis=String(_pyT(g.axis)?g.axis:'X').toUpperCase().slice(0,1);
      if(axis!=='X'&&axis!=='Z') axis='X';
      const label=(g.label===undefined)?null:g.label;
      const gid=_pyT(g.id)?g.id:('grid_'+axis.toLowerCase()+'_'+
        ((label===null||label===undefined)?k:label));
      lines.push({id:_snid(bid,gid,'grid',k), type:'GRID_LINE', building_id:bid,
        axis:axis, label:label, position_m:_snum(g.position_m),
        position_stated:_snum(g.position_m)!==null,
        source:_ssrc(_pyT(g.source)?g.source:gs.source)}); });
    lines.sort((a,b)=>_sKeyCmp([a.axis,a.position_m,String(a.id)],
                               [b.axis,b.position_m,String(b.id)]));
    const org=(gs.origin&&typeof gs.origin==='object')?gs.origin:{};
    out.push({id:_snid(bid,gs.id,'gs',n), type:'GRID_SYSTEM', building_id:bid,
      label:(gs.label===undefined)?null:gs.label,
      origin:{x:_snum(org.x)||0.0, z:_snum(org.z)||0.0},
      rotation_deg:_snum(gs.rotation_deg)||0.0,
      rotation_stated:_snum(gs.rotation_deg)!==null,
      source:_ssrc(gs.source), grids:lines}); });
  out.sort(_byId); return out; }
function _sGridIndex(systems){
  const idx=new Set();
  systems.forEach(gs=>gs.grids.forEach(g=>idx.add(g.id)));
  return idx; }
/* -------------------------------------------------------------- العقد --- */
function _sNodes(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.nodes)?raw.nodes:[]).forEach((nd,n)=>{
    const lvl=_sLevelOf(levelsIdx,nd.level);
    let y=_snum(nd.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    out.push({id:_snid(bid,nd.id,'node',n), type:'STRUCTURAL_NODE', building_id:bid,
      x:_snum(nd.x), y:y, z:_snum(nd.z),
      y_source:(_snum(nd.y)!==null)?'imported':((lvl!==null)?'architectural_level':'unknown'),
      level_ref:(nd.level===undefined)?null:nd.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(nd.level===null||nd.level===undefined),
      raw_x:(nd.x===undefined)?null:nd.x, raw_z:(nd.z===undefined)?null:nd.z,
      source:_ssrc(nd.source)}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ الأعمدة --- */
/* مقطع معلن فقط. لا نختار بُعداً إنشائياً من أجل الرسم */
function _sSection(sec){
  if(!sec||typeof sec!=='object'||Array.isArray(sec)) return null;
  let shape=String(_pyT(sec.shape)?sec.shape:'unknown').toLowerCase();
  if(STRUCT_SECTION_SHAPES.indexOf(shape)<0) shape='other';
  const pick=(a,b)=>_snum((sec[a]!==null&&sec[a]!==undefined)?sec[a]:sec[b]);
  const out={shape:shape, width_m:pick('width','width_m'),
    depth_m:pick('depth','depth_m'), diameter_m:pick('diameter','diameter_m'),
    source:_ssrc(sec.source,'imported')};
  if(out.width_m===null&&out.depth_m===null&&out.diameter_m===null) return null;
  return out; }
/* هندسة الرسم فقط. تُوسم دائماً بمصدرها ولا تُكتب في النموذج الدلالي */
function _sRenderSection(section,wkey,dkey){
  if(section&&section.diameter_m!==null&&section.diameter_m!==undefined){
    const d=section.diameter_m;
    return {shape:section.shape,w:d,d:d,source:'model'}; }
  if(section&&(section.width_m!==null||section.depth_m!==null)){
    let w=section.width_m, d=section.depth_m;
    if(w===null) w=d;
    if(d===null) d=w;
    return {shape:section.shape,w:w,d:d,source:'model'}; }
  return {shape:'unknown',w:STRUCT_FALLBACKS[wkey],d:STRUCT_FALLBACKS[dkey],
    source:'display_fallback'}; }
function _sColumns(raw,bid,levelsIdx,gridIdx){
  const out=[];
  (_pyT(raw.columns)?raw.columns:[]).forEach((c,n)=>{
    const base=_sLevelOf(levelsIdx,c.base_level), top=_sLevelOf(levelsIdx,c.top_level);
    const pos=(c.position&&typeof c.position==='object'&&!Array.isArray(c.position))?c.position:c;
    const x=_snum(pos.x), z=_snum(pos.z);
    let be=_snum(c.base_elevation_m), te=_snum(c.top_elevation_m);
    if(be===null&&base!==null) be=base.elevation_m;
    if(te===null&&top!==null) te=top.elevation_m;
    const h=(be!==null&&te!==null)?(te-be):null;
    const sec=_sSection(c.section);
    const refs=(_pyT(c.grid_refs)?c.grid_refs:[]).slice();
    out.push({id:_snid(bid,c.id,'col',n), type:'COLUMN', building_id:bid,
      x:x, z:z, raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      base_level_ref:(c.base_level===undefined)?null:c.base_level,
      top_level_ref:(c.top_level===undefined)?null:c.top_level,
      base_level_id:base?base.id:null, top_level_id:top?top.id:null,
      base_level_index:base?base.index:null, top_level_index:top?top.index:null,
      levels_resolved:((base!==null)||(c.base_level===null||c.base_level===undefined))
                      &&((top!==null)||(c.top_level===null||c.top_level===undefined)),
      base_elevation_m:be, top_elevation_m:te, height_m:h,
      height_basis:((_snum(c.base_elevation_m)===null&&be!==null)?'architectural_levels'
                    :((be!==null)?'stated_elevations':'unresolved')),
      declared_height_m:_snum(c.height_m),
      section:sec,
      render_section:_sRenderSection(sec,'column_width_m','column_depth_m'),
      material_ref:(c.material_ref===undefined)?null:c.material_ref,
      grid_refs:refs,
      unresolved_grid_refs:refs.filter(r=>_pyT(r)&&!gridIdx.has(_snid(bid,r,'grid',0))
                                         &&!gridIdx.has(r)),
      structural_role:_pyT(c.structural_role)?String(c.structural_role).toLowerCase():'unknown',
      source:_ssrc(c.source), status:null, stack:null,
      note:'represented structural column — no capacity, sizing or adequacy is implied'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------- الجسور --- */
function _sBeams(raw,bid,levelsIdx,nodeIdx,gridIdx){
  const out=[];
  (_pyT(raw.beams)?raw.beams:[]).forEach((b,n)=>{
    const lvl=_sLevelOf(levelsIdx,b.level);
    const ends=[];
    [['from','from_point'],['to','to_point']].forEach(pair=>{
      const ref=(b[pair[0]]===undefined)?null:b[pair[0]];
      const pt=b[pair[1]];
      const node=_pyT(ref)?(nodeIdx.get(String(ref))||nodeIdx.get(_snid(bid,ref,'node',0))||null)
                          :null;
      if(node){ ends.push({ref:ref,node_id:node.id,x:node.x,z:node.z,basis:'structural_node'}); }
      else if(pt&&typeof pt==='object'&&_snum(pt.x)!==null&&_snum(pt.z)!==null){
        ends.push({ref:null,node_id:null,x:_snum(pt.x),z:_snum(pt.z),basis:'stated_point'}); }
      else {
        ends.push({ref:ref,node_id:null,x:null,z:null,
          basis:(ref!==null&&ref!==undefined)?'unknown_node':'unresolved'}); } });
    let length=null;
    if(ends.every(e=>e.x!==null&&e.z!==null)){
      const dx=ends[1].x-ends[0].x, dz=ends[1].z-ends[0].z;
      length=Math.sqrt(dx*dx+dz*dz); }
    const sec=_sSection(b.section);
    const grefs=(_pyT(b.grid_refs)?b.grid_refs:[]).slice();
    out.push({id:_snid(bid,b.id,'beam',n), type:'BEAM', building_id:bid,
      level_ref:(b.level===undefined)?null:b.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(b.level===null||b.level===undefined),
      elevation_m:(_snum(b.elevation_m)!==null)?_snum(b.elevation_m):(lvl?lvl.elevation_m:null),
      start:ends[0], end:ends[1], length_m:length,
      section:sec, render_section:_sRenderSection(sec,'beam_width_m','beam_depth_m'),
      material_ref:(b.material_ref===undefined)?null:b.material_ref,
      grid_refs:grefs,
      unresolved_grid_refs:grefs.filter(r=>_pyT(r)&&!gridIdx.has(r)
                                          &&!gridIdx.has(_snid(bid,r,'grid',0))),
      structural_role:_pyT(b.structural_role)?String(b.structural_role).toLowerCase():'unknown',
      source:_ssrc(b.source), status:null,
      note:'represented structural beam — no span, sizing or capacity is implied'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------ البلاطات والجدران والنوى --- */
function _sOutline(v){
  if(Array.isArray(v)&&v.length>=4){
    const vals=v.slice(0,4).map(_snum);
    return vals.every(x=>x!==null)?vals:null; }
  return null; }
function _sSlabs(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.slabs)?raw.slabs:[]).forEach((s,n)=>{
    const lvl=_sLevelOf(levelsIdx,s.level);
    /* البلاطة المعمارية ليست بلاطة إنشائية: التصنيف يأتي من النموذج لا منّا */
    const cls=String(_pyT(s.classification)?s.classification
      :((['user','imported','manual_verified'].indexOf(s.source)>=0)?'supplied':'unverified'))
      .toLowerCase();
    out.push({id:_snid(bid,s.id,'sslab',n), type:'STRUCTURAL_SLAB', building_id:bid,
      level_ref:(s.level===undefined)?null:s.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(s.level===null||s.level===undefined),
      elevation_m:lvl?lvl.elevation_m:null,
      outline:_sOutline(s.outline),
      thickness_m:_sfallback(s.thickness_m,'structural_slab_thickness_m'),
      system:(s.system===undefined)?null:s.system,
      material_ref:(s.material_ref===undefined)?null:s.material_ref,
      classification:cls,
      supported_by:(_pyT(s.supported_by)?s.supported_by:[]).slice(),
      structural_role:_pyT(s.structural_role)?String(s.structural_role).toLowerCase():'unknown',
      source:_ssrc(s.source),
      note:'a structural slab is a separate element from the architectural floor slab'}); });
  out.sort(_byId); return out; }
function _sWalls(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.walls)?raw.walls:[]).forEach((w,n)=>{
    const refs=Array.isArray(w.levels)?w.levels
      :((w.level!==null&&w.level!==undefined)?[w.level]:[]);
    const lv=refs.map(r=>_sLevelOf(levelsIdx,r));
    const st=(w.start&&typeof w.start==='object')?w.start:{};
    const en=(w.end&&typeof w.end==='object')?w.end:{};
    const sx=_snum(st.x), sz=_snum(st.z), ex=_snum(en.x), ez=_snum(en.z);
    const length=([sx,sz,ex,ez].every(v=>v!==null))
      ?Math.sqrt(Math.pow(ex-sx,2)+Math.pow(ez-sz,2)):null;
    out.push({id:_snid(bid,w.id,'swall',n), type:'STRUCTURAL_WALL', building_id:bid,
      level_refs:refs, level_ids:lv.filter(Boolean).map(l=>l.id),
      level_indexes:lv.filter(Boolean).map(l=>l.index).sort(_sSortNum),
      levels_resolved:lv.every(l=>l!==null)&&refs.length>0,
      start:{x:sx,z:sz}, end:{x:ex,z:ez}, length_m:length,
      thickness_m:_sfallback(w.thickness_m,'structural_wall_thickness_m'),
      material_ref:(w.material_ref===undefined)?null:w.material_ref,
      /* لا يصير جداراً حاملاً ولا جدار قص إلا بذكر صريح */
      structural_role:_pyT(w.structural_role)?String(w.structural_role).toLowerCase():'unknown',
      arch_wall_id:(w.arch_wall_id===undefined)?null:w.arch_wall_id,
      supported_by:(_pyT(w.supported_by)?w.supported_by:[]).slice(),
      source:_ssrc(w.source),
      note:'an architectural wall never becomes structural without explicit evidence'}); });
  out.sort(_byId); return out; }
function _sCores(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.cores)?raw.cores:[]).forEach((c,n)=>{
    const refs=(_pyT(c.levels)?c.levels:[]).slice();
    const lv=refs.map(r=>_sLevelOf(levelsIdx,r));
    out.push({id:_snid(bid,c.id,'score',n), type:'STRUCTURAL_CORE', building_id:bid,
      level_refs:refs, level_ids:lv.filter(Boolean).map(l=>l.id),
      level_indexes:lv.filter(Boolean).map(l=>l.index).sort(_sSortNum),
      levels_resolved:lv.every(l=>l!==null)&&refs.length>0,
      outline:_sOutline(c.outline),
      thickness_m:_sfallback(c.thickness_m,'structural_wall_thickness_m'),
      material_ref:(c.material_ref===undefined)?null:c.material_ref,
      arch_core_id:(c.arch_core_id===undefined)?null:c.arch_core_id,
      arch_core_link_source:_pyT(c.arch_core_id)?_ssrc(c.arch_core_link_source):'unknown',
      structural_role:_pyT(c.structural_role)?String(c.structural_role).toLowerCase():'unknown',
      source:_ssrc(c.source),
      note:'an architectural stair or elevator core is not a lateral core '+
           'unless the model says so'}); });
  out.sort(_byId); return out; }
/* ----------------------------------------------------------- الأساسات --- */
function _sFoundations(raw,bid){
  const out=[];
  (_pyT(raw.foundations)?raw.foundations:[]).forEach((f,n)=>{
    let t=String(_pyT(f.type)?f.type:'unknown').toLowerCase();
    if(STRUCT_FOUNDATION_TYPES.indexOf(t)<0) t='other';
    const pos=(f.position&&typeof f.position==='object'&&!Array.isArray(f.position))?f.position:f;
    out.push({id:_snid(bid,f.id,'fnd',n), type:'FOUNDATION', building_id:bid,
      foundation_type:t, declared_type:(f.type===undefined)?null:f.type,
      x:_snum(pos.x), z:_snum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      outline:_sOutline(f.outline),
      width_m:_sfallback(f.width_m,'foundation_width_m'),
      depth_m:_sfallback(f.depth_m,'foundation_depth_m'),
      thickness_m:_sfallback(f.thickness_m,'foundation_thickness_m'),
      embedment_m:_sfallback(f.embedment_m,'foundation_embedment_m'),
      top_elevation_m:_snum(f.top_elevation_m),
      material_ref:(f.material_ref===undefined)?null:f.material_ref,
      supports:(_pyT(f.supports)?f.supports:[]).slice(),
      /* لا تربة ولا قدرة تحمّل: لا شيء من ذلك يُستنتج هنا */
      soil:null, source:_ssrc(f.source),
      note:'represented foundation — no size, soil property or bearing capacity '+
           'is calculated or implied'}); });
  out.sort(_byId); return out; }
/* ---------------------------------------------------- تكديس الأعمدة --- */
/* استمرارية هندسية بين مستويين. ليست حكماً بصحّة إنشائية إطلاقاً */
function _sStacks(columns,issues){
  const rels=[], byTop=new Map();
  columns.forEach(c=>{ if(c.top_level_index!==null&&c.top_level_index!==undefined){
    if(!byTop.has(c.top_level_index)) byTop.set(c.top_level_index,[]);
    byTop.get(c.top_level_index).push(c); } });
  columns.forEach(c=>{
    const bi=c.base_level_index;
    if(bi===null||bi===undefined||c.x===null||c.z===null){
      c.stack={state:'unresolved',reason:'base level or position is not resolved'};
      return; }
    const below=(byTop.get(bi)||[]).filter(d=>d.id!==c.id&&d.x!==null&&d.z!==null);
    if(!below.length){
      c.stack={state:'unresolved',reason:'no column terminates at this base level',
        supported_by:null,offset_m:null};
      return; }
    let best=null, dist=null;
    below.forEach(d=>{
      const g=Math.sqrt(Math.pow(d.x-c.x,2)+Math.pow(d.z-c.z,2));
      if(dist===null||g<dist||(g===dist&&_scmp(String(d.id),String(best.id))<0)){ best=d; dist=g; } });
    let state;
    if(dist<=_S_POS_TOL) state='aligned';
    else if(dist<=_S_OFFSET_TOL){ state='offset';
      issues.push({code:'COLUMN_OFFSET',subject:c.id,other:best.id,
        offset_m:_pyRound(dist,6),
        detail:'the column below is offset; no transfer element is designed or assumed'}); }
    else { state='unresolved';
      issues.push({code:'STRUCTURAL_ALIGNMENT_BREAK',subject:c.id,nearest:best.id,
        distance_m:_pyRound(dist,6),
        detail:'no column terminates under this column within tolerance; '+
               'reported as a factual condition only'}); }
    c.stack={state:state,supported_by:best.id,offset_m:_pyRound(dist,6),reason:null};
    rels.push(['COLUMN_STACKS',best.id,c.id,(state==='aligned')?'confirmed':'inferred',
      'geometric_continuity_between_levels',{alignment:state,offset_m:_pyRound(dist,6)}]); });
  return rels; }
/* ----------------------------------------------------------- العلاقات --- */
function _sRelationships(bid,cols,beams,slabs,walls,cores,fnds,stackRels,arch,issues){
  const rels=[]; let seq=0;
  const add=(rtype,frm,to,status,basis,meta)=>{ seq+=1;
    const e={id:bid+'.srel_'+seq,type:rtype,from:frm,to:to,
      source:(status!=='confirmed')?'geometry_inference':'model_declaration',
      status:status,basis:basis,
      note:'geometric connectivity only — this is not a load path'};
    if(_pyT(meta)) e.meta=meta;
    rels.push(e); return e; };
  stackRels.forEach(r=>add(r[0],r[1],r[2],r[3],r[4],r[5]));
  const colIds=new Set(cols.map(c=>c.id));
  beams.forEach(b=>{
    [b.start,b.end].forEach(end=>{
      if(_pyT(end.node_id)) add('BEAM_CONNECTS',b.id,end.node_id,'confirmed',
        'beam endpoint references a declared structural node');
      else if(end.basis==='stated_point') add('BEAM_CONNECTS',b.id,null,'inferred',
        'beam endpoint is a stated point with no node',{x:end.x,z:end.z});
      else add('BEAM_CONNECTS',b.id,null,'unresolved',
        'beam endpoint could not be resolved',{ref:end.ref}); });
    /* تلامس عمود/جسر: اتصال هندسي فقط، ولا يعني أنّ العمود يحمل الجسر */
    if(b.level_index!==null&&b.level_index!==undefined){
      [b.start,b.end].forEach(end=>{
        if(end.x===null) return;
        cols.forEach(c=>{
          if(c.x===null||c.top_level_index!==b.level_index) return;
          if(Math.sqrt(Math.pow(c.x-end.x,2)+Math.pow(c.z-end.z,2))<=_S_POS_TOL)
            add('COLUMN_SUPPORTS',c.id,b.id,'confirmed',
              'beam endpoint coincides with the column axis at this level',
              {disclaimer:'geometric connectivity, not a load path'}); }); }); } });
  const otherIds=id=>beams.concat(walls).concat(cores).some(e=>e.id===id);
  slabs.forEach(s=>s.supported_by.forEach(ref=>{
    const tgt=_snid(bid,ref,'x',0);
    const known=colIds.has(tgt)||otherIds(tgt);
    add('SLAB_SUPPORTED_BY',s.id,known?tgt:null,known?'confirmed':'unresolved',
      known?'declared by the model':'declared support was not found'); }));
  const wallTargets=id=>beams.concat(walls).concat(fnds).some(e=>e.id===id);
  walls.forEach(w=>w.supported_by.forEach(ref=>{
    const tgt=_snid(bid,ref,'x',0);
    const known=colIds.has(tgt)||wallTargets(tgt);
    add('WALL_SUPPORTED_BY',w.id,known?tgt:null,known?'confirmed':'unresolved',
      known?'declared by the model':'declared support was not found'); }));
  const allIds=new Set(cols.concat(beams).concat(slabs).concat(walls).concat(cores).map(e=>e.id));
  fnds.forEach(f=>{
    if(!f.supports.length)
      issues.push({code:'FOUNDATION_REF_MISSING',subject:f.id,
        detail:'this foundation declares no member it is placed under'});
    f.supports.forEach(ref=>{
      const tgt=_snid(bid,ref,'x',0);
      if(allIds.has(tgt))
        add('FOUNDATION_SUPPORTS',f.id,tgt,'confirmed','declared by the model',
          {disclaimer:'placement relationship only — no bearing check is performed'});
      else { issues.push({code:'FOUNDATION_TARGET_UNRESOLVED',subject:f.id,ref:ref});
        add('FOUNDATION_SUPPORTS',f.id,null,'unresolved',
          'declared support target was not found'); } }); });
  cores.forEach(c=>{ if(c.level_indexes.length>1)
    add('CORE_SPANS_LEVELS',c.id,null,'confirmed','declared by the model',
      {levels:c.level_indexes.slice()}); });
  /* موقع العضو داخل فراغ معماري — علاقة مكانية فقط، لا حكم بالقبول */
  if(arch){
    cols.forEach(c=>{
      if(c.x===null||c.base_level_index===null||c.base_level_index===undefined) return;
      (arch.spaces||[]).forEach(sp=>{
        const rc=sp.rect;
        if(!rc||sp.level_index!==c.base_level_index) return;
        if(rc[0]-_S_EPS<=c.x&&c.x<=rc[0]+rc[2]+_S_EPS&&
           rc[1]-_S_EPS<=c.z&&c.z<=rc[1]+rc[3]+_S_EPS)
          add('MEMBER_IN_SPACE',c.id,sp.id,'confirmed',
            'the column axis lies inside this architectural space',
            {space_id:(sp.space_id===undefined)?null:sp.space_id,
             disclaimer:'spatial location only — acceptability is not judged here'}); }); }); }
  return rels; }
/* ------------------------------------------------- تداخل مع المعماري --- */
/* تعارضات هندسية واضحة فقط — ليست كشف تصادم BIM كاملاً ولا فحص كود */
function _sInterference(cols,beams,fnds,arch,building,issues){
  if(!arch) return;
  cols.forEach(c=>{
    if(c.x===null||c.base_level_index===null||c.base_level_index===undefined) return;
    const rs=c.render_section, known=rs.source==='model';
    const hw=known?(rs.w/2.0):0.0, hd=known?(rs.d/2.0):0.0;
    const basis=known?'column_section_footprint':'column_axis_point';
    (arch.voids||[]).forEach(v=>{
      if(v.level_index!==c.base_level_index&&v.level_index!==c.top_level_index) return;
      const r=v.rect;
      if(c.x+hw>r[0]&&c.x-hw<r[0]+r[2]&&c.z+hd>r[1]&&c.z-hd<r[1]+r[3]){
        const code=(v.core_type==='ELEVATOR_SHAFT')?'COLUMN_IN_ELEVATOR_CORE'
                                                   :'COLUMN_IN_FLOOR_OPENING';
        issues.push({code:code,subject:c.id,other:v.id,basis:basis}); } });
    (arch.openings||[]).forEach(o=>{
      if(o.level_index!==c.base_level_index) return;
      let w=o.width_m.value;
      if(w===null||w===undefined) w=o.width_m.render_fallback;
      const a=o.u_center-w/2.0, b=o.u_center+w/2.0;
      let cu,cf,hu,hf;
      if(o.axis==='x'){ cu=c.x; cf=c.z; hu=hw; hf=hd; }
      else { cu=c.z; cf=c.x; hu=hd; hf=hw; }
      if(cu+hu>a&&cu-hu<b&&Math.abs(cf-o.fixed)<=Math.max(hf,0.15))
        issues.push({code:'COLUMN_BLOCKS_OPENING',subject:c.id,other:o.id,basis:basis}); }); });
  beams.forEach(b=>{
    if(b.start.x===null||b.end.x===null||b.level_index===null||b.level_index===undefined) return;
    (arch.openings||[]).forEach(o=>{
      if(o.level_index!==b.level_index||o.type!=='DOOR') return;
      const w=o.width_m.value||o.width_m.render_fallback;
      const ax=o.axis;
      const fu0=(ax==='x')?b.start.x:b.start.z, fu1=(ax==='x')?b.end.x:b.end.z;
      const ff0=(ax==='x')?b.start.z:b.start.x, ff1=(ax==='x')?b.end.z:b.end.x;
      if(Math.abs(ff0-o.fixed)<=0.15&&Math.abs(ff1-o.fixed)<=0.15){
        const lo=Math.min(fu0,fu1), hi=Math.max(fu0,fu1);
        if(lo<o.u_center+w/2.0&&hi>o.u_center-w/2.0)
          issues.push({code:'BEAM_CROSSES_OPENING',subject:b.id,other:o.id,
            detail:'the beam runs along the wall line carrying this opening; '+
                   'head clearance is NOT evaluated'}); } }); });
  const site=(building.site&&typeof building.site==='object')?building.site:null;
  if(site){
    const sw=_snum(site.w), sd=_snum(site.d);
    fnds.forEach(f=>{
      if(f.x===null||sw===null||sd===null) return;
      if(f.x<-_S_EPS||f.z<-_S_EPS||f.x>sw+_S_EPS||f.z>sd+_S_EPS)
        issues.push({code:'FOUNDATION_OUTSIDE_SITE',subject:f.id,site:[sw,sd]}); }); } }
/* ----------------------------------------------------------- التصريف --- */
function compileStructure(building,buildingId,position,rotationDeg,arch){
  const bid=buildingId||'bld_0';
  const raw=_sraw(building);
  const levels=_aLevels(building,bid);
  const levelsIdx=_sLevelsIndex(building,bid);
  if(arch===undefined||arch===null){
    try{ arch=compileArchitecture(building,bid,position,rotationDeg); }catch(e){ arch=null; } }
  const issues=[];
  const knownKeys=['status','synthetic','meta','grid_systems','grids','materials','nodes',
    'columns','beams','slabs','walls','cores','foundations',
    'layer_visibility','visible_layers'];
  Object.keys(raw).sort(_scmp).forEach(k=>{
    if(knownKeys.indexOf(k)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:k,
        detail:'this collection is not part of the structural schema and was NOT interpreted'}); });
  const materials=_sMaterials(raw,bid);
  const gridSystems=_sGrids(raw,bid);
  const gridIdx=_sGridIndex(gridSystems);
  const nodes=_sNodes(raw,bid,levelsIdx);
  const nodeIdx=new Map(); nodes.forEach(nd=>nodeIdx.set(nd.id,nd));
  const cols=_sColumns(raw,bid,levelsIdx,gridIdx);
  const beams=_sBeams(raw,bid,levelsIdx,nodeIdx,gridIdx);
  const slabs=_sSlabs(raw,bid,levelsIdx);
  const walls=_sWalls(raw,bid,levelsIdx);
  const cores=_sCores(raw,bid,levelsIdx);
  const fnds=_sFoundations(raw,bid);
  const counted=cols.length+beams.length+slabs.length+walls.length+cores.length+fnds.length
    +nodes.length+gridSystems.reduce((s,g)=>s+g.grids.length,0);
  const declared=String(_pyT(raw.status)?raw.status:'').toUpperCase();
  let status;
  if(STRUCT_MODEL_STATUS.indexOf(declared)>=0) status=declared;
  else if(counted===0) status='NOT_DEFINED';
  else {
    const verified=cols.concat(beams).concat(slabs).concat(walls).concat(cores).concat(fnds)
      .every(e=>STRUCT_VERIFIED_SOURCES.indexOf(e.source)>=0);
    status=verified?'REPRESENTED':'PARTIAL'; }
  const out={schema:STRUCT_SCHEMA, compiler_version:STRUCT_COMPILER_VERSION, building_id:bid,
    status:status,
    status_basis:(STRUCT_MODEL_STATUS.indexOf(declared)>=0)?'declared_by_model'
      :((counted===0)?'no structural element is present':'derived from element provenance'),
    synthetic:raw.synthetic===true, regulatory:false,
    transform:{position:position||{x:0.0,z:0.0}, rotation_deg:Number(rotationDeg||0.0),
      applied:'local coordinates; world transform is applied on read'},
    levels:levels.map(l=>({id:l.id,index:l.index,elevation_m:l.elevation_m,
      elevation_source:l.elevation_source})),
    grid_systems:gridSystems, materials:materials, nodes:nodes,
    columns:cols, beams:beams, slabs:slabs, walls:walls, cores:cores, foundations:fnds,
    relationships:[], issues:[],
    meta:{note:ACS_STRUCT_SPEC.note, elements:counted,
      levels_source:'architectural level table',
      load_path:'not derived — geometric connectivity only',
      navigation_impact:'none — structural members are not navigation obstacles in this phase'}};
  const stackRels=_sStacks(cols,issues);
  out.relationships=_sRelationships(bid,cols,beams,slabs,walls,cores,fnds,stackRels,arch,issues);
  _sInterference(cols,beams,fnds,arch,building,issues);
  structColumnsInside(out,arch).forEach(i=>{ delete i.severity; issues.push(i); });
  validateStructure(out).forEach(i=>issues.push(i));
  issues.forEach(i=>{ i.severity=structSeverityOf(i.code); });
  const dec=issues.map((it,i)=>({it:it,i:i}));
  dec.sort((a,b)=>{
    const sa=STRUCT_SEVERITIES.indexOf(a.it.severity)*-1;
    const sb=STRUCT_SEVERITIES.indexOf(b.it.severity)*-1;
    if(sa!==sb) return sa-sb;
    const c=_scmp(String(a.it.code),String(b.it.code));
    if(c!==0) return c;
    const d=_scmp(String(a.it.subject),String(b.it.subject));
    return d!==0?d:(a.i-b.i); });
  out.issues=dec.map(d=>d.it);
  return out; }
/* ------------------------------------------------------------ التحقّق --- */
/* فحوص سلامة نموذج — ليست فحوص كود إنشائي إطلاقاً */
function validateStructure(struct){
  const issues=[], bid=struct.building_id;
  const groups=['nodes','columns','beams','slabs','walls','cores','foundations','materials'];
  const seen=new Map();
  groups.forEach(key=>(struct[key]||[]).forEach(e=>{
    if(seen.has(e.id)) issues.push({code:'DUPLICATE_ELEMENT_ID',subject:e.id,other:seen.get(e.id)});
    seen.set(e.id,key);
    if(STRUCT_ELEMENT_TYPES.indexOf(e.type)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:e.id,declared:e.type});
    if(bid&&String(e.id).indexOf(String(bid)+'.')!==0)
      issues.push({code:'CROSS_BUILDING_REF',subject:e.id}); }));
  (struct.grid_systems||[]).forEach(gs=>gs.grids.forEach(g=>{
    if(seen.has(g.id)) issues.push({code:'DUPLICATE_ELEMENT_ID',subject:g.id,other:seen.get(g.id)});
    seen.set(g.id,'grids'); }));
  const matIds=new Set((struct.materials||[]).map(m=>m.id));
  ['columns','beams','slabs','walls','cores','foundations'].forEach(key=>
    (struct[key]||[]).forEach(e=>{
      const ref=e.material_ref;
      if(ref===null||ref===undefined) issues.push({code:'MATERIAL_UNKNOWN',subject:e.id});
      else if(!matIds.has(_snid(bid,ref,'mat',0))&&!matIds.has(String(ref)))
        issues.push({code:'INVALID_MATERIAL_REF',subject:e.id,ref:ref}); }));
  (struct.nodes||[]).forEach(n=>{
    if(_sBadNumber(n.raw_x)||_sBadNumber(n.raw_z)||n.x===null||n.z===null)
      issues.push({code:'NAN_COORDINATE',subject:n.id});
    if(!n.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:n.id,ref:n.level_ref}); });
  const archLevels=new Set((struct.levels||[]).map(l=>l.index));
  (struct.columns||[]).forEach(c=>{
    if(_sBadNumber(c.raw_x)||_sBadNumber(c.raw_z)||c.x===null||c.z===null)
      issues.push({code:'NAN_COORDINATE',subject:c.id});
    if(!c.levels_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:c.id,
      base:c.base_level_ref,top:c.top_level_ref});
    if(c.height_m!==null&&Math.abs(c.height_m)<=_S_EPS)
      issues.push({code:'COLUMN_ZERO_HEIGHT',subject:c.id});
    else if(c.height_m!==null&&c.height_m<0)
      issues.push({code:'NEGATIVE_DIMENSION',subject:c.id,field:'height_m'});
    if(c.declared_height_m!==null&&c.height_m!==null&&
       Math.abs(c.declared_height_m-c.height_m)>1e-3)
      issues.push({code:'COLUMN_HEIGHT_MISMATCH',subject:c.id,
        declared:c.declared_height_m,from_levels:c.height_m});
    if(c.section===null) issues.push({code:'SECTION_UNKNOWN',subject:c.id});
    else ['width_m','depth_m','diameter_m'].forEach(f=>{
      if(c.section[f]!==null&&c.section[f]!==undefined&&c.section[f]<=0)
        issues.push({code:'NEGATIVE_DIMENSION',subject:c.id,field:f}); });
    c.unresolved_grid_refs.forEach(r=>issues.push({code:'INVALID_GRID_REF',subject:c.id,ref:r}));
    if(c.base_level_index!==null&&c.base_level_index!==undefined&&!archLevels.has(c.base_level_index))
      issues.push({code:'INVALID_LEVEL_REF',subject:c.id,base:c.base_level_index}); });
  (struct.beams||[]).forEach(b=>{
    [b.start,b.end].forEach(end=>{
      if(end.basis==='unknown_node'){
        issues.push({code:'INVALID_NODE_REF',subject:b.id,ref:end.ref});
        issues.push({code:'BEAM_ENDPOINT_UNRESOLVED',subject:b.id,ref:end.ref}); }
      else if(end.basis==='unresolved')
        issues.push({code:'BEAM_ENDPOINT_UNRESOLVED',subject:b.id,ref:end.ref});
      else if(end.node_id===null&&end.basis==='stated_point')
        issues.push({code:'BEAM_FLOATING',subject:b.id,
          detail:'endpoint is a bare point with no structural node'}); });
    if(!b.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:b.id,ref:b.level_ref});
    if(b.length_m!==null&&b.length_m<=_S_EPS)
      issues.push({code:'MEMBER_ZERO_LENGTH',subject:b.id});
    if(b.section===null) issues.push({code:'SECTION_UNKNOWN',subject:b.id});
    else ['width_m','depth_m','diameter_m'].forEach(f=>{
      if(b.section[f]!==null&&b.section[f]!==undefined&&b.section[f]<=0)
        issues.push({code:'NEGATIVE_DIMENSION',subject:b.id,field:f}); });
    b.unresolved_grid_refs.forEach(r=>issues.push({code:'INVALID_GRID_REF',subject:b.id,ref:r})); });
  (struct.slabs||[]).forEach(s=>{
    if(!s.level_resolved) issues.push({code:'SLAB_LEVEL_UNRESOLVED',subject:s.id,ref:s.level_ref});
    if(s.thickness_m.value!==null&&s.thickness_m.value<=0)
      issues.push({code:'NEGATIVE_DIMENSION',subject:s.id,field:'thickness_m'}); });
  (struct.walls||[]).forEach(w=>{
    if(!w.levels_resolved) issues.push({code:'WALL_LEVELS_UNRESOLVED',subject:w.id,
      refs:w.level_refs});
    if(w.length_m!==null&&w.length_m<=_S_EPS)
      issues.push({code:'MEMBER_ZERO_LENGTH',subject:w.id});
    if(w.thickness_m.value!==null&&w.thickness_m.value<=0)
      issues.push({code:'NEGATIVE_DIMENSION',subject:w.id,field:'thickness_m'}); });
  (struct.cores||[]).forEach(c=>{
    if(!c.levels_resolved) issues.push({code:'CORE_LEVELS_UNRESOLVED',subject:c.id,
      refs:c.level_refs}); });
  (struct.foundations||[]).forEach(f=>{
    if(_sBadNumber(f.raw_x)||_sBadNumber(f.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:f.id});
    ['width_m','depth_m','thickness_m','embedment_m'].forEach(key=>{
      if(f[key].value!==null&&f[key].value<=0)
        issues.push({code:'NEGATIVE_DIMENSION',subject:f.id,field:key}); }); });
  return issues; }
/* عمود خارج مسطح المبنى — واقعة هندسية تُبلَّغ ولا تُصحَّح */
function structColumnsInside(struct,arch){
  const out=[];
  if(!arch) return out;
  const boxes=new Map();
  (arch.spaces||[]).forEach(s=>{
    const rc=s.rect;
    if(!rc) return;
    const li=s.level_index, r=[rc[0],rc[1],rc[0]+rc[2],rc[1]+rc[3]];
    const b=boxes.get(li);
    boxes.set(li, b===undefined?r:[Math.min(b[0],r[0]),Math.min(b[1],r[1]),
      Math.max(b[2],r[2]),Math.max(b[3],r[3])]); });
  (struct.columns||[]).forEach(c=>{
    const b=boxes.get(c.base_level_index);
    if(b===undefined||c.x===null) return;
    if(!(b[0]-0.5<=c.x&&c.x<=b[2]+0.5&&b[1]-0.5<=c.z&&c.z<=b[3]+0.5))
      out.push({code:'COLUMN_OUTSIDE_BUILDING',subject:c.id,
        severity:structSeverityOf('COLUMN_OUTSIDE_BUILDING'),footprint:b}); });
  return out; }
/* ------------------------------------------------------- بيانات الرسم --- */
/* هندسة عرض فقط. كل عنصر يعلن هل أبعاده من النموذج أم احتياط عرض */
function structRenderItems(struct){
  const items=[];
  (struct.columns||[]).forEach(c=>{
    if(c.x===null||c.base_elevation_m===null||c.height_m===null) return;
    const rs=c.render_section;
    items.push({name:'STRUCT|COLUMN|'+c.id, kind:'COLUMN', id:c.id,
      cx:c.x, cy:c.base_elevation_m+c.height_m/2.0, cz:c.z,
      ex:rs.w, ey:Math.abs(c.height_m), ez:rs.d,
      geometry_source:rs.source, material_ref:c.material_ref, element_source:c.source}); });
  (struct.beams||[]).forEach(b=>{
    if(b.start.x===null||b.end.x===null||b.elevation_m===null||!b.length_m) return;
    const rs=b.render_section;
    const mx=(b.start.x+b.end.x)/2.0, mz=(b.start.z+b.end.z)/2.0;
    const dx=b.end.x-b.start.x, dz=b.end.z-b.start.z;
    items.push({name:'STRUCT|BEAM|'+b.id, kind:'BEAM', id:b.id,
      cx:mx, cy:b.elevation_m-rs.d/2.0, cz:mz,
      ex:b.length_m, ey:rs.d, ez:rs.w, rot_y:Math.atan2(-dz,dx),
      geometry_source:rs.source, material_ref:b.material_ref, element_source:b.source}); });
  (struct.slabs||[]).forEach(s=>{
    const o=s.outline;
    if(!o||s.elevation_m===null) return;
    let t=s.thickness_m.value;
    const src=(t!==null)?'model':'display_fallback';
    if(t===null) t=s.thickness_m.render_fallback;
    items.push({name:'STRUCT|SLAB|'+s.id, kind:'STRUCTURAL_SLAB', id:s.id,
      cx:o[0]+o[2]/2.0, cy:s.elevation_m-t/2.0, cz:o[1]+o[3]/2.0,
      ex:o[2], ey:t, ez:o[3],
      geometry_source:src, material_ref:s.material_ref, element_source:s.source}); });
  const lvIdx=new Map((struct.levels||[]).map(l=>[l.index,l]));
  (struct.walls||[]).forEach(w=>{
    if(w.start.x===null||w.end.x===null||!w.length_m||!w.level_indexes.length) return;
    let t=w.thickness_m.value;
    const src=(t!==null)?'model':'display_fallback';
    if(t===null) t=w.thickness_m.render_fallback;
    const lo=lvIdx.get(Math.min.apply(null,w.level_indexes));
    const hi=lvIdx.get(Math.max.apply(null,w.level_indexes));
    const base=lo?lo.elevation_m:null, topl=hi?hi.elevation_m:null;
    if(base===null||topl===null||base===undefined||topl===undefined) return;
    const h=Math.max(topl-base,0.0);
    if(h<=_S_EPS) return;
    const dx=w.end.x-w.start.x, dz=w.end.z-w.start.z;
    items.push({name:'STRUCT|WALL|'+w.id, kind:'STRUCTURAL_WALL', id:w.id,
      cx:(w.start.x+w.end.x)/2.0, cy:base+h/2.0, cz:(w.start.z+w.end.z)/2.0,
      ex:w.length_m, ey:h, ez:t, rot_y:Math.atan2(-dz,dx),
      geometry_source:src, material_ref:w.material_ref, element_source:w.source}); });
  (struct.cores||[]).forEach(c=>{
    const o=c.outline;
    if(!o||!c.level_indexes.length) return;
    const lo=lvIdx.get(Math.min.apply(null,c.level_indexes));
    const hi=lvIdx.get(Math.max.apply(null,c.level_indexes));
    const base=lo?lo.elevation_m:null, topl=hi?hi.elevation_m:null;
    if(base===null||topl===null||base===undefined||topl===undefined||topl-base<=_S_EPS) return;
    items.push({name:'STRUCT|CORE|'+c.id, kind:'STRUCTURAL_CORE', id:c.id,
      cx:o[0]+o[2]/2.0, cy:base+(topl-base)/2.0, cz:o[1]+o[3]/2.0,
      ex:o[2], ey:topl-base, ez:o[3],
      geometry_source:'model', material_ref:c.material_ref, element_source:c.source}); });
  (struct.foundations||[]).forEach(f=>{
    if(f.x===null) return;
    let w=f.width_m.value, d=f.depth_m.value, t=f.thickness_m.value;
    let src=(w!==null&&d!==null&&t!==null)?'model':'display_fallback';
    if(w===null) w=f.width_m.render_fallback;
    if(d===null) d=f.depth_m.render_fallback;
    if(t===null) t=f.thickness_m.render_fallback;
    let top=f.top_elevation_m, topSrc='model';
    if(top===null){
      top=-((f.embedment_m.value!==null)?f.embedment_m.value:f.embedment_m.render_fallback);
      topSrc='display_fallback'; }
    let cx=f.x, cz=f.z;
    if(f.outline){ const o=f.outline;
      cx=o[0]+o[2]/2.0; cz=o[1]+o[3]/2.0; w=o[2]; d=o[3]; src='model'; }
    items.push({name:'STRUCT|FOUNDATION|'+f.id, kind:'FOUNDATION', id:f.id,
      cx:cx, cy:top-t/2.0, cz:cz, ex:w, ey:t, ez:d,
      geometry_source:(topSrc==='model')?src:'display_fallback',
      material_ref:f.material_ref, element_source:f.source}); });
  (struct.grid_systems||[]).forEach(gs=>gs.grids.forEach(g=>{
    if(g.position_m===null) return;
    items.push({name:'STRUCT|GRID|'+g.id, kind:'GRID_LINE', id:g.id,
      axis:g.axis, position_m:g.position_m, origin:gs.origin, rotation_deg:gs.rotation_deg,
      label:g.label, geometry_source:'model', element_source:g.source}); }));
  items.sort((a,b)=>_scmp(String(a.name),String(b.name)));
  return items; }
/* --------------------------------------------------------- اقتراحات --- */
/* اقتراح شبكة مفاهيمية — ليس تصميماً إنشائياً ولا يُكتب في النموذج */
function suggestStructuralGrid(building,spacingX,spacingZ,buildingId,basis){
  buildingId=buildingId||'bld_0';
  basis=basis||'explicitly requested spacing';
  if((spacingX===null||spacingX===undefined)&&(spacingZ===null||spacingZ===undefined))
    return {kind:'SUGGESTION',applied:false,persisted:false,reason:'NO_SPACING_SUPPLIED',
      detail:'a grid is not invented; a spacing must be supplied explicitly'};
  let arch=null;
  try{ arch=compileArchitecture(building,buildingId); }catch(e){ arch=null; }
  const rects=((arch||{}).spaces||[]).filter(s=>s.rect).map(s=>s.rect);
  if(!rects.length)
    return {kind:'SUGGESTION',applied:false,persisted:false,reason:'NO_FOOTPRINT',
      detail:'no architectural footprint is available to lay a grid over'};
  const bb=[Math.min.apply(null,rects.map(r=>r[0])),Math.min.apply(null,rects.map(r=>r[1])),
            Math.max.apply(null,rects.map(r=>r[0]+r[2])),Math.max.apply(null,rects.map(r=>r[1]+r[3]))];
  const lines=[];
  const lay=(axis,lo,hi,step,labels)=>{
    if(step===null||step===undefined||step<=0) return;
    let n=0, p=lo;
    while(p<=hi+_S_EPS){
      const lab=labels(n);
      lines.push({id:buildingId+'.grid_'+axis.toLowerCase()+'_'+lab,type:'GRID_LINE',
        building_id:buildingId,axis:axis,label:lab,position_m:_pyRound(p,6),
        position_stated:false,source:'system_suggested'});
      n+=1; p=lo+n*step; } };
  lay('X',bb[0],bb[2],_snum(spacingX),
      i=>String.fromCharCode(65+(i%26))+((i<26)?'':String(Math.floor(i/26))));
  lay('Z',bb[1],bb[3],_snum(spacingZ),i=>String(i+1));
  return {kind:'SUGGESTION',applied:false,persisted:false,source:'system_suggested',basis:basis,
    footprint:bb,spacing_x_m:_snum(spacingX),spacing_z_m:_snum(spacingZ),
    grid_system:{id:buildingId+'.gs_suggested',type:'GRID_SYSTEM',building_id:buildingId,
      label:'suggested',origin:{x:0.0,z:0.0},rotation_deg:0.0,rotation_stated:false,
      source:'system_suggested',grids:lines},
    note:'a suggested grid is a proposal, not structural design and not model truth; '+
         'nothing is written into the model'}; }
/* ------------------------------------------------------------- خدمات --- */
function structElementById(struct,eid){
  const keys=['columns','beams','slabs','walls','cores','foundations','nodes','materials',
              'grid_systems'];
  for(const key of keys)
    for(const el of (struct[key]||[])){
      if(el.id===eid) return el;
      if(key==='grid_systems') for(const g of (el.grids||[])) if(g.id===eid) return g; }
  for(const r of (struct.relationships||[])) if(r.id===eid) return r;
  return null; }
function structToWorld(struct,x,z){
  const t=struct.transform||{};
  const rot=(Number(t.rotation_deg||0.0))*Math.PI/180;
  const px=Number((t.position||{}).x||0.0), pz=Number((t.position||{}).z||0.0);
  const ca=Math.cos(rot), sa=Math.sin(rot);
  return [px+x*ca-z*sa, pz+x*sa+z*ca]; }
/* خطّ محور في الإحداثيات العامة — يحترم دوران الشبكة ودوران المبنى معاً */
function structGridToWorld(struct,gridSystem,gridLine,span){
  span=(span===undefined||span===null)?100.0:span;
  if(gridLine.position_m===null||gridLine.position_m===undefined) return null;
  const o=gridSystem.origin||{x:0.0,z:0.0};
  const rot=(Number(gridSystem.rotation_deg||0.0))*Math.PI/180;
  const ca=Math.cos(rot), sa=Math.sin(rot);
  const p=Number(gridLine.position_m);
  const seg=(gridLine.axis==='X')?[[p,-span],[p,span]]:[[-span,p],[span,p]];
  return seg.map(q=>{
    const gx=o.x+q[0]*ca-q[1]*sa, gz=o.z+q[0]*sa+q[1]*ca;
    return structToWorld(struct,gx,gz); }); }
/* حقائق إنشائية معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية هنا */
function structRuleInputs(struct){
  const out={};
  (struct.columns||[]).forEach(c=>{ const sec=c.section||{};
    out[c.id]={'structural.column.section_shape':(sec.shape===undefined)?null:sec.shape,
      'structural.column.section_width':(sec.width_m===undefined)?null:sec.width_m,
      'structural.column.section_depth':(sec.depth_m===undefined)?null:sec.depth_m,
      'structural.column.section_diameter':(sec.diameter_m===undefined)?null:sec.diameter_m,
      'structural.member.material':_sMaterialName(struct,c.material_ref),
      'structural.column.height_m':c.height_m,
      'structural.member.source':c.source}; });
  (struct.beams||[]).forEach(b=>{ const sec=b.section||{};
    out[b.id]={'structural.beam.section_width':(sec.width_m===undefined)?null:sec.width_m,
      'structural.beam.section_depth':(sec.depth_m===undefined)?null:sec.depth_m,
      'structural.beam.length_m':b.length_m,
      'structural.member.material':_sMaterialName(struct,b.material_ref),
      'structural.member.source':b.source}; });
  (struct.foundations||[]).forEach(f=>{
    out[f.id]={'structural.foundation.type':f.foundation_type,
      'structural.member.material':_sMaterialName(struct,f.material_ref),
      'structural.member.source':f.source}; });
  return out; }
function _sMaterialName(struct,ref){
  if(ref===null||ref===undefined) return null;
  const bid=struct.building_id;
  for(const m of (struct.materials||[]))
    if(m.id===ref||m.id===_snid(bid,ref,'mat',0)) return m.material;
  return null; }
function structSummary(struct){
  const iss=struct.issues||[], cols=struct.columns||[];
  const st=c=>(c.stack||{}).state;
  return {building_id:struct.building_id, compiler_version:struct.compiler_version,
    status:struct.status, synthetic:struct.synthetic===true, regulatory:false,
    grid_systems:(struct.grid_systems||[]).length,
    grid_lines:(struct.grid_systems||[]).reduce((s,g)=>s+g.grids.length,0),
    materials:(struct.materials||[]).length, nodes:(struct.nodes||[]).length,
    columns:cols.length, beams:(struct.beams||[]).length,
    slabs:(struct.slabs||[]).length, walls:(struct.walls||[]).length,
    cores:(struct.cores||[]).length, foundations:(struct.foundations||[]).length,
    relationships:(struct.relationships||[]).length,
    columns_with_section:cols.filter(c=>_pyT(c.section)).length,
    columns_aligned:cols.filter(c=>st(c)==='aligned').length,
    columns_offset:cols.filter(c=>st(c)==='offset').length,
    columns_unresolved:cols.filter(c=>st(c)==='unresolved').length,
    issues:iss.length,
    errors:iss.filter(i=>i.severity==='ERROR').length,
    warnings:iss.filter(i=>i.severity==='WARNING').length,
    infos:iss.filter(i=>i.severity==='INFO').length,
    note:'structural representation only — no design, no load calculation, '+
         'no sizing, no code compliance'}; }
/* ==================================================================
   المرحلة 2 — أساس نموذج أنظمة الكهروميكانيك (نسخة مطابقة لـ acs_mep.py).
   تمثيل فقط: لا تصميم ولا حساب أحمال/تدفّق/ضغط ولا تحجيم ولا مطابقة كود •
   النظام لا يُستنتج من نوع المبنى • احتياط العرض ليس قيمة هندسية •
   وجود نهاية في فراغ ليس كفاية خدمة • التعارض يُبلَّغ ولا يُصحَّح.
   ================================================================== */
const ACS_MEP_SPEC = {
 "schema": "acs.mep/1",
 "compiler_version": "acs-mep-compiler/1.0.0",
 "note": "MEP REPRESENTATION ONLY. This layer stores and normalises MEP systems, networks, equipment and terminals that were supplied to it. It performs NO MEP design and NO calculation of any kind: no electrical load, voltage drop, short-circuit, cable, breaker or transformer sizing; no lighting level; no cooling, heating or airflow calculation and no duct sizing, static pressure or psychrometrics; no fixture units, water demand, pipe or drainage sizing, pump head; no sprinkler hydraulics, fire-water demand or fire-alarm design. Nothing here may be read as evidence that any system is adequate, balanced, calculated or compliant.",
 "fire_note": "Fire-protection content in this layer is DATA REPRESENTATION ONLY. There is no Fire / Life-Safety engine: coverage, spacing, device quantity, hydraulics, alarm zoning and code compliance are all out of scope and are never evaluated.",
 "element_types": [
  "MEP_SYSTEM",
  "MEP_NODE",
  "MEP_SEGMENT",
  "MEP_EQUIPMENT",
  "MEP_TERMINAL",
  "MEP_RISER",
  "MEP_PENETRATION"
 ],
 "model_status": [
  "NOT_DEFINED",
  "PARTIAL",
  "REPRESENTED",
  "IMPORTED",
  "VERIFIED_DATA"
 ],
 "status_note": "DESIGNED / COMPLIANT / ADEQUATE / BALANCED / CALCULATED are deliberately absent. No engine in this platform can justify them.",
 "provenance_values": [
  "user",
  "imported",
  "ai_inference",
  "system_suggested",
  "system_default",
  "manual_verified",
  "test_fixture",
  "display_fallback",
  "phase1_adapter",
  "unknown"
 ],
 "provenance_note": "system_default and display_fallback can never become verified engineering data. phase1_adapter marks a terminal derived from an existing Phase 1 point; the adapter carries the original provenance through unchanged and can never raise it. rule and code_required are intentionally NOT provenance values here because no verified MEP rule evidence exists.",
 "verified_sources": [
  "user",
  "imported",
  "manual_verified"
 ],
 "system_types": [
  "ELECTRICAL_POWER",
  "LIGHTING",
  "EMERGENCY_POWER",
  "LOW_CURRENT",
  "DATA_NETWORK",
  "SECURITY",
  "DOMESTIC_COLD_WATER",
  "DOMESTIC_HOT_WATER",
  "HOT_WATER_RECIRCULATION",
  "SANITARY_DRAINAGE",
  "STORM_DRAINAGE",
  "VENT_DRAINAGE",
  "HVAC_SUPPLY",
  "HVAC_RETURN",
  "HVAC_EXHAUST",
  "HVAC_FRESH_AIR",
  "REFRIGERANT",
  "CHILLED_WATER",
  "HEATING_WATER",
  "GAS",
  "MEDICAL_GAS",
  "FIRE_WATER",
  "SPRINKLER",
  "FIRE_ALARM",
  "OTHER"
 ],
 "system_note": "no system is ever instantiated automatically. A villa does not get a sprinkler system, a hotel does not get emergency power and a warehouse does not get fire-water infrastructure because of what it is. A system exists only because the model states it.",
 "system_disciplines": {
  "ELECTRICAL_POWER": "ELECTRICAL",
  "LIGHTING": "LIGHTING",
  "EMERGENCY_POWER": "ELECTRICAL",
  "LOW_CURRENT": "ICT",
  "DATA_NETWORK": "ICT",
  "SECURITY": "ICT",
  "DOMESTIC_COLD_WATER": "PLUMBING",
  "DOMESTIC_HOT_WATER": "PLUMBING",
  "HOT_WATER_RECIRCULATION": "PLUMBING",
  "SANITARY_DRAINAGE": "DRAINAGE",
  "STORM_DRAINAGE": "DRAINAGE",
  "VENT_DRAINAGE": "DRAINAGE",
  "HVAC_SUPPLY": "HVAC",
  "HVAC_RETURN": "HVAC",
  "HVAC_EXHAUST": "HVAC",
  "HVAC_FRESH_AIR": "HVAC",
  "REFRIGERANT": "HVAC",
  "CHILLED_WATER": "HVAC",
  "HEATING_WATER": "HVAC",
  "GAS": "PLUMBING",
  "MEDICAL_GAS": "PLUMBING",
  "FIRE_WATER": "FIRE",
  "SPRINKLER": "FIRE",
  "FIRE_ALARM": "FIRE",
  "OTHER": "OTHER"
 },
 "disciplines": [
  "ELECTRICAL",
  "LIGHTING",
  "ICT",
  "PLUMBING",
  "DRAINAGE",
  "HVAC",
  "FIRE",
  "OTHER"
 ],
 "media": [
  "electricity",
  "air",
  "water",
  "wastewater",
  "refrigerant",
  "gas",
  "data",
  "signal",
  "fire_water",
  "unknown"
 ],
 "medium_note": "a medium is a factual label. It attaches no pressure, temperature, flow, velocity or performance assumption of any kind.",
 "node_kinds": [
  "source",
  "junction",
  "equipment_connection",
  "terminal",
  "distribution_point",
  "riser_connection",
  "other"
 ],
 "segment_kinds": [
  "duct",
  "pipe",
  "conduit",
  "cable_tray",
  "cable",
  "busway",
  "other"
 ],
 "routing_statuses": [
  "UNROUTED",
  "ROUTED",
  "PARTIAL",
  "IMPORTED",
  "UNRESOLVED"
 ],
 "routing_note": "OPTIMIZED is deliberately absent: no routing optimisation exists. A segment with endpoints but no supplied geometry stays UNROUTED — a path is never fabricated to connect them.",
 "equipment_types": [
  "panel",
  "distribution_board",
  "switchboard",
  "transformer",
  "generator",
  "ups",
  "isolator",
  "ahu",
  "fcu",
  "vav",
  "fan",
  "chiller",
  "boiler",
  "heat_pump",
  "split_unit",
  "pump",
  "water_heater",
  "tank",
  "water_meter",
  "fire_pump",
  "rack",
  "other"
 ],
 "terminal_types": [
  "socket",
  "switch",
  "light_fixture",
  "data_outlet",
  "tv_outlet",
  "sensor",
  "thermostat",
  "equipment_connection",
  "appliance_connection",
  "diffuser",
  "grille",
  "wc",
  "lavatory",
  "shower",
  "sink",
  "urinal",
  "floor_drain",
  "hose_bib",
  "sprinkler_head",
  "smoke_detector",
  "heat_detector",
  "manual_call_point",
  "fire_alarm_device",
  "fire_hose_reel",
  "hydrant",
  "cctv",
  "wifi_ap",
  "access_control",
  "intercom",
  "bms_point",
  "other"
 ],
 "port_types": [
  "electrical",
  "water",
  "drainage",
  "air",
  "data",
  "control",
  "gas",
  "refrigerant"
 ],
 "riser_kinds": [
  "electrical_riser",
  "plumbing_riser",
  "drainage_stack",
  "duct_riser",
  "data_riser",
  "fire_riser",
  "other"
 ],
 "penetration_host_types": [
  "ARCH_WALL",
  "ARCH_SLAB",
  "STRUCT_BEAM",
  "STRUCT_COLUMN",
  "STRUCT_SLAB",
  "STRUCT_WALL",
  "OTHER"
 ],
 "penetration_note": "a penetration records that the model states an opening exists where a segment passes through a host. It implies nothing about fire stopping, sleeves, sealing or reinforcement — those are future layers and are never inferred here.",
 "relationship_types": [
  "SEGMENT_CONNECTS",
  "EQUIPMENT_CONNECTED_TO",
  "TERMINAL_CONNECTED_TO",
  "RISER_CONNECTS_LEVELS",
  "RISER_IN_SHAFT",
  "SYSTEM_SERVES_SPACE",
  "SYSTEM_HAS_TERMINAL_IN",
  "PANEL_FEEDS",
  "CIRCUIT_FEEDS",
  "TERMINAL_ON_CIRCUIT",
  "PENETRATION_THROUGH"
 ],
 "relationship_statuses": [
  "confirmed",
  "inferred",
  "unresolved"
 ],
 "relationship_note": "these edges record model topology and factual location only. A terminal in a space means that space HAS A REPRESENTED TERMINAL — never that it receives adequate airflow, water, light or power. No edge here asserts service adequacy, and circuits are never grouped automatically.",
 "issue_severities": [
  "INFO",
  "WARNING",
  "ERROR"
 ],
 "severity_note": "these are model-quality severities. UNSAFE / CODE VIOLATION / FIRE VIOLATION are deliberately absent and are never justified by this layer.",
 "issue_codes": {
  "DUPLICATE_ELEMENT_ID": "ERROR",
  "UNSUPPORTED_ELEMENT_TYPE": "WARNING",
  "UNKNOWN_SYSTEM_TYPE": "WARNING",
  "UNKNOWN_MEDIUM": "WARNING",
  "UNKNOWN_EQUIPMENT_TYPE": "WARNING",
  "UNKNOWN_TERMINAL_TYPE": "WARNING",
  "UNKNOWN_SEGMENT_KIND": "WARNING",
  "INVALID_SYSTEM_REF": "ERROR",
  "INVALID_NODE_REF": "ERROR",
  "INVALID_EQUIPMENT_REF": "ERROR",
  "INVALID_LEVEL_REF": "ERROR",
  "INVALID_SPACE_REF": "ERROR",
  "INVALID_PORT_TYPE": "WARNING",
  "CROSS_BUILDING_REF": "ERROR",
  "NAN_COORDINATE": "ERROR",
  "NEGATIVE_DIMENSION": "ERROR",
  "SEGMENT_ZERO_LENGTH": "ERROR",
  "SEGMENT_ENDPOINT_UNRESOLVED": "ERROR",
  "SEGMENT_UNROUTED": "INFO",
  "ORPHAN_TERMINAL": "WARNING",
  "ORPHAN_NODE": "INFO",
  "SIZE_UNKNOWN": "INFO",
  "RISER_LEVELS_UNRESOLVED": "ERROR",
  "RISER_OUTSIDE_SHAFT": "WARNING",
  "PENETRATION_HOST_UNRESOLVED": "WARNING",
  "PENETRATION_SEGMENT_UNRESOLVED": "ERROR",
  "EQUIPMENT_OUTSIDE_SPACE": "WARNING",
  "TERMINAL_OUTSIDE_SPACE": "WARNING",
  "ROUTE_OUTSIDE_BUILDING": "WARNING",
  "MEP_ELEMENT_IN_FLOOR_OPENING": "INFO",
  "SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION": "WARNING",
  "SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION": "WARNING",
  "SEGMENT_CROSSES_STRUCTURAL_BEAM": "WARNING",
  "SEGMENT_CROSSES_STRUCTURAL_COLUMN": "WARNING",
  "SEGMENT_CROSSES_STRUCTURAL_SLAB": "WARNING"
 },
 "display_fallbacks": {
  "pipe_diameter_m": 0.05,
  "duct_width_m": 0.4,
  "duct_height_m": 0.25,
  "conduit_diameter_m": 0.025,
  "cable_tray_width_m": 0.3,
  "cable_tray_height_m": 0.1,
  "equipment_w_m": 0.6,
  "equipment_d_m": 0.4,
  "equipment_h_m": 0.9,
  "terminal_size_m": 0.15,
  "riser_w_m": 0.6,
  "riser_d_m": 0.6
 },
 "display_fallback_note": "DISPLAY VALUE IS NOT AN ENGINEERING VALUE. When a diameter, duct size, equipment envelope or terminal size is not supplied the semantic field stays null, the renderer reads these numbers instead tagged source=display_fallback, and the fallback is never written back into the model, never exported as engineering metadata and never reaches a rule input.",
 "forbidden_claims": [
  "adequate",
  "balanced",
  "calculated",
  "compliant",
  "code_required",
  "design_load",
  "connected_load",
  "demand_load",
  "voltage_drop",
  "short_circuit_current",
  "breaker_size",
  "cable_size",
  "lux",
  "illuminance",
  "cooling_load",
  "heating_load",
  "airflow_cfm",
  "airflow_ls",
  "static_pressure",
  "duct_velocity",
  "fixture_units",
  "water_demand",
  "pump_head",
  "sprinkler_density",
  "hydraulic_calculation",
  "fire_water_demand",
  "alarm_zone_verified",
  "meets_nfpa",
  "meets_nec",
  "meets_ashrae"
 ],
 "id_patterns": {
  "system": "<bid>.mep.sys_<n>",
  "node": "<bid>.mep.node_<n>",
  "segment": "<bid>.mep.seg_<n>",
  "equipment": "<bid>.mep.eq_<n>",
  "terminal": "<bid>.mep.term_<n>",
  "riser": "<bid>.mep.riser_<n>",
  "penetration": "<bid>.mep.pen_<n>",
  "relationship": "<bid>.mep.rel_<n>",
  "adapted_terminal": "<bid>.mep.p1_<space_id>_<point_index>"
 },
 "id_note": "an id supplied by the model is kept and namespaced with the building id; an id that is absent is generated from the element's canonical sort position, so the same model always yields the same ids. Two buildings can never collide, and site utility networks between buildings are out of scope in this phase.",
 "source_of_truth": "the MEP model lives alongside the architectural and structural models and never replaces or edits either. Levels come from the architectural level table and spaces from the architectural space table, so an MEP element cannot float on renderer-only coordinates. Architectural walls, slabs, shafts and cores are never reclassified as MEP elements, and structural members are never modified by a detected clash.",
 "axis_note": "MEP geometry uses the existing X / Y / Z metre convention in building-local coordinates, and the building transform (position + rotation) is applied on read exactly as in the architectural and structural layers. No second coordinate convention is introduced.",
 "navigation_note": "MEP elements are NOT navigation obstacles in this phase. Navigation, egress and walking-distance results are unchanged by the presence of an MEP model, deliberately and by design.",
 "no_generator_note": "this phase ships NO MEP generator, NO automatic circuiting, NO automatic routing and NO automatic system instantiation. Every system, route, equipment item and terminal exists only because the model supplied it, or because an existing Phase 1 point was adapted with its original provenance preserved.",
 "discipline_note": "disciplines double as the renderer debug layers. Lighting is separated from general power so the two can be shown independently; the separation is a display and organisation convenience and carries no engineering meaning."
};
const MEP_SCHEMA = ACS_MEP_SPEC.schema;
const MEP_COMPILER_VERSION = ACS_MEP_SPEC.compiler_version;
const MEP_ELEMENT_TYPES = ACS_MEP_SPEC.element_types;
const MEP_MODEL_STATUS = ACS_MEP_SPEC.model_status;
const MEP_PROVENANCE = ACS_MEP_SPEC.provenance_values;
const MEP_VERIFIED_SOURCES = ACS_MEP_SPEC.verified_sources;
const MEP_SYSTEM_TYPES = ACS_MEP_SPEC.system_types;
const MEP_DISCIPLINE_OF = ACS_MEP_SPEC.system_disciplines;
const MEP_DISCIPLINES = ACS_MEP_SPEC.disciplines;
const MEP_MEDIA = ACS_MEP_SPEC.media;
const MEP_NODE_KINDS = ACS_MEP_SPEC.node_kinds;
const MEP_SEGMENT_KINDS = ACS_MEP_SPEC.segment_kinds;
const MEP_ROUTING_STATUSES = ACS_MEP_SPEC.routing_statuses;
const MEP_EQUIPMENT_TYPES = ACS_MEP_SPEC.equipment_types;
const MEP_TERMINAL_TYPES = ACS_MEP_SPEC.terminal_types;
const MEP_PORT_TYPES = ACS_MEP_SPEC.port_types;
const MEP_RISER_KINDS = ACS_MEP_SPEC.riser_kinds;
const MEP_PENETRATION_HOSTS = ACS_MEP_SPEC.penetration_host_types;
const MEP_REL_TYPES = ACS_MEP_SPEC.relationship_types;
const MEP_REL_STATUSES = ACS_MEP_SPEC.relationship_statuses;
const MEP_SEVERITIES = ACS_MEP_SPEC.issue_severities;
const MEP_ISSUE_CODES = ACS_MEP_SPEC.issue_codes;
const MEP_FALLBACKS = ACS_MEP_SPEC.display_fallbacks;
const _M_EPS = 1e-6;
const _M_TOL = 0.15;
/* محوّل نقاط المرحلة 1 → نهايات ممثَّلة. الإسناد يُنقل كما هو ولا يُرقّى أبداً */
const _MEP_P1 = {outlet:['socket','ELECTRICAL_POWER'], switch:['switch','LIGHTING'],
  network:['data_outlet','DATA_NETWORK'], usb:['socket','ELECTRICAL_POWER'],
  tv:['tv_outlet','LOW_CURRENT'], ev:['equipment_connection','ELECTRICAL_POWER'],
  light:['light_fixture','LIGHTING'], spot:['light_fixture','LIGHTING'],
  ptl:['light_fixture','LIGHTING'], camera:['cctv','SECURITY'],
  ac:['equipment_connection','HVAC_SUPPLY'], vent:['grille','HVAC_EXHAUST'],
  smoke:['smoke_detector','FIRE_ALARM'], sprinkler:['sprinkler_head','SPRINKLER']};

function mepSeverityOf(code){
  return Object.prototype.hasOwnProperty.call(MEP_ISSUE_CODES,code)
    ?MEP_ISSUE_CODES[code]:'WARNING'; }
function _mnum(v){ return _snum(v); }
function _mBadNumber(v){ return _sBadNumber(v); }
function _msrc(v,dflt){
  const s=(v===null||v===undefined)?(dflt||'unknown'):String(v).toLowerCase();
  return MEP_PROVENANCE.indexOf(s)>=0?s:'unknown'; }
/* قيمة دلالية + احتياط عرض منفصل. الاحتياط ليس قيمة هندسية أبداً */
function _mfallback(value,key){
  const n=_mnum(value);
  if(n===null) return {value:null,render_fallback:MEP_FALLBACKS[key],
    source:'unknown',render_source:'display_fallback'};
  return {value:n,render_fallback:MEP_FALLBACKS[key],source:'imported',render_source:'model'}; }
/* خصائص اختيارية مذكورة صراحةً فقط — كل واحدة بمصدرها */
function _mPropMap(props,source){
  const out={};
  if(props&&typeof props==='object'&&!Array.isArray(props))
    Object.keys(props).sort(_scmp).forEach(k=>{
      out[String(k)]={value:props[k],source:_msrc(source,'imported')}; });
  return out; }
function _mraw(building){
  const m=building.mep;
  return (m&&typeof m==='object'&&!Array.isArray(m))?m:{}; }
function _mnid(bid,given,prefix,n){
  if(_pyT(given)){
    const s=String(given);
    if(s.indexOf(bid+'.')===0) return s;
    const head=s.split('.')[0];
    if(head.indexOf('bld_')===0&&head!==bid) return s;
    return bid+'.mep.'+s; }
  return bid+'.mep.'+prefix+'_'+n; }
function _mLevelsIndex(building,bid){
  const idx=new Map();
  _aLevels(building,bid).forEach(l=>{ idx.set('#'+l.index,l); idx.set('$'+String(l.id),l); });
  return idx; }
function _mLevelOf(idx,ref){
  if(ref===null||ref===undefined||typeof ref==='boolean') return null;
  if(typeof ref==='number') return idx.get('#'+Math.trunc(ref))||null;
  return idx.get('$'+String(ref))||null; }
function _mSpaceIndex(arch){
  const idx=new Map();
  ((arch||{}).spaces||[]).forEach(s=>{ idx.set(s.id,s);
    if(_pyT(s.space_id)&&!idx.has(s.space_id)) idx.set(s.space_id,s); });
  return idx; }
/* نقطة ثلاثية: {x,y,z} أو [x,y,z] أو [x,z]. الارتفاع الغائب يأخذ منسوب المستوى */
function _mPoint3(v,defaultY){
  let x=null,y=null,z=null;
  if(v&&typeof v==='object'&&!Array.isArray(v)){ x=_mnum(v.x); y=_mnum(v.y); z=_mnum(v.z); }
  else if(Array.isArray(v)&&v.length>=3){ x=_mnum(v[0]); y=_mnum(v[1]); z=_mnum(v[2]); }
  else if(Array.isArray(v)&&v.length===2){ x=_mnum(v[0]); y=null; z=_mnum(v[1]); }
  else return null;
  if(x===null||z===null) return null;
  return [x,(y===null)?((defaultY===undefined)?null:defaultY):y,z]; }
/* ------------------------------------------------------------- الأنظمة --- */
function _mSystems(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.systems)?raw.systems:[]).forEach((s,n)=>{
    const t=String(_pyT(s.type)?s.type:'OTHER').toUpperCase();
    const known=MEP_SYSTEM_TYPES.indexOf(t)>=0;
    const med=String(_pyT(s.medium)?s.medium:'unknown').toLowerCase();
    const medKnown=MEP_MEDIA.indexOf(med)>=0;
    const lv=(_pyT(s.serves_levels)?s.serves_levels:[]).map(r=>_mLevelOf(levelsIdx,r));
    out.push({id:_mnid(bid,s.id,'sys',n), type:'MEP_SYSTEM', building_id:bid,
      system_type:known?t:'OTHER', declared_type:(s.type===undefined)?null:s.type,
      system_type_recognised:known,
      discipline:MEP_DISCIPLINE_OF[known?t:'OTHER']||'OTHER',
      name:(s.name===undefined)?null:s.name,
      medium:medKnown?med:'unknown', declared_medium:(s.medium===undefined)?null:s.medium,
      medium_recognised:medKnown,
      serves_level_refs:(_pyT(s.serves_levels)?s.serves_levels:[]).slice(),
      serves_level_ids:lv.filter(Boolean).map(l=>l.id),
      levels_resolved:lv.every(l=>l!==null),
      metadata:_mPropMap(s.metadata,s.source),
      status:_pyT(s.status)?String(s.status).toUpperCase():null,
      source:_msrc(s.source),
      note:'represented MEP system — no capacity, adequacy or compliance is implied'}); });
  out.sort(_byId); return out; }
/* --------------------------------------------------------------- العقد --- */
function _mNodes(raw,bid,levelsIdx,spaceIdx,sysIds){
  const out=[];
  (_pyT(raw.nodes)?raw.nodes:[]).forEach((nd,n)=>{
    const lvl=_mLevelOf(levelsIdx,nd.level);
    const kind=String(_pyT(nd.kind)?nd.kind:'junction').toLowerCase();
    const pos=(nd.position&&typeof nd.position==='object'&&!Array.isArray(nd.position))
      ?nd.position:nd;
    let y=_mnum(pos.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    const sid=(nd.system_id===undefined)?null:nd.system_id;
    const sp=_pyT(nd.space)?nd.space:(_pyT(nd.space_id)?nd.space_id:null);
    out.push({id:_mnid(bid,nd.id,'node',n), type:'MEP_NODE', building_id:bid,
      system_id:sid,
      system_resolved:(sid===null||sid===undefined)||sysIds.has(_mnid(bid,sid,'sys',0)),
      kind:(MEP_NODE_KINDS.indexOf(kind)>=0)?kind:'other',
      declared_kind:(nd.kind===undefined)?null:nd.kind,
      x:_mnum(pos.x), y:y, z:_mnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      y_source:(_mnum(pos.y)!==null)?'imported':((lvl!==null)?'architectural_level':'unknown'),
      level_ref:(nd.level===undefined)?null:nd.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(nd.level===null||nd.level===undefined),
      space_ref:sp, space_id:sp?((spaceIdx.get(String(sp))||{}).id||null):null,
      space_resolved:(sp===null)||spaceIdx.has(String(sp)),
      source:_msrc(nd.source), note:'a node carries no capacity'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------- المقاطع --- */
/* مقاس معلن فقط. لا نختار قطراً ولا مقطع مجرى من أجل الرسم */
function _mSize(sz){
  if(!sz||typeof sz!=='object'||Array.isArray(sz)) return null;
  const pick=(a,b)=>_mnum((sz[a]!==null&&sz[a]!==undefined)?sz[a]:sz[b]);
  const out={diameter_m:pick('diameter_m','diameter'), width_m:pick('width_m','width'),
    height_m:pick('height_m','height'), source:_msrc(sz.source,'imported')};
  if(out.diameter_m===null&&out.width_m===null&&out.height_m===null) return null;
  return out; }
function _mRenderSize(size,kind){
  if(size&&size.diameter_m!==null&&size.diameter_m!==undefined){
    const d=size.diameter_m; return {w:d,h:d,source:'model'}; }
  if(size&&(size.width_m!==null||size.height_m!==null)){
    let w=size.width_m, h=size.height_m;
    if(w===null) w=h;
    if(h===null) h=w;
    return {w:w,h:h,source:'model'}; }
  if(kind==='duct') return {w:MEP_FALLBACKS.duct_width_m,h:MEP_FALLBACKS.duct_height_m,
    source:'display_fallback'};
  if(kind==='conduit') return {w:MEP_FALLBACKS.conduit_diameter_m,
    h:MEP_FALLBACKS.conduit_diameter_m,source:'display_fallback'};
  if(kind==='cable_tray') return {w:MEP_FALLBACKS.cable_tray_width_m,
    h:MEP_FALLBACKS.cable_tray_height_m,source:'display_fallback'};
  return {w:MEP_FALLBACKS.pipe_diameter_m,h:MEP_FALLBACKS.pipe_diameter_m,
    source:'display_fallback'}; }
function _mPolyline(v,defaultY){
  if(!Array.isArray(v)||v.length<2) return null;
  const pts=[];
  for(const p of v){ const q=_mPoint3(p,defaultY); if(q===null) return null; pts.push(q); }
  return pts; }
function _mSegments(raw,bid,levelsIdx,nodeIdx,sysIds){
  const out=[];
  (_pyT(raw.segments)?raw.segments:[]).forEach((s,n)=>{
    const lvl=_mLevelOf(levelsIdx,s.level);
    const baseY=lvl?lvl.elevation_m:null;
    const kind=String(_pyT(s.kind)?s.kind:'other').toLowerCase();
    const ends=[];
    ['from_node','to_node'].forEach(key=>{
      const alt=key.split('_')[0];
      const ref=(s[key]!==null&&s[key]!==undefined)?s[key]
                :((s[alt]===undefined)?null:s[alt]);
      const node=_pyT(ref)?(nodeIdx.get(String(ref))||nodeIdx.get(_mnid(bid,ref,'node',0))||null)
                          :null;
      if(node) ends.push({ref:ref,node_id:node.id,x:node.x,y:node.y,z:node.z,basis:'mep_node'});
      else ends.push({ref:ref,node_id:null,x:null,y:null,z:null,
        basis:(ref!==null&&ref!==undefined)?'unknown_node':'unresolved'}); });
    const poly=_mPolyline(_pyT(s.polyline)?s.polyline:s.geometry,baseY);
    let length=null;
    if(poly){ length=0.0;
      for(let i=0;i+1<poly.length;i++){ const a=poly[i], b=poly[i+1];
        const ay=(a[1]===null||a[1]===undefined)?0.0:a[1];
        const by=(b[1]===null||b[1]===undefined)?0.0:b[1];
        length+=Math.sqrt(Math.pow(b[0]-a[0],2)+Math.pow(by-ay,2)+Math.pow(b[2]-a[2],2)); } }
    const declared=String(_pyT(s.routing_status)?s.routing_status:'').toUpperCase();
    let routing;
    if(MEP_ROUTING_STATUSES.indexOf(declared)>=0) routing=declared;
    else if(poly) routing='ROUTED';
    else if(ends.some(e=>e.basis==='unknown_node')) routing='UNRESOLVED';
    else routing='UNROUTED';
    const size=_mSize(s.size);
    const sid=(s.system_id===undefined)?null:s.system_id;
    out.push({id:_mnid(bid,s.id,'seg',n), type:'MEP_SEGMENT', building_id:bid,
      system_id:sid,
      system_resolved:(sid===null||sid===undefined)||sysIds.has(_mnid(bid,sid,'sys',0)),
      kind:(MEP_SEGMENT_KINDS.indexOf(kind)>=0)?kind:'other',
      declared_kind:(s.kind===undefined)?null:s.kind,
      kind_recognised:MEP_SEGMENT_KINDS.indexOf(kind)>=0,
      level_ref:(s.level===undefined)?null:s.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(s.level===null||s.level===undefined),
      start:ends[0], end:ends[1], polyline:poly, length_m:length,
      routing_status:routing, size:size, render_size:_mRenderSize(size,kind),
      material:(s.material===undefined)?null:s.material,
      source:_msrc(s.source),
      note:'represented route — no sizing, flow, pressure or capacity is implied'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ المعدّات --- */
function _mPorts(v,source){
  const out=[];
  (_pyT(v)?v:[]).forEach(p=>{
    if(p&&typeof p==='object'&&!Array.isArray(p)){
      const t=String(_pyT(p.type)?p.type:'').toLowerCase();
      out.push({id:(p.id===undefined)?null:p.id, port_type:t,
        port_type_recognised:MEP_PORT_TYPES.indexOf(t)>=0,
        source:_msrc(_pyT(p.source)?p.source:source)}); }
    else if(typeof p==='string')
      out.push({id:null, port_type:p.toLowerCase(),
        port_type_recognised:MEP_PORT_TYPES.indexOf(p.toLowerCase())>=0,
        source:_msrc(source)}); });
  return out; }
function _mDims(d){
  if(!d||typeof d!=='object'||Array.isArray(d)) return null;
  const pick=(a,b)=>_mnum((d[a]!==null&&d[a]!==undefined)?d[a]:d[b]);
  const out={w_m:pick('w','w_m'), d_m:pick('d','d_m'), h_m:pick('h','h_m')};
  if(out.w_m===null&&out.d_m===null&&out.h_m===null) return null;
  return out; }
function _mEquipment(raw,bid,levelsIdx,spaceIdx,sysIds){
  const out=[];
  (_pyT(raw.equipment)?raw.equipment:[]).forEach((e,n)=>{
    const lvl=_mLevelOf(levelsIdx,e.level);
    const t=String(_pyT(e.type)?e.type:'other').toLowerCase();
    const pos=(e.position&&typeof e.position==='object'&&!Array.isArray(e.position))?e.position:e;
    let y=_mnum(pos.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    const sp=_pyT(e.space)?e.space:(_pyT(e.space_id)?e.space_id:null);
    const sid=(e.system_id===undefined)?null:e.system_id;
    const dims=_mDims(e.dimensions);
    out.push({id:_mnid(bid,e.id,'eq',n), type:'MEP_EQUIPMENT', building_id:bid,
      system_id:sid,
      system_resolved:(sid===null||sid===undefined)||sysIds.has(_mnid(bid,sid,'sys',0)),
      equipment_type:(MEP_EQUIPMENT_TYPES.indexOf(t)>=0)?t:'other',
      declared_type:(e.type===undefined)?null:e.type,
      equipment_type_recognised:MEP_EQUIPMENT_TYPES.indexOf(t)>=0,
      x:_mnum(pos.x), y:y, z:_mnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      level_ref:(e.level===undefined)?null:e.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(e.level===null||e.level===undefined),
      space_ref:sp, space_id:sp?((spaceIdx.get(String(sp))||{}).id||null):null,
      space_resolved:(sp===null)||spaceIdx.has(String(sp)),
      dimensions:dims,
      render_dimensions:{
        w:(dims&&dims.w_m!==null)?dims.w_m:MEP_FALLBACKS.equipment_w_m,
        d:(dims&&dims.d_m!==null)?dims.d_m:MEP_FALLBACKS.equipment_d_m,
        h:(dims&&dims.h_m!==null)?dims.h_m:MEP_FALLBACKS.equipment_h_m,
        source:(dims&&dims.w_m!==null&&dims.d_m!==null&&dims.h_m!==null)
               ?'model':'display_fallback'},
      /* لا قدرة ولا جهد ولا تيار ولا تدفّق يُختلق: ما لم يُذكر يبقى غائباً */
      properties:_mPropMap(e.properties,e.source),
      ports:_mPorts(e.ports,e.source),
      connections:(_pyT(e.connections)?e.connections:[]).slice(),
      source:_msrc(e.source),
      note:'represented equipment — no rating, capacity or duty is implied'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ النهايات --- */
function _mTerminals(raw,bid,levelsIdx,spaceIdx,sysIds){
  const out=[];
  (_pyT(raw.terminals)?raw.terminals:[]).forEach((t,n)=>{
    const lvl=_mLevelOf(levelsIdx,t.level);
    const tt=String(_pyT(t.type)?t.type:'other').toLowerCase();
    const pos=(t.position&&typeof t.position==='object'&&!Array.isArray(t.position))?t.position:t;
    let y=_mnum(pos.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    const sp=_pyT(t.space)?t.space:(_pyT(t.space_id)?t.space_id:null);
    const sid=(t.system_id===undefined)?null:t.system_id;
    out.push({id:_mnid(bid,t.id,'term',n), type:'MEP_TERMINAL', building_id:bid,
      system_id:sid,
      system_resolved:(sid===null||sid===undefined)||sysIds.has(_mnid(bid,sid,'sys',0)),
      terminal_type:(MEP_TERMINAL_TYPES.indexOf(tt)>=0)?tt:'other',
      declared_type:(t.type===undefined)?null:t.type,
      terminal_type_recognised:MEP_TERMINAL_TYPES.indexOf(tt)>=0,
      x:_mnum(pos.x), y:y, z:_mnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      level_ref:(t.level===undefined)?null:t.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(t.level===null||t.level===undefined),
      space_ref:sp, space_id:sp?((spaceIdx.get(String(sp))||{}).id||null):null,
      space_resolved:(sp===null)||spaceIdx.has(String(sp)),
      node_ref:(t.node===undefined)?null:t.node,
      circuit_ref:(t.circuit===undefined)?null:t.circuit,
      properties:_mPropMap(t.properties,t.source),
      adapted:false, origin:'model', source:_msrc(t.source),
      note:'a represented terminal in a space is not a claim of adequate service'}); });
  out.sort(_byId); return out; }
/* يمثّل نقاط المرحلة 1 كنهايات ممثَّلة. لا عنصر دلالي مكرّر، والإسناد ينتقل كما
   هو: نقطة أضافها النظام تبقى system_default ولا تصير أبداً مطلوبة بقاعدة */
function adaptPhase1Terminals(building,bid,arch){
  bid=bid||'bld_0';
  if(arch===undefined||arch===null){
    try{ arch=compileArchitecture(building,bid); }catch(e){ arch=null; } }
  const out=[];
  _aLevels(building,bid).forEach(lvl=>{
    _aRoomsOf(building,lvl.template,bid).forEach(tr=>{
      const sid=tr[0], room=tr[1], rc=_aRect(room);
      (_pyT(room.points)?room.points:[]).forEach((p,pi)=>{
        const kind=String(_pyT(p.type)?p.type:'').toLowerCase();
        const mapped=Object.prototype.hasOwnProperty.call(_MEP_P1,kind)?_MEP_P1[kind]:null;
        if(mapped===null) return;
        const px=_mnum(p.x), pz=_mnum(p.z);
        out.push({id:bid+'.mep.p1_'+sid+'_'+pi+'@'+lvl.index,
          type:'MEP_TERMINAL', building_id:bid,
          system_id:null, system_resolved:true, suggested_system_type:mapped[1],
          terminal_type:mapped[0], declared_type:(p.type===undefined)?null:p.type,
          terminal_type_recognised:true,
          x:(rc&&px!==null)?(rc[0]+px):null, y:lvl.elevation_m,
          z:(rc&&pz!==null)?(rc[1]+pz):null,
          raw_x:(p.x===undefined)?null:p.x, raw_z:(p.z===undefined)?null:p.z,
          level_ref:lvl.index, level_id:lvl.id, level_index:lvl.index, level_resolved:true,
          space_ref:sid, space_id:sid+'@'+lvl.index, space_resolved:true,
          node_ref:null, circuit_ref:null, properties:{},
          adapted:true, origin:'phase1_point', origin_ref:sid+'.point_'+pi,
          /* الإسناد الأصلي ينتقل كما هو ولا يُرقّى إطلاقاً */
          original_source:_msrc(p.source,'system_default'),
          source:'phase1_adapter',
          note:'adapted from an existing Phase 1 point; the original provenance is '+
               'carried through unchanged and is never raised'}); }); }); });
  out.sort(_byId); return out; }
/* -------------------------------------------------------------- المناور --- */
function _mRisers(raw,bid,levelsIdx,arch,sysIds){
  const out=[];
  const cores=new Map(((arch||{}).cores||[]).map(c=>[c.id,c]));
  (_pyT(raw.risers)?raw.risers:[]).forEach((r,n)=>{
    const refs=(_pyT(r.levels)?r.levels:[]).slice();
    const lv=refs.map(x=>_mLevelOf(levelsIdx,x));
    const kind=String(_pyT(r.kind)?r.kind:'other').toLowerCase();
    const pos=(r.position&&typeof r.position==='object'&&!Array.isArray(r.position))?r.position:r;
    const coreId=(r.arch_core_id===undefined)?null:r.arch_core_id;
    const core=_pyT(coreId)?(cores.get(coreId)||null):null;
    const sids=(_pyT(r.system_ids)?r.system_ids:[]).slice();
    out.push({id:_mnid(bid,r.id,'riser',n), type:'MEP_RISER', building_id:bid,
      riser_kind:(MEP_RISER_KINDS.indexOf(kind)>=0)?kind:'other',
      declared_kind:(r.kind===undefined)?null:r.kind,
      x:_mnum(pos.x), z:_mnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      w_m:_mfallback(r.w_m,'riser_w_m'), d_m:_mfallback(r.d_m,'riser_d_m'),
      level_refs:refs, level_ids:lv.filter(Boolean).map(l=>l.id),
      level_indexes:lv.filter(Boolean).map(l=>l.index).sort(_sSortNum),
      levels_resolved:lv.every(l=>l!==null)&&refs.length>0,
      system_ids:sids,
      unresolved_system_ids:sids.filter(s=>!sysIds.has(_mnid(bid,s,'sys',0))),
      /* مناور المعماري ليست مناور MEP تلقائياً: الربط يحتاج دليلاً معلناً */
      arch_core_id:coreId,
      arch_core_resolved:_pyT(coreId)?(core!==null):null,
      arch_core_link_source:_pyT(coreId)?_msrc(r.arch_core_link_source):'unknown',
      source:_msrc(r.source),
      note:'an architectural shaft or core is not an MEP riser without explicit evidence'}); });
  out.sort(_byId); return out; }
/* ---------------------------------------------------------- الاختراقات --- */
function _mPenetrations(raw,bid,levelsIdx,segIds,arch,struct){
  const hosts=new Set();
  ['walls','slabs'].forEach(k=>((arch||{})[k]||[]).forEach(e=>hosts.add(e.id)));
  ['beams','columns','slabs','walls'].forEach(k=>((struct||{})[k]||[]).forEach(e=>hosts.add(e.id)));
  const out=[];
  (_pyT(raw.penetrations)?raw.penetrations:[]).forEach((p,n)=>{
    const lvl=_mLevelOf(levelsIdx,p.level);
    const ht=String(_pyT(p.host_type)?p.host_type:'OTHER').toUpperCase();
    const seg=(p.segment_id===undefined)?null:p.segment_id;
    const host=(p.host_id===undefined)?null:p.host_id;
    out.push({id:_mnid(bid,p.id,'pen',n), type:'MEP_PENETRATION', building_id:bid,
      segment_id:seg,
      segment_resolved:(seg!==null&&seg!==undefined)&&segIds.has(_mnid(bid,seg,'seg',0)),
      host_type:(MEP_PENETRATION_HOSTS.indexOf(ht)>=0)?ht:'OTHER',
      declared_host_type:(p.host_type===undefined)?null:p.host_type,
      host_id:host, host_resolved:_pyT(host)?hosts.has(host):false,
      x:_mnum(p.x), z:_mnum(p.z),
      level_ref:(p.level===undefined)?null:p.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      size:_mSize(p.size), source:_msrc(p.source),
      note:'a represented opening only — no fire stopping, sleeve or reinforcement '+
           'requirement is inferred'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ العلاقات --- */
function _mRelationships(bid,systems,nodes,segments,equipment,terminals,risers,pens,arch,raw,
                         issues){
  const rels=[]; let seq=0;
  const add=(rtype,frm,to,status,basis,meta)=>{ seq+=1;
    const e={id:bid+'.mep.rel_'+seq,type:rtype,from:frm,to:to,
      source:(status==='confirmed')?'model_declaration':'geometry_inference',
      status:status,basis:basis,
      note:'model topology and factual location only — no service adequacy is claimed'};
    if(_pyT(meta)) e.meta=meta;
    rels.push(e); return e; };
  const nodeIds=new Set(nodes.map(n=>n.id));
  const eqIds=new Set(equipment.map(e=>e.id));
  segments.forEach(s=>{
    [s.start,s.end].forEach(end=>{
      if(_pyT(end.node_id)) add('SEGMENT_CONNECTS',s.id,end.node_id,'confirmed',
        'segment endpoint references a declared MEP node');
      else add('SEGMENT_CONNECTS',s.id,null,'unresolved',
        'segment endpoint could not be resolved',{ref:end.ref}); });
    if(s.routing_status==='UNROUTED')
      add('SEGMENT_CONNECTS',s.id,null,'unresolved',
        'endpoints exist but no route geometry was supplied — no path is fabricated',
        {routing_status:'UNROUTED'}); });
  equipment.forEach(e=>e.connections.forEach(ref=>{
    const tgt=_mnid(bid,ref,'node',0);
    const known=nodeIds.has(tgt)||eqIds.has(tgt);
    add('EQUIPMENT_CONNECTED_TO',e.id,known?tgt:null,known?'confirmed':'unresolved',
      known?'declared by the model':'declared connection was not found'); }));
  terminals.forEach(t=>{
    if(_pyT(t.node_ref)){
      const tgt=_mnid(bid,t.node_ref,'node',0);
      const known=nodeIds.has(tgt);
      add('TERMINAL_CONNECTED_TO',t.id,known?tgt:null,known?'confirmed':'unresolved',
        known?'declared by the model':'declared node was not found'); }
    if(_pyT(t.circuit_ref))
      /* الدائرة تُذكر ولا تُصمَّم: لا تجميع تلقائي لمقابس في دوائر */
      add('TERMINAL_ON_CIRCUIT',t.id,String(t.circuit_ref),'confirmed','declared by the model',
        {disclaimer:'circuits are never grouped automatically'}); });
  (_pyT(raw.circuits)?raw.circuits:[]).forEach(c=>{
    const pref=(c.panel===undefined)?null:c.panel;
    if(_pyT(pref)) add('PANEL_FEEDS',_mnid(bid,pref,'eq',0),String(c.id),'confirmed',
      'declared by the model');
    (_pyT(c.terminals)?c.terminals:[]).forEach(ref=>
      add('CIRCUIT_FEEDS',String(c.id),_mnid(bid,ref,'term',0),'confirmed',
        'declared by the model')); });
  risers.forEach(r=>{
    if(r.level_indexes.length>1)
      add('RISER_CONNECTS_LEVELS',r.id,null,'confirmed','declared by the model',
        {levels:r.level_indexes.slice()});
    if(_pyT(r.arch_core_id))
      add('RISER_IN_SHAFT',r.id,r.arch_core_id,r.arch_core_resolved?'confirmed':'unresolved',
        'declared association with an architectural core',
        {link_source:r.arch_core_link_source}); });
  pens.forEach(p=>add('PENETRATION_THROUGH',p.id,p.host_id,
    p.host_resolved?'confirmed':'unresolved','declared by the model',
    {segment_id:p.segment_id,host_type:p.host_type}));
  /* موقع النهاية داخل فراغ معماري — واقعة مكانية، لا كفاية خدمة */
  const spaces=new Set(((arch||{}).spaces||[]).map(s=>s.id));
  const sysById=new Set(systems.map(s=>s.id));
  const seen=new Set();
  terminals.forEach(t=>{
    let sp=t.space_id;
    if(!_pyT(sp)&&t.x!==null&&t.x!==undefined&&t.level_index!==null&&t.level_index!==undefined){
      for(const s of ((arch||{}).spaces||[])){
        const rc=s.rect;
        if(rc&&s.level_index===t.level_index&&
           rc[0]-_M_EPS<=t.x&&t.x<=rc[0]+rc[2]+_M_EPS&&
           rc[1]-_M_EPS<=t.z&&t.z<=rc[1]+rc[3]+_M_EPS){ sp=s.id; break; } } }
    if(!_pyT(sp)||!spaces.has(sp)) return;
    add('SYSTEM_HAS_TERMINAL_IN',t.id,sp,'confirmed',
      'the terminal lies inside this architectural space',
      {disclaimer:'a represented terminal is not a claim of adequate service'});
    const sysid=t.system_id;
    const key=String(sysid)+'|'+sp;
    if(_pyT(sysid)&&sysById.has(_mnid(bid,sysid,'sys',0))&&!seen.has(key)){
      seen.add(key);
      add('SYSTEM_SERVES_SPACE',_mnid(bid,sysid,'sys',0),sp,'confirmed',
        'the system has a represented terminal in this space',
        {disclaimer:'representation only — no adequacy of airflow, water, light or '+
                    'power is claimed'}); } });
  return rels; }
/* --------------------------------------------------- التعارض والاختراق --- */
function _mSeg2d(p,q){ return [p[0],p[2],q[0],q[2]]; }
/* تقاطع مقطعين ثنائيي الأبعاد تقاطعاً حقيقياً (لا مجرّد تلامس طرف) */
function _mCross(a,b){
  const x1=a[0],z1=a[1],x2=a[2],z2=a[3];
  const x3=b[0],z3=b[1],x4=b[2],z4=b[3];
  const d=(x2-x1)*(z4-z3)-(z2-z1)*(x4-x3);
  if(Math.abs(d)<1e-12) return false;
  const t=((x3-x1)*(z4-z3)-(z3-z1)*(x4-x3))/d;
  const u=((x3-x1)*(z2-z1)-(z3-z1)*(x2-x1))/d;
  return t>1e-9&&t<1-1e-9&&u>1e-9&&u<1-1e-9; }
/* هل يمرّ مقطع ثنائي الأبعاد داخل مستطيل؟ فحص بالأطراف والحواف */
function _mSegHitsBox(a,b,box){
  if((box[0]<=a[0]&&a[0]<=box[2]&&box[1]<=a[2]&&a[2]<=box[3])||
     (box[0]<=b[0]&&b[0]<=box[2]&&box[1]<=b[2]&&b[2]<=box[3])) return true;
  const edges=[[box[0],box[1],box[2],box[1]],[box[2],box[1],box[2],box[3]],
               [box[2],box[3],box[0],box[3]],[box[0],box[3],box[0],box[1]]];
  const seg=[a[0],a[2],b[0],b[2]];
  return edges.some(e=>_mCross(seg,e)); }
/* تعارضات هندسية واضحة فقط — ليست كشف تصادم BIM ولا حكم مطابقة */
function _mInterference(bid,segments,equipment,terminals,risers,pens,arch,struct,building,issues){
  const penHosts=new Set(pens.map(p=>String(p.segment_id)+'|'+String(p.host_id)));
  const penAny=new Set(pens.map(p=>String(p.segment_id)));
  if(arch){
    const walls=arch.walls||[], voids=arch.voids||[];
    segments.forEach(s=>{
      if(!s.polyline) return;
      for(let i=0;i+1<s.polyline.length;i++){
        const a=s.polyline[i], b=s.polyline[i+1];
        const seg=_mSeg2d(a,b);
        walls.forEach(w=>{
          if(s.level_index!==null&&s.level_index!==undefined&&w.level_index!==s.level_index) return;
          const wl=[w.start.x,w.start.z,w.end.x,w.end.z];
          if(_mCross(seg,wl)){
            const rawId=String(s.id).split('.mep.').slice(-1)[0];
            if(penHosts.has(String(s.id)+'|'+w.id)||penHosts.has(rawId+'|'+w.id)) return;
            issues.push({code:'SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION',
              subject:s.id,other:w.id,
              detail:'no penetration is represented at this crossing; '+
                     'nothing is cut and nothing is rerouted'}); } });
        const ay=(a[1]===null||a[1]===undefined)?null:a[1];
        const by=(b[1]===null||b[1]===undefined)?null:b[1];
        if(ay!==null&&by!==null&&Math.abs(by-ay)>_M_TOL){
          const lo=Math.min(ay,by), hi=Math.max(ay,by);
          (arch.slabs||[]).forEach(sl=>{
            const el=sl.elevation_m;
            if(el===null||el===undefined||!(lo+_M_EPS<el&&el<hi-_M_EPS)) return;
            const rawId=String(s.id).split('.mep.').slice(-1)[0];
            if(penHosts.has(String(s.id)+'|'+sl.id)||penHosts.has(rawId+'|'+sl.id)) return;
            issues.push({code:'SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION',
              subject:s.id,other:sl.id,
              detail:'no penetration is represented at this level'}); }); }
        for(const v of voids){
          const r=v.rect;
          let hit=false;
          for(const pt of [a,b])
            if(r[0]<=pt[0]&&pt[0]<=r[0]+r[2]&&r[1]<=pt[2]&&pt[2]<=r[1]+r[3]){ hit=true; break; }
          if(hit) issues.push({code:'MEP_ELEMENT_IN_FLOOR_OPENING',subject:s.id,other:v.id}); } } });
    const spaces=new Map((arch.spaces||[]).map(s=>[s.id,s]));
    equipment.concat(terminals).forEach(e=>{
      const sp=spaces.get(e.space_id);
      if(!sp||!sp.rect||e.x===null||e.x===undefined) return;
      const rc=sp.rect;
      if(!(rc[0]-_M_TOL<=e.x&&e.x<=rc[0]+rc[2]+_M_TOL&&
           rc[1]-_M_TOL<=e.z&&e.z<=rc[1]+rc[3]+_M_TOL))
        issues.push({code:(e.type==='MEP_EQUIPMENT')?'EQUIPMENT_OUTSIDE_SPACE'
                                                    :'TERMINAL_OUTSIDE_SPACE',
          subject:e.id,other:sp.id}); });
    const rects=(arch.spaces||[]).filter(s=>s.rect).map(s=>s.rect);
    if(rects.length){
      const bb=[Math.min.apply(null,rects.map(r=>r[0])),Math.min.apply(null,rects.map(r=>r[1])),
                Math.max.apply(null,rects.map(r=>r[0]+r[2])),
                Math.max.apply(null,rects.map(r=>r[1]+r[3]))];
      segments.forEach(s=>{
        if(!s.polyline) return;
        if(s.polyline.some(p=>!(bb[0]-1.0<=p[0]&&p[0]<=bb[2]+1.0&&
                                bb[1]-1.0<=p[2]&&p[2]<=bb[3]+1.0)))
          issues.push({code:'ROUTE_OUTSIDE_BUILDING',subject:s.id,footprint:bb}); }); }
    const cores=new Map((arch.cores||[]).map(c=>[c.id,c]));
    risers.forEach(r=>{
      const c=cores.get(r.arch_core_id);
      if(!c||r.x===null||r.x===undefined) return;
      const fw=c.footprint_w_m.value||c.footprint_w_m.render_fallback;
      const fd=c.footprint_d_m.value||c.footprint_d_m.render_fallback;
      if(Math.abs(r.x-c.x)>fw/2.0+_M_TOL||Math.abs(r.z-c.z)>fd/2.0+_M_TOL)
        issues.push({code:'RISER_OUTSIDE_SHAFT',subject:r.id,other:c.id}); }); }
  if(struct){
    segments.forEach(s=>{
      if(!s.polyline) return;
      for(let i=0;i+1<s.polyline.length;i++){
        const a=s.polyline[i], b=s.polyline[i+1];
        const seg=_mSeg2d(a,b);
        (struct.beams||[]).forEach(bm=>{
          if(bm.start.x===null||bm.end.x===null) return;
          if(s.level_index!==null&&s.level_index!==undefined&&bm.level_index!==s.level_index) return;
          const bl=[bm.start.x,bm.start.z,bm.end.x,bm.end.z];
          if(_mCross(seg,bl))
            issues.push({code:'SEGMENT_CROSSES_STRUCTURAL_BEAM',subject:s.id,other:bm.id,
              detail:'reported only — the structural member is not cut and the route '+
                     'is not redesigned'}); });
        (struct.columns||[]).forEach(c=>{
          if(c.x===null) return;
          const rs=c.render_section, known=rs.source==='model';
          const hw=known?rs.w/2.0:_M_TOL, hd=known?rs.d/2.0:_M_TOL;
          const box=[c.x-hw,c.z-hd,c.x+hw,c.z+hd];
          if(_mSegHitsBox(a,b,box))
            issues.push({code:'SEGMENT_CROSSES_STRUCTURAL_COLUMN',subject:s.id,other:c.id,
              basis:known?'column_section_footprint':'column_axis_proximity'}); });
        const ay=(a[1]===null||a[1]===undefined)?null:a[1];
        const by=(b[1]===null||b[1]===undefined)?null:b[1];
        if(ay!==null&&by!==null&&Math.abs(by-ay)>_M_TOL){
          const lo=Math.min(ay,by), hi=Math.max(ay,by);
          (struct.slabs||[]).forEach(sl=>{
            const el=sl.elevation_m;
            if(el===null||el===undefined||!(lo+_M_EPS<el&&el<hi-_M_EPS)) return;
            if(penAny.has(String(s.id))) return;
            issues.push({code:'SEGMENT_CROSSES_STRUCTURAL_SLAB',subject:s.id,other:sl.id}); }); } } }); } }
/* ------------------------------------------------------------- التصريف --- */
function compileMep(building,buildingId,position,rotationDeg,arch,struct,adaptPhase1){
  const bid=buildingId||'bld_0';
  const raw=_mraw(building);
  if(arch===undefined||arch===null){
    try{ arch=compileArchitecture(building,bid,position,rotationDeg); }catch(e){ arch=null; } }
  if(struct===undefined||struct===null){
    try{ struct=compileStructure(building,bid,position,rotationDeg,arch); }catch(e){ struct=null; } }
  if(adaptPhase1===undefined) adaptPhase1=true;
  const levelsIdx=_mLevelsIndex(building,bid);
  const spaceIdx=_mSpaceIndex(arch);
  const issues=[];
  const knownKeys=['status','synthetic','meta','systems','nodes','segments','equipment',
    'terminals','risers','penetrations','circuits','layer_visibility','visible_layers'];
  Object.keys(raw).sort(_scmp).forEach(k=>{
    if(knownKeys.indexOf(k)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:k,
        detail:'this collection is not part of the MEP schema and was NOT interpreted'}); });
  const systems=_mSystems(raw,bid,levelsIdx);
  const sysIds=new Set(systems.map(s=>s.id));
  const nodes=_mNodes(raw,bid,levelsIdx,spaceIdx,sysIds);
  const nodeIdx=new Map(nodes.map(n=>[n.id,n]));
  const segments=_mSegments(raw,bid,levelsIdx,nodeIdx,sysIds);
  const segIds=new Set(segments.map(s=>s.id));
  const equipment=_mEquipment(raw,bid,levelsIdx,spaceIdx,sysIds);
  const terminals=_mTerminals(raw,bid,levelsIdx,spaceIdx,sysIds);
  const risers=_mRisers(raw,bid,levelsIdx,arch,sysIds);
  const pens=_mPenetrations(raw,bid,levelsIdx,segIds,arch,struct);
  const adapted=adaptPhase1?adaptPhase1Terminals(building,bid,arch):[];
  const counted=systems.length+nodes.length+segments.length+equipment.length+terminals.length
    +risers.length+pens.length;
  const declared=String(_pyT(raw.status)?raw.status:'').toUpperCase();
  let status;
  if(MEP_MODEL_STATUS.indexOf(declared)>=0) status=declared;
  else if(counted===0) status='NOT_DEFINED';
  else {
    const verified=systems.concat(nodes).concat(segments).concat(equipment)
      .concat(terminals).concat(risers)
      .every(e=>MEP_VERIFIED_SOURCES.indexOf(e.source)>=0);
    status=verified?'REPRESENTED':'PARTIAL'; }
  const out={schema:MEP_SCHEMA, compiler_version:MEP_COMPILER_VERSION, building_id:bid,
    status:status,
    status_basis:(MEP_MODEL_STATUS.indexOf(declared)>=0)?'declared_by_model'
      :((counted===0)?'no MEP element is present':'derived from element provenance'),
    synthetic:raw.synthetic===true, regulatory:false,
    transform:{position:position||{x:0.0,z:0.0}, rotation_deg:Number(rotationDeg||0.0),
      applied:'local coordinates; world transform is applied on read'},
    levels:_aLevels(building,bid).map(l=>({id:l.id,index:l.index,elevation_m:l.elevation_m})),
    systems:systems, nodes:nodes, segments:segments, equipment:equipment,
    terminals:terminals, adapted_terminals:adapted, risers:risers,
    penetrations:pens, relationships:[], issues:[],
    meta:{note:ACS_MEP_SPEC.note, fire_note:ACS_MEP_SPEC.fire_note,
      elements:counted, adapted_terminals:adapted.length,
      levels_source:'architectural level table',
      spaces_source:'architectural space table',
      service_adequacy:'not evaluated — representation only',
      navigation_impact:ACS_MEP_SPEC.navigation_note}};
  out.relationships=_mRelationships(bid,systems,nodes,segments,equipment,
    terminals.concat(adapted),risers,pens,arch,raw,issues);
  _mInterference(bid,segments,equipment,terminals,risers,pens,arch,struct,building,issues);
  validateMep(out).forEach(i=>issues.push(i));
  issues.forEach(i=>{ i.severity=mepSeverityOf(i.code); });
  const dec=issues.map((it,i)=>({it:it,i:i}));
  dec.sort((a,b)=>{
    const sa=MEP_SEVERITIES.indexOf(a.it.severity)*-1;
    const sb=MEP_SEVERITIES.indexOf(b.it.severity)*-1;
    if(sa!==sb) return sa-sb;
    const c=_scmp(String(a.it.code),String(b.it.code));
    if(c!==0) return c;
    const d=_scmp(String(a.it.subject),String(b.it.subject));
    return d!==0?d:(a.i-b.i); });
  out.issues=dec.map(d=>d.it);
  return out; }
/* ------------------------------------------------------------- التحقّق --- */
/* فحوص سلامة نموذج — ليست فحوص كود MEP إطلاقاً */
function validateMep(mep){
  const issues=[], bid=mep.building_id;
  const groups=['systems','nodes','segments','equipment','terminals','risers','penetrations'];
  const seen=new Map();
  groups.forEach(key=>(mep[key]||[]).forEach(e=>{
    if(seen.has(e.id)) issues.push({code:'DUPLICATE_ELEMENT_ID',subject:e.id,other:seen.get(e.id)});
    seen.set(e.id,key);
    if(MEP_ELEMENT_TYPES.indexOf(e.type)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:e.id,declared:e.type});
    if(bid&&String(e.id).indexOf(String(bid)+'.')!==0)
      issues.push({code:'CROSS_BUILDING_REF',subject:e.id}); }));
  (mep.systems||[]).forEach(s=>{
    if(!s.system_type_recognised)
      issues.push({code:'UNKNOWN_SYSTEM_TYPE',subject:s.id,declared:s.declared_type});
    if(!s.medium_recognised)
      issues.push({code:'UNKNOWN_MEDIUM',subject:s.id,declared:s.declared_medium});
    if(!s.levels_resolved)
      issues.push({code:'INVALID_LEVEL_REF',subject:s.id,refs:s.serves_level_refs}); });
  (mep.nodes||[]).forEach(n=>{
    if(_mBadNumber(n.raw_x)||_mBadNumber(n.raw_z)||n.x===null||n.z===null)
      issues.push({code:'NAN_COORDINATE',subject:n.id});
    if(!n.system_resolved) issues.push({code:'INVALID_SYSTEM_REF',subject:n.id,ref:n.system_id});
    if(!n.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:n.id,ref:n.level_ref});
    if(!n.space_resolved) issues.push({code:'INVALID_SPACE_REF',subject:n.id,ref:n.space_ref}); });
  const usedNodes=new Set();
  (mep.segments||[]).forEach(s=>{
    [s.start,s.end].forEach(end=>{
      if(_pyT(end.node_id)) usedNodes.add(end.node_id);
      else if(end.basis==='unknown_node'){
        issues.push({code:'INVALID_NODE_REF',subject:s.id,ref:end.ref});
        issues.push({code:'SEGMENT_ENDPOINT_UNRESOLVED',subject:s.id,ref:end.ref}); }
      else issues.push({code:'SEGMENT_ENDPOINT_UNRESOLVED',subject:s.id,ref:end.ref}); });
    if(!s.system_resolved) issues.push({code:'INVALID_SYSTEM_REF',subject:s.id,ref:s.system_id});
    if(!s.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:s.id,ref:s.level_ref});
    if(!s.kind_recognised)
      issues.push({code:'UNKNOWN_SEGMENT_KIND',subject:s.id,declared:s.declared_kind});
    if(s.length_m!==null&&s.length_m<=_M_EPS)
      issues.push({code:'SEGMENT_ZERO_LENGTH',subject:s.id});
    if(s.routing_status==='UNROUTED')
      issues.push({code:'SEGMENT_UNROUTED',subject:s.id,
        detail:'endpoints exist but no route geometry was supplied; no path is fabricated'});
    if(s.size===null) issues.push({code:'SIZE_UNKNOWN',subject:s.id});
    else ['diameter_m','width_m','height_m'].forEach(f=>{
      if(s.size[f]!==null&&s.size[f]!==undefined&&s.size[f]<=0)
        issues.push({code:'NEGATIVE_DIMENSION',subject:s.id,field:f}); }); });
  (mep.nodes||[]).forEach(n=>{
    if(!usedNodes.has(n.id)&&n.kind!=='terminal'&&n.kind!=='equipment_connection')
      issues.push({code:'ORPHAN_NODE',subject:n.id,
        detail:'no segment references this node'}); });
  const nodeIds=new Set((mep.nodes||[]).map(n=>n.id));
  const eqIds=new Set((mep.equipment||[]).map(x=>x.id));
  (mep.equipment||[]).forEach(e=>{
    if(_mBadNumber(e.raw_x)||_mBadNumber(e.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:e.id});
    if(!e.system_resolved) issues.push({code:'INVALID_SYSTEM_REF',subject:e.id,ref:e.system_id});
    if(!e.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:e.id,ref:e.level_ref});
    if(!e.space_resolved) issues.push({code:'INVALID_SPACE_REF',subject:e.id,ref:e.space_ref});
    if(!e.equipment_type_recognised)
      issues.push({code:'UNKNOWN_EQUIPMENT_TYPE',subject:e.id,declared:e.declared_type});
    if(e.dimensions) ['w_m','d_m','h_m'].forEach(f=>{
      if(e.dimensions[f]!==null&&e.dimensions[f]!==undefined&&e.dimensions[f]<=0)
        issues.push({code:'NEGATIVE_DIMENSION',subject:e.id,field:f}); });
    e.ports.forEach(p=>{ if(!p.port_type_recognised)
      issues.push({code:'INVALID_PORT_TYPE',subject:e.id,declared:p.port_type}); });
    e.connections.forEach(ref=>{
      if(!nodeIds.has(_mnid(bid,ref,'node',0))&&!eqIds.has(_mnid(bid,ref,'eq',0)))
        issues.push({code:'INVALID_EQUIPMENT_REF',subject:e.id,ref:ref}); }); });
  (mep.terminals||[]).forEach(t=>{
    if(_mBadNumber(t.raw_x)||_mBadNumber(t.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:t.id});
    if(!t.system_resolved) issues.push({code:'INVALID_SYSTEM_REF',subject:t.id,ref:t.system_id});
    if(!t.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:t.id,ref:t.level_ref});
    if(!t.space_resolved) issues.push({code:'INVALID_SPACE_REF',subject:t.id,ref:t.space_ref});
    if(!t.terminal_type_recognised)
      issues.push({code:'UNKNOWN_TERMINAL_TYPE',subject:t.id,declared:t.declared_type});
    if((t.system_id===null||t.system_id===undefined)&&(t.node_ref===null||t.node_ref===undefined))
      issues.push({code:'ORPHAN_TERMINAL',subject:t.id,
        detail:'the terminal names neither a system nor a node'}); });
  (mep.risers||[]).forEach(r=>{
    if(!r.levels_resolved)
      issues.push({code:'RISER_LEVELS_UNRESOLVED',subject:r.id,refs:r.level_refs});
    r.unresolved_system_ids.forEach(s=>
      issues.push({code:'INVALID_SYSTEM_REF',subject:r.id,ref:s}));
    if(_mBadNumber(r.raw_x)||_mBadNumber(r.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:r.id}); });
  (mep.penetrations||[]).forEach(p=>{
    if(!p.segment_resolved)
      issues.push({code:'PENETRATION_SEGMENT_UNRESOLVED',subject:p.id,ref:p.segment_id});
    if(!p.host_resolved)
      issues.push({code:'PENETRATION_HOST_UNRESOLVED',subject:p.id,ref:p.host_id}); });
  return issues; }
/* -------------------------------------------------------- بيانات الرسم --- */
const _MEP_DISC_TAG=(()=>{const m={}; MEP_DISCIPLINES.forEach(d=>{m[d]=d;}); return m;})();
function _mDisciplineOf(mep,systemId,fallback){
  for(const s of (mep.systems||[]))
    if(s.id===systemId||s.id===_mnid(mep.building_id,systemId,'sys',0)) return s.discipline;
  return (fallback===undefined||fallback===null)?'OTHER':fallback; }
/* هندسة عرض فقط. كل عنصر يعلن هل أبعاده من النموذج أم احتياط عرض */
function mepRenderItems(mep){
  const items=[];
  (mep.segments||[]).forEach(s=>{
    if(!s.polyline||s.polyline.length<2) return;
    const disc=_mDisciplineOf(mep,s.system_id);
    const rs=s.render_size;
    for(let i=0;i+1<s.polyline.length;i++){
      const a=s.polyline[i], b=s.polyline[i+1];
      const ay=(a[1]===null||a[1]===undefined)?0.0:a[1];
      const by=(b[1]===null||b[1]===undefined)?0.0:b[1];
      const dx=b[0]-a[0], dy=by-ay, dz=b[2]-a[2];
      const ln=Math.sqrt(dx*dx+dy*dy+dz*dz);
      if(ln<=_M_EPS) continue;
      items.push({name:'MEP|'+(_MEP_DISC_TAG[disc]||'OTHER')+'|'+s.id+'|'+i,
        kind:'SEGMENT', id:s.id, discipline:disc,
        cx:(a[0]+b[0])/2.0, cy:(ay+by)/2.0, cz:(a[2]+b[2])/2.0,
        ex:ln, ey:rs.h, ez:rs.w, rot_y:Math.atan2(-dz,dx),
        vertical:Math.abs(dy)>Math.abs(dx)+Math.abs(dz),
        geometry_source:rs.source, element_source:s.source}); } });
  (mep.equipment||[]).forEach(e=>{
    if(e.x===null||e.y===null||e.y===undefined) return;
    const rd=e.render_dimensions;
    const disc=_mDisciplineOf(mep,e.system_id);
    items.push({name:'MEP|'+(_MEP_DISC_TAG[disc]||'OTHER')+'|'+e.id+'|eq',
      kind:'EQUIPMENT', id:e.id, discipline:disc,
      cx:e.x, cy:e.y+rd.h/2.0, cz:e.z, ex:rd.w, ey:rd.h, ez:rd.d,
      geometry_source:rd.source, element_source:e.source}); });
  (mep.terminals||[]).concat(mep.adapted_terminals||[]).forEach(t=>{
    if(t.x===null||t.y===null||t.y===undefined) return;
    const disc=_mDisciplineOf(mep,t.system_id,
      MEP_DISCIPLINE_OF[t.suggested_system_type||'OTHER']||'OTHER');
    const sz=MEP_FALLBACKS.terminal_size_m;
    items.push({name:'MEP|'+(_MEP_DISC_TAG[disc]||'OTHER')+'|'+t.id+'|term',
      kind:'TERMINAL', id:t.id, discipline:disc, terminal_type:t.terminal_type,
      cx:t.x, cy:t.y+sz/2.0, cz:t.z, ex:sz, ey:sz, ez:sz,
      geometry_source:'display_fallback', element_source:t.source,
      adapted:t.adapted===true}); });
  const lvIdx=new Map((mep.levels||[]).map(l=>[l.index,l]));
  (mep.risers||[]).forEach(r=>{
    if(r.x===null||!r.level_indexes.length) return;
    const lo=lvIdx.get(Math.min.apply(null,r.level_indexes));
    const hi=lvIdx.get(Math.max.apply(null,r.level_indexes));
    const base=lo?lo.elevation_m:null, top=hi?hi.elevation_m:null;
    if(base===null||top===null||base===undefined||top===undefined||top-base<=_M_EPS) return;
    let w=r.w_m.value, d=r.d_m.value;
    const src=(w!==null&&d!==null)?'model':'display_fallback';
    if(w===null) w=r.w_m.render_fallback;
    if(d===null) d=r.d_m.render_fallback;
    items.push({name:'MEP|RISER|'+r.id+'|riser', kind:'RISER', id:r.id, discipline:'OTHER',
      cx:r.x, cy:base+(top-base)/2.0, cz:r.z, ex:w, ey:top-base, ez:d,
      geometry_source:src, element_source:r.source}); });
  items.sort((a,b)=>_scmp(String(a.name),String(b.name)));
  return items; }
/* --------------------------------------------------------------- خدمات --- */
function mepElementById(mep,eid){
  const keys=['systems','nodes','segments','equipment','terminals','adapted_terminals',
              'risers','penetrations'];
  for(const key of keys) for(const el of (mep[key]||[])) if(el.id===eid) return el;
  for(const r of (mep.relationships||[])) if(r.id===eid) return r;
  return null; }
function mepSystemById(mep,sid){
  for(const s of (mep.systems||[]))
    if(s.id===sid||s.id===_mnid(mep.building_id,sid,'sys',0)) return s;
  return null; }
function mepInterferences(mep){
  const codes=['SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION',
    'SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION','SEGMENT_CROSSES_STRUCTURAL_BEAM',
    'SEGMENT_CROSSES_STRUCTURAL_COLUMN','SEGMENT_CROSSES_STRUCTURAL_SLAB',
    'RISER_OUTSIDE_SHAFT','EQUIPMENT_OUTSIDE_SPACE','TERMINAL_OUTSIDE_SPACE',
    'MEP_ELEMENT_IN_FLOOR_OPENING','ROUTE_OUTSIDE_BUILDING'];
  return (mep.issues||[]).filter(i=>codes.indexOf(i.code)>=0); }
function mepToWorld(mep,x,z){
  const t=mep.transform||{};
  const rot=(Number(t.rotation_deg||0.0))*Math.PI/180;
  const px=Number((t.position||{}).x||0.0), pz=Number((t.position||{}).z||0.0);
  const ca=Math.cos(rot), sa=Math.sin(rot);
  return [px+x*ca-z*sa, pz+x*sa+z*ca]; }
/* حقائق MEP معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية هنا،
   والاحتياط لا يدخل أبداً: ما لم يُذكر يبقى null */
function mepRuleInputs(mep){
  const out={building:{}};
  const present={};
  (mep.systems||[]).forEach(s=>{ present[s.system_type]=true; });
  MEP_SYSTEM_TYPES.forEach(t=>{ out.building['mep.system.exists.'+t]=present[t]===true; });
  const terms=(mep.terminals||[]).concat(mep.adapted_terminals||[]);
  out.building['mep.terminal.count']=terms.length;
  out.building['mep.equipment.count']=(mep.equipment||[]).length;
  (mep.equipment||[]).forEach(e=>{
    out[e.id]={'mep.equipment.type':e.equipment_type,
      'mep.equipment.system':e.system_id,
      'mep.member.source':e.source}; });
  (mep.segments||[]).forEach(s=>{ const sz=s.size||{};
    out[s.id]={'mep.segment.kind':s.kind,
      'mep.segment.size.diameter_m':(sz.diameter_m===undefined)?null:sz.diameter_m,
      'mep.segment.size.width_m':(sz.width_m===undefined)?null:sz.width_m,
      'mep.segment.size.height_m':(sz.height_m===undefined)?null:sz.height_m,
      'mep.segment.routing_status':s.routing_status,
      'mep.member.source':s.source}; });
  const served=new Map();
  (mep.relationships||[]).forEach(r=>{
    if(r.type==='SYSTEM_SERVES_SPACE'){
      if(!served.has(r.to)) served.set(r.to,[]);
      served.get(r.to).push(r.from); } });
  Array.from(served.keys()).sort(_scmp).forEach(sp=>{
    if(!out[sp]) out[sp]={};
    out[sp]['mep.system.serves_space']=served.get(sp).slice().sort(_scmp); });
  return out; }
function mepSummary(mep){
  const iss=mep.issues||[], byDisc={};
  (mep.systems||[]).forEach(s=>{ byDisc[s.discipline]=(byDisc[s.discipline]||0)+1; });
  const segs=mep.segments||[];
  return {building_id:mep.building_id, compiler_version:mep.compiler_version,
    status:mep.status, synthetic:mep.synthetic===true, regulatory:false,
    systems:(mep.systems||[]).length, systems_by_discipline:byDisc,
    nodes:(mep.nodes||[]).length, segments:segs.length,
    routed_segments:segs.filter(s=>s.routing_status==='ROUTED').length,
    unrouted_segments:segs.filter(s=>s.routing_status==='UNROUTED').length,
    segments_with_size:segs.filter(s=>_pyT(s.size)).length,
    equipment:(mep.equipment||[]).length,
    terminals:(mep.terminals||[]).length,
    adapted_terminals:(mep.adapted_terminals||[]).length,
    risers:(mep.risers||[]).length, penetrations:(mep.penetrations||[]).length,
    relationships:(mep.relationships||[]).length,
    interferences:mepInterferences(mep).length,
    issues:iss.length,
    errors:iss.filter(i=>i.severity==='ERROR').length,
    warnings:iss.filter(i=>i.severity==='WARNING').length,
    infos:iss.filter(i=>i.severity==='INFO').length,
    note:'MEP representation only — no design, no load or flow calculation, '+
         'no sizing, no code compliance'}; }
/* ==================================================================
   المرحلة 2 — أساس نموذج بيانات الحريق وسلامة الأرواح (مطابق لـ acs_fls.py).
   تمثيل وطوبولوجيا فقط: لا هندسة حريق ولا محاكاة ولا تغطية ولا هيدروليك ولا
   مطابقة كود ولا قيم NFPA/SBC • الجهاز موجود ≠ التغطية مؤكّدة •
   الغياب ليس مخالفة • CODE_REQUIRED غير موجود هنا إطلاقاً •
   لا تعديل للمعماري ولا للإنشائي ولا لـ MEP، ولا إصلاح تلقائي.
   ================================================================== */
const ACS_FLS_SPEC = {
 "schema": "acs.fls/1",
 "compiler_version": "acs-fls-compiler/1.0.0",
 "note": "FIRE & LIFE-SAFETY REPRESENTATION AND TOPOLOGY ONLY. This layer normalises and connects fire and life-safety facts that already exist elsewhere in the model. It performs NO fire engineering and NO fire simulation: no sprinkler spacing, coverage, hydraulics, density or demand-area selection; no fire-water demand, pump or tank sizing; no detector spacing or quantity; no alarm zoning, audibility or notification design; no fire-resistance rating calculation or inference; no evacuation or egress compliance. It implements NO NFPA, SBC, IBC or Civil Defense rule value. Nothing here may be read as evidence that anything is protected, covered, adequate, approved or compliant.",
 "fire_note": "Fire-protection content in this layer is DATA REPRESENTATION AND TOPOLOGY ONLY. There is no Fire / Life-Safety engine: coverage, spacing, device quantity, sprinkler hydraulics, fire-water demand, alarm zoning, notification audibility, fire-resistance rating and code compliance are all out of scope and are never evaluated or inferred.",
 "element_types": [
  "FLS_ZONE",
  "FLS_BARRIER",
  "FLS_OPENING",
  "FLS_EXIT",
  "FLS_STAIR",
  "FLS_SHAFT",
  "FLS_DEVICE",
  "FLS_SYSTEM",
  "FLS_SIGN",
  "FLS_ASSEMBLY_POINT",
  "FLS_REFUGE_AREA",
  "FLS_SMOKE_CONTROL"
 ],
 "model_status": [
  "NOT_DEFINED",
  "PARTIAL",
  "REPRESENTED",
  "IMPORTED",
  "VERIFIED_DATA"
 ],
 "status_note": "COMPLIANT / SAFE / APPROVED / CERTIFIED / DESIGNED are deliberately absent. No engine in this platform can justify them, and absence of data is never a violation.",
 "provenance_values": [
  "user",
  "imported",
  "ai_inference",
  "system_default",
  "manual_verified",
  "phase1_adapter",
  "mep_adapter",
  "egress_adapter",
  "arch_adapter",
  "test_fixture",
  "display_fallback",
  "unknown"
 ],
 "forbidden_provenance": [
  "code_required",
  "rule",
  "nfpa",
  "sbc",
  "civil_defense"
 ],
 "provenance_note": "code_required and rule are NOT provenance values here and never can be in this phase: no verified fire rule evidence exists anywhere in the platform. An adapter carries the original provenance of the object it references through unchanged and can never raise it — a system-added smoke detector stays system_default.",
 "verified_sources": [
  "user",
  "imported",
  "manual_verified"
 ],
 "adapter_origins": [
  "model",
  "mep_adapter",
  "phase1_adapter",
  "egress_adapter",
  "arch_adapter"
 ],
 "adapter_note": "this layer does not duplicate semantic objects or geometry. An exit comes from the egress foundation, a sprinkler head or detector from the MEP model, a stair or shaft from the architectural cores, a Phase 1 safety point from the Phase 1 adapter. Each adapted element references its source element id and emits no second geometry.",
 "device_types": [
  "SMOKE_DETECTOR",
  "HEAT_DETECTOR",
  "MULTI_SENSOR",
  "MANUAL_CALL_POINT",
  "ALARM_SOUNDER",
  "STROBE",
  "SOUNDER_STROBE",
  "FIRE_ALARM_PANEL",
  "REPEATER_PANEL",
  "SPRINKLER_HEAD",
  "HOSE_REEL",
  "FIRE_EXTINGUISHER",
  "HYDRANT",
  "FIRE_PUMP",
  "FIRE_WATER_TANK",
  "FLOW_SWITCH",
  "VALVE",
  "PRESSURE_SWITCH",
  "EMERGENCY_LIGHT",
  "EXIT_SIGN",
  "VOICE_EVAC_DEVICE",
  "OTHER"
 ],
 "device_note": "no device is ever instantiated automatically. A device exists because the model declared it, or because an existing MEP or Phase 1 object was referenced through an adapter. No coverage radius, activation temperature, K-factor, pressure, flow, candela or sound level is ever inferred.",
 "device_categories": {
  "SMOKE_DETECTOR": "DETECTION",
  "HEAT_DETECTOR": "DETECTION",
  "MULTI_SENSOR": "DETECTION",
  "MANUAL_CALL_POINT": "DETECTION",
  "FLOW_SWITCH": "DETECTION",
  "PRESSURE_SWITCH": "DETECTION",
  "ALARM_SOUNDER": "ALARM",
  "STROBE": "ALARM",
  "SOUNDER_STROBE": "ALARM",
  "VOICE_EVAC_DEVICE": "ALARM",
  "FIRE_ALARM_PANEL": "ALARM",
  "REPEATER_PANEL": "ALARM",
  "SPRINKLER_HEAD": "SUPPRESSION",
  "HOSE_REEL": "SUPPRESSION",
  "FIRE_EXTINGUISHER": "SUPPRESSION",
  "VALVE": "SUPPRESSION",
  "HYDRANT": "FIRE_WATER",
  "FIRE_PUMP": "FIRE_WATER",
  "FIRE_WATER_TANK": "FIRE_WATER",
  "EMERGENCY_LIGHT": "EMERGENCY_LIGHTING",
  "EXIT_SIGN": "SIGNAGE",
  "OTHER": "OTHER"
 },
 "device_categories_list": [
  "DETECTION",
  "ALARM",
  "SUPPRESSION",
  "FIRE_WATER",
  "EMERGENCY_LIGHTING",
  "SIGNAGE",
  "OTHER"
 ],
 "mep_device_map": {
  "smoke_detector": "SMOKE_DETECTOR",
  "heat_detector": "HEAT_DETECTOR",
  "manual_call_point": "MANUAL_CALL_POINT",
  "fire_alarm_device": "SOUNDER_STROBE",
  "sprinkler_head": "SPRINKLER_HEAD",
  "fire_hose_reel": "HOSE_REEL",
  "hydrant": "HYDRANT"
 },
 "mep_equipment_map": {
  "fire_pump": "FIRE_PUMP"
 },
 "referenced_mep_systems": [
  "SPRINKLER",
  "FIRE_WATER",
  "FIRE_ALARM",
  "EMERGENCY_POWER",
  "LIGHTING"
 ],
 "mep_note": "the MEP model stays the single source of truth for system topology. This layer never maintains a parallel sprinkler pipe network; it references MEP systems and elements and records their fire/life-safety role as represented data.",
 "barrier_types": [
  "FIRE_BARRIER",
  "SMOKE_BARRIER",
  "FIRE_PARTITION",
  "FIRE_WALL",
  "SHAFT_ENCLOSURE",
  "OTHER",
  "UNKNOWN"
 ],
 "barrier_note": "an architectural wall is not a fire barrier and a structural wall is not a fire barrier. A barrier exists only where the model explicitly classifies one, and it references its host wall rather than creating new geometry.",
 "opening_types": [
  "FIRE_DOOR",
  "SMOKE_DOOR",
  "FIRE_DAMPER",
  "FIRE_SHUTTER",
  "GLAZED_ASSEMBLY",
  "OTHER",
  "UNKNOWN"
 ],
 "opening_note": "a normal architectural door is NOT a fire door. A fire door exists only where the model explicitly says so, and it references the architectural opening it classifies.",
 "protection_statuses": [
  "unknown",
  "declared_protected",
  "declared_unprotected"
 ],
 "protection_note": "a stair is never classified as a protected stair automatically, and a shaft is never assumed to be fire-rated. Without explicit data the status stays unknown.",
 "rating_note": "rating_minutes is carried only when the model supplies it. It is never inferred from a material, a thickness, an element type or a building type, and it is never validated or calculated. Unknown means null.",
 "smoke_control_kinds": [
  "smoke_exhaust",
  "pressurization",
  "smoke_barrier",
  "smoke_zone",
  "other"
 ],
 "smoke_control_note": "these are DATA PLACEHOLDERS. No smoke modelling, airflow calculation or pressurisation analysis exists in this platform.",
 "relationship_types": [
  "DEVICE_IN_SPACE",
  "DEVICE_ON_SYSTEM",
  "DEVICE_CONNECTED_TO_LOOP",
  "PANEL_CONTROLS_DEVICE",
  "DEVICE_IN_ALARM_ZONE",
  "SYSTEM_HAS_DEVICE",
  "EXIT_SERVES_LEVEL",
  "SIGN_INDICATES_EXIT",
  "BARRIER_CONTAINS_OPENING",
  "FIRE_DOOR_HOSTED_BY_BARRIER",
  "ZONE_CONTAINS_SPACE",
  "STAIR_REFERENCES_CORE",
  "ASSEMBLY_POINT_ON_SITE"
 ],
 "relationship_statuses": [
  "confirmed",
  "inferred",
  "unresolved"
 ],
 "relationship_note": "these edges are factual only. A represented detector in a space is NOT coverage of that space, and a represented sprinkler head in a space is NOT protection of that space. No edge here asserts coverage, protection, adequacy or compliance.",
 "semantics": [
  "DEVICE_PRESENT is not COVERAGE_CONFIRMED",
  "SYSTEM_PRESENT is not SYSTEM_ADEQUATE",
  "EXIT_PRESENT is not EGRESS_COMPLIANT",
  "BARRIER_PRESENT is not FIRE_SEPARATION_COMPLIANT",
  "SIGN_PRESENT is not SIGNAGE_ADEQUATE",
  "RATING_STATED is not RATING_VERIFIED"
 ],
 "issue_severities": [
  "INFO",
  "WARNING",
  "ERROR"
 ],
 "severity_note": "these are model-quality severities for data integrity. UNSAFE / CODE VIOLATION / FIRE VIOLATION / NON_COMPLIANT are deliberately absent. The absence of a sprinkler system, a fire alarm or a fire door is NEVER an issue in this layer: absence is not a violation without a verified rule.",
 "issue_codes": {
  "DUPLICATE_ELEMENT_ID": "ERROR",
  "UNSUPPORTED_ELEMENT_TYPE": "WARNING",
  "UNKNOWN_DEVICE_TYPE": "WARNING",
  "UNKNOWN_BARRIER_TYPE": "WARNING",
  "UNKNOWN_OPENING_TYPE": "WARNING",
  "INVALID_SYSTEM_REF": "ERROR",
  "INVALID_MEP_ELEMENT_REF": "ERROR",
  "INVALID_LEVEL_REF": "ERROR",
  "INVALID_SPACE_REF": "ERROR",
  "INVALID_EXIT_REF": "ERROR",
  "INVALID_HOST_WALL_REF": "ERROR",
  "INVALID_HOST_OPENING_REF": "ERROR",
  "INVALID_CORE_REF": "ERROR",
  "INVALID_ZONE_SPACE_REF": "ERROR",
  "INVALID_BARRIER_REF": "ERROR",
  "INVALID_RATING_VALUE": "ERROR",
  "CROSS_BUILDING_REF": "ERROR",
  "NAN_COORDINATE": "ERROR",
  "DEVICE_OUTSIDE_SPACE": "WARNING",
  "DEVICE_IN_FLOOR_OPENING": "INFO",
  "SIGN_TARGET_MISSING": "ERROR",
  "FIRE_DOOR_NOT_HOSTED": "WARNING",
  "BARRIER_WITHOUT_HOST": "WARNING",
  "ASSEMBLY_POINT_INSIDE_BUILDING": "WARNING",
  "RATING_UNKNOWN": "INFO",
  "PROTECTION_UNKNOWN": "INFO",
  "DEVICE_WITHOUT_SYSTEM": "INFO",
  "ZONE_WITHOUT_SPACES": "INFO"
 },
 "display_fallbacks": {
  "device_size_m": 0.12,
  "sign_w_m": 0.3,
  "sign_h_m": 0.15,
  "barrier_marker_thickness_m": 0.05,
  "assembly_point_size_m": 2.0
 },
 "display_fallback_note": "DISPLAY VALUE IS NOT AN ENGINEERING VALUE. Device and sign geometry is a drawing convenience: the semantic dimension stays null, the renderer reads these numbers tagged source=display_fallback, and the fallback never reaches an export as engineering metadata and never reaches a rule input.",
 "render_modes": [
  "emitted",
  "referenced"
 ],
 "render_note": "an element adapted from MEP or from a Phase 1 point is rendered as REFERENCED: the MEP or Phase 1 layer already draws it and this layer emits no second geometry for it. Only elements that exist nowhere else — a declared exit sign, a declared barrier marker, a declared assembly point — are EMITTED.",
 "render_layers": [
  "FLS_DETECTION",
  "FLS_ALARM",
  "FLS_SUPPRESSION",
  "FLS_FIRE_WATER",
  "FLS_EMERGENCY_LIGHTING",
  "FLS_SIGNAGE",
  "FLS_BARRIER",
  "FLS_FIRE_DOOR",
  "FLS_ZONE",
  "FLS_OTHER"
 ],
 "colour_note": "colour distinguishes element type only. No colour in this layer means safe, failed, compliant or non-compliant, and there is no red-means-violation logic anywhere.",
 "forbidden_claims": [
  "protected",
  "covered",
  "coverage_confirmed",
  "coverage_radius",
  "spacing_ok",
  "adequate",
  "compliant",
  "code_required",
  "certified",
  "approved",
  "fire_resistance_verified",
  "design_density",
  "k_factor",
  "hydraulic_calculation",
  "fire_water_demand",
  "demand_area",
  "candela",
  "sound_level_db",
  "audibility",
  "travel_distance_limit",
  "occupant_load",
  "meets_nfpa",
  "meets_sbc",
  "meets_ibc",
  "meets_civil_defense"
 ],
 "id_patterns": {
  "zone": "<bid>.fls.zone_<n>",
  "barrier": "<bid>.fls.barrier_<n>",
  "opening": "<bid>.fls.open_<n>",
  "exit": "<bid>.fls.exit_<n>",
  "stair": "<bid>.fls.stair_<n>",
  "shaft": "<bid>.fls.shaft_<n>",
  "device": "<bid>.fls.dev_<n>",
  "system": "<bid>.fls.sys_<n>",
  "sign": "<bid>.fls.sign_<n>",
  "assembly_point": "<bid>.fls.assembly_<n>",
  "refuge_area": "<bid>.fls.refuge_<n>",
  "smoke_control": "<bid>.fls.smoke_<n>",
  "relationship": "<bid>.fls.rel_<n>",
  "adapted_device": "<bid>.fls.mep_<mep_element_id>"
 },
 "id_note": "an id supplied by the model is kept and namespaced with the building id; an id that is absent is generated from the element's canonical sort position, so the same model always yields the same ids. Two buildings can never collide. Site pathfinding between buildings and to assembly points is out of scope in this phase.",
 "source_of_truth": "the egress foundation remains the source of truth for represented exits, the MEP model for fire system topology and devices, the architectural model for walls, openings and cores, and the structural model for members. This layer references all of them and edits none of them. There is no second exit-inference engine.",
 "navigation_note": "fire and life-safety objects are NOT navigation obstacles and do NOT change egress selection or routing in this phase. Navigation, egress and walking-distance results are unchanged by the presence of an FLS model, deliberately and by design.",
 "distance_note": "no fire-code travel distance exists. Real walking distance stays purely geometric; this layer may quote a measured distance_status and walking_distance_m as factual data and never compares them to any limit.",
 "occupancy_note": "a building programme is NOT a fire occupancy classification. Only a verified regulatory occupancy could ever be referenced, and the verified regulatory occupancy count in this platform is still zero.",
 "no_generator_note": "this phase ships NO fire engine, NO fire simulation, NO automatic device placement, NO automatic zoning, NO automatic loop design and NO auto-fix. Every zone, barrier, fire door, device, sign, assembly point and refuge area exists only because the model supplied it or because an existing object was referenced through a declared adapter."
};
const FLS_SCHEMA = ACS_FLS_SPEC.schema;
const FLS_COMPILER_VERSION = ACS_FLS_SPEC.compiler_version;
const FLS_ELEMENT_TYPES = ACS_FLS_SPEC.element_types;
const FLS_MODEL_STATUS = ACS_FLS_SPEC.model_status;
const FLS_PROVENANCE = ACS_FLS_SPEC.provenance_values;
const FLS_FORBIDDEN_PROVENANCE = ACS_FLS_SPEC.forbidden_provenance;
const FLS_VERIFIED_SOURCES = ACS_FLS_SPEC.verified_sources;
const FLS_ADAPTER_ORIGINS = ACS_FLS_SPEC.adapter_origins;
const FLS_DEVICE_TYPES = ACS_FLS_SPEC.device_types;
const FLS_DEVICE_CATEGORY = ACS_FLS_SPEC.device_categories;
const FLS_DEVICE_CATEGORIES = ACS_FLS_SPEC.device_categories_list;
const FLS_MEP_DEVICE_MAP = ACS_FLS_SPEC.mep_device_map;
const FLS_MEP_EQUIPMENT_MAP = ACS_FLS_SPEC.mep_equipment_map;
const FLS_REFERENCED_MEP_SYSTEMS = ACS_FLS_SPEC.referenced_mep_systems;
const FLS_BARRIER_TYPES = ACS_FLS_SPEC.barrier_types;
const FLS_OPENING_TYPES = ACS_FLS_SPEC.opening_types;
const FLS_PROTECTION_STATUSES = ACS_FLS_SPEC.protection_statuses;
const FLS_SMOKE_CONTROL_KINDS = ACS_FLS_SPEC.smoke_control_kinds;
const FLS_REL_TYPES = ACS_FLS_SPEC.relationship_types;
const FLS_REL_STATUSES = ACS_FLS_SPEC.relationship_statuses;
const FLS_SEVERITIES = ACS_FLS_SPEC.issue_severities;
const FLS_ISSUE_CODES = ACS_FLS_SPEC.issue_codes;
const FLS_FALLBACKS = ACS_FLS_SPEC.display_fallbacks;
const FLS_RENDER_LAYERS = ACS_FLS_SPEC.render_layers;
const _F_EPS = 1e-6;
const _F_TOL = 0.15;
const _FLS_LAYER_OF = {DETECTION:'FLS_DETECTION', ALARM:'FLS_ALARM',
  SUPPRESSION:'FLS_SUPPRESSION', FIRE_WATER:'FLS_FIRE_WATER',
  EMERGENCY_LIGHTING:'FLS_EMERGENCY_LIGHTING', SIGNAGE:'FLS_SIGNAGE', OTHER:'FLS_OTHER'};

function flsSeverityOf(code){
  return Object.prototype.hasOwnProperty.call(FLS_ISSUE_CODES,code)
    ?FLS_ISSUE_CODES[code]:'WARNING'; }
function _fnum(v){ return _snum(v); }
function _fBadNumber(v){ return _sBadNumber(v); }
/* CODE_REQUIRED و RULE ممنوعتان هنا: لا دليل قاعدة حريق مُتحقَّق منه في المنصّة */
function _fsrc(v,dflt){
  const s=(v===null||v===undefined)?(dflt||'unknown'):String(v).toLowerCase();
  if(FLS_FORBIDDEN_PROVENANCE.indexOf(s)>=0) return 'unknown';
  return FLS_PROVENANCE.indexOf(s)>=0?s:'unknown'; }
function _fraw(building){
  const f=building.fire_life_safety;
  return (f&&typeof f==='object'&&!Array.isArray(f))?f:{}; }
function _fnid(bid,given,prefix,n){
  if(_pyT(given)){
    const s=String(given);
    if(s.indexOf(bid+'.')===0) return s;
    const head=s.split('.')[0];
    if(head.indexOf('bld_')===0&&head!==bid) return s;
    return bid+'.fls.'+s; }
  return bid+'.fls.'+prefix+'_'+n; }
function _fLevelsIndex(building,bid){
  const idx=new Map();
  _aLevels(building,bid).forEach(l=>{ idx.set('#'+l.index,l); idx.set('$'+String(l.id),l); });
  return idx; }
function _fLevelOf(idx,ref){
  if(ref===null||ref===undefined||typeof ref==='boolean') return null;
  if(typeof ref==='number') return idx.get('#'+Math.trunc(ref))||null;
  return idx.get('$'+String(ref))||null; }
function _fSpaceIndex(arch){
  const idx=new Map();
  ((arch||{}).spaces||[]).forEach(s=>{ idx.set(s.id,s);
    if(_pyT(s.space_id)&&!idx.has(s.space_id)) idx.set(s.space_id,s); });
  return idx; }
/* مدّة المقاومة المذكورة فقط. لا تُستنتج من مادة ولا تُحسب ولا تُتحقّق */
function _frating(v){
  const n=_fnum(v);
  if(n===null) return {value:null,source:'unknown',
    note:'rating is never inferred from a material or an element type'};
  return {value:n,source:'imported',
    note:'stated by the model; not verified and not calculated'}; }
function _fprops(props,source){
  const out={};
  if(props&&typeof props==='object'&&!Array.isArray(props))
    Object.keys(props).sort(_scmp).forEach(k=>{
      out[String(k)]={value:props[k],source:_fsrc(source,'imported')}; });
  return out; }
/* ------------------------------------------------------------- الأنظمة --- */
/* مراجع إلى أنظمة MEP ذات دور حريق/سلامة. لا طوبولوجيا موازية */
function _fSystems(raw,bid,mep){
  const out=[];
  const mepSys=new Map(((mep||{}).systems||[]).map(s=>[s.id,s]));
  const seen=new Set();
  (_pyT(raw.systems)?raw.systems:[]).forEach((s,n)=>{
    const ref=_pyT(s.mep_system_id)?s.mep_system_id:(_pyT(s.system_id)?s.system_id:null);
    const full=_pyT(ref)?_mnid(bid,ref,'sys',0):null;
    const m=(full!==null)?(mepSys.get(full)||null):null;
    seen.add(full);
    out.push({id:_fnid(bid,s.id,'sys',n), type:'FLS_SYSTEM', building_id:bid,
      mep_system_id:full, mep_system_resolved:m!==null,
      mep_system_type:m?m.system_type:null,
      role:String(_pyT(s.role)?s.role:'unknown').toLowerCase(),
      name:(s.name===undefined)?null:s.name,
      status:_pyT(s.status)?String(s.status).toUpperCase():null,
      origin:'model', source:_fsrc(s.source),
      note:'a represented system is not an operational, complete or adequate system'}); });
  /* مراجع تلقائية لأنظمة MEP الحريقية الموجودة — إشارة لا تكرار */
  ((mep||{}).systems||[]).forEach(m=>{
    if(FLS_REFERENCED_MEP_SYSTEMS.indexOf(m.system_type)>=0&&!seen.has(m.id))
      out.push({id:bid+'.fls.mep_'+String(m.id).split('.mep.').slice(-1)[0],
        type:'FLS_SYSTEM', building_id:bid,
        mep_system_id:m.id, mep_system_resolved:true,
        mep_system_type:m.system_type, role:'unknown',
        name:(m.name===undefined)?null:m.name,
        status:null, origin:'mep_adapter',
        /* إسناد نظام MEP ينتقل كما هو ولا يُرقّى */
        original_source:m.source, source:'mep_adapter',
        note:'referenced from the MEP model; the MEP model remains the source of '+
             'truth for its topology'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------- الأجهزة --- */
function _fDeviceCommon(bid,dtype,origin){
  const cat=Object.prototype.hasOwnProperty.call(FLS_DEVICE_CATEGORY,dtype)
    ?FLS_DEVICE_CATEGORY[dtype]:'OTHER';
  return {type:'FLS_DEVICE', building_id:bid, device_type:dtype, device_category:cat,
    render_layer:_FLS_LAYER_OF[cat]||'FLS_OTHER', origin:origin}; }
function _fMepHas(mep,bid,ref){
  if(!mep||ref===null||ref===undefined) return false;
  const full=_mnid(bid,ref,'term',0);
  const keys=['terminals','adapted_terminals','equipment','nodes','segments'];
  for(const key of keys) for(const e of (mep[key]||[]))
    if(e.id===ref||e.id===full) return true;
  return false; }
function _fDevices(raw,bid,levelsIdx,spaceIdx,sysIds,mep){
  const out=[];
  (_pyT(raw.devices)?raw.devices:[]).forEach((d,n)=>{
    const lvl=_fLevelOf(levelsIdx,d.level);
    const t=String(_pyT(d.type)?d.type:'OTHER').toUpperCase();
    const known=FLS_DEVICE_TYPES.indexOf(t)>=0;
    const pos=(d.position&&typeof d.position==='object'&&!Array.isArray(d.position))?d.position:d;
    let y=_fnum(pos.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    const sp=_pyT(d.space)?d.space:(_pyT(d.space_id)?d.space_id:null);
    const sid=(d.system_id===undefined)?null:d.system_id;
    const e=_fDeviceCommon(bid,known?t:'OTHER','model');
    e.id=_fnid(bid,d.id,'dev',n);
    e.declared_type=(d.type===undefined)?null:d.type;
    e.device_type_recognised=known;
    e.system_id=_pyT(sid)?_fnid(bid,sid,'sys',0):null;
    e.system_resolved=(sid===null||sid===undefined)||sysIds.has(_fnid(bid,sid,'sys',0));
    /* مرجع صريح إلى عنصر MEP قائم — يُتحقّق منه ولا يُختلق */
    e.mep_element_id=(d.mep_element_id===undefined)?null:d.mep_element_id;
    e.mep_element_resolved=(d.mep_element_id===null||d.mep_element_id===undefined)
      ?null:_fMepHas(mep,bid,d.mep_element_id);
    e.x=_fnum(pos.x); e.y=y; e.z=_fnum(pos.z);
    e.raw_x=(pos.x===undefined)?null:pos.x; e.raw_z=(pos.z===undefined)?null:pos.z;
    e.level_ref=(d.level===undefined)?null:d.level;
    e.level_id=lvl?lvl.id:null; e.level_index=lvl?lvl.index:null;
    e.level_resolved=(lvl!==null)||(d.level===null||d.level===undefined);
    e.space_ref=sp; e.space_id=sp?((spaceIdx.get(String(sp))||{}).id||null):null;
    e.space_resolved=(sp===null)||spaceIdx.has(String(sp));
    e.loop_ref=(d.loop===undefined)?null:d.loop;
    e.panel_ref=(d.panel===undefined)?null:d.panel;
    e.alarm_zone_ref=(d.alarm_zone===undefined)?null:d.alarm_zone;
    /* لا نصف قطر تغطية ولا حرارة تشغيل ولا K ولا ضغط ولا تدفّق ولا شمعة */
    e.properties=_fprops(d.properties,d.source);
    e.status=_pyT(d.status)?String(d.status).toUpperCase():null;
    e.source=_fsrc(d.source);
    e.note='a represented device is not coverage, protection or compliance';
    out.push(e); });
  /* محوّل MEP: كل نهاية/معدّة حريقية موجودة تُشار إليها ولا تُنسخ */
  ((mep||{}).terminals||[]).concat((mep||{}).adapted_terminals||[]).forEach(t=>{
    const mapped=Object.prototype.hasOwnProperty.call(FLS_MEP_DEVICE_MAP,t.terminal_type)
      ?FLS_MEP_DEVICE_MAP[t.terminal_type]:null;
    if(mapped===null) return;
    const e=_fDeviceCommon(bid,mapped,
      (t.origin!=='phase1_point')?'mep_adapter':'phase1_adapter');
    e.id=bid+'.fls.mep_'+String(t.id).split('.mep.').slice(-1)[0];
    e.declared_type=(t.terminal_type===undefined)?null:t.terminal_type;
    e.device_type_recognised=true;
    e.system_id=null; e.system_resolved=true;
    e.mep_element_id=t.id; e.mep_element_resolved=true;
    e.mep_system_id=(t.system_id===undefined)?null:t.system_id;
    e.x=(t.x===undefined)?null:t.x; e.y=(t.y===undefined)?null:t.y;
    e.z=(t.z===undefined)?null:t.z;
    e.raw_x=(t.raw_x===undefined)?null:t.raw_x; e.raw_z=(t.raw_z===undefined)?null:t.raw_z;
    e.level_ref=(t.level_ref===undefined)?null:t.level_ref;
    e.level_id=(t.level_id===undefined)?null:t.level_id;
    e.level_index=(t.level_index===undefined)?null:t.level_index;
    e.level_resolved=(t.level_resolved===undefined)?null:t.level_resolved;
    e.space_ref=(t.space_ref===undefined)?null:t.space_ref;
    e.space_id=(t.space_id===undefined)?null:t.space_id;
    e.space_resolved=(t.space_resolved===undefined)?null:t.space_resolved;
    e.loop_ref=null; e.panel_ref=null; e.alarm_zone_ref=null;
    e.properties={}; e.status=null;
    /* إسناد العنصر الأصلي ينتقل كما هو ولا يُرقّى أبداً */
    e.original_source=_pyT(t.original_source)?t.original_source:t.source;
    e.source=(t.origin==='phase1_point')?'phase1_adapter':'mep_adapter';
    e.note='referenced from the MEP model; no second geometry is created and the '+
           'original provenance is carried through unchanged';
    out.push(e); });
  ((mep||{}).equipment||[]).forEach(eq=>{
    const mapped=Object.prototype.hasOwnProperty.call(FLS_MEP_EQUIPMENT_MAP,eq.equipment_type)
      ?FLS_MEP_EQUIPMENT_MAP[eq.equipment_type]:null;
    if(mapped===null) return;
    const e=_fDeviceCommon(bid,mapped,'mep_adapter');
    e.id=bid+'.fls.mep_'+String(eq.id).split('.mep.').slice(-1)[0];
    e.declared_type=(eq.equipment_type===undefined)?null:eq.equipment_type;
    e.device_type_recognised=true;
    e.system_id=null; e.system_resolved=true;
    e.mep_element_id=eq.id; e.mep_element_resolved=true;
    e.mep_system_id=(eq.system_id===undefined)?null:eq.system_id;
    e.x=(eq.x===undefined)?null:eq.x; e.y=(eq.y===undefined)?null:eq.y;
    e.z=(eq.z===undefined)?null:eq.z;
    e.raw_x=(eq.raw_x===undefined)?null:eq.raw_x; e.raw_z=(eq.raw_z===undefined)?null:eq.raw_z;
    e.level_ref=(eq.level_ref===undefined)?null:eq.level_ref;
    e.level_id=(eq.level_id===undefined)?null:eq.level_id;
    e.level_index=(eq.level_index===undefined)?null:eq.level_index;
    e.level_resolved=(eq.level_resolved===undefined)?null:eq.level_resolved;
    e.space_ref=(eq.space_ref===undefined)?null:eq.space_ref;
    e.space_id=(eq.space_id===undefined)?null:eq.space_id;
    e.space_resolved=(eq.space_resolved===undefined)?null:eq.space_resolved;
    e.loop_ref=null; e.panel_ref=null; e.alarm_zone_ref=null;
    e.properties={}; e.status=null;
    e.original_source=eq.source; e.source='mep_adapter';
    e.note='referenced from the MEP model; no second geometry is created';
    out.push(e); });
  out.sort(_byId); return out; }
/* -------------------------------------------------- المخارج والدرج والمنور --- */
/* المخارج تأتي من أساس الإخلاء وحده. لا محرّك استنتاج مخارج ثانٍ هنا */
function _fExits(raw,bid,building,rels,arch,levelsIdx){
  let egExits=[];
  try{ egExits=extractExits(building,rels,bid); }catch(e){ egExits=[]; }
  const idx=new Map(egExits.map(e=>[e.id,e]));
  const out=[], seen=new Set();
  (_pyT(raw.exits)?raw.exits:[]).forEach((x,n)=>{
    const ref=_pyT(x.exit_id)?x.exit_id:(_pyT(x.exit_ref)?x.exit_ref:null);
    const e=(ref!==null)?(idx.get(ref)||null):null;
    seen.add(ref);
    out.push({id:_fnid(bid,x.id,'exit',n), type:'FLS_EXIT', building_id:bid,
      exit_ref:ref, exit_resolved:e!==null,
      space_id:e?((e.space===undefined)?null:e.space):((x.space===undefined)?null:x.space),
      level_id:e?((e.level===undefined)?null:e.level):((x.level===undefined)?null:x.level),
      destination:e?((e.destination===undefined)?null:e.destination):null,
      egress_status:e?((e.status===undefined)?null:e.status):null,
      via:e?((e.via===undefined)?null:e.via):null,
      properties:_fprops(x.properties,x.source),
      origin:'model', source:_fsrc(x.source),
      note:'a represented exit is not a compliant means of egress'}); });
  egExits.forEach(e=>{
    if(seen.has(e.id)) return;
    out.push({id:bid+'.fls.eg_'+String(e.id).split('.').slice(-1)[0],
      type:'FLS_EXIT', building_id:bid,
      exit_ref:e.id, exit_resolved:true,
      space_id:(e.space===undefined)?null:e.space,
      level_id:(e.level===undefined)?null:e.level,
      destination:(e.destination===undefined)?null:e.destination,
      egress_status:(e.status===undefined)?null:e.status,
      via:(e.via===undefined)?null:e.via, properties:{},
      origin:'egress_adapter',
      original_source:(e.source===undefined)?null:e.source, source:'egress_adapter',
      note:'referenced from the egress foundation, which remains the source of truth'}); });
  out.sort(_byId); return out; }
/* درج مُشار إليه من النوى المعمارية. لا تصنيف تلقائي كدرج محمي */
function _fStairs(raw,bid,arch){
  const cores=new Map(((arch||{}).cores||[]).map(c=>[c.id,c]));
  const out=[], seen=new Set();
  (_pyT(raw.stairs)?raw.stairs:[]).forEach((s,n)=>{
    const ref=_pyT(s.core_id)?s.core_id:(_pyT(s.arch_core_id)?s.arch_core_id:null);
    const c=(ref!==null)?(cores.get(ref)||null):null;
    seen.add(ref);
    const prot=String(_pyT(s.protection_status)?s.protection_status:'unknown').toLowerCase();
    out.push({id:_fnid(bid,s.id,'stair',n), type:'FLS_STAIR', building_id:bid,
      core_id:ref, core_resolved:c!==null, core_type:c?c.type:null,
      served_levels:(c&&c.served_levels)?c.served_levels.slice():[],
      /* لا يصير محمياً إلا بتصريح معلن */
      protection_status:(FLS_PROTECTION_STATUSES.indexOf(prot)>=0)?prot:'unknown',
      enclosure_barrier_ref:(s.enclosure_barrier===undefined)?null:s.enclosure_barrier,
      rating_minutes:_frating(s.rating_minutes),
      origin:'model', source:_fsrc(s.source),
      note:'a stair is never classified as a protected stair automatically'}); });
  ((arch||{}).cores||[]).forEach(c=>{
    if(seen.has(c.id)||c.type!=='STAIR') return;
    out.push({id:bid+'.fls.core_'+String(c.id).split('.').slice(-1)[0],
      type:'FLS_STAIR', building_id:bid,
      core_id:c.id, core_resolved:true, core_type:c.type,
      served_levels:(c.served_levels||[]).slice(),
      protection_status:'unknown', enclosure_barrier_ref:null,
      rating_minutes:_frating(null),
      origin:'arch_adapter', source:'arch_adapter',
      note:'referenced from the architectural cores; protection is unknown, not assumed'}); });
  out.sort(_byId); return out; }
function _fShafts(raw,bid,arch,mep){
  const cores=new Map(((arch||{}).cores||[]).map(c=>[c.id,c]));
  const risers=new Map(((mep||{}).risers||[]).map(r=>[r.id,r]));
  const out=[];
  (_pyT(raw.shafts)?raw.shafts:[]).forEach((s,n)=>{
    const ref=_pyT(s.core_id)?s.core_id:(_pyT(s.riser_id)?s.riser_id:null);
    const c=(ref!==null)?(cores.get(ref)||risers.get(ref)||null):null;
    const prot=String(_pyT(s.protection_status)?s.protection_status:'unknown').toLowerCase();
    out.push({id:_fnid(bid,s.id,'shaft',n), type:'FLS_SHAFT', building_id:bid,
      host_ref:ref, host_resolved:c!==null,
      host_kind:cores.has(ref)?'arch_core':(risers.has(ref)?'mep_riser':'unknown'),
      protection_status:(FLS_PROTECTION_STATUSES.indexOf(prot)>=0)?prot:'unknown',
      rating_minutes:_frating(s.rating_minutes),
      origin:'model', source:_fsrc(s.source),
      note:'a shaft is not assumed to be fire-rated'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------- الحواجز وفتحاتها --- */
function _fBarriers(raw,bid,arch,levelsIdx){
  const walls=new Set(((arch||{}).walls||[]).map(w=>w.id));
  const out=[];
  (_pyT(raw.barriers)?raw.barriers:[]).forEach((b,n)=>{
    const t=String(_pyT(b.type)?b.type:'UNKNOWN').toUpperCase();
    const host=_pyT(b.host_wall_id)?b.host_wall_id:(_pyT(b.host_wall)?b.host_wall:null);
    const hosts=(_pyT(b.host_wall_ids)?b.host_wall_ids:(_pyT(host)?[host]:[])).slice();
    const resolved=hosts.filter(h=>walls.has(h));
    out.push({id:_fnid(bid,b.id,'barrier',n), type:'FLS_BARRIER', building_id:bid,
      barrier_type:(FLS_BARRIER_TYPES.indexOf(t)>=0)?t:'OTHER',
      declared_type:(b.type===undefined)?null:b.type,
      barrier_type_recognised:FLS_BARRIER_TYPES.indexOf(t)>=0,
      host_wall_ids:hosts, resolved_host_wall_ids:resolved,
      hosts_resolved:hosts.length>0&&resolved.length===hosts.length,
      level_refs:(_pyT(b.levels)?b.levels:[]).slice(),
      rating_minutes:_frating(b.rating_minutes),
      continuity:String(_pyT(b.continuity)?b.continuity:'unknown').toLowerCase(),
      origin:'model', source:_fsrc(b.source),
      note:'an architectural or structural wall is never a fire barrier without '+
           'explicit classification'}); });
  out.sort(_byId); return out; }
function _fOpenings(raw,bid,arch,barrierIds){
  const ops=new Map(((arch||{}).openings||[]).map(o=>[o.id,o]));
  const refs=new Map();
  ((arch||{}).openings||[]).forEach(o=>{ if(!refs.has(o.opening_ref)) refs.set(o.opening_ref,o); });
  const out=[];
  (_pyT(raw.openings)?raw.openings:[]).forEach((p,n)=>{
    const t=String(_pyT(p.type)?p.type:'UNKNOWN').toUpperCase();
    const host=_pyT(p.arch_opening_id)?p.arch_opening_id
      :(_pyT(p.opening_id)?p.opening_id:(_pyT(p.door_id)?p.door_id:null));
    const a=(host!==null)?(ops.get(host)||refs.get(host)||null):null;
    const bref=(p.barrier_id===undefined)?null:p.barrier_id;
    out.push({id:_fnid(bid,p.id,'open',n), type:'FLS_OPENING', building_id:bid,
      opening_type:(FLS_OPENING_TYPES.indexOf(t)>=0)?t:'OTHER',
      declared_type:(p.type===undefined)?null:p.type,
      opening_type_recognised:FLS_OPENING_TYPES.indexOf(t)>=0,
      arch_opening_id:host, arch_opening_resolved:a!==null,
      resolved_opening_id:a?a.id:null, arch_opening_type:a?a.type:null,
      barrier_id:_pyT(bref)?_fnid(bid,bref,'barrier',0):null,
      barrier_resolved:(bref===null||bref===undefined)||barrierIds.has(_fnid(bid,bref,'barrier',0)),
      fire_door:(p.fire_door===true)||t==='FIRE_DOOR',
      rating_minutes:_frating(p.rating_minutes),
      self_closing:(typeof p.self_closing==='boolean')?p.self_closing:null,
      smoke_controlled:(typeof p.smoke_controlled==='boolean')?p.smoke_controlled:null,
      origin:'model', source:_fsrc(p.source),
      note:'a normal architectural door is not a fire door; this classification is '+
           'explicit model data and is not evaluated against any code'}); });
  out.sort(_byId); return out; }
/* --------------------------------------------- المناطق واللافتات وغيرها --- */
function _fZones(raw,bid,levelsIdx,spaceIdx){
  const out=[];
  (_pyT(raw.zones)?raw.zones:[]).forEach((z,n)=>{
    const lrefs=(_pyT(z.level_ids)?z.level_ids:(_pyT(z.levels)?z.levels:[])).slice();
    const lv=lrefs.map(r=>_fLevelOf(levelsIdx,r));
    const sp=(_pyT(z.space_ids)?z.space_ids:(_pyT(z.spaces)?z.spaces:[])).slice();
    out.push({id:_fnid(bid,z.id,'zone',n), type:'FLS_ZONE', building_id:bid,
      name:(z.name===undefined)?null:z.name,
      zone_kind:String(_pyT(z.kind)?z.kind:'fire_compartment').toLowerCase(),
      level_refs:lrefs, level_ids:lv.filter(Boolean).map(l=>l.id),
      levels_resolved:lv.every(l=>l!==null),
      space_ids:sp, resolved_space_ids:sp.filter(s=>spaceIdx.has(String(s))),
      spaces_resolved:sp.every(s=>spaceIdx.has(String(s))),
      boundary_refs:(_pyT(z.boundary_refs)?z.boundary_refs:[]).slice(),
      rating_minutes:_frating(z.rating_minutes),
      origin:'model', source:_fsrc(z.source),
      note:'a compartment is never inferred from room boundaries'}); });
  out.sort(_byId); return out; }
function _fSigns(raw,bid,levelsIdx,spaceIdx,exitRefs){
  const out=[];
  (_pyT(raw.signs)?raw.signs:[]).forEach((s,n)=>{
    const lvl=_fLevelOf(levelsIdx,s.level);
    const pos=(s.position&&typeof s.position==='object'&&!Array.isArray(s.position))?s.position:s;
    let y=_fnum(pos.y);
    if(y===null&&lvl!==null) y=lvl.elevation_m;
    const sp=_pyT(s.space)?s.space:(_pyT(s.space_id)?s.space_id:null);
    const tgt=_pyT(s.indicates_exit)?s.indicates_exit:(_pyT(s.exit_id)?s.exit_id:null);
    out.push({id:_fnid(bid,s.id,'sign',n), type:'FLS_SIGN', building_id:bid,
      sign_kind:String(_pyT(s.kind)?s.kind:'exit_sign').toLowerCase(),
      indicates_exit:tgt, target_resolved:_pyT(tgt)?exitRefs.has(tgt):null,
      x:_fnum(pos.x), y:y, z:_fnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      level_ref:(s.level===undefined)?null:s.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(s.level===null||s.level===undefined),
      space_ref:sp, space_id:sp?((spaceIdx.get(String(sp))||{}).id||null):null,
      space_resolved:(sp===null)||spaceIdx.has(String(sp)),
      illuminated:(typeof s.illuminated==='boolean')?s.illuminated:null,
      origin:'model', source:_fsrc(s.source),
      note:'whether signage is required or adequate is never determined here'}); });
  out.sort(_byId); return out; }
function _fPoints(raw,bid,key,prefix,etype,levelsIdx,spaceIdx,note){
  const out=[];
  (_pyT(raw[key])?raw[key]:[]).forEach((p,n)=>{
    const lvl=_fLevelOf(levelsIdx,p.level);
    const pos=(p.position&&typeof p.position==='object'&&!Array.isArray(p.position))?p.position:p;
    const sp=_pyT(p.space)?p.space:(_pyT(p.space_id)?p.space_id:null);
    out.push({id:_fnid(bid,p.id,prefix,n), type:etype, building_id:bid,
      name:(p.name===undefined)?null:p.name,
      scope:String(_pyT(p.scope)?p.scope
        :((etype==='FLS_ASSEMBLY_POINT')?'site':'building')).toLowerCase(),
      x:_fnum(pos.x), z:_fnum(pos.z),
      raw_x:(pos.x===undefined)?null:pos.x, raw_z:(pos.z===undefined)?null:pos.z,
      level_ref:(p.level===undefined)?null:p.level,
      level_id:lvl?lvl.id:null, level_index:lvl?lvl.index:null,
      level_resolved:(lvl!==null)||(p.level===null||p.level===undefined),
      space_ref:sp, space_id:sp?((spaceIdx.get(String(sp))||{}).id||null):null,
      space_resolved:(sp===null)||spaceIdx.has(String(sp)),
      capacity_persons:null,
      properties:_fprops(p.properties,p.source),
      origin:'model', source:_fsrc(p.source), note:note}); });
  out.sort(_byId); return out; }
function _fSmokeControl(raw,bid,levelsIdx){
  const out=[];
  (_pyT(raw.smoke_control)?raw.smoke_control:[]).forEach((s,n)=>{
    const k=String(_pyT(s.kind)?s.kind:'other').toLowerCase();
    const lrefs=(_pyT(s.levels)?s.levels:[]).slice();
    const lv=lrefs.map(r=>_fLevelOf(levelsIdx,r));
    out.push({id:_fnid(bid,s.id,'smoke',n), type:'FLS_SMOKE_CONTROL', building_id:bid,
      kind:(FLS_SMOKE_CONTROL_KINDS.indexOf(k)>=0)?k:'other',
      declared_kind:(s.kind===undefined)?null:s.kind,
      level_refs:lrefs, level_ids:lv.filter(Boolean).map(l=>l.id),
      levels_resolved:lv.every(l=>l!==null),
      space_ids:(_pyT(s.spaces)?s.spaces:[]).slice(),
      system_ref:(s.system_id===undefined)?null:s.system_id,
      properties:_fprops(s.properties,s.source),
      origin:'model', source:_fsrc(s.source),
      note:'a data placeholder only — no smoke modelling, airflow or pressurisation '+
           'analysis exists'}); });
  out.sort(_byId); return out; }
/* ------------------------------------------------------------ العلاقات --- */
function _fRelationships(bid,systems,devices,exits,stairs,barriers,openings,zones,signs,
                         assembly,refuge,arch,issues){
  const rels=[]; let seq=0;
  const add=(rtype,frm,to,status,basis,meta)=>{ seq+=1;
    const e={id:bid+'.fls.rel_'+seq,type:rtype,from:frm,to:to,
      source:(status==='confirmed')?'model_declaration':'reference_resolution',
      status:status,basis:basis,
      note:'factual representation and location only — never coverage, protection, '+
           'adequacy or compliance'};
    if(_pyT(meta)) e.meta=meta;
    rels.push(e); return e; };
  const sysById=new Set(systems.map(s=>s.id));
  devices.forEach(d=>{
    if(_pyT(d.space_id))
      add('DEVICE_IN_SPACE',d.id,d.space_id,'confirmed',
        'the device lies in this architectural space',
        {disclaimer:'a represented '+d.device_type.toLowerCase()+' in a space is not '+
                    'coverage or protection of that space'});
    if(_pyT(d.system_id)&&sysById.has(d.system_id)){
      add('DEVICE_ON_SYSTEM',d.id,d.system_id,'confirmed','declared by the model');
      add('SYSTEM_HAS_DEVICE',d.system_id,d.id,'confirmed','declared by the model'); }
    else if(_pyT(d.mep_system_id)){
      for(const s of systems){
        if(s.mep_system_id===_mnid(bid,d.mep_system_id,'sys',0)){
          add('DEVICE_ON_SYSTEM',d.id,s.id,'confirmed',
            'resolved through the MEP system the referenced element belongs to');
          add('SYSTEM_HAS_DEVICE',s.id,d.id,'confirmed',
            'resolved through the MEP system the referenced element belongs to');
          break; } } }
    else if(d.origin==='model')
      /* ملاحظة فجوة بيانات تخصّ ما صرّح به النموذج فقط، لا ما أُشير إليه */
      issues.push({code:'DEVICE_WITHOUT_SYSTEM',subject:d.id,
        detail:'the device names no system; this is a data gap, not a violation'});
    if(_pyT(d.loop_ref))
      add('DEVICE_CONNECTED_TO_LOOP',d.id,String(d.loop_ref),'confirmed',
        'declared by the model',{disclaimer:'loops are never designed automatically'});
    if(_pyT(d.panel_ref))
      add('PANEL_CONTROLS_DEVICE',String(d.panel_ref),d.id,'confirmed','declared by the model');
    if(_pyT(d.alarm_zone_ref))
      add('DEVICE_IN_ALARM_ZONE',d.id,String(d.alarm_zone_ref),'confirmed',
        'declared by the model',
        {disclaimer:'alarm zones are never derived from floors or rooms'}); });
  exits.forEach(x=>{ if(_pyT(x.level_id))
    add('EXIT_SERVES_LEVEL',x.id,x.level_id,'confirmed','taken from the egress foundation',
      {disclaimer:'a represented exit is not a compliant means of egress'}); });
  /* هدف اللافتة يجب أن يكون مخرجاً محلولاً فعلاً في أساس الإخلاء، لا مجرّد
     مرجع مذكور: مرجع لا يقابله مخرج حقيقي يُبلَّغ ولا يُخترع له هدف */
  const exitRefs=new Set(exits.filter(x=>x.exit_resolved).map(x=>x.exit_ref));
  signs.forEach(s=>{
    if(!_pyT(s.indicates_exit)) return;
    const ok=exitRefs.has(s.indicates_exit);
    add('SIGN_INDICATES_EXIT',s.id,ok?s.indicates_exit:null,ok?'confirmed':'unresolved',
      ok?'declared by the model':'the referenced exit does not exist');
    if(!ok) issues.push({code:'SIGN_TARGET_MISSING',subject:s.id,ref:s.indicates_exit,
      detail:'the target is not invented; the reference is reported'}); });
  const bById=new Set(barriers.map(b=>b.id));
  openings.forEach(o=>{
    if(_pyT(o.barrier_id)&&bById.has(o.barrier_id)){
      add('BARRIER_CONTAINS_OPENING',o.barrier_id,o.id,'confirmed','declared by the model');
      if(o.fire_door)
        add('FIRE_DOOR_HOSTED_BY_BARRIER',o.id,o.barrier_id,'confirmed',
          'declared by the model'); } });
  zones.forEach(z=>z.resolved_space_ids.forEach(sp=>
    add('ZONE_CONTAINS_SPACE',z.id,sp,'confirmed','declared by the model')));
  stairs.forEach(s=>{ if(s.core_resolved)
    add('STAIR_REFERENCES_CORE',s.id,s.core_id,'confirmed',
      'referenced from the architectural cores',{protection_status:s.protection_status}); });
  assembly.forEach(a=>add('ASSEMBLY_POINT_ON_SITE',a.id,null,'confirmed',
    'declared by the model',
    {disclaimer:'no path from a building exit to an assembly point exists in this phase'}));
  return rels; }
/* ------------------------------------------------- سلامة النموذج والتعارض --- */
function _fIntegrity(bid,devices,signs,openings,barriers,assembly,arch,building,issues){
  const voids=(arch||{}).voids||[];
  const spaces=new Map(((arch||{}).spaces||[]).map(s=>[s.id,s]));
  devices.forEach(d=>{
    const sp=spaces.get(d.space_id);
    if(sp&&sp.rect&&d.x!==null&&d.x!==undefined){
      const rc=sp.rect;
      if(!(rc[0]-_F_TOL<=d.x&&d.x<=rc[0]+rc[2]+_F_TOL&&
           rc[1]-_F_TOL<=d.z&&d.z<=rc[1]+rc[3]+_F_TOL))
        issues.push({code:'DEVICE_OUTSIDE_SPACE',subject:d.id,other:sp.id}); }
    if(d.x===null||d.x===undefined||d.level_index===null||d.level_index===undefined) return;
    voids.forEach(v=>{
      if(v.level_index!==d.level_index) return;
      const r=v.rect;
      if(r[0]<=d.x&&d.x<=r[0]+r[2]&&r[1]<=d.z&&d.z<=r[1]+r[3])
        issues.push({code:'DEVICE_IN_FLOOR_OPENING',subject:d.id,other:v.id,
          detail:'reported as a factual location, not as a fault'}); }); });
  openings.forEach(o=>{
    if(!o.arch_opening_resolved)
      issues.push({code:o.fire_door?'FIRE_DOOR_NOT_HOSTED':'INVALID_HOST_OPENING_REF',
        subject:o.id,ref:o.arch_opening_id}); });
  barriers.forEach(b=>{
    if(!b.hosts_resolved)
      issues.push({code:'BARRIER_WITHOUT_HOST',subject:b.id,refs:b.host_wall_ids}); });
  const rects=((arch||{}).spaces||[]).filter(s=>s.rect).map(s=>s.rect);
  if(rects.length){
    const bb=[Math.min.apply(null,rects.map(r=>r[0])),Math.min.apply(null,rects.map(r=>r[1])),
              Math.max.apply(null,rects.map(r=>r[0]+r[2])),
              Math.max.apply(null,rects.map(r=>r[1]+r[3]))];
    assembly.forEach(a=>{
      if(a.x===null||a.x===undefined) return;
      if(bb[0]<=a.x&&a.x<=bb[2]&&bb[1]<=a.z&&a.z<=bb[3])
        issues.push({code:'ASSEMBLY_POINT_INSIDE_BUILDING',subject:a.id,footprint:bb}); }); } }
/* ------------------------------------------------------------- التصريف --- */
function compileFls(building,buildingId,position,rotationDeg,arch,mep,rels){
  const bid=buildingId||'bld_0';
  const raw=_fraw(building);
  if(arch===undefined||arch===null){
    try{ arch=compileArchitecture(building,bid,position,rotationDeg); }catch(e){ arch=null; } }
  if(rels===undefined||rels===null){
    try{ rels=buildRelationships(building,bid); }catch(e){ rels=[]; } }
  if(mep===undefined||mep===null){
    try{ mep=compileMep(building,bid,position,rotationDeg,arch); }catch(e){ mep=null; } }
  const levelsIdx=_fLevelsIndex(building,bid);
  const spaceIdx=_fSpaceIndex(arch);
  const issues=[];
  const knownKeys=['status','synthetic','meta','zones','barriers','openings','exits','stairs',
    'shafts','devices','systems','signs','assembly_points','refuge_areas','smoke_control',
    'layer_visibility','visible_layers'];
  Object.keys(raw).sort(_scmp).forEach(k=>{
    if(knownKeys.indexOf(k)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:k,
        detail:'this collection is not part of the FLS schema and was NOT interpreted'}); });
  const systems=_fSystems(raw,bid,mep);
  const sysIds=new Set(systems.map(s=>s.id));
  const devices=_fDevices(raw,bid,levelsIdx,spaceIdx,sysIds,mep);
  const exits=_fExits(raw,bid,building,rels,arch,levelsIdx);
  const exitRefs=new Set(exits.map(x=>x.exit_ref));
  const stairs=_fStairs(raw,bid,arch);
  const shafts=_fShafts(raw,bid,arch,mep);
  const barriers=_fBarriers(raw,bid,arch,levelsIdx);
  const barrierIds=new Set(barriers.map(b=>b.id));
  const openings=_fOpenings(raw,bid,arch,barrierIds);
  const zones=_fZones(raw,bid,levelsIdx,spaceIdx);
  const signs=_fSigns(raw,bid,levelsIdx,spaceIdx,exitRefs);
  const assembly=_fPoints(raw,bid,'assembly_points','assembly','FLS_ASSEMBLY_POINT',
    levelsIdx,spaceIdx,
    'an assembly point is represented data only; no site evacuation path exists in this phase');
  const refuge=_fPoints(raw,bid,'refuge_areas','refuge','FLS_REFUGE_AREA',levelsIdx,spaceIdx,
    'an area of refuge is never inferred from a lobby, landing, stair or corridor, and '+
    'accessibility is never evaluated');
  const smoke=_fSmokeControl(raw,bid,levelsIdx);
  const cnt=k=>(_pyT(raw[k])?raw[k].length:0);
  const declaredCount=cnt('zones')+cnt('barriers')+cnt('openings')+cnt('devices')+cnt('systems')
    +cnt('signs')+cnt('assembly_points')+cnt('refuge_areas')+cnt('smoke_control')+cnt('shafts')
    +cnt('stairs')+cnt('exits');
  const referenced=devices.length+systems.length+exits.length+stairs.length;
  const declared=String(_pyT(raw.status)?raw.status:'').toUpperCase();
  let status;
  if(FLS_MODEL_STATUS.indexOf(declared)>=0) status=declared;
  else if(declaredCount===0) status='NOT_DEFINED';
  else {
    const verified=devices.concat(barriers).concat(openings).concat(zones).concat(signs)
      .filter(e=>e.origin==='model')
      .every(e=>FLS_VERIFIED_SOURCES.indexOf(e.source)>=0);
    status=verified?'REPRESENTED':'PARTIAL'; }
  const out={schema:FLS_SCHEMA, compiler_version:FLS_COMPILER_VERSION, building_id:bid,
    status:status,
    status_basis:(FLS_MODEL_STATUS.indexOf(declared)>=0)?'declared_by_model'
      :((declaredCount===0)
        ?('no fire or life-safety element is declared; '+referenced+
          ' element(s) are referenced from other layers')
        :'derived from element provenance'),
    synthetic:raw.synthetic===true, regulatory:false,
    transform:{position:position||{x:0.0,z:0.0}, rotation_deg:Number(rotationDeg||0.0),
      applied:'local coordinates; world transform is applied on read'},
    levels:_aLevels(building,bid).map(l=>({id:l.id,index:l.index,elevation_m:l.elevation_m})),
    zones:zones, barriers:barriers, openings:openings, exits:exits, stairs:stairs,
    shafts:shafts, devices:devices, systems:systems, signs:signs,
    assembly_points:assembly, refuge_areas:refuge, smoke_control:smoke,
    relationships:[], issues:[],
    meta:{note:ACS_FLS_SPEC.note, fire_note:ACS_FLS_SPEC.fire_note,
      semantics:ACS_FLS_SPEC.semantics,
      declared_elements:declaredCount, referenced_elements:referenced,
      sources_of_truth:ACS_FLS_SPEC.source_of_truth,
      navigation_impact:ACS_FLS_SPEC.navigation_note,
      distance_impact:ACS_FLS_SPEC.distance_note,
      occupancy_note:ACS_FLS_SPEC.occupancy_note,
      compliance:'NOT_EVALUATED'}};
  out.relationships=_fRelationships(bid,systems,devices,exits,stairs,barriers,openings,zones,
    signs,assembly,refuge,arch,issues);
  _fIntegrity(bid,devices,signs,openings,barriers,assembly,arch,building,issues);
  validateFls(out).forEach(i=>issues.push(i));
  issues.forEach(i=>{ i.severity=flsSeverityOf(i.code); });
  const dec=issues.map((it,i)=>({it:it,i:i}));
  dec.sort((a,b)=>{
    const sa=FLS_SEVERITIES.indexOf(a.it.severity)*-1;
    const sb=FLS_SEVERITIES.indexOf(b.it.severity)*-1;
    if(sa!==sb) return sa-sb;
    const c=_scmp(String(a.it.code),String(b.it.code));
    if(c!==0) return c;
    const d=_scmp(String(a.it.subject),String(b.it.subject));
    return d!==0?d:(a.i-b.i); });
  out.issues=dec.map(d=>d.it);
  return out; }
/* ------------------------------------------------------------- التحقّق --- */
/* فحوص سلامة بيانات — ليست فحوص كود حريق، والغياب ليس مخالفة */
function validateFls(fls){
  const issues=[], bid=fls.building_id;
  const groups=['zones','barriers','openings','exits','stairs','shafts','devices','systems',
    'signs','assembly_points','refuge_areas','smoke_control'];
  const seen=new Map();
  groups.forEach(key=>(fls[key]||[]).forEach(e=>{
    if(seen.has(e.id)) issues.push({code:'DUPLICATE_ELEMENT_ID',subject:e.id,other:seen.get(e.id)});
    seen.set(e.id,key);
    if(FLS_ELEMENT_TYPES.indexOf(e.type)<0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:e.id,declared:e.type});
    if(bid&&String(e.id).indexOf(String(bid)+'.')!==0)
      issues.push({code:'CROSS_BUILDING_REF',subject:e.id});
    if(FLS_FORBIDDEN_PROVENANCE.indexOf(e.source)>=0)
      issues.push({code:'UNSUPPORTED_ELEMENT_TYPE',subject:e.id,declared:e.source}); }));
  (fls.systems||[]).forEach(s=>{
    if(!s.mep_system_resolved)
      issues.push({code:'INVALID_SYSTEM_REF',subject:s.id,ref:s.mep_system_id}); });
  (fls.devices||[]).forEach(d=>{
    if(_fBadNumber(d.raw_x)||_fBadNumber(d.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:d.id});
    if(!d.device_type_recognised)
      issues.push({code:'UNKNOWN_DEVICE_TYPE',subject:d.id,declared:d.declared_type});
    if(!d.system_resolved)
      issues.push({code:'INVALID_SYSTEM_REF',subject:d.id,ref:d.system_id});
    if(d.mep_element_resolved===false)
      issues.push({code:'INVALID_MEP_ELEMENT_REF',subject:d.id,ref:d.mep_element_id});
    if(!d.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:d.id,ref:d.level_ref});
    if(!d.space_resolved) issues.push({code:'INVALID_SPACE_REF',subject:d.id,ref:d.space_ref}); });
  (fls.exits||[]).forEach(x=>{
    if(!x.exit_resolved) issues.push({code:'INVALID_EXIT_REF',subject:x.id,ref:x.exit_ref}); });
  (fls.stairs||[]).forEach(s=>{
    if(!s.core_resolved) issues.push({code:'INVALID_CORE_REF',subject:s.id,ref:s.core_id});
    if(s.protection_status==='unknown'&&s.origin==='model')
      issues.push({code:'PROTECTION_UNKNOWN',subject:s.id,
        detail:'protection is not assumed; this is a data gap, not a violation'}); });
  (fls.shafts||[]).forEach(s=>{
    if(!s.host_resolved) issues.push({code:'INVALID_CORE_REF',subject:s.id,ref:s.host_ref}); });
  (fls.barriers||[]).forEach(b=>{
    if(!b.barrier_type_recognised)
      issues.push({code:'UNKNOWN_BARRIER_TYPE',subject:b.id,declared:b.declared_type});
    b.host_wall_ids.forEach(h=>{ if(b.resolved_host_wall_ids.indexOf(h)<0)
      issues.push({code:'INVALID_HOST_WALL_REF',subject:b.id,ref:h}); });
    if(b.rating_minutes.value===null)
      issues.push({code:'RATING_UNKNOWN',subject:b.id,
        detail:'rating is never inferred; this is a data gap, not a violation'});
    else if(b.rating_minutes.value<=0)
      issues.push({code:'INVALID_RATING_VALUE',subject:b.id,value:b.rating_minutes.value}); });
  (fls.openings||[]).forEach(o=>{
    if(!o.opening_type_recognised)
      issues.push({code:'UNKNOWN_OPENING_TYPE',subject:o.id,declared:o.declared_type});
    if(!o.barrier_resolved)
      issues.push({code:'INVALID_BARRIER_REF',subject:o.id,ref:o.barrier_id});
    if(o.rating_minutes.value!==null&&o.rating_minutes.value<=0)
      issues.push({code:'INVALID_RATING_VALUE',subject:o.id,value:o.rating_minutes.value}); });
  (fls.zones||[]).forEach(z=>{
    if(!z.levels_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:z.id,refs:z.level_refs});
    z.space_ids.forEach(sp=>{ if(z.resolved_space_ids.indexOf(sp)<0)
      issues.push({code:'INVALID_ZONE_SPACE_REF',subject:z.id,ref:sp}); });
    if(!z.space_ids.length)
      issues.push({code:'ZONE_WITHOUT_SPACES',subject:z.id,
        detail:'a compartment is never populated by inference'}); });
  (fls.signs||[]).forEach(s=>{
    if(_fBadNumber(s.raw_x)||_fBadNumber(s.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:s.id});
    if(!s.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:s.id,ref:s.level_ref});
    if(!s.space_resolved) issues.push({code:'INVALID_SPACE_REF',subject:s.id,ref:s.space_ref}); });
  (fls.assembly_points||[]).concat(fls.refuge_areas||[]).forEach(p=>{
    if(_fBadNumber(p.raw_x)||_fBadNumber(p.raw_z))
      issues.push({code:'NAN_COORDINATE',subject:p.id});
    if(!p.level_resolved) issues.push({code:'INVALID_LEVEL_REF',subject:p.id,ref:p.level_ref}); });
  (fls.smoke_control||[]).forEach(s=>{
    if(!s.levels_resolved)
      issues.push({code:'INVALID_LEVEL_REF',subject:s.id,refs:s.level_refs}); });
  return issues; }
/* -------------------------------------------------------- بيانات الرسم --- */
/* عناصر مُشار إليها لا تُرسم مرّتين: ما رسمه MEP يبقى له، وما لا وجود له في أي
   طبقة أخرى (لافتة · نقطة تجمّع) يُرسم هنا مرّة واحدة */
function flsRenderItems(fls){
  const items=[];
  (fls.devices||[]).forEach(d=>{
    if(d.x===null||d.x===undefined||d.y===null||d.y===undefined) return;
    const referenced=(d.origin==='mep_adapter'||d.origin==='phase1_adapter');
    const sz=FLS_FALLBACKS.device_size_m;
    items.push({name:'FLS|'+d.device_type+'|'+d.id, kind:'DEVICE', id:d.id,
      device_type:d.device_type, category:d.device_category, layer:d.render_layer,
      render_mode:referenced?'referenced':'emitted',
      references:(d.mep_element_id===undefined)?null:d.mep_element_id,
      cx:d.x, cy:d.y+sz/2.0, cz:d.z, ex:sz, ey:sz, ez:sz,
      geometry_source:'display_fallback', element_source:d.source}); });
  (fls.signs||[]).forEach(s=>{
    if(s.x===null||s.x===undefined||s.y===null||s.y===undefined) return;
    items.push({name:'FLS|EXIT_SIGN|'+s.id, kind:'SIGN', id:s.id,
      device_type:'EXIT_SIGN', category:'SIGNAGE', layer:'FLS_SIGNAGE',
      render_mode:'emitted', references:null,
      cx:s.x, cy:s.y+2.1, cz:s.z,
      ex:FLS_FALLBACKS.sign_w_m, ey:FLS_FALLBACKS.sign_h_m, ez:0.04,
      geometry_source:'display_fallback', element_source:s.source}); });
  (fls.assembly_points||[]).forEach(a=>{
    if(a.x===null||a.x===undefined) return;
    const sz=FLS_FALLBACKS.assembly_point_size_m;
    items.push({name:'FLS|ASSEMBLY_POINT|'+a.id, kind:'ASSEMBLY_POINT', id:a.id,
      device_type:'OTHER', category:'OTHER', layer:'FLS_OTHER',
      render_mode:'emitted', references:null,
      cx:a.x, cy:0.05, cz:a.z, ex:sz, ey:0.1, ez:sz,
      geometry_source:'display_fallback', element_source:a.source}); });
  items.sort((a,b)=>_scmp(String(a.name),String(b.name)));
  return items; }
/* ---------------------------------------------------------------- تدقيق --- */
/* أعداد واقعية فقط. الغياب لا يُعدّ مخالفة، والمطابقة غير مُقيَّمة */
function flsAudit(fls){
  const devs=fls.devices||[];
  const byType={}, byCat={};
  devs.forEach(d=>{ byType[d.device_type]=(byType[d.device_type]||0)+1;
    byCat[d.device_category]=(byCat[d.device_category]||0)+1; });
  const iss=fls.issues||[];
  const g=(o,k)=>Object.prototype.hasOwnProperty.call(o,k)?o[k]:0;
  return {building_id:fls.building_id, status:fls.status,
    devices_total:devs.length, devices_by_type:byType, devices_by_category:byCat,
    smoke_detectors:g(byType,'SMOKE_DETECTOR'), heat_detectors:g(byType,'HEAT_DETECTOR'),
    manual_call_points:g(byType,'MANUAL_CALL_POINT'), alarm_devices:g(byCat,'ALARM'),
    sprinklers:g(byType,'SPRINKLER_HEAD'), extinguishers:g(byType,'FIRE_EXTINGUISHER'),
    hose_reels:g(byType,'HOSE_REEL'),
    represented_exits:(fls.exits||[]).length, exit_signs:(fls.signs||[]).length,
    fire_doors:(fls.openings||[]).filter(o=>o.fire_door).length,
    barriers:(fls.barriers||[]).length,
    rated_barriers:(fls.barriers||[]).filter(b=>b.rating_minutes.value!==null).length,
    zones:(fls.zones||[]).length, stairs:(fls.stairs||[]).length,
    protected_stairs_declared:(fls.stairs||[])
      .filter(s=>s.protection_status==='declared_protected').length,
    shafts:(fls.shafts||[]).length,
    assembly_points:(fls.assembly_points||[]).length,
    refuge_areas:(fls.refuge_areas||[]).length,
    smoke_control_entries:(fls.smoke_control||[]).length,
    referenced_systems:(fls.systems||[]).length,
    relationships:(fls.relationships||[]).length,
    adapted_from_mep:devs.filter(d=>d.origin==='mep_adapter').length,
    adapted_from_phase1:devs.filter(d=>d.origin==='phase1_adapter').length,
    issues:iss.length,
    errors:iss.filter(i=>i.severity==='ERROR').length,
    warnings:iss.filter(i=>i.severity==='WARNING').length,
    infos:iss.filter(i=>i.severity==='INFO').length,
    code_required:0, coverage:'NOT_EVALUATED', compliance:'NOT_EVALUATED',
    note:'counts of represented elements only. A missing element is NOT a violation: '+
         'absence is not a violation without a verified rule, and no coverage, '+
         'protection, adequacy or compliance is evaluated anywhere'}; }
/* --------------------------------------------------------------- خدمات --- */
function flsElementById(fls,eid){
  const keys=['zones','barriers','openings','exits','stairs','shafts','devices','systems',
    'signs','assembly_points','refuge_areas','smoke_control'];
  for(const key of keys) for(const el of (fls[key]||[])) if(el.id===eid) return el;
  for(const r of (fls.relationships||[])) if(r.id===eid) return r;
  return null; }
function flsToWorld(fls,x,z){
  const t=fls.transform||{};
  const rot=(Number(t.rotation_deg||0.0))*Math.PI/180;
  const px=Number((t.position||{}).x||0.0), pz=Number((t.position||{}).z||0.0);
  const ca=Math.cos(rot), sa=Math.sin(rot);
  return [px+x*ca-z*sa, pz+x*sa+z*ca]; }
/* يقتبس قياس مسار إخلاء موجود كواقعة. لا مقارنة بأي حدّ ولا حكم مطابقة */
function flsEgressFacts(building,bid,spaceId,rels){
  bid=bid||'bld_0';
  if(rels===undefined||rels===null){
    try{ rels=buildRelationships(building,bid); }catch(e){ rels=[]; } }
  let r=null;
  try{ r=findEgress(building,rels,spaceId,bid); }catch(e){ return null; }
  if(!r) return null;
  return {space_id:spaceId, status:r.status,
    exit_id:(r.exit||{}).id===undefined?null:(r.exit||{}).id,
    distance_status:(r.distance_status===undefined)?null:r.distance_status,
    walking_distance_m:(r.distance===undefined)?null:r.distance,
    selection_basis:(r.selection_basis===undefined)?null:r.selection_basis,
    compliance:'NOT_EVALUATED',
    note:'quoted from the egress and distance foundations as factual data; it is '+
         'never compared to any code travel-distance limit'}; }
/* حقائق معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية ولا حدّ هنا */
function flsRuleInputs(fls){
  const a=flsAudit(fls);
  const out={building:{}};
  FLS_DEVICE_TYPES.forEach(t=>{
    out.building['fls.device.exists.'+t]=
      (Object.prototype.hasOwnProperty.call(a.devices_by_type,t)&&a.devices_by_type[t]>0);
    out.building['fls.device.count.'+t]=
      Object.prototype.hasOwnProperty.call(a.devices_by_type,t)?a.devices_by_type[t]:0; });
  out.building['fls.device.count']=a.devices_total;
  out.building['fls.exit.count']=a.represented_exits;
  out.building['fls.zone.exists']=a.zones>0;
  out.building['fls.zone.count']=a.zones;
  out.building['fls.fire_door.count']=a.fire_doors;
  FLS_REFERENCED_MEP_SYSTEMS.forEach(t=>{
    out.building['fls.system.exists.'+t]=(fls.systems||[]).some(s=>s.mep_system_type===t); });
  (fls.openings||[]).forEach(o=>{
    out[o.id]={'fls.fire_door.rating':o.rating_minutes.value,
      'fls.fire_door.self_closing':o.self_closing,
      'fls.member.source':o.source}; });
  (fls.barriers||[]).forEach(b=>{
    out[b.id]={'fls.barrier.rating':b.rating_minutes.value,
      'fls.barrier.type':b.barrier_type,
      'fls.member.source':b.source}; });
  return out; }
function flsSummary(fls){
  const a=flsAudit(fls);
  return {building_id:fls.building_id, compiler_version:fls.compiler_version,
    status:fls.status, status_basis:fls.status_basis,
    synthetic:fls.synthetic===true, regulatory:false,
    devices:a.devices_total, exits:a.represented_exits, signs:a.exit_signs,
    fire_doors:a.fire_doors, barriers:a.barriers, zones:a.zones, stairs:a.stairs,
    shafts:a.shafts, systems:a.referenced_systems,
    assembly_points:a.assembly_points, refuge_areas:a.refuge_areas,
    relationships:a.relationships, issues:a.issues,
    errors:a.errors, warnings:a.warnings, infos:a.infos,
    code_required:0, coverage:'NOT_EVALUATED', compliance:'NOT_EVALUATED',
    note:'fire and life-safety representation and topology only — no fire design, '+
         'no simulation, no coverage or hydraulic analysis, no code compliance'}; }
/* ==================================================================
   المرحلة 3 — أساس العرض البصري والتقديم (مطابق لـ acs_visual.py).
   تصوير يحفظ الهندسة فقط: لا تعديل هندسي ولا توليد هندسة بالذكاء الاصطناعي •
   المادة البصرية مظهر لا خاصية إنشائية أو حريقية أو حرارية • الديكور
   VISUAL_ONLY ولا يدخل أي عدّ هندسي • الطبقة مشتقّة ولا تُكتب في أي نموذج.
   ================================================================== */


export { ACS_FLS_SPEC, ACS_MEP_SPEC, ACS_STRUCT_SPEC, FLS_ADAPTER_ORIGINS, FLS_BARRIER_TYPES, FLS_COMPILER_VERSION, FLS_DEVICE_CATEGORIES, FLS_DEVICE_CATEGORY, FLS_DEVICE_TYPES, FLS_ELEMENT_TYPES, FLS_FALLBACKS, FLS_FORBIDDEN_PROVENANCE, FLS_ISSUE_CODES, FLS_MEP_DEVICE_MAP, FLS_MEP_EQUIPMENT_MAP, FLS_MODEL_STATUS, FLS_OPENING_TYPES, FLS_PROTECTION_STATUSES, FLS_PROVENANCE, FLS_REFERENCED_MEP_SYSTEMS, FLS_REL_STATUSES, FLS_REL_TYPES, FLS_RENDER_LAYERS, FLS_SCHEMA, FLS_SEVERITIES, FLS_SMOKE_CONTROL_KINDS, FLS_VERIFIED_SOURCES, MEP_COMPILER_VERSION, MEP_DISCIPLINES, MEP_DISCIPLINE_OF, MEP_ELEMENT_TYPES, MEP_EQUIPMENT_TYPES, MEP_FALLBACKS, MEP_ISSUE_CODES, MEP_MEDIA, MEP_MODEL_STATUS, MEP_NODE_KINDS, MEP_PENETRATION_HOSTS, MEP_PORT_TYPES, MEP_PROVENANCE, MEP_REL_STATUSES, MEP_REL_TYPES, MEP_RISER_KINDS, MEP_ROUTING_STATUSES, MEP_SCHEMA, MEP_SEGMENT_KINDS, MEP_SEVERITIES, MEP_SYSTEM_TYPES, MEP_TERMINAL_TYPES, MEP_VERIFIED_SOURCES, STRUCT_ALIGNMENT_STATES, STRUCT_COMPILER_VERSION, STRUCT_ELEMENT_TYPES, STRUCT_FALLBACKS, STRUCT_FOUNDATION_TYPES, STRUCT_ISSUE_CODES, STRUCT_MATERIALS, STRUCT_MODEL_STATUS, STRUCT_PROVENANCE, STRUCT_REL_STATUSES, STRUCT_REL_TYPES, STRUCT_ROLES, STRUCT_SCHEMA, STRUCT_SECTION_SHAPES, STRUCT_SEVERITIES, STRUCT_VERIFIED_SOURCES, _FLS_LAYER_OF, _F_EPS, _F_TOL, _MEP_DISC_TAG, _MEP_P1, _M_EPS, _M_TOL, _S_EPS, _S_OFFSET_TOL, _S_POS_TOL, _byId, _fBadNumber, _fBarriers, _fDeviceCommon, _fDevices, _fExits, _fIntegrity, _fLevelOf, _fLevelsIndex, _fMepHas, _fOpenings, _fPoints, _fRelationships, _fShafts, _fSigns, _fSmokeControl, _fSpaceIndex, _fStairs, _fSystems, _fZones, _fnid, _fnum, _fprops, _frating, _fraw, _fsrc, _mBadNumber, _mCross, _mDims, _mDisciplineOf, _mEquipment, _mInterference, _mLevelOf, _mLevelsIndex, _mNodes, _mPenetrations, _mPoint3, _mPolyline, _mPorts, _mPropMap, _mRelationships, _mRenderSize, _mRisers, _mSeg2d, _mSegHitsBox, _mSegments, _mSize, _mSpaceIndex, _mSystems, _mTerminals, _mfallback, _mnid, _mnum, _mraw, _msrc, _sBadNumber, _sBeams, _sColumns, _sCores, _sFoundations, _sGridIndex, _sGrids, _sInterference, _sKey, _sKeyCmp, _sLevelOf, _sLevelsIndex, _sMaterialName, _sMaterials, _sNodes, _sOutline, _sRelationships, _sRenderSection, _sSection, _sSlabs, _sSortNum, _sStacks, _sWalls, _sfallback, _snid, _snum, _sprop, _sraw, _ssrc, adaptPhase1Terminals, archDoorConnectsConfirmed, archElementById, archOpeningAnchor, archOpeningByRef, archSharedWallBetween, archSummary, archToWorld, compileArchitecture, compileFls, compileMep, compileStructure, flsAudit, flsEgressFacts, flsElementById, flsRenderItems, flsRuleInputs, flsSeverityOf, flsSummary, flsToWorld, mepElementById, mepInterferences, mepRenderItems, mepRuleInputs, mepSeverityOf, mepSummary, mepSystemById, mepToWorld, structColumnsInside, structElementById, structGridToWorld, structRenderItems, structRuleInputs, structSeverityOf, structSummary, structToWorld, suggestStructuralGrid, validateArchitecture, validateFls, validateMep, validateStructure };
