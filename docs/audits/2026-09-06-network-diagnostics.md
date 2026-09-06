# Mobile generation failure: bounded remediation

## Executive summary / current state

The supplied mobile screenshots show `NETWORK_DNS` after generation, a rendered
building, and explicitly unsupported authoring capabilities. They do not establish
whether the rendered building came from AI or a built-in example, or whether the
generation request failed because of DNS, CORS, a proxy, Safari, or a disconnected
response. Successful release checks on `e99127b8e8317f3181424704e1281122321d2f66`
did not exercise paid generation or the user's iPhone.

The shipped transport was reproduced in Node with a Safari-style `TypeError('Load
failed')`: it returned `NETWORK_DNS`. Its error table also asserted that the request
never reached the server. Both claims exceeded the evidence available to browser
JavaScript. A second defect cleared the deadline as soon as headers arrived,
leaving response-body reads unbounded and reporting broken reads as invalid JSON.

Read-only Render app logs for 2026-09-06 08:45–08:51 UTC contain successful health
checks and one `llm_generation` event at 08:48:40 UTC with duration 378640 ms,
provider `deepseek`, and `success: true`. This is provider-stage success, not proof
that a valid model was delivered to this user. The event contains no request ID
that ties it to the screenshots. No new paid call was initiated for this audit.

## Files and architectural changes

- `public/app/ui/workspace-ui-wiring.js`: classify unspecified fetch/body failures
  as `NETWORK_ERROR`; reserve offline/non-delivery for the pre-send offline check;
  preserve HTTP status and request ID after headers; enforce the deadline through
  body reading and compose the caller's signal with the deadline signal.
- `public/app/trust/core.js`: bilingual uncertainty wording, conservative legacy
  `NETWORK_DNS` handling, and no safe retry claim based only on a client key.
  The backend currently has no implemented idempotency-key deduplication contract.
- `public/app/trust/wiring.js`: missing request ID no longer implies non-delivery.
- `tests/remediation/_transport_source.js`, `test_transport_errors.js`, and
  `test_transport_browser.js`: test the shipped transport block, including real
  Chromium fetch, body deadlines, offline, CORS, and CSP rejection cases. The
  browser harness is isolated transport coverage, not full WebGL or Safari proof.
- `tests/remediation/test_production_error_ui.js` and `test_model_apply.js`: update
  the explicit error contract and require the exact transport-class set.
- `.github/workflows/ci.yml`: both new suites are required by existing CI gates.

No model/schema migration, visual material change, CSP relaxation, CORS relaxation,
Render setting change, secret change, or paid API invocation is included.

## Security changes

Avoid misleading delivery/retry guarantees for potentially billable operations.
Do not infer DNS from opaque browser failures. Keep deadlines active until the
body completes and clean up timer/listener resources on completion or failure.
Production CSP is unchanged. Browser fixtures intercept the allowed backend URL;
they do not contact production or an AI provider.

## Tests executed locally

| Exact command | Result |
| --- | --- |
| `node tests/lib/run.js tests/remediation/test_production_error_ui.js` before changes | 262 passed, 0 failed |
| `node tests/remediation/test_transport_errors.js` | 18 passed, 0 failed |
| `node tests/lib/run.js tests/remediation/test_production_error_ui.js` after changes | 276 passed, 0 failed |
| `node tests/lib/run.js tests/remediation/test_concurrency.js` | 61 passed, 0 failed; client contract only |
| `node tests/lib/run.js tests/remediation/test_csp.js` | 142 passed, 0 failed; Node contract only |
| `node tests/lib/run.js tests/remediation/test_model_apply.js` | Initially 84 passed, 1 failed on the old ten-class count; after updating the explicit set: 85 passed, 0 failed |
| `node tests/lib/run.js tests/remediation/test_persistence.js` | 105 passed, 0 failed; pure logic only |
| `python3 tests/phase9_2/test_live_render.py` | 77 passed, 0 failed; contract only |
| `bash tests/deploy/verify_deploy.sh` | 605 passed, 0 failed; deployment content only |
| `/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/security/test_security.py` | 377 passed, 0 failed |
| `npm ci --ignore-scripts` | Exit 0, 7 packages installed |
| `bash tools/netlify-build.sh` | Exit 0; runtime assets, build metadata and CSP hash checks pass; generated local build stamp restored before commit |
| `node --check tests/remediation/test_transport_browser.js` | Exit 0 |
| `node --check public/app/ui/workspace-ui-wiring.js` | Exit 0 |
| `git diff --check` | Exit 0 |
| `PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=10000 npx playwright install chromium` | Exit 1, five CDN download timeouts; local browser NOT VERIFIED |

An initial mistyped command `python3 tests/deploy/test_deploy_closure.py` exited 2
because that file does not exist. The actual closure suite above was then run.

## Browser verification and CI status

Local Chromium acquisition failed; no mocked test is counted as browser evidence.
The new browser test is wired into CI with Playwright-managed discovery. At
preparation time, new-branch CI and browser results are pending. The PR checks and
subsequent review must establish results on its actual head, not reuse PR7's green
checks. Full regression is pending CI.

## Known issues / unverified items

- The actual phone disconnection cause remains NOT VERIFIED. The approximately
  six-minute provider call makes request-lifetime investigation relevant but does
  not prove Safari/proxy timeout. Do not tell the user to change DNS on this basis.
- Long generation still depends on a single HTTP response. Durable jobs with
  persisted results, polling/reconnection, ownership, budgets and transactional
  idempotency remain a separate architectural phase, requiring design and tests.
- Manually pressing the main generate button again can still create another
  billable request. This change removes the misleading safe retry affordance; it
  does not implement backend deduplication or durable recovery.
- ROTATE/SCALE and the displayed unsupported snapping modes remain unimplemented.
  Their mobile UI presentation and washed-out rendering require separate work;
  neither was concealed or reclassified as supported.
- Unknown engineering dimensions/provenance gaps identified in the earlier audit
  remain open. Regulatory validation: NOT EVALUATED.

## Deployment plan / definition of done / next actions

Publish a focused draft PR; require all CI checks and actual Chromium evidence,
review the diff and browser scope, then obtain approval for its production merge.
Do not reuse approval for PR7 as approval for this new production release. After
approval, verify both deployment SHAs, CSP/CORS and the changed transport on the
deployed frontend. PRODUCTION VERIFICATION PENDING for this change.

To close the reported phone incident, obtain a correlated request trace and verify
recovery/delivery on iOS; changing the displayed error alone is not incident closure.
