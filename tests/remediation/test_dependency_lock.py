# -*- coding: utf-8 -*-
"""عقد تثبيت التبعيات — «ما يُركَّب في الإنتاج هو ما يقوله المستودع، بالضبط».

العطل الذي يمنعه هذا الملفّ: كانت requirements.txt تحمل مواصفات مفتوحة
(fastapi>=0.110 …)، فكل `docker build` يحلّ إلى أحدث ما نُشر ذلك اليوم. صورتان
مبنيّتان من نفس الالتزام (commit) تحملان مكتبات مختلفة، فعطل الإنتاج لا يمكن
إعادة إنتاجه محلياً، والترقية تحدث بلا قرار ولا اختبار ولا سجلّ.

العقد المفروض هنا، حتمياً وبلا شبكة:

  1. الملفّان requirements.in و requirements.lock موجودان ويُحلَّلان.
  2. كل تبعية مباشرة في requirements.in لها في requirements.lock إمّا تثبيت
     == دقيق، وإمّا علامة UNRESOLVED-OFFLINE صريحة. لا شيء يمرّ بصمت.
  3. requirements.txt بلا أي مواصفة مفتوحة (>= ~= * أو اسم مجرّد)، ولا ينحرف
     عن requirements.lock، ويبقى صالحاً لمسار Docker: الصورة تنسخ
     `requirements.txt` وحده، فسطر `-r requirements.lock` كان سيكسر البناء.
  4. package-lock.json: نسخة قفل معلنة، وplaywright وplaywright-core بنفس
     الإصدار الذي يسمح به مدى package.json، ومع بصمة sha512 لكل منهما.
  5. إصدارات الواجهة الموردة الثلاثة متطابقة في كل موضع تُذكر فيه — رفع الرقم
     في مكان واحد دون البقية يُفشل هذا الاختبار قبل أن يصل إلى النشر.
  6. مدخل تدقيق التبعيات موجود وقابل للتنفيذ.

هذا الملفّ لا يستورد tools/dependency_audit.py عمداً: أداة تفحص نفسها ليست
تحقّقاً. التحليل هنا مستقلّ، فإن أخطأت الأداة ظهر الخلاف بدل أن يختفي.

لا يتحقّق هذا الملفّ من: البصمات، ولا الثغرات، ولا وجود الإصدارات على الفهرس.
تلك تحتاج شبكة، وتُعلن NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED هناك.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def rd(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def canon(name):
    """توحيد اسم حزمة PyPI (PEP 503): - و _ و . سواء."""
    return re.sub(r'[-_.]+', '-', (name or '').strip().lower())


REQ_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]*)'
                    r'(\[[^\]]*\])?'
                    r'\s*(==|>=|<=|~=|!=|>|<)?\s*'
                    r'([^\s;]+)?')
OPEN_TOKENS = ('>=', '<=', '~=', '!=', '>', '<', '*')


def req_lines(text):
    """الأسطر الفعّالة (غير المعلَّقة) المحلَّلة كطلبات pip."""
    out = []
    for raw in text.splitlines():
        s = raw.split('#', 1)[0].strip()
        if not s or s.startswith('--hash='):
            continue
        if s.startswith('-'):
            out.append({'raw': s, 'name': None, 'extras': '', 'spec': None,
                        'version': None, 'option': True})
            continue
        m = REQ_RE.match(s)
        out.append({'raw': s, 'name': m.group(1) if m else None,
                    'extras': (m.group(2) or '') if m else '',
                    'spec': m.group(3) if m else None,
                    'version': m.group(4) if m else None, 'option': False})
    return out


def unresolved_names(text):
    names = []
    for raw in text.splitlines():
        m = re.match(r'^#\s*UNRESOLVED-OFFLINE\s+'
                     r'([A-Za-z0-9][A-Za-z0-9._-]*)', raw.strip())
        if m:
            names.append(m.group(1))
    return names


# ═════════════════════════════════════ أ · الملفّان موجودان ويُحلَّلان ═══════
print('\n── أ · THE TWO-FILE DISCIPLINE EXISTS ──')

chk('requirements.in exists', exists('requirements.in'))
chk('requirements.lock exists', exists('requirements.lock'))
chk('requirements.txt exists', exists('requirements.txt'))
if not (exists('requirements.in') and exists('requirements.lock')
        and exists('requirements.txt')):
    print('\nDEPENDENCY LOCK CONTRACT: cannot continue without the files.')
    sys.exit(1)

IN_TXT = rd('requirements.in')
LOCK_TXT = rd('requirements.lock')
TXT_TXT = rd('requirements.txt')

direct = [r for r in req_lines(IN_TXT) if not r['option']]
lock_active = [r for r in req_lines(LOCK_TXT) if not r['option']]
lock_unres = unresolved_names(LOCK_TXT)
txt_reqs = [r for r in req_lines(TXT_TXT) if not r['option']]
txt_opts = [r for r in req_lines(TXT_TXT) if r['option']]

chk('requirements.in parses into at least one direct requirement',
    len(direct) >= 1, 'parsed %d' % len(direct))
chk('every parsed line of requirements.in has a package name',
    all(r['name'] for r in direct),
    str([r['raw'] for r in direct if not r['name']]))
chk('requirements.lock parses (%d active pin(s), %d UNRESOLVED-OFFLINE)'
    % (len(lock_active), len(lock_unres)),
    bool(lock_active) or bool(lock_unres))
chk('every active line of requirements.lock is an exact == pin',
    all(r['spec'] == '==' and r['version'] for r in lock_active),
    str([r['raw'] for r in lock_active if r['spec'] != '==']))
chk('reviewed direct dependencies are pinned explicitly before resolution',
    all(r['spec'] == '==' and r['version'] for r in direct))

print('\n── ب · UNIVERSAL LOCK WITH REAL DISTRIBUTION HASHES ──')
head = LOCK_TXT[:6000]
chk('the header records universal Python 3.11 resolution with hashes',
    all(flag in head for flag in ('uv pip compile', '--universal',
        '--python-version 3.11', '--generate-hashes', 'requirements.in')))
chk('no dependency is left unresolved', not lock_unres)
blocks = re.split(r'(?m)(?=^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?==)',
                  LOCK_TXT)[1:]
chk('every active requirement has its own hashed block',
    len(blocks) == len(lock_active)
    and all(re.search(r'--hash=sha256:[a-f0-9]{64}\b', block) for block in blocks))
chk('every resolved block records why the package is installed',
    all(re.search(r'^\s*#\s*via\b', block, re.M) for block in blocks))
chk('deployment requirements are byte-identical to the reviewed lock',
    TXT_TXT == LOCK_TXT)

# ═══════════════════════ ج · كل تبعية مباشرة مثبّتة أو معلَّمة صراحةً ═══════
print('\n── ج · EVERY DIRECT REQUIREMENT IS PINNED OR EXPLICITLY UNRESOLVED ──')
lock_by_name = dict((canon(r['name']), r) for r in lock_active)
unres_canon = set(canon(n) for n in lock_unres)
for d in direct:
    c = canon(d['name'])
    pin = lock_by_name.get(c)
    if pin is not None:
        chk('%s is pinned == in requirements.lock (%s)'
            % (d['name'], pin['version']),
            pin['spec'] == '==' and bool(pin['version']))
        chk('%s keeps its extras in the lock (%s)'
            % (d['name'], d['extras'] or 'none'),
            canon(pin['extras']) == canon(d['extras']),
            'in=%s lock=%s' % (d['extras'], pin['extras']))
    else:
        chk('%s is explicitly marked UNRESOLVED-OFFLINE in requirements.lock'
            % d['name'], c in unres_canon,
            'neither pinned nor marked — it would resolve silently at build')

chk('no name is both pinned and marked UNRESOLVED-OFFLINE',
    not (set(lock_by_name) & unres_canon),
    str(sorted(set(lock_by_name) & unres_canon)))
chk('every UNRESOLVED-OFFLINE entry is inert (commented out, pip never '
    'reads it)',
    all(canon(n) not in set(canon(r['name']) for r in lock_active)
        for n in lock_unres))

# ══════════════════ د · requirements.txt بلا مواصفة مفتوحة ولا انحراف ══════
print('\n── د · requirements.txt CARRIES NO OPEN-ENDED SPECIFIER ──')
is_include_form = (len(txt_reqs) == 0 and len(txt_opts) == 1
                   and 'requirements.lock' in txt_opts[0]['raw'])
chk('requirements.txt is either `-r requirements.lock` or only == pins',
    is_include_form or (txt_reqs and all(r['spec'] == '=='
                                         and r['version'] for r in txt_reqs)),
    str([r['raw'] for r in txt_reqs if r['spec'] != '==']))
for r in txt_reqs:
    found = [t for t in OPEN_TOKENS if t in r['raw'].split(';', 1)[0]]
    chk('no open-ended specifier in %r' % r['raw'], not found,
        'found %s' % ', '.join(found))
    chk('%r is not a bare package name' % r['raw'],
        bool(r['spec'] and r['version']))

# مسار Docker: الصورة تنسخ requirements.txt وحده — أي `-r` فيه يكسر البناء
print('\n── هـ · THE DOCKER INSTALL PATH STAYS VALID ──')
docker = rd('Dockerfile')
copied = set()
for line in docker.splitlines():
    s = line.strip()
    if s.startswith('COPY'):
        copied.update(s.split()[1:])
chk('the Dockerfile still copies requirements.txt',
    'requirements.txt' in copied)
chk('the Dockerfile still installs from requirements.txt',
    re.search(r'pip install[^\n]*-r\s+requirements\.txt', docker) is not None)
for opt in txt_opts:
    m = re.match(r'^(?:-r|--requirement)[=\s]+(\S+)', opt['raw'])
    target = m.group(1) if m else None
    chk('requirements.txt includes %r and that file IS copied into the image'
        % target, target in copied,
        'the image copies requirements.txt alone; %r would not exist inside '
        'it and `pip install` would fail' % target)
chk('requirements.txt needs no file the image does not copy',
    all(re.match(r'^(?:-r|--requirement)[=\s]+(\S+)', o['raw'])
        and re.match(r'^(?:-r|--requirement)[=\s]+(\S+)',
                     o['raw']).group(1) in copied for o in txt_opts))

print('\n── و · requirements.txt AND requirements.lock CANNOT DRIFT ──')
for r in txt_reqs:
    pin = lock_by_name.get(canon(r['name']))
    chk('%s installed by requirements.txt is present in the lock' % r['name'],
        pin is not None)
    if pin:
        chk('%s: requirements.txt %s == requirements.lock %s'
            % (r['name'], r['version'], pin['version']),
            r['version'] == pin['version'])
        chk('%s: same extras in both files (%s)'
            % (r['name'], r['extras'] or 'none'),
            canon(r['extras']) == canon(pin['extras']),
            'txt=%s lock=%s' % (r['extras'], pin['extras']))
if not is_include_form:
    missing = sorted(set(lock_by_name)
                     - set(canon(r['name']) for r in txt_reqs))
    chk('every active lock pin is actually installed by requirements.txt',
        not missing, ', '.join(missing))
    direct_missing = sorted(set(canon(d['name']) for d in direct)
                            - set(canon(r['name']) for r in txt_reqs)
                            - unres_canon)
    chk('every direct requirement reaches the image', not direct_missing,
        ', '.join(direct_missing))

# ═══════════════════════════════════════ ز · قفل npm وبصماته ═══════════════
print('\n── ز · package-lock.json IS A REAL LOCK ──')
chk('package-lock.json exists', exists('package-lock.json'))
chk('package.json exists', exists('package.json'))
plock = json.loads(rd('package-lock.json'))
pkg = json.loads(rd('package.json'))
chk('lockfileVersion is present (%s)' % plock.get('lockfileVersion'),
    'lockfileVersion' in plock)
entries = plock.get('packages') or {}
locked = {}
for name in ('playwright', 'playwright-core'):
    node = entries.get('node_modules/' + name)
    chk('%s is present in package-lock.json' % name, node is not None)
    if node is None:
        continue
    locked[name] = node.get('version')
    chk('%s is pinned to an exact version (%s)' % (name, node.get('version')),
        bool(re.match(r'^\d+\.\d+\.\d+', str(node.get('version') or ''))))
    integ = str(node.get('integrity') or '')
    chk('%s carries an integrity hash and it is sha512' % name,
        integ.startswith('sha512-') and len(integ) > 40, integ[:20])
chk('playwright and playwright-core are locked to the SAME exact version (%s)'
    % locked.get('playwright'),
    len(locked) == 2 and locked['playwright'] == locked['playwright-core'],
    str(locked))

declared = ((pkg.get('devDependencies') or {}).get('playwright')
            or (pkg.get('dependencies') or {}).get('playwright') or '')


def semver_allows(rng, version):
    """يكفي هنا دعم ^ و ~ و = والرقم المجرّد — وهو كل ما يستعمله المستودع."""
    rng = (rng or '').strip()
    m = re.match(r'^([\^~=]?)v?(\d+)\.(\d+)\.(\d+)', rng)
    v = re.match(r'^(\d+)\.(\d+)\.(\d+)', version or '')
    if not m or not v:
        return False
    op = m.group(1)
    base = tuple(int(x) for x in m.groups()[1:])
    got = tuple(int(x) for x in v.groups())
    if op in ('', '='):
        return got == base
    if got < base:
        return False
    if op == '^':
        return got[0] == base[0] if base[0] else got[:2] == base[:2]
    if op == '~':
        return got[:2] == base[:2]
    return False


chk('package.json declares playwright with a range (%r)' % declared,
    bool(declared))
chk('the locked playwright version %s satisfies package.json %r'
    % (locked.get('playwright'), declared),
    semver_allows(declared, locked.get('playwright') or ''))
chk('the locked version is the exact version package.json names (%r)'
    % declared,
    (declared.lstrip('^~=v ') == (locked.get('playwright') or '')),
    'a caret range that has drifted from its floor means `npm install` and '
    '`npm ci` can disagree')

# ══════════════════════ ح · إصدارات الواجهة الموردة لا تنحرف ═══════════════
print('\n── ح · THE VENDORED FRONTEND VERSIONS AGREE IN EVERY PLACE ──')
sh = rd('tools/netlify-build.sh')
guard = rd('tools/check_index_guard.py')
# F-09 — القشرة تحمل خريطة الاستيراد (three)، والوحدات تحمل الاستيراد الديناميكي
# (pdf.js). كلاهما شيفرة منشورة، فالمصدر الواحد هنا هو tools/app_source.py:
# القشرة + الوحدات + ورقة الأنماط. قراءة الصفحة وحدها كانت ستفقد pdf.js صامتاً.
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import app_source as AS                                           # noqa: E402
shell = AS.shell()
page = AS.page_text() + '\n' + AS.css_text()

SOURCES = {
    'three': [
        ('tools/netlify-build.sh THREE=', sh, r'^THREE=([0-9][\w.\-]*)'),
        ('tools/netlify-build.sh header comment', sh,
         r'#.*\bthree ([0-9][\w.\-]*)'),
        ('tools/check_index_guard.py IMPORTMAP_THREE', guard,
         r'/vendor/three@([0-9][\w.\-]*)/build/'),
        ('tools/check_index_guard.py IMPORTMAP_ADDONS', guard,
         r'/vendor/three@([0-9][\w.\-]*)/examples/'),
        ('public/index.html importmap', shell,
         r'/vendor/three@([0-9][\w.\-]*)/'),
        # المسارات المطلقة داخل أدوات التحقّق: رفع الرقم في netlify-build.sh وحده
        # يجعل هذه الملفّات تقرأ مساراً غير موجود، فتفشل بعد النشر لا قبله
        ('netlify.toml build comment', rd('netlify.toml'),
         r'three@([0-9][\w.\-]*)'),
        ('tests/deploy/verify_page_boot.js', rd('tests/deploy/verify_page_boot.js'),
         r"'three@([0-9][\w.\-]*)'"),
        ('tests/phase9_1/capture_reference.js',
         rd('tests/phase9_1/capture_reference.js'), r"'three@([0-9][\w.\-]*)'"),
        ('tests/phase9_2/capture_reference_92.js',
         rd('tests/phase9_2/capture_reference_92.js'),
         r"'three@([0-9][\w.\-]*)'"),
    ],
    # F-11 — es-module-shims حُذف: خرائط الاستيراد أصلية في كل متصفّح مدعوم،
    # والمُلطِّف كان يقرأ الوسوم ويقيّم نصّاً، وهو ما كان يفرض 'unsafe-inline'.
    # لم يعد له موضع في الواجهة المشحونة، فلم يعد له عقدُ إصدار يُطابَق: عقده
    # الآن هو الغياب، ويُفحَص أدناه فحصاً موجباً لا بإسقاطه من الجدول.
    'pdfjs-dist': [
        ('tools/netlify-build.sh PDFJS=', sh, r'^PDFJS=([0-9][\w.\-]*)'),
        ('tools/netlify-build.sh header comment', sh,
         r'#.*\bpdfjs-dist ([0-9][\w.\-]*)'),
        ('public/app dynamic import', page,
         r'/vendor/pdfjs@([0-9][\w.\-]*)/'),
    ],
}
# النُّسخ المعلنة في tools/netlify-build.sh هي المرجع: هي التي تُجلب فعلاً
DECLARED = {'three': '0.160.0', 'pdfjs-dist': '4.10.38'}
for lib, sources in sorted(SOURCES.items()):
    seen = {}
    for label, text, pattern in sources:
        found = sorted(set(re.findall(pattern, text, re.M)))
        seen[label] = found
        chk('%s: %s names a version' % (lib, label), len(found) == 1,
            str(found))
    flat = set(v for vs in seen.values() for v in vs)
    chk('%s is ONE version across all %d places: %s'
        % (lib, len(sources), ', '.join(sorted(flat)) or '<none>'),
        len(flat) == 1, json.dumps(seen))
    chk('%s is the version the build script vendors (%s)'
        % (lib, DECLARED[lib]), flat == {DECLARED[lib]},
        'expected %s, found %s' % (DECLARED[lib], sorted(flat)))

chk('the shim/pdf/three paths in the page are local, never a CDN',
    not re.search(r'(unpkg\.com|jsdelivr\.net|cdnjs\.cloudflare\.com)'
                  r'[^"\']*(three|pdfjs|es-module-shims)', page))

# ── es-module-shims: عقده الآن هو الغياب، ويُفحَص موجباً ──────────────────
print('\n── ح٢ · es-module-shims IS NO LONGER A RUNTIME DEPENDENCY (F-11) ──')
_shim_refs = []
for _rel, _txt in (('public/index.html (shell)', shell),
                   ('public/app/**/*.js (modules)', AS.app_text()),
                   ('public/app/styles/app.css', AS.css_text())):
    for _m in re.finditer(r'/vendor/es-module-shims[^\s"\'<>)]*', _txt):
        _shim_refs.append('%s: %s' % (_rel, _m.group(0)))
chk('nothing in the shipped frontend loads or resolves es-module-shims — no '
    'script tag, no vendor path, in the shell, the modules or the stylesheet',
    _shim_refs == [], ' | '.join(_shim_refs[:4]))
chk('the shell carries no <script> pointing at the shim',
    re.search(r'<script[^>]+src="[^"]*es-module-shims', shell) is None)
chk('the import map is native and needs no polyfill: it is the only inline '
    'script in the shell and it declares type="importmap"',
    len(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', shell)) == 1
    and '<script type="importmap">' in shell,
    str(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', shell)))
# الجانب الآخر من العقد: ما دام غير مستعمَل فلا يجوز أن يظلّ البناء يجلبه.
# هذا فحص على tools/netlify-build.sh، وسقوطه يعني حمولةً ميتة تُنشر بلا مستهلك.
_shim_build = sorted(set(re.findall(r'es-module-shims[@\-][0-9][\w.\-]*', sh)))
chk('the build script no longer vendors es-module-shims — an unreferenced '
    'vendored library is dead payload on every deploy',
    _shim_build == [] and 'SHIMS=' not in sh, ', '.join(_shim_build) or 'SHIMS=')

# ══════════════════════════ ط · مدخل تدقيق التبعيات ════════════════════════
print('\n── ط · A DEPENDENCY-AUDIT ENTRY POINT EXISTS AND RUNS ──')
AUDIT = 'tools/dependency_audit.py'
chk('%s exists' % AUDIT, exists(AUDIT))
if exists(AUDIT):
    apath = os.path.join(ROOT, AUDIT)
    chk('%s is executable (mode %s)'
        % (AUDIT, oct(os.stat(apath).st_mode & 0o777)),
        os.access(apath, os.X_OK))
    src = rd(AUDIT)
    chk('%s starts with a shebang so it runs as a command' % AUDIT,
        src.startswith('#!'))
    chk('%s exits non-zero on drift' % AUDIT,
        'sys.exit(' in src and 'return 1' in src)
    chk('%s declares NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED instead of '
        'claiming the network checks passed' % AUDIT,
        'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED' in src)
    chk('%s names the CVE scan it cannot run' % AUDIT,
        'pip-audit' in src and 'npm audit' in src)
    chk('%s names hash verification as the thing it cannot do' % AUDIT,
        'hash' in src.lower())

chk('DEPENDENCY-POLICY.md documents the update procedure',
    exists('DEPENDENCY-POLICY.md'))
chk('.gitignore exists', exists('.gitignore'))
if exists('.gitignore'):
    gi = rd('.gitignore')
    chk('.gitignore ignores node_modules (dependencies are restored by npm ci)',
        bool(re.search(r'^\s*/?node_modules/?\s*$', gi, re.M)))
    chk('.gitignore documents deterministic dependency restoration',
        'npm ci' in gi and 'package-lock.json' in gi)

print('\n──────────────────────────────────────────────')
print('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: artefact hashes, CVE '
      'status,')
print('  the transitive closure (%d name(s) UNRESOLVED-OFFLINE), and whether '
      'any' % len(lock_unres))
print('  pinned version exists on PyPI at all. All four need a package index.')
print('──────────────────────────────────────────────')
print('DEPENDENCY LOCK CONTRACT: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
