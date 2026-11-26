// Plot inputs in step 01: Arabic-Indic digits, the command block, the preview's
// parity with the server (acs_plot_rules.resolve), the option estimate parity
// and the module wiring on a minimal DOM. No browser or network.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {parseNumber,plotCommand,preview,overlay,summaryText,PLOT_ISSUE_NAMES,PLOT_SCOPE_NAMES} from '../../public/app/core/plot-rules.mjs';
import {residentialOptions} from '../../public/app/core/residential-program.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let passed = 0;
const check = (name, fn) => { fn(); passed++; console.log('PASS', name); };
const python = (code, input) => {
  const out = spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,' + JSON.stringify(ROOT) + ');' + code],
    {input: JSON.stringify(input), encoding: 'utf8', cwd: ROOT});
  assert.equal(out.status, 0, out.stderr);
  return JSON.parse(out.stdout);
};

check('Arabic-Indic and extended digits, Arabic decimal comma and units', () => {
  assert.equal(parseNumber('٢٫٥'), 2.5);
  assert.equal(parseNumber('۳'), 3);
  assert.equal(parseNumber(' ١٥ م '), 15);
  assert.equal(parseNumber('٦٥٪'), 65);
  assert.equal(parseNumber('2,5'), 2.5);
  assert.equal(parseNumber(''), null);
  assert.ok(Number.isNaN(parseNumber('ثلاثة')));
});

check('command block from form text', () => {
  const plot = plotCommand({streets: ['N', 'E'], streetWidth: '٢٠', setbacks: {N: '', E: '٣', S: '١٫٥', W: '0'},
    coverage: '٦٠', placement: 'pilotis', count: '٨', landing: true});
  assert.deepEqual(plot, {streets: ['N', 'E'], setbacks_m: {E: 3, S: 1.5, W: 0}, parking: {placement: 'pilotis', count: 8},
    landing_entries: true, street_width_m: 20, max_coverage: .6});
  assert.deepEqual(plotCommand({}), {streets: [], setbacks_m: {}, parking: {placement: 'front_setback'}, landing_entries: false});
  assert.throws(() => plotCommand({streets: ['N', 'N']}), /جهة مختلفة/);
  assert.throws(() => plotCommand({setbacks: {N: '٤٠'}}), /ارتداد الشمال/);
  assert.throws(() => plotCommand({count: '٢٫٥'}), /عددًا صحيحًا/);
  assert.throws(() => plotCommand({coverage: 'كثير'}), /نسبة البناء/);
});

check('preview matches the server resolution for the same inputs', () => {
  const cases = [
    {plot: {streets: ['N'], parking: {placement: 'none'}}, width: 20, depth: 25, levels: 3, units: 6},
    {plot: {streets: ['S'], street_width_m: 20, parking: {placement: 'none'}}, width: 20, depth: 25, levels: 6, units: 12},
    {plot: {streets: ['N', 'E'], setbacks_m: {W: 0, S: 1.5}, max_coverage: .7, parking: {placement: 'none'}}, width: 20, depth: 25, levels: 3, units: 6},
    {plot: {streets: ['N'], parking: {placement: 'none'}}, width: 30, depth: 40, levels: 3, units: 6},
    {plot: {streets: ['W'], parking: {placement: 'front_setback'}}, width: 25, depth: 20, levels: 2, units: 4},
    {plot: {streets: ['N'], parking: {placement: 'pilotis'}}, width: 20, depth: 25, levels: 3, units: 4},
  ];
  const server = python(`
import acs_plot_rules as P
out=[]
for c in json.load(sys.stdin):
    rows=[{'id':m,'metric':m,'expected':v,'confirmed':True,'source':'inferred'} for m,v in
          (('site_width_m',c['width']),('site_depth_m',c['depth']),('level_count',c['levels']),('unit_count',c['units']))]
    r=P.resolve(c['plot'],'عمارة',rows,None)
    out.append({'setbacks':r['setbacks_m'],'envelope':r['envelope'],'required':r['parking']['required'],
                'capacity':r['parking']['capacity_estimate'],'coverage':r['max_coverage']})
print(json.dumps(out))`, cases);
  cases.forEach((c, i) => {
    const p = preview({levels: c.levels, units: c.units, width: c.width, depth: c.depth, streets: c.plot.streets,
      streetWidth: c.plot.street_width_m ?? null, setbacks: c.plot.setbacks_m || {}, coverage: c.plot.max_coverage ?? null,
      placement: c.plot.parking.placement, count: null});
    assert.deepEqual(p.setbacks, server[i].setbacks, 'setbacks ' + i);
    assert.deepEqual(p.envelope, server[i].envelope, 'envelope ' + i);
    assert.equal(p.required, server[i].required, 'parking ' + i);
    assert.equal(p.capacity, server[i].capacity, 'capacity ' + i);
    assert.equal(p.coverage, server[i].coverage, 'coverage ' + i);
  });
  const tight = preview({levels: 3, units: 6, width: 20, depth: 25, streets: ['N'], placement: 'front_setback'});
  assert.equal(tight.ok, false);
  assert.match(summaryText(tight, 'front_setback'), /لا يتسع الارتداد الأمامي/);
});

check('option estimate on the card equals the server target', () => {
  const combos = [];
  for (const id of ['A', 'B', 'C']) for (const beds of [1, 2, 3, 4]) for (const baths of [1, 2, 3]) for (const guests of ['separate', 'none']) {
    const o = residentialOptions({units: 4, levels: 2, width: 20, depth: 25, bedrooms: beds, bathrooms: baths, guests}).find(x => x.id === id);
    combos.push({id, beds, baths, majlis: o.majlis, card: o.estimatedUnitArea});
  }
  const server = python(`
import acs_plot_rules as P
out=[]
for c in json.load(sys.stdin):
    rows=[{'metric':'room_count_per_unit','role':r,'expected':n} for r,n in (('bedroom',c['beds']),('bathroom',c['baths']),('majlis',c['majlis']),('living',1),('kitchen',1))]
    out.append(P.unit_area_estimate(c['id'],rows,'الخيار المختار'))
print(json.dumps(out))`, combos);
  assert.deepEqual(server, combos.map(c => c.card));
});

check('Arabic labels for every server finding code and the review scope', () => {
  const codes = python(`
import re
print(json.dumps(sorted(set(re.findall(r"'(PLOT_[A-Z_]+)'", open('acs_plot_rules.py',encoding='utf-8').read())))))`, null);
  const shown = codes.filter(c => !['PLOT_SITE_REQUIRED', 'PLOT_PARKING_COUNT_REQUIRED', 'PLOT_ENVELOPE_EMPTY', 'PLOT_BUILDING_EXCEEDS_ENVELOPE',
    'PLOT_PARKING_DOES_NOT_FIT', 'PLOT_PILOTIS_NEEDS_LEVELS', 'PLOT_PILOTIS_PROGRAM_CONFLICT', 'PLOT_ENVELOPE_TOO_SMALL'].includes(c));
  for (const code of shown) assert.ok(PLOT_ISSUE_NAMES[code], code);
  assert.ok(PLOT_SCOPE_NAMES.plot_rules);
});

check('overlay draws the envelope on every floor and stalls on the ground floor', () => {
  const summary = {envelope: [2, 5.5, 16, 17.5], parking: {stalls: [[0, 0, 2.5, 5.5], [2.5, 0, 2.5, 5.5]]}};
  assert.equal(overlay(summary, 0).length, 3);
  assert.equal(overlay(summary, 1).length, 1);
  assert.equal(overlay(summary, 1)[0].attrs['data-plot'], 'envelope');
  assert.deepEqual(overlay(null, 0), []);
});

// ── minimal DOM for the step-01 module ──────────────────────────────────────
class Node {
  constructor(tag, attrs = {}) { Object.assign(this, {tagName: tag.toUpperCase(), listeners: {}, hidden: false, textContent: '', placeholder: '', value: '', checked: false}, attrs); }
  addEventListener(kind, fn) { (this.listeners[kind] ||= []).push(fn); }
  fire(kind) { for (const node of [this, this.parent].filter(Boolean)) for (const fn of node.listeners[kind] || []) fn({target: this}); }
  after(node) { this.next = node; node.placed = true; }
  closest() { return this; }
  append(node) { this.next = node; node.placed = true; }
}
const registry = new Map();
const base = {cwType: 'residential', cwBrief: 'عمارة سكنية', cwWidth: '٢٠', cwDepth: '٢٥', cwLevels: '3', cwUnits: '2', cwUnitsScope: 'per_level', cwStreet: 'S'};
for (const [id, value] of Object.entries(base)) registry.set(id, new Node('input', {id, value}));
registry.set('cwResidential', new Node('section', {id: 'cwResidential'}));
registry.set('cwConfirmed', new Node('input', {id: 'cwConfirmed', type: 'checkbox', checked: true}));
const store = new Map();
globalThis.localStorage = {getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v))};
globalThis.document = {createElement(tag) {
  const node = new Node(tag);
  Object.defineProperty(node, 'innerHTML', {set(html) {
    for (const m of html.matchAll(/<(input|select|a|p)\b([^>]*)>/g)) {
      const id = /id="([^"]+)"/.exec(m[2])?.[1];
      if (!id) continue;
      const first = m[1] === 'select' ? /<option value="([^"]*)"/.exec(html.slice(m.index))?.[1] ?? '' : '';
      registry.set(id, new Node(m[1], {id, type: /type="([^"]+)"/.exec(m[2])?.[1] || m[1], value: first, parent: node}));
    }
  }});
  return node;
}};
const root = {querySelector: sel => registry.get(sel.slice(1)) || null};
const {createPlotRules} = await import('../../public/app/ui/plot-rules.mjs');
const $ = id => registry.get(id);

check('step-01 module wiring: placement, defaults shown, Arabic digits, re-confirmation', () => {
  const issueNames = {OTHER: 'x'}, scopeNames = {};
  const plot = createPlotRules(root, {storageKey: () => 'draft:plot', issueNames, scopeNames});
  assert.equal(issueNames.PLOT_UPPER_EXTERIOR_DOOR, 'باب خارجي في دور علوي');
  assert.equal(issueNames.OTHER, 'x');
  assert.ok(scopeNames.plot_rules);
  assert.equal($('cwResidential').next.id, 'cwPlot');
  assert.equal($('cwPlotStreet'), undefined, 'reuses the residential street select');
  assert.equal($('cwPlotSetbackS').placeholder, 'افتراضي 3');
  assert.equal($('cwPlotSetbackE').placeholder, 'افتراضي 2');
  assert.equal($('cwPlotCoverage').placeholder, 'افتراضي 65');
  assert.equal($('cwPlotParkingCount').placeholder, 'افتراضي 9');
  assert.match($('cwPlotSummary').textContent, /المساحة القابلة للبناء/);
  $('cwPlotSetbackW').value = '٠'; $('cwPlotSetbackW').fire('input');
  assert.equal($('cwConfirmed').checked, false);
  $('cwPlotParking').value = 'none'; $('cwPlotParking').fire('change');
  assert.deepEqual(plot.command(), {plot: {streets: ['S'], setbacks_m: {W: 0}, parking: {placement: 'none'}, landing_entries: false}});
  $('cwPlotStreet2').value = 'S'; $('cwPlotStreet2').fire('change');
  assert.throws(() => plot.command(), /جهة مختلفة/);
  assert.match($('cwPlotSummary').textContent, /جهة مختلفة/);
  $('cwPlotStreet2').value = 'E'; $('cwPlotStreet2').fire('change');
  const saved = JSON.parse(store.get('draft:plot'));
  assert.equal(saved.cwPlotSetbackW, '٠');
  $('cwPlotSetbackW').value = ''; plot.fill();
  assert.equal($('cwPlotSetbackW').value, '٠');
  $('cwType').value = 'warehouse'; $('cwType').fire('change');
  assert.equal(registry.get('cwPlotSummary').parent.hidden, true);
  assert.deepEqual(plot.command(), {});
  const drawn = [];
  plot.draw({level_index: 0}, {envelope: [2, 3, 16, 20], parking: {stalls: [[0, 0, 2.5, 5.5]]}}, (tag, attrs) => drawn.push([tag, attrs['data-plot']]));
  assert.deepEqual(drawn, [['rect', 'envelope'], ['rect', 'stall']]);
});

console.log('PLOT RULES UI: ' + passed + ' passed, 0 failed');
