// Plot rules for the brief form: parsing, a live envelope preview and the
// command block. The server (acs_plot_rules.py) is authoritative and resolves
// the same defaults; this preview only explains them before any paid call.
// Defaults: «اشتراطات إنشاء المباني السكنية», Ministry of Municipalities and
// Housing, July 2024 — always shown as editable assumptions, never as a ruling.
export const SIDES = ['N','E','S','W'];
export const SIDE_AR = {N:'الشمال',E:'الشرق',S:'الجنوب',W:'الغرب'};
export const SOURCE_URL = 'https://momah.gov.sa/sites/default/files/2024-07/ashtratat%20a%27nsha%20almbany%20alsknyt%20almnshwrt%20%60ly%20mwq%60%20alwzart%20.pdf';
export const SOURCE_TITLE = 'اشتراطات إنشاء المباني السكنية — وزارة البلديات والإسكان (2024)';
const DEFAULTS = {
  apartments:{frontMin:3,streetMin:2,neighbor:2,neighborTall:3,coverage:.65},
  villa:{frontMin:3,frontWide:6,streetMin:2,neighbor:1.5,neighborTall:1.5,coverage:.75},
};
export const ASSUMED_STREET_WIDTH = 15, STALL_W = 2.5, STALL_D = 5.5, PATH_W = 1.5, PILOTIS_M2_PER_STALL = 25, PILOTIS_CORE_M2 = 30;
export const PLACEMENTS = {front_setback:'في الارتداد الأمامي على الشارع',pilotis:'تحت المبنى في الدور الأرضي (بيلوتي)',none:'بدون مواقف في هذا المقترح (قبو أو حل لاحق)'};

// Arabic-Indic (٠-٩) and Extended (۰-۹) digits, Arabic decimal separator and units.
export function parseNumber(text) {
  if (text == null) return null;
  const s = String(text).normalize('NFKC')
    .replace(/[٠-٩]/g, c => String(c.charCodeAt(0) - 0x660))
    .replace(/[۰-۹]/g, c => String(c.charCodeAt(0) - 0x6f0))
    .replace(/[٫,،]/g, '.').replace(/[٪%]|م²|م|m/gi, '').replace(/\s+/g, '');
  if (!s) return null;
  return /^\d+(?:\.\d+)?$/.test(s) ? Number(s) : NaN;
}

const round2 = v => Math.round(v * 100) / 100;
const fmt = v => String(round2(v));

// Mirrors acs_plot_rules.resolve for the numbers shown before generation.
/** Is this brief one villa/house? Mirrors the server reading: the signed-in form
 *  appends «نوع المشروع: سكني / عمارة / فيلا» to every residential brief, so that
 *  category line is ignored; «بيت الدرج» is a stair core, not a house; apartment
 *  words win; and a confirmed count above one flat is never a villa. */
export function villaBrief(text, total = null) {
  return briefSays(text) === 'single_dwelling' && (!total || total === 1);
}
// The same word lists as acs_residential_access._brief_says: whole words with
// optional Arabic conjunction/preposition/article prefixes and pronoun suffixes.
// Plural or dual houses (فلل، بيوت، فيلتين) are several dwellings; any
// apartment word wins.
const OWNER = '(?:ي|ه|ها|نا|كم|هم)';
const feminine = (stem, dual = false) => stem + '(?:[ةه]|ت' + (dual ? '(?:ين|ان)|ت' : '') + OWNER + ')';
const wholeWords = stems => new RegExp('(?<![\\p{L}\\p{N}_])(?:و|ف)?(?:لل|ب|ل|ك)?(?:ال)?(?:' + stems.join('|') + ')' + OWNER + '?(?![\\p{L}\\p{N}_])', 'iu');
const HOUSE = wholeWords(['فيلا', feminine('فيل'), feminine('فل'), 'بيت', 'منزل', 'قصر', 'villa', 'house', 'townhouse']);
const APARTMENT = wholeWords([feminine('شق', true), 'شقق', feminine('عمار', true), 'عمائر', 'apartments?', 'flats?', 'condo(?:minium)?s?']);
const UNITS = /وحدات\s+سكني[ةه]|residential\s+units/i;
/** 'single_dwelling', 'apartments' or null, as the server reads a brief. */
export function briefSays(text) {
  const t = String(text || '').replace(/^\s*نوع المشروع\s*:.*$/gm, ' ').replace(/[أإآ]/g, 'ا')
    .replace(/بيت\s+(?:ال)?(?:درج|سلم|مصعد)/g, ' ');
  if (APARTMENT.test(t) || UNITS.test(t)) return 'apartments';
  return HOUSE.test(t) ? 'single_dwelling' : null;
}

// stall: [width, depth] (a confirmed program may state its own); building: the
// confirmed building [width, depth], whose ground floor holds pilotis parking.
export function preview({villa=false, levels=1, units=null, width, depth, streets=[], streetWidth=null,
                         setbacks={}, coverage=null, placement='front_setback', count=null, stall=[STALL_W, STALL_D], building=null}) {
  const d = villa ? DEFAULTS.villa : DEFAULTS.apartments, warnings = [];
  const W = Number(width), D = Number(depth);
  if (!(W > 0 && D > 0)) return {ready:false, warnings:['أدخل عرض الأرض وعمقها لحساب المساحة القابلة للبناء.']};
  const street = streets.length ? streets : ['N'], primary = street[0];
  const sw = streetWidth ?? ASSUMED_STREET_WIDTH;
  const neighbor = levels > 5 ? d.neighborTall : d.neighbor;
  const out = {}, sources = {};
  for (const side of SIDES) {
    if (setbacks[side] != null) { out[side] = setbacks[side]; sources[side] = 'user'; continue; }
    out[side] = round2(side === primary ? (villa && sw >= 30 ? d.frontWide : Math.max(d.frontMin, sw / 5))
      : street.includes(side) ? Math.max(d.streetMin, ASSUMED_STREET_WIDTH / 5) : neighbor);
    sources[side] = 'default';
  }
  const cov = coverage ?? d.coverage;
  const regulatory = villa ? (W * D <= 400 ? 1 : 2) : (units ? Math.ceil(1.5 * units - 1e-9) : null);
  const required = placement === 'none' ? 0 : (count ?? regulatory);
  const [stallW, stallD] = stall;
  let x0 = out.W, x1 = W - out.E, z0 = out.N, z1 = D - out.S;
  if (placement === 'front_setback' && required > 0 && out[primary] < stallD) {
    if (primary === 'N') z0 = stallD; else if (primary === 'S') z1 = D - stallD;
    else if (primary === 'W') x0 = stallD; else x1 = W - stallD;
  }
  if (x1 - x0 < 3 || z1 - z0 < 3) return {ready:false, setbacks:out, sources, coverage:cov, required,
    warnings:['الارتدادات لا تترك مساحة بناء كافية (أقل من 3 م). راجع الارتدادات أو مكان المواقف.']};
  const cap = cov * W * D;
  if ((x1 - x0) * (z1 - z0) > cap + 1e-6) {
    if (primary === 'N' || primary === 'S') { const depthCap = Math.floor(cap / (x1 - x0) * 100) / 100; if (primary === 'N') z1 = z0 + depthCap; else z0 = z1 - depthCap; }
    else { const widthCap = Math.floor(cap / (z1 - z0) * 100) / 100; if (primary === 'W') x1 = x0 + widthCap; else x0 = x1 - widthCap; }
  }
  const envelope = [round2(x0), round2(z0), round2(x1 - x0), round2(z1 - z0)], area = envelope[2] * envelope[3];
  const frontage = primary === 'N' || primary === 'S' ? W : D;
  const parkingArea = building ? building[0] * building[1] : area;
  let capacity = null;
  if (placement === 'front_setback' && required > 0) capacity = Math.max(0, Math.floor((frontage - PATH_W) / stallW + 1e-9) - 1);
  else if (placement === 'pilotis') capacity = Math.floor((parkingArea - PILOTIS_CORE_M2) / PILOTIS_M2_PER_STALL + 1e-9);
  // The required count is the owner's, or the stated regulatory default: an assumption they can lower.
  const requiredSource = count != null ? 'user' : 'default';
  const basis = requiredSource === 'user' ? 'من إدخالك' : villa ? 'افتراض نظامي لفيلا على أرض '+fmt(W * D)+' م²'
    : 'افتراض نظامي: 1.5 موقف لكل شقة × '+units+' شقق مقربة للأعلى';
  if (required == null && placement !== 'none') warnings.push('حدّد عدد الشقق أو عدد المواقف حتى تُحجز المواقف.');
  if (capacity != null && required != null && capacity < required) {
    const lower = requiredSource === 'user' ? 'قلّل «عدد المواقف» إلى '+Math.max(capacity, 0)+' أو أقل'
      : 'أدخل في «عدد المواقف» عددًا أقل ('+Math.max(capacity, 0)+' أو أقل) إن كان اشتراط أمانتك أقل، فالعدد '+required+' افتراض قابل للتعديل';
    warnings.push(placement === 'pilotis'
      ? 'المواقف المطلوبة '+required+' ('+basis+') ولا يتسع الدور الأرضي ('+fmt(parkingArea)+' م²) إلا لنحو '+Math.max(capacity, 0)+'. للمتابعة: '+lower
        +'، أو قلّل عدد الشقق، أو راجع الارتدادات، أو اختر «'+PLACEMENTS.none+'» إن كانت المواقف في قبو.'
      : 'المواقف المطلوبة '+required+' ('+basis+') ولا يتسع الارتداد الأمامي بطول '+fmt(frontage)+' م إلا لنحو '+capacity+' مع ممر المدخل. للمتابعة: '+lower
        +'، أو اختر مكان المواقف «'+PLACEMENTS.pilotis+'»، أو «'+PLACEMENTS.none+'» إن كانت المواقف في قبو.');
  }
  if (placement === 'pilotis' && levels < 2) warnings.push('المواقف تحت المبنى تحتاج دورين على الأقل.');
  if (placement === 'none' && regulatory) warnings.push('اخترت عدم تخصيص مواقف؛ الاشتراط الافتراضي '+regulatory+' مواقف وستظهر ملاحظة في المراجعة.');
  return {ready:true, setbacks:out, sources, coverage:cov, envelope, area, share:area / (W * D), required, requiredSource, basis, regulatory, capacity,
    frontage, warnings, ok:!warnings.some(w => /لا يتسع|تحتاج دورين|لا تترك/.test(w))};
}

// The server's deterministic plot refusals (acs_plot_rules.resolve), checked on the
// request about to be sent and before the paid confirmation: a plot the server would
// refuse never reaches the paid dialog. Same inputs as the server: the confirmed
// requirements, the brief, the plot block and a confirmed program card, which fills
// what the plot block leaves empty. Returns null, or {code, message} in Arabic.
// The checks the server makes later from the chosen option (flat area, the pilotis
// flat count) are not repeated here; the server still refuses them before any call.
export function plotPreflight({brief='', requirements=[], plot={}, program=null}) {
  const confirmed = metric => {
    const values = new Set((requirements || []).filter(r => r && r.metric === metric && r.expected != null).map(r => r.expected));
    return values.size === 1 ? [...values][0] : null;
  };
  const num = v => typeof v === 'number' && Number.isFinite(v);
  const W = confirmed('site_width_m'), D = confirmed('site_depth_m');
  if (!(num(W) && num(D) && W > 0 && D > 0))
    return {code:'PLOT_SITE_REQUIRED', message:'أدخل عرض الأرض وعمقها حتى تُحسب المساحة القابلة للبناء بعد الارتدادات.'};
  const said = briefSays(brief), count = confirmed('unit_count');
  const villa = (said === 'single_dwelling' && (count == null || count === 1)) || (said === null && count === 1);
  const lv = confirmed('level_count'), levels = Number.isInteger(lv) && lv > 0 ? lv : 1;
  const units = Number.isInteger(count) && count > 0 ? count : (villa ? 1 : null);
  const card = program && typeof program === 'object' ? program : null;
  const site = card?.site || {}, parking = card?.parking || {};
  const streets = plot.streets?.length ? plot.streets : (site.street_sides || []).filter(s => SIDES.includes(s)).slice(0, 2);
  const setbacks = {};
  for (const side of SIDES) {
    const given = plot.setbacks_m?.[side], stated = site.setbacks_m?.[side];
    if (num(given)) setbacks[side] = given; else if (num(stated)) setbacks[side] = stated;
  }
  let placement = plot.parking?.placement || 'front_setback';
  const ground = Array.isArray(card?.levels) && card.levels.length ? card.levels[0] : null;
  if (placement === 'front_setback' && ground && !ground.units?.length && (ground.use === 'parking' || parking.placement === 'pilotis')) placement = 'pilotis';
  const sw = parking.stall_width_m, sd = parking.stall_depth_m;
  const stall = num(sw) && num(sd) && sw >= 1.8 && sw <= 8 && sd >= 1.8 && sd <= 8 ? [sw, sd] : [STALL_W, STALL_D];
  let bw = confirmed('building_width_m'), bd = confirmed('building_depth_m');
  if (!(num(bw) && num(bd)) && num(site.footprint?.width_m) && num(site.footprint?.depth_m)) [bw, bd] = [site.footprint.width_m, site.footprint.depth_m];
  const building = num(bw) && num(bd) ? [bw, bd] : null;
  const count0 = Number.isInteger(plot.parking?.count) ? plot.parking.count : Number.isInteger(parking.count) ? parking.count : null;
  const p = preview({villa, levels, units, width:W, depth:D, streets,
    streetWidth:num(plot.street_width_m) ? plot.street_width_m : num(site.street_width_m) ? site.street_width_m : null,
    setbacks, coverage:num(plot.max_coverage) ? plot.max_coverage : null, placement, count:count0, stall, building});
  const refuse = (code, message) => ({code, message:message+' لم يُرسل أي طلب ولم يُستهلك أي رصيد؛ عدّل «الأرض والارتدادات والمواقف» في الخطوة 01 ثم أعد المحاولة.'});
  if (p.required == null && placement !== 'none') return refuse('PLOT_PARKING_COUNT_REQUIRED', 'حدّد عدد الشقق أو عدد المواقف المطلوبة حتى تُحجز المواقف.');
  if (!p.ready) return refuse('PLOT_ENVELOPE_EMPTY', p.warnings.join(' '));
  if (building && (building[0] > p.envelope[2] + 0.01 || building[1] > p.envelope[3] + 0.01))
    return refuse('PLOT_BUILDING_EXCEEDS_ENVELOPE', 'أبعاد المبنى المؤكدة '+fmt(building[0])+' × '+fmt(building[1])+' م أكبر من المساحة القابلة للبناء بعد الارتدادات '
      +fmt(p.envelope[2])+' × '+fmt(p.envelope[3])+' م. صغّر المبنى أو راجع الارتدادات.');
  if (placement === 'front_setback' && p.capacity != null && p.capacity < p.required)
    return refuse('PLOT_PARKING_DOES_NOT_FIT', p.warnings.find(w => w.includes('لا يتسع')));
  if (placement === 'pilotis' && levels < 2) return refuse('PLOT_PILOTIS_NEEDS_LEVELS', 'المواقف تحت المبنى تحتاج دورين على الأقل: دور أرضي للمواقف وفوقه الشقق.');
  if (placement === 'pilotis' && p.capacity < p.required) return refuse('PLOT_PARKING_DOES_NOT_FIT', p.warnings.find(w => w.includes('لا يتسع')));
  return null;
}

export function summaryText(p, placement) {
  if (!p.ready) return p.warnings.join(' ');
  const [, , w, d] = p.envelope;
  let text = 'المساحة القابلة للبناء ≈ '+fmt(w)+' × '+fmt(d)+' م = '+fmt(p.area)+' م² ('+Math.round(p.share*100)+'٪ من الأرض) بعد الارتدادات'
    +(p.sources && Object.values(p.sources).includes('default') ? ' (بعضها افتراضي)' : '')+' ونسبة بناء '+Math.round(p.coverage*100)+'٪.';
  if (placement === 'pilotis') text += ' الدور الأرضي للمواقف والمدخل، والشقق في الأدوار فوقه.';
  // The parking requirement against the capacity, before any paid request.
  if (p.required && !p.warnings.some(w => w.includes('المواقف المطلوبة'))) text += ' المواقف المطلوبة '+p.required+(p.basis ? ' ('+p.basis+')' : '')
    +(p.capacity != null ? '؛ السعة التقديرية '+p.capacity+(placement === 'pilotis' ? ' في الدور الأرضي' : ' في الارتداد الأمامي') : '')+'.';
  return [text, ...p.warnings].join(' ');
}

// The `plot` command block. Throws Arabic errors for unreadable input.
export function plotCommand({streets=[], streetWidth='', setbacks={}, coverage='', placement='front_setback', count='', landing=false}) {
  const number = (text, label, lo, hi) => {
    const v = parseNumber(text);
    if (v == null) return null;
    if (!Number.isFinite(v) || v < lo || v > hi) throw new Error('راجع '+label+': أدخل رقمًا بين '+lo+' و'+hi+'.');
    return v;
  };
  const sides = streets.filter(Boolean);
  if (new Set(sides).size !== sides.length) throw new Error('الشارع الثاني يجب أن يكون على جهة مختلفة عن الشارع الرئيسي.');
  const plot = {streets:sides, setbacks_m:{}, parking:{placement}, landing_entries:!!landing};
  const width = number(streetWidth, 'عرض الشارع', 4, 120);
  if (width != null) plot.street_width_m = width;
  for (const side of SIDES) { const v = number(setbacks[side], 'ارتداد '+SIDE_AR[side], 0, 30); if (v != null) plot.setbacks_m[side] = v; }
  const cov = number(coverage, 'نسبة البناء', 20, 100);
  if (cov != null) plot.max_coverage = round2(cov / 100);
  const n = number(count, 'عدد المواقف', 0, 500);
  if (n != null) { if (!Number.isInteger(n)) throw new Error('عدد المواقف يجب أن يكون عددًا صحيحًا.'); plot.parking.count = n; }
  if (!PLACEMENTS[placement]) throw new Error('اختر مكان المواقف.');
  return plot;
}

export const PLOT_SCOPE_NAMES = {plot_rules:'اشتراطات الأرض والمواقف (مدخلات وافتراضات معلنة)'};
export const PLOT_ISSUE_NAMES = {
  PLOT_OUTSIDE_ENVELOPE:'فراغات خارج المساحة القابلة للبناء',
  PLOT_COVERAGE_EXCEEDED:'نسبة البناء أكبر من الحد',
  PLOT_OPENING_ON_BOUNDARY:'فتحة على حد أرض الجار',
  PLOT_WINDOW_TOO_CLOSE:'نافذة قريبة من حد الجار',
  PLOT_WINDOW_BELOW_DEFAULT:'نافذة على ارتداد أقل من الافتراض النظامي',
  PLOT_PARKING_SHORTFALL:'المواقف أقل من المطلوب',
  PLOT_PARKING_NOT_PROVIDED:'لا مواقف في هذا المقترح',
  PLOT_UPPER_EXTERIOR_DOOR:'باب خارجي في دور علوي',
  PLOT_UPPER_TERRACE_DOOR:'باب علوي على سطح الدور الأسفل',
  PLOT_UPPER_ENTRANCE_LOBBY:'بهو المدخل يتكرر في دور علوي',
  PLOT_ENTRANCE_NOT_ON_STREET:'المدخل لا يطل على الشارع',
  PLOT_ENTRY_NOT_ON_LANDING:'مدخل الشقة ليس على بسطة الدرج',
  PLOT_DEAD_END_CORRIDOR:'ممر مشترك مسدود النهاية',
  PLOT_UNIT_AREA_OFF_TARGET:'مساحة الشقة بعيدة عن التقدير',
  PLOT_ZONING_MAJLIS_FAR:'المجلس بعيد عن المدخل',
  PLOT_ZONING_BEDROOM_AT_ENTRY:'غرفة نوم عند باب المدخل',
  PLOT_RULES_INVALID:'بيانات الأرض في النسخة غير صالحة',
};

// Drawing data for the plan: the dashed buildable envelope and, on the ground
// floor, the stalls the server derived. No authority: display only.
// The drawing shows the requested stalls, never the estimated capacity; a
// summary from an older server listed every stall that fits, so cap it here.
export function drawnStalls(parking) {
  const stalls = Array.isArray(parking?.stalls) ? parking.stalls : [];
  return Number.isInteger(parking?.required) && parking.required >= 0 ? stalls.slice(0, parking.required) : stalls;
}
export function overlay(summary, levelIndex) {
  if (!summary || !Array.isArray(summary.envelope)) return [];
  const [x, z, w, d] = summary.envelope;
  const shapes = [{tag:'rect', attrs:{x, y:z, width:w, height:d, fill:'none', stroke:'#2a9d8f', 'stroke-width':.08, 'stroke-dasharray':'.45 .3', 'data-plot':'envelope'}}];
  if (levelIndex === 0) for (const [sx, sz, sw, sd] of drawnStalls(summary.parking))
    shapes.push({tag:'rect', attrs:{x:sx, y:sz, width:sw, height:sd, fill:'rgba(233,196,106,.25)', stroke:'#b08a2e', 'stroke-width':.04, 'data-plot':'stall'}});
  return shapes;
}
