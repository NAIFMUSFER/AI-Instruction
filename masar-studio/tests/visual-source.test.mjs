import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {understand,generate,validate,conceptEnvelopeArea,importEnvelope,current,clone,totals} from '../shared/model.js';
import {renderSourceStatus} from '../src/render-ui.js';
import {createRenderScene} from '../shared/render-scene.js';
const full=readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
const legacy=()=>current(importEnvelope(readFileSync(new URL('./fixtures/legacy-chalet-source.json',import.meta.url),'utf8')));
test('reproduced legacy generic chalet is large and contains an unrequested stair',()=>{
 const m=legacy();
 assert.equal(totals(m).footprint,266);
 assert.equal(m.levels[0].rooms.filter(r=>r.kind==='stairs').length,1);
 assert.equal(m.brief.buildingArea,null);
});
test('full description without its last budget paragraph receives a visible assumption, not a claimed request',()=>{
 const text=full.slice(0,full.lastIndexOf('\n\n')),b=understand(text);
 assert.equal(b.prompt,text);assert.equal(b.sources.buildingArea,'assumed');
 assert.equal(b.buildingArea.source,'assumed');assert.deepEqual([b.buildingArea.min,b.buildingArea.max],[120,160]);
 const m=generate(b);
 assert.ok(conceptEnvelopeArea(m)<=160);assert.deepEqual(validate(m).filter(i=>i.status==='error'),[]);
 assert.equal(m.requirements.find(r=>r.type==='building-area').source,'assumed');
 assert.ok(!m.levels[0].rooms.some(r=>r.kind==='stairs'));
});
test('existing Chalet template also follows the reviewed compact path',()=>{
 const b=understand(legacy().brief.prompt),m=generate(b);
 assert.equal(b.buildingArea.source,'assumed');
 assert.equal(m.design.layoutStrategy,'compact-three-bedroom-v1');
 assert.ok(conceptEnvelopeArea(m)<=160);
 assert.ok(totals(m).outdoorArea>300);
 assert.equal(m.levels[0].rooms.filter(r=>r.kind==='bedroom').length,3);
 assert.deepEqual(validate(m).filter(i=>i.status==='error'),[]);
});
test('explicit request is never replaced by the default interval',()=>{
 const b=understand(full);
 assert.equal(b.buildingArea.source,'requested');
 assert.equal(b.sources.buildingArea,'requested');
 const x=understand('شاليه 20×25 دور واحد 3 غرف نوم مسبح مساحة البناء 130–170 م²');
 assert.deepEqual([x.buildingArea.min,x.buildingArea.max],[130,170]);
});
test('assumption is not applied to another type, floor count, bedroom count or negative pool request',()=>{
 for(const text of ['فيلا 20×25 دور واحد 3 غرف نوم مسبح','شاليه 20×25 دورين 3 غرف نوم مسبح','شاليه 20×25 دور واحد 5 غرف نوم مسبح','شاليه 20×25 دور واحد 3 غرف نوم بدون مسبح','شاليه 12×15 دور واحد 3 غرف نوم مسبح']){
   assert.equal(understand(text).buildingArea,null,text);
 }
});
test('source diagnostics reveal a legacy layout without changing it',()=>{
 const m=legacy(),before=JSON.stringify(m),status=renderSourceStatus(m);
 assert.equal(status.needsRebuild,true);assert.ok(status.warnings.length);
 assert.equal(status.envelope,conceptEnvelopeArea(m));assert.equal(status.unbuilt,450-status.envelope);
 assert.equal(JSON.stringify(m),before);
});
test('new compact model and scene identify the actual same project',()=>{
 const m=generate(understand(full)),before=JSON.stringify(m);
 assert.equal(renderSourceStatus(m).needsRebuild,false);
 const scene=createRenderScene(m,'revision-proof');
 assert.equal(scene.source.modelId,m.id);assert.equal(scene.source.revisionId,'revision-proof');
 assert.equal(scene.proofs.rooms.length,m.levels[0].rooms.length);
 assert.equal(JSON.stringify(m),before);
});
test('a demo is labelled as a demo and never offers automatic migration',()=>{
 const s=renderSourceStatus(legacy(),true);
 assert.equal(s.demo,true);assert.equal(s.needsRebuild,false);
});
test('source diagnostics expose literal kind/bedroom/area mismatches, not presentation changes',()=>{
 const m=legacy();m.brief.prompt=full;m.design.projectType='warehouse';
 const s=renderSourceStatus(m);
 assert.ok(s.warnings.some(w=>w.includes('نوع النموذج')));
 assert.ok(s.warnings.some(w=>w.includes('120–160')));
 m.levels[0].rooms.find(r=>r.kind==='bedroom').kind='storage';
 assert.ok(renderSourceStatus(m).warnings.some(w=>w.includes('عدد غرف النوم')));
});
test('read-only material panel does not offer regeneration',async()=>{
 const html=readFileSync(new URL('../src/render-ui.js',import.meta.url),'utf8');
 assert.match(html,/source\.needsRebuild&&!isReadOnly\(\)/);
});
