#!/usr/bin/env python3
# One-shot branch transform trigger: product files are committed by the workflow.
from pathlib import Path
p=Path('tests/remediation/test_persistence.js')
s=p.read_text(encoding='utf-8')
marker="console.log('\\n== §14 — الصفحة المشحونة تُعلن الحفظ المحلي ولا تدّعي سحابة ==');"
if 'design versions use a dedicated IndexedDB store' not in s:
    block=r'''
console.log('\n== §13b — نسخ التصميم المعتمدة مستقلة عن AUTOSAVE ==');
(function(){
  const indexHtml=require('fs').readFileSync(_np.join(__dirname,'../../public/index.html'),'utf8');
  chk('design versions use a dedicated IndexedDB store',
      page.indexOf("ST_VER='design_versions'")>=0);
  chk('design versions are not part of rolling autosave pruning',
      page.indexOf("idbTx(db,[ST_VER],'readwrite'")>=0
      && page.indexOf("origin:'DESIGN_VERSION'")>=0);
  chk('a successful generation exposes an explicit save-design action',
      indexHtml.indexOf('id="acsSaveDesign"')>=0
      && indexHtml.indexOf('حفظ هذه النسخة')>=0);
  chk('saved versions can be restored and one can be marked accepted',
      page.indexOf('async function vRestore(id)')>=0
      && page.indexOf('async function vAccept(id)')>=0);
  chk('save action is revealed only after the generation success event',
      page.indexOf("acs:generation-succeeded")>=0
      && page.indexOf('vShowBar(true)')>=0);
})();

'''
    if marker not in s: raise SystemExit('persistence test insertion marker missing')
    s=s.replace(marker,block+marker,1)
    p.write_text(s,encoding='utf-8')
print('design version tests transform applied')
