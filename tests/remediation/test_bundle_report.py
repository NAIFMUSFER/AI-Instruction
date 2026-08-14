# -*- coding: utf-8 -*-
"""F-09 — تقرير الحزمة: رقم مقيس، حتميّ، ولا يدّعي أن التفكيك جرى.

    python3 tests/remediation/test_bundle_report.py

ثلاثة أشياء تُثبَت هنا، وواحد يُمنَع:

  أ) التقرير موجود ويُعاد إنتاجه حتميّاً: يُشغَّل tools/bundle_report.py مرّتين
     ويُقارَن المخرَجان بايتاً ببايت. تقرير غير حتميّ لا يصلح خطَّ أساسٍ يُقاس
     عليه تحسّن لاحق.

  ب) كل رقم فيه يطابق قياساً مستقلّاً للملفّ نفسه — مستقلّاً فعلاً: هذا الملفّ
     لا يستورد tools/bundle_report.py ولا يستدعي أيّاً من دوالّه، بل يقيس على
     البايتات الخام (bytes) لا على النصّ (str)، بمسح مكتوب هنا من الصفر. لو
     كان يستدعي الأداة لكان يقارن الأداة بنفسها، وهو لا شيء.

  ج) الحارس ليس عقيماً: تُمرَّر عليه أرقام مغلوطة عمداً ويجب أن يمسكها.

  د) المنع: التقرير لا يجوز أن يدّعي أن F-09 نُفِّذ. الصفحة ما زالت كتلة واحدة،
     وأي صياغة تلمّح إلى غير ذلك تُسقِط هذا الملفّ.
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
TOOL = os.path.join(ROOT, "tools", "bundle_report.py")
REPORT = os.path.join(ROOT, "tests", "performance", "bundle_report.json")

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
# يعمل على البايتات لا على النصّ، ولا يشترك في سطر واحد مع الأداة.
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

# الكتل المولَّدة — مسح سطريّ (طريقة أخرى تماماً عن regex الأداة)
IND_BLOCKS = []
_off = 0
_begin_js = re.compile(rb'^/\* ===== ACS (?!END)(.*?) ===== \*/\s*$')
_begin_dom = re.compile(rb'^<!-- ===== ACS (?!END)(.*?) ===== -->\s*$')
_line_offsets = []
for _line in RAW.split(b'\n'):
    _line_offsets.append((_off, _line))
    _off += len(_line) + 1
for _start, _line in _line_offsets:
    for _rx, _kind, _end in ((_begin_js, 'js', b'/* ===== END ACS %s ===== */'),
                             (_begin_dom, 'dom', b'<!-- ===== END ACS %s ===== -->')):
        m = _rx.match(_line.strip())
        if not m:
            continue
        name = m.group(1)
        core = name.split(b' (')[0].strip()
        endm = _end % core
        e = RAW.find(endm, _start)
        if e < 0:
            IND_BLOCKS.append({"name": core.decode(), "kind": "UNPAIRED",
                               "bytes": 0, "start": _start, "stop": _start})
            continue
        # موضع بداية السطر نفسه (بعد أي مسافة بادئة) — الأداة تبدأ من `/*`
        real = RAW.find(m.group(0).split(b' ===== ')[0], _start)
        IND_BLOCKS.append({
            "name": core.decode(), "kind": _kind,
            "bytes": (e + len(endm)) - real, "start": real,
            "stop": e + len(endm)})
IND_BLOCKS.sort(key=lambda x: x["start"])
# CSS = كل كتلة تقع داخل جسم <style>
for blkq in IND_BLOCKS:
    for st in IND_STYLES:
        if st["body_start"] <= blkq["start"] < st["body_end"] and blkq["kind"] == 'js':
            blkq["kind"] = 'css'


def ind_gzip():
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=9, mtime=0) as g:
        g.write(RAW)
    return len(buf.getvalue())


# ═══════════════════════════════════════════════════ أ · الوجود والحتمية ════
print('\n== أ · THE REPORT EXISTS AND IS REGENERATED DETERMINISTICALLY ==')
chk('tools/bundle_report.py exists', os.path.isfile(TOOL))
chk('the tool declares itself measurement-only in its docstring',
    'قياس فقط' in io.open(TOOL, encoding='utf-8').read()
    or 'measurement only' in io.open(TOOL, encoding='utf-8').read().lower())


def run_tool(args=()):
    return subprocess.run([sys.executable, TOOL] + list(args), cwd=ROOT,
                          capture_output=True, text=True)


r1 = run_tool(['--stdout'])
r2 = run_tool(['--stdout'])
chk('the tool runs cleanly (twice)', r1.returncode == 0 and r2.returncode == 0,
    (r1.stderr or r2.stderr)[:200])
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
    w.returncode == 0 and os.path.isfile(REPORT), w.stderr[:200])
R = json.loads(io.open(REPORT, encoding='utf-8').read())
chk('the written file equals what the tool prints',
    io.open(REPORT, encoding='utf-8').read() == r1.stdout)
chk('the report declares itself deterministic', R.get('deterministic') is True)

# ═════════════════════════════ ب · مطابقة قياس مستقلّ للملفّ نفسه ═══════════
print('\n== ب · EVERY NUMBER MATCHES A FRESH INDEPENDENT MEASUREMENT ==')
chk('this test does not import the tool it checks (otherwise it would be '
    'comparing the tool with itself)',
    'bundle_report' not in [m for m in sys.modules]
    and ('import ' + 'bundle_report')
    not in io.open(__file__, encoding='utf-8').read().replace(
        "'import ' + 'bundle_report'", ''))

chk('total page bytes match', R['source']['bytes'] == len(RAW),
    '%s vs %s' % (R['source']['bytes'], len(RAW)))
chk('total page bytes match os.path.getsize as a third witness',
    R['source']['bytes'] == os.path.getsize(PAGE))
chk('sha256 of the page matches',
    R['source']['sha256'] == hashlib.sha256(RAW).hexdigest())
chk('line count matches', R['source']['lines'] == RAW.count(b'\n') + 1)
chk('gzip size matches an independently computed gzip',
    R['compression']['gzip_bytes'] == ind_gzip(),
    '%s vs %s' % (R['compression']['gzip_bytes'], ind_gzip()))
chk('gzip is a real reduction, so it was really computed (not copied from raw)',
    0 < R['compression']['gzip_bytes'] < R['source']['bytes'])

chk('script element count matches (%d)' % len(IND_SCRIPTS),
    R['elements']['script_element_count'] == len(IND_SCRIPTS),
    '%s vs %s' % (R['elements']['script_element_count'], len(IND_SCRIPTS)))
chk('style element count matches (%d)' % len(IND_STYLES),
    R['elements']['style_element_count'] == len(IND_STYLES))
chk('there is exactly ONE <style> block — the fact F-09 must change',
    len(IND_STYLES) == 1)
for i, (rep_s, ind_s) in enumerate(zip(R['elements']['scripts'], IND_SCRIPTS), 1):
    chk('script #%d (%s, line %d): body bytes match (%d)'
        % (i, rep_s['kind'], rep_s['line'], ind_s['body_bytes']),
        rep_s['body_bytes'] == ind_s['body_bytes']
        and rep_s['kind'] == ind_s['kind'],
        '%s/%s vs %s/%s' % (rep_s['kind'], rep_s['body_bytes'],
                            ind_s['kind'], ind_s['body_bytes']))
chk('the single <style> body byte count matches (%d)' % IND_STYLES[0]['body_bytes'],
    R['elements']['styles'][0]['body_bytes'] == IND_STYLES[0]['body_bytes'])
chk('the classic/module/importmap totals add up to the per-element sum',
    R['elements']['totals']['classic_script_bytes']
    + R['elements']['totals']['module_script_bytes']
    + R['elements']['totals']['importmap_script_bytes']
    == sum(s['body_bytes'] for s in IND_SCRIPTS))

print('\n  -- generated marker blocks --')
counts = {'js': 0, 'css': 0, 'dom': 0}
for blk in IND_BLOCKS:
    counts[blk['kind']] = counts.get(blk['kind'], 0) + 1
chk('10 generated JS pairs, independently counted',
    counts.get('js') == 10 == R['generated_blocks']['counts']['js'],
    'independent=%s report=%s' % (counts.get('js'),
                                  R['generated_blocks']['counts']['js']))
chk('6 generated CSS pairs, independently counted',
    counts.get('css') == 6 == R['generated_blocks']['counts']['css'],
    'independent=%s report=%s' % (counts.get('css'),
                                  R['generated_blocks']['counts']['css']))
chk('6 generated DOM pairs, independently counted',
    counts.get('dom') == 6 == R['generated_blocks']['counts']['dom'],
    'independent=%s report=%s' % (counts.get('dom'),
                                  R['generated_blocks']['counts']['dom']))
chk('no generated marker is left unpaired',
    R['generated_blocks']['counts']['unpaired'] == 0)
IND_BY_NAME = {b['name']: b for b in IND_BLOCKS}
for blk in R['generated_blocks']['blocks']:
    ind = IND_BY_NAME.get(blk['name'])
    chk('block %-20s (%s): %7d bytes matches independently'
        % (blk['name'], blk['kind'], blk['bytes']),
        ind is not None and ind['bytes'] == blk['bytes']
        and ind['kind'] == blk['kind'],
        'independent=%s' % (str(ind and (ind['kind'], ind['bytes'])),))
chk('the sum of generated blocks matches the declared total',
    R['generated_blocks']['total_bytes']
    == sum(b['bytes'] for b in R['generated_blocks']['blocks'])
    == sum(b['bytes'] for b in IND_BLOCKS))
chk('the hand-written remainder is exactly page minus generated',
    R['hand_written']['remainder_bytes']
    == len(RAW) - sum(b['bytes'] for b in IND_BLOCKS))
chk('the remainder is a real majority of the page — F-09 is mostly hand work',
    R['hand_written']['remainder_bytes'] > R['generated_blocks']['total_bytes'])

print('\n  -- brotli and vendored assets: null-with-reason, never estimated --')
brv, brr = R['compression']['brotli_bytes'], R['compression']['brotli_reason']
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

# ═══════════════════════════════════════════════════════ ج · الميزانية ══════
print('\n== ج · THE BUDGET IS DECLARED, AND THE CURRENT DELTA IS STATED ==')
B = R['budget']
chk('an index-shell budget is declared as a number',
    isinstance(B['index_shell_budget_bytes'], int)
    and B['index_shell_budget_bytes'] > 0)
chk('the budget is dramatically smaller than the current page',
    B['index_shell_budget_bytes'] * 5 < B['current_index_bytes'],
    '%d vs %d' % (B['index_shell_budget_bytes'], B['current_index_bytes']))
chk('the current page really is over 1 MB', B['current_index_bytes'] > 1024 * 1024)
chk('the current delta is stated and arithmetically correct',
    B['current_delta_bytes']
    == B['current_index_bytes'] - B['index_shell_budget_bytes'] > 0,
    str(B['current_delta_bytes']))
chk('the over-budget ratio is stated',
    B['current_ratio_over_budget'] > 1.0, str(B['current_ratio_over_budget']))
chk('budget_met is FALSE — the budget is a target, not an achievement',
    B['budget_met'] is False)
chk('the budget section says plainly that these are targets',
    'TARGET' in B['budget_note'].upper())
chk('the largest single inline script is stated and is the application module',
    B['largest_single_inline_script_bytes']
    == max(s['body_bytes'] for s in IND_SCRIPTS))

# ══════════════════════════════════ د · لا ادّعاء بأن التفكيك جرى ═══════════
print('\n== د · THE REPORT DOES NOT CLAIM THE MODULARISATION WAS DONE ==')
chk('status is exactly the declared measurement-only status',
    R['status'] == 'F-09 NOT IMPLEMENTED — measurement only', R['status'])
chk('the status says NOT IMPLEMENTED', 'NOT IMPLEMENTED' in R['status'])
TEXT = json.dumps(R, ensure_ascii=False)
FORBIDDEN_CLAIMS = [
    'F-09 complete', 'F-09 COMPLETE', 'F-09 done', 'F-09 implemented',
    'modularisation complete', 'modularization complete',
    'frontend modularised', 'frontend modularized',
    'split into public/app', 'now modular', 'budget met',
]
for claimq in FORBIDDEN_CLAIMS:
    chk('the report never says %r' % claimq, claimq.lower() not in TEXT.lower())
chk('the report explicitly warns it must not be read as evidence of the split',
    'must not be read as evidence' in R['what_this_is'].lower()
    or 'does NOT modify' in R['what_this_is'])
chk('reality check: public/app/ does not exist, so nothing was split',
    not os.path.isdir(os.path.join(ROOT, 'public', 'app')))
chk('reality check: the shipped page still loads zero external application '
    'scripts',
    not re.search(rb'<script[^>]+src\s*=\s*["\']/app/', RAW))
chk('reality check: the application is still one inline module of >1 MB',
    max(s['body_bytes'] for s in IND_SCRIPTS if s['kind'] == 'module')
    > 1024 * 1024)
chk('the report lists what it does NOT measure',
    isinstance(R.get('not_measured_here'), list)
    and len(R['not_measured_here']) >= 2)
chk('it names the runtime cost as NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
    any('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED' in s
        for s in R['not_measured_here']))

# ══════════════════════════════════════════ هـ · الحارس ليس عقيماً ══════════
print('\n== هـ · THE COMPARISON WOULD ACTUALLY CATCH A WRONG NUMBER ==')


def compare(rep):
    """نفس منطق المطابقة أعلاه، مجموعاً — لنمرّر عليه تقارير مغلوطة."""
    bad = []
    if rep['source']['bytes'] != len(RAW):
        bad.append('total bytes')
    if rep['compression']['gzip_bytes'] != ind_gzip():
        bad.append('gzip')
    if rep['elements']['script_element_count'] != len(IND_SCRIPTS):
        bad.append('script count')
    if rep['generated_blocks']['counts']['js'] != 10:
        bad.append('js blocks')
    if rep['generated_blocks']['total_bytes'] != sum(b['bytes'] for b in IND_BLOCKS):
        bad.append('generated total')
    if 'NOT IMPLEMENTED' not in rep['status']:
        bad.append('status claims implementation')
    if rep['budget']['budget_met'] is not False:
        bad.append('budget claimed met')
    return bad


chk('the comparison passes the real report', compare(R) == [], str(compare(R)))
for label, mutate in (
        ('a page size that is off by one byte',
         lambda d: d['source'].__setitem__('bytes', d['source']['bytes'] + 1)),
        ('a fabricated gzip size',
         lambda d: d['compression'].__setitem__('gzip_bytes', 123456)),
        ('a missing script element',
         lambda d: d['elements'].__setitem__('script_element_count', 6)),
        ('a wrong generated-block count',
         lambda d: d['generated_blocks']['counts'].__setitem__('js', 9)),
        ('a generated total that does not add up',
         lambda d: d['generated_blocks'].__setitem__('total_bytes', 1)),
        ('a status that claims F-09 was implemented',
         lambda d: d.__setitem__('status', 'F-09 IMPLEMENTED')),
        ('a budget declared met',
         lambda d: d['budget'].__setitem__('budget_met', True))):
    mutant = json.loads(json.dumps(R))
    mutate(mutant)
    chk('the comparison rejects %s' % label, compare(mutant) != [])

print('\n' + '─' * 62)
print('  page %d B · gzip %d B · brotli %s · module %d B · generated %d B · '
      'remainder %d B'
      % (R['source']['bytes'], R['compression']['gzip_bytes'],
         R['compression']['brotli_bytes'],
         R['elements']['totals']['module_script_bytes'],
         R['generated_blocks']['total_bytes'],
         R['hand_written']['remainder_bytes']))
print('  budget %d B · delta +%d B (%.2f× over) · budget_met=%s'
      % (B['index_shell_budget_bytes'], B['current_delta_bytes'],
         B['current_ratio_over_budget'], B['budget_met']))
print('  STATUS: %s' % R['status'])
print('─' * 62)
print('BUNDLE REPORT: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
