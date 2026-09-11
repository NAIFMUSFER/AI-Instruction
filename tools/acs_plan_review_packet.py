"""Offline read-only view packets derived from the existing canonical workspace.

This does not approve a plan, authenticate an actor, generate a model, or create
production routes. An exported hash detects corruption, not a forged issuer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from acs_plan_review import PlanError
from acs_plan_projection import project
from acs_plan_scorecard import measure_plan

FILE_SCHEMA = 'acs.plan-review-file/1.0'
VIEW_SCHEMA = 'acs.plan-review-view/1.0'
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
REQUIREMENT_FIELDS = ('id', 'source', 'source_id', 'source_span', 'metric',
                      'expected', 'role', 'edge', 'kind', 'room', 'template', 'confirmed')


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def build_review_packet(workspace, revision_id: str) -> dict:
    """Project an exact revision; never use an unbound current-model variable.

    Only presentation metadata is exported. The canonical Building stays in the
    workspace, and raw brief/evidence/notes/actor names are not copied here.
    """
    rev = workspace.get(revision_id)
    receipt = getattr(rev, 'bound_content_hash', rev.content_hash)
    report = workspace.review(revision_id)
    if (report.get('revision_id') != rev.id or report.get('model_hash') != rev.model_hash
            or report.get('content_hash') != rev.content_hash):
        raise PlanError('REVIEW_REVISION_CHANGED', 'Review does not match the selected revision')
    projections = [project(rev, level['index']) for level in rev.model['levels']]
    manifest = getattr(rev, 'semantic_lock_manifest', None)
    selectors = [] if manifest is None else [r['selector'] for r in manifest['locks']]
    payload = {
        'schema': VIEW_SCHEMA, 'read_only': True,
        'revision': {'id': rev.id, 'version': rev.number,
                     'model_hash': rev.model_hash, 'content_hash': rev.content_hash},
        'review': {
            'revision_id': rev.id, 'model_hash': rev.model_hash,
            'content_hash': rev.content_hash, 'scopes': report['scopes'],
            'issues': [{k: item[k] for k in ('code', 'severity', 'requirement_id') if k in item}
                       for item in report['issues']],
            # Deliberately no can_approve, approval state, or authority token.
        },
        'scorecard': measure_plan(rev.model),
        'requirements': [{k: r[k] for k in REQUIREMENT_FIELDS if k in r}
                         for r in json.loads(rev.requirements_json)],
        'locks': {'rooms': [list(r) for r in rev.locked_rooms], 'semantic': selectors},
        'projections': projections,
    }
    now = workspace.get(revision_id)
    if getattr(now, 'bound_content_hash', now.content_hash) != receipt:
        raise PlanError('REVIEW_REVISION_CHANGED', 'Selected revision changed during projection')
    raw = _json(payload)
    if len(raw.encode('utf-8')) > MAX_PAYLOAD_BYTES:
        raise PlanError('REVIEW_VIEW_LIMIT', 'View packet exceeds its presentation budget')
    packet = {'schema': FILE_SCHEMA, 'payload_json': raw,
              'payload_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest()}
    if len(_json(packet).encode('utf-8')) > MAX_FILE_BYTES:
        raise PlanError('REVIEW_VIEW_LIMIT', 'Encoded view packet is too large')
    return packet


def write_review_packet(workspace, revision_id: str, destination: Path) -> None:
    packet = build_review_packet(workspace, revision_id)
    # Never silently replace a previously exported review file.
    with Path(destination).open('x', encoding='utf-8') as stream:
        stream.write(_json(packet))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Export a draft ACS 2D review packet; never approve or generate.')
    parser.add_argument('input', type=Path, help='JSON with building, brief and requirements')
    parser.add_argument('output', type=Path, help='New .acs-review.json file')
    args = parser.parse_args(argv)
    from acs_plan_review import MAX_BYTES
    from acs_plan_lock_binding import PlanLockWorkspace
    from acs_plan_bridge import existing_geometry_verifier
    with args.input.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise PlanError('INPUT_LIMIT', 'Input exceeds the canonical input ceiling')
    data = json.loads(raw)
    ws = PlanLockWorkspace(verifier=existing_geometry_verifier)
    rev = ws.propose(data['building'], brief=data['brief'], requirements=data['requirements'],
                     expected_head=None, note='Explicit offline draft review export')
    write_review_packet(ws, rev.id, args.output)
    print('Read-only draft packet exported. No approval, generation, upload or cloud save occurred.')


if __name__ == '__main__':
    main()
