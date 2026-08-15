# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 6.

يبني نماذج العرض نفسها (الشجرة، الفاحص، مركز الملاحظات، التغطية، التصدير،
المساعد، المراجع) على نفس التجهيزات، ويكتب النتيجة القانونية إلى JSON
يقارنه compare.js. لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس.
"""
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
sys.path.insert(0, PHASE)

import acs_authoring as AU                                       # noqa: E402
import acs_workspace as W                                        # noqa: E402
import acs_arch as ARCH                                          # noqa: E402
import acs_coord as COORD                                        # noqa: E402
import acs_visual as VIS                                         # noqa: E402
import acs_runtime as RT                                         # noqa: E402
import lib_workspace_fixtures as LIB                             # noqa: E402

OUT = os.environ.get('ACS_PARITY_WORKSPACE_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_workspace_py.json')
AT = '2026-01-01T00:00:00Z'

FX = LIB.models()
MEPF = LIB.mep()
ALL = {}
ALL.update(FX)
for k, v in MEPF.items():
    ALL['mep_' + k] = v

MODEL_KEYS = sorted(ALL.keys())
LANGS = ['en', 'ar']
TARGETS = ['g.majlis', 'bld_0.g.majlis.door_0', 'g.corridor.obj_0', 'site',
           'building', 'g', 'bld_0.flr_0.wall_0', 'nope', '', 'runtime:obj:x',
           'obstacle:x']


def compiled(model, bid):
    arch = coord = vis = rt = None
    try:
        arch = ARCH.compile_architecture(copy.deepcopy(model), bid, None, 0)
    except Exception:
        arch = None
    try:
        coord = COORD.compile_coordination(copy.deepcopy(model), bid, None, 0)
    except Exception:
        coord = None
    try:
        vis = VIS.compile_visual_scene(copy.deepcopy(model), bid, None, 0,
                                       {'mode': 'ENGINEERING'})
        rt = RT.compile_runtime_scene(vis, None)
    except Exception:
        vis = None
        rt = None
    return arch, coord, vis, rt


out = {}
for key in MODEL_KEYS:
    model = copy.deepcopy(ALL[key])
    before = json.dumps(model, sort_keys=True)
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    arch, coord, vis, rt = compiled(model, 'bld_0')

    entry = {'model_hash_of': W.model_hash_of(project)}
    for lang in LANGS:
        tree = W.project_tree(project, arch, coord, lang)
        entry['tree_' + lang] = tree
        entry['flat_' + lang] = W.flatten_tree(
            tree, [n['node_id'] for n in [tree['root']]] +
            ['site', 'bld_0', 'bld_0.flr_0', 'bld_0.flr_0.spaces'], None, None)
        entry['insp_' + lang] = {
            t: W.inspector_model(project, t, arch, vis, coord, lang)
            for t in TARGETS}
    entry['issues'] = W.issue_center(project, arch, coord, rt, None, 'bld_0')
    entry['issue_targets'] = [W.issue_targets(i) for cat in
                              sorted(entry['issues']['categories'].keys())
                              for i in entry['issues']['categories'][cat]]
    entry['summary'] = W.workspace_summary(project, W.ui_state_default(),
                                           entry['tree_en'], entry['issues'])
    entry['exports'] = {k: W.export_descriptor(project, k, 'COMMITTED', None, AT)
                        for k in W.SPEC['export_kinds']}
    if json.dumps(model, sort_keys=True) != before:
        raise SystemExit('a workspace view model mutated the engineering model: ' + key)
    if W.model_hash_of(project) != entry['model_hash_of']:
        raise SystemExit('the project hash changed while building views: ' + key)
    out[key] = entry

# ---- العمليات المتاحة لكل نوع عقدة، مقفولاً وغير مقفول
out['__operations__'] = {
    kind + ('|locked' if locked else '|open'): W.available_operations(kind, locked)
    for kind in W.SPEC['tree_node_kinds'] for locked in (False, True)}

# ---- عرض القيم المجهولة والمشتقّة والتحويلات
# ترقيم القيم بدل تمثيلها النصّي: repr في بايثون يميّز 0 عن 0.0 بينما
# جافاسكربت لا تفعل، وهو فرق في صياغة مفتاح الاختبار لا في السلوك المقارَن
VALUES = [None, 0, 1, 2.5, -3.25, 1e21, 'text', '', True, False]
CONVERT_VALUES = [0, 1, 2.5, -3.25, 1234.5678, None]
disp = {}
for lang in LANGS:
    for editability in W.SPEC['editability_classes']:
        for i, value in enumerate(VALUES):
            disp['%s|%s|%d' % (lang, editability, i)] = W.display_value(
                value, editability, lang)
out['__display__'] = disp
out['__convert__'] = {'%s|%d' % (u, i): W.convert_display(v, u)
                      for u in W.SPEC['display_units']
                      for i, v in enumerate(CONVERT_VALUES)}
# label() نطاقها تسميات المصدر لا نصوص الواجهة؛ تُفحَص على نطاقها الحقيقي
out['__labels__'] = {'%s|%s' % (lang, k): W.label(k, lang)
                     for lang in LANGS
                     for k in sorted(list(W.SPEC['provenance_labels'].keys()) +
                                     ['not_a_label_key', ''])}
# نصوص الواجهة تُقرأ من المواصفة في التطبيقين — لا جدول خاصّ في أيّهما
out['__ui_labels__'] = {'%s|%s' % (lang, k): W.SPEC['ui_labels'][k][lang]
                        for lang in LANGS
                        for k in sorted(W.SPEC['ui_labels'].keys())}
out['__provenance__'] = {'%s|%s' % (lang, src): W.resolve_provenance_label(src, lang)
                         for lang in LANGS
                         for src in sorted(W.SPEC['provenance_labels'].keys()) +
                         ['NOT_A_REAL_SOURCE', '', 'CODE_COMPLIANT']}

# ---- تغطية المتطلّبات
cov = {}
for lang in LANGS:
    cov[lang + '|null'] = W.requirement_coverage(None, lang)
    cov[lang + '|empty'] = W.requirement_coverage({}, lang)
    cov[lang + '|real'] = W.requirement_coverage(
        {'requirements': [
            {'id': 'r1', 'text': 'ثلاث غرف نوم', 'klass': 'SPATIAL'},
            {'id': 'r2', 'text': 'مصعد', 'klass': 'UNSUPPORTED'},
            {'id': 'r3', 'text': 'مطبخ 12 متر', 'klass': 'DIMENSIONAL',
             'satisfied_by': ['g.kitchen']}]}, lang)
out['__coverage__'] = cov

# ---- حدود الحالة
out['__state__'] = {
    'classify': {k: W.classify_state_key(k) for k in
                 sorted(list(W.SPEC['state_ownership'].keys()) +
                        ['not_a_key', '', 'model', 'ui_mode'])},
    'ui_default': W.ui_state_default()}

# ---- المراجع البصرية والنيّة، بما فيها المدخلات الخبيثة
ctx = W.presentation_context(None)
refs = {}
cases = [
    ('ok', 'STYLE', 'PROJECT', None, 'https://example.invalid/a.png', 'مرجع'),
    ('ok_space', 'MATERIAL', 'SPACE', 'g.majlis',
     'https://example.invalid/b.png', 'رخام'),
    ('script_uri', 'STYLE', 'PROJECT', None, 'javascript:alert(1)', 'x'),
    ('markup_caption', 'STYLE', 'PROJECT', None, 'https://example.invalid/a.png',
     '<img src=x onerror=alert(1)>'),
    ('data_html', 'STYLE', 'PROJECT', None, 'data:text/html,<script>x</script>', 'x'),
    ('svg_caption', 'LIGHTING', 'PROJECT', None, 'https://example.invalid/a.png',
     '<svg onload=alert(1)>'),
    ('bad_kind', 'NOT_A_KIND', 'PROJECT', None, 'https://example.invalid/a.png', 'x'),
    ('bad_scope', 'STYLE', 'NOT_A_SCOPE', None, 'https://example.invalid/a.png', 'x'),
    ('empty_uri', 'STYLE', 'PROJECT', None, '', 'x'),
    ('none_uri', 'STYLE', 'PROJECT', None, None, 'x'),
]
for name, kind, scope, sid, uri, cap in cases:
    r = W.attach_reference(ctx, kind, scope, sid, uri, 'user', cap)
    refs[name] = {'valid': r['valid'], 'issues': r.get('issues'),
                  'count': len((r.get('context') or ctx).get('references') or [])}
out['__references__'] = refs
INTENT_VALUES = ['warm', '', '<script>x</script>']
out['__intent__'] = {
    '%s|%d' % (f, i): (lambda r: {'valid': r['valid'], 'issues': r.get('issues')})(
        W.set_visual_intent(W.presentation_context(None), f, v))
    for f in list(W.SPEC['visual_intent_fields']) + ['not_a_field']
    for i, v in enumerate(INTENT_VALUES)}

# ---- المساعد: ادّعاءات ومقترحات، بلا إيداع تلقائي
out['__assistant__'] = {
    'claims': {'%s|%s' % (k, t[:12]): W.assistant_claim(k, t, None)
               for k in list(W.SPEC['assistant_claim_classes']) + ['NOT_A_CLASS']
               for t in ['this is compliant with code', 'the room is 5 m wide', '']},
}
proj = AU.create_project(copy.deepcopy(FX['villa']), 'bld_0', 'IMPORT', None)
out['__assistant__']['propose'] = W.assistant_propose_edit(
    proj, 'اجعل المجلس أوسع',
    {'type': 'RESIZE_SPACE', 'target_id': 'g.majlis',
     'parameters': {'w': 6, 'd': 4}}, 'because the user asked')
out['__assistant__']['propose_unknown'] = W.assistant_propose_edit(
    proj, 'nothing matches this', None, None)

# ---- عزل حالة الواجهة عن النموذج
ui = W.ui_state_default()
ui['selected_id'] = 'g.majlis'
ui['ui_mode'] = 'EDIT'
out['__ui_boundary__'] = W.assert_ui_state_excluded(proj, ui)

out['__spec__'] = {'schema': W.SCHEMA, 'version': W.SPEC['version']}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
print('python workspace parity written: %s (%d keys)' % (OUT, len(out)))
