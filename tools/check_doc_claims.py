#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/check_doc_claims.py — F-53.

النمط الذي بُني هذا الحارس لأجله
--------------------------------
الكود في هذا المستودع محكومٌ بمعيار عالٍ وتصحّحه اختباراته باستمرار. والنثر
الذي يصفه غير محكوم بشيء. أربع حالات وُجدت قبل هذا الحارس، كلّها من النوع
نفسه — جملةٌ تصف حالةً انتهت:

  KI-12  إدخالٌ يصف إعادة هيكلةٍ بأنها تغييرٌ سلوكيّ خطر، ولم تكن تحتاج
         تغييراً سلوكياً أصلاً.
  KI-13  اختبارٌ ما يزال يطبع «قائم» بعد إغلاق العطل بإصلاح كامل.
  KI-14  عنوانٌ يقول OPEN وإدخالٌ لاحق في **الملفّ نفسه** يقول CLOSED.
  KI-27  وثيقةُ المدخل الافتراضي للإصلاح تقول «لا يُكتَب حرف في النموذج
         الهندسي» بينما يكتب في ١٠٨ من ١٦٥ نموذجاً.

كلٌّ منها أُغلق بإعطاء الجملة اختباراً لا بإعادة صياغتها. هذا الحارس يعمّم
ذلك على صنفٍ واحد من الادّعاءات — الوحيد القابل للقياس آلياً بلا التباس:
«حزمة كذا فيها N توكيداً».

لماذا هذا الصنف بالذات
----------------------
لأنه يبلى **بصمت وبسرعة**. أوّل تشغيل لهذا الحارس وجد ٥ من ١١ ادّعاءً قديمة،
أحدها كُتب قبل ساعتين في الجلسة نفسها وبلي قبل أن تنتهي:

    test_csp.js                     141 → 142
    test_csp_style_architecture.js   61 →  64
    test_panel_entry.js              33 →  37
    test_plan_chunking.py            59 →  72
    test_plate_extent.py            158 → 159

لا أحد كتب رقماً خاطئاً. كلّها كانت صحيحة يوم كُتبت، ثم أُضيف توكيد. وهذا
بالضبط ما يجعل الحارس ضرورياً: الخطأ هنا لا يقع بالإهمال بل بمرور الوقت.

القياس، لا التقدير
------------------
كل حزمة تُشغَّل فعلاً ويُقرأ العدد الذي **تعلنه هي عن نفسها**. لا عدّ ساكن
لأنماط نصّية: حزمٌ هنا توكّد داخل حلقات، فالعدّ الساكن يعطي رقماً لا يطابق ما
يجري وقت التشغيل، ويصير الحارس نفسه ادّعاءً غير مقيس.

وهو لهذا بطيء، فلا يُستدعى من بناء الواجهة. موضعه tools/ci_run.sh حيث تُشغَّل
الحزم أصلاً.

الاستعمال:
    python3 tools/check_doc_claims.py            # يفحص ويعيد ١ عند الاختلاف
    python3 tools/check_doc_claims.py --list     # يعرض الادّعاءات بلا تشغيل
    python3 tools/check_doc_claims.py --fix      # يكتب الأرقام المقيسة

الصنف الثاني: كتلة الحالة الراهنة
---------------------------------
أرقام الأحجام في هذا المستودع صنفان لا يميّزهما النحو: «١,٨١٩,٥٨٨ بايت عبر ٢٥
ملفاً» سجلُّ جولة F-09، و«١,٤٣١,٠٦٩ بايت» وصفُ الحاضر بعد F-50 — وكلاهما
بصيغة المضارع. حارسٌ يخمّن المقصود سيُفسد أحد الصنفين حتماً، كما أفسد --fix
رقماً تاريخياً في أوّل تشغيل له.

فلا تخمين: **مكانٌ واحد معلَن للحاضر**، بين علامتَي ACS:CURRENT-STATE، يُولَّد
من tests/performance/bundle_report.json ومن نظام الملفّات مباشرة. ما بداخله
مقيسٌ دائماً؛ وما خارجه نثرٌ يُقرأ سجلّاً لجولته، ولا يُطالَب بمواكبة الحاضر.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# «tests/…/x.py — N assertions» بأي فاصل، مع أو بلا علامات الاقتباس المائلة.
CLAIM = re.compile(
    r'`?(tests/[\w/]+\.(?:py|js))`?'      # الحزمة
    r'([^\n]{0,90}?)'                     # ما بينهما، بلا سطر جديد
    r'(\d+)\s+assertions')                # العدد المدَّعى

DOC_SUFFIX = '.md'

# ادّعاءٌ تاريخيّ ليس ادّعاءً عن الحاضر. «٣٧ توكيداً، بعد أن كانت ٢٩» جملةٌ
# صحيحةٌ تماماً، ورقمُها الثاني يجب أن يبقى ٢٩ إلى الأبد. أوّل تشغيل لهذا
# الحارس رسب في هذا بالذات وطالب بتحديث الرقم التاريخي — وهو الخطأ نفسه الذي
# بُني الحارس ليمنعه، مقلوباً: فرضُ الحاضر على جملةٍ تصف الماضي.
# العلامة تسبق الرقم أو تتبعه، والمفردات تختلف باختلاف الموضع. خلطُهما في
# قائمة واحدة تُفحَص في الاتجاهين أسقط ٣ ادّعاءات حيّة، لأن «was» تَرِد بعد
# أي رقم في نثرٍ عادي. الاتجاه جزءٌ من معنى العلامة، لا تفصيلٌ تقني.
BEFORE_MARKERS = ('up from', 'previously', 'rather than', 'instead of',
                  'was ', 'before F-', 'بعد أن كان', 'كانت ', 'سابقاً')
AFTER_MARKERS = ('as of ', 'at the time of', 'حينها', 'آنذاك', 'في تلك الجولة')
AFTER_WINDOW = 18

# Read each suite's own terminal summary. Python suites are executable scripts
# or stdlib unittest entry points; measuring them must not require pytest.
COUNT_PATTERNS = (
    re.compile(r'(\d+)\s+passed(?:,\s*\d+\s+failed)?'),
    re.compile(r'Ran\s+(\d+)\s+tests?\b'),
)


def discover(root=ROOT):
    """يعيد [(ملفّ التوثيق، الحزمة، العدد المدَّعى، المدى في النصّ)]."""
    out = []
    for name in sorted(os.listdir(root)):
        if not name.endswith(DOC_SUFFIX):
            continue
        path = os.path.join(root, name)
        try:
            with open(path, encoding='utf-8') as fh:
                text = fh.read()
        except OSError:
            continue
        for m in CLAIM.finditer(text):
            # العلامة قد تسبق الرقم («up from 29») أو تتبعه («29 assertions
            # as of F-27»). فحصٌ في اتجاه واحد يفوّت النصف الثاني — وقد فوّته
            # فعلاً، فطالب الحارس بتحديث سجلّ جولةٍ مضت.
            before = m.group(2)
            after = text[m.end(0):m.end(0) + AFTER_WINDOW]
            if (any(h in before for h in BEFORE_MARKERS)
                    or any(h in after for h in AFTER_MARKERS)):
                continue                      # رقمٌ تاريخيّ، لا يُقاس بالحاضر
            out.append((name, m.group(1), int(m.group(3)),
                        (m.start(3), m.end(3))))
    return out


def measure(suite, timeout=600):
    """يشغّل الحزمة ويعيد (العدد، سبب الفشل إن تعذّر)."""
    full = os.path.join(ROOT, suite)
    if not os.path.exists(full):
        return None, 'الملفّ غير موجود'
    env = dict(os.environ, ACS_ENV='test',
               ANTHROPIC_API_KEY=os.environ.get('ANTHROPIC_API_KEY', 'dummy'))
    cmd = ['node' if suite.endswith('.js') else sys.executable, full]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.TimeoutExpired:
        return None, 'تجاوز المهلة (%ds)' % timeout
    except OSError as exc:
        return None, 'تعذّر تشغيل الحزمة: %s' % type(exc).__name__
    text = proc.stdout.decode('utf-8', 'replace')
    if proc.returncode != 0:
        tail = ' | '.join(text.strip().splitlines()[-3:])[:240]
        return None, 'suite exited %d: %s' % (proc.returncode, tail)
    best = None
    for pat in COUNT_PATTERNS:
        found = pat.findall(text)
        if found:
            best = int(found[-1])
            break
    if best is None:
        # حزمٌ تطبع تقريرها بالعربية أو بصيغة خاصّة: يُعدّ سطور «✓».
        ticks = len(re.findall(r'(?m)^\s*[✓·]\s', text))
        if ticks:
            best = ticks
    if best is not None:
        return best, None
    # لا عدد. إن كانت الحزمة تعلن أن جزءاً من تغطيتها يحتاج بيئة خارجية،
    # فالنقص في البيئة لا في التوثيق، ولا يجوز إعلان الادّعاء بالياً.
    #
    # الترتيب هنا مقصود وقد أخطأتُ فيه أوّلاً: كان هذا الفحص قبل استخراج
    # العدد، فتخطّى حزماً تطبع تلك الجملة كملاحظة نطاق **وتنجح وتعلن عددها**
    # في السطر التالي — أي أنه أسكت قياساً ممكناً. الشرط الصحيح: تخطَّ فقط
    # حين لا يوجد عدد أصلاً.
    if 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED' in text:
        return None, 'SKIP: الحزمة لم تعلن عدداً وتحتاج بيئة خارجية'
    tail = ' | '.join(x.strip() for x in text.strip().split('\n')[-2:])[:90]
    return None, 'تعذّر استخراج عدد — آخر مخرَج: %s' % tail


STATE_BEGIN = '<!-- ACS:CURRENT-STATE:BEGIN — مولَّدة بـtools/check_doc_claims.py، لا تُحرَّر يدوياً -->'
STATE_END = '<!-- ACS:CURRENT-STATE:END -->'
STATE_DOC = 'KNOWN-ISSUES.md'


def _fmt(n):
    return format(int(n), ',')


def render_state():
    """يبني كتلة الحالة الراهنة من القياس وحده."""
    import json as _json
    rp = os.path.join(ROOT, 'tests', 'performance', 'bundle_report.json')
    with open(rp, encoding='utf-8') as fh:
        j = _json.load(fh)
    shell = os.path.join(ROOT, 'public', 'index.html')
    js = j['javascript']
    lazy = js.get('lazy_declared') or j.get('lazy_declared') or []
    total = js['first_party_total_bytes']
    rows = [
        ('index shell (`public/index.html`)', '%s B' % _fmt(os.path.getsize(shell))),
        ('first-party JavaScript, all modules', '%s B in %d modules'
         % (_fmt(total), js['first_party_module_count'])),
        ('evaluated on first load (core + boot)', '%s B'
         % _fmt(js['initial_javascript_bytes'])),
        ('  of which core modules', '%s B in %d modules'
         % (_fmt(js['core_initial_bytes']), js['core_initial_module_count'])),
        ('deferred until a panel is opened', '%s B in %d modules'
         % (_fmt(js['lazy_bytes']), js['lazy_module_count'])),
        ('share of first-party JS deferred', '%.1f %%'
         % (100.0 * js['lazy_bytes'] / total if total else 0.0)),
        ('largest single module', '%s B of a %s B cap'
         % (_fmt(j['budget']['largest_module_bytes']),
            _fmt(j['budget']['max_single_module_budget_bytes']))),
    ]
    out = [STATE_BEGIN, '',
           '### Current measured source state',
           '',
           'Generated from `tests/performance/bundle_report.json` and the files',
           'themselves before build provenance stamping. Deployment-specific',
           'identity values are outside this source snapshot. Every size figure',
           'that describes **today** lives here and',
           'nowhere else; a number in the prose above is the record of its own pass',
           'and is not expected to track the present.',
           '',
           '| | |', '|---|---|']
    for k, v in rows:
        out.append('| %s | **%s** |' % (k, v))
    out += ['', 'Deferred modules, in load order:', '']
    for m in lazy:
        out.append('* `%s`' % m)
    out += ['', STATE_END]
    return '\n'.join(out)


def state_block(text):
    i = text.find(STATE_BEGIN)
    if i < 0:
        return None
    j = text.find(STATE_END, i)
    if j < 0:
        return None
    return text[i:j + len(STATE_END)]


def check_state(fix=False):
    """يعيد (سليم؟، رسالة)."""
    path = os.path.join(ROOT, STATE_DOC)
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    try:
        want = render_state()
    except (OSError, KeyError) as exc:
        return False, 'تعذّر بناء كتلة الحالة: %r' % (exc,)
    have = state_block(text)
    if have is None:
        if not fix:
            return False, 'كتلة الحالة الراهنة غائبة عن %s' % STATE_DOC
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text.rstrip() + '\n\n---\n\n' + want + '\n')
        return True, 'أُنشئت كتلة الحالة الراهنة في %s' % STATE_DOC
    if have == want:
        return True, 'كتلة الحالة الراهنة تطابق القياس.'
    if not fix:
        return False, ('كتلة الحالة الراهنة لا تطابق القياس — الأرقام تحرّكت '
                       'ولم تُعَد التوليد. شغّل --fix.')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text.replace(have, want))
    return True, 'أُعيد توليد كتلة الحالة الراهنة.'


def main(argv):
    claims = discover()
    if not claims:
        print('لا ادّعاءات «N assertions» في ملفّات التوثيق — لا شيء يُفحَص.')
        return 0
    if '--list' in argv:
        for doc, suite, n, _span in claims:
            print('%-22s %-52s %d' % (doc, suite, n))
        return 0

    fix = '--fix' in argv
    state_ok, state_msg = check_state(fix=fix)
    print(('  ✓ ' if state_ok else '  ✗ ') + state_msg + '\n')
    print('فحص %d ادّعاءً في التوثيق بتشغيل حزمها فعلاً…\n' % len(claims))
    stale, broken, skipped, ok = [], [], [], 0
    measured = {}
    for _doc, suite, _n, _span in claims:
        if suite not in measured:
            measured[suite] = measure(suite)
    for doc, suite, claimed, _span in claims:
        actual, err = measured[suite]
        if err and err.startswith('SKIP:'):
            skipped.append((suite, err[5:].strip()))
            print('  ~  %-50s %-6s %s' % (suite, claimed, err[5:].strip()))
        elif err:
            broken.append((doc, suite, claimed, err))
            print('  ?  %-50s %-6s %s' % (suite, claimed, err))
        elif actual != claimed:
            stale.append((doc, suite, claimed, actual))
            print('  ✗  %-50s موثَّق=%-5d فعلي=%d' % (suite, claimed, actual))
        else:
            ok += 1
            print('  ✓  %-50s %d' % (suite, claimed))

    print()
    # --fix يكتب في التوثيق، فهو أخطر ما هنا. أوّل تشغيل له أعاد كتابة رقم
    # تاريخيّ («٢٩ توكيداً as of F-27») بالرقم الحالي، فمحا سجلّ جولةٍ مضت —
    # الخطأ الذي بُني هذا الحارس ليمنعه، بيد الحارس نفسه. العلامة 'as of'
    # أُضيفت أعلاه، والفلترة تجري في discover() قبل أن يرى --fix شيئاً.
    if fix and stale:
        by_doc = {}
        for doc, suite, _c, actual in stale:
            by_doc.setdefault(doc, []).append((suite, actual))
        for doc, rows in by_doc.items():
            path = os.path.join(ROOT, doc)
            with open(path, encoding='utf-8') as fh:
                text = fh.read()
            for suite, actual in rows:
                def _sub(m, _s=suite, _a=actual):
                    # يُستبدَل **الرقم وحده** داخل النصّ المطابَق. صياغةٌ أولى
                    # أعادت بناء السطر من مجموعات النمط، فمحت العلامات المائلة
                    # حول مسار الحزمة — الأداة أفسدت التوثيق وهي تصحّحه.
                    if m.group(1) != _s:
                        return m.group(0)
                    whole = m.group(0)
                    lo = m.start(3) - m.start(0)
                    hi = m.end(3) - m.start(0)
                    return whole[:lo] + str(_a) + whole[hi:]
                text = CLAIM.sub(_sub, text)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)
            print('كُتبت %d قيمة في %s' % (len(rows), doc))
        return 0

    if not state_ok:
        print('DOC CLAIMS FAILED: ' + state_msg)
        return 1
    if not stale and not broken and not skipped:
        note = ('' if not skipped
                else ' (و%d تخطّاها لأن حزمتها تحتاج بيئة خارجية)' % len(skipped))
        print('✓ كل ادّعاء قابل للقياس يطابق ما تعلنه حزمته: %d من %d%s.'
              % (ok, len(claims), note))
        return 0
    if stale:
        print('DOC CLAIMS FAILED: %d ادّعاءً بلي.' % len(stale))
        print('العدد صحيح يوم كُتب ثم أُضيف توكيد — هذا هو النمط بعينه.')
        print('شغّل: python3 tools/check_doc_claims.py --fix')
    if broken:
        # An unavailable or failed suite is not evidence of a stale number,
        # but it is still a failed verification. CI must prove every claim.
        print('DOC CLAIMS FAILED: %d suite(s) could not be measured successfully.'
              % len(broken))
    if skipped:
        print('DOC CLAIMS FAILED: %d suite(s) require an unavailable environment.'
              % len(skipped))
    return 1 if (stale or broken or skipped or not state_ok) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
