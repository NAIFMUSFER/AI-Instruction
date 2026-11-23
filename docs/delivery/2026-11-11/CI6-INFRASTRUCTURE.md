# CI6 infrastructure snapshot — 2026-11-11

Observed: `2026-11-11T15:00:09.709Z`. PR191 head `6a0dfd85e31b0c89df3eac0076d0e7a424084d75`. **Not accepted: no completed guest-roof browser journey on this head.**

The first attempt contains 16 jobs: 10 succeeded, 3 failed, 2 were canceled, and Async remained running at this snapshot. Full terminal logs were read and sanitized; hashes and step results are in [the attempt1 inventory](evidence/ci6-attempt1-inventory.json). The eight main contract/build jobs succeeded, and the dependency job actually completed its advisory scans. This does not replace the missing browser gates.

Failures occurred in runner dependency preparation: Ubuntu mirror DNS resolution failed for `azure.archive.ubuntu.com`, `archive.ubuntu.com` or `security.ubuntu.com`. The critical Poppler install ended with exit100; Chromium installation ended with exit1. Google and 2D reached their bounded workflow limits during preparation. No dependency, test, timeout, or browser requirement was removed.

| Job | Attempt1 result | Observed scope |
|---|---|---|
| [Read-only 2D packets and Chromium-WebKit UI](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040358084/job/130590342790) | cancelled | Canceled during Chromium dependency setup after repeated DNS errors; no 2D browser run. |
| [Async delivery and mobile recovery](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040358010/job/130590332080) | in_progress | Still installing dependencies/browser engines; final log unavailable. |
| [Connected nested lock UI and authority boundary](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040358136/job/130590178128) | success | Semantic lock regression passed. |
| [auth](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040358468/job/130590353109) | cancelled | Canceled during Chromium installation after repeated DNS errors; no auth/guest browser run. |
| [9 · Docker image builds](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406195) | success | Image and runtime packaging probe passed (17 assertions). |
| [8 · Frontend build gates (index guard · integration · API base)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406552) | success | Build/index/source gates passed. |
| [2 · JS ⇄ Python parity and browser-mirror suites](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406570) | success | Pure Node/parity gates passed; scoped probes do not verify browser rendering. |
| [4 · Security and configuration](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406620) | success | Security/configuration contracts passed (377). |
| [7 · Dependency audit and lock contract](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406664) | success | 33 dependency-contract targets and actual Python/npm advisory scans passed. |
| [1 · Python contracts (py_compile + phase suites)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406703) | success | 13 Python targets passed. |
| [6 · Deployment closure (content, not the live site)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406819) | success | Deployment content closure passed (767); no live deployment. |
| [3 · Real Chromium (Playwright — this job MAY use the network)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406828) | failure | Chromium OS-dependency installation failed with DNS errors, exit1; browser suites skipped. |
| [5 · Accessibility (DOM contract of the shipped page)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590406910) | success | DOM accessibility contract passed; no formal WCAG/browser acceptance. |
| [Delivery critical journeys](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130590407005) | failure | Poppler installation failed resolving Ubuntu mirror, exit100; critical suites skipped. |
| [CI required (mark THIS one as the required status check)](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130596255983) | failure | Aggregate correctly failed mandatory jobs. |
| [10 · Collect every test log](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130596255999) | success | Evidence collector completed; no browser acceptance implied. |

## Same-head retry — separate evidence

The integration agent triggered one retry of main and Google under the authorized CI verification task. Critical retry [130596778360](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43040357993/job/130596778360) again failed at **14:55:32 UTC**, resolving the Ubuntu mirror while downloading `libpoppler134` and `poppler-utils`, exit100. Its subsequent missing-artifact failure correctly reports that no test output exists. Main Chromium and Google were still installing dependencies at this snapshot. No additional retry was made.

The API reports eight success job IDs in attempt2 with identical original logs/timestamps. They are carried-forward results, not eight new executions. The separate [attempt2 inventory](evidence/ci6-attempt2-inventory.json) records the original ID for each. Async initial-attempt evidence and any later cancellation will be archived separately when terminal.

## Independent test correction awaiting the next head

A deterministic fixture synchronization defect was independently reproduced: the preceding authored model and recovery import both had width24, so the width-only wait could pass before the asynchronous file read/import. The new focused test executes the actual import handler and wait predicate with a delayed read; the corrected predicate requires the recovery model identity and width. The original timeout and downstream assertions remain. This test-only correction is now wired into dependency-free Node parity, critical Node and Google contracts. Local focused regression PASS, CI gate 78 PASS, and diff checks pass. No production source or bundle changed. The next head must complete all gates; this snapshot is not acceptance.

Netlify preview cancellation at the ignore stage is intentional under the no-deployment instruction (deployment `6af47dcc8712ccea0740740a`, unpublished). It is not a successful deployment. Full logs remain outside git; the inventories retain sanitized hashes and step outcomes.
