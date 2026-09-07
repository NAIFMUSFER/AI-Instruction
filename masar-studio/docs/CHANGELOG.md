# 4.1.0

Recovered complete v4 modules; reconstructed missing frontend/build/tests from the
v3 delivery without claiming the old incomplete upload was a complete archive.

- Fixed IFC EXPRESS errors: placement axes, spatial aggregation, containment,
  owner history and hosted void depth. Verified real void-subtracted wall volumes.
- Encoded Arabic and supplementary Unicode with correct STEP UCS escapes; preserved
  literal backslashes rather than interpreting them as injected escape sequences.
- Preserved opening IDs, zero sill, door height and other doors during a door edit.
  Added explicit door/window deletion and door addition with preview/locks.
- Enforced full opening/host span, T-junction constraints, individual opening locks,
  polygon simplicity/overlap, layer consistency and unchecked discipline metadata.
- Fixed southeast/southwest notch orientation and office counts below floor count;
  recognized the Arabic retail noun.
- Repaired root-scoped offline PWA; private APIs and share-token URLs never cached.
- Preserved cloud base versions across local reload; added stale-save choices.
  Review comment resolution does not rewrite a project. Invalid links fail closed.
- Added CSV formula hardening, exact production origin validation, private DB
  permissions, no-downgrade schema gate and scoped persistence disclosure.
- Added consistent private backup/restore, session invalidation on restore,
  non-root read-only Docker/Compose and independent lifecycle tests.

See machine-readable test outputs for the exact source under test. This is not a
claim of arbitrary BIM round trip, building-code approval or live paid AI acceptance.
