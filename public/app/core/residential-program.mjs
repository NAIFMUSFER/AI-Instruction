const normalize = text => text.normalize('NFKC').replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)>0x6ef?c.charCodeAt(0)-0x6f0:c.charCodeAt(0)-0x660)).replace(/[أإآ]/g,'ا').replace(/ة/g,'ه');
const words = {'واحد':1,'واحده':1,'اثنين':2,'اثنتين':2,'ثلاث':3,'ثلاثه':3,'اربع':4,'اربعه':4,'خمس':5,'خمسه':5,'ست':6,'سته':6};
const quantity = v => words[v] || Number(v);
export function readResidential(text) {
  const s=normalize(text), out={};
  const n='(\\d{1,3}|ثلاثه?|اربعه?|خمسه?|سته?)';
  const unit=s.match(new RegExp(n+'\\s*(?:شقق|شقه|وحدات سكنيه|apartments?|flats?)','i'));
  if(unit){out.units=quantity(unit[1]);out.scope=/في\s*كل\s*(?:دور|طابق)|كل\s*(?:دور|طابق)\s*\d|لكل\s*(?:دور|طابق)|per\s*(?:floor|storey)/i.test(s)?'per_level':'total';out.unitEvidence=unit[0];}
  if(/شقتين|شقتان/.test(s)){out.units=2;out.scope=/كل\s*(?:دور|طابق)/.test(s)?'per_level':'total';}
  // «وفي كل دور شقة» and «شقة واحدة في كل دور»: one flat on every floor.
  const single=out.units?null:s.match(/(?:كل|لكل)\s*(?:دور|طابق)\s*(?:فيه\s+|به\s+)?(?:ال)?شقه(?:\s+واحده)?(?![ء-ي])|(?:^|[\s،.,])(?:ال)?شقه\s+(?:واحده\s+)?(?:في|لكل|بكل)\s*(?:كل\s*)?(?:دور|طابق)(?![ء-ي])/);
  if(single){out.units=1;out.scope='per_level';out.unitEvidence=single[0].trim();}
  const floors=s.match(new RegExp(n+'\\s*(?:ادوار|طوابق|floors?)','i'));
  if(floors)out.levels=quantity(floors[1]);else if(/دورين|دوران|طابقين|طابقان/.test(s))out.levels=2;
  const bedrooms=s.match(new RegExp('(?:كل شقه|لكل شقه|في الشقه)[^؛\\n]{0,35}?'+n+'\\s*غرف(?:ه)?\\s*نوم'));
  if(bedrooms)out.bedrooms=quantity(bedrooms[1]);
  if(/مجلس\s*(?:منفصل|مستقل)/.test(s))out.guests='separate';
  // The street side: «الواجهة الشمالية … على الشارع», «الشارع من الشمال», «أرض شمالية».
  const sides=new Set(),side={شمال:'N',جنوب:'S',شرق:'E',غرب:'W'};
  for(const m of s.matchAll(/واجهه\s+(?:ال)?(شمال|جنوب|شرق|غرب)يه[^.\n؛]{0,40}?(?:على|علي|تطل\s+على|مطله\s+على)\s+(?:ال)?شارع(?![ء-ي])/g))sides.add(side[m[1]]);
  for(const m of s.matchAll(/(?:^|[\s،.,])و?(?:ال)?شارع\s+(?:(?:من|في)\s+)?(?:(?:ال)?(?:جهه|ناحيه)\s+)?(?:ال)?(شمال|جنوب|شرق|غرب)(?:ي|يه)?(?![ء-ي])/g))sides.add(side[m[1]]);
  for(const m of s.matchAll(/(?:^|[\s،.,])(?:ال)?(?:ارض|قطعه)\s+(شمال|جنوب|شرق|غرب)يه(?![ء-ي])/g))sides.add(side[m[1]]);
  if(sides.size===1)out.street=[...sides][0];
  return out;
}
export function residentialOptions({units,scope='total',levels,width,depth,bedrooms,bathrooms,guests='suggest',purpose='unknown'}) {
  units=Number(units);levels=Number(levels);
  if(!Number.isInteger(units)||units<1||units>100||!Number.isInteger(levels)||levels<1||levels>30)throw new Error('حدد عدد الشقق والأدوار للمقارنة.');
  const total=scope==='per_level'?units*levels:units;
  if(total<levels)throw new Error('عدد الشقق أقل من الأدوار؛ وضّح توزيع الأدوار غير السكنية في وصفك.');
  const distribution=Array.from({length:levels},(_,i)=>Math.floor(total/levels)+(i<total%levels?1:0));
  const variants=[{id:'A',title:'صالة أوسع',bedrooms:2,majlis:0,why:'يعطي مساحة أكبر لاجتماع الأسرة.',tradeoff:'عدد غرف نوم أقل من خيار الأسرة الكبيرة.'},{id:'B',title:'غرف أكثر للأسرة',bedrooms:3,majlis:0,why:'يوفر غرفًا مستقلة لعدد أكبر من أفراد الأسرة.',tradeoff:'تقل المساحة المتاحة للصالة عند ثبات مساحة الشقة.'},{id:'C',title:'خصوصية الضيوف',bedrooms:2,majlis:1,why:'يفصل استقبال الضيوف عن حركة الأسرة.',tradeoff:'المجلس ومدخله يحتاجان مساحة إضافية.'}];
  return variants.map(o=>{
    const count=bedrooms===''||bedrooms==null?o.bedrooms:Number(bedrooms), baths=bathrooms===''||bathrooms==null?2:Number(bathrooms);
    if(!Number.isInteger(count)||count<1||count>8||!Number.isInteger(baths)||baths<1||baths>8)throw new Error('راجع عدد غرف النوم ودورات المياه لكل شقة.');
    const majlis=guests==='separate'?1:guests==='none'?0:o.majlis;
    const areas={bedroom:12,living:o.id==='A'?24:18,kitchen:10,bathroom:4.5,majlis:18,circulation:10};
    const estimatedUnitArea=(count*areas.bedroom+areas.living+areas.kitchen+baths*areas.bathroom+majlis*areas.majlis+areas.circulation)*1.15;
    const available=Number(width)*Number(depth),required=estimatedUnitArea*Math.max(...distribution)+25;
    return {...o,bedrooms:count,bathrooms:baths,majlis,total,distribution,scope,units,areas,
      recommended:(guests==='separate'?o.id==='C':purpose==='family'?o.id==='B':o.id==='A'),
      estimatedUnitArea:Math.round(estimatedUnitArea),requiredFloorArea:Math.round(required),
      feasible:Number.isFinite(available)&&available>0&&required<=available,
      feasibilityNote:'تقدير مساحة أولي يشمل حركة داخلية و15٪ للجدران و25 م² للنواة المشتركة؛ لا يشمل الارتدادات والمواقف. يفحص التوزيع والفتحات بعد التوليد.'};
  });
}

// ── One villa or house: the step-01 villa program ───────────────────────────
// The fields become confirmed requirement rows (room_count per role and
// ensuite_bedroom_count) that the server measures; acs_villa_program.py checks
// the livability rules the counts cannot see. Defaults are stated, editable
// planning assumptions.
export const VILLA_SOURCE = 'brief:villa-program';
export const VILLA_DEFAULTS = Object.freeze({bedrooms: 4, master: true, maid: false, driver: false});
export const VILLA_LIMITS = Object.freeze({bedrooms: 10, bathrooms: 14});
const whole = (text, label, lo, hi) => {
  const s = normalize(String(text ?? '')).replace(/[\s‎‏]/g, '');
  if (s === '') return null;
  const n = Number(s);
  if (!/^[0-9]+$/.test(s) || n < lo || n > hi) throw new Error(label + ': أدخل عددًا صحيحًا من ' + lo + ' إلى ' + hi + '.');
  return n;
};
const yes = v => v === true || v === 'yes';
/** Resolve the villa fields (text as typed, Arabic-Indic digits accepted) with
 *  their defaults: 4 bedrooms, a master suite, bathrooms = bedrooms + 1 (the
 *  guest WC) plus one WC per service room, no maid's or driver's room. */
export function villaProgram({bedrooms = '', master = 'yes', bathrooms = '', maid = 'no', driver = 'no'} = {}) {
  const beds = whole(bedrooms, 'غرف النوم', 1, VILLA_LIMITS.bedrooms) ?? VILLA_DEFAULTS.bedrooms;
  const suite = yes(master), hasMaid = yes(maid), hasDriver = yes(driver);
  const auto = beds + 1 + (hasMaid ? 1 : 0) + (hasDriver ? 1 : 0);
  const typed = whole(bathrooms, 'الحمامات ودورات المياه', 1, VILLA_LIMITS.bathrooms);
  const baths = typed ?? Math.min(auto, VILLA_LIMITS.bathrooms);
  const least = (suite ? 2 : 1) + (hasMaid ? 1 : 0) + (hasDriver ? 1 : 0);
  if (baths < least) throw new Error('الحمامات ودورات المياه (' + baths + ') أقل من الحد الأدنى لهذا البرنامج (' + least + '): '
    + (suite ? 'حمام خاص لغرفة النوم الرئيسية و' : '') + 'دورة مياه للضيوف' + (hasMaid || hasDriver ? ' ودورة مياه لكل غرفة خدمة' : '') + '.');
  return {bedrooms: beds, master: suite, bathrooms: baths, autoBathrooms: typed == null, maid: hasMaid, driver: hasDriver};
}
// Arabic counting: 1 مفرد، 2 مثنى، 3–10 جمع، 11+ مفرد.
const counted = (n, one, two, few, many) => n === 1 ? one : n === 2 ? two : n >= 3 && n <= 10 ? n + ' ' + few : n + ' ' + many;
export const bedroomsText = n => counted(n, 'غرفة نوم واحدة', 'غرفتا نوم', 'غرف نوم', 'غرفة نوم');
export const bathroomsText = n => counted(n, 'حمام واحد', 'حمامان', 'حمامات ودورات مياه', 'حمامًا ودورة مياه');
/** One line for the owner: what the program asks for, defaults included. */
export function villaSummary(p) {
  return bedroomsText(p.bedrooms) + (p.master ? '، منها غرفة نوم رئيسية بحمام خاص' : '') + '؛ '
    + bathroomsText(p.bathrooms) + ' منها دورة مياه للضيوف' + (p.master ? ' والحمام الخاص' : '')
    + (p.maid || p.driver ? ' ودورة مياه لكل غرفة خدمة' : '') + (p.autoBathrooms ? ' (تلقائي)' : '') + '؛ '
    + (p.maid ? 'غرفة خادمة' : 'بدون غرفة خادمة') + '؛ ' + (p.driver ? 'غرفة سائق' : 'بدون غرفة سائق') + '.';
}
/** Confirmed requirement rows for the program: [{metric, role?, expected, label}]. */
export function villaRows(p) {
  const rows = [{metric: 'room_count', role: 'bedroom', expected: p.bedrooms, label: 'غرف النوم في الفيلا'}];
  if (p.master) rows.push({metric: 'ensuite_bedroom_count', expected: 1, label: 'غرف نوم بحمام خاص'});
  rows.push({metric: 'room_count', role: 'bathroom', expected: p.bathrooms, label: 'الحمامات ودورات المياه في الفيلا'});
  if (p.maid) rows.push({metric: 'room_count', role: 'maid_room', expected: 1, label: 'غرفة الخادمة'});
  if (p.driver) rows.push({metric: 'room_count', role: 'driver_room', expected: 1, label: 'غرفة السائق'});
  return rows;
}
/** Bedrooms and service rooms written in a villa brief («٥ غرف نوم»، «غرفة خادمة»). */
export function readVilla(text) {
  const s = normalize(String(text || '')), out = {};
  const n = '(\\d{1,2}|ثلاثه?|اربعه?|خمسه?|سته?)';
  const beds = s.match(new RegExp('(?<![\\p{L}\\p{N}])' + n + '\\s*غرف(?:ه)?\\s*نوم', 'u'));
  if (beds) out.bedrooms = quantity(beds[1]);
  if (/غرف[هة]?\s*(?:ال)?(?:خادم|عامل|شغال)/.test(s)) out.maid = 'yes';
  if (/غرف[هة]?\s*(?:ال)?سائق/.test(s)) out.driver = 'yes';
  return out;
}
// Three villa concepts that differ in what they give space to. Areas are
// planning assumptions (m²), not a design: each card's estimate is the sum of
// its rooms plus walls and circulation.
const VILLA_VARIANTS = [
  {id: 'A', title: 'بيت عائلي مدمج', factor: 1.15,
   areas: {bedroom: 13, master: 18, ensuite: 5, bath: 4.5, guestWc: 2.5, majlis: 20, living: 24, dining: 12, kitchen: 12, entrance: 6, service: 9, stairs: 12},
   rooms: 'مجلس بجوار المدخل، صالة أسرة مفتوحة على الطعام، مطبخ',
   why: 'أقل مساحة مبنية لنفس عدد الغرف، فتبقى مساحة أكبر للحديقة والمواقف.',
   tradeoff: 'الضيوف والأسرة يتشاركون المدخل، والغرف بمقاسات اقتصادية.'},
  {id: 'B', title: 'فصل الضيوف عن العائلة', factor: 1.2,
   areas: {bedroom: 14, master: 20, ensuite: 6, bath: 4.5, guestWc: 3, majlis: 28, guestDining: 16, guestEntrance: 6, living: 28, dining: 12, kitchen: 14, entrance: 6, service: 9, stairs: 12},
   rooms: 'مدخل ومجلس ومقلط ودورة مياه للضيوف منفصلة، ومدخل وصالة وطعام للأسرة، مطبخ',
   why: 'يدخل الضيوف إلى المجلس دون المرور بمنطقة الأسرة.',
   tradeoff: 'مدخلان ومقلط يحتاجان مساحة إضافية في الدور الأرضي.'},
  {id: 'C', title: 'جناح رئيسي واسع', factor: 1.2,
   areas: {bedroom: 14, master: 26, ensuite: 9, dressing: 6, bath: 4.5, guestWc: 2.5, majlis: 22, living: 28, dining: 14, kitchen: 14, entrance: 6, service: 9, stairs: 12},
   rooms: 'جناح رئيسي بحمام واسع وغرفة ملابس، مجلس، صالة أسرة، طعام، مطبخ',
   why: 'غرفة نوم رئيسية أوسع مع غرفة ملابس وحمام أكبر.',
   tradeoff: 'تصغر الصالة أو الغرف الأخرى إن ضاقت المساحة المبنية.'},
];
/** Villa option cards: {id, title, roomsText, why, tradeoff, estimatedArea, available, feasible, recommended}.
 *  ``buildable`` is the footprint (m²) left by the setbacks, or null when unknown. */
export function villaOptions(program, {levels = 1, buildable = null, guests = 'suggest'} = {}) {
  const floors = Number.isInteger(Number(levels)) && Number(levels) >= 1 ? Number(levels) : 1;
  const available = Number.isFinite(buildable) && buildable > 0 ? Math.round(buildable * floors) : null;
  return VILLA_VARIANTS.map(v => {
    const a = v.areas, others = program.bedrooms - (program.master ? 1 : 0);
    const shared = program.bathrooms - 1 - (program.master ? 1 : 0) - (program.maid ? 1 : 0) - (program.driver ? 1 : 0);
    let sum = others * a.bedroom + (program.master ? a.master + a.ensuite + (a.dressing || 0) : a.bedroom)
      + Math.max(0, shared) * a.bath + a.guestWc + a.majlis + (a.guestDining || 0) + (a.guestEntrance || 0)
      + a.living + a.dining + a.kitchen + a.entrance + (program.maid ? a.service + 2.5 : 0) + (program.driver ? a.service + 2.5 : 0)
      + (floors > 1 ? a.stairs * floors : 0);
    const estimatedArea = Math.round(sum * v.factor);
    return {...v, villa: true, program, levels: floors, estimatedArea, available,
      feasible: available == null || estimatedArea <= available,
      recommended: guests === 'separate' ? v.id === 'B' : v.id === 'A',
      roomsText: bedroomsText(program.bedrooms) + (program.master ? ' منها رئيسية بحمام خاص' : '') + '، ' + bathroomsText(program.bathrooms)
        + '، ' + v.rooms + (program.maid ? '، غرفة خادمة' : '') + (program.driver ? '، غرفة سائق' : '') + '.'};
  });
}
// Arabic names of the villa review findings (acs_villa_program.py) and scope.
export const VILLA_ISSUE_NAMES = Object.freeze({
  VILLA_AGGREGATE_ROOM: 'فراغ واحد يجمع عدة غرف',
  VILLA_BEDROOM_OVERSIZED: 'غرفة نوم أكبر من المعتاد',
  VILLA_NO_BATHROOM: 'المسكن بلا حمام',
  VILLA_FLOOR_WITHOUT_BATHROOM: 'دور فيه غرف نوم بلا حمام',
  VILLA_GUEST_WC_MISSING: 'لا دورة مياه للضيوف في الدور الأرضي',
  VILLA_MAJLIS_FAR: 'المجلس بعيد عن المدخل',
  VILLA_KITCHEN_INTERIOR: 'المطبخ بلا جدار خارجي',
  VILLA_ENSUITE_MISSING: 'غرفة النوم الرئيسية بلا حمام خاص',
});
export const VILLA_SCOPE_NAMES = Object.freeze({dwelling_program: 'برنامج الفيلا وصلاحية السكن'});
