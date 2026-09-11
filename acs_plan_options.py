"""Measured comparison for ACS plan-first design alternatives.

This module compares canonical design options without ranking them or inventing an
AI quality score. It reuses the deterministic plan scorecard and publishes only
measured deltas whose source data is available in both the reference and target
option. Regulatory/structural compliance, storage capacity, throughput and travel
remain outside this contract unless a future authoritative engine supplies them.

The comparison is headless and inert: no provider, network, compiler, renderer or
production route is imported or invoked here.
"""
from __future__ import annotations

from typing import Any

from acs_plan_review import PlanError, canonical, digest
from acs_plan_scorecard import measure_plan

SCHEMA = "acs.plan-options/1.0"
MAX_OPTIONS = 8

_SCALAR_METRICS = (
    "site_area_m2",
    "level_count",
    "space_rect_area_m2",
    "dock_count",
    "rack_group_count",
    "rack_declared_level_sum",
    "station_count",
)
_MAP_METRICS = (
    "zone_area_by_role_m2",
    "dock_count_by_edge",
    "lane_area_by_kind_m2",
)


def _option_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 80


def _finite_number(value: Any) -> bool:
    # bool is deliberately excluded even though it is an int subclass.
    return type(value) in (int, float) and value == value and value not in (float("inf"), float("-inf"))


def _delta(reference: Any, value: Any) -> float | int | None:
    if not (_finite_number(reference) and _finite_number(value)):
        return None
    result = value - reference
    # Preserve integer counts where both inputs are integer counts.
    return result if type(reference) is float or type(value) is float else int(result)


def _map_delta(reference: Any, value: Any) -> dict[str, float | int] | None:
    """Compare complete measured mappings; absence of a key means measured zero.

    A mapping value of None means the scorecard could not establish the complete
    measurement, so no partial delta is published.
    """
    if not isinstance(reference, dict) or not isinstance(value, dict):
        return None
    keys = sorted(set(reference) | set(value))
    out: dict[str, float | int] = {}
    for key in keys:
        a, b = reference.get(key, 0), value.get(key, 0)
        d = _delta(a, b)
        if d is None:
            return None
        out[str(key)] = d
    return out


def compare_options(options: list[dict], *, declared_program_receipt: str | None = None) -> dict:
    """Compare 2..8 alternatives against the first option as the reference.

    `declared_program_receipt` is an opaque host receipt used only to label the
    comparison set. This module cannot authenticate that receipt and therefore
    never calls it verified. The caller must bind it to the confirmed Program of
    Requirements in an authenticated persistence layer.
    """
    if not isinstance(options, list) or not (2 <= len(options) <= MAX_OPTIONS):
        raise PlanError("OPTION_COUNT", "Provide between 2 and 8 design options")
    if declared_program_receipt is not None and (
            not isinstance(declared_program_receipt, str)
            or not declared_program_receipt.strip()
            or len(declared_program_receipt) > 256):
        raise PlanError("INVALID_PROGRAM_RECEIPT", "Program receipt must be a bounded non-empty string")

    seen: set[str] = set()
    measured: list[dict] = []
    # Bound the aggregate request as well as each canonical model. This prevents
    # option comparison from becoming a multiplier around the plan-review limits.
    canonical(options)

    for raw in options:
        if not isinstance(raw, dict) or not _option_id(raw.get("id")):
            raise PlanError("INVALID_OPTION", "Every option needs a stable bounded id")
        option_id = raw["id"].strip()
        if option_id in seen:
            raise PlanError("DUPLICATE_OPTION", "Design option ids must be unique")
        seen.add(option_id)
        model = raw.get("model")
        if not isinstance(model, dict):
            raise PlanError("INVALID_OPTION", "Every option needs canonical Building JSON")
        # Canonicalize/detach so scorecard code cannot observe a caller mutation
        # while the comparison is being assembled.
        model = __import__("json").loads(canonical(model))
        scorecard = measure_plan(model)
        typology = scorecard.get("typology")
        if typology == "unknown":
            raise PlanError("OPTION_TYPOLOGY_UNKNOWN", "Design options need an explicit canonical typology")
        revision_id = raw.get("revision_id")
        if revision_id is not None and not _option_id(revision_id):
            raise PlanError("INVALID_OPTION", "revision_id must be a bounded non-empty string when supplied")
        measured.append({
            "option_id": option_id,
            "revision_id": revision_id,
            "model_hash": digest(model),
            "scorecard": scorecard,
            "site": model.get("site"),
        })

    typologies = {item["scorecard"]["typology"] for item in measured}
    if len(typologies) != 1:
        raise PlanError("OPTION_TYPOLOGY_MISMATCH", "Only alternatives of the same typology are comparable")

    reference = measured[0]
    ref_metrics = reference["scorecard"]["metrics"]
    rows: list[dict] = []
    for item in measured:
        metrics = item["scorecard"]["metrics"]
        scalar = {key: _delta(ref_metrics.get(key), metrics.get(key))
                  for key in _SCALAR_METRICS if key in ref_metrics or key in metrics}
        mappings = {key: _map_delta(ref_metrics.get(key), metrics.get(key))
                    for key in _MAP_METRICS if key in ref_metrics or key in metrics}
        rows.append({
            "option_id": item["option_id"],
            "revision_id": item["revision_id"],
            "model_hash": item["model_hash"],
            "scorecard": item["scorecard"],
            "delta_from_reference": {"scalar": scalar, "mapping": mappings},
        })

    same_site = all(canonical(item["site"]) == canonical(reference["site"]) for item in measured[1:])
    level_counts = [item["scorecard"]["metrics"].get("level_count") for item in measured]
    same_level_count = all(v == level_counts[0] for v in level_counts[1:])
    disclosures = []
    if declared_program_receipt is None:
        disclosures.append("PROGRAM_EQUIVALENCE_NOT_VERIFIED")
    if not same_site:
        disclosures.append("SITE_CONSTRAINT_DIFFERS")
    if not same_level_count:
        disclosures.append("LEVEL_COUNT_DIFFERS")

    return {
        "schema": SCHEMA,
        "reference_option_id": reference["option_id"],
        "typology": next(iter(typologies)),
        "declared_program_receipt": declared_program_receipt,
        "program_receipt_authenticated": False,
        "same_site_geometry": same_site,
        "same_level_count": same_level_count,
        "options": rows,
        "disclosures": disclosures,
        "claims_best_option": False,
        "claims_regulatory_compliance": False,
        "claims_structural_safety": False,
    }
