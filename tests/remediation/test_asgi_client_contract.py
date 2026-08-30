#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_asgi_client_contract.py
#
# الثابت: **طبقة اختبار ASGI قابلة للبناء أصلاً.**
#
# العطل الذي أوجب هذا الملفّ
# --------------------------
#   tests/phase9_2/test_backend_contract.py:371
#       client = TestClient(API.app, raise_server_exceptions=False)
#   TypeError: Client.__init__() got an unexpected keyword argument 'app'
#
# ولم يكن عطلاً في الشفرة ولا في الاختبار: كان انجرافَ إصدارٍ لم يكن مثبَّتاً.
#
#   • starlette يجلبه fastapi، و httpx يجلبه anthropic. لم يكن أيّهما مثبَّتاً
#     في requirements.txt، فكان `pip install -r requirements.txt` يحلّهما إلى
#     أحدث المتاح **يوم تشغيل CI**. أي أن نتيجة البناء دالّة في التاريخ.
#   • httpx 0.28.0 (2024-11-28): «The deprecated `app` argument has now been
#     removed.» آخر إصدار يقبله: 0.27.x.
#   • starlette أزال تمرير `app=` إلى httpx.Client داخل TestClient في
#     0.37.0 (2024-02-05، PR #2526).
#   • fastapi==0.110 يعلن `starlette>=0.36.3,<0.37.0` — أي أنه **يستبعد كل
#     إصدار من starlette يعمل مع httpx ≥ 0.28**.
#
# فالتقاطع خالٍ: على هذه المجموعة، أيّ httpx ≥ 0.28 يرمي حتماً — لا احتمالاً —
# عند بناء TestClient، قبل أن يُنفَّذ توكيد واحد.
#
# ما لا يفعله هذا الملفّ
# ---------------------
# لا يلفّ البناء في try/except ولا يحوّل الانهيار إلى «NOT VERIFIED». ذلك
# إخفاءُ العطل لا إصلاحه: الاختبار كان محقّاً في السقوط، والخطأ كان في
# الإصدارات. يُثبَّت هنا القيدُ نفسه، فلا يعود الانجراف ممكناً صامتاً.
#
# يعمل بلا شبكة وبلا تثبيت أيّ حزمة: يقرأ التثبيتات من ملفّات المستودع.
# وإن صادف بيئةً فيها الحزم مركَّبة فعلاً، أضاف فحصاً حيّاً فوق ذلك.
# ==============================================================================
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

_p = _f = 0


def chk(name, cond, detail=''):
    global _p, _f
    if cond:
        _p += 1
        print('  ✓', name)
    else:
        _f += 1
        print('  ✗', name, ('\n      ' + str(detail)) if detail else '')


def rd(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def ver(v):
    """'0.27.2' → (0, 27, 2). يقارن رقماً برقم لا نصّاً: '0.9' > '0.28' نصّياً."""
    parts = []
    for chunk in str(v).split('.'):
        m = re.match(r'^(\d+)', chunk)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def pins(text):
    """يقرأ `name==version` من سطر غير معلَّق. المفاتيح بحروف صغيرة وبلا extras."""
    out = {}
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        m = re.match(r'^([A-Za-z0-9._-]+)(\[[^\]]*\])?==([^\s;]+)$', line)
        if m:
            out[m.group(1).lower().replace('_', '-')] = m.group(3)
    return out


# ── العقد نفسه، مكتوباً مرّةً واحدة ─────────────────────────────────────────
# الشاهد لكل رقم مذكور في الترويسة أعلاه.
HTTPX_DROPPED_APP = (0, 28, 0)      # httpx 0.28.0 — أزال وسيط `app`
STARLETTE_FIXED_AT = (0, 37, 0)     # starlette 0.37.0 — توقّف عن تمريره


def compatible(starlette_v, httpx_v):
    """صحيحٌ إن أمكن بناء starlette.testclient.TestClient بهذين الإصدارين.

    القاعدة الوحيدة: starlette الذي ما زال يمرّر `app=` يحتاج httpx يقبله.
    """
    if ver(starlette_v) >= STARLETTE_FIXED_AT:
        return True                                  # لم يعد يمرّره أصلاً
    return ver(httpx_v) < HTTPX_DROPPED_APP


print('== أ · الحزمتان اللتان كسرتا CI مثبَّتتان الآن في الملفّات الثلاثة ==')
FILES = {'requirements.in': rd('requirements.in'),
         'requirements.txt': rd('requirements.txt'),
         'requirements.lock': rd('requirements.lock')}
TXT = pins(FILES['requirements.txt'])
LOCK = pins(FILES['requirements.lock'])

for name in ('starlette', 'httpx'):
    chk('%s is pinned in requirements.txt' % name, name in TXT, sorted(TXT))
    chk('%s is pinned in requirements.lock' % name, name in LOCK, sorted(LOCK))
    chk('%s is declared in requirements.in (a human decision, not a '
        'resolver accident)' % name,
        re.search(r'^\s*%s\s*$' % name, FILES['requirements.in'], re.M)
        is not None)
    chk('%s agrees between requirements.txt and requirements.lock' % name,
        TXT.get(name) == LOCK.get(name),
        '%s vs %s' % (TXT.get(name), LOCK.get(name)))

chk('neither is left as an inert UNRESOLVED-OFFLINE line — a name cannot be '
    'both pinned and unresolved',
    not re.search(r'^#\s*UNRESOLVED-OFFLINE\s+(starlette|httpx)\b',
                  FILES['requirements.lock'], re.M))

print('\n== ب · التثبيتان متوافقان — وهذا هو الثابت المحروس ==')
S, H = TXT.get('starlette', '0'), TXT.get('httpx', '0')
print('     starlette==%s   httpx==%s' % (S, H))
chk('the pinned pair can construct starlette.testclient.TestClient',
    compatible(S, H),
    'starlette %s still passes app= to httpx.Client, and httpx %s removed it'
    % (S, H))
chk('httpx stays below the release that removed the `app` argument (0.28.0), '
    'because the pinned starlette is below the release that stopped passing '
    'it (0.37.0)',
    ver(S) >= STARLETTE_FIXED_AT or ver(H) < HTTPX_DROPPED_APP,
    'starlette=%s httpx=%s' % (S, H))
chk('httpx satisfies anthropic 0.40\'s own declared `httpx>=0.23.0, <1`',
    (0, 23, 0) <= ver(H) < (1, 0, 0), H)

print('\n== ج · التثبيت لا يخالف ما يعلنه fastapi نفسه ==')
# fastapi 0.110.0 · pyproject.toml, verbatim: "starlette>=0.36.3,<0.37.0"
FASTAPI_STARLETTE_RANGE = ((0, 36, 3), (0, 37, 0))
chk('fastapi is pinned at the version this range was read from',
    TXT.get('fastapi') == '0.110', TXT.get('fastapi'))
chk('the starlette pin sits inside fastapi 0.110\'s declared range '
    '>=0.36.3,<0.37.0 — it removes a float, it does not narrow the framework',
    FASTAPI_STARLETTE_RANGE[0] <= ver(S) < FASTAPI_STARLETTE_RANGE[1], S)
chk('that range excludes every starlette that works with httpx>=0.28, which '
    'is why httpx had to be the pin that moves',
    FASTAPI_STARLETTE_RANGE[1] <= STARLETTE_FIXED_AT)

print('\n== د · شاهد سالب: القاعدة تُدين التركيبة التي كسرت CI فعلاً ==')
# لو كانت compatible() متساهلة لمرّ كل ما تحتها. لا يمرّ.
chk('the exact combination CI installed (starlette 0.36.3 + httpx 0.28.1) is '
    'reported INCOMPATIBLE', not compatible('0.36.3', '0.28.1'))
chk('and so is any later httpx on that starlette (0.36.3 + 0.29.0)',
    not compatible('0.36.3', '0.29.0'))
chk('the repaired pair (0.36.3 + 0.27.2) is reported compatible',
    compatible('0.36.3', '0.27.2'))
chk('the forward path (starlette 0.37.0 + httpx 0.28.1) is reported '
    'compatible — the rule permits the upgrade, it does not forbid it',
    compatible('0.37.0', '0.28.1'))
# لو قُورنت الإصدارات نصّاً لَعُدَّ 0.9 أحدث من 0.28، ولانقلب الحكم كلّه.
chk('version comparison is numeric, not lexicographic: as strings '
    '"0.9.0" > "0.28.0", but numerically 0.9.0 < 0.28.0 — and the rule uses '
    'the numeric order',
    '0.9.0' > '0.28.0' and ver('0.9.0') < ver('0.28.0'))
chk('so an httpx 0.9-style version is NOT mistaken for one past 0.28',
    compatible('0.36.3', '0.9.0'))

print('\n== هـ · الاختبار الذي سقط ما زال يبني TestClient بلا حماية ==')
BC = 'tests/phase9_2/test_backend_contract.py'
src = rd(BC)
ctor = re.search(r'^\s*client\s*=\s*TestClient\(', src, re.M)
chk('%s still constructs TestClient at module level' % BC, ctor is not None)
if ctor:
    line_no = src[:ctor.start()].count('\n') + 1
    # الأسطر الخمسة قبل البناء: لا try ولا except يلتقط الانهيار
    before = '\n'.join(src.splitlines()[max(0, line_no - 6):line_no - 1])
    chk('the construction is NOT wrapped in a try/except that would downgrade '
        'this failure to a skip — the fix is the pin, not a swallowed error',
        not re.search(r'^\s*try\s*:\s*$', before, re.M), before.strip()[-120:])
chk('it still passes raise_server_exceptions=False, so a 500 is asserted on '
    'rather than raised past the assertions',
    'raise_server_exceptions=False' in src)
chk('no pytest.skip / unittest.skip was introduced into it',
    'skip' not in src.lower().replace('skipped', ''))

print('\n== و · طبقة حيّة إن كانت الحزم مركَّبة (وإلا: تُعلَن غير متحقَّقة) ==')
live = {}
for mod in ('httpx', 'starlette', 'fastapi'):
    try:
        m = __import__(mod)
        live[mod] = getattr(m, '__version__', None)
    except Exception:                                       # noqa: BLE001
        live[mod] = None

if all(live.values()):
    print('     installed: ' + ', '.join('%s %s' % kv for kv in live.items()))
    chk('the INSTALLED pair is compatible by the same rule',
        compatible(live['starlette'], live['httpx']),
        live)
    chk('the installed versions match the pins',
        live['starlette'] == S and live['httpx'] == H, live)
    try:
        from starlette.applications import Starlette
        from starlette.testclient import TestClient
        c = TestClient(Starlette(), raise_server_exceptions=False)
        chk('TestClient(app) actually constructs — the original TypeError is '
            'gone, measured not inferred', c is not None)
    except TypeError as e:                                  # noqa: BLE001
        chk('TestClient(app) actually constructs', False, 'TypeError: %s' % e)
    except Exception as e:                                  # noqa: BLE001
        chk('TestClient(app) actually constructs', False,
            '%s: %s' % (type(e).__name__, e))
else:
    missing = [k for k, v in live.items() if not v]
    print('  NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: %s not installed '
          'here (this sandbox has no package index: pip returns HTTP 403).'
          % ', '.join(missing))
    print('  Sections أ…هـ above are read from the repository files and are '
          'fully executed; only the live construction needs an install.')

print('\n== ز · الآليّة نفسها، مقيسة على المكتبة الحقيقية المركَّبة ==')
# هذا القسم لا يحتاج التثبيتات المطلوبة — يحتاج httpx أيّاً كان إصداره.
# يربط ثابتَ القاعدة (0.28.0) بسلوكٍ مُنفَّذ بدل أن يبقى رقماً منقولاً عن سجلّ
# تغييرات. ويعمل في الاتّجاهين: على httpx قديم يجب أن يُقبَل `app=`، وعلى
# جديد يجب أن يُرفض. أيّ انحراف يعني أن القاعدة تصف عالماً غير هذا.
try:
    import httpx as _hx
    _hv = getattr(_hx, '__version__', '0')
except Exception:                                           # noqa: BLE001
    _hx, _hv = None, None

if _hx is None:
    print('  NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: httpx is not '
          'importable here, so the mechanism cannot be executed.')
else:
    print('     installed httpx %s (the rule predicts `app=` is %s)'
          % (_hv, 'REJECTED' if ver(_hv) >= HTTPX_DROPPED_APP else 'accepted'))
    _rejected = None
    try:
        _hx.Client(app=(lambda *a, **k: None))
        _rejected = False
    except TypeError:
        _rejected = True
    except Exception:                                       # noqa: BLE001
        _rejected = None
    chk('httpx\'s real acceptance of `app=` matches what its version predicts '
        '— the 0.28.0 boundary is executed, not quoted',
        _rejected is not None
        and _rejected == (ver(_hv) >= HTTPX_DROPPED_APP),
        'httpx %s → app= rejected=%s' % (_hv, _rejected))

    try:
        import starlette as _st
        from starlette.applications import Starlette as _App
        from starlette.testclient import TestClient as _TC
        _sv = getattr(_st, '__version__', '0')
    except Exception:                                       # noqa: BLE001
        _st = None

    if _st is None:
        print('  starlette is not importable here — the TestClient half of '
              'the mechanism is NOT VERIFIED in this environment.')
    else:
        import inspect as _in
        _src = _in.getsource(_TC.__init__)
        _passes_app = bool(re.search(r'\bapp\s*=\s*self\.app\b', _src))
        chk('starlette %s passes `app=` to httpx.Client exactly when its '
            'version says it should (< 0.37.0)' % _sv,
            _passes_app == (ver(_sv) < STARLETTE_FIXED_AT),
            'starlette %s → passes app=%s' % (_sv, _passes_app))
        _built, _err = None, ''
        try:
            _TC(_App(), raise_server_exceptions=False)
            _built = True
        except Exception as _e:                             # noqa: BLE001
            _built, _err = False, '%s: %s' % (type(_e).__name__, _e)
        chk('constructing TestClient on the INSTALLED pair (starlette %s + '
            'httpx %s) succeeds exactly when the rule says it should'
            % (_sv, _hv),
            _built == compatible(_sv, _hv), _err or 'built=%s' % _built)

print('\n' + '─' * 62)
print('ASGI CLIENT CONTRACT: %d passed, %d failed' % (_p, _f))
sys.exit(1 if _f else 0)
