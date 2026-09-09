# Local visual downloads — verified runtime 56c48c2

## Published state
The existing customer preview at https://masar-customer-preview.onrender.com now serves runtime 56c48c2db177878b44932feea195ff10f7aee7d5. Render deploy dep-dagpk4vqj5pc73d3asb0 became live at 2026-09-09T17:41:22.948355Z. Only MASAR_APPROVED_COMMIT was merged into the existing service environment. No new service, paid plan, worker, GPU, durable storage, main/production-v4 merge or ACS/dawaee change was made.

## User journey
Open the current project, open «معاينة المشروع والخامات», choose finishes/furniture/quality and press «معاينة بالخامات». Below the actual viewer, «تنزيل صورة المعاينة PNG» exports the current camera view at 640×480 or 1280×960, including a visible concept/not-Blender-render footer and the source revision. «تنزيل مجسم GLB كامل» exports the same canonical render contract as a full glTF 2 binary visual model. It can be imported through Blender File > Import > glTF 2.0. Neither download calls a render job endpoint or requires an account.

This is not Cycles rendering, automatic native .blend production, a MASAR import format or BIM round-trip. The cloud-render button correctly remains disabled in Option A. JSON project exports remain the way to preserve editable geometry, original brief and history; GLB is a visual handoff.

## Source and safety invariants
Downloads remain disabled until a real PBR scene is installed. Changing finish, quality, room or furniture settings invalidates the output buttons until the viewer is refreshed. Async output is rejected if the source/settings changed or the dialog closed. Opening another material dialog never reuses a disposed scene as current.

GLB is built from a separate complete scene: roofs stay present even when cutaway hides them in the viewer, and selection highlight cannot contaminate exported materials. Furniture follows the selected presentation setting. Exported metadata explicitly identifies the model and revision and whitelists semantic element/room IDs; original prompts, comments and account data are not added. Renderer size, camera aspect and selected materials are restored after the bounded PNG capture. No room, floor, constraint or revision is changed by visual export.

Local exports are bounded to 4,000 box objects and a 24 MB GLB buffer. Larger scenes retain JSON handoff. These limits do not certify low-memory physical-phone performance. The public shell cache version was increased without clearing IndexedDB or user projects.

## Reproduction and verification
Predeployment run 34383389786 succeeded before runtime was committed: 540 Node assertions, new browser downloads, all existing customer/room/inspection/layout/recovery suites, three-browser HTTP/offline regressions, 56 standalone flows and 12 independent IFC fixtures. Two earlier candidate runs were correctly blocked: a truncated staged method and a minimal DOM test fixture were corrected; an unrelated system-Chrome APT index hash mismatch was isolated by disabling only that unused index in the disposable CI runner, not by disabling signature or hash checks.

Published acceptance run 34384507173 succeeded. See LIVE-34384507173.json for machine-derived details. Eleven served public modules, including the two built Three.js bundles, matched the pinned checkout byte-for-byte. Health/readiness, CSP/HSTS, disabled cloud-render capability and explicit ephemeral persistence were verified.

Live results: 540 Node passes, 146 browser checks with zero failures. This includes 15 Chromium local-export checks and 8 WebKit UI/JSON/history checks, plus existing affected product journeys. The complete original 2,191-character chalet brief was used. Full before/after history comparisons cover settings, exporting, dialog disposal and reload.

Three actual downloaded GLBs passed Khronos validation with zero errors and zero warnings. Informational entries concern unused UV attributes on plain-colour box geometry; they are retained in the reports. Warm and slate live downloads were independently imported in network-isolated Blender 4.5.13 LTS. Their 399 and 383 mesh objects respectively matched every canonical object's identity and bounding geometry, including 21 roof pieces in both cases. The maximum observed coordinate deviation was approximately 0.00000162 m. No architectural or engineering accuracy certification is implied by numeric file checks.

The delivered source ZIP was extracted into a new clean CI directory; every manifest file was checked, 540 Node tests passed again, rebuilt standalone HTML matched byte-for-byte, and the actual Chromium local-export journey passed 15 checks from that extracted source. After downloading the live artifact, its SHA-256, all delivery SHA256SUMS entries and all 107 source-file manifest entries were independently checked in the conversation container. A separate direct network check from that container was unavailable due to DNS resolution; live verification was performed by GitHub's runner, not claimed to have run in that local environment.

## Evidence
Predeployment run: 34383389786, artifact 10117038169, SHA-256 5161a866b62bfbfc1b40e6dbe1cd5177c8bc57b955be38ec7f3472b5cda835cb.
Live run: 34384507173, artifact 10117307463, SHA-256 b80b5e01e034eeb80143bfcf8a7a8dd007bf50fda228983de5135e70001d6099.
Delivered source ZIP SHA-256: d859cc4c551aeb9afd1a4f8fff6d114244c70605265b88e0477e3ce0b298ccda.

The one-shot transport was removed. Workflow-only commit 59da0d6c3a885d00ab654809c7b811a5498f6c18 makes subsequent acceptance contents:read and removes commit/deploy steps. The deployed application remains pinned to 56c48c2.

## Retained limits
Chromium used software WebGL. WebKit checks here cover UI, source JSON and history, not its PBR GPU export path; no physical iPhone test was performed. PNG is an actual browser-view capture, not a photorealistic Cycles image. Original architectural constraints and the conceptual nature of the model are unchanged. Server persistence remains ephemeral and aiConfigured=false. No paid or hosted Blender rendering was enabled.
