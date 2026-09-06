# Audit evidence and reproduction

Base: remediation/production-trust at 962f8daec2f194957d1a4322ce1ed22fd39086ea.
The work branch is audit/fix-2026-09-06. baseline/ is immutable evidence from the original source.
Evidence fixtures are intentionally malformed. They are not customer construction deliverables.

Use a separate checkout/worktree for execution: repository build/test commands generate files.
Activate the Python environment with requirements.txt plus numpy and psutil; run npm ci.
Python 3.12.13 / Node 24.19.0 were used here; Docker/CI versions differ as recorded in the report.

```sh
python artifacts/audit/tools/audit_run_tests.py /absolute/path/to/checkout /absolute/path/to/new-results
python artifacts/audit/tools/audit_model_probes.py /absolute/path/to/checkout /absolute/path/to/new-model-probes
python artifacts/audit/tools/audit_http.py /absolute/path/to/checkout /absolute/path/to/new-http
```

audit_http.py starts an actual local FastAPI process and makes the requests in requests.json.
It requires a real provider credential for generation. Do not put credentials in arguments/files.
--live --generate makes two real, potentially billed requests to the configured public service;
it is separate from the offline regression suite. Existing live records describe a newer SHA.

```sh
node artifacts/audit/tools/audit_generate_local.js /absolute/path/to/checkout /absolute/path/to/new-run/local-models
python artifacts/audit/tools/audit_exports.py /absolute/path/to/checkout /absolute/path/to/new-run/local-models /absolute/path/to/new-run/local-exports --local
```

The local generator expects sibling http/requests.json. It executes shipped generation functions
with explicit DOM-control doubles and records this scope. local-bundle.js is an intermediate
reproducible bundle; it is not an application source change. There is no LLM or pixel rendering
in this probe. audit_exports uses the shipped geometry/docs compilers; only its room-outline
DXF is audit-specific because no native DXF exporter was found.

audit_extra.py uses real ASGI/form/image parsing and a deterministic provider double.
Place its output beside model-probes/ from audit_model_probes.py, since it also reads the
explicit-elevation glTF. The multipart test is bounded to MAX_UPLOAD+1024 bytes.

audit_js_probes.js runs shipped DXF/transport functions. It expects the baseline local bundle
at ../../baseline/local-models/local-bundle.js relative to its output. It never sends a request.

Full original stdout/stderr lives in baseline/all-tests/*.log. Harness failures are retained
and distinguished from application failures in baseline/TEST-RESULTS.md.
No log states that unavailable Chromium or missing provider credentials passed.
The original independent 22-defect fixture was not available; our counterexamples are labelled.

Secret scans only record type/location, never values. Their heuristic scope is documented.

## Resume after the decision

The last product commit tested is 9597a126e2cb96765d22447ddcf7c6422e1701e9.
See AUDIT-REPORT.md section 14 for the CAD decision and the still-missing original 22-defect fixture.
Do not merge the original untracked files from the newer main into this older branch's test suite.
Use a clean worktree of the audit branch for candidate tests; candidate-source-check.json records
the source equality for the completed run (the two differing JSON files are generated test outputs).

Final full-suite evidence: fixes/C02b/all-tests-confirmed/.
Final case outputs and stage timings: fixes/C02b/regeneration-final/local-exports/.
The final Netlify build was executed in a clean worktree of the product commit above; final/ holds
the command/result and complete log. No deployment was performed.

The original audit_model_probes.py is a **baseline probe** with old expected behaviour; do not treat
its hard-coded repair description as a final assertion. For the individual final validator witnesses:

```sh
python artifacts/audit/tools/audit_validator_cases.py /absolute/path/to/candidate artifacts/audit/evidence/model-probes /absolute/path/to/new-validator-results.json
node artifacts/audit/tools/audit_cad_decision_probe.js /absolute/path/to/candidate /absolute/path/to/new-cad-witness
python artifacts/audit/tools/audit_inventory.py /absolute/path/to/candidate /absolute/path/to/new-inventory
```

These 11 individual defect witnesses and one valid control do not replace the independent all-22 fixture.
Whitespace in raw logs is intentionally preserved verbatim; whitespace gates apply to changed source,
not to rewriting captured stdout/stderr.
