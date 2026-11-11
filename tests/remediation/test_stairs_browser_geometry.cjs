'use strict';
// Execute the shipped compiler branch. addBox is a geometry recorder here, not a
// duplicate stair implementation; the resolver, rotations and slab cuts stay real.
const assert=require('node:assert/strict'),vm=require('node:vm');
const APP=require('../lib/app_source.js');
const ctx={structuredClone,THREE:{Group:class{}}};vm.createContext(ctx);
vm.runInContext(APP.nodeBundle(['core/stairs.mjs','core/viewer.js','core/standards.js','core/disciplines.js','generated/pbr.js'])+'\nconst captured=[];addBox=(g,cx,cy,cz,w,h,d,material,tag,pick,color,rot)=>{captured.push({center:[cx,cy,cz],size:[w,h,d],material,tag,rot});};\nglobalThis.probe=(obj,cx=0,cz=0,base=0)=>{captured.length=0;buildObject({},obj,"stairs",cx,cz,base,"F0","core",0);return JSON.parse(JSON.stringify(captured));};',ctx);
const stair={id:'stair_core_0_1',kind:'stairs',form:'u_return',x:2,z:2,y:0,w:1.9,d:3.8,h:3.2,rot:0,count:1,pitch:1,dir:'x',stair:{schema:'acs.stair/1',source_level_index:0,target_level_index:1,source_elevation_m:0,target_elevation_m:3.2,flight_width_m:.9,gap_m:.1,tread_m:.25,risers_per_flight:9,entry_landing_m:.9,mid_landing_m:.9,landing_thickness_m:.15}};
const boxes=ctx.probe(stair);
assert.equal(boxes.length,17,'a U-return flight emits eight treads each side and one mid landing');
const mid=boxes.find(box=>box.tag.endsWith('|mid_landing'));
assert.ok(mid,'canonical component suffix identifies the mid landing');
assert.equal(Math.round((mid.center[1]+mid.size[1]/2)*1e6)/1e6,1.6,'mid landing top is halfway to the actual target level');
assert.equal(boxes.filter(box=>box.tag.includes('|f1_t')).length,8);
assert.equal(boxes.filter(box=>box.tag.includes('|f2_t')).length,8);
assert.ok(boxes.every(box=>box.tag.includes('|stair_core_0_1|')),'physical components preserve the canonical object ID');
assert.ok(boxes.every(box=>box.center[1]+box.size[1]/2<3.2),'target arrival is a retained slab, not a fictitious outgoing flight');
for(const rotation of [0,90,180,270]){
 const rotated=ctx.probe({...stair,rot:rotation},11,17,4.2);
 assert.equal(rotated.length,17);const angle=rotation*Math.PI/180;
 rotated.forEach((box,i)=>{
  const expected=[11+boxes[i].center[0]*Math.cos(angle)-boxes[i].center[2]*Math.sin(angle),4.2+boxes[i].center[1],17+boxes[i].center[0]*Math.sin(angle)+boxes[i].center[2]*Math.cos(angle)];
  box.center.forEach((value,axis)=>assert.ok(Math.abs(value-expected[axis])<1e-6,'exact local/world transform applied once'));
 });
}
for(const form of ['U_RETURN','',null,'spiral'])assert.throws(()=>ctx.probe({...stair,form}),/STAIR_FORM_UNSUPPORTED/,'an explicitly unsupported form never silently becomes a legacy straight flight');
const legacy={...stair};delete legacy.form;assert.equal(ctx.probe(legacy).length,21,'absent legacy form retains existing behavior without a physical U claim');
assert.throws(()=>ctx.probe({...stair,rot:45}),/STAIR_ROTATION_UNSUPPORTED/,'unsupported opening rotation cannot be rendered as an accepted flight');
vm.runInContext('globalThis.compileCapture=model=>{captured.length=0;compile(model);return JSON.parse(JSON.stringify(captured));};Object.assign(globalThis,{withDefaultStairs,stairConnections,compileArchitecture});',ctx);
const base={wall_t:.2,wall_h:3,floor_height:3.2,levels:[{index:0,template:'core'},{index:1,template:'core'}],floors:{core:{rooms:[{id:'s',role:'stairs',core_id:'c',rect:[0,0,4,4],doors:[{edge:'N',offset:2,width:1}],floor_color:'#cccccc',ceiling_color:'#ffffff'}]}}};
const overlap=(a,b)=>Math.max(0,Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1]));
const footprint=box=>[box.center[0]-box.size[0]/2,box.center[2]-box.size[2]/2,box.size[0],box.size[2]];
for(const edge of ['N','E','S','W']){
 const input=structuredClone(base);input.floors.core.rooms[0].doors[0].edge=edge;
 const model=ctx.withDefaultStairs(input)[0],before=JSON.stringify(model),connections=ctx.stairConnections(model),arch=ctx.compileArchitecture(model),compiled=ctx.compileCapture(model);
 assert.equal(connections.length,1);assert.equal(arch.voids.length,1,'one exact opening without duplicate full-core hole');
 const {opening,arrival}=connections[0];assert.deepEqual(Array.from(arch.voids[0].rect),Array.from(opening));
 const upperSlab=compiled.filter(box=>box.tag.startsWith('FLOOR|F1|slab|'));
 assert.ok(upperSlab.length>1,'target slab is cut into actual strips');
 for(const box of upperSlab)assert.ok(overlap(footprint(box),opening)<1e-6,'target slab does not cover the stair opening');
 const retained=upperSlab.reduce((area,box)=>area+overlap(footprint(box),arrival),0);
 assert.ok(Math.abs(retained-arrival[2]*arrival[3])<1e-6,'arrival landing remains fully supported by the geometric slab');
 const finish=compiled.filter(box=>box.tag.startsWith('FLOOR|F1|s|plate'));
 assert.ok(finish.length>1);for(const box of finish)assert.ok(overlap(footprint(box),opening)<1e-6,'floor finish cannot re-cover the opening');
 const ceiling=compiled.filter(box=>box.tag.startsWith('FLOOR|F0|s|ceil'));
 assert.ok(ceiling.length>1);for(const box of ceiling)assert.ok(overlap(footprint(box),opening)<1e-6,'source ceiling cannot block the physical flight');
 assert.equal(compiled.filter(box=>box.tag.startsWith('OBJ|F0|s|')).length,17);
 assert.equal(compiled.filter(box=>box.tag.startsWith('OBJ|F1|s|')).length,0,'top level has no fictitious outbound flight');
 assert.equal(JSON.stringify(model),before,'rendering preserves canonical geometry and provenance');
 const stale=structuredClone(model);stale.levels[1].elevation=4.2;
 assert.throws(()=>ctx.compileCapture(stale),/STAIR_CONNECTION_STALE/,'stale connection fails before geometry can replace the current view');
}
console.log('PASS shipped physical stairs: flights, landing, cardinal transforms, exact slab/finish/ceiling holes, arrival preservation, IDs and stale rejection');
