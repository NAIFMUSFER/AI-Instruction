#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/transform_design_versions.py')
s=p.read_text(encoding='utf-8')
s2=s.replace("db.createObjectStore(ST_META); });", "db.createObjectStore(ST_META); };")
s2=s2.replace("db.createObjectStore(ST_VER,{keyPath:'record_id'}); });", "db.createObjectStore(ST_VER,{keyPath:'record_id'}); };")
if s2==s: raise SystemExit('upgrade transform marker correction did not apply')
p.write_text(s2,encoding='utf-8')
print('corrected IndexedDB upgrade transform marker')
