"""Approved Frozen-Baseline-only PDF plan export for ACS Plan-first v2.

The PDF is a deterministic review artifact derived from the exact canonical plan
that has already crossed :class:`acs_plan_lock_binding.PlanLockWorkspace`'s
approval boundary. It does not call an LLM, CAD engine, BIM compiler, regulator,
or geometry repair/replanning path. One page is emitted per canonical level.

Only schematic space boundaries are drawn because those are the exact geometric
primitives currently admitted by ``acs_plan_projection.project``. Room labels are
kept in the hash-bound UTF-8 sidecar (the PDF uses an ASCII base font and numbered
space callouts) so non-Latin labels are never silently corrupted or transliterated.

The sidecar preserves revision/model hashes, semantic-lock binding and
requirement/source provenance. It is traceability evidence, not construction,
regulatory, structural, fire-safety or accessibility certification. The Canonical
ACS Model remains Source of Truth; PDF is a derived artifact only.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import PROVENANCE_SCHEMA, project, provenance_map
from acs_plan_review import PlanError, canonical, digest

SCHEMA = "acs.plan-pdf-export/1.0"
MODE = "DETERMINISTIC_APPROVED_FROZEN_BASELINE_ONLY"
PDF_SCOPE = "SPACE_BOUNDARIES_ONLY"
PAGE_W = 841.89  # A4 landscape, points
PAGE_H = 595.28
MARGIN = 42.0
HEADER_H = 44.0
FOOTER_H = 34.0


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path]:
    out = Path(out_path)
    if not out.name or out.suffix.lower() != ".pdf":
        raise PlanError("INVALID_OUTPUT_PATH", "Approved plan PDF export emits .pdf only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "PDF output directory must already exist")
    sidecar = Path(str(out) + ".baseline.json")
    for path in (out, sidecar):
        if path.exists() and path.is_symlink():
            raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing a symlinked PDF artifact/receipt path")
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
                        "PDF provenance does not match approved canonical space identities")


def _pdf_text(value: Any) -> str:
    """Return safe ASCII text for a base-14 PDF string literal."""
    text = str(value)
    return "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in text)


def _pdf_escape(value: Any) -> str:
    return _pdf_text(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _num(value: float) -> str:
    if not math.isfinite(value):
        raise PlanError("INVALID_PDF_GEOMETRY", "PDF projection contains non-finite geometry")
    value = 0.0 if abs(value) < 0.0000005 else value
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _page_stream(projection: dict, page_number: int, total_pages: int,
                 *, revision_id: str, model_hash: str, provenance_hash: str) -> tuple[bytes, dict]:
    site = projection.get("site")
    if not isinstance(site, dict):
        raise PlanError("INVALID_PDF_GEOMETRY", "Projected plan has no site geometry")
    width, depth = site.get("w"), site.get("d")
    if (type(width) not in (int, float) or type(depth) not in (int, float)
            or not math.isfinite(width) or not math.isfinite(depth)
            or width <= 0 or depth <= 0):
        raise PlanError("INVALID_PDF_GEOMETRY", "PDF requires positive measured site width/depth")

    draw_w = PAGE_W - 2 * MARGIN
    draw_h = PAGE_H - 2 * MARGIN - HEADER_H - FOOTER_H
    scale = min(draw_w / width, draw_h / depth)
    origin_x = MARGIN + (draw_w - width * scale) / 2
    origin_y = MARGIN + FOOTER_H + (draw_h - depth * scale) / 2
    level_index = projection.get("level_index")

    commands = [
        "q",
        "0 G 0 g",
        "0.8 w",
        "BT /F1 12 Tf",
        f"{_num(MARGIN)} {_num(PAGE_H - MARGIN + 8)} Td",
        f"(ACS Frozen Baseline - Level {_pdf_escape(level_index)} - Page {page_number}/{total_pages}) Tj",
        "ET",
        "BT /F1 7 Tf",
        f"{_num(MARGIN)} {_num(PAGE_H - MARGIN - 7)} Td",
        f"(Revision {_pdf_escape(revision_id)} | Model {_pdf_escape(model_hash[:20])} | Provenance {_pdf_escape(provenance_hash[:20])}) Tj",
        "ET",
        f"{_num(origin_x)} {_num(origin_y)} {_num(width * scale)} {_num(depth * scale)} re S",
    ]

    spaces = []
    primitives = projection.get("primitives")
    if not isinstance(primitives, list):
        raise PlanError("INVALID_PDF_GEOMETRY", "Projected plan has no primitive list")
    for ordinal, item in enumerate(primitives, 1):
        if not isinstance(item, dict):
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space primitive is malformed")
        rect = item.get("rect_xz_m")
        if (not isinstance(rect, list) or len(rect) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in rect)):
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space rectangle is malformed")
        x, z, w, d = rect
        if w <= 0 or d <= 0:
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space rectangle must be positive")
        px = origin_x + x * scale
        py = origin_y + (depth - (z + d)) * scale
        pw, ph = w * scale, d * scale
        commands.append(f"{_num(px)} {_num(py)} {_num(pw)} {_num(ph)} re S")
        label_x = px + pw / 2
        label_y = py + ph / 2
        font_size = max(5.5, min(9.0, min(pw, ph) * 0.12))
        area = item.get("space_rect_area_m2")
        area_text = f"{float(area):.2f} m2" if type(area) in (int, float) and math.isfinite(area) else "area ?"
        commands.extend([
            f"BT /F1 {_num(font_size)} Tf {_num(label_x - 13)} {_num(label_y)} Td (S{ordinal}) Tj ET",
            f"BT /F1 5.5 Tf {_num(label_x - 18)} {_num(label_y - 8)} Td ({_pdf_escape(area_text)}) Tj ET",
        ])
        source_id = item.get("source_id")
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        if not isinstance(source_id, str) or not source_id:
            raise PlanError("PROVENANCE_MISMATCH", "PDF primitive is missing a source_id")
        spaces.append({
            "ordinal": ordinal,
            "source_id": source_id,
            "source": source,
            "label": item.get("label"),
            "space_rect_area_m2": area,
            "rect_xz_m": rect,
        })

    commands.extend([
        "BT /F1 6.5 Tf",
        f"{_num(MARGIN)} {_num(MARGIN - 2)} Td",
        "(SCHEMATIC SPACE BOUNDARIES ONLY - NOT FOR CONSTRUCTION - REGULATORY COMPLIANCE NOT VERIFIED) Tj",
        "ET",
        "Q",
    ])
    stream = ("\n".join(commands) + "\n").encode("ascii")
    manifest = {
        "page_number": page_number,
        "level_index": level_index,
        "site_w_m": width,
        "site_d_m": depth,
        "scale_points_per_m": round(scale, 8),
        "space_count": len(spaces),
        "spaces": spaces,
    }
    manifest["projection_hash"] = digest({
        "scope": projection.get("scope"),
        "revision_id": projection.get("revision_id"),
        "model_hash": projection.get("model_hash"),
        "level_index": level_index,
        "site": site,
        "primitives": primitives,
        "provenance_hash": projection.get("provenance_hash"),
        "requirements_hash": projection.get("requirements_hash"),
    })
    return stream, manifest


def _build_pdf(page_streams: list[bytes], *, revision_id: str, model_hash: str,
               requirements_hash: str, provenance_hash: str, page_manifest_hash: str) -> bytes:
    """Build a small deterministic PDF 1.4 document using only the standard library."""
    if not page_streams:
        raise PlanError("INVALID_PDF_GEOMETRY", "PDF requires at least one canonical level")

    objects: list[bytes | None] = [None, None]  # catalog, pages tree
    font_id = len(objects) + 1
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    for stream in page_streams:
        content_id = len(objects) + 1
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream")
        page_id = len(objects) + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )

    info_id = len(objects) + 1
    title = _pdf_escape(f"ACS Frozen Baseline {revision_id}")
    subject = _pdf_escape(
        f"model={model_hash};requirements={requirements_hash};provenance={provenance_hash};pages={page_manifest_hash};scope={PDF_SCOPE}"
    )
    objects.append(f"<< /Title ({title}) /Subject ({subject}) /Creator (ACS Plan-first v2 deterministic exporter) >>".encode("ascii"))
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("ascii")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        if obj is None:
            raise PlanError("PDF_EXPORT_FAILED", "Internal PDF object graph is incomplete")
        offsets.append(len(out))
        out.extend(f"{number} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


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


def export_approved_pdf(workspace: PlanLockWorkspace, revision_id: str,
                        out_path: str | os.PathLike[str], *, overwrite: bool = False) -> dict:
    """Export exact approved 2D space boundaries as a hash-bound multi-page PDF."""
    if not isinstance(workspace, PlanLockWorkspace):
        raise PlanError("INVALID_WORKSPACE", "PDF export requires a PlanLockWorkspace")
    out, sidecar = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing PDF artifact or receipt")

    # Approval authority boundary first: drafts must fail before projection/export.
    handoff = workspace.handoff(revision_id)
    bound = workspace.get(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    baseline = json.loads(canonical(handoff.get("baseline")))
    before_json = canonical(building)
    before_hash = digest(building)
    if baseline.get("revision_id") != revision_id:
        raise PlanError("BASELINE_CHANGED", "Approved PDF baseline revision identity changed")
    if baseline.get("model_hash") != before_hash or bound.model_hash != before_hash:
        raise PlanError("BASELINE_CHANGED", "Approved PDF model hash does not match its receipt")

    provenance = provenance_map(bound.revision)
    _verify_space_map_matches_handoff(handoff.get("source_map"), provenance)
    source_map = json.loads(canonical(provenance["entries"]))
    source_map_hash = digest(source_map)

    levels = building.get("levels")
    if not isinstance(levels, list) or not levels:
        raise PlanError("INVALID_PDF_GEOMETRY", "Approved baseline has no canonical levels")
    level_indices = []
    for row in levels:
        if not isinstance(row, dict) or type(row.get("index")) is not int:
            raise PlanError("INVALID_PDF_GEOMETRY", "Approved baseline level identity is malformed")
        if row["index"] in level_indices:
            raise PlanError("INVALID_PDF_GEOMETRY", "Approved baseline level indices must be unique")
        level_indices.append(row["index"])

    streams: list[bytes] = []
    pages: list[dict] = []
    for page_number, level_index in enumerate(level_indices, 1):
        projected = project(bound.revision, level_index)
        if (projected.get("revision_id") != revision_id
                or projected.get("model_hash") != before_hash
                or projected.get("provenance_hash") != provenance["provenance_hash"]):
            raise PlanError("BASELINE_CHANGED", "PDF projection detached from Frozen Baseline")
        stream, manifest = _page_stream(
            projected, page_number, len(level_indices), revision_id=revision_id,
            model_hash=before_hash, provenance_hash=provenance["provenance_hash"])
        streams.append(stream)
        pages.append(manifest)

    if canonical(building) != before_json or digest(building) != before_hash:
        raise PlanError("EXPORT_MUTATED_BASELINE", "PDF export changed the approved canonical plan")
    page_manifest_hash = digest(pages)
    pdf = _build_pdf(
        streams, revision_id=revision_id, model_hash=before_hash,
        requirements_hash=provenance["requirements_hash"],
        provenance_hash=provenance["provenance_hash"],
        page_manifest_hash=page_manifest_hash)
    if not pdf.startswith(b"%PDF-1.4") or not pdf.rstrip().endswith(b"%%EOF"):
        raise PlanError("PDF_EXPORT_FAILED", "Generated PDF envelope is invalid")

    receipt = {
        "schema": SCHEMA,
        "mode": MODE,
        "pdf_scope": PDF_SCOPE,
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
        "page_manifest_hash": page_manifest_hash,
        "pages": pages,
        "provider_calls": 0,
        "replanning_calls": 0,
        "construction_approved": False,
        "regulatory_compliance": "NOT_VERIFIED",
        "structural_safety": "NOT_VERIFIED",
        "fire_life_safety_compliance": "NOT_VERIFIED",
    }

    temp_pdf = None
    temp_receipt = None
    try:
        temp_pdf = _publish_bytes_atomic(out, pdf, suffix=".pdf")
        receipt["artifact_sha256"] = _artifact_sha(temp_pdf)
        receipt["artifact_bytes"] = temp_pdf.stat().st_size
        canonical(receipt)
        temp_receipt = _publish_text_atomic(sidecar, canonical(receipt), suffix=".baseline.json")
        if not overwrite and (out.exists() or sidecar.exists()):
            raise PlanError("OUTPUT_EXISTS", "PDF output appeared before atomic publication")
        os.replace(temp_pdf, out)
        temp_pdf = None
        os.replace(temp_receipt, sidecar)
        temp_receipt = None
        return json.loads(canonical(receipt))
    finally:
        for path in (temp_pdf, temp_receipt):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def verify_pdf_export(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify PDF bytes plus the Frozen-Baseline provenance sidecar."""
    out, sidecar = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_PDF_ARTIFACT", "PDF artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "PDF baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != MODE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown PDF baseline receipt")
    if receipt.get("pdf_scope") != PDF_SCOPE:
        raise PlanError("INVALID_BASELINE_RECEIPT", "PDF receipt does not declare the exact Plan-first scope")
    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "PDF artifact bytes no longer match the approved receipt")
    payload = out.read_bytes()
    if not payload.startswith(b"%PDF-1.4") or not payload.rstrip().endswith(b"%%EOF"):
        raise PlanError("INVALID_PDF_ARTIFACT", "PDF envelope is malformed")
    marker_text = payload.decode("latin-1", errors="strict")
    for value in (receipt.get("revision_id"), receipt.get("model_hash"),
                  receipt.get("requirements_hash"), receipt.get("provenance_hash"),
                  receipt.get("page_manifest_hash")):
        if not isinstance(value, str) or value not in marker_text:
            raise PlanError("PROVENANCE_MISMATCH", "PDF metadata is detached from its Frozen Baseline receipt")
    if digest(receipt.get("source_map")) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "PDF source map hash does not match the receipt")
    if receipt.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise PlanError("PROVENANCE_MISMATCH", "Unknown plan provenance schema in PDF receipt")
    reconstructed = {
        "schema": receipt["provenance_schema"],
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "entries": receipt.get("source_map"),
    }
    if digest(reconstructed) != receipt.get("provenance_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "PDF plan provenance hash does not match its source map")
    pages = receipt.get("pages")
    if not isinstance(pages, list) or not pages or digest(pages) != receipt.get("page_manifest_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "PDF page manifest hash does not match the receipt")
    return {
        "ok": True,
        "artifact_sha256": actual_sha,
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "pdf_scope": receipt.get("pdf_scope"),
        "page_count": len(pages),
    }
