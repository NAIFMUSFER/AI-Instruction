// Compare the actual independent Python and native JS implementations. No DOM,
// Three.js, provider requests, mock geometry or npm dependency is involved.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),APP=require('../lib/app_source.js');
const compileArchitecture=new Function(APP.nodeBundle()+';return compileArchitecture;')();
import {hasUStairs,resolveStairGeometry,stairConnections,withDefaultStairs,validateStairReport} from '../../public/app/core/stairs.mjs';
const clone=value=>JSON.parse(JSON.stringify(value));
const model=()=>({wall_t:.2,wall_h:3,floor_height:3.2,levels:[{index:0,template:'core'},{index:1,template:'core'}],floors:{core:{rooms:[{id:'s',role:'stairs',core_id:'vertical',rect:[0,0,4,4],doors:[{edge:'N',offset:2,width:1}],floor_color:'#cccccc',ceiling_color:'#ffffff'}]}}});
const cases=[];function add(id,op,value){cases.push({id,op,value});}
for(const edge of ['N','E','S','W']){const m=model();m.floors.core.rooms[0].doors[0].edge=edge;add('edge-'+edge,'default',m);add('architecture-'+edge,'architecture',withDefaultStairs(m)[0]);}
const uneven=model();uneven.levels=[{index:9,template:'core',elevation:-3.2},{index:-2,template:'core',elevation:0},{index:4,template:'core',elevation:3.6},{index:0,template:'roof',kind:'roof',elevation:6.8}];uneven.floors.roof={rooms:[{id:'deck',rect:[0,0,4,4]}]};add('elevation-order-and-roof','default',uneven);add('architecture-nonuniform-elevation','architecture',withDefaultStairs(uneven)[0]);
for(const [id,change]of [
 ['narrow',m=>m.floors.core.rooms[0].rect=[0,0,2,3]],
 ['unknown-elevation',m=>delete m.floor_height],
 ['unknown-core',m=>delete m.floors.core.rooms[0].core_id],
 ['only-named-room',m=>delete m.floors.core.rooms[0].role],
 ['rise-too-high',m=>m.floor_height=4.2],
 ['door-missing',m=>m.floors.core.rooms[0].doors=[]],
 ['two-doors',m=>m.floors.core.rooms[0].doors.push({edge:'S',offset:2,width:1})],
 ['door-offset',m=>m.floors.core.rooms[0].doors[0].offset=.2],
 ['authored-object',m=>m.floors.core.rooms[0].objects=[{id:'old',kind:'stairs',x:2,z:2,w:1,d:2,h:3.2}]],
 ['unicode-core-over-limit',m=>m.floors.core.rooms[0].core_id='نواة🏠'.repeat(60)],
 ['unicode-core-boundary',m=>m.floors.core.rooms[0].core_id='نواة🏠'.repeat(30)],
 ['authored-arabic',m=>m.floors.core.rooms[0].objects=[{id:'old',name:'درج خاص'}]],
 ['unsupported-form',m=>m.floors.core.rooms[0].objects=[{kind:'stairs',form:'U_RETURN'}]],
 ['malformed-objects',m=>m.floors.core.rooms[0].objects=null],
 ['malformed-rooms',m=>m.floors.core.rooms=null],
 ['malformed-floor',m=>m.floors.core=[]],
 ['malformed-level',m=>m.levels[0]=null],
 ['malformed-template',m=>m.levels[0].template={}],
 ['forged-default-report',m=>m.meta={acs_stairs:{schema:'acs.stairs/1',source:'system_default',generated_connections:999,unsupported:[],physical_traversal:'VERIFIED'}}],
 ['shared-roof-template',m=>m.levels.push({index:2,template:'core',kind:'roof',elevation:6.4})],
 ['instance-room-cap',m=>{m.levels=Array.from({length:64},(_,index)=>({index,template:'core'}));m.floors.core.rooms.push(...Array.from({length:39},(_,i)=>({id:'r'+i,role:'living',rect:[5+i*2,0,2,2]})));}],
 ['nested-id-collision',m=>m.floors.core.rooms[0].furniture=[{id:'stairs_vertical_0_1',name:'preserve'}]],
 ['template-collision',m=>m.floors.core__stairs_1={rooms:[]}],
 ['unicode-core-template',m=>{m.floors.core.rooms[0].core_id='نواة🏠'.repeat(40);const f=m.floors.core;delete m.floors.core;m.floors['طابق🏠'.repeat(40)]=f;for(const l of m.levels)l.template='طابق🏠'.repeat(40);}],
 ['empty-metadata',m=>m.meta={other:'retained'}],
 ['bad-metadata',m=>m.meta=[]],
 ['level-limit',m=>m.levels=Array.from({length:65},(_,index)=>({index,template:'core'}))],
 ['one-level',m=>m.levels.splice(1)],
 ['null-index',m=>m.levels[1].index=null],
 ['null-elevation',m=>m.levels[1].elevation=null],
 ['same-elevation',m=>m.levels[1].elevation=0],
]){const m=model();change(m);add(id,'default',m);}
add('model-null','default',null);add('model-array','default',[]);
// Resource admission uses the actual Python guard to find the one-byte boundary.
// Metadata 1 and 1.0 must have the same bound despite different native serializers.
const boundaryPy=`import sys,json
from acs_stairs import _resource_limited,_levels
m=json.load(sys.stdin)
def bound(number):
 lo,hi=0,600001
 while lo+1<hi:
  n=(lo+hi)//2;m['meta']={'scalar':number,'padding':'x'*n}
  if _resource_limited(m,_levels(m)):hi=n
  else:lo=n
 return lo
print(json.dumps({'integer':bound(1),'float':bound(1.0)}))`;
const boundaryRun=spawnSync(process.env.PYTHON||'python',['-c',boundaryPy],{input:JSON.stringify(model()),encoding:'utf8',timeout:60000});
assert.equal(boundaryRun.status,0,boundaryRun.stderr||boundaryRun.error?.message);
const boundary=JSON.parse(boundaryRun.stdout);assert.equal(boundary.integer,boundary.float,'1/1.0 resource accounting has no serializer drift');
assert.ok(boundary.integer>1000&&boundary.integer<600000,'actual resource bound found, not a vacuous test');
for(const [suffix,n]of [['exact-fit',boundary.integer],['one-byte-over',boundary.integer+1]]){const m=model();m.meta={scalar:1,padding:'x'.repeat(n)};add('resource-'+suffix,'default',m);}
const many=model();many.levels=Array.from({length:45},(_,index)=>({index,template:'core'}));many.floors.core.rooms=Array.from({length:3},(_,i)=>({...clone(model().floors.core.rooms[0]),id:'s'+i,core_id:'c'+i,rect:[i*5,0,4,4]}));add('resource-132-connections','default',many);
const largeDescription=model();largeDescription.levels=Array.from({length:4},(_,index)=>({index,template:'core'}));largeDescription.floors.core.description='وصف'.repeat(30000);add('resource-clone-size','default',largeDescription);
const manyNodes=model();manyNodes.meta={nodes:Array(30001).fill(null)};add('resource-node-count','default',manyNodes);
const unsafe=model();unsafe.meta={number:Number.MAX_SAFE_INTEGER+1};add('resource-numeric-range','default',unsafe);
const acceptedBoundary=model();acceptedBoundary.meta={scalar:1,padding:'x'.repeat(boundary.integer)};assert.equal(withDefaultStairs(acceptedBoundary)[2],null);
const rejectedBoundary=model();rejectedBoundary.meta={scalar:1,padding:'x'.repeat(boundary.integer+1)};const limited=withDefaultStairs(rejectedBoundary);assert.equal(limited[0],rejectedBoundary,'limit denial returns the original without deep clone');assert.equal(limited[2],'STAIR_RESOURCE_LIMIT');assert.equal(rejectedBoundary.meta.acs_stairs,undefined);

const physical=withDefaultStairs(model())[0];
add('canonical-connections','connections',physical);add('idempotent-default','default',physical);
const obj=stairConnections(physical)[0].object;add('canonical-resolver','resolve',obj);
for(const rotation of [-360,-90,0,90,180,270,360])add('rotation-'+rotation,'resolve',{...obj,rot:rotation});
for(const [id,change]of [
 ['stale-height',m=>m.levels[1].elevation=4.2],
 ['stale-source-roof',m=>m.levels[0].kind='roof'],
 ['stale-target-door',m=>m.floors[m.levels[1].template].rooms[0].doors[0].edge='S'],
 ['stale-target-core',m=>m.floors[m.levels[1].template].rooms[0].rect[2]=5],
 ['scope-record-key-order',m=>m.levels[1].stair_template_instance.room_mapping=m.levels[1].stair_template_instance.room_mapping.map(({id,role})=>({role,id}))],
 ['stale-scope-record',m=>delete m.levels[1].stair_template_instance],
 ['stale-scope-mapping',m=>m.levels[1].stair_template_instance.room_mapping[0].role='living'],
 ['stale-target-id',m=>m.floors[m.levels[1].template].rooms[0].core_id='other'],
]){const m=clone(physical);change(m);add(id,'connections',m);}
for(const [id,change]of [
 ['missing-id',o=>delete o.id],['long-id',o=>o.id='x'.repeat(161)],['unsupported-form-null',o=>o.form=null],
 ['oblique',o=>o.rot=45],['huge-risers',o=>o.stair.risers_per_flight=100000],['boolean-risers',o=>o.stair.risers_per_flight=true],
 ['string-height',o=>o.h='3.2'],['missing-position',o=>delete o.x],['wrong-height',o=>o.h=3],['raised-object',o=>o.y=.1],
 ['zero-gap',o=>o.stair.gap_m=0],['schema',o=>o.stair.schema='bad'],['repetition',o=>o.count=2],['wrong-footprint',o=>o.d=3.9],
]){const o=clone(obj);change(o);add(id,'resolve',o);}
const py=`import sys,json,copy\nfrom acs_stairs import with_default_stairs,stair_connections,resolve_stair_geometry\nfrom acs_arch import compile_architecture\nmethods={'default':with_default_stairs,'connections':stair_connections,'resolve':resolve_stair_geometry,'architecture':compile_architecture}\nout=[]\nfor c in json.load(sys.stdin):\n v=c['value']; before=copy.deepcopy(v)\n try:\n  result=methods[c['op']](v); row={'id':c['id'],'outcome':'return','value':result}\n except Exception as e:\n  row={'id':c['id'],'outcome':'error','error':str(e)}\n row['mutated']=v!=before;out.append(row)\nprint(json.dumps(out,ensure_ascii=False,allow_nan=False))`;
const run=spawnSync(process.env.PYTHON||'python',['-c',py],{input:JSON.stringify(cases),encoding:'utf8',timeout:60000,maxBuffer:8*1024*1024});
assert.equal(run.status,0,run.stderr||run.error?.message);const expected=JSON.parse(run.stdout);
const methods={default:withDefaultStairs,connections:stairConnections,resolve:resolveStairGeometry,architecture:compileArchitecture};
for(const [i,c]of cases.entries()){
 const value=clone(c.value),before=clone(value);let actual;
 try{actual={id:c.id,outcome:'return',value:methods[c.op](value)};}catch(error){actual={id:c.id,outcome:'error',error:error.message};}
 actual.mutated=JSON.stringify(value)!==JSON.stringify(before);
 assert.equal(actual.mutated,false,c.id+' pure helper preserves input');
 assert.deepEqual(clone(actual),expected[i],c.id+' exact Python/JS value, error, identity and rounding parity');
}
// Independent oracles prevent a matching bug in the two implementations from
// being promoted to a capability: these conditions must refuse or preserve data.
const falseRoof=clone(physical);falseRoof.levels[0].kind='roof';assert.throws(()=>stairConnections(falseRoof),/STAIR_ROOF_ACCESS_UNSUPPORTED/);
const collision=model();collision.floors.core.rooms[0].furniture=[{id:'stairs_vertical_0_1'}];const collisionOut=withDefaultStairs(collision)[0];assert.equal(stairConnections(collisionOut)[0].source_object_id,'stairs_vertical_0_1_2');
const forged=model();forged.meta={acs_stairs:{schema:'acs.stairs/1',source:'system_default',generated_connections:999,physical_traversal:'VERIFIED',unsupported:[]}};assert.equal(withDefaultStairs(forged)[2],'STAIR_REPORT_INVALID');assert.throws(()=>validateStairReport(forged),/STAIR_REPORT_INVALID/);
const roofSharing=model();roofSharing.levels.push({index:2,template:'core',kind:'roof',elevation:6.4});const roofBefore=clone(roofSharing.floors.core),roofAfter=withDefaultStairs(roofSharing)[0];assert.deepEqual(roofAfter.floors.core,roofBefore);assert.equal(stairConnections(roofAfter).length,1);assert.equal(roofAfter.levels[2].template,'core');
const unicode=model();unicode.floors.core.rooms[0].core_id='نواة🏠'.repeat(30);const unicodeObj=stairConnections(withDefaultStairs(unicode)[0])[0].object;assert.equal(Array.from(unicodeObj.id).length,160);assert.match(unicodeObj.id,/_[a-f0-9]{20}$/);
assert.equal(hasUStairs(physical),true);assert.equal(hasUStairs(model()),false);
const source=readFileSync(new URL('../../public/app/core/stairs.mjs',import.meta.url),'utf8');assert.doesNotMatch(source,/^import\s/m,'physical compiler dependency remains a pure leaf');
console.log(`PASS physical stairs parity: ${cases.length} independent Python/JS scenarios, immutable inputs, Unicode IDs, unsupported and stale geometry`);
