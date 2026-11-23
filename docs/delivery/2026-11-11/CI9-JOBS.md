# CI9 final verification — 2026-11-11

**PASS: all six triggered workflows and all 17 jobs succeeded. No failures, cancellations, retries or skipped jobs.** This completes the repository CI gate for the bounded guest-roof increment. It does not establish deployment, live AI quality or production database migration state.

Head: `064f4a96fdc1941f010b0f6ab814c765acd260c5`. Tree: `9b99a6771cf6a8a9783b80989310436cea110496`. Tested PR merge: `af3a66bd4c09155b90d42a49fdabea7e8c65f992`. Observed: `2026-11-11T16:39:43.659Z`.

All 17 terminal full logs were fetched, inspected and sanitized (3,482,631 bytes). [Machine inventory](evidence/ci9-jobs.json) records every run, job, step outcome and SHA256 of each sanitized log.

| Job | Result | Observed evidence |
|---|---|---|
| [Async delivery and mobile recovery · 130643582654](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456978/job/130643582654) | SUCCESS | Async Chromium/WebKit recovery keeps exactly one generation; auth 393/1280, guest three journeys, mobile one-POST/reload/pixels, connected 393/1280/no-WebGL and panel 37 all passed. |
| [auth · 130643583113](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456959/job/130643583113) | SUCCESS | Shipped auth 393/1280 and all three guest journeys passed; normal cleanup completed. Full-log duration 10m7.856s fits the bounded 15-minute job budget. |
| [contracts · 130643582924](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456981/job/130643582924) | SUCCESS | Foundation contract suites passed; complete step states and log hash retained. |
| [Connected nested lock UI and authority boundary · 130643583226](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456989/job/130643583226) | SUCCESS | Nested semantic-lock UI and authority-boundary contracts passed. |
| [Read-only 2D packets and Chromium-WebKit UI · 130643582906](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456970/job/130643582906) | SUCCESS | Actual 2D UI: 138 assertions, Chromium and WebKit, viewport widths 320/393/800/1280. Synthetic inputs; no API upload or external request. |
| [4 · Security and configuration · 130643583121](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583121) | SUCCESS | Backend/configuration security: 377 assertions passed. |
| [2 · JS ⇄ Python parity and browser-mirror suites · 130643583697](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583697) | SUCCESS | Parity 8, mirrored suites 17, Node remediation 7 and dependency-free 4 targets passed, including the strict import-wait regression. Scoped browser probes are not renderer acceptance. |
| [8 · Frontend build gates (index guard · integration · API base) · 130643583718](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583718) | SUCCESS | Frontend/index/source build gates passed. |
| [Delivery critical journeys · 130643583794](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583794) | SUCCESS | Critical Python 27 targets, Node 14 targets and actual Chromium 3 targets passed: guest, connected workspace and two exact approved fixtures in 24 views. |
| [6 · Deployment closure (content, not the live site) · 130643583839](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583839) | SUCCESS | Deployment content closure: 767 assertions passed. This is not a live deployment check. |
| [9 · Docker image builds · 130643583879](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583879) | SUCCESS | Actual Docker image roof helper and provenance: 17 assertions passed. |
| [7 · Dependency audit and lock contract · 130643583900](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583900) | SUCCESS | 33 dependency/provider/remediation targets passed; actual Python/npm advisory scans reported no known findings at 16:11:07/09 UTC. |
| [3 · Real Chromium (Playwright — this job MAY use the network) · 130643583977](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583977) | SUCCESS | Full Chromium: boot 33/33, visual 326/326 across four fixtures × 11 modes, DOM/ARIA 136/0, direct browser 12/12 and Node scene 3/3. All eight CSP attack classes blocked; zero boot CSP violations. |
| [5 · Accessibility (DOM contract of the shipped page) · 130643583991](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643583991) | SUCCESS | DOM accessibility contract passed. Formal WCAG/assistive technology is outside this scoped job. |
| [1 · Python contracts (py_compile + phase suites) · 130643584026](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130643584026) | SUCCESS | 14 Python targets passed, including 14 offline mirror-preparation regression tests. |
| [10 · Collect every test log · 130659713240](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130659713240) | SUCCESS | Collected 46 evidence files; artifact 13872817172, 4,078,626 bytes, SHA256 f4cb9e0a0693fb9a9cd92cf4568b50d5c730398dcf1aec8f9eaea130bdc79f53. |
| [CI required (mark THIS one as the required status check) · 130659713305](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/job/130659713305) | SUCCESS | Main aggregate confirmed all ten mandatory main-workflow jobs succeeded. Separate triggered workflows also succeeded; this does not establish branch-protection enforcement. |

## Completed customer-journey evidence

Google, Async and critical each executed the complete shipped guest suite: fresh desktop/mobile sample, canonical system-default roof, explicit roof removal/restoration and retained removal preference, local edit, exact download/reload, JSON import, unsupported-file preservation, two tabs, denied storage, late recovery with/without interaction, unchanged legacy roofless/authored imports, explicit guest with stored credentials, zero guest auth/private/provider requests, and useful no-WebGL fallback. These are controlled test-origin journeys, not production accounts or paid generation.

Guest roof Python/JS parity passed 10 cases; roof helper passed 28 cases; actual local-handler integration and delayed-import regression passed. Critical geometry-independent readers and Arabic PDF extraction also passed. Connected fixtures exercised revision/approval/locks, exact derived 3D, exports, restore and no-WebGL handling on desktop/mobile. Short-request recovery passed in Chromium and WebKit with exactly one synthetic generation.

Google completed normally: log span 16:09:21.744–16:19:29.600 UTC (10m7.856s); the actual auth/guest step began 16:10:13.096 and all three guest journeys passed at 16:19:28.662. Cleanup completed at 16:19:29.550. The only preceding budget change was the overall job bound from 10 to 15 minutes; individual waits, assertions, recovery delays and the two-second viewer gate were unchanged. CI8 remains historically canceled and is not relabeled green.

The full main boot/visual check ran 16:11:30.868–16:30:47.650 and passed 33 boot plus 326 visual checks across four fixtures and eleven modes. DOM/ARIA 136 checks passed at 16:36:21.446, with axe-core and actual assistive technologies explicitly unverified. The main aggregate succeeded after all mandatory jobs; required-check branch settings were not changed or claimed.

## Current-head visual evidence

[Approved artifact 13872186153](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/artifacts/13872186153) was downloaded and its ZIP independently hashed: `cebd060c482233da85197f31c6e190f33e2036104e76954b293bb83dbb534b4f`. It contains 35 files, including 24 original screenshots. The frontend specialist inspected all 24 current-head images through four contact sheets and read the actual metadata.

Environment: four logical CPU cores, Linux HeadlessChrome 151, ANGLE SwiftShader, economy preset, animated transitions disabled. Viewports: 1440×900 and 393×852. These are desktop automation viewports, not physical phone tests.

| Fixture / viewport | First view ms | Slowest preset ms | Meshes / triangles | Roof source |
|---|---:|---:|---:|---|
| residential 1440×900 | 1472.067 | 1348.394 | 67 / 804 | artifact |
| warehouse 1440×900 | 1269.555 | 1368.453 | 72 / 864 | assumed |
| residential 393×852 | 1337.952 | 690.087 | 67 / 804 | artifact |
| warehouse 393×852 | 1316.767 | 518.424 | 72 / 864 | assumed |

All 24 presets met the unchanged two-second bound; identity/hash remained consistent across every view. All four frame-p95 values are null with one interval sample, and the frame target is false: smooth 20/33ms interaction is not verified. Current revisions and hashes are embedded in the inventory.

Geometry is visible and useful in all six presets; the warehouse aerial view is fully framed and its interior racks/lane readable. Remaining limitations are visible: mobile revision badges obscure some upper geometry; the lower inspector covers part of a door/dock; the navigation note overlaps the lower cutaway edge. The basic residential fixture has an empty stairs-labelled core and an upper exterior door without access geometry. No traversability or complete architectural BIM claim is supported. Residential roof geometry is canonical; the warehouse roof is two explicitly assumed presentation pieces with zero canonical roof meshes, and its options disclosure is collapsed in these screenshots.

## Release boundary

[Collected main evidence](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43055456986/artifacts/13872817172): 46 files, 4,078,626 bytes, SHA256 `f4cb9e0a0693fb9a9cd92cf4568b50d5c730398dcf1aec8f9eaea130bdc79f53`. Actual package preparation selected the verified HTTPS kernel.org Ubuntu mirror in all five browser/critical jobs; the mandatory gpgv/Ubuntu keyring, metadata and APT package checks stayed enforced.

Netlify preview 6af4932b97cf687ca08c80ec intentionally canceled at the review-branch ignore stage; published_at is null. No deployment or merge was performed. This report is evidence for the completed CI gate; it does not convert fixture success into a live provider, production authorization or production database claim.
