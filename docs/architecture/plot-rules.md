# Plot rules: buildable envelope, parking and Saudi residential basics

Status: implemented on `claude/plot-rules` (not yet deployed). Scope: residential
generation from a description (apartment buildings and villas). Warehouses and
uploaded-plan transcription are unchanged.

## Why

The architect review of a generated 20 × 25 m Riyadh building (3 floors, 2 flats
per floor) found: 100 % plot coverage with every habitable window on a
neighbour's plot line (B1), six flats and no parking (B2), the guest/family
zoning reversed (B3), and the ground-floor lobby with its street door repeated
on the upper floors, opening onto the void (B4); plus flat entries off a
corridor instead of the stair landing (M1), a 17.5 m dead-end corridor (M2) and
flats about twice the option estimate (M3). The contract had no setback,
street, coverage or parking fields and the prompt told the model not to add
setbacks or parking.

## Principle

ACS does not invent regulation. A plot rule is an input: the user states it, or
ACS applies a clearly labelled, editable default assumption that cites its
source. Every assumption is written in plain Arabic to `meta.assumptions` and is
shown in the review («افتراض: ارتداد جانبي (الغرب) 2 م — … عدّله حسب اشتراطات
أمانة منطقتك»). Nothing here is a compliance certificate.

## Inputs (generation command field `plot`)

```json
{"streets": ["N", "E"],            // 0–2 distinct sides; empty = unknown → assumed N
 "street_width_m": 15,             // optional, primary street
 "setbacks_m": {"N": 3, "W": 0},   // optional per side; missing = default
 "max_coverage": 0.65,             // optional ratio
 "parking": {"placement": "front_setback" | "pilotis" | "none", "count": 9},
 "landing_entries": true}          // flats open on the stair landing
```

Validated strictly by `acs_plot_rules.validate_input` (unknown keys, ranges,
duplicate sides and non-integer counts are rejected). The block is part of the
job's resume binding, so a resumed job cannot silently change the plot.
Coordinates are the canonical plan's: x east, z south, so N is the land edge
z = 0. Old commands and old revisions without `plot` keep their previous
generation and review behaviour exactly.

Step 01 of the workspace shows these inputs in a new module
(`public/app/ui/plot-rules.mjs`, logic in `public/app/core/plot-rules.mjs`):
second street, street width, four setbacks with the default shown as the
placeholder, coverage, parking placement and count, and the landing option. It
reuses the existing «جهة الشارع» select, accepts Arabic-Indic digits and the
Arabic decimal comma, previews the envelope and parking capacity live, and
asks for re-confirmation when a value changes.

## Defaults and sources

Source: «اشتراطات إنشاء المباني السكنية», Ministry of Municipalities and Housing,
July 2024 — <https://momah.gov.sa/sites/default/files/2024-07/ashtratat%20a%27nsha%20almbany%20alsknyt%20almnshwrt%20%60ly%20mwq%60%20alwzart%20.pdf>
(retrieved 2026-11-26; clause numbers below are that document's).

| Value | Apartment building (عمارة) | Villa (فيلا) | Source |
|---|---|---|---|
| Front (street) setback | 1/5 street width, min 3 m | 1/5 street width, min 3 m; 6 m on streets ≥ 30 m | §4-2-4 (4), §4-1-4 (4–5) |
| Second street (corner) | 1/5 street width, min 2 m | same | §4-2-4 (4), §4-1-4 (4) |
| Neighbour (side/rear) | 2 m up to 5 floors, 3 m above | 1.5 m | §4-2-4 (4), §4-1-4 (4) |
| Coverage | ground 65 % (upper 75 %) | 75 % | §4-2-4 (1–2), §4-1-4 (1–2) |
| Parking | 1.5 per flat, rounded up | 1 per villa ≤ 400 m² land, 2 above | §4-2-4 (6), §4-1-4 (14) |
| Parking in the front setback | allowed (front fence may be removed) | allowed | §4-4 (8), §4-1-4 (11) |
| Ground floor as parking (pilotis) | allowed in multi-storey buildings, ≥ 2.5 m clear | — | §4-4 (5) |
| Street width when unknown | 15 m | 15 m | **unverified** assumption |
| Stall size | 2.5 × 5.5 m perpendicular | same | **unverified** common practice |
| Pilotis capacity | 25 m² per stall incl. aisle, 30 m² for lobby/stairs | — | **unverified** planning ratio |
| Window distance to a neighbour line | ≥ that side's setback; never on a 0 m line | same | derived from the setback rule |
| Flat area target | option card estimate ±25 % | — | ACS estimate (not a regulation) |
| Entry ↔ majlis ≤ 5 m, bedroom door ≥ 3 m from entry, landing ≤ 6 m, dead end ≤ 6 m | | | ACS planning assumptions (dead end **unverified** against the fire code) |

Coverage is applied to every floor with the ground-floor ratio (conservative;
upper floors could take 75 %).

## Envelope algorithm (`acs_plot_rules.resolve`, deterministic)

1. Land = confirmed `site_width_m × site_depth_m` (required).
2. Setbacks per side from the user or the defaults above (primary street,
   second street, neighbours; >5 floors widens apartment neighbour setbacks).
3. Rectangle = land minus setbacks.
4. Front-setback parking: the primary street setback is deepened to the stall
   depth (5.5 m) when needed, so one perpendicular row fits in front.
5. Coverage cap: if the rectangle exceeds `coverage × land`, trim the side
   opposite the primary street (rear) to the cap.
6. A confirmed building size (`building_width_m/depth`) must fit; it is then
   anchored on the street setback line, centred laterally, and becomes the
   envelope. With plot rules the model's `site` is the land, and the building
   size requirement is measured as the rooms' extent (a maximum).
7. Preflight (before any paid call, Arabic message, job not created):
   land missing, envelope narrower than 3 m, building larger than the envelope,
   parking that cannot fit (front row: `floor((frontage − 1.5) / 2.5) − 1`,
   pilotis: `floor((envelope − 30) / 25)`), pilotis with one floor or with a
   per-floor program that puts flats on the parking floor, and a program that
   cannot fit even at the low end of the flat-area tolerance
   (`flats per floor × target × 0.75 + 20 m²`).

The resolved block (`schema: acs.plot-rules/1`) is stamped by the trusted parent
into `meta.acs_plot_rules` from the validated command. The worker derives the
same block for the prompt; provider or worker copies are discarded, and chat
edits always carry the revision's block unchanged.

## Generation

- The prompt replaces «لا تضف … ارتدادات أو موقفاً» with a «اشتراطات الأرض»
  section: land, street sides, every setback, the envelope rectangle in plan
  coordinates, parking reservation, entrance on the street side, ground vs
  typical template, landing entries, flat area target, window and privacy
  rules. The planning, repair and openings system prompts get a short
  PLOT RULES addendum.
- The confirmed-program manifest now emits a distinct ground template
  (`residential_<n>_ground`: entrance lobby + flats, or `parking_ground` with
  the pilotis hall) and a typical upper template (`residential_<n>`: stair
  landing role `lobby`, no entrance lobby, no external door). Each flat gets a
  foyer zone; up to two flats per floor open on the lobby/landing, a common
  corridor is planned only for more flats.
- Layout: site forced to the land; a layout that fits the envelope but sits at
  the wrong origin is moved by one shared offset (disclosed); rooms outside
  the envelope are findings for the paid repair, with the exact inequalities.
- Openings: the plot context goes to the openings stage; window-on-boundary and
  upper-external-door findings join the existing corrective pass but never fail
  the job (they stay blocking in the review).
- Fallback: when the provider layout/openings fail, `acs_plot_layout` builds a
  disclosed rectangular plan inside the envelope (stairs and landing on the
  street, both flats opening on the landing beside their majlis, bedrooms at
  the back, windows only where the plot rules allow).

## Checks (`acs_plot_rules.check`, review scope `plot_rules`)

Run only for revisions that carry `meta.acs_plot_rules`; identical storeys
(stair variants) are reported once with their floor numbers.

| Code | Severity |
|---|---|
| `PLOT_OUTSIDE_ENVELOPE` rooms outside the envelope | blocking |
| `PLOT_COVERAGE_EXCEEDED` | blocking |
| `PLOT_OPENING_ON_BOUNDARY` window/door on a 0 m non-street plot line | blocking |
| `PLOT_WINDOW_TOO_CLOSE` habitable window nearer than that side's setback | blocking |
| `PLOT_WINDOW_BELOW_DEFAULT` user setback below the regulatory default | advisory |
| `PLOT_PARKING_SHORTFALL` (front stalls derived from the ground floor, or pilotis area) | blocking |
| `PLOT_PARKING_NOT_PROVIDED` (placement «none») | advisory |
| `PLOT_UPPER_EXTERIOR_DOOR` upper door to the void | blocking |
| `PLOT_UPPER_TERRACE_DOOR` upper door onto a lower roof | advisory |
| `PLOT_UPPER_ENTRANCE_LOBBY` entrance lobby repeated upstairs | advisory |
| `PLOT_ENTRANCE_NOT_ON_STREET` | advisory |
| `PLOT_ENTRY_NOT_ON_LANDING` (only when requested) | blocking |
| `PLOT_DEAD_END_CORRIDOR` | advisory |
| `PLOT_UNIT_AREA_OFF_TARGET` | advisory |
| `PLOT_ZONING_MAJLIS_FAR`, `PLOT_ZONING_BEDROOM_AT_ENTRY` | blocking if the brief asked for guest privacy, else advisory |
| `PLOT_RULES_INVALID` malformed stamped block | blocking |

Advisories are returned in `review.advisories`, never block approval, and are
shown in the workspace list prefixed «ملاحظة استشارية لا تمنع الاعتماد». The
workspace state also returns `plot_rules` (envelope, setbacks, derived stalls)
so the plan draws the dashed envelope and the parking row.

## Out of scope

Structure, fire code (escape distances, dead-end limits, stair widths), MEP,
accessibility, building height and annex rules, projections/balconies over
setbacks, basements, municipality-specific overrides (e.g. Riyadh, Jeddah
zoning plans), irregular (non-rectangular) plots, chamfered corners, plot
orientation other than the plan axes, and any approval by a municipality or a
licensed engineer.

## Risks

- Prompts are longer: about 2.2 k characters (plot section ≈ 1.2 k Arabic
  characters plus the English system addendum) on every outline, plan-chunk
  and repair call, and about 0.9 k on every openings call — roughly
  0.6–1 k extra input tokens per call, with matching cost and some latency.
- Stricter checks mean more paid repair/correction calls within the budget the
  user chose, and more jobs ending in the deterministic fallback.
- Small or deep-narrow envelopes may not fit the requested program: the user
  is told before generation (Arabic preflight) when the numbers clearly cannot
  fit; borderline cases are still generated and reported in the review.
- Defaults are national; municipalities can differ. They are labelled and
  editable, but a user who ignores them may still plan with the wrong values.
- Pilotis depends on the residential options card counting flats on the floors
  above the parking floor (one hook line in `residential-options.mjs`).
