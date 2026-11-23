"""Fail-closed release evidence aggregation; process status is authoritative."""
import json
from pathlib import Path
import re
import sys

SCHEMA = 'acs-production-verification/1.0.0'
PARTS = [('verify_live.json', {'A', 'B', 'G'}),
         ('verify_live_browser.json', {'C', 'D', 'E', 'F', 'G(browser)'})]


def inspect(path, process_exit, required):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema') != SCHEMA:
            raise ValueError('EVIDENCE_SCHEMA_INVALID')
        if not isinstance(data.get('frontend'), str) or not re.match(r'^https?://', data['frontend']):
            raise ValueError('EVIDENCE_TARGET_MISSING')
        if type(data.get('exit_code')) is not int or data['exit_code'] != process_exit:
            raise ValueError('EVIDENCE_PROCESS_EXIT_MISMATCH')
        checks = data.get('checks')
        if not isinstance(checks, list) or not checks:
            raise ValueError('EVIDENCE_CHECKS_MISSING')
        counts = {'pass': 0, 'fail': 0, 'not_verified': 0, 'total': len(checks)}
        for check in checks:
            if not isinstance(check, dict) or check.get('status') not in ('PASS', 'FAIL', 'NOT VERIFIED'):
                raise ValueError('EVIDENCE_CHECK_INVALID')
            counts[{'PASS': 'pass', 'FAIL': 'fail', 'NOT VERIFIED': 'not_verified'}[check['status']]] += 1
        if data.get('counts') != counts:
            raise ValueError('EVIDENCE_COUNTS_MISMATCH')
        declared = set(data.get('groups') or [])
        present = {str(row.get('group')) for row in checks}
        # Browser provenance rows use G, while the declaration scopes it as G(browser).
        present |= {'G(browser)'} if 'G' in present else set()
        if not required <= declared or not required <= present:
            raise ValueError('EVIDENCE_REQUIRED_GROUP_MISSING')
        if process_exit not in (0, 1, 2):
            raise ValueError('EVIDENCE_PROCESS_CRASH')
        verdict = 'FAIL' if process_exit == 1 or counts['fail'] else 'INCOMPLETE' if process_exit == 2 or counts['not_verified'] else 'PASS'
        if verdict == 'PASS':
            observed = data.get('observed') or {}
            frontend_sha = observed.get('frontend_sha') or (observed.get('build_info') or {}).get('git_sha')
            shas = [frontend_sha] + ([observed.get('backend_sha')] if 'A' in required else [])
            if not all(isinstance(sha, str) and re.fullmatch(r'[a-f0-9]{40}', sha) for sha in shas):
                raise ValueError('EVIDENCE_PROVENANCE_MISSING')
            expected = data.get('expect_sha')
            if expected and any(sha != expected for sha in shas):
                raise ValueError('EVIDENCE_PROVENANCE_MISMATCH')
        if verdict == 'PASS' and data.get('verdict') != 'PASS':
            raise ValueError('EVIDENCE_VERDICT_MISMATCH')
        return {'verdict': verdict, 'process_exit': process_exit, 'counts': counts,
                'frontend': data['frontend'], 'expect_sha': data.get('expect_sha'),
                'observed': data.get('observed')}, 1 if verdict == 'FAIL' else 2 if verdict == 'INCOMPLETE' else 0
    except (OSError, ValueError, TypeError) as exc:
        # Do not echo arbitrary summary content or a child exception payload.
        return {'verdict': 'FAIL', 'process_exit': process_exit,
                'error': str(exc) if isinstance(exc, ValueError) and str(exc).startswith('EVIDENCE_') else 'EVIDENCE_MISSING_OR_MALFORMED'}, 1


def main(argv):
    out, stamp, http_exit, browser_exit = argv
    combined = {'schema': 'acs-production-verification-suite/2.0.0', 'started_at': stamp,
                'parts': {}, 'counts': {'pass': 0, 'fail': 0, 'not_verified': 0, 'total': 0}}
    results = []
    for (name, groups), rc in zip(PARTS, (int(http_exit), int(browser_exit))):
        part, code = inspect(Path(out)/name, rc, groups)
        results.append(code); combined['parts'][name] = part
        for key, value in (part.get('counts') or {}).items():combined['counts'][key] += value
    code = 1 if 1 in results else 2 if 2 in results else 0
    combined['verdict'] = {0: 'PASS', 1: 'FAIL', 2: 'INCOMPLETE'}[code]
    combined['exit_code'] = code
    (Path(out)/'summary.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PRODUCTION VERIFICATION: '+combined['verdict'])
    print(json.dumps(combined['parts'], ensure_ascii=False))
    return code


if __name__ == '__main__':sys.exit(main(sys.argv[1:]))
