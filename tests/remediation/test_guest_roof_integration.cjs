'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const APP=require('../lib/app_source.js'),SEG=require('../lib/js_segment.js');
const source=APP.stripModuleSyntax(fs.readFileSync('public/app/ui/workspace-ui-wiring.js','utf8'),'wiring');
const statements=SEG.topLevelStatements(source).map(s=>source.slice(s.start,s.end));
function fn(name){const found=statements.find(s=>new RegExp('^function '+name+'\\(').test(SEG.head(s)));assert.ok(found,'shipped function '+name+' exists');return found;}
const context={structuredClone,TextEncoder,window:{ACS:{guest:true}},lastBuilding:null,floorsFound:new Set(),setModel:b=>{context.lastBuilding=b;return b;}};
vm.createContext(context);
vm.runInContext(APP.nodeBundle(['core/stairs.mjs','core/context-details.mjs','core/viewer.js','core/standards.js','core/roof.mjs'])+'\n'+['localGeneratedModel','localModelCounts','floorLabel','assertLocalRoofMutable','applyLocalEdit','localGenerationError','localRoofState','buildLocalRoofControl'].map(fn).join('\n')+'\nObject.assign(globalThis,{localGeneratedModel,localModelCounts,floorLabel,applyLocalEdit,localGenerationError,removeAutoRoof,roofRemovedByUser,withDefaultRoof,parseDescription,localRoofState,buildLocalRoofControl});',context);
const bare={wall_h:3,floor_height:3.2,levels:[{index:0,template:'g'},{index:1,template:'g'}],floors:{g:{rooms:[{id:'r',rect:[0,0,4,5]}]}}};
const before=JSON.stringify(bare),fresh=context.localGeneratedModel(bare,{freshSample:true});
assert.equal(fresh.levels.filter(l=>l.kind==='roof').length,1);assert.equal(JSON.stringify(bare),before);
context.lastBuilding=context.removeAutoRoof(fresh);
const regenerated=context.localGeneratedModel(bare);assert.ok(context.roofRemovedByUser(regenerated));assert.equal(regenerated.levels.length,2);
assert.equal(context.localGeneratedModel(bare,{freshSample:true}).levels.length,3);
const edited=structuredClone(regenerated);edited.floors.g.rooms[0].rect[2]=6;context.applyLocalEdit(edited);assert.ok(context.roofRemovedByUser(context.lastBuilding));
context.lastBuilding=fresh;const wider=structuredClone(fresh);wider.floors.g.rooms[0].rect[2]=7;context.applyLocalEdit(wider);assert.equal(context.lastBuilding.floors.roof.rooms[0].rect[2],7);
const locked=structuredClone(fresh);locked._authoring_locks={r:{locked:true}};context.lastBuilding=locked;assert.throws(()=>context.applyLocalEdit(wider),/LOCK_CONTEXT_CHANGED/);assert.equal(context.lastBuilding,locked);
const collision=structuredClone(bare);collision.floors.roof={rooms:[]};context.lastBuilding=context.localGeneratedModel(collision,{freshSample:true});assert.equal(context.lastBuilding.levels.at(-1).template,'roof_2');context.applyLocalEdit(bare,{generated:true});assert.equal(context.lastBuilding.levels.at(-1).template,'roof');assert.deepEqual(Object.keys(context.lastBuilding.floors).sort(),['g','roof']);
context.lastBuilding=fresh;const unknownHeight=structuredClone(bare);unknownHeight.floor_height=null;assert.throws(()=>context.applyLocalEdit(unknownHeight,{generated:true}),/ROOF_HEIGHT_NOT_SPECIFIED/);assert.equal(context.lastBuilding,fresh,'failed default roof generation preserves prior model');
const counts=context.localModelCounts(fresh);assert.equal(counts.occupied_levels,2);assert.equal(counts.occupied_rooms,2);assert.equal(counts.roof_levels,1);assert.equal(counts.roof_decks,1);
context.lastBuilding=fresh;assert.equal(context.floorLabel('F2'),'السطح');context.lastBuilding=bare;assert.notEqual(context.floorLabel('F1'),'السطح');
context.document={createElement:()=>({setAttribute(){}})};
// The compiler accepts legacy/null level rows using acsRenderLevel's display address.
// UI derivation must tolerate the same input without writing inferred indices to it.
for(const levels of [null,7,{},[null,{}, {template:'g',kind:'roof'}]]){
  const legacy={...structuredClone(bare),levels},saved=JSON.stringify(legacy);context.lastBuilding=legacy;
  assert.doesNotThrow(()=>context.localModelCounts(legacy),'legacy levels do not break the model count');
  assert.doesNotThrow(()=>context.floorLabel('F2'),'legacy levels do not break floor labels');
  assert.doesNotThrow(()=>context.localRoofState(),'legacy levels do not break roof controls');
  assert.doesNotThrow(()=>context.buildLocalRoofControl({appendChild(){}}),'actual contextual control tolerates the imported levels');
  assert.equal(JSON.stringify(legacy),saved,'display normalization must not modify imported data');
}
context.lastBuilding={...structuredClone(bare),levels:[null,{template:'g',kind:'roof'}]};
assert.equal(context.floorLabel('F1'),'السطح','explicit roof uses the compiler-derived display index');
assert.equal(context.localModelCounts(context.lastBuilding).roof_levels,1);
const high=structuredClone(bare);high.levels=Array.from({length:63},(_,index)=>({index,template:'g'}));context.lastBuilding=null;assert.equal(context.localGeneratedModel(high).levels.length,64);high.levels.push({index:63,template:'g'});assert.throws(()=>context.applyLocalEdit(high,{generated:true}),/ROOF_LEVEL_LIMIT_EXCEEDED/);assert.equal(context.lastBuilding,null);
context.lastBuilding=context.removeAutoRoof(fresh);assert.equal(context.localGeneratedModel(high).levels.length,64);
assert.throws(()=>context.parseDescription('غرفة 4x5',30,25,64),/LOCAL_LEVEL_LIMIT_EXCEEDED/);
const generated=context.parseDescription('غرفة 4x5',30,25,2);assert.equal(generated.levels.length,3);assert.equal(generated.floors.roof,undefined);assert.equal(generated.floors.typical.rooms.length,1);
const setter=fn('setModel');assert.ok(!/withDefaultRoof|carryAutoRoof|localGeneratedModel/.test(setter),'generic import/recovery setter never adds roof');
assert.match(source,/setModel\(localGeneratedModel\(EXAMPLE,\{freshSample:true\}\)\)/);assert.match(source,/applyLocalEdit\(buildLocal\(txt,W,D,nF\),\{generated:true\}\)/,'actual local generation uses edit boundary');
assert.match(fn('buildLocalRoofControl'),/className='btn ghost acs-u-15'/,'toggle uses existing44px class');
assert.match(fs.readFileSync('public/app/styles/app.css','utf8'),/\.acs-u-15\{[^}]*min-height:44px/);
assert.match(context.localGenerationError(new Error('ROOF_LEVEL_LIMIT_EXCEEDED')),/64.*السطح/);assert.match(context.localGenerationError(new Error('LOCAL_LEVEL_LIMIT_EXCEEDED')),/64/);assert.match(context.localGenerationError(new Error('LOCK_CONTEXT_CHANGED')),/مقفول/);
for(const [code,meaning]of [
  ['ROOF_HEIGHT_NOT_SPECIFIED',/أكمل ارتفاع.*لم نفترض/],['ROOF_HEIGHT_INVALID',/أرقام موجبة/],
  ['ROOF_LEVEL_ELEVATION_NOT_SPECIFIED',/أكمل رقم المستوى/],['ROOF_LEVEL_ELEVATION_INVALID',/عدد صحيح/],
  ['ROOF_TOP_LEVEL_HAS_NO_ROOMS',/أضف غرفاً/],['ROOF_NO_OCCUPIED_LEVEL',/أضف مستوى مشغولاً/],
  ['ROOF_LEVEL_EXISTS',/سطح ثانٍ/],['ROOF_NOT_AUTOMATIC',/المؤلف يدوياً/],
  ['ROOF_PREFERENCE_CONFLICT',/اختر استعادة/],['ROOF_PARAPET_HEIGHT_INVALID',/بين 0 و2 متر/]
]){const message=context.localGenerationError(new Error(code));assert.match(message,meaning);assert.ok(!message.includes('ROOF_'),'ordinary UI shows an actionable Arabic explanation');}
// Execute the actual setter with renderer boundaries replaced, not its state logic.
// A new successful model resets selection; a presentation rebuild or rejected
// compilation must preserve the current visible selection and canonical model.
const previous={site:{w:10,d:10},levels:[{index:0,template:'g'}]},replacement={site:{w:20,d:20},levels:[{index:0,template:'g'}]};
const view={lastBuilding:previous,model:null,floorSel:'F9',matCache:{},registry:{},floorsFound:new Set(),doorMeshes:[],
  isProjectModel:()=>false,compile:()=>({traverse(){}}),scene:{add(){},remove(){}},bounds:{c:{set(){}},r:1},
  acsReconcileCamera:()=>({applied:true,bounds:{cx:0,cy:1,cz:0,radius:1}}),
  sun:{shadow:{camera:{updateProjectionMatrix(){}}},target:{position:{copy(){}}}},ensureGround(){},buildFloors(){},buildLayers(){},updateVis(){},
  localModelCounts:()=>({occupied_rooms:1,occupied_levels:1,roof_levels:0}),acsCompileSummary:()=>({degraded:false}),statusEl:{},
  document:{getElementById:()=>null,querySelectorAll:()=>[]},window:{ACS:{}},showTab(){}};
vm.createContext(view);vm.runInContext(fn('setModel')+';globalThis.applyActual=setModel;',view);
view.applyActual(replacement);assert.equal(view.floorSel,'all','explicit replacement clears an old selected roof');assert.equal(view.lastBuilding,replacement);
view.floorSel='F0';view.applyActual(null);assert.equal(view.floorSel,'F0','presentation-only rebuild preserves selected floor');
view.floorSel='F7';const oldView=view.model;view.compile=()=>{throw new Error('compile refused');};assert.throws(()=>view.applyActual(previous),/compile refused/);assert.equal(view.floorSel,'F7');assert.equal(view.lastBuilding,replacement);assert.equal(view.model,oldView);
// The roof command must obey the same atomicity, including its own pre-setter work.
view.lastBuilding=fresh;view.floorSel='F2';
Object.assign(view,{removeAutoRoof:context.removeAutoRoof,SCENE_LIMITS:vm.runInContext('SCENE_LIMITS',context)});
vm.runInContext(fn('assertLocalRoofMutable')+'\n'+fn('changeLocalRoof')+';globalThis.changeRoof=changeLocalRoof;',view);
assert.throws(()=>view.changeRoof('remove'),/compile refused/);
assert.equal(view.floorSel,'F2','failed roof removal preserves selected roof');
assert.equal(view.lastBuilding,fresh,'failed roof removal preserves canonical model');assert.equal(view.model,oldView,'failed roof removal preserves visible model');
// A default edit must reject a failed roof derivation before invoking the setter.
// Exercise the shipped edit handler, roof helper and setter together.
view.carryAutoRoof=vm.runInContext('carryAutoRoof',context);
vm.runInContext(fn('applyLocalEdit')+';globalThis.applyEdit=applyLocalEdit;',view);
let editCompiles=0;view.compile=()=>{editCompiles++;return {traverse(){}};};
view.lastBuilding=fresh;view.floorSel='F2';
assert.throws(()=>view.applyEdit(unknownHeight),/ROOF_HEIGHT_NOT_SPECIFIED/);
assert.equal(editCompiles,0,'invalid default edit never reaches compilation');
assert.equal(view.lastBuilding,fresh);assert.equal(view.model,oldView);assert.equal(view.floorSel,'F2');
// An explicit removal preference remains a valid roofless edit, not an omission failure.
view.lastBuilding=context.removeAutoRoof(fresh);
const allowed=view.applyEdit(bare);assert.equal(editCompiles,1);
assert.ok(context.roofRemovedByUser(allowed));assert.ok(context.roofRemovedByUser(view.lastBuilding));
assert.equal(view.lastBuilding.levels.some(level=>level.kind==='roof'),false);assert.equal(view.floorSel,'all');
console.log('PASS guest roof integration: creation/removal/regeneration/edit/locks/counts/explicit labels/physical level limits/import preservation/44px/Arabic errors');
