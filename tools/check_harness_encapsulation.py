# -*- coding: utf-8 -*-
"""حارس تغليف المحرّك — يمنع المِرقاب من لمس نطاق الوحدة.

حالة المحرّك (scene, renderer, camera, orbit, model) محصورة عمداً داخل سكربت
الوحدة. مِرقاب النشر يعمل عبر جسور القراءة العامة وحدها. حادثة حقيقية:
تسلّل `scene.updateMatrixWorld(...)` و`model.traverse(...)` إلى داخل
page.evaluate فانفجر `ReferenceError: scene is not defined` على النشر الحقيقي
بينما كان التطبيق سليماً.

هذا الحارس يجرّد التعليقات والنصوص ثم يفحص جسم كل page.evaluate: أي معرّف من
نطاق الوحدة يُرفض. الحلّ الصحيح دائماً جسر قراءة ضيّق، لا رفع المتغيّر إلى
النطاق العام.

    python3 tools/check_harness_encapsulation.py [<root>]
"""
import io
import os
import re
import sys

FORBIDDEN = ('scene', 'renderer', 'camera', 'orbit', 'controls', 'model',
             'sun', 'pmrem', 'sky', 'matCache', 'player')
HARNESSES = (
    os.path.join('tests', 'deploy', 'verify_page_boot.js'),
    os.path.join('tests', 'deploy', 'lib_viewport_pixels.js'),
    os.path.join('tests', 'phase9_2', 'capture_reference_92.js'),
    os.path.join('tests', 'phase9_1', 'capture_reference.js'),
)


def strip_noise(src):
    """يزيل التعليقات والسلاسل النصية حتى لا يُحاسَب شرحٌ على أنه كود."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            out.append(' ')
        elif c == '/' and nxt == '/':
            j = src.find('\n', i)
            i = n if j < 0 else j
            out.append(' ')
        elif c in '"\'`':
            q, j = c, i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == q:
                    break
                j += 1
            i = j + 1
            out.append('""')
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def evaluate_bodies(src):
    """كل جسم page.evaluate / pg.evaluate / waitForFunction بالتوازن الأقواسي."""
    bodies = []
    for m in re.finditer(r'\b\w+\.(?:evaluate|evaluateHandle|waitForFunction)'
                         r'\s*\(', src):
        i = m.end()
        depth, j = 1, i
        while j < len(src) and depth:
            if src[j] == '(':
                depth += 1
            elif src[j] == ')':
                depth -= 1
            j += 1
        bodies.append((m.start(), src[i:j - 1]))
    return bodies


def check(root):
    fails = []
    scanned = 0
    for rel in HARNESSES:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        with io.open(path, encoding='utf-8') as fh:
            src = strip_noise(fh.read())
        for pos, body in evaluate_bodies(src):
            scanned += 1
            for ident in FORBIDDEN:
                for hit in re.finditer(r'(?<![\w.$])' + ident + r'(?![\w$])',
                                       body):
                    before = body[max(0, hit.start() - 24):hit.start()]
                    if 'window.ACS' in before or 'ACS.' in before:
                        continue
                    line = src.count('\n', 0, pos + hit.start()) + 1
                    fails.append(
                        '%s: page.evaluate body reaches module-scoped %r '
                        '(near line %d). Engine state is intentionally not '
                        'global — add a narrow read-only bridge on '
                        'window.ACS instead.' % (rel, ident, line))
    return fails, scanned


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    fails, scanned = check(root)
    if fails:
        print('HARNESS ENCAPSULATION GATE FAILED')
        for x in fails:
            print('  ✗ %s' % x)
        sys.exit(1)
    print('✓ harness encapsulation: %d evaluate bodies use public bridges '
          'only; module scope is untouched' % scanned)


if __name__ == '__main__':
    main()
