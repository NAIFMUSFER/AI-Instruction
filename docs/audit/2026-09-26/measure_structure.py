import ast,json,sys,collections,re,posixpath,subprocess
from pathlib import Path
# Read-only documentation evidence; deliberately not installed as a build gate.
# Static imports plus explicitly named late/global edges are not whole-program
# analysis. See STRUCTURE-PROPOSAL.md before interpreting the proposed DAG.
arguments = [arg for arg in sys.argv[1:] if arg != '--verify']
R=Path(arguments[0]) if arguments else Path(__file__).resolve().parents[3]
B={
'shared_kernel':['acs_api_errors','acs_workspace_progress','acs_opening_identity','acs_project'],
'platform':['acs_auth','acs_auth_gateway','acs_rate_limit','acs_cpu_pool','acs_upload_security','acs_logging','acs_build_info','acs_async_jobs'],
'source_evidence':['acs_rules','acs_ingest','acs_occupancy','acs_design_research'],
'revision_identity':['acs_revision'],
'geometry':['acs_arch','acs_struct','acs_mep','acs_fls','acs_relations','acs_navigation','acs_distance','acs_egress'],
'coordination':['acs_coord'],
'validation':['acs_validate','acs_residential_access'],
'authoring':['acs_authoring','acs_workspace'],
'engineering_changes':['acs_engineering_authority','acs_layout','acs_engineering_approval'],
'plan_revision':['acs_plan_review','acs_plan_scorecard','acs_plan_semantic_locks','acs_plan_semantic_diff','acs_plan_options','acs_plan_lock_binding','acs_plan_store','acs_plan_store_port','acs_plan_store_reload','acs_supabase_plan_store','warehouse_vertical_stage_gate'],
'understanding':['acs_understand','acs_generation','acs_plan_chunks','acs_programs','acs_provider','acs_provider_budget','acs_generation_job','acs_residential_generation','acs_residential_layout','acs_residential_manifest'],
'connected_workspace':['acs_plan_bridge','acs_plan_commands','acs_plan_persisted_commands','acs_plan_chat_job','acs_plan_chat_orchestration','acs_plan_http','acs_plan_session','acs_workspace_http','acs_workspace_service','acs_plan_sources','acs_plan_overlap_repair','acs_plan_projection','warehouse_program_feasibility','warehouse_soft_area_fit'],
'bim_exchange':['acs_bim'],
'documentation':['acs_docs'],
'presentation':['acs_compiler','acs_visual','acs_render','acs_pbr','acs_archdetail'],
'walkthrough':['acs_runtime'],
'composition':['acs_understand_api']}
F={
'platform':['boot/a11y-baseline.js','boot/api-base.js','boot/build-info.js','boot/debug-toggle.js','boot/engine-guard.js','boot/style-bridge.js'],
'shared_kernel':['shared-state.js','late-bindings.js','trust/core.js'],
'composition':['main.js','importmap.sha256','styles/app.css','ui/panels-entry.js','ui/workspace-viewport-selection-runtime.js','ui/residential-quality.js','ui/generation-jobs.js'],
'connected_workspace':['core/brief-program.mjs','core/plan-review-packet.mjs','core/residential-program.mjs','ui/approved-viewer.mjs','ui/brief-review.mjs','ui/connected-semantic-locks.mjs','ui/connected-workspace.mjs','ui/plan-upload.mjs','ui/residential-options.mjs','styles/connected-workspace.css'],
'model_workbench':['core/viewer.js','core/standards.js','core/disciplines.js','generated/pbr.js','generated/pbr-bridge.js','render/scene.js','render/warehouse-canonical-identity.js','ui/workspace-ui-wiring.js','trust/wiring.js','ui/workspace-viewport-selection.js','generated/authoring.js'],
'walkthrough':['generated/runtime.js'],
'workspace_inspector':['generated/workspace-ui.js'],
'bim_exchange':['generated/bim.js'],
'documentation':['generated/docs.js'],
'presentation':['generated/render-engine.js','generated/arch-detail.js','generated/arch-detail-bridge.js']}

def scc(G):
 index={};low={};stack=[];on=set();cs=[]
 def visit(v):
  index[v]=low[v]=len(index);stack.append(v);on.add(v)
  for w in sorted(G.get(v,())):
   if w not in index:visit(w);low[v]=min(low[v],low[w])
   elif w in on:low[v]=min(low[v],index[w])
  if low[v]==index[v]:
   c=[]
   while True:
    w=stack.pop();on.remove(w);c.append(w)
    if w==v:break
   cs.append(sorted(c))
 for v in sorted(G):
  if v not in index:visit(v)
 return sorted(c for c in cs if len(c)>1)

def grouped(G, groups):
 who={v:k for k,vs in groups.items() for v in vs};out={k:set() for k in groups}
 for a,ds in G.items():
  for b in ds:
   if who[a]!=who[b]:out[who[a]].add(who[b])
 return out
mods={p.stem:p for p in R.glob('*.py')};G={m:set() for m in mods}
for m,p in mods.items():
 for n in ast.walk(ast.parse(p.read_text())):
  if isinstance(n,ast.Import):G[m].update(a.name for a in n.names if a.name in mods)
  elif isinstance(n,ast.ImportFrom) and n.module in mods:G[m].add(n.module)
BG=grouped(G,B)
files={str(p.relative_to(R/'public/app')):p for p in (R/'public/app').rglob('*') if p.is_file()}
FG={f:set() for f in files}; pub={};reads={}
# Exact line form of imports emitted by the existing generator, no matching exports with expressions.
for f,p in files.items():
 if p.suffix not in ('.js','.mjs'):continue
 s=p.read_text()
 for m in re.finditer(r'^import\s+(?:[^\n]*?\s+from\s+)?[\'\"]([^\'\"\n]+)[\'\"]\s*;',s,re.M):
  spec=m[1]
  if spec.startswith('.'):
   dest=posixpath.normpath(posixpath.join(posixpath.dirname(f),spec))
   if dest in files:FG[f].add(dest)
 for m in re.finditer(r'Object\.assign\(__ACS_LATE,\s*\{([^}]+)\}',s):
  for n in m[1].split(','):pub[n.strip()]=f
 reads[f]=set(re.findall(r'__ACS_LATE\.([A-Za-z_$][\w$]*)',s))
static=scc(FG)
for f,p in files.items():
 if p.suffix not in ('.js','.mjs'):continue
 for spec in re.findall(r"import\(\s*['\"]([^'\"]+)['\"]\s*\)",p.read_text()):
  dest=posixpath.normpath(posixpath.join(posixpath.dirname(f),spec))
  if dest in files:FG[f].add(dest)
for f,names in reads.items():
 for n in names:
  if n in pub:FG[f].add(pub[n])
# Confirmed call-time namespace edge: wiring calls ACS.trust.modelReviewSummary;
# implementation lives in trust/core and is published by trust/wiring. Resolve to implementation.
FG['ui/workspace-ui-wiring.js'].add('trust/core.js')
FG['ui/residential-quality.js'].update(['ui/panels-entry.js','generated/arch-detail.js','generated/arch-detail-bridge.js','generated/pbr.js','generated/pbr-bridge.js','ui/workspace-ui-wiring.js'])
FG['ui/generation-jobs.js'].add('ui/residential-quality.js')
# Exclude composition-root edges from dependency direction among reusable features.
# The selection runtime imports only the lazy-loading entry point. This coupling
# requires moving loader into model_workbench, not pretending composition is a leaf.
FFG=grouped(FG,F)
def git(*args):
 return subprocess.check_output(['git', '-C', str(R), *args],text=True).strip()
scoped=set(git('ls-files','acs_*.py','public/app/*').splitlines())
counts=collections.Counter(); pairs=collections.Counter(); changed=0
for block in git('log','adec616','-80','--format=COMMIT:%H','--name-only','--no-merges').split('COMMIT:')[1:]:
 touched=sorted(set(block.splitlines()[1:])&scoped)
 if touched:
  changed+=1;counts.update(touched)
  import itertools
  pairs.update(itertools.combinations(touched,2))
history={'sample_command':'git log adec616 -80 --format=COMMIT:%H --name-only --no-merges',
         'commits_with_scoped_changes':changed,'frequently_changed':counts.most_common(12),
         'frequent_pairs':pairs.most_common(12)}
who_b={m:f for f,ms in B.items() for m in ms}
controllers={'acs_auth_gateway','acs_plan_http','acs_workspace_http','acs_plan_commands',
             'acs_plan_persisted_commands','acs_engineering_approval'}
models={'acs_plan_review','acs_plan_lock_binding','acs_plan_store_port'}
move_map={}
for m in sorted(mods):
 feature=who_b[m]
 if feature=='shared_kernel':target='acs/shared_kernel/'+m+'.py'
 elif feature=='composition':target='acs/application/controllers/'+m+'.py'
 else:
  role='controllers' if m in controllers else 'models' if m in models else 'services'
  target='acs/features/'+feature+'/'+role+'/'+m+'.py'
 move_map[m+'.py']=target
for p in sorted(R.glob('acs_*.json')):
 feature=who_b.get(p.stem)
 if p.stem=='acs_sources':feature='source_evidence'
 if p.stem=='acs_engineering_changes':feature='engineering_changes'
 if not feature:raise ValueError('Unclassified schema '+p.name)
 move_map[p.name]='acs/features/'+feature+'/models/'+p.name
who_f={m:f for f,ms in F.items() for m in ms}
for f in sorted(files):
 feature=who_f[f];name=Path(f).name
 if f in ('main.js','importmap.sha256','styles/app.css') or f.startswith('boot/'):
  target='public/app/'+f
 elif feature=='composition':target='public/app/application/controllers/'+name
 elif feature=='shared_kernel':
  target='public/app/shared/'+f.replace('trust/core.js','trust-core.js')
 else:
  if f.startswith('generated/'):
   role='controllers' if ('-bridge.js' in f or feature=='workspace_inspector') else 'services'
   rest=role+'/generated/'+name
  elif f.startswith('core/') and feature=='connected_workspace':rest='models/'+name
  elif f.startswith('core/'):rest='services/'+name
  elif f.startswith('styles/'):rest='styles/'+name
  elif f.startswith('trust/'):rest='controllers/trust-'+name
  else:rest='controllers/'+name
  target='public/app/features/'+feature+'/'+rest
 move_map['public/app/'+f]=target
# Explicit generator/template locations stay stable; their declared targets and
# package resource readers must change if/when this conditional map is executed.
result = {
    'canonical_json': len(list(R.glob('acs_*.json'))),
    'history': history,
    'move_map': move_map,
    'root_py': len(mods),
    'acs_root_py': len([m for m in mods if m.startswith('acs_')]),
    'frontend_files': len(files),
    'frontend_javascript': len([p for p in files.values() if p.suffix in ('.js', '.mjs')]),
    'backend_module_sccs': scc(G),
    'frontend_static_sccs': static,
    'frontend_with_late_sccs': scc(FG),
    'proposed_backend_sccs': scc(BG),
    'proposed_frontend_sccs': scc(FFG),
    'backend_edges': {k: sorted(v) for k,v in BG.items()},
    'frontend_edges': {k: sorted(v) for k,v in FFG.items()},
    'backend_inventory_missing': sorted(set(mods)-{x for vs in B.values() for x in vs}),
    'frontend_inventory_missing': sorted(set(files)-{x for vs in F.values() for x in vs}),
}
if '--verify' in sys.argv:
    # Documentation checks only. Never mutate repository source to probe a graph.
    expected = ({p.name for p in R.glob('*.py')}
                | {p.name for p in R.glob('acs_*.json')}
                | {'public/app/'+f for f in files})
    assert set(move_map) == expected, 'incomplete move map'
    assert len(set(move_map.values())) == len(expected), 'destination collision'
    report = (R/'STRUCTURE-PROPOSAL.md').read_text()
    rows = dict(re.findall(r'^\| `([^`]+)` \| `([^`]+)` \|$', report, re.M))
    assert all(rows.get(k) == v for k,v in move_map.items()), 'report/map disagreement'
    assert not scc(BG) and not scc(FFG), 'proposed grouping is cyclic'
    broken = {k: set(v) for k,v in BG.items()}
    broken['validation'].add('understanding')
    assert scc(broken), 'backend reverse-edge negative control was not detected'
    broken = {k: set(v) for k,v in FFG.items()}
    broken['model_workbench'].add('presentation')
    assert scc(broken), 'browser reverse-edge negative control was not detected'
    print('PASS: exhaustive source map, unique destinations, exact Markdown agreement.')
    print('PASS: sound proposed import graphs are acyclic.')
    print('PASS: deliberate backend/browser reverse edges are detected in memory.')
else:
    print(json.dumps(result, indent=2))
