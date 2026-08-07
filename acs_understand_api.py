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

_hits = defaultdict(deque)
_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _rate(key: str, limit: int, window: int):
    """نافذة منزلقة بسيطة داخل العملية — تكفي لخادم واحد وتمنع الاستنزاف."""
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False, int(window - (now - q[0])) + 1
        q.append(now)
        return True, 0


def guard(request: Request, kind: str = "gen"):
    ip = _client_ip(request)
    ok, wait = _rate("ALL:day", RL_GLOBAL_DAY, 86400)
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
    deep: bool | None = None      # فرض/تعطيل التوليد على مرحلتين


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
        if req.btype and req.btype != "auto":
            # تلميح صريح لنوع المبنى يغلب الكشف التلقائي
            text = "[نوع المبنى: %s]\n" % req.btype + text
            if req.btype in ("warehouse", "industrial", "factory", "logistics"):
                text = ("[warehouse مستودع racking pallet conveyor picking docks]\n") + text
        building = U.understand(text, model=req.model, deep=req.deep)
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
        out = U.apply_notes(req.building, req.notes, model=req.model)
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
        n2 = notes
        if btype and btype != "auto":
            n2 = ("نوع المبنى: %s. " % btype) + (notes or "")
            if btype in ("warehouse", "industrial", "factory", "logistics"):
                n2 = "warehouse مستودع racking pallet conveyor docks picking. " + n2
        building = U.understand_images(imgs, site_w=site_w, site_d=site_d,
                                       floors=floors, model=model, notes=n2)
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
        if btype and btype != "auto":
            text = "[نوع المبنى: %s]\n" % btype + text
            if btype in ("warehouse", "industrial", "factory", "logistics"):
                text = "[warehouse مستودع racking pallet conveyor picking docks]\n" + text
        building = U.understand(text, model=model)
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
