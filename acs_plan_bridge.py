"""Opt-in adapters. Not registered on production routes in this foundation PR.

The hosting API must use its existing quota/body guards and isolated job runner.
No paid call may run on the request event loop. In particular, these functions
must NOT be called automatically merely because this module is imported.
"""
from __future__ import annotations
import json
from acs_plan_review import PlanError, PlanWorkspace, canonical, _number


def generate_candidate(description: str, *, model=None, btype=None,
                       request_id=None) -> dict:
    """Run the existing bounded PLAN stage only, never details or 3D assembly."""
    if not isinstance(description, str) or not description.strip():
        raise PlanError('DESCRIPTION_REQUIRED', 'An engineer brief is required')
    if len(description) > 60_000:
        raise PlanError('INPUT_LIMIT', 'Brief exceeds the existing 60k character ceiling')
    import acs_understand as U
    kind = U.detect_type(description, btype)
    stages = []
    building = U._plan_bounded(description, model=model, btype=kind,
                               stages=stages, request_id=request_id)
    # Keep ALL planner disclosures/unresolved-space flags; never repair or hide.
    building = json.loads(canonical(building))
    return {'building': building, 'stage': 'PLAN_DRAFT',
            'engineer_approved': False, 'detail_stage_run': False,
            'model_compiled': False, 'stages': stages}


def propose_chat_edit(workspace: PlanWorkspace, notes: list[dict], *,
                      expected_head: str, model=None,
                      semantic_lock_manifest: dict | None = None):
    """One paid edit proposal, not a replacement of an approved 3D model.

    Workspace room locks and optional stable semantic locks are enforced after
    the provider reply, before revision admission. A rejected lock violation is
    NOT retried or switched to another provider here. The semantic manifest is a
    headless foundation artifact; the future authenticated host must persist and
    bind it to the project/revision before exposing cross-device editing.
    """
    if expected_head != workspace.head:
        raise PlanError('STALE_REVISION', 'The reviewed plan has changed')
    if not isinstance(notes, list) or not notes or any(
            not isinstance(n, dict) or not isinstance(n.get('text'), str)
            or not n['text'].strip() for n in notes):
        raise PlanError('INVALID_EDIT', 'Explicit engineer notes are required')
    canonical(notes)
    before = workspace.get(expected_head)
    import acs_understand as U
    candidate = U.apply_notes(before.model, json.loads(canonical(notes)), model=model)
    if semantic_lock_manifest is not None:
        from acs_plan_semantic_locks import verify_lock_manifest
        verify_lock_manifest(before.model, candidate, semantic_lock_manifest)
    return workspace.propose(candidate, brief=before.brief,
        requirements=json.loads(before.requirements_json), expected_head=expected_head,
        note='\n'.join(n['text'] for n in notes))


def propose_bound_chat_edit(workspace, notes: list[dict], *,
                            expected_head: str, model=None):
    """Propose one chat edit against server-held revision-bound locks.

    This is the safer bridge for a host using ``PlanLockWorkspace``.  The caller
    supplies only the expected revision and engineer notes; it cannot substitute
    a detached semantic-lock manifest.  The exact manifest already bound to the
    head revision is loaded and verified by ``workspace.get`` and is enforced
    again by ``workspace.propose`` before immutable history is extended.

    The provider therefore proposes geometry, but the canonical workspace owns
    admission.  A successful edit is always a new draft revision.  Any earlier
    approved baseline remains frozen and no 3D/compiler path is invoked here.
    """
    from acs_plan_lock_binding import PlanLockWorkspace
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError('INVALID_WORKSPACE', 'Bound chat edits require PlanLockWorkspace')
    if expected_head != workspace.head:
        raise PlanError('STALE_REVISION', 'The reviewed plan has changed')
    if not isinstance(notes, list) or not notes or any(
            not isinstance(n, dict) or not isinstance(n.get('text'), str)
            or not n['text'].strip() for n in notes):
        raise PlanError('INVALID_EDIT', 'Explicit engineer notes are required')
    notes_json = canonical(notes)
    # get() validates the stored bound manifest before any provider work begins.
    before = workspace.get(expected_head)
    import acs_understand as U
    candidate = U.apply_notes(before.model, json.loads(notes_json), model=model)
    # PlanLockWorkspace.propose verifies inherited room/semantic locks before
    # admission, then rebinds the exact lock set to the new immutable revision.
    return workspace.propose(
        candidate, brief=before.brief,
        requirements=json.loads(before.requirements_json),
        expected_head=expected_head,
        note='\n'.join(n['text'] for n in notes))


def existing_geometry_verifier(building: dict) -> dict:
    """Conservative bridge to ACS's existing validator, not code certification.

    Explicit door arrays or open-space intent are required for each space.
    Multi-floor core checks additionally require explicit role/core_id and an
    identical core rectangle on every level. Missing intent stays NOT_VERIFIED.
    All existing validator findings block conceptual approval in this first pass;
    no substring-based filtering suppresses an inconvenient finding.
    """
    import acs_validate as V
    findings, _ = V.validate_building(building)
    floors, levels = building['floors'], building['levels']
    rooms = [r for f in floors.values() for r in f['rooms']]
    def openings_explicit(room):
        if room.get('walls') == 'none':
            return True
        if not isinstance(room.get('doors'), list) or not isinstance(room.get('windows'), list):
            return False
        return all(isinstance(o, dict) and all(_number(o.get(k)) and o[k] > 0 for k in ('w', 'h'))
                   and o.get('edge') in ('N', 'S', 'E', 'W') and _number(o.get('offset'))
                   for o in room['doors'] + room['windows'])
    topology_known = all(openings_explicit(r) for r in rooms)
    vertical_known = len(levels) == 1
    core_issue = False
    if len(levels) > 1:
        stacks = []
        for level in levels:
            cores = [r for r in floors[level['template']]['rooms']
                     if r.get('role') in ('stair', 'stairs', 'elevator')]
            ids = [r.get('core_id') for r in cores]
            if (not cores or any(not isinstance(i, str) or not i.strip() for i in ids)
                    or len(set(ids)) != len(ids)):
                stacks = []
                break
            stacks.append({r['core_id']: r['rect'] for r in cores})
        vertical_known = bool(stacks)
        core_issue = vertical_known and any(s != stacks[0] for s in stacks[1:])
    issues = [{'code': 'ACS_GEOMETRY_FINDING', 'message': str(x), 'severity': 'error'}
              for x in findings]
    if core_issue:
        issues.append({'code': 'VERTICAL_CORE_MISMATCH', 'severity': 'error'})
    return {'scopes': {
        'topology': ('FAIL' if findings else 'PASS') if topology_known else 'NOT_VERIFIED',
        'vertical_circulation': ('FAIL' if core_issue or findings else 'PASS') if vertical_known else 'NOT_VERIFIED'},
        'issues': issues}
