# -*- coding: utf-8 -*-
"""F-18/F-13 — السجلّ المنظَّم وحدوده الخصوصية.

العيب الذي يعيده هذا الملفّ ثم يثبت زواله: مسار الطلب كان يطبع traceback خاماً.
الـtraceback يتجاوز كل تعقيم — استثناء من مكتبة المزوّد قد يحمل جسم الطلب، أي
وصف الزائر كاملاً، إلى سجلّ الخادم. ومعه كان الرد الخام والمفتاح على بُعد سطر
واحد من الظهور في سجلّ إنتاجي يقرأه من لا يملك حقّ قراءة بيانات الزائر.

العقد المُثبَت هنا، بتشغيل الشيفرة نفسها لا بقراءتها:
  أ) سطر JSON واحد صالح لكل حدث، بحقول معلنة.
  ب) الحجب بالاسم: كل اسم في FORBIDDEN_FIELDS يسقط ولو مُرِّر صراحةً.
  ج) الحجب بالشكل: ما يشبه المفتاح يُعقَّم داخل القيم المسموح بها نفسها.
  د) الاستثناء: صنفٌ وموضعٌ في الإنتاج، أثرٌ كامل في التطوير — وبينهما لا نصّ.
  هـ) تليمتري التوليد: الحقول المعلنة وحدها تمرّ.
  و) الوصل الثابت: لا traceback.print_exc في مسار الطلب، ولا طباعة لوصف الزائر.

طريقة اختبار عَلَم الأثر: **إعادة تحميل الوحدة** (importlib.reload) بعد ضبط
ACS_LOG_STACK_TRACES في البيئة. اخترناها لأن العَلَم يُقرأ عند الاستيراد ويُقرأ
داخل `exception()` كمتغيّر وحدة: إعادة التحميل تُشغّل المسار الحقيقي كاملاً بدل
ترقيع قيمة في الذاكرة، فلا نثبت سلوكاً لا يحدث في الإنتاج.
"""
import ast
import importlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                        # noqa: E402
import acs_logging as L                                           # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def rd(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8') as fh:
        return fh.read()


class Cap(object):
    """مجرى التقاط — نقرأ منه الأسطر المكتوبة فعلاً، لا القاموس المُعاد."""

    def __init__(self):
        self.buf = io.StringIO()

    def write(self, s):
        return self.buf.write(s)

    def flush(self):
        pass

    def lines(self):
        return [x for x in self.buf.getvalue().split('\n') if x.strip()]

    def one(self):
        ls = self.lines()
        return ls[0] if len(ls) == 1 else ''

    def reset(self):
        self.buf = io.StringIO()


def logger(min_level='info', cls=None, **kw):
    cap = Cap()
    klass = cls or L.StructuredLogger
    return cap, klass(stream=cap, min_level=min_level, **kw)


# ═══════════════════════════════════════ أ) سطر واحد، JSON صالح، حقول معلنة ═
print('\n── أ · سطر JSON واحد لكل حدث ──')

cap, log = logger()
log.info('unit_test_event', status=200, duration_ms=12)
_lines = cap.lines()
chk('one event writes exactly one line', len(_lines) == 1, str(len(_lines)))

_rec = None
try:
    _rec = json.loads(_lines[0]) if _lines else None
except ValueError as err:
    _rec = None
chk('that line is valid JSON', isinstance(_rec, dict))
chk('every event carries ts, level, event and service',
    isinstance(_rec, dict)
    and all(k in _rec for k in ('ts', 'level', 'event', 'service')),
    str(sorted((_rec or {}).keys())))
chk('the declared fields survive intact',
    (_rec or {}).get('status') == 200 and (_rec or {}).get('duration_ms') == 12)
chk('the timestamp is UTC ISO-8601 to the second',
    isinstance((_rec or {}).get('ts'), str)
    and len(_rec['ts']) == 20 and _rec['ts'].endswith('Z') and 'T' in _rec['ts'],
    str((_rec or {}).get('ts')))

cap.reset()
for lvl in ('info', 'warn', 'error'):
    getattr(log, lvl)('multi_%s' % lvl)
chk('three events write three separate lines, one JSON object each',
    len(cap.lines()) == 3
    and all(isinstance(json.loads(x), dict) for x in cap.lines()))
chk('a newline inside a value can never split the record into two lines',
    (lambda: (logger()[0], None))() is not None)
cap2, log2 = logger()
log2.info('newline_probe', detail='first line\nsecond line')
chk('an embedded newline is escaped, not emitted raw',
    len(cap2.lines()) == 1 and '\\n' in cap2.lines()[0],
    str(len(cap2.lines())))

# ═════════════════════════════════════════════════════ ب) ترشيح المستوى ═════
print('\n── ب · ترشيح المستوى ──')

cap, log = logger(min_level='info')
_ret = log.debug('debug_event_should_vanish', k=1)
chk('a debug event is suppressed at min_level=info',
    cap.lines() == [] and _ret is None, str(cap.lines()))
log.info('info_event_passes')
chk('an info event passes at min_level=info', len(cap.lines()) == 1)

cap, dbg = logger(min_level='debug')
dbg.debug('debug_event_passes_when_asked')
chk('the same debug event passes at min_level=debug', len(cap.lines()) == 1)

cap, quiet = logger(min_level='error')
quiet.warn('warn_suppressed')
quiet.error('error_passes')
chk('a warn is suppressed at min_level=error while an error passes',
    len(cap.lines()) == 1
    and json.loads(cap.lines()[0])['event'] == 'error_passes')

chk('an unknown level name never opens the gate — the module falls back to info',
    L.MIN_LEVEL in L._LEVEL_RANK)

# ══════════════════════════════════════════ ج) الحجب بالاسم — كل حقل محجوب ═
print('\n── ج · الحجب بالاسم ──')

SECRETS = {
    'text': 'الوصف السرّي للزائر — قاعة رياضية في حي النرجس',
    'description': 'CONFIDENTIAL_DESCRIPTION_VALUE',
    'prompt': 'SYSTEM_PROMPT_VALUE_SHOULD_NEVER_APPEAR',
    'building': '{"site": {"w": 20}, "owner": "PRIVATE_OWNER_NAME"}',
    'api_key': 'sk-' + 'ant-' + 'PRIVATEKEY0123456789',
    'authorization': 'Bearer PRIVATE_AUTH_TOKEN_VALUE',
    'cookie': 'session=PRIVATE_COOKIE_VALUE',
}

cap, log = logger()
log.info('explicit_forbidden_fields', request_id='req_1', **SECRETS)
_line = cap.one()
chk('the event is still emitted, with the safe fields kept',
    bool(_line) and json.loads(_line).get('request_id') == 'req_1')
_missing_keys = [k for k in SECRETS if k in (json.loads(_line) if _line else {})]
chk('not one forbidden KEY survives into the record', _missing_keys == [],
    ', '.join(_missing_keys))
_leaked = [k for k, v in SECRETS.items() if v in (_line or '')]
chk('not one forbidden VALUE appears anywhere in the emitted line',
    _leaked == [], ', '.join(_leaked))
chk('nor does any fragment of the visitor description',
    'النرجس' not in (_line or '') and 'PRIVATE_OWNER_NAME' not in (_line or ''))

_survivors = []
for name in sorted(L.FORBIDDEN_FIELDS):
    c, lg = logger()
    token = 'SENTINEL_%s_VALUE' % name.replace('-', '_').upper()
    lg.info('forbidden_sweep', **{name: token})
    line = c.one()
    if token in line or name in json.loads(line):
        _survivors.append(name)
chk('EVERY declared forbidden field is dropped when passed explicitly '
    '(%d fields swept)' % len(L.FORBIDDEN_FIELDS),
    _survivors == [], ', '.join(_survivors))

c, lg = logger()
lg.info('case_probe', TEXT='UPPERCASE_LEAK', Api_Key='MIXED_CASE_LEAK')
chk('the block list is case-insensitive — TEXT and Api_Key are dropped too',
    'UPPERCASE_LEAK' not in c.one() and 'MIXED_CASE_LEAK' not in c.one())

# ══════════════════════════════════ ج2) الحجب بالشكل داخل القيم المسموح بها ═
print('\n── ج2 · تعقيم شكل السرّ داخل قيمة مسموح بها ──')

KEYISH = 'sk-' + 'ant-' + 'abc123DEF456ghi789jkl'
JWTISH = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig'
c, lg = logger()
lg.error('upstream_detail', detail='call failed with key %s and header %s'
         % (KEYISH, JWTISH))
_line = c.one()
chk('a key shape inside an ALLOWED value is redacted', KEYISH not in _line
    and 'sk-ant-' not in _line, _line[:160])
chk('a bearer token inside an ALLOWED value is redacted',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in _line
    and 'Bearer eyJ' not in _line, _line[:160])
chk('the redaction marker proves acs_api_errors.redact actually ran',
    '[REDACTED]' in _line and _line.count('[REDACTED]') >= 2,
    str(_line.count('[REDACTED]')))
chk('the emitted value equals exactly what E.redact produces — same function, '
    'not a private copy',
    json.loads(_line)['detail']
    == E.redact('call failed with key %s and header %s' % (KEYISH, JWTISH)))
chk('the logger reaches redaction through acs_api_errors, not a local regex',
    '_E.redact(' in rd('acs_logging.py'))

c, lg = logger()
lg.error('nested_secret', upstream={'kind': 'auth', 'hint': 'key=' + KEYISH})
chk('a key shape nested one level deep is redacted too',
    KEYISH not in c.one() and '[REDACTED]' in c.one())

# ══════════════════════════════════════════ ج3) الاقتطاع والتحديد البنيوي ═══
print('\n── ج3 · الاقتطاع والحدود البنيوية ──')

LONG = 'A' * (L.MAX_VALUE_CHARS + 500)
c, lg = logger()
lg.info('long_value', detail=LONG)
_v = json.loads(c.one())['detail']
chk('a long value is truncated to the declared cap',
    len(_v) == L.MAX_VALUE_CHARS + 1 and _v.endswith('…'),
    '%d vs cap %d' % (len(_v), L.MAX_VALUE_CHARS))
chk('the cap is a declared constant, not a magic number in the emitter',
    isinstance(L.MAX_VALUE_CHARS, int) and 0 < L.MAX_VALUE_CHARS <= 2000)

c, lg = logger()
lg.info('nested_shapes',
        upstream={'kind': 'x', 'text': 'NESTED_DESCRIPTION_LEAK',
                  'inner': {'api_key': 'NESTED_KEY_LEAK', 'status': 500,
                            'deeper': {'prompt': 'DEEP_PROMPT_LEAK', 'ok': True}}},
        items=[{'text': 'LIST_DESCRIPTION_LEAK', 'n': 1},
               'plain', {'n': 2}])
_line = c.one()
_rec = json.loads(_line)
chk('a forbidden key nested inside a dict is dropped',
    'NESTED_DESCRIPTION_LEAK' not in _line and 'NESTED_KEY_LEAK' not in _line)
chk('recursion does not stop at depth one — a forbidden key three levels down '
    'is dropped as well', 'DEEP_PROMPT_LEAK' not in _line)
chk('a forbidden key inside a list of dicts is dropped',
    'LIST_DESCRIPTION_LEAK' not in _line)
chk('the harmless nested values survive — sanitising is not deleting',
    _rec['upstream']['kind'] == 'x'
    and _rec['upstream']['inner']['status'] == 500
    and _rec['upstream']['inner']['deeper']['ok'] is True)

c, lg = logger()
lg.info('bounded', items=list(range(100)),
        mapping={('k%03d' % i): i for i in range(100)})
_rec = json.loads(c.one())
chk('a long list is bounded, not emitted whole', len(_rec['items']) == 20,
    str(len(_rec['items'])))
chk('a wide dict is bounded, not emitted whole', len(_rec['mapping']) == 20,
    str(len(_rec['mapping'])))

c, lg = logger()
lg.info('none_field', absent=None, present=0)
_rec = json.loads(c.one())
chk('a None field is omitted rather than logged as null',
    'absent' not in _rec and _rec['present'] == 0)

c, lg = logger()


class _Weird(object):
    def __str__(self):
        return 'object carrying ' + KEYISH


lg.info('unknown_type', blob=_Weird())
chk('an unknown object is stringified through the same sanitiser, not repr-ed raw',
    KEYISH not in c.one() and '[REDACTED]' in c.one())

# ═══════════════════════════════════════════════════ د) الاستثناء والأثر ════
print('\n── د · الاستثناء: صنف وموضع، لا نصّ ──')

RAISE_SECRET = 'RAW_EXCEPTION_TEXT_WITH_USER_DESCRIPTION النرجس'


def _boom():
    raise RuntimeError(RAISE_SECRET + ' key=' + KEYISH)


def _caught():
    try:
        _boom()
    except RuntimeError as exc:
        return exc
    return None


_env_saved = dict(os.environ)


def _reload_logging(stack_traces):
    os.environ['ACS_LOG_STACK_TRACES'] = '1' if stack_traces else '0'
    return importlib.reload(L)


LP = _reload_logging(False)                         # الإنتاج: بلا أثر كامل
chk('with ACS_LOG_STACK_TRACES disabled the module flag is off',
    LP.STACK_TRACES is False)
capP = Cap()
logP = LP.StructuredLogger(stream=capP, min_level='info')
logP.exception('unhandled_request_error', _caught(), request_id='req_9')
_line = capP.one()
_rec = json.loads(_line) if _line else {}
chk('an exception event still emits exactly one JSON line', bool(_line))
chk('it names the exception CLASS', _rec.get('error_class') == 'RuntimeError')
chk('it names the position as file:line', ':' in str(_rec.get('error_at'))
    and str(_rec.get('error_at')).split(':')[-1].isdigit()
    and str(_rec.get('error_at')).startswith('test_logging.py'),
    str(_rec.get('error_at')))
chk('it carries NO stack field in production', 'stack' not in _rec,
    str(sorted(_rec.keys())))
chk('and NO raw exception text — the traceback bypass is closed',
    RAISE_SECRET not in _line and 'النرجس' not in _line
    and KEYISH not in _line)
chk('the request id still ties the event to the request',
    _rec.get('request_id') == 'req_9')

LD = _reload_logging(True)                          # التطوير: أثر كامل معلن
chk('with ACS_LOG_STACK_TRACES enabled the module flag is on',
    LD.STACK_TRACES is True)
capD = Cap()
logD = LD.StructuredLogger(stream=capD, min_level='info')
logD.exception('unhandled_request_error', _caught())
_recD = json.loads(capD.one()) if capD.one() else {}
chk('a stack field appears only when stack traces are explicitly enabled',
    'stack' in _recD and 'Traceback' in _recD['stack'])
chk('no key shape survives into the development stack either',
    KEYISH not in capD.one())
chk('the development stack is bounded by the same declared cap — a deep '
    'traceback cannot flood the log',
    len(_recD.get('stack', '')) <= LD.MAX_VALUE_CHARS + 1,
    str(len(_recD.get('stack', ''))))

# أثرٌ ضحل (إطار واحد) ليبقى نصّ الاستثناء داخل السقف بعد الاقتطاع: هكذا نرى
# فعل التعقيم نفسه على حقل الأثر، لا غيابَ السرّ لأن الاقتطاع ابتلعه.
try:
    raise RuntimeError('shallow failure key=' + KEYISH)
except RuntimeError as _shallow:
    _shallow_exc = _shallow
capS = Cap()
LD.StructuredLogger(stream=capS, min_level='info').exception(
    'shallow_probe', _shallow_exc)
_stack = json.loads(capS.one()).get('stack', '')
chk('the development stack itself is redacted before it is written',
    KEYISH not in _stack and '[REDACTED]' in _stack, _stack[-120:])
chk('the two modes differ ONLY by the stack field',
    set(_recD.keys()) - set(_rec.keys()) == {'stack'},
    str(set(_recD.keys()) ^ set(_rec.keys())))

os.environ.pop('ACS_LOG_STACK_TRACES', None)
if 'ACS_LOG_STACK_TRACES' in _env_saved:
    os.environ['ACS_LOG_STACK_TRACES'] = _env_saved['ACS_LOG_STACK_TRACES']
L = importlib.reload(L)
chk('the module restores its declared default after the probe '
    '(development on, production off)',
    L.STACK_TRACES is (not L.IS_PRODUCTION))

# ═════════════════════════════════════════════ هـ) تليمتري التوليد (F-13) ═══
print('\n── هـ · تليمتري التوليد ──')

c, lg = logger()
_ret = lg.generation(request_id='req_t', strategy='single', model='claude-sonnet-5',
                     stages='single', input_tokens=1200, output_tokens=900,
                     stop_reason='end_turn', max_output_tokens=32000,
                     duration_ms=4210, retries=0, truncated=False,
                     upstream_class=None, success=True,
                     estimated_cost_usd=0.0123,
                     text='secret user description',
                     description='another secret',
                     prompt='the whole system prompt',
                     api_key='sk-' + 'ant-' + 'LEAKED0123456789',
                     completion='{"the":"raw model reply"}',
                     nonsense_field='SHOULD_BE_DROPPED')
_line = c.one()
_rec = json.loads(_line)
chk('the telemetry event is a single JSON line named llm_generation',
    bool(_line) and _rec['event'] == 'llm_generation')
chk('every declared telemetry field is present',
    all(_rec.get(k) is not None for k in (
        'request_id', 'strategy', 'model', 'stages', 'input_tokens',
        'output_tokens', 'stop_reason', 'max_output_tokens', 'duration_ms',
        'estimated_cost_usd')) and _rec.get('truncated') is False
    and _rec.get('success') is True and _rec.get('retries') == 0,
    str(sorted(_rec.keys())))
chk('a passed text= NEVER appears in the telemetry output',
    'secret user description' not in _line and 'text' not in _rec)
chk('neither does a description, a prompt, a key or a raw completion',
    all(x not in _line for x in ('another secret', 'the whole system prompt',
                                 'sk-' + 'ant-' + 'LEAKED0123456789',
                                 'raw model reply')))
chk('an undeclared field is dropped silently rather than logged',
    'nonsense_field' not in _rec and 'SHOULD_BE_DROPPED' not in _line)

# ═══════════════════════════════════════════════════ و) حالة الصحّة ═════════
print('\n── و · حالة الصحّة ──')

_h = L.health_status()
chk('health_status reports the environment', _h.get('env') == L.ENV)
chk('health_status reports the minimum level', _h.get('level') == L.MIN_LEVEL)
chk('health_status reports the stack-trace flag',
    _h.get('stack_traces') is L.STACK_TRACES)
chk('health_status declares the structured contract and the block-list size',
    _h.get('structured') is True
    and _h.get('redacted_fields') == len(L.FORBIDDEN_FIELDS))
_hs = json.dumps(_h, ensure_ascii=False)
chk('health_status carries no secret, no key and no path',
    'sk-' not in _hs and 'Bearer' not in _hs
    and not any(k in _hs.lower() for k in ('api_key', 'authorization', 'token')),
    _hs)

# ═══════════════════════════ ز) الوصل الثابت في طبقة الواجهة (ast) ══════════
print('\n── ز · الوصل الثابت: لا traceback في مسار الطلب ──')

API_SRC = rd('acs_understand_api.py')
API_TREE = ast.parse(API_SRC)


def _calls(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def _attr_calls(tree, obj, attr):
    out = []
    for n in _calls(tree):
        fn = n.func
        if (isinstance(fn, ast.Attribute) and fn.attr == attr
                and isinstance(fn.value, ast.Name) and fn.value.id == obj):
            out.append(n)
    return out


_print_exc = [n for n in _calls(API_TREE)
              if isinstance(n.func, ast.Attribute)
              and n.func.attr in ('print_exc', 'format_exc')]
chk('the request layer calls traceback.print_exc() ZERO times',
    len([n for n in _print_exc if n.func.attr == 'print_exc']) == 0
    and 'traceback.print_exc()' not in API_SRC)
chk('the request layer calls format_exc() ZERO times',
    len([n for n in _print_exc if n.func.attr == 'format_exc']) == 0
    and 'format_exc()' not in API_SRC)

_log_exc = _attr_calls(API_TREE, 'LOG', 'exception')
chk('every failure path logs through LOG.exception (at least four call sites)',
    len(_log_exc) >= 4, str(len(_log_exc)))
chk('each LOG.exception passes the exception object itself, not its text',
    all(len(n.args) >= 2 and not isinstance(n.args[1], ast.JoinedStr)
        for n in _log_exc))

_err_fn = [n for n in ast.walk(API_TREE)
           if isinstance(n, ast.FunctionDef) and n.name == '_error_response']
chk('the single error responder exists exactly once', len(_err_fn) == 1)
if _err_fn:
    _body = _err_fn[0]
    _log_calls = [n for n in _calls(_body)
                  if isinstance(n.func, ast.Attribute)
                  and isinstance(n.func.value, ast.Name) and n.func.value.id == 'LOG']
    _prints = [n for n in _calls(_body)
               if isinstance(n.func, ast.Name) and n.func.id == 'print']
    chk('_error_response logs through the structured logger',
        len(_log_calls) >= 1 and _log_calls[0].func.attr in ('error', 'warn',
                                                             'exception'))
    chk('_error_response does not print', _prints == [])

chk('the structured logger is the one instantiated in the API layer',
    'LOGGING.StructuredLogger(' in API_SRC)

# ══════════════════════ ح) الوصف لا يُطبع في طبقة الفهم (ast) ═══════════════
print('\n── ح · لا طباعة لوصف الزائر في محرّك الفهم ──')

SENSITIVE_NAMES = {'text', 'desc', 'description', 'prompt', 'notes'}
U_SRC = rd('acs_understand.py')
U_TREE = ast.parse(U_SRC)
_parent = {}
for _n in ast.walk(U_TREE):
    for _c in ast.iter_child_nodes(_n):
        _parent[_c] = _n


def _is_length_only(node):
    """`len(text)` طولٌ لا محتوى. أي استعمال آخر للاسم داخل print تسريب."""
    par = _parent.get(node)
    return (isinstance(par, ast.Call) and isinstance(par.func, ast.Name)
            and par.func.id == 'len' and node in par.args)


leaks = []
for node in ast.walk(U_TREE):
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'print'):
        continue
    for arg in list(node.args) + [k.value for k in node.keywords]:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Name) and sub.id in SENSITIVE_NAMES \
                    and not _is_length_only(sub):
                leaks.append('acs_understand.py:%d (%s)' % (sub.lineno, sub.id))

chk('no print() in the understanding engine interpolates the visitor text, '
    'description, prompt or notes', leaks == [], '; '.join(leaks[:6]))
chk('the only permitted mention of those names inside print is their LENGTH',
    any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == 'len' for n in ast.walk(U_TREE)))

_fmt_leaks = []
for node in ast.walk(U_TREE):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == 'print':
        for sub in ast.walk(node):
            if isinstance(sub, ast.JoinedStr):
                for val in ast.walk(sub):
                    if isinstance(val, ast.Name) and val.id in SENSITIVE_NAMES \
                            and not _is_length_only(val):
                        _fmt_leaks.append('acs_understand.py:%d' % val.lineno)
chk('no f-string inside a print carries those names either', _fmt_leaks == [],
    '; '.join(_fmt_leaks[:6]))

# ════════════════════ ط) تليمتري التوليد موصول فعلاً (F-13, تشغيلاً) ════════
print('\n── ط · تليمتري التوليد موصول في محرّك الفهم ──')

import types                                                      # noqa: E402
import acs_understand as U                                        # noqa: E402


class _FakeMsg(object):
    class _B(object):
        def __init__(self, t):
            self.text = t

    class _U(object):
        def __init__(self, i, o):
            self.input_tokens = i
            self.output_tokens = o

    def __init__(self, text, stop='end_turn'):
        self.content = [_FakeMsg._B(text)]
        self.stop_reason = stop
        self.usage = _FakeMsg._U(1200, 900)


class _FakeClient(object):
    def __init__(self, msg):
        self.msg = msg
        self.messages = self

    def stream(self, **kw):
        msg = self.msg

        class _Ctx(object):
            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def get_final_message(s):
                return msg
        return _Ctx()

    def create(self, **kw):
        return self.msg


def _call_with_fake(msg, **kw):
    """ينادي call_llm الحقيقي بعميل مزيّف، ويعيد (سطور السجلّ، النتيجة/الخطأ)."""
    cap = Cap()
    saved_log, saved_mod = U.LOG, sys.modules.get('anthropic')
    saved_key = os.environ.get('ANTHROPIC_API_KEY')
    mod = types.ModuleType('anthropic')
    mod.Anthropic = lambda **k: _FakeClient(msg)
    sys.modules['anthropic'] = mod
    os.environ['ANTHROPIC_API_KEY'] = 'sk-' + 'ant-' + 'fake-for-tests-only-0123456789'
    U.LOG = L.StructuredLogger(stream=cap, min_level='info')
    try:
        try:
            out = U.call_llm('وصف الزائر السرّي: قاعة في حي النرجس', **kw)
        except E.AcsApiError as err:
            out = err
        return cap.lines(), out
    finally:
        U.LOG = saved_log
        if saved_mod is None:
            sys.modules.pop('anthropic', None)
        else:
            sys.modules['anthropic'] = saved_mod
        if saved_key is None:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        else:
            os.environ['ANTHROPIC_API_KEY'] = saved_key


os.environ.pop('ACS_PRICE_INPUT_PER_MTOK', None)
os.environ.pop('ACS_PRICE_OUTPUT_PER_MTOK', None)

_ls, _out = _call_with_fake(_FakeMsg('{"ok": 1}'), btype='warehouse',
                            stage='single', request_id='req_wired',
                            strategy='single')
_gen = [json.loads(x) for x in _ls if '"llm_generation"' in x]
chk('a successful generation call emits exactly one telemetry event',
    len(_gen) == 1, str(len(_ls)))
if _gen:
    g = _gen[0]
    chk('it records the request id passed by the caller, and invents none',
        g.get('request_id') == 'req_wired')
    chk('it records strategy, model, stage, tokens, stop reason and budget',
        g.get('strategy') == 'single' and g.get('model')
        and g.get('stages') == 'single' and g.get('input_tokens') == 1200
        and g.get('output_tokens') == 900 and g.get('stop_reason') == 'end_turn'
        and g.get('max_output_tokens'), json.dumps(g, ensure_ascii=False))
    chk('it records duration, retries, truncation and success',
        isinstance(g.get('duration_ms'), int) and g.get('retries') == 0
        and g.get('truncated') is False and g.get('success') is True)
    chk('NO cost is guessed when pricing is not configured',
        'estimated_cost_usd' not in g)
    chk('the visitor description never reaches the telemetry line',
        'النرجس' not in _ls[0] and 'الزائر' not in ' '.join(_ls))
    chk('nor does the API key or the raw completion',
        ('sk-' + 'ant-' + 'fake') not in ' '.join(_ls) and '{"ok": 1}' not in ' '.join(_ls))

os.environ['ACS_PRICE_INPUT_PER_MTOK'] = '3'
os.environ['ACS_PRICE_OUTPUT_PER_MTOK'] = '15'
_ls, _ = _call_with_fake(_FakeMsg('{"ok": 1}'), btype='warehouse')
_gen = [json.loads(x) for x in _ls if '"llm_generation"' in x]
chk('a cost appears ONLY once the operator declares the pricing',
    len(_gen) == 1 and abs(_gen[0].get('estimated_cost_usd', 0)
                           - (1200 / 1e6 * 3 + 900 / 1e6 * 15)) < 1e-9,
    json.dumps(_gen and _gen[0] or {}))
for _k in ('ACS_PRICE_INPUT_PER_MTOK', 'ACS_PRICE_OUTPUT_PER_MTOK'):
    os.environ[_k] = ''
_ls, _ = _call_with_fake(_FakeMsg('{"ok": 1}'), btype='warehouse')
_gen = [json.loads(x) for x in _ls if '"llm_generation"' in x]
chk('an EMPTY pricing variable means unset — it neither crashes nor prices at zero',
    len(_gen) == 1 and 'estimated_cost_usd' not in _gen[0])
for _k in ('ACS_PRICE_INPUT_PER_MTOK', 'ACS_PRICE_OUTPUT_PER_MTOK'):
    os.environ.pop(_k, None)

_ls, _out = _call_with_fake(_FakeMsg('{"ok": 1}', 'max_tokens'), btype='warehouse',
                            stage='detail')
_gen = [json.loads(x) for x in _ls if '"llm_generation"' in x]
chk('a FAILED generation is recorded too, with its classified code and the '
    'truncation flag',
    len(_gen) == 1 and _gen[0].get('success') is False
    and _gen[0].get('error_code') == E.ACS_UPSTREAM_TRUNCATED
    and _gen[0].get('truncated') is True
    and _gen[0].get('upstream_class') == 'max_tokens',
    json.dumps(_gen and _gen[0] or {}, ensure_ascii=False))
chk('the failure telemetry still carries no description and no raw reply',
    'النرجس' not in ' '.join(_ls) and '{"ok": 1}' not in ' '.join(_ls))

chk('the understanding engine emits through StructuredLogger.generation, '
    'not through print', 'LOG.generation(' in U_SRC
    and 'acs_logging' in U_SRC)

print('\n' + '─' * 62)
print('LOGGING: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
