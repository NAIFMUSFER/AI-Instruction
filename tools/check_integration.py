# -*- coding: utf-8 -*-
"""حارس التكامل — يمنع الشجرة نصف المدمَجة من المرور بصمت.

سبب وجوده حادثة حقيقية: وصلت شجرة فيها ملف اختبار جديد وملف بايثون قديم،
فانفجر الاختبار بـ AttributeError عميق (`acs_pbr has no attribute 'CLIP'`)،
وبقي مِرقاب الإقلاع القديم يطبع نجاحاً بينما نافذة العرض سوداء عند المستخدم.
العطل لم يكن في المنطق بل في أن الطبقات لم تكن من نفس الإصدار.

الحلّ: عقد واحد معلَن (viewport_contract_version) تُصرّح به كل طبقة —
مواصفة JSON، وحدة بايثون، مرآة المتصفّح المولَّدة، جسر الوحدة، والصفحة
المشحونة — ويُرفض أي اختلاف قبل البناء وقبل النشر وقبل التغليف.

    python3 tools/check_integration.py            # يفحص شجرة العمل
    python3 tools/check_integration.py <root>     # يفحص شجرة أخرى
"""
import io
import json
import os
import re
import sys

REQUIRED_PY_SYMBOLS = ('VB', 'CLIP', 'VIEWPORT_CONTRACT',
                       'VIEWPORT_CONTRACT_SYMBOLS', 'bounds_member',
                       'bounds_from_descriptors', 'camera_clip',
                       'frustum_contains', 'material_safe')
REQUIRED_JS_SYMBOLS = ('PQ_VB', 'PQ_CLIP', 'PQ_VIEWPORT_CONTRACT',
                       'pqBoundsMember', 'pqBoundsFromDescriptors',
                       'pqCameraClip', 'pqFrustumContains', 'pqMaterialSafe')
REQUIRED_BRIDGE_SYMBOLS = ('_pqDescribe', '_pqSceneBounds',
                           '_pqApplyCameraSafety',
                           'window.ACS.renderDiagnostics')
# الوسم القديم يُعرَف بجملة الطباعة نفسها لا بذكرها في تعليق شارح
LEGACY_HARNESS_PRINT = re.compile(r"""console\.log\(\s*['"]PAGE BOOT""")
HARNESS_VERSION_MARKER = 'HARNESS: verify_page_boot'


def _read(root, rel):
    with io.open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()


def check(root):
    """يعيد (الأعطال، الملخّص) — قائمة فارغة تعني شجرة متكاملة."""
    fails = []
    facts = {}

    def need(rel):
        if not os.path.isfile(os.path.join(root, rel)):
            fails.append('MISSING FILE: %s' % rel)
            return None
        return _read(root, rel)

    spec_raw = need('acs_pbr.json')
    py = need('acs_pbr.py')
    page = need(os.path.join('public', 'index.html'))
    bridge = need(os.path.join('tools', '_pbr_bridge_block.js'))
    injector = need(os.path.join('tools', 'build_pbr_browser.py'))
    test = need(os.path.join('tests', 'phase9_2', 'test_black_viewport.py'))
    harness = need(os.path.join('tests', 'deploy', 'verify_page_boot.js'))
    pixels = need(os.path.join('tests', 'deploy', 'lib_viewport_pixels.js'))
    if fails:
        return fails, facts

    # 1) المواصفة تعلن العقد
    try:
        spec = json.loads(spec_raw)
    except ValueError as e:
        return ['acs_pbr.json is not valid JSON: %s' % e], facts
    contract = spec.get('viewport_contract_version')
    facts['contract'] = contract
    if not contract:
        fails.append('acs_pbr.json does not declare viewport_contract_version')
    for k in ('viewport_bounds', 'camera_clip', 'viewport_contract_symbols'):
        if k not in spec:
            fails.append('acs_pbr.json lacks the %s contract block' % k)

    # 2) وحدة بايثون تعلن نفس العقد وتكشف كل رموزه
    for sym in REQUIRED_PY_SYMBOLS:
        pat = (r'^%s\s*=' % re.escape(sym)) if sym.isupper() \
            else (r'^def\s+%s\s*\(' % re.escape(sym))
        if not re.search(pat, py, re.M):
            fails.append('acs_pbr.py does not define %s — the Python layer is '
                         'older than the specification (this is the exact '
                         'partial-merge failure the gate exists to catch)'
                         % sym)
    if contract and ('SPEC["viewport_contract_version"]' not in py):
        fails.append('acs_pbr.py does not read the contract version from the '
                     'specification')

    # 3) المرآة المولَّدة في الصفحة المشحونة
    for sym in REQUIRED_JS_SYMBOLS:
        if sym not in page:
            fails.append('public/index.html lacks the browser mirror symbol '
                         '%s — regenerate with tools/build_pbr_browser.py'
                         % sym)
    for sym in REQUIRED_JS_SYMBOLS:
        if sym not in injector:
            fails.append('tools/build_pbr_browser.py does not emit %s' % sym)

    # 4) الجسر يستعمل المحكّم الواحد لا محكّماً ثانياً
    for sym in REQUIRED_BRIDGE_SYMBOLS:
        if sym not in bridge:
            fails.append('tools/_pbr_bridge_block.js lacks %s' % sym)
        if sym not in page:
            fails.append('public/index.html lacks the bridge symbol %s' % sym)
    if 'pqBoundsMember(_pqDescribe(o))' not in bridge:
        fails.append('the bridge does not route scene bounds through the '
                     'shared predicate')

    # 5) العقد نفسه مكتوب حرفياً في الصفحة المشحونة
    if contract and contract not in page:
        fails.append('the shipped page does not carry the contract version %s'
                     % contract)

    # 6) الاختبار والمِرقاب من نفس الجيل
    if 'P.CLIP' in test and 'CLIP' not in py:
        fails.append('tests/phase9_2/test_black_viewport.py expects P.CLIP '
                     'but acs_pbr.py does not provide it')
    if LEGACY_HARNESS_PRINT.search(harness):
        fails.append('tests/deploy/verify_page_boot.js is the LEGACY harness '
                     '(it prints "PAGE BOOT: N passed") — it cannot '
                     'distinguish a booted page from a visible model')
    if HARNESS_VERSION_MARKER not in harness:
        fails.append('tests/deploy/verify_page_boot.js does not announce its '
                     'harness version — a stale copy would be invisible in '
                     'the logs')
    for needle in ('VISUAL MODEL', 'analysePageViewport', 'setModel'):
        if needle not in harness:
            fails.append('verify_page_boot.js lacks %s' % needle)
    for needle in ('getImageData', 'near_black_pct', 'luminance_variance',
                   'non_background_pct'):
        if needle not in pixels:
            fails.append('lib_viewport_pixels.js lacks %s' % needle)

    # 7) الطبقتان تتفقان على العقد وقت التشغيل فعلاً
    sys.path.insert(0, root)
    for mod in ('acs_pbr',):
        if mod in sys.modules:
            del sys.modules[mod]
    try:
        import acs_pbr as P
        facts['python_contract'] = getattr(P, 'VIEWPORT_CONTRACT', None)
        if facts['python_contract'] != contract:
            fails.append('the imported Python layer declares %r but the '
                         'specification declares %r'
                         % (facts['python_contract'], contract))
        for sym in spec.get('viewport_contract_symbols', []):
            if not callable(getattr(P, sym, None)):
                fails.append('acs_pbr.%s is not callable at runtime' % sym)
    except Exception as e:                                  # noqa: BLE001
        fails.append('importing acs_pbr failed: %s' % e)
    return fails, facts


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    fails, facts = check(root)
    if fails:
        print('INTEGRATION GATE FAILED — this tree is only partially merged.')
        for x in fails:
            print('  ✗ %s' % x)
        print('\nEvery layer must come from the same delivery: acs_pbr.json, '
              'acs_pbr.py, tools/build_pbr_browser.py, '
              'tools/_pbr_bridge_block.js, the regenerated public/index.html, '
              'and the tests under tests/. Re-extract the full package and '
              'run: python3 tools/build_pbr_browser.py && '
              'python3 tools/build_archdetail_browser.py')
        sys.exit(1)
    print('✓ integration gate: every layer declares %s '
          '(spec, python, browser mirror, bridge, shipped page, tests)'
          % facts.get('contract'))


if __name__ == '__main__':
    main()
