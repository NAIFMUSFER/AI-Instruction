// Local, bounded reading of explicit quantities. It is not a general semantic
// parser. Unsupported and conditional prose remains in the original brief.
// All external source offsets are Unicode code points, matching Python slicing.
export const metricLabels = Object.freeze({
  site_width_m:'عرض الموقع (م)', site_depth_m:'عمق الموقع (م)', level_count:'عدد الأدوار',
  building_target_area_m2:'مساحة المبنى المستهدفة (م²)',
  room_count:'عدد فراغات الاستخدام', min_space_area_by_role_m2:'أقل مساحة للاستخدام (م²)',
  unit_count:'إجمالي الشقق', unit_count_per_level:'الشقق في كل دور', room_count_per_unit:'عدد الفراغات داخل كل شقة',
  dock_count:'عدد الأرصفة', min_dock_count:'أقل عدد أرصفة', min_rack_group_count:'أقل عدد مجموعات رفوف',
});
const roles = {bedroom:'غرف النوم',office:'المكاتب',kitchen:'المطابخ',living:'الصالات',bathroom:'دورات المياه',majlis:'المجالس',stairs:'الدرج',elevator:'المصاعد'};
export const requirementKey = r => JSON.stringify([r.metric, r.role || '']);
export const requirementLabel = r => (r.metric==='room_count_per_unit' ? (roles[r.role]||r.role)+' في كل شقة' : r.metric==='room_count' && roles[r.role]) || metricLabels[r.metric] || r.metric;
export function warehouseRequirementsPreflight(requirements) {
  const reqs=Array.isArray(requirements)?requirements:[];
  const confirmed=metric=>{
    const values=reqs.filter(r=>r&&typeof r==='object'&&r.metric===metric).map(r=>r.expected);
    if(values.length!==1)return null;
    const value=values[0];
    return typeof value==='number'&&Number.isFinite(value)?value:null;
  };
  const w=confirmed('site_width_m'),d=confirmed('site_depth_m'),levels=confirmed('level_count'),target=confirmed('building_target_area_m2');
  if([w,d,levels,target].some(v=>v===null))return {status:'NOT_EVALUATED',may_generate_layout:true};
  const site=w*d;
  if(target>site*levels)return {status:'BUILDING_TARGET_EXCEEDS_THEORETICAL_FLOOR_AREA',site_area_m2:site,building_target_m2:target,level_count:levels,may_generate_layout:false};
  if(levels===1&&target>=site)return {status:'BUILDABLE_ENVELOPE_NOT_VERIFIED',site_area_m2:site,building_target_m2:target,level_count:levels,unallocated_site_area_m2:Math.max(0,site-target),may_generate_layout:false};
  return {status:'FEASIBLE_FOR_LAYOUT_PREFLIGHT',site_area_m2:site,building_target_m2:target,level_count:levels,unallocated_site_area_m2:levels?site-target/levels:null,may_generate_layout:true};
}

const normal = s => s.replace(/[٠-٩۰-۹أإآ]/g,c=>{
  const n=c.charCodeAt(0);
  return n>=0x6f0&&n<=0x6f9?String(n-0x6f0):n>=0x660&&n<=0x669?String(n-0x660):'ا';
}).replace(/٫/g,'.');
const cp = s => Array.from(s).length;
const N = '[0-9]+(?:\\.[0-9]+)?';
const U = '(?:millimeters?|centimeters?|metres?|meters?|mm|cm|m|مليمتر|سنتيمتر|متر|سم|مم|م)';
const site = '(?:الموقع|الارض|موقع|ارض|site|plot)';
const factor = u => /^(?:mm|millimeter|مم|مليمتر)/i.test(u)?0.001:/^(?:cm|centimeter|سم|سنتيمتر)/i.test(u)?0.01:1;
const ambiguous = /(?:\b(?:if|or|not|about|around|approximately|per|each)\b|(?:^|\s)(?:لا|ليس|بدون|اذا|ان|او)(?:\s|$)|تقريب|حوالي|لكل|كل\s+(?:دور|طابق|شقه|شقة)|[بل]الدور|[بل]الطابق|في\s+(?:الدور|الطابق)|[-−]\s*[0-9]|[0-9]\s*(?:[-–—/]|الى|to)\s*[0-9]|[0-9][,٬][0-9])/iu;
const bounded = /(?:على\s+(?:الاقل|الاكثر)|حد\s+(?:ادنى|اقصى)|at\s+(?:least|most)|minimum|maximum|less\s+than|more\s+than|[<>])/iu;

export function analyzeBrief(brief) {
  if(typeof brief!=='string'||cp(brief)>60000)throw new Error('الوصف يتجاوز الحد المسموح.');
  const candidates=[],questions=[],seen=new Set();
  const chunks=brief.matchAll(/[^\n؛;!?؟]+/gu);
  const add=(metric,n,unit,match,base,source='requested',role)=>{
    const numeric=typeof n==='string'?n.replace(/[,٬]/g,''):n;
    const expected=Number(numeric)*(unit?factor(unit):1);
    if(!Number.isFinite(expected)||expected<0||(['level_count','room_count','dock_count','min_dock_count','min_rack_group_count'].includes(metric)&&!Number.isInteger(expected))){
      questions.push('ورد عدد غير صحيح: «'+match[0]+'». حدّد عددًا صحيحًا.');return;
    }
    const key=JSON.stringify([metric,role||'',expected]);if(seen.has(key))return;seen.add(key);
    const start=base+match.index,end=start+match[0].length;
    candidates.push({id:'text-'+cp(brief.slice(0,start))+'-'+metric,metric,expected,source,source_id:'brief:text',
      evidence:brief.slice(start,end),source_span:{start:cp(brief.slice(0,start)),end:cp(brief.slice(0,end))},
      confirmed:false,...(role?{role}:{})});
  };
  for(const chunk of chunks){
    const text=normal(chunk[0]);
    // Building target area is a planning budget, not site area. Approximate
    // wording is intentionally reviewable/inferred rather than silently hard.
    const areaPattern=/(?:مساحة\s+(?:المبنى|مبنى(?:\s+المستودع)?)(?:\s+(?:المستهدفة|المغلقة))?|building\s+(?:target\s+)?area)\s*(?:تقارب|قرابة|حوالي|≈|~)?\s*[:=]?\s*(?<n>[0-9]+(?:[,٬][0-9]{3})*(?:\.[0-9]+)?)\s*(?:م(?:تر)?\s*(?:مربع|²)|m²|sqm)(?![\p{L}\p{N}])/giu;
    for(const match of text.matchAll(areaPattern))add('building_target_area_m2',match.groups.n,null,match,chunk.index,'inferred');
    // A comma-grouped measured area such as 5,000 m² is an ordinary
    // thousands separator, not a numeric range/decimal ambiguity. It may stay
    // in the brief without creating a noisy pre-generation question. We do
    // not promote it to a hard requirement unless a supported area phrase
    // matched above; confirmed form values remain the source of truth.
    const groupedMeasuredArea=/[0-9]+(?:[,٬][0-9]{3})+\s*(?:م(?:تر)?\s*(?:مربع|²)|m²|sqm)(?![\p{L}\p{N}])/iu;
    if(ambiguous.test(text)&&!areaPattern.test(text)&&!groupedMeasuredArea.test(text)){
      if(/[0-9]/.test(text))questions.push('راجع الشرط أو نطاق العدد في: «'+chunk[0].trim().slice(0,200)+'». أضف القيم الإجمالية المؤكدة في الحقول.');
      continue;
    }
    const patterns=[
      ['site_width_m',`(?:عرض\\s+${site}|${site}\\s+(?:ب?عرض|width))\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
      ['site_depth_m',`(?:عمق\\s+${site}|${site}\\s+(?:ب?عمق|depth))\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`],
      ['level_count',`عدد\\s+(?:الادوار|الطوابق)\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
      ['level_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s*(?:ادوار|طوابق|floors?|storeys?|stories)(?![\\p{L}\\p{N}])`],
      ['room_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:غرف(?:ة|ه)?\\s+نوم|bedrooms?)(?![\\p{L}\\p{N}])`,'bedroom'],
      ['room_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:مكاتب|offices?)(?![\\p{L}\\p{N}])`,'office'],
      ['room_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:مطابخ|kitchens?)(?![\\p{L}\\p{N}])`,'kitchen'],
      ['dock_count',`عدد\\s+الارصفه?\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
      ['dock_count',`عدد\\s+الارصفة\\s*[:=]?\\s*(?<n>${N})(?![0-9.])`],
      ['dock_count',`(?<![\\p{L}\\p{N}.])(?<n>${N})\\s+(?:ارصفه|ارصفة|docks?)(?![\\p{L}\\p{N}])`],
      ['min_rack_group_count',`(?:على\\s+الاقل|at\\s+least)\\s+(?<n>${N})\\s+(?:مجموعات\\s+رفوف|rack\\s+groups?)(?![\\p{L}\\p{N}])`],
    ];
    for(const [metric,pattern,role] of patterns){
      for(const match of text.matchAll(new RegExp(pattern,'giu'))){
        // A minimum dock request must not become an exact count.
        const prefix=text.slice(Math.max(0,match.index-20),match.index);
        const minimum=metric==='dock_count'&&/(?:على\s+الاقل|at\s+least)\s*$/i.test(prefix);
        if(bounded.test(text)&&!minimum&&metric!=='min_rack_group_count'){
          questions.push('راجع الحد الأدنى أو الأعلى في: «'+chunk[0].trim().slice(0,200)+'». حدّد نوع المتطلب وقيمته قبل التوليد.');continue;
        }
        add(minimum?'min_dock_count':metric,match.groups.n,match.groups.u,match,chunk.index,'requested',role);
      }
    }
    // Standalone project-dimension lines, never a room's dimensions or a
    // unitless number. An unlabelled pair still needs explicit order review.
    if(!bounded.test(text)){
      for(const [metric,label] of [['site_width_m','عرض'],['site_depth_m','عمق']]){
        for(const pattern of [
          `^\\s*(?:ال)?${label}\\s*[:=]?\\s*(?<n>${N})\\s*(?<u>${U})\\s*[.،,]?\\s*$`,
          `^\\s*(?<n>${N})\\s*(?<u>${U})\\s+(?:ال)?${label}\\s*[.،,]?\\s*$`,
        ])for(const match of text.matchAll(new RegExp(pattern,'giu')))add(metric,match.groups.n,match.groups.u,match,chunk.index);
      }
      const compact=`^\\s*(?<n>${N})\\s*(?<u>${U})\\s*(?:×|x|في)\\s*(?<d>${N})\\s*(?<du>${U})\\s*[.،,]?\\s*$`;
      for(const match of text.matchAll(new RegExp(compact,'giu'))){
        add('site_width_m',match.groups.n,match.groups.u,match,chunk.index,'inferred');
        add('site_depth_m',match.groups.d,match.groups.du,match,chunk.index,'inferred');
      }
      for(const match of text.matchAll(/(?<![\p{L}])(?:دورين|دوران|طابقين|طابقان)(?![\p{L}])/gu))add('level_count',2,null,match,chunk.index);
    }
    const pair=`(?:ابعاد\\s+${site}|${site}\\s+dimensions|${site})\\s*[:=]?\\s*(?<n>${N})\\s*[×x]\\s*(?<d>${N})\\s*(?<u>${U})(?![\\p{L}\\p{N}²])`;
    for(const match of text.matchAll(new RegExp(pair,'giu'))){
      add('site_width_m',match.groups.n,match.groups.u,match,chunk.index,'inferred');
      add('site_depth_m',match.groups.d,match.groups.u,match,chunk.index,'inferred');
    }
  }
  if(candidates.length>100)throw new Error('الوصف يحتوي متطلبات أكثر من الحد المسموح. اختصره قبل المتابعة.');
  return {candidates,questions:[...new Set(questions)]};
}

export function buildBriefProgram(input) {
  const text=input.brief?.trim();
  if(!text)throw new Error('اكتب وصف المشروع أولًا.');
  if(cp(text)>58000)throw new Error('الوصف يتجاوز الحد المسموح.');
  if(!['residential','warehouse'].includes(input.type))throw new Error('اختر نوع المشروع.');
  const analysis=analyzeBrief(text), values=[
    {metric:'site_width_m',expected:input.width},
    {metric:'site_depth_m',expected:input.depth},
    {metric:'level_count',expected:input.levels},
    ...(input.rows||[]).map(r=>({...r})),
  ];
  if(values.length>100)throw new Error('عدد المتطلبات يتجاوز الحد المسموح.');
  const known=new Map();
  for(const r of values){
    if(!Object.hasOwn(metricLabels,r.metric))throw new Error('نوع المتطلب غير مدعوم.');
    if(r.expected===''||r.expected===null||r.expected===undefined||(typeof r.expected==='string'&&!r.expected.trim()))throw new Error('حدّد '+requirementLabel(r)+'؛ القيمة غير محددة.');
    if(!['number','string'].includes(typeof r.expected))throw new Error('أدخل قيمة رقمية في '+requirementLabel(r)+'.');
    r.expected=Number(r.expected);
    if(!Number.isFinite(r.expected)||r.expected<0||(['site_width_m','site_depth_m','level_count'].includes(r.metric)&&r.expected<=0))throw new Error('أدخل أبعادًا وأعداد أدوار موجبة، وقيم متطلبات غير سالبة.');
    if(!['min_space_area_by_role_m2','building_target_area_m2'].includes(r.metric)&&!r.metric.endsWith('_m')&&!Number.isInteger(r.expected))throw new Error('أدخل عددًا صحيحًا في '+requirementLabel(r)+'.');
    if(['room_count','room_count_per_unit','min_space_area_by_role_m2'].includes(r.metric)){
      r.role=r.role?.trim();if(!r.role||r.role.length>80)throw new Error('حدد استخدام الفراغ للمتطلب.');
    }else delete r.role;
    const key=requirementKey(r);
    if(known.has(key))throw new Error('تعارض أو تكرار في '+requirementLabel(r)+'. اجمعه في متطلب واحد.');
    known.set(key,r);
  }
  if(input.type==='warehouse'){
    const preflight=warehouseRequirementsPreflight(values);
    if(!preflight.may_generate_layout){
      if(preflight.status==='BUILDABLE_ENVELOPE_NOT_VERIFIED')throw new Error('مساحة المبنى المستهدفة تستهلك كامل مساحة الموقع في مشروع من دور واحد. أدخل مساحة مبنى أصغر أو موقعًا أكبر؛ لن يخترع ACS ارتدادات أو أبعادًا تنظيمية.');
      if(preflight.status==='BUILDING_TARGET_EXCEEDS_THEORETICAL_FLOOR_AREA')throw new Error('مساحة المبنى المستهدفة أكبر من المساحة النظرية المتاحة عبر عدد الأدوار المؤكد. عدّل مساحة المبنى أو أبعاد الموقع أو عدد الأدوار قبل الانتقال إلى البدائل.');
    }
  }
  const grouped=new Map();
  for(const c of analysis.candidates){
    const key=requirementKey(c), previous=grouped.get(key);
    if(previous&&Math.abs(previous.expected-c.expected)>1e-8)throw new Error('تعارض في الوصف: '+requirementLabel(c)+' ورد بأكثر من قيمة. وضّح القيمة المطلوبة في الوصف.');
    grouped.set(key,c);
    const r=known.get(key);
    if(!r)throw new Error('ورد متطلب '+requirementLabel(c)+' في الوصف. أضفه إلى البرنامج قبل التأكيد.');
    if(Math.abs(r.expected-c.expected)>1e-8)throw new Error('تعارض بين الوصف والحقول في '+requirementLabel(c)+'. صحّح الوصف أو القيمة قبل التوليد.');
  }

  // Requirement ids are provenance identities, not row positions. Preserve an
  // unambiguous stored id when the same requirement/value and exact evidence
  // survive a revision. Older connected-workspace revisions did not store a
  // source_span, so migrate them only when their evidence occurs exactly once.
  const saved=Array.isArray(input.savedRequirements)?input.savedRequirements:[];
  const savedIdCounts=new Map();
  for(const p of saved){
    if(p&&typeof p.id==='string'&&p.id.trim()&&p.id.length<=160)
      savedIdCounts.set(p.id,(savedIdCounts.get(p.id)||0)+1);
  }
  const recoverSource=p=>{
    if(!p||typeof p!=='object'||typeof p.evidence!=='string'||!p.evidence)return null;
    const span=p.source_span;
    if(span&&Number.isInteger(span.start)&&Number.isInteger(span.end)&&span.start>=0&&span.end>span.start&&span.end<=cp(text)
        &&Array.from(text).slice(span.start,span.end).join('')===p.evidence)return {...p,source_span:{start:span.start,end:span.end}};
    const first=text.indexOf(p.evidence);
    if(first<0||text.indexOf(p.evidence,first+p.evidence.length)>=0)return null;
    return {...p,source_span:{start:cp(text.slice(0,first)),end:cp(text.slice(0,first+p.evidence.length))}};
  };
  const reusable=saved.map(recoverSource).filter(p=>p&&typeof p.id==='string'&&p.id.trim()&&p.id.length<=160&&savedIdCounts.get(p.id)===1);
  // Every previously valid provenance id is retired from fresh allocation even
  // when its evidence is edited away. Only `reusable` ids may be preserved.
  const reservedIds=new Set(savedIdCounts.keys()), usedIds=new Set();
  let nextId=0;
  const freshId=()=>{
    let id;
    do{id='brief-'+nextId++;}while(usedIds.has(id)||reservedIds.has(id));
    usedIds.add(id);return id;
  };

  const typeLine='نوع المشروع: '+(input.type==='warehouse'?'مستودع / صناعي':'سكني / عمارة / فيلا');
  let brief=text.split('\n').includes(typeLine)?text:text+'\n\n'+typeLine;
  const requirements=[];
  for(const r of values){
    const matches=reusable.filter(p=>requirementKey(p)===requirementKey(r)&&Number(p.expected)===r.expected);
    const prior=matches.length===1?matches[0]:null;
    const extracted=grouped.get(requirementKey(r));
    let source=prior || extracted;
    if(!source){
      const evidence=requirementLabel(r)+(r.role?' ('+r.role+')':'')+': '+r.expected;
      const start=cp(brief)+1;brief+='\n'+evidence;
      source={source:'requested',source_id:'brief:form',evidence,source_span:{start,end:cp(brief)}};
    }
    let id=prior?.id;
    if(!id||usedIds.has(id))id=freshId();else usedIds.add(id);
    requirements.push({id,metric:r.metric,expected:r.expected,...(r.role?{role:r.role}:{}),
      source:source.source,source_id:source.source_id,evidence:source.evidence,source_span:{...source.source_span},confirmed:true});
  }
  if(cp(brief)>60000)throw new Error('الوصف مع المتطلبات يتجاوز الحد المسموح.');
  return {brief,requirements};
}
