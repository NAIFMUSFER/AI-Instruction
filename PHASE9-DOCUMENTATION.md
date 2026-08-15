# Phase 9 — Construction Documentation & Professional Drawing Output Engine

**Documentation reports what the model contains. It never invents engineering
information to make a drawing look complete, and it never writes back.**

---

## 0. The arrow that does not exist

```
CANONICAL MODEL
  → ARCH / STRUCT / MEP / FLS / COORDINATION
    → DOCUMENTATION COMPILER
      → VIEW DEFINITION
        → DRAWING GEOMETRY
          → ANNOTATION
            → SHEET COMPOSITION
              → EXPORT
```

There is no return arrow. `documentation_is_read_only` is `true`, `writes_to_model`,
`reverse_write_allowed` and `mutates_engineering_model` are all `false`, and
`model_hash_inputs` is `["model"]` and nothing else. `build_view` raises if the project
hash moves while it runs. An edit reaches the model only through the Phase 5 authoring
path, exactly as before.

Test L runs every documentation operation — seven view types, twelve schedules,
quantities, sheets, SVG, PDF and the JSON package — across eight models and then compares
the canonical model **bytes**. They are unchanged on every one.

## 1. Files

| File | Lines | Role |
| --- | --- | --- |
| `acs_docs.json` | 670 | the canonical documentation specification — 146 top-level keys |
| `acs_docs.py` | 2,168 | view engine, plan/elevation/section geometry, dimensions, annotations, schedules, quantities, sheets, staleness, SVG, PDF, export |
| `tools/build_docs_browser.py` | 1,928 | injects the JavaScript mirror, the DOCUMENTATION panel and its styles into `public/index.html`; idempotent |
| `tests/phase9/` | 2,502 | contract suite (Tests A–N), parity, browser, benchmark, artifact generator, runner |
| `tests/phase9/outputs/` | — | 55 real artifacts with `ARTIFACT-MANIFEST.json` |

## 2. The rule that shapes every number: a render fallback is not a measurement

The canonical layers carry each value as a triple: `{value, source, render_fallback}`. A
wall whose thickness the model never stated arrives as
`{"value": null, "source": "unknown", "render_fallback": 0.15}` — the fallback exists so
Phase 3 can draw *something*.

Documentation reads `value` and nothing else. `stated()` returns `UNKNOWN` and the
fallback is never substituted — not into a dimension, not into a schedule cell, not into a
quantity. An unknown dimension is emitted with `measurement_status: UNKNOWN` and **no
display value**. An unknown schedule cell displays `NOT_SPECIFIED`. This is asserted
directly against a fixture that genuinely has both a null value and a non-null fallback.

The same discipline produces the sharpest rule in the schedules: **nominal width never
becomes clear width.** The villa states nominal widths for all eleven doors and clear
width for none; all eleven clear-width cells read `NOT_SPECIFIED`. Fire rating and
material likewise. `forbidden_schedule_invention` names each of these substitutions so the
prohibition is data, not prose.

## 3. Views

Twelve view types, each with an explicit support status. Nine are `SUPPORTED`, two are
`PARTIALLY_SUPPORTED` (roof and ceiling plans — outlines where represented, no build-up
and no invented grid), and `THREE_D_REFERENCE` is `NOT_SUPPORTED` and refused, because
this layer owns no raster pipeline. A view type is never claimed supported merely because
the enum exists.

An unknown level, an unknown scale, an elevation without a direction, a section without a
cut plane, a non-finite coordinate and a malformed crop are each **refused with a typed
issue** rather than defaulted.

**Floor plans** derive from `acs_arch` compiled geometry — walls, openings, spaces, slabs,
voids and cores. Every drawn identifier exists in the compiled architecture, and every
architectural wall on the level is drawn. A shared wall keeps its single canonical identity
and is never redrawn per room. No door swing is invented where `swing_status` is
`not_specified`.

**Elevations** project exterior walls and represented external openings onto a vertical
plane, applying the building rotation from the model transform rather than ignoring it. An
opening whose width the model does not state is **not drawn at an invented size** — it
raises a typed issue instead.

**Sections** intersect a vertical plane with the geometry mathematically. Cut, projected,
beyond-depth and unresolved are counted and reported separately. Sections at x=3, x=7 and
x=11 cut genuinely different elements, and every wall reported as cut is verified to span
the cut plane.

A defect worth naming: the first implementation had the parallel test inverted, so walls
running along the cut axis were classified projected instead of cut. The adversarial
fixtures caught it and it was fixed, not tested around.

**Slab voids.** A section through the stair void splits the slab strip; a section away from
it leaves the slab whole. A stair does not appear to pass through an uncut slab.

## 4. Dimensions

Eleven measurement types with full provenance: source elements, exact value, display value,
unit, precision, provenance class and measurement status. **Display rounding never
modifies `exact_value`** — asserted to within 5e-4 on every measured dimension.

Four dimension policies, from `NONE` to `FULL_CHAIN`, so a cluttered chain is a choice
rather than an accident. Level datums come from real architectural level elevations; FFL,
SSL, TOS and TOC are named in `forbidden_datum_labels` and never emitted, because no
corresponding semantic datum exists in the canonical model. Grid spacings are computed only
from represented structural grids — the architectural fixtures have none, and none is
generated to satisfy a drawing convention.

## 5. Annotations

Twelve annotation types, each carrying one of four provenance classes. Generated text is
never presented as user-authored: a room tag is `MODEL_DERIVED`, a door tag is
`DOCUMENTATION_DERIVED`, and a user note is `USER_AUTHORED`. User notes live in
documentation state and change no architectural, structural, MEP or FLS semantics.

## 6. Discipline drawings

**Structural** plans draw represented columns, beams, structural slabs, foundations and
grids. A column spans from its base level to its top level as the model declares, so it
appears on every plan it passes through — read from the represented span, not assumed. No
reinforcement, no sizing, no load and no adequacy claim appears anywhere.

**MEP** plans draw represented equipment, terminals, routed segments and risers. **An
unrouted segment stays unrouted**: it is classified `UNRESOLVED`, drawn not at all, and
reported with a typed issue. No route is fabricated to complete a drawing, and no CFM,
voltage, pressure, flow or duct size is generated.

**Fire and life safety** plans draw represented devices, signs and exits. Nine compliance
phrases — "code compliant", "coverage compliant", "adequate", "protected" and the rest —
are named in the specification and asserted absent from the drawing and the schedule.
Presence is documented; adequacy is never claimed.

**Coordination** plans show existing clash findings as annotations. `AUTO_FIX_CLASH` is a
forbidden panel control and `AUTOMATIC_CLASH_RESOLUTION` is a declared hard-stop boundary.

## 7. Quantities

Sixteen quantity types, each stating unit, source elements, measurement basis and coverage.
Coverage distinguishes `COMPLETE_FOR_REPRESENTED_MODEL`, `PARTIAL` and `NOT_AVAILABLE` — a
discipline with no represented data reports `NOT_AVAILABLE` with a null quantity, not a
misleading zero. Unrouted MEP segments make the segment length `PARTIAL` rather than being
estimated.

The report declares `is_bill_of_quantities: false` and `is_cost_estimate: false`. Ten
cost-shaped field names are forbidden and asserted absent, as is every currency symbol.

## 8. Sheets, title blocks and export

Five paper sizes, and A1 is not assumed for anything. Viewports carry deterministic
geometry; an overlap is **detected and reported, and engineering content is never silently
moved**; a viewport leaving the sheet is refused. A true engineering scale is reported only
when the view actually fits at that scale — otherwise the mode is `FIT_TO_SHEET` and the
scale is reported as absent rather than invented.

The title block is neutral: unknown fields stay blank, and no company name, engineer name,
licence number, stamp, seal or signature is generated. `APPROVED_FOR_CONSTRUCTION`,
`IFC`, `CERTIFIED` and `AS_BUILT` are declared restricted and refused with a typed issue —
the system does not grant itself that authority.

**SVG** is real vector geometry that parses as XML, with no embedded raster and no script
element. **PDF** is a real PDF 1.4 file: `%PDF-` header, catalogue, page tree, one page per
sheet with an explicit MediaBox in points, uncompressed content streams of vector
operators, xref table and trailer, ending `%%EOF`. No CAD interoperability is claimed from
it. **DXF is not implemented and no file is emitted with a DXF extension** — a renamed file
is not an exchange format.

The JSON package carries the source model hash, views, sheets, schedules, quantities,
artifact identities, provenance and staleness, and states `derived_from_ifc: false` —
documentation consumes the canonical model, never an exported IFC file.

## 9. Staleness and regeneration

When the model moves, every artifact turns `STALE_MODEL_CHANGED`. Nothing is regenerated
automatically and nothing is deleted; `auto_regenerate` and `history_overwrite_allowed` are
both `false`. Regeneration is explicit, produces a new documentation revision, and preserves
the previous one in an append-only history. Revision clouds are emitted only from a real
diff and carry no engineering interpretation. The impact report states plainly that it
claims no engineering validity beyond the model hash.

## 10. Security

Untrusted text is separated into two classes, in the specification rather than in prose.
Twenty-one declared unsafe patterns — script and markup tags, event handlers,
`javascript:`, `vbscript:`, `data:text/html`, `file://`, `<!ENTITY`, path traversal, NUL —
are **refused** in title blocks, sheet names and export set names. Labels that merely
resemble a prototype key or a template expression — `__proto__`, `constructor`,
`{{7*7}}`, `<b>bold</b>` — are **carried as inert text**, because a real project may
legitimately contain them, and their inertness is proven positively: never an object key at
any depth, never a canonical field, and in real Chromium written as escaped text with zero
elements opened.

Export filenames pass an allow-list, not a deny-list. Eleven hostile filenames — traversal,
absolute paths, reserved device names, embedded separators, a NUL byte, an over-long name —
are each refused, and `export_directory_escape_allowed` is `false`.

Thirteen malformed view definitions run through the real module in the backend security
suite: not a dict, unknown types, non-finite and infinite cut planes, out-of-bounds
coordinates, malformed crops, unknown disciplines. None crashes, every one is refused with
a declared issue code, and none moves the model hash.

## 11. Python ↔ JavaScript parity

Seventy-two assertions, byte-identical across all seventeen compared keys and twelve
fixture models: view definitions, plan geometry, elevation geometry, section geometry,
dimensions, annotations, draw operations, SVG bytes and hashes, schedule rows, quantities,
sheet descriptors, title-block refusals, document descriptors, PDF content streams and
MediaBoxes, export manifests, export sets, staleness verdicts and safety tables.

Three real divergences were found and fixed at contract level rather than normalised away:
`JSON.stringify` silently drops `undefined`-valued keys where Python keeps explicit nulls
(eighteen fields corrected); `String(0)` and `str(0.0)` differ, so the shared deterministic
formatter is now used in the slab-outline schedule cell as it already was in the drawing;
and the parity comparator itself was blind to `__proto__` until it was given an explicit
property definition and a self-test that fails loudly if it goes blind again.

For PDF, byte identity is not claimed across implementations. What is compared is the whole
drawing — page count, MediaBoxes and the exact content-stream operator text — with the
basis declared as `SEMANTIC_CONTENT_STREAM` and the reason stated. Parity is not waived.

## 12. The workspace panel

A DOCUMENTATION panel in the Phase 6 workspace with a tree of Views, Schedules, Quantities
and Sheets, a drawing viewer, real schedule tables, a quantity report, a sheet editor with
movable viewports, and an export workflow. It exposes **no engineering mutation control**,
asserted against a declared forbidden list of ten.

Verified in real Chromium — 85 assertions, no page errors: the panel opens; a floor plan
renders as a real SVG element with real `<line>` and `<rect>` children bound to the model
hash; sections and elevations are created from explicit definitions and an elevation
without a direction is refused; schedules render as real tables with unknown cells shown as
`NOT_SPECIFIED`; the quantity report renders with no currency and no cost field; viewports
move as documentation edits without touching the model; a restricted status is refused;
export produces a manifest bound to the model hash; every artifact turns out of date when
the model moves and nothing regenerates itself; hostile labels are inert and nothing
executes; and an Arabic ↔ English switch preserves the whole documentation state while the
drawing geometry stays byte-identical.

## 13. Verification classes

| Class | Meaning | Applied to |
| --- | --- | --- |
| CODE_VERIFIED | proven by an executed test | the whole documentation layer |
| RUNTIME_VERIFIED | real files produced and re-parsed; real Chromium | 23 SVG files parsed as XML, 6 PDFs, the panel in Chromium |
| NOT_VERIFIED | requires an environment this sandbox lacks | printing, external CAD validation, third-party PDF/SVG viewers |

## 14. Known limitations

- **No construction detailing, reinforcement, fabrication or shop drawings.** Declared
  hard-stop boundaries. A detail view is a magnified crop of existing geometry; no
  waterproofing layer, fastener or assembly is invented.
- **No cost estimation and no bill-of-quantities completeness claim.**
- **No regulatory compliance, code interpretation, occupancy determination or professional
  stamp.**
- **DXF is not implemented.** SVG, PDF and JSON only.
- **A section is taken on x or z.** An arbitrary section plane is future work.
- **A room `name` in the raw model is not surfaced.** `acs_arch` reports the room
  identifier as the space name, and documentation reports what the compiler states rather
  than reaching around it into raw model JSON. Changing that is a Phase 2 decision, not a
  Phase 9 one, so it is reported here rather than worked around.
- **PDF text is WinAnsi.** Non-Latin glyphs in the PDF text layer are substituted; the full
  Unicode text is preserved in the SVG and in the JSON package, and this is stated rather
  than hidden. Embedding a Unicode font is future work.
- **No external CAD or PDF validator ran.** No network, no such tool in this sandbox.
- **Printing is not verified.** `print_verified` is `false`.

## 15. Hard stop

Phase 9 ends here. Phase 10, cloud collaboration, multi-user editing, live Revit
synchronisation, automatic structural, MEP or fire design, regulatory code automation,
autonomous design, AI engineering auto-edit, construction scheduling and cost estimation
are **not** started and require explicit approval.
