// Local, bounded reading of explicit quantities. It is not a general semantic
// parser. Unsupported and conditional prose remains in the original brief.
// All external source offsets are Unicode code points, matching Python slicing.
import {metricLabels,requirementMetrics} from '../generated/requirement-metrics.mjs';
export {metricLabels};
const roles = {bedroom:'غرف النوم',office:'المكاتب',kitchen:'المطابخ',living:'الصالات',bathroom:'دورات المياه',majlis:'المجالس',stairs:'الدرج',elevator:'المصاعد',maid_room:'غرف الخادمة',driver_room:'غرف السائق'};
// Digits as typed on an Arabic phone keyboard: Arabic-Indic or Persian digits and
// the Arabic decimal separator «٫». Length-preserving, so a caret can be kept.
export const asciiNumberText = text => String(text ?? '')
  .replace(/[\u0660-\u0669]/g, c => String(c.charCodeAt(0) - 0x660))
  .replace(/[\u06F0-\u06F9]/g, c => String(c.charCodeAt(0) - 0x6F0))
  .replace(/\u066B/g, '.');
// Also drops spaces, direction marks and the Arabic thousands separator «٬», and
// reads a single comma as the decimal separator («20,5» or «20،5»).
export function normalizeNumberText(text) {
  let out = asciiNumberText(text).replace(/[\u066C\s\u200E\u200F]/g, '');
  if (!out.includes('.') && /^[0-9]+[,،][0-9]+$/.test(out)) out = out.replace(/[,،]/, '.');
  return out;
}
// Planning limits checked before any paid request; they name the limit in Arabic.
export const PROGRAM_LIMITS = Object.freeze({
  residential: {side_m: 200, levels: 30, units_per_level: 20, units: 100, rooms_per_unit: 8},
  warehouse: {side_m: 1000, levels: 10},
});
// A per-floor row (a confirmed floor program, core/floor-program.mjs) is keyed by its floor too.
// Its labels repeat floor-program's ROLE_LABEL and floor names (a UI test keeps them equal).
export const requirementKey = r => JSON.stringify(Number.isInteger(r.level) ? [r.metric, r.role || '', r.level] : [r.metric, r.role || '']);
const floorRoles = {bedroom:'غرف النوم',bathroom:'الحمامات ودورات المياه',living:'الصالات',majlis:'المجالس',dining:'غرف الطعام',kitchen:'المطابخ',pantry:'مستودعات المؤن',laundry:'غرف الغسيل',storage:'المخازن',office:'المكاتب',dressing:'غرف الملابس',maid_room:'غرف الخادمة',driver_room:'غرف السائق',terrace:'التراسات',balcony:'الشرفات'};
const floorNames = ['الدور الأرضي','الدور الأول','الدور الثاني','الدور الثالث','الدور الرابع','الدور الخامس','الدور السادس','الدور السابع','الدور الثامن','الدور التاسع'];
const floorName = i => floorNames[i] ?? 'الدور ' + i;
const floorLabel = r => r.metric === 'ensuite_bedroom_count_by_level' ? 'غرف النوم بحمام خاص' : (floorRoles[r.role] || roles[r.role] || r.role);
export const requirementLabel = r => (r.metric==='room_count_per_unit' ? (roles[r.role]||r.role)+' في كل شقة'
  : ['room_count_by_level','ensuite_bedroom_count_by_level'].includes(r.metric) && Number.isInteger(r.level) ? floorLabel(r)+' في '+floorName(r.level)
  : r.metric==='room_count' && roles[r.role]) || metricLabels[r.metric] || r.metric;
export function warehouseRequirementsPreflight(requirements) {
  const reqs=Array.isArray(requirements)?requirements:[];
  const confirmed=metric=>{
    const values=reqs.filter(r=>r&&typeof r==='object'&&r.metric===metric).map(r=>r.expected);
    if(values.length!==1)return null;
    const value=values[0];
    return typeof value==='number'&&Number.isFinite(value)?value:null;
  };
  const w=confirmed('site_width_m'),d=confirmed('site_depth_m'),levels=confirmed('level_count'),target=confirmed('building_target_area_m2');
  if([w,d,levels,target].some(v=>v===null))return {status:'NOT_EVALUATED',may_generate_layout:true};
  const site=w*d;
  if(target>site*levels)return {status:'BUILDING_TARGET_EXCEEDS_THEORETICAL_FLOOR_AREA',site_area_m2:site,building_target_m2:target,level_count:levels,may_generate_layout:false};
  if(levels===1&&target>=site)return {status:'BUILDABLE_ENVELOPE_NOT_VERIFIED',site_area_m2:site,building_target_m2:target,level_count:levels,unallocated_site_area_m2:Math.max(0,site-target),may_generate_layout:false};
  return {status:'FEASIBLE_FOR_LAYOUT_PREFLIGHT',site_area_m2:site,building_target_m2:target,level_count:levels,unallocated_site_area_m2:levels?site-target/levels:null,may_generate_layout:true};
}

const normal = s => s.replace(/[٠-٩۰-۹أإآ]/g,c=>{
  const n=c.charCodeAt(0);
  return n>=0x6f0&&n<=0x6f9?String(n-0x6f0):n>=0x660&&n<=0x669?String(n-0x660):'ا';
}).replace(/٫/g,'.');
const cp = s => Array.from(s).length;
const N = '[0-9]+(?:\\.[0-9]+)?';
const U = '(?:millimeters?|centimeters?|metres?|meters?|mm|cm|m|مليمتر|سنتيمتر|امتار|مترا?|سم|مم|م)';
const site = '(?:الموقع|الارض|موقع|ارض|site|plot)';
const factor = u => /^(?:mm|millimeter|مم|مليمتر)/i.test(u)?0.001:/^(?:cm|centimeter|سم|سنتيمتر)/i.test(u)?0.01:1;
const ambiguous = /(?:\b(?:if|or|not|about|around|approximately|per|each)\b|(?:^|\s)و?(?:لا|ليس|بدون|اذا|ان|او)(?:\s|$)|تقريب|حوالي|نحو\s*[0-9]|تقارب|قراب[ةه]|لكل|كل\s+(?:دور|طابق|شقه|شقة)|[بل]الدور|[بل]الطابق|في\s+(?:الدور|الطابق)|(?:هذا|ذلك)\s+(?:الدور|الطابق)|[-−]\s*[0-9]|[0-9]\s*(?:[-–—/]|الى|to)\s*[0-9]|[0-9][,٬][0-9])/iu;
const bounded = /(?:على\s+(?:الاقل|الاكثر)|حد\s+(?:ادنى|اقصى)|at\s+(?:least|most)|minimum|maximum|less\s+than|more\s+than|[<>])/iu;
// مفردات محدودة لغرف النوم؛ لا نبدّل الكلمات في الوصف حتى تبقى شواهده حرفية.
const bedroomWords = Object.freeze({ثلاث:3,ثلاثة:3,اربع:4,اربعة:4,خمس:5,خمسة:5,ست:6,ستة:6,سبع:7,سبعة:7,ثمان:8,ثماني:8,ثمانية:8,تسع:9,تسعة:9,عشر:10,عشرة:10});
const wordBedroom = `(?<![\\p{L}\\p{N}.])(?:و\\s*)?(?<word>${Object.keys(bedroomWords).join('|')})\\s+غرف\\s+نوم(?![\\p{L}\\p{N}])`;
const oneLevel = /(?<![\p{L}\p{N}.])(?:و\s*)?(?:دور|طابق)\s+واحد(?![\p{L}\p{N}])/gu;
// «ألف وأربع» و«أربع عشرة» و«دور واحد ونصف» ليست أعدادًا بسيطة مؤكدة.
const numberWord = `(?:${Object.keys(bedroomWords).join('|')}|واحد|واحدة|احد|احدى|اثنان|اثنين|اثنتان|اثنتين|عشرون|عشرين|ثلاثون|ثلاثين|اربعون|اربعين|خمسون|خمسين|ستون|ستين|سبعون|سبعين|ثمانون|ثمانين|تسعون|تسعين|(?:ثلاث|اربع|خمس|ست|سبع|ثمان|تسع)\\s*م(?:ا)?ئة|مائة|مئة|مئتان|مئتين|مائتان|مائتين|الف|الفان|الفين|الاف|مليون|مليونان|مليونين|ملايين|مليار|مليارات|نصف|ربع|ثلث|${N})`;
const compoundBefore = new RegExp(`(?:^|\\s)${numberWord}\\s*(?:(?:و|الى|حتى)\\s*)?$`,'u');
const compoundAfter = new RegExp(`^\\s+(?:و\\s*)?${numberWord}(?![\\p{L}\\p{N}.])`,'u');
const followingBedroom = new RegExp(`^\\s*${wordBedroom}`,'u');
const wordRange = new RegExp(`(?:^|\\s)(?:الى|حتى)\\s+(?:و\\s*)?${numberWord}\\s+(?:غرف\\s+نوم|bedrooms?)(?![\\p{L}\\p{N}])`,'iu');
const compoundWordCount = (text,match) => {
  const after=text.slice(match.index+match[0].length);
  return compoundBefore.test(text.slice(0,match.index)) || (compoundAfter.test(after)&&!followingBedroom.test(after));
};

// The building's own size, separate from the land («عرض المبنى ٢٠ م وعمقه ٢٥ م»، «والمبنى ٢٠×٢٥ م»).
const building='(?:المبنى|العمار[ةه]|البناء|البناي[ةه])';
const buildingPair=`(?:ابعاد\\s+${building}|(?<![\\p{L}])و?(?:ال)?مبنى|العمار[ةه]\\s+(?:ابعادها|مقاسها))\\s*[:=]?\\s*(?<n>${N})\\s*[×x]\\s*(?<d>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`;
const sitePair=`(?:ابعاد\\s+${site}|${site}\\s+dimensions|${site})\\s*[:=]?\\s*(?<n>${N})\\s*[×x]\\s*(?<d>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`;
const buildingSides=[
  ['building_width_m',`عرض\\s+${building}\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
  ['building_depth_m',`(?:عمق\\s+${building}|(?<=عرض\\s+${building}[^،.\\n]{0,40})و?عمق(?:ه|ها))\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
];
const patterns=[
  ['site_width_m',`(?:عرض\\s+${site}|${site}\\s+(?:ب?عرض(?:ها)?|width))\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
  ['site_depth_m',`(?:عمق\\s+${site}|${site}\\s+(?:ب?عمق(?:ها)?|depth)|(?<=${site}\\s+عرضها[^،.\\n]{0,25})و?عمقها)\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
  ['level_count',`عدد\\s+(?:الادوار|الطوابق)\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
  ['level_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s*(?:ادوار|طوابق|floors?|storeys?|stories)(?![\\p{L}\\p{N}])`],
  ['room_count',`(?<![\\p{L}\\p{N}.])(?:و\\s*)?(?<n>${N})\\s+(?:غرف(?:ة|ه)?\\s+نوم|bedrooms?)(?![\\p{L}\\p{N}])`,'bedroom'],
  ['room_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:مكاتب|offices?)(?![\\p{L}\\p{N}])`,'office'],
  ['room_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:مطابخ|kitchens?)(?![\\p{L}\\p{N}])`,'kitchen'],
  ['dock_count',`عدد\\s+الارصفه?\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
  ['dock_count',`عدد\\s+الارصفة\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
  ['dock_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:ارصفه|ارصفة|docks?)(?![\\p{L}\\p{N}])`],
  ['min_rack_group_count',`(?:على\\s+الاقل|at\\s+least)\\s+(?<n>${N})\\s+(?:مجموعات\\s+رفوف|rack\\s+groups?)(?![\\p{L}\\p{N}])`],
];
// A plot's street frontage is its width along that street: «عرض الواجهة الشمالية ٢٠ م على الشارع».
const frontage=`عرض\\s+(?:ال)?واجه[ةه](?:\\s+(?:ال)?(?<side>شمالي|جنوبي|شرقي|غربي)[ةه])?\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])(?=[^،.\\n]{0,16}?(?:ال)?شارع)`;
const landFrontage=`(?:عرض\\s+)?(?:ال)?واجه[ةه]\\s+${site}\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`;
// The plot's own area («أرض مستطيلة مساحتها ٥٠٠ م²»): a check on width × depth, never a requirement.
const plotArea=`(?:مساح[ةه]\\s+${site}|(?<![\\p{L}])${site}(?:\\s+[\\p{L}\\u064B-\\u0652]+){0,2}?\\s+مساحت(?:ها|ه))\\s*[:=]?\\s*(?<n>[0-9]+(?:[,٬][0-9]{3})*(?:\\.[0-9]+)?)\\s*(?:م(?:تر)?\\s*(?:مربع|²)|m²|sqm)(?![\\p{L}\\p{N}])`;
// What a qualified sentence would have yielded: only these deserve a question.
const quantityHints=[...patterns.map(p=>p[1]),...buildingSides.map(p=>p[1]),buildingPair,sitePair,frontage,landFrontage,plotArea,
  `(?:ابعاد\\s+${site}|${site}\\s+dimensions|${site})\\s*[:=]?\\s*${N}\\s*[×x]\\s*${N}`].map(p=>new RegExp(p,'iu'));
// «أرضي وأول وثانٍ» lists every floor; «أرضي + ٢» counts the floors above the ground floor.
const ordinals=['اول','ثان','ثالث','رابع','خامس','سادس','سابع','ثامن','تاسع','عاشر'];
const storey='(?:(?:ال)?(?:دور|طابق)\\s+)?(?:ال)?';
const floorList=new RegExp(`(?<![\\p{L}])${storey}ارضي(?:\\s*(?:[،,+]\\s*)?و?\\s*${storey}(?:${ordinals.join('|')})(?:ي|[\\u064B-\\u0652])*(?![\\p{L}]))+`,'gu');
const groundPlus=/(?<![\p{L}])(?:ال)?ارضي\s*(?:\+|زائد)\s*(?<n>[0-9]+)(?![0-9]|\.[0-9]|\s*(?:ادوار|طوابق|دور|طابق))/gu;
const listGuard=/(?:^|\s)و?(?:لا|ليس|بدون|اذا|او)(?:\s|$)|تقريب|حوالي|(?:في|على|عن|الى)\s*$/u;
// Sentences inside one line: a full stop that is not a decimal point.
const sentences=chunk=>Array.from(chunk[0].matchAll(/(?:[^.]|\.(?=[0-9٠-٩۰-۹]))+\.?/gu),m=>({0:m[0],index:chunk.index+m.index}));
const scopeWords=/(?:\b(?:per|each)\b|كل\s+(?:دور|طابق|شقه|شقة)|لكل|[بل]الدور|[بل]الطابق|في\s+(?:الدور|الطابق)|(?:هذا|ذلك)\s+(?:الدور|الطابق))/iu;
const approximate=/(?:\b(?:about|around|approximately)\b|تقريب|حوالي|نحو\s*[0-9]|تقارب|قراب[ةه])/iu;
const rangeWords=/[0-9]\s*(?:[-–—/]|الى|to)\s*[0-9]/iu;
// The reason a sentence with a quantity is not read as an exact project total.
function qualifiedQuestion(text,quote){
  const q='«'+quote.trim().slice(0,200)+'»';
  if(rangeWords.test(text))return 'ورد نطاق أرقام في '+q+'. اختر قيمة واحدة مؤكدة وأدخلها في الحقل.';
  if(approximate.test(text))return 'القيمة تقريبية في '+q+'. أدخل القيمة المؤكدة في الحقل إن أردت اعتمادها.';
  if(scopeWords.test(text))return 'العدد في '+q+' لدور أو لشقة، لا للمبنى كله. أدخل الإجمالي المؤكد في الجدول، أو حدّد عدد الشقق ونطاقه في «الشقق واحتياجات الأسرة».';
  return 'راجع الشرط أو نطاق العدد في: '+q+'. أضف القيم الإجمالية المؤكدة في الحقول.';
}

export function analyzeBrief(brief) {
  if(typeof brief!=='string'||cp(brief)>60000)throw new Error('الوصف يتجاوز الحد المسموح.');
  const candidates=[],questions=[],seen=new Set(),areas=[];
  const chunks=brief.matchAll(/[^\n؛;!?؟]+/gu);
  const add=(metric,n,unit,match,base,source='requested',role)=>{
    const numeric=typeof n==='string'?n.replace(/[,٬]/g,''):n;
    const expected=Number(numeric)*(unit?factor(unit):1);
    if(!Number.isFinite(expected)||expected<0||(['level_count','room_count','dock_count','min_dock_count','min_rack_group_count'].includes(metric)&&!Number.isInteger(expected))){
      questions.push('ورد عدد غير صحيح: «'+match[0]+'». حدّد عددًا صحيحًا.');return;
    }
    const key=JSON.stringify([metric,role||'',expected]);if(seen.has(key))return;seen.add(key);
    const start=base+match.index,end=start+match[0].length;
    candidates.push({id:'text-'+cp(brief.slice(0,start))+'-'+metric,metric,expected,source,source_id:'brief:text',
      evidence:brief.slice(start,end),source_span:{start:cp(brief.slice(0,start)),end:cp(brief.slice(0,end))},
      confirmed:false,...(role?{role}:{})});
  };
  // An enumerated floor list stays exact even beside a per-floor qualifier
  // («أرضي وأول وثانٍ، وفي كل دور شقة»); a negation, condition or «أو» near it does not.
  const floorLists=(text,chunk)=>{
    const near=match=>listGuard.test(text.slice(Math.max(0,match.index-25),match.index))
      ||listGuard.test(text.slice(match.index,match.index+match[0].length+25).replace(/\s*$/,' '));
    for(const match of text.matchAll(floorList)){
      const named=Array.from(match[0].matchAll(new RegExp(ordinals.join('|'),'gu')),m=>m[0]);
      if(near(match)||!named.every((name,i)=>name===ordinals[i]))continue;
      add('level_count',1+named.length,null,match,chunk.index);
    }
    for(const match of text.matchAll(groundPlus))if(!near(match))add('level_count',Number(match.groups.n)+1,null,match,chunk.index);
  };
  const scan=(chunk,line)=>{
    const text=normal(chunk[0]);
    floorLists(text,chunk);
    const wordCounts=[
      ...Array.from(text.matchAll(new RegExp(wordBedroom,'gu')),match=>({metric:'room_count',role:'bedroom',n:bedroomWords[match.groups.word],match})),
      ...Array.from(text.matchAll(oneLevel),match=>({metric:'level_count',n:1,match})),
    ];
    // Building target area is a planning budget, not site area. Approximate
    // wording is intentionally reviewable/inferred rather than silently hard.
    const areaPattern=/(?:مساحة\s+(?:المبنى|مبنى(?:\s+المستودع)?)(?:\s+(?:المستهدفة|المغلقة))?|building\s+(?:target\s+)?area)\s*(?:تقارب|قرابة|حوالي|≈|~)?\s*[:=]?\s*(?<n>[0-9]+(?:[,٬][0-9]{3})*(?:\.[0-9]+)?)\s*(?:م(?:تر)?\s*(?:مربع|²)|m²|sqm)(?![\p{L}\p{N}])/giu;
    for(const match of text.matchAll(areaPattern))add('building_target_area_m2',match.groups.n,null,match,chunk.index,'inferred');
    // A comma-grouped measured area such as 5,000 m² is an ordinary
    // thousands separator, not a numeric range/decimal ambiguity. It may stay
    // in the brief without creating a noisy pre-generation question. We do
    // not promote it to a hard requirement unless a supported area phrase
    // matched above; confirmed form values remain the source of truth.
    const groupedMeasuredArea=/[0-9]+(?:[,٬][0-9]{3})+\s*(?:م(?:تر)?\s*(?:مربع|²)|m²|sqm)(?![\p{L}\p{N}])/iu;
    if((ambiguous.test(text)&&!areaPattern.test(text)&&!groupedMeasuredArea.test(text))||(wordCounts.length&&wordRange.test(text))){
      // Only the qualified sentence is held back; the line's other sentences are still read.
      const parts=line?sentences(chunk):[];
      if(parts.length>1){for(const part of parts)scan(part,false);return;}
      if(/[0-9]/.test(text)||wordCounts.length)if(wordCounts.length||quantityHints.some(hint=>hint.test(text)))questions.push(qualifiedQuestion(text,chunk[0]));
      return;
    }
    // «٣ أدوار غير الأرضي» and «أرضي + ٣ أدوار» are four floors with the ground floor.
    const groundAfter=/^\s+(?:غير|عدا|ماعدا|بخلاف|فوق)\s+(?:(?:ال)?(?:دور|طابق)\s+)?(?:ال)?ارضي(?![\p{L}\p{N}])/u;
    const groundBefore=/(?:^|[\s،.,])(?:ال)?ارضي\s*(?:\+|و|زائد)\s*$/u;
    const levelCount=(n,match)=>{
      const after=text.slice(match.index+match[0].length).match(groundAfter);
      const before=text.slice(0,match.index).match(groundBefore);
      if(!after&&!before)return add('level_count',n,null,match,chunk.index);
      const start=before?match.index-before[0].trimStart().length:match.index;
      const end=match.index+match[0].length+(after?after[0].length:0);
      add('level_count',Number(n)+1,null,{index:start,0:text.slice(start,end)},chunk.index);
    };
    for(const [metric,pattern] of buildingSides)for(const match of text.matchAll(new RegExp(pattern,'gu')))add(metric,match.groups.n,match.groups.u,match,chunk.index);
    for(const match of text.matchAll(new RegExp(buildingPair,'gu'))){
      add('building_width_m',match.groups.n,match.groups.u,match,chunk.index,'inferred');
      add('building_depth_m',match.groups.d,match.groups.u,match,chunk.index,'inferred');
    }
    for(const match of text.matchAll(new RegExp(plotArea,'gu')))
      areas.push({value:Number(match.groups.n.replace(/[,٬]/g,'')),match:{index:match.index,0:match[0]},base:chunk.index});
    for(const [pattern,street] of [[frontage,true],[landFrontage,false]]){
      for(const match of text.matchAll(new RegExp(pattern,'gu'))){
        const quote=chunk[0].substr(match.index,match[0].length);
        if(bounded.test(text)){questions.push('راجع الحد الأدنى أو الأعلى في: «'+chunk[0].trim().slice(0,200)+'». حدّد نوع المتطلب وقيمته قبل التوليد.');continue;}
        // An east or west street runs north–south: that frontage is the plot's depth (z), not its width (x).
        if(/شرقي|غربي/.test(match.groups.side||'')){
          questions.push('الواجهة على الشارع في «'+quote+'» '+(/شرقي/.test(match.groups.side)?'شرقية':'غربية')+'، وطولها يمتد من الشمال إلى الجنوب: أدخله في «عمق الموقع»، والبعد الآخر في «عرض الموقع»، واختر جهة الشارع.');continue;
        }
        add('site_width_m',match.groups.n,match.groups.u,match,chunk.index,street&&!match.groups.side?'inferred':'requested');
      }
    }
    for(const [metric,pattern,role] of patterns){
      for(const match of text.matchAll(new RegExp(pattern,'giu'))){
        // A minimum dock request must not become an exact count.
        const prefix=text.slice(Math.max(0,match.index-20),match.index);
        const minimum=metric==='dock_count'&&/(?:على\s+الاقل|at\s+least)\s*$/i.test(prefix);
        if(bounded.test(text)&&!minimum&&metric!=='min_rack_group_count'){
          questions.push('راجع الحد الأدنى أو الأعلى في: «'+chunk[0].trim().slice(0,200)+'». حدّد نوع المتطلب وقيمته قبل التوليد.');continue;
        }
        if(metric==='level_count'){levelCount(match.groups.n,match);continue;}
        add(minimum?'min_dock_count':metric,match.groups.n,match.groups.u,match,chunk.index,'requested',role);
      }
    }
    for(const {metric,role,n,match} of wordCounts){
      if(ambiguous.test(text)||bounded.test(text)||compoundWordCount(text,match)){
        questions.push('راجع العدد المركّب أو الشرط في: «'+chunk[0].trim().slice(0,200)+'». أضف العدد الإجمالي المؤكد في الحقول.');continue;
      }
      add(metric,n,null,match,chunk.index,'requested',role);
    }
    // Standalone project-dimension lines, never a room's dimensions or a
    // unitless number. An unlabelled pair still needs explicit order review.
    if(!bounded.test(text)){
      for(const [metric,label] of line?[['site_width_m','عرض'],['site_depth_m','عمق']]:[]){
        for(const pattern of [
          `^\\s*(?:ال)?${label}\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})\\s*[.،,]?\\s*$`,
          `^\\s*(?<n>${N})\\s*(?<u>${U})\\s+(?:ال)?${label}\\s*[.،,]?\\s*$`,
        ])for(const match of text.matchAll(new RegExp(pattern,'giu')))add(metric,match.groups.n,match.groups.u,match,chunk.index);
      }
      const compact=`^\\s*(?<n>${N})\\s*(?<u>${U})\\s*(?:×|x|في)\\s*(?<d>${N})\\s*(?<du>${U})\\s*[.،,]?\\s*$`;
      for(const match of line?text.matchAll(new RegExp(compact,'giu')):[]){
        add('site_width_m',match.groups.n,match.groups.u,match,chunk.index,'inferred');
        add('site_depth_m',match.groups.d,match.groups.du,match,chunk.index,'inferred');
      }
      for(const match of text.matchAll(/(?<![\p{L}])(?:دورين|دوران|طابقين|طابقان)(?![\p{L}])/gu))levelCount(2,match);
    }
    for(const match of text.matchAll(new RegExp(sitePair,'giu'))){
      add('site_width_m',match.groups.n,match.groups.u,match,chunk.index,'inferred');
      add('site_depth_m',match.groups.d,match.groups.u,match,chunk.index,'inferred');
    }
    // لا نفترض المتر لزوج بلا وحدة. تبقى الإجابة المؤكدة إدخالًا مستقلًا من المستخدم.
    const unitlessPair=`(?<![\\p{L}\\p{N}])(?:ابعاد\\s+${site}|${site}\\s+dimensions|${site})\\s*[:=]?\\s*${N}\\s*[×x]\\s*${N}(?![\\p{L}\\p{N}.])(?!\\s*${U}(?![\\p{L}\\p{N}²]))`;
    for(const match of text.matchAll(new RegExp(unitlessPair,'giu'))){
      const quote=chunk[0].slice(match.index,match.index+match[0].length);
      questions.push('أكّد وحدة أبعاد الموقع «'+quote+'» وترتيب العرض والعمق، ثم أدخل القيم بالمتر في الحقول.');
    }
  };
  for(const chunk of chunks)scan(chunk,true);
  // The plot's stated area checks width × depth, or supplies the one side not written.
  const stated=[...new Set(areas.map(a=>a.value))];
  let siteArea=null;
  if(stated.length>1)questions.push('وردت مساحة الأرض بأكثر من قيمة ('+stated.join(' و')+' م²). وضّح المساحة المقصودة.');
  else if(stated.length===1){
    const area=stated[0],fact=areas[0],one=metric=>{const v=[...new Set(candidates.filter(c=>c.metric===metric).map(c=>c.expected))];return v.length===1?v[0]:null;};
    const w=one('site_width_m'),d=one('site_depth_m'),start=fact.base+fact.match.index;
    siteArea={value:area,evidence:brief.slice(start,start+fact.match[0].length)};
    if(w&&d){
      if(Math.abs(w*d-area)>Math.max(0.5,area*0.01))questions.push('مساحة الأرض في الوصف ('+area+' م²) لا تساوي العرض × العمق ('+w+' × '+d+' = '+Math.round(w*d*100)/100+' م²). راجع الأبعاد قبل التأكيد.');
      else siteArea.matches=true;
    }else if(w||d){
      const other=Math.round(area/(w||d)*100)/100;
      if(other>0&&Math.abs(other*(w||d)-area)<=area*0.005)add(w?'site_depth_m':'site_width_m',other,null,fact.match,fact.base,'inferred');
    }
  }
  if(candidates.length>100)throw new Error('الوصف يحتوي متطلبات أكثر من الحد المسموح. اختصره قبل المتابعة.');
  return {candidates,questions:[...new Set(questions)],...(siteArea?{site_area_m2:siteArea}:{})};
}

export function buildBriefProgram(input) {
  const text=input.brief?.trim();
  if(!text)throw new Error('اكتب وصف المشروع أولًا.');
  if(cp(text)>58000)throw new Error('الوصف يتجاوز الحد المسموح.');
  if(!['residential','warehouse'].includes(input.type))throw new Error('اختر نوع المشروع.');
  const analysis=analyzeBrief(text), values=[
    {metric:'site_width_m',expected:input.width},
    {metric:'site_depth_m',expected:input.depth},
    {metric:'level_count',expected:input.levels},
    // Optional: the building's own size. Empty means the building fills the land.
    ...[['building_width_m',input.buildingWidth],['building_depth_m',input.buildingDepth]]
      .filter(([,value])=>value!==undefined&&value!==null&&String(value).trim()!=='').map(([metric,expected])=>({metric,expected})),
    ...(input.rows||[]).map(r=>({...r})),
  ];
  if(values.length>100)throw new Error('عدد المتطلبات يتجاوز الحد المسموح.');
  const known=new Map();
  for(const r of values){
    if(!Object.hasOwn(metricLabels,r.metric))throw new Error('نوع المتطلب غير مدعوم.');
    if(r.expected===''||r.expected===null||r.expected===undefined||(typeof r.expected==='string'&&!r.expected.trim()))throw new Error('حدّد '+requirementLabel(r)+'؛ القيمة غير محددة.');
    if(!['number','string'].includes(typeof r.expected))throw new Error('أدخل قيمة رقمية في '+requirementLabel(r)+'.');
    if(typeof r.expected==='string')r.expected=normalizeNumberText(r.expected);
    r.expected=Number(r.expected);
    if(!Number.isFinite(r.expected)||r.expected<0||(['site_width_m','site_depth_m','building_width_m','building_depth_m','level_count'].includes(r.metric)&&r.expected<=0))throw new Error('أدخل أبعادًا وأعداد أدوار موجبة، وقيم متطلبات غير سالبة.');
    if(!['min_space_area_by_role_m2','building_target_area_m2'].includes(r.metric)&&!r.metric.endsWith('_m')&&!Number.isInteger(r.expected))throw new Error('أدخل عددًا صحيحًا في '+requirementLabel(r)+'.');
    if(['room_count','room_count_per_unit','min_space_area_by_role_m2'].includes(r.metric)){
      r.role=r.role?.trim();if(!r.role||r.role.length>80)throw new Error('حدد استخدام الفراغ للمتطلب.');
    }else delete r.role;
    const key=requirementKey(r);
    if(known.has(key))throw new Error('تعارض أو تكرار في '+requirementLabel(r)+'. اجمعه في متطلب واحد.');
    known.set(key,r);
  }
  const limits=PROGRAM_LIMITS[input.type],kind=input.type==='residential'?'للمشاريع السكنية':'للمستودعات';
  for(const r of known.values()){
    if(['site_width_m','site_depth_m','building_width_m','building_depth_m'].includes(r.metric)&&r.expected>limits.side_m)
      throw new Error(requirementLabel(r)+' ('+r.expected+' م) أكبر من الحد المدعوم '+kind+' ('+limits.side_m+' م). راجع القيمة؛ وإن كانت صحيحة فقسّم المشروع إلى مبانٍ أصغر.');
    if(r.metric==='level_count'&&r.expected>limits.levels)
      throw new Error('عدد الأدوار ('+r.expected+') أكبر من الحد المدعوم '+kind+' ('+limits.levels+' دورًا). راجع العدد قبل المتابعة.');
  }
  for(const [building,land] of [['building_width_m','site_width_m'],['building_depth_m','site_depth_m']]){
    const b=known.get(requirementKey({metric:building})),l=known.get(requirementKey({metric:land}));
    if(b&&l&&b.expected>l.expected+1e-8)throw new Error(requirementLabel(b)+' ('+b.expected+') أكبر من '+requirementLabel(l)+' ('+l.expected+'). المبنى يقع داخل الأرض؛ صحّح أحدهما.');
  }
  if(input.type==='warehouse'){
    const preflight=warehouseRequirementsPreflight(values);
    if(!preflight.may_generate_layout){
      if(preflight.status==='BUILDABLE_ENVELOPE_NOT_VERIFIED')throw new Error('مساحة المبنى المستهدفة تستهلك كامل مساحة الموقع في مشروع من دور واحد. أدخل مساحة مبنى أصغر أو موقعًا أكبر؛ لن يخترع ACS ارتدادات أو أبعادًا تنظيمية.');
      if(preflight.status==='BUILDING_TARGET_EXCEEDS_THEORETICAL_FLOOR_AREA')throw new Error('مساحة المبنى المستهدفة أكبر من المساحة النظرية المتاحة عبر عدد الأدوار المؤكد. عدّل مساحة المبنى أو أبعاد الموقع أو عدد الأدوار قبل الانتقال إلى البدائل.');
    }
  }
  const grouped=new Map();
  for(const c of analysis.candidates){
    const key=requirementKey(c), previous=grouped.get(key);
    if(previous&&Math.abs(previous.expected-c.expected)>1e-8)throw new Error('تعارض في الوصف: '+requirementLabel(c)+' ورد بأكثر من قيمة. وضّح القيمة المطلوبة في الوصف.');
    grouped.set(key,c);
    const r=known.get(key);
    if(!r)throw new Error('ورد متطلب '+requirementLabel(c)+' في الوصف. أضفه إلى البرنامج قبل التأكيد.');
    if(Math.abs(r.expected-c.expected)>1e-8)throw new Error('تعارض بين الوصف والحقول في '+requirementLabel(c)+'. صحّح الوصف أو القيمة قبل التوليد.');
  }

  // Requirement ids are provenance identities, not row positions. Preserve an
  // unambiguous stored id when the same requirement/value and exact evidence
  // survive a revision. Older connected-workspace revisions did not store a
  // source_span, so migrate them only when their evidence occurs exactly once.
  const saved=Array.isArray(input.savedRequirements)?input.savedRequirements:[];
  const savedIdCounts=new Map();
  for(const p of saved){
    if(p&&typeof p.id==='string'&&p.id.trim()&&p.id.length<=160)
      savedIdCounts.set(p.id,(savedIdCounts.get(p.id)||0)+1);
  }
  const recoverSource=p=>{
    if(!p||typeof p!=='object'||typeof p.evidence!=='string'||!p.evidence)return null;
    const span=p.source_span;
    if(span&&Number.isInteger(span.start)&&Number.isInteger(span.end)&&span.start>=0&&span.end>span.start&&span.end<=cp(text)
        &&Array.from(text).slice(span.start,span.end).join('')===p.evidence)return {...p,source_span:{start:span.start,end:span.end}};
    const first=text.indexOf(p.evidence);
    if(first<0||text.indexOf(p.evidence,first+p.evidence.length)>=0)return null;
    return {...p,source_span:{start:cp(text.slice(0,first)),end:cp(text.slice(0,first+p.evidence.length))}};
  };
  const reusable=saved.map(recoverSource).filter(p=>p&&typeof p.id==='string'&&p.id.trim()&&p.id.length<=160&&savedIdCounts.get(p.id)===1);
  // Every previously valid provenance id is retired from fresh allocation even
  // when its evidence is edited away. Only `reusable` ids may be preserved.
  const reservedIds=new Set(savedIdCounts.keys()), usedIds=new Set();
  let nextId=0;
  const freshId=()=>{
    let id;
    do{id='brief-'+nextId++;}while(usedIds.has(id)||reservedIds.has(id));
    usedIds.add(id);return id;
  };

  const typeLine='نوع المشروع: '+(input.type==='warehouse'?'مستودع / صناعي':'سكني / عمارة / فيلا');
  let brief=text.split('\n').includes(typeLine)?text:text+'\n\n'+typeLine;
  const requirements=[];
  for(const r of values){
    const matches=reusable.filter(p=>requirementKey(p)===requirementKey(r)&&Number(p.expected)===r.expected);
    const prior=matches.length===1?matches[0]:null;
    const extracted=grouped.get(requirementKey(r));
    let source=prior || extracted;
    if(!source){
      const evidence=requirementLabel(r)+(r.role?' ('+r.role+')':'')+': '+r.expected;
      const start=cp(brief)+1;brief+='\n'+evidence;
      source={source:'requested',source_id:'brief:form',evidence,source_span:{start,end:cp(brief)}};
    }
    let id=prior?.id;
    if(!id||usedIds.has(id))id=freshId();else usedIds.add(id);
    requirements.push({id,metric:r.metric,expected:r.expected,...(r.role?{role:r.role}:{}),
      source:source.source,source_id:source.source_id,evidence:source.evidence,source_span:{...source.source_span},confirmed:true});
  }
  if(cp(brief)>60000)throw new Error('الوصف مع المتطلبات يتجاوز الحد المسموح.');
  return {brief,requirements};
}
