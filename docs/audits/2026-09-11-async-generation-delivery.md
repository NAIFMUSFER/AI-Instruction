# Generation delivery after a lost browser connection

## Evidence before the change

At production commit `0598a4a7488bff0c43cd1bf7f9337f662d52714e`, the client
`acsGenerateFromServer` in `public/app/ui/workspace-ui-wiring.js:1805` waited for
one POST to `/v1/understand` with a 900,000 ms deadline. The handler at
`acs_understand_api.py:759` waited for both `run_job` and `_understand_payload`
before returning. It exposed no recoverable delivery record.

The reported iPhone screenshot shows NETWORK_ERROR. The operator's Render logs
show a corresponding iPhone POST returning HTTP 200 after 147,469 ms and a
SUCCEEDED worker. This establishes that server completion and browser delivery
can diverge, not which particular Safari/network component interrupted delivery.

## Change

New `/v1/jobs/understand`, `/v1/jobs/understand/image`,
`/v1/jobs/understand/pdf` and `/v1/jobs/edit` submission endpoints return 202.
A detached task invokes the EXISTING handler. Validation, generation quotas,
worker isolation, generation deadlines, review reports and edit approval remain
owned by the original handlers. The legacy endpoints are unchanged.

The client makes one submission, then short GET requests (15–20 seconds maximum
per request). A lost submission receipt is recovered by the pre-generated job
id. A lost status or result response is retried as a GET, never as another paid
POST. Reloading the same tab offers a recovery button. A server-side failed job
returns its original error envelope/status/Retry-After through the result route.
Stored terminal errors are delivered once even when the error is marked retryable;
only interrupted result delivery is retried. Error text is rendered as text.

Results and status require a random 256-bit capability in X-ACS-Job-Token;
knowing a job id alone is insufficient. Capabilities are not in URLs, response
bodies, logs, or the public diagnostic state. sessionStorage contains only the
job capability and delivery metadata, not the description, uploaded files, or
building. An IP-derived admission bucket is not used to authorize recovery, so
mobile network changes do not invalidate the capability.

## Explicit boundaries

Storage is **bounded process memory**, not a durable queue: 8 active tasks,
1,024 records, 8 MiB per result and 128 MiB reserved/retained result memory.
Results are retained for 30 minutes after completion; local input/admission
errors for at most 60 seconds. Idempotency tombstones are retained for 24 hours.
A sweeper removes expired payloads. No model or input is written to server disk.

**Server restarts/redeployments lose these records.** Both /health and the
recovery UI disclose this. Missing/expired records never cause automatic paid
resubmission. A durable shared store and queue are still required for recovery
across server restarts or multiple instances. The existing production deployment
is explicitly single-instance. This patch does not add infrastructure or costs.

Recovered edit results are downloaded as proposals; recovery never bypasses
engineering confirmation. A recovered generation still crosses the existing
model-application and first-frame checks. The original user description is not
invented after reload. OpenAI integration and provider settings are unchanged.

## Verification

- 13 Python controlled-handler tests exercise quick acceptance, receipt loss,
  capability checks, replay conflicts, expiry, capacity, deadlines, result bounds,
  original route/guard reuse and CORS.
- 10 Node tests execute the shipped job client and exercise receipt loss, offline
  polling, interrupted result downloads, GET-only reload recovery, backend-origin
  scoping, old-backend rejection and terminal HTTP 429/500/503/504 preservation.
- Local HTTP browser fixtures passed refresh and offline/reconnect in real
  Chromium and WebKit in Actions runs 34542359781 and 34542836057. These are
  transport tests, not live LLM or physical-iPhone claims.
- Run 34542836057 also passed the complete shipped mobile page under production
  CSP with actual Three.js: one POST, reload recovery, 123 canonical meshes,
  application state VISIBLE, and pixels_verified=true. Generation was a
  controlled six-second fixture, not a live provider call.
- That run exposed an isolated panel-test stub without acsApplyBuilding exports.
  The panel-only test now excludes the rendering-dependent recovery module, as
  it already excludes the rendering bridges. Its 37 assertions are unchanged;
  the separate shipped-page test covers the real recovery/render integration.
- The new Python and Node contracts are invoked by an existing mandatory CI
  generation target. Browser verification is a separate fail-closed workflow.
  Full CI and post-deployment checks must complete before release is reported.

No claim is made that an old synchronous result, created before this patch, can
be recovered: that old route did not retain a retrievable delivery record.
