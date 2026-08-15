/* يولّد نماذج بصرية تركيبية بالكامل — أهداف الفيلا/الفندق/المستودع/العيادة/المختلط.
   لا شيء هنا تصميم ولا قيمة تنظيمية: كل عنصر مُضاف synthetic:true و source:test_fixture. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, FIXDIR=path.join(HERE,'fixtures');
const FX=JSON.parse(fs.readFileSync(path.join(FIXDIR,'base_fixtures.json'),'utf8'));
const MS=JSON.parse(fs.readFileSync(path.join(FIXDIR,'mep_fixtures.json'),'utf8'));
const FL=JSON.parse(fs.readFileSync(path.join(FIXDIR,'fls_fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const FIX='test_fixture';
const M={};

/* الأهداف الخمسة كما هي — بلا أي تعديل هندسي */
M.villa=C(FX.villa);
M.hotel=C(FX.hotel);
M.warehouse=C(FX.warehouse);
M.clinic=C(FX.clinic);
M.office=C(FX.office);

/* مختلط الاستعمال: برامج طوابق مختلفة في المبنى نفسه */
{ const b=C(FX.office);
  b.meta={type:'mixed_use',name:'mixed'};
  b.levels=[{index:0,name:'retail',template:'g'},{index:1,name:'office',template:'o'},
            {index:2,name:'resid',template:'r'}];
  b.floors.o=C(b.floors.g);
  b.floors.r={rooms:[{id:'apt1',rect:[0,0,8,6],doors:[{edge:'S',offset:4,width:1}]},
                     {id:'apt2',rect:[8,0,8,6],doors:[{edge:'S',offset:4,width:1}]},
                     {id:'lobby_r',rect:[0,6,16,4],doors:[{edge:'N',offset:8,width:1.6}]}]};
  M.mixed_use=b; }

/* نافذة صريحة: كي تظهر الواجهة والفتحات فعلاً بدل الصفر */
{ const b=C(FX.villa);
  b.floors.g.rooms[0].windows=[{edge:'N',offset:3,width:1.6,height:1.4,sill:0.9}];
  b.floors.g.rooms[4].windows=[{edge:'W',offset:2.5,width:1.2,height:1.4,sill:0.9}];
  b.floors.f.rooms[1].windows=[{edge:'N',offset:3,width:1.6,height:1.4,sill:0.9}];
  M.villa_windows=b; }

/* عناصر يطلبها المستخدم صراحةً: تبقى هندسية ولا تُعامَل ديكوراً */
{ const b=C(FX.villa);
  b.floors.g.rooms[0].objects=[{kind:'sofa',count:2,x:2,z:2},{kind:'table',count:1,x:4,z:3}];
  b.floors.f.rooms[1].objects=[{kind:'bed',count:1,x:3,z:2.5}];
  M.villa_user_objects=b; }

/* عنصر مائي مذكور صراحةً — لا مسبح يُختلق في أي نموذج آخر */
{ const b=C(FX.villa);
  b.site_features=[{id:'pool_1',kind:'pool',x:18,z:4,w:8,d:4,synthetic:true,source:FIX}];
  M.villa_pool=b; }

/* بلا مقاسات موقع: يجب أن تبقى الأرضية بصرية معلنة لا حدود موقع */
{ const b=C(FX.clinic); delete b.site; M.no_site=b; }

/* نموذج فارغ عملياً: يجب ألّا ينهار المشهد */
{ M.degenerate={meta:{type:'other',name:'x'},site:{w:10,d:10},wall_h:3,floor_height:3.2,
    levels:[{index:0,template:'g'}],floors:{g:{rooms:[]}}}; }

/* MEP + حريق حاضران: وضع الهندسة يجب أن يعرض كل التخصّصات */
M.villa_full=C(MS.models.villa_mep);
M.hotel_full=C(MS.models.hotel_mep);
M.clash_full=C(MS.models.clash_mep);
M.fls_full=C(FL.models.villa_fls);

/* إضاءة ليلية عند وحدات إنارة ممثَّلة */
{ const b=C(MS.models.villa_mep);
  b.mep.terminals=(b.mep.terminals||[]).concat([
    {id:'t_l2',system_id:'sys_light',type:'light_fixture',x:10,z:2.5,level:0,source:FIX},
    {id:'t_l3',system_id:'sys_light',type:'light_fixture',x:10,z:7.5,level:0,source:FIX}]);
  M.villa_lights=b; }

const modes=['ENGINEERING','ARCHITECTURAL','PRESENTATION','DOLLHOUSE','CUTAWAY',
             'FLOOR_PLAN_2D','SECTION','ELEVATION','VR'];
const queries=[];
Object.keys(M).sort().forEach(k=>{
  queries.push({n:k+'|PRESENTATION',m:k,bid:'bld_0',pos:null,rot:0,mode:'PRESENTATION',
                theme:'Neutral',light:'DAY',quality:'MEDIUM'});
});
modes.forEach(md=>queries.push({n:'villa|'+md,m:'villa',bid:'bld_0',pos:null,rot:0,mode:md,
  theme:'Modern',light:'DAY',quality:'HIGH'}));
['Modern','Contemporary','Classic','Industrial','Minimal','Luxury','Neutral']
  .forEach(t=>queries.push({n:'villa|theme|'+t,m:'villa',bid:'bld_0',pos:null,rot:0,
    mode:'ARCHITECTURAL',theme:t,light:'DAY',quality:'MEDIUM'}));
['DAY','GOLDEN_HOUR','NIGHT'].forEach(l=>queries.push({n:'villa_lights|'+l,m:'villa_lights',
  bid:'bld_0',pos:null,rot:0,mode:'PRESENTATION',theme:'Neutral',light:l,quality:'MEDIUM'}));
['LOW','MEDIUM','HIGH','ULTRA'].forEach(q=>queries.push({n:'hotel|q|'+q,m:'hotel',bid:'bld_0',
  pos:null,rot:0,mode:'PRESENTATION',theme:'Neutral',light:'DAY',quality:q}));
queries.push({n:'villa@rot45',m:'villa',bid:'bld_0',pos:{x:-6,z:4},rot:45,
  mode:'PRESENTATION',theme:'Neutral',light:'DAY',quality:'MEDIUM'});
queries.push({n:'villa@bld_7',m:'villa',bid:'bld_7',pos:null,rot:0,
  mode:'ENGINEERING',theme:'Neutral',light:'DAY',quality:'MEDIUM'});
queries.push({n:'clash_full|ENGINEERING+overlay',m:'clash_full',bid:'bld_0',pos:null,rot:0,
  mode:'ENGINEERING',theme:'Neutral',light:'DAY',quality:'MEDIUM',clash:true});
queries.push({n:'villa|deco',m:'villa',bid:'bld_0',pos:null,rot:0,mode:'DOLLHOUSE',
  theme:'Modern',light:'DAY',quality:'HIGH',deco:true});
queries.push({n:'villa|entourage',m:'villa',bid:'bld_0',pos:null,rot:0,mode:'PRESENTATION',
  theme:'Modern',light:'DAY',quality:'HIGH',deco:true,ent:true,entn:6});
queries.push({n:'villa_pool|PRESENTATION',m:'villa_pool',bid:'bld_0',pos:null,rot:0,
  mode:'PRESENTATION',theme:'Neutral',light:'DAY',quality:'MEDIUM'});

const drawings=[];
['villa','villa_windows','hotel','warehouse','clinic','mixed_use','degenerate'].forEach(k=>{
  [0,1,2].forEach(li=>drawings.push({n:k+'|plan|'+li,m:k,kind:'plan',level:li,style:'TECHNICAL'}));
  ['x','z'].forEach(ax=>drawings.push({n:k+'|section|'+ax,m:k,kind:'section',axis:ax}));
  ['NORTH','SOUTH','EAST','WEST'].forEach(f=>drawings.push({n:k+'|elev|'+f,m:k,kind:'elevation',
    face:f}));
});
['TECHNICAL','CLEAN','MONOCHROME','ZONING'].forEach(st=>drawings.push(
  {n:'villa|plan|style|'+st,m:'villa',kind:'plan',level:0,style:st}));
[2.5,10.0,11.4].forEach(p=>drawings.push({n:'villa|section|x@'+p,m:'villa',kind:'section',
  axis:'x',position:p}));

fs.writeFileSync(path.join(FIXDIR,'visual_scenarios.json'),
  JSON.stringify({models:M,queries:queries,drawings:drawings}));
console.log('visual scenarios:',Object.keys(M).length,'queries:',queries.length,
            'drawings:',drawings.length);
