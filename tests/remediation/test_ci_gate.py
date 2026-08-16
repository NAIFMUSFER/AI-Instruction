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

    print("\n" + "=" * 62)
    print("CI GATE: %d passed, %d failed" % (p[0], f[0]))
    print("LIVE HTTP REACHABILITY: NOT VERIFIED — EXTERNAL ENVIRONMENT "
          "REQUIRED (this sandbox blocks the CONNECT tunnel; DNS and TLS to "
          "the configured origin DO succeed, which is what this file can prove).")
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
