// The structured program from the smart brief reader (acs_brief_reader.py):
// Arabic labels, the live checks shown while the owner edits the card, the
// owner-side preflight and the mapping onto the step-01 fields. The server
// validates the same program again before any generation uses it.
export const SCHEMA = 'acs.brief-program/1';
export const SIDE_AR = {N:'الشمال',E:'الشرق',S:'الجنوب',W:'الغرب'};
export const POSITION_AR = {N:'الشمال',NE:'الشمال الشرقي',E:'الشرق',SE:'الجنوب الشرقي',S:'الجنوب',SW:'الجنوب الغربي',W:'الغرب',NW:'الشمال الغربي',center:'الوسط'};
export const ROLE_AR = {bedroom:'غرفة نوم',bathroom:'حمام / دورة مياه',living:'صالة',majlis:'مجلس',dining:'سفرة',kitchen:'مطبخ',pantry:'مؤن',laundry:'غسيل',storage:'تخزين',office:'مكتب',dressing:'غرفة ملابس',maid:'غرفة خادمة',driver:'غرفة سائق',corridor:'ممر',entrance:'مدخل / ردهة',terrace:'تراس',balcony:'شرفة',other:'فراغ آخر'};
export const OUTDOOR_AR = {pool:'مسبح',garden:'حديقة',seating:'جلسة',courtyard:'فناء',yard:'حوش',service_yard:'حوش خدمة',walkway:'ممر خارجي',outdoor_dining:'طعام خارجي',equipment:'غرفة معدات',other:'عنصر خارجي'};
export const STAIR_AR = {u_two_flights:'درج على شكل U بقلبتين وبسطة وسطية',straight:'درج مستقيم',l_shape:'درج على شكل L',spiral:'درج حلزوني'};
export const OUTPUT_AR = {furnished_plans:'مخططات أدوار مؤثثة',site_plan:'مخطط موقع بالأبعاد',outdoor_plan:'مخطط الأحواش والحديقة',section:'قطاع رأسي',views_3d:'مجسّم ثلاثي الأبعاد',floor_isolation:'عزل كل دور في المجسّم'};
// Outputs the signed-in workspace already produces (the 3D viewer has a floor selector).
export const OUTPUT_READY = new Set(['views_3d','floor_isolation']);
export const LIMITS = Object.freeze({side:[2,200],setback:[0,30],room:[0.5,40],count:[1,12],parking:[0,100],stall:[1.8,8],levels:30});

const fmt = v => String(Math.round(Number(v) * 100) / 100);
const num = v => typeof v === 'number' && Number.isFinite(v);
const counted = (unit, role) => unit.rooms.filter(r => r.role === role).reduce((n, r) => n + r.count, 0);
export const bedroomsOf = unit => counted(unit, 'bedroom');
export const bathroomsOf = unit => counted(unit, 'bathroom');

/** The building's own extent: footprint, else land less stated setbacks, else null. */
export function envelope(site) {
  const fp = site.footprint || {};
  if (num(fp.width_m) && num(fp.depth_m)) return [fp.width_m, fp.depth_m];
  if (!num(site.width_m) || !num(site.depth_m)) return null;
  const sb = site.setbacks_m || {};
  return [site.width_m - (sb.W || 0) - (sb.E || 0), site.depth_m - (sb.N || 0) - (sb.S || 0)];
}

/** Same arithmetic notes as acs_brief_reader.checks (a parity test keeps them equal). */
export function programChecks(program) {
  const site = program.site, sb = site.setbacks_m, notes = [];
  const {width_m:w, depth_m:d, area_m2:area, footprint:fp} = site;
  if (num(w) && num(d) && num(area) && Math.abs(w * d - area) > Math.max(0.5, area * 0.01))
    notes.push({code:'SITE_AREA', message:'مساحة الأرض المذكورة ('+fmt(area)+' م²) لا تساوي العرض × العمق ('+fmt(w)+' × '+fmt(d)+' = '+fmt(w * d)+' م²).'});
  for (const [across, size, [a, b], label] of [[w, fp.width_m, ['W','E'], 'العرض'], [d, fp.depth_m, ['N','S'], 'العمق']]) {
    if ([across, size, sb[a], sb[b]].every(num) && Math.abs(sb[a] + size + sb[b] - across) > 0.05)
      notes.push({code:'STRIPS_' + (a === 'W' ? 'WIDTH' : 'DEPTH'), message:'في '+label+': ارتداد '+SIDE_AR[a]+' '+fmt(sb[a])+' + المبنى '+fmt(size)
        +' + ارتداد '+SIDE_AR[b]+' '+fmt(sb[b])+' = '+fmt(sb[a] + size + sb[b])+' م، والأرض '+fmt(across)+' م.'});
  }
  const env = envelope(site), holder = env && Math.min(...env) > 0 ? env[0] * env[1] : null;
  for (const level of program.levels) {
    const total = level.units.reduce((n, u) => n + u.rooms.reduce((m, r) => m + (num(r.width_m) ? r.width_m * r.depth_m * r.count : 0), 0), 0);
    if (holder != null && total > holder + 0.01)
      notes.push({code:'LEVEL_AREA', message:'مجموع المقاسات المستهدفة في '+level.name+' ('+fmt(total)+' م²) أكبر من مساحة المبنى ('+fmt(holder)+' م²) قبل الجدران والدرج.'});
    for (const unit of level.units) for (const [role, stated, label] of [['bedroom', unit.bedrooms, 'غرف النوم'], ['bathroom', unit.bathrooms, 'الحمامات']])
      if (stated != null && stated !== counted(unit, role))
        notes.push({code:'UNIT_' + role.toUpperCase() + 'S', message:'في '+level.name+': عدد '+label+' في الوصف '+stated+'، والمدرج في البرنامج '+counted(unit, role)+'.'});
  }
  return notes.slice(0, 24);
}

/** Owner-side preflight in Arabic; the server repeats it (acs_brief_reader.validate_program). */
export function checkProgram(program) {
  const range = (v, [lo, hi], label) => {
    if (v == null) return;
    if (!num(v) || v < lo || v > hi) throw new Error(label + ': أدخل رقمًا من ' + lo + ' إلى ' + hi + '.');
  };
  const site = program.site;
  range(site.width_m, LIMITS.side, 'عرض الأرض'); range(site.depth_m, LIMITS.side, 'عمق الأرض');
  for (const s of ['N','E','S','W']) range(site.setbacks_m[s], LIMITS.setback, 'ارتداد ' + SIDE_AR[s]);
  range(site.footprint.width_m, LIMITS.side, 'عرض كتلة المبنى'); range(site.footprint.depth_m, LIMITS.side, 'عمق كتلة المبنى');
  if ((site.footprint.width_m == null) !== (site.footprint.depth_m == null)) throw new Error('أدخل عرض كتلة المبنى وعمقها معًا، أو اتركهما فارغين.');
  if (num(site.footprint.width_m) && ((num(site.width_m) && site.footprint.width_m > site.width_m + 0.01) || (num(site.depth_m) && site.footprint.depth_m > site.depth_m + 0.01)))
    throw new Error('كتلة المبنى أكبر من الأرض. صحّح أحدهما.');
  for (const [across, [a, b]] of [[site.width_m, ['W','E']], [site.depth_m, ['N','S']]])
    if (num(across) && (site.setbacks_m[a] || 0) + (site.setbacks_m[b] || 0) >= across) throw new Error('ارتدادا '+SIDE_AR[a]+' و'+SIDE_AR[b]+' لا يتركان أرضًا للبناء.');
  if (!program.levels.length || program.levels.length > LIMITS.levels) throw new Error('عدد الأدوار يجب أن يكون من 1 إلى 30.');
  const env = envelope(site), holder = env && Math.min(...env) > 0 ? env[0] * env[1] : null;
  for (const level of program.levels) for (const unit of level.units) for (const room of unit.rooms) {
    const label = (room.name || 'فراغ') + ' في ' + level.name;
    if (!String(room.name || '').trim()) throw new Error('اكتب اسم كل فراغ في ' + level.name + '.');
    if (!Number.isInteger(room.count) || room.count < LIMITS.count[0] || room.count > LIMITS.count[1]) throw new Error(label + ': العدد من 1 إلى 12.');
    range(room.width_m, LIMITS.room, label + ' (العرض)'); range(room.depth_m, LIMITS.room, label + ' (العمق)');
    if ((room.width_m == null) !== (room.depth_m == null)) throw new Error(label + ': أدخل العرض والعمق معًا، أو اتركهما فارغين.');
    if (holder != null && num(room.width_m) && room.width_m * room.depth_m > holder + 0.01) throw new Error(label + ' أكبر من مساحة المبنى.');
  }
  const parking = program.parking;
  if (parking.count != null && (!Number.isInteger(parking.count) || parking.count < 0 || parking.count > 100)) throw new Error('عدد المواقف: عدد صحيح من 0 إلى 100.');
  range(parking.stall_width_m, LIMITS.stall, 'عرض الموقف'); range(parking.stall_depth_m, LIMITS.stall, 'عمق الموقف');
  return program;
}

const placementOf = {front_setback:'front_setback', pilotis:'pilotis', basement:'none', street:'none'};

/** The step-01 values a confirmed program fills, and what stays for the owner. */
export function programFields(program) {
  const site = program.site, levels = program.levels, fp = site.footprint;
  const occupied = levels.filter(l => l.units.length), all = occupied.flatMap(l => l.units);
  const pilotisGround = program.parking.placement === 'pilotis' && !levels[0]?.units.length;
  const perLevel = [...new Set(occupied.map(l => l.units.length))];
  const notes = [], rows = [];
  let units = null;
  // One villa or house: its whole program fills the villa fields (residential-options.mjs).
  if (program.building_type === 'villa') {
    const rooms = all.flatMap(u => u.rooms), total = role => rooms.filter(r => r.role === role).reduce((n, r) => n + r.count, 0);
    const stated = all.map(u => u.bathrooms).filter(v => v != null);
    const bathrooms = stated.length === all.length && all.length ? stated.reduce((n, v) => n + v, 0) : total('bathroom');
    return {...base(program), units:null, bedrooms:null, bathrooms:null, guests:null, rows:[], notes,
      villa:{bedrooms:total('bedroom') || null, master:rooms.some(r => r.role === 'bedroom' && r.ensuite) ? 'yes' : null,
        bathrooms:bathrooms || null, maid:total('maid') ? 'yes' : null, driver:total('driver') ? 'yes' : null}};
  }
  if (all.length) {
    if (perLevel.length === 1 && (occupied.length === levels.length || (pilotisGround && occupied.length === levels.length - 1)))
      units = {units:perLevel[0], scope:'per_level'};
    else units = {units:all.length, scope:'total'};
  }
  const same = values => values.length && values.every(v => v === values[0]) ? values[0] : null;
  const beds = all.map(bedroomsOf), baths = all.map(u => u.bathrooms ?? bathroomsOf(u));
  const bedrooms = same(beds), bathrooms = same(baths);
  // A uniform per-flat count goes to the flat fields; an uneven program keeps its
  // building total as a requirement when it divides evenly across the flats.
  for (const [role, list, uniform, label] of [['bedroom', beds, bedrooms, 'غرف النوم'], ['bathroom', baths, bathrooms, 'الحمامات']]) {
    if (uniform != null || !list.length) continue;
    const total = list.reduce((n, v) => n + v, 0);
    if (total % all.length === 0) rows.push({metric:'room_count', role, expected:total});
    else notes.push('مجموع '+label+' ('+total+') لا يتوزع بالتساوي على '+all.length+' شقق؛ أدخل العدد المطلوب يدويًا.');
  }
  if (bedrooms == null && beds.length) notes.push('برنامج كل دور مختلف: يرسم المولّد الحالي توزيعًا موحّدًا ويُرسل برنامج كل دور للنموذج وصفًا.');
  const majlis = all.map(u => counted(u, 'majlis') > 0);
  return {
    ...base(program), units,
    bedrooms:bedrooms != null && bedrooms >= 1 && bedrooms <= 8 ? bedrooms : null,
    bathrooms:bathrooms != null && bathrooms >= 1 && bathrooms <= 8 ? bathrooms : null,
    guests:!majlis.length ? null : majlis.every(Boolean) ? 'separate' : majlis.every(v => !v) ? 'none' : 'suggest',
    rows, notes, villa:null,
  };
}
// Land, building, street, plot and core values shared by buildings and villas.
function base(program) {
  const site = program.site, fp = site.footprint;
  return {width:site.width_m, depth:site.depth_m, levels:program.levels.length,
    buildingWidth:fp.width_m, buildingDepth:fp.depth_m,
    street:site.street_sides[0] || null, street2:site.street_sides[1] || null, streetWidth:site.street_width_m,
    setbacks:{...site.setbacks_m}, city:program.city || null,
    parking:{placement:placementOf[program.parking.placement] || null, count:program.parking.count},
    landing:program.core.landing_entries === true};
}

/** A short summary line per level for the card. */
export function levelSummary(level) {
  if (!level.units.length) return 'بلا شقق';
  const parts = level.units.length === 1 ? ['شقة واحدة'] : [level.units.length === 2 ? 'شقتان' : level.units.length + ' شقق'];
  const beds = level.units.reduce((n, u) => n + bedroomsOf(u), 0), baths = level.units.reduce((n, u) => n + bathroomsOf(u), 0);
  parts.push(beds + ' غرف نوم', baths + ' حمامات', level.units.reduce((n, u) => n + u.rooms.length, 0) + ' بندًا');
  return parts.join(' · ');
}

/** Values the program fixed in the confirmed fields, to notice later edits. */
export function programKey(program) {
  const s = program.site;
  return JSON.stringify([s.width_m, s.depth_m, program.levels.length, s.footprint.width_m, s.footprint.depth_m]);
}

export const clone = value => JSON.parse(JSON.stringify(value));
