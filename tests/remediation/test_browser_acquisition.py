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
# العقد المُثبَّت هنا: لا ملفّ تحت tests/remediation/ ينادي chromium.launch
# مباشرةً. من أراد متصفّحاً فليطلبه من المُحدِّد، فيبقى قرارُ «أيّ ثنائيّة» في
# موضع واحد يُصحَّح مرّة واحدة.
# ==============================================================================
import os
import re
import sys

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

print("== أ · لا نداء مباشر لـ chromium.launch تحت tests/remediation ==")
targets = sorted(f for f in os.listdir(HERE) if f.endswith(".js"))
chk("there are browser suites to check at all", len(targets) > 0, len(targets))

offenders_direct, offenders_baked, users = [], [], []
for f in targets:
    raw = open(os.path.join(HERE, f), encoding="utf-8").read()
    src = code_only(raw)
    if DIRECT.search(src):
        offenders_direct.append(f)
    if BAKED.search(src):
        offenders_baked.append(f)
    if "pw_chromium.js" in src:
        users.append(f)

chk("NO suite calls chromium.launch() directly — every launch goes through "
    "tools/pw_chromium.js", not offenders_direct, offenders_direct)
chk("NO suite bakes a /opt browser path of its own", not offenders_baked,
    offenders_baked)

print("\n== ب · المجموعات التي تطلق متصفّحاً تمرّ من المُحدّد ==")
EXPECTED = ["csp_browser_probe.js", "test_accessibility.js",
            "test_apply_render_browser.js", "test_csp_style_architecture.js",
            "test_panel_entry.js", "test_scene_benchmark.js",
            "test_webgl_diagnostics.js"]
for f in EXPECTED:
    chk(f + " requires tools/pw_chromium.js", f in users, users)

print("\n== ج · المُحدّد نفسه ==")
helper = open(HELPER, encoding="utf-8").read() if os.path.exists(HELPER) else ""
chk("tools/pw_chromium.js exists", bool(helper))
chk("it exports executable() and launch()",
    "exports = { executable, launch" in helper)
chk("it honours an environment override before scanning",
    "ACS_CHROMIUM" in helper)
chk("it scans PLAYWRIGHT_BROWSERS_PATH and /opt/pw-browsers",
    "PLAYWRIGHT_BROWSERS_PATH" in helper and "/opt/pw-browsers" in helper)
chk("it REFUSES to fabricate a browser — it throws when none exists",
    "throw new Error('no Chromium binary is available" in helper)

print("\n== د · شاهد سالب: المُجرِّد لا يُخفي نداءً حقيقياً ==")
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

print("\n" + "─" * 62)
print("BROWSER ACQUISITION: %d passed, %d failed" % (_p, _f))
sys.exit(1 if _f else 0)
