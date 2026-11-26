"""Smart brief reading: one confirmed, budgeted provider call and a strictly validated program.

The provider is always stubbed. Covers the read action (admission, confirmation,
one-request budget, error envelope, durable receipt), the validator (shape,
ranges, consistency, sanitising), and the hand-off to generation (validation,
staleness, prompt summary, revision persistence and chat-edit carry).
"""
from __future__ import annotations

import asyncio
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
import acs_api_errors as E
import acs_brief_reader as B
import acs_workspace_http as H
import acs_workspace_service as S
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_provider_budget import consume, limited
from test_connected_workspace import ACTOR, PROJECT, Runner, model

FIXTURES = ROOT / 'tests' / 'remediation' / 'fixtures' / 'brief_reader'
BRIEF = (FIXTURES / 'owner_brief.txt').read_text(encoding='utf-8')
JOB = '44444444-4444-4444-8444-444444444444'


def owner_program():
    return json.loads((FIXTURES / 'owner_program.json').read_text(encoding='utf-8'))


def read_command(**extra):
    return {'action': 'read_brief', 'job_id': JOB, 'brief': BRIEF, 'confirmed': True, 'max_provider_calls': 1, **extra}


class Validator(unittest.TestCase):
    def test_owner_program_is_accepted_with_server_checks_and_honest_limits(self):
        p = B.validate_program(owner_program())
        self.assertEqual([len(level['units']) for level in p['levels']], [1, 1, 1])
        self.assertEqual(p['site']['setbacks_m'], {'N': 5.5, 'E': 5.5, 'S': 3.5, 'W': 1.5})
        self.assertEqual(p['site']['footprint'], {'width_m': 13, 'depth_m': 16, 'position': 'W'})
        # The brief says three bathrooms on the first floor but names two: a check, not a failure.
        self.assertEqual([c['code'] for c in p['checks']], ['UNIT_BATHROOMS'])
        self.assertIn('الدور الأول', p['checks'][0]['message'])
        # Phase 2 plans and checks per-floor programs, target sizes and the stated stall size.
        self.assertEqual([c['code'] for c in p['cannot_do']],
                         ['OUTDOOR', 'STAIR_TYPE', 'FACADE',
                          'OUTPUT_FURNISHED_PLANS', 'OUTPUT_OUTDOOR_PLAN', 'OUTPUT_SECTION', 'OUTPUT_SITE_PLAN'])
        self.assertEqual(B.validate_program(p), p, 'a validated program is a fixed point (incoming checks are recomputed)')

    def test_out_of_range_numbers_and_unknown_shapes_are_refused(self):
        cases = [
            (['site', 'width_m'], 500), (['site', 'setbacks_m', 'N'], -1), (['site', 'street_sides'], ['N', 'N']),
            (['levels', 0, 'units', 0, 'rooms', 0, 'count'], 0), (['levels', 0, 'units', 0, 'rooms', 0, 'width_m'], 99),
            (['levels', 0, 'units', 0, 'rooms', 0, 'role'], 'ballroom'), (['parking', 'count'], 2.5),
            (['levels', 0, 'units', 0, 'rooms', 0, 'depth_m'], None), (['site', 'width_m'], True),
            (['site', 'width_m'], float('nan')), (['outputs', 'section'], 'yes'), (['schema'], 'acs.brief-program/2'),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                p = owner_program()
                target = p
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(PlanError) as caught:
                    B.validate_program(p)
                self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_INVALID')
        p = owner_program(); p['site']['basement_m'] = 3
        with self.assertRaises(PlanError):
            B.validate_program(p)
        p = owner_program(); p['levels'] = []
        with self.assertRaises(PlanError):
            B.validate_program(p)
        p = owner_program(); p['levels'] = p['levels'] * 11
        with self.assertRaises(PlanError):
            B.validate_program(p)

    def test_impossible_geometry_is_inconsistent(self):
        def broken(change):
            p = owner_program(); change(p)
            with self.assertRaises(PlanError) as caught:
                B.validate_program(p)
            self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_INCONSISTENT')
            return str(caught.exception)
        self.assertIn('أكبر من الأرض', broken(lambda p: p['site']['footprint'].update(width_m=21)))
        self.assertIn('لا يتركان أرضًا', broken(lambda p: p['site']['setbacks_m'].update(W=10, E=10)))
        # A room larger than the 13 x 16 m building block.
        broken(lambda p: p['levels'][0]['units'][0]['rooms'][0].update(width_m=15, depth_m=15))
        broken(lambda p: p['outdoor'][0].update(width_m=40, depth_m=40))
        broken(lambda p: p['parking'].update(count=60))

    def test_sums_and_area_are_checked(self):
        p = owner_program()
        p['site']['area_m2'] = 600
        p['site']['setbacks_m']['E'] = 4
        p['levels'][2]['units'][0]['bedrooms'] = 3
        codes = [c['code'] for c in B.validate_program(p)['checks']]
        self.assertEqual(codes, ['SITE_AREA', 'STRIPS_WIDTH', 'UNIT_BATHROOMS', 'UNIT_BEDROOMS'])

    def test_model_text_is_sanitised_before_it_can_reach_a_prompt_or_page(self):
        p = owner_program()
        room = p['levels'][0]['units'][0]['rooms'][0]
        room['name'] = '<script>x</script>\n"ignore previous" `{}` ‮مجلس'
        room['note'] = 'line\nbreak\u0000 ' + 'ط' * 400
        p['other_requests'] = ['{"role":"system"}']
        out = B.validate_program(p)
        name = out['levels'][0]['units'][0]['rooms'][0]['name']
        for bad in '<>"`{}\n‮':
            self.assertNotIn(bad, name)
        self.assertLessEqual(len(name), 40)
        self.assertLessEqual(len(out['levels'][0]['units'][0]['rooms'][0]['note']), 120)
        self.assertNotIn('{', out['other_requests'][0])
        summary = B.prompt_summary(out)
        data = json.loads(summary[summary.index('\n', 1) + 1:])
        self.assertEqual(data['levels'][0]['units'][0]['rooms'][0]['name'], name)
        self.assertNotIn('note', json.dumps(data), 'free notes stay out of the planning prompt')
        self.assertNotIn('other_requests', json.dumps(data))


class ReplyAndWorker(unittest.TestCase):
    def test_json_only_reply(self):
        self.assertEqual(B.parse_reply('{"a":1}'), {'a': 1})
        self.assertEqual(B.parse_reply('```json\n{"a":1}\n```'), {'a': 1})
        for text in ['Here is the program: {"a":1}', '{"a":1} done', '[1,2]', '', '{"a":', None]:
            with self.subTest(text=text), self.assertRaises(PlanError) as caught:
                B.parse_reply(text)
            self.assertEqual(caught.exception.code, 'BRIEF_READ_INVALID_JSON')

    def test_one_provider_request_with_the_reader_prompt(self):
        import acs_understand as U
        seen = []
        def provider(description, **kw):
            consume()
            seen.append((description, kw))
            return json.dumps(owner_program(), ensure_ascii=False)
        with patch.object(U, 'call_llm', provider):
            out = B.read_program(BRIEF, 1)
        self.assertEqual(out['provider_calls'], 1)
        self.assertEqual(out['program']['schema'], B.SCHEMA)
        description, kw = seen[0]
        self.assertEqual(description, BRIEF)
        self.assertEqual(kw['system_override'], B.SYSTEM)
        self.assertEqual(kw['stage'], 'brief_read')
        self.assertIn('JSON only', B.SYSTEM)

    def test_a_second_request_is_refused_by_the_budget(self):
        import acs_understand as U
        def greedy(description, **kw):
            consume(); consume()
            return '{}'
        with patch.object(U, 'call_llm', greedy), self.assertRaises(E.AcsApiError) as caught:
            B.read_program(BRIEF, 1)
        self.assertEqual(caught.exception.code, E.ACS_PROVIDER_BUDGET_EXHAUSTED)

    def test_command_contract(self):
        self.assertEqual(B.read_command(read_command())['max_provider_calls'], 1)
        for change, code in [({'confirmed': False}, 'EXPLICIT_CONFIRMATION_REQUIRED'),
                             ({'max_provider_calls': 2}, 'INVALID_BUDGET'), ({'max_provider_calls': True}, 'INVALID_BUDGET'),
                             ({'brief': 'عمارة'}, 'DESCRIPTION_REQUIRED'), ({'extra': 1}, 'INVALID_PLAN_COMMAND')]:
            with self.subTest(change=change), self.assertRaises(PlanError) as caught:
                B.read_command(read_command(**change))
            self.assertEqual(caught.exception.code, code)
        missing = read_command(); del missing['confirmed']
        with self.assertRaises(PlanError):
            B.read_command(missing)

    def test_parent_validates_what_the_worker_returns(self):
        class Worker:
            def __init__(self, result): self.result, self.calls = result, []
            def run(self, target, kwargs, **controls):
                self.calls.append((target, kwargs, controls)); return self.result
        worker = Worker({'program': owner_program(), 'provider_calls': 1})
        program, calls = B.read_and_check(read_command(), runner=worker)
        self.assertEqual(calls, 1)
        self.assertEqual(worker.calls[0][0], B.TARGET)
        self.assertEqual(worker.calls[0][1], {'brief': BRIEF, 'max_provider_calls': 1})
        bad = owner_program(); bad['site']['width_m'] = 9999
        with self.assertRaises(PlanError) as caught:
            B.read_and_check(read_command(), runner=Worker({'program': bad, 'provider_calls': 1}))
        self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_INVALID')
        unconfirmed = Worker({'program': owner_program()})
        with self.assertRaises(PlanError):
            B.read_and_check(read_command(confirmed=False), runner=unconfirmed)
        self.assertEqual(unconfirmed.calls, [], 'no provider work before confirmation')


class JobStore:
    def __init__(self):
        self.jobs = {}

    def _request(self, method, path, payload=None, **kwargs):
        if method == 'GET':
            return [dict(j) for j in self.jobs.values()]
        if method == 'POST':
            if payload['id'] in self.jobs:
                return []
            self.jobs[payload['id']] = dict(payload)
            return [dict(payload)]
        if method == 'PATCH':
            job_id = path.split('&id=eq.')[1]
            self.jobs[job_id].update(payload)


class Limiter:
    def __init__(self, allowed=True):
        self.allowed, self.kinds = allowed, []

    def check(self, identity, kind):
        self.kinds.append(kind)
        return {'allowed': self.allowed, 'retry_after': 30}


class ReadActionHTTP(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        H.ACTIVE_JOBS.clear(); H.ACTIVE_PROJECTS.clear()

    async def call(self, middleware, store, payload):
        scope = {'type': 'http', 'path': '/v1/projects/' + PROJECT + '/workspace', 'method': 'POST', 'headers': [],
                 'state': {}, 'client': ('127.0.0.1', 1)}
        events = []
        async def receive():
            return {'type': 'http.request', 'body': json.dumps(payload).encode(), 'more_body': False}
        async def send(message):
            events.append(message)
        async def authorize(scope, send):
            scope['state']['authenticated_user_id'] = ACTOR; return True
        with patch.object(H.AUTH, 'authorize_asgi', authorize), \
             patch.object(H.SESSION, 'authenticated_supabase_plan_store', return_value=store), \
             patch.object(H.SERVICE, 'workspace', return_value=type('W', (), {'head': 'plan_other', 'history': lambda self: []})()):
            await middleware(scope, receive, send)
        return events[0]['status'], json.loads(events[1]['body'])

    async def test_confirmed_read_is_a_durable_job_with_a_validated_program(self):
        store, limiter, middleware = JobStore(), Limiter(), H.WorkspaceMiddleware(None)
        reads = []
        def stub(command, on_progress=None):
            reads.append(command['job_id'])
            on_progress({'phase': 'UNDERSTANDING', 'provider_calls': 1})
            return B.validate_program(owner_program()), 1
        with patch.object(H.RL, 'default_limiter', return_value=limiter), patch.object(H.BRIEF, 'read_and_check', stub):
            status, started = await self.call(middleware, store, read_command())
            # The read needs no particular head: a stale head never blocks it.
            self.assertEqual(status, 202)
            self.assertEqual(started['job']['state'], 'RUNNING')
            self.assertEqual(started['job']['kind'], 'read_brief')
            self.assertFalse(started['job']['can_resume'])
            await asyncio.gather(*middleware.tasks)
            status, polled = await self.call(middleware, store, {'action': 'job', 'job_id': JOB})
        self.assertEqual(reads, [JOB])
        self.assertEqual(limiter.kinds, ['edit'], 'a read uses the paid-edit quota, never the generation quota')
        job = polled['job']
        self.assertEqual((status, job['state'], job['revision_id'], job['provider_calls']), (200, 'SUCCEEDED', None, 1))
        self.assertEqual(job['program']['site']['width_m'], 20)
        self.assertEqual(store.jobs[JOB]['checkpoint']['kind'], 'brief_program')
        self.assertEqual(store.jobs[JOB]['resume_command']['action'], 'read_brief')
        # Another device finds the newest validated read (and its brief) without a provider call.
        status, latest = await self.call(middleware, store, {'action': 'brief_read_latest'})
        self.assertEqual(status, 200)
        self.assertEqual(latest['read']['job_id'], JOB)
        self.assertEqual(latest['read']['brief'], BRIEF)
        self.assertEqual(latest['read']['program']['levels'][1]['name'], 'الدور الأول')
        # A read is never resumable and never re-sent automatically.
        status, resumed = await self.call(middleware, store, {'action': 'resume', 'job_id': '55555555-5555-4555-8555-555555555555',
                                                              'resume_job_id': JOB, 'confirmed': True, 'max_provider_calls': 1})
        self.assertEqual((status, resumed['error']['code']), (400, 'INVALID_RESUME'))

    async def test_unconfirmed_or_over_budget_reads_start_nothing(self):
        store, limiter, middleware = JobStore(), Limiter(), H.WorkspaceMiddleware(None)
        def stub(*a, **k):
            raise AssertionError('no provider work')
        with patch.object(H.RL, 'default_limiter', return_value=limiter), patch.object(H.BRIEF, 'read_and_check', stub):
            for payload, code in [(read_command(confirmed=False), 'EXPLICIT_CONFIRMATION_REQUIRED'),
                                  (read_command(max_provider_calls=3), 'INVALID_BUDGET'),
                                  (read_command(brief='قصير'), 'DESCRIPTION_REQUIRED')]:
                status, body = await self.call(middleware, store, payload)
                self.assertEqual((status, body['ok'], body['error']['code']), (400, False, code))
                self.assertIn('contract', body, 'the shared error envelope')
        self.assertEqual(store.jobs, {})
        self.assertEqual(limiter.kinds, [])

    async def test_rate_limit_and_one_paid_job_per_project(self):
        store, middleware = JobStore(), H.WorkspaceMiddleware(None)
        with patch.object(H.RL, 'default_limiter', return_value=Limiter(allowed=False)):
            status, body = await self.call(middleware, store, read_command())
        self.assertEqual((status, body['error']['code']), (429, E.ACS_RATE_LIMITED))
        self.assertEqual(store.jobs, {})
        H.ACTIVE_PROJECTS[PROJECT] = '66666666-6666-4666-8666-666666666666'
        with patch.object(H.RL, 'default_limiter', return_value=Limiter()):
            status, body = await self.call(middleware, store, read_command())
        self.assertEqual((status, body['error']['code']), (409, 'GENERATION_IN_PROGRESS'))

    async def test_failed_read_keeps_only_a_code_and_an_arabic_reason(self):
        store, middleware = JobStore(), H.WorkspaceMiddleware(None)
        def stub(command, on_progress=None):
            raise PlanError('BRIEF_READ_INVALID_JSON', 'raw provider text must never be stored')
        with patch.object(H.RL, 'default_limiter', return_value=Limiter()), patch.object(H.BRIEF, 'read_and_check', stub):
            await self.call(middleware, store, read_command())
            await asyncio.gather(*middleware.tasks)
            status, polled = await self.call(middleware, store, {'action': 'job', 'job_id': JOB})
        job = polled['job']
        self.assertEqual((job['state'], job['error_code']), ('FAILED', 'BRIEF_READ_INVALID_JSON'))
        self.assertIn('الذكاء الاصطناعي', job['error_message'])
        self.assertNotIn('program', job)
        self.assertNotIn('raw provider', json.dumps(store.jobs))


def residential_command(program=None, width=20):
    brief = 'عمارة سكنية بشقة في كل دور. عرض الموقع 20 متر.'
    cmd = {'action': 'generate', 'job_id': '77777777-7777-4777-8777-777777777777', 'brief': brief,
           'requirements': [{'id': 'width', 'metric': 'site_width_m', 'expected': width, 'source': 'requested',
                             'evidence': '20', 'confirmed': True}],
           'expected_head': None, 'option': 'A', 'confirmed': True, 'max_provider_calls': 3}
    if program is not None:
        cmd['program'] = program
    return cmd


def small_program():
    p = owner_program()
    p['site'].update(width_m=20, depth_m=20, area_m2=None)
    p['site']['setbacks_m'] = {'N': None, 'E': None, 'S': None, 'W': None}
    p['site']['footprint'] = {'width_m': None, 'depth_m': None, 'position': None}
    p['levels'] = p['levels'][:1]
    return p


class GenerationHandOff(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        db = SQLitePlanStore(Path(self.temp.name) / 'plans.sqlite3'); db.create_project(PROJECT, owner_id=ACTOR)
        self.store = SQLitePlanStoreAdapter(db)

    def tearDown(self):
        self.temp.cleanup()

    def test_command_validates_the_program_before_any_paid_call(self):
        out = S.generation_command(residential_command(small_program()))
        self.assertEqual(out['program']['checks'], B.checks(out['program']))
        with self.assertRaises(PlanError) as caught:
            S.generation_command(residential_command(small_program(), width=22))
        self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_STALE')
        bad = small_program(); bad['levels'][0]['units'][0]['rooms'][0]['count'] = 99
        with self.assertRaises(PlanError) as caught:
            S.generation_command(residential_command(bad))
        self.assertEqual(caught.exception.code, 'BRIEF_PROGRAM_INVALID')
        warehouse = residential_command(small_program()); warehouse['brief'] = 'مستودع توزيع بعرض 20 متر'
        with self.assertRaises(PlanError) as caught:
            S.generation_command(warehouse)
        self.assertEqual(caught.exception.code, 'INVALID_BRIEF_PROGRAM')

    def test_confirmed_program_reaches_the_worker_and_persists_with_the_revision(self):
        runner = Runner(model())
        rid = S.generate_and_save(self.store, PROJECT, ACTOR, residential_command(small_program()), runner=runner)
        sent = runner.calls[0][1]
        self.assertEqual(sent['program']['levels'][0]['name'], 'الدور الأرضي')
        view = S.view(SQLitePlanStoreAdapter(SQLitePlanStore(Path(self.temp.name) / 'plans.sqlite3')), PROJECT, ACTOR)
        self.assertEqual(view['revision_id'], rid)
        self.assertEqual(view['brief_program'], B.validate_program(small_program()))
        self.assertIsNone(view['plot_input'])
        # A provider cannot plant or rewrite the stamped program.
        forged = model(); forged['meta'][B.META_KEY] = {'schema': B.SCHEMA, 'levels': 'forged'}
        self.assertNotIn(B.META_KEY, B.stamp(forged, None)['meta'])
        before = {'meta': {B.META_KEY: view['brief_program']}}
        edited = B.carry(before, {'meta': {B.META_KEY: 'provider'}})
        self.assertEqual(edited['meta'][B.META_KEY], view['brief_program'])

    def test_planning_prompt_gets_a_server_built_summary(self):
        import acs_plan_bridge
        captured = []
        class Stop(Exception):
            pass
        def capture(prompt, **kw):
            captured.append(prompt); raise Stop()
        program = B.validate_program(small_program())
        program['levels'][0]['units'][0]['rooms'][0]['name'] = 'مجلس'
        with patch.object(acs_plan_bridge, 'generate_candidate', capture), self.assertRaises(Stop):
            S.generate_plan_candidate(residential_command()['brief'], residential_command()['requirements'], 'A', 3, program=program)
        prompt = captured[0]
        self.assertIn('برنامج المالك المؤكد', prompt)
        self.assertIn('"target_m":[4,4.5]', prompt)
        self.assertIn('"outdoor_not_drawn"', prompt)
        with patch.object(acs_plan_bridge, 'generate_candidate', capture), self.assertRaises(Stop):
            S.generate_plan_candidate(residential_command()['brief'], residential_command()['requirements'], 'A', 3)
        self.assertNotIn('برنامج المالك المؤكد', captured[1], 'no program, no summary')

    def test_owner_plot_inputs_come_back_without_assumed_defaults(self):
        import acs_plot_rules as P
        rows = [{'id': m, 'metric': m, 'expected': v, 'confirmed': True, 'source': 'inferred'} for m, v in
                (('site_width_m', 20), ('site_depth_m', 25), ('level_count', 3), ('unit_count', 3))]
        rules = P.resolve({'streets': ['N'], 'setbacks_m': {'N': 5.5, 'E': 5.5, 'S': 3.5, 'W': 1.5},
                           'parking': {'placement': 'front_setback', 'count': 2}, 'landing_entries': True}, 'عمارة', rows)
        self.assertEqual(B.plot_input(rules), {'streets': ['N'], 'setbacks_m': {'N': 5.5, 'E': 5.5, 'S': 3.5, 'W': 1.5},
                                               'parking': {'placement': 'front_setback', 'count': 2}, 'landing_entries': True})
        assumed = P.resolve({'parking': {'placement': 'none'}}, 'عمارة', rows)
        self.assertEqual(B.plot_input(assumed), {'streets': [], 'setbacks_m': {}, 'parking': {'placement': 'none'},
                                                 'landing_entries': False})


if __name__ == '__main__':
    unittest.main(verbosity=2)
