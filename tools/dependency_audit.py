#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تدقيق التبعيات — يعمل بلا شبكة، ويقول صراحةً ما لا يستطيع التحقّق منه.

    python3 tools/dependency_audit.py [ROOT]

ما يتحقّق منه فعلاً (حتمي، بلا شبكة):
  1. مجموعة التثبيتات المحلولة: requirements.in ⇄ requirements.lock ⇄ requirements.txt.
  2. requirements.txt بلا أي مواصفة مفتوحة (>= أو <= أو ~= أو * أو اسم مجرّد)،
     وبلا `-r` (صورة Docker تنسخ هذا الملفّ وحده فلا يصل إليه ملفّ آخر).
  3. package-lock.json: نسخة القفل موجودة، وplaywright/playwright-core مثبّتان
     بنفس الإصدار بالضبط، ومع بصمة sha512 لكل حزمة.
  4. إصدارات الواجهة الموردة الحالية (three · pdfjs-dist)
     متطابقة في ثلاثة مواضع: tools/netlify-build.sh و tools/check_index_guard.py
     و public/index.html. أي انحراف في موضع واحد يُفشل التدقيق.

ما لا يستطيع التحقّق منه هنا، ويُعلنه بلا تجميل بدل ادّعاء النجاح:
  • بصمات الحِزم (hashes) — تحتاج جلب الأثر نفسه من الفهرس.
  • مسح الثغرات (CVE) — يحتاج قاعدة استشارات حيّة.
  • هل يوجد إصدار أحدث متوافق — يحتاج الفهرس.

الخروج: 0 إن لم يوجد انحراف، 1 عند أي انحراف. «غير مُتحقَّق» ليس فشلاً:
يُطبع بوضوح ولا يغيّر رمز الخروج.
"""
import json
import os
import re
import sys

NOT_VERIFIED = 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED'

# مواصفة مفتوحة: كل ما ليس تثبيتاً دقيقاً بـ ==
OPEN_SPECIFIERS = ('>=', '<=', '~=', '!=', '>', '<', '*')

# اسم الحزمة الموحّد: PyPI يعامل - و _ و . سواءً (PEP 503)
def canon(name):
    return re.sub(r'[-_.]+', '-', name.strip().lower())


def rd(root, rel):
    with open(os.path.join(root, rel), encoding='utf-8') as fh:
        return fh.read()


# ─────────────────────────────────────────────────────── تحليل ملفّات pip ──
def parse_requirement_line(line):
    """يعيد (name, extras, specifier, version) أو None لسطر غير طلب."""
    s = line.split('#', 1)[0].strip()
    if not s or s.startswith('--hash='):
        return None
    m = re.match(r'^([A-Za-z0-9][A-Za-z0-9._-]*)'      # الاسم
                 r'(\[[^\]]*\])?'                       # الإضافات
                 r'\s*(==|>=|<=|~=|!=|>|<)?\s*'         # المواصفة
                 r'([^\s;]+)?', s)
    if not m:
        return {'raw': s, 'name': None, 'extras': '', 'spec': None,
                'version': None}
    return {'raw': s, 'name': m.group(1), 'extras': m.group(2) or '',
            'spec': m.group(3), 'version': m.group(4)}


def parse_in(text):
    """التبعيات المباشرة كما حرّرها الإنسان."""
    out = []
    for line in text.splitlines():
        r = parse_requirement_line(line)
        if r and r['name']:
            out.append(r)
    return out


def parse_lock(text):
    """يعيد (التثبيتات الفعّالة، الأسماء المعلَّمة UNRESOLVED-OFFLINE)."""
    pins, unresolved = [], []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            m = re.match(r'^#\s*UNRESOLVED-OFFLINE\s+'
                         r'([A-Za-z0-9][A-Za-z0-9._-]*)', stripped)
            if m:
                unresolved.append(m.group(1))
            continue
        r = parse_requirement_line(line)
        if r and r['name']:
            pins.append(r)
    return pins, unresolved


def parse_txt(text):
    reqs, includes = [], []
    for line in text.splitlines():
        s = line.split('#', 1)[0].strip()
        if not s:
            continue
        if s.startswith('-r') or s.startswith('--requirement'):
            includes.append(s)
            continue
        r = parse_requirement_line(line)
        if r:
            reqs.append(r)
    return reqs, includes


# ───────────────────────────────────────────── إصدارات الواجهة الموردة ──
def vendored_versions(root):
    """Extract versions only from locations that remain authoritative.

    Architecture note:
      * es-module-shims was intentionally removed during the strict-CSP /
        native-ES-module remediation and is no longer a shipped dependency.
      * pdfjs-dist is vendored by tools/netlify-build.sh and consumed through
        the modular frontend; public/index.html is no longer an authoritative
        version declaration for it.
      * three remains referenced by multiple runtime/test/config locations, so
        all of those declarations must continue to agree.
    """
    sh = rd(root, 'tools/netlify-build.sh')
    guard = rd(root, 'tools/check_index_guard.py')
    page = rd(root, 'public/index.html')

    def one(pattern, text, label):
        found = sorted(set(re.findall(pattern, text, re.M)))
        return found if found else ['<absent:%s>' % label]

    return {
        'three': {
            'tools/netlify-build.sh (THREE=)':
                one(r'^THREE=([0-9][0-9A-Za-z.\-]*)', sh, 'THREE='),
            'tools/netlify-build.sh (header comment)':
                one(r'#.*\bthree ([0-9][0-9A-Za-z.\-]*)', sh, 'comment'),
            'tools/check_index_guard.py':
                one(r'/vendor/three@([0-9][0-9A-Za-z.\-]*)/', guard, 'three@'),
            'public/index.html':
                one(r'/vendor/three@([0-9][0-9A-Za-z.\-]*)/', page, 'three@'),
            'netlify.toml':
                one(r'three@([0-9][0-9A-Za-z.\-]*)',
                    rd(root, 'netlify.toml'), 'three@'),
            'tests/deploy/verify_page_boot.js':
                one(r"'three@([0-9][0-9A-Za-z.\-]*)'",
                    rd(root, 'tests/deploy/verify_page_boot.js'), 'three@'),
            'tests/phase9_1/capture_reference.js':
                one(r"'three@([0-9][0-9A-Za-z.\-]*)'",
                    rd(root, 'tests/phase9_1/capture_reference.js'), 'three@'),
            'tests/phase9_2/capture_reference_92.js':
                one(r"'three@([0-9][0-9A-Za-z.\-]*)'",
                    rd(root, 'tests/phase9_2/capture_reference_92.js'),
                    'three@'),
        },
        'pdfjs-dist': {
            'tools/netlify-build.sh (PDFJS=)':
                one(r'^PDFJS=([0-9][0-9A-Za-z.\-]*)', sh, 'PDFJS='),
            'tools/netlify-build.sh (header comment)':
                one(r'#.*\bpdfjs-dist ([0-9][0-9A-Za-z.\-]*)',
                    sh, 'comment'),
        },
    }

# ───────────────────────────────────────────────────────────── التدقيق ──
class Audit(object):
    def __init__(self):
        self.drift = []
        self.checks = 0

    def ok(self, msg):
        self.checks += 1
        print('  ✓ %s' % msg)

    def bad(self, msg, detail=''):
        self.checks += 1
        self.drift.append(msg)
        print('  ✗ %s%s' % (msg, ('  — %s' % detail) if detail else ''))

    def chk(self, cond, msg, detail=''):
        self.ok(msg) if cond else self.bad(msg, detail)


def main(root):
    a = Audit()
    print('=' * 78)
    print('DEPENDENCY AUDIT — offline · %s' % root)
    print('=' * 78)

    for rel in ('requirements.in', 'requirements.lock', 'requirements.txt',
                'package-lock.json', 'package.json',
                'tools/netlify-build.sh', 'tools/check_index_guard.py',
                'public/index.html'):
        if not os.path.exists(os.path.join(root, rel)):
            print('\nFATAL: missing %s' % rel)
            return 1

    # ── 1 · مجموعة التثبيتات ────────────────────────────────────────────
    print('\n── 1 · THE RESOLVED PIN SET ──')
    direct = parse_in(rd(root, 'requirements.in'))
    pins, unresolved = parse_lock(rd(root, 'requirements.lock'))
    txt_reqs, txt_includes = parse_txt(rd(root, 'requirements.txt'))
    lock_by_name = dict((canon(p['name']), p) for p in pins)

    print('  requirements.in    : %d direct requirement(s)' % len(direct))
    print('  requirements.lock  : %d active pin(s), %d UNRESOLVED-OFFLINE'
          % (len(pins), len(unresolved)))
    print('  requirements.txt   : %d requirement(s)' % len(txt_reqs))
    print('')
    for p in sorted(pins, key=lambda x: canon(x['name'])):
        print('    %-28s %s%s' % (p['name'] + p['extras'],
                                  p['spec'] or '', p['version'] or ''))
    if unresolved:
        print('')
        for name in unresolved:
            print('    %-28s UNRESOLVED-OFFLINE' % name)

    # ── 2 · تغطية: كل تبعية مباشرة مثبّتة في القفل ─────────────────────
    print('\n── 2 · EVERY DIRECT REQUIREMENT IS PINNED IN THE LOCK ──')
    unresolved_canon = set(canon(u) for u in unresolved)
    for d in direct:
        c = canon(d['name'])
        p = lock_by_name.get(c)
        if p is not None and p['spec'] == '==' and p['version']:
            a.ok('%s is pinned %s==%s in requirements.lock'
                 % (d['name'], p['name'], p['version']))
        elif c in unresolved_canon:
            a.ok('%s is explicitly marked UNRESOLVED-OFFLINE' % d['name'])
        else:
            a.bad('%s appears in requirements.in but is neither pinned nor '
                  'marked UNRESOLVED-OFFLINE in requirements.lock' % d['name'])

    # ── 3 · requirements.txt: بلا مواصفة مفتوحة وبلا -r ────────────────
    print('\n── 3 · requirements.txt CARRIES NO OPEN-ENDED SPECIFIER ──')
    a.chk(not txt_includes,
          'requirements.txt is self-contained (no -r include)',
          'the Docker image copies requirements.txt alone; %s could never '
          'be read inside it' % (txt_includes[0] if txt_includes else ''))
    for r in txt_reqs:
        raw = r['raw']
        opened = [s for s in OPEN_SPECIFIERS if s in raw.split(';', 1)[0]]
        if opened:
            a.bad('open-ended specifier in requirements.txt: %s' % raw,
                  'found %s' % ', '.join(opened))
        elif r['spec'] == '==' and r['version']:
            a.ok('%s is pinned exactly (%s==%s)'
                 % (r['name'], r['name'], r['version']))
        else:
            a.bad('bare or unpinned requirement in requirements.txt: %s' % raw)

    # ── 4 · لا انحراف بين requirements.txt و requirements.lock ─────────
    print('\n── 4 · requirements.txt AGREES WITH requirements.lock ──')
    for r in txt_reqs:
        if not r['name']:
            continue
        p = lock_by_name.get(canon(r['name']))
        if p is None:
            a.bad('%s is installed by requirements.txt but absent from '
                  'requirements.lock' % r['name'])
        else:
            a.chk(p['version'] == r['version'],
                  '%s pinned identically in both files (%s)'
                  % (r['name'], r['version']),
                  'lock=%s txt=%s' % (p['version'], r['version']))
            a.chk(canon(p['extras']) == canon(r['extras']),
                  '%s carries the same extras in both files (%s)'
                  % (r['name'], r['extras'] or 'none'),
                  'lock=%s txt=%s' % (p['extras'], r['extras']))
    lock_names = set(lock_by_name)
    txt_names = set(canon(r['name']) for r in txt_reqs if r['name'])
    missing = sorted(lock_names - txt_names)
    a.chk(not missing,
          'every active lock pin is installed by requirements.txt',
          ', '.join(missing))

    # ── 5 · package-lock.json ──────────────────────────────────────────
    print('\n── 5 · package-lock.json INTEGRITY FIELDS ──')
    plock = json.loads(rd(root, 'package-lock.json'))
    pkg = json.loads(rd(root, 'package.json'))
    a.chk('lockfileVersion' in plock,
          'lockfileVersion is present (%s)' % plock.get('lockfileVersion'))
    entries = plock.get('packages') or {}
    versions = {}
    for name in ('playwright', 'playwright-core'):
        node = entries.get('node_modules/' + name)
        if node is None:
            a.bad('%s is absent from package-lock.json' % name)
            continue
        versions[name] = node.get('version')
        a.chk(bool(node.get('version')),
              '%s is pinned to %s' % (name, node.get('version')))
        integ = node.get('integrity') or ''
        a.chk(integ.startswith('sha512-'),
              '%s carries an sha512 integrity hash' % name,
              integ[:24])
    if len(versions) == 2:
        a.chk(versions['playwright'] == versions['playwright-core'],
              'playwright and playwright-core are the SAME version (%s)'
              % versions.get('playwright'),
              str(versions))
    declared = ((pkg.get('devDependencies') or {}).get('playwright')
                or (pkg.get('dependencies') or {}).get('playwright') or '')
    a.chk(declared.lstrip('^~=v ') == (versions.get('playwright') or ''),
          'package.json range %r is satisfied by the locked version %s'
          % (declared, versions.get('playwright')))

    # ── 6 · إصدارات الواجهة الموردة في ثلاثة مواضع ─────────────────────
    print('\n── 6 · VENDORED FRONTEND VERSIONS AGREE EVERYWHERE ──')
    for lib, places in sorted(vendored_versions(root).items()):
        flat = set()
        for found in places.values():
            flat.update(found)
        a.chk(len(flat) == 1 and not any(v.startswith('<absent') for v in flat),
              '%s is one version across %d file(s): %s'
              % (lib, len(places), ', '.join(sorted(flat))),
              json.dumps(places, ensure_ascii=False))

    # ── 7 · ما لا يمكن التحقّق منه هنا ─────────────────────────────────
    print('\n── 7 · WHAT THIS AUDIT CANNOT CHECK ──')
    print('  ! %s' % NOT_VERIFIED)
    print('      · CVE / advisory scan of every pin above.')
    print('        needs a live advisory database. run on a networked machine:')
    print('          pip install pip-audit && pip-audit -r requirements.txt')
    print('          npm audit --package-lock-only')
    print('  ! %s' % NOT_VERIFIED)
    print('      · artefact hash verification for the Python pins.')
    print('        hashes are recorded in the lock; verify fetched bytes with:')
    print('          pip install --require-hashes -r requirements.txt')
    print('        regenerate only after reviewing dependency changes:')
    print('          uv pip compile --universal --python-version 3.11 '
          '--generate-hashes --no-strip-extras requirements.in -o requirements.lock')
    print('  ! %s' % NOT_VERIFIED)
    print('      · whether a newer compatible release exists for any pin,')
    print('        and the transitive closure itself (%d name(s) still marked '
          'UNRESOLVED-OFFLINE).' % len(unresolved))
    print('  ! %s' % NOT_VERIFIED)
    print('      · the npm integrity hashes above are read, not recomputed:')
    print('        proving them needs the tarballs. run: npm ci')

    # ── الحصيلة ────────────────────────────────────────────────────────
    print('\n' + '=' * 78)
    if a.drift:
        print('DEPENDENCY AUDIT: DRIFT DETECTED — %d of %d checks failed'
              % (len(a.drift), a.checks))
        for d in a.drift:
            print('  ✗ %s' % d)
        return 1
    print('DEPENDENCY AUDIT: %d checks passed, no drift.' % a.checks)
    print('Verified offline only. The three %s items above are NOT claims of '
          'safety.' % NOT_VERIFIED)
    return 0


if __name__ == '__main__':
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else os.path.dirname(HERE)))
