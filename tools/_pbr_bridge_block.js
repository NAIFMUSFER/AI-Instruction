/* جسر الجودة البصرية — يعيش في نطاق الوحدة حيث THREE والمشهد الحيّ.
   يطبّق إعداداً عرضياً محسوباً في الطبقة الحتمية على العرض، قابلاً للعكس،
   ولا يقرأ من النموذج القانوني إلا حدوده، ولا يكتب إليه شيئاً أبداً.
   كل كائن يضيفه يحمل PQ_ في اسمه ويوضع في المشهد لا في مجموعة المبنى، فيبقى
   خارج تصدير GLB الهندسي وخارج BIM والتوثيق والكمّيات بالبناء لا بالوعد. */
window.__ACS_PQ__={composer:null,context:null,saved:null,fills:[],applied:null};
function _pqSceneBounds(){
  try{
    const box=new THREE.Box3();
    let found=false;
    scene.traverse(o=>{
      if(o.isMesh&&o.name!=='PQ_CONTEXT'&&!o.userData.acs_debug_only
        &&(!o.parent||o.parent.name!=='PQ_CONTEXT')
        &&(!o.parent||o.parent.name!=='VISUAL_ONLY')){
        box.expandByObject(o); found=true; } });
    if(!found) return null;
    const c=box.getCenter(new THREE.Vector3());
    const s=box.getSize(new THREE.Vector3());
    return {cx:c.x,cy:c.y,cz:c.z,min_y:box.min.y,
      radius:Math.max(s.x,s.y,s.z)/2||10};
  }catch(e){ return null; } }
window.ACS.pbrBounds=_pqSceneBounds;
window.ACS.pbrCaps=function(){
  try{
    const gl=renderer.getContext();
    return {webgl2:renderer.capabilities.isWebGL2,
      max_texture_size:renderer.capabilities.maxTextureSize,
      device_pixel_ratio:(typeof devicePixelRatio!=='undefined')
        ?devicePixelRatio:1};
  }catch(e){ return {webgl2:false,max_texture_size:2048,
    device_pixel_ratio:1}; } };
function _pqSaveOriginals(){
  if(window.__ACS_PQ__.saved) return;
  const saved={mats:{},exposure:renderer.toneMappingExposure,
    pixelRatio:renderer.getPixelRatio(),
    shadow:{enabled:renderer.shadowMap.enabled,
      mapSize:sun.shadow.mapSize.x,bias:sun.shadow.bias},
    sunIntensity:sun.intensity,sunColor:sun.color.getHex(),
    environment:scene.environment,background:scene.background};
  for(const key in matCache){
    const m=matCache[key];
    saved.mats[key]={material:m,roughness:m.roughness,metalness:m.metalness,
      color:m.color?m.color.getHex():null,
      emissiveIntensity:m.emissiveIntensity};
  }
  window.__ACS_PQ__.saved=saved; }
function _pqRestore(){
  const s=window.__ACS_PQ__.saved;
  if(!s) return {restored:false};
  for(const key in s.mats){
    const rec=s.mats[key], m=rec.material;
    /* استُبدلت المادّة بزجاج فيزيائي؟ أعد الأصل إلى كل الأجسام */
    if(m.userData._pqReplacement){
      scene.traverse(o=>{ if(o.isMesh&&o.material===m.userData._pqReplacement)
        o.material=m; });
      m.userData._pqReplacement.dispose&&m.userData._pqReplacement.dispose();
      delete m.userData._pqReplacement; }
    m.roughness=rec.roughness; m.metalness=rec.metalness;
    if(rec.color!==null&&m.color) m.color.setHex(rec.color);
    m.emissiveIntensity=rec.emissiveIntensity; m.needsUpdate=true; }
  renderer.toneMappingExposure=s.exposure;
  renderer.setPixelRatio(s.pixelRatio);
  renderer.shadowMap.enabled=s.shadow.enabled;
  sun.intensity=s.sunIntensity; sun.color.setHex(s.sunColor);
  scene.environment=s.environment; scene.background=s.background;
  window.__ACS_PQ__.fills.forEach(f=>{ scene.remove(f); });
  window.__ACS_PQ__.fills=[];
  if(window.__ACS_PQ__.context){ scene.remove(window.__ACS_PQ__.context);
    window.__ACS_PQ__.context=null; }
  if(window.__ACS_PQ__.composer){ window.__ACS_PQ__.composer=null; }
  window.__ACS_PQ__.applied=null;
  return {restored:true}; }
window.ACS.pbrRestore=_pqRestore;
window.ACS.pbrApply=function(cfg){
  const report={applied:false,issues:[],changed:[],fallbacks:[],
    model_untouched:true,visual_only:true};
  try{
    if(!cfg||cfg.writes_to_model!==false){
      report.issues.push({code:'PQ_INVALID_OVERRIDE',severity:'ERROR',
        blocking:true,message:'a presentation config must declare '+
        'writes_to_model:false'});
      return report; }
    _pqSaveOriginals();
    /* 1. التعريض ونسبة البكسل والظلال */
    renderer.toneMappingExposure=cfg.exposure;
    renderer.setPixelRatio(Math.min(
      (typeof devicePixelRatio!=='undefined')?devicePixelRatio:1,
      cfg.quality.pixel_ratio));
    report.changed.push('exposure','pixel_ratio');
    const shadowsOn=(cfg.shadows_enabled!==false)&&cfg.lighting.shadows;
    renderer.shadowMap.enabled=shadowsOn;
    if(shadowsOn&&cfg.shadow){
      sun.castShadow=true;
      sun.shadow.mapSize.set(cfg.shadow.map_size,cfg.shadow.map_size);
      sun.shadow.bias=cfg.shadow.bias;
      sun.shadow.normalBias=cfg.shadow.normal_bias;
      sun.shadow.radius=cfg.shadow.radius_px;
      const c=cfg.shadow.camera;
      sun.shadow.camera.left=c.left; sun.shadow.camera.right=c.right;
      sun.shadow.camera.top=c.top; sun.shadow.camera.bottom=c.bottom;
      sun.shadow.camera.near=c.near; sun.shadow.camera.far=c.far;
      sun.shadow.camera.updateProjectionMatrix();
      if(sun.shadow.map){ sun.shadow.map.dispose(); sun.shadow.map=null; }
      report.changed.push('shadows'); }
    /* 2. الشمس والملء — أضواء عرضية فقط، لا صلة بتجهيزات MEP */
    const L=cfg.lighting;
    setSun(L.sun_elevation_deg,L.sun_azimuth_deg);
    sun.intensity=L.sun_intensity; sun.color.set(L.sun_color);
    window.__ACS_PQ__.fills.forEach(f=>{ scene.remove(f); });
    window.__ACS_PQ__.fills=[];
    (L.fills||[]).forEach(f=>{
      const d=new THREE.DirectionalLight(f.color,f.intensity);
      const el=f.elevation_deg*Math.PI/180, az=f.azimuth_deg*Math.PI/180;
      d.position.set(Math.cos(el)*Math.sin(az),Math.sin(el),
        Math.cos(el)*Math.cos(az)).multiplyScalar(120);
      d.name='PQ_FILL'; d.userData.visual_only=true; d.castShadow=false;
      scene.add(d); window.__ACS_PQ__.fills.push(d); });
    report.changed.push('lighting');
    /* 3. البيئة (PMREM محلي — لا HDRI بعيد) */
    try{
      if(cfg.environment.mode==='SKY'){
        scene.environment=pmrem.fromScene(sky,0.02).texture;
        scene.background=(L.background==='SKY')?null:scene.background;
      } else {
        scene.environment=pmrem.fromScene(new RoomEnvironment(),0.04).texture; }
      report.changed.push('environment');
    }catch(e){
      report.fallbacks.push('ENVIRONMENT_KEPT'); }
    /* 4. الخامات — مظهر عرضي قابل للعكس؛ لا قيمة تدخل النموذج */
    if(cfg.materials_mode==='REALISTIC'){
      for(const key in matCache){
        const m=matCache[key], name=m.userData.matName;
        const map=pqMaterialForEngineering(name);
        if(!map.mapped) continue;                 /* غير المصنَّف يبقى كما هو */
        const def=pqMaterial(map.material_id,
          (cfg.material_overrides||{})[map.material_id]).material;
        if(def.three_material==='physical'&&name==='window'){
          if(!m.userData._pqReplacement){
            const g=new THREE.MeshPhysicalMaterial({
              color:new THREE.Color(def.base_color),
              roughness:def.roughness,metalness:def.metalness,
              transmission:def.transmission,ior:def.ior,
              thickness:def.thickness_m,transparent:true,
              opacity:def.opacity==null?1:def.opacity});
            g.userData.visual_only=true;
            m.userData._pqReplacement=g; }
          scene.traverse(o=>{ if(o.isMesh&&o.material===m)
            o.material=m.userData._pqReplacement; });
        } else {
          m.roughness=def.roughness; m.metalness=def.metalness;
          if(def.emissive&&m.emissive){ m.emissive.set(def.emissive);
            m.emissiveIntensity=def.emissive_intensity; }
          m.needsUpdate=true; } }
      report.changed.push('materials');
    } else { _pqRestoreMaterialsOnly(); }
    /* 5. أرضية سياق عرضية — في المشهد لا في مجموعة المبنى */
    if(window.__ACS_PQ__.context){ scene.remove(window.__ACS_PQ__.context);
      window.__ACS_PQ__.context=null; }
    if(cfg.ground_context_enabled){
      const b=_pqSceneBounds();
      if(b){
        const gDef=pqMaterial(
          ACS_PBR_SPEC.ground_context.default_ground_material).material;
        const size=b.radius*2*ACS_PBR_SPEC.ground_context.size_factor;
        const ground=new THREE.Mesh(new THREE.PlaneGeometry(size,size),
          new THREE.MeshStandardMaterial({
            color:new THREE.Color(gDef.base_color),
            roughness:gDef.roughness,metalness:gDef.metalness}));
        ground.rotation.x=-Math.PI/2;
        ground.position.set(b.cx,(b.min_y||0)-0.02,b.cz);
        ground.receiveShadow=true;
        ground.name='PQ_CONTEXT'; ground.userData.visual_only=true;
        scene.add(ground);
        window.__ACS_PQ__.context=ground;
        report.changed.push('ground_context'); } }
    /* 6. معالجة لاحقة اختيارية — فشلها تراجع نظيف، لا شاشة فارغة */
    window.__ACS_PQ__.composer=null;
    if(cfg.quality.post_processing&&(cfg.ssao_enabled||cfg.quality.antialias==='FXAA_COMPOSER')){
      Promise.all([
        import('three/addons/postprocessing/EffectComposer.js'),
        import('three/addons/postprocessing/RenderPass.js'),
        import('three/addons/postprocessing/OutputPass.js'),
        import('three/addons/postprocessing/ShaderPass.js'),
        import('three/addons/shaders/FXAAShader.js'),
        (cfg.ssao_enabled?import('three/addons/postprocessing/SSAOPass.js')
          :Promise.resolve(null))
      ]).then(mods=>{
        try{
          const composer=new mods[0].EffectComposer(renderer);
          composer.addPass(new mods[1].RenderPass(scene,camera));
          if(cfg.ssao_enabled&&mods[5]){
            const ss=new mods[5].SSAOPass(scene,camera,innerWidth,innerHeight);
            ss.kernelRadius=0.5; ss.minDistance=0.001; ss.maxDistance=0.15;
            composer.addPass(ss); }
          if(cfg.quality.antialias==='FXAA_COMPOSER'){
            const fx=new mods[3].ShaderPass(mods[4].FXAAShader);
            fx.material.uniforms.resolution.value.set(
              1/(innerWidth*renderer.getPixelRatio()),
              1/(innerHeight*renderer.getPixelRatio()));
            composer.addPass(fx); }
          composer.addPass(new mods[2].OutputPass());
          window.__ACS_PQ__.composer=composer;
        }catch(e){ window.__ACS_PQ__.composer=null;
          report.fallbacks.push('POST_UNAVAILABLE'); }
      }).catch(()=>{ window.__ACS_PQ__.composer=null;
        report.fallbacks.push('POST_UNAVAILABLE'); }); }
    window.__ACS_PQ__.applied=cfg.presentation_config_hash;
    report.applied=true;
    report.presentation_config_hash=cfg.presentation_config_hash;
    return report;
  }catch(e){
    report.issues.push({code:'PQ_POST_UNAVAILABLE',severity:'WARNING',
      blocking:false,message:String(e&&e.message||e).slice(0,120)});
    return report; } };
function _pqRestoreMaterialsOnly(){
  const s=window.__ACS_PQ__.saved;
  if(!s) return;
  for(const key in s.mats){
    const rec=s.mats[key], m=rec.material;
    if(m.userData._pqReplacement){
      scene.traverse(o=>{ if(o.isMesh&&o.material===m.userData._pqReplacement)
        o.material=m; }); }
    m.roughness=rec.roughness; m.metalness=rec.metalness;
    if(rec.color!==null&&m.color) m.color.setHex(rec.color);
    m.emissiveIntensity=rec.emissiveIntensity; m.needsUpdate=true; } }
window.ACS.pbrCameraPreset=function(presetName){
  try{
    const b=_pqSceneBounds();
    const r=pqCamera(presetName,b);
    if(!r.valid) return r;
    camera.fov=r.camera.fov; camera.updateProjectionMatrix();
    camera.position.set(r.camera.position[0],r.camera.position[1],
      r.camera.position[2]);
    if(typeof orbit!=='undefined'&&orbit&&orbit.target){
      orbit.target.set(r.camera.target[0],r.camera.target[1],
        r.camera.target[2]); orbit.update(); }
    return r;
  }catch(e){ return {valid:false,camera:null,
    issues:[{code:'PQ_THREE_UNAVAILABLE',severity:'ERROR',blocking:false,
      message:String(e&&e.message||e).slice(0,120)}]}; } };
window.ACS.pbrCapture=function(opts){
  try{
    const o=opts||{};
    const w=Math.min(o.width||1920,ACS_PBR_SPEC.capture.max_dimension_px);
    const h=Math.min(o.height||1080,ACS_PBR_SPEC.capture.max_dimension_px);
    const pw=renderer.domElement.width, ph=renderer.domElement.height;
    renderer.setSize(w,h,false);
    camera.aspect=w/h; camera.updateProjectionMatrix();
    if(window.__ACS_PQ__.composer) window.__ACS_PQ__.composer.render();
    else renderer.render(scene,camera);
    const url=renderer.domElement.toDataURL('image/png');
    renderer.setSize(pw,ph,false);
    camera.aspect=pw/ph; camera.updateProjectionMatrix();
    const mh=(window.ACS&&window.ACS.workspace&&window.ACS.workspace.project)
      ?null:null;
    const cfgHash=window.__ACS_PQ__.applied;
    const md=pqCaptureMetadata({presentation_config_hash:cfgHash,
      materials_mode:null,exposure:renderer.toneMappingExposure},
      mh,w,h,null);
    return {captured:true,data_url:url,metadata:md.metadata,
      is_engineering_evidence:false};
  }catch(e){ return {captured:false,
    issues:[{code:'PQ_THREE_UNAVAILABLE',severity:'ERROR',blocking:false,
      message:String(e&&e.message||e).slice(0,120)}]}; } };
