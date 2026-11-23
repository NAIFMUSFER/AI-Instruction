// Authored local residential scheme. Coordinates are metres, x east and z south.
// The apartment wing is mirrored about the common entrance. All floor/room
// instances, apertures, furniture and stairs are part of the exported model.
import { withDefaultStairs } from './stairs.mjs';

const round = value => Math.round(value * 1000) / 1000;
const levelsAr = ['الأرضي', 'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس'];
const opposite = { N: 'S', S: 'N', E: 'W', W: 'E' };

function unsupported(message) {
  const error = new Error(message);
  error.code = 'LOCAL_APARTMENT_UNSUPPORTED';
  throw error;
}

function rectangle(id, name, role, rect, unit) {
  const room = {id, name, role, rect, wall_color: '#deccb0', floor_color: '#d6c3a7', doors: [], windows: []};
  if (unit) room.unit_id = unit;
  return room;
}

function sharedWall(a, b) {
  const [x,z,w,d] = a.rect, [bx,bz,bw,bd] = b.rect;
  const eq = (m,n) => Math.abs(m - n) < 0.002;
  if (eq(x+w,bx) || eq(x,bx+bw)) return [eq(x+w,bx) ? 'E':'W', Math.max(z,bz), Math.min(z+d,bz+bd), z, bz];
  if (eq(z+d,bz) || eq(z,bz+bd)) return [eq(z+d,bz) ? 'S':'N', Math.max(x,bx), Math.min(x+w,bx+bw), x, bx];
  throw new Error('LOCAL_APARTMENT_ROOMS_NOT_ADJACENT');
}

// Emit corresponding real cuts in both room shells at the same world position.
function connect(a,b,desired = 0.95, material = 'wood') {
  const [edge,start,end,fromA,fromB] = sharedWall(a,b);
  const width = round(Math.min(desired, end-start-0.24));
  if (width < 0.75) throw new Error('LOCAL_APARTMENT_DOOR_TOO_NARROW');
  const center = (start+end)/2;
  const door = (room, other, side, origin) => ({
    id: room.id+'_to_'+other.id, edge: side, offset: round(center-origin), width, height: 2.18, material
  });
  a.doors.push(door(a,b,edge,fromA));
  b.doors.push(door(b,a,opposite[edge],fromB));
}

function windowAt(room,edge,fraction,width,sill=0.76,height=1.78) {
  const span = room.rect[['N','S'].includes(edge) ? 2 : 3];
  const offset = fraction*span;
  room.windows.push({id:room.id+'_window_'+room.windows.length,edge,offset:round(offset),
    width:round(Math.min(width,2*Math.min(offset,span-offset)-0.28)),sill,height});
}

function object(room,kind,name,x,z,w,d,h,rot=0,y=0) {
  (room.objects ||= []).push({id:room.id+'_'+kind+'_'+room.objects.length,
    kind,name,x:round(x),z:round(z),w:round(w),d:round(d),h:round(h),rot,y:round(y)});
}

function furnish(r) {
  function place(room,kind,name,fx,fz,w,d,h,rot=0) {
    object(room,kind,name,room.rect[2]*fx,room.rect[3]*fz,w,d,h,rot);
  }
  place(r.living,'sofa','كنبة المعيشة',0.38,0.34,2.35,0.92,0.82);
  place(r.living,'armchair','كرسي',0.27,0.59,0.85,0.86,0.8,90);
  place(r.living,'table','طاولة القهوة',0.56,0.53,1.05,0.55,0.42);
  place(r.majlis,'sofa','كنبة الضيوف',0.49,0.26,2.3,0.82,0.78);
  place(r.majlis,'armchair','كرسي ضيافة',0.25,0.56,0.78,0.8,0.78,90);
  place(r.dining,'dining','طاولة لستة',0.43,0.5,1.76,0.85,0.76);
  for(const side of [-1,1]) for(const dx of [-0.60,0,0.60]) {
    object(r.dining,'chair','كرسي طعام',r.dining.rect[2]*0.43+dx,r.dining.rect[3]/2+side*0.7,0.42,0.43,0.84,side<0?180:0);
  }
  place(r.kitchen,'cabinet','سطح تحضير',0.13,0.40,0.55,1.95,0.9);
  place(r.kitchen,'fridge','ثلاجة',0.16,0.84,0.72,0.66,1.8);
  place(r.kitchen,'oven','فرن',0.40,0.85,0.60,0.65,0.90);
  place(r.kitchen,'sink','حوض المطبخ',0.15,0.21,0.50,0.46,0.94);
  for(const room of [r.master,r.bed1,r.bed2]) {
    place(room,'bed','سرير',0.43,0.48,room===r.master?1.70:1.14,1.95,0.55);
    place(room,'wardrobe','خزانة',0.24,0.87,1.38,0.54,2.15);
  }
}

function floorPlan(width,depth,index,storeyHeight) {
  const sx=width/20, sz=depth/25;
  const rect=(x,z,w,d) => [round(x*sx),round(z*sz), round((x+w)*sx)-round(x*sx), round((z+d)*sz)-round(z*sz)].map(round);
  const entranceDepth=index?0:1.35;
  const lobby=rectangle('lobby',index?'بسطة وبهو مشترك':'بهو المدخل','lobby',rect(8,entranceDepth,4,7.2-entranceDepth));
  const stair=rectangle('stair','الدرج المشترك','stairs',rect(8,7.2,2.4,4.8));
  const lift=rectangle('lift','حيّز المصعد المقترح','elevator',rect(10.4,7.2,1.6,4.8));
  stair.core_id='central'; lift.core_id='lift';
  lobby.wall_color='#bfab90'; lobby.floor_color='#b6a286';
  const rooms=[lobby,stair,lift];
  connect(lobby,stair,1.0); connect(lobby,lift,0.90,'metal');
  if(index===0) {
    const porch=rectangle('entrance_porch','رواق المدخل','porch',rect(8,0,4,entranceDepth));
    porch.walls=[]; porch.floor_color='#9c8265'; rooms.push(porch);
    connect(lobby,porch,1.90,'glass');
    const [,,pw,pd]=porch.rect;
    const canopyHeight=Math.min(2.67,storeyHeight-0.32);
    object(porch,'box','مظلة المدخل',pw/2,pd/2,pw-0.06,pd-0.04,0.15,0,canopyHeight);
    porch.objects.at(-1).color='#795c42';
    for(const px of [0.20,pw-0.20]) {
      object(porch,'column','دعامة الرواق',px,0.22,0.20,0.24,canopyHeight);
      porch.objects.at(-1).color='#b6a186';
    }
    windowAt(lobby,'N',0.105,0.50,0.30,2.15);
    windowAt(lobby,'N',0.895,0.50,0.30,2.15);
  } else windowAt(lobby,'N',0.5,3.0,0.28,2.15);

  for(const unit of ['west','east']) {
    const r={}, side=unit==='west'?'W':'E';
    const add=(id,name,role,x,z,w,d) => {
      const pos=rect(unit==='west'?x:20-x-w,z,w,d);
      const room=rectangle(unit+'_'+id,name,role,pos,unit);
      r[id]=room; rooms.push(room);
      return room;
    };
    const balconyDepth=index ? 1.6 : 0;
    if(index) {
      const balcony=add('balcony','شرفة غائرة','balcony',0,0,4.4,balconyDepth);
      balcony.walls=[]; balcony.floor_color='#aa8460';
      const [,,bw,bd]=balcony.rect, exteriorX=unit==='west'?0.09:bw-0.09;
      object(balcony,'railing','حاجز الشرفة الأمامي',bw/2,0.09,bw-0.12,0.08,1.10);
      object(balcony,'railing','حاجز الشرفة الجانبي',exteriorX,bd/2,bd-0.12,0.08,1.10,90);
      // A permeable screen shades only the end bay, keeping the sliding door and view clear.
      const screenWidth=bw*0.31;
      const slats=Math.ceil(screenWidth/0.17);
      for(let i=0;i<slats;i++) {
        const x=0.16+(i+0.5)*(screenWidth-0.16)/slats;
        object(balcony,'box','ريشة تظليل',unit==='west'?x:bw-x,0.22,0.065,0.15,storeyHeight-0.25,15);
        balcony.objects.at(-1).color='#865d3b';
      }
    }
    add('living','صالة عائلية','living',0,balconyDepth,4.4,7.2-balconyDepth);
    add('majlis','مجلس الضيوف','majlis',4.4,0,3.6,5);
    add('foyer','مدخل الشقة','entry',4.4,5,3.6,2.2);
    add('dining','صالة الطعام','dining',0,7.2,4.4,3.6);
    add('kitchen','مطبخ','kitchen',0,10.8,4.4,4);
    add('hall','ممر النوم','corridor',4.4,7.2,1.8,12.8);
    add('guest_wc','دورة مياه الضيوف','bathroom',6.2,7.2,1.8,2.3);
    add('laundry','غرفة غسيل','laundry',6.2,9.5,1.8,2.5);
    add('store','مخزن','storage',6.2,12,3.8,2);
    add('bath','حمام مشترك','bathroom',6.2,14,3.8,3);
    add('wardrobe','غرفة ملابس','closet',6.2,17,1.9,3);
    add('ensuite','حمام الجناح','bathroom',8.1,17,1.9,3);
    add('bed1','غرفة نوم ١','bedroom',0,14.8,4.4,3.7);
    add('bed2','غرفة نوم ٢','bedroom',0,18.5,4.4,6.5);
    add('master','غرفة النوم الرئيسية','bedroom',4.4,20,5.6,5);
    connect(lobby,r.foyer,1.05);
    connect(r.foyer,r.majlis); connect(r.foyer,r.guest_wc,0.8);
    connect(r.foyer,r.living,1.15); connect(r.foyer,r.hall);
    connect(r.living,r.dining,1.65); connect(r.dining,r.kitchen,1.08);
    for (const id of ['kitchen','laundry','store','bath','bed1','bed2','master']) connect(r.hall,r[id]);
    connect(r.master,r.wardrobe,0.85); connect(r.master,r.ensuite,0.85);
    if(index) connect(r.living,r.balcony,2.45,'glass');
    else windowAt(r.living,'N',0.5,3.05,0.52,2.04);
    windowAt(r.majlis,'N',0.5,2.53,0.61,1.96);
    for(const id of ['living','dining','kitchen','bed1','bed2']) windowAt(r[id],side,0.5,id==='living'?3.15:2.1,id==='kitchen'?1.08:0.78,id==='kitchen'?1.28:1.77);
    windowAt(r.bed2,'S',0.5,2.6); windowAt(r.master,'S',0.53,3.12);
    if(!index && unit==='west') furnish(r);
  }
  return {rooms};
}

const assumptions = [
  'مخطط محلي مفاهيمي بشقتين وثلاث غرف نوم لكل شقة. أبعاد الغرف الفعلية مشتقة من المخطط وقد تختلف عن الأهداف النصية.',
  'الدرجات والبسطات وفتحات البلاطات ممثلة بين الأدوار السكنية. المصعد حيّز مقترح، والوصول إلى سطح الخدمات يحتاج إلى تصميم.',
  'الأثاث والتشطيبات اقتراحات للمقياس. مجاري الخدمات والمواقف والارتدادات والتحقق الإنشائي والتنظيمي تحتاج إلى مراجعة مستقلة.'
];

function design(width,depth,levels,height,source) {
  if(!Number.isFinite(width)||width<18||width>32||!Number.isFinite(depth)||depth<22||depth>36)
    unsupported('أدخل أبعاد المبنى الخارجية. يدعم هذا التوزيع واجهة بين 18 و32 م وعمقاً بين 22 و36 م.');
  if(!Number.isInteger(levels)||levels<1||levels>6)
    unsupported('يدعم مخطط الشقق المحلي من دور سكني واحد إلى ستة أدوار شاملة الأرضي.');
  if(!Number.isFinite(height)||height<2.8||height>3.6)
    unsupported('يدعم الدرج المحلي ارتفاع دور موحّداً بين 2.8 و3.6 م.');
  const title='عمارة سكنية '+width+' × '+depth+' م';
  const model={
    meta:{name:title,type:'residential',north:'-Z',acs_apartment:{schema:'acs.local-apartment/1',source,width_m:width,depth_m:depth,
      occupied_levels:levels,units_per_floor:2,units_total:2*levels,bedrooms_per_unit:3,street_edge:'N',assumptions:[...assumptions]}},
    site:{w:width,d:depth},floor_height:height,wall_h:round(height-0.18),wall_t:0.18,levels:[],floors:{}
  };
  for(let i=0;i<levels;i++) {
    const template='level_'+i;
    model.levels.push({index:i,name:levelsAr[i],elevation:round(i*height),template});
    model.floors[template]=floorPlan(width,depth,i,height);
  }
  if(levels===1) return model;
  const [result,report,reason]=withDefaultStairs(model);
  if(reason || report.generated_connections!==levels-1) unsupported('تعذّر وصل الدرج ضمن الأبعاد المحددة. راجع عرض المبنى وعمقه وارتفاع الدور.');
  return result;
}

export function apartmentSample() {
  return design(20,25,3,3.4,'synthetic_sample');
}

function normalize(text) {
  return String(text||'').toLowerCase().replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)%16))
    .replace(/[\u064b-\u065f\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/٫/g,'.');
}
const numberWord={'واحد':1,'واحده':1,'اثنان':2,'اثنين':2,'ثلاث':3,'ثلاثه':3,'اربع':4,'اربعه':4,'خمس':5,'خمسه':5,'ست':6,'سته':6,'سبع':7,'سبعه':7,'ثمانيه':8,'ثمان':8,'تسعه':9,'عشره':10};
const count='(\\d+|'+Object.keys(numberWord).sort((a,b)=>b.length-a.length).join('|')+')';
const asCount = value=>Number.isNaN(Number(value))?numberWord[value]:Number(value);
const decimal='(\\d+(?:\\.\\d+)?)';
function dimensions(text) {
  // Only the building introduction supplies exterior dimensions. Room goals
  // and numbered programme headings in subsequent paragraphs are unrelated.
  const first=text.split(/\n\s*\n|(?:مجلس|غرفه نوم|صاله عائليه|مطبخ)/)[0].slice(0,650);
  const pair = first.match(new RegExp(decimal+'\\s*(?:متر|م)?\\s*(?:[×x*]|في|بـ?)\\s*'+decimal+'(?:\\s*(?:متر|م))?'));
  const frontage = first.match(new RegExp(decimal+'\\s*(?:مترا?|م)?\\s*(?:على\\s+)?واجهه'));
  const depth = first.match(new RegExp(decimal+'\\s*(?:مترا?|م)?\\s*عمق'));
  const dw=first.match(new RegExp('(?:عرض(?:ها|ه)?|واجهه(?:\\s+المبنى)?)\\s*[:=]?\\s*'+decimal));
  const dd=first.match(new RegExp('عمق(?:ها|ه)?\\s*[:=]?\\s*'+decimal));
  const matched=pair||((frontage||dw)&&(depth||dd));
  if(matched && /(?:قطعه(?:\s+الارض)?|(?:مساحه|ابعاد|على)\s+(?:قطعه\s+)?(?:ال)?ارض|الارض\s+(?:ب?مقاس|بابعاد|\d))/.test(first) && !/(?:ابعاد|مسطح|بصمه|عرض)\s+(?:المبنى|العماره)/.test(first))
    unsupported('ذكرت أبعاد الأرض. حدّد عرض المبنى وعمقه بعد الارتدادات لاستخدام مخطط الشقق المحلي.');
  return pair?[+pair[1],+pair[2]]:matched?[+(frontage||dw)[1],+(depth||dd)[1]]:null;
}

export function apartmentFromBrief(text,{width=20,depth=25,levels=3}={}) {
  const t=normalize(text);
  if(!/(?:عماره|عمار[هة]|مبنى\s+سكني|بنايه\s+سكنيه|apartment\s+building|residential\s+building)/.test(t.slice(0,260))) return null;
  if(/^(?:صمم\s+|انشئ\s+|ابن\s+)?(?:مستودع|مصنع|فيلا|مدرسه)/.test(t.trim())) return null;
  const explicitSize=dimensions(t);
  if(explicitSize) [width,depth]=explicitSize;
  const statedFloors=t.match(new RegExp(count+'\\s*(?:ادوار|طوابق|floors|storeys)'));
  if(statedFloors) levels=asCount(statedFloors[1]);
  else if(/(?:دور\s+|طابق\s+)?ارضي[^.\n]{0,70}(?:اول)[^.\n]{0,40}(?:ثان)/.test(t)) levels=3;
  else if(/(?:دوران|دورين|طابقين|طابقان)(?:\s|[.،,]|$)/.test(t.slice(0,240))) levels=2;
  else if(/(?:دور|طابق)\s+واحد/.test(t.slice(0,240))) levels=1;
  const perFloor=t.match(new RegExp(count+'\\s*شقق?\\s*(?:في|ب|لكل)\\s*(?:كل\\s+)?(?:دور|طابق)')) || t.match(new RegExp('(?:في|ب)\\s*كل\\s*(?:دور|طابق)\\s*'+count+'\\s*شقق?'));
  const total=t.match(new RegExp('(?:ب?اجمالي|مجموع(?:ها)?)\\s*'+count+'\\s*شقق?'));
  if((perFloor&&asCount(perFloor[1])!==2)||(total&&asCount(total[1])!==2*levels)||/(?:شقه\s+(?:واحده\s+)?(?:بكل|لكل|في كل)\s+دور|كل دور\s+شقه\s+واحده)/.test(t))
    unsupported('يدعم هذا المخطط المحلي شقتين في كل دور. راجع عدد الشقق والأدوار قبل الإنشاء.');
  if(/قبو|بدروم/.test(t.replace(/(?:لا\s+(?:يوجد|اريد|يتضمن|يشمل)?\s*|بلا\s*|بدون\s*|من دون\s*)(?:اي\s*)?(?:قبو|بدروم)/g,'')))
    unsupported('يتضمن وصفك قبواً. يدعم مخطط الشقق المحلي الأدوار فوق الأرض فقط.');
  if(/(?:واجهه(?:\s+الشارع)?|شارع)\s+(?:ال)?(?:جنوبي|غربي|شرقي)/.test(t))
    unsupported('مدخل مخطط الشقق المحلي على الواجهة الشمالية. يتطلب اتجاه الشارع المطلوب توزيعاً آخر.');
  let height=3.4;
  const storey=t.match(new RegExp('ارتفاع\\s+(?:(?:كل|بين)\\s+)?(?:ال)?(?:دور|طابق)(?:\\s+الواحد)?\\s*[:=]?\\s*'+decimal));
  if(storey) height=+storey[1];
  // Respect the declared first-floor datum and flag inconsistent level series.
  const datum=(name)=>t.match(new RegExp('(?:منسوب\\s+|و)?'+name+'\\s*[:=]?\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*م'));
  const first=datum('الاول'), second=datum('الثاني'), roof=datum('(?:بلاطه\\s+)?السطح'), ground=datum('الارضي');
  if(first && !storey) height=+first[1];
  if((ground&&+ground[1]!==0)||(first&&Math.abs(+first[1]-height)>0.01)||(second&&Math.abs(+second[1]-2*height)>0.01)||(roof&&Math.abs(+roof[1]-levels*height)>0.01))
    unsupported('المناسيب المحددة غير منتظمة. يدعم مخطط الشقق المحلي ارتفاعاً موحّداً يبدأ من منسوب أرضي 0.00 م.');
  return design(width,depth,levels,height,'local_brief');
}
