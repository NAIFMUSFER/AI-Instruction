# Firebase phone verification readiness

Project: `naif-c8b45`. The owner confirmed Phone enabled, Blaze billing,
Saudi Arabia allowed, and the production Netlify domain authorized.

`/firebase-check/index.html` is a standalone, explicit SMS smoke test. It does
not integrate Firebase identities with ACS project access. Sending requires
a user action and reCAPTCHA; no automatic sends or analytics are included.
Firebase auth state is in memory and signed out after successful verification.
The browser cooldown is a UX control, not a server-side abuse limit.

## Manual release gate

- Confirm the deployed page has the scoped Firebase CSP, with no second
  conflicting `frame-src 'none'` policy. Check reCAPTCHA on iOS Safari.
- Authorize the exact preview domain in Firebase when using a deploy preview.
- Submit your own Saudi number; enter the received code directly on the page.
- Confirm success; confirm opening ACS still uses its existing Supabase session.
- Do not interpret an SMS delivery receipt as a completed code verification.

## Remaining application integration

Current ACS uses `/auth/v1/user`, Supabase refresh/logout endpoints and UUID
foreign keys referencing `auth.users(id)` for project ownership, memberships,
jobs and approvals. A Firebase ID token cannot be substituted into this contract.

Before enabling phone login on the main page, implement and verify an explicit
identity mapping with proof of both identities for existing-account linking.
Never auto-link by a browser-provided UUID, email or matching phone number alone.
Supabase third-party Firebase integration requires project registration and a
server-issued `role: authenticated` claim; it does not migrate `auth.users` or
convert Firebase subjects into the existing project UUIDs. Preserve existing
users, ownership policies, and email recovery throughout the migration.

References:
- https://firebase.google.com/docs/auth/web/phone-auth
- https://supabase.com/docs/guides/auth/third-party/firebase-auth

Live SMS and production account integration are pending; local mocked tests
must never be reported as proof of delivery or successful production login.
