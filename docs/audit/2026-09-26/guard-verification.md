# Baseline guard mutation evidence — 2026-09-26

The coordinator tested the actual guards in an archived copy of `adec616`. The supplied checkout was not mutated. Run:

```sh
python3 docs/audit/2026-09-26/audit_guard_mutations.py . /tmp/acs-audit-guard-evidence
```

The script needs the baseline virtualenv beside the checkout and its installed `node_modules`. It records command output outside Git, applies one mutation at a time, restores the original, and requires the sound and restored cases to pass. A nonzero broken case alone is insufficient.

<!-- ACS:CURRENT-STATE:BEGIN -->

This is a dated audit snapshot. The reproduction command above produced these exit codes:

| Guard command | Deliberate break | Sound / broken / restored |
|---|---|---|
| `python3 tools/check_integration.py` | Change the canonical viewport-contract version | `0 / 1 / 0` |
| `python3 tools/check_index_guard.py public/index.html` | Add executable inline JavaScript | `0 / 1 / 0` |
| `python3 tools/check_api_base.py` | Change API origin without CSP authorization | `0 / 1 / 0` |
| `python3 tools/check_csp_hash.py` | Change one import-map byte without updating its hashes | `0 / 1 / 0` |
| `node tests/remediation/test_module_graph.js` | Statically import a declared deferred module | `0 / 1 / 0` |
| `python3 tests/deploy/verify_deploy.py` | Introduce forbidden inline JavaScript into the shipped shell | `0 / 1 / 0` |
| `check_doc_claims.check_state()` through the Python command in the script | Alter a measured current-state byte count | `0 / 1 / 0` |
| `node tests/phase3/lib/extract_browser_bundle.js` | Introduce invalid syntax in shared state | `0 / 1 / 0` |

<!-- ACS:CURRENT-STATE:END -->

This demonstrates that the listed guards react to these specific broken contracts. It does not prove that they detect every possible integration error. Existing CI-runner and regulatory-boundary negative controls were also executed in the baseline suites; each remediation stream separately mutation-tested its new guards. No production guard was relaxed and no generated application output was hand-edited by this verification.
