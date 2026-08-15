# Phase 8 — Final Report

**BIM Interoperability & Exchange Foundation**
Executed in the build sandbox on the repository at `/home/claude/acs/AI-Instruction-main`.
Every number below came from a command that was actually run. Nothing here is projected.

---

## 1. Scope delivered

A deterministic BIM exchange layer that exports the canonical engineering model to real
IFC4 STEP files, parses external IFC into a controlled staging representation, validates it,
maps it semantically, detects unsupported, ambiguous, lossy and unsafe mappings, produces
controlled authoring proposals, preserves revision history, and supports round-trip fidelity
testing — while the canonical model remains the sole internal engineering authority.

Out of scope and not started: cloud collaboration, automatic structural or MEP design, code
compliance, autonomous design, AI engineering auto-edit, multi-user cloud authoring, live
Revit sync.

## 2. The mandatory invariant

Declared in `acs_bim.json`, mirrored into `public/index.html`, asserted in the Python suite,
the parity suite, the browser suite and the backend security suite:

```json
{
  "external_bim_is_model_truth": false,
  "direct_import_write_allowed": false,
  "requires_explicit_commit": true,
  "writes_via_authoring_path": true
}
```

**Result: PASS.**

## 3. Files added or changed

| File | Lines | Status |
| --- | --- | --- |
| `acs_bim.json` | 681 | new — 107 top-level keys |
| `acs_bim.py` | 2,282 | new |
| `tools/build_bim_browser.py` | 862 | new — injects 54 KB of JavaScript, the panel DOM and its styles |
| `tests/phase8/test_bim.py` | 835 | new |
| `tests/phase8/test_parity.js` + `parity/` | 492 | new |
| `tests/phase8/test_bim_browser.js` | 275 | new |
| `tests/phase8/benchmark_bim.py` | 138 | new |
| `tests/phase8/make_outputs.py` | 105 | new |
| `tests/phase8/fixture_generator.py` | 80 | new |
| `tests/phase8/lib_bim_fixtures.py` / `.js` / `lib_large_fixture.py` | 123 | new |
| `tests/phase8/run_all.sh` | — | new |
| `tests/security/test_security.py` | +100 | extended — S-B1…S-B22 |
| `tests/phase3/lib/build_browser_page.js` | +10 | extended — injects the BIM DOM and styles |
| `PHASE8-BIM-INTEROPERABILITY.md`, `PHASE8-FINAL-REPORT.md` | — | new |

Phases 1–7 source files were **not** modified.

## 4. Test execution — exact counts

```
sh tests/phase8/run_all.sh --browser
```

| Suite | Passed | Failed |
| --- | ---: | ---: |
| BIM EXCHANGE (`test_bim.py`) | 526 | 0 |
| BIM PARITY SUITE (`test_parity.js`) | 53 | 0 |
| BIM BROWSER (Node scope) | 4 | 0 |
| BIM BROWSER (real Chromium) | 58 | 0 |
| BACKEND/CONFIG SECURITY | 259 | 0 |
| Phase 7 — render contract / targets / security / parity | 272 / 93 / 163 / 49 | 0 |
| Phase 7 — render security in real Chromium | 242 | 0 |
| Phase 6 — workspace contract / workflow / DOM / security / parity | 113 / 153 / 1 / 167 / 47 | 0 |
| Phase 5 — contract / commands / transactions / revisions / AI / integration / immutability / adversarial / browser / parity | 127 / 180 / 120 / 89 / 67 / 70 / 105 / 519 / 55 / 35 | 0 |
| Phase 4 — scene / navigation / collision / portals / selection / visibility / measurement / immutability / adversarial / regression / parity | 49 / 39 / 73 / 45 / 113 / 145 / 131 / 135 / 457 / 23 / 17 | 0 |
| Phase 3 — visual foundation / adversarial / dev API | 211 / 115 / 31 | 0 |

```
sh tests/phase8/run_all.sh --browser → 6,446 assertions passed → 0 failed → exit 0
```

(The security suite runs once per nested phase runner; the 6,446 total counts each
execution as it occurred.)

**Result: PASS.**

## 5. Real IFC artifacts produced

Thirteen IFC files, thirteen manifests, twelve round-trip reports, one import report, one
benchmark record and one index — 41 files, 7.7 MB, in `tests/phase8/outputs/`.

| Model | IFC entities | Canonical objects | Round trip | Semantic | Geometry | Relationship | Property | Model hash changed |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| clinic | 319 | 30 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| clinic_glazed | 427 | 39 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| hotel | 590 | 64 | WARNING | 1.000 | 1.000 | 1.000 | 1.000 | no |
| hotel_glazed | 698 | 74 | WARNING | 1.000 | 1.000 | 1.000 | 1.000 | no |
| office | 393 | 39 | WARNING | 1.000 | 1.000 | 1.000 | 1.000 | no |
| villa | 668 | 70 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| villa_glazed | 904 | 91 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| villa_single_level | 545 | 50 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| warehouse | 261 | 23 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| warehouse_glazed | 307 | 27 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| synthetic_grid | 35,485 | 4,112 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |
| synthetic_grid_large | 82,601 | 9,624 | PASS | 1.000 | 1.000 | 1.000 | 1.000 | no |

The three `WARNING` results are honest: those models contain an `elevator` object for which
no IFC mapping is declared. The loss is reported as `UNSUPPORTED_ENTITY`; nothing is invented
in its place. Critical loss count is 0 on every model.

**Result: PASS.**

## 6. Real IFC file structure (§57)

Every produced `.ifc` file was re-opened from disk and asserted to begin `ISO-10303-21;`,
carry `HEADER;` and `DATA;` sections with at least two `ENDSEC;`, declare
`FILE_SCHEMA(('IFC4'))`, end `END-ISO-10303-21;`, not begin with `{` or `[`, parse back
through the real parser, and match the `file_hash` recorded in its manifest.

**Result: PASS.**

## 7. NO FAKE IFC (§66)

No JSON object is written with an IFC name or presented as IFC. `IFC_NORMALIZED_EXCHANGE`
exists as a named internal intermediate representation between the canonical model and the
serialiser, and is documented as such.

**Result: PASS.**

## 8. Import staging

Nine import states, a staging record that carries `writes_to_model: false`, a
`STAGED EXTERNAL BIM` preview label rendered in the panel, and counts by support level
(supported / partially supported / preserved opaque / unsupported / refused).

**Result: PASS.**

## 9. Units

`unit_policy: DECLARED_ONLY`. Metres, millimetres, centimetres and feet were each exercised
with a real file and converted by the declared factor; a file declaring no length unit is
refused with a typed issue rather than defaulted.

**Result: PASS — no unknown unit is silently defaulted.**

## 10. Coordinates, placements and recursion defence

Nested `IFCLOCALPLACEMENT` chains resolve to a single project world. Cycles raise
`BIM_PLACEMENT_CYCLE`. The declared depth limit of 32 is enforced on the **true chain
depth**, verified in both file orderings — top-down and bottom-up — because memoised
recursion depth alone would have let a bottom-up ordering slip past the limit. That was a
real defect found by the adversarial fixture and fixed, not tested around.

**Result: PASS.**

## 11. Georeferencing

Four declared states, kept separate from project coordinates. No coordinate is invented from
a georeference and no georeference is inferred from coordinates.

**Result: PASS.**

## 12. Missing dimensions

Where the canonical model states no wall thickness, the export writes an `IFCPROPERTYSET`
`ACS_SourceCompleteness` with `ThicknessIsModelStated = .F.` via
`IFCRELDEFINESBYPROPERTIES`, and the reader restores `thickness_known: false`. Property
fidelity rose from 0.043 to 1.000 once the file declared what it did not know.

**Result: PASS — no missing BIM dimension is guessed.**

## 13. Properties, materials, classifications

Four declared canonical property mappings; everything else stays external metadata under a
fixed key. `material_promotion_allowed: false`, `classification_authority: false`,
`space_purpose_inference: false`.

**Result: PASS — no visual or external material is promoted to an engineering material.**

## 14. Round-trip fidelity

Sixteen compared dimensions, four fidelity scores, five declared tolerances (all ≤ 0.05 m /
0.05°). A critical geometry loss can never report `PASS`, in the specification and in the
code.

**Result: PASS.**

## 15. Diff engine

Ten difference types, five-step matching precedence with the basis always reported, and the
rule that a geometric match must also agree on semantic type and storey. Nearest-coordinate
alone is never a match.

**Result: PASS.**

## 16. Conflicts

Eleven conflict classes, five of them blocking. Host conflicts, unresolved references,
duplicate identifiers and stale targets were each exercised with a real file.

**Result: PASS.**

## 17. Proposals and the commit path

Proposals start `PENDING` or `BLOCKED` and carry `writes_to_model: false`. Accepting changes
nothing. Committing routes through `acs_authoring.validate_transaction` /
`commit_transaction` using `import_command_source: "IMPORT"` and
`import_command_map: {"PROPERTY_CHANGED.name": "RENAME_SPACE"}` — both asserted against
`acs_authoring.json` so Phase 8 cannot invent vocabulary. The generated command carries
exactly four fields and no invented one.

A defect was found here and fixed rather than worked around: the first implementation used a
made-up source `BIM_IMPORT`, which the authoring layer correctly rejected with
`INVALID_COMMAND`. The fix was to use the vocabulary Phase 5 already declares, not to widen
Phase 5.

**Result: PASS — the commit produces a new revision, appears in ordinary revision history,
and leaves the source project object unmutated.**

## 18. Staleness

A proposal set whose target model moved reports `STALE_TARGET_MODEL` and is refused; an
export manifest whose model moved reports `STALE_SOURCE_MODEL`. Neither is auto-deleted, and
neither is silently re-pointed.

**Result: PASS.**

## 19. Parser security and resource limits

Thirteen declared limits, all finite. Thirteen malformed payloads exercised through the real
parser in the backend security suite: empty file, JSON pretending to be IFC, missing DATA
section, unterminated string, unterminated argument list, dangling reference, duplicate entity
number, non-finite numeric, script in a name, `file://` reference, 200-deep nested argument
list, 2 MB line. None crashed the parser; every one was refused or typed; every issue code
raised is one the specification declares.

**Result: PASS — no infinite recursion, no stack exhaustion.**

## 20. Untrusted strings

Two classes, distinguished in the specification rather than conflated:

- **Refused** (21 declared unsafe patterns): script and markup tags, event handlers,
  `javascript:`, `vbscript:`, `data:text/html`, `file://`, `<!ENTITY`, `<!DOCTYPE`, `../`,
  `..\`, NUL. Seven real payloads were each exercised through a real IFC file and each
  produced `BIM_UNSAFE_STRING` and never reached a staged name.
- **Carried as inert text**: `__proto__`, `constructor`, `prototype`, `{{7*7}}`,
  `<b>bold</b>`, `a "quoted" & <tag>`. Not refused, because a valid external file may label a
  room that way. Proven inert positively: never an object key at any depth of the staging
  record, only ever a value in a declared `text_only_field`, creating no canonical field,
  and in real Chromium rendered as escaped text with zero elements opened.

The same names **as property keys** are refused with `BIM_PROPERTY_REFUSED` before they can
become keys.

**Result: PASS.**

## 21. Two real defects found and closed

1. **Prototype pollution vector in the parser.** External `IFCPROPERTYSINGLEVALUE` names were
   used directly as dictionary keys. Harmless in Python, pollution in JavaScript. Property
   names now pass `safe_key` before becoming keys, and a refused one raises
   `BIM_PROPERTY_REFUSED`. The declared `forbidden_property_keys` list is now enforced at the
   point it matters.
2. **A blind spot in the parity comparator.** Canonicalising with `o[k] = v` silently drops
   `__proto__`, so a prototype key present on one side and absent on the other compared as
   equal. The comparator now uses `Object.defineProperty` and carries a self-test that fails
   loudly if it goes blind again; the safety tables on both sides are arrays of pairs so an
   untrusted string is never an object key even in a fixture.

## 22. External references

`remote_dependency: false`, `remote_reference_policy: NEVER_FETCH`,
`allowed_external_reference_schemes: []`. Neither the Python module nor the generated browser
block contains a network call — asserted by pattern in the security suite.

**Result: PASS — no remote BIM resource is auto-fetched.**

## 23. Model hash invariance

Every stage — build exchange, validate, serialise, parse, stage, validate, diff, conflicts,
propose, accept, reject, round-trip compare, export descriptor — was checked to leave
`model_hash` and `current_revision` unchanged. The exporter additionally raises if the project
moved during export. The only change comes from an explicit commit through the authoring path.

**Result: PASS.**

## 24. Python ↔ JavaScript parity

53 assertions, byte identical on every compared key: exchange models, exchange validations,
export manifests, staging counts, import diffs, conflict sets, proposal sets, generated
commands, staleness verdicts, empty commits, deterministic identifiers, model hashes, the
commit case, the specification view, the safety verdict tables and the unit factor table.

The boundary is declared, not disguised: STEP parsing and serialisation run in Python only;
`BX_STEP_PARSER_IN_BROWSER = false` and `serialised_in_browser: false` are both asserted to be
present in the shipped page.

**Result: PASS.**

## 25. Real browser verification

```
node tests/phase3/lib/run_browser.js tests/phase8/test_bim_browser.js
→ BROWSER (Chromium) test_bim_browser.js: {"pass":58,"fail":0} page errors: none
```

Covered: the panel opens inside the workspace; the import review renders real counts under a
`STAGED EXTERNAL BIM` label; validation reports the real issue list; the diff and proposal
sections render real entries; Accept and Reject are real clicks that change proposal state
without touching the model; the explicit commit produces a new revision through the authoring
path and lands in ordinary revision history; the export summary and round-trip report render;
hostile imported strings are inert and nothing executes; an Arabic ↔ English switch preserves
the entire exchange state; the panel fits a narrow viewport and every visible control meets the
hit target.

**Result: PASS.**

## 26. Performance

Measured on real IFC text, CPU milliseconds in this sandbox on one run, entity counts beside
every time. No frame rate, no GPU, no rendering measured or claimed.

| Model | Objects | IFC entities | Bytes | Export | Parse | Placements | Stage | Round trip |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| warehouse | 23 | 261 | 13,948 | 1.8 ms | 2.1 ms | 0.3 ms | 3.7 ms | 0.2 ms |
| villa_glazed | 91 | 904 | 51,152 | 7.5 ms | 7.8 ms | 1.6 ms | 10.9 ms | 0.8 ms |
| synthetic_grid | 4,112 | 35,485 | 2,246,816 | 415 ms | 372 ms | 108 ms | 646 ms | 35 ms |
| synthetic_grid_large | 9,624 | 82,601 | 5,276,346 | 822 ms | 999 ms | 158 ms | 1,934 ms | 82 ms |

The largest measured file uses 41.30 % of the declared entity budget (82,601 of 200,000) and
7.9 % of the declared byte budget.

**Result: PASS.**

## 27. Large model fixture

`synthetic_grid` (8 levels × 64 spaces) and `synthetic_grid_large` (12 levels × 100 spaces):
regular grids with a door and two windows per space and a full placement hierarchy. Both stay
inside every declared limit, parse back with every entity accounted for, and round-trip PASS
with zero critical loss. They are measurement fixtures, not architecture, and nothing
engineering is derived from them.

**Result: PASS.**

## 28. Auditability

Nine declared audit events. The audit records hashes, never raw payloads and never secrets;
an unsafe payload is stored as `sha256:…`; an undeclared event is not recorded; a prototype
key is dropped from the record.

**Result: PASS.**

## 29. Verification classification

| Class | Verdict |
| --- | --- |
| CODE_VERIFIED | the exchange layer, serialiser, parser, staging, units, placements, diff, conflicts, proposals, commit bridge, staleness, audit, security |
| RUNTIME_VERIFIED | 13 real IFC files written to disk, read back and compared; the panel and hostile-import handling in real Chromium |
| INTEROP_VERIFIED | **none** |
| NOT_VERIFIED | independent validator, third-party authoring tool round trip, IFC2X3 writing, non-parametric geometry conversion |

### `INTEROP_VERIFIED: none`

This sandbox has no outbound network and no independent IFC implementation — no
`ifcopenshell`, no Revit, no ArchiCAD, no Solibri, no buildingSMART validator. §64 forbids
calling internal export → internal import interoperability, and this report does not. The
files are structurally IFC4 STEP by the specification and parse back with this
implementation. Whether a third-party tool opens them is **unknown and not claimed**.

## 30. PASS / FAIL / NOT_VERIFIED, separated

**PASS (executed and proven here)**
Mandatory invariant · real IFC4 STEP export for 12 models · STEP file structure ·
parse-back · export determinism · round-trip fidelity 1.000 on all four dimensions with zero
critical loss · unit normalisation and refusal of undeclared units · nested placement
resolution · true-chain depth limiting in both file orderings · cycle detection · opening and
host relationships · unsupported entity preservation · missing-dimension declaration ·
georeference separation · diff and matching precedence · conflict classification · proposal
lifecycle · commit through the Phase 5 authoring path with a new revision in ordinary history
· staleness discipline · 13 malformed payloads handled safely · unsafe-string refusal ·
inert-text proof · property-key refusal · no network call · model hash invariance at every
stage · Python ↔ JavaScript parity (53 assertions) · real Chromium panel verification (58
assertions) · Phase 1–7 regression unchanged · 6,446 assertions, 0 failed.

**FAIL**
None.

**NOT_VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**
- Independent IFC validation of the produced files (no validator, no network).
- Opening the produced files in Revit, ArchiCAD, Solibri or any third-party tool.
- Importing a file authored by a third-party tool (none exists in this sandbox; every file
  parsed here was produced by this serialiser or hand-built as an adversarial fixture).
- WebGL 3D display of imported geometry — `public/vendor/` is empty because the sandbox has
  no network, so Three.js never loads. Chromium here does report WebGL 2.0 via SwiftShader,
  so the limitation is the missing library, not the browser.
- IFC2X3 writing (declared out of scope).
- Conversion of swept-solid, B-rep and CSG geometry into canonical engineering geometry
  (read and preserved, not converted).

**NOT_IMPLEMENTED (declared, not pretended)**
- Authoring commands for `OBJECT_RESIZED`, `OBJECT_ADDED` and `OBJECT_REMOVED` proposals.
  They are diffed, classified and proposed, and reported as unsupported at commit rather than
  force-fitted onto a command that does not mean the same thing.

## 31. Explicit final confirmations

| # | Confirmation | Verdict |
| --- | --- | --- |
| 1 | NO DIRECT BIM IMPORT MUTATION | CONFIRMED |
| 2 | NO SILENT IMPORT COMMIT | CONFIRMED |
| 3 | NO EXTERNAL BIM FILE BECOMES MODEL TRUTH | CONFIRMED |
| 4 | NO EXPORT MUTATES THE MODEL | CONFIRMED |
| 5 | NO UNSUPPORTED ENTITY IS INVENTED AS A SUPPORTED ONE | CONFIRMED |
| 6 | NO MISSING BIM DIMENSION IS GUESSED | CONFIRMED |
| 7 | NO UNKNOWN UNIT IS SILENTLY DEFAULTED | CONFIRMED |
| 8 | NO REMOTE BIM RESOURCE IS AUTO-FETCHED | CONFIRMED |
| 9 | NO IMPORT BYPASSES REVISION HISTORY | CONFIRMED |
| 10 | NO AI AUTO-EDITS BIM ENGINEERING | CONFIRMED — this layer contains no AI path at all |
| 11 | NO VISUAL MATERIAL IS PROMOTED TO ENGINEERING MATERIAL | CONFIRMED |
| 12 | NO ROUND-TRIP PASS IS CLAIMED WHEN CRITICAL GEOMETRY DRIFTS | CONFIRMED |
| 13 | NO INTEROP_VERIFIED CLAIM WITHOUT AN INDEPENDENT IMPLEMENTATION | CONFIRMED — `INTEROP_VERIFIED: none` |
| 14 | NO PHASE 1–7 REGRESSION | CONFIRMED — every earlier suite re-ran unchanged and passed |

---

## 32. DEPLOYMENT DELIVERABLES

The deployable-bundle requirement was issued for the end of Phase 9. Phase 9 has not been
specified or begun, so the machinery is delivered here against the **Phase 8** tested state
and will be re-run and re-issued under `PHASE9-*` names when Phase 9 lands.

- **Full deployable repository:** `AI-Construction-Studio-Phase8.zip`
- **SHA-256:** published in the sidecar `AI-Construction-Studio-Phase8.zip.sha256` and in the
  delivery message. It is deliberately **not** written into this file: this file is inside the
  archive, so embedding the digest here would change the archive and invalidate the digest.
  Verify with `sha256sum -c AI-Construction-Studio-Phase8.zip.sha256`.
- **Contents:** 342 files in 40 directories (382 zip entries), 16,069,832 bytes uncompressed
- **Deployment manifest:** `DEPLOYMENT-MANIFEST.md`
- **Historical Phase 8 production verification:** superseded by `PHASE9-PRODUCTION-VERIFICATION.md` and the later Phase 9.x verification checklists.
- **Deployment validation script:** `tests/deploy/verify_deploy.sh` (+ `verify_deploy.py`) —
  191 checks passed, 0 failed
- **Environment variable template:** `.env.example` — names and non-secret defaults only
- **Changed-files archive:** not produced; the complete repository archive is the deliverable
- **Frontend production build:** `bash tools/netlify-build.sh` → **EXIT 1**,
  `npm error 403 Forbidden — GET https://registry.npmjs.org/three`.
  **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (this sandbox has no registry access).
  The script failed fast rather than continuing with missing libraries, which is the intended
  behaviour and is asserted. The published page itself, `public/index.html`, is committed and
  needs no build step.
- **Backend production build:** `docker build -t acs-engine .` → **EXIT 1**, no Docker daemon
  in this sandbox. **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.**
  `pip download -r requirements.txt` → **EXIT 1**, no PyPI access. **NOT VERIFIED.**
  What *was* executed statically: all 33 `COPY` sources resolve, `py_compile` of every module
  the image copies passes, the backend core imports cleanly, and `acs_understand_api` fails
  only on the third-party `fastapi` import that `requirements.txt` declares.
- **Live deployment:** **NOT VERIFIED** — nothing has been deployed from this sandbox and no
  live URL was tested.

### Archive integrity

The archive was built from the final tested state and then **extracted to a different path
and re-verified from scratch**:

```
sh tests/phase8/run_all.sh --browser   (from the extracted copy) → 6,446 passed, 0 failed
sh tests/deploy/verify_deploy.sh       (from the extracted copy) →   191 passed, 0 failed
```

That round trip found a real defect and it was fixed rather than excused: the Phase 4 model
regression asserted its baseline path did not contain the substring `/tmp`, which fails
whenever the repository is extracted under a temporary directory — the baseline was always a
committed repository file. The check now asserts the real intent (inside the repository tree,
under `tests/`, a non-empty regular file, and not in the directory the run writes scratch
output to) and passes from any location. The assertion is stronger than before, not weaker.

### Deployment audit findings

1. **No module the deployed API needs is missing from the image.** The entrypoint's transitive
   closure is 5 modules and the Dockerfile copies every one. Verified by computing the closure
   from the AST, not by reading the `COPY` list.
2. **Fifteen modules ship in the image without being reachable from the API entrypoint**
   (`acs_arch`, `acs_coord`, `acs_distance`, `acs_egress`, `acs_fls`, `acs_ingest`, `acs_mep`,
   `acs_navigation`, `acs_occupancy`, `acs_project`, `acs_relations`, `acs_revision`,
   `acs_rules`, `acs_struct`, `acs_visual`). Not a fault — they are the server-side reference
   implementation — but it is now reported rather than implicit.
3. **Six modules are deliberately absent from the image** (`acs_runtime`, `acs_authoring`,
   `acs_workspace`, `acs_render`, `acs_bim`, `acs_compiler`). These layers execute in the
   browser from the mirrors injected into `public/index.html`. If a future phase gives the API
   an endpoint that imports one of them, the closure check fails until the Dockerfile is
   updated.
4. **A false PASS in the first draft of the deploy check was caught and fixed.**
   `public/vendor/` contains three empty directories, and an "is it populated" check written
   as `any(os.scandir(...))` passed on the directory entries alone. It now counts files and
   matches them against the 13 the build script requires — currently 0 present, reported as
   `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED` rather than green.
5. **No secret and no sandbox path is packaged.** No `.env`, no credential-shaped value, no
   `/home/`, `/tmp/acs_` or `/opt/pw-browsers` reference in anything deployed. The `sk-ant-…`
   string in two source comments is a placeholder in a usage note, not a key. `render.yaml`
   declares `ANTHROPIC_API_KEY` with `sync: false` and no value, and `/health` returns
   `bool(...)`, never the key.

---

## HARD STOP

Phase 8 — BIM Interoperability & Exchange Foundation is complete and stopped here.

**Not begun, and requiring explicit approval:** Phase 9, cloud collaboration, automatic
structural design, automatic MEP design, an automatic code-compliance engine, autonomous
design, AI engineering auto-edit, multi-user cloud authoring, live Revit sync.
