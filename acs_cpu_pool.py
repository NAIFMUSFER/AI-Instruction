# -*- coding: utf-8 -*-
"""acs_cpu_pool — عزل العمل الحاسوبيّ الثقيل عن حلقة الأحداث (KI-14 · F-46).

العطل الذي تغلقه هذه الوحدة
---------------------------
كان معالجا الرفع في acs_understand_api يستدعيان مدقّق الرفع **متزامناً داخل
`async def`**:

    @app.post("/v1/understand/image")
    async def understand_image(...):
        checked = UPLOAD.validate_images(raw)      # ← فكّ بكسلات على الحلقة

    @app.post("/v1/understand/pdf")
    async def understand_pdf(...):
        checked = UPLOAD.validate_pdf(data)        # ← تحليل صفحات على الحلقة

وفكّ الصورة وتحليل الـPDF عملٌ حاسوبيّ خالص. القياس على أثقل **مدخل مقبول**
(tests/remediation/test_event_loop.py):

    صورة واحدة 3340×3340 (‎33.5 م.ب مفكوكة، تحت السقف بالضبط)
        → توقّف حلقة 440 ms · أطول طلب خفيف 443 ms
    ستّ صور — وهي **مرفوضة** بتجاوز ميزانية البكسل
        → توقّف حلقة 1505 ms قبل أن تُرفض

الثانية أسوأ: الرفض نفسه يكلّف الخادم ثانيةً ونصفاً من الشلل التامّ، فيصير
سلاحَ حرمانٍ من الخدمة بحمولةٍ ترفضها البوّابة أصلاً. طوال ذلك لا يُخدَم
‎/health‎ ولا ‎/ready‎ ولا أيّ طلب آخر: العمليّة كلّها متوقّفة، لا بطيئة.

المعمارية
---------
مجمّع **عمليات** محدود ودائم — لا عملية لكل نداء. المدقّق يُنفَّذ في عاملٍ
منفصل، والحلقة تنتظره بـ`await` فتبقى حرّة لخدمة كل شيء آخر.

  · لماذا عمليات لا خيوط: pypdf بايثون خالص يمسك القفل العامّ طوال التحليل،
    فخيطٌ لا يحرّر الحلقة إلّا جزئياً. وPillow يحرّر القفل في الفكّ ويمسكه في
    محاسبة الميزانية. العمليّة تحرّرها كاملةً بلا استثناء.
  · لماذا مجمّع دائم لا `JobRunner`: مشغّل التوليد يولّد عمليةً لكل مهمّة
    (وهو صحيح هناك: مهمّة تدوم دقائق ويجب أن تكون قابلة للإنهاء). تدقيقٌ
    يستغرق ٤٠٠ms لا يحتمل ٣٠٠ms إنشاء عملية، ولا يجوز أن يستهلك مقعداً من
    مقاعد التوليد فيرفض توليداً مشروعاً.
  · لماذا لا يُنقَل الاستثناء عبر الحدّ: `UploadRejected(code, message_ar,
    detail)` لا يُفكّ تخليصه (pickle يستدعي `__init__` بوسيط واحد). فالعامل
    يعيد **مغلّفاً** لا استثناءً، والأب يعيد بناء الرفض من رموزٍ معلنة.

الحدود المفروضة هنا — كلّها صريحة وقابلة للقياس
------------------------------------------------
  عدد العمّال            ACS_CPU_WORKERS        (افتراضي ٢)
  عمق الطابور            ACS_CPU_QUEUE          (افتراضي ٨)
  مهلة العملية الواحدة   ACS_CPU_TIMEOUT_S      (افتراضي ٤٥)
  إعادة تدوير العامل     ACS_CPU_TASKS_PER_CHILD (افتراضي ٥٠)

عند الإشباع يُرفض الطلب **صراحةً وحتميّاً** (ACS_RATE_LIMITED مع Retry-After)
لا يُصفّ بلا سقف ثم يُقتل بمهلة البوّابة.

حدّ الإلغاء — معلَن بلا مواربة
------------------------------
عند المهلة أو انقطاع العميل يُحرَّر المقعد فوراً ويُرفَع ACS_TIMEOUT مصنّفاً.
العامل يُكمل ما بدأه: بايثون لا تقتل مهمّةً داخل `ProcessPoolExecutor`، ولا
نزعم أننا نفعل — وهو نفس الحدّ المعلَن في مشغّل التوليد تجاه المزوّد. الفارق
الجوهريّ هنا أن العمل **محدودٌ بعقد المدخل نفسه** (سقف البايتات والبكسلات
والصفحات والفكّ)، فالعامل المتروك ينتهي في زمن محدود مقيس لا يفتح باب استهلاك
غير محدود. وإعادة تدوير العامل بعد ACS_CPU_TASKS_PER_CHILD مهمّة تمنع تراكم
الذاكرة.
"""
import concurrent.futures
import os
import threading
import time

CONTRACT_VERSION = "acs.cpu-pool/1.0.0"


def _env_int(name, default):
    try:
        v = int(str(os.environ.get(name, "")).strip() or default)
    except (TypeError, ValueError):
        return int(default)
    return v if v > 0 else int(default)


def _env_float(name, default):
    try:
        v = float(str(os.environ.get(name, "")).strip() or default)
    except (TypeError, ValueError):
        return float(default)
    return v if v > 0 else float(default)


CPU_WORKERS = _env_int("ACS_CPU_WORKERS", 2)
CPU_QUEUE = _env_int("ACS_CPU_QUEUE", 8)
CPU_TIMEOUT_S = _env_float("ACS_CPU_TIMEOUT_S", 45.0)
CPU_TASKS_PER_CHILD = _env_int("ACS_CPU_TASKS_PER_CHILD", 50)

EXEC_PROCESS = "process"
EXEC_THREAD = "thread"

# الأهداف المسموح تنفيذها في العامل — قائمة معلنة، لا اسم يصل من الشبكة.
TARGETS = {
    "validate_images": ("acs_upload_security", "validate_images"),
    "validate_image": ("acs_upload_security", "validate_image"),
    "validate_pdf": ("acs_upload_security", "validate_pdf"),
    "validate_json_bytes": ("acs_upload_security", "validate_json_bytes"),
    "validate_dxf_bytes": ("acs_upload_security", "validate_dxf_bytes"),
    # KI-14: مخطّط سلطة التغيير الهندسي يعمل على **كل** رد ناجح من
    # /v1/understand، وكلفته تنمو فوق الخطّية مع عدد الغرف: قياساً ٢٫٨ms عند
    # ٢٠ غرفة، و٣٩٨ms عند ١٦٠٠، و**٥٧١٤ms** عند ٨٤٠٠ — وكلّها نماذج تحت سقف
    # ACS_MAX_BUILDING. خمس ثوانٍ من الشلل التامّ على ردٍّ ناجح.
    "ea_plan": ("acs_engineering_authority", "plan"),
    "ea_flat_diff": ("acs_engineering_authority", "flat_diff"),
}


class PoolSaturated(Exception):
    """لا مقعد ولا موضع في الطابور. الرفض الصريح أصدق من طابور بلا سقف."""


class PoolTimeout(Exception):
    """تجاوزت العملية مهلتها. المقعد حُرّر، والعامل يُكمل عملاً محدوداً بالعقد."""


class WorkerCrashed(Exception):
    """مات العامل (OOM أو إشارة). يُصنَّف عطلَ خادم لا عطلَ عميل."""


# ---------------------------------------------------------------------------
# ما يُنفَّذ في العامل. دالّة عليا وحدها — قابلة للتخليص تحت spawn.
# ---------------------------------------------------------------------------
def _worker(target, args, kwargs):                              # pragma: no cover
    """ينفّذ هدفاً معلناً ويعيد **مغلّفاً** لا استثناء.

    الاستثناء لا يعبر الحدّ: `UploadRejected` لا يُفكّ تخليصه، وأثرُ الاستدعاء
    قد يحمل مسارات ومحتوى. فيُعاد رمزٌ ورسالةٌ معلنان لا غير.
    """
    import importlib
    mod_name, fn_name = TARGETS[target]
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name)
    try:
        return {"ok": True, "value": fn(*(args or ()), **(kwargs or {}))}
    except BaseException as exc:                                # noqa: BLE001
        code = getattr(exc, "code", None)
        if code is not None:
            return {"ok": False, "kind": "rejected", "code": str(code),
                    "message_ar": str(getattr(exc, "message_ar", "") or "")[:400],
                    "detail": str(getattr(exc, "detail", "") or "")[:200]}
        return {"ok": False, "kind": "error",
                "error_class": type(exc).__name__,
                "message": str(exc)[:300]}


class CpuPool(object):
    """مجمّع محدود دائم + قبولٌ محسوب + مهلة + قياسات."""

    def __init__(self, workers=None, queue=None, timeout_s=None,
                 executor=EXEC_PROCESS, tasks_per_child=None):
        self.workers = int(workers or CPU_WORKERS)
        self.queue = int(queue if queue is not None else CPU_QUEUE)
        self.timeout_s = float(timeout_s or CPU_TIMEOUT_S)
        self.capacity = self.workers + self.queue
        self.tasks_per_child = int(tasks_per_child or CPU_TASKS_PER_CHILD)
        self._sem = threading.BoundedSemaphore(self.capacity)
        self._lock = threading.Lock()
        self._in_flight = 0
        self._executor = None
        self._kind = None
        self._requested = executor
        self._degraded_reason = None
        self._stats = {"submitted": 0, "succeeded": 0, "rejected_input": 0,
                       "saturated": 0, "timed_out": 0, "crashed": 0,
                       "failed": 0}
        self._max_wait_ms = 0.0

    # ------------------------------------------------------------ إقلاع ----
    def _ensure(self):
        if self._executor is not None:
            return self._executor
        with self._lock:
            if self._executor is not None:
                return self._executor
            if self._requested == EXEC_PROCESS:
                try:
                    import multiprocessing
                    ctx = multiprocessing.get_context("spawn")
                    kw = {"max_workers": self.workers, "mp_context": ctx}
                    # max_tasks_per_child موجود منذ 3.11 — يمنع تراكم الذاكرة.
                    try:
                        self._executor = concurrent.futures.ProcessPoolExecutor(
                            max_tasks_per_child=self.tasks_per_child, **kw)
                    except TypeError:                           # pragma: no cover
                        self._executor = concurrent.futures.ProcessPoolExecutor(**kw)
                    self._kind = EXEC_PROCESS
                except Exception as exc:                        # noqa: BLE001
                    # منصّة تمنع spawn: نتراجع إلى خيوط **ونُعلن ذلك**. لا
                    # تدهور صامت: /health يقول executor=thread و degraded=true.
                    self._degraded_reason = type(exc).__name__
                    self._executor = concurrent.futures.ThreadPoolExecutor(
                        max_workers=self.workers,
                        thread_name_prefix="acs-cpu")
                    self._kind = EXEC_THREAD
            else:
                self._executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.workers, thread_name_prefix="acs-cpu")
                self._kind = EXEC_THREAD
            return self._executor

    def warmup(self):
        """يوقظ العمّال قبل أول طلب حقيقيّ، فلا يدفع أوّل مستخدمٍ ثمن الإقلاع."""
        ex = self._ensure()
        try:
            list(ex.map(_noop, range(self.workers)))
        except Exception:                                       # noqa: BLE001
            pass
        return self.health_status()

    # ------------------------------------------------------------ تنفيذ ---
    def submit(self, target, args=(), kwargs=None, timeout_s=None):
        """يعيد (future, release) — المستدعي ينتظر بـ`await` ثم يُطلق المقعد."""
        if target not in TARGETS:
            raise KeyError("undeclared cpu-pool target: %r" % (target,))
        if not self._sem.acquire(blocking=False):
            with self._lock:
                self._stats["saturated"] += 1
            raise PoolSaturated(
                "cpu pool saturated: %d workers + %d queue all busy"
                % (self.workers, self.queue))
        ex = self._ensure()
        with self._lock:
            self._in_flight += 1
            self._stats["submitted"] += 1
        released = {"v": False}

        def release():
            if released["v"]:
                return
            released["v"] = True
            with self._lock:
                self._in_flight = max(0, self._in_flight - 1)
            try:
                self._sem.release()
            except ValueError:                                  # pragma: no cover
                pass

        try:
            fut = ex.submit(_worker, target, tuple(args), dict(kwargs or {}))
        except Exception:                                       # noqa: BLE001
            release()
            raise
        return fut, release

    def unwrap(self, envelope):
        """يعيد بناء النتيجة أو الرفض من مغلّف العامل."""
        if not isinstance(envelope, dict):
            with self._lock:
                self._stats["failed"] += 1
            raise WorkerCrashed("cpu worker returned a malformed envelope")
        if envelope.get("ok"):
            with self._lock:
                self._stats["succeeded"] += 1
            return envelope.get("value")
        if envelope.get("kind") == "rejected":
            with self._lock:
                self._stats["rejected_input"] += 1
            import acs_upload_security as U
            raise U.UploadRejected(envelope.get("code") or "UPLOAD_REJECTED",
                                   envelope.get("message_ar") or "",
                                   envelope.get("detail") or "")
        with self._lock:
            self._stats["failed"] += 1
        raise WorkerCrashed("%s: %s" % (envelope.get("error_class") or "Exception",
                                        envelope.get("message") or ""))

    def note_timeout(self):
        with self._lock:
            self._stats["timed_out"] += 1

    def note_crash(self):
        with self._lock:
            self._stats["crashed"] += 1

    def note_wait(self, ms):
        if ms > self._max_wait_ms:
            self._max_wait_ms = ms

    # ------------------------------------------------------------ قياس ----
    def in_flight(self):
        with self._lock:
            return self._in_flight

    def available(self):
        return max(0, self.capacity - self.in_flight())

    def health_status(self):
        return {"contract": CONTRACT_VERSION,
                "executor": self._kind or ("%s (not started)" % self._requested),
                "isolated": self._kind == EXEC_PROCESS,
                "degraded": bool(self._degraded_reason),
                "degraded_reason": self._degraded_reason,
                "workers": self.workers, "queue": self.queue,
                "capacity": self.capacity,
                "in_flight": self.in_flight(), "available": self.available(),
                "timeout_s": self.timeout_s,
                "tasks_per_child": self.tasks_per_child,
                "max_admission_wait_ms": round(self._max_wait_ms, 1),
                "stats": dict(self._stats),
                "cancellation_note": (
                    "a timed-out validation frees the server slot immediately; "
                    "the worker finishes work that is already bounded by the "
                    "upload contract (bytes, pixels, pages, decompression). "
                    "no in-process task kill is claimed")}

    def shutdown(self, wait=False):
        ex, self._executor = self._executor, None
        self._kind = None
        if ex is not None:
            try:
                ex.shutdown(wait=wait, cancel_futures=True)
            except TypeError:                                   # pragma: no cover
                ex.shutdown(wait=wait)


def _noop(_x):                                                  # pragma: no cover
    return True


_DEFAULT = None
_DEFAULT_LOCK = threading.Lock()


def default_pool():
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = CpuPool()
        return _DEFAULT


def reset_default_pool():
    """للاختبار وحده."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is not None:
            _DEFAULT.shutdown()
        _DEFAULT = None


def health_status():
    return default_pool().health_status()


async def run(target, args=(), kwargs=None, timeout_s=None, pool=None):
    """ينفّذ هدفاً معلناً خارج الحلقة وينتظره بـ`await`. لا يحجب الحلقة أبداً."""
    import asyncio
    p = pool or default_pool()
    limit = float(timeout_s or p.timeout_s)
    t0 = time.perf_counter()
    fut, release = p.submit(target, args, kwargs, limit)
    aio = asyncio.wrap_future(fut)
    try:
        env = await asyncio.wait_for(aio, timeout=limit)
    except asyncio.TimeoutError:
        p.note_timeout()
        release()
        raise PoolTimeout("validation exceeded %.0fs" % limit)
    except concurrent.futures.process.BrokenProcessPool as exc:
        p.note_crash()
        release()
        # عاملٌ مات يترك المجمّع معطوباً: يُعاد بناؤه فلا يبقى الخادم بلا تدقيق.
        p.shutdown()
        raise WorkerCrashed(type(exc).__name__)
    except asyncio.CancelledError:
        # انقطاع العميل: المقعد يعود فوراً، والعمل محدود بعقد المدخل فينتهي.
        release()
        raise
    else:
        release()
    p.note_wait((time.perf_counter() - t0) * 1000.0)
    return p.unwrap(env)


SPEC = {"module": "acs_cpu_pool", "contract_version": CONTRACT_VERSION,
        "targets": sorted(TARGETS), "workers": CPU_WORKERS, "queue": CPU_QUEUE,
        "timeout_s": CPU_TIMEOUT_S, "tasks_per_child": CPU_TASKS_PER_CHILD,
        "guarantees": [
            "no CPU-heavy validation runs on the asyncio event loop",
            "concurrency is bounded by workers+queue and saturation is an "
            "explicit deterministic rejection, never an unbounded queue",
            "a timed-out or disconnected request frees its slot immediately",
            "abandoned work is bounded by the upload contract, so it terminates",
            "a worker crash rebuilds the pool instead of disabling validation",
            "falling back from processes to threads is reported, never silent"]}
