// A confirmed per-floor program (acs_floor_program.py): the per-floor requirement
// rows the step-02 option cards send, three layout options for the same rooms,
// and the Arabic names of the per-floor review findings. The server derives the
// same rows from the same program; a parity test keeps them equal.
export const PROGRAM_SOURCE = 'brief:program';
export const LEVEL_METRIC = 'room_count_by_level', ENSUITE_METRIC = 'ensuite_bedroom_count_by_level';
export const COUNTED_ROLES = ['bedroom', 'bathroom', 'living', 'majlis', 'dining', 'kitchen', 'pantry', 'laundry', 'storage',
  'office', 'dressing', 'maid_room', 'driver_room', 'terrace', 'balcony'];
export const ROLE_LABEL = {bedroom:'غرف النوم', bathroom:'الحمامات ودورات المياه', living:'الصالات', majlis:'المجالس',
  dining:'غرف الطعام', kitchen:'المطابخ', pantry:'مستودعات المؤن', laundry:'غرف الغسيل', storage:'المخازن', office:'المكاتب',
  dressing:'غرف الملابس', maid_room:'غرف الخادمة', driver_room:'غرف السائق', terrace:'التراسات', balcony:'الشرفات'};
export const ENSUITE_LABEL = 'غرف النوم بحمام خاص';
const FLOOR_NAMES = ['الدور الأرضي', 'الدور الأول', 'الدور الثاني', 'الدور الثالث', 'الدور الرابع', 'الدور الخامس',
  'الدور السادس', 'الدور السابع', 'الدور الثامن', 'الدور التاسع'];
export const floorName = i => FLOOR_NAMES[i] ?? 'الدور ' + i;
export const MAX_REQUIREMENTS = 100;   // acs_workspace_service.generation_command

// A flat's rooms as planned: the listed rooms, plus unnamed bedrooms or bathrooms
// when the brief states a larger total than it lists (acs_floor_program.unit_rooms).
const EXTRA_NAMES = {bedroom:'غرفة نوم إضافية', bathroom:'حمام إضافي'};
export function unitRooms(unit) {
  const rooms = [...unit.rooms];
  for (const [role, stated] of [['bedroom', unit.bedrooms], ['bathroom', unit.bathrooms]]) {
    const listed = unit.rooms.filter(r => r.role === role).reduce((n, r) => n + r.count, 0);
    if (Number.isInteger(stated) && stated > listed)
      rooms.push({role, name:EXTRA_NAMES[role], count:stated - listed, width_m:null, depth_m:null, approx:false, ensuite:false, note:null});
  }
  return rooms;
}
/** {role: count} of the counted roles on one program level (all its flats). */
export function levelCounts(level) {
  const out = {};
  for (const unit of level.units) for (const room of unitRooms(unit))
    if (COUNTED_ROLES.includes(room.role)) out[room.role] = (out[room.role] || 0) + room.count;
  return out;
}
export const levelEnsuite = level => level.units.reduce((n, u) => n + u.rooms.filter(r => r.role === 'bedroom' && r.ensuite).reduce((m, r) => m + r.count, 0), 0);

/** A program planned floor by floor: an apartment building with flats on at least one floor. */
export const floorProgram = program => !!program && program.building_type !== 'villa' && program.levels.some(l => l.units.length);

/** The confirmed per-floor rows, as acs_floor_program.requirement_rows builds them. */
export function programRows(program) {
  const rows = [];
  const row = (metric, level, role, expected, label) => ({id:'program-l' + level + '-' + (role || 'ensuite'), metric, level, expected,
    source:'inferred', source_id:PROGRAM_SOURCE, evidence:label + ': ' + expected, confirmed:true, ...(role ? {role} : {})});
  program.levels.forEach((level, i) => {
    const counts = levelCounts(level);
    for (const role of COUNTED_ROLES) if (counts[role]) rows.push(row(LEVEL_METRIC, i, role, counts[role], ROLE_LABEL[role] + ' في ' + floorName(i)));
    const ensuite = levelEnsuite(level);
    if (ensuite) rows.push(row(ENSUITE_METRIC, i, null, ensuite, ENSUITE_LABEL + ' في ' + floorName(i)));
  });
  return rows;
}

/** Rows a confirmed program contradicts, in Arabic (acs_floor_program.contradictions). */
export function programConflicts(program, rows) {
  const out = [], levels = program.levels, units = levels.map(l => l.units.length), totals = {};
  for (const level of levels) for (const [role, n] of Object.entries(levelCounts(level))) totals[role] = (totals[role] || 0) + n;
  const expected = new Map(programRows(program).map(r => [r.metric + '|' + r.level + '|' + (r.role || ''), r.expected]));
  for (const r of rows) {
    if (!r || r.expected == null) continue;
    if (r.metric === LEVEL_METRIC || r.metric === ENSUITE_METRIC) {
      const want = expected.get(r.metric + '|' + r.level + '|' + (r.role || '')) ?? 0;
      if (!Number.isInteger(r.level) || r.level < 0 || r.level >= levels.length) out.push('متطلب لدور غير موجود في البرنامج المؤكد.');
      else if (r.expected !== want) out.push((r.metric === ENSUITE_METRIC ? ENSUITE_LABEL : ROLE_LABEL[r.role] || r.role) + ' في ' + floorName(r.level) + ': المتطلب ' + r.expected + ' والبرنامج المؤكد ' + want + '.');
    } else if (r.metric === 'unit_count' && r.expected !== units.reduce((a, b) => a + b, 0)) {
      out.push('إجمالي الشقق في المتطلبات ' + r.expected + ' والبرنامج المؤكد ' + units.reduce((a, b) => a + b, 0) + '.');
    } else if (r.metric === 'unit_count_per_level' && (new Set(units).size !== 1 || r.expected !== units[0])) {
      out.push('عدد الشقق في كل دور لا يطابق البرنامج المؤكد.');
    } else if (r.metric === 'room_count' && r.template == null && COUNTED_ROLES.includes(r.role) && r.expected !== (totals[r.role] || 0)) {
      out.push('إجمالي ' + ROLE_LABEL[r.role] + ' في المتطلبات ' + r.expected + ' والبرنامج المؤكد ' + (totals[r.role] || 0) + '.');
    } else if (r.metric === 'room_count_per_unit' && COUNTED_ROLES.includes(r.role)) {
      const perUnit = new Set(levels.flatMap(l => l.units.map(u => unitRooms(u).filter(m => m.role === r.role).reduce((n, m) => n + m.count, 0))));
      if (perUnit.size !== 1 || !perUnit.has(r.expected)) out.push(ROLE_LABEL[r.role] + ' «في كل شقة» = ' + r.expected + ' يخالف البرنامج المؤكد، وبرنامج كل دور مختلف.');
    }
  }
  return out;
}

// Three ways to lay out the same confirmed rooms; they match the server's
// option goals (acs_workspace_service.OPTIONS) and never change a room count.
const LAYOUTS = [
  {id:'A', title:'مخطط مدمج حول النواة', why:'يجمع الحركة حول الدرج والمصعد بممرات قصيرة، فتبقى مساحة أكبر للغرف بمقاساتها المطلوبة.',
   tradeoff:'الغرف أقرب إلى بعضها، والفصل بين الضيوف والأسرة أقل.'},
  {id:'B', title:'وضوح الحركة', why:'مسار واضح من باب كل شقة إلى الصالة ثم الغرف، والمطبخ قرب السفرة أو الصالة.',
   tradeoff:'قد يطول الممر الداخلي قليلًا على حساب الصالة.'},
  {id:'C', title:'فصل الضيوف عن الأسرة', why:'المجلس ودورة مياهه عند مدخل كل شقة، وغرف النوم في الطرف الهادئ بعيدًا عن الضيوف.',
   tradeoff:'منطقة الضيوف عند المدخل تأخذ من واجهة الشقة.'},
];
const arabicCount = (n, one, two, few, many) => n === 1 ? one : n === 2 ? two : n >= 3 && n <= 10 ? n + ' ' + few : n + ' ' + many;
/** One short line per floor for the cards: «الدور الأول: 4 غرف نوم، 2 حمامات، مجلس، مكتب». */
export function floorText(level, i) {
  if (!level.units.length) return floorName(i) + ': ' + (level.use === 'parking' ? 'مواقف' : 'بلا شقق');
  const c = levelCounts(level), parts = [];
  if (level.units.length > 1) parts.push(arabicCount(level.units.length, 'شقة', 'شقتان', 'شقق', 'شقة'));
  if (c.bedroom) parts.push(arabicCount(c.bedroom, 'غرفة نوم', 'غرفتا نوم', 'غرف نوم', 'غرفة نوم'));
  if (c.bathroom) parts.push(arabicCount(c.bathroom, 'حمام', 'حمامان', 'حمامات', 'حمامًا'));
  for (const [role, word] of [['majlis', 'مجلس'], ['office', 'مكتب'], ['terrace', 'تراس'], ['maid_room', 'غرفة خادمة'], ['driver_room', 'غرفة سائق']])
    if (c[role]) parts.push(c[role] > 1 ? c[role] + ' ' + word : word);
  return floorName(i) + ': ' + parts.join('، ');
}
const targetArea = level => level.units.reduce((n, u) => n + u.rooms.reduce((m, r) => m + (r.width_m != null ? r.width_m * r.depth_m * r.count : 0), 0), 0);

/** The option cards for a confirmed program: same rooms, three layouts.
 *  ``buildable`` is the footprint (m²) the plot preview allows, or null. */
export function programOptions(program, {buildable = null, guests = 'suggest'} = {}) {
  const fp = program.site?.footprint;
  const available = Number.isFinite(fp?.width_m) && Number.isFinite(fp?.depth_m) ? fp.width_m * fp.depth_m
    : Number.isFinite(buildable) && buildable > 0 ? buildable : null;
  const largest = Math.max(0, ...program.levels.map(targetArea));
  const sized = program.levels.some(l => l.units.some(u => u.rooms.some(r => r.width_m != null)));
  const majlis = program.levels.some(l => levelCounts(l).majlis);
  return LAYOUTS.map(o => ({...o, floorProgram:true, floors:program.levels.map(floorText), largestTarget:Math.round(largest), available:available == null ? null : Math.round(available),
    // Stated sizes plus about 15% for walls and 25 m² for the stair core must fit the block.
    feasible:available == null || largest * 1.15 + 25 <= available + 1e-9, sized,
    recommended:guests === 'separate' || (guests === 'suggest' && majlis) ? o.id === 'C' : o.id === 'B'}));
}

export const PROGRAM_ISSUE_NAMES = Object.freeze({
  PROGRAM_LEVEL_ROOMS:'عدد غرف دور يخالف برنامجه المؤكد',
  PROGRAM_LEVEL_ENSUITE:'غرفة نوم بلا حمامها الخاص المطلوب',
  PROGRAM_ROOM_SIZE_OFF:'مقاس غرفة بعيد عن المقاس المطلوب',
  PROGRAM_ROOM_SIZE_NEAR:'مقاس غرفة يختلف قليلًا عن المطلوب',
  PROGRAM_ROOM_PROPORTION:'غرفة أضيق من المقاس المطلوب',
  PROGRAM_IDENTICAL_FLOORS:'أدوار مرسومة بتوزيع واحد وبرامجها مختلفة',
  PROGRAM_WET_STACK:'حمامات أو مطابخ لا تقع فوق مجاري الدور الأسفل',
  PROGRAM_FLOOR_COUNT:'عدد الأدوار يخالف البرنامج المؤكد',
  BRIEF_PROGRAM_INVALID:'برنامج الأدوار المحفوظ غير صالح',
});
export const PROGRAM_SCOPE_NAMES = Object.freeze({brief_program:'برنامج كل دور والمقاسات المستهدفة'});
