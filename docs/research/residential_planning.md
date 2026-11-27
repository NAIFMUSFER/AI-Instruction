# Residential planning: research, audit and the rules ACS now applies

Status: research note for the residential planner (`acs_residential_generation`,
`acs_floor_program`, `acs_plot_rules`, `acs_brief_reader`) and the checks the
plan must pass (`acs_validate`, `acs_residential_access`, `acs_plan_review`).
Written 2026-11-27 after the owner's corner-duplex brief
(`tests/remediation/fixtures/brief_reader/corner_duplex_brief.txt`) ended with
seven blocking findings.

Nothing here is a compliance certificate. ACS plans concepts. Every number
below is either a cited source, the documented basis of the Saudi code, or a
labelled ACS planning assumption. A licensed engineer and the municipality
decide the real design.

How the sources were read: this session could search the web but could not
open pages directly (the network blocked `momah.gov.sa`, `aleqt.com` and
other hosts). The figures below come from the search results' excerpts of the
cited pages. The setback, coverage and parking defaults were read from the
MOMAH 2024 PDF on 2026-11-26 (`docs/architecture/plot-rules.md`). The SBC 1101
and SBC 201 texts were not read. Their stated basis is the ICC 2015
International Codes, so the IRC and IBC figures are given as that basis, not
as the Saudi text.

## 1. The live failure

The owner's brief: a 24 × 30 m corner plot in Riyadh (streets north and
east). The building block is about 16 × 18 m in the north-west, with
setbacks of 6 m north, 6 m south, 2.5 m west and 5.5 m east. The ground and
first floors are one duplex around a garden and pool. The second floor is a
separate 3-bedroom flat with its own entrance, stair and lift.

The saved layout is `fixtures/floor_program/corner_duplex_layout.unrepaired`.
After the free overlap trim, its V1 still had seven blocking findings:

| Finding | Cause in the layout |
|---|---|
| 5 × «معلّق» (floating) | First floor: the parents' bedroom (46% supported), two children's rooms (17% and 3%) and the shared bathroom (0%) stand over open ground. The ground floor left x 14.2–18.5, z 14–24 and the strip south of the living room unbuilt. Second floor: the master bathroom (0%) stands over a first-floor void. |
| Pool bathroom unreachable | Its only door opens to the yard, as the brief asks («مدخل من الحوش»). The access check accepted yard-only rooms only for storage, equipment and pump rooms of ≤ 6 m², and never for a single dwelling. |
| Majlis 6.87 m from the family entrance | The brief brings guests in from the east («يدخل ضيف المجلس من الشرق»). For a flat, the zoning check counted only doors onto common rooms as entrances, so a guest door was never an entrance. The openings prompt never asked for one. |

Advisories: the shared bathroom was 1.7 m wide against a 3 × 2.6 m target.
Wet rooms were not stacked. The dressing room was 18% under its target: the
free trim had taken 0.6 m off it.

Root causes:

1. The workspace planner was never told that storeys stack. The legacy
   single-call prompt had that rule (`RESIDENTIAL_MASSING_RULE`). The
   workspace planning policy (`PLANNING_SYSTEM`) replaced it and dropped it.
   The chunk prompt even says «لا تعامل غرف الدور الآخر كعوائق» without saying
   that the storey below is the support.
2. The plot prompt told the planner to leave leftover envelope as open space
   («اترك الباقي فراغًا خارجيًا»). The upper programs were bigger than the
   ground program, and nothing said the upper floors must stay over the
   ground's built area.
3. The layout stage measured floating rooms only as repair "advisories". They
   rode along on a repair call but never caused one. Once the free trim had
   cleared the only hard finding, nothing looked at them before the paid
   openings stage. The openings stage cannot move rooms.

## 2. Research summary

### 2.1 Saudi house and duplex planning: zoning, privacy, entrances

- The majlis (guest reception) sits next to the entrance, so guests reach it
  without crossing family space. Traditionally it had its own entrance. The
  men's and women's reception areas had separate entrances.
  [Al-Monitor/AFP 2022](https://www.al-monitor.com/originals/2022/07/new-architectural-openness-remaking-saudi-streets).
- Privacy is the core cultural requirement of the Riyadh villa, and the
  research finds the villa type often fails it.
  [Almehrej 2015, Northumbria](https://researchportal.northumbria.ac.uk/en/studentTheses/a-design-guide-for-contemporary-saudi-arabian-homes-in-riyadh-4/);
  [AlKhateeb 2015, Bournemouth](https://eprints.bournemouth.ac.uk/25016/1/AlKhateeb%2C%20Maryam_Ph.D._2015.pdf).
- Zones: public or guest (majlis, guest WC, dining for guests), semi-private
  (family living, kitchen), and private (bedrooms, usually upstairs). Service
  (kitchen service door, maid and driver rooms) is reached from the side or
  service yard.
- The Riyadh «فيلا دوبلكس مع شقة» typology is common in listings. A duplex
  over ground and first floor has an internal stair. The flat above has its
  own entrance, its own electricity and water meters and often its own
  parking. Examples: [Bayut, Al-Janadriyah](https://www.bayut.sa/%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1/%D8%AA%D9%81%D8%A7%D8%B5%D9%8A%D9%84-87993656.html)
  and [Bayut, Al-Tuwaiq](https://www.bayut.sa/%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1/%D8%AA%D9%81%D8%A7%D8%B5%D9%8A%D9%84-87753457.html).
  These are listings, not standards.
- Domestic-worker rooms (2024 rules, from a secondary source): at least
  6.5 m² and 2.1 m wide, with the bathroom extra to that area. A driver's
  room may open onto the outer wall with a door at least 0.8 m wide.
  [Raghdan 2025](https://raghdan.sa/ar/news/humanizing-domestic-worker-housing-2025-legal-standards-and-humane-design-for-maid-and-driver-rooms-in-saudi-villas/).
- ACS assumption, unchanged: the majlis door is within 5 m of the entrance
  door that serves it, and no bedroom door is within 3 m of an entrance door
  (`acs_plot_rules.ENTRY_MAJLIS_MAX_M`, `ENTRY_BEDROOM_MIN_M`).

### 2.2 Plot rules (MOMAH 2024, Riyadh)

The setbacks, coverage and parking defaults are in
`docs/architecture/plot-rules.md`. Source:
[MOMAH «اشتراطات إنشاء المباني السكنية» (July 2024)](https://momah.gov.sa/sites/default/files/2024-07/ashtratat%20a%27nsha%20almbany%20alsknyt%20almnshwrt%20%60ly%20mwq%60%20alwzart%20.pdf).
Additional points from the Riyadh municipality's villa audit form
([نموذج تدقيق الفلل](https://cts.alriyadh.gov.sa/_layouts/RM_Pages/FormsDownload/BlS_Project_audit_Form1.doc)):

- A first-floor projection over the front (street) setback may be at most
  1.20 m.
- No projections or balconies toward a neighbour inside the minimum setback.
- Balcony parapets on the neighbour side are 1.80 m high.
- Roof annex: at most 50% of the first floor in the Amanah form and in
  [Riyadh guide T3.1](https://eservices.alriyadh.gov.sa/Documents/BuildingCodes/T3.1%20v1.0.pdf).
  A later ministry amendment reports 70%
  ([Ajel](https://ajel.sa/local/7is8h2riji)). Not used by ACS yet.

### 2.3 Structure: upper floors over a supported footprint

- Load paths should run straight down. A column that stops on a beam (a
  transfer column) is a special, costlier element. It is typical of irregular
  residential plans and needs engineering design.
  [Untirta, transfer columns in a 3-storey house](https://jurnal.untirta.ac.id/index.php/jft/article/download/32287/14638).
- Cantilevers: ACI 318 Table 7.3.1.1 sets the minimum one-way slab thickness
  at l/10 for a cantilever, against l/20 simply supported, l/24 with one end
  continuous and l/28 with both ends continuous. A 1.2 m cantilever therefore
  needs about 0.12 m before deflection checks, and deeper with a wall load on
  its tip.
  [Tekla, ACI 318-19 one-way slab example](https://support.tekla.com/doc/tekla-tedds/2025/ver_verification_example_rc_one_way_slab_design_aci).
- Saudi villas allow at most a 1.2 m first-floor projection, and only over
  the street setback (§2.2).
- Rule adopted: an upper room stands over rooms of the storey below, or over
  a covered porch carried on columns on the ground storey. A projection of up
  to 1.2 m is planned only when the brief asks for a cantilever. The
  deterministic check is the review's own measure, `acs_validate` check 3: a
  room counts as floating below 50% support, once the storey below covers at
  least 60% of the one above. So the layout stage never asks for more than
  the review blocks.

### 2.4 Wet stacks

- Group bathrooms, toilets and laundries together. Put upper-floor wet areas
  above ground-floor wet areas. Run the soil stack straight, with no offsets.
  [BRANZ, designing a domestic plumbing system](https://www.branz.co.nz/design-build/articles/designing-a-domestic-plumbing-system).
- Soil, waste and vent lines must line up through every level, and a change
  on one floor breaks the stack.
  [Construction Placements, plumbing coordination](https://www.constructionplacements.com/plumbing-coordination-challenges-high-rise-construction).
- ACS check (advisory): `PROGRAM_WET_STACK` passes when an upper wet room
  overlaps a wet room below by at least 0.5 m² (`acs_floor_program.WET_STACK_MIN_M2`).

### 2.5 Stair and lift cores

| Item | Value | Source |
|---|---|---|
| Dwelling stair clear width | ≥ 914 mm (36 in) | IRC R311.7.1 ([2018 IRC stair guide](https://timnath.org/wp-content/uploads/2022/03/2018-RESIDENTIAL-STAIR-GUIDE.pdf)) |
| Riser / tread (dwelling) | ≤ 196 mm / ≥ 254 mm | IRC R311.7.5 (same) |
| Headroom | ≥ 2032 mm (6 ft 8 in) | IRC R311.7.2 (same) |
| Landing depth | ≥ 914 mm in the direction of travel | IRC R311.7.6 (same) |
| Building stair width | ≥ 1118 mm (44 in); 914 mm when the storey's occupant load is < 50 | IBC 1011.2 ([ICC, 2021 IBC means of egress](https://iccsafe.org/wp-content/uploads/2021-IBC-Means-of-Egress.pdf)) |
| 8-person 630 kg lift car | 1100 × 1400 mm; shaft about 1.5–1.6 × 1.65–2.2 m by maker | EN 81-20 cars ([TK Elevator](https://digital.brochure.tkelevator.com/tke/brochure/eox1b/shaft-dimensions-8)) |
| SBC basis | SBC 2018 is based on the 2015 International Codes; SBC 201 is based on IBC 2015 | [ICC Saudi Arabia](https://iccsafe.org/?p=240998), [MLIT Japan](https://www.mlit.go.jp/common/001404290.pdf) |

The ACS core (`acs_floor_program`) is a stair of 2.6 × 5.0 m and a lift of
2.0 × 2.2 m. Two 1.2 m flights with a 0.2 m gap make 2.6 m. Nine treads of
0.28 m (2.52 m) plus two 1.2 m landings make 4.92 m. With 0.17 m risers, that
covers a 3.2 m storey. This fits the IBC building stair (≥ 1.118 m, riser
≤ 178 mm, tread ≥ 279 mm), and the lift shaft is on the generous side. Cores
stay identical on every floor.

### 2.6 Room, corridor, door and window dimensions

| Item | Value | Source |
|---|---|---|
| Habitable room | ≥ 6.5 m² (70 sq ft), ≥ 2.13 m (7 ft) in any plan dimension | IRC R304 ([Seattle](https://www.seattle.gov/documents/Departments/SDCI/Codes/2015SRC3041HabitableRoomSize.pdf)) |
| Single bedroom | ≥ 7.5 m², ≥ 2.15 m wide | UK NDSS ([gov.uk](https://www.gov.uk/government/publications/technical-housing-standards-nationally-described-space-standard/technical-housing-standards-nationally-described-space-standard)) |
| Double bedroom | ≥ 11.5 m²; one ≥ 2.75 m wide, others ≥ 2.55 m | UK NDSS (same) |
| Maid / driver room | ≥ 6.5 m², ≥ 2.1 m wide | Saudi 2024 rules via [Raghdan](https://raghdan.sa/ar/news/humanizing-domestic-worker-housing-2025-legal-standards-and-humane-design-for-maid-and-driver-rooms-in-saudi-villas/) (secondary) |
| Hallway | ≥ 914 mm (3 ft) | IRC R311.6 ([Montana DLI, 2021 IRC means of egress](https://bsd.dli.mt.gov/_docs/Training/2021-IRC-Means-of-Egress-Thursday-AM.pdf)) |
| Passage conventions | single file about 600 mm; two people passing 1100–1200 mm; beside a bed 700–900 mm | Neufert / Panero, quoted by [Studio Matrx](https://www.studiomatrx.org/students/space-planning-ergonomics/space-standards-and-clearances) |
| Egress door | 813 mm clear (32 in) × 1981 mm (78 in) | IRC R311.2 (Montana DLI, above) |
| Water closet / lavatory | ≥ 533 mm (21 in) clear in front | IRC R307 ([ICC sample](https://shop.iccsafe.org/media/wysiwyg/material/7100S15-Sample.pdf)) |
| Natural light / ventilation | glazing ≥ 8% of floor area; openable ≥ 4% | IRC R303.1 ([Boise](https://cityofboise.org/media/3923/433-irc-code-section-r303-light-ventilation.pdf)) |

Time-Saver Standards: the search reached only the tables of contents
(bedrooms p. 80, bathrooms p. 87). None of its figures are used.

### 2.7 Minimums ACS now uses

ACS uses two tiers on purpose: a comfortable planning target, and an
absolute floor below which the room does not work.

| Role | Planning target (prompt), clear short side | Absolute floor (advisory check) | Basis of the floor |
|---|---|---|---|
| bedroom | 2.7 m | 2.1 m | IRC 2.13 m habitable; NDSS single 2.15 m |
| maid / driver room | 2.1 m | 2.1 m | Saudi 2024 (secondary) |
| living, majlis, dining | 3.0 m | 2.1 m | IRC habitable |
| office | — | 2.1 m | IRC habitable |
| kitchen | 2.1 m | 1.6 m | 0.6 m counter + 1.07 m work aisle (NKBA convention) |
| bathroom | 1.5 m (WC alone 1.2 m) | 0.9 m | IRC R307 WC space 0.76 m plus walls |
| corridor | 1.2 m | 0.9 m | IRC R311.6 0.914 m |
| entrance / lobby | 1.5 m | 0.9 m | IRC hallway |
| laundry, dressing, pantry, store | 1.2 m | — | ACS assumption |
| doors (openings prompt) | entrance 1.0–1.2 m, rooms 0.9 m, bathrooms 0.8 m | — | IRC 0.813 m egress clear; common practice |
| windows (openings prompt) | about 1/8 of floor area, sill 0.9 m (bathroom 1.6 m) | — | IRC 8% light |

A size the brief states always wins over a planning target.

## 3. Audit of the instructions before this change

| # | Where | Finding | Kind |
|---|---|---|---|
| A1 | `PLANNING_SYSTEM` (workspace plan policy) | No rule that upper rooms stand on the storey below. The legacy `RESIDENTIAL_MASSING_RULE` had one, but the workspace policy replaced that prompt. | missing |
| A2 | `acs_understand.PLAN_CHUNK_MSG` | «لا تعامل غرف الدور الآخر كعوائق» with no counterpart saying the storey below is the support. The planner saw the ground rooms in `planned_rooms` but had no reason to stay over them. | ambiguous |
| A3 | `acs_plot_rules.prompt_text` | «اترك الباقي فراغًا خارجيًا»: when the upper programs are larger than the ground program, leftover ground envelope under the upper rooms. | contradictory |
| A4 | `prepare_layout` | Floating rooms were only `context.advisories` on a repair call. They never bought a call or reached the openings stage as a fault. The free trim then removed the only hard finding (live). | missing check |
| A5 | `ADVISORY_REPAIR` | "less than half of its area over built space": no target, no option other than moving the room. | ambiguous |
| A6 | `F.PLANNING_ADDENDUM` + `F.prompt_text` | Wet stacking was stated twice (system and prompt) and only for confirmed floor programs. Villas and apartment buildings without a program never got it. | redundant and missing |
| A7 | `OPENINGS_SYSTEM` + `P.OPENINGS_ADDENDUM` | "Keep each … entrance door next to the majlis": wrong when guests have their own door. Nothing about yard-only rooms. | ambiguous |
| A8 | `acs_plot_rules._zoning` | For a flat, only doors onto common rooms counted as entrances, so a ground guest door into the majlis or its guest lobby never served the majlis (live). | check gap |
| A9 | `acs_residential_access.issues` | A small yard room was accepted only for storage, equipment and pump roles, never for a pool bathroom. A single dwelling had no yard exemption at all. | check gap |
| A10 | every planning prompt | No minimum width by role: only bedroom areas (12–20 m²) for villas and the brief's own targets. `MIN_CORRIDOR_W = 1.2` in `acs_validate` is unused. `_trim_overlaps` could leave a bedroom at 1.2 m. | missing |
| A11 | `_trim_overlaps` | The trimmed room lost area even when free space lay on its other side (the dressing room went 18% under). | quality |
| A12 | `acs_brief_reader.SYSTEM` | Sound for this failure: it already says that a yard-only room belongs to its floor's unit. Gaps: a duplex spanning two floors cannot be one unit, and the brief's second, private stair (ground to first only) has no field. The per-floor planner receives room notes only through the full brief text. | known limits (not changed) |
| A13 | `SINGLE_DWELLING_PLANNING` vs `VILLA_ROOM_PROGRAM` | Each repeats the other's rules: about 0.8 k characters sent twice on villa calls, once in English and once in Arabic. Left as is, because tests pin both. | redundant (not changed) |

## 4. What changed

### Instructions (paid on every call: kept short)

- `PLANNING_SYSTEM` (outline, plan chunks, repair) gains three short blocks:
  - **STACKING**: rooms over rooms of the storey below, using `context.below`;
    a covered porch on the ground storey instead of a void; a cantilever of at
    most 1.2 m, and only when asked; wet rooms over wet rooms.
  - **ZONING**: the majlis and guest WC within 5 m of the entrance that serves
    them, or with their own guest door; yard rooms on the ground storey,
    against the yard.
  - **Clear short sides by role**: the planning targets in §2.7.
- `STACK_REPAIR` replaces `ADVISORY_REPAIR`. It is sent only when a room
  floats, and it states the two fixes: move the room over the storey below,
  or add a ground porch.
- `OPENINGS_SYSTEM` gains: yard rooms open to the yard; a guest door into the
  majlis or its guest lobby; door widths; window size; a porch needs no door.
- `P.OPENINGS_ADDENDUM` drops its majlis sentence (now in `OPENINGS_SYSTEM`).
  `F.PLANNING_ADDENDUM` and `F.prompt_text` drop the wet-stack sentence (now
  stated once in `PLANNING_SYSTEM`).
- `P.prompt_text`: leftover envelope stays open, but «لا تعلوه غرفة في دور
  أعلى». The privacy line allows a guest door of the majlis's own.
- `REPAIR_SYSTEM`: `porch` is added to the role list.

### Deterministic checks and free fixes (no provider call)

| Step | Where | What |
|---|---|---|
| Floating-room finding | `prepare_layout.findings` | `UNSUPPORTED_UPPER_ROOM` uses the review's own measure. It is a soft finding: blocking in the review but never a failed job. It buys at most one repair, and only when the budget also covers the openings stage. |
| Covered porch | `_support_porches` | A first-storey room over open ground gets «رواق مظلل» under it on the ground storey (role `porch`, `walls: "none"`, `covered: true`; the 3D context places its corner columns). This only happens when the ground template is used by the ground storey alone, the pieces are at least 1.0 m wide and 1.5 m², they overlap nothing, and the result adds no finding (envelope, access, program). The fix is disclosed in `meta.assumptions`. |
| Storey below for the planner | `acs_understand._plan_spatial_context` | Upper-storey plan chunks of a residential building get `below = {template, extent, open}`. `open` lists the unbuilt rectangles inside the storey below, largest first, at most 12. It is given only once every zone of that storey has been planned. |
| Area-keeping trim | `_regrow` | After a sliver trim, the room grows back to its area along its other axis, into free space on its floor. The result is kept only if it adds no finding. Live: the dressing room goes back to 8.84 m². |
| Role-aware trim | `_trim_overlaps` | A trim never leaves a room below `MIN_SHORT_SIDE_M` for its role. |
| Yard rooms | `acs_residential_access` | On the ground storey, a bathroom of ≤ 6 m² whose door opens to the yard is reached from outside, for flats and villas alike. So is a wall-less porch with an exterior side. A bedroom, or a larger room, opening only to the yard is still disconnected. |
| Guest entrance | `acs_plot_rules._entries` | On the ground storey, a flat's entrance, guest lobby or majlis door to the exterior is an entrance of that flat. A kitchen service door is not. |
| Free guest door | `_guest_doors` (after openings) | The majlis gets an external door in its own wall when it is more than 5 m from every entrance and the brief asks for guest privacy (blocking) or a guest entrance («يدخل ضيف المجلس من الشرق»). The side the brief names comes first, then street sides. The door never goes on a neighbour's plot line or across an existing opening. It is kept only if it clears the finding and adds none. |
| Width floor | `acs_residential_access.narrow_rooms` | `ROOM_TOO_NARROW` is an advisory in the verifier's review notes. It never blocks. |
| Porch is outdoors | `acs_validate` | A wall-less porch needs no door and no light point. |

### Replay of the live layout

The trim, the regrow and the porches are free. Four of the five floating
rooms are carried on ground porches. The dressing room is back at 8.84 m².
One repair call carries the last finding (the second-floor master bathroom
over a first-floor void). A stub repair that puts a store under that
bathroom ends with no «معلّق» in the review
(`tests/remediation/test_upper_floor_support.py`).

### Prompt size

Measured on the confirmed-floor-program generation in
`tests/remediation/test_floor_program.py`: three plan chunks, one repair and
three openings calls. Tokens are estimated at 4 ASCII characters or
2.5 Arabic characters per token; no tokenizer was available offline.

| Call | Before (chars / ≈ tokens) | After | Change |
|---|---|---|---|
| plan chunk (system + prompt) | 21 135 / 6 126 | 22 072 / 6 361 | +937 chars, ≈ +235 tokens (+3.8%) |
| repair, when a room floats | 23 276 / 6 514 | 24 421 / 6 817 | +1 145 chars, ≈ +303 tokens (+4.7%; 260 chars of it only when a room floats) |
| openings | 10 523 / 3 112 | 10 826 / 3 188 | +303 chars, ≈ +76 tokens (+2.4%) |

Constants: `PLANNING_SYSTEM` 1 446 → 2 389; `OPENINGS_SYSTEM` 1 720 → 2 094;
`F.PLANNING_ADDENDUM` 656 → 536; `P.OPENINGS_ADDENDUM` 682 → 611. A typical
three-floor job pays about 0.9 k more input tokens. One avoided repair call,
which may think its whole 16 000-token output cap away, costs far more.

## 5. Open risks

- **Porches change the plan.** A ground porch under a first-floor room is a
  design decision: columns in the garden side, a covered terrace. It is
  disclosed and editable, but the owner did not draw it.
- **Floating upper storeys above the first.** A second-floor room over a
  first-floor void still needs the paid repair. A porch there would itself
  float.
- **The 50% support threshold** is the review's existing measure. The prompt
  asks for full support, so plans between 50% and 100% pass.
- **The width floors are advisory.** The planning targets are ACS
  assumptions, not the SBC text.
- **The private duplex stair** (ground to first only) cannot be modelled:
  cores must be identical on every floor. The duplex then reaches its upper
  floor through the common stair landing, as the brief also allows.
- **Unit ids per floor.** The floor-program manifest numbers flats per floor,
  so the duplex and the second-floor flat both get `apartment_1`.
- **Guest-entrance wording.** The detection is regex based. A brief that
  phrases it differently gets no free door; the prompt still asks the planner
  for one.
- **The planner may still ignore the rules.** The free fixes and the bounded
  repair are the safety net, and the review still blocks what remains.
