"""Phase 2: every floor follows its own confirmed program, close to its target sizes.

The owner's brief (fixtures/brief_reader) asks for three different flats: a
3-bedroom ground flat with four bathrooms and a majlis, a 4-bedroom first
floor and a second floor with two bedrooms, an office and a terrace, with
target sizes, a west-placed block, 2.7 x 5.2 m stalls and one stair and lift
core. Before phase 2 the planner repeated one floor template and nothing
checked sizes.

Offline throughout: the model is stubbed (no key, no network). Covered: the
per-floor manifest and core, the program reaching every stage, per-floor
requirement metrics and target sizes in the review (a passing hand-drawn
model and failing edits of it), the plot rules (stall, footprint position,
parking floor), contradicting option rows, the fallback, old revisions and
the prompt-size budget.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests' / 'remediation'))
import acs_brief_reader as B
import acs_floor_program as F
import acs_plot_rules as P
import acs_residential_generation as G
import acs_understand as U
import acs_workspace_service as S
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_provider_budget import consume
from acs_workspace_progress import planning_system
from floor_program_fixture import owner_model, owner_variant

FIXTURES = ROOT / 'tests' / 'remediation' / 'fixtures' / 'brief_reader'
BRIEF = (FIXTURES / 'owner_brief.txt').read_text(encoding='utf-8')
PROJECT = '11111111-1111-4111-8111-111111111111'
ACTOR = '22222222-2222-4222-8222-222222222222'
PLOT = {'streets': ['N'], 'parking': {'placement': 'front_setback'}, 'landing_entries': True}


def program():
    return B.validate_program(json.loads((FIXTURES / 'owner_program.json').read_text(encoding='utf-8')))


def base_rows():
    """What step 01 confirms from the owner's card (site, block, floors, flats)."""
    return [{'id': m, 'metric': m, 'expected': v, 'confirmed': True, 'source': 'inferred', 'source_id': 'brief:form',
             'evidence': m + ': ' + str(v)}
            for m, v in (('site_width_m', 20), ('site_depth_m', 25), ('level_count', 3), ('unit_count', 3),
                         ('building_width_m', 13), ('building_depth_m', 16))]


def rows():
    return base_rows() + F.requirement_rows(program())


def rules(prog=None, plot=None):
    return P.resolve(plot or PLOT, BRIEF, rows(), 'A', program=prog or program())


def review(model, requirements=None, prog=None, plot_rules=None):
    model = copy.deepcopy(model)
    P.stamp(model, plot_rules or rules())
    B.stamp(model, prog or program())
    ws = PlanLockWorkspace(existing_geometry_verifier)
    rev = ws.propose(model, brief=BRIEF, requirements=rows() if requirements is None else requirements,
                     expected_head=None, note='floor program')
    return ws.review(rev.id)


def room(model, template, rid):
    return next(r for r in model['floors'][template]['rooms'] if r['id'] == rid)


# ── the planner's manifest ───────────────────────────────────────────────────
class Manifest(unittest.TestCase):
    def setUp(self):
        self.manifest = F.manifest(program(), BRIEF, rows(), rules())

    def test_three_distinct_templates_with_each_floors_rooms(self):
        m = self.manifest
        self.assertEqual([l['template'] for l in m['envelope']['levels']], ['level_0', 'level_1', 'level_2'])
        def counts(template):
            out = {}
            for z in m['zones']:
                if z['template'] == template and z['role'] in F.COUNTED_ROLES:
                    out[z['role']] = out.get(z['role'], 0) + 1
            return out
        self.assertEqual(counts('level_0'), {'majlis': 1, 'bathroom': 4, 'living': 1, 'dining': 1, 'kitchen': 1,
                                             'pantry': 1, 'bedroom': 3, 'laundry': 1})
        # The brief states three bathrooms on the first floor and names two: the third is planned unnamed.
        self.assertEqual(counts('level_1'), {'majlis': 1, 'bathroom': 3, 'living': 1, 'bedroom': 4, 'kitchen': 1,
                                             'pantry': 1, 'laundry': 1})
        self.assertIn('حمام إضافي', [z['name'] for z in m['zones'] if z['template'] == 'level_1'])
        self.assertEqual(counts('level_2'), {'terrace': 1, 'living': 1, 'kitchen': 1, 'bedroom': 2, 'dressing': 1,
                                             'bathroom': 2, 'office': 1})
        majlis = next(z for z in m['zones'] if z['id'] == 'level_0_majlis_1')
        self.assertEqual((majlis['name'], majlis['target_m'], majlis['unit_id']), ('مجلس الضيوف', [4, 4.5], 'apartment_1'))
        kids = [z for z in m['zones'] if z['template'] == 'level_0' and z['role'] == 'bedroom' and z.get('approx')]
        self.assertEqual([z['name'] for z in kids], ['غرفة نوم للأبناء 1', 'غرفة نوم للأبناء 2'])
        suite = next(z for z in m['zones'] if z['id'] == 'level_2_bedroom_1')
        self.assertTrue(suite['ensuite'])
        # The ground floor has the building lobby; upper floors a landing and the flat's own foyer.
        self.assertEqual([z['role'] for z in m['zones'] if z['template'] == 'level_0' and not z.get('unit_id')],
                         ['entrance', 'stairs', 'elevator'])
        self.assertEqual([z['name'] for z in m['zones'] if z['template'] == 'level_1' and z['role'] in ('lobby', 'entrance')],
                         ['بسطة الدرج', 'مدخل الشقة'])

    def test_the_core_is_planned_once_at_the_stated_corner_of_the_west_block(self):
        m = self.manifest
        cores = {chunk['template']: {r['role']: r['rect'] for r in rooms} for chunk, rooms, _ in m['results']}
        self.assertEqual(set(cores), {'level_0', 'level_1', 'level_2'})
        self.assertEqual(len({json.dumps(c, sort_keys=True) for c in cores.values()}), 1, 'same rectangles on every floor')
        self.assertEqual(cores['level_0'], {'stairs': [1.5, 5.5, 2.6, 5.0], 'elevator': [4.1, 8.3, 2.0, 2.2]})
        planned = {r['id'] for _, rooms, _ in m['results'] for r in rooms}
        self.assertFalse(planned & {z['id'] for z in m['pending']}, 'pre-placed zones are not asked again')
        self.assertEqual(len(m['pending']) + len(planned), len(m['zones']))

    def test_equal_floor_programs_share_a_template_and_villas_keep_their_planner(self):
        prog = program()
        prog['levels'][2] = copy.deepcopy(prog['levels'][1])
        m = F.manifest(prog, BRIEF, base_rows() + F.requirement_rows(prog), rules(prog))
        self.assertEqual([l['template'] for l in m['envelope']['levels']], ['level_0', 'level_1', 'level_1'])
        villa = program(); villa['building_type'] = 'villa'
        self.assertIsNone(F.manifest(villa, BRIEF, rows(), rules()))
        self.assertIsNone(F.manifest(program(), BRIEF, [r for r in rows() if r['metric'] != 'level_count'], rules()),
                          'no confirmed floor count: the outline stage plans it')


# ── offline generation: the model is stubbed ────────────────────────────────
class Provider:
    """Answers from the hand-drawn owner model: plan chunks, one repair, openings.

    Its plan-chunk ids are not the owner model's ids, so its openings answers
    need the repair to put the model's rooms in place. The free size fit would
    grow the short majlis back without that repair, so it is held off here
    (free_fit); FreeSizeFit below runs the same chunks with it on."""
    free_fit = False

    def __init__(self):
        self.model, self.calls = owner_model(), []
        self.rooms = {(t, r['name']): r for t, f in self.model['floors'].items() for r in f['rooms']}

    def __call__(self, text, **kw):
        stage = kw['stage']
        self.calls.append((stage, text, kw.get('system_override') or planning_system(stage)))
        consume()
        if stage == 'plan_chunk':
            ask = json.loads(text.split('منطقة):\n', 1)[1].split('\n\n', 1)[0])
            out = []
            for z in ask:
                rect = list(self.rooms[(z['template'], z['name'])]['rect'])
                if z['id'] == 'level_0_majlis_1':
                    rect[3] = round(rect[3] * 0.7, 2)   # 30% too small: the repair corrects it
                out.append({'id': z['id'], 'rect': rect, 'role': z['role'], 'name': z['name'],
                            **{k: z[k] for k in ('unit_id', 'core_id') if k in z}})
            return json.dumps({'rooms': out}, ensure_ascii=False)
        if stage == 'repair':
            keep = ('id', 'name', 'role', 'rect', 'walls', 'unit_id', 'core_id')
            return json.dumps({'floors': {t: {'rooms': [{k: r[k] for k in keep if k in r} for r in f['rooms']]}
                                          for t, f in self.model['floors'].items()}}, ensure_ascii=False)
        if stage == 'detail':
            context = json.loads(text)
            rooms = {r['id']: r for r in self.model['floors'][context['target_template']]['rooms']}
            return json.dumps({'rooms': [{'id': i, **{k: rooms[i][k] for k in ('doors', 'windows', 'points')}}
                                         for i in context['requested_ids']]}, ensure_ascii=False)
        raise AssertionError('unexpected stage ' + stage)

    def stage(self, name):
        return [c for c in self.calls if c[0] == name]


def generate(provider, budget=12, prog=None, requirements=None, plot=PLOT):
    fit = G._size_candidates if getattr(provider, 'free_fit', True) else (lambda *a, **k: [])
    with patch.object(U, 'call_llm', side_effect=provider), patch.object(G, '_size_candidates', fit):
        return S.generate_plan_candidate(BRIEF, requirements or rows(), 'C', budget, plot=plot, program=prog or program())


def asked(text):
    return json.loads(text.split('منطقة):\n', 1)[1].split('\n\n', 1)[0])


class Generation(unittest.TestCase):
    def setUp(self):
        self.provider = Provider()
        self.out = generate(self.provider)

    def test_no_outline_call_one_plan_call_per_floor_one_repair_and_openings_per_floor(self):
        self.assertEqual([c[0] for c in self.provider.calls],
                         ['plan_chunk'] * 3 + ['repair'] + ['detail'] * 3)
        self.assertEqual(self.out['provider_calls'], 7)

    def test_three_distinct_floor_prompts_with_the_right_rooms_and_sizes(self):
        chunks = [asked(text) for _, text, _ in self.provider.stage('plan_chunk')]
        self.assertEqual([{z['template'] for z in ask} for ask in chunks], [{'level_0'}, {'level_1'}, {'level_2'}])
        names = [[z['name'] for z in ask] for ask in chunks]
        self.assertIn('مجلس الضيوف', names[0]); self.assertIn('حمام المسبح', names[0])
        self.assertIn('جناح الوالدين', names[1]); self.assertNotIn('مجلس الضيوف', names[1])
        self.assertIn('تراس شمالي', names[2]); self.assertIn('مكتب', names[2]); self.assertNotIn('مجلس أمامي', names[2])
        self.assertEqual(sum('target_m' in z for z in chunks[0]), 10)
        self.assertEqual(next(z for z in chunks[1] if z['name'] == 'مطبخ مغلق')['target_m'], [3.3, 3.8])
        for _, text, system in self.provider.stage('plan_chunk'):
            self.assertIn('برنامج الأدوار المؤكد', text)
            self.assertNotIn('برنامج المالك المؤكد', text, 'the per-floor rooms travel with their zones only')
            self.assertNotIn('room_count_by_level', text, 'per-floor rows stay out of the prompt')
            self.assertIn('CONFIRMED FLOOR PROGRAM', system)
            self.assertIn('المساحة القابلة للبناء: x من 1.5 إلى 14.5 وz من 5.5 إلى 21.5 (13 × 16 م)', text)

    def test_the_core_is_fixed_and_aligned_on_every_floor(self):
        for _, text, _ in self.provider.stage('plan_chunk'):
            context = json.loads(text.split('سياق التخطيط المشترك:\n', 1)[1].split('\n\n', 1)[0])
            fixed = {r['id']: r['rect'] for r in context['planned_rooms'] if r['role'] in ('stairs', 'elevator')}
            self.assertEqual(len(fixed), 6, 'stairs and lift of all three floors are planned before any chunk')
            self.assertEqual({json.dumps(v) for k, v in fixed.items() if k.endswith('stairs')}, {'[1.5, 5.5, 2.6, 5.0]'})
        building = self.out['building']
        cores = [{r['role']: r['rect'] for r in building['floors'][t]['rooms'] if r['role'] in ('stairs', 'elevator')}
                 for t in ('level_0', 'level_1', 'level_2')]
        self.assertTrue(cores[0] == cores[1] == cores[2])

    def test_the_program_reaches_the_repair_and_every_openings_call(self):
        _, text, system = self.provider.stage('repair')[0]
        context = json.loads(text)
        self.assertEqual(set(context['program']), {'level_0', 'level_1', 'level_2'})
        self.assertEqual(context['program']['level_1']['floor'], 'الدور الأول')
        # The stubbed plan chunks leave the fixture's corridor fill out, so one
        # second-floor bedroom stands over a void of the first floor. A covered
        # porch under it, entered from a first-floor room, carries it for free
        # (a porch is no program room, so the confirmed counts are unchanged);
        # the repair only carries the majlis size.
        self.assertEqual([f['code'] for f in context['findings']], ['PROGRAM_ROOM_SIZE_OFF'])
        self.assertEqual(context['findings'][0]['room_ref'], ['level_0', 'level_0_majlis_1'])
        porches = [r for r in context['building']['floors']['level_1']['rooms'] if r['role'] == 'porch']
        self.assertEqual([(p['name'], p['walls'], p['covered']) for p in porches], [('شرفة مغطاة', 'none', True)])
        self.assertEqual(G._unsupported_findings(context['building']), [])
        self.assertNotIn('UNSUPPORTED_UPPER_ROOM: that upper room', system)
        self.assertIn('context.program holds each floor template', system)
        for _, text, system in self.provider.stage('detail'):
            context = json.loads(text)
            self.assertEqual(context['program'], F.floor_programs(program(), self.out['building'])[context['target_template']])
            self.assertIn('ensuite=true gets the only door', system)
        floors = [json.loads(t)['program']['floor'] for _, t, _ in self.provider.stage('detail')]
        self.assertEqual(floors, ['الدور الأرضي', 'الدور الأول', 'الدور الثاني'])

    def test_the_generated_building_follows_the_program_and_can_be_approved(self):
        result = review(self.out['building'])
        self.assertTrue(result['can_approve'], result['issues'][:3])
        self.assertEqual(result['scopes']['brief_program'], 'PASS')
        self.assertEqual(result['scopes']['program'], 'PASS')

    def test_the_program_persists_with_the_saved_revision(self):
        provider = Provider()

        class InProcess:
            def run(self, target, kwargs, **controls):
                with patch.object(U, 'call_llm', side_effect=provider), \
                        patch.object(G, '_size_candidates', lambda *a, **k: []):
                    return S.generate_plan_candidate(**kwargs)
        command = {'action': 'generate', 'job_id': '77777777-7777-4777-8777-777777777777', 'brief': BRIEF,
                   'requirements': rows(), 'expected_head': None, 'option': 'C', 'confirmed': True,
                   'max_provider_calls': 12, 'plot': PLOT,
                   'program': {k: v for k, v in program().items() if k not in ('checks', 'cannot_do')}}
        with tempfile.TemporaryDirectory() as tmp:
            db = SQLitePlanStore(Path(tmp) / 'plans.sqlite3'); db.create_project(PROJECT, owner_id=ACTOR)
            store = SQLitePlanStoreAdapter(db)
            rid = S.generate_and_save(store, PROJECT, ACTOR, command, runner=InProcess())
            view = S.view(store, PROJECT, ACTOR)
        self.assertEqual(view['revision_id'], rid)
        self.assertEqual(view['brief_program'], program())
        self.assertEqual([c[0] for c in provider.calls], ['plan_chunk'] * 3 + ['repair'] + ['detail'] * 3)
        blocking = [f for f in view['review_findings'] if f.get('severity') != 'advisory']
        self.assertEqual(blocking, [])


class FreeSizeFit(unittest.TestCase):
    """The plan chunk leaves the majlis 30% short with free floor beside it:
    the layout stage grows it back for free, so no repair call is spent."""

    class Chunks(Provider):
        free_fit = True

        def __call__(self, text, **kw):
            if kw['stage'] == 'detail':
                self.calls.append(('detail', text, None))
                self.detail = json.loads(text)
                raise StopIteration('openings are covered by Generation')
            return super().__call__(text, **kw)

    def test_the_short_majlis_is_fitted_before_any_paid_repair(self):
        provider = self.Chunks()
        with self.assertRaises(Exception):
            generate(provider)
        self.assertEqual([c[0] for c in provider.calls], ['plan_chunk'] * 3 + ['detail'])
        majlis = next(r for r in provider.detail['all_rooms'] if r['id'] == 'level_0_majlis_1')
        self.assertEqual(majlis['rect'], provider.rooms[('level_0', 'مجلس الضيوف')]['rect'])


class KeptDraft(unittest.TestCase):
    """Live job 38f36e00: every floor had its openings, one corrective call
    was spent, and the cap of 8 ran out before the next. The job failed and
    nothing was saved. A confirmed floor program has no fallback that fits it,
    so the paid plan is now kept as a draft that the review blocks."""

    class DoorlessBedroom(Provider):
        def __call__(self, text, **kw):
            out = super().__call__(text, **kw)
            if kw['stage'] == 'detail':
                context = json.loads(text)
                if context['target_template'] == 'level_1':
                    target = next(r['id'] for r in context['all_rooms'] if r['role'] == 'bedroom')
                    self.doorless = target
                    value = json.loads(out)
                    for row in value['rooms']:
                        if row['id'] == target:
                            row['doors'] = []   # never corrected by this stub
                    out = json.dumps(value, ensure_ascii=False)
            return out

    def test_budget_out_during_correction_keeps_the_detailed_plan(self):
        provider = self.DoorlessBedroom()
        out = generate(provider, budget=7)
        self.assertEqual([c[0] for c in provider.calls], ['plan_chunk'] * 3 + ['repair'] + ['detail'] * 3)
        rooms = {r['id']: r for f in out['building']['floors'].values() for r in f['rooms']}
        self.assertEqual(rooms[provider.doorless]['doors'], [])
        self.assertTrue(all('doors' in r for r in rooms.values()), 'every room has had its openings call')
        result = review(out['building'])
        self.assertFalse(result['can_approve'], 'what remains blocks approval in the review')

    def test_corrections_still_run_while_calls_remain(self):
        provider = self.DoorlessBedroom()
        out = generate(provider, budget=12)
        self.assertGreater([c[0] for c in provider.calls].count('detail'), 3, 'the corrective pass still runs')
        self.assertFalse(review(out['building'])['can_approve'])

    def test_other_plans_keep_their_previous_behaviour(self):
        import acs_residential_generation as G
        import inspect
        self.assertFalse(inspect.signature(G.detail).parameters['keep_unresolved'].default)


# ── the review: per-floor metrics and target sizes ──────────────────────────
class Review(unittest.TestCase):
    def test_the_owner_model_passes_every_check(self):
        result = review(owner_model())
        self.assertTrue(result['can_approve'], result['issues'])
        self.assertEqual({k: v for k, v in result['scopes'].items() if v != 'NOT_VERIFIED'},
                         {'rectangular_geometry': 'PASS', 'program': 'PASS', 'topology': 'PASS',
                          'vertical_circulation': 'PASS', 'plot_rules': 'PASS', 'brief_program': 'PASS'})
        self.assertFalse([a for a in result['advisories'] if a['code'].startswith('PROGRAM_')])

    def test_per_floor_rows_are_measured(self):
        from acs_plan_review import _program
        model = owner_model()
        self.assertEqual(F.level_role_count(model, 1, 'bedroom'), 4)
        self.assertEqual(F.level_role_count(model, 2, 'office'), 1)
        self.assertEqual([F.level_ensuite_count(model, i) for i in range(3)], [1, 1, 1])
        self.assertIsNone(F.level_role_count(model, 3, 'bedroom'))
        bare = copy.deepcopy(model)
        for f in bare['floors'].values():
            for r in f['rooms']:
                r['doors'] = []
        self.assertIsNone(F.level_ensuite_count(bare, 0), 'unknown before openings, never a guessed zero')
        P.stamp(model, rules())   # with plot rules the confirmed block size is the rooms' footprint
        self.assertEqual(_program(model, BRIEF, rows()), [])
        bad = [dict(r, expected=r['expected'] + 1) if r['id'] == 'program-l2-bedroom' else r for r in rows()]
        self.assertEqual([(i['code'], i['requirement_id']) for i in _program(model, BRIEF, bad)],
                         [('REQUIREMENT_MISMATCH', 'program-l2-bedroom')])

    def test_wrong_bedrooms_on_the_first_floor_block_approval(self):
        def drop(model):
            extra = room(model, 'level_1', 'level_1_extra_2')
            extra.update(role='living', name='صالة جلوس')
        result = review(owner_variant(drop))
        self.assertFalse(result['can_approve'])
        mismatched = [i['requirement_id'] for i in result['issues'] if i['code'] == 'REQUIREMENT_MISMATCH']
        self.assertEqual(sorted(mismatched), ['program-l1-bedroom', 'program-l1-living'])
        # Without the per-floor rows (an API caller), the program check says it in Arabic.
        result = review(owner_variant(drop), requirements=base_rows())
        floor = [i for i in result['issues'] if i['code'] == 'PROGRAM_LEVEL_ROOMS']
        self.assertEqual(len(floor), 2)
        self.assertIn('الدور الأول: غرف النوم في المخطط 3 والبرنامج المؤكد 4', ' '.join(i['message'] for i in floor))
        self.assertEqual(result['scopes']['brief_program'], 'FAIL')

    def test_a_majlis_forty_percent_too_large_blocks_with_an_arabic_message(self):
        model = owner_model()
        # The drawn 4 x 4.5 m majlis against a target 40% smaller: the review measures each room.
        prog = program()
        majlis = prog['levels'][0]['units'][0]['rooms'][0]
        self.assertEqual((majlis['name'], majlis['width_m'], majlis['depth_m']), ('مجلس الضيوف', 4, 4.5))
        majlis['width_m'], majlis['depth_m'] = 4, round(4.5 / 1.4, 4)   # the drawn 18 m² is now 40% over target
        result = review(model, prog=prog)
        off = [i for i in result['issues'] if i['code'] == 'PROGRAM_ROOM_SIZE_OFF']
        self.assertEqual(len(off), 1)
        self.assertEqual(off[0]['room_ref'], ['level_0', 'level_0_majlis'])
        self.assertIn('«مجلس الضيوف» في الدور الأرضي: مساحته 18 م²', off[0]['message'])
        self.assertIn('أكبر بـ40٪، والمسموح ±20٪', off[0]['message'])
        self.assertFalse(result['can_approve'])

    def test_a_drawn_majlis_forty_percent_over_its_target_is_blocking(self):
        def grow(model):
            # Widen the majlis into the guest WC column: 5.6 x 4.5 = 25.2 m² (+40%).
            majlis = room(model, 'level_0', 'level_0_majlis')
            majlis['rect'][2] = 5.6
            for rid in ('level_0_guest_wc', 'level_0_pool_bath'):
                r = room(model, 'level_0', rid)
                r['rect'] = [r['rect'][0] + 1.6, r['rect'][1], r['rect'][2] - 1.6, r['rect'][3]]
                for o in r['doors'] + r['windows']:
                    if o['edge'] in ('N', 'S'):
                        o['offset'] = round(min(o['offset'], r['rect'][2] - 0.5), 4)
        result = review(owner_variant(grow))
        off = [i for i in result['issues'] if i['code'] == 'PROGRAM_ROOM_SIZE_OFF']
        self.assertTrue(any(i['room_ref'] == ['level_0', 'level_0_majlis'] and 'أكبر بـ40٪' in i['message'] for i in off), off)

    def test_identical_floors_are_refused(self):
        def same(model):
            model['levels'][2]['template'] = 'level_1'
            del model['floors']['level_2']
        result = review(owner_variant(same))
        self.assertFalse(result['can_approve'])
        identical = [i for i in result['issues'] if i['code'] == 'PROGRAM_IDENTICAL_FLOORS']
        self.assertEqual(len(identical), 1)
        self.assertIn('الدور الأول والدور الثاني مرسومان بتوزيع واحد', identical[0]['message'])
        self.assertIn('program-l2-office', [i.get('requirement_id') for i in result['issues']])

    def test_tolerances_exact_and_approximate(self):
        prog = program()
        level = prog['levels'][0]
        level['units'][0]['rooms'] = [r for r in level['units'][0]['rooms'] if r['role'] != 'bedroom' or r['ensuite']]
        model = owner_model()
        cases = ((1.05, []), (1.15, ['PROGRAM_ROOM_SIZE_NEAR']), (1.25, ['PROGRAM_ROOM_SIZE_OFF']))
        for factor, expected in cases:
            target = room(model, 'level_0', 'level_0_master')
            want = 15.2 * factor
            target_rect = [target['rect'][0], target['rect'][1], 4.0, round(want / 4.0, 4)]
            probe = {'role': 'bedroom', 'name': 'غرفة النوم الرئيسية', 'rect': target_rect}
            matches = F.size_matches(level, [probe])
            dev = F._deviation(*matches[0])
            soft, hard = F.TOLERANCE[False]
            got = [] if abs(dev) <= soft + 1e-9 else ['PROGRAM_ROOM_SIZE_NEAR' if abs(dev) <= hard + 1e-9 else 'PROGRAM_ROOM_SIZE_OFF']
            self.assertEqual(got, expected, factor)
        self.assertEqual(F.TOLERANCE[True], (0.15, 0.25), '«نحو/تقريبًا» states a wider tolerance')

    def test_old_revisions_review_as_before(self):
        model = owner_model()
        P.stamp(model, rules())
        ws = PlanLockWorkspace(existing_geometry_verifier)
        rev = ws.propose(model, brief=BRIEF, requirements=base_rows(), expected_head=None, note='no program')
        result = ws.review(rev.id)
        self.assertNotIn('brief_program', result['scopes'])
        self.assertFalse([i for i in result['issues'] if i['code'].startswith('PROGRAM_')])

    def test_every_finding_code_has_an_arabic_name_in_the_page(self):
        import re
        source = (ROOT / 'acs_floor_program.py').read_text(encoding='utf-8')
        page = (ROOT / 'public' / 'app' / 'core' / 'floor-program.mjs').read_text(encoding='utf-8')
        for code in sorted(set(re.findall(r"'(PROGRAM_[A-Z_]+)'", source))):
            self.assertIn(code + ':', page, code)


# ── option rows that contradict an uneven program are refused ───────────────
class Contradictions(unittest.TestCase):
    def command(self, requirements):
        return {'action': 'generate', 'job_id': '77777777-7777-4777-8777-777777777777', 'brief': BRIEF,
                'requirements': requirements, 'expected_head': None, 'option': 'B', 'confirmed': True,
                'max_provider_calls': 12, 'plot': PLOT,
                'program': {k: v for k, v in program().items() if k not in ('checks', 'cannot_do')}}

    def test_uniform_per_flat_rows_from_an_old_option_card_are_refused_before_any_call(self):
        old_card = base_rows() + [
            {'id': 'option-B-room_count-majlis', 'metric': 'room_count', 'role': 'majlis', 'expected': 0,
             'source': 'inferred', 'evidence': 'إجمالي المجالس: 0', 'confirmed': True},
            {'id': 'option-B-room_count_per_unit-bedroom', 'metric': 'room_count_per_unit', 'role': 'bedroom',
             'expected': 3, 'source': 'inferred', 'evidence': 'غرف النوم في كل شقة: 3', 'confirmed': True}]
        with self.assertRaises(PlanError) as caught:
            S.generation_command(self.command(old_card))
        self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_CONFLICT')
        self.assertIn('إجمالي المجالس في المتطلبات 0 والبرنامج المؤكد 2', str(caught.exception))

    def test_per_floor_rows_must_equal_the_program(self):
        S.generation_command(self.command(rows()))
        wrong = [dict(r, expected=3) if r['id'] == 'program-l1-bedroom' else r for r in rows()]
        with self.assertRaises(PlanError) as caught:
            S.generation_command(self.command(wrong))
        self.assertIn('غرف النوم في الدور الأول: المتطلب 3 والبرنامج المؤكد 4', str(caught.exception))


# ── plot rules from the program ──────────────────────────────────────────────
class PlotRules(unittest.TestCase):
    def test_stall_size_from_the_program_and_the_default_without_it(self):
        r = rules()
        self.assertEqual(r['parking']['stall_m'], [2.7, 5.2])
        self.assertEqual(r['parking']['depth_m'], 5.2)
        self.assertEqual((r['parking']['required'], r['parking']['required_source']), (2, 'user'))
        self.assertIn('موقف 2.7 × 5.2 م من وصفك', ' '.join(r['assumptions']))
        stalls = P.stalls(owner_model(), r)
        self.assertTrue(stalls and all(s[2:] == [2.7, 5.2] for s in stalls))
        plain = P.resolve(PLOT, BRIEF, rows(), 'A')
        self.assertEqual(plain['parking']['stall_m'], [2.5, 5.5])
        legacy = dict(r, parking={k: v for k, v in r['parking'].items() if k != 'stall_m'})
        self.assertTrue(all(s[2:] == [2.5, 5.5] for s in P.stalls(owner_model(), legacy)), 'old revisions: the default')

    def test_two_requested_stalls_are_drawn_as_two_not_the_capacity(self):
        # Live review: «المواقف المطلوبة 2؛ السعة التقديرية 6» drew six stall rectangles.
        r, model = rules(), owner_model()
        self.assertGreater(len(P.stalls(model, r)), 2, 'more stalls fit than were asked for')
        parking = P.summary(model, r)['parking']
        self.assertEqual(parking['required'], 2)
        self.assertEqual(len(parking['stalls']), 2)
        self.assertTrue(all(s[2:] == [2.7, 5.2] for s in parking['stalls']), 'the stated stall size')
        self.assertEqual(parking['stall_m'], [2.7, 5.2])
        self.assertEqual(parking['capacity'], len(P.stalls(model, r)))
        self.assertNotIn('PLOT_PARKING_SHORTFALL', {f['code'] for f in P.check(model, r)[0]})
        # Inside the front setback, beside the path to the building door, never on the building.
        front = r['building_footprint'][1]
        self.assertTrue(all(s[1] == 0.0 and s[1] + s[3] <= front + 1e-9 for s in parking['stalls']))

    def test_the_block_sits_west_with_the_stated_lane(self):
        r = rules()
        self.assertEqual(r['building_footprint'], [1.5, 5.5, 13.0, 16.0])
        self.assertEqual(r['setback_sources'], {'N': 'user', 'E': 'user', 'S': 'user', 'W': 'user'})
        # Only the west lane stated: the default east setback would centre the block; the position keeps it west.
        prog = program()
        prog['site']['setbacks_m'] = {'N': None, 'E': None, 'S': None, 'W': 1.5}
        west = P.resolve(PLOT, BRIEF, base_rows(), 'A', program=prog)
        self.assertEqual(west['building_footprint'][0], 1.5)
        self.assertIn('في غرب الأرض كما في وصفك؛ المسافة إلى حد الأرض: الغرب 1.5 م', ' '.join(west['assumptions']))
        prog['site']['footprint']['position'] = None
        centred = P.resolve(PLOT, BRIEF, base_rows(), 'A', program=prog)
        self.assertGreater(centred['building_footprint'][0], 1.5)
        # The owner's own plot inputs win over the program.
        user = P.resolve(dict(PLOT, setbacks_m={'W': 1.0}), BRIEF, base_rows(), 'A', program=program())
        self.assertEqual((user['setbacks_m']['W'], user['building_footprint'][0]), (1.0, 1.0))

    def test_a_parking_only_ground_floor_becomes_pilotis(self):
        prog = program()
        prog['levels'][0] = {'name': 'الدور الأرضي', 'use': 'parking', 'units': [], 'note': None}
        prog = B.validate_program(prog)
        r = P.resolve(PLOT, BRIEF, base_rows(), 'A', program=prog)
        self.assertEqual(r['parking']['placement'], 'pilotis')
        self.assertIn('الدور الأرضي مواقف تحت المبنى', ' '.join(r['assumptions']))
        none = P.resolve(dict(PLOT, parking={'placement': 'none'}), BRIEF, base_rows(), 'A', program=prog)
        self.assertEqual(none['parking']['placement'], 'none', 'an explicit «no parking» choice stays')


# ── the deterministic fallback ───────────────────────────────────────────────
def simple_program():
    """Two different floors without sizes: what the fallback can always fit."""
    prog = program()
    prog['site']['setbacks_m'] = {'N': 5.5, 'E': 3.0, 'S': 3.0, 'W': 1.5}
    prog['site']['footprint'] = {'width_m': 15.5, 'depth_m': 16.5, 'position': 'W'}
    room_ = lambda role, name, count=1, ensuite=False: {'role': role, 'name': name, 'count': count, 'width_m': None,
                                                       'depth_m': None, 'approx': False, 'ensuite': ensuite, 'note': None}
    prog['levels'] = [
        {'name': 'الدور الأرضي', 'use': 'residential', 'note': None, 'units': [{'name': None, 'bedrooms': 2, 'bathrooms': 2, 'rooms': [
            room_('majlis', 'مجلس'), room_('living', 'صالة'), room_('kitchen', 'مطبخ'), room_('bedroom', 'غرفة نوم', 2),
            room_('bathroom', 'حمام', 2)]}]},
        {'name': 'الدور الأول', 'use': 'residential', 'note': None, 'units': [{'name': None, 'bedrooms': 3, 'bathrooms': 2, 'rooms': [
            room_('living', 'صالة'), room_('kitchen', 'مطبخ'), room_('bedroom', 'جناح', 1, True), room_('bathroom', 'حمام الجناح'),
            room_('bedroom', 'غرفة نوم', 2), room_('bathroom', 'حمام')]}]}]
    return B.validate_program(prog)


class Fallback(unittest.TestCase):
    def test_the_owner_program_fails_naming_the_floor_it_cannot_fit(self):
        from acs_floor_layout import propose
        with self.assertRaises(PlanError) as caught:
            propose(program(), BRIEF, rows(), rules())
        self.assertTrue(caught.exception.code.startswith(F.FLOOR_NOT_FITTED), caught.exception.code)
        index = int(caught.exception.code[len(F.FLOOR_NOT_FITTED):])
        self.assertIn(F.floor_name(index), str(caught.exception))
        message = S.geometry_failure_message(caught.exception.code)
        self.assertIn('تعذّر على التوزيع البديل الحتمي ترتيب غرف ' + F.floor_name(index), message)
        self.assertIn('لم تُحفظ نسخة بأدوار متطابقة', message)

    def test_a_failed_provider_layout_uses_the_floor_fallback_never_identical_floors(self):
        prog = simple_program()
        requirements = [r for r in base_rows() if r['metric'] not in ('building_width_m', 'building_depth_m', 'unit_count')]
        requirements = [dict(r, expected=2) if r['metric'] == 'level_count' else r for r in requirements]
        requirements += [{'id': 'units', 'metric': 'unit_count', 'expected': 2, 'confirmed': True, 'source': 'inferred'}]
        requirements += F.requirement_rows(prog)

        def broken(text, **kw):
            consume()
            if kw['stage'] == 'plan_chunk':
                return json.dumps({'rooms': [{'id': z['id'], 'rect': [1.5, 5.5, 1, 1], 'role': z['role']} for z in asked(text)]})
            return '{}'   # a repair or openings reply without the requested data
        with patch.object(U, 'call_llm', side_effect=broken):
            out = S.generate_plan_candidate(BRIEF, requirements, 'A', 6, plot=PLOT, program=prog)
        building = out['building']
        self.assertEqual(building['meta']['acs_layout_method'], 'floor_program_fallback_v1')
        self.assertEqual([l['template'] for l in building['levels']], ['level_0', 'level_1'])
        model = copy.deepcopy(building)
        B.stamp(model, prog)
        ws = PlanLockWorkspace(existing_geometry_verifier)
        rev = ws.propose(model, brief=BRIEF, requirements=requirements, expected_head=None, note='fallback')
        result = ws.review(rev.id)
        self.assertTrue(result['can_approve'], result['issues'][:3])
        self.assertEqual(F.level_role_count(building, 0, 'majlis'), 1)
        self.assertEqual(F.level_role_count(building, 1, 'majlis'), 0)
        self.assertEqual(F.level_ensuite_count(building, 1), 1)

    def test_the_uniform_fallback_is_never_used_for_a_floor_program(self):
        def broken(text, **kw):
            consume()
            if kw['stage'] == 'plan_chunk':
                return json.dumps({'rooms': [{'id': z['id'], 'rect': [1.5, 5.5, 1, 1], 'role': z['role']} for z in asked(text)]})
            return '{}'   # a repair or openings reply without the requested data
        with patch('acs_plot_layout.propose', side_effect=AssertionError('uniform fallback')), \
                patch('acs_residential_layout.propose', side_effect=AssertionError('uniform fallback')), \
                patch.object(U, 'call_llm', side_effect=broken), self.assertRaises(PlanError) as caught:
            S.generate_plan_candidate(BRIEF, rows(), 'A', 6, plot=PLOT, program=program())
        self.assertTrue(caught.exception.code.startswith(F.FLOOR_NOT_FITTED))


# ── prompt size: only the floor a call works on ─────────────────────────────
class PromptBudget(unittest.TestCase):
    def test_extra_program_text_per_call_stays_small(self):
        provider = Provider()
        generate(provider)
        building = owner_model()
        summary = len(B.prompt_summary(program()))
        building_block = len(F.prompt_text(program()))
        self.assertLess(building_block, summary / 2, 'the plan prompt keeps a short building summary')
        for template, floor in F.floor_programs(program(), building).items():
            size = len(json.dumps(floor, ensure_ascii=False, separators=(',', ':')))
            self.assertLess(size, 1500, template)
        repair = len(json.dumps(F.floor_programs(program(), building), ensure_ascii=False, separators=(',', ':')))
        self.assertLess(repair, 3500)


if __name__ == '__main__':
    unittest.main(verbosity=2)
