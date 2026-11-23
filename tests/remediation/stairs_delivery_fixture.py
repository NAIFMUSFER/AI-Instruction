"""Explicit synthetic stair fixtures; never a provider or walkability benchmark."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def base_model(edge='N', levels=None, two_cores=False):
    rooms = []
    for suffix, x in [('a', 0), ('b', 6)] if two_cores else [('a', 0)]:
        rooms.append({'id': 'stairs_' + suffix, 'name': 'درج ' + suffix,
                      'role': 'stairs', 'core_id': 'core_' + suffix, 'rect': [x, 0, 4, 4],
                      'doors': [{'id': 'entry_' + suffix, 'edge': edge, 'offset': 2,
                                 'width': 1, 'height': 2.1, 'material': 'wood'}],
                      'windows': [], 'points': [{'id': 'light_' + suffix, 'type': 'light', 'x': .4, 'z': .4}], 'objects': [],
                      'floor_color': '#c9c4b8', 'ceiling_color': '#f3f0e9'})
    return {'site': {'w': 10 if two_cores else 4, 'd': 4}, 'wall_h': 3,
            'wall_t': .2, 'floor_height': 3.2,
            'levels': copy.deepcopy(levels or [{'index': 0, 'template': 'shared', 'elevation': 0},
                                             {'index': 1, 'template': 'shared', 'elevation': 3.2}]),
            'floors': {'shared': {'rooms': rooms}}}


def canonical_fixture(**kwargs):
    from acs_stairs import with_default_stairs
    original = base_model(**kwargs)
    model, report, reason = with_default_stairs(original)
    assert reason is None and report['generated_connections'] > 0, (reason, report)
    assert report['physical_traversal'] == 'NOT_VERIFIED'
    return model


def approved_fixture(output):
    from acs_plan_lock_binding import PlanLockWorkspace
    from acs_plan_bridge import existing_geometry_verifier
    from tools.acs_plan_handoff import compile_approved_baseline, verify_compiled_artifact
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    model = canonical_fixture()
    workspace = PlanLockWorkspace(existing_geometry_verifier)
    rev = workspace.propose(model, brief='Synthetic two-level stair core with 32 m² total room area.',
                            requirements=[{'id': 'area', 'metric': 'building_target_area_m2',
                                           'expected': 32, 'source': 'requested', 'evidence': '32'}],
                            expected_head=None, note='Synthetic stairs QA; no provider call')
    review = workspace.review(rev.id)
    assert review['can_approve'], review
    workspace.approve(rev.id, expected_head=rev.id, actor_label='synthetic-stairs-test',
                      confirmed=True, acknowledge_concept_only=True)
    artifact = output / 'stairs.gltf'
    receipt = compile_approved_baseline(workspace, rev.id, artifact)
    assert verify_compiled_artifact(artifact)['ok']
    (output / 'stairs.canonical.json').write_text(json.dumps(model, ensure_ascii=False, indent=2))
    record = {'kind': 'stairs', 'revision': rev.id, 'model_hash': rev.model_hash,
              'gltf': artifact.name, 'receipt': receipt,
              'physical_traversal': 'NOT_VERIFIED',
              'scope': 'synthetic conceptual two-flight stair; no provider, guards, headroom or code claim'}
    (output / 'stairs-fixture.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


if __name__ == '__main__':
    print(json.dumps(approved_fixture(sys.argv[1]), ensure_ascii=False))
