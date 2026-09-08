# Resumed customer verification — 2026-09-08

## Exact state
Application commit: `887aea9b999af3aecca0d6dae08920df4e06e0f8`.
Live candidate: https://masar-customer-preview.onrender.com .
Application branch: `audit/masar-customer-journey-20260908`; PR #11 remains unmerged.
The interrupted-session continuation discovered and preserved completed implementation rather than applying the older QA branch over it. This continuation changed verification/documentation only; it did not modify the application or redeploy any existing service.

## Fresh observed verification
Run: https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/34276559335 .
Job: `102230902750`; completed successfully at 2026-09-08T20:45:43Z.
- All 492 Node tests passed; no failures or skipped tests in this suite.
- Actual HTTPS customer journey: 14/14 checks in Chromium and 14/14 in WebKit.
- Original customer text was 2,191 characters, preserved exactly and not shortened.
- Tested mobile viewport: 390 x 844 with touch/mobile context. Additional layout checks at 320 and 768 pixels; desktop screenshot at 1440 x 1000.
- Both browsers submitted the original description, produced the chalet, downloaded its actual JSON and restored it after a browser reload through IndexedDB.
- Both browsers checked Back preserves input, switching warehouse-to-chalet restores a nonzero bedroom programme, invalid/infeasible area errors stay visible inside the dialog, and native invalid field errors are visible.
- No unhandled page errors in either browser.
- Live /api/health, /api/ready, /api/version returned 200; deployed commit matched the approved source. Five public application modules/styles matched source bytes exactly.

## Actual downloaded output, same in both browsers
- Project type: chalet; one level; plot: 20 x 25 m (500 m²); bedrooms: 3.
- 17 authored spaces including two circulation spaces. The existing totals.rooms field counts 15 non-circulation spaces; these are different counts, not contradictory test results.
- Conceptual room/polygon area total: 144.009 m². This is not a certified net usable-area takeoff.
- Conservative conceptual building envelope, including wall allowance and detached pool WC: 150.732 m², within the requested 120–160 m² interval. This is not permit gross floor area.
- Plot area outside that envelope: 349.268 m², including pool, parking and other outdoor allocations; not all of it is garden.
- Main programme includes three bedrooms; master ensuite and dressing; guest entrance, majlis and guest WC; living, dining, kitchen, pantry, laundry, shared WC; circulation; detached pool WC.
- Site allocations include parking 2.7 x 5 m, pool 6 x 3 m, pergola/covered-session position 4 x 3.5 m, BBQ/preparation position 2.8 x 1.4 m, and rear landscaping.
- Model validation reported no blocking errors for overlaps, plot bounds and its implemented connectivity checks. This is not architectural approval.

## Architectural quality is still provisional
The family circulation space is approximately 1.158 x 10.419 m in the canonical geometry. The client's request to avoid long corridors is not fully satisfied; this remains a design-quality issue, despite successful generation. Actual clear widths after wall finishes, furniture fit, master-room usable shape, glazing privacy, daylight, ventilation, pool safety and construction detailing require further architectural review. A space's presence does not prove adequacy. No structural, municipal-code, fire, accessibility or MEP approval is claimed. The generator remains a constrained concept template, not a general architectural solver.

## Hosting boundaries
Preview storage is explicitly ephemeral; important projects should be exported to MASAR JSON. External AI is not configured. Option A is unchanged: no cloud Blender worker and no new paid storage/compute. The old masar-blender-preview remains on its old release; it is not the corrected URL above. No main, production-v4, ACS or dawaee change occurred in this continuation.

## Evidence
Artifact `10075964961`: `masar-resumed-customer-evidence`, 1,443,266 bytes.
Archive SHA-256: `4d5d0bb22f0436536492e2c5172d2e0ba5f8d8a278536b5786a584935b4c26ff` (GitHub artifact service/log).
Contains actual downloaded MASAR-Chalet-20x25.json, source-match report, model-result report, Node log and both browsers' reports/screenshots. Artifact was fetched via the GitHub connector; extraction in the chat container was unavailable, so no claim of local archive extraction is made.
