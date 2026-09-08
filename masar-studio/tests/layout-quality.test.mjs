import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {generate,understand,clone,validate,area,conceptEnvelopeArea,roomPolygon,pointInPolygon,doorPoint,createHistory,pushHistory,current,exportEnvelope,importEnvelope,checkLocks} from '../shared/model.js';
import {deriveBuildingGraph,exportIFC} from '../shared/building.js';
import {createRenderScene} from '../shared/render-scene.js';
import {reviewLayout,compactCirculationAlternative,interiorRectangles} from '../shared/layout-quality.js';
const text=readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
const base=()=>generate(understand(text));
const alt=m=>{const result=compactCirculationAlternative(m);assert.ok(result.alternative,result.reason);return result.alternative;};
const errors=m=>validate(m).filter(i=>i.status==='error');
function links(m) {
 const rooms=m.levels[0].rooms,graph=new Map(rooms.map(r=>[r.id,new Set()]));
 for(const r of rooms)for(const d of r.doors){const p=doorPoint(r,d);if(d.side==='east')p[0]+=.02;if(d.side==='west')p[0]-=.02;if(d.side==='north')p[1]+=.02;if(d.side==='south')p[1]-=.02;
 for(const other of rooms)if(other.id!==r.id&&pointInPolygon(p,roomPolygon(other))){graph.get(r.id).add(other.id);graph.get(other.id).add(r.id);}}
 return graph;
}
test('review exposes narrow actual master polygon rather than treating its generous bbox as usable',()=>{
 const m=base(),copy=JSON.stringify(m),q=reviewLayout(m),master=q.bedrooms.find(r=>r.id==='l0-master');
 assert.equal(q.longestHallExtentM,10.419);assert.equal(q.hallAreaM2,14.522);assert.equal(master.bedZoneFits,false);assert.equal(master.largestRectangle.w,2.412);
 assert.equal(JSON.stringify(m),copy);assert.match(q.scope,/not.*walking/);
});
test('inside rectangles never bridge an L-shaped void',()=>{
 const r={x:0,y:0,w:5,d:5,footprint:[[0,0],[5,0],[5,2],[2,2],[2,5],[0,5]]};
 const rects=interiorRectangles(r);assert.equal(rects[0].w*rects[0].d,10);assert.ok(rects.every(c=>c.w<=2||c.d<=2));
});
test('splitting one corridor into named pieces does not falsely improve the straight-extent metric',()=>{
 const m=base(),l=m.levels[0];const make=(id,y,d)=>({id,name:id,kind:'hall',x:0,y,w:1.4,d,height:3,locked:false,doors:[],windows:[]});
 l.rooms=[make('a',0,10)];assert.equal(reviewLayout(m).longestHallExtentM,10);
 l.rooms=[make('a',0,5),make('b',5,5)];assert.equal(reviewLayout(m).longestHallExtentM,10);
 l.rooms=[make('a',0,5),make('b',5.001,4.999)];assert.equal(reviewLayout(m).longestHallExtentM,10);
 l.rooms=[make('a',0,4),make('b',6,4)];assert.equal(reviewLayout(m).longestHallExtentM,4);
});
test('measurable alternative reduces both hall extent and hall-plus-reception allocation',()=>{
 const m=base(),a=alt(m),before=a.beforeReview,after=a.review;
 assert.ok(after.longestHallExtentM<5.5);assert.ok(after.longestHallExtentM<before.longestHallExtentM*.55);
 assert.ok(after.hallAreaM2<before.hallAreaM2*.8);assert.ok(after.circulationAndReceptionM2<before.circulationAndReceptionM2*.8);
 assert.ok(after.bedrooms.every(r=>r.bedZoneFits));assert.equal(a.model.levels[0].rooms.find(r=>r.id==='l0-master').footprint,undefined);
 assert.ok(after.envelopeM2>=120&&after.envelopeM2<=160);assert.deepEqual(errors(a.model),[]);
 mkdirSync('test-output/layout-quality',{recursive:true});
 writeFileSync('test-output/layout-quality/comparison.json',JSON.stringify({before,after,sourceTextPreserved:a.model.brief.prompt===text,roomChanges:m.levels[0].rooms.map(r=>({id:r.id,name:r.name,beforeM2:area(r),afterM2:area(a.model.levels[0].rooms.find(n=>n.id===r.id))}))},null,2));
 writeFileSync('test-output/layout-quality/candidate.json',JSON.stringify(a.model,null,2));
 writeFileSync('test-output/layout-quality/candidate.ifc',exportIFC(a.model));
});
test('all 17 spaces, original brief, metadata, plot, features and requirements survive without mutation',()=>{
 const m=base();m.comments.push({id:'note',roomId:'l0-master',text:'Keep this annotation',author:'Owner',at:'2026-09-09',resolved:false});m.levels[0].rooms[0].name='غرفة خاصة';m.levels[0].rooms[0].note='Annotation';
 const snapshot=JSON.stringify(m),a=alt(m).model;
 assert.equal(JSON.stringify(m),snapshot);assert.equal(a.id,m.id);assert.deepEqual(a.brief,m.brief);assert.deepEqual(a.site,m.site);assert.deepEqual(a.requirements,m.requirements);assert.deepEqual(a.comments,m.comments);assert.deepEqual(a.authoring,m.authoring);
 assert.deepEqual(a.levels[0].rooms.map(r=>[r.id,r.kind,r.name,r.note]).sort(),m.levels[0].rooms.map(r=>[r.id,r.kind,r.name,r.note]).sort());
 assert.equal(a.levels[0].rooms.length,17);
});
test('additional locked measured relationships cannot be worsened by the proposed plan',()=>{
 const m=base();m.requirements.push({id:'new-relation',type:'adjacency',value:{type:'near-entry',subjectKind:'bedroom'},label:'اختبار تثبيت علاقة',locked:true,source:'requested'});
 const result=compactCirculationAlternative(m);
 if(result.alternative)checkLocks(m,result.alternative.model);else assert.match(result.reason,/قيود/);
});
test('locked rooms, locked openings and manually changed geometry are never regenerated',()=>{
 for(const change of [m=>m.levels[0].rooms[0].locked=true,m=>m.levels[0].rooms[0].doors[0].locked=true,m=>m.levels[0].rooms[0].windows[0].locked=true,m=>m.levels[0].rooms[0].x+=.1,m=>m.levels[0].rooms[0].doors[0].width=.8]){
 const m=base();change(m);const copy=JSON.stringify(m),result=compactCirculationAlternative(m);assert.equal(result.alternative,null);assert.ok(result.reason);assert.equal(JSON.stringify(m),copy);}
});
test('guest WC and majlis are reachable without any internal route through family rooms',()=>{
 const m=alt(base()).model,g=links(m),seen=new Set(['l0-guest-entry']),todo=[...seen];
 for(let i=0;i<todo.length;i++)for(const id of g.get(todo[i]))if(!seen.has(id)){seen.add(id);todo.push(id);}
 assert.deepEqual([...seen].sort(),['l0-guest-entry','l0-guest-bath','l0-majlis'].sort());
 assert.deepEqual([...g.get('l0-ensuite')],['l0-master']);assert.deepEqual([...g.get('l0-wardrobe')],['l0-master']);
});
test('kitchen has a valid rear exit, and the material/IFC geometry keeps all hosts',()=>{
 const m=alt(base()).model,k=m.levels[0].rooms.find(r=>r.kind==='kitchen');assert.ok(k.doors.some(d=>d.entry&&d.side==='north'));
 const graph=deriveBuildingGraph(m);assert.ok(graph.elements.openings.every(o=>o.hostWallId));
 const scene=createRenderScene(m,'quality-revision');assert.equal(scene.proofs.rooms.length,17);assert.equal(scene.source.modelId,m.id);assert.equal(scene.source.revisionId,'quality-revision');
 assert.ok(scene.objects.length>100);
});
test('rectangular principal bedroom and dining can each contain the disclosed illustrative zone',()=>{
 const m=alt(base()).model,master=m.levels[0].rooms.find(r=>r.id==='l0-master'),dining=m.levels[0].rooms.find(r=>r.kind==='dining');
 assert.ok(master.w-.24>=3&&master.d-.24>=2.8);
 assert.ok((dining.w-.24>=2.8&&dining.d-.24>=2.1)||(dining.d-.24>=2.8&&dining.w-.24>=2.1));
});
test('orientation and supported small-budget matrix have real valid alternatives or explicit refusal',()=>{
 for(const street of ['جنوب','شمال','شرق','غرب'])for(const max of [140,150,160,170,180]){
 const b=understand(text);b.street=street;b.buildingArea={...b.buildingArea,max};if(['شرق','غرب'].includes(street)){b.width=25;b.depth=20;}
 const m=generate(b);
 const result=compactCirculationAlternative(m);assert.ok(result.alternative,result.reason);const a=result.alternative.model;
 assert.deepEqual(errors(a),[],street+max);assert.ok(conceptEnvelopeArea(a)<=max);assert.deepEqual(a.site,m.site);
 }
});
test('unrelated layouts and already improved layouts have no misleading replan option',()=>{
 const villa=generate(understand('فيلا ثلاثة أدوار خمس غرف نوم أرض 20×25'));assert.equal(compactCirculationAlternative(villa).alternative,null);
 assert.equal(compactCirculationAlternative(alt(base()).model).alternative,null);
});
test('acceptance appends a revision; original history and export import remain intact',()=>{
 const m=base(),h=createHistory(m),a=alt(m),next=pushHistory(h,a.model,a.label);
 assert.equal(next.revisions.length,2);assert.deepEqual(next.revisions[0].model,m);assert.equal(h.revisions.length,1);
 const restored=importEnvelope(JSON.stringify(exportEnvelope(next)));assert.equal(current(restored).design.layoutStrategy,'compact-short-circulation-v2');assert.equal(restored.revisions[0].model.design.layoutStrategy,'compact-three-bedroom-v1');
});
