# AI Construction Studio — production trust audit, 2026-09-05

## Executive summary

Release gate: **OPEN / NOT READY FOR PRODUCTION RELEASE**. This phase preserves the existing application and the pending browser-acquisition fixes. It repairs verifiability and dependency security; it does not claim completion of the master product specification.

Repository: https://github.com/NAIFMUSFER/AI-Instruction

Initial main: `962f8daec2f194957d1a4322ce1ed22fd39086ea`, clean checkout. Work was based on existing PR #3, `fix/browser-acquisition`, at `a2973ebdecd9b4ea4f317781a8de9129bf4a854b`, to preserve its 51-file change set. Working branch: `codex/acs-production-audit-20260905`. No main merge or production deployment was performed.

## A. Current state audit

| Area | Evidence and current state |
|---|---|
| Model | Existing Python canonical geometry, project adapter, stable-ID helpers, authoring/revisions and generated JavaScript mirrors. Preserve these contracts. |
| Visualization/documentation | Three.js, modes, BIM/documentation/PBR layers and deterministic parity suites exist. Presence and passing contracts do not establish real-browser functionality. |
| Backend | FastAPI endpoints `/health`, `/ready`, `/version`, `/v1/understand`, `/v1/edit`, `/v1/understand/image`, `/v1/understand/pdf`. |
| Persistence/auth | Browser IndexedDB projects and localStorage name-based login; no server project database, authenticated project API or durable job queue identified. |
| Hosting | Netlify serves `public/`; Render serves Docker/Python. No hosting migration attempted. |
| Live HTTP | On 2026-09-05 at about 19:27 UTC, health/ready/version returned 200. Both front and back declared main SHA `962f8dae…`. |
| Provenance issue | Backend declared `built_at=2026-08-15T04:59:00+03:00`, preceding the commit date. The source of the stale deployed value is NOT VERIFIED without deployment configuration access. |
| CSP | Live header has `style-src 'self'`, restricted script sources and import-map hash, no unsafe-inline/eval. Runtime behavior: BROWSER NOT VERIFIED. |
| CORS | Trusted Netlify preflight returned 200 with exact allow-origin. Untrusted origin returned 400 without allow-origin. Preview/staging origins remain undefined. |
| Rate limits | Deployment reports process-local state and single-instance topology. This is not restart-durable enforcement. |
| Performance | Static guard measured shell 47,424 bytes, 27 modules totalling about 1.906 MB, largest standards module 228,695 bytes. Startup/FPS/memory and large-model performance NOT VERIFIED in Chromium. |

A later run of the repository's direct-DNS live verifier exited 2 (`gaierror`). This environment limitation does not invalidate the separately captured HTTP responses, and does not establish a production DNS outage. No paid generation call was made.

## B. Gap analysis

1. **Release blockers:** real Chromium acquisition/runtime CSP/core workflow, complete cancellation verification, exact-commit green CI, deployed timestamp investigation, dependency changes reviewed in browser.
2. **Product security/integrity:** authenticated authorization, transactional server persistence, durable revisions/jobs/idempotency/budgets, secure object storage and tenant isolation.
3. **Unknown data:** project adapter can derive level elevations with fallback height values when information is absent. This needs a controlled schema/provenance change and tests; it was not silently rewritten in this security phase.
4. **Product coverage:** complete bilingual interface, accessible mobile review, measured startup/large-model performance, full upload-to-confirmation-to-export workflow evidence.
5. **Regulation:** authoritative, licensed/versioned jurisdiction rule packs and validated evaluators are absent: **NOT EVALUATED**. Existing visuals are not engineering approval.
6. **Operational coverage:** real Windows execution, comprehensive secret-scanning CI gate, staging/preview environment policy and validated rollback.

## C. Target architecture

Keep the canonical model and deterministic Python/JavaScript transformations. Introduce a schema-versioned application service with authenticated project authorization, PostgreSQL transactions for project versions/revisions/jobs, private object storage for quarantined uploads, and bounded workers for parsing/provider calls. Use optimistic concurrency and idempotency keys; persist budget decisions where required. Every transformation validates IDs, references, finite geometry and provenance. Geometry-changing proposals require explicit revisions. Presentation settings remain separate. Regulatory evaluators consume explicit versioned rule sources and return evidence, never invented approval.

## D. Prioritized remediation plan

P0: finish trusted CI/browser evidence, review security updates, investigate deployed metadata. P1: identity, authorization, persistence and concurrency. P2: unknown-data/provenance confirmation and controlled authoring across supported building types. P3: complete bilingual/accessibility/review UX and performance. P4: staging release rehearsal and explicit production authorization.

## E. Implementation phases and changes in this phase

- Preserve the existing PR and schema. No application restart or geometry rewrite.
- Make dependency advisory failures and unavailable advisory services fail CI; remove advisory-only fallbacks.
- Correct the production browser workflow to pass the actual frontend URL. Remove a grouped-command path that could mask the first failed check. Local pixel fixtures remain in CI.
- Prevent build metadata from borrowing timestamp/branch/version from a metadata file for a different commit. Require a valid commit identifier and timezone-aware timestamp before setting the existing metadata verification flag. This validates consistency/format, not authenticity or actual deployment age.
- Resolve and hash-lock Python direct/transitive dependencies for Python 3.11 and platform markers; keep production/development dependencies separate. Docker installs with `--require-hashes`.
- Upgrade FastAPI to 0.141.1, Starlette to 1.3.1, pypdf to 6.16.1, python-multipart to 0.0.31. Preserve Anthropic/httpx and Uvicorn pins. Installed metadata and `pip check` replace an obsolete exact-framework assertion.
- Upgrade PDF.js 4.0.379 to 4.10.38, include it in npm's integrity lock/audit, copy runtime assets from `npm ci`, remove the vulnerable cached generated copy, and explicitly pass `isEvalSupported:false` at all three parsing call sites. Pin Netlify Node to 22.
- Fix bundle reporting when a present vendor asset has a null absence reason. Read required assets from the actual shell array instead of treating mkdir/copy directories as files; remove an unsubstantiated offline-environment statement.
- Correct the event-loop comparative assertion at the monitor's 10 ms sampling resolution. Sub-tick work must remain sub-tick; measurable work must improve. Existing 250 ms/500 ms limits, output parity and the heavy-work 4x witness remain enforced; negative cases reject regression.

PDF.js advisory: [Mozilla GHSA-wgrm-67xf-hhpq](https://github.com/mozilla/pdf.js/security/advisories/GHSA-wgrm-67xf-hhpq). The former 4.0.379 copy is affected by CVE-2024-4367. A clean scan is time-bound and does not prove absence of application vulnerabilities.

## Files changed

- `.github/workflows/ci.yml`
- `.github/workflows/production-verify.yml`
- `DEPENDENCY-POLICY.md`
- `Dockerfile`
- `acs_build_info.py`
- `docs/audits/2026-09-05-production-trust.md`
- `netlify.toml`
- `package-lock.json`
- `package.json`
- `public/app/ui/workspace-ui-wiring.js`
- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements.in`
- `requirements.lock`
- `requirements.txt`
- `tests/deploy/verify_deploy.py`
- `tests/remediation/test_asgi_client_contract.py`
- `tests/remediation/test_build_metadata.py`
- `tests/remediation/test_bundle_report.py`
- `tests/remediation/test_ci_gate.py`
- `tests/remediation/test_dependency_lock.py`
- `tests/remediation/test_event_loop.py`
- `tests/remediation/test_pdf_runtime.mjs`
- `tools/bundle_report.py`
- `tools/dependency_audit.py`
- `tools/netlify-build.sh`
- `tools/vendor.sh`

## F. Test plan and executed evidence

All commands below ran from the repository. `P` in this report denotes `/workspace/scratch/5b03d54e3a82/acs-release-venv/bin`; `E` denotes `/workspace/scratch/5b03d54e3a82/evidence`. Python test runners used `PATH=$P:$PATH`. Counts are suite assertions unless explicitly labelled targets; overlapping runs must not be added together.

| Executed command | Result |
|---|---|
| `python -m pip install --require-hashes -r requirements.txt -r requirements-dev.txt` using release venv Python 3.11.15 | Exit 0; actual hash-checked installation |
| `python -m pip check` using release venv | Exit 0; no broken requirements |
| `pip-audit -r requirements.txt --format json --output E/pip-audit-baseline.json` using audit venv | Exit 1; 57 advisory records across 3 packages, not 57 distinct CVEs |
| `pip-audit -r requirements.txt --format json --output E/pip-audit-after.json` using audit venv | Exit 0; no known vulnerabilities found |
| `npm audit --json > E/npm-audit-final.json` | Exit 0; 0 findings, including locked PDF.js |
| `bash tools/ci_run.sh --log E/phases-python-final.log --label 'all phase Python contracts' --runner python3 tests/phase*/test_*.py tests/security/test_security.py` | 10 targets passed, 0 failed; 2,100 assertions passed, 0 failed |
| `bash tools/ci_run.sh --log E/parity-final.log --label 'phase parity' --runner node tests/phase4/test_parity.js tests/phase5/test_parity.js tests/phase6/test_parity.js tests/phase7/test_parity.js tests/phase8/test_parity.js tests/phase9/test_parity.js tests/phase9_1/test_parity.js tests/phase9_2/test_parity.js` | 8 targets passed, 0 failed; 288 assertions passed, 0 failed |
| `bash tools/ci_run.sh --log E/node-final.log --label 'Node mirror and remediation contracts' --runner 'node tests/lib/run.js' tests/phase2/test_*.js tests/phase3/test_visual.js tests/phase3/test_visual_adversarial.js tests/phase3/test_dev_api.js tests/remediation/test_csp.js tests/remediation/test_webgl_diagnostics.js tests/remediation/test_concurrency.js tests/remediation/test_production_error_ui.js tests/remediation/test_persistence.js tests/remediation/test_model_apply.js tests/remediation/test_scene_limits.js` | 24 targets passed, 0 failed; 2,913 Node assertions passed. Embedded browser probe reported NOT VERIFIED; this is not a browser pass. |
| `bash tools/ci_run.sh --log E/remediation-final.log --label 'all remediation Python contracts' --runner python3 tests/remediation/test_*.py` | Exit 1; 24 targets passed, 2 failed. Event-loop comparison failed; cancellation suite aborted on psutil NoSuchProcess. Completed summary assertions: 2,064 passed, 1 failed; partial cancellation assertions not included. |
| `python3 tests/remediation/test_event_loop.py > E/event-loop-final.log 2>&1` | After fix: 63 passed, 0 failed; actual asyncio/validators/Redis, not FastAPI routing |
| `python3 tests/remediation/test_ci_gate.py > E/ci-gate-final.log 2>&1` | 78 passed, 0 failed; executes shipped shell gate bodies with success/failure witnesses |
| `python3 tests/remediation/test_build_metadata.py` | Before fix: 94 passed, 5 failed. After: 99 passed, 0 failed |
| `node tests/remediation/test_pdf_runtime.mjs > E/pdf-runtime-final.log 2>&1` | 7 passed, 0 failed; actual vendored parser/worker, text extraction, page dimensions, malformed input rejection; Node only |
| `bash tools/netlify-build.sh > E/frontend-build-final.log 2>&1` | Exit 0; vendoring, metadata stamp, integration/index/API-base/CSP-hash guards |
| `bash tools/vendor.sh > E/vendor-final.log 2>&1` | Exit 0; integrity-locked assets and removal of obsolete PDF copy |
| `python3 tests/deploy/verify_deploy.py > E/deploy-closure-final2.log 2>&1` | 600 passed, 0 failed; static deployment closure, not production verification |
| `npx playwright install chromium` | Exit 1; managed browser CDN download timed out |
| `npx playwright install --only-shell chromium` | Exit 1; managed headless-shell CDN download timed out |
| `python3 tests/deploy/verify_backend_live.py > E/backend-live-final.log 2>&1` | Exit 2; direct DNS unavailable here; generation not called |
| `git diff --check` | Exit 0 |

Cancellation environment reproduction: `python -c 'import os,psutil; print(os.getpid()); print(os.path.exists("/proc/%s"%os.getpid())); print(psutil.Process())'` reports that the running process has no corresponding `/proc` entry, then raises `psutil.NoSuchProcess`. The test remains enabled and unchanged. Its outcome is **NOT VERIFIED**, not PASS. The original whole remediation run remains failed; a complete green rerun has not been claimed.

The initial baseline remediation runner also failed due to unavailable Chromium, a stamped generated build-info file violating source-token expectations, and the bundle null-reason defect. Generated measurement/stamp outputs were preserved in evidence and restored to repository source form. An early dependency verification run overlapped installation and failed on missing packages; the completed-install critical-path rerun passed all 5 targets (803 assertions).

## Browser verification

**BROWSER NOT VERIFIED**. No real Chromium runtime CSP, WebGL pixel, PDF rendering, keyboard/accessibility or responsive result is claimed from Node/DOM contracts. Playwright-managed discovery remains intact; no hard-coded executable, version downgrade or skipped gate was introduced to manufacture a pass. Windows execution is also NOT VERIFIED.

## CI status

Existing PR run [33380958761](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/33380958761): eight substantive jobs passed; Chromium direct suite and required aggregate failed. Public annotations identify one failing direct target, but do not expose which target or its complete failure log.

Production verification run [33961042931](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/33961042931): backend passed; page boot failed. Its old workflow tested a locally served checkout despite its live label. This phase corrects the URL and shell semantics, but does not claim to have diagnosed the remote browser target without logs.

New-branch remote CI: **NOT RUN**. GitHub connection was reported successful by the app, but no GitHub operation tools were exposed to this execution session. A noninteractive push dry-run failed because Git had no credentials. Do not confuse this runtime access limitation with the user not connecting GitHub.

## G. Security plan

Enforce the new dependency gates and maintain lock integrity. Then implement tenant-aware authentication/authorization, private upload quarantine/storage with bounded parsing, durable abuse budgets, transactional revision checks and request/job correlation without secrets. Add a dedicated secret-scanning gate, audit its false-positive process, and verify headers/CORS in each environment. Existing static deployment security scans are not a comprehensive secret scan. No CSP weakening, token exposure, production data mutation or arbitrary regulatory threshold was introduced.

## H. Deployment plan and status

**PRODUCTION VERIFICATION PENDING** for these changes. First make the branch available through authenticated repository access, run all required CI including Chromium and cancellation on a normal Linux runner, and run the cross-platform harness on Windows. Review exact-commit artifacts and timestamp sources. Deploy to staging, verify front/back SHA, CSP/CORS, health/readiness and create/upload/confirm/model/edit/export workflows with no critical console errors. Record rollback artifacts and data-migration reversibility. Production release requires explicit authorization and completed gates. No merge, push or deploy is represented as completed in this report.

## I. Definition of done / next actions

A phase closes only with implementation, reproducible passing tests, security review, real-browser evidence where relevant, regression evidence and updated documentation. A release additionally requires reviewed exact-commit CI, environment provenance and verified deployed workflows. This phase has useful implemented fixes, but its browser/cancellation/remote release gates remain open. Advance to identity and persistence only after closing current verification blockers, consistent with the requested priority order.
