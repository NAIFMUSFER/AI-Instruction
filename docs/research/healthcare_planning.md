# Healthcare planning research for ACS: clinics, polyclinics, small hospitals

Date: 2026-11-27. Scope: concept planning of outpatient clinics, polyclinics
(مجمع طبي) and small hospitals in Saudi Arabia, at the level ACS plans today:
rectangular rooms on storey templates, then doors, windows and light points.
This note feeds `acs_healthcare_program.py` (room table, flow rules, instruction
texts and checks). Each source has a key in backticks; the module cites the same
keys in `SOURCES`.

**How to read the numbers.** They are planning assumptions taken from published
guidelines and codes. ACS uses them to brief the model and to check a concept
layout. They are not a code review: MOH licensing, CBAHI accreditation, the Saudi
Building Code (SBC 201/801) and Civil Defense approval need a licensed designer
and the authority. Where a guideline gives a range, ACS takes the stricter value
or says why not.

**How the sources were read.** The Saudi municipal requirement (`MOMRA-1441`) and
the DHA guideline parts (`DHA-C2`, `DHA-C6`, `DHA-SC`, `DHA-OR`) were read in full
from the publisher. FGI, IBC/SBC 201, NFPA 101, HBN/HTM and AusHFG are paywalled
or blocked from this session's network; their figures come from the publishers'
summaries, state adoptions and checklists cited below, and are marked so. A
claim that only a secondary source gives is said to be one.

## 1. Frameworks that govern a Saudi healthcare building

| Framework | What it governs | How ACS uses it |
|---|---|---|
| MOMRA/MOMAH «اشتراطات مباني الصحة والخدمات الاجتماعية الأهلية» 1441 H / 2019 (`MOMRA-1441`) | Private hospitals, medical complexes, clinics, labs, radiology and day-surgery centres: classification, plot minimums, parking, technical requirements | Typology definitions; 8% window rule; lift above two storeys; waste rooms; toilet ratios |
| Saudi Building Code SBC 201 (IBC 2015 base with Saudi amendments) and SBC 801 (fire) | Occupancy Group I-2 (hospitals) and B / ambulatory care; corridors, smoke compartments, refuge | Corridor 2.44 m for beds, compartments, travel distance, refuge (`IBC-SBC201`, `IBC-REFUGE`) |
| MOH regulations and CBAHI standards | Licensing and accreditation; `MOMRA-1441` 5-1 says interior medical spaces follow «متطلبات وزارة الصحة» and the CBAHI code | No open MOH space-standard was found; ACS uses international guidelines below as stated assumptions |
| FGI Guidelines 2022 (Hospitals; Outpatient Facilities) (`FGI`) | US minimum room sizes, clearances, infection control | Exam, OR and ICU minimums |
| DHA Health Facility Guidelines 2019 (Dubai, derived from AusHFG) (`DHA-C2`, `DHA-C6`, `DHA-SC`, `DHA-OR`, `DHA-E11`) | GCC-context room components, corridors, doors, lifts, operating unit | Most room areas, corridor and door widths, bed lift, OR suite planning |
| AusHFG (`AUSHFG`) | Australasian standard components | Ensuite 5 m2, single bedroom 16.5 m2 cross-check |
| UK HBN 00-04, HBN 04-01 (+ Supplement 1), HBN 26, HTM 01-01 | Circulation, inpatient rooms, isolation suites, theatres, decontamination | Cross-checks of isolation lobbies, CSSD flow |

### 1.1 What the Saudi municipal requirement says (`MOMRA-1441`, read in full)

* **Classification (3-1):** hospital (examination, treatment and admission);
  general medical complex (at least three specialties, one of them basic:
  surgery, internal medicine, obstetrics, paediatrics or family medicine);
  specialised medical complex (one specialty, **at least 3 clinics**); clinic;
  radiology centre; medical laboratory; day-surgery centre; support centres.
* **Minimum plot area (table 4-1)**, zone A (main cities) / zone B: general
  medical complex 400 / 300 m2; specialised complex 240 / 190 m2; clinic 80 /
  60 m2; radiology centre 300 m2; medical laboratory 120 / 90 m2; day surgery
  600 / 400 m2 standalone (400 / 300 m2 annexed); hospitals by bed (per-bed
  plot area and parking per bed; the table text is partly illegible in the
  published scan, so ACS does not use those two numbers).
* **Architecture (5-1):** interior spaces follow MOH requirements and the CBAHI
  code; fire protection per SBC-801 and SBC-201 chapter 9 with all escape routes;
  natural light and ventilation for all spaces **with window area at least 8% of
  the floor area**, artificial light and ventilation allowed by operating need;
  **medical waste rooms required**; main medical gas store outside the main
  building; an external pharmacy for hospitals of **100 beds or more**;
  radiation shielding approved by the authority; staff housing allowed on the
  plot but fully separated from the hospital.
* **Universal access (5-1-3):** handrails in patient corridors at **0.85 to
  0.95 m**; 5% of WCs and basins accessible (at least one); accessible parking by
  table 5-3.
* **Toilets (table 5-2):** hospitals and medical complexes, one WC and one basin
  per patient room, **or one bathroom shared by two adjacent rooms that both open
  directly into it**; clinics, radiology, labs and day surgery one WC per 25 and
  one basin per 40 for the first 50/80 persons.
* **Electrical (5-3 item 11):** buildings **above two storeys** have passenger
  lifts for persons with disabilities. Standby generators for medical buildings.
* **Mechanical (5-4):** ventilation designed to **ASHRAE 170-2017**; medical
  gases to NFPA 55/99; fire per NFPA 99-2018 where SBC is silent (SBC prevails).

### 1.2 Group I-2 in the building code (`IBC-SBC201`, `IBC-REFUGE`)

SBC 201 is based on IBC 2015 with Saudi amendments; the SBC text itself was not
reachable from this session, so the values below are the IBC figures as the
NFSA summary and the New York City adoption state them, and must be checked
against SBC 201 chapter 4 and 10 before any claim:

* Corridors in areas where **bed movement** is required: **96 in = 2.44 m** clear
  (IBC Table 1020.2).
* Smoke barriers divide **every storey used by persons receiving care, treatment
  or sleeping** (and other storeys with 50 or more occupants) into **at least two
  smoke compartments**; each compartment at most **22,500 ft2 = 2,090 m2**; travel
  distance from any point to a smoke-barrier door at most **200 ft = 61 m**
  (IBC 407.5). NFPA 101 newer editions allow up to 40,000 ft2 for some hospitals:
  ACS keeps the stricter 2,090 m2.
* Refuge area in each compartment for the occupants of the adjoining one: **30
  net ft2 = 2.8 m2 per care recipient on a bed or stretcher**, 6 ft2 = 0.56 m2 per
  other occupant (IBC 407.5.1 as adopted in NYC).
* Means-of-egress doors used for **bed movement**: **41.5 in = 1.05 m** clear
  (`NFPA101-DOOR`, NFPA 101 and the I-codes).

## 2. Typologies

| Typology | Definition used by ACS | Core program (ACS `PROGRAMS`) |
|---|---|---|
| Clinic (عيادة) | One outpatient practice, no inpatient beds | entrance, reception, waiting, exam room, accessible toilet, clean utility, soiled utility, medical waste room |
| Polyclinic (مجمع طبي / مركز طبي) | Several outpatient clinics; `MOMRA-1441` specialised complex has **at least 3 clinics** | clinic program + **3 exam rooms** + treatment room |
| Small hospital (مستشفى صغير) | Up to about 100 beds (the external-pharmacy threshold of `MOMRA-1441`): outpatients, emergency, imaging, lab, pharmacy, one or more wards, optional OR suite and ICU | see `PROGRAMS['hospital']`: emergency with ambulance entrance, resuscitation and treatment, X-ray, lab, pharmacy, ward rooms with ensuites, isolation room with anteroom, nurse station, clean and soiled utility, medication room, staff change, service entrance and waste room |

The ACS program registry (`acs_programs.json`) already detects `clinic` and
`hospital` from Arabic and English keywords (category `healthcare`); the
`polyclinic` split is new in the pack (`typology_of`).

## 3. Departments and adjacency

| Department | Must be near (adjacent or same storey) | Kept away from | Source |
|---|---|---|---|
| Main entrance, reception, waiting | street; outpatients; pharmacy | ambulance and service entrances | `MOMRA-1441`, ACEM ED design guideline (separate ambulance and walk-in entrances) |
| Outpatients (exam, treatment, sample collection) | waiting / public corridor; lab, imaging | inpatient and OR zones | `DHA-C2` (outpatient corridors 1.85 m) |
| Emergency | own **ambulance entrance on another facade**; resuscitation and treatment on a bed corridor; **imaging on the same storey**; fast bed route to OR and ICU | public waiting of outpatients | ACEM design guideline (two entrances; imaging in or near ED), `DHA-OR` 4.1 (OR close to ED and ICU) |
| Imaging | ED and outpatients; bed access | — | `DHA-C2` (radiology corridor 2.0 m for irregular bed traffic) |
| Laboratory, pharmacy | outpatients; ward supply route | — | `MOMRA-1441` (external pharmacy at 100 beds) |
| Inpatient wards | bed corridor; per storey nurse station, clean utility, soiled utility, medication room; bed lift | public routes | `DHA-SC`, FGI (clean and soiled workrooms per unit) |
| ICU | OR suite (same storey or bed lift); ED | public routes | `DHA-OR` 4.1 |
| OR suite | ICU, ED, wards; sterile supply (CSSD) with clean and used lifts; staff change one-way into the suite | public | `DHA-OR` 3.5, 3.7, 4.1 |
| Support and logistics (waste, service entrance, cleaners, morgue) | service corridor; outside for collection | public and clean routes | `MOMRA-1441` (waste rooms), DHA planning |

## 4. Separated flows

Five flows are kept apart: **patients and visitors**, **staff**, **beds**
(inpatients and emergency patients on trolleys), **clean and sterile supplies**,
**soiled goods and waste**.

* Public route: entrance, reception, waiting, public corridor, outpatient rooms.
  Patients on beds and staff use bed and staff corridors and the bed lift.
* OR suite (`DHA-OR`, read in full): a restricted unit with controlled entry;
  separate entrances for staff, services and patients; staff change rooms
  arranged for **one-way traffic** into the suite; **sealed carts are mandatory**
  for supplies; **scrub bays adjacent to each OR** with a door into the OR (no
  scrub sink inside the OR, no open scrub troughs in corridors); equipment stores
  at **10 m2 per OR**; **recovery stage 1 at least 2 bed spaces per OR**, stage 2
  at least 2 (ideally 3) per OR; ORs **positive pressure with HEPA**; stores
  positive to adjacent areas; endoscopy rooms preferably negative; switchable
  rooms avoided. The single-corridor and double-corridor ("race track") models
  are both acceptable; modern design treats all corridors as degrees of clean,
  not a "dirty corridor".
* Sterile services (HTM 01-01, FGI): **one-way flow** from soiled to clean to
  sterile; decontamination separated by walls from the clean workroom, with
  pass-through washer-disinfectors or windows, never a door between them.
* Soiled utility, clean-up and waste rooms open onto corridors, never into a
  clean room, a sterile store or a waiting area; sterile stores share no wall with
  soiled rooms.

ACS encodes these as `FLOW_RULES` (door and wall separations), `OR_SUITE_CORE`
(the OR core opens only inside the suite) and `STOREY_RULES` (support on the
same storey).

## 5. Room sizes and clearances

Clear internal areas; ACS checks the room rectangle against them.

| Room (ACS role) | Published figures | ACS minimum (area / short side) | Source |
|---|---|---|---|
| Exam room `exam_room` | FGI hospital-based exam **120 ft2 = 11.15 m2, 10 ft = 3.05 m wide**; outpatient exam 80 ft2 (7.4 m2), specialty 100 ft2; NHS consulting/exam 16-18 m2 | **11.15 m2 / 3.05 m** (one universal room so any exam room can serve any clinic) | `FGI-HFM` (FGI summary); NHS Property Services sheet |
| Treatment room `treatment_room` | DHA 14 m2 | 14 / 3.05 (width ACS) | `DHA-SC` |
| Procedure room `procedure_room` | DHA 20 m2 and 25 m2 | 20 / 4.0 (width ACS) | `DHA-SC` |
| Single patient room `patient_room` (toilet excluded) | DHA standard 1-bed 18 m2; AusHFG 16.5 m2 (+ ensuite 5 m2); FGI at least 120 ft2 clear with 3 ft at the sides and foot of the bed; NHS Scotland 19 m2 | **18 m2 / 3.3 m** (width ACS: 1 m bed + 0.9 m side clearance + 1.2 m transfer side + headwall) | `DHA-SC`, `AUSHFG`, `MA-DPH` |
| Ensuite `ensuite` | AusHFG 5 m2 | 5 / 1.6 | `AUSHFG` |
| Isolation room `isolation_room` | DHA negative-pressure 1-bed 18 m2 (28 m2 large) | 18 / 3.3 | `DHA-SC` |
| Anteroom `anteroom` | DHA airlock 6 m2; HBN 04-01 Supp. 1 (2024) personnel lobby 5 m2, bed lobby 6.5 m2 | 6 / 1.8 | `DHA-SC`, HBN 04-01 Supp. 1 |
| ICU room `icu_room` | FGI **200 ft2 = 18.6 m2** clear; head 1 ft, foot 5 ft, transfer side 5 ft, other side 4 ft; FGI 2010 13 ft (3.96 m) headwall per bed; DHA ICU 25 m2 | **18.6 m2 / 3.96 m** | `MA-DPH`, `FGI` |
| Operating room `operating_room` | FGI general OR **400 ft2 = 37.2 m2**, **20 ft = 6.1 m** clear; large-equipment 600 ft2; DHA general 42 m2, digital **55 m2 (optimal)**, large 60 m2, hybrid 70 m2 | **37.2 m2 / 6.1 m**; the text asks for 42-55 m2 practice through the DHA references in this note | `FGI` (via state templates and summaries), `DHA-OR` |
| Scrub `scrub` | DHA 6 m2 | 6 / 1.5 | `DHA-SC` |
| Anaesthetic induction | DHA 15 m2 (optional) | 15 | `DHA-OR` |
| Recovery `recovery` | DHA stage 1 bay 12 m2; 2 per OR | 12 m2 per bed; capacity = floor(area / 12) | `DHA-SC`, `DHA-OR` |
| Sterile store `sterile_store` | DHA 12 m2 (20 m2 CSSD) | 12 / 2.4 | `DHA-SC` |
| Clean-up `clean_up` | DHA 7 m2 | 7 / 2.0 | `DHA-SC` |
| Clean utility / soiled utility | DHA 12 m2 (sub-room 8 m2) / 12-14 m2 (sub-room 8 m2) | 8 / 2.0 each | `DHA-SC`, `DHA-OR` |
| Medication room | DHA 10 m2 | 10 / 2.4 | `DHA-SC` |
| Nurse station | DHA 14 m2 (5 and 20 m2 variants) | 14 / 2.4 | `DHA-SC` |
| Resuscitation | DHA critical patient bay 20 m2 | 20 / 4.0 | `DHA-SC` |
| ED treatment | DHA acute treatment bay 12 m2 | 12 / 3.0 | `DHA-SC` |
| Waiting / reception | DHA 10 m2 and up | 10 | `DHA-SC` |
| Accessible toilet | DHA 6 m2; ICC A117.1-2017 turning circle **67 in = 1.70 m** for new buildings (60 in = 1.525 m in older editions and existing buildings) | 6 / 1.7 | `DHA-SC`, `ICC-A117` |
| Sample collection | DHA blood collection bay 5 m2 | 5 / 2.0 | `DHA-SC` |
| Pharmacy | DHA pharmacy counter 9 m2 | 9 / 2.4 | `DHA-SC` |
| Staff change / staff room / office / cleaner's room | DHA 12 / 15 / 9 / 6 m2 | same | `DHA-SC` |
| X-ray, ultrasound, lab | equipment-specific; not found in an open primary source | 25 / 4.5, 12 / 3.0, 12 / 3.0 (ACS) | `ACS` |

Ceiling heights (not checked by ACS, which has one wall height per storey):
DHA recommends 2.7 m in patient bedrooms and work areas, **3.0 m in ICU, CCU,
resuscitation, operating, interventional imaging and birthing rooms** (`DHA-C2`
2.2). ACS should give hospital storeys a floor height of at least 4.2 m.

## 6. Circulation

* **Corridors** (`DHA-C2` 2.1, clear of handrails, 100 mm allowed per handrail):
  patient areas with regular bed, trolley and stretcher traffic (inpatient,
  operating, ICU) **2,450 mm**; outpatient units **1,850 mm**, and no corridor a
  patient uses is ever below 1,850 mm; irregular bed traffic (radiology)
  2,000 mm with widening at doors; staff-only corridors up to 12 m long
  1,500 mm; interdepartmental travel and public corridors at least 2,450 mm.
  Corridors may need widening, a recessed door or a double door where a bed
  turns into a room. IBC: 96 in (2.44 m) where beds move.
* **Doors** (`DHA-C6` 6.2): patient bedrooms **1,400 x 2,140 mm** clear in new
  work, never below 1,200 x 2,040 mm; stretcher, wheelchair and mobility-aid rooms
  **900 mm**; ensuites, bathrooms and showers used with hoists **1,000 mm**.
  NFPA 101 / IBC: bed-movement egress doors 41.5 in (1.05 m). Doors into
  corridors are recessed where they swing out (100 mm beyond the swing).
* **Bed lift** (`DHA-E11`): rated load 2,500 kg, clear car **1,800 x 2,700 mm**,
  clear door **1,400 x 2,200 mm**, car height at least 2,500 mm. The SSU may be
  served by dedicated **clean and used goods lifts** (`DHA-OR` 3.5).
* **Circulation share** (`DHA-C2` 2.4, minimum %): inpatient units 35, ICU 40,
  emergency 40, operating unit 40-45, outpatients 32, health centre 32,
  imaging 35-40, pharmacy 25, laboratory 25, sterile supply 25. ACS does not
  check these yet; they are useful to size a brief's gross area.

## 7. Fire: compartments and horizontal evacuation

Hospitals defend in place: patients are moved horizontally through a smoke
barrier into the next compartment, not down the stairs. ACS asks for and checks,
on every storey with patient care:

1. at least **two compartments** (`compartment` on every room);
2. each at most **2,090 m2**;
3. neighbouring compartments meet at a **corridor-to-corridor wall of at least
   1.2 m** (the cross-corridor smoke door must take a bed);
4. no care room farther than **61 m** in a straight line from that boundary
   (a lower bound of the real travel distance, so a finding is always real);
5. advisory: the corridors and waiting of the receiving compartment hold
   **2.8 m2 per bed** of the compartment it receives from.

Not evaluated by ACS: fire-resistance ratings, smoke-barrier construction,
sprinklers, exit counts and widths, stair pressurisation, Civil Defense
approval (SBC 801).

## 8. Infection control

* **Airborne infection isolation (AII):** at least **12 air changes per hour
  (2 outdoor)**, negative pressure, single-patient room with its own toilet
  (FGI and ASHRAE 170 as the NIH technical bulletin and the UCSF Curry TB
  centre manual summarise them). FGI and CDC do not require an anteroom; when
  there is one, the room is negative to the anteroom and the anteroom negative
  to the corridor (ASHRAE 170 addendum). DHA Part D (Class N): isolation room
  -10 Pa, anteroom -5 Pa, ensuite -15 Pa; HBN 04-01 Supplement 1 (2024) uses a
  bedroom, lobby and en-suite suite (personnel lobby 5 m2, bed lobby 6.5 m2).
  **ACS decision:** every isolation room has its own anteroom (staff entry,
  PPE, hand basin) and ensuite, and keeps its bed door onto the bed corridor,
  as the AusHFG Class N room layout does.
* **Hand hygiene:** a hand-washing station in every patient room besides the
  one in its toilet (FGI since 2001); one clinical hand basin per four bays in
  holding and recovery (`DHA-OR` 5.14.1). Not checked by ACS (no fixtures yet).
* **Clean and soiled utility** per unit; soiled workroom with a flushing-rim
  clinical sink (FGI 2.1-2.8.12.2 as the Joint Commission FAQ cites it).
* Ventilation, pressure regimes, filtration and medical gases are outside the
  concept model and stay **NOT_EVALUATED**.

## ACS assumptions

Numbers whose source key is `ACS` are planning assumptions where no open
primary source gave a value: most minimum short sides (for example 3.3 m for a
patient room, 3.05 m for a treatment room, 4.0 m for a procedure room), the
X-ray, ultrasound and lab areas, the 1.2 m exterior wall run for a patient
window and the 1.6 m ensuite width. **Policy:** a size from a guideline or code
blocks approval when missed; a size marked `ACS` only advises. Further ACS
decisions:

* one universal exam room at the FGI hospital size (11.15 m2), not the 7.4 m2
  outpatient minimum, so rooms can be swapped between specialties;
* the stricter of each pair: 2.44 m bed corridor (IBC) rather than 2.4 m,
  2,090 m2 compartments (IBC) rather than NFPA's 40,000 ft2, 1.2 m bed doors
  (DHA minimum) rather than NFPA's 1.05 m, with 1.4 m advised;
* an ensuite may serve two adjacent patient rooms (`MOMRA-1441` table 5-2);
* every storey with patient care is compartmented in a hospital (IBC wording),
  not only storeys with more than 30 sleeping patients (NFPA wording);
* polyclinic = at least three exam rooms and a treatment room.

## Sources

| Key | Source | Accessed |
|---|---|---|
| `MOMRA-1441` | Ministry of Municipal and Rural Affairs, «اشتراطات مباني الصحة والخدمات الاجتماعية الأهلية», 1441 H / 2019, [PDF](https://momah.gov.sa/sites/default/files/2022-02/%D8%A3%D8%AF%D8%A7%D8%A9%20%D8%A7%D9%84%D8%A7%D8%B5%D8%AF%D8%A7%D8%B1%20%2B%20%D8%A7%D8%B4%D8%AA%D8%B1%D8%A7%D8%B7%D8%A7%D8%AA%20%D9%85%D8%A8%D8%A7%D9%86%D9%8A%20%D8%A7%D9%84%D8%B5%D8%AD%D8%A9%20%D9%88%D8%A7%D9%84%D8%AE%D8%AF%D9%85%D8%A7%D8%AA%20%D8%A7%D9%84%D8%A5%D8%AC%D8%AA%D9%85%D8%A7%D8%B9%D9%8A%D8%A9%20%D8%A7%D9%84%D8%A3%D9%87%D9%84%D9%8A%D8%A9.pdf) | read in full |
| `DHA-C2` | DHA Health Facility Guidelines 2019, Part C 2 «Space, Standards & Dimensions», [link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/Guidelines/FileContent/Preview/DHAHFG/Part%20C_2%20-%20Space_Standards_Dimensions) | read in full |
| `DHA-C6` | DHA HFG Part C 6 «Doors», [link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/Guidelines/FileContent/Preview/DHAHFG/Part%20C_6%20-%20Doors) | read in full |
| `DHA-SC` | DHA HFG Standard Components A-E, F-P, Q-Z (room names carry their areas), [link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/StdComps/All/AtoE/DHAHFG) | read in full |
| `DHA-OR` | DHA HFG Part B 350 «Operating Unit», [link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/Guidelines/FileContent/Preview/DHAHFG/DHA_part_b_operating_unit) | first 45 pages (planning, flows, schedule start) |
| `DHA-E11` | DHA HFG Part E 11 «Vertical Transportation System», [link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/Guidelines/FileContent/Preview/DHAHFG/Part%20E_11%20-%20Engineering%20-%20Vertical%20Transportation%20System) | search excerpt |
| `FGI` | Facility Guidelines Institute, Guidelines for Design and Construction of Hospitals / Outpatient Facilities (2018, 2022), [fgiguidelines.org](https://fgiguidelines.org/); OR 400 ft2 / 20 ft and ICU 200 ft2 / 13 ft via state templates and summaries | secondary |
| `FGI-HFM` | B. Langlands, «Design distinctions for exam, procedure and operating rooms», HFM, [link](https://hfmmagazine.com/articles/3764-design-distinctions-for-exam-procedure-and-operating-rooms) | search excerpt |
| `MA-DPH` | Massachusetts DPH plan-review checklists IP1 (med/surg unit) and IP5 (ICU) built on FGI, [IP5](https://www.mass.gov/doc/ip5-intensive-care-unit-0/download) | search excerpt |
| `IBC-SBC201` | NFSA, Group I-2 requirements summary (IBC), [PDF](https://nfsa.org/wp-content/uploads/2025/01/I-2C1-1.pdf); IBC Table 1020.2 | search excerpt |
| `IBC-REFUGE` | New York City Building Code 407.5.1 refuge area (IBC adoption), [link](https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-167229) | search excerpt |
| `NFPA101-DOOR` | «Decoded: patient room doors in health care occupancies», [link](https://idighardware.com/2021/03/decoded-patient-room-doors-in-health-care-occupancies/) | search excerpt |
| `AUSHFG` | AusHFG HPU 340 Adult Acute Inpatient Unit, schedule of accommodation (rev. 8, 2025), [PDF](https://aushfg-prod-com-au.s3.amazonaws.com/download/HPU_B.0340_8_SOA%20Extract.pdf) | search excerpt |
| `ICC-A117` | ICC A117.1 turning space (2017: 67 in new construction), [ICC draft](https://www.iccsafe.org/wp-content/uploads/asc_a117_1/A117.1_2023-clean-draft-for-final-2025-9-1.pdf); [Access Board comparison](https://www.access-board.gov/ada/ada-ibc-comparison/chapter-3/) | search excerpt |
| `ACS` | this note, section «ACS assumptions» | — |

Also consulted (not cited by a module key): ACEM Emergency Department Design
Guidelines G15 ([link](https://acem.org.au/Documents/Guidelines/Emergency-Department-Design));
NHS England HBN 04-01 Supplement 1, 2024 revision
([PDF](https://www.england.nhs.uk/wp-content/uploads/2009/12/health-building-note-04-01-supplement-1-july-2025.pdf));
NHS Scotland repeatable rooms report (19 m2 single bedroom,
[PDF](https://www.nss.nhs.scot/media/1833/nhss-repeatable-rooms-report-vdraft-dec-2020.pdf));
NHS Property Services design standards appendix I (consulting/exam 16-18 m2,
[PDF](https://www.property.nhs.uk/media/mu5luyza/nhsps-standard-health-design-standards-appendix-i.pdf));
NIH ORF technical bulletin on isolation rooms
([PDF](https://orf.od.nih.gov/TechnicalResources/Documents/Technical%20Bulletins/21TB/HVAC%20Considerations%20for%20Converting%20Patient%20Rms%20to%20Infection%20Isol%20Rms%20or%20Prot%20Envi%20Rms-October%202021%20Technical%20Bulletin_508.pdf));
UCSF Curry TB Center AIIR guide
([PDF](https://www.currytbcenter.ucsf.edu/sites/default/files/2023-12/IC_2023_AIIR_December_2023.pdf));
DHA Part D 4 «Isolation Rooms»
([link](https://services.dha.gov.ae/tahpi-app/HealthFacilityGuidelines/Guidelines/FileContent/Preview/DHAHFG/Part%20D_4%20-%20Isolation%20Rooms));
AusHFG Class N room layout sheet (Tasmania Parliament,
[PDF](https://www.parliament.tas.gov.au/__data/assets/pdf_file/0019/84340/09-AUSHFGRoomLayout-and-DataSheet_RLS_1BR-IS-N1_4.pdf));
Joint Commission FAQ on soiled workrooms
([link](https://jointcommission.org/standards/standard-faqs/home-care/environment-of-care-ec/000001272));
HFM «FGI requirements for sterile processing facilities»
([link](https://hfmmagazine.com/node/698709)); MOH hospital commissioning
checklists ([PDF](https://www.moh.gov.sa/Documents/HOSPITAL-COMMISSIONING-CHECKLISTS.pdf)).

Not reachable from this session: the SBC 201/801 texts, the FGI 2022 books,
HBN 00-04 / 04-01 / 26 PDFs and the AusHFG website (network-blocked or
paywalled). Before a figure is presented to a client as a code value, check it
against the adopted Saudi edition.
