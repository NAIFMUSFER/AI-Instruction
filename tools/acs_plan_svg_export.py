"""Approved Frozen-Baseline-only SVG export for ACS Design Pipeline v2.

Preview SVGs may be rendered from any revision by ``acs_plan_projection.to_svg``.
This module is the stricter release/export boundary: only an engineer-approved
``PlanLockWorkspace`` revision can be published. The output and sidecar remain
bound to the exact canonical revision, level, semantic-lock receipt and
requirement/source provenance. SVG is derived; the Canonical ACS Model remains
Source of Truth. No provider, replanning, regulation or safety claim is involved.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import PROVENANCE_SCHEMA, SCOPE, project, provenance_map, to_svg
from acs_plan_review import PlanError, canonical, digest

SCHEMA = "acs.plan-svg-export/1.0"
MODE = "DETERMINISTIC_APPROVED_FROZEN_BASELINE_ONLY"
SVG_SCOPE = SCOPE


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path]:
    out = Path(out_path)
    if not out.name or out.suffix.lower() != ".svg":
        raise PlanError("INVALID_OUTPUT_PATH", "Approved plan SVG export emits .svg only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "SVG output directory must already exist")
    sidecar = Path(str(out) + ".baseline.json")
    for path in (out, sidecar):
        if path.exists() and path.is_symlink():
            raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing a symlinked SVG artifact/receipt path")
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
                        "SVG provenance does not match approved canonical space identities")


def _svg_metadata(payload: bytes) -> dict:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise PlanError("INVALID_SVG_ARTIFACT", "SVG XML is malformed") from exc
    if root.tag.split("}")[-1] != "svg":
        raise PlanError("INVALID_SVG_ARTIFACT", "SVG root element is missing")
    nodes = [node for node in root.iter() if node.tag.split("}")[-1] == "metadata"]
    if len(nodes) != 1 or not isinstance(nodes[0].text, str):
        raise PlanError("PROVENANCE_MISMATCH", "SVG must contain one provenance metadata block")
    try:
        value = json.loads(nodes[0].text)
    except json.JSONDecodeError as exc:
        raise PlanError("PROVENANCE_MISMATCH", "SVG provenance metadata is invalid JSON") from exc
    if not isinstance(value, dict):
        raise PlanError("PROVENANCE_MISMATCH", "SVG provenance metadata must be an object")
    return value


def _publish_bytes_atomic(path: Path, payload: bytes, *, suffix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=".acs-plan-", suffix=suffix, dir=str(path.parent))
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        return temp
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _publish_text_atomic(path: Path, text: str, *, suffix: str) -> Path:
    return _publish_bytes_atomic(path, text.encode("utf-8"), suffix=suffix)


def export_approved_svg(workspace: PlanLockWorkspace, revision_id: str, level_index: int,
                        out_path: str | os.PathLike[str], *, overwrite: bool = False) -> dict:
    """Publish one approved canonical level as a deterministic hash-bound SVG."""
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError("INVALID_WORKSPACE", "SVG export requires a PlanLockWorkspace")
    if type(level_index) is not int:
        raise PlanError("INVALID_LEVEL", "Approved SVG export requires an integer level index")
    out, sidecar = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing SVG artifact or receipt")

    handoff = workspace.handoff(revision_id)  # rejects drafts before projection
    bound = workspace.get(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    baseline = json.loads(canonical(handoff.get("baseline")))
    before_json = canonical(building)
    before_hash = digest(building)
    if baseline.get("revision_id") != revision_id:
        raise PlanError("BASELINE_CHANGED", "Approved SVG baseline revision identity changed")
    if baseline.get("model_hash") != before_hash or bound.model_hash != before_hash:
        raise PlanError("BASELINE_CHANGED", "Approved SVG model hash does not match its receipt")

    provenance = provenance_map(bound.revision)
    _verify_space_map_matches_handoff(handoff.get("source_map"), provenance)
    source_map = json.loads(canonical(provenance["entries"]))
    projected = project(bound.revision, level_index)
    if (projected.get("revision_id") != revision_id
            or projected.get("model_hash") != before_hash
            or projected.get("provenance_hash") != provenance["provenance_hash"]
            or projected.get("requirements_hash") != provenance["requirements_hash"]
            or projected.get("scope") != SVG_SCOPE):
        raise PlanError("BASELINE_CHANGED", "SVG projection detached from Frozen Baseline")

    svg_bytes = to_svg(bound.revision, level_index).encode("utf-8")
    metadata = _svg_metadata(svg_bytes)
    expected_metadata = {k: v for k, v in projected.items() if k != "primitives"}
    if canonical(metadata) != canonical(expected_metadata):
        raise PlanError("PROVENANCE_MISMATCH", "SVG embedded metadata detached from canonical projection")
    if canonical(building) != before_json or digest(building) != before_hash:
        raise PlanError("EXPORT_MUTATED_BASELINE", "SVG export changed the approved canonical plan")
    primitives = projected.get("primitives")
    if not isinstance(primitives, list):
        raise PlanError("INVALID_SVG_ARTIFACT", "SVG projection has no primitive list")

    receipt = {
        "schema": SCHEMA, "mode": MODE, "svg_scope": SVG_SCOPE,
        "revision_id": revision_id, "model_hash": before_hash, "level_index": level_index,
        "content_hash": baseline.get("content_hash"),
        "approval_scope": baseline.get("approval_scope"),
        "lock_binding_schema": baseline.get("lock_binding_schema"),
        "bound_content_hash": baseline.get("bound_content_hash"),
        "semantic_lock_manifest_hash": baseline.get("semantic_lock_manifest_hash"),
        "semantic_lock_count": baseline.get("semantic_lock_count"),
        "provenance_schema": provenance["schema"],
        "requirements_hash": provenance["requirements_hash"],
        "provenance_hash": provenance["provenance_hash"],
        "source_map_hash": digest(source_map), "source_map": source_map,
        "projection_hash": digest(projected), "projected_space_count": len(primitives),
        "canonical_model_is_source_of_truth": True,
        "svg_is_source_of_truth": False,
        "provider_calls": 0, "replanning_calls": 0,
        "construction_approved": False,
        "regulatory_compliance": "NOT_VERIFIED",
        "structural_safety": "NOT_VERIFIED",
        "fire_life_safety_compliance": "NOT_VERIFIED",
    }

    temp_svg = temp_receipt = None
    try:
        temp_svg = _publish_bytes_atomic(out, svg_bytes, suffix=".svg")
        receipt["artifact_sha256"] = _artifact_sha(temp_svg)
        receipt["artifact_bytes"] = temp_svg.stat().st_size
        canonical(receipt)
        temp_receipt = _publish_text_atomic(sidecar, canonical(receipt), suffix=".baseline.json")
        if not overwrite and (out.exists() or sidecar.exists()):
            raise PlanError("OUTPUT_EXISTS", "SVG output appeared before atomic publication")
        os.replace(temp_svg, out); temp_svg = None
        os.replace(temp_receipt, sidecar); temp_receipt = None
        return json.loads(canonical(receipt))
    finally:
        for path in (temp_svg, temp_receipt):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def _valid_lock_receipt(receipt: dict) -> bool:
    count = receipt.get("semantic_lock_count")
    if type(count) is not int or count < 0:
        return False
    if not isinstance(receipt.get("lock_binding_schema"), str) or not receipt["lock_binding_schema"]:
        return False
    if not isinstance(receipt.get("bound_content_hash"), str) or not receipt["bound_content_hash"]:
        return False
    manifest_hash = receipt.get("semantic_lock_manifest_hash")
    if count == 0:
        return manifest_hash is None
    return isinstance(manifest_hash, str) and bool(manifest_hash)


def verify_svg_export(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify SVG bytes, authority semantics and Frozen-Baseline provenance sidecar."""
    out, sidecar = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_SVG_ARTIFACT", "SVG artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "SVG baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != MODE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown SVG baseline receipt")
    if receipt.get("svg_scope") != SVG_SCOPE or type(receipt.get("level_index")) is not int:
        raise PlanError("INVALID_BASELINE_RECEIPT", "SVG receipt does not declare the exact Plan-first scope/level")
    if (receipt.get("canonical_model_is_source_of_truth") is not True
            or receipt.get("svg_is_source_of_truth") is not False
            or receipt.get("provider_calls") != 0 or receipt.get("replanning_calls") != 0):
        raise PlanError("INVALID_BASELINE_RECEIPT", "SVG receipt violates derived-artifact authority semantics")
    if not _valid_lock_receipt(receipt):
        raise PlanError("INVALID_BASELINE_RECEIPT", "SVG receipt has incomplete semantic-lock binding")
    if (receipt.get("construction_approved") is not False
            or receipt.get("regulatory_compliance") != "NOT_VERIFIED"
            or receipt.get("structural_safety") != "NOT_VERIFIED"
            or receipt.get("fire_life_safety_compliance") != "NOT_VERIFIED"):
        raise PlanError("INVALID_BASELINE_RECEIPT", "SVG receipt contains unsupported safety/compliance claims")

    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "SVG artifact bytes no longer match the approved receipt")
    metadata = _svg_metadata(out.read_bytes())
    for key in ("revision_id", "model_hash", "level_index", "provenance_schema",
                "requirements_hash", "provenance_hash", "source_map"):
        if canonical(metadata.get(key)) != canonical(receipt.get(key)):
            raise PlanError("PROVENANCE_MISMATCH", f"SVG metadata field {key} is detached from its receipt")
    if digest(receipt.get("source_map")) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "SVG source map hash does not match the receipt")
    if receipt.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise PlanError("PROVENANCE_MISMATCH", "Unknown plan provenance schema in SVG receipt")
    reconstructed = {
        "schema": receipt["provenance_schema"], "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"), "requirements_hash": receipt.get("requirements_hash"),
        "entries": receipt.get("source_map"),
    }
    if digest(reconstructed) != receipt.get("provenance_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "SVG plan provenance hash does not match its source map")
    if type(receipt.get("projected_space_count")) is not int or receipt["projected_space_count"] < 0:
        raise PlanError("INVALID_BASELINE_RECEIPT", "SVG projected space count is invalid")
    return {
        "ok": True, "artifact_sha256": actual_sha,
        "revision_id": receipt.get("revision_id"), "model_hash": receipt.get("model_hash"),
        "level_index": receipt.get("level_index"), "requirements_hash": receipt.get("requirements_hash"),
        "svg_scope": receipt.get("svg_scope"), "projected_space_count": receipt.get("projected_space_count"),
    }
