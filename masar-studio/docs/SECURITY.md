# MASAR Studio 4 — Security Notes

## Implemented

- scrypt password hashing with random per-password salt.
- timing-safe login comparison including dummy material for unknown users.
- random session token; only hash stored in SQLite.
- HttpOnly + SameSite=Strict cookie; Secure in production.
- CSRF required for authenticated state-changing routes.
- exact Origin enforcement on writes.
- bounded JSON bodies and canonical history validation before persistence.
- optimistic compare-and-swap to prevent stale project overwrite.
- account/project/share ownership isolation.
- share snapshots immutable; review comments stored separately.
- static serving allowlist; DB/server source/env/private files not served.
- CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy; HSTS in production.
- local rate limiting does not trust arbitrary forwarded IP headers.
- AI key remains server-side; AI returns proposal only.

## Authoring/import attack surface

### MASAR JSON
Import has size bound + schema/history validation before state replacement.

### IFC4
`shared/ifc.js` treats IFC as untrusted text:

- 12 MB maximum UI/import budget.
- requires IFC4 marker.
- quote/depth-aware STEP statement splitting instead of executing input.
- numeric/geometry validation before canonical model creation.
- bounded supported entity mapping; unsupported geometry rejects.
- imported document becomes a candidate new project only after explicit user acknowledgment.

No `eval`, code execution, arbitrary fetch or external-resource resolution occurs from IFC contents.

### DXF/images
DXF parser is limited to supported 2D entities and bounded line counts/coordinates. Images are presentation references; no embedded script execution.

## Remaining production work

- managed secret rotation.
- centralized logs/audit/metrics with redaction.
- MFA/SSO/recovery/email ownership verification.
- managed backup/restore drills and disaster recovery.
- WAF/DDoS controls where appropriate.
- external penetration test before public high-risk use.
- distributed session/rate-limit/persistence strategy for multi-instance scale.

The current rate limiter and SQLite design are single-node oriented.
