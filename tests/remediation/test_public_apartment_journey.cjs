'use strict';
// Acceptance for the actual public guest entry. The browser exercises controls;
// read-only observations of exported rooms and rendered meshes tie each still to its model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
const {execFileSync} = require('node:child_process');
const PW = require('../../tools/pw_chromium.js');
const {analysePageViewport} = require('../deploy/lib_viewport_pixels.js');

const root = path.resolve(__dirname, '../..');
const pub = path.join(root, 'public');
const out = path.resolve(process.env.ACS_APARTMENT_EVIDENCE || 'logs/public-apartment');
const live = process.env.ACS_APARTMENT_LIVE === '1';
const origin = live ? 'https://sprightly-selkie-d906c3.netlify.app' : 'https://acs-guest.test';
const CASES = Object.freeze([
  {id:'riyadh-20x25',fixture:'riyadh-apartment-ar.txt',width:20,depth:25,levels:3,units:6,entrance:'N',courtyard:false,baseline:true},
  {id:'riyadh-24x28',fixture:'riyadh-apartment-24x28-ar.txt',width:24,depth:28,levels:4,units:8,entrance:'N',courtyard:false},
  {id:'central-courtyard',fixture:'riyadh-apartment-courtyard-ar.txt',width:20,depth:25,levels:3,units:6,entrance:'N',courtyard:true},
  {id:'saudi-west-entry',fixture:'saudi-apartment-west-ar.txt',width:24,depth:28,levels:3,units:6,entrance:'W',courtyard:false},
]);
const checkoutSHA = execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const sourceSHA = process.env.ACS_VERIFY_EXPECT_SHA || checkoutSHA;
assert.match(sourceSHA,/^[0-9a-f]{40}$/,'evidence requires a full source commit SHA');
assert.equal(checkoutSHA,sourceSHA,'checked-out source must match the requested evidence commit');
const sourceTreeDirty = execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim().length>0;
const caseBrief = spec => fs.readFileSync(path.join(root,'tests/fixtures/briefs',spec.fixture),'utf8');
const csp = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(root, 'netlify.toml'), 'utf8'))[1];
const sha256 = body => crypto.createHash('sha256').update(body).digest('hex');
const near = (a,b) => Math.abs(a-b) <= .01;

function doorExit(rect, door, step=.02){
  const [x,z,w,d] = rect;
  switch(door.edge){
    case 'N': return [x+door.offset,z-step];
    case 'S': return [x+door.offset,z+d+step];
    case 'W': return [x-step,z+door.offset];
    case 'E': return [x+w+step,z+door.offset];
    default: throw Error('Missing door wall');
  }
}
function contains([x,z,w,d],[u,v]){
  return u>=x && u<=x+w && v>=z && v<=z+d;
}
function intersects(a,b){
  return Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0])>.003 &&
    Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1])>.003;
}
function facadeOpening(room,opening,edge,spec,half){
  if(opening.edge!==edge)return false;
  const [x,z,w,d]=room.rect;
  return {N:near(z,half),S:near(z+d,spec.depth-half),W:near(x,half),E:near(x+w,spec.width-half)}[edge];
}
function inspectApartment(model,spec=CASES[0]){
  const occupied = model.levels.filter(l => l.kind!=='roof');
  assert.deepEqual(occupied.map(l=>l.index),Array.from({length:spec.levels},(_,i)=>i),'physical floor count must follow this brief');
  assert.deepEqual(occupied.map(l=>l.elevation),Array.from({length:spec.levels},(_,i)=>Math.round(i*3.4*100)/100),'requested floor elevations');
  assert.deepEqual([model.site.w,model.site.d],[spec.width,spec.depth],'building width and depth must follow this brief');
  assert.equal(model.meta.acs_apartment.units_total,spec.units,'declared units must agree with independently counted rooms');
  const half=model.wall_t/2;
  let courtyard=null,courtyardAxes=null;
  if(spec.courtyard){
    const declared=model.meta.acs_apartment.courtyard;
    assert.equal(declared?.open_to_sky,true,'requested courtyard must be open to the sky');
    assert.equal(declared.occupied_floor,false,'open courtyard cannot count as an occupied floor');
    courtyard=declared.rect_m;
    assert.ok(Array.isArray(courtyard)&&courtyard.length===4&&courtyard.every(Number.isFinite),'courtyard must declare a measurable clear rectangle');
    assert.ok(courtyard[2]>1&&courtyard[3]>1&&courtyard[0]>.5&&courtyard[1]>.5&&courtyard[0]+courtyard[2]<spec.width-.5&&courtyard[1]+courtyard[3]<spec.depth-.5,'courtyard must be a usable interior opening within the facade');
    assert.ok(Math.abs((courtyard[0]+courtyard[2]/2)/spec.width-.5)<1/6&&Math.abs((courtyard[1]+courtyard[3]/2)/spec.depth-.5)<1/6,'courtyard must remain in the central portion of the building');
    courtyardAxes=declared.footprint_void_m;
    assert.ok(Array.isArray(courtyardAxes)&&courtyardAxes.length===4&&courtyardAxes.every(Number.isFinite),'courtyard must reserve a declared footprint independently of its clear dimensions');
    assert.ok(contains(courtyardAxes,[courtyard[0],courtyard[1]])&&contains(courtyardAxes,[courtyard[0]+courtyard[2],courtyard[1]+courtyard[3]]),'clear courtyard must fit within its unoccupied footprint');
  }else assert.ok(!model.meta.acs_apartment.courtyard,'a courtyard must not appear in briefs that did not request one');
  const levelData = occupied.map(level=>{
    const rooms = model.floors[level.template].rooms;
    const courts=model.floors[level.template].courtyards||[];
    assert.equal(courts.length,spec.courtyard?1:0,'each physical floor must retain the requested courtyard count');
    if(spec.courtyard){
      assert.deepEqual(courts[0].clear_rect,courtyard,'clear courtyard must align through all occupied levels');
      assert.deepEqual(courts[0].rect,courtyardAxes,'courtyard footprint must align through all occupied levels');
      assert.equal(courts[0].open_to_sky,true);
    }
    assert.equal(new Set(rooms.map(room=>room.id)).size,rooms.length,'room identifiers must be unique within each level');
    const span = [Infinity,Infinity,-Infinity,-Infinity];
    const neighbours=new Map(rooms.map(room=>[room.id,new Set()]));
    let groundCourtyardDoors=0;
    for(const room of rooms){
      const [x,z,w,d] = room.rect;
      assert.ok(w>0 && d>0 && room.rect.every(Number.isFinite));
      assert.ok(x>=-.01 && z>=-.01 && x+w<=spec.width+.01 && z+d<=spec.depth+.01,'room outside declared footprint: '+room.id);
      if(courtyard)assert.ok(!intersects(room.rect,courtyard),'an occupied room covers the open courtyard: '+room.id);
      for(const other of rooms)if(other!==room)assert.ok(!intersects(room.rect,other.rect),'overlapping rooms: '+room.id+'/'+other.id);
      span[0]=Math.min(span[0],x);span[1]=Math.min(span[1],z);
      span[2]=Math.max(span[2],x+w);span[3]=Math.max(span[3],z+d);
      for(const door of room.doors||[]){
        const length=room.rect[['N','S'].includes(door.edge)?2:3];
        assert.ok(Number.isFinite(door.offset)&&door.width>=.75&&door.offset-door.width/2>=.06&&door.offset+door.width/2<=length-.06,'door outside its hosting wall: '+room.id+'/'+door.id);
        const exit=doorExit(room.rect,door);
        const other=rooms.find(other=>other!==room&&contains(other.rect,exit));
        if(!other){
          assert.ok(spec.courtyard&&level.index===0&&room.id==='courtyard_gallery_north'&&room.role==='corridor'&&!room.unit_id&&door.id==='court_ground_door','door opens into unsupported air: '+level.index+'/'+room.id);
          assert.ok(contains(courtyardAxes,exit)&&contains(courtyard,doorExit(room.rect,door,half+.02)),'named ground courtyard door must actually open into its at-grade clear space');
          groundCourtyardDoors++;
          continue;
        }
        const center=doorExit(room.rect,door,0);
        assert.ok(other.doors?.some(peer=>{
          const p=doorExit(other.rect,peer,0);
          return {N:'S',S:'N',W:'E',E:'W'}[door.edge]===peer.edge&&near(p[0],center[0])&&near(p[1],center[1])&&near(peer.width,door.width);
        }),'door lacks a reciprocal opening: '+room.id+'/'+door.id);
        neighbours.get(room.id).add(other.id);
      }
    }
    assert.equal(groundCourtyardDoors,spec.courtyard&&level.index===0?1:0,'exactly the declared ground garden access may open outside occupied rooms; upper doors remain paired');
    assert.ok(span.every((v,i)=>near(v,[half,half,spec.width-half,spec.depth-half][i])),'exterior wall centerlines must enclose the requested footprint');
    const start=rooms.find(r=>r.id===(level.index?'lobby':'entrance_porch'));
    assert.ok(start,'common entry is represented by actual geometry');
    const seen=new Set(),pending=[start.id];
    while(pending.length){const id=pending.pop();if(seen.has(id))continue;seen.add(id);pending.push(...neighbours.get(id));}
    assert.equal(seen.size,rooms.length,'each occupied room must be connected to the shared entry through valid doors');
    if(!level.index){
      const [x,z,w,d]=start.rect;
      const actualEdge=near(z,half)?'N':near(x,half)?'W':near(x+w,spec.width-half)?'E':near(z+d,spec.depth-half)?'S':null;
      assert.equal(actualEdge,spec.entrance,'entry porch geometry must move to the requested facade');
      const lobby=rooms.find(r=>r.id==='lobby');
      assert.ok(lobby.doors.some(door=>door.edge===spec.entrance&&contains(start.rect,doorExit(lobby.rect,door))),'actual lobby entrance door must face the requested street');
    }
    const units={};
    assert.deepEqual([...new Set(rooms.map(room=>room.unit_id).filter(Boolean))].sort(),['east','west'],'each floor must contain exactly two independently identified apartments');
    for(const side of ['east','west']){
      const enclosures=rooms.filter(r=>r.unit_id===side);
      const bedrooms=enclosures.filter(r=>/bed|master|نوم/i.test([r.id,r.role].join(' ')) &&
        !/bath|ensuite|dress|wardrobe/i.test(r.id));
      assert.equal(bedrooms.length,3,'each unit contains exactly three distinct bedrooms: '+side);
      assert.ok(bedrooms.every(r=>r.windows?.length>0),'every bedroom has a real window opening');
      assert.ok(bedrooms.every(room=>room.windows.some(window=>{
        const daylight=doorExit(room.rect,window,model.wall_t+.02);
        return !rooms.some(other=>other!==room&&contains(other.rect,daylight));
      })),'every bedroom window must reach an exterior or open courtyard instead of another room');
      assert.ok(enclosures.some(r=>/kitchen/.test(r.role+' '+r.id)), 'independent kitchen for '+side);
      assert.ok(enclosures.some(r=>/majlis/.test(r.role+' '+r.id)), 'guest room for '+side);
      units[side]={rooms:enclosures.length,bedrooms:bedrooms.length};
    }
    const streetWindows=rooms.flatMap(r=>(r.windows||[]).filter(a=>facadeOpening(r,a,spec.entrance,spec,half)));
    assert.ok(streetWindows.length>=2,'requested street elevation must contain windows from actual rooms');
    return {level:level.index,elevation:level.elevation,units,connectedRooms:seen.size,groundCourtyardDoors,streetWindows:streetWindows.length};
  });
  const physicalUnits=levelData.reduce((sum,level)=>sum+Object.keys(level.units).length,0);
  assert.equal(physicalUnits,spec.units,'physical apartments must follow this brief');
  return {physicalUnits,levels:levelData,courtyard};
}

async function serve(context, denied){
  const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.jpg':'image/jpeg','.woff2':'font/woff2'};
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
// «مشروع جديد» holds the ways to begin (brief, examples); «•••» holds the rest.
const START_SHEET=new Set(['guestCreate','guestExample','guestWarehouse']);
async function menu(page,id){
  const item=page.locator('#'+id);
  if(!(await item.isVisible()))await page.locator(START_SHEET.has(id)?'#guestStart':'#guestTools').click();
  await item.click();
}
async function ready(page){
  await page.waitForFunction(()=>window.ACS?.exportModel?.() && document.querySelector('#acsGuestBanner')?.dataset.recovery==='complete',null,{timeout:60000});
}
async function runtime(page){
  return page.evaluate(async()=>{
    const {registry,camera}=await import('/app/ui/workspace-ui-wiring.js');
    const {renderer}=await import('/app/render/scene.js');
    const {Box3,Vector3}=await import('three');
    const state=window.ACS.guestViewState();
    camera.updateMatrixWorld();
    const floors=new Set(), kinds={}, wallBounds={}, floorSurfaces=[], ndc=[Infinity,Infinity,-Infinity,-Infinity];
    let visibleRackSections=0;
    const doorPairs=[],entranceDoors=[];
    for(const [kind,layer] of Object.entries(registry)){
      const visible=layer.meshes.filter(m=>m.visible);
      kinds[kind]=visible.length;
      if(kind==='DOOR')for(const mesh of visible){
        const pair=mesh.userData.acs_door_pair;
        if(pair)doorPairs.push({id:pair.floor_key+'|'+pair.pair_id,hosts:pair.hosts.length});
        if(pair?.floor_key==='F0'&&pair.hosts.some(host=>host.room_id==='entrance_porch')&&pair.hosts.some(host=>host.room_id==='lobby')){
          const bounds=new Box3().setFromObject(mesh);
          entranceDoors.push({name:mesh.name,center:bounds.getCenter(new Vector3()).toArray(),size:bounds.getSize(new Vector3()).toArray()});
        }
      }
      if(kind==='FURN')visibleRackSections=visible.filter(mesh=>/\|rack\d/.test(mesh.name)).length;
      if(!['WALL','WINDOW','DOOR','FLOOR'].includes(kind))continue;
      for(const mesh of visible){
        const floor=mesh.name.split('|')[1];floors.add(floor);mesh.updateWorldMatrix(true,false);
        if(!mesh.geometry.boundingBox)mesh.geometry.computeBoundingBox();
        const bb=mesh.geometry.boundingBox;
        const slab=kind==='FLOOR'?[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity]:null;
        for(const x of [bb.min.x,bb.max.x])for(const y of [bb.min.y,bb.max.y])for(const z of [bb.min.z,bb.max.z]){
          const p=new Vector3(x,y,z).applyMatrix4(mesh.matrixWorld);
          if(slab)for(const [i,value] of [p.x,p.y,p.z].entries()){
            slab[i]=Math.min(slab[i],value);slab[i+3]=Math.max(slab[i+3],value);
          }
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
        if(slab)floorSurfaces.push({name:mesh.name,bounds:slab});
      }
    }
    const {modelRevision}=await import('/app/core/standards.js');
    const revision=modelRevision(window.ACS.exportModel(),'building','bld_0',null);
    const rendered=renderer.info.render;
    return {state,revision:{id:revision.revision_id,hash:revision.model_hash},
      triangles:rendered.triangles,drawCalls:rendered.calls,eye:camera.position.toArray(),floors:[...floors],kinds,wallBounds,floorSurfaces,doorPairs,entranceDoors,visibleRackSections,ndc,quality:window.ACS.legacyRenderQuality()};
  });
}
async function capture(page,report,label,expected,close=false){
  if(expected)await page.waitForFunction(mode=>window.ACS?.guestViewState?.().mode===mode,expected);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const scene=await runtime(page);
  const file=report.evidencePrefix+'-'+label+'.png';
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
  fs.writeFileSync(path.join(out,report.evidencePrefix+'-journey.json'),JSON.stringify(report,null,2));
  return scene;
}
async function nativeEntry(ctx,report){
  const phone=await ctx.newPage();
  try{
    await phone.goto(origin+'/guest-plans/apartment-iphone.html');
    const launch=phone.locator('a[rel~="ar"]');
    assert.equal(await launch.getAttribute('href'),'/guest-plans/apartment-20x25.usdz');
    await launch.locator('img').evaluate(img=>img.decode());
    assert.equal(await launch.locator('img').evaluate(img=>img.naturalWidth>300),true);
    const web=phone.getByRole('link',{name:'استكشف المبنى في المتصفح'});
    assert.equal(await web.getAttribute('href'),'/?guest=1&example=apartment-20x25');
    const file=report.evidencePrefix+'-open-on-iphone.png';
    await phone.screenshot({path:path.join(out,file),animations:'disabled'});
    console.log(report.width+' wrote '+file);
    report.nativeEntry={file,nativeHandoff:'/guest-plans/apartment-20x25.usdz',physicalIPhoneTest:false};
  }finally{await phone.close();}
}
async function idleFrames(page){
  // Playwright checks the predicate's immediate truthiness. An async predicate
  // returns a truthy Promise even when that Promise later resolves to false,
  // ending polling early. Keep the predicate synchronous and its idle sample
  // private to this call; observe counters without asking the app to redraw.
  const sample=await page.evaluateHandle(()=>({since:null,draws:null,rendererFrames:null}));
  let snapshot;
  try{
    snapshot=await page.waitForFunction(sample=>{
      const current=window.ACS.guestRenderStats(),now=performance.now();
      if(current.owner!=='guest'||current.pending||!Number.isFinite(current.draws)||!Number.isFinite(current.rendererFrames)){
        sample.since=null;return false;
      }
      if(sample.since===null||sample.draws!==current.draws||sample.rendererFrames!==current.rendererFrames){
        Object.assign(sample,{since:now,draws:current.draws,rendererFrames:current.rendererFrames});
        return false;
      }
      return now-sample.since>=350?current:false;
    },sample,{polling:100,timeout:25000});
    return await snapshot.jsonValue();
  }finally{await snapshot?.dispose();await sample.dispose();}
}
async function inspectOrbit(page,report){
  report.orbitFrames={phase:'initial_idle'};
  let camera;
  try{
    const before=await idleFrames(page);
    camera=await page.evaluateHandle(async()=>{
      const {camera}=await import('/app/ui/workspace-ui-wiring.js');return camera;
    });
    const eye=await camera.evaluate(camera=>camera.position.toArray());
    Object.assign(report.orbitFrames,{before,eyeBefore:eye,phase:'gesture'});
    const point=await page.evaluate(()=>{
      const y=Math.round(innerHeight*.52);
      for(const ratio of [.35,.48,.62]){
        const x=Math.round(innerWidth*ratio);
        if(document.elementFromPoint(x,y)?.matches('#app canvas'))return {x,y};
      }
      return null;
    });
    report.orbitFrames.point=point;
    assert.ok(point,'viewer must be available to orbit');
    await page.mouse.move(point.x,point.y);await page.mouse.down();
    await page.mouse.move(point.x+28,point.y-10,{steps:5});await page.mouse.up();
    await page.waitForFunction(({camera,eye})=>Math.hypot(camera.position.x-eye[0],camera.position.z-eye[2])>.10,
      {camera,eye},{timeout:15000});
    const after=await idleFrames(page);
    Object.assign(report.orbitFrames,{after,eyeAfter:await camera.evaluate(camera=>camera.position.toArray()),phase:'frame_growth'});
    console.log(report.caseId+' '+report.width+' orbit counters '+JSON.stringify(report.orbitFrames));
    assert.ok(after.draws>before.draws&&after.rendererFrames>before.rendererFrames,'real orbit gesture must submit a rendered frame');
    report.orbitFrames.phase='passed';
  }catch(error){
    report.orbitFrames.failureStats=await page.evaluate(()=>window.ACS.guestRenderStats()).catch(()=>null);
    console.log(report.caseId+' '+report.width+' orbit failure '+JSON.stringify(report.orbitFrames));
    throw error;
  }finally{await camera?.dispose();}
}
async function publishedQuickLook(){
  const asset='/guest-plans/apartment-20x25.usdz';
  const opts={redirect:'error',signal:AbortSignal.timeout(20000)};
  const range=await fetch(origin+asset,{...opts,headers:{Range:'bytes=0-31'}});
  assert.equal(range.status,206,'native viewer byte range');
  assert.match(range.headers.get('content-type')||'',/^model\/vnd\.usdz\+zip(?:;|$)/i);
  assert.match(range.headers.get('content-range')||'',/^bytes 0-31\/\d+$/);
  const prefix=Buffer.from(await range.arrayBuffer());
  assert.equal(prefix.length,32);assert.equal(prefix.readUInt32LE(0),0x04034b50);
  const local=fs.readFileSync(path.join(pub,asset.slice(1)));
  const full=await fetch(origin+asset,{redirect:'error',signal:AbortSignal.timeout(45000)});
  assert.equal(full.status,200);
  const bytes=Buffer.from(await full.arrayBuffer());
  assert.equal(sha256(bytes),sha256(local),'published USDZ must match verified native model');
  return {bytes:bytes.length,sha256:sha256(bytes),type:range.headers.get('content-type'),range:range.status};
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
function assertWallEnvelope(bounds,level,spec=CASES[0]){
  assert.ok(bounds,'missing walls on physical floor '+level);
  const [x,y,z,maxX,,maxZ]=bounds;
  assert.ok(near(x,0)&&near(z,0)&&near(maxX,spec.width)&&near(maxZ,spec.depth),
    'outside wall faces differ from requested '+spec.width+' x '+spec.depth+' m footprint on level '+level+': '+bounds.join(','));
  assert.ok(near(y,level*3.4),'wall elevation on level '+level+': '+y);
}
function assertCourtyardSurfaces(surfaces,rect,source){
  assert.ok(surfaces.length>0,source+' must contain actual horizontal floor geometry');
  for(const surface of surfaces){
    const [x,,z,maxX,,maxZ]=surface.bounds;
    assert.ok(!intersects([x,z,maxX-x,maxZ-z],rect),source+' closes the requested courtyard: '+surface.name);
  }
}
function readGLBGeometry(asset,bytes,bin){
  // Read actual POSITION data independently from the browser scene and GLB writer.
  const {Matrix4,Vector3,Quaternion}=require('three');
  const floors={},floorSurfaces=[];
  function visit(index,parent){
    const node=asset.nodes[index],local=new Matrix4();
    if(node.matrix)local.fromArray(node.matrix);
    else local.compose(new Vector3(...(node.translation||[0,0,0])),new Quaternion(...(node.rotation||[0,0,0,1])),new Vector3(...(node.scale||[1,1,1])));
    const world=parent.clone().multiply(local);
    const name=/^(WALL|FLOOR)\|(F\d+)\|/.exec(node.name||'');
    if(name && node.mesh!=null){
      const bounds=name[1]==='WALL'?(floors[name[2]]||=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity]):[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
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
      if(name[1]==='FLOOR')floorSurfaces.push({name:node.name,bounds});
    }
    for(const child of node.children||[])visit(child,world);
  }
  for(const node of asset.scenes[asset.scene||0].nodes)visit(node,new Matrix4());
  return {floors,floorSurfaces};
}
async function modelGLB(page,report,options=CASES[0]){
  const spec={width:options.width??20,depth:options.depth??25,levels:options.levels??options.floors??3};
  const directory=options.directory??out,filename=options.filename??report.evidencePrefix+'-apartment.glb';
  await menu(page,'guestFloors');await page.locator('#acsTabShow').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#bGlb').click()]);
  assert.equal(await download.failure(),null);
  const file=path.join(directory,filename);await download.saveAs(file);
  const bytes=fs.readFileSync(file);assert.equal(bytes.toString('utf8',0,4),'glTF');
  assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
  assert.equal(bytes.toString('utf8',16,20),'JSON');
  const asset=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const binHeader=20+bytes.readUInt32LE(12);assert.equal(bytes.toString('ascii',binHeader+4,binHeader+8),'BIN\0');
  const {floors:wallBounds,floorSurfaces}=readGLBGeometry(asset,bytes,binHeader+8);
  for(let level=0;level<spec.levels;level++)assertWallEnvelope(wallBounds['F'+level],level,spec);
  const names=asset.nodes.map(node=>node.name||'');
  for(const floor of Array.from({length:spec.levels},(_,i)=>'F'+i)){
    for(const kind of ['WALL','WINDOW','DOOR'])assert.ok(names.some(n=>n.startsWith(kind+'|'+floor+'|')),kind+' missing on '+floor+' in GLB');
  }
  const courtyard=options.courtyardRect??report.model?.courtyard??report.voidRect;
  if(courtyard)assertCourtyardSurfaces(floorSurfaces,courtyard,'downloaded GLB');
  report.glb={sha256:sha256(bytes),bytes:bytes.length,meshes:asset.meshes.length,wallBounds};
}
async function closeProjectPanel(page,width){
  if(width===393&&await page.locator('#projectPanelClose').isVisible())await page.locator('#projectPanelClose').click();
}
async function upperFloorViews(page,report,spec){
  for(let level=1;level<spec.levels;level++){
    await menu(page,'guestFloors');
    await page.locator('#floors [data-floor="F'+level+'"]').click();
    await closeProjectPanel(page,report.width);
    const view=await capture(page,report,'floor-'+level+'-cutaway','cutaway');
    assert.equal(view.state.floorKey,'F'+level,'actual UI must select the requested upper floor');
    assertWallEnvelope(view.wallBounds['F'+level],level,spec);
    if(spec.courtyard)assertCourtyardSurfaces(view.floorSurfaces,report.model.courtyard,'upper-floor 3D');
  }
}
async function floorPlans(page,report,spec,model){
  await page.locator('#guestPlan').click();
  const dlg=page.locator('#guestPlanDialog');
  await dlg.waitFor({state:'visible'});
  report.floorPlans=[];
  for(let level=0;level<spec.levels;level++){
    await page.locator('#guestPlanFloor').selectOption(String(level));
    const diagram=page.locator('#guestPlanViewport svg');
    assert.equal(await diagram.getAttribute('data-level-index'),String(level));
    assert.ok(near(Number(await diagram.getAttribute('data-width-m')),spec.width),'SVG must measure the actual requested width');
    assert.ok(near(Number(await diagram.getAttribute('data-depth-m')),spec.depth),'SVG must measure the actual requested depth');
    for(const side of ['east','west'])assert.ok(await diagram.locator('[data-unit="'+side+'"]').count()>=3);
    assert.ok(await diagram.locator('[data-opening-id]').count()>6);
    assert.equal(await diagram.locator('[data-courtyard-id]').count(),spec.courtyard?1:0,'the live floor sheet must identify the actual courtyard opening');
    const projected=await page.evaluate(index=>{
      const packet=window.ACS.floorPlan2D(index,'TECHNICAL');
      const diagram=document.querySelector('#guestPlanViewport svg');
      const drawn=[...diagram.querySelectorAll('[data-room-key]')].map(group=>{
        const rect=group.querySelector('rect');
        return {id:group.getAttribute('data-room-key'),rect:['x','y','width','height'].map(key=>Number(rect.getAttribute(key)))};
      });
      const courts=[...diagram.querySelectorAll('[data-courtyard-id] rect')].map(rect=>['x','y','width','height'].map(key=>Number(rect.getAttribute(key))));
      return {spaces:packet.spaces,drawn,courts};
    },level);
    const rooms=model.floors[model.levels.find(item=>item.index===level).template].rooms;
    assert.equal(projected.spaces.length,rooms.length,'floor projection must retain every room');
    assert.equal(projected.drawn.length,rooms.length,'SVG must draw every projected room');
    // Recover SVG scale from a known room, then compare every independently
    // rendered rectangle with the selected model, including the courtyard gap.
    const first=projected.spaces[0], drawn=projected.drawn.find(item=>item.id===first.id);
    assert.ok(drawn,'SVG room identity must trace to the actual projection');
    const scale=drawn.rect[2]/first.w;
    assert.ok(scale>0&&Math.abs(drawn.rect[3]/first.d-scale)<.003,'SVG must use equal scales on both axes');
    const offset=[drawn.rect[0]-first.x*scale,drawn.rect[1]-first.z*scale];
    if(spec.courtyard){
      const rect=projected.courts[0];
      const actual=[(rect[0]-offset[0])/scale,(rect[1]-offset[1])/scale,rect[2]/scale,rect[3]/scale];
      assert.ok(actual.every((value,index)=>near(value,report.model.courtyard[index])),'actual SVG courtyard geometry must match the measured clear opening');
    }
    for(const space of projected.spaces){
      const room=rooms.find(item=>item.id===space.name);
      assert.ok(room,'projected room must belong to the selected floor');
      const rendered=projected.drawn.find(item=>item.id===space.id);
      assert.ok(rendered,'projected room missing from the actual SVG');
      const actual=[(rendered.rect[0]-offset[0])/scale,(rendered.rect[1]-offset[1])/scale,rendered.rect[2]/scale,rendered.rect[3]/scale];
      assert.ok(actual.every((v,i)=>near(v,room.rect[i])),'SVG geometry differs from selected room '+room.id);
      if(spec.courtyard)assert.ok(!intersects(actual,report.model.courtyard),'drawn floor plan fills the open courtyard');
    }
    const prefix=report.evidencePrefix+'-floor-'+level;
    await page.screenshot({path:path.join(out,prefix+'-plan.png'),animations:'disabled'});
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#guestPlanDownload').click()]);
    assert.equal(await download.failure(),null);assert.match(download.suggestedFilename(),/\.svg$/i);
    const svgFile=path.join(out,prefix+'.svg');await download.saveAs(svgFile);
    const svg=fs.readFileSync(svgFile,'utf8');
    assert.ok(svg.includes('<svg')&&svg.includes('data-room-key'));
    assert.ok(svg.includes('data-level-index="'+level+'"'),'downloaded plan must identify its physical floor');
    assert.ok(svg.includes('data-width-m="'+spec.width+'"')&&svg.includes('data-depth-m="'+spec.depth+'"'),'downloaded plan dimensions');
    assert.equal((svg.match(/data-courtyard-id=/g)||[]).length,spec.courtyard?1:0,'downloaded plan must preserve its actual courtyard');
    report.floorPlans.push({level,rooms:rooms.length,file:prefix+'.svg',sha256:sha256(svg)});
  }
  await page.locator('#guestPlanClose').click();await dlg.waitFor({state:'hidden'});
}
async function checkedViewport(browser,width,spec){
  const height=width===393?852:900, denied=[], errors=[];
  const ctx=await browser.newContext({viewport:{width,height},serviceWorkers:'block',acceptDownloads:true});
  ctx.setDefaultTimeout(45000);
  const brief=caseBrief(spec);
  const report={caseId:spec.id,sourceSHA,sourceTreeDirty,briefFixture:spec.fixture,briefHash:sha256(brief),expected:spec,width,height,
    evidencePrefix:spec.id+'-'+width+'-'+sourceSHA.slice(0,12),views:[],result:'INCOMPLETE'};
  let page,phase;
  function step(name){
    phase=name;report.phase=name;
    console.log(spec.id+' '+width+' '+name);
    fs.writeFileSync(path.join(out,report.evidencePrefix+'-journey.json'),JSON.stringify(report,null,2));
  }
  step('open_public_entry');
  try{
    await serve(ctx,denied);
    if(spec.baseline){step('static_phone_entry');await nativeEntry(ctx,report);}
    step('open_public_entry');page=await ctx.newPage();
    page.on('pageerror',e=>errors.push(e.name));
    await page.goto(origin+'/');await ready(page);
    const identity=await page.evaluate(()=>window.ACS_BUILD_INFO?.git_sha||null);
    assert.equal(identity,sourceSHA,'rendered build stamp must match the exact candidate or published source SHA');
    report.checkedBuild=identity;
    assert.equal(await page.locator('#login').isVisible(),false);
    const banner=await page.locator('#acsGuestBanner').boundingBox();
    if(width===393)assert.ok(banner.height<=92,'phone guest controls still dominate the model: '+banner.height);
    assert.ok(!(await page.locator('#guestSignin').isVisible()),'login CTA must not dominate the fresh entry');
    const fresh=await capture(page,report,'fresh-entry','exterior');
    if(spec.baseline){
      await inspectOrbit(page,report);
      // Open a real mesh's palette before replacing its model. A stale palette
      // retains live color handlers even after its captured mesh is detached.
      const pickMesh=()=>page.evaluate(async()=>{
        const {model,camera}=await import('/app/ui/workspace-ui-wiring.js');
        const {Raycaster,Vector2}=await import('three'),ray=new Raycaster();
        for(const ry of [.5,.4,.6,.3,.7])for(const rx of [.35,.45,.55,.25,.65]){
          const x=Math.round(innerWidth*rx),y=Math.round(innerHeight*ry);
          if(!document.elementFromPoint(x,y)?.matches('#app canvas'))continue;
          ray.setFromCamera(new Vector2(x/innerWidth*2-1,-y/innerHeight*2+1),camera);
          const hit=ray.intersectObject(model,true).find(hit=>hit.object.visible);
          const tag=hit?.object.userData.tag||'',[,floor,id]=tag.split('|'),built=window.ACS.exportModel();
          // Slabs and other shared parts carry no room: the card names rooms only.
          const level=built.levels.find(l=>'F'+l.index===floor),room=level&&built.floors[level.template]?.rooms?.find(r=>r.id===id);
          if(/^(WALL|FLOOR|DOOR|WINDOW)\|/.test(tag)&&room)return {x,y,tag};
        }
        return null;
      });
      let selected=await pickMesh();
      assert.ok(selected,'a visible current-model mesh must be available for selection');
      // A guest tap shows the plain room card over the building; the inspector is one step away.
      await page.mouse.click(selected.x,selected.y);
      const info=page.locator('#guestRoomCard'),inspector=page.locator('#acsWorkspace');
      await info.waitFor({state:'visible'});
      assert.equal(await inspector.isVisible(),false,'a room tap keeps the building visible');
      await page.locator('#guestRoomDetails').click();
      await inspector.waitFor({state:'visible'});
      await page.locator('#guestReturnToModel').click();
      await inspector.waitFor({state:'hidden'});
      // The inspector may reframe the camera: pick again from the current view.
      selected=await pickMesh();assert.ok(selected,'a visible mesh after returning from the inspector');
      await page.mouse.click(selected.x,selected.y);await info.waitFor({state:'visible'});
      assert.ok(await info.locator('.qc input[type="color"]').isVisible(),'the selected mesh must expose actual color actions');
      const roomName=await page.evaluate(tag=>{const [,floor,id]=tag.split('|'),model=window.ACS.exportModel();
        const level=model.levels.find(l=>'F'+l.index===floor);return model.floors[level.template].rooms.find(r=>r.id===id)?.name;},selected.tag);
      report.selectionRetirement={selected,text:await info.textContent()};
      assert.ok(roomName&&report.selectionRetirement.text.includes(roomName),'card must name the room actually clicked');
      step('warehouse_cutaway');await menu(page,'guestWarehouse');
      await page.waitForFunction(()=>window.ACS.exportModel().site.w===120);
      report.selectionRetirement.after=await page.evaluate(()=>({hidden:document.getElementById('guestRoomCard').hidden,children:document.getElementById('guestRoomColours').childElementCount,
        info:document.getElementById('info').childElementCount}));
      assert.deepEqual(report.selectionRetirement.after,{hidden:true,children:0,info:0},'replacing the model must retire its old palette and captured color actions');
      const warehouse=await capture(page,report,'warehouse-workfloor','cutaway');
      assert.ok(warehouse.visibleRackSections>0,'visible racks must expose the purpose of the cutaway');
      const beforeToggle=await idleFrames(page);
      step('warehouse_exterior');await page.locator('#guestViewToggle').click();
      await capture(page,report,'warehouse-exterior','exterior');
      const afterToggle=await idleFrames(page);
      report.toggleFrames={before:beforeToggle,after:afterToggle};
      console.log(report.caseId+' '+report.width+' toggle counters '+JSON.stringify(report.toggleFrames));
      assert.ok(afterToggle.draws>beforeToggle.draws&&afterToggle.rendererFrames>beforeToggle.rendererFrames,'cutaway toggle must redraw then settle');
      await cameraControl(page,'bird');await capture(page,report,'warehouse-aerial','aerial');
      await cameraControl(page,'arch');await capture(page,report,'warehouse-eye-level','street');
      await detailAndInterior(page,report,'warehouse');
    }
    step('complete_arabic_brief');await menu(page,'guestCreate');
    await page.locator('#descText').fill(brief);await page.locator('#genText').click();
    await page.locator('#guestConfirm[data-mode="confirm"]').waitFor();await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(expected=>{
      const model=window.ACS.exportModel(),apartment=model?.meta?.acs_apartment;
      return apartment?.source==='local_brief'&&apartment.units_total===expected.units&&
        model.site?.w===expected.width&&model.site?.d===expected.depth&&model.levels?.filter(level=>level.kind!=='roof').length===expected.levels;
    },spec,{timeout:45000});
    await closeProjectPanel(page,width);
    const model=await page.evaluate(()=>window.ACS.exportModel());
    report.model=inspectApartment(model,spec);report.modelHash=sha256(JSON.stringify(model));
    step('actual_model_download');
    const [modelDownload]=await Promise.all([page.waitForEvent('download'),menu(page,'guestExport')]);
    assert.equal(await modelDownload.failure(),null);
    const jsonFile=path.join(out,report.evidencePrefix+'-apartment.json');
    await modelDownload.saveAs(jsonFile);
    const exported=JSON.parse(fs.readFileSync(jsonFile,'utf8'));
    assert.deepEqual(inspectApartment(exported,spec),report.model);
    for(const k of Object.keys(model.floors)){
      assert.deepEqual(exported.floors[k].rooms.map(r=>r.rect),model.floors[k].rooms.map(r=>r.rect));
    }
    report.downloadHash=sha256(fs.readFileSync(jsonFile));
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,'downloading JSON modified the selected model');
    step('housing_exterior');const exterior=await capture(page,report,'apartment-exterior','exterior');
    assert.ok(exterior.kinds.WINDOW>=6 && exterior.kinds.DOOR>=6,'real building window/door meshes required');
    for(let i=0;i<spec.levels;i++)assert.ok(exterior.floors.includes('F'+i),'whole occupied building visible through requested floor '+i);
    if(spec.courtyard)assertCourtyardSurfaces(exterior.floorSurfaces,report.model.courtyard,'rendered exterior');
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
    const groundRooms=model.floors[model.levels.find(level=>level.index===0).template].rooms;
    const lobby=groundRooms.find(room=>room.id==='lobby');
    const porch=groundRooms.find(room=>room.id==='entrance_porch');
    const entryDoor=lobby.doors.find(door=>contains(porch.rect,doorExit(lobby.rect,door)));
    const entryPoint=doorExit(lobby.rect,entryDoor,0);
    assert.equal(exterior.entranceDoors.length,1,'the rendered model must contain one actual main entrance leaf');
    const renderedEntry=exterior.entranceDoors[0];
    assert.ok(near(renderedEntry.center[0],entryPoint[0])&&near(renderedEntry.center[2],entryPoint[1]),'rendered entrance must follow the selected model instead of a stale facade');
    const along=spec.entrance==='N'||spec.entrance==='S'?0:2;
    assert.ok(near(renderedEntry.size[along],entryDoor.width)&&renderedEntry.size[2-along]<.1,'entrance mesh must face the requested compass direction');

    for(const level of report.model.levels){
      assertWallEnvelope(exterior.wallBounds['F'+level.level],level.level,spec);
    }
    await cameraControl(page,'arch');await capture(page,report,'apartment-eye-level','street');
    await cameraControl(page,'bird');await capture(page,report,'apartment-aerial','aerial');
    await detailAndInterior(page,report,'apartment');
    step('housing_cutaway');await page.locator('#guestViewToggle').click();
    await capture(page,report,'apartment-cutaway','cutaway');
    step('upper_floor_views');await upperFloorViews(page,report,spec);
    step('apartment_plans');await floorPlans(page,report,spec,model);
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,'presentation state modified the selected model');
    if(width===1440){
      step('download_glb');await modelGLB(page,report,spec);
      assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,'GLB export modified the selected source model');
    }
    if(spec.baseline){
      step('separate_example');await page.goto(origin+'/?guest=1&example=apartment-20x25');await ready(page);
      assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_apartment_20x25_v1');
      inspectApartment(await page.evaluate(()=>window.ACS.exportModel()));
    }
    assert.deepEqual(denied,[]);assert.deepEqual(errors,[]);
    report.forbiddenRequests=denied.length;report.result='PASS';return report;
  }catch(e){
    report.result='FAIL';report.phase=phase;report.diagnostic=e.message.slice(0,700);report.errors=errors;
    if(page)await page.screenshot({path:path.join(out,report.evidencePrefix+'-failure.png'),timeout:8000}).catch(()=>{});
    return report;
  }
  finally{
    report.forbiddenRequests=denied.length;report.blockedRequests=denied;report.errors=errors;
    fs.writeFileSync(path.join(out,report.evidencePrefix+'-journey.json'),JSON.stringify(report,null,2));await ctx.close();
  }
}
async function main(){
  fs.mkdirSync(out,{recursive:true});
  const configured=process.env.ACS_APARTMENT_VIEWPORT;
  if(configured!==undefined && !['393','1440'].includes(configured))throw Error('ACS_APARTMENT_VIEWPORT must be 393 or 1440');
  const widths=configured===undefined?[393,1440]:[Number(configured)];
  const selectedCase=process.env.ACS_APARTMENT_CASE;
  if(selectedCase!==undefined&&!CASES.some(spec=>spec.id===selectedCase))throw Error('ACS_APARTMENT_CASE must be one of '+CASES.map(spec=>spec.id).join(', '));
  const cases=selectedCase===undefined?CASES:CASES.filter(spec=>spec.id===selectedCase);
  const quickLook=live&&cases.some(spec=>spec.baseline)?await publishedQuickLook():null;
  const b=await PW.launch();
  try{
    const runs=[];
    for(const spec of cases)for(const width of widths)runs.push(await checkedViewport(b,width,spec));
    fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({scope:live?'published':'candidate assets',sourceSHA,sourceTreeDirty,browser:b.version(),publishedQuickLook:quickLook,host:{os:os.platform(),release:os.release(),cpu:os.cpus()[0]?.model,logicalCpuCount:os.availableParallelism(),physicalPhone:false},syntheticBrief:true,requestedCases:cases.map(spec=>spec.id),runs},null,2));
    const failures=runs.filter(run=>run.result!=='PASS');
    if(failures.length)throw Error(failures.map(run=>run.caseId+' '+run.width+' '+run.phase+' '+run.diagnostic).join('\n'));
    console.log('PASS public apartment: '+cases.map(spec=>spec.id).join(', ')+' at '+widths.join(', ')+', real floor and facade geometry, connected rooms, requested courtyard opening, every floor SVG, unchanged JSON/GLB source, zero private/provider requests');
  }finally{await b.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exitCode=1;});
module.exports={CASES,caseBrief,inspectApartment,assertCourtyardSurfaces,readGLBGeometry,serve,menu,runtime,cameraControl,modelGLB,origin,sourceSHA,sourceTreeDirty};
