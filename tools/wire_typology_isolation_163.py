#!/usr/bin/env python3
# trigger after workflow installation
from pathlib import Path
p=Path('public/app/ui/connected-workspace.mjs')
s=p.read_text(encoding='utf-8')
old="const program=source.source_id?briefProgram():residentialOptions.program(briefProgram(),option);"
new="const program=source.source_id?briefProgram():($('cwType').value==='residential'?residentialOptions.program(briefProgram(),option):briefProgram());"
if new in s:
    print('already wired')
elif s.count(old)!=1:
    raise SystemExit(f'expected one generation routing anchor, found {s.count(old)}')
else:
    p.write_text(s.replace(old,new,1),encoding='utf-8')
    print('wired typology-specific program strategy')
