import test from 'node:test';
import assert from 'node:assert/strict';
import {createHistory,generate,understand,current,clone,propose,commitPreview,area} from '../shared/model.js';
import {createRenderScene,stableJSON,renderSettings} from '../shared/render-scene.js';
const fixture=()=>createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم')));
test('render snapshot is immutable, deterministic, metre-based and revision-linked',()=>{
 const h=fixture(),m=current(h),before=JSON.stringify(h),s=createRenderScene(m,h.revisions[0].id);
 assert.equal(JSON.stringify(h),before);assert.equal(stableJSON(s),stableJSON(createRenderScene(m,h.revisions[0].id)));
 assert.equal(s.source.revisionId,h.revisions[0].id);assert.equal(s.units,'m');assert.equal(s.axes,'X-east Y-north Z-up');assert.equal(new Set(s.objects.map(o=>o.id)).size,s.objects.length);
 assert.equal(s.proofs.rooms.length,m.levels.reduce((n,l)=>n+l.rooms.length,0));
});
test('no descriptions, comments, accounts, uploaded references or arbitrary URLs cross render boundary',()=>{
 const h=fixture(),m=current(h);m.brief.prompt='PRIVATE_PROMPT';m.comments=[{id:'c1',roomId:m.levels[0].rooms[0].id,text:'PRIVATE_COMMENT',author:'PRIVATE_AUTHOR',resolved:false,at:new Date().toISOString()}];
 const s=JSON.stringify(createRenderScene(m,h.revisions[0].id));for(const word of ['PRIVATE_PROMPT','PRIVATE_COMMENT','PRIVATE_AUTHOR'])assert.ok(!s.includes(word));
 assert.ok(!Object.hasOwn(JSON.parse(s),'model'));
});
for(const input of [{quality:'ultra'},{finish:'__proto__'},{python:'import os'},{blendFile:'/etc/passwd'},{textureURL:'https://evil.test'},{roomId:[]},{furniture:1},null])test('render settings reject unsafe/unknown input '+JSON.stringify(input),()=>assert.throws(()=>renderSettings(input)));
test('render fails closed on unresolved geometry and nonexistent camera room',()=>{
 const h=fixture(),m=clone(current(h));m.levels[0].rooms[0].x=m.levels[0].rooms[1].x;m.levels[0].rooms[0].y=m.levels[0].rooms[1].y;
 assert.throws(()=>createRenderScene(m,'revision'));assert.throws(()=>createRenderScene(current(h),'r',{roomId:'missing'}));
});
test('wall geometry stays full-height and has no solid cell through an authored aperture',()=>{
 const h=fixture(),s=createRenderScene(current(h),'revision');
 for(const wall of s.proofs.walls){const boxes=s.objects.filter(o=>wall.objectIds.includes(o.id));assert.ok(boxes.length);assert.ok(boxes.every(b=>b.size[wall.axis==='v'?0:1]===wall.thickness));
  for(const b of boxes){const along=b.min[wall.axis==='v'?1:0]+b.size[wall.axis==='v'?1:0]/2,z=b.min[2]+b.size[2]/2-wall.elevation;assert.ok(!wall.apertures.some(a=>along>a.a&&along<a.b&&z>a.z&&z<a.top));}
  assert.ok(Math.abs(Math.max(...boxes.map(b=>b.min[2]+b.size[2]))-(wall.elevation+wall.height))<.00001);
 }
});
test('L-shaped room export does not fill the carved-out floor or roof area',()=>{
 const h=fixture(),base=current(h),r=base.levels.at(-1).rooms.find(r=>!r.locked&&r.kind==='bedroom');
 let next;for(const corner of ['ne','nw','se','sw']){try{next=commitPreview(base,propose(base,{type:'notch',roomId:r.id,width:.45,depth:.45,corner}));break;}catch{}}
 assert.ok(next);const room=next.levels.at(-1).rooms.find(x=>x.id===r.id),s=createRenderScene(next,'r');
 const floors=s.objects.filter(o=>o.category==='space-floor'&&o.roomId===r.id),sum=floors.reduce((n,o)=>n+o.size[0]*o.size[1],0);assert.ok(Math.abs(sum-area(room))<.002);assert.ok(sum<r.w*r.d);
});
test('changing finishes never changes geometric boxes or canonical history',()=>{
 const h=fixture(),a=createRenderScene(current(h),'r',{finish:'warm'}),b=createRenderScene(current(h),'r',{finish:'slate'});
 assert.deepEqual(a.objects,b.objects);assert.notDeepEqual(a.materials,b.materials);assert.deepEqual(a.proofs,b.proofs);
});
