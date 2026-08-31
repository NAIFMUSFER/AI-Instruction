#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_inline_style_sources.py
#
# العقد: **الوثيقة المخدومة لا تحمل تنسيقاً في العلامة — ولا مصدرَ واحد في
#         شيفرة التطبيق يعيده إليها.**
#
# ما أوجب هذا الملفّ — بقياسٍ في Chromium حقيقيّ
# ---------------------------------------------
# الوظيفة الثالثة على GitHub Actions أسقطت مجموعتين بالقياس نفسه:
#
#   tests/deploy/verify_page_boot.js
#     ✗ no element carries a style= attribute …                        [11,0]
#   tests/remediation/test_accessibility.js
#     ✗ no <style> block and no style= attribute survive …
#       {"styleBlocks":0,"inlineStyleAttrs":11,"inlineHandlers":[]}
#
# وصفر خرقِ سياسة في الحالتين: السياسة لم تُخرَق قطّ، لأن إسناد CSSOM لا تحكمه
# style-src (مقيسٌ في test_csp_style_architecture.js §١). لكنّ الإسناد
# **يُسلسِل نفسه** في سمة style، فتبقى الوثيقة المخدومة تحمل تنسيقاً في
# العلامة — وهو ما تمنعه معمارية أصناف المنفعة المعلنة.
#
# المصدران، مُحدَّدان بالقياس لا بالتخمين (أُقلعت public/ تحت السياسة
# الإنتاجية نفسها في Chromium حقيقيّ، وعُدّت العناصر الحاملة للسمة):
#
#   ١٠ × <i style="background: rgb(…)">   ← لوحة الألوان COLOR_SWATCH
#        public/app/ui/workspace-ui-wiring.js — عشرة ألوان **ثابتة** معلنة في
#        المصدر، لا بيانات مستخدم. صارت أصنافاً .acs-sw-01 … .acs-sw-10.
#    ١ × <canvas style="width:…px;height:…px">
#        كتبه three.js من renderer.setSize(w,h) لأن الوسيط الثالث updateStyle
#        كان متروكاً لقيمته الضمنية true. المستودع يمرّر false في أربعة مواضع
#        أخرى أصلاً؛ وُحِّد، وصار قياس الكانفس من #app > canvas.
#
# ما ليس في نطاق هذا الملفّ، وسببه
# --------------------------------
# إسنادات إظهار/إخفاء مشروطة (el.style.display في مسارات الدخول والنوافذ) لا
# تُدان هنا: هي حالة واجهة لحظية لا تنسيقاً ثابتاً، ولا تنفَّذ في الحالة التي
# تقيسها المجموعتان أعلاه. وإن نُفِّذت يوماً في تلك الحالة فسيسقط القياس الحيّ
# نفسه — فالبوّابة الحقيقية هناك، وهذا الملفّ يحرس المصدرين المُثبَتين.
# ==============================================================================
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
APP = os.path.join(ROOT, "public", "app")
CSS = os.path.join(APP, "styles", "app.css")
WIRING = os.path.join(APP, "ui", "workspace-ui-wiring.js")
SCENE = os.path.join(APP, "render", "scene.js")

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


def shipped_js():
    out = {}
    for base, dirs, files in os.walk(APP):
        dirs[:] = [d for d in dirs if d != "vendor"]
        for f in files:
            if f.endswith(".js"):
                p = os.path.join(base, f)
                out[os.path.relpath(p, ROOT)] = rd(p)
    return out


def code_only(src):
    """يحذف تعليقات /* */ و // — العقد على ما يُنفَّذ لا على شرحه."""
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


# إسنادُ لونٍ إلى عنصر عبر CSSOM — الصنف الذي أنتج العشرة.
PAINT = re.compile(r"\.style\.(background|backgroundColor|borderColor)\s*=")
# نداءُ setSize على **محرّك العرض** بوسيطين فقط — الذي أنتج الحادي عشر.
# التضييق مقصود ومُدقَّق أدناه: EffectComposer.setSize(w,h) توقيعٌ بوسيطين لا
# ثالث له ولا يمسّ العلامة، فإدانتُه كانت ستكون خطأً في العقد لا عطلاً في
# الشيفرة — وهو ما أظهره هذا الاختبار نفسه عند كتابته.
RENDERER_SETSIZE = re.compile(r"\brenderer\.setSize\(")
ANY_SETSIZE = re.compile(r"\b([A-Za-z_$][\w$]*)\.setSize\(")

SRC = shipped_js()
css = rd(CSS)

print("== أ · لا مصدر يعيد كتابة اللون في العلامة ==")
painters = sorted(f for f, s in SRC.items() if PAINT.search(code_only(s)))
chk("there are shipped modules to check at all", len(SRC) > 10, len(SRC))
chk("NO shipped module paints an element through el.style.background — the "
    "ten palette colours are static and belong in the stylesheet",
    not painters, painters)

print("\n== ب · الأصناف موجودة وتطابق القائمة ترتيباً ولوناً ==")
wiring = rd(WIRING)
m = re.search(r"const COLOR_SWATCH\s*=\s*\[(.*?)\];", wiring, re.S)
chk("COLOR_SWATCH is still the single declared palette", m is not None)
hexes = re.findall(r"'(#[0-9a-fA-F]{6})'", m.group(1)) if m else []
chk("it declares ten colours", len(hexes) == 10, len(hexes))
classes = re.findall(r"\.acs-sw-(\d\d)\{background:(#[0-9a-fA-F]{6})\}", css)
chk("app.css defines exactly one class per declared colour",
    len(classes) == len(hexes), "%d classes / %d colours"
    % (len(classes), len(hexes)))
chk("and each class carries the colour at the SAME index — the list and the "
    "stylesheet cannot drift apart silently",
    [c for _, c in classes] == hexes
    and [n for n, _ in classes] == ["%02d" % (i + 1) for i in range(len(hexes))],
    str(classes[:3]) + " vs " + str(hexes[:3]))
chk("the mapping is computed in ONE place (swatchClass) rather than spelled "
    "out at each call site", "function swatchClass(ix)" in wiring
    and len(re.findall(r"className\s*=\s*swatchClass\(ix\)", wiring)) == 2,
    len(re.findall(r"className\s*=\s*swatchClass\(", wiring)))

print("\n== ج · الكانفس يُقاس من ورقة الأنماط لا من العلامة ==")
def _args(src, at):
    return src[at:].split(")")[0]


renderer_calls, other_receivers = [], {}
for f, src in SRC.items():
    code = code_only(src)
    for call in RENDERER_SETSIZE.finditer(code):
        renderer_calls.append((f, _args(code, call.end())))
    for call in ANY_SETSIZE.finditer(code):
        recv = call.group(1)
        if recv != "renderer":
            other_receivers.setdefault(recv, []).append(f)

chk("there are renderer.setSize() calls to audit", len(renderer_calls) >= 3,
    len(renderer_calls))
bad_setsize = [f + ": renderer.setSize(" + a.strip()[:60] + ")"
               for f, a in renderer_calls if a.count(",") < 2]
chk("every renderer.setSize() in shipped code passes updateStyle explicitly — "
    "its default is true, and true is what wrote style= onto the canvas",
    not bad_setsize, bad_setsize)
chk("and every one of them passes false",
    all("false" in a for _, a in renderer_calls),
    [a for _, a in renderer_calls])
# التضييق على المتلقّي `renderer` ليس ثغرة تُترك بلا حساب: كل متلقٍّ آخر
# يُسمَّى هنا، فمن أضاف محرّك عرضٍ باسمٍ ثانٍ ظهر في هذا التوكيد فوراً.
chk("and every OTHER .setSize() receiver in shipped code is a post-processing "
    "object whose setSize takes (w, h) only and never touches the DOM — the "
    "narrowing above is audited, not assumed",
    set(other_receivers) <= {"composer", "c"},
    {k: sorted(set(v)) for k, v in other_receivers.items()})
chk("the stylesheet sizes the canvas instead", 
    re.search(r"#app\s*>\s*canvas\{[^}]*width:100%[^}]*height:100%", css)
    is not None,
    [ln for ln in css.splitlines() if "canvas" in ln][:3])

print("\n== د · شواهد سالبة: الكواشف تُدين الأسطر التي أُصلحت بعينها ==")
chk("the paint detector fires on the exact line that produced the ten",
    bool(PAINT.search("const i=document.createElement('i'); i.style.background=hx;")))
chk("it is not fooled by a mere mention inside a comment",
    not PAINT.search(code_only("/* i.style.background=hx */\n")))
_old = "renderer.setSize(innerWidth,innerHeight);"
_head = _old[_old.index("(") + 1:_old.index(")")]
chk("the setSize detector fires on the exact two-argument call that produced "
    "the eleventh", _head.count(",") < 2, _head)
chk("and it accepts the three-argument form the repository already used "
    "elsewhere", "renderer.setSize(w,h,false)".split("(")[1].count(",") == 2)

print("\n" + "─" * 62)
print("INLINE STYLE SOURCES: %d passed, %d failed" % (_p, _f))
sys.exit(1 if _f else 0)
