# CI11 — PR192 superseded head (11 November2026)

Head `14a2adf25983167f18bda0bba79eda2ce0475c6c`; tree `d2a5afe14b09ff020be22e9953b333d6af736c1d`; actual tested merge `5a1a129d3822c7fdc03dba91417faacb4db4fee2` into base `064f4a96fdc1941f010b0f6ab814c765acd260c5`.

**Not accepted.** All30 workflows terminal:27 success,3 canceled. All41 jobs terminal:36 success,2 failure,3 canceled. No retries. Complete sanitized logs for all41 jobs (3,052,733bytes) were fetched and reviewed with all job/step conclusions; SHA-256 hashes are in [inventory](evidence/ci11-jobs.json). The30-run total was independently checked with `per_page=100`.

The new external IFC reader installed actual IfcOpenShell0.9.0.post1 and ran. Its absence check compared an empty tuple with an empty list, failing at17:41:16 UTC. This does not show an emitted IfcStair. Earlier schema/ID assertions reached before that line; subsequent bounds checks did not execute.32 of33 critical Python targets passed. The failure correctly prevented the generated-source, Node and approved-stair browser stages, so no new stairs screenshots exist for this head.

The integration owner pushed the narrow `len(collection)==0` correction on head `76a90b920d84c9cef8785f3de63f82eaa508154a`, keeping zero-entity semantics unchanged. Existing concurrency canceled three still-running jobs; none is recorded as successful. CI10 evidence remains historical, not acceptance of this head.

Observed partial progress before cancellation:

- Main Chromium:mobile65 and the repaired full documentation gate passed, then5 shipped page-bundle targets, transport7, pixel-analyzer20. Full boot/visual verifier started the villa and then warehouse; it did not emit its final BOOT/VISUAL result. Later accessibility suites were not completed.
- Google:actual auth393/1280 passed, and guest393 reached its journey PASS at17:43:04; desktop guest/final three-journey summary did not complete.
- Async:the original seven-case fallback export suite now passed, as did earlier auth/workspace/recovery contracts. Actual auth393/1280 passed; guest393 reached journey PASS17:44:26 before cancellation. Later workspace/browser stages were not accepted.
- Actual2D Chromium/WebKit suite completed; actual pip/npm advisory checks returned clear17:41:46/47. Docker18 checks passed.

| Workflow / job | Result | Evidence reviewed |
|---|---|---|
| [ACS warehouse program feasibility / regression](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070365052/job/130696284412) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [ACS warehouse soft area fit / regression](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364558/job/130696283868) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [ACS warehouse vertical stage gate / vertical-stage-contract](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363539/job/130696279157) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Async generation delivery / Async delivery and mobile recovery](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363522/job/130696278957) | CANCELLED | CANCELED during guest journey. Prior failing fallback7 nowPASS; async/auth/workspace/recovery and actual shipped auth393/1280 passed. Guest393 reached PASS17:44:26; later workspace/browser stages incomplete. |
| [Authenticated Plan-first HTTP command boundary / plan-http-command-boundary](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364253/job/130696281825) | SUCCESS | Unittest invocations: 26, 7 methods; all reported OK. |
| [Authenticated PlanStore session boundary / plan-store-authenticated-session](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364133/job/130696285004) | SUCCESS | Declared contract output and steps passed. |
| [CI / 6 · Deployment closure (content, not the live site)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696284800) | SUCCESS | 772 deploy-content assertions PASS; not deployed-site acceptance. |
| [CI / 2 · JS ⇄ Python parity and browser-mirror suites](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285297) | SUCCESS | 8 parity,17 JS-mirror,7 remediation and4 isolated-loader targets PASS. |
| [CI / 5 · Accessibility (DOM contract of the shipped page)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285298) | SUCCESS | One static DOM contract; formal WCAG explicitly NOT_VERIFIED. |
| [CI / 7 · Dependency audit and lock contract](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285335) | SUCCESS | 33 contract targets passed; actual pip/npm feeds report no known vulnerabilities17:41:46/47 UTC. |
| [CI / 4 · Security and configuration](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285409) | SUCCESS | 377 backend/config security assertions PASS. |
| [CI / 8 · Frontend build gates (index guard · integration · API base)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285443) | SUCCESS | Index/build/API-base gates PASS. |
| [CI / 1 · Python contracts (py_compile + phase suites)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285585) | SUCCESS | 14 Python contract targets PASS. |
| [CI / Delivery critical journeys](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285621) | FAILURE | FAIL: new IfcOpenShell test compares emptytuple() with emptylist[]. No unexpected IfcStair demonstrated.32/33Python targets pass; later bounds and all critical Node/browser stages not executed. |
| [CI / 3 · Real Chromium (Playwright — this job MAY use the network)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285836) | CANCELLED | CANCELED after actual mobile65, documentation gate,5 page-bundle targets, transport7 and viewport-pixels20 passed. Full boot began villa then warehouse; no final BOOT/VISUAL summary or full acceptance. |
| [CI / 9 · Docker image builds](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696286753) | SUCCESS | Actual Docker18 provenance checks passed, including stair-helper single-storey policy. |
| [CI / CI required (mark THIS one as the required status check)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130699376476) | FAILURE | FAIL CLOSED: mandatory critical failure and canceled mainbrowser prevent aggregate success. |
| [CI / 10 · Collect every test log](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130699376844) | SUCCESS | Collected logs/artifact successfully; no canceled test is promoted to PASS. |
| [Google sign-in / auth](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363702/job/130696280222) | CANCELLED | CANCELED during guest journey. Actual shipped auth393/1280 passed; guest393 journey reached PASS17:43:04. No final3-journey completion. |
| [Plan chat isolated provider worker / isolated-plan-chat-worker](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364195/job/130696283150) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan chat stale-safe orchestration / stale-safe-chat-orchestration](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364450/job/130696309294) | SUCCESS | Unittest invocations: 4, 2 methods; all reported OK. |
| [Plan-first 2D review UI / Read-only 2D packets and Chromium-WebKit UI](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364396/job/130696288248) | SUCCESS | Actual2D Chromium/WebKit320/393/800/1280 PASS including CSP and no-outside-request controls. |
| [Plan-first approved 3D derived authority / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364023/job/130696282326) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan-first approved 3D lock binding / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363589/job/130696280198) | SUCCESS | Unittest invocations: 1 methods; all reported OK. |
| [Plan-first approved generic object geometry / object-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364075/job/130696282845) | SUCCESS | Previously failing unchanged generic-object suite:7 methods PASS. |
| [Plan-first approved nested 3D provenance / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363564/job/130696280773) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan-first approved room presentation geometry / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364306/job/130696283180) | SUCCESS | Unittest invocations: 5 methods; all reported OK. |
| [Plan-first approved warehouse lane geometry / lane-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364155/job/130696283298) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Plan-first approved warehouse station geometry / station-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363955/job/130696281951) | SUCCESS | Unittest invocations: 6 methods; all reported OK. |
| [Plan-first connected semantic locks / Connected nested lock UI and authority boundary](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364802/job/130696284863) | SUCCESS | Unittest invocations: 13, 8 methods; all reported OK. |
| [Plan-first foundation contracts / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363887/job/130696283711) | SUCCESS | Unittest invocations: 12, 7, 8, 10, 6, 13, 8, 9, 3, 5, 3, 7, 8, 7, 8, 3, 40, 14, 8, 7, 8, 3, 15, 11, 17, 8, 9, 3, 2, 2, 3, 18, 13, 12, 7, 20, 1, 3 methods; all reported OK. |
| [Plan-first frozen-baseline PDF export / pdf-contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364479/job/130696286008) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Plan-first frozen-baseline SVG export / svg-contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363802/job/130696281465) | SUCCESS | Unittest invocations: 6 methods; all reported OK. |
| [Plan-first generic role-area constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364042/job/130696284123) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first registered typology lifecycle / lifecycle](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364074/job/130696282240) | SUCCESS | Unittest invocations: 2 methods; all reported OK. |
| [Plan-first semantic revision diff / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364432/job/130696284894) | SUCCESS | Unittest invocations: 8, 3 methods; all reported OK. |
| [Plan-first warehouse dock-zone constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363913/job/130696280554) | SUCCESS | Unittest invocations: 9 methods; all reported OK. |
| [Plan-first warehouse lane centerline constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070363810/job/130696283874) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first warehouse rack/lane conflicts / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364369/job/130696284733) | SUCCESS | Unittest invocations: 9 methods; all reported OK. |
| [Plan-first warehouse zone allocation constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364652/job/130696284339) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first warehouse zone allocation ratios / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364352/job/130696284324) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |

The aggregate failed on both a mandatory failure and cancellation. Its name does not establish branch protection. Logs include partial evidence without converting it into complete journeys. Counts across methods, assertions and targets are not additive. No deployment, live paid generation, production DB authorization, physical-phone performance, walkability or engineering/code approval is claimed.
