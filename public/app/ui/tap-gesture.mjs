/* One rule for "was this a tap?" on the 3D canvas.

   Orbiting, panning and pinching start with the same pointerdown as a tap.
   The old check compared only where the pointer went down and where it came
   up, so a drag that wandered away and ended near its start (3 px) counted as
   a tap and opened the inspector. A gesture is a tap only when:
   - one pointer was involved (a second finger means pinch or rotate),
   - it never travelled further than the slop for its pointer type, measured
     on every move rather than only at the end, and
   - it was released within TAP_MAX_MS (a longer press is a hold, not a tap). */
export const TAP_SLOP_PX = Object.freeze({mouse: 5, pen: 8, touch: 10});
export const TAP_MAX_MS = 500;

export function createTapTracker(target, {onTap = null, now = () => performance.now()} = {}) {
  let active = null, last = null;
  const slop = type => TAP_SLOP_PX[type] ?? TAP_SLOP_PX.touch;
  function travel(e) {
    const d = Math.hypot(Number(e.clientX) - active.x, Number(e.clientY) - active.y);
    if (Number.isFinite(d)) active.travel = Math.max(active.travel, d);
    else active.invalid = true;
  }
  function down(e) {
    if (active) { active.multi = true; return; }
    if (e.isPrimary === false) return;
    if (e.button !== undefined && e.button !== 0) return;
    active = {id: e.pointerId, type: e.pointerType || 'mouse', x: Number(e.clientX), y: Number(e.clientY),
      t: now(), travel: 0, multi: false, invalid: false};
  }
  function move(e) { if (active && e.pointerId === active.id) travel(e); }
  function up(e) {
    if (!active || e.pointerId !== active.id) return;
    travel(e);
    const g = active; active = null;
    const tap = !g.multi && !g.invalid && g.travel <= slop(g.type) && now() - g.t <= TAP_MAX_MS;
    last = {tap, x: Number(e.clientX), y: Number(e.clientY), at: now()};
    if (tap && typeof onTap === 'function') onTap(e);
  }
  function cancel() { active = null; last = {tap: false, x: NaN, y: NaN, at: now()}; }
  target.addEventListener('pointerdown', down, {passive: true});
  target.addEventListener('pointermove', move, {passive: true});
  target.addEventListener('pointerup', up, {passive: true});
  target.addEventListener('pointercancel', cancel, {passive: true});
  return {
    /* For a click listener: true only if the click ends the tap just recorded. */
    wasTap(clickEvent) {
      const g = last; last = null;
      return !!g && g.tap && now() - g.at < 1000 &&
        Math.hypot(Number(clickEvent.clientX) - g.x, Number(clickEvent.clientY) - g.y) <= 12;
    },
    destroy() {
      target.removeEventListener('pointerdown', down);
      target.removeEventListener('pointermove', move);
      target.removeEventListener('pointerup', up);
      target.removeEventListener('pointercancel', cancel);
    },
  };
}
