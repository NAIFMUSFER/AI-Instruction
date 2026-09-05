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
/* سلطةُ حدودٍ واحدة. كانت هنا حسبةٌ ثانية ساذجة (اتّحاد Box3 لكل الأعضاء)
   موازيةً لطبقة الاسترداد pqRobustBounds التي تستبعد العنصر التالف وتُبلّغ عنه.
   فكانت الكاميرا تُصالَح على الحدود المحصَّنة بينما تُبنى الأرضية السياقية
   ونطاق SSAO وإعدادات الكاميرا وتشخيص model_bounds على الحدود الملوَّثة:
   إحداثيّةٌ شاردة واحدة عند x=99999 أعطت model_bounds بنصف قطر ٥٠ كم
   (مقيس في CI على live_large_generated_outlier) والمنظرُ سليم. الآن تمرّ
   الحدود كلّها من الطبقة المحصَّنة نفسها، بالشكل نفسه الذي كان يعيده هذا
   الملفّ: {cx,cy,cz,min_y,size,radius,member_count} أو null بلا هندسة. */
function _pqSceneBounds(){
  try{
    const rb=_pqRobustSceneBounds();
    if(!rb||!rb.valid||!rb.bounds) return null;
    const b=rb.bounds;
    if(![b.cx,b.cy,b.cz,b.min_y,b.radius].every(v=>isFinite(v))) return null;
    return Object.assign({},b,{member_count:rb.member_count||0});
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

/* التشخيص التفصيلي للعرض (العقد القديم، بكل مفاتيحه) — صار باسمه الصريح
   renderDiagnosticsDetail، لأن window.ACS.renderDiagnostics صار عقداً
   مضبوط المفاتيح يعيش في سكربت الوحدة المكتوب يدوياً (F-08). */
window.ACS.renderDiagnosticsDetail=function(){
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


/* ============ §6 — تشخيص المحاذاة (حقائق عرضية فقط، بلا تحريك) ==========
   يقيس المشهد الحقيقي بعد تحديث مصفوفات العالم، ويصنّف احتواء كل كائن
   مستضاف داخل غرفته، ويحسب خطأ ارتفاع السطح وأدوار المبنى. لا يحرّك جسماً
   ولا يلمس النموذج القانوني: يبلّغ فقط (§7/§17). */
function _pqTagParts(o){
  const n=o.name||'';
  const i=n.indexOf('|');
  if(i<0) return null;
  const p=n.split('|');
  return {layer:p[0],floor:p[1]||null,room:p[2]||null,rest:p[3]||null}; }

function _pqWorldBox(o){
  /* §8 — لا قياس قبل تحديث مصفوفة العالم */
  o.updateMatrixWorld(true);
  const b=new THREE.Box3().setFromObject(o);
  if(!isFinite(b.min.x)||!isFinite(b.max.x)) return null;
  return {min:[b.min.x,b.min.y,b.min.z],max:[b.max.x,b.max.y,b.max.z]}; }

window.ACS.alignmentDiagnostics=function(){
  try{
    if(typeof model==='undefined'||!model)
      return {objects_checked:0,canonical_hosts_checked:0,
        unresolved_transforms:0,detached_objects:0,outside_host_objects:0,
        roof_alignment:null,level_alignment:[],max_position_error_m:null,
        issues:[{code:'ALIGN_TRANSFORM_UNRESOLVED',severity:'WARNING',
          blocking:false,message:'no canonical model is loaded'}],
        writes_to_model:false};
    scene.updateMatrixWorld(true);
    const fh=(lastBuilding&&Number(lastBuilding.floor_height))||3.2;
    /* أصول الغرف من البيانات القانونية نفسها لا من المشهد */
    const hosts={};
    const levelsSeen={};
    const inputLevels=((lastBuilding||{}).levels||[]);
    const renderedLevels=(Array.isArray(inputLevels)?inputLevels:[])
      .slice(0,SCENE_LIMITS.max_levels).map(acsRenderLevel);
    renderedLevels.forEach(resolved=>{
      const lv=resolved.raw, li=resolved.index;
      const tmpl=(((lastBuilding||{}).floors)||{})[lv.template]||{};
      levelsSeen['F'+li]={index:li,derived:resolved.derived,rects:[]};
      (tmpl.rooms||[]).forEach(r=>{
        if(!Array.isArray(r.rect)||r.rect.length!==4) return;
        const key='F'+li+'|'+(r.id||'room');
        const y=pqLevelBaseY(li,fh).base_y;
        const H=Number(r.wall_h)||Number((lastBuilding||{}).wall_h)||3.0;
        hosts[key]={rect:r.rect,level_index:li,base_y:y,
          box:{min:[r.rect[0],y,r.rect[1]],
               max:[r.rect[0]+r.rect[2],y+H,r.rect[1]+r.rect[3]]}};
        levelsSeen['F'+li].rects.push(r.rect); }); });
    const issues=[];
    let checked=0,unresolved=0,outside=0,detached=0,maxErr=0;
    const hosted={INSIDE:0,INTERSECTING_BOUNDARY:0,OUTSIDE:0,UNRESOLVED:0};
    const sample=[];
    model.traverse(o=>{
      if(!o.isMesh) return;
      const t=_pqTagParts(o);
      if(!t) return;
      if(['FURN','OBJ'].indexOf(t.layer)<0) return;   /* الكائنات المستضافة */
      checked++;
      const key=t.floor+'|'+t.room;
      const h=hosts[key];
      if(!h){ unresolved++; hosted.UNRESOLVED++;
        if(issues.length<40) issues.push({code:'ALIGN_HOST_NOT_FOUND',
          severity:'WARNING',blocking:false,element_id:o.name,
          message:'no canonical host rectangle for '+key});
        return; }
      const wb=_pqWorldBox(o);
      if(!wb){ unresolved++; hosted.UNRESOLVED++;
        if(issues.length<40) issues.push({code:'ALIGN_TRANSFORM_UNRESOLVED',
          severity:'WARNING',blocking:false,element_id:o.name,
          message:'world bounds could not be measured'});
        return; }
      const c=pqContainment(wb,h.box);
      hosted[c.classification]++;
      if(c.classification==='OUTSIDE'){
        outside++;
        const dx=Math.max(h.box.min[0]-wb.max[0],wb.min[0]-h.box.max[0],0);
        const dz=Math.max(h.box.min[2]-wb.max[2],wb.min[2]-h.box.max[2],0);
        const err=Math.max(dx,dz);
        if(err>maxErr) maxErr=err;
        if(sample.length<12) sample.push({element_id:o.name,host:key,
          error_m:Math.round(err*1000)/1000,
          classification:c.classification});
        if(issues.length<40) issues.push({code:'ALIGN_OBJECT_OUTSIDE_HOST',
          severity:'WARNING',blocking:false,element_id:o.name,
          message:'outside its host by '+err.toFixed(3)+' m'}); } });
    /* محاذاة الأدوار والسطح من الشبكات الفعلية */
    const levelAlign=[];
    Object.keys(levelsSeen).sort().forEach(k=>{
      const L=levelsSeen[k];
      const expect=pqLevelBaseY(L.index,fh).base_y;
      let minY=Infinity;
      model.traverse(o=>{
        if(!o.isMesh) return;
        const t=_pqTagParts(o);
        if(!t||t.floor!==k||t.layer!=='FLOOR') return;
        const wb=_pqWorldBox(o);
        if(wb) minY=Math.min(minY,wb.max[1]); });
      const actual=isFinite(minY)?minY:null;
      const err=(actual===null)?null:Math.abs(actual-expect);
      if(err!==null&&err>maxErr) maxErr=err;
      if(err!==null&&err>Number(PQ_TC.roof_tolerance_m)){
        detached++;
        issues.push({code:'ALIGN_LEVEL_MISMATCH',severity:'WARNING',
          blocking:false,element_id:k,
          message:'level plate top is '+err.toFixed(3)+' m from '
            +expect.toFixed(3)+' m'}); }
      levelAlign.push({level:k,index:L.index,
        index_source:L.derived?'ARRAY_ORDER_RENDER_FALLBACK':'MODEL_INDEX',
        expected_base_y:expect,
        actual_plate_top_y:actual,
        error_m:(err===null)?null:Math.round(err*1000)/1000,
        aligned:(err!==null&&err<=Number(PQ_TC.roof_tolerance_m))}); });
    /* PHASE10_FOOTPRINT_PLATE (KI-3): امتداد لوح الدور صار اتحاد بصمات غرفه
       عبر pqPlateRect وحده، والاصطلاح السابق PHASE1_SITE_WIDE_PLATE مسجَّل
       هنا بسببه فلا يكون التغيير صامتاً. الفرق الآن يُقاس على اللوح المرسوم
       فعلاً في المشهد لا على الاصطلاح: فإن عاد لوحٌ يتجاوز بصمة دوره بأكثر
       من متر رُفع ALIGN_ROOF_DETACHED لأيّ دور — لا للأدوار العليا وحدها. */
    const renderedPlate={};
    model.traverse(o=>{
      if(!o.isMesh) return;
      const t=_pqTagParts(o);
      if(!t||t.layer!=='FLOOR'||!t.rest
         ||String(t.rest).indexOf('slab')!==0) return;
      const wb=_pqWorldBox(o);
      if(!wb) return;
      const cur=renderedPlate[t.floor];
      renderedPlate[t.floor]=cur
        ?[Math.min(cur[0],wb.min[0]),Math.min(cur[1],wb.min[2]),
          Math.max(cur[2],wb.max[0]),Math.max(cur[3],wb.max[2])]
        :[wb.min[0],wb.min[2],wb.max[0],wb.max[2]]; });
    const plateOverhang=[];
    Object.keys(levelsSeen).sort().forEach(k=>{
      const L=levelsSeen[k];
      if(!L.rects.length) return;
      const site=((lastBuilding||{}).site)||{};
      const sw=Number(site.w)||0, sd=Number(site.d)||0;
      const pr=pqPlateRect(L.rects,[0,0,sw,sd]).rect;
      if(!pr||!(sw>0&&sd>0)) return;
      const ratio=(sw*sd)/Math.max(pr[2]*pr[3],1e-9);
      const avoided=Math.max(sw-pr[2],sd-pr[3]);
      const rp=renderedPlate[k]||null;
      const rendered=rp?[rp[0],rp[1],rp[2]-rp[0],rp[3]-rp[1]]:null;
      const over=rendered
        ?Math.max(pr[0]-rendered[0],pr[1]-rendered[1],
                  (rendered[0]+rendered[2])-(pr[0]+pr[2]),
                  (rendered[1]+rendered[3])-(pr[1]+pr[3]),0)
        :null;
      plateOverhang.push({level:k,index:L.index,
        site_plate:[0,0,sw,sd],room_union_plate:pr,
        rendered_plate:rendered?rendered.map(v=>Math.round(v*1000)/1000):null,
        overhang_m:(over===null)?null:Math.round(over*1000)/1000,
        avoided_site_overhang_m:Math.round(avoided*1000)/1000,
        area_ratio:Math.round(ratio*100)/100,
        convention:PQ_PLATE_POLICY.policy,
        previous_convention:PQ_PLATE_POLICY.previous_policy,
        previous_pinned_by:PQ_PLATE_POLICY.previous_pinned_by,
        change_reason:PQ_PLATE_POLICY.reason,
        extent_source:PQ_PLATE_POLICY.extent_source,
        pinned_by:'PHASE10_PRODUCTION_TRUST',
        change_requires_approval:true});
      if(over!==null&&over>1.0)
        issues.push({code:'ALIGN_ROOF_DETACHED',severity:'WARNING',
          blocking:false,element_id:k,
          message:'the rendered level plate overhangs its own room footprint '
            +'by '+over.toFixed(2)+' m, which the declared '
            +PQ_PLATE_POLICY.policy+' convention forbids'}); });
    const idx=renderedLevels.map(l=>l.index);
    const top=idx.length?Math.max.apply(null,idx):null;
    let roof=null;
    if(top!==null){
      let roofY=null;
      model.traverse(o=>{
        if(!o.isMesh) return;
        const t=_pqTagParts(o);
        if(!t||t.layer!=='FLOOR'||t.floor!=='F'+top) return;
        const wb=_pqWorldBox(o);
        if(wb) roofY=(roofY===null)?wb.max[1]:Math.max(roofY,wb.max[1]); });
      roof=pqRoofAlignment(top-1,fh,roofY);
      (roof.issues||[]).forEach(i=>issues.push(i)); }
    return {objects_checked:checked,
      canonical_hosts_checked:Object.keys(hosts).length,
      unresolved_transforms:unresolved,detached_objects:detached,
      outside_host_objects:outside,containment:hosted,
      roof_alignment:roof,level_alignment:levelAlign,
      plate_overhang:plateOverhang,
      max_position_error_m:Math.round(maxErr*1000)/1000,
      samples:sample,
      axis_convention:PQ_TC.axis,
      transform_contract:PQ_TC.version,
      objects_moved_to_fit:0,writes_to_model:false,
      exposes_canonical_state:false,issues:issues};
  }catch(e){
    return {objects_checked:0,writes_to_model:false,
      issues:[{code:'ALIGN_TRANSFORM_UNRESOLVED',severity:'ERROR',
        blocking:false,message:String(e&&e.message||e).slice(0,160)}]}; } };


/* ===== §15 — بصمة تحويلات الهندسة القانونية (قراءة فقط، بلا كشف إحداثيات)
   يحتاج مِرقاب النشر مقارنة مصفوفات العالم قبل التبديل وبعده. حالة المحرّك
   (scene/model/renderer/camera) محصورة في نطاق الوحدة عمداً، ولا تُرفع إلى
   النطاق العام لإرضاء اختبار. هذا الجسر الضيّق يعيد بصمة مستقرّة وعدداً
   فقط — أداة مقارنة لا تصدير بيانات — فيبقى التغليف سليماً. */
window.ACS.canonicalTransformSnapshot=function(){
  try{
    if(typeof model==='undefined'||!model)
      return {available:false,count:0,digest:null,
        reason:'no canonical model is loaded'};
    scene.updateMatrixWorld(true);
    const rows=[];
    model.traverse(m=>{
      if(!m.isMesh||!m.name||m.name.indexOf('|')<0) return;
      if(!pqBoundsMember(_pqDescribe(m)).included) return;
      rows.push(m.name+':'+m.matrixWorld.elements
        .map(v=>Math.round(v*1e6)/1e6).join(',')); });
    rows.sort();
    const joined=rows.join('|');
    const digest=(typeof sha256Hex==='function')
      ?sha256Hex(joined).slice(0,32)
      :String(joined.length);
    return {available:true,count:rows.length,digest:digest,
      exposes_coordinates:false,writes_to_model:false};
  }catch(e){
    return {available:false,count:0,digest:null,
      reason:String(e&&e.message||e).slice(0,120)}; } };

/* ═══════ استرداد العرض للنماذج المولَّدة الحيّة (render-recovery/1.0.0) ═════
   العطل: نموذج مولّد بمئات العناصر — الواجهة حيّة والعدّادات ممتلئة والمشهد
   أسود. السبب أن setModel كان يؤطّر الكاميرا من Box3().setFromObject(model):
   كل شبكة بلا فحص صلاحية، وnear/far يبقيان على قيمتَي إنشاء الكاميرا
   (0.05 / 6000) بلا إعادة ضبط. نقطة واحدة عند x=99999 ⇒ نصف قطر ٥٠ كم ⇒
   كاميرا على بُعد ١٠٧ كم خلف مستوى قصّ ٦ كم ⇒ إطار أسود.
   هنا المصالحة الوحيدة المخوَّلة بعد تحميل نموذج، وتمرّ بالعقد القانوني نفسه. */
window.__ACS_RR__={last_fit:null,last_verify:null,recovery:null,cycles:0};

/* وصف كائن مع صندوقه العالمي — لازم لفحص الصلاحية، والوصف بلا صندوق أعمى. */
function _pqDescribeBoxed(o){
  const d=_pqDescribe(o);
  try{
    const b=new THREE.Box3().setFromObject(o);
    d.box={min:[b.min.x,b.min.y,b.min.z],max:[b.max.x,b.max.y,b.max.z]};
  }catch(e){ d.box=null; }
  return d; }

/* أوصاف الهندسة القانونية وحدها — قبّة السماء والأرضية والسياق مستبعدة بالعقد. */
function _pqCanonicalDescriptors(){
  const out=[];
  try{
    scene.updateMatrixWorld(true);
    scene.traverse(o=>{ if(o.isMesh) out.push(_pqDescribeBoxed(o)); });
  }catch(e){}
  return out; }

/* حدود محصّنة: تستبعد التالف وحده وتُبلّغ عن الشاذّ بلا حذف هندسة مشروعة. */
function _pqRobustSceneBounds(){
  const r=pqRobustBounds(_pqCanonicalDescriptors());
  return r; }

/* ── المصالحة الوحيدة: موضع وهدف ومستويا قصّ معاً، لا موضعٌ بلا قصّ ───────── */
function acsReconcileCamera(opts){
  opts=opts||{};
  const rb=_pqRobustSceneBounds();
  const rec={contract:PQ_RENDER_RECOVERY_CONTRACT,
    diagnostics:rb.diagnostics||null,issues:(rb.issues||[]).slice(0,24),
    applied:false,camera_in_frustum:false,bounds:rb.bounds||null};
  if(!rb.valid||!rb.bounds){ window.__ACS_RR__.last_fit=rec; return rec; }
  const asp=(camera&&camera.aspect)?camera.aspect:1.6;
  const fov=(camera&&camera.fov)?camera.fov:52;
  const fit=pqCameraFit(rb.bounds,fov,asp,
    (opts.azimuth===undefined)?35:opts.azimuth,
    (opts.elevation===undefined)?22:opts.elevation,0);
  rec.issues=rec.issues.concat((fit.issues||[]).slice(0,12));
  rec.camera_in_frustum=!!fit.camera_in_frustum;
  rec.attempt=fit.attempt;
  rec.distance=fit.distance;
  if(!fit.camera){ window.__ACS_RR__.last_fit=rec; return rec; }
  const c=fit.camera;
  try{
    camera.position.set(c.position[0],c.position[1],c.position[2]);
    camera.near=c.near; camera.far=c.far;
    camera.updateProjectionMatrix();
    if(typeof orbit!=='undefined'&&orbit&&orbit.target){
      /* هدف نموذج سابق لا يبقى أبداً: مركز حدود النموذج الحالي وحده. */
      orbit.target.set(c.target[0],c.target[1],c.target[2]); orbit.update(); }
    rec.applied=true;
  }catch(e){ rec.error=String(e&&e.message||e).slice(0,120); }
  rec.camera={position:c.position,target:c.target,near:c.near,far:c.far,
    fov:c.fov,aspect:c.aspect};
  window.__ACS_RR__.last_fit=rec;
  return rec; }

/* ── §8 فتح آمن للمعالجة اللاحقة: مؤلِّف أسود لا يُبقى أبداً ────────────────── */
function _pqDisableComposer(reason){
  if(!window.__ACS_PQ__||!window.__ACS_PQ__.composer) return false;
  window.__ACS_PQ__.composer=null;
  window.__ACS_RR__.postprocess_fail_open=reason||'BLACK_FRAME';
  try{ renderer.render(scene,camera); }catch(e){}
  return true; }

/* ── §13 جسر قراءة فقط: هل النموذج مرئيّ فعلاً؟ لا يغيّر حالة ولا يرسم ────── */
window.ACS.verifyVisibleModel=function(){
  try{
    const d=(typeof window.ACS.renderDiagnosticsDetail==='function')
      ?window.ACS.renderDiagnosticsDetail():{};
    const rb=_pqRobustSceneBounds();
    const px=(typeof window.ACS.viewportPixels==='function')
      ?window.ACS.viewportPixels():{status:'UNAVAILABLE'};
    const fit=window.__ACS_RR__.last_fit;
    const clipValid=!!(camera&&isFinite(camera.near)&&isFinite(camera.far)
      &&camera.near>0&&camera.far>camera.near);
    const out={
      model_loaded:!!(typeof model!=='undefined'&&model),
      canonical_meshes:(rb.diagnostics||{}).canonical_mesh_count||0,
      included_in_bounds:(rb.diagnostics||{}).included_in_bounds||0,
      excluded_invalid_bounds:(rb.diagnostics||{}).excluded_invalid_bounds||0,
      visible_meshes:d.visible_meshes===undefined?null:d.visible_meshes,
      draw_calls:d.draw_calls===undefined?null:d.draw_calls,
      triangles:d.triangles===undefined?null:d.triangles,
      geometries:d.geometries===undefined?null:d.geometries,
      textures:d.textures===undefined?null:d.textures,
      bounds_valid:!!rb.valid,
      scene_radius:(rb.bounds||{}).radius===undefined?null:(rb.bounds||{}).radius,
      camera_in_frustum:fit?!!fit.camera_in_frustum:null,
      clip_valid:clipValid,
      camera_near:camera?camera.near:null, camera_far:camera?camera.far:null,
      webgl_context_ok:!!d.webgl_context_ok,
      composer_active:!!((window.__ACS_PQ__||{}).composer),
      pixels_visible:(px&&px.status)?px.status!=='BLACK':null,
      pixel_status:(px&&px.status)||'UNAVAILABLE',
      outliers:(rb.diagnostics||{}).outliers||[],
      fallback_used:window.__ACS_RR__.postprocess_fail_open
        ||((window.__ACS_RR__.recovery||{}).applied_step||null),
      recovery_cycles:window.__ACS_RR__.cycles,
      contract:PQ_RENDER_RECOVERY_CONTRACT,
      exposes_coordinates:false, writes_to_model:false};
    window.__ACS_RR__.last_verify=out;
    return out;
  }catch(e){ return {model_loaded:false,error:String(e&&e.message||e).slice(0,120),
    contract:PQ_RENDER_RECOVERY_CONTRACT}; } };

/* ── §14 دورة استرداد واحدة، حتمية، وتُسمّي الطبقة المسؤولة ───────────────── */
function acsRecoverBlackViewport(){
  const v=window.ACS.verifyVisibleModel();
  const plan=pqRecoveryPlan({canonical_meshes:v.canonical_meshes,
    draw_calls:v.draw_calls, viewport_black:(v.pixel_status==='BLACK'),
    composer_active:v.composer_active,
    materials_replaced:!!((window.__ACS_PQ__||{}).saved)});
  const rec={contract:PQ_RENDER_RECOVERY_CONTRACT,plan:plan,
    attempted:[],applied_step:null,recovered:false,
    issues:(plan.issues||[]).slice(0,8)};
  if(!plan.needed||window.__ACS_RR__.cycles>=plan.max_cycles){
    window.__ACS_RR__.recovery=rec; return rec; }
  window.__ACS_RR__.cycles++;
  for(let i=0;i<plan.steps.length;i++){
    const step=plan.steps[i];
    rec.attempted.push(step);
    try{
      if(step==='DISABLE_COMPOSER') _pqDisableComposer('BLACK_FRAME');
      else if(step==='RESTORE_ENGINEERING_MATERIALS'){
        if(typeof window.ACS.pbrRestore==='function') window.ACS.pbrRestore(); }
      else if(step==='REFIT_CAMERA') acsReconcileCamera();
      else if(step==='RENDER_BASE') renderer.render(scene,camera);
      renderer.render(scene,camera);
    }catch(e){ rec.error=String(e&&e.message||e).slice(0,120); }
    const px=(typeof window.ACS.viewportPixels==='function')
      ?window.ACS.viewportPixels():{status:'UNAVAILABLE'};
    if(px&&px.status&&px.status!=='BLACK'){
      rec.applied_step=step; rec.recovered=true;
      rec.issues.push(pqIssue('RENDER_RECOVERED','INFO',null,
        'the viewport recovered after '+step+' — that layer is responsible'));
      break; } }
  if(!rec.recovered) rec.issues.push(pqIssue('RENDER_BLACK_VIEWPORT','WARNING',
    null,'one recovery cycle did not restore visible pixels'));
  window.__ACS_RR__.recovery=rec;
  return rec; }

/* تقرير قراءة فقط عن آخر مصالحة واسترداد — للمِرقاب وللكونسول. */
window.ACS.renderRecoveryReport=function(){
  return {contract:PQ_RENDER_RECOVERY_CONTRACT,
    last_fit:window.__ACS_RR__.last_fit,
    last_verify:window.__ACS_RR__.last_verify,
    recovery:window.__ACS_RR__.recovery,
    cycles:window.__ACS_RR__.cycles,
    postprocess_fail_open:window.__ACS_RR__.postprocess_fail_open||null}; };

/* ── §11 ضغط موارد WebGL: قياس وتحذير، بلا أي مساس بالصحّة ───────────────── */
window.ACS.renderResourcePressure=function(){
  try{
    const info=renderer.info||{render:{},memory:{}};
    const calls=(info.render||{}).calls||0, tris=(info.render||{}).triangles||0;
    const geo=(info.memory||{}).geometries||0, tex=(info.memory||{}).textures||0;
    const flags=[];
    if(calls>PQ_RR.draw_call_warn) flags.push('DRAW_CALLS');
    if(geo>PQ_RR.geometry_warn) flags.push('GEOMETRIES');
    if(tris>PQ_RR.triangle_warn) flags.push('TRIANGLES');
    return {draw_calls:calls,triangles:tris,geometries:geo,textures:tex,
      thresholds:{draw_calls:PQ_RR.draw_call_warn,
        geometries:PQ_RR.geometry_warn,triangles:PQ_RR.triangle_warn},
      pressure:flags,
      issues:flags.length?[pqIssue('RENDER_RESOURCE_PRESSURE','INFO',null,
        'resource pressure: '+flags.join(', ')+' — correctness unaffected')]:[]};
  }catch(e){ return {draw_calls:null,pressure:[],
    error:String(e&&e.message||e).slice(0,80)}; } };
