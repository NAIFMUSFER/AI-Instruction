import {analyzeBrief,buildBriefProgram,metricLabels,requirementKey,requirementLabel} from '../core/brief-program.mjs';

// Owns the existing requirements form only. No network, model or approval access.
export function createBriefEditor(root,{storageKey,onError}) {
  const $=id=>root.querySelector('#'+id);
  const fields={site_width_m:'cwWidth',site_depth_m:'cwDepth',level_count:'cwLevels'};
  let analysis=null,savedRequirements=[];
  function el(tag,text,parent,cls){const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;if(parent)parent.append(node);return node;}
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
  function input(){return {brief:$('cwBrief').value,type:$('cwType').value,width:$('cwWidth').value,depth:$('cwDepth').value,levels:$('cwLevels').value,rows:rows(),savedRequirements};}
  function draft(){
    const data=input();
    try{localStorage.setItem(storageKey(),JSON.stringify({brief:data.brief,type:data.type,w:data.width,d:data.depth,levels:data.levels,rows:data.rows,savedRequirements}));}catch(e){}
    $('cwConfirmed').checked=false;
  }
  function add(data={}){
    const row=el('tr',null,$('cwRequirements'));
    const select=el('select',null,el('td',null,row));select.setAttribute('aria-label','نوع المتطلب');
    for(const [key,label] of Object.entries(metricLabels)){if(fields[key])continue;const o=el('option',label,select);o.value=key;}
    if(data.metric&&!Object.hasOwn(metricLabels,data.metric)){const o=el('option',data.metric+' · متطلب محفوظ',select);o.value=data.metric;}
    select.value=data.metric||'room_count';
    const role=el('select',null,el('td',null,row));role.dataset.role='';role.setAttribute('aria-label','استخدام الفراغ');
    const uses={bedroom:'غرفة نوم',living:'صالة',kitchen:'مطبخ',bathroom:'دورة مياه',majlis:'مجلس',corridor:'ممر',stairs:'درج',elevator:'مصعد',office:'مكتب',storage:'تخزين',staging:'تجهيز',receiving:'استلام',shipping:'شحن'};
    if(data.role&&!Object.hasOwn(uses,data.role))uses[data.role]=data.role;
    for(const [id,label] of Object.entries(uses)){const o=el('option',label,role);o.value=id;}role.value=data.role||'bedroom';
    const expected=el('input',null,el('td',null,row));expected.dataset.value='';expected.type='number';expected.min='0';expected.step='any';expected.setAttribute('aria-label','القيمة المطلوبة');expected.value=data.expected??'';
    const remove=el('button','حذف',el('td',null,row));remove.type='button';remove.setAttribute('aria-label','حذف المتطلب');
    remove.addEventListener('click',()=>{row.remove();draft();showQuestions();});
    return row;
  }
  function showQuestions(){
    const items=[...(analysis?.questions||[])];
    for(const [metric,id] of Object.entries(fields))if($(id).value==='')items.push('ما '+metricLabels[metric]+'؟ القيمة غير محددة.');
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
      notice.textContent=analysis.candidates.length?'اختر القيم التي تريد إضافتها، ثم راجع البرنامج. تغيير الوصف أو القيم يلغي التأكيد السابق.':'لم أجد أبعادًا أو أعدادًا صريحة بهذه الصياغة. أدخلها في الحقول؛ وصفك سيبقى محفوظًا كاملًا.';
      $('cwConfirmed').checked=false;showQuestions();
    }catch(e){onError(e);}
  }
  read.addEventListener('click',readBrief);
  $('cwAddRequirement').addEventListener('click',()=>{add();draft();showQuestions();});
  $('cwBriefForm').addEventListener('input',e=>{
    if(e.target.id==='cwConfirmed')return;
    draft();
    if(e.target.id==='cwBrief'){
      analysis=null;savedRequirements=[];cards.replaceChildren();sources.replaceChildren();questions.replaceChildren();
      notice.textContent='تغيّر الوصف. اقرأ المتطلبات مجددًا أو راجع الأبعاد والأعداد في الحقول.';
      questionTitle.hidden=questions.hidden=true;
    }else showQuestions();
  });
  return {
    program(){try{return buildBriefProgram(input());}catch(e){showQuestions();throw e;}},
    fill(data,typology){
      let saved=null;try{saved=JSON.parse(localStorage.getItem(storageKey())||'null');}catch(e){}
      $('cwRequirements').replaceChildren();
      if(saved&&typeof saved==='object'&&!Array.isArray(saved)){
        $('cwBrief').value=typeof saved.brief==='string'?saved.brief:'';$('cwType').value=saved.type||'residential';
        $('cwWidth').value=saved.w??'';$('cwDepth').value=saved.d??'';$('cwLevels').value=saved.levels??'';
        savedRequirements=Array.isArray(saved.savedRequirements)?saved.savedRequirements:[];
        for(const r of (Array.isArray(saved.rows)?saved.rows:[]).slice(0,97))if(r&&typeof r==='object')add(r);
      }else if(data?.brief){
        $('cwBrief').value=data.brief;savedRequirements=data.requirements||[];
        for(const r of savedRequirements){const id=fields[r.metric];if(id)$(id).value=r.expected??'';else add(r);}
        if(typology==='warehouse')$('cwType').value='warehouse';
      }
      // Restoring a local draft or cloud revision is not a fresh confirmation.
      $('cwConfirmed').checked=false;showQuestions();
    },
  };
}
