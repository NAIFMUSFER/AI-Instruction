# -*- coding: utf-8 -*-
"""F-06 — إلغاء التوليد فعلاً: المهلة تُنهي العامل ولا تتركه يستنزف المقعد.

يعيد إنتاج العيب ثم يثبت زواله:

  كان التوليد يُنفَّذ في خيط داخل ThreadPoolExecutor والمهلة تُطبَّق على الانتظار
  وحده. بايثون لا تقتل خيطاً، فالخيط المتروك يُكمل نداء المزوّد حتى ٦٠٠ ثانية
  أخرى وهو يحتجز أحد ثمانية مقاعد؛ تسعة عملاء متروكين يشبعون المجمّع ويحوّلون
  كل طلب تالٍ إلى 504.

  الآن كل توليد عملية مستقلّة. هذا الملفّ لا يقرأ الشيفرة ليصدّقها: يشغّل هدفاً
  اصطناعياً معلّقاً حقيقياً، يقرأ رقم عملية الابن من ملفّ علامة، ويثبت بعد المهلة
  أن الابن لم يعد حيّاً ولا بقي زومبي، وأن المقعد عاد فوراً.

الأقسام:
  أ) المسار السعيد ومسار الفشل: حالة معلنة ومقعد يعود.
  ب) المزوّد المعلّق: TimeoutError حقيقيّ، وعملية ابن ميّتة.
  ج) لا عملية يتيمة ولا زومبي غير محصود.
  د) السعة: رفض صريح لا طابور بلا سقف، ثم تعافٍ.
  هـ) cancel() آمن للاستدعاء مرّتين.
  و) لا نتيجة تُودَع ولا مراجعة تُنشأ عند المهلة.
  ز) صدق منفّذ الخيوط: يقول إنه لا يُلغي، ولا يدّعي إنهاءً.
  ح) health_status: حدود معلنة بلا أسرار.
  ط) فحص ربط ساكن: كل مسار توليد يمرّ عبر run_job.

ملاحظة تشغيلية: طريقة البدء spawn تعيد تنفيذ الوحدة الرئيسة في الابن، لذلك كل
العمل داخل main() خلف حارس __main__، ولا يُطبع شيء في نطاق الوحدة.
"""
import ast
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

# تُقرأ هذه عند الاستيراد داخل الوحدة تحت الاختبار، فتُضبط قبله.
os.environ["ACS_JOB_ADMISSION_WAIT_S"] = "0"
os.environ["ACS_JOB_EXECUTOR"] = "process"
os.environ["ACS_JOB_START_METHOD"] = "spawn"

import acs_authoring as A                                          # noqa: E402
import acs_generation_job as J                                     # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


# ─────────────────────────────────────────────────────────────── أدوات ────
TARGET_HANG = "acs_generation_job:_sleep_forever"
TARGET_ECHO = "acs_generation_job:_echo"
TARGET_BOOM = "acs_generation_job:_boom"

SECRETISH = re.compile(
    r'(?i)(secret|token|password|passwd|api[_-]?key|apikey|credential|'
    r'authorization|cookie|private[_-]?key|bearer|session[_-]?id)')

TMPDIR = [None]


def tmp_marker(name):
    """ملفّ علامة داخل مجلّد مؤقّت واحد يُحذف كلّه في النهاية."""
    return os.path.join(TMPDIR[0], name)


def set_marker(path):
    """يُضبط في os.environ قبل بدء الابن — spawn يورّث البيئة لا الذاكرة."""
    os.environ["ACS_JOB_TEST_MARKER"] = path or ""


def read_marker(path, wait_s=3.0):
    """يقرأ رقم عملية الابن، بانتظار محدود لأن الكتابة تحدث في الابن."""
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                raw = fh.read().strip()
            if raw:
                return int(raw)
        except (OSError, ValueError):
            pass
        time.sleep(0.02)
    return None


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:                                    # pragma: no cover
        return True


def pid_state(pid):
    """حرف الحالة من /proc/<pid>/stat، أو None إذا اختفى القيد كلّياً."""
    try:
        with open('/proc/%d/stat' % pid, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        return raw.rsplit(')', 1)[1].split()[0]
    except (OSError, IndexError):
        return None


def wait_reaped(pid, wait_s=5.0):
    """انتظار محدود للحصاد. يعيد (حيّ؟، حالة /proc الأخيرة)."""
    deadline = time.time() + wait_s
    state = pid_state(pid)
    while time.time() < deadline:
        if not pid_alive(pid) and state is None:
            return False, None
        time.sleep(0.05)
        state = pid_state(pid)
    return pid_alive(pid), state


def catcher():
    """يلتقط كائن الوظيفة من on_event ليُفحص حالتها المعلنة."""
    seen = []
    return seen, lambda job: seen.append(job.snapshot())


def raised(fn):
    try:
        return None, fn()
    except BaseException as exc:                                  # noqa: BLE001
        return exc, None


def keys_of(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            keys_of(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            keys_of(v, out)
    return out


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def mk_model():
    return {"meta": {"name": "cancel-probe", "type": "villa"},
            "site": {"w": 20.0, "d": 16.0},
            "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
            "levels": [{"index": 0, "name": "ground", "template": "g"}],
            "floors": {"g": {"rooms": [
                {"id": "living", "rect": [0.0, 0.0, 6.0, 5.0]},
                {"id": "bed", "rect": [7.0, 0.0, 5.0, 4.0]}]}}}


def runner(capacity=2, executor="process"):
    return J.JobRunner(capacity=capacity, executor=executor,
                       start_method="spawn")


# ═══════════════════════════════════════════ أ) المسار السعيد والفشل ══════
def section_happy_and_failure(s):
    print('\n── أ · المسار السعيد ومسار الفشل%s ──' % s)
    r = runner(capacity=2)
    set_marker("")

    seen, ev = catcher()
    before = r.stats()["succeeded"]
    exc, value = raised(lambda: r.run(TARGET_ECHO, {"value": "قيمة"},
                                      timeout_s=20.0, request_id="rq_ok",
                                      on_event=ev))
    chk('_echo returns its value through a real child process%s' % s,
        exc is None and value == "قيمة", '%r / %r' % (exc, value))
    chk('the succeeded job declares state SUCCEEDED%s' % s,
        len(seen) == 1 and seen[-1]["state"] == J.STATE_SUCCEEDED,
        str(seen[-1:]))
    chk('the succeeded job carries the request id%s' % s,
        bool(seen) and seen[-1]["request_id"] == "rq_ok")
    chk('stats().succeeded incremented by exactly one%s' % s,
        r.stats()["succeeded"] == before + 1, str(r.stats()))
    chk('the slot is released after success%s' % s,
        r.in_flight() == 0 and r.available() == r.capacity,
        'in_flight=%d available=%d' % (r.in_flight(), r.available()))

    seen2, ev2 = catcher()
    exc, _ = raised(lambda: r.run(TARGET_BOOM, {"message": "provider blew up"},
                                  timeout_s=20.0, on_event=ev2))
    chk('_boom raises JobError, not a bare exception%s' % s,
        isinstance(exc, J.JobError), type(exc).__name__)
    chk('the JobError carries error_class == "RuntimeError"%s' % s,
        getattr(exc, "error_class", None) == "RuntimeError",
        repr(getattr(exc, "error_class", None)))
    chk('the child exception message survives the process boundary%s' % s,
        "provider blew up" in str(exc), str(exc)[:120])
    chk('the failed job declares state FAILED%s' % s,
        len(seen2) == 1 and seen2[-1]["state"] == J.STATE_FAILED,
        str(seen2[-1:]))
    chk('stats().failed == 1 and succeeded unchanged%s' % s,
        r.stats()["failed"] == 1 and r.stats()["succeeded"] == before + 1,
        str(r.stats()))
    chk('the slot is released after failure%s' % s,
        r.in_flight() == 0 and r.available() == r.capacity,
        'in_flight=%d available=%d' % (r.in_flight(), r.available()))


# ══════════════════════════════════════ ب/ج) المزوّد المعلّق ولا يتيم ══════
def section_hanging_provider(s):
    print('\n── ب · المزوّد المعلّق: مهلة حقيقية وعملية ابن ميّتة%s ──' % s)
    marker = tmp_marker('hang_pid_%s.txt' % (s.strip(' ·') or 'first'))
    if os.path.exists(marker):
        os.unlink(marker)
    set_marker(marker)
    r = runner(capacity=2)
    seen, ev = catcher()

    t0 = time.time()
    exc, _ = raised(lambda: r.run(TARGET_HANG, {"seconds": 600.0},
                                  timeout_s=1.5, request_id="rq_hang",
                                  on_event=ev))
    elapsed = time.time() - t0
    set_marker("")

    chk('the hanging target raises TimeoutError%s' % s,
        isinstance(exc, TimeoutError), '%s: %s' % (type(exc).__name__, exc))
    # الانحدار المحروس: TimeoutError صنف فرعي من OSError، وكان معالج
    # (EOFError, OSError) يبتلعه ويحوّله JobError فتضيع المهلة عن المستدعي.
    chk('the timeout is NOT downgraded to a JobError (OSError subclass trap)%s'
        % s, not isinstance(exc, J.JobError), type(exc).__name__)
    chk('the timeout message names termination of the worker%s' % s,
        'terminated' in str(exc).lower(), str(exc)[:120])
    chk('elapsed is close to the 1.5 s timeout, not the 600 s sleep%s' % s,
        1.0 <= elapsed < 5.0, 'elapsed=%.2fs' % elapsed)

    pid = read_marker(marker)
    chk('the child recorded its own pid in the marker file%s' % s,
        isinstance(pid, int) and pid > 0 and pid != os.getpid(), repr(pid))

    alive, state = (True, '?') if not pid else wait_reaped(pid)
    chk('the child pid is no longer alive after the timeout%s' % s,
        pid and not alive, 'pid=%s still alive, /proc state=%s' % (pid, state))

    chk('stats().timed_out == 1%s' % s,
        r.stats()["timed_out"] == 1, str(r.stats()))
    chk('the timeout is not double-counted as a failure%s' % s,
        r.stats()["failed"] == 0, str(r.stats()))
    chk('the job declares state TIMED_OUT%s' % s,
        len(seen) == 1 and seen[-1]["state"] == J.STATE_TIMED_OUT,
        str(seen[-1:]))
    chk('the job records a finish time%s' % s,
        bool(seen) and seen[-1]["finished_at"] is not None)
    chk('in_flight() == 0 after the timeout%s' % s,
        r.in_flight() == 0, str(r.in_flight()))
    chk('available() == capacity — the worker slot is recovered%s' % s,
        r.available() == r.capacity,
        'available=%d capacity=%d' % (r.available(), r.capacity))

    print('\n── ج · لا عملية يتيمة ولا زومبي غير محصود%s ──' % s)
    chk('no /proc entry survives for the abandoned job%s' % s,
        pid and state is None,
        'pid=%s /proc state=%r (Z means an un-reaped zombie)' % (pid, state))
    chk('the child is not left as an un-reaped zombie%s' % s,
        state != 'Z', '/proc state=%r after a bounded 5 s wait' % (state,))

    try:
        import psutil
        kids = psutil.Process().children(recursive=True)
        rows = [(k.pid, k.status(), ' '.join(k.cmdline()[:3])) for k in kids]
        chk('psutil sees no live child process for that job%s' % s,
            all(k.pid != pid for k in kids), str(rows))
        stray = [x for x in rows if 'resource_tracker' not in x[2]]
        chk('the only surviving child is the multiprocessing resource tracker%s'
            % s, not stray, str(stray))
    except ImportError:                                        # pragma: no cover
        chk('psutil child enumeration%s' % s, False, 'psutil not importable')

    if os.path.exists(marker):
        os.unlink(marker)
    return pid


# ═══════════════════════════════════════════════════════════ د) السعة ═════
def section_capacity(s):
    print('\n── د · السعة: رفض صريح لا طابور بلا سقف%s ──' % s)
    chk('ACS_JOB_ADMISSION_WAIT_S is effectively zero%s' % s,
        J.ADMISSION_WAIT_S == 0.0, repr(J.ADMISSION_WAIT_S))
    set_marker("")
    r = runner(capacity=2)
    outcomes = []

    def occupy():
        exc, _ = raised(lambda: r.run(TARGET_HANG, {"seconds": 600.0},
                                      timeout_s=1.5))
        outcomes.append(type(exc).__name__)

    ths = [threading.Thread(target=occupy, daemon=True) for _ in range(2)]
    for t in ths:
        t.start()
    deadline = time.time() + 5.0
    while r.in_flight() < 2 and time.time() < deadline:
        time.sleep(0.01)
    chk('both slots are occupied by the two long jobs%s' % s,
        r.in_flight() == 2 and r.available() == 0,
        'in_flight=%d available=%d' % (r.in_flight(), r.available()))

    t0 = time.time()
    exc, _ = raised(lambda: r.run(TARGET_ECHO, {"value": 1}, timeout_s=10.0))
    reject_s = time.time() - t0
    chk('a third run() raises JobRejected%s' % s,
        isinstance(exc, J.JobRejected), '%s: %s' % (type(exc).__name__, exc))
    chk('the rejection is immediate — it does not queue unboundedly%s' % s,
        reject_s < 0.5, 'waited %.3fs before rejecting' % reject_s)
    chk('the rejection message names the capacity%s' % s,
        '2' in str(exc), str(exc)[:120])
    chk('stats().rejected == 1 and the rejected job was never submitted%s' % s,
        r.stats()["rejected"] == 1 and r.stats()["submitted"] == 2,
        str(r.stats()))

    for t in ths:
        t.join(20.0)
    chk('both long jobs ended in TimeoutError%s' % s,
        outcomes == ['TimeoutError', 'TimeoutError'], str(outcomes))
    chk('both slots come back after the timeouts%s' % s,
        r.in_flight() == 0 and r.available() == 2,
        'in_flight=%d available=%d' % (r.in_flight(), r.available()))
    chk('stats().timed_out == 2%s' % s, r.stats()["timed_out"] == 2,
        str(r.stats()))
    exc, value = raised(lambda: r.run(TARGET_ECHO, {"value": "again"},
                                      timeout_s=20.0))
    chk('the runner accepts work again after the timeouts%s' % s,
        exc is None and value == "again", '%r / %r' % (exc, value))


# ═════════════════════════════════════════════ هـ) cancel() المتكرّر ══════
def section_cancel_idempotent(s):
    print('\n── هـ · cancel() آمن للاستدعاء مرّتين%s ──' % s)
    job = J.GenerationJob(TARGET_HANG, request_id="rq_cancel")
    exc1, first = raised(job.cancel)
    exc2, second = raised(job.cancel)
    chk('the first cancel() does not raise%s' % s, exc1 is None, repr(exc1))
    chk('the second cancel() does not raise%s' % s, exc2 is None, repr(exc2))
    chk('both calls return a terminal state%s' % s,
        first in J.TERMINAL and second in J.TERMINAL, '%r / %r' % (first, second))
    chk('the second call returns the same terminal state%s' % s,
        first == second == J.STATE_CANCELLED, '%r / %r' % (first, second))
    chk('the job is marked cancelled and keeps a finish time%s' % s,
        job.cancelled and job.finished_at is not None)

    reasoned = J.GenerationJob(TARGET_HANG)
    chk('cancel(reason) honours the declared reason%s' % s,
        reasoned.cancel(J.STATE_TIMED_OUT) == J.STATE_TIMED_OUT)
    chk('a later cancel() cannot overwrite a terminal state%s' % s,
        reasoned.cancel() == J.STATE_TIMED_OUT, reasoned.state)

    # وظيفة انتهت فعلاً بمهلة عبر المشغّل: الإلغاء بعدها لا يزال آمناً.
    set_marker("")
    r = runner(capacity=1)
    seen, ev = catcher()
    raised(lambda: r.run(TARGET_HANG, {"seconds": 600.0}, timeout_s=1.5,
                         on_event=ev))
    chk('a job already timed out by the runner reports TIMED_OUT%s' % s,
        bool(seen) and seen[-1]["state"] == J.STATE_TIMED_OUT, str(seen[-1:]))


# ══════════════════════════ و) لا إيداع ولا مراجعة عند المهلة ════════════
def section_no_commit(s):
    print('\n── و · لا نتيجة تُودَع ولا مراجعة تُنشأ عند المهلة%s ──' % s)
    project = A.create_project(mk_model(), "bld_0", source="TEST",
                               actor_id="tester")
    before_blob = canon(project)
    before_hash = project["model_hash"]
    before_hist = len(project["history"])
    before_rev = project["current_revision"]
    before_revs = len(project.get("revision_models", {}) or {})

    set_marker("")
    r = runner(capacity=1)
    exc, _ = raised(lambda: r.run(TARGET_HANG, {"seconds": 600.0},
                                  timeout_s=1.0, request_id="rq_nocommit"))
    chk('the generation timed out as designed%s' % s,
        isinstance(exc, TimeoutError), '%s: %s' % (type(exc).__name__, exc))
    chk('the project is byte-identical after the abandoned generation%s' % s,
        canon(project) == before_blob, 'the project was mutated')
    chk('model_hash is unchanged%s' % s,
        project["model_hash"] == before_hash, project["model_hash"])
    chk('the history length is unchanged%s' % s,
        len(project["history"]) == before_hist,
        '%d -> %d' % (before_hist, len(project["history"])))
    chk('current_revision is unchanged — no revision was created%s' % s,
        project["current_revision"] == before_rev,
        '%r -> %r' % (before_rev, project["current_revision"]))
    chk('no revision model was stored%s' % s,
        len(project.get("revision_models", {}) or {}) == before_revs)
    chk('the runner recorded a timeout, not a result%s' % s,
        r.stats()["timed_out"] == 1 and r.stats()["succeeded"] == 0,
        str(r.stats()))


# ══════════════════════════════════════ ز) صدق منفّذ الخيوط ═══════════════
def section_thread_honesty(s):
    print('\n── ز · صدق منفّذ الخيوط: لا يدّعي إلغاءً لا يملكه%s ──' % s)
    set_marker("")
    tr = runner(capacity=2, executor="thread")
    pr = runner(capacity=2, executor="process")
    chk('health_status().cancellable is False for the thread executor%s' % s,
        tr.health_status()["cancellable"] is False,
        repr(tr.health_status()["cancellable"]))
    chk('health_status().cancellable is True for the process executor%s' % s,
        pr.health_status()["cancellable"] is True,
        repr(pr.health_status()["cancellable"]))

    t0 = time.time()
    exc, _ = raised(lambda: tr.run(TARGET_HANG, {"seconds": 3.0},
                                   timeout_s=1.0))
    elapsed = time.time() - t0
    msg = str(exc)
    chk('the thread executor still raises TimeoutError%s' % s,
        isinstance(exc, TimeoutError), '%s: %s' % (type(exc).__name__, exc))
    chk('it returns at the timeout, not at the end of the work%s' % s,
        0.8 <= elapsed < 2.5, 'elapsed=%.2fs' % elapsed)
    chk('the message says the thread executor cannot cancel the worker%s' % s,
        'thread executor cannot' in msg and 'cancel' in msg, msg[:160])
    chk('the message does not claim the worker was terminated%s' % s,
        'terminated' not in msg.lower(), msg[:160])
    chk('the thread timeout still frees the accounting slot%s' % s,
        tr.in_flight() == 0 and tr.available() == tr.capacity,
        'in_flight=%d available=%d' % (tr.in_flight(), tr.available()))


# ═════════════════════════════════════════════ ح) health_status ═══════════
def section_health(s):
    print('\n── ح · health_status: حدود معلنة بلا أسرار%s ──' % s)
    set_marker("")
    r = runner(capacity=3)
    h = r.health_status()
    required = ("executor", "capacity", "in_flight", "available", "cancellable",
                "start_method", "stats", "boundary_note")
    chk('health_status exposes every declared field%s' % s,
        all(k in h for k in required),
        str([k for k in required if k not in h]))
    chk('executor and capacity report the real configuration%s' % s,
        h["executor"] == "process" and h["capacity"] == 3, str(h))
    chk('in_flight and available are consistent with an idle runner%s' % s,
        h["in_flight"] == 0 and h["available"] == 3, str(h))
    chk('start_method is spawn — the module default%s' % s,
        h["start_method"] == "spawn" and J.START_METHOD == "spawn",
        '%r / %r' % (h["start_method"], J.START_METHOD))
    chk('stats is the full counter set%s' % s,
        set(h["stats"]) == {"submitted", "succeeded", "failed", "timed_out",
                            "rejected", "cancelled"}, str(h["stats"]))
    note = h["boundary_note"].lower()
    chk('the boundary note admits the provider request is not recalled%s' % s,
        'not recalled' in note and 'provider' in note, h["boundary_note"][:200])
    chk('the boundary note claims no provider cancellation API%s' % s,
        'no provider cancellation api is claimed' in note,
        h["boundary_note"][:200])
    chk('the boundary note still states the slot is freed%s' % s,
        'frees the server slot' in note, h["boundary_note"][:200])
    leaked = [k for k in keys_of(h, []) if SECRETISH.search(k)]
    chk('no secret-looking key is present in health_status%s' % s,
        not leaked, str(leaked))
    chk('module-level health_status() matches the runner shape%s' % s,
        set(J.health_status()) == set(h), str(set(J.health_status()) ^ set(h)))


# ═══════════════════════════════════════ ط) فحص الربط الساكن ══════════════
def section_static_wiring():
    print('\n── ط · فحص ربط ساكن: كل مسار توليد يمرّ عبر run_job ──')
    path = os.path.join(ROOT, 'acs_understand_api.py')
    with open(path, 'r', encoding='utf-8') as fh:
        src = fh.read()
    tree = ast.parse(src)

    fns = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns.setdefault(node.name, node)

    def named_calls(node, name):
        return [c for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id == name]

    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                for a in n.names}
    chk('acs_understand_api imports acs_generation_job',
        'acs_generation_job' in imported, str(sorted(imported)[:12]))
    chk('run_job is defined in acs_understand_api',
        'run_job' in fns and isinstance(fns['run_job'], ast.AsyncFunctionDef))

    total = len(named_calls(tree, 'run_job'))
    chk('run_job is called at least four times — one per generation route',
        total >= 4, 'found %d call sites' % total)

    routes = ('understand', 'edit', 'understand_image', 'understand_pdf')
    for name in routes:
        node = fns.get(name)
        chk('route handler %s() exists' % name, node is not None)
        if node is None:
            continue
        chk('route %s() calls run_job' % name,
            len(named_calls(node, 'run_job')) >= 1)
        chk('route %s() does not call the legacy run_bounded' % name,
            not named_calls(node, 'run_bounded'))

    legacy = named_calls(tree, 'run_bounded')
    chk('no call site of run_bounded remains anywhere in the API module',
        not legacy,
        'call sites at lines %s' % [c.lineno for c in legacy])
    chk('run_bounded may remain defined, but only as a dead compatibility path',
        'run_bounded' in fns)
    chk('run_job routes the runner through the shared default runner',
        '_JOBS = JOBS.default_runner()' in src)
    chk('run_job maps JobRejected and TimeoutError to distinct API errors',
        'except JOBS.JobRejected' in src and 'except TimeoutError' in src)


# ═══════════════════════════════════════════════════════════ التشغيل ══════
def main():
    TMPDIR[0] = tempfile.mkdtemp(prefix='acs_gencancel_')
    try:
        for cycle in (1, 2):
            s = '' if cycle == 1 else ' · repeat'
            if cycle == 2:
                print('\n' + '=' * 62)
                print('الدورة الثانية — تأكيد الحتمية (نفس الفحوص، مشغّلات جديدة)')
            section_happy_and_failure(s)
            section_hanging_provider(s)
            section_capacity(s)
            section_cancel_idempotent(s)
            section_no_commit(s)
            section_thread_honesty(s)
            section_health(s)
        section_static_wiring()

        print('\n── تنظيف ──')
        set_marker("")
        try:
            import psutil
            rows = [(k.pid, k.status(), ' '.join(k.cmdline()[:3]))
                    for k in psutil.Process().children(recursive=True)]
            stray = [x for x in rows if 'resource_tracker' not in x[2]]
            chk('no stray worker process survives the suite',
                not stray, str(stray))
        except ImportError:                                    # pragma: no cover
            chk('stray process sweep', False, 'psutil not importable')
        left = os.listdir(TMPDIR[0])
        chk('every marker file created by the suite was removed',
            not left, str(left))
    finally:
        os.environ.pop("ACS_JOB_TEST_MARKER", None)
        if TMPDIR[0]:
            shutil.rmtree(TMPDIR[0], ignore_errors=True)

    print('\n' + '─' * 62)
    print('GENERATION CANCEL: %d passed, %d failed' % (p[0], f[0]))
    sys.exit(1 if f[0] else 0)


if __name__ == '__main__':
    main()
