// The drawing consumes the existing architectural projection for a single physical
// level. Colours, index labels and scale annotations belong only to the drawing.
import { hasUStairs, resolveStairGeometry, stairConnections } from '../core/stairs.mjs';

const units = {
  east: { name: 'الشقة الشرقية', fill: '#e5efeb' },
  west: { name: 'الشقة الغربية', fill: '#f4e8d9' },
  shared: { name: 'المساحات المشتركة', fill: '#e8ebee' },
};
const arabic = /[\u0600-\u06ff]/;
const metric = new Intl.NumberFormat('ar-SA-u-nu-latn', { maximumFractionDigits: 2 });
const fmt = value => metric.format(value);
const q = value => Number(value.toFixed(3));
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]
));
const roomMeasure = r => `${fmt(r.w)} × ${fmt(r.d)} م`;
function levelLabel(level) {
  if (level?.name && /^(الأرضي|الأول|الثاني|الثالث|الرابع|الخامس)$/.test(level.name)) return `الدور ${level.name}`;
  return level?.name || ({0:'الدور الأرضي',1:'الدور الأول',2:'الدور الثاني'}[level?.index] ?? `الدور ${fmt(level?.index ?? 0)}`);
}
function floorData(packet, model) {
  const level = (model.levels || []).find(item => item.index === packet.level_index);
  const rooms = (model.floors?.[level?.template]?.rooms || []);
  const byId = new Map(rooms.map(item => [String(item.id), item]));
  const hasUnits = rooms.some(room => room.unit_id === 'east' || room.unit_id === 'west');
  const spaces = (packet.spaces || [])
    .filter(room => room.boundary_basis === 'rectangle_edges' && [room.x,room.z,room.w,room.d].every(Number.isFinite) && room.w > 0 && room.d > 0)
    .map(room => {
      const source = byId.get(String(room.name)) || {};
      const unit = source.unit_id === 'east' || source.unit_id === 'west' ? source.unit_id : 'shared';
      return { ...room, displayName: String(source.name || room.name || room.space_id), unit };
    })
    .sort((a,b) => a.z - b.z || a.x - b.x || a.displayName.localeCompare(b.displayName, 'ar'));
  return {level,spaces,hasUnits};
}
function line(x1, y1, x2, y2, color, width, attrs = '') {
  return `<line x1="${q(x1)}" y1="${q(y1)}" x2="${q(x2)}" y2="${q(y2)}" stroke="${color}" stroke-width="${q(width)}" ${attrs}/>`;
}
function label(x, y, content, size = 15, options = {}) {
  const dir = options.dir || (arabic.test(content) ? 'rtl' : 'ltr');
  return `<text x="${q(x)}" y="${q(y)}" font-size="${size}" direction="${dir}" text-anchor="${options.anchor || 'middle'}" fill="${options.color || '#243d43'}" font-weight="${options.weight || 400}">${esc(content)}</text>`;
}
function axisBounds(spaces) {
  let x0=Infinity, z0=Infinity, x1=-Infinity, z1=-Infinity;
  for (const room of spaces) {
    x0=Math.min(x0,room.x); z0=Math.min(z0,room.z);
    x1=Math.max(x1,room.x+room.w); z1=Math.max(z1,room.z+room.d);
  }
  return {x0,z0,width:x1-x0,depth:z1-z0};
}
const segmentIsFinite = s => [s.x1,s.z1,s.x2,s.z2].every(Number.isFinite);

// The plan projector returns centre lines. Each supported wall is a rectangular
// strip whose half-thickness extends normal to its axis (not along its length).
function wallFaceBounds(grid, walls) {
  let x0=grid.x0, z0=grid.z0;
  let x1=x0+grid.width, z1=z0+grid.depth;
  for (const wall of walls) {
    const dx=wall.x2-wall.x1, dz=wall.z2-wall.z1;
    const length=Math.hypot(dx,dz);
    if (!length) continue;
    const halfWidth=wall.thickness_m/2;
    const offsetX=Math.abs(dz/length)*halfWidth;
    const offsetZ=Math.abs(dx/length)*halfWidth;
    x0=Math.min(x0,wall.x1-offsetX,wall.x2-offsetX);
    x1=Math.max(x1,wall.x1+offsetX,wall.x2+offsetX);
    z0=Math.min(z0,wall.z1-offsetZ,wall.z2-offsetZ);
    z1=Math.max(z1,wall.z1+offsetZ,wall.z2+offsetZ);
  }
  return {x0,z0,width:x1-x0,depth:z1-z0};
}

function stairDrawing(model, packet, spaces, x, y, scale) {
  if (!hasUStairs(model)) return '';
  const drawing = [];
  for (const connection of stairConnections(model)) {
    const obj = connection.object;
    // Draw the incoming aperture before any ascending treads at this level.
    if (connection.target_level_index === packet.level_index) {
      const [ox,oz,ow,od] = connection.opening;
      drawing.unshift(`<rect data-stair-opening="${esc(obj.id)}" x="${q(x(ox))}" y="${q(y(oz))}" width="${q(ow*scale)}" height="${q(od*scale)}" pointer-events="none" fill="#d1dcda" stroke="#637773" stroke-width="1.4" stroke-dasharray="4 3"/>`);
    }
    if (connection.source_level_index !== packet.level_index) continue;
    const space=spaces.find(s=>s.name===connection.room_id);
    if (!space) continue;
    const treads = resolveStairGeometry(obj).components.map(part => {
      const [dx,,dz]=part.center, [w,,d]=part.size;
      return `<rect data-stair-part="${esc(part.id)}" x="${q((dx-w/2)*scale)}" y="${q((dz-d/2)*scale)}" width="${q(w*scale)}" height="${q(d*scale)}" fill="#e4ded3" stroke="#64706c" stroke-width="1.1"/>`;
    });
    drawing.push(`<g data-stair-object="${esc(obj.id)}" pointer-events="none" transform="translate(${q(x(space.x+obj.x))} ${q(y(space.z+obj.z))}) rotate(${q(obj.rot)})"><title>درجات وبسطة الدرج</title>${treads.join('')}</g>`);
  }
  return drawing.join('');
}

export function renderGuestFloorSVG(packet, model, {schedule = true, landscape = false, selected = ''} = {}) {
  const {level,spaces,hasUnits} = floorData(packet,model);
  if (!spaces.length) throw new Error('لا توجد فراغات مستطيلة قابلة للرسم في هذا الطابق.');
  const walls = packet.walls.filter(segmentIsFinite);
  const grid = axisBounds(spaces);
  const onWallAxes = model.meta?.acs_apartment?.wall_reference === 'room_wall_centrelines';
  const hasExteriorDimensions = onWallAxes && walls.length > 0 && walls.every(w =>
    Number.isFinite(w.thickness_m) && w.thickness_m > 0 && w.thickness_source !== 'unknown');
  const b = hasExteriorDimensions ? wallFaceBounds(grid, walls) : grid;
  const scale = Math.min(590/b.width, 790/b.depth);
  const dw = b.width*scale, dh = b.depth*scale;
  const left=(720-dw)/2, top=schedule?106:64, bottom=top+dh;
  const x = value => left+(value-b.x0)*scale, y = value => top+(value-b.z0)*scale;
  const groups=[],labels=[];
  spaces.forEach((room,index) => {
    const number=index+1, rw=room.w*scale, rh=room.d*scale;
    const cx=x(room.x+room.w/2), cy=y(room.z+room.d/2);
    const display=room.displayName, showName=rw>66 && rh>32 && display.length*5.6<rw;
    const font=rw>90 && rh>44?14:12;
    groups.push(`<g data-room-key="${esc(room.id)}" data-unit="${esc(room.unit)}"><title>${esc(display)} · ${esc(roomMeasure(room))}</title><rect x="${q(x(room.x))}" y="${q(y(room.z))}" width="${q(rw)}" height="${q(rh)}" fill="${room.id===selected?'#d0ae6d':hasUnits?units[room.unit].fill:'#e7eeeb'}"/></g>`);
    labels.push(`<g pointer-events="none">${label(cx,cy+(showName?-2:5),String(number),font,{weight:700})}${showName?label(cx,cy+14,display,12):''}</g>`);
  });
  const wallsById = new Map(walls.map(w => [w.id,w]));
  const wallWidth = w => Number.isFinite(w.thickness_m)&&w.thickness_m>0?Math.max(1,w.thickness_m*scale):2;
  const wallLines = walls.map(w => line(x(w.x1),y(w.z1),x(w.x2),y(w.z2),'#2d3838',wallWidth(w),`data-wall-id="${esc(w.id)}"`));
  const openingLines = [];
  for (const o of packet.openings || []) {
    const w = wallsById.get(o.host_wall_id);
    if (!w || !segmentIsFinite(o) || !(o.width_m>0)) continue;
    const x1=x(o.x1), y1=y(o.z1), x2=x(o.x2), y2=y(o.z2);
    const glazed=o.type==='WINDOW';
    openingLines.push(`<g data-opening-id="${esc(o.id)}" data-opening-type="${esc(o.type)}"><title>${glazed?'نافذة':'باب'} · ${esc(fmt(o.width_m))} م</title>${line(x1,y1,x2,y2,'#fffdf8',wallWidth(w)+1)}${line(x1,y1,x2,y2,glazed?'#357887':'#93611c',glazed?2.4:1.4,glazed?'':'stroke-dasharray="3 3"')}</g>`);
  }
  const stairs=stairDrawing(model,packet,spaces,x,y,scale);
  const dim='#637373';
  let measures=line(left,top-20,left+dw,top-20,dim,1)+line(left,top-25,left,top-12,dim,1)+line(left+dw,top-25,left+dw,top-12,dim,1);
  measures+=label(left+dw/2,top-27,`${fmt(b.width)} م`,16);
  measures+=line(left-14,top,left-14,bottom,dim,1)+line(left-19,top,left-8,top,dim,1)+line(left-19,bottom,left-8,bottom,dim,1);
  measures+=`<g transform="translate(${q(left-25)} ${q(top+dh/2)}) rotate(-90)">${label(0,0,`${fmt(b.depth)} م`,16)}</g>`;
  // North is drawn only when explicitly declared for this local-coordinate plan.
  if(model.meta?.acs_apartment?.street_edge==='N'){
    measures+=`<path d="M 682 ${top+24} v -32 l -5 8 m 5 -8 l 5 8" stroke="#264447" stroke-width="2" fill="none"/>`+label(682,top+44,'شمال',14);
  }
  const barLimit=Math.min(b.width/3,b.depth/3);
  const barPower=10**Math.floor(Math.log10(barLimit));
  const bar=(barLimit/barPower>=5?5:barLimit/barPower>=2?2:1)*barPower;
  const scaleY=bottom+29;
  measures+=line(left,scaleY,left+bar*scale,scaleY,'#294449',3)+line(left,scaleY-5,left,scaleY+3,'#294449',2)+line(left+bar*scale,scaleY-5,left+bar*scale,scaleY+3,'#294449',2)+label(left+bar*scale/2,scaleY+19,`${fmt(bar)} م`,13);
  const dimensionNote = hasExteriorDimensions ? 'القياس العام بين الوجوه الخارجية للجدران' : 'القياس العام بين حدود شبكة الفراغات';
  measures+=label(660,scaleY+15,dimensionNote,13,{anchor:'start',color:dim});
  const drawEnd=bottom+63;
  let end=drawEnd, index='';
  if(schedule){
    const sorted=[...spaces.entries()].sort(([,a],[,b])=>a.unit.localeCompare(b.unit)||a.z-b.z||a.x-b.x);
    for(const unit of ['east','west','shared']){
      const list=sorted.filter(([,r])=>r.unit===unit);
      if(!list.length)continue;
      end+=25;index+=label(665,end,hasUnits?units[unit].name:'الفراغات',18,{anchor:'start',weight:700});
      end+=8;index+=line(55,end,665,end,'#b4c0bb',1);
      list.forEach(([i,r],n)=>{
        const col=n%2, row=Math.floor(n/2), lx=col===0?665:342, ly=end+25+row*39;
        index+=label(lx-14,ly,String(i+1),14,{weight:700});
        index+=label(lx-35,ly,r.displayName,13,{dir:'rtl',anchor:'start'});
        index+=label(lx-35,ly+15,`${roomMeasure(r)}  ·  ${fmt(r.area_m2)} م²`,12,{dir:'rtl',anchor:'start',color:'#4d6161'});
      });
      end+=Math.ceil(list.length/2)*39+9;
    }
    if (hasExteriorDimensions) {
      end+=23;index+=label(360,end,`مساحة المستطيل المحيط بالجدران ${fmt(b.width*b.depth)} م²`,14);
      end+=19;index+=label(360,end,`امتداد محاور الجدران ${fmt(grid.width)} × ${fmt(grid.depth)} م`,14);
    }
    end+=22;index+=label(360,end,onWallAxes?'أبعاد الغرف ومساحاتها محسوبة على محاور الجدران، قبل خصم سماكاتها.':'أبعاد الفراغات ومساحاتها محسوبة من حدودها في النموذج.',14);
    end+=20;index+=label(360,end,'الخط المتقطع باب، والخط الأزرق نافذة.',14);end+=22;
  }
  const spread = landscape && schedule;
  const sheetWidth = spread ? 1410 : 720;
  const offsetY = 86-drawEnd;
  const sheetHeight = spread ? Math.max(drawEnd,end+offsetY) : end;
  const title = `مخطط ${levelLabel(level)}`;
  const indexTransform = spread ? ` transform="translate(680 ${q(offsetY)})"` : '';
  const header = schedule ? label(spread?1345:665,40,title,24,{anchor:'start',weight:700}) : '';
  const caption = schedule ? label(spread?1345:665,64,'تصميم مفاهيمي • مخطط الفراغات',14,{anchor:'start',color:'#526a6c'}) : '';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${sheetWidth} ${q(sheetHeight)}" width="${sheetWidth}" height="${q(sheetHeight)}" data-level-index="${esc(packet.level_index)}" data-width-m="${q(b.width)}" data-depth-m="${q(b.depth)}" data-grid-width-m="${q(grid.width)}" data-grid-depth-m="${q(grid.depth)}" data-dimension-basis="${hasExteriorDimensions?'outer_wall_faces':'room_grid'}" role="img" aria-labelledby="acsPlanTitle" font-family="Arial, 'DejaVu Sans', sans-serif"><title id="acsPlanTitle">${esc(title)} · مخطط الفراغات</title><rect width="${sheetWidth}" height="${q(sheetHeight)}" fill="#fffdf8"/>${header}${caption}<g data-layout="drawing">${groups.join('')}${stairs}${wallLines.join('')}${openingLines.join('')}${labels.join('')}${measures}</g><g data-layout="schedule"${indexTransform}>${index}</g></svg>`;

}

function element(tag, text, id) {
  const node=document.createElement(tag);
  if(text)node.textContent=text;
  if(id)node.id=id;
  return node;
}
export function openGuestFloorPlan(acs, initialLevel=0) {
  const existing=document.getElementById('guestPlanDialog');
  if(existing?.open)return existing;
  const model=acs.exportModel();
  const levels=(model?.levels||[]).filter(l=>Number.isInteger(l.index)&&model.floors?.[l.template]?.rooms?.length);
  if(!levels.length)throw new Error('لا توجد طوابق متاحة في هذا النموذج.');
  if(!document.getElementById('guestPlanStyle')){
    const link=element('link',null,'guestPlanStyle');link.rel='stylesheet';link.href=new URL('../styles/guest-floor-plan.css',import.meta.url).href;document.head.append(link);
  }
  const previous=document.activeElement,dialog=element('dialog',null,'guestPlanDialog');dialog.dir='rtl';
  dialog.setAttribute('aria-labelledby','guestPlanTitle');
  const header=element('header'), heading=element('h2','مخطط الدور','guestPlanTitle');
  const close=element('button','إغلاق','guestPlanClose');close.type='button';close.addEventListener('click',()=>dialog.close());
  header.append(heading,close);
  const controls=element('div');controls.className='guest-plan-fields';
  const floorLabelNode=element('label','الدور'),floor=element('select',null,'guestPlanFloor');floorLabelNode.append(floor);
  for(const level of levels){const opt=element('option',levelLabel(level));opt.value=String(level.index);floor.append(opt);}
  floor.value=String(levels.find(l=>l.index===initialLevel)?.index??levels[0].index);
  const roomLabel=element('label','الفراغ'),roomChoice=element('select',null,'guestPlanRoom');roomLabel.append(roomChoice);
  controls.append(floorLabelNode,roomLabel);
  const viewport=element('div',null,'guestPlanViewport'),details=element('p',null,'guestPlanDetails');details.setAttribute('role','status');
  const footer=element('footer'),zoom=element('button','تكبير المخطط','guestPlanZoom'),download=element('button','تنزيل مخطط SVG','guestPlanDownload');
  for(const btn of [zoom,download])btn.type='button';
  zoom.setAttribute('aria-pressed','false');footer.append(zoom,download);
  dialog.append(header,controls,viewport,details,footer);document.body.append(dialog);
  let packet, info;
  function sameModel() {
    if (acs.exportModel()===model) return true;
    viewport.replaceChildren();
    details.textContent='تغيّر النموذج. أغلق المخطط وافتحه لعرض النسخة الحالية.';
    download.disabled=true;
    return false;
  }
  function draw(){
    if (!sameModel()) return;
    const id=roomChoice.value,r=info.spaces.find(item=>item.id===id);
    viewport.innerHTML=renderGuestFloorSVG(packet,model,{schedule:false,selected:id});
    const gridLabel=model.meta?.acs_apartment?.wall_reference==='room_wall_centrelines'?' على محاور الجدران':' على شبكة الفراغات';
    details.textContent=r?`${info.hasUnits?units[r.unit].name+' · ':''}${r.displayName} · ${roomMeasure(r)} · ${fmt(r.area_m2)} م²${gridLabel}`
      :'اختر فراغًا لعرض أبعاده ومساحته. الخط الأزرق نافذة والمتقطع باب.';
  }
  function changeFloor(){
    if (!sameModel()) return;
    try {
      packet=acs.floorPlan2D(Number(floor.value),'TECHNICAL');info=floorData(packet,model);
      roomChoice.replaceChildren(element('option','كل الفراغات'));roomChoice.firstChild.value='';
      info.spaces.forEach((r,i)=>{const opt=element('option',`${i+1}. ${r.displayName}${info.hasUnits?' · '+units[r.unit].name:''}`);opt.value=r.id;roomChoice.append(opt);});
      draw();download.disabled=false;
    } catch {
      viewport.replaceChildren();
      details.textContent='تعذّر عرض مساحات هذا الدور. اختر دورًا آخر.';
      roomChoice.replaceChildren();download.disabled=true;
    }
  }
  floor.addEventListener('change',changeFloor);roomChoice.addEventListener('change',draw);
  viewport.addEventListener('click',event=>{const id=event.target.closest('[data-room-key]')?.getAttribute('data-room-key');if(id){roomChoice.value=id;draw();}});
  zoom.addEventListener('click',()=>{
    const enlarged=viewport.classList.toggle('guest-plan-enlarged');zoom.setAttribute('aria-pressed',String(enlarged));zoom.textContent=enlarged?'ملاءمة المخطط':'تكبير المخطط';
  });
  download.addEventListener('click',()=>{
    if (!sameModel()) return;
    const url=URL.createObjectURL(new Blob([renderGuestFloorSVG(packet,model)],{type:'image/svg+xml;charset=utf-8'}));
    const a=element('a');a.href=url;a.download=`apartment-floor-${packet.level_index}.svg`;dialog.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  dialog.addEventListener('close',()=>{dialog.remove();if(previous?.isConnected)previous.focus();},{once:true});
  changeFloor();dialog.showModal();close.focus();return dialog;
}
