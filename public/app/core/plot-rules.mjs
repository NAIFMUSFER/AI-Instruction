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
export function preview({villa=false, levels=1, units=null, width, depth, streets=[], streetWidth=null,
                         setbacks={}, coverage=null, placement='front_setback', count=null}) {
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
  let x0 = out.W, x1 = W - out.E, z0 = out.N, z1 = D - out.S;
  if (placement === 'front_setback' && required > 0 && out[primary] < STALL_D) {
    if (primary === 'N') z0 = STALL_D; else if (primary === 'S') z1 = D - STALL_D;
    else if (primary === 'W') x0 = STALL_D; else x1 = W - STALL_D;
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
  let capacity = null;
  if (placement === 'front_setback' && required > 0) capacity = Math.max(0, Math.floor((frontage - PATH_W) / STALL_W + 1e-9) - 1);
  else if (placement === 'pilotis') capacity = Math.floor((area - PILOTIS_CORE_M2) / PILOTIS_M2_PER_STALL + 1e-9);
  if (required == null && placement !== 'none') warnings.push('حدّد عدد الشقق أو عدد المواقف حتى تُحجز المواقف.');
  if (capacity != null && required != null && capacity < required)
    warnings.push('المواقف المطلوبة '+required+' ولا يتسع '+(placement==='pilotis'?'الدور الأرضي':'الارتداد الأمامي')+' إلا لنحو '+capacity+'. '+(placement==='pilotis'?'قلّل عدد الشقق أو راجع الارتدادات.':'اختر المواقف تحت المبنى، أو قلّل الشقق، أو «بدون مواقف» إن كانت في قبو.'));
  if (placement === 'pilotis' && levels < 2) warnings.push('المواقف تحت المبنى تحتاج دورين على الأقل.');
  if (placement === 'none' && regulatory) warnings.push('اخترت عدم تخصيص مواقف؛ الاشتراط الافتراضي '+regulatory+' مواقف وستظهر ملاحظة في المراجعة.');
  return {ready:true, setbacks:out, sources, coverage:cov, envelope, area, share:area / (W * D), required, regulatory, capacity,
    frontage, warnings, ok:!warnings.some(w => /لا يتسع|تحتاج دورين|لا تترك/.test(w))};
}

export function summaryText(p, placement) {
  if (!p.ready) return p.warnings.join(' ');
  const [, , w, d] = p.envelope;
  let text = 'المساحة القابلة للبناء ≈ '+fmt(w)+' × '+fmt(d)+' م = '+fmt(p.area)+' م² ('+Math.round(p.share*100)+'٪ من الأرض) بعد الارتدادات'
    +(p.sources && Object.values(p.sources).includes('default') ? ' (بعضها افتراضي)' : '')+' ونسبة بناء '+Math.round(p.coverage*100)+'٪.';
  if (placement === 'pilotis') text += ' الدور الأرضي للمواقف والمدخل، والشقق في الأدوار فوقه.';
  if (p.required && !p.warnings.some(w => w.includes('المواقف المطلوبة'))) text += ' المواقف المطلوبة '+p.required+(p.capacity != null ? '؛ السعة التقديرية '+p.capacity : '')+'.';
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
export function overlay(summary, levelIndex) {
  if (!summary || !Array.isArray(summary.envelope)) return [];
  const [x, z, w, d] = summary.envelope;
  const shapes = [{tag:'rect', attrs:{x, y:z, width:w, height:d, fill:'none', stroke:'#2a9d8f', 'stroke-width':.08, 'stroke-dasharray':'.45 .3', 'data-plot':'envelope'}}];
  if (levelIndex === 0) for (const [sx, sz, sw, sd] of summary.parking?.stalls || [])
    shapes.push({tag:'rect', attrs:{x:sx, y:sz, width:sw, height:sd, fill:'rgba(233,196,106,.25)', stroke:'#b08a2e', 'stroke-width':.04, 'data-plot':'stall'}});
  return shapes;
}
