"""Stage-aware admission for unresolved warehouse vertical engineering values.

No defaults are supplied here. Horizontal Design Options/2D may disclose missing
vertical engineering facts; approval/BIM/3D must still fail closed until explicit.
"""
from __future__ import annotations
import math
from acs_plan_review import PlanError
from acs_plan_scorecard import measure_plan

_VERTICAL_FIELDS = ("floor_height", "wall_h", "wall_t")
_DRAFT_STAGES = frozenset({"PLAN_DRAFT", "DESIGN_OPTION", "REVIEW_2D"})
_DOWNSTREAM_STAGES = frozenset({"APPROVAL", "FROZEN_BASELINE", "BIM_3D"})


def _warehouse(model: dict) -> bool:
    return isinstance(model, dict) and measure_plan(model).get("typology") == "warehouse"


def _positive(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def warehouse_vertical_stage_gate(model: dict, stage: str) -> dict:
    if stage not in _DRAFT_STAGES | _DOWNSTREAM_STAGES:
        raise PlanError("INVALID_PLAN_STAGE", "Unknown plan-stage admission boundary")
    if not _warehouse(model):
        return {"applicable": False, "stage": stage, "missing": [], "blocking": False}
    missing = [key for key in _VERTICAL_FIELDS if not _positive(model.get(key))]
    return {"applicable": True, "stage": stage, "missing": missing,
            "blocking": bool(missing) and stage in _DOWNSTREAM_STAGES}


def draft_geometry_admission(model: dict, issues: list[dict]) -> dict:
    """Defer only warehouse vertical unknowns; every horizontal defect stays fatal."""
    gate = warehouse_vertical_stage_gate(model, "PLAN_DRAFT")
    deferred, blocking = [], []
    for issue in issues:
        path = issue.get("path") if isinstance(issue, dict) else None
        vertical = (gate["applicable"] and isinstance(issue, dict)
                    and issue.get("code") == "DIMENSION_NOT_SPECIFIED"
                    and isinstance(path, str) and path.lstrip("/") in gate["missing"])
        (deferred if vertical else blocking).append(issue)
    return {"blocking": blocking, "deferred": deferred, "vertical": gate}


def require_warehouse_vertical_for_downstream(model: dict, stage: str = "APPROVAL") -> None:
    gate = warehouse_vertical_stage_gate(model, stage)
    if gate["blocking"]:
        raise PlanError("DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        "Warehouse vertical engineering values remain unresolved: "
                        + ", ".join(gate["missing"]))
