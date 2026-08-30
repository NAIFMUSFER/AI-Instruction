#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_job_boundary.py
#
# العقد: **هويّة الخطأ المصنَّف تعبر حدّ العملية سليمة — والمجهول يبقى مجهولاً.**
#
# ما أوجب هذا الملفّ
# ------------------
# أبلغ CI/1 ثلاثة أعطال في tests/phase9_2/test_backend_contract.py:
#     متوقَّع 504 + ACS_TIMEOUT             · واقع 502 + ACS_UPSTREAM_UNKNOWN
#     متوقَّع ACS_UPSTREAM_AUTH             · واقع ACS_UPSTREAM_UNKNOWN / JobError
#     متوقَّع ACS_UPSTREAM_TRAILING_JSON    · واقع ACS_UPSTREAM_UNKNOWN
#
# والتفسير الأوّل المطروح كان أن حدّ العملية يفقد التصنيف. **قِيس، فلم يكن
# كذلك**: حدّ العملية ينقل AcsApiError سليماً برمزه وقابليّة إعادته ومغلّف
# upstream — وهو ما يقيسه هذا الملفّ بتشغيلٍ حقيقيّ لا بمحاكاة.
#
# السبب الحقيقيّ: العامل عمليةٌ أخرى تستورد وحدة الهدف باسمها، فترقيعُ
# `acs_understand.understand` في عملية الاختبار لا يبلغه. كان الاختبار يُدخِل
# عطلاً لا يراه الخادم، فيصل المستخدمَ عطلُ الأصل بدله — وهو RuntimeError غير
# مصنَّف، أي ACS_UPSTREAM_UNKNOWN. الرمز كان صادقاً؛ التجربة هي التي لم تقع.
#
# لذلك يُوجَّه الهدف هنا إلى tests/remediation/lib_job_faults.py: دوالّ حقيقية
# على مستوى وحدة، تُستورَد في العامل كما يُستورَد الأصل، فيقع العطل حيث يقع
# في الإنتاج.
#
# يعمل بلا fastapi: يقيس الحدّ نفسه (acs_generation_job) لا طبقة HTTP فوقه.
# ==============================================================================
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import acs_api_errors as E                                        # noqa: E402
import acs_generation_job as JOBS                                 # noqa: E402

_p = _f = 0


def chk(name, cond, detail=""):
    global _p, _f
    if cond:
        _p += 1
        print("  ✓", name)
    else:
        _f += 1
        print("  ✗", name, ("\n      " + str(detail)) if detail else "")


FAULTS = "lib_job_faults:"


def run(target, kwargs=None, timeout_s=None):
    """يشغّل هدفاً عبر الحدّ الحقيقيّ ويعيد الاستثناء كما وصل الأب."""
    runner = JOBS.default_runner()
    try:
        value = runner.run(FAULTS + target, kwargs or {}, timeout_s=timeout_s)
        return None, value
    except BaseException as exc:                                  # noqa: BLE001
        return exc, None


def main():
    """كل القياس داخل main.

    المنفِّذ يبدأ العملية بـspawn، والابنة تستورد وحدة الهدف — ومعها هذه
    الوحدة إن كانت هي نقطة الدخول. فلو جرى القياس على مستوى الوحدة لأعادت كل
    ابنةٍ تشغيله فتلد ابنةً أخرى:
        RuntimeError: An attempt has been made to start a new process before
        the current process has finished its bootstrapping phase.
    الحارس `if __name__ == "__main__"` هو ما يفصل «تُستورَد» عن «تُشغَّل».
    """
    print("== أ · المنفِّذ تحت الاختبار هو منفِّذ الإنتاج، لا بديلٌ أسهل ==")
    # لو كان الخيطُ هو المنفِّذ لَما كان هناك حدُّ عملية أصلاً، ولمرّ كل ما تحته
    # بلا معنى. يُثبَت أوّلاً أن ما يُقاس هو ما يعمل في الإنتاج.
    chk("the default executor is the process executor",
        JOBS.EXECUTOR == JOBS.EXECUTOR_PROCESS, JOBS.EXECUTOR)
    chk("the worker is started with a method that does NOT inherit the parent's "
        "patched module objects — which is exactly why an in-process monkeypatch "
        "cannot reach it", JOBS.START_METHOD in ("spawn", "forkserver"),
        JOBS.START_METHOD)
    health = JOBS.health_status()
    chk("health reports the process executor and a real capacity",
        health.get("executor") == "process" and health.get("capacity", 0) >= 1,
        str({k: health.get(k) for k in ("executor", "capacity", "cancellable")}))

    print("\n== ب · ACS_UPSTREAM_AUTH يعبر الحدّ بهويّته كاملة ==")
    exc, _ = run("upstream_auth")
    chk("an upstream auth failure raised INSIDE the worker arrives as AcsApiError, "
        "not as JobError", isinstance(exc, E.AcsApiError),
        "%s: %s" % (type(exc).__name__, str(exc)[:120]))
    if isinstance(exc, E.AcsApiError):
        chk("its code is ACS_UPSTREAM_AUTH", exc.code == E.ACS_UPSTREAM_AUTH, exc.code)
        chk("retryable survives the boundary as False", exc.retryable is False,
            str(exc.retryable))
        chk("the upstream envelope survives and names the provider",
            isinstance(exc.upstream, dict)
            and exc.upstream.get("provider") == "anthropic", str(exc.upstream))
        chk("and it maps to a real HTTP status", exc.code in E.HTTP_STATUS,
            str(E.HTTP_STATUS.get(exc.code)))

    print("\n== ج · ACS_UPSTREAM_TRAILING_JSON يعبر الحدّ ==")
    exc, _ = run("upstream_trailing_json")
    chk("the two-object reply arrives as AcsApiError", isinstance(exc, E.AcsApiError),
        "%s: %s" % (type(exc).__name__, str(exc)[:120]))
    if isinstance(exc, E.AcsApiError):
        chk("its code is ACS_UPSTREAM_TRAILING_JSON",
            exc.code == E.ACS_UPSTREAM_TRAILING_JSON, exc.code)
        chk("the raw decoder text 'Extra data' never reaches the caller",
            "Extra data" not in str(exc.message or ""), str(exc.message)[:120])

    print("\n== د · التوقّف يصير TimeoutError عند الحدّ، و504 عند الـAPI ==")
    t0 = time.time()
    exc, _ = run("stall", {"seconds": 20.0}, timeout_s=0.6)
    elapsed = time.time() - t0
    chk("a worker that stalls raises TimeoutError at the boundary",
        isinstance(exc, TimeoutError),
        "%s: %s" % (type(exc).__name__, str(exc)[:120]))
    chk("and it returns in about the declared limit, not after the stall "
        "(%.2fs for a 20s stall at a 0.6s limit)" % elapsed, elapsed < 10.0,
        "%.2fs" % elapsed)
    chk("TimeoutError is NOT downgraded to JobError — it is an OSError subclass, "
        "which a broad `except (EOFError, OSError)` would have swallowed",
        not isinstance(exc, JOBS.JobError))
    chk("the API maps that timeout to ACS_TIMEOUT",
        E.ACS_TIMEOUT in E.HTTP_STATUS)
    chk("and ACS_TIMEOUT is HTTP 504, not 502",
        E.HTTP_STATUS[E.ACS_TIMEOUT] == 504, str(E.HTTP_STATUS[E.ACS_TIMEOUT]))

    print("\n== هـ · المجهول يبقى مجهولاً — لا ترقية ولا تصنيف مُختلَق ==")
    exc, _ = run("unknown_failure")
    chk("a genuinely unclassified RuntimeError does NOT arrive as AcsApiError",
        not isinstance(exc, E.AcsApiError),
        "%s: %s" % (type(exc).__name__, str(exc)[:120]))
    chk("it arrives as JobError, carrying the original class name",
        isinstance(exc, JOBS.JobError)
        and getattr(exc, "error_class", None) == "RuntimeError",
        "%s / %s" % (type(exc).__name__, getattr(exc, "error_class", None)))
    classified = E.classify_upstream(exc)
    chk("and the API classifies it ACS_UPSTREAM_UNKNOWN — the fallback is intact",
        classified.code == E.ACS_UPSTREAM_UNKNOWN, classified.code)

    print("\n== و · شاهد سالب: الحدّ لا يقبل رمزاً مُختلَقاً من الابنة ==")
    # الأب يعيد بناء الخطأ من حمولة تصل عبر أنبوب. لو قبل أي نصّ رمزاً، لاستطاعت
    # ابنةٌ مُخترَقة أن تنتحل أي تصنيف. القبول مقصورٌ على القائمة المعلنة.
    before = dict(E.HTTP_STATUS)
    raised = []
    try:
        JOBS._reraise_classified({"acs_code": "ACS_TOTALLY_MADE_UP",
                                  "message": "x", "retryable": True})
    except BaseException as exc:                                      # noqa: BLE001
        raised.append(exc)
    chk("an unknown code in the wire payload is refused, not resurrected",
        not raised, str(raised[:1]))
    try:
        JOBS._reraise_classified({"acs_code": E.ACS_UPSTREAM_AUTH, "message": "y",
                                  "retryable": False})
    except E.AcsApiError as exc:
        raised.append(exc)
    chk("but a declared code IS rebuilt — the guard is a whitelist, not a wall",
        any(isinstance(x, E.AcsApiError) and x.code == E.ACS_UPSTREAM_AUTH
            for x in raised))
    chk("the error table itself was not mutated by any of this",
        E.HTTP_STATUS == before)

    print("\n== ح · موتُ العامل بلا إرسال: يُبلَّغ برمز خروجه، ويبقى مجهولاً ==")
    # هذه هي الحالة التي أنتجت EOFError في CI. لم تكن عطلاً في نقل التصنيف —
    # كانت الابنة تموت قبل الإرسال أصلاً، لأن spawn يعيد تنفيذ ملفّ نقطة
    # الدخول، وملفّ الاختبار لم يكن محروساً بـ__main__ فأعاد بناء TestClient
    # في كل عامل. رمزُ الخروج هو ما يفصل «مات» عن «فقد التصنيف».
    exc, _ = run("die_without_sending")
    chk("a worker that exits without sending is reported, not swallowed",
        isinstance(exc, JOBS.JobError),
        "%s: %s" % (type(exc).__name__, str(exc)[:120]))
    chk("the parent names the pipe symptom (EOFError) as the error class",
        getattr(exc, "error_class", None) == "EOFError",
        str(getattr(exc, "error_class", None)))
    chk("and it carries the CHILD'S EXIT CODE, so a dead worker is "
        "distinguishable from a lost classification",
        "child exit code: 7" in str(exc), str(exc)[:160])
    chk("a dead worker is NOT promoted to a typed upstream code",
        not isinstance(exc, E.AcsApiError))
    chk("it classifies as ACS_UPSTREAM_UNKNOWN, like any unknown failure",
        E.classify_upstream(exc).code == E.ACS_UPSTREAM_UNKNOWN,
        E.classify_upstream(exc).code)

    print("\n== ط · كل ملفّ يبلغ مُشغِّل الوظائف محروسٌ بـ__main__ ==")
    # بلا الحارس تعيد كل ابنةٍ تنفيذ الملفّ كاملاً. وأسوأ ما في ذلك أنه لا
    # يظهر فشلاً نظيفاً: توكيدُ المهلة كان **يمرّ لسببٍ خاطئ** — الأب ينتظر
    # مهلته ويعلن TIMED_OUT مهما فعلت الابنة، والابنة ميّتة أصلاً.
    import re as _re
    tests_root = os.path.join(ROOT, "tests")
    reach, unguarded = [], []
    for dirpath, dirnames, files in os.walk(tests_root):
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            if "acs_generation_job" not in src and "default_runner" not in src:
                continue
            rel = os.path.relpath(path, ROOT)
            reach.append(rel)
            if not _re.search(r'^if __name__ ?== ?[\'"]__main__[\'"]', src, _re.M):
                unguarded.append(rel)
    chk("there are files that reach the job runner (%d)" % len(reach),
        len(reach) >= 3, str(reach))
    chk("EVERY one of them guards __main__ — spawn re-executes the entry file, "
        "so an unguarded suite re-runs itself inside every worker",
        not unguarded, str(unguarded))

    print("\n== ز · لا تسريب: لا مفتاح ولا أثر استدعاء يعبر الحدّ إلى العميل ==")
    exc, _ = run("leaky_failure")
    text = "%s %s %s" % (type(exc).__name__, exc, getattr(exc, "error_class", ""))
    chk("the worker's message reaches the parent (the failure is not silent)",
        "boom" in text, text[:120])
    chk("no credential-shaped value survives into the parent's exception",
        "sk-ant" not in text, text[:200])
    chk("no source-file traceback frame survives",
        ".py\", line" not in text and "Traceback" not in text, text[:200])
    envelope = E.classify_upstream(exc).envelope("req_probe")
    flat = str(envelope)
    chk("nor into the client envelope", "sk-ant" not in flat and "Traceback" not in flat,
        flat[:200])
    chk("and the envelope still carries exactly the five declared fields",
        set(envelope.get("error", {})) == {"code", "message", "request_id",
                                           "retryable", "upstream"},
        str(sorted(envelope.get("error", {}))))


    print("\n" + "─" * 62)
    print("JOB BOUNDARY: %d passed, %d failed" % (_p, _f))
    return 1 if _f else 0


if __name__ == "__main__":
    sys.exit(main())
