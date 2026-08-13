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
from pydantic import BaseModel

import acs_understand as U
import acs_api_errors as E

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
    print("[ACS-ERR] %s %s -> %s (%d)" % (rid, request.url.path, err.code, err.status))
    return JSONResponse(status_code=err.status, content=body, headers=headers)


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
        import traceback
        print("\n===== ACS UNHANDLED (%s) =====" % rid)
        traceback.print_exc()
        print("==============================\n")
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
RL_GEN_HOUR  = int(os.environ.get("ACS_RL_GEN_HOUR", "8"))     # توليد/زائر/ساعة
RL_GEN_DAY   = int(os.environ.get("ACS_RL_GEN_DAY", "25"))     # توليد/زائر/يوم
RL_EDIT_HOUR = int(os.environ.get("ACS_RL_EDIT_HOUR", "30"))   # تعديلات/زائر/ساعة
RL_GLOBAL_DAY = int(os.environ.get("ACS_RL_GLOBAL_DAY", "400"))  # سقف يومي للخادم كله
MAX_TEXT = int(os.environ.get("ACS_MAX_TEXT", "60000"))        # حرفاً لكل طلب
MAX_UPLOAD = int(os.environ.get("ACS_MAX_UPLOAD_MB", "12")) * 1024 * 1024
MAX_BUILDING = int(os.environ.get("ACS_MAX_BUILDING", "900000"))   # حجم النموذج في /v1/edit
ALLOWED_MODELS = {m.strip() for m in os.environ.get(
    "ACS_ALLOWED_MODELS", "claude-sonnet-5,claude-haiku-4-5").split(",") if m.strip()}


def _safe_model(m):
    """لا يختار الزائر النموذج — إلا من قائمة مسموحة صراحةً."""
    m = (m or "").strip()
    return m if m in ALLOWED_MODELS else None

_hits = defaultdict(deque)
_lock = threading.Lock()


TRUSTED_HOPS = int(os.environ.get("ACS_TRUSTED_PROXIES", "1"))


def _client_ip(request: Request) -> str:
    """آخر قيمة في X-Forwarded-For هي التي يكتبها البروكسي الموثوق؛
    أوّلها يكتبها العميل ويستطيع تزويرها كل طلب لتجاوز حدّ المعدّل."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        parts = [p.strip() for p in fwd.split(",") if p.strip()]
        if parts:
            return parts[-min(TRUSTED_HOPS, len(parts))]
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "?"


def _rate(key: str, limit: int, window: int, consume: bool = True):
    """نافذة منزلقة داخل العملية. consume=False يفحص بلا تسجيل."""
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            if not q:
                return True, 0
            return False, int(window - (now - q[0])) + 1
        if consume:
            q.append(now)
        # تنظيف دوري لمفاتيح الـIP الفارغة (تسرّب ذاكرة في خادم طويل العمر)
        if len(_hits) > 4000:
            for k in [k for k, v in list(_hits.items()) if not v]:
                _hits.pop(k, None)
        return True, 0


def _too_many(msg, wait):
    """429 دائماً بجسد JSON صالح وترويسة Retry-After — الحدود كما هي بلا تخفيف."""
    return E.AcsApiError(E.ACS_RATE_LIMITED, msg, retryable=True,
                         retry_after=max(1, int(wait or 60)))


def guard(request: Request, kind: str = "gen"):
    ip = _client_ip(request)
    # افحص العام بلا استهلاك أولاً، ثم حدّ الزائر، ولا تُسجّل في العام إلا بعد نجاحهما —
    # وإلا استطاع زائر واحد مرفوض أن يستنفد السقف العام ويُطفئ الخدمة للجميع.
    ok, wait = _rate("ALL:day", RL_GLOBAL_DAY, 86400, consume=False)
    if not ok:
        raise _too_many("بلغ الخادم سقفه اليومي. حاول غداً أو شغّل نسخة خاصة بك.", wait)
    if kind == "gen":
        ok, wait = _rate("h:" + ip, RL_GEN_HOUR, 3600)
        if not ok:
            raise _too_many("تجاوزت %d عمليات توليد في الساعة. أعِد المحاولة بعد %d دقيقة."
                            % (RL_GEN_HOUR, max(1, wait // 60)), wait)
        ok, wait = _rate("d:" + ip, RL_GEN_DAY, 86400)
        if not ok:
            raise _too_many("تجاوزت %d عملية توليد اليوم. أعِد المحاولة غداً."
                            % RL_GEN_DAY, wait)
    else:
        ok, wait = _rate("e:" + ip, RL_EDIT_HOUR, 3600)
        if not ok:
            raise _too_many("تجاوزت حدّ التعديلات في الساعة. أعِد المحاولة بعد %d دقيقة."
                            % max(1, wait // 60), wait)
    _rate("ALL:day", RL_GLOBAL_DAY, 86400)      # يُستهلك العام بعد اجتياز كل الفحوص


def _cap(text: str) -> str:
    if len(text) > MAX_TEXT:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "الوصف طويل جداً (%d حرف). الحدّ %d — اختصره أو قسّمه."
                            % (len(text), MAX_TEXT))
    return text


# ---------------------------------------------------------------------------
# مهلة صريحة على كل توليد: العامل المحجوز بلا سقف يبتلع خيطاً ثم تقتله البوّابة،
# فيصل العميل انقطاعٌ بلا جسد رد — لا يمكن تصنيفه ولا عرضه. هنا نردّ 504 بجسد JSON.
# الخيط المتروك يُكمل ثم تُهمَل نتيجته: بايثون لا تقتل خيطاً، ولا ندّعي أننا نفعل.
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_S = float(os.environ.get("ACS_REQUEST_TIMEOUT_S", "840"))
_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=int(os.environ.get("ACS_WORKER_THREADS", "8")),
    thread_name_prefix="acs-gen")


async def run_bounded(fn, what="التوليد", seconds=None):
    limit = float(seconds or REQUEST_TIMEOUT_S)
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(_POOL, fn)
    # الخيط المتروك بعد المهلة يُكمل عمله (بايثون لا تقتل خيطاً، ولا ندّعي ذلك)؛
    # نستهلك نتيجته حتى لا يُسجَّل "exception was never retrieved" في السجلّ.
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
    text: str
    model: str | None = None
    btype: str | None = None      # auto | residential | warehouse | office | retail
    strict: bool | None = None    # التزام حرفي بوصف العميل: لا إضافات قياسية
    site_w: float | None = None   # أبعاد الأرض من الواجهة (اختيارية)
    site_d: float | None = None
    floors: int | None = None
    deep: bool | None = None      # فرض/تعطيل التوليد على مرحلتين


def _model_configured() -> str:
    return (os.environ.get("ACS_LLM_MODEL", "claude-sonnet-5") or "").strip()


def _api_key_configured() -> bool:
    """وجود المفتاح فقط — قيمته لا تُقرأ ولا تُطبع ولا تُعاد بأي شكل."""
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())


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
                       "max_text": MAX_TEXT,
                       "request_timeout_s": int(REQUEST_TIMEOUT_S)}}


@app.get("/ready")
def ready():
    """جاهزية التوليد فعلاً: مفتاح مضبوط + نموذج ضمن المسموح + المكتبة مُثبَّتة.
    الحياة (/health) شيء والجاهزية شيء آخر — الخلط بينهما يخفي خادماً حيّاً عاجزاً."""
    missing = []
    if not _api_key_configured():
        missing.append("ANTHROPIC_API_KEY")       # الاسم فقط، بلا قيمة
    model = _model_configured()
    if not model:
        missing.append("ACS_LLM_MODEL")
    elif model not in ALLOWED_MODELS:
        missing.append("ACS_ALLOWED_MODELS")
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


def _understand_payload(building):
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    meta = building.get("meta", {})
    return {"ok": True, "building": building, "levels": len(building["levels"]),
            "rooms": nr, "type": meta.get("type"),
            "mode": meta.get("acs_mode", "single"),
            "generation": _generation_summary(meta),
            "issues": meta.get("acs_issues", 0), "report": _report(building)}


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

    def _work():
        # أبعاد الأرض وعدد الأدوار تصل إلى مقدّر حجم المخرج: القرار «مرحلة واحدة
        # أم مراحل» يحتاجها، وبدونها يُقدَّر مبنى ٩٦٠٠ م² كأنه غرفة.
        return U.understand(text, model=_safe_model(req.model), deep=req.deep,
                            strict=bool(req.strict), btype=bt,
                            site_w=req.site_w, site_d=req.site_d, floors=req.floors)

    try:
        building = await run_bounded(_work, "الفهم والتوليد")
    except E.AcsApiError:
        raise                                     # مصنّف سلفاً — لا تُعِد تغليفه
    except Exception as e:
        import traceback
        print("\n===== ACS ERROR (%s) =====" % rid)
        traceback.print_exc()
        print("============================\n")
        raise E.classify_upstream(e)
    return _understand_payload(building)


class EditReq(BaseModel):
    building: dict
    notes: list[dict]
    model: str | None = None


@app.post("/v1/edit")
async def edit(req: EditReq, request: Request):
    """ينفّذ ملاحظات المهندس على النموذج ويعيده بعد التحقّق والإصلاح."""
    import traceback
    if not req.notes:
        raise E.AcsApiError(E.ACS_BAD_REQUEST, "لا توجد ملاحظات.")
    guard(request, "edit")
    rid = request_id_of(request)
    print("[ACS] edit: %d ملاحظة" % len(req.notes))
    if len(json.dumps(req.building, ensure_ascii=False)) > MAX_BUILDING:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "النموذج كبير جداً للتعديل — قلّل التفاصيل أو عدّل دوراً واحداً.")
    if len(req.notes) > 40:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "عدد الملاحظات كبير (%d) — أرسلها على دفعات." % len(req.notes))
    try:
        out = await run_bounded(
            lambda: U.apply_notes(req.building, req.notes, model=_safe_model(req.model)),
            "تنفيذ التعديلات")
    except E.AcsApiError:
        raise
    except Exception as e:
        print("\n===== ACS EDIT ERROR (%s) =====" % rid); traceback.print_exc(); print("=========================\n")
        raise E.classify_upstream(e)
    nr = sum(len(f.get("rooms", [])) for f in out["floors"].values())
    return {"ok": True, "building": out, "levels": len(out["levels"]), "rooms": nr,
            "issues": out.get("meta", {}).get("acs_issues", 0)}


@app.post("/v1/understand/image")
async def understand_image(
    request: Request,
    files: list[UploadFile] = File(...),
    site_w: float | None = Form(None),
    site_d: float | None = Form(None),
    floors: int | None = Form(None),
    notes: str = Form(""),
    btype: str | None = Form(None),
    strict: str | None = Form(None),
    model: str | None = Form(None),
):
    """يقرأ مخططاً معمارياً مرسوماً (صورة/صور) بالرؤية ويبني النموذج."""
    import base64, traceback
    guard(request, "gen")
    imgs = []
    for f in files[:6]:                       # حتى 6 صفحات
        data = await f.read()
        if len(data) > 5 * 1024 * 1024:
            raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                                "حجم الصورة كبير (%.1f م.ب) — صغّرها إلى أقل من 5 م.ب."
                                % (len(data) / 1048576))
        mt = f.content_type or "image/png"
        if mt not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
            mt = "image/png"
        imgs.append((mt, base64.standard_b64encode(data).decode("ascii")))
    if not imgs:
        raise E.AcsApiError(E.ACS_BAD_REQUEST, "لم تُرفع صور.")
    rid = request_id_of(request)
    print("[ACS] plan images: %d" % len(imgs))
    bt = btype if (btype and btype != "auto") else None
    _strict = str(strict) in ("1", "true", "True")
    try:
        building = await run_bounded(
            lambda: U.understand_images(imgs, site_w=site_w, site_d=site_d,
                                        floors=floors, model=_safe_model(model),
                                        notes=notes, strict=_strict, btype=bt),
            "قراءة المخطط")
    except E.AcsApiError:
        raise
    except Exception as e:
        print("\n===== ACS VISION ERROR (%s) =====" % rid); traceback.print_exc(); print("===========================\n")
        raise E.classify_upstream(e)
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    return {"ok": True, "building": building, "levels": len(building["levels"]), "rooms": nr,
            "issues": building.get("meta", {}).get("acs_issues", 0),
            "report": _report(building)}


@app.post("/v1/understand/pdf")
async def understand_pdf(request: Request, file: UploadFile = File(...),
                         btype: str | None = Form(None), model: str | None = None):
    import tempfile, os as _os, traceback
    guard(request, "gen")
    rid = request_id_of(request)
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                            "حجم الملف %.1f م.ب — الحدّ %d م.ب."
                            % (len(data) / 1048576, MAX_UPLOAD // 1048576))
    # ملف مؤقت متوافق مع ويندوز/لينكس (لا تستخدم /tmp مباشرة)
    fd, tmp = tempfile.mkstemp(suffix=".pdf", prefix="acs_")
    try:
        with _os.fdopen(fd, "wb") as f:
            f.write(data)
        text = U.pdf_to_text(tmp)
        print("[ACS] PDF %s -> %d chars" % (file.filename, len(text)))
        if len(text.strip()) < 50:
            raise E.AcsApiError(
                E.ACS_UNPROCESSABLE,
                "PDF بلا نص — يبدو مخططاً مرسوماً/مصوّراً. أرسله كصورة إلى "
                "/v1/understand/image ليُقرأ بالرؤية (الموقع يفعل ذلك تلقائياً).")
        text = _cap(text)
        building = await run_bounded(
            lambda: U.understand(text, model=_safe_model(model),
                                 btype=(btype if (btype and btype != "auto") else None)),
            "فهم PDF")
    except E.AcsApiError:
        raise
    except Exception as e:
        print("\n===== ACS PDF ERROR (%s) =====" % rid); traceback.print_exc(); print("================================\n")
        raise E.classify_upstream(e)
    finally:
        try: _os.remove(tmp)
        except Exception: pass
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    return {"ok": True, "building": building, "levels": len(building["levels"]), "rooms": nr,
            "chars": len(text), "report": _report(building)}


# ---------------------------------------------------------------------------
# §14 تحقّق الإقلاع: يُعلن كفاية الضبط **بأسماء المتغيّرات وحدها**. لا تُطبع قيمة
# سرّ ولا جزء منها ولا طولها. خادم ناقص الضبط يقلع ويردّ 503 مصنّفاً من /ready —
# أوضح من خادم يقلع صامتاً ثم يفشل عند أول توليد بعد دقيقة انتظار.
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup_env_check():
    ok, missing = [], []
    (ok if _api_key_configured() else missing).append("ANTHROPIC_API_KEY")
    model = _model_configured()
    (ok if model else missing).append("ACS_LLM_MODEL")
    if model and model not in ALLOWED_MODELS:
        missing.append("ACS_ALLOWED_MODELS")
    (ok if _origins else missing).append("ACS_ALLOWED_ORIGINS")
    print("[ACS-BOOT] %s v%s · error-contract=%s" %
          (SERVICE_NAME, SERVICE_VERSION, E.ERROR_CONTRACT_VERSION))
    print("[ACS-BOOT] port=%s host=0.0.0.0 timeout=%ds origins=%d models=%d"
          % (os.environ.get("PORT", "8000"), int(REQUEST_TIMEOUT_S),
             len(_origins), len(ALLOWED_MODELS)))
    print("[ACS-BOOT] configured: %s" % (", ".join(sorted(ok)) or "—"))
    if missing:
        print("[ACS-BOOT] MISSING (names only): %s" % ", ".join(sorted(set(missing))))
        print("[ACS-BOOT] الخدمة حيّة لكن /ready سيردّ 503 حتى يكتمل الضبط.")
