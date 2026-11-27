# Mosque: planning research for the ACS instruction pack

Status: research for `acs_typology_mosque.py`; not wired into generation or
review (see `typologies_integration_plan.md`). The main Saudi source is the
mosque design guide series published with the Saudi Building Code (Guide 4:
architectural requirements, amenities and supplements) [S1], read in this
session from its PDF. Its text states that the Saudi Building Code prevails
where the two differ. Numbers below are planning references; the final qibla
is set on site by survey, and the Ministry of Islamic Affairs (MoIA) licenses
every mosque [S1].

## Orienting the prayer hall to the qibla

### 1. The qibla bearing

The qibla is the **initial great-circle bearing** from the site to the Kaaba
(21.4225° N, 39.8262° E), in degrees clockwise from **true** north [S6]:

```
θ = atan2( sin Δλ · cos φk ,  cos φs · sin φk − sin φs · cos φk · cos Δλ )
    φs, λs: site latitude and longitude; φk, λk: the Kaaba; Δλ = λk − λs
```

`qibla_bearing(lat, lon)` implements it. With city-centre coordinates:

| City | Bearing (true) | Nearest plan wall on a north-aligned plot | Row angle |
|---|---|---|---|
| Riyadh (24.71 N, 46.68 E) | **243.8°** (sources quote 244.5–244.7° for other points in the city [S7]; "about 245°") | W | 26.2° |
| Dammam | 244.1° | W | 25.9° |
| Jeddah | 101.1° | E | 11.1° |
| Madinah | 176.2° | S | 3.8° |
| Abha | 322.3° | N | 37.7° |
| Tabuk | 156.3° | S | 23.7° |

Within a city the bearing changes by about a degree from one district to the
next, so the pack takes, in order: a stated bearing, the site's coordinates,
then the named city's centre (`CITY_COORDS`, approximate). Mecca itself is left
out: around the Haram the direction changes with every plot.

### 2. From true north to the plot's north

ACS plans on the plot's own axes: x east, z south, `z = 0` the north facade,
`meta.north = "-Z"`. A real plot is rarely aligned with true north. Let
**α = the true bearing of the plot's own north** (its −z axis), clockwise
positive. The qibla in plot terms is:

```
β = θ − α                       (bearing relative to the plot's north)
plan vector (dx, dz) = (sin β, −cos β)        x east, z south
```

The **qibla wall** of the prayer hall is the side whose outward normal is
nearest to β: N (0°), E (90°), S (180°) or W (270°). The **residual**
`r = β − normal` (−45° … +45°) is the angle at which the prayer rows (saff
lines in the carpet) are marked across a hall whose walls follow the plot
(`qibla_edge(bearing, plot_north)`).

Worked examples for Riyadh (θ = 243.8°):

- North-aligned plot (α = 0): β = 243.8° → qibla wall **W**, rows at **26.2°**
  (counter-clockwise from the west normal, toward the south-west).
- Plot turned 26.2° west (α = −26.2°): β = 270° → wall W, rows parallel to it.
- Plot turned 90° (its north points east, α = 90°): β = 153.8° → wall **S**,
  rows at 26.2°.

What α must be: the plot's north **in true terms**. A Saudi survey plan gives
grid north (UTM, zone 37 or 38) or magnetic north. Grid convergence in Riyadh
is about **0.7°** (UTM 38N, central meridian 45° E: γ ≈ (λ − λ0)·sin φ); magnetic
declination is a few degrees east and changes yearly (take it from the NOAA
World Magnetic Model for the site and date [S8]). Both are small next to the
row angle but must not be confused.

### 3. What ACS can draw, and the Saudi rule

The Saudi guide asks for **the prayer hall to face the qibla, not necessarily
the rest of the mosque**, which may follow the street grid (Guide 4, §4-5-5 and
figure 4-14) [S1]. ACS rooms are axis-aligned rectangles (a polygon is an
unsupported space), so a hall cannot be rotated. The pack therefore:

1. puts the hall's **long side on the qibla wall** (the guide prefers the hall
   elongated along the qibla wall so the front rows are longest, §4-4-2-1);
2. puts the **mihrab** outside the middle of that wall, axial with the main
   entrance on the opposite wall (§4-7-7);
3. reports the residual angle: under 15° the rows are simply marked at that
   angle; above 15° an advisory recommends rotating the hall in design
   development (Riyadh on a north-aligned plot: 26°).

The planner receives the wall as data (`program_text`), never computes it.

## Capacity and occupant load

| Item | Value | Source |
|---|---|---|
| One worshipper in a row | **1.2 m deep × 0.6 m wide = 0.72 m²** | mosque design regulations [S2] |
| Hall net area | worshippers × 0.72 m² (250 men → 180 m²) | |
| Egress load (assembly, chairs only/standing) | 7 ft² net = **0.65 m²** | IBC 2015 T1004.1.2 [S3] |
| Women's hall when no number is stated | ≥ **15 %** of the men's hall | Abu Dhabi mosque regulations, press summary [S5] (advisory) |
| Highway mosques | designed for about 100 men and 50 women | Guide 4 §4-6-3 [S1] |
| Clear interior height of the hall | **≥ 3 m**; the hall height in proportion to its length with a 17° sight line | Guide 4 §4-4-2 [S1] |

## Room program (the pack's `ROOM_TABLE`)

| Role | Min | Rule | Source |
|---|---|---|---|
| prayer_hall | 36 m², 6 m wide | long side on the qibla wall; no door to toilets | [S1][S2] |
| women_prayer_hall | 12 m², 3.6 m | own entrance; no door to men's rooms; hears the imam | [S1] |
| mihrab | **1.5 m wide × 2 m deep** (3 m²) | outside the middle of the qibla wall | Guide 4 §4-7-7-1 |
| imam_room | **6 m²** (3 × 2 m) | touches the mihrab or the front of the hall so the imam reaches the minbar without crossing rows; own outside door | §4-7-3 |
| imam_wc | **2 m²** with a basin | entered from the imam room | §4-7-3 |
| wudu_male / wudu_female | 6 / 4 m² | one place per **25** worshippers; taps **≥ 0.8 m** apart; women's ablution separate and linked to the women's hall | §4-7-9-5, §4-7-9-1 |
| toilet_male / toilet_female | 2.5 m² | **one WC per 50 worshippers** in residential districts, **per 40** in commercial areas; cubicle ≥ **1.0 × 1.5 m**; one basin per 3 WCs; two ablution taps per WC; one western WC per 3 squat WCs | §4-7-9-1 |
| shoe_area | 4 m² | benches at the line between the unclean and clean zones | §4-5-3 |
| entrance / women_entrance | 6 / 4 m² on the facade | separate, safe women's entrance close to but screened from the men's | §4-5-6, §4-6-3 |
| library | **9 m²** local mosque, **16 m²** jami | | §4-7-5 |
| lesson_hall | **20 m²** where needed in large jami | | §4-7-6 |
| storage | furnishings **6 m²**, Qurans **4 m²**, cleaning **3 m²** | doors open outward | §4-7-4 |
| minaret | 2.2 m wide footprint (inner stair ≥ **0.8 m**, spiral preferred) | the guide gives a 1:3 height ratio between the minaret and the facade (with parapet), subject to building rules; ACS does not check heights | §4-7-8 |
| imam_residence | in the unclean zone | §4-5-3 |

Planning quantities (`requirements_for`): 250 men and 40 women in a residential
district → hall 180 m², women 28.8 m², **10 + 2 ablution places**, **5 + 1 WCs**,
2 basins. The guide's WC ratio is stricter than IPC 2015 for places of worship
(1 WC per 150 men, 1 per 75 women [S4]); the pack uses the guide's.

Capacity of drawn rooms: worshippers = floor(hall area ÷ 0.72); ablution places
from `objects` of kind wudu/ablution/tap, else area ÷ 1.5 m² (0.8 m of bench
by about 1.9 m with the passage behind); WCs from toilet objects, else area ÷
2.5 m².

## Zoning and adjacency

- **Clean zone**: prayer halls, ablution, library, imam's office. **Unclean
  zone**: toilets, the imam's residence. Benches for shoes on the line between
  them (§4-5-3). The pack forbids a toilet door into a prayer hall and any
  toilet or ablution room on the hall's **qibla wall** (Saudi practice; error).
- **WC orientation**: toilets are placed perpendicular to the qibla
  (§4-7-9-1-2), i.e. a user neither faces nor turns their back to the qibla.
  Fixture direction is an object-stage concern; the openings text states it.
- **Women**: own entrance, ablution and toilets reached without crossing any
  men's room; full audio and partial visual connection with the men's hall; a
  waiting room for children by the women's hall in highway mosques (§4-6-3).
- **Main entrance** on the wall opposite the qibla, axial with the mihrab;
  side exits; doors open outward (§4-3-2-23).
- **Windows** on the two side walls of the hall (§4-4-2), none on the qibla
  wall; high windows in toilets and ablution rooms for privacy (§4-7-9-1-4).
- **Parking**: imam and muezzin spaces; accessible spaces within 30 m of the
  main entrance (§4-5-4). Site-level, outside the room checks.

## Egress

The hall is an assembly space without fixed seats: 0.65 m² net per person for
the exit count. 250 + 40 worshippers ≈ 350 people → **2 exits** (3 above 500);
exits may be the hall's own exterior doors. Assembly single exit only up to 49;
exit separation 1/2 of the diagonal (1/3 sprinklered); travel 200 ft = 61 m
(250 ft = 76 m sprinklered) [S3].

## What the pack checks (`acs_typology_mosque.check`)

Errors: missing hall, mihrab, imam room, men's ablution, toilets or entrance (and
the women's set unless `women_section` is false); mihrab on a wall other than
the qibla wall, or off its centre by more than 10 % of the wall; a toilet or
ablution room behind the qibla wall; hall lower than 3 m; hall or women's hall
below the stated capacity; ablution places or WCs below the ratios; the women's
hall reached only through men's rooms, or women's ablution and toilets cut off
from it; toilet doors into a hall; core, exit and width checks. Advisories:
qibla unknown (no city, coordinates or bearing); plot north assumed true north;
rows angled more than 15°; hall deeper than its qibla wall; women's hall below
15 % when no number is stated; no shoe area.

## Verification status

Read this session: the Guide 4 PDF (text extracted; some lines were stored
right-to-left and were decoded by reversing them; the guide's figures, such as
the men-to-women hall ratio in figure 4-9, were not readable), IBC 2015 chapter
10 and IPC 2015 chapter 4. From search summaries: the 1.2 × 0.6 m row module,
the Abu Dhabi 15 % for women and 1.85 m² of prayer space per worshipper (a
far larger allowance than the 0.72 m² row module; the pack does not use it), the
Riyadh bearings. Not
reachable: MoIA's own mosque standards and Guide 3 (urban planning) PDF.

## Sources

- [S1] Mosque design and development guides with the Saudi Building Code, Guide 4: architectural requirements, amenities and supplements (hosted by the Abdullatif Al-Fozan Award): https://alfozanaward.org/wp-content/uploads/2024/12/4-الدليل-الرابع-الاشتراطات-المعمارية،-والكماليات-والمكملات.pdf ; Guide 3 (urban planning): https://alfozanaward.org/wp-content/uploads/2024/12/3-الدليل-الثالث-اشتراطات-التخطيط-العمراني.pdf
- [S2] Mosque general design regulations (1.2 m × 0.6 m per worshipper): https://www.scribd.com/doc/76445468/Mosque-General-Design-Regulations
- [S3] IBC 2015 Chapter 10: https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress
- [S4] IPC 2015 Chapter 4 (places of worship 1 per 150 men, 1 per 75 women): https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings
- [S5] The National, Abu Dhabi mosque design rules (1.85 m² per worshipper; ≥ 15 % for women): https://www.thenationalnews.com/uae/all-mosques-must-meet-new-design-rules-says-abu-dhabi-1.465521 ; regulations volume 1: https://dmt.gov.ae/-/media/Project/DMT/DMT/E-Library/10-24/02/Abu-Dhabi-Mosque-Development-Regulations---Volume-1--Planning-Ar.pdf
- [S6] Qibla (definition, great-circle direction): https://en.wikipedia.org/wiki/Qibla
- [S7] Riyadh qibla 244.5° (ihadis) and 244.67° (timesprayer): https://dev.ihadis.com/en/qibla-direction/saudi-arabia/riyadh ; https://timesprayer.com/direction-qibla-riyadh.html
- [S8] NOAA World Magnetic Model 2025: https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ngdc:WMM2025/html
