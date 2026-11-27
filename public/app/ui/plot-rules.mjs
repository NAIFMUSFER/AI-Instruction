// Step 01 plot inputs: street side(s), setbacks, coverage and parking. Empty
// fields use labelled default assumptions that the server resolves and writes
// into the review; nothing here is a regulatory ruling.
import {PLACEMENTS,PLOT_ISSUE_NAMES,PLOT_SCOPE_NAMES,SIDES,SIDE_AR,SOURCE_TITLE,SOURCE_URL,overlay,parseNumber,plotCommand,preview,summaryText,villaBrief} from '../core/plot-rules.mjs';

const sideOptions = first => first+SIDES.map(s => '<option value="'+s+'">'+SIDE_AR[s].replace('ال','')+'</option>').join('');

// issueNames/scopeNames: the review's label tables; the plot codes are added to them.
export function createPlotRules(root, {storageKey, issueNames, scopeNames}) {
  if (issueNames) Object.assign(issueNames, PLOT_ISSUE_NAMES);
  if (scopeNames) Object.assign(scopeNames, PLOT_SCOPE_NAMES);
  const $ = id => root.querySelector('#'+id);
  const section = document.createElement('section');
  section.className = 'cw-brief-review'; section.id = 'cwPlot';
  const own = !$('cwStreet');   // reuse the residential street select when it exists
  section.innerHTML = '<h3>الأرض والارتدادات والمواقف</h3>'
    + '<p class="cw-muted">اترك الحقل فارغًا ونفترض قيمة من <a id="cwPlotSource" target="_blank" rel="noopener"></a>، وتظهر في المراجعة لتعدّلها.</p>'
    + '<div class="cw-fields">'
    + (own ? '<label>جهة الشارع<select id="cwPlotStreet">'+sideOptions('<option value="">لا أعرف الآن (نفترض الشمال)</option>')+'</select></label>' : '')
    + '<label>شارع ثانٍ (أرض على زاويتين)<select id="cwPlotStreet2">'+sideOptions('<option value="">لا يوجد</option>')+'</select></label>'
    + '<label>عرض الشارع (م)<input id="cwPlotStreetWidth" inputmode="decimal" autocomplete="off" placeholder="غير معروف"></label></div>'
    + '<div class="cw-fields">'+SIDES.map(s => '<label>ارتداد '+SIDE_AR[s]+' (م)<input id="cwPlotSetback'+s+'" inputmode="decimal" autocomplete="off"></label>').join('')+'</div>'
    + '<div class="cw-fields"><label>نسبة البناء القصوى (٪)<input id="cwPlotCoverage" inputmode="decimal" autocomplete="off"></label>'
    + '<label>مكان المواقف<select id="cwPlotParking">'+Object.entries(PLACEMENTS).map(([k, v]) => '<option value="'+k+'">'+v+'</option>').join('')+'</select></label>'
    + '<label>عدد المواقف<input id="cwPlotParkingCount" inputmode="numeric" autocomplete="off"></label></div>'
    + '<label class="cw-check"><input id="cwPlotLanding" type="checkbox"> مدخل كل شقة من بسطة الدرج مباشرة</label>'
    + '<p id="cwPlotSummary" class="cw-muted" role="status" aria-live="polite"></p>';
  const anchor = $('cwResidential') || $('cwBuildingFields') || $('cwLevels')?.closest('.cw-fields');
  if (anchor) anchor.after(section); else $('cwBriefForm')?.append(section);
  const link = $('cwPlotSource'); link.href = SOURCE_URL; link.textContent = SOURCE_TITLE;
  const fields = ['cwPlotStreet','cwPlotStreet2','cwPlotStreetWidth',...SIDES.map(s => 'cwPlotSetback'+s),'cwPlotCoverage','cwPlotParking','cwPlotParkingCount','cwPlotLanding'];
  const value = id => { const n = $(id); return !n ? '' : n.type === 'checkbox' ? n.checked : n.value; };
  const primary = () => { const v = own ? value('cwPlotStreet') : value('cwStreet'); return SIDES.includes(v) ? v : ''; };
  function inputs() {
    return {streets:[primary(), value('cwPlotStreet2')].filter(Boolean), streetWidth:value('cwPlotStreetWidth'),
      setbacks:Object.fromEntries(SIDES.map(s => [s, value('cwPlotSetback'+s)])), coverage:value('cwPlotCoverage'),
      placement:value('cwPlotParking') || 'front_setback', count:value('cwPlotParkingCount'), landing:value('cwPlotLanding')};
  }
  function program() {
    const levels = parseNumber(value('cwLevels')) || 1, units = parseNumber(value('cwUnits')) || null;
    const pilotis = value('cwPlotParking') === 'pilotis';
    const total = units && value('cwUnitsScope') === 'per_level' ? units * Math.max(1, levels - (pilotis ? 1 : 0)) : units;
    const villa = villaBrief(value('cwBrief'), total);
    return {levels, units:total, villa};
  }
  function current() {
    const raw = inputs(), parsed = plotCommand(raw), {levels, units, villa} = program();
    const p = preview({villa, levels, units, width:parseNumber(value('cwWidth')), depth:parseNumber(value('cwDepth')),
      streets:parsed.streets, streetWidth:parsed.street_width_m ?? null, setbacks:parsed.setbacks_m,
      coverage:parsed.max_coverage ?? null, placement:parsed.parking.placement, count:parsed.parking.count ?? null});
    return {p, parsed};
  }
  function refresh() {
    // A plan read from the owner's file is transcribed as drawn: no plot rules (U8).
    section.hidden = value('cwType') !== 'residential' || value('cwStartMode') === 'upload';
    let p;
    try {
      const now = current(); p = now.p;
      $('cwPlotSummary').textContent = summaryText(p, now.parsed.parking.placement)
        + (primary() ? '' : ' جهة الشارع غير محددة فنفترض الشمال.');
    } catch (e) { $('cwPlotSummary').textContent = e.message; }
    for (const s of SIDES) $('cwPlotSetback'+s).placeholder = p?.setbacks ? 'افتراضي '+p.setbacks[s] : 'افتراضي';
    $('cwPlotCoverage').placeholder = p?.coverage ? 'افتراضي '+Math.round(p.coverage * 100) : 'افتراضي';
    $('cwPlotStreetWidth').placeholder = 'غير معروف — نفترض 15';
    $('cwPlotParkingCount').placeholder = p?.regulatory ? 'افتراضي '+p.regulatory : 'حسب عدد الشقق';
  }
  function save() {
    try { localStorage.setItem(storageKey(), JSON.stringify(Object.fromEntries(fields.filter($).map(id => [id, value(id)])))); } catch (e) {}
    const confirmed = $('cwConfirmed'); if (confirmed) confirmed.checked = false;   // re-confirm, like the residential card
    refresh();
  }
  section.addEventListener('input', save); section.addEventListener('change', save);
  for (const id of ['cwWidth','cwDepth','cwLevels','cwUnits','cwUnitsScope','cwType','cwStreet','cwBrief','cwStartMode'])
    for (const kind of ['input','change']) $(id)?.addEventListener(kind, refresh);
  refresh();
  return {
    fill() {
      try { const data = JSON.parse(localStorage.getItem(storageKey()) || 'null');
        if (data) for (const id of fields) { const n = $(id); if (!n || !(id in data)) continue; if (n.type === 'checkbox') n.checked = data[id] === true; else if (typeof data[id] === 'string') n.value = data[id]; }
      } catch (e) {}
      refresh();
    },
    // The buildable footprint (m²) the preview derives, or null: sizes the villa cards.
    buildable() {
      if (value('cwType') !== 'residential') return null;
      try { const {p} = current(); return p.ready ? p.area : null; } catch (e) { return null; }
    },
    // {plot} for a residential generation from the description; {} otherwise.
    command() {
      if (value('cwType') !== 'residential') return {};
      return {plot:plotCommand(inputs())};
    },
    draw(projection, summary, add) {
      for (const shape of overlay(summary, projection?.level_index)) add(shape.tag, shape.attrs);
    },
  };
}
