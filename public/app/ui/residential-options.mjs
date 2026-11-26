import {readResidential,residentialOptions,readVilla,villaProgram,villaSummary,villaRows,villaOptions,VILLA_DEFAULTS,VILLA_SOURCE,VILLA_ISSUE_NAMES,VILLA_SCOPE_NAMES} from '../core/residential-program.mjs';
import {PROGRAM_LIMITS,normalizeNumberText} from '../core/brief-program.mjs';
import {villaBrief} from '../core/plot-rules.mjs';
import {floorProgram,programOptions,programRows,programConflicts,MAX_REQUIREMENTS,PROGRAM_ISSUE_NAMES,PROGRAM_SCOPE_NAMES} from '../core/floor-program.mjs';
// buildable(): the plot preview's buildable footprint (m²) or null; it sizes the villa cards.
// issueNames/scopeNames: the review's label tables; the villa and per-floor codes are added to them.
// confirmedProgram(): the smart-reading card ({program, confirmed}) or null; a confirmed
// apartment program replaces the per-flat cards with layouts of its own floors.
export function createResidentialOptions(root,{storageKey,api,onError,buildable=()=>null,issueNames,scopeNames,confirmedProgram=()=>null}) {
 if(issueNames)Object.assign(issueNames,VILLA_ISSUE_NAMES,PROGRAM_ISSUE_NAMES);if(scopeNames)Object.assign(scopeNames,VILLA_SCOPE_NAMES,PROGRAM_SCOPE_NAMES);
 const $=id=>root.querySelector('#'+id),el=(tag,text,parent)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(parent)parent.append(n);return n;};
 const section=el('section');section.className='cw-brief-review';section.id='cwResidential';
 const choice=(id,options)=>'<select id="'+id+'">'+options.map(([v,label])=>'<option value="'+v+'">'+label+'</option>').join('')+'</select>';
 section.innerHTML=`<h3 id="cwResidentialTitle">الشقق واحتياجات الأسرة</h3><div class="cw-fields" id="cwApartmentFields"><label>عدد الشقق<input id="cwUnits" type="text" inputmode="numeric" autocomplete="off" placeholder="غير محدد"></label><label>المقصود بالعدد<select id="cwUnitsScope"><option value="total">إجمالي المبنى</option><option value="per_level">في كل دور</option></select></label><label>الاستخدام<select id="cwPurpose"><option value="unknown">لا أعرف الآن</option><option value="family">سكن عائلي</option><option value="rental">تأجير</option></select></label></div><div class="cw-fields" id="cwFlatFields"><label>غرف النوم في الشقة<input id="cwBedrooms" type="text" inputmode="numeric" autocomplete="off" placeholder="اقترح لي"></label><label>دورات المياه في الشقة<input id="cwBathrooms" type="text" inputmode="numeric" autocomplete="off" placeholder="اقترح لي"></label></div><div class="cw-fields" id="cwVillaFields" hidden><label>غرف النوم<input id="cwVillaBedrooms" type="text" inputmode="numeric" autocomplete="off" placeholder="افتراضي ${VILLA_DEFAULTS.bedrooms}"></label><label>جناح رئيسي بحمام خاص${choice('cwVillaMaster',[['yes','نعم'],['no','لا']])}</label><label>الحمامات ودورات المياه<input id="cwVillaBathrooms" type="text" inputmode="numeric" autocomplete="off" placeholder="تلقائي"></label><label>غرفة خادمة${choice('cwVillaMaid',[['no','لا'],['yes','نعم، بدورة مياه']])}</label><label>غرفة سائق${choice('cwVillaDriver',[['no','لا'],['yes','نعم، بدورة مياه']])}</label></div><p id="cwVillaSummary" class="cw-muted" role="status" aria-live="polite" hidden></p><div class="cw-fields"><label>مجلس الضيوف<select id="cwGuests"><option value="suggest">اقترح لي</option><option value="separate">مجلس مستقل</option><option value="none">بدون مجلس مستقل</option></select></label><label>المدينة<input id="cwCity" maxlength="120" placeholder="مثل: الرياض"></label><label>جهة الشارع<select id="cwStreet"><option value="unknown">لا أعرف الآن</option><option value="N">شمال</option><option value="S">جنوب</option><option value="E">شرق</option><option value="W">غرب</option></select></label></div><p id="cwResidentialSummary" class="cw-muted"></p>`;
 ($('cwBuildingFields')||$('cwLevels').closest('.cw-fields')).after(section);
 const sourcePanel=el('section',null,root.querySelector('[data-step-panel="2"]'));sourcePanel.className='cw-card';sourcePanel.id='cwResearch';
 el('h3','مراجع تساعدك على مراجعة التصميم',sourcePanel);const note=el('p','',sourcePanel);note.id='cwResearchStatus';const links=el('div',null,sourcePanel);
 // Arabic counting: 1 مفرد، 2 مثنى، 3–10 جمع، 11+ مفرد منصوب.
 const counted=(n,one,two,few,many)=>{n=Number(n);return n===1?one:n===2?two:n>=3&&n<=10?n+' '+few:n+' '+many;};
 const bedrooms=n=>counted(n,'غرفة نوم','غرفتا نوم','غرف نوم','غرفة نوم'),baths=n=>counted(n,'دورة مياه','دورتا مياه','دورات مياه','دورة مياه'),flats=n=>counted(n,'شقة واحدة','شقتان','شقق','شقة');
 const villaFields=['cwVillaBedrooms','cwVillaMaster','cwVillaBathrooms','cwVillaMaid','cwVillaDriver'];
 const fields=['cwUnits','cwUnitsScope','cwPurpose','cwBedrooms','cwBathrooms','cwGuests','cwCity','cwStreet',...villaFields];let choices=[],prepared=null,researchEpoch=0;const originals=[...root.querySelectorAll('[data-option]')].map(b=>({id:b.dataset.option,title:b.closest('article').querySelector('h2').textContent,body:b.closest('article').querySelector('p').textContent,button:b.textContent}));
 function fingerprint(base){const card=confirmedProgram();return JSON.stringify([base,snapshot(),$('cwLevels').value,$('cwWidth').value,$('cwDepth').value,$('cwBldWidth').value,$('cwBldDepth').value,$('cwType').value,card?.confirmed?card.program.levels:null]);}
 // The confirmed card's program when it is planned floor by floor (an apartment building).
 function perFloor(){const card=confirmedProgram();return $('cwType').value==='residential'&&card?.confirmed&&floorProgram(card.program)&&!villa()?card.program:null;}
 function snapshot(){return Object.fromEntries(fields.map(id=>[id,$(id).value]));}
 // One villa or house, read as the server reads it (acs_residential_access._brief_says).
 function villa(){
  if($('cwType').value!=='residential')return false;
  const units=Number(normalizeNumberText($('cwUnits').value))||null,levels=Number(normalizeNumberText($('cwLevels').value))||1;
  return villaBrief($('cwBrief').value,units&&$('cwUnitsScope').value==='per_level'?units*levels:units);
 }
 function villaInputs(){return {bedrooms:$('cwVillaBedrooms').value,master:$('cwVillaMaster').value,bathrooms:$('cwVillaBathrooms').value,maid:$('cwVillaMaid').value,driver:$('cwVillaDriver').value};}
 function save(){try{localStorage.setItem(storageKey(),JSON.stringify(snapshot()));}catch(e){}$('cwConfirmed').checked=false;summary();}
 function summary(){
  const isVilla=villa(),count=Number($('cwUnits').value),levels=Number($('cwLevels').value);section.hidden=$('cwType').value!=='residential';
  $('cwResidentialTitle').textContent=isVilla?'برنامج الفيلا':'الشقق واحتياجات الأسرة';
  $('cwApartmentFields').hidden=$('cwFlatFields').hidden=isVilla;$('cwVillaFields').hidden=$('cwVillaSummary').hidden=!isVilla;
  if(isVilla){
   try{const p=villaProgram(villaInputs());$('cwVillaSummary').textContent='البرنامج: '+villaSummary(p);$('cwVillaBathrooms').placeholder=p.autoBathrooms?'تلقائي: '+p.bathrooms:'';}
   catch(e){$('cwVillaSummary').textContent=e.message;}
   $('cwResidentialSummary').textContent='فيلا لأسرة واحدة: تُرسم كل غرفة نوم وكل حمام فراغًا مستقلًا، ويُفحص المخطط على هذه الأعداد. اترك الحقل فارغًا لاستخدام القيمة الافتراضية.';
   return;
  }
  $('cwResidentialSummary').textContent=count>0?( $('cwUnitsScope').value==='per_level'?flats(count)+' في كل دور؛ الإجمالي '+(levels>0?flats(count*levels):'يحتاج عدد الأدوار')+'.':flats(count)+' في إجمالي المبنى. غيّر الاختيار إن كنت تقصد العدد في كل دور.'):'للعمارة، حدّد عدد الشقق لعرض برامج غرف قابلة للمقارنة. للفيلا، اذكر «فيلا» في الوصف لتظهر حقول غرف النوم والحمامات.';
 }
 section.addEventListener('input',save);section.addEventListener('change',save);$('cwLevels').addEventListener('input',summary);$('cwType').addEventListener('change',summary);$('cwBrief').addEventListener('input',summary);
 $('cwReadBrief').addEventListener('click',()=>{const text=$('cwBrief').value;
  // The street side helps a villa and a building alike (plot rules, entrance).
  const street=readResidential(text).street;if(street&&$('cwStreet').value==='unknown'){$('cwStreet').value=street;$('cwStreet').dispatchEvent(new Event('change',{bubbles:true}));}
  if(villa()){const found=readVilla(text);if(found.bedrooms)$('cwVillaBedrooms').value=found.bedrooms;if(found.maid)$('cwVillaMaid').value=found.maid;if(found.driver)$('cwVillaDriver').value=found.driver;save();return;}
  const found=readResidential(text);if(found.units){$('cwUnits').value=found.units;$('cwUnitsScope').value=found.scope;}if(found.bedrooms)$('cwBedrooms').value=found.bedrooms;if(found.guests)$('cwGuests').value=found.guests;save();});
 async function sources(){
  const epoch=++researchEpoch;note.textContent='جارٍ جلب المراجع الرسمية…';links.replaceChildren();
  try{const data=await api({action:'research',city:$('cwCity').value,building_type:$('cwType').value});if(epoch!==researchEpoch)return;note.textContent=data.message;
   for(const source of data.sources||[]){const box=el('p',null,links);const a=el('a',source.title,box);a.href=source.url;a.target='_blank';a.rel='noopener';el('span',' · '+(source.status==='retrieved'?'تم الجلب':'تعذّر الجلب')+' · '+source.checked_at.slice(0,10),box);el('p',source.information_used||'لم تُستخدم معلومات هذا المصدر.',box);}
  }catch(e){if(epoch===researchEpoch)note.textContent='تعذّر جلب المراجع الآن. يمكنك المتابعة بمقترح تصميم دون ادعاء مطابقة محلية.';}
 }
 // A count the owner already confirmed in the requirements table (or the brief) wins over an empty field.
 function villaFromBase(base){
  const fixed=role=>base.requirements.find(r=>r.metric==='room_count'&&r.role===role&&r.template==null)?.expected;
  const input=villaInputs();
  for(const [key,role,label] of [['bedrooms','bedroom','غرف النوم'],['bathrooms','bathroom','الحمامات ودورات المياه']]){
   const confirmed=fixed(role);if(confirmed==null)continue;
   const typed=normalizeNumberText(input[key]);
   if(typed!==''&&Number(typed)!==confirmed)throw new Error(label+' في برنامج الفيلا ('+typed+') يختلف عن المتطلب المؤكد ('+confirmed+'). وحّد القيمتين قبل المتابعة.');
   input[key]=String(confirmed);
  }
  return villaProgram(input);
 }
 function showVilla(base){
  const program=villaFromBase(base),levels=Number(normalizeNumberText($('cwLevels').value))||1;
  choices=villaOptions(program,{levels,buildable:buildable(),guests:$('cwGuests').value});
  for(const o of choices){const b=root.querySelector('[data-option="'+o.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=o.title+(o.recommended?' · مقترح لك':'');card.querySelector('p').textContent=o.roomsText+' '+o.why+' '+o.tradeoff;
   card.querySelector('[data-residential-detail]')?.remove();
   const p=el('p','تقدير المساحة المبنية ≈ '+o.estimatedArea+' م² على '+counted(o.levels,'دور واحد','دورين','أدوار','دورًا')+(o.available!=null?' من نحو '+o.available+' م² تسمح بها الارتدادات ونسبة البناء':'')+'. '+(o.feasible?'تقدير أولي يشمل الجدران والحركة؛ يُفحص المخطط بعد التوليد على غرف النوم والحمامات ودورة مياه الضيوف.':'المساحة المسموح ببنائها لا تكفي هذا البديل. قلّل غرف النوم أو اختر بديلًا أصغر.'),card);
   p.dataset.residentialDetail='';card.insertBefore(p,b);b.textContent='اختيار «'+o.title+'» والتوليد';b.disabled=!o.feasible;b.dataset.unavailable=String(!o.feasible);
  }
 }
 function showProgram(base,program){
  choices=programOptions(program,{buildable:buildable(),guests:$('cwGuests').value});
  // A confirmed requirement that the program contradicts is shown now, not after a paid call.
  const conflict=programConflicts(program,base.requirements)[0];
  for(const o of choices){const b=root.querySelector('[data-option="'+o.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=o.title+(o.recommended?' · مقترح لك':'');
   card.querySelector('p').textContent='الغرف نفسها من برنامجك المؤكد، بتوزيع مختلف: '+o.why+' '+o.tradeoff;
   card.querySelector('[data-residential-detail]')?.remove();
   if(conflict)o.feasible=false;
   const p=el('p',o.floors.join('؛ ')+'. '+(conflict?'متطلب مؤكد يخالف برنامج الأدوار: '+conflict+' احذفه من جدول المتطلبات أو أكّد بطاقة البرنامج من جديد.':o.feasible?(o.sized?'تُفحص أعداد غرف كل دور ومقاساتها المستهدفة بعد التوليد.':'تُفحص أعداد غرف كل دور بعد التوليد.'):'مجموع المقاسات المستهدفة في أكبر دور ('+o.largestTarget+' م²) مع الجدران والدرج لا يتسع في نحو '+o.available+' م². راجع المقاسات في بطاقة «فهمنا».'),card);
   p.dataset.residentialDetail='';card.insertBefore(p,b);b.textContent='اختيار «'+o.title+'» والتوليد';b.disabled=!o.feasible;b.dataset.unavailable=String(!o.feasible);
  }
 }
 // A confirmed floor program: per-floor rows (the same on every card) and one brief line.
 function programCommand(base,o,program){
  let brief=base.brief;const requirements=base.requirements.map(r=>({...r}));
  const conflicts=programConflicts(program,requirements);
  if(conflicts.length)throw new Error('المتطلبات المؤكدة تخالف برنامج الأدوار المؤكد: '+conflicts[0]+' احذف المتطلب المخالف من الجدول أو أكّد بطاقة البرنامج من جديد.');
  const units=program.levels.map(l=>l.units.length),rows=[{id:'program-unit_count',metric:'unit_count',expected:units.reduce((a,b)=>a+b,0),source:'inferred',source_id:'brief:program',evidence:'إجمالي الشقق: '+units.reduce((a,b)=>a+b,0),confirmed:true},...programRows(program)];
  for(const row of rows){
   const old=requirements.find(r=>r.metric===row.metric&&(r.role||'')===(row.role||'')&&(r.level??null)===(row.level??null)&&r.template==null);
   if(old)continue; // equal by programConflicts
   if(requirements.some(r=>r.id===row.id))throw new Error('معرّف متطلب مكرر: '+row.id+'. أعد تحميل الصفحة ثم أعد المحاولة.');
   requirements.push(row);
  }
  if(requirements.length>MAX_REQUIREMENTS)throw new Error('برنامج الأدوار يحتاج '+requirements.length+' متطلبًا، والحد '+MAX_REQUIREMENTS+'. اجمع الأدوار المتماثلة في بطاقة البرنامج أو احذف متطلبات مكررة.');
  brief+='\nتصور التوزيع المختار: '+o.title+' — '+o.why+' يُرسم كل دور ببرنامجه من بطاقة «فهمنا» المؤكدة.\nالمدينة: '+($('cwCity').value||'غير محددة')+'؛ جهة الشارع: '+$('cwStreet').selectedOptions[0].textContent+'.';
  return {brief,requirements};
 }
 // The villa program as confirmed requirement rows, each with its own evidence line in the brief.
 function villaCommand(base,o){
  let brief=base.brief;const requirements=base.requirements.map(r=>({...r}));const p=o.program;
  const line=text=>{const start=Array.from(brief).length+1;brief+='\n'+text;return {start,end:Array.from(brief).length};};
  brief+='\nبرنامج الفيلا: '+villaSummary(p);
  for(const row of villaRows(p)){
   const old=requirements.find(r=>r.metric===row.metric&&(r.role||'')===(row.role||'')&&r.template==null);
   if(old){if(old.expected!==row.expected)throw new Error('برنامج الفيلا يتعارض مع المتطلب المؤكد: '+row.label);continue;}
   const evidence=row.label+': '+row.expected,span=line(evidence);let rid='villa-'+row.metric+'-'+(row.role||'all');while(requirements.some(r=>r.id===rid))rid+='x';
   requirements.push({id:rid,metric:row.metric,expected:row.expected,...(row.role?{role:row.role}:{}),source:'inferred',source_id:VILLA_SOURCE,evidence,source_span:span,confirmed:true});
  }
  brief+='\nتصور الفيلا المختار: '+o.title+' — '+o.why+({separate:' مجلس ضيوف مستقل.',none:' بدون مجلس ضيوف مستقل.'}[$('cwGuests').value]||'')+'\nالمدينة: '+($('cwCity').value||'غير محددة')+'؛ جهة الشارع: '+$('cwStreet').selectedOptions[0].textContent+'.';
  return {brief,requirements};
 }
 return {
  // Arabic validation in the status line instead of the browser's English bubble.
  validate(){
   if($('cwType').value!=='residential')return;
   if(villa()){villaProgram(villaInputs());return;}
   const limits=PROGRAM_LIMITS.residential;
   const whole=(id,label,max)=>{const text=normalizeNumberText($(id).value);if(text==='')return null;const n=Number(text);
    if(!/^[0-9]+$/.test(text)||n<1||n>max)throw new Error(label+': أدخل عددًا صحيحًا من 1 إلى '+max+'.');return n;};
   const units=whole('cwUnits','عدد الشقق',limits.units);
   if(units!=null&&$('cwUnitsScope').value==='per_level'&&units>limits.units_per_level)throw new Error('عدد الشقق في كل دور ('+units+') أكبر من الحد المدعوم ('+limits.units_per_level+' شقة في الدور). راجع العدد، أو اختر «إجمالي المبنى» إن كان هذا عدد المبنى كله.');
   whole('cwBedrooms','غرف النوم في الشقة',limits.rooms_per_unit);whole('cwBathrooms','دورات المياه في الشقة',limits.rooms_per_unit);
  },
  fill(){try{const data=JSON.parse(localStorage.getItem(storageKey())||'null');if(data)for(const id of fields)if(typeof data[id]==='string')$(id).value=data[id];}catch(e){}summary();},
  prepare(base){
   summary();choices=[];prepared=fingerprint(base);for(const old of originals){const b=root.querySelector('[data-option="'+old.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=old.title;card.querySelector('p').textContent=old.body;card.querySelector('[data-residential-detail]')?.remove();b.textContent=old.button;b.dataset.unavailable='false';}sourcePanel.hidden=$('cwType').value!=='residential';
   if($('cwType').value==='residential')sources();
   if($('cwType').value!=='residential')return;
   if(villa()){showVilla(base);return;}
   const program=perFloor();if(program){showProgram(base,program);return;}
   if(!$('cwUnits').value)return;
   const levels=$('cwPlotParking')?.value==='pilotis'?String(Number($('cwLevels').value)-1):$('cwLevels').value; // parking floor holds no flats
   const units=Number($('cwUnits').value)*($('cwUnitsScope').value==='per_level'?Number(levels):1);
   const fixed=role=>base.requirements.find(r=>r.metric==='room_count'&&r.role===role)?.expected;
   choices=residentialOptions({units:$('cwUnits').value,scope:$('cwUnitsScope').value,levels,width:$('cwBldWidth').value||$('cwWidth').value,depth:$('cwBldDepth').value||$('cwDepth').value,bedrooms:fixed('bedroom')!=null?fixed('bedroom')/units:$('cwBedrooms').value,bathrooms:fixed('bathroom')!=null?fixed('bathroom')/units:$('cwBathrooms').value,guests:$('cwGuests').value,purpose:$('cwPurpose').value});
   for(const o of choices){const b=root.querySelector('[data-option="'+o.id+'"]'),card=b.closest('article');card.querySelector('h2').textContent=o.title+(o.recommended?' · مقترح لك':'');card.querySelector('p').textContent=bedrooms(o.bedrooms)+'، صالة، مطبخ، '+baths(o.bathrooms)+(o.majlis?'، مجلس مستقل':'')+' في كل شقة. '+o.why+' '+o.tradeoff;
    card.querySelector('[data-residential-detail]')?.remove();const p=el('p',flats(o.total)+'؛ توزيعها على الأدوار: '+o.distribution.join('، ')+'. تقدير الشقة '+o.estimatedUnitArea+' م². '+(o.feasible?o.feasibilityNote:'المساحة الإجمالية لا تكفي هذا البرنامج المقترح. قلّل عدد الشقق أو عدّل الغرف قبل التوليد.'),card);p.dataset.residentialDetail='';card.insertBefore(p,b);b.textContent='اختيار '+o.title+' والتوليد';b.disabled=!o.feasible;b.dataset.unavailable=String(!o.feasible);
   }
  },
  program(base,id){
   if(choices.length&&prepared!==fingerprint(base))throw new Error('تغيّرت المدخلات. اضغط متابعة إلى البدائل لتحديث المقارنة.');
   const o=choices.find(x=>x.id===id);if(!o){if($('cwType').value==='residential'&&(villa()||perFloor()||$('cwUnits').value))throw new Error(villa()?'راجع برنامج الفيلا من زر متابعة إلى البدائل أولًا.':'راجع خيارات الغرف من زر متابعة إلى البدائل أولًا.');return base;}if(!o.feasible)throw new Error('عدّل البرنامج ليتناسب مع مساحة الموقع أولًا.');
   if(o.villa)return villaCommand(base,o);
   if(o.floorProgram){const program=perFloor();if(!program)throw new Error('تغيّرت بطاقة البرنامج. اضغط متابعة إلى البدائل لتحديث المقارنة.');return programCommand(base,o,program);}
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
