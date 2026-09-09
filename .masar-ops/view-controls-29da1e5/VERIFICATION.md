# Floor and camera release — verified runtime 29da1e5

## Published state
The existing customer preview https://masar-customer-preview.onrender.com serves source 29da1e575a365fea5b7665633f8094a9ff5675d0. Render deployment dep-dagqd49t0dsc73a93a0g became live at 2026-09-09T18:34:45.667314Z on service srv-dag72o740ujc738cd8s0. Only MASAR_APPROVED_COMMIT was merged into the existing environment. No new service, paid renderer, GPU, durable storage or unrelated ACS/dawaee modification was made. The published source stays pinned; workflow-only changes do not deploy automatically.

The work was resumed from its actual pending camera/floor candidate, not rebuilt. Predeployment run 34388789488 passed all gates before committing this runtime. Live run 34389742405 then completed successfully on the same customer URL, with eleven served modules/bundles matching the accepted source byte-for-byte. Health/readiness, CSP/HSTS, aiConfigured=false, disabled cloud rendering and ephemeral storage were checked.

## User-visible improvements
After opening «معاينة المشروع والخامات» and building «معاينة بالخامات», the user can choose all floors or one actual floor through «نطاق العرض فقط». Isolating a floor hides other floors and the site without moving model coordinates or altering the saved geometry/history. The all-floor default remains available.

Six named perspective views are provided: iso, top, north, south, east, west, plus refit. Direction names refer to model axes, not surveyed north or street direction; the overhead view is not an orthographic plan. Eight bounding corners are fitted against both horizontal and vertical camera fields of view. Automated framing was exercised at 320, 390, 768 and 1280 pixel widths. Manual orbit/pan leaves automatic fitting until reset.

Picking excludes invisible meshes and their hidden ancestors, so hidden floors/roofs cannot win selection. An independent overlapping-box harness in the real pinned Three.js viewer verifies this rather than assuming invisibility prevents ray hits.

PNG captures the selected visible floor and roof scope and labels that scope. Complete GLB export deliberately retains all canonical floors and roof objects even while one floor is isolated. Two GLBs downloaded in isolated and all-floor views were equivalent in their parsed document and both passed Khronos validation with zero errors and warnings. Informational unused-attribute notices remain in the reports. GLB is still a visual handoff, not an editable MASAR/BIM round-trip.

Changing scene settings disables old view controls/downloads until a fresh scene is built. Reopening does not reuse a disposed viewer. Full before/after history comparisons cover display changes, downloads, close and reload.

## Measured verification
- Node: 546 passed, zero failed/skipped.
- Published browser acceptance: 170 checks passed, zero failed. New camera/floor suite: 16 Chromium and 8 WebKit checks. Other affected suites include material downloads, room review, plan inspection, layout quality and the exact original chalet request.
- The source ZIP was extracted in a separate clean CI directory, every manifest entry verified, rebuilt HTML compared byte-for-byte and 546 Node tests rerun successfully. The extracted source also passed all 16 Chromium camera/floor checks.
- Chromium coverage uses software WebGL and actual PNG/GLB downloads. WebKit coverage is UI/source/history, not its GPU renderer or physical iPhone hardware.
- Predeployment artifact 10119014507 SHA-256: e3646e85b678d67598c17940513ac90f16508fc9d23f90220a9b4d24786b38ef.
- Live artifact 10119384811 SHA-256: b22ec038ad2ad57dbdcc7ec2aa36b156c9f666aeab70208b5e594569897fa035.
- Delivered source ZIP SHA-256: f24c0db102dab2f466b6b73d7d35bcb05fb588b481617e3645b185ac5402aeb3.

After downloading the live artifact to the conversation container, ZIP integrity, the artifact digest, every delivery SHA256SUMS entry and all 111 source manifest entries were independently checked. No font files are included in the delivered source. The screenshots are actual test output of the original chalet brief and a separate three-floor villa test; not stock renders or a copy of an unknown user's browser-saved project.

## Use and limits
Refresh the same page without clearing browser data. Open the material preview, build the scene, choose the floor and camera, and use refit when needed. PNG follows the visible scope; GLB remains complete. Retain MASAR project JSON for editable project history. Option A is unchanged: no cloud Blender rendering and no permanent server storage. This release improves inspection, framing and selection, not architectural layout, furniture fit, ventilation, safety or construction/regulatory approval.
