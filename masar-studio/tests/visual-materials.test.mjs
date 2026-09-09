import test from 'node:test';
import assert from 'node:assert/strict';
import {generate,understand} from '../shared/model.js';
import {createRenderScene} from '../shared/render-scene.js';
test('presentation contract exposes physical glass and water without changing canonical geometry',()=>{
 const model=generate(understand('شاليه دور واحد على أرض 20×25 مع ثلاث غرف نوم ومسبح'));
 const before=JSON.stringify(model); const scene=createRenderScene(model,'visual-quality-test',{finish:'warm',furniture:true});
 assert.equal(JSON.stringify(model),before);
 assert.ok(scene.materials.glass.transmission>=.5); assert.equal(scene.materials.glass.ior,1.45);
 assert.equal(scene.materials.water.ior,1.333); assert.equal(scene.materials.water.clearcoat,1);
 assert.ok(scene.objects.length>0);
});
