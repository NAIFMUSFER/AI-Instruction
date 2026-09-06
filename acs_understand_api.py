# -*- coding: utf-8 -*-
# =============================================================================
# acs_understand_api.py  --  خدمة محرّك الفهم (FastAPI)
# يستقبل وصفاً نصّياً (أو PDF) ويعيد Building JSON عبر Claude، ليعرضه موقع العميل.
#
#   pip install fastapi uvicorn anthropic pypdf python-multipart
#   export ANTHROPIC_API_KEY=sk-ant-...
#   export ACS_LLM_MODEL=claude-sonnet-5     # راجع docs.claude.com لأحدث معرّف
#   uvicorn acs_understand_api:app --host 0.0.0.0 --port 8000
#
# نقاط النهاية:
#   POST /v1/understand        {text, model?}            -> {building}
#   POST /v1/understand/pdf    (ملف PDF multipart)        -> {building}
#   GET  /health
# =============================================================================

import os
import json
import time
import asyncio
import threading
import concurrent.futures
from collections import defaultdict, deque
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

import acs_understand as U
import acs_api_errors as E
import acs_logging as LOGGING
import acs_build_info as BUILD
import acs_rate_limit as RL
import acs_upload_security as UPLOAD
import acs_engineering_authority as EA
import acs_cpu_pool as CPU
import acs_generation_job as JOBS
import acs_provider as PROV

LOG = LOGGING.StructuredLogger(service="ACS Understanding Engine",
                               version=BUILD.SERVICE_VERSION)

SERVICE_NAME = "ACS Understanding Engine"
SERVICE_VERSION = "1.3"

app = FastAPI(title="ACS Understanding API", version=SERVICE_VERSION)

# ---------------------------------------------------------------------------
# عقد الرد: كل رد — نجاحاً كان أو فشلاً — كائن JSON واحد صالح. لا traceback،
# ولا صفحة HTML، ولا كائنان مُلصقان. راجع acs_api_errors.py.
# ---------------------------------------------------------------------------
REQUEST_ID_HEADER = "X-Request-ID"


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if rid:
        return rid
    rid = (request.headers.get(REQUEST_ID_HEADER) or "").strip()[:64] or E.new_request_id()
    try:
        request.state.request_id = rid
    except Exception:
        pass
    return rid


def _error_response(request, err: "E.AcsApiError"):
    rid = request_id_of(request)
    body = err.envelope(rid)
    headers = {REQUEST_ID_HEADER: rid}
    if err.retry_after:
        headers["Retry-After"] = str(int(err.retry_after))
    # سجلّ الخادم: الرمز والمعرّف فقط — لا مفاتيح ولا رؤوس تفويض ولا نص الزائر.
    LOG.error("request_failed", request_id=rid, endpoint=request.url.path,
              error_code=err.code, status=err.status,
              upstream_class=(err.upstream or {}).get("kind")
              if isinstance(getattr(err, "upstream", None), dict) else None,
              retry_after=err.retry_after)
    return JSONResponse(status_code=err.status, content=body, headers=headers)


class UploadBodyLimit:
    """Bound the complete upload before Starlette parses or spools any part.

    MAX_UPLOAD remains the aggregate file-byte limit. The envelope also allows
    UTF-8 notes and bounded multipart headers/boundaries; neither is a file.
    Buffering is bounded and ends before parser allocation, so rejection cannot
    leave a partially spooled UploadFile open.
    """
    MAX_UTF8_BYTES_PER_CHARACTER = 4
    MULTIPART_ENVELOPE_BYTES = 64 * 1024
    PATHS = frozenset(("/v1/understand/image", "/v1/understand/pdf"))

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope.get("method") != "POST"
                or scope.get("path") not in self.PATHS):
            return await self.app(scope, receive, send)
        request = Request(scope)
        budget = (MAX_UPLOAD + self.MAX_UTF8_BYTES_PER_CHARACTER * MAX_NOTES
                  + self.MULTIPART_ENVELOPE_BYTES)
        length = request.headers.get("content-length")
        if length is not None:
            try:
                declared = int(length)
                if declared < 0:
                    raise ValueError
            except ValueError:
                response = _error_response(request, E.AcsApiError(E.ACS_BAD_REQUEST))
                return await response(scope, receive, send)
            if declared > budget:
                response = _error_response(request, E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE))
                return await response(scope, receive, send)
        buffered = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(buffered) + len(chunk) > budget:
                response = _error_response(request, E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE))
                return await response(scope, receive, send)
            buffered.extend(chunk)
            if not message.get("more_body", False):
                break
        pending = [{"type": "http.request", "body": bytes(buffered), "more_body": False}]
        buffered.clear()

        async def bounded_receive():
            return pending.pop() if pending else await receive()

        await self.app(scope, bounded_receive, send)


# Inside the envelope and CORS middleware, outside request/form parsing.
app.add_middleware(UploadBodyLimit)


@app.middleware("http")
async def acs_envelope_middleware(request: Request, call_next):
    """يمنح كل طلب معرّفاً، ويضمن أن أي انفلات يخرج مغلّفاً JSON.

    مُسجَّل **قبل** CORS عمداً: Starlette يجعل آخر وسيط مُضاف هو الأخارجي، فيبقى
    CORS محيطاً بهذا — فتحمل ردود الأخطاء ترويسات CORS ويقرأها المتصفّح بدل أن
    يراها فشل شبكة مبهماً. معالج `Exception` وحده يقع خارج CORS، فلا نتّكل عليه.
    """
    rid = request_id_of(request)
    try:
        response = await call_next(request)
    except E.AcsApiError as err:
        return _error_response(request, err)
    except Exception as exc:                       # noqa: BLE001 — لا شيء يخرج غير مغلّف
        # F-18: لا traceback خام في مسار الطلب. الـtraceback يتجاوز التعقيم وقد
        # يحمل جسم طلب المزوّد — أي وصف الزائر — إلى السجلّ.
        LOG.exception("unhandled_request_error", exc,
                      request_id=rid, endpoint=request.url.path,
                      method=request.method)
        return _error_response(request, E.AcsApiError(
            E.ACS_INTERNAL, "%s (%s)" % (E.MESSAGE_AR[E.ACS_INTERNAL],
                                         type(exc).__name__)))
    response.headers[REQUEST_ID_HEADER] = rid
    return response


# يسمح لموقع العميل (static HTML) بالنداء من المتصفح.
# الافتراضي الآمن هو نطاق الواجهة على Netlify — لا "*" — حتى لا ينفتح
# الخادم للجميع إذا نُشر بلا ضبط. اضبط ACS_ALLOWED_ORIGINS لتجاوزه
# (نطاقات مفصولة بفواصل)؛ "*" مسموح صراحةً للتطوير المحلي فقط.
_DEFAULT_ORIGIN = "https://sprightly-selkie-d906c3.netlify.app"
_origins = [o.strip() for o in os.environ.get("ACS_ALLOWED_ORIGINS", _DEFAULT_ORIGIN).split(",") if o.strip()]
if not _origins:
    _origins = [_DEFAULT_ORIGIN]
app.add_middleware(
    CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
)


# ── معالجات الاستثناءات: لا مسار فشل واحد يخرج بغير JSON ────────────────────
@app.exception_handler(E.AcsApiError)
async def _h_acs(request: Request, exc: E.AcsApiError):
    return _error_response(request, exc)


@app.exception_handler(RequestValidationError)
async def _h_validation(request: Request, exc: RequestValidationError):
    # لا نُعيد كائن pydantic الخام: قد يحمل جسم الطلب كاملاً في `input`.
    try:
        fields = ".".join(str(p) for p in (exc.errors()[0].get("loc") or [])[-2:])
    except Exception:
        fields = ""
    return _error_response(request, E.AcsApiError(
        E.ACS_VALIDATION_FAILED,
        "بيانات الطلب لا تطابق العقد المطلوب%s." % (" (%s)" % fields if fields else "")))


# يُسجَّل على صنف Starlette **وعلى** صنف FastAPI معاً: مُوجِّه Starlette يرمي
# صنفه الأعلى عند 404/405، والبحث عن المعالج يصعد في سلسلة الوراثة لا ينزل —
# فمعالجٌ مسجَّل على الصنف الفرعي وحده لا يلتقط 404 إطلاقاً، فتعود صيغة
# {"detail": "..."} الافتراضية بدل المغلّف.
@app.exception_handler(StarletteHTTPException)
@app.exception_handler(HTTPException)
async def _h_http(request: Request, exc):
    status = int(getattr(exc, "status_code", 500) or 500)
    code = {400: E.ACS_BAD_REQUEST, 404: E.ACS_NOT_FOUND, 405: E.ACS_METHOD_NOT_ALLOWED,
            413: E.ACS_PAYLOAD_TOO_LARGE, 422: E.ACS_UNPROCESSABLE,
            429: E.ACS_RATE_LIMITED, 503: E.ACS_NOT_CONFIGURED,
            504: E.ACS_TIMEOUT}.get(status, E.ACS_INTERNAL)
    detail = exc.detail if isinstance(getattr(exc, "detail", None), str) else None
    # نصوص Starlette الجاهزة إنجليزية وعامّة؛ رسالتنا العربية أوضح للمستخدم.
    if detail in ("Not Found", "Method Not Allowed", "Internal Server Error",
                  "Unprocessable Entity", "Bad Request", None, ""):
        detail = None
    err = E.AcsApiError(code, detail or E.MESSAGE_AR.get(code), status=status)
    ra = (getattr(exc, "headers", None) or {}).get("Retry-After")
    if ra:
        err.retry_after = ra
    return _error_response(request, err)


@app.exception_handler(Exception)
async def _h_any(request: Request, exc: Exception):
    return _error_response(request, E.AcsApiError(E.ACS_INTERNAL))

# ---------------------------------------------------------------------------
# حماية الخادم العام: حدّ طلبات لكل IP + حدّ يومي إجمالي + حدّ حجم النص.
# الخادم مفتوح للزوّار، والمفتاح عليه — بلا هذا يمكن استنزاف الرصيد في دقائق.
# ---------------------------------------------------------------------------
def env_int(name, default):
    """قراءة عدد صحيح من البيئة بلا إسقاط الخدمة عند الاستيراد.

    F-19: كان `int(os.environ.get(...))` يرفع ValueError على القيمة الفارغة،
    و`.env.example` نفسه يشحن `ACS_MAX_BUILDING=` و`ACS_MAX_UPLOAD_MB=` فارغَين
    مع تعليمة `cp .env.example .env` — فينكسر استيراد الوحدة كلّها ولا يقلع
    الخادم إطلاقاً. القيمة الفارغة أو غير الرقمية أو غير الموجبة تعود إلى
    الافتراضي المُعلن. نفس المعالجة الموجودة أصلاً في acs_rate_limit.env_int.
    """
    default = int(default)
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


RL_GEN_HOUR  = env_int("ACS_RL_GEN_HOUR", 8)       # توليد/زائر/ساعة
RL_GEN_DAY   = env_int("ACS_RL_GEN_DAY", 25)       # توليد/زائر/يوم
RL_EDIT_HOUR = env_int("ACS_RL_EDIT_HOUR", 30)     # تعديلات/زائر/ساعة
RL_GLOBAL_DAY = env_int("ACS_RL_GLOBAL_DAY", 400)  # سقف يومي للخادم كله
MAX_TEXT = env_int("ACS_MAX_TEXT", 60000)          # حرفاً لكل طلب
MAX_UPLOAD = env_int("ACS_MAX_UPLOAD_MB", 12) * 1024 * 1024
MAX_BUILDING = env_int("ACS_MAX_BUILDING", 900000)   # حجم النموذج في /v1/edit
# F-20: سقف مجموع أحرف الملاحظات في /v1/edit و/v1/understand/image. كان الحقل
# بلا أي حدّ حجم ويُمرَّر إلى المُوجّه بـtruncate=False، فأربعون ملاحظة بعشرة
# ملايين حرف تُقبل وتُنسخ عبر حدّ العملية.
MAX_NOTES = env_int("ACS_MAX_NOTES_CHARS", 20000)
# ACS_ALLOWED_MODELS إن ضُبط يعلو كل شيء. وإلّا تُشتقّ القائمة من المزوّد
# المحلول — فالافتراضي المدفون `claude-sonnet-5,claude-haiku-4-5` كان يرفض كل
# معرّف deepseek، فيقلع الخادم ثم يردّ /ready بـ503 على ضبطٍ صحيح تماماً.
# على المزوّد anthropic (الافتراضي) الناتج مطابقٌ حرفياً لما كان.
ALLOWED_MODELS = PROV.allowed_models()


def _upload_error(exc):
    """يحوّل رفض الرفع إلى مغلّف الخطأ القياسي — 4xx لا 500، وبلا اسم ملفّ خام."""
    code = getattr(exc, "code", "UPLOAD_REJECTED")
    too_big = code in ("IMAGE_TOO_LARGE", "PDF_TOO_LARGE", "JSON_TOO_LARGE",
                       "DXF_TOO_LARGE", "IMAGE_TOO_MANY_PIXELS",
                       "IMAGE_SIDE_TOO_LARGE", "IMAGE_PIXEL_BUDGET_EXCEEDED",
                       "PDF_TOO_MANY_PAGES", "TOO_MANY_FILES")
    api = E.AcsApiError(
        E.ACS_PAYLOAD_TOO_LARGE if too_big else E.ACS_UNPROCESSABLE,
        getattr(exc, "message_ar", None) or "تعذّر قبول الملفّ المرفوع.")
    return api


def _safe_model(m):
    """لا يختار الزائر النموذج — إلا من قائمة مسموحة صراحةً."""
    m = (m or "").strip()
    return m if m in ALLOWED_MODELS else None

# F-04: الحدّ صار في acs_rate_limit — مخزن ذرّي مشترك (Redis) أو ذاكرة محدودة
# المفاتيح. الحدّ داخل العملية وحده كان يتضاعف مع كل عامل ومع كل نسخة، ويتسرّب
# مع كل هوية مزوّرة. التفاصيل والاختبارات في acs_rate_limit.py.
TRUSTED_HOPS = RL.trusted_hops()
_LIMITER = RL.default_limiter()


def _client_ip(request: Request) -> str:
    """هويّة العميل — منطق الرؤوس كلّه في acs_rate_limit.client_identity.

    X-Real-IP لم يعد يُصدَّق افتراضياً: كان يمنح كل طلب دلواً جديداً."""
    try:
        headers = {k.lower(): v for k, v in request.headers.items()}
    except Exception:                                           # pragma: no cover
        headers = {}
    peer = request.client.host if request.client else None
    return RL.client_identity(headers, peer)


def _too_many(msg, wait):
    """429 دائماً بجسد JSON صالح وترويسة Retry-After — الحدود كما هي بلا تخفيف."""
    return E.AcsApiError(E.ACS_RATE_LIMITED, msg, retryable=True,
                         retry_after=max(1, int(wait or 60)))


def guard(request: Request, kind: str = "gen"):
    """يطبّق الحدّ المشترك. الترتيب محفوظ: العام يُفحَص بلا استهلاك، ثم حدّ
    الزائر، ثم يُستهلك العام — وإلا أطفأ زائرٌ مرفوضٌ الخدمة للجميع."""
    ip = _client_ip(request)
    decision = _LIMITER.check(ip, kind)
    if not decision.get("allowed"):
        raise _too_many(decision.get("message")
                        or "تجاوزت الحدّ المسموح. أعِد المحاولة لاحقاً.",
                        decision.get("retry_after"))
    return decision


def _cap(text: str) -> str:
    if len(text) > MAX_TEXT:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "الوصف طويل جداً (%d حرف). الحدّ %d — اختصره أو قسّمه."
                            % (len(text), MAX_TEXT))
    return text


#: سقوف مسح الوزن. المسح نفسه يجب ألّا يصير هجوماً على بنيةٍ متداخلة.
_WEIGH_MAX_NODES = 20000
_WEIGH_MAX_DEPTH = 12


def _string_weight(value, budget, _depth=0, _seen=None):
    """مجموع أطوال **كل** السلاسل داخل قيمة، بمسحٍ محدود يتوقّف عند الميزانية.

    يُحسَب المفتاح والقيمة معاً: كلاهما يصل التوجيه.
    """
    if _seen is None:
        _seen = [0]                                   # عدّاد عُقَد مشترك
    total = 0
    if _depth > _WEIGH_MAX_DEPTH:
        return budget + 1                             # عمق مريب: يُعدّ تجاوزاً
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, (list, tuple)):
        items = ((None, v) for v in value)
    else:
        # كائن pydantic أو ما شابه: تُقرأ حقوله المعلنة إن وُجدت.
        data = getattr(value, "__dict__", None)
        if not isinstance(data, dict):
            return 0
        items = data.items()
    for key, item in items:
        _seen[0] += 1
        if _seen[0] > _WEIGH_MAX_NODES:
            return budget + 1                         # بنية أوسع من أن تُقاس
        if isinstance(key, str):
            total += len(key)
        total += _string_weight(item, budget, _depth + 1, _seen)
        if total > budget:
            return total                              # خروج مبكر: لا مسح زائد
    return total


def _cap_notes(notes) -> None:
    """F-20: سقف على الملاحظات — نصّاً واحداً أو قائمة كائنات.

    كان MAX_NOTES غير موجود أصلاً: الحقل `notes` في /v1/edit يُفحص عدده (٤٠)
    ولا يُفحص حجمه، ثم يُدرَج حرفياً في نصّ التوجيه بـtruncate=False.
    """
    if not notes:
        return
    if isinstance(notes, str):
        total = len(notes)
    else:
        # W1-E: كان العدّ مقصوراً على أربعة مفاتيح — text/layer/floor/room —
        # فأيّ مفتاحٍ آخر لا يُحسب إطلاقاً. مقيس: `[{"kind": "A"*10_000_000}]`
        # يمرّ، و`[{"kind": "A"*5_000_000}] × 40` (٢٠٠ م.ب) يمرّ كذلك، بينما
        # ٣٠ ٠٠٠ حرفاً في `text` تُرفض. والملاحظات تُدرَج في التوجيه
        # بـ`truncate=False`، فالمقياس يجب أن يكون ما يصل التوجيه فعلاً:
        # **كل** سلسلة في الملاحظة، مهما كان مفتاحها وعمقها.
        total = _string_weight(notes, MAX_NOTES)
    if total > MAX_NOTES:
        raise E.AcsApiError(
            E.ACS_PAYLOAD_TOO_LARGE,
            "الملاحظات طويلة جداً (%d حرف). الحدّ %d — اختصرها أو أرسلها على دفعات."
            % (total, MAX_NOTES))


async def _read_capped(upload, budget, seen=0):
    """F-21: يقرأ الملفّ المرفوع على دفعات ويتوقّف فور تجاوز MAX_UPLOAD.

    كان `await file.read()` يُحضر الجسد كلّه إلى الذاكرة قبل أي فحص حجم، وكان
    MAX_UPLOAD مُعلناً في /health وغير مستعمَل في أي مقارنة في المستودع كلّه
    (موضعان فقط: تعريفه وعرضه). جسد ٤ غيغابايت كان يصير مقيماً في الذاكرة قبل
    أن يُستشار حدّ الاثني عشر ميغابايت.
    """
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(262144)
        if not chunk:
            break
        total += len(chunk)
        if total + seen > budget:
            raise E.AcsApiError(
                E.ACS_PAYLOAD_TOO_LARGE,
                "حجم الرفع أكبر من الحدّ المسموح (%d ميغابايت)."
                % (budget // (1024 * 1024)))
        chunks.append(chunk)
    return b"".join(chunks), total


# ---------------------------------------------------------------------------
# مهلة صريحة على كل توليد: العامل المحجوز بلا سقف يبتلع خيطاً ثم تقتله البوّابة،
# فيصل العميل انقطاعٌ بلا جسد رد — لا يمكن تصنيفه ولا عرضه. هنا نردّ 504 بجسد JSON.
# الخيط المتروك يُكمل ثم تُهمَل نتيجته: بايثون لا تقتل خيطاً، ولا ندّعي أننا نفعل.
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_S = float(os.environ.get("ACS_REQUEST_TIMEOUT_S", "840"))
_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=env_int("ACS_WORKER_THREADS", 8),
    thread_name_prefix="acs-gen")
_JOBS = JOBS.default_runner()

# ---------------------------------------------------------------------------
# KI-14/F-46 · مجمّع العمل الحاسوبيّ. مدقّقات الرفع كانت تُستدعى متزامنةً داخل
# `async def`، فتوقف الحلقة كلّها: ٤٤٩ms لصورة واحدة مقبولة، و١٤٩٠ms لدفعة
# **مرفوضة** — أي أن الرفض نفسه كان سلاح حرمانٍ من الخدمة. القياس في
# tests/remediation/test_event_loop.py.
# ---------------------------------------------------------------------------
_CPU = CPU.default_pool()


async def _validate(target, *args):
    """يشغّل مدقّقاً معلناً خارج الحلقة، ويترجم أعطال المجمّع إلى مغلّف الأخطاء.

    الرفض (UploadRejected) يصعد كما هو ليعالجه `_upload_error` بلا تغيير في
    عقد الأخطاء. أما الإشباع والمهلة وموت العامل فأعطال خادم مصنّفة.
    """
    try:
        return await CPU.run(target, args)
    except CPU.PoolSaturated as exc:
        LOG.warn("validation_rejected", detail=str(exc)[:200],
                 in_flight=_CPU.in_flight())
        raise E.AcsApiError(
            E.ACS_RATE_LIMITED,
            "الخادم مشغول بفحص ملفّات أخرى. أعِد المحاولة بعد قليل.",
            retryable=True, retry_after=15)
    except CPU.PoolTimeout:
        LOG.warn("validation_timeout", target=target,
                 timeout_s=_CPU.timeout_s)
        raise E.AcsApiError(
            E.ACS_TIMEOUT,
            "تجاوز فحص الملفّ مهلة الخادم. قلّل حجم الملفّ أو عدد الصفحات.")
    except CPU.WorkerCrashed as exc:
        LOG.warn("validation_worker_crashed", target=target,
                 detail=str(exc)[:120])
        raise E.AcsApiError(
            E.ACS_UPSTREAM_UNKNOWN,
            "تعذّر فحص الملفّ على الخادم. أعِد المحاولة.", retryable=True)


async def run_job(target, kwargs, what="التوليد", seconds=None, request_id=None):
    """F-06: التوليد عملية مستقلّة تُنهى فعلاً عند المهلة.

    كان الخيط المتروك يُكمل نداء المزوّد ويحتجز مقعده حتى ٦٠٠ ثانية أخرى، فيشبع
    المجمّع ويحوّل كل طلب تالٍ إلى 504. الآن يُنهى العامل ويتحرّر المقعد فوراً."""
    limit = float(seconds or REQUEST_TIMEOUT_S)
    loop = asyncio.get_running_loop()
    started = time.time()

    def _event(job):
        LOG.info("generation_job", request_id=job.request_id, job_id=job.id,
                 state=job.state, target=job.target,
                 duration_ms=job.duration_ms(), error_class=job.error_class,
                 # F-34: الرمز المصنَّف في الابنة. بلا هذا كان السجلّ يقول
                 # error_class=AcsApiError ولا يقول أي عطل هو.
                 error_code=job.error_code)

    def _call():
        return _JOBS.run(target, kwargs, timeout_s=limit,
                         request_id=request_id, on_event=_event)

    try:
        return await loop.run_in_executor(_POOL, _call)
    except JOBS.JobRejected as exc:
        LOG.warn("generation_rejected", request_id=request_id,
                 detail=str(exc)[:200], in_flight=_JOBS.in_flight())
        raise E.AcsApiError(
            E.ACS_RATE_LIMITED,
            "الخادم مشغول بالكامل الآن. أعِد المحاولة بعد قليل.",
            retryable=True, retry_after=30)
    except TimeoutError:
        LOG.warn("generation_timeout", request_id=request_id, target=target,
                 duration_ms=int((time.time() - started) * 1000),
                 slot_released=True, available=_JOBS.available())
        raise E.AcsApiError(
            E.ACS_TIMEOUT,
            "تجاوز %s مهلة الخادم (%d ثانية). قصّر الوصف أو قسّمه ثم أعِد المحاولة."
            % (what, int(limit)))
    except JOBS.JobError as exc:
        raise E.classify_upstream(exc, provider=_resolved_provider())


async def run_bounded(fn, what="التوليد", seconds=None):
    """مسار متوافق قديم — محفوظ للاستدعاءات الخارجية. لا يُستعمل في أي مسار
    توليد داخل هذا الملفّ: الخيط المتروك بعد المهلة لا يُلغى، وهذا سبب F-06."""
    limit = float(seconds or REQUEST_TIMEOUT_S)
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(_POOL, fn)
    fut.add_done_callback(lambda ft: ft.cancelled() or ft.exception())
    try:
        return await asyncio.wait_for(asyncio.shield(fut), timeout=limit)
    except asyncio.TimeoutError:
        raise E.AcsApiError(
            E.ACS_TIMEOUT,
            "تجاوز %s مهلة الخادم (%d ثانية). قصّر الوصف أو قسّمه ثم أعِد المحاولة."
            % (what, int(limit)))


def _report(building: dict) -> dict:
    """تقرير التغطية: ماذا طلب العميل وأين نُفِّذ كل بند."""
    meta = building.get("meta", {}) or {}
    return {"requirements": meta.get("requirements") or [],
            "extras": meta.get("extras") or [],
            "added": meta.get("added") or []}


class UnderstandReq(BaseModel):
    # F-24: pydantic v2 يقبل inf/nan افتراضياً (allow_inf_nan=True). كان
    # {"text":"x","site_w":1e400,"site_d":1e400} يمرّ فيصير site_w = inf، ثم
    # يرفع acs_generation.plan_strategy الخطأ OverflowError عند
    # `int(area / AREA_PER_ZONE[kind])` — وهو ليس ضمن `except (TypeError,
    # ValueError)` هناك — فيهرب إلى except العام في العملية الابنة ويظهر
    # للمستخدم 502 «عطل غير مصنّف من مزوّد النموذج». عطلٌ محلّي يُنسب إلى طرف
    # ثالث، ويستهلك مقعد توليد وعملية كاملة بلا أي تكلفة رموز على المهاجم.
    model_config = ConfigDict(allow_inf_nan=False)

    text: str
    model: str | None = None
    btype: str | None = None      # auto | residential | warehouse | office | retail
    strict: bool | None = None    # التزام حرفي بوصف العميل: لا إضافات قياسية
    site_w: float | None = Field(default=None, gt=0, le=100000)
    site_d: float | None = Field(default=None, gt=0, le=100000)
    floors: int | None = Field(default=None, ge=1, le=400)
    deep: bool | None = None      # فرض/تعطيل التوليد على مرحلتين


def _model_configured() -> str:
    """معرّف النموذج الفعليّ بعد حلّ المزوّد — لا الافتراضي المدفون."""
    return (PROV.primary().model or "").strip()


def _api_key_configured() -> bool:
    """وجود المفتاح فقط — قيمته لا تُقرأ ولا تُطبع ولا تُعاد بأي شكل.

    القرار كلّه في acs_provider (الجديد والقديم، ولمن يُقبل كلٌّ منهما).
    """
    return bool(PROV.primary().api_key)


def _resolved_provider() -> str:
    """اسم المزوّد المحلول فعلاً — لا اسمٌ مكتوب حرفياً.

    W1-D: كانت أربعةُ مواضع تنادي `E.classify_upstream(e)` بلا `provider=`،
    فتأخذ الافتراضَ "anthropic". على نشرٍ deepseek — وهو النشر الحيّ — كان كلُّ
    عطلٍ يُرفع من طبقة الواجهة يُنسَب إلى anthropic، بما في ذلك موتُ عمليتنا
    نحن تحت ضغط الذاكرة. وهذا أسوأ من حقلٍ غائب: غيابٌ يُقرأ معلومةً.
    """
    try:
        return PROV.primary().provider or "unknown"
    except Exception:                                             # noqa: BLE001
        return "unknown"


def _key_env_name() -> str:
    """أسماء المتغيّرات المقبولة للمفتاح — أسماءٌ لا قيم. تُشتقّ من عقد المزوّد
    الواحد، فلا يوجد في هذا الملفّ اسمُ متغيّرٍ سرّيّ مكتوبٌ حرفياً."""
    p = PROV.primary()
    names = ["ACS_LLM_API_KEY"]
    legacy = (PROV.PROVIDER_SPEC.get(p.provider or "") or {}).get(
        "legacy_key_env")
    if legacy:
        names.append(legacy)
    return "/".join(names)


@app.get("/")
def root():
    """صفحة حالة بسيطة — حتى لا يظهر Not Found لمن يفتح الجذر."""
    return {"ok": True,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "status": "running",
            "health": "/health",
            "ready": "/ready",
            "error_contract": E.ERROR_CONTRACT_VERSION,
            "endpoints": ["/v1/understand", "/v1/edit",
                          "/v1/understand/image", "/v1/understand/pdf"],
            "docs": "/docs"}


@app.get("/health")
def health():
    """حياة العملية + كفاية الضبط. `key` و`model` مُبقيان لتوافق واجهات قديمة.
    لا يظهر هنا أي سرّ: `api_key_configured` منطقيّ لا قيمة."""
    return {"ok": True,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "error_contract": E.ERROR_CONTRACT_VERSION,
            "model_configured": _model_configured(),
            "api_key_configured": _api_key_configured(),
            "allowed_models": sorted(ALLOWED_MODELS),
            "allowed_origins_count": len(_origins),
            "model": _model_configured(),          # توافق خلفي
            "key": _api_key_configured(),          # توافق خلفي
            "limits": {"gen_hour": RL_GEN_HOUR, "gen_day": RL_GEN_DAY,
                       "edit_hour": RL_EDIT_HOUR, "global_day": RL_GLOBAL_DAY,
                       "max_text": MAX_TEXT,
                       "max_upload_bytes": MAX_UPLOAD,
                       "max_building_chars": MAX_BUILDING,
                       "request_timeout_s": int(REQUEST_TIMEOUT_S)},
            # حالة الأنظمة الفرعية — بلا أي سرّ ولا عنوان مخزن ولا كلمة مرور
            "rate_limit": RL.health_status(),
            "uploads": UPLOAD.health_status(),
            "engineering_changes": EA.health_status(),
            "logging": LOGGING.health_status(),
            "generation_jobs": JOBS.health_status(),
            # حالة مزوّد النموذج — أسماء ومضيف فقط. لا مفتاح، ولا عنوان كامل
            # (قد يحمل اعتماداً مضمَّناً)، ولا رصيد حساب ولا أي حالة فوترة.
            "llm": PROV.health_status(),
            # KI-14/F-46: حالة مجمّع العمل الحاسوبيّ. `isolated=false` يعني
            # أن المنصّة منعت spawn وأننا على خيوط — تدهورٌ مُعلَن لا صامت.
            "cpu_pool": CPU.health_status(),
            "build": {k: v for k, v in BUILD.build_info().items()
                      if k in ("version", "git_sha_short", "built_at",
                               "provenance_verified")}}


@app.get("/version")
def version():
    """أصل البناء — SHA وطابع زمني ونسخ المخطّطات. لا سرّ ولا مسار ملفّ.

    بلا هذا لا يستطيع تحقّقٌ إنتاجيّ أن يقول أيّ نسخة قاسها."""
    info = BUILD.build_info()
    return {"service": info["service"],
            "version": info["version"],
            "git_sha": info["git_sha"],
            "git_sha_short": info["git_sha_short"],
            "git_branch": info["git_branch"],
            "built_at": info["built_at"],
            "provenance_verified": info["provenance_verified"],
            "schema_versions": dict(info["schema_versions"],
                                    error_contract=E.ERROR_CONTRACT_VERSION,
                                    engineering_changes=EA.SCHEMA)}


@app.get("/ready")
def ready():
    """جاهزية التوليد فعلاً: مفتاح مضبوط + نموذج ضمن المسموح + المكتبة مُثبَّتة.
    الحياة (/health) شيء والجاهزية شيء آخر — الخلط بينهما يخفي خادماً حيّاً عاجزاً."""
    missing = []
    if not _api_key_configured():
        missing.append(_key_env_name())           # الاسم فقط، بلا قيمة
    model = _model_configured()
    if not model:
        missing.append("ACS_LLM_MODEL")
    elif model not in ALLOWED_MODELS:
        missing.append("ACS_ALLOWED_MODELS")
    _p = PROV.primary()
    if _p.state == PROV.UNKNOWN_PROVIDER:
        missing.append("ACS_LLM_PROVIDER")
    elif _p.state == PROV.MISSING_BASE_URL:
        missing.append("ACS_LLM_BASE_URL")
    try:
        import anthropic                          # noqa: F401
        sdk = True
    except Exception:
        sdk = False
        missing.append("anthropic")
    if missing:
        raise E.AcsApiError(
            E.ACS_NOT_CONFIGURED,
            "الخادم حيّ لكنه غير جاهز للتوليد. ناقص: %s" % ", ".join(missing))
    return {"ok": True, "ready": True, "service": SERVICE_NAME,
            "version": SERVICE_VERSION, "model_configured": model,
            "api_key_configured": True, "sdk": sdk}


def _generation_summary(meta):
    """ملخّص آمن للواجهة: تصنيف وأرقام مجمّعة — لا نصّ زائر ولا محتوى رد."""
    g = meta.get("acs_generation") or {}
    if not g:
        return None
    st = g.get("stages") or []
    return {"strategy": g.get("strategy"), "size_class": g.get("size_class"),
            "estimated_output_tokens": g.get("estimated_output_tokens"),
            "max_output_tokens": g.get("max_output_tokens"),
            "escalations": g.get("escalations", 0),
            "stages": len(st),
            "stop_reasons": sorted({s.get("stop_reason") for s in st
                                    if s.get("stop_reason")}),
            "output_tokens_total": sum(s.get("output_tokens") or 0 for s in st),
            "input_tokens_total": sum(s.get("input_tokens") or 0 for s in st),
            "stage_detail": [{"stage": s.get("stage"), "depth": s.get("depth"),
                              "stop_reason": s.get("stop_reason"),
                              "output_tokens": s.get("output_tokens"),
                              "input_tokens": s.get("input_tokens"),
                              "max_output_tokens": s.get("max_output_tokens"),
                              "parsed": s.get("parsed"),
                              "error": s.get("error")} for s in st[:12]]}


async def _engineering_authority(building):
    """F-01 — سلطة التغيير الهندسي.

    كان النظام يُصلح النموذج حسابياً بعد التوليد بلا إفصاح: يُزيح الغرف، ويقلّصها،
    ويضيف أبواباً وكواشف دخان ومرشّات وأفياشاً. صار ذلك كلّه اقتراحات تُعرَض ولا
    تُطبَّق. النموذج المُعاد هنا هو مخرج التوليد نفسه، ولا يوجد مسار إيداع تلقائي.

    الاقتراحات تُعاد في الرد لا داخل النموذج، حتى لا يغيّر الإفصاحُ بصمةَ النموذج."""
    try:
        # KI-14/F-46: كان هذا النداء يعمل على الحلقة في كل رد ناجح. قياساً:
        # ٢٫٨ms عند ٢٠ غرفة · ٣٩٨ms عند ١٦٠٠ · ٥٧١٤ms عند ٨٤٠٠ — والأخير
        # نموذجٌ تحت سقف ACS_MAX_BUILDING. أي خمس ثوانٍ من الشلل على **نجاح**.
        # W1-B: يعود النموذج المُطبَّع مع الخطّة. كان `ea_plan` يطبّق
        # SAFE_NORMALIZATION داخل العامل على نسخته المُسلسَلة وحدها، فيعلن الردّ
        # تطبيعاتٍ لا يحويها النموذج المُعاد، وتصف البصماتُ كائنَ العامل لا
        # الكائنَ المُعاد. مقيس: floor_height تعود None إلى العميل بينما الردّ
        # يعلنها 3.2 — وهي بالضبط عائلة KI-25 (baseY = index × floor_height).
        out = await _validate("ea_plan_model", building)
        plan = out["plan"]
        normalised = out["building"]
    except Exception as exc:                                    # noqa: BLE001
        LOG.exception("engineering_plan_failed", exc)
        return {"available": False, "applied": False, "auto_commit_path": False,
                "proposals": [], "proposal_count": 0,
                "detail": "NOT EVALUATED — the proposal planner did not run"}, None
    return {"available": True,
            "applied": False,
            "auto_commit_path": False,
            "engineering_authority": False,
            "requires_user_confirmation": bool(plan["proposals"]),
            "proposal_count": len(plan["proposals"]),
            "model_hash_before": plan["model_hash_before"],
            "model_hash_after": plan["model_hash_after"],
            "model_unchanged": plan["unchanged"],
            "safe_normalisations": plan["safe_changes"],
            "proposals": plan["proposals"],
            "registry": plan["registry"]}, normalised


async def _edit_diff(before, after):
    """فرق مُسطَّح بين نموذجين — للعرض قبل الاستبدال، لا للإيداع."""
    try:
        # KI-14/F-46: الفرق المسطَّح يمرّ على النموذجين كاملين — خارج الحلقة.
        return await _validate("ea_flat_diff", before, after)
    except Exception as exc:                                    # noqa: BLE001
        LOG.exception("edit_diff_failed", exc)
        return {"available": False,
                "detail": "NOT EVALUATED — the diff could not be computed"}


async def _understand_payload(building):
    # A generated repair travels as review data, outside the canonical model
    # before authority hashes or validation are calculated.
    repair = (building.get("meta") or {}).get("acs_repair_proposal")
    if isinstance(repair, dict):
        building = dict(building)
        building["meta"] = dict(building.get("meta") or {})
        building["meta"].pop("acs_repair_proposal", None)
    # W1-B: التطبيع أوّلاً، ثم العدّ والردّ — على النموذج نفسه الذي سيخرج.
    # كان العدّ يسبق `_engineering_authority`، فحتى لو عاد نموذجٌ مُطبَّع لكانت
    # الأعداد والبصمات تصف كائناً آخر. إن لم يعمل المخطّط (`None`) يبقى
    # النموذج كما وصل — لا يُخترَع تطبيع ولا يُدَّعى.
    authority, normalised = await _engineering_authority(building)
    if isinstance(normalised, dict) and normalised.get("floors") is not None:
        building = normalised
    # Validate the model actually returned, after normalisation. A stored
    # generation count is historical metadata, not a result for this model.
    issues, validation_stats = await _validate("validate_building", building)
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    meta = building.get("meta", {})
    payload = {"ok": True, "building": building, "levels": len(building["levels"]),
            "rooms": nr, "type": meta.get("type"),
            "mode": meta.get("acs_mode", "single"),
            "generation": _generation_summary(meta),
            "engineering_authority": authority,
            "engineering_proposals": authority.get("proposals") or [],
            "compliance": {"status": "NOT_EVALUATED",
                           "note": "لا حزمة أنظمة موثّقة محمّلة — هذا تحقّق نموذج "
                                   "هندسي وليس مطابقة أنظمة."},
            "issues": len(issues),
            "model_validation": {"status": "COMPLETED", "scope": "acs_validate",
                                 "issues": issues, "stats": validation_stats},
            "report": _report(building)}
    if isinstance(repair, dict) and isinstance(repair.get("building"), dict):
        payload["report"]["repair_proposal"] = {
            "building": repair["building"], "applied": False,
            "requires_confirmation": True,
            "issues_before": issues, "issues_after": repair.get("issues_after") or [],
            "engineering_diff": await _edit_diff(building, repair["building"])}
    return payload


@app.post("/v1/understand")
async def understand(req: UnderstandReq, request: Request):
    if not req.text.strip():
        raise E.AcsApiError(E.ACS_BAD_REQUEST, "النص فارغ.")
    _cap(req.text)
    guard(request, "gen")
    rid = request_id_of(request)
    text = req.text
    hints = []
    if req.site_w and req.site_d:
        hints.append("أبعاد الأرض/مسطح البناء: العرض %.1f م (محور X) × العمق %.1f م (محور Z)."
                     % (float(req.site_w), float(req.site_d)))
    if req.floors:
        hints.append("عدد الأدوار: %d." % int(req.floors))
    if hints:
        text = "[معطيات الموقع من العميل] " + " ".join(hints) + "\n" + text
    bt = req.btype if (req.btype and req.btype != "auto") else None

    # أبعاد الأرض وعدد الأدوار تصل إلى مقدّر حجم المخرج: القرار «مرحلة واحدة
    # أم مراحل» يحتاجها، وبدونها يُقدَّر مبنى ٩٦٠٠ م² كأنه غرفة.
    _kwargs = dict(description=text, model=_safe_model(req.model), deep=req.deep,
                   strict=bool(req.strict), btype=bt,
                   site_w=req.site_w, site_d=req.site_d, floors=req.floors)
    try:
        building = await run_job("acs_understand:understand", _kwargs,
                                 "الفهم والتوليد", request_id=rid)
    except E.AcsApiError:
        raise                                     # مصنّف سلفاً — لا تُعِد تغليفه
    except Exception as e:
        LOG.exception("generation_failed", e, request_id=rid,
                      endpoint="/v1/understand")
        raise E.classify_upstream(e, provider=_resolved_provider())
    return await _understand_payload(building)


class EditReq(BaseModel):
    building: dict
    notes: list[dict]
    model: str | None = None


@app.post("/v1/edit")
async def edit(req: EditReq, request: Request):
    """ينفّذ ملاحظات المهندس على النموذج ويعيد الفرق قبل أي استبدال.

    F-01: هذا المسار يستبدل النموذج كاملاً بمخرج نموذج لغوي. صار الرد يحمل
    engineering_diff و requires_confirmation، فلا يستبدل العميل نموذجه بلا عرض
    ما تغيّر. الخادم لا يودع شيئاً — لا يملك مشروعاً أصلاً."""
    if not req.notes:
        raise E.AcsApiError(E.ACS_BAD_REQUEST, "لا توجد ملاحظات.")
    guard(request, "edit")
    rid = request_id_of(request)
    LOG.info("edit_requested", request_id=rid, endpoint="/v1/edit",
             notes=len(req.notes))
    # F-19: النموذج الوارد JSON غير موثوق — الحجم والعمق وعدد المفاتيح ومفاتيح
    # تلويث النموذج الأولي تُفحَص قبل أي معالجة.
    # KI-14/F-46: التسلسل والتحقّق كلاهما حاسوبيّ ويكبر مع النموذج (٩٠٠ ك.ب
    # مسموحة، عمق ٤٠، مئة ألف مفتاح). قياسه اليوم ~١٠ms، وهو دون العتبة —
    # لكنّه يكبر مع المدخل، والمبدأ واحد: لا تحليل مدخلٍ غير موثوق على الحلقة.
    try:
        await _validate("validate_json_bytes",
                        json.dumps(req.building, ensure_ascii=False)
                        .encode("utf-8"))
    except UPLOAD.UploadRejected as exc:
        LOG.warn("upload_rejected", request_id=rid, endpoint="/v1/edit",
                 error_code=exc.code, detail=getattr(exc, "detail", None))
        raise _upload_error(exc)
    if len(json.dumps(req.building, ensure_ascii=False)) > MAX_BUILDING:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "النموذج كبير جداً للتعديل — قلّل التفاصيل أو عدّل دوراً واحداً.")
    if len(req.notes) > 40:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "عدد الملاحظات كبير (%d) — أرسلها على دفعات." % len(req.notes))
    # F-20: العدد وحده لا يكفي — الحجم كان بلا أي حدّ، والنصّ يُمرَّر إلى
    # المُوجّه بـtruncate=False فلا يقصّه MAX_DESC_CHARS أيضاً.
    _cap_notes(req.notes)
    try:
        out = await run_job("acs_understand:apply_notes",
                            dict(building=req.building, notes=req.notes,
                                 model=_safe_model(req.model)),
                            "تنفيذ التعديلات", request_id=rid)
    except E.AcsApiError:
        raise
    except Exception as e:
        LOG.exception("edit_failed", e, request_id=rid, endpoint="/v1/edit")
        raise E.classify_upstream(e, provider=_resolved_provider())
    payload = await _understand_payload(out)
    payload["engineering_diff"] = await _edit_diff(req.building, out)
    payload["requires_confirmation"] = True
    payload["change_id"] = "EDIT_MODEL_REPLACEMENT"
    payload["confirmation_note"] = (
        "هذا الرد اقتراح استبدال للنموذج كاملاً. اعرض الفرق على المستخدم قبل "
        "اعتماده — الخادم لا يودع ولا يملك سلطة هندسية.")
    return payload


@app.post("/v1/understand/image")
async def understand_image(
    request: Request,
    files: list[UploadFile] = File(...),
    site_w: float | None = Form(None, gt=0, le=100000, allow_inf_nan=False),
    site_d: float | None = Form(None, gt=0, le=100000, allow_inf_nan=False),
    floors: int | None = Form(None, ge=1, le=400),
    notes: str = Form(""),
    btype: str | None = Form(None),
    strict: str | None = Form(None),
    model: str | None = Form(None),
):
    """يقرأ مخططاً معمارياً مرسوماً (صورة/صور) بالرؤية ويبني النموذج."""
    import base64, traceback
    guard(request, "gen")
    # F-05: لا ثقة باسم الملفّ ولا بـContent-Type. البايتات تُشمّ وتُفكّ فعلاً
    # وتُعاد ترميزاً بلا بيانات وصفية قبل أن تغادر الخادم. لا إعادة وسم صامتة.
    rid = request_id_of(request)
    _cap_notes(notes)
    raw = []
    seen = 0
    for f in files:
        data, size = await _read_capped(f, MAX_UPLOAD, seen)
        seen += size
        raw.append((data, f.content_type))
    try:
        checked = await _validate("validate_images", raw)
    except UPLOAD.UploadRejected as exc:
        LOG.warn("upload_rejected", request_id=rid, endpoint="/v1/understand/image",
                 error_code=exc.code, detail=getattr(exc, "detail", None),
                 files=len(raw))
        raise _upload_error(exc)
    imgs = [(c["media_type"],
             base64.standard_b64encode(c["normalized"]).decode("ascii"))
            for c in checked]
    if not imgs:
        raise E.AcsApiError(E.ACS_BAD_REQUEST, "لم تُرفع صور.")
    LOG.info("upload_accepted", request_id=rid, endpoint="/v1/understand/image",
             files=len(imgs),
             pixels=sum(c["width"] * c["height"] for c in checked))
    bt = btype if (btype and btype != "auto") else None
    _strict = str(strict) in ("1", "true", "True")
    try:
        building = await run_job("acs_understand:understand_images",
                                 dict(images=imgs, site_w=site_w, site_d=site_d,
                                      floors=floors, model=_safe_model(model),
                                      notes=notes, strict=_strict, btype=bt),
                                 "قراءة المخطط", request_id=rid)
    except E.AcsApiError:
        raise
    except Exception as e:
        LOG.exception("vision_generation_failed", e, request_id=rid,
                      endpoint="/v1/understand/image")
        raise E.classify_upstream(e, provider=_resolved_provider())
    return await _understand_payload(building)


@app.post("/v1/understand/pdf")
async def understand_pdf(request: Request, file: UploadFile = File(...),
                         btype: str | None = Form(None),
                         model: str | None = Form(None)):
    guard(request, "gen")
    rid = request_id_of(request)
    # F-21: القراءة محدودة بـMAX_UPLOAD قبل أن يصير الجسد مقيماً في الذاكرة.
    data, _ = await _read_capped(file, MAX_UPLOAD)
    # F-05: لا ملفّ مؤقّت، ولا اسم ملفّ في السجلّ، ولا توقيع مفترض. التحقّق يقرأ
    # البايتات في الذاكرة، ويرفض التوقيع الخاطئ والمشفّر والمقطوع وعدد الصفحات
    # قبل استخراج أي نصّ — فلا يصير خطأ العميل خطأ 500 من المحلّل.
    try:
        checked = await _validate("validate_pdf", data)
    except UPLOAD.UploadRejected as exc:
        LOG.warn("upload_rejected", request_id=rid, endpoint="/v1/understand/pdf",
                 error_code=exc.code, detail=getattr(exc, "detail", None),
                 filename_label=UPLOAD.safe_filename_label(file.filename))
        raise _upload_error(exc)
    text = checked["text"]
    LOG.info("upload_accepted", request_id=rid, endpoint="/v1/understand/pdf",
             filename_label=UPLOAD.safe_filename_label(file.filename),
             pages=checked["pages"], chars=len(text),
             truncated=bool(checked.get("truncated")))
    try:
        if len(text.strip()) < 50:
            raise E.AcsApiError(
                E.ACS_UNPROCESSABLE,
                "PDF بلا نص — يبدو مخططاً مرسوماً/مصوّراً. أرسله كصورة إلى "
                "/v1/understand/image ليُقرأ بالرؤية (الموقع يفعل ذلك تلقائياً).")
        text = _cap(text)
        building = await run_job(
            "acs_understand:understand",
            dict(description=text, model=_safe_model(model),
                 btype=(btype if (btype and btype != "auto") else None)),
            "فهم PDF", request_id=rid)
    except E.AcsApiError:
        raise
    except Exception as e:
        LOG.exception("pdf_generation_failed", e, request_id=rid,
                      endpoint="/v1/understand/pdf")
        raise E.classify_upstream(e, provider=_resolved_provider())
    payload = await _understand_payload(building)
    payload["chars"] = len(text)
    payload["pdf_pages"] = checked["pages"]
    return payload


# ---------------------------------------------------------------------------
# §14 تحقّق الإقلاع: يُعلن كفاية الضبط **بأسماء المتغيّرات وحدها**. لا تُطبع قيمة
# سرّ ولا جزء منها ولا طولها. خادم ناقص الضبط يقلع ويردّ 503 مصنّفاً من /ready —
# أوضح من خادم يقلع صامتاً ثم يفشل عند أول توليد بعد دقيقة انتظار.
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup_env_check():
    ok, missing = [], []
    (ok if _api_key_configured() else missing).append(_key_env_name())
    model = _model_configured()
    (ok if model else missing).append("ACS_LLM_MODEL")
    if model and model not in ALLOWED_MODELS:
        missing.append("ACS_ALLOWED_MODELS")
    (ok if _origins else missing).append("ACS_ALLOWED_ORIGINS")
    _p, _f = PROV.primary(), PROV.fallback()
    if _p.state == PROV.UNKNOWN_PROVIDER:
        missing.append("ACS_LLM_PROVIDER")
    elif _p.state == PROV.MISSING_BASE_URL:
        missing.append("ACS_LLM_BASE_URL")
    print("[ACS-BOOT] %s v%s · error-contract=%s" %
          (SERVICE_NAME, SERVICE_VERSION, E.ERROR_CONTRACT_VERSION))
    print("[ACS-BOOT] port=%s host=0.0.0.0 timeout=%ds origins=%d models=%d"
          % (os.environ.get("PORT", "8000"), int(REQUEST_TIMEOUT_S),
             len(_origins), len(ALLOWED_MODELS)))
    print("[ACS-BOOT] configured: %s" % (", ".join(sorted(ok)) or "—"))
    # المزوّد يُعلَن عند الإقلاع باسمه ومضيفه: نشرٌ يظنّ نفسه على deepseek بينما
    # يُنادي api.anthropic.com عطلٌ صامتٌ تماماً في السجلّ بلا هذا السطر.
    print("[ACS-BOOT] llm provider=%s model=%s host=%s transport=%s state=%s"
          % (_p.provider, _p.model, _p.base_host or "sdk-default",
             _p.transport, _p.state))
    print("[ACS-BOOT] llm fallback=%s%s (on_billing=%s)"
          % (_f.provider or "none",
             (" model=%s host=%s" % (_f.model, _f.base_host or "sdk-default"))
             if _f.ok else " [%s]" % _f.state,
             PROV.fallback_on_billing()))
    if missing:
        print("[ACS-BOOT] MISSING (names only): %s" % ", ".join(sorted(set(missing))))
        print("[ACS-BOOT] الخدمة حيّة لكن /ready سيردّ 503 حتى يكتمل الضبط.")
    # F-47: قرار حدّ المعدّل يُتَّخذ عند الإقلاع لا يُؤجَّل إلى تحذير في /health.
    # ضبطٌ إنتاجيّ بحدٍّ محليّ العملية وبلا إقرار صريح — أو بإقرارٍ تنقضه
    # المنصّة بإعلانها تزامناً أكبر من واحد — لا يجوز الإقلاع عليه: السقف
    # اليوميّ العامّ يصير قابلاً للمضاعفة بعدد النسخ بلا أن يعلم أحد.
    inv = RL.production_invariant()
    print("[ACS-BOOT] rate-limit invariant: %s (distributed=%s, concurrency=%s)"
          % (inv["state"], inv["distributed"], inv["declared_concurrency"]))
    if not inv["ok"]:
        print("[ACS-BOOT] REFUSING TO START — %s" % inv["detail"])
        raise RL.ProductionInvariantError("%s: %s" % (inv["state"], inv["detail"]))
    # F-46: العمّال يُوقظون قبل أوّل طلب حقيقيّ، فلا يدفع أوّل مستخدمٍ ثمن spawn.
    _cpu = _CPU.warmup()
    print("[ACS-BOOT] cpu pool: executor=%s isolated=%s workers=%d queue=%d"
          % (_cpu["executor"], _cpu["isolated"], _cpu["workers"], _cpu["queue"]))
