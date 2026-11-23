# Paid-operation and ingress delivery evidence — 2026-11-10

Baseline: `c37b5250dc4ff18ba0606add993b5afe52beebaa`. Source work only at this checkpoint; the integration owner records exact commits and actual deployment separately.

## Safe increment, independent of new database migrations

- The old plan `chat_edit` URL now delegates to the same workspace admission path. Explicit confirmation, bounded call budget, expected head and job ID are required. Both entry points share one process task pool and verified-actor quota key.
- Production unscoped direct/legacy asynchronous paid submission returns `409 PAID_WORKSPACE_REQUIRED` after authentication. Anonymous requests still receive `401`; old result retrieval and development/test handlers remain. The connected project workspace is the supported paid path.
- Outbound identity/auth requests have a cheap bounded gate (16 active outbound operations, 120 attempts per socket peer per minute, 1,200 globally per process per minute, at most 4,096 retained peers). No forwarded client identity is trusted. Disconnect does not free a still-running thread's permit. These are process safety bounds, not a distributed billing quota.
- Direct and asynchronous JSON/multipart bodies are bounded before framework parsing, including chunked input. Auth/project parsers use the same total upload deadline. Disconnect does not reserve a paid job.
- A different process ID no longer turns RUNNING into INTERRUPTED. Only known completed layout/detail/geometry failures or explicit budget exhaustion can offer resume; storage, transport, unknown and worker failures do not.
- Confirmed requirement metrics are checked before paid work. PR183 warehouse policy and canonical residential role changes are integrated without a branch merge.

The safe release does **not** claim durable lease expiry, signed job ownership, database write authorization, or durable pre-call accounting are deployed. The separate source snapshots in the integration owner's release-split directory retain the old database transport and add only compatible safety changes.

## Pending database increment

`2026111002_acs_workspace_job_leases.sql` depends on the database owner's verifier/key migration and atomic canonical-write migration. The signing key must already be provisioned before job mutation grants change. No production key or database migration was installed by this agent.

The signed job RPC enforces actor/project roles, confirmation, expected revision, idempotency, durable global/actor request quotas and capacity, one child resume per source job, monotonically spent call counts, a server-clock lease and worker token fencing. Membership is locked during each admission transaction. Lease comparisons refresh the clock after lock waits. Signature expiry caps lease renewal.

Worker progress is acknowledged over duplex IPC only after the trusted parent persists it. A rejected or expired progress acknowledgment blocks the next synthetic outbound operation in real process tests. Canonical append and job SUCCEEDED are one database transaction (implemented by the database owner); optional receipt retries cannot reverse completion. Cancellation, stale leases and late workers cannot append.

Unknown/expired provider outcomes are deliberately not resumable. Cancellation does not claim to recall an already accepted provider request. The heartbeat currently fails closed after a database error; a long in-flight result can be rejected after lease expiry even if connectivity later recovers. No duplicate request is automatically issued.

## Evidence

Four initial paid/preauth regressions and five ingress witnesses failed on the reviewed baseline before the fixes. Later, two real subprocess regressions proved that the old one-way progress pipe allowed outbound work before durable accounting. Before/after logs are adjacent to this document.

Observed passing suites:

| Suite | Observed result |
|---|---|
| delivery_paid_admission | 10 tests |
| delivery_ingress | 7 tests |
| auth_gateway | 26 tests |
| production_auth_boundary | 7 tests |
| supabase_auth_integration | 5 tests |
| async_generation_jobs | 13 tests |
| plan_http_command_boundary | 7 tests |
| workspace_recovery | 20 tests |
| connected_workspace | 17 tests |
| job_boundary | 34 assertions |
| delivery_progress_ack | 3 real subprocess tests |
| plan_store_postgres_boundary plus delivery_job_leases_postgres | 53 base + 37 lease SQL assertions |

A separate safe-snapshot run passed 53 tests before the final additional unknown-storage-resume witness; the final 10-test paid suite was also run independently. These counts are suite observations, not unique end-to-end customer journeys.

PostgreSQL tests execute real migrations/functions/grants against dedicated synthetic users/projects, using standalone PostgreSQL. True competing-connection lock contention, multiple deployed replicas, live authenticated accounts and a paid provider call were not exercised. Exact live database identity/key provisioning is an external deployment blocker, not a test pass. No fixture is evidence of live AI quality.
