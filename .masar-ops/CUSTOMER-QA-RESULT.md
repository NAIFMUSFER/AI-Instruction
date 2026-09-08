# MASAR — exact customer journey QA, 2026-09-08

## Published candidate
URL: https://masar-customer-preview.onrender.com
Service: masar-customer-preview / srv-dag72o740ujc738cd8s0.
Workspace: My Workspace; compute plan Free; Frankfurt; automatic deployment disabled.
Source: audit/masar-customer-journey-20260908 at 887aea9b999af3aecca0d6dae08920df4e06e0f8.
Deploy dep-dag72on40ujc738cdch0 became live at 2026-09-08T20:35:30Z.
The live check compared five served source files byte-for-byte with this commit and checked /api/health, /api/ready and /api/version.
No existing ACS, dawaee, original MASAR, Blender preview or previous quality preview service was modified. A previously existing audit/masar-chalet-generation-20260908 was discovered and preserved, not overwritten. PR #11 keeps this deeper candidate separate for later reconciliation.

## Exact reproduction, not a guess about prompt length
The complete customer brief is tests/fixtures/customer-chalet-ar.txt: 2,191 characters, unchanged. The previous 12,000-character input limit was not reached.
On the older published Blender preview, its parser selected warehouse and zero bedrooms because of the ancillary store/pantry mention, despite the principal villa/chalet request.
The uncorrected default path could generate a wrong warehouse; it was not a universal frozen submit button.
A second real mobile-width browser observation changed that misclassified selection to chalet and submitted. The modal remained open, bedrooms remained 0, and the error was rendered only in #toasts OUTSIDE the dialog. No #modal-error existed.
Observed message: المشروع السكني يحتاج من 1 إلى 16 غرفة نوم ضمن نطاق المولّد.
Evidence: before-correction-diagnostic.json and old-release-hidden-error.png in live acceptance run 34275998294, recorded 20:41:41Z.

## Implemented repairs
shared/model.js::understand now resolves principal project intent, accepts unit-rich dimensions, retains the requested area interval, and attributes the garden relationship to the actual room in the phrase.
src/app.js::reportError displays errors inside the open dialog with role=alert and focus/scroll handling. Native invalid fields also display an in-dialog message. Back preserves the complete original description. Switching project type cannot leave a residential project at zero bedrooms.
The confirmation UI exposes editable minimum and maximum building area. Invalid or unsupported combinations return an explicit message; the cap is not silently discarded.
A compact one-storey, three-bedroom residential concept is provided for the supported area/plot envelope, with guest entrance and bathroom, living/dining/kitchen, pantry, laundry, master ensuite/dressing, and detached pool WC plus parking/pool/outdoor allocations. This is a constrained concept template, not free-form architectural reasoning.
The budget is checked against a conservative ground envelope including a conceptual wall allowance and the detached service. It remains a measurable locked requirement after edits. This differs from net room area and is not a permit-area calculation.
An additional spatial QA pass widened a too-narrow service passage, stopped detached services from distorting the main building's garden facade, and separated slab/roof envelopes so they do not cover the open yard between buildings. Stair warnings are absent when no stair is present.

## Observed acceptance results
Render build logs at 20:35:01Z: 492 Node assertions passed; 0 failed.
Spatial QA run 34274903198: success, including the existing Chromium/WebKit HTTP tests, 56 standalone interactions, exact-customer acceptance and existing independent IFC fixtures.
Published acceptance run: https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/34275998294
Chromium mobile-width customer journey: 14 passed, 0 failed, no uncaught page errors.
WebKit mobile-width customer journey: 14 passed, 0 failed, no uncaught page errors.
Both pasted the original brief, reviewed the correct chalet/3-bedroom/20x25/120–160 values, exercised invalid range and invalid field recovery, generated, downloaded the real project JSON, and restored it after reload through IndexedDB. Layout checks included 320, 390 and 768 pixels.
Published material-viewer checks: 9 passed. The actual customer model produced nonblank Three.js pixels; room picking worked; the downloaded Blender contract contained all 17 spaces; the dialog resized and reopened; no third-party runtime requests or uncaught page errors were observed.
The independent IFC4 check used the project downloaded from the live UI: 134 geometry shapes decoded, no schema/EXPRESS issues, no geometry failures. This verifies the file, not building compliance.

## Actual downloaded customer model
Original text retained: true; 2,191 characters.
Plot: 20 x 25 m = 500 m².
Residential storeys: 1 (an assumption exposed for confirmation, not a fact stated by the user).
Bedrooms: 3; no unrequested stair.
Net room/floor area under the existing MASAR metric: 144.009 m².
Conservative conceptual building envelope including wall allowance and detached pool WC: 150.732 m².
Remaining land outside that envelope: 349.268 m²; includes outdoor circulation, parking, pool and seating, not all green space.
Generated space count: 17 including two circulation spaces.
Model blocker count: 0 in the implemented concept checks; unchecked engineering and qualitative requirements remain explicitly open.
Family living: 4.824 x 4.245 m. Kitchen: 3.666 x 3.087 m. Additional bedrooms: each 4.824 x 3.087 m.
The master is L-shaped, with a separate ensuite and dressing space; its net room area is 13.032 m², not the full bounding rectangle.
Important architectural review item: the family distribution corridor is still approximately 1.158 x 10.419 m. No claim is made that the user's preference to avoid long corridors is fully achieved. Master/guest-room shapes and proportions, furniture fit, kitchen island, sliding glazing and privacy, natural ventilation/daylight, acoustic separation from the pool, outdoor services and detailed pergola/BBQ design need further designer review.

## Delivery and operational boundaries
Artifact 10075825011, masar-customer-live-verified, 3,838,425 bytes.
SHA-256: b372e0f0bba2996721bd257809388ad795711518181d4a8677e50b3b5edfb73f.
Contains customer-delivery/MASAR-Chalet-20x25.json downloaded through the actual UI, the tested source ZIP, standalone HTML, IFC, Blender-scene JSON, screenshots, source hashes and live reports. The new source ZIP was assembled from the tested checkout; it was not re-extracted and rerun in this live workflow. Do not claim a clean-ZIP replay for this new package.
Database remains ephemeral; export important projects as MASAR JSON to the user's device. No paid plan, durable storage or cloud Blender worker was activated. The improved material preview and scene export are client functions, not hosted image rendering.
The primary constrained template supports one storey and three bedrooms, no elevator, up to one parking place, and the documented oriented plot envelope; unsupported changes fail explicitly. Four truly distinct compact alternatives are not certified by this audit. Existing broader generation remains available without this particular budget constraint.
Automated WebKit and software-rendered Chromium are not physical iPhone testing. A valid model and passing software tests do not constitute architectural, structural, fire, MEP, pool safety, accessibility or Saudi-code approval.
