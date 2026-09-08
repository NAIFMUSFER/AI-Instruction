"""One-shot, guarded repair of the audited 23bf68d application. Never runs at app startup."""
from pathlib import Path
import subprocess
root=Path('masar-studio')
for file,expected in [('shared/model.js','03b00d114cc6cdf264e84adcff62b9aac3c03231'),('src/app.js','3e5312641232bcae7b2530346da8d6899da03251')]:
    assert subprocess.check_output(['git','hash-object',str(root/file)],text=True).strip()==expected, 'Unexpected source: '+file

def change(s,old,new):
    assert s.count(old)==1, 'Ambiguous/missing patch anchor: '+old[:120]
    return s.replace(old,new,1)

p=root/'shared/model.js';s=p.read_text()
s=change(s,'export function understand(prompt) {',r'''// Project identity comes from the requested building, not a pantry mentioned later.
function requestedProjectType(t) {
    const heading=t.split(/[،.\n]/)[0];
    const classify=x=>/شاليه/.test(x)?'chalet':/(?:فيلا|فله|منزل|\bvilla\b)/.test(x)?'villa':/(?:مستودع|مخزن|warehouse)/.test(x)?'warehouse':/(?:مكاتب|مكتب اداري|office)/.test(x)?'office':/(?:متجر|محل تجاري|تجز[يئ]ه|retail)/.test(x)?'retail':null;
    return classify(heading)||classify(t)||'villa';
}
function requestedBuildingArea(t) {
    const n='(\\d+(?:\\.\\d+)?)', sep='\\s*(?:–|—|-|الي|الى)\\s*';
    const pair=t.match(new RegExp(n+sep+n+'\\s*(?:م(?:تر)?\\s*(?:²|2|مربع)|m2)\\s*(?:مباني|بناء|مسطح)'))
      ||t.match(new RegExp('مساحه\\s*(?:ال)?(?:بناء|مبني|مباني)[^\\d\\n]{0,25}'+n+sep+n));
    if(pair)return {min:Number(pair[1]),max:Number(pair[2])};
    const one=t.match(/مساحه\s*(?:ال)?(?:بناء|مبني|مباني)[^\d\n]{0,25}(\d+(?:\.\d+)?)\s*(?:م|m)/);
    return one?{min:Number(one[1]),max:Number(one[1])}:null;
}
export function understand(prompt) {''')
a=s.index('    const dim = t.match(');z=s.index('    const residential = ',a)
s=s[:a]+r'''    const dim = t.match(/([-+]?\d+(?:\.\d+)?)\s*(?:متر|م)?\s*(?:واجهه|عرض)?\s*(?:×|x|\*|في|بـ?)\s*([-+]?\d+(?:\.\d+)?)/);
    const projectType = requestedProjectType(t), requestedArea=requestedBuildingArea(t);
'''+s[z:]
s=change(s,"        projectType, priority, style, title: titles[projectType],","        projectType, priority, style, title: titles[projectType],\n        buildingAreaMin: requestedArea?.min ?? null, buildingAreaMax: requestedArea?.max ?? null,\n        requestedDetails: String(prompt).split(/\\n\\s*\\n/).filter(Boolean).flatMap(x=>x.match(/[\\s\\S]{1,800}/g)||[]).slice(0,55),")
s=change(s,"intents: [], unresolved: []","intents: [], unresolved: []") if False else s
s=change(s,"    if (brief.width < 12", "    brief.sources.buildingArea = requestedArea ? 'requested' : 'unspecified';\n    if (/(?:^|[ ،\\n])موقف سيارات/.test(t) && parking.source === 'assumed') {brief.parking=1;brief.sources.parking='requested';}\n    if (brief.width < 12")
a=s.index("    if (/(?:مطبخ|معيش)");z=s.index('    return brief;',a)
s=s[:a]+r'''    for(const [re,kind,label] of [
        [/(?:معيشه|الصاله)[^،.\n]{0,65}(?:حديق|مسبح|اطلال)/,'living','المعيشة مرتبطة بالجهة الخارجية'],
        [/مطبخ[^،.\n]{0,34}(?:حديق|مسبح|خارجي|اطلال)/,'kitchen','المطبخ مرتبط بالجهة الخارجية']
    ]) if(re.test(t)) brief.intents.push({type:'garden-edge',subjectKind:kind,label,source:'requested'});
'''+s[z:]
old="    const bx = round(sideSetback), by = round(endSetback), bw = round(W - sideSetback * 2), bd = round(D - endSetback * 2), hw = Math.max(1.5, Math.min(2.2, bw * .08));"
new=r'''    const bx = round(sideSetback), by = round(endSetback);
    let bw=round(W-sideSetback*2), bd=round(D-endSetback*2);
    const boundedArea=brief.buildingAreaMin!=null||brief.buildingAreaMax!=null;
    if(boundedArea){
        const lo=brief.buildingAreaMin,hi=brief.buildingAreaMax;
        if(![lo,hi].every(Number.isFinite)||lo<40||hi<lo||hi>50000)throw Error('راجع نطاق مساحة البناء: الحد الأدنى 40 م²، والحد الأعلى يجب ألا يقل عن الأدنى.');
        const available=bw*bd*brief.floors;
        if(lo>available+.05)throw Error('مساحة البناء المطلوبة لا تتسع داخل توزيع الموقع المفاهيمي. عدّل نطاق المساحة أو الأبعاد.');
        const target=Math.min((lo+hi)/2,available)/brief.floors,scale=Math.sqrt(target/(bw*bd));
        bw=round(bw*scale);bd=round(bd*scale);
    }
    const hw=Math.max(1.2,Math.min(2.2,bw*.08)),compactResidential=boundedArea&&residential&&brief.floors===1;
    const explicitStair=/(?:درج|سلم|سلالم)/.test(normalizeText(brief.prompt))&&!/(?:بدون|دون|لا اريد)\s*(?:درج|سلم|سلالم)/.test(normalizeText(brief.prompt));
    const hasCore=brief.floors>1||brief.elevator||explicitStair;'''
# Keep the original corridor dimensions outside the newly supported bounded-area case.
new=new.replace('const hw=Math.max(1.2,Math.min(2.2,bw*.08))','const hw=Math.max(boundedArea?1.2:1.5,Math.min(2.2,bw*.08))')
s=change(s,old,new)
old="        const r = [], prefix = `l${f}`, configs = cfgFor(f), leftCfg = configs.filter((_, i) => i % 2 === 0), rightCfg = configs.filter((_, i) => i % 2 === 1);"
new=r'''        const r = [], prefix = `l${f}`, configs = cfgFor(f);
        let leftCfg=configs.filter((_,i)=>i%2===0),rightCfg=configs.filter((_,i)=>i%2===1);
        if(compactResidential){
            const bedrooms=configs.filter(c=>c.kind==='bedroom');
            leftCfg=['majlis','kitchen','living'].map(kind=>configs.find(c=>c.kind===kind)).filter(Boolean);
            if(/(?:ضيوف|الضيوف)/.test(brief.prompt)&&/(?:مياه|حمام)/.test(brief.prompt)){
                const guest={name:'دورة مياه الضيوف',kind:'bath'};configs.push(guest);leftCfg.splice(1,0,guest);
            }
            rightCfg=[...bedrooms,configs.find(c=>c.kind==='bath')].filter(Boolean);
            if(bedrooms.length>1){rightCfg.splice(rightCfg.indexOf(bedrooms[0]),1);rightCfg.push(bedrooms[0]);}
            const master=bedrooms[0];if(master&&/(?:master|رئيسيه|ماستر)/.test(normalizeText(brief.prompt)))master.name='غرفة النوم الرئيسية';
            const living=leftCfg.find(c=>c.kind==='living');if(living&&/طعام/.test(brief.prompt))living.name='المعيشة ومنطقة الطعام';
        }
        const weight=c=>!compactResidential?1:({bedroom:14,majlis:18,living:26,kitchen:12,bath:6}[c.kind]||8);
        const bounds=(cfg,i,depth)=>{const total=cfg.reduce((n,c)=>n+weight(c),0),before=cfg.slice(0,i).reduce((n,c)=>n+weight(c),0);return [round(by+depth*before/total),round(by+depth*(before+weight(cfg[i]))/total)];};'''
s=change(s,old,new)
s=change(s,'const coreD = Math.min(4.8, Math.max(3.6, bd * .28))','const coreD = hasCore ? Math.min(4.8, Math.max(3.6, bd * .28)) : 0')
s=change(s,'const y1 = round(by + i * bd / leftCfg.length), y2 = round(by + (i + 1) * bd / leftCfg.length);','const [y1,y2] = bounds(leftCfg,i,bd);')
s=change(s,'const y1 = round(by + i * rightUsableD / Math.max(rightCfg.length, 1)), y2 = round(by + (i + 1) * rightUsableD / Math.max(rightCfg.length, 1));','const [y1,y2] = bounds(rightCfg,i,rightUsableD);')
s=change(s,"        } else { const stair = room(","        } else if(hasCore) { const stair = room(")
# A requested area is a measured constraint, not a text-only claim; details remain visible for human review.
s=change(s,"        ...(brief.elevator ? [{ id: 'r-elevator'", "        ...(boundedArea ? [{id:'r-building-area',label:`مساحة بناء مفاهيمية ${brief.buildingAreaMin}–${brief.buildingAreaMax} م²`,type:'custom',metric:'floor-area',range:[brief.buildingAreaMin,brief.buildingAreaMax],source:brief.sources.buildingArea||'requested',locked:true}] : []),\n        ...(brief.requestedDetails||[]).map((label,i)=>({id:`r-detail-${i}`,label,type:'custom',source:'requested',locked:true})),\n        ...(brief.elevator ? [{ id: 'r-elevator'")
s=change(s,'export function requirementStatus(m, req) {',r'''export function requirementStatus(m, req) {
    if(req.type==='floors')return {measurable:true,satisfied:m.levels.length===req.value,detail:`${m.levels.length} أدوار في النموذج`};
    if(req.type==='bedrooms'){const count=m.levels.flatMap(l=>l.rooms).filter(r=>r.kind==='bedroom').length;return {measurable:true,satisfied:count===req.value,detail:`${count} غرف نوم في النموذج`};}
    if(req.type==='site')return {measurable:true,satisfied:m.site.width===req.value?.[0]&&m.site.depth===req.value?.[1],detail:`${m.site.width} × ${m.site.depth} م`};
    if(req.type==='custom'&&req.metric==='floor-area'&&req.range?.length===2&&req.range.every(Number.isFinite)){
        const actual=totals(m).floorArea;return {measurable:true,satisfied:actual>=req.range[0]-.05&&actual<=req.range[1]+.05,detail:`${actual} م² حسب حدود الغرف المفاهيمية؛ ليست حصرًا تنفيذيًا شاملاً لسماكات الجدران`};
    }''')
s=change(s,"        if (req.type === 'unresolved' || req.type === 'custom')", "        if(req.metric==='floor-area'){const status=requirementStatus(m,req);add(req.id,status.satisfied?'checked':'error',`${req.label}: ${status.detail}`,[],'requirements');}\n        if (req.type === 'unresolved' || req.type === 'custom' && req.metric!=='floor-area')")
p.write_text(s)

p=root/'src/app.js';s=p.read_text()
s=change(s,"function reportError(e) { console.warn('[MASAR]', e.message); toast(e.message || 'تعذّرت العملية؛ لم نطبق تغييرًا.', true); }",r'''function reportError(e) {
    const message=e.message||'تعذّرت العملية؛ لم نطبق تغييرًا.';console.warn('[MASAR]',message);
    if($('#modal').open){
        let box=$('#modal-error');if(!box){box=document.createElement('div');box.id='modal-error';box.className='notice error';box.setAttribute('role','alert');box.tabIndex=-1;$('#modal-content').prepend(box);}
        box.textContent=message;box.scrollIntoView({block:'nearest'});box.focus({preventScroll:true});
    } else toast(message,true);
}''')
s=change(s,'**استراتيجية توزيع مفاهيمية**','<strong>استراتيجية توزيع مفاهيمية</strong>')
s=change(s,'</div><div class="feature-checks">',r'''<label class="field"><span>مساحة البناء المطلوبة — من (م²)</span><input type="number" name="buildingAreaMin" min="40" max="50000" step="0.1" value="${brief.buildingAreaMin??''}">${source('buildingArea')}</label><label class="field"><span>مساحة البناء المطلوبة — إلى (م²)</span><input type="number" name="buildingAreaMax" min="40" max="50000" step="0.1" value="${brief.buildingAreaMax??''}"><small>حدود مفاهيمية للغرف؛ اترك الحقلين فارغين عند عدم تحديد المساحة.</small></label></div><div class="feature-checks">''')
s=change(s,'${brief.unresolved.map(s=>',r'''${brief.buildingAreaMax?'<div class="notice warn">تقييد المساحة لا يعني أن جميع تفاصيل البرنامج تتسع تلقائيًا. الحمام الخاص وغرفة الملابس والبانتري والغسيل والبرجولة والشواء والحمام الخارجي تحتاج تطويرًا ومراجعة منفصلة؛ لا نعدّ حفظ النص تنفيذًا لهذه العناصر.</div>':''}<details class="notice"><summary>الطلب الأصلي كاملًا — التفاصيل غير المقاسة محفوظة للمراجعة</summary><div class="original-prompt">${E(brief.prompt)}</div></details>${brief.unresolved.map(s=>''')
s=change(s,"            brief.unresolved=[];", "            brief.buildingAreaMin=get('buildingAreaMin')?Number(data.get('buildingAreaMin')):null;\n            brief.buildingAreaMax=get('buildingAreaMax')?Number(data.get('buildingAreaMax')):null;\n            if((brief.buildingAreaMin===null)!==(brief.buildingAreaMax===null))throw Error('أدخل الحدين الأدنى والأعلى لمساحة البناء، أو اتركهما معًا فارغين.');\n            brief.unresolved=[];")
# Never lose the entered description when navigating back from confirmation.
s=change(s,'maxlength="12000" required placeholder="مثال:', 'maxlength="12000" required placeholder="مثال:') if False else s
s=change(s,'الشارع جنوب."></textarea>','الشارع جنوب.">${E(state.pendingBrief?.prompt||\'\')}</textarea>')
# Native form errors must be visible in the dialog top layer, not behind its backdrop.
s=change(s,"document.addEventListener('submit', async (e) =>",r'''document.addEventListener('invalid',e=>{
    if(e.target.closest('#modal')){const name=e.target.closest('label')?.querySelector('span')?.textContent||'القيم المطلوبة';reportError(Error('راجع '+name+'؛ أدخل قيمة ضمن النطاق المعروض وأكّد المراجعة.'));}
},true);
document.addEventListener('change',e=>{
    if(!e.target.matches('#brief-form select[name="projectType"]'))return;
    const form=e.target.form,type=e.target.value,residential=['villa','chalet'].includes(type),beds=form.elements.bedrooms,offices=form.elements.offices;
    beds.min=residential?'1':'0';offices.min=type==='office'?'1':'0';
    // A derived zero is not a residential choice. Re-read the original numeric request.
    if(residential&&Number(beds.value)===0){const original=state.pendingBrief.prompt;const match=original.match(/(?:3|٣)\s*غرف/);const parsed=understand(type==='chalet'?'شاليه، '+original:'فيلا، '+original);beds.value=String(parsed.bedrooms||3);}
    if(type==='office'&&Number(offices.value)===0)offices.value='4';
});
document.addEventListener('submit', async (e) =>''')
s=change(s,'const match=original.match(/(?:3|٣)\s*غرف/);','')
p.write_text(s)
# Existing service worker must never serve stale patched app modules.
p=root/'public/sw.js';s=p.read_text();s=change(s,"const CACHE='masar-4.1.0-shell-v3';","const CACHE='masar-4.1.0-shell-chalet-quality-1';");p.write_text(s)
print('Applied guarded quality patch; no deployment performed.')
