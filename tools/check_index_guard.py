# -*- coding: utf-8 -*-
"""حارس صفحة التطبيق — بعد التفكيك (F-09/F-11)، علاج إنتاجي دائم.

مصدر الحقيقة الوحيد لفحص سلامة الواجهة المشحونة بنيوياً: يستدعيه بناء Netlify
قبل النشر (فشل الفحص = فشل البناء فلا يُنشر شيء مكسور)، ويستدعيه تحقّق النشر مع
اختبارات سلبية تثبت أن الحارس نفسه ليس عقيماً.

╔══════════════════════════════════════════════════════════════════════════╗
║ الانقلاب: كان `MIN_BYTES = 1000000` — «صفحة أصغر من ميغابايت مبتورة».     ║
║ صار     `MAX_BYTES = 204800`  — «صفحة أكبر من 200 KB لم تُفكَّك».           ║
║ الشرط نفسه انقلب اتجاهه لأن المعمار انقلب: قبل F-09 كان التطبيق كلّه داخل   ║
║ الصفحة فكان الحجم دليل الاكتمال؛ بعد F-09 صار التطبيق ملفّات تحت /app/     ║
║ وصارت الصفحة قشرةً، فأي حجم كبير دليلُ ارتداد لا دليلُ اكتمال. الاكتمال     ║
║ لم يُلغَ بل نُقل إلى مكانه الصحيح: كل فحص كان يجري على نصّ الصفحة يجري الآن  ║
║ على نصّ الوحدات (app_source.app_text)، ومعه فحوص جديدة لم تكن ممكنة أصلاً:  ║
║ كل مرجع في القشرة يُحلّ إلى ملفّ موجود، ولا سطر جافاسكربت داخلي، ولا سمة    ║
║ style، ولا وحدة يتيمة، ولا وحدة تتجاوز السقف.                             ║
╚══════════════════════════════════════════════════════════════════════════╝

    python3 tools/check_index_guard.py public/index.html
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import app_source as A                                            # noqa: E402

# ── الحدود المعلَنة ─────────────────────────────────────────────────────────
# سقف القشرة. الصفحة لا تحمل تطبيقاً: ترويسة + كتل DOM المولَّدة + <link> +
# خمسة <script src> + وسم وحدة واحد. 200 KB سقف كريم لذلك، والقشرة اليوم
# ‏44 KB — أي ارتفاع نحو السقف يعني أن شيئاً عاد ليُلصق في الصفحة.
MAX_BYTES = 200 * 1024              # 204800 — كان MIN_BYTES = 1000000
# أكبر ملفّ JS واحد. تقسيمٌ لا ينتج عنه قطعة أصغر من ذلك ليس تقسيماً.
MODULE_SIZE_CAP = 300 * 1024        # 307200
# استثناءات موثّقة من السقف أعلاه. اليوم فارغة، ويجب أن تبقى كذلك: من يريد
# تجاوز السقف يكتب اسم ملفّه هنا مع سببه صراحةً، فيصير التجاوز قراراً مرئياً
# في المراجعة بدل أن يكون انزلاقاً صامتاً.
OVERSIZE_ALLOWLIST = {}             # اسم الوحدة → سبب موثّق

# الوحدات التي لا يستوردها main.js عمداً — ولكل واحدة سبب بنيوي:
#   boot/*        سكربتات كلاسيكية يحمّلها وسم <script src> قبل الوحدات
#   styles/       ليست جافاسكربت
#   main.js       هو المستورِد نفسه
#   shared-state.js  تستورده الوحدات لا نقطة الدخول
NOT_IMPORTED_BY_MAIN = ("main.js", "shared-state.js")

PAIRS = [
    ('/* ===== ACS RUNTIME LAYER', '/* ===== END ACS RUNTIME LAYER ===== */'),
    ('/* ===== ACS AUTHORING LAYER',
     '/* ===== END ACS AUTHORING LAYER ===== */'),
    ('/* ===== ACS WORKSPACE UI', '/* ===== END ACS WORKSPACE UI ===== */'),
    ('/* ===== ACS RENDER ENGINE', '/* ===== END ACS RENDER ENGINE ===== */'),
    ('/* ===== ACS BIM EXCHANGE', '/* ===== END ACS BIM EXCHANGE ===== */'),
    ('/* ===== ACS DOCUMENTATION', '/* ===== END ACS DOCUMENTATION ===== */'),
    ('/* ===== ACS PBR QUALITY', '/* ===== END ACS PBR QUALITY ===== */'),
    ('/* ===== ACS PBR BRIDGE', '/* ===== END ACS PBR BRIDGE ===== */'),
    ('/* ===== ACS ARCH DETAIL (generated',
     '/* ===== END ACS ARCH DETAIL ===== */'),
    ('/* ===== ACS ARCH DETAIL BRIDGE',
     '/* ===== END ACS ARCH DETAIL BRIDGE ===== */'),
]

ENGINE_NEEDLES = (
    ("import * as THREE from 'three'", 'THREE import'),
    ('new THREE.Scene(', 'scene initialization'),
    ('new THREE.WebGLRenderer(', 'renderer initialization'),
    ('new THREE.PerspectiveCamera(', 'camera initialization'),
    ('renderer.setAnimationLoop', 'render loop'),
)

IMPORTMAP_THREE = '/vendor/three@0.160.0/build/three.module.js'
IMPORTMAP_ADDONS = '/vendor/three@0.160.0/examples/jsm/'

ENTRY_TAG_RX = re.compile(
    r'<script\b[^>]*\btype\s*=\s*"module"[^>]*\bsrc\s*=\s*"/app/main\.js"')
STYLESHEET_RX = re.compile(
    r'<link\b[^>]*\brel\s*=\s*"stylesheet"[^>]*\bhref\s*=\s*"([^"]+)"')
SRC_RX = re.compile(r'\bsrc\s*=\s*"([^"]+)"')
TYPE_RX = re.compile(r'\btype\s*=\s*"([^"]+)"')

# دالّة العرض: الفرع المُسرَّع وفرعه الاحتياطي. الاثنان انتقلا مع الشيفرة إلى
# وحدات /app/، ويُبحَث عنهما هناك — لا في الصفحة. (اليوم هما في
# public/app/ui/workspace-ui-wiring.js؛ الحارس لا يثبّت الملفّ بل يعدّ عبر
# الوحدات كلّها، فنقل الدالّة بين الملفّات لا يكسره ولا يخفيه.)
DISPATCHER = ('window.__ACS_PQ__&&window.__ACS_PQ__.composer'
              '&&!renderer.xr.isPresenting){window.__ACS_PQ__.composer'
              '.render();}')
DISPATCHER_FALLBACK = 'else{renderer.render(scene,camera);}'


# ═══════════════════════════════════════════════ عناصر الصفحة (مسح تسلسلي) ══
def script_elements(page):
    """عناصر <script> الحقيقية بمسح تسلسلي — لا regex عام.

    النصّ قد يحوي سلاسل تبدأ بـ`<script` داخل مواصفات JSON؛ المسح التسلسلي يقفز
    من نهاية كل عنصر إلى ما بعده فلا يرى ما بداخله.
    """
    out, i = [], 0
    while True:
        a = page.find('<script', i)
        if a < 0:
            return out
        ge = page.find('>', a)
        if ge < 0:
            return out
        e = page.find('</script>', ge)
        if e < 0:
            return out
        out.append({'attrs': page[a + 7:ge].strip(),
                    'body': page[ge + 1:e],
                    'line': page.count('\n', 0, a) + 1})
        i = e + 9


# ═══════════════════════════════════════════════════════ فحص القشرة وحدها ══
def check_page_text(page, size=None):
    """يفحص نصّ القشرة ويعيد قائمة أعطال — قائمة فارغة = قشرة سليمة.

    هذا الفحص عن الصفحة فقط. فحوص الشيفرة انتقلت إلى check_app_text()،
    وفحوص شجرة الوحدات إلى check_app_tree()؛ check_file() يجمع الثلاثة.
    """
    fails = []
    if size is None:
        size = len(page.encode('utf-8'))
    if size == 0:
        return ['public/index.html is EMPTY (0 bytes)']
    if size > MAX_BYTES:
        fails.append('public/index.html is %d bytes — ABOVE the shell maximum '
                     '%d. After F-09 the page is a shell; this size means '
                     'application code has been pasted back into it '
                     '(the pre-F-09 page was 1,863,894 bytes)'
                     % (size, MAX_BYTES))
    low = page.lower()
    for tag in ('<!doctype html', '<html', '</html>', '<body', '</body>'):
        if tag not in low:
            fails.append('missing basic HTML structure: %s' % tag)
    if 'id="app"' not in page and 'id="left"' not in page:
        fails.append('the ACS application root is missing')

    # خريطة الاستيراد ما زالت تُحلَّل JSON فعلاً وتشير إلى النسخة المثبّتة محلياً
    m = re.search(r'<script type="importmap">\s*(\{.*?\})\s*</script>',
                  page, re.S)
    if not m:
        fails.append('no <script type="importmap"> block')
    else:
        try:
            imap = json.loads(m.group(1))
            imports = imap.get('imports') or {}
            if imports.get('three') != IMPORTMAP_THREE:
                fails.append('importmap "three" does not point at the '
                             'pinned local vendor build')
            if imports.get('three/addons/') != IMPORTMAP_ADDONS:
                fails.append('importmap "three/addons/" does not point at '
                             'the local jsm tree')
        except ValueError as e:
            fails.append('importmap is not valid JSON: %s' % e)

    # نقطة الدخول ووسم التنسيق
    if not ENTRY_TAG_RX.search(page):
        fails.append('the module entry point <script type="module" '
                     'src="/app/main.js"> is missing — the shell would load '
                     'no application code at all')
    if not STYLESHEET_RX.search(page):
        fails.append('the <link rel="stylesheet"> to the application '
                     'stylesheet is missing')

    # لا سطر جافاسكربت قابل للتنفيذ داخل الصفحة (شرط CSP بلا 'unsafe-inline')
    for s in script_elements(page):
        has_src = bool(SRC_RX.search(s['attrs']))
        tm = TYPE_RX.search(s['attrs'])
        stype = tm.group(1) if tm else ''
        if has_src:
            if s['body'].strip():
                fails.append('the <script src> element at line %d also has an '
                             'inline body — inline JavaScript is refused by '
                             'the CSP' % s['line'])
            continue
        if stype != 'importmap':
            fails.append('executable inline <script%s> at line %d — after '
                         'F-11 the ONLY inline script allowed in the page is '
                         'type="importmap" (it cannot be external), and it is '
                         "permitted by a sha256 hash, not by 'unsafe-inline'"
                         % ((' type="%s"' % stype) if stype else '', s['line']))
        elif not s['body'].strip():
            fails.append('the importmap element at line %d is empty'
                         % s['line'])

    # لا تنسيق داخل الصفحة: لا كتلة <style> ولا سمة style="…"
    if '<style' in low:
        fails.append('a <style> block remains in the page — it would force '
                     "style-src 'unsafe-inline'; move it into "
                     'public/app/styles/app.css')
    sm = re.search(r'\sstyle\s*=\s*"', page)
    if sm:
        fails.append('an inline style="…" attribute remains at line %d — it '
                     "would force style-src 'unsafe-inline'; "
                     'tools/frontend_shell.js turns these into .acs-u-NN '
                     'classes' % (page.count('\n', 0, sm.start()) + 1))
    return fails


def check_references(page, public_dir):
    """كل مرجع في القشرة يُحلّ إلى ملفّ موجود وغير فارغ على القرص.

    فحص لم يكن ممكناً قبل F-09 (لم يكن هناك مرجع أصلاً). هو الذي يمنع الحالة
    الجديدة الوحيدة الخطرة: قشرة سليمة تماماً تشير إلى ملفّ لم يُنشر.
    """
    fails = []
    refs = []
    for s in script_elements(page):
        mm = SRC_RX.search(s['attrs'])
        if mm:
            refs.append((mm.group(1), 'script'))
    refs += [(mm.group(1), 'stylesheet') for mm in STYLESHEET_RX.finditer(page)]
    if not refs:
        fails.append('the shell references no external asset at all')
    for ref, kind in refs:
        if ref.startswith('data:'):
            continue
        if not ref.startswith('/'):
            fails.append('%s reference %r is not site-absolute' % (kind, ref))
            continue
        if ref.startswith('/vendor/'):
            continue                # يملؤه بناء Netlify، وله حارسه في vendor.sh
        p = os.path.join(public_dir, ref.lstrip('/').replace('/', os.sep))
        if not os.path.isfile(p):
            fails.append('%s reference %s does not exist on disk (%s) — the '
                         'shell would 404 in production' % (kind, ref, p))
        elif os.path.getsize(p) == 0:
            fails.append('%s reference %s exists but is EMPTY' % (kind, ref))
    return fails


# ═══════════════════════════════════════════ فحص شيفرة التطبيق (الوحدات) ═══
def check_app_text(app):
    """كل ما كان يُفحَص في نصّ الصفحة، يُفحَص الآن في نصّ الوحدات."""
    fails = []
    for needle, what in ENGINE_NEEDLES:
        if needle not in app:
            fails.append('the application modules lack %s' % what)
    for a, b in PAIRS:
        if app.count(b) != 1:
            fails.append('generated end-marker not exactly once across the app '
                         'modules (%d): %s' % (app.count(b), b))
            continue
        ia = app.find(a)
        if ia < 0:
            fails.append('generated begin-marker missing: %s' % a)
        elif ia > app.index(b):
            fails.append('marker pair out of order: %s' % a)
    if app.count(DISPATCHER) != 1:
        fails.append('render-loop dispatcher must appear exactly once across '
                     'the app modules (found %d)' % app.count(DISPATCHER))
    if DISPATCHER_FALLBACK not in app:
        fails.append('render-loop fallback branch is missing')
    if not re.search(r'window\.ACS\s*=\s*\{', app):
        fails.append('window.ACS is never initialised — the boot guard and '
                     'every window.ACS.* entry point would be undefined')
    return fails


def check_app_tree(app_dir, modules, load_order):
    """الشجرة نفسها: لا وحدة يتيمة، ولا استيراد لملفّ غير موجود، ولا وحدة ضخمة."""
    fails = []
    if not os.path.isdir(app_dir):
        return ['public/app/ does not exist — the application was never split']
    if not modules:
        return ['public/app/ contains no JavaScript module']

    expected = set(f for f in modules
                   if not f.startswith('boot/') and not f.startswith('styles/')
                   and f not in NOT_IMPORTED_BY_MAIN)
    declared = set(load_order)
    for orphan in sorted(expected - declared):
        fails.append('public/app/%s exists but public/app/main.js never '
                     'imports it — a module nothing loads is dead weight that '
                     'still passes every other check' % orphan)
    for missing in sorted(declared - set(modules)):
        fails.append('public/app/main.js imports ./%s but that file does not '
                     'exist' % missing)
    if len(load_order) != len(declared):
        fails.append('public/app/main.js imports the same module twice — '
                     'evaluation order is then ambiguous')

    for name in sorted(modules):
        n = len(modules[name].encode('utf-8'))
        if n > MODULE_SIZE_CAP and name not in OVERSIZE_ALLOWLIST:
            fails.append('public/app/%s is %d bytes — above the %d byte module '
                         'cap and NOT in OVERSIZE_ALLOWLIST. Split it, or add '
                         'it to the allow-list in tools/check_index_guard.py '
                         'with a written reason' % (name, n, MODULE_SIZE_CAP))
    for k in sorted(k for k in OVERSIZE_ALLOWLIST if k not in modules):
        fails.append('OVERSIZE_ALLOWLIST names %r which no longer exists — '
                     'remove the stale exemption' % k)
    return fails


# ═════════════════════════════════════════════════════════════ المُنسِّق ═════
def check_file(path):
    if not os.path.isfile(path):
        return ['public/index.html does not exist']
    size = os.path.getsize(path)
    if size == 0:
        return ['public/index.html is EMPTY (0 bytes)']
    with open(path, encoding='utf-8') as f:
        page = f.read()
    public_dir = os.path.dirname(os.path.abspath(path))
    fails = check_page_text(page, size)
    fails += check_references(page, public_dir)
    fails += check_app_text(A.app_text())
    fails += check_app_tree(A.APP, A.modules(), A.order())
    return fails


def main():
    path = sys.argv[1] if len(sys.argv) > 1 \
        else os.path.join('public', 'index.html')
    fails = check_file(path)
    if fails:
        for x in fails:
            print('INDEX GUARD FAILED: %s' % x)
        print('refusing to publish a broken application page.')
        sys.exit(1)
    with open(path, encoding='utf-8') as fh:
        page = fh.read()
    n_refs = len([1 for s in script_elements(page) if SRC_RX.search(s['attrs'])]
                 ) + len(STYLESHEET_RX.findall(page))
    sizes = {k: len(v.encode('utf-8')) for k, v in A.modules().items()}
    biggest = max(sizes, key=lambda k: sizes[k])
    print('✓ index guard: shell %d bytes (max %d) · %d referenced assets all '
          'resolve · zero inline JS, zero inline style · %d modules under '
          '/app/ (%d imported by main.js), largest %s at %d B (cap %d, '
          'allow-list empty) · importmap valid · engine init present · '
          'all %d generated block pairs intact across the modules'
          % (os.path.getsize(path), MAX_BYTES, n_refs, len(sizes),
             len(A.order()), biggest, sizes[biggest], MODULE_SIZE_CAP,
             len(PAIRS)))


if __name__ == '__main__':
    main()
