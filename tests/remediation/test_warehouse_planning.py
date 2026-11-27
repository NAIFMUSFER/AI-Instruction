"""Warehouse planning: dock layout, truck court, cited review notes and the planner policy.

Synthetic models and a mocked SDK only; no network and no paid provider call.
    PYTHONPATH=. python tests/remediation/test_warehouse_planning.py
"""
import copy
import json
from pathlib import Path
import shlex
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests' / 'remediation'))
import acs_plan_chunks as PC
import acs_understand as U
import acs_workspace_service as S
import warehouse_planning as WP
from acs_plan_overlap_repair import POSITION_REPAIR_SYSTEM, repair_overlap
from acs_plan_review import PlanWorkspace, _geometry
from acs_plan_scorecard import measure_plan
from acs_warehouse_generation import PLANNING_SYSTEM
from test_audit_backend_provider import provider

BRIEF = ('مستودع توزيع في الرياض على أرض 80×120 م، الارتفاع الصافي 11 م. الاستلام من الجهة الشمالية '
         'فيه 4 أرصفة، ثم تخزين بالتات، ومنطقة تجهيز الشحن، و4 أرصفة صادر من الجهة الشمالية، ومكتب.')


def req(metric, expected, **extra):
    return dict({'id': metric, 'metric': metric, 'expected': expected, 'source': 'requested',
                 'evidence': 'synthetic', 'confirmed': True}, **extra)


def model(site=(80, 120), rooms=None, wall_h=11.0):
    """A U-flow warehouse: dock zones on the north wall, office on the south."""
    rows = rooms or [
        ('receiving', [0, 40, 40, 18]), ('shipping', [40, 40, 40, 18]),
        ('storage', [0, 58, 80, 40]), ('office', [0, 98, 20, 10]), ('packing', [20, 98, 60, 10])]
    return {'meta': {'type': 'warehouse'}, 'site': {'w': site[0], 'd': site[1]},
            'floor_height': wall_h + 1, 'wall_h': wall_h, 'wall_t': 0.3,
            'levels': [{'id': 'L0', 'index': 0, 'template': 'ground'}],
            'floors': {'ground': {'rooms': [
                {'id': rid, 'name': rid, 'role': rid, 'rect': list(rect), 'walls': 'full' if rid == 'office' else 'none'}
                for rid, rect in rows]}}}


def rooms(building):
    return {r.get('id'): r for r in building['floors']['ground']['rooms']}


def codes(notes):
    return [n['code'] for n in notes]


class DockLayout(unittest.TestCase):
    def test_confirmed_total_without_intents_is_split_and_measured_exactly(self):
        out, notes = WP.layout_docks(model(), [req('dock_count', 8)], [])
        r = rooms(out)
        self.assertEqual([(d['edge'], d['count']) for d in r['receiving']['docks']], [('N', 4)])
        self.assertEqual([(d['edge'], d['count']) for d in r['shipping']['docks']], [('N', 4)])
        for room in (r['receiving'], r['shipping']):
            dock = room['docks'][0]
            self.assertEqual((dock['id'], dock['width'], dock['height'], dock['pitch']), ('dock-n', 3.0, 3.0, 4.0))
            first, last = dock['offset'], dock['offset'] + dock['pitch'] * (dock['count'] - 1)
            self.assertGreaterEqual(first - dock['width'] / 2, 0)
            self.assertLessEqual(last + dock['width'] / 2, room['rect'][2])
        self.assertEqual(measure_plan(out)['metrics']['dock_count'], 8)
        self.assertEqual(len(notes), 2)
        self.assertTrue(all(n.startswith('افتراض:') for n in notes))
        self.assertEqual(out['meta']['acs_stage_diagnostics'][-1]['placed'], 8)

    def test_planner_intents_win_and_are_trimmed_or_topped_up_to_the_confirmed_total(self):
        intents = [{'template': 'ground', 'room': 'receiving', 'edge': 'N', 'count': 6},
                   {'template': 'ground', 'room': 'shipping', 'edge': 'N', 'count': 4}]
        out, _ = WP.layout_docks(model(), [req('dock_count', 8)], intents)
        self.assertEqual(measure_plan(out)['metrics']['dock_count'], 8)
        self.assertEqual(rooms(out)['receiving']['docks'][0]['count'], 4)
        out, _ = WP.layout_docks(model(), [req('dock_count', 12)], intents[:1])
        self.assertEqual(measure_plan(out)['metrics']['dock_count'], 12)
        self.assertEqual(rooms(out)['receiving']['docks'][0]['count'], 10)  # capacity of 40 m at 3.66 m
        out, _ = WP.layout_docks(model(), [req('min_dock_count', 3)], intents)
        self.assertEqual(measure_plan(out)['metrics']['dock_count'], 10)  # a minimum never trims
        out, _ = WP.layout_docks(model(), [], intents)
        self.assertEqual(measure_plan(out)['metrics']['dock_count'], 10)  # no requirement: as planned

    def test_intent_on_an_interior_wall_moves_to_the_exterior_wall(self):
        intents = [{'template': 'ground', 'room': 'receiving', 'edge': 'S', 'count': 3}]
        out, _ = WP.layout_docks(model(), [], intents)
        self.assertEqual(rooms(out)['receiving']['docks'][0]['edge'], 'N')

    def test_short_frontage_is_reported_never_squeezed_below_twelve_foot_centres(self):
        out, notes = WP.layout_docks(model(), [req('dock_count', 30)], [])
        docks = [d for r in rooms(out).values() for d in r.get('docks', [])]
        self.assertEqual(sum(d['count'] for d in docks), 20)
        self.assertTrue(all(d['pitch'] >= WP.DOCK_PITCH_MIN for d in docks))
        self.assertTrue(any(n.startswith('تنبيه:') and '30' in n for n in notes))
        advice = WP.check(out, [req('dock_count', 30)])
        self.assertIn('WAREHOUSE_DOCK_FRONTAGE_SHORT', codes(advice))

    def test_a_template_shared_by_two_storeys_gets_no_docks(self):
        b = model()
        b['levels'].append({'id': 'L1', 'index': 1, 'template': 'ground'})
        out, notes = WP.layout_docks(b, [req('dock_count', 8)], [])
        self.assertFalse([r for r in rooms(out).values() if r.get('docks')])
        self.assertTrue(notes and notes[0].startswith('تنبيه:'))

    def test_authored_or_malformed_dock_data_is_never_replaced(self):
        b = model()
        authored = {'id': 'mine', 'edge': 'N', 'offset': 5, 'width': 3, 'height': 3, 'count': 2, 'pitch': 4}
        rooms(b)['receiving']['docks'] = [dict(authored)]
        rooms(b)['shipping']['docks'] = 'not a list'
        rooms(b)['storage'].pop('id')
        out, notes = WP.layout_docks(b, [req('dock_count', 8)], [])
        self.assertEqual(rooms(out)['receiving']['docks'], [authored])
        self.assertEqual(rooms(out)['shipping']['docks'], 'not a list')
        self.assertTrue(any(n.startswith('تنبيه:') for n in notes))

    def test_door_height_stays_below_a_low_wall(self):
        out, _ = WP.layout_docks(model(wall_h=3.0), [req('dock_count', 2)], [])
        self.assertTrue(all(d['height'] <= 2.7 for r in rooms(out).values() for d in r.get('docks', [])))

    def test_exterior_runs_subtract_touching_neighbours(self):
        b = model()
        r = rooms(b)
        others = b['floors']['ground']['rooms']
        self.assertEqual(WP.exterior_runs(r['receiving'], others, 'N'), [(0.0, 40.0)])
        self.assertEqual(WP.exterior_runs(r['receiving'], others, 'E'), [])
        self.assertEqual(WP.exterior_runs(r['storage'], others, 'S'), [])
        self.assertEqual(WP.exterior_runs(r['storage'], others, 'W'), [(0.0, 40.0)])

    def test_planner_dock_intents_survive_the_chunk_only_on_dock_zones(self):
        chunk = {'index': 0, 'zone_ids': ['receiving', 'storage']}
        payload = {'rooms': [
            {'id': 'receiving', 'role': 'receiving', 'rect': [0, 0, 40, 18],
             'docks': [{'edge': 'N', 'count': 4, 'offset': 2}, {'edge': 'X', 'count': 1}, {'edge': 'S', 'count': 99}]},
            {'id': 'storage', 'role': 'storage', 'rect': [0, 18, 40, 40], 'docks': [{'edge': 'N', 'count': 2}]}]}
        got, issues = PC.validate_chunk(chunk, payload)
        self.assertEqual(issues, [])
        self.assertEqual(got[0]['docks'], [{'edge': 'N', 'count': 4}])
        self.assertNotIn('docks', got[1])


class TruckCourt(unittest.TestCase):
    def test_one_shift_keeps_the_court_and_changes_no_size(self):
        docked, _ = WP.layout_docks(model(), [req('dock_count', 8)], [])
        moved = copy.deepcopy(docked)
        for room in moved['floors']['ground']['rooms']:
            room['rect'][1] -= 40  # building pushed against the north boundary
        out, notes = WP.place_for_truck_court(moved, [])
        self.assertEqual(rooms(out)['receiving']['rect'], [0, 35.0, 40, 18])
        for a, b in zip(moved['floors']['ground']['rooms'], out['floors']['ground']['rooms']):
            self.assertEqual(a['rect'][2:], b['rect'][2:])
            self.assertEqual(b['rect'][1] - a['rect'][1], 35.0)
        self.assertEqual(_geometry(out)[0], [])
        self.assertEqual(len(notes), 1)
        self.assertNotIn('WAREHOUSE_TRUCK_COURT_SHALLOW', codes(WP.check(out, [])))

    def test_no_shift_when_the_site_is_the_building_or_no_shift_can_fit(self):
        docked, _ = WP.layout_docks(model(), [req('dock_count', 8)], [])
        for room in docked['floors']['ground']['rooms']:
            room['rect'][1] -= 40
        out, notes = WP.place_for_truck_court(docked, [req('building_width_m', 80)])
        self.assertEqual((out['floors'], notes), (docked['floors'], []))
        tight = copy.deepcopy(docked)
        tight['site']['d'] = 80  # 68 m of building leaves 12 m
        out, notes = WP.place_for_truck_court(tight, [])
        self.assertEqual((out['floors'], notes), (tight['floors'], []))
        self.assertIn('WAREHOUSE_TRUCK_COURT_SHALLOW', codes(WP.check(tight, [])))
        self.assertNotIn('WAREHOUSE_TRUCK_COURT_SHALLOW', codes(WP.check(tight, [req('building_depth_m', 80)])))


class ReviewNotes(unittest.TestCase):
    def test_sound_u_flow_plan_has_no_notes(self):
        out, _ = WP.layout_docks(model(), [req('dock_count', 8)], [])
        self.assertEqual(WP.check(out, [req('dock_count', 8)]), [])

    def test_each_planning_dimension_is_measured_and_cited(self):
        b = model(rooms=[('receiving', [0, 0, 40, 12]), ('storage', [0, 12, 80, 60])], wall_h=5.0)
        out, _ = WP.layout_docks(b, [], [{'template': 'ground', 'room': 'receiving', 'edge': 'N', 'count': 4}])
        rec = rooms(out)['receiving']
        rec['docks'][0]['pitch'] = 3.2
        rooms(out)['storage']['racks'] = [
            {'kind': 'pallet', 'x': 1, 'z': 1, 'w': 20, 'd': 20, 'dir': 'x', 'aisle': 1.8, 'h': 4.8}]
        notes = WP.check(out, [])
        self.assertEqual(set(codes(notes)), {
            'WAREHOUSE_STAGING_SHALLOW', 'WAREHOUSE_TRUCK_COURT_SHALLOW', 'WAREHOUSE_DOCK_SPACING_TIGHT',
            'WAREHOUSE_CLEAR_HEIGHT_LOW', 'WAREHOUSE_RACK_AISLE_NARROW', 'WAREHOUSE_RACK_SPRINKLER_CLEARANCE'})
        for note in notes:
            self.assertEqual(note['severity'], 'advisory')
            self.assertIn(WP.SOURCES[note['source']], note['message'])
            self.assertNotRegex(note['message'], 'مطابق|compliant|معتمد')

    def test_interior_dock_zone_is_flagged(self):
        b = model(rooms=[('storage', [0, 0, 80, 20]), ('qc', [0, 20, 30, 20]), ('receiving', [30, 20, 20, 20]),
                         ('packing', [50, 20, 30, 20]), ('sorting', [0, 40, 80, 20])])
        self.assertIn('WAREHOUSE_DOCK_ZONE_INTERIOR', codes(WP.check(b, [])))
        b['floors']['ground']['rooms'].pop()  # its south wall is now an exterior wall
        self.assertNotIn('WAREHOUSE_DOCK_ZONE_INTERIOR', codes(WP.check(b, [])))

    def test_egress_lower_bound_only_for_a_deep_single_block(self):
        big = model(site=(400, 400), rooms=[('storage', [0, 0, 200, 200])])
        notes = WP.check(big, [])
        self.assertIn('WAREHOUSE_EGRESS_DISTANCE', codes(notes))
        self.assertGreaterEqual(WP.farthest_from_exterior(big['floors']['ground']['rooms']), 95)
        small = model(site=(400, 400), rooms=[('storage', [0, 0, 140, 300])])
        self.assertLess(WP.farthest_from_exterior(small['floors']['ground']['rooms']), 71)
        self.assertNotIn('WAREHOUSE_EGRESS_DISTANCE', codes(WP.check(small, [])))

    def test_not_a_warehouse_or_not_measurable_gives_nothing(self):
        b = model()
        b['meta']['type'] = 'residential'
        self.assertEqual(WP.check(b, [req('dock_count', 8)]), [])
        self.assertEqual(WP.check({'meta': {'type': 'warehouse'}}, []), [])

    def test_review_shows_notes_as_advisories_that_never_block(self):
        requirements = [req('dock_count', 4)]
        b, _ = WP.layout_docks(model(rooms=[('receiving', [0, 0, 40, 12]), ('storage', [0, 12, 80, 60])]),
                               requirements, [])
        ws = PlanWorkspace(verifier=S.existing_geometry_verifier)
        rev = ws.propose(b, brief='synthetic', requirements=requirements, expected_head=None, note='t')
        result = ws.review(rev.id)
        self.assertLessEqual({'WAREHOUSE_STAGING_SHALLOW', 'WAREHOUSE_TRUCK_COURT_SHALLOW'},
                             set(codes(result['advisories'])))
        self.assertFalse([i for i in result['issues'] if i['code'].startswith('WAREHOUSE_')])
        self.assertTrue(result['can_approve'], result['issues'])


def outline_and_chunk(dock_intents=True):
    rows = [('receiving', [0, 40, 40, 18]), ('shipping', [40, 40, 40, 18]),
            ('storage', [0, 58, 80, 40]), ('office', [0, 98, 20, 10])]
    chunk = [{'id': rid, 'role': rid, 'name': rid, 'rect': rect, 'walls': 'none'} for rid, rect in rows]
    if dock_intents:
        chunk[0]['docks'] = [{'edge': 'N', 'count': 4}]
        chunk[1]['docks'] = [{'edge': 'N', 'count': 4}]
    outline = {'site': {'w': 80, 'd': 120}, 'floor_height': 12, 'wall_h': 11, 'wall_t': 0.3,
               'levels': [{'index': 0, 'id': 'L0', 'template': 'ground'}],
               'meta': {'assumptions': ['افتراض: الشحن والاستلام على الواجهة الشمالية (تدفق U).']},
               'zones': [{'id': rid, 'role': rid, 'template': 'ground'} for rid, _ in rows]}
    return [outline, {'rooms': chunk}]


def run_worker(replies, requirements):
    replies, requests = iter(replies), []

    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(type='text', text=json.dumps(next(replies)))],
                stop_reason='end_turn', usage=types.SimpleNamespace(input_tokens=100, output_tokens=100))

    class Messages:
        def __init__(self, calls, fail): pass
        def stream(self, *, model, max_tokens, messages, system=None):
            requests.append({'system': system})
            return Stream()

    with provider(Messages):
        result = S.generate_plan_candidate(BRIEF, requirements, 'A', 6)
    return result, requests


class Pipeline(unittest.TestCase):
    def test_one_request_gives_typed_docked_disclosed_plan_for_two_paid_calls(self):
        result, requests = run_worker(outline_and_chunk(), [req('dock_count', 8)])
        b = result['building']
        self.assertEqual(result['provider_calls'], 2)
        self.assertEqual([r['system'] for r in requests], [PLANNING_SYSTEM, PLANNING_SYSTEM])
        self.assertEqual(b['meta']['type'], 'warehouse')
        self.assertEqual(measure_plan(b)['metrics']['dock_count'], 8)
        self.assertEqual(_geometry(b)[0], [])
        notes = b['meta']['assumptions']
        self.assertEqual(notes[0], 'افتراض: الشحن والاستلام على الواجهة الشمالية (تدفق U).')
        self.assertEqual(sum('أبواب أرصفة' in n for n in notes), 2)
        ws = PlanWorkspace()
        rev = ws.propose(b, brief=BRIEF, requirements=[req('dock_count', 8)], expected_head=None, note='t')
        review = ws.review(rev.id)
        self.assertNotIn('REQUIREMENT_MISMATCH', codes(review['issues']))
        self.assertNotIn('REQUIREMENT_METRIC_NOT_APPLICABLE', codes(review['issues']))

    def test_laid_out_docks_save_review_approve_and_export(self):
        import base64
        import tempfile
        from acs_plan_persisted_commands import execute_persisted_plan_command
        from acs_plan_store import SQLitePlanStore
        from acs_plan_store_port import SQLitePlanStoreAdapter
        project, actor = '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222'
        requirements = [dict(req('dock_count', 8), evidence='4 أرصفة')]
        result, _ = run_worker(outline_and_chunk(), requirements)

        class Runner:
            def run(self, target, kwargs, **controls):
                return {'building': copy.deepcopy(result['building']), 'provider_calls': 2}

        with tempfile.TemporaryDirectory() as directory:
            db = SQLitePlanStore(Path(directory) / 'plans.sqlite3')
            db.create_project(project, owner_id=actor)
            store = SQLitePlanStoreAdapter(db)
            rid = S.generate_and_save(store, project, actor, {
                'action': 'generate', 'job_id': '33333333-3333-4333-8333-333333333333', 'brief': BRIEF,
                'requirements': requirements, 'expected_head': None, 'option': 'A', 'confirmed': True,
                'max_provider_calls': 3}, runner=Runner())
            view = S.view(store, project, actor)
            self.assertTrue(view['authority']['can_approve_concept'])
            self.assertEqual(sum('أبواب أرصفة' in n for n in view['planning_assumptions']), 2)
            approved = execute_persisted_plan_command(
                store, project, {'action': 'approve', 'expected_head': rid, 'confirmed': True,
                                 'acknowledge_concept_only': True},
                actor_id=actor, verifier=S.existing_geometry_verifier)
            self.assertEqual(approved['baseline'], rid)
            for fmt in ('svg', 'gltf', 'ifc'):
                artifact = S.artifact(store, project, actor, {'action': 'artifact', 'revision_id': rid,
                                                              'format': fmt, 'level_index': 0})
                self.assertTrue(base64.b64decode(artifact['data_base64']))

    def test_missing_intents_are_completed_free_from_the_confirmed_total(self):
        result, _ = run_worker(outline_and_chunk(dock_intents=False), [req('dock_count', 6)])
        self.assertEqual(result['provider_calls'], 2)
        self.assertEqual(measure_plan(result['building'])['metrics']['dock_count'], 6)

    def test_position_repair_sends_its_own_compact_policy(self):
        b = model()
        b['floors']['ground']['rooms'][1]['rect'][:2] = [30, 40]
        seen = {}

        def reply(*args, **kwargs):
            seen.update(kwargs)
            rs = rooms(model())
            return json.dumps({'positions': [{'template': 'ground', 'id': k, 'x': v['rect'][0], 'z': v['rect'][1]}
                                             for k, v in rs.items()]})

        with patch('acs_plan_overlap_repair.place_nonoverlapping', return_value=None), \
                patch.object(U, 'call_llm', side_effect=reply):
            fixed = repair_overlap(b, BRIEF, {'used': 2, 'limit': 6})
        self.assertEqual(_geometry(fixed)[0], [])
        self.assertEqual(seen['system_override'], POSITION_REPAIR_SYSTEM)
        self.assertLess(len(POSITION_REPAIR_SYSTEM) * 20, len(U.system_prompt('warehouse')))


class Policy(unittest.TestCase):
    def test_policy_keeps_the_measured_contract_and_a_token_budget(self):
        for phrase in ('non-overlapping', 'Do not add an envelope', '"docks":[{"edge":"N|S|E|W","count":n}]',
                       '35 m', '3.66 m', '16-20 m', 'meta.assumptions', 'clear height'):
            self.assertIn(phrase, PLANNING_SYSTEM)
        # Every character is paid on each outline and plan_chunk call.
        self.assertLessEqual(len(PLANNING_SYSTEM), 2600)

    def test_legacy_warehouse_defaults_follow_the_research(self):
        legacy = U.system_prompt('warehouse')
        for wrong in ('عرض 3.5–3.7 م', 'ارتفاع باب 4.0–4.5 م', 'مساحة مناورة أمامه ≥ 12 م',
                      '"width":3.6,"height":4.2', '≥ 4 مخارج طوارئ', 'التزم بها حرفياً', 'أبعاد قياسية إلزامية',
                      'سلامة وأمن (إلزامي)', 'لا تقل عن 6'):
            self.assertNotIn(wrong, legacy)
        for right in ('2.7–3.0 م عرضًا', '≥ 35 م داخل الأرض', '0.46 م'):
            self.assertIn(right, legacy)

    def test_the_image_ships_the_module(self):
        sources = [w for line in (ROOT / 'Dockerfile').read_text().splitlines()
                   for w in (shlex.split(line, comments=True) or [''])[1:-1]
                   if line.startswith('COPY')]
        self.assertIn('warehouse_planning.py', sources)


if __name__ == '__main__':
    unittest.main()
