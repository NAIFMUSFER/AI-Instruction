# -*- coding: utf-8 -*-
"""F-09 — تقرير الحزمة بعد التفكيك: رقم مقيس، حتميّ، ولا يدّعي أكثر ممّا جرى.

    python3 tests/remediation/test_bundle_report.py

خمسة أشياء تُثبَت هنا، وواحد يُمنَع:

  أ) التقرير موجود ويُعاد إنتاجه حتميّاً: يُشغَّل tools/bundle_report.py مرّتين
     ويُقارَن المخرَجان بايتاً ببايت. تقرير غير حتميّ لا يصلح خطَّ أساسٍ يُقاس
     عليه تحسّن لاحق.

  ب) كل رقم فيه يطابق قياساً مستقلّاً — مستقلّاً فعلاً: هذا الملفّ لا يستورد
     tools/bundle_report.py ولا tools/app_source.py ولا يستدعي أيّاً من دوالّهما،
     بل يمشي شجرة public/app/ بنفسه ويقيس على البايتات الخام (bytes) لا على
     النصّ (str)، بمسحٍ مكتوب هنا من الصفر. لو كان يستدعي الأداة لكان يقارن
     الأداة بنفسها، وهو لا شيء.

  ج) الميزانية مُحقَّقة فعلاً لا مُعلَنة فقط: القشرة دون السقف، وأكبر وحدة دون
     عتبة التحذير، والقيمتان محسوبتان من القياس المستقلّ لا منقولتين.

  د) المنع — وهو جوهر هذا الملفّ بعد أن صار التفكيك واقعاً: لا يجوز أن يدّعي
     التقرير تفكيكاً لم يحدث. لا يكفي عدّ الملفّات: تقسيمٌ يضع معظم الشيفرة في
     ملفّ واحد ويشتّت الباقي يعطي عدداً كبيراً وهو ليس تقسيماً. فيُفحَص شيئان:

        • عدد وحدات الطرف الأوّل ≥ 15   (الواقع اليوم: 24 وحدة)
        • لا وحدة واحدة تحمل أكثر من 20٪ من مجموع شيفنة الطرف الأوّل
          (الواقع اليوم: أكبر وحدة core/standards.js بنسبة 12.59٪ من
           1,814,026 بايت — أي هامش يقارب 7.4 نقطة مئوية تحت العتبة)

     العتبتان مضبوطتان لتمرّا اليوم بهامش واضح، وتسقطا فور أن يعود ملفّ واحد
     ليبتلع الشيفرة تحت اسم «وحدة».

  هـ) الحارس ليس عقيماً: تُمرَّر عليه تقارير مغلوطة عمداً ويجب أن يمسكها.
"""
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PAGE = os.path.join(ROOT, "public", "index.html")
APP = os.path.join(ROOT, "public", "app")
CSS = os.path.join(APP, "styles", "app.css")
TOOL = os.path.join(ROOT, "tools", "bundle_report.py")
REPORT = os.path.join(ROOT, "tests", "performance", "bundle_report.json")

# ── العتبات المضادّة للتلاعب — أرقام معلنة، والواقع اليوم مكتوب بجانب كلٍّ منها
MIN_FIRST_PARTY_MODULES = 15        # الواقع: 24
MAX_SINGLE_MODULE_SHARE_PCT = 20.0  # الواقع: 12.59٪ (core/standards.js)
MODULE_WARN_BYTES = 300 * 1024      # 307200 — الواقع: أكبر وحدة 228,371 B
SHELL_BUDGET_BYTES = 200 * 1024     # 204800 — الواقع: القشرة 44,253 B

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


# ══════════════════════════════════════ قياس مستقلّ، مكتوب هنا من الصفر ══════
# يعمل على البايتات لا على النصّ، ولا يشترك في سطر واحد مع الأداة ولا مع
# tools/app_source.py — شجرة public/app/ تُمشى هنا مشياً مستقلّاً.
RAW = open(PAGE, 'rb').read()


def _elements(raw, open_tag, close_tag):
    """مسح تسلسلي على البايتات: يقفز من نهاية كل عنصر، فلا يرى ما بداخله."""
    out, i = [], 0
    while True:
        a = raw.find(open_tag, i)
        if a < 0:
            break
        ge = raw.find(b'>', a)
        e = raw.find(close_tag, ge)
        if e < 0:
            break
        out.append({"open": a, "body_start": ge + 1, "body_end": e,
                    "attrs": raw[a + len(open_tag):ge].strip(),
                    "body_bytes": e - (ge + 1),
                    "element_bytes": (e + len(close_tag)) - a})
        i = e + len(close_tag)
    return out


IND_SCRIPTS = _elements(RAW, b'<script', b'</script>')
IND_STYLES = _elements(RAW, b'<style', b'</style>')
for s in IND_SCRIPTS:
    s["kind"] = ("module" if b'type="module"' in s["attrs"]
                 else "importmap" if b'type="importmap"' in s["attrs"]
                 else "classic")
    s["external"] = b'src=' in s["attrs"]

# ── شجرة الوحدات: مشيٌ مستقلّ، والأحجام من os.path.getsize (شاهد ثالث) ──────
IND_MODULES = {}
for _base, _dirs, _names in os.walk(APP):
    for _n in sorted(_names):
        if not _n.endswith('.js'):
            continue
        _p = os.path.join(_base, _n)
        IND_MODULES[os.path.relpath(_p, APP).replace(os.sep, '/')] = \
            os.path.getsize(_p)
IND_TOTAL_JS = sum(IND_MODULES.values())
IND_BOOT = {k: v for k, v in IND_MODULES.items() if k.startswith('boot/')}

# ── الإغلاق الساكن من main.js: تحليل سطريّ (طريقة أخرى غير regex الأداة) ────
def _static_targets(rel):
    src = io.open(os.path.join(APP, rel), encoding='utf-8').read()
    out = []
    for line in src.split('\n'):
        line = line.strip()
        if not line.startswith('import ') or not line.endswith(';'):
            continue
        # آخر سلسلة بين علامتَي اقتباس مفردتين/مزدوجتين في الجملة هي المُحدِّد
        for quote in ("'", '"'):
            a = line.find(quote)
            if a < 0:
                continue
            bq = line.find(quote, a + 1)
            if bq < 0:
                continue
            spec = line[a + 1:bq]
            if spec.startswith('.'):
                out.append(os.path.normpath(
                    os.path.join(os.path.dirname(rel), spec)).replace(os.sep, '/'))
            break
    return out


IND_EAGER, _stack = set(), ['main.js']
while _stack:
    _cur = _stack.pop()
    if _cur in IND_EAGER or _cur not in IND_MODULES:
        continue
    IND_EAGER.add(_cur)
    _stack.extend(_static_targets(_cur))
IND_CORE_BYTES = sum(IND_MODULES[k] for k in IND_EAGER)
IND_LAZY = sorted(k for k in IND_MODULES
                  if k not in IND_EAGER and not k.startswith('boot/'))

IND_LARGEST = max(IND_MODULES, key=lambda k: (IND_MODULES[k], k))
IND_LARGEST_PCT = 100.0 * IND_MODULES[IND_LARGEST] / IND_TOTAL_JS


def ind_gzip(raw):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=9, mtime=0) as g:
        g.write(raw)
    return len(buf.getvalue())


# ═══════════════════════════════════════════════════ أ · الوجود والحتمية ════
print('\n== أ · THE REPORT EXISTS AND IS REGENERATED DETERMINISTICALLY ==')
TOOLSRC = io.open(TOOL, encoding='utf-8').read()
chk('tools/bundle_report.py exists', os.path.isfile(TOOL))
chk('the tool still declares itself measurement-only',
    'قياس فقط' in TOOLSRC or 'measurement only' in TOOLSRC.lower()
    or 'MEASUREMENT ONLY' in TOOLSRC)


def run_tool(args=()):
    return subprocess.run([sys.executable, TOOL] + list(args), cwd=ROOT,
                          capture_output=True, text=True)


r1 = run_tool(['--stdout'])
r2 = run_tool(['--stdout'])
chk('the tool runs cleanly (twice)', r1.returncode == 0 and r2.returncode == 0,
    (r1.stderr or r2.stderr)[:300])
chk('two consecutive runs produce byte-identical output — the report is a '
    'usable baseline, not a moving target',
    r1.stdout == r2.stdout,
    'first %d bytes vs second %d bytes' % (len(r1.stdout), len(r2.stdout)))
chk('the output carries no timestamp field (the usual source of false diffs)',
    not re.search(r'"(generated_at|timestamp|date|now)[^"]*"\s*:', r1.stdout),
    (re.search(r'"[^"]*(generated_at|timestamp)[^"]*"', r1.stdout) or ['-'])[0])
chk('the output embeds no absolute sandbox path',
    '/tmp/' not in r1.stdout and ROOT not in r1.stdout)

w = run_tool()
chk('the tool writes tests/performance/bundle_report.json',
    w.returncode == 0 and os.path.isfile(REPORT), w.stderr[:300])
R = json.loads(io.open(REPORT, encoding='utf-8').read())
chk('the written file equals what the tool prints',
    io.open(REPORT, encoding='utf-8').read() == r1.stdout)
chk('the report declares itself deterministic', R.get('deterministic') is True)
chk('the report announces the post-split schema (acs.bundle/2)',
    R.get('report') == 'acs.bundle/2', str(R.get('report')))

# ═════════════════════════════ ب · مطابقة قياس مستقلّ للشجرة نفسها ══════════
print('\n== ب · EVERY NUMBER MATCHES A FRESH INDEPENDENT MEASUREMENT ==')
chk('this test imports neither the tool it checks nor the shared app_source '
    'helper (otherwise it would be comparing them with themselves)',
    'bundle_report' not in sys.modules and 'app_source' not in sys.modules)

S = R['shell']
chk('shell raw bytes match', S['raw_bytes'] == len(RAW),
    '%s vs %s' % (S['raw_bytes'], len(RAW)))
chk('shell raw bytes match os.path.getsize as a third witness',
    S['raw_bytes'] == os.path.getsize(PAGE))
chk('shell sha256 matches', S['sha256'] == hashlib.sha256(RAW).hexdigest())
chk('shell line count matches', S['lines'] == RAW.count(b'\n') + 1)
chk('shell gzip size matches an independently computed gzip',
    S['gzip_bytes'] == ind_gzip(RAW),
    '%s vs %s' % (S['gzip_bytes'], ind_gzip(RAW)))
chk('gzip is a real reduction, so it was really computed (not copied from raw)',
    0 < S['gzip_bytes'] < S['raw_bytes'])
chk('script element count matches (%d)' % len(IND_SCRIPTS),
    S['script_element_count'] == len(IND_SCRIPTS),
    '%s vs %s' % (S['script_element_count'], len(IND_SCRIPTS)))
chk('external script count matches (%d)'
    % len([s for s in IND_SCRIPTS if s['external']]),
    S['external_script_count'] == len([s for s in IND_SCRIPTS if s['external']]))

print('\n  -- the CSP-relevant zeroes, measured not asserted --')
chk('ZERO executable inline scripts in the shell — this is what lets '
    "script-src drop 'unsafe-inline'",
    S['inline_executable_script_count'] == 0
    == len([s for s in IND_SCRIPTS
            if not s['external'] and s['kind'] != 'importmap']))
chk('ZERO <style> blocks in the shell (independently counted)',
    S['style_element_count'] == 0 == len(IND_STYLES))
chk('ZERO style="…" attributes in the shell (independently counted)',
    S['inline_style_attribute_count'] == 0
    == len(re.findall(rb'\sstyle\s*=\s*"', RAW)))
chk('exactly one inline element remains and it is the import map',
    len([s for s in IND_SCRIPTS
         if not s['external'] and s['kind'] == 'importmap']) == 1
    and S['inline_importmap_bytes'] > 0)

print('\n  -- the module tree --')
J = R['javascript']
chk('first-party module count matches an independent walk (%d)'
    % len(IND_MODULES),
    J['first_party_module_count'] == len(IND_MODULES),
    '%s vs %s' % (J['first_party_module_count'], len(IND_MODULES)))
chk('total first-party JS bytes match (%d)' % IND_TOTAL_JS,
    J['first_party_total_bytes'] == IND_TOTAL_JS,
    '%s vs %s' % (J['first_party_total_bytes'], IND_TOTAL_JS))
chk('the per-module list covers every module on disk, once each',
    sorted(m['path'] for m in J['modules'])
    == sorted('public/app/' + k for k in IND_MODULES))
chk('the per-module byte counts sum to the declared total',
    sum(m['bytes'] for m in J['modules']) == J['first_party_total_bytes']
    == IND_TOTAL_JS)
chk('the per-module list is sorted largest first',
    [m['bytes'] for m in J['modules']]
    == sorted((m['bytes'] for m in J['modules']), reverse=True))
for m in J['modules'][:5]:
    rel = m['path'][len('public/app/'):]
    chk('module %-34s %7d bytes matches getsize' % (rel, m['bytes']),
        IND_MODULES.get(rel) == m['bytes'],
        'independent=%s' % IND_MODULES.get(rel))
chk('the largest module is the one an independent measurement finds (%s)'
    % IND_LARGEST,
    J['largest_module']['path'] == 'public/app/' + IND_LARGEST
    and J['largest_module']['bytes'] == IND_MODULES[IND_LARGEST],
    str(J['largest_module']))

chk('core initial JS matches the independently computed static closure '
    '(%d bytes in %d modules)' % (IND_CORE_BYTES, len(IND_EAGER)),
    J['core_initial_bytes'] == IND_CORE_BYTES
    and J['core_initial_module_count'] == len(IND_EAGER),
    '%s/%s vs %s/%s' % (J['core_initial_bytes'], J['core_initial_module_count'],
                        IND_CORE_BYTES, len(IND_EAGER)))
chk('boot scripts are counted separately and match (%d bytes in %d files)'
    % (sum(IND_BOOT.values()), len(IND_BOOT)),
    J['boot_bytes'] == sum(IND_BOOT.values())
    and J['boot_script_count'] == len(IND_BOOT))
chk('core + boot equals the declared first-load JavaScript',
    J['initial_javascript_bytes'] == J['core_initial_bytes'] + J['boot_bytes'])

print('\n  -- lazy JS: reported honestly, not invented --')
chk('lazy first-party JS is reported as the real number (%d bytes, %d modules)'
    % (sum(IND_MODULES[k] for k in IND_LAZY), len(IND_LAZY)),
    J['lazy_bytes'] == sum(IND_MODULES[k] for k in IND_LAZY)
    and J['lazy_module_count'] == len(IND_LAZY),
    '%s/%s vs %s/%s' % (J['lazy_bytes'], J['lazy_module_count'],
                        sum(IND_MODULES[k] for k in IND_LAZY), len(IND_LAZY)))
chk('there is no lazy first-party JS today and the report SAYS SO instead of '
    'implying code-splitting that was never done',
    J['lazy_bytes'] == 0 and J['lazy_module_count'] == 0
    and 'NOT IMPLEMENTED' in J['lazy_note'],
    J['lazy_note'][:120])
chk('every dynamic import() found is accounted for, and none of them is '
    'first-party (so none of them defers first-party bytes)',
    J['dynamic_import_count'] == len(J['dynamic_imports'])
    and J['first_party_dynamic_import_count']
    == len([d for d in J['dynamic_imports'] if d['first_party']]) == 0,
    str(J['first_party_dynamic_import_count']))

print('\n  -- stylesheet and generated markers --')
C = R['css']
chk('the stylesheet byte count matches getsize (%d)' % os.path.getsize(CSS),
    C['raw_bytes'] == os.path.getsize(CSS),
    '%s vs %s' % (C['raw_bytes'], os.path.getsize(CSS)))
chk('the stylesheet gzip size matches an independent gzip',
    C['gzip_bytes'] == ind_gzip(open(CSS, 'rb').read()))
G = R['generated_blocks']
chk('all 10 generated JS marker pairs survived the split into public/app/',
    G['js_pairs_in_modules'] == G['expected']['js_pairs_in_modules'] == 10,
    str(G['js_pairs_in_modules']))
chk('all 6 generated CSS pairs are in the extracted stylesheet',
    G['css_pairs_in_stylesheet'] == G['expected']['css_pairs_in_stylesheet']
    == 6, str(G['css_pairs_in_stylesheet']))
# العدّ المستقلّ يشترط علامة النهاية ` ===== -->` كاملةً: بدونها يلتقط النمط
# أي تعليق يبدأ بـ«ACS» فيُبالغ العدّ ويصير الشاهد المستقلّ أسوأ من الأداة.
IND_DOM_PAIRS = len(re.findall(
    rb'<!-- ===== ACS (?!END)[A-Z0-9][A-Z0-9 .]*?(?: \([^)]*\))? ===== -->',
    RAW))
chk('all 6 generated DOM pairs stayed in the shell (independently counted)',
    G['dom_pairs_in_shell'] == G['expected']['dom_pairs_in_shell'] == 6
    == IND_DOM_PAIRS,
    '%s vs independent %s' % (G['dom_pairs_in_shell'], IND_DOM_PAIRS))

print('\n  -- brotli and vendored assets: null-with-reason, never estimated --')
brv, brr = S['brotli_bytes'], S['brotli_reason']
try:
    import brotli as _br                                          # noqa: F401
    _has_brotli = True
except Exception:                                                 # noqa: BLE001
    _has_brotli = False
chk('brotli is reported as a number if and only if a brotli module is '
    'importable; otherwise null WITH a reason',
    (isinstance(brv, int) and brr is None) if _has_brotli
    else (brv is None and isinstance(brr, str) and len(brr) > 20),
    'importable=%s value=%r reason=%r' % (_has_brotli, brv, brr))
chk('no estimated or rounded brotli number is smuggled in as a string',
    brv is None or isinstance(brv, int))
V = R['vendor']
_vendor_dir = os.path.join(ROOT, 'public', 'vendor')
_vendor_files = ([] if not os.path.isdir(_vendor_dir)
                 else [n for _b, _d, ns in os.walk(_vendor_dir) for n in ns])
chk('vendored asset sizes are reported as null with a reason while '
    'public/vendor is unpopulated',
    (V.get('total_bytes') is None and isinstance(V.get('reason'), str)
     and len(V['reason']) > 20) if not _vendor_files
    else (V.get('total_bytes') == sum(
        os.path.getsize(os.path.join(_b, n))
        for _b, _d, ns in os.walk(_vendor_dir) for n in ns)),
    'files present=%d value=%r' % (len(_vendor_files), V.get('total_bytes')))
chk('the vendor reason names the real cause and does not claim a measurement',
    bool(_vendor_files)
    or ('EMPTY' in V['reason'] or 'does not exist' in V['reason']))
chk('the vendor reason no longer counts es-module-shims among the vendored '
    'assets — F-11 removed it from the page and from the build',
    bool(_vendor_files)
    or 'no longer vendored' in V['reason'], V.get('reason', '')[:120])

# ═══════════════════════════════════════ ج · الميزانية مُحقَّقة لا مُعلَنة ═══
print('\n== ج · THE BUDGET IS DECLARED *AND* MET, BOTH COMPUTED ==')
B = R['budget']
chk('the shell budget is the declared 200 KB (204800)',
    B['index_shell_budget_bytes'] == SHELL_BUDGET_BYTES == 204800,
    str(B['index_shell_budget_bytes']))
chk('a stricter preferred target of 150 KB (153600) is declared too',
    B['index_shell_preferred_bytes'] == 153600
    < B['index_shell_budget_bytes'], str(B['index_shell_preferred_bytes']))
chk('the shell is UNDER budget, measured independently (%d ≤ %d)'
    % (len(RAW), SHELL_BUDGET_BYTES),
    len(RAW) <= SHELL_BUDGET_BYTES and B['current_index_bytes'] == len(RAW))
chk('budget_met is TRUE and agrees with the independent measurement',
    B['budget_met'] is (len(RAW) <= SHELL_BUDGET_BYTES) is True,
    str(B['budget_met']))
chk('the stricter preferred target is met too, and is reported separately',
    B['preferred_met'] is (len(RAW) <= 153600) is True, str(B['preferred_met']))
chk('the stated headroom is arithmetically correct',
    B['headroom_bytes'] == B['index_shell_budget_bytes']
    - B['current_index_bytes'] > 0, str(B['headroom_bytes']))
chk('the shell is at least 8× smaller than the pre-split page (1,863,894 B) — '
    'the split moved real bytes, not labels',
    len(RAW) * 8 < 1863894, str(len(RAW)))
chk('the largest module is UNDER the 300 KB warning threshold (%d ≤ %d), '
    'measured independently' % (IND_MODULES[IND_LARGEST], MODULE_WARN_BYTES),
    IND_MODULES[IND_LARGEST] <= MODULE_WARN_BYTES
    and B['largest_module_bytes'] == IND_MODULES[IND_LARGEST],
    '%s vs %s' % (B['largest_module_bytes'], IND_MODULES[IND_LARGEST]))
chk('module_size_warnings is an array and is EMPTY today',
    isinstance(R['module_size_warnings'], list)
    and R['module_size_warnings'] == [], str(R['module_size_warnings'])[:120])
chk('the warning threshold is the declared 300 KB (307200)',
    R['module_size_warning_threshold_bytes'] == MODULE_WARN_BYTES == 307200)
chk('the warnings array agrees with an independent scan of the tree',
    [m for m in J['modules'] if m['bytes'] > MODULE_WARN_BYTES] == []
    == [k for k in IND_MODULES if IND_MODULES[k] > MODULE_WARN_BYTES])

# ══════════════════ د · لا ادّعاء بتفكيك لم يحدث (المضادّ للتلاعب) ═════════
print('\n== د · THE REPORT DOES NOT CLAIM A MODULARISATION THAT DID NOT HAPPEN ==')
chk('reality check: public/app/ exists and holds JavaScript modules',
    os.path.isdir(APP) and len(IND_MODULES) > 0)
chk('reality check: the shell really does load an external application module',
    bool(re.search(rb'<script[^>]+type="module"[^>]+src\s*=\s*"/app/main\.js"',
                   RAW)))
chk('reality check: no inline module of application code is left in the shell',
    max([s['body_bytes'] for s in IND_SCRIPTS
         if not s['external']] or [0]) < 4096,
    str(max([s['body_bytes'] for s in IND_SCRIPTS if not s['external']] or [0])))
chk('reality check: every <script src> and the stylesheet resolve to a real '
    'file on disk',
    all(os.path.isfile(os.path.join(ROOT, 'public',
                                    s['attrs'].split(b'src="')[1]
                                    .split(b'"')[0].decode().lstrip('/')))
        for s in IND_SCRIPTS if s['external']))

print('\n  -- the anti-gaming assertion: a file count is not a split --')
chk('there are at least %d first-party modules (today: %d)'
    % (MIN_FIRST_PARTY_MODULES, len(IND_MODULES)),
    len(IND_MODULES) >= MIN_FIRST_PARTY_MODULES, str(len(IND_MODULES)))
chk('NO single module holds more than %.0f%% of total first-party JS — the '
    'largest, %s, holds %.2f%% (%d of %d bytes)'
    % (MAX_SINGLE_MODULE_SHARE_PCT, IND_LARGEST, IND_LARGEST_PCT,
       IND_MODULES[IND_LARGEST], IND_TOTAL_JS),
    IND_LARGEST_PCT <= MAX_SINGLE_MODULE_SHARE_PCT,
    'a split whose biggest piece still holds most of the code is a rename, '
    'not a split')
chk('the report itself states that share, and it matches the independent '
    'computation',
    abs(J['largest_module_pct_of_first_party_js'] - IND_LARGEST_PCT) < 0.02,
    '%s vs %.2f' % (J['largest_module_pct_of_first_party_js'], IND_LARGEST_PCT))
chk('the top three modules together are still a minority of first-party JS',
    sum(m['bytes'] for m in J['modules'][:3]) * 2 < IND_TOTAL_JS,
    '%d of %d' % (sum(m['bytes'] for m in J['modules'][:3]), IND_TOTAL_JS))

TEXT = json.dumps(R, ensure_ascii=False)
chk('the status names the measurement for what it is and does not claim the '
    'application was verified to run',
    'MEASUREMENT ONLY' in R['status'].upper()
    and ('does NOT prove' in R['status'] or 'not prove' in R['status'].lower()),
    R['status'][:160])
FORBIDDEN_CLAIMS = [
    'performance improved', 'faster load', 'load time reduced',
    'lazy loading implemented', 'code splitting implemented',
    'verified in production', 'brotli measured',
]
for claimq in FORBIDDEN_CLAIMS:
    chk('the report never says %r' % claimq, claimq.lower() not in TEXT.lower())
chk('the report warns it must not be read as evidence that the app works',
    'must not be read as evidence' in R['what_this_is'].lower())
chk('the report lists what it does NOT measure',
    isinstance(R.get('not_measured_here'), list)
    and len(R['not_measured_here']) >= 2)
chk('it names the runtime behaviour as NOT VERIFIED — EXTERNAL ENVIRONMENT '
    'REQUIRED',
    any('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED' in s
        for s in R['not_measured_here']))

# ══════════════════════════════════════════ هـ · الحارس ليس عقيماً ══════════
print('\n== هـ · THE COMPARISON WOULD ACTUALLY CATCH A WRONG NUMBER ==')


def compare(rep):
    """نفس منطق المطابقة أعلاه، مجموعاً — لنمرّر عليه تقارير مغلوطة."""
    bad = []
    if rep['shell']['raw_bytes'] != len(RAW):
        bad.append('shell bytes')
    if rep['shell']['gzip_bytes'] != ind_gzip(RAW):
        bad.append('gzip')
    if rep['shell']['inline_executable_script_count'] != 0:
        bad.append('inline executable script present')
    if rep['javascript']['first_party_total_bytes'] != IND_TOTAL_JS:
        bad.append('first-party total')
    if rep['javascript']['first_party_module_count'] != len(IND_MODULES):
        bad.append('module count mismatch')
    if rep['javascript']['first_party_module_count'] < MIN_FIRST_PARTY_MODULES:
        bad.append('too few modules to be a split')
    if (rep['javascript']['largest_module']['bytes']
            > MAX_SINGLE_MODULE_SHARE_PCT / 100.0
            * rep['javascript']['first_party_total_bytes']):
        bad.append('one module holds too much of the code')
    if rep['javascript']['largest_module']['bytes'] > MODULE_WARN_BYTES \
            and not rep['module_size_warnings']:
        bad.append('oversized module not warned about')
    if rep['budget']['current_index_bytes'] > SHELL_BUDGET_BYTES:
        bad.append('shell over budget')
    if rep['budget']['budget_met'] is not (
            rep['budget']['current_index_bytes'] <= SHELL_BUDGET_BYTES):
        bad.append('budget_met does not follow from the number')
    if rep['javascript']['lazy_bytes'] != sum(IND_MODULES[k] for k in IND_LAZY):
        bad.append('lazy bytes fabricated')
    if 'MEASUREMENT ONLY' not in rep['status'].upper():
        bad.append('status overclaims')
    return bad


chk('the comparison passes the real report', compare(R) == [], str(compare(R)))
for label, mutate in (
        ('a shell size that is off by one byte',
         lambda d: d['shell'].__setitem__('raw_bytes',
                                          d['shell']['raw_bytes'] + 1)),
        ('a fabricated gzip size',
         lambda d: d['shell'].__setitem__('gzip_bytes', 123456)),
        ('an inline executable script sneaking back into the shell',
         lambda d: d['shell'].__setitem__('inline_executable_script_count', 1)),
        ('a fabricated first-party total',
         lambda d: d['javascript'].__setitem__('first_party_total_bytes', 999)),
        ('a module count that is really one big file plus scraps',
         lambda d: d['javascript'].__setitem__('first_party_module_count', 3)),
        ('one module holding 90% of the code (a rename, not a split)',
         lambda d: d['javascript']['largest_module'].__setitem__(
             'bytes', int(0.9 * d['javascript']['first_party_total_bytes']))),
        ('a shell that has grown past the 200 KB budget',
         lambda d: d['budget'].__setitem__('current_index_bytes', 300000)),
        ('budget_met asserted rather than computed',
         lambda d: (d['budget'].__setitem__('current_index_bytes', 300000),
                    d['budget'].__setitem__('budget_met', True))),
        ('invented lazy-loaded bytes',
         lambda d: d['javascript'].__setitem__('lazy_bytes', 500000)),
        ('a status that claims more than measurement',
         lambda d: d.__setitem__('status', 'F-09 COMPLETE AND VERIFIED'))):
    mutant = json.loads(json.dumps(R))
    mutate(mutant)
    chk('the comparison rejects %s' % label, compare(mutant) != [])

print('\n' + '─' * 68)
print('  shell %d B (gzip %d B, brotli %s) · budget %d B · %.1f%% used'
      % (S['raw_bytes'], S['gzip_bytes'], S['brotli_bytes'],
         B['index_shell_budget_bytes'], 100.0 * B['ratio_of_budget_used']))
print('  first-party JS %d B in %d modules · core %d B in %d · boot %d B in %d '
      '· lazy %d B'
      % (J['first_party_total_bytes'], J['first_party_module_count'],
         J['core_initial_bytes'], J['core_initial_module_count'],
         J['boot_bytes'], J['boot_script_count'], J['lazy_bytes']))
print('  largest module %s — %d B = %.2f%% of first-party JS (cap %.0f%%, '
      'warn at %d B)'
      % (J['largest_module']['path'], J['largest_module']['bytes'],
         J['largest_module_pct_of_first_party_js'],
         MAX_SINGLE_MODULE_SHARE_PCT, MODULE_WARN_BYTES))
print('  css %d B (gzip %d B) · module_size_warnings: %d'
      % (C['raw_bytes'], C['gzip_bytes'], len(R['module_size_warnings'])))
print('  STATUS: %s' % R['status'].split('.')[0].strip())
print('─' * 68)
print('BUNDLE REPORT: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
