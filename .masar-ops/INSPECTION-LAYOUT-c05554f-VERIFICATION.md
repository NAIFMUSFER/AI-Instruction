# MASAR inspection and measured layout quality — c05554f

## Published runtime
The existing https://masar-customer-preview.onrender.com service was updated in place; no new preview URL was created. Render service srv-dag72o740ujc738cd8s0 remains Free, Frankfurt, automatic deploy off. Only MASAR_APPROVED_COMMIT was merged into its environment configuration. Deploy dep-daglk70u01pc738e9cng became live at 2026-09-09T13:08:29.954493Z with runtime c05554fda1d03e29063494115c72c0db5687d09d. No main/production-v4 merge, paid worker, GPU, durable storage or unrelated ACS/dawaee service change was made in this work.

Live workflow 34355260657 completed successfully. Its exact checkout and the live /api/version both identify c05554fda1d03e29063494115c72c0db5687d09d. Ten served JavaScript/CSS/service-worker modules were compared byte-for-byte with that checkout. Health/readiness returned 200, persistenceClass remained ephemeral, aiConfigured remained false, and render capabilities had enabled=false and workerOnline=false. CSP and HSTS assertions passed.

## New read-only plan inspection
The plan toolbar now includes «تكبير وفحص». It opens «فحص المخطط والموقع», also reachable through «فتح مخطط مكبّر» in «جودة التوزيع والمقايضات». It captures the currently displayed canonical model and identifies the project, floor and exact saved revision. An uncommitted alternative is explicitly labelled «معاينة غير محفوظة».

The separate inspector supports 100–600 percent zoom, pan, a full-site reset, keyboard navigation and a two-pointer pinch handler. The SVG has no room-edit drag targets. Actual pointer movement, controls, navigation to site elements, full SVG export and complete history equality were tested. Two-finger handler coverage uses disclosed synthetic PointerEvents and a temporary capture stub inside the test; it is not a claim of physical iPhone pinch verification. Only the inspector frame consumes those gestures, not the whole editor or page.

Outdoor rectangles are now labelled in the main plan and vector exports: pool, parking, garden, terrace and BBQ. Labels and IDs are escaped, with user-defined full names retained in titles/accessible text and the inspection schedule. The schedule lists canonical dimensions and rectangular area; selecting a row focuses its actual position. It warns that overlapping allocations must not be added as exclusive ground area, that outside-envelope area is not all planting, and that a nonrectangular room bounding box is not a usable furniture rectangle. Downloading after zoom still exports the entire uncropped canonical SVG.

The added public module is in both the standalone build order and the versioned public service-worker shell. Cache-version update does not clear IndexedDB or local projects. Layouts were checked at 320, 390 and 768 pixels; controls are wrapped rather than removed to avoid overflow.

## Existing optional layout improvement preserved and reverified
The measured-quality feature was already published at fe368d102dc417b79f861f448e7d9a8feec456df when this work resumed. It was not rebuilt or silently applied to saved projects. This release integrates the new inspector with it and re-exercises the same exact 2,191-character original description through the live UI.

Through «جودة التوزيع» → «معاينة الحركة الأقصر» → explicit acceptance, the eligible original compact one-storey three-bedroom concept produces the following measurements in the project downloaded from the live interface:

| Metric | Before | Optional accepted alternative |
| --- | --- | --- |
| Longest straight hall-union cross-section | 10.419 m | 5.402 m |
| Hall polygon allocation | 14.522 m² | 10.946 m² |
| Halls plus reception | 19.288 m² | 14.297 m² |
| Principal bedroom polygon area | 13.032 m² | 14.855 m² |
| Principal bedroom usable-shape observation | L-shaped; largest contained rectangle 2.412 × 4.245 m | Rectangular 4.052 × 3.666 m |
| Living-room polygon area | 20.478 m² | 26.170 m² |
| Each secondary bedroom polygon area | 14.892 m² | 12.658 m² |
| Dining polygon area | 11.466 m² | 9.194 m² |
| Conservative ground envelope with wall allowance | 150.732 m² | 150.736 m² |
| Outside that envelope | 349.268 m² | 349.264 m² |

This is a tradeoff, not improvement to every dimension: secondary bedrooms, dining and some service spaces get smaller; the family entrance moves to the side. All 17 room-by-room area changes are visible before acceptance. Three bedrooms, all 17 space IDs, the unchanged original brief, requirement objects, authoring information and outdoor features are preserved. Acceptance adds one revision; cancellation preserves the entire original history; undo/redo and reload restore exact models. Locked or manually edited geometry is not overwritten by this whole-layout template.

The measured hall extent merges contiguous hall polygons before measurement, so simply renaming or splitting a corridor cannot fake a shorter result. This is not walking distance or an egress-distance test. The bedroom check only tests a disclosed illustrative 3 × 2.8 m bed zone against actual polygons after wall allowance. It does not validate actual door swings, full furniture layout, wheelchair access, ventilation, daylight, visual/acoustic privacy, pool safety, structure, MEP or regulatory compliance. Room-polygon area is not an approved finished-clear-area or permit quantity. The layout is still a constrained concept, not an unrestricted architectural optimizer or approved building design.

## Verification results
Predeployment workflow 34354389244 passed all gates before committing runtime c05554f:
- Node: 524 passed, 0 failed, 0 skipped.
- New inspection: 17 Chromium + 17 WebKit checks.
- Existing measured-quality: 15 Chromium + 14 WebKit.
- Source/legacy recovery: 15 Chromium + 14 WebKit.
- Exact original request: 14 Chromium + 14 WebKit.
- Existing HTTP/offline/account regressions: 28 each in Chromium, Firefox and WebKit.
- Existing standalone interactions: 56 passed.
- Independent IFC fixture validation: 12 passed, 0 failed.

The initial inspection run 34353696119 stopped because the new test selected an inert background duplicate of the inspection button while a native dialog was open. The locator was scoped to the active dialog; no force clicks, runtime workarounds or removal of assertions were used. The subsequent full gate passed.

Live workflow 34355260657 verified 91 checks, 0 failures: inspection 17+17, optional quality 15+14, exact request 14+14. It verified whole-history preservation across read-only gestures/export/closing and cancellation, actual reload persistence, original request generation, optional layout apply/undo/redo/locks, and Chromium material-scene identity. No unhandled page errors or third-party runtime requests occurred in these journeys. The live source also repeated 524 Node tests.

The IFC exported from the actual improved downloaded project passed independent IFC4 EXPRESS and geometry checks with 131 represented products, no schema issues and no geometry failures. This is file validation, not architectural/code approval. The material image is a screenshot of the real Three.js preview, not a Cycles rendering or a stock illustration. WebKit checks here cover UI/source/recovery, not physical Safari hardware or its PBR GPU renderer.

After download, both archive digests and the delivery SHA256SUMS were checked. All 93 source files were checked against INSPECTION-MANIFEST.json. The delivered source ZIP was then extracted into a separate clean directory: syntax/build and 524 Node tests passed again under local Node 22.16.0. Its rebuilt 418,946-byte standalone HTML matched the delivered HTML byte-for-byte. CI used Node 22.23.2; the local package recheck is reported separately and did not replace browser CI.

The completed one-shot transport was removed. A following workflow-only commit 24ce514041aa223a167102db080faf5116b39973 changes inspection CI into repeatable contents:read acceptance with no commit/deploy step. It does not change the published application source or the pinned deployment.

## Evidence digests
- Predeployment artifact 10105307975: add00d7acb8e3bc1718190e42b762ec299e5bd10c78290a75cbeb7fa4570807f.
- Live artifact 10105524977: 25731fed370c21de706b298d4da8fa9295db199e71e9d78c1784d2d6102732e5.
- MASAR-Improved-Source.zip: 546ae70ab2d16a7963fcc469ffc251738adc40ed60562ab0a5bde83d242d1707.
- MASAR-Chalet-Improved.json: c9f8fac271cb786d007d071f3065002d8ee47a67af0395bf1d566e1554f02de8.
- MASAR-Improved-Standalone.html: 675898015f677f24308d8ae6739a54dbc43bb25d13e5198a32874ae23fd951c6.

## Customer use and retained limits
Refresh the same customer-preview page without clearing browser data. Use «جودة التوزيع» to review the optional shorter-hall layout; use «تكبير وفحص» to examine the current plan without editing it. Existing eligible designs change only after explicit acceptance. Old generic projects retain the earlier non-destructive description/re-evaluation flow.

Option A remains preview-only: no hosted Blender render job and no paid worker was enabled. Important projects should still be exported as MASAR JSON because the preview server database is explicitly temporary. The exported project retains the original revision as well as the accepted optional layout.
