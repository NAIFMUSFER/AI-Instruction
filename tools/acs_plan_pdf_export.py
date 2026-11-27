"""Approved Frozen-Baseline-only PDF plan export for ACS Plan-first v2.

The PDF is a deterministic review artifact derived from the exact canonical plan
that has already crossed :class:`acs_plan_lock_binding.PlanLockWorkspace`'s
approval boundary. It does not call an LLM, CAD engine, BIM compiler, regulator,
or geometry repair/replanning path. One page is emitted per canonical level.

Each page is a plan sheet (ISO A-series, standard scale such as 1:100) drawn by
:mod:`acs_plan_drafting` from the exact canonical facts that the projection and
the 3D compiler use: walls at the canonical thickness, doors, windows, stairs,
dimension chains, room tags with net area, north arrow, scale bar and a title
block with an area schedule. Door swing side/hand are disclosed drafting
defaults; no structural grid, column or MEP is invented. All text uses an
embedded Unicode font with Arabic shaping, bidirectional ordering and logical
ActualText. Room numbers (S1, S2, ...) and the hash-bound UTF-8 sidecar
preserve identity.

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


def _level_title(projection: dict) -> str:
    """Title follows the explicit canonical level kind in this bound projection."""
    index = _pdf_escape(projection.get("level_index"))
    if projection.get("level_kind") == "roof":
        return f"Roof deck, unoccupied - Level {index}"
    return f"Level {index}"


_AR_ORDINALS = ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر")


def _arabic_level_title(projection: dict) -> str:
    """Arabic page title: «مخطط الدور الأرضي», «مخطط السطح (غير مشغول)»."""
    index = projection.get("level_index")
    if projection.get("level_kind") == "roof":
        return "مخطط السطح (غير مشغول)"
    if type(index) is not int:
        return "مخطط الدور"
    if index == 0:
        return "مخطط الدور الأرضي"
    if 1 <= index <= len(_AR_ORDINALS):
        return "مخطط الدور " + _AR_ORDINALS[index - 1]
    return "مخطط الدور %d" % index


MM = 72.0 / 25.4  # PDF points per millimetre


def _hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(round(int(value[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4))


class _PdfSheet:
    """Content-stream writer for one sheet; input is paper millimetres (y down)."""

    def __init__(self, height_mm: float, font):
        import acs_drafting_standards as STD
        self.std = STD
        self.h = height_mm
        self.font = font
        self.out: list[str] = []
        self.stroke_state = None

    def xy(self, pt) -> str:
        return "%s %s" % (_num(pt[0] * MM), _num((self.h - pt[1]) * MM))

    def stroke_style(self, layer: str, weight: float | None = None) -> None:
        spec = self.std.LAYERS[layer]
        dash = self.std.LINETYPE_MM[spec["lt"]]
        state = (spec["svg"], weight or spec["lw"], dash)
        if state == self.stroke_state:
            return
        self.stroke_state = state
        r, g, b = _hex_rgb(spec["svg"])
        pattern = " ".join(_num((v if v else 0.2) * MM) for v in dash)
        self.out.append("%s %s %s RG %s w [%s] 0 d" % (_num(r), _num(g), _num(b), _num(state[1] * MM), pattern))

    def lines(self, layer: str, segments: list) -> None:
        if not segments:
            return
        self.stroke_style(layer)
        self.out.append(" ".join("%s m %s l" % (self.xy(a), self.xy(b)) for a, b in segments) + " S")

    def arc(self, layer: str, c, start, end) -> None:
        self.stroke_style(layer)
        a0 = math.atan2(start[1] - c[1], start[0] - c[0])
        a1 = math.atan2(end[1] - c[1], end[0] - c[0])
        delta = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        r = math.hypot(start[0] - c[0], start[1] - c[1])
        self.out.append(self._arc_path(c, r, a0, delta, move=True) + " S")

    def _arc_path(self, c, r, a0, delta, move) -> str:
        parts = []
        steps = max(1, int(math.ceil(abs(delta) / (math.pi / 2) - 1e-9)))
        step = delta / steps
        kappa = 4.0 / 3.0 * math.tan(step / 4.0)
        angle = a0
        if move:
            parts.append("%s m" % self.xy((c[0] + r * math.cos(angle), c[1] + r * math.sin(angle))))
        for _ in range(steps):
            b0 = (c[0] + r * math.cos(angle), c[1] + r * math.sin(angle))
            b3 = (c[0] + r * math.cos(angle + step), c[1] + r * math.sin(angle + step))
            b1 = (b0[0] - kappa * r * math.sin(angle), b0[1] + kappa * r * math.cos(angle))
            b2 = (b3[0] + kappa * r * math.sin(angle + step), b3[1] - kappa * r * math.cos(angle + step))
            parts.append("%s %s %s c" % (self.xy(b1), self.xy(b2), self.xy(b3)))
            angle += step
        return " ".join(parts)

    def fill_loops(self, color: str, loops: list) -> None:
        r, g, b = _hex_rgb(color)
        path = " ".join(" ".join(("%s m" if i == 0 else "%s l") % self.xy(pt) for i, pt in enumerate(loop)) + " h"
                        for loop in loops)
        self.out.append("%s %s %s rg %s f*" % (_num(r), _num(g), _num(b), path))

    def circle(self, layer: str, c, r, fill: bool) -> None:
        self.stroke_style(layer)
        path = self._arc_path(c, r, 0.0, 2 * math.pi - 1e-9, move=True) + " h"
        self.out.append(("0.067 g %s f" if fill else "%s S") % path)

    def poly(self, layer: str, pts: list, fill: bool, weight: float | None = None) -> None:
        self.stroke_style(layer, weight)
        path = " ".join(("%s m" if i == 0 else "%s l") % self.xy(pt) for i, pt in enumerate(pts)) + " h"
        if fill:
            self.out.append("0.067 g %s f" % path)
        elif layer == "A-ANNO-SYMB":
            self.out.append("1 g %s B" % path)
        else:
            self.out.append("%s S" % path)

    def text(self, text: str, at, size_mm: float, anchor: str = "start", rotate: float = 0.0,
             halo: bool = False) -> None:
        from acs_pdf_text import PdfTextError  # noqa: F401  (raised by shape)
        logical, visual, width_em = self.font.shape(text)
        size_mm = self.std.font_size_mm(size_mm)  # lettering (cap) height -> em size
        width = width_em * size_mm
        theta = math.radians(rotate or 0.0)
        dx, dy = math.cos(theta), -math.sin(theta)        # baseline direction on paper (y down)
        nx, ny = -math.sin(theta), -math.cos(theta)       # "up" direction on paper
        shift = {"start": 0.0, "middle": -width / 2, "end": -width}[anchor]
        sx, sy = at[0] + shift * dx, at[1] + shift * dy
        if halo:
            corners = []
            for u, v in ((-0.4, -0.28 * size_mm), (width + 0.4, -0.28 * size_mm),
                         (width + 0.4, 0.9 * size_mm), (-0.4, 0.9 * size_mm)):
                corners.append((sx + u * dx + v * nx, sy + u * dy + v * ny))
            self.out.append("1 g " + " ".join(("%s m" if i == 0 else "%s l") % self.xy(pt)
                                              for i, pt in enumerate(corners)) + " h f")
        glyphs = "".join("%04X" % self.font.codes[ch] for ch in visual)
        actual = ("﻿" + logical).encode("utf-16-be").hex().upper()
        cos, sin = math.cos(theta), math.sin(theta)
        self.out.append("/Span << /ActualText <%s> >> BDC\nBT 0 g /F2 %s Tf %s %s %s %s %s Tm <%s> Tj ET\nEMC" % (
            actual, _num(size_mm * MM), _num(cos), _num(sin), _num(-sin), _num(cos),
            self.xy((sx, sy)), glyphs))

    def stream(self) -> bytes:
        return ("q\n" + "\n".join(self.out) + "\nQ\n").encode("ascii")


def _draw_text(sheet: _PdfSheet, op: dict, at) -> None:
    from acs_pdf_text import PdfTextError
    try:
        sheet.text(op["text"], at, op["size"], op["anchor"], op.get("rotate") or 0.0, op.get("halo", False))
    except PdfTextError as exc:
        if op.get("optional"):
            return
        raise PlanError('PDF_TEXT_UNSUPPORTED',
            'يحتوي اسم فراغ على محارف لا يدعمها خط PDF. استخدم أسماء عربية أو لاتينية؛ تبقى الأسماء الأصلية في ملف المراجعة.') from exc


def _page_stream(projection: dict, page_number: int, total_pages: int,
                 *, revision_id: str, model_hash: str, provenance_hash: str,
                 unicode_font, model: dict, sheet: dict) -> tuple[bytes, dict]:
    import acs_plan_drafting as D
    site = projection.get("site")
    if not isinstance(site, dict):
        raise PlanError("INVALID_PDF_GEOMETRY", "Projected plan has no site geometry")
    width, depth = site.get("w"), site.get("d")
    if (type(width) not in (int, float) or type(depth) not in (int, float)
            or not math.isfinite(width) or not math.isfinite(depth)
            or width <= 0 or depth <= 0):
        raise PlanError("INVALID_PDF_GEOMETRY", "PDF requires positive measured site width/depth")
    level_index = projection.get("level_index")
    primitives = projection.get("primitives")
    if not isinstance(primitives, list):
        raise PlanError("INVALID_PDF_GEOMETRY", "Projected plan has no primitive list")
    for item in primitives:
        if not isinstance(item, dict):
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space primitive is malformed")
        rect = item.get("rect_xz_m")
        if (not isinstance(rect, list) or len(rect) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in rect)):
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space rectangle is malformed")
        if rect[2] <= 0 or rect[3] <= 0:
            raise PlanError("INVALID_PDF_GEOMETRY", "Projected space rectangle must be positive")
        if not isinstance(item.get("source_id"), str) or not item.get("source_id"):
            raise PlanError("PROVENANCE_MISMATCH", "PDF primitive is missing a source_id")

    paper = D.Paper(sheet)
    draft = D.level_drafting(model, level_index, primitives, projection.get("source_map") or [])
    ops = D.plan_ops(draft, paper)
    title_en = _level_title(projection) if projection.get("level_kind") == "roof" else _level_title(projection) + " floor plan"
    pdf = _PdfSheet(sheet["paper_mm"][1], unicode_font)
    to_paper = paper.to_paper

    x0, y0 = to_paper((0.0, 0.0))
    x1, y1 = to_paper((width, depth))
    pdf.poly("C-PROP", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], False)
    pdf.lines("A-AREA-BNDY", [(to_paper(op["a"]), to_paper(op["b"])) for op in ops["areas"]])
    for op in ops["fills"]:
        pdf.fill_loops(pdf.std.LAYERS[op["layer"]]["svg"], [[to_paper(pt) for pt in loop] for loop in op["loops"]])
    batches: dict = {}
    for op in ops["lines"]:
        if op["op"] == "line":
            batches.setdefault(op["layer"], []).append((to_paper(op["a"]), to_paper(op["b"])))
        elif op["op"] == "loops":
            for loop in op["loops"]:
                pts = [to_paper(pt) for pt in loop]
                batches.setdefault(op["layer"], []).extend(zip(pts, pts[1:] + pts[:1]))
    for layer, segments in batches.items():
        pdf.lines(layer, segments)
    for op in ops["lines"]:
        if op["op"] == "arc":
            pdf.arc(op["layer"], to_paper(op["c"]), to_paper(op["from"]), to_paper(op["to"]))
    dim_lines, dim_texts = [], []
    for op in ops["dims"]:
        for part in D.expand_dim(op, paper):
            if part["op"] == "line":
                dim_lines.append((to_paper(part["a"]), to_paper(part["b"])))
            else:
                dim_texts.append(part)
    pdf.lines("A-ANNO-DIMS", dim_lines)
    for op in ops["symbols"]:
        if op["op"] == "circle":
            pdf.circle(op["layer"], to_paper(op["c"]), op["r"] * paper.k, op.get("fill", False))
        else:
            pdf.poly(op["layer"], [to_paper(pt) for pt in op["pts"]], op.get("fill", False))
    for op in dim_texts + ops["texts"]:
        _draw_text(pdf, op, to_paper(op["at"]))
    for room in ops["rooms"]:
        for op in room["texts"]:
            _draw_text(pdf, op, to_paper(op["at"]))
    sheet_ops = D.sheet_ops(draft, sheet, paper, model=model, page_number=page_number, page_count=total_pages,
                            title_en=title_en, revision_id=revision_id, model_hash=model_hash,
                            provenance_hash=provenance_hash, schedule=True)
    pdf.lines("A-ANNO-TTLB", [(op["a"], op["b"]) for op in sheet_ops if op["op"] == "line" and op["layer"] == "A-ANNO-TTLB"])
    pdf.lines("A-ANNO-TEXT", [(op["a"], op["b"]) for op in sheet_ops if op["op"] == "line" and op["layer"] == "A-ANNO-TEXT"])
    for op in sheet_ops:
        if op["op"] == "poly":
            pdf.poly(op["layer"], op["pts"], op.get("fill", False), op.get("weight"))
        elif op["op"] == "circle":
            pdf.circle(op["layer"], op["c"], op["r"], op.get("fill", False))
    for op in sheet_ops:
        if op["op"] == "text":
            _draw_text(pdf, op, op["at"])

    tags = {tag["source_id"]: tag for tag in draft["tags"]}
    spaces = []
    for ordinal, item in enumerate(primitives, 1):
        tag = tags[item["source_id"]]
        spaces.append({
            "ordinal": ordinal,
            "number": tag["number"],
            "source_id": item["source_id"],
            "source": item.get("source") if isinstance(item.get("source"), dict) else {},
            "label": item.get("label"),
            "space_rect_area_m2": item.get("space_rect_area_m2"),
            "rect_xz_m": item["rect_xz_m"],
            "net_area_m2": tag["net_area_m2"],
            "clear_size_m": [tag["clear_w_m"], tag["clear_d_m"]],
        })
    manifest = {
        "page_number": page_number,
        "level_index": level_index,
        "site_w_m": width,
        "site_d_m": depth,
        "scale_points_per_m": round(paper.k * MM, 8),
        "space_count": len(spaces),
        "spaces": spaces,
        "sheet": {"paper": sheet["paper"], "paper_mm": sheet["paper_mm"], "scale": sheet["scale"],
                  "standard_scale": sheet["standard_scale"], "sheet_number": "A-%d" % (100 + page_number)},
        "drafting": D.summary(draft, sheet),
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
    return pdf.stream(), manifest


def _build_pdf(page_streams: list[bytes], *, revision_id: str, model_hash: str,
               requirements_hash: str, provenance_hash: str, page_manifest_hash: str,
               unicode_font=None, page_sizes_mm: list | None = None) -> bytes:
    """Build a small deterministic PDF 1.4 document using only the standard library."""
    import zlib
    if not page_streams:
        raise PlanError("INVALID_PDF_GEOMETRY", "PDF requires at least one canonical level")
    sizes = page_sizes_mm or [(PAGE_W / MM, PAGE_H / MM)] * len(page_streams)

    objects: list[bytes | None] = [None, None]  # catalog, pages tree
    font_id = len(objects) + 1
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    unicode_id = unicode_font.append_objects(objects) if unicode_font is not None else None
    unicode_resource = f' /F2 {unicode_id} 0 R' if unicode_id is not None else ''
    page_ids: list[int] = []
    for stream, (w_mm, h_mm) in zip(page_streams, sizes):
        packed = zlib.compress(stream, 9)
        content_id = len(objects) + 1
        objects.append(b"<< /Length " + str(len(packed)).encode("ascii") + b" /Filter /FlateDecode >>\nstream\n"
                       + packed + b"\nendstream")
        page_id = len(objects) + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_mm * MM:.2f} {h_mm * MM:.2f}] "
            f"/Resources << /Font << /F1 {font_id} 0 R{unicode_resource} >> >> /Contents {content_id} 0 R >>".encode("ascii")
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
    from acs_pdf_text import PdfUnicodeFont
    unicode_font = PdfUnicodeFont()
    import acs_plan_drafting
    sheet = acs_plan_drafting.sheet_for(bound.revision.model)  # one paper and scale for the whole set
    for page_number, level_index in enumerate(level_indices, 1):
        projected = project(bound.revision, level_index)
        if (projected.get("revision_id") != revision_id
                or projected.get("model_hash") != before_hash
                or projected.get("provenance_hash") != provenance["provenance_hash"]):
            raise PlanError("BASELINE_CHANGED", "PDF projection detached from Frozen Baseline")
        stream, manifest = _page_stream(
            projected, page_number, len(level_indices), revision_id=revision_id,
            model_hash=before_hash, provenance_hash=provenance["provenance_hash"],
            unicode_font=unicode_font, model=bound.revision.model, sheet=sheet)
        streams.append(stream)
        pages.append(manifest)

    if canonical(building) != before_json or digest(building) != before_hash:
        raise PlanError("EXPORT_MUTATED_BASELINE", "PDF export changed the approved canonical plan")
    page_manifest_hash = digest(pages)
    pdf = _build_pdf(
        streams, revision_id=revision_id, model_hash=before_hash,
        requirements_hash=provenance["requirements_hash"],
        provenance_hash=provenance["provenance_hash"],
        page_manifest_hash=page_manifest_hash, unicode_font=unicode_font,
        page_sizes_mm=[tuple(sheet["paper_mm"])] * len(streams))
    if not pdf.startswith(b"%PDF-1.4") or not pdf.rstrip().endswith(b"%%EOF"):
        raise PlanError("PDF_EXPORT_FAILED", "Generated PDF envelope is invalid")

    receipt = {
        "schema": SCHEMA,
        "mode": MODE,
        "pdf_scope": PDF_SCOPE,
        "text_profile": "EMBEDDED_UNICODE_ARABIC_RTL_ACTUALTEXT",
        "drawing_content": acs_plan_drafting.SCOPE,
        "drafting_schema": acs_plan_drafting.SCHEMA,
        "sheet": {"paper": sheet["paper"], "paper_mm": sheet["paper_mm"], "scale": sheet["scale"],
                  "standard_scale": sheet["standard_scale"]},
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
