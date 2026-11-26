// Human Arabic names for saved plan rooms and floors, read from the review
// packet's own projections. Internal ids are for the engineer view only.
const AR_DIGITS = '٠١٢٣٤٥٦٧٨٩';
export const arabicDigits = value => String(value).replace(/[0-9]/g, d => AR_DIGITS[d]);

export function floorLabel(index) {
  if (index < 0) return 'القبو ' + Math.abs(index);
  return index === 0 ? 'الدور الأرضي' : index === 1 ? 'الدور الأول' : 'الدور ' + index;
}

const ROLE_WORDS = {
  bedroom: 'غرفة نوم', living: 'صالة', kitchen: 'مطبخ', bathroom: 'دورة مياه', corridor: 'ممر',
  majlis: 'مجلس', dining: 'غرفة طعام', balcony: 'شرفة', laundry: 'غرفة غسيل', storage: 'مخزن',
};
const SHARED_WORDS = {
  lobby: 'مدخل العمارة', shared_corridor: 'الممر المشترك', stairs: 'الدرج المشترك', elevator: 'المصعد',
};
const hasArabic = text => /[؀-ۿ]/.test(text);

// A readable name from a generated room id, when the loaded version lacks the room.
export function roomNameFromId(roomId) {
  const id = String(roomId || '');
  const unit = /apartment_(\d+)_([a-z]+)_(\d+)$/.exec(id);
  if (unit && ROLE_WORDS[unit[2]]) return ROLE_WORDS[unit[2]] + ' ' + arabicDigits(unit[3]) + ' – الشقة ' + arabicDigits(unit[1]);
  const shared = Object.keys(SHARED_WORDS).find(key => id === key || id.endsWith('_' + key));
  if (shared) return SHARED_WORDS[shared];
  return hasArabic(id) ? id.slice(0, 80) : 'فراغ';
}

const primitive = (projection, template, roomId) => (Array.isArray(projection?.primitives) ? projection.primitives : [])
  .find(row => row?.source?.room_id === roomId && (template == null || row.source.template === template));
const label = row => String(row?.label || '').trim().slice(0, 80);

// «غرفة نوم ١ - الشقة ١ – الدور الأول», or «السطح فوق …» for the automatic roof deck.
export function planRoomName(projections, template, roomId) {
  const list = Array.isArray(projections) ? projections : [];
  const owner = list.find(projection => primitive(projection, template, roomId));
  if (owner?.level_kind === 'roof' || (!owner && /^roof_/.test(String(roomId || '')))) {
    const below = String(roomId || '').replace(/^roof_/, '');
    const under = [...list].reverse().find(projection => projection?.level_kind !== 'roof' && primitive(projection, null, below));
    if (under) return 'السطح فوق ' + label(primitive(under, null, below));
    return below !== roomId ? 'السطح فوق ' + roomNameFromId(below) : 'السطح';
  }
  if (owner) return (label(primitive(owner, template, roomId)) || roomNameFromId(roomId)) + ' – ' + floorLabel(owner.level_index);
  return roomNameFromId(roomId);
}
