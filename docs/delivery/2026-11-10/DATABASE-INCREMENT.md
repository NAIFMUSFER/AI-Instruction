# Pending database activation increment

Prepared 10 November 2026 on top of safe application release commit `a6da9d6d278b71082781ce8ef075bbb741ee77ff`.

**Reviewable implementation; not approved as a production activation or deployed database change.** The actual ACS Supabase project is unavailable through the connected database account. The dedicated backend signer has not been provisioned. Deploying this adapter/jobs build before its matching database migrations and key configuration would deliberately fail closed.

## Included changes

- Explicit membership denial for missing/unauthorized users, with protected SECURITY DEFINER/helper grants and ownership predicates.
- Metadata pages and bounded individual revision reads preserve immutable history without the old aggregate 3 MB transport failure. The existing 100-revision admission limit remains.
- Canonical writes require full existing Python receipt validation followed by a short-lived backend capability bound to real JWT actor, project, purpose, exact document and expected head. Old authenticated public/private write RPCs and direct receipt-table writes are revoked at activation.
- Durable job admission, per-job lease tokens/heartbeats, SQL quota/concurrency checks, exact replay identity and a conservative explicit resume allowlist. Direct authenticated job mutations are revoked.
- A provider-call progress event must receive the parent's durable database acknowledgment before the child proceeds to outbound work. Missing/late acknowledgments prevent another call.
- Canonical append and matching leased job SUCCEEDED state commit atomically. Cancellation, lease expiry or a lost delivery response cannot downgrade an already committed result.
- Executable PostgreSQL migration/RBAC/job tests, bounded-history tests and process acknowledgment tests run in both the always-on delivery CI job and the focused adapter workflow. Existing safe-release checks remain present.

## Evidence and limits

The pending worktree passed 53 real PostgreSQL boundary assertions, 37 job assertions, 3 real process acknowledgment tests, 34 job-boundary cases and 54 connected/recovery/admission cases. Nine additional adapter/history suites passed (including 31 unittest cases). Results and complete logs are recorded in [pending job results](database/pending-job-test-results.json) and [pending adapter/history results](database/pending-adapter-history-results.json). Baseline denial/history regressions and detailed source review are in [database evidence](database/STATUS.md) and [independent job review](database/JOBS-ADVERSARIAL-REVIEW.md).

PostgreSQL tests use a real isolated engine with synthetic auth/storage scaffolding. They do not establish actual Supabase/PostgREST JWT behavior, production grant/migration state, or multi-connection lock-contention behavior. No real user data or paid provider call was used. A request already accepted by a provider cannot be recalled. Heartbeat persistence failures currently fail closed and can interrupt otherwise healthy long-running work; no automatic uncertain retry is enabled.

## Required activation sequence

1. Identify and access the actual ACS database; inspect its live migrations, table/function definitions and grants, and verify a recovery backup.
2. Pause new paid/cloud writes and drain workers. Keep guest/local entry available.
3. Securely provision one new random 32-byte key, encoded as 64 lowercase hexadecimal characters, for backend-only `ACS_PLAN_WRITE_SECRET` and the protected `acs_private.acs_backend_write_keys` row named `v1` (insert the row after migration 01 creates its table in step 4). Never put the value in Git, logs, browser configuration or a user JWT.
4. In the authorized release transaction apply migration `2026111001`, provision the protected key row, then migrations `2026111002` and `2026111003`. The activation migrations stop if the key is absent. Coordinate activation with deployment of this exact adapter/jobs build; do not serve mixed old/new write contracts.
5. Verify synthetic real-JWT owner/editor/viewer/removed-member and cross-project cases, malformed direct writes, exact revision save/approval/reopen, job cancellation/late completion, two replicas and real database lock contention. Record database migration IDs and backend commit SHA separately.
6. If activation fails, retain paused/read-only cloud writes until a secure compatible app/database pair is restored. Never grant the old unsafe RPCs as a fallback or rewrite immutable history.

This increment must stay a draft/unmerged activation candidate until those prerequisites are available and verified. Application improvements already released independently are not gated on obtaining database credentials, and are not replaced by this branch.
