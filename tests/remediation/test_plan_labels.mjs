import assert from 'node:assert/strict';
import {arabicOrdinal, floorLabel, planRoomName, roomNameFromId} from '../../public/app/core/plan-labels.mjs';

// Owner-facing names for saved rooms and floors (UX audit M5/m6): no internal ids,
// ordinal Arabic floors.
assert.deepEqual([0, 1, 2, 3, 10, 11, 12, 20, 21, 25, 30].map(floorLabel), [
  'الدور الأرضي', 'الدور الأول', 'الدور الثاني', 'الدور الثالث', 'الدور العاشر', 'الدور الحادي عشر',
  'الدور الثاني عشر', 'الدور العشرون', 'الدور الحادي والعشرون', 'الدور الخامس والعشرون', 'الدور الثلاثون']);
assert.deepEqual([-1, -2].map(floorLabel), ['القبو', 'القبو الثاني']);
assert.equal(arabicOrdinal(100), null);
assert.equal(floorLabel(120), 'الدور 120');
console.log('PASS ordinal Arabic floor names');

const room = (template, id, label) => ({label, source: {template, room_id: id}});
const projections = [
  {level_index: 0, primitives: [room('residential_2', 'residential_2_apartment_1_bedroom_1', 'غرفة نوم ١ - الشقة ١')]},
  {level_index: 1, primitives: [room('residential_2__stairs_1', 'residential_2_apartment_1_bedroom_1', 'غرفة نوم ١ - الشقة ١')]},
  {level_index: 2, level_kind: 'roof', level_auto: true, primitives: [room('roof', 'roof_residential_2_apartment_1_bedroom_1', 'سطح')]},
];
assert.equal(planRoomName(projections, 'residential_2__stairs_1', 'residential_2_apartment_1_bedroom_1'), 'غرفة نوم ١ - الشقة ١ – الدور الأول');
assert.equal(planRoomName(projections, null, 'residential_2_apartment_1_bedroom_1'), 'غرفة نوم ١ - الشقة ١ – الدور الأرضي');
assert.equal(planRoomName(projections, 'roof', 'roof_residential_2_apartment_1_bedroom_1'), 'السطح فوق غرفة نوم ١ - الشقة ١');
assert.equal(planRoomName([], 'residential_2', 'residential_2_apartment_2_bathroom_1'), 'دورة مياه ١ – الشقة ٢');
assert.equal(roomNameFromId('residential_2_shared_corridor'), 'الممر المشترك');
assert.equal(roomNameFromId('x9_unknown'), 'فراغ', 'an unknown id is never shown raw');
for (const name of [planRoomName(projections, 'residential_2', 'residential_2_apartment_1_bedroom_1'), roomNameFromId('a1_bath1_d_corr1')])
  assert.ok(!/[a-z]_[a-z0-9]/i.test(name), 'no internal id in: ' + name);
console.log('PASS room names from the review packet, roof decks and generated ids');

// Room names on the 2D plan (live review: doubled/smeared text, small rooms overflowing).
// The owner's ground floor: one flat, 19+ rooms, from tests/remediation/floor_program_fixture.py.
{
  const {roomLabelLayout, textEm} = await import('../../public/app/core/plan-labels.mjs');
  const rooms = [['الدرج', 2.6, 5], ['المصعد', 2, 2.2], ['بهو مدخل العمارة', 2, 2.8], ['ردهة مدخل الضيوف', 1.2, 2.8],
    ['ممر الشقة', 1.2, 13.2], ['مجلس الضيوف', 4, 4.5], ['مغاسل ودورة مياه الضيوف', 3.2, 3.3], ['حمام المسبح', 3.2, 1.2],
    ['الصالة العائلية', 4, 5], ['السفرة', 3.2, 3.4], ['المطبخ الرئيسي', 4.6, 2.8], ['مستودع المؤن', 1.4, 1.8],
    ['الغسيل والتخزين', 1.8, 1.8], ['ممر الخدمة', 1.4, 1.8], ['غرفة نوم للأبناء 1', 4.6, 2.45], ['الحمام العائلي', 4.6, 1.5],
    ['غرفة نوم للأبناء 2', 4.6, 2.45], ['غرفة النوم الرئيسية', 4, 3.8], ['حمام غرفة النوم الرئيسية', 3.2, 3.8], ['ممر', 3.2, .9]];
  const extent = 26.75, opts = {min: extent * .009, max: extent * .026};      // as connected-workspace draws a 20 × 25 m site
  for (const [name, w, d] of rooms) {
    const layout = roomLabelLayout(name, w, d, opts);
    assert.ok(layout, 'every room of the flat is named: ' + name);
    const along = layout.vertical ? d : w, across = layout.vertical ? w : d;
    assert.ok(layout.along <= along * .861);
    for (const item of layout.items) {
      assert.ok(textEm(item.text) * item.size <= layout.along + 1e-6, name + ': «' + item.text + '» fits along the room');
      assert.ok(item.size >= opts.min * (item.kind === 'name' ? 1 : .6) - 1e-3 && item.size <= opts.max + 1e-3, name + ' size within the drawing scale');
      assert.ok(Math.abs(item.offset) + item.size * .6 <= across / 2 + 1e-6, name + ': the stack fits across the room');
    }
    const names = layout.items.filter(item => item.kind === 'name');
    assert.equal(names.map(item => item.text).join(' ').replace('…', ''), name, 'the whole name, at most on two lines');
    assert.ok(names.length <= 2 && new Set(names.map(item => item.size)).size === 1);
    const size = layout.items.find(item => item.kind === 'size');
    if (size) assert.ok(size.size < names[0].size, 'the size line is smaller than the name');
  }
  // The previous fixed formula overflowed small rooms: name size max(.16, min(w, d) × .105) on one line.
  const old = (name, w, d) => textEm(name) * Math.max(.16, Math.min(w, d) * .105) > w;
  assert.ok(old('ردهة مدخل الضيوف', 1.2, 2.8) && old('حمام غرفة النوم الرئيسية', 3.2, 3.8) && old('مغاسل ودورة مياه الضيوف', 3.2, 3.3));
  // Small rooms: the size line shortens to the area or is left out; a tall corridor is named along its length.
  const pantry = roomLabelLayout('مستودع المؤن', 1.4, 1.8, opts);
  assert.ok(!pantry.items.some(item => item.text === '1.4 × 1.8 م'), 'no full size line that would overflow');
  assert.equal(roomLabelLayout('ممر الشقة', 1.2, 13.2, opts).vertical, true);
  assert.equal(roomLabelLayout('مجلس الضيوف', 4, 4.5, opts).items.at(-1).text, '4 × 4.5 م');
  // A long name in a tiny room is cut (full name stays in the room list); a sliver gets no text.
  const cut = roomLabelLayout('غرفة الملابس والتخزين الإضافية للجناح', .9, .9, opts);
  assert.ok(cut.items.length === 1 && cut.items[0].text.endsWith('…') && textEm(cut.items[0].text) * cut.items[0].size <= cut.along + 1e-6);
  assert.equal(roomLabelLayout('ممر', .1, .4, opts), null);
  assert.equal(roomLabelLayout('', 3, 3, opts), null);
  console.log('PASS plan room names fit their rooms: one or two lines, vertical in corridors, shortened size line');
}
// The plan draws them crisp: the room group's outline and fill-opacity do not reach the text.
{
  const {readFileSync} = await import('node:fs');
  const css = readFileSync(new URL('../../public/app/styles/connected-workspace.css', import.meta.url), 'utf8');
  const rule = /#designWorkspace :is\(#cwPlan,\.cw-viewer-fallback\) text \{([^}]*)\}/.exec(css)?.[1] || '';
  for (const part of ['fill-opacity:1', 'paint-order:stroke fill', 'stroke:#', 'font-weight:400'])
    assert.ok(rule.includes(part), 'plan text rule sets ' + part);
  assert.ok(!/stroke-width/.test(rule), 'the halo width comes from each text (proportional), not a CSS length');
  const source = readFileSync(new URL('../../public/app/ui/connected-workspace.mjs', import.meta.url), 'utf8');
  assert.match(source, /'stroke-width':Math\.round\(line\.size\*140\)\/1000/);
  assert.doesNotMatch(source, /Math\.max\(\.16,Math\.min\(w,d\)\*\.105\)/, 'the old fixed label formula is gone');
  console.log('PASS plan text keeps a thin proportional halo and no inherited room outline');
}
