"""Versioned opening source identities shared by admission and authoring.

No geometry mutation, LLM call, authoring command or UI dependency.
"""
import re

# Reserved derived projections cannot become canonical opening sources.
DERIVED_NS = ("runtime:", "obstacle:", "portal:", "walk:", "vertical:",
              "measure:", "vis:", "clash_", "nav:", "egress:")


def _issue(code, subject, detail):
    return {"code": code, "severity": "ERROR", "subject": subject, "detail": detail}


def _all_rooms(model):
    return [(t, r) for t in sorted((model.get("floors") or {}).keys())
            for r in ((model["floors"][t] or {}).get("rooms") or [])]


def _space_key(building_id, template, room_id):
    return "%s.%s.%s" % (building_id, template, room_id)


OPENING_IDENTITY_SCHEMA = "acs.opening-identity/1"


def opening_identity_issues(model, building_id="bld_0"):
    """Validate persistent source identities; legacy positional IDs remain readable."""
    issues, seen = [], set()
    reserved = {building_id, "site", "__proto__", "constructor", "prototype"}
    for t, room in _all_rooms(model):
        reserved.update([str(room.get("id")),
                         room.get("space_id") or _space_key(building_id, t, room.get("id"))])
    for lv in model.get("levels") or []:
        if isinstance(lv, dict):
            reserved.add(lv.get("id") or "%s.flr_%s" % (building_id, lv.get("index", 0)))
    marker = model.get("_opening_identity")
    if marker is not None and (not isinstance(marker, dict) or
            marker.get("schema") != OPENING_IDENTITY_SCHEMA or
            type(marker.get("next")) is not int or not 0 <= marker["next"] < 2147483647):
        issues.append(_issue("MODEL_INTEGRITY_FAILURE", "_opening_identity",
                             "unsupported opening identity version or allocator"))
    for t, room in _all_rooms(model):
        sid = room.get("space_id") or _space_key(building_id, t, room.get("id"))
        for key in ("doors", "windows"):
            for i, op in enumerate(room.get(key) or []):
                legacy = "%s.%s_%d" % (sid, key[:-1], i)
                if not isinstance(op, dict):
                    issues.append(_issue("MODEL_INTEGRITY_FAILURE", legacy,
                                         "an opening record is not an object"))
                    continue
                oid = op.get("id", legacy if marker is None else None)
                if (not isinstance(oid, str) or not oid or
                        len(oid.encode("utf-16-le", errors="surrogatepass")) // 2 > 256 or
                        re.search(r'''[@\s\x00-\x1f\x7f-\x9f\ufeff<>"'\\]''', oid) or
                        any(oid.startswith(ns) for ns in DERIVED_NS)):
                    issues.append(_issue("MODEL_INTEGRITY_FAILURE", legacy,
                                         "opening identity is missing or invalid"))
                    continue
                if oid in seen or oid in reserved:
                    issues.append(_issue("ID_COLLISION", oid, "duplicate opening identity"))
                seen.add(oid)
    return issues


class OpeningIdentityError(ValueError):
    """The opening identity contract does not hold for this model."""


def _opening_id_counts(model):
    counts = {}
    for _t, room in _all_rooms(model):
        for key in ("doors", "windows"):
            for op in room.get(key) or []:
                oid = op.get("id") if isinstance(op, dict) else None
                if isinstance(oid, str):
                    counts[oid] = counts.get(oid, 0) + 1
    return counts


def inherited_collisions(model, building_id="bld_0"):
    """Repeated opening IDs an already admitted model carries: {id: occurrences}.

    Revision admission does not require unique opening IDs, and generated plans
    repeat them: a stair-template variant is a deep copy of its source template,
    openings included (acs_stairs.with_default_stairs), and a generated door can
    carry one ID on both of its faces. An edit of such a saved plan starts from
    it as it is. Only ID_COLLISION is inherited; a missing, malformed or derived
    namespace ID is not listed here and still fails closed.
    """
    counts = _opening_id_counts(model)
    return {i["subject"]: counts.get(i["subject"], 0)
            for i in opening_identity_issues(model, building_id)
            if i["code"] == "ID_COLLISION"}


def stabilise_opening_ids(model, building_id="bld_0", inherited=None):
    """Explicit, idempotent migration on a candidate/new model, never on saved history.

    Existing positional references become stored source IDs unchanged. No geometry
    or provenance is inferred. A migrated model with missing IDs fails closed.
    Callers include the returned paths in the same authoring revision.

    ``inherited`` (from :func:`inherited_collisions` of the admitted source) lets
    an edit keep the repeats that source already had, never more of them; any
    new repeat or invalid ID still fails closed.
    """
    issues = opening_identity_issues(model, building_id)
    if inherited:
        counts = _opening_id_counts(model)
        issues = [i for i in issues
                  if not (i["code"] == "ID_COLLISION" and i["subject"] in inherited
                          and counts.get(i["subject"], 0) <= inherited[i["subject"]])]
    if issues:
        raise OpeningIdentityError("invalid opening identity contract")
    if model.get("_opening_identity") is not None:
        return []
    changed = []
    for t, room in _all_rooms(model):
        sid = room.get("space_id") or _space_key(building_id, t, room.get("id"))
        for key in ("doors", "windows"):
            for i, op in enumerate(room.get(key) or []):
                if "id" not in op:
                    op["id"] = "%s.%s_%d" % (sid, key[:-1], i)
                    changed.append("floors.%s.rooms.%s.%s[%d].id" %
                                   (t, room.get("id"), key, i))
    model["_opening_identity"] = {"schema": OPENING_IDENTITY_SCHEMA, "next": 0}
    return changed + ["_opening_identity"]
