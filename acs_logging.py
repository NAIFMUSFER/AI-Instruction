# -*- coding: utf-8 -*-
# =============================================================================
# acs_logging.py — سجلّ إنتاج منظَّم (F-18).
#
# كان مسار الطلب يطبع traceback خاماً. الـtraceback يتجاوز كل تعقيم: استثناء من
# مكتبة المزوّد قد يحمل جسم الطلب — أي وصف الزائر كاملاً — إلى سجلّ الخادم.
#
# العقد هنا:
#   • سطر واحد JSON لكل حدث، بحقول معلنة.
#   • قائمة حجب صريحة: المفتاح، التفويض، وصف المستخدم، محتوى الصورة/الـPDF،
#     ونموذج المبنى كاملاً — لا شيء من ذلك يدخل السجلّ افتراضياً.
#   • الـtraceback في التطوير فقط. في الإنتاج يُسجَّل صنف الاستثناء وموضعه
#     (الملف والسطر) لا نصّه.
#   • رد المستخدم يبقى JSON معقَّماً في الحالتين.
# =============================================================================
import json
import os
import sys
import time
import traceback as _tb

try:
    import acs_api_errors as _E
except Exception:                                               # pragma: no cover
    _E = None

LEVELS = ("debug", "info", "warn", "error")
_LEVEL_RANK = {name: i for i, name in enumerate(LEVELS)}


def _env(name, default=""):
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _env_bool(name, default=False):
    v = _env(name, "").lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


ENV = _env("ACS_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"
MIN_LEVEL = _env("ACS_LOG_LEVEL", "info").lower()
if MIN_LEVEL not in _LEVEL_RANK:
    MIN_LEVEL = "info"
# الـtraceback الكامل: تطوير فقط ما لم يُطلَب صراحة
STACK_TRACES = _env_bool("ACS_LOG_STACK_TRACES", not IS_PRODUCTION)

# حقول لا تُسجَّل أبداً — الحجب بالاسم قبل أي تسلسل
FORBIDDEN_FIELDS = frozenset((
    "api_key", "apikey", "anthropic_api_key", "authorization", "auth",
    "token", "secret", "password", "cookie", "set-cookie",
    "text", "description", "prompt", "notes", "user_text", "body",
    "building", "model_json", "image", "image_bytes", "pdf", "pdf_bytes",
    "content", "completion", "response_text", "raw",
))

MAX_VALUE_CHARS = 300


def _redact(value):
    if _E is not None and isinstance(value, str):
        try:
            value = _E.redact(value)
        except Exception:                                       # pragma: no cover
            pass
    return value


def _safe_value(v):
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        s = _redact(v)
        return s if len(s) <= MAX_VALUE_CHARS else s[:MAX_VALUE_CHARS] + "…"
    if isinstance(v, (list, tuple)):
        return [_safe_value(x) for x in list(v)[:20]]
    if isinstance(v, dict):
        return {str(k): _safe_value(x) for k, x in list(v.items())[:20]
                if str(k).lower() not in FORBIDDEN_FIELDS}
    return _safe_value(str(v))


class StructuredLogger(object):
    """سجلّ JSON بسطر واحد لكل حدث. لا حالة عالمية غير قابلة للحقن."""

    def __init__(self, stream=None, service="ACS Understanding Engine",
                 version=None, min_level=None):
        self._stream = stream or sys.stdout
        self.service = service
        self.version = version
        self.min_level = (min_level or MIN_LEVEL).lower()

    # -------------------------------------------------------------- كتابة --
    def _emit(self, level, event, **fields):
        if _LEVEL_RANK.get(level, 1) < _LEVEL_RANK.get(self.min_level, 1):
            return None
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "level": level, "event": str(event)[:120],
               "service": self.service}
        if self.version:
            rec["version"] = self.version
        for k, v in fields.items():
            key = str(k).lower()
            if key in FORBIDDEN_FIELDS:
                continue
            if v is None:
                continue
            rec[key] = _safe_value(v)
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True, default=str)
        try:
            self._stream.write(line + "\n")
            self._stream.flush()
        except Exception:                                       # pragma: no cover
            pass
        return rec

    def debug(self, event, **f):
        return self._emit("debug", event, **f)

    def info(self, event, **f):
        return self._emit("info", event, **f)

    def warn(self, event, **f):
        return self._emit("warn", event, **f)

    def error(self, event, **f):
        return self._emit("error", event, **f)

    # ------------------------------------------------------------ استثناء --
    def exception(self, event, exc, **fields):
        """يسجّل استثناءً بلا تسريب نصّه في الإنتاج.

        الإنتاج: صنف الاستثناء + الملفّ والسطر الأخير — يكفيان للتشخيص.
        التطوير: الأثر الكامل."""
        where = None
        try:
            tb = exc.__traceback__
            last = None
            while tb is not None:
                last = tb
                tb = tb.tb_next
            if last is not None:
                where = "%s:%d" % (os.path.basename(last.tb_frame.f_code.co_filename),
                                   last.tb_lineno)
        except Exception:                                       # pragma: no cover
            where = None
        fields.setdefault("error_class", type(exc).__name__)
        if where:
            fields.setdefault("error_at", where)
        if STACK_TRACES:
            fields["stack"] = _redact("".join(
                _tb.format_exception(type(exc), exc, exc.__traceback__)))[-4000:]
        return self._emit("error", event, **fields)

    # ------------------------------------------------------------- تليمتري --
    def generation(self, **fields):
        """تليمتري توليد: أرقام وتصنيفات فقط (F-13). لا وصف زائر ولا رد خام."""
        # KI-24/F-38: chunk_index و chunk_count معلنان صراحةً. القناة تُسقط أي
        # حقل غير معلن، فلولا إعلانهما لاختفى موضع العطل من سجلّ الإنتاج بلا
        # أثر — وهو ما يجعل شريحةً فاشلة بين عشرين شريحة غير قابلة للتشخيص.
        allowed = ("request_id", "strategy", "model", "stages", "input_tokens",
                   "output_tokens", "stop_reason", "max_output_tokens",
                   "duration_ms", "retries", "truncated", "upstream_class",
                   "success", "error_code", "estimated_cost_usd", "escalations",
                   "endpoint", "chunk_index", "chunk_count",
                   # F-50: بلا هذه الحقول كان سجلّ الإنتاج يقول
                   # `upstream_class=BadRequestError` ولا يقول أيّ وسيط رفضه
                   # المزوّد ولا أيّ سقف طُلب ولا أيّ نسخة SDK تعمل. كلّها
                   # مصنّفات وأرقام: لا نصّ زائر ولا رد خام ولا مفتاح.
                   # (sdk_version كان يُقاس فعلاً في acs_understand ثم تُسقطه
                   #  هذه القائمة صامتةً — نفس عطل KI-24/F-38 في موضع آخر.)
                   "sdk_version", "transport", "thinking_sent",
                   "provider_error_type", "provider_param",
                   "provider_limit", "provider_detail",
                   "requested_max_tokens", "budget_clamped",
                   # هجرة المزوّد: أيّ مزوّد ونموذج ومضيف خدم هذا النداء، وهل
                   # وقع تحويل إلى بديل ولماذا. `provider_base_host` مضيفٌ
                   # وحده — لا عنوان كامل، فالعنوان قد يحمل اعتماداً مضمَّناً.
                   "provider", "provider_model", "provider_base_host",
                   "fallback_attempted", "fallback_provider",
                   "fallback_reason", "fallback_success",
                   # W2-A: محاسبة كتل الرد. بلا هذه الحقول لا يستطيع السجلّ
                   # الإجابة عن «out_tokens=16000 و out_chars=0 — أين ذهبت؟»،
                   # وهو السؤال الذي يقرّر تصميم W2-C. أنواعٌ وأعدادٌ وأطوال:
                   # لا نصّ، ولا محتوى كتلة، ولا توجيه، ولا مفتاح.
                   "output_chars", "chars_per_output_token",
                   "content_blocks", "content_block_types",
                   "text_blocks", "nontext_blocks", "text_block_chars",
                   "cache_read_input_tokens", "cache_creation_input_tokens",
                   "reasoning_tokens",
                   # W2-D: محاولةٌ مطابقة بايتاً لم تُرسَل.
                   "retry_skipped_reason", "retries_skipped")
        clean = {k: v for k, v in fields.items() if k in allowed}
        return self._emit("info", "llm_generation", **clean)


def request_fields(request_id=None, endpoint=None, method=None, status=None,
                   duration_ms=None, error_code=None, upstream_class=None,
                   stage=None):
    """الحقول المعلنة لكل حدث في مسار الطلب."""
    return {"request_id": request_id, "endpoint": endpoint, "method": method,
            "status": status, "duration_ms": duration_ms,
            "error_code": error_code, "upstream_class": upstream_class,
            "stage": stage}


def health_status():
    return {"level": MIN_LEVEL, "env": ENV, "stack_traces": STACK_TRACES,
            "structured": True, "redacted_fields": len(FORBIDDEN_FIELDS)}


LOG = StructuredLogger()
