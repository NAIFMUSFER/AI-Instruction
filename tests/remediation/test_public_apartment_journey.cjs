'use strict';
// Acceptance for the actual public guest entry. The browser exercises controls;
// read-only observations of exported rooms and rendered meshes tie each still to its model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
const PW = require('../../tools/pw_chromium.js');
const {analysePageViewport} = require('../deploy/lib_viewport_pixels.js');

const root = path.resolve(__dirname, '../..');
const pub = path.join(root, 'public');
const out = path.resolve(process.env.ACS_APARTMENT_EVIDENCE || 'logs/public-apartment');
const live = process.env.ACS_APARTMENT_LIVE === '1';
const origin = live ? 'https://sprightly-selkie-d906c3.netlify.app' : 'https://acs-guest.test';
const brief = fs.readFileSync(path.join(root, 'tests/fixtures/briefs/riyadh-apartment-ar.txt'), 'utf8');
const csp = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(root, 'netlify.toml'), 'utf8'))[1];
const sha256 = body => crypto.createHash('sha256').update(body).digest('hex');
const near = (a,b) => Math.abs(a-b) <= .01;

function doorExit(rect, door){
  const [x,z,w,d] = rect;
  switch(door.edge){
    case 'N': return [x+door.offset,z-.02];
    case 'S': return [x+door.offset,z+d+.02];
    case 'W': return [x-.02,z+door.offset];
    case 'E': return [x+w+.02,z+door.offset];
    default: throw Error('Missing door wall');
  }
}
function contains([x,z,w,d],[u,v]){
  return u>=x && u<=x+w && v>=z && v<=z+d;
}
function inspectApartment(model){
  const occupied = model.levels.filter(l => l.kind!=='roof');
  assert.deepEqual(occupied.map(l=>l.elevation), [0,3.4,6.8], 'three physical floors at requested elevations');
  assert.deepEqual([model.site.w,model.site.d], [20,25], 'building width and depth must follow the brief');
  const levelData = occupied.map(level=>{
    const rooms = model.floors[level.template].rooms;
    const span = [Infinity,Infinity,-Infinity,-Infinity];
    for(const room of rooms){
      const [x,z,w,d] = room.rect;
      assert.ok(w>0 && d>0 && room.rect.every(Number.isFinite));
      assert.ok(x>=-.01 && z>=-.01 && x+w<=20.01 && z+d<=25.01, 'room outside declared footprint: '+room.id);
      span[0]=Math.min(span[0],x);span[1]=Math.min(span[1],z);
      span[2]=Math.max(span[2],x+w);span[3]=Math.max(span[3],z+d);
      if(level.index>0){
        for(const door of room.doors||[]){
          const exit=doorExit(room.rect,door);
          assert.ok(rooms.some(other=>other!==room && contains(other.rect,exit)),
            'upper door opens into unsupported air: '+level.index+'/'+room.id);
        }
      }
    }
    assert.ok(span.every((v,i)=>near(v,[.09,.09,19.91,24.91][i])), 'exterior wall centerlines should enclose the footprint once wall thickness is included');
    const units={};
    for(const side of ['east','west']){
      const enclosures=rooms.filter(r=>r.unit_id===side);
      const bedrooms=enclosures.filter(r=>/bed|master|نوم/i.test([r.id,r.role].join(' ')) &&
        !/bath|ensuite|dress|wardrobe/i.test(r.id));
      assert.ok(bedrooms.length>=3, 'each unit contains three distinct bedrooms: '+side);
      assert.ok(bedrooms.every(r=>r.windows?.length>0),'every bedroom has a real window opening');
      assert.ok(enclosures.some(r=>/kitchen/.test(r.role+' '+r.id)), 'independent kitchen for '+side);
      assert.ok(enclosures.some(r=>/majlis/.test(r.role+' '+r.id)), 'guest room for '+side);
      units[side]={rooms:enclosures.length,bedrooms:bedrooms.length};
    }
    const north=rooms.flatMap(r=>(r.windows||[]).filter(a=>a.edge==='N' && near(r.rect[1],.09)));
    assert.ok(north.length>=2,'street elevation must contain windows from actual rooms');
    return {level:level.index,elevation:level.elevation,units,streetWindows:north.length};
  });
  return {physicalUnits:levelData.length*2,levels:levelData};
}

async function serve(context, denied){
  const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.woff2':'font/woff2'};
  await context.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.origin!==origin || /^\/(?:v1|auth|rest|functions|storage)(?:\/|$)/.test(u.pathname)){
      denied.push(u.pathname);return route.abort();
    }
    if(live)return route.continue();
    const file=path.resolve(pub,'.'+(u.pathname==='/'?'/index.html':u.pathname));
    if(!file.startsWith(pub+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({body:fs.readFileSync(file),headers:{'content-type':mime[path.extname(file)]||'application/octet-stream','content-security-policy':csp}});
  });
}
async function menu(page,id){
  const item=page.locator('#'+id);if(!(await item.isVisible()))await page.locator('#guestTools').click();
  await item.click();
}
async function ready(page){
  await page.waitForFunction(()=>window.ACS?.exportModel?.() && document.querySelector('#acsGuestBanner')?.dataset.recovery==='complete',null,{timeout:60000});
}
async function runtime(page){
  return page.evaluate(async()=>{
    const {registry,camera}=await import('/app/ui/workspace-ui-wiring.js');
    const {renderer}=await import('/app/render/scene.js');
    const {Vector3}=await import('three');
    const state=window.ACS.guestViewState();
    camera.updateMatrixWorld();
    const floors=new Set(), kinds={}, wallBounds={}, ndc=[Infinity,Infinity,-Infinity,-Infinity];
    let visibleRackSections=0;
    const doorPairs=[];
    for(const [kind,layer] of Object.entries(registry)){
      const visible=layer.meshes.filter(m=>m.visible);
      kinds[kind]=visible.length;
      if(kind==='DOOR')for(const mesh of visible){
        const pair=mesh.userData.acs_door_pair;
        if(pair)doorPairs.push({id:pair.floor_key+'|'+pair.pair_id,hosts:pair.hosts.length});
      }
      if(kind==='FURN')visibleRackSections=visible.filter(mesh=>/\|rack\d/.test(mesh.name)).length;
      if(!['WALL','WINDOW','DOOR','FLOOR'].includes(kind))continue;
      for(const mesh of visible){
        const floor=mesh.name.split('|')[1];floors.add(floor);mesh.updateWorldMatrix(true,false);
        if(!mesh.geometry.boundingBox)mesh.geometry.computeBoundingBox();
        const bb=mesh.geometry.boundingBox;
        for(const x of [bb.min.x,bb.max.x])for(const y of [bb.min.y,bb.max.y])for(const z of [bb.min.z,bb.max.z]){
          const p=new Vector3(x,y,z).applyMatrix4(mesh.matrixWorld);
          if(kind==='WALL'){
            const bounds=wallBounds[floor]||=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
            for(const [i,value] of [p.x,p.y,p.z].entries()){
              bounds[i]=Math.min(bounds[i],value);bounds[i+3]=Math.max(bounds[i+3],value);
            }
          }
          p.project(camera);
          ndc[0]=Math.min(ndc[0],p.x);ndc[1]=Math.min(ndc[1],p.y);
          ndc[2]=Math.max(ndc[2],p.x);ndc[3]=Math.max(ndc[3],p.y);
        }
      }
    }
    const {modelRevision}=await import('/app/core/standards.js');
    const revision=modelRevision(window.ACS.exportModel(),'building','bld_0',null);
    const rendered=renderer.info.render;
    return {state,revision:{id:revision.revision_id,hash:revision.model_hash},
      triangles:rendered.triangles,drawCalls:rendered.calls,eye:camera.position.toArray(),floors:[...floors],kinds,wallBounds,doorPairs,visibleRackSections,ndc,quality:window.ACS.legacyRenderQuality()};
  });
}
async function capture(page,report,label,expected,close=false){
  if(expected)await page.waitForFunction(mode=>window.ACS?.guestViewState?.().mode===mode,expected);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const scene=await runtime(page);
  const file=report.width+'-'+label+'.png';
  console.log(report.width+' capturing '+label);
  await page.screenshot({path:path.join(out,file),animations:'disabled'});
  console.log(report.width+' wrote '+file);
  const view={label,file,scene};report.views.push(view);
  assert.ok(scene.state.cameraY>scene.state.groundY,'camera below ground');
  assert.ok(scene.state.orbitMaxPolar<=Math.PI/2+1e-5,'orbit can turn under the ground');
  if(!close)assert.ok(scene.ndc.every(v=>Number.isFinite(v) && Math.abs(v)<1.03),label+' cut off: '+scene.ndc);
  if(expected==='cutaway'){
    assert.deepEqual(scene.floors,[scene.state.floorKey],'visible built walls and glazing match selected floor');
    assert.ok(scene.kinds.WALL>0,'cutaway contains walls');
  }
  const pixels=await analysePageViewport(page,'#app canvas');
  assert.equal(pixels.verdict,'VISIBLE_CONTENT');
  view.pixels={verdict:pixels.verdict,colours:pixels.distinct_colours,mean:pixels.luminance_mean,variance:pixels.luminance_variance};
  fs.writeFileSync(path.join(out,report.width+'-journey.json'),JSON.stringify(report,null,2));
  return scene;
}
async function cameraControl(page,view){
  const control=page.locator('#camBar [data-view="'+view+'"]');
  if(!(await control.isVisible()))await page.locator('#mobileToolsToggle').click();
  await control.click();
}
async function detailAndInterior(page,report,prefix){
  await menu(page,'guestDetail');const close=await capture(page,report,prefix+'-detail','detail',true);
  assert.match(close.state.focusSource,/^DOOR\|F0\|/,'detail must target an actual entrance mesh');
  await menu(page,'guestInterior');const inside=await capture(page,report,prefix+'-interior','interior',true);
  const floor=await page.evaluate(()=>{const model=window.ACS.exportModel();return model.floors[model.levels.find(level=>level.index===0).template].rooms;});
  const rooms=floor.filter(room=>contains(room.rect,[inside.eye[0],inside.eye[2]])).map(room=>room.id);
  assert.ok(rooms.length>0,'the interior preset must place the eye inside a real ground-floor room');
  assert.ok(rooms.some(room=>inside.state.focusSource.split('|').includes(room)), 'interior focus and camera room must agree');
  report.views.at(-1).sourceRooms=rooms;
  await page.locator('#guestViewToggle').click();
  assert.equal((await runtime(page)).state.mode,'exterior');
}
function assertWallEnvelope(bounds,level){
  assert.ok(bounds,'missing walls on physical floor '+level);
  const [x,y,z,maxX,,maxZ]=bounds;
  assert.ok(near(x,0)&&near(z,0)&&near(maxX,20)&&near(maxZ,25),
    'outside wall faces differ from 20 x 25 m footprint on level '+level+': '+bounds.join(','));
  assert.ok(near(y,level*3.4),'wall elevation on level '+level+': '+y);
}
function readGLBWalls(asset,bytes,bin){
  // Read actual POSITION data independently from the browser scene and GLB writer.
  const {Matrix4,Vector3,Quaternion}=require('three');
  const floors={};
  function visit(index,parent){
    const node=asset.nodes[index],local=new Matrix4();
    if(node.matrix)local.fromArray(node.matrix);
    else local.compose(new Vector3(...(node.translation||[0,0,0])),new Quaternion(...(node.rotation||[0,0,0,1])),new Vector3(...(node.scale||[1,1,1])));
    const world=parent.clone().multiply(local);
    const name=/^WALL\|(F[012])\|/.exec(node.name||'');
    if(name && node.mesh!=null){
      const bounds=floors[name[1]]||=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
      for(const primitive of asset.meshes[node.mesh].primitives){
        const acc=asset.accessors[primitive.attributes.POSITION],view=asset.bufferViews[acc.bufferView];
        assert.ok(acc.componentType===5126&&acc.type==='VEC3'&&view.buffer===0&&!acc.sparse,'unexpected GLB coordinate layout');
        for(let i=0;i<acc.count;i++){
          const at=bin+(view.byteOffset||0)+(acc.byteOffset||0)+i*(view.byteStride||12);
          const vertex=new Vector3(bytes.readFloatLE(at),bytes.readFloatLE(at+4),bytes.readFloatLE(at+8)).applyMatrix4(world);
          for(const [axis,value] of vertex.toArray().entries()){
            bounds[axis]=Math.min(bounds[axis],value);bounds[axis+3]=Math.max(bounds[axis+3],value);
          }
        }
      }
    }
    for(const child of node.children||[])visit(child,world);
  }
  for(const node of asset.scenes[asset.scene||0].nodes)visit(node,new Matrix4());
  return floors;
}
async function modelGLB(page,report){
  await menu(page,'guestFloors');await page.locator('#acsTabShow').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#bGlb').click()]);
  const file=path.join(out,'apartment.glb');await download.saveAs(file);
  const bytes=fs.readFileSync(file);assert.equal(bytes.toString('utf8',0,4),'glTF');
  assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
  assert.equal(bytes.toString('utf8',16,20),'JSON');
  const asset=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const binHeader=20+bytes.readUInt32LE(12);assert.equal(bytes.toString('ascii',binHeader+4,binHeader+8),'BIN\0');
  const wallBounds=readGLBWalls(asset,bytes,binHeader+8);
  for(const level of [0,1,2])assertWallEnvelope(wallBounds['F'+level],level);
  const names=asset.nodes.map(node=>node.name||'');
  for(const floor of ['F0','F1','F2']){
    for(const kind of ['WALL','WINDOW','DOOR'])assert.ok(names.some(n=>n.startsWith(kind+'|'+floor+'|')),kind+' missing on '+floor+' in GLB');
  }
  report.glb={sha256:sha256(bytes),bytes:bytes.length,meshes:asset.meshes.length,wallBounds};
}
async function checkedViewport(browser,width){
  const height=width===393?852:900, denied=[], errors=[];
  const ctx=await browser.newContext({viewport:{width,height},serviceWorkers:'block',acceptDownloads:true});
  ctx.setDefaultTimeout(45000);
  const report={width,height,views:[],result:'INCOMPLETE'};
  let page,phase;
  function step(name){
    phase=name;report.phase=name;
    console.log(width+' '+name);
    fs.writeFileSync(path.join(out,width+'-journey.json'),JSON.stringify(report,null,2));
  }
  step('open_public_entry');
  try{
    await serve(ctx,denied);page=await ctx.newPage();
    page.on('pageerror',e=>errors.push(e.name));
    await page.goto(origin+'/');await ready(page);
    const identity=await page.evaluate(()=>window.ACS_BUILD_INFO?.git_sha||null);
    if(live)assert.equal(identity,process.env.ACS_VERIFY_EXPECT_SHA);
    report.checkedBuild=identity;
    assert.equal(await page.locator('#login').isVisible(),false);
    const banner=await page.locator('#acsGuestBanner').boundingBox();
    if(width===393)assert.ok(banner.height<=92,'phone guest controls still dominate the model: '+banner.height);
    assert.ok(!(await page.locator('#guestSignin').isVisible()),'login CTA must not dominate the fresh entry');
    await capture(page,report,'fresh-entry','exterior');
    step('warehouse_cutaway');await menu(page,'guestWarehouse');
    await page.waitForFunction(()=>window.ACS.exportModel().site.w===120);
    const warehouse=await capture(page,report,'warehouse-workfloor','cutaway');
    assert.ok(warehouse.visibleRackSections>0,'visible racks must expose the purpose of the cutaway');
    step('warehouse_exterior');await page.locator('#guestViewToggle').click();
    await capture(page,report,'warehouse-exterior','exterior');
    await cameraControl(page,'bird');await capture(page,report,'warehouse-aerial','aerial');
    await cameraControl(page,'arch');await capture(page,report,'warehouse-eye-level','street');
    await detailAndInterior(page,report,'warehouse');
    step('complete_arabic_brief');await page.locator('#guestCreate').click();
    await page.locator('#descText').fill(brief);await page.locator('#genText').click();
    await page.waitForFunction(()=>window.ACS.exportModel()?.meta?.acs_apartment?.units_total===6,null,{timeout:45000});
    if(width===393&&await page.locator('#projectPanelClose').isVisible())await page.locator('#projectPanelClose').click();
    const model=await page.evaluate(()=>window.ACS.exportModel());
    report.model=inspectApartment(model);report.modelHash=sha256(JSON.stringify(model));
    step('actual_model_download');
    const [modelDownload]=await Promise.all([page.waitForEvent('download'),menu(page,'guestExport')]);
    assert.equal(await modelDownload.failure(),null);
    const jsonFile=path.join(out,width+'-apartment.json');
    await modelDownload.saveAs(jsonFile);
    const exported=JSON.parse(fs.readFileSync(jsonFile,'utf8'));
    assert.deepEqual(inspectApartment(exported),report.model);
    for(const k of Object.keys(model.floors)){
      assert.deepEqual(exported.floors[k].rooms.map(r=>r.rect),model.floors[k].rooms.map(r=>r.rect));
    }
    report.downloadHash=sha256(fs.readFileSync(jsonFile));
    step('housing_exterior');const exterior=await capture(page,report,'apartment-exterior','exterior');
    assert.ok(exterior.kinds.WINDOW>=6 && exterior.kinds.DOOR>=6,'real building window/door meshes required');
    assert.ok(exterior.floors.includes('F2'),'whole occupied building visible');
    const sourcePairs=new Set();
    for(const level of model.levels){
      for(const room of model.floors[level.template].rooms){
        for(const door of room.doors||[]){
          if(door.acs_door_pair)sourcePairs.add('F'+level.index+'|'+door.acs_door_pair.id);
        }
      }
    }
    assert.deepEqual(exterior.doorPairs.map(p=>p.id).sort(),[...sourcePairs].sort(),'each pair of canonical hosts has one physical door mesh');
    assert.ok(exterior.doorPairs.every(p=>p.hosts===2),'both room hosts are preserved');

    for(const level of report.model.levels){
      assertWallEnvelope(exterior.wallBounds['F'+level.level],level.level);
    }
    await cameraControl(page,'arch');await capture(page,report,'apartment-eye-level','street');
    await cameraControl(page,'bird');await capture(page,report,'apartment-aerial','aerial');
    await detailAndInterior(page,report,'apartment');
    step('housing_cutaway');await page.locator('#guestViewToggle').click();
    await capture(page,report,'apartment-cutaway','cutaway');
    step('apartment_plan');await page.locator('#guestPlan').click();
    const dlg=page.locator('#guestPlanDialog');
    await dlg.waitFor({state:'visible'});await page.locator('#guestPlanFloor').selectOption('1');
    const diagram=page.locator('#guestPlanViewport svg');assert.equal(await diagram.getAttribute('data-level-index'),'1');
    for(const side of ['east','west'])assert.ok(await diagram.locator('[data-unit="'+side+'"]').count()>=3);
    assert.ok(await diagram.locator('[data-opening-id]').count()>6);
    await page.screenshot({path:path.join(out,width+'-first-floor-plan.png'),animations:'disabled'});
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#guestPlanDownload').click()]);
    assert.equal(await download.failure(),null);assert.match(download.suggestedFilename(),/\.svg$/i);
    const svgFile=path.join(out,width+'-first-floor.svg');await download.saveAs(svgFile);
    const svg=fs.readFileSync(svgFile,'utf8');assert.ok(svg.includes('<svg')&&svg.includes('data-room-key'));
    await page.locator('#guestPlanClose').click();await dlg.waitFor({state:'hidden'});
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,'presentation state modified the selected model');
    if(width===1440){step('download_glb');await modelGLB(page,report);}
    step('separate_example');await page.goto(origin+'/?guest=1&example=apartment-20x25');await ready(page);
    assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_apartment_20x25_v1');
    inspectApartment(await page.evaluate(()=>window.ACS.exportModel()));
    assert.deepEqual(denied,[]);assert.deepEqual(errors,[]);
    report.forbiddenRequests=denied.length;report.result='PASS';return report;
  }catch(e){
    report.result='FAIL';report.phase=phase;report.diagnostic=e.message.slice(0,700);report.errors=errors;
    if(page)await page.screenshot({path:path.join(out,width+'-failure.png'),timeout:8000}).catch(()=>{});
    return report;
  }
  finally{fs.writeFileSync(path.join(out,width+'-journey.json'),JSON.stringify(report,null,2));await ctx.close();}
}
async function main(){
  fs.mkdirSync(out,{recursive:true});
  const configured=process.env.ACS_APARTMENT_VIEWPORT;
  if(configured!==undefined && !['393','1440'].includes(configured))throw Error('ACS_APARTMENT_VIEWPORT must be 393 or 1440');
  const widths=configured===undefined?[393,1440]:[Number(configured)];
  const b=await PW.launch();
  try{
    const runs=[];
    for(const width of widths)runs.push(await checkedViewport(b,width));
    fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({scope:live?'published':'candidate assets',browser:b.version(),host:{os:os.platform(),release:os.release(),cpu:os.cpus()[0]?.model,logicalCpuCount:os.availableParallelism(),physicalPhone:false},syntheticBrief:true,briefHash:sha256(brief),runs},null,2));
    const failures=runs.filter(run=>run.result!=='PASS');
    if(failures.length)throw Error(failures.map(run=>run.width+' '+run.phase+' '+run.diagnostic).join('\n'));
    console.log('PASS public apartment: actual Arabic brief, six physical units, contained upper doors, visible facade openings, camera above ground, floor SVG, warehouse cutaway, zero private/provider requests');
  }finally{await b.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exitCode=1;});
module.exports={inspectApartment};
