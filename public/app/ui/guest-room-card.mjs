/* Guest room card: tapping a room keeps the building on screen and shows what
   an owner asks first (name, floor, area, dimensions). The engineering
   inspector is one explicit button away («تفاصيل هندسية»). Presentation only:
   nothing here writes to the model. */
import { guestRoomFacts, openGuestFloorPlan } from './guest-floor-plan.mjs';

export function installGuestRoomCard(A) {
  const card = document.createElement('section');
  card.id = 'guestRoomCard';
  card.hidden = true;
  card.setAttribute('aria-labelledby', 'guestRoomName');
  card.innerHTML = `
    <header><h2 id="guestRoomName"></h2>
      <button id="guestRoomClose" type="button" aria-label="إغلاق بطاقة الغرفة">✕</button></header>
    <p id="guestRoomWhere"></p>
    <dl>
      <div><dt>المساحة</dt><dd id="guestRoomArea"></dd></div>
      <div><dt>الأبعاد</dt><dd id="guestRoomSize" dir="rtl"></dd></div>
    </dl>
    <p id="guestRoomBasis"></p>
    <div id="guestRoomColours"></div>
    <div class="guest-room-actions">
      <button id="guestRoomPlan" type="button" aria-haspopup="dialog">افتحها في المخطط</button>
      <button id="guestRoomDetails" type="button">تفاصيل هندسية</button>
    </div>`;
  document.body.append(card);
  const $ = id => card.querySelector('#' + id);
  let current = null;

  function close() {
    if (card.hidden) return;
    card.hidden = true;
    $('guestRoomColours').replaceChildren();
    current?.clearHighlight?.();
    current = null;
  }
  function show(selection, {mesh = null, clearHighlight = null, openInspector = null} = {}) {
    let facts = null;
    try { facts = guestRoomFacts(A, selection.level_index, selection.room_id); } catch {}
    if (!facts) return false;
    if (current && current.clearHighlight !== clearHighlight) current.clearHighlight?.();
    current = {selection, facts, clearHighlight, openInspector};
    $('guestRoomName').textContent = facts.name;
    $('guestRoomWhere').textContent = [facts.unit, facts.floor].filter(Boolean).join(' · ');
    $('guestRoomArea').textContent = facts.area;
    $('guestRoomSize').textContent = facts.size;
    $('guestRoomBasis').textContent = facts.basis;
    $('guestRoomColours').replaceChildren(...(A.quickColourControls?.(mesh) || []));
    $('guestRoomDetails').hidden = typeof openInspector !== 'function';
    card.hidden = false;
    const live = document.getElementById('acsLiveRegion');
    if (live) live.textContent = `اخترت ${facts.name} في ${facts.floor}: ${facts.area}.`;
    return true;
  }
  $('guestRoomClose').addEventListener('click', close);
  $('guestRoomPlan').addEventListener('click', () => {
    if (!current) return;
    try { openGuestFloorPlan(A, current.facts.levelIndex, current.facts.spaceId || ''); } catch {}
  });
  $('guestRoomDetails').addEventListener('click', () => {
    const open = current?.openInspector;
    card.hidden = true;
    $('guestRoomColours').replaceChildren();
    current = null;
    if (typeof open === 'function') void open();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !card.hidden && !document.querySelector('dialog[open]')) close();
  });
  A.guestRoomCard = {show, close, retire: close, element: card};
  return A.guestRoomCard;
}
