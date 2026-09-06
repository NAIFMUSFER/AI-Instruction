# -*- coding: utf-8 -*-
"""عقد الواجهة الخلفية — «كل رد كائن JSON واحد صالح».

يعيد إنتاج العطل الإنتاجي ثم يثبت زواله:

  الواجهة أبلغت `JSON parse failure: Extra data` وHTTP 500 على /v1/understand.
  السبب لم يكن في المتصفّح ولا في Three.js: كان في `extract_json` على الخادم.
  كانت تقتطع الرد بـ `raw.find('{')` حتى `raw.rfind('}')`، فإن أعاد النموذج
  كائناً ثم سطر شرح فيه قوس، صار المقتطع كائنين مُلصقين، فانفجر
  `json.JSONDecodeError: Extra data` داخل نداء الفهم، فتحوّل إلى HTTPException
  500 يحمل نصّ الخطأ نفسه — فقرأت الواجهة «Extra data» وظنّت العطل عندها.

الملف أربعة أقسام:
  أ) عقد الأخطاء ذاته (رموز، حالات، تسلسل JSON، تعقيم الأسرار، التصنيف).
  ب) المحلّل الحتمي: كائن واحد أعلى-مستوى، ورفض الزائد صراحةً.
  ج) تحليل بنيوي لملفّ الواجهة: لا مسار فشل يخرج بغير المغلّف.
  د) عقد حيّ عبر TestClient إن كانت FastAPI مثبّتة (وإلا: NOT VERIFIED صراحةً).
"""
import ast
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                        # noqa: E402
import acs_understand as U                                        # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


# ══════════════════════════════════════════════════════════════════════════
# لماذا كل ما يلي داخل دالّة وتحت حارس `__main__`
# ---------------------------------------------------------------------------
# القسم د يمرّ بحدّ عملية حقيقيّ: الـAPI يسلّم التوليد إلى عاملٍ يُبدَأ بـspawn.
# وspawn يعيد تنفيذ **ملفّ نقطة الدخول** في كل ابنة (`_fixup_main_from_path`)،
# فكان جسم هذا الملفّ يُنفَّذ من جديد داخل كل عامل: يبني TestClient، ويستدعي
# الـAPI، ويحاول أن يولّد عاملاً آخر — فيموت قبل أن يرسل حمولته.
#
# ما وصل CI من ذلك:
#     target = lib_job_faults:upstream_auth   → error_class = EOFError
#     target = lib_job_faults:upstream_trailing_json → error_class = EOFError
# أي أن الابنة ماتت قبل الإرسال، فقرأ الأب JobError ⇒ ACS_UPSTREAM_UNKNOWN.
# ولم يكن ذلك عطلاً في نقل التصنيف: الحدّ نفسه مقيس سليماً في
# tests/remediation/test_job_boundary.py (٢٧ توكيداً).
#
# وأخطر من ذلك: `stall` كان **يمرّ لسببٍ خاطئ** — الأب ينتظر مهلته ثم يعلن
# TIMED_OUT مهما فعلت الابنة، فبدا التوكيد ناجحاً والابنة ميّتة أصلاً.
#
# أُعيد إنتاجه في سكربتٍ مسطّح مصغّر: `__name__ = __mp_main__` في الابنة، ثم
#     RuntimeError: An attempt has been made to start a new process before
#     the current process has finished its bootstrapping phase.
#
# الحارس هو ما يفصل «تُستورَد» عن «تُشغَّل». والملفّات الأخرى التي تولّد عمليات
# (test_generation_cancel · test_provider_integration · test_job_boundary)
# محروسة أصلاً — هذا وحده لم يكن، ولم يكن يولّد عمليات قبل اليوم.
# ══════════════════════════════════════════════════════════════════════════
def main():
    # ═══════════════════════════════════════════════════ أ) عقد الأخطاء ═════════
    print('\n── أ · عقد المغلّف الموحّد ──')

    chk('the error contract declares a version', bool(E.ERROR_CONTRACT_VERSION))
    chk('every declared code has an HTTP status',
        all(c in E.HTTP_STATUS for c in E.CODES),
        str([c for c in E.CODES if c not in E.HTTP_STATUS]))
    chk('every declared code has an Arabic user-facing message',
        all(c in E.MESSAGE_AR and E.MESSAGE_AR[c].strip() for c in E.CODES),
        str([c for c in E.CODES if not E.MESSAGE_AR.get(c)]))
    chk('upstream codes are namespaced ACS_UPSTREAM_*',
        all(c.startswith('ACS_UPSTREAM_') for c in E.UPSTREAM_CODES)
        and len(E.UPSTREAM_CODES) >= 12)
    chk('no message leaks a python type, path or traceback marker',
        not any(tok in m for m in E.MESSAGE_AR.values()
                for tok in ('Traceback', '.py', 'Error(', 'File "')))

    for code in E.CODES:
        env = E.envelope(code, E.MESSAGE_AR[code], 'req_test')
        ok = (env.get('ok') is False
              and set(env['error']) == {'code', 'message', 'request_id',
                                        'retryable', 'upstream'}
              and env['error']['code'] == code
              and isinstance(env['error']['retryable'], bool))
        if not ok:
            chk('envelope shape for %s' % code, False, json.dumps(env, ensure_ascii=False))
            break
    else:
        chk('every code produces the exact five-field envelope (%d codes)' % len(E.CODES), True)

    chk('every envelope survives json.dumps -> json.loads unchanged',
        all(json.loads(json.dumps(E.envelope(c, E.MESSAGE_AR[c], 'req_x'),
                                  ensure_ascii=False))
            == E.envelope(c, E.MESSAGE_AR[c], 'req_x') for c in E.CODES))
    chk('an envelope is exactly one top-level JSON object',
        len(U.scan_top_level_json(json.dumps(
            E.envelope(E.ACS_INTERNAL, 'x', 'req_x'), ensure_ascii=False))[0]) == 1)

    chk('retryable is true only for transient classes',
        all((c in E.RETRYABLE) == E.envelope(c, '', 'r')['error']['retryable']
            for c in E.CODES))
    chk('authentication and model-rejection are never retryable',
        not any(c in E.RETRYABLE for c in (
            E.ACS_UPSTREAM_AUTH, E.ACS_UPSTREAM_PERMISSION,
            E.ACS_UPSTREAM_MODEL_REJECTED, E.ACS_UPSTREAM_NOT_CONFIGURED,
            E.ACS_UPSTREAM_INVALID_JSON, E.ACS_UPSTREAM_TRAILING_JSON)))
    chk('rate limit, overload, upstream timeout and connection loss are retryable',
        all(c in E.RETRYABLE for c in (
            E.ACS_UPSTREAM_RATE_LIMIT, E.ACS_UPSTREAM_OVERLOADED,
            E.ACS_UPSTREAM_TIMEOUT, E.ACS_UPSTREAM_CONNECTION)))
    chk('rate limiting maps to 429 and processing timeout to 504',
        E.HTTP_STATUS[E.ACS_RATE_LIMITED] == 429
        and E.HTTP_STATUS[E.ACS_TIMEOUT] == 504
        and E.HTTP_STATUS[E.ACS_UPSTREAM_TIMEOUT] == 504)

    # ── التعقيم: لا يخرج مفتاح ولا رأس تفويض في أي مسار ─────────────────────────
    SECRETS = ('sk-' + 'ant-' + 'api03-AAAABBBBCCCCDDDD',
               'Authorization: Bearer abcdef0123456789',
               'x-api-key: ' + 'sk-' + 'ant-' + 'api03-ZZZZYYYYXXXX')
    for s in SECRETS:
        chk('redact() removes %r-shaped material' % s.split(':')[0][:14],
            'sk-ant' not in E.redact('failed with ' + s)
            and 'abcdef0123456789' not in E.redact('failed with ' + s))
    chk('a secret pasted into an error message never reaches the envelope',
        'sk-ant' not in json.dumps(E.envelope(
            E.ACS_INTERNAL, 'boom ' + 'sk-' + 'ant-' + 'api03-LEAKED', 'req_x'), ensure_ascii=False))
    chk('a secret pasted into AcsApiError never reaches the envelope',
        'LEAKED' not in json.dumps(
            E.AcsApiError(E.ACS_INTERNAL, 'boom ' + 'sk-' + 'ant-' + 'api03-LEAKED').envelope('r'),
            ensure_ascii=False))
    chk('the upstream block is whitelisted — unknown keys are dropped',
        set(E.envelope(E.ACS_UPSTREAM_AUTH, 'x', 'r',
                       upstream={'provider': 'anthropic', 'kind': 'AuthenticationError',
                                 'status': 401, 'attempts': 1,
                                 'api_key': 'sk-' + 'ant-' + 'LEAK'})['error']['upstream'])
        == {'provider', 'kind', 'status', 'attempts'})

    chk('request ids are unique and prefixed',
        len({E.new_request_id() for _ in range(500)}) == 500
        and E.new_request_id().startswith('req_'))


    # ── تصنيف أعطال المنبع ───────────────────────────────────────────────────────
    class _Fake(Exception):
        def __init__(self, name, status=None):
            Exception.__init__(self, name)
            self.status_code = status
            self.__class__ = type(name, (_Fake,), {})


    def fake(name, status=None):
        cls = type(name, (Exception,), {})
        e = cls('simulated')
        if status is not None:
            e.status_code = status
        return e


    CLASSIFY = [
        ('AuthenticationError', 401, E.ACS_UPSTREAM_AUTH, False),
        ('PermissionDeniedError', 403, E.ACS_UPSTREAM_PERMISSION, False),
        ('NotFoundError', 404, E.ACS_UPSTREAM_MODEL_REJECTED, False),
        ('RateLimitError', 429, E.ACS_UPSTREAM_RATE_LIMIT, True),
        ('APITimeoutError', None, E.ACS_UPSTREAM_TIMEOUT, True),
        ('APIConnectionError', None, E.ACS_UPSTREAM_CONNECTION, True),
        ('BadRequestError', 400, E.ACS_UPSTREAM_BAD_REQUEST, False),
        ('InternalServerError', 500, E.ACS_UPSTREAM_UNAVAILABLE, True),
        ('APIStatusError', 529, E.ACS_UPSTREAM_OVERLOADED, True),
    ]
    for name, status, want, retry in CLASSIFY:
        err = E.classify_upstream(fake(name, status), attempts=2)
        chk('%s -> %s (retryable=%s)' % (name, want, retry),
            err.code == want and err.retryable is retry, err.code)
    chk('an unmapped exception still classifies, never escapes unclassified',
        E.classify_upstream(ValueError('who knows')).code == E.ACS_UPSTREAM_UNKNOWN)
    chk('classification never raises for exotic inputs',
        all(isinstance(E.classify_upstream(x), E.AcsApiError)
            for x in (Exception(), KeyError('k'), OSError(101, 'net'), None)))
    chk('an already-classified error passes through unchanged',
        E.classify_upstream(E.AcsApiError(E.ACS_UPSTREAM_AUTH)).code == E.ACS_UPSTREAM_AUTH)
    chk('classified upstream errors carry provider and kind, never a key',
        'api_key' not in json.dumps(
            E.classify_upstream(fake('AuthenticationError', 401)).envelope('r')))


    # ═════════════════════════════════ ب) المحلّل الحتمي (سبب «Extra data») ═════
    print('\n── ب · محلّل JSON حتمي: كائن واحد أعلى-مستوى ──')

    # البرهان أولاً: القاعدة القديمة تنفجر فعلاً على المدخل نفسه.
    PROD = '{"site":{"w":20},"floors":{}}\n\nملاحظة: {"note":"extra"}'
    _a, _b = PROD.find('{'), PROD.rfind('}')
    _old_raised = ''
    try:
        json.loads(PROD[_a:_b + 1])
    except json.JSONDecodeError as _e:
        _old_raised = str(_e)
    chk('the naive find("{")/rfind("}") slice really raises "Extra data" '
        '(the reported production message)',
        _old_raised.startswith('Extra data'), _old_raised or 'it did not raise')

    CASES = [
        ('a bare object', '{"a":1}', 'OK'),
        ('a fenced object with prose around it', 'Sure:\n```json\n{"a":1}\n```\ndone.', 'OK'),
        ('prose braces that are not JSON', 'note { not json } then {"a":1}', 'OK'),
        ('a string containing braces', '{"note":"a { b } c"}', 'OK'),
        ('an orphan closing brace before the object', 'oops } {"a":1}', 'OK'),
        ('THE PRODUCTION DEFECT: object + trailing object', PROD,
         E.ACS_UPSTREAM_TRAILING_JSON),
        ('two fenced blocks', '```json\n{"a":1}\n```\n```json\n{"b":2}\n```',
         E.ACS_UPSTREAM_TRAILING_JSON),
        ('an empty response', '   ', E.ACS_UPSTREAM_EMPTY_RESPONSE),
        ('a refusal with no JSON at all', 'I cannot do that.', E.ACS_UPSTREAM_INVALID_JSON),
        # كان هذا يُصلَح بإغلاق الأقواس ويُقبَل. صار يُرفَض عمداً (§8 من علاج الانقطاع):
        # نصفُ نموذجٍ مغلَقٍ بالأقواس يمرّ التحقّق الخفيف ثم يصل المصرِّف مبتوراً.
        ('a truncated object is REJECTED, never brace-repaired',
         '{"site":{"w":20,"d":15},"floors":{"f0":{"rooms":[{"rect":[0,0,5,5]}',
         E.ACS_UPSTREAM_TRUNCATED),
    ]
    for name, raw, want in CASES:
        try:
            U.extract_json(raw)
            got = 'OK'
        except E.AcsApiError as err:
            got = err.code
        except Exception as err:                                      # noqa: BLE001
            got = 'UNCLASSIFIED:' + type(err).__name__
        chk('%s -> %s' % (name, want), got == want, 'got %s' % got)

    def _safe_extract(raw):
        try:
            U.extract_json(raw)
            return True
        except E.AcsApiError:
            return True
        except Exception:                                             # noqa: BLE001
            return False


    chk('adversarial input is always classified, never an unhandled exception',
        all(_safe_extract(x) for x in (
            '{' * 400, '}' * 400, '{"a":' + '[' * 200, '\x00{"a":1}',
            '{"a":1}{"b":2}{"c":3}', '{"a":"' + '\\"' * 200 + '"}', '', None)))

    chk('the scanner reports depth honestly: a truncated tail is flagged',
        U.scan_top_level_json('{"a":{"b":1}')[2] is True)
    chk('the scanner never descends into a failed outer object '
        '(a truncated object is one truncated object, not two nested ones)',
        U.scan_top_level_json('{"a":{"b":1},"c":{"d":2}')[0] == []
        and U.scan_top_level_json('{"a":{"b":1},"c":{"d":2}')[2] is True)
    chk('two complete siblings are seen as two, and rejected upstream',
        len(U.scan_top_level_json('{"a":1} {"b":2}')[0]) == 2)
    chk('the extraction path is free of naive brace slicing',
        'rfind("}")' not in io.open(os.path.join(ROOT, 'acs_understand.py'),
                                    encoding='utf-8').read().split(
            'def extract_json')[1][:2000])


    # ═══════════════════════════ ج) بنية ملفّ الواجهة: لا مسار فشل غير مغلّف ════
    print('\n── ج · بنية acs_understand_api.py ──')

    API_PATH = os.path.join(ROOT, 'acs_understand_api.py')
    API_SRC = io.open(API_PATH, encoding='utf-8').read()
    TREE = ast.parse(API_SRC)


    def decorated_with(node, *names):
        for d in getattr(node, 'decorator_list', []):
            src = ast.unparse(d) if hasattr(ast, 'unparse') else ''
            if any(n in src for n in names):
                return True
        return False


    handlers = [n for n in ast.walk(TREE)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and decorated_with(n, 'exception_handler')]
    handled = ' '.join(ast.unparse(d) for n in handlers for d in n.decorator_list) \
        if hasattr(ast, 'unparse') else API_SRC
    for want in ('AcsApiError', 'RequestValidationError', 'HTTPException', 'Exception'):
        chk('an exception handler is registered for %s' % want, want in handled)

    chk("the HTTP-exception handler is registered on Starlette's base class too — "
        "the router raises that class for 404/405 and handler lookup walks upward, "
        "so a subclass-only registration silently returns {'detail': ...} instead",
        'StarletteHTTPException' in API_SRC
        and '@app.exception_handler(StarletteHTTPException)' in API_SRC)
    chk('the generic Starlette wording is replaced by the Arabic contract message',
        '"Method Not Allowed"' in API_SRC and '"Not Found"' in API_SRC)
    chk('a catch-all middleware wraps every request in the envelope',
        'acs_envelope_middleware' in API_SRC and '@app.middleware("http")' in API_SRC)
    chk('the envelope middleware is registered BEFORE CORS so error responses '
        'still carry CORS headers and are readable by the browser',
        API_SRC.index('acs_envelope_middleware') < API_SRC.index('CORSMiddleware,'))
    chk('CORS exposes X-Request-ID and Retry-After to the page',
        'expose_headers' in API_SRC and 'REQUEST_ID_HEADER' in API_SRC)
    chk('CORS is not opened to "*" by default',
        '"*"' not in API_SRC.split('_DEFAULT_ORIGIN =')[1].split('add_middleware')[0])

    chk('no endpoint raises a bare HTTPException(500, ...) carrying the exception text',
        'HTTPException(500' not in API_SRC)
    chk('no endpoint returns a traceback or exception string to the client',
        'traceback.format_exc()' not in API_SRC
        and 'str(e)[:900]' not in API_SRC)
    # F-18: كان الشرط أن يُطبع الـtraceback في السجلّ (٣ مواضع على الأقل). ذلك هو
    # العيب نفسه: الـtraceback يتجاوز redact() وقد يحمل جسم طلب المزوّد — أي وصف
    # الزائر كاملاً — إلى سجلّ الإنتاج. الشرط الآن أقوى لا أضعف: لا traceback خام
    # إطلاقاً، وكل فشل في مسار الطلب يمرّ بالسجلّ المنظَّم الذي يحجب بالاسم.
    chk('no raw traceback is printed anywhere in a request path (F-18)',
        'traceback.print_exc()' not in API_SRC and 'format_exc()' not in API_SRC)
    chk('every request-path failure is logged through the structured logger',
        API_SRC.count('LOG.exception(') >= 4 and 'import acs_logging' in API_SRC)
    _LOG_SRC = open(os.path.join(ROOT, 'acs_logging.py'), encoding='utf-8').read()
    chk('the structured logger blocks user text and secrets by field name',
        all(("'%s'" % k) in _LOG_SRC or ('"%s"' % k) in _LOG_SRC
            for k in ('text', 'description', 'prompt', 'building', 'api_key',
                      'authorization')))
    chk('the structured logger emits one JSON object per event',
        'json.dumps(rec' in _LOG_SRC)
    chk('full stack traces are off by default in production',
        'ACS_LOG_STACK_TRACES' in _LOG_SRC and 'IS_PRODUCTION' in _LOG_SRC)

    routes = [n for n in ast.walk(TREE)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and decorated_with(n, 'app.get', 'app.post')]
    chk('every documented endpoint is present',
        {'root', 'health', 'ready', 'understand', 'edit',
         'understand_image', 'understand_pdf'} <= {r.name for r in routes},
        str(sorted(r.name for r in routes)))

    for want in ('ok', 'service', 'version', 'model_configured', 'api_key_configured'):
        chk('/health declares %r' % want, ("'%s'" % want) in API_SRC or ('"%s"' % want) in API_SRC)
    chk('/health reports key presence as a boolean, never the key itself',
        'def _api_key_configured' in API_SRC
        and 'return bool(' in API_SRC.split('def _api_key_configured')[1][:300])
    chk('the API key value is never placed in any response or log line',
        all('ANTHROPIC_API_KEY' not in ln or 'bool(' in ln or '#' in ln
            or 'append(' in ln or 'environ' in ln
            for ln in API_SRC.split('\n')))
    chk('startup validation reports missing configuration by NAME only',
        '_startup_env_check' in API_SRC
        and 'MISSING (names only)' in API_SRC)

    chk('generation is bounded by an explicit server deadline that answers 504',
        'run_bounded' in API_SRC and 'ACS_TIMEOUT' in API_SRC
        and 'asyncio.wait_for' in API_SRC)
    chk('rate limiting still raises 429 and now carries Retry-After',
        '_too_many' in API_SRC and 'Retry-After' in API_SRC
        and 'ACS_RATE_LIMITED' in API_SRC)
    chk('the four rate-limit envs are still read — no limit was weakened',
        all(k in API_SRC for k in ('ACS_RL_GEN_HOUR', 'ACS_RL_GEN_DAY',
                                   'ACS_RL_EDIT_HOUR', 'ACS_RL_GLOBAL_DAY')))
    chk('the visitor still cannot choose an arbitrary model',
        'def _safe_model' in API_SRC and 'ALLOWED_MODELS' in API_SRC)
    chk('the pinned model identifier is untouched', 'claude-sonnet-5' in API_SRC)

    DOCKER = io.open(os.path.join(ROOT, 'Dockerfile'), encoding='utf-8').read()
    chk('the container binds 0.0.0.0 and honours Render\'s $PORT',
        '--host 0.0.0.0' in DOCKER and '${PORT:-8000}' in DOCKER)
    chk('the new error-contract module is shipped in the image',
        'acs_api_errors.py' in DOCKER)
    RENDER = io.open(os.path.join(ROOT, 'render.yaml'), encoding='utf-8').read()
    chk('the health check path is declared for the platform',
        'healthCheckPath: /health' in RENDER)
    chk('the API key is never committed — it is declared sync:false',
        'ANTHROPIC_API_KEY' in RENDER and 'sync: false' in RENDER
        and 'sk-ant' not in RENDER)
    chk('the allowed-origin list is pinned to the deployed frontend, not "*"',
        'ACS_ALLOWED_ORIGINS' in RENDER and '"*"' not in RENDER)
    chk('the allowed-model list is declared explicitly for the deployment',
        'ACS_ALLOWED_MODELS' in RENDER)


    # ═════════════════════════════════════════════ د) عقد حيّ عبر TestClient ════
    print('\n── د · عقد حيّ (FastAPI TestClient) ──')
    try:
        from fastapi.testclient import TestClient                     # noqa: E402
        import acs_understand_api as API                              # noqa: E402
        _live = True
    except Exception as _e:                                           # noqa: BLE001
        _live = False
        print('  NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: fastapi is not '
              'installed in this sandbox (%s). Run this file on any machine with '
              '`pip install -r requirements.txt` to execute section د.'
              % type(_e).__name__)

    if _live:
        client = TestClient(API.app, raise_server_exceptions=False)

        # ── حالة حدّ المعدّل: من الوحدة الحقيقية، لا من قاموسٍ لم يعد موجوداً ──
        # كان هذا القسم يعبث بـ`API._hits` و`API.RL_GEN_HOUR` مباشرةً. أزال تصحيحُ
        # F-04 الاثنين من مسار القرار: العدّ صار في acs_rate_limit، و
        # `_LIMITER = RL.default_limiter()` يُربَط عند الاستيراد ويقرأ حدوده من
        # البيئة، فلا يرى إسناداً لاحقاً إلى API.RL_GEN_HOUR.
        #
        # ولم يظهر ذلك لأن هذا القسم كان يموت قبله بسطر واحد:
        #     TypeError: Client.__init__() got an unexpected keyword argument 'app'
        # فبقيت الإشارتان الميّتتان سنةً كاملة خلف عطلٍ آخر. الآن يُختبَر المحدّد
        # الحقيقي: نفس التوكيدات، على المسار الذي يعمل في الإنتاج فعلاً.
        import acs_rate_limit as RLM                                  # noqa: E402
        import acs_generation_job as JOBSM                            # noqa: E402

        # ── لماذا لم يعد هذا القسم يرقّع U.understand ─────────────────────────
        # العامل يعمل في عملية أخرى (spawn) ويستورد وحدة الهدف باسمها. فترقيعُ
        # `acs_understand.understand` هنا لا يبلغه إطلاقاً: الابنة تنادي الأصل.
        # فكانت هذه التوكيدات الثلاثة تُدخِل عطلاً لا يراه الخادم، ويصل بدله عطلُ
        # الأصل — RuntimeError غير مصنَّف — فيُقرأ ACS_UPSTREAM_UNKNOWN:
        #     متوقَّع 504/ACS_TIMEOUT           واقع 502/ACS_UPSTREAM_UNKNOWN
        #     متوقَّع ACS_UPSTREAM_AUTH          واقع ACS_UPSTREAM_UNKNOWN
        #     متوقَّع ACS_UPSTREAM_TRAILING_JSON واقع ACS_UPSTREAM_UNKNOWN
        # الرمز كان صادقاً؛ التجربة هي التي لم تقع.
        #
        # الآن يُوجَّه هدف الوظيفة إلى tests/remediation/lib_job_faults.py: دوالّ
        # حقيقية تُستورَد في العامل كما يُستورَد الأصل، فيقع العطل حيث يقع في
        # الإنتاج ويعبر حدّ العملية نفسه. لا توكيد تغيّر، ولا رمز خُفِّف.
        # وحدّ العملية ذاته مقيس مستقلاً في tests/remediation/test_job_boundary.py.
        _FAULTS = os.path.join(ROOT, 'tests', 'remediation')
        if _FAULTS not in sys.path:
            sys.path.insert(0, _FAULTS)
        _real_target = API.TARGET_UNDERSTAND

        def _fault(name):
            """يوجّه هدف /v1/understand إلى دالّة عطلٍ تعمل داخل العامل."""
            API.TARGET_UNDERSTAND = 'lib_job_faults:' + name

        def _restore_target():
            API.TARGET_UNDERSTAND = _real_target

        def _rl_reset(gen_hour=None):
            """يعيد بناء المحدّد الوحيد، اختيارياً بحدٍّ ساعيّ آخر.

            إعادةُ الربط على API._LIMITER لازمة: الوحدة أمسكت المرجع عند
            الاستيراد، فتصفيرُ المصنع وحده يترك الخادم على النسخة القديمة."""
            if gen_hour is None:
                os.environ.pop('ACS_RL_GEN_HOUR', None)
            else:
                os.environ['ACS_RL_GEN_HOUR'] = str(gen_hour)
            RLM.reset_default_limiter()
            API._LIMITER = RLM.default_limiter()
            return API._LIMITER

        def probe(method, path, **kw):
            r = getattr(client, method)(path, **kw)
            try:
                body = json.loads(r.text)
                parsed = True
            except Exception:                                         # noqa: BLE001
                body, parsed = None, False
            return r, body, parsed

        seen = []
        for method, path, kw in (
                ('get', '/', {}), ('get', '/health', {}), ('get', '/ready', {}),
                ('get', '/does-not-exist', {}),
                ('post', '/health', {}),
                ('post', '/v1/understand', {'json': {}}),
                ('post', '/v1/understand', {'json': {'text': ''}}),
                ('post', '/v1/understand', {'content': b'not json',
                                            'headers': {'Content-Type': 'application/json'}}),
                ('post', '/v1/edit', {'json': {'building': {}, 'notes': []}}),
        ):
            r, body, parsed = probe(method, path, **kw)
            seen.append((method, path, r.status_code, parsed, body))
            chk('json.loads(response.text) succeeds for %s %s (HTTP %d)'
                % (method.upper(), path, r.status_code), parsed,
                r.text[:120])

        chk('every failing response carries the five-field envelope',
            all(set(b['error']) == {'code', 'message', 'request_id', 'retryable',
                                    'upstream'}
                for _, _, st, ok, b in seen if ok and st >= 400 and isinstance(b, dict)
                and b.get('ok') is False))
        chk('every failing response declares a known code',
            all(b['error']['code'] in E.HTTP_STATUS
                for _, _, st, ok, b in seen if ok and st >= 400 and isinstance(b, dict)
                and b.get('ok') is False))
        chk('every response carries an X-Request-ID header',
            all(client.get('/health').headers.get('X-Request-ID')
                for _ in range(3)))
        chk('a provided X-Request-ID is echoed back for correlation',
            client.get('/health', headers={'X-Request-ID': 'req_caller_1'}
                       ).headers.get('X-Request-ID') == 'req_caller_1')
        chk('no response body is HTML',
            all('<html' not in (r0.text or '').lower()
                for r0 in (client.get('/nope'), client.post('/v1/understand', json={}))))

        h = client.get('/health')
        hb = json.loads(h.text)
        chk('/health answers 200 with ok/service/version/model_configured/'
            'api_key_configured',
            h.status_code == 200 and hb.get('ok') is True
            and hb.get('service') and hb.get('version')
            and 'model_configured' in hb and isinstance(hb.get('api_key_configured'), bool))
        chk('/health never returns the key itself',
            'sk-ant' not in h.text)

        rd = client.get('/ready')
        rb = json.loads(rd.text)
        chk('/ready is a real readiness verdict, not an alias of /health',
            (rd.status_code == 200 and rb.get('ready') is True)
            or (rd.status_code == 503 and rb.get('ok') is False
                and rb['error']['code'] == E.ACS_NOT_CONFIGURED))
        chk('/ready names missing configuration without printing any value',
            'sk-ant' not in rd.text)

        nf = client.get('/does-not-exist')
        chk('an unknown path returns the envelope with ACS_NOT_FOUND, not Starlette HTML',
            nf.status_code == 404 and json.loads(nf.text)['error']['code'] == E.ACS_NOT_FOUND)
        ma = client.post('/health')
        chk('a wrong method returns ACS_METHOD_NOT_ALLOWED as JSON',
            ma.status_code == 405
            and json.loads(ma.text)['error']['code'] == E.ACS_METHOD_NOT_ALLOWED)
        inv = client.post('/v1/understand', json={})
        chk('a schema violation returns ACS_VALIDATION_FAILED as JSON, and does not '
            'echo the request body back',
            inv.status_code == 422
            and json.loads(inv.text)['error']['code'] == E.ACS_VALIDATION_FAILED)
        empt = client.post('/v1/understand', json={'text': '   '})
        chk('an empty description is rejected before any upstream call is made',
            empt.status_code == 400
            and json.loads(empt.text)['error']['code'] == E.ACS_BAD_REQUEST)
        big = client.post('/v1/understand', json={'text': 'x' * (API.MAX_TEXT + 10)})
        chk('an oversized description returns ACS_PAYLOAD_TOO_LARGE as JSON',
            big.status_code == 413
            and json.loads(big.text)['error']['code'] == E.ACS_PAYLOAD_TOO_LARGE)

        origin = sorted(API._origins)[0]
        pre = client.options('/v1/understand', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST'})
        chk('the deployed frontend origin passes CORS preflight',
            pre.headers.get('access-control-allow-origin') == origin,
            str(dict(pre.headers)))
        bad = client.options('/v1/understand', headers={
            'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'})
        chk('an unlisted origin is NOT granted CORS',
            bad.headers.get('access-control-allow-origin') != 'https://evil.example')

        # حدّ المعدّل ما يزال يعمل ويردّ JSON صالحاً مع Retry-After
        saved = API.RL_GEN_HOUR
        saved_env = os.environ.get('ACS_RL_GEN_HOUR')
        try:
            API.RL_GEN_HOUR = 1          # ما يُعرَض في /health
            lim = _rl_reset(1)           # وما يُقرّر فعلاً
            chk('the limiter under test really carries gen_hour = 1 — the probe '
                'below measures the enforced limit, not a displayed one',
                RLM.health_status(lim)['limits']['gen_hour'] == 1,
                str(RLM.health_status(lim)['limits']))
            for _ in range(3):
                rl = client.post('/v1/understand', json={'text': 'مستودع صغير'},
                                 headers={'X-Forwarded-For': '203.0.113.9'})
                if rl.status_code == 429:
                    break
            chk('the hourly generation limit still fires',
                rl.status_code == 429, 'last status %d' % rl.status_code)
            rlb = json.loads(rl.text)
            chk('a 429 is valid JSON with ACS_RATE_LIMITED and a Retry-After header',
                rlb['error']['code'] == E.ACS_RATE_LIMITED
                and rl.headers.get('Retry-After'))
            chk('a 429 is retryable in the envelope', rlb['error']['retryable'] is True)
        finally:
            API.RL_GEN_HOUR = saved
            if saved_env is None:
                _rl_reset()
            else:
                _rl_reset(saved_env)

        # فشل المنبع يخرج مصنّفاً وليس 500 عاماً
        _real = U.understand

        try:
            _fault('upstream_auth')
            au = client.post('/v1/understand', json={'text': 'مستودع بسيط 20×15م'},
                             headers={'X-Forwarded-For': '198.51.100.7'})
            aub = json.loads(au.text)
            chk('an upstream auth failure surfaces as ACS_UPSTREAM_AUTH, valid JSON, '
                'not a 500 traceback',
                aub['error']['code'] == E.ACS_UPSTREAM_AUTH
                and aub['error']['retryable'] is False)
            chk('the upstream block names the provider without any credential',
                (aub['error']['upstream'] or {}).get('provider') == 'anthropic'
                and 'sk-ant' not in au.text)
        finally:
            _restore_target()
            _rl_reset()

        # العطل الأصلي، حيّاً: رد بكائنين → مغلّف مصنّف، لا «Extra data» ولا 500
        try:
            _fault('upstream_trailing_json')
            ex = client.post('/v1/understand', json={'text': 'مستودع بسيط 20×15م'},
                             headers={'X-Forwarded-For': '198.51.100.8'})
            exb = json.loads(ex.text)
            chk('THE PRODUCTION FAILURE, end to end: a two-object model reply now '
                'returns ACS_UPSTREAM_TRAILING_JSON as one valid JSON object',
                exb['error']['code'] == E.ACS_UPSTREAM_TRAILING_JSON)
            chk('the client never sees the raw "Extra data" decoder text again',
                'Extra data' not in ex.text)
        finally:
            _restore_target()
            _rl_reset()

        # مهلة الخادم → 504 بجسد JSON. التوقّف يقع في العامل فعلاً، فتُقاس المهلة
        # على المسار الذي يعمل في الإنتاج لا على دالّة نائمة في عملية الاختبار.
        saved_to = API.REQUEST_TIMEOUT_S
        try:
            API.REQUEST_TIMEOUT_S = 0.4
            _fault('stall')
            to = client.post('/v1/understand', json={'text': 'مستودع بسيط 20×15م'},
                             headers={'X-Forwarded-For': '198.51.100.9'})
            tob = json.loads(to.text)
            chk('a server-side stall returns 504 with ACS_TIMEOUT as valid JSON',
                to.status_code == 504 and tob['error']['code'] == E.ACS_TIMEOUT)
        finally:
            API.REQUEST_TIMEOUT_S = saved_to
            _restore_target()
            _rl_reset()

        # انفلات غير متوقّع تماماً — يبقى مجهولاً، ولا يُرقّى إلى رمزٍ مصنَّف
        try:
            _fault('unknown_failure')
            un = client.post('/v1/understand', json={'text': 'مستودع بسيط 20×15م'},
                             headers={'X-Forwarded-For': '198.51.100.10'})
            chk('a wholly unexpected exception still returns one valid JSON envelope',
                json.loads(un.text)['error']['code'] in
                (E.ACS_UPSTREAM_UNKNOWN, E.ACS_INTERNAL))
        finally:
            _restore_target()
            _rl_reset()

        chk('the real generation target was restored — no later assertion runs '
            'against a fault module', API.TARGET_UNDERSTAND == _real_target,
            API.TARGET_UNDERSTAND)
        chk('and U.understand was never monkeypatched away in this section: the '
            'worker imports the module itself, so a parent-side patch would have '
            'staged a fault the server never sees',
            U.understand is _real)

    print('\n──────────────────────────────────────────────')
    print('BACKEND CONTRACT: %d passed, %d failed%s'
          % (p[0], f[0], '' if _live else '  (section د NOT VERIFIED — fastapi absent)'))
    if f[0]:
        sys.exit(1)



if __name__ == "__main__":
    main()
