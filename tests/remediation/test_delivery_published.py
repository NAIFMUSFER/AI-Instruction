"""Small offline regressions for the published-revision wait; no network."""
import importlib.util
import contextlib
import io
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("published", ROOT / "tests/deploy/wait_published_revision.py")
published = importlib.util.module_from_spec(spec)
spec.loader.exec_module(published)
EXPECTED = "a" * 40
spec = importlib.util.spec_from_file_location("live", ROOT / "tests/production/verify_live.py")
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class ServedModuleImportTests(unittest.TestCase):
    def test_asset_contract_reads_target_deployment_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            deployed = Path(directory)
            (deployed / 'public/app').mkdir(parents=True)
            (deployed / 'tools').mkdir()
            shutil.copy(ROOT / 'tools/app_source.py', deployed / 'tools/app_source.py')
            (deployed / 'public/index.html').write_text('<html></html>')
            (deployed / 'public/app/main.js').write_text("import './deployed-only.mjs';")
            (deployed / 'public/app/deployed-only.mjs').write_text('export const active = true;')
            result = subprocess.run([sys.executable, '-c',
                "import json, runpy; print(json.dumps(runpy.run_path('tests/production/verify_live.py')['critical_assets']()[3]))"],
                cwd=ROOT, env={**os.environ, 'ACS_PUBLISHED_SOURCE_ROOT': directory},
                check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout), ['/app/main.js', '/app/deployed-only.mjs'])

    def verdict(self, missing_prefix=False, missing_vendor=False):
        shell = (ROOT / 'public/index.html').read_text()
        if missing_prefix:
            shell = shell.replace('"three/addons/":', '"wrong/addons/":')
        def http(url, **kwargs):
            asset = url.removeprefix('https://frontend.invalid')
            if missing_vendor and asset.endswith('/loaders/GLTFLoader.js'):
                return live.Resp(404, text='missing', raw=b'missing')
            source = ROOT / 'public' / asset.lstrip('/')
            text = source.read_text() if source.is_file() else "const REVISION = '160';\n" + ' ' * 100
            return live.Resp(200, text=text, raw=text.encode())
        state = {'frontend_root': live.Resp(200, text=shell, raw=shell.encode())}
        result = live.Results()
        with mock.patch.object(live, 'http', side_effect=http), contextlib.redirect_stdout(io.StringIO()):
            live.group_b(result, 'https://frontend.invalid', 'https://backend.invalid', 1, state)
        return next(row['status'] for row in result.rows if row['id'] == 'B6')

    def test_served_module_imports_work_with_shell_only_import_map(self):
        self.assertEqual(self.verdict(), 'PASS')

    def test_missing_served_prefix_fails_even_when_repository_map_is_valid(self):
        self.assertEqual(self.verdict(missing_prefix=True), 'FAIL')

    def test_missing_imported_vendor_file_fails(self):
        self.assertEqual(self.verdict(missing_vendor=True), 'FAIL')



class PublishedWorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github/workflows/delivery-published.yml").read_text()

    def test_monitor_changes_trigger_both_fast_lanes(self):
        triggers = self.workflow.split("permissions:", 1)[0]
        for event in ("pull_request", "push"):
            match = re.search(r"^  " + event + r":\n((?:    .*\n)+)", triggers, re.MULTILINE)
            self.assertIsNotNone(match, event)
            self.assertIn("branches: [main]", match[1])
            self.assertIn("tests/deploy/verify_public_guest.js", match[1])
            self.assertIn("tests/remediation/test_public_guest_monitor.cjs", match[1])
            self.assertIn("tests/production/**", match[1])
        self.assertIn("workflows: [CI]", triggers)
        self.assertNotIn("pull_request_target", self.workflow)
        self.assertIn("node tests/remediation/test_public_guest_monitor.cjs", self.workflow)

    def test_base_and_candidate_identity_are_separate(self):
        self.assertIn("ACS_VERIFY_EXPECT_SHA: ${{ github.event.pull_request.base.sha || github.event.workflow_run.head_sha || github.sha }}", self.workflow)
        self.assertIn("ACS_VERIFIER_SHA: ${{ github.event.pull_request.head.sha || github.event.workflow_run.head_sha || github.sha }}", self.workflow)
        self.assertIn("ref: ${{ env.ACS_VERIFIER_SHA }}", self.workflow)
        self.assertIn('test "$(git rev-parse HEAD)" = "$ACS_VERIFIER_SHA"', self.workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", self.workflow)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", self.workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.workflow)
        self.assertIn("contents: read", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)

    def test_receipts_have_distinct_labels_and_fixed_destinations(self):
        for label in ("monitor-on-base", "early-production", "post-ci-production"):
            self.assertIn(label, self.workflow)
        self.assertIn("name: ${{ env.ACS_RELEASE_SCOPE }}-${{ env.ACS_VERIFY_EXPECT_SHA }}-${{ github.run_id }}", self.workflow)
        self.assertIn("ACS_VERIFY_FRONTEND: https://sprightly-selkie-d906c3.netlify.app", self.workflow)
        self.assertIn("ACS_VERIFY_BACKEND: https://acs-engine.onrender.com", self.workflow)
        self.assertIn("public-journey-scope.json", self.workflow)
        self.assertNotIn("workflow_dispatch", self.workflow)
        self.assertNotIn("continue-on-error", self.workflow)

class PublishedRevisionTests(unittest.TestCase):
    def test_stamped_identity_and_verified_backend_required(self):
        source = (ROOT / "public/app/boot/build-info.js").read_text()
        with self.assertRaises(ValueError):
            published.revision("frontend", source)
        self.assertEqual(published.revision("frontend", source.replace("__ACS_GIT_SHA__", EXPECTED)), EXPECTED)
        for data in ({}, {"git_sha": EXPECTED}, {"git_sha": "short", "provenance_verified": True}):
            with self.assertRaises(ValueError):
                published.revision("backend", json.dumps(data))
        self.assertEqual(published.revision("backend", json.dumps({"git_sha": EXPECTED, "provenance_verified": True})), EXPECTED)

    def run_wait(self, probe, expected=EXPECTED):
        now = [0]
        def pause(seconds):
            now[0] += seconds
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, "evidence.json")
            code = published.wait("https://frontend.invalid", "https://backend.invalid", expected, 30, output,
                                  probe=probe, clock=lambda: now[0], pause=pause)
            return code, json.loads(output.read_text())

    def test_stale_deployment_can_recover_only_when_both_identities_match(self):
        calls = []
        def probe(kind, url, expected, timeout):
            calls.append((kind, url, timeout))
            return {"status": "MATCH" if kind == "frontend" or len(calls) > 2 else "MISMATCH", "git_sha": expected}
        code, result = self.run_wait(probe)
        self.assertEqual(code, 0)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(len(result["attempts"]), 2)
        self.assertTrue(all(timeout <= 15 for _, _, timeout in calls))
        self.assertTrue(all(url.endswith(("build-info.js", "/version")) for _, url, _ in calls))

    def test_missing_malformed_and_mismatched_deployments_fail_with_evidence(self):
        for status in ("UNAVAILABLE", "INVALID", "MISMATCH"):
            with self.subTest(status=status):
                code, result = self.run_wait(lambda *args: {"status": status})
                self.assertEqual(code, 1)
                self.assertEqual(result["verdict"], "FAIL")
                self.assertEqual(len(result["attempts"]), 2)
                self.assertIn("WITHIN_BOUND", result["reason"])

    def test_unknown_expected_identity_fails_before_any_network_work(self):
        def forbidden(*args):
            self.fail("invalid expected SHA must not probe")
        code, result = self.run_wait(forbidden, "unknown")
        self.assertEqual(code, 1)
        self.assertEqual(result["attempts"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
