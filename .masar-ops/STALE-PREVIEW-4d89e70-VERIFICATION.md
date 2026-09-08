# Stale-preview recovery — verified runtime 4d89e70

## Deployment
The existing https://masar-customer-preview.onrender.com service was updated in place. No new service was created. Render service `srv-dag72o740ujc738cd8s0`, workspace `tea-d9qth1iju40c73btab90`, remains Free, Frankfurt, automatic deploy disabled. Only MASAR_APPROVED_COMMIT was changed through the environment-variable merge operation. Deploy `dep-dag7uo9t0dsc73e9mn50` became live at 2026-09-08T21:35:12Z with source `4d89e70843e78f2e89cc6b519745c39239020242` on `audit/masar-customer-journey-20260908`. No main/production-v4/Blender-base merge and no ACS/dawaee service modification.

## Reproduced gap, without guessing the user's browser state
The screenshot alone does not prove the exact locally saved project or a browser-cache fault. The previous 887aea9 application still generated a generic grid for the built-in chalet description without a numeric building-area interval: nine spaces, one unrequested stair, a conservative conceptual envelope of 273.978 m² on its 18×25 plot. The customer's long description missing only its final area paragraph also fell back to nine spaces and one stair, with 312.458 m² on 20×25. The complete 2,191-character request including 120–160 m² already generated the compact 150.732 m² concept. Changing finishes or upgrading application files did not regenerate an already saved old model. The old visualization panel did not clearly identify the source project/revision or distinguish a demo.

## Implemented repair
For the supported single-storey three-bedroom chalet/pool programme without a numeric area, the confirmation form now offers an editable 120–160 m² conceptual envelope as an explicitly labelled assumption, not a claimed user request. An explicitly provided interval remains requested and unchanged. Unsupported combinations are not silently widened.

The visualization dialog is now titled «معاينة المشروع والخامات». Its source card identifies the opened project, site dimensions, bedrooms, conceptual envelope, unbuilt remainder and exact revision. A fresh example is labelled «مثال توضيحي — ليس مشروعك». PBR canvas metadata and the downloaded Blender scene are checked against the current canonical model ID and revision ID.

Restored generic chalet models are not silently changed. A warning offers «مراجعة الوصف وإنشاء توزيع مستقل». The original project must save successfully first. Cancelling leaves original geometry, prompt and identity unchanged; confirming creates a distinct project from the same original description. The original remains retrievable through Projects. This is a new proposal from the original brief, not automatic migration of manual design edits.

Native material-selection controls are reflowed into one column on small screens to fix a reproduced WebKit 320px overflow; no options or controls were clipped to pass the test. The public service-worker shell version was incremented. No IndexedDB/local-project deletion or cache-clearing instruction was used.

## Verified evidence
Predeployment workflow 34280749890 succeeded and committed the runtime only after all gates: 502 Node tests; source/recovery journeys 15 Chromium and 14 WebKit; exact-request journeys 14 per browser; existing HTTP regressions 28 each on Chromium/Firefox/WebKit; existing standalone interactions 56. Render's build repeated 502 passed, 0 failed.

Live workflow https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/34281488503 completed successfully. Its checkout and the live /api/version both identify 4d89e70843e78f2e89cc6b519745c39239020242. Seven served public modules were compared byte-for-byte with that source. Health/readiness, CSP/HSTS and disabled rendering capabilities were verified.

The published-site reports total 63 checks, 0 failures: source/recovery 15 Chromium + 14 WebKit; original full request 14 Chromium + 14 WebKit; actual 20×25 PBR/source/export checks 6 Chromium. No unhandled page errors or third-party runtime requests occurred in the source/recovery and PBR journeys. PBR was exercised using software-accelerated Chromium; WebKit coverage here is the UI, source identity, recovery and full-request flow, not its PBR renderer or physical iPhone hardware.

The actual project downloaded from the live UI retained all 2,191 description characters, 17 authored spaces including 3 bedrooms, a 150.732 m² conservative ground envelope and 349.268 m² outside that envelope. Its actual material-view PNG, project JSON and Blender scene JSON are in the live artifact. The material image is not a stock example and is not a Cycles image. Generic-model cancellation and subsequent retrieval were compared against the full original imported fixture, not just its title.

CI artifact 10077595830 SHA-256: 6fad65e58ac077f04d27731d271834f5b591f7d11a209dfb167702ec10794a74.
Live artifact 10077889080 SHA-256: 7ae206cf537d9359f8918482ba8ddd735415901b17109210cddc7f8e2c0b5dc6. Both archives and the live delivery's internal SHA256SUMS were verified after download.

## Customer instructions and boundaries
Refresh the same customer-preview page without clearing browser data. Reopen the material dialog and inspect its source card. For a saved generic chalet, use «مراجعة الوصف وإنشاء توزيع مستقل», review the assumptions and confirm. No retyping is required; the old local project remains available.

Option A remains unchanged: cloud rendering enabled=false and workerOnline=false. No paid worker/GPU or durable store was provisioned. The current account database remains explicitly ephemeral; retain exported MASAR JSON for important work. This change does not certify architectural quality: the compact concept still has a roughly 10.4 m family corridor, and furniture fit, daylight, privacy, pool safety, construction and MEP need specialist review. No claim is made that the screenshot alone identified the user's exact saved model or that every possible stale-cache condition was fixed.
