# Office building: planning research for the ACS instruction pack

Status: research for `acs_typology_office.py`; not wired into generation or
review (see `typologies_integration_plan.md`). Every number below is a planning
reference with its source and how it was checked. Nothing here is a code
compliance verdict, and the pack never says a layout complies.

## Which code applies in Saudi Arabia

- **SBC 201** (Saudi Building Code, general building) governs occupant load,
  exits, corridors, stairs and travel distance for offices (Group B). The
  2018 edition was adapted from **IBC 2015** by the Saudi Building Code National
  Committee [S1][S2]. ACS could not open the official SBC 201 text in this
  session (it is sold through sbc.gov.sa), so the pack uses the **IBC 2015**
  values, read verbatim from the ICC public text [S3], and labels them as the
  SBC 201 base. Where IBC 2018/2021 changed a value, both are shown.
- **SBC 701** (plumbing) is the IPC counterpart; fixture counts come from
  **IPC 2015 Table 403.1**, read verbatim [S4].
- **SBC 801** (fire) decides whether sprinklers are required. The pack does not
  decide that: sprinkler status is an input (`sprinklered`: true, false or
  unknown). Unknown uses the sprinklered limits but reports them as advisories.
- **SBC 1101** is the Saudi residential code for one- and two-family houses
  (R3) [S11]; it does not apply to offices.

## Occupant load

| Space | Factor | Basis | Source |
|---|---|---|---|
| Business areas (offices, reception, pantry) | 100 ft² gross = **9.29 m²/person** | gross | IBC 2015 T1004.1.2 [S3] |
| Same, IBC 2018/2021 | 150 ft² gross = 13.94 m²/person | gross | IBC 2021 T1004.5 [S5] |
| Concentrated business (call centres, trading floors) | 50 ft² gross = 4.65 m² | gross | IBC 2021 §1004.8 [S5] |
| Meeting / conference (tables and chairs) | 15 ft² net = **1.39 m²** | net | IBC 2015 T1004.1.2 [S3] |
| Prayer room (chairs only / standing) | 7 ft² net = 0.65 m² | net | IBC 2015 T1004.1.2 [S3] |
| Storage, server room | 300 ft² gross = 27.9 m² | gross | IBC 2015 T1004.1.2 [S3] |

The pack keeps the IBC 2015 factor (9.29 m²): it is the SBC 201 base and gives
the higher, safer load. Gross factors are applied to the room plus its share of
the storey's corridors, toilets and cores (`acs_typology_common.occupant_load`).

Design density is a different number from code load: the BCO guide gave
8–13 m² NIA per workspace in 2014 and 8–10 m² in 2019; its 2022 paper moved to
10–12 m² and treats 8 m² as an exceptional high density [S6]. The pack plans at
**10 m² per desk** and flags below 8 m² NIA per employee as an error, 8–10 m² as
an advisory.

## Room sizes (the pack's `ROOM_TABLE`)

| Role | Min area | Min width | Must touch | Exterior wall | Basis |
|---|---|---|---|---|---|
| lobby | 12 m² | 3.0 m | — | — | practice |
| reception | 9 m² | 2.4 m | lobby or corridor | — | Neufert [S7] |
| open_office | 30 m² | 4.8 m | corridor, lobby, reception | **required** | BCO [S6] |
| office (private) | 9 m² (max 40) | 2.7 m | circulation or open office | preferred | Neufert 8–10 m² [S7] |
| meeting_room | 9 m² | 2.7 m | circulation or open office | preferred | 9 m² for 4 people [S8] |
| pantry | 4 m² | 1.8 m | circulation or open office | — | practice |
| prayer_room | 9 m² | 2.4 m | circulation; no door to toilets | — | Saudi practice |
| toilet_male / toilet_female | 3 m² | 1.5 m | circulation; no door to pantry or workrooms | — | IPC [S4]; 1.5 m fits an accessible turning circle |
| storage | 2 m² | 1.0 m | circulation or open office | — | practice |
| it | 6 m² | 2.0 m | circulation | — | practice |
| corridor | — | 0.914 / 1.118 m by load | — | — | IBC 2015 T1020.2 [S3] |
| stairs | 12 m² | 2.4 m | corridor or lobby | — | IBC 1011.2 + ACS U-stair (2 × 1.118 m flights + 0.1 m gap) |
| elevator | 3.2 m² | 1.6 m | corridor or lobby | — | practice |

Meeting rooms are planned at about 2 m² per seat (vendor guides give 1.8–2.4 m²
[S8]); the program text proposes seats for about 20 % of staff.

## Corridors, stairs and exits (IBC 2015, read verbatim [S3])

- **Corridor width** (T1020.2): 44 in = **1118 mm**; 36 in = 914 mm when the
  corridor serves fewer than 50 people. The pack asks the planner for 1.2 m
  (1.5 m preferred) and checks the table value.
- **Stair width** (1011.2): 44 in = **1118 mm**; 36 in below 50 occupants.
  **Capacity** (1005.3.1): 0.3 in = **7.6 mm per occupant**, 5.1 mm with
  sprinklers and an emergency voice/alarm system. The check divides the
  storey's load over its stairs and requires a stair room of two flights plus a
  0.1 m gap.
- **Other egress components** (1005.3.2): 5.1 mm per occupant (3.8 mm
  sprinklered with voice alarm).
- **Door width** (1010.1.1): 32 in = 813 mm clear minimum. The openings text
  asks 0.9–1.0 m leaves (1.0 m clear-ish for accessible toilets) and 1.8 m at
  the entrance.
- **Exits per storey** (T1006.3.1): 1–500 people → **2**; 501–1000 → 3; over
  1000 → 4.
- **Single exit** (T1006.3.2(2)): Group B first storey up to **49** people
  (common path 75 ft = 23 m); second storey up to **29**; third storey and above
  never. A template repeated over several storeys is judged at its highest one.
- **Exit separation** (1007.1.1): at least **1/2 of the diagonal** of the area
  served, **1/3** when sprinklered.
- **Exit access travel distance** (T1017.2): Group B **200 ft = 61 m**
  unsprinklered, **300 ft = 91.4 m** sprinklered.
- **Dead-end corridors** (1020.4): 20 ft = **6.1 m**; 50 ft = 15.2 m in a
  sprinklered Group B building; unlimited when shorter than 2.5 × its width.

How ACS measures these on rectangles: exits above ground are stair rooms; on
the ground storey, rooms with a door to the outside (before doors exist, an
entrance, lobby or stair with an exterior wall run of 1 m or more). Travel
distance is measured from each room's farthest corner through passage points
(door centres, or shared-wall midpoints before doors) to the nearest exit room;
travel inside the exit room is not counted. It is an approximation and is
reported as one.

## Toilets (IPC 2015 Table 403.1, read verbatim [S4])

Business (Group B): **WC 1 per 25 for the first 50, then 1 per 50**;
lavatories 1 per 40 for the first 80, then 1 per 80; drinking fountain 1 per
100; one service sink (not for 15 people or fewer). The load is split half and
half by sex unless stated (403.1.1), separate facilities above 15 people
(403.2), and toilets within one storey and 152 m (500 ft) of every occupant
(403.3.3). Example: 120 people → 60 men → 2 + 10/50 → **3 WCs**, same for women.

WC capacity of a toilet room is read from its `objects` of kind toilet or
urinal when present, otherwise at **2.5 m² per WC** (a 1.0 × 1.5 m cubicle plus
its share of basins and circulation, from the Saudi mosque guide cubicle
minimum [S9]).

## Adjacency and zoning

- Plan the **core first** (stairs, elevator, toilets, risers) in the deep zone,
  stacked with the same rectangle and `core_id` on every storey.
- Workplaces on the facade: no workplace deeper than **10.5 m** from a window
  wall (half of the BCO deep-plan 21 m window-to-window [S6]).
- A continuous corridor or lobby reaches every room and core; meeting rooms,
  toilets and the prayer room open onto circulation, never through an office;
  toilets never open onto the pantry or a workroom.
- Reception beside the lobby; the lobby on the street with a 1.8 m door.
- Lifts: ISO 8100-32 office criteria are an up-peak handling capacity of
  **12 % of the population in 5 minutes** and an interval of **30 s or less**
  [S10]. The pack only asks for one lift from three storeys up (advisory) and
  leaves lift sizing to the engineer.

## Saudi practice

- A **prayer room** (musalla) in workplaces is the norm; the pack advises one,
  next to circulation and never opening onto toilets.
- **Separate men's and women's toilets** on every office floor; IPC requires
  separation above 15 people anyway.
- Women-only office sections (common in banks and some ministries) are not
  modelled; a brief that asks for them should be planned as separate suites with
  their own toilets and prayer room.

## What the pack checks (`acs_typology_office.check`)

Errors: missing lobby, stairs or workrooms; room below its minimum area or
width; room not reaching circulation; forbidden door (toilet to pantry or
workroom, prayer room to toilet); open office without an exterior wall; core
missing or misaligned; too few exits; corridor or stair too narrow; too few WCs,
no women's/men's separation, a storey more than one storey from toilets; NIA
below 8 m² per stated employee. Advisories: private office or meeting room
without a window, workroom deeper than 10.5 m, a storey without toilets, no lift
from three storeys, no prayer room, density below 10 m², and the sprinkler-
dependent limits (exit separation, travel, dead ends) while sprinklers are
unknown.

## Verification status

- Read verbatim this session: IBC 2015 and IBC 2021 chapter 10, IPC 2015
  chapter 4 (ICC public pages).
- From search summaries, not the documents themselves: BCO densities and plan
  depth, Neufert office areas, the meeting-room minimum, ISO 8100-32 lift
  criteria, the SBC 201 ← IBC 2015 relationship.
- Not verified: the official SBC 201-2018 tables (they may amend an IBC value);
  SBC 801 sprinkler triggers.

## Sources

- [S1] ICC pages on the Saudi Building Code (2018 edition revised from the 2015 International Codes): https://iccsafe.org/?p=240998 and https://shop.iccsafe.org/2018-saudi-building-code-sbc-201-study-companion.html
- [S2] Japan MLIT, summary of the Saudi Building Code (latest 2018, adapted from IBC 2015): https://www.mlit.go.jp/common/001404290.pdf
- [S3] IBC 2015 Chapter 10, Means of Egress: https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress
- [S4] IPC 2015 Chapter 4, Fixtures: https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings
- [S5] IBC 2021 Chapter 10, Means of Egress: https://codes.iccsafe.org/content/IBC2021P2/chapter-10-means-of-egress
- [S6] CIBSE Journal on BCO densities (2014: 8–13 m²; 2019: 8–10 m²; 2022: 10–12 m², deep plan 15–21 m): https://www.cibsejournal.com/opinion/how-change-office-densities-could-affect-office-design/
- [S7] Neufert office data (separate office 8–10 m² minimum), Scribd copy: https://www.scribd.com/document/718433275/neufert-reference-1
- [S8] Macquarie University space planning, meeting rooms (minimum 9 m² for 4): https://www.property.mq.edu.au/space_types/staff_spaces/meeting_rooms
- [S9] Saudi mosque design guide 4 (WC cubicle at least 1.0 × 1.5 m); see `mosque_planning.md`.
- [S10] Elevator World on ISO 8100-32:2020 office criteria (12 % in 5 min, ≤ 30 s): https://elevatorworld.com/?p=20988
- [S11] Saudi Engineers guidelines for SBC 1101/1102 (residential R3): https://saudieng.sa/English/RegulationsAndProcedures/Pages/SBCGuidelines.aspx
