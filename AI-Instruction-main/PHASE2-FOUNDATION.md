# PHASE 2 — FOUNDATION (Project Hierarchy + Building Program Registry)

**Scope:** foundation only. No structural, MEP, fire/life-safety, evacuation, accessibility,
IFC, BOQ, or code-compliance engine. No fake compliance claims. Phase 1 behaviour preserved.

**Product frame:** AI Construction Studio is a **general-purpose** construction / digital-twin
platform. Industrial (warehouse/factory) is **one optional program among many** — it has no
privileged position in the core.

---

## 1. Core model (unchanged) vs Program (new, optional)

| CORE ENGINE (generic, unchanged) | PROGRAM (optional, additive) |
|---|---|
| geometry, levels/floors, spaces (rooms), walls, doors, windows | building-type vocabulary (aliases/keywords) |
| `objects[]` (people, vehicles, furniture, equipment) | space categories (classification only) |
| provenance (`source`, coverage semantics) | optional suggested spaces (guidance) |
| generic metadata, IDs | optional AI prompt context |

The renderer, compiler, validator and layout engine remain **program-agnostic**. A program never
injects geometry and never asserts a requirement.

## 2. Project hierarchy

```
PROJECT → SITE → BUILDING[] → LEVEL/FLOOR → SPACE → ELEMENTS/OBJECTS
```

```jsonc
{
  "schema": "acs.project/1",
  "project": {
    "id": "prj_0", "name": "…",
    "site": { "id":"site_0", "w":40, "d":30, "units":"m", "north":"-Z",
              "origin": {"x":0,"y":0,"z":0} },
    "buildings": [
      { "id":"bld_0", "name":"مبنى 1", "building_type":"villa",
        "programs":["villa"], "position":{"x":0,"z":0,"rotation":0},
        "active": true, "building": { /* Phase 1 building node, verbatim */ } }
    ],
    "meta": {"created_from":"phase1_building"}
  }
}
```

Multi-building (compound / campus / resort / mixed-use) is supported **at the data level**:
`project.buildings[]` holds any number of buildings, each with its own type, programs and
`position`. A full multi-building UI is **not** part of this phase.

## 3. Backward compatibility (no breaking change)

- A Phase 1 building (`{site, levels, floors, meta}`) is still valid and **is** a BUILDING node.
- `to_project()` / `toProject()` **wrap without copying** — the same object is reused, so no data
  can be lost or diverge. `toProject(project)` is idempotent.
- `active_building()` / `activeBuilding()` return the Phase 1-shaped node that the renderer,
  compiler and GLB exporter consume **unchanged**.
- `setModel()` accepts a project *or* a building.
- **JSON export is an additive envelope:** all Phase 1 fields stay at the file root (so existing
  consumers keep working) and `project{…}` is added alongside. No duplication of geometry.
- New IDs (`level.id`, `level.elevation`, `room.space_id`, `site.id`) are added only when absent.

## 4. Program registry — single source of truth

Canonical file: **`acs_programs.json`**.
- Backend consumes it directly (`acs_programs.py`).
- Frontend embeds a mirrored copy in `public/index.html` (kept offline-safe, no runtime fetch).
- A **drift test** in the suite fails the build if the two ever differ (ids, order, domain,
  categories, strong/weak keywords, space categories).

Programs: `residential, villa, apartment, hotel, resort, office, commercial, retail, restaurant,
clinic, hospital, school, university, government, parking, mixed_use, warehouse, factory,
industrial, logistics`.

Each program contributes only optional data: `aliases/keywords`, `space_categories`,
`suggested_spaces`, `program_context` (AI hint). **No mandatory requirements. No rules. No code claims.**

**Industrial domain is bit-identical to Phase 1**: `{warehouse, industrial, factory, logistics}` —
therefore `acs_validate.py`, `acs_layout.py` and `acs_compiler.py` required **zero** changes and
industrial isolation is unchanged.

## 5. Type detection — unified

Before: frontend was binary (`warehouse | residential`); backend had 4 types. They could disagree.
After: **one algorithm, one keyword set**, implemented identically in `acs_programs.detect_type()`
and `detectTypeJS()`:

- strong keyword = 3 pts, weak = 1 pt
- industrial is chosen only when `score ≥ 3` **and** it beats residential indicators
  (the Phase 1 guard that stops "رفوف تخزين" in a home from becoming a warehouse)
- ties break toward the program whose keyword appears **earliest** (the building's own noun)
- default: `residential`; an explicit UI selection always wins

Verified identical across frontend and backend for 10 building types.

## 6. Space categories (classification only — not rules)

`residential | hospitality | healthcare | workplace | retail | education | industrial | parking | mixed`
— e.g. healthcare → `clinical, diagnostic, patient, support, administration, circulation`.

## 7. Programs must not invent requirements

A program is **guidance**, never permission to fabricate. Anything a program or the AI contributes
that the user did not request must be classified `AI_SUGGESTED` / `SYSTEM_DEFAULT` — **never**
`USER_REQUESTED`, and never `CODE_REQUIRED` (which still requires `rule_id + standard + condition +
result`; count remains **0** because no rule engine exists). Suggested spaces are **not**
auto-injected into any model.

## 8. Coordinate system (documented, unchanged from Phase 1)

- **X** = width, east–west · **Z** = depth, north–south (`z = 0` is the north façade) · **Y** = up
- Units: **metres**. Origin `(0,0,0)` = site corner.
- Floor elevation = `level.index × floor_height` (stored additively as `level.elevation`).
- Building placement inside the site: `building.position { x, z, rotation° }` (default `0,0,0`).
- Three.js orientation is **unchanged**.

## 9. Stable IDs

`project.id` · `site.id` · `building.id` · `level.id` (`<bld>.flr_<n>`) · `room.space_id`
(`<bld>.<template>.<room>`). These exist so a future relationships graph can reference them.
**The relationships graph itself is not implemented.**

## 10. Migration strategy

No migration required. Old files load as-is; the project envelope is applied on demand
(`toProject`) and on export. Nothing rewrites stored data.

## 11. Files

New: `acs_programs.json`, `acs_programs.py`, `acs_project.py`, `PHASE2-FOUNDATION.md`.
Changed: `public/index.html` (registry mirror + project adapter + unified detection + export
envelope), `acs_understand.py` (delegates detection to the registry), `Dockerfile` (ships the new
modules).

## 12. Remaining future layers (NOT implemented)

Vertical connectivity graph · structural layer · MEP · fire/life-safety · evacuation ·
accessibility · code-rule engine (SBC/IBC/NFPA/ADA) · IFC · BOQ · maintenance / IoT digital twin ·
full multi-building & project-tree UI.

---

# PHASE 2 — RELATIONSHIPS & VERTICAL CONNECTIVITY FOUNDATION

Generic connectivity graph. **No evacuation, fire, MEP, structural, accessibility, code rules or
pathfinding** — data edges only.

## R1. Data model

`building.relationships[]` (intra-building) and `project.relationships[]` (project scope). Both
purely additive; an **empty array is valid** and is never padded with invented edges.

```jsonc
{ "id":"bld_0.rel_7", "type":"DOOR_CONNECTS",
  "from":"bld_0.g.majlis", "to":"bld_0.g.corridor",
  "via":"bld_0.g.majlis.door_0",
  "source":"geometry_inference", "status":"inferred",
  "meta":{"edge":"E","template":"g"} }
```

IDs reuse the Phase 2 stable IDs (`<bld>.<tmpl>.<room>`, `<bld>.flr_<n>`); relationship IDs are
namespaced per building/project so multi-building projects cannot collide.

## R2. Types (6, deliberately few)

`SPACE_ADJACENT` · `SPACE_CONNECTED` (reserved) · `DOOR_CONNECTS` · `VERTICAL_CONNECTS` ·
`LEVEL_CONNECTS` · `BUILDING_ON_SITE`.

## R3. Provenance & resolution

`source` ∈ `user | ai_inference | system_generated | geometry_inference | rule`
(`rule` is **rejected by the validator** — no rule engine exists).
`status` ∈ `confirmed | inferred | unresolved`.
**`confidence` is deliberately omitted** — no honest quantitative basis exists, and the spec allows
omission rather than fabrication.

## R4. Inference rules (evidence-gated)

- **Adjacency** — rectangles facing each other with overlap > 0 and gap ≤ `ADJ_TOL` (0.20 m, a wall
  thickness). `confirmed` when touching (≤ 0.02 m), else `inferred`. Container spaces (e.g. the
  industrial `envelope`) are excluded so they never masquerade as neighbours.
- **Doors** — probe 0.15 m outside the door's edge. Exactly one space found → `DOOR_CONNECTS`
  (`inferred`). Zero or ambiguous → `to: null`, `status: unresolved`, with a reason. **Never guessed.**
- **Vertical** — stair/elevator instances are clustered into *vertical cores* by position
  (`CORE_TOL` 1.5 m) across levels. A core present on ≥ 2 levels emits `VERTICAL_CONNECTS` between
  consecutive serviced levels (`inferred`), with `meta.serviced_levels`. A core on **one** level
  emits **no** connection — only an `unresolved` record. This is the permanent fix for
  "a stair mesh does not mean the floors are connected".
- **LEVEL_CONNECTS** — derived aggregate of proven vertical cores (`system_generated`).

## R5. Validation (structural only)

Dangling space/level refs · self-links · duplicate ids · duplicate edges · unknown type/source/status ·
`DOOR_CONNECTS` missing `via` · resolved edge missing an endpoint · cross-building refs without
explicit permission · `source=rule` without evidence. **No engineering compliance checks.**

## R6. Parity

The builder exists in Python (`acs_relations.py`, canonical) and JavaScript (mirrored in
`public/index.html`). A parity test asserts both produce **byte-identical graphs** on all fixtures.

## R7. Developer inspector (no production UI change)

Console-only: `ACS.relationships()`, `ACS.relationshipSummary()`, `ACS.relationshipIssues()`,
`ACS.spaceLinks(spaceId)`.

## R8. Measured graphs (executed)

| Fixture | Adjacent | Doors | Vertical | Level | Unresolved | Validator |
|---|---|---|---|---|---|---|
| Villa (2 levels) | 12 | 10 | 1 | 1 | 1 | 0 issues |
| Hotel (3 levels) | 5 | 2 | 4 | 2 | 0 | 0 issues |
| Clinic (1 level) | 5 | 3 | 0 | 0 | 0 | 0 issues |
| Office (2 levels) | 5 | 2 | 2 | 1 | 0 | 0 issues |
| Warehouse | 2 | 1 | 0 | 0 | 0 | 0 issues |

## R9. Not implemented (later phases)

Pathfinding · evacuation · fire/life-safety · MEP · structural · accessibility · code rules ·
physical inter-building circulation · relationship editing UI.

---

# PHASE 2 — CIRCULATION & PATHFINDING FOUNDATION

Answers only: **"is there a connectivity route through the relationship graph?"** It does **not**
answer whether a route is code-compliant, an evacuation route, accessible, or within any regulated
travel distance.

## N1. Architecture

```
RELATIONSHIP GRAPH  →  NAVIGATION GRAPH  →  PATH QUERY
   (source of truth)      (derived)          (result, not stored)
```
Navigation node = **a space on a specific level**: `"<space_id>@<level_index>"` — required because a
floor template may repeat across levels (a hotel's `guest_1` exists on 3 levels).
Relationships are the source of truth; **paths are query results and are not persisted**.

## N2. Edge eligibility (mandatory distinctions)

| Relationship | Traversable? |
|---|---|
| `DOOR_CONNECTS`, status `confirmed`/`inferred`, both endpoints | **Yes** |
| `DOOR_CONNECTS`, status `unresolved` | **No** — never in a primary path |
| `VERTICAL_CONNECTS` with valid `from_space/to_space/from_level/to_level` | **Yes** |
| `SPACE_ADJACENT` | **No** — adjacency ≠ an opening |
| `LEVEL_CONNECTS` (derived aggregate) | **No** |
| `BUILDING_ON_SITE` | **No** — not a walking edge |

## N3. Path result schema

```jsonc
{ "status":"FOUND", "from":"bld_0.g.majlis@0", "to":"bld_0.f.bed1@1",
  "nodes":[…], "edges":[…], "transitions":[…], "hops":3,
  "resolution":"contains_inferred_edges",
  "distance": null, "distance_status":"PARTIAL",
  "metrics":{"horizontal_centroid_m":9.43,"vertical_transitions":1,
             "measured_segments":"2/3","note":"مسافة بين مراكز الفراغات — ليست مسافة مشي…"},
  "reason": null }
```
`status` ∈ `FOUND | NO_PATH | UNRESOLVED | INVALID_SOURCE | INVALID_TARGET |
NOT_SUPPORTED_INTER_BUILDING`. `resolution` ∈ `confirmed | contains_inferred_edges | unresolved`.

## N4. Search & distance

**Minimum-hop BFS on unweighted topology** — deliberately *not* called "shortest distance", because
no trustworthy edge weights exist. `distance` is **always `null`**: true walking distance is not
computed. `metrics.horizontal_centroid_m` is derived from real rect centroids and is explicitly
labelled as *not* walking distance; vertical travel is marked `distance_measurable: false`.
`distance_status` is therefore `PARTIAL` or `NOT_MEASURED` — never "complete".

## N5. Transitions

Door: `{type, via, from, to, level, source, status}`. Vertical: `{type, kind, via, from_level,
to_level, from, to, source, status, distance_measurable:false}` — recorded in the **traversal**
direction and never collapsed into an invisible edge.

## N6. Provenance & unresolved handling

Each edge carries the originating relationship's `source`/`status`, and the path's `resolution`
degrades accordingly. Unresolved edges are excluded by default; `include_unresolved` is a
**debug-only** switch whose result is labelled `resolution: "unresolved"` and never presented as a
verified route. A default query also reports `unresolved_alternative_exists` as a hint.

## N7. Ambiguity is refused, not guessed

A bare space id on a template serving several levels returns `INVALID_SOURCE` with
`ambiguous_level: specify space@level (…)` rather than silently picking a level.

## N8. Multi-building

Intra-building pathfinding only. A cross-building query returns
`NOT_SUPPORTED_INTER_BUILDING` — **no site circulation is invented**.

## N9. Developer API (no production UI)

`ACS.findPath(a,b)` · `ACS.pathSummary(a,b)` · `ACS.navigationGraph()` · `ACS.navigationIssues()`.

## N10. Performance (executed)

| Spaces | Nav nodes | Nav edges | Nav graph build | Query |
|---|---|---|---|---|
| 100 | 202 | 201 | 2 ms | 1.1 ms |
| 500 | 1002 | 1001 | 4 ms | 5.9 ms |
| 1000 | 2002 | 2001 | 8 ms | 11.2 ms |

Relationship building is O(n²) in adjacency (≈0.9 s at 1000 spaces) — acceptable now, noted for
later optimisation rather than optimised prematurely.

## N11. Not implemented

Evacuation · fire/life-safety · accessibility · MEP · structural · code rules · weighted/real
walking distance · inter-building circulation · production routing UI.

---

# PHASE 2 — EGRESS & EVACUATION FOUNDATION (topology only)

Answers only: **what exits are represented, and which spaces can reach one through the connectivity
graph.** `compliance` is **always `NOT_EVALUATED`**. No fire, code, occupant-load, travel-distance,
exit-count, exit-width or accessibility evaluation exists.

## E1. Exit data model
```jsonc
{ "id":"bld_0.exit_1", "type":"exit", "building_id":"bld_0",
  "level_id":"bld_0.flr_0", "level":0, "space_id":"bld_0.g.majlis",
  "via":"bld_0.g.majlis.door_1", "destination":"exterior",
  "source":"geometry_inference", "status":"inferred",
  "meta":{"basis":"door_probe_outside_level_footprint"} }
```
`destination` ∈ `exterior | site | protected_area | unknown` — **no code meaning attached**.

## E2. Extraction rules (evidence-ordered, never invented)
1. **Explicit** `door.exit === true` / `door.destination` → `confirmed`.
2. **Geometry** — an unresolved door whose outward probe lands **outside the level footprint bbox**
   → `destination: exterior`, `inferred`. A door inside the footprint with an unknown other side is
   **not** an exit.
3. **Marker only** — a `points[].type === "exit"` in a space with no proven exterior door →
   `unresolved`, `destination: unknown`. `auto:true` ⇒ `system_generated`, else `user`.

`source = rule` is rejected by the validator. Unresolved exits are **never** promoted to a primary
destination, and a system-added exit is never labelled required.

## E3. Architecture
`RELATIONSHIP GRAPH → NAVIGATION GRAPH → EGRESS GRAPH → EGRESS QUERY`. The navigation engine is
**reused, not duplicated**; exits/relationships persist, paths are derived.

## E4. Query & selection
`find_egress(space)` → `FOUND | NO_EXIT_DEFINED | NO_PATH | UNRESOLVED_EXIT | INVALID_ORIGIN |
AMBIGUOUS_ORIGIN | NOT_SUPPORTED_INTER_BUILDING`. Candidates were ranked **only** by
`selection_basis: "minimum_hops"` (tie → exit id). The primary is a *documented topological
selection*, explicitly **not** "best/safest/shortest-distance/required".
**Superseded in part by §W7:** ranking becomes `minimum_measured_walking_distance` *only* when every
compared candidate measures `COMPLETE`; otherwise it stays `minimum_hops` and records why.

## E5. Characteristics (facts, not conclusions)
`door_count`, `vertical_transition_count`, `uses_stairs`, `uses_elevator`, `levels_crossed`,
`contains_inferred_edges`, `contains_unresolved_edges:false`. Elevator use is **recorded, never
judged** — no hardcoded "elevators may/may not be used". Stairs are `kind: stairs` only — never
"fire stair" or "protected".

## E6. Distance
`distance` stayed **`null`** in this sub-phase; `metrics.horizontal_centroid_m` keeps its explicit
"not walking distance" warning. No centroid value is ever promoted to walking distance.
**Superseded by §W:** `distance` is now populated **only** from measured model geometry and **only**
when `distance_status == "COMPLETE"`. The centroid diagnostic remains separate and is still never
promoted.

## E7. Audit schema
`spaces, nav_nodes, exits_total, confirmed_exits, inferred_exits, unresolved_exits,
nodes_with_reachable_exit, nodes_without_reachable_exit, spaces_without_nav_edges,
compliance:"NOT_EVALUATED"`.

## E8. Conditions kept distinct
`NO_EXIT_DEFINED` (nothing represented) ≠ `NO_PATH` + `reason: NO_PATH_TO_REPRESENTED_EXIT`
(exit exists, no topological route) ≠ `UNRESOLVED_EXIT` (marker without proven destination).
Nothing is auto-fixed: no door, corridor, stair or exit is ever created.

## E9. Performance (executed)
| Spaces | Exits | Extract | Audit | Query |
|---|---|---|---|---|
| 100 | 2 | 0 ms | 1 ms | 3 ms |
| 500 | 2 | 1 ms | 7 ms | 13 ms |
| 1000 | 2 | 3 ms | 14 ms | 31 ms |
Audit uses a single multi-source BFS from all exits (one pass, not per-space).

## E10. Developer API
`ACS.exits()` · `ACS.findEgress(id)` · `ACS.egressCandidates(id)` · `ACS.egressAudit()` ·
`ACS.egressIssues()` · `ACS.egressSummary(id)`.

## E11. Not implemented
Fire · code rules (SBC/NFPA/IBC/ADA/Civil Defense) · occupant load · travel-distance limits · exit
count/width/separation · dead-end limits · exit discharge · accessibility · fire compartments ·
site/assembly-area evacuation · production egress UI.

---

# PHASE 2 — REAL WALKING DISTANCE GEOMETRY FOUNDATION

*Measurement only. No code compliance, no fire rules, no occupant load, no exit limits, no
travel-distance maxima.* The layer answers exactly one question: **how many metres of this
already-existing route can actually be measured from the model's own geometry?**
It never answers: is this distance legal / within limit / safe / compliant.

## W1. Architecture (one direction, no shortcuts)
`RELATIONSHIP → NAVIGATION → PATH QUERY → ROUTE GEOMETRY → DISTANCE MEASUREMENT`
Geometry **measures an existing route**; it never creates connectivity. Relationships remain the
single source of truth. Measurement output is fully derived — it is never written back into the
building model.

## W2. Segment types and measurement bases
| Segment | Basis | Source of the number |
|---|---|---|
| `in_space` (normal room) | `straight_line_inside_rect` | the room rectangle + real anchors |
| `in_space` (long/thin, aspect ≥ 3) | `corridor_centerline` | centreline derived from the rectangle itself |
| `door_transition` | `door_geometry` | the model's own `wall_t` |
| `stair` | `stair_geometry` | `run_m`(+`rise_m`) **or** `risers`×`tread_m`(+`riser_m`) |
| `vertical_transport` (elevator) | `not_walking_distance` | never a walking length |
| anything unprovable | `unmeasured` | recorded with a stated reason |

"Corridor" here is **geometric** (aspect ratio ≥ `CORRIDOR_ASPECT = 3.0`), never nominal — a space
is not treated as a corridor because it is *named* one.

## W3. Anchors — no invented positions
Door crossing points come from the door's real `edge` + `offset` on the room rectangle
(N: `x+off, z` · S: `x+off, z+d` · W: `x, z+off` · E: `x+w, z+off`). If `edge` **or** `offset` is
not stated, `door_anchor` returns `null` and the segment becomes `unmeasured` — no default is
fabricated. Vertical elements (stairs/elevator) use their stated `x`/`z` (room-relative); when the
position is not stated the walk to/from that element is recorded as unmeasured
(`vertical_element_position_not_stated` / `vertical_element_arrival_position_not_stated`) rather
than silently skipped or replaced by the room centre.

## W4. What `walking_distance_m` means
Horizontal walking segments **plus** measured stair walking — nothing else. It excludes elevator
travel, excludes the centroid diagnostic, and excludes every unmeasured segment. It is populated
**only** when `distance_status == "COMPLETE"`; in every other state it is `null`.

## W5. Status vocabulary
`COMPLETE` (every required segment measured) · `PARTIAL` (some segment unprovable — the measured
horizontal amount is reported separately as `measured_horizontal_m`) · `NOT_MEASURED` ·
`GEOMETRY_NOT_SUPPORTED` (a space on the route is not rectangular — no straight line is drawn
through walls) · `INVALID_PATH` (no `FOUND` topological route to measure).
`origin_basis` is always declared: `explicit_origin_point` · `space_centroid_fallback` ·
`unmeasured`. When the centroid fallback is used on a COMPLETE measurement, the result carries an
explicit note stating that assumption.

## W6. Vertical movement
Stairs are measured **only** from geometry present in the model; absent stair dimensions →
`unmeasured` + reason, never an invented riser/tread. Elevators are recorded as
`vertical_transport` with `elevation_change_m` and contribute **zero** to walking distance.
`vertical_elevation_change_m` is reported as an independent fact, never merged into the walk.

## W7. Egress integration (guarded ranking)
Every egress candidate carries an additive `distance_measurement`; the destination point is the
**exit door's own anchor**, not the room centre. Ranking:
* all candidates `COMPLETE` → `selection_basis: "minimum_measured_walking_distance"`;
* otherwise → `selection_basis: "minimum_hops"` **plus** `selection_basis_reason`
  (`geometric shortest route not claimed: <n> PARTIAL, <m> GEOMETRY_NOT_SUPPORTED …`).
`compliance` stays `NOT_EVALUATED` everywhere; `alternative_exits` carry their own
`distance_status` and `walking_distance_m`.

## W8. Structural validation (not compliance)
`validate_measurement` rejects: NaN/negative lengths · unknown bases · segment sum ≠
`horizontal_m` · `COMPLETE` with unmeasured segments · `walking_distance_m` set without
`COMPLETE` · any walking length attached to elevator travel.

## W9. Parity (executed)
`acs_distance.py` ↔ the in-page mirror: **26/26 scenarios byte-identical** (19 COMPLETE, 4 PARTIAL,
1 GEOMETRY_NOT_SUPPORTED, 1 INVALID_PATH, 1 NO_PATH egress) under canonical key-sorted comparison,
covering measurements, structural issues and summary strings. `math.hypot` was replaced with an
explicit `sqrt(dx²+dz²)` on both sides, and Python's `round()` (half-to-even) is mirrored exactly in
JS — verified against real Python output over 219 values × 3 modes.

## W10. Performance (executed — 41 spaces, 119 relationships)
| Queries | Path | Geometry + measurement | Total |
|---|---|---|---|
| 100 | 31.9 ms (0.319 ms/q) | 5.9 ms (0.059 ms/q) | 37.9 ms |
| 500 | 54.2 ms (0.108 ms/q) | 21.5 ms (0.043 ms/q) | 75.7 ms |
| 1000 | 105.2 ms (0.105 ms/q) | 27.3 ms (0.027 ms/q) | 132.5 ms |
Python mirror, same shape: 1000 queries → path 232.1 ms, measurement 41.3 ms. Measurement is
strictly cheaper than the path query it measures; nothing is cached between queries.

## W11. Developer API (no production UI change)
`ACS.measurePath(from,to[,opt])` · `ACS.pathGeometry(from,to)` · `ACS.measureEgress(space)` ·
`ACS.distanceIssues([from,to])` · `ACS.distanceSummary(from,to)`.
`opt.origin` / `opt.destination` accept explicit points and are reflected in `origin_basis`.

## W12. Not implemented (still absent, deliberately)
Travel-distance limits · common-path / dead-end limits · occupant load · exit count/width/
separation · fire ratings or protected stairs · elevator-permission rules · accessible-route
grading · non-rectangular (polygon) route geometry · furniture/obstacle-aware routing ·
door swing/clear width · any SBC / IBC / NFPA / ADA / Civil-Defense evaluation.

---

# PHASE 2 — CODE RULE ENGINE FOUNDATION (evidence-gated architecture only)

**Regulatory rule count after this phase: ZERO.** No SBC / IBC / NFPA / ADA / Civil-Defense /
municipality / health / education value is encoded anywhere. This phase builds the machine that
*could* evaluate such rules once their official text is supplied and approved — and the gates that
stop anything unproven from ever executing as compliance.

## C1. Architecture
`RULE SOURCE REGISTRY → RULE DEFINITION → APPLICABILITY → INPUT RESOLUTION → DATA-QUALITY GATE →
EVALUATION → EVIDENCE → RESULT`. The engine is **read-only**: it never touches geometry, never
adds an exit/door/stair, and is deliberately not wired to any auto-fix path. This phase implements
VALIDATION only; the later `VALIDATION → RECOMMENDATION → USER APPROVAL → MODEL CHANGE` chain does
not exist yet.

## C2. RuleDefinition schema
`rule_id · namespace · regulatory · title · category · severity · enabled · revision · standard ·
edition · section · jurisdiction_required · jurisdiction{country,region,authority} ·
source{type,source_id,document_id,page,clause,url,verified} · subject_type ·
applies_to{subject_type,conditions[]} · inputs[{key,unit,required,quality}] · operator · expected`.
Identity is `rule_uid = standard|edition|section|rule_id|rREVISION` — a rule's meaning can never
change silently.

## C3. Mandatory evidence
A rule executes as **regulatory** only with: `rule_id`, `standard`, `edition`, `section`, a source
document reference (`document_id` or `url`), `source.verified === true`, a real `applies_to`,
declared `inputs`, and a known `operator`/`expected`. Anything missing ⇒ `INVALID_RULE_DEFINITION`
and the rule does not run. Synthetic rules are forced the other way: `regulatory:false`,
`namespace:"TEST_ONLY"`, `source.type:"synthetic_test"`, `rule_id` prefixed `TEST_ONLY.`.

## C4. RuleSource registry
Nine descriptors ship: SBC, IBC, NFPA, ADA, CIVIL_DEFENSE, MUNICIPALITY, HEALTH_FACILITY,
EDUCATION — each `status:"NOT_LOADED"`, `verified:false`, `edition:null` (no edition is invented) —
plus `synthetic_test` (`status:"SYNTHETIC"`).

## C5. Jurisdiction
`country · region · authority`, declared by the project context only. Arabic input never implies a
country — a test asserts this explicitly. A rule with `jurisdiction_required` and no declared
country ⇒ `NOT_EVALUATED / JURISDICTION_NOT_SET`; a declared but different country ⇒
`NOT_APPLICABLE / JURISDICTION_MISMATCH` (never FAIL).

## C6. Versioning & edition isolation
A project pins editions via `context.edition_pin = {STANDARD: EDITION}`. A rule from another
edition of that standard ⇒ `NOT_APPLICABLE / EDITION_NOT_PINNED`. Where the same `rule_id` exists
in two editions, lookup by id alone is treated as **ambiguous**: the CODE_REQUIRED gate refuses it
and the developer API returns `UNSUPPORTED / AMBIGUOUS_RULE_ID` rather than picking one.

## C7. Applicability ≠ existence
`applies_to.conditions` use resolvable contract inputs with `in` / `equals` / `not_in`. Missing
classification data ⇒ `INSUFFICIENT_DATA` (never a guess, never NOT_APPLICABLE).
`NOT_APPLICABLE`, `NOT_EVALUATED` and `INSUFFICIENT_DATA` stay three distinct outcomes.

## C8. Input contract
23 declared keys across ROUTE, EGRESS, DOOR, SPACE and BUILDING, resolved from existing model
APIs only. A key outside the contract is a definition error. Absent model fields are reported as
absent — e.g. `door.clear_width` is read from a stated `clear_width_m` and is **never** derived
from the door's opening `width`.

## C9. Data-quality gate
An input may declare `quality {status_key, accept[], reasons{}}`. The gate runs **before** the
required-input check, because "the data isn't good enough" explains an absent value better than
"value missing". So `distance_status = PARTIAL` ⇒ `NOT_EVALUATED / INCOMPLETE_DISTANCE_MEASUREMENT`,
`GEOMETRY_NOT_SUPPORTED` ⇒ `NOT_EVALUATED / GEOMETRY_NOT_SUPPORTED`, `NOT_MEASURED` ⇒
`DISTANCE_NOT_MEASURED`, `INVALID_PATH` ⇒ `INVALID_PATH`.

## C10. Result schema & states
`rule_id · rule_uid · rule_revision · namespace · regulatory · ruleset_id/version · standard ·
edition · section · severity · status · subject_type · subject_id · applicability · data_quality ·
reason · actual · required · input_provenance · inputs · evidence · engine_version · evaluated_at ·
code_required_eligible · definition_issues`.
States: `PASS · FAIL · NOT_APPLICABLE · NOT_EVALUATED · INSUFFICIENT_DATA ·
INVALID_RULE_DEFINITION · UNSUPPORTED` — never collapsed.
`evaluated_at` comes from the caller's context; the engine invents no clock (this also keeps
results reproducible and parity-comparable).

## C11. PASS/FAIL semantics
PASS/FAIL require: valid definition **and** `applicability === APPLICABLE` **and**
`data_quality === COMPLETE` **and** an executed comparison. Missing data never becomes PASS and
never becomes FAIL — asserted across every result the suite produces.

## C12. Evidence chain
Each result carries the rule source (standard/edition/section/verified), the jurisdiction when one
gated the evaluation, the path and its hop count, the measurement status and segment count, the
door/space/building the number came from, and — when a quality gate fires — the actual status
versus the accepted set. A FAIL is auditable back to the geometry that produced the number.

## C13. Provenance
Every resolved input records `user · ai_inference · system_default · geometry_inference · rule`.
Route inputs take the **weakest** source on the route, so inferred connectivity is never laundered
into confirmed fact. Results may be produced from inferred data, but always disclose it.

## C14. Units & precision
16 units over 8 dimensions; comparison always happens in the dimension's base unit and a
cross-dimension comparison is refused (`UNSUPPORTED`). `evaluation_value` is unrounded — the
measurement layer now publishes `walking_distance_exact_m` alongside the 3-dp display value, and
the engine evaluates the exact one. `display_value`/`display_unit` are separate and never feed a
comparison (24.90548817090728 evaluates; 24.905 m displays; 0.95 m displays as 950 mm).

## C15. Expression safety & import security
Rules are **data**. No `eval`, no `exec`, no `new Function`, no dynamic expression execution on
either side — asserted by tests over the engine source itself. Imported rulesets are untrusted:
rejected for unknown operators, unknown units, inputs outside the contract, unknown subject types,
unknown severity/completeness, forbidden executable-looking keys (`script`, `function`,
`__proto__`, …), `javascript:`/`data:` strings, non-https source URLs, duplicate rule identities,
nested composite operators, and `complete_for_declared_scope` without a declared scope.

## C16. CODE_REQUIRED gate
`hasRuleEvidence` no longer accepts field presence alone. A CODE_REQUIRED claim now requires the
cited rule to be **loaded in the registry, regulatory, source-verified, definition-valid and
unambiguous**. Synthetic TEST_ONLY rules can never open it. Since the registry ships zero
regulatory rules, CODE_REQUIRED remains structurally impossible in this phase.

## C17. Aggregation semantics
`rules_evaluated · pass · fail · not_applicable · not_evaluated · insufficient_data ·
invalid_rules · unsupported · regulatory_results · synthetic_results · regulatory_rules_loaded ·
completeness · coverage_scope`. `overall_compliance` is **`NOT_DETERMINED`** unless regulatory
rules were evaluated, the ruleset declares `complete_for_declared_scope`, and nothing was
unevaluated/insufficient/invalid/unsupported. The statement reads "evaluated against N configured
rules" and can never read "the building is compliant".

## C18. Storage
Rule library and project data are separate: `acs_rules.json` (registry) is never embedded in a
building model; a project references `ruleset_id` + `edition` + `jurisdiction`. Results are
exportable separately and carry rule_uid, ruleset version, engine version, subject ids, input
values and the caller-supplied timestamp — enough to reproduce them, with no claim of staying
valid after the geometry changes.

## C19. AI boundary
LLM output can never become an executable rule: a rule must pass `validate_rule` with a verified
non-synthetic source, and the AI path has no way to set `source.verified`. AI may later map facts
to declared inputs, explain a verified rule, or summarise results — authoritative content comes
only from the registry.

## C20. Parity & tests (executed)
Rule suite **129/129** in Node and **129/129** in real Chromium. JS↔Python **28/28 byte-identical**
scenarios (12 PASS, 3 FAIL, 3 NOT_EVALUATED, 4 NOT_APPLICABLE, 2 INSUFFICIENT_DATA, plus 3 whole
ruleset runs with aggregation). The browser registry is proven byte-identical to `acs_rules.json`
by a drift test, so rule content is never hand-maintained twice.

## C21. Performance (executed — villa model, 5 subjects incl. route geometry)
| Rules | Evaluations | Validate | Evaluate | Aggregate |
|---|---|---|---|---|
| 100 | 500 | 4.5 ms | 16.8 ms (0.034 ms/eval) | 0.4 ms |
| 500 | 2500 | 5.5 ms | 46.1 ms (0.018 ms/eval) | 0.4 ms |
| 1000 | 5000 | 8.4 ms | 77.8 ms (0.016 ms/eval) | 0.8 ms |
Subject resolution (including route geometry measurement) took 4.8 ms for 5 subjects.

## C22. Developer API (no production UI)
`ACS.rules()` · `ACS.ruleSources()` · `ACS.ruleSets()` · `ACS.ruleSubject(id)` ·
`ACS.evaluateRule(ruleId, subjectId[, ctx][, ruleSetId])` ·
`ACS.evaluateRuleSet(ruleSetId, subjectIds[, ctx])` · `ACS.ruleIssues()` ·
`ACS.complianceSummary(ruleSetId, subjectIds[, ctx])` · `ACS.regulatoryRuleCount()`.
Subject ids: `BUILDING:<id>` · `SPACE:<id>` · `DOOR:<space>.door_<i>` · `ROUTE:<from>><to>` ·
`EGRESS:<space>`.

## C23. Known limitations
No regulatory content of any kind · no fire, occupant-load, accessibility, structural or MEP
engine · no remediation or auto-fix · no rule authoring UI · rules for only 5 of the 14 declared
subject types are resolvable today (ROUTE, EGRESS, DOOR, SPACE, BUILDING) · composite operators do
not nest · no model-revision hash on exported results (stale results are therefore not treated as
authoritative) · `space.level` is declared in the contract but not resolvable from the current
model and correctly reports as absent.

---

# PHASE 2 — AUTHORITATIVE RULE PACK INGESTION & VERIFICATION FOUNDATION

**Real regulatory rule count after this phase: ZERO.** Every document, fragment, candidate and pack
shipped here is synthetic (`synthetic:true`, `official:false`, `regulatory:false`,
namespace `TEST_ONLY`). No standard text, clause number, edition, page or URL of any real code
appears anywhere. This phase builds the *road* real code must travel — and the gates along it.

## I1. Pipeline
`OFFICIAL SOURCE → SOURCE DOCUMENT → METADATA → CLAUSE/FRAGMENT → CANDIDATE RULE →
EXPLICIT VERIFICATION → VERIFIED RULE → VERSIONED RULE PACK → PROJECT ACTIVATION → RULE ENGINE`
Nine documented stages. Extraction is not verification, verification is not activation, and no
step may be skipped: `EXTRACTED → VERIFIED` is not a legal transition, and there is no `ACTIVE`
candidate state at all.

## I2. SourceDocument
`document_id · source_id · title · standard · edition · jurisdiction{country,region,authority} ·
document_type · official · synthetic · origin{type,url,filename} · integrity{sha256,size_bytes} ·
verification{status,method,evidence,verified_at,verified_by} · relations[] · history[]`.
Origins: `uploaded_file · official_url · manual_reference` — web access is never required.

## I3. Source states
`UNVERIFIED → SOURCE_IDENTIFIED → OFFICIAL_SOURCE_VERIFIED → CONTENT_VERIFIED`, plus terminal
`SUPERSEDED · REVOKED · INVALID`. Officialness and content correctness are **separate**: a document
can come from an official source and still be the wrong edition, incomplete, superseded or an
amendment. `UNVERIFIED → CONTENT_VERIFIED` is refused; every forward transition demands a
verification method **and** recorded evidence; and `OFFICIAL_SOURCE_VERIFIED` is refused unless the
document is marked official by evidence — a title that *looks* official proves nothing.

## I4. Integrity
Real SHA-256 over the document's UTF-8 bytes, in both languages (a pure-JS implementation, verified
against Python over the standard vectors and 10 payloads). Identity is the hash, never the filename.
A new edition is a new document; changed bytes at the same URL are a new revision. Verified rules
stay pinned to the hash they were verified against — changed bytes yield `SOURCE_HASH_MISMATCH` and
the old record is **never** silently re-pointed.

## I5. Clause fragments
`fragment_id · document_id · document_hash · section · clause · page · kind · text_reference ·
excerpt · normalized_meaning · location{start,end} · extraction_method · status`.
Kinds: `clause · table_row · table_cell · definition · exception · footnote`.
Source text, fragment, candidate and rule stay four separate objects — extracting one number does
not create a rule.

## I6. Copyright-safe storage
Excerpts are capped at 300 characters and a longer one is rejected outright; a fragment must carry
at least a `text_reference` pointer. The pack stores metadata, hashes, locations and structured
rule definitions — never a reproduction of a standard. The audit export carries no excerpt text at
all and states its copyright position explicitly.

## I7. CandidateRule
`candidate_id · document_id · document_hash · fragment_ids[] · section · clause · page ·
extraction_method · interpretation_method · ai_assisted · proposed_rule · exceptions[] ·
cross_references[] · definition_refs[] · table_context · status · status_detail · verification ·
history[]`. States: `EXTRACTED · NEEDS_INTERPRETATION · NEEDS_CROSS_REFERENCE ·
NEEDS_EXCEPTION_REVIEW · READY_FOR_VERIFICATION · REJECTED · VERIFIED`. A candidate is never
executable by the rule engine — only a verified candidate inside an activated pack is.

## I8. Assessment
`assess_candidate` derives the state the evidence *earns* — it never raises a candidate to
VERIFIED. Broken fragment references or a hash mismatch ⇒ `REJECTED`; unresolved cross references ⇒
`NEEDS_CROSS_REFERENCE`; open exceptions ⇒ `NEEDS_EXCEPTION_REVIEW`; missing definition fragments or
a missing interpretation method ⇒ `NEEDS_INTERPRETATION`.

## I9. AI boundary
`ai_assisted` is a mandatory explicit field and reduces **no** evidence requirement: the AI-assisted
fixture still needs the document CONTENT_VERIFIED, the hash matched and the fragments cited.
`verification_method: "ai_suggestion"` is rejected with `AI_MAY_NOT_VERIFY` for both candidates and
packs. AI cannot mark a source official, choose an edition, invent a clause, verify a candidate or
activate a pack.

## I10. Verification gate
The only path to VERIFIED is an explicit verification operation. The record holds verifier, method,
timestamp, document id and hash, rule-definition hash, cited fragment ids, the `ai_assisted` flag
and notes. No user identity is fabricated — `verifier` stays `null` and the method is
`explicit_manual_approval` when no auth system exists.

## I11. Rule definition hash
SHA-256 over a canonical JSON of the meaning-bearing fields only (rule_id, standard, edition,
section, applies_to, inputs, operator, expected, exceptions, revision, subject_type, jurisdiction).
Changing the wording of a title does not change it; changing an expected value does — and the old
verification then reports `RULE_DEFINITION_CHANGED` instead of silently covering the new meaning.

## I12. RulePack
`rulepack_id · version · standard · edition · jurisdiction · source_documents[] · candidate_ids[] ·
verification{status,method,verified_at,verified_by,notes} · coverage_scope[] · completeness ·
regulatory · synthetic · history[]`. States: `DRAFT → UNDER_REVIEW → VERIFIED_PARTIAL |
VERIFIED_FOR_DECLARED_SCOPE`, plus `SUPERSEDED · REVOKED`. There is deliberately no bare `VERIFIED`
state that would hide scope. `VERIFIED_FOR_DECLARED_SCOPE` is refused unless completeness is
explicitly `complete_for_declared_scope` with a declared scope; a pack containing an unverified or
stale-verified candidate cannot be verified at all.

## I13. Activation
`IMPORTED ≠ VERIFIED ≠ ACTIVATED`. A verified pack does nothing until the project references it by
`rulepack_id` + `version` with `enabled:true`. Absent reference, disabled reference, wrong version,
unverified pack and invalid pack each produce a *stated rejection reason*, never silent activation.
Activation is never inferred from building type or from any other model fact.

## I14. Conflicts
Documents carry `supersedes · superseded_by · amends · amended_by · references · depends_on` so
precedence can be *expressed*, but no legal precedence is implemented. Two activated packs carrying
the same `rule_id` with different definition hashes produce `RULE_CONFLICT`, and every affected rule
returns `NOT_EVALUATED` — no arbitrary winner is picked.

## I15. Applicability trace
Every evaluated result now carries `applicability_trace`: the edition pin, the jurisdiction, the
subject type and each applicability condition with its expected value, actual value and whether it
was satisfied. "Rule applied" alone is no longer an acceptable output.

## I16. Import security
Documents are data and are never executed. Rejected: duplicate document/fragment/candidate ids and
duplicate pack id+version, non-64-hex digests, non-integer sizes, missing referenced documents,
broken fragment references, unknown origin/status/kind/extraction/verification/relation values,
non-https official URLs, `<script>`/`javascript:`/`data:text/html` strings, executable-looking keys,
oversized excerpts, flattened table candidates, candidates claiming VERIFIED without a record,
regulatory candidates on non-CONTENT_VERIFIED or non-official documents, and unknown
operators/units (delegated to the rule validator). No `eval`, `exec`, `new Function`, shell or
remote include exists on either side — asserted against the source text itself.

## I17. Tests & parity (executed)
Ingestion suite **145/145** in Node and **145/145** in real Chromium, zero page errors.
JS↔Python **30/30 byte-identical** steps covering hashing, state transitions, verification refusals
and successes, assessment of every fixture candidate, pack flow, project evaluation under two
editions, conflict handling, audit export and four import-rejection cases. A drift test proves the
embedded browser fixtures are byte-identical to `acs_ingest.json`.

## I18. Performance (executed)
| Candidates | Source validate | Candidate validate | Verify (incl. SHA-256) | Pack assembly | Activation lookup | Evaluate |
|---|---|---|---|---|---|---|
| 100 | 0.6 ms | 15.3 ms | 50.2 ms | 38.1 ms | 18.0 ms | 22.9 ms |
| 500 | 0.1 ms | 21.0 ms | 66.3 ms | 56.0 ms | 87.5 ms | 103.5 ms |
| 1000 | 0.2 ms | 46.9 ms | 106.0 ms | 128.7 ms | 225.4 ms | 208.0 ms |
Activation lookup re-validates the whole pack on every call — correctness before caching; no
premature optimisation.

## I19. Developer API
`ACS.ruleDocuments()` · `ACS.ruleFragments([documentId])` · `ACS.ruleCandidates()` ·
`ACS.rulePacks()` · `ACS.ruleSourceIssues()` · `ACS.verifyCandidate(id, opts)` ·
`ACS.verifyRulePack(id, version, opts)` · `ACS.activateRulePack(id, version[, enabled])` ·
`ACS.deactivateRulePack(id, version)` · `ACS.activeRulePacks()` · `ACS.setJurisdiction(j)` ·
`ACS.projectCodeContext()` · `ACS.rulePackSummary(subjectIds[, ctx])` · `ACS.ruleAudit()`.
The session starts with the synthetic fixtures loaded and **nothing activated**.

## I20. Known limitations
No real regulatory content and no ingestion of any actual standard · no PDF/OCR text-layer
extraction implemented (methods are declared, extraction itself is out of scope here) · no user
authentication, so verifier identity stays null rather than invented · no legal precedence
resolution between base code, amendment and local amendment · no model-revision hash binding
evaluation results to geometry · definitions are referenced but no definition content is populated ·
activation revalidates rather than caches · rule packs cannot yet be signed.

---

# PHASE 2 — SBC 201 PILOT, INGESTION RUN #1 (source authentication only)

**Outcome: the supplied file is authenticated but carries no clause text, so ZERO candidate rules
were produced. Real regulatory rules verified = 0, active = 0, CODE_REQUIRED = 0.**

## S1. Document registered
`acs_sources.json` is a new, separate register for **real** source documents — metadata, integrity
hashes and table-of-contents locators only. Synthetic fixtures stay in `acs_ingest.json`; the two
never mix. Loaders: `acs_ingest.real_store()` / `ingestRealStore()`.

| Field | Value (from the document itself) |
|---|---|
| document_id | `SBC201-CC-2024` |
| Title | The Saudi General Building Code — SBC 201 - CC — Code & Commentaries |
| Standard / edition | `SBC 201` / `2024` (cover art and the running footer `SBC 201-CC-2024`) |
| Jurisdiction | Kingdom of Saudi Arabia (cover mark), authority `null` — the issuing body's legal name is not printed in the supplied pages |
| Document type | `excerpt_front_matter_and_table_of_contents` · completeness `excerpt` |
| Origin | `uploaded_file` → `SBC201_CC_241224FA.pdf` |
| SHA-256 | `5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06` |
| Size | 3 270 898 bytes · 10 pages |
| Status | `OFFICIAL_SOURCE_VERIFIED` — **not** `CONTENT_VERIFIED` |

## S2. Why CONTENT_VERIFIED was withheld
The file is the cover plus the table of contents (printed roman pages xiii–xxi). Measured content
inventory: 0 occurrences of "shall", no clause, table, exception, footnote or definition text.
There is nothing whose content could be verified, so the two states stayed separate exactly as the
model requires. The withholding itself is recorded as transition evidence.

## S3. Evidence retained
Transition history now stores the evidence of **every** step, not just the latest — so the
`SOURCE_IDENTIFIED` evidence (including the user's origin claim, recorded as a *claim*, not proof)
survives the later `OFFICIAL_SOURCE_VERIFIED` transition.

## S4. Locators, not clauses
32 `toc_locator` fragments were recorded — the Means of Egress chapter entry plus its 31 sections
(1001–1031) with the page numbers printed in the table of contents. A new fragment kind
`toc_locator` was added because a table-of-contents entry is a navigation pointer, not a
requirement; it can never be mistaken for a clause. Chapter bounds: Means of Egress begins at
printed page 996; the next chapter (Accessibility) begins at 1287.

## S5. Zero candidates, by design
No `CandidateRule` was created. A number cannot be extracted without applicability context, and no
number exists in the supplied pages. A regulatory candidate pinned to this document is refused by
the pipeline with `regulatory candidate references a document that is not CONTENT_VERIFIED` — a
test asserts exactly that, and asserts `codeRequiredAllowed` stays false for any SBC rule id.

## S6. Tests
Ingestion suite **167/167** in Node and **167/167** in real Chromium (22 new assertions covering
the real register: hash, size, edition provenance, jurisdiction evidence, state separation, excerpt
inventory, locator-only fragments, zero candidates/packs/activation, and refusal of a regulatory
candidate on a non-content-verified document). Security suite extended to **35/35**, including
"no `shall` anywhere in the real register" and "no candidates or packs in the real register".

## S7. Ingestion run #2 — second file, chain of custody enforced

A second file was supplied: **SBC 201 - CR, Code Requirements, edition 2018**, SHA-256
`e8f3afc4064a5eaa6ee6f4809a4d3357b0dc20bcfcd93afcf4db51ee6843b972`, 7 469 728 bytes, 50 pages.
It self-identifies (`SBC 201-CR-18` footer, `COPYRIGHT © 2018`) and — unlike the 2024 file — names
the issuing authority explicitly: **Saudi Building Code National Committee (SBCNC)**.

It contains front matter, the key list, the copyright and committee pages, the preface, the full
table of contents, Chapter 1 complete and Chapter 2 (Definitions) partial. **Chapter 10 Means of
Egress appears in the table of contents only** (printed page 372; §1017 at page 403); its clause
text is absent. Candidates producible: **zero**, again.

Two provenance facts were recorded rather than glossed over: the supplied filename indicates a
third-party document-sharing site, not the issuing authority; and the document's own notice
prohibits reproduction or distribution — including publishing on cloud sites — without written
permission. It is registered `official: false`, stopped at `SOURCE_IDENTIFIED`, with a `licensing`
block recording `redistribution_permitted: false` and `permission_evidence: null`.

**New engine rule (chain of custody).** `origin.origin_authority` was added with values
`issuing_authority · authorized_distributor · third_party_redistribution · unknown`. A document may
not be marked `official` unless its origin authority is one of the first two, and
`transition_document` refuses `OFFICIAL_SOURCE_VERIFIED` with `ORIGIN_NOT_IN_OFFICIAL_CHAIN` even if
`official` is forced true. A re-hosted copy can never become an official source, however authentic
its content looks.

The 2018 and 2024 files are registered as two separate documents with separate hashes; the newer
edition was not silently preferred, and no `supersedes` relation was asserted because neither
document states one. Ingest suite: **182/182** in Node and in Chromium.

## S8. Ingestion run #3 — IBC 2024 link refused, and the guard it produced

A link to ICC Digital Codes, *Chapter 10 Means of Egress — 2024 International Building Code*, was
supplied. It was **not** registered as a source document, for three independent reasons:

1. **Wrong standard.** The pilot targets SBC 201. IBC is a different code by a different publisher.
2. **Wrong base edition even as a reference.** The SBC 201-CR-18 preface states that *"2015
   International Building Code (IBC 2015), published by the International Code Council (ICC), is the
   base code in the development of this Code"* and that *"many changes and modifications were made
   in its base code (IBC 2015)"* for Saudi conditions. IBC **2024** is not the base of SBC 201-2018,
   and the Saudi modifications are not quantified anywhere in the supplied pages.
3. **No obtainable bytes.** The chapter text sits behind a Digital Codes Premium subscription, so no
   integrity hash could be computed. A document cannot enter the register without one — registering
   a hash of a paywall shell would be worse than registering nothing.

The base-code relationship is recorded on the 2018 document as `base_code` metadata with its
evidence quote and the explicit implication that *IBC text is not evidence for an SBC requirement*.

**New engine rule (no cross-standard substitution).** `validate_candidate` now rejects
`STANDARD_MISMATCH` when a rule's declared standard differs from its cited source document's
standard, and `EDITION_MISMATCH` when the editions differ. Encoding an IBC value while citing an
SBC document is now structurally impossible, as is citing a 2018 document for a 2024 rule.
Ingest suite: **188/188**.

---

# PHASE 2 — REGULATORY OCCUPANCY & CODE CONTEXT FOUNDATION

**Real regulatory occupancy classifications after this phase: ZERO.** Every classification shipped
is `TEST_OCC_*`, `regulatory: false`, `synthetic: true`. No SBC or IBC occupancy group name appears
anywhere in the shipped classification content.

## O1. The separation this layer exists to enforce
`BUILDING PROGRAM ≠ REGULATORY OCCUPANCY ≠ PROJECT JURISDICTION ≠ RULESET ACTIVATION`.
`acs_programs.json` stays product vocabulary; a test asserts it was not turned into a
classification registry. A program can only *suggest*, and only when a classification pack is
already activated — suggestions come from the pack's own `program_hints`, never from a hardcoded
unsourced table.

## O2. CodeContext (additive)
`jurisdiction{country,region,authority}` · `code_context{standard,edition,rulepacks[],
classification_packs[]}` · `occupancy{status,classifications[]}`. Everything starts null/empty, and
a pack reference must state `enabled` explicitly. Building JSON is untouched — Phase 1/2 models
carry no code context.

## O3. OccupancyClassification
`id · subject_id · subject_type · classification_system · standard · edition · jurisdiction ·
group · subgroup · pack_id · pack_version · source · status · evidence[] · declared_value ·
declared_by · declaration_time · verification · regulatory · synthetic · history[]`.

## O4. States and provenance
States: `UNCLASSIFIED · CANDIDATE · NEEDS_INFORMATION · READY_FOR_VERIFICATION · VERIFIED ·
CONFLICT · NOT_APPLICABLE`, with an explicit transition table — `UNCLASSIFIED → VERIFIED` is not a
legal move. Provenance: `USER_DECLARED · AUTHORITATIVE_MAPPING · MANUAL_VERIFIED · AI_SUGGESTED`.
Only `VERIFIED` satisfies rule applicability; `CANDIDATE` never does.

## O5. Verification gate
One explicit path to VERIFIED. It requires a known method (never `ai_suggestion`), recorded
evidence, a pack that is itself verified **and** activated in the project, and a group that exists
in that pack. On success the source becomes `MANUAL_VERIFIED` and the original source is retained
as `source_before` — a human took responsibility, and the record says whose suggestion it was. No
verifier identity is invented when no auth exists.

## O6. Mixed occupancy
Classifications attach to `PROJECT · SITE · BUILDING · LEVEL · SPACE · ZONE`. Different groups on
different subjects coexist without collapsing to one building-wide value, and the building itself
stays `UNCLASSIFIED` unless classified in its own right. `building_type: mixed_use` remains a
product label with no regulatory meaning. No separation, rated assembly or fire boundary is ever
claimed.

## O7. Classification pack
`pack_id · version · classification_system · standard · edition · jurisdiction ·
source_documents[] · classifications[] · program_hints[] · verification · coverage_scope[] ·
completeness · regulatory · synthetic`. Lifecycle mirrors the rule pack: `DRAFT → UNDER_REVIEW →
VERIFIED_PARTIAL | VERIFIED_FOR_DECLARED_SCOPE`, plus `SUPERSEDED · REVOKED`. A regulatory pack must
cite source documents. Nothing activates without an explicit project pin.

## O8. Rule-engine integration
Six read-only contracts: `occupancy.status · group · subgroup · standard · edition ·
jurisdiction_country`, resolvable for any subject type. `group` and its siblings are published
**only** when the resolved status is `VERIFIED`.

A generic, declarative **alignment** mechanism was added to the rule engine: an input may declare
`alignment: [{input, rule_field, reason}]`, and the engine refuses to evaluate when the resolved
value differs from the rule's own field. This is how edition and jurisdiction alignment are
enforced without putting occupancy-specific logic into the generic engine.

Outcomes: no classification → `NOT_EVALUATED / OCCUPANCY_NOT_CLASSIFIED` (or `INSUFFICIENT_DATA`
for a rule with no quality gate) · candidate only → `NOT_EVALUATED / OCCUPANCY_NOT_VERIFIED` ·
conflict → `NOT_EVALUATED / OCCUPANCY_CLASSIFICATION_CONFLICT` · edition mismatch →
`OCCUPANCY_EDITION_MISMATCH` · jurisdiction mismatch → `OCCUPANCY_JURISDICTION_MISMATCH`.

## O9. Conflict
Two verified classifications on the **same** subject with different meaning ⇒ `CONFLICT`, no group
published, no silent winner, dependent rules `NOT_EVALUATED`. Different subjects with different
groups is mixed occupancy, not conflict.

## O10. AI boundary
An AI suggestion is `AI_SUGGESTED` + `CANDIDATE`, always. `ai_suggestion` as a verification method
is refused for both classifications and packs. An AI-suggested record carrying VERIFIED status is
structurally invalid. AI cannot name a group that does not exist in a loaded pack. Arabic text
sets neither jurisdiction nor classification — asserted directly.

## O11. Tests, parity, performance (executed)
Occupancy suite **98/98** in Node and in Chromium. JS↔Python **27/27 byte-identical** steps across
suggestion, declaration, verification refusals and successes, conflict, mixed occupancy, audit,
export, pack security and five rule-integration outcomes.

| Subjects | Candidate resolution | Verification | Index lookup | Audit | Rule applicability |
|---|---|---|---|---|---|
| 100 | 17.8 ms | 5.9 ms | 2.6 ms | 1.2 ms | 11.0 ms |
| 500 | 18.5 ms | 16.1 ms | 6.9 ms | 6.4 ms | 12.8 ms |
| 1000 | 25.2 ms | 36.9 ms | 25.1 ms | 21.1 ms | 20.2 ms |

## O12. Developer API
`ACS.classificationPacks()` · `ACS.verifyClassificationPack(id,version,opts)` ·
`ACS.activateClassificationPack(id,version[,enabled])` · `ACS.occupancies()` ·
`ACS.occupancyFor(subjectId)` · `ACS.occupancyCandidates(subjectId[,subjectType])` ·
`ACS.declareOccupancy(subjectId,group,opts)` · `ACS.verifyOccupancy(id,opts)` ·
`ACS.occupancyIssues()` · `ACS.occupancyAudit()` · `ACS.codeContext()`.

## O13. Known limitations
No real classification content and no authoritative mapping loaded · a mapping engine
(facts → classification) is modelled but not implemented; classification is by declaration plus
review · no occupant load, sprinkler status, fire rating or separation anywhere · ZONE is a declared
subject type but the geometry model cannot yet delimit a zone, so zone classification is by
association to spaces only · no authentication, so `declared_by` and `verifier` stay null · packs
are not signed.

---

# PHASE 2 — MODEL REVISION & COMPLIANCE SNAPSHOT INTEGRITY FOUNDATION

**No regulatory content was added.** Regulatory rule count 0, real occupancy classification count 0,
SBC pilot state unchanged. This layer answers only two questions: *which exact model state produced
this result*, and *has anything it depended on changed since*.

## V1. Architecture
`MODEL → CANONICAL SNAPSHOT → MODEL HASH → EVALUATION → RESULT SNAPSHOT → STALENESS CHECK`.
Revision metadata is derived on demand and never written into the model. The hash is the identity
anchor; the timestamp is descriptive only.

## V2. Canonicalization — `acs-model-canonical/1`
**Inclusion is a denylist, not an allowlist.** Every field participates in the hash except the
declared volatile keys. An unrecognised engineering field therefore still invalidates stale
results — the safe direction, because a false staleness costs one re-evaluation while a false
CURRENT costs correctness.

**Order-insensitive (each with a stated reason):** `levels` (each level carries an explicit index,
so array position is not the authority) · `code_context.rulepacks` and
`code_context.classification_packs` (sets of pins) · `buildings` (identified by id, hashed
individually).

**Order-sensitive:** `floors.*.rooms` (position feeds the `sp_<i>` fallback space id) ·
`rooms.*.doors` (`door_<i>` ids appear in relationships, exit `via` references and distance
anchors) · `rooms.*.objects` (`stairs_<i>`/`elevator_<i>` ids appear in vertical transitions) ·
`rooms.*.points` (`exitpoint_<i>`) · `rect` (it is `[x, z, w, d]`) · `polygon` (vertex order is the
outline). Any array not listed keeps its order — conservative, because an unknown array may be
positional.

**Excluded (volatile):** camera, view, viewer, ui, selection, debug, fps, stats, session, toast,
cache, render, renderer, theme, material_preview, orbit, controls, downloaded_at, exported_at,
thumbnail, preview and other runtime keys — 24 in total. A UI-only change leaves every result
CURRENT.

**Derived, therefore not hashed:** relationships, navigation graph, egress results, distance
measurements, coverage/report objects. They are functions of the geometry that *is* hashed, so a
geometry edit that changes the relationship graph changes the hash anyway — tested directly.

## V3. Numbers
No rounding before hashing: `24.90548817090728` and `24.905` hash differently, by test. Integral
floats normalise so `6.0` and `6` agree.

A real divergence was found by a deliberately hostile fixture and fixed at the source: Python
renders `5e-07` and `1e-05` where JavaScript renders `5e-7` and `0.00001`. Numbers are now emitted
as a canonical token `#n:<normalised scientific>` computed identically in both languages, so neither
language's default float formatting can leak into a hash. The prefix prevents a number colliding
with a string that looks like one.

## V4. ID stability (audited, not assumed)
`ensure_element_ids` is fully deterministic — ids derive from building id, template name and either
the room's own id or its position; there is no counter, clock or randomness. It does mutate,
so canonicalization applies it **to a deep copy**: a model hashes identically before and after
`ensure_element_ids`, and the input is never touched. Renaming a room id does change the hash,
correctly, because the id defines references.

## V5. Scope
`model_hash(model, scope)` supports `building` and `project`; `building_hashes(project)` returns one
hash per building. Changing building B leaves building A's hash byte-identical, so a
building-A-scoped result stays CURRENT while the project-scoped result goes stale. Reordering the
building list does not change the project hash.

## V6. Result snapshot
`model_hash · model_scope · building_id · canonicalization_version · hash_algorithm · rule_hash ·
rule_id · rule_revision · rulepack_id · rulepack_version · source_document_hashes ·
occupancy_refs · occupancy_hash · code_context_hash · engine_version · evaluated_at`, alongside the
untouched result. Additive and backward-compatible.

## V7. Integrity statuses
`CURRENT · CURRENT_UNDER_SAME_HASH · STALE_MODEL_CHANGED · STALE_RULE_CHANGED ·
STALE_RULEPACK_CHANGED · STALE_OCCUPANCY_CHANGED · STALE_CODE_CONTEXT_CHANGED ·
STALE_SOURCE_CHANGED · UNVERIFIABLE`, with a declared precedence order. Integrity is separate from
the rule result: a stored `PASS` with `STALE_MODEL_CHANGED` exports with
`presented_as_current: false`.

`CURRENT_UNDER_SAME_HASH` means the model matched but some anchor was not supplied for checking, and
the result names which. `UNVERIFIABLE` means the canonicalization version or hash algorithm differs
— hashes from incompatible canonicalization are never compared.

## V8. No silent re-evaluation
`check_result_integrity` only reports; `apply_integrity` only labels. Neither recomputes a result.
Multiple snapshots of different model states coexist, and `stale_results` lists the outdated ones
with their reasons while their stored values remain exactly as evaluated.

## V9. Tests, parity, performance (executed)
Revision suite **99/99** in Node and in Chromium. JS↔Python **16/16 byte-identical** canonical
snapshots *and* hashes across Arabic text, `«»`, a surrogate-pair glyph, empty strings, null,
booleans, negative zero, `5e-7`, `1e21`, `24.90548817090728`, nested arrays/objects, four building
fixtures, key reordering, level reordering, room reordering, a two-building project and its
reordering, plus code-context and occupancy hashes and a revision diff.

| Model | Canonicalize | SHA-256 | End-to-end |
|---|---|---|---|
| villa (11 spaces) | 1.0 ms | 5.3 ms | 6.3 ms |
| 101 spaces | 1.5 ms | 16.3 ms | 8.1 ms |
| 501 spaces | 8.1 ms | 18.0 ms | 12.1 ms |
| 1001 spaces | 12.0 ms | 30.2 ms | 25.4 ms |
| 5-building project (1005 spaces) | — | — | project 56.3 ms · per-building 20.9 ms |

## V10. Developer API
`ACS.modelHash(scope)` · `ACS.modelRevision(scope,bid,at)` · `ACS.canonicalModel(scope)` ·
`ACS.snapshotResult(ruleId,subjectId,opt)` · `ACS.resultIntegrity(snapshot)` · `ACS.snapshots()` ·
`ACS.staleResults()` · `ACS.revisionDiff(otherModel,scope)`. Snapshots accumulate in session
history; nothing is overwritten.

## V11. Known limitations
Snapshot history is in-memory and per session — no persistence layer, by design for this phase ·
no signing of snapshots, so an exported snapshot proves provenance only to a party that trusts the
exporter · `revision_diff` is factual only and draws no engineering conclusion · derived analyses
(paths, egress, distance) are snapshotted only when explicitly asked, never automatically · the
canonical form is deliberately conservative, so a harmless model reformat that reorders rooms will
report staleness.

---

# W. ARCHITECTURAL GEOMETRY & BUILDING ENVELOPE FOUNDATION

**Geometric fidelity only. No structural design, no MEP, no fire engineering, no accessibility
evaluation, no regulatory compliance, no auto-fix.** Every element produced here is architectural.
Nothing compiled by this layer is load-bearing, rated, or compliant, and nothing in it may be read
as such.

## W1. What was added
`acs_arch.json` — the canonical specification (schema, compiler version, 12 element types, 5
provenance values, 3 exposure values, 3 evidence states, 3 level kinds, 3 host states, 19 geometry
issue codes, render-fallback defaults, forbidden claims, id patterns).
`acs_arch.py` — the deterministic compiler and validator.
The browser mirror inside `public/index.html`, which embeds `acs_arch.json` **verbatim** and is
proved byte-identical to the file on disk by a drift test in both Node and Chromium.

The semantic model — spaces, doors, windows, levels, objects — remains the single source of truth.
Physical elements are *compiled* from it; they are never stored back into it and never edit it.

## W2. The element vocabulary is one vocabulary
`WALL · DOOR · WINDOW · OPENING · FLOOR_SLAB · FLOOR_OPENING · CEILING · ROOF · STAIR ·
ELEVATOR_SHAFT · CORE · ENVELOPE`. A hotel wall and a villa wall come out of the same function with
the same fields. Nothing in the compiler branches on building type, program, or room name. The five
fixtures (villa, hotel, clinic, office, warehouse) each compile through the identical code path, and
the test suite asserts the shared vocabulary on all of them.

## W3. A shared wall is defined once
Every space edge is projected onto its axis line and every boundary is split at *every* breakpoint
contributed by any space on that line. A segment bounded by two spaces becomes one wall that both
spaces reference — not two coincident walls. A partially shared boundary breaks into the shared part
and the unshared remainder, each a separate segment.

Wall numbering follows the canonical sort of the wall's own geometry (`axis, fixed, u0, u1`), not
room iteration order. Reversing the room array produces byte-identical wall ids and geometry; this
is asserted directly.

## W4. Exterior is inferred, and says so
Exposure is one of `interior · exterior · unresolved`, each with an evidence status
(`confirmed · inferred · unresolved`) and an explicit basis string:

- bounded by two spaces → `interior / confirmed`
- probe on the far side lands inside another space → `interior / inferred`
- probe lands inside the declared rectangle of a space whose outline is **unsupported** →
  `unresolved` (we refuse to treat a rectangle we know is wrong as a footprint)
- probe lands inside the level footprint but in no space → `unresolved`
  (`opposite_side_is_void_inside_the_footprint`) — **an internal courtyard is never called exterior**
- probe lands outside the level footprint → `exterior / inferred`
- the model declares the space exterior → `exterior / confirmed`, **but only for walls bounded by a
  single space**: a room-level flag never overrides a wall that physically separates two spaces.

The villa compiles to 18 exterior, 12 shared and 8 unresolved walls. The courtyard fixture leaves
exactly its four courtyard-facing walls unresolved rather than claiming a facade.

## W5. A render fallback is never an engineering value
Every dimensional property is `{value, render_fallback, source}`. When the model does not state a
value, `value` stays `null`, the drawing convenience is exposed separately as `render_fallback`, and
`source` is `unknown`. A door's `clear_width_m` is never derived from its nominal width. An
unspecified swing is reported `not_specified`, not assumed. `defaults_note` in the spec states in
writing that the defaults are render fallbacks, and the security scan asserts that sentence exists.

## W6. Openings are hosted, not floating
Each door and window is matched to the wall segment that carries it: `resolved` when it fits inside
one segment, `partial` with a note when it spans several or hangs off the end, `unresolved` when no
segment carries it. The host wall lists the opening back. Validation distinguishes
`OPENING_WIDER_THAN_HOST` (genuinely wider than the segment) from `OPENING_OUTSIDE_HOST` (fits, but
positioned off the end) — the two are different defects and are not merged.

## W7. Slabs, voids and vertical cores
A vertical core is a stair or elevator object grouped by stable position across levels. Every level
a core passes through — above the lowest level it serves, up to the highest — receives a
`FLOOR_OPENING` derived from the core footprint. A core serving more than one level without a void
is reported (`VOID_MISSING_FOR_CORE`); a core whose position the model never stated is reported
(`CORE_POSITION_NOT_STATED`) rather than silently centred.

**The renderer consumes these voids.** `slabStrips()` splits the floor plate into axis-aligned solid
strips around every void — no CSG, no approximation. A stair no longer passes through an uncut
slab. The rendered strip area equals plate area minus void area exactly, and no strip overlaps a
void; both are asserted numerically against the compiler output. A level with no void still renders
exactly one slab box, as in Phase 1. **No structural framing around the opening is implied or
drawn.** The plate extent itself remains the Phase 1 site-sized convention — the compiler's own slab
outline (the bounding box of the spaces, flagged as an approximation when the spaces do not tile the
footprint) is exposed through the developer API and is deliberately *not* used as the render extent,
so no Phase 1 visual behaviour changed beyond the cut.

## W8. Element identity
A floor template used on two levels describes **two** physical rooms, not one. Space instances are
therefore identified as `<space_id>@<level_index>` — the same identity the navigation graph already
uses — while `space_id` keeps the semantic id the relationship, navigation, egress, distance and
rule layers join on. Openings carry the same pair: `id` = `<space_id>.door_<i>@<level>`,
`opening_ref` = `<space_id>.door_<i>` (the `via` reference the relationship layer emits). Element ids
are unique inside a building and namespaced by building id; this is asserted across every fixture.

## W9. Integration with the existing layers — additive only
**Relationships.** `DOOR_CONNECTS` rises from `inferred` to `confirmed` only when the compiler
proves the door is hosted (`resolved`) on a wall shared by exactly two spaces, and those two spaces
are exactly the pair the edge links. The upgraded edge records `meta.wall_id` and
`meta.evidence_basis`. Absence of proof changes nothing: the existing geometric inference stands,
`unresolved` edges are never upgraded, and no edge is created or removed. Villa: 11 door edges
before and after — 9 confirmed, 2 unresolved.

**Distance.** `door_anchor()` now prefers the compiled opening geometry when a compiled model is
available, falling back to the rectangle derivation otherwise. The guard is unchanged and comes
first: an unstated edge or offset still yields **no anchor at all**, compiler or not. For
axis-aligned rectangles the two derivations are mathematically identical; the suite proves it by
comparing both anchors for every door in every fixture rather than asserting it.

**Revision.** Compiling architecture does not touch the model, so the model hash is unchanged by
compilation; a real geometry change changes both the hash and the compiled walls.

## W10. Validation is geometric, never regulatory
19 issue codes covering wall degeneracy and duplication, opening hosting and fit, window sill and
head against wall height, space overlap, space containment (a project-layout envelope containing
sub-zones is `SPACE_CONTAINED`, not a bogus `SPACE_OVERLAP`), unsupported shapes, level elevation
consistency, and core/void coherence. None of them is a code check. A non-rectangular outline is
reported and **never approximated into a rectangle**: no walls are fabricated for it, and it is
listed under `approximations` with a reason.

## W11. Tests, parity, performance (executed)
Architecture suite **147/147** and renderer suite **22/22**, each passing in Node and in Chromium.
Full regression: 16 suites in Chromium and 14 in Node, **1051 assertions, 0 failures**, plus 60
backend/config security checks and 9 D-1 checks.

JS↔Python parity: **23/23 byte-identical** compiled models — the five fixtures plus shared-wall,
partially-shared, unsupported-shape, overlap/containment, hostile-opening, bad-level, multi-core,
Arabic and astral-plane names, declared-exterior, reversed room order, courtyard, empty and
fully-unstated models, and three transformed/renamed-building variants. Anchors, world transforms,
door evidence, summaries and validation output are all included in the comparison.

| Spaces (×2 levels) | Instances | Walls | Openings | JS compile | JS validate | Py compile | Py validate |
|---|---|---|---|---|---|---|---|
| 100 | 200 | 440 | 268 | 12 ms | 1 ms | 23 ms | 7 ms |
| 500 | 1000 | 2090 | 1334 | 84 ms | 9 ms | 373 ms | 174 ms |
| 1000 | 2000 | 4128 | 2668 | 107 ms | 27 ms | 1423 ms | 690 ms |

Element counts are identical in both languages at every scale.

## W12. Developer API
`ACS.architecture(bid,pos,rot)` · `ACS.archElements(bid)` · `ACS.walls(bid)` · `ACS.openings(bid)` ·
`ACS.envelope(bid)` · `ACS.geometryIssues(bid)` · `ACS.archApproximations(bid)` ·
`ACS.elementById(id,bid)` · `ACS.sharedWall(a,b,bid)` · `ACS.doorEvidence(openingRef,bid)` ·
`ACS.archSummary(bid)`. All read-only and derived on demand; nothing is cached into the model.

## W13. Known limitations — stated, not hidden
Only axis-aligned rectangular space outlines are compiled; polygons are reported, not approximated ·
walls are single-line segments with a thickness property, not solids with joins or mitres ·
the slab outline is the bounding box of the spaces and is flagged as an approximation whenever the
spaces do not tile the level footprint · the renderer's plate extent is still the site rectangle
(Phase 1 convention), not the compiler's slab outline · curved and sloped geometry, roof pitches,
parapets, mullions and stair flights/landings are out of scope · a courtyard is left `unresolved`
rather than resolved, by design · **full WebGL rendering was not verified in this environment**:
`public/vendor/` is empty because the sandbox has no outbound network, so the 3D scene was verified
by running the repository's own `compile()` against a recording stub in both Node and Chromium —
pixel output remains **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

---

# X. STRUCTURAL MODEL FOUNDATION

**Structural representation only. No structural design, no load calculation (dead, live, wind,
seismic), no member sizing, no reinforcement design, no foundation design, no capacity, deflection,
shear, moment or punching-shear calculation, no soil assessment, no structural code compliance, no
auto-fix.** Nothing this layer produces may be read as evidence that any member is adequate, safe or
compliant.

## X1. Architecture
The structural model lives **alongside** the architectural model and never replaces it:

    SEMANTIC BUILDING MODEL
      ├── ARCHITECTURAL MODEL   walls · openings · spaces · slabs · cores · envelope
      └── STRUCTURAL MODEL      grids · nodes · columns · beams · slabs · walls ·
                               foundations · cores · materials · relationships

Input lives at `building.structural` and is purely additive — a Phase 1 model with no `structural`
key compiles to `status: NOT_DEFINED` with zero elements and zero issues, and every existing
consumer keeps working untouched. Levels are read from the **architectural level table**, so a
structural member can never float on renderer-only coordinates.

## X2. Files changed
New: `acs_struct.json` (canonical spec), `acs_struct.py` (compiler + validator), and the browser
mirror inside `public/index.html` which embeds `acs_struct.json` verbatim and is proved
byte-identical by a drift test in Node and in Chromium. Changed: `acs_revision.json` (structural
member order declared order-sensitive; `layer_visibility` / `visible_layers` declared volatile),
`public/index.html` (mirror, renderer debug layer, JSON export, developer API, property card),
`Dockerfile` (ships the two new files), `PHASE2-FOUNDATION.md`.

## X3. Schema and status
Ten element types (`GRID_SYSTEM · GRID_LINE · STRUCTURAL_NODE · COLUMN · BEAM · STRUCTURAL_SLAB ·
STRUCTURAL_WALL · FOUNDATION · STRUCTURAL_CORE · MATERIAL`). Model status is one of
`NOT_DEFINED · PARTIAL · REPRESENTED · IMPORTED · VERIFIED_DATA`; `DESIGNED`, `SAFE` and `COMPLIANT`
are deliberately absent because nothing in this platform could justify them. An undeclared status is
*derived* from element provenance, and the derivation basis is reported next to it.

## X4. Provenance
`user · imported · ai_inference · system_suggested · system_default · manual_verified ·
test_fixture · display_fallback · unknown`. Only `user`, `imported` and `manual_verified` count as
verified sources — `ai_inference` and `system_suggested` are proposals and are separated from
verified data by construction. `rule` is intentionally **not** a provenance value here, because no
verified structural rule evidence exists anywhere in the platform.

## X5. Grid
A building may carry several grid systems. Each has its own origin and rotation, and each line
carries an axis (`X`/`Z`), a label, a position and `position_stated`. `grid_to_world()` composes the
grid rotation with the building transform, so a rotated grid inside a rotated building is expressed
without ever assuming project world axes. Unresolved grid references are reported, not dropped.

`suggest_structural_grid(spacing_x, spacing_z)` is the **only** proposal helper. It returns a
`SUGGESTION` object with `applied:false`, `persisted:false` and `source: system_suggested`, it
refuses with `NO_SPACING_SUPPLIED` when no spacing is given and `NO_FOOTPRINT` when there is nothing
to lay a grid over, and it writes nothing into the model. **No automatic structural-system generator
ships in this phase.**

## X6. Columns, beams, slabs, walls, cores, foundations
A column records the levels it spans, the elevations those levels give it, its measured height and
the basis of that height. A beam resolves each endpoint to a declared structural node, or to a
stated point (flagged `BEAM_FLOATING`), or not at all (`INVALID_NODE_REF` +
`BEAM_ENDPOINT_UNRESOLVED`). **Beams are never auto-connected between neighbouring columns** — the
villa fixture has 9 columns and exactly the 7 beams it declares.

A structural slab is a distinct element from the architectural floor slab and exists only where the
model declares one. An architectural wall never becomes a structural wall, and an architectural
stair or elevator core never becomes a lateral core: `structural_role` stays `unknown` unless the
model states it. Foundation types come from a closed list and are never chosen from the building
type — the villa fixture has isolated footings and the hotel fixture a raft **because the fixtures
say so**. No soil property and no bearing capacity is produced anywhere; `soil` is always `null`.

## X7. Materials
`concrete · steel · timber · masonry · composite · other · unknown`. A material label carries no
strength, grade, density, modulus, fire rating or capacity: concrete does not imply an f′c and steel
does not imply an Fy. Each optional property is a `{value, source}` pair that stays `null/unknown`
unless supplied.

## X8. Display fallbacks
Every drawable dimension is `{value, render_fallback, source, render_source}`. When a section,
thickness or footprint is not supplied the semantic field stays `null`, the renderer reads the
fallback instead, and the geometry is tagged `display_fallback` on the mesh, in the render item and
in the property card. A fallback is never written back into the model, never exported as engineering
metadata, and never reaches the rule inputs — the warehouse fixture draws columns from fallbacks
while `structural.column.section_width` remains `null`.

## X9. Relationships — connectivity, not load path
`COLUMN_SUPPORTS · BEAM_CONNECTS · SLAB_SUPPORTED_BY · WALL_SUPPORTED_BY · FOUNDATION_SUPPORTS ·
CORE_SPANS_LEVELS · COLUMN_STACKS · MEMBER_IN_SPACE`, each with a status and a basis, and each
carrying the note *"geometric connectivity only — this is not a load path"*. `COLUMN_SUPPORTS` is
emitted when a beam endpoint coincides with a column axis and carries an explicit disclaimer;
`FOUNDATION_SUPPORTS` states that no bearing check was performed; `SLAB_SUPPORTED_BY` and
`WALL_SUPPORTED_BY` are emitted **only** from declared `supported_by` lists, never inferred.

## X10. Stacking, offset and alignment break
Column continuity is measured geometrically: within 0.01 m → `aligned`, within 1.00 m → `offset`
(`COLUMN_OFFSET`, WARNING, *"no transfer element is designed or assumed"*), beyond that →
`unresolved` (`STRUCTURAL_ALIGNMENT_BREAK`, WARNING, *"reported as a factual condition only"*).
**No transfer beam is designed and nothing is auto-fixed** — the hotel fixture keeps exactly its 8
declared beams after both conditions are reported.

## X11. Structural ↔ architectural interference
Obvious geometric conflicts only, never full BIM clash detection: `COLUMN_BLOCKS_OPENING`,
`COLUMN_IN_FLOOR_OPENING`, `COLUMN_IN_ELEVATOR_CORE`, `BEAM_CROSSES_OPENING` (INFO, and it says head
clearance is *not* evaluated), `FOUNDATION_OUTSIDE_SITE`, `COLUMN_OUTSIDE_BUILDING`. Each clash
records the basis it was tested on — `column_section_footprint` when the section is known,
`column_axis_point` when it is not, so an unknown section never fakes a footprint. A column inside a
room is a `MEMBER_IN_SPACE` relationship carrying *"spatial location only — acceptability is not
judged here"*, never a prohibition.

## X12. Integrity validation
29 issue codes with `INFO / WARNING / ERROR` severities; `UNSAFE`, `DANGEROUS` and `CODE VIOLATION`
are deliberately absent. Covered: duplicate ids, unsupported collections, invalid level / node /
material / grid references, cross-building ids, NaN coordinates, negative dimensions, zero-length
members, zero-height and height-mismatched columns, floating and unresolved beam endpoints, missing
and unresolvable foundation targets, unresolved slab / wall / core levels, unknown sections and
materials, plus the alignment and interference conditions above. A deliberately broken fixture
triggers **every** one of the 29 codes. None of them is a code check.

## X13. Fixtures (synthetic only)
`villa_struct` (grid + 9 columns + 7 beams + slab + 9 footings), `hotel_struct` (three-level stacks,
a declared offset, a declared alignment break, a lateral core, a shear wall), `warehouse_struct`
(sections and material deliberately **unknown** — proving no steel default), `mixed_struct` (retail
+ office + residential over one unchanged structural system), plus `broken_struct`, `clash_struct`,
`lift_clash_struct` and `no_struct`. Every element is `synthetic: true`, `regulatory: false`,
`source: test_fixture`. **None of this is a real structural design.**

## X14. Renderer, GLB and JSON
Structural meshes are named `STRUCT|COLUMN|<id>`, `STRUCT|BEAM|<id>`, `STRUCT|SLAB|<id>`,
`STRUCT|WALL|<id>`, `STRUCT|CORE|<id>`, `STRUCT|FOUNDATION|<id>`. They live in their own `STRUCT`
layer, **hidden by default**, and never enter the floor filter. Colour distinguishes element *kind*
only — never safety or status — and the property card exposes id, type, source, levels, material,
section (or "not stated") and stack state, plus an explicit line when the drawn geometry is a
display fallback. GLB export already runs with `onlyVisible:false`, so represented structural
elements export; fallback dimensions carry their `display_fallback` tag rather than posing as
engineering metadata. JSON export adds `structural` (verbatim) and `structural_compiled` additively
and removes no architectural representation.

## X15. Revision hashing
Because `structural` lives inside the building, it is hashed by the existing canonicalisation.
Verified by test: moving a column, removing a beam, changing a section, adding a foundation and
changing a material property each change the hash; toggling `layer_visibility` and moving the camera
do not; compiling the structure does not.

## X16. No architectural / navigation / egress / distance regression
Asserted directly, not assumed: adding a structural block leaves the compiled architectural walls,
openings, voids and envelope byte-identical; the relationship graph, the navigation path, the egress
result and the measured walking distance are all byte-identical with and without it. **Structural
members are not navigation obstacles in this phase** — the compiled model states this in
`meta.navigation_impact`, and distances are deliberately *not* rerouted around columns.

## X17. Tests, parity, performance (executed)
Structural suite **177/177** and renderer suite **32/32**, each in Node and in Chromium. Full
regression: 17 suites in Chromium and 15 in Node, **1220 assertions, 0 failures**, plus 74
backend/config security checks and 9 D-1 checks. JS↔Python parity **13/13 byte-identical** compiled
structural models — the four programme fixtures plus the broken, clash, elevator-clash, empty and
three transformed/renamed-building variants, comparing the whole model, the summary, the render
items, the rule inputs, the world-space grid lines and the validation output.

| Target members | Columns | Beams | Relationships | Render items | JS normalise | JS validate | Py normalise | Py validate |
|---|---|---|---|---|---|---|---|---|
| 100 | 25 | 20 | 186 | 70 | 5 ms | 0 ms | 2 ms | 0 ms |
| 500 | 125 | 114 | 1036 | 364 | 9 ms | 0 ms | 41 ms | 1 ms |
| 1000 | 250 | 234 | 2123 | 734 | 19 ms | 1 ms | 130 ms | 2 ms |
| 5000 | 1250 | 1215 | 10969 | 3715 | 223 ms | 3 ms | 3278 ms | 11 ms |

Element, relationship and issue counts are identical in both languages at every scale.

## X18. Developer API
`ACS.structuralModel(bid,pos,rot)` · `ACS.structuralElements(bid)` · `ACS.structuralGrid(bid)` ·
`ACS.structuralIssues(bid)` · `ACS.structuralElement(id,bid)` · `ACS.structuralSummary(bid)` ·
`ACS.structuralRenderItems(bid)` · `ACS.structuralRuleInputs(bid)` ·
`ACS.suggestStructuralGrid(sx,sz,bid)` · `ACS.structuralLayerVisible(on)`. All read-only and derived
on demand; the visibility toggle is pure view state and is excluded from the revision hash.

## X19. Future rule contract
`structural.column.section_shape / section_width / section_depth / section_diameter / height_m`,
`structural.beam.section_width / section_depth / length_m`, `structural.foundation.type`,
`structural.member.material`, `structural.member.source`. These are **inputs only**: no regulatory
structural rule exists, missing data stays missing rather than defaulting, and the rule input map
contains no limit, threshold or verdict.

## X20. Known limitations — stated, not hidden
No analysis model, no load path, no member forces — geometric connectivity only · columns are
vertical prisms between two level elevations; inclined, tapered and curved members are out of scope ·
beams are straight single-span segments with no haunches, cambers or joints · structural slabs and
cores are rectangular outlines · pile groups, pile caps and rafts are represented as single elements
with no internal layout · interference detection covers the obvious cases listed above and is not
BIM clash detection · structural members do not affect navigation, egress or walking distance in
this phase, by design · the 5000-member Python normalisation takes ~3.3 s, dominated by the
relationship pass, and was left unoptimised deliberately · **full WebGL rendering was not verified
in this environment**: `public/vendor/` is empty because the sandbox has no outbound network, so the
structural debug layer was verified by running the repository's own `compile()` against a recording
stub in Node and in Chromium — pixel output remains **NOT VERIFIED — EXTERNAL ENVIRONMENT
REQUIRED**, as is the live Render backend (`fastapi` is absent here; the API module compile-checks
clean).
