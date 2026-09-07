/** Reproducible IFC interoperability fixtures; no private user project or API call. */
import { mkdir,writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { generate,understand,assertModel,propose,commitPreview,area,clone } from '../shared/model.js';
import { deriveBuildingGraph,exportIFC,ifcGuid } from '../shared/building.js';
import { parseIFC } from '../shared/ifc.js';
const out=path.resolve(process.argv[2]||'test-output/ifc');await mkdir(out,{recursive:true});
const models=[['villa',generate(understand('فيلا أرض 20×25 ثلاثة أدوار خمس غرف نوم'))],['eight-storeys',generate(understand('فيلا أرض 30×35 ثمانية أدوار 16 غرفة نوم'))]];
for(const kind of ['شاليه','مكاتب','مستودع','تجزئة'])models.push([`kind-${models.length}`,generate(understand(`${kind} أرض 25×30 ثلاثة أدوار`))]);
function roomFixture(){const m=generate(understand('أرض 20×25 دور واحد غرفة نوم واحدة'));m.id='interop-room';m.title="مشروع 'نايف' 🏡";m.levels=[{id:'interop-level',name:'الأرضي',elevation:0,height:3,rooms:[{id:'interop-room-1',name:"مجلس 'نايف' 🏡",kind:'majlis',x:1,y:1,w:8,d:6,height:3,locked:false,note:'',doors:[{id:'entry',side:'south',offset:.5,width:1,entry:true,height:2.2}],windows:[]}]}];m.requirements=[];m.site.features=[];return assertModel(m);}
for(const corner of ['ne','nw','se','sw']){let m=roomFixture();m=commitPreview(m,propose(m,{type:'notch',roomId:'interop-room-1',width:1,depth:1,corner}));models.push(['notch-'+corner,m]);}
let m=roomFixture();m=commitPreview(m,propose(m,{type:'window',roomId:'interop-room-1',side:'north',width:1.3,height:1,sill:0}));m=commitPreview(m,propose(m,{type:'window',roomId:'interop-room-1',side:'east',width:1,height:1.2,sill:.9}));models.push(['hosted-windows',m]);
const thick=clone(m);thick.id='thick';thick.authoring.wallTypes[0].layers[1].thickness=.4;thick.authoring.wallTypes[0].totalThickness=.44;models.push(['thick-wall',assertModel(thick)]);
const fixtures=[];
for(const [name,model] of models){
 const before=JSON.stringify(model), graph=deriveBuildingGraph(model), text=exportIFC(model), imported=parseIFC(text);
 assert.equal(JSON.stringify(model),before);assert.equal(imported.levels.length,model.levels.length);
 assert.equal(imported.levels.flatMap(l=>l.rooms).length,graph.counts.spaces);
 for(const s of graph.elements.spaces){const found=imported.levels.flatMap(l=>l.rooms).find(r=>r.id===s.id);assert.ok(found);assert.equal(found.name,s.name);assert.ok(Math.abs(area(found)-s.area)<.005);}
 const expected={name,units:'m',title:model.title,counts:graph.counts,
  spaces:graph.elements.spaces.map(s=>({guid:ifcGuid('space:'+s.id),name:s.name,volume:s.area*s.h,z:s.z,height:s.h})),
  walls:graph.elements.walls.map(w=>({...w,guid:ifcGuid(w.id),openings:graph.elements.openings.filter(o=>o.hostWallId===w.id)}))};
 await writeFile(path.join(out,name+'.ifc'),text);await writeFile(path.join(out,name+'.json'),JSON.stringify(expected,null,2));fixtures.push(name);
}
await writeFile(path.join(out,'fixtures.json'),JSON.stringify(fixtures));console.log(JSON.stringify({fixtures:fixtures.length,sourceUnchanged:true,ownSubsetRoundTrip:true}));
