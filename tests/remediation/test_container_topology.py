#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_container_topology.py
#
# العقد: **الوظيفة التي تُقلع الصورة تُعلن الطوبولوجيا التي تختبرها —
#         والإنتاج يظلّ يرفض ضبطاً محليّ العملية غير مُقرٍّ به.**
#
# ما أوجب هذا الملفّ — بدليلٍ من الحاوية نفسها
# --------------------------------------------
# أثبتت أدواتُ التشخيص المضافة إلى الوظيفة ٩ السببَ بدل تخمينه:
#     Status     exited        ExitCode   3        OOMKilled  false
#     Cmd        sh -c "uvicorn acs_understand_api:app --host 0.0.0.0
#                        --port ${PORT:-8000}"
#     User       acs           WorkingDir /app     ExposedPorts 8000/tcp
#     [ACS-BOOT] REFUSING TO START — ACS_ENV=production with a process-local
#     rate limiter and no ACS_SINGLE_INSTANCE=1 acknowledgement.
#
# فالصورة تبني وتُقلع، والأمر صحيح، والمنفذ مكشوف، والربط على 0.0.0.0. لا شيء
# من ذلك هو العطل: **الخادم نفسه يرفض**، وهو محقّ. حدُّ معدّلٍ محليّ العملية
# في الإنتاج بلا إقرارٍ صريح يعني أن السقف اليوميّ العامّ يتضاعف بعدد النسخ
# بلا أن يعلم أحد.
#
# فالإصلاح ليس إضعاف الثابت ولا تعديل Dockerfile للالتفاف عليه، بل **إعلان
# الطوبولوجيا**: وظيفة ٩ تشغّل حاويةً واحدة بالضبط، فتقول ذلك. وهو المخرج
# الذي يسمّيه نصّ الرفض نفسه.
#
# ويثبّت هذا الملفّ الطرفين معاً: أن CI يعلن، وأن الإنتاج ما زال يرفض.
# يعمل بلا Docker وبلا شبكة: يقرأ سير العمل، ويستدعي الثابت مباشرةً بضبطٍ
# مُمرَّر — لا يلمس بيئة العملية.
# ==============================================================================
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import acs_rate_limit as RL                                       # noqa: E402

CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")

_p = _f = 0


def chk(name, cond, detail=""):
    global _p, _f
    if cond:
        _p += 1
        print("  ✓", name)
    else:
        _f += 1
        print("  ✗", name, ("\n      " + str(detail)) if detail else "")


def rd(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


CI_SRC = rd(CI)
def _run_step(src):
    """نصّ أمر `docker run` كاملاً، بأسطر المتابعة التي تنتهي بشرطة مائلة."""
    at = src.find("docker run ")
    if at < 0:
        return ""
    out = []
    for line in src[at:].splitlines():
        out.append(line)
        if not line.rstrip().endswith("\\"):
            break
    return "\n".join(out)


RUN_STEP = _run_step(CI_SRC)


def main():
    print("== أ · الوظيفة ٩ تشغّل حاويةً واحدة بالضبط ==")
    runs = re.findall(r"^\s*docker run\b", CI_SRC, re.M)
    chk("exactly one `docker run` in the workflow", len(runs) == 1, str(len(runs)))
    chk("it names a single container", RUN_STEP.count("--name") == 1, RUN_STEP[:200])
    chk("it publishes a single port", RUN_STEP.count("-p ") == 1)
    chk("it does not ask for replicas or scale",
        "--scale" not in CI_SRC and "replicas" not in CI_SRC)

    print("\n== ب · وتُعلن تلك الطوبولوجيا صراحةً للخادم ==")
    chk("the run declares ACS_ENV=production — the invariant is exercised, "
        "not side-stepped by testing a non-production config",
        "-e ACS_ENV=production" in RUN_STEP, RUN_STEP[:300])
    chk("it declares ACS_SINGLE_INSTANCE=1",
        "-e ACS_SINGLE_INSTANCE=1" in RUN_STEP)
    chk("it declares the concurrency it actually runs",
        re.search(r"-e\s+WEB_CONCURRENCY=1\b", RUN_STEP) is not None,
        RUN_STEP[:300])
    # اسمُ المتغيّر ليس تفصيلاً: اسمٌ غير مُدرَج يمرّ صامتاً بلا أثر، فيبدو
    # الإقرار مضبوطاً وهو لا يُقرأ أصلاً.
    chk("and that name is one the invariant actually reads "
        "(acs_rate_limit.CONCURRENCY_VARS)",
        "WEB_CONCURRENCY" in RL.CONCURRENCY_VARS, str(RL.CONCURRENCY_VARS))
    chk("no ACS_-prefixed misspelling of it is passed instead",
        "ACS_WEB_CONCURRENCY" not in RUN_STEP)

    print("\n== ج · الثابت يقبل ما تعلنه الوظيفة ==")
    RL.reset_default_limiter()
    ci_env = {"ACS_ENV": "production", "ACS_SINGLE_INSTANCE": "1",
              "WEB_CONCURRENCY": "1"}
    inv = RL.production_invariant(env=ci_env)
    chk("the exact environment the CI container is given boots",
        inv["ok"] is True, str(inv.get("state")))
    chk("and it is recorded as a DECLARED single instance, not as a "
        "distributed backend it does not have",
        inv["state"] == RL.INVARIANT_SINGLE and inv["distributed"] is False,
        "%s / distributed=%s" % (inv["state"], inv["distributed"]))
    chk("the declaration is visible in the verdict, so a reader can tell "
        "which topology was asserted",
        inv["single_instance_declared"] is True
        and inv["declared_concurrency"] == 1,
        str({k: inv.get(k) for k in ("single_instance_declared",
                                     "declared_concurrency")}))

    print("\n== د · شاهد سالب: الإنتاج ما زال يرفض ما يجب أن يرفضه ==")
    RL.reset_default_limiter()
    bare = RL.production_invariant(env={"ACS_ENV": "production"})
    chk("production with a process-local limiter and NO acknowledgement still "
        "refuses to boot", bare["ok"] is False, str(bare.get("state")))
    chk("and it refuses under the declared name UNDECLARED_SINGLE_INSTANCE",
        bare["state"] == RL.INVARIANT_UNDECLARED, str(bare["state"]))
    chk("its message names both escape routes and neither is 'ignore it'",
        "ACS_RATE_LIMIT_BACKEND=redis" in str(bare.get("detail"))
        and "ACS_SINGLE_INSTANCE=1" in str(bare.get("detail")),
        str(bare.get("detail"))[:200])

    RL.reset_default_limiter()
    lying = RL.production_invariant(env={"ACS_ENV": "production",
                                         "ACS_SINGLE_INSTANCE": "1",
                                         "WEB_CONCURRENCY": "4"})
    chk("a declaration the platform contradicts (single instance claimed, "
        "4 workers asked for) is REFUSED — the acknowledgement is not a "
        "blanket opt-out", lying["ok"] is False, str(lying.get("state")))
    chk("and it refuses as SINGLE_INSTANCE_INVARIANT_VIOLATED",
        lying["state"] == RL.INVARIANT_VIOLATED, str(lying["state"]))

    RL.reset_default_limiter()
    dist = RL.production_invariant(env={"ACS_ENV": "production",
                                        "WEB_CONCURRENCY": "4"},
                                   limiter=_FakeDistributed())
    chk("a genuinely distributed backend needs no acknowledgement at any scale",
        dist["ok"] is True and dist["distributed"] is True,
        str({k: dist.get(k) for k in ("ok", "state", "distributed")}))

    print("\n== هـ · الثابت نفسه لم يُلمَس، ولا الـDockerfile ==")
    src = rd(os.path.join(ROOT, "acs_rate_limit.py"))
    chk("production_invariant still raises through a dedicated error type",
        "class ProductionInvariantError" in src)
    api = rd(os.path.join(ROOT, "acs_understand_api.py"))
    chk("the API still refuses to start on a failed invariant — the check was "
        "not downgraded to a warning",
        "raise RL.ProductionInvariantError" in api)
    chk("and it still prints the boot verdict either way",
        "[ACS-BOOT] rate-limit invariant:" in api)
    docker = rd(os.path.join(ROOT, "Dockerfile"))
    chk("the Dockerfile hard-codes NO single-instance acknowledgement — the "
        "declaration belongs to whoever runs the image, not to the image",
        "ACS_SINGLE_INSTANCE" not in docker)
    # الصورة **تُثبِّت** ACS_ENV=production عمداً (F-25): بلا ذلك تبقى القيمة
    # "development" في الإنتاج فتنطفئ حراسات كثيرة بصمت. فوجودها هنا هو ما
    # يجعل الوظيفة ٩ تختبر الثابت حقاً بدل أن تتفاداه بضبطٍ غير إنتاجيّ.
    chk("the image DOES pin ACS_ENV=production (F-25) — which is precisely why "
        "job 9 exercises the invariant rather than dodging it",
        re.search(r"^\s*ENV\s+ACS_ENV=production", docker, re.M) is not None)

    print("\n== و · بوّابة الصحّة ما زالت بوّابة ==")
    step = CI_SRC[CI_SRC.find("The image boots and answers /health"):]
    step = step[:step.find("- uses:")] if "- uses:" in step else step
    chk("the health probe still runs against the started container",
        "curl -fsS http://127.0.0.1:8000/health" in step)
    chk("and a container that never answers still fails the job",
        'if [ "$healthy" -ne 1 ]; then' in step and "exit 1" in step)
    chk("no `|| true` and no `continue-on-error` guards that gate",
        "|| true" not in step and "continue-on-error" not in step)

    print("\n" + "─" * 62)
    print("CONTAINER TOPOLOGY: %d passed, %d failed" % (_p, _f))
    return 1 if _f else 0


class _FakeDistributed(object):
    """محدّدٌ بواجهةٍ خلفية موزّعة — لقياس الفرع الآخر بلا Redis حيّ."""

    class _Backend(object):
        distributed = True

    backend = _Backend()
    limits = {"gen_hour": 8, "gen_day": 25, "edit_hour": 30, "global_day": 400}


if __name__ == "__main__":
    sys.exit(main())
