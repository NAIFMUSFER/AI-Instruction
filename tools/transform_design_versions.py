#!/usr/bin/env python3
from pathlib import Path


def rep(path, old, new):
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise SystemExit("marker mismatch in %s: %d" % (path, src.count(old)))
    p.write_text(src.replace(old, new, 1), encoding="utf-8")


# Visible controls beside generation results.
rep("public/index.html",
'''      <div id="reportBox" class="report" role="region" aria-label="تقرير التغطية وحالات الخطأ — Coverage report and error states"></div>

      <div class="cards">''',
'''      <div id="reportBox" class="report" role="region" aria-label="تقرير التغطية وحالات الخطأ — Coverage report and error states"></div>
      <div id="acsDesignVersionBar" class="row acs-hidden" role="group" aria-label="حفظ وإدارة نسخ التصميم — Save and manage design versions">
        <button class="btn" id="acsSaveDesign" type="button">💾 حفظ هذه النسخة</button>
        <button class="ghost acs-u-11" id="acsShowVersions" type="button">🗂 نسخ التصميم</button>
      </div>
      <div id="acsDesignVersionState" class="note acs-hidden" role="status" aria-live="polite"></div>
      <div id="acsDesignVersionList" class="note acs-hidden" role="region" aria-label="نسخ التصميم المحفوظة — Saved design versions"></div>

      <div class="cards">''')

p = "public/app/trust/wiring.js"
rep(p,
"const DB_NAME='acs_local_project', DB_VER=1;\nconst ST_REC='records', ST_META='meta';",
"const DB_NAME='acs_local_project', DB_VER=2;\nconst ST_REC='records', ST_META='meta', ST_VER='design_versions';")
rep(p,
'''      if(!db.objectStoreNames.contains(ST_META))
        db.createObjectStore(ST_META); });''',
'''      if(!db.objectStoreNames.contains(ST_META))
        db.createObjectStore(ST_META);
      if(!db.objectStoreNames.contains(ST_VER))
        db.createObjectStore(ST_VER,{keyPath:'record_id'}); });''')
rep(p,
'''    await idbTx(db,[ST_REC,ST_META],'readwrite',tx=>{
      tx.objectStore(ST_REC).clear(); tx.objectStore(ST_META).delete(PTR_KEY); });''',
'''    await idbTx(db,[ST_REC,ST_META,ST_VER],'readwrite',tx=>{
      tx.objectStore(ST_REC).clear(); tx.objectStore(ST_META).delete(PTR_KEY);
      tx.objectStore(ST_VER).clear(); });''')

version_code = r'''
/* ═══════════ 1b · نسخ التصميم التي يعتمدها المهندس ═══════════════════════
   تختلف عن AUTOSAVE: لا تدخل في تقليم السجلات الدوّارة، ولا تُستبدل عند توليد
   نموذج جديد. كل نسخة سجلّ P.encode متحقق الهاش، محفوظ محلياً على هذا الجهاز. */
async function vList(){
  const db=await idbOpen(); let rows=[];
  await idbTx(db,[ST_VER],'readonly',tx=>{
    tx.objectStore(ST_VER).getAll().onsuccess=e=>{ rows=e.target.result||[]; }; });
  db.close();
  return rows.filter(r=>P.validateRecord(r).usable).sort((a,b)=>(b.saved_at_ms||0)-(a.saved_at_ms||0));
}
async function vSave(){
  const project=pProject();
  if(!project.model) return {ok:false,code:'NO_MODEL'};
  const now=Date.now(), current=await vList();
  const enc=P.encode(project,{now:now,origin:'DESIGN_VERSION',project_id:'default',
    record_id:'ver_'+now+'_'+T.hash(T.canonical(project.model)).slice(0,10)});
  if(!enc.ok) return enc;
  const rec=enc.record;
  rec.version_number=current.reduce((m,r)=>Math.max(m,Number(r.version_number)||0),0)+1;
  rec.version_label='V'+rec.version_number; rec.accepted=false; rec.saved_by_user=true;
  const db=await idbOpen();
  await idbTx(db,[ST_VER],'readwrite',tx=>tx.objectStore(ST_VER).put(rec)); db.close();
  await vRender();
  return {ok:true,code:'VERSION_SAVED',record_id:rec.record_id,label:rec.version_label};
}
async function vRestore(id){
  const db=await idbOpen(); let rec=null;
  await idbTx(db,[ST_VER],'readonly',tx=>{
    tx.objectStore(ST_VER).get(id).onsuccess=e=>{rec=e.target.result||null;}; }); db.close();
  const d=P.decode(rec);
  if(!d.ok||!d.project||!d.project.model) return {ok:false,code:d.code||'VERSION_INVALID'};
  setModel(d.project.model); __ACS_SHARED.LAST_REQUEST_TEXT=d.project.request_text||'';
  const desc=$('descText'); if(desc&&d.project.request_text) desc.value=d.project.request_text;
  try{ if(typeof statusEl!=='undefined'&&statusEl)
    statusEl.textContent='✓ استُعيدت '+(rec.version_label||'نسخة محفوظة')+' — يمكنك متابعة التعديل أو توليد نسخة جديدة.'; }catch(e){}
  return {ok:true,code:'VERSION_RESTORED',label:rec.version_label};
}
async function vAccept(id){
  const db=await idbOpen();
  await idbTx(db,[ST_VER],'readwrite',tx=>{
    const s=tx.objectStore(ST_VER), g=s.getAll();
    g.onsuccess=()=>{ (g.result||[]).forEach(r=>{r.accepted=r.record_id===id; s.put(r);}); }; });
  db.close(); await vRender(); return {ok:true,code:'VERSION_ACCEPTED'};
}
async function vDelete(id){
  const db=await idbOpen();
  await idbTx(db,[ST_VER],'readwrite',tx=>tx.objectStore(ST_VER).delete(id)); db.close();
  await vRender(); return {ok:true,code:'VERSION_DELETED'};
}
function vShowBar(show){ const bar=$('acsDesignVersionBar'); if(bar) bar.classList.toggle('acs-hidden',show===false); }
async function vRender(){
  const box=$('acsDesignVersionList'), st=$('acsDesignVersionState'); if(!box) return [];
  const rows=await vList();
  if(!rows.length){ box.innerHTML='<span lang="ar">لا توجد نسخ محفوظة بعد.</span>'; return rows; }
  box.innerHTML='<b>نسخ التصميم المحفوظة</b><br>'+rows.map(r=>
    '<div class="acs-rec-act" data-version="'+escT(r.record_id)+'">'
    +'<b>'+escT(r.version_label||'نسخة')+(r.accepted?' ⭐':'')+'</b> · '
    +escT(new Date(r.saved_at_ms||0).toLocaleString('ar'))+'<br>'
    +'<button type="button" class="ghost" data-vrestore="'+escT(r.record_id)+'">فتح</button> '
    +'<button type="button" class="ghost" data-vaccept="'+escT(r.record_id)+'">اعتماد ⭐</button> '
    +'<button type="button" class="ghost" data-vdelete="'+escT(r.record_id)+'">حذف</button></div>').join('');
  box.querySelectorAll('[data-vrestore]').forEach(b=>b.onclick=()=>vRestore(b.dataset.vrestore));
  box.querySelectorAll('[data-vaccept]').forEach(b=>b.onclick=()=>vAccept(b.dataset.vaccept));
  box.querySelectorAll('[data-vdelete]').forEach(b=>b.onclick=()=>vDelete(b.dataset.vdelete));
  if(st){ st.textContent=rows.length+' نسخة محفوظة على هذا الجهاز'; st.classList.remove('acs-hidden'); }
  return rows;
}
'''
rep(p, "function pDownload(name, mime, text){", version_code + "\nfunction pDownload(name, mime, text){")
rep(p,
'''  storage_kind:'INDEXEDDB_LOCAL_TO_THIS_DEVICE',
  is_cloud_backup:false
};''',
'''  storage_kind:'INDEXEDDB_LOCAL_TO_THIS_DEVICE',
  is_cloud_backup:false
};
window.ACS.designVersions={save:vSave,list:vList,restore:vRestore,accept:vAccept,remove:vDelete,render:vRender,
  storage_kind:'INDEXEDDB_LOCAL_TO_THIS_DEVICE',is_cloud_backup:false};''')
rep(p,
'''  const bs=$('acsSaveNow');
  if(bs) bs.onclick=()=>{ window.ACS.persistence.save('MANUAL'); };''',
'''  const bs=$('acsSaveNow');
  if(bs) bs.onclick=()=>{ window.ACS.persistence.save('MANUAL'); };
  const sv=$('acsSaveDesign');
  if(sv) sv.onclick=async()=>{
    const r=await vSave(), st=$('acsDesignVersionState');
    if(st){ st.classList.remove('acs-hidden'); st.textContent=r.ok
      ?('✓ حُفظ التصميم كـ '+r.label+' — لن يضيع عند توليد نسخة جديدة.')
      :'تعذّر حفظ نسخة التصميم ('+r.code+').'; }
    if(r.ok) liveSay('حُفظت '+r.label+' من التصميم.'); };
  const vl=$('acsShowVersions');
  if(vl) vl.onclick=async()=>{ const box=$('acsDesignVersionList'); await vRender(); if(box) box.classList.toggle('acs-hidden'); };
  document.addEventListener('acs:generation-started',()=>vShowBar(false));
  document.addEventListener('acs:generation-succeeded',async()=>{vShowBar(true); await vRender();});''')
rep(p,
'''  pRecover().then(r=>{
    window.ACS.recoveryResult=()=>r;''',
'''  vRender().catch(()=>{});
  pRecover().then(r=>{
    window.ACS.recoveryResult=()=>r;''')

# Generation lifecycle events are emitted only after the first real rendered frame.
p = "public/app/ui/workspace-ui-wiring.js"
rep(p,
'''  document.getElementById('reportBox').className='report';

  const res=await''',
'''  document.getElementById('reportBox').className='report';
  document.dispatchEvent(new CustomEvent('acs:generation-started'));

  const res=await''')
rep(p,
'''      +' · '+window.ACS.trust.modelReviewSummary(data,document.documentElement.lang);
  };''',
'''      +' · '+window.ACS.trust.modelReviewSummary(data,document.documentElement.lang);
    document.dispatchEvent(new CustomEvent('acs:generation-succeeded',{detail:{
      rooms:data.rooms||null,levels:data.levels||null,mode:data.mode||null,request_id:res.request_id||''}}));
  };''')

print("design version transform applied")
