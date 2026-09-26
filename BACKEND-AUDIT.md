# ACS — Backend and platform audit

Scope: the measured work base and unchanged-baseline procedure are in `BASELINE.md`. This branch changes provider transport selection and repair telemetry only. It does not change geometry, engineering authority, regulatory thresholds, live configuration, provider selection, or dependencies. All provider failure exercises use synthetic SDK responses; they do not spend provider credit.

## Findings ordered by user impact

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

The replay recorded **250 invocations, 32 nonzero exits, and 0 new failing names or changed exit statuses** relative to the **248-invocation / 32-nonzero** baseline. The additional invocations are the **2 new passing audit suites**. The corrected Phase-1 runner reproduced its existing **4 passes / 2 DOM-dependent failures**. These counts include the baseline's initial incorrect runner invocations and environment-dependent checks; they are not counts of product defects.

Integration, index guard, API origin and CSP hash gates passed. Deploy verification reported **733 passed, 0 failed**. The exact bare `ACS_ENV=test bash tools/ci_run.sh` still returns its baseline **64 usage exit**, because this revision requires a runner and targets. The documentation-claim gate still reports unavailable Chromium coverage. Missing browser/vendor checks and PID namespace behavior were retained as baseline limits, not patched away. Generated test outputs and `package-lock.json` were restored before commit.

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

The offline API/error contract is measured. Live provider timing, actual billable token totals, and a real browser completing each injected failure: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. The customer and frontend streams own the end-user browser observations.

## Security boundaries

- Upload validators derive image type from bytes, reject type mismatches and excessive decoded size, decode/re-encode accepted images, bound PDF streams/pages/text, and reject hostile JSON structure. Filesystem checks exercise traversal-like names without treating supplied filenames as paths. Evidence: `test_upload_security.py`, `acs_upload_security.py`; the suite includes accepted files and adversarial controls.
- CPU-heavy admission runs through the bounded worker pool; provider generation uses a separate cancellable job runner. Evidence: `test_event_loop.py` and the cancellation suite's bounded-time/slot-release checks. An idle memory graph does not prove peak concurrent upload capacity.
- The memory limiter has locking inside the process, bounded key storage and eviction handling. Production startup demands the declared single-instance topology unless a distributed limiter is selected. This is an explicit deployment invariant, **not a distributed lease capable of discovering every independently started replica**. Evidence: `test_rate_limit.py`, `test_event_loop.py`, `acs_rate_limit.production_invariant`, and `render.yaml`.
- Static CORS/CSP, configuration secret checks, logging privacy and the regulatory refusal were exercised. The private plan-source path uses fixed bucket paths and validated project/source identities with the user's access token; stored originals and previews are disclosed in `public/privacy.html`. Evidence: `test_security.py`, `test_privacy_boundary.py`, `test_plan_source_upload.py`, and source inspection of `acs_plan_sources.py`. Live Supabase policies, provider retention terms and production log contents: **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
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
