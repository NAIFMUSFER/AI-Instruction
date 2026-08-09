# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 5.

يشغّل نفس السيناريوهات والحالات الخصومية على نفس ملفّ التجهيزات، ويكتب النتيجة
القانونية إلى ملفّ JSON يقارنه compare.js. لا يُسمح بـ Python PASS / JS FAIL.
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

import acs_authoring as A                                    # noqa: E402
import lib_authoring_fixtures as LIB                          # noqa: E402

OUT = os.environ.get('ACS_PARITY_AUTHORING_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_authoring_py.json')
SC = LIB.load()
AT = '2026-01-01T00:00:00Z'

out = {}
for name, model_key, raw_cmd in SC['scenarios']:
    model = copy.deepcopy(SC['models'][model_key])
    before = json.dumps(model, sort_keys=True)
    cmd = LIB.hydrate(raw_cmd)
    project = A.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)

    norm = A.normalise_command(copy.deepcopy(cmd), None,
                               cmd.get('snap') if isinstance(cmd, dict) else None,
                               cmd.get('grid_m') if isinstance(cmd, dict) else None)
    preview = A.preview_command(model, copy.deepcopy(cmd), None, 'bld_0',
                                cmd.get('snap') if isinstance(cmd, dict) else None,
                                cmd.get('grid_m') if isinstance(cmd, dict) else None)
    impact = A.dependency_impact(copy.deepcopy(cmd), model, 'bld_0')
    txn = A.validate_transaction(project, [copy.deepcopy(cmd)], 'bld_0')
    commit = A.commit_transaction(project, [copy.deepcopy(cmd)],
                                  confirm=(txn.get('transaction') or {})
                                  .get('confirmation_digest'),
                                  acknowledge_warnings=True,
                                  created_at=AT)
    if json.dumps(model, sort_keys=True) != before:
        raise SystemExit('the authoring engine mutated the model: ' + name)
    if A.model_hash(project['model'], 'building', 'bld_0') != project['model_hash']:
        raise SystemExit('the project model changed in place: ' + name)

    entry = {
        'normalised': norm,
        'command_hash': A.command_hash(copy.deepcopy(cmd)),
        'preview': preview,
        'impact': impact,
        'transaction': txn,
        'committed': commit['valid'] and commit.get('committed'),
        'commit_state': commit.get('state'),
        'commit_issues': commit['issues'],
        'commit_revision': commit.get('revision'),
        'commit_model_hash': commit.get('model_hash'),
        'stale_artifacts': commit.get('stale_artifacts'),
        'audit': commit.get('audit'),
        'base_model_hash': project['model_hash'],
        'base_revision': project['current_revision'],
    }
    if commit.get('committed'):
        np = commit['project']
        entry['history'] = np['history']
        entry['summary'] = A.summary(np)
        entry['diff'] = A.revision_diff(project['model'], np['model'])
        entry['serialised'] = A.serialise_project(np, True, False)
        u = A.undo(np, None, AT, 'bld_0')
        entry['undo_state'] = u.get('state')
        entry['undo_hash'] = u.get('model_hash')
        entry['undo_revision'] = u.get('revision')
        if u.get('project'):
            r = A.redo(u['project'], None, AT, 'bld_0')
            entry['redo_state'] = r.get('state')
            entry['redo_hash'] = r.get('model_hash')
    out[name] = entry

adv = {}
for key, raw in SC['adversarial']:
    cmd = LIB.hydrate(raw)
    model = copy.deepcopy(SC['models']['villa'])
    project = A.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    n = A.normalise_command(copy.deepcopy(cmd))
    p = A.preview_command(model, copy.deepcopy(cmd), None, 'bld_0')
    t = A.validate_transaction(project, [copy.deepcopy(cmd)], 'bld_0')
    c = A.commit_transaction(project, [copy.deepcopy(cmd)], confirm='x',
                             acknowledge_warnings=True)
    adv[key] = {'normalise_valid': n['valid'],
                'normalise_codes': [i['code'] for i in n['issues']],
                'preview_valid': p['valid'],
                'preview_codes': [i['code'] for i in p['issues']],
                'preview_state': p.get('state'),
                'transaction_state': t.get('state'),
                'transaction_codes': [i['code'] for i in t['issues']],
                'committed': c.get('committed'),
                'commit_codes': [i['code'] for i in c['issues']],
                'model_unchanged': A.model_hash(project['model'], 'building', 'bld_0')
                == project['model_hash']}
out['__adversarial__'] = adv

targets = ['g.majlis', 'bld_0.g.majlis.door_0', 'g.corridor.obj_0', 'site', 'building',
           'g', 'bld_0.flr_0.wall_0', 'nope', '', 'runtime:obj:x', 'obstacle:x']
model = copy.deepcopy(SC['models']['villa'])
out['__ops__'] = {
    'spec_schema': A.SCHEMA,
    'command_types': list(A.COMMAND_TYPES),
    'issue_codes': list(A.ISSUE_CODES),
    'resolve': {t: A.resolve_target(model, t, 'bld_0') for t in targets},
    'properties': {t: A.editable_properties(model, t, 'bld_0') for t in targets},
    'integrity': A.validate_model_integrity(model, 'bld_0'),
    'nl': {phrase: A.resolve_nl_target(model, phrase, 'bld_0')
           for phrase in ['majlis', 'corridor', 'nothing here', '', 'kitchen']},
    'nl_dup': {phrase: A.resolve_nl_target(
        copy.deepcopy(SC['models']['dup_ids']), phrase, 'bld_0')
        for phrase in ['corridor', 'a', 'b']},
    'proposal': A.propose_command(
        {'type': 'MOVE_WALL', 'target_id': 'bld_0.flr_0.wall_0',
         'parameters': {'delta_m': 0.5}}, 'because the user asked', None),
    'hashes': {n: A.command_hash({'type': 'RENAME_SPACE', 'target_id': 'g.majlis',
                                  'parameters': {'name': n}})
               for n in ['a', 'b', 'مجلس']},
    'load_roundtrip': (lambda p: {
        'hash': p['model_hash'], 'revision': p['current_revision'],
        'valid': True})(A.load_project(A.serialise_project(
            A.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None),
            True, True), 'bld_0')['project']),
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
print('python authoring parity written: %s (%d keys)' % (OUT, len(out)))
