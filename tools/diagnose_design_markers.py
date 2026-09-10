#!/usr/bin/env python3
from pathlib import Path
p=Path('public/app/trust/wiring.js').read_text(encoding='utf-8')
markers=[
("db","const DB_NAME='acs_local_project', DB_VER=1;\nconst ST_REC='records', ST_META='meta';"),
("upgrade","      if(!db.objectStoreNames.contains(ST_META))\n        db.createObjectStore(ST_META); });"),
("clear","    await idbTx(db,[ST_REC,ST_META],'readwrite',tx=>{\n      tx.objectStore(ST_REC).clear(); tx.objectStore(ST_META).delete(PTR_KEY); });"),
("download","function pDownload(name, mime, text){"),
("persistence","  storage_kind:'INDEXEDDB_LOCAL_TO_THIS_DEVICE',\n  is_cloud_backup:false\n};"),
("save","  const bs=$('acsSaveNow');\n  if(bs) bs.onclick=()=>{ window.ACS.persistence.save('MANUAL'); };"),
("recover","  pRecover().then(r=>{\n    window.ACS.recoveryResult=()=>r;"),
]
for n,m in markers: print(n,p.count(m))
