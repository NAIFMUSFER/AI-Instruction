# -*- coding: utf-8 -*-
# =============================================================================
# acs_generation_job.py — تنفيذ التوليد كوظيفة قابلة للإلغاء فعلاً (F-06).
#
# ما كان يحدث: التوليد يُنفَّذ في خيط داخل ThreadPoolExecutor، والمهلة تُطبَّق على
# الانتظار وحده عبر asyncio.wait_for(shield(fut)). بايثون لا تقتل خيطاً، فالخيط
# المتروك يُكمل نداء المزوّد حتى 600 ثانية أخرى وهو يحتجز أحد ثمانية مقاعد.
# تسعة عملاء متروكين يشبعون المجمّع ويحوّلون كل طلب تالٍ إلى 504 — انهيار متتالٍ.
#
# ما يحدث الآن: كل توليد عملية مستقلّة (multiprocessing). المهلة تُنهي العملية
# فعلاً — terminate ثم kill — فيتحرّر المقعد فوراً ويتوقّف استهلاك المزوّد.
#
# الحدّ المُعلَن بصدق: إلغاء عملية لا يُلغي الطلب الذي وصل مزوّد النموذج بالفعل.
# لا واجهة إلغاء في SDK المزوّد اليوم؛ ما نضمنه أن الخادم لا يبقى محتجَزاً وأن
# الرد المهجور لا يُودَع ولا ينتج مراجعة. الحدّ موصوف هنا لا مُدّعى تجاوزه.
# =============================================================================
import importlib
import multiprocessing
import os
import threading
import time
import uuid

STATE_PENDING = "PENDING"
STATE_RUNNING = "RUNNING"
STATE_SUCCEEDED = "SUCCEEDED"
STATE_FAILED = "FAILED"
STATE_TIMED_OUT = "TIMED_OUT"
STATE_CANCELLED = "CANCELLED"
STATE_REJECTED = "REJECTED"

TERMINAL = (STATE_SUCCEEDED, STATE_FAILED, STATE_TIMED_OUT,
            STATE_CANCELLED, STATE_REJECTED)

EXECUTOR_PROCESS = "process"
EXECUTOR_THREAD = "thread"


def _env(name, default=""):
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _env_int(name, default):
    try:
        return int(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


CAPACITY = max(1, _env_int("ACS_JOB_CAPACITY", _env_int("ACS_WORKER_THREADS", 8)))
DEFAULT_TIMEOUT_S = _env_float("ACS_REQUEST_TIMEOUT_S", 840.0)
ADMISSION_WAIT_S = _env_float("ACS_JOB_ADMISSION_WAIT_S", 0.0)
TERMINATE_GRACE_S = _env_float("ACS_JOB_TERMINATE_GRACE_S", 3.0)
EXECUTOR = _env("ACS_JOB_EXECUTOR", EXECUTOR_PROCESS).lower()
START_METHOD = _env("ACS_JOB_START_METHOD", "spawn").lower()


class JobRejected(Exception):
    """لا مقعد متاح. الرفض الصريح أصدق من طابور بلا سقف ثم 504 للجميع."""


class JobError(Exception):
    def __init__(self, message, error_class=None):
        Exception.__init__(self, message)
        self.error_class = error_class or "Exception"


def _child(target, kwargs, conn):                               # pragma: no cover
    """جسم العملية الابنة — تُستورَد الوحدة هنا لا تُنقَل الدالّة."""
    try:
        mod_name, fn_name = target.split(":", 1)
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
        value = fn(**(kwargs or {}))
        conn.send(("ok", value))
    except BaseException as exc:                                # noqa: BLE001
        try:
            conn.send(("err", (type(exc).__name__, str(exc)[:2000])))
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


class GenerationJob(object):
    """وظيفة توليد واحدة — بحالة معلنة وإلغاء حقيقي."""

    __slots__ = ("id", "state", "created_at", "started_at", "finished_at",
                 "request_id", "target", "result", "error", "error_class",
                 "_proc", "_parent", "_lock", "_cancelled", "timeout_s")

    def __init__(self, target, request_id=None, timeout_s=None):
        self.id = "job_" + uuid.uuid4().hex[:16]
        self.state = STATE_PENDING
        self.created_at = time.time()
        self.started_at = None
        self.finished_at = None
        self.request_id = request_id
        self.target = target
        self.result = None
        self.error = None
        self.error_class = None
        self.timeout_s = float(timeout_s or DEFAULT_TIMEOUT_S)
        self._proc = None
        self._parent = None
        self._lock = threading.Lock()
        self._cancelled = False

    # ------------------------------------------------------------ إلغاء ----
    def cancel(self, reason=STATE_CANCELLED):
        """يُنهي العملية فعلاً. آمن للاستدعاء مرّتين، ولا يترك عملية يتيمة."""
        with self._lock:
            self._cancelled = True
            proc = self._proc
            if self.state in TERMINAL:
                return self.state
            self.state = reason
            self.finished_at = time.time()
        if proc is not None and proc.is_alive():
            try:
                proc.terminate()
                proc.join(TERMINATE_GRACE_S)
            except Exception:                                   # pragma: no cover
                pass
            if proc.is_alive():
                try:
                    proc.kill()
                    proc.join(TERMINATE_GRACE_S)
                except Exception:                               # pragma: no cover
                    pass
        return self.state

    @property
    def cancelled(self):
        return self._cancelled

    def duration_ms(self):
        end = self.finished_at or time.time()
        start = self.started_at or self.created_at
        return int((end - start) * 1000)

    def snapshot(self):
        return {"id": self.id, "state": self.state, "request_id": self.request_id,
                "target": self.target, "created_at": self.created_at,
                "started_at": self.started_at, "finished_at": self.finished_at,
                "duration_ms": self.duration_ms(),
                "error_class": self.error_class,
                "timeout_s": self.timeout_s}


class JobRunner(object):
    """سعة محدودة + تنفيذ في عملية قابلة للإنهاء."""

    def __init__(self, capacity=None, executor=None, start_method=None):
        self.capacity = int(capacity or CAPACITY)
        self.executor = (executor or EXECUTOR).lower()
        self._sem = threading.BoundedSemaphore(self.capacity)
        self._in_flight = {}
        self._lock = threading.Lock()
        self._stats = {"submitted": 0, "succeeded": 0, "failed": 0,
                       "timed_out": 0, "rejected": 0, "cancelled": 0}
        method = (start_method or START_METHOD)
        try:
            self._ctx = multiprocessing.get_context(method)
        except ValueError:                                      # pragma: no cover
            self._ctx = multiprocessing.get_context()

    # ------------------------------------------------------------ قياسات ---
    def in_flight(self):
        with self._lock:
            return len(self._in_flight)

    def available(self):
        return max(0, self.capacity - self.in_flight())

    def stats(self):
        with self._lock:
            return dict(self._stats)

    def health_status(self):
        return {"executor": self.executor, "capacity": self.capacity,
                "in_flight": self.in_flight(), "available": self.available(),
                "cancellable": self.executor == EXECUTOR_PROCESS,
                "start_method": getattr(self._ctx, "_name", "unknown"),
                "stats": self.stats(),
                "boundary_note": ("terminating the worker frees the server slot and "
                                  "stops local work; a request already accepted by "
                                  "the model provider is not recalled — no provider "
                                  "cancellation API is claimed")}

    # ------------------------------------------------------------ تشغيل ----
    def run(self, target, kwargs=None, timeout_s=None, request_id=None,
            on_event=None):
        """ينفّذ target ("module:function") ويعيد النتيجة أو يرفع JobError.

        عند المهلة: تُنهى العملية، يتحرّر المقعد، ويُرفَع TimeoutError."""
        job = GenerationJob(target, request_id=request_id, timeout_s=timeout_s)
        if not self._sem.acquire(blocking=ADMISSION_WAIT_S > 0,
                                 timeout=ADMISSION_WAIT_S or None):
            job.state = STATE_REJECTED
            job.finished_at = time.time()
            with self._lock:
                self._stats["rejected"] += 1
            if on_event:
                on_event(job)
            raise JobRejected("all %d generation slots are busy" % self.capacity)
        with self._lock:
            self._in_flight[job.id] = job
            self._stats["submitted"] += 1
        try:
            return self._execute(job, kwargs or {}, on_event)
        finally:
            with self._lock:
                self._in_flight.pop(job.id, None)
            try:
                self._sem.release()
            except ValueError:                                  # pragma: no cover
                pass

    def _execute(self, job, kwargs, on_event):
        if self.executor == EXECUTOR_THREAD:
            return self._execute_thread(job, kwargs, on_event)
        parent, child = self._ctx.Pipe(duplex=False)
        proc = self._ctx.Process(target=_child, args=(job.target, kwargs, child),
                                 daemon=True)
        job._proc = proc
        job._parent = parent
        job.started_at = time.time()
        job.state = STATE_RUNNING
        proc.start()
        child.close()                       # الأب لا يحتفظ بطرف الكتابة
        try:
            ready = parent.poll(job.timeout_s)
            if not ready:
                job.cancel(STATE_TIMED_OUT)
                with self._lock:
                    self._stats["timed_out"] += 1
                if on_event:
                    on_event(job)
                raise TimeoutError("generation exceeded %d s and the worker was "
                                   "terminated" % int(job.timeout_s))
            kind, payload = parent.recv()
        except (EOFError, OSError) as exc:
            job.state = STATE_FAILED
            job.error_class = type(exc).__name__
            job.finished_at = time.time()
            with self._lock:
                self._stats["failed"] += 1
            if on_event:
                on_event(job)
            raise JobError("the generation worker died before returning a result",
                           type(exc).__name__)
        finally:
            try:
                parent.close()
            except Exception:                                   # pragma: no cover
                pass
            if proc.is_alive():
                proc.terminate()
            proc.join(TERMINATE_GRACE_S)
            if proc.is_alive():                                 # pragma: no cover
                proc.kill()
                proc.join(TERMINATE_GRACE_S)
        job.finished_at = time.time()
        if kind == "ok":
            job.state = STATE_SUCCEEDED
            job.result = payload
            with self._lock:
                self._stats["succeeded"] += 1
            if on_event:
                on_event(job)
            return payload
        job.state = STATE_FAILED
        job.error_class, job.error = payload
        with self._lock:
            self._stats["failed"] += 1
        if on_event:
            on_event(job)
        raise JobError(job.error, job.error_class)

    def _execute_thread(self, job, kwargs, on_event):
        """مسار احتياطي للتطوير فقط — لا يضمن الإلغاء، ويقول ذلك."""
        box = {}

        def _run():
            try:
                mod_name, fn_name = job.target.split(":", 1)
                fn = getattr(importlib.import_module(mod_name), fn_name)
                box["ok"] = fn(**kwargs)
            except BaseException as exc:                        # noqa: BLE001
                box["err"] = (type(exc).__name__, str(exc)[:2000])

        th = threading.Thread(target=_run, daemon=True)
        job.started_at = time.time()
        job.state = STATE_RUNNING
        th.start()
        th.join(job.timeout_s)
        if th.is_alive():
            job.state = STATE_TIMED_OUT
            job.finished_at = time.time()
            with self._lock:
                self._stats["timed_out"] += 1
            if on_event:
                on_event(job)
            raise TimeoutError("generation exceeded %d s; the thread executor cannot "
                               "cancel the worker — use the process executor"
                               % int(job.timeout_s))
        job.finished_at = time.time()
        if "err" in box:
            job.state = STATE_FAILED
            job.error_class, job.error = box["err"]
            with self._lock:
                self._stats["failed"] += 1
            if on_event:
                on_event(job)
            raise JobError(job.error, job.error_class)
        job.state = STATE_SUCCEEDED
        job.result = box.get("ok")
        with self._lock:
            self._stats["succeeded"] += 1
        if on_event:
            on_event(job)
        return job.result


_DEFAULT = None
_DEFAULT_LOCK = threading.Lock()


def default_runner():
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = JobRunner()
        return _DEFAULT


def reset_default_runner():
    """للاختبار فقط."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        _DEFAULT = None


def health_status():
    return default_runner().health_status()


# ------------------------------------------------- أهداف اختبارية معلنة ----
def _sleep_forever(seconds=86400.0, **_):                       # pragma: no cover
    """هدف اصطناعي: مزوّد لا يردّ. يُستعمل في اختبار الإلغاء وحده."""
    marker = _env("ACS_JOB_TEST_MARKER", "")
    if marker:
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
    time.sleep(float(seconds))
    return "never"


def _echo(value=None, **_):                                     # pragma: no cover
    return value


def _boom(message="synthetic provider failure", **_):           # pragma: no cover
    raise RuntimeError(message)
