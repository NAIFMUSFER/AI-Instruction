// Human Arabic names for saved plan rooms and floors, read from the review
// packet's own projections. Internal ids are for the engineer view only.
const AR_DIGITS = '٠١٢٣٤٥٦٧٨٩';
export const arabicDigits = value => String(value).replace(/[0-9]/g, d => AR_DIGITS[d]);

const UNITS = ['', 'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس', 'السابع', 'الثامن', 'التاسع'];
const TENS = ['', 'العاشر', 'العشرون', 'الثلاثون', 'الأربعون', 'الخمسون', 'الستون', 'السبعون', 'الثمانون', 'التسعون'];
// Arabic ordinal for a storey: الأول، الثاني … العاشر، الحادي عشر … العشرون، الحادي والعشرون …
export function arabicOrdinal(n) {
  if (!Number.isInteger(n) || n < 1 || n > 99) return null;
  if (n < 10) return UNITS[n];
  if (n === 10) return TENS[1];
  if (n < 20) return (n === 11 ? 'الحادي' : UNITS[n - 10]) + ' عشر';
  const unit = n % 10, tens = TENS[Math.floor(n / 10)];
  return unit ? (unit === 1 ? 'الحادي' : UNITS[unit]) + ' و' + tens : tens;
}
// «الدور الأرضي»، «الدور الأول»، «الدور الثاني»…؛ basements «القبو»، «القبو الثاني».
export function floorLabel(index) {
  if (index === 0) return 'الدور الأرضي';
  const ordinal = arabicOrdinal(Math.abs(index));
  if (index < 0) return index === -1 ? 'القبو' : ordinal ? 'القبو ' + ordinal : 'القبو ' + Math.abs(index);
  return ordinal ? 'الدور ' + ordinal : 'الدور ' + index;
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

// ── Room names on the 2D plan ──────────────────────────────────────────────
// Advance widths in em, on the generous side so an estimated label stays
// inside its room; the page measures the drawn text and shrinks it further.
const ARABIC_MARK = /[ً-ٰٟ]/u, ARABIC_LETTER = /[؀-ۿݐ-ݿ]/u;
export function textEm(text) {
  let em = 0;
  for (const ch of String(text)) em += ch === ' ' ? .3 : ARABIC_MARK.test(ch) ? 0 : /[0-9.,]/.test(ch) ? .58
    : ARABIC_LETTER.test(ch) ? .55 : /[A-Z]/.test(ch) ? .7 : .6;
  return em;
}
const metres = value => String(Math.round(value * 100) / 100);
// Two lines split at the word boundary that balances them best.
function twoLines(text) {
  const words = text.split(/\s+/);
  if (words.length < 2) return null;
  let best = null;
  for (let i = 1; i < words.length; i++) {
    const lines = [words.slice(0, i).join(' '), words.slice(i).join(' ')], wide = Math.max(...lines.map(textEm));
    if (!best || wide < best.wide) best = {lines, wide};
  }
  return best.lines;
}
/** Where a room's name and size go inside its w × d rectangle (plan metres).
 *  Picks the largest legible name: one line or two, across the room or along a
 *  tall narrow one; the size line is «w × d م», shortened to the area, or left
 *  out when it does not fit. A name too long even at the smallest size is cut
 *  with «…» (the full name stays in the room list and the accessible name).
 *  Returns null when no readable text fits. Items are offset across the text
 *  from the room centre; `along` is the length each line may take. */
export function roomLabelLayout(name, w, d, {min = .18, max = .62} = {}) {
  const text = String(name || '').trim().slice(0, 40);
  if (!text || !(w > 0 && d > 0)) return null;
  const sizes = [metres(w) + ' × ' + metres(d) + ' م', metres(w * d) + ' م²', null];
  let best = null;
  for (const vertical of d > w * 1.6 ? [false, true] : [false]) {
    const along = (vertical ? d : w) * .86, across = (vertical ? w : d) * .86;
    for (const lines of [[text], twoLines(text)]) {
      if (!lines) continue;
      for (const [rank, dims] of sizes.entries()) {
        let size = Math.min(max, along / Math.max(...lines.map(textEm)));
        let small = dims ? Math.min(size * .8, along / textEm(dims)) : 0;
        if (dims && small < size * .6) continue;
        const tall = lines.length * size * 1.2 + small * 1.3;
        if (tall > across) { size *= across / tall; small *= across / tall; }
        if (size < min) continue;
        const score = size * [1, .97, .8][rank] * (lines.length > 1 ? .94 : 1) * (vertical ? .85 : 1);
        if (!best || score > best.score) best = {score, lines, size, dims, small, vertical, along};
      }
    }
  }
  if (!best) {
    // Cut the name to what fits on one line at the smallest size, along the longer side.
    const vertical = d > w, along = (vertical ? d : w) * .86, size = Math.min(min, (vertical ? w : d) * .86 / 1.2);
    let cut = '';
    for (const ch of text) { if (textEm(cut + ch + '…') * size > along) break; cut += ch; }
    if ([...cut.trim()].length < 2 || size < min * .6) return null;
    best = {lines: [cut.trim() + '…'], size, dims: null, small: 0, vertical, along};
  }
  // Sizes round down, so a line sized to the room never rounds past it.
  const round = value => Math.round(value * 1000) / 1000, floor = value => Math.floor(value * 1000) / 1000;
  const tall = best.lines.length * best.size * 1.2 + best.small * 1.3, top = -tall / 2;
  const items = best.lines.map((line, i) => ({kind: 'name', text: line, size: floor(best.size), offset: round(top + best.size * 1.2 * (i + .5))}));
  if (best.dims) items.push({kind: 'size', text: best.dims, size: floor(best.small), offset: round(top + best.lines.length * best.size * 1.2 + best.small * .65)});
  return {vertical: best.vertical, along: round(best.along), items};
}
