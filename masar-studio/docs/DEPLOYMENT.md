# Deployment and restore runbook — 4.1.0

## Isolated deployment

In the existing repository use only `masar/production-v4`, directory `masar-studio`.
Do not merge MASAR into the legacy ACS production entrypoint or reuse dawaee data.
Read the exact CI report for this tree before deploying. `/api/version` reports the
package/model version and a commit when the host supplies RENDER_GIT_COMMIT/GIT_COMMIT.
`/api/ready` checks SQLite availability; it is not proof of storage durability.

## Native Node

Use Node 22.23.2. Build with `npm ci --ignore-scripts && npm run check && npm run build`.
Start with `npm start`. For the current repository prefix commands with
`cd masar-studio &&`. The production origin must be an HTTPS origin only, with no
credentials/path/query/fragment. Render's RENDER_EXTERNAL_URL may supply it.

Required production environment:

```
NODE_ENV=production
HOST=0.0.0.0
PORT=3000
PUBLIC_ORIGIN=https://your-domain.example
DB_PATH=/persistent/masar.sqlite
PERSISTENCE_CLASS=persistent
ALLOW_REGISTRATION=false
```

Create the mount first and grant only the application user access. Use exactly one
application instance against the database. Use BOOTSTRAP_EMAIL/BOOTSTRAP_PASSWORD
through the provider's secrets interface once; do not commit them. Remove the
bootstrap password after successful account setup. Do not reuse sample credentials.

## Docker Compose

`PUBLIC_ORIGIN=https://your-domain.example docker compose up --build -d`.
The named `masar-data` volume persists independently of container recreation. The
application filesystem is read-only and the service binds port 3000 on host loopback.
Provide an HTTPS reverse proxy, TLS certificate, OS security updates and monitoring.
Do not run `docker compose down -v` on a production data volume.

## Render preview

The included blueprint is free staging with PERSISTENCE_CLASS=ephemeral, a temporary
SQLite path and a permanent warning in the UI. It must not be represented as durable
production. A paid persistent disk/hosted database is a separate operator decision.
No cloud storage is provisioned merely by setting PERSISTENCE_CLASS=persistent.
Workspace selection and any specific recurring expense must be confirmed before
provisioning through a connector. Do not alter existing ACS/dawaee services.

## Consistent backup

Run as an authorized operator, outside the public HTTP interface:

```
node tools/backup.mjs create /persistent/masar.sqlite /secure-backups/2026-09-08.sqlite
```

The native SQLite online backup API includes a consistent WAL view. A raw copy of
the main SQLite file while writes are active is not an equivalent backup. The new
snapshot and JSON manifest are restricted to mode 0600. Place backups on separate,
access-controlled/encrypted storage. Do not upload them to a public source repository.
Retention, offsite transfer and scheduled jobs belong to the operator; the source
does not claim those services are already running.

## Recovery drill

1. Preserve the original database and backup. Restore only to a new target path.
2. `node tools/backup.mjs restore /secure-backups/2026-09-08.sqlite /persistent/restored.sqlite`
3. The tool checks hash, size, schema, foreign keys and integrity, and refuses overwrite.
4. Stop the app, change DB_PATH to the new restored path, start, and log in again.
   Old sessions are invalidated by the restore; project/account data is preserved.
5. Verify project IDs, history counts, exports and owner/reviewer access before traffic.

SHA-256 detects corruption, not adversarial replacement of both snapshot and manifest.
Restore only trusted backups from protected storage. Schema versions newer than the
server are refused, never silently downgraded. Rollback to an older application
requires a compatible database snapshot, not an in-place schema downgrade.

## Operational gates

Check HTTPS cookies/origin protection; create/save/read/restart/export; test an
unauthorized account; create/revoke a review link; verify the real disk lifecycle;
perform the recovery drill. Keep keys server-side. Optional AI needs an explicitly
configured model and key, and a separate authorized live acceptance test.
