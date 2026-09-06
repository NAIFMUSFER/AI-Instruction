# -*- coding: utf-8 -*-
"""تحقّق النشر — حتمي، ويحسب ما يلزم بدل أن يفترضه.

القاعدة التي يفرضها هذا الملفّ: لا يُعدّ ملفّ منشوراً لمجرّد وجوده في المستودع.
كل وحدة يصل إليها مدخل الخادوم فعلاً يجب أن ينسخها Dockerfile، وكل كتلة متصفّح
مولَّدة يجب أن تكون داخل ما ينشره Netlify، ولا يجوز أن يتسرّب مسار صندوق رمليّ
ولا سرّ إلى ما يُنشر.

F-09/F-11 — بعد تفكيك الصفحة لم تعد `page` مفهوماً واحداً. صار عندنا اثنان:

    shell   نصّ public/index.html — العلامة وخريطة الاستيراد فقط.
    app     شيفرة التطبيق كلّها موصولة بترتيب التحميل الحقيقي.

توكيدات العلامة تُقاس على shell، وتوكيدات الرموز على app. `page` = الاثنان
معاً، ولا تُستعمل إلّا حيث يكون المطلوب «في أيٍّ منهما» صراحةً. المصدر الوحيد
الذي يعرف هذا التخطيط هو tools/app_source.py — لا يُكرَّر هنا.
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

p = [0]
f = [0]
notes = []


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


def note(msg):
    notes.append(msg)
    print('  · %s' % msg)


def rd(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


# ------------------------------------------------- 0. حارس صفحة التطبيق --
print('\n== 0 · THE APPLICATION PAGE GUARD (EMPTY-PAGE REMEDIATION) ==')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import app_source as AS                                           # noqa: E402
import check_index_guard as IG                                    # noqa: E402

# القشرة والشيفرة: مفهومان لا مفهوم واحد. راجع سلسلة التوثيق أعلى الملفّ.
shell = AS.shell()
app = AS.app_text()
page = AS.page_text()
css = AS.css_text()
modules = AS.modules()
boot_scripts = AS.boot_scripts()

_page_fails = IG.check_file(os.path.join(ROOT, 'public', 'index.html'))
chk('public/index.html passes the structural guard', _page_fails == [],
    '; '.join(_page_fails[:3]))
chk('the netlify build runs the same guard before publishing',
    'check_index_guard.py' in rd('tools/netlify-build.sh')
    and 'exit 1' in rd('tools/netlify-build.sh'))


# ── الفحوص السلبية تُجرى على شجرة حقيقية، لا على نصّ في الذاكرة ──────────
# قبل F-09 كان كل ما يفحصه الحارس داخل ملفّ واحد، فكان تحوير نصّه كافياً. الآن
# الشيفرة في ملفّات، والحارس يقرأ الشجرة. نُحوّر نسخةً كاملة من tools/ و public/
# ونشغّل الحارس عليها كما يشغّله البناء بالضبط:
#     python3 tools/check_index_guard.py public/index.html
# فيبقى الفحص الذاتي صحيحاً مهما كانت آليّة الحارس الداخلية، ويبقى مقيساً على
# ما يجري في البناء لا على استدعاء دالّة داخلية قد لا تكون هي المسار الحقيقي.
def _guard_run(mutate):
    tmp = tempfile.mkdtemp(prefix='acs_guard_')
    try:
        shutil.copytree(os.path.join(ROOT, 'tools'), os.path.join(tmp, 'tools'))
        shutil.copytree(os.path.join(ROOT, 'public'),
                        os.path.join(tmp, 'public'))
        if mutate is not None:
            mutate(tmp)
        r = subprocess.run(
            [sys.executable, os.path.join('tools', 'check_index_guard.py'),
             os.path.join('public', 'index.html')],
            cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return r.returncode, r.stdout.decode('utf-8', 'replace')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tree_files(root):
    out = [os.path.join(root, 'public', 'index.html')]
    for base, _d, fns in os.walk(os.path.join(root, 'public', 'app')):
        out += [os.path.join(base, x) for x in sorted(fns)]
    return [x for x in out if os.path.isfile(x)]


def _edit(root, needle, repl, append=False):
    """يحوّر أوّل ملفّ في الشجرة المنشورة يحمل `needle`. غيابُه خطأ صريح."""
    for p_ in _tree_files(root):
        try:
            with open(p_, encoding='utf-8') as fh:
                t = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if needle in t:
            t = (t + repl) if append else t.replace(needle, repl, 1)
            with open(p_, 'w', encoding='utf-8') as fh:
                fh.write(t)
            return True
    raise AssertionError('the needle is not in the published tree: %r' % needle)


_base_rc, _base_out = _guard_run(None)
# لولا هذه، لكانت كل الفحوص السلبية أدناه عقيمة: لو كان الحارس يقرأ شجرة
# المستودع بدل النسخة، لسقطت النسخة السليمة أيضاً ولمرّ كل تحوير «بنجاح».
chk('guard self-test harness: an UNMUTATED copy of the published tree passes, '
    'so the guard really reads the tree it is pointed at',
    _base_rc == 0, _base_out[:200])


def _refused(name, mutate):
    rc, out = _guard_run(mutate)
    chk('guard self-test: %s' % name, rc != 0, out[:200])
    return out


_refused('an EMPTY page is refused',
         lambda r: open(os.path.join(r, 'public', 'index.html'), 'w').close())
_refused('a truncated page is refused',
         lambda r: open(os.path.join(r, 'public', 'index.html'), 'w',
                        encoding='utf-8').write(shell[:len(shell) // 3]))
_stub = _refused(
    'a stub page is refused',
    lambda r: open(os.path.join(r, 'public', 'index.html'), 'w',
                   encoding='utf-8').write(
        '<!DOCTYPE html><html><body>x</body></html>'))
chk('guard self-test: and it says WHY the stub is refused, in bytes or '
    'structure — not a bare non-zero exit',
    re.search(r'byte|minimum|size|structure|importmap|module', _stub, re.I)
    is not None, _stub[:200])
_refused('a missing importmap is refused',
         lambda r: _edit(r, '<script type="importmap">',
                         '<script type="importmap-disabled">'))
_refused('an importmap with invalid JSON is refused',
         lambda r: _edit(r, '"three":', '"three" broken:'))
_refused('an importmap pointing at a CDN is refused',
         lambda r: _edit(r, IG.IMPORTMAP_THREE,
                         'https://unpkg.com/three/build/three.module.js'))
_refused('a missing application entry (<script type=module src>) is refused',
         lambda r: _edit(r, '<script type="module" src="/app/main.js">',
                         '<script type="disabled" src="/app/main.js">'))
_refused('a deleted application entry MODULE is refused — the page would '
         'serve a 404 to its own entry point',
         lambda r: os.remove(os.path.join(r, 'public', 'app', 'main.js')))
# كل خيط محرّك معلَن، وكل زوج علامات معلَن — لا ثلاثة منها فقط كما كان.
for _needle, _what in IG.ENGINE_NEEDLES:
    _refused('missing %s is refused (declared engine needle)' % _what,
             (lambda n: (lambda r: _edit(r, n, '/* removed by self-test */')))(
                 _needle))
for _a, _b in IG.PAIRS:
    _refused('a missing generated end-marker is refused: %s' % _b[:46],
             (lambda b: (lambda r: _edit(r, b, '')))(_b))
    _refused('a DUPLICATED generated end-marker is refused: %s' % _b[:46],
             (lambda b: (lambda r: _edit(r, b, '\n' + b, append=True)))(_b))
chk('guard self-test: a missing file path is refused',
    IG.check_file(os.path.join(ROOT, 'public', 'no_such_page.html')) != [])
chk('the guard checks every phase layer structurally (10 marker pairs)',
    len(IG.PAIRS) == 10 and len(IG.ENGINE_NEEDLES) == 5)
note('the guard self-tests run the guard as the build runs it '
     '(python3 tools/check_index_guard.py public/index.html) against a mutated '
     'copy of tools/ + public/, covering all %d engine needles and all %d '
     'marker pairs' % (len(IG.ENGINE_NEEDLES), len(IG.PAIRS)))

# ---------------------------------------------------------------- 1. الوجود --
print('\n== 1 · REQUIRED DEPLOYMENT FILES EXIST ==')
REQUIRED = [
    'Dockerfile', 'render.yaml', 'netlify.toml', 'requirements.txt',
    'public/index.html', 'tools/netlify-build.sh', 'tools/vendor.sh',
]
for r in REQUIRED:
    chk('%s is present' % r, exists(r))

print('\n== 2 · BROWSER INJECTORS AND THEIR CANONICAL SPECS ==')
INJECTORS = [
    ('tools/build_visual_browser.py', 'acs_visual.json'),
    ('tools/build_runtime_browser.py', 'acs_runtime.json'),
    ('tools/build_authoring_browser.py', 'acs_authoring.json'),
    ('tools/build_workspace_ui.py', 'acs_workspace.json'),
    ('tools/build_render_browser.py', 'acs_render.json'),
    ('tools/build_bim_browser.py', 'acs_bim.json'),
    ('tools/build_docs_browser.py', 'acs_docs.json'),
    ('tools/build_pbr_browser.py', 'acs_pbr.json'),
    ('tools/build_archdetail_browser.py', 'acs_archdetail.json'),
]
for tool, spec in INJECTORS:
    chk('%s is present' % tool, exists(tool))
    chk('%s is present' % spec, exists(spec))

# --------------------------------------------------- 3. إغلاق استيراد الخادوم --
print('\n== 3 · THE BACKEND IMPORT CLOSURE IS ACTUALLY COPIED BY THE DOCKERFILE ==')
ENTRY = 'acs_understand_api'


def _acs_imports(path):
    out = set()
    try:
        tree = ast.parse(open(path, encoding='utf-8').read())
    except (OSError, SyntaxError):
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith('acs_'):
                    out.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module and n.module.startswith('acs_'):
                out.add(n.module)
    return out


closure = {ENTRY}
stack = [ENTRY]
while stack:
    m = stack.pop()
    path = os.path.join(ROOT, m + '.py')
    if not os.path.exists(path):
        continue
    for dep in _acs_imports(path):
        if dep not in closure:
            closure.add(dep)
            stack.append(dep)

needed_json = set()
for m in sorted(closure):
    path = os.path.join(ROOT, m + '.py')
    if os.path.exists(path):
        src = open(path, encoding='utf-8').read()
        for a, b in re.findall(r'"(acs_[a-z_]+\.json)"|\'(acs_[a-z_]+\.json)\'', src):
            needed_json.add(a or b)

docker = rd('Dockerfile')
copied = set()
for line in docker.splitlines():
    s = line.strip()
    if s.startswith('COPY'):
        for tok in s.split()[1:]:
            if tok.startswith('acs_') or tok in ('requirements.txt',):
                copied.add(tok)

note('the deployed API entrypoint is %s.py' % ENTRY)
note('its transitive closure is %d module(s): %s'
     % (len(closure), ', '.join(sorted(m + '.py' for m in closure))))
for m in sorted(closure):
    chk('the Dockerfile copies %s.py (required at runtime)' % m,
        (m + '.py') in copied)
for j in sorted(needed_json):
    chk('the Dockerfile copies %s (required at runtime)' % j, j in copied)
chk('the Dockerfile installs the declared dependencies',
    'requirements.txt' in copied and 'pip install' in docker)
chk('the Dockerfile launches the real entrypoint',
    'acs_understand_api:app' in docker)
chk('the container port is taken from the platform, not hardcoded',
    '${PORT:-8000}' in docker)

# وحدات موجودة في المستودع ولا يصل إليها الخادوم: تُذكر صراحةً لا تمرّ بصمت
all_mods = sorted(x[:-3] for x in os.listdir(ROOT)
                  if re.match(r'^acs_.*\.py$', x))
not_reachable = [m for m in all_mods if m not in closure]
in_image_unreachable = sorted(m for m in not_reachable if (m + '.py') in copied)
not_in_image = sorted(m for m in not_reachable if (m + '.py') not in copied)
note('%d module(s) are in the image but not reachable from the API entrypoint: %s'
     % (len(in_image_unreachable), ', '.join(in_image_unreachable) or 'none'))
note('%d module(s) are browser-mirrored only and intentionally absent from the '
     'image: %s' % (len(not_in_image), ', '.join(not_in_image) or 'none'))
chk('no module the API needs is missing from the image',
    all((m + '.py') in copied for m in closure))

# ------------------------------ 4. الواجهة: كتل مولَّدة داخل ما يُنشر فعلاً --
print('\n== 4 · THE PUBLISHED FRONTEND CARRIES EVERY GENERATED BROWSER BLOCK ==')
# قبل F-09: «الكتلة داخل index.html». بعده: الكتلة داخل وحدة تحت public/app/
# **يستوردها main.js**. البديل أشدّ لا أضعف: لا يكفي وجود النصّ في ملفّ ما، بل
# يجب أن يكون الملفّ في رسم الاستيراد وإلّا شُحن ولم يُقيَّم أبداً.
MARKERS = []
for tool, _ in INJECTORS:
    if not exists(tool):
        continue
    src = rd(tool)
    for m in re.findall(r'^(?:JS_|CSS_|DOM_)?(?:BEGIN|END)\s*=\s*[\'"](.+?)[\'"]\s*$',
                        src, re.M):
        MARKERS.append((tool, m))
chk('marker definitions were found in the injectors', len(MARKERS) >= 10,
    str(len(MARKERS)))
_IMPORTED = set(AS.order())
_carrier = {}                     # علامة → الملفّات المنشورة التي تحملها
_frontend_files = dict(modules)
_frontend_files['index.html(shell)'] = shell
if css:
    _frontend_files['styles/app.css'] = css
for tool, m in MARKERS:
    hits = sorted(k for k, v in _frontend_files.items() if m in v)
    total = sum(v.count(m) for v in _frontend_files.values())
    _carrier[m] = hits
    label = m[:58] + ('…' if len(m) > 58 else '')
    chk('the published frontend carries exactly one %s' % label,
        total == 1, '%d occurrence(s), from %s' % (total, tool))
    chk('and it is in a file the browser actually evaluates: %s' % label,
        len(hits) == 1
        and (hits[0] in _IMPORTED or hits[0] in ('index.html(shell)',
                                                 'styles/app.css')
             or hits[0].startswith('boot/')),
        '%s (main.js imports %d module(s))' % (hits, len(_IMPORTED)))

print('\n== 5 · THE MIRRORED SPECIFICATIONS HAVE NOT DRIFTED FROM THE FILES ==')
SPEC_VARS = [
    ('acs_visual.json', 'ACS_VISUAL_SPEC'),
    ('acs_runtime.json', 'ACS_RUNTIME_SPEC'),
    ('acs_authoring.json', 'ACS_AUTHORING_SPEC'),
    ('acs_workspace.json', 'ACS_WORKSPACE_SPEC'),
    ('acs_render.json', 'ACS_RENDER_SPEC'),
    ('acs_bim.json', 'ACS_BIM_SPEC'),
    ('acs_docs.json', 'ACS_DOCS_SPEC'),
    ('acs_pbr.json', 'ACS_PBR_SPEC'),
    ('acs_archdetail.json', 'ACS_ARCHDETAIL_SPEC'),
]
for spec, var in SPEC_VARS:
    if not exists(spec):
        continue
    m = re.search(re.escape('const ' + var) + r'\s*=\s*(\{.*?\});\s*\n', app, re.S)
    if not m:
        chk('%s is mirrored into the shipped modules as %s' % (spec, var),
            False, 'not found')
        continue
    try:
        mirrored = json.loads(m.group(1))
        ok = mirrored == json.loads(rd(spec))
    except ValueError as e:
        ok = False
        mirrored = str(e)
    chk('%s in the shipped modules is byte-equal to the file on disk' % var,
        ok)

# ------------------------------------------------------ 6. تهيئة Netlify --
print('\n== 6 · NETLIFY CONFIGURATION IS VALID AND MATCHES REALITY ==')
nt = rd('netlify.toml')
pub = re.search(r'publish\s*=\s*"([^"]+)"', nt)
cmd = re.search(r'command\s*=\s*"([^"]+)"', nt)
chk('a publish directory is declared', bool(pub), nt[:80])
chk('the declared publish directory exists',
    bool(pub) and os.path.isdir(os.path.join(ROOT, pub.group(1))),
    pub.group(1) if pub else '')
chk('the published directory contains the application entry',
    bool(pub) and os.path.exists(os.path.join(ROOT, pub.group(1), 'index.html')))
chk('a build command is declared', bool(cmd))

# ---- الأساس (base) — دفاع دائم عن جذر النشر (hotfix) --------------------
# خطأ الإنتاج "Base directory does not exist: /opt/build" ينشأ حين يُحلّ أساس
# البناء خارج نسخة المستودع. المشروع يُنشر من جذر المستودع، فالمفتاح إمّا غائب
# تماماً وإمّا مجلّد نسبي موجود داخل الشجرة. يُقرأ TOML قراءةً حقيقية لا بمطابقة
# نصّية: base-uri داخل CSP ليست أساس بناء، ومطابقة "base" النصّية تخلط بينهما.
try:
    import tomllib as _toml
    _nt = _toml.loads(nt)
    _toml_ok = True
except Exception as _e:                                           # noqa: BLE001
    _nt, _toml_ok = {}, False
chk('netlify.toml parses as real TOML', _toml_ok)

def _bases(cfg):
    """كل أساس معلَن: [build] وكل [context.*] — لا يفلت سياق واحد."""
    out = []
    b = (cfg.get('build') or {}).get('base')
    if b is not None:
        out.append(('build', b))
    for ctx, body in (cfg.get('context') or {}).items():
        if isinstance(body, dict) and body.get('base') is not None:
            out.append(('context.' + ctx, body['base']))
    return out

_declared = _bases(_nt)
if not _declared:
    note('netlify.toml declares no build base in any context; the effective '
         'base is the repository root, which is the intended contract')
chk('no build base is declared, or every declared base is repository-relative',
    all(not os.path.isabs(str(v)) for _k, v in _declared),
    ', '.join('%s=%r' % kv for kv in _declared))
chk('no declared base escapes the repository with a parent segment',
    all('..' not in str(v).split('/') for _k, v in _declared),
    ', '.join('%s=%r' % kv for kv in _declared))
for _k, _v in _declared:
    _res = os.path.normpath(os.path.join(ROOT, str(_v)))
    chk('the %s base resolves inside the repository root' % _k,
        _res == ROOT or _res.startswith(ROOT + os.sep), _res)
    chk('the %s base is a directory committed in the repository' % _k,
        os.path.isdir(_res), _res)
_eff_rel = str(_declared[0][1]) if _declared else '.'
_eff = os.path.normpath(os.path.join(ROOT, _eff_rel))
note('the effective Netlify build base is %s'
     % ('the repository root (base NOT SET)' if _eff == ROOT else _eff_rel))
chk('the effective base exists and is inside the repository',
    os.path.isdir(_eff)
    and (_eff == ROOT or _eff.startswith(ROOT + os.sep)), _eff)
chk('the publish directory resolves to a real directory under the effective base',
    bool(pub) and os.path.isdir(os.path.join(_eff, pub.group(1))),
    os.path.join(_eff_rel, pub.group(1)) if pub else '')
chk('the published directory under the effective base carries the app entry',
    bool(pub) and os.path.isfile(os.path.join(_eff, pub.group(1), 'index.html')))
if cmd:
    _script = cmd.group(1).split()[-1]
    chk('the build command script resolves from the effective base',
        os.path.isfile(os.path.join(_eff, _script)),
        os.path.join(_eff_rel, _script))
    chk('the build command references no parent directory',
        '..' not in cmd.group(1).split('/'), cmd.group(1))
chk('no absolute build path is baked into netlify.toml',
    not re.search(r'=\s*"/(?!\*)', nt), 'an absolute path is declared')
chk('the netlify configuration names no builder-internal path',
    '/opt/build' not in nt)
# لا ملفّ تهيئة آخر يستطيع إعادة إدخال أساس
_other = [x for x in ('netlify.yml', 'netlify.yaml', '.netlify')
          if exists(x)]
chk('no second Netlify configuration file can reintroduce a base',
    _other == [], ', '.join(_other))

# فحص ذاتي للحارس نفسه: الفحوص أعلاه تمرّ اليوم لأن المفتاح غائب، فلو كانت
# عقيمة لمرّت أيضاً على تهيئة معطوبة. نمرّر تهيئات معادية عبر المنطق نفسه
# ونشترط أن يمسكها — وإلّا فالحارس زينة لا حماية.
def _base_verdict(toml_text):
    """يعيد True إذا كانت التهيئة مقبولة بالقواعد نفسها أعلاه."""
    try:
        cfg = _toml.loads(toml_text)
    except Exception:                                             # noqa: BLE001
        return False
    for _k, v in _bases(cfg):
        v = str(v)
        if os.path.isabs(v):
            return False
        if '..' in v.split('/'):
            return False
        res = os.path.normpath(os.path.join(ROOT, v))
        if not (res == ROOT or res.startswith(ROOT + os.sep)):
            return False
        if not os.path.isdir(res):
            return False
    return True


_HOSTILE = [
    ('parent directory base', '[build]\nbase = ".."\npublish = "public"\n'),
    ('parent with slash', '[build]\nbase = "../"\npublish = "public"\n'),
    ('nested escape', '[build]\nbase = "tools/../.."\npublish = "public"\n'),
    ('absolute builder path', '[build]\nbase = "/opt/build"\npublish = "public"\n'),
    ('absolute repo path', '[build]\nbase = "/opt/build/repo"\npublish = "public"\n'),
    ('absolute root', '[build]\nbase = "/"\npublish = "public"\n'),
    ('missing directory', '[build]\nbase = "no_such_dir"\npublish = "public"\n'),
    ('context escape', '[build]\npublish = "public"\n\n'
                       '[context.production]\nbase = ".."\n'),
    ('context absolute', '[build]\npublish = "public"\n\n'
                         '[context.deploy-preview]\nbase = "/opt/build"\n'),
]
for _name, _text in _HOSTILE:
    chk('the base guard rejects a %s' % _name,
        _base_verdict(_text) is False)
chk('the base guard accepts the shipped configuration',
    _base_verdict(nt) is True)
chk('the base guard accepts a legitimate committed subdirectory',
    _base_verdict('[build]\nbase = "tools"\npublish = "public"\n') is True)
if cmd:
    script = cmd.group(1).split()[-1]
    chk('the build command points at a script that exists in the repository',
        exists(script), script)
chk('a Content-Security-Policy header is declared', 'Content-Security-Policy' in nt)
csp = re.search(r'Content-Security-Policy\s*=\s*"([^"]+)"', nt)
chk('the CSP does not use a wildcard script source',
    bool(csp) and 'script-src *' not in csp.group(1)
    and "script-src 'self'" in csp.group(1))
chk('the CSP pins connect-src rather than allowing anything',
    bool(csp) and 'connect-src' in csp.group(1)
    and '*' not in csp.group(1).split('connect-src')[1].split(';')[0])
chk('framing is denied', 'X-Frame-Options' in nt and "frame-ancestors 'none'" in nt)

# ── 6b · السياسة الصارمة: لا استثناء مضمّن ولا تقييم نصّ (F-11) ──────────
print('\n== 6b · THE CONTENT SECURITY POLICY IS STRICT, AND THE PAGE EARNS IT ==')
CSP_TEXT = csp.group(1) if csp else ''
CSP_DIRS = {}
for _d in [x.strip() for x in CSP_TEXT.split(';') if x.strip()]:
    _parts = _d.split()
    CSP_DIRS[_parts[0]] = _parts[1:]
note('the declared CSP has %d directive(s): %s'
     % (len(CSP_DIRS), ', '.join(sorted(CSP_DIRS))))
chk('the policy parses into named directives at all', len(CSP_DIRS) >= 8,
    str(sorted(CSP_DIRS)))
_unsafe = sorted(d for d, v in CSP_DIRS.items()
                 if "'unsafe-inline'" in v or "'unsafe-eval'" in v)
chk("NO directive carries 'unsafe-inline' or 'unsafe-eval' — not one",
    _unsafe == [], ', '.join(_unsafe))
chk('script-src is exactly \'self\' plus one sha256 source',
    [x for x in CSP_DIRS.get('script-src', []) if not x.startswith("'sha256-")]
    == ["'self'"], str(CSP_DIRS.get('script-src')))
_hashes = [x.strip("'") for x in CSP_DIRS.get('script-src', [])
           if x.startswith("'sha256-")]
chk('script-src carries EXACTLY ONE hash source', len(_hashes) == 1,
    str(_hashes))
_IMAP_HASH = AS.importmap_hash()
chk('that hash is the sha256 of the page\'s own inline import map — the only '
    'inline script left in the shell',
    _hashes == [_IMAP_HASH], 'policy=%s computed=%s' % (_hashes, _IMAP_HASH))
chk('the recorded hash file agrees with the page and the policy',
    (not exists('public/app/importmap.sha256'))
    or rd('public/app/importmap.sha256').strip() == _IMAP_HASH,
    rd('public/app/importmap.sha256').strip()
    if exists('public/app/importmap.sha256') else 'absent')
chk("style-src is 'self' only — the stylesheet is external, so no inline "
    'style needs allowing', CSP_DIRS.get('style-src') == ["'self'"],
    str(CSP_DIRS.get('style-src')))
for _d, _want in (('default-src', ["'self'"]), ('base-uri', ["'self'"]),
                  ('object-src', ["'none'"]), ('frame-ancestors', ["'none'"]),
                  ('frame-src', ["'none'"]), ('form-action', ["'self'"]),
                  ('worker-src', ["'self'"]), ('font-src', ["'self'"])):
    chk('%s is %s' % (_d, ' '.join(_want)), CSP_DIRS.get(_d) == _want,
        str(CSP_DIRS.get(_d)))

# -------------------------------------------------------- 7. تهيئة Render --
print('\n== 7 · RENDER CONFIGURATION IS VALID AND MATCHES REALITY ==')
ry = rd('render.yaml')
chk('a web service is declared', re.search(r'type:\s*web', ry) is not None)
chk('the runtime is docker, matching the Dockerfile in the repository',
    re.search(r'runtime:\s*docker', ry) is not None)
hc = re.search(r'healthCheckPath:\s*(\S+)', ry)
chk('a health check path is declared', bool(hc))
chk('the health check path is served by the API',
    bool(hc) and ('@app.get("%s")' % hc.group(1)) in rd('acs_understand_api.py'),
    hc.group(1) if hc else '')
chk('the secret is declared without a value',
    re.search(r'key:\s*ANTHROPIC_API_KEY\s*\n\s*sync:\s*false', ry) is not None)
chk('the allowed origin is pinned, not a wildcard',
    'ACS_ALLOWED_ORIGINS' in ry and '"*"' not in ry)
chk('the model identifier is unchanged', 'claude-sonnet-5' in ry)
chk('rate limits are still declared',
    all(k in ry for k in ('ACS_RL_GEN_HOUR', 'ACS_RL_GEN_DAY',
                          'ACS_RL_EDIT_HOUR', 'ACS_RL_GLOBAL_DAY')))

print('\n== 8 · EVERY ENV VAR THE BACKEND READS IS DECLARED OR DEFAULTED ==')
env_read = set()
for m in sorted(closure):
    path = os.path.join(ROOT, m + '.py')
    if os.path.exists(path):
        src = open(path, encoding='utf-8').read()
        for name in re.findall(r'os\.environ\.get\(\s*"([A-Z_]+)"(\s*,)?', src):
            env_read.add(name[0])
        for name in re.findall(r'os\.environ\.get\(\s*"([A-Z_]+)"\s*\)', src):
            env_read.add(name)
api_src = rd('acs_understand_api.py')
for name in re.findall(r'os\.environ\.get\(\s*"([A-Z_]+)"', api_src):
    env_read.add(name)
note('the backend reads %d environment variable(s)' % len(env_read))
undeclared_nodefault = []
for name in sorted(env_read):
    has_default = re.search(r'os\.environ\.get\(\s*"%s"\s*,' % name,
                            api_src + ''.join(
                                open(os.path.join(ROOT, m + '.py'),
                                     encoding='utf-8').read()
                                for m in sorted(closure)
                                if os.path.exists(os.path.join(ROOT, m + '.py'))))
    if not has_default and name not in ry:
        undeclared_nodefault.append(name)
chk('no environment variable is both undeclared and undefaulted',
    undeclared_nodefault == [], ', '.join(undeclared_nodefault))

# ------------------------------------------------- 9. لا مسار صندوق ولا سرّ --
print('\n== 9 · NO SANDBOX PATH LEAKS INTO ANYTHING DEPLOYED ==')
DEPLOYED = ['public/index.html', 'Dockerfile', 'netlify.toml', 'render.yaml',
            'requirements.txt', 'tools/netlify-build.sh', 'tools/vendor.sh']
# F-09 — الصفحة وحدها لم تعد الواجهة. كل ملفّ منشور تحت public/app/ يُمسح أيضاً:
# مسار صندوق أو سرّ في وحدة يُنشر تماماً كما يُنشر في الصفحة.
DEPLOYED += sorted('public/app/' + k for k in modules)
if exists('public/app/styles/app.css'):
    DEPLOYED.append('public/app/styles/app.css')
DEPLOYED += sorted(m + '.py' for m in closure)
DEPLOYED += [x for x in os.listdir(ROOT) if re.match(r'^acs_.*\.(py|json)$', x)]
note('%d published frontend file(s) are scanned for sandbox paths and secrets '
     'alongside the page' % (len(modules) + (1 if css else 0)))
SANDBOX = re.compile(r'/home/[a-z]+/|/opt/pw-browsers|/tmp/acs_|file:///home/')
for rel in sorted(set(DEPLOYED)):
    if not exists(rel):
        continue
    hits = SANDBOX.findall(rd(rel))
    chk('%s carries no sandbox path' % rel, not hits, str(hits[:3]))

print('\n== 10 · NO SECRET IS PACKAGED ==')
SECRET = re.compile(
    r'sk-ant-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{20,}|'
    r'AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,}|'
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----')
for rel in sorted(set(DEPLOYED)):
    if not exists(rel):
        continue
    chk('%s carries no credential-shaped value' % rel, not SECRET.search(rd(rel)))
dotenvs = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames
                   if d not in ('.git', 'node_modules', '__pycache__')]
    for fn in filenames:
        if fn == '.env' or fn.startswith('.env.') and fn != '.env.example':
            dotenvs.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
chk('no real .env file is present in the repository', dotenvs == [],
    ', '.join(dotenvs))
chk('an .env.example with placeholders only is provided', exists('.env.example'))
if exists('.env.example'):
    ex = rd('.env.example')
    chk('the .env.example contains no real value', not SECRET.search(ex))
    chk('the .env.example names the secret without setting it',
        re.search(r'^ANTHROPIC_API_KEY=\s*$', ex, re.M) is not None
        or re.search(r'^ANTHROPIC_API_KEY=<', ex, re.M) is not None)
# لا يُثبَّت هذا على صياغة بعينها: يُفحص كل موضع يُذكر فيه اسم المتغيّر، ويُطلب
# أن يكون سياقه وجودياً (bool/strip/إلحاق اسم) لا تمريراً للقيمة.
_key_lines = [ln for ln in api_src.split('\n') if 'ANTHROPIC_API_KEY' in ln]
chk('the API reads the key name somewhere (the check is not vacuous)',
    len(_key_lines) >= 1)
chk('every mention of the key is existence-only — the value is never returned',
    all(('bool(' in ln) or ln.strip().startswith('#') or 'append(' in ln
        for ln in _key_lines), '; '.join(_key_lines)[:200])
chk('the key-presence helper returns a boolean, not the key',
    re.search(r'def _api_key_configured[^\n]*\n(?:\s+"""[\s\S]*?"""\n)?\s+return bool\(',
              api_src) is not None)
_key_value_reads = [ln for ln in _key_lines
                    if re.search(r'(return|print|yield|format\()', ln)
                    and 'bool(' not in ln]
chk('no response, log line or f-string carries the key value',
    _key_value_reads == [], '; '.join(_key_value_reads)[:200])
chk('the API never returns the key itself, only whether one is set',
    'api_key_configured' in api_src and not any(
        'bool(' not in ln for ln in _key_lines
        if re.match(r'\s*return\b', ln)))

# ------------------------------------------------ 11. اتّساق داخلي للحزمة --
print('\n== 11 · THE PRODUCTION BUNDLE IS INTERNALLY SELF-CONSISTENT ==')
# ── ما حلّ محلّ «صفحة واحدة قائمة بذاتها» ────────────────────────────────
# التوكيدة القديمة كانت: حجم public/index.html > 100 ك.ب — أي «الصفحة تحمل كل
# شيء». هذا بالضبط ما ثبّت العيب: مليون وثمانمئة ألف بايت لا يُخزَّن منها شيء
# ولا تحتمل سياسة أمن صارمة. بديلها ثلاث توكيدات أشدّ مجتمعةً:
#   (١) الصفحة قشرة صغيرة،
#   (٢) الشيفرة لم تختفِ بل انتقلت — مجموعها لا يقلّ عمّا كان،
#   (٣) وكل ملفّ منها موصول فعلاً بمدخل الوحدات.
SHELL_BYTES = os.path.getsize(os.path.join(ROOT, 'public/index.html'))
MOD_BYTES = sum(len(v.encode('utf-8')) for v in modules.values())
CSS_BYTES = len(css.encode('utf-8'))
PRE_SPLIT_PAGE_BYTES = 1863894      # المقيس على الشجرة قبل F-09
note('shell=%d B · %d module(s)=%d B · css=%d B · pre-split single page=%d B'
     % (SHELL_BYTES, len(modules), MOD_BYTES, CSS_BYTES,
        PRE_SPLIT_PAGE_BYTES))
chk('the published page is a SHELL, not the application: under 200 KB',
    SHELL_BYTES < 200000, str(SHELL_BYTES))
chk('and dramatically smaller than the single file it replaced (under a tenth)',
    SHELL_BYTES * 10 < PRE_SPLIT_PAGE_BYTES, str(SHELL_BYTES))
chk('the application did not shrink, it moved: shell + modules + stylesheet '
    'carry at least what the single page carried',
    SHELL_BYTES + MOD_BYTES + CSS_BYTES >= PRE_SPLIT_PAGE_BYTES * 0.9,
    str(SHELL_BYTES + MOD_BYTES + CSS_BYTES))
chk('the application is split into separately cacheable modules',
    len(modules) >= 15, str(len(modules)))

# ── الصفحة لا تحمل جافاسكربت تنفيذياً مضمّناً، ولا نمطاً مضمّناً (F-11) ──
_inline_scripts = re.findall(r'<script(?![^>]*\bsrc=)([^>]*)>', shell)
_non_importmap = [a for a in _inline_scripts
                  if 'type="importmap"' not in a]
chk('the page contains NO executable inline script: the only inline <script> '
    'is the import map',
    len(_inline_scripts) == 1 and _non_importmap == [],
    'inline=%r' % (_inline_scripts,))
chk('the page contains NO <style> block', not re.search(r'<style[\s>]', shell),
    'a <style> block is present')
_style_attrs = re.findall(r'<[^>]*\sstyle\s*=\s*"[^"]*"', shell)
chk('the page contains NO style= attribute — the .acs-u-NN utility classes '
    'replaced every one of them', _style_attrs == [],
    '; '.join(x[:70] for x in _style_attrs[:3]))
_UTIL = sorted(set(re.findall(r'\bacs-u-\d+\b', shell)))
chk('the utility classes that replaced them ship in the external stylesheet, '
    'so nothing lost its styling silently',
    all(('.' + u) in css for u in _UTIL) and len(_UTIL) > 0,
    ', '.join(u for u in _UTIL if ('.' + u) not in css)[:120])
_inline_handlers = sorted(set(re.findall(r'\s(on[a-z]+)\s*=\s*"', shell)))
chk('the page carries NO inline event-handler attribute — under this CSP one '
    'would never fire, so its presence is dead code, not style',
    _inline_handlers == [], ', '.join(_inline_handlers))

# ── كل مرجع في القشرة يُحلّ إلى ملفّ موجود ────────────────────────────────
srcs = re.findall(r'<script[^>]+src="([^"]+)"', shell)
links = re.findall(r'<link[^>]+rel="stylesheet"[^>]*href="([^"]+)"', shell) \
    + re.findall(r'<link[^>]+href="([^"]+)"[^>]*rel="stylesheet"', shell)
all_links = re.findall(r'<link[^>]+href="([^"]+)"', shell)
remote = [u for u in srcs + all_links
          if u.startswith('http://') or u.startswith('//')
          or (u.startswith('https://') and 'acs-engine.onrender.com' not in u)]
chk('the page loads no remote script or stylesheet at runtime', remote == [],
    ', '.join(remote[:3]))
chk('the shell declares at least one script and exactly one stylesheet',
    len(srcs) >= 2 and len(links) == 1, 'scripts=%r css=%r' % (srcs, links))
_ref_missing = []
for u in srcs + links:
    if re.match(r'^[a-z]+:', u):                      # data: / https: — ليست ملفّاً
        continue
    _fp = os.path.join(ROOT, 'public', u.lstrip('./').lstrip('/'))
    if not (os.path.isfile(_fp) and os.path.getsize(_fp) > 0):
        _ref_missing.append(u)
chk('EVERY <script src> and <link rel=stylesheet> in the shell resolves to a '
    'non-empty file that exists in public/', _ref_missing == [],
    ', '.join(_ref_missing))
chk('the module entry point the shell names is public/app/main.js',
    '<script type="module" src="/app/main.js"></script>' in shell)
# العدد ثابت معلن لا مشتقّ: قائمة متقلّصة بصمت هي كيف يختفي سكربت إقلاع
# فيصير الحارس أخضر والصفحة ناقصة. يُحدَّث عمداً عند إضافة سكربت أو حذفه.
#   5 → 6 مع F-30 (KI-13): boot/style-bridge.js يطبّق الهندسة الديناميكية
#   عبر CSSOM لأن `style-src 'self'` يحجب سمة style حتى داخل innerHTML.
EXPECTED_BOOT_SCRIPTS = 6
chk('every classic boot script the shell names exists under public/app/boot/',
    all(os.path.isfile(os.path.join(ROOT, 'public', 'app', 'boot', b))
        for b in boot_scripts)
    and len(boot_scripts) == EXPECTED_BOOT_SCRIPTS,
    ', '.join(sorted(boot_scripts)))
_boot_referenced = sorted(set(re.findall(r'src="/app/boot/([^"]+)"', shell)))
chk('and every boot script that ships is actually referenced by the shell — '
    'no orphan boot file',
    _boot_referenced == sorted(boot_scripts),
    'referenced=%s shipped=%s' % (_boot_referenced, sorted(boot_scripts)))

# ── رسم الاستيراد مغلق: لا وحدة يتيمة ولا استيراد مفقود ─────────────────
_IMPORTED = AS.order()
_EXEMPT = {'main.js', 'shared-state.js'}
_expected = sorted(k for k in modules
                   if k not in _EXEMPT and not k.startswith('boot/')
                   and not k.startswith('styles/'))
_orphans = [k for k in _expected if k not in _IMPORTED]
_missing_imports = [k for k in _IMPORTED if k not in modules]
chk('public/app/main.js imports EVERY shipped module except boot/, styles/, '
    'main.js and shared-state.js — no orphan file is published',
    _orphans == [], ', '.join(_orphans))
chk('and every module main.js imports really exists — no missing import',
    _missing_imports == [], ', '.join(_missing_imports))
chk('the import list has no duplicate: a module evaluated twice is a second '
    'copy of its state',
    len(_IMPORTED) == len(set(_IMPORTED)),
    str(sorted(x for x in set(_IMPORTED) if _IMPORTED.count(x) > 1)))
note('main.js imports %d module(s) in the original evaluation order; '
     'shared-state.js carries the %d bindings written across module boundaries'
     % (len(_IMPORTED),
        len(re.findall(r'^\s+\w+:', modules.get('shared-state.js', ''), re.M))))
chk('the cross-module write surface is a single sealed object, not a set of '
    'globals',
    'Object.seal(' in modules.get('shared-state.js', '')
    and 'export const __ACS_SHARED' in modules.get('shared-state.js', ''))

# ── es-module-shims ذهب: لا في القشرة ولا في الوحدات ولا في متطلّبات التوريد ──
_shim_page = re.findall(r'/vendor/es-module-shims[^\s"\'<>)]*', shell + app + css)
chk('es-module-shims is referenced nowhere in the shipped frontend (shell, '
    'modules or stylesheet)', _shim_page == [], ', '.join(_shim_page[:3]))

local_refs = [u for u in srcs + all_links
              if u.startswith('./') or u.startswith('/')
              or not re.match(r'^[a-z]+:', u)]
missing_local = [u for u in local_refs
                 if not os.path.exists(os.path.join(ROOT, 'public',
                                                    u.lstrip('./').lstrip('/')))]
vendored = [u for u in missing_local if '/vendor/' in u]
other_missing = [u for u in missing_local if '/vendor/' not in u]
chk('every non-vendored local reference resolves inside public/',
    other_missing == [], ', '.join(other_missing[:3]))
if vendored:
    note('%d vendored reference(s) resolve only after the Netlify build runs '
         'tools/netlify-build.sh: %s'
         % (len(vendored), ', '.join(sorted(set(vendored))[:3])))
# مجلّد موجود ليس دليلاً على ملفّ موجود: نعدّ الملفّات لا المجلّدات، ونطابق
# القائمة الحرجة التي يفرضها سكربت البناء نفسه
vend = os.path.join(ROOT, 'public', 'vendor')
vendor_files = []
if os.path.isdir(vend):
    for dp, _dn, fns in os.walk(vend):
        vendor_files += [os.path.join(dp, x) for x in fns]
nb = rd('tools/netlify-build.sh')
# النُّسخ تُقرأ من السكربت نفسه لا من قائمة مكتوبة بيد: رفعُ رقمٍ هناك لا يجوز
# أن يمرّ لأن هذا الملفّ ما زال يحمل الرقم القديم.
_vars = dict(re.findall(r'^([A-Z]+)=([0-9][\w.\-]*)\s*$', nb, re.M))
note('the build script declares %d vendored version(s): %s'
     % (len(_vars), ', '.join('%s=%s' % kv for kv in sorted(_vars.items()))))
_must_block = re.search(r'^must=\(\n(.*?)^\)', nb, re.M | re.S)
chk('build declares a non-empty required asset array', bool(_must_block))
must_vendor = re.findall(r'"\$VEN/([^"]+)"', _must_block.group(1) if _must_block else '')
must_vendor = sorted(set(v for v in must_vendor
                         if v.count('/') >= 1 and not v.endswith('/')))
_unresolved = sorted(set(v for v in must_vendor
                         for t in re.findall(r'\$([A-Z]+)', v)
                         if t not in _vars))
chk('every version placeholder in the vendor list resolves to a declared '
    'variable', _unresolved == [], ', '.join(_unresolved))
for _k, _v in _vars.items():
    must_vendor = [v.replace('$' + _k, _v) for v in must_vendor]
present = [v for v in must_vendor
           if os.path.isfile(os.path.join(vend, v))
           and os.path.getsize(os.path.join(vend, v)) > 0]
if len(present) == len(must_vendor) and must_vendor:
    chk('every runtime library the build script requires is vendored '
        '(%d files)' % len(present), True)
else:
    note('public/vendor holds %d file(s); the build script requires %d and %d '
         'are present. Run tools/netlify-build.sh to materialize locked assets. '
         'Three.js-dependent 3D runtime behaviour in this checkout is '
         'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.'
         % (len(vendor_files), len(must_vendor), len(present)))
    chk('the missing runtime libraries are fetched by the declared build '
        'command, not expected in the repository',
        bool(cmd) and 'netlify-build.sh' in cmd.group(1))
chk('the vendor fetch script pins exact versions',
    all(re.match(r'^\d+(\.\d+)*$', v) for v in _vars.values())
    and _vars.get('THREE') == '0.160.0' and _vars.get('PDFJS') == '4.10.38',
    str(_vars))
# F-11 — es-module-shims حُذف من الواجهة. حمولة مُوَرَّدة بلا مستهلك تُنشر في
# كل بناء ولا يطلبها أحد: تُرفَض هنا صراحةً بدل أن تبقى بلا مالك.
_shim_vendor = sorted(set(v for v in must_vendor if 'es-module-shims' in v))
chk('the build script vendors NO es-module-shims: nothing in the shipped '
    'frontend loads it, so fetching it is dead payload on every deploy',
    _shim_vendor == [] and 'SHIMS' not in _vars,
    ', '.join(_shim_vendor) or 'SHIMS=%s' % _vars.get('SHIMS'))
chk('the vendored libraries are exactly the two the frontend actually '
    'resolves: three (import map) and pdfjs (dynamic import)',
    sorted(_vars) == ['PDFJS', 'THREE'], str(sorted(_vars)))
_vendor_needed = sorted(set(re.findall(r'/vendor/([A-Za-z0-9@.\-]+)/',
                                       shell + app)))
chk('every /vendor/ package the frontend references is fetched by the build '
    'script', all(any(v.startswith(pkg) for v in must_vendor)
                  for pkg in _vendor_needed),
    'referenced=%s' % _vendor_needed)
chk('the vendor fetch script fails the build on a missing file',
    'set -euo pipefail' in rd('tools/netlify-build.sh')
    and 'MISSING/EMPTY' in rd('tools/netlify-build.sh'))
chk('the model identifier is unchanged in the Dockerfile',
    'ACS_LLM_MODEL=claude-sonnet-5' in docker)

print('\n== 11b · EVERY CANONICAL SPEC IS CLASSIFIED, NONE IS ORPHANED ==')
# لا يكفي أن يوجد ملفّ في المستودع: كل acs_*.json و acs_*.py يجب أن يقع في
# واحدة من ثلاث خانات معلَنة — تشغيل الخادوم، أو مرآة المتصفّح، أو الاختبار.
browser_specs = set()
for tool, spec in INJECTORS:
    if exists(tool):
        browser_specs.add(spec)
        browser_specs.add(spec.replace('.json', '.py'))
backend_files = set(m + '.py' for m in closure) | set(needed_json)
image_files = set(copied)
# أدوات سطر أوامر تعمل خارج الخادوم وخارج الصفحة: تُصنَّف صراحةً بدل أن تبقى
# يتيمة. الشرط أن يثبت الفحص أن الخادوم لا يصل إليها فعلاً.
OFFLINE_TOOLS = ['acs_compiler.py']
# رفقاء طبقة التأليف: شيفرة مرجعية تعيش حيث تعيش مرآة التأليف في المتصفّح، ولا
# تُشحَن في صورة الخادوم. تُصنَّف صراحةً، ويُثبَت أدناه أن الخادوم لا يصل إليها.
AUTHORING_COMPANIONS = ['acs_engineering_approval.py']
browser_specs |= set(AUTHORING_COMPANIONS)
all_specs = sorted(x for x in os.listdir(ROOT)
                   if re.match(r'^acs_.*\.(py|json)$', x))
unclassified = []
for a in all_specs:
    if (a in backend_files or a in image_files or a in browser_specs
            or a in OFFLINE_TOOLS):
        continue
    unclassified.append(a)
note('%d canonical file(s) are browser-mirrored: %s'
     % (len(browser_specs), ', '.join(sorted(browser_specs))))
note('%d offline command-line tool(s), deployed nowhere by design: %s'
     % (len(OFFLINE_TOOLS), ', '.join(OFFLINE_TOOLS)))
chk('every canonical file is classified: image, browser mirror or offline tool',
    unclassified == [], ', '.join(unclassified))
for t in AUTHORING_COMPANIONS:
    chk('the authoring companion %s is genuinely unreachable from the API' % t,
        t[:-3] not in closure)
    chk('the authoring companion %s is not shipped in the container' % t,
        t not in image_files)
for t in OFFLINE_TOOLS:
    chk('the offline tool %s is genuinely unreachable from the API' % t,
        t[:-3] not in closure)
    chk('the offline tool %s is not shipped in the container' % t,
        t not in image_files)
# المرآة نفسها مفحوصة بايت-بايت في القسم 5؛ هنا نتحقّق فقط من أن كل مواصفة
# متصفّح لها متغيّر معلَن يُقارَن هناك، فلا تفلت واحدة من فحص الانحراف
mirrored_vars = {sp for sp, _ in SPEC_VARS}
for spec in sorted(x for x in browser_specs if x.endswith('.json')):
    chk('the browser-mirrored %s is covered by the drift check' % spec,
        spec in mirrored_vars)
chk('a browser-only layer is not silently required by the backend',
    all((s.replace('.json', '') not in closure)
        for s in browser_specs if s.endswith('.json')))

print('\n== 11c · THE VISUAL QUALITY BRIDGE AND ITS VENDORED MODULES ==')
# جسر الجودة يعيش داخل سكربت الوحدة، فلا تمسكه علامات الكتل الكلاسيكية —
# يُفحص هنا صراحةً: موجود مرّة واحدة، وخطّاف الحلقة واحد، ولا CDN وقت التشغيل.
chk('the PBR bridge is present exactly once',
    app.count('/* ===== ACS PBR BRIDGE (module scope) ===== */') == 1
    and app.count('/* ===== END ACS PBR BRIDGE ===== */') == 1)
chk('the render loop hook is present exactly once',
    app.count('window.__ACS_PQ__&&window.__ACS_PQ__.composer') == 1)
chk('the original render call survives as the fallback path',
    'else{renderer.render(scene,camera);}' in app)
chk('post-processing modules import from the local vendor origin only',
    app.count("import('three/addons/postprocessing/") >= 4
    and "import('http" not in app and 'import("http' not in app)
_pq = json.loads(rd('acs_pbr.json'))
for mod in _pq['post_processing_modules']:
    chk('the vendor build verifies %s' % mod,
        'examples/jsm/' + mod in rd('tools/netlify-build.sh'))
chk('the local texture root exists and documents the empty-set default',
    exists('public/assets/materials/README.txt')
    and _pq['texture_policy']['local_texture_sets'] == []
    and _pq['texture_policy']['remote_texture_allowed'] is False)
chk('no remote texture or environment host is referenced by the quality layer',
    _pq['remote_environment_allowed'] is False
    and _pq['texture_policy']['allowed_schemes'] == [])

print('\n== 11d · THE ARCHITECTURAL DETAIL LAYER (PHASE 9.2) ==')
# طبقة التفصيل المعماري تمتد فوق 9.1 بلا محرّك ثانٍ ولا سجلّ مكرّر.
chk('the archdetail bridge is present exactly once',
    app.count('/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */') == 1
    and app.count('/* ===== END ACS ARCH DETAIL BRIDGE ===== */') == 1)
chk('the archdetail generated block is present exactly once',
    app.count('/* ===== ACS ARCH DETAIL '
               '(generated by tools/build_archdetail_browser.py) ===== */')
    == 1 and app.count('/* ===== END ACS ARCH DETAIL ===== */') == 1)
chk('the 9.1 render loop hook is still single — no second dispatcher',
    app.count('window.__ACS_PQ__&&window.__ACS_PQ__.composer') == 1)
_ad = json.loads(rd('acs_archdetail.json'))
chk('the layer extends acs.pbr and never reverses',
    _ad['extends'] == 'acs.pbr' and _ad['reverse_arrow_exists'] is False
    and _ad['writes_to_model'] is False)
_ada = app.index('/* ===== ACS ARCH DETAIL '
                  '(generated by tools/build_archdetail_browser.py) ===== */')
_ade = app.index('/* ===== END ACS ARCH DETAIL ===== */')
_adb = app.index('/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */')
_adz = app.index('/* ===== END ACS ARCH DETAIL BRIDGE ===== */')
_adlayer = app[_ada:_ade] + app[_adb:_adz]
chk('no network scheme in the architectural layer',
    'http://' not in _adlayer and 'https://' not in _adlayer)
chk('no url-based gltf, remote texture or executable asset policy',
    _ad['url_gltf_allowed'] is False
    and _ad['remote_texture_allowed'] is False
    and _ad['executable_assets_allowed'] is False
    and _ad['texture_policy_inherited_from'] == 'acs.pbr')
chk('the bridge adds only AD_* presentation groups',
    all(g.startswith('AD_') for g in _ad['group_names'].values()))
chk('the archdetail layer needs no new vendored module',
    'archdetail' not in rd('tools/netlify-build.sh'))

print('\n== 11d2 · ONE VIEWPORT CONTRACT ACROSS EVERY LAYER ==')
sys.path.insert(0, ROOT)
import check_integration as IG2                                   # noqa: E402
import acs_pbr as _PQ_MOD                                         # noqa: E402
_ifails, _ifacts = IG2.check(ROOT)
chk('the integration gate passes on this tree', _ifails == [],
    '; '.join(_ifails[:3]))
chk('the contract version is declared in the specification',
    bool(_ifacts.get('contract')), str(_ifacts.get('contract')))
chk('the python layer declares the same contract at runtime',
    _ifacts.get('python_contract') == _ifacts.get('contract'))
chk('the netlify build refuses to publish a partially merged tree',
    'check_integration.py' in rd('tools/netlify-build.sh'))
chk('the black-viewport test refuses to run on a partial tree instead of '
    'raising AttributeError',
    'PARTIALLY MERGED TREE'
    in rd('tests/phase9_2/test_black_viewport.py'))
chk('the boot harness announces its version so a stale copy is visible',
    'HARNESS: verify_page_boot'
    in rd('tests/deploy/verify_page_boot.js'))
chk('every contract symbol is callable in the python layer',
    all(callable(getattr(_PQ_MOD, _s, None))
        for _s in json.loads(rd('acs_pbr.json'))
        ['viewport_contract_symbols']))
chk('every contract symbol is mirrored in the shipped page',
    all(m in app for m in ('pqBoundsMember', 'pqBoundsFromDescriptors',
                            'pqCameraClip', 'pqFrustumContains',
                            'pqMaterialSafe')))

print('\n== 11e · THE VIEWPORT VISIBILITY APPARATUS (BLACK-SCREEN REMEDIATION) ==')
chk('the decoded-pixel analyser ships',
    exists('tests/deploy/lib_viewport_pixels.js')
    and exists('tests/deploy/test_viewport_pixels.js'))
chk('the boot harness separates BOOT from VISUAL MODEL',
    'VISUAL MODEL' in rd('tests/deploy/verify_page_boot.js')
    and 'BOOT:' in rd('tests/deploy/verify_page_boot.js'))
chk('the boot harness loads real canonical fixtures, not an empty workspace',
    'base_fixtures.json' in rd('tests/deploy/verify_page_boot.js')
    and 'setModel' in rd('tests/deploy/verify_page_boot.js'))
chk('the discredited PNG byte-size heuristic is gone for good',
    'png.length>25000' not in rd('tests/deploy/verify_page_boot.js')
    and 'uniform black frame' not in rd('tests/deploy/verify_page_boot.js'))
chk('the analyser decodes RGBA and reports luminance statistics',
    all(k in rd('tests/deploy/lib_viewport_pixels.js') for k in (
        'getImageData', 'luminance_mean', 'luminance_variance',
        'near_black_pct', 'luminance_buckets')))
_pq2 = json.loads(rd('acs_pbr.json'))
chk('the sky dome and ground plane are canonically excluded from bounds',
    'SKY_DOME' in _pq2['viewport_bounds']['excluded_object_names']
    and 'GROUND_PLANE' in _pq2['viewport_bounds']['excluded_object_names'])
chk('the page names the sky dome and ground plane so they can be excluded',
    "sky.name='SKY_DOME'" in app and "g.name='GROUND_PLANE'" in app)
chk('the camera clip contract is applied by the bridge, not just declared',
    'pqCameraClip' in app and 'pqFrustumContains' in app
    and '_pqApplyCameraSafety' in app)
chk('the render diagnostics bridge is present and presentation-only',
    'window.ACS.renderDiagnostics' in app
    and 'exposes_canonical_state:false' in app)
chk('presentation material application fails open to the engineering material',
    'pqMaterialSafe' in app and 'MATERIAL_FAIL_OPEN' in app)
chk('the composer is resized with the renderer',
    'composer.setSize' in app and '_resizeHooked' in app)
chk('the black-viewport regression ships and is wired into the phase gate',
    exists('tests/phase9_2/test_black_viewport.py')
    and 'test_black_viewport.py' in rd('tests/phase9_2/run_all.sh')
    and 'test_viewport_pixels.js' in rd('tests/phase9_2/run_all.sh'))

print('\n== 11f · THE TRANSFORM AND ALIGNMENT CONTRACT ==')
_tc = json.loads(rd('acs_pbr.json'))['transform_contract']
chk('the coordinate space chain is declared end to end',
    _tc['spaces'][0] == 'PROJECT' and _tc['spaces'][-1] == 'WORLD'
    and len(_tc['spaces']) == 7)
chk('the axis convention is declared explicitly',
    _tc['axis']['y'] == 'VERTICAL_ELEVATION'
    and _tc['axis']['x'] == 'HORIZONTAL_WIDTH')
chk('the elevation and host rules say EXACTLY ONCE',
    'EXACTLY ONCE' in _tc['elevation_rule']
    and 'exactly once' in _tc['host_rule'])
chk('the plate and rack rules are declared canonically',
    'floating plate' in _tc['plate_rule']
    and 'MINUS the offset' in _tc['rack_rule'])
chk('the tolerance is small and carries its justification',
    0 < _tc['roof_tolerance_m'] <= 0.05
    and len(_tc['tolerance_note']) > 40)
chk('presentation offsets to hide misalignment are forbidden',
    'PRESENTATION_OFFSET_TO_HIDE_MISALIGNMENT' in _tc['forbidden']
    and 'AUTOMATIC_SNAP_TO_NEAREST_HOST' in _tc['forbidden'])
chk('the shipped compiler derives its rack block from the contract',
    'pqRackBlock([rx,rz,rw,rd],R)' in app
    and 'const bw=Math.min(+R.w||rw,rw), bd=Math.min(+R.d||rd,rd);'
    not in app)
# F-07 / KI-3 — كانت هذه التوكيدة تثبّت السلوك القديم («الاصطلاح مُبقًى عمداً»)،
# فاستُبدلت بتوكيدة أشدّ على السلوك الجديد: الامتداد من عقد الامتداد الوحيد،
# ونصّ اللوح على مقاس الموقع مُزال من المصرِّف نصّاً لا اصطلاحاً.
chk('the level plate is derived from the room footprint through the single '
    'shared extent contract, and the site-wide plate is gone from the compiler',
    'pqPlateRect((fdef.rooms||[]).map(r=>r.rect)' in app
    and 'slabStrips(_pr[0],_pr[1],_pr[2],_pr[3],holes)' in app
    and 'slabStrips(0,0,site.w,site.d,holes)' not in app
    and 'PHASE10_FOOTPRINT_PLATE' in app
    and 'plate_overhang' in app
    and 'change_requires_approval:true' in app)
chk('the plate policy change is provenanced, not silent: the new name, the '
    'previous name, what pinned it and why it changed all ship',
    _PQ_MOD.PLATE_POLICY['policy'] == 'PHASE10_FOOTPRINT_PLATE'
    and _PQ_MOD.PLATE_POLICY['previous_policy'] == 'PHASE1_SITE_WIDE_PLATE'
    and _PQ_MOD.PLATE_POLICY['previous_pinned_by'] == 'PHASE4_GOLDEN_BASELINE'
    and _PQ_MOD.PLATE_POLICY['extent_source'] == 'plate_rect'
    and len(_PQ_MOD.PLATE_POLICY['reason']) > 60
    and _PQ_MOD.PLATE_POLICY['changes_canonical_model'] is False
    and _PQ_MOD.PLATE_POLICY['changes_quantities'] is False
    and 'PHASE1_SITE_WIDE_PLATE' in app)
chk('the Python compiler and the page agree on the plate extent contract',
    'PBR.plate_rect(' in rd('acs_compiler.py')
    and 'PBR.slab_strips(' in rd('acs_compiler.py')
    and 'site["w"], 0.15, site["d"], "floor", "FLOOR|%s|slab|0" % fkey'
    not in rd('acs_compiler.py'))
chk('alignment diagnostics ship and never move an object',
    'window.ACS.alignmentDiagnostics' in app
    and 'objects_moved_to_fit:0' in app
    and 'moved_to_fit:false' in app)
chk('world bounds are measured only after updateMatrixWorld',
    'o.updateMatrixWorld(true);' in app)
chk('the seven ALIGN issue codes are declared and none is blocking',
    all(c in json.loads(rd('acs_pbr.json'))['issue_codes'] for c in (
        'ALIGN_TRANSFORM_UNRESOLVED', 'ALIGN_HOST_NOT_FOUND',
        'ALIGN_OBJECT_OUTSIDE_HOST', 'ALIGN_LEVEL_MISMATCH',
        'ALIGN_ROOF_DETACHED', 'ALIGN_DOUBLE_TRANSFORM',
        'ALIGN_AXIS_MISMATCH'))
    and not any(c.startswith('ALIGN_') for c in
                json.loads(rd('acs_pbr.json'))['blocking_issue_codes']))
chk('the alignment regression ships and is wired into the phase gate',
    exists('tests/phase9_2/test_alignment.py')
    and 'test_alignment.py' in rd('tests/phase9_2/run_all.sh'))

print('\n== 11g · THE HARNESS NEVER TOUCHES MODULE SCOPE ==')
import check_harness_encapsulation as HE                          # noqa: E402
_hfails, _hscanned = HE.check(ROOT)
chk('every page.evaluate body uses public bridges only', _hfails == [],
    '; '.join(_hfails[:2]))
chk('the scan is not vacuous — evaluate bodies were actually parsed',
    _hscanned >= 10, 'bodies=%d' % _hscanned)
chk('gate self-test: a module-scoped access is caught',
    HE.check_source_for_test() if hasattr(HE, 'check_source_for_test')
    else len(HE.evaluate_bodies(HE.strip_noise(
        "pg.evaluate(() => { scene.updateMatrixWorld(true); });"))) == 1)
chk('gate self-test: an explanatory comment naming scene is NOT a violation',
    'scene' not in HE.strip_noise('/* touches scene here */ var a=1;'))
chk('the narrow read-only snapshot bridge exists instead of a global',
    'window.ACS.canonicalTransformSnapshot' in app
    and 'exposes_coordinates:false' in app)
chk('engine state was NOT promoted to the global scope to satisfy a test',
    'window.scene' not in page and 'window.renderer' not in page
    and 'window.camera' not in page)
chk('the harness asks for the snapshot bridge during boot',
    'canonicalTransformSnapshot' in rd('tests/deploy/verify_page_boot.js'))

print('\n== 11h · ONE AUTHORITATIVE API BASE, AND THE API ERROR CONTRACT ==')
import check_api_base as AB                                       # noqa: E402
_afails, _ainfo = AB.check(ROOT)
chk('the shipped page declares exactly one API origin and every /v1 call '
    'is classified', _afails == [], '; '.join(_afails[:2]))
chk('the configured origin is https', str(_ainfo.get('base','')).startswith('https://'),
    str(_ainfo.get('base')))
chk('the CSP connect-src allows exactly that origin — otherwise the browser '
    'blocks every call from the deployed page', _ainfo.get('csp_ok') is True)
chk('gate self-test: a second hard-coded origin would be caught',
    'route every call through ACS_API.url()' in rd('tools/check_api_base.py'))
chk('the error-contract module is deployed and copied into the image',
    exists('acs_api_errors.py') and 'acs_api_errors.py' in docker)
_err = rd('acs_api_errors.py')
chk('the error contract declares a version and the ACS_UPSTREAM_* family',
    'ERROR_CONTRACT_VERSION' in _err and _err.count('ACS_UPSTREAM_') > 20)
chk('the envelope is the only failure shape: ok/error{code,message,request_id,'
    'retryable,upstream}',
    all(('"%s"' % k) in _err or ("'%s'" % k) in _err
        for k in ('code', 'message', 'request_id', 'retryable', 'upstream')))
chk('secrets are redacted before any message leaves the process',
    'def redact' in _err and 'sk-ant-' in _err and '[REDACTED]' in _err)
_api = rd('acs_understand_api.py')
chk('the API imports the shared error contract rather than re-inventing one',
    'import acs_api_errors as E' in _api)
chk('no failure path returns a traceback or an exception string to the client',
    'HTTPException(500' not in _api and 'str(e)[:900]' not in _api)
chk('the envelope middleware is inside CORS so error responses stay readable',
    _api.index('acs_envelope_middleware') < _api.index('CORSMiddleware,'))
chk('/health and /ready are both declared, and neither returns a credential',
    '@app.get("/health")' in _api and '@app.get("/ready")' in _api
    and 'def _api_key_configured' in _api)
chk('startup validation names missing variables only, never values',
    '_startup_env_check' in _api and 'MISSING (names only)' in _api)
chk('generation is bounded by a server deadline that answers 504 JSON',
    'run_bounded' in _api and 'ACS_TIMEOUT' in _api)
chk('rate limits are unchanged and 429 carries Retry-After',
    all(k in _api for k in ('ACS_RL_GEN_HOUR', 'ACS_RL_GEN_DAY',
                            'ACS_RL_EDIT_HOUR', 'ACS_RL_GLOBAL_DAY'))
    and 'Retry-After' in _api)
chk('the deterministic JSON parser replaced the naive brace slice',
    'def scan_top_level_json' in rd('acs_understand.py')
    and 'rfind("}")' not in rd('acs_understand.py'))
chk('the live backend verifier ships and defaults to no model spend',
    exists('tests/deploy/verify_backend_live.py')
    and "--generation" in rd('tests/deploy/verify_backend_live.py'))
chk('the live verifier reads the base from the page, not a second copy',
    'CONFIGURED_BASE' in rd('tests/deploy/verify_backend_live.py'))

print('\n== 11i · ONE OUTPUT BUDGET AND A COMPLETION CONTRACT ==')
import acs_api_errors as _ERR                                    # noqa: E402
import acs_generation as _GEN                                     # noqa: E402
_gen_src = rd('acs_generation.py')
_api_err_src = rd('acs_api_errors.py')
_und = rd('acs_understand.py')
chk('the generation budget module is deployed and copied into the image',
    exists('acs_generation.py') and 'acs_generation.py' in docker)
chk('it declares a contract version', bool(_GEN.GENERATION_CONTRACT_VERSION))
chk('there is exactly ONE authoritative output budget name',
    'ACS_LLM_MAX_OUTPUT_TOKENS' in _gen_src and _GEN.max_output_tokens() > 0)
chk('every stage budget derives from it — no free token constant remains in the '
    'generation path',
    not re.search(r'max_tokens\s*=\s*\d{4,}', _und)
    and 'ACS_MAX_TOKENS", "32000"' not in _und)
chk('the deployment declares the budget and the escalation bounds',
    all(k in ry for k in ('ACS_LLM_MAX_OUTPUT_TOKENS', 'ACS_MAX_ESCALATIONS',
                          'ACS_MAX_GROUP_SPLITS')))
# W2-E: كان هذا الفحص مربوطاً بالسلسلة الحرفية `if stop == "max_tokens"`.
# الثابت المحروس سلوكيّ — «الحكم على اكتمال الرد يسبق تحليله» — والسلسلة
# مجرّد تهجئة له، فتغيّرت التهجئة (صار الحكم مشتقّاً من دلالة الرد) وسقط
# الفحص على ثابتٍ لم يُكسَر. يُقاس الآن بمواضع العُقد لا بنصّها.
_und_tree = ast.parse(_und)
_impl = next((n for n in ast.walk(_und_tree)
              if isinstance(n, ast.FunctionDef) and n.name == '_call_llm_impl'),
             None)
_verdict_lines = [n.lineno for n in ast.walk(_impl or _und_tree)
                  if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute)
                  and n.func.attr == 'classify_response']
_extract_line = next((n.lineno for n in ast.walk(_und_tree)
                      if isinstance(n, ast.FunctionDef)
                      and n.name == 'extract_json'), 0)
chk('the stop-reason contract is judged BEFORE parsing',
    bool(_verdict_lines) and bool(_extract_line)
    and min(_verdict_lines) < _extract_line,
    (_verdict_lines, _extract_line))
chk('a max_tokens stop raises the truncation code rather than returning text',
    'E.RESP_TRUNCATED' in _und and 'refusal' in _api_err_src
    and 'raise E.AcsApiError(' in _und
    and _ERR.classify_response('max_tokens', 500, 1, 0)[1]
    == _ERR.ACS_UPSTREAM_TRUNCATED)
# وحالةٌ رابعة قِيست حيّاً: ميزانيةٌ كاملة في محتوى غير مرئي. لا هي فراغ ولا
# هي نصفُ JSON — ولها رمزها، وهي دليل بلوغ سقفٍ يُشطَر ويُصعَّد.
chk('a full budget spent on non-visible content is not called an empty reply',
    _ERR.classify_response('max_tokens', 0, 0, 1)[1]
    == _ERR.ACS_UPSTREAM_NO_VISIBLE_OUTPUT
    and _ERR.ACS_UPSTREAM_NO_VISIBLE_OUTPUT in _ERR.CEILING_CODES
    and _ERR.ACS_UPSTREAM_TRUNCATED in _ERR.CEILING_CODES)
chk('every ceiling code is mapped to a user-facing state in the shipped page',
    all(c in rd('public/app/trust/core.js') for c in _ERR.CEILING_CODES))
chk('brace repair of a truncated reply is gone from the codebase',
    'def _balance_json' not in _und)
chk('the input-length heuristic that mis-routed the production prompt is gone',
    'def _should_go_deep' not in _und and 'plan_strategy' in _und)
chk('truncation never retries the identical request — it changes strategy',
    'MAX_STRATEGY_ESCALATIONS' in _gen_src and '_detail_group_split' in _und)
chk('the escalation and split limits are finite',
    0 <= _GEN.MAX_STRATEGY_ESCALATIONS <= 3 and 1 <= _GEN.MAX_GROUP_SPLITS <= 4)
chk('stage-1 geometry is authoritative and any override is reported',
    'STAGE_RECT_OVERRIDE_REJECTED' in _und and 'STAGE_ADDED_ZONES' in _und)
chk('the compact-output rule reaches the shipped instructions',
    'COMPACT_RULE' in _gen_src and 'G.COMPACT_RULE' in _und)
chk('generation telemetry is aggregate-only in the API response',
    'def _generation_summary' in api_src
    and 'requirements' not in api_src.split('def _generation_summary')[1][:600])
chk('the production prompt classifies SMALL and takes one stage',
    _GEN.plan_strategy(
        "مستودع بسيط 20×15م، دور واحد، منطقة تخزين ومنطقة استقبال.",
        "warehouse", 20, 15, 1)["size_class"] == _GEN.SMALL)
chk('a distribution-centre prompt is routed to staged generation',
    _GEN.plan_strategy(
        "مركز توزيع 120×80م: استلام، تخزين، التقاط، تغليف، فرز، شحن، "
        "12 رصيف تحميل، مكاتب", "warehouse", 120, 80, 1)["strategy"]
    == _GEN.STRATEGY_STAGED)

print('\n== 11j · THE LIVE MODEL RENDER-RECOVERY CONTRACT ==')
_RR = _PQ_MOD.RR
chk('the render-recovery contract is declared in the canonical spec',
    _PQ_MOD.RENDER_RECOVERY_CONTRACT == 'render-recovery/1.0.0')
chk('the spec, the python layer and the shipped page all carry it',
    'render_recovery' in rd('acs_pbr.json')
    and 'RENDER_RECOVERY_CONTRACT' in rd('acs_pbr.py')
    and 'render-recovery/1.0.0' in app)
chk('every declared symbol exists in the python layer',
    all(hasattr(_PQ_MOD, s) for s in _PQ_MOD.RENDER_RECOVERY_SYMBOLS))
chk('every declared symbol has a browser mirror in the shipped page',
    all(('pq' + s.title().replace('_', '')) in app
        for s in _PQ_MOD.RENDER_RECOVERY_SYMBOLS))
chk('the model-load path reconciles the camera through the contract',
    'acsReconcileCamera' in app
    and 'window.ACS.verifyVisibleModel' in app)
chk('the model-load path assigns near and far — the defect was that it never did',
    'camera.near=c.near; camera.far=c.far' in app.replace('\n', ' ')
    or 'camera.near=c.near' in app)
chk('one recovery cycle only, and it is declared',
    int(_RR['max_recovery_cycles']) == 1 and 'RENDER_BLACK_VIEWPORT' in app)
chk('post-processing fails open to the base renderer, never to black',
    '_pqDisableComposer' in app and 'POSTPROCESS_FAIL_OPEN' in rd('acs_pbr.json'))
chk('render failure classes are separate from transport classes in the page',
    'ACS_TRANSPORT_CLASSES' in app and 'RENDER_BLACK_VIEWPORT' in app
    and 'window.ACS.lastFailure' in app)
chk('the large live-model regression fixtures ship with the tests',
    exists('tests/phase9_2/fixtures/live_large_generated.json')
    and exists('tests/phase9_2/fixtures/live_large_generated_outlier.json'))
chk('the large fixture declares its provenance honestly',
    'RECONSTRUCTED' in rd('tests/phase9_2/fixtures/live_large_generated.json')
    and '"captured_from_live_backend": false'
    in rd('tests/phase9_2/fixtures/live_large_generated.json').lower())
chk('the boot harness loads the large fixtures and the outlier variant',
    'live_large_generated_outlier' in rd('tests/deploy/verify_page_boot.js'))
chk('the requirement-coverage and duplication audits ship',
    'def coverage_report' in rd('acs_generation.py')
    and 'def duplication_report' in rd('acs_generation.py'))
chk('one stray coordinate no longer moves the camera: proven here, not asserted',
    _PQ_MOD.robust_bounds([
        {'is_mesh': True, 'parent_names': ['BUILDING'], 'name': 'WALL|F0|a',
         'box': {'min': [0, 0, 0], 'max': [10, 3, 8]}},
        {'is_mesh': True, 'parent_names': ['BUILDING'], 'name': 'ELEC|F0|p',
         'box': {'min': [99999, 0, 0], 'max': [99999.2, .2, .2]}}
    ])['bounds']['radius'] < 20)

print('\n== 12 · TEST-ONLY MATERIAL IS NOT REQUIRED BY PRODUCTION ==')
chk('no deployed source imports anything from tests/',
    not any(re.search(r'from\s+tests|import\s+tests|[\'"]tests/', rd(rel))
            for rel in sorted(set(DEPLOYED)) if exists(rel)))
chk('the Dockerfile copies nothing from tests/', 'tests' not in docker)
chk('the Netlify publish directory contains no test fixture',
    not os.path.isdir(os.path.join(ROOT, 'public', 'tests')))

print('\n' + '─' * 62)
for n in notes:
    print('NOTE: %s' % n)
print('DEPLOY VERIFICATION: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
