# Phase 9 — Final Report

**Construction Documentation & Professional Drawing Output Engine**
Executed in the build sandbox. Every number below came from a command that was actually
run. Nothing here is projected.

---

## 1. Architecture

```
CANONICAL MODEL → ARCH / STRUCT / MEP / FLS / COORDINATION → DOCUMENTATION COMPILER
  → VIEW DEFINITION → DRAWING GEOMETRY → ANNOTATION → SHEET COMPOSITION → EXPORT
```

No return arrow. `documentation_is_read_only: true`; `writes_to_model`,
`reverse_write_allowed` and `mutates_engineering_model` all `false`. `build_view` raises if
the project hash moves while it runs. An edit reaches the model only through the Phase 5
authoring path. Phases 1–8 were not redesigned and no second engineering model exists.

**Result: PASS.**

## 2. Files created or changed

| File | Lines | Status |
| --- | --- | --- |
| `acs_docs.json` | 670 | new — 146 top-level keys |
| `acs_docs.py` | 2,168 | new |
| `tools/build_docs_browser.py` | 1,928 | new — injects 111 KB of JavaScript, the panel DOM and styles |
| `tests/phase9/test_docs.py` | 1,127 | new — contract and Tests A–N |
| `tests/phase9/test_parity.js` + `parity/` | 548 | new |
| `tests/phase9/test_docs_browser.js` | 367 | new |
| `tests/phase9/benchmark_docs.py` | 128 | new |
| `tests/phase9/make_outputs.py` | 205 | new |
| `tests/phase9/lib_docs_fixtures.py` / `.js` | 127 | new |
| `tests/phase9/run_all.sh` | — | new |
| `tests/security/test_security.py` | +130 | extended — S-D1…S-D29 |
| `tests/deploy/verify_deploy.py` | +35 | extended — Phase 9 closure, no orphaned file |
| `tests/phase3/lib/build_browser_page.js` | +10 | extended — injects the DOCS DOM and styles |
| `PHASE9-DOCUMENTATION.md`, `PHASE9-FINAL-REPORT.md`, `PHASE9-DEPLOYMENT-MANIFEST.md`, `PHASE9-PRODUCTION-VERIFICATION.md` | — | new |

Phase 1–8 source files were **not** modified.

## 3. Documentation schema

146 keys: 12 view types with explicit support, 5 support states, 8 disciplines, 24
categories, 4 geometry classes, 11 dimension types with 3 provenance classes, 12 annotation
types with 4 provenance classes, 12 schedule types with declared columns, 16 quantity types
with 3 coverage states, 5 paper sizes, 5 scales, 2 scale modes, 5 documentation states, 3
export formats, 29 issue codes (15 blocking), 21 unsafe patterns, 15 limits, 24 hard-stop
boundaries.

## 4. View engine

Explicit support per type; `THREE_D_REFERENCE` is `NOT_SUPPORTED` and refused. Unknown view
type, level, scale, discipline, orientation, cut plane, crop and non-finite coordinates are
each refused with a typed issue rather than defaulted. Deterministic identities: same model
plus same definition yields the same `view_id`; no random UUIDs.

**Result: PASS.**

## 5. Floor plans (TEST A)

Derived from `acs_arch` compiled geometry. Every drawn wall, space, door and window exists
in the compiled architecture; every architectural wall on the level is drawn; no element is
invented. A shared wall is one wall and is never redrawn per room. Unresolved exposure is
carried through unchanged. No door swing is invented where the model says
`not_specified`. Not a rasterised viewport — element geometry.

**Result: PASS.**

## 6. Elevations (TEST B)

Four elevations produced, each showing only represented external openings, each recording
the building rotation it applied. Level lines come from real level elevations. No
photorealistic content enters the engineering elevation layer. An opening with no stated
width is not drawn at an invented size.

**Result: PASS.**

## 7. Sections (TEST C)

Mathematical intersection of a vertical plane with the geometry. Cut, projected,
beyond-depth and unresolved reported separately; every wall reported as cut is verified to
span the plane; different positions cut different elements. A section through the stair void
splits the slab strip, and a section away from it leaves the slab whole.

A real defect was found and fixed: the parallel test was inverted, so walls running along
the cut axis were classified projected instead of cut.

**Result: PASS.**

## 8. Dimensions

Full provenance on every dimension. Display rounding never modifies `exact_value`.
An unknown value yields `measurement_status: UNKNOWN` with no display value — **a render
fallback is never promoted to a measurement**, asserted against a fixture that really has a
null value beside a non-null fallback. Four declared chain policies. Level datums from real
elevations; FFL, SSL, TOS and TOC never emitted. Grid spacings only from represented grids.

**Result: PASS — no fake dimension.**

## 9. Annotations

Twelve types, four provenance classes. Generated text is never presented as user-authored.
User notes live in documentation state and change no engineering semantics.

**Result: PASS.**

## 10. Schedules (TESTS D, E, F, G, H)

Room schedule: zero phantom rooms, zero missing represented rooms, every row bound to its
source element and model hash. Door and window schedules map to canonical openings with
deterministic tags. **Clear width is never filled in from nominal width** — all eleven
doors state nominal and none states clear, and all eleven clear-width cells read
`NOT_SPECIFIED`. Fire rating and material likewise. Structural schedules report represented
columns, beams and foundations with unknown sections and materials left unknown, and no
reinforcement or sizing anywhere. MEP schedules report represented equipment with no CFM,
flow, pressure or capacity. FLS schedules report represented devices with **none of the
nine forbidden compliance phrases** present.

**Result: PASS.**

## 11. Quantities (TEST J)

Counts and measurements cross-checked against the canonical model: rooms, doors, windows,
levels, wall length and space area all match exactly. A discipline with no represented data
reports `NOT_AVAILABLE` with a null quantity rather than a misleading zero; unrouted MEP
makes segment length `PARTIAL`. No cost, rate, price, currency or budget field exists; the
report declares itself neither a bill of quantities nor a cost estimate.

**Result: PASS.**

## 12. Sheets

Five paper sizes, A1 not assumed. Deterministic viewport geometry; overlaps detected and
reported with content never silently moved; a viewport leaving the sheet refused. True scale
reported only when the view fits, otherwise `FIT_TO_SHEET` with no invented scale. Neutral
title block with blank unknowns and no company, engineer, stamp or signature. All four
restricted statuses refused.

**Result: PASS.**

## 13. Revisions and staleness (TEST K)

A model change committed through the Phase 5 authoring path turned every artifact
`STALE_MODEL_CHANGED`. Nothing auto-regenerated, nothing auto-deleted. Explicit regeneration
produced revision B, preserved revision A in append-only history, and the regenerated
drawing and dimension reflect the geometric change. Revision clouds come only from a real
diff and carry no engineering interpretation.

**Result: PASS.**

## 14. Export

**SVG**: real vector geometry, parses as XML, no embedded raster, no script element, bound
to the model hash, marked not a construction drawing. **PDF**: real PDF 1.4 —
`%PDF-` signature, catalogue, page tree, one page per sheet, explicit MediaBox in points
(A3 = 1190.55 pt), uncompressed vector content streams, xref, trailer, `%%EOF`; no CAD
interoperability claimed. **JSON**: views, sheets, schedules, quantities, artifact
identities, provenance and staleness, with `derived_from_ifc: false`. Every export manifest
field present and every file bound to the model hash. **DXF is not implemented and no file
is emitted with a DXF extension.**

**Result: PASS.**

## 15. Security (TEST N)

Seven hostile payloads refused in title blocks and sheet names. Ten inert labels carried as
text with positive proof of inertness: never an object key at any depth, never a canonical
field, escaped in the document. Eleven hostile filenames refused by allow-list; traversal
refused with a typed issue. Oversized notes, non-finite and out-of-bounds coordinates,
malformed definitions, duplicate artifact identities and forged model hashes all handled.
Thirteen malformed view definitions run through the real module: none crashes, every one is
refused with a declared issue code, none moves the model hash. No `eval`, no `exec`, no
`new Function`; the module opens nothing but its own specification.

**Result: PASS.**

## 16. Performance

CPU milliseconds in this sandbox on one run, element counts beside every timing. No frame
rate, no GPU, no 3D rendering measured or claimed.

| Model | Spaces | Drawn | View | Section | Dims | Sched | SVG | PDF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| villa_glazed | 11 | 46 | 0.3 ms | 0.6 ms | 0.5 ms | 0.6 ms | 0.5 ms | 0.4 ms |
| clinic | 5 | 25 | 0.2 ms | 0.2 ms | 0.3 ms | 0.2 ms | 0.3 ms | 0.2 ms |
| warehouse | 4 | 22 | 0.1 ms | 0.2 ms | 0.2 ms | 0.2 ms | 0.2 ms | 0.2 ms |
| clash_mep | 11 | 35 | 0.3 ms | 0.3 ms | 0.6 ms | 0.4 ms | 0.3 ms | 0.3 ms |
| grid_100 | 100 | 521 | 3.7 ms | 3.9 ms | 5.7 ms | 2.7 ms | 5.6 ms | 3.9 ms |
| grid_500 | 500 | 2,561 | 44.1 ms | 38.6 ms | 28.4 ms | 15.5 ms | 30.6 ms | 17.5 ms |
| grid_1000 | 1,000 | 5,111 | 111.0 ms | 116.5 ms | 54.9 ms | 39.1 ms | 52.9 ms | 32.5 ms |

Largest model: 1,000 spaces, 5,111 drawn elements, 3,000 schedule rows, 1,064,806-byte SVG,
367,859-byte PDF.

**Result: PASS.**

## 17. Python ↔ JavaScript parity

```
node tests/phase9/test_parity.js → 72 passed, 0 failed
DOCS PARITY: 17/17 byte-identical
```

Compared across 12 fixture models: view definitions, validity verdicts, plan/elevation/
section geometry, dimensions, annotations, draw operations, SVG bytes and hashes, schedule
rows, quantities, sheet descriptors, title-block refusals, document descriptors, PDF content
streams and MediaBoxes, export manifests, export sets, staleness verdicts, model hashes,
immutability verdicts, safety tables and stated-value readings.

Three divergences found and fixed at contract level: `undefined` keys dropped by
`JSON.stringify` where Python keeps explicit nulls (18 fields); `String(0)` vs `str(0.0)` in
a schedule cell (now the shared formatter); and the comparator's own blindness to
`__proto__` (now `Object.defineProperty` plus a self-test). PDF parity is compared on page
count, MediaBoxes and exact content-stream text with the basis declared —
`SEMANTIC_CONTENT_STREAM` — not waived.

**Result: PASS.**

## 18. Chromium verification

```
node tests/phase3/lib/run_browser.js tests/phase9/test_docs_browser.js
→ {"pass":85,"fail":0} page errors: none
```

Panel and tree; floor-plan viewer rendering a real SVG element with real children bound to
the model hash; section and elevation creation with an undirected elevation refused;
schedule tables with `NOT_SPECIFIED` cells; quantity report with no currency and no cost
field; sheet editor with a movable viewport and a refused restricted status; export
workflow with a manifest bound to the model hash; staleness with nothing auto-regenerating;
hostile labels inert with nothing executing; Arabic RTL with byte-identical drawing
geometry; responsive widths and touch targets.

**Result: PASS.**

## 19. Regression

Every earlier suite re-ran unchanged and passed.

| Suite | Passed | Failed |
| --- | ---: | ---: |
| DOCUMENTATION (`test_docs.py`) | 421 | 0 |
| DOCS PARITY SUITE | 72 | 0 |
| DOCS BROWSER (Node / Chromium) | 4 / 85 | 0 |
| BACKEND/CONFIG SECURITY | 331 | 0 |
| DEPLOY VERIFICATION | 215 | 0 |
| Phase 8 — BIM exchange / parity / browser (Node, Chromium) | 526 / 53 / 4 / 58 | 0 |
| Phase 7 — render contract / targets / security / parity / Chromium | 272 / 93 / 163 / 49 / 242 | 0 |
| Phase 6 — workspace contract / workflow / DOM / security / parity | 113 / 153 / 1 / 167 / 47 | 0 |
| Phase 5 — contract / commands / transactions / revisions / AI / integration / immutability / adversarial / browser / parity | 127 / 180 / 120 / 89 / 67 / 70 / 105 / 519 / 55 / 35 | 0 |
| Phase 4 — scene / navigation / collision / portals / selection / visibility / measurement / immutability / adversarial / regression / parity | 49 / 39 / 73 / 45 / 113 / 145 / 131 / 135 / 457 / 23 / 17 | 0 |
| Phase 3 — visual foundation / adversarial / dev API | 211 / 115 / 31 | 0 |

```
sh tests/phase9/run_all.sh --browser → 8,006 assertions passed → 0 failed → exit 0
```

(The security and deploy suites run once per nested phase runner; the total counts each
execution as it occurred.)

**Result: PASS — no Phase 1–8 invariant regressed.**

## 20. Deployment verification

```
sh tests/deploy/verify_deploy.sh → 215 checks passed, 0 failed
```

The backend closure is computed from the AST, not a hand-maintained list. Phase 9 adds no
backend endpoint and no backend dependency: `acs_docs` is browser-mirrored and
intentionally absent from the container, and the closure check proves the API cannot reach
it. A new check was added so that **every** `acs_*.py` and `acs_*.json` must be classified
as container runtime, browser mirror or declared offline CLI — nothing may be orphaned.

**Result: PASS.**

## 21. Generated artifact inventory

55 files, 389,143 bytes, in `tests/phase9/outputs/`, each bound to its model hash by
`ARTIFACT-MANIFEST.json`.

| Kind | Count |
| --- | ---: |
| VIEW_SVG | 23 |
| SCHEDULE | 14 |
| QUANTITY_REPORT | 6 |
| SHEET_PDF | 6 |
| DOCUMENTATION_PACKAGE | 6 |

Coverage: **villa** — 2 floor plans, 4 elevations, 2 sections, room/door/window schedules,
quantity report, 2 composed sheets, PDF. **hotel** — floor plan, elevation, section,
room/door schedules, quantity report, PDF. **clinic** — floor plan, room/door schedules,
quantity report, PDF. **warehouse** — floor plan, room schedule, quantity report, PDF.
**clash_mep** — floor plan plus structural, MEP and coordination plans on both levels,
column/beam/foundation/MEP-equipment schedules, quantity report, 4-page PDF.
**villa_fls** — floor plan plus FLS plans, device and sign schedules, quantity report, PDF.

All 23 SVG files parse as XML; all 6 PDFs carry a `%PDF-1.4` signature and the page counts
recorded in the manifest.

**Result: PASS.**

## 22. Known limitations

- No construction detailing, reinforcement drawings, fabrication or shop drawings.
- No cost estimating; no bill-of-quantities completeness claim.
- No regulatory approval, code interpretation, occupancy determination or professional stamp.
- No independent CAD validation and no external PDF/SVG validator ran — none exists in this
  sandbox and there is no network. `cad_validated` is `false`.
- Printing is not verified; `print_verified` is `false`.
- DXF is not implemented.
- A section plane is taken on x or z only.
- **A room `name` in the raw model is not surfaced**: `acs_arch` reports the room identifier
  as the space name, and documentation reports what the compiler states rather than reaching
  around it into raw model JSON. Changing that is a Phase 2 decision, not a Phase 9 one.
- **PDF text is WinAnsi**: non-Latin glyphs are substituted in the PDF text layer. The full
  Unicode text is preserved in the SVG and the JSON package. Embedding a Unicode font is
  future work.
- Roof and ceiling plans are `PARTIALLY_SUPPORTED`; `THREE_D_REFERENCE` is `NOT_SUPPORTED`.
- WebGL 3D display remains `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED` (`public/vendor/`
  is empty because the sandbox has no network).

## 23. Explicit confirmations

| # | Confirmation | Verdict |
| --- | --- | --- |
| 1 | NO ENGINEERING MODEL MUTATION FROM DOCUMENTATION | CONFIRMED — model bytes compared across 8 models after full documentation |
| 2 | NO AUTO-FIX | CONFIRMED |
| 3 | NO AUTO-REROUTING | CONFIRMED — an unrouted segment stays unrouted |
| 4 | NO STRUCTURAL DESIGN | CONFIRMED |
| 5 | NO REINFORCEMENT DESIGN | CONFIRMED |
| 6 | NO MEP DESIGN | CONFIRMED |
| 7 | NO FIRE ENGINEERING | CONFIRMED |
| 8 | NO CODE COMPLIANCE INVENTION | CONFIRMED — nine forbidden phrases asserted absent |
| 9 | NO OCCUPANCY INVENTION | CONFIRMED |
| 10 | NO MATERIAL PROPERTY INVENTION | CONFIRMED |
| 11 | NO COST INVENTION | CONFIRMED — ten cost fields and every currency symbol asserted absent |
| 12 | NO PROFESSIONAL APPROVAL CLAIM | CONFIRMED — all four restricted statuses refused |
| 13 | NO AI MODIFICATION OF TECHNICAL DRAWING GEOMETRY | CONFIRMED |
| 14 | NO PHASE 1–8 REGRESSION | CONFIRMED — every earlier suite re-ran and passed |

## 24. DEPLOYMENT DELIVERABLES

- **Full deployable repository:** `AI-Construction-Studio-Phase9.zip`
- **SHA-256:** published in the sidecar `AI-Construction-Studio-Phase9.zip.sha256` and in
  the delivery message. It is deliberately not written into this file, which is inside the
  archive — embedding the digest here would change the archive and invalidate it. Verify
  with `sha256sum -c AI-Construction-Studio-Phase9.zip.sha256`.
- **Deployment manifest:** `PHASE9-DEPLOYMENT-MANIFEST.md`
- **Production verification:** `PHASE9-PRODUCTION-VERIFICATION.md`
- **Deployment validation:** `tests/deploy/verify_deploy.sh` (+ `verify_deploy.py`) — 215
  checks passed, 0 failed
- **Changed-files archive:** not produced; the complete repository archive is the deliverable
- **Frontend production build:** `bash tools/netlify-build.sh` → **EXIT 1**,
  `npm error 403 Forbidden — GET https://registry.npmjs.org/three`.
  **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** The script failed fast rather than
  shipping a partial vendor set, which is the intended behaviour. `public/index.html` is
  committed and needs no build step.
- **Backend production build:** `docker build -t acs-engine .` → **EXIT 1**, no Docker
  daemon. `pip download -r requirements.txt` → **EXIT 1**, no PyPI.
  **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** Statically verified: all 33 `COPY`
  sources resolve, `py_compile` passes on all 20 modules in the image, the backend core
  imports cleanly, and `acs_understand_api` fails only on the third-party `fastapi` that
  `requirements.txt` declares.
- **Live deployment:** **NOT VERIFIED** — nothing was deployed from this sandbox and no live
  URL was tested.

---

## HARD STOP

Phase 9 — Construction Documentation & Professional Drawing Output Engine is complete and
stopped here.

**Not begun, and requiring explicit approval:** Phase 10, cloud collaboration, multi-user
editing, live Revit synchronisation, automatic structural design, automatic MEP design,
automatic fire design, regulatory code automation, autonomous design, AI engineering
auto-edit, construction scheduling, cost estimation.
