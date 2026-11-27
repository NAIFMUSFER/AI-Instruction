# Hotel: planning research for the ACS instruction pack

Status: research for `acs_typology_hotel.py`; not wired into generation or
review (see `typologies_integration_plan.md`). Lowest priority of the five
typologies; the official room-area-per-star table could not be read in this
session, so room areas are an owner-editable input.

## Saudi context

- Hotels are licensed and classified by the **Ministry of Tourism** (MT)
  under the hospitality facilities regulations; the classification criteria set
  minimum standard-room areas **including the bathroom** for two adults in
  tiers of **16, 18, 22 and 30 m²**, suites from **32 m²**, bathrooms from
  **3 m²**; balconies and terraces do not count [S1]. The mapping of tiers to
  star categories was not legible in the extracted criteria. A third-party
  guide gives different, bathroom-excluded figures (16 / 22 / 28 / 36 m² for
  1 / 3 / 4 / 5 stars) [S5]; the pack does **not** use it.
- Heritage hotels: standard room ≥ 20 m² with bathroom, suite ≥ 32 m²,
  bathroom ≥ 4 m² [S4].
- The building code side is SBC 201 (IBC 2015 base): hotels are Group **R-1**.

The pack's `ROOM_MIN_M2` maps stars 1–5 to 16 / 18 / 22 / 30 / 30 m² as a
**labelled planning assumption** (an ordering of the published tiers), and
`room_min_m2` lets the owner state the class area directly; with neither, rooms
are planned at **22 m²** (mid-scale).

## Occupant load (IBC 2015 Table 1004.1.2, read verbatim [S2])

| Space | Factor |
|---|---|
| Guest floors (residential) | 200 ft² gross = **18.58 m²/person** |
| Restaurant, lounge, meeting (tables and chairs) | 15 ft² net = 1.39 m² |
| Commercial kitchen | 200 ft² gross = 18.58 m² |
| Offices | 100 ft² gross = 9.29 m² |
| Prayer room | 7 ft² net = 0.65 m² |
| Linen, luggage, storage | 300 ft² gross = 27.9 m² |

## Guest room as a unit

A guest room is a **unit**: its bedroom (`guest_room` or `suite`) and its
en-suite `bathroom` carry the same `unit_id`, the convention the residential
pack uses for an apartment. The bathroom touches its room and opens only into
it; the room opens onto the guest corridor and has a window on an exterior
wall. IPC 2015 Table 403.1 requires for R-1 hotels **one WC, one lavatory and
one bath or shower per sleeping unit** [S3].

| Role | Min | Notes |
|---|---|---|
| guest_room | 12 m² bedroom part, **3.3 m** wide; room + bathroom ≥ class area (22 m² default) | exterior wall required; no door to kitchen or linen room |
| suite | 24 m² bedroom part, 3.6 m; suite + bathroom ≥ **32 m²** | |
| bathroom | **3 m²**, 1.5 m wide | MT minimum; entered only from its room |
| linen_room | 4 m², 1.8 m | on every guest floor beside the service lift (practice) |
| lobby | 40 m², 5 m | on the street |
| reception | 9 m² | beside the lobby |
| luggage_room | 4 m² | beside lobby or reception |
| restaurant / kitchen | 40 / 20 m² | kitchen on a service corridor |
| toilet_male / toilet_female (public) | 3 m² | near lobby and restaurant |
| corridor | 1118 mm code; **1.8 m** practice for double-loaded guest corridors (1.8–2.4 m) [S6] | |
| stairs / elevator / service_elevator | 12 m², 2.4 m / 3.2 m² / 3.6 m² | stacked with the same rect and `core_id` |

Typical guest bay: 3.6 m room width + 1.8 m bathroom = 5.4 m per unit; 6.6 m
deep on each side of a 1.8 m corridor (the compliant fixture uses this: room
23.8 m² + bathroom 7.2 m² = 31 m²). Guest floors are typically 65–85 % of the
hotel's area [S7].

## Exits, corridors, travel (IBC 2015, read verbatim [S2])

- R-1 single exit only for a first storey of up to **10** people; every guest
  floor needs **two stairs**, separated by 1/2 of the diagonal (1/3
  sprinklered).
- Corridors 1118 mm (914 mm below 50 people); stairs 1118 mm per flight.
- Exit access travel R: **200 ft = 61 m** unsprinklered, **250 ft = 76 m**
  sprinklered; common path in R-1 75 ft sprinklered (not measured by ACS);
  dead ends 6.1 m (15.2 m sprinklered R-1).

## Public toilets

Restaurant and banquet spaces (A-2): **WC 1 per 75** of each sex, lavatory
1 per 200 [S3]. The pack sizes public toilets on the restaurant, lounge and
meeting load and checks they are within one storey of those rooms.

## Zoning

Front of house (lobby, reception, luggage, restaurant, prayer room, public
toilets) on the street; back of house (kitchen, staff, stores) on a service
corridor and service lift, out of guests' sight; guest floors repeated as one
template, cores stacked; a linen room and the service lift together on each
guest floor; at least one guest lift from three storeys up (error).

## What the pack checks (`acs_typology_hotel.check`)

Errors: missing lobby or reception; a guest room without `unit_id`, without its
own bathroom, or below the class area (32 m² for suites); a bathroom opening
anywhere but into its own room; guest room without an exterior wall; fewer
rooms than confirmed; no guest lift from three storeys; table sizes; core,
exits, widths; public WCs short. Advisories: no linen room on a guest floor;
guest corridor under 1.8 m; back-of-house rooms below practice sizes; the
sprinkler-dependent limits while sprinklers are unknown.

## Verification status

Read verbatim: IBC 2015 chapter 10, IPC 2015 chapter 4. From search summaries of
the MT criteria PDFs: the 16/18/22/30 m² tiers, 32 m² suites, 3 m² bathrooms
(star mapping unknown). From a trade article: heritage hotel figures. Before
shipping the hotel pack, read MT `hotels-classification-criteria-en-v03.pdf`
and replace `ROOM_MIN_M2` with its per-star rows.

## Sources

- [S1] Ministry of Tourism, hotels classification criteria (v03): https://cdn.mt.gov.sa/mtportal/mt-fe-production/content/policies-regulations/documents/classification-criteria/hotels-classification-criteria-en-v03.pdf ; 2022 edition: https://cdn.mt.gov.sa/mtportal/mt-fe-production/content/policies-regulations/documents/tourist_accommodation/hotels/Hotels_Classification_Criteria_20220628_En.pdf
- [S2] IBC 2015 Chapter 10: https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress
- [S3] IPC 2015 Chapter 4: https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings
- [S4] Hotelier Middle East on Saudi heritage hotel inspections (20 m², suites 32 m², bathroom 4 m²): https://www.hoteliermiddleeast.com/saudi-arabia/can-your-guestroom-design-pass-saudis-heritage-hotel-inspection
- [S5] Daranan blog, SCTH classification requirements (not used; conflicts with MT): https://daranan.com/blog/scth-hotel-classification-requirements-saudi-arabia/
- [S6] Four-star hotel design standards (double-loaded corridor 1.8–2.4 m; student compilation): https://fr.slideshare.net/yasminebannoura/4-star-hotels-design-standards
- [S7] Design guide for hotels (guest floors 65–85 % of the area), Scribd copy: https://www.scribd.com/doc/269116558/7151503-Design-Guide-for-Hotels
