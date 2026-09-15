#!/usr/bin/env python3
"""One-shot exact patch for #155 production wiring; fail closed on source drift."""
from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one patch anchor, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "acs_workspace_service.py",
    '''    issues, _ = _geometry(revision.model)\n    if issues:\n        # First category in the canonical validator's deterministic order.\n        # The remaining projection checks stay authoritative and unchanged.\n        reason = issues[0].get("code")\n        code = "PLAN_GEOMETRY_" + reason if reason in GEOMETRY_MESSAGES else "INVALID_GEOMETRY"\n        raise PlanError(code, geometry_failure_message(code))\n    _view_result(ws, "generate", revision.id)  # projection admission before write\n''',
    '''    issues, _ = _geometry(revision.model)\n    # Warehouse Design Options are allowed to reach read-only 2D review while\n    # vertical engineering facts remain explicitly unknown. Only those three\n    # unknowns are deferred; every horizontal/canonical defect remains blocking.\n    from warehouse_vertical_stage_gate import draft_geometry_admission\n    admission = draft_geometry_admission(revision.model, issues)\n    if admission["blocking"]:\n        # First blocking category in the canonical validator's deterministic order.\n        reason = admission["blocking"][0].get("code")\n        code = "PLAN_GEOMETRY_" + reason if reason in GEOMETRY_MESSAGES else "INVALID_GEOMETRY"\n        raise PlanError(code, geometry_failure_message(code))\n    _view_result(ws, "generate", revision.id)  # stage-aware 2D projection admission before write\n''')

replace_once(
    "acs_plan_projection.py",
    '''    issues, _ = _geometry(model)\n    if issues:\n        raise PlanError('INVALID_GEOMETRY', 'Resolve geometry issues before CAD export')\n''',
    '''    issues, _ = _geometry(model)\n    # This projector is also the read-only 2D review surface. Warehouse drafts\n    # may defer only unresolved floor/wall vertical values; horizontal geometry\n    # still fails closed. Approved CAD remains protected by workspace.handoff().\n    from warehouse_vertical_stage_gate import draft_geometry_admission\n    admission = draft_geometry_admission(model, issues)\n    if admission['blocking']:\n        raise PlanError('INVALID_GEOMETRY', 'Resolve blocking geometry issues before 2D projection')\n''')

replace_once(
    "acs_plan_review.py",
    '''            if confirmed is not True or acknowledge_concept_only is not True or not _id(actor_label):\n                raise PlanError("EXPLICIT_APPROVAL_REQUIRED", "Explicit conceptual-design approval is required")\n            if not self.review(revision_id)["can_approve"]:\n''',
    '''            if confirmed is not True or acknowledge_concept_only is not True or not _id(actor_label):\n                raise PlanError("EXPLICIT_APPROVAL_REQUIRED", "Explicit conceptual-design approval is required")\n            # #155: a reviewable warehouse draft is not an approvable warehouse.\n            # Do not infer clear height or wall engineering at the approval boundary.\n            from warehouse_vertical_stage_gate import require_warehouse_vertical_for_downstream\n            require_warehouse_vertical_for_downstream(self.get(revision_id).model, "APPROVAL")\n            if not self.review(revision_id)["can_approve"]:\n''')

replace_once(
    "acs_plan_review.py",
    '''            rev = self.get(revision_id)\n            approval = self._approvals.get(revision_id)\n''',
    '''            rev = self.get(revision_id)\n            # Defence in depth for old/imported receipts: BIM/3D can never inherit\n            # a warehouse baseline whose vertical engineering facts are unresolved.\n            from warehouse_vertical_stage_gate import require_warehouse_vertical_for_downstream\n            require_warehouse_vertical_for_downstream(rev.model, "BIM_3D")\n            approval = self._approvals.get(revision_id)\n''')

replace_once(
    "Dockerfile",
    '''COPY acs_workspace_http.py acs_workspace_service.py acs_provider_budget.py acs_plan_overlap_repair.py acs_plan_sources.py ./\n''',
    '''COPY acs_workspace_http.py acs_workspace_service.py acs_provider_budget.py acs_plan_overlap_repair.py acs_plan_sources.py ./\n# #155 stage-aware warehouse draft admission; contains policy only, no defaults.\nCOPY warehouse_vertical_stage_gate.py ./\n''')

replace_once(
    "tests/remediation/test_warehouse_vertical_stage_gate.py",
    '''from acs_plan_review import PlanError, _geometry\nfrom warehouse_vertical_stage_gate import (draft_geometry_admission,\n''',
    '''from acs_plan_review import PlanError, PlanWorkspace, _geometry\nfrom acs_plan_projection import project\nfrom warehouse_vertical_stage_gate import (draft_geometry_admission,\n''')

replace_once(
    "tests/remediation/test_warehouse_vertical_stage_gate.py",
    '''    def test_non_finite_values_never_count_as_resolved(self):\n''',
    '''    def test_read_only_2d_survives_only_deferred_vertical_unknowns(self):\n        building=model()\n        ws=PlanWorkspace(lambda _m:{"scopes":{"topology":"PASS","vertical_circulation":"PASS"},"issues":[]})\n        rev=ws.propose(building,brief="warehouse 50x100",requirements=[],expected_head=None,note="draft")\n        drawing=project(rev,0)\n        self.assertEqual(len(drawing["primitives"]),2)\n        self.assertFalse(ws.review(rev.id)["can_approve"])\n        with self.assertRaises(PlanError) as caught:\n            ws.approve(rev.id,expected_head=rev.id,actor_label="engineer",confirmed=True,acknowledge_concept_only=True)\n        self.assertEqual(caught.exception.code,"DOWNSTREAM_GEOMETRY_NOT_SPECIFIED")\n\n    def test_read_only_2d_still_rejects_horizontal_failure(self):\n        building=model(); building["floors"]["ground"]["rooms"][0]["rect"]=[30,10,30,50]\n        ws=PlanWorkspace()\n        rev=ws.propose(building,brief="warehouse 50x100",requirements=[],expected_head=None,note="bad horizontal")\n        with self.assertRaises(PlanError) as caught:\n            project(rev,0)\n        self.assertEqual(caught.exception.code,"INVALID_GEOMETRY")\n\n    def test_non_finite_values_never_count_as_resolved(self):\n''')

print("warehouse stage-gate production wiring applied")
