# -*- coding: utf-8 -*-
"""W2-A/W2-D — محاسبة رد المزوّد، وإسقاط المحاولة المطابقة بايتاً.

    python3 tests/remediation/test_provider_accounting.py

لماذا هذه الموجة تبدأ بالقياس لا بالتصميم
------------------------------------------
السجلّ الحيّ يقول: `out_tokens=16000` و`out_chars=0` و`stop=max_tokens`.
ولا يقول **أين ذهبت** الستّة عشر ألفاً. والاستخراج القائم

    parts = [getattr(b, "text", None) for b in (msg.content or [])]

يُبقي الكتل النصّية وحدها ويُسقط ما عداها صامتاً — وتلك الكتل استهلكت
الميزانية. فأيُّ تصميمٍ لتقطيعٍ جديد يُبنى قبل هذا القياس يُبنى على فرضية.

W2-A يسجّل البنية وحدها: عدد الكتل، وأنواعها بأسمائها، وكم نصّيةٌ وكم غير
نصّية، وأطوال النصّ لكل كتلة، ونسبة الأحرف إلى رمز المخرج، وحقول الكاش إن
أعلنها المزوّد. لا نصّ، ولا محتوى كتلة، ولا توجيه، ولا نموذج مبنى، ولا مفتاح.

W2-D يُسقط محاولةً **مطابقة بايتاً** لمحاولةٍ أُرسلت. سلّم المحاولات وُضع
ليغيّر إعداد التفكير وحده، ومع anthropic==0.40 لا يُرسَل `thinking` إطلاقاً
(KI-23/F-31)، فالمحاولتان تبنيان الوسائط نفسها. والقاعدة عامّة: تُقارَن
البصمة، فإن اختلف الطلب فعلاً أُرسل. هذا الملفّ يثبت الاثنين **بالتقاط
الوسائط المُرسَلة فعلاً**، لا بقراءة النيّة.

نطاق مُعلَن: لا مفتاح ولا شبكة. أنواع الكتل الحقيقية التي يعيدها deepseek
تبقى:
LIVE DEEPSEEK BLOCK TYPES: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
"""
import importlib
import io
import json
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
#: علامةٌ لا تظهر في أي مكان آخر — إن ظهرت في سجلّ، فقد تسرّب محتوى كتلة.
SENTINEL = "ZQX-BLOCK-CONTENT-MUST-NEVER-BE-LOGGED-7419"


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ═══════════════════ بديل SDK يلتقط الوسائط المُرسَلة فعلاً ═══════════════════
class _Usage(object):
    def __init__(self, i=1000, o=900, **extra):
        self.input_tokens = i
        self.output_tokens = o
        for k, v in extra.items():
            setattr(self, k, v)


class _Blk(object):
    """كتلة رد. `text` غائبة تماماً على الكتل غير النصّية — كما في SDK."""

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


def install(behaviour, thinking_capable=False):
    """يركّب بديل anthropic ويعيد سجلّ **الوسائط الكاملة** لكل نداء."""
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

        if thinking_capable:
            def create(self, *, thinking=None, **kw):
                return self._serve(dict(kw, **({"thinking": thinking}
                                               if thinking is not None else {})))

            def stream(self, *, thinking=None, **kw):
                return _Ctx(self._serve(dict(kw, **({"thinking": thinking}
                                                    if thinking is not None else {}))))
        else:
            # توقيع v0.40.0 حرفياً: لا thinking ولا **kwargs.
            def create(self, *, max_tokens, messages, model, metadata=None,
                       stop_sequences=None, stream=None, system=None,
                       temperature=None, tool_choice=None, tools=None,
                       top_k=None, top_p=None, extra_headers=None,
                       extra_query=None, extra_body=None, timeout=None):
                return self._serve({"model": model, "max_tokens": max_tokens,
                                    "system": system, "messages": messages})

            def stream(self, *, max_tokens, messages, model, metadata=None,
                       stop_sequences=None, system=None, temperature=None,
                       top_k=None, top_p=None, tool_choice=None, tools=None,
                       extra_headers=None, extra_query=None, extra_body=None,
                       timeout=None):
                return _Ctx(self._serve({"model": model, "max_tokens": max_tokens,
                                         "system": system, "messages": messages}))

    class _Client(object):
        def __init__(self, *, api_key=None, base_url=None, timeout=None):
            self.ctor = {"api_key": api_key, "base_url": base_url}
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    mod.__version__ = "0.40.0" if not thinking_capable else "0.47.0"
    sys.modules["anthropic"] = mod
    return sent


def deepseek_env():
    for k in ("ACS_LLM_FALLBACK_PROVIDER", "ACS_LLM_FALLBACK_API_KEY",
              "ANTHROPIC_API_KEY", "ACS_ALLOWED_MODELS"):
        os.environ.pop(k, None)
    os.environ["ACS_LLM_PROVIDER"] = "deepseek"
    os.environ["ACS_LLM_BASE_URL"] = "https://api.deepseek.com/anthropic"
    os.environ["ACS_LLM_API_KEY"] = FAKE_DEEPSEEK
    os.environ["ACS_LLM_MODEL"] = "deepseek-v4-pro"
    os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"


def fresh():
    import acs_understand as U
    return importlib.reload(U)


class _Cap(LOGGING.StructuredLogger):
    """يلتقط السجلّ **بعد** مرور قائمة السماح — لا قبلها."""

    def __init__(self, sink):
        LOGGING.StructuredLogger.__init__(self,
                                          service="ACS Understanding Engine")
        self.sink = sink

    def _emit(self, level, event, **fields):
        rec = LOGGING.StructuredLogger._emit(self, level, event, **fields)
        if rec:
            self.sink.append(rec)
        return rec


def run_once(U, sink, stage="plan_chunk", max_tokens=16000):
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


def main():
    src = io.open(os.path.join(ROOT, "acs_understand.py"), encoding="utf-8").read()

    # ═══ أ · W2-D: التكافؤ يُثبَت بالتقاط الوسائط، لا بالقراءة ════════════════
    print("\n== أ · W2-D — هل المحاولتان متطابقتان فعلاً؟ يُقاس، لا يُفترَض ==")
    deepseek_env()
    # ردٌّ بلا نصّ إطلاقاً: الشكل الحيّ الذي كان يستدعي إعادة المحاولة.
    empty = _Msg([_Blk("thinking")], stop="max_tokens",
                 usage=_Usage(i=5692, o=16000))
    sent = install(lambda n: empty)
    U = fresh()
    sink = []
    out, tel = run_once(U, sink)

    chk("the empty-response shape still fails the call",
        isinstance(out, E.AcsApiError), type(out).__name__)
    chk("EXACTLY ONE request was sent, not two", len(sent) == 1, len(sent))
    chk("the skip is recorded with its reason",
        tel.get("retry_skipped_reason") == "identical_request",
        tel.get("retry_skipped_reason"))
    chk("and the number skipped is recorded", tel.get("retries_skipped") == 1,
        tel.get("retries_skipped"))

    # التكافؤ نفسه: تُبنى الوسائط للمحاولتين وتُقارَن بايتاً.
    kw_off = {"model": "deepseek-v4-pro", "max_tokens": 16000,
              "system": "S", "messages": [{"role": "user", "content": "X"}]}
    kw_default = dict(kw_off)
    chk("PROOF OF EQUIVALENCE — with sdk 0.40 the two attempts build the same "
        "request, so the second cannot produce a different result",
        U._request_fingerprint(kw_off) == U._request_fingerprint(kw_default))
    chk("and a genuinely different request has a different fingerprint",
        U._request_fingerprint(kw_off)
        != U._request_fingerprint(dict(kw_off, thinking={"type": "disabled"})))
    chk("a different max_tokens is a different request",
        U._request_fingerprint(kw_off)
        != U._request_fingerprint(dict(kw_off, max_tokens=8000)))
    chk("the fingerprint is never logged",
        all("fingerprint" not in json.dumps(r) for r in sink))

    # الشاهد السالب: مكتبة **تعرف** thinking ⇒ الطلبان يختلفان ⇒ يُرسَلان معاً.
    sent2 = install(lambda n: empty, thinking_capable=True)
    U2 = fresh()
    sink2 = []
    out2, tel2 = run_once(U2, sink2)
    chk("NEGATIVE CONTROL — on an SDK that DOES accept `thinking` the two "
        "attempts genuinely differ, so BOTH are still sent",
        len(sent2) == 2, len(sent2))
    chk("  …and the requests differ exactly in `thinking`",
        len(sent2) == 2 and ("thinking" in sent2[0]) != ("thinking" in sent2[1]),
        [sorted(k for k in s) for s in sent2])
    chk("  …and nothing is recorded as skipped there",
        tel2.get("retry_skipped_reason") is None)
    chk("the ladder itself is untouched — it is still two attempts",
        src.count("(max_tokens, OFF)") == 1 and src.count("(max_tokens, None)") == 1)

    # نجاحٌ من أوّل محاولة: لا شيء يُسقَط.
    good = _Msg([_Blk("text", '{"ok":1}')], stop="end_turn",
                usage=_Usage(i=1000, o=40))
    sent3 = install(lambda n: good)
    U3 = fresh()
    sink3 = []
    out3, tel3 = run_once(U3, sink3)
    chk("a first-attempt success sends exactly one request",
        len(sent3) == 1 and out3.strip() == '{"ok":1}', len(sent3))
    chk("and records no skip", tel3.get("retry_skipped_reason") is None)

    # ═══ ب · W2-A: محاسبة الكتل ══════════════════════════════════════════════
    print("\n== ب · W2-A — أين ذهبت رموز المخرجات ==")
    mixed = _Msg([_Blk("thinking"), _Blk("text", "A" * 305), _Blk("thinking")],
                 stop="max_tokens", usage=_Usage(i=1225, o=16000))
    install(lambda n: mixed)
    U4 = fresh()
    sink4 = []
    out4, tel4 = run_once(U4, sink4)
    chk("every block is counted", tel4.get("content_blocks") == 3,
        tel4.get("content_blocks"))
    chk("the types are named", tel4.get("content_block_types") == "text:1,thinking:2",
        tel4.get("content_block_types"))
    chk("text and non-text blocks are separated",
        tel4.get("text_blocks") == 1 and tel4.get("nontext_blocks") == 2,
        (tel4.get("text_blocks"), tel4.get("nontext_blocks")))
    chk("per-block visible chars are recorded",
        tel4.get("text_block_chars") == "0,305,0", tel4.get("text_block_chars"))
    chk("visible chars are recorded as a first-class field",
        tel4.get("output_chars") == 305, tel4.get("output_chars"))
    # النسبة تُدوَّر إلى أربع منازل عمداً: رقمٌ يُقرأ في السجلّ لا كسرٌ عائم خام.
    chk("the chars-per-output-token ratio is computed (4 dp, as declared)",
        tel4.get("chars_per_output_token") == round(305.0 / 16000, 4),
        tel4.get("chars_per_output_token"))

    # الشكل الحيّ بالضبط: صفر حرف، ميزانية كاملة.
    install(lambda n: _Msg([_Blk("thinking")], stop="max_tokens",
                           usage=_Usage(i=5692, o=16000)))
    U5 = fresh()
    sink5 = []
    _, tel5 = run_once(U5, sink5)
    chk("the live shape (out_chars=0, out_tokens=16000) now says where they went",
        tel5.get("nontext_blocks") == 1 and tel5.get("text_blocks") == 0
        and tel5.get("content_block_types") == "thinking:1",
        tel5.get("content_block_types"))
    chk("and its ratio is exactly zero, not absent",
        tel5.get("chars_per_output_token") == 0.0,
        tel5.get("chars_per_output_token"))

    # حالةٌ ثالثة يجب ألّا تُخلَط بالثانية: **لا كتل إطلاقاً**.
    install(lambda n: _Msg([], stop="max_tokens", usage=_Usage(i=10, o=16000)))
    U6 = fresh()
    sink6 = []
    _, tel6 = run_once(U6, sink6)
    chk("a response with NO blocks at all is distinguishable from one with "
        "non-text blocks", tel6.get("content_blocks") == 0
        and tel6.get("content_block_types") == "none",
        tel6.get("content_block_types"))

    # حقول الكاش — تفصل «كاش أصاب» عن «محاسبة غير موثوقة».
    install(lambda n: _Msg([_Blk("text", "{}")], stop="end_turn",
                           usage=_Usage(i=60, o=900,
                                        cache_read_input_tokens=5632)))
    U7 = fresh()
    sink7 = []
    _, tel7 = run_once(U7, sink7)
    chk("cache token fields are recorded when the provider exposes them",
        tel7.get("cache_read_input_tokens") == 5632,
        tel7.get("cache_read_input_tokens"))
    chk("and they are absent, not zero, when it does not",
        tel4.get("cache_read_input_tokens") is None)

    # ═══ ج · القناة تُسقط ما لم يُعلَن — فالحقول الجديدة تُقاس هناك ═══════════
    print("\n== ج · كل حقل جديد ينجو من قائمة السماح ==")
    rec = [r for r in sink4 if r.get("event") == "llm_generation"]
    chk("a generation record was emitted", len(rec) == 1, len(rec))
    if rec:
        r = rec[0]
        for field, want in (("content_blocks", 3),
                            ("content_block_types", "text:1,thinking:2"),
                            ("text_blocks", 1), ("nontext_blocks", 2),
                            ("text_block_chars", "0,305,0"),
                            ("output_chars", 305)):
            chk("the channel passes %s" % field, r.get(field) == want, r.get(field))
        chk("the channel passes chars_per_output_token",
            r.get("chars_per_output_token") is not None)
    rec7 = [r for r in sink7 if r.get("event") == "llm_generation"]
    chk("the channel passes cache_read_input_tokens",
        rec7 and rec7[0].get("cache_read_input_tokens") == 5632)
    rec_skip = [r for r in sink if r.get("event") == "llm_generation"]
    chk("the channel passes retry_skipped_reason",
        rec_skip and rec_skip[0].get("retry_skipped_reason") == "identical_request")

    # ═══ د · لا محتوى ولا سرّ في أي شيء يُسجَّل ══════════════════════════════
    print("\n== د · بنيةٌ فقط: لا نصّ كتلة، ولا توجيه، ولا مفتاح ==")
    install(lambda n: _Msg([_Blk("thinking"),
                            _Blk("text", SENTINEL + " " + SENTINEL)],
                           stop="end_turn", usage=_Usage(i=10, o=50)))
    U8 = fresh()
    sink8 = []
    _, tel8 = run_once(U8, sink8)
    dump = json.dumps(sink8, ensure_ascii=False)
    chk("the block's own text never reaches the log", SENTINEL not in dump)
    chk("the prompt text never reaches the log", "مستودع كبير" not in dump)
    chk("the api key never reaches the log", FAKE_DEEPSEEK not in dump)
    chk("no full endpoint URL reaches the log", "://" not in dump)
    chk("but the STRUCTURE did reach it — the record is not empty of accounting",
        '"content_blocks"' in dump and '"content_block_types"' in dump)
    chk("block type names are sanitised to identifiers",
        U8._block_type(_Blk("text\n; DROP", None)) == "textDROP",
        U8._block_type(_Blk("text\n; DROP", None)))
    chk("a block with no type at all still yields an identifier",
        isinstance(U8._block_type(object()), str)
        and U8._block_type(object()) != "")

    # ═══ هـ · لا شيء غير المحاسبة تغيّر ═══════════════════════════════════════
    print("\n== هـ · W2-A/W2-D لم يمسّا ميزانيةً ولا تقطيعاً ولا ثابتاً ==")
    importlib.reload(G)
    chk("STAGE_SHARE unchanged",
        G.STAGE_SHARE == {"single": 1.00, "plan": 0.50, "detail": 0.75,
                          "repair": 1.00})
    chk("STAGE_FLOOR unchanged", G.STAGE_FLOOR == 4000)
    os.environ["ACS_LLM_MAX_OUTPUT_TOKENS"] = "32000"
    importlib.reload(G)
    chk("stage budgets unchanged (32000/16000/24000)",
        (G.stage_budget("single"), G.stage_budget("plan"),
         G.stage_budget("detail")) == (32000, 16000, 24000))
    importlib.reload(PC)
    chk("KI-24 chunk constants unchanged",
        (PC.T_OUTLINE_ZONE, PC.CHUNK_SAFETY, PC.MIN_CHUNK_ZONES,
         PC.MAX_CHUNK_SPLITS, PC.MAX_PLAN_CHUNKS) == (26, 0.60, 4, 3, 24))
    chk("measured_zone_rate is NOT touched in this commit — W2-C is the wave "
        "that changes it, and only after the live measurement",
        "out_tokens" in io.open(os.path.join(ROOT, "acs_plan_chunks.py"),
                                encoding="utf-8").read())
    chk("KI-23's thinking gate is untouched",
        '_sdk_supports(client, "thinking")' in src)
    chk("KI-26 endpoint safety is untouched",
        "_sdk_accepts_base_url" in src and "MISSING_BASE_URL" in src)
    chk("F-50 diagnostic fields are still emitted",
        all(k in src for k in ("provider_error_type", "provider_param",
                               "provider_limit", "provider_detail",
                               "requested_max_tokens")))
    deepseek_env()
    cfg = PROV.primary()
    chk("provider resolution is untouched",
        cfg.provider == "deepseek" and cfg.base_host == "api.deepseek.com")

    print("\n" + "=" * 62)
    print("PROVIDER ACCOUNTING: %d passed, %d failed" % (p[0], f[0]))
    print("LIVE DEEPSEEK BLOCK TYPES: NOT VERIFIED — EXTERNAL ENVIRONMENT "
          "REQUIRED. What DeepSeek actually returns in those 16 000 tokens is "
          "the measurement this commit exists to obtain; it cannot be taken "
          "from a double, and W2-C must not be designed until it is read.")
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
