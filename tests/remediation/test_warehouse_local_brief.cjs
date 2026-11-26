'use strict';
// Local (guest) warehouse generator: what a Saudi operator asked for must be
// what the plan contains — sides, dock counts, enterable rack aisles, real
// personnel/exit doors, a truck yard inside the plot, clear height, city and a
// sorting area. Runs the shipped viewer.js in a Node vm; no DOM, no provider.
//   node tests/remediation/test_warehouse_local_brief.cjs
const assert=require('node:assert/strict'),vm=require('node:vm');
const APP=require('../lib/app_source.js');
const ctx={structuredClone,TextEncoder};vm.createContext(ctx);
vm.runInContext(APP.nodeBundle(['core/stairs.mjs','core/context-details.mjs','core/viewer.js','core/standards.js','core/disciplines.js']),ctx);
const run=src=>vm.runInContext(src,ctx);
ctx.__args=null;
const gen=(text,w,d)=>{ctx.__args=[text,w,d];return JSON.parse(JSON.stringify(run('warehouseFromText(__args[0],__args[1],__args[2],{}).building')));};
const genError=(text,w,d)=>{ctx.__args=[text,w,d];try{run('warehouseFromText(__args[0],__args[1],__args[2],{})');}catch(e){return e;}return null;};
// ACS_TEST_CONTINUE=1 reports every failing check (used to show the pre-fix state).
const keepGoing=process.env.ACS_TEST_CONTINUE==='1';
let checks=0,failed=0;
const ok=(name,cond,detail)=>{
  if(cond){checks++;console.log('PASS '+name);return;}
  if(!keepGoing) assert.ok(cond,name+(detail?' — '+detail:''));
  failed++;console.log('FAIL '+name+(detail?' — '+String(detail).slice(0,160):''));
};
const section=(name,fn)=>{try{fn();}catch(e){if(!keepGoing)throw e;failed++;console.log('FAIL '+name+' — '+String(e.message).slice(0,160));}};

const distribution=side=>`أبغى مستودع توزيع للمواد الغذائية الجافة في الرياض، الأرض 80×50 متر والارتفاع الصافي 11 متر. البضاعة كراتين على بالتات. الاستلام من الجهة ${side} فيه 4 أرصفة، بعده منطقة فحص الجودة، ثم تخزين بالتات على رفوف عالية، ومنطقة التقاط الطلبات، ومنطقة تغليف، ومنطقة تجهيز الشحن، و4 أرصفة صادر من الجهة الجنوبية، ومكتب إداري يطل على الصالة.`;
const spareParts=side=>`عندي مستودع قطع غيار سيارات في جدة، الأرض 50×35 متر والارتفاع الصافي 8 متر. نستلم البضاعة من الجهة ${side} برصيفين، ونفحص القطع ونسجلها، بعدين نخزنها على أرفف متوسطة للقطع المتوسطة وصناديق للقطع الصغيرة، وفيه منطقة التقاط وتغليف وشحن للعملاء والورش، ومكتب للمبيعات والمخزون.`;
const dammam=side=>`نبي مستودع مبرد للخضار في الدمام ٦٠×٤٠ م بارتفاع صافي ١٠ م، الاستلام من الجهة ${side} برصيفين، وتخزين بالتات على رفوف، ومنطقة فرز، وشحن من الجهة الشمالية بثلاث أرصفة، ومكتب صغير.`;
const reach='أبغى مستودع توزيع في الرياض، الأرض 80×50 متر والارتفاع الصافي 11 متر. نشتغل برافعات ريتش ترك وعرض الممر بين الرفوف 3 متر. الاستلام من الجهة الشمالية فيه 4 أرصفة، ثم تخزين بالتات، ومنطقة تجهيز الشحن، و4 أرصفة صادر من الجهة الجنوبية.';

const rooms=b=>b.floors[b.levels[0].template].rooms;
const envelope=b=>rooms(b).find(r=>r.id==='envelope');
function docks(b,role){
  return rooms(b).filter(r=>(r.docks||[]).length&&(role==='receiving'?r.id==='inbound_docks':r.id==='outbound_docks'))
    .flatMap(r=>r.docks.map(d=>({room:r,dock:d})));
}
const onEdge=(rect,edge,env)=>Math.abs({N:rect[1]-env[1],S:rect[1]+rect[3]-env[1]-env[3],W:rect[0]-env[0],E:rect[0]+rect[2]-env[0]-env[2]}[edge])<0.02;
// Mirror of the shipped compiler's rack rows (viewer.js buildRacks + pqRackBlock).
const RACK={pallet:[1.1,3.4],shelf:[0.6,1.4],bin:[0.45,1.1],flow:[1.2,1.6],cage:[1.0,1.2]};
function rackRows(room,R){
  const [rx,rz,rw,rd]=room.rect,[dep0,ais0]=RACK[R.kind]||RACK.pallet,depth=+R.depth||dep0,aisle=+R.aisle||ais0;
  const ox=Math.min(Math.max(+R.x||0,0),rw),oz=Math.min(Math.max(+R.z||0,0),rd);
  const w=Math.min(+R.w||rw-ox,rw-ox),d=Math.min(+R.d||rd-oz,rd-oz),dirX=R.dir!=='z';
  const across=dirX?d:w,pitch=depth+aisle,n=Math.max(1,Math.floor((across+aisle)/pitch)),rows=[];
  for(let r=0;r<n;r++){const off=r*pitch;if(off>across-0.05)break;
    rows.push(dirX?[rx+ox,rz+oz+off,w,depth]:[rx+ox+off,rz+oz,depth,d]);}
  return {rows,aisle,dirX};
}
// Free length beyond each end of every aisle between two rack rows, measured
// along the run until another rack row, a walled room or the building wall.
function aisleAccess(b){
  const env=envelope(b).rect, all=[];
  for(const r of rooms(b)) for(const R of r.racks||[]) all.push({room:r,R,...rackRows(r,R)});
  const blockers=all.flatMap(g=>g.rows).concat(rooms(b).filter(r=>r.id!=='envelope'&&r.walls&&r.walls!=='none').map(r=>r.rect));
  const out=[];
  for(const g of all){
    const sw=v=>g.dirX?v:[v[1],v[0],v[3],v[2]], E=sw(env);
    for(let i=0;i+1<g.rows.length;i++){
      const a=sw(g.rows[i]),c0=a[1]+a[3]+0.01,c1=sw(g.rows[i+1])[1]-0.01,s0=a[0],s1=a[0]+a[2];
      let lo=E[0],hi=E[0]+E[2];
      for(const k of blockers.map(sw)){ if(Math.min(c1,k[1]+k[3])-Math.max(c0,k[1])<=1e-6) continue;
        if(k[0]+k[2]<=s0+1e-6) lo=Math.max(lo,k[0]+k[2]); else if(k[0]>=s1-1e-6) hi=Math.min(hi,k[0]); }
      out.push({zone:g.room.id,kind:g.R.kind,aisle:g.aisle,ends:[s0-lo,hi-s1]});
    }
  }
  return out;
}
function bandPassage(b,zoneId){ // widest gap across a pallet band, perpendicular to the runs
  const env=envelope(b).rect,g=rooms(b).filter(r=>r.id===zoneId).flatMap(r=>(r.racks||[]).map(R=>rackRows(r,R)));
  if(!g.length) return null;const dirX=g[0].dirX,sw=v=>dirX?v:[v[1],v[0],v[3],v[2]],E=sw(env);
  const rows=g.flatMap(x=>x.rows).map(sw),c0=Math.min(...rows.map(r=>r[1])),c1=Math.max(...rows.map(r=>r[1]+r[3]));
  const blk=rows.concat(rooms(b).filter(r=>r.id!=='envelope'&&r.walls&&r.walls!=='none').map(r=>sw(r.rect)))
    .filter(k=>Math.min(c1,k[1]+k[3])-Math.max(c0,k[1])>1e-6).map(k=>[k[0],k[0]+k[2]]).sort((p,q)=>p[0]-q[0]);
  let cur=E[0],best=0;for(const [p,q] of blk){best=Math.max(best,p-cur);cur=Math.max(cur,q);}return Math.max(best,E[0]+E[2]-cur);
}
function doorPoint(env,d){const [x,z,w,h]=env;return {N:[x+d.offset,z],S:[x+d.offset,z+h],W:[x,z+d.offset],E:[x+w,z+d.offset]}[d.edge];}

// 1 — receiving and dispatch sides are honoured, and change the model.
section('1 — receiving and dispatch sides are honoured, and change the model.',()=>{
const sides={N:'الشمالية',E:'الشرقية',W:'الغربية'},bySide={};
for(const [edge,word] of Object.entries(sides)){
  const b=gen(distribution(word),80,50),env=envelope(b).rect;bySide[edge]=JSON.stringify(rooms(b));
  const rec=docks(b,'receiving'),shp=docks(b,'shipping');
  ok('distribution: receiving docks on the requested '+edge+' wall',rec.length&&rec.every(x=>x.dock.edge===edge&&onEdge(x.room.rect,edge,env)),JSON.stringify(rec.map(x=>x.dock.edge)));
  ok('distribution: dispatch docks stay on the requested south wall ('+edge+')',shp.length&&shp.every(x=>x.dock.edge==='S'&&onEdge(x.room.rect,'S',env)));
  ok('distribution: dock counts 4 + 4 as written ('+edge+')',rec.reduce((s,x)=>s+x.dock.count,0)===4&&shp.reduce((s,x)=>s+x.dock.count,0)===4);
  ok('distribution: coverage names the requested receiving side ('+edge+')',b.meta.requirements.some(q=>q.where==='inbound_docks'&&q.req.includes(word)));
}
ok('changing only the receiving side changes the plan',new Set(Object.values(bySide)).size===3);
for(const [edge,word] of [['W','الغربية'],['E','الشرقية']]){
  const b=gen(spareParts(word),50,35),env=envelope(b).rect,rec=docks(b,'receiving'),shp=docks(b,'shipping');
  ok('spare parts: receiving on '+edge+' with 2 docks («برصيفين»)',rec.length===1&&rec[0].dock.edge===edge&&rec[0].dock.count===2&&onEdge(rec[0].room.rect,edge,env));
  ok('spare parts: shipping has a dock on an external wall ('+edge+')',shp.length&&shp.every(x=>onEdge(x.room.rect,x.dock.edge,env)));
  ok('spare parts: an assumed shipping side/count is declared, not attributed to the client',
     b.meta.acs_warehouse.shipping.count_source==='assumption'&&b.meta.added.some(a=>/رصيف شحن واحد/.test(a)));
}
for(const [edge,word] of [['W','الغربية'],['E','الشرقية']]){
  const b=gen(dammam(word),60,40),env=envelope(b).rect,rec=docks(b,'receiving'),shp=docks(b,'shipping');
  ok('Dammam cold store: receiving 2 docks on '+edge,rec.length===1&&rec[0].dock.edge===edge&&rec[0].dock.count===2);
  ok('Dammam cold store: 3 dispatch docks on the north wall ('+edge+')',shp.length===1&&shp[0].dock.edge==='N'&&shp[0].dock.count===3&&onEdge(shp[0].room.rect,'N',env));
  ok('Dammam: coverage claims 2 receiving docks, not 6',b.meta.requirements.some(q=>q.where==='inbound_docks'&&/\(2\)/.test(q.req)));
}

});
// 2 — every rack aisle can be entered; aisle width follows the stated equipment.
section('2 — every rack aisle can be entered; aisle width follows the stated equipment.',()=>{
for(const [label,b] of [['distribution N',gen(distribution('الشمالية'),80,50)],['distribution E',gen(distribution('الشرقية'),80,50)],
                        ['spare parts W',gen(spareParts('الغربية'),50,35)],['Dammam W',gen(dammam('الغربية'),60,40)],
                        ['sample 120×80',JSON.parse(JSON.stringify(run('warehouseModel(120,80,{clear:12})')))]]){
  const acc=aisleAccess(b);
  ok(label+': rack aisles exist',acc.length>0);
  for(const a of acc) ok(label+': '+a.zone+' '+a.kind+' aisle opens at an end at least '+(a.kind==='pallet'?'its width':'1.2 m'),
     Math.max(...a.ends)>=(a.kind==='pallet'?a.aisle:1.2)-1e-6,JSON.stringify(a.ends));
  const pallet=rooms(b).find(r=>(r.racks||[]).some(R=>R.kind==='pallet'));
  if(pallet) ok(label+': a forklift can cross the pallet band (≥ 3.4 m passage)',bandPassage(b,pallet.id)>=3.4-1e-6,String(bandPassage(b,pallet.id)));
}
{
  const b=gen(reach,80,50),pal=rooms(b).flatMap(r=>r.racks||[]).filter(R=>R.kind==='pallet');
  ok('reach truck + «عرض الممر 3 متر»: pallet aisle is 3 m',pal.length&&pal.every(R=>R.aisle===3),JSON.stringify(pal.map(R=>R.aisle)));
  ok('reach truck: the dock count is not taken from «3 متر»',docks(b,'receiving')[0].dock.count===4);
  const d=gen(distribution('الشمالية'),80,50);
  ok('no equipment stated: default aisle is declared as an assumption',d.meta.acs_warehouse.rack_aisle_source==='assumption'&&d.meta.added.some(a=>/نوع الرافعة/.test(a)));
  const r2=gen(reach.replace(' وعرض الممر بين الرفوف 3 متر',''),80,50);
  ok('reach truck without a width: equipment default 2.9 m, declared',r2.meta.acs_warehouse.rack_aisle_m===2.9&&r2.meta.acs_warehouse.equipment==='reach');
}

});
// 3 — personnel doors and emergency exits are openings in the external wall.
section('3 — personnel doors and emergency exits are openings in the external wall.',()=>{
for(const [label,b] of [['distribution',gen(distribution('الشمالية'),80,50)],['spare parts',gen(spareParts('الغربية'),50,35)],
                        ['sample',JSON.parse(JSON.stringify(run('warehouseModel(120,80,{clear:12})')))]]){
  const env=envelope(b),doors=env.doors||[];
  ok(label+': at least two door openings in the external wall',doors.length>=2,String(doors.length));
  const dockCuts=rooms(b).flatMap(r=>(r.docks||[]).flatMap(D=>[...Array(D.count)].map((_,i)=>{
    const c=((D.edge==='N'||D.edge==='S')?r.rect[0]:r.rect[1])+D.offset+D.pitch*i;return {edge:D.edge,a:c-D.width/2,b:c+D.width/2};})));
  for(const d of doors){const p=doorPoint(env.rect,d),u=(d.edge==='N'||d.edge==='S')?p[0]:p[1];
    ok(label+': door '+d.id+' does not collide with a dock door',dockCuts.every(c=>c.edge!==d.edge||u+d.width/2<=c.a||u-d.width/2>=c.b));}
  const signs=(env.points||[]).filter(p=>p.type==='exit');
  ok(label+': every exit sign stands at a real door',signs.length===doors.length&&signs.every(s=>doors.some(d=>{
    const p=doorPoint(env.rect,d);return Math.hypot(env.rect[0]+s.x-p[0],env.rect[1]+s.z-p[1])<1;})));
}
{
  const b=gen(distribution('الشمالية'),80,50),env=envelope(b),office=rooms(b).find(r=>r.id==='inventory_office');
  const door=(env.doors||[]).find(d=>d.id==='personnel_entrance'),p=door&&doorPoint(env.rect,door);
  ok('the office has a staff entrance from outside',p&&p[0]>=office.rect[0]-0.02&&p[0]<=office.rect[0]+office.rect[2]+0.02&&p[1]>=office.rect[1]-0.02&&p[1]<=office.rect[1]+office.rect[3]+0.02);
  ok('the office has no wall of its own on that external edge',Array.isArray(office.walls)&&!office.walls.includes(door.edge));
}

});
// 4 — the building leaves a truck yard in front of every dock wall.
section('4 — the building leaves a truck yard in front of every dock wall.',()=>{
for(const [label,b] of [['distribution N',gen(distribution('الشمالية'),80,50)],['distribution E',gen(distribution('الشرقية'),80,50)],
                        ['spare parts',gen(spareParts('الغربية'),50,35)],['Dammam',gen(dammam('الغربية'),60,40)],
                        ['sample',JSON.parse(JSON.stringify(run('warehouseModel(120,80,{clear:12})')))]]){
  const env=envelope(b).rect,s=b.site,gap={N:env[1],S:s.d-env[1]-env[3],W:env[0],E:s.w-env[0]-env[2]};
  const dockEdges=new Set(rooms(b).flatMap(r=>(r.docks||[]).map(d=>d.edge)));
  ok(label+': building is smaller than the plot',env[2]*env[3]<s.w*s.d-1);
  for(const e of dockEdges) ok(label+': ≥ 12 m truck yard in front of the '+e+' docks',gap[e]>=12-1e-6,String(gap[e]));
}
{
  const e=genError('مستودع توزيع، الأرض 30×30 متر، الاستلام من الجهة الشمالية فيه 4 أرصفة، فحص الجودة، تخزين بالتات، التقاط، تغليف، و4 أرصفة صادر من الجهة الجنوبية، ومكتب.',30,30);
  ok('a plot too small for yards and program says so',e&&e.code==='LOCAL_WAREHOUSE_UNSUPPORTED'&&/الأرض|المبنى/.test(e.message),e&&e.message);
}

});
// 6 — clear height, city and a sorting area.
section('6 — clear height, city and a sorting area.',()=>{
{
  const d=gen(distribution('الشمالية'),80,50),s=gen(spareParts('الغربية'),50,35),m=gen(dammam('الغربية'),60,40);
  ok('«الارتفاع الصافي 11 متر» is the clear height',d.wall_h===11);
  ok('«بارتفاع صافي ١٠ م» is the clear height',m.wall_h===10);
  ok('spare parts clear height 8 m',s.wall_h===8);
  ok('the city is kept: الرياض / جدة / الدمام',d.meta.city==='الرياض'&&s.meta.city==='جدة'&&m.meta.city==='الدمام');
  ok('no invented city when none is written',!('city' in gen('مستودع فيه تخزين بالتات وتغليف',60,40).meta));
  ok('the clear height is not reported as rack levels',!d.meta.requirements.some(q=>/11\s*مستويات/.test(q.req)));
  ok('cold store: no «60 levels» and model levels match the report',!m.meta.requirements.some(q=>/60/.test(q.req))&&
     rooms(m).flatMap(r=>r.racks||[]).every(R=>R.levels<=10));
  ok('«منطقة فرز» is a sorting zone, not an automatic sorter',rooms(m).some(r=>r.id==='manual_sort')&&!rooms(m).some(r=>r.id==='auto_sorter'));
  const auto=gen('مستودع في الرياض فيه استلام وفرز آلي بسيور وتغليف وشحن',80,60);
  ok('«فرز آلي» still builds the automatic sorter',rooms(auto).some(r=>r.id==='auto_sorter'));
}
});
// The shipped sample keeps its site and stays a warehouse.
section('The shipped sample keeps its site and stays a warehouse.',()=>{
{
  const s=JSON.parse(JSON.stringify(run('warehouseModel(120,80,{clear:12})')));
  ok('sample keeps its 120×80 plot',s.site.w===120&&s.site.d===80&&s.meta.type==='warehouse');
}
});
if(failed){console.log('FAILED '+failed+' warehouse local brief checks');process.exitCode=1;}
else console.log('PASS warehouse local brief: '+checks+' checks');
