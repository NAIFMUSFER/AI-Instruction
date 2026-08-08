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
import threading
from collections import defaultdict, deque
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import acs_understand as U

app = FastAPI(title="ACS Understanding API", version="1.2")

# يسمح لموقع العميل (static HTML) بالنداء من المتصفح
_origins = [o.strip() for o in os.environ.get("ACS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"],
)

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


def guard(request: Request, kind: str = "gen"):
    ip = _client_ip(request)
    # افحص العام بلا استهلاك أولاً، ثم حدّ الزائر، ولا تُسجّل في العام إلا بعد نجاحهما —
    # وإلا استطاع زائر واحد مرفوض أن يستنفد السقف العام ويُطفئ الخدمة للجميع.
    ok, _ = _rate("ALL:day", RL_GLOBAL_DAY, 86400, consume=False)
    if not ok:
        raise HTTPException(429, "بلغ الخادم سقفه اليومي. حاول غداً أو شغّل نسخة خاصة بك.")
    if kind == "gen":
        ok, wait = _rate("h:" + ip, RL_GEN_HOUR, 3600)
        if not ok:
            raise HTTPException(429, "تجاوزت %d عمليات توليد في الساعة. أعِد المحاولة بعد %d دقيقة."
                                % (RL_GEN_HOUR, max(1, wait // 60)))
        ok, wait = _rate("d:" + ip, RL_GEN_DAY, 86400)
        if not ok:
            raise HTTPException(429, "تجاوزت %d عملية توليد اليوم. أعِد المحاولة غداً." % RL_GEN_DAY)
    else:
        ok, wait = _rate("e:" + ip, RL_EDIT_HOUR, 3600)
        if not ok:
            raise HTTPException(429, "تجاوزت حدّ التعديلات في الساعة. أعِد المحاولة بعد %d دقيقة."
                                % max(1, wait // 60))
    _rate("ALL:day", RL_GLOBAL_DAY, 86400)      # يُستهلك العام بعد اجتياز كل الفحوص


def _cap(text: str) -> str:
    if len(text) > MAX_TEXT:
        raise HTTPException(413, "الوصف طويل جداً (%d حرف). الحدّ %d — اختصره أو قسّمه."
                            % (len(text), MAX_TEXT))
    return text


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


@app.get("/")
def root():
    """صفحة حالة بسيطة — حتى لا يظهر Not Found لمن يفتح الجذر."""
    return {"service": "ACS Understanding Engine",
            "status": "running",
            "health": "/health",
            "endpoints": ["/v1/understand", "/v1/edit",
                          "/v1/understand/image", "/v1/understand/pdf"],
            "docs": "/docs"}


@app.get("/health")
def health():
    return {"ok": True, "model": os.environ.get("ACS_LLM_MODEL", "claude-sonnet-5"),
            "key": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "limits": {"gen_hour": RL_GEN_HOUR, "gen_day": RL_GEN_DAY,
                       "max_text": MAX_TEXT}}


@app.post("/v1/understand")
def understand(req: UnderstandReq, request: Request):
    if not req.text.strip():
        raise HTTPException(400, "النص فارغ")
    _cap(req.text)
    guard(request, "gen")
    try:
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
        building = U.understand(text, model=_safe_model(req.model), deep=req.deep,
                                strict=bool(req.strict), btype=bt)
    except Exception as e:
        import traceback
        print("\n===== ACS ERROR (full) =====")
        traceback.print_exc()
        print("============================\n")
        raise HTTPException(500, "فشل الفهم: %s" % str(e)[:900])
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    meta = building.get("meta", {})
    return {"building": building, "levels": len(building["levels"]), "rooms": nr,
            "type": meta.get("type"), "mode": meta.get("acs_mode", "single"),
            "issues": meta.get("acs_issues", 0), "report": _report(building)}


class EditReq(BaseModel):
    building: dict
    notes: list[dict]
    model: str | None = None


@app.post("/v1/edit")
def edit(req: EditReq, request: Request):
    """ينفّذ ملاحظات المهندس على النموذج ويعيده بعد التحقّق والإصلاح."""
    import traceback
    if not req.notes:
        raise HTTPException(400, "لا توجد ملاحظات.")
    guard(request, "edit")
    print("[ACS] edit: %d ملاحظة" % len(req.notes))
    try:
        if len(json.dumps(req.building, ensure_ascii=False)) > MAX_BUILDING:
            raise HTTPException(413, "النموذج كبير جداً للتعديل — قلّل التفاصيل أو عدّل دوراً واحداً.")
        if len(req.notes) > 40:
            raise HTTPException(413, "عدد الملاحظات كبير (%d) — أرسلها على دفعات." % len(req.notes))
        out = U.apply_notes(req.building, req.notes, model=_safe_model(req.model))
    except Exception as e:
        print("\n===== ACS EDIT ERROR ====="); traceback.print_exc(); print("=========================\n")
        raise HTTPException(500, "فشل تنفيذ التعديلات: %s" % str(e)[:900])
    nr = sum(len(f.get("rooms", [])) for f in out["floors"].values())
    return {"building": out, "levels": len(out["levels"]), "rooms": nr,
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
            raise HTTPException(400, "حجم الصورة كبير (%.1f م.ب) — صغّرها إلى أقل من 5 م.ب."
                                % (len(data) / 1048576))
        mt = f.content_type or "image/png"
        if mt not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
            mt = "image/png"
        imgs.append((mt, base64.standard_b64encode(data).decode("ascii")))
    if not imgs:
        raise HTTPException(400, "لم تُرفع صور.")
    print("[ACS] plan images: %d" % len(imgs))
    try:
        bt = btype if (btype and btype != "auto") else None
        building = U.understand_images(imgs, site_w=site_w, site_d=site_d,
                                       floors=floors, model=_safe_model(model), notes=notes,
                                       strict=str(strict) in ("1", "true", "True"),
                                       btype=bt)
    except Exception as e:
        print("\n===== ACS VISION ERROR ====="); traceback.print_exc(); print("===========================\n")
        raise HTTPException(500, "فشل قراءة المخطط: %s" % str(e)[:900])
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    return {"building": building, "levels": len(building["levels"]), "rooms": nr,
            "issues": building.get("meta", {}).get("acs_issues", 0),
            "report": _report(building)}


@app.post("/v1/understand/pdf")
async def understand_pdf(request: Request, file: UploadFile = File(...),
                         btype: str | None = Form(None), model: str | None = None):
    import tempfile, os as _os, traceback
    guard(request, "gen")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "حجم الملف %.1f م.ب — الحدّ %d م.ب."
                            % (len(data) / 1048576, MAX_UPLOAD // 1048576))
    # ملف مؤقت متوافق مع ويندوز/لينكس (لا تستخدم /tmp مباشرة)
    fd, tmp = tempfile.mkstemp(suffix=".pdf", prefix="acs_")
    try:
        with _os.fdopen(fd, "wb") as f:
            f.write(data)
        text = U.pdf_to_text(tmp)
        print("[ACS] PDF %s -> %d chars" % (file.filename, len(text)))
        if len(text.strip()) < 50:
            raise HTTPException(
                422, "PDF بلا نص — يبدو مخططاً مرسوماً/مصوّراً. أرسله كصورة إلى "
                     "/v1/understand/image ليُقرأ بالرؤية (الموقع يفعل ذلك تلقائياً).")
        text = _cap(text)
        building = U.understand(text, model=_safe_model(model),
                                btype=(btype if (btype and btype != "auto") else None))
    except HTTPException:
        raise
    except Exception as e:
        print("\n===== ACS PDF ERROR (full) ====="); traceback.print_exc(); print("================================\n")
        raise HTTPException(500, "فشل قراءة/فهم PDF: %s" % str(e)[:900])
    finally:
        try: _os.remove(tmp)
        except Exception: pass
    nr = sum(len(f.get("rooms", [])) for f in building["floors"].values())
    return {"building": building, "levels": len(building["levels"]), "rooms": nr,
            "chars": len(text), "report": _report(building)}
