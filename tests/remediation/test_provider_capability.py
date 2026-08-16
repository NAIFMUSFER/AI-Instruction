# -*- coding: utf-8 -*-
"""W2-B/W2-C/W2-E — قدرة المزوّد المُعلَنة، التوجيه والتقطيع، ودلالة الرد.

    python3 tests/remediation/test_provider_capability.py

الدليل الحيّ الذي بُني عليه هذا الملفّ (الإنتاج، SHA 681ec04)
-------------------------------------------------------------
    single  end_turn    out_chars=6917   out_tokens=13945  cpt=0.4960  ✓ 3D
    single  end_turn    out_chars=20463  out_tokens=31022  cpt=0.6596  ✓ 3D
    single  max_tokens  out_chars=18982  out_tokens=32000  cpt=0.5932  TRUNCATED
    plan    max_tokens  out_chars=0      out_tokens=16000  cpt=0.0
            blocks=1  types=thinking:1  text_blocks=0  nontext_blocks=1
            retry_skipped_reason=identical_request → 502 EMPTY_RESPONSE

النداء الأخير يحسم ثلاث مسائل دفعةً واحدة:

  ١ · `output_tokens` عند هذا المزوّد ليست وكيلاً عن حجم المحتوى المرئي —
      ميزانيةٌ كاملة استُهلكت وصفرُ حرفٍ وصل. (W2-B: تُعلَن قدرةً، لا يُتفرَّع
      على اسم.)
  ٢ · فقراءتها كثافةً في F-40 تُصغّر الشريحة عند كل ردّ، والردّ التالي يعيد
      القياس نفسه، فالتكيّف يغذّي نفسه: 60→35→20→11→6→4. (W2-C)
  ٣ · وتصنيفه EMPTY_RESPONSE وصفٌ كاذب ورمزٌ لا يُشطَر ولا يُصعَّد، فينتهي
      الطلب 502 بلا محاولة تعافٍ واحدة. (W2-E)

وحالة MEDIUM تكشف عطلاً رابعاً في **التوجيه** نفسه: est=15944 دون عتبة
19200 فاختير النداء الواحد، ثم استُهلكت 32000 وقُطِع المخرج. العتبة تقارن
تقديرَ محتوىً بميزانيةٍ تُحاسِب شيئاً آخر.

الشواهد السالبة في هذا الملفّ (المطلوبة نصّاً في التفويض)
---------------------------------------------------------
  د١ · إعادة تغذية رموز المخرج على مزوّدٍ غير وكيل **تُعيد إنتاج** الانهيار
       المقيس رقماً برقم: 60→35→20→11→6→4.
  د٢ · مسار المزوّد الوكيل يعطي نفس الأرقام بالضبط قبل التغيير وبعده.
  د٣ · ردٌّ استهلك ميزانيته كلّها في التفكير لا يمكن أن يُقرأ JSON صالحاً.
  د٤ · JSON مرئيّ جزئيّ عند السقف = TRUNCATED، وليس EMPTY_RESPONSE.

نطاق مُعلَن: لا مفتاح ولا شبكة. القبول الحيّ لـLARGE يبقى
LIVE LARGE ACCEPTANCE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
"""
import ast
import importlib
import io
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                       # noqa: E402
import acs_generation as G                                       # noqa: E402
import acs_logging as LOGGING                                    # noqa: E402
import acs_plan_chunks as PC                                     # noqa: E402
import acs_provider as PROV                                      # noqa: E402

p = [0]
f = [0]

FAKE_DEEPSEEK = "sk-" + "d" * 32
FAKE_ANTHROPIC = "sk-ant-" + "a" * 32

# القيم الحيّة، مكتوبةً مرّةً واحدة فيُقرأ منها كل ما بعدها.
LIVE_PLAN_BUDGET = 16000
LIVE_PLAN_OUT_TOKENS = 16000
LIVE_PLAN_OUT_CHARS = 0
LIVE_MEDIUM_EST = 15944
LIVE_MEDIUM_BUDGET = 32000
#: الانهيار كما رُصد في التدقيق — هو المرجع الذي يقيس عليه الشاهد السالب د١.
LIVE_CASCADE = [60, 35, 20, 11, 6, 4]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ═══════════════════════════ بديل SDK بتوقيع v0.40.0 ═══════════════════════
class _Usage(object):
    def __init__(self, i=1000, o=900, **extra):
        self.input_tokens = i
        self.output_tokens = o
        for k, v in extra.items():
            setattr(self, k, v)


class _Blk(object):
    """`text` غائبة تماماً على الكتل غير النصّية — كما في SDK."""

    def __init__(self, btype, text=None):
        self.type = btype
        if text is not None:
            self.text = text


class _Msg(object):
    def __init__(self, blocks, stop="end_turn", usage=None):
        self.content = list(blocks)
        self.stop_reason = stop
        self.usage = usage or _Usage()


class _Ctx(object):
    def __init__(self, m):
        self._m = m

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._m


def install(behaviour):
    sent = []

    class _Messages(object):
        def _serve(self, kw):
            if len(sent) >= 12:
                raise RuntimeError("unbounded retry")
            sent.append(dict(kw))
            act = behaviour(len(sent))
            if isinstance(act, Exception):
                raise act
            return act

        def create(self, *, max_tokens, messages, model, metadata=None,
                   stop_sequences=None, stream=None, system=None,
                   temperature=None, tool_choice=None, tools=None,
                   top_k=None, top_p=None, extra_headers=None,
                   extra_query=None, extra_body=None, timeout=None):
            return self._serve({"model": model, "max_tokens": max_tokens})

        def stream(self, *, max_tokens, messages, model, metadata=None,
                   stop_sequences=None, system=None, temperature=None,
                   top_k=None, top_p=None, tool_choice=None, tools=None,
                   extra_headers=None, extra_query=None, extra_body=None,
                   timeout=None):
            return _Ctx(self._serve({"model": model, "max_tokens": max_tokens}))

    class _Client(object):
        def __init__(self, *, api_key=None, base_url=None, timeout=None):
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    mod.__version__ = "0.40.0"
    sys.modules["anthropic"] = mod
    return sent


def _clear():
    for k in ("ACS_LLM_PROVIDER", "ACS_LLM_BASE_URL", "ACS_LLM_API_KEY",
              "ACS_LLM_MODEL", "ACS_LLM_FALLBACK_PROVIDER",
              "ACS_LLM_FALLBACK_API_KEY", "ANTHROPIC_API_KEY",
              "ACS_ALLOWED_MODELS", "ACS_LLM_CONTENT_TOKEN_MULTIPLIER",
              "ACS_LLM_OUTPUT_TOKENS_CONTENT_PROXY"):
        os.environ.pop(k, None)


def deepseek_env():
    _clear()
    os.environ["ACS_LLM_PROVIDER"] = "deepseek"
    os.environ["ACS_LLM_BASE_URL"] = "https://api.deepseek.com/anthropic"
    os.environ["ACS_LLM_API_KEY"] = FAKE_DEEPSEEK
    os.environ["ACS_LLM_MODEL"] = "deepseek-v4-pro"
    os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"


def anthropic_env():
    _clear()
    os.environ["ACS_LLM_PROVIDER"] = "anthropic"
    os.environ["ACS_LLM_API_KEY"] = FAKE_ANTHROPIC
    os.environ["ACS_LLM_MODEL"] = "claude-sonnet-5"
    os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"


def fresh():
    import acs_understand as U
    return importlib.reload(U)


class _Cap(LOGGING.StructuredLogger):
    def __init__(self, sink):
        LOGGING.StructuredLogger.__init__(self,
                                          service="ACS Understanding Engine")
        self.sink = sink

    def _emit(self, level, event, **fields):
        rec = LOGGING.StructuredLogger._emit(self, level, event, **fields)
        if rec:
            self.sink.append(rec)
        return rec


def run_once(U, sink, stage="plan_chunk", max_tokens=LIVE_PLAN_BUDGET):
    saved, U.LOG = U.LOG, _Cap(sink)
    tel = {}
    try:
        try:
            out = U._call_llm_impl("مستودع كبير", max_tokens=max_tokens,
                                   stage=stage, telemetry=tel)
        except Exception as exc:                                  # noqa: BLE001
            out = exc
        U._emit_generation_telemetry(tel, stage, strategy="staged",
                                     duration_ms=1,
                                     success=not isinstance(out, Exception))
    finally:
        U.LOG = saved
    return out, tel


# ═══════════ صياغة F-40 **قبل** W2-C — مرجعُ الشاهدين السالبين د١ ود٢ ═══════
def legacy_measured_zone_rate(out_tokens, zone_count, previous=None):
    """الصياغة الأصلية حرفياً. مكتوبةٌ هنا لا مستوردة: الشاهد السالب يحتاج
    السلوك القديم بعد أن يزول من الشفرة."""
    base = max(int(previous or 0), PC.estimate_plan_zone_tokens())
    n = max(1, int(zone_count or 0))
    seen = int(int(out_tokens or 0) / n) + 1
    return max(base, seen)


def cascade(rate_fn, rounds=6, budget=LIVE_PLAN_BUDGET):
    """يشغّل حلقة اشتقاق حجم الشريحة كما في `_plan_bounded`، ويعيد الأحجام.

    كل جولة تُطعَم **القراءة الحيّة نفسها**: الميزانية كاملةً في رموز المخرج،
    وصفرَ حرفٍ مرئيّ، وصفرَ منطقةٍ اكتملت. هذا هو المدخل المقيس، لا مدخلٌ
    مصنوع ليُثبت شيئاً.
    """
    sizes = []
    rate = None
    for _ in range(rounds):
        size = PC.chunk_size_for(budget, None, rate)
        sizes.append(size)
        rate = rate_fn(LIVE_PLAN_OUT_TOKENS, size, rate)
    return sizes


def main():
    gen_src = io.open(os.path.join(ROOT, "acs_generation.py"),
                      encoding="utf-8").read()
    pc_src = io.open(os.path.join(ROOT, "acs_plan_chunks.py"),
                     encoding="utf-8").read()
    us_src = io.open(os.path.join(ROOT, "acs_understand.py"),
                     encoding="utf-8").read()

    # ═══ أ · W2-B — القدرة مُعلَنة، ومقيَّدة، ولا تُقرأ من اسم ════════════════
    print("\n== أ · W2-B — قدرة المزوّد بيانٌ مُعلَن لا اسمٌ يُتفرَّع عليه ==")
    anthropic_env()
    a_caps = PROV.capabilities()
    deepseek_env()
    d_caps = PROV.capabilities()

    chk("anthropic يعلن أن رموز مخرجه وكيلٌ عن المحتوى — وهو السلوك القائم",
        a_caps["output_tokens_are_content_proxy"] is True, a_caps)
    chk("deepseek يعلن أنها ليست كذلك — وهو ما قِيس حيّاً",
        d_caps["output_tokens_are_content_proxy"] is False, d_caps)
    chk("مضاعِف anthropic 1.0 بالضبط: لا يغيّر أي حساب قائم",
        a_caps["content_token_multiplier"] == 1.0, a_caps)
    chk("مضاعِف deepseek 2.0 — مشتقّ من القياس (31022/15944 = 1.946) بهامش أمان",
        d_caps["content_token_multiplier"] == 2.0, d_caps)
    chk("كل مفتاح قدرة له افتراضٌ مُعلَن في CAPABILITY_DEFAULTS",
        set(a_caps) == set(PROV.CAPABILITY_DEFAULTS)
        and set(d_caps) == set(PROV.CAPABILITY_DEFAULTS))
    chk("الافتراض هو السلوك القائم: مزوّدٌ لا يعلن قدرةً يُعامَل معاملة الوكيل",
        PROV.CAPABILITY_DEFAULTS["output_tokens_are_content_proxy"] is True
        and PROV.CAPABILITY_DEFAULTS["content_token_multiplier"] == 1.0)

    os.environ["ACS_LLM_CONTENT_TOKEN_MULTIPLIER"] = "0.25"
    chk("مضاعِفٌ دون 1.0 يُرفَض: ادّعاءُ وفرٍ يرفع العتبة في اتّجاه الخطر",
        PROV.capabilities()["content_token_multiplier"]
        == PROV.MIN_CONTENT_TOKEN_MULTIPLIER)
    os.environ["ACS_LLM_CONTENT_TOKEN_MULTIPLIER"] = "9999"
    chk("ومضاعِفٌ هارب يُقصّ إلى الحدّ الأعلى المُعلَن",
        PROV.capabilities()["content_token_multiplier"]
        == PROV.MAX_CONTENT_TOKEN_MULTIPLIER)
    os.environ["ACS_LLM_CONTENT_TOKEN_MULTIPLIER"] = "not-a-number"
    chk("وقيمةٌ غير رقمية تسقط إلى المُعلَن لا إلى صفر ولا إلى استثناء",
        PROV.capabilities()["content_token_multiplier"] == 2.0)
    os.environ.pop("ACS_LLM_CONTENT_TOKEN_MULTIPLIER")

    os.environ["ACS_LLM_OUTPUT_TOKENS_CONTENT_PROXY"] = "1"
    chk("للمشغّل تجاوزٌ صريح إن كذّب القياسُ الإعلان — بلا تعديل شفرة",
        PROV.capabilities()["output_tokens_are_content_proxy"] is True)
    os.environ.pop("ACS_LLM_OUTPUT_TOKENS_CONTENT_PROXY")

    chk("القدرة تظهر في /health: المشغّل يرى بأيّ محاسبةٍ يعمل النظام",
        isinstance(PROV.health_status().get("capabilities"), dict)
        and PROV.health_status()["capabilities"]
        ["output_tokens_are_content_proxy"] is False)
    chk("والعقد يعلن المفاتيح وحدودها بدل دفنها",
        PROV.spec()["capability_keys"] == sorted(PROV.CAPABILITY_DEFAULTS)
        and PROV.spec()["content_token_multiplier_bounds"] == [1.0, 8.0])
    chk("القدرة لا تحمل مفتاحاً ولا عنواناً كاملاً",
        not any("key" in k or "url" in k for k in d_caps))

    # الشرط الثاني في التفويض: لا تفرّع على اسم مزوّد داخل منطق التقطيع.
    def literal_provider_names(src):
        tree = ast.parse(src)
        doc = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef,
                                 ast.AsyncFunctionDef)):
                d = ast.get_docstring(node, clean=False)
                if d is not None:
                    doc.add(d)
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in doc:
                    continue
                for name in PROV.PROVIDERS:
                    if name in node.value:
                        hits.append((node.lineno, node.value[:40]))
        return hits

    chk("منطق التقطيع لا يذكر اسم مزوّدٍ في أي قيمة نصّية منفَّذة",
        literal_provider_names(pc_src) == [], literal_provider_names(pc_src))
    chk("ومنطق التوجيه كذلك",
        literal_provider_names(gen_src) == [], literal_provider_names(gen_src))
    chk("acs_plan_chunks لا يستورد acs_provider في أعلى الملفّ — القدرة تُقرأ "
        "عند الحاجة فتبقى الوحدة نقيّة وقابلة للاختبار بلا بيئة",
        "\nimport acs_provider" not in pc_src)

    # ═══ ب · W2-C/١ — التوجيه: الحالة الحيّة التي قُطِعت ══════════════════════
    print("\n== ب · W2-C — التوجيه محسوبٌ باقتصاد المزوّد العامل (المطلب 5) ==")
    anthropic_env()
    chk("مع الوكيل: الطلب المحاسَب = تقدير المحتوى نفسه، بلا زيادة رمز",
        G.accounted_output_tokens(LIVE_MEDIUM_EST) == LIVE_MEDIUM_EST)
    chk("والحالة الحيّة تبقى MEDIUM ⇒ نداءٌ واحد — سلوكٌ قائم لم يتغيّر",
        G.classify(G.accounted_output_tokens(LIVE_MEDIUM_EST),
                   LIVE_MEDIUM_BUDGET) == G.MEDIUM)

    deepseek_env()
    acc = G.accounted_output_tokens(LIVE_MEDIUM_EST)
    thresh = int(LIVE_MEDIUM_BUDGET * G.SINGLE_STAGE_SAFETY)
    chk("الحالة الحيّة: est=15944 دون العتبة 19200 — ولذلك اختير النداء الواحد",
        LIVE_MEDIUM_EST < thresh)
    chk("وقد استهلك فعلاً 31022 ثمّ 32000 وقُطِع: العتبة كانت تقيس بالوحدة الخطأ",
        acc >= 31022 - 1, acc)
    chk("بعد W2-C: الطلب المحاسَب %d يتجاوز العتبة ⇒ يُوجَّه إلى المراحل" % acc,
        G.classify(acc, LIVE_MEDIUM_BUDGET) != G.MEDIUM
        and acc > thresh, (acc, thresh))
    chk("ولا يُوجَّه SMALL إلى المراحل بلا سبب: 6917 حرفاً نجحت حيّاً وتبقى واحدة",
        G.classify(G.accounted_output_tokens(int(LIVE_MEDIUM_BUDGET * 0.24)),
                   LIVE_MEDIUM_BUDGET) in (G.SMALL, G.MEDIUM))

    plan = G.plan_strategy("مستودع صناعي كبير", btype="warehouse",
                           site_w=120, site_d=90)
    chk("plan_strategy يعلن المضاعِف والطلب المحاسَب — التوجيه قابل للمراجعة",
        plan["content_token_multiplier"] == 2.0
        and plan["accounted_output_tokens"]
        == int(plan["estimated_output_tokens"] * 2.0))
    chk("ولا يُخفي تقدير المحتوى الأصلي خلفه",
        plan["estimated_output_tokens"] > 0
        and plan["estimated_output_tokens"] != plan["accounted_output_tokens"])

    # المطلب 6: لا يُعالَج شيء برفع السقف.
    ds_budgets = {s: G.stage_budget(s)
                  for s in ("single", "plan", "detail", "repair")}
    ds_max, ds_outline = G.max_output_tokens(), PC.outline_budget()
    anthropic_env()
    an_budgets = {s: G.stage_budget(s)
                  for s in ("single", "plan", "detail", "repair")}
    chk("المطلب 6 — لا سقفَ رُفِع: ميزانيات المراحل واحدة عند المزوّدين",
        ds_budgets == an_budgets, (ds_budgets, an_budgets))
    chk("ولا الميزانية الواحدة ولا سقف البيان",
        ds_max == G.max_output_tokens() and ds_outline == PC.outline_budget())
    chk("والمضاعِف يرفع **الطلب المقدَّر** لا `max_tokens` — لا يظهر في أي ميزانية",
        "content_token_multiplier" not in gen_src.split("def stage_budget")[1]
        .split("def ")[0])

    # ═══ ج · W2-C/٢ — التقطيع يُقاس بالمحتوى المرئي المكتمل ═════════════════
    print("\n== ج · W2-C — كلفة المنطقة تُقاس بما وصل ويمكن التحقّق منه ==")
    est = PC.estimate_plan_zone_tokens()
    chk("القراءة الحيّة (16000 رمزاً، 0 حرف، 0 منطقة مكتملة) لا تُغيّر الكلفة",
        PC.measured_zone_rate(LIVE_PLAN_OUT_TOKENS, 60, None,
                              visible_chars=LIVE_PLAN_OUT_CHARS,
                              completed_zones=0,
                              tokens_are_content_proxy=False) == est)
    chk("ولا تُغيّرها حتى لو سبقتها كلفةٌ أعلى: الرتابة محفوظة، ولا ارتفاع بلا قياس",
        PC.measured_zone_rate(LIVE_PLAN_OUT_TOKENS, 60, 300,
                              visible_chars=0, completed_zones=0,
                              tokens_are_content_proxy=False) == 300)
    chk("محتوىً مرئيّ مكتمل يُقاس فعلاً: 4400 حرفاً / 10 مناطق ⇒ 201 رمزاً",
        PC.measured_zone_rate(16000, 10, None, visible_chars=4400,
                              completed_zones=10,
                              tokens_are_content_proxy=False)
        == int(4400 / PC.VISIBLE_CHARS_PER_TOKEN / 10) + 1)
    chk("والمقيس دون التقدير لا يُكافأ بشريحة أكبر — التكيّف أحاديّ الاتجاه",
        PC.measured_zone_rate(16000, 10, None, visible_chars=100,
                              completed_zones=10,
                              tokens_are_content_proxy=False) == est)
    chk("وسقفٌ صريح يمنع قياساً شاذّاً واحداً من شلّ ما بعده",
        PC.measured_zone_rate(16000, 1, None, visible_chars=10 ** 6,
                              completed_zones=1,
                              tokens_are_content_proxy=False)
        == PC.zone_rate_ceiling())
    chk("السقف مُعلَن لا مدفون، ومشتقّ من تسامح الإسهاب القائم",
        PC.zone_rate_ceiling() == int(est * PC.MAX_ZONE_RATE_FACTOR)
        and PC.MAX_ZONE_RATE_FACTOR == PC.VERBOSITY_TOLERANCE)
    chk("والرتابة غير المتناقصة (شرط F-40) محفوظة عبر أي تسلسل قياسات",
        all(PC.measured_zone_rate(16000, 8, prev, visible_chars=c,
                                  completed_zones=8,
                                  tokens_are_content_proxy=False) >= prev
            for prev in (0, 156, 300, 468, 900)
            for c in (0, 100, 4400, 10 ** 6)))
    chk("وحتميّ: نفس المدخل يعطي نفس المخرج دائماً",
        len({PC.measured_zone_rate(16000, 9, 200, visible_chars=3000,
                                   completed_zones=7,
                                   tokens_are_content_proxy=False)
             for _ in range(50)}) == 1)
    chk("والمحاسبة المُعلَنة تظهر في عقد الوحدة",
        PC.spec()["zone_rate_ceiling"] == PC.zone_rate_ceiling()
        and PC.spec()["visible_chars_per_token"] == PC.VISIBLE_CHARS_PER_TOKEN)

    deepseek_env()
    chk("والقدرة تُقرأ من المزوّد حين لا تُمرَّر صراحةً",
        PC._tokens_are_content_proxy_default() is False)
    anthropic_env()
    chk("وتعود إلى الوكيل عند المزوّد الوكيل",
        PC._tokens_are_content_proxy_default() is True)

    # ═══ د١ · شاهد سالب — إعادة التغذية تُعيد إنتاج الانهيار المقيس ══════════
    print("\n== د١ · شاهد سالب — إعادة رموز المخرج تُعيد الانهيار رقماً برقم ==")
    old = cascade(legacy_measured_zone_rate)
    new = cascade(lambda t, n, prev: PC.measured_zone_rate(
        t, n, prev, visible_chars=LIVE_PLAN_OUT_CHARS, completed_zones=0,
        tokens_are_content_proxy=False))
    chk("بالصياغة القديمة: %s — وهو الانهيار الموثّق في التدقيق حرفياً"
        % (old,), old == LIVE_CASCADE, old)
    chk("العطل حقيقيّ لا نظريّ: الشريحة تنتهي عند MIN_CHUNK_ZONES",
        old[-1] == PC.MIN_CHUNK_ZONES)
    chk("وعدد النداءات لمئة منطقة يتضاعف %.1f× (2 → %d نداءً)"
        % (-(-100 // old[-1]) / float(-(-100 // old[0])), -(-100 // old[-1])),
        -(-100 // old[-1]) >= 10 * -(-100 // old[0]))
    chk("بالصياغة الجديدة: %s — ثابتة، فلا تصعيد ولا انفجار نداءات" % (new,),
        len(set(new)) == 1 and new[0] == old[0], new)
    chk("والفرق نابعٌ من القياس وحده: نفس المدخل، ونفس الميزانية، ونفس الحلقة",
        old[0] == new[0])

    # ═══ د٢ · شاهد سالب — مسار المزوّد الوكيل لم يتغيّر بايتاً ════════════════
    print("\n== د٢ · شاهد سالب — مسار المزوّد الوكيل مطابقٌ لما كان (المطلب 4) ==")
    same = True
    for prev in (None, 0, 100, 156, 400, 5000):
        for tok in (0, 1, 305, 4303, 16000, 32000):
            for n in (0, 1, 4, 17, 60):
                a = legacy_measured_zone_rate(tok, n, prev)
                b = PC.measured_zone_rate(tok, n, prev,
                                          tokens_are_content_proxy=True)
                # ووسائط W2-C لا تؤثّر فيه إطلاقاً حتى لو مُرِّرت
                c = PC.measured_zone_rate(tok, n, prev, visible_chars=99999,
                                          completed_zones=1,
                                          tokens_are_content_proxy=True)
                if not (a == b == c):
                    same = False
    chk("١٨٠ تركيبة: القديم == الجديد == الجديد بوسائط W2-C ممرَّرة",
        same)
    anthropic_env()
    chk("ومع المزوّد الوكيل تُقرأ القدرة من البيئة فتعطي النتيجة نفسها",
        PC.measured_zone_rate(16000, 60, None, visible_chars=0,
                              completed_zones=0)
        == legacy_measured_zone_rate(16000, 60, None))
    chk("وسلسلة الانهيار نفسها ما زالت تعمل عند الوكيل — لم يُضعَف حارسٌ قائم",
        cascade(lambda t, n, prev: PC.measured_zone_rate(t, n, prev))
        == LIVE_CASCADE)
    an_plan = G.plan_strategy("مستودع صناعي كبير", btype="warehouse",
                              site_w=120, site_d=90)
    chk("وplan_strategy عند الوكيل: التصنيف مُشتقّ من التقدير نفسه لا من مضاعَفه",
        an_plan["accounted_output_tokens"] == an_plan["estimated_output_tokens"]
        and an_plan["size_class"] == G.classify(
            an_plan["estimated_output_tokens"], an_plan["max_output_tokens"]))

    # ═══ هـ · W2-E — أربع دلالات لا اثنتان ═══════════════════════════════════
    print("\n== هـ · W2-E — دلالة الرد تُشتقّ من محاسبة الكتل (المطلب 7) ==")
    chk("١ سقفٌ + تفكيرٌ وحده + صفرُ حرف ⇒ NO_VISIBLE_OUTPUT",
        E.classify_response("max_tokens", 0, 0, 1)
        == (E.RESP_NO_VISIBLE_OUTPUT, E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT))
    chk("٢ سقفٌ + JSON مرئيّ جزئيّ ⇒ TRUNCATED",
        E.classify_response("max_tokens", 18982, 1, 1)
        == (E.RESP_TRUNCATED, E.ACS_UPSTREAM_TRUNCATED))
    chk("٣ end_turn + نصّ صالح ⇒ OK بلا رمز خطأ",
        E.classify_response("end_turn", 20463, 1, 1) == (E.RESP_OK, None))
    chk("٤ ردٌّ بلا أي كتلة ⇒ EMPTY_RESPONSE — وهي حالةٌ أخرى فعلاً",
        E.classify_response("end_turn", 0, 0, 0)
        == (E.RESP_EMPTY, E.ACS_UPSTREAM_EMPTY_RESPONSE))
    chk("والامتناع المُعلَن يعلو كلّ ذلك",
        E.classify_response("refusal", 0, 0, 1)[1] == E.ACS_UPSTREAM_REFUSED
        and E.classify_response("refusal", 500, 1, 0)[1]
        == E.ACS_UPSTREAM_REFUSED)
    chk("ردٌّ يحمل تفكيراً ونصّاً معاً — الشكل الغالب حيّاً — لا يُصنَّف بلا مخرج",
        E.classify_response("end_turn", 6917, 1, 1)[0] == E.RESP_OK)
    chk("الدلالات الخمس معلنة، والدالّة لا تعيد غيرها",
        {E.classify_response(s, c, t, nt)[0]
         for s in ("end_turn", "max_tokens", "refusal", "?", None)
         for c in (0, 1) for t in (0, 1) for nt in (0, 1)}
        <= set(E.RESPONSE_SEMANTICS))
    chk("الدالّة خالصة: لا بيئة ولا شبكة ولا SDK — قيمٌ داخلة وقيمٌ خارجة",
        E.classify_response("max_tokens", 0, 0, 1)
        == E.classify_response("max_tokens", 0, 0, 1))
    chk("ومحصّنة ضدّ قيمٍ غير رقمية بدل أن ترفع داخل مسار الرد",
        E.classify_response("max_tokens", None, None, None)[1]
        == E.ACS_UPSTREAM_EMPTY_RESPONSE
        and E.classify_response("max_tokens", "x", "y", "z")[1]
        == E.ACS_UPSTREAM_EMPTY_RESPONSE)

    chk("الرمز الجديد مُعلَن في CODES وله حالة HTTP ورسالة عربية",
        E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT in E.CODES
        and E.HTTP_STATUS[E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT] == 502
        and E.MESSAGE_AR.get(E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT))
    chk("ورسالته لا تقول «رداً فارغاً» — الوصف الكاذب هو نصف العطل",
        "فارغ" not in E.MESSAGE_AR[E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT])
    chk("وليس قابلاً لإعادة المحاولة: حدثُ سقفٍ حتميّ، وتكرارُه حرقُ ميزانية كاملة",
        E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT not in E.RETRYABLE)
    chk("ولا للتحويل إلى مزوّد بديل: المخرج وصل ورديئاً، وليست مسألة توفّر",
        E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT not in E.FALLBACK_ELIGIBLE
        and E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT
        not in E.FALLBACK_ELIGIBLE_ON_BILLING)
    chk("وهو دليل بلوغ سقفٍ إلى جانب TRUNCATED — فيُشطَر ويُصعَّد",
        E.CEILING_CODES == frozenset({E.ACS_UPSTREAM_TRUNCATED,
                                      E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT}))
    chk("ورسالته لا تحمل مساراً ولا اسم صنف بايثون",
        ".py" not in E.MESSAGE_AR[E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT]
        and "Error" not in E.MESSAGE_AR[E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT])

    # مواضع القرار الأربعة تقرأ الدليل لا الرمز الواحد
    for anchor, label in (
            ("if err.code not in E.CEILING_CODES or depth >= G.MAX_GROUP_SPLITS",
             "شطر مجموعة التفصيل"),
            ("if err.code not in E.CEILING_CODES:", "إعادة الخطّة بشرائح محدودة"),
            ("if (err.code in E.CEILING_CODES", "تصعيد النداء الواحد"),
            ("hit_ceiling = (err.code in E.CEILING_CODES", "شطر شريحة الخطّة")):
        chk("موضع القرار «%s» يقرأ دليل بلوغ السقف لا رمزاً بعينه" % label,
            anchor in us_src)
    chk("ولم يبقَ موضعُ قرارِ سقفٍ يقارن TRUNCATED وحدها",
        "err.code == E.ACS_UPSTREAM_TRUNCATED" not in us_src
        and "err.code != E.ACS_UPSTREAM_TRUNCATED" not in us_src)

    # ═══ د٣ · شاهد سالب — التفكير الكامل لا يُقرأ JSON صالحاً ════════════════
    print("\n== د٣ · شاهد سالب — ردٌّ استهلك ميزانيته تفكيراً لا يمرّ أبداً ==")
    deepseek_env()
    thinking_only = _Msg([_Blk("thinking")], stop="max_tokens",
                         usage=_Usage(i=5692, o=LIVE_PLAN_OUT_TOKENS))
    sent = install(lambda n: thinking_only)
    U = fresh()
    sink = []
    out, tel = run_once(U, sink)
    chk("يُرفَع NO_VISIBLE_OUTPUT لا EMPTY_RESPONSE — الوصف صار صادقاً",
        isinstance(out, E.AcsApiError)
        and out.code == E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT,
        getattr(out, "code", out))
    chk("ولا يعود نصّ إطلاقاً: لا شيء يصل إلى extract_json",
        isinstance(out, Exception))
    chk("والتليمتري يحمل الدلالة صراحةً",
        tel.get("response_semantic") == E.RESP_NO_VISIBLE_OUTPUT, tel.get(
            "response_semantic"))
    chk("والمحاسبة تقول أين ذهبت الميزانية: كتلةٌ واحدة غير نصّية",
        tel.get("nontext_blocks") == 1 and tel.get("text_blocks") == 0
        and tel.get("output_chars") == 0)
    chk("وW2-D ما زال يمنع الطلب المطابق بايتاً — نداءٌ واحد لا اثنان (المطلب 8)",
        len(sent) == 1 and tel.get("retry_skipped_reason")
        == "identical_request", len(sent))
    rec = [r for r in sink if r.get("event") == "llm_generation"]
    chk("والدلالة تعبر قائمة السماح إلى سجلّ الإنتاج بدل أن تُسقَط صامتةً",
        rec and rec[-1].get("response_semantic") == E.RESP_NO_VISIBLE_OUTPUT,
        rec[-1] if rec else None)
    chk("وبلا محاسبة الكتل (W2-A) كان التصنيف سيبقى EMPTY — المحاسبة حاملة",
        E.classify_response("max_tokens", 0, 0, 0)[1]
        == E.ACS_UPSTREAM_EMPTY_RESPONSE)
    chk("والسجلّ لا يحمل مفتاحاً ولا عنواناً كاملاً",
        rec and FAKE_DEEPSEEK not in repr(rec[-1])
        and "https://" not in repr(rec[-1]))

    # ═══ د٤ · شاهد سالب — JSON جزئيّ عند السقف = TRUNCATED ═══════════════════
    print("\n== د٤ · شاهد سالب — نصفُ JSON عند السقف انقطاعٌ لا فراغ ==")
    partial = _Msg([_Blk("thinking"),
                    _Blk("text", '{"site": {"w": 40, "d": 30}, "floors": {"t":')],
                   stop="max_tokens", usage=_Usage(i=5000, o=32000))
    install(lambda n: partial)
    U = fresh()
    sink2 = []
    out2, tel2 = run_once(U, sink2, stage="single", max_tokens=32000)
    chk("يُرفَع TRUNCATED — وهو ما يستدعي الشطر والتصعيد",
        isinstance(out2, E.AcsApiError)
        and out2.code == E.ACS_UPSTREAM_TRUNCATED, getattr(out2, "code", out2))
    chk("وليس EMPTY_RESPONSE ولا NO_VISIBLE_OUTPUT: النصّ وصل ومرئيّ",
        out2.code not in (E.ACS_UPSTREAM_EMPTY_RESPONSE,
                          E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT))
    chk("والدلالة truncated في التليمتري",
        tel2.get("response_semantic") == E.RESP_TRUNCATED)
    chk("والنصف الواصل لا يُرمَّم ولا يُغلَق قوسُه ولا يمرّ إلى المصرِّف",
        isinstance(out2, Exception))
    chk("ومحاسبة الكتل تفصل النصّي عن غيره في نفس الرد",
        tel2.get("text_blocks") == 1 and tel2.get("nontext_blocks") == 1
        and tel2.get("output_chars") > 0)
    chk("ونسبة الأحرف إلى الرمز محسوبة — وهي المقياس الذي أثبت العطل",
        isinstance(tel2.get("chars_per_output_token"), float))
    chk("والنصّ الواصل نفسه لا يظهر في السجلّ",
        '"site"' not in repr([r for r in sink2
                              if r.get("event") == "llm_generation"]))

    # الحالة الرابعة: رد سليم يمرّ كما كان
    ok = _Msg([_Blk("thinking"), _Blk("text", '{"site": {"w": 40, "d": 30}}')],
              stop="end_turn", usage=_Usage(i=5000, o=13945))
    install(lambda n: ok)
    U = fresh()
    out3, tel3 = run_once(U, [], stage="single", max_tokens=32000)
    chk("والردّ السليم يمرّ كما كان — لا حارسَ جديدٌ يعترض الحالة الناجحة",
        isinstance(out3, str) and '"site"' in out3, out3)
    chk("ودلالته ok وtel['complete'] صحيح",
        tel3.get("response_semantic") == E.RESP_OK
        and tel3.get("complete") is True)

    # ═══ و · الثوابت السابقة لم تُمَسّ ════════════════════════════════════════
    print("\n== و · الثوابت السابقة (المطلبان 8 و9) ==")
    chk("KI-24: ثوابت التقطيع كما هي — لم يُرفع سقفٌ ولا وُسِّع هامش",
        PC.CHUNK_SAFETY == 0.60 and PC.MIN_CHUNK_ZONES == 4
        and PC.MAX_CHUNK_ZONES == 60 and PC.T_OUTLINE_ZONE == 26
        and PC.MAX_CHUNK_SPLITS == 3 and PC.MAX_PLAN_CHUNKS == 24)
    chk("F-39: الشطر ما زال حارس الانقطاع — لم يُستبدَل بتصغير الكلّ",
        len(PC.split_chunk({"index": 0,
                        "zone_ids": ["z%d" % i for i in range(20)]}, 0)) == 2)
    chk("F-40: النداء الاستكشافي ما زال قائماً",
        PC.needs_pilot(60, 16000) is True and PC.PILOT_ZONES == 4)
    chk("STAGE_SHARE والميزانيات كما هي — لم يُمَسّ اقتصاد المراحل",
        G.STAGE_SHARE == {"single": 1.00, "plan": 0.50, "detail": 0.75,
                          "repair": 1.00})
    chk("KI-23: لا `thinking` يُرسَل مع SDK 0.40 — لم يتغيّر شيء في بناء الطلب",
        "_sdk_supports" in us_src and "supports_thinking" in us_src)
    chk("W2-D: البصمة ما زالت تُحسَب ولا تُسجَّل أبداً",
        "_request_fingerprint" in us_src
        and "fingerprint" not in str(LOGGING.StructuredLogger.generation
                                     .__doc__ or "")
        and all("fingerprint" not in k for k in (tel or {})))
    chk("F-50: تشخيص رفض المزوّد قائم بحقوله كلّها",
        all(x in us_src for x in ("provider_error_type", "requested_max_tokens",
                                  "sdk_version", "transport")))
    chk("عزل الأسرار: القدرة لا تُقرَأ من مفتاح ولا تفتح مساراً إلى مزوّد آخر",
        "api_key" not in str(PROV.capabilities()))

    print("\n" + "─" * 62)
    print("LIVE LARGE ACCEPTANCE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.")
    print("  هذا الملفّ يثبت المنطق على القيم المقيسة حيّاً. أنّ توليد LARGE")
    print("  حقيقياً يكتمل دون 840 ث بلا تصعيد تقطيع يحتاج نشراً وتشغيلاً —")
    print("  وهو ما يبقى شرطاً في بوّابة W2 بعد النشر، مع W2-G.")
    print("─" * 62)
    print("PROVIDER CAPABILITY / ROUTING / RESPONSE SEMANTICS: "
          "%d passed, %d failed" % (p[0], f[0]))
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
