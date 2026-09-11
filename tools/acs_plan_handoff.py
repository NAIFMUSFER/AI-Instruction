"""Approved-plan-only 3D compilation boundary for ACS Plan-first v2.

This module never calls an LLM and never repairs/replans geometry. It accepts only
an already-approved :class:`acs_plan_review.PlanWorkspace` revision, compiles the
exact canonical Building JSON returned by ``workspace.handoff()``, embeds a
non-geometric baseline receipt into the glTF root ``extras``, and writes a
hash-bound provenance sidecar next to the artifact.

The sidecar is traceability evidence, not regulatory/structural certification.
This module intentionally lives under ``tools/`` while the 3D handoff is an
offline/CI foundation rather than a public production route. Import is inert:
``acs_compiler`` is imported only inside the compile function.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable

from acs_plan_review import PlanError, PlanWorkspace, canonical, digest

SCHEMA = "acs.plan-3d-handoff/1.0"


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path]:
    out = Path(out_path)
    if not out.name or out.suffix.lower() != ".gltf":
        raise PlanError("INVALID_OUTPUT_PATH", "Approved 3D handoff currently emits .gltf only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "3D output directory must already exist")
    if out.exists() and out.is_symlink():
        raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing to replace a symlinked 3D artifact")
    sidecar = Path(str(out) + ".baseline.json")
    if sidecar.exists() and sidecar.is_symlink():
        raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing to replace a symlinked baseline receipt")
    return out, sidecar


def _embed_baseline_marker(gltf_path: Path, marker: dict) -> None:
    try:
        raw = json.loads(gltf_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "Compiler did not produce readable glTF JSON") from exc
    if not isinstance(raw, dict):
        raise PlanError("INVALID_3D_ARTIFACT", "Compiler glTF root must be an object")
    extras = raw.get("extras")
    if extras is None:
        extras = {}
        raw["extras"] = extras
    if not isinstance(extras, dict) or "acs_plan_baseline" in extras:
        raise PlanError("INVALID_3D_ARTIFACT", "glTF extras cannot safely carry ACS baseline provenance")
    extras["acs_plan_baseline"] = marker
    # The canonical plan/receipt envelope is deliberately bounded to 900 kB,
    # but a real glTF can be much larger. Do not route artifact JSON through
    # ``canonical`` merely to serialize it: that would reject valid large
    # geometry after a successful compile. We still reject NaN/Infinity and
    # hash the final bytes below; baseline metadata itself remains canonical.
    try:
        encoded = json.dumps(raw, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "glTF JSON contains unsupported values") from exc
    gltf_path.write_text(encoded, encoding="utf-8")


def compile_approved_baseline(
    workspace: PlanWorkspace,
    revision_id: str,
    out_path: str | os.PathLike[str],
    *,
    compiler: Callable[[dict, str], tuple[int, int]] | None = None,
    overwrite: bool = False,
) -> dict:
    """Compile exactly one approved baseline and return its provenance receipt.

    ``workspace.handoff`` is the authority boundary: drafts fail before the
    compiler is imported/called. The Building object is canonicalized and hashed
    before compilation; mutation by the compiler fails closed. The final file is
    written atomically only after those checks pass.
    """
    if not isinstance(workspace, PlanWorkspace):
        raise PlanError("INVALID_WORKSPACE", "Approved 3D handoff requires a PlanWorkspace")
    out, sidecar = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing 3D artifact or receipt")

    handoff = workspace.handoff(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    baseline = json.loads(canonical(handoff.get("baseline")))
    source_map = json.loads(canonical(handoff.get("source_map")))
    before_json = canonical(building)
    before_hash = digest(building)
    if baseline.get("model_hash") != before_hash:
        raise PlanError("BASELINE_CHANGED", "Approved handoff model hash does not match its receipt")
    source_map_hash = digest(source_map)

    if compiler is None:
        import acs_compiler as _compiler
        compiler = _compiler.compile_building
        compiler_id = "acs_compiler.compile_building"
    else:
        compiler_id = getattr(compiler, "__qualname__", None) or getattr(compiler, "__name__", None) or "callable"

    temp_artifact = None
    temp_receipt = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".acs-plan-", suffix=".gltf", dir=str(out.parent))
        os.close(fd)
        os.unlink(temp_name)  # compiler owns creation; existence is verified below
        temp_artifact = Path(temp_name)

        result = compiler(building, str(temp_artifact))
        if (not isinstance(result, tuple) or len(result) != 2
                or type(result[0]) is not int or type(result[1]) is not int
                or result[0] < 0 or result[1] < 0):
            raise PlanError("INVALID_COMPILER_RESULT", "3D compiler returned invalid node/buffer measurements")
        if canonical(building) != before_json or digest(building) != before_hash:
            raise PlanError("COMPILER_MUTATED_BASELINE", "3D compiler modified the approved canonical plan")
        if not temp_artifact.exists() or not temp_artifact.is_file() or temp_artifact.stat().st_size <= 0:
            raise PlanError("MISSING_3D_ARTIFACT", "3D compiler did not produce a non-empty glTF artifact")

        marker = {
            "schema": SCHEMA,
            "revision_id": baseline.get("revision_id"),
            "model_hash": before_hash,
            "content_hash": baseline.get("content_hash"),
            "approval_scope": baseline.get("approval_scope"),
            "source_map_hash": source_map_hash,
        }
        _embed_baseline_marker(temp_artifact, marker)
        artifact_sha = _artifact_sha(temp_artifact)
        receipt = {
            "schema": SCHEMA,
            "mode": "DETERMINISTIC_APPROVED_BASELINE_ONLY",
            "revision_id": marker["revision_id"],
            "model_hash": before_hash,
            "content_hash": marker["content_hash"],
            "approval_scope": marker["approval_scope"],
            "source_map_hash": source_map_hash,
            "source_map": source_map,
            "compiler": compiler_id,
            "compiler_node_count": result[0],
            "compiler_buffer_bytes": result[1],
            "artifact_sha256": artifact_sha,
            "artifact_bytes": temp_artifact.stat().st_size,
            "provider_calls": 0,
            "regulatory_compliance": "NOT_VERIFIED",
            "structural_safety": "NOT_VERIFIED",
        }
        canonical(receipt)

        fd, receipt_name = tempfile.mkstemp(prefix=".acs-plan-", suffix=".baseline.json", dir=str(out.parent))
        os.close(fd)
        temp_receipt = Path(receipt_name)
        temp_receipt.write_text(canonical(receipt), encoding="utf-8")

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


def verify_compiled_artifact(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify artifact bytes and embedded baseline marker against the sidecar/receipt."""
    out, sidecar = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_3D_ARTIFACT", "3D artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "3D baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != "DETERMINISTIC_APPROVED_BASELINE_ONLY":
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown 3D baseline receipt")
    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "3D artifact bytes no longer match the approved receipt")
    try:
        gltf = json.loads(out.read_text(encoding="utf-8"))
        marker = (gltf.get("extras") or {}).get("acs_plan_baseline") if isinstance(gltf, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "3D artifact is not readable glTF JSON") from exc
    expected = {k: receipt.get(k) for k in (
        "schema", "revision_id", "model_hash", "content_hash", "approval_scope", "source_map_hash")}
    if not isinstance(marker, dict) or canonical(marker) != canonical(expected):
        raise PlanError("PROVENANCE_MISMATCH", "Embedded 3D baseline provenance does not match the receipt")
    if digest(receipt.get("source_map")) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "Source map hash does not match the receipt")
    return {"ok": True, "artifact_sha256": actual_sha,
            "revision_id": receipt.get("revision_id"), "model_hash": receipt.get("model_hash")}
