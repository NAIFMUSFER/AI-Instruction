# PR190 CI4: observed job results

Head: `3bc06725203533f59a7e4ec9358b0df4b5c9dff6`. Tested merge: `5e0f86b18d96c26fe2ae55d3f03bd934c30e3366`.

**The CI gate passed:** all 31 returned PR-triggered workflows and 42 jobs completed successfully, including collector and aggregate. No job was canceled and no job step was skipped. The aggregate printed “all mandatory jobs succeeded.” This satisfies the requested CI prerequisite for the next review increment; it does not mean PR190 was merged, deployed or made mandatory by branch protection.

All 42 full logs were downloaded and scanned. Job/step outcomes and suite verdicts were reviewed, with selected detailed reading of regression contexts. After environment loss, the logs were fetched again and this report reconstructed from those records. This is CI evidence review, not deep source review of every dependency installer or source line.

The real Chromium job completed BOOT 33/33 and VISUAL 326/326 across four fixtures × 11 modes. The verifier ran 11:18:16–11:28:00 UTC (about 9m44s). Real Chromium DOM/ARIA accessibility reported 136 passed, zero failed and one scoped note. Axe-core and actual assistive technologies were not tested. The CSP probe blocked eight attack classes with zero boot policy violations. All 12 direct browser targets and three later Node scene targets passed; scene limits reported 175 assertions.

Critical delivery passed 26 Python targets, 12 Node targets and three browser targets. Google and Async passed actual shipped authentication at 393 and 1280 pixels and all three guest journeys. The connected lifecycle passed at both widths in two workflows: generation, reload, locks, conceptual approval, SVG, exact 3D, chat revision and logout. The 393-pixel no-WebGL case retained useful 2D/save/approval/export/recovery.

The completed connected sequence verifies explicit approval invalidation before roof removal, one new draft, retained historical approval, saved removal preference across reload/regeneration, restoration, and lock refusal without changes to head/history/provider count. Later approval succeeds. A held comparison prevents revision selection until settlement; a forced historical roof click issues zero writes and preserves head/history. The corrected fixture retains its explicit two-unit requirements; no approval rule or assertion was relaxed.

The dependency job passed all 33 offline targets and its 15-case spatial companion. The required advisory scan ran at 11:18:53 UTC and reported no known Python vulnerabilities and zero npm vulnerabilities. This is the feed observation for this head, not a guarantee against undiscovered or future vulnerabilities.

The approved viewer passed 24 views (two exact synthetic fixtures × six presets × desktop/mobile), identities, selection, floor isolation, keyboard, idle rendering, context loss and disposal. The frontend specialist inspected all 24 images before the outage. The recovered [visual artifact](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/artifacts/13851585137) matches the original verified SHA-256 `6cdb020700a693656eff12902445358d0d6f7d1ca7aac2a4ebfe05501e6cf335`; QA re-read its measurement JSON.

| Synthetic fixture | Viewport | First view, ms | Slowest preset, ms | Meshes / triangles |
|---|---|---:|---:|---:|
| residential | 1440×900 | 1492.927 | 1360.905 | 67 / 804 |
| warehouse | 1440×900 | 1382.194 | 1349.486 | 72 / 864 |
| residential | 393×852 | 1500.031 | 666.715 | 67 / 804 |
| warehouse | 393×852 | 1187.850 | 520.489 | 72 / 864 |

These are Linux Headless Chrome 151 observations with four logical cores and SwiftShader economy quality, with animated transitions disabled. Every preset completed within the hard 2,000ms bound. **All four frame-p95 values are null, with one sample each, and their frame-rate target is false. Smooth rendering targets remain NOT VERIFIED.** These observations are not physical iPhone or hardware-GPU benchmarks.

Known visual limits remain: mobile badge/inspector overlays cover part of the model, fixture labels include English IDs, and these fixtures do not establish physical stairs or traversable vertical circulation. Synthetic controlled-provider output does not prove arbitrary live AI quality or construction-ready BIM.

The [collector artifact](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/artifacts/13851197789) contains 46 files and 4,067,719 bytes. Netlify branch/PR previews were intentionally canceled before build with no deployed URL. No deployment, production DB migration, real customer account, paid-provider request or branch-protection change is established by this review.

Machine-readable measurements, all step conclusions and sanitized-log hashes: [ci4-jobs.json](evidence/ci4-jobs.json). Full sanitized logs are retained outside the repository.

| Workflow / job | Result | Log reviewed | Evidence |
|---|---|---|---|
| Plan-first frozen-baseline CAD export / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626098/job/130489019644) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626098) |
| Plan-first warehouse zone allocation constraints / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626181/job/130489018687) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626181) |
| Plan-first explicit element provenance / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626138/job/130489018820) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626138) |
| Plan-first warehouse operational metrics / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626100/job/130489018626) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626100) |
| Plan-first frozen-baseline SVG export / svg-contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626203/job/130489019046) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626203) |
| Plan chat candidate admission / candidate-admission | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626110/job/130489018445) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626110) |
| Google sign-in / auth | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625995/job/130489017931) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625995) |
| Async generation delivery / Async delivery and mobile recovery | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625818/job/130489017455) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625818) |
| Plan-first generic role-area constraints / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626025/job/130489018562) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626025) |
| Authenticated Plan-first HTTP command boundary / plan-http-command-boundary | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626064/job/130489017900) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626064) |
| Plan-first foundation contracts / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625855/job/130489017606) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625855) |
| Plan-first warehouse dock-zone constraints / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626088/job/130489018616) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626088) |
| Plan-first warehouse zone allocation ratios / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625760/job/130489017640) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625760) |
| Plan-first warehouse expansion reserves / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625777/job/130489017380) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625777) |
| Plan-first approved nested 3D provenance / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626044/job/130489018494) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626044) |
| Authenticated PlanStore session boundary / plan-store-authenticated-session | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625984/job/130489017646) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625984) |
| Plan-first warehouse dock allocation by zone / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626040/job/130489018258) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626040) |
| Plan-first warehouse lane centerline constraints / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626009/job/130489018036) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626009) |
| ACS warehouse vertical stage gate / vertical-stage-contract | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626087/job/130489018255) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626087) |
| Plan-first frozen-baseline PDF export / pdf-contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626010/job/130489017898) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626010) |
| Plan-first registered typology lifecycle / lifecycle | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626046/job/130489018449) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626046) |
| Plan-first residential measured scorecard / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626024/job/130489021607) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626024) |
| Plan-first connected semantic locks / Connected nested lock UI and authority boundary | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626012/job/130489018408) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626012) |
| Plan-first warehouse rack/lane conflicts / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626065/job/130489018717) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626065) |
| Plan-first semantic revision diff / contracts | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626053/job/130489018522) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626053) |
| ACS warehouse soft area fit / regression | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625770/job/130489016913) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625770) |
| Plan chat isolated provider worker / isolated-plan-chat-worker | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625775/job/130489017325) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625775) |
| ACS warehouse program feasibility / regression | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626067/job/130489018067) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626067) |
| Plan chat stale-safe orchestration / stale-safe-chat-orchestration | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626030/job/130489017213) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626030) |
| Plan-first 2D review UI / Read-only 2D packets and Chromium-WebKit UI | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625934/job/130489018060) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010625934) |
| CI / 3 · Real Chromium (Playwright — this job MAY use the network) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489018415) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / Delivery critical journeys | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489018918) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 1 · Python contracts (py_compile + phase suites) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489018939) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 6 · Deployment closure (content, not the live site) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489018945) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 2 · JS ⇄ Python parity and browser-mirror suites | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489018955) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 9 · Docker image builds | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489019074) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 4 · Security and configuration | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489019116) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 7 · Dependency audit and lock contract | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489019163) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 8 · Frontend build gates (index guard · integration · API base) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489019177) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 5 · Accessibility (DOM contract of the shipped page) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130489019189) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / 10 · Collect every test log | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130495733852) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |
| CI / CI required (mark THIS one as the required status check) | success | yes | [job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041/job/130495733878) · [run](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43010626041) |

The connector exposes first pages only. This inventory covers the 31 returned PR-triggered workflows and 42 returned jobs; it makes no assertion about untriggered workflows or complete production readiness. Explicitly scoped Node/DOM renderer or network checks remain NOT VERIFIED beyond their measured contract.
