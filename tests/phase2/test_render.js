/* ======================================================================
   المرحلة 2 — اختبار العارض: البلاطة تُقصّ عند النوى الرأسية فعلاً.
   يشغّل شيفرة compile() نفسها في المستودع مقابل بديل THREE يسجّل الصناديق:
   هذا يتحقّق من الهندسة المرسومة، لا من البكسل. عرض WebGL الحقيقي غير مُتحقَّق
   منه هنا ويُبلَّغ عنه صراحةً — NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));

const boxes=[];
globalThis.THREE={
  Group:function(){ this.children=[]; this.name=''; this.add=function(o){this.children.push(o);}; },
  BoxGeometry:function(x,y,z){ this.p=[x,y,z]; },
  Mesh:function(g,m){ this.g=g; this.m=m; this.name=''; this.castShadow=false;
    this.receiveShadow=false; this.rotation={y:0}; this.visible=true; this.userData={};
    this.position={x:0,y:0,z:0,set:(a,b,c)=>{this.position.x=a;this.position.y=b;this.position.z=c;}};
    boxes.push(this); }
};
/* الخامات مستبعدة عمداً: هذا فحص هندسة لا مظهر، وخامة حقيقية تحتاج WebGL.
   قبل F-09 كان المستخرج يترك getMat خارج الحزمة فيكفي تعريفه على globalThis؛
   صارت الحزمة تحمل الأصل، فالإبدال يجري على الارتباط نفسه ويُتحقَّق منه. */
getMat=()=>({userData:{}});
scaleBoxUV=()=>{};
OBJ_UNKNOWN=[];
if(getMat('x').map!==undefined)
  throw new Error('the material stub did not take effect — this suite would then '
    +'be making a pixel claim it cannot verify');

const run=(model)=>{ boxes.length=0; const g=compile(C(model));
  return {group:g, boxes:boxes.slice()}; };
const slabs=(bx,fkey)=>bx.filter(b=>b.name.indexOf('FLOOR|'+fkey+'|slab|')===0);

console.log('\n== §16 — SLAB IS CUT AT VERTICAL CORES ==');
{ const r=run(FX.villa);
  const arch=compileArchitecture(C(FX.villa),'bld_0');
  const voids=arch.voids.filter(v=>v.level_index===1);
  chk('the villa model does have a stair void on level 1', voids.length===1, voids.length);
  const s0=slabs(r.boxes,'F0'), s1=slabs(r.boxes,'F1');
  chk('a level with no void still renders a single slab box', s0.length===1, s0.length);
  chk('the level the stair passes through renders several slab strips instead of one',
      s1.length>1, s1.length);
  const site=FX.villa.site;
  const area=s1.reduce((s,b)=>s+b.g.p[0]*b.g.p[2],0);
  /* ── F-07 / KI-3 — PHASE1_SITE_WIDE_PLATE ← PHASE10_FOOTPRINT_PLATE ──────
     كان لوح كل دور يُبنى على مستطيل الموقع كلّه، فكان المتوقَّع هنا
     site.w*site.d − hole = 30×24 − 1.2×4.2 = 720 − 5.04 = 714.96. صار امتداد
     اللوح اتحادَ بصمات غرف الدور نفسه (عقد pqPlateRect وحده)، والموقع مستوى
     عرضٍ منفصل. المتوقَّع الجديد يُشتقّ من التجهيزة لا يُكتب رقماً:

       غرف الدور 1: [6,0,2,10] [0,0,6,5] [8,0,6,5] [8,5,6,5] [0,5,3,3]
       اتحاد بصماتها = [0,0,14,10]                    → 14 × 10 = 140
       فراغ الدرج    = [6.4,5.9,1.2,4.2] يمتدّ إلى z=10.1 أي 0.1 م خارج اللوح
                       (بصمة النواة احتياط عرض حول موضع مستنتَج)، فما يُقصّ
                       من اللوح هو تقاطعه معه = [6.4,5.9,1.2,4.1] → 4.92
       المتوقَّع = 140 − 4.92 = 135.08

     التوكيدة لم تُضعَّف بل شُدّت: يُتحقَّق أوّلاً أن امتداد اللوح المرسوم هو
     اتحاد بصمات الدور بعينه (لا المساحة وحدها)، ثم أن المجموع مطابق تماماً،
     ثم أن الامتداد لم يعد امتداد الموقع — فلا يعود PHASE1_SITE_WIDE_PLATE
     خِلسةً ويمرّ. */
  const lvl1=(FX.villa.levels||[]).filter(l=>l.index===1)[0];
  const rects=((FX.villa.floors||{})[lvl1.template]||{}).rooms.map(r=>r.rect);
  const px0=Math.min.apply(null,rects.map(r=>r[0]));
  const pz0=Math.min.apply(null,rects.map(r=>r[1]));
  const px1=Math.max.apply(null,rects.map(r=>r[0]+r[2]));
  const pz1=Math.max.apply(null,rects.map(r=>r[1]+r[3]));
  const span=(a0,a1,b0,b1)=>Math.max(0,Math.min(a1,b1)-Math.max(a0,b0));
  const drawn={x0:Math.min.apply(null,s1.map(b=>b.position.x-b.g.p[0]/2)),
               z0:Math.min.apply(null,s1.map(b=>b.position.z-b.g.p[2]/2)),
               x1:Math.max.apply(null,s1.map(b=>b.position.x+b.g.p[0]/2)),
               z1:Math.max.apply(null,s1.map(b=>b.position.z+b.g.p[2]/2))};
  chk('F-07: the plate spans the level room-footprint union, not the site',
      Math.abs(drawn.x0-px0)<1e-6&&Math.abs(drawn.z0-pz0)<1e-6
      &&Math.abs(drawn.x1-px1)<1e-6&&Math.abs(drawn.z1-pz1)<1e-6,
      JSON.stringify(drawn)+' vs ['+[px0,pz0,px1,pz1].join(',')+']');
  /* الفراغ يُقصّ على حدود اللوح: ما خرج عنه لم يكن مرسوماً أصلاً */
  const hole=voids.reduce((s,v)=>s+span(v.rect[0],v.rect[0]+v.rect[2],px0,px1)
                                  *span(v.rect[1],v.rect[1]+v.rect[3],pz0,pz1),0);
  const expected=(px1-px0)*(pz1-pz0)-hole;
  chk('the rendered strips total exactly the plate area minus the void area',
      Math.abs(area-expected)<1e-6, area+' vs '+expected);
  chk('F-07: and that total is no longer the old site-wide plate figure',
      Math.abs(area-(site.w*site.d
        -voids.reduce((s,v)=>s+v.rect[2]*v.rect[3],0)))>1e-6,
      area+' vs old '+(site.w*site.d
        -voids.reduce((s,v)=>s+v.rect[2]*v.rect[3],0)));
  const inside=(b,v)=>{ const x0=b.position.x-b.g.p[0]/2, x1=b.position.x+b.g.p[0]/2;
    const z0=b.position.z-b.g.p[2]/2, z1=b.position.z+b.g.p[2]/2;
    return x0+1e-9<v.rect[0]+v.rect[2] && x1-1e-9>v.rect[0] &&
           z0+1e-9<v.rect[1]+v.rect[3] && z1-1e-9>v.rect[1]; };
  chk('no rendered strip covers any part of the stair void',
      s1.every(b=>voids.every(v=>!inside(b,v))));
  chk('every strip keeps the Phase 1 slab thickness and elevation',
      s1.every(b=>Math.abs(b.g.p[1]-0.15)<1e-12));
  chk('all slab boxes still carry the FLOOR| naming Phase 1 selection depends on',
      r.boxes.filter(b=>/\|slab\|/.test(b.name)).every(b=>/^FLOOR\|F\d+\|slab\|\d+$/.test(b.name))); }

console.log('\n== §17 — NO PHASE 1 RENDER REGRESSION ==');
{ const before=(m)=>{ /* السلوك القديم: لوح واحد بمقاس الموقع لكل مستوى */
    return (m.levels||[]).length; };
  ['clinic','warehouse'].forEach(n=>{ const r=run(FX[n]);
    const a=compileArchitecture(C(FX[n]),'bld_0');
    chk(n+': no vertical core ⇒ exactly one slab per level, as before',
        a.voids.length===0&&
        (FX[n].levels||[]).every(l=>slabs(r.boxes,'F'+l.index).length===1)); });
  const r=run(FX.hotel);
  chk('hotel: rooms and walls are still built on every level',
      r.boxes.some(b=>/^WALL\|F0\|/.test(b.name))&&r.boxes.some(b=>/^WALL\|F1\|/.test(b.name)));
  /* الحائط الحامل لباب يخرج كعدّة مقاطع صلبة (يسار · يمين · عتب) لا كلوح واحد */
  { const per={};
    r.boxes.filter(b=>/^WALL\|/.test(b.name)).forEach(b=>{
      const k=b.name.replace(/\d+$/,''); per[k]=(per[k]||0)+1; });
    chk('hotel: an edge carrying a door is split into several solid segments',
        per['WALL|F1|guest_1|wSs']===3, per['WALL|F1|guest_1|wSs']);
    chk('hotel: an edge with no opening stays a single solid segment',
        per['WALL|F1|guest_1|wNs']===1, per['WALL|F1|guest_1|wNs']); }
  chk('compile still returns a group named BUILDING', r.group.name==='BUILDING');
  chk('compile never emits a zero-size box', r.boxes.every(b=>b.g.p.every(v=>v>0))); }

console.log('\n== §18 — STRIP GEOMETRY IS EXACT, NOT APPROXIMATE ==');
{ chk('a hole in the middle yields four strips around it',
      slabStrips(0,0,10,10,[[4,4,2,2]]).length===4,
      JSON.stringify(slabStrips(0,0,10,10,[[4,4,2,2]])));
  chk('a hole touching an edge yields three strips',
      slabStrips(0,0,10,10,[[0,4,2,2]]).length===3);
  chk('a hole covering the whole plate yields no strip',
      slabStrips(0,0,10,10,[[0,0,10,10]]).length===0);
  chk('a hole entirely outside the plate is ignored',
      slabStrips(0,0,10,10,[[20,20,2,2]]).length===1);
  chk('a hole partly outside is clipped, not dropped',
      Math.abs(slabStrips(0,0,10,10,[[-1,4,3,2]]).reduce((s,r)=>s+r[2]*r[3],0)-(100-4))<1e-9);
  chk('two holes both get cut',
      Math.abs(slabStrips(0,0,10,10,[[1,1,2,2],[6,6,2,2]])
        .reduce((s,r)=>s+r[2]*r[3],0)-(100-8))<1e-9);
  chk('overlapping holes are not double-subtracted',
      Math.abs(slabStrips(0,0,10,10,[[1,1,3,3],[2,2,3,3]])
        .reduce((s,r)=>s+r[2]*r[3],0)-(100-(9+9-4)))<1e-9);
  chk('no strip has zero or negative extent',
      slabStrips(0,0,10,10,[[4,4,2,2],[0,0,1,1]]).every(r=>r[2]>0&&r[3]>0)); }

console.log('\n== §19 — STRUCTURAL DEBUG LAYER IN THE RENDERER ==');
{ const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'struct_scen.json'),'utf8'));
  const r=run(SC.models.villa_struct);
  const sb=r.boxes.filter(b=>/^STRUCT\|/.test(b.name));
  chk('structural boxes are emitted into the scene', sb.length>0, sb.length);
  chk('they use the STRUCT| naming convention for GLB export',
      sb.every(b=>/^STRUCT\|(COLUMN|BEAM|SLAB|WALL|CORE|FOUNDATION)\|bld_0\./.test(b.name)));
  chk('every structural box is hidden by default', sb.every(b=>b.visible===false));
  chk('every structural box records where its geometry came from',
      sb.every(b=>['model','display_fallback'].indexOf(b.userData.struct.geometry_source)>=0));
  chk('a column box is present for every compiled column',
      sb.filter(b=>b.userData.struct.kind==='COLUMN').length===
      compileStructure(C(SC.models.villa_struct),'bld_0').columns.length);
  chk('grid lines are NOT drawn as solid boxes',
      sb.every(b=>b.userData.struct.kind!=='GRID_LINE'));
  const plain=run(FX.villa);
  chk('a model with no structural data emits no structural box',
      plain.boxes.filter(b=>/^STRUCT\|/.test(b.name)).length===0);
  chk('the architectural boxes are identical with and without structural data',
      JSON.stringify(plain.boxes.filter(b=>!/^STRUCT\|/.test(b.name)).map(b=>[b.name,b.g.p]))===
      JSON.stringify(r.boxes.filter(b=>!/^STRUCT\|/.test(b.name)).map(b=>[b.name,b.g.p])));
  chk('a warehouse whose sections are unknown still draws, but as display fallback',
      (()=>{const w=run(SC.models.warehouse_struct);
        const wb=w.boxes.filter(b=>/^STRUCT\|COLUMN/.test(b.name));
        return wb.length>0&&wb.every(b=>b.userData.struct.geometry_source==='display_fallback');})());
  chk('colour marks the element kind, never a safety state',
      Object.keys(STRUCT_KIND_COLOR).every(k=>STRUCT_ELEMENT_TYPES.indexOf(k)>=0)); }

console.log('\n== §20 — MEP DEBUG LAYERS IN THE RENDERER ==');
{ const MC=JSON.parse(fs.readFileSync(_np.join(FIXD,'mep_scen.json'),'utf8'));
  const r=run(MC.models.villa_mep);
  const mb=r.boxes.filter(b=>/^MEP\|/.test(b.name));
  chk('MEP boxes are emitted into the scene', mb.length>0, mb.length);
  chk('they use the MEP| naming convention for GLB export',
      mb.every(b=>/^MEP\|(ELECTRICAL|LIGHTING|ICT|PLUMBING|DRAINAGE|HVAC|FIRE|OTHER|RISER)\|/
        .test(b.name)));
  chk('every MEP box is hidden by default', mb.every(b=>b.visible===false));
  chk('every MEP box records where its geometry came from',
      mb.every(b=>['model','display_fallback'].indexOf(b.userData.mep.geometry_source)>=0));
  chk('an unrouted duct draws nothing at all',
      mb.every(b=>b.userData.mep.id!=='bld_0.mep.seg_sup_1'));
  const plain=run(FX.villa);
  chk('a model with no MEP data emits no MEP box',
      plain.boxes.filter(b=>/^MEP\|/.test(b.name)).length===0);
  chk('the architectural boxes are identical with and without MEP data',
      JSON.stringify(plain.boxes.filter(b=>!/^(MEP|STRUCT)\|/.test(b.name))
        .map(b=>[b.name,b.g.p]))===
      JSON.stringify(r.boxes.filter(b=>!/^(MEP|STRUCT)\|/.test(b.name)).map(b=>[b.name,b.g.p])));
  chk('a warehouse whose sizes are unknown still draws, but as display fallback',
      (()=>{const w=run(MC.models.warehouse_mep);
        const wb=w.boxes.filter(b=>/^MEP\|/.test(b.name)&&b.userData.mep.kind==='SEGMENT');
        return wb.length>0&&wb.every(b=>b.userData.mep.geometry_source==='display_fallback');})());
  chk('adapted Phase 1 points are drawn and marked as adapted',
      (()=>{const a=run(MC.models.phase1_points);
        const ab=a.boxes.filter(b=>/^MEP\|/.test(b.name));
        return ab.length===5&&ab.every(b=>b.userData.mep.adapted===true);})());
  chk('colour marks the discipline, never a safety state',
      Object.keys(MEP_DISC_COLOR).every(k=>MEP_DISCIPLINES.indexOf(k)>=0||k==='RISER')); }

console.log('\n== §21 — FLS DEBUG LAYERS IN THE RENDERER ==');
{ const FC=JSON.parse(fs.readFileSync(_np.join(FIXD,'fls_scen.json'),'utf8'));
  const r=run(FC.models.villa_fls);
  const fb=r.boxes.filter(b=>/^FLS\|/.test(b.name));
  chk('FLS boxes are emitted into the scene', fb.length>0, fb.length);
  chk('they use the FLS| naming convention for GLB export',
      fb.every(b=>/^FLS\|[A-Z_]+\|bld_0\.fls\./.test(b.name)));
  chk('every FLS box is hidden by default', fb.every(b=>b.visible===false));
  chk('every FLS box declares its geometry is a display fallback',
      fb.every(b=>b.userData.fls.geometry_source==='display_fallback'));
  chk('only emitted items are drawn — referenced MEP devices are not duplicated',
      fb.every(b=>b.userData.fls.render_mode==='emitted'));
  const p1=run(FC.models.phase1_fls);
  chk('a Phase 1 adapted detector is NOT drawn a second time by the FLS layer',
      p1.boxes.filter(b=>/^FLS\|/.test(b.name)).length===0&&
      p1.boxes.filter(b=>/^MEP\|/.test(b.name)).length===5);
  const plain=run(FX.villa);
  chk('a model with no FLS data emits no FLS box',
      plain.boxes.filter(b=>/^FLS\|/.test(b.name)).length===0);
  chk('the architectural boxes are identical with and without FLS data',
      JSON.stringify(plain.boxes.filter(b=>!/^(MEP|STRUCT|FLS)\|/.test(b.name))
        .map(b=>[b.name,b.g.p]))===
      JSON.stringify(r.boxes.filter(b=>!/^(MEP|STRUCT|FLS)\|/.test(b.name))
        .map(b=>[b.name,b.g.p])));
  chk('colour marks the layer, never a compliance state',
      Object.keys(FLS_LAYER_COLOR).every(k=>FLS_RENDER_LAYERS.indexOf(k)>=0)); }

console.log(`\nRENDER: ${pass} passed, ${fail} failed`);
