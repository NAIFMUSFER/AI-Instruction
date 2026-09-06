# Dependency policy

Production requirements and development tools are separate. Reviewed direct inputs
are `requirements.in` and `requirements-dev.in`. They contain explicit version pins.
The production lock is `requirements.lock`; `requirements.txt` is its byte-identical
copy because Docker copies this file alone. `requirements-dev.txt` is a separate,
hashed lock and is excluded from the production image.

Locks were resolved against the package index on 2026-09-05 using uv 0.11.33.
They include distribution SHA-256 hashes and conditional dependencies for supported
platforms, including Linux and Windows. There are no unresolved dependency names.
Actual Windows installation and execution must still be tested in Windows CI.

```bash
uv pip compile --universal --python-version 3.11 --generate-hashes --no-strip-extras requirements.in -o requirements.lock
python -c "from pathlib import Path; Path('requirements.txt').write_bytes(Path('requirements.lock').read_bytes())"
uv pip compile --universal --python-version 3.11 --generate-hashes --no-strip-extras requirements-dev.in -o requirements-dev.txt
python -m pip install --require-hashes -r requirements.txt -r requirements-dev.txt
python -m pip check
```

The Starlette, multipart and pypdf upgrades address advisories detected in the old
0.36.3 / 0.0.9 / 4.0.0 pins. FastAPI changes with Starlette so declared framework
constraints remain satisfied. The Anthropic/httpx pair and Uvicorn version are
preserved. The ASGI compatibility test reads installed package metadata and executes
`pip check` instead of permanently requiring the vulnerable FastAPI/Starlette pair.

CI must fail on dependency drift, vulnerability findings, unavailable advisory
services, install/hash failures or test failures. No `continue-on-error` or shell
fallback may turn a scan failure into a success. A clean advisory scan is time-bound;
it is not proof that the application has no security defects.

Runtime browser libraries must agree between the npm lock, build scripts and imports.
Use `npm ci`; include every shipped npm package in the lock so `npm audit` covers it.
Never audit only package names while downloading untracked runtime libraries later.

Every dependency update requires API/upload regressions, provider-contract tests,
frontend build checks and real Chromium for affected browser behavior. An unavailable
browser is `BROWSER NOT VERIFIED`, and prevents closing the release gate.
