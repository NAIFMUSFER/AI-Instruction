/* يولّد تجهيزات المرحلة 5 من تجهيزات المستودع نفسها — لا مصدر في /tmp.
   المخرَج: نماذج قانونية، سيناريوهات أوامر، وحالات خصومية تُغذّى للتطبيقَين نصّاً بنصّ. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const P3=path.join(ROOT,'tests','phase3','fixtures');
const BASE=JSON.parse(fs.readFileSync(path.join(P3,'base_fixtures.json'),'utf8'));
const MEPF=JSON.parse(fs.readFileSync(path.join(P3,'mep_fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));

const models={};
['villa','hotel','clinic','warehouse','office'].forEach(k=>{ models[k]=C(BASE[k]); });
models.villa_mep=C(MEPF.models.villa_mep);
models.clash_mep=C(MEPF.models.clash_mep);
/* نموذج مفرد المستوى لاختبار حذف المستوى الأخير */
models.single_level={meta:{type:'office',name:'single'},wall_h:3,wall_t:0.2,
  floor_height:3.2,site:{w:20,d:20},levels:[{index:0,name:'ground',template:'g'}],
  floors:{g:{rooms:[
    {id:'a',rect:[0,0,6,5],doors:[{edge:'E',offset:2.5,width:0.9}]},
    {id:'b',rect:[6,0,6,5]}]}}};
/* نموذج بنوافذ وأجسام لاختبار أوامر النوافذ والأجسام */
models.windowed=(function(){ const m=C(BASE.villa);
  const g=m.floors.g.rooms.filter(r=>r.id==='majlis')[0];
  g.windows=[{edge:'N',offset:2,width:1.2,height:1.4,sill:0.9},
             {edge:'S',offset:3,width:1.0,height:1.4,sill:0.9}];
  g.objects=[{kind:'desk',x:1,z:1,count:1}];
  return m; })();
/* نموذج يحمل المعرّف نفسه على قالبين لإثبات الغموض */
models.dup_ids=(function(){ const m=C(models_seed_single()); return m; })();
function models_seed_single(){
  return {meta:{type:'office',name:'dup'},wall_h:3,wall_t:0.2,floor_height:3.2,
    site:{w:20,d:20},
    levels:[{index:0,name:'ground',template:'g'},{index:1,name:'first',template:'f'}],
    floors:{g:{rooms:[{id:'corridor',rect:[0,0,6,5]},{id:'a',rect:[6,0,6,5]}]},
            f:{rooms:[{id:'corridor',rect:[0,0,6,5]},{id:'b',rect:[6,0,6,5]}]}}}; }
/* نموذج يحمل نقاطاً دلالية لاختبار أوامر النقاط (كاشف دخان، كاميرا، مخرج) */
models.pointed=(function(){ const m=C(BASE.villa);
  const g=m.floors.g.rooms.filter(r=>r.id==='majlis')[0];
  g.points=[{type:'smoke',x:1,z:1,height:2.9},
            {type:'camera',x:2,z:1,height:2.7}];
  return m; })();
/* نموذج بقالب فارغ إضافي لاختبار ADD_LEVEL */
models.spare_template=(function(){ const m=C(models.single_level);
  m.floors.upper={rooms:[{id:'u1',rect:[0,0,6,5]}]}; return m; })();

/* سيناريوهات أوامر: (اسم، نموذج، أمر) — تُشغَّل حرفياً في اللغتين */
const scenarios=[
 ['rename','villa',{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Grand Majlis'}}],
 ['resize','villa',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}}],
 ['resize_shrink','villa',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:3,d:5}}],
 ['resize_tiny','villa',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:0.01,d:5}}],
 ['add_space','villa',{type:'ADD_SPACE',parameters:{template:'g',rect:[20,12,4,4],id:'store'}}],
 ['add_space_auto_id','villa',{type:'ADD_SPACE',parameters:{template:'g',rect:[20,12,4,4]}}],
 ['add_space_overlap','villa',{type:'ADD_SPACE',parameters:{template:'g',rect:[0,0,4,4],id:'ov'}}],
 ['delete_space','villa',{type:'DELETE_SPACE',target_id:'g.guest',parameters:{}}],
 ['move_wall_free','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.5}}],
 ['move_wall_hosted_no_strategy','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',
   parameters:{delta_m:0.5}}],
 ['move_wall_hosted_relative','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',
   parameters:{delta_m:0.5,hosted_strategy:'KEEP_RELATIVE_POSITION'}}],
 ['move_wall_hosted_world','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',
   parameters:{delta_m:0.5,hosted_strategy:'KEEP_WORLD_POSITION'}}],
 ['move_wall_hosted_cancel','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',
   parameters:{delta_m:0.5,hosted_strategy:'CANCEL_IF_HOSTED'}}],
 ['move_wall_collapse','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:99}}],
 ['move_wall_unknown','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_999',
   parameters:{delta_m:0.5}}],
 ['add_wall','villa',{type:'ADD_WALL',target_id:'bld_0.flr_0',parameters:{}}],
 ['delete_wall','villa',{type:'DELETE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{}}],
 ['move_door_ok','villa',{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
   parameters:{offset:3.0}}],
 ['move_door_far','villa',{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
   parameters:{offset:99}}],
 ['move_door_edge_flip','villa',{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
   parameters:{offset:2.0,edge:'N'}}],
 ['add_door','villa',{type:'ADD_DOOR',target_id:'g.majlis',
   parameters:{edge:'N',offset:3,width:1.0,height:2.1}}],
 ['add_door_out','villa',{type:'ADD_DOOR',target_id:'g.majlis',
   parameters:{edge:'N',offset:5.9,width:1.0}}],
 ['delete_door','villa',{type:'DELETE_DOOR',target_id:'bld_0.g.majlis.door_0',parameters:{}}],
 ['door_props','villa',{type:'CHANGE_DOOR_PROPERTIES',target_id:'bld_0.g.majlis.door_0',
   parameters:{width:1.1,height:2.2}}],
 ['door_props_too_wide','villa',{type:'CHANGE_DOOR_PROPERTIES',
   target_id:'bld_0.g.majlis.door_0',parameters:{width:20}}],
 ['add_window','villa',{type:'ADD_WINDOW',target_id:'g.majlis',
   parameters:{edge:'N',offset:2,width:1.2,height:1.4,sill:0.9}}],
 ['add_object','villa',{type:'ADD_OBJECT',target_id:'g.majlis',
   parameters:{kind:'desk',x:2,z:2,count:1}}],
 ['move_stair','villa',{type:'MOVE_STAIR',target_id:'g.corridor.obj_0',
   parameters:{x:1.5,z:8.5}}],
 ['move_stair_as_object','villa',{type:'MOVE_OBJECT',target_id:'g.corridor.obj_0',
   parameters:{x:1.5,z:8.5}}],
 ['delete_stair','villa',{type:'DELETE_STAIR',target_id:'g.corridor.obj_0',parameters:{}}],
 ['add_stair','villa',{type:'ADD_STAIR',target_id:'g.majlis',parameters:{x:1,z:1}}],
 ['level_height','villa',{type:'CHANGE_LEVEL_HEIGHT',parameters:{height_m:3.6}}],
 ['level_height_absurd','villa',{type:'CHANGE_LEVEL_HEIGHT',parameters:{height_m:900}}],
 ['add_level','spare_template',{type:'ADD_LEVEL',parameters:{template:'upper',name:'first'}}],
 ['add_level_unknown','villa',{type:'ADD_LEVEL',parameters:{template:'nope'}}],
 ['delete_level_last','single_level',{type:'DELETE_LEVEL',target_id:'g',parameters:{}}],
 ['delete_level_occupied','villa',{type:'DELETE_LEVEL',target_id:'f',parameters:{}}],
 ['site','villa',{type:'CHANGE_SITE_DIMENSIONS',parameters:{w:40,d:30}}],
 ['building_pos','villa',{type:'CHANGE_BUILDING_POSITION',parameters:{x:12,z:-4}}],
 ['building_rot','villa',{type:'CHANGE_BUILDING_ROTATION',parameters:{rotation_deg:405}}],
 ['promote','villa',{type:'PROMOTE_VISUAL_OBJECT',target_id:'vis:tree_1',
   parameters:{space_id:'g.majlis',semantic_kind:'planter',x:1,z:1,
     provenance:'user promoted a visual entourage object'}}],
 ['promote_no_kind','villa',{type:'PROMOTE_VISUAL_OBJECT',target_id:'vis:tree_1',
   parameters:{space_id:'g.majlis',x:1,z:1,provenance:'x'}}],
 ['lock','villa',{type:'LOCK_ELEMENT',target_id:'g.majlis',parameters:{reason:'IMPORTED'}}],
 ['unlock_unlocked','villa',{type:'UNLOCK_ELEMENT',target_id:'g.majlis',parameters:{}}],
 ['constraint_ok','villa',{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
   parameters:{offset:3.0},constraints:{must_not_change:['SPACE_RECT']}}],
 ['constraint_violated','villa',{type:'RESIZE_SPACE',target_id:'g.majlis',
   parameters:{w:6,d:4},constraints:{must_not_change:['SPACE_RECT']}}],
 ['constraint_max_delta','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.5},constraints:{max_delta_m:0.1}}],
 ['constraint_scope','villa',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'X'},constraints:{allowed_scope:['MEP']}}],
 ['snap_grid','villa',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.5321},snap:'GRID',grid_m:0.25}],
 ['not_implemented','villa',{type:'MOVE_COLUMN',target_id:'x',parameters:{}}],
 ['forbidden_type','villa',{type:'RAW_JSON_MUTATION',target_id:'x',parameters:{}}],
 ['ambiguous','dup_ids',{type:'RENAME_SPACE',target_id:'corridor',parameters:{name:'X'}}],
 ['move_window','windowed',{type:'MOVE_WINDOW',target_id:'bld_0.g.majlis.window_0',
   parameters:{offset:3.0}}],
 ['move_window_out','windowed',{type:'MOVE_WINDOW',target_id:'bld_0.g.majlis.window_0',
   parameters:{offset:99}}],
 ['delete_window','windowed',{type:'DELETE_WINDOW',target_id:'bld_0.g.majlis.window_1',
   parameters:{}}],
 ['window_props','windowed',{type:'CHANGE_WINDOW_PROPERTIES',
   target_id:'bld_0.g.majlis.window_0',parameters:{width:1.4,height:1.6,sill:1.0}}],
 ['delete_object','windowed',{type:'DELETE_OBJECT',target_id:'g.majlis.obj_0',
   parameters:{}}],
 ['move_object','windowed',{type:'MOVE_OBJECT',target_id:'g.majlis.obj_0',
   parameters:{x:2.5,z:2.5}}],
 ['add_point','villa',{type:'ADD_POINT',target_id:'g.majlis',
   parameters:{point_type:'smoke',x:2,z:2,height:2.9}}],
 ['add_point_outside','villa',{type:'ADD_POINT',target_id:'g.majlis',
   parameters:{point_type:'smoke',x:999,z:2}}],
 ['add_point_no_type','villa',{type:'ADD_POINT',target_id:'g.majlis',
   parameters:{x:2,z:2}}],
 ['move_point','pointed',{type:'MOVE_POINT',target_id:'g.majlis.point_0',
   parameters:{x:2.5,z:2.5}}],
 ['move_point_outside','pointed',{type:'MOVE_POINT',target_id:'g.majlis.point_0',
   parameters:{x:-4,z:2.5}}],
 ['delete_point','pointed',{type:'DELETE_POINT',target_id:'g.majlis.point_1',
   parameters:{}}],
 ['point_props','pointed',{type:'CHANGE_POINT_PROPERTIES',
   target_id:'g.majlis.point_0',parameters:{height:2.6}}],
 ['point_props_empty','pointed',{type:'CHANGE_POINT_PROPERTIES',
   target_id:'g.majlis.point_0',parameters:{}}],
 ['hotel_resize','hotel',{type:'RESIZE_SPACE',target_id:'g.lobby',parameters:{w:12,d:9}}],
 ['clinic_rename','clinic',{type:'RENAME_SPACE',target_id:'g.reception',
   parameters:{name:'Front Desk'}}],
 ['mep_adjacent_wall','clash_mep',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.4}}]
];

/* حالات خصومية: تُمرَّر كما هي إلى المطبّع والمعاينة */
const adversarial=[
 ['null_command',null],
 ['string_command','MOVE_WALL'],
 ['array_command',[{type:'MOVE_WALL'}]],
 ['number_command',42],
 ['empty_object',{}],
 ['unknown_type',{type:'TELEPORT_WALL',target_id:'x',parameters:{}}],
 ['array_as_type',{type:['MOVE_WALL'],target_id:'x',parameters:{}}],
 ['numeric_type',{type:7,target_id:'x',parameters:{}}],
 ['forbidden_set_field',{type:'SET_ANY_FIELD',target_id:'x',parameters:{path:'a.b',value:1}}],
 ['forbidden_patch',{type:'PATCH_OBJECT',target_id:'x',parameters:{}}],
 /* المفتاح يُبنى عبر JSON.parse كي يكون خاصّية ذاتية حقيقية لا تعييناً للنموذج الأولي */
 ['proto_pollution',JSON.parse('{"type":"RENAME_SPACE","target_id":"g.majlis",'
   +'"parameters":{"name":"x","__proto__":{"polluted":true}}}')],
 ['constructor_key',JSON.parse('{"type":"RENAME_SPACE","target_id":"g.majlis",'
   +'"parameters":{"name":"x","constructor":{"a":1}}}')],
 ['script_value',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'<script>alert(1)</script>'}}],
 ['javascript_url',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'javascript:alert(1)'}}],
 ['eval_value',{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'eval(1+1)'}}],
 ['nan_delta',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:'NaN_MARKER'}}],
 ['inf_delta',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:'INF_MARKER'}}],
 ['huge_delta',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:1e308}}],
 ['huge_coord',{type:'ADD_SPACE',parameters:{template:'g',rect:[1e9,1e9,5,5],id:'far'}}],
 ['negative_dim',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:-5,d:5}}],
 ['zero_dim',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:0,d:5}}],
 ['string_dim',{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:'wide',d:5}}],
 ['array_target',{type:'RENAME_SPACE',target_id:['g.majlis'],parameters:{name:'x'}}],
 ['object_target',{type:'RENAME_SPACE',target_id:{id:'g.majlis'},parameters:{name:'x'}}],
 ['null_target',{type:'RENAME_SPACE',target_id:null,parameters:{name:'x'}}],
 ['unknown_target',{type:'RENAME_SPACE',target_id:'no.such.space',parameters:{name:'x'}}],
 ['params_array',{type:'RENAME_SPACE',target_id:'g.majlis',parameters:['name','x']}],
 ['params_string',{type:'RENAME_SPACE',target_id:'g.majlis',parameters:'name=x'}],
 ['constraints_array',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x'},constraints:['must_not_change']}],
 ['unknown_constraint',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x'},constraints:{must_explode:['SPACE_RECT']}}],
 ['unknown_constraint_subject',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x'},constraints:{must_not_change:['THE_WEATHER']}}],
 ['negative_max_delta',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x'},constraints:{max_delta_m:-1}}],
 ['deep_nesting',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x',a:{b:{c:{d:{e:{f:{g:{h:1}}}}}}}}}],
 ['long_string',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:new Array(900).join('x')}}],
 ['bool_delta',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:true}}],
 ['unknown_snap',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.5},snap:'MAGNETIC'}],
 ['declared_unimplemented_snap',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
   parameters:{delta_m:0.5},snap:'ENDPOINT'}],
 ['bad_source',{type:'RENAME_SPACE',target_id:'g.majlis',
   parameters:{name:'x'},source:'ROOT'}],
 ['unknown_strategy',{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',
   parameters:{delta_m:0.5,hosted_strategy:'TELEPORT_THEM'}}],
 ['bad_lock_reason',{type:'LOCK_ELEMENT',target_id:'g.majlis',parameters:{reason:'BECAUSE'}}]
];

const out={models:models,scenarios:scenarios,adversarial:adversarial,
  base_revision_probe:'rev:0000000000000000'};
const dst=path.join(HERE,'fixtures','authoring_scenarios.json');
fs.writeFileSync(dst,JSON.stringify(out));
console.log('phase 5 fixtures written:',dst,
  Object.keys(models).length+' models,',scenarios.length+' scenarios,',
  adversarial.length+' adversarial');
