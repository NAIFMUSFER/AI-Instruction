# Phase 5 — Project Authoring & Controlled Editing Foundation

**Controlled model mutation only. Revisioned, validated, auditable. No silent edits.
No runtime-to-model writes.**

---

## 0. The two invariants this phase holds at once

Phase 4 guaranteed:

> **RUNTIME IS EPHEMERAL. ENGINEERING MODEL IS IMMUTABLE.**

Phase 5 adds a way to change the model — and that guarantee still holds, because the new
path is not a relaxation of the old one. It is a separate subsystem:

```
USER ACTION
     ↓
AUTHORING COMMAND        typed, normalised, hashed
     ↓
VALIDATION / PREVIEW     on a candidate copy
     ↓
AUTHORING TRANSACTION    all-or-nothing
     ↓  explicit commit only
NEW ENGINEERING REVISION
     ↓
rebuild downstream derived data
     ↓
Coordination · Visual Scene · Runtime Scene
```

Runtime state still has no arrow pointing upward. A runtime action carrying a model-write
intent is still refused with `RUNTIME_MODEL_WRITE_ATTEMPT`, and the whole Phase 4
immutability suite is re-run as a hard gate inside Phase 5.

---

## 1. Files

| File | Role |
|------|------|
| `acs_authoring.json` | The canonical authoring specification — the single source of truth |
| `acs_authoring.py` | The Python authoring engine |
| `tools/build_authoring_browser.py` | Generates the browser mirror and injects it into `public/index.html` between explicit markers, **after** the runtime block so neither injector can erase the other |
| `tests/phase5/…` | Suites, fixtures, parity harness, benchmarks, `run_all.sh` |

The specification is mirrored verbatim into the page and a drift test compares the injected
object with `acs_authoring.json` byte for byte.

---

## 2. The authoring command

Every edit is a typed command. There is no free-form mutation payload and no path-based write.

```json
{
  "command_id": "cmd:<sha256_16>",
  "type": "MOVE_WALL",
  "target_id": "bld_0.flr_0.wall_0",
  "parameters": { "delta_m": 0.5, "hosted_strategy": "KEEP_RELATIVE_POSITION" },
  "constraints": { "must_not_change": ["SPACE_AREA"], "max_delta_m": 1.0 },
  "source": "USER",
  "actor_id": null,
  "base_revision": "rev:<sha256_16>",
  "created_at": "2026-01-01T00:00:00Z",
  "status": "NORMALISED",
  "writes_to_model": false
}
```

`SET_ANY_FIELD`, `PATCH_OBJECT`, `RAW_JSON_MUTATION`, `WRITE_MODEL`, `SET_MODEL`, `EVAL` and
`EXEC` are declared **forbidden types** and refused with `COMMAND_NOT_ALLOWED` — they are
refused rather than merely absent, and a test proves each one is.

### Command identity is deterministic

The hash covers type, target, normalised parameters, constraints and base revision. It does
**not** cover `created_at`, `actor_id` or `source`. Key order does not matter; constraint
order does not matter. Twenty repeated hashes of the same edit are identical.

---

## 3. Supported commands

Fully implemented (architecture, site, objects, project):

`MOVE_WALL` · `ADD_WALL`* · `DELETE_WALL`* · `MOVE_DOOR` · `ADD_DOOR` · `DELETE_DOOR` ·
`CHANGE_DOOR_PROPERTIES` · `MOVE_WINDOW` · `ADD_WINDOW` · `DELETE_WINDOW` ·
`CHANGE_WINDOW_PROPERTIES` · `RESIZE_SPACE` · `RENAME_SPACE` · `ADD_SPACE` · `DELETE_SPACE` ·
`MOVE_OBJECT` · `ADD_OBJECT` · `DELETE_OBJECT` · `CHANGE_LEVEL_HEIGHT` · `ADD_LEVEL` ·
`DELETE_LEVEL` · `MOVE_STAIR` · `ADD_STAIR` · `DELETE_STAIR` · `CHANGE_SITE_DIMENSIONS` ·
`CHANGE_BUILDING_POSITION` · `CHANGE_BUILDING_ROTATION` · `PROMOTE_VISUAL_OBJECT` ·
`LOCK_ELEMENT` · `UNLOCK_ELEMENT`

\* In this model walls are **derived** from space rectangles. `ADD_WALL` and `DELETE_WALL`
are therefore refused with an explanation that names the semantic source, rather than
pretending to author a free-standing wall that the compiler would immediately contradict.

Declared but **not implemented**: `MOVE_COLUMN` (STRUCTURE), `MOVE_DUCT` (MEP),
`CHANGE_FIRE_DOOR_METADATA` (FLS). They exist so discipline ownership is *expressed* rather
than implied. Submitting one is refused with `COMMAND_NOT_IMPLEMENTED` — never silently
ignored, never silently rewritten into an architectural edit.

### Discipline ownership

Architecture commands own architecture. Site commands own the site and building transform.
No architectural command may reach a structural, MEP or fire/life-safety record; an attempt
is refused with `AUTHORING_SCOPE_VIOLATION`. A stair carries vertical connectivity, so it may
not be moved through the generic object command — that too is a scope violation.

---

## 4. Transaction lifecycle

```
IDLE → DRAFT → PREVIEWED → VALIDATED → READY_TO_COMMIT → COMMITTED
```

Failure states: `REJECTED`, `CONFLICT`, `STALE_BASE_REVISION`, `INVALID_COMMAND`.

The transition table is declared in the specification and a test asserts that **no state
reaches `COMMITTED` except `READY_TO_COMMIT`** — a draft can never become a mutation.

---

## 5. Preview

`preview_command` builds a **candidate model from a copy**. The canonical model is compared
before and after and must be byte-identical; the engine asserts this internally as well as in
the suites.

```
BASE MODEL (H1) + COMMAND → CANDIDATE MODEL (H2) → PREVIEW SCENE
cancel → current model is still H1, history length still 1
```

The preview result carries `preview: true`, `committed: false`, both hashes, the changed
paths, the affected dependencies and the separately-tracked **dependency-breaking** list.

---

## 6. Validation

`validate_model_integrity` checks structural coherence only: levels exist and reference real
floor plates, space ids are unique per template, rectangles are finite and positive, spaces on
one template do not overlap, every opening fits its host edge, every object states a kind, and
site dimensions are positive.

> A valid transaction means **the data model is structurally coherent**. It does **not** mean
> code compliant, safe, structurally adequate, MEP adequate or fire compliant.

No issue code is named as a code violation, and the whole specification contains no
SBC/IBC/NFPA/ADA/ACI/ASCE/AISC/Eurocode/NEC/IEC/ASHRAE vocabulary — asserted by a test that
also proves the probe is not vacuous.

---

## 7. Commit

1. the base revision is verified as current, 2. the candidate is validated, 3. a new canonical
model is generated, 4. a new model hash is generated, 5. a revision record is created, 6. the
parent revision is preserved, 7. stale derived artifacts are named, 8. downstream rebuild is
triggered by hash change. **No step mutates anything in place** — the previous model object
stays byte-identical and remains addressable through its own revision.

Commit policy is declared, not hidden: an `ERROR` always rejects; a `WARNING` requires
explicit acknowledgement under the declared default (`ALLOW_WITH_EXPLICIT_ACKNOWLEDGEMENT`);
`ALLOW_SILENTLY` exists only as a deliberate opt-in.

A destructive command, or one whose **dependency-breaking** list is non-empty, additionally
requires a confirmation token equal to the transaction's computed digest. A harmless preview
requires nothing.

---

## 8. Revisions, undo, redo, diff

History is append-only. Undo and redo are **new forward revisions**, not deletions and not a
pointer moving backwards:

```
R1 → R2 (MOVE_WALL) → R3 (undo of R2) → R4 (redo of R2)
```

After all four, every earlier revision is still in history and every earlier model is still
addressable and still hashes to its recorded value.

`revision_diff` reports added, removed and changed paths, added/removed/changed elements, and
before/after values for each property change.

---

## 9. Dependency invalidation and selective rebuild

Each command type declares exactly which derived artifacts it invalidates. A wall move
invalidates architecture, relationships, coordination, visual, runtime, navigation, egress,
distance, rule results, snapshots and renders — and **not** structure, MEP or fire/life-safety,
because an architectural edit never rebuilds or moves those. A rename invalidates far less. A
lock invalidates nothing.

`dependency_impact` reports the exact affected element ids — never "some dependencies" — and
states `structure_mutated: false`, `mep_mutated: false`, `fls_mutated: false`.

---

## 10. Wall, opening, space, level, stair and site editing

**Walls.** A wall is resolved back to the space edges that generate it, and moving it edits
those rectangles. Openings riding the wall are handled by an explicitly stated strategy —
`KEEP_RELATIVE_POSITION`, `KEEP_WORLD_POSITION` or `CANCEL_IF_HOSTED`. There is **no default**;
a missing strategy is refused with `HOSTED_STRATEGY_REQUIRED`, because silently choosing one
would decide an engineering question on the user's behalf. No opening is ever left floating: if
keeping the world position would push an opening past its host edge, the command is refused with
`OPENING_OUT_OF_RANGE` rather than clipped.

**Openings.** Every move, addition and property change re-checks that the opening fits its host
edge; the refusal states the edge span, the requested centre and the width.

**Spaces.** A resize edits the canonical rectangle — the architectural source of truth — and the
derived walls are regenerated from it. It is never a stretched render box. Deleting a space
reports every dependent opening and object by exact id and requires confirmation.

**Levels.** The last remaining level cannot be deleted. A level still carrying spaces refuses to
cascade with `LEVEL_NOT_EMPTY`, naming how many spaces are in the way.

**Stairs.** Move, add and delete report `vertical_connectivity` as affected. No stair result
claims any compliance.

**Site.** Site dimensions, building position and building rotation are model facts; the visual,
runtime and coordination layers rebuild their world transforms from them.

---

## 11. Property editability

Five classes: `EDITABLE`, `READ_ONLY`, `DERIVED`, `UNKNOWN`, `DISPLAY_ONLY`. Space rectangles
and names are editable; the computed area, the model hash, the coordination clash count, the
compiled wall geometry and the runtime obstacle are `DERIVED`; the source id is `READ_ONLY`; the
render material is `DISPLAY_ONLY`; an unstated clear width is `UNKNOWN` and reported
`NOT_SPECIFIED` rather than invented. Not every displayed property is editable, and a test
asserts exactly that.

A derived element is edited by editing the element it was derived from — never directly. An
identifier in a derived namespace (`runtime:`, `obstacle:`, `portal:`, `walk:`, `vertical:`,
`measure:`, `vis:`, `clash_`, `nav:`, `egress:`) is refused as an authoring target.

---

## 12. Visual-only promotion

A visual object never becomes engineering content implicitly. `PROMOTE_VISUAL_OBJECT` is the one
path, and it requires a target semantic kind, coordinates and a provenance string. The result
records `promoted_from_visual`, the provenance and the source visual object id.

---

## 13. AI boundary

AI may **propose**. `propose_command` returns `PROPOSED_AUTHORING_COMMAND` with
`committed: false` and `requires_explicit_confirmation: true`, and creates no revision.

An AI-sourced command passes through the identical schema, normaliser, validator, security
scan, revision guard and preview as a user command, and additionally cannot commit without an
explicit token — the refusal code is `AI_COMMIT_NOT_PERMITTED`. There is no privileged AI path.

The natural-language pipeline is declared as seven explicit stages with user confirmation
between preview and commit. Target resolution is a separate stage: an ambiguous phrase returns
`AMBIGUOUS_TARGET` with the candidate list and chooses nothing.

Negative instructions survive as constraints. "Move the door but do not change the room size"
becomes `must_not_change: ["SPACE_RECT"]`, the constraint is part of the command hash so it
cannot be dropped downstream, and violating it is refused with `CONSTRAINT_VIOLATION`. Every
declared `must_not_change` subject is proven enforced by an executed test.

---

## 14. Batch transactions

Commands validate together and commit atomically. In the required 5-command test with one bad
command, all five report individual results, four are individually accepted, the one failure is
identified by index, and **zero** changes reach the model. The same batch without the failing
command commits as a single revision containing all four edits.

Batch size and payload size are capped; an oversized batch is refused with `BATCH_TOO_LARGE`
rather than attempted.

---

## 15. Locks

`LOCK_ELEMENT` / `UNLOCK_ELEMENT` with reasons `IMPORTED`, `USER_LOCKED`, `SYSTEM`. A locked
element refuses every mutating command with `TARGET_LOCKED` and the refusal names the reason. It
can still be read and still be unlocked. Locks are semantic — there are no users and no roles in
this phase, and none are fabricated.

---

## 16. Save and load

`serialise_project` writes the canonical model, its hash, the revision pointer and (optionally)
history and audit log. It writes **no** runtime state: no camera, no selection, no portal state,
no measurement, no preview, no pending command. `load_project` reconstructs the model, hash,
pointer and history, reports a hash mismatch if the stored hash disagrees with the stored model,
and always starts runtime state fresh.

---

## 17. Security

Authoring input is untrusted. Prototype-pollution keys (`__proto__`, `constructor`, …) are
refused before any processing; script payloads, `javascript:` URLs and `eval(`-style strings are
refused; non-finite numbers, absurd coordinates, over-deep nesting, over-long strings and
oversized payloads are refused. The engine uses no `eval`, no `exec` and no `Function`
constructor — asserted by the security suite against both the Python source and the injected
browser block, with a non-vacuity check.

---

## 18. Parity and browser verification

```
AUTHORING PARITY: 63/63 byte-identical   command hashes: 61/61   candidate models: 61/61
validation issues: 61/61   transaction results: 61/61   diffs: 61/61   adversarial: 40/40
```

Every Phase 5 suite also runs inside real Chromium with matching assertion counts, and the whole
parity comparison is repeated **in the browser** against Python.

Three divergences were found and fixed at the contract level:

1. **`_pyRound` corrupted large magnitudes.** `(1e308).toFixed(20)` returns exponential
   notation, which the parser turned into `0.000001`. Any value ≥ 1e21 was silently corrupted in
   the browser while Python was correct. Fixed by returning the value unchanged at that
   magnitude, exactly as Python's `round` does. This was a latent Phase 1 defect, not a Phase 5
   one.
2. **Diff numeric comparison.** Python distinguished `0` from `0.0`; the diff now compares
   through the same canonical numeric encoder used for hashing.
3. **Non-finite values lost in the parity harness.** A JSON round-trip turned `NaN` into `null`
   before it reached the engine, hiding a real adversarial case.

---

## 19. Verification results

| Suite | Checks |
|-------|--------|
| `test_authoring.js` | 127 |
| `test_commands.js` | 180 |
| `test_transaction.js` | 120 |
| `test_revision.js` | 89 |
| `test_ai_boundary.js` | 67 |
| `test_integration.js` | 70 |
| `test_immutability.js` | 105 |
| `test_adversarial.js` | 519 |
| `test_browser.js` | 55 (Node) / 80 (Chromium) |
| `test_parity.js` | 35 |
| `test_browser_parity.js` | 43 |
| **Phase 5 total** | **1410** |
| Security | 151 |
| Phase 4 regression | 1097 |
| Phase 3 regression | 357 |
| Phase 2 regression | 1598 |
| Phase 1 regression | 163 |

Engineering model hashes are unchanged from the Phase 4 baseline; the 3D geometry of all eight
models (785 meshes) is byte-identical to the restored original baseline.

---

## 20. Known limitations

- Walls, slabs, envelopes and voids are derived, so they are authored through their space
  sources. Free-standing wall authoring would need a different canonical model and is not faked.
- Structural, MEP and fire/life-safety authoring is declared in the vocabulary but not
  implemented. Those commands are refused explicitly.
- Only `NONE` and `GRID` snapping are implemented; `ENDPOINT`, `MIDPOINT`, `WALL`, `OPENING` and
  `ALIGNMENT` are declared and refused as unimplemented.
- Only `TRANSLATE` is implemented among gizmo operations.
- Undo and redo reconstruct from stored revision snapshots. A project loaded without
  `revision_models` can commit forward but cannot undo past what it carries.
- There is no authentication, no roles, no collaboration, no cloud persistence and no real-time
  synchronisation. The revision guard is the concurrency *foundation*, nothing more.
- Coordination, navigation, egress and distance results shown in a preview are geometric facts.
  `compliance` stays `NOT_EVALUATED` and explicit re-evaluation remains required after any commit.

## 21. What is NOT verified here

| Item | Status |
|------|--------|
| Real WebGL pixels, materials, shadows, textures | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| Frames per second, GPU behaviour, texture memory | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| Pointer, touch and headset input driving the gizmos | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| The live Render backend | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |

## 22. How to reproduce

```
sh tests/phase5/run_all.sh            # everything except the real browser
sh tests/phase5/run_all.sh --browser  # add the Chromium pass
```

Both work from a clean checkout and from any working directory. Nothing is read from `/tmp`;
`/tmp` is used only for run outputs.
