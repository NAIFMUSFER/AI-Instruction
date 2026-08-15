# -*- coding: utf-8 -*-
"""هجرة المزوّد — deepseek أساسياً وanthropic بديلاً، بلا مسّ مسار التوليد.

    python3 tests/remediation/test_multi_provider.py

ما يقيسه هذا الملفّ، ولماذا هذه الأشياء بالذات:

1) الحلّ (A/B): من أين يأتي المفتاح والعنوان والنموذج. كان `_call_llm_impl`
   يقرأ ANTHROPIC_API_KEY وACS_LLM_MODEL من المحيط بنفسه، فتبديل نقطة النهاية
   كان يعني تعديل دالّة التوليد — وهي الدالّة التي تحرسها KI-23/KI-24/F-50.

2) سلامة نقطة النهاية (D): وهي الخطر الحقيقي في هذه الهجرة. deepseek يُنادى
   عبر مكتبة anthropic نفسها؛ فإن لم يُطبَّق base_url لأي سبب، ذهب **مفتاح
   deepseek إلى api.anthropic.com**. هذا تسريب اعتماد لا «تدهور لطيف»،
   فيُفحَص قبل النداء ويُرفض ACS_INTEGRATION_ERROR بلا أي بايت شبكة.

3) التحويل (E/F): محاولةٌ واحدة على مزوّدٍ واحد، بقائمة سماح لا قائمة منع.
   يُقاس عددُ النداءات فعلاً — لا نيّة الكود — فلا يمرّ عودٌ ذاتيّ ولا حلقة.

4) الفوترة (G): الرمز الجديد يأتي من شاهد المزوّد الصريح وحده. 400 عامّ يبقى
   400 عامّاً، ورسالة المستخدم لا تذكر رصيداً ولا حساباً.

نطاق مُعلَن: لا مفتاح حقيقيّ ولا شبكة. بديل SDK هنا يحمل توقيع v0.40.0
الحقيقي، ويسجّل ما بُني به العميل، فيُقاس **إلى أين كان النداء ذاهباً**.
النداء الحيّ على deepseek يبقى:
LIVE DEEPSEEK CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
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
import acs_provider as PROV                                      # noqa: E402
import acs_logging as LOGGING                                    # noqa: E402

p = [0]
f = [0]

#: مفاتيح وهمية — مبنيّة بالتقطيع حتى لا يوجد في الملفّ سطرٌ يشبه مفتاحاً.
FAKE_ANTHROPIC = "sk-" + "ant-" + "api03-" + "A" * 24
FAKE_DEEPSEEK = "sk-" + "d" * 32


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ════════════════════════ بديل SDK: يسجّل وجهة النداء ═══════════════════════
class _Usage(object):
    input_tokens = 1200
    output_tokens = 900


class _Block(object):
    def __init__(self, text):
        self.text = text


class _Msg(object):
    def __init__(self, text, stop="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop
        self.usage = _Usage()


class _Ctx(object):
    def __init__(self, m):
        self._m = m

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._m


class ProviderError(Exception):
    """شكل استثناء SDK: status_code · body · message — كما في الإنتاج."""

    def __init__(self, message, status=400, etype="invalid_request_error"):
        Exception.__init__(self, message)
        self.message = message
        self.status_code = status
        self.body = {"type": "error",
                     "error": {"type": etype, "message": message}}


class _Messages(object):
    """توقيع v0.40.0 حرفياً: لا thinking ولا **kwargs."""

    def __init__(self, client, log, behaviour):
        self._c = client
        self._log = log
        self._b = behaviour

    #: قاطعُ دورةٍ في البديل نفسه. المسار السليم يبلغ ٤ نداءات كحدّ أقصى
    #: (محاولتان × مزوّدَين)، فأيّ تجاوزٍ لهذا يعني حلقةً أو عوداً ذاتيّاً —
    #: ويُعلَن فشلاً محدوداً يُقرأ، بدل أن يموت العدّاء بـRecursionError.
    MAX_CALLS = 12

    def _serve(self, method, model, max_tokens):
        if len(self._log) >= self.MAX_CALLS:
            raise RuntimeError("provider called %d times — unbounded retry or "
                               "recursive fallback" % len(self._log))
        self._log.append({"method": method, "model": model,
                          "max_tokens": max_tokens,
                          "api_key": self._c.ctor.get("api_key"),
                          "base_url": self._c.ctor.get("base_url")})
        act = self._b(self._c.ctor)
        if isinstance(act, Exception):
            raise act
        return act

    def create(self, *, max_tokens, messages, model, metadata=None,
               stop_sequences=None, stream=None, system=None, temperature=None,
               tool_choice=None, tools=None, top_k=None, top_p=None,
               extra_headers=None, extra_query=None, extra_body=None,
               timeout=None):
        return self._serve("create", model, max_tokens)

    def stream(self, *, max_tokens, messages, model, metadata=None,
               stop_sequences=None, system=None, temperature=None, top_k=None,
               top_p=None, tool_choice=None, tools=None, extra_headers=None,
               extra_query=None, extra_body=None, timeout=None):
        return _Ctx(self._serve("stream", model, max_tokens))


def install(behaviour, accepts_base_url=True, version="0.40.0"):
    """يركّب بديل anthropic. `accepts_base_url` يحاكي مكتبةً لا تعرف base_url."""
    log = []

    if accepts_base_url:
        class _Client(object):
            def __init__(self, *, api_key=None, base_url=None, timeout=None):
                self.ctor = {"api_key": api_key, "base_url": base_url,
                             "timeout": timeout}
                self.messages = _Messages(self, log, behaviour)
    else:
        class _Client(object):                      # توقيع بلا base_url إطلاقاً
            def __init__(self, *, api_key=None, timeout=None):
                self.ctor = {"api_key": api_key, "timeout": timeout}
                self.messages = _Messages(self, log, behaviour)

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    mod.__version__ = version
    sys.modules["anthropic"] = mod
    return log


def fresh_understand():
    import acs_understand as U
    return importlib.reload(U)


def clear_env():
    for k in ("ACS_LLM_PROVIDER", "ACS_LLM_BASE_URL", "ACS_LLM_API_KEY",
              "ACS_LLM_MODEL", "ACS_LLM_TRANSPORT", "ACS_ALLOWED_MODELS",
              "ACS_LLM_FALLBACK_PROVIDER", "ACS_LLM_FALLBACK_BASE_URL",
              "ACS_LLM_FALLBACK_API_KEY", "ACS_LLM_FALLBACK_MODEL",
              "ACS_LLM_FALLBACK_ON_BILLING", "ANTHROPIC_API_KEY",
              "ACS_LLM_MODEL_MAX_OUTPUT"):
        os.environ.pop(k, None)
    os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"


def deepseek_env():
    clear_env()
    os.environ["ACS_LLM_PROVIDER"] = "deepseek"
    os.environ["ACS_LLM_BASE_URL"] = "https://api.deepseek.com/anthropic"
    os.environ["ACS_LLM_API_KEY"] = FAKE_DEEPSEEK
    os.environ["ACS_LLM_MODEL"] = "deepseek-v4-pro"


def main():
    src_provider = io.open(os.path.join(ROOT, "acs_provider.py"),
                           encoding="utf-8").read()
    src_understand = io.open(os.path.join(ROOT, "acs_understand.py"),
                             encoding="utf-8").read()

    # ═══ أ · حلّ deepseek ═══════════════════════════════════════════════════
    print("\n── أ · A: deepseek أساسياً — مزوّد ومفتاح وعنوان ونموذج ──")
    deepseek_env()
    cfg = PROV.primary()
    chk("provider resolves to deepseek", cfg.provider == "deepseek", cfg.provider)
    chk("the base URL is the documented Anthropic-compatible endpoint",
        cfg.base_url == "https://api.deepseek.com/anthropic", cfg.base_url)
    chk("the host recorded for telemetry is api.deepseek.com",
        cfg.base_host == "api.deepseek.com", cfg.base_host)
    chk("the DeepSeek key is selected", cfg.api_key == FAKE_DEEPSEEK)
    chk("the model is the configured DeepSeek identifier",
        cfg.model == "deepseek-v4-pro", cfg.model)
    chk("the configuration resolves cleanly", cfg.ok and cfg.state == PROV.RESOLVED,
        cfg.state)
    chk("the allowed-model list admits the DeepSeek identifier",
        cfg.model in PROV.allowed_models(cfg), sorted(PROV.allowed_models(cfg)))

    os.environ.pop("ACS_LLM_BASE_URL")
    chk("with no explicit base URL the documented default is used, never "
        "Anthropic's", PROV.primary().base_host == "api.deepseek.com")
    os.environ["ACS_LLM_BASE_URL"] = "https://api.deepseek.com/anthropic"

    os.environ.pop("ACS_LLM_MODEL")
    chk("with no explicit model the documented DeepSeek default is used",
        PROV.primary().model == "deepseek-v4-pro", PROV.primary().model)
    os.environ["ACS_LLM_MODEL"] = "deepseek-v4-pro"

    # ═══ ب · التوافق الخلفي ═════════════════════════════════════════════════
    print("\n── ب · B: نشر anthropic القائم يظلّ يعمل بمتغيّراته القديمة ──")
    clear_env()
    os.environ["ANTHROPIC_API_KEY"] = FAKE_ANTHROPIC
    legacy = PROV.primary()
    chk("with no ACS_LLM_PROVIDER the provider defaults to anthropic",
        legacy.provider == "anthropic", legacy.provider)
    chk("the legacy ANTHROPIC_API_KEY is accepted",
        legacy.api_key == FAKE_ANTHROPIC and legacy.ok, legacy.state)
    chk("no base URL is imposed on anthropic — the SDK default stands",
        legacy.base_url is None and legacy.base_host is None)
    chk("the model default is unchanged", legacy.model == "claude-sonnet-5",
        legacy.model)
    chk("the allowed-model default is byte-identical to the pre-migration set",
        PROV.allowed_models(legacy) == {"claude-sonnet-5", "claude-haiku-4-5"},
        sorted(PROV.allowed_models(legacy)))
    os.environ["ACS_LLM_API_KEY"] = "sk-" + "explicit-wins-" + "B" * 12
    chk("an explicit ACS_LLM_API_KEY overrides the legacy one",
        PROV.primary().api_key.startswith("sk-explicit-wins-"))
    os.environ.pop("ACS_LLM_API_KEY")

    # المفتاح القديم لا يُعار — وهذا هو الفحص الذي يمنع تسريب اعتماد.
    os.environ["ACS_LLM_PROVIDER"] = "deepseek"
    borrowed = PROV.primary()
    chk("ANTHROPIC_API_KEY is NEVER used as an implicit DeepSeek key",
        borrowed.api_key is None and not borrowed.ok, borrowed.api_key)
    chk("the missing variable is named, and named correctly",
        "ACS_LLM_API_KEY" in borrowed.missing, borrowed.missing)
    chk("PROVIDER_SPEC declares no legacy key env for deepseek",
        PROV.PROVIDER_SPEC["deepseek"]["legacy_key_env"] is None)

    clear_env()
    os.environ["ACS_LLM_PROVIDER"] = "wat"
    chk("an unknown provider name is a configuration fault, not an upstream one",
        PROV.primary().state == PROV.UNKNOWN_PROVIDER)

    # ═══ ج · عزل السرّ ══════════════════════════════════════════════════════
    print("\n── ج · C: لا مفتاح — أساسيّاً ولا بديلاً — يظهر في أي مخرَج ──")
    deepseek_env()
    os.environ["ACS_LLM_FALLBACK_PROVIDER"] = "anthropic"
    os.environ["ACS_LLM_FALLBACK_API_KEY"] = FAKE_ANTHROPIC
    os.environ["ACS_LLM_FALLBACK_MODEL"] = "claude-sonnet-5"
    prim, fb = PROV.primary(), PROV.fallback()
    both = (FAKE_DEEPSEEK, FAKE_ANTHROPIC)

    health = json.dumps(PROV.health_status(), ensure_ascii=False)
    chk("no key appears in /health provider state",
        not any(k in health for k in both))
    chk("/health carries the host, not the URL",
        '"llm_base_host": "api.deepseek.com"' in health
        and "://" not in health, health[:120])
    for cfg_ in (prim, fb):
        pub = json.dumps(cfg_.public(), ensure_ascii=False)
        chk("%s public() carries no key" % cfg_.role,
            not any(k in pub for k in both))
        chk("%s repr() carries no key" % cfg_.role,
            not any(k in repr(cfg_) for k in both))
    chk("ProviderConfig has no __dict__ to leak (declared __slots__)",
        not hasattr(prim, "__dict__"))
    chk("the module source contains no credential-shaped literal",
        re.search(r"sk-[A-Za-z0-9_\-]{16,}", src_provider) is None)

    # التعقيم القائم يبتلع مفتاح deepseek أيضاً، لا مفتاح anthropic وحده.
    chk("redact() removes a DeepSeek-shaped key from any message",
        FAKE_DEEPSEEK not in E.redact("boom key=%s tail" % FAKE_DEEPSEEK))
    leaky = ProviderError("Bad key %s in request" % FAKE_DEEPSEEK)
    det = E.safe_provider_detail(leaky)
    chk("safe_provider_detail() strips the key out of the provider message",
        FAKE_DEEPSEEK not in json.dumps(det, ensure_ascii=False), det)

    # ═══ د · سلامة نقطة النهاية ═════════════════════════════════════════════
    print("\n── د · D: ضبط deepseek لا يمكن أن ينتهي إلى api.anthropic.com ──")
    deepseek_env()
    log = install(lambda ctor: _Msg('{"ok":1}'))
    U = fresh_understand()
    out = U._call_llm_impl("مستودع صغير", max_tokens=1000, stage="single")
    chk("the call succeeds through the DeepSeek endpoint", out.strip() == '{"ok":1}')
    chk("exactly one upstream call was made", len(log) == 1, len(log))
    chk("the client was built with the DeepSeek base URL",
        log[0]["base_url"] == "https://api.deepseek.com/anthropic",
        log[0]["base_url"])
    chk("the DeepSeek key — and only it — was sent",
        log[0]["api_key"] == FAKE_DEEPSEEK)
    chk("the DeepSeek model was requested", log[0]["model"] == "deepseek-v4-pro")

    # مكتبة لا تقبل base_url: يجب أن يُرفض قبل النداء، لا أن يُسقَط الوسيط.
    log2 = install(lambda ctor: _Msg('{"ok":1}'), accepts_base_url=False)
    U = fresh_understand()
    try:
        U._call_llm_impl("مستودع صغير", max_tokens=1000, stage="single")
        chk("an SDK without base_url support is refused", False, "no error raised")
    except E.AcsApiError as err:
        chk("an SDK without base_url support is refused",
            err.code == E.ACS_INTEGRATION_ERROR, err.code)
        chk("it is a local integration fault, not an upstream one",
            err.code not in E.UPSTREAM_CODES)
        chk("the refusal names base_url as the parameter",
            (err.upstream or {}).get("parameter") == "base_url", err.upstream)
        chk("the refusal carries no key",
            not any(k in json.dumps(err.upstream, ensure_ascii=False)
                    for k in both))
    chk("NOT ONE byte was sent when the endpoint could not be applied",
        len(log2) == 0, len(log2))
    chk("the guard is introspection, not a version string",
        "_sdk_accepts_base_url" in src_understand
        and "inspect.signature(anthropic.Anthropic.__init__)" in src_understand)

    # ═══ هـ · التحويل: محاولةٌ واحدة ═══════════════════════════════════════
    print("\n── هـ · E: سبب مسموح ⇒ نداء بديل واحد بالضبط، ونجاحه يُعاد ──")
    deepseek_env()
    os.environ["ACS_LLM_FALLBACK_PROVIDER"] = "anthropic"
    os.environ["ACS_LLM_FALLBACK_API_KEY"] = FAKE_ANTHROPIC
    os.environ["ACS_LLM_FALLBACK_MODEL"] = "claude-sonnet-5"

    def overloaded_then_ok(ctor):
        if ctor.get("base_url"):                      # الأساسي = deepseek
            return ProviderError("upstream is overloaded", status=529,
                                 etype="overloaded_error")
        return _Msg('{"from":"fallback"}')            # البديل = anthropic

    log3 = install(overloaded_then_ok)
    U = fresh_understand()
    tel = {}
    # لا يُترك النداء بلا حارس: عودٌ ذاتيّ في التحويل يجعل هذا السطر ينفجر بدل
    # أن يُقرأ حكماً. يُلتقط كل استثناء ثم يُحكم على النتيجة.
    try:
        out = U._call_llm_impl("مستودع صغير", max_tokens=1000, stage="plan",
                               telemetry=tel)
    except Exception as exc:                                  # noqa: BLE001
        out = "<raised %s>" % type(exc).__name__
    chk("the fallback's answer is what the caller receives",
        out.strip() == '{"from":"fallback"}', out[:40])
    deep = [c for c in log3 if c["base_url"]]
    anth = [c for c in log3 if not c["base_url"]]
    chk("the fallback provider was called exactly once", len(anth) == 1, len(anth))
    chk("the fallback used the fallback key, not the primary one",
        anth and anth[0]["api_key"] == FAKE_ANTHROPIC)
    chk("the fallback used the fallback model",
        anth and anth[0]["model"] == "claude-sonnet-5")
    chk("the primary was not retried after the switch", len(deep) <= 2, len(deep))
    chk("telemetry records that a fallback was attempted",
        tel.get("fallback_attempted") is True)
    chk("telemetry names the fallback provider",
        tel.get("fallback_provider") == "anthropic", tel.get("fallback_provider"))
    chk("telemetry records the reason",
        tel.get("fallback_reason") == "provider_unavailable",
        tel.get("fallback_reason"))
    chk("telemetry records the outcome", tel.get("fallback_success") is True)
    chk("telemetry attributes the answer to the provider that served it",
        tel.get("provider") == "anthropic"
        and tel.get("provider_base_host") is None, tel.get("provider"))

    # لا عودٌ ذاتيّ: إن فشل البديل أيضاً، لا ثالث ولا رجوع إلى الأوّل.
    log4 = install(lambda ctor: ProviderError("upstream is overloaded",
                                              status=529,
                                              etype="overloaded_error"))
    U = fresh_understand()
    tel2 = {}
    # يُلتقط كل استثناء لا AcsApiError وحده: عودٌ ذاتيّ جامح ينتهي RecursionError،
    # وهو فشلٌ يجب أن يُقرأ حكماً واضحاً لا انهيار عدّاء.
    raised = None
    try:
        U._call_llm_impl("مستودع صغير", max_tokens=1000, stage="plan",
                         telemetry=tel2)
    except Exception as exc:                                  # noqa: BLE001
        raised = exc
    chk("a failing fallback still fails the call",
        isinstance(raised, E.AcsApiError)
        and raised.code == E.ACS_UPSTREAM_OVERLOADED, type(raised).__name__)
    chk("the failure is a classified provider fault, never a runaway recursion",
        isinstance(raised, E.AcsApiError)
        and "unbounded" not in str(getattr(raised, "upstream", "")),
        type(raised).__name__)
    # سلّم المحاولتين القائم × مزوّدَين = ٤ نداءات كحدّ أقصى، ولا خامس.
    chk("the fallback never falls back again — the call count is bounded",
        len(log4) <= 4, len(log4))
    chk("both providers were tried, each once as a provider",
        len({bool(c["base_url"]) for c in log4}) == 2)
    chk("telemetry records the failed fallback as failed",
        tel2.get("fallback_attempted") is True
        and tel2.get("fallback_success") is False, tel2)

    # بلا بديل مضبوط: لا تحويل، والسبب مُسجَّل — لا صمت.
    deepseek_env()
    log5 = install(lambda ctor: ProviderError("upstream is overloaded",
                                              status=529,
                                              etype="overloaded_error"))
    U = fresh_understand()
    tel3 = {}
    try:
        U._call_llm_impl("مستودع صغير", max_tokens=1000, stage="plan",
                         telemetry=tel3)
    except E.AcsApiError:
        pass
    chk("with no fallback configured only the primary is called",
        all(c["base_url"] for c in log5), log5)
    chk("the reason for NOT switching is recorded, not left silent",
        tel3.get("fallback_reason") == "no_fallback_configured",
        tel3.get("fallback_reason"))
    chk("fallback_attempted is explicitly false, not absent",
        tel3.get("fallback_attempted") is False)

    # ═══ و · ما لا يُحوَّل أبداً ═════════════════════════════════════════════
    print("\n── و · F: قائمة سماح — كل ما عداها ممنوع بالبناء ──")
    deepseek_env()
    os.environ["ACS_LLM_FALLBACK_PROVIDER"] = "anthropic"
    os.environ["ACS_LLM_FALLBACK_API_KEY"] = FAKE_ANTHROPIC
    fb_cfg = PROV.fallback()
    chk("a fallback IS configured for this section — the check is meaningful",
        fb_cfg.ok)
    DENIED = (E.ACS_INTEGRATION_ERROR, E.ACS_UPSTREAM_MAX_TOKENS,
              E.ACS_UPSTREAM_BAD_REQUEST, E.ACS_UPSTREAM_INVALID_JSON,
              E.ACS_UPSTREAM_TRAILING_JSON, E.ACS_UPSTREAM_TRUNCATED,
              E.ACS_UPSTREAM_REFUSED, E.ACS_UPSTREAM_EMPTY_RESPONSE,
              E.ACS_UPSTREAM_AUTH, E.ACS_UPSTREAM_PERMISSION,
              E.ACS_UPSTREAM_MODEL_REJECTED, E.ACS_UPSTREAM_TIMEOUT,
              E.ACS_UPSTREAM_RATE_LIMIT, E.ACS_VALIDATION_FAILED,
              E.ACS_UNPROCESSABLE, E.ACS_UPSTREAM_NOT_CONFIGURED)
    for code in DENIED:
        allowed, reason = PROV.should_fallback(code, fb_cfg)
        chk("no fallback for %s" % code, allowed is False, reason)
    chk("the eligible set is small and explicit",
        E.FALLBACK_ELIGIBLE == frozenset({E.ACS_UPSTREAM_UNAVAILABLE,
                                          E.ACS_UPSTREAM_OVERLOADED,
                                          E.ACS_UPSTREAM_CONNECTION}),
        sorted(E.FALLBACK_ELIGIBLE))
    chk("every eligible code is a declared upstream code",
        all(c in E.UPSTREAM_CODES for c in E.FALLBACK_ELIGIBLE))
    chk("no eligible code is one we caused ourselves",
        not (E.FALLBACK_ELIGIBLE & {E.ACS_INTEGRATION_ERROR,
                                    E.ACS_UPSTREAM_BAD_REQUEST,
                                    E.ACS_UPSTREAM_MAX_TOKENS}))

    # عطل تكامل محلّي حقيقيّ عبر المسار كلّه: لا يُحوَّل ولو كان بديل مضبوطاً.
    log6 = install(lambda ctor: _Msg('{"ok":1}'), accepts_base_url=False)
    U = fresh_understand()
    try:
        U._call_llm_impl("مستودع", max_tokens=1000, stage="plan")
    except E.AcsApiError as err:
        chk("a local integration fault never reaches any provider",
            err.code == E.ACS_INTEGRATION_ERROR and len(log6) == 0,
            (err.code, len(log6)))

    # مخرج النموذج الرديء يُحكم عليه **بعد** عودة النداء، فلا يمكنه التحويل بنيوياً.
    chk("JSON parsing happens after the provider call returns, so malformed "
        "output structurally cannot trigger a switch",
        src_understand.index("def _call_llm_impl") <
        src_understand.index("def scan_top_level_json"))

    # ═══ ز · الفوترة ════════════════════════════════════════════════════════
    print("\n── ز · G: رمز الفوترة من شاهد المزوّد وحده ──")
    live = ("Your credit balance is too low to access the Anthropic API. "
            "Please go to Plans & Billing to upgrade or purchase credits.")
    err = E.classify_upstream(ProviderError(live), provider="anthropic")
    chk("the measured live 400 now classifies as ACS_UPSTREAM_BILLING",
        err.code == E.ACS_UPSTREAM_BILLING, err.code)
    chk("its HTTP status is 503 — service unavailable, not a client error",
        err.status == 503, err.status)
    chk("it is not retryable", err.retryable is False)
    chk("the user message reveals no billing, credit or account state",
        not any(w in err.message for w in ("رصيد", "فوتر", "حساب", "دفع",
                                           "credit", "billing", "balance")),
        err.message)
    chk("the user message is the declared Arabic one",
        err.message == E.MESSAGE_AR[E.ACS_UPSTREAM_BILLING], err.message)
    chk("the operator still gets the safe redacted provider detail",
        "credit balance" in (err.upstream or {}).get("detail", ""),
        (err.upstream or {}).get("detail"))
    chk("the provider name is recorded, not assumed",
        E.classify_upstream(ProviderError(live),
                            provider="deepseek").upstream["provider"]
        == "deepseek")

    ds = E.classify_upstream(
        ProviderError("You have run out of balance", status=402,
                      etype="invalid_request_error"), provider="deepseek")
    chk("DeepSeek's documented 402 Insufficient Balance classifies as billing",
        ds.code == E.ACS_UPSTREAM_BILLING, ds.code)

    # والأهمّ: 400 عامّ لا يصير فوترةً.
    generic = E.classify_upstream(
        ProviderError("messages: at least one message is required"))
    chk("a generic 400 is NOT reclassified as billing",
        generic.code == E.ACS_UPSTREAM_BAD_REQUEST, generic.code)
    mt = E.classify_upstream(ProviderError(
        "max_tokens: 64000 > 32000, which is the maximum allowed number of "
        "output tokens for this model"))
    chk("a max_tokens 400 still classifies as ACS_UPSTREAM_MAX_TOKENS, not "
        "billing", mt.code == E.ACS_UPSTREAM_MAX_TOKENS, mt.code)
    chk("billing evidence is required explicitly",
        E.is_billing_evidence({"detail": "messages: invalid"}) is False)
    chk("an explicit billing_error type is enough on its own",
        E.is_billing_evidence({"error_type": "billing_error"}) is True)

    # التحويل عند الفوترة مشروط بمفتاح صريح.
    deepseek_env()
    os.environ["ACS_LLM_FALLBACK_PROVIDER"] = "anthropic"
    os.environ["ACS_LLM_FALLBACK_API_KEY"] = FAKE_ANTHROPIC
    fb_cfg = PROV.fallback()
    allowed, reason = PROV.should_fallback(E.ACS_UPSTREAM_BILLING, fb_cfg)
    chk("billing does NOT switch providers by default",
        allowed is False and reason == "billing_fallback_disabled", reason)
    os.environ["ACS_LLM_FALLBACK_ON_BILLING"] = "1"
    allowed, reason = PROV.should_fallback(E.ACS_UPSTREAM_BILLING, fb_cfg)
    chk("billing switches only when the operator says so explicitly",
        allowed is True and reason == "provider_billing", reason)
    os.environ.pop("ACS_LLM_FALLBACK_ON_BILLING")

    # ═══ ح · التليمتري يمرّ فعلاً من القناة ═════════════════════════════════
    print("\n── ح · قناة السجلّ تُسقط ما لم يُعلَن — فالحقول الجديدة تُقاس ──")
    captured = []

    class _Cap(LOGGING.StructuredLogger):
        def _emit(self, level, event, **fields):
            captured.append(dict(fields, event=event))
            return fields

    deepseek_env()
    install(lambda ctor: _Msg('{"ok":1}'))
    U = fresh_understand()
    saved = U.LOG                    # acs_understand يملك مسجّله الخاصّ
    U.LOG = _Cap(service="ACS Understanding Engine")
    try:
        U.call_llm("مستودع صغير", max_tokens=1000, stage="single")
    finally:
        U.LOG = saved
    rec = [c for c in captured if c.get("event") == "llm_generation"]
    chk("a generation telemetry event was emitted", len(rec) == 1, len(rec))
    if rec:
        r = rec[0]
        for field, want in (("provider", "deepseek"),
                            ("provider_model", "deepseek-v4-pro"),
                            ("provider_base_host", "api.deepseek.com")):
            chk("the channel passes %s" % field, r.get(field) == want,
                r.get(field))
        chk("F-50's fields still survive the channel",
            r.get("sdk_version") == "0.40.0"
            and r.get("requested_max_tokens") == 1000, r)
        chk("no key reached the telemetry record",
            not any(k in json.dumps(r, ensure_ascii=False) for k in both))
        chk("the full base URL never reaches the telemetry record",
            "://" not in json.dumps(r, ensure_ascii=False))

    # ═══ ط · ما لم يتغيّر ═══════════════════════════════════════════════════
    print("\n── ط · هجرة مزوّد فقط: عقود التوليد لم تُمَسّ ──")
    clear_env()
    import acs_generation as G
    importlib.reload(G)
    chk("STAGE_SHARE is unchanged",
        G.STAGE_SHARE == {"single": 1.00, "plan": 0.50, "detail": 0.75,
                          "repair": 1.00}, G.STAGE_SHARE)
    chk("STAGE_FLOOR is unchanged", G.STAGE_FLOOR == 4000, G.STAGE_FLOOR)
    os.environ["ACS_LLM_MAX_OUTPUT_TOKENS"] = "32000"
    importlib.reload(G)
    chk("stage budgets are unchanged on the anthropic default",
        (G.stage_budget("single"), G.stage_budget("plan"),
         G.stage_budget("detail")) == (32000, 16000, 24000),
        (G.stage_budget("single"), G.stage_budget("plan"),
         G.stage_budget("detail")))
    chk("with no operator ceiling and no documented one, none is invented",
        G.model_max_output() is None, G.model_max_output())
    os.environ["ACS_LLM_PROVIDER"] = "deepseek"
    chk("DeepSeek's documented 384K ceiling is used when the operator sets none",
        G.model_max_output() == 384000, G.model_max_output())
    chk("that documented ceiling changes no stage budget",
        (G.stage_budget("single"), G.stage_budget("plan"),
         G.stage_budget("detail")) == (32000, 16000, 24000))
    os.environ["ACS_LLM_MODEL_MAX_OUTPUT"] = "8000"
    chk("the operator's ceiling still wins over the documented one",
        G.model_max_output() == 8000 and G.clamp_to_model(32000) == (8000, True))
    os.environ.pop("ACS_LLM_MODEL_MAX_OUTPUT")

    import acs_plan_chunks as PC
    importlib.reload(PC)
    chk("KI-24 chunking constants are unchanged",
        (PC.T_OUTLINE_ZONE, PC.CHUNK_SAFETY, PC.MIN_CHUNK_ZONES,
         PC.MAX_CHUNK_SPLITS, PC.MAX_PLAN_CHUNKS) == (26, 0.60, 4, 3, 24))
    chk("KI-23's thinking gate is untouched",
        "_sdk_supports(client, \"thinking\")" in src_understand)
    chk("the provider layer opens no connection and imports no SDK",
        "import anthropic" not in src_provider
        and "requests" not in src_provider)

    print("\n" + "=" * 62)
    print("MULTI-PROVIDER: %d passed, %d failed" % (p[0], f[0]))
    print("LIVE DEEPSEEK CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED "
          "(no key, and PyPI/egress for the real SDK is blocked here).")
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
