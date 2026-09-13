"""Approved Frozen-Baseline-only IFC4 export for ACS Plan-first v2.

This bridge reuses :mod:`acs_bim`; it does not introduce a second BIM geometry
engine.  The exact canonical Building returned by ``PlanLockWorkspace.handoff``
is exported only after lock-bound conceptual approval.  A hash-bound sidecar
carries revision, semantic-lock and requirement/source provenance alongside the
IFC artifact.

The current Plan-first IFC scope is deliberately ``SPACES_ONLY``.  The existing
general BIM exporter can serialize wider building semantics, but some of those
paths use explicitly disclosed placeholder geometry when a property such as slab
thickness is absent.  An approved Plan-first artifact must not turn such a
placeholder into asserted approved geometry, so richer IFC geometry remains a
later slice that must first gain exact canonical contracts.

The sidecar is traceability evidence, not regulatory/structural certification.
IFC remains an exchange artifact; the Canonical ACS Model remains Source of Truth.
Import is intentionally inert: ``acs_bim`` is imported only after the approval
boundary has succeeded.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import PROVENANCE_SCHEMA, provenance_map
from acs_plan_review import PlanError, canonical, digest

SCHEMA = "acs.plan-ifc-export/1.1"
MODE = "DETERMINISTIC_APPROVED_FROZEN_BASELINE_ONLY"
IFC_SCOPE = "SPACES_ONLY"


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path]:
    out = Path(out_path)
    if not out.name or out.suffix.lower() != ".ifc":
        raise PlanError("INVALID_OUTPUT_PATH", "Approved BIM export currently emits .ifc only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "IFC output directory must already exist")
    sidecar = Path(str(out) + ".baseline.json")
    for path in (out, sidecar):
        if path.exists() and path.is_symlink():
            raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing a symlinked IFC artifact/receipt path")
    return out, sidecar


def _verify_space_map_matches_handoff(handoff_map: object, provenance: dict) -> None:
    if not isinstance(handoff_map, list):
        raise PlanError("PROVENANCE_MISMATCH", "Approved handoff source map is malformed")
    legacy = []
    for row in handoff_map:
        if not isinstance(row, dict):
            raise PlanError("PROVENANCE_MISMATCH", "Approved handoff source identity is malformed")
        legacy.append((row.get("level_index"), row.get("template"), row.get("room_id")))
    enriched = [
        (entry["source"].get("level_index"), entry["source"].get("template"),
         entry["source"].get("room_id"))
        for entry in provenance.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("source"), dict)
        and entry["source"].get("kind") == "space"
    ]
    if legacy != enriched:
        raise PlanError("PROVENANCE_MISMATCH",
                        "IFC provenance does not match approved canonical space identities")


def _publish_text_atomic(path: Path, text: str, *, suffix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=".acs-plan-", suffix=suffix, dir=str(path.parent))
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        return temp
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def export_approved_ifc(
    workspace: PlanLockWorkspace,
    revision_id: str,
    out_path: str | os.PathLike[str],
    *,
    overwrite: bool = False,
) -> dict:
    """Export exact approved space geometry through the existing IFC4 exporter.

    Drafts fail before ``acs_bim`` is imported.  The exporter receives a detached
    copy of the exact approved canonical Building and may not change its hash.
    Publication is atomic and accompanied by a hash-bound provenance receipt.
    Non-space geometry is deliberately excluded until every exported dimension is
    backed by an exact canonical contract rather than an exporter placeholder.
    """
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError("INVALID_WORKSPACE", "IFC export requires a PlanLockWorkspace")
    out, sidecar = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing IFC artifact or receipt")

    # Authority boundary first.  This must complete before the BIM exporter is
    # imported so an unapproved draft cannot reach export code at all.
    handoff = workspace.handoff(revision_id)
    bound = workspace.get(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    baseline = json.loads(canonical(handoff.get("baseline")))
    before_json = canonical(building)
    before_hash = digest(building)
    if baseline.get("revision_id") != revision_id:
        raise PlanError("BASELINE_CHANGED", "Approved IFC baseline revision identity changed")
    if baseline.get("model_hash") != before_hash or bound.model_hash != before_hash:
        raise PlanError("BASELINE_CHANGED", "Approved IFC model hash does not match its receipt")

    provenance = provenance_map(bound.revision)
    _verify_space_map_matches_handoff(handoff.get("source_map"), provenance)
    source_map = json.loads(canonical(provenance["entries"]))
    source_map_hash = digest(source_map)

    # Existing canonical BIM exporter only; no provider/compiler/replanning path.
    import acs_bim

    project = {
        "model": json.loads(before_json),
        "model_hash": before_hash,
        "current_revision": revision_id,
        "building_id": "bld_0",
    }
    exported = acs_bim.export_ifc(project, {"scope": IFC_SCOPE}, None)
    if canonical(building) != before_json or digest(building) != before_hash:
        raise PlanError("EXPORT_MUTATED_BASELINE", "IFC export changed the approved canonical plan")
    if not isinstance(exported, dict) or exported.get("valid") is not True:
        raise PlanError("IFC_EXPORT_FAILED", "Existing ACS BIM exporter rejected the approved baseline")
    text = exported.get("file")
    manifest = exported.get("manifest")
    if not isinstance(text, str) or not text.startswith("ISO-10303-21;") or not isinstance(manifest, dict):
        raise PlanError("INVALID_IFC_ARTIFACT", "ACS BIM exporter did not return a valid IFC4 artifact")
    if manifest.get("model_hash") != before_hash or manifest.get("revision_id") != revision_id:
        raise PlanError("BASELINE_CHANGED", "IFC exporter manifest is not bound to the approved baseline")
    if manifest.get("wall_count") != 0 or manifest.get("slab_count") != 0:
        raise PlanError("UNVERIFIED_IFC_GEOMETRY",
                        "Plan-first IFC emitted non-space geometry outside its exact scope")

    receipt = {
        "schema": SCHEMA,
        "mode": MODE,
        "ifc_scope": IFC_SCOPE,
        "revision_id": revision_id,
        "model_hash": before_hash,
        "content_hash": baseline.get("content_hash"),
        "approval_scope": baseline.get("approval_scope"),
        "lock_binding_schema": baseline.get("lock_binding_schema"),
        "bound_content_hash": baseline.get("bound_content_hash"),
        "semantic_lock_manifest_hash": baseline.get("semantic_lock_manifest_hash"),
        "semantic_lock_count": baseline.get("semantic_lock_count"),
        "provenance_schema": provenance["schema"],
        "requirements_hash": provenance["requirements_hash"],
        "provenance_hash": provenance["provenance_hash"],
        "source_map_hash": source_map_hash,
        "source_map": source_map,
        "ifc_manifest": json.loads(canonical(manifest)),
        "ifc_manifest_hash": digest(manifest),
        "provider_calls": 0,
        "replanning_calls": 0,
        "canonical_model_is_source_of_truth": True,
        "ifc_is_source_of_truth": False,
        "regulatory_compliance": "NOT_VERIFIED",
        "structural_safety": "NOT_VERIFIED",
    }

    temp_ifc = None
    temp_receipt = None
    try:
        temp_ifc = _publish_text_atomic(out, text, suffix=".ifc")
        receipt["artifact_sha256"] = _artifact_sha(temp_ifc)
        receipt["artifact_bytes"] = temp_ifc.stat().st_size
        canonical(receipt)
        temp_receipt = _publish_text_atomic(sidecar, canonical(receipt), suffix=".baseline.json")
        if overwrite:
            # os.replace is still atomic; explicit overwrite is the only path that
            # may replace an existing regular artifact/receipt pair.
            pass
        elif out.exists() or sidecar.exists():
            raise PlanError("OUTPUT_EXISTS", "IFC output appeared before atomic publication")
        os.replace(temp_ifc, out)
        temp_ifc = None
        os.replace(temp_receipt, sidecar)
        temp_receipt = None
        return json.loads(canonical(receipt))
    finally:
        for path in (temp_ifc, temp_receipt):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def verify_ifc_export(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify IFC bytes and the hash-bound Frozen-Baseline provenance sidecar."""
    out, sidecar = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_IFC_ARTIFACT", "IFC artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "IFC baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != MODE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown IFC baseline receipt")
    if receipt.get("ifc_scope") != IFC_SCOPE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "IFC receipt does not declare the exact Plan-first scope")
    if (receipt.get("canonical_model_is_source_of_truth") is not True
            or receipt.get("ifc_is_source_of_truth") is not False
            or receipt.get("replanning_calls") != 0):
        raise PlanError("INVALID_BASELINE_RECEIPT",
                        "IFC receipt overstates derived-artifact authority or downstream replanning")
    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "IFC artifact bytes no longer match the approved receipt")
    try:
        text = out.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PlanError("INVALID_IFC_ARTIFACT", "IFC artifact is not readable UTF-8 STEP text") from exc
    if not text.startswith("ISO-10303-21;") or "END-ISO-10303-21;" not in text:
        raise PlanError("INVALID_IFC_ARTIFACT", "IFC STEP envelope is malformed")
    if "IFCWALLSTANDARDCASE" in text or "IFCSLAB" in text:
        raise PlanError("UNVERIFIED_IFC_GEOMETRY", "IFC artifact contains geometry outside its declared scope")
    if digest(receipt.get("source_map")) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "IFC source map hash does not match the receipt")
    if receipt.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise PlanError("PROVENANCE_MISMATCH", "Unknown plan provenance schema in IFC receipt")
    reconstructed = {
        "schema": receipt["provenance_schema"],
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "entries": receipt.get("source_map"),
    }
    if digest(reconstructed) != receipt.get("provenance_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "IFC plan provenance hash does not match its source map")
    manifest = receipt.get("ifc_manifest")
    if not isinstance(manifest, dict) or digest(manifest) != receipt.get("ifc_manifest_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "IFC exporter manifest hash does not match the receipt")
    if manifest.get("revision_id") != receipt.get("revision_id") or manifest.get("model_hash") != receipt.get("model_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "IFC exporter manifest is detached from the Frozen Baseline")
    if manifest.get("wall_count") != 0 or manifest.get("slab_count") != 0:
        raise PlanError("UNVERIFIED_IFC_GEOMETRY", "IFC manifest contains geometry outside Plan-first scope")
    return {
        "ok": True,
        "artifact_sha256": actual_sha,
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "ifc_scope": receipt.get("ifc_scope"),
    }
