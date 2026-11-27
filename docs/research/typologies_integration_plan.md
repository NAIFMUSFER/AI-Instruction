# Typology packs: integration plan

Status: proposal for the owner's approval. The five packs
(`acs_typology_office.py`, `acs_typology_retail.py`, `acs_typology_school.py`,
`acs_typology_mosque.py`, `acs_typology_hotel.py`, shared
`acs_typology_common.py`) are committed but **not imported by any live module**
(`tests/remediation/test_typology_packs.py::Instructions.test_packs_are_not_wired_into_the_live_path`
keeps it so until this plan is approved). Research per type:
`docs/research/<type>_planning.md`.

## What each pack provides

| Item | Use in the live path |
|---|---|
| `ROOM_PROGRAM` (Arabic) | appended to the generation prompt, like `acs_residential_generation.ROOM_PROGRAM` |
| `program_text(options)` (Arabic, computed) | appended after it: computed areas, WC counts, exits, the mosque's qibla wall |
| `PLANNING_SYSTEM` | the outline / plan_chunk policy (`acs_workspace_progress.planning_policy`) |
| `REPAIR_SYSTEM` | appended to `PLANNING_SYSTEM` for the bounded layout repair call; contract `{"floors":{template:{"rooms":[…]}}}` |
| `OPENINGS_SYSTEM` | the detail-stage system text; contract `{"rooms":[{"id","doors","windows","points"}]}` |
| `ROOM_TABLE`, `LOADS`, `SOURCES` | data for the checks and for the UI's role labels |
| `check(building, options)` | `(blocking, advisory)` findings, each `{code, severity, basis, message (Arabic), fix (English), source, room_ref?}` |

Instruction sizes (characters, stated in each module's `INSTRUCTION_SIZES` and
held by the tests; residential for comparison: planning 1446, openings 1720,
repair 894, room program 647):

| Pack | ROOM_PROGRAM | PLANNING | OPENINGS | REPAIR |
|---|---|---|---|---|
| office | 569 | 1649 | 1618 | 966 |
| retail / mixed use | 638 | 1767 | 1644 | 1123 |
| school | 721 | 1915 | 1732 | 1081 |
| mosque | 772 | 1708 | 1770 | 1027 |
| hotel | 602 | 1603 | 1585 | 1034 |

Bounds: room program ≤ 900, planning ≤ 2400, openings ≤ 2400, repair ≤ 1600,
planning + repair ≤ 4000, `program_text` ≤ 900 for large programs.

## Recommendation: ship the office pack first

1. **Closest to what already works.** An office building is the apartment
   pipeline without units: repeated typical floors, a stacked stair and lift
   core, one common corridor. `prepare_layout` / `detail` in
   `acs_residential_generation.py` need the fewest changes to drive it.
2. **The rules are the firmest.** Every hard office check rests on numbers read
   verbatim from IBC 2015 (the SBC 201 base) and IPC 2015; no Ministry manual,
   municipal variant, gender rule or survey input is needed.
3. **ACS already half-knows it.** `acs_programs.json` detects office briefs
   («مبنى مكاتب», «برج مكاتب», «مقر إداري»), `brief-program.mjs` already reads
   «N مكاتب» as `room_count` role `office`, and `acs_compiler.ADMIN_ROLES`
   treats `office` and `meeting` as walled rooms.
4. **Failures are measurable and explainable**: exits, toilets, daylight depth,
   desk density.

Then, in order: **mixed use** (large Saudi demand; reuses the residential
pipeline for the flats and the office pack for office floors, but needs the
separate-entrance rules and a detection fix, below); **mosque** (simple program,
but needs a new plot-north input and careful qibla wording in the UI); **school**
(needs the Ministry / Tatweer manuals before its numbers are final); **hotel**
(needs the Ministry of Tourism per-star area table).

## Steps (office first; the same steps repeat per typology)

### 1. A registry of packs

New `acs_typology_registry.py`:

```python
PACKS = {'office': 'acs_typology_office', 'mixed_use': 'acs_typology_retail',
         'commercial': 'acs_typology_retail', 'retail': 'acs_typology_retail',
         'school': 'acs_typology_school', 'mosque': 'acs_typology_mosque',
         'hotel': 'acs_typology_hotel'}
ENABLED = {'office'}            # widen one typology at a time
def pack_for(program_id): ...   # importlib, only for ENABLED ids
```

Remove the "not wired" guard test for the enabled pack only (keep it for the
others), and add the registry to `Dockerfile` (`COPY acs_typology_*.py ./`).

### 2. Detection and the explicit type

- `acs_workspace_service.generation_command`: accept an optional `type` from
  the form (one of `residential`, `warehouse` and the enabled ids) and pass it to
  `U.detect_type(brief, explicit=type)` in `generate_plan_candidate`. Today the
  type is inferred from the brief alone plus the form's appended line
  («نوع المشروع: …», `brief-program.mjs` line 373).
- `acs_programs.json` + its mirror `ACS_PROGRAMS` in
  `public/app/render/scene.js` (drift test `tests/phase1/test_phase2.js`):
  add a `mosque` program (strong: «مسجد», «جامع», «mosque»; weak: «مصلى»,
  «محراب», «مئذنة», «ميضأة»), and for mixed use add Saudi phrases
  («عمارة تجارية», «تجارية سكنية», «محلات وشقق», «تجاري سكني») — today
  «عمارة» scores 3 for `apartment` and «تجاري» only 1, so a mixed-use brief is
  routed to residential. `tests/remediation/test_plan_typology_lifecycle.py`
  covers a new registered program automatically.

### 3. Generation (`acs_workspace_service.generate_plan_candidate`)

Where `policy = PLANNING_SYSTEM if residential else WAREHOUSE_PLANNING_SYSTEM if warehouse else None`
(about line 381), add the pack branch:

```python
pack = pack_for(detected) if not residential and not warehouse else None
if pack:
    options = typology_options(requirements, command)      # step 5
    prompt += '\n' + pack.ROOM_PROGRAM + pack.program_text(options)
    policy = pack.PLANNING_SYSTEM
```

After `generate_candidate`, call a new `acs_typology_generation.py` that
mirrors `acs_residential_generation.prepare_layout` and `detail` but takes the
pack:

- **Layout findings**: `_structure` + `_geometry` (from `acs_plan_review`), then
  `pack.check(building_without_doors, options)`: errors are hard, advisories
  soft. Before openings the checks run in geometric mode (a shared wall of
  0.6 m is a potential door), which the tests prove clean on every compliant
  fixture.
- **Repair**: one call with `pack.PLANNING_SYSTEM + pack.REPAIR_SYSTEM`, context
  `{'building', 'requirements', 'brief', 'findings': [{code, room_ref, fix}]}`
  (the English `fix` field is written for this), a second only on strict
  progress within the budget — the residential rules, unchanged. Reuse
  `_trim_overlaps` for slivers.
- **Openings**: the residential `detail` loop with `system = pack.OPENINGS_SYSTEM`;
  its corrective pass uses `acs_validate.validate_building` plus
  `pack.check(building, options)` blocking findings with a `room_ref`.
- Stamp `meta.type = pack.TYPOLOGY` (read by `acs_validate.building_type` and
  `acs_plan_scorecard._typology`) and `meta.typology_options`.
- No deterministic fallback layout at first: a failed repair raises
  `PLAN_LAYOUT_INCOMPLETE` as today.

### 4. Review (`acs_plan_review.py`, after the villa block near line 905)

```python
pack = pack_for(meta.get('type')) if isinstance(meta, dict) else None
if pack and not geometry_issues:
    blocking, advice = pack.check(model, (meta.get('typology_options') or {}))
    if transcription: advice, blocking = [dict(b, severity='advisory') for b in blocking] + advice, []
    issues.extend(blocking); advisories += advice
    scopes['typology_program'] = 'FAIL' if blocking else 'PASS'
```

and include `pack` in the condition that publishes `result["advisories"]`.
Findings carry `basis` (`program`, `code`, `saudi_guide`, `practice`) and
`source`, so the review can show «مرجع: …» under each one.

### 5. Inputs: brief, requirements and form

- `acs_requirement_metrics.json` → regenerate
  `public/app/generated/requirement-metrics.mjs` with
  `tools/build_requirement_metrics.py`: add `occupant_count` (employees,
  students, worshippers), `class_size`, `women_occupant_count`; reuse
  `room_count` with roles `classroom`, `shop`, `guest_room`.
- `public/app/core/brief-program.mjs`: accept the new `input.type` values
  (line 288), add `PROGRAM_LIMITS` per type (office: side 200 m, levels 40;
  mixed use: as residential; school: levels 4; mosque: levels 2; hotel: levels
  40), role labels for the new roles, and patterns such as «N فصول»,
  «N محلات», «يتسع لـN مصلٍ», «N غرفة فندقية». The line «نوع المشروع: …»
  names the typology.
- `public/app/ui/connected-workspace.mjs` (the `cwType` select near line 595):
  add «مبنى مكاتب», «محلات / متعدد الاستخدامات», «مدرسة», «مسجد», «فندق», and
  per-type fields: employees; shops, upper use (offices/apartments) and street
  side; school gender (بنين / بنات / طفولة مبكرة), classrooms, class size;
  mosque men, women, district (سكني / تجاري), city, and **plot north
  deviation** (degrees, with a help text on true vs. grid vs. magnetic north);
  hotel rooms and class area or stars; sprinklers (غير محدد / نعم / لا).
  `brief-review.mjs` adds starters per type; `brief-reader.mjs` keeps smart
  reading residential-only (`acs_brief_reader.confirmed_program` line 712
  refuses other types) until a reader exists for them.
- `acs_plot_rules.py`: carry `north_deg` in the plot block and stamp it in
  `meta.qibla.plot_north_deg` for mosques; `streets` already exists and feeds
  the retail frontage check.

### 6. Viewer and compiler (optional, visual only)

`acs_compiler.ROLE_COLOR` tints for the new roles; non-industrial rooms already
get full walls. For mosques, a later `objects` kind such as `prayer_rows` with
the residual angle would draw the saff lines in 3D. `acs_validate` needs no
change: the compliant fixtures of all five packs are clean for it, and the
retail text forbids `unit`/`apt`/`flat` in shop ids (its generic-space rule).
`acs_design_research.research` accepts only residential and warehouse (line 45):
leave it, or add catalogues per type.

### 7. CI and release

- `.github/workflows/ci.yml`, job "python contract suites": add
  `tests/remediation/test_typology_packs.py`; also `tests/remediation/run_all.sh`.
- Before enabling a pack for users: three owner-approved paid briefs per
  typology through the live path, reviewed by an architect, recorded under
  `docs/audits/`.

## Open risks

- **SBC text not read.** Code numbers are the IBC 2015 / IPC 2015 base of SBC
  201 / SBC 701; Saudi amendments to a specific value would not show. Obtain the
  SBC 201 and SBC 701 tables and diff them with each pack's constants.
- **Saudi manuals not read**: Ministry of Education and Tatweer school
  standards, MoIA mosque standards, the Ministry of Tourism per-star table, and
  each Amanah's commercial rules. Those values are labelled `saudi_guide` or
  `practice` and are the first to update.
- **Rectangles only.** A prayer hall cannot rotate to the qibla; rows are marked
  at the residual angle (26° in Riyadh on a north-aligned plot). Curved or
  angled facades, atria and double-height spaces are outside the contract.
- **Approximations**: travel distance (passage points, no in-room travel for
  exit rooms), occupant loads (support area shared into gross factors), WC
  capacity by area. They are conservative but not code measurements; the
  findings say so.
- **Sprinklers unknown** by default: the sprinkler-dependent limits are
  advisories until the form states the system.
- **Prompt cost**: each pack adds about 1.6–1.9 k characters to every outline
  and plan_chunk call, as the residential policy does; no new call is added.
- **Detection**: until step 2 lands, «عمارة تجارية» briefs go to residential.
- **Research gaps**: Firecrawl credits ran out mid-research and direct page
  fetches are blocked in this session, so several Saudi figures come from search
  summaries (each research document says which).
