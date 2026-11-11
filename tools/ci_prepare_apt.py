#!/usr/bin/env python3
"""Prefer a verified Ubuntu mirror on GitHub's known mirror-list runner layout.

No package/trust/pinning/validity settings are changed. Only mirror-specific
DNS, connection, or timeout failures permit the second candidate. Network and
signature checks run unprivileged; sudo is used solely for local backup/install.
APT still performs its normal signature, freshness and package-hash checks.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

MIRRORS = Path('/etc/apt/apt-mirrors.txt')
SOURCES = Path('/etc/apt/sources.list.d/ubuntu.sources')
KEYRING = Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')
CANDIDATES = ('https://archive.ubuntu.com/ubuntu/', 'https://mirrors.kernel.org/ubuntu/')
NETWORK_FAILURES = {6, 7, 28}  # curl: host DNS, connect, timeout; NOT proxy DNS/TLS/HTTP.
MAX_BYTES = 2 * 1024 * 1024


class PreparationError(RuntimeError):
    pass


class MirrorUnavailable(PreparationError):
    pass


def fields(text: str) -> dict[str, str]:
    """Parse one Deb822 paragraph; duplicate fields are never accepted."""
    result = {}
    key = None
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        if line[0].isspace() and key:
            result[key] += ' ' + line.strip()
            continue
        name, separator, value = line.partition(':')
        if not separator or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*', name) or name in result:
            raise PreparationError('APT_METADATA_FORMAT')
        key = name
        result[key] = value.strip()
    return result


def inspect_layout(os_release: str, sources: str, mirrors: str, architecture: str) -> tuple[str, tuple[str, ...]]:
    os_fields = {}
    for line in os_release.splitlines():
        key, sep, value = line.partition('=')
        if sep:
            os_fields[key] = value.strip().strip('"')
    codename = os_fields.get('VERSION_CODENAME', '')
    if os_fields.get('ID') != 'ubuntu' or not re.fullmatch(r'[a-z]+', codename):
        raise PreparationError('APT_UNSUPPORTED_OS')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', architecture):
        raise PreparationError('APT_UNSUPPORTED_ARCHITECTURE')
    suites = tuple(codename + suffix for suffix in ('', '-updates', '-backports', '-security'))
    found = []
    allowed = {'Types', 'URIs', 'Suites', 'Components', 'Signed-By', 'Architectures'}
    for paragraph in re.split(r'\n\s*\n', sources.strip()):
        source = fields(paragraph)
        if not source:
            continue
        if (set(source) - allowed or source.get('Types') != 'deb'
                or source.get('URIs') != 'mirror+file:' + str(MIRRORS)
                or source.get('Signed-By') != str(KEYRING)
                or set(source.get('Components', '').split()) != {'main', 'restricted', 'universe', 'multiverse'}
                or ('Architectures' in source and architecture not in source['Architectures'].split())):
            raise PreparationError('APT_UNSUPPORTED_SOURCE_LAYOUT')
        found.extend(source.get('Suites', '').split())
    if sorted(found) != sorted(suites):
        raise PreparationError('APT_UNSUPPORTED_SUITES')
    known = {'http://azure.archive.ubuntu.com/ubuntu/',
             'https://archive.ubuntu.com/ubuntu/', 'https://security.ubuntu.com/ubuntu/'}
    seen = set()
    for line in mirrors.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split('\t')
        uri = parts[0].strip().rstrip('/') + '/'
        if (uri not in known or uri in seen or len(parts) != 2
                or not re.fullmatch(r'priority:[1-9][0-9]*', parts[1].strip())):
            raise PreparationError('APT_UNSUPPORTED_MIRROR_LAYOUT')
        seen.add(uri)
    if seen != known:
        raise PreparationError('APT_UNSUPPORTED_MIRROR_LAYOUT')
    return codename, suites


def validate_release(text: str, suite: str, codename: str, architecture: str, now: datetime) -> None:
    release = fields(text)
    if (release.get('Origin') != 'Ubuntu' or release.get('Label') != 'Ubuntu'
            or release.get('Suite') != suite or release.get('Codename') != codename
            or architecture not in release.get('Architectures', '').split()
            or not {'main', 'restricted', 'universe', 'multiverse'}.issubset(release.get('Components', '').split())
            or not release.get('SHA256')):
        raise PreparationError('APT_RELEASE_IDENTITY_MISMATCH')
    try:
        issued = parsedate_to_datetime(release['Date'])
        expires = parsedate_to_datetime(release['Valid-Until']) if 'Valid-Until' in release else None
        if issued.tzinfo is None or (expires is not None and expires.tzinfo is None):
            raise ValueError('timezone missing')
        # Match APT's default future-date tolerance; do not invent expiry where
        # Ubuntu omits Valid-Until (notably the immutable base release).
        if issued > now + timedelta(seconds=10) or (expires is not None and (expires <= now or expires < issued)):
            raise ValueError('invalid validity interval')
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise PreparationError('APT_RELEASE_FRESHNESS_FAILED') from exc


def verify_candidate(candidate: str, suites: tuple[str, ...], codename: str, architecture: str,
                     keyring: Path, *, run=subprocess.run, now=None) -> None:
    now = now or datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix='acs-apt-verify-') as directory:
        temp = Path(directory)
        for suite in suites:
            signed, verified = temp / 'InRelease', temp / 'Release'
            signed.unlink(missing_ok=True)
            verified.unlink(missing_ok=True)
            url = candidate + 'dists/' + suite + '/InRelease'
            cmd = ['curl', '--disable', '--silent', '--show-error', '--fail', '--location',
                   '--proto', '=https', '--proto-redir', '=https', '--max-redirs', '2',
                   '--connect-timeout', '5', '--max-time', '15', '--max-filesize', str(MAX_BYTES),
                   '--output', str(signed), '--write-out', '%{url_effective}', url]
            result = run(cmd, capture_output=True, text=True, timeout=20, check=False)
            if result.returncode in NETWORK_FAILURES:
                raise MirrorUnavailable('APT_MIRROR_NETWORK_UNAVAILABLE')
            if result.returncode:
                # Never echo curl stderr: inherited proxy details may be sensitive.
                raise PreparationError('APT_MIRROR_HTTPS_FAILED')
            final = urlsplit(result.stdout.strip())
            hosts = {'archive.ubuntu.com'} if candidate == CANDIDATES[0] else {'mirrors.kernel.org', 'mirrors.edge.kernel.org'}
            if (final.scheme != 'https' or final.hostname not in hosts or final.port not in (None, 443)
                    or final.username or final.password or final.query or final.fragment
                    or final.path != '/ubuntu/dists/' + suite + '/InRelease'):
                raise PreparationError('APT_MIRROR_REDIRECT_REFUSED')
            if not signed.is_file() or not 0 < signed.stat().st_size <= MAX_BYTES:
                raise PreparationError('APT_RELEASE_SIZE_FAILED')
            # Isolated homedir prevents any user keyring from extending trust.
            result = run(['gpgv', '--homedir', directory, '--keyring', str(keyring),
                          '--output', str(verified), str(signed)],
                         capture_output=True, text=True, timeout=10, check=False)
            if result.returncode or not verified.is_file():
                raise PreparationError('APT_RELEASE_SIGNATURE_FAILED')
            if not 0 < verified.stat().st_size <= MAX_BYTES:
                raise PreparationError('APT_RELEASE_SIZE_FAILED')
            validate_release(verified.read_text(encoding='utf-8'), suite, codename, architecture, now)


def prepare(os_release: str, sources: str, original: str, architecture: str, keyring: Path,
            *, run=subprocess.run, now=None) -> tuple[str, str]:
    codename, suites = inspect_layout(os_release, sources, original, architecture)
    for candidate in CANDIDATES:
        try:
            verify_candidate(candidate, suites, codename, architecture, keyring, run=run, now=now)
        except MirrorUnavailable:
            continue
        # APT randomizes equal priorities. A unique priority:0 is lower than all
        # preserved runner fallbacks; prepending an unprioritized URI is not enough.
        fallbacks = ''.join(line for line in original.splitlines(keepends=True)
                            if line.split('\t', 1)[0].strip().rstrip('/') + '/' != candidate)
        return candidate, candidate + '\tpriority:0\n' + fallbacks
    raise PreparationError('APT_NO_VERIFIED_MIRROR')


def install_mirror_list(original: str, replacement: str, *, run=subprocess.run) -> None:
    backup = MIRRORS.with_name(MIRRORS.name + '.acs-ci-original')
    staged = MIRRORS.with_name(MIRRORS.name + '.acs-ci-new')
    if (MIRRORS.is_symlink() or backup.exists() or backup.is_symlink()
            or staged.exists() or staged.is_symlink() or MIRRORS.read_text() != original):
        raise PreparationError('APT_MIRROR_CHANGED_OR_BACKUP_EXISTS')
    with tempfile.TemporaryDirectory(prefix='acs-apt-install-') as directory:
        prepared = Path(directory) / 'apt-mirrors.txt'
        prepared.write_text(replacement, encoding='utf-8')
        # Only local filesystem utilities run as root. Backup precedes an atomic
        # rename; all source files, trust files and apt configuration stay intact.
        for cmd in (
            ['sudo', '-n', 'cp', '--preserve=all', '--', str(MIRRORS), str(backup)],
            ['sudo', '-n', 'install', '-m', '0644', '--', str(prepared), str(staged)],
            ['sudo', '-n', 'mv', '-T', '--', str(staged), str(MIRRORS)],
        ):
            run(cmd, capture_output=True, text=True, timeout=10, check=True)


def main() -> int:
    try:
        if os.environ.get('GITHUB_ACTIONS') != 'true' or os.geteuid() == 0:
            raise PreparationError('APT_REQUIRES_UNPRIVILEGED_GITHUB_RUNNER')
        for path in (MIRRORS, SOURCES, KEYRING):
            if path.is_symlink() or not path.is_file():
                raise PreparationError('APT_UNSUPPORTED_SOURCE_LAYOUT')
        sources, original = SOURCES.read_text(), MIRRORS.read_text()
        architecture = subprocess.run(['dpkg', '--print-architecture'], capture_output=True,
                                      text=True, timeout=5, check=True).stdout.strip()
        selected, replacement = prepare(Path('/etc/os-release').read_text(), sources, original,
                                        architecture, KEYRING)
        if SOURCES.read_text() != sources:
            raise PreparationError('APT_SOURCES_CHANGED')
        install_mirror_list(original, replacement)
        print('Verified Ubuntu mirror selected: ' + selected)
        return 0
    except PreparationError as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        print('APT_PREPARATION_FAILED', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
