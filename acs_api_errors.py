# -*- coding: utf-8 -*-
# =============================================================================
# acs_api_errors.py  --  عقد الأخطاء الموحّد لواجهة محرّك الفهم
#
# قاعدة واحدة لا استثناء لها: **كل** رد من الواجهة هو كائن JSON واحد صالح.
# لا traceback، ولا صفحة HTML، ولا نصّان مُلصقان. النجاح والفشل كلاهما JSON.
#
#   نجاح:  {"ok": true,  ...حمولة نقطة النهاية...}
#   فشل :  {"ok": false, "error": {"code","message","request_id",
#                                  "retryable","upstream"}}
#
# `upstream` هو null إن كان الخطأ محلياً، أو كائن يصف مصدر العطل الخارجي
# (المزوّد، صنف الخطأ، حالته) — **بلا أي سرّ ولا مفتاح ولا رأس تفويض**.
#
# هذا الملف بيانات وتصنيف فقط: لا يستورد FastAPI ولا anthropic، فيبقى
# قابلاً للاستيراد من طبقة الفهم ومن طبقة الواجهة معاً بلا دوران.
# =============================================================================

import re
import uuid

ERROR_CONTRACT_VERSION = "acs-error-envelope/1.0.0"

# ── رموز محلية (عطل عندنا أو في الطلب) ──────────────────────────────────────
ACS_BAD_REQUEST        = "ACS_BAD_REQUEST"
ACS_VALIDATION_FAILED  = "ACS_VALIDATION_FAILED"
ACS_PAYLOAD_TOO_LARGE  = "ACS_PAYLOAD_TOO_LARGE"
ACS_UNPROCESSABLE      = "ACS_UNPROCESSABLE"
ACS_NOT_FOUND          = "ACS_NOT_FOUND"
ACS_METHOD_NOT_ALLOWED = "ACS_METHOD_NOT_ALLOWED"
ACS_RATE_LIMITED       = "ACS_RATE_LIMITED"
ACS_TIMEOUT            = "ACS_TIMEOUT"
ACS_NOT_CONFIGURED     = "ACS_NOT_CONFIGURED"
ACS_INTERNAL           = "ACS_INTERNAL"
# F-33: عطلٌ في تكامل هذا الخادم مع مكتبة المزوّد — لا في المزوّد نفسه. مثاله
# المقيس: إرسال وسيط لا تعرفه النسخة المثبّتة، فترفع بايثون TypeError عند ربط
# الوسائط قبل أي بايت شبكة. كان يُصنَّف ACS_UPSTREAM_UNKNOWN، فيقرأ المستخدم
# «عطل من مزوّد النموذج» عن خطأ برمجيّ محلّي بحت، ويُسمَّم قياس أعطال المزوّد.
ACS_INTEGRATION_ERROR  = "ACS_INTEGRATION_ERROR"

# ── رموز المنبع (النموذج اللغوي / مزوّده) ───────────────────────────────────
ACS_UPSTREAM_NOT_CONFIGURED   = "ACS_UPSTREAM_NOT_CONFIGURED"
ACS_UPSTREAM_AUTH             = "ACS_UPSTREAM_AUTH"
ACS_UPSTREAM_PERMISSION       = "ACS_UPSTREAM_PERMISSION"
ACS_UPSTREAM_MODEL_REJECTED   = "ACS_UPSTREAM_MODEL_REJECTED"
ACS_UPSTREAM_BAD_REQUEST      = "ACS_UPSTREAM_BAD_REQUEST"
# F-50: رفضٌ من المزوّد سببه سقف المخرجات تحديداً. كان يندرج تحت
# ACS_UPSTREAM_BAD_REQUEST العامّ («رفض المزوّد صياغة الطلب») — وهي رسالة
# لا تُخبر المشغّل بشيء يفعله، بينما هذا العطل بالذات له إجراء واحد معروف:
# اضبط ACS_LLM_MODEL_MAX_OUTPUT على السقف الذي أعلنه المزوّد نفسه.
ACS_UPSTREAM_MAX_TOKENS       = "ACS_UPSTREAM_MAX_TOKENS"
# مقيس حيّاً (req_034b149147eb43a5): المزوّد ردّ 400 بـ
#   error.type=invalid_request_error
#   "Your credit balance is too low to access the Anthropic API…"
# فصُنّف ACS_UPSTREAM_BAD_REQUEST وقرأ المستخدم «رفض المزوّد صياغة الطلب».
# صياغة الطلب كانت سليمة تماماً؛ العطل تشغيليّ عند المشغّل. الرمز منفصل لأن
# الإجراء منفصل، والرسالة الظاهرة لا تكشف شيئاً عن حساب المشغّل ولا رصيده.
ACS_UPSTREAM_BILLING          = "ACS_UPSTREAM_BILLING"
ACS_UPSTREAM_RATE_LIMIT       = "ACS_UPSTREAM_RATE_LIMIT"
ACS_UPSTREAM_OVERLOADED       = "ACS_UPSTREAM_OVERLOADED"
ACS_UPSTREAM_UNAVAILABLE      = "ACS_UPSTREAM_UNAVAILABLE"
ACS_UPSTREAM_TIMEOUT          = "ACS_UPSTREAM_TIMEOUT"
ACS_UPSTREAM_CONNECTION       = "ACS_UPSTREAM_CONNECTION"
ACS_UPSTREAM_EMPTY_RESPONSE   = "ACS_UPSTREAM_EMPTY_RESPONSE"
# W2-E · رد وصل فعلاً، واستهلك ميزانيته، ولم يحمل حرفاً مرئياً واحداً.
# ليس EMPTY_RESPONSE: «أعاد النموذج رداً فارغاً» وصفٌ كاذب لستّة عشر ألف رمزٍ
# محاسَبة في كتلة تفكير — وهو ما قيس حيّاً. وليس TRUNCATED: لا يوجد نصفُ JSON
# يُقصّ. تمييزه يغيّر ثلاثة قرارات: أنه لا يُعاد كما هو، وأنه دليل بلوغ سقف
# يستدعي الشطر والتصعيد، وأن المشغّل يقرأ سببه الحقيقي في السجلّ.
ACS_UPSTREAM_NO_VISIBLE_OUTPUT = "ACS_UPSTREAM_NO_VISIBLE_OUTPUT"
ACS_UPSTREAM_INVALID_JSON     = "ACS_UPSTREAM_INVALID_JSON"
ACS_UPSTREAM_TRAILING_JSON    = "ACS_UPSTREAM_TRAILING_JSON"
ACS_UPSTREAM_TRUNCATED        = "ACS_UPSTREAM_TRUNCATED"
ACS_UPSTREAM_REFUSED          = "ACS_UPSTREAM_REFUSED"
ACS_UPSTREAM_UNKNOWN          = "ACS_UPSTREAM_UNKNOWN"

CODES = (
    ACS_BAD_REQUEST, ACS_VALIDATION_FAILED, ACS_PAYLOAD_TOO_LARGE,
    ACS_UNPROCESSABLE, ACS_NOT_FOUND, ACS_METHOD_NOT_ALLOWED,
    ACS_RATE_LIMITED, ACS_TIMEOUT, ACS_NOT_CONFIGURED, ACS_INTERNAL,
    ACS_INTEGRATION_ERROR,
    ACS_UPSTREAM_NOT_CONFIGURED, ACS_UPSTREAM_AUTH, ACS_UPSTREAM_PERMISSION,
    ACS_UPSTREAM_MODEL_REJECTED, ACS_UPSTREAM_BAD_REQUEST,
    ACS_UPSTREAM_MAX_TOKENS, ACS_UPSTREAM_BILLING,
    ACS_UPSTREAM_RATE_LIMIT, ACS_UPSTREAM_OVERLOADED,
    ACS_UPSTREAM_UNAVAILABLE, ACS_UPSTREAM_TIMEOUT, ACS_UPSTREAM_CONNECTION,
    ACS_UPSTREAM_EMPTY_RESPONSE, ACS_UPSTREAM_NO_VISIBLE_OUTPUT,
    ACS_UPSTREAM_INVALID_JSON,
    ACS_UPSTREAM_TRAILING_JSON, ACS_UPSTREAM_TRUNCATED, ACS_UPSTREAM_REFUSED,
    ACS_UPSTREAM_UNKNOWN,
)

UPSTREAM_CODES = tuple(c for c in CODES if c.startswith("ACS_UPSTREAM_"))

# أعادة المحاولة مسموحة لهذه وحدها. مفتاح خاطئ أو نموذج مرفوض لا يُصلحه التكرار،
# وتكراره يحرق الرصيد والزمن ويخفي السبب الحقيقي عن المستخدم.
RETRYABLE = frozenset({
    ACS_UPSTREAM_RATE_LIMIT, ACS_UPSTREAM_OVERLOADED,
    ACS_UPSTREAM_UNAVAILABLE, ACS_UPSTREAM_TIMEOUT,
    ACS_UPSTREAM_CONNECTION, ACS_UPSTREAM_EMPTY_RESPONSE,
    ACS_TIMEOUT,
})

# التحويل إلى مزوّد بديل مسموح لهذه وحدها — قائمة سماح، والافتراض المنع.
# قائمة منعٍ كانت ستفتح الباب لكل رمز جديد يُضاف لاحقاً بلا أن ينتبه أحد.
#
# ما ليس هنا، ولماذا:
#   ACS_INTEGRATION_ERROR     عطلنا نحن — سيتكرّر حرفياً عند أي مزوّد.
#   ACS_UPSTREAM_BAD_REQUEST  طلبنا نحن مُصاغ خطأً — كذلك.
#   ACS_UPSTREAM_MAX_TOKENS   ضبطُ سقفٍ عندنا — تحويله يخفي عطل ضبط.
#   ACS_UPSTREAM_AUTH/PERMISSION/MODEL_REJECTED  ضبط اعتماد أو معرّف.
#   ACS_UPSTREAM_INVALID_JSON / TRAILING_JSON / TRUNCATED / REFUSED /
#   EMPTY_RESPONSE            مخرج النموذج وصل وكان رديئاً؛ إعادة التوليد عند
#                             مزوّد آخر إنفاقٌ مضاعف على عطلٍ ليس عطل توفّر.
#   ACS_UPSTREAM_TIMEOUT      المهلة لا تثبت أن المزوّد لم يقبل الطلب: قد يكون
#                             يولّد الآن. إرسال نسخة ثانية يضاعف الكلفة على
#                             عملٍ ربّما اكتمل.
#   ACS_UPSTREAM_RATE_LIMIT   حدّ معدّل عابر له إعادة محاولة، لا تحويل.
# ACS_UPSTREAM_BILLING مشروطة بمفتاح صريح — انظر acs_provider.should_fallback.
FALLBACK_ELIGIBLE = frozenset({
    ACS_UPSTREAM_UNAVAILABLE,
    ACS_UPSTREAM_OVERLOADED,
    ACS_UPSTREAM_CONNECTION,
})

#: تُضاف إلى ما سبق فقط حين يُفعّل المشغّل ACS_LLM_FALLBACK_ON_BILLING.
FALLBACK_ELIGIBLE_ON_BILLING = frozenset({ACS_UPSTREAM_BILLING})

# ── W2-E · دلالة الرد: أربع حالات لا حالتان ────────────────────────────────
# كان المسار يعرف حالتين: «فيه نصّ» و«ليس فيه نصّ». فسقط الردّ الذي استهلك
# ميزانيته كلّها في كتلة تفكير — ردٌّ وصل، وكلّف ميزانية كاملة، ودلّ على بلوغ
# السقف — في خانة «رد فارغ»، فلم يُشطَر ولم يُصعَّد ووصل المستخدم 502 برسالة
# تقول إن النموذج لم يُجب. هذه الدالّة خالصة: لا SDK ولا شبكة ولا بيئة، تُختبَر
# وحدها على الحالات الأربع المقيسة حيّاً.
RESP_OK = "ok"
RESP_TRUNCATED = "truncated"
RESP_NO_VISIBLE_OUTPUT = "no_visible_output"
RESP_EMPTY = "empty"
RESP_REFUSED = "refused"
RESPONSE_SEMANTICS = (RESP_OK, RESP_TRUNCATED, RESP_NO_VISIBLE_OUTPUT,
                      RESP_EMPTY, RESP_REFUSED)

#: أدلّة بلوغ سقف المخرج. الشطر (F-39) وتصعيد الاستراتيجية (§12) يشترطان دليلاً
#: على بلوغ السقف لا رمزاً بعينه — فلا يُسقط رمزٌ جديد أحدَهما صامتاً.
CEILING_CODES = frozenset({ACS_UPSTREAM_TRUNCATED, ACS_UPSTREAM_NO_VISIBLE_OUTPUT})


def classify_response(stop_reason, visible_chars, text_blocks=0,
                      nontext_blocks=0):
    """دلالة ردٍّ وصل فعلاً → (الدلالة، رمز الخطأ أو None). دالّة خالصة.

    الترتيب مقصود، وكلّ فرعٍ منه حالةٌ مقيسة على الإنتاج (SHA 681ec04):

      · refusal                     → امتناع مُعلَن، مهما كان ما وصل.
      · نصّ مرئي + stop=max_tokens   → TRUNCATED. نصفُ JSON قُطِع، والشطر يفيده.
                                       (قِيس: out_chars=18982 عند 32000 رمزاً.)
      · نصّ مرئي + غير ذلك           → OK. الحكم على صلاحيته للمحلّل بعدُ.
      · بلا نصّ + كتلة غير نصّية     → NO_VISIBLE_OUTPUT. الميزانية ذهبت إلى
                                       محتوى لا نراه. (قِيس: out_tokens=16000،
                                       blocks=1، types=thinking:1، 0 حرف.)
      · بلا نصّ وبلا كتل             → EMPTY. لم يصل شيء أصلاً.

    ملاحظة على الترتيب: النصّ المرئي يُحكَم عليه **قبل** الكتل غير النصّية، فردٌّ
    يحمل تفكيراً ونصّاً معاً لا يُصنَّف «بلا مخرج مرئي» لمجرّد وجود التفكير —
    وهو الشكل الغالب في الحالات الناجحة المقيسة (blocks=2, text:1, thinking:1).
    """
    stop = str(stop_reason or "")
    try:
        chars = int(visible_chars or 0)
    except (TypeError, ValueError):
        chars = 0
    try:
        nontext = int(nontext_blocks or 0)
    except (TypeError, ValueError):
        nontext = 0

    if stop == "refusal":
        return RESP_REFUSED, ACS_UPSTREAM_REFUSED
    if chars > 0:
        if stop == "max_tokens":
            return RESP_TRUNCATED, ACS_UPSTREAM_TRUNCATED
        return RESP_OK, None
    if nontext > 0:
        return RESP_NO_VISIBLE_OUTPUT, ACS_UPSTREAM_NO_VISIBLE_OUTPUT
    return RESP_EMPTY, ACS_UPSTREAM_EMPTY_RESPONSE


# رمز → حالة HTTP. الحالة تصف ما يفعله العميل، لا مكان العطل.
HTTP_STATUS = {
    ACS_BAD_REQUEST: 400,
    ACS_VALIDATION_FAILED: 422,
    ACS_PAYLOAD_TOO_LARGE: 413,
    ACS_UNPROCESSABLE: 422,
    ACS_NOT_FOUND: 404,
    ACS_METHOD_NOT_ALLOWED: 405,
    ACS_RATE_LIMITED: 429,
    ACS_TIMEOUT: 504,
    ACS_NOT_CONFIGURED: 503,
    ACS_INTERNAL: 500,
    # 500 لا 502: العطل هنا، والمستخدم لا يملك ما يفعله سوى إبلاغ المشغّل.
    ACS_INTEGRATION_ERROR: 500,
    ACS_UPSTREAM_NOT_CONFIGURED: 503,
    ACS_UPSTREAM_AUTH: 502,
    ACS_UPSTREAM_PERMISSION: 502,
    ACS_UPSTREAM_MODEL_REJECTED: 502,
    ACS_UPSTREAM_BAD_REQUEST: 502,
    ACS_UPSTREAM_MAX_TOKENS: 502,
    # 503 لا 502: العطل ليس في الطلب ولا في المزوّد كخدمة، بل في توفّر الخدمة
    # لدينا. 503 هو ما يقرؤه وكيلٌ أو مراقبٌ على أنه «عُد لاحقاً»، وهو الصحيح.
    ACS_UPSTREAM_BILLING: 503,
    ACS_UPSTREAM_RATE_LIMIT: 429,
    ACS_UPSTREAM_OVERLOADED: 503,
    ACS_UPSTREAM_UNAVAILABLE: 503,
    ACS_UPSTREAM_TIMEOUT: 504,
    ACS_UPSTREAM_CONNECTION: 502,
    ACS_UPSTREAM_EMPTY_RESPONSE: 502,
    ACS_UPSTREAM_NO_VISIBLE_OUTPUT: 502,
    ACS_UPSTREAM_INVALID_JSON: 502,
    ACS_UPSTREAM_TRAILING_JSON: 502,
    ACS_UPSTREAM_TRUNCATED: 502,
    ACS_UPSTREAM_REFUSED: 502,
    ACS_UPSTREAM_UNKNOWN: 502,
}

# رسالة عربية واحدة لكل رمز — يراها المستخدم، فلا تحوي مسارات ولا أصناف بايثون.
MESSAGE_AR = {
    ACS_BAD_REQUEST: "الطلب غير صالح.",
    ACS_VALIDATION_FAILED: "بيانات الطلب لا تطابق العقد المطلوب.",
    ACS_PAYLOAD_TOO_LARGE: "حجم الطلب يتجاوز الحدّ المسموح.",
    ACS_UNPROCESSABLE: "تعذّر تنفيذ الطلب بمحتواه الحالي.",
    ACS_NOT_FOUND: "المسار غير موجود على هذا الخادم.",
    ACS_METHOD_NOT_ALLOWED: "طريقة الطلب غير مسموحة لهذا المسار.",
    ACS_RATE_LIMITED: "تجاوزت حدّ الطلبات المسموح. أعِد المحاولة لاحقاً.",
    ACS_TIMEOUT: "انتهت مهلة المعالجة على الخادم قبل اكتمال التوليد.",
    ACS_NOT_CONFIGURED: "الخادم غير مكتمل الضبط.",
    ACS_INTERNAL: "عطل داخلي غير متوقّع في الخادم.",
    ACS_INTEGRATION_ERROR: ("عطل في تكامل الخادم مع مكتبة مزوّد النموذج — "
                            "ليس عطلاً في طلبك ولا لدى المزوّد. أُبلِغ المشغّل، "
                            "ولا يفيد تكرار المحاولة."),
    ACS_UPSTREAM_NOT_CONFIGURED: "مفتاح المحرّك غير مضبوط على الخادم.",
    ACS_UPSTREAM_AUTH: "رفض مزوّد النموذج بيانات الاعتماد.",
    ACS_UPSTREAM_PERMISSION: "لا صلاحية لدى الخادم لاستخدام هذا النموذج.",
    ACS_UPSTREAM_MODEL_REJECTED: "رفض المزوّد معرّف النموذج المطلوب.",
    ACS_UPSTREAM_BAD_REQUEST: "رفض المزوّد صياغة الطلب.",
    # لا تذكر رصيداً ولا فوترةً ولا حساباً: المستخدم ليس المشغّل، وكشفُ حالة
    # حساب المشغّل له تسريبُ معلومة تشغيلية بلا فائدة له. التفصيل الآمن يبقى
    # في تليمتري المشغّل وحدها.
    ACS_UPSTREAM_BILLING: ("خدمة الذكاء الاصطناعي غير متاحة حالياً بسبب "
                           "إعدادات مزوّد الخدمة."),
    ACS_UPSTREAM_MAX_TOKENS: "طلب الخادم سقف مخرجات أعلى ممّا يسمح به "
                             "النموذج. راجع إعدادات النشر.",
    ACS_UPSTREAM_RATE_LIMIT: "بلغ المزوّد حدّ الطلبات. أعِد المحاولة بعد قليل.",
    ACS_UPSTREAM_OVERLOADED: "المزوّد مُحمَّل حالياً. أعِد المحاولة بعد قليل.",
    ACS_UPSTREAM_UNAVAILABLE: "خدمة المزوّد غير متاحة حالياً.",
    ACS_UPSTREAM_TIMEOUT: "انتهت مهلة انتظار رد النموذج.",
    ACS_UPSTREAM_CONNECTION: "تعذّر الاتصال بمزوّد النموذج.",
    ACS_UPSTREAM_EMPTY_RESPONSE: "أعاد النموذج رداً فارغاً.",
    ACS_UPSTREAM_NO_VISIBLE_OUTPUT: (
        "استهلك النموذج ميزانية المخرج كاملةً في محتوى غير مرئي ولم يُعِد نصّاً. "
        "حاول تقليل التفاصيل أو أعِد المحاولة."),
    ACS_UPSTREAM_INVALID_JSON: "رد النموذج ليس JSON صالحاً.",
    ACS_UPSTREAM_TRAILING_JSON: "رد النموذج يحوي أكثر من كائن JSON — لن نخمّن أيّها النموذج.",
    ACS_UPSTREAM_TRUNCATED: (
        "تعذّر إكمال النموذج لأن الاستجابة تجاوزت حدّ التوليد. "
        "حاول تقليل التفاصيل أو أعِد المحاولة."),
    ACS_UPSTREAM_REFUSED: "امتنع النموذج عن إكمال هذا الطلب.",
    ACS_UPSTREAM_UNKNOWN: "عطل غير مصنّف من مزوّد النموذج.",
}


def new_request_id():
    """معرّف طلب قصير قابل للنسخ من الشاشة ومطابقته بالسجلّ."""
    return "req_" + uuid.uuid4().hex[:16]


# ── تعقيم: لا يخرج سرّ إلى العميل ولا إلى السجلّ تحت أي ظرف ─────────────────
_SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)\b(x-api-key|authorization|api[_-]?key)\b\s*[:=]\s*\S+"),
)


def redact(text):
    """يستبدل أي شكل يشبه المفتاح بعلامة ثابتة. يُطبَّق على كل رسالة خارجة."""
    s = "" if text is None else str(text)
    for pat in _SECRET_PATTERNS:
        s = pat.sub("[REDACTED]", s)
    return s


class AcsApiError(Exception):
    """خطأ يحمل رمزه وحالته — يُترجَم إلى المغلّف حرفياً بلا تخمين."""

    def __init__(self, code, message=None, upstream=None, status=None,
                 retryable=None, retry_after=None):
        self.code = code if code in HTTP_STATUS else ACS_INTERNAL
        self.message = redact(message or MESSAGE_AR.get(self.code, MESSAGE_AR[ACS_INTERNAL]))
        self.upstream = upstream
        self.status = int(status or HTTP_STATUS[self.code])
        self.retryable = bool(self.code in RETRYABLE if retryable is None else retryable)
        self.retry_after = retry_after
        super().__init__("%s: %s" % (self.code, self.message))

    def envelope(self, request_id):
        return envelope(self.code, self.message, request_id,
                        retryable=self.retryable, upstream=self.upstream)


def envelope(code, message, request_id, retryable=None, upstream=None):
    """المغلّف الوحيد للفشل. الشكل ثابت — لا حقل ناقص ولا حقل زائد."""
    code = code if code in HTTP_STATUS else ACS_INTERNAL
    if retryable is None:
        retryable = code in RETRYABLE
    up = None
    if upstream:
        # لا نمرّر إلا حقولاً معروفة، ومعقّمة — أي حقل غريب يُسقَط.
        up = {"provider": redact(upstream.get("provider") or "anthropic"),
              "kind": redact(upstream.get("kind") or "unknown"),
              "status": upstream.get("status") if isinstance(
                  upstream.get("status"), int) else None,
              "attempts": upstream.get("attempts") if isinstance(
                  upstream.get("attempts"), int) else None}
    return {"ok": False,
            "error": {"code": code,
                      "message": redact(message or MESSAGE_AR.get(code, "")),
                      "request_id": request_id,
                      "retryable": bool(retryable),
                      "upstream": up},
            "contract": ERROR_CONTRACT_VERSION}


# ── تصنيف أعطال المنبع ──────────────────────────────────────────────────────
# نصنّف باسم الصنف وبحالة HTTP إن توفّرت، لا بمطابقة نصّ الرسالة وحدها:
# نصّ المزوّد يتغيّر بين الإصدارات، بينما اسم الصنف والحالة عقد أوضح.
_BY_CLASS = (
    ("AuthenticationError",   ACS_UPSTREAM_AUTH),
    ("PermissionDeniedError", ACS_UPSTREAM_PERMISSION),
    ("NotFoundError",         ACS_UPSTREAM_MODEL_REJECTED),
    ("RateLimitError",        ACS_UPSTREAM_RATE_LIMIT),
    ("APITimeoutError",       ACS_UPSTREAM_TIMEOUT),
    ("APIConnectionError",    ACS_UPSTREAM_CONNECTION),
    ("BadRequestError",       ACS_UPSTREAM_BAD_REQUEST),
    ("InternalServerError",   ACS_UPSTREAM_UNAVAILABLE),
    ("APIStatusError",        ACS_UPSTREAM_UNKNOWN),
)

_BY_STATUS = {400: ACS_UPSTREAM_BAD_REQUEST, 401: ACS_UPSTREAM_AUTH,
              # deepseek يعلن 402 «Insufficient Balance» صراحةً — حالةٌ
              # لا تحتمل تأويلاً، فلا تحتاج مطابقة نصّ.
              402: ACS_UPSTREAM_BILLING,
              403: ACS_UPSTREAM_PERMISSION, 404: ACS_UPSTREAM_MODEL_REJECTED,
              408: ACS_UPSTREAM_TIMEOUT, 413: ACS_UPSTREAM_BAD_REQUEST,
              429: ACS_UPSTREAM_RATE_LIMIT, 500: ACS_UPSTREAM_UNAVAILABLE,
              502: ACS_UPSTREAM_UNAVAILABLE, 503: ACS_UPSTREAM_UNAVAILABLE,
              529: ACS_UPSTREAM_OVERLOADED}


# ── F-50 · استخراج آمن لسبب رفض المزوّد ─────────────────────────────────────
# العطل الذي يغلقه هذا القسم
# --------------------------
#     POST /v1/understand → 502 ACS_UPSTREAM_BAD_REQUEST
#     upstream_class=BadRequestError · duration_ms=884
# و**لا شيء غير ذلك**. المزوّد يردّ 400 بجسدٍ منظَّم يسمّي الوسيط المخالف
# ويذكر حدّه، وclassify_upstream كان يحتفظ بأربعة حقول فقط —
# (provider, kind, status, attempts) — ويُلقي الباقي. فيصل المشغّل خبرٌ لا
# يقود إلى أي إجراء: «رفض المزوّد صياغة الطلب». الطلب فيه عشرة وسائط، وأيّها
# المخالف لا يُعرَف إلّا بتخمين.
#
# ما يُستخرَج هنا **مصنَّفات لا نصّ حرّ**: نوع الخطأ من المزوّد، واسم الوسيط
# من قائمة معلنة، والأرقام. والرسالة نفسها تمرّ بمصفاة صارمة (ASCII فقط،
# محدودة الطول، بعد redact) — وهي كافية لأنّ رسائل التحقّق عند المزوّد تصف
# **شكل** الطلب لا محتواه، والمحتوى هنا عربيّ فتسقطه المصفاة حتماً.

#: أسماء وسائط واجهة الرسائل. لا يُسجَّل اسمٌ خارج هذه القائمة أبداً.
PROVIDER_PARAMS = (
    "max_tokens", "model", "messages", "system", "thinking", "temperature",
    "top_p", "top_k", "stop_sequences", "stream", "tools", "tool_choice",
    "metadata", "anthropic-beta", "anthropic-version", "container",
    "service_tier", "mcp_servers", "betas",
)

#: أنواع الأخطاء التي يعلنها المزوّد. أي نوع آخر يُسجَّل "other".
PROVIDER_ERROR_TYPES = (
    "invalid_request_error", "authentication_error", "permission_error",
    "not_found_error", "request_too_large", "rate_limit_error",
    "api_error", "overloaded_error", "billing_error",
)

#: شواهد الرصيد/الحساب الصريحة. لا يُصنَّف 400 عامّ فوترةً أبداً — يجب أن يقول
#: المزوّد ذلك بنفسه. القائمة صريحة ومحدودة عمداً: توسيعها بمرادفات ظنّية يحوّل
#: كل رفض غامض إلى «فوترة»، فيُرسل المشغّل إلى صفحة الدفع بدل سبب العطل.
BILLING_MARKERS = (
    "credit balance",          # anthropic — مقيس حيّاً
    "purchase credits",        # anthropic — مقيس حيّاً
    "billing",                 # عامّ لدى المزوّدَين
    "account balance",
    "insufficient balance",    # deepseek — 402 Insufficient Balance
    "run out of balance",      # deepseek — نصّ التوثيق
    "quota",
)

_ASCII_SAFE = re.compile(r"[^\x20-\x7E]+")
_MAXTOK_RE = re.compile(
    r"max_tokens\s*:?\s*(\d+)\s*>\s*(\d+)", re.I)
_LIMIT_RE = re.compile(r"maximum allowed number of output tokens[^0-9]{0,40}(\d+)",
                       re.I)


def _provider_body(exc):
    """جسد الخطأ المنظَّم من المزوّد إن وُجد. لا يرمي أبداً."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            j = resp.json()
            if isinstance(j, dict):
                return j
        except Exception:                                       # noqa: BLE001
            pass
    return None


def safe_provider_detail(exc, max_chars=240):
    """حقولٌ آمنة تصف **سبب** رفض المزوّد. لا مفتاح ولا نصّ زائر ولا جسد خام.

    تعيد قاموساً قد يحمل:
        error_type   نوعٌ من PROVIDER_ERROR_TYPES أو "other"
        param        اسمٌ من PROVIDER_PARAMS وحدها
        requested    العدد الذي طلبه الخادم (حين يذكره المزوّد)
        limit        الحدّ الذي يسمح به المزوّد (حين يذكره)
        provider_request_id  معرّف الطلب عند المزوّد، للمراسلة
        detail       رسالة التحقّق **بعد** التنقية: ASCII فقط ومحدودة الطول
    """
    out = {}
    body = _provider_body(exc)
    err = body.get("error") if isinstance(body, dict) else None
    msg = ""
    if isinstance(err, dict):
        t = str(err.get("type") or "")
        out["error_type"] = t if t in PROVIDER_ERROR_TYPES else (
            "other" if t else None)
        msg = str(err.get("message") or "")
    if not msg:
        msg = str(getattr(exc, "message", "") or "")
    if not msg:
        msg = str(exc)

    # الرقم المطلوب والحدّ المسموح — من صياغة المزوّد القانونية نفسها.
    m = _MAXTOK_RE.search(msg)
    if m:
        out["requested"] = int(m.group(1))
        out["limit"] = int(m.group(2))
    else:
        m2 = _LIMIT_RE.search(msg)
        if m2:
            out["limit"] = int(m2.group(1))

    # اسم الوسيط: المزوّد يضعه **بادئةً قبل أوّل نقطتين** —
    #     "stream: must be true when max_tokens is greater than 21333"
    # المخالف هنا `stream` لا `max_tokens`، والأخير مذكورٌ في الشرح وحده.
    # لذلك تُقرأ البادئة أوّلاً، ولا يُلجأ إلى المسح العامّ إلّا إن غابت —
    # وإلّا نُسب العطل إلى الوسيط الخطأ وأُرسل المشغّل إلى الجهة الخطأ.
    low = msg.lower()
    head = low.split(":", 1)[0].strip() if ":" in low else ""
    root = head.split(".", 1)[0].strip() if head else ""
    if root in PROVIDER_PARAMS:
        out["param"] = root
    else:
        for name in sorted(PROVIDER_PARAMS, key=len, reverse=True):
            if name in low:
                out["param"] = name
                break

    rid = getattr(exc, "request_id", None)
    if isinstance(rid, str) and 0 < len(rid) <= 64:
        out["provider_request_id"] = rid

    # المصفاة: redact ثم إسقاط كل ما ليس ASCII مطبوعاً ثم قصّ. الوصف والتوجيه
    # في هذا المشروع عربيّان، فإسقاط غير ASCII يمحوهما حتماً لو تسرّبا.
    clean = _ASCII_SAFE.sub(" ", redact(msg))
    clean = " ".join(clean.split())[:int(max_chars)]
    if clean:
        out["detail"] = clean
    return out


def is_billing_evidence(detail, status=None):
    """هل يثبت المزوّد بنفسه أن العطل رصيد/حساب؟ الافتراض «لا».

    ثلاثة شواهد مقبولة، وكلّها من المزوّد لا من تخميننا:
      • حالة 402 المخصّصة لذلك عند deepseek،
      • error.type = billing_error،
      • عبارة صريحة من BILLING_MARKERS في رسالة التحقّق.
    ما عدا ذلك يبقى على تصنيفه — 400 غامض ليس فوترةً.
    """
    if status == 402:
        return True
    d = detail if isinstance(detail, dict) else {}
    if d.get("error_type") == "billing_error":
        return True
    text = str(d.get("detail") or "").lower()
    return any(mark in text for mark in BILLING_MARKERS) if text else False


def classify_upstream(exc, attempts=None, provider="anthropic"):
    """استثناء من مسار النموذج → AcsApiError مصنّف. لا يرمي أبداً.

    `provider` يدخل الحقل `upstream.provider` وحده. كان الاسم مثبّتاً
    "anthropic" في النصّ، فكان سجلّ نشرٍ على deepseek يسمّي المزوّد الخطأ في كل
    عطل — أسوأ من غياب الحقل، لأنه غيابٌ يبدو معلومة.
    """
    if isinstance(exc, AcsApiError):
        return exc
    name = type(exc).__name__
    status = None
    for attr in ("status_code", "http_status", "code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int):
            status = v
            break
    if status is None:
        resp = getattr(exc, "response", None)
        v = getattr(resp, "status_code", None)
        if isinstance(v, int):
            status = v

    code = None
    for cls, c in _BY_CLASS:
        if cls == name:
            code = c
            break
    if code in (None, ACS_UPSTREAM_UNKNOWN) and status in _BY_STATUS:
        code = _BY_STATUS[status]
    if code is None:
        low = str(exc).lower()
        if "timed out" in low or "timeout" in low:
            code = ACS_UPSTREAM_TIMEOUT
        elif "overloaded" in low:
            code = ACS_UPSTREAM_OVERLOADED
        elif isinstance(exc, (ConnectionError, OSError)):
            code = ACS_UPSTREAM_CONNECTION
        else:
            code = ACS_UPSTREAM_UNKNOWN
    # F-50: سبب الرفض يُستخرَج ويُحفَظ. كان يُلقى، فيصل المشغّل
    # `upstream_class=BadRequestError` وحدها — خبرٌ لا يقود إلى إجراء.
    detail = {}
    try:
        detail = safe_provider_detail(exc)
    except Exception:                                           # noqa: BLE001
        detail = {}
    # الفوترة تُفحَص **قبل** سقف الرموز: رفض الرصيد يأتي 400 بلا وسيط مخالف
    # وبلا حدّ، فلا يتنازع الفرعان — لكن الترتيب يجعل ذلك خاصيّةً لا مصادفة.
    if code in (ACS_UPSTREAM_BAD_REQUEST, ACS_UPSTREAM_UNKNOWN,
                ACS_UPSTREAM_PERMISSION, ACS_UPSTREAM_BILLING) and \
            is_billing_evidence(detail, status):
        code = ACS_UPSTREAM_BILLING
    # 400 سببه سقف المخرجات له رمزه: الإجراء معروف، فلا يُخفى تحت العامّ.
    # الشرط: `max_tokens` هو الوسيط **المخالف**، أو أن المزوّد ذكر حدّ
    # المخرجات صراحةً. ذكرُ max_tokens في شرح عطلٍ آخر لا يكفي.
    elif code == ACS_UPSTREAM_BAD_REQUEST and (
            detail.get("param") == "max_tokens"
            or detail.get("limit") is not None):
        code = ACS_UPSTREAM_MAX_TOKENS
    up = {"provider": provider or "anthropic", "kind": name,
          "status": status, "attempts": attempts}
    for key in ("error_type", "param", "requested", "limit",
                "provider_request_id", "detail"):
        if detail.get(key) is not None:
            up[key] = detail[key]
    return AcsApiError(code, MESSAGE_AR[code], upstream=up)
