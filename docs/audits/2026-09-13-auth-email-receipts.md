# ACS authentication email follow-up

The owner reported a reset email opening `localhost` and a signup message saying
the provider did not return a valid session. These are distinct failures.

## Signup response repair

[GoTrue REST signup](https://github.com/supabase/auth/blob/master/internal/api/signup.go)
returns the User object itself when email confirmation is pending. It may also
return an obfuscated User for repeated signup. It returns access/refresh tokens
only for an actual session. The ACS gateway previously forwarded that bare User,
while the browser expected a `user` property, producing the incorrect error.

The signup route now wraps only a successful, token-free bare User as
`{user, session: null}`. The browser clears the password and shows a conditional
confirmation/sign-in message. It does not save a session, open/create a project,
or claim that an email was sent or that a new account exists. Partial tokens,
malformed users and user-only sign-in results remain errors. No authentication,
RLS or approval check is bypassed.

Regression evidence covers both raw REST User shapes, the ASGI HTTP route,
no project creation, no-token browser handling, malformed/partial replies,
sign-in separation, password clearing and the exact production email callback.
The new raw-response cases failed before the repair.

## Reset URL configuration requires activation

The gateway already pins `redirect_to` to
`https://sprightly-selkie-d906c3.netlify.app/` by default. It ignores redirect
values supplied by the browser and rejects a non-HTTPS configured callback.

[Supabase redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls)
requires the production Site URL and matching allowed redirect URL. The owner
screenshot proves a localhost destination; the exact dashboard configuration
has not been read or changed through this session's tools.

For ACS project `hbahakzhrnpmgwkoyyhm` (AAA), set **Site URL** to
`https://sprightly-selkie-d906c3.netlify.app/` and add that exact value to
**Redirect URLs**, preserving any other legitimate project entries. The relevant
page is https://supabase.com/dashboard/project/hbahakzhrnpmgwkoyyhm/auth/url-configuration.
Then request a fresh recovery email from the ACS sign-in screen. Previously
issued links may be expired or already consumed; do not treat them as new proof.

The connected Supabase tools do not expose Auth configuration updates, and no
authenticated management CLI/token is available here. Do not change SQL auth
records, auto-confirm the user, reuse a screenshot password, or request the full
recovery link as a workaround. Actual reset email destination, owner password
entry and sign-in must be verified separately; this code fix does not establish
that the external Site URL was corrected.
