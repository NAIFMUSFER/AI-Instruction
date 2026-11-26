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
