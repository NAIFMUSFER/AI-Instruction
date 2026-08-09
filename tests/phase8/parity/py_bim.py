# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 8.

حدّ معلَن لا يُموّه: تحليل STEP وتسلسله يعملان في بايثون وحدها
(BX_STEP_PARSER_IN_BROWSER = false). فما يقارَن هنا هو الطبقة المشتركة التي
تعمل في اللغتين: بناء نموذج التبادل، والتحقّق، ووصف التصدير، والفرق،
والتضاربات، والمقترحات، والقِدَم، والأمر المولَّد، والإيداع عبر مسار التأليف.
لذلك يكتب هذا الملفّ التمثيل المرحلي المشترك إلى ملفّ يقرأه جانب جافاسكربت،
فيبدأ الطرفان من المدخل نفسه بالضبط.
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

import acs_bim as B                                               # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_bim_fixtures as LIB                                    # noqa: E402

OUT = os.environ.get('ACS_PARITY_BIM_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_bim_py.json')
STAGING_OUT = os.environ.get('ACS_PARITY_BIM_STAGING') or os.path.join(
    PHASE, 'fixtures', 'staging_parity.json')
AT = '2026-01-01T00:00:00Z'

ALL = LIB.models()
MODEL_KEYS = sorted(ALL.keys())

out = {}
staging_share = {}
for key in MODEL_KEYS:
    model = copy.deepcopy(ALL[key])
    before = json.dumps(model, sort_keys=True, ensure_ascii=False)
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    h0 = project['model_hash']

    entry = {'model_hash': h0}
    built = B.build_exchange(project, {})
    entry['exchange_valid'] = built['valid']
    entry['exchange'] = built['exchange'] if built['valid'] else None
    entry['exchange_issues'] = [i['code'] for i in built['issues']]
    if not built['valid']:
        out[key] = entry
        continue
    ex = built['exchange']
    entry['validation'] = B.validate_exchange(ex)

    exp = B.export_ifc(project, {}, None)
    entry['export_valid'] = exp['valid']
    # وصف التصدير في المتصفّح لا يحمل بصمة الملفّ لأنه لا يسلسل؛ نقارن الحقول
    # المشتركة وحدها ونصرّح بذلك
    man = dict(exp['manifest'])
    entry['manifest_shared'] = {k: man[k] for k in sorted(man)
                                if k not in ('file_hash', 'body_hash',
                                             'entity_count')}
    entry['manifest_serialised_only'] = {
        'file_hash': man['file_hash'], 'body_hash': man['body_hash'],
        'entity_count': man['entity_count']}

    st = B.stage_import(exp['file'], key + '.ifc', {}, 'imp_fixed', AT)
    entry['staging_valid'] = st['valid']
    staging_share[key] = st['staging']
    entry['staging_counts'] = st['staging']['counts'] if st['staging'] else None

    d = B.import_diff(project, st['staging'], {})
    entry['diff'] = d['diff']
    entry['conflicts'] = B._conflicts(project, st['staging'], ex)
    ps = B.import_proposals(d['diff'], st['staging'])
    entry['proposals'] = ps
    entry['staleness_current'] = B.import_staleness(ps, project)
    moved = copy.deepcopy(project)
    moved['model_hash'] = 'moved'
    moved['current_revision'] = 'rev:moved'
    entry['staleness_moved'] = B.import_staleness(ps, moved)
    entry['export_staleness_current'] = B.export_staleness(man, project)
    entry['export_staleness_moved'] = B.export_staleness(man, moved)
    entry['commands'] = [B._command_for(p) for p in ps['proposals']]
    entry['commit_nothing_accepted'] = {
        k2: v2 for k2, v2 in B.commit_import(project, ps, AU, AT).items()
        if k2 in ('valid', 'committed', 'state', 'note')}
    entry['guids'] = {s: B.ifc_guid(s) for s in
                      ('space:' + key, 'wall:' + key, 'door:' + key,
                       'level:' + key, 'مجلس', "O'Brien")}
    entry['model_untouched'] = (project['model_hash'] == h0
                                and json.dumps(model, sort_keys=True,
                                               ensure_ascii=False) == before)
    out[key] = entry

# حالة إيداع حقيقية: نموذج معدَّل يُصدَّر ثم يُستورَد على النموذج الأصلي
renamed = copy.deepcopy(ALL['villa_glazed'])
renamed['floors']['g']['rooms'][0]['name'] = 'majlis_renamed'
prj2 = AU.create_project(copy.deepcopy(renamed), 'bld_0', 'IMPORT', None)
alt = B.export_ifc(prj2, {}, None)
base = AU.create_project(copy.deepcopy(ALL['villa_glazed']), 'bld_0', 'IMPORT', None)
sta = B.stage_import(alt['file'], 'alt.ifc', {}, 'imp_alt', AT)
staging_share['__alt'] = sta['staging']
d2 = B.import_diff(base, sta['staging'], {})
ps2 = B.import_proposals(d2['diff'], sta['staging'])
name_props = [p for p in ps2['proposals']
              if p['change_type'] == 'PROPERTY_CHANGED' and p['field'] == 'name']
acc = B.set_proposal_state(ps2, name_props[0]['proposal_id'], 'ACCEPTED') \
    if name_props else None
com = B.commit_import(base, acc['proposals'], AU, AT) if acc else None
out['__commit'] = {
    'diff': d2['diff'], 'proposals': ps2,
    'name_proposal_count': len(name_props),
    'accepted': acc,
    'command': B._command_for(name_props[0]) if name_props else None,
    'commit': None if not com else {
        k: com[k] for k in ('valid', 'committed', 'state', 'via',
                            'previous_model_hash', 'new_model_hash',
                            'previous_revision', 'new_revision',
                            'changed_objects', 'commands')},
    'base_untouched': base['model_hash'] == out['villa_glazed']['model_hash'],
}

out['__spec'] = {
    'schema': B.SPEC['schema'], 'version': B.SPEC['version'],
    'invariant': {k: B.SPEC[k] for k in
                  ('external_bim_is_model_truth', 'direct_import_write_allowed',
                   'requires_explicit_commit', 'writes_via_authoring_path')},
    'command_source': B.SPEC['import_command_source'],
    'command_map': B.SPEC['import_command_map'],
    'limits': B.SPEC['limits'], 'tolerances': B.SPEC['tolerances'],
}
# أزواج لا كائنات: النصّ المفحوص لا يصير مفتاح كائن حتى في ملفّ تكافؤ
out['__safety'] = {
    'unsafe': [[p, B.is_unsafe(p)] for p in
               ['<script>x</script>', 'javascript:a', 'JavaScript:A', '../x',
                'data:text/html,x', '<!ENTITY e>', 'file:///etc/passwd',
                'vbscript:x', 'plain name', 'مجلس', "O'Brien Room",
                '__proto__', 'constructor', '{{7*7}}']],
    'safe_key': [[k, B.safe_key(k)] for k in
                 ['LoadBearing', 'IsExternal', '__proto__', 'constructor',
                  'prototype', '__defineGetter__', 'a b', '', 'x' * 300]],
    'safe_id': [[k, B.is_safe_id(k)] for k in
                ['bld_0.flr_0.g.r1', 'a-b_c:d@e$f', 'has space', 'مجلس', '']],
}
out['__units'] = {u: B.LENGTH_UNITS[u] for u in sorted(B.LENGTH_UNITS)}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
os.makedirs(os.path.dirname(STAGING_OUT), exist_ok=True)
with open(STAGING_OUT, 'w', encoding='utf-8') as f:
    json.dump(staging_share, f, ensure_ascii=False, sort_keys=True)
print('parity written: %d models, staging shared for %d'
      % (len(MODEL_KEYS), len(staging_share)))
