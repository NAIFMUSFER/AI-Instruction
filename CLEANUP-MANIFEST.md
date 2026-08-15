# AI3 Clean Source Package — Cleanup Manifest

This package is a source-first reconstruction of the project for a clean GitHub redeploy.

## Removed from the clean package

- `.git/` — repository metadata/history is not application source.
- `node_modules/` — dependencies are reproducible from `package-lock.json`; CI already runs `npm ci`.
- `__pycache__/`, `*.pyc` — generated Python cache files.
- `last_llm_response.txt` — runtime diagnostic output; may contain raw model output and is already ignored by policy.
- `PRODUCTION-VERIFICATION.md` — obsolete Phase 8 checklist; Phase 9/9.1/9.2 checklists supersede it.
- `tests/production/outputs/*.log` — generated execution logs; JSON evidence and test sources are retained.
- `tests/remediation_baseline/*.log` — generated baseline logs; source/baseline metadata is retained.
- `public/vendor/` — build-generated runtime vendor directory; Netlify recreates it with `tools/netlify-build.sh`.

## Retained intentionally

- `package.json` and `package-lock.json`.
- `.github/workflows/` CI and production verification workflows.
- `netlify.toml`, `render.yaml`, `Dockerfile` and dependency lock files.
- Frontend and backend source.
- Phase test suites, fixtures, manifests and reference outputs that act as regression evidence/contracts.
- Current Phase 9, 9.1 and 9.2 production-verification checklists.
- Historical reports that document engineering/audit decisions, except the superseded Phase 8 checklist noted above.

## Repository-policy change

The clean package changes the repository to a conventional reproducible dependency model:

- `node_modules/` is ignored and not committed.
- CI/browser jobs restore exact Node dependencies via `npm ci` from `package-lock.json`.
- Netlify runtime assets (Three.js/pdf.js) remain separately vendored at build time by `tools/netlify-build.sh`.

`tests/remediation/test_dependency_lock.py` is updated to enforce this clean-source policy rather than the previous offline-vendored `node_modules` policy.
