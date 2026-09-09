# Floor views and camera framing — verified runtime 3c971cd

## Published state
The existing https://masar-customer-preview.onrender.com service was updated in place. Render service srv-dag72o740ujc738cd8s0, workspace tea-d9qth1iju40c73btab90, remains Free, Frankfurt and automatic deploy off. The final deployment dep-dagqkseq1p3s739e5dsg became live at 2026-09-09T18:51:10.943189Z with runtime 3c971cddc52e1fbe00275f0c5be627b82b81c74a. Only MASAR_APPROVED_COMMIT was merged into the existing environment. No other service, paid plan, worker, GPU, durable store, AI provider, main/production-v4 merge or ACS/dawaee change was made.

## Customer-visible changes
Open the current project through «إخراج Blender», then «معاينة بالخامات» inside «معاينة المشروع والخامات». The new «نطاق العرض فقط» selector offers all floors and site or an individual floor. Individual-floor mode hides the other floors and site for inspection; it never removes floors from the canonical model or moves their elevation. Six quick perspective views include general, overhead and the four model-axis directions. «إعادة احتواء الجزء المعروض» fits the current visible part again.

Named camera presets fit all eight bounding corners against horizontal and vertical fields of view rather than relying on a single distance independent of screen shape. Presets refit on viewport resize; manual orbit/pan ends automatic framing until reset. Controls remain disabled before a real material viewer exists and after changed scene settings until rebuilding the preview. Reopening starts a new viewer. The model-axis directions are not verified survey north or a street direction; the overhead image is perspective, not an orthographic plan or construction elevation.

Picking now excludes hidden meshes and any mesh with a hidden ancestor, so hidden roofs/floors cannot intercept a click as visible geometry. A separate deliberately overlapping-box harness proves this behavior independently of generated buildings. It is not used as customer geometry or as a substitute for the full real-project tests.

PNG captures the selected display scope and carries its floor ordinal/all-floors state, roof visibility and revision in a visible footer. Complete GLB continues to export all canonical floors and roofs, irrespective of isolation, cutaway or selected-room highlight. Full history, original description, geometry, constraints and locks are unchanged by these read-only controls. JSON is still the editable project backup; GLB is only visual handoff.

## Actual PNG defect proved and repaired
After initial floor-view acceptance, an additional real-browser regression exposed a fixed-size PNG crop when exporting an east-facing view fitted to a wide viewport. The unmodified exporter narrowed the camera aspect to the PNG content rectangle. Its downloaded 640x480 image had model pixels touching both side edges: observed box (0,173,640,287) in a 640x420 content aperture. The test was required to fail with that exact cropping error before a renderer change was applied.

Run 34390553137 then applied the guarded correction: preserve the displayed camera aspect inside the fixed PNG using letterboxing, without stretching geometry, and restore renderer size/aspect/materials afterward. The same regression and all retained product journeys passed before committing runtime 3c971cd. The frame is preserved; this does not claim to undo a user's deliberately cropped manual zoom or create a photorealistic Blender render.

Two earlier camera acceptance failures concerned screenshot observation rather than app geometry: CSS-rounded corners and native sticky dialog chrome were counted as model pixels. The observations were corrected to the computed aperture and a centered unobstructed canvas. Original nonempty and non-cropping assertions remained; no force clicks, hidden controls or browser policy bypass was used.

## Verification
Feature gate 34388789488 passed before committing 29da1e5. The final correction gate 34390553137 passed after reproducing the crop. Both exercised all Node tests, source/history/room/inspection/quality/full-description journeys, the existing three-engine HTTP/account/offline tests, 56 standalone interactions and 12 independent IFC fixtures.

Final published acceptance 34391552738 completed successfully against exactly 3c971cd. Its live /api/version matched the checkout; eleven public modules including the built Three.js bundles matched byte-for-byte. Health/readiness, CSP/HSTS, ephemeral persistence and disabled cloud rendering/AI were verified. The machine-derived LIVE-34391552738.json records:
- 546 Node tests passed, zero failures or skipped tests.
- 171 live-browser checks passed, zero failures. New floor/camera checks are 17 Chromium plus 8 WebKit; remaining checks preserve local downloads, room reports, 2D inspection, layout comparison and the exact original 2,191-character chalet request.
- Both complete three-floor GLBs downloaded from isolated and all-floor views passed Khronos validation with zero errors and zero warnings; 490 informational unused-UV entries per file are retained rather than hidden.
- The delivered source ZIP was extracted in a separate clean CI directory and every manifest entry checked. All 546 Node tests passed again, rebuilt standalone HTML matched byte-for-byte, and the extracted application passed 17 actual Chromium floor/camera/export checks.

After download to the conversation environment, the outer ZIP digest, all delivery SHA256SUMS and all 111 source-file manifest hashes were verified independently. The source package was checked to exclude font files. Raw live reports were checked against the 171 total and had no unhandled page errors. Actual final PNGs were visually inspected. No local browser result is claimed where local navigation was blocked by administrator policy; the authorized GitHub runner performed browser acceptance without altering that policy.

## Artifacts
Initial feature gate artifact 10119014507: e3646e85b678d67598c17940513ac90f16508fc9d23f90220a9b4d24786b38ef.
Negative/positive PNG correction artifact 10119720187: 532ec2345af5a0a32e87d7d4372f3452a6aec0f27303ef4617c46679e9096cef.
Final live delivery artifact 10120028426: 641697ca08f5c169a90b499aac0a5ff08b2abe7c25a53e40da138a533579b5ed.
Source ZIP: 74d8cccbce33b425d40d9570ef7ec939c1c4152ef4debb8f0ab86e522ecb87d2.

The delivered selected-floor PNG demonstrates the second floor of a separate three-floor test villa, not the customer's single-floor chalet. Chalet overhead and wide-view exports derive from the original customer description. All are actual Three.js output, not stock examples or Cycles renders.

## Retained boundaries and cleanup
Chromium uses software WebGL. WebKit checks cover UI, source and history, not its PBR GPU/export path; physical iPhone testing was not performed. No architectural optimization or construction/survey/regulatory approval is implied by camera or file validation. Option A remains unchanged: cloud rendering is off, AI is not configured and server persistence is temporary.

The completed one-shot transport and PNG repair workflow were removed. The repeatable floor/camera workflow is contents:read and includes the new PNG regression, with no commit/deploy step. Cleanup commit e689646f86d5d248c3f8da567c84d470d93c64da changes no application source; the deployment stays pinned to 3c971cd.

Refresh the same preview URL without clearing local browser data, rebuild the material preview and use the floor/camera controls. Existing saved geometry is not regenerated or replaced. Keep an exported MASAR project JSON for important work.
