#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_browser_acquisition.py
#
# اكتساب المتصفّح مسارٌ واحد: tools/pw_chromium.js.
#
# لماذا يوجد هذا الاختبار
# -----------------------
# كانت مجموعات المتصفّح تكتسب Chromium بأربع طرائق مختلفة في الملفّ نفسه:
#
#   chromium.launch()                                   ← لا احتياط
#   chromium.launch({executablePath:'/opt/pw-browsers/chromium'})  ← مسار مخبوز
#   try{ launch() }catch{ launch({executablePath:…}) }   ← احتياط يدويّ مكرَّر
#   PW.launch()                                         ← المسار الصحيح
#
# ونسخة Playwright المثبّتة تطلب بناءً محدّداً من Chromium (1234)، بينما الصندوق
# يحمل 1194. فكانت النتيجة أن الغياب البيئيّ نفسه يُقرأ ثلاث قراءات متناقضة:
#
#   test_panel_entry.js            → 13 توكيداً ثم «NOT VERIFIED»
#   test_csp_style_architecture.js → 20 توكيداً ثم «NOT VERIFIED»
#   test_apply_render_browser.js   → استثناء غير ملتقَط، وخروج ≠ 0
#   test_scene_benchmark.js        → استثناء غير ملتقَط، وخروج ≠ 0
#
# أي أن المجموعة كلّها كانت تُبلِّغ «FAILURES PRESENT» بسبب اسم مجلَّد، لا بسبب
# عطلٍ في المنتج — وفي الوقت نفسه كانت 110 توكيدات حقيقية (30 + 80) لا تُنفَّذ
# إطلاقاً رغم أنها لا تحتاج three.js أصلاً. توحيد المسار شغّلها.
#
# ولماذا وُسِّع نطاقه
# ------------------
# لأن أوّل صيغةٍ منه مسحت `tests/remediation/*.js` وحدها. فبقي خارج العقد ما
# يشغّله CI فعلاً، وأثبتته الوظيفة الثالثة على GitHub Actions:
#
#   ✗ browser fixture error browserType.launch: Failed to launch chromium
#     because executable doesn't exist at /opt/pw-browsers/chromium
#
# وهو مسار صورة هذا الصندوق، مخبوزاً في tests/deploy/test_viewport_pixels.js —
# ولا وجود له على العدّاء إطلاقاً. وفي الوقت نفسه كانت الثنائيّة التي نزّلها
# `npx playwright install --with-deps chromium` إلى
# /home/runner/.cache/ms-playwright/chromium-1234 قائمةً بلا مستعمل. ومثلُه
# كان في tests/deploy/verify_page_boot.js (احتياطٌ يدويّ نجا بالصدفة لأن
# النداء الأوّل نجح) وفي tests/production/verify_live_browser.js (سقوطٌ صامت
# إلى `{}` يُخفي أيّ ثنائيّة استُعملت).
#
# فالعقد الآن على **الشجرة كلّها**، لا على مجلَّد واحد: من أراد متصفّحاً فليطلبه
# من المُحدِّد، فيبقى قرارُ «أيّ ثنائيّة» في موضع واحد يُصحَّح مرّة واحدة.
# ==============================================================================
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HELPER = os.path.join(ROOT, "tools", "pw_chromium.js")

_p = _f = 0


def chk(name, cond, detail=""):
    global _p, _f
    if cond:
        _p += 1
        print("  ✓", name)
    else:
        _f += 1
        print("  ✗", name, ("\n      " + str(detail)) if detail else "")


# النداء المباشر: chromium.launch(  —  ويُستثنى المُحدِّد نفسه، فهو موضعه.
DIRECT = re.compile(r"\bchromium\s*\.\s*launch\s*\(")
# المسار المخبوز: أيّ ذكر لثنائيّة داخل /opt خارج المُحدِّد.
BAKED = re.compile(r"executablePath\s*:\s*['\"]/opt/")
# وأعمّ منه: أيّ ذكرٍ لجذر الصورة أصلاً خارج المُحدِّد — فحتى `existsSync`
# على مسارٍ تحته هو قرارُ اكتسابٍ اتُّخذ في المكان الخطأ.
SANDBOX_ROOT = re.compile(r"/opt/pw-browsers")

SKIP_DIRS = {"node_modules", ".git", "vendor", "screenshots", "outputs"}
# الامتدادات الثلاثة كلّها: أوّل صيغةٍ من هذا المسح فحصت `.js` وحدها، فبقي
# tools/verify-offline.mjs — نصّ تحقّقٍ موثَّق في VERIFICATION-RUNBOOK — ينادي
# chromium.launch مباشرةً خارج المُحدِّد. الامتداد ليس تفصيلاً في عقدٍ يدّعي
# تغطية الشجرة كلّها.
JS_EXT = (".js", ".mjs", ".cjs")


def js_files():
    """كل ملفّات JS في الشجرة عدا التبعيات والمخرجات — والمُحدِّد نفسه."""
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(JS_EXT):
                continue
            p = os.path.join(base, f)
            if os.path.abspath(p) == os.path.abspath(HELPER):
                continue
            out.append(os.path.relpath(p, ROOT))
    return sorted(out)


def code_only(src):
    """يحذف تعليقات /* */ و // فيبقى ما يُنفَّذ وحده.

    العقد على الشيفرة لا على النثر: شرحُ *لماذا* لا ننادي chromium.launch
    مباشرةً يذكر الاسم بالضرورة، ولو فحصنا الملفّ خاماً لأدان الشرحُ نفسه
    الإصلاحَ الذي يشرحه. الحذف سطحيّ ومقصود كذلك — لا يفهم السلاسل النصّية —
    ولذلك يُشدَّد أثره باختبار سالب أدناه بدل الثقة به.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        two = src[i:i + 2]
        if two == "/*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif two == "//":
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


print("== أ · لا نداء مباشر لـ chromium.launch في الشجرة كلّها ==")
TARGETS = js_files()
chk("there are JavaScript files to check at all", len(TARGETS) > 10, len(TARGETS))
# النطاق نفسه جزءٌ من العقد: حصرُ المسح في tests/remediation هو ما سمح
# بعودة العطل، فيُثبَّت أن المسح يتجاوزه.
chk("the scan covers .mjs and .cjs too, not only .js — a .mjs verification "
    "script is how a direct chromium.launch survived the first scan",
    any(t.endswith(".mjs") or t.endswith(".cjs") for t in TARGETS),
    [t for t in TARGETS if t.endswith((".mjs", ".cjs"))][:5])
chk("the scan reaches beyond tests/remediation — the narrow scan is what let "
    "the baked path survive",
    any(t.startswith("tests" + os.sep + "deploy") for t in TARGETS)
    and any(t.startswith("tests" + os.sep + "production") for t in TARGETS)
    and any(t.startswith("tests" + os.sep + "phase3") for t in TARGETS),
    [t for t in TARGETS if not t.startswith("tests" + os.sep + "remediation")][:5])

offenders_direct, offenders_baked, offenders_root, users = [], [], [], []
for f in TARGETS:
    raw = open(os.path.join(ROOT, f), encoding="utf-8").read()
    src = code_only(raw)
    if DIRECT.search(src):
        offenders_direct.append(f)
    if BAKED.search(src):
        offenders_baked.append(f)
    if SANDBOX_ROOT.search(src):
        offenders_root.append(f)
    if "pw_chromium.js" in src:
        users.append(f)

chk("NO file calls chromium.launch() directly — every launch goes through "
    "tools/pw_chromium.js", not offenders_direct, offenders_direct)
chk("NO file bakes a /opt browser path of its own", not offenders_baked,
    offenders_baked)
chk("NO file outside the resolver even names the image's browser root — "
    "acquisition decisions live in one place", not offenders_root,
    offenders_root)

print("\n== ب · المجموعات التي تطلق متصفّحاً تمرّ من المُحدّد ==")
EXPECTED = [
    # مجموعات المعالجة
    os.path.join("tests", "remediation", "csp_browser_probe.js"),
    os.path.join("tests", "remediation", "test_accessibility.js"),
    os.path.join("tests", "remediation", "test_apply_render_browser.js"),
    os.path.join("tests", "remediation", "test_csp_style_architecture.js"),
    os.path.join("tests", "remediation", "test_panel_entry.js"),
    os.path.join("tests", "remediation", "test_scene_benchmark.js"),
    os.path.join("tests", "remediation", "test_webgl_diagnostics.js"),
    # ما تشغّله الوظيفة الثالثة على GitHub Actions ولم يكن في العقد
    os.path.join("tests", "deploy", "test_viewport_pixels.js"),
    os.path.join("tests", "deploy", "verify_page_boot.js"),
    os.path.join("tests", "phase3", "lib", "run_browser.js"),
    # وبقيّة ما يطلق متصفّحاً في الشجرة
    os.path.join("tests", "production", "verify_live_browser.js"),
    os.path.join("tests", "performance", "run_perf.js"),
    os.path.join("tests", "phase4", "test_browser_parity.js"),
    os.path.join("tests", "phase5", "test_browser_parity.js"),
    os.path.join("tests", "phase6", "test_responsive.js"),
    os.path.join("tests", "phase6", "walkthrough.js"),
    os.path.join("tests", "phase9_1", "capture_reference.js"),
    os.path.join("tests", "phase9_2", "capture_reference_92.js"),
    # نصّ تحقّق موثَّق (VERIFICATION-RUNBOOK.md §A) لا مجموعة اختبار — والعقد
    # يشمله: «كل ملفّ يطلق Chromium»، لا «كل اختبار».
    os.path.join("tools", "verify-offline.mjs"),
]
for f in EXPECTED:
    chk(f + " requires tools/pw_chromium.js", f in users, users)

print("\n== ج · المُحدّد نفسه ==")
helper = open(HELPER, encoding="utf-8").read() if os.path.exists(HELPER) else ""
hcode = code_only(helper)
chk("tools/pw_chromium.js exists", bool(helper))
chk("it exports executable() and launch()",
    "exports = { executable, launch" in helper)
chk("it honours an environment override before scanning",
    "ACS_CHROMIUM" in helper)
chk("it scans PLAYWRIGHT_BROWSERS_PATH and /opt/pw-browsers",
    "PLAYWRIGHT_BROWSERS_PATH" in helper and "/opt/pw-browsers" in helper)
chk("it REFUSES to fabricate a browser — it throws when none exists",
    "throw new Error('no Chromium binary is available" in helper)

# الترتيب هو العقد، لا مجرّد وجود الفرعين: في GitHub Actions تُنزَّل الثنائيّة
# المُدارة فعلاً، فلا يجوز لأي مسحِ جذورٍ أن يسبقها. يُقاس داخل جسم resolve()
# على الشيفرة المجرّدة من التعليقات — لا على ترتيب التصريحات ولا على شرحٍ نثريّ.
body = hcode[hcode.find("function resolve("):]
body = body[:body.find("\nfunction ")]
at_pw = body.find("playwright-managed")
at_scan = body.find("scanBrowsersRoot(")
chk("resolve() has a body to inspect", at_pw >= 0 and at_scan >= 0,
    body[:200])
chk("Playwright's own managed executable is consulted BEFORE the root scan — "
    "this is what makes the browser `playwright install` downloaded in CI the "
    "one that actually gets used",
    0 <= at_pw < at_scan, "playwright@%s scan@%s" % (at_pw, at_scan))
chk("and an explicit operator override precedes both",
    0 <= body.find("CANDIDATE_ENV") < at_pw)
chk("the image root appears as a search ROOT, never as an executable path",
    "SANDBOX_BROWSERS_ROOT = '/opt/pw-browsers'" in hcode
    and "/opt/pw-browsers/chromium" not in hcode,
    [ln for ln in hcode.splitlines() if "/opt/pw-browsers" in ln])
chk("a full chromium build outranks a headless shell — the shell cannot carry "
    "the WebGL measurements these suites make",
    "headless" in hcode and "rank(" in hcode)

print("\n== د · المُحدّد يرفض حيّاً: لا اختلاق عند الغياب ==")
# ليس فحصاً نصّياً: يُشغَّل المُحدِّد في عملية أخرى بلا جذورٍ إطلاقاً وبلا
# تجاوزات بيئية، فيجب أن يعطي null ثم يرمي. لو أضاف أحدٌ احتياطاً يُخفي الغياب
# — سقوطاً صامتاً إلى ثنائيّةٍ أخرى أو إلى `{}` — لسقط هذا هنا.
chk("launch() resolves through the same seam it is measured with — the "
    "refusal path tested below is the production one",
    "const r = resolve(acq);" in hcode)
# الحَقن يضيّق ولا يوسّع: كل مفتاح فيه يحذف مصدراً من مصادر الاكتساب. لو صار
# يضيف مساراً لصار الشاهد أدناه يقيس شيئاً آخر.
chk("the injection seam can only REMOVE sources, never add one",
    "o.playwright === false" in hcode and "o.roots ||" in hcode
    and "o.env ||" in hcode)
PROBE = r"""
const PW = require(process.argv[2]);
const NONE = { env: {}, roots: [], playwright: false };
(async () => {
  const r = PW.resolve(NONE);
  let threw = '', launched = false, b = null;
  try { b = await PW.launch({}, NONE); launched = true; }
  catch (e) { threw = String(e.message); }
  if (b) await b.close();
  console.log(JSON.stringify({ path: r.path, source: r.source,
    searched: r.searched.length, threw: threw, launched: launched }));
})();
"""
tmpd = tempfile.mkdtemp(prefix="acs_acq_probe_")
probe = os.path.join(tmpd, "probe.js")
open(probe, "w", encoding="utf-8").write(PROBE)
try:
    out = subprocess.run([os.environ.get("NODE", "node"), probe, HELPER],
                         cwd=ROOT, capture_output=True, text=True, timeout=90)
    live = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
except (OSError, subprocess.TimeoutExpired) as e:
    live, out = "", e

if live.startswith("{"):
    import json
    v = json.loads(live)
    chk("with no root to scan the resolver returns NO path — it does not "
        "invent one", v["path"] is None, v)
    chk("and launch() throws instead of quietly launching something else",
        v["launched"] is False
        and v["threw"].startswith("no Chromium binary is available"),
        v["threw"][:200])
    chk("the refusal names what was searched, so a CI log says WHY",
        v["searched"] >= 2 and "searched:" in v["threw"], v["threw"][:220])
else:
    # لا يُدَّعى نجاح ولا يُدَّعى فشل: البيئة نفسها غير متاحة.
    print("  · live resolver probe NOT VERIFIED — EXTERNAL ENVIRONMENT "
          "REQUIRED (node unavailable): %s" % (out,))

print("\n== د٢ · الرفض يبقى رفضَ اكتساب حتى بلا حزمة playwright ==")
# هذا بالضبط ما أسقط توكيدَين في الوظيفة السابعة على GitHub Actions:
#     BROWSER ACQUISITION: 41 passed, 2 failed
# تلك الوظيفة لا تشغّل `npm ci`، فحزمة playwright غير مركَّبة فيها أصلاً. وكان
# launch() يحمّلها **قبل** أن يحسم الاكتساب، فيصل المستدعي:
#     Cannot find module 'playwright'
# بدل رفضِ اكتسابٍ يسمّي ما فُتِّش عنه. والغياب مُسجَّل داخل searched أصلاً،
# فالرسالة الصحيحة كانت موجودة ولا تُقال.
#
# يُقاس هنا بعزلٍ حقيقي: تُنسَخ الشيفرة نفسها إلى مجلّد خارج الشجرة، وتُشغَّل
# بلا NODE_PATH، فلا تُحَلّ playwright من أي جذر. لا محاكاة للغياب: غيابٌ فعليّ.
ISO = tempfile.mkdtemp(prefix="acs_acq_iso_")
helper_bytes = open(HELPER, "rb").read()
iso_helper = os.path.join(ISO, "pw_chromium.js")
open(iso_helper, "wb").write(helper_bytes)
chk("the isolated copy is the same resolver, byte for byte",
    open(iso_helper, "rb").read() == helper_bytes)
ISO_PROBE = r"""
const PW = require(process.argv[2]);
let pwPresent = true;
try { require('playwright'); } catch (e) { pwPresent = false; }
(async () => {
  let threw = '', launched = false;
  try { await PW.launch({}, { env: {}, roots: [] }); launched = true; }
  catch (e) { threw = String(e.message); }
  console.log(JSON.stringify({ pwPresent: pwPresent, threw: threw,
                               launched: launched }));
})();
"""
iso_probe = os.path.join(ISO, "probe.js")
open(iso_probe, "w", encoding="utf-8").write(ISO_PROBE)
iso_env = dict(os.environ)
iso_env.pop("NODE_PATH", None)
for k in ("ACS_CHROMIUM", "CHROMIUM_PATH", "PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
    iso_env.pop(k, None)
try:
    io_out = subprocess.run([os.environ.get("NODE", "node"), iso_probe,
                             iso_helper],
                            cwd=ISO, env=iso_env, capture_output=True,
                            text=True, timeout=90)
    iso_live = io_out.stdout.strip().splitlines()[-1] if io_out.stdout.strip() else ""
except (OSError, subprocess.TimeoutExpired) as e:
    iso_live, io_out = "", e

if iso_live.startswith("{"):
    import json as _json
    w = _json.loads(iso_live)
    chk("the isolation is real: playwright genuinely cannot be resolved there — "
        "this is CI job 7's condition, which runs no `npm ci`",
        w["pwPresent"] is False, w)
    chk("and launch() still refuses as an ACQUISITION failure, not as a missing "
        "module — the message names the browser, not the package",
        w["launched"] is False
        and w["threw"].startswith("no Chromium binary is available"),
        w["threw"][:220])
    chk("and it still names what was searched, including that playwright "
        "itself could not be loaded",
        "searched:" in w["threw"]
        and "playwright could not be loaded" in w["threw"], w["threw"][:260])
else:
    print("  · isolated no-playwright probe NOT VERIFIED — EXTERNAL "
          "ENVIRONMENT REQUIRED (node unavailable): %s" % (io_out,))

print("\n== د٣ · تجاوزٌ صريح لا يُنفَّذ لا يُتجاوَز بصمت ==")
# الأسبقيّة المعلَنة: تجاوزٌ صريح ← ثنائيّة Playwright المُدارة ← جذور البحث.
# فلو سقط تجاوزٌ خاطئ إلى المصدر التالي لَحصل المشغّل على متصفّحٍ غير الذي
# طلبه ولَما علم — وهو سقوطٌ صامت بالتعريف. يُقاس على آلةٍ **فيها** متصفّح
# صالح، وإلا لم يثبت شيء: الرفض هنا ليس لعدم وجود بديل، بل لأن الصريح صريح.
OVERRIDE_PROBE = r"""
const PW = require(process.argv[2]);
const BAD = { env: { ACS_CHROMIUM: '/definitely/not/a/browser' } };
(async () => {
  const real = PW.resolve();
  const r = PW.resolve(BAD);
  let threw = '', launched = false;
  try { const b = await PW.launch({}, BAD); launched = true; await b.close(); }
  catch (e) { threw = String(e.message); }
  console.log(JSON.stringify({ realPath: real.path, path: r.path,
    source: r.source, refusal: r.refusal || '', threw: threw,
    launched: launched }));
})();
"""
ov_probe = os.path.join(tmpd, "override.js")
open(ov_probe, "w", encoding="utf-8").write(OVERRIDE_PROBE)
try:
    ov_out = subprocess.run([os.environ.get("NODE", "node"), ov_probe, HELPER],
                            cwd=ROOT, capture_output=True, text=True,
                            timeout=90)
    ov_live = ov_out.stdout.strip().splitlines()[-1] if ov_out.stdout.strip() else ""
except (OSError, subprocess.TimeoutExpired) as e:
    ov_live, ov_out = "", e

if ov_live.startswith("{"):
    import json as _json
    o = _json.loads(ov_live)
    if o["realPath"]:
        chk("a VALID browser exists on this machine — so the refusal below is "
            "about the override, not about scarcity", bool(o["realPath"]),
            o["realPath"])
        chk("an explicit override naming a file that does not exist resolves to "
            "NOTHING — it does not quietly fall through to another browser",
            o["path"] is None and o["source"] is None, o)
        chk("and launch() refuses, naming the override that could not be honoured",
            o["launched"] is False
            and "/definitely/not/a/browser" in o["threw"]
            and "override" in o["threw"], o["threw"][:220])
        chk("and the refusal is distinguishable from 'no browser anywhere'",
            "does not exist" in o["refusal"], o["refusal"])
    else:
        print("  · override witness NOT VERIFIED — EXTERNAL ENVIRONMENT "
              "REQUIRED: no valid browser on this machine, so a refusal here "
              "would prove nothing.")
else:
    print("  · override witness NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED "
          "(node unavailable): %s" % (ov_out,))

print("\n== د٤ · السجلّ يقول أيّ ثنائيّة اختيرت ومن أين ==")
chk("the resolver announces the selection: path, source and searched locations",
    "[ACS-BROWSER] selected: " in hcode and "source: " in hcode
    and "[ACS-BROWSER] searched: " in hcode)
chk("and it announces on stderr, so byte-compared stdout of the parity suites "
    "is not disturbed", "process.stderr.write('[ACS-BROWSER]" in hcode)
# الإعلان لا يُقاس إلا من إطلاقٍ نجح فعلاً — مسابر §د٣ ترفض عمداً فلا تُعلن.
LAUNCH_PROBE = r"""
const PW = require(process.argv[2]);
(async () => {
  try { const b = await PW.launch(); await b.close(); console.log('LAUNCHED'); }
  catch (e) { console.log('NOLAUNCH ' + e.message); }
})();
"""
ln_probe = os.path.join(tmpd, "launch.js")
open(ln_probe, "w", encoding="utf-8").write(LAUNCH_PROBE)
try:
    ln = subprocess.run([os.environ.get("NODE", "node"), ln_probe, HELPER],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
except (OSError, subprocess.TimeoutExpired) as e:
    ln = None
if ln is not None and "LAUNCHED" in (ln.stdout or ""):
    chk("a REAL successful launch emits the selection line on stderr",
        "[ACS-BROWSER] selected: " in (ln.stderr or ""),
        (ln.stderr or "")[:200])
    chk("and that line names an executable that actually exists",
        any(os.path.exists(tok) for tok in (ln.stderr or "").split()
            if tok.startswith("/")), (ln.stderr or "")[:200])
    chk("and the searched locations are reported beside it",
        "[ACS-BROWSER] searched: " in (ln.stderr or ""),
        (ln.stderr or "")[:300])
else:
    print("  · live launch announcement NOT VERIFIED — EXTERNAL ENVIRONMENT "
          "REQUIRED (no browser here): %s"
          % ((ln.stdout.strip() if ln is not None else "node unavailable"),))

print("\n== هـ · شاهد سالب: المُجرِّد لا يُخفي نداءً حقيقياً ==")
# لو كان code_only() هو ما يُمرِّر الملفّات، لمرّ هذا أيضاً. لا يمرّ.
POSITIVE = "const b = await chromium.launch({ args: [] });"
NEGATIVE = "/* chromium.launch() ممنوع هنا */\n// chromium.launch()\n"
chk("a REAL direct call is still caught after comment stripping",
    bool(DIRECT.search(code_only(POSITIVE + NEGATIVE))))
chk("a call named ONLY inside comments is not counted as one",
    not DIRECT.search(code_only(NEGATIVE)))
chk("stripping keeps the code around a comment intact",
    code_only("a();/* x */b();") == "a();b();",
    code_only("a();/* x */b();"))
# والشاهد على الفحصين الجديدين كذلك — وإلا كان «لا مخالف» يعني «لا فحص».
chk("the baked-path detector still fires on the exact line CI reported",
    bool(BAKED.search(code_only(
        "chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });"))))
chk("the image-root detector fires even without executablePath:",
    bool(SANDBOX_ROOT.search(code_only(
        "const P = '/opt/pw-browsers/chromium';"))))

print("\n" + "─" * 62)
print("BROWSER ACQUISITION: %d passed, %d failed" % (_p, _f))
sys.exit(1 if _f else 0)
