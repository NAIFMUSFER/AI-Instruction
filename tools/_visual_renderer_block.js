/* ============ تطبيق وضع العرض البصري على المشهد نفسه ============
   لا يغيّر هندسة النموذج ولا يعيد بناءها: يبدّل المواد والرؤية والقصّ فقط،
   ويضيف الأجسام البصرية إلى المشهد لا إلى مجموعة المبنى، فتبقى خارج تصدير
   GLB الهندسي بالبناء نفسه لا بالوعد. */
let VIS_GROUP=null, VIS_ORIGINAL=null, VIS_STATE=null;
function _visColorOf(o){
  if(o.engineering_color) return o.engineering_color;
  const m=VIS_MATERIALS[o.material];
  return m?m.base_color:'#cccccc'; }
function _visRestore(){
  if(VIS_ORIGINAL){ VIS_ORIGINAL.forEach(e=>{
    try{ e.mesh.material=e.material; e.mesh.visible=e.visible; }catch(err){} });
    VIS_ORIGINAL=null; }
  if(VIS_GROUP){ try{ scene.remove(VIS_GROUP);
    VIS_GROUP.traverse(o=>{ if(o.geometry)o.geometry.dispose();
      if(o.material&&o.material.dispose)o.material.dispose(); }); }catch(err){}
    VIS_GROUP=null; }
  try{ renderer.clippingPlanes=[]; }catch(err){}
  VIS_STATE=null; }
function applyVisualMode(mode,opts){
  if(!lastBuilding||!model) return null;
  _visRestore();
  opts=Object.assign({},opts||{},{mode:mode});
  let sc;
  try{ sc=compileVisualScene(lastBuilding,opts.building_id||'bld_0',null,0,opts); }
  catch(e){ return null; }
  /* فهرسة أجسام المشهد بمعرّف العنصر المصدر كي نلوّن الشبكات القائمة كما هي */
  const byId={};
  sc.objects.forEach(o=>{ if(o.source_element_id) byId[o.source_element_id]=o; });
  VIS_ORIGINAL=[];
  const eng=VIS_ENGINEERING_MODES.indexOf(sc.mode)>=0;
  model.traverse(m=>{
    if(!m.isMesh) return;
    VIS_ORIGINAL.push({mesh:m,material:m.material,visible:m.visible});
    const u=m.userData||{};
    const eid=(u.struct&&u.struct.id)||(u.mep&&u.mep.id)||(u.fls&&u.fls.id)||null;
    const o=eid?byId[eid]:null;
    if(o){ try{ m.material=getMat('frame',_visColorOf(o)); }catch(e){} }
    else if(!eng&&/^(WALL|FLOOR|ROOF|DOOR|WINDOW)\|/.test(m.name||'')){
      const slot=/^WALL/.test(m.name)?'wall':(/^FLOOR/.test(m.name)?'floor':'roof');
      const pal=VIS_THEME_PALETTE[sc.presentation.theme]||{};
      const mid=pal[slot];
      const col=(VIS_MATERIALS[mid]||{}).base_color;
      if(col){ try{ m.material=getMat('frame',col); }catch(e){} } }
    /* الدمى: إخفاء السقف وقصّ ما فوق ارتفاع معلن — رؤية فقط، لا هندسة */
    const dh=sc.presentation.dollhouse;
    if(dh&&m.position&&m.position.y>dh.clip_above_m) m.visible=false;
  });
  /* الأجسام البصرية تُضاف إلى المشهد لا إلى المبنى */
  VIS_GROUP=new THREE.Group(); VIS_GROUP.name='VISUAL_ONLY';
  VIS_GROUP.userData.acs_visual_only=true;
  sc.objects.filter(o=>o.visual_only).forEach(o=>{
    const g=o.geometry;
    if(!(g.ex>0&&g.ey>0&&g.ez>0)) return;
    try{
      const mesh=new THREE.Mesh(new THREE.BoxGeometry(g.ex,g.ey,g.ez),
        getMat('frame',_visColorOf(o)));
      mesh.position.set(g.cx,g.cy,g.cz); mesh.rotation.y=g.rot_y;
      mesh.name='VISUAL|'+o.layer+'|'+o.id;
      mesh.userData.acs_visual_only=true;
      mesh.userData.visual={id:o.id,kind:o.kind,layer:o.layer,
        visual_class:o.visual_class||null,material:o.material,
        material_provenance:o.material_provenance};
      VIS_GROUP.add(mesh);
    }catch(e){}
  });
  scene.add(VIS_GROUP);
  /* إضاءة التقديم — طبقة بصرية مستقلّة عن وحدات إنارة MEP */
  const p=VIS_LIGHTING_PARAMS[sc.presentation.lighting_preset];
  try{
    setSun(p.sun_elevation_deg,p.sun_azimuth_deg);
    sun.intensity=p.sun_intensity;
    sun.color.set(p.sun_color);
    sun.castShadow=!!sc.presentation.quality_params.shadows;
    if(sc.presentation.quality_params.shadow_map)
      sun.shadow.mapSize.set(sc.presentation.quality_params.shadow_map,
        sc.presentation.quality_params.shadow_map);
    renderer.toneMapping=(sc.presentation.quality_params.tone_mapping==='aces')
      ?THREE.ACESFilmicToneMapping:THREE.NoToneMapping;
    renderer.toneMappingExposure=sc.environment.exposure;
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,
      sc.presentation.quality_params.pixel_ratio));
  }catch(e){}
  /* القصّ: مستويات قصّ قابلة للعكس، ولا تمسّ الهندسة */
  try{
    const cu=sc.presentation.cutaway;
    if(cu){ renderer.localClippingEnabled=true;
      renderer.clippingPlanes=[new THREE.Plane(
        new THREE.Vector3(cu.normal[0],cu.normal[1],cu.normal[2]),cu.constant_m)]; }
  }catch(e){}
  VIS_STATE={mode:sc.mode,scene_id:sc.scene_id,model_hash:sc.model_hash,
    objects:sc.counts.objects,visual_only:sc.counts.visual_only_objects};
  return {mode:sc.mode,scene_id:sc.scene_id,model_hash:sc.model_hash,
    summary:sc.summary,
    note:'presentation state applied to the existing scene; the model geometry is '+
         'unchanged and no visual object is part of the building group'}; }
function clearVisualMode(){ _visRestore(); return true; }
