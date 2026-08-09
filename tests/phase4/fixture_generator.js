/* يولّد تجهيزات المرحلة 4 من تجهيزات المراحل السابقة الموجودة في المستودع.
   لا تجهيز جديد يُلفَّق ولا ملفّ مصدر يعيش في /tmp. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXDIR=_np.join(HERE,'fixtures');
const P3=_np.resolve(ROOT,'tests','phase3','fixtures');
const BASE=JSON.parse(fs.readFileSync(_np.join(P3,'base_fixtures.json'),'utf8'));
const VIS=JSON.parse(fs.readFileSync(_np.join(P3,'visual_scenarios.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const M={};
/* الأهداف الخمسة المطلوبة كما هي، بلا أي تحوير */
['villa','hotel','clinic','warehouse','office'].forEach(k=>{ M[k]=C(BASE[k]); });
/* نماذج غنيّة بالتخصّصات من المرحلة 3 — إنشائي و MEP وحريق حاضرة */
M.villa_full=C(VIS.models.villa_full);
M.clash_full=C(VIS.models.clash_full);
M.fls_full=C(VIS.models.fls_full);
M.mixed_use=C(VIS.models.mixed_use);
M.villa_windows=C(VIS.models.villa_windows);
M.degenerate=C(VIS.models.degenerate);
M.no_site=C(VIS.models.no_site);

/* استعلامات: كل نموذج في وضع هندسي، مع دوران وإزاحة لإثبات التعامل مع
   الهندسة المدارة، ومع ديكور صريح لإثبات فصل الأجسام البصرية. */
const queries=[];
Object.keys(M).sort().forEach(k=>queries.push({n:k,m:k,bid:'bld_0',pos:null,rot:0,
  mode:'ENGINEERING',deco:false}));
queries.push({n:'villa@rot45',m:'villa',bid:'bld_0',pos:{x:-6,z:4},rot:45,
  mode:'ENGINEERING',deco:false});
queries.push({n:'villa@rot90',m:'villa',bid:'bld_3',pos:{x:12,z:-4},rot:90,
  mode:'ENGINEERING',deco:false});
queries.push({n:'villa_full|deco',m:'villa_full',bid:'bld_0',pos:null,rot:0,
  mode:'ENGINEERING',deco:true});
queries.push({n:'villa_full|deco_blocking',m:'villa_full',bid:'bld_0',pos:null,rot:0,
  mode:'ENGINEERING',deco:true,cfg:{decoration_collision:'BLOCKING'}});
queries.push({n:'hotel|presentation',m:'hotel',bid:'bld_0',pos:null,rot:0,
  mode:'PRESENTATION',deco:false});

/* مشاهد باطلة وخصومية: تُغذّى للتطبيقَين نصّاً بنصّ */
const adversarial=[
 ['null_scene', null],
 ['string_scene', 'not a scene'],
 ['empty_object', {}],
 ['objects_not_array', {scene_id:'s', objects:'nope'}],
 ['missing_scene_id', {objects:[]}],
 ['object_without_id', {scene_id:'s',objects:[{geometry:{cx:0,cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:0}}],
   spaces_index:[]}],
 ['object_without_geometry', {scene_id:'s',objects:[{id:'a'}],spaces_index:[]}],
 ['nan_geometry', {scene_id:'s',objects:[{id:'a',kind:'WALL',layer:'ARCHITECTURE',
   source_element_id:'w',geometry:{cx:'NaN_MARKER',cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:0}}],
   spaces_index:[]}],
 ['infinite_geometry', {scene_id:'s',objects:[{id:'a',kind:'WALL',layer:'ARCHITECTURE',
   source_element_id:'w',geometry:{cx:'INF_MARKER',cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:0}}],
   spaces_index:[]}],
 ['nan_rotation', {scene_id:'s',objects:[{id:'a',kind:'WALL',layer:'ARCHITECTURE',
   source_element_id:'w',geometry:{cx:0,cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:'NaN_MARKER'}}],
   spaces_index:[]}],
 ['duplicate_object_id', {scene_id:'s',objects:[
   {id:'a',kind:'WALL',layer:'ARCHITECTURE',source_element_id:'w',
    geometry:{cx:0,cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:0}},
   {id:'a',kind:'WALL',layer:'ARCHITECTURE',source_element_id:'w',
    geometry:{cx:1,cy:0,cz:0,ex:1,ey:1,ez:1,rot_y:0}}],spaces_index:[]}],
 ['bad_space_rect', {scene_id:'s',objects:[],spaces_index:[
   {id:'sp',space_id:'sp',name:'x',rect:[0,0,-1,2],level_index:0,area_m2:1,_elev:0}]}],
 ['space_rect_wrong_length', {scene_id:'s',objects:[],spaces_index:[
   {id:'sp',space_id:'sp',name:'x',rect:[0,0,1],level_index:0,area_m2:1,_elev:0}]}],
 ['space_without_elevation', {scene_id:'s',objects:[],spaces_index:[
   {id:'sp',space_id:'sp',name:'x',rect:[0,0,2,2],level_index:0,area_m2:4,_elev:'NaN_MARKER'}]}],
 ['door_missing_host', {scene_id:'s',objects:[
   {id:'d1',kind:'DOOR',layer:'ARCHITECTURE',source_element_id:'door1',
    host_wall_id:'ghost_wall',level_index:0,
    geometry:{cx:0,cy:1,cz:0,ex:0.12,ey:2.1,ez:0.9,rot_y:0}}],
   spaces_index:[]}],
 ['write_flag_in_config', {scene_id:'s',objects:[],spaces_index:[]}]];

fs.writeFileSync(_np.join(FIXDIR,'runtime_scenarios.json'),
  JSON.stringify({models:M,queries:queries,adversarial:adversarial}));
console.log('runtime fixtures:',Object.keys(M).length,'queries:',queries.length,
  'adversarial:',adversarial.length);
