// Added by the customer regression patch. These functions use the canonical model helpers.
function customerProjectType(text) {
    const lead = text.split(/[\n.!؟،]/)[0];
    const classify = s => {
        if (/فيلا\s+(?:بنظام|على\s+نظام|بطابع)\s+شاليه/.test(s)) return 'chalet';
        const match = s.match(/شاليه|فيلا|منزل|مستودع|مخزن|warehouse|مكاتب|مكتب اداري|office|متجر|محل تجاري|تجز[يئ]ه|retail/);
        if (!match) return null;
        return /شاليه/.test(match[0]) ? 'chalet' : /فيلا|منزل/.test(match[0]) ? 'villa' : /مستودع|مخزن|warehouse/.test(match[0]) ? 'warehouse' : /مكاتب|مكتب اداري|office/.test(match[0]) ? 'office' : 'retail';
    };
    return classify(lead) || classify(text) || 'villa';
}
function customerAreaBudget(text) {
    const unit='(?:م(?:²|2)|متر(?:ا)?\\s*مربع(?:ا)?)', number='(\\d+(?:\\.\\d+)?)';
    const range=new RegExp(number+'\\s*(?:–|—|-|الى|إلى)\\s*'+number+'\\s*'+unit+'\\s*(?:مباني|مبان|بناء|بنا|مبنيه)');
    const before=new RegExp('(?:مساحه\\s*(?:البناء|المبني|المباني)|مساحه\\s*بناء)[^\\d\\n]{0,20}'+number+'(?:\\s*(?:–|—|-|الى)\\s*'+number+')?\\s*'+unit);
    const exactAfter=new RegExp(number+'\\s*'+unit+'\\s*(?:مباني|مبان|بناء|بنا|مبنيه)');
    const m=text.match(range)||text.match(before)||text.match(exactAfter);
    if (!m) return null;
    const a=Number(m[1]),b=Number(m[2]||m[1]);
    return {min:a,max:b,source:'requested',metric:'conservative-concept-ground-envelope'};
}
// Conservative plan-area envelope including the maximum conceptual wall half-thickness.
// Rectangle bounds make this an upper bound for notched spaces, not a permit area calculation.
export function conceptEnvelopeArea(m) {
    const thickness=Math.max(...effectiveAuthoring(m).wallTypes.map(t=>t.totalThickness),.2), pad=thickness/2;
    const rs=m.levels[0].rooms.map(r=>({x:r.x-pad,y:r.y-pad,w:r.w+2*pad,d:r.d+2*pad}));
    const xs=[...new Set(rs.flatMap(r=>[r.x,r.x+r.w]))].sort((a,b)=>a-b);
    let area=0;
    for(let i=0;i<xs.length-1;i++){
        const mid=(xs[i]+xs[i+1])/2, intervals=rs.filter(r=>mid>r.x&&mid<r.x+r.w).map(r=>[r.y,r.y+r.d]).sort((a,b)=>a[0]-b[0]);
        let lo=null,hi=null,total=0;
        for(const [a,b] of intervals){if(lo===null){lo=a;hi=b;}else if(a<=hi)hi=Math.max(hi,b);else{total+=hi-lo;lo=a;hi=b;}}
        if(lo!==null)total+=hi-lo;
        area+=(xs[i+1]-xs[i])*total;
    }
    return round(area);
}
function applyCustomerBudget(m,b) {
    if(!b.buildingArea) return m;
    const budget=b.buildingArea;
    if(!Number.isFinite(budget.min)||!Number.isFinite(budget.max)||budget.min<=0||budget.max<budget.min)throw Error('نطاق مساحة المباني غير صالح. أدخل حدًا أدنى موجبًا وحدًا أعلى لا يقل عنه.');
    if(!['villa','chalet'].includes(b.projectType)||b.floors!==1||b.bedrooms!==3||b.elevator)throw Error('المخطط المدمج محدود المساحة يدعم حاليًا فيلا أو شاليه من دور واحد وثلاث غرف نوم دون مصعد. لم نغيّر طلبك أو نتجاوز المساحة؛ راجع هذه القيم أو أزل قيد المساحة صراحة.');
    const rotated=['شرق','غرب'].includes(b.street), W=rotated?b.depth:b.width,D=rotated?b.width:b.depth;
    if(W<17||D<23||budget.max<140||b.parking>1)throw Error('البرنامج المدمج الحالي يحتاج عرضًا مواجهًا للشارع 17 م وعمقًا 23 م على الأقل، وحد مساحة مباني 140 م² أو أكثر وموقفًا واحدًا كحد أقصى. لم يتم توليد بديل مخالف؛ راجع القيم أو البرنامج.');
    const cap=Math.min(budget.max,180), k=Math.sqrt((cap-16)/154.72), bw=14*k,bd=10.8*k,bx=(W-bw)/2,by=5.8;
    if(budget.min>cap||by+bd+6>D)throw Error('قيد المساحة أو مساحة الحوش لا يلائمان هذا البرنامج المدمج. لم يتم توسيع المبنى أو تغيير الأرض تلقائيًا.');
    const rooms=[];
    const add=(id,name,kind,x,y,w,d,side='east',offset=.5,entry=false)=>{const r=room('l0-'+id,name,kind,bx+x*k,by+y*k,w*k,d*k,side,entry);r.doors[0].offset=offset; r.provenance='generated-compact-concept-v1';rooms.push(r);return r;};
    const bed2=add('bed2','غرفة نوم 2','bedroom',0,0,5,3.2);
    const bed3=add('bed3','غرفة نوم 3','bedroom',0,3.2,5,3.2);
    const master=add('master','غرفة النوم الرئيسية','bedroom',0,6.4,5,4.4);
    master.footprint=[[2.5,6.4],[5,6.4],[5,10.8],[0,10.8],[0,9.6],[2.5,9.6]].map(([x,y])=>[round(bx+x*k),round(by+y*k)]);
    add('ensuite','حمام الغرفة الرئيسية','bath',0,6.4,2.5,1.7);
    add('wardrobe','غرفة ملابس الرئيسية','storage',0,8.1,2.5,1.5);
    const hall=add('hall','توزيع العائلة','hall',5,0,1.2,10.8,'south',.5,true);
    hall.doors.push({id:'l0-hall-rear',side:'north',offset:.5,width:.85,entry:true});
    const lobby=add('guest-entry','مدخل الضيوف المستقل','reception',6.2,0,1.6,3.2,'south',.5,true);
    // A controllable door, not an open passage, separates guests from family circulation.
    lobby.doors.push({id:'l0-guest-family-door',side:'west',offset:.7,width:.85,entry:false});
    add('guest-bath','حمام ومغاسل الضيوف','bath',7.8,0,1.8,1.6,'west');
    const majlis=add('majlis','مجلس الضيوف','majlis',7.8,0,6.2,3.2,'west',.75);
    majlis.footprint=[[9.6,0],[14,0],[14,3.2],[7.8,3.2],[7.8,1.6],[9.6,1.6]].map(([x,y])=>[round(bx+x*k),round(by+y*k)]);
    add('shared-bath','الحمام المشترك','bath',6.2,3.2,2.2,2.2,'west');
    add('pantry','بانتري','storage',8.4,3.2,1.8,1.6,'east');
    add('laundry','غرفة الغسيل','laundry',8.4,4.8,1.8,1.6,'east');
    const kitchen=add('kitchen','المطبخ الرئيسي','kitchen',10.2,3.2,3.8,3.2,'north');
    add('transition','توزيع الخدمات','hall',6.2,5.4,2.2,1,'west');
    const living=add('living','المعيشة العائلية','living',6.2,6.4,5,4.4,'west');
    living.doors.push({id:'l0-living-garden-door',side:'north',offset:.5,width:2.2,entry:true});
    living.note='فتحة خارجية واسعة إلى الحديقة؛ نوع الباب المنزلق وتفاصيله الإنشائية لم تعتمد.';
    const dining=add('dining','منطقة الطعام','dining',11.2,6.4,2.8,4.4,'west');
    const externalBath=room('l0-pool-bath','دورة مياه المسبح','bath',W-3.3,by+bd+.9,1.6*k,2.2*k,'east',true);rooms.push(externalBath);
    const window=(r,side,offset=.5,width=1.2)=>r.windows=[{id:r.id+'-window',side,offset,width:Math.min(width,sideSpan(r,side)-.3),height:1.2,sill:.9,typeId:m.authoring.defaults.windowTypeId,locked:false,provenance:'generated-concept-window'}];
    window(bed2,'west');window(bed3,'west');window(master,'north');window(majlis,'south',.68);window(kitchen,'east');window(dining,'north');
    m.levels=[{id:'l0',name:'الدور الأرضي',elevation:0,height:3.3,rooms}];
    m.site.setback={front:by,back:1,left:1,right:1};
    m.site.features=[{id:'parking-1',type:'parking',name:'موقف سيارة مفاهيمي',x:W-3.7,y:.3,w:2.7,d:5,locked:true,provenance:'requested-concept-feature'},
      {id:'terrace-1',type:'terrace',name:'جلسة مغطاة وبرجولة — موضع مبدئي',x:bx,y:by+bd+1.1,w:4,d:3.5,locked:true,provenance:'requested-concept-feature'},
      {id:'bbq-1',type:'terrace',name:'شواء وتحضير — موضع مبدئي',x:bx,y:by+bd+4.9,w:2.8,d:1.4,locked:true,provenance:'requested-concept-feature'}];
    if(b.parking===0)m.site.features=m.site.features.filter(f=>f.type!=='parking');
    if(b.pool)m.site.features.push({id:'pool-1',type:'pool',name:'مسبح مستطيل مفاهيمي',x:bx+6.1*k,y:by+bd+2.1,w:6,d:3,locked:true,provenance:'requested-concept-feature'});
    m.site.features.push({id:'garden-1',type:'garden',name:'حديقة خلفية — الباقي ساحات وحركة',x:1,y:D-2.1,w:W-2,d:1.6,locked:false,provenance:'concept-landscape-allocation'});
    const turn=(r)=>{const {x,y,w,d}=r;const maps={شمال:{south:'north',north:'south',east:'west',west:'east'},شرق:{south:'east',north:'west',east:'north',west:'south'},غرب:{south:'west',north:'east',east:'south',west:'north'}};
      const pt=([a,c])=>b.street==='شمال'?[b.width-a,b.depth-c]:b.street==='شرق'?[b.width-c,a]:[c,b.depth-a];
      if(b.street==='جنوب')return;
      if(b.street==='شمال'){r.x=round(b.width-x-w);r.y=round(b.depth-y-d);}else if(b.street==='شرق'){r.x=round(b.width-y-d);r.y=x;r.w=d;r.d=w;}else{r.x=y;r.y=round(b.depth-x-w);r.w=d;r.d=w;}
      if(r.footprint)r.footprint=r.footprint.map(p=>pt(p).map(round));
      for(const o of [...r.doors||[],...r.windows||[]]){const old=o.side;o.side=maps[b.street][old];if(b.street==='شمال'||b.street==='شرق'&&['east','west'].includes(old)||b.street==='غرب'&&['north','south'].includes(old))o.offset=round(1-o.offset);}
    };
    [...rooms,...m.site.features].forEach(turn);
    m.requirements.push({id:'r-building-area',label:`مساحة المباني المطلوبة ${budget.min}–${budget.max} م²`,type:'building-area',value:[budget.min,budget.max],source:'requested',locked:true});
    m.requirements.push({id:'r-compact-review',label:'البرنامج المدمج اقتراح مبدئي: راجع عرض الممرات وخصوصية الزجاج وصوت المسبح، والجزيرة والأثاث ومغاسل الضيوف وتفاصيل الشواء والبرجولة مع المصمم. وجود المساحة لا يثبت كفايتها.',type:'custom',source:'requested',locked:true});
    m.design.layoutStrategy='compact-three-bedroom-v1';
    const envelope=conceptEnvelopeArea(m);
    if(envelope>budget.max+.05||envelope<budget.min-.05)throw Error(`المقترح داخل المحرك يحتاج غلافًا مساحته ${envelope} م² مقابل نطاقك ${budget.min}–${budget.max}. لم نتجاوز قيدك تلقائيًا.`);
    return m;
}
