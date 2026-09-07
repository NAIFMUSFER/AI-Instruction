import test from 'node:test';
import assert from 'node:assert/strict';
import { understand, generate, clone, propose, commitPreview } from '../shared/model.js';
import { deriveWalls, deriveOpenings, deriveBuildingGraph, elementSchedule, elementScheduleCSV, requirementMatrix, requirementMatrixCSV, evaluateRulePack, exportIFC, ifcGuid, projectReadiness } from '../shared/building.js';

const fixture=()=>generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم الشارع جنوب مع مصعد ومسبح، المجلس قرب المدخل والمعيشة على الحديقة'));

test('derived building graph has spaces, atomized walls, hosted doors, slabs and roof',()=>{
  const m=fixture(), g=deriveBuildingGraph(m);
  assert.equal(g.counts.spaces,m.levels.reduce((n,l)=>n+l.rooms.length,0));
  assert.equal(g.counts.openings,m.levels.reduce((n,l)=>n+l.rooms.reduce((x,r)=>x+r.doors.length+(r.windows||[]).length,0),0));
  assert.equal(g.counts.slabs,m.levels.length);
  assert.equal(g.counts.roofs,1);
  assert.ok(g.counts.walls>g.counts.spaces);
  assert.ok(g.elements.walls.some(w=>w.external));
  assert.ok(g.elements.walls.some(w=>!w.external));
  assert.ok(g.elements.openings.every(o=>o.hostWallId));
});

test('derived element IDs are stable for an unchanged model and change with affected geometry',()=>{
  const m=fixture(), before=deriveWalls(m).map(w=>w.id);
  assert.deepEqual(deriveWalls(clone(m)).map(w=>w.id),before);
  const r=m.levels[0].rooms.find(r=>r.kind==='majlis');
  const p=propose(m,{type:'rename',roomId:r.id,name:'مجلس رسمي'}), renamed=commitPreview(m,p);
  assert.deepEqual(deriveWalls(renamed).map(w=>w.id),before,'renaming must not mutate derived wall geometry IDs');
});

test('door derivation keeps canonical door identity and host relationship',()=>{
  const m=fixture(), doors=deriveOpenings(m).filter(o=>o.type==='door'), canonical=m.levels.flatMap(l=>l.rooms).flatMap(r=>r.doors.map(d=>d.id)).sort();
  assert.deepEqual(doors.map(d=>d.id).sort(),canonical);
  assert.ok(doors.some(d=>d.entry));
  assert.ok(doors.filter(d=>d.entry).every(d=>d.hostWallId));
});

test('element and requirement schedules are deterministic and safe CSV',()=>{
  const m=fixture(), elements=elementSchedule(m), reqs=requirementMatrix(m);
  assert.ok(elements.some(r=>r.category==='Wall'));
  assert.ok(elements.some(r=>r.category==='Door'));
  assert.ok(elements.some(r=>r.category==='Slab'));
  assert.ok(reqs.some(r=>r.measurable));
  const ecsv=elementScheduleCSV(m), rcsv=requirementMatrixCSV(m);
  assert.ok(ecsv.startsWith('\uFEFF'));
  assert.match(ecsv,/"Wall"/);
  assert.match(rcsv,/"Measurable"/);
  assert.ok(!ecsv.includes('undefined'));
});

test('concept quality rule pack is explicitly non-compliance and does not hide unchecked engineering',()=>{
  const m=fixture(), result=evaluateRulePack(m);
  assert.equal(result.pack.compliance,false);
  assert.equal(result.pack.authority,'product-heuristic');
  assert.equal(result.summary.fail,0);
  assert.ok(result.summary.unchecked>0);
  assert.match(result.pack.disclaimer,/ليست/);
  const ready=projectReadiness(m);
  assert.equal(ready.deliveryReady,true);
  assert.equal(ready.complianceReady,false);
  assert.ok(ready.validation.unchecked>0);
});

test('quality rule review is surfaced without becoming a blocker or code violation',()=>{
  const m=fixture(), door=m.levels[0].rooms.find(r=>r.kind==='bath').doors[0];
  door.width=.6;
  const result=evaluateRulePack(m);
  const review=result.results.find(r=>r.ruleId==='door-concept-width'&&r.targets[0]===door.id);
  assert.equal(review.status,'review');
  assert.match(review.message,/مفاهيمي/);
  assert.equal(result.summary.fail,0);
});

test('IFC GUIDs are valid-length deterministic compressed identifiers',()=>{
  const a=ifcGuid('abc'), b=ifcGuid('abc'), c=ifcGuid('abd');
  assert.equal(a,b); assert.notEqual(a,c); assert.match(a,/^[0-3][0-9A-Za-z_$]{21}$/);
});

test('IFC4 coordination export contains project hierarchy and conceptual spaces/walls/slabs/doors with valid references',()=>{
  const m=fixture(), text=exportIFC(m);
  assert.match(text,/^ISO-10303-21;/);
  assert.match(text,/FILE_SCHEMA\(\('IFC4'\)\)/);
  assert.match(text,/IFCPROJECT\(/);
  assert.match(text,/IFCBUILDINGSTOREY\(/);
  assert.match(text,/IFCSPACE\(/);
  assert.match(text,/IFCWALL\(/);
  assert.match(text,/IFCSLAB\(/);
  assert.match(text,/IFCDOOR\(/);
  assert.match(text,/IFCWINDOW\(/);
  assert.match(text,/IFCRELVOIDSELEMENT\(/);
  assert.match(text,/IFCRELFILLSELEMENT\(/);
  assert.match(text,/NOT FOR CONSTRUCTION/);
  assert.ok(!/\b(?:NaN|undefined|Infinity)\b/.test(text));
  const definitions=[...text.matchAll(/^#(\d+)=/gm)].map(m=>Number(m[1]));
  assert.deepEqual(definitions,[...Array(definitions.length)].map((_,i)=>i+1));
  const max=definitions.at(-1);
  for(const ref of text.matchAll(/#(\d+)/g)) assert.ok(Number(ref[1])<=max,`dangling IFC reference #${ref[1]}`);
  assert.match(text,/END-ISO-10303-21;\s*$/);
});
