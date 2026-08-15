# -*- coding: utf-8 -*-
"""F-31…F-34 — مسار نداء المزوّد: عطلٌ محلّي لا يُنسب إلى المزوّد.

    python3 tests/remediation/test_provider_integration.py

العطل الإنتاجي الذي يثبّته هذا الملفّ
------------------------------------
سجلّ Render، الطلب POST /v1/understand → 502:

    [ACS-PLAN] class=LARGE est_out=34437 zones=51 budget=32000 -> staged
    [ACS-DEEP] نوع المبنى: warehouse
    [ACS-LLM] call failed (max_tokens=16000, thinking=off) -> ACS_UPSTREAM_UNKNOWN
    {"event":"llm_generation","success":false,"upstream_class":"TypeError",
     "duration_ms":389}
    {"event":"generation_job","state":"FAILED","error_class":"AcsApiError"}
    {"error_code":"ACS_UPSTREAM_UNKNOWN","upstream_class":"JobError","status":502}

ثلاثة أعطال متراكبة:

  ١ (F-31) `thinking={"type":"disabled"}` يُرسَل إلى anthropic==0.40 المثبّتة
    في requirements.txt. توقيع تلك النسخة keyword-only صريح **بلا** وسيط
    باسم thinking و**بلا** ‎**kwargs‎ (المصدر: anthropic-sdk-python @ v0.40.0،
    ‏src/anthropic/resources/messages.py). فترفع بايثون TypeError عند ربط
    الوسائط — قبل أي بايت شبكة. الرقم 389ms في التليمتري هو أثر ذلك: لا رحلة
    شبكة أصلاً.

  ٢ (F-32) `except (AttributeError, TypeError)` كان يعيد إرسال **نفس** الوسائط
    إلى create(). الاستثناء كُتب لحالة «مكتبة قديمة بلا stream()»، لكنه ابتلع
    خطأ الوسائط أيضاً فكرّر فشلاً مضموناً ومحا أثر السبب.

  ٣ (F-33/F-34) TypeError محلّي صُنِّف ACS_UPSTREAM_UNKNOWN (502، «عطل غير
    مصنّف من مزوّد النموذج»)، ثم سُحق التصنيف مرّة أخرى عند حدّ العملية:
    الابنة كانت تشحن (اسم الصنف، النصّ) فقط، فيصير كل شيء JobError عند الأب،
    ويعيد classify_upstream تصنيفه باسم صنف لا يعرفه أي جدول.

لماذا لم تكشفه الحزم القائمة
----------------------------
البدائل المستعملة في tests/phase9_2/test_generation_budget.py و
tests/remediation/test_logging.py تعرّف `create(self, **kw)` و`stream(self, **kw)`.
البديل الذي يقبل **أي** وسيط لا يمكنه أن يكشف عدم تطابق توقيع. البديل هنا
ينسخ توقيع v0.40.0 حرفياً، فالخطأ الذي يظهر ترفعه بايثون نفسها لا شيفرة هذا
الملفّ — ولو أضاف أحدٌ الوسيط إلى التوقيع (أي رفع النسخة) اختفى من تلقائه.

النطاق: لا شبكة ولا مفتاح في هذا الصندوق. نداء مزوّد حيّ =
NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
"""
import importlib
import io
import json
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                       # noqa: E402
import acs_generation_job as JOBS                                # noqa: E402

p = [0]
f = [0]



def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ════════════════════════ بديل SDK بتوقيع حقيقيّ ════════════════════════════
class _Usage(object):
    def __init__(self, i=1200, o=900):
        self.input_tokens = i
        self.output_tokens = o


class _Block(object):
    def __init__(self, text):
        self.text = text


class _Msg(object):
    def __init__(self, text, stop="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop
        self.usage = _Usage()


class _Ctx(object):
    def __init__(self, msg):
        self._m = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._m


class Messages040(object):
    """التوقيع منسوخ حرفياً من anthropic v0.40.0 — لا thinking، ولا **kwargs."""

    def __init__(self, sink, script):
        self._sink = sink
        self._script = script

    def _next(self):
        return self._script.pop(0) if self._script else _Msg('{"ok":1}')

    def create(self, *, max_tokens, messages, model,
               metadata=None, stop_sequences=None, stream=None, system=None,
               temperature=None, tool_choice=None, tools=None, top_k=None,
               top_p=None, extra_headers=None, extra_query=None,
               extra_body=None, timeout=None):
        self._sink.append({"method": "create", "model": model,
                           "max_tokens": max_tokens})
        return self._next()

    def stream(self, *, max_tokens, messages, model,
               metadata=None, stop_sequences=None, system=None,
               temperature=None, top_k=None, top_p=None, tool_choice=None,
               tools=None, extra_headers=None, extra_query=None,
               extra_body=None, timeout=None):
        self._sink.append({"method": "stream", "model": model,
                           "max_tokens": max_tokens})
        return _Ctx(self._next())


class Messages047(Messages040):
    """نسخة تعرف thinking (أُضيف بعد 0.40؛ موجود في v0.47.0)."""

    def create(self, *, thinking=None, **kw):
        self._sink.append({"method": "create", "thinking": thinking,
                           "model": kw.get("model"),
                           "max_tokens": kw.get("max_tokens")})
        return self._next()

    def stream(self, *, thinking=None, **kw):
        self._sink.append({"method": "stream", "thinking": thinking,
                           "model": kw.get("model"),
                           "max_tokens": kw.get("max_tokens")})
        return _Ctx(self._next())


class MessagesNoStream(Messages040):
    """مكتبة قديمة بلا stream() إطلاقاً — الحالة التي كُتب لها الرجوع."""

    stream = property(lambda self: (_ for _ in ()).throw(
        AttributeError("'Messages' object has no attribute 'stream'")))


class MessagesRejectsUnknown(Messages040):
    """توقيع يرفض وسيطاً آخر — للتأكّد أن التصنيف عامّ لا مخصَّص لـthinking."""

    def create(self, *, max_tokens, messages, model, system=None,
               timeout=None):
        self._sink.append({"method": "create"})
        return self._next()

    def stream(self, *, max_tokens, messages, model, system=None,
               timeout=None):
        self._sink.append({"method": "stream"})
        return _Ctx(self._next())


def install(messages_cls, script=None, version="0.40.0"):
    """يركّب بديل anthropic ويعيد (سجلّ النداءات، الوحدة)."""
    sink = []

    class _Client(object):
        def __init__(self, **kw):
            self.messages = messages_cls(sink, list(script or []))
            self.ctor_kwargs = kw

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    mod.__version__ = version
    sys.modules["anthropic"] = mod
    return sink, mod


def fresh_understand():
    """يعيد تحميل acs_understand بعد تركيب البديل — لا حالة عالقة."""
    import acs_understand as U
    return importlib.reload(U)


_saved_key = os.environ.get("ANTHROPIC_API_KEY")
os.environ["ANTHROPIC_API_KEY"] = "sk-" + "ant-" + "fake-for-tests-only"
os.environ.setdefault("ACS_LLM_MODEL", "claude-sonnet-5")
os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"        # لا نوم في الاختبار

def main():
    """كل الجسم التنفيذي داخل دالّة — عرف tests/remediation/
    test_generation_cancel.py نفسه. spawn يعيد استيراد __main__ في كل
    عملية ابنة؛ لو كان الجسم في نطاق الوحدة لأُعيد تنفيذ الحزمة كلّها
    داخل الطفل (أو مات الطفل عند حارس خروج)، فلا يصل الهدف أصلاً.
    """
    DESC = "مستودع 100×60 فيه ستة عمال ورافعة شوكية"


    # ═══════════════ أ · إعادة إنتاج العطل الإنتاجي بالتوقيع الحقيقي ════════════
    print("\n== أ · التوقيع الحقيقي لـanthropic==0.40 (المثبّتة في requirements.txt) ==")

    sink, mod = install(Messages040)
    U = fresh_understand()

    chk("requirements.txt ما زال يثبّت النسخة التي كُتب لها هذا الاختبار",
        "anthropic==0.40" in io.open(os.path.join(ROOT, "requirements.txt"),
                                     encoding="utf-8").read())

    # البديل نفسه يجب أن يرفض thinking — وإلّا لكان الاختبار عبثياً
    _raw = None
    try:
        mod.Anthropic().messages.stream(model="m", max_tokens=1, system="s",
                                        messages=[], thinking={"type": "disabled"})
    except TypeError as exc:
        _raw = exc
    chk("البديل يرفض thinking كما ترفضه النسخة الحقيقية (الاختبار غير عبثيّ)",
        _raw is not None and "unexpected keyword argument 'thinking'" in str(_raw),
        str(_raw))
    chk("والرفض من ربط الوسائط في بايثون لا من منطق مكتوب في البديل",
        _raw is not None and type(_raw) is TypeError)

    # الفحص الجوهري: هل يمرّ النداء الآن؟
    out = None
    err = None
    try:
        out = U._call_llm_impl(DESC, model="claude-sonnet-5", max_tokens=16000,
                               stage="plan")
    except BaseException as exc:                                      # noqa: BLE001
        err = exc
    chk("نداء /v1/understand ينجح على النسخة المثبّتة (كان يفشل TypeError)",
        err is None and out is not None,
        "%s: %s" % (type(err).__name__, str(err)[:120]) if err else "")
    chk("ولم يُرسَل thinking إلى نسخة لا تعرفه",
        all("thinking" not in c for c in sink), json.dumps(sink[:2]))
    chk("والنداء سلك مسار البثّ (stream) لا الرجوع الاحتياطي",
        bool(sink) and sink[0]["method"] == "stream", json.dumps(sink[:1]))
    chk("واسم النموذج وصل كما هو بلا ترجمة",
        bool(sink) and sink[0]["model"] == "claude-sonnet-5", json.dumps(sink[:1]))
    chk("وميزانية المرحلة وصلت كما طُلبت",
        bool(sink) and sink[0]["max_tokens"] == 16000, json.dumps(sink[:1]))


    # ═══════════════ ب · النسخة التي تعرف thinking لا تفقد السلوك ═══════════════
    print("\n== ب · على نسخة تعرف thinking يُرسَل صراحةً (لا فقدان سلوك) ==")

    sink, mod = install(Messages047, version="0.47.0")
    U = fresh_understand()
    err = None
    try:
        U._call_llm_impl(DESC, model="claude-sonnet-5", max_tokens=16000,
                         stage="plan")
    except BaseException as exc:                                      # noqa: BLE001
        err = exc
    chk("النداء ينجح على النسخة الأحدث أيضاً", err is None,
        "%s: %s" % (type(err).__name__, str(err)[:120]) if err else "")
    chk("و thinking أُرسل بقيمة disabled صراحةً",
        bool(sink) and sink[0].get("thinking") == {"type": "disabled"},
        json.dumps(sink[:1]))
    chk("الاستبطان يميّز النسختين فعلاً",
        U._sdk_supports(mod.Anthropic(), "thinking") is True)
    sink040, mod040 = install(Messages040)
    chk("ويقول لا عن النسخة القديمة",
        U._sdk_supports(mod040.Anthropic(), "thinking") is False)


    # ═══════════════ ج · مكتبة بلا stream() — الرجوع المشروع وحده ═══════════════
    print("\n== ج · مكتبة قديمة بلا stream(): الرجوع إلى create() ما زال يعمل ==")

    sink, mod = install(MessagesNoStream)
    U = fresh_understand()
    err = None
    try:
        U._call_llm_impl(DESC, model="claude-sonnet-5", max_tokens=16000,
                         stage="plan")
    except BaseException as exc:                                      # noqa: BLE001
        err = exc
    chk("AttributeError وحده يفتح مسار create() الاحتياطي", err is None,
        "%s: %s" % (type(err).__name__, str(err)[:120]) if err else "")
    chk("والنداء وصل create() فعلاً",
        bool(sink) and sink[-1]["method"] == "create", json.dumps(sink[-1:]))


    # ═══════════════ د · وسيط SDK غير صالح ⇒ تصنيف محلّي حتميّ ══════════════════
    print("\n== د · وسيط لا تعرفه المكتبة ⇒ ACS_INTEGRATION_ERROR لا عطل مزوّد ==")

    sink, mod = install(MessagesRejectsUnknown)
    U = fresh_understand()
    # نحقن وسيطاً لا يعرفه التوقيع، بنفس الطريقة التي كان يفعلها thinking:
    # نجبر الاستبطان على «نعم» فيُرسَل الوسيط ويفشل الربط. هذا يحاكي الصنف كلّه
    # (أي وسيط مستقبليّ) لا حالة thinking وحدها.
    _real_supports = U._sdk_supports
    U._sdk_supports = lambda client, param: True
    err = None
    try:
        U._call_llm_impl(DESC, model="claude-sonnet-5", max_tokens=16000,
                         stage="plan")
    except BaseException as exc:                                      # noqa: BLE001
        err = exc
    U._sdk_supports = _real_supports

    chk("العطل مصنَّف AcsApiError لا استثناء خام",
        isinstance(err, E.AcsApiError), "%s" % type(err).__name__)
    if isinstance(err, E.AcsApiError):
        up = err.upstream if isinstance(err.upstream, dict) else {}
        chk("الرمز ACS_INTEGRATION_ERROR", err.code == E.ACS_INTEGRATION_ERROR,
            err.code)
        chk("وليس أي رمز من عائلة ACS_UPSTREAM_* — العطل ليس عند المزوّد",
            err.code not in E.UPSTREAM_CODES, err.code)
        chk("والحالة 500 لا 502", E.HTTP_STATUS[err.code] == 500,
            str(E.HTTP_STATUS.get(err.code)))
        chk("وغير قابل لإعادة المحاولة — التكرار لا يصلح خطأ برمجيّاً",
            err.retryable is False)
        chk("والتليمتري يسمّي الجهة: fault=local_integration",
            up.get("fault") == "local_integration", json.dumps(up, ensure_ascii=False))
        chk("ويسمّي الوسيط المخالف بالضبط",
            up.get("parameter") == "thinking", json.dumps(up, ensure_ascii=False))
        chk("ويسجّل نسخة الـSDK المثبّتة",
            up.get("sdk_version") == "0.40.0", json.dumps(up, ensure_ascii=False))
        chk("ورسالة العميل تقول إن العطل ليس لديه ولا عند المزوّد",
            "ليس عطلاً في طلبك" in err.message, err.message[:80])

    # الضابط السالب: العطل الحقيقيّ من المزوّد يبقى upstream
    print("\n   ضابط سالب — عطل مزوّد حقيقيّ يبقى مصنَّفاً عطل مزوّد:")


    class _RateLimitError(Exception):
        status_code = 429


    class _APITimeoutError(Exception):
        pass


    for exc_obj, want in ((_RateLimitError("429 rate limited"),
                           E.ACS_UPSTREAM_RATE_LIMIT),
                          (_APITimeoutError("request timed out"),
                           E.ACS_UPSTREAM_TIMEOUT),
                          (TypeError("unsupported operand type(s) for +: int, str"),
                           E.ACS_UPSTREAM_UNKNOWN)):
        got = U._classify_call_error(exc_obj, attempts=1, sdk_version="0.40.0")
        chk("   %-34s ⇒ %s" % (type(exc_obj).__name__ + " " + str(exc_obj)[:18],
                               want), got.code == want, got.code)


    # ═══════════════ هـ · حدّ العملية يحفظ التصنيف ══════════════════════════════
    print("\n== هـ · حدّ العملية لا يسحق التصنيف (F-34) ==")

    chk("الابنة تشحن رمز التصنيف مع الخطأ",
        JOBS._classified_payload(
            E.AcsApiError(E.ACS_INTEGRATION_ERROR))["acs_code"]
        == E.ACS_INTEGRATION_ERROR)
    chk("ولا تشحن شيئاً لخطأ غير مصنَّف", JOBS._classified_payload(ValueError("x")) is None)
    chk("والأب يقبل الشكل القديم (اسم، نصّ) بلا انكسار",
        JOBS._unpack_err(("ValueError", "boom")) == ("ValueError", "boom", None))

    _re = None
    try:
        JOBS._reraise_classified({"acs_code": E.ACS_INTEGRATION_ERROR,
                                  "message": "m", "retryable": False,
                                  "upstream": {"fault": "local_integration"}})
    except E.AcsApiError as exc:
        _re = exc
    chk("الأب يعيد رفع نفس الرمز لا JobError",
        _re is not None and _re.code == E.ACS_INTEGRATION_ERROR,
        getattr(_re, "code", None))
    chk("ويحفظ مغلّف upstream الوصفيّ",
        _re is not None and (_re.upstream or {}).get("fault") == "local_integration")

    _none = JOBS._reraise_classified({"acs_code": "ACS_NOT_A_REAL_CODE"})
    chk("ورمزٌ غير معلن يُهمَل بدل أن يُحقَن", _none is None)

    # الرحلة كاملة عبر عملية ابنة حقيقية (spawn). الهدف داخل acs_generation_job
    # نفسه — نفس عرف tests/remediation/test_generation_cancel.py: وحدة يستوردها
    # الطفل بلا حيلة تحزيم.
    runner = JOBS.JobRunner(capacity=2, executor="process", start_method="spawn")
    seen = {}
    crossed = None
    try:
        runner.run("acs_generation_job:_boom_classified", {}, timeout_s=90,
                   on_event=lambda j: seen.update(j.snapshot()))
    except BaseException as exc:                                      # noqa: BLE001
        crossed = exc
    chk("عبر عملية ابنة حقيقية (spawn): الرمز يصل الأب كما هو",
        isinstance(crossed, E.AcsApiError)
        and crossed.code == E.ACS_INTEGRATION_ERROR,
        "%s: %s" % (type(crossed).__name__, getattr(crossed, "code", "")))
    chk("ولم يتحوّل إلى JobError", not isinstance(crossed, JOBS.JobError))
    chk("ومغلّف upstream عبر الأنبوب سليم",
        isinstance(crossed, E.AcsApiError)
        and (crossed.upstream or {}).get("parameter") == "thinking",
        json.dumps(getattr(crossed, "upstream", None), ensure_ascii=False))
    chk("وسجلّ المهمّة يحمل الرمز لا اسم الصنف وحده",
        seen.get("error_code") == E.ACS_INTEGRATION_ERROR,
        json.dumps({k: seen.get(k) for k in ("error_class", "error_code")}))

    # نفس الشيء على منفّذ الخيط — المسار الثاني في الملفّ نفسه
    tr = JOBS.JobRunner(capacity=2, executor="thread")
    crossed_t = None
    try:
        tr.run("acs_generation_job:_boom_classified", {}, timeout_s=30)
    except BaseException as exc:                                      # noqa: BLE001
        crossed_t = exc
    chk("ومنفّذ الخيط يحفظ التصنيف أيضاً (لا مسار يتخلّف)",
        isinstance(crossed_t, E.AcsApiError)
        and crossed_t.code == E.ACS_INTEGRATION_ERROR,
        "%s: %s" % (type(crossed_t).__name__, getattr(crossed_t, "code", "")))

    # عطل غير مصنَّف يبقى JobError كما كان — لا تغيير في السلوك القائم
    plain = None
    try:
        runner.run("acs_generation_job:_boom", {}, timeout_s=90)
    except BaseException as exc:                                      # noqa: BLE001
        plain = exc
    chk("والعطل غير المصنَّف يبقى JobError كما كان (لا سلوك تغيّر بلا داعٍ)",
        isinstance(plain, JOBS.JobError), type(plain).__name__)

    # ولو أعاد الأب تصنيفه بالطريقة القديمة لصار 502 — نثبت الفارق
    _old_way = E.classify_upstream(JOBS.JobError("worker failed", "AcsApiError"))
    chk("الطريق القديم كان يعطي ACS_UPSTREAM_UNKNOWN — الفارق مقيس",
        _old_way.code == E.ACS_UPSTREAM_UNKNOWN
        and E.HTTP_STATUS[_old_way.code] == 502, _old_way.code)


    # ═══════════════ و · المسار المرحلي (staged) كما في السجلّ ══════════════════
    print("\n== و · المسار المرحلي — نفس التصنيف الذي أنتج العطل الإنتاجي ==")

    import acs_generation as G                                        # noqa: E402
    plan = G.plan_strategy("warehouse", DESC, 100.0, 60.0, 1)
    chk("الطلب الإنتاجي ما زال يُصنَّف مساراً مرحلياً",
        isinstance(plan, dict) and (plan.get("strategy") or "").upper().find("STAG") >= 0,
        json.dumps({k: plan.get(k) for k in ("strategy", "size_class", "zones")},
                   ensure_ascii=False) if isinstance(plan, dict) else str(plan)[:120])

    sink, mod = install(Messages040)
    U = fresh_understand()
    _stage_calls = []
    _real = U._call_llm_impl


    def _spy(*a, **kw):
        _stage_calls.append(kw.get("stage"))
        return _real(*a, **kw)


    U._call_llm_impl = _spy
    err = None
    try:
        U.call_llm(DESC, model="claude-sonnet-5",
                   max_tokens=G.stage_budget("plan"), stage="plan")
    except BaseException as exc:                                      # noqa: BLE001
        err = exc
    U._call_llm_impl = _real
    chk("مرحلة الخطّة تصل المزوّد بلا TypeError", err is None,
        "%s: %s" % (type(err).__name__, str(err)[:120]) if err else "")
    chk("وسُجّلت باسم المرحلة الصحيح", _stage_calls == ["plan"], str(_stage_calls))


    # ═══════════════ ز · لا تسريب: لا مفتاح ولا توجيه ولا رد خام ════════════════
    print("\n== ز · التليمتري والسجلّ: صفر تسريب ==")

    SECRET = "sk-" + "ant-" + "SUPERSECRET0123456789"
    PROMPT_MARK = "علامة-نصّ-التوجيه-السرّية"
    os.environ["ANTHROPIC_API_KEY"] = SECRET

    sink, mod = install(Messages040, script=[_Msg('{"leaked":"' + PROMPT_MARK + '"}')])
    U = fresh_understand()

    import acs_logging as LOGGING                                     # noqa: E402

    buf = io.StringIO()
    _stdout = sys.stdout
    sys.stdout = buf
    try:
        tel = {}
        U._call_llm_impl(DESC + " " + PROMPT_MARK, model="claude-sonnet-5",
                         max_tokens=16000, stage="plan", telemetry=tel)
    except BaseException:                                             # noqa: BLE001
        pass
    finally:
        sys.stdout = _stdout
    printed = buf.getvalue()

    chk("لا مفتاح في المخرجات المطبوعة", SECRET not in printed)
    chk("ولا جزء منه", SECRET[8:24] not in printed)
    chk("لا نصّ توجيه المستخدم في المخرجات", PROMPT_MARK not in printed)
    tel_blob = json.dumps(tel, ensure_ascii=False, default=str)
    chk("لا مفتاح في التليمتري", SECRET not in tel_blob)
    chk("ولا نصّ توجيه ولا رد خام في التليمتري", PROMPT_MARK not in tel_blob,
        tel_blob[:160])
    chk("التليمتري يحمل ما هو آمن ومفيد فقط",
        tel.get("model") == "claude-sonnet-5" and tel.get("sdk_version") == "0.40.0"
        and "stop_reason" in tel, tel_blob[:200])

    # التصنيف المحلّي نفسه لا يسرّب شيئاً
    err_local = U._classify_call_error(
        TypeError("create() got an unexpected keyword argument 'thinking'"),
        attempts=1, sdk_version="0.40.0")
    blob = json.dumps({"m": err_local.message, "u": err_local.upstream},
                      ensure_ascii=False, default=str)
    chk("مغلّف العطل المحلّي بلا مفتاح وبلا توجيه",
        SECRET not in blob and PROMPT_MARK not in blob)
    chk("ولا يحمل أثر استدعاء", "Traceback" not in blob and "File \"" not in blob)
    chk("ويحمل اسم الوسيط وحده كمعرّف برمجيّ",
        err_local.upstream.get("parameter") == "thinking")

    if _saved_key is None:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    else:
        os.environ["ANTHROPIC_API_KEY"] = _saved_key


    # ═══════════════ ح · حارس ساكن: لا وسيط غير مفحوص في مسار النداء ════════════
    print("\n== ح · حارس ساكن على شيفرة المسار ==")

    SRC = io.open(os.path.join(ROOT, "acs_understand.py"), encoding="utf-8").read()
    chk("الرجوع إلى create() لم يعد يبتلع TypeError",
        "except (AttributeError, TypeError):" not in SRC)
    chk("و AttributeError وحده هو ما يفتحه", "except AttributeError:" in SRC)
    chk("و thinking مشروط بدعم النسخة المثبّتة",
        re.search(r"if thinking is not None and supports_thinking", SRC) is not None)
    _calls = len(re.findall(r"supports_thinking\s*=\s*_sdk_supports\(", SRC))
    chk("والاستبطان يُسأل مرّة واحدة قبل الحلقة لا داخل كل محاولة",
        _calls == 1 and SRC.index("supports_thinking =") < SRC.index("def _call("),
        str(_calls))
    chk("ولا يزال التصنيف يمرّ عبر _classify_call_error لا classify_upstream مباشرةً",
        "_classify_call_error(e, attempts=tried" in SRC)

    print("\n" + "─" * 62)
    print("LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED "
          "(no network, no ANTHROPIC_API_KEY in this sandbox)")
    print("PROVIDER INTEGRATION: %d passed, %d failed" % (p[0], f[0]))
    if f[0]:
        sys.exit(1)



if __name__ == "__main__":
    main()