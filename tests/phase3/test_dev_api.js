/* يتحقّق من ربط واجهة العرض البصري بتشغيل الكتلة المحقونة نفسها في index.html */
const fs=require('fs'), path=require('path');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const SC=JSON.parse(fs.readFileSync(path.join(HERE,'fixtures','visual_scenarios.json'),'utf8'));
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const lastBuilding=JSON.parse(JSON.stringify(SC.models.villa_full));
const registry={};
const src=fs.readFileSync(path.join(ROOT,'public','index.html'),'utf8');
const a=src.indexOf('/* ---- عرض بصري وتقديم');
const b=src.indexOf('/* ---- تنسيق بين التخصّصات', a);
const block=src.slice(a,b);
chk('the visual dev API block exists in index.html', block.length>2500, block.length);
/* مضيف محايد يعمل في Node وفي المتصفّح معاً: لا اعتماد على global ولا على
   كائن window الحقيقي للصفحة */
const HOST={ACS:{}};
/* لا سياق WebGL هنا: نمرّر بدائل تُظهر بصدق أنّ البكسل غير متحقَّق منه */
const renderer={domElement:{width:0,height:0,toDataURL:()=>{throw new Error('no webgl');}},
  getPixelRatio:()=>1,setPixelRatio:()=>{},setSize:()=>{},render:()=>{}};
const camera={isPerspectiveCamera:true,aspect:1,updateProjectionMatrix:()=>{}};
const scene={}; const innerWidth=1280, innerHeight=720;
eval('(function(){const window=HOST;'+block+'})()');
const ACS=HOST.ACS;
chk('ACS.visualScene() returns a derived scene', !!(ACS.visualScene()||{}).schema);
chk('ACS.visualModes() lists all nine modes', ACS.visualModes().length===9);
chk('ACS.visualThemes() lists the themes', ACS.visualThemes().length===7);
chk('ACS.visualMaterials() returns VISUAL_MATERIAL entries only',
    ACS.visualMaterials().every(m=>m.material_class==='VISUAL_MATERIAL'));
chk('ACS.visualSummary() declares no engineering mutation',
    ACS.visualSummary().engineering_geometry_modified===false);
chk('ACS.visualObjects("ARCHITECTURE") filters by layer',
    ACS.visualObjects('ARCHITECTURE').every(o=>o.layer==='ARCHITECTURE'));
chk('ACS.visualObject(id) resolves an object',
    ACS.visualObject(ACS.visualObjects()[0].id).id===ACS.visualObjects()[0].id);
chk('ACS.visualValidate() reports no integrity issue', ACS.visualValidate().length===0);
chk('ACS.floorPlan2D() derives a plan from the model',
    ACS.floorPlan2D(0,'TECHNICAL').kind==='FLOOR_PLAN_2D');
chk('ACS.sectionView() derives a section', ACS.sectionView('x',null).kind==='SECTION');
chk('ACS.elevationView() derives an elevation',
    ACS.elevationView('NORTH').kind==='ELEVATION');
chk('ACS.cameraPresets() lists the presets', ACS.cameraPresets().length>=9);
chk('ACS.frameCamera() reframes without regenerating geometry', (function(){
  const before=JSON.stringify(ACS.visualObjects());
  ACS.cameraPresets().forEach(p=>ACS.frameCamera(p,null));
  return JSON.stringify(ACS.visualObjects())===before; })());
chk('ACS.visualInstancing() never merges a modelled element',
    ACS.visualInstancing({include_decoration:true}).modelled_objects_merged===0);
chk('ACS.visualLod() never drops a modelled element',
    ACS.visualLod(5).dropped_modelled===0);
chk('ACS.snapshotRequest() clamps an absurd resolution',
    ACS.snapshotRequest({width:99999,height:99999}).issues
      .indexOf('SNAPSHOT_EXCEEDS_MAX_PIXELS')>=0);
chk('ACS.renderMetadata() carries the model hash',
    !!ACS.renderMetadata(null,'DETERMINISTIC_RENDER',null).model_hash);
chk('ACS.renderCurrency() reports CURRENT for the live model',
    ACS.renderCurrency(ACS.renderMetadata(null,null,null)).status==='CURRENT');
chk('ACS.snapshot() reports honestly when no WebGL context exists', (function(){
  const s=ACS.snapshot({width:800,height:600});
  return s.rendered===false&&/NOT VERIFIED/.test(s.note)&&!!s.metadata.model_hash; })());
chk('ACS.controlBuffers() returns deterministic passes',
    ACS.controlBuffers(null).buffers.every(b2=>b2.deterministic===true));
chk('ACS.geometrySignature() carries the protected features',
    ['door_count','window_count','floor_count','footprint']
      .every(k=>ACS.geometrySignature()[k]!==undefined));
chk('ACS.aiEnhancementRequest() cannot write to the model and ships no generator',
    (function(){ const r=ACS.aiEnhancementRequest('warm light');
      return r.writes_to_model===false&&r.generator_shipped===false
        &&r.network_call===false; })());
chk('ACS.checkVisualConsistency() flags drift without touching the model',
    (function(){ const r=ACS.aiEnhancementRequest('x');
      const d=ACS.checkVisualConsistency(r,{door_count:999});
      return d.drift===true&&d.model_modified===false; })());
chk('ACS.exportVisualScene(false) excludes visual-only objects',
    ACS.exportVisualScene(false,{include_decoration:true}).objects
      .every(o=>o.visual_only===false));
chk('ACS.exportVisualScene(true) is explicitly a presentation export',
    ACS.exportVisualScene(true).kind==='PRESENTATION_GLB');
chk('ACS.presentationBlock() is additive and outside the revision hash',
    ACS.presentationBlock().presentation.affects_revision_hash===false);
chk('ACS.visualAssets() are all licensed',
    ACS.visualAssets().every(x=>x.license&&x.license!=='UNKNOWN'));
chk('ACS.validateVisualAsset() refuses metadata carrying code',
    ACS.validateVisualAsset({id:'x',type:'y',asset_class:'VISUAL_ONLY',license:'CC0',
      dimensions_m:{w:1,d:1,h:1},source:'s',eval:'x'})
      .some(i=>/MUST_NOT_CARRY_CODE/.test(i)));
chk('ACS.visualLayerVisible refuses to hide a discipline in the engineering view',
    ACS.visualLayerVisible('MEP',false,{mode:'ENGINEERING'})[1]
      ==='ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE');
chk('the visual API exposes no geometry-editing entry point',
    !Object.keys(ACS).some(k=>/^visual.*(move|edit|set(Wall|Door|Room)|generate)/i.test(k)));
console.log('\nVISUAL DEV API: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
