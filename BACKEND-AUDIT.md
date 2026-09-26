# ACS — Backend and platform audit

Scope: the measured work base and unchanged-baseline procedure are in `BASELINE.md`. This branch changes provider transport selection, repair telemetry and the connected warehouse planner's instructions. Geometry and authority checks remain strict. Provider failure exercises use synthetic SDK responses. The later live generation diagnosis below uses only the parent's explicitly authorised synthetic projects and bounded read-only deployment, log and checkpoint queries.

## Findings ordered by user impact

**B-WAREHOUSE — fixed instruction conflict; live success remains unverified.** The connected warehouse planner inherited a legacy instruction to wrap its functional zones in an overlapping envelope room. Its canonical workspace rejects overlapping rooms and counted that envelope again when checking whether the proposed areas could fit. A saved live checkpoint reproduced the rejection even though the functional zones fit. The connected worker now supplies a dedicated planning policy during outline and plan-chunk calls. It asks for disjoint functional zones without an enclosing room. This does not delete existing geometry, relax overlap or area checks, or rescue old checkpoints. The regression captures the actual SDK system messages; a mutation removing the policy restores the contradictory instruction. Prompt correction alone cannot guarantee that a provider follows the instruction. A new deployed end-to-end generation is still required before calling the customer outcome fixed.

**B-VILLA — open, measured incomplete generation.** The saved villa checkpoint uses Arabic room roles that the residential contract treats differently from its English roles. The aligned Arabic stair is reported missing, while Arabic bedroom roles bypass the apartment-access scope. The brief's bedroom count is absent from the confirmed requirements, so a shared floor template duplicates the bedrooms without a count finding. The failed repair response is not stored in that checkpoint: the exact reason its candidate remained invalid is unknown. Changing only the stair check would leave the access/count problem unresolved. No broad role conversion or geometry exception was added here.

**B-PROVIDER — fixed: a failure inside an already-started stream could silently submit another provider request.** The transport fallback caught `AttributeError` across stream creation, entry, decoding and exit. Injecting that exception after submission led to `stream → create → success`, masking the first failure and potentially charging for another response. Method lookup is now the only fallback boundary. A failure after lookup remains a classified error and is not resubmitted through `create`. The missing-stream compatibility path also previously consumed budget before discovering that no stream method existed; a valid call could therefore be rejected without sending anything. The budget is now consumed immediately before the selected transport is called.

Proof: `ACS_ENV=test python3 tests/remediation/test_audit_backend_provider.py`. The regression was run red against unchanged production source before the patch; the suite now exercises broken and sound paths. In-memory mutations restore the broad catch and phantom budget charge and reproduce their failures. No production file is modified by the mutation tests.

**B-USAGE — fixed: repair usage disappeared from generation's stage summary.** The legacy understanding path logged individual repair calls but did not carry their telemetry into the returned generation stages. This made the API summary undercount successful repairs and paid replies that failed JSON parsing. Repair telemetry is now passed through and recorded even when the previous draft is kept. The product still returns a draft with disclosed unresolved issues when repair cannot clear them; no compliance or engineering approval is manufactured.

Proof: the `RepairAccounting` cases in the same command exercise repeated unsuccessful repairs, malformed repair output, a sound model needing no repair, and an in-memory mutation that disconnects repair telemetry.

**B-COST — limitation, not a solved billing guarantee.** The legacy generation path has stage token limits, timeout/cancellation, request rate limits and bounded chunk splitting. It has no monetary ceiling per user request. The dedicated plan worker additionally enforces a provider-call budget and disables SDK retries while that budget is active. The returned stage trace is bounded and is not a billing ledger: retries and traces beyond its retained stage window cannot be treated as a full invoice. Repair accounting fixes the measured omission but does not establish a universal spending cap. A dollar estimate without the operator's provider prices and actual usage would be invented. No scaling change or Redis dependency was introduced.

Inspection commands: `rg -n 'limited|consume|max_retries|stages\[:|estimated_cost_usd|ACS_PRICE' acs_provider_budget.py acs_understand.py acs_understand_api.py`; `rg -n 'TIMEOUT|MAX_.*SPLIT|MAX_PLAN_CHUNKS' acs_generation.py acs_plan_chunks.py acs_generation_job.py`. Provider failure, accounting and cancellation evidence is listed below.

## Measured snapshot

<!-- ACS:CURRENT-STATE:BEGIN — backend audit snapshot; reproduced by the commands in this block -->

The source snapshot was measured on this audit branch on 2026-09-26. These figures describe these executions, not a promise about future deployments.

### Model entry points and the repair contract

Command: `ACS_ENV=test python3 tests/remediation/test_audit_backend_corpus.py --report`. It recursively discovers actual building objects in `tests/**/*.json`, including nested models, using the existing corpus depth convention. Both independent executions receive fresh deep copies. Visual-scene time is fixed explicitly so a timestamp is not mistaken for geometry nondeterminism.

| Entry point | Models | Exceptions | Different repeated outputs or final input | Caller inputs changed |
|---|---:|---:|---:|---:|
| `acs_bim.opening_identity_issues` | 165 | 0 | 0 | 0 |
| `acs_layout.autofix` default PROPOSE | 165 | 0 | 0 | 108 |
| `acs_layout.autofix` explicit APPLY | 165 | 0 | 0 | 162 |
| `acs_visual.compile_visual_scene` | 165 | 0 | 0 | 0 |
| `acs_validate.validate_building` | 165 | 0 | 0 | 0 |

The same command reports `validate → autofix(APPLY) → validate`: **0 issue-count increases, 0 exceptions and 0 nondeterministic results**. APPLY intentionally writes its caller's model. PROPOSE permits the documented SAFE_NORMALIZATION changes; the independent allowlist remains enforced by `ACS_ENV=test python3 tests/remediation/test_autofix_propose_boundary.py`. Calling PROPOSE immutable would be false.

Commands `ACS_ENV=test python3 tests/remediation/test_audit_backend_provider.py` and `ACS_ENV=test python3 tests/remediation/test_audit_backend_corpus.py` pass **10 and 5 tests**, respectively. The repeated-repair test makes **6 synthetic calls** (initial generation plus **5** repairs), records **6** stages, and accounts for the injected **600 input / 120 output tokens**. Its red execution recorded only the initial stage. These are injected usage quantities, not actual provider consumption.

### Security and provider suites

Each row is produced by `ACS_ENV=test python3 <path>`. The security suite assertions were inspected before relying on their results; the source/configuration checks are not represented as live penetration tests.

| Path | Measured result |
|---|---|
| `tests/security/test_security.py` | 377 passed, 0 failed |
| `tests/remediation/test_upload_security.py` | 200 passed, 0 failed |
| `tests/remediation/test_rate_limit.py` | 120 passed, 0 failed |
| `tests/remediation/test_privacy_boundary.py` | 74 passed, 0 failed |
| `tests/remediation/test_provider_integration.py` | 56 passed, 0 failed |
| `tests/remediation/test_provider_accounting.py` | 51 passed, 0 failed |
| `tests/remediation/test_multi_provider.py` | 111 passed, 0 failed |
| `tests/remediation/test_provider_reject.py` | 57 passed, 0 failed |
| `tests/remediation/test_rule_source_boundary.py` | 9 tests passed |
| `tests/remediation/test_event_loop.py` | 63 passed, 0 failed; real local Redis server, not production Redis |

Local runtime limits and SDK defaults are measured with:

```sh
python3 - <<'PY'
import inspect, json, anthropic
import acs_generation as G, acs_rate_limit as RL, acs_upload_security as U
print(json.dumps({
    'sdk_default_max_retries': inspect.signature(anthropic.Anthropic).parameters['max_retries'].default,
    'stage_budgets': {s: G.stage_budget(s) for s in G.STAGE_SHARE},
    'rate_limit_defaults': RL.DEFAULT_LIMITS,
    'upload_limits': U.health_status()['limits']}, indent=2))
PY
```

Measured defaults: SDK retries **2**; stage output limits **32,000 single / 16,000 plan / 24,000 detail / 32,000 repair tokens**; request limits **8 generations/hour, 25/day, 30 edits/hour, 400 generation requests/day globally**. These are configuration limits, not a per-request dollar ceiling. `render.yaml` declares **600 seconds upstream** and **840 seconds request timeout** (`rg -n -A1 'ACS_.*TIMEOUT' render.yaml`). An already-accepted upstream request cannot be recalled when the local worker is terminated.

Selected upload budgets from the same command: image wire bytes **5,242,880**, decoded raster bytes **33,554,432**, PDF wire bytes **12,582,912**, PDF decoded streams **25,165,824**, PDF pages **200**, JSON bytes **900,000**, DXF bytes **16,777,216**. Parser admission is bounded; this does not assert immunity to every malicious file.

### Observed production resources

Read-only Render command used by the coordinating audit: `get_metrics(resourceId="srv-d9qtsv3m8hqs73967680", workspaceId="tea-d9qth1iju40c73btab90", metricTypes=["cpu_usage","memory_usage","memory_limit","instance_count","http_request_count"], resolution=300)`.

The returned window was **2026-09-26 18:04–19:04 UTC**. It showed **1 instance**, memory usage **112,824,320 bytes** against **536,870,900 bytes**, CPU **0.0017482133–0.0019023867 CPU units**, and request samples containing **one 200 response followed by zero-request samples**. CPU is reported in the provider's CPU units, not confused with percentage of the starter plan's allocation. This is an idle observation window, not a load-capacity benchmark.

### Baseline comparison

Commands: `npm install`; `TMPDIR=/workspace/scratch/cc68e7a7ea83/audit-evidence/tmp-backend python3 docs/audit/2026-09-26/run_baseline.py "$PWD" /workspace/scratch/cc68e7a7ea83/audit-evidence/backend`; then the baseline's corrected Phase-1 invocations, each with `bash tools/ci_run.sh --label phase1-correct-runner --runner 'node tests/lib/run.js' tests/phase1/<test>.js`.

The final replay, including the warehouse-policy correction, recorded **251 invocations, 32 nonzero exits, and 0 new failing names or changed exit statuses** relative to the **248-invocation / 32-nonzero** baseline. The additional invocations are the **3 new passing audit suites**. The corrected Phase-1 runner reproduced its existing **4 passes / 2 DOM-dependent failures**. These counts include the baseline's initial incorrect runner invocations and environment-dependent checks; they are not counts of product defects. Final evidence is `backend-warehouse-final/final-results.json` and `comparison.json` in the audit evidence directory, produced by the same harness with that output directory plus the corrected runner commands.

Integration, index guard, API origin and CSP hash gates passed. Final deploy verification reported **736 passed, 0 failed**. Adding the runtime module first exposed **2 failing deployment assertions** because its explicit Docker copy was missing; the copy list was corrected and the same gate rerun. The recovery suite's warehouse policy assertion was updated from absent policy to the dedicated warehouse policy, retaining its assertion that residential detailing is never called; all **20 tests pass**. The exact bare `ACS_ENV=test bash tools/ci_run.sh` still returns its baseline **64 usage exit**, because this revision requires a runner and targets. The documentation-claim gate still reports unavailable Chromium coverage. Missing browser/vendor checks and PID namespace behavior were retained as baseline limits, not patched away. Generated test outputs and `package-lock.json` were restored before commit.

### Authorised live checkpoint diagnosis

Deployment command: `render.list_deploys(serviceId="srv-d9qtsv3m8hqs73967680", workspaceId="tea-d9qth1iju40c73btab90", limit=3)`. The live deployment was `dep-dalsqvbbc2fs738da120`, commit `adec616aa5191315991fb9439cee83efbb719b8f`, finished at **2026-09-17T11:23:02.435391Z**. These observations precede deployment of this audit branch.

Checkpoint command, run separately for each authorised synthetic project through `supabase.execute_sql(project_id="hbahakzhrnpmgwkoyyhm", query=...)`:

```sql
select id, state, error_code, created_at, finished_at, phase,
       provider_calls, checkpoint, resume_command
from public.acs_workspace_jobs
where project_id = 'faa52763-ee3a-4624-acd5-d59a6d3cabcb'
order by created_at asc limit 3;
-- Same selected fields, only this other authorised project, limit 2:
-- c468139c-eff5-48f7-ada9-7640f37f9cd8
```

The villa's initial job `91ec47f4-959c-4bfe-88de-0f3b945b2616` failed with `PLAN_LAYOUT_INCOMPLETE` after **3 provider calls**, at **21:00:09.458605 UTC**. Its resume failed with the same code at **21:01:55.638946 UTC**, with the cumulative count **4**. Both checkpoints contain the same pre-repair layout. The exact brief was `فيلا دورين على أرض ٢٠×٢٥، مجلس ومقلط ومطبخ وأربع غرف نوم ودرج داخلي`; the submitted form additionally confirmed the site width/depth. Calling `_geometry`, `_program`, `acs_residential_access.issues(..., doors=False)` and `check_rooms` on `checkpoint.building` gives, respectively, **0 geometry findings, 0 program findings, 0 access findings, and `RESIDENTIAL_CORE_MISSING`**. The common template has **4 Arabic-role bedrooms and 1 Arabic-role stair**, repeated on **2 levels**, yielding **8 bedroom instances**. Only site width, depth and level count were confirmed as requirements. This measures the saved input to repair, not the unpersisted failed repair response.

Log command: `render.list_logs(resource=["srv-d9qtsv3m8hqs73967680"], workspaceId="tea-d9qth1iju40c73btab90", startTime="2026-09-26T20:59:50Z", endTime="2026-09-26T21:01:00Z", type=["app"], direction="forward", limit=100)`. The initial villa's outline, plan chunk and repair each ended normally with `end_turn`; logged durations were **2288, 3091 and 2554 ms**, with no retry or fallback. The wire host was **api.deepseek.com**, while the API-format provider label was `anthropic` and model alias `claude-sonnet-5`. This was not evidence of an outage, token truncation or exhausted call budget. No credentials or unrelated project data were read.

The warehouse job `05ccf138-10bd-4827-acff-52fc1f39774e` ran **21:03:59.105550–21:04:03.660787 UTC**, consumed **2 provider calls**, and failed with `PLAN_GEOMETRY_AREA_EXCEEDS_SITE`. Reconstructing its outline checkpoint with `acs_plan_chunks.merge_plan(checkpoint['zones'], checkpoint['results'], checkpoint['envelope'])` yields a **40 × 60 m** envelope (**2400 m²**) plus **6** functional zones of **520, 1120, 520, 48, 24 and 24 m²**. `_geometry` reports exactly **6 envelope-to-zone overlaps**. The repair sums **4656 m²** against **2400 m²**. A diagnostic copy containing only the functional zones has **2256 m²** and **0 geometry findings**; production data was not edited. These dimensions and both rejection/sound cases are reproduced in `ACS_ENV=test python3 tests/remediation/test_audit_backend_warehouse_policy.py`.

That new regression ran **6 tests**, initially with **2 failing tests** against unchanged source; all **6 pass** after the policy correction. It checks the actual SDK messages for both planning stages, unchanged strict rejection of the reconstructed overlapping model, sound interior zones, genuine excess area without an envelope, policy scope restoration, and an in-memory mutation removing the policy wiring. No live provider call is made by this suite.

<!-- ACS:CURRENT-STATE:END -->

## Failure paths and what reaches the user

| Injected condition | Server result and visible contract | Evidence / limit |
|---|---|---|
| Slow provider | `ACS_UPSTREAM_TIMEOUT`; Arabic message says the model response timed out. Whole-job timeout uses `ACS_TIMEOUT`; the process executor terminates the local worker and releases its slot. | `test_provider_integration.py`, `test_generation_cancel.py`; production-provider cancellation is not claimed. |
| Provider rate limit | `ACS_UPSTREAM_RATE_LIMIT`; retryable Arabic instruction to try again later. Local quota exhaustion is separately `ACS_RATE_LIMITED`. | `test_provider_integration.py`, `test_rate_limit.py`; live exhaustion deliberately not induced. |
| Malformed JSON | `ACS_UPSTREAM_INVALID_JSON`; classified failure for initial generation. A malformed repair preserves the earlier draft and records failed repair telemetry. | New `RepairAccounting` test and existing backend contract/parser suites. |
| Persistent geometry issues | Repair stops at its configured limit and exposes the remaining issues in the draft. Geometry quality and compliance remain separate. | New repeated-repair test plus `test_model_diagnostics.py`; no regulatory thresholds added. |
| A staged detail group fails | The staged path can retain that group's planned rooms without the missing detail. Failed stage telemetry accompanies the retained plan; this is a partial-detail draft, not a recovered complete provider response. | `test_plan_chunking.py` and inspection of `understand_deep.work` / `_detail_group_split`; visibility of the warning in the live browser remains external verification. |
| Provider unavailable | `ACS_UPSTREAM_CONNECTION`; the API error contract gives an Arabic connection failure. A configured secondary provider is governed by the existing explicit fallback policy. | `test_multi_provider.py`, `test_provider_integration.py`; no claim that an actual provider outage was induced. |
| Broken stream decoder | A classified failure; no silent transport resubmission. | New `ProviderTransport` tests and historical mutation controls. |

The offline API/error contract is measured. The scoped live timing above is measured; actual billable token totals and a real browser completing every injected failure remain **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. The customer and frontend streams own the end-user browser observations.

## Security boundaries

- Upload validators derive image type from bytes, reject type mismatches and excessive decoded size, decode/re-encode accepted images, bound PDF streams/pages/text, and reject hostile JSON structure. Filesystem checks exercise traversal-like names without treating supplied filenames as paths. Evidence: `test_upload_security.py`, `acs_upload_security.py`; the suite includes accepted files and adversarial controls.
- CPU-heavy admission runs through the bounded worker pool; provider generation uses a separate cancellable job runner. Evidence: `test_event_loop.py` and the cancellation suite's bounded-time/slot-release checks. An idle memory graph does not prove peak concurrent upload capacity.
- The memory limiter has locking inside the process, bounded key storage and eviction handling. Production startup demands the declared single-instance topology unless a distributed limiter is selected. This is an explicit deployment invariant, **not a distributed lease capable of discovering every independently started replica**. Evidence: `test_rate_limit.py`, `test_event_loop.py`, `acs_rate_limit.production_invariant`, and `render.yaml`.
- Static CORS/CSP, configuration secret checks, logging privacy and the regulatory refusal were exercised. The private plan-source path uses fixed bucket paths and validated project/source identities with the user's access token; stored originals and previews are disclosed in `public/privacy.html`. Evidence: `test_security.py`, `test_privacy_boundary.py`, `test_plan_source_upload.py`, and source inspection of `acs_plan_sources.py`. The bounded live logs above were inspected; a general production-log privacy audit, live Supabase policy enforcement and provider retention terms remain **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
- `validate_dxf_bytes` is explicitly a lightweight structural/size guard, not a complete CAD parser. The connected plan-source upload admits PDF/PNG/JPEG/WebP; native DWG ingestion is not claimed. Evidence: `rg -n 'def validate_dxf_bytes|no SECTION|ENDSEC' acs_upload_security.py`; `rg -n 'media ==|media in|الصيغ المدعومة' acs_plan_sources.py`; `test_plan_source_upload.py`. Native AutoCAD/DWG and hostile DWG execution: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

## Why Redis was not added

Adding `redis` today is not justified by the measured production traffic or instance count. The tested memory deployment is adequate for the declared topology; the package alone would not provision a store or make counters shared. The existing Redis backend should be activated, with a pinned dependency and operational store, when distributed instances are actually required or when quota persistence across restarts is an explicit need. Memory quotas reset on restart; this limitation is measured by the existing rate-limit suite and is not hidden.

Dependency check: `python3 -c "from pathlib import Path; print('redis==' in Path('requirements.lock').read_text())"` returns `False`. Redis construction fails closed if explicitly selected without its dependency/configuration. No Redis install, replica increase, or production deployment was performed.

## Environmental verification limit

`tests/remediation/test_generation_cancel.py` contains `/proc/<pid>` and psutil assertions that are unreliable in this execution environment. Direct measurement showed `os.getpid()` and the host-mounted `/proc/self` refer to different PID namespaces; `/proc/<os.getpid()>/comm` can identify an unrelated process. The suite's process termination, timeout and slot-release checks execute, but the host-PID sweep cannot certify child cleanup here. This is a pre-existing baseline condition; the product and assertions were not weakened.

Reproduce the namespace observation:

```sh
python3 - <<'PY'
import os
from pathlib import Path
print('namespace PID:', os.getpid(), 'proc self:', os.readlink('/proc/self'))
print('\n'.join(line for line in Path('/proc/self/status').read_text().splitlines()
                if line.startswith(('Pid:', 'PPid:', 'NSpid:'))))
path = Path('/proc/%s/comm' % os.getpid())
print('same-number proc process:', path.read_text().strip() if path.exists() else 'absent')
PY
```

Clean child-process enumeration on a conventional Linux runner: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. The new SHA-pinned backend workflow runs the provider/corpus regressions and existing provider/authority suites without live credentials; existing CI continues to own its broader cancellation gate.
