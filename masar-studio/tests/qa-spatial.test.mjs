import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {understand,generate,validate,conceptEnvelopeArea,touchesGardenEdge} from '../shared/model.js';
import {deriveBuildingGraph} from '../shared/building.js';
import {createRenderScene} from '../shared/render-scene.js';
const prompt=readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
test('garden relationship stays attached to its textual subject, not a kitchen elsewhere',()=>{
  const b=understand(prompt);assert.ok(b.intents.some(i=>i.type==='garden-edge'&&i.subjectKind==='living'));
  assert.ok(!b.intents.some(i=>i.type==='garden-edge'&&i.subjectKind==='kitchen'));
});
test('detached pool bathroom cannot move the main living room away from its garden facade',()=>{
  const m=generate(understand(prompt));assert.equal(touchesGardenEdge(m,m.levels[0].rooms.find(r=>r.kind==='living')),true);
  assert.ok(!validate(m).some(i=>i.status==='warning'));
  assert.ok(!validate(m).some(i=>i.id==='stairs-design'));
});
test('slab and roof envelopes do not bridge the open yard to a detached service',()=>{
  const m=generate(understand(prompt)),g=deriveBuildingGraph(m);
  assert.equal(g.elements.slabs.length,2);assert.equal(g.elements.roofs.length,2);
  for(const kind of ['slabs','roofs'])assert.ok(g.elements[kind].reduce((a,r)=>a+r.w*r.d,0)<160);
  assert.ok(conceptEnvelopeArea(m)<=160);
});
test('actual Blender scene export accepts the revised customer programme without changing it',()=>{
  const m=generate(understand(prompt)),before=JSON.stringify(m),scene=createRenderScene(m,'customer-review');
  assert.equal(JSON.stringify(m),before);assert.equal(scene.proofs.rooms.length,m.levels[0].rooms.length);
  assert.ok(scene.objects.some(o=>o.category==='roof'));assert.ok(!scene.objects.some(o=>o.category==='stairs'));
});
