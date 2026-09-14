# First-project creation after Google login

Production request logs on 2026-09-14 show Google start/exchange succeeding
at 03:43 UTC, followed by bootstrap-project POST 403 after a name was provided.
The initial unnamed bootstrap correctly returned 400 (project name required).

The SELECT policy only consulted project membership. INSERT uses
`Prefer: return=representation`, so PostgreSQL checks SELECT visibility before
the AFTER INSERT trigger creates the owner membership. A rollback-only probe
using a synthetic identity reproduced SQLSTATE 42501 on INSERT RETURNING.

The repair includes direct authenticated owner visibility in the SELECT policy,
alongside the existing collaborator predicate. INSERT still requires owner_id
to equal auth.uid(); RLS, memberships, project identities, and grants stay intact.
No service credential or caller-provided owner bypass is introduced.

## Applied production repair

Supabase project AAA (`hbahakzhrnpmgwkoyyhm`) migration
`20260914035029_acs_project_owner_returning` was applied successfully.
The CLI-created local migration was aligned to the version returned by the
production migration ledger.

`tests/remediation/project_bootstrap_returning.sql` passed both in a transaction
with the proposed policy and again after deployment. It verifies creation with
RETURNING, the owner membership, owner reload, and denied unrelated read access.
All probe users and project writes were rolled back; no real owner was impersonated.

The gateway also maps project-store failures to a project-specific Arabic message
instead of suggesting that successful Google login failed. This code change
requires normal CI/merge/deployment; the database repair is already active.
Local auth gateway tests: 26 passed.

The real owner's next project attempt remains the final end-to-end confirmation.
This change does not remove email login or claim completion of Google-only UI.
