"""Offline regression of CI mirror admission; never accesses /etc or network.

The subprocess fake supplies verified plaintext only on successful gpgv calls.
These are control-flow/metadata regressions, not a real Ubuntu signature claim;
the CI preparation itself must run gpgv against the runner's archive keyring.
"""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import ci_prepare_apt as apt

NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
ORIGINAL = ('http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\n'
            'https://archive.ubuntu.com/ubuntu/\tpriority:2\n'
            'https://security.ubuntu.com/ubuntu/\tpriority:3\n')


def sources(codename):
    return ('Types: deb\nURIs: mirror+file:/etc/apt/apt-mirrors.txt\n'
            f'Suites: {codename} {codename}-updates {codename}-backports\n'
            'Components: main restricted universe multiverse\n'
            'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\n'
            'Types: deb\nURIs: mirror+file:/etc/apt/apt-mirrors.txt\n'
            f'Suites: {codename}-security\n'
            'Components: main restricted universe multiverse\n'
            'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n')


def release(codename, suite):
    return (f'Origin: Ubuntu\nLabel: Ubuntu\nSuite: {suite}\nCodename: {codename}\n'
            'Architectures: amd64 amd64v3 arm64\nComponents: main restricted universe multiverse\n'
            'Date: Wed, 11 Nov 2026 09:00:00 UTC\n'
            'SHA256:\n ' + 'a' * 64 + ' 123 main/binary-amd64/Packages.xz\n')


class Commands:
    def __init__(self, codename='noble', failures=None, transform=None, signature_failure=False):
        self.codename = codename
        self.failures = failures or {}
        self.transform = transform or (lambda text: text)
        self.signature_failure = signature_failure
        self.calls = []
        self.suite = None

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if cmd[0] == 'curl':
            url = cmd[-1]
            self.suite = url.split('/')[-2]
            candidate = next(c for c in apt.CANDIDATES if url.startswith(c))
            code = self.failures.get((candidate, self.suite), self.failures.get(candidate, 0))
            if not code:
                Path(cmd[cmd.index('--output') + 1]).write_text('synthetic signed envelope')
            return subprocess.CompletedProcess(cmd, code, url.replace('mirrors.kernel.org', 'mirrors.edge.kernel.org'), 'sensitive diagnostic must never be printed')
        if cmd[0] == 'gpgv':
            if not self.signature_failure:
                Path(cmd[cmd.index('--output') + 1]).write_text(self.transform(release(self.codename, self.suite)))
            return subprocess.CompletedProcess(cmd, 1 if self.signature_failure else 0, '', '')
        raise AssertionError('unexpected command: ' + repr(cmd))


class AptMirrorTests(unittest.TestCase):
    def prepare(self, runner, *, original=ORIGINAL, source_text=None, architecture='amd64'):
        code = runner.codename
        return apt.prepare(f'ID=ubuntu\nVERSION_CODENAME={code}\n', source_text or sources(code),
                           original, architecture, apt.KEYRING, run=runner, now=NOW)

    def test_actual_noble_and_resolute_suites_all_verified(self):
        for codename in ('noble', 'resolute'):
            with self.subTest(codename=codename):
                runner = Commands(codename)
                selected, result = self.prepare(runner)
                self.assertEqual(selected, apt.CANDIDATES[0])
                self.assertEqual(result.splitlines()[0], selected + '\tpriority:0')
                self.assertEqual(len(result.splitlines()), 3)
                self.assertIn(ORIGINAL.splitlines()[0], result)
                self.assertIn(ORIGINAL.splitlines()[2], result)
                expected = {codename + suffix for suffix in ('', '-updates', '-backports', '-security')}
                self.assertEqual({cmd[-1].split('/')[-2] for cmd, _ in runner.calls if cmd[0] == 'curl'}, expected)
                self.assertEqual(sum(cmd[0] == 'gpgv' for cmd, _ in runner.calls), 4)

    def test_only_mirror_network_failures_allow_verified_alternate(self):
        for failure in (6, 7, 28):
            runner = Commands(failures={apt.CANDIDATES[0]: failure})
            selected, result = self.prepare(runner)
            self.assertEqual(selected, apt.CANDIDATES[1])
            self.assertEqual(result, selected + '\tpriority:0\n' + ORIGINAL)
            self.assertEqual(sum(cmd[0] == 'gpgv' for cmd, _ in runner.calls), 4)

    def test_any_pocket_network_failure_requires_all_four_on_alternate(self):
        runner = Commands(failures={(apt.CANDIDATES[0], 'noble-security'): 6})
        selected, _ = self.prepare(runner)
        self.assertEqual(selected, apt.CANDIDATES[1])
        self.assertEqual(sum(cmd[0] == 'gpgv' for cmd, _ in runner.calls), 7)

    def test_tls_http_proxy_dns_and_policy_failures_never_fall_back(self):
        for failure in (5, 22, 35, 60, 63, 97):
            with self.subTest(curl_exit=failure):
                runner = Commands(failures={apt.CANDIDATES[0]: failure})
                with self.assertRaisesRegex(apt.PreparationError, 'HTTPS_FAILED'):
                    self.prepare(runner)
                self.assertEqual(len(runner.calls), 1)

    def test_bad_signature_never_falls_back(self):
        runner = Commands(signature_failure=True)
        with self.assertRaisesRegex(apt.PreparationError, 'SIGNATURE_FAILED'):
            self.prepare(runner)
        self.assertEqual([c[0] for c, _ in runner.calls], ['curl', 'gpgv'])

    def test_wrong_suite_codename_origin_architecture_rejected(self):
        for old, new in [('Suite: noble', 'Suite: resolute'), ('Codename: noble', 'Codename: resolute'),
                         ('Origin: Ubuntu', 'Origin: Other'), ('Label: Ubuntu', 'Label: Other'),
                         ('amd64 amd64v3 arm64', 'arm64'), ('restricted universe multiverse', 'restricted')]:
            with self.subTest(field=old):
                runner = Commands(transform=lambda text, old=old, new=new: text.replace(old, new))
                with self.assertRaisesRegex(apt.PreparationError, 'IDENTITY_MISMATCH'):
                    self.prepare(runner)
                self.assertEqual(len(runner.calls), 2)

    def test_expired_future_invalid_dates_rejected(self):
        for transform in [lambda s: s + 'Valid-Until: Wed, 11 Nov 2026 10:00:00 UTC\n',
                          lambda s: s.replace('09:00:00 UTC', '12:00:11 UTC'),
                          lambda s: s.replace('Wed, 11 Nov 2026 09:00:00 UTC', 'not a date')]:
            runner = Commands(transform=transform)
            with self.assertRaisesRegex(apt.PreparationError, 'FRESHNESS_FAILED'):
                self.prepare(runner)
            self.assertEqual(len(runner.calls), 2)

    def test_immutable_base_has_no_invented_expiry(self):
        text = release('noble', 'noble').replace('Wed, 11 Nov 2026 09:00:00 UTC', 'Thu, 25 Apr 2024 09:00:00 UTC')
        apt.validate_release(text, 'noble', 'noble', 'amd64', NOW)

    def test_duplicate_metadata_and_invalid_redirect_rejected(self):
        runner = Commands(transform=lambda text: text + 'Suite: noble\n')
        with self.assertRaisesRegex(apt.PreparationError, 'METADATA_FORMAT'):
            self.prepare(runner)
        for final in ('http://archive.ubuntu.com/ubuntu/dists/noble/InRelease',
                      'https://unlisted.invalid/ubuntu/dists/noble/InRelease'):
            runner = Commands()
            def redirected(cmd, **kwargs):
                result = runner(cmd, **kwargs)
                if cmd[0] == 'curl':
                    result.stdout = final
                return result
            with self.assertRaisesRegex(apt.PreparationError, 'REDIRECT_REFUSED'):
                apt.prepare('ID=ubuntu\nVERSION_CODENAME=noble', sources('noble'), ORIGINAL, 'amd64',
                            apt.KEYRING, run=redirected, now=NOW)

    def test_no_verified_candidates_fail(self):
        runner = Commands(failures={c: 6 for c in apt.CANDIDATES})
        with self.assertRaisesRegex(apt.PreparationError, 'NO_VERIFIED_MIRROR'):
            self.prepare(runner)
        self.assertEqual(len(runner.calls), 2)

    def test_unknown_layout_or_trust_override_stops_before_network(self):
        for source in (sources('noble').replace('mirror+file:', 'file:'),
                       sources('noble').replace(str(apt.KEYRING), '/tmp/other.gpg'),
                       sources('noble') + 'Trusted: yes\n',
                       sources('noble') + 'Check-Valid-Until: no\n',
                       sources('noble').replace('noble-security', 'resolute-security')):
            runner = Commands()
            with self.assertRaises(apt.PreparationError):
                self.prepare(runner, source_text=source)
            self.assertEqual(runner.calls, [])
        for original in (ORIGINAL.replace('priority:1', 'priority:0'),
                         ORIGINAL.replace('azure.archive.ubuntu.com', 'unknown.invalid'),
                         ORIGINAL.replace('\tpriority:2', ''), ''):
            runner = Commands()
            with self.assertRaises(apt.PreparationError):
                self.prepare(runner, original=original)
            self.assertEqual(runner.calls, [])

    def test_curl_and_gpgv_security_flags_and_bounds(self):
        runner = Commands()
        self.prepare(runner)
        for cmd, kwargs in runner.calls:
            self.assertNotIn('sudo', cmd)
            self.assertLessEqual(kwargs['timeout'], 20)
            if cmd[0] == 'curl':
                self.assertEqual(cmd[1], '--disable')
                self.assertEqual(cmd[cmd.index('--proto') + 1], '=https')
                self.assertEqual(cmd[cmd.index('--proto-redir') + 1], '=https')
                self.assertEqual(cmd[cmd.index('--max-time') + 1], '15')
                self.assertNotIn('--insecure', cmd)
                self.assertNotIn('--proxy', cmd)
                self.assertNotIn('--resolve', cmd)
            else:
                self.assertEqual(cmd[cmd.index('--keyring') + 1], str(apt.KEYRING))
                self.assertIn('--homedir', cmd)

    def test_failed_preparation_leaves_files_and_backup_untouched(self):
        for runner in (Commands(signature_failure=True), Commands(failures={apt.CANDIDATES[0]: 60}),
                       Commands(transform=lambda s: s.replace('Suite: noble', 'Suite: wrong')),
                       Commands(failures={c: 6 for c in apt.CANDIDATES})):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                mirror = root / 'apt-mirrors.txt'
                trust = root / 'ubuntu.sources'
                mirror.write_text(ORIGINAL)
                trust.write_text(sources('noble'))
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                with self.assertRaises(apt.PreparationError):
                    _, result = self.prepare(runner)
                    with patch.object(apt, 'MIRRORS', mirror):
                        apt.install_mirror_list(ORIGINAL, result)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_install_is_backup_then_local_atomic_replace_only(self):
        with tempfile.TemporaryDirectory() as directory:
            mirror = Path(directory) / 'apt-mirrors.txt'
            mirror.write_text(ORIGINAL)
            selected, replacement = self.prepare(Commands(failures={apt.CANDIDATES[0]: 6}))
            calls = []
            def local(cmd, **kwargs):
                calls.append(cmd)
                self.assertEqual(cmd[:2], ['sudo', '-n'])
                if cmd[2] in ('cp', 'install'):
                    Path(cmd[-1]).write_bytes(Path(cmd[-2]).read_bytes())
                elif cmd[2] == 'mv':
                    Path(cmd[-2]).replace(cmd[-1])
                else:
                    self.fail('unexpected privileged command')
            with patch.object(apt, 'MIRRORS', mirror):
                apt.install_mirror_list(ORIGINAL, replacement, run=local)
                self.assertEqual(mirror.read_text(), selected + '\tpriority:0\n' + ORIGINAL)
                self.assertEqual(mirror.with_name(mirror.name + '.acs-ci-original').read_text(), ORIGINAL)
                with self.assertRaises(apt.PreparationError):
                    apt.install_mirror_list(replacement, replacement, run=local)
            self.assertEqual([c[2] for c in calls], ['cp', 'install', 'mv'])


if __name__ == '__main__':
    unittest.main()
