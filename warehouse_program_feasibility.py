"""Deterministic warehouse program feasibility before geometric layout.

This module never invents setbacks, code dimensions, building targets, or room
areas. It separates indoor program demand from outdoor site operations and
makes feasibility explicit before expensive/detail generation.
"""
from __future__ import annotations
import math

_VALID_SCOPES = frozenset({"indoor", "outdoor"})


def _area(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def classify_warehouse_program(program):
    indoor = outdoor = hard_indoor = 0.0
    invalid = []
    for index, item in enumerate(program if isinstance(program, list) else []):
        if not isinstance(item, dict) or item.get("scope") not in _VALID_SCOPES:
            invalid.append(index); continue
        area = _area(item.get("area_m2"))
        if area is None:
            invalid.append(index); continue
        if item["scope"] == "indoor":
            indoor += area
            if item.get("hard") is True:
                hard_indoor += area
        else:
            outdoor += area
    return {"indoor_area_m2": indoor, "outdoor_area_m2": outdoor,
            "hard_indoor_area_m2": hard_indoor, "invalid_indices": invalid}


def generated_indoor_area(building):
    """Measure canonical floor rectangles only; site/outdoor objects are excluded."""
    try:
        floors=building['floors']
        if not isinstance(floors,dict): return None
        total=0.0
        for floor in floors.values():
            for room in floor['rooms']:
                rect=room['rect']
                if not isinstance(rect,list) or len(rect)!=4: return None
                w,d=_area(rect[2]),_area(rect[3])
                if w is None or d is None:return None
                total += w*d
        return total
    except (KeyError,TypeError):
        return None


def warehouse_program_feasibility(*, site_area_m2, building_target_m2, program):
    site = _area(site_area_m2)
    target = _area(building_target_m2)
    classified = classify_warehouse_program(program)
    base = {
        "site_area_m2": site,
        "building_target_m2": target,
        "indoor_program_m2": classified["indoor_area_m2"],
        "outdoor_program_m2": classified["outdoor_area_m2"],
        "hard_indoor_area_m2": classified["hard_indoor_area_m2"],
        "invalid_indices": classified["invalid_indices"],
    }
    if classified["invalid_indices"]:
        return {**base, "status":"PROGRAM_NOT_VERIFIED", "indoor_budget_m2":None,
                "adjustment_required":False, "may_generate_layout":False}
    # Site area alone is not permission to build over the whole plot.
    if target is None or target <= 0:
        return {**base, "status":"BUILDABLE_ENVELOPE_NOT_VERIFIED", "indoor_budget_m2":None,
                "adjustment_required":False, "may_generate_layout":False}
    # An explicit building target cannot exceed an explicit site, but no setback
    # or regulatory deduction is inferred here.
    if site is not None and target > site:
        return {**base, "status":"BUILDING_TARGET_EXCEEDS_SITE", "indoor_budget_m2":target,
                "adjustment_required":False, "may_generate_layout":False}
    if classified["hard_indoor_area_m2"] > target:
        return {**base, "status":"INFEASIBLE_HARD_PROGRAM", "indoor_budget_m2":target,
                "adjustment_required":False, "may_generate_layout":False}
    adjustment = classified["indoor_area_m2"] > target
    return {**base, "status":"ADJUSTABLE" if adjustment else "FEASIBLE",
            "indoor_budget_m2":target, "adjustment_required":adjustment,
            "may_generate_layout":True}
