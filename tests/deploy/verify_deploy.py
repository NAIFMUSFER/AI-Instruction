# -*- coding: utf-8 -*-
"""تحقّق النشر — حتمي، ويحسب ما يلزم بدل أن يفترضه.

القاعدة التي يفرضها هذا الملفّ: لا يُعدّ ملفّ منشوراً لمجرّد وجوده في المستودع.
كل وحدة يصل إليها مدخل الخادوم فعلاً يجب أن ينسخها Dockerfile، وكل كتلة متصفّح
مولَّدة يجب أن تكون داخل الصفحة التي ينشرها Netlify، ولا يجوز أن يتسرّب مسار
صندوق رمليّ ولا سرّ إلى ما يُنشر.
"""
import ast
import hashlib
import json
import os
import re
import sys

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
import check_index_guard as IG                                    # noqa: E402
_page_fails = IG.check_file(os.path.join(ROOT, 'public', 'index.html'))
chk('public/index.html passes the structural guard', _page_fails == [],
    '; '.join(_page_fails[:3]))
chk('the netlify build runs the same guard before publishing',
    'check_index_guard.py' in rd('tools/netlify-build.sh')
    and 'exit 1' in rd('tools/netlify-build.sh'))
_good = rd('public/index.html')
chk('guard self-test: an EMPTY page is refused',
    IG.check_page_text('', 0) != [])
chk('guard self-test: a truncated page is refused',
    IG.check_page_text(_good[:200000]) != [])
chk('guard self-test: a page below the generated minimum is refused',
    any('below the generated minimum' in x
        for x in IG.check_page_text('<!DOCTYPE html><html><body>x</body>'
                                    '</html>')))
chk('guard self-test: a missing importmap is refused',
    any('importmap' in x for x in IG.check_page_text(
        _good.replace('<script type="importmap">',
                      '<script type="importmap-disabled">', 1))))
chk('guard self-test: an importmap with invalid JSON is refused',
    any('not valid JSON' in x for x in IG.check_page_text(
        _good.replace('"three":', '"three" broken:', 1))))
chk('guard self-test: an importmap pointing at a CDN is refused',
    any('pinned local vendor' in x for x in IG.check_page_text(
        _good.replace(IG.IMPORTMAP_THREE,
                      'https://unpkg.com/three/build/three.module.js', 1))))
chk('guard self-test: missing renderer initialization is refused',
    any('renderer initialization' in x for x in IG.check_page_text(
        _good.replace('new THREE.WebGLRenderer(',
                      'new THREE.DisabledRenderer(', 1))))
chk('guard self-test: missing scene initialization is refused',
    any('scene initialization' in x for x in IG.check_page_text(
        _good.replace('new THREE.Scene(', 'new THREE.Absent(', 1))))
chk('guard self-test: missing render loop is refused',
    any('render loop' in x for x in IG.check_page_text(
        _good.replace('renderer.setAnimationLoop', 'renderer.noLoop', 1))))
chk('guard self-test: a missing generated 9.1 block is refused',
    any('PBR QUALITY' in x for x in IG.check_page_text(
        _good.replace('/* ===== END ACS PBR QUALITY ===== */', '', 1))))
chk('guard self-test: a duplicated generated 9.2 block is refused',
    any('ARCH DETAIL' in x for x in IG.check_page_text(
        _good + '\n/* ===== END ACS ARCH DETAIL ===== */')))
chk('guard self-test: a missing file path is refused',
    IG.check_file(os.path.join(ROOT, 'public', 'no_such_page.html')) != [])
chk('the guard checks every phase layer structurally (10 marker pairs)',
    len(IG.PAIRS) == 10 and len(IG.ENGINE_NEEDLES) == 5)

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

# ----------------------------------------- 4. الواجهة: كتل مولَّدة داخل الصفحة --
print('\n== 4 · THE PUBLISHED PAGE CARRIES EVERY GENERATED BROWSER BLOCK ==')
page = rd('public/index.html')
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
for tool, m in MARKERS:
    chk('the page carries exactly one %s' % (m[:58] + ('…' if len(m) > 58 else '')),
        page.count(m) == 1, '%d occurrence(s), from %s' % (page.count(m), tool))

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
    m = re.search(re.escape('const ' + var) + r'\s*=\s*(\{.*?\});\s*\n', page, re.S)
    if not m:
        chk('%s is mirrored into the page as %s' % (spec, var), False, 'not found')
        continue
    try:
        mirrored = json.loads(m.group(1))
        ok = mirrored == json.loads(rd(spec))
    except ValueError as e:
        ok = False
        mirrored = str(e)
    chk('%s in the page is byte-equal to the file on disk' % var, ok)

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
DEPLOYED += sorted(m + '.py' for m in closure)
DEPLOYED += [x for x in os.listdir(ROOT) if re.match(r'^acs_.*\.(py|json)$', x)]
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
chk('the API never returns the key itself, only whether one is set',
    '"key": bool(' in api_src and 'ANTHROPIC_API_KEY' in api_src
    and not re.search(r'return[^\n]*os\.environ\.get\("ANTHROPIC_API_KEY"\)', api_src))

# ------------------------------------------------ 11. اتّساق داخلي للحزمة --
print('\n== 11 · THE PRODUCTION BUNDLE IS INTERNALLY SELF-CONSISTENT ==')
chk('the published page is a single self-contained file',
    os.path.getsize(os.path.join(ROOT, 'public/index.html')) > 100000)
srcs = re.findall(r'<script[^>]+src="([^"]+)"', page)
links = re.findall(r'<link[^>]+href="([^"]+)"', page)
remote = [u for u in srcs + links
          if u.startswith('http://') or u.startswith('//')
          or (u.startswith('https://') and 'acs-engine.onrender.com' not in u)]
chk('the page loads no remote script or stylesheet at runtime', remote == [],
    ', '.join(remote[:3]))
local_refs = [u for u in srcs + links if u.startswith('./') or u.startswith('/')
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
must_vendor = re.findall(r'"\$VEN/([^"]+)"', nb)
must_vendor = sorted(set(v for v in must_vendor
                         if v.count('/') >= 1 and not v.endswith('/')))
must_vendor = [v.replace('$THREE', '0.160.0').replace('$SHIMS', '1.8.2')
                .replace('$PDFJS', '4.0.379') for v in must_vendor]
present = [v for v in must_vendor
           if os.path.isfile(os.path.join(vend, v))
           and os.path.getsize(os.path.join(vend, v)) > 0]
if len(present) == len(must_vendor) and must_vendor:
    chk('every runtime library the build script requires is vendored '
        '(%d files)' % len(present), True)
else:
    note('public/vendor holds %d file(s); the build script requires %d and %d '
         'are present. This sandbox has no network, so tools/netlify-build.sh '
         'has never run here. Netlify populates this directory at build time. '
         'Three.js-dependent 3D runtime behaviour in this checkout is '
         'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.'
         % (len(vendor_files), len(must_vendor), len(present)))
    chk('the missing runtime libraries are fetched by the declared build '
        'command, not expected in the repository',
        bool(cmd) and 'netlify-build.sh' in cmd.group(1))
chk('the vendor fetch script pins exact versions',
    all(v in rd('tools/netlify-build.sh')
        for v in ('THREE=0.160.0', 'SHIMS=1.8.2', 'PDFJS=4.0.379')))
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
    page.count('/* ===== ACS PBR BRIDGE (module scope) ===== */') == 1
    and page.count('/* ===== END ACS PBR BRIDGE ===== */') == 1)
chk('the render loop hook is present exactly once',
    page.count('window.__ACS_PQ__&&window.__ACS_PQ__.composer') == 1)
chk('the original render call survives as the fallback path',
    'else{renderer.render(scene,camera);}' in page)
chk('post-processing modules import from the local vendor origin only',
    page.count("import('three/addons/postprocessing/") >= 4
    and "import('http" not in page and 'import("http' not in page)
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
    page.count('/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */') == 1
    and page.count('/* ===== END ACS ARCH DETAIL BRIDGE ===== */') == 1)
chk('the archdetail generated block is present exactly once',
    page.count('/* ===== ACS ARCH DETAIL '
               '(generated by tools/build_archdetail_browser.py) ===== */')
    == 1 and page.count('/* ===== END ACS ARCH DETAIL ===== */') == 1)
chk('the 9.1 render loop hook is still single — no second dispatcher',
    page.count('window.__ACS_PQ__&&window.__ACS_PQ__.composer') == 1)
_ad = json.loads(rd('acs_archdetail.json'))
chk('the layer extends acs.pbr and never reverses',
    _ad['extends'] == 'acs.pbr' and _ad['reverse_arrow_exists'] is False
    and _ad['writes_to_model'] is False)
_ada = page.index('/* ===== ACS ARCH DETAIL '
                  '(generated by tools/build_archdetail_browser.py) ===== */')
_ade = page.index('/* ===== END ACS ARCH DETAIL ===== */')
_adb = page.index('/* ===== ACS ARCH DETAIL BRIDGE (module scope) ===== */')
_adz = page.index('/* ===== END ACS ARCH DETAIL BRIDGE ===== */')
_adlayer = page[_ada:_ade] + page[_adb:_adz]
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
    all(m in page for m in ('pqBoundsMember', 'pqBoundsFromDescriptors',
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
    "sky.name='SKY_DOME'" in page and "g.name='GROUND_PLANE'" in page)
chk('the camera clip contract is applied by the bridge, not just declared',
    'pqCameraClip' in page and 'pqFrustumContains' in page
    and '_pqApplyCameraSafety' in page)
chk('the render diagnostics bridge is present and presentation-only',
    'window.ACS.renderDiagnostics' in page
    and 'exposes_canonical_state:false' in page)
chk('presentation material application fails open to the engineering material',
    'pqMaterialSafe' in page and 'MATERIAL_FAIL_OPEN' in page)
chk('the composer is resized with the renderer',
    'composer.setSize' in page and '_resizeHooked' in page)
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
    'pqRackBlock([rx,rz,rw,rd],R)' in page
    and 'const bw=Math.min(+R.w||rw,rw), bd=Math.min(+R.d||rd,rd);'
    not in page)
chk('the Phase 1 site-wide plate convention is retained deliberately and its '
    'deviation is measured, not hidden',
    'slabStrips(0,0,site.w,site.d,holes)' in page
    and 'pqPlateRect((fdef.rooms||[]).map(r=>r.rect)' in page
    and 'plate_overhang' in page
    and 'change_requires_approval:true' in page)
chk('alignment diagnostics ship and never move an object',
    'window.ACS.alignmentDiagnostics' in page
    and 'objects_moved_to_fit:0' in page
    and 'moved_to_fit:false' in page)
chk('world bounds are measured only after updateMatrixWorld',
    'o.updateMatrixWorld(true);' in page)
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
    'window.ACS.canonicalTransformSnapshot' in page
    and 'exposes_coordinates:false' in page)
chk('engine state was NOT promoted to the global scope to satisfy a test',
    'window.scene' not in page and 'window.renderer' not in page
    and 'window.camera' not in page)
chk('the harness asks for the snapshot bridge during boot',
    'canonicalTransformSnapshot' in rd('tests/deploy/verify_page_boot.js'))

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
