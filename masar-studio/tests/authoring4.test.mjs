import test from 'node:test';
import assert from 'node:assert/strict';
import { understand, generate, clone, propose, commitPreview, parseCommand, diffModels, area, roomPolygon, validate } from '../shared/model.js';
import { authoringDefaults, effectiveAuthoring, wallTypeFor, windowTypeFor } from '../shared/authoring.js';
import { deriveBuildingGraph, evaluateRulePack, exportIFC } from '../shared/building.js';
import { parseIFC } from '../shared/ifc.js';
import { planSVG, sceneBoxes } from '../shared/geometry.js';

const fixture=()=>generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم الشارع جنوب مع مصعد، المجلس قرب المدخل والمعيشة على الحديقة'));
const roomWithExteriorWindow=m=>m.levels.flatMap(l=>l.rooms).find(r=>(r.windows||[]).length);

test('4.0 authoring defaults expose distinct composite external/internal wall types',()=>{
  const a=authoringDefaults(), ext=a.wallTypes.find(t=>t.classification==='external'), int=a.wallTypes.find(t=>t.classification==='internal');
  assert.ok(ext&&int); assert.notEqual(ext.id,int.id); assert.notEqual(ext.totalThickness,int.totalThickness);
  for(const t of [ext,int]) assert.ok(Math.abs(t.layers.reduce((n,l)=>n+l.thickness,0)-t.totalThickness)<.002);
});

test('legacy schema-v1 projects receive effective authoring defaults without canonical mutation',()=>{
  const m=fixture(), before=JSON.stringify(m); delete m.authoring; const stripped=JSON.stringify(m), a=effectiveAuthoring(m);
  assert.ok(a.wallTypes.length>=2&&a.windowTypes.length>=1); assert.equal(JSON.stringify(m),stripped); assert.notEqual(stripped,before);
});

test('generated hosted windows are canonical, typed, finite and model-valid',()=>{
  const m=fixture(), r=roomWithExteriorWindow(m); assert.ok(r); const w=r.windows[0];
  assert.ok(w.id&&['north','south','east','west'].includes(w.side)); assert.ok(Number.isFinite(w.width)&&Number.isFinite(w.height)&&Number.isFinite(w.sill));
  assert.equal(windowTypeFor(m,w.typeId).id,w.typeId); assert.doesNotThrow(()=>validate(m));
});

test('hosted window authoring is previewed then committed with stable identity',()=>{
  const m=fixture(), r=roomWithExteriorWindow(m), old=r.windows[0], p=propose(m,{type:'window',roomId:r.id,windowId:old.id,side:old.side,typeId:old.typeId,width:1.4,height:1.3,sill:.8,offset:.45});
  assert.equal(p.blockers.length,0); assert.equal(JSON.stringify(m).includes('"width":1.4'),false);
  const n=commitPreview(m,p), w=n.levels.flatMap(l=>l.rooms).find(x=>x.id===r.id).windows.find(x=>x.id===old.id); assert.equal(w.width,1.4); assert.equal(w.id,old.id);
});

test('hosted window removal is transactional and leaves the source untouched',()=>{
  const m=fixture(), r=roomWithExteriorWindow(m), id=r.windows[0].id, before=JSON.stringify(m), p=propose(m,{type:'remove-window',roomId:r.id,windowId:id});
  assert.equal(JSON.stringify(m),before); const n=commitPreview(m,p); assert.equal(n.levels.flatMap(l=>l.rooms).find(x=>x.id===r.id).windows.some(w=>w.id===id),false);
});

test('L-notch authoring creates an exact orthogonal polygon while retaining bbox semantics',()=>{
  const m=fixture(), r=m.levels[0].rooms.find(x=>x.kind==='majlis'), oldArea=area(r), p=propose(m,{type:'notch',roomId:r.id,width:.75,depth:.5,corner:'ne'});
  assert.equal(p.blockers.length,0); const n=commitPreview(m,p), nr=n.levels[0].rooms.find(x=>x.id===r.id);
  assert.equal(nr.x,r.x); assert.equal(nr.y,r.y); assert.equal(nr.w,r.w); assert.equal(nr.d,r.d); assert.equal(roomPolygon(nr).length,6); assert.equal(area(nr),Math.round((oldArea-.375)*1000)/1000);
});

test('moving a polygon room translates every authored vertex by the same vector',()=>{
  const m=fixture(), r=m.levels[0].rooms.find(x=>x.kind==='majlis'), notched=commitPreview(m,propose(m,{type:'notch',roomId:r.id,width:.5,depth:.5,corner:'nw'})), a=notched.levels[0].rooms.find(x=>x.id===r.id), before=clone(a.footprint);
  const preview=propose(notched,{type:'move',roomId:r.id,x:a.x+.25,y:a.y+.5}), moved=preview.candidate.levels[0].rooms.find(x=>x.id===r.id);
  assert.deepEqual(moved.footprint,before.map(([x,y])=>[Math.round((x+.25)*1000)/1000,Math.round((y+.5)*1000)/1000]));
});

test('local Arabic parser resolves hosted-window and L-notch commands deterministically',()=>{
  const m=fixture(), r=m.levels[0].rooms.find(x=>x.kind==='majlis');
  assert.deepEqual(parseCommand('نافذة شمال 1.5 متر',m,r.id),{type:'window',roomId:r.id,side:'north',width:1.5});
  assert.deepEqual(parseCommand('تجويف 1×0.5 شمال شرق',m,r.id),{type:'notch',roomId:r.id,width:1,depth:.5,corner:'ne'});
});

test('project-level wall layer edits are visible in canonical diff and retain layer-sum integrity',()=>{
  const m=fixture(), n=clone(m); n.authoring=effectiveAuthoring(n); n.authoring.wallTypes=clone(n.authoring.wallTypes); const t=n.authoring.wallTypes[0]; t.layers=clone(t.layers); t.layers[0].thickness=.03; t.totalThickness=Math.round(t.layers.reduce((s,l)=>s+l.thickness,0)*1000)/1000;
  const d=diffModels(m,n); assert.ok(d.some(x=>x.id==='project:authoring')); assert.equal(wallTypeFor(n,true).totalThickness,t.totalThickness); assert.doesNotThrow(()=>validate(n));
});

test('derived authoring graph resolves canonical windows to external host walls and quality remains non-compliance',()=>{
  const m=fixture(), g=deriveBuildingGraph(m), wins=g.elements.openings.filter(o=>o.type==='window'); assert.ok(wins.length);
  for(const w of wins){const host=g.elements.walls.find(x=>x.id===w.hostWallId); assert.ok(host); assert.equal(host.external,true);}
  const qa=evaluateRulePack(m); assert.equal(qa.pack.id,'masar-authoring-quality-2026.2'); assert.equal(qa.pack.compliance,false); assert.equal(qa.results.filter(x=>x.ruleId==='window-host'&&x.status==='fail').length,0);
});

test('polygon presentation geometry preserves exact floor area and SVG emits the true polygon',()=>{
  const m=fixture(), r=m.levels[0].rooms.find(x=>x.kind==='majlis'), n=commitPreview(m,propose(m,{type:'notch',roomId:r.id,width:.8,depth:.6,corner:'se'})), nr=n.levels[0].rooms.find(x=>x.id===r.id);
  const floor=sceneBoxes(n,{levelId:'l0'}).filter(b=>b.kind==='floor'&&b.roomId===r.id), sum=Math.round(floor.reduce((s,b)=>s+b.w*b.d,0)*1000)/1000;
  assert.equal(sum,area(nr)); const svg=planSVG(n,'l0'); assert.match(svg,new RegExp(`<polygon[^>]+data-canonical-room-id=|<polygon`)); assert.ok(svg.includes(roomPolygon(nr)[0].join(',')));
});

test('MASAR IFC4 export reimports the supported spaces/doors/windows subset and rejects IFC2X3',()=>{
  const m=fixture(), text=exportIFC(m), imported=parseIFC(text), a=deriveBuildingGraph(m).counts, b=deriveBuildingGraph(imported).counts;
  assert.equal(imported.levels.length,m.levels.length); assert.equal(b.spaces,a.spaces); assert.equal(b.doors,a.doors); assert.equal(b.windows,a.windows); assert.doesNotThrow(()=>validate(imported));
  assert.throws(()=>parseIFC(text.replace("'IFC4'","'IFC2X3'")),/IFC4/);
});
