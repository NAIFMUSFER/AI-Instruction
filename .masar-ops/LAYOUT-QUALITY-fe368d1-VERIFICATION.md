# Measured layout quality — verified preview runtime fe368d1

## Runtime and deployment
The existing https://masar-customer-preview.onrender.com service was updated in place. Runtime source is fe368d102dc417b79f861f448e7d9a8feec456df on audit/masar-customer-journey-20260908. Render service srv-dag72o740ujc738cd8s0 in workspace tea-d9qth1iju40c73btab90 remains Free/Frankfurt with automatic deploy disabled. Only MASAR_APPROVED_COMMIT was merged into the service environment. Deploy dep-dag8omrl550s73a9djmg became live at 2026-09-08T22:30:36Z. No new service, paid plan, cloud Blender worker, external AI provider, main/production-v4 merge, ACS or dawaee change was made.

The audit branch subsequently received 3b31798e9541f8b5292a7e3ded2515bd013004d8, a workflow-only change converting completed one-shot transport into repeatable read-only acceptance. It does not change the deployed application files, and the preview remains pinned to fe368d1. Repeatable CI succeeded in run 34286411427.

## Implemented functionality
The toolbar's «جودة التوزيع» opens «جودة التوزيع والمقايضات». A second entry is present in the material-preview source card. This read-only review measures the real canonical geometry, compares an eligible optional proposal, lists every bedroom's actual polygon area and an illustrative contained-rectangle bed-zone check, exposes all 17 before/after space areas, and downloads a revision-bound quality JSON report. No description or account data is duplicated in this report.

For an unedited/unlocked compact-three-bedroom-v1 model, «معاينة الحركة الأقصر» creates the ordinary non-persistent change preview. It is a whole-layout alternative, not a promise to move one wall. The banner explicitly discloses a side family entrance, smaller secondary bedrooms/dining and changed internal partitions/openings. «اعتماد التعديل» adds one revision; cancellation leaves the full original history unchanged. Undo/redo and IndexedDB reload were verified using exact exported geometry, not matching titles alone.

The proposal preserves the original description, requirement objects, comment targets, all 17 room IDs/kinds/names/notes, authoring settings, plot and every outdoor feature. It refuses locked rooms/openings, manually edited geometry, unrelated programmes, unsupported cases, and already-improved layouts. It cannot worsen previously satisfied locked measurable requirements or exceed the declared envelope budget. The alternative gallery now disables unchanged or geometrically blocked proposals rather than suggesting a successful improvement when no change exists.

## Actual customer results, not stock illustrations
The original 2,191-character customer description is unchanged. The actual project was generated, improved, accepted and downloaded through the published mobile UI separately in Chromium and WebKit. It retains 20x25 m land, three bedrooms and 17 authored spaces. Pool, parking, garden, terrace and BBQ coordinates/dimensions remain exactly unchanged.

Before -> after measurements:
- Longest straight hall extent through the UNION of hall polygons: 10.419 -> 5.402 m.
- Hall polygon area: 14.522 -> 10.946 m².
- Hall plus reception allocation: 19.288 -> 14.297 m². Including reception prevents claiming an improvement merely by renaming a hall.
- Principal bedroom polygon area: 13.032 -> 14.855 m².
- Principal bedroom: old L-shaped polygon with largest contained rectangle 2.412x4.245 m -> new rectangular room 4.052x3.666 m.
- Secondary bedrooms: 14.892 -> 12.658 m² each, explicitly disclosed as a tradeoff.
- Dining: approximately 11.466 -> 9.196 m², explicitly disclosed as a tradeoff.
- Conservative conceptual building envelope: 150.732 -> 150.736 m², still within 120–160. The millimetre-rounding difference is not a meaningful area saving or increase.
- Outside the candidate envelope: 349.264 m², including pool, parking, paving and circulation, not all planting.

The proposed kitchen has a hosted rear/garden exit. The guest entrance/WC/majlis have a separate interior connectivity graph from family rooms. This is not a certification of acoustic/visual privacy or an outdoor access-route design.

## Verification
Initial predeployment gate 34285538526 succeeded before committing any application changes: 515 Node tests, 15 Chromium + 14 WebKit new quality journeys, original-description acceptance 14 per browser, legacy/source recovery 15 Chromium + 14 WebKit, existing HTTP regressions 28 each on Chromium/Firefox/WebKit, and 56 standalone interactions. Independent IfcOpenShell schema/EXPRESS and geometry verification of the new customer IFC produced 131 shapes, zero schema issues and zero geometry failures. A budget/orientation matrix and independent room-connectivity tests are part of Node acceptance.

Published-site gate 34286305889 succeeded. It checked /api/version against fe368d1, compared seven served JavaScript/CSS modules plus public HTML byte-for-byte with the pinned source, and checked health/readiness, ephemeral persistence and CSP/HSTS. The live UI reports contain 57 checks with zero failures: quality journeys 15 Chromium + 14 WebKit and original-description journeys 14 per browser. The quality journeys include 320/390/768px layouts, explicit tradeoffs, cancellation, acceptance, undo/redo, reload, real locking/unlocking, unchanged-card disabling and no unhandled page errors or third-party runtime requests. Chromium exercised the actual software-rendered Three.js view and its Blender scene JSON against the accepted canonical model/revision; WebKit did not certify PBR or physical iPhone behaviour. The downloaded improved IFC independently passed again with 131 represented products and no schema/geometry errors.

CI artifact 10079468319 SHA-256: 1e6e8197f2d1985eb8c8f49da2c6e1c14a58f6cc7d35002d57572941ef4d2838.
Live artifact 10079663398 SHA-256: a62c2ef6b25d2a4bb4f42739020ad661a4e9d59203ef2f0eb0a34f68df637f69.
Both downloaded archives passed ZIP integrity and SHA-256 checks. All 42 delivered file hashes and all 90 source-manifest files were checked. The delivered source ZIP was then extracted to a fresh directory: syntax/build and all 515 Node tests passed, rebuilt standalone HTML matched the delivered HTML byte-for-byte, and 56 standalone interactions passed. Local HTTP browser navigation was blocked by the managed browser policy; it was not bypassed or counted as a pass. Real HTTP/browser acceptance above ran in GitHub CI and against the published HTTPS site.

## Scope and remaining design work
Hall extent measures an axis-aligned continuous span through the hall polygons with the model's geometric tolerance; it is NOT total walking, shortest path, evacuation distance or a clear-width check. Splitting a corridor into differently named hall rooms cannot shorten the metric. A bedroom result tests whether an illustrative 3x2.8 m bed zone fits inside the actual polygon after a conservative wall allowance. It does not check door swings, cupboards, accessibility or approve furniture placement. The envelope and room areas are conceptual, not licensed construction takeoff or finished clear floor areas.

This is a constrained optional alternative, not a general-purpose architectural solver. The side approach, kitchen island, detailed bathroom/dressing layouts, window privacy, daylight, ventilation, pool safety, structure, fire and MEP still need specialist review. Diagram label density on the small service spaces remains a presentation limitation; the separate room-area table exposes the full names and measurements. Material screenshots are real web previews, not Cycles renders. Option A and ephemeral server storage remain unchanged; retain exported MASAR JSON for important work.

## Customer use
Refresh the same customer-preview page without clearing browser data. Open a supported compact chalet and choose «جودة التوزيع» -> inspect before/after and tradeoffs -> «معاينة الحركة الأقصر» -> «اعتماد التعديل» only after reviewing. «إلغاء» preserves the current plan; «تراجع» restores the original geometry after acceptance. No retyping is required. A saved legacy generic layout must first use the already existing description-review/rebuild flow; it is never silently migrated.
