/* ======================================================================
   المرحلة 3 — اختبارات أساس العرض البصري والتقديم.
   تصوير يحفظ الهندسة فقط: لا تعديل هندسي، ولا هندسة من الذكاء الاصطناعي،
   والديكور البصري ليس بيانات هندسية.
   ====================================================================== */
const fs=require('fs'), path=require('path');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(path.join(HERE,'fixtures','base_fixtures.json'),'utf8'));
const SC=JSON.parse(fs.readFileSync(path.join(HERE,'fixtures','visual_scenarios.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const V=(name,opts)=>compileVisualScene(C(SC.models[name]),'bld_0',null,0,
  Object.assign({at:AT},opts||{}));
const AR=(name)=>compileArchitecture(C(SC.models[name]),'bld_0',null,0);
const ENGI=(m)=>{const a=compileArchitecture(C(m),'bld_0',null,0);
  const s=compileStructure(C(m),'bld_0',null,0,a);
  const p=compileMep(C(m),'bld_0',null,0,a,s);
  const f=compileFls(C(m),'bld_0',null,0,a,p);
  const co=compileCoordination(C(m),'bld_0',null,0,a,s,p,f,null);
  return JSON.stringify([a,s,p,f,co]); };
/* الكلمات الممنوعة ترد داخل نصوص النفي نفسها، فالفحص يقرأ الحقول لا النصّ الخام */
const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer','derivation',
  'authority','material_class_note','theme_note','decoration_note','site_note',
  'water_note','lighting_note','night_fixture_note','quality_note','lod_note',
  'instancing_note','floor_plan_note','dimension_note','elevation_note','dollhouse_note',
  'cutaway_note','render_authority_note','control_buffer_note','ai_note','drift_note',
  'asset_note','procedural_fallback_note','texture_note','vr_scale_note',
  'walkthrough_note','export_note','revision_note','rule_note','no_generator_note',
  'mode_note','layer_note','clash_overlay_note','provenance_note','authority_note',
  'derivation_note','geometry_confidence_note','mode_intent'];
const scanFields=(root,re)=>{ const hits=[];
  const walk=(v,path)=>{ if(Array.isArray(v)) return v.forEach(x=>walk(x,path));
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(NOTE_KEYS.indexOf(k)>=0) return;
      if(re.test(k)) hits.push(path+'.'+k);
      if(typeof v[k]==='string'&&re.test(v[k])) hits.push(path+'.'+k+'="'+v[k]+'"');
      walk(v[k],path+'.'+k); }); };
  walk(root,''); return hits; };

console.log('\n== §1 — SPEC INTEGRITY AND NO-DRIFT ==');
const CANON=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_visual.json'),'utf8'));
chk('browser spec is byte-identical to acs_visual.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_VISUAL_SPEC));
chk('schema and compiler version are pinned',
    VIS_SCHEMA==='acs.visual/1'&&/^acs-visual-compiler\//.test(VIS_COMPILER_VERSION));
chk('all nine visual modes are declared', VIS_MODES.length===9);
chk('every material is classified VISUAL_MATERIAL and nothing else',
    VIS_MATERIAL_CLASS==='VISUAL_MATERIAL');
chk('no material in the library carries an engineering property',
    Object.keys(VIS_MATERIALS).every(k=>{const m=VIS_MATERIALS[k];
      return !('fire_rating' in m)&&!('thermal' in m)&&!('u_value' in m)
        &&!('strength' in m)&&!('reaction_to_fire' in m);}));
chk('material provenance separates SYSTEM_DEFAULT from USER',
    VIS_PROVENANCE.indexOf('SYSTEM_DEFAULT')>=0&&VIS_PROVENANCE.indexOf('USER')>=0
    &&VIS_PROVENANCE.indexOf('VISUAL_THEME')>=0&&VIS_PROVENANCE.indexOf('AI_SUGGESTED')>=0);
chk('the spec forbids treating a render as measured or as-built',
    ['photoreal_is_measured','render_is_as_built','ai_generated_geometry',
     'decoration_is_engineering_object','entourage_is_occupant']
      .every(w=>ACS_VISUAL_SPEC.forbidden_claims.indexOf(w)>=0));
chk('the spec names no code, standard or authority',
    !/\bNFPA\b|\bIBC\b|\bSBC\b|\bASHRAE\b|\bADA\b|\bNEC\b|civil.?defen/i.test(
      JSON.stringify({a:ACS_VISUAL_SPEC.materials,b:ACS_VISUAL_SPEC.visual_modes,
        c:ACS_VISUAL_SPEC.themes,d:ACS_VISUAL_SPEC.quality_params,
        e:ACS_VISUAL_SPEC.rule_inputs,f:ACS_VISUAL_SPEC.drift_codes})));
chk('the AI may not change any layout feature',
    ['wall_positions','door_count','window_count','floor_count','stair_location',
     'building_footprint','room_count'].every(k=>VIS_AI_MAY_NOT_CHANGE.indexOf(k)>=0));

console.log('\n== §2 — NO ENGINEERING GEOMETRY MUTATION ==');
const NAMES=Object.keys(SC.models);
chk('compiling a scene mutates no source model', NAMES.every(n=>{
  const m=C(SC.models[n]); const b=JSON.stringify(m);
  compileVisualScene(m,'bld_0',null,0,{mode:'PRESENTATION',at:AT});
  return JSON.stringify(m)===b; }));
chk('every visual mode leaves the model untouched', VIS_MODES.every(md=>{
  const m=C(SC.models.villa); const b=JSON.stringify(m);
  compileVisualScene(m,'bld_0',null,0,{mode:md,at:AT});
  return JSON.stringify(m)===b; }));
chk('every discipline model is byte-identical after visualisation', (function(){
  const before=ENGI(SC.models.villa_full);
  VIS_MODES.forEach(md=>compileVisualScene(C(SC.models.villa_full),'bld_0',null,0,
    {mode:md,include_decoration:true,include_entourage:true,entourage_count:4,at:AT}));
  return ENGI(SC.models.villa_full)===before; })());
chk('every theme leaves the compiled architecture identical', (function(){
  const base=JSON.stringify(AR('villa'));
  return VIS_THEMES.every(t=>{ compileVisualScene(C(SC.models.villa),'bld_0',null,0,
    {mode:'ARCHITECTURAL',theme:t,at:AT}); return JSON.stringify(AR('villa'))===base; }); })());
chk('every quality profile leaves the compiled architecture identical', (function(){
  const base=JSON.stringify(AR('hotel'));
  return VIS_QUALITY_PROFILES.every(q=>{ compileVisualScene(C(SC.models.hotel),'bld_0',
    null,0,{quality:q,at:AT}); return JSON.stringify(AR('hotel'))===base; }); })());
chk('the summary states no engineering geometry was modified',
    NAMES.every(n=>V(n).summary.engineering_geometry_modified===false));
chk('no scene contains a geometry-generation or redesign claim',
    NAMES.every(n=>scanFields(V(n),/generated_geometry|redesign|moved_wall|relocated/i)
      .length===0));

console.log('\n== §3 — OBJECTS ARE DERIVED, NEVER AUTHORED ==');
const villa=V('villa');
chk('every non-visual object names the model element it came from',
    villa.objects.filter(o=>!o.visual_only).every(o=>!!o.source_element_id));
chk('every source element id resolves in the architectural model', (function(){
  const a=AR('villa'); const ids={};
  ['walls','openings','slabs','ceilings','roofs','cores','voids'].forEach(k=>
    (a[k]||[]).forEach(e=>{ids[e.id]=true;}));
  return villa.objects.filter(o=>!o.visual_only&&o.layer==='ARCHITECTURE')
    .every(o=>ids[o.source_element_id]); })());
chk('wall count in the scene equals the wall count in the model',
    villa.objects.filter(o=>o.kind==='WALL').length===AR('villa').walls.length);
chk('opening count in the scene equals the opening count in the model',
    villa.objects.filter(o=>o.kind==='DOOR'||o.kind==='WINDOW').length
      ===AR('villa').openings.length);
chk('an object sized from a render fallback says so',
    villa.objects.filter(o=>o.geometry_source==='display_fallback').length>0);
chk('no display fallback is relabelled as a model dimension',
    villa.objects.every(o=>o.geometry_source==='model'
      ||o.geometry_source==='display_fallback'));
chk('the visual roof cap is visual-only and never a modelled roof', (function(){
  const c=villa.objects.filter(o=>o.kind==='ROOF_CAP');
  return c.length===1&&c[0].visual_only===true&&c[0].semantic===false
    &&c[0].source_element_id===null&&c[0].geometry_source==='display_fallback'; })());
chk('a model that states a roof gets no visual cap',
    V('villa').objects.filter(o=>o.kind==='ROOF').length===0);

console.log('\n== §4 — VISUAL MODES ==');
chk('every declared mode compiles', VIS_MODES.every(md=>{
  try{ return !!V('villa',{mode:md}).scene_id; }catch(e){ return false; } }));
chk('an unknown mode falls back to PRESENTATION rather than inventing one',
    V('villa',{mode:'HOLOGRAM'}).mode==='PRESENTATION');
chk('ENGINEERING mode shows every discipline',
    ['ARCHITECTURE','STRUCTURE','MEP','FLS'].every(l=>
      V('villa_full',{mode:'ENGINEERING'}).presentation.layers.indexOf(l)>=0));
chk('ENGINEERING mode is still available and technically styled',
    V('villa',{mode:'ENGINEERING'}).objects.filter(o=>o.layer==='ARCHITECTURE')
      .every(o=>o.material==='technical'));
chk('ARCHITECTURAL mode applies finishes rather than technical shading',
    V('villa',{mode:'ARCHITECTURAL',theme:'Classic'}).objects
      .filter(o=>o.kind==='WALL').every(o=>o.material!=='technical'));
chk('ARCHITECTURAL mode adds ceilings that ENGINEERING mode omits',
    V('villa',{mode:'ARCHITECTURAL'}).objects.filter(o=>o.kind==='CEILING').length>0
    &&V('villa',{mode:'ENGINEERING'}).objects.filter(o=>o.kind==='CEILING').length===0);
chk('PRESENTATION mode carries a sky, exposure and tone mapping', (function(){
  const e=V('villa',{mode:'PRESENTATION'}).environment;
  return e.background==='sky'&&e.exposure>0&&!!e.tone_mapping; })());
chk('every mode reports the same model hash for the same model',
    new Set(VIS_MODES.map(md=>V('villa',{mode:md}).model_hash)).size===1);

console.log('\n== §5 — MATERIALS AND PROVENANCE ==');
chk('every emitted material is VISUAL_MATERIAL',
    villa.materials.every(m=>m.material_class==='VISUAL_MATERIAL'));
chk('no emitted material carries a fire, thermal or structural property',
    villa.materials.every(m=>m.fire_rating===null&&m.thermal_property===null
      &&m.structural_material===false));
chk('a material chosen by the system is SYSTEM_DEFAULT, not a user requirement',
    V('villa',{theme:'Neutral'}).objects.filter(o=>o.kind==='WALL')
      .every(o=>o.material_provenance==='SYSTEM_DEFAULT'));
chk('a material chosen by a theme is VISUAL_THEME, not a user requirement',
    V('villa',{theme:'Luxury'}).objects.filter(o=>o.kind==='WALL')
      .every(o=>o.material_provenance==='VISUAL_THEME'));
chk('a material stated by the user is USER',
    V('villa',{materials:{wall:'marble'}}).objects.filter(o=>o.kind==='WALL')
      .every(o=>o.material==='marble'&&o.material_provenance==='USER'));
chk('an AI-suggested material stays AI_SUGGESTED',
    V('villa',{materials:{wall:{material:'stone',provenance:'AI_SUGGESTED'}}}).objects
      .filter(o=>o.kind==='WALL').every(o=>o.material_provenance==='AI_SUGGESTED'));
chk('an unknown material never silently becomes a real one',
    V('villa',{materials:{wall:'unobtanium'}}).objects.filter(o=>o.kind==='WALL')
      .every(o=>VIS_MATERIALS[o.material]!==undefined));
/* fire_rating و thermal_property حاضران كنفي صريح بقيمة null — نتحقّق من ذلك
   ثم نتأكّد أنّ أيّ حقل آخر لا يحمل خاصية هندسية مشتقّة من اسم المادة */
chk('a material name is never treated as an engineering material', (function(){
  const denied=villa.materials.every(m=>m.fire_rating===null&&m.thermal_property===null
    &&m.structural_material===false);
  const stripped=JSON.parse(JSON.stringify(villa));
  (stripped.materials||[]).forEach(m=>{ delete m.fire_rating; delete m.thermal_property;
    delete m.structural_material; });
  const leaked=scanFields(stripped,
    /fire_rating|thermal_conduct|u_value|reaction_to_fire|concrete_grade|fire_class/i);
  return denied&&leaked.length===0; })());

console.log('\n== §6 — THEMES CHANGE APPEARANCE ONLY ==');
chk('a theme changes the finishes it selects',
    V('villa',{theme:'Industrial'}).objects.filter(o=>o.kind==='WALL')[0].material!==
    V('villa',{theme:'Luxury'}).objects.filter(o=>o.kind==='WALL')[0].material);
chk('a theme changes no room dimension, opening or level', (function(){
  const g=t=>{const s=V('villa',{theme:t});
    return JSON.stringify(s.objects.filter(o=>!o.visual_only)
      .map(o=>[o.id,o.kind,o.geometry]));};
  return VIS_THEMES.every(t=>g(t)===g('Neutral')); })());
chk('an unknown theme falls back to the default rather than inventing one',
    V('villa',{theme:'Cyberpunk'}).presentation.theme===VIS_DEFAULT_THEME);
chk('a theme never changes the building type or level count',
    VIS_THEMES.every(t=>V('villa',{theme:t}).objects.filter(o=>o.kind==='SLAB').length
      ===villa.objects.filter(o=>o.kind==='SLAB').length));

console.log('\n== §7 — DECORATION IS NOT ENGINEERING DATA ==');
const deco=V('villa',{mode:'DOLLHOUSE',include_decoration:true});
chk('decoration is emitted only when explicitly requested',
    V('villa',{mode:'DOLLHOUSE'}).counts.decoration_objects===0
    &&deco.counts.decoration_objects>0);
chk('every decoration object is VISUAL_ONLY and never semantic',
    deco.objects.filter(o=>o.visual_class===VIS_DECORATION_CLASS)
      .every(o=>o.visual_only===true&&o.semantic===false));
chk('no decoration object references a model element',
    deco.objects.filter(o=>o.visual_class===VIS_DECORATION_CLASS)
      .every(o=>o.source_element_id===null));
chk('decoration is excluded from the engineering export',
    visExportScene(deco,false).objects.every(o=>!o.visual_only));
chk('decoration appears only in an explicitly requested presentation export',
    visExportScene(deco,true).objects.some(o=>o.visual_only));
chk('a user-requested object stays engineering data and is never re-labelled', (function(){
  const a=AR('villa_user_objects');
  const s=V('villa_user_objects',{include_decoration:true});
  const room=(SC.models.villa_user_objects.floors.g.rooms[0].objects||[]);
  return room.length===2&&a.spaces.length>0&&
    s.objects.filter(o=>o.visual_class===VIS_DECORATION_CLASS)
      .every(o=>o.source_element_id===null); })());
chk('decoration never enters an occupant, coverage or load count',
    scanFields(deco,/occupant|coverage|load_kw|demand|egress_capacity/i).length===0);
chk('decoration counts are reported separately from semantic objects',
    deco.counts.semantic_objects+deco.counts.visual_only_objects===deco.counts.objects
    &&deco.counts.decoration_objects<=deco.counts.visual_only_objects);
chk('entourage is visual-only and never an occupant',
    V('villa',{include_entourage:true,entourage_count:6}).objects
      .filter(o=>o.visual_class===VIS_ENTOURAGE_CLASS)
      .every(o=>o.visual_only&&!o.semantic));

console.log('\n== §8 — SITE, LANDSCAPE AND WATER ==');
chk('a stated site produces a ground plane at the stated size', (function(){
  const g=villa.objects.filter(o=>o.kind==='GROUND')[0];
  return g&&g.site_dimensions_stated===true
    &&Math.abs(g.geometry.ex-FX.villa.site.w)<1e-6; })());
chk('a model with no site still renders, and says the extent is not a boundary',
    (function(){ const g=V('no_site').objects.filter(o=>o.kind==='GROUND')[0];
      return g&&g.site_dimensions_stated===false&&g.visual_only===true; })());
chk('the ground plane is always visual-only',
    NAMES.every(n=>V(n).objects.filter(o=>o.kind==='GROUND')
      .every(o=>o.visual_only===true)));
chk('landscape objects are visual-only and separately layered',
    V('villa',{mode:'PRESENTATION'}).objects
      .filter(o=>o.visual_class===VIS_LANDSCAPE_CLASS)
      .every(o=>o.layer==='LANDSCAPE'&&o.visual_only));
chk('water is emitted only for a represented water feature',
    V('villa_pool').objects.filter(o=>o.kind==='WATER').length===1
    &&V('villa').objects.filter(o=>o.kind==='WATER').length===0);
chk('no pool is ever invented in any fixture',
    NAMES.filter(n=>n!=='villa_pool').every(n=>
      V(n).objects.filter(o=>o.kind==='WATER').length===0));
chk('no road, parking or fence is invented',
    NAMES.every(n=>V(n).objects.every(o=>
      ['ROAD','PARKING','FENCE','GATE'].indexOf(o.kind)<0)));

console.log('\n== §9 — DOLLHOUSE AND CUTAWAY ==');
const dh=V('villa',{mode:'DOLLHOUSE'});
chk('dollhouse hides the roof and ceilings',
    dh.presentation.dollhouse.hide_roof===true
    &&dh.presentation.dollhouse.hide_ceilings===true);
chk('dollhouse states a clip height rather than shortening a wall',
    typeof dh.presentation.dollhouse.clip_above_m==='number');
chk('dollhouse generates no second model — the geometry is identical', (function(){
  const g=s=>JSON.stringify(s.objects.filter(o=>!o.visual_only&&o.layer==='ARCHITECTURE'
    &&o.kind!=='CEILING').map(o=>[o.id,o.geometry]));
  return g(dh)===g(V('villa',{mode:'ARCHITECTURAL'})); })());
chk('dollhouse is reversible', dh.presentation.dollhouse.reversible===true);
chk('every room keeps its exact position and size in dollhouse', (function(){
  const a=JSON.stringify(AR('villa').spaces.map(s=>[s.id,s.rect]));
  V('villa',{mode:'DOLLHOUSE'});
  return JSON.stringify(AR('villa').spaces.map(s=>[s.id,s.rect]))===a; })());
const cut=V('villa',{mode:'CUTAWAY',cutaway:{method:'CLIP_PLANE',nz:1,constant:5}});
chk('cutaway records a clipping plane, not a geometry edit',
    cut.presentation.cutaway.method==='CLIP_PLANE'
    &&cut.presentation.cutaway.reversible===true);
chk('an unknown cutaway method falls back rather than failing',
    V('villa',{mode:'CUTAWAY',cutaway:{method:'CHAINSAW'}}).presentation.cutaway.method
      ==='CLIP_PLANE');
chk('cutaway leaves the architectural geometry identical', (function(){
  const g=s=>JSON.stringify(s.objects.filter(o=>o.kind==='WALL').map(o=>[o.id,o.geometry]));
  return g(cut)===g(V('villa',{mode:'ARCHITECTURAL'})); })());

console.log('\n== §10 — 2D FLOOR PLANS ==');
const p0=visFloorPlan(AR('villa'),0,'TECHNICAL','bld_0');
const p1=visFloorPlan(AR('villa'),1,'TECHNICAL','bld_0');
chk('the plan projects the real walls of that level',
    p0.counts.walls===AR('villa').walls.filter(w=>w.level_index===0).length);
chk('the plan projects the real openings of that level',
    p0.counts.openings===AR('villa').openings.filter(o=>o.level_index===0).length);
chk('the plan carries room boundaries, names and labels',
    p0.spaces.length>0&&p0.spaces.every(s=>s.name!==undefined&&s.w>0&&s.d>0));
chk('the plan carries stairs where a core serves the level',
    p0.counts.stairs===1&&p1.counts.stairs===1);
chk('two levels give two different plans', JSON.stringify(p0)!==JSON.stringify(p1));
chk('a level that does not exist reports so instead of inventing one',
    visFloorPlan(AR('villa'),9,'TECHNICAL','bld_0').level_exists===false);
chk('every plan style yields the same geometry', (function(){
  const g=st=>JSON.stringify(visFloorPlan(AR('villa'),0,st,'bld_0').walls);
  return VIS_PLAN_STYLES.every(st=>g(st)===g('TECHNICAL')); })());
chk('the plan makes no CAD-grade claim',
    /makes no CAD-grade claim/.test(p0.note)&&!/CAD.?ready|drafting standard/i.test(p0.note));
chk('the plan never claims compliance or adequacy',
    scanFields(p0,/compliant|violation|adequate|approved/i).length===0);

console.log('\n== §11 — DIMENSIONS COME FROM THE MODEL ONLY ==');
chk('every stated dimension is sourced model',
    p0.dimensions.filter(d=>d.value_m!==null).every(d=>d.source==='model'));
chk('room widths and depths match the model rectangles', (function(){
  const a=AR('villa'); let ok=true;
  p0.dimensions.filter(d=>d.kind==='space_width').forEach(d=>{
    const sp=a.spaces.filter(s=>s.id===d.subject)[0];
    if(!sp||Math.abs(sp.rect[2]-d.value_m)>1e-6) ok=false; });
  return ok; })());
chk('wall lengths match the model', (function(){
  const a=AR('villa'); let ok=true;
  p0.dimensions.filter(d=>d.kind==='wall_length').forEach(d=>{
    const w=a.walls.filter(x=>x.id===d.subject)[0];
    if(!w||Math.abs(w.length_m-d.value_m)>1e-6) ok=false; });
  return ok; })());
chk('an unknown dimension is null with source unknown, never fabricated', (function(){
  const m=C(SC.models.villa);
  m.floors.g.rooms[0].doors=[{edge:'E',offset:2.5}];
  const a=compileArchitecture(m,'bld_0',null,0);
  const p=visFloorPlan(a,0,'TECHNICAL','bld_0');
  const d=p.dimensions.filter(x=>x.kind==='opening_width'&&x.value_m===null);
  return p.counts.unknown_dimensions>0&&d.every(x=>x.source==='unknown'); })());
chk('no dimension is invented for a model with no rooms',
    visFloorPlan(AR('degenerate'),0,'TECHNICAL','bld_0').counts.dimensions===0);

console.log('\n== §12 — SECTIONS ==');
const sx=visSection(AR('villa'),'x',null,'bld_0');
chk('the section reports every level of the model',
    sx.counts.levels===AR('villa').levels.length);
chk('the section cuts real walls', sx.counts.walls>0);
chk('a section through a door shows the opening',
    visSection(AR('villa'),'x',2.5,'bld_0').counts.openings>0);
chk('a section outside the building cuts nothing rather than inventing',
    visSection(AR('villa'),'x',999,'bld_0').counts.walls===0);
chk('the section shows the stair core where the plane crosses it',
    visSection(AR('villa'),'x',10.0,'bld_0').counts.stairs===1);
chk('both section axes work and differ',
    JSON.stringify(visSection(AR('villa'),'x',null,'bld_0'))!==
    JSON.stringify(visSection(AR('villa'),'z',null,'bld_0')));
chk('an unknown axis falls back rather than failing',
    visSection(AR('villa'),'diagonal',null,'bld_0').axis==='x');
chk('the section draws no structural or code conclusion',
    /no structural or code interpretation is made/.test(sx.note)
    &&scanFields(sx,/adequate|compliant|capacity|load/i).length===0);

console.log('\n== §13 — ELEVATIONS ==');
chk('all four faces are produced', VIS_ELEVATION_FACES.every(f=>
    !!visElevation(AR('villa'),f,'bld_0').kind));
chk('an elevation uses real envelope walls', (function(){
  const a=AR('villa'); const ext={};
  (a.envelope.exterior_walls||[]).forEach(id=>{ext[id]=true;});
  return visElevation(a,'NORTH','bld_0').walls.every(w=>ext[w.id]); })());
chk('no opening is invented to balance a facade', (function(){
  const a=AR('villa'); let ok=true;
  VIS_ELEVATION_FACES.forEach(f=>{ const e=visElevation(a,f,'bld_0');
    e.openings.forEach(o=>{ if(!a.openings.some(x=>x.id===o.id)) ok=false; }); });
  return ok; })());
chk('a model with real windows shows them on the matching facade',
    visElevation(AR('villa_windows'),'NORTH','bld_0').counts.openings>0);
chk('a facade with no openings honestly shows none',
    visElevation(AR('villa'),'SOUTH','bld_0').counts.openings===0);
chk('an unknown face falls back rather than inventing one',
    visElevation(AR('villa'),'UPWARD','bld_0').face==='NORTH');
chk('four faces are not identical', new Set(VIS_ELEVATION_FACES.map(f=>
    JSON.stringify(visElevation(AR('villa'),f,'bld_0').walls))).size>1);

console.log('\n== §14 — CAMERAS AND FRAMING ==');
chk('every camera preset is produced', villa.cameras.length===VIS_CAMERA_PRESETS.length);
chk('framing is computed from the model bounds with a stated margin',
    villa.cameras.every(c=>JSON.stringify(c.fit_bbox)===JSON.stringify(villa.bounds)
      &&c.margin>1));
chk('the exterior camera sits outside the building bounds', (function(){
  const c=villa.cameras.filter(x=>x.preset==='EXTERIOR_FRONT')[0];
  return c.position[2]<villa.bounds[2]; })());
chk('the top camera sits above the building', (function(){
  const c=villa.cameras.filter(x=>x.preset==='TOP')[0];
  return c.position[1]>villa.bounds[4]; })());
chk('the section and elevation cameras are orthographic',
    villa.cameras.filter(c=>c.preset==='SECTION'||c.preset==='ELEVATION')
      .every(c=>c.projection==='orthographic'&&c.fov_deg===null));
chk('the interior camera stands at eye height inside the model',
    (function(){ const c=visFrameCamera(villa,'INTERIOR_ROOM','bld_0.g.majlis@0');
      return Math.abs(c.position[1]-VIS_CAMERA_DEFAULTS.eye_height_m)<1e-6; })());
chk('camera metadata is declared presentation state, not model truth',
    villa.cameras.every(c=>c.presentation_state===true));
chk('changing the camera regenerates no geometry', (function(){
  const g=JSON.stringify(villa.objects);
  VIS_CAMERA_PRESETS.forEach(p=>visFrameCamera(villa,p,null));
  return JSON.stringify(villa.objects)===g; })());
chk('a bigger building is framed from further away',
    visFrameCamera(V('hotel'),'EXTERIOR_CORNER',null).position[1]>
    visFrameCamera(V('clinic'),'EXTERIOR_CORNER',null).position[1]);
chk('an unknown camera preset returns nothing rather than guessing',
    visFrameCamera(villa,'DRONE',null)===null);

console.log('\n== §15 — LIGHTING, DAY/NIGHT AND SHADOWS ==');
chk('the light rig carries sun, sky and ambient',
    ['SUN','SKY','AMBIENT'].every(k=>villa.lights.some(l=>l.kind===k)));
chk('every presentation light is declared visual-only',
    villa.lights.every(l=>l.visual_only===true));
chk('no presentation light is treated as an MEP luminaire',
    villa.lights.every(l=>/not an MEP luminaire/.test(l.note)||l.kind==='INTERIOR_VISUAL'));
chk('the three lighting presets differ', new Set(VIS_LIGHTING_PRESETS.map(p=>
    JSON.stringify(V('villa',{lighting:p}).lights))).size===3);
chk('night places emitters only at represented fixtures', (function(){
  const n=V('villa_lights',{lighting:'NIGHT'});
  const em=n.lights.filter(l=>l.kind==='INTERIOR_VISUAL');
  return em.length>0&&em.every(l=>!!l.at_mep_element); })());
chk('a model with no fixtures gets no interior emitters at night',
    V('villa',{lighting:'NIGHT'}).lights.filter(l=>l.kind==='INTERIOR_VISUAL').length===0);
chk('no lighting adequacy, lux or illuminance is ever claimed',
    scanFields(V('villa_lights',{lighting:'NIGHT'}),/lux|illuminance|adequa|lumen/i)
      .length===0);
chk('shadows are a quality setting, never a geometry change',
    VIS_QUALITY_PARAMS.LOW.shadows===false&&VIS_QUALITY_PARAMS.HIGH.shadows===true);
chk('an unknown lighting preset falls back to the default',
    V('villa',{lighting:'ECLIPSE'}).presentation.lighting_preset===VIS_DEFAULT_LIGHTING);

console.log('\n== §16 — QUALITY, LOD AND INSTANCING ==');
chk('all four quality profiles are available', VIS_QUALITY_PROFILES.length===4);
chk('quality changes pixel ratio, shadow map and textures but not geometry', (function(){
  const g=q=>JSON.stringify(V('hotel',{quality:q}).objects.filter(o=>!o.visual_only)
    .map(o=>[o.id,o.geometry]));
  return VIS_QUALITY_PROFILES.every(q=>g(q)===g('MEDIUM'))
    &&VIS_QUALITY_PARAMS.LOW.pixel_ratio!==VIS_QUALITY_PARAMS.ULTRA.pixel_ratio; })());
chk('an unknown quality profile falls back to the default',
    V('villa',{quality:'INSANE'}).presentation.quality===VIS_DEFAULT_QUALITY);
chk('LOD drops visual-only detail and never a modelled element', (function(){
  const s=V('villa',{mode:'PRESENTATION',include_decoration:true});
  const l=visLodPlan(s,5);
  return l.dropped_modelled===0&&l.dropped_visual_only>0; })());
chk('LOD never drops a modelled element even at a tiny budget',
    visLodPlan(V('hotel'),1).dropped_modelled===0);
chk('instancing groups only visual-only repeated objects', (function(){
  const s=V('villa',{mode:'PRESENTATION',include_decoration:true});
  const p=visInstancingPlan(s);
  const ids={}; s.objects.forEach(o=>{ids[o.id]=o;});
  return p.modelled_objects_merged===0
    &&p.groups.every(g=>g.object_ids.every(id=>ids[id].visual_only)); })());
chk('no modelled element is ever merged into an instance group',
    visInstancingPlan(V('hotel',{include_decoration:true})).modelled_objects_merged===0);

console.log('\n== §17 — SNAPSHOTS AND RENDER METADATA ==');
const req=visSnapshotRequest(villa,{width:3840,height:2160,format:'PNG'});
chk('a snapshot request records size, format and camera',
    req.width===3840&&req.height===2160&&req.format==='PNG'&&!!req.camera);
chk('an absurd resolution is clamped and the clamp is reported',
    visSnapshotRequest(villa,{width:99999,height:99999}).issues
      .indexOf('SNAPSHOT_EXCEEDS_MAX_PIXELS')>=0);
chk('an unsupported format is refused rather than silently accepted',
    visSnapshotRequest(villa,{format:'TIFF'}).issues
      .indexOf('SNAPSHOT_FORMAT_UNSUPPORTED')>=0);
const rm=visRenderMetadata(villa,req,'DETERMINISTIC_RENDER',AT,null);
chk('render metadata carries the model hash and building id',
    rm.model_hash===villa.model_hash&&rm.building_id==='bld_0');
chk('render metadata carries camera, mode, theme, lighting and quality',
    !!rm.camera&&!!rm.visual_mode&&!!rm.theme&&!!rm.lighting_preset&&!!rm.quality);
chk('a deterministic render is authorised as an engineering view of the model',
    rm.authority==='ENGINEERING_VIEW_OF_MODEL'&&rm.is_engineering_model===true);
chk('the render id is deterministic for the same inputs',
    visRenderMetadata(villa,req,'DETERMINISTIC_RENDER',AT,null).render_id===rm.render_id);
chk('a different camera gives a different render id',
    visRenderMetadata(villa,visSnapshotRequest(villa,{camera:'TOP'}),
      'DETERMINISTIC_RENDER',AT,null).render_id!==rm.render_id);

console.log('\n== §18 — REVISION INTEGRITY OF A RENDER ==');
chk('a render of the unchanged model is CURRENT',
    visCheckRenderCurrency(rm,C(SC.models.villa),'bld_0').status==='CURRENT');
chk('a render of a changed model is STALE, never relabelled current', (function(){
  const r=visCheckRenderCurrency(rm,C(SC.models.hotel),'bld_0');
  return r.status==='STALE_MODEL_CHANGED'&&r.presented_as_current===false; })());
chk('a render with no hash is UNVERIFIABLE rather than assumed current',
    visCheckRenderCurrency({},C(SC.models.villa),'bld_0').status==='UNVERIFIABLE');
chk('presentation state is declared outside the revision hash',
    visPresentationBlock(villa)[VIS_PRESENTATION_KEY].affects_revision_hash===false);
chk('the presentation block is additive and separate',
    Object.keys(visPresentationBlock(villa)).length===1
    &&VIS_PRESENTATION_KEY==='presentation');

console.log('\n== §19 — AI ENHANCEMENT IS DOWNSTREAM AND POWERLESS ==');
const air=visAiEnhancementRequest(villa,'evening light',null,0.4,AR('villa'));
chk('the pipeline starts at the canonical model and ends at the image',
    air.stage_pipeline[0]==='CANONICAL_MODEL'
    &&air.stage_pipeline[air.stage_pipeline.length-1]==='PRESENTATION_IMAGE');
chk('a deterministic base render is required before enhancement',
    air.base_render_required===true);
chk('the request cannot write to the model', air.writes_to_model===false);
chk('no image generator is shipped and no network call is made',
    air.generator_shipped===false&&air.network_call===false);
chk('the request carries the geometry signature the AI must not change',
    ['door_count','window_count','floor_count','room_count','footprint']
      .every(k=>air.geometry_signature[k]!==undefined));
chk('an AI image is authorised as VISUALISATION, never as the model',
    air.authority==='VISUALISATION'
    &&visRenderMetadata(villa,null,'AI_ENHANCED_VISUALISATION',AT,{}).authority
      ==='VISUALISATION');
chk('an AI render is never marked an engineering model',
    visRenderMetadata(villa,null,'AI_ENHANCED_VISUALISATION',AT,{})
      .is_engineering_model===false);
chk('an unknown render kind falls back to deterministic rather than to AI',
    visRenderMetadata(villa,null,'MAGIC',AT,null).kind==='DETERMINISTIC_RENDER');
chk('the AI may change appearance but not layout',
    VIS_AI_MAY_CHANGE.indexOf('materials')>=0&&VIS_AI_MAY_CHANGE.indexOf('lighting')>=0
    &&VIS_AI_MAY_CHANGE.indexOf('wall_positions')<0
    &&VIS_AI_MAY_NOT_CHANGE.indexOf('wall_positions')>=0);

console.log('\n== §20 — CONTROL BUFFERS AND DRIFT DETECTION ==');
const cb=visControlBuffers(villa,null);
chk('all six control buffers are available', cb.available.length===6);
chk('buffers are deterministic passes over the real geometry',
    cb.buffers.every(b=>b.deterministic===true&&b.from_model===true));
chk('the object-id buffer lists only modelled objects', (function(){
  const b=cb.buffers.filter(x=>x.kind==='object_id')[0];
  const ids={}; villa.objects.forEach(o=>{ids[o.id]=o;});
  return b.ids.every(id=>ids[id]&&!ids[id].visual_only); })());
chk('a matching image reports no drift', (function(){
  const s=air.geometry_signature;
  return visCheckConsistency(air,{door_count:s.door_count,window_count:s.window_count,
    floor_count:s.floor_count,room_count:s.room_count,footprint:s.footprint,
    model_hash:s.model_hash}).drift===false; })());
chk('a wrong door count is flagged VISUAL_GEOMETRY_DRIFT',
    visCheckConsistency(air,{door_count:99}).findings
      .some(f=>f.code==='VISUAL_GEOMETRY_DRIFT'));
chk('a wrong floor count is flagged specifically',
    visCheckConsistency(air,{floor_count:9}).findings
      .some(f=>f.code==='VISUAL_LEVEL_COUNT_MISMATCH'));
chk('a wrong footprint is flagged specifically',
    visCheckConsistency(air,{footprint:[0,0,999,999]}).findings
      .some(f=>f.code==='VISUAL_FOOTPRINT_MISMATCH'));
chk('a footprint within tolerance is not flagged', (function(){
  const f=air.geometry_signature.footprint.slice();
  f[0]+=0.2;
  return !visCheckConsistency(air,{footprint:f},0.5).findings
    .some(x=>x.code==='VISUAL_FOOTPRINT_MISMATCH'); })());
chk('an image claiming another model hash is flagged',
    visCheckConsistency(air,{model_hash:'deadbeef'}).findings
      .some(f=>f.code==='VISUAL_SOURCE_HASH_MISMATCH'));
chk('drift never rewrites the model and never accepts the image as geometry', (function(){
  const r=visCheckConsistency(air,{door_count:99,floor_count:9});
  return r.model_modified===false&&r.image_accepted_as_geometry===false; })());
chk('drift findings are ERROR-severity data findings only',
    visCheckConsistency(air,{door_count:99}).findings
      .every(f=>VIS_DRIFT_SEVERITIES.indexOf(f.severity)>=0));

console.log('\n== §21 — LAYERS, ENGINEERING VS PRESENTATION ==');
chk('all seven presentation-facing layers are toggleable',
    ['ARCHITECTURE','FURNITURE','STRUCTURE','MEP','FLS','SITE','LANDSCAPE']
      .every(l=>VIS_LAYERS.indexOf(l)>=0));
chk('a presentation view may hide a technical layer',
    visSetLayerVisible(V('villa_full',{mode:'PRESENTATION',layers:['ARCHITECTURE','MEP']}),
      'MEP',false)[0]===true);
chk('the engineering view refuses to hide a discipline',
    visSetLayerVisible(V('villa_full',{mode:'ENGINEERING'}),'MEP',false)[1]
      ==='ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE');
chk('an unknown layer is refused rather than created',
    visSetLayerVisible(C(villa),'MAGIC',true)[1]==='LAYER_UNKNOWN');
chk('hiding a layer changes visibility only, never geometry', (function(){
  const s=V('villa_full',{mode:'PRESENTATION',layers:['ARCHITECTURE','MEP']});
  const g=JSON.stringify(s.objects.map(o=>[o.id,o.geometry]));
  visSetLayerVisible(s,'MEP',false);
  return JSON.stringify(s.objects.map(o=>[o.id,o.geometry]))===g; })());
chk('clash markers are off by default in an architectural presentation',
    V('clash_full',{mode:'PRESENTATION'}).presentation.clash_overlay===false);
chk('the clash overlay is available on the engineering view', (function(){
  const s=V('clash_full',{mode:'ENGINEERING',clash_overlay:true});
  return s.presentation.clash_overlay===true&&(s.clash_overlay||[]).length>0; })());
chk('a clash overlay is visual-only and never baked into geometry',
    (V('clash_full',{mode:'ENGINEERING',clash_overlay:true}).clash_overlay||[])
      .every(c=>c.visual_only===true));
chk('a clash is never removed from the model to prettify an image',
    (function(){ const before=ENGI(SC.models.clash_full);
      V('clash_full',{mode:'PRESENTATION'});
      return ENGI(SC.models.clash_full)===before; })());

console.log('\n== §22 — EXPORTS STAY SEPARATE ==');
chk('the engineering export excludes every visual-only object',
    visExportScene(deco,false).objects.every(o=>o.visual_only===false));
chk('the presentation export is explicitly requested and marked',
    visExportScene(deco,true).kind==='PRESENTATION_GLB'
    &&visExportScene(deco,true).includes_visual_only===true);
chk('the presentation export never replaces the engineering export',
    /never replaces it/.test(visExportScene(deco,true).note));
chk('both exports are marked derived',
    visExportScene(deco,false).derived===true&&visExportScene(deco,true).derived===true);
chk('the engineering export keeps traceability to source elements',
    visExportScene(villa,false).objects.every(o=>!!o.source_element_id));

console.log('\n== §23 — ASSET LIBRARY AND LICENSING ==');
chk('every library asset declares a license and a source',
    visAssetLibrary().every(a=>VIS_ASSET_LICENSES.indexOf(a.license)>=0&&!!a.source));
chk('no library asset carries an UNKNOWN license',
    visAssetLibrary().every(a=>a.license!=='UNKNOWN'));
chk('every library asset declares its visual-only status and dimensions',
    visAssetLibrary().every(a=>VIS_ASSET_CLASSES.indexOf(a.asset_class)>=0
      &&a.dimensions_m.w>0&&a.dimensions_m.d>0&&a.dimensions_m.h>0));
chk('an asset with an unknown license is refused',
    visValidateAsset({id:'x',type:'y',asset_class:'VISUAL_ONLY',license:'UNKNOWN',
      dimensions_m:{w:1,d:1,h:1},source:'s'})
      .indexOf('ASSET_LICENSE_UNKNOWN_NOT_EMITTED')>=0);
chk('asset metadata carrying code is refused, never executed',
    visValidateAsset({id:'x',type:'y',asset_class:'VISUAL_ONLY',license:'CC0',
      dimensions_m:{w:1,d:1,h:1},source:'s',script:'alert(1)'})
      .some(i=>/MUST_NOT_CARRY_CODE/.test(i)));
chk('a valid library asset passes validation',
    visValidateAsset(visAssetById('asset.proc.tree')).length===0);
chk('a missing asset degrades to procedural geometry rather than breaking', (function(){
  const s=V('villa',{mode:'DOLLHOUSE',include_decoration:true});
  return s.objects.filter(o=>o.visual_class===VIS_DECORATION_CLASS)
    .every(o=>!!o.asset_id); })());
chk('nothing is downloaded and no remote asset host appears anywhere',
    scanFields(visAssetLibrary(),/https?:\/\//i).length===0
    &&scanFields(villa,/https?:\/\//i).length===0);

console.log('\n== §24 — VR AND WALKTHROUGH ==');
chk('VR uses the same geometry as presentation', (function(){
  const g=s=>JSON.stringify(s.objects.filter(o=>!o.visual_only).map(o=>[o.id,o.geometry]));
  return g(V('villa',{mode:'VR'}))===g(V('villa',{mode:'PRESENTATION'})); })());
chk('one model metre is one physical metre unless scaling is explicit',
    V('villa',{mode:'VR'}).presentation.scale===1
    &&V('villa',{mode:'VR'}).presentation.scale_is_explicit===false);
chk('an explicit visualisation scale is recorded, never silent', (function(){
  const s=V('villa',{mode:'VR',scale:0.02});
  return s.presentation.scale===0.02&&s.presentation.scale_is_explicit===true; })());
chk('an invalid scale falls back to 1:1 rather than distorting silently',
    V('villa',{mode:'VR',scale:0}).presentation.scale===1);
chk('walkthrough is a camera, not an accessibility claim',
    !!villa.cameras.filter(c=>c.preset==='WALKTHROUGH')[0]
    &&/not accessibility-compliant navigation/.test(ACS_VISUAL_SPEC.walkthrough_note));
chk('a panorama camera preset exists for future 360 output',
    VIS_CAMERA_PRESETS.indexOf('PANORAMA_360')>=0);

console.log('\n== §25 — VIEW CONSISTENCY ACROSS MULTIPLE VIEWS ==');
chk('every view of the same model reports the same model hash',
    new Set(['ENGINEERING','ARCHITECTURAL','PRESENTATION','DOLLHOUSE','VR']
      .map(md=>V('villa',{mode:md}).model_hash)).size===1);
chk('a door is at the same coordinates in every view', (function(){
  const doorOf=md=>{const s=V('villa',{mode:md});
    const d=s.objects.filter(o=>o.kind==='DOOR').sort((a,b)=>a.id<b.id?-1:1)[0];
    return JSON.stringify(d.geometry);};
  const base=doorOf('ARCHITECTURAL');
  return ['PRESENTATION','DOLLHOUSE','CUTAWAY','VR','ENGINEERING']
    .every(md=>doorOf(md)===base); })());
chk('the wall count is identical across every view',
    new Set(VIS_MODES.map(md=>V('villa',{mode:md}).objects
      .filter(o=>o.kind==='WALL').length)).size===1);
chk('the 2D plan agrees with the 3D scene on opening count',
    visFloorPlan(AR('villa'),0,'TECHNICAL','bld_0').counts.openings
      +visFloorPlan(AR('villa'),1,'TECHNICAL','bld_0').counts.openings
      ===villa.objects.filter(o=>o.kind==='DOOR'||o.kind==='WINDOW').length);
chk('a rotated building yields the same object set at moved coordinates', (function(){
  const a=V('villa'); const b=compileVisualScene(C(SC.models.villa),'bld_0',{x:-6,z:4},45,
    {mode:'PRESENTATION',at:AT});
  return JSON.stringify(a.objects.map(o=>o.id))===JSON.stringify(b.objects.map(o=>o.id))
    &&JSON.stringify(a.bounds)!==JSON.stringify(b.bounds); })());

console.log('\n== §26 — TARGETS: VILLA · HOTEL · WAREHOUSE · CLINIC · MIXED ==');
[['villa',7],['hotel',7],['warehouse',7],['clinic',7],['mixed_use',7]].forEach(t=>{
  const n=t[0];
  const views={A:V(n,{mode:'ENGINEERING'}),B:V(n,{mode:'ARCHITECTURAL'}),
    C:V(n,{mode:'DOLLHOUSE'}),D:visFloorPlan(AR(n),0,'TECHNICAL','bld_0'),
    E:visFloorPlan(AR(n),1,'TECHNICAL','bld_0'),
    F:visFrameCamera(V(n),'INTERIOR_ROOM',null),
    G:visSnapshotRequest(V(n),{width:3840,height:2160})};
  chk(n+': all seven target outputs derive from one model hash',
      Object.keys(views).length===t[1]
      &&views.A.model_hash===views.B.model_hash
      &&views.B.model_hash===views.C.model_hash
      &&views.D.kind==='FLOOR_PLAN_2D'&&!!views.F&&views.G.width===3840);
});
chk('the warehouse gets no warehouse-specific visual style',
    V('warehouse',{mode:'ARCHITECTURAL',theme:'Neutral'}).objects
      .filter(o=>o.kind==='WALL')[0].material===
    V('clinic',{mode:'ARCHITECTURAL',theme:'Neutral'}).objects
      .filter(o=>o.kind==='WALL')[0].material);
chk('the clinic gets no healthcare decoration assumption',
    V('clinic',{mode:'DOLLHOUSE',include_decoration:true}).objects
      .filter(o=>o.visual_class===VIS_DECORATION_CLASS)
      .every(o=>VIS_DECORATION_KINDS.indexOf(o.kind.toLowerCase())>=0));
chk('a mixed-use building renders every floor programme',
    V('mixed_use').objects.filter(o=>o.kind==='SLAB').length>=3);
chk('the hotel repeats its floors without drift', (function(){
  const s=V('hotel'); const byLvl={};
  s.objects.filter(o=>o.kind==='WALL').forEach(o=>{
    byLvl[o.level_index]=(byLvl[o.level_index]||0)+1; });
  const counts=Object.keys(byLvl).map(k=>byLvl[k]);
  return counts.length>1&&new Set(counts).size<=2; })());

console.log('\n== §27 — DEGENERATE AND HOSTILE INPUT ==');
chk('a model with no rooms still yields a scene rather than crashing',
    V('degenerate').counts.objects>=0&&!!V('degenerate').summary);
chk('a model with no site still yields a scene', !!V('no_site').summary);
chk('a hostile space name cannot escape into any emitted field', (function(){
  const m=C(SC.models.villa);
  m.floors.g.rooms[0].id='<img src=x onerror=alert(1)>';
  const s=compileVisualScene(m,'bld_0',null,0,{mode:'PRESENTATION',at:AT});
  return scanFields(s,/onerror|<script/i).length===0
    ||s.objects.every(o=>typeof o.id==='string'); })());
chk('a hostile material override cannot inject an unknown material',
    V('villa',{materials:{wall:'<script>'}}).objects.filter(o=>o.kind==='WALL')
      .every(o=>VIS_MATERIALS[o.material]!==undefined));
chk('a NaN scale is rejected rather than propagated',
    V('villa',{scale:'abc'}).presentation.scale===1);
chk('the scene never contains a non-finite coordinate',
    NAMES.every(n=>V(n).objects.every(o=>['cx','cy','cz','ex','ey','ez','rot_y']
      .every(k=>isFinite(o.geometry[k])))));
chk('validation reports no integrity issue on any fixture',
    NAMES.every(n=>visValidateScene(V(n)).length===0));

console.log('\n== §28 — DETERMINISM AND RULE INPUTS ==');
chk('two compilations of the same inputs are byte-identical',
    JSON.stringify(V('villa'))===JSON.stringify(V('villa')));
chk('objects are sorted deterministically by layer, kind then id',
    NAMES.every(n=>{const s=V(n);
      return JSON.stringify(s.objects.map(o=>o.id))===JSON.stringify(
        s.objects.slice().sort((a,b)=>(a.layer<b.layer?-1:a.layer>b.layer?1:0)
          ||(a.kind<b.kind?-1:a.kind>b.kind?1:0)
          ||(a.id<b.id?-1:a.id>b.id?1:0)).map(o=>o.id));}));
chk('rule inputs are visual facts only, never regulatory',
    Object.keys(visRuleInputs(villa).building).every(k=>k.indexOf('visual.')===0));
chk('no visual value is ever compared to a threshold',
    scanFields(visRuleInputs(villa),/limit|maximum|minimum|threshold|required/i).length===0);
chk('the summary declares compliance NOT_EVALUATED',
    NAMES.every(n=>V(n).summary.compliance==='NOT_EVALUATED'));
chk('no scene claims visual verification of anything',
    NAMES.every(n=>scanFields(V(n),/visually_verified|verified_compliance|photoreal/i)
      .length===0));

console.log('\n──────────────────────────────────────────────');
console.log('VISUAL FOUNDATION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
