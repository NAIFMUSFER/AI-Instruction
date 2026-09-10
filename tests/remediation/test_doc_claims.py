"""Regression checks for the F-53 CI integration and measurement failures."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'doc_claims', ROOT / 'tools/check_doc_claims.py')
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)


class Measurements(unittest.TestCase):
    def measure_script(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'suite.py').write_text(source)
            with mock.patch.object(claims, 'ROOT', tmp):
                return claims.measure('suite.py')

    def test_script_summary_is_measured(self):
        self.assertEqual(self.measure_script("print('3 passed, 0 failed')\n"),
                         (3, None))

    def test_unittest_runs_without_pytest(self):
        source = ('import unittest\n'
                  'class T(unittest.TestCase):\n'
                  '    def test_one(self): self.assertEqual(1 + 1, 2)\n'
                  'unittest.main()\n')
        self.assertEqual(self.measure_script(source), (1, None))

    def test_failed_suite_cannot_supply_a_passing_count(self):
        count, error = self.measure_script(
            "print('3 passed, 1 failed')\nraise SystemExit(1)\n")
        self.assertIsNone(count)
        self.assertIn('exited 1', error)

    def test_missing_browser_cannot_be_misreported_as_count_drift(self):
        count, error = self.measure_script(
            "print('20 passed, 0 failed')\n"
            "print('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED')\n"
            "raise SystemExit(1)\n")
        self.assertIsNone(count)
        self.assertIn('exited 1', error)

    def test_unparseable_success_is_not_a_measurement(self):
        count, error = self.measure_script("print('started')\n")
        self.assertIsNone(count)
        self.assertIsNotNone(error)

    def test_unavailable_measurement_fails_the_gate(self):
        with mock.patch.object(claims, 'discover', return_value=[
                ('KNOWN-ISSUES.md', 'tests/suite.py', 3, (0, 1))]), \
                mock.patch.object(claims, 'check_state', return_value=(True, 'ok')), \
                mock.patch.object(claims, 'measure', return_value=(None, 'failed')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(claims.main([]), 1)

    def test_skipped_measurement_fails_the_gate(self):
        with mock.patch.object(claims, 'discover', return_value=[
                ('KNOWN-ISSUES.md', 'tests/suite.py', 3, (0, 1))]), \
                mock.patch.object(claims, 'check_state', return_value=(True, 'ok')), \
                mock.patch.object(claims, 'measure', return_value=(None, 'SKIP: browser')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(claims.main([]), 1)


class RunnerIntegration(unittest.TestCase):
    def invoke(self, check, target_exit=0, guard_exit=0):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tools').mkdir()
            (root / 'tools/check_doc_claims.py').write_text(
                "print('DOCUMENTATION_GUARD_RAN')\nraise SystemExit(%d)\n" % guard_exit)
            target = root / 'target.py'
            target.write_text('raise SystemExit(%d)\n' % target_exit)
            cmd = ['bash', str(ROOT / 'tools/ci_run.sh'), '--runner', sys.executable]
            if check:
                cmd.append('--check-doc-claims')
            cmd.append(str(target))
            return subprocess.run(cmd, cwd=tmp, capture_output=True, text=True,
                                  timeout=10)

    def test_plain_runner_preserves_target_only_success(self):
        result = self.invoke(False, guard_exit=1)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('DOCUMENTATION_GUARD_RAN', result.stdout)

    def test_explicit_guard_runs_once_after_successful_targets(self):
        result = self.invoke(True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.count('DOCUMENTATION_GUARD_RAN'), 1)

    def test_explicit_guard_failure_blocks_success(self):
        result = self.invoke(True, guard_exit=1)
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_target_failure_is_preserved_before_guard(self):
        result = self.invoke(True, target_exit=3)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertNotIn('DOCUMENTATION_GUARD_RAN', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
