import { createRenderScene, stableJSON, RENDER_FINISHES } from '../shared/render-scene.js';
import { escapeHTML as E } from '../shared/geometry.js';
import { totals, conceptEnvelopeArea, understand } from '../shared/model.js';
/** Read-only diagnostic: the material viewer is never a generation or migration operation. */
export function renderSourceStatus(model, demo=false) {
    const t=totals(model), envelope=conceptEnvelopeArea(model), warnings=[];
    let expected=null;
    try { expected=understand(model.brief?.prompt||''); } catch {}
    const residential=['villa','chalet'].includes(expected?.projectType);
    const wrongType=residential && !['villa','chalet'].includes(model.design?.projectType);
    const wrongBeds=residential && expected.sources?.bedrooms==='requested' && t.bedrooms!==expected.bedrooms;
    const requested=expected?.buildingArea?.source==='requested'?expected.buildingArea:null;
    const wrongArea=!!requested && (envelope>requested.max+.05||envelope<requested.min-.05);
    const genericChalet=expected?.projectType==='chalet' && expected.pool && expected.floors===1 &&
        expected.bedrooms===3 && !model.design?.layoutStrategy?.startsWith('compact-');
    if(wrongType)warnings.push('نوع النموذج المفتوح لا يطابق نوع المشروع في وصفه المحفوظ.');
    if(wrongBeds)warnings.push('عدد غرف النوم في النموذج لا يطابق العدد المطلوب في وصفه المحفوظ.');
    if(wrongArea)warnings.push(`المبنى المفتوح لا يطابق نطاق ${requested.min}–${requested.max} م² في وصفه.`);
    if(genericChalet)warnings.push('هذا توزيع شاليه عام، وليس التوزيع المدمج ذي الحوش الواسع. تغيير الخامات لن يصحح التوزيع.');
    return {title:model.title,projectType:model.design?.projectType||'villa',levels:model.levels.length,
        bedrooms:t.bedrooms,landArea:t.landArea,width:model.site.width,depth:model.site.depth,
        envelope,unbuilt:Math.max(0,t.landArea-envelope),demo:!!demo,warnings,
        needsRebuild:!demo&&(wrongType||wrongBeds||wrongArea||genericChalet)};
}

/** Isolated panel; the existing studio remains operational when worker/WebGL2 is absent. */
export async function openRenderStudio({api,getModel,getRevision,getCloudVersion,isPending,isReadOnly,saveCloud,showModal,onSelect,reportError,isDemo=()=>false}) {
    const source=renderSourceStatus(getModel(),isDemo()),sourceRevision=getRevision();
    const types={villa:'فيلا',chalet:'شاليه',office:'مكاتب',warehouse:'مستودع',retail:'تجاري'};
    const num=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:2});
    const contextHTML=`<section id="render-source" class="render-source" aria-label="مصدر المجسم">
        <strong>${source.demo?'مثال توضيحي — ليس مشروعك':'المشروع المفتوح'}: ${E(source.title)}</strong>
        <p>${E(types[source.projectType]||source.projectType)} · ${source.levels} دور · ${source.bedrooms} غرف نوم · أرض ${num(source.width)} × ${num(source.depth)} م</p>
        <div class="render-source-metrics"><span>غلاف المباني التقريبي <b>${num(source.envelope)} م²</b></span><span>خارج المباني <b>${num(source.unbuilt)} م²</b></span></div>
        <small>يشمل الخارج المسبح والمواقف والجلسات، وليس كله حديقة. الغلاف المفاهيمي ليس مسطح رخصة.</small>
        <small>نسخة التصميم: <b dir="ltr">${E(sourceRevision)}</b></small>
        <p>هذه معاينة للنموذج المفتوح نفسه؛ ليست إعادة تصميم ولا صورة ناتجة من Blender.</p><button type="button" class="btn light" data-action="quality-review">فحص جودة التوزيع قبل الخامات</button>
        ${source.demo?'<button type="button" class="btn primary" data-action="new">ابدأ مشروعك بدل المثال</button>':''}
        ${!source.demo&&getModel().brief?.prompt?`<details><summary>الوصف المحفوظ لهذا المجسم</summary><p class="render-original">${E(getModel().brief.prompt)}</p></details>`:''}
        ${source.warnings.length?`<div id="render-source-warning" class="notice warn" role="status">${source.warnings.map(s=>`<p>${E(s)}</p>`).join('')}${source.needsRebuild&&!isReadOnly()?'<button type="button" class="btn light" data-action="regenerate-brief">مراجعة الوصف وإنشاء توزيع مستقل</button><small>لا نحذف المشروع الحالي أو نعدّل أبعاده تلقائيًا.</small>':''}</div>`:''}
    </section>`;
    showModal('معاينة المشروع والخامات', `<section id="render-studio">${contextHTML}<p class="notice">التشطيبات والأثاث للعرض فقط. الإخراج لا يغيّر أبعاد التصميم ولا يعني اعتمادًا هندسيًا.</p><div class="properties-grid"><label class="field"><span>التشطيب</span><select id="render-finish">${Object.entries(RENDER_FINISHES).map(([id,f])=>`<option value="${id}">${E(f.label)}</option>`).join('')}</select></label><label class="field"><span>جودة الصور</span><select id="render-quality"><option value="preview">تجريبية · 640 × 480</option><option value="standard">أعلى · 1280 × 960</option></select></label><label class="field"><span>المساحة للمنظور الداخلي</span><select id="render-room"><option value="">اختيار تلقائي</option>${getModel().levels.map(l=>l.rooms.map(r=>`<option value="${E(r.id)}">${E(l.name)} · ${E(r.name)}</option>`).join('')).join('')}</select></label></div><label class="check-line"><input type="checkbox" id="render-furniture" checked>أثاث توضيحي غير هندسي</label><div class="render-actions"><button class="btn light" id="render-pbr">معاينة بالخامات</button><button class="btn light" id="render-local">تنزيل مشهد Blender</button><button class="btn primary" id="render-start" disabled>إنشاء صور وملف Blender</button></div><p id="render-capability" class="notice" aria-live="polite">جارٍ التحقق من عامل الإخراج…</p><div id="render-canvas-host" hidden><canvas id="render-canvas" tabindex="0" aria-label="المجسم بالخامات؛ اسحب للدوران وانقر غرفة للتحديد"></canvas><label class="check-line"><input id="render-cutaway" type="checkbox">إخفاء سقف العرض فقط</label><p id="render-selection">اختر مساحة لتحديدها في مخطط مسار.</p></div><div id="render-gallery"></div><h3>مهام حسابك</h3><div id="render-jobs" aria-live="polite"></div><p class="property-note">تحتاج خدمة الصور إلى عامل Blender مستقل وتخزين مهيأ. مشهد JSON يُفتح بالسكربت المرفق بالمشروع، وليس مباشرةً بقائمة فتح Blender. لا نرفع وصفك أو التعليقات إلى عامل الإخراج.</p></section>`,'MASAR / VISUALIZATION');
    const host=document.getElementById('render-studio'),dialog=document.getElementById('modal');let disposed=false,busy=false,viewer=null,poll=null,capabilities={enabled:false,workerOnline:false};
    const $=s=>host.querySelector(s),alive=()=>!disposed&&host.isConnected;
    const revision=()=>getRevision();
    const settings=()=>({finish:$('#render-finish').value,quality:$('#render-quality').value,roomId:$('#render-room').value||null,furniture:$('#render-furniture').checked});
    const snapshot=()=>{if(isPending())throw Error('اعتمد التعديل أو ألغِ المعاينة أولًا.');return createRenderScene(getModel(),revision(),settings());};
    const execute=fn=>async e=>{if(e?.currentTarget?.tagName==='BUTTON')e.preventDefault();try{await fn(e);}catch(err){reportError(err);}};
    // The shared dialog can reopen before its previous queued close event arrives.
    const closed=()=>{if(!dialog.open||!host.isConnected)dispose();};
    const dispose=()=>{if(disposed)return;disposed=true;clearTimeout(poll);viewer?.dispose();dialog.removeEventListener('close',closed);};dialog.addEventListener('close',closed);
    async function ensureViewer(){
        if(globalThis.MASAR_STANDALONE)throw Error('عرض الخامات يحتاج تشغيل الخادم؛ ملف HTML المستقل يبقي العارض الأساسي.');
        $('#render-canvas-host').hidden=false;
        if(!viewer){let module;try{module=await import('/public/render-viewer.js');}catch{throw Error('عارض الخامات غير مبني بعد. شغّل build داخل render-viewer؛ بقي العارض الأساسي متاحًا.');}if(!alive())return null;try{viewer=module.createViewer($('#render-canvas'),(roomId)=>{if(roomId){onSelect(roomId);$('#render-selection').textContent='تم تحديد المساحة في المخطط: '+(getModel().levels.flatMap(l=>l.rooms).find(r=>r.id===roomId)?.name||roomId);}});}catch{throw Error('الجهاز لا يدعم عارض الخامات WebGL2؛ العارض الأساسي والمخطط متاحان.');}}
        return viewer;
    }
    $('#render-pbr').addEventListener('click',execute(async()=>{const s=snapshot(),v=await ensureViewer();v?.setScene(s);v?.cutaway($('#render-cutaway').checked);
        if(alive()){$('#render-canvas').dataset.sourceModel=s.source.modelId;$('#render-canvas').dataset.sourceRevision=s.source.revisionId;}}));
    $('#render-cutaway').addEventListener('change',()=>viewer?.cutaway($('#render-cutaway').checked));
    $('#render-local').addEventListener('click',execute(()=>{const raw=stableJSON(snapshot());const url=URL.createObjectURL(new Blob([raw],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='MASAR-Blender-Scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}));
    const stateLabels={queued:'في الطابور',running:'جارٍ الإخراج',succeeded:'مكتملة',failed:'فشلت — لم يتغير المشروع',cancelled:'أُلغيت'};
    async function refresh(){
        if(!alive())return dispose();
        try {
            if(globalThis.MASAR_STANDALONE||!api.available){$('#render-capability').textContent='خدمة الصور غير متصلة. يمكنك تنزيل مشهد JSON للعمل محليًا.';return;}
            capabilities=await api.request('/api/renders/capabilities',{timeout:5000});if(!alive())return;
            $('#render-capability').textContent=!capabilities.enabled?'معاينة الخامات وتنزيل مشهد JSON متاحان. إنتاج صور Cycles وملف .blend غير متاح في هذه المعاينة؛ تسجيل الدخول لا يفعّله.':!capabilities.workerOnline?'عامل Blender غير متصل؛ لن ندّعي بدء رندر.':`عامل Blender متصل · تحفظ النتائج ${capabilities.retentionDays} أيام. ${capabilities.storage==='ephemeral'?'تنبيه: التخزين الخادمي مؤقت.':''}`;
            $('#render-start').disabled=busy||!capabilities.enabled||!api.user||!capabilities.workerOnline||isReadOnly()||isPending();
            $('#render-start').textContent=!capabilities.enabled?'الرندر السحابي غير متاح في المعاينة':'إنشاء صور وملف Blender';
            if(!api.user){$('#render-jobs').textContent=capabilities.enabled?'سجّل الدخول من «الحساب» للحفظ والإخراج على الخادم.':'لا توجد خدمة رندر سحابية في خيار المعاينة. المعاينة المحلية وتنزيل المشهد لا يحتاجان حسابًا.';return;}
            const {jobs}=await api.request('/api/renders');if(!alive())return;
            $('#render-jobs').innerHTML=jobs.length?jobs.map(job=>{
                const other=job.projectId!==getModel().id,old=job.stale||other||job.revisionId!==revision();
                return `<article class="render-job" data-job="${E(job.id)}"><strong>${E(stateLabels[job.status]||job.status)}</strong><p>${other?'لمشروع آخر':old?'لنسخة أقدم — ليست التصميم الحالي':'لنفس نسخة التصميم'} · ${E(RENDER_FINISHES[job.settings.finish]?.label||job.settings.finish)} · محاولة ${job.attempt}/2</p><small dir="ltr">${E(job.revisionId)}</small><div class="render-actions">${['queued','running'].includes(job.status)?'<button class="btn light small" data-render-job-action="cancel">إلغاء الإخراج</button>':''}${job.status==='failed'&&job.attempt<2?'<button class="btn light small" data-render-job-action="retry">إعادة محاولة النسخة نفسها</button>':''}${job.status==='succeeded'?`<button class="btn light small" data-render-job-action="view">عرض الصور</button>${!old?'<button class="btn light small" data-render-job-action="glb">فتح GLB المتزامن</button>':''}${job.files.map(f=>`<a class="btn light small" href="${E(f.url)}" download>${E(f.name)}</a>`).join('')}`:''}</div></article>`;
            }).join(''):'لا توجد مهام إخراج بعد.';
            host.renderJobs=jobs;
        }catch(e){if(alive()){$('#render-capability').textContent='تعذر الوصول لعامل الإخراج. التصميم المحلي محفوظ مستقلًا.';$('#render-start').disabled=true;}}
        finally{if(alive())poll=setTimeout(refresh,5000);}
    }
    $('#render-start').addEventListener('click',execute(async()=>{
        if(busy)return;const s=snapshot();if(!api.user||isReadOnly())throw Error('تحتاج حساب مالك المشروع.');busy=true;$('#render-start').disabled=true;
        try {await saveCloud();if(!alive())return;if(revision()!==s.source.revisionId)throw Error('تغيرت نسخة المشروع أثناء الحفظ؛ أعد الطلب.');await api.request('/api/renders',{method:'POST',body:{projectId:s.source.modelId,revisionId:s.source.revisionId,version:getCloudVersion(),settings:s.settings}});clearTimeout(poll);await refresh();}finally{busy=false;}
    }));
    $('#render-jobs').addEventListener('click',execute(async e=>{
        const button=e.target.closest('[data-render-job-action]');if(!button)return;e.preventDefault();const id=button.closest('[data-job]').dataset.job,job=host.renderJobs?.find(j=>j.id===id);if(!job)return;
        const action=button.dataset.renderJobAction;
        if(['cancel','retry'].includes(action)){await api.request(`/api/renders/${id}/${action}`,{method:'POST',body:{}});clearTimeout(poll);await refresh();}
        if(action==='view'){$('#render-gallery').innerHTML=`<p class="notice">صور النسخة ${E(job.revisionId)} — ${!job.stale&&job.revisionId===revision()&&job.projectId===getModel().id?'الحالية':'ليست النسخة الحالية'}</p>${job.files.filter(f=>f.name.endsWith('.png')).map(f=>`<figure><img src="${E(f.url)}" alt="${f.name==='exterior.png'?'إخراج خارجي':'إخراج داخلي'} من Blender" loading="lazy"><figcaption>${f.name==='exterior.png'?'منظور خارجي':'منظور داخلي'}</figcaption></figure>`).join('')}`;}
        if(action==='glb'){if(job.stale||isPending()||job.revisionId!==revision()||job.projectId!==getModel().id)throw Error('لا يمكن عرض نسخة قديمة كأنها التصميم الحالي.');const v=await ensureViewer(),file=job.files.find(f=>f.name==='model.glb');const response=await fetch(file.url,{credentials:'same-origin',redirect:'error'});if(!response.ok)throw Error('تعذر تحميل المجسم.');await v?.loadGLB(await response.arrayBuffer());v?.cutaway($('#render-cutaway').checked);}
    }));
    await refresh();
}
