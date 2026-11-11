# CI8 job review — 2026-11-11

Observed `2026-11-11T16:08:01.815Z`. PR191 head `6e44ae478e351346124865fcae14d00ee7e99fdc`, tested merge `ec15def123a52b247d409b963a9f545c64303e0f`.

**Six workflows,17 terminal jobs:16success and1canceled. This head is not accepted as fully green.** All17 full logs were fetched, inspected and hashed in [the machine inventory](evidence/ci8-jobs.json). Main, critical, Async, foundation, locks and2D completed successfully. Google completed all auth/guest assertion PASS messages but was canceled at its overall10-minute budget during final cleanup. The main aggregate is green and does not cover this separate Google workflow. No assertion, individual test wait, recovery delay or2-second approved-viewer gate was removed or increased.

| Job | Result | Observed scope |
|---|---|---|
| [Read-only 2D packets and Chromium-WebKit UI · 130625320526](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323919/job/130625320526) | success | Actual Chromium/WebKit2D review138 assertions at320/393/800/1280 widths passed; synthetic input, no production/provider claim. |
| [Async delivery and mobile recovery · 130625321209](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050324083/job/130625321209) | success | Chromium/WebKit recovery exactlyone generation, auth393/1280+guest3, mobileonePOST+pixels, connected393/1280/noWebGL and panel37 passed. |
| [contracts · 130625321295](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323892/job/130625321295) | success | Foundation contracts passed; exact step outcomes retained in inventory. |
| [Connected nested lock UI and authority boundary · 130625321706](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323840/job/130625321706) | success | Nested semantic lock UI/authority contracts passed. |
| [1 · Python contracts (py_compile + phase suites) · 130625320510](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625320510) | success | 14 Python targets passed, including14 mirror helper regressions without apt. |
| [5 · Accessibility (DOM contract of the shipped page) · 130625320889](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625320889) | success | DOM contract1 passed; formal WCAG/browser acceptance not established by this job. |
| [4 · Security and configuration · 130625321003](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321003) | success | Security/configuration377 passed. |
| [3 · Real Chromium (Playwright — this job MAY use the network) · 130625321011](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321011) | success | Main real Chromium PASS: boot33/33 and visual326/326 (four fixtures×11 modes), DOM/ARIA136/0 with scoped axe/assistive-technology limits, direct browser12/12, Node scene3/3. Full boot15:40:44→16:00:23; job finished16:06:14. |
| [8 · Frontend build gates (index guard · integration · API base) · 130625321073](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321073) | success | Frontend/index/source build gates passed. |
| [2 · JS ⇄ Python parity and browser-mirror suites · 130625321109](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321109) | success | Parity8 +mirrors17 +Node7 +dependency-free4 targets passed, including strict import wait. Scoped browser probes explicitly NOT VERIFIED. |
| [Delivery critical journeys · 130625321115](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321115) | success | 27 Python +14 Node +3 actual Chromium targets passed. Guest3, connected393/1280/noWebGL, exact approved24 views; all original assertions retained. |
| [7 · Dependency audit and lock contract · 130625321135](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321135) | success | 33 dependency/provider/remediation targets passed; real Python/npm advisory scans clear15:39:39 UTC. |
| [9 · Docker image builds · 130625321248](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321248) | success | Actual Docker roof-helper/provenance17 passed. |
| [6 · Deployment closure (content, not the live site) · 130625321742](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130625321742) | success | Deployment content767 passed; no live deployment. |
| [auth · 130625321145](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323808/job/130625321145) | cancelled | Overall10min budget canceled job15:48:19.545 after auth393/1280 and guest3 assertion PASS15:48:19.454. Browser close/step completion not verified; not a successful job. |
| [CI required (mark THIS one as the required status check) · 130641801870](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130641801870) | success | Main aggregate succeeded: all10 mandatory main-workflow jobs succeeded. This aggregate does not include the independent Google workflow and does not prove branch protection. |
| [10 · Collect every test log · 130641801915](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/job/130641801915) | success | Collected46files/4,075,485B; artifact13871057379 sha256c8f48d05ddc87fa2f779b9f7f2dc2533063150394f3d37780143eaed9c26e6c1. |

## Setup repair and exact timing

Terminal2D, Google, critical and Async logs each report `https://mirrors.kernel.org/ubuntu/` selected. The executed helper only prints this after real gpgv checks against the existing Ubuntu archive keyring for all four suites, expected release identity/freshness checks, and local mirror-list replacement. TLS, APT package signatures/hashes, package requirements and network policies remain enforced. The logs do not expose a signature fingerprint; the success evidence is the mandatory signed-path execution and subsequent actual apt/browser installations.

Google job130625321145 started15:38:11 UTC; setup ended15:39:06.950 (~56s). Shipped auth393/1280 passed15:39:10.754/13.689. Guest393 ran~136s; guest1280/storage/recovery ran~409s. All3 guest journeys reported PASS15:48:19.454, followed91ms later by runner cancellation15:48:19.545. No application assertion error was reported. This remains CANCELED, with final browser-close/step exit unverified. Independently, identical guest coverage passed in critical15:46:54 and Async15:47:43; both jobs completed successfully.

## Approved artifact evidence and limits

Downloaded artifact13869527738 ZIP SHA256 matches GitHub: `7befe395d3af456ed8df29945de7283319b240b68a5e3aab53e4f7a511da2580`. It includes24screenshots and exact revision/hash metadata: two synthetic approved fixtures, six views, desktop1440×900/mobile393×852. Four logical cores, LinuxHeadlessChrome151, SwiftShader, economy preset, animated transitions disabled.

| Fixture/viewport | First view ms | Slowest preset ms | Meshes/triangles | Roof source |
|---|---:|---:|---:|---|
| residential 1440×900 | 1233.785 | 1029.427 | 67/804 | artifact |
| warehouse 1440×900 | 1029.948 | 1005.207 | 72/864 | assumed |
| residential 393×852 | 1020.946 | 264.873 | 67/804 | artifact |
| warehouse 393×852 | 918.961 | 235.051 | 72/864 | assumed |

All24 preset transitions met the unchanged2s gate. All four frame-p95 values are null with one interval sample each, and the frame target is false: smooth-frame performance is not verified. IDs/hashes agree across all six views. Residential roof comes from the approved artifact; warehouse roof is an explicitly assumed presentation element. These are fixtures, not arbitrary live AI-generation or physical-phone evidence. The frontend specialist inspected all24 images through four contact sheets plus the actual metadata: all six presets show useful geometry, the aerial warehouse is fully framed, entrance/detail and interior racks/lanes are readable. Remaining limitations: the mobile revision badge obscures part of the upper roof/façade/back rack; the detail inspector obscures the lower door. The residential fixture is basic box geometry with an empty stairs-labelled room and an upper exterior door without access geometry. No physical circulation or building-completeness claim is supported. Roof option disclosure is collapsed in these screenshots. These observations are qualitative; the original24 images are retained.

Netlify deployment6af48bde7896c3f657aa6b4e intentionally canceled at its review-branch ignore stage; published_at is null. It is not a successful deployment. No merge, production release, paid provider request or Step4b implementation occurred. Full sanitized logs remain outside git; [The inventory](evidence/ci8-jobs.json) includes exact step states, log hashes, artifact receipts and current visual measurements.

Main boot33/33 and visual326/326 completed16:00:23 UTC after four fixtures×11 modes; deterministic DOM/ARIA136/0 completed16:06:00, with axe-core and real assistive technology explicitly unverified. [Collected evidence](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/artifacts/13871057379) contains46files; SHA256 `c8f48d05ddc87fa2f779b9f7f2dc2533063150394f3d37780143eaed9c26e6c1`. [Approved-viewer artifact](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323939/artifacts/13869527738) contains the original24screenshots.

The integration owner approved a separate Google overall-job budget10→15minutes based on the measured completion above and two independent successful guest executions. That next candidate must pass its own workflows; this historical canceled result is retained. No claim is made that repository branch checks are enforced by protection settings.
