# CAD drafting standards for ACS plan drawings

Research note for the 2D exports (SVG, PDF, DXF) that ACS produces from an
approved canonical plan. It records the conventions engineers expect from an
AutoCAD/Revit floor plan, the concrete values ACS adopted, and how sure we are
of each one. The machine-readable table is `acs_drafting_standards.py`; the
drawing code is `acs_plan_drafting.py`.

How to read the values:

* **Code reference**: a number from a model code (IBC/IRC, ICC A117.1). SBC 201
  (2018) was revised from the 2015 IBC with local modifications
  ([MLIT summary](https://www.mlit.go.jp/common/001404290.pdf),
  [ICC SBC 201 study companion](https://shop.iccsafe.org/2018-saudi-building-code-sbc-201-study-companion.html)).
  The SBC text itself was not available to this research, so these numbers are
  cited, not certified. Check the adopted SBC text before using them as
  pass/fail rules.
* **Practice**: common Saudi/Gulf or international office practice from
  secondary sources (suppliers, handbooks, municipal checklists).
* **Convention**: how ACS draws. It never changes canonical geometry.

Network note: only search summaries were available in this session; the
standards PDFs themselves could not be opened. Where only a secondary source
confirmed a value, the text says so.

---

## 1. AutoCAD conventions

### 1.1 Layer names (US National CAD Standard / AIA CAD Layer Guidelines)

Format: `Discipline-Major-Minor-Minor-Status`, for example `A-WALL-PRHT`
([City of Mesa CAD manual](https://www.mesaaz.gov/files/assets/public/v/1/business-development/engineering/engineering-cad-standards.pdf),
[AIA layer list, U. Oregon](https://pages.uoregon.edu/arch/landcad/Layer_Standards.htm),
[NCS v5 guidelines copy](https://forums.autodesk.com/autodesk/attachments/autodesk/66/350158/1/NCS_v5_AIA%20CAD%20Layer%20Guidelines.pdf)).

**Saudi relevance.** EXPRO (the Government Expenditure & Projects Efficiency
Authority) publishes a CAD Standards Procedure (EPM-KE0-PR-000008). Its Arabic
text asks that colour, linetype and lineweight be **ByLayer**, and EXPRO's
Graphical Blocks and Symbols Guide refers to the US NCS v6 and makes NCS
general symbols mandatory on its projects
([CAD Standards Procedure](https://www.expro.gov.sa/api/uploads/CAD%20Standards%20Procedure.pdf),
[Arabic edition](https://www.expro.gov.sa/api/uploads/%D8%A7%D9%84%D8%AF%D9%84%D9%8A%D9%84%20%D8%A7%D9%84%D8%A5%D8%AC%D8%B1%D8%A7%D8%A6%D9%8A%20%D9%84%D9%85%D8%B9%D8%A7%D9%8A%D9%8A%D8%B1%20%D8%A7%D9%84%D8%AA%D8%B5%D9%85%D9%8A%D9%85%20%D8%A8%D9%85%D8%B3%D8%A7%D8%B9%D8%AF%D8%A9%20%D8%A7%D9%84%D8%AD%D8%A7%D8%B3%D9%88%D8%A8.pdf),
[Graphical Blocks and Symbols Guide](https://expro.gov.sa/api/uploads/Graphical%20Blocks%20and%20Symbols%20Guide.pdf)).
So NCS layer names with ByLayer properties are the defensible default for Saudi
engineers. ISO 13567 is the alternative international scheme; it forbids the
`ANNO` major group ([NCS list, Scribd copy](https://www.scribd.com/document/328631209/NCS-CAD-Layer-Guidelines-pdf)).

| Layer | Meaning (sources) | ACS content |
|---|---|---|
| `A-WALL` | Full-height walls ([TTU](https://www.depts.ttu.edu/EngineeringServices/CADD_GIS/Documents/eng_gs10101.pdf)) | Wall outlines at the cut plane |
| `A-WALL-PATT` | Wall hatch / poché ([Triton list](https://academics.triton.edu/faculty/fheitzman/layname.html)) | One solid hatch with all wall loops |
| `A-WALL-PRHT` | Partial-height walls ([UW standard](https://cpd.uw.edu/files/media/uwf-ds-uw-architectural-cad-standard-layers.pdf)) | Walls and parapets lower than the cut plane |
| `A-DOOR` | Doors | Door leaves, overhead dock-door lines |
| `A-DOOR-SWNG` | Swing arcs (office extension in the NCS minor-group pattern) | Thin 90° swing arcs |
| `A-GLAZ` | Windows, glazed walls (TTU) | Sill and glazing lines |
| `A-FLOR-STRS` | Stair treads, escalators, ladders ([Calgary](https://live-ucalgary.ucalgary.ca/sites/default/files/teams/223/Design%20Standards/8.4.2%20Layer%20Naming%20Convention.pdf)) | Treads, landings, arrows, cut line |
| `A-FLOR-OVHD` | Items above the cut plane | Dashed stair flights above the cut |
| `A-FLOR-EVTR` | Elevators | Shaft cross |
| `A-FLOR-IDEN` | Room numbers, names and targets (TTU) | Room names |
| `A-AREA` | Area calculations and boundaries ([U. Oregon](https://pages.uoregon.edu/arch/landcad/Layer_Standards.htm)) | Canonical room rectangles, **non-plotting** |
| `A-AREA-IDEN` | Area tags; sources disagree (UW: boundaries; Calgary: tags) | Net area and clear size of each room |
| `A-AREA-BNDY` | ACS extension | Plotted dashed separation lines where a space has no wall |
| `A-ANNO-DIMS` | Dimensions (NCS minor group `DIMS`) | DIMENSION entities |
| `A-ANNO-SYMB` | Reference symbols (NCS `SYMB`) | North arrow, scale bar |
| `A-ANNO-TEXT` / `A-ANNO-NOTE` | Text and notes | Titles, general notes, disclaimer |
| `A-ANNO-TTLB` | Title block (listed; description unverified) | Sheet frame and title block |
| `C-PROP` | Property lines (civil) | Canonical site rectangle, phantom line |

### 1.2 Line widths and linetypes

ISO 128 uses a √2 series: 0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0 mm.
Construction drawings normally use three widths (narrow, wide, extra wide);
visible outlines cut in section are drawn wide when hatched and extra wide when
not hatched ([ISO 128-23 sample](https://cdn.standards.iteh.ai/samples/22292/a9f6396b7eb94397aa5e41513ebf09b1/ISO-128-23-1999.pdf);
ISO 128-23 is withdrawn and replaced by ISO 128-2:2020). NCS names Fine 0.18,
Thin 0.25, Medium 0.35, Wide 0.50, Extra wide 0.70, then 1.00/1.40/2.00 mm, with
0.13 mm as an optional extra-fine width
([CAD Setter Out](https://cadsetterout.com/drawing-standards/line-weights/amp),
[Land F/X](https://www.landfx.com/docs/cad-basics/plotting/1203-lineweight.html)).

ACS widths: cut walls 0.50, partial walls/doors/windows/stairs 0.25, dimensions
0.18, swing arcs and poché 0.13, title-block rules 0.35, sheet frame 0.70.
Linetypes: continuous; DASHED (3 mm dash, 1.5 mm gap on paper) for items above
the cut and space separations; PHANTOM for the site line. DXF linetype patterns
are pre-scaled to the sheet scale with `$LTSCALE = 1`.

### 1.3 Units and insertion units

`$INSUNITS` 4 = millimetres, 6 = metres; `$MEASUREMENT` 1 = metric. The two are
independent, and some importers (Tekla) assume millimetres whenever
`$MEASUREMENT` is metric
([ezdxf units](https://ezdxf.readthedocs.io/en/stable/concepts/units.html),
[AutoCAD INSUNITS](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-LT/files/GUID-A58A87BB-482B-4042-A00A-EEF55A2B4FD8.htm),
[Tekla](https://support.tekla.com/article/how-are-units-defined-in-imported-dwg-files-in-tekla-structures)).
Most metric offices draw buildings in millimetres; some European practice still
uses centimetres ([draftsperson.net](https://blog.draftsperson.net/drafting-standards-what-metric-units-do-i-draw-with)).

**ACS decision:** keep metres (1 drawing unit = 1 m). The canonical model is in
metres, the existing DXF contract pins `$INSUNITS = 6`, and the CAD and IFC
north/position readers compare coordinates in metres. The title block states
"1 unit = 1 m". Risk: an engineer whose template is in millimetres must insert
with unit conversion (AutoCAD does this automatically from `$INSUNITS`).

### 1.4 Text heights

ISO 3098 heights: 1.8, 2.5, 3.5, 5, 7, 10, 14, 20 mm, where *h* is the
capital-letter height ([ISO 3098-0 sample](https://cdn.standards.iteh.ai/samples/24792/1811286881f24ea49763a66a747029c8/ISO-3098-0-1997.pdf)).
Typical use: 2.5 mm for dimensions and notes, 3.5 mm for sub-titles and room
names, 5 mm for drawing titles, 7 mm for sheet titles
([draftsperson.net](https://blog.draftsperson.net/text-heights-in-drawings/),
[CAD Setter Out](https://cadsetterout.com/drawing-standards/lettering-heights/)).
Model height = paper height × scale
([chart](https://blog.draftsperson.net/wp-content/uploads/2026/08/text-height-at-scale-chart.pdf)):

| Paper height | Model height at 1:50 | Model height at 1:100 | ACS use |
|---|---|---|---|
| 1.8 mm | 90 mm | 180 mm | Minimum (notes) |
| 2.0 mm | 100 mm | 200 mm | Clear room size, schedule rows |
| 2.5 mm | 125 mm | 250 mm | Dimensions, room area line |
| 3.5 mm | 175 mm | 350 mm | Room names, sub-titles |
| 5.0 mm | 250 mm | 500 mm | Drawing title |
| 7.0 mm | 350 mm | 700 mm | (sheet titles, not used) |

AutoCAD's TEXT height is the cap height, so ACS writes these values directly as
DXF heights. SVG and PDF font sizes are em sizes, so they use *h* / 0.72
(`acs_drafting_standards.CAP_HEIGHT_RATIO`).

### 1.5 Scales, paper and frame

ISO 5455 recommends 1:2, 1:5, 1:10 and their ×10ⁿ multiples (1:20, 1:50, 1:100,
1:200, 1:500 ...) and allows intermediate scales only for functional reasons
([ISO 5455](https://www.iso.org/standard/11500.html),
[sample](https://cdn.standards.iteh.ai/samples/11500/dc0452907ab547f5aee36c22006aa275/ISO-5455-1979.pdf)).
Municipal examples: Sharjah asks for plans, elevations and sections at 1:100 or
1:50, site plans at 1:200 or 1:100, stair details at 1:20, black-and-white A2
sheets, an 8 × 10 cm stamp box and a north arrow
([Sharjah architectural checklist](https://portal.shjmun.gov.ae/en/eservices/Attachements/%D9%82%D8%A7%D8%A6%D9%85%D8%A9%20%D8%A7%D9%84%D8%AA%D8%AF%D9%82%D9%8A%D9%82%20%D8%A7%D9%84%D9%85%D8%B9%D9%85%D8%A7%D8%B1%D9%8A%D8%A9.pdf)).
Riyadh's villa project form asks for final structural and MEP drawings at 1:50
with an A3 paper copy
([Riyadh BLS form 1](https://cts.alriyadh.gov.sa/_layouts/RM_Pages/FormsDownload/BLS_Project_Attach_Form1.pdf)).

**ACS decision:** one sheet size and one standard scale for the whole set,
chosen in this order: A3 1:50 (small plans), A3/A2/A1 at 1:100, then 1:200,
1:500, 1:1000, 1:2000. A plan that fits none is drawn on A0 at a computed scale
and labelled "non-standard". ISO 5457 frame: 20 mm filing margin on the left,
10 mm elsewhere; a 90 mm title-block column on the right. The SVG is drawn at
true size (`width="594mm"`, 1 user unit = 1 mm on paper), so it prints to scale.

---

## 2. Graphic symbols

* **Doors.** A leaf line at 90° to the wall from the hinge, plus a quarter-circle
  swing arc; the hinge is read from the arc's centre; double doors show two arcs
  meeting in the middle; sliding doors are two overlapping parallel lines
  ([Noble Desktop](https://www.nobledesktop.com/learn/blueprint-reading/understanding-different-types-of-doors-and-windows-in-floor-plans),
  [Architecture Courses](https://architecturecourses.org/design/architectural-drawing-symbols)).
  ACS: the leaf starts on the wall face of the room it swings into; arc 0.13 mm,
  leaf 0.25 mm; openings 1.40 m and wider are drawn as double leaves.
  **Disclosed default:** the canonical model has no swing side or hand. ACS
  swings doors into the more private room (bath/bedroom/store over living
  rooms over circulation; wall-less porches count as outside, so entrance doors
  open inwards; ties go to the smaller room) and hinges on the jamb nearer that
  room's corner so the open leaf rests against a wall.
* **Windows.** A break in the wall with thin sill lines on both faces and a
  frame/glass line inside the opening; detail is often keyed to a schedule
  (same sources). ACS: both sill lines plus a double glazing line on the wall
  axis, all on `A-GLAZ`.
* **Stairs.** Treads as lines, an arrow from where you stand, labelled UP/DN;
  a flight that continues past the plan cut ends at a diagonal break line and
  the part above the cut is dashed; stacked stairs show the flight beyond
  ([Noble Desktop, stairs](https://www.nobledesktop.com/learn/blueprint-reading/understanding-stacked-and-switchback-stairs-in-floor-plans-a-comprehensive-guide),
  [Graphisoft stair display](https://help.graphisoft.com/AC/20/INT/AC20Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-231.htm)).
  The plan cut is taken at 1.2 m (`CUT_PLANE_HEIGHT_M`, practice value; Revit's
  default view range uses 1200 mm). ACS: departing U stairs show «صعود» with a
  dot at the start, a break line at the riser that passes 1.2 m, and dashed
  flights above; arriving stairs show «نزول»; stacked cores show both arrows.
* **North arrow.** Required on plan sheets, omitted on non-plan views
  ([AE Drawing Handbook](https://w.tboake.com/2022/THE%20AE%20DRAWING%20HANDBOOK-Sept2022.pdf),
  Sharjah checklist above). ACS draws it in the title block pointing to plan
  north (canonical −Z, the same direction IFC exports as `TrueNorth (0,1)`).
* **Scale bar.** A graphic scale stays valid when a sheet is reduced
  ([NPS reference manual](https://www.nps.gov/dscw/upload/ReferenceManual10A_April2001.pdf)).
  ACS: about 50 mm long (5 m at 1:100), alternating filled segments, in metres.
* **Grid and axis bubbles.** Grid lines label one direction with letters and the
  other with numbers; many offices skip I and O; text about 3.5 mm
  ([CAD Setter Out grid frame](https://cadsetterout.com/drawing-standards/grid-reference-frame/),
  [Archinect discussion](https://archinect.com/forum/thread/150433483/gridline-labelling-standards),
  [Revit grids](https://help.autodesk.com/cloudhelp/2020/ENU/RevitLT-Model/files/GUID-A529C10A-F22F-4919-A7B3-B1847A498004.htm)).
  Bubble diameter was not found in a standard (offices use about 8–12 mm).
  **ACS does not draw grids:** the canonical model has no structural grid or
  columns, and inventing axes would mislead the structural engineer. This is
  listed under `not_drawn` in every receipt.

## 3. Dimensions

Floor plans are dimensioned from the outside in and from the general to the
particular, usually with three strings on each face; exterior elements (piers,
window openings, column lines) are dimensioned outside the plan and interior
ones inside; every element should be locatable by two strings, no more
([Noble Desktop](https://www.nobledesktop.com/learn/blueprint-reading/understanding-dimension-chains-in-architectural-drawings-a-detailed-analysis),
[AIA, the lost art of dimensioning](https://www.aia.org/sites/default/files/2025-12/AIA_BestPractices_Thelostartofdimensioning.pdf),
[Dietrich's floor-plan dimensions](https://docs.dietrichs.com/dietrichs-intelligent-documentation/dietrichs/plans/floor-plans/floor-plan-dimensions)).
The King Saud University drafting notes place dimension lines 12 mm from the
view and the figures on or above the line
([KSU dimensioning](https://faculty.ksu.edu.sa/sites/default/files/Dimension.pdf)).

ACS chains on every face (inside to outside):

1. **Openings**: outer face, each window/door/dock jamb on that façade, outer face.
2. **Walls**: outer face, centre line of every interior wall that meets the
   façade, outer face.
3. **Overall**: outer face to outer face.

First line 10 mm from the outer face, 7 mm between lines, 2 mm extension gap
and overrun, 45° architectural ticks 2.5 mm, text 2.5 mm above the line
(vertical chains read from the right), metres to two decimals. Chains always
close: the segments of each string add up to the overall dimension. Exterior
walls are dimensioned to the outer face and interior walls to their centre
line because the canonical room rectangles *are* wall centre lines
(`meta.acs_apartment.wall_reference = room_wall_centrelines`). In the DXF the
segments are real `DIMENSION` entities (style `ACS-ARCH`, `DIMSCALE` = sheet
scale) so engineers can edit them.

## 4. Room tags

Revit's stock room tags carry name and number, optionally area or volume;
net room area can be computed as gross minus construction area
([Revit room tags](https://help.autodesk.com/cloudhelp/2017/ENU/Revit-Model/files/GUID-5FBF2AA2-B811-4443-9DBB-9DE62191F332.htm),
[Revit Areabook net room area](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-Analyze/files/GUID-451071BC-301B-4F29-AFE5-81EDD40CCBFB.htm)).
ACS tag (centred, shrunk to fit, white mask behind text):

```
مجلس الضيوف          name, 3.5 mm (A-FLOR-IDEN)
S6 · 16.21 m2        number + net area, 2.5 mm (A-AREA-IDEN)
3.39 × 4.78          clear size between wall faces, 2.0 mm
```

Room numbers S1, S2 ... follow projection order and match the PDF receipt. A
stair room's tag moves onto the stair landing so it does not cover treads. The
title block repeats every room in an area schedule with net and axis (canonical
rectangle) areas, plus totals. Level is given by the sheet title and number
(A-101 ground, A-102 first ...), following the NCS sheet-number pattern.

## 5. Wall drafting

* **Thickness (practice).** Saudi block suppliers: 20 cm blocks for exterior
  walls, 10 and 15 cm for interior partitions; standard block widths 100, 150,
  200, 250 and 300 mm; villas are usually a concrete frame with 200 mm
  insulated block infill
  ([Al Mabsat blocks](https://almabsat-dev.pages.dev/en/products/standard-blocks/),
  [block sizes](https://www.youmats.com/en/the-bricks),
  [UCD research on Saudi villas](https://researchrepository.ucd.ie/rest/bitstreams/47881/retrieve)).
  Exterior 200–300 mm (cladding or cavity adds thickness); interior 100–150 mm;
  wet walls and cores 150–200 mm.
* **Centre line versus faces.** CAD plans draw both wall faces, fill or hatch the
  cut, and close corners and T-junctions without internal lines. ACS walls are
  centred on the canonical room edges at the model `wall_t` (the same rule the
  3D compiler uses), merged where rooms share a wall, extended by half a
  thickness at corners, cut by every opening, and filled with solid grey poché.
  Walls lower than the 1.2 m cut plane (parapets, `low`/`rail` walls) are drawn
  uncut; `glass` walls are drawn as glazing.
* **Gap.** The model has one global wall thickness, so exterior and interior
  walls draw with the same thickness. A per-wall thickness in the canonical
  model is needed before the drawing can show 200 mm exterior and 100 mm
  interior walls; `WALL_THICKNESS_M` is ready for planners to use.

## 6. Saudi practice

* **Permits.** Building permits are requested only through the Balady portal or
  app; the owner authorises an accredited engineering office, which prepares the
  architectural and structural designs after choosing the land survey report
  ([Balady: issuing a building permit](https://balady.gov.sa/en/services/issuing-building-permit),
  [MoMAH](https://momah.gov.sa/en/node/5104)). No public Balady drafting
  standard (layers, scales, sheet sizes) was found; offices follow their own or
  the client's standard (EXPRO for government work).
* **Areas that matter.** Municipal permit fees are charged per m² of
  «مسطحات البناء» including external and roof annexes, basements, projections and
  every storey ([MoMAH municipal fees regulation](https://momah.gov.sa/sites/default/files/2025-11/layht%20rswm%20alkhdmat%20albldyt.pdf)).
  The residential requirements in force from 14 July 2024 define building ratio
  as the permitted ground-floor footprint divided by the plot area; set-backs
  are measured from the property line to the ground-floor building line
  ([MoMAH residential building requirements](https://momah.gov.sa/sites/default/files/2024-07/ashtratat%20a%27nsha%20almbany%20alsknyt%20almnshwrt%20%60ly%20mwq%60%20alwzart%20.pdf)).
  The exact measuring face for «مسطحات البناء» was not found in these sources.
* **How measurements are written.** No Saudi rule was found for digits or units
  on drawings. Practice seen in Saudi engineering material: Western digits for
  dimensions, metres with two decimals or centimetres, and a note such as
  «جميع الأبعاد بالمتر ما لم يذكر خلاف ذلك». Arabic room names keep the digits
  the user wrote (e.g. «غرفة نوم ٢»). ACS writes dimensions in metres with two
  decimals, areas as `m2`, and states the units in Arabic and English in the
  title block. Arabic text in the PDF is shaped and bidi-ordered with logical
  ActualText; Arabic figures next to Arabic labels are kept as separate text
  runs so bidi never reorders "446.31 m2".
* **Arabic in AutoCAD.** Arial (AutoCAD's default TrueType face) contains Arabic,
  but right-to-left text can display or print reversed in AutoCAD, and SHX fonts
  have no Arabic glyphs
  ([Autodesk: Arabic printed incorrectly](https://knowledge.autodesk.com/support/autocad/troubleshooting/caas/sfdcarticles/sfdcarticles/Arabic-fonts-printed-incorrectly-from-AutoCAD.html),
  [Autodesk forum](https://forums.autodesk.com/t5/autocad-forum/viewing-printing-right-to-left-language-like-arabic/m-p/5913388),
  [Arial and Arabic in AutoCAD](https://marketplace.autodesk.com/apps/6308ba97-6815-454b-9616-cd92befb3a07)).
  ACS stores logical Unicode in TEXT entities with an Arial text style. Display
  inside AutoCAD has not been verified.

## 7. Measurement standards: net and gross area

* **IPMS (residential).** IPMS 2 is the floor area to the internal dominant face
  (IDF); IPMS 3A is the exclusive area to the outer face of external walls (and to
  the centre line of walls shared with neighbours); IPMS 3B/3C measure to the
  IDF including/excluding internal walls and columns
  ([RICS isurv: IPMS residential](https://www.isurv.com/info/390/features/10570/ipms_introducing_residential_buildings),
  [RICS Property Measurement](https://www.rics.org/content/dam/ricsglobal/documents/standards/January_2018_RICS_Property_Measurement_2nd_Edition.pdf)).
* **IBC language (basis of SBC 201).** Gross floor area: the floor area within
  the inside perimeter of the exterior walls, without deducting interior walls;
  net floor area: the actually occupied area, excluding corridors, stairs,
  toilets and mechanical rooms. The Dubai Building Code repeats these
  definitions ([DBC areas](https://dxmdigitaldocs.github.io/site/docs/dubai-building-code/areas));
  the SBC 201 wording was not retrieved.
* **ACS measures.** *Net (صافي)* is the clear area between wall faces of each
  room (centre-line rectangle minus half a wall on every walled edge; open edges
  are not reduced). This is close to IPMS 3C per room. *Axis (محاور)* is the
  canonical rectangle area, which is what the planner and the on-screen editor
  use. *Floor footprint to outer wall faces* is the union of enclosed rooms and
  walls on a level, close to IPMS 3A / gross external area. All three are
  drafting measures and are labelled as such; none is a permit calculation.

---

## 8. Dimensional standards for planners

`acs_drafting_standards.py` holds these values with their basis and source key.

| Rule | Value | Basis |
|---|---|---|
| Egress door clear width | ≥ 0.813 m (32 in) | IBC 1010.1.1 ([2018 Seattle/IBC ch. 10](https://www.seattle.gov/documents/Departments/SDCI/Codes/SeattleBuildingCode/2018SBCChapter10.pdf)) |
| Dwelling egress door | ≥ 0.813 m clear, ≥ 1.981 m high | IRC R311.2 ([Austin handout](https://Austintexas.gov/sites/default/files/files/Development_Services/RES_ResidentialTechnicalReviewHandout.pdf)) |
| Accessible door | ≥ 0.815 m clear; 0.915 m if deeper than 0.61 m | ICC A117.1 / ADA 404.2.3 ([US Access Board](https://www.access-board.gov/ada/chapter/ch04/)) |
| Nominal leaves (practice) | entrance 1.0–1.2 m, rooms 0.9 m, bath 0.8 m, closet 0.7 m | Practice (a 0.9 m leaf gives about 0.815 m clear) |
| Exterior wall | 0.20 m (0.20–0.30) | Saudi block practice |
| Interior partition | 0.15 m (0.10–0.15) | Saudi block practice |
| Stair (general) | riser 0.102–0.178 m, tread ≥ 0.279 m, width ≥ 1.118 m (0.914 m < 50 occupants), headroom ≥ 2.032 m | IBC 1011 ([county handout](https://humboldtcountynv.gov/DocumentCenter/View/3386/Commercial-Stair-Handout-4-19)) |
| Stair (dwelling) | riser ≤ 0.196 m, tread ≥ 0.254 m, width ≥ 0.914 m, headroom ≥ 2.032 m | IRC R311.7 ([2018 residential stair guide](https://timnath.org/wp-content/uploads/2022/03/2018-RESIDENTIAL-STAIR-GUIDE.pdf)) |
| Stair comfort | 0.60 ≤ 2R + T ≤ 0.65 m | Blondel rule, practice |
| Corridor | ≥ 1.118 m; ≥ 0.914 m under 50 occupants; ≥ 0.914 m in a dwelling (IRC R311.6); 0.915 m accessible route; 2.438 m for I-2 bed movement | IBC Table 1020.2 ([study guide](https://open-exam-prep.com/study-guides/are-pa/ch06-egress-life-safety/egress-capacity-stairs)), IRC, A117.1 |
| Habitable room | ≥ 6.5 m², ≥ 2.134 m in every direction | IRC R304 ([Seattle R304](https://seattle.gov/documents/Departments/SDCI/Codes/R304.1%20Habitable%20Room%20Areas.pdf)) |

The ACS U-stair default (riser 3.4 m / 18 = 0.189 m, tread 0.25 m) meets the
dwelling riser limit and the comfort rule (2R + T = 0.628 m), but its tread is
4 mm short of the IRC 0.254 m minimum and 29 mm short of the IBC 0.279 m
minimum. Typology owners should decide which row applies to shared apartment
stairs; `acs_drafting_standards.stair_ok` reports it.

## 9. Audit of the ACS exports (before → after)

| Item | Before | After |
|---|---|---|
| Content | Room rectangles only ("SPACE_BOUNDARIES_ONLY") | Same hash-bound rectangles plus walls, doors, windows, docks, stairs, lift shafts, dimensions, tags, title block |
| DXF layers | `ACS_SPACE_BOUNDARIES`, `ACS_SPACE_LABELS`, `ACS_REVIEW_NOTES`, all colour 7, default weight | 19 layers in the NCS pattern (two are ACS extensions) with colour, ISO lineweight, linetype; entities ByLayer; room rectangles non-plotting |
| DXF units | `$INSUNITS 6`, `$LUPREC 4`, no dimstyle | `$INSUNITS 6`, `$MEASUREMENT 1`, `$LUNITS 2`, `$LUPREC 3`, `$LWDISPLAY 1`, `$DIMSCALE` = scale, `ACS-ARCH` dimstyle |
| Text style | `Standard` (txt.shx, no Arabic glyphs) | `ACS-ARABIC` (arial.ttf) |
| Text sizes | Proportional to room size (1.3–4.4 mm at 1:100) | ISO 3098 heights 1.8/2.0/2.5/3.5/5 mm, shrink-to-fit with 1.8 mm floor |
| Walls | None (centre-line rectangles drawn as thin outlines) | Canonical thickness, merged, closed corners, cut by openings, solid poché |
| Doors | None | Leaf + 90° arc, double leaves ≥ 1.4 m, swing defaults disclosed |
| Windows | None | Sill lines + double glazing line |
| Stairs | None | Treads, UP/DN arrows, 1.2 m cut line, dashed flights above |
| Dimensions | One "4.36 × 7.148 m" label per room | Three closing chains per face; DXF `DIMENSION` entities |
| Room tags | Name + centre-line size (SVG) / centre-line area (PDF) | Name, number, net area, clear size; schedule with net and axis areas |
| Scale | None (SVG unitless; PDF fitted to A4 at an arbitrary scale) | Standard scale and ISO paper for the set; SVG at true size |
| North arrow / scale bar | None | Both, on every sheet |
| Title block | Header and footer lines | Project, drawing title (AR/EN), sheet number, scale/paper, units, area schedule, notes, hashes, disclaimer |

## 10. Open items

* Per-wall thickness in the canonical model (exterior vs interior).
* Door swing side, hand and type (hinged/sliding/pocket) as canonical facts, so
  the default swing rule can be replaced by the planner's decision.
* Structural grid and columns only once the structural model supplies them.
* Window types, sill heights and a door/window schedule (A-DOOR-IDEN/A-GLAZ-IDEN tags).
* Warehouse racks, lanes and stations in 2D (not drawn yet; listed in `not_drawn`).
* Opening the DXF in AutoCAD/BricsCAD to confirm Arabic display and dimension
  rendering; confirming the SBC 201/1101 values against the adopted text; asking
  a Balady-accredited office for its sheet standard (A3/A1, cm or m).
