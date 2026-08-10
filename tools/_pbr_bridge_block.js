/* جسر الجودة البصرية — يعيش في نطاق الوحدة حيث THREE والمشهد الحيّ.
   يطبّق إعداداً عرضياً محسوباً في الطبقة الحتمية على العرض، قابلاً للعكس،
   ولا يقرأ من النموذج القانوني إلا حدوده، ولا يكتب إليه شيئاً أبداً.
   كل كائن يضيفه يحمل PQ_ في اسمه ويوضع في المشهد لا في مجموعة المبنى، فيبقى
   خارج تصدير GLB الهندسي وخارج BIM والتوثيق والكمّيات بالبناء لا بالوعد. */
window.__ACS_PQ__={composer:null,context:null,saved:null,fills:[],applied:null};
/* وصف كائن للمحكّم النقي: الاسم، سلسلة الآباء، أعلام العرض، وصندوقه. */
function _pqDescribe(o){
  const parents=[]; let p=o.parent;
  while(p){ if(p.name) parents.push(p.name); p=p.parent; }
  return {name:o.name||'',is_mesh:!!o.isMesh,parent_names:parents,
    user_data:o.userData||{}}; }

/* حدود المشهد القانونية — الهندسة القانونية وحدها. قبّة السماء والأرضية
   السياقية وحامل اللاعب وكل مجموعة عرضية مستبعَدة صراحةً: إدخالها كان يضخّم
   نصف القطر آلاف الأضعاف فيخرج المشهد من هرم الرؤية ومن القبّة ⇒ شاشة سوداء. */
function _pqSceneBounds(){
  try{
    const box=new THREE.Box3(); let found=0;
    scene.traverse(o=>{
      if(!o.isMesh) return;
      if(!pqBoundsMember(_pqDescribe(o)).included) return;
      box.expandByObject(o); found++; });
    if(!found) return null;
    const c=box.getCenter(new THREE.Vector3());
    const sz=box.getSize(new THREE.Vector3());
    if(![c.x,c.y,c.z,sz.x,sz.y,sz.z].every(v=>isFinite(v))) return null;
    return {cx:c.x,cy:c.y,cz:c.z,min_y:box.min.y,
      size:[sz.x,sz.y,sz.z],member_count:found,
      radius:Math.max(Math.max(sz.x,Math.max(sz.y,sz.z))/2,0.5)};
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
        const _res=pqMaterial(map.material_id,
          (cfg.material_overrides||{})[map.material_id]);
        if(!_res.valid){ report.fallbacks.push('MATERIAL_KEPT'); continue; }
        const def=_res.material;
        /* §7 — بوّابة الأمان: خامة غير صالحة تسقط مفتوحةً إلى خامة الهندسة
           لا إلى جسم أسود أو شفّاف تماماً */
        const _safe=pqMaterialSafe(def);
        if(!_safe.safe){
          report.fallbacks.push('MATERIAL_FAIL_OPEN');
          (_safe.issues||[]).forEach(i=>report.issues.push(i));
          continue; }
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
            /* نطاق SSAO يُشتقّ من حجم النموذج الحقيقي: القيم الثابتة على مشهد
               كبير تجعل الحجب كاملاً فيسودّ الإطار */
            const _b=_pqSceneBounds();
            const _r=(_b&&isFinite(_b.radius))?_b.radius:10;
            ss.kernelRadius=Math.max(0.05,Math.min(_r*0.03,2.0));
            ss.minDistance=Math.max(0.0005,_r*0.00005);
            ss.maxDistance=Math.max(0.02,Math.min(_r*0.02,1.0));
            composer.addPass(ss); }
          if(cfg.quality.antialias==='FXAA_COMPOSER'){
            const fx=new mods[3].ShaderPass(mods[4].FXAAShader);
            fx.material.uniforms.resolution.value.set(
              1/(innerWidth*renderer.getPixelRatio()),
              1/(innerHeight*renderer.getPixelRatio()));
            composer.addPass(fx); }
          composer.addPass(new mods[2].OutputPass());
          composer.setSize(innerWidth,innerHeight);
          window.__ACS_PQ__.composer=composer;
          /* الحلقة تستعمل المؤلِّف؛ فلا بدّ من ملاءمة مقاسه عند كل تحجيم،
             وإلا رُسم بمقاس قديم (إطار فارغ/مشوّه) */
          if(!window.__ACS_PQ__._resizeHooked){
            window.__ACS_PQ__._resizeHooked=true;
            addEventListener('resize',()=>{
              const c=window.__ACS_PQ__.composer;
              if(c&&c.setSize) c.setSize(innerWidth,innerHeight); }); }
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
/* عقد أمان الكاميرا (§8): بعد أي وضع كاميرا، تُعاد ملاءمة مستويي القصّ
   ليحتويا النموذج، وتُقصّ المسافة لتبقى داخل قبّة السماء، ثم يُتحقّق فعلياً
   من تقاطع النموذج مع هرم الرؤية. الفشل يُبلَّغ ولا يُترك أسود صامتاً. */
function _pqApplyCameraSafety(b,pos,target){
  const issues=[];
  if(!b) return {applied:false,issues:[{code:'PQ_BOUNDS_UNAVAILABLE',
    severity:'WARNING',blocking:false,
    message:'no canonical geometry — camera left untouched'}]};
  const cl=pqCameraClip(b,pos);
  cl.issues.forEach(i=>issues.push(i));
  const P=cl.clip.position;
  camera.position.set(P[0],P[1],P[2]);
  camera.near=cl.clip.near; camera.far=cl.clip.far;
  if(typeof innerWidth!=='undefined'&&innerHeight)
    camera.aspect=innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  if(typeof orbit!=='undefined'&&orbit&&orbit.target){
    orbit.target.set(target[0],target[1],target[2]); orbit.update(); }
  const fr=pqFrustumContains({position:P,target:target,fov:camera.fov,
    aspect:camera.aspect,near:camera.near,far:camera.far},b);
  fr.issues.forEach(i=>issues.push(i));
  return {applied:true,clip:cl.clip,frustum:fr,issues:issues}; }

window.ACS.pbrCameraPreset=function(presetName){
  try{
    const b=_pqSceneBounds();
    const r=pqCamera(presetName,b);
    if(!r.valid) return r;
    camera.fov=r.camera.fov; camera.updateProjectionMatrix();
    const safety=_pqApplyCameraSafety(b,r.camera.position,r.camera.target);
    r.safety=safety;
    (safety.issues||[]).forEach(i=>r.issues.push(i));
    if(!safety.applied){
      camera.position.set(r.camera.position[0],r.camera.position[1],
        r.camera.position[2]);
      if(typeof orbit!=='undefined'&&orbit&&orbit.target){
        orbit.target.set(r.camera.target[0],r.camera.target[1],
          r.camera.target[2]); orbit.update(); } }
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

/* ===================== §5 — تشخيص العرض (حقائق عرضية فقط) =================
   يكشف حالة الرسم لا حالة الهندسة: لا يقرأ نموذجاً قانونياً ولا يعدّله،
   ولا يُصدِّر أي قيمة هندسية. وجوده يجعل «أقلعت الصفحة» و«ظهر النموذج»
   سؤالين منفصلين يُجابان بالأرقام لا بالظنّ. */
function _pqViewportLuminance(){
  try{
    const gl=renderer.getContext();
    const w=Math.max(1,Math.min(renderer.domElement.width,320));
    const h=Math.max(1,Math.min(renderer.domElement.height,180));
    const px=new Uint8Array(w*h*4);
    gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);
    let sum=0,sum2=0,dark=0;
    const buckets={};
    const n=w*h;
    for(let i=0;i<n;i++){
      const r=px[i*4],g=px[i*4+1],b=px[i*4+2];
      const l=0.2126*r+0.7152*g+0.0722*b;
      sum+=l; sum2+=l*l;
      if(l<8) dark++;
      buckets[Math.floor(l/16)]=1; }
    const mean=sum/n, varr=Math.max(0,sum2/n-mean*mean);
    return {sampled:n,luminance_mean:Math.round(mean*100)/100,
      luminance_variance:Math.round(varr*100)/100,
      near_black_pct:Math.round((dark/n)*10000)/100,
      luminance_buckets:Object.keys(buckets).length,
      status:(dark/n>0.985||(mean<3&&varr<4))?'BLACK':'NON_BLACK'};
  }catch(e){ return {sampled:0,status:'UNAVAILABLE',
    error:String(e&&e.message||e).slice(0,80)}; } }

window.ACS.renderDiagnostics=function(){
  try{
    const info=renderer.info||{render:{},memory:{}};
    const el=renderer.domElement;
    let meshes=0,visible=0,geoms=0,mats=0,canon=0;
    const seenG={},seenM={};
    scene.traverse(o=>{
      if(!o.isMesh) return;
      meshes++;
      let vis=o.visible, p=o.parent;
      while(vis&&p){ vis=p.visible; p=p.parent; }
      if(vis) visible++;
      if(pqBoundsMember(_pqDescribe(o)).included) canon++;
      if(o.geometry&&!seenG[o.geometry.uuid]){ seenG[o.geometry.uuid]=1; geoms++; }
      if(o.material&&!seenM[o.material.uuid]){ seenM[o.material.uuid]=1; mats++; } });
    const lights={ambient:0,hemisphere:0,directional:0,point:0,spot:0};
    let lightSum=0;
    scene.traverse(o=>{
      if(!o.isLight) return;
      const t=o.isAmbientLight?'ambient':o.isHemisphereLight?'hemisphere'
        :o.isDirectionalLight?'directional':o.isPointLight?'point'
        :o.isSpotLight?'spot':null;
      if(t){ lights[t]++; lightSum+=(o.intensity||0); } });
    const b=_pqSceneBounds();
    const tgt=(typeof orbit!=='undefined'&&orbit&&orbit.target)
      ?[orbit.target.x,orbit.target.y,orbit.target.z]
      :[0,0,0];
    const fr=b?pqFrustumContains({position:[camera.position.x,
        camera.position.y,camera.position.z],target:tgt,fov:camera.fov,
        aspect:camera.aspect,near:camera.near,far:camera.far},b):null;
    let ctxOk=false;
    try{ ctxOk=!!renderer.getContext()&&!renderer.getContext().isContextLost(); }
    catch(e){ ctxOk=false; }
    return {
      renderer_ready:true, webgl_context_ok:ctxOk,
      webgl2:!!renderer.capabilities.isWebGL2,
      canvas_width:el.width, canvas_height:el.height,
      css_width:el.clientWidth, css_height:el.clientHeight,
      device_pixel_ratio:(typeof devicePixelRatio!=='undefined')
        ?devicePixelRatio:1,
      pixel_ratio:renderer.getPixelRatio(),
      draw_calls:info.render?info.render.calls:null,
      triangles:info.render?info.render.triangles:null,
      geometries:info.memory?info.memory.geometries:null,
      textures:info.memory?info.memory.textures:null,
      scene_children:scene.children.length,
      mesh_count:meshes, visible_meshes:visible,
      canonical_meshes:canon,
      geometry_count:geoms, material_count:mats,
      scene_background:scene.background?
        (scene.background.isColor?('#'+scene.background.getHexString())
          :'TEXTURE'):null,
      scene_environment:!!scene.environment,
      model_bounds:b,
      camera_position:[camera.position.x,camera.position.y,camera.position.z],
      camera_target:tgt,
      camera_quaternion:[camera.quaternion.x,camera.quaternion.y,
        camera.quaternion.z,camera.quaternion.w],
      camera_near:camera.near, camera_far:camera.far,
      camera_fov:camera.fov, camera_aspect:camera.aspect,
      projection_matrix_finite:camera.projectionMatrix.elements
        .every(v=>isFinite(v)),
      camera_in_frustum:fr?fr.contains:null,
      camera_frustum_detail:fr,
      lights:lights, light_intensity_sum:Math.round(lightSum*1000)/1000,
      tone_mapping_exposure:renderer.toneMappingExposure,
      shadows_enabled:renderer.shadowMap.enabled,
      shadow_map_size:sun&&sun.shadow?sun.shadow.mapSize.x:null,
      presentation_profile:(window.__ACS_PQ__&&window.__ACS_PQ__.applied)
        ?window.__ACS_PQ__.applied:null,
      archdetail_applied:(window.__ACS_AD__&&window.__ACS_AD__.applied)
        ?window.__ACS_AD__.applied:null,
      composer_active:!!((window.__ACS_PQ__||{}).composer),
      viewport_luminance:_pqViewportLuminance(),
      writes_to_model:false, exposes_canonical_state:false };
  }catch(e){
    return {renderer_ready:false,webgl_context_ok:false,
      error:String(e&&e.message||e).slice(0,160),
      writes_to_model:false,exposes_canonical_state:false}; } };
