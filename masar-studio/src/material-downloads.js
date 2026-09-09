/** Client-only visual downloads. No server jobs, prompts, comments or model writes. */
export const VISUAL_EXPORT_LIMIT = 4000;
export function visualExportDescriptor(spec) {
    if (spec?.schema !== 'masar-render-scene-1' || spec.units !== 'm') throw Error('مشهد المعاينة غير صالح للتصدير.');
    const source = spec.source;
    for (const key of ['modelId','revisionId']) if (typeof source?.[key] !== 'string' || !source[key] || source[key].length > 160) throw Error('مرجع المشروع أو النسخة غير صالح.');
    if (!Array.isArray(spec.objects) || !spec.objects.length || spec.objects.length > VISUAL_EXPORT_LIMIT) throw Error('التنزيل المحلي يدعم حتى 4,000 عنصر؛ نزّل مشهد JSON للمشاريع الأكبر.');
    if (!['warm','white','slate'].includes(spec.settings?.finish) || typeof spec.settings?.furniture !== 'boolean') throw Error('إعدادات المعاينة غير صالحة.');
    const ids = new Set();
    for (const o of spec.objects) {
        if (typeof o.id !== 'string' || !o.id || ids.has(o.id) || o.shape !== 'box' || !Array.isArray(o.min) || !Array.isArray(o.size) || o.min.length !== 3 || o.size.length !== 3 || ![...o.min,...o.size].every(Number.isFinite) || o.size.some(x=>x<=0)) throw Error('أحد عناصر المجسم غير صالح أو مكرر.');
        ids.add(o.id);
    }
    return {schema:'masar-browser-visual-1',modelId:source.modelId,revisionId:source.revisionId,units:'m',axes:'X-east Y-up Z-south',objectCount:spec.objects.length,finish:spec.settings.finish,furniture:spec.settings.furniture,roof:'included',scope:'Concept visualization only; not BIM round-trip, construction approval or a Blender render.'};
}
export function inspectLocalGLB(buffer) {
    if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 32 || buffer.byteLength > 24_000_000) throw Error('حجم GLB غير صالح.');
    const v=new DataView(buffer), length=v.getUint32(12,true);
    if(v.getUint32(0,true)!==0x46546c67 || v.getUint32(4,true)!==2 || v.getUint32(8,true)!==buffer.byteLength || v.getUint32(16,true)!==0x4e4f534a || length%4 || length<2 || 20+length>buffer.byteLength) throw Error('بنية GLB غير صالحة.');
    const doc=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,length)));
    if(doc.asset?.version!=='2.0' || (doc.buffers||[]).some(b=>b.uri) || (doc.images||[]).some(i=>i.uri) || doc.extensionsRequired?.length || !doc.meshes?.length) throw Error('التصدير يجب أن يكون مجسمًا ذاتي المحتوى.');
    return doc;
}
export function attachMaterialDownloads({host,getViewer,getSnapshot,isAlive,reportError}) {
    const parent=host.querySelector('#render-canvas-host');
    const root=document.createElement('section');root.id='material-downloads';
    root.innerHTML='<h3>تنزيل المعاينة من جهازك</h3><div class="render-actions"><button type="button" class="btn light" id="render-save-png" disabled>تنزيل صورة المعاينة PNG</button><button type="button" class="btn light" id="render-save-glb" disabled>تنزيل مجسم GLB كامل</button></div><p id="render-download-state" class="notice" role="status">أنشئ المعاينة بالخامات أولًا.</p><p class="property-note">PNG لقطة من زاوية العرض الحالية وليست صورة Cycles؛ تضاف إليها هوية النسخة وحدود الاستخدام. ملف GLB يتضمن جميع الأدوار والسقف كاملًا حتى عند عزل دور أو إخفاء السقف في العرض، ويحفظ الأثاث حسب اختيارك دون لون التحديد. يمكن استيراده في Blender من File → Import → glTF 2.0؛ ليس ملف MASAR لاسترجاع المخطط. لا يحتاج حسابًا أو عامل رندر.</p>';
    parent.append(root);
    const png=root.querySelector('#render-save-png'),glb=root.querySelector('#render-save-glb'),status=root.querySelector('#render-download-state');
    const inputs=['#render-finish','#render-quality','#render-room','#render-furniture'].map(id=>host.querySelector(id));
    let disposed=false,source=null,fingerprint='',epoch=0,busy=false;
    const alive=()=>!disposed&&isAlive()&&root.isConnected;
    function update(){if(!alive())return;png.disabled=glb.disabled=!source||busy;}
    function invalidate(){epoch++;source=null;fingerprint='';if(alive()){status.textContent='تغيّرت إعدادات العرض؛ اضغط «معاينة بالخامات» لتحديثه قبل التنزيل.';host.querySelector('#render-canvas').dataset.exportReady='false';update();}}
    for(const input of inputs)input.addEventListener('change',invalidate);
    function same(token,expected){return alive()&&token===epoch&&source&&JSON.stringify(getSnapshot())===expected;}
    function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.hidden=true;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
    async function run(kind) {
        if(busy||!source||!alive())return;
        const token=epoch,expected=fingerprint,s=source;
        try {
            if(!same(token,expected))throw Error('تغيّر المشروع أو إعداداته؛ أعد المعاينة قبل التنزيل.');
            const descriptor=visualExportDescriptor(s),v=getViewer();if(!v)throw Error('عارض الخامات غير جاهز.');
            busy=true;update();status.textContent='جارٍ تجهيز الملف محليًا؛ لم يتغير المشروع…';
            let blob;
            if(kind==='png')blob=await v.capturePNG({width:s.resolution.width,height:s.resolution.height,revisionId:s.source.revisionId,modelId:s.source.modelId});
            else {const buffer=await v.exportGLB(descriptor);inspectLocalGLB(buffer);blob=new Blob([buffer],{type:'model/gltf-binary'});}
            if(!same(token,expected))throw Error('لم يُنزّل الملف لأن المصدر تغيّر أو أُغلقت المعاينة؛ أعد المحاولة من النسخة الحالية.');
            if(!(blob instanceof Blob)||!blob.size)throw Error('لم ينتج ملف قابل للتنزيل.');
            const ref=s.source.revisionId.replace(/[^A-Za-z0-9_-]/g,'').slice(0,20)||'revision';
            save(blob,`MASAR-${kind==='png'?'Preview':'Model'}-${ref}.${kind}`);
            status.textContent=kind==='png'?'جُهزت صورة المعاينة من المتصفح؛ ليست رندر Blender.':'جُهز GLB كامل بالسقف والخامات؛ افتحه في Blender عبر استيراد glTF 2.0.';
        } catch(error){if(alive()){status.textContent=error.message||'تعذر تجهيز الملف.';reportError(error);}}
        finally{busy=false;update();}
    }
    const onPNG=()=>run('png'),onGLB=()=>run('glb');png.addEventListener('click',onPNG);glb.addEventListener('click',onGLB);
    return {
        setSource(spec){if(!alive())return;epoch++;source=structuredClone(spec);fingerprint=JSON.stringify(spec);status.textContent='جاهز لتنزيل النسخة المعروضة من جهازك؛ دون رندر سحابي.';host.querySelector('#render-canvas').dataset.exportReady='true';update();},
        invalidate,
        dispose(){disposed=true;epoch++;source=null;for(const input of inputs)input.removeEventListener('change',invalidate);png.removeEventListener('click',onPNG);glb.removeEventListener('click',onGLB);}
    };
}
