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

# ── رموز المنبع (النموذج اللغوي / مزوّده) ───────────────────────────────────
ACS_UPSTREAM_NOT_CONFIGURED   = "ACS_UPSTREAM_NOT_CONFIGURED"
ACS_UPSTREAM_AUTH             = "ACS_UPSTREAM_AUTH"
ACS_UPSTREAM_PERMISSION       = "ACS_UPSTREAM_PERMISSION"
ACS_UPSTREAM_MODEL_REJECTED   = "ACS_UPSTREAM_MODEL_REJECTED"
ACS_UPSTREAM_BAD_REQUEST      = "ACS_UPSTREAM_BAD_REQUEST"
ACS_UPSTREAM_RATE_LIMIT       = "ACS_UPSTREAM_RATE_LIMIT"
ACS_UPSTREAM_OVERLOADED       = "ACS_UPSTREAM_OVERLOADED"
ACS_UPSTREAM_UNAVAILABLE      = "ACS_UPSTREAM_UNAVAILABLE"
ACS_UPSTREAM_TIMEOUT          = "ACS_UPSTREAM_TIMEOUT"
ACS_UPSTREAM_CONNECTION       = "ACS_UPSTREAM_CONNECTION"
ACS_UPSTREAM_EMPTY_RESPONSE   = "ACS_UPSTREAM_EMPTY_RESPONSE"
ACS_UPSTREAM_INVALID_JSON     = "ACS_UPSTREAM_INVALID_JSON"
ACS_UPSTREAM_TRAILING_JSON    = "ACS_UPSTREAM_TRAILING_JSON"
ACS_UPSTREAM_TRUNCATED        = "ACS_UPSTREAM_TRUNCATED"
ACS_UPSTREAM_REFUSED          = "ACS_UPSTREAM_REFUSED"
ACS_UPSTREAM_UNKNOWN          = "ACS_UPSTREAM_UNKNOWN"

CODES = (
    ACS_BAD_REQUEST, ACS_VALIDATION_FAILED, ACS_PAYLOAD_TOO_LARGE,
    ACS_UNPROCESSABLE, ACS_NOT_FOUND, ACS_METHOD_NOT_ALLOWED,
    ACS_RATE_LIMITED, ACS_TIMEOUT, ACS_NOT_CONFIGURED, ACS_INTERNAL,
    ACS_UPSTREAM_NOT_CONFIGURED, ACS_UPSTREAM_AUTH, ACS_UPSTREAM_PERMISSION,
    ACS_UPSTREAM_MODEL_REJECTED, ACS_UPSTREAM_BAD_REQUEST,
    ACS_UPSTREAM_RATE_LIMIT, ACS_UPSTREAM_OVERLOADED,
    ACS_UPSTREAM_UNAVAILABLE, ACS_UPSTREAM_TIMEOUT, ACS_UPSTREAM_CONNECTION,
    ACS_UPSTREAM_EMPTY_RESPONSE, ACS_UPSTREAM_INVALID_JSON,
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
    ACS_UPSTREAM_NOT_CONFIGURED: 503,
    ACS_UPSTREAM_AUTH: 502,
    ACS_UPSTREAM_PERMISSION: 502,
    ACS_UPSTREAM_MODEL_REJECTED: 502,
    ACS_UPSTREAM_BAD_REQUEST: 502,
    ACS_UPSTREAM_RATE_LIMIT: 429,
    ACS_UPSTREAM_OVERLOADED: 503,
    ACS_UPSTREAM_UNAVAILABLE: 503,
    ACS_UPSTREAM_TIMEOUT: 504,
    ACS_UPSTREAM_CONNECTION: 502,
    ACS_UPSTREAM_EMPTY_RESPONSE: 502,
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
    ACS_UPSTREAM_NOT_CONFIGURED: "مفتاح المحرّك غير مضبوط على الخادم.",
    ACS_UPSTREAM_AUTH: "رفض مزوّد النموذج بيانات الاعتماد.",
    ACS_UPSTREAM_PERMISSION: "لا صلاحية لدى الخادم لاستخدام هذا النموذج.",
    ACS_UPSTREAM_MODEL_REJECTED: "رفض المزوّد معرّف النموذج المطلوب.",
    ACS_UPSTREAM_BAD_REQUEST: "رفض المزوّد صياغة الطلب.",
    ACS_UPSTREAM_RATE_LIMIT: "بلغ المزوّد حدّ الطلبات. أعِد المحاولة بعد قليل.",
    ACS_UPSTREAM_OVERLOADED: "المزوّد مُحمَّل حالياً. أعِد المحاولة بعد قليل.",
    ACS_UPSTREAM_UNAVAILABLE: "خدمة المزوّد غير متاحة حالياً.",
    ACS_UPSTREAM_TIMEOUT: "انتهت مهلة انتظار رد النموذج.",
    ACS_UPSTREAM_CONNECTION: "تعذّر الاتصال بمزوّد النموذج.",
    ACS_UPSTREAM_EMPTY_RESPONSE: "أعاد النموذج رداً فارغاً.",
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
              403: ACS_UPSTREAM_PERMISSION, 404: ACS_UPSTREAM_MODEL_REJECTED,
              408: ACS_UPSTREAM_TIMEOUT, 413: ACS_UPSTREAM_BAD_REQUEST,
              429: ACS_UPSTREAM_RATE_LIMIT, 500: ACS_UPSTREAM_UNAVAILABLE,
              502: ACS_UPSTREAM_UNAVAILABLE, 503: ACS_UPSTREAM_UNAVAILABLE,
              529: ACS_UPSTREAM_OVERLOADED}


def classify_upstream(exc, attempts=None):
    """استثناء من مسار النموذج → AcsApiError مصنّف. لا يرمي أبداً."""
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
    return AcsApiError(code, MESSAGE_AR[code],
                       upstream={"provider": "anthropic", "kind": name,
                                 "status": status, "attempts": attempts})
