# Google sign-in for acsAI

ACS keeps its existing Supabase users, sessions, project UUID ownership and RLS.
Google is the first sign-in option; email/password, email confirmation and
password recovery remain available. No Firebase auth, SMS, schema migration,
admin credential or new dependency is required by this change.

## Provider setup before release

The ACS Supabase project is **AAA**, reference `hbahakzhrnpmgwkoyyhm`.
The Tadawee project is separate and must not be used for ACS authentication.

1. In [Google Auth Platform](https://console.cloud.google.com/auth/overview),
   select the Google Cloud project you own. The existing Firebase-linked
   project can be used; Firebase Phone Authentication is not involved.
2. Configure audience, branding and a support email. Use an External audience
   for public users. If the app is in Testing, add the intended test account;
   complete Google's production requirements before public rollout.
3. Create an OAuth client of type **Web application**. Use these exact values:

| Setting | Value |
| --- | --- |
| Authorized JavaScript origin | `https://sprightly-selkie-d906c3.netlify.app` |
| Authorized redirect URI in Google | `https://hbahakzhrnpmgwkoyyhm.supabase.co/auth/v1/callback` |
| Supabase Site URL / allowed app redirect | `https://sprightly-selkie-d906c3.netlify.app/` |

4. Enable Google under **Authentication → Sign In / Providers** in the
   [ACS Supabase dashboard](https://supabase.com/dashboard/project/hbahakzhrnpmgwkoyyhm/auth/providers).
   Enter the Google Client ID and Client Secret there. Never put the Client
   Secret in the frontend, a commit or a chat message.
5. Grant only `openid`, email and profile scopes. This integration does not
   request Gmail, Drive, contacts, or offline access to Google APIs.

The gateway uses its existing `ACS_AUTH_SUPABASE_URL` and
`ACS_AUTH_SUPABASE_PUBLISHABLE_KEY`. `ACS_AUTH_SITE_URL` selects a server-owned
HTTPS app callback (default: the production root above). The frontend requires
that callback to have the same origin as the initiating tab, so a production
callback cannot strand a preview tab's proof. To test a separate preview,
configure an isolated backend's callback and CORS origin and allow that exact
callback in Supabase; do not enable broad redirect wildcards.

## Flow and account continuity

- The browser generates a 256-bit random verifier in its own tab. Only its
  SHA-256 challenge goes to `/v1/auth/google/start`. The gateway checks the
  public Supabase provider settings and constructs the Google authorization
  URL using the configured Supabase project and callback.
- The Google round trip uses the same tab. Supabase checks the provider OAuth
  state and redirects back with a one-time code. ACS removes that code from
  the address bar before asynchronous work and exchanges it with the stored
  proof at `/v1/auth/google/exchange`.
- The proof expires after ten minutes and is consumed before exchange. A
  missing proof, wrong origin, changed account, cancellation or stale response
  cannot open a project. A failed exchange requires starting Google again.
- Only the Supabase session is returned. Google API access/refresh tokens are
  discarded. Existing bootstrap and user-token RLS checks remain authoritative.
- Supabase controls identity linking for matching verified email addresses.
  Use the same email as the existing ACS account to retain its user identity;
  ACS does not merge users or transfer projects based on browser-supplied data.
  A different Google email may create a separate account.

## Validation and deployment

Run `node tests/remediation/test_auth_session.js` and
`python3 tests/remediation/test_auth_gateway.py`. These cover PKCE challenge
generation, fixed redirects, cancellation, session races, first-project naming,
existing-project reuse, recovery and logout. Run `bash tools/netlify-build.sh`
and `node tests/remediation/test_auth_shipped_page.cjs` with Chromium available
to verify the real shipped UI at phone and desktop widths under production CSP.
The dedicated Google sign-in workflow runs these checks with mocked provider
responses; it does not sign in to a real Google account.

Deploy the backend routes before the frontend. A live owner-authorized Google
round trip is still required after provider setup: verify the signed-in email,
existing project access, a reload, and logout on the production origin. No live
Google success or production activation is claimed by the mocked checks.

References checked on 2026-09-13:
[Google provider setup](https://supabase.com/docs/guides/auth/social-login/auth-google),
[PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow),
[identity linking](https://supabase.com/docs/guides/auth/auth-identity-linking),
[Supabase Auth API](https://github.com/supabase/auth/blob/master/openapi.yaml).

SMS is out of scope for ACS. Tadawee caregiver notifications need a transactional
messaging provider such as Prelude Notify and their own templates and delivery
handling. Successful Prelude Verify OTP testing does not establish Notify
sender approval or production availability.
