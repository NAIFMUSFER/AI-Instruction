# -*- coding: utf-8 -*-
"""حارس صفحة التطبيق — المرحلة 9.2، علاج إنتاجي دائم.

مصدر الحقيقة الوحيد لفحص سلامة public/index.html بنيوياً:
يستدعيه بناء Netlify قبل النشر (فشل الفحص = فشل البناء فلا يُنشر شيء مكسور)،
ويستدعيه تحقّق النشر مع اختبارات سلبية تثبت أن الحارس نفسه ليس عقيماً.

الفحوص بنيوية لا نصّية فقط: الحجم الأدنى للصفحة المولَّدة، استخراج خريطة
الاستيراد وتحليلها JSON فعلياً، وجود تهيئة المحرّك داخل سكربت الوحدة،
واكتمال كل أزواج الكتل المولَّدة وترتيبها وعدم تكرارها.
"""
import json
import os
import re

MIN_BYTES = 1000000     # الصفحة المولَّدة الكاملة ≈ 1.6MB — أي شيء دونها مبتور

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


def check_page_text(page, size=None):
    """يفحص نصّ الصفحة ويعيد قائمة أعطال — قائمة فارغة = سليم."""
    fails = []
    if size is None:
        size = len(page.encode('utf-8'))
    if size == 0:
        return ['public/index.html is EMPTY (0 bytes)']
    if size < MIN_BYTES:
        fails.append('public/index.html is %d bytes — below the generated '
                     'minimum %d' % (size, MIN_BYTES))
    low = page.lower()
    for tag in ('<!doctype html', '<html', '</html>', '<body', '</body>'):
        if tag not in low:
            fails.append('missing basic HTML structure: %s' % tag)
    if 'id="app"' not in page and 'id="left"' not in page:
        fails.append('the ACS application root is missing')
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
    mod = re.search(r'<script type="module">(.*?)</script>', page, re.S)
    if not mod:
        fails.append('no <script type="module"> application script')
    else:
        for needle, what in ENGINE_NEEDLES:
            if needle not in mod.group(1):
                fails.append('module script lacks %s' % what)
    for a, b in PAIRS:
        if page.count(b) != 1:
            fails.append('generated end-marker not exactly once: %s' % b)
            continue
        ia = page.find(a)
        if ia < 0:
            fails.append('generated begin-marker missing: %s' % a)
        elif ia > page.index(b):
            fails.append('marker pair out of order: %s' % a)
    disp = ('window.__ACS_PQ__&&window.__ACS_PQ__.composer'
            '&&!renderer.xr.isPresenting){window.__ACS_PQ__.composer'
            '.render();}')
    if page.count(disp) != 1:
        fails.append('render-loop dispatcher must appear exactly once')
    if 'else{renderer.render(scene,camera);}' not in page:
        fails.append('render-loop fallback branch is missing')
    return fails


def check_file(path):
    if not os.path.isfile(path):
        return ['public/index.html does not exist']
    size = os.path.getsize(path)
    if size == 0:
        return ['public/index.html is EMPTY (0 bytes)']
    with open(path, encoding='utf-8') as f:
        page = f.read()
    return check_page_text(page, size)


def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 \
        else os.path.join('public', 'index.html')
    fails = check_file(path)
    if fails:
        for x in fails:
            print('INDEX GUARD FAILED: %s' % x)
        print('refusing to publish a broken application page.')
        sys.exit(1)
    print('✓ index guard: %d bytes, importmap valid, engine init present, '
          'all %d generated block pairs intact'
          % (os.path.getsize(path), len(PAIRS)))


if __name__ == '__main__':
    main()
