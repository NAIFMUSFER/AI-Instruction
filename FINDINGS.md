# ACS — consolidated audit and remediation

Evidence recorded on 2026-09-26. This report combines the customer, engineering,
backend, frontend and architecture streams. The ordering is a judgment about
customer impact, not a measured conversion or revenue forecast.

## What would most change whether an engineering office pays

1. **A defensible building result.** Reproducible opening-validation misses and
   false positives have fixes with failing-first tests. That does not establish
   structural adequacy, physical stair traversal, complete accessible routes or
   reliable import into Revit. Independent engineering acceptance remains a
   prerequisite for selling a construction-ready result.
2. **A demonstrable end-to-end customer journey.** The live cold visitor saw an
   authentication screen with no visible brief input or example result. This
   prevented evaluation of the Arabic villa, contradiction handling and exports.
   Required authentication is an observed product choice, not a broken-login
   finding. Whether a new customer can reach a useful building remains unverified.
3. **An accountable operator for confidential drawings.** The public privacy
   disclosure sends provider/retention questions to an unnamed operator without
   a visible contact action. Identifying that operator and establishing the
   applicable provider contract is **an operational/commercial problem, not a
   demonstrated code defect**. It cannot be solved by inventing privacy promises.

The code fixes are proposed on independent branches. None of this audit was
merged to `main` or deployed to production. Blocked customer/device acceptance
is explicitly distinguished from passing local contracts below.

## Findings ordered by impact

| Priority | Finding and customer cost | Disposition | Evidence |
|---|---|---|---|
| High | Invalid opening data could pass validation or raise inside the repair loop; overlapping doors/windows could go unreported. This can yield misleading geometry or abort generation. | Fixed in engineering PR: validate dimensions/edges before conversion, compare stated wall heights, preserve a shared collision ledger, and include single-room models. | E1–E3; engineering defect table. |
| High | A window on a clear exterior part of a partly shared edge could be reported as internal; vertically separated windows could be reported as colliding. Unnecessary repair can damage sound input. | Fixed with aperture-specific neighbour checks and stated vertical intervals; unknown dimensions remain unknown. | E1–E3, positive controls and corpus comparison. |
| High | The available output evidence does not establish full structural support, stair geometry, door swings/clearances or complete cross-level traversal. A clean validator result cannot stand for those judgments. | Open model/engineering acceptance boundary. No invented geometry or regulatory thresholds were added. | E4; coordinate review of villa, hotel, office, clinic and warehouse fixtures. Fresh live generation and Revit are unverified. |
| High | A failure after a provider stream started could silently submit a second request through the compatibility transport. The first error was masked and another request could incur cost. | Fixed in backend PR: fallback only for absence of the stream method; a started transport's failure propagates. | B1; injected stream creation/entry/decoding/exit failures and historical mutations. |
| High | Repair usage was absent from the returned generation stage summary, including paid malformed repair replies. A missing-stream SDK could also consume budget before any request was sent. | Fixed repair telemetry and transport budget placement. The stage summary remains a bounded trace, not a complete billing ledger. | B1; no-repair, repeated-repair and malformed-repair controls. |
| High | The public visitor cannot evaluate generation/export without authentication; the requested Arabic villa and hostile inputs were therefore never submitted. | Observed friction; authenticated acceptance remains blocked. No fake successful journey or account creation was substituted. | C1; CUSTOMER-REVIEW.md. |
| High | Provider identity/retention and operator accountability cannot be settled from the public disclosure. It also discloses no interface deletion control for uploaded originals. | Operator decision and evidence required. Actual authenticated deletion behavior was not tested. | C2; visible Arabic/English privacy page. |
| Medium | Advanced panels left keyboard focus on their opener or stranded it after closure; architectural controls lacked programmatic labels and meaningful icon names. | Fixed in frontend PR: synchronous entry focus, careful return focus, and generator-owned accessible markup. Panels remain nonmodal. | F1–F3; same-tick, no-model, delayed-load and intentionally moved-focus controls. |
| Medium | Legacy generation has token/time/rate bounds but no monetary ceiling per request. Killing a local worker cannot recall an accepted upstream request. | Disclosed limitation. No unsupported dollar cap or pricing estimate supplied. | B3; provider budget, generation and API source inspection; synthetic failure suites. |
| Medium | Deterministic Arabic coverage diagnostics omit several ordinary Saudi terms and associate `قبو` with parking. | Diagnostic vocabulary gap recorded. It does not prove the live language model fails these words. No blanket basement-to-parking semantic rule added. | E4; full vocabulary table in ENGINEERING-AUDIT.md. |
| Medium | Old security assertions rejected workspace/render modules solely because they were already deferred instead of eagerly imported. | Fixed delivery guards require a unique declared loading path and loader. Existing escaping/malicious-input checks remain. | F4; sound eager/lazy cases and deliberate missing/duplicate ownership/loading. |
| Evidence gap | Actual Intel GPU capacity, phone experience, real Three.js draw calls/texture memory and headset traversal were not measured on the requested devices. | No performance claim, GPU optimization or ray/path-tracing default change. | F5 and external-verification table. |
| Deferred intentionally | Additional whole-module deferral, Redis installation and folder migration lack measured justification under their stated constraints. | Keep the loading graph, declared single-instance deployment and source layout. Supply a conditional feature proposal and reversible plan. | F6, B4 and A1; details below. |

## Measurement record and regression comparison

<!-- ACS:CURRENT-STATE:BEGIN — dated audit evidence, not rolling deployment claims -->

The requested commit `9e3e472d6de893c8cad8b72eb870bf5768f20147` was measured
unchanged. The observed main head was
`adec616aa5191315991fb9439cee83efbb719b8f`, with **766** subsequent commits:
`git rev-list --count 9e3e472..adec616` and
`git merge-base --is-ancestor 9e3e472 adec616`. Work used the observed head to
preserve subsequent product development. Both exact-command baselines are in
[BASELINE.md](BASELINE.md), including verbatim nonzero outputs.

The exact requested bare `ACS_ENV=test bash tools/ci_run.sh` exits **64** with
`ci_run: --runner is required`. It is not represented as a full suite pass.
The expanded harness invokes each discovered target through the declared runner.
Its initial **242** invocations produced **30** nonzero exits. Six initial
Phase-1 Node invocations lacked their shared-scope runner; those outputs are
retained, and their corrected invocations add **4** passes and **2** DOM-dependent
failures. The complete baseline therefore records **248** invocations and **32**
nonzero exits. These are invocation outcomes, not a count of product defects.

Reproduce discovery with:

```sh
TMPDIR=/tmp/acs-audit-tmp python3 docs/audit/2026-09-26/run_baseline.py "$PWD" /tmp/acs-audit-results
```

Create the temporary directory first. The harness expects the audit virtualenv
beside the checkout; [baseline-results.json](docs/audit/2026-09-26/baseline-results.json)
records the exact individual commands, including the corrected Phase-1 runners.
The baseline deliberately retains missing Chromium/vendor capabilities and the
measured host/namespace PID mismatch. No product behavior was weakened to make
those environments look green.

| Branch replay | Invocations / nonzero exits | Comparison scope |
|---|---:|---|
| Untouched baseline including corrected runners | 248 / 32 | Complete recorded baseline |
| Backend | 250 / 32 | Same failures and exit statuses; new provider/corpus suites pass |
| Engineering | 249 / 32 | Same failures and exit statuses; new geometry suite passes; final report wording separately checked after CI caught a documentation regression |
| Frontend | 244 / 29 | Compared with original 242 / 30 discovery: two stale security failures fixed; new guard suite passes; new browser suite explicitly refuses missing Chromium and passes in the prepared environment |
| Customer/consolidation application source | 242 / 30 | Same original outcomes; no application source changes |
| Architecture | Exact Phase-0 replay | Same gate/invocation/environment outcomes; application source unchanged |

The frontend's new missing-browser refusal was not silently added to BASELINE.md
or called a pass. Its positive prepared-browser result and CI workflow install
the necessary browser. Source gates passed on all branches; patched deployment
verification reported **733 passed / 0 failed**. Reproduction: the four source
gate commands and `ACS_ENV=test python3 tests/deploy/verify_deploy.py` listed in
BASELINE.md. Generated test outputs, package-lock changes and the generated
bundle-report artifact were excluded from commits.

### Defect and guard proof

| Evidence | Measured outcome | Command |
|---|---|---|
| E1 — opening geometry | Initial 19 tests: 21 failing subcases and 4 errors. Final suite: 20 tests pass. | `python3 tests/remediation/test_audit_engineering_openings.py` on engineering branch; red summary retained in its report |
| E2 — geometry mutations | 14 killed, none survived | `python3 tests/remediation/test_audit_engineering_openings.py --mutations` |
| E3 — existing corpus | 165 models; no changed validator results, mutation or nondeterminism | `python3 tests/remediation/test_audit_engineering_openings.py --compare-baseline adec616` |
| E4 — manual review inputs, IFC and vocabulary | Explicit coordinates, issue lists, serialized IFC census and synonym results for 5 fixture types | `python3 tests/remediation/test_audit_engineering_openings.py --evidence` |
| B1 — provider defects | 10 tests pass, including historical mutation controls | `ACS_ENV=test python3 tests/remediation/test_audit_backend_provider.py` |
| B2 — robustness/repair | 5 tests pass across 165 models; no entry-point exceptions/nondeterminism and no APPLY issue-count increase | `ACS_ENV=test python3 tests/remediation/test_audit_backend_corpus.py`; repeat with `--report` for census |
| F1 — panel focus and generated semantics | 39 passed / 0 failed; 2 focus-source mutations and 3 semantic removals rejected | `node tests/remediation/test_audit_frontend_panels.js --mutations` with `ACS_CHROMIUM` set to the prepared browser |
| F2 — original panel timing | 37 passed / 0 failed; eager/cached opening stays in the click's tick | `node tests/remediation/test_panel_entry.js` with prepared Chromium |
| F3 — existing accessibility scope | 136 passed / 0 failed; generated-panel exclusions explicitly supplemented by F1 | `node tests/remediation/test_accessibility.js` with prepared Chromium |
| F4 — declared loading guards | 12 passed / 0 failed, including 8 deliberately invalid ownership/loading paths | `node tests/remediation/test_audit_frontend_guards.js` |
| F5 — scene contracts | Scene limits 171/0; adapter benchmark 81/0 with `three_js_real: false` | `node tests/remediation/test_scene_limits.js`; `node tests/remediation/test_scene_benchmark.js` in prepared environment |
| G1 — actual build/closure guards | 8 guards each returned sound/broken/restored exit codes 0/1/0 | `python3 docs/audit/2026-09-26/audit_guard_mutations.py . /tmp/acs-audit-guard-evidence` |
| A1 — proposed structure | 142 mapped files: 77 root Python, 21 JSON resources, 44 frontend files. No omitted scope or duplicate targets; proposed measured graph has no cross-feature cycles; reverse-edge mutations detected. | `python3 docs/audit/2026-09-26/measure_structure.py --verify` on architecture branch |

G1's exact mutations and commands are in
[guard-verification.md](docs/audit/2026-09-26/guard-verification.md). A deliberate
failure alone is insufficient: its sound and restored controls also passed.

The coordinator also applied the independent backend, engineering and frontend
source commits to a detached local integration checkout. All **22** targeted
commands passed there: E1–E3; B1/B2; F1–F4; existing topology, corpus, regulatory,
provider integration/accounting and module-graph suites; the four source gates;
deployment verification; bundle report; and documentation claims. The prepared
browser and baseline virtualenv were used. This establishes compatibility of
those changes under the tested contracts, not a replacement for future merged
CI or external product acceptance.

The robustness sweep found no caller-input mutation in opening identity, visual
compilation or validation. `autofix(PROPOSE)` mutated **108** inputs through its
documented SAFE_NORMALIZATION allowance; `autofix(APPLY)` mutated **162** as
expected. Those are API semantics, not an immutable-API guarantee. B2's report
and `test_autofix_propose_boundary.py` reproduce the distinction.

### Source weight and measured operating load

F6 commands: `python3 tools/bundle_report.py`,
`node tests/remediation/test_module_graph.js`, and
`python3 tests/remediation/test_bundle_report.py`.
The untouched audit snapshot contained **2,131,718 B** of first-party JavaScript,
**1,665,849 B** initially loaded source and **465,869 B** deferred. Source bytes
are not compressed network bytes or parse-time measurements. The focus fix adds
**2,383 JS bytes** and generated labels add **498 HTML bytes**. No speedup is
claimed. The maintained source counts remain generated in the existing
`KNOWN-ISSUES.md` current-state block on the frontend branch.

B4 used the read-only Render command
`get_metrics(resourceId="srv-d9qtsv3m8hqs73967680", workspaceId="tea-d9qth1iju40c73btab90", metricTypes=["cpu_usage","memory_usage","memory_limit","instance_count","http_request_count"], resolution=300)`.
Its returned window, **2026-09-26 18:04–19:04 UTC**, showed **1 instance**,
**112,824,320 B** memory against **536,870,900 B**, and
**0.0017482133–0.0019023867 CPU units**. Request samples contained one HTTP 200
response followed by zero-request samples. This is an idle observation window,
not a load-capacity test or a percentage of the starter plan allocation.

<!-- ACS:CURRENT-STATE:END -->

## Boundaries retained and decisions not to make speculative changes

**Geometry and authority.** `test_rule_source_boundary.py` continues to require
`NOT_EVALUATED` for regulatory review. New findings compare represented geometry
only. Missing wall/window heights, lift footprints, stair flights or load data
are not manufactured. IFC serialization contains real space, wall, door and
window entities and metre units; unsupported lift objects/property losses are
disclosed. That is useful exchange evidence, but not independent Revit acceptance.

**Provider and security.** B3 is reproduced by
`rg -n 'limited|consume|max_retries|stages\[:|estimated_cost_usd|ACS_PRICE' acs_provider_budget.py acs_understand.py acs_understand_api.py`
and the failure-path table in BACKEND-AUDIT.md. Synthetic provider tests trace
timeouts, rate limiting, malformed JSON, repeated unresolved issues and connection
failure to classified API errors or disclosed partial drafts. They do not simulate
a paid live outage. Upload tests exercise byte-derived media type, decoded-size
bounds, PDF/image/JSON rejection and traversal-like names. The connected source
upload accepts PDF and supported raster images; native DWG support was not claimed.
The lightweight DXF guard is not a complete hostile-CAD parser.

**Redis.** The measured idle, declared single-instance topology does not justify
adding a distributed store now. A missing package is not evidence that it should
be enabled. The existing memory limiter's locking and startup invariant are
tested; counters reset on restart. Activate the tested Redis path with an actual
store and pinned dependency when multiple instances or persistent quotas become
a real requirement. No dependency or deployment scaling was changed.

**Deferral and rendering.** No additional module satisfied all the requested
whole-module deferral conditions. PBR stays eager because the viewer depends on
its plate/rack helpers. Other candidates have additional importers or install
startup listeners/wrappers. The import order, lazy declarations, API origin and
importmap hashes remain intact. Raw-WebGL adapter measurements cannot substitute
for the owner's Intel GPU; ray/path tracing was not enabled.

**Feature structure.** Retain the present layout for now. The proposal combines
authority/layout into engineering changes, distinguishes durable plan revisions
from connected workspace orchestration, and keeps the browser's late-bound model
workbench together. Each proposed feature owns models/services/controllers and
exposes a defined public surface. Application composition depends on features;
features must not import composition. The complete old-to-new map and permitted
dependency directions are in STRUCTURE-PROPOSAL.md.

Conditional migration first establishes ownership/runtime seams, then moves an
isolated leaf behind compatibility exports, updates resource/generator paths and
all path-sensitive gates together, and repeats that small reversible unit only
while independently green. Browser moves require a valid external-module
generator workflow; the historical inline splitter is not suitable for the
already-externalized page. Import order, lazy ownership, CSP, extraction, deploy,
documentation and container contracts must remain checked at each stage. No
customer benefit or developer-time saving was measured to justify doing this now.

## What remains unverified

The following outcomes all mean **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
They are not passing tests and are not newly proven product defects.

| Required acceptance | Concrete missing environment/evidence |
|---|---|
| Arabic villa to a rendered building; impossible briefs; empty/long/mixed-language/words-as-numbers attacks | Authenticated live ACS session; the customer stream used only the public UI and did not read source or bypass login |
| Cold/warm throttled 3G first paint, time to type, requests and transfer bytes; physical phone repeat | Supported browser throttling/cache/network measurement controls and a phone; no tool-call duration substituted |
| Live panels and IFC/glTF/DXF/SVG opened in the customer's software | Authenticated generated model and external viewers |
| Fresh building generations and independent Revit scale/storey/entity acceptance | Provider-backed live generation and Revit; repository fixtures/serialization were the available substitute and are labelled as such |
| Owner's Intel GPU frame budget, real texture memory and draw calls; WebXR | Actual machine, real renderer measurement and headset |
| Complete screen-reader/RTL accessibility acceptance | Real assistive technology and independent complete interaction review; local DOM/CSP/keyboard checks cover only their declared scope |
| Actual provider outage, billed usage, retention and cancellation of upstream computation | Controlled provider environment, operator contract and billing records |
| Live Supabase policies, production logs, native hostile DWG | Authorized external systems and the relevant native parser environment |
| Full structural design, physical stairs and resolved pedestrian/egress routes | Missing model contracts plus responsible engineering review; no code thresholds inferred |

C1/C2 reproduction uses the supported live browser: `customerTab.goto(...)`,
`customerTab.reload()` and `customerTab.playwright.domSnapshot()` on
`https://sprightly-selkie-d906c3.netlify.app/`, followed by the visible
`الخصوصية وحفظ البيانات` link and the new tab's DOM snapshot. Exact commands and
the expectation/happened/cost records are in CUSTOMER-REVIEW.md. The deployment's
commit was not identified from that UI; it is not equated with the source baseline.

## Reviewable deliverables

| Stream | Full report | Independent PR |
|---|---|---|
| Customer and consolidation | [CUSTOMER-REVIEW.md](CUSTOMER-REVIEW.md), this FINDINGS.md, baseline and guard evidence | This branch: `audit/acs-customer-20260926` |
| Engineering | [ENGINEERING-AUDIT.md](https://github.com/NAIFMUSFER/AI-Instruction/blob/audit/acs-engineering-20260926/ENGINEERING-AUDIT.md) | [PR #184](https://github.com/NAIFMUSFER/AI-Instruction/pull/184) |
| Backend/platform | [BACKEND-AUDIT.md](https://github.com/NAIFMUSFER/AI-Instruction/blob/audit/acs-backend-20260926/BACKEND-AUDIT.md) | [PR #183](https://github.com/NAIFMUSFER/AI-Instruction/pull/183) |
| Frontend/delivery | [FRONTEND-AUDIT.md](https://github.com/NAIFMUSFER/AI-Instruction/blob/audit/acs-frontend-20260926/FRONTEND-AUDIT.md) | [PR #185](https://github.com/NAIFMUSFER/AI-Instruction/pull/185) |
| Architecture | [STRUCTURE-PROPOSAL.md](https://github.com/NAIFMUSFER/AI-Instruction/blob/audit/acs-architecture-20260926/STRUCTURE-PROPOSAL.md) | [PR #182](https://github.com/NAIFMUSFER/AI-Instruction/pull/182) |

Application edits have separate owners. Shared baseline documents are identical
on the branches. Reports are reviewable draft deliverables, not a release
approval. Before any future merge, rebase onto the then-current main, compare
against BASELINE.md and require the actual combined branch checks to pass.
Production adoption is outside this audit's authorized branch-only workflow.
