"""Independent IFC4 schema check of actual exports; no substitute for geometry QA.

Usage: audit_ifc_schema.py CHECKOUT OUTPUT model1.json [model2.json ...] [--express]
Requires IfcOpenShell in the audit environment only, not the product runtime.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

root,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
sys.path.insert(0,str(root))
import acs_bim as B
import acs_authoring as A
import ifcopenshell
import ifcopenshell.validate

out.mkdir(parents=True,exist_ok=True)
summary=[]
express='--express' in sys.argv[3:]
for name in [a for a in sys.argv[3:] if a!='--express']:
    source=Path(name).resolve();model=json.loads(source.read_text())
    start=time.perf_counter()
    result=B.export_ifc(A.create_project(model),generated_at='2026-09-06T00:00:00Z')
    if not result['valid']:
        summary.append({'source':str(source),'export_valid':False,'issues':result['issues']})
        continue
    text=result['file'];(out/(source.stem+'.ifc')).write_text(text)
    doc=ifcopenshell.file.from_string(text)
    logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(doc,logger,express_rules=express)
    rows=[{k:(v if isinstance(v,(str,int,float,bool,list,dict,type(None))) else str(v))
           for k,v in row.items()} for row in logger.statements]
    (out/(source.stem+'-schema.json')).write_text(json.dumps(rows,indent=2)+'\n')
    summary.append({'source':str(source),'export_valid':True,'schema':doc.schema,
                    'schema_errors':sum(e.get('type')=='schema' for e in rows),
                    'validation_errors':len(rows),'express_rules_evaluated':express,
                    'checker_version':ifcopenshell.version,
                    'sha256':hashlib.sha256(text.encode()).hexdigest(),
                    'seconds':time.perf_counter()-start})
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
