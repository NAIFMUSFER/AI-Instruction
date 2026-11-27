# Retail, showroom and mixed-use: planning research for the ACS instruction pack

Status: research for `acs_typology_retail.py`; not wired into generation or
review (see `typologies_integration_plan.md`). Covers ground-floor shops and
showrooms with offices or apartments above, the common Saudi «عمارة تجارية
سكنية» or «تجارية إدارية». Numbers are planning references with sources, not
compliance verdicts.

## Codes and rules that apply

- **SBC 201** (IBC 2015 base, see `office_planning.md`) for mercantile (Group M)
  occupant load and egress, and for apartments above (Group R-2, which SBC 201
  covers; **SBC 1101** covers one- and two-family houses only [S9]).
- **SBC 701** / IPC 2015 for fixtures [S2].
- **Municipal requirements** (MoMAH «اشتراطات إنشاء المباني السكنية» and the
  residential-commercial building rules) for separate entrances, where shops may
  open, shop sizes and parking [S3][S4][S5].
- **SBC 801** and IBC 2015 Table 508.4 for the fire separation between shops and
  dwellings: outside what ACS measures; the pack states it, never sizes it.

## Occupant load (IBC 2015 Table 1004.1.2, read verbatim [S1])

| Space | Factor | Note |
|---|---|---|
| Mercantile (shops, showrooms) | 60 ft² gross = **5.57 m²/person** | IBC 2015 already uses 60 gross on every floor; older editions used 30 ft² on the ground floor |
| Storage, stock, shipping | 300 ft² gross = 27.9 m² | shop stores |
| Business (offices above) | 100 ft² gross = 9.29 m² | see office research |
| Residential (apartments above) | 200 ft² gross = 18.58 m² | |

Example: three shops of 60 m² → 180 m² + support ≈ 40–50 people on the ground
storey: two exits needed (more than 49), which the shops' own street doors give.

## Shops and showrooms

| Item | Value | Source / basis |
|---|---|---|
| Shop minimum area | **24 m²** | Saudi municipal rule as reported in the press [S5] (an older rule; confirm with the Amanah) |
| Shop minimum width (street frontage) | **4 m** | same [S5] |
| Shop depth | about 2–4 × frontage (12–16 m typical for 4–5 m units) | practice |
| Showroom | ≥ 50 m², frontage ≥ 6 m | practice (car and furniture showrooms) |
| Shop store | behind its shop, entered only from it; ≥ 4 m², ≥ 1.5 m wide | practice |
| Mezzanine | allowed only where the Amanah permits, connected directly to the shop below [S5] | not modelled |
| Parking | **1 space per 45 m² of shops, at least one per shop** | municipal practice reported in the press [S5] |
| Where shops open | onto the **commercial street** only; not onto residential streets (except a residential street 15 m wide or more, with the Amanah's approval) [S5] | |

The pack's `program_text` states the computed parking count for the planner but
does not check parking geometry (plot rules own the site).

## Mixed use: separation of uses

- **Separate entrances.** The residential-commercial rules require the
  residential entrance to be separate from the commercial or office entrance
  [S3]. The pack requires a `residential_lobby` on the facade on the ground
  storey that reaches the upper stairs and lift through circulation only.
- **No passage through a shop.** Nobody reaches an upper floor through a shop;
  no shop opens onto the residential lobby, the stairs or the lift.
- **Shops below homes.** Shops sit on storeys below every apartment storey; a
  shop on or above an apartment storey is an error.
- **Fire separation.** Between a mercantile storey and dwellings above, IBC
  2015 Table 508.4 requires a fire barrier and horizontal assembly, 2 h
  unsprinklered and 1 h sprinklered for R next to M (cited from the IBC table,
  not re-read in this session). ACS does not model ratings; the program text
  says the engineer sets it.
- **Apartments above** need a kitchen and a bathroom per `unit_id` and a living
  room or bedroom; habitable rooms at least **6.5 m² and 2.13 m (7 ft)** wide,
  IRC 2015 R304 [S6], the same 6.5 m² / 2.1 m the Saudi villa rules give for a
  worker's bedroom [S7]. The inside of each apartment stays the residential
  pipeline's job; the pack checks only these interface rules.

## Corridors, stairs, exits, travel

As in the office research (IBC 2015 chapter 10): corridors 1118 mm (914 mm
below 50 people); stairs 1118 mm per flight plus 7.6 mm per occupant;
exits per storey 2 / 3 / 4 by 500 / 1000; Group M single exit on the first
storey up to 49 people and the second up to 29; exit access travel **200 ft =
61 m** unsprinklered, **250 ft = 76 m** sprinklered (Group M); dead ends 6.1 m
(15.2 m sprinklered).

**Apartment storeys** (R-2): one exit is allowed for up to **4 dwelling units**
per storey on the first to third storeys above grade, in a sprinklered building
with emergency escape openings and a common path of 125 ft (IBC 2015 Table
1006.3.2(1), read verbatim [S1]). The pack applies that count; sprinkler status
and escape openings remain the engineer's check.

## Toilets (IPC 2015 Table 403.1, read verbatim [S2])

- Mercantile: **WC 1 per 500** of each sex, lavatory 1 per 750, drinking
  fountain 1 per 1000; separate facilities are **not required up to 100
  people** in mercantile (403.2 exception 3). In practice each Saudi shop gets
  its own small WC inside its store.
- Offices above: business ratios (office research). The pack adds the two
  groups' requirements and compares them with every non-apartment toilet room.

## Adjacency and zoning summary

Street facade: shopfronts, the residential lobby door. Behind the shops: their
stores and WCs, a service corridor for deliveries and refuse where the plot
allows. Core (stairs, lift) reached from the residential lobby. Upper storeys:
apartments around a stair landing, each through its own entrance corridor; or
office floors planned with the office pack.

## What the pack checks (`acs_typology_retail.check`)

Errors: no shop; shop or showroom below area or width; street frontage under
4 m (6 m showroom) on the stated street sides; shop on or above an apartment
storey; no separate facade entrance for the upper storeys; upper stairs reached
only through a shop; a shop door into the residential lobby or the core; a
store not reached from its shop; an apartment without kitchen, bathroom or
living room; core missing or misaligned; exits, corridor and stair widths;
fixtures. Advisories: the sprinkler-dependent limits while sprinklers are
unknown; office rooms without windows.

## Verification status

Read verbatim: IBC 2015 chapter 10 and IPC 2015 chapter 4. Press or portal
summaries (search, not the documents): shop 24 m² / 4 m, parking 1 per 45 m²,
shops on the commercial street, separate entrances. Not re-read: IBC Table
508.4. These municipal rules vary by Amanah and edition; the integration plan
makes them editable inputs like the plot rules.

## Sources

- [S1] IBC 2015 Chapter 10: https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress
- [S2] IPC 2015 Chapter 4: https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings
- [S3] SCBC Istitlaa, MoMAH residential building requirements (separate residential and commercial/office entrances): https://istitlaa.scbc.gov.sa/ar/Municipality/momra/residential/Pages/default.aspx
- [S4] Al-Madina, residential-commercial coverage limits: https://www.al-madina.com/article/874378
- [S5] Jehat, sixteen conditions for residential-commercial buildings (coverage, shops on the commercial street, shop 24 m² and 4 m, 1 space per 45 m²): https://jehat.net/?act=artc&id=113173
- [S6] Seattle SDCI note on IRC 2015 R304 habitable room size: https://www.seattle.gov/documents/Departments/SDCI/Codes/2015SRC3041HabitableRoomSize.pdf
- [S7] Arab News on the villa regulations (worker bedroom 6.5 m², 2.1 m): https://arabnews.com/node/2550786/amp
- [S8] IBC 2015 Chapter 5, Table 508.4 (separated occupancies): https://codes.iccsafe.org/content/IBC2015/chapter-5-general-building-heights-and-areas
- [S9] Saudi Engineers guidelines for SBC 1101/1102 (R3 residential): https://saudieng.sa/English/RegulationsAndProcedures/Pages/SBCGuidelines.aspx
