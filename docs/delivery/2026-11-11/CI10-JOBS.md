# CI10 — PR192 initial head (11 November 2026)

Head `b88f560ca35f6ef6dc4acf6cb2d06af13676432e`; tree `f71c0eefc758cd500b75234c9c024c5456e93c8f`. Actual tested merge `6328d61eb51040e63d44f74b4fe57546cb9275d6` into PR191 base `064f4a96fdc1941f010b0f6ab814c765acd260c5`.

**Not accepted:** all30 triggered workflows are terminal:27 success and3 failure. All41 jobs are terminal:37 success,4 failure,0 canceled. There were no reruns. API `per_page=100` returned `total_count=30`; completeness was checked beyond the connector's30-item default. Every job's complete sanitized log was fetched and its steps/outcomes inspected:41 logs, 3,331,469 bytes, with SHA-256 hashes in [inventory](evidence/ci10-jobs.json).

The three underlying failures are independent; the fourth failed job is the mandatory aggregate:

1. **Generic object validation:** the new stair validator incorrectly broadened its boundary to unmarked non-stair object collections. The unchanged existing test passes on both checked baseline snapshots. CI10 has6 passing cases and1 error in this seven-case suite.
2. **Connected IFC:** legacy full-export opening validation ran in the connected spaces-only scope and blocked a valid approved fallback model. Seven fallback cases ran with1 error; subsequent Async browser steps were skipped.
3. **Measured documentation:**65 actual mobile DOM/CSS assertions passed, then the generated CURRENT-STATE block differed from the measured module/byte values. Full page boot, visual matrix and later main-browser accessibility suites did not execute.

Local diagnoses/fixes are archived separately in [fix evidence](evidence/ci10-fixes/manifest.json). They do not turn this failed head green. The document `--fix` regenerated its block, but the full local documentation gate remains unavailable/partial without Chromium; its guard unit tests passing do not change that result.

## Actual browser and artifact evidence

- Google shipped auth passed at393/1280;3 guest journeys completed at17:27:49 UTC. All job steps and cleanup completed successfully.
- Critical gate passed31 Python targets,17 Node targets and4 real Chromium targets. Guest3 journeys passed17:30:36; connected393/1280/no-WebGL passed17:30:59–17:31:39; existing24 approved-fixture views passed17:32:35.
- New approved stairs browser test passed17:33:00 UTC:12 preset images plus2 upper-arrival images, actual tread selection and stable source/revision/model identity. Physical traversal remains NOT_VERIFIED. Image quality/occlusion and exact device measurements require inspection of the artifact, separate from this assertion result.
- Actual 2D Chromium/WebKit checks passed at320/393/800/1280, including selection, locks, import races, CSP negative controls and no outside requests.
- Critical artifact [13877017147](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/artifacts/13877017147):5,414,285 bytes; API and upload log SHA-256 `57b064214b9ad18a99a8d7d5d800a347dd02acb12902ffe359cdc4af74cbb5aa`. Download/visual inspection is owned by the integration agent.
- Collected artifact [13876054864](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/artifacts/13876054864):5,603,604 bytes; SHA-256 `cc0ca894b0f586818bb947c5d36adbda5e0b0b9e1a5805ecfa2033d06c01adb5`.

All five package-preparation jobs selected the verified primary HTTPS Ubuntu archive; no DNS fallback or signature bypass was needed in this run. Actual pip/npm advisory feeds completed and reported no known vulnerabilities at17:23:36/38 UTC. Actual Docker image provenance passed18 checks, including execution of the stair helper on a single-storey fixture without inventing a flight.

## Per-job review

| Workflow / job | Result | Evidence reviewed |
|---|---|---|
| [ACS warehouse program feasibility / regression](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459628/job/130686110155) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [ACS warehouse soft area fit / regression](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459682/job/130686110142) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [ACS warehouse vertical stage gate / vertical-stage-contract](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459530/job/130686110349) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Async generation delivery / Async delivery and mobile recovery](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459658/job/130686116450) | FAILURE | FAIL: seven residential fallback cases include one IFC_EXPORT_FAILED. Earlier async13, auth31, workspace34, recovery20 passed; actual browser steps did not execute. |
| [Authenticated Plan-first HTTP command boundary / plan-http-command-boundary](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459715/job/130686110415) | SUCCESS | Unittest invocations: 26, 7 methods; all reported OK. |
| [Authenticated PlanStore session boundary / plan-store-authenticated-session](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459576/job/130686109918) | SUCCESS | Declared contract completed; output and step conclusions reviewed. |
| [CI / 3 · Real Chromium (Playwright — this job MAY use the network)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111242) | FAILURE | FAIL: actual mobile layout65 passed, then generated CURRENT-STATE documentation drift. Full page boot/visual and subsequent browser suites did not execute. |
| [CI / 1 · Python contracts (py_compile + phase suites)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111718) | SUCCESS | 14 Python contract targets passed, including14 offline apt-helper cases. |
| [CI / 4 · Security and configuration](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111797) | SUCCESS | 377 backend/config security assertions passed; not adversarial production DB execution. |
| [CI / 6 · Deployment closure (content, not the live site)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111858) | SUCCESS | 772 deploy-content assertions; not live deployment. Vendor/GPU runtime not verified in this job. |
| [CI / 8 · Frontend build gates (index guard · integration · API base)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111881) | SUCCESS | Index guard, frontend integration and configured API-base build checks passed. |
| [CI / 9 · Docker image builds](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686111938) | SUCCESS | Actual Docker build/container:18 provenance assertions passed, including stair helper import/single-storey no-flight policy; no paid request. |
| [CI / 2 · JS ⇄ Python parity and browser-mirror suites](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686112065) | SUCCESS | 8 parity,17 JS-mirror,7 remediation and4 isolated-loader targets passed; import recovery wait regression passed. |
| [CI / 7 · Dependency audit and lock contract](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686112137) | SUCCESS | 33 contract targets passed; actual pip/npm advisory scans report no known vulnerabilities at17:23:36/38 UTC. |
| [CI / Delivery critical journeys](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686112214) | SUCCESS | 31 Python +17 Node +4 actual Chromium targets passed. Guest3, connected393/1280/no-WebGL, existing24 approved views and new14 stair views passed. Stair capture completed17:33:00 UTC; traversal NOT_VERIFIED. |
| [CI / 5 · Accessibility (DOM contract of the shipped page)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130686112218) | SUCCESS | One DOM contract only; formal WCAG explicitly NOT VERIFIED. |
| [CI / 10 · Collect every test log](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130692368316) | SUCCESS | All ten main-job artifacts collected, with downloaded ZIP digests logged; aggregate artifact13876054864 uploaded. |
| [CI / CI required (mark THIS one as the required status check)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459364/job/130692368536) | FAILURE | FAIL CLOSED: mandatory Chromium job failed on documentation drift. This aggregate is not proof that repository branch protection is enforced. |
| [Google sign-in / auth](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459603/job/130686110663) | SUCCESS | Actual shipped auth393/1280 passed; all3 guest journeys passed17:27:49 UTC. Auth31/gateway26 and strict import-wait regression passed; cleanup completed. |
| [Plan chat isolated provider worker / isolated-plan-chat-worker](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459458/job/130686110568) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan chat stale-safe orchestration / stale-safe-chat-orchestration](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459766/job/130686110950) | SUCCESS | Unittest invocations: 4, 2 methods; all reported OK. |
| [Plan-first 2D review UI / Read-only 2D packets and Chromium-WebKit UI](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459745/job/130686111570) | SUCCESS | 10 Python cases plus actual Chromium/WebKit at320/393/800/1280: import/selection/zoom/locks/CSP/no-outside-request contracts passed. |
| [Plan-first approved 3D derived authority / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459644/job/130686110336) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan-first approved 3D lock binding / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459600/job/130686110695) | SUCCESS | Unittest invocations: 1 methods; all reported OK. |
| [Plan-first approved generic object geometry / object-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459733/job/130686110900) | FAILURE | FAIL: malformed-object test expects later INVALID_PROVENANCE, but approval raises PLAN_NOT_READY. Six of seven cases pass; one error. Compiler not invoked. |
| [Plan-first approved nested 3D provenance / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459572/job/130686110522) | SUCCESS | Unittest invocations: 4 methods; all reported OK. |
| [Plan-first approved room presentation geometry / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459871/job/130686111576) | SUCCESS | Unittest invocations: 5 methods; all reported OK. |
| [Plan-first approved warehouse lane geometry / lane-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459604/job/130686112197) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Plan-first approved warehouse station geometry / station-geometry](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459697/job/130686111037) | SUCCESS | Unittest invocations: 6 methods; all reported OK. |
| [Plan-first connected semantic locks / Connected nested lock UI and authority boundary](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459843/job/130686674019) | SUCCESS | Unittest invocations: 13, 8 methods; all reported OK. |
| [Plan-first foundation contracts / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459683/job/130686110952) | SUCCESS | Unittest invocations: 12, 7, 8, 10, 6, 13, 8, 9, 3, 5, 3, 7, 8, 7, 8, 3, 40, 14, 8, 7, 8, 3, 15, 11, 17, 8, 9, 3, 2, 2, 3, 18, 13, 12, 7, 20, 1, 3 methods; all reported OK. |
| [Plan-first frozen-baseline PDF export / pdf-contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459700/job/130686111644) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |
| [Plan-first frozen-baseline SVG export / svg-contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459379/job/130686110242) | SUCCESS | Unittest invocations: 6 methods; all reported OK. |
| [Plan-first generic role-area constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459334/job/130686110182) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first registered typology lifecycle / lifecycle](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459408/job/130686111237) | SUCCESS | Unittest invocations: 2 methods; all reported OK. |
| [Plan-first semantic revision diff / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459556/job/130686110198) | SUCCESS | Unittest invocations: 8, 3 methods; all reported OK. |
| [Plan-first warehouse dock-zone constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459614/job/130686110305) | SUCCESS | Unittest invocations: 9 methods; all reported OK. |
| [Plan-first warehouse lane centerline constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459448/job/130686109990) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first warehouse rack/lane conflicts / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459359/job/130686110266) | SUCCESS | Unittest invocations: 9 methods; all reported OK. |
| [Plan-first warehouse zone allocation constraints / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459789/job/130686111726) | SUCCESS | Unittest invocations: 8 methods; all reported OK. |
| [Plan-first warehouse zone allocation ratios / contracts](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43067459319/job/130686347544) | SUCCESS | Unittest invocations: 7 methods; all reported OK. |

## Release boundary

Netlify review preview `6af4a43986d6aedd3a51d3a4` was intentionally canceled by the review-only guard before publishing (`published_at=null`). Its successful cancellation context is not a successful deployment. See [guard evidence](evidence/ci10-netlify.json). No merge, deployment, migration or paid provider request occurred in this QA review.

Suite counts are not additive: targets, methods, assertions and repeated tests differ. The passing static accessibility job explicitly does not verify formal WCAG. No live generation, production authorization database, physical phone, smooth-frame target, stair traversal, structural adequacy or code compliance is claimed. Repository protection is separate from the CI aggregate and is not inferred from its name.

## Integration visual inspection

The critical ZIP was downloaded and its SHA256 independently matched. All fourteen new stair captures were visually inspected through two contact sheets; native mobile interior and desktop arrival images were also inspected. The47 meshes/564 triangles retained canonical hash `0b709c11674f14ff3e93f451927c062a74aedf49f93eb1b38963b9e913960331`. First view1097.530ms desktop/1102.707ms mobile; worst preset800.717/607.749ms. Four logical cores, Linux Chrome151/ANGLE SwiftShader, economy quality. Frame-p95 remains null with one interval sample: smooth-frame performance is NOT_VERIFIED.

The flights and arrival opening are visible. Cutaway shows one level; detail frames one tread, not an entire assembly. Mobile overlays obscure some geometry. The isolated synthetic core includes an upper exterior doorway; no complete access route, guards or structural support is established. See [exact visual record](evidence/ci10-stairs-visual-review.json). This passing visual check does not change CI10 overall failure.
