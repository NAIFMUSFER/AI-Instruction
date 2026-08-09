# -*- coding: utf-8 -*-
"""يولّد تجهيزات المرحلة 8 التي يحتاجها المتصفّح.

المتصفّح لا يحلّل STEP (BX_STEP_PARSER_IN_BROWSER = false)، فالتمثيل المرحلي
يُولَّد هنا من ملفّات IFC حقيقية ثم يُقرأ في الصفحة. لا يُختلق تمثيل مرحلي
يدوياً: كل ما يُكتب هنا خرج من المسلسِل ثم من المحلّل فعلاً.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_bim as B                                               # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_bim_fixtures as LIB                                    # noqa: E402

FIX = os.path.join(HERE, 'fixtures')
AT = '2026-01-01T00:00:00Z'
os.makedirs(FIX, exist_ok=True)

ALL = LIB.models()

# ------------------------------------------------------------------ مشترك --
shared = {}
for key in sorted(ALL):
    prj = AU.create_project(copy.deepcopy(ALL[key]), 'bld_0', 'IMPORT', None)
    exp = B.export_ifc(prj, {}, None)
    if not exp['valid']:
        raise SystemExit('fixture export failed for %s' % key)
    st = B.stage_import(exp['file'], key + '.ifc', {}, 'imp_fixed', AT)
    shared[key] = st['staging']

renamed = copy.deepcopy(ALL['villa_glazed'])
renamed['floors']['g']['rooms'][0]['name'] = 'majlis_renamed'
prj2 = AU.create_project(copy.deepcopy(renamed), 'bld_0', 'IMPORT', None)
alt = B.export_ifc(prj2, {}, None)
shared['__alt'] = B.stage_import(alt['file'], 'alt.ifc', {}, 'imp_alt', AT)['staging']

with open(os.path.join(FIX, 'staging_parity.json'), 'w', encoding='utf-8') as f:
    json.dump(shared, f, ensure_ascii=False, sort_keys=True)

# ------------------------------------------------------ حمولات معادية حقّاً --
# ملفّ IFC مصطنع يحمل نصوصاً معادية في حقول نصّية فقط. الصنف التنفيذي يُرفض في
# التمرحل، والصنف الخامل يمرّ نصّاً — والصفحة يجب أن تكتبه نصّاً لا وسماً.
HOSTILE = ["<scr" + "ipt>window.__PWNED__=1</scr" + "ipt>",
           '<img src=x onerror="window.__PWNED__=1">',
           'javascript:window.__PWNED__=1',
           '../../etc/passwd',
           '__proto__', 'constructor', 'prototype', '{{7*7}}',
           # وسم غير مدرَج في أنماط الرفض عمداً: يمرّ نصّاً، وعلى الصفحة أن
           # تكتبه نصّاً مهرَّباً لا عنصراً — وهذا إثبات موجب للتهريب
           '<b>bold</b>', 'a "quoted" & <tag>',
           "O'Brien Room", 'مجلس', 'Café – 100%']
body = ''
n = 100
for i, s in enumerate(HOSTILE):
    esc = s.replace('\\', '\\\\').replace("'", "''")
    body += '#%d=IFCLOCALPLACEMENT(#14,#7);\n' % (n + i * 2)
    body += ("#%d=IFCSPACE('0aaaaaaaaaaaaaaaaaaH%02d',$,'%s',$,$,#%d,$,'1',"
             ".ELEMENT.,.INTERNAL.,0.);\n" % (n + i * 2 + 1, i, esc, n + i * 2))
hostile_text = LIB.minimal(None, body)
hs = B.stage_import(hostile_text, 'hostile.ifc', {}, 'imp_hostile', AT)
with open(os.path.join(FIX, 'staging_hostile.json'), 'w', encoding='utf-8') as f:
    json.dump({'staging': hs['staging'], 'valid': hs['valid'],
               'issues': hs['issues'], 'payloads': HOSTILE},
              f, ensure_ascii=False, sort_keys=True)

# ----------------------------------------------------- تقرير ذهاب وإياب حقّ --
prj = AU.create_project(copy.deepcopy(ALL['villa_glazed']), 'bld_0', 'IMPORT', None)
rt = B.roundtrip_report(prj, shared['villa_glazed'], {})
with open(os.path.join(FIX, 'roundtrip_report.json'), 'w', encoding='utf-8') as f:
    json.dump(rt, f, ensure_ascii=False, sort_keys=True)

print('phase 8 fixtures: %d staged models, %d hostile labels, roundtrip %s'
      % (len(shared), len(HOSTILE), (rt.get('report') or {}).get('status')))
