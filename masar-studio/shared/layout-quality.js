/** Geometric design-review aids, not building-code or circulation certification.
 * Pure reads. Any regenerated layout must be explicitly previewed and accepted.
 */
import { assertModel, clone, generate, validate, checkLocks, roomPolygon, pointInPolygon, round, area, totals, conceptEnvelopeArea, requirementStatus } from './model.js';
import { effectiveAuthoring } from './authoring.js';

// Work on the actual polygon, not its bounding box (an L-shaped bedroom may have
// a large bbox while still being too narrow for even an illustrative bed zone).
export function interiorRectangles(room) {
    const polygon = roomPolygon(room);
    const xs = [...new Set(polygon.map(p => p[0]))].sort((a,b) => a-b);
    const ys = [...new Set(polygon.map(p => p[1]))].sort((a,b) => a-b);
    const grid = xs.slice(1).map((x,i) => ys.slice(1).map((y,j) => pointInPolygon([(x+xs[i])/2,(y+ys[j])/2],polygon,false)));
    const rectangles=[];
    for(let left=0;left<xs.length-1;left++) {
        const occupied=Array(ys.length-1).fill(true);
        for(let right=left;right<xs.length-1;right++) {
            for(let j=0;j<occupied.length;j++) occupied[j]=occupied[j]&&grid[right][j];
            let start=-1;
            for(let j=0;j<=occupied.length;j++) {
                if(occupied[j]&&start<0) start=j;
                if(!occupied[j]&&start>=0) { rectangles.push({x:xs[left],y:ys[start],w:round(xs[right+1]-xs[left]),d:round(ys[j]-ys[start])});start=-1; }
            }
        }
    }
    return rectangles.sort((a,b)=>b.w*b.d-a.w*a.d);
}

// Union adjacent hall polygons before measuring. Splitting a long corridor into
// two named spaces must never make its measured straight extent appear shorter.
function longestHallExtent(rooms) {
    if(!rooms.length) return 0;
    const polygons=rooms.map(roomPolygon);let longest=0;
    for(const vertical of [false,true]) {
        const along=vertical?1:0, across=vertical?0:1;
        const lanes=[...new Set(polygons.flatMap(p=>p.map(v=>v[across])))].sort((a,b)=>a-b);
        for(let j=1;j<lanes.length;j++) {
            if(lanes[j]-lanes[j-1]<=.002)continue;
            const cross=(lanes[j]+lanes[j-1])/2,intervals=[];
            for(const polygon of polygons) {
                const hits=[];
                for(let i=0;i<polygon.length;i++) {
                    const a=polygon[i],b=polygon[(i+1)%polygon.length];
                    if((a[across]<=cross&&b[across]>cross)||(b[across]<=cross&&a[across]>cross))hits.push(a[along]+(cross-a[across])*(b[along]-a[along])/(b[across]-a[across]));
                }
                hits.sort((a,b)=>a-b);for(let i=0;i<hits.length;i+=2)intervals.push([hits[i],hits[i+1]]);
            }
            intervals.sort((a,b)=>a[0]-b[0]);let low=null,high=null;
            for(const [a,b] of intervals) {
                if(low===null||a>high+.002){low=a;high=b;}else high=Math.max(high,b);
                longest=Math.max(longest,high-low);
            }
        }
    }
    return round(longest);
}

export function reviewLayout(model) {
    assertModel(model);
    const rooms=model.levels.flatMap(l=>l.rooms), t=totals(model), envelope=conceptEnvelopeArea(model);
    const wallAllowance=Math.max(.2,...effectiveAuthoring(model).wallTypes.map(w=>w.totalThickness));
    const bedrooms=rooms.filter(r=>r.kind==='bedroom').map(r=>{
        const rects=interiorRectangles(r), largest=rects[0];
        // An illustrative 1.8 x 2 m bed + 0.6 m sides and 0.8 m foot area.
        // This ignores door swings, cupboards, egress and accessibility.
        const bedZoneFits=rects.some(c=>(c.w-wallAllowance>=3&&c.d-wallAllowance>=2.8)||(c.d-wallAllowance>=3&&c.w-wallAllowance>=2.8));
        return {id:r.id,name:r.name,areaM2:area(r),largestRectangle:largest,bedZoneFits};
    });
    return {
        schema:'masar-layout-review-1', envelopeM2:envelope, outsideEnvelopeM2:round(t.landArea-envelope), roomPolygonAreaM2:t.floorArea,
        hallAreaM2:round(rooms.filter(r=>r.kind==='hall').reduce((n,r)=>n+area(r),0)),
        circulationAndReceptionM2:round(rooms.filter(r=>['hall','reception','stairs','elevator'].includes(r.kind)).reduce((n,r)=>n+area(r),0)),
        longestHallExtentM:Math.max(0,...model.levels.map(l=>longestHallExtent(l.rooms.filter(r=>r.kind==='hall')))),
        bedrooms, wallAllowanceM:wallAllowance,
        cautions:[...bedrooms.filter(r=>!r.bedZoneFits).map(r=>({id:r.id,text:`${r.name}: لم نجد داخل المضلع مستطيلاً يتسع لمنطقة سرير توضيحية 3 × 2.8 م بعد بدل الجدران.`}))],
        scope:'Geometric space planning only. Hall extent is not walking/egress distance. Bed-zone fit is not furniture, door-swing, daylight, privacy or code approval.'
    };
}

const geometryOf=m=>JSON.stringify(m.levels.map(l=>({id:l.id,height:l.height,elevation:l.elevation,rooms:l.rooms.map(r=>({id:r.id,kind:r.kind,x:r.x,y:r.y,w:r.w,d:r.d,height:r.height,footprint:r.footprint,doors:r.doors,windows:r.windows,buildingGroup:r.buildingGroup}))})));

/** A constrained, explicit alternative to the shipped 3-bedroom compact template.
 * Never applied on load, never rewrites an edited/locked layout, never changes the
 * plot, outdoor allocations, prompt, requirements, room IDs, comments or finishes.
 */
export function compactCirculationAlternative(base) {
    assertModel(base);
    if(base.design?.layoutStrategy!=='compact-three-bedroom-v1') return {alternative:null,reason:'هذا البديل مخصص للتوزيع المدمج الأول من دور واحد وثلاث غرف نوم.'};
    if(base.levels.flatMap(l=>l.rooms).some(r=>r.locked||[...r.doors,...r.windows||[]].some(o=>o.locked))) return {alternative:null,reason:'توجد غرف أو فتحات مثبتة؛ لن يعيد المقترح توزيعها أو يتجاوز تثبيتها.'};
    let original;
    try {original=generate(clone(base.brief));} catch {return {alternative:null,reason:'البرنامج الأصلي غير متاح لهذا المقترح؛ بقي مشروعك دون تغيير.'};}
    if(geometryOf(base)!==geometryOf(original)) return {alternative:null,reason:'المخطط يحتوي تعديلات هندسية يدوية؛ لا نستبدلها بقالب جديد. تابع التعديل الموضعي مع الحفاظ عليها.'};
    const candidate=clone(base), b=base.brief, sideways=['شرق','غرب'].includes(b.street), W=sideways?b.depth:b.width;
    const k=Math.sqrt((Math.min(b.buildingArea.max,180)-16)/154.72), bx=(W-14*k)/2, by=5.8;
    const previous=new Map(base.levels[0].rooms.map(r=>[r.id,r])), rooms=[];
    function add(id,x,y,w,d) {
        const old=previous.get('l0-'+id);if(!old)throw Error('المساحة الأصلية غير موجودة.');
        const r=clone(old);delete r.footprint;r.x=round(bx+x*k);r.y=round(by+y*k);r.w=round(w*k);r.d=round(d*k);r.doors=[];r.windows=[];r.provenance='generated-short-circulation-concept-v2';rooms.push(r);return r;
    }
    function polygon(r,pts) { r.footprint=pts.map(([x,y])=>[round(bx+x*k),round(by+y*k)]); }
    function door(r,side,offset=.5,width=.85,entry=false,suffix='door') {r.doors.push({id:r.id+'-'+suffix,side,offset,width,height:2.15,entry});}
    function win(r,side,offset=.5,width=1.2) {r.windows.push({id:r.id+'-window',side,offset,width,height:1.2,sill:.9,typeId:base.authoring.defaults.windowTypeId,locked:false,provenance:'generated-concept-window'});}
    const bed2=add('bed2',0,0,3.4,4);door(bed2,'north',2.2/3.4);win(bed2,'west');
    const bed3=add('bed3',3.4,0,3.4,4);door(bed3,'north',1.4/3.4);win(bed3,'south');
    const master=add('master',0,7,4.2,3.8);door(master,'east',.6/3.8);win(master,'north',.5,1.6);
    const ensuite=add('ensuite',0,5.4,2.4,1.6);door(ensuite,'north');
    const wardrobe=add('wardrobe',2.4,5.4,1.8,1.6);door(wardrobe,'north');
    const hall=add('hall',1.4,4,4.2,4.2);polygon(hall,[[1.4,4],[5.6,4],[5.6,8.2],[4.2,8.2],[4.2,5.4],[1.4,5.4]]);
    door(hall,'west',.7/4.2);door(hall,'east',3/4.2,.95,false,'living-door');
    const entry=add('guest-entry',6.8,0,1.8,2);door(entry,'south',.5,1,true);
    const guestBath=add('guest-bath',6.8,2,1.8,2);door(guestBath,'south');
    const majlis=add('majlis',8.6,0,5.4,3);door(majlis,'west',1/3);win(majlis,'south');
    const bath=add('shared-bath',5.6,4,2.2,2);door(bath,'west',.35);
    const pantry=add('pantry',7.8,3,4,2);polygon(pantry,[[8.6,3],[11.8,3],[11.8,5],[7.8,5],[7.8,4],[8.6,4]]);door(pantry,'north',.3);
    const laundry=add('laundry',11.8,3,2.2,2);door(laundry,'north');
    const kitchen=add('kitchen',10.2,7.6,3.8,3.2);door(kitchen,'south',.5,1.4);door(kitchen,'north',.5,1.6,true,'garden-door');win(kitchen,'east');
    const transition=add('transition',0,4,1.4,1.4);door(transition,'west',.5,.9,true);
    const living=add('living',4.2,5,6,5.8);polygon(living,[[7.8,5],[10.2,5],[10.2,10.8],[4.2,10.8],[4.2,8.2],[5.6,8.2],[5.6,6],[7.8,6]]);door(living,'north',4.3/6,2.2,true,'garden-door');
    const dining=add('dining',10.2,5,3.8,2.6);door(dining,'west',.5,1.8);
    function turn(r) {
        if(b.street==='جنوب')return;
        const {x,y,w,d}=r;
        const pt=([a,c])=>b.street==='شمال'?[b.width-a,b.depth-c]:b.street==='شرق'?[b.width-c,a]:[c,b.depth-a];
        if(b.street==='شمال'){r.x=round(b.width-x-w);r.y=round(b.depth-y-d);}else if(b.street==='شرق'){r.x=round(b.width-y-d);r.y=x;r.w=d;r.d=w;}else{r.x=y;r.y=round(b.depth-x-w);r.w=d;r.d=w;}
        if(r.footprint)r.footprint=r.footprint.map(p=>pt(p).map(round));
        const map={شمال:{south:'north',north:'south',east:'west',west:'east'},شرق:{south:'east',north:'west',east:'north',west:'south'},غرب:{south:'west',north:'east',east:'south',west:'north'}}[b.street];
        for(const o of [...r.doors,...r.windows]){const old=o.side;o.side=map[old];if(b.street==='شمال'||b.street==='شرق'&&['east','west'].includes(old)||b.street==='غرب'&&['north','south'].includes(old))o.offset=1-o.offset;}
    }
    rooms.forEach(turn);rooms.push(clone(previous.get('l0-pool-bath')));
    candidate.levels[0].rooms=rooms;candidate.design.layoutStrategy='compact-short-circulation-v2';
    try {
        assertModel(candidate);checkLocks(base,candidate);
        const errors=validate(candidate).filter(x=>x.status==='error');if(errors.length)throw Error(errors.map(x=>x.message).join('؛ '));
        for(const req of base.requirements.filter(r=>r.locked)) {const before=requirementStatus(base,req),after=requirementStatus(candidate,req);if(before.measurable&&before.satisfied&&!after.satisfied)throw Error('المقترح يخالف متطلبًا مثبتًا: '+req.label);}
        const before=reviewLayout(base),after=reviewLayout(candidate);
        if(after.longestHallExtentM>=before.longestHallExtentM||after.hallAreaM2>=before.hallAreaM2)throw Error('لم يتحسن امتداد الممر أو مساحته، لذلك لم نعرض بديلًا مضللًا.');
        return {alternative:{label:'حركة أقصر وغرفة رئيسية أوضح',description:'ممر منكسر أقصر، غرفة رئيسية مستطيلة، معيشة أوسع ومطبخ على الحديقة. مدخل العائلة من الجانب؛ تقل مساحة غرفتي النوم الإضافيتين. راجع المقايضات قبل الاعتماد.',strategy:'short-circulation',model:candidate,beforeReview:before,review:after},reason:null};
    } catch(error) {return {alternative:null,reason:'لم يجتز البديل قيود مشروعك: '+error.message};}
}
