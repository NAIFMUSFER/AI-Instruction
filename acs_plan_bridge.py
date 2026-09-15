"""Opt-in adapters. Not registered on production routes in this foundation PR.

The hosting API must use its existing quota/body guards and isolated job runner.
No paid call may run on the request event loop. In particular, these functions
must NOT be called automatically merely because this module is imported.
"""
from __future__ import annotations
import json
from acs_plan_review import PlanError, PlanWorkspace, canonical, _number


# These top-level Building fields describe facts/authority that ACS derives or
# records outside the model-proposal provider. A provider may preserve an
# already-present legacy value byte-for-byte, but it must never introduce,
# delete, or alter one while proposing geometry. Review/scorecard code remains
# the authority for measured metrics; approval/baseline authority remains in the
# authenticated canonical workspace.
_SERVER_DERIVED_BUILDING_FIELDS = frozenset({
    'scorecard', 'metrics', 'validation', 'review',
    'regulatory_compliance', 'structural_safety',
    'construction_approved', 'engineer_approved',
    'approval', 'approval_receipt', 'baseline', 'authority',
})


def _reject_provider_authority_changes(before: dict, candidate: dict) -> None:
    """Fail closed if provider output changes server-derived Building authority."""
    before_meta = before.get('meta') if isinstance(before.get('meta'), dict) else {}
    after_meta = candidate.get('meta') if isinstance(candidate.get('meta'), dict) else {}
    if canonical(before_meta.get('acs_plan_source')) != canonical(after_meta.get('acs_plan_source')):
        raise PlanError('PROVIDER_AUTHORITY_FIELD', 'Provider changed the stored plan-source receipt')
    for key in _SERVER_DERIVED_BUILDING_FIELDS:
        before_has = key in before
        candidate_has = key in candidate
        if before_has != candidate_has:
            raise PlanError(
                'PROVIDER_AUTHORITY_FIELD',
                'Provider candidate changed a server-derived review/approval field',
            )
        if before_has and canonical(before[key]) != canonical(candidate[key]):
            raise PlanError(
                'PROVIDER_AUTHORITY_FIELD',
                'Provider candidate changed a server-derived review/approval field',
            )


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


def _bound_chat_edit_context(workspace, notes: list[dict], expected_head: str):
    """Validate immutable Plan-first edit context without invoking a provider."""
    from acs_plan_lock_binding import PlanLockWorkspace
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError('INVALID_WORKSPACE', 'Bound chat edits require PlanLockWorkspace')
    if expected_head != workspace.head:
        raise PlanError('STALE_REVISION', 'The reviewed plan has changed')
    if not isinstance(notes, list) or not notes or any(
            not isinstance(n, dict) or not isinstance(n.get('text'), str)
            or not n['text'].strip() for n in notes):
        raise PlanError('INVALID_EDIT', 'Explicit engineer notes are required')
    parsed_notes = json.loads(canonical(notes))
    # get() validates the stored revision-bound manifest before any candidate is
    # admitted or any provider work is started by the synchronous compatibility path.
    before = workspace.get(expected_head)
    return before, parsed_notes


def admit_bound_chat_edit_candidate(workspace, notes: list[dict], *,
                                    expected_head: str, candidate: dict):
    """Admit a precomputed chat candidate through canonical revision authority.

    This function intentionally performs **no provider work**. It is the parent-
    process seam needed by an isolated job runner: a worker may return proposed
    geometry, but only the authenticated host can re-check the expected head and
    ask ``PlanLockWorkspace`` to enforce inherited room/semantic locks before an
    immutable draft revision is created.

    Provider output also cannot manufacture measured scorecards, validation,
    compliance, approval, baseline, or other server-derived authority inside the
    Canonical Building. Those facts are preserved from the current canonical
    revision only when already present and unchanged; trusted ACS review and
    approval boundaries remain their source of truth.

    Approval is never copied to the new revision, an existing Frozen Baseline is
    never moved, and no CAD/BIM/3D/compiler path is invoked here.
    """
    before, parsed_notes = _bound_chat_edit_context(workspace, notes, expected_head)
    if not isinstance(candidate, dict):
        raise PlanError('INVALID_EDIT', 'Provider candidate must be a building object')
    detached_candidate = json.loads(canonical(candidate))
    _reject_provider_authority_changes(before.model, detached_candidate)
    return workspace.propose(
        detached_candidate,
        brief=before.brief,
        requirements=json.loads(before.requirements_json),
        expected_head=expected_head,
        note='\n'.join(n['text'] for n in parsed_notes),
    )


def propose_bound_chat_edit(workspace, notes: list[dict], *,
                            expected_head: str, model=None):
    """Propose one synchronous chat edit against server-held revision-bound locks.

    This compatibility bridge still performs the provider call synchronously and
    therefore must not be wired directly to a production request loop. The
    provider only proposes geometry. Final admission is delegated to
    :func:`admit_bound_chat_edit_candidate`, which re-checks the current head and
    makes the canonical workspace enforce all inherited locks before history is
    extended. A successful edit is always a new draft revision; any approved
    baseline remains frozen and no 3D/compiler path is invoked here.
    """
    before, parsed_notes = _bound_chat_edit_context(workspace, notes, expected_head)
    import acs_understand as U
    candidate = U.apply_notes(before.model, parsed_notes, model=model)
    # Re-enter the provider-free admission seam after provider execution. This
    # intentionally re-checks expected_head so concurrent edits cannot be
    # admitted merely because provider work began against an older revision.
    return admit_bound_chat_edit_candidate(
        workspace, parsed_notes, expected_head=expected_head, candidate=candidate)


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
        def explicit(opening):
            if not isinstance(opening, dict):
                return False
            for short, long in (('w', 'width'), ('h', 'height')):
                value = opening.get(long, opening.get(short))
                if not _number(value) or value <= 0:
                    return False
                if short in opening and long in opening and opening[short] != opening[long]:
                    return False
            return opening.get('edge') in ('N', 'S', 'E', 'W') and _number(opening.get('offset'))
        return all(explicit(o) for o in room['doors'] + room['windows'])
    topology_known = all(openings_explicit(r) for r in rooms)
    from acs_residential_access import issues as residential_access_issues, opening_collisions
    if topology_known:
        findings += [item['message'] for item in residential_access_issues(building)]
        findings += [item['message'] for item in opening_collisions(building)]
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
