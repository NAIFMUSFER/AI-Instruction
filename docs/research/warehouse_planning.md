# Warehouse planning: research, audit and the values ACS uses

Date: 27 November 2026. Scope: the connected-workspace warehouse planner
(`acs_warehouse_generation.PLANNING_SYSTEM`), the warehouse pipeline in
`acs_workspace_service.generate_plan_candidate`, the legacy warehouse prompt in
`acs_understand.py`, dock reading in `public/app/core/brief-program.mjs`, and the
new deterministic module `warehouse_planning.py`.

## ملخص بالعربية

- خطة المستودع في مساحة العمل كانت مناطق فقط: لا أرصفة، ولا نوع مبنى في `meta.type`، فكان كل متطلب «عدد الأرصفة» يفشل في المراجعة مهما كان المخطط.
- صار المخطط (الذكاء الاصطناعي) يحدد لكل منطقة أرصفة الواجهة وعدد الأبواب فقط، ويرتّب الخادم الأبواب حتميًا ومجانًا: باب 3 × 3 م بتباعد مراكز 4 م (لا أقل من 3.66 م) على الجدار الخارجي، ثم يزيح المبنى لتبقى ساحة شاحنات بعمق 35 م داخل الأرض عند الإمكان.
- أضيفت ملاحظات مراجعة استشارية موثّقة المصدر لا تمنع الاعتماد: عمق التجهيز (16 م)، ساحة الشاحنات (35 م)، تباعد الأرصفة، طول واجهة الأرصفة، الارتفاع الصافي (6 م)، حد أدنى لمسافة الهروب (76 م)، عرض ممرات البالتات (2.4 م)، والخلوص تحت الرشاشات (0.46 م).
- صُححت قيم خاطئة في التعليمات القديمة: باب الرصيف 3.5–3.7 × 4.0–4.5 م (مقاس باب دخول أرضي)، ومساحة مناورة 12 م (الصحيح نحو 35 م)، و«4 مخارج» و«6 كاميرات» أعداد مخترعة.
- قراءة الوصف: «و4 أرصفة» لم تكن تُقرأ، و«6 أرصفة استلام و8 أرصفة شحن» كانت تُقرأ 6 بدل 14.

## 1. Method and limits

Sources were found with web search on 27 November 2026. This session's network
blocked direct page fetches (ritehite.com, mhi.org) and the Firecrawl account had no
credits, so each value below rests on the search engine's quoted passages from the
listed pages. Code values are taken from US model-code text adopted by states (for
example Washington WAC 51-54A, which reprints the IBC), ICC training material and
interpretations. The SBC 201 and SBC 801 texts and the numeric tables of the Saudi
warehouse requirements (MOMAH, 1446 H) were not reachable; where a Saudi value is
needed the IBC value is used and marked as such. Every number here is a planning
default for a concept plan, not a design or compliance value.

## 2. Flow and layout

| Topic | Finding | Source |
|---|---|---|
| U-flow | Receiving and shipping on one side share dock resources and yard; less space for staging; risk of congestion when the U is narrow. | [G2](https://learn.g2.com/warehouse-layout), [Shopify](https://www.shopify.com/blog/warehouse-design) |
| I-flow (through) | Receiving and shipping on opposite walls, storage between; suits high volume and cross-docking; longer travel and two dock walls/yards. | same |
| Cross-dock DCs | Standard for large bulk DCs; truck courts on both long sides. | [LoopNet](https://loopnet.com/learn/3-warehouse-types-for-e-commerce-distribution/2061349385), [CCIM study guide](https://open-exam-prep.com/study-guides/ccim/ch8-commercial-sectors/industrial-market-analysis) |
| Cross aisles | Equally spaced cross aisles cut travel time; three is a reasonable default when aisle count and length are unknown. | [Sabancı University study](https://research.sabanciuniv.edu/id/eprint/7186/1/AU8518_C005.pdf) |

No authoritative source was found for office placement; ACS keeps the common
practice of a compact office/staff block at the personnel entrance, away from dock
walls and truck traffic, as a planner default only.

## 3. Docks, staging and the truck court

| Item | Value | Source |
|---|---|---|
| Dock door opening | 9 ft wide x 10 ft high most common; 8-10 ft wide range (2.44-3.05 m x 3.05 m) | [Blue Giant door size](https://www.bluegiant.com/architects/planning-and-design/door-size/), [Rite-Hite pt 1](https://www.ritehite.com/en/AM/News/2012/Blog/Loading-Dock-Design-Pt1) |
| Door centres | At least 12 ft (3.66 m), commonly 12-14 ft (3.66-4.27 m); 12 ft fits a 10 ft truck with mirrors | Rite-Hite pt 1, [MMH](https://www.mmh.com/article/loading_dock_best_practices_make_their_mark/Rite-Hite) |
| Dock height | 48-52 in (1.22-1.32 m) common; 44-55 in range | [Blue Giant guide 2026](https://www.bluegiant.com/getmedia/367f0058-ec36-41ba-b0c2-93afb9367d51/Blue-Giant-Dock-Design-Guide-2026.pdf), [Miner](https://www.minercorp.com/?p=25491) |
| Leveler length | 6 or 8 ft (1.8-2.4 m) | [Pentalift](https://www.pentalift.com/solutions_category/mechanical-size-and-capacity-options/) |
| Approach (apron) | 2 x longest tractor-trailer + 5-15 ft (ATA rule); 75 ft rig at 12 ft centres gives 165 ft | [Rite-Hite pt 2](https://ritehite.com/en/am/news/2012/blog/loading-dock-design-pt2) |
| Apron for a GCC/EU 16.5 m articulated truck | 2 x 16.5 + 1.5-4.5 = **34.5-37.5 m** (own arithmetic) | from the rule above |
| Truck court practice | 120 ft (36.6 m) minimum for semi-trailers; 185-200 ft (56-61 m) for bulk cross-docks; ~1 extra trailer stall per door | [Link Logistics](https://www.linklogistics.com/news-insights/industrial-real-estate-101/what-is-a-loading-dock-a-guide-to-types-configurations-and-key-features/), CCIM study guide, [Cushman & Wakefield](https://www.cushmanwakefield.com/en/united-states/insights/us-articles/the-industrial-spec-sweet-spot-what-tenants-want) |
| Interior staging | 53-57 ft (16.2-17.4 m) to floor-drop one trailer load; big-box DCs 75 ft (22.9 m) | Rite-Hite pt 2 |
| Speed bay | Column-free 60 ft (18.3 m) from the dock wall to the first column line; older buildings 30 ft | [Bays and column spacing](https://red-pufferfish-xgpt.squarespace.com/blog/2016/12/07/bays-and-column-spacing), [AK Equipment](https://www.akequipment.com/warehouse-design-starting-with-the-dock-area/) |
| Saudi practice | Loading and unloading areas must be inside the plot without obstructing truck entry/exit; loading positions per a table, allowed in setbacks or inside the warehouse | [MOMAH warehouses and stores requirements, 1446 H](https://momah.gov.sa/sites/default/files/2025-04/ashtratat%20almstwd%60at%20walmkhazn.pdf), [NCC consultation](https://istitlaa.ncc.gov.sa/ar/Municipality/momra/warehouses/Pages/Article_004.aspx) |
| Saudi setbacks (unofficial) | Front 6 m, side 3 m, rear 2-3 m by hazard class (commercial blog, not verified against MOMAH) | [Hayaza](https://hayaza.sa/blog/warehouse-workshop-building-requirements) |

## 4. Storage, aisles and height

| Item | Value | Source |
|---|---|---|
| Counterbalance aisle | About 12 ft (3.66 m) for conventional rack; at least 10.5 ft (3.2 m) to turn | [OSHA eTool](https://osha.gov/etools/powered-industrial-trucks/workplace/narrow-aisles), [Toyota](https://www.toyotaforklift.com/blog/do-more-with-less-narrow-aisle-forklifts) |
| Reach truck aisle | 8.5-10.5 ft (2.6-3.2 m); down to 96 in (2.44 m) | Toyota, [MHL (Hyster)](https://www.mhlnews.com/powered-vehicles/narrow-aisle-form-follows-lift-truck-function) |
| Very narrow aisle (guided) | 5-7 ft (1.5-2.1 m); vendors quote down to 50 in | Toyota, [AK Equipment](https://www.akequipment.com/?p=2298) |
| Aisle width method | Take it from the truck's turning and load geometry, not a rule of thumb | [Cisco-Eagle](https://www.cisco-eagle.com/blog/2013/05/31/key-considerations-for-warehouse-aisle-widths/) |
| Selective rack frame | Frame depth = pallet depth - 6 in (48 in pallet -> 42 in frame); 1200 mm pallets -> about 1.07 m | [Rack design guide](https://www.cisco-eagle.com/uploads/SK-General-Rack/RackDesignGuide.pdf) |
| Beam length | Two 1200 mm loads need about 2.7-2.8 m between uprights (108 in beam) | [Interlake Mecalux guide](https://www.cisco-eagle.com/uploads/Interlake-Mecalux/Selective_Pallet_Rack_Brochure.pdf) |
| Rack to building | Down-aisle clearance 5 % of rack height, cross-aisle 2 % | [Cisco-Eagle clearances](https://www.cisco-eagle.com/blog/2021/05/11/pallet-rack-clearances-lateral-vertical-and-building-structures) |
| Clear height | 36-40 ft (11-12.2 m) for institutional bulk DCs (5-6 rack tiers); 28-32 ft (8.5-9.8 m) in smaller/older stock | CCIM study guide, [RE Business](https://rebusinessonline.com/a-new-era-for-industrial-design/) |
| Sprinkler clearance | 18 in (0.46 m) between deflector and top of storage; 36 in (0.91 m) for ESFR | [OSHA on NFPA 13](https://osha.gov/laws-regs/standardinterpretations/2008-09-29), [Minnesota SFM](https://dps.mn.gov/divisions/sfm/fire-code/Documents/Fire-Code-Interpretations/Rolling-File-Cabinets.pdf) |
| High-piled storage | Combustibles stored above 12 ft (3.66 m) fall under IFC chapter 32 (SBC 801 counterpart) | [ICC high-piled storage](https://iccsafe.org/wp-content/uploads/High-Piled-Combustiable-Storage.pdf) |

## 5. Area ratios

| Ratio | Value | Source |
|---|---|---|
| Aisles in a selective-rack layout | 40-50 % of floor area | [Doss capacity planner](https://www.doss.com/tools/warehouse-capacity-planner) |
| Racks plus aisles | up to about 80 % of floor area | [Cisco-Eagle space efficiency](https://www.cisco-eagle.com/blog/2014/08/18/how-to-measure-and-improve-industrial-storage-space-efficiency) |
| Peak utilisation | about 75 % of space in an average US warehouse | [Plant Engineering](https://www.plantengineering.com/articles/best-practices-space-utilization) |
| Cubic utilisation | 70-85 % good for selective racking; below 55 % signals waste | Doss |
| Capacity rule of thumb | 50,000 sq ft at 30 ft clear: 4,000-6,000 pallet positions | Doss |

Planning consequence: in a typical DC most of the indoor area belongs to the storage
zone (racks plus their aisles); dock staging, packing, offices and amenities take the
remainder. ACS does not turn these ratios into checks because the brief's program
and the confirmed target area already allocate the area.

## 6. Structure

Column grids of about 50 x 54 ft (15.2 x 16.5 m) or 52 x 50 ft with 60 ft (18.3 m)
speed bays along the dock walls (CCIM study guide; broker listings in the search).
Saudi warehouses are often pre-engineered steel frames; no Saudi grid standard was
found. ACS plans zones, not columns, and adds no grid check.

## 7. Fire and egress (IBC; SBC 201/801 are derived from the I-Codes)

SBC 201 (2018) is based on the 2015 International Building Code with Saudi changes
([MLIT](https://www.mlit.go.jp/common/001404290.pdf),
[ICC](https://shop.iccsafe.org/2018-saudi-building-code-sbc-201-study-companion.html));
SBC 801 on the 2015 IFC and NFPA standards
([ASRJETS](https://asrjetsjournal.org/American_Scientific_Journal/article/download/11808/2855/28128)).
The metric values below are conversions of the IBC values, not quotations of SBC.

| Item | IBC value | Metric | Source |
|---|---|---|---|
| Exit access travel, S-1 (moderate hazard storage) | 200 ft / 250 ft sprinklered | 61 / 76 m | [WAC 51-54A-1017](https://lawfilesext.leg.wa.gov/Law/WAC/WAC%20%2051%20%20TITLE/WAC%20%2051%20-%2054A%20CHAPTER/WAC%20%2051%20-%2054A-1017.htm) |
| Exit access travel, S-2 (low hazard) | 300 ft / 400 ft sprinklered | 91 / 122 m | same |
| S-1/F-1 increase (1017.2.2) | 400 ft when one storey, >= 24 ft floor to ceiling/deck, fully sprinklered (903.3.1.1) | 122 m, 7.3 m | [BOAF interpretation](https://interpretations.boaf.net/view/8089), [CSE](https://www.csemag.com/the-ibcs-modification-to-exit-access-travel-distance/) |
| Smoke removal | Vents or mechanical smoke removal for S-1/F-1 over 50,000 sq ft (910) | 4,645 m2 | CSE |
| Common path, S sprinklered | 100 ft | 30 m | [ICC 2012 excerpts](https://iccsafe.org/wp-content/uploads/ahc/2012CodeExcerts.pdf) |
| Exit separation (1007.1.1) | >= 1/3 of the area's diagonal when sprinklered, 1/2 otherwise | | [ICC BU 21-86-22](https://www3.iccsafe.org/cs/committeeArea/pdf_file/BU_21_86_22.pdf) |
| Occupant load factor | Warehouses 500 sq ft gross per person | 46.5 m2 | [WAC 51-54A-1004](https://lawfilesext.leg.wa.gov/Law/WAC/WAC%20%2051%20%20TITLE/WAC%20%2051%20-%2054A%20CHAPTER/WAC%20%2051%20-%2054A-1004.htm) |
| Egress capacity | 0.2 in/occupant non-stair (0.15 with sprinklers and voice alarm) | 5.1 / 3.8 mm | [ICC 2021 MoE slides](https://iccsafe.org/wp-content/uploads/2021-IBC-Means-of-Egress.pdf) |
| Egress door width | 32 in clear (not verified in this search) | 813 mm | study guides only |
| Mezzanine | Aggregate <= 1/3 of the room's floor area (505.2.1); 7 ft headroom above and below | 2.13 m | [WAC 51-50-0505](https://lawfilesext.leg.wa.gov/Law/WACArchive/2019/htm/WAC%20%2051%20%20TITLE/WAC%20%2051%20-%2050%20%20CHAPTER/WAC%20%2051%20-%2050%20-0505.htm) |

Consequence for a concept plan: a straight line is the shortest possible path, so if
some floor point is farther than 76 m in a straight line from every exterior wall, no
arrangement of perimeter exits keeps S-1 travel within 76 m. That lower bound is the
only egress fact ACS measures; travel routes, exit counts and widths stay
NOT_EVALUATED.

## 8. Values adopted in ACS

| Constant (`warehouse_planning.py`) | Value | Used in | Basis |
|---|---|---|---|
| `DOCK_DOOR_W`, `DOCK_DOOR_H` | 3.0 m, 3.0 m (capped at 0.9 x wall height) | dock layout | 9-10 ft x 10 ft doors |
| `DOCK_PITCH` / `DOCK_PITCH_MIN` | 4.0 m / 3.66 m | prompt, dock layout, spacing and frontage notes | 12-14 ft centres |
| `STAGING_DEPTH_MIN` | 16 m (prompt: 16-20 m) | prompt, staging note | 53-57 ft floor drop; 60 ft speed bay |
| `TRUCK_COURT_MIN` | 35 m | prompt, court placement, court note | 2 x 16.5 m + 1.5 m |
| `CLEAR_HEIGHT_MIN` | 6 m (prompt default 10-12 m) | clear-height note | 28-40 ft practice |
| `EGRESS_TRAVEL_M` | 76 m (122 m conditional) | egress lower-bound note | IBC Table 1017.2, 1017.2.2 |
| `SPRINKLER_CLEARANCE` | 0.46 m (ESFR 0.91 m) | rack note | NFPA 13 |
| `PALLET_AISLE_MIN` | 2.4 m | rack aisle note | reach truck lower bound |

## 9. Audit of the instructions before this change

Connected planner (`PLANNING_SYSTEM`, 1,479 characters) and its pipeline:

1. **Dock requirements could never pass.** The policy forbade "openings" in outline
   and plan_chunk, `validate_chunk` dropped any `docks`, and no later warehouse stage
   added them, so a confirmed `dock_count` measured 0 and failed review on every
   generation.
2. **No typology.** The staged plan never set `meta.type`, so the scorecard read the
   typology as `unknown`: warehouse metrics were not measured, dock and rack
   requirements failed as `REQUIREMENT_METRIC_NOT_APPLICABLE`, and the vertical stage
   gate and the handoff dock/rack guards (all keyed on `meta.type`) did not apply.
3. **No planning knowledge.** Nothing about flow, which zones need an exterior wall,
   frontage per door, staging depth, a truck court inside the plot, office placement
   or clear height. A plan could put receiving in the middle of the building or fill
   the plot to its boundary.
4. **Silent 3 m warehouse.** `merge_plan` falls back to `wall_h` 3.0 and
   `floor_height` 3.2 when the outline omits them; the policy never asked for the
   clear height.
5. **Ambiguity.** "Keep unspecified proposals explicit assumptions" named no place;
   the review card reads `meta.assumptions`. No role vocabulary was given, while the
   scorecard and requirement selectors group by role.

Legacy warehouse prompt (single-shot `/v1/understand`, chat edits, and until now the
position repair call):

6. **Wrong dock defaults.** Door 3.5-3.7 m wide x 4.0-4.5 m high is a grade-level
   drive-in door, not a dock door; centres 4.0-6.5 m waste frontage; "manoeuvring
   >= 12 m" is about a third of the apron a 16.5 m truck needs.
7. **Invented mandatory quantities.** ">= 4 emergency exits" and "at least 6
   cameras" were presented as mandatory, contradicting `REQUIREMENTS_RULE` (no code
   claims) and the repository policy that regulatory quantities stay NOT_EVALUATED.
8. **Contradiction.** "Follow literally" and "mandatory" headings fought the
   priority rule that reference rules are defaults the client overrides.
9. **Missing limits.** One 3.4 m forklift aisle for every truck type; 8-9 m racks
   with no sprinkler clearance.
10. **Wasted repair tokens.** The paid position repair sent the 9,345-character
    generation prompt, which asks for a whole Building JSON, for a reply that is only
    `{"positions": [...]}`.

Brief reader (`brief-program.mjs`):

11. "و4 أرصفة" (number joined to «و») was not read, so a second dock group vanished.
12. "6 أرصفة استلام و8 أرصفة شحن" was read as `dock_count` 6, not 14.

Still open: rack groups (`min_rack_group_count`) are not planned at concept stage,
so that requirement still fails; clear height is prose, not a requirement metric;
chat edits on a connected warehouse still use the legacy prompt, whose envelope rule
contradicts the connected no-envelope contract; `acs_validate.IND_AISLE` is unused.

## 10. What changed

- `PLANNING_SYSTEM` rewritten: role vocabulary, flow and U-flow default, dock zones on
  an exterior wall with 4 m per door and 16-20 m staging, a 35 m truck court, storage
  and office placement, `wall_h` from the clear height (10-12 m default), assumptions
  in `meta.assumptions`, and per dock zone a compact `docks: [{edge, count}]` intent.
  1,479 -> 2,513 characters (+1,034, about +260 tokens per outline or plan_chunk call;
  a small warehouse makes two such calls).
- `warehouse_planning.py` (new, no provider call): exact dock groups from the intents,
  completed or trimmed to the confirmed total; one position-only shift that keeps the
  truck court when the plot allows it; Arabic disclosures in `meta.assumptions`; and
  cited review notes that never block approval.
- Pipeline: `meta.type = "warehouse"` is server-derived; intents leave the rooms
  while areas are fitted and overlaps repaired, then return as dock groups.
- Position repair: its own 332-character system policy instead of the 9,345-character
  generation prompt.
- Legacy prompt: dock door 2.7-3.0 x 3.0 m, centres 3.7-4.3 m (>= 3.66 m), 16-20 m
  staging and a 35 m truck court, per-truck aisle widths, sprinkler clearance, no
  invented exit or camera counts, no "mandatory" wording (9,345 -> 9,501 characters).
- Brief reader: «و» before a dock count, and receiving + shipping groups summed into
  one inferred `dock_count` for the owner to confirm.
