# -*- coding: utf-8 -*-
"""tools/app_source.py — مصدر واحد لقراءة شيفرة الواجهة بعد التفكيك (F-09).

نظير بايثون لـ tests/lib/app_source.js. قبل F-09 كانت الأدوات تقرأ
public/index.html نصّاً وتبحث فيه؛ بعد التفكيك صار التطبيق ملفّات تحت
public/app/ والصفحة قشرة. هذه الوحدة وحدها تعرف التخطيط.

    shell()      نصّ القشرة (بنية + خريطة استيراد فقط)
    modules()    dict: مسار نسبي تحت public/app → نصّ
    app_text()   شيفرة التطبيق موصولة بترتيب التحميل الحقيقي
    page_text()  القشرة + الشيفرة — بديل مطابق دلالياً لِما كان `page`

الفصل مقصود: البحث في العلامة يستعمل shell()، والبحث عن رمز يستعمل app_text().
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUB = os.path.join(ROOT, "public")
APP = os.path.join(PUB, "app")

# الطبقات النقيّة: لا DOM ولا Three ولا window
PURE = ("core/polygon.js", "core/viewer.js", "core/standards.js", "core/disciplines.js")


def _read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def shell():
    return _read(os.path.join(PUB, "index.html"))


def order():
    """ترتيب التحميل الحقيقي كما يعلنه public/app/main.js."""
    main = _read(os.path.join(APP, "main.js"))
    return re.findall(r"^import '\./(.+?)';$", main, re.M)


def modules():
    out = {}
    for base, _dirs, files in os.walk(APP):
        for f in sorted(files):
            if not f.endswith(".js"):
                continue
            p = os.path.join(base, f)
            out[os.path.relpath(p, APP).replace("\\", "/")] = _read(p)
    return out


def app_text():
    mods = modules()
    seq = [f for f in order() if f in mods]
    rest = sorted(f for f in mods if f not in seq)
    return "\n".join("/* ==== public/app/%s ==== */\n%s" % (f, mods[f])
                     for f in seq + rest)


def page_text():
    return shell() + "\n" + app_text()


def module_bytes():
    return {k: len(v.encode("utf-8")) for k, v in modules().items()}


def css_text():
    p = os.path.join(APP, "styles", "app.css")
    return _read(p) if os.path.exists(p) else ""


def boot_scripts():
    d = os.path.join(APP, "boot")
    if not os.path.isdir(d):
        return {}
    return {f: _read(os.path.join(d, f))
            for f in sorted(os.listdir(d)) if f.endswith(".js")}


def importmap():
    """نصّ خريطة الاستيراد الداخلية كما يراها CSP بالضبط (بلا الوسمين)."""
    html = shell()
    m = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    return m.group(1) if m else ""


def importmap_hash():
    import base64
    import hashlib
    return "sha256-" + base64.b64encode(
        hashlib.sha256(importmap().encode("utf-8")).digest()).decode("ascii")
