// Project-scoped original + explicit PDF page selection. No automatic paid calls.
export function createPlanUpload(root,{storageKey,onError}) {
  const $=id=>root.querySelector('#'+id),MAX=5*1024*1024;
  let file=null,pdf=null,preview64=null,rows=[],selected=null,epoch=0,ready=false,uploadId=null,objectUrl=null,uploading=false,opening=false;
  function node(tag,text,parent){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(parent)parent.append(n);return n;}
  const section=node('section');section.className='cw-source';section.id='cwSource';
  section.innerHTML=`<label for="cwStartMode">كيف تريد بدء المخطط؟</label><select id="cwStartMode"><option value="describe">وصف مشروع جديد</option><option value="upload">رفع مخطط جاهز</option></select>
  <div id="cwUploadPanel" hidden><p class="cw-muted">ارفع صورة PNG أو JPEG أو WebP، أو ملف PDF حتى 5 ميجابايت. يُحفظ الأصل في مشروعك. في PDF اختر الصفحة التي تريد قراءتها.</p>
  <label for="cwPlanFile">ملف المخطط</label><input id="cwPlanFile" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp" data-mutate>
  <div id="cwPdfPagePanel" hidden><label for="cwPdfPage">الصفحة المطلوب استخدامها</label><select id="cwPdfPage" data-mutate></select></div>
  <img id="cwSourcePreview" alt="معاينة صفحة المخطط المختارة" hidden><p id="cwSourceStatus" role="status" aria-live="polite"></p>
  <button id="cwSaveSource" type="button" data-mutate disabled>حفظ المخطط في المشروع</button>
  <label for="cwSavedSource">مخطط محفوظ في هذا المشروع</label><select id="cwSavedSource" data-mutate><option value="">اختر مخططًا</option></select><button id="cwDownloadSource" type="button" disabled>تنزيل الملف الأصلي</button>
  <label for="cwSourceMode">كيف نستخدم المخطط؟</label><select id="cwSourceMode" data-mutate><option value="preserve">قراءة التوزيع الحالي للمراجعة</option><option value="revise">اقتراح تعديلات حسب وصفي</option></select>
  <p class="cw-muted">راجع أبعاد الموقع والأدوار أدناه. قراءة الصورة لا تثبت المقياس أو دقة نقل جميع العناصر؛ راجع المسودة مقابل الأصل قبل اعتمادها. تُقرأ الصفحة المختارة فقط.</p></div>`;
  $('cwBriefForm').querySelector('h2').after(section);
  function notice(text){$('cwSourceStatus').textContent=text;}
  async function api(body){
    const session=await window.ACS_AUTH.freshSession();if(!session)throw new Error('انتهت جلسة الدخول. أعد الدخول قبل رفع الملف.');
    return window.ACS_AUTH.acsFetchJSON('/v1/projects/'+window.ACS.projectId+'/workspace/plan-source',body,session.access_token,90000);
  }
  function persist(){
    $('cwConfirmed').checked=false;
    try{localStorage.setItem(storageKey(),JSON.stringify({id:selected,mode:$('cwStartMode').value,policy:$('cwSourceMode').value}));}catch(e){}
  }
  function selectSource(id){selected=rows.some(r=>r.id===id)?id:null;$('cwSavedSource').value=selected||'';$('cwDownloadSource').disabled=!selected;}
  function renderRows(){
    $('cwSavedSource').replaceChildren();const blank=node('option','اختر مخططًا',$('cwSavedSource'));blank.value='';
    for(const row of rows){const o=node('option',row.name+(row.media_type==='application/pdf'?' · الصفحة '+row.page+' من '+row.page_count:''),$('cwSavedSource'));o.value=row.id;}
    selectSource(selected);
  }
  function releasePreview(){if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;$('cwSourcePreview').hidden=true;$('cwSourcePreview').removeAttribute('src');}
  function base64(bytes){let s='';for(let i=0;i<bytes.length;i+=32768)s+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(s);}
  async function renderPage(){
    if(!pdf)return;const current=++epoch;ready=false;sync();notice('جارٍ تجهيز الصفحة المختارة…');
    const page=await pdf.getPage(Number($('cwPdfPage').value));const vp0=page.getViewport({scale:1});
    if(!Number.isFinite(vp0.width)||!Number.isFinite(vp0.height)||vp0.width<=0||vp0.height<=0)throw new Error('أبعاد صفحة PDF غير صالحة.');
    const vp=page.getViewport({scale:Math.min(2,1600/Math.max(vp0.width,vp0.height))});
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.ceil(vp.width));canvas.height=Math.max(1,Math.ceil(vp.height));
    try{
      await page.render({canvasContext:canvas.getContext('2d'),viewport:vp}).promise;
      if(current!==epoch)return;
      const data=canvas.toDataURL('image/jpeg',.92);preview64=data.split(',')[1];
      $('cwSourcePreview').src=data;$('cwSourcePreview').hidden=false;ready=true;uploadId=crypto.randomUUID();
      notice('الصفحة '+$('cwPdfPage').value+' من '+pdf.numPages+' جاهزة. احفظها ثم راجع المتطلبات.');
    }finally{canvas.width=canvas.height=0;page.cleanup();sync();}
  }
  async function chooseFile(){
    ++epoch;ready=false;uploadId=null;preview64=null;selectSource(null);persist();releasePreview();sync();
    if(pdf){await pdf.destroy();pdf=null;}$('cwPdfPagePanel').hidden=true;
    file=$('cwPlanFile').files[0]||null;if(!file){notice('');return;}
    if(!file.size||file.size>MAX)throw new Error('اختر ملفًا لا يتجاوز 5 ميجابايت.');
    notice('جارٍ فتح الملف…');const current=epoch;
    const magic=new Uint8Array(await file.slice(0,12).arrayBuffer());
    const isPdf=String.fromCharCode(...magic.subarray(0,5))==='%PDF-';
    if(isPdf){
      const pdfjs=await import('/vendor/pdfjs@4.10.38/pdf.min.mjs');pdfjs.GlobalWorkerOptions.workerSrc='/vendor/pdfjs@4.10.38/pdf.worker.min.mjs';
      const loading=pdfjs.getDocument({data:await file.arrayBuffer(),isEvalSupported:false});
      loading.onPassword=()=>{loading.destroy();onError(new Error('ملف PDF محمي بكلمة مرور. ارفع نسخة غير محمية.'));};
      const doc=await loading.promise;if(current!==epoch){await doc.destroy();return;}
      if(doc.numPages>200){await doc.destroy();throw new Error('ملف PDF يتجاوز 200 صفحة. ارفع الصفحات المطلوبة في ملف أصغر.');}
      pdf=doc;$('cwPdfPage').replaceChildren();for(let i=1;i<=pdf.numPages;i++){const o=node('option','الصفحة '+i,$('cwPdfPage'));o.value=i;}
      $('cwPdfPagePanel').hidden=false;await renderPage();
    }else{
      const png=magic[0]===137&&magic[1]===80,jpg=magic[0]===255&&magic[1]===216;
      const webp=String.fromCharCode(...magic.subarray(0,4))==='RIFF'&&String.fromCharCode(...magic.subarray(8,12))==='WEBP';
      if(!png&&!jpg&&!webp)throw new Error('الملف ليس صورة مدعومة أو PDF.');
      objectUrl=URL.createObjectURL(file);const img=$('cwSourcePreview');img.src=objectUrl;
      await img.decode();if(current!==epoch)return;
      if(img.naturalWidth*img.naturalHeight>40000000||Math.max(img.naturalWidth,img.naturalHeight)>12000)throw new Error('أبعاد الصورة كبيرة. صدّر صورة أصغر.');
      img.dataset.media=png?'image/png':jpg?'image/jpeg':'image/webp';img.hidden=false;ready=true;uploadId=crypto.randomUUID();notice('المعاينة جاهزة. احفظ المخطط ثم راجع المتطلبات.');sync();
    }
  }
  function sync(){const blocked=uploading||opening||root.getAttribute('aria-busy')==='true'||!$('cwRecoverJob').hidden;$('cwSaveSource').disabled=blocked||!ready;for(const id of ['cwStartMode','cwPlanFile','cwPdfPage','cwSavedSource','cwSourceMode'])$(id).disabled=blocked;}
  $('cwStartMode').addEventListener('change',()=>{$('cwUploadPanel').hidden=$('cwStartMode').value!=='upload';persist();});
  $('cwSourceMode').addEventListener('change',persist);
  async function prepare(fn){opening=true;sync();try{await fn();}catch(e){ready=false;releasePreview();notice(e.message);onError(e);}finally{opening=false;sync();}}
  $('cwPlanFile').addEventListener('change',()=>prepare(chooseFile));
  $('cwPdfPage').addEventListener('change',()=>{selectSource(null);persist();prepare(renderPage);});
  $('cwSavedSource').addEventListener('change',()=>{ready=false;releasePreview();selectSource($('cwSavedSource').value);persist();sync();const row=rows.find(r=>r.id===selected);notice(row?'سيستخدم الطلب '+row.name+' · الصفحة '+row.page+'. يمكنك تنزيل الأصل للمراجعة.':'اختر مخططًا محفوظًا أو ارفع ملفًا جديدًا.');});
  $('cwSaveSource').addEventListener('click',async()=>{
    if(!file||!ready||$('cwSaveSource').disabled)return;ready=false;uploading=true;sync();
    try{
      notice('جارٍ رفع المخطط وحفظ الأصل…');
      const body={action:'upload',source_id:uploadId,name:file.name,media_type:pdf?'application/pdf':$('cwSourcePreview').dataset.media,data_base64:base64(new Uint8Array(await file.arrayBuffer())),page:pdf?Number($('cwPdfPage').value):1};
      if(pdf)body.preview_base64=preview64;
      const result=await api(body);rows=[result.source,...rows.filter(r=>r.id!==result.source.id)];selected=result.source.id;renderRows();persist();notice('حُفظ الأصل في المشروع. راجع المتطلبات ثم تابع لاستخدام المخطط.');
    }catch(e){ready=true;notice('لم يتأكد حفظ الملف. أعد المحاولة؛ الرفع لا يبدأ توليدًا مدفوعًا.');onError(e);}
    finally{uploading=false;sync();}
  });
  $('cwDownloadSource').addEventListener('click',async()=>{
    if(!selected)return;try{const data=await api({action:'download',source_id:selected});const raw=Uint8Array.from(atob(data.data_base64),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([raw],{type:data.media_type}));const a=node('a',null,document.body);a.href=url;a.download=data.name;a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}catch(e){onError(e);}
  });
  return {
    sync,
    command(){if($('cwStartMode').value!=='upload')return {};if(!selected)throw new Error('احفظ المخطط أو اختر ملفًا محفوظًا قبل المتابعة.');return {source_id:selected,source_mode:$('cwSourceMode').value};},
    async restore(){const data=await api({action:'list'});rows=data.sources;let saved;try{saved=JSON.parse(localStorage.getItem(storageKey())||'null');}catch(e){}selected=saved?.id;renderRows();if(saved?.mode==='upload'){$('cwStartMode').value='upload';$('cwUploadPanel').hidden=false;}if(saved?.policy==='revise')$('cwSourceMode').value='revise';sync();},
  };
}
