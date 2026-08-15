# Phase 8 — BIM Interoperability & Exchange Foundation

**Deterministic exchange. The canonical engineering model stays the only engineering
authority. No external file becomes model truth. No import writes without an explicit
human commit.**

---

## 0. The rule that shapes everything else

```json
{
  "external_bim_is_model_truth": false,
  "direct_import_write_allowed": false,
  "requires_explicit_commit": true,
  "writes_via_authoring_path": true
}
```

Those four values are in `acs_bim.json`, mirrored byte-for-byte into `public/index.html`,
asserted by a drift test in both the Python suite and the browser suite, and re-checked in
the backend security suite. They are not documentation about intent; they are the thing the
code reads at runtime.

The pipelines follow from them:

```
IMPORT
  EXTERNAL BIM FILE
    → STEP PARSER
      → IMPORT STAGING MODEL          (never the model; labelled STAGED EXTERNAL BIM)
        → SCHEMA + SECURITY VALIDATION
          → SEMANTIC MAPPING
            → DIFF / CONFLICT / LOSS ANALYSIS
              → IMPORT PROPOSAL       (PENDING · ACCEPTED · REJECTED · BLOCKED)
                → EXPLICIT USER ACCEPTANCE
                  → PHASE 5 AUTHORING / REVISION PATH
                    → CANONICAL MODEL

EXPORT
  CANONICAL MODEL → BIM MAPPING → EXCHANGE MODEL → VALIDATION → SERIALISATION → IFC FILE
```

There is no arrow from a staged file into the model. `commit_import` cannot write: it
translates accepted proposals into commands that already exist in the Phase 5 vocabulary and
hands them to `acs_authoring.validate_transaction` / `commit_transaction`. If the authoring
layer refuses, the import is refused. Phase 8 owns no write path of its own.

## 1. Files

| File | Role |
| --- | --- |
| `acs_bim.json` | the canonical exchange specification — 107 top-level keys: support levels, entity and relationship coverage, states, mapping and matching rules, loss and conflict classes, units, tolerances, limits, unsafe patterns, issue codes, panel contract, hard-stop boundaries |
| `acs_bim.py` | 2,282 lines: exchange builder, IFC4 STEP serialiser, STEP parser, staging model, unit and placement resolution, relationship graph, round-trip comparison, diff, conflicts, proposals, commit bridge, audit |
| `tools/build_bim_browser.py` | injects the JavaScript mirror, the BIM panel DOM and its styles into `public/index.html`; idempotent, marker-delimited |
| `tests/phase8/` | contract suite, parity suite, browser suite, fixtures, benchmark, artifact generator, runner |
| `tests/phase8/outputs/` | 41 real artifacts: 13 IFC files, 13 manifests, 12 round-trip reports, 1 import report, 1 benchmark, 1 index |

## 2. Real IFC, and the line that was not crossed

Every file in `tests/phase8/outputs/*.ifc` is an ISO-10303-21 STEP physical file: it opens
`ISO-10303-21;`, carries a `HEADER;` section with `FILE_DESCRIPTION`, `FILE_NAME` and
`FILE_SCHEMA(('IFC4'))`, a `DATA;` section of numbered instances, and closes
`END-ISO-10303-21;`. Each one is parsed back by the same parser and the test asserts it is
not JSON wearing an `.ifc` name.

§66 of the brief is explicit that a JSON object must never be presented as IFC. It is not.
`IFC_NORMALIZED_EXCHANGE` exists and is named as what it is — an internal intermediate
representation between the canonical model and the serialiser — and it is never written to
disk with an IFC extension.

## 3. Support is declared, never implied

Twenty IFC entities carry an explicit support level: `SUPPORTED`,
`PARTIALLY_SUPPORTED`, `PRESERVED_OPAQUE`, `UNSUPPORTED`, `REFUSED`. Six relationship types
likewise. An entity the specification does not list is counted, reported and preserved as an
opaque external record — it is never quietly mapped onto something that looks similar. The
hotel and office models export with round-trip status `WARNING` for exactly this reason: they
contain an `elevator` object and there is no declared IFC mapping for it, so the loss is
reported rather than invented away.

Writable schema: IFC4. Readable: IFC4 and IFC2X3. A file declaring anything else is refused
with a typed issue rather than parsed hopefully.

## 4. Nothing is guessed

**Units.** `unit_policy` is `DECLARED_ONLY`. A file that declares metres, millimetres,
centimetres or feet is converted by the declared factor; a file that declares no length unit
is refused, not defaulted to metres.

**Missing dimensions.** When the canonical model does not state a wall thickness, the
exporter does not invent one and then let it read back as fact. It writes the geometry with
the declared placeholder *and* an `IFCPROPERTYSET` named `ACS_SourceCompleteness` carrying
`ThicknessIsModelStated = .F.`, attached through `IFCRELDEFINESBYPROPERTIES`. On the way back
in, the reader restores `thickness_known: false`. Before this was added, property fidelity on
those models measured 0.043; with the declaration it measures 1.000 — because the file now
says what it knows and what it does not.

**Coordinates.** Placement chains are resolved to one project world. Nested
`IFCLOCALPLACEMENT` hierarchies are walked, cycles are detected, and the declared depth limit
of 32 is enforced on the *true chain depth* rather than on recursion depth — otherwise the
limit would be an artefact of entity ordering in the file, and a bottom-up ordering would slip
past it. Both orderings are tested.

**Georeferencing** is a separate, declared state (`NONE`, `DECLARED`, `PARTIAL`,
`REFUSED`), never mixed into project coordinates.

**Materials and classifications** carry no engineering authority:
`material_promotion_allowed` is `false`, `classification_authority` is `false`,
`space_purpose_inference` is `false`. A space named "electrical room" in an external file
does not authorise equipment.

## 5. Round-trip fidelity, measured on sixteen things

`roundtrip_report` compares building count, level count, level elevations, space count, space
names, wall count, wall positions, wall dimensions, door count, door positions, window count,
window positions, slab count, stair count, containment and host relationships — and reports
four fidelity numbers: semantic, geometry, relationship and property. Tolerances are declared
(position and dimension 0.001 m, angle 0.01°, area 0.01 m², elevation 0.001 m).

A critical geometry loss can never report `PASS`; the specification says so and the code
enforces it. Across the twelve exported models, geometry fidelity is 1.000 and the critical
loss count is 0 everywhere, including on the 82,601-entity synthetic file.

## 6. Diff, proposals and the commit

The diff engine matches by declared precedence — recorded mapping, source GlobalId, exported
identifier, semantic-and-geometry agreement, then unmatched — and always reports which basis
it used. A geometric match must also agree on semantic type and storey; nearest-coordinate
alone is never a match, and an ambiguous match stays unresolved.

Ten difference types and eleven conflict classes are declared, five of them blocking. Every
proposal starts `PENDING` or `BLOCKED`, carries `writes_to_model: false`, and can be accepted
or rejected without touching anything.

Committing is the only write, and it is not Phase 8's write. `import_command_source` is
`IMPORT` — a source Phase 5 already declares — and `import_command_map` maps
`PROPERTY_CHANGED.name` to `RENAME_SPACE`, a command type Phase 5 already declares. A test
asserts both against `acs_authoring.json` rather than trusting the string. A proposal with no
declared command mapping is reported as unsupported and is never committed.

If the target model moves between staging and commit, the proposal set is `STALE_TARGET_MODEL`
and the commit is refused — never silently rebased.

## 7. Security: allow-lists, and an honest distinction

Untrusted text arrives from files nobody in this project wrote. Two classes are treated
differently, and the difference is stated in the specification rather than left to the
reader:

**Refused.** Twenty-one declared unsafe patterns — script and markup tags, event handlers,
`javascript:`, `vbscript:`, `data:text/html`, `file://`, `<!ENTITY`, `<!DOCTYPE`, path
traversal, NUL. These are executable, fetchable or traversing. A file carrying one in a name
gets a typed `BIM_UNSAFE_STRING` and that name never reaches a staged record.

**Carried as inert text.** `__proto__`, `constructor`, `prototype`, `{{7*7}}`, `<b>bold</b>`.
These are *not* refused, because a real external file may legitimately label a room that way
and refusing it would reject a valid file over the content of a label. Instead the guarantee
is positive and tested: such a label appears only as a value in a declared `text_only_field`,
it is never an object key at any depth of the staging record (a walker checks every key), it
creates no canonical field, and in real Chromium it is written to the document as escaped
text — `&lt;b&gt;bold&lt;/b&gt;` in the markup, `<b>bold</b>` in the text content, and zero
`<b>` elements in the panel.

**A real defect this found and closed.** External property *names* were being used directly
as dictionary keys when reading `IFCPROPERTYSINGLEVALUE`. Harmless in Python, prototype
pollution in JavaScript. Property names now pass `safe_key` before they can become a key at
all, and a refused one raises `BIM_PROPERTY_REFUSED`. The declared
`forbidden_property_keys` list is now actually enforced at the point it matters instead of
only being declared.

**A second defect, in the test harness itself.** The parity comparator canonicalised objects
with `o[k] = v`, which silently drops `__proto__` — so a prototype key present on the Python
side and absent on the JavaScript side compared as equal. The comparator now uses
`Object.defineProperty` and carries a self-test that fails loudly if it ever goes blind
again. The safety tables on both sides are now arrays of pairs, so an untrusted string is
never an object key even in a test fixture.

No remote resource is ever fetched: `remote_dependency` is `false`,
`remote_reference_policy` is `NEVER_FETCH`, `allowed_external_reference_schemes` is empty,
and neither the Python module nor the generated browser block contains a network call.

Thirteen malformed payloads are run through the real parser in the backend security suite —
empty file, JSON pretending to be IFC, missing DATA section, unterminated string,
unterminated argument list, dangling reference, duplicate entity number, non-finite numeric,
script in a name, `file://` reference, 200-deep nested argument list, 2 MB line. None
crashes, every one is refused or typed, and every issue code raised is one the specification
declares.

## 8. Python ↔ JavaScript parity, with the boundary stated

STEP parsing and serialisation run in Python only. The browser declares this in its own
source: `BX_STEP_PARSER_IN_BROWSER = false`, and its export descriptor carries
`serialised_in_browser: false`. This is not hidden behind a passing test — the parity suite
asserts that both declarations are present in the shipped page.

What is compared is the layer that genuinely runs in both: exchange model construction,
validation, export descriptor, import diff, conflicts, proposals, staleness, generated
commands, deterministic identifiers, unit factors, and the commit through the authoring path.
Both sides start from the identical staging representation, which the Python side writes out
precisely because it is the side that can parse. Fifty-three parity assertions pass, byte
identical on every compared key.

The IFC GlobalId is deterministic and agrees across implementations: the same seed yields
`2650_TYdkpUiAqq_AtSkfx` in both.

## 9. The workspace panel

A BIM / Exchange panel inside the Phase 6 workspace: Import, Export, Validate, Compare,
Proposals, Round-trip. It shows the canonical model's revision and hash, then — under a
`STAGED EXTERNAL BIM` label — the imported file's name, hash, size, schema, unit, entity
counts by support level, error and warning counts, georeference state, and a preview of the
staged space names. It renders difference entries, proposals with working Accept and Reject
buttons, an explicit commit control, the export summary and the round-trip report.

It exposes no engineering mutation control, and the specification names four things it must
never offer: `IMPORT_AND_REPLACE_MODEL`, `APPLY_ALL_WITHOUT_REVIEW`, `AUTO_COMMIT_IMPORT`,
`OVERWRITE_MODEL`.

Verified in real Chromium (58 assertions, no page errors): the panel opens, a real staged
file renders, accept and reject are real clicks that change proposal state without touching
the model, the explicit commit produces a new revision through the authoring path and appears
in ordinary revision history, hostile labels are inert, and an Arabic ↔ English switch
preserves the entire exchange state.

## 10. Verification classes

| Class | Meaning | Applied to |
| --- | --- | --- |
| CODE_VERIFIED | proven by an executed test | the whole exchange layer, parser, staging, diff, proposals, commit bridge, security |
| RUNTIME_VERIFIED | real execution in a real engine | the panel and hostile-import handling in Chromium; 13 real IFC files written, read back and compared |
| INTEROP_VERIFIED | an independent implementation read or wrote the file | **none** |
| NOT_VERIFIED | requires an environment this sandbox lacks | everything below |

**`INTEROP_VERIFIED: none`.** This sandbox has no outbound network and no
`ifcopenshell`, no Revit, no ArchiCAD, no Solibri, no buildingSMART validator. Internal
export → internal import is *not* interoperability, and §64 forbids calling it that. The
files are structurally IFC4 STEP by the specification and parse back with this
implementation; whether Revit opens them is unknown and is not claimed.

## 11. Known limitations

- **No independent validator ran.** See above. This is the single largest gap in the phase.
- **Import geometry coverage is parametric-first.** Rectangular extruded profiles and
  declared axis lengths are mapped parametrically; other geometry is classified
  (`BOUNDING_GEOMETRY_ONLY`, `TESSELLATED_PRESERVED`, `OPAQUE_GEOMETRY`,
  `UNSUPPORTED_GEOMETRY`) and preserved rather than converted. Swept solids, B-reps and CSG
  are read and preserved, not turned into canonical engineering geometry.
- **Only one proposal type commits today.** `PROPERTY_CHANGED.name` → `RENAME_SPACE`.
  Resizes and additions are diffed, reported and proposed, but have no declared command in
  this phase, so they are reported as unsupported rather than force-fitted.
- **IFC2X3 is readable, not writable.** Writing it is declared out of scope here.
- **The browser does not parse STEP.** Declared, tested, and stated on the page.
- **The large fixture is synthetic.** `synthetic_grid` and `synthetic_grid_large` are regular
  grids generated for measurement. They are not architecture and nothing engineering is
  derived from them.
- **Benchmarks are CPU milliseconds in this sandbox on one run.** No frame rate, no GPU, no
  rendering is measured or claimed by this layer.

## 12. Hard stop

Phase 8 ends here. Cloud collaboration, automatic structural design, automatic MEP design,
an automatic code-compliance engine, autonomous design, AI engineering auto-edit, multi-user
cloud authoring and live Revit sync are **not** started and require explicit approval.
