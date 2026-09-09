from pathlib import Path
import subprocess
root=Path('masar-studio')
expected={'shared/model.js':'03b00d114cc6cdf264e84adcff62b9aac3c03231','src/app.js':'3e5312641232bcae7b2530346da8d6899da03251'}
for name,sha in expected.items():
    assert subprocess.check_output(['git','hash-object',str(root/name)],text=True).strip()==sha,'Unexpected source: '+name

def replace(text,old,new):
    assert text.count(old)==1, 'Patch match count '+str(text.count(old))+': '+old[:100]
    return text.replace(old,new,1)

p=root/'shared/model.js';s=p.read_text()
start=s.index('    const projectType = /(?:مستودع|مخزن|warehouse)/')
end=s.index('\n',start)
s=s[:start]+"    const projectType = customerProjectType(t);"+s[end:]
s=replace(s,"    const dim = t.match(/([-+]?\\d+(?:\\.\\d+)?)\\s*(?:×|x|\\*|في|بـ?)\\s*([-+]?\\d+(?:\\.\\d+)?)/);", "    const dim = t.match(/([-+]?\\d+(?:\\.\\d+)?)\\s*(?:متر\\s*(?:واجهه|عرض)?\\s*)?(?:×|x|\\*|في|بـ?)\\s*([-+]?\\d+(?:\\.\\d+)?)/);")
s=replace(s,"        projectType, priority, style, title: titles[projectType],", "        projectType, priority, style, title: titles[projectType], buildingArea: customerAreaBudget(t),")
s=replace(s,"    return brief;", "    if (/(?:الاولو[يه]+|اولوي[هت])[^.\\n]{0,100}(?:شاليه|حديق|مسبح|حوش)/.test(t)) brief.priority='outdoor';\n    return brief;")
old="    return { schemaVersion: VERSION, id: uid(), title: brief.title, authoring, site:"
s=replace(s,old,"    const generated = { schemaVersion: VERSION, id: uid(), title: brief.title, authoring, site:")
s=replace(s,"generatedVariant: variant }, createdAt: new Date().toISOString() };\n}","generatedVariant: variant }, createdAt: new Date().toISOString() };\n    return applyCustomerBudget(generated, brief);\n}")
s=replace(s,"['floors', 'bedrooms', 'site', 'feature', 'adjacency', 'unresolved', 'custom'].includes(r.type)","['floors', 'bedrooms', 'site', 'feature', 'adjacency', 'unresolved', 'custom', 'building-area'].includes(r.type)")
s=replace(s,"export function requirementStatus(m, req) {", "export function requirementStatus(m, req) {\n    if(req.type==='building-area'){const a=conceptEnvelopeArea(m),bounds=req.value;const valid=Array.isArray(bounds)&&bounds.length===2&&bounds.every(Number.isFinite)&&bounds[0]>0&&bounds[1]>=bounds[0];return {measurable:true,satisfied:valid&&a>=bounds[0]-.05&&a<=bounds[1]+.05,detail:`غلاف مفاهيمي محافظ يشمل سماكات الجدران: ${a} م²؛ ليس مسطح رخصة.`};}")
s=replace(s,"        if (req.type === 'feature' || req.type === 'adjacency') {", "        if (req.type === 'building-area') {const status=requirementStatus(m,req);add(req.id,status.satisfied?'checked':'error',req.label+': '+status.detail,[],'requirements');}\n        if (req.type === 'feature' || req.type === 'adjacency') {")
s += '\n'+Path('.masar-ops/customer-model-snippet.js').read_text()
p.write_text(s)

p=root/'src/app.js';s=p.read_text()
s=replace(s,"function reportError(e) { console.warn('[MASAR]', e.message); toast(e.message || 'تعذّرت العملية؛ لم نطبق تغييرًا.', true); }", """function reportError(e) {
    const message=e.message || 'تعذّرت العملية؛ لم نطبق تغييرًا.';
    console.warn('[MASAR]',message);
    if($('#modal')?.open){
        let box=$('#modal-error');
        if(!box){box=document.createElement('div');box.id='modal-error';box.className='notice error';box.setAttribute('role','alert');box.tabIndex=-1;$('#modal-content').prepend(box);}
        box.hidden=false;box.textContent=message;box.focus({preventScroll:true});box.scrollIntoView({block:'nearest'});
    }else toast(message,true);
}""")
s=replace(s,"state.pendingBrief = brief;", "state.pendingBrief = brief; state.draftPrompt = brief.prompt;")
s=replace(s,"واحد.</textarea>","واحد.</textarea>") if "واحد.</textarea>" in s else s
# Preserve the original text on Back instead of requiring re-entry.
s=replace(s,'الشارع جنوب.\"></textarea>','الشارع جنوب.\">${E(state.draftPrompt || \'\')}</textarea>')
s=replace(s,'<form id="brief-form"><div class="brief-confirm-grid">','<form id="brief-form"><div id="modal-error" class="notice error" role="alert" tabindex="-1" hidden></div><div class="brief-confirm-grid">')
needle='<div class="feature-checks"><label class="check-line"><input type="checkbox" name="elevator"'
addition='''<div class="brief-confirm-grid area-budget"><label class="field"><span>الحد الأدنى للمباني م² — اختياري</span><input type="number" name="areaMin" min="1" max="20000" step="0.1" value="${brief.buildingArea?.min ?? ''}"></label><label class="field"><span>الحد الأعلى للمباني م² — اختياري</span><input type="number" name="areaMax" min="1" max="20000" step="0.1" value="${brief.buildingArea?.max ?? ''}"></label></div><p class="notice">قيد المساحة لا يُحذف ولا يُتجاوز تلقائيًا. في المخطط المدمج نقيس غلاف الدور الأرضي والجدران ودورة المياه الخارجية تقديريًا؛ هذا ليس مسطح رخصة. عدد الأدوار وجهة الشارع افتراضان ما لم تذكرهما أو تعدّلهما.</p>${brief.buildingArea?'<details class="notice"><summary>حدود توزيع هذا البرنامج ضمن المساحة</summary><p>مقترح مدمج من دور واحد وثلاث غرف نوم مع جناح رئيسي وخدمات وضيافة وموقف ومسبح وجلسات. المقاسات مبدئية وليست ضمانًا لراحة كل مساحة. الجزيرة ونوع الزجاج والمنزلق والتهوية والخصوصية الصوتية وأثاث البرجولة والشواء تحتاج مراجعة؛ لا تعتبر منجزة بمجرد توليد الكتل.</p></details>':''}<div class="feature-checks"><label class="check-line"><input type="checkbox" name="elevator"'''
s=replace(s,needle,addition)
s=replace(s,'**استراتيجية توزيع مفاهيمية**','<strong>استراتيجية توزيع مفاهيمية</strong>')
s=replace(s,"            brief.unresolved=[];", """            if(!data.has('confirm')) throw Error('أكد مراجعة المدخلات أولًا.');
            if(get('areaMin')||get('areaMax')) {
                const min=Number(get('areaMin')),max=Number(get('areaMax'));
                if(!get('areaMin')||!get('areaMax')||!Number.isFinite(min)||!Number.isFinite(max)||min<=0||max<min) throw Error('أدخل حدًا أدنى موجبًا للمباني وحدًا أعلى لا يقل عنه.');
                brief.buildingArea={min,max,source:'confirmed',metric:'conservative-concept-ground-envelope'};
            } else brief.buildingArea=null;
            brief.unresolved=[];""")
needle="document.addEventListener('submit', async (e) =>"
extra="""// Native constraint-validation events do not trigger submit. Show them inside the modal,
// not behind the top-layer dialog, and preserve the user's input.
document.addEventListener('invalid',e=>{if(e.target.closest('#brief-form')){e.preventDefault();const label=e.target.closest('label')?.querySelector('span')?.textContent||e.target.name;reportError(Error(label+': '+e.target.validationMessage));}},true);
document.addEventListener('change',e=>{
    const f=e.target.closest('#brief-form');if(!f||e.target.name!=='projectType')return;
    const residential=['villa','chalet'].includes(e.target.value),beds=f.elements.namedItem('bedrooms'),offices=f.elements.namedItem('offices');
    if(residential&&Number(beds.value)<1)beds.value=String(state.pendingBrief?.bedrooms||3);
    if(e.target.value==='office'&&Number(offices.value)<1)offices.value=String(state.pendingBrief?.offices||4);
    beds.min=residential?'1':'0';
    const title=f.elements.namedItem('title'),names={villa:'فيلا الفناء',chalet:'شاليه الفناء',office:'مكاتب مسار',warehouse:'مستودع مسار',retail:'مساحة تجارية'};
    if(Object.values(names).includes(title.value))title.value=names[e.target.value];
});
"""
s=replace(s,needle,extra+needle)
p.write_text(s)
p=root/'src/style.css';p.write_text(p.read_text()+'''\n/* Customer generation: errors stay in the modal top layer and mobile fields do not zoom. */
#modal-error { scroll-margin: 16px; border: 2px solid #9b3c32; background: #fff2ef; color: #80291f; }
#modal-error[hidden] { display: none; }
#brief-form input, #brief-form select { font-size: 16px; min-width: 0; }
#brief-form .area-budget { margin-block: 16px; }
#brief-form details summary { cursor: pointer; font-weight: 700; }
''')
# Preserve request-specific clauses as review requirements in the new compact scheme.
# Only canonical model and UI files are changed; no data migrations or provider settings.
for name in ['shared/model.js','src/app.js']:
    subprocess.run(['node','--check',str(root/name)],check=True)
