'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'public/app/ui/residential-quality.js'), 'utf8');
let passed = 0;
function chk(name, value) {
  assert.ok(value, name); passed++; console.log('PASS ' + name);
}

async function flush() {
  await Promise.resolve(); await Promise.resolve(); await new Promise(r => setTimeout(r, 0));
}

(async () => {
  let current = null;
  let pbrApply = 0, detailApply = 0, ensure = 0, camera = null;
  let pbrRestore = 0, adRestore = 0;
  const pbrCalls = [], adCalls = [];
  const generatedVilla = {meta:{type:'villa'},site:{w:20,d:25},levels:[],floors:{}};

  const ACS = {
    setModel(building) { current = building; return 'SET_OK'; },
    exportModel() { return current; },
    pbr: { config(...args) {
      pbrCalls.push(args);
      return {valid:true, config:{writes_to_model:false}};
    }},
    pbrCaps() { return {webgl2:true}; },
    pbrBounds() { return {cx:0,cy:1,cz:0,radius:10,min_y:0}; },
    pbrApply() { pbrApply++; return {applied:true}; },
    pbrCameraPreset(name) { camera = name; return {applied:true}; },
    pbrRestore() { pbrRestore++; return {restored:true}; },
    adRestore() { adRestore++; return true; },
    async ensureLayer(ns) {
      ensure++;
      assert.equal(ns, 'archdetail');
      ACS.archdetail = {config(...args) {
        adCalls.push(args);
        return {valid:true,config:{writes_to_model:false,detail:{effective:'DETAIL_HIGH'}}};
      }};
      ACS.adModelSummary = () => ({exterior_walls:4,windows:6});
      ACS.adApply = () => { detailApply++; return {applied:true}; };
      return true;
    },
  };

  const genButton = {onclick: async function () { current = generatedVilla; }};
  const context = {
    window:{ACS,innerWidth:1280},
    document:{getElementById:id=>id==='genLLM'?genButton:null},
    requestAnimationFrame:fn=>fn(),
    Promise, Set, String, Object, Number, Array, Math, console,
  };
  vm.runInNewContext(SRC, context, {filename:'residential-quality.js'});

  chk('public setModel keeps its synchronous return contract',
      context.window.ACS.setModel({meta:{type:'villa'}}) === 'SET_OK');
  await flush();
  chk('villa automatically receives the shipped PBR presentation', pbrApply === 1);
  chk('desktop residential quality asks for HIGH PBR quality', pbrCalls[0][0] === 'HIGH');
  chk('PBR uses the declared realistic/noon/sky path',
      pbrCalls[0][1] === 'CLEAR_NOON' && pbrCalls[0][2] === 'REALISTIC' && pbrCalls[0][3] === 'SKY');
  chk('residential presentation uses the hero exterior camera', camera === 'EXTERIOR_HERO');
  chk('architectural detail is loaded through the existing lazy owner', ensure === 1);
  chk('architectural detail is applied after PBR', detailApply === 1);
  chk('detail request is HIGH + REALISTIC without inventing user facade intent',
      adCalls[0][0] === 'DETAIL_HIGH' && adCalls[0][1] === 'REALISTIC'
      && Array.isArray(adCalls[0][8]) && adCalls[0][8].length === 0);

  const beforeWarehousePbr = pbrApply, beforeWarehouseEnsure = ensure;
  context.window.ACS.setModel({meta:{type:'warehouse'}});
  await flush();
  chk('warehouse never receives residential PBR automatically', pbrApply === beforeWarehousePbr);
  chk('warehouse never loads residential architectural detail automatically', ensure === beforeWarehouseEnsure);
  chk('leaving residential mode restores only the presentation that this policy owned',
      pbrRestore >= 1 && adRestore >= 1);

  context.window.innerWidth = 390;
  context.window.ACS.setModel({meta:{type:'apartment'}});
  await flush();
  chk('phone width alone no longer downgrades a capable/unknown phone to MEDIUM',
      pbrCalls[pbrCalls.length - 1][0] === 'HIGH');
  chk('phone width alone does not force architectural-detail fallback',
      adCalls[adCalls.length - 1][7] === false);

  const pbrBeforeGenerated = pbrApply;
  current = {meta:{type:'warehouse'}};
  await genButton.onclick();
  await flush();
  chk('server-generation path is observed even though it uses module-local setModel',
      pbrApply === pbrBeforeGenerated + 1);
  chk('the enhancer never mutates the generated canonical object',
      generatedVilla.meta.type === 'villa' && generatedVilla.site.w === 20);
  chk('diagnostic state reports presentation only after a residential model',
      context.window.ACS.residentialQuality.state().applied === true);
  chk('classifier is narrow: office is not silently treated as residential',
      context.window.ACS.residentialQuality.isResidential({meta:{type:'office'}}) === false);

  const good = {meta:{type:'villa'},site:{w:20,d:25},levels:[{index:0,template:'g'}],
    floors:{g:{rooms:[{id:'living',rect:[2,2,6,5]},{id:'bed',rect:[8,2,4,4]}]}}};
  const goodAudit = context.window.ACS.residentialQuality.audit(good);
  chk('valid residential geometry is eligible for engineer approval',
      goodAudit.applicable === true && goodAudit.block_approval === false && goodAudit.score >= 70);

  const bad = {meta:{type:'villa'},site:{w:20,d:25},levels:[{index:0,template:'g'}],
    floors:{g:{rooms:[{id:'outside',rect:[19,1,5,4]},{id:'tiny',rect:[1,1,.4,.4],acs_unresolved:true}]}}};
  const badAudit = context.window.ACS.residentialQuality.audit(bad);
  chk('out-of-site/unresolved residential geometry blocks local approval',
      badAudit.block_approval === true && badAudit.critical >= 2);
  chk('audit is diagnostic only and does not mutate the model', bad.floors.g.rooms[0].rect[0] === 19);

  console.log(`RESIDENTIAL PRESENTATION: ${passed} passed, 0 failed`);
})().catch(err => { console.error(err); process.exitCode = 1; });
