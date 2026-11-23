"""Reproduce baseline guard mutations on an archived copy, never on the supplied checkout.
Usage: python3 docs/audit/2026-09-26/audit_guard_mutations.py CHECKOUT SCRATCH_OUTPUT
Requires the audit virtualenv beside CHECKOUT and its installed node_modules.
This deliberately pins adec616: it is a dated baseline measurement.
"""
import pathlib,subprocess,os,json,shutil,tarfile,io,sys
source=pathlib.Path(sys.argv[1]).resolve(); base=pathlib.Path(sys.argv[2]).resolve(); base.mkdir(parents=True,exist_ok=True); root=base/'audit-gate-copy'; root.mkdir(parents=True,exist_ok=True)
data=subprocess.check_output(['git','archive','adec616'],cwd=source)
with tarfile.open(fileobj=io.BytesIO(data)) as t:t.extractall(root,filter='data')
if not (root/'node_modules').exists():(root/'node_modules').symlink_to(source/'node_modules',target_is_directory=True)
env=dict(os.environ,ACS_ENV='test',PYTHONPATH=str(root),TMPDIR=str(base/'audit-evidence/tmp-gates'));pathlib.Path(env['TMPDIR']).mkdir(parents=True,exist_ok=True);env['PATH']=str(source.parent/'acs-venv/bin')+':'+env['PATH']
out=base/'audit-evidence/gates';out.mkdir(parents=True,exist_ok=True);rows=[]
def check(name,cmd,rel,transform):
 p=root/rel; original=p.read_text(); changed=transform(original); assert changed!=original
 codes=[]
 for stage in ['sound','broken','restored']:
  p.write_text(changed if stage=='broken' else original)
  q=subprocess.run(cmd,cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
  (out/(name+'-'+stage+'.log')).write_text(q.stdout);codes.append(q.returncode)
 assert codes[0]==0 and codes[1]!=0 and codes[2]==0,(name,codes)
 rows.append(dict(guard=name,command=' '.join(cmd),mutated=rel,return_codes=codes));print(name,codes,flush=True)
check('integration',['python3','tools/check_integration.py'],'acs_pbr.json',lambda s:s.replace('"viewport_contract_version": "viewport-safety/1.0.0"','"viewport_contract_version": "audit-broken"'))
check('index',['python3','tools/check_index_guard.py','public/index.html'],'public/index.html',lambda s:s.replace('</body>','<script>window.auditMutation=true;</script></body>'))
check('api-origin',['python3','tools/check_api_base.py'],'public/app/boot/api-base.js',lambda s:s.replace('https://acs-engine.onrender.com','https://audit-invalid.example'))
check('csp-hash',['python3','tools/check_csp_hash.py'],'public/index.html',lambda s:s.replace('<script type="importmap">','<script type="importmap"> '))
check('module-graph',['node','tests/remediation/test_module_graph.js'],'public/app/main.js',lambda s:s+"\nimport './generated/workspace-ui.js';\n")
check('deploy',['python3','tests/deploy/verify_deploy.py'],'public/index.html',lambda s:s.replace('</body>','<script>window.auditMutation=true;</script></body>'))
subprocess.run(['python3','tools/bundle_report.py'],cwd=root,env=env,stdout=subprocess.DEVNULL,check=True)
check('doc-state',['python3','-c','import sys;sys.path.insert(0,"tools");import check_doc_claims as c;ok,msg=c.check_state();print(msg);sys.exit(0 if ok else 1)'],'KNOWN-ISSUES.md',lambda s:s.replace('2,131,718 B','2,131,719 B'))
check('extractor',['node','tests/phase3/lib/extract_browser_bundle.js'],'public/app/shared-state.js',lambda s:s+'\nconst AUDIT_BROKEN = ;\n')
(out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
