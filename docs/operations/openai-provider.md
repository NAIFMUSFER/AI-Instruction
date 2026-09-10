# Native OpenAI provider — deployment and verification

## Scope

`acs_provider.py` resolves OpenAI as a first-class provider. `acs_openai.py`
implements the native Responses API with the existing locked `httpx==0.27.2`.
It does not send the Anthropic wire protocol to OpenAI and does not add or
upgrade dependencies. The existing text, plan/chunk, detail, vision, error,
telemetry, cancellation and geometry-validation boundaries remain in place.
The default provider is unchanged: merely deploying these files does not switch
a running service to OpenAI.

The request uses JSON mode (`text.format.type=json_object`), not a strict JSON
Schema output contract. Dynamic ACS floor/template objects continue through the
existing parser and Building validation. Valid JSON alone is not architectural
correctness, code compliance, or proof of a complete client programme.

## Credential ownership

OpenAI reads `OPENAI_API_KEY` only. It never silently uses `ACS_LLM_API_KEY`,
which may already contain the live DeepSeek credential. A key selector contains
the **name** of an allowed environment variable, never its secret value.

`ACS_LLM_FALLBACK_API_KEY_ENV=ACS_LLM_API_KEY` explicitly preserves the existing
DeepSeek key when OpenAI becomes primary. DeepSeek cannot select
`OPENAI_API_KEY`; OpenAI cannot select an arbitrary environment variable.
No key is copied into source, workflows, public assets, logs or deployment docs.
The health field `llm.openai_key_configured` reports presence only; it is NOT an
API authentication, model-access, billing or generation test.

The OpenAI endpoint is restricted to `https://api.openai.com/v1`, redirects are
not followed, and environment proxy credentials are not implicitly consumed.
A stale DeepSeek base URL therefore fails before an OpenAI key can be attached.

## Activation on the existing ACS Render service

Service: `acs-engine`. Do not change unrelated services or replace the complete
environment. Preserve the existing secret values and CORS allowlist.

1. Require the full PR CI result, including `ci-required`, to succeed.
2. Deploy the reviewed commit with DeepSeek still primary. Check `/health` and
   `/version` against the deployed commit and confirm
   `llm.openai_key_configured=true`. Do not print the key or list secret values.
3. Merge only these **non-secret** configuration changes into the environment:

```dotenv
ACS_LLM_PROVIDER=openai
ACS_LLM_API_KEY_ENV=OPENAI_API_KEY
ACS_LLM_BASE_URL=https://api.openai.com/v1
ACS_LLM_MODEL=gpt-5.4
ACS_ALLOWED_MODELS=gpt-5.4,gpt-5.4-mini
ACS_OPENAI_REASONING_EFFORT=low
ACS_LLM_TRANSPORT=stream
ACS_LLM_FALLBACK_PROVIDER=deepseek
ACS_LLM_FALLBACK_API_KEY_ENV=ACS_LLM_API_KEY
ACS_LLM_FALLBACK_BASE_URL=https://api.deepseek.com/anthropic
ACS_LLM_FALLBACK_MODEL=deepseek-v4-pro
ACS_LLM_FALLBACK_ON_BILLING=0
```

Leave `OPENAI_API_KEY` and the existing `ACS_LLM_API_KEY` untouched. Preserve the
existing global/per-user quotas, request timeouts and output-token budget.
The known model ceiling is 128,000 output tokens for `gpt-5.4` and
`gpt-5.4-mini`; unknown model identifiers get no invented ceiling. The current
ACS request budget is not automatically raised to that ceiling.

4. Wait for Render's configuration deployment to become live. Verify `/ready`,
   `/health` and the exact provider/model/host/fallback metadata.
5. Submit one small synthetic residential description via the existing API,
   without user/customer data. Correlate its request ID with server telemetry.
   Require a complete response, `provider=openai`, the intended model and
   `fallback_attempted=false`. A successful response served by DeepSeek is not
   proof that OpenAI worked. Do not repeatedly retry authentication or billing
   failures; report and roll back instead.
6. Verify the same flow through the production browser UI. Repeat the approved
   origin preflight tests plus a disallowed-origin negative control. An HTTP
   preflight success alone is not proof that generation or 3D rendering works.

## Fallback and spending boundaries

The pre-existing fallback allowlist remains authoritative: provider
unavailability, overload or connection failure before acceptance can select one
configured fallback. Billing fallback remains disabled unless an operator
explicitly opts in. Authentication, permissions, unknown models, rate limits,
timeouts, malformed JSON, refusal and truncated output do not silently switch
to another provider. The fallback uses its own model even when the client
provided a primary-model override.

After HTTP 200, an interrupted OpenAI transport is treated as incomplete, not as
a fresh connection failure eligible for duplicate spending. The adapter has no
SDK-level retry loop. The existing ACS request fingerprint and strategy/budget
controls still govern retries and escalation.

Responses must carry a terminal completed/incomplete/failed event. Complete-
looking deltas and `[DONE]` without a terminal response are not accepted.
Refusals and output-token ceilings remain distinct. Unknown token usage stays
`None`; total output usage includes reasoning, and cache/reasoning counts are
recorded only when the provider supplies them. Raw reasoning is never retained
by this adapter. `store=false` disables Responses application storage; it does
not assert a zero-retention agreement or replace the provider's data policy.

`content_token_multiplier=2.0` is a conservative scheduling allowance, NOT a
measured OpenAI efficiency ratio. Real workload measurements may justify an
explicit operator adjustment. It does not increase the output-token budget.

## Rollback without moving secrets

Restore these non-secret settings, keeping the original DeepSeek key in place:

```dotenv
ACS_LLM_PROVIDER=deepseek
ACS_LLM_API_KEY_ENV=ACS_LLM_API_KEY
ACS_LLM_BASE_URL=https://api.deepseek.com/anthropic
ACS_LLM_MODEL=deepseek-v4-pro
ACS_ALLOWED_MODELS=deepseek-v4-pro,deepseek-v4-flash
ACS_LLM_FALLBACK_PROVIDER=
```

An empty fallback-provider value disables fallback even if other fallback
variables remain. Wait for the configuration deploy and verify `/ready` and
provider/model metadata. Do not delete either secret to roll back.

## Automated evidence and its limits

`tests/remediation/test_openai_provider.py` uses synthetic `httpx.MockTransport`
responses. It exercises the real `U.call_llm` path, key/model isolation,
stream/create protocols, image translation, terminal-response validation,
redaction, bounded reads, usage accounting and fallback classification. It is
chained through the existing mandatory spatial CI target. These tests never
use a live API key and do not prove account credit, model access, live generation
quality, or browser rendering. Those require the post-deployment checks above.

Focused run 34539554757 passed the first 33 OpenAI tests and all nine provider
regression targets. Run 34539897158 additionally reproduces and fixes malformed
nested terminal-response handling, then runs the expanded suite and the same
nine targets. Temporary transformation scripts/workflows are removed before PR.

## Official reference material

Checked 2026-09-11:
- https://developers.openai.com/api/docs/models/gpt-5.4
- https://developers.openai.com/api/docs/models/gpt-5.4-mini
- https://developers.openai.com/api/docs/guides/streaming-responses
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/error-codes
- https://developers.openai.com/api/reference/python/resources/responses/methods/create
