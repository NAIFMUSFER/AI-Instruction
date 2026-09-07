import test from 'node:test';
import assert from 'node:assert/strict';
import { generate,understand,clone,propose,commitPreview,validate,assertModel,area,roomPolygon,pointInPolygon,overlap,checkLocks } from '../shared/model.js';
import { deriveBuildingGraph,exportIFC } from '../shared/building.js';
import { parseIFC } from '../shared/ifc.js';
import { sceneBoxes,planSVG } from '../shared/geometry.js';

export function isolatedRoom(){
 const m=generate(understand('أرض 20×25 دور واحد غرفة نوم واحدة'));
 m.levels=[{id:'test-level',name:'الأرضي',elevation:0,height:3,rooms:[{id:'test-room',name:"مجلس 'نايف' 🏡",kind:'majlis',x:1,y:1,w:8,d:6,height:3,locked:false,note:'',doors:[{id:'entry',side:'south',offset:.5,width:1,entry:true,height:2.2}],windows:[]}]}];
 m.requirements=[];m.site.features=[];return assertModel(m);
}
const room=m=>m.levels[0].rooms[0];
const errors=m=>validate(m).filter(i=>i.status==='error');
for(const [corner,point]of Object.entries({ne:[8.5,6.5],nw:[1.5,6.5],se:[8.5,1.5],sw:[1.5,1.5]}))test('Notch '+corner+' removes exactly the requested physical corner',()=>{
 const m=isolatedRoom(),before=JSON.stringify(m),p=propose(m,{type:'notch',roomId:room(m).id,width:1,depth:1,corner});
 assert.equal(p.blockers.length,0);const n=commitPreview(m,p),r=room(n);assert.equal(area(r),47);assert.equal(pointInPolygon(point,r.footprint),false);assert.equal(pointInPolygon([5,4],r.footprint),true);
 assert.equal(JSON.stringify(m),before);assert.equal(sceneBoxes(n,{levelId:n.levels[0].id}).filter(x=>x.kind==='floor').reduce((s,x)=>s+x.w*x.d,0),47);
});
test('Window IDs cannot collide after removal and later insertion',()=>{
 let m=isolatedRoom();const make=(offset=.25)=>({type:'window',roomId:room(m).id,side:'north',offset,width:1,height:1,sill:1});
 m=commitPreview(m,propose(m,make()));const first=room(m).windows[0].id;
 m=commitPreview(m,propose(m,make(.75)));const second=room(m).windows[1].id;
 m=commitPreview(m,propose(m,{type:'remove-window',roomId:room(m).id,windowId:first}));
 m=commitPreview(m,propose(m,make()));assert.equal(new Set(room(m).windows.map(w=>w.id)).size,2);assert.ok(room(m).windows.some(w=>w.id===second));assert.ok(room(m).windows.every(w=>w.id!==first));
});
test('Unknown window target and unknown declared type both reject without mutation',()=>{
 const m=isolatedRoom(),before=JSON.stringify(m),base={type:'window',roomId:room(m).id,side:'north',width:1};
 assert.throws(()=>propose(m,{...base,windowId:'unknown'}),/غير موجودة/);assert.throws(()=>propose(m,{...base,typeId:'unknown'}),/غير موجود/);assert.equal(JSON.stringify(m),before);
});
test('Locked individual windows prevent edits, deletion and host movement',()=>{
 let m=isolatedRoom();m=commitPreview(m,propose(m,{type:'window',roomId:room(m).id,side:'north',width:1}));const w=room(m).windows[0];w.locked=true;
 for(const c of [{type:'window',windowId:w.id,side:'north',width:2},{type:'remove-window',windowId:w.id},{type:'move',x:2}])assert.throws(()=>propose(m,{...c,roomId:room(m).id}),/مثبتة/);
 assert.doesNotThrow(()=>propose(m,{type:'rename',roomId:room(m).id,name:'اسم جديد'}));
});
test('Window overlap and door/window intersection prevent commit',()=>{
 const m=isolatedRoom(),a=propose(m,{type:'window',roomId:room(m).id,side:'south',width:1,height:1,sill:.9});
 assert.ok(a.blockers.some(x=>x.id.startsWith('opening-overlap')));assert.throws(()=>commitPreview(m,a));
 const b=commitPreview(m,propose(m,{type:'window',roomId:room(m).id,side:'north',width:1}));
 assert.ok(propose(b,{type:'window',roomId:room(m).id,side:'north',width:1}).blockers.some(x=>x.id.startsWith('opening-overlap')));
});
test('Full aperture width, not merely its centre, must lie on an actual polygon edge',()=>{
 const m=isolatedRoom(),n=commitPreview(m,propose(m,{type:'notch',roomId:room(m).id,width:2,depth:2,corner:'ne'}));
 const p=propose(n,{type:'window',roomId:room(m).id,side:'north',offset:.70,width:1.8});
 assert.ok(p.blockers.some(x=>x.id.startsWith('window-boundary')));assert.throws(()=>commitPreview(n,p));
});
test('Hosted aperture crossing an atomized T-junction is refused for commit and IFC',()=>{
 const m=isolatedRoom();m.levels[0].rooms.push({id:'annex',name:'ملحق',kind:'service',x:4,y:7,w:5,d:3,height:3,locked:false,note:'',doors:[],windows:[]});
 const p=propose(m,{type:'window',roomId:room(m).id,side:'north',offset:.375,width:1});
 assert.ok(p.blockers.some(x=>x.id.startsWith('host-span')));assert.throws(()=>exportIFC(p.candidate),/مضيف/);
});
test('Wall types cannot silently replace empty/invalid authoring definitions with defaults',()=>{
 for(const mutate of [m=>m.authoring.wallTypes=[],m=>m.authoring.windowTypes=[],m=>m.authoring.wallTypes[0].totalThickness=.6,m=>m.authoring.wallTypes[0].layers[1].id=m.authoring.wallTypes[0].layers[0].id,m=>m.authoring.defaults.externalWallTypeId=m.authoring.defaults.internalWallTypeId]){const m=isolatedRoom();mutate(m);assert.throws(()=>assertModel(m));}
});
test('Imported metadata cannot promote unimplemented disciplines to approved/checked',()=>{
 for(const key of ['structure','mep','fire','accessibility','regulatory']){const m=isolatedRoom();m.authoring.disciplineStatus[key]='approved';assert.throws(()=>assertModel(m));}
});
test('Room heights exceeding the level are blocked instead of hidden by rendering',()=>{
 const m=isolatedRoom(),p=propose(m,{type:'resize',roomId:room(m).id,height:4});assert.ok(p.blockers.some(x=>x.id==='height-test-room'));assert.throws(()=>commitPreview(m,p));
});
test('Concave cavity and adjacent boundary are not false positive overlaps',()=>{
 const a={x:0,y:0,w:6,d:6,footprint:[[0,0],[6,0],[6,1],[1,1],[1,5],[6,5],[6,6],[0,6]]};
 const b={x:2,y:2,w:2,d:2};assert.equal(overlap(a,b),false);assert.equal(overlap(b,a),false);
 assert.equal(overlap(a,{x:0,y:2,w:2,d:2}),true);assert.equal(overlap(a,{x:1,y:2,w:1,d:1}),false);
 assert.equal(overlap(a,a),true);
});
test('Strict point containment excludes edges and polygon self-touching is rejected',()=>{
 assert.equal(pointInPolygon([0,1],[[0,0],[2,0],[2,2],[0,2]],false),false);
 const m=isolatedRoom(),r=room(m);r.x=0;r.y=0;r.w=6;r.d=6;r.footprint=[[0,0],[6,0],[6,6],[3,6],[3,3],[1,3],[1,6],[0,6],[0,3],[3,3],[3,1],[0,1]];
 assert.throws(()=>assertModel(m),/بسيط/);
});
test('IFC round-trip preserves zero window sill, explicit door height, labels and support counts',()=>{
 let m=isolatedRoom();m=commitPreview(m,propose(m,{type:'window',roomId:room(m).id,side:'north',width:1.3,height:1,sill:0}));
 const n=parseIFC(exportIFC(m));assert.equal(room(n).windows[0].sill,0);assert.equal(room(n).doors[0].height,2.2);assert.equal(room(n).name,room(m).name);assert.equal(area(room(n)),area(room(m)));assert.equal(errors(n).length,0);
});
test('IFC spaces use aggregation, hosted void cuts exceed wall depth, STEP labels escaped',()=>{
 const m=isolatedRoom(),text=exportIFC(m);assert.match(text,/\\X2\\/);assert.ok(!text.includes(room(m).name));assert.match(text,/IFCRELAGGREGATES/);assert.doesNotThrow(()=>parseIFC(text));
 const g=deriveBuildingGraph(m);assert.equal(g.counts.spaces,1);
});
for(const [name,transform] of [
 ['truncation',s=>s.slice(0,-30)],['wrong schema',s=>s.replace("'IFC4'","'IFC2X3'")],
 ['duplicate record',s=>s.replace('END-ISO-10303-21;',"#1=IFCCARTESIANPOINT((0.,0.,0.));END-ISO-10303-21;")],
 ['unsupported unit',s=>s.replace('.LENGTHUNIT.,$,.METRE.','.LENGTHUNIT.,$,.FOOT.')],
 ['tilted extrusion',s=>s.replaceAll('IFCDIRECTION((0.,0.,1.))','IFCDIRECTION((0.,1.,0.))')],
 ['rotated room placement',s=>s.replace('IFCAXIS2PLACEMENT3D(#1,$,$)','IFCAXIS2PLACEMENT3D(#1,$,#999999)')]
])test('IFC rejects '+name+' without returning invented geometry',()=>{assert.throws(()=>parseIFC(transform(exportIFC(isolatedRoom()))),/IFC/);});
test('Presentation of project-level metadata diffs never emits NaN geometry',()=>{
 const m=isolatedRoom();assert.ok(!planSVG(m,m.levels[0].id,{previewChanges:[{id:'project:authoring',before:m.authoring}]}).includes('NaN'));
});
test('Retail Arabic noun and office counts below level count preserve the brief',()=>{
 assert.equal(understand('تجزئة أرض 25×30 ثلاثة أدوار').projectType,'retail');
 const b=understand('مكاتب أرض 25×30 ثلاثة أدوار 1 مكتب'),m=generate(b);assert.equal(m.levels.flatMap(l=>l.rooms).filter(r=>r.kind==='office').length,1);
});
test('STEP literal backslashes and supplementary Unicode do not become escape directives',()=>{
 const m=isolatedRoom();room(m).name=String.raw`C:\models\X2\1234\X0\ بيت 🏡`;const text=exportIFC(m);assert.match(text,/\\X4\\0001F3E1\\X0\\/);assert.equal(room(parseIFC(text)).name,room(m).name);
});
test('CSV exported user strings cannot start executable spreadsheet formulas',async()=>{
 const {csvCell}=await import('../shared/building.js');for(const value of ['=1+1','+SUM(1,2)','-cmd','@something','\t=HYPERLINK("test")'])assert.equal(csvCell(value).slice(0,2),'"\'');
 assert.equal(csvCell(-1),'"-1"');assert.equal(csvCell('مجلس نايف'),'"مجلس نايف"');
});
test('Editing a door preserves other openings, explicit height, and stable IDs',()=>{
 let m=isolatedRoom();const original=clone(room(m).doors[0]);m=commitPreview(m,propose(m,{type:'door',roomId:room(m).id,create:true,side:'east',width:1,height:2.3,offset:.5,entry:false}));const second=clone(room(m).doors[1]);assert.equal(room(m).doors.length,2);
 m=commitPreview(m,propose(m,{type:'door',roomId:room(m).id,doorId:original.id,side:'south',width:1.2}));assert.deepEqual(room(m).doors[1],second);assert.equal(room(m).doors[0].height,2.2);assert.equal(room(m).doors[0].entry,true);
 m=commitPreview(m,propose(m,{type:'remove-door',roomId:room(m).id,doorId:second.id}));assert.equal(room(m).doors.length,1);assert.equal(room(m).doors[0].id,original.id);
 assert.throws(()=>propose(m,{type:'door',roomId:room(m).id,doorId:'missing',side:'north'}),/غير موجود/);
});
test('Individually locked door rejects direct edit, deletion and host movement',()=>{
 const m=isolatedRoom();room(m).doors[0].locked=true;for(const c of [{type:'door',doorId:'entry',side:'north'},{type:'remove-door',doorId:'entry'},{type:'move',x:2}])assert.throws(()=>propose(m,{...c,roomId:room(m).id}),/مثبت/);
});
