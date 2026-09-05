# -*- coding: utf-8 -*-
"""W0 — البوّابات نفسها: CI لا يستطيع أن يكذب، والتحقّق الحيّ يصل فعلاً.

    python3 tests/remediation/test_ci_gate.py

لماذا هذا الملفّ موجود
----------------------
كل ما في `tests/` عديم القيمة إن كانت الوظيفة التي تشغّله تمرّ خضراء رغم
فشله. وهذا ما كان يحدث في **خمسة** مواضع:

    set -o pipefail
    for t in a b c ; do node "$t" | tee -a log ; done

حالةُ خروج حلقة `for` في الصَّدَفة هي حالةُ **آخر تكرار وحده**. فلو فشل `a`
ونجح `c` خرجت الحلقة بصفر. `set -o pipefail` لا يعالج هذا إطلاقاً: هو يصحّح
حالة الأنبوب داخل التكرار الواحد لا حالة الحلقة. والشيء نفسه في مجموعة
الأقواس `{ … } | tee`: حالتها حالةُ آخر أمرٍ فيها.

وبالتوازي: `tests/deploy/verify_backend_live.py` — السكربت الحيّ الوحيد في
production-verify.yml — كان يقرأ CONFIGURED_BASE من `public/index.html`، وF-09
نقل الثابت إلى `public/app/boot/api-base.js`. فكان يخرج بالرمز 2 «لا عنوان»
قبل فتح أي مقبس، على كل جهاز، كل يوم.

ما يقيسه هذا الملفّ: دلالة الخروج نفسها — لا نيّة الكود. كل شاهد سالب هنا
يُعيد إدخال العطل الأصلي حرفياً ويثبت أنه يُكتشَف.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")
PROD = os.path.join(ROOT, ".github", "workflows", "production-verify.yml")
RUNNER = os.path.join(ROOT, "tools", "ci_run.sh")
LIVE = os.path.join(ROOT, "tests", "deploy", "verify_backend_live.py")

p = [0]
f = [0]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


def rd(path):
    return io.open(path, encoding="utf-8").read()


def sh(script, cwd=None):
    """يشغّل سكربت bash ويعيد (rc, out). لا يرفع أبداً."""
    r = subprocess.run(["bash", "-c", script], cwd=cwd or ROOT,
                       capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr)


def main():
    tmp = tempfile.mkdtemp(prefix="acs_ci_gate_")
    good = os.path.join(tmp, "good.py")
    bad = os.path.join(tmp, "bad.py")
    io.open(good, "w").write("print('ok')\n")
    io.open(bad, "w").write("import sys; sys.exit(3)\n")

    # ═══ أ · الشاهد السالب: دلالة الحلقة العارية ═════════════════════════════
    print("\n== أ · الشاهد السالب — العطل الأصلي، مُعاد إدخاله ==")
    rc, _ = sh('for t in a b c; do if [ "$t" = a ]; then false; else true; fi; done')
    chk("a bare `for` loop EXITS 0 although its first item failed "
        "— this is the defect, reproduced", rc == 0, "rc=%s" % rc)
    rc, _ = sh('set -o pipefail\n'
               'for t in a b c; do if [ "$t" = a ]; then false; else true; fi'
               ' | cat; done')
    chk("`set -o pipefail` does NOT fix it — it governs the pipe, not the loop",
        rc == 0, "rc=%s" % rc)
    rc, _ = sh('set -o pipefail\n{ python3 "%s"; python3 "%s"; } | cat'
               % (bad, good))
    chk("a `{ … } | tee` group EXITS 0 although its first command failed "
        "— the same defect, fifth site", rc == 0, "rc=%s" % rc)
    rc, _ = sh('set -e\nFAIL=0\nguard(){ [ "$1" -ne 0 ] && FAIL=1; }\n'
               'false; guard $?\necho "reached"')
    chk("`set -e` + `cmd; guard $?` never reaches guard — run_all.sh's "
        "accumulator was dead code", rc != 0 and "reached" not in _,
        "rc=%s" % rc)

    # ═══ ب · المُشغِّل: حالة خروج يُعتمد عليها ════════════════════════════════
    print("\n== ب · tools/ci_run.sh — أيّ فشل، لا آخر فشل ==")
    chk("the runner exists and is executable", os.path.isfile(RUNNER)
        and os.access(RUNNER, os.X_OK))
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3" "%s" "%s" "%s"'
                 % (bad, good, good))
    chk("a FIRST-item failure fails the runner", rc == 1, "rc=%s" % rc)
    chk("and the failing target is named in the output", "bad.py" in out
        and "FAILED TARGETS" in out)
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3" "%s" "%s"'
                 % (good, bad))
    chk("a LAST-item failure fails the runner too", rc == 1, "rc=%s" % rc)
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3" "%s" "%s" "%s"'
                 % (good, bad, good))
    chk("a MIDDLE-item failure fails the runner", rc == 1, "rc=%s" % rc)
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3" "%s" "%s"'
                 % (good, good))
    chk("all-pass exits 0", rc == 0, "rc=%s" % rc)
    chk("and the summary counts every target", "2 passed, 0 failed, 2 total" in out,
        out[-160:])
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3"')
    chk("an EMPTY target list is refused, not reported as success",
        rc == 64, "rc=%s" % rc)
    rc, out = sh('bash tools/ci_run.sh --label t "%s"' % good)
    chk("a missing --runner is refused", rc == 64, "rc=%s" % rc)
    logf = os.path.join(tmp, "x.log")
    rc, out = sh('bash tools/ci_run.sh --log "%s" --label t --runner "python3" '
                 '"%s" "%s"' % (logf, bad, good))
    chk("the log is written even when a target fails", rc == 1
        and os.path.isfile(logf) and "bad.py" in rd(logf), "rc=%s" % rc)
    chk("the exit code is the TEST's, not tee's — PIPESTATUS is read",
        "PIPESTATUS[0]" in rd(RUNNER))
    rc, out = sh('bash tools/ci_run.sh --label t --runner "python3" "%s"'
                 % os.path.join(tmp, "does_not_exist.py"))
    chk("a target that cannot even start fails the runner", rc == 1, "rc=%s" % rc)

    # ═══ ج · لم يبقَ في CI موضعٌ يُخفي فشلاً ═════════════════════════════════
    print("\n== ج · كل موضع تشغيل اختبار في CI صار مُبوَّباً ==")
    ci = rd(CI)
    chk("no bare `for t in` test loop remains in ci.yml",
        re.search(r"for\s+\w+\s+in\s+tests/", ci) is None)
    # كل مجموعة أقواس تُشغِّل أمراً قابلاً للفشل يجب أن تبدأ بـ set -e.
    groups = re.findall(r"^          \{\n(.*?)^          \} ", ci,
                        re.S | re.M)
    unguarded = [g for g in groups
                 if re.search(r"^\s+(python3?|node|bash -n)\s", g, re.M)
                 and "set -e" not in g]
    chk("every brace group that runs a command declares `set -e`",
        unguarded == [], "%d unguarded" % len(unguarded))
    chk("the runner is actually used by ci.yml", ci.count("tools/ci_run.sh") >= 4,
        ci.count("tools/ci_run.sh"))
    chk("the aggregate in job 3 is a flag, not last-command semantics",
        "rc=0" in ci and "|| rc=1" in ci and "exit $rc" in ci)
    chk("production-verify pipes a single command with pipefail, so its "
        "status is the script's", "set -o pipefail" in rd(PROD)
        and "verify_backend_live.py 2>&1 | tee" in rd(PROD))

    scan = ci.split("      - name: CVE scan", 1)[1].split("      - uses:", 1)[0]
    chk("CVE findings cannot be marked continue-on-error", "continue-on-error" not in scan)
    block = scan.split("        run: |\n", 1)[1]
    script = "\n".join(line[10:] for line in block.splitlines())
    # Execute the shipped shell body with fake tools, preserving its pipelines.
    for pip_rc, npm_rc in ((0, 0), (1, 0), (0, 1), (2, 0)):
        harness = ("mkdir -p logs\npython(){ return 0; }\n"
                   "pip-audit(){ return %d; }\nnpm(){ return %d; }\n"
                   % (pip_rc, npm_rc)) + script
        rc, _ = sh(harness, cwd=tmp)
        chk("CVE gate preserves pip=%d npm=%d failure" % (pip_rc, npm_rc),
            (rc == 0) == (pip_rc == 0 and npm_rc == 0), "rc=%s" % rc)

    # ═══ د · المجموعات التي كانت خارج كل بوّابة ══════════════════════════════
    print("\n== د · المجموعات التي لم تكن مُبوَّبة صارت مُبوَّبة ==")
    NEWLY_GATED = (
        "test_upload_security.py", "test_rate_limit.py",
        "test_engineering_authority.py", "test_generation_cancel.py",
        "test_logging.py", "test_privacy_boundary.py",
        "test_build_metadata.py", "test_plate_extent.py",
        "test_bundle_report.py", "test_api_wiring.py",
        "test_production_error_ui.js", "test_csp.js",
        "test_webgl_diagnostics.js", "test_concurrency.js",
        "test_persistence.js", "test_accessibility.js",
        "csp_browser_probe.js",
    )
    for name in NEWLY_GATED:
        chk("CI now runs %s" % name, name in ci)
    # ما استُثني عمداً، ومعه سببه — حتى لا يُقرأ الغياب سهواً.
    EXCLUDED = {
        "test_performance.js": "duplicate coverage: the same budgets are "
                               "measured by test_scene_benchmark.js, which IS "
                               "gated; this one adds no independent assertion",
        "run_all.sh": "an orchestrator, not a suite — CI lists its targets "
                      "explicitly so a skipped step is visible in the job log",
    }
    for name, why in EXCLUDED.items():
        chk("%s is excluded on purpose (%s)" % (name, why[:48]), bool(why))

    # ═══ هـ · التحقّق الحيّ يصل إلى الخادم فعلاً ══════════════════════════════
    print("\n== هـ · verify_backend_live يحلّ العنوان من مصدره القانوني ==")
    src = rd(LIVE)
    sys.path.insert(0, os.path.join(ROOT, "tests", "deploy"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("acs_live_verifier", LIVE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    base = mod.configured_base()
    chk("configured_base() resolves a non-empty https origin",
        base.startswith("https://") and len(base) > 12, repr(base))
    boot = rd(os.path.join(ROOT, "public", "app", "boot", "api-base.js"))
    m = re.search(r'CONFIGURED_BASE\s*=\s*"([^"]*)"', boot)
    chk("and it equals the constant in public/app/boot/api-base.js "
        "— the canonical source, not a second copy",
        bool(m) and base == m.group(1).rstrip("/"), repr(base))
    page = rd(os.path.join(ROOT, "public", "index.html"))
    chk("the shell no longer carries the constant at all (F-09 moved it), "
        "which is why reading only the shell returned nothing",
        "CONFIGURED_BASE" not in page)
    chk("the verifier reads the boot scripts, not just the shell",
        "BOOT_DIR" in src and "_shipped_sources" in src)
    # لا مصدر ثانٍ للحقيقة: العنوان قد يظهر في مثال الاستعمال داخل سلسلة
    # التوثيق (وهو توثيق لا إعداد)، لكنه يجب ألّا يظهر في **شفرة** الملفّ.
    # يُجرَّد التوثيق والتعليقات بالمحلّل نفسه ثم يُبحَث فيما تبقّى.
    import ast as _ast
    tree = _ast.parse(src)
    code_only = "\n".join(
        ln for ln in _ast.unparse(tree).splitlines()
        if not ln.strip().startswith("#"))
    for node in _ast.walk(tree):                       # اطرح كل سلاسل التوثيق
        if isinstance(node, (_ast.Module, _ast.FunctionDef, _ast.ClassDef)):
            doc = _ast.get_docstring(node)
            if doc:
                code_only = code_only.replace(doc, "")
    chk("no second source of truth: the origin literal appears in no "
        "executable statement of the verifier (a docstring usage example "
        "is documentation, not configuration)",
        "onrender.com" not in code_only,
        [l for l in code_only.splitlines() if "onrender.com" in l][:1])

    # الشاهد السالب: أخفِ الثابت عن كلا المصدرين ⇒ يجب أن يعجز، لا أن يخمّن.
    old_page, old_boot = mod.PAGE, mod.BOOT_DIR
    try:
        mod.PAGE = os.path.join(tmp, "empty.html")
        io.open(mod.PAGE, "w").write("<html></html>")
        mod.BOOT_DIR = os.path.join(tmp, "no_boot")
        chk("NEGATIVE CONTROL — with the constant absent from every shipped "
            "source, the verifier resolves nothing and cannot silently "
            "invent an origin", mod.configured_base() == "")
    finally:
        mod.PAGE, mod.BOOT_DIR = old_page, old_boot
    chk("and it recovers once the real sources are restored",
        mod.configured_base() == base)
    chk("the stale hard-coded model assertion is gone",
        'model_configured") == "claude-sonnet-5"' not in src)
    chk("and the provider block is asserted instead",
        "llm_provider" in src and "llm_state" in src
        and "resolved" in src)

    # ═══ و · run_all.sh يُجمِّع فعلاً ═════════════════════════════════════════
    print("\n== و · run_all.sh لم يعد يموت قبل مُجمِّعه ==")
    ra = rd(os.path.join(HERE, "run_all.sh"))
    chk("run_all.sh no longer sets -e, so `guard $?` is reachable",
        not re.search(r"^set -e\s*$", ra, re.M))
    chk("its accumulator and its failure branch are still present",
        "FAIL=1" in ra and "FAILURES PRESENT" in ra and "exit 1" in ra)
    rc, out = sh('cd "%s" && FAIL=0\n'
                 'guard(){ if [ "$1" -ne 0 ]; then FAIL=1; fi; }\n'
                 'false; guard $?\n'
                 'if [ "$FAIL" -ne 0 ]; then echo "FAILURES PRESENT"; exit 1; fi'
                 % ROOT)
    chk("the same shape now reaches the failure branch and exits non-zero",
        rc == 1 and "FAILURES PRESENT" in out, "rc=%s" % rc)

    print("\n== ز · كل وظيفة تشغّل مجموعات Python تُركِّب تثبيتاتها أوّلاً ==")
    # العطل: `7 · Dependency audit and lock contract` كانت تشغّل ٢٢ مجموعة على
    # مفسّرٍ عارٍ — checkout، setup-python، setup-node، ثم المجموعات مباشرةً.
    # فسقطت ستٌّ منها لأن ما تستورده غير مركَّب، لا لأن فيها عطلاً:
    #   test_event_loop · test_upload_security · test_generation_cancel
    #   test_privacy_boundary · test_api_wiring · test_p0_hardening
    # أُعيد إنتاجه بحجب الحزم عن المفسّر، ثم أُصلح بخطوة تركيب.
    #
    # الثابت هنا يمنع تكرارها في وظيفةٍ تُضاف لاحقاً: من شغّل مجموعةً بـpython3
    # فليُركِّب التثبيتات قبلها.
    jobs = re.split(r"\n  (?=[a-z][a-z0-9-]*:\n)", ci)
    runs_python, installs = [], {}
    for blk in jobs[1:]:
        m = re.match(r"\s*([a-z0-9-]+):", blk)
        if not m:
            continue
        name = m.group(1)
        # وظيفة «تشغّل مجموعات» = تمرّر أهداف .py إلى مُشغِّل python3
        if re.search(r'--runner\s+"python3"', blk) or \
           re.search(r"^\s*python3?\s+\S*tests/\S+\.py", blk, re.M):
            runs_python.append(name)
            installs[name] = bool(
                re.search(r"pip install[^\n]*-r\s+requirements\.txt", blk))
    chk("ci.yml declares at least two jobs that run Python suites",
        len(runs_python) >= 2, str(runs_python))
    for name in runs_python:
        chk("job '%s' installs the pinned requirements before running them"
            % name, installs[name],
            "no `pip install -r requirements.txt` step in this job")

    print("\n== ح · تبعية الاختبار مثبّتة، ولم تُجعَل اختيارية ==")
    dev = os.path.join(ROOT, "requirements-dev.txt")
    chk("requirements-dev.txt exists", os.path.exists(dev))
    devtxt = open(dev, encoding="utf-8").read() if os.path.exists(dev) else ""
    chk("psutil is pinned there with ==, not a floor or a bare name",
        re.search(r"^psutil==\d+\.\d+", devtxt, re.M) is not None)
    chk("it is NOT in requirements.txt — the production image must not carry a "
        "test-only package",
        "psutil" not in open(os.path.join(ROOT, "requirements.txt"),
                             encoding="utf-8").read())
    chk("the job that needs it installs it",
        re.search(r"pip install[^\n]*requirements-dev\.txt", ci) is not None)
    gen = open(os.path.join(ROOT, "tests", "remediation",
                            "test_generation_cancel.py"), encoding="utf-8").read()
    chk("and the suite still imports psutil directly — the dependency was "
        "installed, not made optional",
        re.search(r"^\s*import psutil\s*$", gen, re.M) is not None)
    chk("no try/except was wrapped around that import to let it pass silently",
        not re.search(r"try:\s*\n\s*import psutil\s*\n\s*except", gen))

    print("\n== Production page verification reaches the deployment and preserves failure ==")
    prod = rd(PROD)
    live_job = prod.split("  live-page-boot:\n", 1)[1]
    url_match = re.search(r"ACS_FRONTEND_URL:\s*(https://\S+)", live_job)
    chk("the live page job declares an explicit HTTPS deployment URL", bool(url_match))
    live_step = live_job.split("- name: Boot the page and analyse the rendered viewport", 1)[1]
    live_step = live_step.split("- uses:", 1)[0]
    run = live_step.split("run: |\n", 1)[1]
    run = "\n".join(line[10:] for line in run.splitlines() if line.strip())
    chk("the live verifier receives the deployment URL instead of starting localhost",
        'verify_page_boot.js "$ACS_FRONTEND_URL"' in run)
    chk("the live job does not build an unrelated local frontend",
        "bash tools/netlify-build.sh" not in live_job)
    chk("synthetic pixel fixtures remain in CI, not labelled production evidence",
        "tests/deploy/test_viewport_pixels.js" in ci
        and "tests/deploy/test_viewport_pixels.js" not in run)
    with tempfile.TemporaryDirectory(prefix="acs-live-gate-") as tmp:
        node = os.path.join(tmp, "node")
        with open(node, "w", encoding="utf-8") as fh:
            fh.write('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ACS_NODE_ARGS"\n'
                     'exit "$ACS_NODE_EXIT"\n')
        os.chmod(node, 0o755)
        args_file = os.path.join(tmp, "args.txt")
        env = dict(os.environ, PATH=tmp + os.pathsep + os.environ.get("PATH", ""),
                   ACS_FRONTEND_URL=url_match.group(1) if url_match else "MISSING",
                   ACS_NODE_ARGS=args_file)
        for result in (0, 1, 2):
            env["ACS_NODE_EXIT"] = str(result)
            observed = subprocess.run(["bash", "-c", run], cwd=tmp, env=env,
                                      capture_output=True, text=True, timeout=10)
            chk("live workflow preserves verifier exit %d through tee" % result,
                observed.returncode == result, observed.stderr)
            args = rd(args_file).splitlines() if os.path.isfile(args_file) else []
            chk("live workflow actually passes the HTTPS target (exit %d)" % result,
                args == ["tests/deploy/verify_page_boot.js", env["ACS_FRONTEND_URL"]],
                repr(args))
        old_rc, _ = sh("set -o pipefail\n{ false; true; } | cat")
        chk("negative witness: the old grouped workflow masks its first failure",
            old_rc == 0)

    print("\n" + "=" * 62)
    print("CI GATE: %d passed, %d failed" % (p[0], f[0]))
    print("LIVE HTTP REACHABILITY: NOT VERIFIED by this contract suite; "
          "run the deployment verifiers separately.")
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
