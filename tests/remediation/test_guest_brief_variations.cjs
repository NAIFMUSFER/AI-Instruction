'use strict';
// An independent acquisition from an empty guest project for each design, followed by
// edits through its visible controls. Only read-only observations use the scene API.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const PW = require('../../tools/pw_chromium.js');
const { serve, menu, runtime, cameraControl, modelGLB, origin, sourceSHA, sourceTreeDirty } = require('./test_public_apartment_journey.cjs');

const output = path.resolve(process.env.ACS_APARTMENT_EVIDENCE || 'logs/public-apartment', 'variations');
const cases = [
  { name:'01-apartment', text:'أبغى عمارة سكنية، عرض المبنى ٢٠ متر وعمقه ٢٥ متر، ثلاثة أدوار شاملة الأرضي، وفي كل دور شقتين', width:20, depth:25, floors:3 },
  { name:'02-before', text:'أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور', width:24, depth:28, floors:4 },
  { name:'03-courtyard', text:'خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق', width:24, depth:28, floors:4, edit:true, courtyard:true },
  { name:'04-new-brief', text:'ودي بعمارة سكنية في حي الرمال بالرياض، عرضها ٢٢ متر وعمقها ٢٧ متر، دورين شامل الأرضي، في كل دور شقتين، ومدخل العمارة من الشمال', width:22, depth:27, floors:2, entrance:'N' },
  { name:'05-new-entrance', text:'خلّ المدخل من الغرب', width:22, depth:27, floors:2, edit:true, entrance:'W' },
];
const close = (a,b) => Math.abs(a-b)<0.012;
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
const write = (dir,name,body) => fs.writeFileSync(path.join(dir,name), typeof body==='string'?body:JSON.stringify(body,null,2));
const opposite = {N:'S',S:'N',W:'E',E:'W'};

function opening(room,door){
  const [x,z,w,d]=room.rect;
  switch(door.edge){
    case 'N': return [x+door.offset,z];
    case 'S': return [x+door.offset,z+d];
    case 'E': return [x+w,z+door.offset];
    case 'W': return [x,z+door.offset];
    default: throw Error('Invalid door wall on '+room.id);
  }
}
function overlap(a,b){
  return Math.max(0,Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0]))
    * Math.max(0,Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1]));
}
function reachable(adj,start,allowed){
  const visited=new Set(),pending=[start];
  while(pending.length){
    const id=pending.pop();
    if(visited.has(id)||!allowed.has(id))continue;
    visited.add(id);
    for(const next of adj.get(id)||[])if(allowed.has(next))pending.push(next);
  }
  return visited;
}
function inspect(model,c){
  const levels=model.levels.filter(level=>level.kind!=='roof');
  assert.equal(levels.length,c.floors,'occupied levels');
  const expectedEdges=[0,0,c.width,c.depth], floorResults=[];
  let voidRect, footprintVoid, entrance;
  for(const [i,level] of levels.entries()){
    const floor=model.floors[level.template], {rooms}=floor;
    const xs=rooms.flatMap(r=>[r.rect[0],r.rect[0]+r.rect[2]]);
    const zs=rooms.flatMap(r=>[r.rect[1],r.rect[1]+r.rect[3]]);
    const h=model.wall_t/2;
    const edges=[Math.min(...xs)-h,Math.min(...zs)-h,Math.max(...xs)+h,Math.max(...zs)+h];
    assert.ok(edges.every((v,k)=>close(v,expectedEdges[k])), 'wall faces in the plan '+JSON.stringify(edges));
    const courts=floor.courtyards||[];
    assert.equal(courts.length,c.courtyard?1:0,'open courtyards on storey '+i);
    if(c.courtyard){
      const rect=courts[0].clear_rect,footprint=courts[0].rect;
      assert.equal(courts[0].open_to_sky,true);
      assert.ok(Array.isArray(rect)&&rect.length===4,'courtyard must declare its actual clear opening');
      assert.ok(rect.every(Number.isFinite)&&rect[2]>1&&rect[3]>1);
      assert.ok(rect[0]>0 && rect[1]>0 && rect[0]+rect[2]<c.width && rect[1]+rect[3]<c.depth,'courtyard inside perimeter');
      assert.ok(rooms.every(r=>overlap(r.rect,rect)<.01),'occupied floor intersects the opening');
      if(voidRect)assert.deepEqual(rect,voidRect,'courtyard must align vertically');
      if(footprintVoid)assert.deepEqual(footprint,footprintVoid,'reserved courtyard footprint must align vertically');
      assert.deepEqual(model.meta.acs_apartment.courtyard.rect_m,rect,'floor opening and declared clear dimensions must agree');
      voidRect=rect;footprintVoid=footprint;
    }
    const doors = rooms.flatMap(room=>(room.doors||[]).map(door=>({room,door,point:opening(room,door)})));
    const adj = new Map(rooms.map(r=>[r.id,new Set()]));
    let exteriorCourtDoors=0;
    for(const {room,door,point} of doors){
      const peer=doors.find(other=>other.room!==room && other.door.edge===opposite[door.edge]
        && close(door.width,other.door.width) && point.every((v,k)=>close(v,other.point[k])));
      if(peer){
        adj.get(room.id).add(peer.room.id);
      }else{
        assert.ok(i===0&&c.courtyard&&room.id==='courtyard_gallery_north'&&door.id==='court_ground_door'&&room.role==='corridor'&&!room.unit_id,'unpaired door on storey '+i+': '+room.id+'/'+door.id);
        const [cx,cz,cw,cd]=footprintVoid;
        const dx={E:.02,W:-.02}[door.edge]||0, dz={S:.02,N:-.02}[door.edge]||0;
        assert.ok(point[0]+dx>cx && point[0]+dx<cx+cw && point[1]+dz>cz && point[1]+dz<cz+cd,'ground exit opens into courtyard');
        const step=h+.02,[clearX,clearZ,clearW,clearD]=voidRect;
        const px=point[0]+({E:step,W:-step}[door.edge]||0),pz=point[1]+({S:step,N:-step}[door.edge]||0);
        assert.ok(px>clearX&&px<clearX+clearW&&pz>clearZ&&pz<clearZ+clearD,'garden door must reach actual clear space beyond its wall thickness');
        exteriorCourtDoors++;
      }
    }
    assert.equal(exteriorCourtDoors,i===0&&c.courtyard?1:0);
    const stair=rooms.find(r=>r.role==='stairs'), lobby=rooms.find(r=>r.role==='lobby');
    assert.ok(stair&&lobby,'common stair and lobby must exist on every occupied floor');
    const shared=new Set(rooms.filter(room=>!room.unit_id).map(room=>room.id));
    const commonAccess=reachable(adj,lobby.id,shared);
    assert.equal(commonAccess.size,shared.size,'all shared rooms must be connected without crossing a private apartment');
    assert.ok(commonAccess.has(stair.id),'stair landing must be reachable through shared circulation');
    if(i<levels.length-1)assert.ok(stair.objects?.some(o=>o.form==='u_return' && o.stair.target_level_index===levels[i+1].index),'stair flight reaches the next floor');
    const entries=rooms.filter(r=>r.role==='entry');
    assert.equal(entries.length,2,'apartment entrances per floor');
    assert.equal(new Set(entries.map(r=>r.unit_id)).size,2);
    for(const entry of entries){
      assert.ok([...adj.get(entry.id)].some(id=>commonAccess.has(id)),'each apartment entrance must be accessible from the common landing through shared circulation');
      const unit=rooms.filter(r=>r.unit_id===entry.unit_id);
      const allowed=new Set(unit.map(r=>r.id)),visited=reachable(adj,entry.id,allowed);
      assert.equal(visited.size,unit.length,'rooms must be accessible within '+entry.unit_id);
      assert.equal(unit.filter(r=>r.role==='bedroom'&&r.windows?.length).length,3,'daylit bedrooms');
    }
    if(i===0){
      const porch=rooms.find(r=>r.role==='porch');
      assert.ok(porch&&adj.get(porch.id).has(lobby.id),'building entrance connects to lobby');
      const [x,z,w,d]=porch.rect;
      const sides={N:z-h,S:c.depth-(z+d+h),W:x-h,E:c.width-(x+w+h)};
      entrance=Object.keys(sides).find(key=>close(sides[key],0));
      assert.equal(entrance,c.entrance||'N','measured public entrance edge');
    }
    floorResults.push({index:level.index,elevation:level.elevation,apartmentEntrances:entries.length,
      rooms:rooms.length,doorPairs:(doors.length-exteriorCourtDoors)/2,outerFaces:edges,courtyard:floor.courtyards?.[0]?.rect||null});
  }
  return {levels:floorResults.length,units:floorResults.reduce((n,f)=>n+f.apartmentEntrances,0),entrance,voidRect:voidRect||null,floors:floorResults};
}

async function download(page,click,dir,file){
  const [item]=await Promise.all([page.waitForEvent('download'),click()]);
  const target=path.join(dir,file);
  await item.saveAs(target);
  assert.equal(await item.failure(),null);
  return fs.readFileSync(target);
}
async function submit(page,c){
  if(c.edit)await menu(page,'guestRevise');
  const input=page.locator(c.edit?'#guestRevisionText':'#descText');
  await input.fill(c.text);
  const seq=await page.evaluate(()=>window.__acceptanceGenerations.length);
  await page.locator(c.edit?'#guestApplyRevision':'#genText').click();
  await page.waitForFunction(n=>window.__acceptanceGenerations.length>n,seq,{timeout:90000});
  const event=await page.evaluate(n=>window.__acceptanceGenerations[n],seq);
  assert.equal(event.ok,true,event.message||'generation failed');
  await page.waitForFunction(()=>Boolean(window.ACS?.exportModel?.()?.meta?.acs_apartment),null,{timeout:45000});
  const panel=page.locator('#projectPanelClose');
  if(await panel.isVisible())await panel.click();
}
async function camera(page,name){
  await cameraControl(page,name);
  const mobile=page.locator('#mobileToolsToggle');
  if(await mobile.isVisible() && await mobile.getAttribute('aria-expanded')==='true')await mobile.click();
}
async function shot(page,dir,name){
  await page.evaluate(()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))));
  await page.screenshot({path:path.join(dir,name),animations:'disabled'});
}
// Intersect triangles in the visible building itself. The separate site plate is
// ground outside the building group, so it is intentionally absent from this query.
async function probeSky(page,points){
  return page.evaluate(async points=>{
    const {Raycaster,Vector3}=await import('three');
    const {registry}=await import('/app/ui/workspace-ui-wiring.js');
    const meshes=Object.values(registry).flatMap(group=>group.meshes.filter(mesh=>mesh.visible));
    for(const mesh of meshes)mesh.updateWorldMatrix(true,false);
    return points.map(([x,z])=>{
      const ray=new Raycaster(new Vector3(x,100,z),new Vector3(0,-1,0),0,99.95);
      const hits=ray.intersectObjects(meshes,false);
      return {x,z,first:hits[0]?{mesh:hits[0].object.name,y:hits[0].point.y}:null};
    });
  },points);
}
function sampleCourt([x,z,w,d]){
  return [.15,.5,.85].flatMap(rx=>[.15,.5,.85].map(rz=>[x+w*rx,z+d*rz]));
}
async function plan(page,c,dir){
  await page.locator('#guestPlan').click();
  const dialog=page.locator('#guestPlanDialog');await dialog.waitFor({state:'visible'});
  await page.locator('#guestPlanFloor').selectOption('1');
  const drawing=page.locator('#guestPlanViewport svg');
  assert.equal(await drawing.getAttribute('data-level-index'),'1');
  assert.ok(close(Number(await drawing.getAttribute('data-width-m')),c.width));
  assert.ok(close(Number(await drawing.getAttribute('data-depth-m')),c.depth));
  assert.ok(await drawing.locator('[data-opening-id]').count()>6);
  assert.equal(await drawing.locator('[data-courtyard-id]').count(),c.courtyard?1:0);
  await shot(page,dir,'upper-plan.png');
  const svg=await download(page,()=>page.locator('#guestPlanDownload').click(),dir,'upper-plan.svg');
  assert.ok(svg.includes('data-room-key'));
  await page.locator('#guestPlanClose').click();await dialog.waitFor({state:'hidden'});
}
async function run(browser,width){
  const dir=path.join(output,String(width)+'-'+sourceSHA.slice(0,12));fs.mkdirSync(dir,{recursive:true});
  const height=width===393?852:900, denied=[], errors=[];
  const ctx=await browser.newContext({viewport:{width,height},hasTouch:width===393,isMobile:width===393,
    deviceScaleFactor:1,serviceWorkers:'block',acceptDownloads:true});
  ctx.setDefaultTimeout(45000);
  const report={sourceSHA,sourceTreeDirty,viewport:{width,height},browser:browser.version(),origin,cases:[],result:'INCOMPLETE'};
  let page,dirNow=dir,previous;
  try{
    await serve(ctx,denied);
    await ctx.addInitScript(()=>{
      window.__acceptanceGenerations=[];
      window.addEventListener('acs:local-generation',e=>window.__acceptanceGenerations.push({ok:e.detail?.ok,message:e.detail?.message}));
    });
    page=await ctx.newPage();
    page.on('pageerror',error=>errors.push(error.name+': '+error.message));
    for(const c of cases){
      dirNow=path.join(dir,c.name);fs.mkdirSync(dirNow,{recursive:true});
      write(dirNow,'request.txt',c.text);
      console.log(width+' '+c.name);
      if(!c.edit){
        await page.goto(origin+'/?guest=1&new=1');
        await page.locator('#acsGuestBanner[data-recovery="complete"]').waitFor();
        const blank=await page.evaluate(()=>!window.ACS?.exportModel?.());
        assert.ok(blank,'start with an empty model');
        assert.equal(await page.locator('#descText').inputValue(),'');
      }
      const project=new URL(page.url()).searchParams.get('project');
      assert.ok(project,'address must identify this particular guest project');
      if(c.edit)assert.equal(project,previous.project,'edit remained in same guest project');
      else if(previous)assert.notEqual(project,previous.project,'new independent guest project');
      const build=await page.evaluate(()=>window.ACS_BUILD_INFO?.git_sha||null);
      if(process.env.ACS_APARTMENT_LIVE==='1')assert.equal(build,process.env.ACS_VERIFY_EXPECT_SHA);
      const row={name:c.name,request:c.text,project,build,sourceSHA};report.cases.push(row);
      await submit(page,c);
      const bytes=await download(page,()=>menu(page,'guestExport'),dirNow,'model.json');
      const model=JSON.parse(bytes), active=await page.evaluate(()=>window.ACS.exportModel());
      const expectedFloors=structuredClone(active.floors);
      for(const [template,floor] of Object.entries(expectedFloors)){
        floor.rooms.forEach((room,index)=>{room.space_id??='bld_0.'+template+'.'+(room.id||('sp_'+index));});
      }
      assert.deepEqual(model.floors,expectedFloors,'download retains all selected floor geometry, including its derived export IDs');
      Object.assign(row,inspect(model,c));
      row.modelHash=digest(bytes);
      await camera(page,'arch');await shot(page,dirNow,'facade.png');
      await camera(page,'bird');await shot(page,dirNow,'aerial.png');
      const scene=await runtime(page);
      assert.ok(scene.triangles>0&&scene.kinds.WALL>0&&scene.kinds.DOOR>0&&scene.kinds.WINDOW>0,'rendered building');
      row.outerMeshBounds={};
      for(const level of row.floors){
        const bounds=scene.wallBounds['F'+level.index];
        assert.ok(bounds&&[bounds[0],bounds[2],bounds[3],bounds[5]].every((v,i)=>close(v,[0,0,c.width,c.depth][i])),'3D wall envelope on floor '+level.index);
        row.outerMeshBounds['F'+level.index]=bounds;
      }
      if(c.name==='02-before'||c.courtyard){
        await camera(page,'top');await shot(page,dirNow,'top.png');
        // A control ray through an occupied roof must return a hit with either scheme.
        const control=await probeSky(page,[[c.width*.15,c.depth*.4]]);
        assert.ok(control[0].first?.y>=(c.floors-1)*3.4,'control ray intersects an upper surface');
        if(c.courtyard){
          row.skyRays=await probeSky(page,sampleCourt(row.voidRect));
          assert.ok(row.skyRays.every(p=>!p.first),'courtyard obstructed by '+JSON.stringify(row.skyRays));
        }else{
          const checks=await probeSky(page,[[c.width*.50,c.depth*.58]]);
          assert.ok(checks[0].first?.y>=(c.floors-1)*3.4,'sealed roof before the requested edit');
          row.skyRays=checks;
        }
        await menu(page,'guestFloors');await page.locator('#floors [data-floor="F1"]').click();
        const panel=page.locator('#projectPanelClose');if(await panel.isVisible())await panel.click();
        const cut=await runtime(page);
        assert.equal(cut.state.mode,'cutaway');assert.deepEqual(cut.floors,['F1']);
        await shot(page,dirNow,'upper-cutaway.png');
      }
      if(c.name==='01-apartment'){
        await menu(page,'guestInterior');
        const inside=await runtime(page);
        assert.equal(inside.state.mode,'interior');assert.match(inside.state.focusSource,/F0/);
        await shot(page,dirNow,'interior.png');
      }
      await plan(page,c,dirNow);
      if(width===1440)await modelGLB(page,row,{directory:dirNow,filename:'building.glb',width:c.width,depth:c.depth,floors:c.floors,courtyardRect:row.voidRect});
      assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),active,'plan and GLB export did not alter the selected source model');
      if(c.edit)assert.notEqual(row.modelHash,previous.modelHash,'an edit changed exported design');
      previous=row;
      write(dirNow,'measurements.json',row);
    }
    assert.deepEqual(denied,[]);assert.deepEqual(errors,[]);report.result='PASS';
  }catch(error){
    report.result='FAIL';report.error=String(error.stack||error);report.pageErrors=errors;
    if(page)await page.screenshot({path:path.join(dirNow,'failure.png'),timeout:8000}).catch(()=>{});
    throw error;
  }finally{
    write(dir,'summary.json',report);await ctx.close();
  }
}
async function main(){
  const env=process.env.ACS_APARTMENT_VIEWPORT;
  assert.ok(!env||['393','1440'].includes(env));
  const widths=env?[Number(env)]:[393,1440];
  const browser=await PW.launch();
  try{for(const width of widths)await run(browser,width);}finally{await browser.close();}
}
if(require.main===module)main().catch(error=>{console.error(error);process.exitCode=1;});
module.exports={inspect,cases};
