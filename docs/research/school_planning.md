# School: planning research for the ACS instruction pack

Status: research for `acs_typology_school.py`; not wired into generation or
review (see `typologies_integration_plan.md`). Numbers are planning references
with sources; the Ministry of Education's own design manuals were not reachable
in this session, so the code base (IBC 2015, the base of SBC 201) carries the
hard checks and Saudi practice carries the advisories.

## Saudi context

- **Single-sex schools.** Public general education is separated for boys and
  girls. Since 2019 the Ministry's **early-childhood schools** have women teach
  boys in grades 1–3 (with kindergarten); separation continues above grade 3
  [S6]. The pack plans **one school per building**: `boys`, `girls` or
  `early_childhood`; a `mixed` brief is an error that asks for two schools.
- **Girls' schools** in Saudi practice have a screened (non-direct) entrance, a
  **waiting room for parents and visitors** at the entrance so visitors do not
  enter, and a **guard room** entered from outside only; street-facing windows
  on the ground storey are kept high (privacy). These come from Saudi design
  practice and school-design teaching material, not from a published code [S7].
- **Land and site** (MoMAH requirements for private educational buildings,
  December 2025, press summaries): land of at least **4 m² per student** for
  kindergarten rising to **5 m²** for larger complexes; a site on two streets,
  one at least 25 m wide; classrooms as separate fire areas [S4][S5].
- **Labs**: the Tatweer Building Company guide for private schools caps a
  laboratory at **25 students** [S3].

## Occupant load (IBC 2015 Table 1004.1.2, read verbatim [S1])

| Space | Factor |
|---|---|
| Classroom | 20 ft² net = **1.86 m²/student** |
| Shops and vocational rooms (science labs for egress) | 50 ft² net = 4.65 m² |
| Library reading room | 50 ft² net = 4.65 m² |
| Assembly, chairs only (hall, prayer room) | 7 ft² net = 0.65 m² |
| Canteen (tables and chairs) | 15 ft² net = 1.39 m² |
| Offices, staff room | 100 ft² gross = 9.29 m² |

## Room sizes (the pack's `ROOM_TABLE`)

| Role | Min area | Min width | Notes / basis |
|---|---|---|---|
| classroom | **class size × 1.86 m²** (55.7 m² for 30; 67 m² for 36), max 90 | **6.0 m** | code factor as a design floor: capacity = net area ÷ 1.86; exterior wall required (daylight) |
| science_lab | **75 m²** (25 students × 3 m²) | 7.0 m | 90 m² for a practical class of 30 (RSC; BB80 79–91 m²) [S2]; ≤ 25 students [S3]; exterior wall required |
| computer_lab | 60 m² | 6.0 m | practice |
| library (learning resources) | 60 m² | 6.0 m | practice |
| multipurpose_hall | 100 m² | 9.0 m | practice |
| prayer_room (musalla) | 40 m² | 6.0 m | practice; no door to toilets |
| office (administration) | 9 m² | 2.7 m | practice |
| staff_room | 20 m² | 3.6 m | practice |
| health_room | 12 m² | 3.0 m | practice |
| canteen | 20 m² | 3.6 m | practice; opens to circulation or the courtyard |
| waiting_room (girls) | 9 m² | 2.7 m | beside the entrance lobby |
| guard_room | 4 m² | 1.8 m | exterior wall; no door to the corridor or classrooms |
| toilet_students / toilet_staff (toilet_male / toilet_female in early childhood) | 6 / 3 m² | 1.8 / 1.5 m | IPC [S1b] |
| corridor | — | 1118 mm; **1829 mm** when the storey load is 100+ | IBC 2015 T1020.2 [S1] |
| stairs | 12 m² | 2.4 m | IBC 1011.2 + ACS U-stair |

Classrooms are capped at 90 m² as an advisory (a larger "classroom" is usually
two rooms drawn as one).

## Corridors, stairs, exits and travel (IBC 2015, read verbatim [S1])

- Corridors in Group E serving **100 or more** people: **72 in = 1829 mm**
  (T1020.2). Saudi practice is wider: **2.4 m** single-loaded and **3.0 m**
  double-loaded (secondary source [S7]); the pack advises below 2.4 m.
- Stairs 1118 mm per flight plus 7.6 mm per occupant (5.1 mm sprinklered with
  voice alarm).
- Exits per storey 2 / 3 / 4 (T1006.3.1). Group E single exit only on the
  **first storey up to 49** people; never from the second storey up
  (T1006.3.2(2)).
- Exit separation 1/2 of the diagonal (1/3 sprinklered). Travel distance
  Group E **200 ft = 61 m** unsprinklered, **250 ft = 76 m** sprinklered
  (T1017.2). Dead ends 6.1 m, 15.2 m in a sprinklered Group E building.
- Early grades on the ground storey (practice, advisory).

## Toilets (IPC 2015 Table 403.1, read verbatim [S1b])

Educational: **WC 1 per 50**, lavatory 1 per 50, drinking fountain 1 per 100,
one service sink. A single-sex school states its own sex share (403.1.1
exception: actual distribution); an early-childhood school splits boys' and
girls' toilets. The required number is taken on the larger of the student
count and the building occupant load from IBC factors (conservative, because
students move between classroom and lab). Staff toilets are separate from
students' toilets (practice; error when absent). Outdoor yard about **2.5 m²
per student** (secondary source [S7], advisory).

Example (`program_text`): 12 classrooms × 30 = 360 students → classroom ≥ 56 m²,
**8 WCs and 8 basins** for students, yard ≈ 900 m², land ≥ 1800 m² (5 m²).

## Adjacency and zoning

- Entrance lobby on the street; administration, staff room, health room and
  (girls) waiting room by the entrance; guard room outside the secure line.
- Classrooms along exterior walls, opening onto corridors; labs with their
  stores; toilets off the corridor or the courtyard, never into a classroom.
- Prayer room and canteen on circulation or the courtyard; the multipurpose
  hall near the entrance for events.
- Cores: two stairs on every upper storey, stacked, separated.

## What the pack checks (`acs_typology_school.check`)

Errors: a mixed boys-and-girls school; missing classrooms (to the confirmed
count), office, lobby or student toilets (boys' and girls' toilets in early
childhood); classroom below class size × 1.86 m² or 6 m width; classroom or lab
without an exterior wall; rooms not reaching circulation; toilet door into a
classroom; core missing or misaligned; exits, corridor and stair widths; WCs
short; no staff toilet; girls' school without a waiting room; guard room
opening inward. Advisories: early grades upstairs; low street windows in a
girls' school; corridor between 1.83 m and 2.4 m; yard or land per student
short; labs, library, hall and support rooms below practice sizes; the
sprinkler-dependent limits while sprinklers are unknown.

## Verification status

Read verbatim: IBC 2015 chapter 10 and IPC 2015 chapter 4. From search
summaries: early-childhood policy, MoMAH 2025 land per student, lab cap of 25,
lab area 90 m² for 30, corridor and yard practice. Not reachable in this
session: the Ministry's school design standards, the TBC private-school
minimum standards manual (its extracted text was garbled) and the full MoMAH
PDF. Before shipping, the owner should obtain those manuals; the table is the
place to update.

## Sources

- [S1] IBC 2015 Chapter 10: https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress
- [S1b] IPC 2015 Chapter 4: https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings
- [S2] Royal Society of Chemistry, school laboratory benchmarks (90 m² for 30; BB80 79–91 m²): https://edu.rsc.org/download?ac=13913
- [S3] Tatweer Building Company, minimum standards programme for private schools (lab ≤ 25 students): https://tbc.sa/shared/tadarujprogramv11.pdf ; design manual: https://tarkhees.tbc.sa/assets/files/EtimadFiles/ArabicManual.pdf
- [S4] SPA, MoMAH issues municipal requirements for private educational buildings (Dec 2025): https://www.spa.gov.sa/N2472560
- [S5] Okaz, three categories of private educational buildings and land per student: https://www.okaz.com.sa/local/na/2227677 ; full requirements: https://momah.gov.sa/sites/default/files/2025-12/alnskht%20alm%60tmdt%20lashtratat%20almbany%20alt%60lymyt.pdf
- [S6] Arab News, women teach young boys in Saudi public schools (2019, grades 1–3; segregation continues): https://www.arabnews.pk/node/1548366
- [S7] «أسس تصميم المدارس» (corridors 2.4 m / 3.0 m, 2.5 m² of yard per student; secondary source): https://byarchlens.com/%D8%A3%D8%B3%D8%B3-%D8%AA%D8%B5%D9%85%D9%8A%D9%85-%D8%A7%D9%84%D9%85%D8%AF%D8%A7%D8%B1%D8%B3-designing-schools/
