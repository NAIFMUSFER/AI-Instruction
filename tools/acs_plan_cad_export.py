"""Approved Frozen-Baseline-only SVG/DXF export for ACS Plan-first v2.

The Canonical ACS Model remains the Source of Truth.  SVG and DXF are derived
review/exchange artifacts and may never become an alternate authoring authority.
This boundary intentionally calls :meth:`PlanLockWorkspace.handoff` before any
projection or CAD dependency is invoked, so an unapproved draft cannot reach the
approved-export path.

Only the exact ``SPACE_BOUNDARIES_ONLY`` projection already admitted by
``acs_plan_projection`` is exported.  No wall thickness, opening geometry,
structure, MEP, rack clearances, code dimensions, or other missing facts are
invented.  DXF still uses the existing optional ``ezdxf`` dependency and makes no
native-DWG or AutoCAD certification claim.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import PROVENANCE_SCHEMA, SCOPE, project, provenance_map, to_dxf, to_svg
from acs_plan_review import PlanError, canonical, digest

SCHEMA = "acs.plan-cad-export/1.0"
MODE = "DETERMINISTIC_APPROVED_FROZEN_BASELINE_ONLY"
FORMATS = {".svg": "SVG", ".dxf": "DXF"}


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path, str]:
    out = Path(out_path)
    fmt = FORMATS.get(out.suffix.lower()) if out.name else None
    if fmt is None:
        raise PlanError("INVALID_OUTPUT_PATH", "Approved CAD export emits .svg or .dxf only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "CAD output directory must already exist")
    sidecar = Path(str(out) + ".baseline.json")
    for path in (out, sidecar):
        if path.exists() and path.is_symlink():
            raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing a symlinked CAD artifact/receipt path")
    return out, sidecar, fmt


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
                        "CAD provenance does not match approved canonical space identities")


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


def _approved_context(workspace: PlanLockWorkspace, revision_id: str) -> tuple[dict, object, dict]:
    """Cross the approval boundary before projection/CAD work and bind hashes."""
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError("INVALID_WORKSPACE", "Approved CAD export requires a PlanLockWorkspace")
    handoff = workspace.handoff(revision_id)
    bound = workspace.get(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    baseline = json.loads(canonical(handoff.get("baseline")))
    model_hash = digest(building)
    if baseline.get("revision_id") != revision_id:
        raise PlanError("BASELINE_CHANGED", "Approved CAD baseline revision identity changed")
    if baseline.get("model_hash") != model_hash or bound.model_hash != model_hash:
        raise PlanError("BASELINE_CHANGED", "Approved CAD model hash does not match its receipt")
    provenance = provenance_map(bound.revision)
    _verify_space_map_matches_handoff(handoff.get("source_map"), provenance)
    return baseline, bound, provenance


def export_approved_cad(workspace: PlanLockWorkspace, revision_id: str, level_index: int,
                        out_path: str | os.PathLike[str], *, overwrite: bool = False) -> dict:
    """Export one exact approved canonical level as SVG or DXF plus a hash-bound receipt."""
    if type(level_index) is not int:
        raise PlanError("INVALID_LEVEL", "Approved CAD export requires an explicit integer level index")
    out, sidecar, fmt = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing CAD artifact or receipt")

    # Authority first. A draft fails here before project(), to_svg(), to_dxf(), or
    # the optional ezdxf dependency can be reached.
    baseline, bound, provenance = _approved_context(workspace, revision_id)
    projection = project(bound.revision, level_index)
    if (projection.get("scope") != SCOPE
            or projection.get("revision_id") != revision_id
            or projection.get("model_hash") != bound.model_hash
            or projection.get("provenance_hash") != provenance.get("provenance_hash")
            or projection.get("requirements_hash") != provenance.get("requirements_hash")):
        raise PlanError("PROJECTION_CHANGED", "CAD projection is detached from the Frozen Baseline")

    if fmt == "SVG":
        artifact_text = to_svg(bound.revision, level_index)
        try:
            root = ET.fromstring(artifact_text)
            metadata_node = root.find("{*}metadata")
            embedded = json.loads(metadata_node.text) if metadata_node is not None and metadata_node.text else None
        except (ET.ParseError, json.JSONDecodeError) as exc:
            raise PlanError("INVALID_CAD_ARTIFACT", "SVG export did not preserve readable metadata") from exc
        if not isinstance(embedded, dict):
            raise PlanError("INVALID_CAD_ARTIFACT", "SVG export has no projection metadata")
        for key in ("scope", "revision_id", "model_hash", "requirements_hash", "provenance_hash"):
            if embedded.get(key) != projection.get(key):
                raise PlanError("PROJECTION_CHANGED", "SVG metadata is detached from the approved projection")
        format_claims = {"native_dwg": False, "autocad_verified": False}
    else:
        generated = to_dxf(bound.revision, level_index)
        if not isinstance(generated, dict) or not isinstance(generated.get("dxf_text"), str):
            raise PlanError("INVALID_CAD_ARTIFACT", "DXF exporter did not return text")
        manifest = generated.get("manifest")
        if not isinstance(manifest, dict) or canonical(manifest) != canonical(projection):
            raise PlanError("PROJECTION_CHANGED", "DXF manifest is detached from the approved projection")
        artifact_text = generated["dxf_text"]
        format_claims = {
            "native_dwg": generated.get("native_dwg") is True,
            "autocad_verified": generated.get("autocad_verified") is True,
        }
        if format_claims["native_dwg"] or format_claims["autocad_verified"]:
            raise PlanError("UNVERIFIED_CAD_CLAIM", "Plan-first DXF may not claim native DWG or AutoCAD verification")

    # Re-read the immutable bound revision after derivation; exports may not alter
    # the approved authority object or silently advance to another revision.
    after = workspace.get(revision_id)
    if (after.bound_content_hash != bound.bound_content_hash
            or after.model_hash != bound.model_hash
            or workspace.baseline != revision_id):
        raise PlanError("BASELINE_CHANGED", "Frozen Baseline changed during CAD export")

    source_map = json.loads(canonical(provenance["entries"]))
    receipt = {
        "schema": SCHEMA,
        "mode": MODE,
        "format": fmt,
        "projection_scope": SCOPE,
        "level_index": level_index,
        "revision_id": revision_id,
        "model_hash": bound.model_hash,
        "content_hash": baseline.get("content_hash"),
        "approval_scope": baseline.get("approval_scope"),
        "lock_binding_schema": baseline.get("lock_binding_schema"),
        "bound_content_hash": baseline.get("bound_content_hash"),
        "semantic_lock_manifest_hash": baseline.get("semantic_lock_manifest_hash"),
        "semantic_lock_count": baseline.get("semantic_lock_count"),
        "provenance_schema": provenance["schema"],
        "requirements_hash": provenance["requirements_hash"],
        "provenance_hash": provenance["provenance_hash"],
        "source_map_hash": digest(source_map),
        "source_map": source_map,
        "projection_hash": digest(projection),
        "projection_manifest": json.loads(canonical(projection)),
        "provider_calls": 0,
        "replanning_calls": 0,
        "canonical_model_is_source_of_truth": True,
        "cad_is_source_of_truth": False,
        "construction_document": False,
        "regulatory_compliance": "NOT_VERIFIED",
        "structural_safety": "NOT_VERIFIED",
        **format_claims,
    }

    temp_artifact = None
    temp_receipt = None
    try:
        temp_artifact = _publish_text_atomic(out, artifact_text, suffix=out.suffix.lower())
        receipt["artifact_sha256"] = _artifact_sha(temp_artifact)
        receipt["artifact_bytes"] = temp_artifact.stat().st_size
        canonical(receipt)
        temp_receipt = _publish_text_atomic(sidecar, canonical(receipt), suffix=".baseline.json")
        if not overwrite and (out.exists() or sidecar.exists()):
            raise PlanError("OUTPUT_EXISTS", "CAD output appeared before atomic publication")
        os.replace(temp_artifact, out)
        temp_artifact = None
        os.replace(temp_receipt, sidecar)
        temp_receipt = None
        return json.loads(canonical(receipt))
    finally:
        for path in (temp_artifact, temp_receipt):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def verify_cad_export(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify artifact bytes plus Frozen-Baseline/provenance binding.

    DXF generation itself is audited by the existing ezdxf-backed projector. This
    verifier intentionally needs no CAD dependency: it verifies the immutable
    artifact hash and the sidecar's canonical projection/provenance receipts.
    """
    out, sidecar, fmt = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_CAD_ARTIFACT", "CAD artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "CAD baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != MODE or receipt.get("format") != fmt:
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown or mismatched CAD baseline receipt")
    if receipt.get("projection_scope") != SCOPE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "CAD receipt declares an unsupported projection scope")
    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "CAD artifact bytes no longer match the approved receipt")
    source_map = receipt.get("source_map")
    if digest(source_map) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "CAD source map hash does not match the receipt")
    if receipt.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise PlanError("PROVENANCE_MISMATCH", "Unknown plan provenance schema in CAD receipt")
    reconstructed = {
        "schema": receipt["provenance_schema"],
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "entries": source_map,
    }
    if digest(reconstructed) != receipt.get("provenance_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "CAD plan provenance hash does not match its source map")
    projection = receipt.get("projection_manifest")
    if not isinstance(projection, dict) or digest(projection) != receipt.get("projection_hash"):
        raise PlanError("PROJECTION_CHANGED", "CAD projection manifest hash does not match the receipt")
    if (projection.get("revision_id") != receipt.get("revision_id")
            or projection.get("model_hash") != receipt.get("model_hash")
            or projection.get("requirements_hash") != receipt.get("requirements_hash")
            or projection.get("provenance_hash") != receipt.get("provenance_hash")):
        raise PlanError("PROJECTION_CHANGED", "CAD projection manifest is detached from the Frozen Baseline")
    if (receipt.get("canonical_model_is_source_of_truth") is not True
            or receipt.get("cad_is_source_of_truth") is not False
            or receipt.get("construction_document") is not False
            or receipt.get("regulatory_compliance") != "NOT_VERIFIED"):
        raise PlanError("INVALID_BASELINE_RECEIPT", "CAD receipt overstates derived-artifact authority")

    try:
        text = out.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PlanError("INVALID_CAD_ARTIFACT", "CAD artifact is not readable UTF-8 text") from exc
    if fmt == "SVG":
        try:
            root = ET.fromstring(text)
            metadata_node = root.find("{*}metadata")
            embedded = json.loads(metadata_node.text) if metadata_node is not None and metadata_node.text else None
        except (ET.ParseError, json.JSONDecodeError) as exc:
            raise PlanError("INVALID_CAD_ARTIFACT", "SVG artifact metadata is malformed") from exc
        if not isinstance(embedded, dict):
            raise PlanError("INVALID_CAD_ARTIFACT", "SVG artifact metadata is absent")
        if (embedded.get("revision_id") != receipt.get("revision_id")
                or embedded.get("model_hash") != receipt.get("model_hash")
                or embedded.get("provenance_hash") != receipt.get("provenance_hash")):
            raise PlanError("PROJECTION_CHANGED", "SVG artifact metadata is detached from its receipt")
    else:
        # Structural DXF validity was checked by doc.audit() in to_dxf(). Keep this
        # dependency-free verifier deliberately modest; hash binding is authoritative.
        if "SECTION" not in text or "EOF" not in text:
            raise PlanError("INVALID_CAD_ARTIFACT", "DXF text envelope is malformed")
        if receipt.get("native_dwg") is not False or receipt.get("autocad_verified") is not False:
            raise PlanError("UNVERIFIED_CAD_CLAIM", "DXF receipt overstates interoperability verification")

    return {
        "ok": True,
        "format": fmt,
        "artifact_sha256": actual_sha,
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "level_index": receipt.get("level_index"),
        "projection_scope": receipt.get("projection_scope"),
    }
