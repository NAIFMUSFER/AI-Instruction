import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const read = p => fs.readFileSync(path.join(ROOT, p), 'utf8');
let checks = 0;
function ok(name, value) { assert.ok(value, name); checks++; console.log('PASS '+name); }

// Baseline controls: the existing product already has the professional workspace and
// reversible view transforms. This slice must bridge them, not replace either one.
const wiring = read('public/app/ui/workspace-ui-wiring.js');
const workspace = read('public/app/generated/workspace-ui.js');
const scene = read('public/app/render/scene.js');
const main = read('public/app/main.js');
ok('existing workspace exposes canonical selection and inspector',
  workspace.includes('select:select') && workspace.includes('wsInspectorModel'));
ok('existing renderer already owns reversible dollhouse/cutaway behavior',
  scene.includes("DOLLHOUSE") && scene.includes("CUTAWAY") && scene.includes('applyVisualMode'));
ok('current viewport wiring does not hand a viewport hit to workspace.select',
  !wiring.includes('.workspace.select(') && !wiring.includes('workspaceViewportSelection'));

let mod;
try {
  mod = await import(pathToFileURL(path.join(ROOT, 'public/app/ui/workspace-viewport-selection.js')).href+'?t='+Date.now());
} catch (error) {
  console.error('PROVEN_GAP: public/app/ui/workspace-viewport-selection.js is absent or not importable:', error.code || error.message);
  process.exitCode = 1;
  process.exit();
}

ok('main entry graph declares both side-effect-free selection logic and runtime wiring',
  main.includes("import './ui/workspace-viewport-selection.js';")
  && main.includes("import './ui/workspace-viewport-selection-runtime.js';"));

const building = {
  meta:{name:'Selection fixture'},
  levels:[
    {index:0,name:'Ground',template:'ground'},
    {index:1,name:'First',template:'upper'}
  ],
  floors:{
    ground:{rooms:[{
      id:'majlis', rect:[0,0,6,5],
      doors:[{id:'door_guest',edge:'N',offset:2,width:1}],
      windows:[{edge:'E',offset:1,width:1.2}],
      objects:[{id:'chair_1',kind:'chair'}]
    }]},
    upper:{rooms:[{id:'bed1',rect:[0,0,4,4],doors:[],windows:[]}]}
  }
};

const wall = mod.canonicalSelectionForMesh({name:'WALL|F0|majlis|wN0',userData:{}}, building, 'bld_0');
ok('derived wall segment resolves honestly to owning canonical space, not an invented wall id',
  wall && wall.target_id==='bld_0.ground.majlis' && wall.target_kind==='SPACE'
  && wall.hit_kind==='WALL' && wall.identity_strength==='OWNER_SPACE');

const door = mod.canonicalSelectionForMesh({name:'DOOR|F0|majlis|0',userData:{}}, building, 'bld_0');
ok('door mesh resolves to explicit canonical door id',
  door && door.target_id==='door_guest' && door.target_kind==='DOOR'
  && door.identity_strength==='EXACT');

const win = mod.canonicalSelectionForMesh({name:'WINDOW|F0|majlis|0',userData:{}}, building, 'bld_0');
ok('window mesh resolves to the exact workspace fallback id when model id is absent',
  win && win.target_id==='bld_0.ground.majlis.window_0' && win.target_kind==='WINDOW'
  && win.identity_strength==='EXACT');

ok('unknown level fails closed instead of guessing a template',
  mod.canonicalSelectionForMesh({name:'WALL|F9|majlis|0',userData:{}}, building, 'bld_0')===null);

const invalidRoomIdentity = {
  levels:[{index:0,template:'ground'}],
  floors:{ground:{rooms:[{id:null,rect:[0,0,2,2],doors:[],windows:[]}]}}
};
ok('room without a valid canonical id fails closed instead of fabricating null identity',
  mod.canonicalSelectionForMesh({name:'WALL|F0|null|0',userData:{}}, invalidRoomIdentity, 'bld_0')===null);

const invalidLevelIdentity = {
  levels:[{template:'ground'}],
  floors:{ground:{rooms:[{id:'majlis',rect:[0,0,2,2],doors:[],windows:[]}]}}
};
ok('level without a canonical integer index fails closed',
  mod.canonicalSelectionForMesh({name:'WALL|ground|majlis|0',userData:{}}, invalidLevelIdentity, 'bld_0')===null);

ok('visual-only mesh is never promoted to engineering selection',
  mod.canonicalSelectionForMesh({name:'VISUAL|ARCHITECTURE|x',userData:{acs_visual_only:true}}, building, 'bld_0')===null);
ok('presentation/site mesh is never promoted to engineering selection',
  mod.canonicalSelectionForMesh({name:'GROUND_PLANE',userData:{presentation_context:true}}, building, 'bld_0')===null);

const tags = [
  {name:'WALL|F0|majlis|wN0',userData:{}},
  {name:'FLOOR|F0|majlis',userData:{}},
  {name:'DOOR|F0|majlis|0',userData:{}},
  {name:'WINDOW|F0|majlis|0',userData:{}},
  {name:'WALL|F1|bed1|wN0',userData:{}}
];
const roomMeshes = mod.meshesForCanonicalSelection(tags, 'bld_0.ground.majlis', building, 'bld_0');
ok('workspace room selection finds only meshes owned by that same canonical room',
  roomMeshes.length===2 && roomMeshes.every(x=>/^(WALL|FLOOR)\|F0\|majlis/.test(x.name)));

const before = JSON.stringify(building);
mod.canonicalSelectionForMesh(tags[0], building, 'bld_0');
mod.meshesForCanonicalSelection(tags, 'bld_0.ground.majlis', building, 'bld_0');
ok('selection mapping is presentation-only and leaves canonical building byte-identical',
  JSON.stringify(building)===before);

const bridgeSource = read('public/app/ui/workspace-viewport-selection.js');
ok('bridge never assigns canonical model or mesh position as an engineering edit',
  !/lastBuilding\s*=|\.position\s*=|\.position\.(set|copy)\s*\(/.test(bridgeSource));
ok('bridge reuses the existing workspace selection authority',
  bridgeSource.includes('.workspace.select('));
ok('bridge does not create a second cutaway/floor-isolation engine',
  !bridgeSource.includes('applyVisualMode(') && !bridgeSource.includes('clippingPlanes=')
  && !bridgeSource.includes('LEVEL_ISOLATION'));

console.log(`WORKSPACE VIEWPORT SELECTION: ${checks} checks passed.`);
