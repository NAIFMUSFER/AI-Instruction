import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const mod = await import(pathToFileURL(path.join(
  ROOT, 'public/app/ui/workspace-viewport-selection.js')).href+'?t='+Date.now());
let checks = 0;
function ok(name, value) { assert.ok(value, name); checks++; console.log('PASS '+name); }

function fixture() {
  return {
    meta:{type:'warehouse'},
    levels:[{index:0,name:'Ops',template:'ops'}],
    floors:{ops:{rooms:[{
      id:'storage_A', space_id:'space.storage_A', rect:[0,0,30,20],
      doors:[{id:'ped-door-01'}], windows:[],
      racks:[
        {id:'rack-A', source_id:'req-storage-17', provenance:{source:'program',source_id:'req-storage-17'}},
        {id:'rack-B'}
      ],
      docks:[{id:'dock-in-01',source_id:'req-dock-1',edge:'N'}],
      lanes:[{id:'lane-forklift-01',kind:'forklift'}],
      stations:[{id:'station-pack-01',kind:'pack'}]
    }]}}
  };
}

const building = fixture();
const before = JSON.stringify(building);

const rack = mod.canonicalSelectionForMesh(
  {name:'FURN|F0|storage_A|rack0r0L0',userData:{}}, building, 'bld_0');
ok('rack submesh selects explicit canonical rack identity even from FURN layer',
  rack && rack.target_id==='rack-A' && rack.target_kind==='RACK'
  && rack.identity_strength==='EXACT_EXPLICIT_ID');
ok('exact warehouse selection carries canonical selector and existing provenance only',
  rack.canonical_selector && rack.canonical_selector.element_id==='rack-A'
  && rack.source_id==='req-storage-17'
  && rack.provenance && rack.provenance.source==='program');

const dock = mod.canonicalSelectionForMesh(
  {name:'DOOR|F0|storage_A|dock0_0',userData:{}}, building, 'bld_0');
ok('dock door resolves to dock identity before generic residential opening logic',
  dock && dock.target_id==='dock-in-01' && dock.target_kind==='DOCK'
  && dock.identity_strength==='EXACT_EXPLICIT_ID');

const lane = mod.canonicalSelectionForMesh(
  {name:'SAFETY|F0|storage_A|lane0edge',userData:{}}, building, 'bld_0');
ok('lane paint resolves to explicit lane identity even from SAFETY layer',
  lane && lane.target_id==='lane-forklift-01' && lane.target_kind==='LANE');

const station = mod.canonicalSelectionForMesh(
  {name:'ELEC|F0|storage_A|stscr0_0',userData:{}}, building, 'bld_0');
ok('station accessory resolves to explicit station identity even from ELEC layer',
  station && station.target_id==='station-pack-01' && station.target_kind==='STATION');

const rackMeshes = [
  {name:'FURN|F0|storage_A|rack0r0L0',userData:{}},
  {name:'FURN|F0|storage_A|post0r0p0',userData:{}},
  {name:'FURN|F0|storage_A|rack1r0L0',userData:{}},
  {name:'DOOR|F0|storage_A|dock0_0',userData:{}},
];
const exactHighlights = mod.meshesForCanonicalSelection(rackMeshes, 'rack-A', building, 'bld_0');
ok('reverse highlight selects only meshes backed by the same explicit rack id',
  exactHighlights.length===2 && exactHighlights.every(m=>/rack0|post0/.test(m.name)));

const noId = fixture();
delete noId.floors.ops.rooms[0].racks[0].id;
const fallback = mod.canonicalSelectionForMesh(
  {name:'FURN|F0|storage_A|rack0r0L0',userData:{}}, noId, 'bld_0');
ok('legacy rack without stable id falls back to owner space instead of renderer index identity',
  fallback && fallback.target_id==='bld_0.ops.storage_A'
  && fallback.target_kind==='SPACE' && fallback.identity_strength==='OWNER_SPACE');

const duplicate = fixture();
duplicate.floors.ops.rooms[0].racks[1].id='rack-A';
const duplicateFallback = mod.canonicalSelectionForMesh(
  {name:'FURN|F0|storage_A|rack0r0L0',userData:{}}, duplicate, 'bld_0');
ok('duplicate nested ids fail exact selection and safely degrade to owner space',
  duplicateFallback && duplicateFallback.target_id==='bld_0.ops.storage_A'
  && duplicateFallback.identity_strength==='OWNER_SPACE');

const reordered = fixture();
reordered.floors.ops.rooms[0].racks.reverse();
const afterReorder = mod.canonicalSelectionForMesh(
  {name:'FURN|F0|storage_A|rack1r0L0',userData:{}}, reordered, 'bld_0');
ok('explicit engineering identity survives array reorder when renderer locator moves with it',
  afterReorder && afterReorder.target_id==='rack-A'
  && afterReorder.identity_strength==='EXACT_EXPLICIT_ID');

ok('plain point estop is not promoted to lane identity or owner-space warehouse selection',
  mod.canonicalSelectionForMesh(
    {name:'SAFETY|F0|storage_A|estop0',userData:{}}, building, 'bld_0')===null);
ok('presentation-only warehouse mesh still fails closed',
  mod.canonicalSelectionForMesh(
    {name:'FURN|F0|storage_A|rack0r0L0',userData:{acs_visual_only:true}}, building, 'bld_0')===null);
ok('warehouse viewport mapping leaves canonical building byte-identical',
  JSON.stringify(building)===before);

console.log(`WORKSPACE WAREHOUSE EXACT SELECTION: ${checks} checks passed.`);
