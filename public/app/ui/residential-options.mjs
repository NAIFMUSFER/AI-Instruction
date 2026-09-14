import {readResidential,residentialOptions} from '../core/residential-program.mjs';
export function createResidentialOptions(root,{storageKey,api,onError}) {
 const $=id=>root.querySelector('#'+id),el=(tag,text,parent)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(parent)parent.append(n);return n;};
 const section=el('section');section.className='cw-brief-review';section.id='cwResidential';
 section.innerHTML=`<h3>الشقق واحتياجات الأسرة</h3><div class="cw-fields"><label>عدد الشقق<input id="cwUnits" type="number" min="1" max="100" placeholder="غير محدد"></label><label>المقصود بالعدد<select id="cwUnitsScope"><option value="total">إجمالي المبنى</option><option value="per_level">في كل دور</option></select></label><label>الاستخدام<select id="cwPurpose"><option value="unknown">لا أعرف الآن</option><option value="family">سكن عائلي</option><option value="rental">تأجير</option></select></label></div><div class="cw-fields"><label>غرف النوم في الشقة<input id="cwBedrooms" type="number" min="1" max="8" placeholder="اقترح لي"></label><label>دورات المياه في الشقة<input id="cwBathrooms" type="number" min="1" max="8" placeholder="اقترح لي"></label><label>مجلس الضيوف<select id="cwGuests"><option value="suggest">اقترح لي</option><option value="separate">مجلس مستقل</option><option value="none">بدون مجلس مستقل</option></select></label></div><div class="cw-fields"><label>المدينة<input id="cwCity" maxlength="120" placeholder="مثل: الرياض"></label><label>جهة الشارع<select id="cwStreet"><option value="unknown">لا أعرف الآن</option><option value="N">شمال</option><option value="S">جنوب</option><option value="E">شرق</option><option value="W">غرب</option></select></label></div><p id="cwResidentialSummary" class="cw-muted"></p>`;
 $('cwLevels').closest('.cw-fields').after(section);
 const sourcePanel=el('section',null,root.querySelector('[data-step-panel="2"]'));sourcePanel.className='cw-card';sourcePanel.id='cwResearch';
 el('h3','مراجع تساعدك على مراجعة التصميم',sourcePanel);const note=el('p','',sourcePanel);note.id='cwResearchStatus';const links=el('div',null,sourcePanel);
 const fields=['cwUnits','cwUnitsScope','cwPurpose','cwBedrooms','cwBathrooms','cwGuests','cwCity','cwStreet'];let choices=[],prepared=null,researchEpoch=0;const originals=[...root.querySelectorAll('[data-option]')].map(b=>({id:b.dataset.option,title:b.closest('article').querySelector('h2').textContent,body:b.closest('article').querySelector('p').textContent,button:b.textContent}));
 function fingerprint(base){return JSON.stringify([base,snapshot(),$('cwLevels').value,$('cwWidth').value,$('cwDepth').value,$('cwType').value]);}
 function snapshot(){return Object.fromEntries(fields.map(id=>[id,$(id).value]));}
 function save(){try{localStorage.setItem(storageKey(),JSON.stringify(snapshot()));}catch(e){}$('cwConfirmed').checked=false;summary();}
 function summary(){
  const count=Number($('cwUnits').value),levels=Number($('cwLevels').value);section.hidden=$('cwType').value!=='residential';
  $('cwResidentialSummary').textContent=count>0?( $('cwUnitsScope').value==='per_level'?count+' شقق في كل دور؛ الإجمالي '+(levels>0?count*levels:'يحتاج عدد الأدوار')+'.':count+' شقق في إجمالي المبنى. غيّر الاختيار إن كنت تقصد العدد في كل دور.'):'للعمارة، حدّد عدد الشقق لعرض برامج غرف قابلة للمقارنة. للفيلا يمكنك متابعة وصف الغرف مباشرة.';
 }
 section.addEventListener('input',save);section.addEventListener('change',save);$('cwLevels').addEventListener('input',summary);$('cwType').addEventListener('change',summary);
 $('cwReadBrief').addEventListener('click',()=>{const found=readResidential($('cwBrief').value);if(found.units){$('cwUnits').value=found.units;$('cwUnitsScope').value=found.scope;}if(found.bedrooms)$('cwBedrooms').value=found.bedrooms;if(found.guests)$('cwGuests').value=found.guests;save();});
 async function sources(){
  const epoch=++researchEpoch;note.textContent='جارٍ جلب المراجع الرسمية…';links.replaceChildren();
  try{const data=await api({action:'research',city:$('cwCity').value,building_type:$('cwType').value});if(epoch!==researchEpoch)return;note.textContent=data.message;
   for(const source of data.sources||[]){const box=el('p',null,links);const a=el('a',source.title,box);a.href=source.url;a.target='_blank';a.rel='noopener';el('span',' · '+(source.status==='retrieved'?'تم الجلب':'تعذّر الجلب')+' · '+source.checked_at.slice(0,10),box);el('p',source.information_used||'لم تُستخدم معلومات هذا المصدر.',box);}
  }catch(e){if(epoch===researchEpoch)note.textContent='تعذّر جلب المراجع الآن. يمكنك المتابعة بمقترح تصميم دون ادعاء مطابقة محلية.';}
 }
 return {
  fill(){try{const data=JSON.parse(localStorage.getItem(storageKey())||'null');if(data)for(const id of fields)if(typeof data[id]==='string')$(id).value=data[id];}catch(e){}summary();},
  prepare(base){
   summary();choices=[];prepared=fingerprint(base);for(const old of originals){const b=root.querySelector('[data-option="'+old.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=old.title;card.querySelector('p').textContent=old.body;card.querySelector('[data-residential-detail]')?.remove();b.textContent=old.button;b.dataset.unavailable='false';}sourcePanel.hidden=$('cwType').value!=='residential';
   if($('cwType').value==='residential')sources();
   if($('cwType').value!=='residential'||!$('cwUnits').value)return;
   const units=Number($('cwUnits').value)*($('cwUnitsScope').value==='per_level'?Number($('cwLevels').value):1);
   const fixed=role=>base.requirements.find(r=>r.metric==='room_count'&&r.role===role)?.expected;
   choices=residentialOptions({units:$('cwUnits').value,scope:$('cwUnitsScope').value,levels:$('cwLevels').value,width:$('cwWidth').value,depth:$('cwDepth').value,bedrooms:fixed('bedroom')!=null?fixed('bedroom')/units:$('cwBedrooms').value,bathrooms:fixed('bathroom')!=null?fixed('bathroom')/units:$('cwBathrooms').value,guests:$('cwGuests').value,purpose:$('cwPurpose').value});
   for(const o of choices){const b=root.querySelector('[data-option="'+o.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=o.title+(o.recommended?' · مقترح لك':'');card.querySelector('p').textContent=o.bedrooms+' غرف نوم، صالة، مطبخ، '+o.bathrooms+' دورات مياه'+(o.majlis?'، مجلس مستقل':'')+' في كل شقة. '+o.why+' '+o.tradeoff;
    card.querySelector('[data-residential-detail]')?.remove();const p=el('p',o.total+' شقق؛ توزيعها على الأدوار: '+o.distribution.join('، ')+'. تقدير الشقة '+o.estimatedUnitArea+' م². '+(o.feasible?o.feasibilityNote:'المساحة الإجمالية لا تكفي هذا البرنامج المقترح. قلّل عدد الشقق أو عدّل الغرف قبل التوليد.'),card);p.dataset.residentialDetail='';card.insertBefore(p,b);b.textContent='اختيار '+o.title+' والتوليد';b.disabled=!o.feasible;b.dataset.unavailable=String(!o.feasible);
   }
  },
  program(base,id){
   if(choices.length&&prepared!==fingerprint(base))throw new Error('تغيّرت المدخلات. اضغط متابعة إلى البدائل لتحديث المقارنة.');
   const o=choices.find(x=>x.id===id);if(!o){if($('cwType').value==='residential'&&$('cwUnits').value)throw new Error('راجع خيارات الغرف من زر متابعة إلى البدائل أولًا.');return base;}if(!o.feasible)throw new Error('عدّل البرنامج ليتناسب مع مساحة الموقع أولًا.');
   let brief=base.brief;const requirements=base.requirements.map(r=>({...r}));
   const add=(metric,expected,label,role)=>{const old=requirements.find(r=>r.metric===metric&&(r.role||'')===(role||''));if(old){if(old.expected!==expected)throw new Error('الخيار يتعارض مع المتطلب المؤكد: '+label);return;}
    const evidence=label+': '+expected,start=Array.from(brief).length+1;brief+='\n'+evidence;let rid='option-'+id+'-'+metric+'-'+(role||'all');while(requirements.some(r=>r.id===rid))rid+='x';requirements.push({id:rid,metric,expected,...(role?{role}:{}),source:'inferred',source_id:'brief:selected-option',evidence,source_span:{start,end:Array.from(brief).length},confirmed:true});};
   add('unit_count',o.total,'إجمالي الشقق');if(o.scope==='per_level')add('unit_count_per_level',o.units,'عدد الشقق في كل دور');
   for(const [role,n,label] of [['bedroom',o.bedrooms,'غرف النوم'],['living',1,'الصالات'],['kitchen',1,'المطابخ'],['bathroom',o.bathrooms,'دورات المياه'],['majlis',o.majlis,'المجالس']]){add('room_count',n*o.total,'إجمالي '+label,role);add('room_count_per_unit',n,label+' في كل شقة',role);}
   brief+='\nالخيار المختار: '+o.title+'؛ لكل شقة '+o.bedrooms+' غرف نوم وصالة ومطبخ و'+o.bathrooms+' دورات مياه و'+o.majlis+' مجلس مستقل.\nتوزيع الشقق من الأرضي إلى الأعلى: '+o.distribution.join('، ')+'.\nالمدينة: '+($('cwCity').value||'غير محددة')+'؛ جهة الشارع: '+$('cwStreet').selectedOptions[0].textContent+'.';
   return {brief,requirements};
  }
 };
}
