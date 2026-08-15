  /* ---- عرض بصري وتقديم: تصوير يحفظ الهندسة. لا تعديل هندسي إطلاقاً ---- */
  let _visCache=null, _visKey=null;
  const _visOf=(opts)=>{ if(!lastBuilding) return null;
    opts=opts||{};
    const key=JSON.stringify([opts,lastBuilding]);
    if(_visKey===key) return _visCache;
    _visCache=compileVisualScene(lastBuilding,opts.building_id||'bld_0',
      opts.position||null,opts.rotation_deg||0,opts);
    _visKey=key; return _visCache; };
  window.ACS.visualScene=(opts)=>_visOf(opts);
  window.ACS.visualModes=()=>VIS_MODES.slice();
  window.ACS.visualThemes=()=>VIS_THEMES.slice();
  window.ACS.visualMaterials=()=>Object.keys(VIS_MATERIALS).sort()
    .map(k=>visMaterial(k));
  window.ACS.visualSummary=(opts)=>{ const s=_visOf(opts); return s?s.summary:null; };
  window.ACS.visualObjects=(layer,opts)=>{ const s=_visOf(opts);
    return s?(layer?visObjectsByLayer(s,String(layer).toUpperCase()):s.objects.slice()):[]; };
  window.ACS.visualObject=(id,opts)=>{ const s=_visOf(opts);
    return s?visObjectById(s,id):null; };
  window.ACS.visualValidate=(opts)=>{ const s=_visOf(opts);
    return s?visValidateScene(s):[]; };
  window.ACS.visualRuleInputs=(opts)=>{ const s=_visOf(opts);
    return s?visRuleInputs(s):{}; };
  window.ACS.visualLayerVisible=(layer,on,opts)=>{ const s=_visOf(opts);
    if(!s) return [false,'NO_MODEL',null];
    const r=visSetLayerVisible(s,layer,on);
    if(r[0]){ const key=String(layer).toUpperCase();
      const reg=registry&&registry[key==='ARCHITECTURE'?'WALL':key];
      Object.keys(registry||{}).forEach(k=>{ /* حالة عرض فقط */ }); }
    return r; };
  /* المساقط والقطاعات والواجهات — كلّها مشتقّة من الهندسة نفسها */
  window.ACS.floorPlan2D=(levelIndex,style,bid)=>lastBuilding?
    visFloorPlan(compileArchitecture(lastBuilding,bid||'bld_0',null,0),
      (levelIndex===undefined||levelIndex===null)?0:levelIndex,style||null,bid||'bld_0'):null;
  window.ACS.sectionView=(axis,position,bid)=>lastBuilding?
    visSection(compileArchitecture(lastBuilding,bid||'bld_0',null,0),axis||'x',
      (position===undefined)?null:position,bid||'bld_0'):null;
  window.ACS.elevationView=(face,bid)=>lastBuilding?
    visElevation(compileArchitecture(lastBuilding,bid||'bld_0',null,0),face||'NORTH',
      bid||'bld_0'):null;
  /* الكاميرات والأداء */
  window.ACS.cameraPresets=()=>VIS_CAMERA_PRESETS.slice();
  window.ACS.frameCamera=(preset,roomId,opts)=>{ const s=_visOf(opts);
    return s?visFrameCamera(s,preset,(roomId===undefined)?null:roomId):null; };
  window.ACS.visualInstancing=(opts)=>{ const s=_visOf(opts);
    return s?visInstancingPlan(s):null; };
  window.ACS.visualLod=(budget,opts)=>{ const s=_visOf(opts);
    return s?visLodPlan(s,(budget===undefined)?null:budget):null; };
  /* اللقطة وبياناتها — تنفيذ البكسل في المتصفّح، والوصف حتميّ ومتحقَّق منه */
  window.ACS.snapshotRequest=(o,opts)=>{ const s=_visOf(opts);
    return s?visSnapshotRequest(s,o||{}):null; };
  window.ACS.renderMetadata=(req,kind,at,opts)=>{ const s=_visOf(opts);
    return s?visRenderMetadata(s,req||null,kind||'DETERMINISTIC_RENDER',
      (at===undefined)?null:at,null):null; };
  window.ACS.renderCurrency=(meta,bid)=>lastBuilding?
    visCheckRenderCurrency(meta,lastBuilding,bid||'bld_0'):null;
  window.ACS.snapshot=(o,opts)=>{
    const s=_visOf(opts); if(!s) return null;
    const req=visSnapshotRequest(s,o||{});
    const meta=visRenderMetadata(s,req,'DETERMINISTIC_RENDER',null,null);
    let data=null;
    try{
      const prev={w:renderer.domElement.width,h:renderer.domElement.height,
        ratio:renderer.getPixelRatio()};
      renderer.setPixelRatio(1);
      renderer.setSize(req.width,req.height,false);
      if(camera.isPerspectiveCamera){ camera.aspect=req.width/req.height;
        camera.updateProjectionMatrix(); }
      renderer.render(scene,camera);
      data=renderer.domElement.toDataURL(req.format==='JPEG'?'image/jpeg':'image/png',
        req.quality);
      renderer.setPixelRatio(prev.ratio);
      renderer.setSize(innerWidth,innerHeight,false);
      if(camera.isPerspectiveCamera){ camera.aspect=innerWidth/innerHeight;
        camera.updateProjectionMatrix(); }
    }catch(e){ data=null; }
    return {request:req,metadata:meta,data_url:data,
      rendered:!!data,
      note:data?'a deterministic image of the compiled scene at the stated model hash'
                :'NOT VERIFIED — a real WebGL context is required to produce the pixels'}; };
  /* الذكاء الاصطناعي: واجهة فقط. لا مولّد ولا شبكة ولا أي مسار كتابة في النموذج */
  window.ACS.controlBuffers=(kinds,opts)=>{ const s=_visOf(opts);
    return s?visControlBuffers(s,kinds||null):null; };
  window.ACS.geometrySignature=(opts)=>{ const s=_visOf(opts);
    return s?visGeometrySignature(s,lastBuilding?
      compileArchitecture(lastBuilding,'bld_0',null,0):null):null; };
  window.ACS.aiEnhancementRequest=(prompt,buffers,strength,opts)=>{ const s=_visOf(opts);
    return s?visAiEnhancementRequest(s,prompt||null,buffers||null,
      (strength===undefined)?0.35:strength,
      lastBuilding?compileArchitecture(lastBuilding,'bld_0',null,0):null):null; };
  window.ACS.checkVisualConsistency=(req,reported,tol)=>
    visCheckConsistency(req,reported,(tol===undefined)?0.5:tol);
  /* التصدير: الهندسي يبقى بدلالته، والتقديمي منفصل وصريح */
  window.ACS.exportVisualScene=(presentationGlb,opts)=>{ const s=_visOf(opts);
    return s?visExportScene(s,!!presentationGlb):null; };
  window.ACS.presentationBlock=(opts)=>{ const s=_visOf(opts);
    return s?visPresentationBlock(s):null; };
  window.ACS.applyVisualMode=(mode,opts)=>applyVisualMode(mode,opts||{});
  window.ACS.clearVisualMode=()=>clearVisualMode();
  window.ACS.visualState=()=>VIS_STATE;
  window.ACS.visualAssets=()=>visAssetLibrary();
  window.ACS.validateVisualAsset=(a)=>visValidateAsset(a);
