/* جسر الطبقة المعمارية — الكود الوحيد في المرحلة 9.2 الذي يلمس THREE.
   كل ما يضيفه قابل للعكس بلا أثر: مجموعات AD_* تُزال، والخامات المبدَّلة
   تُستعاد من الأصل المحفوظ. لا شيء هنا يقرأ أو يكتب النموذج القانوني. */
window.__ACS_AD__={groups:{},savedMats:[],applied:null,lastCfg:null};

function _adGrp(name){
  let g=window.__ACS_AD__.groups[name];
  if(g) return g;
  g=new THREE.Group(); g.name=name;
  g.userData={visual_only:true,presentation_context:true};
  scene.add(g); window.__ACS_AD__.groups[name]=g; return g; }

function _adSaveMat(mesh){
  window.__ACS_AD__.savedMats.push([mesh,mesh.material]); }

function _adClearAll(){
  const A=window.__ACS_AD__;
  Object.keys(A.groups).forEach(k=>{
    const g=A.groups[k]; scene.remove(g);
    g.traverse(o=>{ if(o.isMesh){ o.geometry.dispose();
      if(o.material&&o.material.userData
         &&o.material.userData._adOwned) o.material.dispose(); } }); });
  A.groups={};
  A.savedMats.forEach(([m,orig])=>{ m.material=orig; });
  A.savedMats=[]; A.applied=null; }

function _adBuildingMeshes(){
  const out=[];
  scene.traverse(o=>{
    if(!o.isMesh||!o.name) return;
    let p=o.parent,skip=false;
    while(p){ if(p.name&&(p.name.indexOf('AD_')===0
      ||p.name.indexOf('PQ_')===0)){ skip=true; break; } p=p.parent; }
    if(!skip) out.push(o); });
  return out; }

function _adBounds(meshes){
  const box=new THREE.Box3();
  meshes.forEach(m=>{ box.expandByObject(m); });
  return box; }

function _adExteriorWalls(){
  const meshes=_adBuildingMeshes()
    .filter(m=>m.name.indexOf('WALL|')===0&&m.material
      &&m.material.userData&&m.material.userData.matName==='wall');
  if(!meshes.length) return {walls:[],bounds:null};
  const bounds=_adBounds(meshes);
  const T=0.6;
  const ext=meshes.filter(m=>{
    const b=new THREE.Box3().setFromObject(m);
    return (Math.abs(b.min.x-bounds.min.x)<T
      ||Math.abs(b.max.x-bounds.max.x)<T
      ||Math.abs(b.min.z-bounds.min.z)<T
      ||Math.abs(b.max.z-bounds.max.z)<T); });
  return {walls:ext,bounds:bounds}; }

function _adOwnedMat(params,texKind,texScale){
  const m=new THREE.MeshStandardMaterial(params);
  if(texKind&&typeof getTex==='function'){
    const t=getTex(texKind);
    if(t){ m.map=t; m.bumpMap=t; m.bumpScale=0.05;
      m.userData.texScale=texScale||1.5; } }
  m.userData._adOwned=true; return m; }

function _adMatFromSpec(mid,seedId){
  const r=adMaterial(mid,null);
  if(!r.valid) return null;
  const s=r.material;
  const v=adVariation('scene',String(seedId||mid),mid);
  const c=new THREE.Color(s.base_color);
  const params={color:c,metalness:s.metalness,
    roughness:Math.min(1,Math.max(0,s.roughness+v.roughness_delta))};
  if(s.emissive_intensity>0){ params.emissive=new THREE.Color(s.emissive);
    params.emissiveIntensity=s.emissive_intensity; }
  if(s.opacity<1){ params.transparent=true; params.opacity=s.opacity; }
  const texByProc={stone_courses:'concrete',plaster:'plaster',
    concrete:'concrete',wood:'wood',metal:'metal',tile:'tile',
    asphalt:'asphalt',grass:null};
  const m=_adOwnedMat(params,
    s.procedural_texture?texByProc[s.procedural_texture]||null:null,
    s.texture_scale_m);
  m.userData.adMaterialId=mid; m.userData.visual_only=true;
  return m; }

/* إطارات النوافذ: مشتقّة من ألواح الزجاج الممثَّلة فعلاً — لا فتحة تُمسّ. */
function _adWindowFrames(group,finish){
  let count=0;
  const frameMat=_adOwnedMat({color:new THREE.Color(
    ACS_ARCHDETAIL_SPEC.window_assembly.frame_finishes[finish]),
    metalness:0.85,roughness:0.35},null,null);
  frameMat.userData.visual_only=true;
  _adBuildingMeshes().filter(m=>m.name.indexOf('WINDOW|')===0
      &&m.geometry&&m.geometry.parameters
      &&m.geometry.parameters.width!==undefined).forEach(m=>{
    const g=m.geometry.parameters;
    const alongX=g.width>g.depth;
    const w=alongX?g.width:g.depth, h=g.height;
    const asm=adWindowAssembly({width:w,height:h,id:m.name},finish);
    if(!asm.valid) return;
    const t=asm.assembly.frame.thickness_m;
    const dep=asm.assembly.frame.depth_m+0.02;
    const mk=(dx,dy,ex,ey)=>{
      const geo=alongX?new THREE.BoxGeometry(ex,ey,dep)
                      :new THREE.BoxGeometry(dep,ey,ex);
      const f=new THREE.Mesh(geo,frameMat);
      f.position.copy(m.position);
      if(alongX){ f.position.x+=dx; } else { f.position.z+=dx; }
      f.position.y+=dy;
      f.castShadow=true; f.receiveShadow=true;
      f.name='AD_FRAME|'+m.name;
      f.userData={visual_only:true,source_element_id:m.name,
        provenance:'PRESENTATION_DEFAULT',confidence:'HIGH',
        reason:'frame derived from the represented opening',
        detail_class:'DERIVED_PRESENTATION_DETAIL'};
      group.add(f); count++; };
    mk(0, h/2+t/2, w+2*t, t);          /* علوي */
    mk(0,-h/2-t/2, w+2*t, t);          /* سفلي */
    mk(-w/2-t/2, 0, t, h);             /* يسار */
    mk( w/2+t/2, 0, t, h);             /* يمين */
  });
  return count; }

/* شرائط LED عرضية على حواف الجدران الخارجية العلوية الممثَّلة. */
function _adLedStrips(group){
  const {walls}=_adExteriorWalls();
  let count=0;
  const led=adLed('facade_strip',{represented:walls.length>0,id:'facade'});
  if(!led.valid) return 0;
  const mat=_adOwnedMat({color:new THREE.Color('#fff2d0'),
    emissive:new THREE.Color('#ffe9b8'),
    emissiveIntensity:led.light.emissive_intensity,
    metalness:0,roughness:0.4},null,null);
  mat.userData.visual_only=true;
  walls.forEach(w=>{
    const b=new THREE.Box3().setFromObject(w);
    const sx=b.max.x-b.min.x, sz=b.max.z-b.min.z;
    if(Math.max(sx,sz)<1.2) return;
    const alongX=sx>=sz;
    const geo=alongX
      ?new THREE.BoxGeometry(sx*0.92,led.light.strip_height_m,
        led.light.strip_depth_m)
      :new THREE.BoxGeometry(led.light.strip_depth_m,
        led.light.strip_height_m,sz*0.92);
    const s=new THREE.Mesh(geo,mat);
    s.position.set((b.min.x+b.max.x)/2,b.max.y-0.10,(b.min.z+b.max.z)/2);
    s.name='AD_LED|'+w.name;
    s.userData={visual_only:true,source_element_id:w.name,
      provenance:'USER_VISUAL_OVERRIDE',confidence:'HIGH',
      reason:'visual-only architectural light on a represented host',
      mep_fixture_reused:false,
      detail_class:'REQUESTED_PRESENTATION_DETAIL'};
    group.add(s); count++; });
  return count; }

/* المحيط: أرضية/موقع/تنسيق — كله PRESENTATION_CONTEXT قابل للإزالة. */
function _adContext(group,mode,lod){
  const meshes=_adBuildingMeshes();
  if(!meshes.length) return {planes:0,trees:0};
  const b=_adBounds(meshes);
  const cx=(b.min.x+b.max.x)/2, cz=(b.min.z+b.max.z)/2;
  const w=(b.max.x-b.min.x), d=(b.max.z-b.min.z);
  let planes=0,trees=0;
  const plane=(mat,sx,sz,y)=>{
    const p=new THREE.Mesh(new THREE.BoxGeometry(sx,0.02,sz),mat);
    p.position.set(cx,y,cz); p.receiveShadow=true;
    p.name='AD_CONTEXT_PLANE'+planes;
    p.userData={visual_only:true,presentation_context:true,
      source_element_id:null,provenance:'PRESENTATION_DEFAULT',
      confidence:'HIGH',reason:'neutral presentation context',
      detail_class:'DEFAULT_PRESENTATION_CONTEXT'};
    group.add(p); planes++; return p; };
  if(mode==='NEUTRAL'||mode==='SITE'||mode==='LANDSCAPE')
    plane(_adMatFromSpec('paving_stone','ground')||getMat('floor'),
      w*2.4,d*2.4,b.min.y-0.02);
  if(mode==='SITE'||mode==='LANDSCAPE'){
    plane(_adMatFromSpec('road_asphalt','path')||getMat('floor'),
      Math.max(3,w*0.25),d*1.2,b.min.y-0.005); }
  if(mode==='LANDSCAPE'){
    const n={LOW:6,STANDARD:10,HIGH:14}[lod]||10;
    const trunkGeo=new THREE.CylinderGeometry(0.14,0.18,2.2,6);
    const canGeo=new THREE.IcosahedronGeometry(1.15,0);
    const trunkMat=_adMatFromSpec('tree_bark','trunk');
    const canMat=_adMatFromSpec('foliage','canopy');
    const trunks=new THREE.InstancedMesh(trunkGeo,trunkMat,n);
    const cans=new THREE.InstancedMesh(canGeo,canMat,n);
    const M=new THREE.Matrix4();
    const R=Math.max(w,d)*0.85+4;
    for(let i=0;i<n;i++){
      const a=(i/n)*Math.PI*2;
      const x=cx+Math.cos(a)*R, z=cz+Math.sin(a)*R;
      M.makeTranslation(x,b.min.y+1.1,z); trunks.setMatrixAt(i,M);
      M.makeTranslation(x,b.min.y+2.9,z); cans.setMatrixAt(i,M); }
    trunks.castShadow=true; cans.castShadow=true;
    trunks.name='AD_TREES_TRUNK'; cans.name='AD_TREES_CANOPY';
    const meta={object_id:'AD_TREES',provenance:'PRESENTATION_DEFAULT',
      visual_only:true,presentation_context:true,'class':'tree'};
    trunks.userData=meta; cans.userData=meta;
    group.add(trunks); group.add(cans); trees=n; }
  return {planes:planes,trees:trees}; }

/* تقسيم الواجهة: استبدال معكوس لخامة الجدران الخارجية الممثَّلة فقط. */
function _adFacade(primaryMid){
  const {walls}=_adExteriorWalls();
  if(!walls.length) return 0;
  let n=0;
  walls.forEach(wm=>{
    const mat=_adMatFromSpec(primaryMid,wm.name);
    if(!mat) return;
    _adSaveMat(wm); wm.material=mat; n++; });
  return n; }

window.ACS=window.ACS||{};
window.ACS.adRestore=_adClearAll;

window.ACS.adModelSummary=function(){
  const meshes=_adBuildingMeshes();
  const walls=meshes.filter(m=>m.name.indexOf('WALL|')===0).length;
  const wins=meshes.filter(m=>m.name.indexOf('WINDOW|')===0).length;
  return {exterior_walls:_adExteriorWalls().walls.length,
    walls:walls,windows:wins,accent_band:0,balcony:false,
    parking_bays:0,objects:[],context_enabled:true}; };

window.ACS.adModelMeta=function(){
  return {type:(typeof window.__ACS_MODEL_TYPE__==='string')
    ?window.__ACS_MODEL_TYPE__:null,indoor:false}; };

window.ACS.adApply=function(cfg){
  if(!cfg||cfg.writes_to_model!==false)
    return {applied:false,issues:[adIssue('AD_INVALID_MODE','ERROR',
      'config','refused: configuration must declare writes_to_model '
      +'false')]};
  _adClearAll();
  window.__ACS_AD__.lastCfg=cfg;
  const prof=cfg.detail||{};
  const added={frames:0,leds:0,context_planes:0,trees:0,facade_walls:0};
  if(prof.effective==='DETAIL_OFF'){
    window.__ACS_AD__.applied={applied:true,added:added,
      detail:'DETAIL_OFF'};
    return window.__ACS_AD__.applied; }
  const det=_adGrp(ACS_ARCHDETAIL_SPEC.group_names.detail);
  const lit=_adGrp(ACS_ARCHDETAIL_SPEC.group_names.lighting);
  const ctx=_adGrp(ACS_ARCHDETAIL_SPEC.group_names.context);
  if(prof.window_frames)
    added.frames=_adWindowFrames(det,
      ACS_ARCHDETAIL_SPEC.window_assembly.default_frame_finish);
  const feats=((cfg.diagnostic||{}).features)||[];
  const has=(f,st)=>feats.some(x=>x.feature===f&&x.status===st);
  if(prof.facade_zoning&&cfg.facade_mode==='REQUESTED'
      &&has('facade_material','APPLIED'))
    added.facade_walls=_adFacade('stone_beige');
  if(prof.led_lighting&&has('led_lighting','VISUAL_ONLY_APPLIED'))
    added.leds=_adLedStrips(lit);
  if(cfg.context_mode!=='NONE'){
    const r=_adContext(ctx,cfg.context_mode,prof.landscape_lod);
    added.context_planes=r.planes; added.trees=r.trees; }
  window.__ACS_AD__.applied={applied:true,added:added,
    detail:prof.effective,
    presentation_config_hash:cfg.presentation_config_hash};
  return window.__ACS_AD__.applied; };

/* مكتبة الكائنات العرضية: بناء وصفة واحدة في موضع محسوم مسبقاً. */
window.ACS.adBuildObject=function(kind,opts){
  const o=opts||{};
  const rec=adObjectRecipe(kind,o.dims||null,o.canonical_dims||null,
    o.variant||null);
  if(!rec.valid) return {built:false,issues:rec.issues};
  const pl=adPlacement({kind:kind,canonical_pos:o.canonical_pos||null,
    user_pos:o.position||null,zone:o.zone||null,index:o.index,of:o.of});
  if(!pl.resolved) return {built:false,issues:pl.issues};
  const g=_adGrp(ACS_ARCHDETAIL_SPEC.group_names.staging);
  const [W,D,H]=rec.recipe.dims_m;
  const px=pl.position[0],py=pl.position[1],pz=pl.position[2];
  const grp=new THREE.Group();
  grp.name='AD_OBJ|'+kind;
  grp.userData={visual_only:true,
    source_element_id:(o.source_element_id===undefined)
      ?null:o.source_element_id,
    provenance:rec.recipe.dims_source==='CANONICAL'
      ?'ENGINEERING_VALUE':'PRESENTATION_DEFAULT',
    confidence:rec.recipe.dims_source==='CANONICAL'?'HIGH':'LOW',
    reason:'presentation object from the deterministic recipe library',
    'class':kind,recipe_id:rec.recipe.recipe_id};
  const box=(mid,dx,dy,dz,ex,ey,ez)=>{
    const m=new THREE.Mesh(new THREE.BoxGeometry(ex,ey,ez),
      _adMatFromSpec(mid,kind+dx+'_'+dy)||getMat('furn'));
    m.position.set(dx,dy,dz); m.castShadow=true; m.receiveShadow=true;
    grp.add(m); };
  const cyl=(mid,dx,dy,dz,r,h,rotZ)=>{
    const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,10),
      _adMatFromSpec(mid,kind+'w'+dx)||getMat('frame'));
    m.position.set(dx,dy,dz); if(rotZ) m.rotation.z=rotZ;
    m.castShadow=true; grp.add(m); };
  const cat=rec.recipe.category;
  if(cat==='vehicles'){
    box('automotive_paint',0,H*0.32,0,W,H*0.42,D*0.98);
    box('vehicle_glass',0,H*0.68,-D*0.05,W*0.88,H*0.30,D*0.5);
    for(const sx of[-1,1]) for(const sz of[-1,1])
      cyl('tire_rubber',sx*W*0.42,H*0.16,sz*D*0.32,H*0.16,0.24,
        Math.PI/2);
    box('led_strip',0,H*0.30,D*0.49,W*0.55,H*0.08,0.02);
  } else if(rec.recipe.recipe_id in
      ACS_ARCHDETAIL_SPEC.forklift_recipes){
    box('forklift_body',0,H*0.28,-D*0.10,W,H*0.34,D*0.55);
    box('forklift_body',0,H*0.10,-D*0.34,W*0.9,H*0.16,D*0.28);
    for(const sx of[-1,1])
      box('forklift_mast',sx*W*0.35,H*0.62,-D*0.12,0.07,H*0.62,0.07);
    box('forklift_mast',0,H*0.92,-D*0.12,W*0.75,0.07,0.07);
    for(const sx of[-1,1])
      box('forklift_mast',sx*W*0.30,H*0.60,D*0.40,0.09,H*0.85,0.09);
    for(const sx of[-1,1])
      box('galvanized_metal',sx*W*0.18,0.10,D*0.46,W*0.14,0.06,D*0.42);
    for(const sx of[-1,1]) for(const sz of[-1,1])
      cyl('tire_rubber',sx*W*0.40,0.20,sz*D*0.28,0.20,0.20,Math.PI/2);
  } else if(cat==='landscape'){
    if(kind==='palm'){
      cyl('tree_bark',0,H*0.36,0,W*0.07,H*0.72,0);
      for(let i=0;i<6;i++){ const a=i*Math.PI/3;
        box('foliage',Math.cos(a)*W*0.3,H*0.76,Math.sin(a)*W*0.3,
          W*0.66,0.08,W*0.2); }
    } else if(kind==='hedge'){ box('foliage',0,H*0.5,0,W,H,D);
    } else if(kind==='planter'){
      box('curb_concrete',0,H*0.25,0,W,H*0.5,D);
      box('foliage',0,H*0.75,0,W*0.85,H*0.5,D*0.85);
    } else {
      cyl('tree_bark',0,H*0.22,0,W*0.06,H*0.44,0);
      box('foliage',0,H*0.68,0,W,H*0.55,D); }
  } else if(kind==='bollard'){
    cyl('bollard_paint',0,H*0.5,0,W*0.5,H,0);
  } else if(kind==='wheel_stop'){
    box('curb_concrete',0,H*0.5,0,W,H,D);
  } else if(kind==='traffic_cone'){
    cyl('safety_yellow',0,H*0.5,0,W*0.4,H,0);
  } else if(kind==='parking_bay'){
    box('parking_paint',0,0.011,0,W,0.012,0.10);
    box('parking_paint',-W/2,0.011,D/2-0.05,0.10,0.012,D);
    box('parking_paint', W/2,0.011,D/2-0.05,0.10,0.012,D);
  } else {
    box('painted_metal',0,H*0.5,0,W,H,D); }
  grp.position.set(px,py,pz);
  if(o.rotY) grp.rotation.y=Number(o.rotY)||0;
  g.add(grp);
  let meshCount=0; grp.traverse(x=>{ if(x.isMesh) meshCount++; });
  return {built:true,meshes:meshCount,recipe:rec.recipe,
    placement:pl,authority:adObjectAuthority(
      {canonical:!!o.canonical,requested:!!o.requested,
       context:!!o.context},true)}; };

window.ACS.adMode=function(mode){
  if(ACS_ARCHDETAIL_SPEC.compare_modes.indexOf(mode)<0)
    return {applied:false,issues:[adIssue('AD_INVALID_MODE','ERROR',mode,
      'compare mode is not declared')]};
  if(mode==='ENGINEERING'){
    _adClearAll();
    if(window.ACS.pbrRestore) window.ACS.pbrRestore();
    return {applied:true,mode:mode}; }
  if(mode==='PBR'){ _adClearAll(); return {applied:true,mode:mode}; }
  const cfg=window.__ACS_AD__.lastCfg
    ||((typeof AD!=='undefined')?(AD.currentConfig()||{}).config:null);
  if(!cfg) return {applied:false,issues:[adIssue('AD_INVALID_MODE',
    'ERROR',mode,'no architectural configuration available')]};
  return Object.assign({mode:mode},window.ACS.adApply(cfg)); };

window.ACS.adCapture=function(opts){
  const o=opts||{};
  if(!window.ACS.pbrCapture)
    return {captured:false,issues:[adIssue('AD_THREE_UNAVAILABLE','ERROR',
      'capture','no capture path in this environment')]};
  const shot=window.ACS.pbrCapture(o);
  if(!shot||shot.captured===false) return shot;
  const md=adCaptureMetadata(o.pbr_config||null,
    window.__ACS_AD__.lastCfg||null,
    (o.model_hash===undefined)?null:o.model_hash,
    (o.revision===undefined)?null:o.revision,
    o.width||1920,o.height||1080,null);
  shot.metadata_arch=md.valid?md.metadata:null;
  shot.is_engineering_evidence=false;
  return shot; };
