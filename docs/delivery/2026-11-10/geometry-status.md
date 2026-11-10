# Geometry and export delivery — 2026-11-10

أصلح هذا التغيير اختلاف الارتفاع والدوران بين النموذج المعتمد والمخرجات، وحافظ على مناطق المستودع المفتوحة، وصحّح حساب المساحة عند تكرار الطوابق. الأرقام أدناه تخص أمثلة اصطناعية ثابتة واختبارات فعلية؛ لا تثبت جودة توليد ذكاء اصطناعي مباشر ولا صلاحية البناء.

Scope: geometry specialist selected source review on baseline `c37b5250dc4ff18ba0606add993b5afe52beebaa`; root owns integrated commit and deployment status. File-level depth is recorded in `coverage-geometry.json`. No all-lines/deep-review claim.

## Evidence and cause

- The same 13 geometry regression tests on the exact starting commit fail: 10 assertion failures and 3 errors exposing missing admitted capabilities. Current implementation passes all13 original regressions plus2 fixture-specific assertions (15total). Logs: `evidence/geometry-baseline-regressions.log`, `evidence/geometry-final-regressions.log`.
- Explicit canonical elevation now controls compiler geometry, including basement indexes; fallback signed index × floor height is used only when elevation is absent. Rotation transforms both local offsets and emitted box vertices/normals at 0°,45°,90°,180°; browser Three rotation sign follows the canonical X-to-Z convention.
- Explicit `walls: none`, `line`, empty lists and partial cardinal-edge lists now remain open in legacy architecture/BIM paths. Per-room IFC height follows `wall_h`, legacy `height`, global fallback. Other unusual wall-height modes are not exhaustively validated here.
- Physical stair identities include level/template/room/element scope; naming a room stairs still does not create treads, landings, openings or traversable stair geometry.
- Floor slabs in the compiler and main local viewer use a disjoint exact union of room rectangles. The L-shaped 12 m² test preserves the empty recess. Bounding rectangles remain metadata explicitly marked `BOUNDING_BOX_ONLY`. Legacy architecture/visual slab representations still have an approximation scope and must not be described as exact union geometry.
- Runtime portal adjacency rotates probe normals into the same world space as the room footprints; capsule passage checks full radius, height and diagonal swept clearance through the host wall. This is collision behavior, not accessibility/code or full-building walkability certification.
- Area aggregation and soft fitting count physical level instances; unused templates do not inflate area and repeated templates are scaled once with instance weighting. `building_target_area_m2` means the sum of canonical room rectangle areas over physical levels. Gross/net/footprint metrics remain distinct and unknown unless separately computed.
- One 29-metric registry feeds review and generated Arabic browser labels; tests exercise every evaluator metric and a feasible warehouse target area approval. Unknown names are exposed to the paid-admission owner before generation. Accepted 128-character room IDs compare successfully; two individually valid ~500 KB option models no longer violate an unrelated aggregate one-model cap.
- PR184 opening and vertical-coverage patches were inspected and selectively reconciled. Current opening20 + door-mesh12 + vertical15 tests pass. Critical architecture compilation exceptions now prevent an approved glTF from being published without openings.

## Independent serialized readers

`tests/remediation/test_geometry_independent_readers.py` uses **IfcOpenShell 0.9.0.post1** for native STEP parsing, IFC schema validation and actual triangulated world bounds, and **ezdxf** for DXF parsing/audit. Both fixtures are approved through the production conceptual geometry verifier before export. Two independent-reader tests cover all3 fixtures and one original-apartment negative-admission test passes; required parser absence is a test failure, not a skip. IfcOpenShell is test-only and not added to production dependencies.

This independently discovered an additional real defect: rectangle profiles used 3D placement where IFC requires 2D placement, causing readers to shift rooms by half their width/depth. The old villa export has four schema errors and shifted geometry. The corrected villa/warehouse have zero schema errors and exact expected space bounds. See `fixtures/independent-reader-evidence.json`. The schema's legitimate `IFCAXIS2PLACEMENT2D` auxiliary entity is now explicitly declared, with unchanged prohibition on invented architectural objects.

## Bounded corpus

All files and per-file SHA256 values are in `fixtures/manifest.json`. Revision IDs identify these saved fixture exports; rerunning the generator produces a new revision receipt while canonical model hashes remain deterministic. These are not provider-generated results. No provider call was made.

| Fixture | Canonical model SHA256 | Physical spaces | Room-area sum | glTF nodes / triangles / bytes |
| --- | --- | ---: | ---: | ---: |
| Villa, two floors at 0 and 4.2 m | `2e363de60f5789596ea31c566aadd07458cdeb71b8cf45aa6bcb535056fd3593` | 4 | 192 m² | 59 / 708 / 119608 |
| Warehouse, open internal operational boundary | `9ebd2862038c49fae1f455cbc057bf75df58fe4c95a862906e2d193e3c7ecd9f` | 2 | 320 m² | 72 / 864 / 146125 |

Saved fixture revisions: villa `plan_2f9be76895a149dea97c0375a8cfd72e`, warehouse `plan_ea80f4b496ab4c7a86b1faa9ef40ee9a`. The warehouse contains explicit racks, lane and loading doors. The villa has aligned core rooms with physical stair geometry explicitly `MISSING` and physical traversal `NOT_VERIFIED` in its receipt.

## Capability matrix

| Output/path | Actual content and identity | Units / geometry agreement | Losses and validation limits |
| --- | --- | --- | --- |
| Connected approved glTF | Compiler walls, apertures, slabs and supported requested objects; canonical revision/hash receipt and source map; reciprocal door source IDs retained | Metres, explicit level elevations, rotated objects and exact rectangular floor union covered | Mesh node names are derived identities; not every mesh has a one-to-one canonical source ID. No full BIM semantics. Fixture counts and buffers verified; browser rendering evidence belongs to frontend report. |
| Connected IFC | `IfcSpace` boundaries/extrusions for every physical space instance; distinct stable source IDs and revision manifest | Metres; canonical X/Z plan → IFC X/Y, canonical elevation → IFC Z; world bounds/schema independently checked | **Spaces only**: no architectural walls, apertures, racks, door leaves or construction detail in this connected export. No Revit application validation. |
| Legacy broader IFC exchange | Explicit mapped spaces, walls, doors/windows and supported symbolic elements; stair IDs now room-scoped | Canonical wall none/partial semantics, profile placement and height precedence tested | Not complete architectural BIM. Stair placeholder does not prove detailed physical stairs. No exhaustive target-tool validation for every entity. |
| Connected SVG | Canonical room boundaries and labels with per-space source IDs/revision | Canonical rectangular plan, floor selection; receipt bound to same revision | Conceptual space plan, not detailed construction drawing; no complete wall/aperture/furniture drafting. |
| Connected DXF | Closed room boundary polylines and labels; stable source IDs/XDATA plus companion revision receipt | Metres; canonical plan Z → negative CAD Y is an explicit drawing convention. Independent ezdxf audit and exact rectangle bounds | Space boundaries, not native DWG/Revit; no complete construction drawings or AutoCAD application test. |
| Connected PDF | Space plan and report using same selected revision | Arabic shaping/searchability separately delivered and tested by provider/PDF specialist | Consult `PROVIDER-PDF.md`; this specialist does not claim PDF visual inspection. |
| Runtime/local viewer | Supported canonical room/element presentation and horizontal collision/portal checks | Rotated portal and full capsule clearance CPU regressions, negative levels and slab union | CPU tests are not GPU performance measurements. No physical stairs traversal, physical iPhone or whole-building walkability claim. |

## Verification commands and limits

New checks: `PYTHONPATH=. python3 tests/remediation/test_geometry_delivery.py` (15); `python3 tests/remediation/test_requirement_vocabulary.py` (4); `node tests/lib/run.js tests/remediation/test_geometry_delivery_browser.js` (passes); `PYTHONPATH=/tmp/acs-ifc-reader:. python3 tests/remediation/test_geometry_independent_readers.py` (3 tests:2 reader checks across3 fixtures plus1 negative admission check; local test-only installation path).

Relevant existing checks passed: semantic diff8, locks18, options17, requirement evidence10, warehouse feasibility8, warehouse soft fit4, PBR Python156, BIM Python526, alignment92, architecture browser147, runtime49, collisions73, portals45, BIM browser4. Python/JS parity runtime17, BIM54 and PBR7 passed with generated source outputs. PR184 mutations were rerun at its isolated original head by the reconciliation specialist; regular suites above were also rerun on the integrated working tree.

No native CAD/BIM application, structural solver, code-compliance verifier or physical mobile device was used. Fixture evidence does not prove live AI generation or production deployment. The root delivery report records final release status and blockers. Legacy `acs_visual.py` still has broader visual fallbacks outside the approved compiler fail-closed change; no blanket fail-closed claim is made.

## Final fixture correction and apartment reader coverage

The primary synthetic villa explicitly declares4.05m walls under its next floor at4.2m and0.15m slab. An emitted-geometry test checks that the wall top meets the slab underside. This is an authored canonical testinput, not a renderer fill or a fact inferred from a user brief. The original3m-wall model remains byte-for-byte unchanged at `tests/remediation/fixtures/geometry/villa_unequal_elevation.json` (canonical SHA256 `0783c360f208c143ee97d6bdbbd37a26a32362631af325c852782fea555499a0`); its1.05m clear gap is asserted, proving the renderer does not invent fill. Physical stairs remain unsupported.

An additional **test-only apartment floor**, outside the two visual fixtures, is exported in `fixtures/apartment/`. It is explicitly newly authored from the old two-unit/balcony footprints:0.2m walls, living/kitchen/bed/bath/corridor subdivision, reciprocal dimensioned doors, lighting and stable element IDs.12spaces /138.8m²; model hash `2ee11183e294615fd53bd6f4f782a91fb57191f36f0ee044f939f0124c499c1b`. Production conceptual verification and export admission both pass. IfcOpenShell checks schema and all12 meshed space bounds; ezdxf checks all12 closed boundary polylines to1e-6m numeric tolerance. There is no apartment screenshot or live-provider claim. The unchanged original apartment remains rejected for missing wall thickness; `apartment-admission.json` records that negative evidence.
