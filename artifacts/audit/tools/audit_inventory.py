"""Read-only source/history inventory. Never prints or saves secret values."""
import ast, collections, datetime, hashlib, io, json, math, os, re, subprocess, sys, zipfile
from pathlib import Path

root=Path(sys.argv[1]).resolve(); out=root/'artifacts/audit/evidence'
out.mkdir(parents=True,exist_ok=True)
def git(*args): return subprocess.check_output(['git',*args],cwd=root)
tracked=set(git('ls-files','-z').decode().split('\0'))-{''}
files=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts
       and not str(p.relative_to(root)).startswith('artifacts/audit/')]
texts={}
for p in files:
    if p.stat().st_size<=4_000_000:
        try: texts[str(p.relative_to(root))]=p.read_text()
        except (UnicodeDecodeError, OSError): pass
imports=collections.defaultdict(list); functions=collections.defaultdict(list)
modules={Path(x).stem:x for x in texts if x.endswith('.py') and '/' not in x}
for path,txt in texts.items():
    if path.endswith('.py'):
        try: tree=ast.parse(txt)
        except SyntaxError: continue
        for n in ast.walk(tree):
            names=[]
            if isinstance(n,ast.Import): names=[x.name for x in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module: names=[n.module]
            elif isinstance(n,ast.Call) and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
                if isinstance(n.func,ast.Name) and n.func.id=='__import__' or isinstance(n.func,ast.Attribute) and n.func.attr=='import_module': names=[n.args[0].value]
            for name in names:
                if name.split('.')[0] in modules:
                    imports[modules[name.split('.')[0]]].append({'file':path,'line':n.lineno,'kind':'python_import'})
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                body=[x for x in n.body if not isinstance(x,ast.Expr) or not isinstance(x.value,ast.Constant) or not isinstance(x.value.value,str)]
                sig=hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False).encode()).hexdigest()
                if len(ast.dump(body[0]))>180 if body else False:
                    functions[sig].append({'file':path,'line':n.lineno,'name':n.name})
    if path.endswith(('.js','.mjs','.html')):
        for m in re.finditer(r'(?:from\s*|import\s*\(?|require\s*\()\s*[\'"]([^\'"]+)[\'"]',txt):
            target=m[1]
            if target.startswith('.'):
                resolved=os.path.normpath(str(Path(path).parent/target))
                if resolved in texts: imports[resolved].append({'file':path,'line':txt[:m.start()].count('\n')+1,'kind':'js_import'})
    # Literal asset references, separate from executable imports.
    if path.endswith(('.html','.js','.py','.sh','.toml','.yml','.yaml')):
        for m in re.finditer(r'[\'"](/?(?:app/|assets/|vendor/)?[A-Za-z0-9_./@-]+\.(?:json|css|js|mjs|svg|png))[\'"]',txt):
            ref=m[1]
            opts=[ref.lstrip('/'),'public/'+ref.lstrip('/'),os.path.normpath(str(Path(path).parent/ref))]
            for dst in dict.fromkeys(opts):
                if dst in texts and dst!=path: imports[dst].append({'file':path,'line':txt[:m.start()].count('\n')+1,'kind':'literal_reference'})
last={}
for block in git('log','--format=@@%H %cI','--name-only').decode().split('@@')[1:]:
    rows=block.splitlines(); head=rows[0].split(' ',1)
    for f in rows[1:]:
        if f.strip(): last.setdefault(f,{'commit':head[0],'date':head[1]})
inventory=[]
for p in sorted(files):
    rel=str(p.relative_to(root)); st=p.stat()
    inventory.append({'path':rel,'tracked':rel in tracked,'bytes':st.st_size,
      'filesystem_mtime_utc':datetime.datetime.fromtimestamp(st.st_mtime,datetime.timezone.utc).isoformat(),
      'last_git_change':last.get(rel),'imported_or_referenced_by':imports.get(rel,[]),
      'old_name_candidate':bool(re.search(r'(^|[/_.-])(v[01]|backup|copy|old)([/_.-]|$)',rel,re.I))})
(out/'file-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
(out/'duplicate-python-bodies.json').write_text(json.dumps([v for v in functions.values() if len(v)>1],indent=2)+'\n')
lines=['# File inventory','',
 'All files present at scan time, including untracked files. Git internals are scanned separately.',
 'mtime is the local filesystem time, not an author timestamp. No importer does not prove a file is dead; CLI, tests and generated artifacts have separate entry points.',
 '', '| File | Tracked | Bytes | Last Git change / local mtime | Importers / literal references |', '|---|---|---:|---|---|']
for r in inventory:
    refs='; '.join(f"{x['file']}:{x['line']} ({x['kind']})" for x in r['imported_or_referenced_by']) or 'None found statically'
    date=(r['last_git_change'] or {}).get('date') or r['filesystem_mtime_utc']
    lines.append(f"| {r['path']} | {r['tracked']} | {r['bytes']} | {date} | {refs} |")
(out/'FILE-INVENTORY.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'files':len(inventory),'tracked':sum(r['tracked'] for r in inventory),'untracked':sum(not r['tracked'] for r in inventory),'old_name_candidates':sum(r['old_name_candidate'] for r in inventory),'duplicate_body_groups':sum(len(v)>1 for v in functions.values())}))

# Whole reachable Git object history, plus nested ZIP members. Values never leave memory.
rules={
 'private_key':rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
 'github_token':rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
 'provider_key':rb'\bsk-(?:ant-api\d+-|proj-)?[A-Za-z0-9_-]{24,}',
 'aws_access_key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'google_api_key':rb'\bAIza[0-9A-Za-z_-]{35}',
 'slack_token':rb'\bxox[baprs]-[A-Za-z0-9-]{24,}',
}
findings=[]; scan_errors=[]; zip_count=0
def scan(blob,path,sha,member=None):
    for name,pattern in rules.items():
        for m in re.finditer(pattern,blob):
            token=m[0]
            placeholder=(len(set(token.split(b'-')[-1]))<=4 or b'example' in token.lower() or b'placeholder' in token.lower())
            findings.append({'type':name,'path':path,'zip_member':member,'blob':sha,
              'line':blob[:m.start()].count(b'\n')+1,'synthetic_candidate':placeholder})
objects=git('rev-list','--objects','--all').decode().splitlines()
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
blobs=0; byte_count=0
for entry in objects:
    sha,_,path=entry.partition(' ')
    proc.stdin.write((sha+'\n').encode()); proc.stdin.flush()
    hdr=proc.stdout.readline().decode().split()
    if len(hdr)<3: continue
    size=int(hdr[2]); blob=proc.stdout.read(size); proc.stdout.read(1)
    if hdr[1]!='blob': continue
    blobs+=1; byte_count+=size; scan(blob,path,sha)
    if blob.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                total=0
                for zi in z.infolist():
                    if zi.is_dir(): continue
                    total+=zi.file_size
                    if zi.file_size>25_000_000 or total>250_000_000:
                        scan_errors.append({'path':path,'member':zi.filename,'reason':'bounded archive scan limit'}); continue
                    scan(z.read(zi),path,sha,zi.filename); zip_count+=1
        except (zipfile.BadZipFile,RuntimeError) as exc: scan_errors.append({'path':path,'reason':type(exc).__name__})
proc.stdin.close();proc.wait()
summary={'method':'known-secret-format regex over every reachable blob and bounded ZIP members; heuristic, not a proof of absence of unknown secret formats',
 'commits':len(git('rev-list','--all').splitlines()),'objects':len(objects),'blobs':blobs,'bytes':byte_count,'zip_members':zip_count,'findings':findings,'unscanned':scan_errors}
(out/'secret-scan.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('commits','objects','blobs','bytes','zip_members')}))
print('secret-format candidates:',len(findings),'archive limits:',len(scan_errors))
