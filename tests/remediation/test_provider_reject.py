# -*- coding: utf-8 -*-
"""F-50 — رفض المزوّد 400 يصير قابلاً للتشخيص، وسقف النموذج يصير مصدراً واحداً.

    python3 tests/remediation/test_provider_reject.py

العطل الإنتاجي
--------------
    POST /v1/understand → 502  ACS_UPSTREAM_BAD_REQUEST
    request_id=req_1e1db28104a9462e · duration_ms=884
    generation_job: error_code=ACS_UPSTREAM_BAD_REQUEST state=FAILED
    request_failed: status=502 upstream_class=BadRequestError

و**لا شيء غير ذلك**. ثمانمئة وأربع وثمانون جزءاً من الألف تعني أن الطلب وصل
المزوّد فعلاً ورُفض بالتحقّق — لا عطلاً محلّياً (KI-23 كان ٣٨٩ms بلا شبكة).
والمزوّد يردّ 400 بجسدٍ منظَّم يسمّي الوسيط المخالف ويذكر حدّه، لكن
`classify_upstream` كان يحتفظ بأربعة حقول — provider/kind/status/attempts —
ويُلقي الباقي. فالطلب فيه عشرة وسائط، وأيّها المخالف لا يُعرَف إلّا بتخمين.

وثلاث فجوات أخرى في السجلّ كانت تُطبق الباب:
  · `sdk_version` يُقاس في acs_understand ثم تُسقطه قائمة السماح في
    acs_logging صامتةً — نفس عطل KI-24/F-38 في موضع آخر.
  · `max_output_tokens` لا يُملأ إلّا بعد **نجاح** الرد، فسجلّ كل نداء فاشل
    يقول null — أي أن أهمّ رقم في تشخيص رفض 400 يغيب عن الحالة الوحيدة التي
    يلزم فيها.
  · لا ثابت في المستودع كلّه يقول كم يقبل النموذج من رموز مخرجة. كل سقف
    مشتقّ من ACS_LLM_MAX_OUTPUT_TOKENS — رقم المشغّل، لا قدرة النموذج.

نطاق مُعلَن: لا مفتاح ولا شبكة هنا. الرفض يُحاكى بشكل استثناء SDK الحقيقي
(status_code · body · message · request_id)، والمقيس هو **الاستخراج
والتصنيف والتسجيل** — وهي كلّ ما كان مفقوداً. النداء الحيّ يبقى:
LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
"""
import importlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                       # noqa: E402
import acs_generation as G                                       # noqa: E402
import acs_logging as LOGGING                                    # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


class BadRequestError(Exception):
    """شكل anthropic.BadRequestError: status_code · body · message · request_id."""

    def __init__(self, message, etype="invalid_request_error", rid=None):
        Exception.__init__(self, message)
        self.message = message
        self.status_code = 400
        self.request_id = rid
        self.body = {"type": "error",
                     "error": {"type": etype, "message": message}}


class NotFoundError(BadRequestError):
    def __init__(self, message):
        BadRequestError.__init__(self, message, "not_found_error")
        self.status_code = 404


def main():
    # ═══ أ · الاستخراج الآمن ═══════════════════════════════════════════════
    print("\n== أ · سبب الرفض يُستخرَج مصنَّفاً لا نصّاً حرّاً ==")
    CASES = [
        ("max_tokens: 32000 > 8192, which is the maximum allowed number of "
         "output tokens for claude-sonnet-5",
         E.ACS_UPSTREAM_MAX_TOKENS, "max_tokens", 32000, 8192),
        ("max_tokens: 17701 > 16384, which is the maximum allowed number of "
         "output tokens for claude-sonnet-5",
         E.ACS_UPSTREAM_MAX_TOKENS, "max_tokens", 17701, 16384),
        ("thinking.budget_tokens: Field required",
         E.ACS_UPSTREAM_BAD_REQUEST, "thinking", None, None),
        ("messages: at least one message is required",
         E.ACS_UPSTREAM_BAD_REQUEST, "messages", None, None),
        ("messages.0.content.0.text: Field required",
         E.ACS_UPSTREAM_BAD_REQUEST, "messages", None, None),
        ("system: text content blocks must be non-empty",
         E.ACS_UPSTREAM_BAD_REQUEST, "system", None, None),
        ("temperature: may not be used with top_p",
         E.ACS_UPSTREAM_BAD_REQUEST, "temperature", None, None),
        ("stream: must be true when max_tokens is greater than 21333",
         E.ACS_UPSTREAM_BAD_REQUEST, "stream", None, None),
        ("anthropic-beta: unrecognized beta header",
         E.ACS_UPSTREAM_BAD_REQUEST, "anthropic-beta", None, None),
    ]
    for msg, want_code, want_param, want_req, want_lim in CASES:
        err = E.classify_upstream(BadRequestError(msg, rid="req_prov_1"))
        up = err.upstream or {}
        ok = (err.code == want_code and up.get("param") == want_param
              and up.get("requested") == want_req
              and up.get("limit") == want_lim
              and up.get("error_type") == "invalid_request_error"
              and up.get("status") == 400)
        chk("%-42s → %s · param=%s%s"
            % (msg[:42], want_code.replace("ACS_UPSTREAM_", ""), want_param,
               (" · limit=%s" % want_lim) if want_lim else ""),
            ok, json.dumps(up, ensure_ascii=False)[:150])
    other = E.classify_upstream(BadRequestError(
        "stream: must be true when max_tokens is greater than 21333"))
    chk("وذكر max_tokens في شرح عطلٍ آخر لا يُصنَّف عطل سقف",
        other.code == E.ACS_UPSTREAM_BAD_REQUEST
        and (other.upstream or {}).get("param") == "stream",
        json.dumps(other.upstream, ensure_ascii=False)[:140])
    err = E.classify_upstream(BadRequestError("x", rid="req_prov_9"))
    chk("ومعرّف طلب المزوّد محفوظ للمراسلة",
        (err.upstream or {}).get("provider_request_id") == "req_prov_9")

    # ═══ ب · لا تسريب ═══════════════════════════════════════════════════════
    print("\n== ب · لا مفتاح ولا نصّ زائر ولا جسد خام ==")
    KEY = "sk-" + "ant-" + "A" * 40
    ARABIC = "مستودع 120×80 فيه اثنا عشر رصيف تحميل وستّة عمّال"
    leaky = BadRequestError(
        "system: %s rejected with %s ; max_tokens: 9 > 8" % (ARABIC, KEY))
    up = (E.classify_upstream(leaky).upstream or {})
    blob = json.dumps(up, ensure_ascii=False)
    chk("لا مفتاح في الحمولة", KEY not in blob and "sk-ant" not in blob)
    chk("ولا حرف عربيّ واحد (المصفاة تُسقط غير ASCII)",
        not re.search(r"[؀-ۿ]", blob), blob[:120])
    chk("ولا الجسد الخام", '"type": "error"' not in blob)
    # الوسيط المخالف هنا `system` (البادئة)، لا `max_tokens` المذكور في الشرح —
    # وهذا ما يجب أن يقوله الاستخراج. والأرقام تنجو رغم التنقية.
    chk("والحقول المصنَّفة نجت رغم التنقية",
        up.get("param") == "system" and up.get("limit") == 8
        and up.get("requested") == 9, json.dumps(up, ensure_ascii=False)[:140])
    long_msg = "max_tokens: " + ("Z" * 4000)
    up2 = (E.classify_upstream(BadRequestError(long_msg)).upstream or {})
    chk("والرسالة مقصوصة بحدّ معلن", len(up2.get("detail") or "") <= 240,
        str(len(up2.get("detail") or "")))
    chk("واسم الوسيط من القائمة المعلنة وحدها",
        (E.classify_upstream(BadRequestError(
            "frobnicate: not a real parameter")).upstream or {}).get("param")
        is None)
    chk("ونوع خطأ غير معروف يُسجَّل other لا حرفياً",
        (E.classify_upstream(BadRequestError(
            "x", etype="wormhole_error")).upstream or {}).get("error_type")
        == "other")

    # ═══ ج · لا انحدار في التصنيفات القائمة ════════════════════════════════
    print("\n== ج · التصنيفات القائمة لم تتغيّر ==")
    chk("404 يبقى ACS_UPSTREAM_MODEL_REJECTED لا max_tokens",
        E.classify_upstream(NotFoundError(
            "model: claude-sonnet-5 not found")).code
        == E.ACS_UPSTREAM_MODEL_REJECTED)
    chk("و400 بلا ذكر سقف يبقى ACS_UPSTREAM_BAD_REQUEST",
        E.classify_upstream(BadRequestError(
            "messages: too many")).code == E.ACS_UPSTREAM_BAD_REQUEST)
    chk("وكلاهما 502 في عقد HTTP",
        E.HTTP_STATUS[E.ACS_UPSTREAM_MAX_TOKENS] == 502
        and E.HTTP_STATUS[E.ACS_UPSTREAM_BAD_REQUEST] == 502)
    chk("والرمز الجديد مُعلَن في جدول الرموز",
        E.ACS_UPSTREAM_MAX_TOKENS in E.CODES
        and E.ACS_UPSTREAM_MAX_TOKENS in E.MESSAGE_AR)
    chk("ورسالته تدلّ المشغّل على إجراء لا على وصف",
        "النموذج" in E.MESSAGE_AR[E.ACS_UPSTREAM_MAX_TOKENS])

    # ═══ د · السجلّ يمرّر الحقول التشخيصية ═════════════════════════════════
    print("\n== د · قناة السجلّ لم تعد تُسقط ما يلزم للتشخيص ==")
    src = io.open(os.path.join(ROOT, "acs_logging.py"), encoding="utf-8").read()
    need = ("sdk_version", "transport", "thinking_sent", "provider_error_type",
            "provider_param", "provider_limit", "provider_detail",
            "requested_max_tokens")
    for name in need:
        chk("قائمة السماح تُعلن %s" % name, '"%s"' % name in src)
    us = io.open(os.path.join(ROOT, "acs_understand.py"),
                 encoding="utf-8").read()
    chk("والمُصدِر يملأها كلّها",
        all(('"%s": tel.get(' % n) in us for n in
            ("sdk_version", "transport", "thinking_sent",
             "requested_max_tokens", "provider_error_type",
             "provider_param", "provider_limit", "provider_detail")))
    # W2-D غيّر توقيع `_call` (صار يأخذ وسائط مبنيّة سلفاً حتى يمكن بصمُها قبل
    # الإرسال). الثابت المحروس هو ثابت F-50 نفسه ولم يتغيّر: يُسجَّل السقف
    # المطلوب **قبل** أن يُنادى المزوّد. تُقاس المواضع بالمحلّل لا بتهجئة النداء.
    import ast as _ast
    _t = _ast.parse(us)
    _rec = [n.lineno for n in _ast.walk(_t)
            if isinstance(n, _ast.Assign)
            and any(isinstance(tg, _ast.Subscript)
                    and isinstance(tg.slice, _ast.Constant)
                    and tg.slice.value == "requested_max_tokens"
                    for tg in n.targets)]
    _callsites = [n.lineno for n in _ast.walk(_t)
                  if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
                  and n.func.id == "_call"]
    chk("والسقف المطلوب يُسجَّل **قبل** النداء لا بعد نجاحه",
        bool(_rec) and bool(_callsites) and min(_rec) < min(_callsites),
        "record@%s call@%s" % (_rec, _callsites))
    # القناة الحقيقية: هل تمرّ الحقول فعلاً؟
    buf = io.StringIO()
    try:
        LOGGING.StructuredLogger(buf).generation(
            sdk_version="0.40.0", transport="stream", thinking_sent=False,
            requested_max_tokens=32000, provider_error_type="invalid_request_error",
            provider_param="max_tokens", provider_limit=8192,
            provider_detail="max_tokens: 32000 > 8192", success=False,
            error_code=E.ACS_UPSTREAM_MAX_TOKENS,
            upstream_class="BadRequestError", api_key="sk-ant-LEAK")
    finally:
        pass
    line = buf.getvalue()
    rec = json.loads(line.strip().splitlines()[-1])
    for name in need:
        chk("والحدث الفعليّ يحمل %s" % name, name in rec, line[:120])
    chk("ولا يحمل حقلاً غير معلن (api_key أُسقط)", "api_key" not in rec)
    chk("ولا قيمة المفتاح", "LEAK" not in line)

    # ═══ هـ · سقف قدرة النموذج: مصدر واحد ═════════════════════════════════
    print("\n== هـ · F-50: سقف واحد مُعلَن يقصّ كل مسار ==")
    saved = dict(os.environ)
    try:
        os.environ["ACS_LLM_MAX_OUTPUT_TOKENS"] = "32000"
        os.environ.pop("ACS_LLM_MODEL_MAX_OUTPUT", None)
        for k in list(os.environ):
            if k.startswith("ACS_MAX_TOKENS"):
                os.environ.pop(k)
        importlib.reload(G)
        PC = importlib.reload(importlib.import_module("acs_plan_chunks"))
        before = {s: G.stage_budget(s)
                  for s in ("single", "plan", "detail", "repair")}
        before["outline"] = PC.outline_budget()
        chk("بلا إعلان: السلوك كما كان تماماً (لا رقم مخترَع)",
            before == {"single": 32000, "plan": 16000, "detail": 24000,
                       "repair": 32000, "outline": 17701},
            json.dumps(before))
        chk("و model_max_output() تعيد None لا تخميناً",
            G.model_max_output() is None)

        os.environ["ACS_LLM_MODEL_MAX_OUTPUT"] = "8192"
        importlib.reload(G)
        PC = importlib.reload(importlib.import_module("acs_plan_chunks"))
        after = {s: G.stage_budget(s)
                 for s in ("single", "plan", "detail", "repair")}
        after["outline"] = PC.outline_budget()
        chk("وبإعلانه: **كل** مسار مقصوص بلا استثناء",
            all(v <= 8192 for v in after.values()), json.dumps(after))
        chk("ولا يُرفَع سقفٌ كان أدنى",
            after["plan"] == 8192 and G.clamp_to_model(100) == (100, False))
        chk("والقصّ مُعلَن لا صامت", G.clamp_to_model(99999) == (8192, True))

        # التجاوزات القديمة تمرّ بالقصّ أيضاً — وإلّا بقي مسار غير مقصوص.
        os.environ["ACS_MAX_TOKENS_PLAN"] = "30000"
        os.environ["ACS_MAX_TOKENS_OUTLINE"] = "30000"
        importlib.reload(G)
        PC = importlib.reload(importlib.import_module("acs_plan_chunks"))
        chk("والتجاوز القديم ACS_MAX_TOKENS_PLAN مقصوص",
            G.stage_budget("plan") == 8192, str(G.stage_budget("plan")))
        chk("والتجاوز ACS_MAX_TOKENS_OUTLINE مقصوص",
            PC.outline_budget() == 8192, str(PC.outline_budget()))
        os.environ.pop("ACS_MAX_TOKENS_PLAN")
        os.environ.pop("ACS_MAX_TOKENS_OUTLINE")

        # المسح الشامل: لا مسار في المستودع يبني سقفاً غير مقصوص.
        os.environ["ACS_LLM_MODEL_MAX_OUTPUT"] = "4096"
        importlib.reload(G)
        PC = importlib.reload(importlib.import_module("acs_plan_chunks"))
        every = [G.stage_budget(s) for s in
                 ("single", "plan", "detail", "repair", "unknown_stage")]
        every += [PC.outline_budget(), PC.plan_chunk_budget()]
        chk("وعند سقفٍ منخفض جداً لا يتجاوزه أيّ سقف مُنتَج",
            all(v <= 4096 for v in every), json.dumps(every))
        chk("ولا ينزل أيٌّ منها تحت أرضية المرحلة المعلنة",
            all(v >= min(G.STAGE_FLOOR, 4096) for v in every),
            json.dumps(every))
    finally:
        os.environ.clear()
        os.environ.update(saved)
        importlib.reload(G)
        importlib.reload(importlib.import_module("acs_plan_chunks"))

    # ═══ و · العقود القائمة لم تُمَسّ ══════════════════════════════════════
    print("\n== و · KI-23 و KI-24 و العقد المحلّي لم تُمَسّ ==")
    chk("KI-23 قائم: thinking مشروط بدعم النسخة",
        "if thinking is not None and supports_thinking" in us)
    chk("و AttributeError وحده يفتح الرجوع إلى create()",
        "except AttributeError:" in us
        and "except (AttributeError, TypeError):" not in us)
    chk("وعطل الوسائط المحلّي يبقى ACS_INTEGRATION_ERROR لا عطل مزوّد",
        "E.ACS_INTEGRATION_ERROR" in us and "local_integration" in us)
    chk("و KI-24 قائم: حصّة plan نصف الميزانية",
        G.STAGE_SHARE["plan"] == 0.50)
    chk("ولم تُرفَع أي حصّة مرحلة",
        G.STAGE_SHARE == {"single": 1.00, "plan": 0.50, "detail": 0.75,
                          "repair": 1.00}, json.dumps(G.STAGE_SHARE))

    print("\n" + "─" * 62)
    print("LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED")
    print("  (no ANTHROPIC_API_KEY and no egress here; what is measured is the")
    print("   extraction, classification, clamping and logging — the parts that")
    print("   were missing and that make the next live 400 self-describing.)")
    print("PROVIDER REJECTION DIAGNOSTICS: %d passed, %d failed" % (p[0], f[0]))
    if f[0]:
        sys.exit(1)


if __name__ == "__main__":
    main()
