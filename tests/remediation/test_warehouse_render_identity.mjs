import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const mod = await import(pathToFileURL(path.join(
  ROOT, 'public/app/render/warehouse-canonical-identity.js')).href+'?t='+Date.now());
let checks = 0;
function ok(name, value) { assert.ok(value, name); checks++; console.log('PASS '+name); }

function fixture() {
  return {
    meta:{type:'warehouse'},
    levels:[{index:0,name:'Ops',template:'ops'}],
    floors:{ops:{rooms:[{
      id:'storage_A', space_id:'space.storage_A', rect:[0,0,30,20],
      racks:[
        {id:'rack-A', source_id:'req-storage-17', kind:'pallet', provenance:{source:'program',source_id:'req-storage-17'}},
        {id:'rack-B', source_id:'plan-option-B', kind:'flow'}
      ],
      docks:[{id:'dock-in-01',source_id:'req-dock-1',edge:'N'}],
      lanes:[{id:'lane-forklift-01',kind:'forklift'}],
      stations:[{id:'station-pack-01',kind:'pack'}]
    }]}}
  };
}

const building = fixture();
const before = JSON.stringify(building);

for (const name of [
  'FURN|F0|storage_A|rack0r0L0',
  'FURN|F0|storage_A|goods0r0L0s1',
  'FURN|F0|storage_A|post0r0p1',
  'FURN|F0|storage_A|beam0r0',
]) {
  const id = mod.canonicalWarehouseIdentityForMesh({name,userData:{}}, building, 'bld_0');
  ok(name+' resolves all rack submeshes to one explicit canonical rack id',
    id && id.target_id==='rack-A' && id.target_kind==='RACK'
    && id.identity_strength==='EXACT_EXPLICIT_ID'
    && id.source_id==='req-storage-17'
    && id.canonical_selector.element_id==='rack-A');
}

const dock = mod.canonicalWarehouseIdentityForMesh(
  {name:'DOOR|F0|storage_A|dock0_0',userData:{}}, building);
ok('dock door resolves to explicit dock record, not the renderer index',
  dock && dock.target_id==='dock-in-01' && dock.target_kind==='DOCK');
const leveler = mod.canonicalWarehouseIdentityForMesh(
  {name:'FLOOR|F0|storage_A|leveler0_0',userData:{}}, building);
ok('dock leveler shares the same canonical dock identity',
  leveler && leveler.target_id==='dock-in-01');

const lane = mod.canonicalWarehouseIdentityForMesh(
  {name:'SAFETY|F0|storage_A|lane0edge',userData:{}}, building);
ok('lane paint/edge resolves to explicit lane identity',
  lane && lane.target_id==='lane-forklift-01' && lane.target_kind==='LANE');
const station = mod.canonicalWarehouseIdentityForMesh(
  {name:'ELEC|F0|storage_A|stscr0_0',userData:{}}, building);
ok('station accessory resolves to explicit station identity',
  station && station.target_id==='station-pack-01' && station.target_kind==='STATION');

const taggedMesh={name:'FURN|F0|storage_A|rack0r0L0',userData:{keep:'yes'}};
const tagged = mod.tagWarehouseRenderedMesh(taggedMesh, building, 'bld_0');
ok('tagger writes presentation metadata while preserving existing mesh userData',
  tagged && taggedMesh.userData.keep==='yes'
  && taggedMesh.userData.acsCanonicalIdentity.target_id==='rack-A');
ok('provenance is preserved from canonical element without inference',
  tagged.provenance && tagged.provenance.source==='program'
  && tagged.provenance.source_id==='req-storage-17');
ok('identity mapping leaves the Canonical ACS Building byte-identical',
  JSON.stringify(building)===before);

const reordered = fixture();
reordered.floors.ops.rooms[0].racks.reverse();
const afterReorder = mod.canonicalWarehouseIdentityForMesh(
  {name:'FURN|F0|storage_A|rack1r0L0',userData:{}}, reordered);
ok('engineering identity survives array reorder when renderer locator changes with it',
  afterReorder && afterReorder.target_id==='rack-A'
  && afterReorder.renderer_locator.array_index===1);

const noId = fixture();
delete noId.floors.ops.rooms[0].racks[0].id;
ok('legacy rack without explicit stable id fails closed',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'FURN|F0|storage_A|rack0r0L0',userData:{}}, noId)===null);

const duplicate = fixture();
duplicate.floors.ops.rooms[0].racks[1].id='rack-A';
ok('duplicate canonical ids fail closed instead of picking one record',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'FURN|F0|storage_A|rack0r0L0',userData:{}}, duplicate)===null);

ok('unknown level fails closed',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'FURN|F9|storage_A|rack0r0L0',userData:{}}, building)===null);
ok('plain point estop is not confused with conveyor lane identity',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'SAFETY|F0|storage_A|estop0',userData:{}}, building)===null);
ok('presentation-only mesh can never gain engineering identity',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'FURN|F0|storage_A|rack0r0L0',userData:{acs_visual_only:true}}, building)===null);
ok('residential/non-warehouse mesh name is outside this contract',
  mod.canonicalWarehouseIdentityForMesh(
    {name:'WALL|F0|majlis|wN0',userData:{}}, building)===null);

const stale={name:'FURN|F0|storage_A|rack0r0L0',userData:{acsCanonicalIdentity:{target_id:'old'}}};
mod.tagWarehouseRenderedMesh(stale,noId,'bld_0');
ok('unresolved model swap clears stale exact mesh identity',
  !Object.prototype.hasOwnProperty.call(stale.userData,'acsCanonicalIdentity'));

const meshes=[
  {name:'FURN|F0|storage_A|rack0r0L0',userData:{}},
  {name:'FURN|F0|storage_A|post0r0p0',userData:{}},
  {name:'FURN|F0|storage_A|rack1r0L0',userData:{}},
  {name:'DOOR|F0|storage_A|dock0_0',userData:{}},
];
const selected=mod.warehouseMeshesForCanonicalId(meshes,'rack-A',building,'bld_0');
ok('reverse highlight returns only submeshes backed by the selected explicit id',
  selected.length===2 && selected.every(m=>/rack0|post0/.test(m.name)));

const batch=mod.tagWarehouseRenderedSubtree(meshes,building,'bld_0');
ok('batch tagger reports exact tagged/unresolved counts without claiming more',
  batch.visited===4 && batch.tagged===4 && batch.unresolved===0);
ok('batch tagger still does not mutate canonical data', JSON.stringify(building)===before);

console.log(`WAREHOUSE RENDER IDENTITY: ${checks} checks passed.`);
