import os, sys, subprocess, pathlib, json, time, re, shlex, glob
root=pathlib.Path(sys.argv[1]).resolve(); out=pathlib.Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,ACS_ENV='test',PYTHONPATH=str(root)); env['PATH']=str(root.parent/'acs-venv/bin')+':'+env['PATH']
results=[]
def run(name,cmd,timeout=180):
    start=time.monotonic(); log=out/(re.sub(r'[^a-zA-Z0-9_-]','_',name)+'.log')
    with log.open('w') as f:
        p=subprocess.Popen(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        try: rc=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124; f.write('\nAUDIT HARNESS: timeout after %s seconds\n'%timeout)
    item=dict(name=name,command=shlex.join(cmd),rc=rc,seconds=round(time.monotonic()-start,3),log=str(log)); results.append(item)
    (out/'results.json').write_text(json.dumps(results,indent=2)); print(name,rc,flush=True)
for name,cmd in [
 ('02-integration',['python3','tools/check_integration.py']),
 ('03-index',['python3','tools/check_index_guard.py','public/index.html']),
 ('04-api',['python3','tools/check_api_base.py']),
 ('05-csp',['python3','tools/check_csp_hash.py']),
 ('06-deploy',['python3','tests/deploy/verify_deploy.py']),
 ('07-ci-exact',['bash','tools/ci_run.sh']),
 ('08-bundle',['python3','tools/bundle_report.py'])]:run(name,cmd)
if len(sys.argv)>3 and sys.argv[3]=='exact': sys.exit(0)
# Derive runner declarations from checked-in workflow command blocks.
runners={}
for path in (root/'.github/workflows').glob('*.y*ml'):
    text=path.read_text().replace('\\\n',' ')
    for line in text.splitlines():
        if 'ci_run.sh' not in line or '--runner' not in line: continue
        try: parts=shlex.split(line)
        except ValueError:continue
        i=parts.index('--runner'); runner=shlex.split(parts[i+1])
        for arg in parts[i+2:]:
            if arg.startswith('tests/'):
                for match in glob.glob(str(root/arg)): runners[str(pathlib.Path(match).relative_to(root))]=runner
for path in (root/'tests').glob('**/run_all.sh'):
    text=path.read_text().replace('$ROOT/', '').replace('$HERE/',str(path.parent.relative_to(root))+'/').replace('"','')
    for m in re.finditer(r'node (tests/(?:phase3/lib/)?(?:lib/)?run\.js) (tests/[^ ;\n]+\.js)',text): runners[m[2]]=['node',m[1]]
targets=sorted(p for p in (root/'tests').rglob('test*') if p.is_file() and p.suffix in ('.py','.js','.mjs','.cjs'))
for p in targets:
    rel=str(p.relative_to(root)); runner=runners.get(rel)
    if runner is None:
        if p.suffix=='.py': runner=['python3']
        elif re.match(r'tests/phase[23]/',rel) and p.name not in ['test_parity.js']: runner=['node','tests/lib/run.js']
        else:runner=['node']
    run(rel,['bash','tools/ci_run.sh','--label','audit-baseline','--runner',shlex.join(runner),rel],120)
run('09-doc-claims',['python3','tools/check_doc_claims.py'],300)
print('DONE',len(results),'failed',sum(r['rc']!=0 for r in results),flush=True)
