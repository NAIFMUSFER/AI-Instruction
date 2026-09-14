const normalize = text => text.normalize('NFKC').replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)>0x6ef?c.charCodeAt(0)-0x6f0:c.charCodeAt(0)-0x660)).replace(/[أإآ]/g,'ا').replace(/ة/g,'ه');
const words = {'واحد':1,'واحده':1,'اثنين':2,'اثنتين':2,'ثلاث':3,'ثلاثه':3,'اربع':4,'اربعه':4,'خمس':5,'خمسه':5,'ست':6,'سته':6};
const quantity = v => words[v] || Number(v);
export function readResidential(text) {
  const s=normalize(text), out={};
  const n='(\\d{1,3}|ثلاثه?|اربعه?|خمسه?|سته?)';
  const unit=s.match(new RegExp(n+'\\s*(?:شقق|شقه|وحدات سكنيه|apartments?|flats?)','i'));
  if(unit){out.units=quantity(unit[1]);out.scope=/في\s*كل\s*(?:دور|طابق)|كل\s*(?:دور|طابق)\s*\d|لكل\s*(?:دور|طابق)|per\s*(?:floor|storey)/i.test(s)?'per_level':'total';out.unitEvidence=unit[0];}
  if(/شقتين|شقتان/.test(s)){out.units=2;out.scope=/كل\s*(?:دور|طابق)/.test(s)?'per_level':'total';}
  const floors=s.match(new RegExp(n+'\\s*(?:ادوار|طوابق|floors?)','i'));
  if(floors)out.levels=quantity(floors[1]);else if(/دورين|دوران|طابقين|طابقان/.test(s))out.levels=2;
  const bedrooms=s.match(new RegExp('(?:كل شقه|لكل شقه|في الشقه)[^؛\\n]{0,35}?'+n+'\\s*غرف(?:ه)?\\s*نوم'));
  if(bedrooms)out.bedrooms=quantity(bedrooms[1]);
  if(/مجلس\s*(?:منفصل|مستقل)/.test(s))out.guests='separate';
  return out;
}
export function residentialOptions({units,scope='total',levels,width,depth,bedrooms,bathrooms,guests='suggest',purpose='unknown'}) {
  units=Number(units);levels=Number(levels);
  if(!Number.isInteger(units)||units<1||units>100||!Number.isInteger(levels)||levels<1||levels>30)throw new Error('حدد عدد الشقق والأدوار للمقارنة.');
  const total=scope==='per_level'?units*levels:units;
  if(total<levels)throw new Error('عدد الشقق أقل من الأدوار؛ وضّح توزيع الأدوار غير السكنية في وصفك.');
  const distribution=Array.from({length:levels},(_,i)=>Math.floor(total/levels)+(i<total%levels?1:0));
  const variants=[{id:'A',title:'صالة أوسع',bedrooms:2,majlis:0,why:'يعطي مساحة أكبر لاجتماع الأسرة.',tradeoff:'عدد غرف نوم أقل من خيار الأسرة الكبيرة.'},{id:'B',title:'غرف أكثر للأسرة',bedrooms:3,majlis:0,why:'يوفر غرفًا مستقلة لعدد أكبر من أفراد الأسرة.',tradeoff:'تقل المساحة المتاحة للصالة عند ثبات مساحة الشقة.'},{id:'C',title:'خصوصية الضيوف',bedrooms:2,majlis:1,why:'يفصل استقبال الضيوف عن حركة الأسرة.',tradeoff:'المجلس ومدخله يحتاجان مساحة إضافية.'}];
  return variants.map(o=>{
    const count=bedrooms===''||bedrooms==null?o.bedrooms:Number(bedrooms), baths=bathrooms===''||bathrooms==null?2:Number(bathrooms);
    if(!Number.isInteger(count)||count<1||count>8||!Number.isInteger(baths)||baths<1||baths>8)throw new Error('راجع عدد غرف النوم ودورات المياه لكل شقة.');
    const majlis=guests==='separate'?1:guests==='none'?0:o.majlis;
    const areas={bedroom:12,living:o.id==='A'?24:18,kitchen:10,bathroom:4.5,majlis:18,circulation:10};
    const estimatedUnitArea=(count*areas.bedroom+areas.living+areas.kitchen+baths*areas.bathroom+majlis*areas.majlis+areas.circulation)*1.15;
    const available=Number(width)*Number(depth),required=estimatedUnitArea*Math.max(...distribution)+25;
    return {...o,bedrooms:count,bathrooms:baths,majlis,total,distribution,scope,units,areas,
      recommended:(guests==='separate'?o.id==='C':purpose==='family'?o.id==='B':o.id==='A'),
      estimatedUnitArea:Math.round(estimatedUnitArea),requiredFloorArea:Math.round(required),
      feasible:Number.isFinite(available)&&available>0&&required<=available,
      feasibilityNote:'تقدير مساحة أولي يشمل حركة داخلية و15٪ للجدران و25 م² للنواة المشتركة؛ لا يشمل الارتدادات والمواقف. يفحص التوزيع والفتحات بعد التوليد.'};
  });
}
