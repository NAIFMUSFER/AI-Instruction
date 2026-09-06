"""Run every repository test entry independently; never stop on the first failure.

Diagnostic harness only, outside the audited source tree. Per-file output is kept
verbatim. Exit 2 and infrastructure failures are not turned into passes.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

root, out = map(lambda x: Path(x).resolve(), sys.argv[1:3])
out.mkdir(parents=True, exist_ok=True)
env = dict(os.environ)
env['PATH'] = str(Path(sys.executable).parent) + ':' + env['PATH']
commands = {}
for script in sorted((root/'tests').glob('**/run_all.sh')):
    for line in script.read_text().splitlines():
        s = line.strip()
        if s.startswith('#'): continue
        s = s.replace('$HERE', str(script.parent)).replace('$ROOT', str(root))
        m = re.match(r'(python3|node)\s+"?([^";\s]+)"?(?:\s+"?([^";\s]+)"?)?', s)
        if not m: continue
        args = [m[1], m[2]]
        if m[3] and 'test_' in m[3]: args.append(m[3])
        target = args[-1]
        if Path(target).name.startswith('test_') and Path(target).is_file():
            rel = str(Path(target).relative_to(root))
            if 'run_browser.js' not in args[1]: commands.setdefault(rel, args)

tests = sorted(p for p in (root/'tests').rglob('test_*')
               if p.is_file() and p.suffix in ('.py', '.js'))
results = []
for p in tests:
    rel = str(p.relative_to(root))
    cmd = commands.get(rel)
    if cmd is None:
        if p.suffix == '.py': cmd = ['python3', str(p)]
        elif p.parent.name in ('phase1', 'phase2'):
            cmd = ['node', str(root/'tests/lib/run.js'), str(p)]
        else:
            text = p.read_text()
            direct = ('require(' in text and ('playwright' in text or 'assert' in text)) or 'parity' in p.name
            cmd = ['node', str(p)] if direct else ['node', str(root/'tests/lib/run.js'), str(p)]
    log = out/(rel.replace('/', '__')+'.log')
    started = time.monotonic()
    with log.open('w') as f:
        try:
            run = subprocess.run(cmd, cwd=root, env=env, stdout=f,
                                 stderr=subprocess.STDOUT, timeout=360)
            rc = run.returncode
        except subprocess.TimeoutExpired:
            f.write('\nAUDIT_HARNESS_TIMEOUT: exceeded 360 seconds\n'); rc = 124
    txt = log.read_text(errors='replace')
    infrastructure = any(x in txt for x in (
        "Executable doesn't exist", 'CHROMIUM UNAVAILABLE',
        'browserType.launch: Executable', 'CHROMIUM ENVIRONMENT UNAVAILABLE'))
    # Final summary counts are evidence; do not sum individual check output again.
    summaries = [l for l in txt.splitlines() if re.search(r'\d+\s*(?:passed|PASS|checks|assertions|failed|FAIL)', l, re.I)]
    reported_failure = any(int(n) > 0 for line in summaries
                           for n in re.findall(r'\b(\d+)\s+failed\b', line, re.I))
    rec = dict(path=rel, command=cmd, exit_code=rc,
               seconds=round(time.monotonic()-started,3),
               reported_failure=reported_failure,
               status=('NOT_VERIFIED' if infrastructure or rc==2 else 'PASS' if rc==0 and not reported_failure else 'FAIL'),
               log=str(log), summary=summaries[-4:])
    results.append(rec)
    (out/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    print(rec['status'], rel, 'exit',rc, 'seconds',rec['seconds'], flush=True)
counts = {x:sum(r['status']==x for r in results) for x in ('PASS','FAIL','NOT_VERIFIED')}
(out/'summary.json').write_text(json.dumps({'counts_test_files':counts, 'tests':len(results)},indent=2)+'\n')
print(json.dumps(counts), flush=True)
