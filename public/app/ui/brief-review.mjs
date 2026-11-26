import {analyzeBrief,asciiNumberText,buildBriefProgram,metricLabels,normalizeNumberText,requirementKey,requirementLabel} from '../core/brief-program.mjs';
import {readResidential} from '../core/residential-program.mjs';

const briefStarters = {
  residential: [
    {id:'apartments', label:'عمارة بشقتين في كل دور', text:'أبغى عمارة سكنية في الرياض. عرض الأرض ٢٠ متر وعمق الأرض ٢٥ متر. عدد الأدوار ٣ شاملة الأرضي.\nأبغى شقتين في كل دور، ومدخل كل شقة من بسطة الدرج المشترك. خلّ غرف النوم بعيدة عن مدخل الضيوف.'},
    {id:'villa', label:'فيلا عائلية', text:'أبغى فيلا عائلية في جدة. عرض الأرض ١٨ متر وعمق الأرض ٢٨ متر. عدد الأدوار ٢ شاملة الأرضي.\nأبغى مجلس الضيوف قريب من المدخل، وصالة الأسرة تطل على الحديقة. خلّ غرف النوم في الدور العلوي والمطبخ قريب من غرفة الطعام.'},
    {id:'courtyard', label:'عمارة بفناء داخلي', text:'أبغى عمارة سكنية حول فناء مفتوح للسماء في الرياض. عرض الأرض ٢٤ متر وعمق الأرض ٢٨ متر. عدد الأدوار ٤ شاملة الأرضي.\nفي كل دور شقتان. أبغى المدخل من الشمال، وممر يربط الدرج بأبواب الشقق حول الفناء.'},
  ],
  warehouse: [
    {id:'distribution', label:'مستودع توزيع', text:'أبغى مستودع توزيع في الدمام. عرض الأرض ٦٠ متر وعمق الأرض ٨٠ متر. المستودع من دور واحد.\nخلّ الاستلام في الواجهة الشرقية والشحن في الغربية، ومنطقة التجهيز قريبة من الشحن. أبغى مسار مشاة منفصل عن حركة الرافعات.'},
    {id:'storage', label:'مستودع قطع غيار', text:'أبغى مستودع قطع غيار في الرياض. عرض الأرض ٤٠ متر وعمق الأرض ٦٠ متر. المستودع من دور واحد.\nأحتاج رصيف استلام، ورفوفًا للقطع الصغيرة، ومنطقة فحص للمواد المرتجعة. خلّ مكتب الصرف قريب من مدخل العملاء.'},
  ],
};

// Owns the existing requirements form only. No network, model or approval access.
export function createBriefEditor(root,{storageKey,onError}) {
  const $=id=>root.querySelector('#'+id);
  // The land (site) and the building are separate sizes (owner decision 3).
  const fields={site_width_m:'cwWidth',site_depth_m:'cwDepth',level_count:'cwLevels',building_width_m:'cwBldWidth',building_depth_m:'cwBldDepth'};
  const optional=new Set(['building_width_m','building_depth_m']);
  // Building width and depth sit beside the land fields; created here so the
  // workspace shell markup stays unchanged.
  const buildingRow=document.createElement('div');
  buildingRow.className='cw-fields';buildingRow.id='cwBuildingFields';
  for(const [id,label] of [['cwBldWidth','عرض المبنى (م)'],['cwBldDepth','عمق المبنى (م)']]){
    const cell=document.createElement('div'),caption=document.createElement('label'),field=document.createElement('input');
    caption.htmlFor=id;caption.textContent=label;
    Object.assign(field,{id,type:'text',inputMode:'decimal',autocomplete:'off',placeholder:'بحجم الأرض'});
    cell.append(caption,field);buildingRow.append(cell);
  }
  $('cwLevels').closest('.cw-fields').after(buildingRow);
  let analysis=null,savedRequirements=[];
  function el(tag,text,parent,cls){const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;if(parent)parent.append(node);return node;}
  const brief=$('cwBrief');
  const starterGroup=el('fieldset',null,null,'cw-brief-starters');
  starterGroup.id='cwBriefStarters';
  el('legend','اختر وصفًا وعدّله',starterGroup);
  const starterButtons=el('div',null,starterGroup,'cw-starter-buttons');
  const replacement=el('div',null,starterGroup,'cw-starter-preview');
  replacement.hidden=true;
  const previewText=el('p',null,replacement);
  const replace=el('button','استبدال الوصف بهذا النص',replacement);
  const keep=el('button','الاحتفاظ بوصفي',replacement);
  replace.type=keep.type='button';
  replace.id='cwReplaceBrief';keep.id='cwKeepBrief';
  root.querySelector('label[for="cwBrief"]').before(starterGroup);

  const starterFieldIds=[...Object.values(fields),'cwUnits','cwUnitsScope','cwCity'];
  // A starter that names its city fills «المدينة» too, while that field is blank or starter-filled.
  const CITY=/(?:^|[\s،.])(?:في|بمدينة|مدينة)\s+(الرياض|جدة|الدمام|مكة المكرمة|مكة|المدينة المنورة|الخبر|الطائف|تبوك|أبها|بريدة|حائل|جازان|نجران|الأحساء|الجبيل|ينبع)(?![\p{L}])/u;
  let linkedFields=new Set(), pendingStarter=null;
  function closeStarterPreview(){
    replacement.hidden=true;pendingStarter=null;
  }
  function applyStarter(starter){
    closeStarterPreview();
    // Only follow blank fields and fields already supplied by a starter.
    // Values typed by the user keep their authority during a template switch.
    for(const id of Object.values(fields))if(!$(id).value)linkedFields.add(id);
    if($('cwType').value==='residential'&&!$('cwUnits').value){
      linkedFields.add('cwUnits');linkedFields.add('cwUnitsScope');
    }
    if($('cwCity')&&!$('cwCity').value)linkedFields.add('cwCity');
    brief.value=starter.text;
    brief.dispatchEvent(new Event('input',{bubbles:true}));
    brief.focus();
  }
  function showStarters(){
    closeStarterPreview();
    starterButtons.replaceChildren();
    for(const starter of briefStarters[$('cwType').value]||[]){
      const button=el('button',starter.label,starterButtons);
      button.type='button';button.dataset.briefStarter=starter.id;
      button.addEventListener('click',()=>{
        if(!brief.value.trim()||brief.value===starter.text){applyStarter(starter);return;}
        pendingStarter=starter;previewText.textContent=starter.text;
        replacement.hidden=false;replace.focus();
      });
    }
    const custom=el('button','اكتب وصفك بنفسك',starterButtons);
    custom.type='button';custom.dataset.briefStarter='custom';
    custom.addEventListener('click',()=>{closeStarterPreview();brief.focus();});
  }
  replace.addEventListener('click',()=>{if(pendingStarter)applyStarter(pendingStarter);});
  keep.addEventListener('click',()=>{closeStarterPreview();brief.focus();});
  $('cwType').addEventListener('change',showStarters);
  showStarters();

  function syncStarterFields(){
    if(!linkedFields.size)return;
    const {candidates}=analyzeBrief(brief.value);
    for(const [metric,id] of Object.entries(fields)){
      if(!linkedFields.has(id))continue;
      const values=candidates.filter(c=>c.metric===metric&&c.source==='requested');
      $(id).value=values.length===1?values[0].expected:'';
    }
    if($('cwType').value==='residential'){
      const parsed=readResidential(brief.value);
      if(linkedFields.has('cwUnits'))$('cwUnits').value=parsed.units??'';
      if(linkedFields.has('cwUnitsScope'))$('cwUnitsScope').value=parsed.scope||'total';
      if(linkedFields.has('cwCity')&&$('cwCity'))$('cwCity').value=CITY.exec(brief.value)?.[1]||'';
      // The residential editor owns its draft and the live unit-count summary.
      $('cwUnits').dispatchEvent(new Event('change',{bubbles:true}));
    }
  }
  const read=el('button','قراءة المتطلبات من الوصف');read.type='button';read.id='cwReadBrief';
  const panel=el('section',null,null,'cw-brief-review');panel.id='cwBriefReview';
  el('h3','مراجعة الوصف',panel);
  const notice=el('p','استخرج الأبعاد والأعداد المكتوبة، ثم راجعها قبل إضافتها. بقية وصفك يبقى محفوظًا ويحتاج مراجعتك.',panel,'cw-muted');
  notice.id='cwBriefNotice';notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');
  const cards=el('div',null,panel,'cw-brief-candidates');cards.id='cwBriefCandidates';
  const questionTitle=el('h3','أسئلة قبل التوليد',panel);
  const questions=el('ul',null,panel);questions.id='cwBriefQuestions';
  const preview=el('details',null,panel);el('summary','القيم التي سيستخدمها المقترح ومصادرها',preview);
  const sources=el('div',null,preview);sources.id='cwBriefSources';
  $('cwBrief').after(read,panel);

  function rows(){return [...$('cwRequirements').children].map(row=>({metric:row.querySelector('select').value,role:row.querySelector('[data-role]').value,expected:row.querySelector('[data-value]').value}));}
  function input(){const residential=$('cwType').value==='residential';return {brief:$('cwBrief').value,type:$('cwType').value,width:$('cwWidth').value,depth:$('cwDepth').value,levels:$('cwLevels').value,
    buildingWidth:residential?$('cwBldWidth').value:'',buildingDepth:residential?$('cwBldDepth').value:'',rows:rows(),savedRequirements};}
  function draft(){
    const data=input();
    try{localStorage.setItem(storageKey(),JSON.stringify({brief:data.brief,type:data.type,w:data.width,d:data.depth,levels:data.levels,bw:$('cwBldWidth').value,bd:$('cwBldDepth').value,rows:data.rows,savedRequirements,starterFields:[...linkedFields]}));}catch(e){}
    $('cwConfirmed').checked=false;
  }
  function add(data={}){
    const row=el('tr',null,$('cwRequirements'));
    const cell=label=>{const td=el('td',null,row);td.dataset.label=label;return td;};
    const select=el('select',null,cell('المتطلب'));select.setAttribute('aria-label','نوع المتطلب');
    for(const [key,label] of Object.entries(metricLabels)){if(fields[key])continue;const o=el('option',label,select);o.value=key;}
    if(data.metric&&!Object.hasOwn(metricLabels,data.metric)){const o=el('option',data.metric+' · متطلب محفوظ',select);o.value=data.metric;}
    select.value=data.metric||'room_count';
    const role=el('select',null,cell('الاستخدام'));role.dataset.role='';role.setAttribute('aria-label','استخدام الفراغ');
    const uses={bedroom:'غرفة نوم',living:'صالة',kitchen:'مطبخ',bathroom:'دورة مياه',majlis:'مجلس',corridor:'ممر',stairs:'درج',elevator:'مصعد',office:'مكتب',storage:'تخزين',staging:'تجهيز',receiving:'استلام',shipping:'شحن'};
    if(data.role&&!Object.hasOwn(uses,data.role))uses[data.role]=data.role;
    for(const [id,label] of Object.entries(uses)){const o=el('option',label,role);o.value=id;}role.value=data.role||'bedroom';
    const expected=el('input',null,cell('القيمة'));expected.dataset.value='';expected.type='text';expected.inputMode='decimal';expected.autocomplete='off';expected.setAttribute('aria-label','القيمة المطلوبة');expected.value=data.expected??'';
    const remove=el('button','حذف',cell(''));remove.type='button';remove.setAttribute('aria-label','حذف المتطلب');
    remove.addEventListener('click',()=>{row.remove();draft();showQuestions();});
    return row;
  }
  function showQuestions(){
    const items=[...(analysis?.questions||[])];
    const residential=$('cwType').value==='residential';
    $('cwBuildingFields').hidden=!residential;
    // An empty new project shows no questions until the owner starts describing it.
    const started=!!$('cwBrief').value.trim()||Object.values(fields).some(id=>$(id).value!=='');
    for(const [metric,id] of Object.entries(fields)){
      if(!started)break;
      if($(id).value!=='')continue;
      if(!optional.has(metric))items.push('ما '+metricLabels[metric]+'؟ القيمة غير محددة.');
      else if(residential&&metric==='building_width_m')items.push('ما عرض المبنى وعمقه بعد الارتدادات؟ إن تركتهما فارغين فسيُرسم المبنى بحجم الأرض كاملة.');
    }
    sources.replaceChildren();
    try{
      const p=buildBriefProgram(input());
      for(const r of p.requirements){
        const card=el('div',null,sources,'cw-brief-source');
        el('strong',requirementLabel(r)+' · '+r.expected,card);
        el('p',(r.source_id==='brief:form'?'إدخال منك':r.source==='inferred'?'تفسير للأبعاد يحتاج تأكيدك':'مذكور في الوصف')+' — «'+r.evidence+'»',card);
      }
    }catch(e){if($('cwBrief').value.trim())items.push(e.message);}
    questions.replaceChildren();for(const item of new Set(items))el('li',item,questions);
    questionTitle.hidden=questions.hidden=!items.length;
  }
  function apply(candidate){
    const id=fields[candidate.metric];
    if(id)$(id).value=candidate.expected;
    else{
      let row=[...$('cwRequirements').children].find(node=>requirementKey({metric:node.querySelector('select').value,role:node.querySelector('[data-role]').value})===requirementKey(candidate));
      if(!row)row=add(candidate);else row.querySelector('[data-value]').value=candidate.expected;
    }
    draft();showQuestions();notice.textContent='أضيفت القيمة إلى البرنامج. راجع بقية القيم ثم أكد المتطلبات.';
  }
  function readBrief(){
    try{
      analysis=analyzeBrief($('cwBrief').value.trim());cards.replaceChildren();
      for(const c of analysis.candidates){
        const card=el('article',null,cards,'cw-brief-candidate');
        el('strong',requirementLabel(c)+' · '+c.expected,card);
        el('span',c.source==='inferred'?'ترتيب مقترح للأبعاد — يحتاج تأكيدك':'مذكور في الوصف',card,'cw-badge');
        el('blockquote',c.evidence,card);
        const use=el('button','استخدام '+c.expected,card);use.type='button';use.dataset.briefMetric=c.metric;use.dataset.briefRole=c.role||'';
        use.setAttribute('aria-label','استخدام '+requirementLabel(c)+' '+c.expected);use.addEventListener('click',()=>apply(c));
      }
      if(analysis.candidates.length>1){
        const all=el('button','استخدام كل القيم ('+analysis.candidates.length+')',cards,'cw-use-all');all.type='button';all.id='cwUseAllBrief';
        all.addEventListener('click',()=>{for(const c of analysis.candidates)apply(c);notice.textContent='أضيفت كل القيم المقروءة إلى البرنامج. راجعها ثم أكد المتطلبات.';});
      }
      const area=analysis.site_area_m2;
      notice.textContent=(analysis.candidates.length?'اختر القيم التي تريد إضافتها، ثم راجع البرنامج. تغيير الوصف أو القيم يلغي التأكيد السابق.':'لم أجد أبعادًا أو أعدادًا صريحة بهذه الصياغة. أدخلها في الحقول، أو جرّب القراءة الذكية؛ وصفك سيبقى محفوظًا كاملًا.')
        +(area?' مساحة الأرض في الوصف '+area.value+' م²'+(area.matches?' وتطابق العرض × العمق.':'.'):'');
      $('cwConfirmed').checked=false;showQuestions();
    }catch(e){onError(e);}
  }
  read.addEventListener('click',readBrief);
  // Number fields are text fields with a numeric keyboard, so Arabic digits and
  // «٫» are accepted: typed digits become ASCII at once (caret kept), and the
  // value is tidied when the field is left. Capture phase: before other readers.
  const numeric=target=>target?.matches?.('input[inputmode="decimal"],input[inputmode="numeric"]');
  $('cwBriefForm').addEventListener('input',e=>{
    if(!numeric(e.target))return;const before=e.target.value,after=asciiNumberText(before);if(after===before)return;
    const start=e.target.selectionStart,end=e.target.selectionEnd;e.target.value=after;try{e.target.setSelectionRange(start,end);}catch(err){}
  },true);
  $('cwBriefForm').addEventListener('change',e=>{if(numeric(e.target)){const tidy=normalizeNumberText(e.target.value);if(tidy!==e.target.value)e.target.value=tidy;}},true);
  $('cwAddRequirement').addEventListener('click',()=>{add();draft();showQuestions();});
  $('cwBriefForm').addEventListener('input',e=>{
    if(e.target.id==='cwConfirmed')return;
    if(e.target.id==='cwBrief'){
      closeStarterPreview();syncStarterFields();
      analysis=null;savedRequirements=[];cards.replaceChildren();sources.replaceChildren();questions.replaceChildren();
      notice.textContent='تغيّر الوصف. اقرأ المتطلبات مجددًا أو راجع الأبعاد والأعداد في الحقول.';
      questionTitle.hidden=questions.hidden=true;
    }else{
      linkedFields.delete(e.target.id);
      showQuestions();
    }
    draft();
  });
  return {
    program(){try{return buildBriefProgram(input());}catch(e){showQuestions();throw e;}},
    // Confirmed values from another reader (the smart-reading card): fields or requirement rows.
    useValues(values){for(const value of values)apply(value);},
    fill(data,typology){
      let saved=null;try{saved=JSON.parse(localStorage.getItem(storageKey())||'null');}catch(e){}
      linkedFields=new Set(starterFieldIds.filter(id=>Array.isArray(saved?.starterFields)&&saved.starterFields.includes(id)));
      $('cwRequirements').replaceChildren();
      if(saved&&typeof saved==='object'&&!Array.isArray(saved)){
        $('cwBrief').value=typeof saved.brief==='string'?saved.brief:'';$('cwType').value=saved.type||'residential';
        $('cwWidth').value=saved.w??'';$('cwDepth').value=saved.d??'';$('cwLevels').value=saved.levels??'';
        $('cwBldWidth').value=saved.bw??'';$('cwBldDepth').value=saved.bd??'';
        savedRequirements=Array.isArray(saved.savedRequirements)?saved.savedRequirements:[];
        for(const r of (Array.isArray(saved.rows)?saved.rows:[]).slice(0,97))if(r&&typeof r==='object')add(r);
      }else if(data?.brief){
        $('cwBrief').value=data.brief;savedRequirements=data.requirements||[];
        $('cwBldWidth').value='';$('cwBldDepth').value='';
        for(const r of savedRequirements){const id=fields[r.metric];if(id)$(id).value=r.expected??'';else add(r);}
        if(typology==='warehouse')$('cwType').value='warehouse';
      }
      // Restoring a local draft or cloud revision is not a fresh confirmation.
      showStarters();$('cwConfirmed').checked=false;showQuestions();
    },
  };
}
