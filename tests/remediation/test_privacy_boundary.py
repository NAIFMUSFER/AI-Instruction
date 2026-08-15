# -*- coding: utf-8 -*-
"""F-12 + الخصوصية — لا مطابقة مدّعاة، ولا بيانات زائر محتفَظ بها بلا إفصاح.

عيبان يتقاطعان في نقطة واحدة: ما تقوله الواجهة عن نفسها.

  F-12 · المطابقة الزائفة: نظامٌ لا يحمّل حزمة أنظمة موثّقة لا يجوز أن تخرج منه
  عبارة «مطابق للكود» أو «معتمد» أو «certified» بأي لغة. الجملة الواحدة من هذا
  النوع تحوّل مخرجاً هندسياً للمراجعة إلى شهادةٍ يعتمد عليها من لا يعرف حدودها.

  الخصوصية · وصف الزائر وملفّاته تُرسَل إلى مزوّد خارجي يضبطه المشغّل. الصمت عن
  ذلك ليس حياداً: المستخدم يكتب ما يظنّه محلياً. وحدّ الخصوصية التقنيّ (حجب
  الحقول، وإطفاء الحفظ الخام) لا قيمة له إن لم يُذكر للمستخدم ما يُرسَل ولمن.

هذا الملفّ يمسح كل سطح يراه المستخدم بحثاً عن ادّعاء مطابقة، ويطبع **كل** موضع
سمح به مع سببه وملفّه وسطره — فالقائمة البيضاء معروضة لا مخبوءة. ثم يثبت أن حالة
المطابقة NOT_EVALUATED حيثما أُعلنت، وأن حدّ التليمتري قائم، وأن صفحة الخصوصية
موجودة وقائمة بذاتها.
"""
import ast
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_logging as L                                           # noqa: E402
import acs_understand as U                                        # noqa: E402
import acs_upload_security as UP                                  # noqa: E402

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
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8') as fh:
        return fh.read()


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, '/')


# ══════════════════════════════════ أ) ماسح المطابقة الزائفة (F-12) ═════════
print('\n── أ · ماسح المطابقة الزائفة ──')

# العبارات التي لا يجوز أن تُقال عن مخرج هذا النظام إثباتاً.
CLAIM_TOKENS = (
    'SBC compliant', 'code approved', 'NFPA compliant', 'code compliant',
    'fully compliant', 'certified',
    'مطابق للكود', 'معتمد نظامياً', 'آمن ومطابق',
)

# سياق النفي: العبارة مذكورة لتُنفى، أو لتُمنع، أو لتُعلَن غائبة. القائمة
# صريحة ومحدودة عمداً — كل توسيع لها يوسّع ما يمرّ، فيُكتب هنا ويُرى.
NEGATION_MARKERS = (
    'NOT_EVALUATED',            # الحالة المعلنة الوحيدة للمطابقة
    'not a compliance',         # «ليست بياناً بالمطابقة»
    'ليس مطابقة',
    'لا تعني المطابقة',
    'does not mean',            # «لا يعني … مطابقاً للكود»
    'deliberately absent',      # كلمة محذوفة عمداً من المفردات
    'forbidden',                # قائمة ألفاظ ممنوعة في المخرج
    'restricted_status',        # حالة لا يضعها النظام من تلقائه
    'declared restricted',
    'is not code compliant',
    'asserted absent',
)

WINDOW = 200            # نصف قطر سياق النفي بالحروف

surfaces = []
surfaces += sorted(glob.glob(os.path.join(ROOT, 'public', '*.html')))
# F-09 — قبل التفكيك كانت كل شيفرة الواجهة داخل public/index.html، فمسح الصفحة
# كان يمسح التطبيق كلّه. بعده صارت الصفحة قشرة: مسحُها وحدها يفقد كل موضع في
# الشيفرة صامتاً. تُضاف الوحدات وورقة الأنماط صراحةً، ويُثبَت أدناه أن العدّ
# بعد التفكيك ليس أقلّ ممّا كان قبله.
surfaces += sorted(glob.glob(os.path.join(ROOT, 'public', 'app', '**', '*.js'),
                             recursive=True))
surfaces += sorted(glob.glob(os.path.join(ROOT, 'public', 'app', '**', '*.css'),
                             recursive=True))
surfaces += sorted(glob.glob(os.path.join(ROOT, 'acs_*.json')))
surfaces += [os.path.join(ROOT, n) for n in
             ('acs_docs.py', 'acs_bim.py', 'acs_rules.py')]
surfaces += sorted(glob.glob(os.path.join(ROOT, '*.md')))
surfaces = [s for s in surfaces if os.path.isfile(s)]

_surface_rel = [rel(x) for x in surfaces]
chk('the scanner actually walks the user-facing surfaces (page, specs, reports)',
    len(surfaces) >= 20
    and 'public/index.html' in _surface_rel
    and rel(os.path.join(ROOT, 'acs_docs.py')) in _surface_rel,
    str(len(surfaces)))
chk('the scanner walks the shipped application modules too — the shell alone '
    'is no longer the application (F-09)',
    'public/app/main.js' in _surface_rel
    and 'public/app/trust/core.js' in _surface_rel
    and 'public/app/styles/app.css' in _surface_rel
    and len([s for s in _surface_rel if s.startswith('public/app/')]) >= 20,
    str(len([s for s in _surface_rel if s.startswith('public/app/')])))

whitelisted = []        # (file, line, token, marker)
violations = []         # (file, line, token, excerpt)

for path in surfaces:
    try:
        txt = rd(rel(path))
    except (OSError, UnicodeDecodeError):
        continue
    low = txt.lower()
    for token in CLAIM_TOKENS:
        for m in re.finditer(re.escape(token.lower()), low):
            line = txt.count('\n', 0, m.start()) + 1
            ctx = txt[max(0, m.start() - WINDOW):m.end() + WINDOW]
            # تطبيع خفيف: التوكيد في Markdown («does **not** mean») وتغليف JSON
            # لا يغيّران معنى النفي، فلا يجوز أن يخفياه عن الماسح.
            # (الشرطة السفلية تبقى: هي جزء من أسماء الحقول مثل restricted_status)
            ctx_low = re.sub(r'\s+', ' ',
                             re.sub(r'[*`>\\"]+', '', ctx)).lower()
            marker = next((mk for mk in NEGATION_MARKERS
                           if mk.lower() in ctx_low), None)
            if marker:
                whitelisted.append((rel(path), line, token, marker))
            else:
                violations.append((rel(path), line, token,
                                   re.sub(r'\s+', ' ',
                                          txt[max(0, m.start() - 70):
                                              m.end() + 70])))

chk('no user-facing surface asserts regulatory compliance outside an explicit '
    'negation or disclaimer context', violations == [],
    ' | '.join('%s:%d [%s] …%s…' % v for v in violations[:4]))

print('\n  القائمة البيضاء المعروضة — كل موضع سُمح به وسببه '
      '(%d موضعاً):' % len(whitelisted))
for fp, ln, tok, mk in whitelisted:
    print('    · %s:%d  «%s»  ⟵ negated by %r' % (fp, ln, tok, mk))
if not whitelisted:
    print('    · (لا شيء)')

chk('every whitelisted occurrence names its file, its line and the marker that '
    'justified it — the whitelist is visible, not hidden',
    all(isinstance(x[1], int) and x[1] > 0 and x[3] in NEGATION_MARKERS
        for x in whitelisted))
chk('the negation vocabulary is a short declared list, not an open door',
    len(NEGATION_MARKERS) <= 12)

# ── لا تُفقَد تغطية بالتفكيك: عدّ ما قبل F-09 هو الأرضية ──────────────────
# قبل التفكيك كانت الواجهة كلّها ملفّاً واحداً (public/index.html، 1,863,894
# بايت) وحمل هذه المواضع بالضبط. بعد التفكيك يجب أن يجد الماسح العدد نفسه أو
# أكثر عبر القشرة + الوحدات + ورقة الأنماط. أي نقص يعني أن مسحاً ضاع صامتاً.
FRONTEND_BASELINE = {'code compliant': 5, 'certified': 6, 'مطابق للكود': 1}
FRONTEND_PREFIXES = ('public/',)
_front = [x for x in (whitelisted + [(v[0], v[1], v[2], None)
                                     for v in violations])
          if x[0].startswith(FRONTEND_PREFIXES)]
_front_counts = {}
for _fp, _ln, _tok, _mk in _front:
    _front_counts[_tok] = _front_counts.get(_tok, 0) + 1
print('\n  عدّ المواضع في سطح الواجهة المشحون (قشرة + وحدات + أنماط):')
for _tok in sorted(set(list(FRONTEND_BASELINE) + list(_front_counts))):
    print('    · «%s»  now=%d  pre-split baseline=%d'
          % (_tok, _front_counts.get(_tok, 0), FRONTEND_BASELINE.get(_tok, 0)))
_lost = {t: (n, _front_counts.get(t, 0))
         for t, n in FRONTEND_BASELINE.items() if _front_counts.get(t, 0) < n}
chk('the split lost NO scanner coverage: every claim token the single-file page '
    'carried is still found in the shipped frontend surface',
    _lost == {}, str(_lost))
chk('the frontend occurrences now live in the modules, not in the shell — and '
    'they are still classified, not skipped',
    sum(_front_counts.values()) >= sum(FRONTEND_BASELINE.values())
    and all(x[0].startswith('public/app/') for x in _front),
    str(sorted(set(x[0] for x in _front))))
_front_viol = [v for v in violations if v[0].startswith(FRONTEND_PREFIXES)]
chk('no shipped frontend file asserts compliance outside a negation context',
    _front_viol == [], ' | '.join('%s:%d [%s]' % (v[0], v[1], v[2])
                                  for v in _front_viol[:4]))
chk('the app stylesheet was scanned too (a claim can be shipped as CSS content)',
    'public/app/styles/app.css' in _surface_rel)

# النفي وحده لا يكفي: نتأكّد أن الماسح يمسك ادّعاءً حقيقياً لو ظهر.
_probe = 'the produced model is fully compliant with the building code'
chk('the scanner is not vacuous — it flags a bare claim with no negation nearby',
    any(t.lower() in _probe.lower() for t in CLAIM_TOKENS)
    and not any(mk.lower() in _probe.lower() for mk in NEGATION_MARKERS))

# ═══════════════════════════ ب) حالة المطابقة المعلنة NOT_EVALUATED ════════
print('\n── ب · حالة المطابقة تبقى NOT_EVALUATED ──')

AUTH_SRC = rd('acs_authoring.py')
chk('acs_authoring.py emits compliance as NOT_EVALUATED',
    'NOT_EVALUATED' in AUTH_SRC
    and re.search(r'compliance\s*[:=]\s*"NOT_EVALUATED"', AUTH_SRC) is not None
    or re.search(r'"compliance"\s*:\s*"NOT_EVALUATED"', AUTH_SRC) is not None)
_bad_auth = re.findall(r'"compliance"\s*:\s*"(?!NOT_EVALUATED)([A-Z_]+)"', AUTH_SRC)
chk('no other compliance status is emitted anywhere in the authoring layer',
    _bad_auth == [], ', '.join(_bad_auth))

AUTH_JSON = json.loads(rd('acs_authoring.json'))
chk('acs_authoring.json declares compliance_status NOT_EVALUATED',
    AUTH_JSON.get('compliance_status') == 'NOT_EVALUATED',
    str(AUTH_JSON.get('compliance_status')))
chk('and says plainly that a valid transaction is not a compliance statement',
    'compliance' in json.dumps(AUTH_JSON, ensure_ascii=False).lower()
    and 'NOT_EVALUATED' in json.dumps(AUTH_JSON, ensure_ascii=False))

API_SRC = rd('acs_understand_api.py')
API_TREE = ast.parse(API_SRC)
_payload = [n for n in ast.walk(API_TREE)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == '_understand_payload']
chk('_understand_payload exists exactly once in the API layer', len(_payload) == 1)

_compliance_block = None
if _payload:
    for node in ast.walk(_payload[0]):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == 'compliance':
                _compliance_block = v
chk('the understand payload carries a compliance block',
    isinstance(_compliance_block, ast.Dict))

_status = None
_note = None
if isinstance(_compliance_block, ast.Dict):
    for k, v in zip(_compliance_block.keys, _compliance_block.values):
        if isinstance(k, ast.Constant) and k.value == 'status' \
                and isinstance(v, ast.Constant):
            _status = v.value
        if isinstance(k, ast.Constant) and k.value == 'note' \
                and isinstance(v, ast.Constant):
            _note = v.value
chk('every /v1/understand response reports compliance.status = NOT_EVALUATED',
    _status == 'NOT_EVALUATED', str(_status))
chk('and says in the response itself that this is not a code-compliance check',
    isinstance(_note, str) and 'مطابقة' in _note and len(_note) > 20,
    str(_note)[:120])
_status_literals = set(re.findall(r'"status"\s*:\s*"([A-Z_]+)"', API_SRC))
chk('no competing compliance verdict is hard-coded anywhere in the API layer',
    _status_literals <= {'NOT_EVALUATED'}, ', '.join(sorted(_status_literals)))

# ═════════════════════════ ج) حدّ الخصوصية في التليمتري والسجلّ ═════════════
print('\n── ج · حدّ الخصوصية في السجلّ والتليمتري ──')

_must_block = ('text', 'description', 'prompt', 'building', 'api_key',
               'authorization')
_uncovered = [x for x in _must_block if x not in L.FORBIDDEN_FIELDS]
chk('FORBIDDEN_FIELDS covers text, description, prompt, building, api_key and '
    'authorization', _uncovered == [], ', '.join(_uncovered))
chk('it also covers the raw reply and the cookie header',
    all(x in L.FORBIDDEN_FIELDS for x in ('cookie', 'raw', 'completion',
                                          'response_text')))
chk('the generation telemetry channel declares a closed field list',
    'allowed = (' in rd('acs_logging.py'))

for _k in ('ACS_RAW_DUMP_ENABLED', 'ACS_RAW_DUMP_DIR', 'ACS_RAW_DUMP_KEEP'):
    os.environ.pop(_k, None)
chk('ACS_RAW_DUMP_ENABLED defaults to OFF when unset',
    U.raw_dump_enabled() is False)
os.environ['ACS_RAW_DUMP_ENABLED'] = ''
chk('an EMPTY value still means OFF — and does not crash the boot path',
    U.raw_dump_enabled() is False)
os.environ['ACS_RAW_DUMP_ENABLED'] = 'nonsense'
chk('an unparsable value means OFF, never ON by accident',
    U.raw_dump_enabled() is False)
os.environ['ACS_RAW_DUMP_ENABLED'] = '1'
chk('it turns on only when the operator sets it explicitly',
    U.raw_dump_enabled() is True)
os.environ.pop('ACS_RAW_DUMP_ENABLED', None)
_st = U.raw_dump_status()
chk('the raw-dump status is off, restricted, rotated and never exposes a path',
    _st['enabled'] is False and _st['file_mode'] == '0o600'
    and _st['dir_mode'] == '0o700' and _st['keep'] >= 1
    and _st['path_exposed_to_client'] is False
    and 'path' not in json.dumps(_st).replace('path_exposed_to_client', ''),
    json.dumps(_st))
chk('the raw dump keeps a bounded number of files, declared in the environment',
    'ACS_RAW_DUMP_KEEP' in rd('acs_understand.py')
    and 'ACS_RAW_DUMP_KEEP' in rd('.env.example'))
chk('the new privacy switches are declared in .env.example with empty-safe '
    'defaults',
    all(('%s=' % k) in rd('.env.example') for k in
        ('ACS_RAW_DUMP_ENABLED', 'ACS_RAW_DUMP_DIR', 'ACS_RAW_DUMP_KEEP',
         'ACS_PRICE_INPUT_PER_MTOK', 'ACS_PRICE_OUTPUT_PER_MTOK')))
chk('the raw dump path is never returned to the client — the API layer never '
    'mentions it', 'ACS_RAW_DUMP' not in API_SRC and '_save_raw' not in API_SRC)

# التشغيل الفعلي: مطفأً لا يكتب شيئاً، ومُفعَّلاً يكتب مقصوراً ومحدوداً ومعقَّماً.
import stat as _stat                                              # noqa: E402
import tempfile as _tempfile                                      # noqa: E402

_probe_root = _tempfile.mkdtemp(prefix='acs_rawdump_probe_')
_probe_dir = os.path.join(_probe_root, 'dumps')
_saved_env = {k: os.environ.get(k) for k in
              ('ACS_RAW_DUMP_ENABLED', 'ACS_RAW_DUMP_DIR', 'ACS_RAW_DUMP_KEEP')}
os.environ['ACS_RAW_DUMP_DIR'] = _probe_dir
os.environ['ACS_RAW_DUMP_KEEP'] = '2'
os.environ.pop('ACS_RAW_DUMP_ENABLED', None)

_off = U._save_raw('a raw model reply about the visitor description')
chk('with the switch off nothing is written at all — no file, no directory',
    _off is None and not os.path.isdir(_probe_dir))

os.environ['ACS_RAW_DUMP_ENABLED'] = '1'

_TEST_KEY_PREFIX = 'sk-' + 'ant-'

for _i in range(4):
    _test_key = _TEST_KEY_PREFIX + 'abc123DEF456ghi789jkl'
    U._save_raw('reply %d key=%s' % (_i, _test_key))


_files = sorted(os.listdir(_probe_dir)) if os.path.isdir(_probe_dir) else []
chk('with the switch on, at most ACS_RAW_DUMP_KEEP files survive rotation',
    len(_files) == 2, str(len(_files)))
chk('the dump directory is restricted to the owner (0700)',
    os.path.isdir(_probe_dir)
    and _stat.S_IMODE(os.stat(_probe_dir).st_mode) == 0o700,
    oct(_stat.S_IMODE(os.stat(_probe_dir).st_mode)) if os.path.isdir(_probe_dir)
    else 'missing')
chk('every dump file is created 0600 — os.open with an explicit mode, not open()',
    _files != [] and all(
        _stat.S_IMODE(os.stat(os.path.join(_probe_dir, n)).st_mode) == 0o600
        for n in _files),
    ', '.join('%s=%s' % (n, oct(_stat.S_IMODE(
        os.stat(os.path.join(_probe_dir, n)).st_mode))) for n in _files))
_dumped = ''.join(open(os.path.join(_probe_dir, n), encoding='utf-8').read()
                  for n in _files)
chk('the existing E.redact() filtering still applies to what is written',
    _TEST_KEY_PREFIX not in _dumped and '[REDACTED]' in _dumped, _dumped[:120])
chk('os.open with an explicit 0o600 mode is the write path in the source',
    'os.open(' in rd('acs_understand.py') and '0o600' in rd('acs_understand.py'))

for _k, _v in _saved_env.items():
    if _v is None:
        os.environ.pop(_k, None)
    else:
        os.environ[_k] = _v
try:
    for _n in os.listdir(_probe_dir):
        os.remove(os.path.join(_probe_dir, _n))
    os.rmdir(_probe_dir)
    os.rmdir(_probe_root)
except OSError:
    pass

# ═══════════════════════════ د) الرفع لا يحتفظ ببايتات المستخدم ═════════════
print('\n── د · الرفع لا يكتب بايتات المستخدم على القرص ──')

_uh = UP.health_status()
chk('acs_upload_security reports writes_temp_files = False',
    _uh.get('writes_temp_files') is False, str(_uh.get('writes_temp_files')))
chk('and reports that no filename is ever used as a path',
    _uh.get('uses_filename_as_path') is False)
UPLOAD_SRC = rd('acs_upload_security.py')
UPLOAD_TREE = ast.parse(UPLOAD_SRC)
_writers = []
for _n in ast.walk(UPLOAD_TREE):
    if isinstance(_n, ast.Call):
        _fn = _n.func
        _nm = (_fn.attr if isinstance(_fn, ast.Attribute)
               else (_fn.id if isinstance(_fn, ast.Name) else ''))
        if _nm in ('mkstemp', 'NamedTemporaryFile', 'mkdtemp', 'TemporaryFile'):
            _writers.append('%s:%d' % ('acs_upload_security.py', _n.lineno))
        if _nm == 'open' and any(
                isinstance(a, ast.Constant) and isinstance(a.value, str)
                and 'w' in a.value for a in _n.args[1:]):
            _writers.append('%s:%d' % ('acs_upload_security.py', _n.lineno))
_imports = [a.name for _n in ast.walk(UPLOAD_TREE)
            if isinstance(_n, ast.Import) for a in _n.names]
chk('the module creates no temporary file — proven on the syntax tree, not by '
    'grepping (the word survives only in the comment explaining the fix)',
    _writers == [] and 'tempfile' not in _imports, ', '.join(_writers))
chk('and its own source says the defect was writing the upload to mkstemp',
    'mkstemp' in UPLOAD_SRC and 'tempfile' not in _imports)

# ═══════════════════════════════ هـ) صفحة الخصوصية ═════════════════════════
print('\n── هـ · صفحة الخصوصية والاستخدام ──')

PRIV_REL = 'public/privacy.html'
PRIV_PATH = os.path.join(ROOT, PRIV_REL)
chk('public/privacy.html exists', os.path.isfile(PRIV_PATH))

PRIV = rd(PRIV_REL) if os.path.isfile(PRIV_PATH) else ''


class _Doc(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.tags = []
        self.attrs = {}
        self.metas = []
        self.title = ''
        self._in_title = False
        self.handlers = []
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.tags.append(tag)
        if tag in ('html', 'body', 'head') and tag not in self.attrs:
            self.attrs[tag] = d
        if tag == 'meta':
            self.metas.append(d)
        if tag == 'title':
            self._in_title = True
        for k, v in attrs:
            if k.lower().startswith('on'):
                self.handlers.append((tag, k))
            if k.lower() in ('src', 'href') and v:
                self.srcs.append(v)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


doc = _Doc()
_parse_error = None
try:
    doc.feed(PRIV)
    doc.close()
except Exception as exc:                                          # noqa: BLE001
    _parse_error = '%s: %s' % (type(exc).__name__, exc)

chk('it parses as HTML without error', _parse_error is None, str(_parse_error))
chk('the document declares <html lang="ar" dir="rtl">',
    doc.attrs.get('html', {}).get('lang') == 'ar'
    and doc.attrs.get('html', {}).get('dir') == 'rtl',
    str(doc.attrs.get('html')))
chk('it has a non-empty <title>', len(doc.title.strip()) > 5, doc.title[:60])
_desc = [m for m in doc.metas if (m.get('name') or '').lower() == 'description']
chk('it has a <meta name="description"> with real content',
    len(_desc) == 1 and len((_desc[0].get('content') or '').strip()) > 40)
_robots = [m for m in doc.metas if (m.get('name') or '').lower() == 'robots']
chk('it declares <meta name="robots" content="index,follow">',
    len(_robots) == 1
    and (_robots[0].get('content') or '').replace(' ', '') == 'index,follow',
    str(_robots))

chk('it references no http:// resource', 'http://' not in PRIV)
_ext = [u for u in doc.srcs if u.startswith('http://') or u.startswith('//')
        or u.startswith('https://')]
chk('it references no external https:// resource', _ext == [] and
    'https://' not in PRIV, ', '.join(_ext[:3]))
chk('CSP · it carries no inline event handler attribute', doc.handlers == [],
    str(doc.handlers[:3]))
chk('CSP · it loads no script at all, inline or external',
    'script' not in doc.tags and '<script' not in PRIV.lower())
chk('CSP · it needs no eval', 'eval(' not in PRIV)
chk('CSP · its styling is an inline <style>, which the site policy allows',
    'style' in doc.tags and 'stylesheet' not in PRIV)

_bilingual = ('lang="en"' in PRIV and 'dir="ltr"' in PRIV)
chk('the page is bilingual — Arabic primary, English secondary', _bilingual)

_say = {
    'what is transmitted to the provider':
        ('مزوّد' in PRIV and 'وصف' in PRIV and 'sent to the AI provider' in PRIV),
    'that uploaded images and PDF go to the provider too':
        ('PDF' in PRIV and ('صور' in PRIV or 'المخططات' in PRIV)),
    'that the user must not upload secrets':
        ('لا ترفع أسراراً' in PRIV or 'أسرار' in PRIV)
        and 'Do not upload secrets' in PRIV,
    'that project data lives in the browser':
        'متصفّح' in PRIV and 'browser storage' in PRIV,
    'that the server does not persist project models':
        'الخادم لا يحتفظ' in PRIV
        and 'does not persist project models' in PRIV,
    'what is NOT stored':
        'ما لا يُخزَّن' in PRIV and 'What is NOT stored' in PRIV,
    'that the provider is configured by the operator':
        'يضبطه مشغّل' in PRIV or 'configured by' in PRIV,
    'that retention depends on the operator contract, with no claim of our own':
        'no retention or auto-deletion claim' in PRIV
        and 'عقد المشغّل' in PRIV,
}
for _label, _ok in _say.items():
    chk('the page states %s' % _label, bool(_ok))

_forbidden_promises = ('نحذف بياناتك فوراً', 'deleted immediately',
                       'never leaves your device', 'we never send',
                       'zero data retention', 'guaranteed deletion')
_found_promise = [x for x in _forbidden_promises if x.lower() in PRIV.lower()]
chk('the page makes no unsupported retention or deletion promise',
    _found_promise == [], ', '.join(_found_promise))
chk('the page states the compliance limit as well — output is NOT_EVALUATED',
    'NOT_EVALUATED' in PRIV)

print('\n' + '─' * 62)
print('PRIVACY BOUNDARY: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
