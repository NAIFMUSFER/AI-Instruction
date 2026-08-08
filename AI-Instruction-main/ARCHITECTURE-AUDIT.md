# AI Construction Studio — Architectural Audit (READ-ONLY, no code changed)

**Question:** is the system `CORE BUILDING ENGINE + building-type/domain rule sets`, or do
industrial/warehouse assumptions leak into the core? **Verdict: core is generic; industrial
is a cleanly-gated optional extension.** One real parity gap found (offline compiler), plus
known capability gaps (type-specific programs, full PROJECT→TWIN hierarchy) that are Phase 2.

Verdicts use **PASS / FAIL / PARTIAL / NOT VERIFIED**. Nothing was modified.

Evidence types: **STATIC** (code read) and **EXECUTED** (ran this session):
- Frontend local pipeline, 10 building types + cross-domain isolation → **33/33 EXECUTED PASS**
- Backend `validate_building → autofix → compile_building` on villa & warehouse → **EXECUTED** (9/10; the 1 is finding D-1)
- Backend security helpers (model allowlist, XFF) → 7/7 EXECUTED (prior turn)
- AI path (LLM `understand()`): **NOT VERIFIED** (needs anthropic + network) — schema/prompt assessed STATIC only.

---

## A. Architectural findings (pipeline stage → who owns what)

| Stage | Generic (core) | Industrial extension (gated) | Evidence |
|---|---|---|---|
| **Type detection** | default `residential`; weighted, needs strong industrial evidence | returns `warehouse` only when `ind≥3 && ind>res` | `acs_understand.py:detect_type` 255–289; FE `detectTypeJS` |
| **Schema (AI)** | `SCHEMA_BRIEF` always (meta/site/levels/floors/rooms + generic `objects`) | `SCHEMA_INDUSTRIAL` **appended only if** industrial; `KNOWLEDGE` vs `KNOWLEDGE_WAREHOUSE`; residential few-shot only if not industrial | `system_prompt` 292–315; `SCHEMA_BRIEF` 25–65; `SCHEMA_INDUSTRIAL` 71–99 |
| **Normalization/Layout** | generic room-packing (`shelf_pack`+shrink), overlap resolve, `ensure_essentials` (door/light/smoke, all `auto:true`) | industrial branch skips packing; industrial lighting/sprinkler grid for open zones | `acs_layout.py:autofix` 223–287; `ensure_essentials` 138–174 (gate at 154) |
| **Validation** | bounds, overlap, min-area, door-per-room, lighting, smoke, outlet/switch heights, corridor width, openings-in-edge — **apply to all types** | rack/lane/dock stats; aisle-width & pallet-aisle rules; extinguisher/exit/assembly/camera/dock-count safety | `acs_validate.py:validate_building` 50–217 (gates at 60, 94, 127, 193) |
| **Compiler (frontend, live)** | walls/doors/windows/points/furniture/**objects** | racks/lanes/stations/docks **only if room carries them**; painted-zone floor only if `_ind && role` | FE `buildRoom`→`buildObjects` 861; gates 615-style |
| **Compiler (offline `acs_compiler.py`)** | walls/doors/windows/points/furniture | racks/lanes/stations/docks gated `if room.get(...)` (615–622); default walls `full` | `build_room` 525–622; `defaults.industrial` 644 |
| **3D** | THREE scene from the model (frontend) | none | — |

**No industrial term is required by the generic path.** Every industrial behavior is behind
`industrial = btype in ("warehouse","industrial","factory","logistics")`, which appears
identically in `acs_understand.py:293`, `acs_layout.py:231`, `acs_validate.py:60`,
`acs_compiler.py:644`.

## B. Generic core confirmed — **PASS**
- EXECUTED: villa/apartment/hotel/clinic/office/restaurant/school/hospital all build through the
  local pipeline with **zero** `racks/lanes/docks/stations` and no industrial `role` injected (33/33).
- EXECUTED: generic villa JSON passes `validate_building` with **0 industrial-type issues**, `autofix`
  runs as `industrial=False`, and `compile_building` emits a valid glTF with WALL/DOOR/FURN and
  **no** rack/dock/lane geometry.
- STATIC: `SCHEMA_BRIEF` and the `objects` type list are domain-neutral.

## C. Industrial-specific extensions identified (keep — do not remove)
- **Schema:** `SCHEMA_INDUSTRIAL` (role/racks/lanes/stations/docks) — `acs_understand.py` 71–99.
- **Knowledge:** `KNOWLEDGE_WAREHOUSE`, warehouse persona/tail — `system_prompt` 296–302.
- **Validation:** `IND_AISLE`, aisle/rack/dock/safety rules — `acs_validate.py` 21, 127–214.
- **Layout:** industrial no-pack branch + open-zone lighting/sprinkler grid — `acs_layout.py` 154–174, 245–251.
- **Compiler:** `build_racks/build_lanes/build_stations/build_docks`, `RACK_DEF`, `LANE_MAT`,
  `ROLE_COLOR`, painted-zone walls — `acs_compiler.py`. All invoked **only** when the room has those fields.
- **FE local generator:** `warehouseFromText`, `ZONE_LIB`, `warehouseModel` — used **only** when
  `detectTypeJS`/picker = warehouse.
All EXECUTED-verified to activate **only** with industrial type/fields.

## D. Industrial leakage into generic logic — **mostly NONE; one PARITY GAP**
- **Core leakage into non-industrial buildings: NONE (PASS).** Verified by execution (B).
- **D-1 (PARTIAL / FAIL for offline tool):** the **offline** `acs_compiler.py` `build_room`
  (525–622) renders walls/doors/windows/points/furniture/racks/lanes/stations/docks but **does not
  implement the generic `room.objects` system** (no `build_objects`). So
  `python3 acs_compiler.py building.json out.gltf` **silently drops** workers/AMR/forklift/people/
  furniture-as-objects — re-introducing the very "silent object drop" fixed in the live app.
  - This is **not** industrial-into-core leakage; it's a **generic-capability parity gap** between
    the two compilers. The **live app + live GLB export** use the **frontend** compiler
    (`buildObjects`, `index.html:861`) and are unaffected — EXECUTED-confirmed objects render in the
    frontend model; the offline CLI is the only affected path. Evidence: `grep objects acs_compiler.py` → none.

## E. Building types handled by the existing DATA pipeline (EXECUTED)
| Type | Detected as | Industrial fields injected? | Result |
|---|---|---|---|
| Villa | residential (generic) | none | **PASS** |
| Apartment building | residential | none | **PASS** |
| Hotel | residential | none | **PASS** |
| Clinic | residential | none | **PASS** |
| Office | residential¹ | none | **PASS** |
| Restaurant | residential | none | **PASS** |
| School | residential | none | **PASS** |
| Hospital | residential | none | **PASS** |
| Warehouse | warehouse | only requested zones/objects | **PASS** |
| Factory | warehouse | only requested | **PASS** |

¹ The **frontend** `detectTypeJS` is binary (warehouse/residential); the **backend** `detect_type`
adds `office`/`retail` (4 types). Either way, non-industrial → the **generic** architectural schema.
AI-path shaping for these prompts is **NOT VERIFIED** (LLM not runnable here); schema/prompt are
STATIC-confirmed generic.

## F. Missing generic capabilities (Phase 2 — not defects, gaps)
1. **Type-specific programs absent.** Hotel/hospital/school/clinic/office/restaurant all collapse to
   one generic architectural schema; there is no per-type space program (e.g., hotel guestroom module,
   hospital OR/ward rules). `detect_type` 255–289 + `system_prompt` 292–315. **PARTIAL.**
2. **Data model is single-building, not PROJECT→SITE→multi-BUILDING.** Root is `site+levels+floors+rooms`
   (`SCHEMA_BRIEF` 25–34). No `PROJECT`/multi-`BUILDING`/`campus` container. **PARTIAL** (see G/H).
3. **No explicit STRUCTURAL / MEP / FIRE layers or RELATIONSHIPS graph.** MEP/fire are `points[]`
   tags (outlet/light/ac/smoke/sprinkler/exit); structural = generic `objects` (column) with no grid;
   no room-connectivity/relationship graph. **PARTIAL.**
4. **Offline compiler object parity (D-1).** **FAIL (offline only).**
5. **FE type detector binary** vs backend 4-type (E¹). **PARTIAL.**

## G. Exact files/functions responsible
- Type detection: `acs_understand.py:detect_type` (255–289); `public/index.html:detectTypeJS`.
- Generic schema: `acs_understand.py:SCHEMA_BRIEF` (25–65), `system_prompt` (292–315).
- Industrial schema/knowledge: `SCHEMA_INDUSTRIAL` (71–99), `KNOWLEDGE_WAREHOUSE`.
- Generic layout/validation: `acs_layout.py:autofix/ensure_essentials`; `acs_validate.py:validate_building`.
- Industrial gates (identical predicate): `acs_understand.py:293`, `acs_layout.py:231`,
  `acs_validate.py:60`, `acs_compiler.py:644`.
- Generic object model: `SCHEMA_BRIEF` objects (46–62); FE `OBJ_LIB/OBJ_AR` (830–871),
  `buildObjects` (1016); local extractor `objectsFromText` (Phase-1 addition).
- **Parity gap (D-1):** `acs_compiler.py:build_room` (525–622) — missing `objects` handling.

## H. Recommended architecture for Phase 2 (no work started)
1. **Formalize CORE + PROGRAMS.** Keep the current generic engine as CORE. Add a
   `building_type` registry where each type (residential, hotel, healthcare, education, office,
   retail, industrial, parking, mixed-use…) contributes an **optional** *space program* + rules,
   loaded the same way `SCHEMA_INDUSTRIAL` already is (append-if-selected). Industrial becomes
   *one* program among many — no privileged status.
2. **Generalize the data model** toward `PROJECT → SITE → BUILDING(s) → FLOOR → SPACE → elements`,
   keeping today's building JSON as the `BUILDING` node so it stays backward-compatible. Industrial
   fields (racks/lanes/docks) remain optional `SPACE` extensions, never core.
3. **Promote element layers:** explicit `structural`, `mep`, `fire_safety`, `relationships`
   (room-connectivity graph) as optional typed layers — enabling evacuation/BOQ later without
   reworking core.
4. **Close D-1 parity** (small, can be Phase-1 follow-up **if you authorize**): port the frontend
   `buildObjects` generic-object rendering into `acs_compiler.py` so the offline glTF CLI stops
   dropping people/vehicles/equipment. Until then, treat `acs_compiler.py` as **industrial/legacy
   export only** and document that the live GLB export (frontend) is authoritative.
5. **Unify type detection** (single source of truth) so FE and backend agree and expose the full
   type set.

---

### Audit verdict summary
| Audit | Verdict |
|---|---|
| 1 — Core vs specialized | **PASS** — core generic + gated industrial extension |
| 2 — 10 building types (DATA) | **PASS** (local pipeline, EXECUTED); AI path **NOT VERIFIED** |
| 3 — Cross-domain negative | **PASS** — villa/hotel/clinic get no industrial objects/fields |
| 4 — Industrial isolation | **PASS** — single gated predicate; EXECUTED |
| 5 — Generic object model | **PASS** — objects are generic types, context-driven |
| 6 — Data model w/o industrial schema | **PASS** for "not required"; **PARTIAL** for full PROJECT→TWIN hierarchy |
| D-1 — Offline compiler object parity | **FAIL (offline CLI only)** — live path unaffected |

No code was modified. `claude-sonnet-5` unchanged. Phase 2 not started.
