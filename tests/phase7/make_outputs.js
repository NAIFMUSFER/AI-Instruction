/* ينتج مخرجات العرض الحقيقية من نفس المراجعة ونفس بصمة النموذج.
   المخرجات دليل، لا ادّعاء: كل ملفّ مشتقّ من الهندسة المصرَّفة. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const OUT=_np.join(HERE,'outputs');
const LIB=require(_np.join(HERE,'lib_render_fixtures.js'));
const ALL=LIB.all();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
if(!fs.existsSync(OUT)) fs.mkdirSync(OUT,{recursive:true});

const manifest=[];
const write=(name,text,meta)=>{
  fs.writeFileSync(_np.join(OUT,name),text,'utf8');
  manifest.push(Object.assign({file:name,bytes:Buffer.byteLength(text)},meta));
  console.log('  ·',name,Buffer.byteLength(text),'bytes'); };
const writeBin=(name,bytes,meta)=>{
  fs.writeFileSync(_np.join(OUT,name),Buffer.from(bytes));
  manifest.push(Object.assign({file:name,bytes:bytes.length},meta));
  console.log('  ·',name,bytes.length,'bytes'); };

['villa_glazed','hotel_glazed','clinic_glazed','warehouse_glazed'].forEach(function(key){
  const model=C(ALL[key]);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const scene=compileVisualScene(C(model),'bld_0',null,0,{mode:'PRESENTATION'});
  const arch=compileArchitecture(C(model),'bld_0',null,0);
  const h0=project.model_hash;
  const short=key.replace('_glazed','');
  console.log('\n'+key+'  revision '+project.current_revision);

  (model.levels||[]).forEach(lv=>{
    const d=rdPlanDrawing(scene,arch,lv.index,'CLEAN');
    if(!d.valid) return;
    write(short+'_plan_level'+lv.index+'.svg',rdPlanSvg(d.drawing),
      {kind:'FLOOR_PLAN',model:key,level:lv.index,
       revision:project.current_revision,model_hash:h0,
       drawing_id:d.drawing.drawing_id,
       walls:d.drawing.walls.length,doors:d.drawing.doors.length,
       windows:d.drawing.windows.length}); });

  ['NORTH','SOUTH','EAST','WEST'].forEach(f=>{
    const d=rdElevationDrawing(scene,f);
    if(!d.valid) return;
    write(short+'_elevation_'+f.toLowerCase()+'.svg',rdElevationSvg(d.drawing),
      {kind:'ELEVATION',model:key,face:f,revision:project.current_revision,
       model_hash:h0,drawing_id:d.drawing.drawing_id,
       openings:d.drawing.opening_count,invented:d.drawing.invented_features}); });

  ['x','z'].forEach(ax=>{
    const d=rdSectionDrawing(scene,ax);
    if(!d.valid) return;
    write(short+'_section_'+ax+'.svg',rdSectionSvg(d.drawing),
      {kind:'SECTION',model:key,axis:ax,revision:project.current_revision,
       model_hash:h0,drawing_id:d.drawing.drawing_id,
       cut_elements:d.drawing.cut_count}); });

  const cam=rdCameraFor(scene,'FRONT_CORNER').camera;
  const bufs=rdControlBuffers(scene,cam,320,200,null,h0).buffers;
  ['DEPTH','EDGE','SEMANTIC_MASK','OBJECT_ID'].forEach(k=>{
    const png=rdBufferPng(bufs,k);
    if(png) writeBin(short+'_buffer_'+k.toLowerCase()+'.png',png,
      {kind:'CONTROL_BUFFER',buffer:k,model:key,camera_id:cam.camera_id,
       revision:project.current_revision,model_hash:h0,
       width:bufs.width,height:bufs.height}); });

  if(project.model_hash!==h0)
    throw new Error('producing outputs changed the model: '+key);
});

fs.writeFileSync(_np.join(OUT,'MANIFEST.json'),
  JSON.stringify({generated_from:'canonical engineering model',
    created_at:AT,note:'every file is derived from the compiled model and is pinned to '+
      'the revision and model hash named in its entry. No file certifies anything.',
    files:manifest},null,1),'utf8');
console.log('\nOUTPUTS: '+manifest.length+' files written to tests/phase7/outputs');
const hashes=Array.from(new Set(manifest.map(m=>m.model_hash+'|'+m.model)));
console.log('one model hash per model: '+(hashes.length===4?'yes':'NO'));
