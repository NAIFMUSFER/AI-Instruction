// Project-scoped original + explicit PDF page selection. No automatic paid calls.
// A plan read from the owner's file is approved as a transcription of it.
export const TRANSCRIPTION={
  concept:'راجعت هذه النسخة وأعتمدها تخطيطيًا فقط. هذا لا يُعد اعتمادًا إنشائيًا أو تصريحًا للتنفيذ.',
  confirm:'أعتمد هذه النسخة كمخطط مقروء من ملفي (نقل مبدئي): الأبواب المرئية فقط مرسومة، ولم يُتحقق من الإنارة أو مسارات الوصول. هذا لا يُعد اعتمادًا إنشائيًا أو تصريحًا للتنفيذ.',
  ready:'المخطط مقروء من ملفك؛ الأبواب المرئية فقط مرسومة. الملاحظات الاستشارية لا تمنع اعتماده كنسخة منقولة مبدئية.',
  approved:'حُفظ اعتماد المخطط المقروء من ملفك كنسخة منقولة مبدئية. يمكنك الآن تحويلها أو تصديرها.',
  issues:{PLAN_SOURCE_TRANSCRIPTION:'مخطط مقروء من ملفك',DOOR_NOT_VISIBLE:'باب غير ظاهر في ملفك',PATH_NOT_VISIBLE:'مسار وصول غير ظاهر في ملفك',LIGHTING_NOT_DECLARED:'نقاط الإنارة لم تُحدَّد بعد',TRANSCRIPTION_ACKNOWLEDGEMENT_REQUIRED:'أكد اعتماد المخطط كنسخة مقروءة من ملفك'},
};
// Limits shared with the engine (acs_plan_sources / acs_upload_security):
// 5 MB stored file, 40 MP and 12000 px per side at most, and the vision read's
// 2576 px long side. Larger photos are downscaled here before upload.
export const LIMITS={file:5*1024*1024,image:25*1024*1024,pixels:40000000,side:12000,read:2576,preview:2*1024*1024};
const UNUSABLE='لا يمكن استخدام هذا الملف كما هو: ';
export function createPlanUpload(root,{storageKey,onError}) {
  const $=id=>root.querySelector('#'+id),MAX=LIMITS.file;
  let file=null,pdf=null,preview64=null,rows=[],selected=null,epoch=0,ready=false,uploadId=null,objectUrl=null,uploading=false,opening=false;
  function node(tag,text,parent){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(parent)parent.append(n);return n;}
  const section=node('section');section.className='cw-source';section.id='cwSource';
  section.innerHTML=`<label for="cwStartMode">كيف تريد بدء المخطط؟</label><select id="cwStartMode"><option value="describe">وصف مشروع جديد</option><option value="upload">رفع مخطط جاهز</option></select>
  <div id="cwUploadPanel" hidden><p class="cw-muted">ارفع صورة PNG أو JPEG أو WebP، أو ملف PDF حتى 5 ميجابايت. الصور الأكبر من 2576 بكسل تُصغَّر على جهازك قبل الرفع، وتُحذف منها بيانات الكاميرا والموقع. في PDF اختر الصفحة التي تريد قراءتها.</p>
  <label for="cwPlanFile">ملف المخطط</label><input id="cwPlanFile" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp" data-mutate>
  <div id="cwPdfPagePanel" hidden><label for="cwPdfPage">الصفحة المطلوب استخدامها</label><select id="cwPdfPage" data-mutate></select></div>
  <img id="cwSourcePreview" alt="معاينة صفحة المخطط المختارة" hidden><p id="cwSourceStatus" role="status" aria-live="polite"></p>
  <button id="cwSaveSource" type="button" data-mutate disabled>حفظ المخطط في المشروع</button>
  <label for="cwSavedSource">مخطط محفوظ في هذا المشروع</label><select id="cwSavedSource" data-mutate><option value="">اختر مخططًا</option></select><button id="cwDownloadSource" type="button" disabled>تنزيل الملف الأصلي</button>
  <label for="cwSourceMode">كيف نستخدم المخطط؟</label><select id="cwSourceMode" data-mutate><option value="preserve">قراءة التوزيع الحالي للمراجعة</option><option value="revise">اقتراح تعديلات حسب وصفي</option><option value="complete">قراءة المخطط ثم إكمال الأبواب (تصميم كامل)</option></select>
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
    if(!file.size)throw new Error('الملف فارغ. اختر ملف المخطط مرة أخرى.');
    notice('جارٍ فتح الملف…');const current=epoch;
    const magic=new Uint8Array(await file.slice(0,12).arrayBuffer());
    const isPdf=String.fromCharCode(...magic.subarray(0,5))==='%PDF-';
    if(file.size>(isPdf?MAX:LIMITS.image))throw new Error(isPdf?'اختر ملف PDF لا يتجاوز 5 ميجابايت.':'اختر صورة لا تتجاوز 25 ميجابايت؛ نصغّرها إلى 5 ميجابايت قبل الرفع.');
    if(isPdf){
      const pdfjs=await import('/vendor/pdfjs@4.10.38/pdf.min.mjs');pdfjs.GlobalWorkerOptions.workerSrc='/vendor/pdfjs@4.10.38/pdf.worker.min.mjs';
      const loading=pdfjs.getDocument({data:await file.arrayBuffer(),isEvalSupported:false});
      let locked=false;loading.onPassword=()=>{locked=true;loading.destroy();};
      let doc;try{doc=await loading.promise;}catch(e){
        // pdf.js reports in English; the owner gets the reason and the way out.
        throw new Error(locked||e?.name==='PasswordException'?UNUSABLE+'ملف PDF محمي بكلمة مرور. أزل الحماية واحفظ نسخة مفتوحة ثم ارفعها.':UNUSABLE+'تعذّر فتح ملف PDF؛ يبدو تالفًا أو غير مكتمل. صدّره من جديد ثم ارفعه.');
      }
      if(current!==epoch){await doc.destroy();return;}
      if(doc.numPages>200){await doc.destroy();throw new Error('ملف PDF يتجاوز 200 صفحة. ارفع الصفحات المطلوبة في ملف أصغر.');}
      pdf=doc;$('cwPdfPage').replaceChildren();for(let i=1;i<=pdf.numPages;i++){const o=node('option','الصفحة '+i,$('cwPdfPage'));o.value=i;}
      $('cwPdfPagePanel').hidden=false;await renderPage();
    }else{
      const png=magic[0]===137&&magic[1]===80,jpg=magic[0]===255&&magic[1]===216;
      const webp=String.fromCharCode(...magic.subarray(0,4))==='RIFF'&&String.fromCharCode(...magic.subarray(8,12))==='WEBP';
      if(!png&&!jpg&&!webp)throw new Error('الملف ليس صورة مدعومة أو PDF.');
      objectUrl=URL.createObjectURL(file);const img=$('cwSourcePreview');img.src=objectUrl;
      await img.decode();if(current!==epoch)return;
      if(img.naturalWidth*img.naturalHeight>LIMITS.pixels||Math.max(img.naturalWidth,img.naturalHeight)>LIMITS.side)throw new Error('أبعاد الصورة أكبر من 40 مليون بكسل أو 12000 بكسل للضلع. صدّر صورة أصغر.');
      img.dataset.media=png?'image/png':jpg?'image/jpeg':'image/webp';
      const before=[img.naturalWidth,img.naturalHeight];
      if(Math.max(...before)>LIMITS.read||file.size>MAX){
        file=await downscale(img,file,png);if(current!==epoch)return;
        releasePreview();objectUrl=URL.createObjectURL(file);img.src=objectUrl;await img.decode();if(current!==epoch)return;
        img.dataset.media=file.type;
      }
      img.hidden=false;ready=true;uploadId=crypto.randomUUID();
      notice((file.size&&before[0]!==img.naturalWidth?'صغّرنا الصورة من '+before.join('×')+' إلى '+img.naturalWidth+'×'+img.naturalHeight+' بكسل على جهازك (حد قراءة المخطط). ':'')+'المعاينة جاهزة. احفظ المخطط ثم راجع المتطلبات.');sync();
    }
  }
  // Long side at most 2576 px (the vision read's limit), re-encoded from pixels:
  // no camera or GPS metadata leaves the device. A drawing stays PNG unless that
  // is still over 5 MB; a photo becomes JPEG.
  async function downscale(img,source,png){
    const scale=Math.min(1,LIMITS.read/Math.max(img.naturalWidth,img.naturalHeight));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.naturalWidth*scale));canvas.height=Math.max(1,Math.round(img.naturalHeight*scale));
    const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    const blob=(type,q)=>new Promise(r=>canvas.toBlob(r,type,q));
    try{
      let out=png?await blob('image/png'):null;
      for(const q of [.9,.82,.72,.6]){if(out&&out.size<=MAX)break;out=await blob('image/jpeg',q);}
      if(!out||out.size>MAX)throw new Error('تعذّر تصغير الصورة إلى 5 ميجابايت. صدّرها بدقة أقل ثم أعد الرفع.');
      const name=out.type==='image/jpeg'?source.name.replace(/\.(png|webp|jpe?g)$/i,'')+'.jpg':source.name;
      return new File([out],name,{type:out.type});
    }finally{canvas.width=canvas.height=0;}
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
    }catch(e){
      // A refused file stays refused: say why and that it cannot be used, not "retry".
      const refused=e?.status>=400&&e?.status<500&&['INVALID_PLAN_SOURCE','INPUT_LIMIT'].includes(e?.code);
      ready=!refused;notice(refused?(/[\u0600-\u06FF]/.test(e.message||'')&&e.message.startsWith(UNUSABLE)?e.message:UNUSABLE+(e.message||'')):'لم يتأكد حفظ الملف. أعد المحاولة؛ الرفع لا يبدأ توليدًا مدفوعًا.');
      if(!refused)onError(e);
    }
    finally{uploading=false;sync();}
  });
  $('cwDownloadSource').addEventListener('click',async()=>{
    if(!selected)return;try{const data=await api({action:'download',source_id:selected});const raw=Uint8Array.from(atob(data.data_base64),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([raw],{type:data.media_type}));const a=node('a',null,document.body);a.href=url;a.download=data.name;a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}catch(e){onError(e);}
  });
  return {
    sync,
    command(){if($('cwStartMode').value!=='upload')return {};if(!selected)throw new Error('احفظ المخطط أو اختر ملفًا محفوظًا قبل المتابعة.');return {source_id:selected,source_mode:$('cwSourceMode').value};},
    async restore(){const data=await api({action:'list'});rows=data.sources;let saved;try{saved=JSON.parse(localStorage.getItem(storageKey())||'null');}catch(e){}selected=saved?.id;renderRows();if(saved?.mode==='upload'){$('cwStartMode').value='upload';$('cwUploadPanel').hidden=false;}if(['revise','complete'].includes(saved?.policy))$('cwSourceMode').value=saved.policy;sync();},
  };
}
