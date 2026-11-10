# ACS — consolidated audit and remediation

Evidence recorded on 2026-09-26, with an authenticated follow-up on
2026-09-27 (Asia/Riyadh). This report combines the customer, engineering,
backend, frontend and architecture streams. The ordering is a judgment about
customer impact, not a measured conversion or revenue forecast.

## What would most change whether an engineering office pays

1. **Ordinary briefs must reach a useful draft.** After the user signed in,
   the requested villa and a warehouse both stopped without a saved revision.
   Apartment cases succeeded through an explicitly disclosed calculated fallback.
   The warehouse planner's envelope instructions contradicted the canonical
   geometry contract; the follow-up fixes that instruction rather than weakening
   validation. Successful live generation after adopting the fixes is not established.
2. **The engineering handoff must match its advertised scope.** Actual IFC
   downloads contain spaces, while the multistorey model has named stair/lift
   rooms without physical vertical geometry. A successful scoped review cannot
   establish a walkable building, structural adequacy or Revit acceptance.
   These are material product-contract gaps, not cosmetic folder-layout concerns.
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
| High | Live warehouse generation was told to include an enclosing room, then rejected when that room overlapped its interior zones. The ordinary request produced no revision. | Dedicated connected-workspace warehouse planning policy proposed on the backend branch; strict geometry and true-capacity rejection retained. Live post-fix outcome unverified. | B5; scoped checkpoint reproduction and failing-first provider-message tests. |
| High | The live multistorey draft contains aligned named stair/lift rooms but no physical vertical cores, while the UI reports a scoped interlevel pass. This cannot demonstrate a walkable building. | Engineering and frontend PRs separate core alignment from unverified physical traversal and disclose missing explicit core geometry. The actual geometry gap remains open. | E5, E7, F8; saved model, architecture compilation, coverage and UI contracts. |
| High | The actual connected-workspace IFC download exports spaces only; it does not contain the architectural entities available in the separate legacy exporter. | Open product-contract gap, explicitly disclosed by the current UI and manifest. Revit acceptance remains unverified. | E5; actual downloaded artifact and manifest, independently parsed. |
| High | Natural Arabic bedroom/single-storey phrases were dropped from confirmation; unitless site dimensions lacked a specific unit question. | Narrow parser repair and guarded vocabulary extension proposed on the frontend branch; original quotation provenance retained, ambiguous totals require review. | F7; exact live briefs, failing-first cases, positive controls and mutations. |
| High | Explicit Arabic room roles bypassed some residential access/count checks and could make an existing stair core appear absent. | Exact recognized roles are normalized before and after layout repair, preserving Arabic names and unknown roles. This exposes real missing access; it is not a claim that the villa now completes. Completed details are reused after role-only conversion, but not after geometry changes. | B6; live checkpoint comparison, sound Arabic-role layout, count/access controls and resumed-details mutation tests. |
| High | Invalid opening data could pass validation or raise inside the repair loop; overlapping doors/windows could go unreported. This can yield misleading geometry or abort generation. | Fixed in engineering PR: validate dimensions/edges before conversion, compare stated wall heights, preserve a shared collision ledger, and include single-room models. | E1–E3; engineering defect table. |
| High | A window on a clear exterior part of a partly shared edge could be reported as internal; vertically separated windows could be reported as colliding. Unnecessary repair can damage sound input. | Fixed with aperture-specific neighbour checks and stated vertical intervals; unknown dimensions remain unknown. | E1–E3, positive controls and corpus comparison. |
| High | The available output evidence does not establish full structural support, stair geometry, door swings/clearances or complete cross-level traversal. A clean validator result cannot stand for those judgments. | Open model/engineering acceptance boundary. No invented geometry or regulatory thresholds were added. | E4 fixture coordinate review, supplemented by E5 live revisions. Revit acceptance remains unverified. |
| High | A failure after a provider stream started could silently submit a second request through the compatibility transport. The first error was masked and another request could incur cost. | Fixed in backend PR: fallback only for absence of the stream method; a started transport's failure propagates. | B1; injected stream creation/entry/decoding/exit failures and historical mutations. |
| High | Repair usage was absent from the returned generation stage summary, including paid malformed repair replies. A missing-stream SDK could also consume budget before any request was sent. | Fixed repair telemetry and transport budget placement. The stage summary remains a bounded trace, not a complete billing ledger. | B1; no-repair, repeated-repair and malformed-repair controls. |
| High | Authentication prevented the initial cold-visitor evaluation. After the user signed in, the villa still failed; a deliberately impossible brief was explicitly rejected without identifying the conflicting constraint. | Historical login block cleared. Preserve the failed journeys and inadequate correction guidance as measured outcomes, without claiming silent acceptance of an incorrect model. | C1/C3; dated public and authenticated sections in CUSTOMER-REVIEW.md. |
| High | Provider identity/retention and operator accountability cannot be settled from the public disclosure. It also discloses no interface deletion control for uploaded originals. | Operator decision and evidence required. Actual authenticated deletion behavior was not tested. | C2; visible Arabic/English privacy page. |
| Medium | Advanced panels left keyboard focus on their opener or stranded it after closure; architectural controls lacked programmatic labels and meaningful icon names. | Fixed in frontend PR: synchronous entry focus, careful return focus, and generator-owned accessible markup. Panels remain nonmodal. | F1–F3; same-tick, no-model, delayed-load and intentionally moved-focus controls. |
| Medium | Legacy generation has token/time/rate bounds but no monetary ceiling per request. Killing a local worker cannot recall an accepted upstream request. | Disclosed limitation. No unsupported dollar cap or pricing estimate supplied. | B3; provider budget, generation and API source inspection; synthetic failure suites. |
| Medium | Deterministic Arabic coverage diagnostics omit several ordinary Saudi terms and associate `قبو` with parking. | Diagnostic vocabulary gap recorded. It does not prove the live language model fails these words. No blanket basement-to-parking semantic rule added. | E4; full vocabulary table in ENGINEERING-AUDIT.md. |
| Medium | Reciprocal room-side door records produced coincident physical leaf meshes in the downloaded apartment glTF. | Engineering PR pairs exact reciprocal leaves while retaining both source identities. Slightly different source coordinates remain separate. No unmeasured flicker or frame-rate claim. | E5–E6; exact POSITION vertex-set comparison and conservative compiler tests. |
| Medium | Apartment alternatives promised different bedroom counts despite the fixed program, and room dimensions exposed long decimal labels. | Measured customer friction; no false claim that the generated bedroom count changed. | C3; visible alternative and review labels. |
| Medium | Old security assertions rejected workspace/render modules solely because they were already deferred instead of eagerly imported. | Fixed delivery guards require a unique declared loading path and loader. Existing escaping/malicious-input checks remain. | F4; sound eager/lazy cases and deliberate missing/duplicate ownership/loading. |
| Evidence gap | Actual Intel GPU capacity, phone experience, real Three.js draw calls/texture memory and headset traversal were not measured on the requested devices. | No performance claim, GPU optimization or ray/path-tracing default change. | F5 and external-verification table. |
| Deferred intentionally | Additional whole-module deferral, Redis installation and folder migration lack measured justification under their stated constraints. | Keep the loading graph, declared single-instance deployment and source layout. Supply a conditional feature proposal and reversible plan. | F6, B4 and A1; details below. |

## Measurement record and regression comparison

<!-- ACS:CURRENT-STATE:BEGIN — dated audit evidence, not rolling deployment claims -->

### Authenticated follow-up, 27 September in Riyadh

C3 uses the supported browser after the user's manual sign-in. The exact briefs,
manual confirmations and visible messages are preserved in CUSTOMER-REVIEW.md.
Reproduction commands are `acsTab.playwright.getByRole(...).fill(prompt)`,
the observed requirement-reading/generation buttons, and
`await acsTab.playwright.domSnapshot()` after each action. The recorded **5**
generation cases produced **2** saved fallback revisions and **3** explicit
rejections; this is not five completed models or a measured success-rate estimate.
The villa's single advertised resume did not produce a revision and is counted
with the original case. The case table records outcomes on the deployed system,
not on the proposed branch fixes.

| Live case | Confirmed input | Observed outcome |
|---|---|---|
| Requested Arabic villa | 20 × 25 m, 2 floors; original exact Arabic prompt | Layout failure, no revision; advertised resume gave the same visible outcome. |
| Warehouse | 40 × 60 m, 1 floor; storage/receiving/shipping/office/toilet | Explicit generated-area rejection, no revision. Scoped checkpoint analysis found an enclosing zone counted with its contained functional zones. |
| Impossible brief | 5 × 5 m site versus requested 20 × 20 m building and ten 20 m² bedrooms | Explicit layout rejection, no revision. No specific explanation of the contradictory constraint. |
| Single-storey apartments | 24 × 30 m, 2 flats, 2 bedrooms and 1 bathroom per flat | V1 saved using a disclosed calculated fallback. Planning-only approval enabled SVG, DXF, glTF and IFC downloads. |
| Multistorey apartments | 30 × 30 m, 3 floors, 2 flats per floor; bedrooms/bathroom as above | V1 saved using the same disclosed fallback. Core-space alignment did not establish physical stair/lift geometry. |

Empty input was rejected with `اكتب وصف المشروع أولًا.` Mixed Arabic/English
requirement reading returned the explicit `2 floors` and `4 bedrooms` candidates.
A client-only long-input test constructed
`['أرض','20×25','متر،','دورين،','4','غرف','نوم',...Array(4993).fill('مراجعة')].join(' ')`.
`text.split(/\s+/).length` measured **5000** words and `text.length` measured
**34982** characters. Reading returned width/depth/floor/bedroom candidates and
no alert. No provider generation or performance claim is made for this input.

E5 uses the successful apartment's downloaded artifacts and its authorized,
read-only saved revision. The download control emitted a success status and
files synchronized to disk even though this browser's download-event wait timed
out. `find /workspace/scratch -maxdepth 1 -type f -mmin -20 -printf '%f %s bytes\n'`
recorded **11639 B IFC**, **34200 B SVG**, **27798 B DXF**, and **480430 B glTF**.
The independent artifact parsers and manifest/hash checks are recorded in
ENGINEERING-AUDIT.md; no Revit session was run. The IFC has **18 IfcSpace** and
no wall, door, window or slab entities. The downloaded glTF has **35** door meshes
but **18** distinct sorted POSITION vertex sets: **17** coincident reciprocal pairs.
These are artifact measurements, not a frame-rate or visual-flicker measurement.

For the multistorey saved model,
`acs_arch.compile_architecture(model, 'bld_0', None, 0)` returned empty cores,
voids and issues. `acs_validate.validate_building(model)` returned no issues.
The pre-fix compiler produced **3** floor slabs without physical stair/lift
objects. The required distinction is core alignment versus physical traversal;
missing geometry must not be filled with invented design values.

The 3D control displayed an explicit unsupported-browser message. The supported
`await acsTab.dev.logs({levels:['error','warn'],limit:12})` read showed
`THREE.WebGLRenderer: Error creating WebGL context` with `GL_VENDOR = Disabled`
and `GL_RENDERER = Disabled`. This is a measured cloud-environment limitation,
not a demonstrated rendering failure on the owner's Intel GPU.

Read-only Render `list_deploys` for the named ACS service identified backend
deployment `dep-dalsqvbbc2fs738da120` at
`adec616aa5191315991fb9439cee83efbb719b8f`. The frontend deployment commit was
not identified. Scoped database reads were restricted to the newly created audit
projects; no existing customer projects or production configuration were changed.

The follow-up customer branch replay used the same baseline harness below and
recorded **242 invocations / 30 nonzero exits**, before changes to this
consolidation report. The fresh backend warehouse replay recorded **251 / 32**
with no new failures; the fresh frontend parser before/after replays both recorded
**250 / 31**, with unchanged exit statuses. The frontend's already documented
missing-Chromium refusal remains explicit. Later follow-up commits require their
own comparison and actual CI; the historical check table does not certify them.

F7: `node tests/remediation/test_audit_frontend_brief.mjs` reports **21 passing
assertions**, including **13 rejected mutations**; the existing
`node tests/remediation/test_brief_program.mjs` reports **13 passing tests**.
The exact villa gains a four-bedroom candidate while its unitless dimensions
remain a clarification question. `python3 tools/bundle_report.py` measures an
additional **3384 B** of source for the parser follow-up, with no speedup claim.
B5: `ACS_ENV=test python3 tests/remediation/test_audit_backend_warehouse_policy.py`
reports **6 passing tests** after **2 initial failures**; removal of the warehouse
policy is rejected. Deployment verification after adding its explicit Docker COPY
reports **736 passed / 0 failed**. These local proofs do not establish a new live
provider outcome.

B6: `ACS_ENV=test python3 tests/remediation/test_audit_backend_residential_roles.py`
reports **14 passing tests**, including **4 rejected mutations** and a
role-only/idempotence/geometry-preservation sweep of **165** existing models.
Those existing models contain none of the new Arabic aliases; translated sound
fixtures and the actual live checkpoint provide the positive language coverage.
The compact checkpoint command in BACKEND-AUDIT.md reproduces a recognized core
and **8** access findings that were previously bypassed. Adding the explicitly
confirmed **4**-bedroom requirement catches **8** generated bedroom instances.
The final backend replay records **252 invocations / 32 nonzero exits**, with
no changed exit statuses or new failures. A completed Arabic-role resume retains
its existing **3**-call budget usage with **0** new provider calls; a real layout
change still invokes repair and details. The unavailable final provider repair
response is not reconstructed or claimed as inspected.

E6–E7: `python3 tests/remediation/test_audit_engineering_door_meshes.py`
reports **12 passing tests**; the corresponding `--mutations` command rejects
**11 mutations**. `python3 tests/remediation/test_audit_engineering_vertical_coverage.py`
reports **15 passing tests**, with **10 mutations** rejected by its `--mutations`
command. The door suite's `--corpus 4980d58` comparison inspects **165 models**:
**162** compile, with the same **3** pre-existing compiler exceptions;
**90** exact reciprocal meshes are removed across **83** models. Non-door
geometry, retained door geometry/materials, input values and review scopes/issues
remain unchanged. This is distinct from the exception-free validator sweep.
Its `--evidence` command, documented in ENGINEERING-AUDIT.md, recompiles the
captured apartment to **21** door meshes by removing **14** exact duplicates.
The remaining **3** identical-vertex pairs have different double-precision source
centres and are deliberately retained. The multilevel capture records **6**
missing core-geometry entries; traversal remains `NOT_VERIFIED`. These are local
recompilations, not replacement live downloads.
The engineering follow-up replay records **249 invocations / 32 nonzero exits**,
with no exit-status differences from its baseline; the new door/coverage suites
are separately measured by the commands above.

F8: `node tests/remediation/test_audit_frontend_vertical.cjs` reports **24 passing
assertions**, including **12 rejected mutations**. Its optional `--review` path
consumes the locally generated review of the captured multilevel model and passes
**26 assertions** across the connected and standalone review surfaces. These
tests exercise the actual render functions with a minimal DOM; they do not prove
visual layout, WebGL or screen-reader behavior. Before/after replays both contain
**251 invocations / 31 nonzero exits**, with unchanged exit statuses. The extra
invocation relative to the parser replay is the already-added brief audit suite;
the new vertical suite is measured separately.

The detached combined checkout applies backend, engineering and frontend source
changes to observed main. Running the four source gates, deploy verification,
bundle report, all new backend/engineering suites, topology/corpus/regulatory
contracts, plan-review/bridge/recovery contracts and frontend brief/module/guard
suites records **25 successful commands**. The additional accessibility and
documentation-claim commands retain their known missing-Chromium exits; their
logs explicitly identify that unavailable environment. The same captured model
passed the combined `PlanWorkspace.review` → frontend `--review` handshake.
Command-by-command evidence is retained outside git; independent PR CI remains
the browser verification source. This is compatibility evidence, not deployment.

The combined commands were run with `ACS_ENV=test` and the audit virtual
environment on `PATH`, in the detached combined checkout:

```bash
python3 tools/check_integration.py
python3 tools/check_index_guard.py public/index.html
python3 tools/check_api_base.py
python3 tools/check_csp_hash.py
python3 tests/deploy/verify_deploy.py
python3 tools/bundle_report.py
python3 tests/remediation/test_audit_backend_corpus.py
python3 tests/remediation/test_audit_backend_provider.py
python3 tests/remediation/test_audit_backend_residential_roles.py
python3 tests/remediation/test_audit_backend_warehouse_policy.py
python3 tests/remediation/test_audit_engineering_openings.py
python3 tests/remediation/test_audit_engineering_door_meshes.py
python3 tests/remediation/test_audit_engineering_vertical_coverage.py
python3 tests/remediation/test_validate_topology.py
python3 tests/remediation/test_validate_against_real_models.py
python3 tests/remediation/test_rule_source_boundary.py
python3 tests/remediation/test_plan_review.py
python3 tests/remediation/test_plan_bridge.py
python3 tests/remediation/test_plan_bridge_integration.py
python3 tests/remediation/test_workspace_recovery.py
node tests/remediation/test_audit_frontend_brief.mjs
node tests/remediation/test_audit_frontend_vertical.cjs
node tests/remediation/test_brief_program.mjs
node tests/remediation/test_module_graph.js
node tests/remediation/test_accessibility.js
node tests/remediation/test_audit_frontend_guards.js
python3 tools/check_doc_claims.py
```

### Final follow-up source heads and check status

Read-only GitHub workflow results were checked at **2026-09-26 22:31 UTC**
against each exact published head. Every workflow on these heads completed with
conclusion `success`, including each long Real Chromium job and the required CI
aggregate. Here, success means repository checks only: it does not merge or
deploy a branch and does not convert any external-environment item into a
verified outcome.

| PR / exact published head | Completed workflow evidence |
|---|---|
| Architecture [#182](https://github.com/NAIFMUSFER/AI-Instruction/pull/182) · `78374061fda33851cc6a7317bcd8c0053818047e` | CI #884; Async #741; semantic locks #227; 2D review #605 |
| Backend [#183](https://github.com/NAIFMUSFER/AI-Instruction/pull/183) · `987e9a7c779af30cd64938f20ce1b0e45715f390` | CI #892; backend audit contracts #3; Async #749; semantic locks #235; 2D review #613 |
| Engineering [#184](https://github.com/NAIFMUSFER/AI-Instruction/pull/184) · `7fd39d8721872d6589c7b9a69aaf64f26878068d` | CI #894; engineering opening geometry #3; Async #751; semantic locks #237; 2D review #615 |
| Frontend [#185](https://github.com/NAIFMUSFER/AI-Instruction/pull/185) · `d95c5713cd20c09de82f14ecf9045f50c700c91a` | CI #893; frontend audit contracts #3; Google sign-in #14; Async #750; semantic locks #236; 2D review #614 |
| Consolidation [#186](https://github.com/NAIFMUSFER/AI-Instruction/pull/186) · `cdb80125d54f09206ddb0edc4751426f037fb1ed` | CI #895; Async #752; semantic locks #238; 2D review #616 |

No completed check on these exact heads failed. The three source fixes remain
independent and unmerged. The architecture proposal is unchanged. The
consolidation head contains reports and evidence only. The documentation-only
commit that records this table is later than `cdb80125...`; its own checks are
visible on PR #186 and must be evaluated independently.

### Original baseline and first remediation pass

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
are not manufactured. The earlier fixture-based legacy IFC serialization contains
real space, wall, door and window entities and metre units; unsupported lift
objects/property losses are disclosed. The actual connected-workspace download
has a different, explicitly spaces-only scope. Neither evidence establishes
independent Revit acceptance; the legacy census must not be attributed to the live download.

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
| Successful live villa and warehouse after the proposed repairs; complete long/mixed-input generation | Authenticated attempts are now recorded, including explicit failures. Long/mixed-input tests covered requirement reading only; no post-deployment success is inferred. |
| Cold/warm throttled 3G first paint, time to type, requests and transfer bytes; physical phone repeat | Supported browser throttling/cache/network measurement controls and a phone; no tool-call duration substituted |
| Full live panel walkthrough and files opened in the customer's software | Actual downloads were obtained and structurally parsed. The cloud browser cannot create a WebGL context; Revit and native customer viewers remain unavailable. |
| Independently accepted generated buildings and Revit scale/storey/entity acceptance | Live fallback revisions supplement the earlier fixtures. Failed generation cases do not count as completed models; no Revit session is available. |
| Owner's Intel GPU frame budget, real texture memory and draw calls; WebXR | Actual machine, real renderer measurement and headset |
| Complete screen-reader/RTL accessibility acceptance | Real assistive technology and independent complete interaction review; local DOM/CSP/keyboard checks cover only their declared scope |
| Actual provider outage, billed usage, retention and cancellation of upstream computation | Controlled provider environment, operator contract and billing records |
| Live Supabase policy enforcement and native hostile DWG | Read-only, audit-project-scoped checkpoints and production logs were inspected; this does not exercise RLS isolation or a native hostile-CAD parser. |
| Full structural design, physical stairs and resolved pedestrian/egress routes | Missing model contracts plus responsible engineering review; no code thresholds inferred |

C1/C2 reproduction uses the supported live browser: `customerTab.goto(...)`,
`customerTab.reload()` and `customerTab.playwright.domSnapshot()` on
`https://sprightly-selkie-d906c3.netlify.app/`, followed by the visible
`الخصوصية وحفظ البيانات` link and the new tab's DOM snapshot. Exact commands and
the expectation/happened/cost records are in CUSTOMER-REVIEW.md. The frontend's
commit was not identified from that UI. The follow-up backend deployment commit
was independently identified through the read-only Render deployment listing.

## Original branch-check record

GitHub Actions was read at **2026-09-26 20:10 UTC** on the exact pull-request
heads below. Every listed workflow completed with conclusion `success`. Here,
`success` means the repository checks completed successfully; it does not turn
the external-environment items above into verified outcomes, merge a branch, or
identify a production deployment.

| PR / exact head | Completed workflows on that head |
|---|---|
| [#182](https://github.com/NAIFMUSFER/AI-Instruction/pull/182) · `78374061fda33851cc6a7317bcd8c0053818047e` | CI #884; Async generation delivery #741; semantic locks #227; 2D review #605 |
| [#183](https://github.com/NAIFMUSFER/AI-Instruction/pull/183) · `eba8b94ec74018f6843420abee81910361caef05` | backend audit contracts #1; CI #883; Async generation delivery #740; semantic locks #226; 2D review #604 |
| [#184](https://github.com/NAIFMUSFER/AI-Instruction/pull/184) · `4980d58b6c2b4431617b64c12018083208d4ef45` | engineering opening geometry #2; CI #887; Async generation delivery #744; semantic locks #230; 2D review #608 |
| [#185](https://github.com/NAIFMUSFER/AI-Instruction/pull/185) · `7dfff96bbcdc5a163fc4148826705ddeaad6ee19` | frontend audit contracts #1; CI #886; Google sign-in #12; Async generation delivery #743; semantic locks #229; 2D review #607 |
| [#186](https://github.com/NAIFMUSFER/AI-Instruction/pull/186) · `404a37c2e509d450c94329bdb05c708ec9016555` | CI #888; Async generation delivery #745; semantic locks #231; 2D review #609 |

The three long CI runs that were still active at the earlier checkpoint completed
their Real Chromium jobs and required aggregate jobs successfully. No obsolete
failed run is used for the engineering result; the row above is the corrected
head `4980d58b...`.

This table is a dated record of the immediately preceding report/source heads.
The documentation-only commit that adds the table is later than `404a37c2...`;
its own head checks remain visible on PR #186 and must not be inferred from this
historical row. No application source changes in this documentation commit.

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
