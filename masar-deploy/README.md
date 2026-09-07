# MASAR Studio 4 deployment bundle

This directory is intentionally isolated from the legacy ACS application on `main`.
Render deploys only this bundle from branch `masar/production-v4`.

The payload is a base64-split deterministic source tarball. `bootstrap.sh` reconstructs it, verifies SHA-256, extracts it into `.masar-runtime`, then runs MASAR check/build/test before the service starts.

Source bundle SHA-256: `f3e4c61eaa2b0c904025ecb8fa9e3ae974d60cfdf4ac232f37ac537c0fd6c9bf`

No existing ACS production files are modified by this branch-only deployment path.
