"""Small offline regressions for the published-revision wait; no network."""
import importlib.util
import contextlib
import io
import json
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
