# Phase 4 — Interactive Walkthrough & Deterministic Simulation Runtime Foundation

**Read-only interaction. Deterministic. Traceable. Immutable upstream.**

---

## 0. The invariant this phase exists to protect

> **RUNTIME IS EPHEMERAL. ENGINEERING MODEL IS IMMUTABLE.**

A selection, a hidden object, an open door, a measurement, a camera position and a simulation clock
are *session state*. None of them is a model fact, none of them survives into a revision hash, and
none of them may be presented as an engineering decision.

The flow is one-way and never reverses:

```
CANONICAL ENGINEERING MODEL
        ↓
   COORDINATION
        ↓
   VISUAL SCENE          (Phase 3 — geometry-preserving, derived)
        ↓
   RUNTIME SCENE         (Phase 4 — walkability, collision, portals, index)
        ↓
   RUNTIME STATE         (Phase 4 — ephemeral session state)
        ↓
   USER INTERACTION
```

There is no arrow pointing back up, and no function in this phase creates one. Any payload that
even *asks* for one is refused with `RUNTIME_MODEL_WRITE_ATTEMPT`.

---

## 1. What was added

| File | Role |
|------|------|
| `acs_runtime.json` | The canonical runtime specification — the single source of truth |
| `acs_runtime.py` | The Python implementation |
| `tools/build_runtime_browser.py` | Generates the browser mirror and injects it into `public/index.html` between explicit `BEGIN`/`END` markers; running it twice replaces the block rather than duplicating it |
| `tests/phase4/…` | The verification suites, fixtures, parity harness and benchmarks |
| `tests/phase3/fixtures/mesh_baseline.json` | The vendored 3D-geometry baseline the model-regression suite compares against |

The specification file is mirrored verbatim into `public/index.html`. A drift test compares the
injected object with `acs_runtime.json` byte for byte, so the two can never diverge quietly.

---

## 2. The runtime scene

`compile_runtime_scene(visual_scene, runtime_config)` reads a Phase 3 visual scene and returns a new
derived structure. It never writes to its input — proven, not asserted, by byte-comparing the visual
scene and the source model before and after every operation in `test_immutability.js`.

The compiled scene contains:

- **objects** — every visual object, each carrying its runtime id, its visual id, its source element
  id, its discipline, its kind, an oriented bounding box, an axis-aligned bounding box, a collision
  decision with the basis for that decision, and whether it is visual-only.
- **walkability.surfaces** — walkable floor rectangles derived from canonical spaces.
- **walkability.obstacles** — the blocking subset, in world coordinates.
- **walkability.portals** — one per modelled door, with derived connectivity.
- **walkability.vertical_connections** — modelled stairs. No lift or escalator behaviour is claimed.
- **rooms** — canonical spaces exposed as runtime rooms.
- **spatial_index** — a uniform grid over obstacles and surfaces.
- **counts**, **defaults**, **issues**, **accepted**, and `writes_to_model: false`.

Every identifier is deterministic and namespaced, so a runtime id can never be confused with a
model id:

```
runtime:<visual_scene_id>            runtime:obj:<source_or_visual_object_id>
runtime:room:<space_id>              walk:space:<space_id>
obstacle:<visual_object_id>          portal:<source_element_id>
vertical:<source_element_id>         measure:<sha256_16>
```

No timestamp, no random value, no UUID and no iteration order enters an identifier. Compiling the
same scene twice yields a byte-identical result.

---

## 3. Navigation

Six modes, each with an explicit contract rather than an implied one:

| Mode | Gravity | Collision | Vertical free | Needs walkable surface |
|------|---------|-----------|---------------|------------------------|
| `ORBIT` | no | no | yes | no |
| `FIRST_PERSON` | no | yes | yes | no |
| `WALK` | **yes** | **yes** | no | **yes** |
| `FLY` | **no** | **no** | **yes** | no |
| `PLAN` | no | no | yes | no |
| `DOLLHOUSE` | no | no | yes | no |

`WALK` and `FLY` are deliberately stated as opposites in the specification itself, so the difference
is a declared contract and not an implementation accident. An unknown mode is refused with
`NAVIGATION_MODE_INVALID`; it is never silently coerced to a default.

Enum values must be **strings**. A list, a number or an object is refused rather than coerced —
otherwise JavaScript would accept `['WALK']` (which stringifies to `WALK`) while Python refused it,
and the two implementations would disagree.

---

## 4. The player capsule

Defaults: radius 0.30 m, height 1.75 m, eye height 1.62 m.
Limits: radius 0.05–1.5 m, height 0.5–3.0 m; the eye must sit within the capsule.

A capsule that is missing, malformed, non-finite, negative, zero or out of range is refused with
`PLAYER_CAPSULE_INVALID`. `create_runtime_state` then falls back to the declared defaults and
records the issue — it does not pretend the caller's capsule was accepted.

---

## 5. Collision

Collision is decided per object kind from a declared policy table, never guessed:

- **Blocking**: walls, columns, beams, structural slabs, foundations, cores, equipment, risers,
  stairs, roofs, ceilings.
- **Non-blocking**: doors (passability is decided by portal state), MEP segments, terminals,
  devices, signs, assembly points, ground, water.
- **Walkable**: slabs.
- **Decoration and every other visual-only object**: `NON_BLOCKING` by default, with the basis
  recorded as `visual_only_never_blocking`. A caller may declare decoration `BLOCKING` for a
  session; that choice is recorded on the runtime scene and never becomes an engineering property.

Objects are tested as **oriented** boxes with a separating-axis test, not as axis-aligned boxes. The
suite includes a case where the axis-aligned test says "overlap" and the oriented test correctly says
"no overlap", so the distinction is proven rather than assumed.

### The spatial index is bounded and honest

A uniform grid of 4 m cells indexes obstacles and surfaces. An entry spanning more cells than the
declared cap is recorded as *oversized* and always returned as a candidate.

A query box wider than the declared cap, or carrying a coordinate beyond
`max_abs_coordinate_m`, or malformed, does **not** enumerate cells. It returns
`full_scan: true` with `scanned_cells: 0` and the complete entry set. This matters twice over: a
hostile query can never be turned into an unbounded cell enumeration, and the index never claims a
speed-up it did not deliver.

Measured on the benchmark fixtures, a local query on a 10,158-object model returns 34 candidates out
of 8,140 indexed entries — a 99.8 % reduction, demonstrated by the benchmark rather than asserted
in prose.

---

## 6. Portals

A portal is derived from a **modelled door**. The door itself is untouched, its hash is unchanged,
and no access control, security, locking or scheduling behaviour is implied or implemented.

Connectivity is derived by probing, never invented:

| Basis | Meaning |
|-------|---------|
| `two_space_probe` | The door's normal reaches a real canonical space on both sides |
| `one_space_probe_exterior` | One side is a real space; the host wall is exterior-exposed |
| `unresolved` | Neither could be proven — `to_space` is `null` and the count is published |

Phase 3 does not cut holes in walls, so an `OPEN` portal creates an aperture carve-out (expanded by
the capsule radius) that overrides the host wall's blocking for that aperture only. A `CLOSED`
portal leaves the wall blocking. Portal state lives in runtime state alone: the compiled portal
keeps its declared default, and the door's model hash is unchanged across any number of transitions.

The room connectivity graph is explicitly a **foundation only** — there is no route planning, no
evacuation routing and no pathfinding anywhere in this phase.

---

## 7. Selection and inspection

Selection is single, ephemeral and stored only in runtime state. No runtime object grows a
`selected` flag, and the returned selection is a copy rather than a live reference.

Inspection reports **only what the source states**. An absent property is reported as the literal
string `NOT_SPECIFIED` — never as `null`, `0`, `""`, `false`, or a plausible default. A visual-only
object reports `engineering_source: NOT_SPECIFIED` and `visual_metadata_only: true`, so it can never
be read as engineering data. No inspection anywhere invents a fire rating, a load, a U-value, a
capacity or a code reference; the suite scans every inspection of every object in every fixture for
that vocabulary, and separately proves the scan is not vacuous by planting a value it must catch.

---

## 8. Visibility

Visibility is an explicit hidden-set plus an optional isolation, evaluated into an effective
visibility list on demand. **Hiding is not deletion**: the object count never changes, the object
still answers selection and inspection while hidden, and the runtime scene is byte-identical before
and after every visibility mode.

Twelve declared modes cover object, room, floor and discipline — show, hide, isolate — plus restore.
An unknown mode or target is refused and changes nothing.

---

## 9. Measurement

Five types: `POINT_TO_POINT`, `OBJECT_WIDTH`, `OBJECT_HEIGHT`, `ROOM_DIMENSION`, `CLEARANCE`.

Distances are **computed from verified coordinates and never trusted from the caller** — a caller who
supplies `distance_m: 999` alongside two points still gets the real distance. Every accepted result
is finite and non-negative. A rotated member measures its own local width, not its axis-aligned
shadow. Every measurement carries `runtime_only: true` and states in its own text that it is never a
code check, a clearance requirement or a compliance statement.

Measurement identifiers are content hashes, so the same measurement always yields the same id and no
timestamp or random component leaks in.

---

## 10. Model write protection

`validate_runtime_action` refuses every declared write intent, every `set_*` and `write_*` prefix,
and the raw keys `geometry`, `source_element_id`, `vertices` and `transform`, with
`RUNTIME_MODEL_WRITE_ATTEMPT`. A runtime configuration that asks for `writes_to_model` is refused at
compile time. A harmless payload is *not* falsely accused — that is checked too.

`test_immutability.js` runs a full session against every fixture — navigation, spawn, movement,
selection, inspection, visibility, measurement, every portal transition, time advance, summary and
connectivity — and then compares the engineering model hash and the visual scene hash before and
after. It also mutates the runtime scene directly at the top level, inside nested objects, inside
arrays and by grafting new fields, and proves that none of it reaches upstream.

---

## 11. Errors

Twenty-six declared validation codes, each with a declared severity. Issues are ordered
deterministically by severity, then code, then subject, then detail — the same hostile scene yields
the same order every time. `accepted` is stated explicitly on every compiled scene: a scene carrying
a single `ERROR` is never presented as valid.

---

## 12. Python ↔ JavaScript parity

Both implementations run the same 17 scenarios and 16 adversarial scenes from the same fixture file,
and their outputs are compared canonically.

```
RUNTIME PARITY: 19/19 byte-identical   adversarial agreement: 16/16   operation agreement: 357/357
```

Two divergences were found and fixed at the contract level rather than papered over:

1. **Numeric encoding.** Python writes `14.0` where JavaScript writes `14`, so any hash over a float
   diverged. Both implementations now route canonical serialisation through the repository's single
   numeric-token encoder (`acs_ingest.canonical_json` / `ingestCanonicalJson`).
2. **Absent versus null.** JavaScript omitted `camera.position` when it was `undefined`, where Python
   emitted `null`. Absence is now written as `null` explicitly.

`test_browser_parity.js` then repeats the whole comparison **inside real Chromium** and additionally
runs every Phase 4 suite in the browser, requiring the browser and Node assertion counts to match
exactly.

---

## 13. Verification results

Executed offline in this environment, all suites green:

| Suite | Checks |
|-------|--------|
| `test_runtime.js` | 49 |
| `test_navigation.js` | 39 |
| `test_collision.js` | 73 |
| `test_portals.js` | 45 |
| `test_selection.js` | 113 |
| `test_visibility.js` | 145 |
| `test_measurement.js` | 131 |
| `test_immutability.js` | 135 |
| `test_adversarial.js` | 457 |
| `test_model_regression.js` | 22 |
| `test_parity.js` | 17 |
| `test_browser_parity.js` (real Chromium) | 44 |
| **Phase 4 total** | **1270** |
| Phase 3 regression | 211 + 115 + 31 |
| Security | 141 |

Engineering model hashes are identical to the Phase 4 pre-implementation baseline:

```
clinic 9d53da26e80c9da134047e9c   hotel 7e6459352f65da0d692a6d34
office e2d7e76e963de85394aa2716   villa de6d2d3568bce08e5bf72882
warehouse 44f38c43a92e731fbe0057c7
```

The 3D geometry the application builds — 785 meshes across 8 models, each with its name, position,
size and rotation — is byte-identical to the baseline.

---

## 14. What is deliberately NOT here

No agent, no LLM control of the runtime, no AI image generation, no generative geometry, no
text-to-building, no procedural architecture, no geometry editing, no BIM authoring, no crowd
simulation, no evacuation simulation, no fire or smoke propagation, no CFD, no thermal simulation,
no structural simulation, no robot, forklift or vehicle physics, no live digital twin, no IoT, no
multiplayer, no network sync, no VR controllers, no AR, no native mobile app, no pathfinding agents,
no NPCs, no gameplay, no physics engine integration, no design optimisation, no automatic design
correction and no automatic engineering decision.

There are no placeholders suggesting any of these are supported.

## 15. What is NOT verified here

| Item | Status |
|------|--------|
| Real WebGL pixels, materials, shadows, textures | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| Frames per second, GPU behaviour, texture memory | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| Pointer, touch, gamepad and headset input devices | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| The live Render backend | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |

The benchmarks report compile time, index build time, query time and candidate counts measured on
this machine. They make **no** claim about frames per second, GPU behaviour or pixel output, because
none of that can be measured here.

---

## 16. How to reproduce

```
sh tests/phase4/run_all.sh            # everything except the real browser
sh tests/phase4/run_all.sh --browser  # add the Chromium pass
```

Both work from a clean checkout and from any working directory. Nothing is read from `/tmp`;
`/tmp` is used only for run outputs.
