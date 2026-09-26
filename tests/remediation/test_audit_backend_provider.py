"""عقد نقل المزوّد: عطل البث لا يفتح نداءً مدفوعاً آخر، والقياس يشمل الإصلاح."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ACS_AUDIT_ROOT']) if os.environ.get('ACS_AUDIT_ROOT') else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_api_errors as E
import acs_provider_budget as BUDGET
import acs_understand as U
import acs_validate as V

MODEL = {'site': {'w': 20, 'd': 25}, 'floor_height': 3.2, 'wall_h': 3, 'wall_t': 0.2,
         'levels': [{'index': 0, 'template': 'G'}],
         'floors': {'G': {'rooms': [{'id': 'غرفة', 'rect': [0, 0, 4, 4],
                                    'doors': [], 'windows': []}]}}, 'meta': {}}

class Message:
    content = [types.SimpleNamespace(type='text', text='{"ok":1}')]
    stop_reason = 'end_turn'
    usage = types.SimpleNamespace(input_tokens=100, output_tokens=20)

class Stream:
    def __init__(self, fail): self.fail = fail
    def __enter__(self):
        if self.fail == 'enter': raise AttributeError('synthetic stream failure')
        return self
    def __exit__(self, *args):
        if self.fail == 'exit': raise AttributeError('synthetic stream failure')
        return False
    def get_final_message(self):
        if self.fail == 'decode': raise AttributeError('synthetic stream failure')
        return Message()

class Messages:
    def __init__(self, calls, fail=None): self.calls, self.fail = calls, fail
    def stream(self, *, model, max_tokens, messages, system=None):
        self.calls.append('stream')
        if self.fail == 'call': raise AttributeError('synthetic stream failure')
        return Stream(self.fail)
    def create(self, *, model, max_tokens, messages, system=None):
        self.calls.append('create')
        return Message()

class NoStream(Messages):
    @property
    def stream(self): raise AttributeError('SDK has no stream method')

@contextlib.contextmanager
def provider(messages_cls=Messages, fail=None):
    calls = []
    mod = types.ModuleType('anthropic'); mod.__version__ = '0.40.0'
    class Client:
        def __init__(self, **kw): self.messages = messages_cls(calls, fail)
    mod.Anthropic = Client
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('ACS_LLM_', 'ANTHROPIC_'))}
    env.update({'ANTHROPIC_API_KEY': 'sk-ant-synthetic-audit-only',
                'ACS_LLM_MODEL': 'claude-sonnet-5', 'ACS_UPSTREAM_BACKOFF_S': '0'})
    with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, {'anthropic': mod}), \
            contextlib.redirect_stdout(io.StringIO()):
        yield calls

def invoke(module=U):
    return module._call_llm_impl('فيلا صغيرة', model='claude-sonnet-5', max_tokens=4000)

# لا يغيّر ملف الإنتاج: نعيد حارس الإصدار القديم داخل نسخة وحدة في الذاكرة.
LEGACY_CALL = '''
def _call(kw):
    import acs_provider_budget as REQUEST_BUDGET
    REQUEST_BUDGET.consume()
    try:
        with client.messages.stream(**kw) as s:
            return s.get_final_message()
    except AttributeError:
        tel["transport"] = "create"
        REQUEST_BUDGET.consume()
        return client.messages.create(**kw)
'''

def transport_mutant():
    tree = ast.parse(Path(U.__file__).read_text())
    class RestoreBroadFallback(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name == '_call' and len(node.args.args) == 1 and node.args.args[0].arg == 'kw':
                return ast.copy_location(ast.parse(LEGACY_CALL).body[0], node)
            return self.generic_visit(node)
    tree = ast.fix_missing_locations(RestoreBroadFallback().visit(tree))
    module = types.ModuleType('acs_understand_audit_mutant'); module.__file__ = U.__file__
    exec(compile(tree, U.__file__, 'exec'), module.__dict__)
    return module

def accounting_mutant():
    tree = ast.parse(Path(U.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'call_llm_repair':
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'call_llm':
                    call.keywords = [kw for kw in call.keywords if kw.arg != 'telemetry']
    module = types.ModuleType('acs_understand_accounting_mutant'); module.__file__ = U.__file__
    exec(compile(ast.fix_missing_locations(tree), U.__file__, 'exec'), module.__dict__)
    return module

class ProviderTransport(unittest.TestCase):
    def test_started_stream_failure_never_resubmits_create(self):
        for phase in ['call', 'enter', 'decode', 'exit']:
            with self.subTest(phase=phase), provider(fail=phase) as calls:
                with self.assertRaises(E.AcsApiError): invoke()
                self.assertEqual(calls, ['stream'])
    def test_sound_stream_spends_one_unit(self):
        with provider() as calls, BUDGET.limited(1) as budget:
            self.assertEqual(invoke(), '{"ok":1}')
            self.assertEqual(calls, ['stream'])
            self.assertEqual(budget['used'], 1)
    def test_absent_stream_calls_create_once_with_one_unit(self):
        with provider(NoStream) as calls, BUDGET.limited(1) as budget:
            self.assertEqual(invoke(), '{"ok":1}')
            self.assertEqual(calls, ['create'])
            self.assertEqual(budget['used'], 1)
    def test_exhausted_budget_sends_nothing(self):
        for cls in (Messages, NoStream):
            with self.subTest(cls=cls.__name__), provider(cls) as calls, BUDGET.limited(1, used=1):
                with self.assertRaises(E.AcsApiError) as raised: invoke()
                self.assertEqual(raised.exception.code, E.ACS_PROVIDER_BUDGET_EXHAUSTED)
                self.assertEqual(calls, [])
    def test_mutation_broad_catch_is_detected(self):
        mutant = transport_mutant()
        with provider(fail='decode') as calls:
            self.assertEqual(invoke(mutant), '{"ok":1}')
            self.assertEqual(calls, ['stream', 'create'])
            self.assertNotEqual(calls, ['stream'], 'الحارس يجب أن يرصد إعادة الإرسال')
    def test_mutation_phantom_budget_is_detected(self):
        mutant = transport_mutant()
        with provider(NoStream) as calls, BUDGET.limited(1):
            with self.assertRaises(E.AcsApiError) as raised: invoke(mutant)
            self.assertEqual(raised.exception.code, E.ACS_PROVIDER_BUDGET_EXHAUSTED)
            self.assertEqual(calls, [])

class RepairAccounting(unittest.TestCase):
    def run_generation(self, malformed_repair=False, sound=False, module=U):
        calls=[]
        def response(description, **kw):
            calls.append(kw['stage'])
            kw['telemetry'].update(input_tokens=100, output_tokens=20, complete=True,
                                   stop_reason='end_turn', max_output_tokens=4000)
            return 'not JSON' if malformed_repair and kw['stage']=='repair' else json.dumps(MODEL)
        with patch.object(module, '_call_llm_impl', side_effect=response), \
                patch.object(module, '_emit_generation_telemetry'), \
                contextlib.redirect_stdout(io.StringIO()):
            if sound:
                with patch.object(V, 'validate_building', return_value=([], {})):
                    building=module.understand('فيلا صغيرة',deep=False,repair_rounds=5)
            else: building=module.understand('فيلا صغيرة',deep=False,repair_rounds=5)
        return building,calls
    def test_every_completed_repair_is_counted(self):
        building,calls=self.run_generation()
        stages=building['meta']['acs_generation']['stages']
        self.assertEqual(calls,['single']+['repair']*5)
        self.assertEqual([s['stage'] for s in stages],calls)
        self.assertEqual(sum(s['input_tokens'] for s in stages),600)
        self.assertEqual(sum(s['output_tokens'] for s in stages),120)
        self.assertEqual(building['meta']['acs_issues'],len(V.validate_building(building)[0]))
    def test_paid_malformed_repair_is_counted_with_error(self):
        building,calls=self.run_generation(malformed_repair=True)
        stages=building['meta']['acs_generation']['stages']
        self.assertEqual(calls,['single','repair'])
        self.assertEqual([s['stage'] for s in stages],calls)
        self.assertEqual(stages[-1]['error'],E.ACS_UPSTREAM_INVALID_JSON)
        self.assertFalse(stages[-1]['parsed'])
        self.assertEqual(building['floors'],MODEL['floors'])
    def test_sound_model_creates_no_phantom_repair_stage(self):
        building,calls=self.run_generation(sound=True)
        self.assertEqual(calls,['single'])
        self.assertEqual([s['stage'] for s in building['meta']['acs_generation']['stages']],calls)
    def test_mutation_lost_repair_usage_is_detected(self):
        building,calls=self.run_generation(module=accounting_mutant())
        stages=building['meta']['acs_generation']['stages']
        self.assertEqual(calls,['single']+['repair']*5)
        self.assertEqual(sum(s.get('input_tokens') or 0 for s in stages),100)
        self.assertNotEqual(sum(s.get('input_tokens') or 0 for s in stages),600)

if __name__=='__main__': unittest.main(verbosity=2)
