# Engineering audit — evidence recorded 2026-09-26

Source reviewed: `adec616aa5191315991fb9439cee83efbb719b8f`, after the untouched
measurement recorded in `BASELINE.md`. This document records this audit run;
its figures are historical measurements, not rolling current-state claims.

The measured repair-loop validator accepted invalid opening geometry and
missed physical opening collisions. It also rejected a sound exterior window.
The fixes below address those reproducible errors without introducing a
regulatory threshold, resizing a room, or claiming structural adequacy.

The commercial limit is broader than these fixes: the available models and
validator results do not establish that a building is construction-ready.
Loads, structural design, a verified regulatory review, and an independent
Revit opening were not established in this audit. That evidence gap is partly
an engineering verification/service problem, not just a code problem.

## Evidence commands

Run from this branch's checkout, with the baseline Python environment:

```sh
python3 tests/remediation/test_audit_engineering_openings.py
python3 tests/remediation/test_audit_engineering_openings.py --mutations
python3 tests/remediation/test_audit_engineering_openings.py --compare-baseline adec616
python3 tests/remediation/test_audit_engineering_openings.py --evidence
python3 tests/remediation/test_validate_topology.py
python3 tests/remediation/test_validate_against_real_models.py
python3 tests/remediation/test_rule_source_boundary.py
```

`--compare-baseline` requires the named commit to exist locally; it executes
that commit's validator and the changed validator on the same discovered
fixtures. `--evidence` prints the room rectangles, openings, objects, validator
issues, real IFC serialization census, declared elevations and vocabulary
probe used in the tables below. No generated IFC, output JSON or test logs are
committed by this stream.

## Defects, severity and the missing checks

Severity here describes impact on the reliability of the product output,
not a structural or regulatory verdict.

| Measured defect | Severity | Did the original validator catch it? | Cause; result after repair |
|---|---|---|---|
| Door width zero or negative; invalid edge `Q`; nonfinite/non-numeric opening coordinates | High | No; invalid numeric strings/null also raised exceptions | The opening loop converted coordinates before checking them and did not reject nonpositive width or an unknown edge. It now returns an Arabic diagnostic and skips invalid geometry in the topology pass. |
| Door taller than the explicitly stated wall; window head above that wall | High | No | No vertical containment check in the repair-loop validator. Explicit dimensions are now compared; missing wall/window dimensions remain unknown. |
| Two intersecting doors in a template containing one room | High | No | An early `len(entries) < 2` return skipped all topology, including collisions within a room. The room's openings are now checked. |
| Door and window intersect horizontally and at explicitly stated elevations | High | No | The span ledger restarted for each opening kind. It now spans doors and windows, and checks their known vertical intervals. |
| A window on a clear portion of an edge was labelled internal because a neighbour touched a different portion | Medium | False positive | The neighbour check used the whole room edge. It now intersects the actual aperture interval with the neighbour. Both the east/west and north/south coordinate conventions are covered. |
| Vertically separated windows at the same horizontal position were reported as colliding | Medium | False positive | The original collision check used horizontal spans alone. Stated vertical separation now suppresses the report. |

Reproduction is in `OpeningGeometry`, `OpeningCollisions` and `WindowExposure`
in the first command above. Each fix has a sound control: normal positive
dimensions, a room-specific taller wall, unknown dimensions, separate apertures,
edge-touching apertures, a transom above a door, stacked windows and an aperture
which really does intersect an interior neighbour.

The existing same-kind plan-overlap behavior is preserved when vertical
dimensions are absent, because that is an existing tested contract. A new
cross-kind collision is reported only when both vertical intervals are known.
Unknown heights are not turned into fabricated defaults.

## Test-first and mutation evidence

The test file was written and executed before changing `acs_validate.py`.
The original validator produced this verbatim summary:

```text
Ran 19 tests in 0.005s

FAILED (failures=21, errors=4)
```

The failure count includes failing subtests. After the fix, the same command
reported `Ran 19 tests` and `OK`. An additional control then proved that an
invalid edge cannot create spurious topology findings; the final suite
reported `Ran 20 tests` and `OK`. The pre-existing topology, real-model and
rule-source commands above reported respectively `Ran 28 tests`, `Ran 8 tests`
and `Ran 9 tests`, all `OK`.

`python3 tests/remediation/test_audit_engineering_openings.py --mutations`
deliberately disables each changed guard in an in-memory copy of the source,
runs the positive/negative tests, and requires failure. Recorded output:

```text
KILLED invalid edge
KILLED invalid edge excluded from topology
KILLED positive width
KILLED finite plan dimensions
KILLED stated vertical dimensions
KILLED unknown or invalid vertical interval
KILLED stated wall height
KILLED room wall override
KILLED single room
KILLED door and window shared span ledger
KILLED vertical separation
KILLED unknown cross-kind elevation
KILLED aperture-specific neighbour
KILLED horizontal separation
MUTATIONS 14 killed 14 survived 0
```

The baseline comparison command recorded:

```json
{"models": 165, "changed_results": [], "mutated": [], "nondeterministic": []}
```

Thus none of the discovered real-fixture validator results changed. The
existing corpus scan still reported its original six F-51 diagnostics, with
no exceptions. This is evidence of no added corpus noise; it is not proof
that every fixture is a sound design or that every possible false positive
has been eliminated.

The dedicated `.github/workflows/acs-audit-engineering.yml` runs the new tests,
mutations, existing topology/corpus checks and regulatory boundary. Its action
SHAs are copied from the existing approved-object workflow; it has read-only
repository permissions and does not deploy.

## Five building types: independent coordinate review

Fresh live generation of five models: **NOT VERIFIED — EXTERNAL ENVIRONMENT
REQUIRED** at the initial audit. No provider credentials or newly generated
live models were available to this stream then. Substituting existing fixtures
is disclosed here; it does not satisfy a live-generation acceptance test.
The dated authenticated follow-up below covers the later captured models.

The audited models are `villa_glazed`, `hotel_glazed`, `office`, `clinic_glazed`
and `warehouse_glazed` from the committed Phase 3/7 fixtures. They are actual
repository model inputs, not five new successful customer generations. The
following review was made from their explicit rectangles/openings/objects,
independently of the validator output. The `--evidence` command reproduces all
coordinates and counts in this section.

| Model | Manual vertical/support review | Access and openings review | Original validator output |
|---|---|---|---|
| Villa | Stair object anchors align at world `(7, 8)` on both levels. Upper room rectangles lie over ground room rectangles. Neither observation proves a load path. | Corridor width is explicitly 2 m. Upper bathroom has a south-edge door facing unmodelled space; full cross-level access is NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED. Glazing follows the exterior edge portions inspected. | 12 issues: lighting omissions and the upper corridor's missing door. No F-51 topology diagnostic. |
| Hotel | Core rectangles and object anchors align; stair anchor `(13, 2)`, lift anchor `(11, 2)`. Lower room geometry is partial compared with the typical floor; unsupported-room inference is deliberately suppressed. | Typical corridor width is 2 m. Guest doors point toward it. Corridor lacks its own door records; lift count is present but individual lift footprints are not stated. | 7 issues: lighting omissions and the typical corridor's missing door. No F-51 topology diagnostic. |
| Office | Core rectangles/anchors align at the same coordinates as the hotel. Lower room geometry is partial; structural support remains unresolved. | Typical corridor width is 2 m. Office/meeting doors face the corridor. No windows are declared, so exterior window placement cannot be judged for this fixture. | 7 issues: lighting omissions and the typical corridor's missing door. No F-51 topology diagnostic. |
| Clinic | Single level: inter-storey continuity is inapplicable. | Reception opens west to the site boundary. The lab and pharmacy have no door records; the validator catches those omissions. The declared glazing was reviewed against each touched edge. | 7 issues: lighting omissions plus missing lab/pharmacy doors. No F-51 topology diagnostic. |
| Warehouse | Single level with a surrounding envelope and declared functional zones. Zone overlap with the envelope is intentional. | Receiving door opens west to the site boundary. A zone's role is not evidence of a closed room; the model does not supply a complete pedestrian route. Glazing is on the north edge. | 4 lighting-omission issues. No F-51 topology diagnostic. |

The zero F-51 rows above do **not** mean zero engineering defects. The models
lack door swing/hinge and clearance data; stair objects lack stated flight,
rise, run, landing and headroom geometry. Egress lengths/dead ends require a
resolved route graph, and no numeric egress or corridor threshold is evaluated
here. Room adjacency is only the existing validator's coarse reachability
heuristic; it is not proof of traversability through the specific door leaves.

These are model/verification limitations, not newly introduced geometry
guards. Adding a code-width rule or guessing a landing would violate the
project's explicit authority boundary. Cross-level walkability and physical
stair traversal: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** for the
rendered output, with missing source dimensions still needing resolution.

## IFC4: real serialization, with the external acceptance boundary

`--evidence` calls `acs_authoring.create_project` and `acs_bim.export_ifc` on
the same models. Recorded results were valid IFC4 headers, declared metre
units, named `IFCSPACE` instances and real wall/door/window entities:

| Model | Storey elevations (m) | IFC spaces | IFC walls | IFC doors | IFC windows | Unsupported objects disclosed |
|---|---|---:|---:|---:|---:|---:|
| Villa | 0, 3.2 | 11 | 44 | 11 | 21 | 0 |
| Hotel | 0, 3.3, 6.6 | 10 | 40 | 8 | 10 | 3 |
| Office | 0, 3.3 | 6 | 24 | 5 | 0 | 2 |
| Clinic | 0 | 5 | 20 | 4 | 9 | 0 |
| Warehouse | 0 | 4 | 16 | 2 | 4 | 0 |

The wall entity counted here is `IFCWALLSTANDARDCASE`; the corresponding
door/window counts are `IFCDOOR`/`IFCWINDOW`, not anonymous mesh objects. Hotel
and office lift objects produce disclosed `UNSUPPORTED_ENTITY` warnings.
Missing wall/slab thicknesses produce disclosed property-loss entries. Their
existence is not silently promoted to known engineering dimensions.

Revit import, its displayed scale, its interpretation of placements and actual
editable entity behavior: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
A serialization census and the repository's own parser are not independent
Revit verification.

## Regulatory boundary and Arabic vocabulary

`python3 tests/remediation/test_rule_source_boundary.py` passed all its tests:
review requirements remain `NOT_EVALUATED`, required values remain unknown,
no uncited threshold enters repair errors and legacy saved proposals cannot
bypass the source requirement. The new geometry tests assert no `الكود`, SBC,
IBC, NFPA, `compliant` or `معتمد` claim in their issue output. No authority
planner or regulatory data was changed by this stream.

The vocabulary probe in `--evidence` exercises the **deterministic coverage
diagnostic**, `acs_generation._synonym_hits`, and `acs_programs.detect_type`:

| Arabic word | Coverage synonym measured | Type detection measured |
|---|---|---|
| مجلس | `majlis` | residential |
| مقلط | none | residential |
| ملحق | none | residential |
| فناء | none | residential |
| منور | none | residential |
| سطح | none | residential |
| قبو | `parking` | residential |
| مستودع | none | warehouse |
| بدروم | none | residential |

This is a limitation of the diagnostic's declared alias table. It is **not**
evidence that the live language model cannot understand those words. In
particular, mapping every basement to parking is not a sound universal
semantic rule. An end-to-end Arabic request/response vocabulary audit remains
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**; it must compare generated
spaces against the exact requested uses, not just keyword hits.

## Delivery and regression status

This stream changes only the repair-loop validator, its dedicated tests,
its dedicated CI workflow and this report. Generated browser files, shared
CI, production settings and the regulatory boundary are untouched. No main
push, merge or production deployment was performed.

The post-change code Phase 0/expanded-suite comparison used the same commands and
environment as `BASELINE.md`, via `python3 ../run_baseline.py .
../audit-evidence/engineering` with a stream-specific `TMPDIR`. The corrected
Phase 1 snippets were also replayed with `--runner 'node tests/lib/run.js'`.
The comparison of the captured `results.json` files recorded 249 invocations,
the same 32 baseline nonzero exits, no new failing target and the added
engineering suite passing. Integration, index guard, API origin, CSP hash and
deploy verification all exited zero; the bare CI runner retained its baseline
usage exit 64. The documentation-claim failure retained its baseline status.

That sweep's privacy scan ran before this report was finalized, so its result
did not cover the final report text. The final PR CI subsequently caught a
new documentation regression: the villa row used a negation phrasing that
the existing compliance-claim guard did not recognize. The
[failing CI job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/36265835407/job/108470203571)
was reproduced locally with `python3 tests/remediation/test_privacy_boundary.py`
(`PRIVACY BOUNDARY: 73 passed, 1 failed`). The row now states the existing
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED` outcome directly. The guard
was not changed or weakened. The earlier no-new-failure comparison therefore
describes the code sweep, not the final report's initial CI result.

After the wording correction, the privacy command reported
`PRIVACY BOUNDARY: 74 passed, 0 failed`, and
`python3 tests/remediation/test_doc_claims.py` reported `Ran 12 tests` and `OK`.
The recorded baseline ran `python3 tools/bundle_report.py` before
`python3 tools/check_doc_claims.py`: its current-state block matched, while
Chromium and the live-panel measurement were unavailable. A later standalone
gate rerun, after restoring the tracked generated bundle report, reported a
stale-artifact mismatch. That was a missing measurement prerequisite in the
rerun, not a current-state mismatch in the recorded baseline.

The final follow-up regenerated the bundle report, then ran the documentation
gate with the pinned Python environment and
`ACS_CHROMIUM=/workspace/scratch/cc68e7a7ea83/browser-runtime/chromium`.
The current-state block matched and all 10 documented claims were measured
successfully; the gate exited zero. This later browser-enabled result is
distinct from the original browser-unavailable baseline. The generated test
artifact was restored afterward and was not committed.

An initial replay exposed missing shell quotes in the baseline's displayed
corrected-runner commands. Those invocation-error logs were retained
separately, the structured runner argument was restored, and the replay then
matched the baseline. No product code was changed to accommodate that error.

Environmental and invocation failures retain their baseline classification.
A passing geometry suite is not a
claim that the live frontend, provider, Revit, headset or rendered stair path
has been verified.

## Authenticated follow-up capture — 2026-09-26

This section records later evidence, not a replacement for the original
untouched baseline. The coordinator created isolated synthetic audit projects
through the authenticated live UI. Only those projects were read. There were
two successful saved live models in this engineering review: an apartment
building on one level and an apartment building on three levels. Both disclosed
the deterministic fallback after provider failure. These are not five successful
live building types. The villa and warehouse attempts did not provide successful
saved models; the backend report covers their incomplete checkpoints.

The backend agent's scoped deployment lookup identified live Render commit
`adec616aa5191315991fb9439cee83efbb719b8f`. Frontend build provenance is
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. The raw captures are excluded
from git. Reproduce their counts, hashes, parser checks and local recompilation
from the authorized evidence directory with:

```bash
python3 tests/remediation/test_audit_engineering_door_meshes.py --evidence /workspace/scratch/cc68e7a7ea83/audit-evidence/engineering-live
```

That command reads `apartment-revision.json`, `multilevel-revision.json`, the
actual downloaded `apartment-approved.{ifc,gltf,dxf,svg}` and their separate
`apartment-{ifc,gltf,dxf,svg}-manifest.json` files. It labels the downloaded glTF
and local recompiled glTF separately. Missing captures are a missing prerequisite,
not permission to substitute repository fixtures for live evidence.

The apartment capture is revision `plan_b82ea4b815604e3b88d724400d3138e8` in
synthetic project `297b015f-5177-4dd7-82cd-3cad31766ec4`. Its model hash is
`2e732037bfe1a46c50bc9f992b5b661260dedc94db3e40ba5d3402c8e4e1a086`.
The multilevel capture is revision `plan_8f9a7eda4c684a1c94c14ee3dc8cec10` in
synthetic project `0708177d-9de0-4777-8518-353f460b053c`. The evidence command
prints each model's levels, room counts, validator result and review coverage.

| Captured output | Measured result | Engineering implication |
|---|---|---|
| One-level apartment | Site 24 × 30 m; 18 template rooms; validator issues `[]`. | Explicit room boundaries and openings can be inspected. Structural load paths, door swing/clearance and ventilation adequacy remain outside this result. |
| Three-level apartment | Site 30 × 30 m; one 20-room template repeated at level indices 0, 1, 2; validator issues `[]`. Stair rectangle `[0,0,4,4]` and lift rectangle `[27,0,3,4]` repeat exactly. | Core room alignment is represented. No stair/lift objects are declared. `acs_arch.compile_architecture` returns zero cores, zero slab voids and no issues. Local compilation retains three full floor slabs and has no stair/lift object meshes. Physical movement between floors is NOT VERIFIED. |

The second row is the most consequential new output miss. An aligned named
room does not establish a flight, landing, headroom or opening in the slab.
The source model and renderer cannot establish a walkable interlevel path from
those room labels. No dimensions or regulatory error were manufactured to fill
that gap. Structural support, egress distances against thresholds, and physical
walkthrough remain **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

### E5 — actual live exports and their declared limits

These are downloaded artifacts from the successful apartment project, not the
older IFC fixture exports discussed above. The evidence command verifies all
artifact byte counts and SHA-256 values against their own manifests and prints
the common model/revision binding. Their declared approval scope is
`CONCEPTUAL_DESIGN_ONLY`; regulatory and structural fields remain `NOT_VERIFIED`.

| Download | Bytes | Local inspection from the evidence command |
|---|---:|---|
| IFC | 11,639 | STEP parser valid; metre length unit with factor 1; one storey at elevation 0; 18 named `IfcSpace` entities; zero wall, door, window and slab entities. Manifest explicitly says `SPACES_ONLY`. |
| glTF | 480,430 | 237 nodes, 948 accessors, 216,144 buffer bytes. Finite coordinates, accessor ranges, declared bounds and triangle indices passed this local structural check. This is not an official Khronos validator run. |
| DXF | 27,798 | ezdxf audit: zero errors/fixes; unit code 6 (metres); 18 polylines and 19 text entities. |
| SVG | 34,200 | XML parses; 18 room groups, 19 rectangles including the site, and 36 text nodes. |

The IFC acceptance requirement for real architectural wall/door/window entities
is not met by this spaces-only live export. Its scope is disclosed. The DXF/SVG
projection also explicitly excludes doors, windows, wall thickness, structural
grid and MEP. Revit import, AutoCAD visual review and headset traversal are
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. Successful local parsing is
not substituted for any of those application checks.

### E6 — reciprocal door records produced coincident glTF leaves

The downloaded apartment glTF contains 35 door meshes but only 18 distinct
POSITION vertex sets: 17 coincident pairs. Adjacent rooms each carry their own
canonical opening record, which is valid topology input. The compiler emitted
a complete leaf for both sides. This is an export defect, not a validator error
and not a reason to delete either room's opening record.

After failing tests were recorded, the compiler was changed to pair only
opposite edges of different rooms on the same floor, with exactly matching
world centres, dimensions, materials and remaining opening semantics. Each pair
retains both source identities in glTF `extras.acs_opening_sources`. Opening
IDs, canonical models and frozen-baseline source maps are unchanged. Same-face
records, ambiguous room IDs, distinct centres/dimensions/materials, and different
hinge/swing metadata remain separate. No coordinate rounding is used.

The evidence command recompiles the captured apartment locally to 21 door
meshes: 14 exact reciprocal duplicates are removed, with 28 source records in
the exported aliases. Three identical-vertex pairs remain because their source
centres differ in double precision. That conservative limitation is intentional.
The locally recompiled three-level capture has 60 door meshes and no coincident
door vertex excess; it still has no physical stair/lift geometry. No GPU timing,
frame-rate improvement, or visible flicker claim was measured.

### E7 — disclose physical traversal separately from core alignment

The existing `vertical_circulation` scope and conceptual approval invariant are
preserved. The bridge and canonical review now add local, model-derived coverage:
`core_alignment`, `geometry_scope: EXPLICIT_CORE_OBJECTS`, `geometry`,
`missing_geometry`, and `physical_traversal: NOT_VERIFIED`. Dimensioned core
objects can establish geometry presence; they never establish physical traversal.
Core objects located in other room roles are recognized. Unmatched objects or
unknown core intent yield unknown coverage instead of a fabricated missing-core
finding. Provider/verifier-supplied coverage cannot promote traversal status.

For the captured multilevel model, the new local review records alignment PASS,
geometry MISSING and missing stair/lift geometry on each level, while retaining
the existing conceptual approval result. The frontend stream separately changes
the scope label to core alignment and displays the unverified traversal status,
including for old responses without this new field. This section does not claim
that these PR changes are deployed.

### Follow-up test and corpus evidence

Before these source edits, `npm install` and the exact Phase 0 commands were
rerun. Integration/index/API/CSP/deploy/bundle checks passed; the bare CI command
again exited 64 for its missing runner. Replaying the 240 test-target commands
printed in `BASELINE.md` produced the same exits as the original record, including
30 nonzero test-target results. No product edit preceded that replay. The logs
are in the external `engineering-live-baseline` evidence directory.

```bash
python3 tests/remediation/test_audit_engineering_door_meshes.py
python3 tests/remediation/test_audit_engineering_door_meshes.py --mutations
python3 tests/remediation/test_audit_engineering_vertical_coverage.py
python3 tests/remediation/test_audit_engineering_vertical_coverage.py --mutations
python3 tests/remediation/test_audit_engineering_door_meshes.py --corpus 4980d58
```

The door suite first recorded failing reciprocal-mesh/alias cases; the coverage
suite first failed because the coverage field was absent. Follow-up negative
tests caught premature float32-only pairing and an exception on a legacy level
without `index`, and both were fixed before delivery. Sound object-based core
controls also prevented a false missing-geometry disclosure. The resulting suites
report 12 door tests and 15 coverage tests passing; all 11 door mutations and
10 coverage mutations are killed. A forged traversal-PASS control also passes.

The corpus command compares with the pre-follow-up PR head `4980d58`: 165 models,
162 compiled, 90 reciprocal door meshes removed across 83 models; all non-door
parts and all retained door geometry/materials are unchanged. Repeated compilation
is deterministic and does not mutate caller input. Existing review scopes/issues
are identical before and after. The three pre-existing compiler exceptions are
preserved and reported, not hidden: `models.unstated` in `arch_scen.json` lacks
`offset`; `live_large_generated.json` and its `_outlier` counterpart lack level
`index`. These compiler exceptions are distinct from the validator sweep, which
had no exceptions. No generated capture or test output is committed.

The final replay used the same commands recorded in `BASELINE.md`, plus
`npm install`, with the pinned virtualenv, `ACS_ENV=test` and an isolated
`TMPDIR`. Its external `engineering-live-after/results.json` records 249
invocations, 32 nonzero exits and no exit differences from the original
baseline. This includes the known missing-browser/vendor failures, the
WebGL timeout and the bare CI runner usage error; it is not an all-green
claim. The comparison is reproducible with:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/workspace/scratch/cc68e7a7ea83/audit-evidence/engineering-live-after/results.json')
rows = json.loads(p.read_text())
print(len(rows), sum(r['exit'] != 0 for r in rows))
print([(r['target'], r['baseline_exit'], r['exit']) for r in rows
       if r['baseline_exit'] != r['exit']])
PY
python3 tests/remediation/test_privacy_boundary.py
python3 tests/remediation/test_doc_claims.py
```

The final report passed the privacy boundary (74 assertions) and documentation
guard unit suite (12 tests). Those checks ran after this live evidence section
was added; the generated bundle/performance outputs and lockfile were restored
before commit.
