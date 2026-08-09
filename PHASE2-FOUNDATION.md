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

---

# Y. MEP SYSTEMS MODEL FOUNDATION

**MEP representation only. No MEP design and no calculation of any kind** — no electrical load,
voltage drop, short-circuit, cable, breaker or transformer sizing; no lighting level; no cooling,
heating or airflow calculation, no duct sizing, static pressure or psychrometrics; no fixture units,
water demand, pipe or drainage sizing, pump head; no sprinkler hydraulics, fire-water demand or
fire-alarm design; **no MEP code compliance and no SBC / NFPA / NEC / IEC / ASHRAE / SMACNA / IPC
values**; no auto-fix. Fire-protection content here is **data representation only — there is no
Fire / Life-Safety engine**.

## Y1. Architecture
    SEMANTIC BUILDING MODEL
      ├── ARCHITECTURAL MODEL
      ├── STRUCTURAL MODEL
      └── MEP MODEL   systems · nodes · segments · equipment · terminals ·
                      risers · penetrations · relationships · issues

Input lives at `building.mep`, purely additive: a model with no `mep` key compiles to
`NOT_DEFINED`, zero elements, zero issues, and every existing consumer keeps working. Levels come
from the architectural level table and spaces from the architectural space table, so an MEP element
cannot float on renderer-only coordinates. MEP never edits the architectural or structural model.

## Y2. Files changed
New: `acs_mep.json` (spec), `acs_mep.py` (compiler + validator), browser mirror in
`public/index.html` (drift-tested byte-identical). Changed: `public/index.html` (mirror, seven
discipline debug layers, property card, JSON export, developer API), `Dockerfile`,
`PHASE2-FOUNDATION.md`.

## Y3. Schema, status and provenance
Seven element types (`MEP_SYSTEM · MEP_NODE · MEP_SEGMENT · MEP_EQUIPMENT · MEP_TERMINAL ·
MEP_RISER · MEP_PENETRATION`). Status is `NOT_DEFINED · PARTIAL · REPRESENTED · IMPORTED ·
VERIFIED_DATA` — `DESIGNED`, `COMPLIANT`, `ADEQUATE`, `BALANCED` and `CALCULATED` are deliberately
absent. Provenance is `user · imported · ai_inference · system_suggested · system_default ·
manual_verified · test_fixture · display_fallback · phase1_adapter · unknown`; only the first,
second and sixth count as verified. `rule` and `code_required` are **not** provenance values at all.

## Y4. System vocabulary
25 system types across 8 disciplines (Electrical, Lighting, ICT, Plumbing, Drainage, HVAC, Fire,
Other) with 10 media. **No system is ever instantiated automatically**: the villa fixture has no
sprinkler system, the hotel fixture no emergency power and the warehouse fixture no fire-water
infrastructure, because none of them declared one — asserted directly. A medium is a factual label
and attaches no pressure, temperature, flow or velocity assumption.

## Y5. Nodes, segments and routing
Nodes carry a kind, a position, a level and a space, and no capacity. Segments carry a kind
(`duct · pipe · conduit · cable_tray · cable · busway · other`), endpoints resolved to nodes, an
optional supplied polyline in real X/Y/Z metres, and a routing status of
`UNROUTED · ROUTED · PARTIAL · IMPORTED · UNRESOLVED`. `OPTIMIZED` is absent because no routing
optimisation exists. **A segment with endpoints but no supplied geometry stays `UNROUTED` and no
path is fabricated** — the relationship layer says so, the issue list says so (INFO), and the
renderer draws nothing for it.

## Y6. Equipment, terminals, ports
22 equipment types and 31 terminal types cover electrical, lighting, HVAC, plumbing fixtures, air
devices, low-current/ICT and fire devices in one vocabulary. **No rating, voltage, current, breaking
capacity, CFM, L/s, throw or neck size is ever produced** — properties exist only where the model
supplies them, each with its own provenance. Connection ports are recorded only where declared, and
an unrecognised port type is reported rather than accepted.

## Y7. The Phase 1 adapter preserves provenance
Existing Phase 1 points (light, outlet, ac, smoke, camera, …) are **adapted**, not duplicated: each
adapted terminal names its `origin_ref` point and carries `original_source` through unchanged. A
system-generated smoke detector stays `system_default`; a user-supplied point stays `user`.
**No adapter can raise a point to a code requirement** — `code_required` is not a value in the
vocabulary and does not appear anywhere in the layer's source, which the security scan asserts. The
adapter can be switched off and changes nothing else.

## Y8. Risers and shaft association
Five riser kinds with a stable XY position, served levels and system references. **An architectural
shaft or core is not an MEP riser**: association requires an explicit `arch_core_id` plus a recorded
`arch_core_link_source`. A riser sitting outside the core it names is reported.

## Y9. Relationships — topology, never adequacy
`SEGMENT_CONNECTS · EQUIPMENT_CONNECTED_TO · TERMINAL_CONNECTED_TO · RISER_CONNECTS_LEVELS ·
RISER_IN_SHAFT · SYSTEM_SERVES_SPACE · SYSTEM_HAS_TERMINAL_IN · PANEL_FEEDS · CIRCUIT_FEEDS ·
TERMINAL_ON_CIRCUIT · PENETRATION_THROUGH`. Every edge carries *"model topology and factual location
only — no service adequacy is claimed"*. A diffuser in Room A means **Room A has a represented
terminal**, never that Room A receives adequate airflow. **Circuits are never grouped automatically**
— `PANEL_FEEDS` / `CIRCUIT_FEEDS` / `TERMINAL_ON_CIRCUIT` appear only when the model declares a
circuit, which is asserted both ways.

## Y10. Interference and penetrations
Architectural: segment crossing a wall or slab without a represented penetration, equipment or
terminal outside its assigned space, riser outside its shaft, MEP element inside a stair void, route
outside the building footprint. Structural: segment crossing a beam, a column (recording whether the
test used a real section footprint or axis proximity) or a structural slab. **Everything is reported
and nothing is corrected** — a beam clash explicitly states the member is not cut and the route is
not redesigned, and tests confirm the compiled architectural and structural models are byte-identical
before and after MEP compilation. A declared penetration suppresses the crossing report at that host
and **implies nothing about fire stopping, sleeves or reinforcement**.

## Y11. Display fallbacks
Pipe diameters, duct sizes, equipment envelopes, terminal sizes and riser footprints all follow the
established pattern: unsupplied ⇒ semantic field `null`, renderer reads a separately tagged
`display_fallback`, and the fallback never reaches the model, the export metadata or the rule
inputs. The warehouse fixture draws its busway from fallbacks while `mep.segment.size.diameter_m`
stays `null`.

## Y12. Validation
35 issue codes with `INFO / WARNING / ERROR`; `UNSAFE`, `CODE VIOLATION` and `FIRE VIOLATION` are
absent. Covered: duplicate ids, unsupported collections, unknown system / medium / equipment /
terminal / segment kinds, invalid system / node / equipment / level / space / port references,
cross-building ids, NaN coordinates, negative dimensions, zero-length and unrouted segments,
unresolved endpoints, orphan terminals and nodes, unknown sizes, unresolved riser levels and
penetration hosts, plus the interference conditions above. A deliberately broken fixture triggers
**every** one of the 35.

## Y13. Fixtures (synthetic only)
`villa_mep` (lighting, sockets, cold water, sanitary, one split unit, one deliberately unrouted
duct), `hotel_mep` (electrical / plumbing / drainage / duct risers across three levels with a
declared slab penetration), `clinic_mep` (power, HVAC, plumbing, data, plus an explicitly labelled
*synthetic* medical-gas system implying **no healthcare compliance**), `warehouse_mep` (sizes
deliberately unknown, no industrial assumption in the core), `mixed_mep` (three programmes, one
unchanged MEP model), plus `clash_mep`, `broken_mep`, `phase1_points` and `no_mep`. Every element is
`synthetic: true`, `regulatory: false`, `source: test_fixture`.

## Y14. Renderer, GLB and JSON
Meshes are named `MEP|<DISCIPLINE>|<id>|<part>` and registered as seven separate debug layers
(`MEP_ELECTRICAL`, `MEP_LIGHTING`, `MEP_ICT`, `MEP_PLUMBING`, `MEP_DRAINAGE`, `MEP_HVAC`,
`MEP_FIRE`, plus `MEP_RISER` / `MEP_OTHER`), **hidden by default** and excluded from the floor
filter. The fire layer's own label says *data only, no safety engine*. Colour marks discipline only
— never safe, failed or compliant — and the property card exposes id, kind, system, medium, source,
level, space, routing status, size (or "not stated"), adapter provenance and an explicit line when
the drawn geometry is a display fallback. JSON export adds `mep` (verbatim) and `mep_compiled`
additively.

## Y15. Revision hashing
Verified by test: moving equipment, changing a pipe route, adding duct route geometry, removing a
terminal, changing a system property and adding a riser each change the building hash; toggling
`layer_visibility` and moving the camera do not; compiling the MEP model does not.

## Y16. No architectural / structural / navigation / egress / distance regression
Asserted directly: the compiled architectural model and the compiled structural model are
byte-identical with and without an MEP block, and so are the relationship graph, the navigation
path, the egress result and the measured walking distance. **MEP elements are not navigation
obstacles in this phase** — stated in the spec, repeated in `meta.navigation_impact`, and no route
is silently rerouted around a duct.

## Y17. Tests, parity, performance (executed)
MEP suite **183/183** and renderer suite **42/42**, each in Node and in Chromium. Full regression:
18 suites in Chromium and 16 in Node, **1413 assertions, 0 failures**, plus 91 backend/config
security checks and 9 D-1 checks. JS↔Python parity **13/13 byte-identical** compiled MEP models —
the five programme fixtures plus clash, broken, Phase 1 adapter, empty and three
transformed/renamed-building variants, comparing the whole model, the summary, the render items, the
rule inputs, the interference list and the validation output.

| Target elements | Segments | Terminals | Relationships | Render items | JS normalise | JS validate | Py normalise | Py validate |
|---|---|---|---|---|---|---|---|---|
| 100 | 16 | 40 | 112 | 57 | 2 ms | 0 ms | 1 ms | 0 ms |
| 500 | 90 | 200 | 580 | 295 | 17 ms | 0 ms | 19 ms | 0 ms |
| 1000 | 186 | 400 | 1172 | 596 | 11 ms | 1 ms | 68 ms | 1 ms |
| 5000 | 968 | 2000 | 5936 | 3018 | 85 ms | 4 ms | 1607 ms | 7 ms |

Element, relationship, interference and issue counts are identical in both languages at every scale.
Complexity: normalisation is linear in element count; relationship building is linear; interference
is O(segments × (walls + beams + columns)) per level, which dominates at scale and was deliberately
left unoptimised.

## Y18. Developer API
`ACS.mepModel(bid,pos,rot)` · `ACS.mepSystems(bid)` · `ACS.mepElements(bid)` ·
`ACS.mepSystem(id,bid)` · `ACS.mepElement(id,bid)` · `ACS.mepIssues(bid)` ·
`ACS.mepInterferences(bid)` · `ACS.mepSummary(bid)` · `ACS.mepRenderItems(bid)` ·
`ACS.mepRuleInputs(bid)` · `ACS.mepLayerVisible(discipline,on)`. All read-only and derived on
demand; the visibility toggle is pure view state and is excluded from the revision hash.

## Y19. Future rule contract
`mep.system.exists.<TYPE>`, `mep.terminal.count`, `mep.equipment.count`, `mep.equipment.type`,
`mep.segment.kind`, `mep.segment.size.diameter_m / width_m / height_m`,
`mep.segment.routing_status`, `mep.system.serves_space`, `mep.member.source`. **Inputs only**: no
regulatory MEP rule exists, missing data stays missing rather than defaulting, display fallbacks are
excluded by construction, and the map contains no limit, threshold or verdict.

## Y20. Known limitations — stated, not hidden
No network solver, no flow direction, no connectivity closure check — topology as supplied only ·
segments are polylines with a nominal rectangular or circular section, with no fittings, bends,
reducers, valves or dampers · risers are single prisms with no internal layout · interference
detection covers the listed cases and is not BIM clash detection; it is 2D-per-level plus a vertical
slab test, so a duct passing over a beam at a different height inside the same level is reported as a
crossing · penetrations are records, not geometry cut into hosts · site utility networks between
buildings are out of scope · fire content is data only and no coverage, spacing, zoning or hydraulic
evaluation exists · MEP elements do not affect navigation, egress or walking distance in this phase,
by design · the 5000-element Python normalisation takes ~1.6 s, dominated by interference, and was
left unoptimised deliberately · **full WebGL rendering was not verified in this environment**:
`public/vendor/` is empty because the sandbox has no outbound network, so the MEP debug layers were
verified by running the repository's own `compile()` against a recording stub in Node and in
Chromium — pixel output remains **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**, as is the live
Render backend (`fastapi` is absent here; the API module compile-checks clean).

---

# Z. FIRE & LIFE-SAFETY DATA MODEL FOUNDATION

**Representation and topology only. No fire design and no fire simulation** — no sprinkler spacing,
coverage, hydraulics, density or demand-area selection; no fire-water demand, pump or tank sizing;
no detector spacing or quantity; no alarm zoning, audibility or notification design; no
fire-resistance rating calculation or inference; no evacuation or egress compliance. **No NFPA, SBC,
IBC or Civil Defense rule value.** No auto-fix, no automatic device placement, no automatic zoning.
**There is no Fire / Life-Safety engine.**

## Z1. Architecture
`building.fire_life_safety` sits alongside the other layers and **connects what already exists**
rather than restating it:

    exits            ← the egress foundation (still the only source of truth for exits)
    devices          ← the MEP model and the Phase 1 adapter
    systems          ← MEP fire-relevant systems
    stairs / shafts  ← the architectural cores and MEP risers
    barriers / fire doors / zones / signs / assembly / refuge / smoke control ← declared only

A model with no `fire_life_safety` key compiles to `NOT_DEFINED` with **zero issues** — absence is
never a fault.

## Z2. Files changed
New: `acs_fls.json` (spec), `acs_fls.py` (compiler + validator + adapters + audit), browser mirror
in `public/index.html` (drift-tested byte-identical). Changed: `public/index.html` (mirror, nine
discipline debug layers, property card, JSON export, developer API), `Dockerfile`,
`PHASE2-FOUNDATION.md`.

## Z3. Status and provenance
Twelve element types. Status is `NOT_DEFINED · PARTIAL · REPRESENTED · IMPORTED · VERIFIED_DATA` —
`COMPLIANT`, `SAFE`, `APPROVED`, `CERTIFIED` and `DESIGNED` are deliberately absent. Provenance is
`user · imported · ai_inference · system_default · manual_verified · phase1_adapter · mep_adapter ·
egress_adapter · arch_adapter · test_fixture · display_fallback · unknown`.

**`code_required` and `rule` are declared FORBIDDEN provenance.** A model that claims
`source: "code_required"` has it neutralised to `unknown` rather than obeyed; the string does not
appear in any compiled model; and every audit reports `code_required: 0`. A system-added Phase 1
smoke detector travels through **two** adapters (Phase 1 → MEP → FLS) and still reports
`original_source: system_default` — asserted directly.

## Z4. Adapters do not duplicate
The egress foundation stays the only exit engine — there is no second exit inference anywhere, and
the FLS exit list matches `extract_exits()` one-for-one. MEP fire terminals and fire equipment become
device **references** carrying `mep_element_id`; architectural stair cores become stair
**references**. The renderer honours this: an adapted device is `render_mode: "referenced"` and is
**not drawn a second time** — the Phase 1 fixture emits 5 MEP boxes and 0 FLS boxes. Only elements
that exist nowhere else (declared devices, exit signs, assembly points) are `emitted`.

## Z5. Device present is not coverage
Six semantic distinctions are declared in the spec and carried in every compiled model:
`DEVICE_PRESENT` is not `COVERAGE_CONFIRMED`, `SYSTEM_PRESENT` is not `SYSTEM_ADEQUATE`,
`EXIT_PRESENT` is not `EGRESS_COMPLIANT`, `BARRIER_PRESENT` is not `FIRE_SEPARATION_COMPLIANT`,
`SIGN_PRESENT` is not `SIGNAGE_ADEQUATE`, `RATING_STATED` is not `RATING_VERIFIED`. Every
`DEVICE_IN_SPACE` edge carries *"a represented X in a space is not coverage or protection of that
space"*. The words *protected* and *covered* appear in no field of any compiled model.

## Z6. Nothing is classified automatically
A normal architectural door yields **no** fire door; declaring one explicitly creates exactly one
reference to the real architectural opening. An architectural shared wall and a structural shear
wall yield **no** barrier. An adapted stair is `protection_status: unknown` and is never called
protected. An MEP riser is not a fire shaft. A room is never turned into a compartment — with no
zone data, `zones` is empty. A rating is carried only when supplied and is **never inferred from a
material**; an unstated rating stays `null` with that sentence attached.

## Z7. Absence is not a violation
No issue code names a missing element. A villa fixture with no sprinklers reports
`sprinklers: 0`, not a deficiency. A warehouse gets no sprinkler or hydrant for being a warehouse.
Data-gap notes (`RATING_UNKNOWN`, `PROTECTION_UNKNOWN`, `DEVICE_WITHOUT_SYSTEM`,
`ZONE_WITHOUT_SPACES`) are INFO, apply only to **declared** elements, and say *"this is a data gap,
not a violation"* in the issue itself.

## Z8. Relationships and integrity
Thirteen relationship types, all factual, all carrying *"never coverage, protection, adequacy or
compliance"*. Loops, panels and alarm zones are represented only where declared and are never
designed or derived from floors. 28 issue codes with `INFO / WARNING / ERROR`; `UNSAFE`,
`CODE VIOLATION` and `FIRE VIOLATION` are absent. A deliberately broken fixture triggers **all 28**.
An exit sign pointing at an unresolved exit is an ERROR and the target is **never invented**.

## Z9. Egress, distance and occupancy
`egress_facts()` quotes an existing measured egress result — status, exit id, `distance_status`,
`walking_distance_m` — as factual data with `compliance: "NOT_EVALUATED"`, and **never compares it
to a travel-distance limit**. No such limit exists in the layer. A building programme is explicitly
not a fire occupancy classification, and the verified regulatory occupancy count is still zero.

## Z10. Audit
Factual counts only, plus `coverage: NOT_EVALUATED`, `compliance: NOT_EVALUATED` and
`code_required: 0`, with the note *"A missing element is NOT a violation"*.

## Z11. Renderer, GLB and JSON
Meshes are named `FLS|<TYPE>|<id>` across nine debug layers (`FLS_DETECTION`, `FLS_ALARM`,
`FLS_SUPPRESSION`, `FLS_FIRE_WATER`, `FLS_EMERGENCY_LIGHTING`, `FLS_SIGNAGE`, `FLS_BARRIER`,
`FLS_FIRE_DOOR`, `FLS_ZONE`, plus `FLS_OTHER`), **hidden by default** and out of the floor filter.
Layer labels themselves say *data only*. Colour marks element type only — the spec states there is
**no red-means-violation logic**. JSON export adds `fire_life_safety` and
`fire_life_safety_compiled` additively.

## Z12. Revision hashing
Verified by test: moving a detector, removing a sprinkler, changing a fire-door rating, changing zone
membership, changing an exit-sign target and changing a fire system reference each change the
building hash; toggling `layer_visibility` and moving the camera do not; compiling the FLS model does
not.

## Z13. No regression anywhere
Asserted directly: the compiled architectural, structural **and MEP** models are byte-identical with
and without an FLS block; compiling FLS does not mutate the MEP model; the relationship graph, the
navigation path, the egress selection and the measured walking distance are all byte-identical.
**Fire objects are not navigation obstacles and change no route in this phase.**

## Z14. Tests, parity, performance (executed)
FLS suite **169/169** and renderer suite **51/51**, each in Node and in Chromium. Full regression:
19 suites in Chromium and 17 in Node, **1602 assertions, 0 failures**, plus 107 backend/config
security checks and 9 D-1 checks. JS↔Python parity **15/15 byte-identical** compiled FLS models —
the five programme fixtures plus the fire-door before/after pair, the single-detector case, the
Phase 1 adapter, the broken fixture, the empty model and three transformed/renamed-building
variants, comparing the whole model, the summary, the audit, the render items, the rule inputs and
the validation output.

| Target devices | Devices | Relationships | Render items (emitted) | JS normalise | JS validate | JS render | JS audit | Py normalise | Py validate |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 80 | 80 | 84 (59) | 1 ms | 0 ms | 1 ms | 1 ms | 0 ms | 0 ms |
| 500 | 400 | 387 | 418 (293) | 5 ms | 1 ms | 1 ms | 0 ms | 4 ms | 0 ms |
| 1000 | 800 | 766 | 836 (586) | 11 ms | 0 ms | 2 ms | 0 ms | 10 ms | 1 ms |
| 5000 | 4000 | 3786 | 4179 (2929) | 55 ms | 4 ms | 18 ms | 2 ms | 55 ms | 8 ms |

MEP adapter overhead at 5000 devices: 63 ms (JS) / 173 ms (Python), measured separately. Device,
relationship, render-item and issue counts are identical in both languages at every scale.

## Z15. Developer API
`ACS.fireLifeSafety(bid)` · `ACS.flsDevices(bid)` · `ACS.flsSystems(bid)` · `ACS.flsZones(bid)` ·
`ACS.flsBarriers(bid)` · `ACS.flsOpenings(bid)` · `ACS.flsExits(bid)` · `ACS.flsSigns(bid)` ·
`ACS.flsStairs(bid)` · `ACS.flsIssues(bid)` · `ACS.flsAudit(bid)` · `ACS.flsSummary(bid)` ·
`ACS.flsElement(id,bid)` · `ACS.flsRenderItems(bid)` · `ACS.flsRuleInputs(bid)` ·
`ACS.flsEgressFacts(spaceId,bid)` · `ACS.flsLayerVisible(layer,on)`. All read-only and derived on
demand; the visibility toggle is pure view state and is excluded from the revision hash.

## Z16. Future rule contract
`fls.device.exists.<TYPE>`, `fls.device.count.<TYPE>`, `fls.device.count`, `fls.exit.count`,
`fls.zone.exists`, `fls.zone.count`, `fls.fire_door.count`, `fls.fire_door.rating`,
`fls.fire_door.self_closing`, `fls.barrier.rating`, `fls.barrier.type`, `fls.system.exists.<TYPE>`,
`fls.member.source`. **Inputs only**: no regulatory fire rule exists, an absent device type is
exposed as `false` rather than as a deficiency, and the map contains no limit, threshold or verdict.

## Z17. Known limitations — stated, not hidden
No fire engine of any kind — no coverage, spacing, hydraulic, audibility or rating evaluation · fire
compartments are polygon-free lists of space references with no geometric boundary solving · barrier
continuity is a declared label, never checked across levels or openings · smoke control entries are
inert placeholders · an assembly point has no route from any exit and no site evacuation exists ·
areas of refuge carry no capacity and no accessibility evaluation · alarm loops and zones are
declared memberships, never designed · device-in-space is a point-in-rectangle test at the assigned
level, not a coverage model · FLS elements affect no navigation, egress or distance result, by
design · the layer reads the MEP model, so MEP compilation cost dominates at scale (173 ms of the
Python 5000-device run) and was left unoptimised deliberately · **full WebGL rendering was not
verified in this environment**: `public/vendor/` is empty because the sandbox has no outbound
network, so the FLS debug layers were verified by running the repository's own `compile()` against a
recording stub in Node and in Chromium — pixel output remains **NOT VERIFIED — EXTERNAL ENVIRONMENT
REQUIRED**, as is the live Render backend (`fastapi` is absent here; the API module compile-checks
clean).

# AA. MULTIDISCIPLINARY COORDINATION & CLASH FOUNDATION

**Detection and traceability only.** This layer reads the compiled architectural, structural, MEP
and fire/life-safety models and reports where they conflict. It performs no auto-fix and no design:
it never moves an MEP route, resizes a beam, moves a door, creates a penetration or an opening,
sizes a sleeve, reroutes a pipe or duct, or repositions equipment. It draws no code, safety or
adequacy conclusion. A clash is a coordination finding about modelled geometry and references —
nothing more.

## AA1. Architecture
`acs_coord.json` is the single source of truth for the vocabulary — four disciplines, eight clash
types, five statuses, four reconciliation states, three severities, six cross-discipline pairs,
eighteen element kinds, eight semantic exemptions, the 2 m grid cell, the broad- and narrow-phase
descriptions and the forbidden-claim list. `acs_coord.py` is the detector. The browser carries the
JSON **verbatim** as `ACS_COORD_SPEC` and a line-by-line mirror of the detector, and a drift test
fails the build if the two copies ever diverge. The layer is derived: compiling it leaves the
architectural, structural, MEP and FLS models byte-identical, which is asserted for every fixture
and for the four compiled models together.

## AA2. Files changed
`acs_coord.json` (new) · `acs_coord.py` (new) · `public/index.html` (mirror, debug overlay, marker
helpers, developer API) · `Dockerfile` (both new files copied into the container) ·
`PHASE2-FOUNDATION.md` · `VERIFICATION-RUNBOOK.md`. Nothing in the architectural, structural, MEP or
fire layers was modified.

## AA3. One world frame, no axis shortcut
Every element is resolved into a world-space oriented box — centre, half-extents and rotation about
Y — before any test. Building position, building rotation, element or grid rotation and level
elevation are all applied first. Rotating the same fixture through 0°, 45° and 90°, and translating
it, yields the same set of findings with different coordinates; the test asserts both halves of that
claim, so a world-axis shortcut cannot pass silently.

## AA4. Broad phase, honestly measured
A uniform spatial hash with a 2 m cell. Each element's index box is inserted into every cell it
overlaps and candidate pairs are the cross-discipline pairs sharing a cell. An element whose index
box spans more than 4096 cells is not indexed at all — it is placed in an oversized list and
compared against every other element, so no pair is ever lost, and the count is reported in
`statistics.oversized_elements` rather than hidden. `statistics.busiest_cell` and
`statistics.candidate_pairs` are reported for the same reason: the behaviour of the acceleration
structure is visible, not asserted.

## AA5. Narrow phase
World AABB overlap with a strictly positive overlap volume, then a separating-axis test on the two
Y-rotated boxes. No mesh boolean is performed and none is needed for the box and swept-segment
geometry this platform emits. Proximity alone never produces a hard clash, and a shared face is
contact rather than intersection — both are asserted directly.

## AA6. Negative space is not matter
`ARCH_VOID` and `ARCH_CORE` are declared negative space: the architectural layer itself punches a
floor void through every slab a core passes. They carry `solid: false`, are indexed but never act as
clash bodies, and an element lying inside one is recorded as `ELEMENT_INSIDE_DECLARED_VOID_OR_CORE`
in the suppressed list. Nothing is dropped in silence, and the layer draws no conclusion about
whether that element belongs there.

## AA7. Exemptions are semantic, never type-blind
Eight exemptions, each justified by an explicit declaration in the models: an opening inside its own
declared host wall; a service segment crossing a wall inside one of that wall's declared openings; a
segment inside a declared penetration that actually covers the crossing; a column through the slab
of a level it spans; a beam meeting a column it is declared to connect to; two representations of
the same source element; an FLS device and the MEP element it references; and an element inside a
declared void or core. No clash is dropped because of the kinds of the two elements involved — the
test proves a column is exempt at its own levels and not exempt at a level it does not span, and
that an opening is exempt in `w1` and not in `w2`. Every applied exemption is recorded with both
element ids on the pair it suppressed.

## AA8. Penetrations
A represented penetration is not a structurally approved opening, is not firestopped and is not code
compliant — the wording travels on every penetration record. Beyond resolving host and service, the
layer checks whether the stated penetration geometrically covers the crossing it claims: covered
suppresses the finding and is logged, not covered raises `PENETRATION_UNRESOLVED`, and a penetration
with no stated position yields no verdict at all rather than a guess. No sleeve size is ever
produced.

## AA9. Geometry confidence
Every geometric clash declares whether both sides were sized from stated model dimensions
(`stated`) or whether at least one side fell back to a render dimension (`display_fallback`), and in
the latter case names which side and repeats that the fallback is never promoted to an engineering
dimension. This is the platform's standing rule applied to coordination: an intersection of display
placeholders is reported as found and labelled, never dropped and never presented as a measured
conflict. In the deliberate clash fixture the four service-through-structure findings are `stated`
and the fifty architectural-versus-structural overlaps are `display_fallback` — the distinction is
visible in `summary.by_geometry_confidence`.

## AA10. Clearance only where stated
A clearance clash exists only where an element states `clearance_m`. No service, maintenance or code
clearance is invented, and with no stated clearance there is no clearance clash — asserted across
four fixtures. The index box is widened by the stated clearance so the broad phase cannot lose a
clearance pair that the AABBs alone would never bring together.

## AA11. Identity, statuses and reconciliation
A clash id is `clash_` plus the first sixteen hex characters of sha256 over the canonical tuple
(type, discipline A, element A, discipline B, element B) — deterministic, identical in both
languages, and the reason reconciliation between revisions is possible at all. `RESOLVED` is
deliberately absent as an automatic status: a clash that no longer appears in a newer snapshot is
`RESOLVED_BY_MODEL_CHANGE` or, if a human had already acted on it, `OBSOLETE` — never "engineered
correctly". `ACKNOWLEDGED`, `RESOLVED_EXTERNALLY` and `FALSE_POSITIVE` come only from an explicit
human decision that records who decided and on what basis; `OPEN` and `OBSOLETE` are refused as
inputs.

## AA12. Snapshot integrity
A single-building snapshot stores the model revision hash; a project snapshot stores one entry per
building carrying the model hash **and the placement**, so a building that merely moved invalidates
the snapshot. `check_snapshot` and `check_project_snapshot` return `CURRENT`,
`STALE_MODEL_CHANGED` or `UNVERIFIABLE` and set `presented_as_current` accordingly — a stale
snapshot is never shown as current and is never silently recomputed.

## AA13. Project scope
Coordination runs across buildings. Each building is resolved into world coordinates first, so two
buildings never clash merely because their local coordinates coincide; every clash names
`building_a`, `building_b` and `cross_building`. Two fixtures 30 m apart produce no cross-building
finding, the same two at 1 m apart produce eight, and the two projects have different snapshot ids
because placement is part of identity.

## AA14. Semantic conflicts are re-classified, never invented
`INVALID_REFERENCE` and `SEMANTIC_CONFLICT` are lifted from the integrity issues each discipline
layer already reports — the coordination layer names the reporting discipline, the source issue code
and the partner discipline, and carries no geometry. It invents no new reference check of its own.

## AA15. Renderer, export and revision
Coordination emits no geometry into the model. The debug overlay highlights the two elements,
isolates them and adds a single translucent marker box at the intersection — added to the **scene**,
never to the building group that `GLTFExporter` serialises, and flagged `acs_debug_only`. Running
the repository's own `compile()` against a recording stub over eight models before and after the
layer was injected produced byte-identical mesh trees, which is the direct evidence that normal
model appearance is unchanged. The coordination snapshot is exported only through
`ACS.exportCoordination()`, is marked `derived: true`, and is never merged into the normal model
export or into any revision hash.

## AA16. Navigation and egress are untouched
Coordination findings do not affect navigation, egress, pathfinding or walking distance in this
phase. A column that geometrically blocks a door is reported as a clash and nothing is silently
rerouted; the test confirms the architectural opening set is unchanged after the detector runs.
Obstacle-aware navigation is a future explicit phase.

## AA17. Tests, parity, performance (executed)
`/tmp/test_coord.js` — **131 checks, 131 passed** in Node and **131 passed, 0 page errors** in real
Chromium via Playwright. Full regression re-run after the change: eighteen other Node suites and all
twenty browser suites green (p0 17 · gate 21 · xss 6 · types 33 · prov 39 · phase2 47 · rel 48 · nav
43 · eg 55 · dist 80 · rules 129 · ingest 188 · occ 98 · rev 99 · arch 147 · render 51 · struct 177
· mep 183 · fls 169 · coord 131). Backend/config security **122 passed, 0 failed** including fifteen
new coordination checks. Developer-API probe **17 passed, 0 failed**, executing the block injected
into `index.html` rather than a model of it. JS↔Python parity **20/20 byte-identical** over the
coordination fixtures, and all ten parity suites re-verified green (arch 23 · struct 13 · mep 13 ·
fls 15 · ingest 30 · occupancy 27 · revision 16 · rules 28 · distance 26 · coord 20). Every Python
module compiles and imports.

Benchmarks, both languages, this machine, 100/500/1000/5000/10000 target elements. Both languages
agree exactly on element count, grid cells, candidate pairs, clashes and suppressions at every size:

| target | elements | grid cells | candidate pairs | clashes | JS broad ms | JS narrow+build ms | Py broad ms | Py narrow+build ms |
|-------:|---------:|-----------:|----------------:|--------:|------------:|-------------------:|------------:|-------------------:|
|    100 |      247 |      1 108 |             740 |     305 |          10 |                 25 |          ~9 |                 ~40 |
|    500 |    1 173 |      5 108 |           3 864 |   1 578 |          58 |                111 |         ~45 |                ~200 |
|  1 000 |    2 316 |      9 799 |           7 810 |   3 186 |          63 |                184 |         ~62 |                ~400 |
|  5 000 |   11 394 |     35 168 |          42 076 |  16 107 |         333 |              1 041 |         305 |              2 100 |
| 10 000 |   22 702 |     69 714 |          84 400 |  32 300 |         717 |              2 541 |         595 |              4 454 |

Scaling is near-linear in elements; `oversized_elements` was 2 at the two largest sizes (the site
slabs) and `busiest_cell` stayed at 11–12 throughout, so the spatial hash never degenerated.

## AA18. Developer API
`ACS.coordination(bid,pos,rot)` · `ACS.clashes(bid)` · `ACS.clash(id,bid)` ·
`ACS.clashesByDiscipline(a,b,bid)` · `ACS.coordinationIssues(bid)` ·
`ACS.coordinationSummary(bid)` · `ACS.coordinationPenetrations(bid)` ·
`ACS.coordinationSuppressed(bid)` · `ACS.coordinationRuleInputs(bid)` ·
`ACS.setClashStatus(id,status,by,at,note,bid)` · `ACS.coordinationSnapshotStatus(snapshot,bid)` ·
`ACS.compareCoordinationRevisions(a,b)` · `ACS.exportCoordination(bid)` ·
`ACS.clashDebugView(id,bid)` · `ACS.highlightClash(id,bid)` · `ACS.clearClashHighlight()`. All
read-only and derived on demand, except the status setter, which records an explicit human decision.
There is deliberately no fix, reroute, resize or optimise entry point, and the test asserts that no
such name exists on the object.

## AA19. Future rule contract
`coordination.clash.count`, `coordination.clash.count_by_type.<TYPE>`, `coordination.issue.exists`,
`coordination.penetration.exists`, `coordination.penetration.count`. **Inputs only**: no regulatory
rule exists here, a clash count is never compared to a threshold, missing data stays missing, and a
model with no clashes reports zero rather than a clean verdict.

## AA20. Known limitations — stated, not hidden
Geometry is boxes and swept segments only — a genuinely non-convex element would be tested through
its oriented box, which is conservative but coarser than a mesh boolean · penetration coverage is a
2D position-and-radius test with a 0.5 m tolerance, not a swept-profile check · the clearance box is
axis-aligned around the element's world AABB rather than around its oriented box · architectural
and structural elements that represent the same physical member are reported as overlapping because
no discipline declares that relationship except for structural walls, and `geometry_confidence`
labels the resulting findings rather than suppressing them · same-discipline clashes are not tested
here by design · a clash is never ranked by importance, only by severity, and severity reflects data
integrity rather than engineering consequence · coordination affects no navigation, egress or
distance result · **full WebGL rendering was not verified in this environment**: `public/vendor/` is
empty because the sandbox has no outbound network, so the debug overlay was verified by executing
the injected API block and the repository's own `compile()` against a recording stub in Node and in
Chromium — pixel output remains **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**, as is the live
Render backend (`fastapi` is absent here; the API module compile-checks clean).

# AB. VISUAL RENDERING & PRESENTATION FOUNDATION (PHASE 3)

**Geometry-preserving visualisation only.** This layer reads the compiled architectural,
structural, MEP, fire/life-safety and coordination models and produces a derived visual scene —
objects, materials, lights, cameras, environment and presentation state. It never moves a wall, a
door, a window, a stair, a structural member, an MEP route or a fire device; it never adds or
removes a room, changes the floor count, or alters the building footprint. Appearance is not
engineering truth.

## AB1. Visual architecture
```
CANONICAL BUILDING MODEL
        ↓  (architecture · structure · MEP · fire/life-safety · coordination)
    VISUAL SCENE            derived; objects carry source_element_id
        ↓
MATERIALS · LIGHTING · CAMERA      appearance only, each with provenance
        ↓
  PRESENTATION RENDER       deterministic; carries the model hash
        ↓
 OPTIONAL AI ENHANCEMENT    downstream, constrained, labelled VISUALISATION
```
Nothing flows back up that pipeline. `acs_visual.json` is the single source of truth for the
vocabulary; `acs_visual.py` is the deterministic scene compiler; the browser carries the JSON
**verbatim** as `ACS_VISUAL_SPEC` plus a line-by-line mirror of the compiler, and a drift test fails
the build if the two ever diverge. Pixel rendering stays browser-side; the scene metadata that
decides what those pixels show is deterministic and tested in both languages.

## AB2. Files changed
`acs_visual.json` (new) · `acs_visual.py` (new) · `public/index.html` (mirror, presentation
renderer pass, developer API) · `Dockerfile` (both new files copied) · `PHASE2-FOUNDATION.md` ·
`VERIFICATION-RUNBOOK.md`. No architectural, structural, MEP, fire or coordination file was
modified.

## AB3. VisualScene schema
`schema · compiler_version · building_id · model_hash · scene_id · created_at · mode · transform ·
bounds · objects[] · materials[] · lights[] · cameras[] · active_camera · environment ·
presentation · drawing · clash_overlay · spaces_index · counts · summary · meta`. Every object
carries `id · kind · layer · geometry{box,cx,cy,cz,ex,ey,ez,rot_y} · material ·
material_provenance · semantic · visual_only · lod · asset_id · asset_fallback · instance_key ·
geometry_source · visible · source_layer · source_element_id`. The source-reference rule is universal and symmetric, and holds
for every object regardless of `visual_class`, material, theme, asset, LOD, geometry source, render
mode, discipline or decoration category: `visual_only: false` **must** carry a `source_element_id`
(otherwise `MODELLED_OBJECT_WITHOUT_SOURCE`), and `visual_only: true` **must not** carry one at all
(otherwise `VISUAL_ONLY_OBJECT_WITH_SOURCE`). `DECORATION_LINKED_TO_MODEL_ELEMENT` is a
specialisation reported *in addition* for a decoration object, never instead of the universal code.
The eight validation codes are declared in `acs_visual.json` and are drift-protected.

## AB4. Visual modes
Nine modes over one model: ENGINEERING · ARCHITECTURAL · PRESENTATION · DOLLHOUSE · CUTAWAY ·
FLOOR_PLAN_2D · SECTION · ELEVATION · VR. A mode changes what is shown, how it is shaded and where
the camera stands. The wall count, the door coordinates and the model hash are identical across all
nine — asserted directly.

## AB5. Engineering mode
Kept, unchanged in intent and available at all times, with the architectural, structural, MEP and
fire layers all on and the coordination overlay available on request. Clarity over realism:
elements are shaded technically and per-discipline. The engineering view **refuses** to hide a
discipline — `set_layer_visible` returns `ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE` — because
hiding one would misrepresent the model rather than present it.

## AB6. Architectural mode
Wall, floor and ceiling finishes, doors, window glazing, roof surfaces and the stair core, all
drawn from the same compiled geometry. Ceilings appear here and are deliberately absent from the
engineering view. Where the model states no roof, a `ROOF_CAP` is emitted — flagged `visual_only`,
`geometry_source: display_fallback`, with no source element — so a visual cap can never be mistaken
for a modelled roof.

## AB7. Presentation mode
Sun, sky and ambient rig, shadow maps, ACES tone mapping, exposure, environment quality, a composed
camera and a ground plane. Geometry is untouched: the same door sits at the same coordinates in
presentation as in engineering.

## AB8. Materials
Twenty-three parametric materials across fourteen families — paint, plaster, concrete, stone, wood,
glass, metal, tile, carpet, fabric, asphalt, grass, water, technical — each `base_color ·
roughness · metalness · opacity`. Every one is classified `VISUAL_MATERIAL` and every emitted
material explicitly carries `fire_rating: null`, `thermal_property: null`,
`structural_material: false`. A wall that looks like concrete is not a concrete wall, and no
rating, class or property may be inferred from a material name.

## AB9. Material provenance
`USER · IMPORTED · AI_SUGGESTED · SYSTEM_DEFAULT · VISUAL_THEME`. A system choice records
SYSTEM_DEFAULT, a theme choice records VISUAL_THEME, and an AI suggestion stays AI_SUGGESTED — none
of them is ever recorded as a user requirement. The test asserts each of the four paths separately.

## AB10. Themes
Modern · Contemporary · Classic · Industrial · Minimal · Luxury · Neutral. A theme selects finishes
and light colour only. The compiled architecture is byte-identical across all seven, and so is the
geometry of every non-visual object — both asserted.

## AB11. Decoration and furniture
A `FURNITURE` layer of `VISUAL_DECORATION` objects, deterministic per space and **off by default**.
Every decoration object is `visual_only: true`, `semantic: false`, has no `source_element_id`, and
is excluded from the engineering export. An object the user actually requested lives in the
engineering model and stays there — decoration is never confused with it and is never promoted into
the model, which this phase deliberately does not implement.

## AB12. No decoration laundering
Decoration, entourage and landscape are counted separately in `counts` and excluded from
`export_scene(presentation_glb=False)`. No occupant, coverage, load or code field anywhere in the
scene refers to them — asserted by field scan across every fixture.

## AB13. Exterior and interior visualisation
Facades, windows, doors, the roof cap and a visual ground plane. Site geometry is never invented: a
stated `site` gives a ground plane at the stated size; a model with no site still renders and the
plane declares `site_dimensions_stated: false` with a note that its extent is not a boundary. Water
appears only for an explicitly represented pool, fountain or water feature — no pool is invented in
any of the sixteen fixtures. Interior cameras stand at eye height inside real spaces and no room is
faked.

## AB14. Dollhouse
Roof and ceilings hidden, enclosure clipped above a stated height, `reversible: true`. It is
expressed as visibility and clipping directives over the *same* objects — the architectural
geometry in dollhouse is byte-identical to architectural mode, and every room keeps its exact
position and size.

## AB15. Cutaway
`CLIP_PLANE · LEVEL_ISOLATION · WALL_CLIP`, all reversible rendering state recorded on the scene
and applied through renderer clipping planes. An unknown method falls back rather than failing, and
the wall geometry is identical to architectural mode.

## AB16. 2D floor plans
Walls, openings, room boundaries with names and label anchors, stairs and dimensions, projected
from the same architectural geometry as the 3D view. Wall and opening counts equal the model's own
counts for that level. Four styles — TECHNICAL · CLEAN · MONOCHROME · ZONING — all yield identical
geometry. A level that does not exist reports `level_exists: false` rather than inventing one, and
the plan states plainly that it makes no CAD-grade claim.

## AB17. Dimensions
Room width and depth, wall length, opening width, all `source: model` and all matching the model
within 1e-6. A dimension the model does not state is emitted as `value_m: null` with
`source: unknown` and is counted in `unknown_dimensions` — never replaced by a plausible number.

## AB18. Sections
An orthographic cut on a stated plane, defaulting to the centre of the building footprint on the
cross axis. Levels, slabs, cut walls, openings crossed by the plane and stair cores are projected.
A section through a doorway shows the opening; a section outside the building cuts nothing rather
than inventing something. No structural or code interpretation is made.

## AB19. Elevations
North · South · East · West, projected from the real envelope walls and their real openings. Every
opening in an elevation exists in the model — asserted by id — and a facade with no openings
honestly shows none rather than balancing itself.

## AB20. Cameras
Ten presets: Exterior Front · Exterior Rear · Exterior Corner · Top · Dollhouse · Interior Room ·
Walkthrough · Section · Elevation · Panorama 360. Framing is computed from the model's own bounding
volume via a bounding-sphere fit with a stated 1.25 margin, so the building is fully visible with a
reasonable margin and the exterior camera provably sits outside the bounds. Section and elevation
cameras are orthographic. Camera state is flagged `presentation_state: true`, and cycling every
preset regenerates no geometry — asserted.

## AB21. Lighting, day/night and shadows
Sun, sky and ambient, plus interior visual emitters at night. Every light is `visual_only: true`
and carries the note that it is not an MEP luminaire; conversely an MEP fixture is never treated as
a presentation light. A night emitter is placed only at a *represented* fixture and asserts nothing
about its output — a model with no fixtures gets no emitters. No lux, illuminance or adequacy claim
appears anywhere. Shadows are a quality setting (off at LOW, on from MEDIUM up), never a geometry
change.

## AB22. Quality profiles, LOD and instancing
LOW · MEDIUM · HIGH · ULTRA control pixel ratio, shadow map size, texture budget, anti-aliasing,
tone mapping, environment quality and the visual object budget. Geometry is identical across all
four. LOD degrades visual-only detail first and never removes a modelled element — asserted even at
a budget of one. Instancing groups only visual-only objects sharing an asset and a material;
`modelled_objects_merged` is structurally zero, because merging a modelled element would destroy
per-element selection.

## AB23. Snapshot export
PNG and JPEG with resolution, camera, mode, background and quality. An absurd resolution is clamped
to the 33.2 Mpx ceiling and the clamp is reported as `SNAPSHOT_EXCEEDS_MAX_PIXELS`; an unsupported
format is refused as `SNAPSHOT_FORMAT_UNSUPPORTED` rather than silently accepted. `ACS.snapshot()`
performs the actual pixel render in the browser and, where no WebGL context exists, returns
`rendered: false` with `NOT VERIFIED — a real WebGL context is required` rather than a fake image.

## AB24. Render metadata
Every render records `model_hash · building_id · scene_id · visual_mode · camera · theme ·
material_preset · lighting_preset · quality · width · height · format · kind · compiler_version ·
created_at`, plus a deterministic `render_id` (sha256 over the canonical body). A deterministic
render is authorised `ENGINEERING_VIEW_OF_MODEL`; an AI-enhanced image is authorised
`VISUALISATION` and `is_engineering_model: false`. An unknown render kind falls back to
deterministic — never to AI.

## AB25. Revision integrity of a render
`check_render_currency` returns `CURRENT`, `STALE_MODEL_CHANGED` or `UNVERIFIABLE` and sets
`presented_as_current` accordingly. A render of a model that has since changed stays historical and
is never relabelled current. Presentation state lives in a separate additive `presentation` block
that declares `affects_revision_hash: false`; no visual value enters any revision hash.

## AB26. AI enhancement architecture
`CANONICAL_MODEL → DETERMINISTIC_BASE_RENDER → CONTROL_BUFFERS → AI_ENHANCEMENT →
PRESENTATION_IMAGE`. `ai_enhancement_request()` returns the pipeline, the required base render, the
ordered names of the buffers that were requested (`requested_control_buffers`), a map from each of
those names to its **deterministic buffer descriptor** (`control_buffers`), the geometry signature,
the may-change and may-not-change lists, and three flags that are structurally false:
`writes_to_model`, `generator_shipped`, `network_call`. A descriptor is data computed from the
compiled model — the modelled object ids, the room ids, the semantic classes, the counts — not a
rasterised image; this phase renders no buffer to pixels and claims none.
**This phase ships no image generator, makes no network call, and provides no path by which an
enhanced image can be written into any model.**

## AB27. Geometry guard
The AI may change materials, lighting, vegetation, weather, furniture style, surface detail, sky and
post-processing. It may not change wall positions, door count, window count, floor count, stair
location, building footprint, room count or level elevations. The guard is not a promise but a
signature: `geometry_signature()` captures door/window/wall/stair counts, floor count, room count,
footprint and model hash from the compiled model, and travels with every request.

## AB28. Control buffers and visual drift detection
Six deterministic descriptors of the real geometry — depth, normal, object_id, semantic_mask,
edge, room_id — each carrying `deterministic: true`, `from_model: true` and the ids, classes or
counts a future generator would consume. The object-id descriptor lists only modelled objects; the
room-id descriptor lists only canonical space references. **No descriptor is a pixel buffer, and no
pixel buffer is generated in this phase.** A request with no geometry signature is not a valid
constrained request: the consistency check raises `VISUAL_SIGNATURE_MISSING` rather than silently
passing an unconstrained image. `check_visual_consistency()` compares
what an image claims against the signature and raises `VISUAL_GEOMETRY_DRIFT` plus a specific code
(`VISUAL_FEATURE_COUNT_MISMATCH`, `VISUAL_LEVEL_COUNT_MISMATCH`, `VISUAL_FOOTPRINT_MISMATCH`,
`VISUAL_SOURCE_HASH_MISMATCH`, `VISUAL_CONTROL_BUFFER_MISSING`, `VISUAL_SIGNATURE_MISSING`). A footprint within tolerance is not
flagged. Every result carries `model_modified: false` and `image_accepted_as_geometry: false` — the
model is never overwritten and the image is never promoted to geometry.

## AB29. VR
VR uses the same geometry as presentation — asserted byte-for-byte. One model metre is one physical
metre: `scale: 1`, `scale_is_explicit: false`. An explicit visualisation scale is recorded and
flagged; an invalid scale falls back to 1:1 rather than distorting silently. WebXR remains the
existing architecture and no separate VR model is built.

## AB30. Walkthrough
A `WALKTHROUGH` camera preset over the existing navigation and camera systems. The spec states in
its own text that walkthrough is not accessibility-compliant navigation; it makes no clearance,
width or route-adequacy claim and changes nothing in the navigation, egress or walking-distance
layers.

## AB31. Asset library
Fourteen local procedural assets, each with `id · type · asset_class · dimensions_m · license ·
source · author`. Nothing is downloaded, no remote host appears anywhere in the library or in any
scene, and a missing asset degrades to a labelled procedural box rather than breaking the render.
`validate_asset()` refuses a missing field, an invalid class, invalid dimensions, an `UNKNOWN`
license, and any metadata field that looks like code (`script`, `code`, `eval`, `onload`, `src`,
`url`, `href`, `exec`) — asset metadata is data and is never executed.

## AB32. Licensing
`PROCEDURAL · CC0 · CC-BY · PROPRIETARY_LICENSED · UNKNOWN`. Everything shipped is `PROCEDURAL`; an
asset with `UNKNOWN` license is never emitted into a scene. Author and source fields are carried
for third-party assets that a future phase may add.

## AB33–AB37. Target results (all executed)
**Villa** — A engineering 3D (52 objects, all four disciplines), B architectural exterior (65),
C dollhouse (65, roof and ceilings hidden, clip at a stated height), D ground-floor plan (20 walls,
7 openings, 6 spaces, 1 stair, 39 dimensions, 0 unknown), E first-floor plan (18/4/5/1, 32
dimensions), F interior living-room camera at 1.6 m eye height inside the real space, G 3840×2160
snapshot request with full metadata. All seven share one model hash.
**Hotel** — exterior, three repeated levels with no per-floor drift, dollhouse on a selected level,
lobby and room interiors, 2D plan; 73 objects, one model hash across every view.
**Warehouse** — exterior and interior render from the same geometry, engineering overlay available,
and the neutral theme gives the warehouse exactly the same wall finish as the clinic — no
warehouse-specific visual style is assumed.
**Clinic** — clean generic interior; every decoration object drawn is from the generic decoration
vocabulary, with no healthcare-specific assumption.
**Mixed-use** — three different floor programmes in one building, three slabs, all rendering
correctly across modes.

## AB38. Performance (executed, this machine)
Scene build, both languages. Pixel FPS and texture memory are honestly unmeasurable here — there is
no WebGL context — and are marked as such in the benchmark output rather than estimated.

| model | spaces | scene objects | modelled | visual-only | draw-call estimate | instance groups | JS build ms | Py build ms | plan ms | section ms | elevation ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| villa | 11 | 77 | 63 | 14 | 66 | 7 | 8 | ~15 | 2 | 1 | 0 |
| hotel | 10 | 73 | 59 | 14 | 62 | 7 | ~7 | ~14 | ~2 | ~1 | 0 |
| warehouse | 4 | 36 | 22 | 14 | 25 | 7 | ~4 | ~8 | ~1 | 0 | 0 |
| project (1000 spaces) | 2 000 | 8 812 | 8 798 | 14 | 8 812 | 0 | 259 | 2 437 | 22 | 7 | 3 |

`fps`, `texture_memory` and `snapshot_pixels_ms` are reported as **NOT VERIFIED — EXTERNAL
ENVIRONMENT REQUIRED** in the benchmark rows themselves.

## AB39. Regression
Nothing in the architectural, structural, MEP, fire/life-safety, coordination, relationship,
navigation, egress, distance, rule, occupancy or revision layers changed. Compiling every visual
mode, theme, quality profile, decoration and entourage combination over the fixtures leaves all
five compiled discipline models byte-identical — asserted directly against
`[arch, struct, mep, fls, coord]`. Running the repository's own `compile()` against a recording stub
over eight models before and after the visual layer was injected produced byte-identical mesh trees:
the visual layer adds its objects to the **scene**, never to the building group that
`GLTFExporter` serialises.

## AB40. Tests, parity (executed)
`/tmp/test_visual.js` — **211 checks, 211 passed** in Node and **211 passed, 0 page errors** in real
Chromium. Developer-API probe **31 passed, 0 failed**, executing the block actually injected into
`index.html`. JS↔Python parity **114/114 byte-identical** over 45 scene queries, 70 derived drawings
and a 45-case operations block. Full regression: all 21 browser suites green (p0 17 · gate 21 ·
xss 6 · types 33 · prov 39 · phase2 47 · rel 48 · nav 43 · eg 55 · dist 80 · rules 129 · ingest 188 ·
occ 98 · rev 99 · arch 147 · render 51 · struct 177 · mep 183 · fls 169 · coord 131 · visual 211),
all eleven parity suites byte-identical, backend/config security **141 passed, 0 failed** including
nineteen new visual checks, and every Python module compiles and imports.

## AB41. Known limitations — stated, not hidden
Visual objects are boxes and swept segments, so a curved or non-convex element is shown through its
oriented box · the roof is a visual cap wherever the model states no roof, and it is labelled rather
than modelled · decoration placement is a deterministic heuristic keyed on room name, not a designed
layout · landscape and entourage positions are deterministic offsets around the bounding box, not a
site design · the 2D plan draws openings as line segments in their host wall with no swing arc, door
leaf or hatch pattern, and no dimension strings or grid bubbles · sections cut on axis-aligned
planes only · elevations pick the outermost wall band within 0.6 m and will under-report a stepped
facade · no texture maps, ambient occlusion, reflection probes or global illumination are shipped ·
the AI enhancement path is an interface, a constraint set and a drift check — **no image generator
exists in this phase** · `check_visual_consistency` compares reported feature counts and footprint,
not pixels, so it detects gross layout drift rather than subtle material or detail drift ·
**full WebGL rendering, real materials, shadows, dollhouse pixels, 2D plan rasterisation, snapshot
pixels, mobile and VR remain NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**: `public/vendor/` is
empty because the sandbox has no outbound network, so everything above was verified by executing the
repository's own code against a recording stub in Node and in real Chromium, and the production
checklist in the runbook exists precisely because the pixels must be signed off on real hardware.

# AC. PHASE 3 AUDIT REMEDIATION & HARDENING

Three audit findings were reproduced independently before any code was changed, and all three were
CONFIRMED. Nothing was fixed by weakening a check, deleting an assertion, changing a test input or
relabelling an unverified item as verified.

## AC1. Finding 1 — the visual-only source rule was not universal
**CONFIRMED.** `validate_scene` enforced the "a visual-only object never names a source element"
half of the contract only when `visual_class == VISUAL_DECORATION`. Evidence: an object
`{visual_only: true, source_element_id: "bld_0.flr_0.wall_0"}` validated clean with no
`visual_class`, with `VISUAL_ONLY_LANDSCAPE` and with `VISUAL_ONLY_ENTOURAGE`, and was caught only
with `VISUAL_DECORATION`. Root cause: the decoration specialisation was written as the *only* rule
rather than as a specialisation of a general one, so the general invariant existed in the
documentation and in the compiler's behaviour but never in the validator.

**Fix.** The rule is now expressed once, symmetrically, and is keyed on `visual_only` alone. The
universal code `VISUAL_ONLY_OBJECT_WITH_SOURCE` was added to a new declared `validation_codes`
vocabulary in `acs_visual.json`; `DECORATION_LINKED_TO_MODEL_ELEMENT` is retained and is now
reported *in addition* for a decoration object, so no previously reported code disappeared. Applied
identically in Python and in the browser mirror.

## AC2. Finding 2 — the AI control-buffer contract was ambiguous
**CONFIRMED.** `ai_enhancement_request()` computed the full buffer descriptors via
`control_buffers()` and then discarded them, placing only `cb["available"]` — a list of names — into
a field called `control_buffers`. Evidence: the field's runtime value was
`["depth","edge","normal","object_id","room_id","semantic_mask"]` and was exactly equal to
`control_buffers(scene)["available"]`, while the descriptors carrying `ids`, `classes` and `count`
were dropped. The Phase 3 report's phrase "six control buffers travel with every request" was
therefore imprecise. A second, related hole was found while reproducing it: a request carrying **no
geometry signature** passed `check_visual_consistency()` with `drift: false`, because every
comparison was skipped when the signature was absent.

**Fix — Option A.** Each requested buffer now travels with its deterministic descriptor. The request
carries `requested_control_buffers` (the ordered names asked for) and `control_buffers` (a map from
each name to its descriptor). No pixel buffer is generated, claimed or implied — the descriptors are
model-derived data, and `deterministic: true` / `from_model: true` travel on each. Separately,
`VISUAL_SIGNATURE_MISSING` (ERROR) was added to the drift vocabulary and a signature-less request is
now rejected rather than silently passed.

## AC3. Finding 3 — verification was not reproducible from a clean checkout
**CONFIRMED.** The repository contained no `tests/` directory of any kind, and
`VERIFICATION-RUNBOOK.md` referenced 25 distinct `/tmp/*` paths. A clean checkout could not
reproduce a single reported number.

**Fix.** Every verification-critical harness now lives in the repository and resolves its paths
relative to the repository root, so it runs from any working directory:

```
tests/
  lib/run.js                      unified Node runner (extracts the browser bundle,
                                  runs a suite in one scope with the real __dirname)
  phase1/  test_p0 · test_gate · test_xss · test_types · test_prov · test_phase2
  phase2/  test_rel · test_nav · test_eg · test_dist · test_rules · test_ingest ·
           test_occ · test_rev · test_arch · test_render · test_struct · test_mep ·
           test_fls · test_coord
           fixtures/   15 vendored scenario files
           parity/     js_<layer>_body.js · py_<layer>.py · compare.js  (10 layers)
  phase3/  test_visual.js · test_visual_adversarial.js · test_dev_api.js
           gen_visual_fixtures.js · perf_visual.js · perf_visual.py
           mesh_invariance_dump.js · run_all.sh
           fixtures/   base · mep · fls · generated visual scenarios
           parity/     js_visual_body.js · py_visual.py · compare.js
           lib/        extract_browser_bundle.js · build_browser_page.js ·
                       run_browser.js · run.js
  security/test_security.py
tools/  build_visual_browser.py   idempotent re-injection of the visual dev API and
                                  presentation renderer pass into public/index.html
```

`sh tests/phase3/run_all.sh` runs the whole Phase 3 verification; `--browser` adds the real Chromium
pass. `/tmp` is used only for run-time output.

## AC4. New permanent regression coverage
`tests/phase3/test_visual_adversarial.js` — **115 checks** covering: the visual-only source rule
across thirteen non-decoration object shapes (generic, landscape, entourage, decoration, asset-based,
system-generated roof cap, theme-generated, AI-suggested-material, instanced, simplified-LOD,
MEP-layered, FLS-layered, site ground plane); the modelled-without-source rejection across four
disciplines; both accepting shapes; the full compile→validate path over every fixture in every mode;
tamper detection on a compiled scene; eight distinct AI signature changes each raising
`VISUAL_GEOMETRY_DRIFT` with `model_modified: false`; four signature-less request shapes each
raising `VISUAL_SIGNATURE_MISSING`; the control-buffer descriptor contract; eight executable asset
metadata fields; material tampering; theme invariance of geometry and hash; and the engineering
view's refusal to hide each of the four disciplines.

Parity gained sixteen adversarial scenes fed identically to both validators, compared on
acceptance/rejection **and** on the exact issue-code sequence.

## AC5. Verification after remediation (all executed here)
| suite | result |
|---|---|
| Python syntax + import (20 modules) | PASS |
| Phase 3 visual (Node / Chromium) | 211/211 · 211/211 |
| Phase 3 adversarial (Node / Chromium) | 115/115 · 115/115 |
| Phase 3 developer API (Node / Chromium) | 31/31 · 31/31 |
| Phase 3 Python↔JS parity | 116/116 byte-identical · 16/16 adversarial agreement |
| Phase 1 suites (Node where DOM-free, Chromium all) | 163/163 |
| Phase 2 suites (Node / Chromium) | 1 499/1 499 |
| Phase 1+2 parity (10 layers) | 211/211 byte-identical |
| security / configuration | 141/141 |
| canonical ↔ browser mirror drift (6 specs) | value-identical; `acs_visual.json` byte-identical |
| mesh invariance over 8 models | byte-identical before/after remediation |
| engineering model hashes | unchanged |

Totals rose from the previous report because regression coverage was added, exactly as expected: the
Phase 3 suite is now 211 + 115 + 31 = **357 checks** rather than 211, and parity is **116/116**
rather than 114/114. No count was preserved artificially.

## AC6. What did not change
No architectural, structural, MEP, fire/life-safety or coordination module was touched — the only
non-test files modified were `acs_visual.json`, `acs_visual.py` and `public/index.html`. CSP is
unchanged, no CDN dependency was added, no network call was introduced, no image generator exists,
and `claude-sonnet-5` is unchanged. The engineering model hashes for all five base fixtures are
identical to before the remediation, and the recording-stub mesh trees over eight models are
byte-identical.
