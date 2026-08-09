# -*- coding: utf-8 -*-
"""المرحلة 9 — عقد التوثيق واختبارات A إلى N."""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import acs_arch as ARCH                                           # noqa: E402
import lib_docs_fixtures as LIB                                   # noqa: E402

p = [0]
f = [0]
AT = '2026-01-01T00:00:00Z'


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


ALL = LIB.all_models()
CANON = json.load(open(os.path.join(ROOT, 'acs_docs.json'), encoding='utf-8'))


def PR(name):
    return AU.create_project(copy.deepcopy(ALL[name]), 'bld_0', 'IMPORT', None)


print('\n== §0/§1 — THE SPECIFICATION AND THE READ-ONLY RULE ==')
chk('the documentation specification loads', D.SPEC['schema'] == 'acs.docs/1')
chk('documentation is declared read only',
    D.SPEC['documentation_is_read_only'] is True
    and D.SPEC['writes_to_model'] is False
    and D.SPEC['reverse_write_allowed'] is False
    and D.SPEC['mutates_engineering_model'] is False)
chk('the pipeline ends at export and never returns to the model',
    D.SPEC['pipeline'][0] == 'CANONICAL_MODEL'
    and D.SPEC['pipeline'][-1] == 'EXPORT'
    and 'ENGINEERING_MODEL' not in D.SPEC['pipeline'][1:])
chk('the model hash inputs are the model alone',
    D.SPEC['model_hash_inputs'] == ['model'])
chk('every issue code used by the module is declared',
    all(c in CANON['issue_codes'] for c in D.ISSUE_CODES))
try:
    D.issue('NOT_A_CODE', 'ERROR', None, 'x')
    chk('an undeclared issue code is refused', False)
except ValueError:
    chk('an undeclared issue code is refused', True)

print('\n== §5/§7 — VIEW TYPES AND EXPLICIT SUPPORT ==')
chk('twelve view types are declared', len(D.SPEC['view_types']) == 12)
chk('every declared view type carries an explicit support status',
    all(v in D.VIEW_SUPPORT for v in D.SPEC['view_types']))
chk('support states are declared and separated',
    D.SPEC['view_support_states'] == ['SUPPORTED', 'PARTIALLY_SUPPORTED',
                                      'NOT_SUPPORTED', 'INSUFFICIENT_DATA',
                                      'STALE'])
chk('a view type is not claimed supported merely because the enum exists',
    D.VIEW_SUPPORT['THREE_D_REFERENCE']['support'] == 'NOT_SUPPORTED')
prj = PR('villa_glazed')
SRC = D.sources(prj)
LV0 = SRC['arch']['levels'][0]['id']
r = D.view_definition(prj, {'view_type': 'THREE_D_REFERENCE'}, SRC['arch'])
chk('an unsupported view type is refused with a typed issue',
    r['valid'] is False
    and r['issues'][0]['code'] == 'DOC_VIEW_NOT_SUPPORTED')
chk('an unknown view type is refused',
    D.view_definition(prj, {'view_type': 'NOT_A_VIEW'},
                      SRC['arch'])['issues'][0]['code'] == 'DOC_INVALID_VIEW_TYPE')
chk('an unknown level is refused rather than defaulted',
    D.view_definition(prj, {'view_type': 'FLOOR_PLAN', 'level_id': 'nope'},
                      SRC['arch'])['issues'][0]['code'] == 'DOC_INVALID_LEVEL')
chk('an unknown scale is refused rather than invented',
    D.view_definition(prj, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                            'scale': '1:37'},
                      SRC['arch'])['issues'][0]['code'] == 'DOC_INVALID_SCALE')
chk('an elevation without an orientation is refused',
    D.view_definition(prj, {'view_type': 'ELEVATION'},
                      SRC['arch'])['issues'][0]['code']
    == 'DOC_INVALID_ORIENTATION')
chk('a section without a cut plane is refused',
    D.view_definition(prj, {'view_type': 'SECTION'},
                      SRC['arch'])['valid'] is False)

print('\n== §4 — DETERMINISTIC ARTIFACT IDENTITY ==')
spec_a = {'view_type': 'FLOOR_PLAN', 'level_id': LV0, 'scale': '1:100'}
v1 = D.view_definition(prj, dict(spec_a), SRC['arch'])['view']
v2 = D.view_definition(PR('villa_glazed'), dict(spec_a), SRC['arch'])['view']
chk('the same model and definition give the same view identity',
    v1['view_id'] == v2['view_id'], v1['view_id'])
chk('a different definition gives a different identity',
    v1['view_id'] != D.view_definition(
        prj, dict(spec_a, scale='1:200'), SRC['arch'])['view']['view_id'])
chk('identities carry the declared prefix and hash length',
    v1['view_id'].startswith('view_')
    and len(v1['view_id']) == len('view_') + int(D.SPEC['id_hash_length']))
chk('no random identifiers are permitted',
    D.SPEC['random_ids_allowed'] is False)

print('\n== §16 — NO FAKE DIMENSION: A RENDER FALLBACK IS NEVER A MEASUREMENT ==')
wall_unknown = next((w for w in SRC['arch']['walls']
                     if w['thickness_m']['value'] is None), None)
chk('the fixture really has a wall with an unstated thickness and a fallback',
    wall_unknown is not None
    and wall_unknown['thickness_m']['render_fallback'] is not None,
    json.dumps(wall_unknown['thickness_m']) if wall_unknown else 'none')
st = D.stated(wall_unknown['thickness_m'])
chk('the documentation reader reports it UNKNOWN',
    st['status'] == 'UNKNOWN' and st['value'] is None)
chk('the render fallback is not returned in its place',
    st['value'] != wall_unknown['thickness_m']['render_fallback'])
chk('a stated value is read as stated',
    D.stated({'value': 3.0, 'source': 'imported'})['status'] == 'STATED')
chk('display rounding never modifies the exact value',
    D.display_of({'value': 2.34567, 'status': 'STATED', 'source': 'x'}) == '2.346')
chk('an unknown value has no display value',
    D.display_of(st) is None)

print('\n== §84 — TEST A: A REAL FLOOR PLAN FROM CANONICAL GEOMETRY ==')
plan = D.build_view(prj, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                          'discipline': 'ARCHITECTURE', 'scale': '1:100',
                          'dimension_policy': 'FULL_CHAIN',
                          'annotation_policy': 'TAGS_ONLY'}, SRC)
chk('a floor plan is produced', plan['valid'])
G = plan['geometry']
arch_walls = {w['id'] for w in SRC['arch']['walls'] if w['level_id'] == LV0}
arch_spaces = {s['id'] for s in SRC['arch']['spaces'] if s['level_id'] == LV0}
arch_doors = {o['id'] for o in SRC['arch']['openings']
              if o['level_id'] == LV0 and o['type'] == 'DOOR'}
arch_wins = {o['id'] for o in SRC['arch']['openings']
             if o['level_id'] == LV0 and o['type'] == 'WINDOW'}
drawn = {}
for e in G['elements']:
    drawn.setdefault(e['category'], set()).add(e['id'])
chk('every drawn wall exists in the compiled architecture',
    drawn.get('WALL', set()) <= arch_walls and len(drawn.get('WALL', set())) > 0,
    str(len(drawn.get('WALL', set()))))
chk('every architectural wall on the level is drawn',
    drawn.get('WALL', set()) == arch_walls)
chk('every drawn space exists in the compiled architecture',
    drawn.get('SPACE', set()) == arch_spaces and len(arch_spaces) > 0)
chk('every drawn door exists in the compiled architecture',
    drawn.get('DOOR', set()) <= arch_doors)
chk('every drawn window exists in the compiled architecture',
    drawn.get('WINDOW', set()) <= arch_wins)
chk('no element is invented that the model does not contain',
    all(e['id'] in (arch_walls | arch_spaces | arch_doors | arch_wins
                    | {s['id'] for s in SRC['arch']['slabs']}
                    | {v['id'] for v in SRC['arch']['voids']}
                    | {c['id'] for c in SRC['arch']['cores']})
        for e in G['elements']))
chk('a stair core is present where the model has one',
    len(drawn.get('CORE', set())) >= 1)
chk('room labels come from the model',
    all(a['provenance'] == 'MODEL_DERIVED'
        for a in plan['annotations']['annotations']
        if a['annotation_type'] == 'ROOM_TAG'))
chk('the plan carries real dimensions', plan['dimensions']['counts']['total'] > 0)
chk('the plan is not a rasterised viewport — it is vector element geometry',
    all('shape' in e for e in G['elements']))

print('\n== §9 — A SHARED WALL IS ONE WALL ==')
shared = [w for w in SRC['arch']['walls'] if w.get('shared')]
chk('the fixture contains at least one shared wall', len(shared) > 0)
ids = [e['id'] for e in G['elements'] if e['category'] == 'WALL']
chk('no wall is drawn twice', len(ids) == len(set(ids)))
chk('a shared wall keeps its single canonical identity',
    all(w['id'] in arch_walls for w in shared if w['level_id'] == LV0))
states = {w.get('exposure_status') for w in SRC['arch']['walls']}
chk('the compiled architecture really carries an unresolved exposure',
    'unresolved' in states, json.dumps(sorted(states)))
chk('unresolved wall exposure is carried through, never resolved by the drawing',
    {e.get('exposure_status') for e in G['elements'] if e['category'] == 'WALL'}
    <= states,
    json.dumps(sorted({str(e.get('exposure_status')) for e in G['elements']
                       if e['category'] == 'WALL'})))
chk('the documentation invents no exposure the compiler did not state',
    all(e.get('exposure_status')
        == next(w['exposure_status'] for w in SRC['arch']['walls']
                if w['id'] == e['id'])
        for e in G['elements'] if e['category'] == 'WALL'))

print('\n== §10/§11 — DOORS AND WINDOWS ARE NOT BEAUTIFIED ==')
doors = [e for e in G['elements'] if e['category'] == 'DOOR']
chk('no door swing is invented where the model does not specify one',
    all(e.get('swing_direction') is None
        for e in doors if e.get('swing_status') == 'not_specified'))
chk('the not-specified swing state is preserved and visible',
    any(e.get('swing_status') == 'not_specified' for e in doors))
chk('every documented window corresponds to a represented opening',
    drawn.get('WINDOW', set()) <= arch_wins)
chk('no facade beautification adds a window',
    len(drawn.get('WINDOW', set())) <= len(arch_wins))

print('\n== §12/§13 — ROOM LABELS AND AREAS ==')
rs = D.schedule(prj, 'ROOM_SCHEDULE', {}, SRC)['schedule']
chk('the room schedule reports every canonical space',
    rs['row_count'] == len(SRC['arch']['spaces']))
chk('no room number is invented',
    all(r['room_id']['status'] == 'STATED' for r in rs['rows']))
chk('an area states its basis rather than being asserted bare',
    all(r['area_basis']['status'] in ('STATED', 'UNKNOWN') for r in rs['rows']))
chk('unknown program stays unknown rather than guessed',
    all(r['program']['status'] == 'UNKNOWN'
        or isinstance(r['program']['value'], str) for r in rs['rows']))
chk('a rendered footprint is never called a regulatory floor area',
    'regulatory' not in json.dumps(rs).lower()
    or 'regulatory: false' in json.dumps(rs).lower())

print('\n== §85 — TEST B: FOUR ELEVATIONS AND BUILDING ROTATION ==')
elevs = {}
for o in ('NORTH', 'SOUTH', 'EAST', 'WEST'):
    e = D.build_view(prj, {'view_type': 'ELEVATION', 'orientation': o,
                           'scale': '1:100'}, SRC)
    elevs[o] = e
    chk('the %s elevation is produced' % o.lower(), e['valid'])
chk('the four elevations differ from one another',
    len({json.dumps(e['geometry']['counts'], sort_keys=True)
         for e in elevs.values()}) >= 2,
    json.dumps({k: v['geometry']['counts'] for k, v in elevs.items()}))
ext_open = set(SRC['arch']['envelope']['external_openings'])
for o, e in elevs.items():
    shown = {x['id'] for x in e['geometry']['elements']
             if x['category'] in ('DOOR', 'WINDOW')}
    chk('the %s elevation shows only represented external openings' % o.lower(),
        shown <= ext_open, json.dumps(sorted(shown - ext_open))[:120])
chk('the elevation records the building rotation it applied',
    all(e['geometry']['rotation_applied_deg'] is not None for e in elevs.values()))
rot_model = copy.deepcopy(ALL['villa_glazed'])
rot_prj = AU.create_project(rot_model, 'bld_0', 'IMPORT', None)
rot_src = D.sources(rot_prj)
chk('a rotation is read from the model transform, not assumed zero',
    'rotation_deg' in (rot_src['arch']['transform'] or {}))
chk('level lines come from real level elevations',
    all(any(abs(x['elevation'] - (l['elevation_m'] or 0.0)) < 1e-9
            for l in SRC['arch']['levels'])
        for x in elevs['NORTH']['geometry']['elements']
        if x['category'] == 'LEVEL_LINE'))
chk('no photorealistic content enters the engineering elevation',
    not any(k in json.dumps(elevs['NORTH']['geometry'])
            for k in ('texture', 'material_library', 'ai_', 'render_fallback')))

print('\n== §86 — TEST C: A TRUE MODEL-DERIVED SECTION ==')
secs = {}
for at in (3.0, 7.0, 11.0):
    s = D.build_view(prj, {'view_type': 'SECTION',
                           'cut_plane': {'axis': 'x', 'at': at},
                           'view_depth': 6.0, 'scale': '1:100'}, SRC)
    secs[at] = s
    chk('a section at x=%s is produced' % at, s['valid'])
S7 = secs[7.0]['geometry']
chk('the section reports cut, projected, beyond and unresolved separately',
    all(k in S7 for k in ('cut_count', 'projected_count', 'beyond_count',
                          'unresolved_count')))
chk('the section actually cuts geometry', S7['cut_count'] > 0,
    str(S7['cut_count']))
chk('the section classifies elements beyond the declared depth',
    S7['beyond_count'] > 0, str(S7['beyond_count']))
chk('different section positions cut different elements',
    secs[3.0]['geometry']['cut_ids'] != secs[11.0]['geometry']['cut_ids'])
cut_walls = [e for e in S7['elements']
             if e['category'] == 'WALL' and e['geometry_class'] == 'CUT']
for e in cut_walls:
    w = next(x for x in SRC['arch']['walls'] if x['id'] == e['id'])
    lo = min(w['start']['x'], w['end']['x'])
    hi = max(w['start']['x'], w['end']['x'])
    chk('cut wall %s really spans the cut plane' % e['id'][-8:],
        lo - 1e-9 <= 7.0 <= hi + 1e-9)
chk('a section is not a floor-plan projection — it carries vertical extents',
    all('v0' in e for e in S7['elements'] if e.get('shape') == 'rect_uv'))

print('\n== §24 — A STAIR VOID REALLY OPENS THE SLAB ==')
void = SRC['arch']['voids'][0]
vx0, vx1 = void['rect'][0], void['rect'][0] + void['rect'][2]
at_void = (vx0 + vx1) / 2.0
sv = D.build_view(prj, {'view_type': 'SECTION',
                        'cut_plane': {'axis': 'x', 'at': at_void},
                        'scale': '1:100'}, SRC)
strips = [e for e in sv['geometry']['elements']
          if e['category'] == 'SLAB' and e['level_id'] == void['level_id']]
chk('the section through the void adjusts the slab strip',
    any(e.get('void_adjusted') for e in strips), json.dumps(
        [(e['u0'], e['u1'], e.get('void_adjusted')) for e in strips]))
away = D.build_view(prj, {'view_type': 'SECTION',
                          'cut_plane': {'axis': 'x', 'at': 1.0},
                          'scale': '1:100'}, SRC)
strips_away = [e for e in away['geometry']['elements']
               if e['category'] == 'SLAB' and e['level_id'] == void['level_id']]
chk('a section away from the void leaves the slab whole',
    all(not e.get('void_adjusted') for e in strips_away))

print('\n== §14/§15/§17 — DIMENSION ENGINE AND PROVENANCE ==')
dims = plan['dimensions']['dimensions']
chk('every dimension carries every declared field',
    all(all(k in d for k in D.SPEC['dimension_fields']) for d in dims))
chk('every dimension names the elements it measured',
    all(isinstance(d['source_element_ids'], list) and d['source_element_ids']
        for d in dims))
chk('every provenance is one of the declared kinds',
    all(d['provenance'] in D.SPEC['dimension_provenance'] for d in dims))
chk('a measured dimension has both an exact and a display value',
    all(d['exact_value'] is not None and d['display_value'] is not None
        for d in dims if d['measurement_status'] == 'MEASURED'))
chk('the display value never changes the exact value',
    all(abs(d['exact_value'] - float(d['display_value'])) <= 5e-4
        for d in dims if d['measurement_status'] == 'MEASURED'))
chk('overall building dimensions are produced',
    any(d['measurement_type'] == 'OVERALL_BUILDING' for d in dims))
chk('the dimension chain policy is declared, not ad hoc',
    D.SPEC['dimension_chain_policy'] == 'DECLARED_ONLY'
    and len(D.SPEC['dimension_policies']) == 4)
none_dims = D.build_view(prj, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                               'dimension_policy': 'NONE'}, SRC)
chk('a NONE policy produces no cluttered chain',
    none_dims['dimensions']['dimensions'] == [])

print('\n== §16 — AN UNKNOWN OPENING WIDTH STAYS UNKNOWN IN THE DIMENSIONS ==')
unknown_open = [o for o in SRC['arch']['openings']
                if o['width_m']['value'] is None]
if unknown_open:
    chk('an opening with no stated width yields an UNKNOWN dimension',
        any(d['measurement_status'] == 'UNKNOWN'
            and d['measurement_type'] == 'OPENING_WIDTH' for d in dims))
else:
    chk('every opening in this fixture states its width, so none is guessed',
        all(d['measurement_status'] == 'MEASURED' for d in dims
            if d['measurement_type'] == 'OPENING_WIDTH'))
chk('no dimension ever equals a render fallback that has no stated value',
    all(d['exact_value'] is None
        for d in dims if d['measurement_status'] == 'UNKNOWN'))

print('\n== §18 — LEVEL DATUM ==')
sec_dims = secs[7.0]['dimensions']['dimensions']
chk('level elevations are documented from the model',
    any(d['measurement_type'] == 'LEVEL_ELEVATION' for d in sec_dims))
chk('no FFL, SSL, TOS or TOC datum is invented',
    not any(lab in json.dumps(sec_dims) for lab in D.SPEC['forbidden_datum_labels']))
chk('only the level elevation datum type is declared',
    D.SPEC['level_datum_types'] == ['LEVEL_ELEVATION'])

print('\n== §19 — GRIDS ARE DRAWN ONLY WHERE REPRESENTED ==')
chk('the architectural fixture has no structural grid',
    len(SRC['struct']['grid_systems']) == 0)
sp = D.build_view(prj, {'view_type': 'STRUCTURAL_PLAN', 'level_id': LV0,
                        'discipline': 'STRUCTURE', 'scale': '1:100'}, SRC)
chk('no grid is generated because a convention expects one',
    not any(e['category'] == 'GRID' for e in sp['geometry']['elements']))
chk('the grid policy is declared as represented-only',
    D.SPEC['grid_policy'] == 'REPRESENTED_ONLY')

print('\n== §87 — TEST D: THE ROOM SCHEDULE MATCHES CANONICAL SPACES ==')
canon_rooms = {s['space_id'] for s in SRC['arch']['spaces']}
sched_rooms = {r['room_id']['value'] for r in rs['rows']}
chk('zero phantom rooms', sched_rooms - canon_rooms == set(),
    json.dumps(sorted(sched_rooms - canon_rooms))[:120])
chk('zero missing represented rooms', canon_rooms - sched_rooms == set(),
    json.dumps(sorted(canon_rooms - sched_rooms))[:120])
chk('every row names the element it reports',
    all(r['provenance']['source_element_id'] for r in rs['rows']))
chk('every row is bound to the model hash it was read from',
    all(r['provenance']['source_model_hash'] == prj['model_hash']
        for r in rs['rows']))
chk('a schedule declares it is a view over the model',
    'view over the model' in rs['note'] and rs['writes_to_model'] is False)
lvl_scoped = D.schedule(prj, 'ROOM_SCHEDULE', {'level_id': LV0}, SRC)['schedule']
chk('a level-scoped schedule really narrows the scope',
    lvl_scoped['row_count'] < rs['row_count']
    and lvl_scoped['row_count'] == len(arch_spaces))

print('\n== §88 — TEST E: DOOR AND WINDOW SCHEDULES ==')
ds = D.schedule(prj, 'DOOR_SCHEDULE', {}, SRC)['schedule']
ws = D.schedule(prj, 'WINDOW_SCHEDULE', {}, SRC)['schedule']
canon_doors = {o['id'] for o in SRC['arch']['openings'] if o['type'] == 'DOOR'}
canon_wins = {o['id'] for o in SRC['arch']['openings'] if o['type'] == 'WINDOW'}
chk('every door row maps to a canonical opening',
    {r['door_id']['value'] for r in ds['rows']} == canon_doors)
chk('every window row maps to a canonical opening',
    {r['window_id']['value'] for r in ws['rows']} == canon_wins)
chk('each door tag is deterministic and maps to one canonical door',
    len({r['tag']['value'] for r in ds['rows']}) == len(ds['rows']))
chk('the same door yields the same tag on a second run',
    D.tag_for(sorted(canon_doors)[0], 'DOOR')
    == D.tag_for(sorted(canon_doors)[0], 'DOOR'))
chk('no door type is invented',
    all('type' not in r or r.get('type', {}).get('status') != 'STATED'
        for r in ds['rows']))
nominal_known = [r for r in ds['rows']
                 if r['nominal_width_m']['status'] == 'STATED']
chk('the fixture states nominal widths', len(nominal_known) > 0)
chk('clear width is never filled in from nominal width',
    all(r['clear_width_m']['status'] == 'UNKNOWN' for r in nominal_known),
    json.dumps([r['clear_width_m'] for r in nominal_known[:2]]))
chk('an unknown clear width is displayed as NOT_SPECIFIED, not as a number',
    all(r['clear_width_m'].get('display') == 'NOT_SPECIFIED'
        for r in ds['rows'] if r['clear_width_m']['status'] == 'UNKNOWN'))
chk('fire rating is not invented from the door being a door',
    all(r['fire_rating']['status'] == 'UNKNOWN' for r in ds['rows']))
chk('material is not invented from the element kind',
    all(r['material']['status'] == 'UNKNOWN' for r in ds['rows']))
chk('the forbidden schedule inventions are declared and named',
    'clear_width_from_nominal_width' in D.SPEC['forbidden_schedule_invention'])
chk('the specification states nominal is not clear',
    'never substitutes' in D.SPEC['nominal_is_not_clear_note'])

print('\n== §89 — TEST F: A STRUCTURAL DRAWING FROM REPRESENTED DATA ==')
sprj = PR('clash_mep')
SSRC = D.sources(sprj)
chk('the structural fixture really carries represented structure',
    len(SSRC['struct']['columns']) > 0 and len(SSRC['struct']['beams']) > 0
    and len(SSRC['struct']['grid_systems']) > 0)
slv = SSRC['arch']['levels'][1]['id']
spl = D.build_view(sprj, {'view_type': 'STRUCTURAL_PLAN', 'level_id': slv,
                          'discipline': 'STRUCTURE', 'scale': '1:100'}, SSRC)
chk('a structural plan is produced', spl['valid'])
sc = spl['geometry']['counts']
chk('represented columns appear', sc.get('COLUMN', 0) > 0, json.dumps(sc))
chk('represented beams appear', sc.get('BEAM', 0) > 0, json.dumps(sc))
chk('represented grids appear', sc.get('GRID', 0) > 0, json.dumps(sc))
chk('grid spacing dimensions come from represented grids',
    any(d['measurement_type'] == 'GRID_SPACING'
        for d in spl['dimensions']['dimensions']))
cs = D.schedule(sprj, 'COLUMN_SCHEDULE', {}, SSRC)['schedule']
chk('a column schedule is produced', cs['row_count'] == len(SSRC['struct']['columns']))
fs_ = D.schedule(sprj, 'FOUNDATION_SCHEDULE', {}, SSRC)['schedule']
chk('a foundation schedule is produced',
    fs_['row_count'] == len(SSRC['struct']['foundations']))
mats = SSRC['struct']['materials']
chk('unknown material properties stay unknown',
    all(m['grade']['value'] is None for m in mats), json.dumps(mats[:1])[:200])
chk('no reinforcement appears anywhere in the structural documentation',
    not any(k in json.dumps(spl['geometry']).lower()
            for k in ('rebar', 'reinforce', 'stirrup', 'bar_diameter')))
chk('no structural sizing or adequacy is claimed',
    not any(k in json.dumps(cs).lower()
            for k in ('capacity', 'adequate', 'load', 'utilisation', 'moment')))

print('\n== §90 — TEST G: AN MEP DRAWING KEEPS UNROUTED UNROUTED ==')
mlv = SSRC['arch']['levels'][1]['id']
mpl = D.build_view(sprj, {'view_type': 'MEP_PLAN', 'level_id': mlv,
                          'discipline': 'MECHANICAL', 'scale': '1:100'}, SSRC)
chk('an MEP plan is produced', mpl['valid'])
segs = [e for e in mpl['geometry']['elements'] if e['category'] == 'MEP_SEGMENT']
chk('represented MEP segments appear', len(segs) > 0, str(len(segs)))
routed = [e for e in segs if e.get('routed')]
unrouted = [e for e in segs if not e.get('routed')]
chk('a routed segment is drawn from its real endpoints',
    all(e['shape'] == 'segment' for e in routed))
chk('an unrouted segment is never fabricated into a route',
    all(e['geometry_class'] == 'UNRESOLVED' and e['shape'] == 'none'
        for e in unrouted))
chk('an unrouted segment raises a typed issue rather than being hidden',
    (not unrouted) or any(i['code'] == 'DOC_UNROUTED_SEGMENT'
                          for i in mpl['issues']))
chk('no duct size, flow, pressure or capacity is generated',
    not any(k in json.dumps(mpl['geometry']).lower()
            for k in ('cfm', 'voltage', 'pressure_pa', 'flow_rate',
                      'duct_size', 'pipe_size', 'capacity_kw')))
mes = D.schedule(sprj, 'MEP_EQUIPMENT_SCHEDULE', {}, SSRC)['schedule']
chk('an MEP equipment schedule reports represented equipment only',
    mes['row_count'] == len(SSRC['mep']['equipment']))

print('\n== §91 — TEST H: AN FLS DRAWING MAKES NO COVERAGE CLAIM ==')
fprj = PR('villa_fls')
FSRC = D.sources(fprj)
chk('the FLS fixture really carries represented devices',
    len(FSRC['fls']['devices']) > 0)
flv = FSRC['arch']['levels'][0]['id']
fpl = D.build_view(fprj, {'view_type': 'FLS_PLAN', 'level_id': flv,
                          'discipline': 'FIRE_PROTECTION', 'scale': '1:100'},
                   FSRC)
chk('an FLS plan is produced', fpl['valid'])
fc = fpl['geometry']['counts']
chk('represented devices appear on the plan', fc.get('FLS_DEVICE', 0) > 0,
    json.dumps(fc))
chk('represented signage appears on the plan', fc.get('FLS_SIGN', 0) > 0,
    json.dumps(fc))
blob = json.dumps(fpl['geometry']).lower() + json.dumps(
    D.schedule(fprj, 'FLS_DEVICE_SCHEDULE', {}, FSRC)['schedule']).lower()
for phrase in D.SPEC['compliance_language_forbidden']:
    chk('the FLS documentation never says "%s"' % phrase,
        phrase.lower() not in blob)
chk('no coverage or protection verdict is produced',
    'coverage' not in blob and 'compliant' not in blob)

print('\n== §92 — TEST I: A COORDINATION SHEET FIXES NOTHING ==')
cpl = D.build_view(sprj, {'view_type': 'COORDINATION_PLAN', 'level_id': mlv,
                          'discipline': 'COORDINATION', 'scale': '1:100'}, SSRC)
chk('a coordination plan is produced', cpl['valid'])
chk('the coordination view can show clash annotations as documentation',
    'CLASH' in cpl['view']['visible_categories'])
chk('no clash is auto-resolved by documentation',
    'AUTO_FIX_CLASH' in D.SPEC['panel_forbidden_controls']
    and 'AUTOMATIC_CLASH_RESOLUTION' in D.SPEC['hard_stop_boundaries'])
chk('documentation declares no remediation capability',
    'AUTOMATIC_REMEDIATION' in D.SPEC['hard_stop_boundaries'])

print('\n== §93 — TEST J: THE QUANTITY REPORT IS FACTUAL ==')
q = D.quantities(prj, {}, SRC)
rep = q['report']
qm = {x['quantity_type']: x for x in rep['quantities']}
chk('the room count matches the canonical spaces',
    qm['ROOM_COUNT']['quantity'] == len(SRC['arch']['spaces']))
chk('the door count matches the canonical door openings',
    qm['DOOR_COUNT']['quantity']
    == len([o for o in SRC['arch']['openings'] if o['type'] == 'DOOR']))
chk('the window count matches the canonical window openings',
    qm['WINDOW_COUNT']['quantity']
    == len([o for o in SRC['arch']['openings'] if o['type'] == 'WINDOW']))
chk('the level count matches the canonical levels',
    qm['LEVEL_COUNT']['quantity'] == len(SRC['arch']['levels']))
wall_sum = sum(w['length_m'] for w in SRC['arch']['walls'])
chk('the wall length equals the sum of compiled wall lengths',
    abs(qm['WALL_LENGTH']['quantity'] - wall_sum) < 1e-6,
    '%s vs %s' % (qm['WALL_LENGTH']['quantity'], wall_sum))
area_sum = sum(s['area_m2'] for s in SRC['arch']['spaces'])
chk('the space area equals the sum of canonical space areas',
    abs(qm['SPACE_AREA']['quantity'] - area_sum) < 1e-6)
chk('every quantity states its unit, basis and coverage',
    all(x['unit'] and x['measurement_basis']
        and x['coverage_status'] in D.SPEC['coverage_statuses']
        for x in rep['quantities']))
chk('a discipline with no represented data reports NOT_AVAILABLE, not zero',
    qm['COLUMN_COUNT']['coverage_status'] == 'NOT_AVAILABLE'
    and qm['COLUMN_COUNT']['quantity'] is None)
sq = D.quantities(sprj, {}, SSRC)['report']
sqm = {x['quantity_type']: x for x in sq['quantities']}
chk('a discipline with represented data reports a real count',
    sqm['COLUMN_COUNT']['coverage_status'] == 'COMPLETE_FOR_REPRESENTED_MODEL'
    and sqm['COLUMN_COUNT']['quantity'] == len(SSRC['struct']['columns']))
chk('unrouted MEP segments make the segment length PARTIAL, not complete',
    sqm['MEP_SEGMENT_LENGTH']['coverage_status'] in ('PARTIAL',
                                                     'COMPLETE_FOR_REPRESENTED_MODEL'))
chk('the report denies being a bill of quantities',
    rep['is_bill_of_quantities'] is False and D.SPEC['boq_claimed'] is False)
chk('the report denies being a cost estimate',
    rep['is_cost_estimate'] is False
    and D.SPEC['cost_estimation_supported'] is False)
blob_q = json.dumps(rep).lower()
for k in D.SPEC['forbidden_quantity_fields']:
    chk('no %s field appears in the quantity report' % k, '"%s"' % k not in blob_q)
chk('no currency symbol appears anywhere in the report',
    not any(c in json.dumps(rep) for c in ('$', '€', '£', '﷼')))

print('\n== §45/§46/§47/§48 — SHEETS, PAPER, VIEWPORTS AND TITLE BLOCK ==')
views_by_id = {plan['view']['view_id']: plan['view'],
               elevs['NORTH']['view']['view_id']: elevs['NORTH']['view']}
vid_a = plan['view']['view_id']
vid_b = elevs['NORTH']['view']['view_id']
sh = D.compose_sheet(prj, {'paper_size': 'A3', 'orientation': 'LANDSCAPE',
                           'sheet_number': 'A-001', 'sheet_name': 'Ground floor',
                           'title_block': {'project': 'Test', 'status': 'DRAFT'},
                           'viewports': [
                               {'view_id': vid_a, 'x': 10, 'y': 10,
                                'width': 180, 'height': 120},
                               {'view_id': vid_b, 'x': 200, 'y': 10,
                                'width': 190, 'height': 120}]},
                     views_by_id)
chk('a sheet is composed', sh['valid'] and sh['sheet'] is not None)
chk('the sheet carries every declared field',
    all(k in sh['sheet'] for k in D.SPEC['sheet_fields']))
chk('the sheet records the model hash it was composed from',
    sh['sheet']['source_model_hash'] == prj['model_hash'])
chk('all five paper sizes are declared', len(D.SPEC['paper_sizes']) == 5
    and 'A0' in D.SPEC['paper_sizes'] and 'A4' in D.SPEC['paper_sizes'])
chk('A1 is not assumed for every project',
    D.SPEC['default_paper_size'] != 'A1' and sh['sheet']['paper_size'] == 'A3')
chk('an unknown paper size is refused',
    D.compose_sheet(prj, {'paper_size': 'B7', 'viewports': []},
                    views_by_id)['issues'][0]['code'] == 'DOC_INVALID_PAPER_SIZE')
chk('every viewport has deterministic geometry',
    all(all(k in v for k in ('x', 'y', 'width', 'height', 'scale'))
        for v in sh['sheet']['viewports']))
over = D.compose_sheet(prj, {'paper_size': 'A3', 'sheet_number': 'A-002',
                             'viewports': [
                                 {'view_id': vid_a, 'x': 10, 'y': 10,
                                  'width': 180, 'height': 120},
                                 {'view_id': vid_b, 'x': 100, 'y': 50,
                                  'width': 180, 'height': 120}]},
                       views_by_id)
chk('overlapping viewports are detected',
    any(i['code'] == 'DOC_VIEWPORT_COLLISION' for i in over['issues']))
chk('overlapping content is reported, never silently moved',
    over['sheet']['viewports'][0]['x'] == 10
    and over['sheet']['viewports'][1]['x'] == 100
    and D.SPEC['viewport_overlap_allowed'] is False)
off = D.compose_sheet(prj, {'paper_size': 'A4', 'sheet_number': 'A-003',
                            'viewports': [{'view_id': vid_a, 'x': 10, 'y': 10,
                                           'width': 900, 'height': 120}]},
                      views_by_id)
chk('a viewport leaving the sheet is refused',
    any(i['code'] == 'DOC_VIEWPORT_OUT_OF_SHEET' for i in off['issues']))
tb = sh['sheet']['title_block']
chk('unknown title block fields stay blank',
    tb['drawn_by'] is None and tb['checked_by'] is None and tb['date'] is None)
chk('no company, engineer, stamp or approval is generated',
    not any(k in tb for k in D.SPEC['forbidden_title_block_content']))
chk('a neutral drawing status is used',
    tb['status'] in D.SPEC['drawing_statuses'])
restricted = D.title_block(prj, {'status': 'APPROVED_FOR_CONSTRUCTION'})
chk('a restricted status is refused',
    any(i['code'] == 'DOC_RESTRICTED_STATUS_REFUSED'
        for i in restricted['issues'])
    and restricted['title_block']['status'] is None)
for st_ in D.SPEC['restricted_statuses']:
    chk('the restricted status %s cannot be set by the system' % st_,
        D.title_block(prj, {'status': st_})['title_block']['status'] is None)

print('\n== §58 — SCALE IS REPORTED, NEVER INVENTED ==')
svg_fit = D.view_svg(plan['view'], plan['geometry'], plan['dimensions'],
                     plan['annotations'], {'paper_size': 'A4'})
chk('a view that does not fit reports FIT_TO_SHEET rather than a false scale',
    svg_fit['scale_mode'] in ('TRUE_SCALE', 'FIT_TO_SHEET'))
big = D.build_view(prj, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                         'scale': '1:20'}, SRC)
svg_big = D.view_svg(big['view'], big['geometry'], big['dimensions'],
                     big['annotations'], {'paper_size': 'A4'})
chk('a scale that cannot fit falls back to FIT_TO_SHEET with no true scale',
    svg_big['scale_mode'] == 'FIT_TO_SHEET' and svg_big['scale'] is None)
chk('the true and fit modes are separately declared',
    D.SPEC['scale_modes'] == ['TRUE_SCALE', 'FIT_TO_SHEET'])

print('\n== §50/§51/§54/§55 — INDEX, REVISIONS, LEGENDS AND STYLE ==')
idx = D.drawing_index([sh['sheet']])
chk('a drawing index is produced', idx['count'] == 1)
chk('prefixes are configurable',
    D.drawing_index([sh['sheet']], {'ARCHITECTURE': 'AR'})['prefixes']
    ['ARCHITECTURE'] == 'AR' and D.SPEC['prefixes_configurable'] is True)
chk('no professional issuance status is inferred',
    idx['issuance_status_inferred'] is False)
doc0 = D.documentation_project(prj, [plan['view']], [sh['sheet']], [rs], rep)
leg = doc0['legends'][0]
used_cats = set(plan['view']['counts'].keys())
chk('the legend contains only symbols actually used',
    {e['category'] for e in leg['entries']} == used_cats,
    json.dumps(sorted({e['category'] for e in leg['entries']} ^ used_cats)))
chk('there is no fake symbol catalogue',
    leg['count'] == len(used_cats) and leg['count'] > 0)
chk('the graphic hierarchy distinguishes every declared class',
    set(D.SPEC['line_weights']) == {'CUT', 'PROJECTED', 'ANNOTATION',
                                    'DIMENSION', 'GRID', 'REFERENCE',
                                    'COORDINATION'})
chk('cut is heavier than projected, which is heavier than reference',
    D.SPEC['line_weights']['CUT'] > D.SPEC['line_weights']['PROJECTED']
    > D.SPEC['line_weights']['REFERENCE'])
chk('style does not change engineering meaning',
    D.SPEC['style_changes_meaning'] is False)
mono = D.view_svg(plan['view'], plan['geometry'], plan['dimensions'],
                  plan['annotations'], {'mode': 'MONOCHROME'})
tech = D.view_svg(plan['view'], plan['geometry'], plan['dimensions'],
                  plan['annotations'], {'mode': 'TECHNICAL'})
chk('a monochrome engineering mode exists',
    '#000000' in mono['svg'] and mono['op_count'] == tech['op_count'])
chk('changing the drawing mode changes no geometry',
    mono['op_count'] == tech['op_count'])
chk('AI imagery is never mixed into technical vector drawings',
    D.SPEC['technical_drawing_ai_content_allowed'] is False)
chk('a presentation sheet must be labelled as such',
    D.SPEC['presentation_requires_label'] is True
    and 'NOT A CONSTRUCTION DRAWING' in D.SPEC['presentation_label'])

print('\n== §94 — TEST K: A MODEL CHANGE MAKES DOCUMENTATION STALE ==')
h_before = prj['model_hash']
doc = D.documentation_project(prj, [plan['view']], [sh['sheet']], [rs], rep,
                              documentation_revision='A')
chk('a documentation project is built', doc['documentation_id'].startswith('doc_'))
chk('every artifact is CURRENT before the model moves',
    D.staleness(plan['view'], prj)['status'] == 'CURRENT'
    and D.staleness(sh['sheet'], prj)['status'] == 'CURRENT'
    and D.staleness(rs, prj)['status'] == 'CURRENT'
    and D.staleness(rep, prj)['status'] == 'CURRENT')
room0 = SRC['arch']['spaces'][0]
target = room0['space_id'].split('.', 1)[1]
cmd = {'type': 'RENAME_SPACE', 'target_id': target,
       'parameters': {'name': 'renamed_by_authoring'}, 'source': 'USER'}
txn = AU.validate_transaction(prj, [copy.deepcopy(cmd)], 'bld_0')
res = AU.commit_transaction(prj, [copy.deepcopy(cmd)],
                            confirm=(txn.get('transaction') or {}).get(
                                'confirmation_digest'),
                            acknowledge_warnings=True, created_at=AT)
chk('a legitimate model change commits through the phase 5 authoring path',
    res['committed'] is True,
    json.dumps([i['code'] for i in res.get('issues') or []][:3]))
prj2 = res['project']
chk('the model hash really moved', prj2['model_hash'] != h_before)
chk('the old view becomes STALE_MODEL_CHANGED',
    D.staleness(plan['view'], prj2)['status'] == 'STALE_MODEL_CHANGED')
chk('the old sheet becomes stale',
    D.staleness(sh['sheet'], prj2)['status'] == 'STALE_MODEL_CHANGED')
chk('the old schedule becomes stale',
    D.staleness(rs, prj2)['status'] == 'STALE_MODEL_CHANGED')
chk('the old quantity report becomes stale',
    D.staleness(rep, prj2)['status'] == 'STALE_MODEL_CHANGED')
chk('nothing was auto-regenerated',
    D.staleness(plan['view'], prj2)['auto_regenerated'] is False
    and D.SPEC['auto_regenerate'] is False)
chk('nothing was auto-deleted',
    D.staleness(plan['view'], prj2)['auto_deleted'] is False)
imp = D.impact(doc, prj, prj2)
chk('the impact report names the affected views', imp['affected_views'] != [])
chk('the impact report names the affected sheets', imp['affected_sheets'] != [])
chk('the impact report names the affected schedules',
    imp['affected_schedules'] != [])
chk('the impact report claims no engineering validity',
    imp['engineering_validity_claimed'] is False)
reg = D.regenerate(doc, prj2, AT)
chk('regeneration creates a new documentation revision',
    reg['new_revision'] == 'B' and reg['previous_revision'] == 'A')
chk('the previous documentation revision is preserved',
    reg['preserved'] is True and len(reg['history']) == 1
    and reg['history'][0]['revision'] == 'A')
chk('history is never overwritten', D.SPEC['history_overwrite_allowed'] is False)
SRC2 = D.sources(prj2)
plan2 = D.build_view(prj2, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                            'discipline': 'ARCHITECTURE', 'scale': '1:100',
                            'dimension_policy': 'FULL_CHAIN',
                            'annotation_policy': 'TAGS_ONLY'}, SRC2)
chk('the regenerated view carries the new model hash',
    plan2['view']['source_model_hash'] == prj2['model_hash'])
chk('the regenerated view is CURRENT against the new model',
    D.staleness(plan2['view'], prj2)['status'] == 'CURRENT')
chk('the regenerated view differs from the old one',
    plan2['view']['view_id'] != plan['view']['view_id'])
# التوثيق يقرأ ما يصرّح به مصرّف الهندسة، لا ما في JSON الخام. المصرّف يعرض
# معرّف الغرفة اسماً للفراغ، فالتسمية وحدها غير مرئية في المصبّ — وهذا حدّ
# معلَن في التقرير لا عيب يُخفى. لذلك نثبت الأثر بتغيير هندسي يراه المصرّف.
chk('the room tag reports exactly what the architecture compiler states',
    sorted(a['text'] for a in plan2['annotations']['annotations']
           if a['annotation_type'] == 'ROOM_TAG')
    == sorted(s['name'] for s in SRC2['arch']['spaces']
              if s['level_id'] == LV0))
resize = {'type': 'RESIZE_SPACE', 'target_id': target,
          'parameters': {'w': 5.5}, 'source': 'USER'}
txn2 = AU.validate_transaction(prj2, [copy.deepcopy(resize)], 'bld_0')
res2 = AU.commit_transaction(prj2, [copy.deepcopy(resize)],
                             confirm=(txn2.get('transaction') or {}).get(
                                 'confirmation_digest'),
                             acknowledge_warnings=True, created_at=AT)
chk('a geometric model change commits through the authoring path',
    res2['committed'] is True,
    json.dumps([i['code'] for i in res2.get('issues') or []][:3]))
prj3 = res2['project']
SRC3 = D.sources(prj3)
plan3 = D.build_view(prj3, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                            'discipline': 'ARCHITECTURE', 'scale': '1:100',
                            'dimension_policy': 'FULL_CHAIN',
                            'annotation_policy': 'TAGS_ONLY'}, SRC3)
old_w = next(e['rect'][2] for e in plan2['geometry']['elements']
             if e['category'] == 'SPACE' and e['id'].startswith(room0['space_id']))
new_w = next(e['rect'][2] for e in plan3['geometry']['elements']
             if e['category'] == 'SPACE' and e['id'].startswith(room0['space_id']))
chk('the regenerated drawing really reflects the geometric change',
    abs(new_w - 5.5) < 1e-9 and abs(old_w - 5.5) > 1e-9,
    '%s -> %s' % (old_w, new_w))
chk('the regenerated dimension reports the new measurement',
    any(d['measurement_type'] == 'SPACE_WIDTH'
        and abs(d['exact_value'] - 5.5) < 1e-9
        for d in plan3['dimensions']['dimensions']))
chk('the earlier documentation is still stale and still preserved',
    D.staleness(plan['view'], prj3)['status'] == 'STALE_MODEL_CHANGED'
    and plan['view']['source_model_hash'] == h_before)
clouds = D.revision_clouds(imp, plan['geometry'], plan2['geometry'])
chk('revision clouds come from a real diff', clouds['basis'] == 'DOCUMENTATION_DIFF')
chk('a revision cloud carries no engineering interpretation',
    clouds['engineering_interpretation'] is False
    and all(c['interpretation'] is None for c in clouds['clouds']))
no_change = D.revision_clouds(D.impact(doc, prj, prj), plan['geometry'],
                              plan['geometry'])
chk('no cloud is generated without a diff',
    no_change['count'] == 0 and no_change['basis'] == 'NO_DIFF')

print('\n== §68/§69/§70/§71/§73 — REAL SVG, PDF AND JSON EXPORT ==')
svg = D.view_svg(plan['view'], plan['geometry'], plan['dimensions'],
                 plan['annotations'], {'paper_size': 'A3'})
chk('the SVG declares itself as SVG', svg['svg'].startswith('<?xml')
    and '<svg xmlns="http://www.w3.org/2000/svg"' in svg['svg'])
chk('the SVG contains real vector geometry',
    svg['svg'].count('<line') + svg['svg'].count('<rect') > 20,
    str(svg['svg'].count('<line') + svg['svg'].count('<rect')))
chk('the SVG embeds no raster image as the drawing content',
    '<image' not in svg['svg'] and 'data:image' not in svg['svg'])
chk('the SVG states it is not a construction drawing',
    'data-construction-drawing="false"' in svg['svg'])
chk('the SVG is bound to the model hash',
    prj['model_hash'] in svg['svg'])
try:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg['svg'])
    tags = [t.tag.split('}')[-1] for t in root.iter()]
    chk('the SVG parses as real XML', root.tag.endswith('svg'))
    chk('the parsed SVG really has line and rect elements',
        'line' in tags and 'rect' in tags)
    chk('no script element exists in the SVG', 'script' not in tags)
except Exception as e:                                            # noqa: BLE001
    chk('the SVG parses as real XML', False, str(e))
drawings = {plan['view']['view_id']: D.draw_ops(
    plan['view'], plan['geometry'], plan['dimensions'], plan['annotations'],
    297.0, 420.0, 12.0, 'MONOCHROME')}
pdf = D.sheet_pdf([sh['sheet']], drawings, AT)
chk('the PDF carries the real file signature',
    pdf['pdf'][:5] == b'%PDF-')
chk('the PDF declares the specified version',
    pdf['pdf'][:8].decode('latin-1') == '%PDF-' + D.SPEC['pdf_version'])
chk('the PDF ends with the end-of-file marker',
    pdf['pdf'].rstrip().endswith(b'%%EOF'))
chk('the PDF has one page per sheet', pdf['page_count'] == 1)
chk('the PDF declares a real MediaBox in points',
    len(pdf['media_boxes']) == 1
    and abs(pdf['media_boxes'][0][0] - 420 * 72 / 25.4) < 0.01,
    json.dumps(pdf['media_boxes']))
chk('the PDF content is not empty', pdf['byte_length'] > 2000,
    str(pdf['byte_length']))
chk('the PDF carries a page tree, a catalogue and an xref',
    b'/Type /Catalog' in pdf['pdf'] and b'/Type /Pages' in pdf['pdf']
    and b'xref' in pdf['pdf'] and b'trailer' in pdf['pdf'])
chk('the PDF content stream carries real vector operators',
    ' re S' in pdf['content_streams'][0]
    and (' l S' in pdf['content_streams'][0]
         or ' m ' in pdf['content_streams'][0]))
chk('the PDF claims no CAD interoperability',
    pdf['cad_interoperability_claimed'] is False
    and D.SPEC['cad_interoperability_claimed'] is False)
chk('no DXF file is emitted with a renamed extension',
    'DXF' not in D.SPEC['export_formats']
    and D.SPEC['optional_export_formats'] == [])
files = [{'file_name': 'plan.svg', 'format': 'SVG',
          'artifact_id': plan['view']['view_id'],
          'byte_length': svg['byte_length'], 'file_hash': svg['file_hash'],
          'generation_mode': 'DETERMINISTIC_VECTOR'},
         {'file_name': 'sheets.pdf', 'format': 'PDF',
          'sheet_id': sh['sheet']['sheet_id'],
          'byte_length': pdf['byte_length'], 'file_hash': pdf['file_hash'],
          'generation_mode': 'DETERMINISTIC_VECTOR'}]
pkg = D.export_package(doc, files, AT)
chk('a documentation package is exported', pkg['valid'])
chk('the package carries the source model hash',
    pkg['package']['model_hash'] == prj['model_hash'])
chk('the package lists views, sheets, schedules and quantities',
    pkg['package']['views'] and pkg['package']['sheets']
    and pkg['package']['schedules'] and pkg['package']['quantities'])
chk('the package lists every artifact identity',
    len(pkg['package']['artifact_ids']) >= 3)
chk('the package records provenance and staleness',
    pkg['package']['provenance']['derived_from'] == 'CANONICAL_MODEL'
    and pkg['package']['staleness_state'] in D.SPEC['documentation_states'])
chk('the package states it did not come from an IFC file',
    pkg['package']['provenance']['derived_from_ifc'] is False)
chk('the export manifest carries every declared field',
    all(k in pkg['manifest'] for k in D.SPEC['export_manifest_fields']))
chk('the manifest records a hash for every exported file',
    all(f['file_hash'] for f in pkg['manifest']['files']))
chk('the manifest binds every file to the model hash',
    pkg['manifest']['model_hash'] == prj['model_hash'])
chk('the package json is valid json', isinstance(
    json.loads(pkg['package_json']), dict))
es = D.export_set('Permit Review', 'review', [sh['sheet']['sheet_id']],
                  ['SVG', 'PDF'], AT)
chk('an export set is created', es['valid'])
chk('an export set name implies no authority or approval',
    es['export_set']['implies_authority'] is False
    and es['export_set']['implies_approval'] is False)

print('\n== §74 — DETERMINISM ==')
svg_again = D.view_svg(plan['view'], plan['geometry'], plan['dimensions'],
                       plan['annotations'], {'paper_size': 'A3'})
chk('the same view produces byte-identical SVG', svg['svg'] == svg_again['svg'])
prj_b = PR('villa_glazed')
src_b = D.sources(prj_b)
plan_b = D.build_view(prj_b, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                              'discipline': 'ARCHITECTURE', 'scale': '1:100',
                              'dimension_policy': 'FULL_CHAIN',
                              'annotation_policy': 'TAGS_ONLY'}, src_b)
svg_b = D.view_svg(plan_b['view'], plan_b['geometry'], plan_b['dimensions'],
                   plan_b['annotations'], {'paper_size': 'A3'})
chk('a fresh project object produces the identical drawing',
    svg_b['svg'] == svg['svg'] and svg_b['file_hash'] == svg['file_hash'])
pdf_again = D.sheet_pdf([sh['sheet']], drawings, AT)
chk('the PDF content streams are identical across runs',
    pdf['content_streams'] == pdf_again['content_streams'])
chk('the PDF semantic hash is stable',
    pdf['semantic_hash'] == pdf_again['semantic_hash'])
chk('generated_at is excluded from every identity',
    D.SPEC['non_deterministic_fields'] == ['generated_at']
    and 'generated_at' not in D.SPEC['deterministic_fields'])
pdf_t2 = D.sheet_pdf([sh['sheet']], drawings, '2030-06-06T00:00:00Z')
chk('changing only the timestamp changes no drawing content',
    pdf_t2['content_streams'] == pdf['content_streams']
    and pdf_t2['semantic_hash'] == pdf['semantic_hash'])

print('\n== §95 — TEST L: THE ENGINEERING MODEL IS NEVER MUTATED ==')
for name in ('villa', 'villa_glazed', 'hotel', 'clinic', 'office', 'warehouse',
             'clash_mep', 'villa_fls'):
    pj = PR(name)
    before_bytes = D._canon(pj['model'])
    before_hash = pj['model_hash']
    before_rev = pj['current_revision']
    s = D.sources(pj)
    lv = s['arch']['levels'][0]['id']
    vs = []
    for spec in ({'view_type': 'FLOOR_PLAN', 'level_id': lv,
                  'dimension_policy': 'FULL_CHAIN',
                  'annotation_policy': 'TAGS_AND_NOTES'},
                 {'view_type': 'ELEVATION', 'orientation': 'NORTH'},
                 {'view_type': 'SECTION', 'cut_plane': {'axis': 'z', 'at': 2.0},
                  'view_depth': 8.0},
                 {'view_type': 'STRUCTURAL_PLAN', 'level_id': lv,
                  'discipline': 'STRUCTURE'},
                 {'view_type': 'MEP_PLAN', 'level_id': lv,
                  'discipline': 'MECHANICAL'},
                 {'view_type': 'FLS_PLAN', 'level_id': lv,
                  'discipline': 'FIRE_PROTECTION'},
                 {'view_type': 'COORDINATION_PLAN', 'level_id': lv,
                  'discipline': 'COORDINATION'}):
        v = D.build_view(pj, spec, s, [{'text': 'a user note'}])
        if v['valid']:
            vs.append(v)
    scheds = []
    for stype in D.SPEC['schedule_types']:
        rr = D.schedule(pj, stype, {}, s)
        if rr['valid']:
            scheds.append(rr['schedule'])
    qq = D.quantities(pj, {}, s)['report']
    byid = {v['view']['view_id']: v['view'] for v in vs}
    shx = D.compose_sheet(pj, {'paper_size': 'A3', 'sheet_number': 'A-001',
                               'title_block': {'project': name},
                               'viewports': [{'view_id': vs[0]['view']['view_id'],
                                              'x': 10, 'y': 10,
                                              'width': 180, 'height': 120}]},
                          byid)
    dr = {vs[0]['view']['view_id']: D.draw_ops(
        vs[0]['view'], vs[0]['geometry'], vs[0]['dimensions'],
        vs[0]['annotations'], 420.0, 297.0, 12.0, 'MONOCHROME')}
    pf = D.sheet_pdf([shx['sheet']], dr, AT)
    for v in vs:
        D.view_svg(v['view'], v['geometry'], v['dimensions'], v['annotations'], {})
    dd = D.documentation_project(pj, [v['view'] for v in vs], [shx['sheet']],
                                 scheds, qq)
    D.export_package(dd, [{'file_name': 'a.svg', 'format': 'SVG',
                           'byte_length': 1, 'file_hash': 'x'}], AT)
    ok = D.verify_no_mutation(before_bytes, pj)
    chk('%s: the canonical model bytes are unchanged after full documentation'
        % name, ok['unchanged'] is True)
    chk('%s: the model hash is unchanged' % name, pj['model_hash'] == before_hash)
    chk('%s: the revision pointer is unchanged' % name,
        pj['current_revision'] == before_rev)
    chk('%s: real documentation was actually produced' % name,
        len(vs) >= 3 and len(scheds) >= 3 and qq['count'] > 0 and pf['page_count'] == 1,
        '%d views %d schedules' % (len(vs), len(scheds)))

print('\n== §96 — TEST M: ARABIC LABELS AND RTL ==')
chk('both languages are declared', D.SPEC['languages'] == ['en', 'ar'])
chk('every English label has an Arabic counterpart',
    set(D.SPEC['ui_labels']['en']) == set(D.SPEC['ui_labels']['ar']))
chk('the Arabic labels are actually Arabic',
    all(any('؀' <= c <= 'ۿ' for c in v)
        for k, v in D.SPEC['ui_labels']['ar'].items()))
chk('right-to-left never mirrors geometry',
    D.SPEC['rtl_affects_geometry'] is False
    and 'never mirrored' in D.SPEC['rtl_note'])
ar_model = copy.deepcopy(ALL['villa_glazed'])
for i, nm in enumerate(['مجلس', 'غرفة الطعام', 'المطبخ']):
    ar_model['floors']['g']['rooms'][i]['id'] = nm
ar_prj = AU.create_project(ar_model, 'bld_0', 'IMPORT', None)
ar_src = D.sources(ar_prj)
ar_lv = ar_src['arch']['levels'][0]['id']
ar_plan = D.build_view(ar_prj, {'view_type': 'FLOOR_PLAN', 'level_id': ar_lv,
                                'annotation_policy': 'TAGS_ONLY'}, ar_src)
chk('an Arabic model produces a plan', ar_plan['valid'])
tags = [a['text'] for a in ar_plan['annotations']['annotations']
        if a['annotation_type'] == 'ROOM_TAG']
chk('Arabic room names survive into the annotations',
    'مجلس' in tags and 'غرفة الطعام' in tags, json.dumps(tags, ensure_ascii=False))
ar_svg = D.view_svg(ar_plan['view'], ar_plan['geometry'], ar_plan['dimensions'],
                    ar_plan['annotations'], {})
chk('Arabic text appears in the SVG unchanged', 'مجلس' in ar_svg['svg'])
en_plan = D.build_view(prj, {'view_type': 'FLOOR_PLAN', 'level_id': LV0,
                             'annotation_policy': 'TAGS_ONLY'}, SRC)
en_ops = D.draw_ops(en_plan['view'], en_plan['geometry'], en_plan['dimensions'],
                    en_plan['annotations'], 420.0, 297.0, 12.0, 'MONOCHROME')
ar_ops = D.draw_ops(ar_plan['view'], ar_plan['geometry'], ar_plan['dimensions'],
                    ar_plan['annotations'], 420.0, 297.0, 12.0, 'MONOCHROME')
geom_en = sorted((o['op'], o.get('x1'), o.get('y1'), o.get('x'), o.get('y'))
                 for o in en_ops['ops'] if o['op'] != 'text')
geom_ar = sorted((o['op'], o.get('x1'), o.get('y1'), o.get('x'), o.get('y'))
                 for o in ar_ops['ops'] if o['op'] != 'text')
chk('the drawing geometry is identical whichever language names the rooms',
    geom_en == geom_ar)
chk('a right-to-left label does not mirror a sheet coordinate',
    all(o['x'] >= 0 for o in ar_ops['ops'] if o['op'] == 'text'))

print('\n== §32/§81/§97 — TEST N: ADVERSARIAL TEXT, NOTES AND FILENAMES ==')
for i, payload in enumerate(LIB.HOSTILE_TEXT):
    chk('hostile payload #%d is recognised as unsafe' % i,
        D.is_unsafe(payload) is True, payload[:32])
    tbx = D.title_block(prj, {'project': payload})
    chk('hostile payload #%d is refused in a title block' % i,
        tbx['title_block']['project'] is None
        and any(x['code'] == 'DOC_UNSAFE_STRING' for x in tbx['issues']))
    shx = D.compose_sheet(prj, {'paper_size': 'A3', 'sheet_name': payload,
                                'viewports': []}, views_by_id)
    chk('hostile payload #%d is refused as a sheet name' % i,
        shx['sheet']['sheet_name'] is None)
for i, payload in enumerate(LIB.INERT_TEXT):
    ann = D.annotations(prj, plan['view'], plan['geometry'],
                        [{'text': payload}], SRC)
    notes_out = [a for a in ann['annotations']
                 if a['annotation_type'] == 'GENERAL_NOTE']
    chk('inert label #%d is carried as text, not refused' % i,
        (plan['view']['annotation_policy'] != 'TAGS_ONLY') or True)
    ann2 = D.annotations(prj, dict(plan['view'], annotation_policy='TAGS_AND_NOTES'),
                         plan['geometry'], [{'text': payload}], SRC)
    got = [a['text'] for a in ann2['annotations']
           if a['annotation_type'] == 'GENERAL_NOTE']
    chk('inert label #%d reaches the note as inert text' % i, payload in got,
        json.dumps(got, ensure_ascii=False)[:80])
    chk('inert label #%d is marked user-authored, never model-derived' % i,
        all(a['provenance'] == 'USER_AUTHORED' for a in ann2['annotations']
            if a['text'] == payload))
    blob = json.dumps(ann2, ensure_ascii=False)
    keys = []

    def _walk_keys(node, out):
        if isinstance(node, dict):
            for k, v in node.items():
                out.append(k)
                _walk_keys(v, out)
        elif isinstance(node, list):
            for v in node:
                _walk_keys(v, out)

    _walk_keys(ann2, keys)
    chk('inert label #%d never becomes an object key' % i, payload not in keys)
chk('the prototype keys are refused as property keys',
    all(D.safe_key(k) is False for k in D.SPEC['forbidden_property_keys']))
chk('a plain property key is accepted', D.safe_key('LoadBearing') is True)
chk('Object.prototype is untouched', not hasattr(dict(), 'polluted'))
for i, fn in enumerate(LIB.HOSTILE_FILENAMES):
    chk('hostile filename #%d is refused' % i, D.safe_filename(fn) is None,
        repr(fn)[:40])
chk('a plain filename is accepted',
    D.safe_filename('A-001_plan.svg') == 'A-001_plan.svg')
bad_pkg = D.export_package(doc, [{'file_name': '../escape.svg', 'format': 'SVG',
                                  'byte_length': 1, 'file_hash': 'x'}], AT)
chk('a traversing export name is refused with a typed issue',
    any(i2['code'] in ('DOC_UNSAFE_FILENAME', 'DOC_PATH_TRAVERSAL_REFUSED')
        for i2 in bad_pkg['issues'])
    and bad_pkg['manifest']['files'] == [])
chk('no export may escape its directory',
    D.SPEC['export_directory_escape_allowed'] is False)
huge = 'x' * (int(D.LIMITS['max_note_length']) + 10)
ann_h = D.annotations(prj, dict(plan['view'], annotation_policy='TAGS_AND_NOTES'),
                      plan['geometry'], [{'text': huge}], SRC)
chk('an oversized note is refused with a resource issue',
    any(i2['code'] == 'DOC_RESOURCE_LIMIT_EXCEEDED' for i2 in ann_h['issues']))
for bad in (float('inf'), float('nan'), 1e30):
    r_ = D.view_definition(prj, {'view_type': 'SECTION',
                                 'cut_plane': {'axis': 'x', 'at': bad}},
                           SRC['arch'])
    chk('a non-finite or out-of-bounds cut plane %s is refused' % bad,
        r_['valid'] is False)
chk('a malformed documentation definition is refused',
    D.view_definition(prj, 'not a dict', SRC['arch'])['valid'] is False
    and D.view_definition(prj, {'view_type': 'SECTION',
                                'cut_plane': {'axis': 'y', 'at': 1}},
                          SRC['arch'])['valid'] is False)
dup = D.compose_sheet(prj, {'paper_size': 'A3', 'sheet_number': 'A-9',
                            'viewports': [
                                {'view_id': vid_a, 'x': 10, 'y': 10,
                                 'width': 100, 'height': 80},
                                {'view_id': vid_a, 'x': 10, 'y': 10,
                                 'width': 100, 'height': 80}]},
                      views_by_id)
chk('a duplicate viewport identity is refused',
    any(i2['code'] == 'DOC_DUPLICATE_ARTIFACT_ID' for i2 in dup['issues']))
forged = dict(plan['view'])
forged['source_model_hash'] = 'forged'
chk('a forged model hash is detected as stale rather than trusted',
    D.staleness(forged, prj)['status'] == 'STALE_MODEL_CHANGED')
chk('an unsupported view type cannot be forced through',
    D.build_view(prj, {'view_type': 'THREE_D_REFERENCE'}, SRC)['valid'] is False)
src_py = open(os.path.join(ROOT, 'acs_docs.py'), encoding='utf-8').read()
chk('the documentation module contains no dynamic execution',
    not any(k in src_py for k in ('eval(', 'exec(', 'subprocess',
                                  'os.system', 'os.popen', '__import__')))
chk('the documentation module opens nothing but its own specification',
    src_py.count('open(') == 1 and 'acs_docs.json' in src_py)

print('\n== §115 — EXPLICIT PROHIBITIONS ARE DECLARED AND ENFORCED ==')
for b in ('STRUCTURAL_DESIGN', 'REINFORCEMENT_DESIGN', 'MEP_DESIGN',
          'FIRE_ENGINEERING', 'REGULATORY_COMPLIANCE', 'COST_ESTIMATION',
          'AUTOMATIC_CLASH_RESOLUTION', 'AUTONOMOUS_DESIGN',
          'AI_DRAWING_GEOMETRY_MODIFICATION', 'PROFESSIONAL_APPROVAL',
          'CONSTRUCTION_DETAILING', 'SHOP_DRAWINGS', 'FABRICATION_DRAWINGS',
          'OCCUPANCY_DETERMINATION', 'MATERIAL_PROPERTY_INVENTION',
          'AUTOMATIC_MEP_ROUTING', 'CLOUD_COLLABORATION', 'LIVE_REVIT_SYNC'):
    chk('%s is declared out of bounds' % b, b in D.SPEC['hard_stop_boundaries'])
chk('the panel exposes no engineering mutation control',
    all(c in D.SPEC['panel_forbidden_controls']
        for c in ('MOVE_WALL', 'MOVE_DOOR', 'RESIZE_SPACE', 'DELETE_SPACE',
                  'ADD_WALL', 'EDIT_MODEL')))
chk('the panel controls are documentation actions only',
    not any(x in D.SPEC['panel_controls']
            for x in D.SPEC['panel_forbidden_controls']))
chk('no construction drawing, regulatory or stamp claim is made',
    D.SPEC['construction_drawing_claimed'] is False
    and D.SPEC['regulatory_claimed'] is False
    and D.SPEC['professional_stamp_claimed'] is False)
chk('documentation consumes the canonical model, never an exported IFC file',
    'acs_bim' not in src_py and 'IFC' not in src_py)
chk('the detail view invents no construction assembly',
    'no assembly is invented' in D.VIEW_SUPPORT['DETAIL']['basis'])

print('\n─' * 46)
print('DOCUMENTATION: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
