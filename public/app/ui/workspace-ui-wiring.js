/* ============================================================
   public/app/ui/workspace-ui-wiring.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { __ACS_SHARED } from '../shared-state.js';
import { __ACS_LATE } from '../late-bindings.js';
import { _sMaterialName, archDoorConnectsConfirmed, archElementById, archSharedWallBetween, archSummary, compileArchitecture, compileFls, compileMep, compileStructure, flsAudit, flsEgressFacts, flsElementById, flsRenderItems, flsRuleInputs, flsSummary, mepElementById, mepInterferences, mepRenderItems, mepRuleInputs, mepSummary, mepSystemById, structElementById, structGridToWorld, structRenderItems, structRuleInputs, structSummary, suggestStructuralGrid } from '../core/disciplines.js';
import { activeOccupancyPacks, addOccupancyClassification, aggregateRuleResults, allRules, assessCandidate, auditOccupancy, canonicalBuilding, canonicalProject, checkResultIntegrity, declareOccupancy, evaluateProject, evaluateRule, evaluateRuleSet, exportOccupancy, exportSnapshot, fragmentsOf, ingCandidate, ingRulePack, ingestAuditExport, ingestStoreIssues, modelHash, modelRevision, occClassification, occPack, occPacks, occupancyIndex, occupancyIssues, regulatoryRuleCount, resolveActiveRules, resolveOccupancy, resolveSubject, revisionDiff, ruleDefinitionHash, ruleIssues, ruleMatches, ruleSetById, ruleSets, ruleSources, snapshotResult, staleResults, suggestOccupancyFromProgram, validateRule, verifyCandidate, verifyOccupancy, verifyOccupancyPack, verifyPack } from '../core/standards.js';
import { ACS_PROJECT_CODE_CONTEXT, ARButton, SCENE_LIMITS, acsBuildDefect, acsBuildDefects, acsCompileSummary, acsFloorIndex, acsFloorName, acsFloorOrder, GLTFExporter, LAYER_NAMES, LAYER_ORDER, OrbitControls, THREE, VRButton, activeBuilding, addBox, attachObjects, auditEgress, buildNavGraph, buildRelationships, classifyReport, compile, detectMeta, distanceSummary, egressSummary, extractExits, findEgress, findPath, getMat, isProjectModel, knownSpaces, matCache, measurePath, navIssues, normDigits, normHex, objCoverage, objectsFromText, parseDescription, pathSummary, projectEnvelope, relationshipSummary, stampMeta, stripBidi, toProject, validateExits, validateMeasurement, validateRelationships, warehouseFromText, warehouseModel } from '../core/viewer.js';
import { acsReconcileCamera, acsRecoverBlackViewport } from '../generated/pbr-bridge.js';
import { VIS_CAMERA_PRESETS, VIS_MATERIALS, VIS_MODES, VIS_STATE, VIS_THEMES, applyVisualMode, checkCoordSnapshot, clearVisualMode, compileCoordination, compileVisualScene, coordClashById, coordDebugView, coordExportSnapshot, coordFilterClashes, coordReconcile, coordRuleInputs, coordSetStatus, detectTypeJS, isIndustrialProgram, renderer, scene, sky, statusEl, su, sun, visAiEnhancementRequest, visAssetLibrary, visCheckConsistency, visCheckRenderCurrency, visControlBuffers, visElevation, visExportScene, visFloorPlan, visFrameCamera, visGeometrySignature, visInstancingPlan, visLodPlan, visMaterial, visObjectById, visObjectsByLayer, visPresentationBlock, visRenderMetadata, visRuleInputs, visSection, visSetLayerVisible, visSnapshotRequest, visValidateAsset, visValidateScene } from '../render/scene.js';



function setSun(elev,azi){const phi=THREE.MathUtils.degToRad(90-elev),th=THREE.MathUtils.degToRad(azi);
  const v=new THREE.Vector3().setFromSphericalCoords(1,phi,th); su.sunPosition.value.copy(v);
  sun.position.copy(v).multiplyScalar(120);}
setSun(52,135);

const camera=new THREE.PerspectiveCamera(52,innerWidth/innerHeight,0.05,6000);
/* حامل اللاعب (dolly): في VR تتحكّم النظارة بالكاميرا، ونحن نحرّك الحامل */
const player=new THREE.Group(); player.name='PLAYER'; scene.add(player); player.add(camera);
const orbit=new OrbitControls(camera,renderer.domElement); orbit.enableDamping=true;
/* ---- متحكّم مشي يعمل على الحاسب والجوال (بلا Pointer Lock) ---- */
const walkState={active:false, yaw:0, pitch:0, eye:1.6, speed:4, run:1, vx:0, vz:0, vy:0};
function walkLook(dx,dy){
  walkState.yaw   -= dx*0.0032;
  walkState.pitch  = Math.max(-1.3, Math.min(1.3, walkState.pitch - dy*0.0032));
}
function applyWalkCamera(){
  const e=new THREE.Euler(walkState.pitch, walkState.yaw, 0, 'YXZ');
  camera.quaternion.setFromEuler(e);
}
function walkMove(dt){
  const sp=walkState.speed*walkState.run*dt;
  const fwd=new THREE.Vector3(-Math.sin(walkState.yaw),0,-Math.cos(walkState.yaw));
  const rgt=new THREE.Vector3(Math.cos(walkState.yaw),0,-Math.sin(walkState.yaw));
  camera.position.addScaledVector(fwd, walkState.vz*sp);
  camera.position.addScaledVector(rgt, walkState.vx*sp);
  if(walkState.vy) camera.position.y += walkState.vy*sp;
}

let ground=null;
/* مستوى الموقع/الأرض العرضي — PHASE10_FOOTPRINT_PLATE §site_plane.
   هذا المستوى وحده هو ما يمثّل قطعة الأرض: يغطّي مستطيل الموقع كاملاً ويتمركز
   عليه، ويعيش في المشهد لا في مجموعة BUILDING، فهو مستثنى بنيوياً من الحدود
   القانونية ومن التصدير ومن الكميات. ألواح أدوار المبنى فوقه لم تعد تمتدّ على
   الموقع بل على بصمة غرف كل دور. */
function ensureGround(cx,cz,size,siteRect){ if(ground)scene.remove(ground);
  const sr=(Array.isArray(siteRect)&&siteRect.length===4
    &&siteRect.every(v=>Number.isFinite(Number(v)))
    &&Number(siteRect[2])>0&&Number(siteRect[3])>0)
    ?siteRect.map(Number):null;
  const sz=sr?Math.max(Number(size)||0,sr[2],sr[3]):size;
  const gx=sr?(sr[0]+sr[2]/2):cx, gz=sr?(sr[1]+sr[3]/2):cz;
  const g=new THREE.Mesh(new THREE.PlaneGeometry(sz,sz),
    new THREE.MeshStandardMaterial({color:0x2b2f36,roughness:0.95,metalness:0}));
  g.rotation.x=-Math.PI/2; g.position.set(gx,-0.1,gz); g.receiveShadow=true;
  g.name='GROUND_PLANE'; g.userData.presentation_context=true;
  g.userData.acs_site_plane={site_rect:sr,covers_site:!!sr,size_m:sz,
    policy:'PHASE10_FOOTPRINT_PLATE',separate_from_level_slabs:true,
    in_building_group:false};
  ground=g; scene.add(g);}

let model=null,registry={},floorsFound=new Set(),floorSel='all',doorMeshes=[],doorTexture=null,bounds={c:new THREE.Vector3(),r:60};
function tagOf(o){let p=o;while(p){if(p.name&&p.name.indexOf('|')>=0)return p.name;p=p.parent;}return null;}

let lastBuilding=null;
function setModel(data){
  // المرحلة 2: يقبل مشروعاً أو مبنى — يعرض المبنى النشط بلا أي تغيير في العارض
  if(isProjectModel(data)){ const ab=activeBuilding(data); if(ab) data=ab; }
  const incoming = data || lastBuilding;
  if(!incoming) return;
  /* ═══ KI-25/F-43 · يُبنى الجديد قبل أن يُهدَم القديم ══════════════════════
     كان الترتيب معكوساً: يُحرَّر المشهد القديم وتُتلَف خاماته كلّها، **ثم**
     يُستدعى compile. فاستثناءٌ واحد فيه — غرفةٌ بلا rect مثلاً — يترك
     المستخدم أمام نافذة فارغة بلا نموذج قديم يعود إليه ولا رسالة، لأن
     `lastBuilding` كان قد صار النموذجَ المعطوب في السطر الذي سبق. حتى
     `setModel(null)` بعدها (تغيير مستوى التفصيل، إطفاء الخامات) يعيد رمي
     الاستثناء نفسه: الصفحة تبقى معطّلة حتى تُحدَّث.
     الآن: البناء أوّلاً على خاماتٍ جديدة، والتراجع معرَّف — إن رمى compile
     عادت الخامات القديمة كما كانت والمشهد لم يُمَسّ، ثم يصعد الاستثناء إلى
     حاجز التطبيق ليُصنَّف. ولا يصير النموذج الجديد هو `lastBuilding` إلّا
     بعد أن يُبنى فعلاً. */
  const _prevMats={};
  for(const k in matCache){ _prevMats[k]=matCache[k]; delete matCache[k]; }
  let _next;
  try{
    _next=compile(incoming);
  }catch(e){
    for(const k in matCache) delete matCache[k];
    for(const k in _prevMats) matCache[k]=_prevMats[k];
    throw e;
  }
  if(data) lastBuilding=data;
  for(const k in _prevMats){ const m=_prevMats[k];
    if(m&&m.dispose){ try{ m.dispose(); }catch(e){} } }
  if(model){                                        // حرّر ذاكرة الرسوميات بعد نجاح البناء
    model.traverse(o=>{ if(o.isMesh&&o.geometry) o.geometry.dispose(); });
    scene.remove(model);
  }
  data=incoming;
  model=_next; scene.add(model);
  registry={};floorsFound=new Set();doorMeshes=[];
  model.traverse(o=>{ if(!o.isMesh)return;
    const tag=o.name||'MISC|F0|?|0'; const parts=tag.split('|');
    const floor=parts[1];
    /* طبقة MEP تُفهرس بالتخصّص، وطبقة الحريق بفئتها، ليُظهَر كلٌّ وحده */
    const fl=o.userData&&o.userData.fls;
    const layer=(parts[0]==='MEP')?('MEP_'+parts[1])
               :((parts[0]==='FLS'&&fl)?fl.layer:parts[0]);
    const st=o.userData&&o.userData.struct, mp=o.userData&&o.userData.mep;
    o.userData={layer,floor,tag};
    if(st) o.userData.struct=st; if(mp) o.userData.mep=mp; if(fl) o.userData.fls=fl;
    const debugLayer=(layer==='STRUCT'||layer.indexOf('MEP_')===0||layer.indexOf('FLS_')===0);
    if(!debugLayer) floorsFound.add(floor);   // الطبقات الهندسية ليست أدواراً
    if(!registry[layer])registry[layer]={meshes:[],visible:!debugLayer,
      color:'#'+o.material.color.getHexString()};
    registry[layer].meshes.push(o); if(layer==='DOOR')doorMeshes.push(o);
  });
  /* ═══ مصالحة الكاميرا الوحيدة المخوَّلة بعد تحميل نموذج ═══════════════════
     كان هنا: Box3().setFromObject(model) على كل شبكة في مجموعة المبنى بلا فحص
     صلاحية، ثم موضع كاميرا مشتقّ من نصف القطر — و**بلا أي إعادة ضبط لـ
     camera.near/far**، فيبقيان على قيمتَي الإنشاء 0.05 / 6000 مهما تغيّر
     النموذج. فإحداثيّة واحدة تالفة بين مئات العناصر المولَّدة (نقطة عند
     x=99999) ترفع نصف القطر من ٨٤ م إلى ٥٠ كم وتضع الكاميرا على بُعد ١٠٧ كم
     خلف مستوى قصّ ثابت عند ٦ كم: لا يتقاطع شيء، فيُمسح الإطار أسود بينما
     الواجهة حيّة وعدّادات الطبقات ممتلئة. هذا هو البلاغ الإنتاجي بالحرف.
     الآن يمرّ التأطير كلّه بعقد أمان المشهد نفسه الذي تستعمله الإعدادات. */
  const _rr=(typeof acsReconcileCamera==='function')?acsReconcileCamera():null;
  if(_rr&&_rr.bounds&&_rr.applied){
    bounds.c.set(_rr.bounds.cx,_rr.bounds.cy,_rr.bounds.cz);
    bounds.r=_rr.bounds.radius||60;
  }else{
    /* احتياط: العقد غير متاح (شجرة جزئية) — السلوك السابق حرفياً، ومع ذلك
       تُضبط مستويات القصّ حتى لا يبقى الخلل الأصلي قائماً في المسار الاحتياطي. */
    const box=new THREE.Box3().setFromObject(model);
    const s=box.getBoundingSphere(new THREE.Sphere());
    if(isFinite(s.radius)&&isFinite(s.center.x)){
      bounds.c.copy(s.center); bounds.r=s.radius||60; }
    else { bounds.c.set(0,0,0); bounds.r=60; }
    orbit.target.copy(bounds.c);
    camera.position.set(bounds.c.x+bounds.r*1.4,bounds.c.y+bounds.r*0.85,
                        bounds.c.z+bounds.r*1.4);
    camera.near=Math.max(0.05,bounds.r*0.002);
    camera.far=Math.max(200,bounds.r*8);
    camera.updateProjectionMatrix();
    orbit.update();
  }
  // ظل الشمس يغطي المبنى
  const sc=sun.shadow.camera; const R=bounds.r*1.3;
  sc.left=-R;sc.right=R;sc.top=R;sc.bottom=-R;sc.near=1;sc.far=bounds.r*6; sc.updateProjectionMatrix();
  sun.target.position.copy(bounds.c); scene.add(sun.target);
  ensureGround(bounds.c.x,bounds.c.z,bounds.r*10,
    [0,0,Number((data.site||{}).w)||0,Number((data.site||{}).d)||0]);
  buildFloors(); buildLayers(); updateVis();
  let n=0; model.traverse(o=>{if(o.isMesh)n++});
  const nz=Object.values(data.floors||{}).reduce((a,f)=>a+((f.rooms||[]).length),0);
  /* KI-26/F-46 · «تم التوليد ✓» كانت تُكتب مهما سقط من النموذج. setModel هو
     المسار المشترك (خادم · مثال · مستودع محلي · استيراد)، فالصدق يبدأ هنا. */
  let _sum=null; try{ _sum=acsCompileSummary(); }catch(e){ _sum=null; }
  const _deg=!!(_sum&&_sum.degraded);
  statusEl.textContent=(_deg?'⚠ بُني ناقصاً  ':'تم التوليد ✓  ')
    +`${n} عنصر · ${nz} منطقة/غرفة · ${Object.keys(registry).length} طبقة · ${floorsFound.size} دور`
    +(_deg?(' — سقط: '+(_sum.degradation_reasons||[]).join(' · ')):'');
  const statEl=document.getElementById('statCount');
  if(statEl) statEl.innerHTML=`<b>${n}</b> عنصر ثلاثي الأبعاد مبنيّ من <b>${nz}</b> منطقة في الوصف.`
    +(n>6000?' <span class="acs-warn">— خفّض «مستوى التفصيل» إن تباطأت الحركة.</span>':'');
  if(window.ACS&&window.ACS.closePanel) window.ACS.closePanel();
  showTab('model'); document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.tab==='model'));
  /* §14: بعد إطارين من الاستقرار، إن بقي المشهد أسود مع وجود هندسة ونداءات
     رسم، تُجرّب دورة استرداد واحدة (لا حلقة) وتُسمّى الطبقة المسؤولة. */
  if(typeof acsRecoverBlackViewport==='function'){
    if(window.__ACS_RR__) window.__ACS_RR__.cycles=0;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      try{
        const rec=acsRecoverBlackViewport();
        if(rec&&rec.plan&&rec.plan.needed){
          acsFail(rec.recovered?ACS_FAIL.RENDER_POSTPROCESS_ERROR
                                :ACS_FAIL.RENDER_BLACK_VIEWPORT,
                  'attempted: '+rec.attempted.join(' > '));
          console.warn('[ACS-RENDER] black viewport with geometry — recovery:',
            rec.attempted.join(' > '), rec.recovered?('recovered at '+rec.applied_step)
              :'NOT RECOVERED');
          if(!rec.recovered&&statusEl) statusEl.textContent=
            '⚠ المشهد لا يعرض النموذج رغم بنائه — افتح الكونسول وشغّل '
            +'ACS.renderRecoveryReport() لمعرفة الطبقة المسؤولة.';
        }
      }catch(e){ console.error('[ACS-RENDER] recovery failed', e); }
    }));
  }
}

/* الأدوار */
function buildFloors(){const wrap=document.getElementById('floors');wrap.innerHTML='';
  const mk=(k,l)=>{const b=document.createElement('button');b.className='ghost';b.textContent=l;
    if(k==='all')b.classList.add('active');
    b.onclick=()=>{floorSel=k;[...wrap.children].forEach(c=>c.classList.remove('active'));b.classList.add('active');updateVis();};
    wrap.appendChild(b);};
  mk('all','الكل');
  /* ═══ KI-26/F-46 · ترتيب الأدوار طبيعيّ لا معجميّ ═══════════════════════
     كان: ‎[...floorsFound].sort()‎ — مقارنةٌ نصّية على مفاتيح مثل 'F10'، فينتج
     F0,F1,F10,F11,F2,…,F9 في كل مبنى فيه عشرة أدوار فأكثر. المستخدم يرى
     شريطاً لا يطابق مبناه، ويضغط «الدور ٢» فيقفز إلى العاشر بصرياً.
     والاسم كان ‎FLOOR_NAMES[f]||f‎ — جدولٌ يقف عند F6 (وF6 نفسه مسمّى
     «السطح» كذباً)، فما فوقه يُعرَض مفتاحاً خاماً «F7».
     الآن: ترتيبٌ عدديّ من ‎acsFloorOrder‎، واسمٌ من ‎acsFloorName‎ يعرف عدد
     الأدوار الكلّي فيسمّي السطحَ سطحاً حين يكون الأعلى فعلاً لا حين يكون ٦. */
  acsFloorOrder(floorsFound).forEach(f=>mk(f,floorLabel(f)));}
/* اسم الدور المعروض في كل موضع بالواجهة — مصدرٌ واحد لا خمسة.
   ‎acsFloorName‎ يحتاج عدد الأدوار الكلّي ليقرّر أيّها السطح؛ يُشتقّ هنا من
   أكبر رقم دورٍ موجود فعلاً في المشهد (لا من عدد المفاتيح: مبنًى مفاتيحه
   F0 وF5 وحدهما ليس مبنى دورين). لا يعيد قيمةً فارغة أبداً. */
function floorLabel(fkey){
  let top=-1;
  floorsFound.forEach(k=>{ const i=acsFloorIndex(k); if(i!==null&&i>top) top=i; });
  return acsFloorName(fkey, top+1);
}
/* الطبقات */
function buildLayers(){const wrap=document.getElementById('layers');wrap.innerHTML='';
  LAYER_ORDER.filter(l=>registry[l]).forEach(l=>{const r=registry[l];
    const row=document.createElement('div');row.className='lay';
    const cb=document.createElement('input');cb.type='checkbox';cb.checked=r.visible;
    cb.onchange=()=>{r.visible=cb.checked;updateVis();};
    const col=document.createElement('input');col.type='color';col.value=r.color;
    col.oninput=()=>{r.color=col.value;r.meshes.forEach(m=>{m.material.color.set(col.value);if(l==='DOOR')m.material.map=null;m.material.needsUpdate=true;});};
    const nm=document.createElement('span');nm.className='nm';nm.textContent=LAYER_NAMES[l]||l;
    const ct=document.createElement('span');ct.className='ct';ct.textContent=r.meshes.length;
    row.append(cb,col,nm,ct);wrap.appendChild(row);});}
function updateVis(){for(const l in registry){const r=registry[l];
  r.meshes.forEach(m=>{m.visible=r.visible&&(floorSel==='all'||m.userData.floor===floorSel);});}}

/* صورة الباب */
const applyAllBtn=document.getElementById('applyAll');
const texTargetEl=document.getElementById('texTarget');
const texRepeatEl=document.getElementById('texRepeat');
const photoApplied=[];                       // لتراجع التطبيق
function useDoorImage(file){const url=URL.createObjectURL(file);
  new THREE.TextureLoader().load(url,tex=>{
    tex.colorSpace=THREE.SRGBColorSpace; tex.wrapS=tex.wrapT=THREE.RepeatWrapping; tex.anisotropy=8;
    doorTexture=tex; applyAllBtn.disabled=false;
    document.getElementById('doorbox').classList.add('hot');
    statusEl.textContent='الصورة جاهزة — اختر الطبقة واضغط «تطبيق»، أو انقر عنصراً بعينه.';});}
function applyDoorTex(m){
  if(!doorTexture)return;
  const t=doorTexture.clone(); t.needsUpdate=true;
  const rep=Math.max(0.1,+texRepeatEl.value||1); t.repeat.set(rep,rep);
  if(!m.userData._origMat) m.userData._origMat=m.material;
  m.material=m.material.clone(); m.material.map=t; m.material.bumpMap=null;
  m.material.color.set(0xffffff); m.material.needsUpdate=true;
  if(photoApplied.indexOf(m)<0) photoApplied.push(m);
}
applyAllBtn.onclick=()=>{
  const layer=texTargetEl.value;
  const list=(registry[layer]&&registry[layer].meshes)||[];
  list.forEach(applyDoorTex);
  statusEl.textContent='طُبّقت الصورة على '+list.length+' عنصراً في طبقة «'+(LAYER_NAMES[layer]||layer)+'».';
};
document.getElementById('clearDoor').onclick=()=>{
  doorTexture=null; applyAllBtn.disabled=true;
  document.getElementById('doorbox').classList.remove('hot');
  photoApplied.forEach(m=>{ if(m.userData._origMat){m.material=m.userData._origMat; delete m.userData._origMat;} });
  photoApplied.length=0; statusEl.textContent='أُلغيت الصور المطبّقة.';
};
document.getElementById('doorfile').onchange=e=>{if(e.target.files[0])useDoorImage(e.target.files[0]);};
document.getElementById('texOn').onchange=e=>{
  __ACS_SHARED.USE_TEX=e.target.checked;
  statusEl.textContent=__ACS_SHARED.USE_TEX?'إعادة البناء بالخامات الواقعية…':'إعادة البناء بألوان مسطّحة…';
  setTimeout(()=>setModel(null),20);
};
document.getElementById('detailSel').onchange=e=>{
  __ACS_SHARED.DETAIL=parseFloat(e.target.value)||1;
  statusEl.textContent='إعادة البناء بمستوى تفصيل جديد…';
  setTimeout(()=>setModel(null),20);
};
/* على الأجهزة الضعيفة (جوال) نبدأ بتفصيل خفيف تلقائياً */
if(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<=4||innerWidth<720){
  __ACS_SHARED.DETAIL=0.5; const ds=document.getElementById('detailSel'); if(ds) ds.value='0.5';
}

/* نقر عنصر */
const ray=new THREE.Raycaster(),mouse=new THREE.Vector2(),infoEl=document.getElementById('info');
renderer.domElement.addEventListener('click',ev=>{ if(walkState.active||!model)return;
  mouse.x=(ev.clientX/innerWidth)*2-1;mouse.y=-(ev.clientY/innerHeight)*2+1;
  ray.setFromCamera(mouse,camera);
  const hits=ray.intersectObjects([model],true).filter(h=>h.object.visible);
  if(!hits.length){infoEl.style.display='none';return;}
  const hit=hits[0], o=hit.object, t=(o.userData.tag||'').split('|');
  if(TOOL!=='none'){ addMeasurePoint(hit.point); return; }
  if(noteMode){ openNote(o, hit.point); return; }
  infoEl.style.display='block';
  if(t[0]==='STRUCT'){ infoEl.innerHTML=structInfoCard(o); return; }
  if(t[0]==='MEP'){ infoEl.innerHTML=mepInfoCard(o); return; }
  if(t[0]==='FLS'){ infoEl.innerHTML=flsInfoCard(o); return; }
  infoEl.innerHTML=`<b>${esc(LAYER_NAMES[t[0]]||t[0])}</b><br>الدور: ${esc(floorLabel(t[1]))} · الغرفة: ${esc(t[2]||'-')}<br><span class="acs-dim-60">${esc(t[3]||'')}</span>`;
  if(doorTexture){applyDoorTex(o);infoEl.innerHTML+='<br><span class="acs-ok">✓ طُبّقت الصورة على هذا العنصر</span>';}
  else infoQuickColors(o);});

/* بطاقة عنصر إنشائي: حقائق النموذج فقط — لا حكم سلامة ولا كفاية ولا مطابقة.
   وإن كانت الأبعاد المرسومة احتياط عرض قيل ذلك صراحةً بدل تمريرها كقياس. */
function structInfoCard(o){
  const u=(o.userData&&o.userData.struct)||{};
  let el=null, mat=null;
  try{ const ST=compileStructure(lastBuilding,'bld_0');
       el=structElementById(ST,u.id);
       mat=el?_sMaterialName(ST,el.material_ref):null; }
  catch(e){ /* KI-26/F-46: كان ‎catch(e){}‎ فارغاً — بطاقةٌ تُعرض بلا حقائق
     النموذج تبدو «عنصراً بلا بيانات» وهي في الحقيقة «مصرِّفٌ سقط». */
    acsBuildDefect('specialization_failed','INFOCARD_STRUCT_COMPILE_FAILED','STRUCT'); }
  const L=[];
  L.push('<b>'+esc(LAYER_NAMES.STRUCT)+'</b>');
  L.push('المعرّف: '+esc(u.id||'-'));
  L.push('النوع: '+esc(u.kind||'-'));
  L.push('المصدر: '+esc((el&&el.source)||u.element_source||'unknown'));
  if(el&&el.level_id) L.push('المستوى: '+esc(el.level_id));
  if(el&&el.base_level_id) L.push('من '+esc(el.base_level_id)+' إلى '+esc(el.top_level_id||'-'));
  if(el&&el.level_ids&&el.level_ids.length) L.push('المستويات: '+esc(el.level_ids.join(' · ')));
  L.push('المادة: '+esc(mat||'غير مذكورة'));
  if(el&&el.section) L.push('المقطع: '+esc(el.section.shape)+' '+
      esc([el.section.width_m,el.section.depth_m,el.section.diameter_m]
          .filter(v=>v!==null&&v!==undefined).join('×')||'-'));
  else if(u.kind==='COLUMN'||u.kind==='BEAM') L.push('المقطع: غير مذكور');
  if(el&&el.stack) L.push('التكديس: '+esc(el.stack.state));
  L.push('<span class="acs-dim-65">هندسة العرض: '+
    (u.geometry_source==='display_fallback'
      ?'احتياط عرض — ليست قياساً إنشائياً'
      :'من النموذج')+'</span>');
  L.push('<span class="acs-dim-65">تمثيل إنشائي فقط — لا تصميم ولا أحمال ولا مطابقة كود'+
         '</span>');
  return L.join('<br>'); }
/* بطاقة عنصر MEP: حقائق النموذج فقط — لا كفاية خدمة ولا مطابقة ولا حالة سلامة.
   وإن كانت الأبعاد المرسومة احتياط عرض قيل ذلك صراحةً بدل تمريرها كمقاس. */
function mepInfoCard(o){
  const u=(o.userData&&o.userData.mep)||{};
  let el=null, sys=null;
  try{ const MP=compileMep(lastBuilding,'bld_0');
       el=mepElementById(MP,u.id);
       sys=el?mepSystemById(MP,el.system_id):null; }
  catch(e){ /* KI-26/F-46: كان ‎catch(e){}‎ فارغاً */
    acsBuildDefect('specialization_failed','INFOCARD_MEP_COMPILE_FAILED','MEP'); }
  const L=[];
  L.push('<b>'+esc(LAYER_NAMES['MEP_'+(u.discipline||'OTHER')]||'MEP')+'</b>');
  L.push('المعرّف: '+esc(u.id||'-'));
  L.push('النوع: '+esc(u.kind||'-')+(u.terminal_type?(' · '+esc(u.terminal_type)):''));
  L.push('النظام: '+esc(sys?((sys.name||sys.system_type)+' ['+sys.system_type+']'):'غير مذكور'));
  L.push('الوسيط: '+esc(sys?sys.medium:'-'));
  L.push('المصدر: '+esc((el&&el.source)||u.element_source||'unknown'));
  if(u.adapted) L.push('محوَّل من نقطة المرحلة 1 — الإسناد الأصلي: '+
    esc((el&&el.original_source)||'system_default'));
  if(el&&el.level_id) L.push('المستوى: '+esc(el.level_id));
  if(el&&el.space_id) L.push('الفراغ: '+esc(el.space_id));
  if(el&&el.routing_status) L.push('حالة التوجيه: '+esc(el.routing_status));
  if(el&&el.size) L.push('المقاس: '+esc([el.size.diameter_m,el.size.width_m,el.size.height_m]
      .filter(v=>v!==null&&v!==undefined).join('×')||'-'));
  else if(u.kind==='SEGMENT') L.push('المقاس: غير مذكور');
  L.push('<span class="acs-dim-65">هندسة العرض: '+
    (u.geometry_source==='display_fallback'
      ?'احتياط عرض — ليست مقاساً هندسياً'
      :'من النموذج')+'</span>');
  L.push('<span class="acs-dim-65">تمثيل MEP فقط — لا تصميم ولا حساب أحمال ولا كفاية '+
         'خدمة ولا مطابقة كود</span>');
  return L.join('<br>'); }
/* بطاقة عنصر حريق/سلامة: حقائق النموذج فقط — لا تغطية ولا كفاية ولا مطابقة.
   ولا يُعرض أي لون كحكم: اللون يميّز نوع العنصر لا حالته. */
function flsInfoCard(o){
  const u=(o.userData&&o.userData.fls)||{};
  let el=null;
  try{ const FL=compileFls(lastBuilding,'bld_0'); el=flsElementById(FL,u.id); }
  catch(e){ /* KI-26/F-46: كان ‎catch(e){}‎ فارغاً */
    acsBuildDefect('specialization_failed','INFOCARD_FLS_COMPILE_FAILED','FLS'); }
  const L=[];
  L.push('<b>'+esc(LAYER_NAMES[u.layer]||'حريق/سلامة')+'</b>');
  L.push('المعرّف: '+esc(u.id||'-'));
  L.push('النوع: '+esc(u.device_type||u.kind||'-'));
  L.push('المصدر: '+esc((el&&el.source)||u.element_source||'unknown'));
  if(el&&el.origin&&el.origin!=='model')
    L.push('مُشار إليه عبر: '+esc(el.origin)+' — الإسناد الأصلي: '+
      esc(el.original_source||'unknown'));
  if(el&&el.level_id) L.push('المستوى: '+esc(el.level_id));
  if(el&&el.space_id) L.push('الفراغ: '+esc(el.space_id));
  if(el&&el.indicates_exit) L.push('يشير إلى المخرج: '+esc(el.indicates_exit)+
    (el.target_resolved?'':' — الهدف غير موجود'));
  if(el&&el.rating_minutes) L.push('المقاومة: '+
    (el.rating_minutes.value===null?'غير مذكورة (لا تُستنتج)':esc(el.rating_minutes.value)+' د'));
  L.push('<span class="acs-dim-65">هندسة العرض: احتياط عرض — ليست قياساً هندسياً</span>');
  L.push('<span class="acs-dim-65">تمثيل بيانات فقط — الجهاز موجود ≠ التغطية مؤكّدة؛ '+
         'لا تصميم حريق ولا محاكاة ولا مطابقة كود</span>');
  return L.join('<br>'); }
/* لوحة ألوان سريعة داخل بطاقة العنصر: نقرة واحدة تلوّن جدران هذه الغرفة فقط */
function infoQuickColors(o){
  const tag=o.userData.tag||'', t=tag.split('|');
  const surf = t[0]==='FLOOR' ? 'floor' : (t[0]==='WALL' ? 'wall' : 'self');
  const lbl = surf==='wall'?'لوّن جدران هذه الغرفة':(surf==='floor'?'لوّن الأرضية':'لوّن هذا العنصر');
  const wrap=document.createElement('div'); wrap.className='qcl'; wrap.textContent='🎨 '+lbl+':';
  const bar=document.createElement('div'); bar.className='qc';
  COLOR_SWATCH.forEach(([nm,hx])=>{
    const i=document.createElement('i'); i.style.background=hx; i.title=nm;
    i.onclick=ev=>{ ev.stopPropagation();
      const msg=applyFinish(tag,surf,hx,o); statusEl.textContent=msg; };
    bar.appendChild(i);
  });
  const cst=document.createElement('input'); cst.type='color'; cst.value='#22c55e';
  cst.className='acs-swatch-btn';
  cst.oninput=()=>{ statusEl.textContent=applyFinish(tag,surf,cst.value,o); };
  bar.appendChild(cst);
  infoEl.appendChild(wrap); infoEl.appendChild(bar);
}

/* ========================= محرّك الألوان والتشطيبات (فوري · بلا خادم) ========================= */
const AR_COLORS={
  'اخضر':'#22c55e','أخضر':'#22c55e','خضراء':'#22c55e','خضر':'#22c55e','green':'#22c55e',
  'زيتوني':'#6b8e23','زيتي':'#6b8e23','فستقي':'#a7d129','نعناعي':'#7fd1ae','زمردي':'#0f9d58',
  'احمر':'#e11d48','أحمر':'#e11d48','حمراء':'#e11d48','red':'#e11d48','عنابي':'#7b1f2b','خمري':'#7b1f2b',
  'وردي':'#f472b6','زهري':'#f472b6','pink':'#f472b6','برتقالي':'#f97316','orange':'#f97316',
  'ازرق':'#2563eb','أزرق':'#2563eb','زرقاء':'#2563eb','blue':'#2563eb','سماوي':'#38bdf8','لبني':'#8ecae6',
  'كحلي':'#1e293b','نيلي':'#3730a3','تركوازي':'#14b8a6','فيروزي':'#14b8a6',
  'اصفر':'#facc15','أصفر':'#facc15','صفراء':'#facc15','yellow':'#facc15','ذهبي':'#d4af37','gold':'#d4af37',
  'بني':'#6b4423','brown':'#6b4423','خشبي':'#7a4a22','بيج':'#e3d5b8','beige':'#e3d5b8','كريمي':'#f2e8d5',
  'رمادي':'#8b8f96','رصاصي':'#6b7280','gray':'#8b8f96','grey':'#8b8f96','فضي':'#c0c4cc',
  'ابيض':'#f5f5f2','أبيض':'#f5f5f2','بيضاء':'#f5f5f2','white':'#f5f5f2',
  'اسود':'#17181b','أسود':'#17181b','سوداء':'#17181b','black':'#17181b',
  'بنفسجي':'#8b5cf6','موف':'#a78bfa','purple':'#8b5cf6','ليلكي':'#c4b5fd',
  'ترابي':'#a89078','رملي':'#dcc9a6','شمبانيا':'#e8d9bd'
};
const COLOR_SWATCH=[['أخضر','#22c55e'],['أزرق','#2563eb'],['رمادي','#8b8f96'],['بيج','#e3d5b8'],
  ['أبيض','#f5f5f2'],['أصفر','#facc15'],['أحمر','#e11d48'],['بني','#6b4423'],['بنفسجي','#8b5cf6'],['كحلي','#1e293b']];

function detectColor(txt){
  const s=stripBidi(String(txt||''));
  const hx=s.match(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/);
  if(hx) return normHex(hx[0]);
  // أطول اسم لون مطابق أولاً، مع احترام حدود الكلمة والسوابق العربية (ال/بال/و…)
  const keys=Object.keys(AR_COLORS).sort((a,b)=>b.length-a.length);
  const AL='\\u0621-\\u064a';
  for(const k of keys){
    const esc=k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const re=new RegExp('(^|[^'+AL+'\\w])(?:ال|بال|لل|كال|وال|و|ب|ل)?'+esc+'(?:ة|ه|ا|ين|ات)?([^'+AL+'\\w]|$)');
    if(re.test(' '+s+' ')) return shadeBy(AR_COLORS[k], s);
  }
  return null;
}
function shadeBy(hex,s){
  let f=0;
  if(/فاتح|لايت|light/.test(s)) f=0.35;
  if(/غامق|داكن|غامقة|dark/.test(s)) f=-0.3;
  if(!f) return hex;
  const n=parseInt(hex.slice(1),16); let r=(n>>16)&255,g=(n>>8)&255,b=n&255;
  const mix=v=>Math.round(f>0? v+(255-v)*f : v*(1+f));
  r=mix(r);g=mix(g);b=mix(b);
  return '#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
}
function detectSurface(txt){
  const s=stripBidi(String(txt||''));
  if(/سقف|السقف|ceiling/.test(s)) return 'ceiling';
  if(/ارضي|أرضي|الارض|الأرض|بلاط|سيراميك|باركيه|floor/.test(s)) return 'floor';
  if(/جدار|الجدار|جدران|حائط|حيطان|الحيطان|wall/.test(s)) return 'wall';
  if(/باب|الباب|door/.test(s)) return 'self';
  return null;
}

/* يفصل قالب الدور إذا كان مشتركاً بين عدّة أدوار، حتى لا يتلوّن باقي الأدوار */
function isolateTemplate(fkey){
  if(!lastBuilding) return null;
  const idx=parseInt(String(fkey).replace(/[^0-9]/g,''),10);
  const lvl=(lastBuilding.levels||[]).find(l=>+l.index===idx);
  if(!lvl) return null;
  const shared=(lastBuilding.levels||[]).filter(l=>l.template===lvl.template).length>1;
  if(shared){
    const nt=lvl.template+'__'+fkey;
    if(!lastBuilding.floors[nt])
      lastBuilding.floors[nt]=JSON.parse(JSON.stringify(lastBuilding.floors[lvl.template]||{rooms:[]}));
    lvl.template=nt;
  }
  return lastBuilding.floors[lvl.template]||null;
}
function roomOfTag(tag){
  const t=String(tag||'').split('|'); if(t.length<3) return null;
  const fdef=isolateTemplate(t[1]); if(!fdef) return null;
  const room=(fdef.rooms||[]).find(r=>String(r.id)===t[2]);
  return room? {room:room, fkey:t[1], rid:t[2]} : null;
}
function meshesOfRoom(fkey,rid,layers){
  const out=[]; if(!model) return out;
  model.traverse(o=>{ if(!o.isMesh) return;
    const t=(o.userData.tag||'').split('|');
    if(t[1]===fkey && t[2]===rid && layers.indexOf(t[0])>=0) out.push(o);
  });
  return out;
}
/* التطبيق الفوري: يغيّر المشهد الآن ويحفظ اللون في النموذج ليبقى بعد إعادة البناء */
function applyFinish(tag, surface, hex, mesh){
  hex=normHex(hex); if(!hex) return 'لون غير صالح.';
  if(surface==='self'){
    if(!mesh) return 'لم يُحدَّد عنصر.';
    const base=(mesh.material&&mesh.material.userData&&mesh.material.userData.matName)||'wall';
    mesh.material=getMat(base,hex); mesh.material.needsUpdate=true;
    const rr=roomOfTag(tag), t=String(tag||'').split('|');
    if(rr && t[0]==='DOOR'){ const i=parseInt(t[3],10);
      if(rr.room.doors&&rr.room.doors[i]) rr.room.doors[i].color=hex; }
    return 'طُبّق اللون على العنصر المحدّد ✓';
  }
  const rr=roomOfTag(tag);
  if(!rr) return 'هذا العنصر ليس ضمن غرفة معرّفة — استخدم «هذا العنصر».';
  const KEY={wall:'wall_color',floor:'floor_color',ceiling:'ceiling_color'}[surface];
  rr.room[KEY]=hex;
  if(surface==='wall'){
    const ms=meshesOfRoom(rr.fkey,rr.rid,['WALL']);
    const m=getMat('wall',hex);
    ms.forEach(o=>{o.material=m;});
    return 'طُبّق اللون على '+ms.length+' جزء جدار في غرفة «'+rr.rid+'» (الدور '+floorLabel(rr.fkey)+') ✓';
  }
  // أرضية/سقف: قد لا يكون اللوح موجوداً بعد → أنشئه في مكانه
  const det=surface==='floor'?'plate':'ceil';
  let found=meshesOfRoom(rr.fkey,rr.rid,['FLOOR']).filter(o=>(o.userData.tag||'').endsWith('|'+det));
  if(found.length){ const m=getMat(surface==='floor'?'floor':'ceiling',hex); found.forEach(o=>{o.material=m;}); }
  else {
    const def={wall_h:lastBuilding.wall_h||3.0, wall_t:lastBuilding.wall_t||0.15};
    const fh=lastBuilding.floor_height||(def.wall_h+0.2);
    const idx=parseInt(rr.fkey.replace(/[^0-9]/g,''),10);
    const [x,z,w,d]=rr.room.rect; const H=rr.room.wall_h||def.wall_h, baseY=idx*fh, t=def.wall_t;
    const g=new THREE.Group();
    if(surface==='floor') addBox(g,x+w/2,baseY+0.012,z+d/2,Math.max(w-t,0.1),0.024,Math.max(d-t,0.1),
        'floor',`FLOOR|${rr.fkey}|${rr.rid}|plate`,false,hex);
    else addBox(g,x+w/2,baseY+H-0.03,z+d/2,Math.max(w-t,0.1),0.05,Math.max(d-t,0.1),
        'ceiling',`FLOOR|${rr.fkey}|${rr.rid}|ceil`,false,hex);
    while(g.children.length){ const o=g.children[0]; g.remove(o);
      o.userData={layer:'FLOOR',floor:rr.fkey,tag:o.name}; model.add(o);
      if(!registry.FLOOR) registry.FLOOR={meshes:[],visible:true,color:'#ffffff'};
      registry.FLOOR.meshes.push(o); }
    updateVis();
  }
  return 'طُبّق لون ال'+(surface==='floor'?'أرضية':'سقف')+' في غرفة «'+rr.rid+'» ✓';
}


/* ==================================================================
   أدوات المهندس: قياس · مقاطع · دراسة الشمس والظل
   ================================================================== */
let TOOL='none';                    // none | measure | area
const measure={pts:[], marks:new THREE.Group(), line:null};
scene.add(measure.marks);
const MEAS_MAT=new THREE.LineBasicMaterial({color:0x38bdf8});

function fmt(m){ return m>=1 ? m.toFixed(2)+' م' : Math.round(m*100)+' سم'; }
function clearMeasure(){
  while(measure.marks.children.length){ const o=measure.marks.children[0];
    measure.marks.remove(o); if(o.geometry)o.geometry.dispose(); }
  measure.pts=[]; setMeasureHUD('');
}
function setMeasureHUD(html){
  const el=document.getElementById('measHUD'); if(!el) return;
  el.innerHTML=html; el.style.display=html?'block':'none';
}
function addMeasurePoint(p){
  measure.pts.push(p.clone());
  const s=new THREE.Mesh(new THREE.SphereGeometry(0.09,12,10),
    new THREE.MeshBasicMaterial({color:0x38bdf8}));
  s.position.copy(p); measure.marks.add(s);

  if(TOOL==='measure'){
    if(measure.pts.length===2){
      const [a,b]=measure.pts;
      const g=new THREE.BufferGeometry().setFromPoints([a,b]);
      measure.marks.add(new THREE.Line(g,MEAS_MAT));
      const d=a.distanceTo(b);
      const dx=Math.abs(a.x-b.x), dy=Math.abs(a.y-b.y), dz=Math.abs(a.z-b.z);
      setMeasureHUD('<b>'+fmt(d)+'</b><span>أفقي '+fmt(Math.hypot(dx,dz))+
                    ' · رأسي '+fmt(dy)+'</span>');
      measure.pts=[];      // ابدأ قياساً جديداً بالنقرة التالية
      setTimeout(()=>{ if(TOOL==='measure'&&measure.marks.children.length>60) clearMeasure(); },50);
    }
  }else if(TOOL==='area'){
    const n=measure.pts.length;
    if(n>=2){
      const g=new THREE.BufferGeometry().setFromPoints(measure.pts.slice(-2));
      measure.marks.add(new THREE.Line(g,MEAS_MAT));
    }
    if(n>=3){
      let A=0; const P=measure.pts;                    // مساحة المضلّع في المستوي الأفقي
      for(let i=0;i<P.length;i++){ const q=P[(i+1)%P.length];
        A += P[i].x*q.z - q.x*P[i].z; }
      A=Math.abs(A)/2;
      let per=0; for(let i=0;i<P.length;i++){ const q=P[(i+1)%P.length];
        per+=Math.hypot(P[i].x-q.x, P[i].z-q.z); }
      setMeasureHUD('<b>'+A.toFixed(2)+' م²</b><span>'+n+' نقاط · محيط '+fmt(per)+
                    ' — انقر «مسح» للبدء من جديد</span>');
    }else setMeasureHUD('<b>—</b><span>انقر ٣ نقاط على الأقل لحساب المساحة</span>');
  }
}
function setTool(t){
  TOOL=(TOOL===t)?'none':t;
  clearMeasure();
  document.querySelectorAll('#camBar button[data-tool]').forEach(b=>
    b.classList.toggle('on', b.dataset.tool===TOOL));
  if(TOOL==='measure') setMeasureHUD('<b>القياس</b><span>انقر نقطتين لقياس المسافة بينهما</span>');
  if(TOOL==='area')    setMeasureHUD('<b>المساحة</b><span>انقر أركان المساحة ثم اقرأ الناتج</span>');
  statusEl.textContent = TOOL==='none' ? 'أُوقفت أداة القياس.' :
    (TOOL==='measure' ? 'أداة القياس: انقر نقطتين.' : 'أداة المساحة: انقر الأركان.');
}

/* ── المقاطع: قصّ المبنى بمستويات لرؤية الداخل بلا دخول وضع المشي ── */
renderer.localClippingEnabled=true;
const clip={x:new THREE.Plane(new THREE.Vector3(-1,0,0),1e6),
            y:new THREE.Plane(new THREE.Vector3(0,-1,0),1e6),
            z:new THREE.Plane(new THREE.Vector3(0,0,-1),1e6), on:false};
function applyClip(){
  const planes = clip.on ? [clip.x,clip.y,clip.z] : [];
  for(const k in matCache){ const m=matCache[k];
    if(m){ m.clippingPlanes=planes; m.clipShadows=true; m.needsUpdate=true; } }
  if(model) model.traverse(o=>{ if(o.isMesh&&o.material&&!o.material.clippingPlanes)
    { o.material.clippingPlanes=planes; o.material.needsUpdate=true; } });
}
function setClip(axis,pct){
  const b=bounds, r=b.r;
  const lo={x:b.c.x-r, y:b.c.y-r, z:b.c.z-r}[axis];
  const v=lo + 2*r*(pct/100);
  clip[axis].constant = v;                       // normal سالب ⇒ يبقى ما قبل المستوي
  clip.on=true; applyClip();
  const lbl=document.getElementById('clipVal_'+axis);
  if(lbl) lbl.textContent=v.toFixed(1)+' م';
}
function resetClip(){
  clip.on=false; clip.x.constant=clip.y.constant=clip.z.constant=1e6; applyClip();
  ['x','y','z'].forEach(a=>{ const s=document.getElementById('clip_'+a); if(s)s.value=100;
    const l=document.getElementById('clipVal_'+a); if(l)l.textContent='—'; });
  statusEl.textContent='أُلغي المقطع.';
}

/* ── دراسة الشمس والظل: موضع الشمس الحقيقي بالتاريخ والوقت وخط العرض ── */
const sunStudy={lat:24.71, lon:46.68, day:172, hour:12};   // الرياض
function sunAngles(lat, dayOfYear, hour){
  const rad=Math.PI/180;
  const dec = 23.45*Math.sin(2*Math.PI*(284+dayOfYear)/365)*rad;   // الميل
  const H   = (hour-12)*15*rad;                                    // الزاوية الساعية
  const la  = lat*rad;
  const alt = Math.asin(Math.sin(la)*Math.sin(dec)+Math.cos(la)*Math.cos(dec)*Math.cos(H));
  let az = Math.atan2(-Math.sin(H)*Math.cos(dec),
                      Math.cos(la)*Math.sin(dec)-Math.sin(la)*Math.cos(dec)*Math.cos(H));
  az = (az/rad+360)%360;
  return {elev: alt/rad, azim: az};
}
function applySunStudy(){
  const a=sunAngles(sunStudy.lat, sunStudy.day, sunStudy.hour);
  const el=Math.max(a.elev, -3);
  setSun(el, a.azim);
  sun.intensity = el<=0 ? 0.05 : 1.4+2.0*Math.min(el/60,1);
  su.turbidity.value = el<12 ? 9 : 6;
  su.rayleigh.value  = el<12 ? 3.2 : 2.2;
  const d=new Date(2026,0,1); d.setDate(sunStudy.day);
  const hh=Math.floor(sunStudy.hour), mm=Math.round((sunStudy.hour-hh)*60);
  const out=document.getElementById('sunOut');
  if(out) out.innerHTML='<b>'+String(hh).padStart(2,'0')+':'+String(mm).padStart(2,'0')+'</b> · '
    + d.toLocaleDateString('ar-SA',{month:'long',day:'numeric'})
    + ' · ارتفاع الشمس <b>'+a.elev.toFixed(0)+'°</b>'
    + (a.elev<=0?' — <span class="acs-warn">بعد الغروب</span>':'');
}

/* ========================= ملاحظات المهندس (تحديد + طلب تعديل) ========================= */
let noteMode=false, notes=[], noteTarget=null, notePoint=null, noteMarkers=new THREE.Group();
scene.add(noteMarkers);
const noteModal=document.getElementById('noteModal');

function openNote(obj, point){
  noteTarget=obj; notePoint=point.clone();
  const t=(obj.userData.tag||'').split('|');
  document.getElementById('nmTarget').textContent=
    (LAYER_NAMES[t[0]]||t[0])+' · الدور: '+floorLabel(t[1])+' · الغرفة: '+(t[2]||'-')+' · '+(t[3]||'');
  document.getElementById('nmText').value='';
  document.getElementById('nmColorMsg').textContent='';
  noteModal.classList.add('on');
  setTimeout(()=>document.getElementById('nmText').focus(),50);
}
/* لوحة الألوان السريعة داخل النافذة */
(function initSwatches(){
  const box=document.getElementById('nmSwatches'), inp=document.getElementById('nmColor');
  COLOR_SWATCH.forEach(([nm,hx])=>{
    const i=document.createElement('i'); i.style.background=hx; i.title=nm; i.dataset.hex=hx;
    i.onclick=()=>{ inp.value=hx;
      [...box.children].forEach(c=>c.classList.remove('on')); i.classList.add('on'); };
    box.appendChild(i);
  });
})();
document.querySelectorAll('.nm-color .cbtn').forEach(b=>{
  b.onclick=()=>{
    if(!noteTarget){document.getElementById('nmColorMsg').textContent='حدّد عنصراً أولاً.';return;}
    const hex=document.getElementById('nmColor').value;
    const msg=applyFinish(noteTarget.userData.tag||'', b.dataset.surface, hex, noteTarget);
    document.getElementById('nmColorMsg').textContent=msg;
    statusEl.textContent=msg;
  };
});
function addMarker(p,idx){
  const g=new THREE.SphereGeometry(0.22,14,12);
  const m=new THREE.Mesh(g,new THREE.MeshBasicMaterial({color:0xffb020}));
  m.position.copy(p); m.name='NOTE|'+idx; noteMarkers.add(m);
  const ring=new THREE.Mesh(new THREE.RingGeometry(0.3,0.42,20),
    new THREE.MeshBasicMaterial({color:0xffb020,side:THREE.DoubleSide,transparent:true,opacity:0.7}));
  ring.position.copy(p); ring.lookAt(camera.position); noteMarkers.add(ring);
}
function renderNotes(){
  const box=document.getElementById('notesList'); box.innerHTML='';
  document.getElementById('noteCount').textContent=notes.length;
  notes.forEach((n,i)=>{
    const d=document.createElement('div'); d.className='noteItem'+(n.done?' done':'');
    d.innerHTML='<span class="del" data-i="'+i+'">✕</span><b>'+esc(n.kind)+'</b> — '+
      esc(n.room)+' ('+esc(n.layer)+')<br><span class="acs-dim-80">'+esc(n.text)+'</span>'+
      (n.done?'<br><span class="ok">✓ نُفّذ فوراً محلياً</span>':'');
    d.querySelector('.del').onclick=()=>{notes.splice(i,1);rebuildMarkers();renderNotes();};
    box.appendChild(d);
  });
}
function rebuildMarkers(){
  while(noteMarkers.children.length) noteMarkers.remove(noteMarkers.children[0]);
  notes.forEach((n,i)=>addMarker(new THREE.Vector3(n.p[0],n.p[1],n.p[2]),i));
}
document.getElementById('nmSave').onclick=()=>{
  const txt=document.getElementById('nmText').value.trim();
  if(!txt){document.getElementById('nmText').focus();return;}
  const tag=noteTarget.userData.tag||'';
  const t=tag.split('|');
  const note={kind:document.getElementById('nmKind').value, text:txt,
    layer:LAYER_NAMES[t[0]]||t[0], floor:floorLabel(t[1]), room:t[2]||'-',
    tag:tag, p:[notePoint.x,notePoint.y,notePoint.z]};

  /* تنفيذ فوري لطلبات اللون — بلا انتظار الخادم */
  let done='';
  const hex=detectColor(txt);
  if(hex){
    let surf=detectSurface(txt);
    if(!surf) surf = (t[0]==='WALL')?'wall' : (t[0]==='FLOOR')?'floor' : 'self';
    done=applyFinish(tag, surf, hex, noteTarget);
    note.done=true; note.applied=surf+' '+hex;
  }
  notes.push(note);
  addMarker(notePoint, notes.length-1);
  noteModal.classList.remove('on'); renderNotes();
  statusEl.textContent = done ? ('✓ '+done+' — نُفّذ محلياً بلا خادم.')
    : ('أُضيفت ملاحظة ('+notes.filter(n=>!n.done).length+' بانتظار المحرّك). اضغط «تنفيذ التعديلات».');
};
document.getElementById('nmCancel').onclick=()=>noteModal.classList.remove('on');

document.getElementById('bNoteMode').onclick=function(){
  noteMode=!noteMode; this.classList.toggle('active',noteMode);
  statusEl.textContent=noteMode?'وضع التعليق مفعّل — انقر أي عنصر لكتابة طلب تعديل.':'أُوقف وضع التعليق.';
};
document.getElementById('bNotesExport').onclick=()=>{
  if(!notes.length){statusEl.textContent='لا توجد ملاحظات.';return;}
  const lines=notes.map((n,i)=>(i+1)+'. ['+n.kind+'] '+n.layer+' · '+n.floor+' · '+n.room+' → '+n.text);
  const blob=new Blob([lines.join('\n')+'\n\n---\nJSON:\n'+JSON.stringify(notes,null,1)],
    {type:'text/plain;charset=utf-8'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='ACS-notes.txt'; a.click();
};
document.getElementById('bNotesApply').onclick=async()=>{
  if(!notes.length){statusEl.textContent='أضِف ملاحظة واحدة على الأقل.';return;}
  const pend=notes.filter(n=>!n.done);
  if(!pend.length){statusEl.textContent='✓ كل الملاحظات نُفّذت فوراً محلياً — لا حاجة للخادم.';return;}
  const llm=srvURL();
  if(!llm){statusEl.textContent='محرّك الفهم غير مضبوط — الألوان والتعديلات المباشرة تعمل بلا خادم.';return;}
  if(!lastBuilding){statusEl.textContent='ولّد نموذجاً أولاً.';return;}
  statusEl.textContent='🤖 تنفيذ '+pend.length+' تعديلاً على النموذج… قد يأخذ دقائق.';
  try{
    const res=await __ACS_SHARED.acsFetchJSON('/v1/edit',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({building:lastBuilding, notes:pend})}, 900000);
    if(res.status!==ACS_NET.SUCCESS||!(res.body&&res.body.building))
      throw new Error(res.message+(res.request_id?(' · معرّف الطلب '+res.request_id):''));
    const data=res.body;
    setModel(data.building);
    notes=[]; rebuildMarkers(); renderNotes();
    statusEl.textContent='✓ نُفّذت التعديلات — '+(data.rooms||'?')+' غرفة · '+(data.levels||'?')+' مستوى';
  }catch(e){ statusEl.textContent='تعذّر التنفيذ: '+e.message; console.error(e); }
};

/* أوضاع */
let mode='orbit',tourT=0,real=false;
/* ── انتقال ناعم بين المناظير (يُلغى فور لمس المستخدم للمشهد) ── */
const fly={on:false,t0:0,ms:1100,p0:new THREE.Vector3(),p1:new THREE.Vector3(),
           t0v:new THREE.Vector3(),t1v:new THREE.Vector3()};
function flyTo(pos,target,ms){
  if(renderer.xr.isPresenting||walkState.active){ camera.position.copy(pos);
    orbit.target.copy(target); orbit.update(); return; }
  fly.p0.copy(camera.position); fly.p1.copy(pos);
  fly.t0v.copy(orbit.target);   fly.t1v.copy(target);
  fly.ms=ms||1100; fly.t0=performance.now(); fly.on=true;
}
function flyStep(){
  if(!fly.on) return false;
  const k=Math.min((performance.now()-fly.t0)/fly.ms,1);
  const e=k<0.5 ? 4*k*k*k : 1-Math.pow(-2*k+2,3)/2;      // easeInOutCubic
  camera.position.lerpVectors(fly.p0,fly.p1,e);
  orbit.target.lerpVectors(fly.t0v,fly.t1v,e);
  orbit.update();
  if(k>=1) fly.on=false;
  return true;
}
renderer.domElement.addEventListener('pointerdown',()=>{fly.on=false;});
renderer.domElement.addEventListener('wheel',()=>{fly.on=false;},{passive:true});

/* ── المناظير ── */
const VIEWS={
  orbit:   {ar:'مداري',      icon:'🔄'},
  arch:    {ar:'لقطة معمارية',icon:'🏛️'},
  bird:    {ar:'عين الطائر',  icon:'🦅'},
  top:     {ar:'مسقط علوي',   icon:'⬛'},
  tour:    {ar:'جولة تلقائية',icon:'🎬'},
  walk:    {ar:'منظور شخصي', icon:'🚶'}
};
function viewPose(m){
  const c=bounds.c, r=bounds.r;
  if(m==='top')   return [new THREE.Vector3(c.x, c.y+r*2.6, c.z+0.01), c.clone()];
  if(m==='bird')  return [new THREE.Vector3(c.x-r*1.15, c.y+r*1.55, c.z+r*1.15), c.clone()];
  if(m==='arch')  // كاميرا معمارية: أفقية بارتفاع النظر، بلا ميل رأسي (خطوط رأسية مستقيمة)
    return [new THREE.Vector3(c.x, c.y-r*0.30, c.z+r*2.5),
            new THREE.Vector3(c.x, c.y-r*0.30, c.z)];
  return [new THREE.Vector3(c.x+r*1.45, c.y+r*0.80, c.z+r*1.45), c.clone()];
}
function setMode(m){
  if(m==='walk'){ mode=m; startWalk(); markView(m); return; }
  if(walkState.active) stopWalk();
  mode=m; markView(m);
  if(m==='tour'){ tourT=performance.now(); return; }
  const [p,t]=viewPose(m);
  flyTo(p,t,1100);
  statusEl.textContent='المنظور: '+(VIEWS[m]?VIEWS[m].ar:m);
}
function markView(m){
  document.querySelectorAll('#camBar button[data-view]').forEach(b=>
    b.classList.toggle('on', b.dataset.view===m));
}
document.getElementById('bShot').onclick=()=>{renderer.render(scene,camera);
  const a=document.createElement('a');a.download='ACS-view.png';a.href=renderer.domElement.toDataURL('image/png');a.click();};

/* تصدير GLB — الجسر إلى Unreal Engine وبقية برامج الـ3D */
function dl(blob,name){ const u=URL.createObjectURL(blob); const a=document.createElement('a');
  a.href=u; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(u),4000); }
document.getElementById('bGlb').onclick=()=>{
  if(!model){statusEl.textContent='ولّد نموذجاً أولاً.';return;}
  statusEl.textContent='جارٍ تجهيز ملف GLB…';
  const nm=((lastBuilding&&lastBuilding.meta&&lastBuilding.meta.name)||'ACS-model')
            .replace(/[\\/:*?"<>|]/g,'-').slice(0,60);
  new GLTFExporter().parse(model, res=>{
      dl(new Blob([res],{type:'model/gltf-binary'}), nm+'.glb');
      let n=0; model.traverse(o=>{if(o.isMesh)n++;});
      statusEl.textContent='✓ صُدِّر '+nm+'.glb — '+n+' عنصراً · جاهز للاستيراد في Unreal.';
    }, err=>{ statusEl.textContent='تعذّر التصدير: '+err; console.error(err); },
    {binary:true, onlyVisible:false, truncateDrawRange:false});
};
document.getElementById('bJson').onclick=()=>{
  if(!lastBuilding){statusEl.textContent='ولّد نموذجاً أولاً.';return;}
  const nm=((lastBuilding.meta&&lastBuilding.meta.name)||'ACS-building')
            .replace(/[\\/:*?"<>|]/g,'-').slice(0,60);
  const payload=projectEnvelope(lastBuilding);   // هرمية المشروع + حقول المرحلة 1 كما هي
  dl(new Blob([JSON.stringify(payload,null,1)],{type:'application/json'}), nm+'.json');
  statusEl.textContent='✓ صُدِّرت بيانات المبنى JSON.';
};

/* مشي */
const keys={};addEventListener('keydown',e=>keys[e.code]=true);addEventListener('keyup',e=>keys[e.code]=false);
// ضوء داخلي يتبع الكاميرا حتى لا تكون الغرف مظلمة أثناء المشي
const headLamp=new THREE.PointLight(0xfff2d8,0,26,2); scene.add(headLamp);

const walkHUD=document.getElementById('walkHUD');
function startWalk(){
  walkState.active=true; walkHUD.classList.add('on');
  orbit.enabled=false;
  const c=bounds.c;
  camera.position.set(c.x, (model? new THREE.Box3().setFromObject(model).min.y : 0) + walkState.eye, c.z);
  walkState.yaw=0; walkState.pitch=0; applyWalkCamera();
  camera.fov=+document.getElementById('optFov').value; camera.updateProjectionMatrix();
}
function stopWalk(){ walkState.active=false; walkHUD.classList.remove('on'); orbit.enabled=true;
  camera.fov=52; camera.updateProjectionMatrix(); }

/* النظر بالسحب (فأرة/لمس) داخل وضع المشي */
(function(){
  let last=null;
  const el=renderer.domElement;
  const start=e=>{ if(!walkState.active)return; const t=e.touches?e.touches[0]:e;
    if(e.touches&&e.touches.length>1)return; last=[t.clientX,t.clientY]; };
  const move=e=>{ if(!walkState.active||!last)return; const t=e.touches?e.touches[0]:e;
    walkLook(t.clientX-last[0], t.clientY-last[1]); last=[t.clientX,t.clientY];
    if(e.cancelable)e.preventDefault(); };
  const end=()=>{ last=null; };
  el.addEventListener('mousedown',start); addEventListener('mousemove',move); addEventListener('mouseup',end);
  el.addEventListener('touchstart',start,{passive:true});
  el.addEventListener('touchmove',move,{passive:false});
  addEventListener('touchend',end);
})();

/* الجويستيك */
(function(){
  const joy=document.getElementById('joy'), knob=document.getElementById('joyKnob');
  let id=null, cx=0, cy=0;
  const R=41;
  function set(dx,dy){
    const len=Math.hypot(dx,dy), k=len>R?R/len:1;
    dx*=k; dy*=k; knob.style.left=(41+dx)+'px'; knob.style.top=(41+dy)+'px';
    walkState.tx = dx/R; walkState.tz = -dy/R; walkState.joy = true;
  }
  function reset(){ knob.style.left='41px'; knob.style.top='41px';
    walkState.tx=walkState.tz=0; walkState.joy=false; }
  function down(e){ const r=joy.getBoundingClientRect(); cx=r.left+r.width/2; cy=r.top+r.height/2;
    const t=e.touches?e.touches[0]:e; id=1; set(t.clientX-cx,t.clientY-cy); if(e.cancelable)e.preventDefault(); }
  function mv(e){ if(!id)return; const t=e.touches?e.touches[0]:e; set(t.clientX-cx,t.clientY-cy);
    if(e.cancelable)e.preventDefault(); }
  function up(){ id=null; reset(); }
  joy.addEventListener('mousedown',down); addEventListener('mousemove',mv); addEventListener('mouseup',up);
  joy.addEventListener('touchstart',down,{passive:false});
  joy.addEventListener('touchmove',mv,{passive:false});
  addEventListener('touchend',up);
})();

/* أزرار المشي وخيارات الرؤية */
(function(){
  const hold=(id,on,off)=>{const b=document.getElementById(id);
    const s=e=>{on(); b.classList.add('active'); if(e.cancelable)e.preventDefault();};
    const t=()=>{off(); b.classList.remove('active');};
    b.addEventListener('mousedown',s); b.addEventListener('mouseup',t); b.addEventListener('mouseleave',t);
    b.addEventListener('touchstart',s,{passive:false}); b.addEventListener('touchend',t);};
  hold('wUp',  ()=>walkState.vy= 1, ()=>walkState.vy=0);
  hold('wDown',()=>walkState.vy=-1, ()=>walkState.vy=0);
  const run=document.getElementById('wRun');
  run.onclick=()=>{ walkState.run = walkState.run>1?1:2.2; run.classList.toggle('active', walkState.run>1); };
  document.getElementById('wExit').onclick=()=>setMode('orbit');
  document.getElementById('optFov').oninput=e=>{ camera.fov=+e.target.value; camera.updateProjectionMatrix(); };
  document.getElementById('optEye').oninput=e=>{ walkState.eye=(+e.target.value)/100; };
  document.getElementById('optSpd').oninput=e=>{ walkState.speed=+e.target.value; };
})();

function walkStep(dt){
  const f=(keys.KeyW?1:0)-(keys.KeyS?1:0), s=(keys.KeyD?1:0)-(keys.KeyA?1:0);
  const q=(keys.KeyQ||keys.Space?1:0)-(keys.KeyE||keys.ShiftLeft?1:0);
  /* تنعيم: نقترب من السرعة المطلوبة تدريجياً فتبدو الحركة سلسة لا مفاجئة */
  if(walkState.tx===undefined){walkState.tx=0;walkState.tz=0;}
  if(f||s){ walkState.tz=f; walkState.tx=s; }
  else if(!walkState.joy){ walkState.tz*=0.82; walkState.tx*=0.82;
    if(Math.abs(walkState.tz)<0.02)walkState.tz=0; if(Math.abs(walkState.tx)<0.02)walkState.tx=0; }
  const k=Math.min(dt*9,1);
  walkState.vz += (walkState.tz-walkState.vz)*k;
  walkState.vx += (walkState.tx-walkState.vx)*k;
  if(q) walkState.vy=q;
  walkState.run = keys.ShiftRight?2.2:walkState.run;
  applyWalkCamera(); walkMove(dt);
  if(!q&&!document.getElementById('wUp').classList.contains('active')
     &&!document.getElementById('wDown').classList.contains('active')) walkState.vy=0;
}
function tourStep(){const t=(performance.now()-tourT)/1000,a=(t%45)/45*Math.PI*2,R=bounds.r*1.5;
  camera.position.set(bounds.c.x+Math.cos(a)*R,bounds.c.y+bounds.r*0.55,bounds.c.z+Math.sin(a)*R);orbit.target.copy(bounds.c);}

/* إفلات صورة */
const drop=document.getElementById('drop');
addEventListener('dragover',e=>{e.preventDefault();drop.style.display='flex';});
drop.addEventListener('dragleave',()=>drop.style.display='none');
addEventListener('drop',e=>{e.preventDefault();drop.style.display='none';
  const f=e.dataTransfer.files[0];if(f&&/^image\//.test(f.type))useDoorImage(f);});

addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
let last=performance.now();
/* ==================================================================
   الواقع الافتراضي — Meta Quest 3 وغيرها عبر WebXR
   تمشي داخل المبنى بمقياس 1:1 حقيقي: ارتفاعك الفعلي، وأبعاد الغرف بالمتر.
   ================================================================== */
const vr={on:false, mode:'vr', turnCool:0, floorCool:0, snap:true, speed:2.6,
          savedDetail:1, savedShadow:true, rays:[], maq:null, arSaved:null};

function vrSetup(){
  for(let i=0;i<2;i++){
    const c=renderer.xr.getController(i);
    const g=new THREE.BufferGeometry().setFromPoints(
      [new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,-1)]);
    const line=new THREE.Line(g,new THREE.LineBasicMaterial({color:0x38bdf8}));
    line.scale.z=3; c.add(line);
    const grip=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.04,0.12),
      new THREE.MeshStandardMaterial({color:0x1b1d21,roughness:0.5}));
    grip.position.z=0.03; c.add(grip);
    c.addEventListener('selectstart',()=>vrTeleport(c));
    player.add(c); vr.rays.push(c);
  }
}
function camWorld(){
  const v=new THREE.Vector3();
  (renderer.xr.isPresenting?renderer.xr.getCamera():camera).getWorldPosition(v);
  return v;
}
function vrRotate(a){
  const c=camWorld();
  player.position.sub(c);
  player.position.applyAxisAngle(new THREE.Vector3(0,1,0),a);
  player.position.add(c);
  player.rotation.y+=a;
}
/* الانتقال الفوري: صوّب بالذراع نحو الأرض واضغط الزناد */
const vrRay=new THREE.Raycaster();
function vrTeleport(ctrl){
  if(!model) return;
  if(vr.mode==='ar'){                       // في الماكيت: الزناد يعيد وضعه أمامك
    if(vr.maq){ const c=camWorld();
      const q=new THREE.Quaternion(); (renderer.xr.getCamera()).getWorldQuaternion(q);
      const e=new THREE.Euler().setFromQuaternion(q,'YXZ');
      vr.maq.position.set(c.x-Math.sin(e.y)*0.9, Math.max(c.y-0.85,0.2), c.z-Math.cos(e.y)*0.9); }
    return;
  }
  const m=new THREE.Matrix4().identity().extractRotation(ctrl.matrixWorld);
  vrRay.ray.origin.setFromMatrixPosition(ctrl.matrixWorld);
  vrRay.ray.direction.set(0,0,-1).applyMatrix4(m);
  const hits=vrRay.intersectObjects([model,...(ground?[ground]:[])],true)
                  .filter(h=>h.object.visible);
  if(!hits.length) return;
  const p=hits[0].point, c=camWorld();
  player.position.x += p.x-c.x;
  player.position.z += p.z-c.z;
  player.position.y  = Math.round(p.y*100)/100;      // ارتفاع أرضية نقطة الوصول
}
/* عصا التحكّم: يسار = مشي · يمين = التفاف/طيران · A صعود دور · B نزول دور */
function vrStep(dt){
  const s=renderer.xr.getSession(); if(!s) return;
  const fh=(lastBuilding&&lastBuilding.floor_height)||3.2;
  vr.turnCool=Math.max(0,vr.turnCool-dt); vr.floorCool=Math.max(0,vr.floorCool-dt);
  const xc=renderer.xr.getCamera();
  /* وضع الماكيت: العصي تدير المجسّم وتكبّره بدل أن تحرّكك */
  if(vr.mode==='ar'){
    for(const src of s.inputSources){
      const gp=src.gamepad; if(!gp||!vr.maq) continue;
      const a=gp.axes, ax=(a.length>2?a[2]:a[0])||0, ay=(a.length>3?a[3]:a[1])||0;
      const dz=v=>Math.abs(v)<0.18?0:v;
      if(src.handedness==='right'){
        if(dz(ax)) vr.maq.rotation.y -= dz(ax)*1.4*dt;
        if(dz(ay)) vr.maq.scale.multiplyScalar(1 - dz(ay)*0.9*dt);
      }else{
        if(dz(ay)) vr.maq.position.y -= dz(ay)*0.5*dt;   // ارفع/اخفض الماكيت
        if(dz(ax)) vr.maq.position.x += dz(ax)*0.5*dt;
      }
    }
    return;
  }
  for(const src of s.inputSources){
    const gp=src.gamepad; if(!gp) continue;
    const a=gp.axes, ax=(a.length>2?a[2]:a[0])||0, ay=(a.length>3?a[3]:a[1])||0;
    const dz=v=>Math.abs(v)<0.18?0:v;
    const sprint=(gp.buttons[1]&&gp.buttons[1].pressed)?2.6:1;
    if(src.handedness==='left'){
      const mx=dz(ax), my=dz(ay);
      if(mx||my){
        const q=new THREE.Quaternion(); xc.getWorldQuaternion(q);
        const e=new THREE.Euler().setFromQuaternion(q,'YXZ');
        const f=new THREE.Vector3(-Math.sin(e.y),0,-Math.cos(e.y));
        const r=new THREE.Vector3(Math.cos(e.y),0,-Math.sin(e.y));
        const sp=vr.speed*sprint*dt;
        player.position.addScaledVector(f,-my*sp);
        player.position.addScaledVector(r, mx*sp);
      }
    }else{
      const tx=dz(ax), ty=dz(ay);
      if(vr.snap){ if(Math.abs(tx)>0.7&&vr.turnCool<=0){ vrRotate(-Math.sign(tx)*Math.PI/6); vr.turnCool=0.28; } }
      else if(tx) vrRotate(-tx*1.6*dt);
      if(Math.abs(ty)>0.6) player.position.y -= ty*2.2*dt*sprint;   // طيران رأسي
    }
    const b=gp.buttons;
    if(b[4]&&b[4].pressed&&vr.floorCool<=0){ player.position.y+=fh; vr.floorCool=0.35; }
    if(b[5]&&b[5].pressed&&vr.floorCool<=0){ player.position.y-=fh; vr.floorCool=0.35; }
  }
}
/* وضع الماكيت (Passthrough): المبنى مصغَّر على طاولتك في غرفتك الحقيقية */
function arScale(){
  if(!model) return;
  const s=Math.min(1.2/Math.max(bounds.r*2,0.001),1);
  vr.arSaved={pos:model.position.clone(),scale:model.scale.clone()};
  model.scale.setScalar(s);
  model.position.set(-bounds.c.x*s, 0, -bounds.c.z*s);
  const g=new THREE.Group(); g.name='MAQUETTE';
  scene.remove(model); g.add(model); scene.add(g); vr.maq=g;
  g.position.set(0,0.75,-0.9);              // أمامك بارتفاع طاولة
  if(ground) ground.visible=false;
  sky.visible=false; scene.background=null;
}
function arRestore(){
  if(vr.maq&&model){ vr.maq.remove(model); scene.add(model); scene.remove(vr.maq); }
  vr.maq=null;
  if(vr.arSaved&&model){ model.position.copy(vr.arSaved.pos); model.scale.copy(vr.arSaved.scale); }
  vr.arSaved=null;
  if(ground) ground.visible=true;
  sky.visible=true;
}
function vrEnter(){
  vr.on=true;
  const ses=renderer.xr.getSession();
  vr.mode=((ses&&ses.environmentBlendMode)||'opaque')==='opaque'?'vr':'ar';   // شفاف = تمرير كاميرا Quest
  vr.savedShadow=renderer.shadowMap.enabled;
  vr.savedDetail=__ACS_SHARED.DETAIL;
  if(walkState.active) stopWalk();
  try{ renderer.xr.setFoveation(1); }catch(e){}
  let n=0; if(model) model.traverse(o=>{if(o.isMesh)n++;});
  // ثبات الإطار أهم من الظلال داخل النظارة، والمشاهد الثقيلة تُبنى بتفصيل أخفّ
  renderer.shadowMap.enabled=false; sun.castShadow=false;
  if(n>2200&&__ACS_SHARED.DETAIL>0.5){ __ACS_SHARED.DETAIL=0.5; const ds=document.getElementById('detailSel');
    if(ds) ds.value='0.5'; setModel(null); }
  player.rotation.y=0;
  if(vr.mode==='ar'){
    player.position.set(0,0,0); arScale(); headLamp.intensity=0;
    statusEl.textContent='وضع الماكيت (Passthrough) — المبنى مصغّر أمامك في غرفتك · '
      +'العصا اليمنى تدوّره · الزناد يعيد وضعه أمامك.';
  }else{
    player.position.set(bounds.c.x, 0, bounds.c.z+Math.min(bounds.r*0.55,14));
    headLamp.intensity=28;
    statusEl.textContent='وضع VR فعّال — العصا اليسرى للمشي · اليمنى للالتفاف · '
      +'الزناد للانتقال · A/B لتغيير الدور.';
  }
}
function vrExit(){
  vr.on=false;
  if(vr.mode==='ar') arRestore();
  vr.mode='vr';
  renderer.shadowMap.enabled=vr.savedShadow; sun.castShadow=true;
  headLamp.intensity=0;
  player.position.set(0,0,0); player.rotation.y=0;
  if(__ACS_SHARED.DETAIL!==vr.savedDetail){ __ACS_SHARED.DETAIL=vr.savedDetail;
    const ds=document.getElementById('detailSel'); if(ds) ds.value=String(__ACS_SHARED.DETAIL); setModel(null); }
  statusEl.textContent='خرجت من وضع النظارة.';
}
renderer.xr.addEventListener('sessionstart',vrEnter);
renderer.xr.addEventListener('sessionend',vrExit);
vrSetup();

/* زر الدخول للنظارة داخل لوحة العرض + كشف التوفّر */
(function initVR(){
  const box=document.getElementById('vrbox'); if(!box) return;
  const st=document.getElementById('vrState');
  if(!navigator.xr){
    st.innerHTML='هذا المتصفّح لا يدعم WebXR. افتح الموقع من <b>متصفّح Meta Quest</b> داخل النظارة '
      +'(الرابط نفسه)، ولا بدّ أن يكون <b>https</b>.';
    return;
  }
  const secure=(location.protocol==='https:'||location.hostname==='localhost'||location.protocol==='file:');
  if(!secure){
    st.innerHTML='⚠️ WebXR يتطلّب <b>https</b>. انشر الموقع (Netlify) ثم افتح الرابط '
      +'من متصفّح Meta Quest داخل النظارة.';
    return;
  }
  navigator.xr.isSessionSupported('immersive-vr').then(ok=>{
    if(!ok){ st.innerHTML='لم تُكتشف نظارة على هذا الجهاز. افتح الرابط نفسه من '
      +'<b>متصفّح Meta Quest</b> داخل النظارة، وسيظهر الزر.'; return; }
    const b=VRButton.createButton(renderer);
    box.appendChild(b);
    st.innerHTML='✓ النظارة جاهزة — «ENTER VR» يدخلك المبنى بمقياس 1:1 حقيقي.';
    // Quest 3: وضع الماكيت بتمرير الكاميرا (Passthrough)
    navigator.xr.isSessionSupported('immersive-ar').then(ar=>{
      if(!ar) return;
      const a=ARButton.createButton(renderer,{optionalFeatures:['local-floor','bounded-floor']});
      a.textContent='🏠 ماكيت في غرفتك (Passthrough)';
      box.appendChild(a);
    }).catch(()=>{});
  }).catch(()=>{ st.textContent='تعذّر فحص دعم النظارة.'; });
  document.getElementById('vrSnap').onchange=e=>{ vr.snap=e.target.checked; };
  document.getElementById('vrSpeed').oninput=e=>{ vr.speed=+e.target.value/10; };
})();

let last2=performance.now();
renderer.setAnimationLoop(()=>{
  const now=performance.now(),dt=Math.min((now-last2)/1000,0.1); last2=now;
  if(renderer.xr.isPresenting){
    vrStep(dt);
    headLamp.position.copy(camWorld());
  }else{
    if(walkState.active)walkStep(dt);
    else if(flyStep()){ /* انتقال ناعم جارٍ */ }
    else{ if(mode==='tour')tourStep(); orbit.update(); }
    headLamp.intensity = walkState.active ? 55 : 0;
    if(walkState.active) headLamp.position.copy(camera.position);
  }
  if(window.__ACS_PQ__&&window.__ACS_PQ__.composer&&!renderer.xr.isPresenting){window.__ACS_PQ__.composer.render();}else{renderer.render(scene,camera);}
});

/* ========================= الواجهة / التبويبات / الدخول ========================= */
function showTab(t){
  /* الإخفاء الابتدائي صنفٌ الآن لا سمة style (style-src 'self')، وإسناد
     style.display='' لا يمحو قاعدة صنف — فالتبديل يجري على الصنف أيضاً. */
  document.querySelectorAll('[data-panel]').forEach(p=>{
    const on = p.dataset.panel===t;
    p.classList.toggle('acs-hidden', !on);
    p.style.display = on ? '' : 'none';
  });
  const bd=document.querySelector('.body'); if(bd) bd.scrollTop=0;
}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');showTab(b.dataset.tab);});

/* يعرض للعميل تقرير تغطية المسار المحلي بنفس صيغة تقرير الخادم */
function showCoverage(cov, added, msg, excluded){
  const box=document.getElementById('reportBox'); if(!box) return;
  if(cov===null){ box.className='report'; box.innerHTML=''; return; }
  if(msg){ box.innerHTML='<div class="rq warn">'+esc(msg)+'</div>'; box.className='report on'; return; }
  // excluded تُمرَّر كفئة مستقلّة — لا تُدمَج مع «مُثِّل بطريقة بديلة»،
  // والتصنيف حسب المصدر يتم داخل showReport (طلب مستخدم/استنتاج/إضافة نظام)
  showReport({requirements:cov, extras:[], excluded:(excluded||[]), added:added||[]});
}

/* نوع المبنى المختار (يُشارَك بين كل التبويبات) — auto يكشفه من النص */
function pickedType(txt){
  const sel=(document.getElementById('bType')||{}).value||'auto';
  return sel==='auto' ? detectTypeJS(txt||'') : sel;
}
/* المولّد المحلي الموحّد: يخدم «وصف نصّي» و«سريع» و«ملفات» بنفس القدرات */
function buildLocal(txt,W,D,nF){
  const t=pickedType(txt);
  __ACS_SHARED.LAST_REQUEST_TEXT = txt||'';            // للتحقّق من ادّعاءات التقرير مقابل طلب العميل
  const oi=objectsFromText(txt);          // بشر/روبوتات/رافعات… من طلب العميل — لا تُسقَط
  if(isIndustrialProgram(t)){            // مسار البرنامج الصناعي (مستودع/مصنع/…) — واحد من عدّة برامج
    const T=normDigits(txt||'');
    const m=T.match(/(\d{2,4})\s*[×xX*]\s*(\d{2,4})/);            // «120x80» في النص يغلب الحقول
    const num=(re)=>{const g=T.match(re); const v=g?parseInt(g[1]||g[2]):NaN; return isNaN(v)?null:v;};
    const w=m?+m[1]:W, d=m?+m[2]:D;
    const clear=num(/ارتفاع\s*(?:صاف[يٍ]?)?\s*(\d{1,2})|clear\s*height\s*(\d{1,2})/);
    const strict=!!(document.getElementById('strictMode')||{}).checked;
    /* الأولوية المطلقة لوصف العميل: نبني ما ذكره هو فقط، بأعداده ومقاساته */
    const ft=warehouseFromText(txt,w,d,{clear:clear,strict:strict});
    if(ft){
      attachObjects(ft.building, oi.objects);
      const reqs=ft.coverage.concat(objCoverage(oi.objects)),
            exc=(ft.excluded||[]).concat(oi.excluded);
      // meta already holds zone coverage/excluded/added — add only the object-level items
      stampMeta(ft.building,'warehouse',objCoverage(oi.objects),oi.excluded,[]);
      showCoverage(reqs, ft.added, null, exc);
      return ft.building;
    }
    /* لم يذكر أي منطقة صناعية معروفة → لكن قد يكون ذكر عناصر (عمّال/رافعات) فلا نُسقِطها */
    const wm=warehouseModel(w,d,{clear:clear||12});
    if(oi.objects.length){
      attachObjects(wm, oi.objects);
      const reqs=objCoverage(oi.objects);
      stampMeta(wm,'warehouse',reqs,oi.excluded,[]);
      showCoverage(reqs, [], null, oi.excluded);
      return wm;
    }
    stampMeta(wm,'warehouse',[],oi.excluded,[]);
    showCoverage([], [], 'لم أتعرّف على مناطق في وصفك لأبنيها. اذكر ما تريده '
      +'(أرصفة، تخزين بالتات، أرفف، التقاط، تغليف، فرز، شحن، مكاتب، صيانة…) '
      +'بأعداده ومقاساته، وسأبني ما ذكرتَه وحده. أو جرّب «مثال: مستودع 120×80» للاطّلاع.');
    return wm;
  }
  /* المسار العام: أبنِ الغرف ثم أرفِق العناصر المطلوبة وأظهِر تغطيتها */
  const b=parseDescription(txt,W,D,nF);
  attachObjects(b, oi.objects);
  const reqs=objCoverage(oi.objects);
  stampMeta(b, t, reqs, oi.excluded, []);                    // تغطية في meta للتصدير
  if(oi.objects.length || oi.excluded.length)
    showCoverage(reqs, [], null, oi.excluded);
  else
    showCoverage(null);
  return b;
}
document.getElementById('genText').onclick=()=>{
  const txt=document.getElementById('descText').value.trim();
  if(!txt){statusEl.textContent='اكتب وصفاً أولاً.';return;}
  const W=+document.getElementById('siteW').value||30,D=+document.getElementById('siteD').value||25,
    nF=+document.getElementById('nFloors').value||3;
  statusEl.textContent='جارٍ التحليل والتوليد…';
  setTimeout(()=>{try{setModel(buildLocal(txt,W,D,nF));}catch(e){statusEl.textContent='خطأ: '+e.message;console.error(e);}},30);
};
/* ===== الخادم المدمج: يعمل لكل زائر بلا كتابة أي رابط ===== */
let SRV_OK=false;
/* ===== عقد نداء الواجهة: عنوان واحد، تصنيف صريح، جسد يُقرأ مرّة واحدة ===== */
function srvURL(){
  /* المصدر الوحيد window.ACS_API. الحقل اليدوي تجاوزٌ يُغذّيه، لا عنوان ثانٍ. */
  const manual=((document.getElementById('llmURL')||{}).value||'').trim();
  window.ACS_API.override=manual;
  return window.ACS_API.base();
}
function apiURL(path){ srvURL(); return window.ACS_API.url(path); }

const ACS_NET={
  SUCCESS:'SUCCESS', OFFLINE:'NETWORK_OFFLINE', DNS:'NETWORK_DNS',
  TIMEOUT:'TIMEOUT', NOT_CONFIGURED:'NOT_CONFIGURED',
  HTTP_4XX:'HTTP_4XX', HTTP_429:'HTTP_429', HTTP_5XX:'HTTP_5XX',
  INVALID_JSON:'INVALID_JSON', API_ERROR:'VALID_API_ERROR'
};
let ACS_LAST_CALL=null;      /* آخر نتيجة نداء — يقرأها ACS.apiDiagnostics() */

/* نداء واحد مصنَّف. لا نستدعي response.json() على العمياء أبداً: الجسد يُقرأ
   نصّاً مرّة واحدة ثمّ يُحلَّل، فخطأ التحليل يصير حالة معلنة لا استثناءً مبهماً،
   ولا يقع «body stream already read» عند محاولة قراءته مرّتين. */
__ACS_SHARED.acsFetchJSON = async function acsFetchJSON(path, opts, timeoutMs){
  const started=Date.now();
  const url=apiURL(path);
  const out={status:'', http:0, request_id:'', url:url, path:path,
             ms:0, body:null, message:'', retryable:false, retry_after:0};
  const done=(o)=>{ o.ms=Date.now()-started; ACS_LAST_CALL=o; return o; };
  if(!window.ACS_API.base()){
    out.status=ACS_NET.NOT_CONFIGURED;
    out.message='عنوان محرّك الفهم غير مضبوط في هذه النسخة من الصفحة.';
    return done(out);
  }
  if(typeof navigator!=='undefined' && navigator.onLine===false){
    out.status=ACS_NET.OFFLINE; out.message='لا يوجد اتصال بالإنترنت على هذا الجهاز.';
    return done(out);
  }
  const c=new AbortController();
  const t=setTimeout(()=>c.abort(), Math.max(1000, timeoutMs||60000));
  let r;
  try{
    r=await fetch(url, Object.assign({signal:c.signal}, opts||{}));
  }catch(e){
    clearTimeout(t);
    if(e && e.name==='AbortError'){
      out.status=ACS_NET.TIMEOUT;
      out.message='انتهت المهلة قبل رد الخادم ('+Math.round((timeoutMs||60000)/1000)+' ثانية).';
      out.retryable=true; return done(out);
    }
    /* المتصفّح لا يكشف سبب فشل الشبكة لسكربت الصفحة (TypeError: Failed to fetch
       تغطّي DNS وCORS والرفض). نُعلن ذلك صراحةً بدل ادّعاء سبب بعينه. */
    out.status=(typeof navigator!=='undefined' && navigator.onLine===false)
      ? ACS_NET.OFFLINE : ACS_NET.DNS;
    out.message='تعذّر الوصول إلى الخادم على '+window.ACS_API.host()
      +' (تعذّر تحديد الاسم، أو رفض الاتصال، أو منع CORS).';
    out.retryable=true; return done(out);
  }
  clearTimeout(t);
  out.http=r.status;
  out.request_id=(r.headers&&r.headers.get&&r.headers.get('X-Request-ID'))||'';
  const ra=(r.headers&&r.headers.get&&r.headers.get('Retry-After'))||'';
  out.retry_after=parseInt(ra,10)||0;
  let raw='';
  try{ raw=await r.text(); }catch(e){ raw=''; }        /* ← قراءة واحدة فقط */
  let data=null, parsed=false;
  if(raw){ try{ data=JSON.parse(raw); parsed=true; }catch(e){ parsed=false; } }
  out.body=data;
  if(!parsed){
    out.status=ACS_NET.INVALID_JSON;
    out.message='رد الخادم ليس JSON صالحاً (HTTP '+r.status+'، '
      +raw.length+' حرفاً). أول ما ورد: '+raw.slice(0,80).replace(/\s+/g,' ');
    return done(out);
  }
  if(data && data.ok===false && data.error){
    out.status=ACS_NET.API_ERROR;
    out.request_id=data.error.request_id||out.request_id;
    out.message=data.error.message||'فشل معلن من الخادم.';
    out.code=data.error.code||''; out.retryable=!!data.error.retryable;
    return done(out);
  }
  if(!r.ok){
    out.status = r.status===429?ACS_NET.HTTP_429
               : (r.status>=500?ACS_NET.HTTP_5XX:ACS_NET.HTTP_4XX);
    out.message=(data&&(data.detail||data.message))||('HTTP '+r.status+' من الخادم.');
    out.retryable=(r.status===429||r.status>=500);
    return done(out);
  }
  out.status=ACS_NET.SUCCESS;
  return done(out);
};
function srvPill(cls,txt){
  const p=document.getElementById('srvPill'); if(!p) return;
  p.className='srv'+(cls?' '+cls:''); p.innerHTML=txt;
}
async function checkServer(quiet){
  const u=srvURL();
  if(!u){ SRV_OK=false;
    srvPill('bad','محرّك الفهم غير مضبوط — التوليد سيكون محلياً تقريبياً. '
      +'<span class="acs-dim-75">(ضع رابط الخادم في الإعدادات المتقدّمة أو في أعلى ملف الموقع)</span>');
    return false; }
  const res=await __ACS_SHARED.acsFetchJSON('/health',{method:'GET'},12000);
  if(res.status!==ACS_NET.SUCCESS){
    SRV_OK=false;
    srvPill('bad','تعذّر الوصول لمحرّك الفهم على '+esc(window.ACS_API.host())+' — '
      +esc(res.status)+'. <span class="acs-dim-75">(قد يكون الخادم نائماً؛ أعِد المحاولة بعد دقيقة)</span>');
    return false;
  }
  const j=res.body||{};
  /* الحقول الجديدة أولاً، والقديمة توافقاً — الخادم يعلن كليهما في /health */
  const keyed=(j.api_key_configured!==undefined)?!!j.api_key_configured:!!j.key;
  SRV_OK=!!(j.ok&&keyed);
  if(SRV_OK){ const L=j.limits||{};
    srvPill('ok','✓ محرّك الفهم متصل — التوليد يقرأ وصفك ويبني عليه'
      +(L.gen_hour?(' <span class="acs-dim-70">(حتى '+L.gen_hour+' عمليات/ساعة)</span>'):'')); }
  else srvPill('bad','الخادم يعمل لكن بلا مفتاح API — التوليد سيكون محلياً.');
  return SRV_OK;
}
/* تقرير التغطية: يعرض كل بند من طلب العميل وأين نُفِّذ */
/* تقرير التغطية — فئات متمايزة لا تُدمَج أبداً:
   طُلب ونُفِّذ · مُثِّل بطريقة بديلة (غير مدعوم مباشرةً) · مُستبعَد بنفيك · أُضيف تلقائياً */
function showReport(rep, userText){
  const box=document.getElementById('reportBox'); if(!box) return;
  const repair=rep&&rep.repair_proposal&&rep.repair_proposal.building ? rep.repair_proposal : null;
  const c=classifyReport(rep, userText!=null?userText:__ACS_SHARED.LAST_REQUEST_TEXT);
  const n=c.user.length+c.ai.length+c.system.length+c.rule.length
         +c.alt.length+c.unsupported.length+c.excluded.length;
  if(!n&&!repair){ box.className='report'; box.innerHTML=''; return; }
  const full=(r,cls)=>'<div class="rq '+cls+'"><b>'+esc(r.req||'')+'</b>'
      +(r.where?'<br><span class="w">↳ في: '+esc(r.where)+'</span>':'')
      +(r.how?'<br><span class="w">'+esc(r.how)+'</span>':'')+'</div>';
  const line=(t,cls)=>'<div class="rq '+cls+'"><span class="w">'+esc(String(t))+'</span></div>';
  let h='<h3>تقرير التغطية</h3>';
  if(c.floors&&c.floors.requested!=null)
    h+=line('عدد الأدوار الذي طلبته: '+c.floors.requested,'');
  if(c.user.length){ h+='<div class="rqhdr">✓ طلبتَه ونُفِّذ — '+c.user.length+' بند</div>';
    c.user.forEach(r=>h+=full(r,'')); }
  if(c.ai.length){ h+='<div class="rqhdr">◇ استُنتج (لم يرد صراحةً في طلبك)</div>';
    c.ai.forEach(r=>h+=full(r,'ai')); }
  if(c.system.length){ h+='<div class="rqhdr">＋ أضافه النظام تلقائياً</div>';
    c.system.forEach(r=>h+=full(r,'add')); }
  if(c.rule.length){ h+='<div class="rqhdr">⚖ مطلوب بقاعدة موثّقة</div>';
    c.rule.forEach(r=>{ h+='<div class="rq rule"><b>'+esc(r.req||'')+'</b><br><span class="w">'
      +esc([r.standard,r.edition,r.rule_id].filter(Boolean).join(' · ')
           +' — '+r.condition+' ⇒ '+r.result)+'</span></div>'; }); }
  if(c.alt.length){ h+='<div class="rqhdr">↺ مُثِّل بطريقة بديلة</div>';
    c.alt.forEach(t=>h+=line(t,'x')); }
  if(c.unsupported.length){ h+='<div class="rqhdr">⚠ غير مدعوم</div>';
    c.unsupported.forEach(t=>h+=line(t,'x')); }
  if(c.excluded.length){ h+='<div class="rqhdr">− مُستبعَد بناءً على نفيك — لم يُضَف</div>';
    c.excluded.forEach(t=>h+=line(t,'neg')); }
  // إفصاح صريح: لا تحقّق مطابقة لأي كود في هذه المرحلة
  if(!c.rule.length && (c.system.length||c.ai.length))
    h+='<div class="rqnote">ملاحظة: العناصر التلقائية إعدادات افتراضية للنظام — '
      +'لم يُنفَّذ تحقّق مطابقة لأي كود أو معيار في هذه المرحلة.</div>';
  if(repair){
    h+='<div class="rq warn"><b>إصلاح مقترح — لم يُطبّق</b><br>'
      +'راجع الفروق، ثم نزّل المقترح واستورده إذا أردت اعتماده. النموذج الأصلي محفوظ.'
      +'<details><summary>عرض الفروق</summary><pre>'
      +esc(JSON.stringify(repair.engineering_diff||{available:false},null,2))
      +'</pre></details><button id="acsRepairDownload" type="button">تنزيل المقترح JSON</button></div>';
  }
  box.innerHTML=h; box.className='report on';
  if(repair){
    const button=box.querySelector('#acsRepairDownload');
    if(button) button.onclick=()=>dl(new Blob([JSON.stringify(repair.building,null,2)],
      {type:'application/json'}),'ACS-repair-proposal.json');
  }
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

/* ===== لوحة خطأ ظاهرة: تشرح، وتُظهر معرّف الطلب، وتُعيد المحاولة ==========
   قاعدة §11: عند فشل التوليد لا يُحمَّل أي نموذج من رد فاشل، ولا يُترك المشهد
   موهماً بالنجاح. البديل المحلي التقريبي خيار صريح يضغطه المستخدم بنفسه ويُسمّى
   ما هو: تقريبي، لا ناتج المحرّك. */
const ACS_ERR_HINT={
  NOT_CONFIGURED:'عنوان محرّك الفهم غير مضبوط في هذه النسخة من الصفحة.',
  NETWORK_OFFLINE:'الجهاز غير متصل بالإنترنت.',
  NETWORK_DNS:'تعذّر الوصول إلى مضيف الخادم. قد يكون اسم النطاق لا يُترجَم، أو الخدمة متوقّفة، أو أصل الصفحة غير مسموح في CORS.',
  TIMEOUT:'انتهت المهلة قبل أن يردّ الخادم. الطلبات الكبيرة تحتاج وقتاً أطول — قصّر الوصف أو أعِد المحاولة.',
  HTTP_429:'تجاوزت حدّ الطلبات المسموح. انتظر ثم أعِد المحاولة.',
  HTTP_4XX:'رفض الخادم الطلب.',
  HTTP_5XX:'عطل داخلي في الخادم.',
  INVALID_JSON:'رد الخادم ليس JSON صالحاً — هذا عطل في الخادم لا في وصفك.',
  VALID_API_ERROR:'أعلن الخادم فشلاً مصنّفاً.'
};
/* §15 فئات الفشل مفصولة: فشل شبكة شيء، وفشل عرض بعد HTTP 200 شيء آخر تماماً.
   ردّ ناجح ثمّ مشهد أسود لا يجوز أن يُعرض NETWORK_DNS أبداً — ذلك يرسل المستخدم
   يفحص اتصاله بينما العطل في الكاميرا أو المعالجة اللاحقة. */
const ACS_FAIL={
  API_NETWORK_ERROR:'API_NETWORK_ERROR', API_HTTP_ERROR:'API_HTTP_ERROR',
  MODEL_PARSE_ERROR:'MODEL_PARSE_ERROR', MODEL_VALIDATION_ERROR:'MODEL_VALIDATION_ERROR',
  MODEL_LOAD_ERROR:'MODEL_LOAD_ERROR',
  /* KI-26/F-46 — «حُمِّل النموذج وسقط منه جزء». ليس MODEL_LOAD_ERROR: النموذج
     وصل وبُني وعُرض فعلاً، لكن تخصّصاً كاملاً سقط أو حدَّ تعقيدٍ قصّ محتوى.
     الخلط بينهما كذبتان: إعلانُ فشلٍ تامّ على مبنًى معروض، أو إعلانُ نجاحٍ
     تامّ على مبنًى ناقص. هذه الفئة هي المنزلة بينهما. */
  MODEL_DEGRADED_RENDER:'MODEL_DEGRADED_RENDER',
  RENDER_CAMERA_ERROR:'RENDER_CAMERA_ERROR',
  RENDER_POSTPROCESS_ERROR:'RENDER_POSTPROCESS_ERROR',
  RENDER_BLACK_VIEWPORT:'RENDER_BLACK_VIEWPORT'};
const ACS_TRANSPORT_CLASSES=['NETWORK_DNS','NETWORK_OFFLINE','TIMEOUT','NOT_CONFIGURED',
  'HTTP_4XX','HTTP_429','HTTP_5XX','INVALID_JSON','VALID_API_ERROR','SUCCESS'];
let ACS_LAST_FAILURE=null;
function acsFail(cls,detail){
  ACS_LAST_FAILURE={class:cls,detail:String(detail||'').slice(0,180),
    phase:(cls.indexOf('RENDER_')===0)?'RENDER'
      :(cls.indexOf('MODEL_')===0)?'MODEL':'API'};
  return ACS_LAST_FAILURE; }
/* ═══════════ KI-25/F-44 · حاجز تطبيق ما بعد 200 ═══════════════════════════
   العطل الذي يغلقه هذا الحاجز
   ---------------------------
   كان بين «الخادم أجاب 200 بنموذج صالح» و«المستخدم يرى مبنى» ستّ خطوات بلا
   حارس واحد:

       setModel(data.building);
       SRV_OK=true; srvPill('ok','✓ محرّك الفهم متصل');

   لا try/catch، ولا سؤال واحد عمّا إذا كان النموذج قد وصل المشهد فعلاً. فكان
   للفشل بعد 200 وجهان، وكلاهما مسكوت عنه:

     · **استثناء** داخل compile — غرفةٌ بلا rect مثلاً — يصعد من دالّة async
       فيصير رفضاً غير ملتقَط. لا لوحة خطأ، ولا زرّ إعادة، وشريط الحالة يبقى
       إلى الأبد على «🤖 محرّك الفهم يقرأ وصفك…». المستخدم ينتظر ما لن يأتي.
     · **لا استثناء إطلاقاً** — وهو ما وقع فعلاً في KI-25: مستوىً بلا `index`
       يبني ألفي شبكة عند إحداثيّة NaN. عقدُ الحدود يستبعدها بحقّ (لأنها
       تالفة)، والعدّاد يعدّها، فتُكتب «تم التوليد ✓ 2001 عنصر» فوق نافذة
       فارغة. **نجاحٌ مُعلَن على لا شيء.**

   ما يفعله الحاجز
   ---------------
   لا يُعلَن نجاح قبل أن تثبت أربع حقائق بالقياس لا بالافتراض:
     ١ · setModel رجع بلا استثناء.
     ٢ · ما بُني هو ما أُعطي: لا غرف مرفوضة، ولا هندسة غير منتهية، ولا مناطق
         سقطت بين البيان والمشهد.
     ٣ · الكاميرا محدودة وحدود المشهد صالحة والنموذج داخل الهرم.
     ٤ · إطارٌ حقيقيّ واحد رُسم على الأقلّ، وبكسلاته ليست خلفيّةً موحّدة.

   وإخفاق أيٍّ منها يُصنَّف بدقّة — MODEL_LOAD_ERROR أو RENDER_CAMERA_ERROR أو
   RENDER_BLACK_VIEWPORT — ويُعرَض بلوحة فيها زرّ إعادة. لا يُنسَب أبداً إلى
   الشبكة ولا إلى الخادم: الخادم أجاب 200 وأجاب صحيحاً، والعطل عندنا.
   ═══════════════════════════════════════════════════════════════════════ */
const ACS_APPLY_CONTRACT='acs.apply-boundary/1.0.0';
/* حصّة الهندسة التي إن سقطت صار المعروض شيئاً آخر غير المطلوب. ليست صفراً:
   عنصرٌ شاذّ واحد يُستبعَد من الحدود سلوكٌ سليم قائم منذ KI-3. */
const ACS_APPLY_MIN_KEPT=0.90;
let ACS_LAST_APPLY=null;
let ACS_APPLY_SEQ=0;
/* KI-25/F-45 · عدّاد الأجيال: ردٌّ قديم لا يكتب فوق نموذج أحدث منه. زرّ
   «إعادة المحاولة» في لوحة الخطأ لم يكن يمرّ بقفل الزرّ الرئيس، فثلاث نقرات
   تعني ثلاثة نداءات متزامنة، والفائز هو آخر الواصلين لا آخر المطلوبين. */
function acsApplyTicket(){ ACS_APPLY_SEQ+=1; return ACS_APPLY_SEQ; }

function _acsZonesAsked(b){
  let n=0;
  const floors=(b||{}).floors||{};
  const levels=Array.isArray((b||{}).levels)?(b||{}).levels:[];
  if(levels.length){
    levels.forEach(l=>{ const f=floors[(l||{}).template];
      n+=(((f||{}).rooms)||[]).length; });
    return n;
  }
  for(const k in floors) n+=((floors[k]||{}).rooms||[]).length;
  return n;
}

function acsApplyBuilding(building, opts){
  opts=opts||{};
  const steps=[];
  const mark=s=>{ steps.push(s); return s; };
  const out={contract:ACS_APPLY_CONTRACT, ok:false, class:null, reached:null,
    steps:steps, error:null, at:null, defects:null, scene:null,
    zones_asked:_acsZonesAsked(building), stale:false};
  mark('RESPONSE_RECEIVED');

  /* ١ · جيل الطلب: ردٌّ سبقه ردٌّ أحدث لا يُطبَّق ولا يُعدّ فشلاً. */
  if(opts.seq!==undefined&&opts.seq!==ACS_APPLY_SEQ){
    out.stale=true; out.class='STALE_RESPONSE_IGNORED';
    out.reached=mark('STALE_IGNORED'); ACS_LAST_APPLY=out; return out;
  }
  mark('BUILDING_ACCEPTED');

  /* ٢ · التطبيق. setModel يبني الجديد قبل هدم القديم (F-43)، فاستثناءٌ هنا
        يترك المشهد السابق سليماً — تراجعٌ معرَّف لا حالة نصفيّة. */
  try{
    setModel(building);
    out.reached=mark('SET_MODEL_COMPLETE');
  }catch(e){
    out.class=ACS_FAIL.MODEL_LOAD_ERROR;
    out.reached=mark('SET_MODEL_THREW');
    out.error=String((e&&e.message)||e).slice(0,200);
    out.at=_acsErrorSite(e);
    out.stack=_acsStackHead(e);
    ACS_LAST_APPLY=out; return out;
  }

  /* ٣ · هل بُني ما أُعطي؟ */
  let dfx=null;
  try{ dfx=acsBuildDefects(); }catch(e){ dfx=null; }
  out.defects=dfx?{non_finite_box:dfx.non_finite_box,
    rejected_room:dfx.rejected_room, rejected_field:dfx.rejected_field,
    derived_level_index:dfx.derived_level_index,
    unknown_object:dfx.unknown_object,
    reasons:dfx.reasons, samples:(dfx.samples||[]).slice(0,8)}:null;

  /* KI-26/F-46 · خلاصة المترجم: سقوط تخصّص أو قرار تدهور تعقيد.
     كان الحاجز يسأل «هل رُفضت غرفة؟ هل هندسةٌ غير منتهية؟» فقط، فمبنًى بُني
     بلا فراغات نوى إطلاقاً (ARCH سقط) أو بلا نصف رفوفه (حدّ تعقيد) كان يمرّ
     إلى «تم التوليد ✓» بلا كلمة. */
  let sum=null;
  try{ sum=acsCompileSummary(); }catch(e){ sum=null; }
  out.summary=sum;

  let v=null;
  try{ v=window.ACS.verifyVisibleModel(); }catch(e){ v=null; }
  out.scene=v?{canonical_meshes:v.canonical_meshes,
    included_in_bounds:v.included_in_bounds,
    excluded_invalid_bounds:v.excluded_invalid_bounds,
    bounds_valid:v.bounds_valid, scene_radius:v.scene_radius,
    camera_in_frustum:v.camera_in_frustum, clip_valid:v.clip_valid,
    camera_near:v.camera_near, camera_far:v.camera_far,
    draw_calls:v.draw_calls, webgl_context_ok:v.webgl_context_ok}:null;

  const built=(v&&v.canonical_meshes)||0;
  const kept=(v&&v.included_in_bounds)||0;
  if(built>0&&kept/built<ACS_APPLY_MIN_KEPT){
    out.class=ACS_FAIL.MODEL_LOAD_ERROR;
    out.reached=mark('GEOMETRY_LOST');
    out.error='بُنيت '+built+' شبكة ولم تصل الحدود إلّا '+kept
      +' — الهندسة المعروضة ليست الهندسة المطلوبة.';
    ACS_LAST_APPLY=out; return out;
  }
  if(dfx&&(dfx.rejected_room>0||dfx.non_finite_box>0)){
    out.class=ACS_FAIL.MODEL_LOAD_ERROR;
    out.reached=mark('MODEL_ELEMENTS_REJECTED');
    out.error='رُفض من النموذج: '+dfx.rejected_room+' غرفة و'
      +dfx.non_finite_box+' عنصراً بإحداثيّات غير صالحة.';
    ACS_LAST_APPLY=out; return out;
  }
  if(built===0&&out.zones_asked>0){
    out.class=ACS_FAIL.MODEL_LOAD_ERROR;
    out.reached=mark('NO_GEOMETRY_BUILT');
    out.error='الرد يحمل '+out.zones_asked+' منطقة ولم تُبنَ منها هندسة.';
    ACS_LAST_APPLY=out; return out;
  }
  mark('GEOMETRY_VERIFIED');

  /* ٤ · الكاميرا: محدودة، وحدودها صالحة، والنموذج داخل هرم الرؤية. */
  const camOk=!!(v&&v.bounds_valid&&v.clip_valid
    &&_acsFin(v.camera_near)!==null&&_acsFin(v.camera_far)!==null
    &&_acsFin(v.scene_radius)!==null);
  if(!camOk||(v&&v.camera_in_frustum===false)){
    out.class=ACS_FAIL.RENDER_CAMERA_ERROR;
    out.reached=mark('CAMERA_FIT_FAILED');
    out.error='تعذّرت مصالحة الكاميرا مع حدود النموذج'
      +(v&&v.camera_in_frustum===false?' (النموذج خارج هرم الرؤية).':'.');
    ACS_LAST_APPLY=out; return out;
  }
  out.reached=mark('CAMERA_FIT_COMPLETE');

  /* ٥ · هل المعروض هو المطلوب كاملاً؟ التخصّص الساقط والتعقيد المقصوص لا
        يمنعان العرض — النموذج على الشاشة — لكنّهما يمنعان **ادّعاء اكتماله**.
        ولهذا تُصنَّف الحالة MODEL_DEGRADED_RENDER لا MODEL_LOAD_ERROR. */
  out.degraded=!!(sum&&sum.degraded);
  out.degradation=out.degraded?{
    specialization_failures:sum.specialization_failures,
    complexity_degradations:sum.complexity_degradations,
    capped_expansions:sum.capped_expansions,
    suppressed_meshes:sum.suppressed_meshes,
    reasons:(sum.degradation_reasons||[]).slice(0,12)}:null;
  if(out.degraded) mark('COMPLEXITY_DEGRADED');

  /* ٦ · الإطار الحقيقيّ يُقاس بعد الرسم لا الآن. النجاح مؤقّت حتى يعود
        acsApplyFirstFrame بجواب البكسلات. */
  out.ok=true;
  out.class=out.degraded?ACS_FAIL.MODEL_DEGRADED_RENDER:null;
  out.reached=mark('AWAITING_FIRST_FRAME');
  ACS_LAST_APPLY=out; return out;
}

/* الشطر الثاني من الحاجز: يُستدعى بعد إطارين حقيقيّين. لا يدّعي نجاحاً قبل
   أن تكون النافذة قد رسمت شيئاً غير خلفيّتها. */
function acsApplyFirstFrame(res){
  if(!res||!res.ok) return res;
  let blank=null, probe=null;
  try{ const b=window.ACS.viewportBlank(); blank=b.blank; probe=b.probe; }
  catch(e){ blank=null; }
  res.pixel_probe=probe?{method:probe.method,non_zero_pct:probe.non_zero_pct,
    max_luminance:probe.max_luminance,reason:probe.reason}:null;
  res.steps.push('FIRST_FRAME_MEASURED');
  if(blank===true){
    res.ok=false; res.class=ACS_FAIL.RENDER_BLACK_VIEWPORT;
    res.reached='VIEWPORT_EMPTY';
    res.error='بُني النموذج وضُبطت الكاميرا، ولم تُرسَم النافذة.';
  }else if(blank===null){
    /* لا سياق بكسلات (عتاد غير متاح): يُعلَن NOT VERIFIED ولا يُدّعى نجاح
       ولا يُدّعى فشل. الادّعاء بلا قياس هو ما أوقعنا في KI-25. */
    res.reached='FIRST_FRAME_NOT_VERIFIED';
    res.pixels_verified=false;
  }else{
    /* KI-26/F-46: مرسومةٌ نعم، كاملةٌ لا. لا يُكتب VISIBLE على مبنًى ناقص. */
    res.reached=res.degraded?'VISIBLE_DEGRADED':'VISIBLE';
    res.pixels_verified=true;
  }
  ACS_LAST_APPLY=res; return res;
}

function _acsErrorSite(e){
  const s=String((e&&e.stack)||'');
  const m=s.match(/((?:https?:\/\/|\/)[^\s()]+?\.js):(\d+):(\d+)/);
  return m?(m[1].split('/').slice(-2).join('/')+':'+m[2]+':'+m[3]):null;
}
function _acsStackHead(e){
  return String((e&&e.stack)||'').split('\n').slice(0,4)
    .map(l=>l.trim()).join(' | ').slice(0,320);
}

/* تلميح إضافي حسب رمز الخادم — يشرح ما يفعله المستخدم، لا ما يعنيه الرمز تقنياً */
const ACS_CODE_HINT={
  ACS_UPSTREAM_TRUNCATED:'الطلب أنتج نموذجاً أكبر من حدّ التوليد في نداء واحد. '
    +'أعِد المحاولة (يُعاد التوليد على مراحل تلقائياً)، أو قلّل التفاصيل المطلوبة.',
  ACS_UPSTREAM_TRAILING_JSON:'ردّ المحرّك جاء بأكثر من كائن واحد؛ لن نخمّن أيّهما النموذج.',
  ACS_UPSTREAM_RATE_LIMIT:'المحرّك مشغول — انتظر قليلاً ثم أعِد المحاولة.',
  ACS_UPSTREAM_NOT_CONFIGURED:'الخادم يعمل لكن بلا مفتاح محرّك — راجع إعدادات النشر.'
};
__ACS_SHARED.acsErrorPanel = function acsErrorPanel(res, onRetry, onLocal){
  const box=document.getElementById('reportBox'); if(!box) return;
  const rid=res.request_id||'';
  const code=res.code||res.status||'';
  const wait=res.retry_after?(' — أعِد المحاولة بعد '+res.retry_after+' ثانية'):'';
  box.className='report open';
  box.innerHTML=
    '<div class="acs-errbox">'
    +'<div class="acs-errtitle">✕ لم يُنفَّذ التوليد على الخادم</div>'
    +'<div>'+esc(res.message||'')+'</div>'
    +'<div class="acs-errbody">'
      +esc(ACS_CODE_HINT[res.code]||ACS_ERR_HINT[res.status]||'')+esc(wait)+'</div>'
    +'<div class="acs-errhint">'
      +'التصنيف: <code>'+esc(code)+'</code>'
      +(res.http?(' · HTTP '+esc(String(res.http))):'')
      +' · الخادم: <code>'+esc(window.ACS_API.host()||'—')+'</code>'
      +(rid?(' · معرّف الطلب: <code id="acsReqId">'+esc(rid)+'</code>'):'')
    +'</div>'
    +'<div class="acs-errrow">'
      +'<button id="acsRetryBtn" type="button">إعادة المحاولة</button>'
      +'<button id="acsLocalBtn" type="button">توليد محلي تقريبي (ليس ناتج المحرّك)</button>'
    +'</div></div>';
  const rb=document.getElementById('acsRetryBtn'); if(rb) rb.onclick=onRetry;
  const lb=document.getElementById('acsLocalBtn'); if(lb) lb.onclick=onLocal;
};

/* KI-25/F-44 · لوحة عطل ما بعد 200 — منفصلة عمداً عن لوحة عطل الخادم.
   الخلط بينهما هو الكذبة التي يمنعها هذا الفصل: «لم يُنفَّذ التوليد على
   الخادم» جملةٌ خاطئة تماماً حين يكون الخادم قد نفّذ وأجاب 200 ونجح، وعطبُنا
   نحن في العرض. المستخدم الذي يقرأ الأولى يتّهم الشبكة ويعيد المحاولة إلى ما
   لا نهاية؛ والذي يقرأ الثانية يعرف أن نموذجه موجود ومحفوظ. */
__ACS_SHARED.acsApplyErrorPanel = function acsApplyErrorPanel(ap, res, onRetry, onLocal){
  const box=document.getElementById('reportBox'); if(!box) return;
  const rid=(res||{}).request_id||'';
  const d=ap.defects||{}; const s=ap.scene||{};
  const deg=ap.degradation||null;
  const bits=[];
  if(deg){
    if(deg.specialization_failures) bits.push(deg.specialization_failures
      +' تخصّصاً سقط كاملاً');
    if(deg.complexity_degradations) bits.push(deg.complexity_degradations
      +' قرار تدهور تعقيد');
    if(deg.capped_expansions) bits.push(deg.capped_expansions+' توسّعاً مقصوصاً');
    if(deg.suppressed_meshes) bits.push(deg.suppressed_meshes+' عنصراً مكبوتاً');
    if((deg.reasons||[]).length) bits.push('الأسباب: '+deg.reasons.join(' · '));
  }
  if(d.rejected_room) bits.push(d.rejected_room+' غرفة مرفوضة');
  if(d.non_finite_box) bits.push(d.non_finite_box+' عنصراً بإحداثيّات غير صالحة');
  if(d.derived_level_index) bits.push(d.derived_level_index+' دوراً بلا رقم');
  if(d.rejected_field) bits.push(d.rejected_field+' حقلاً بشكل غير متوقّع');
  if(s.canonical_meshes!=null) bits.push('بُني '+s.canonical_meshes
    +' عنصراً، وصل الحدود '+s.included_in_bounds);
  box.className='report open';
  /* KI-26/F-46 · العنوان يتبع الحقيقة: مبنًى معروضٌ ناقص ليس مبنًى لم يُعرَض.
     لوحةٌ تقول «لم يُعرَض» فوق مشهدٍ ظاهر تُفقد المستخدمَ الثقةَ في اللوحة
     كلّها، فيتجاهل التحذير الحقيقي: أن جزءاً من مبناه ليس أمامه. */
  const _degTitle=(ap.degraded===true&&ap.ok!==false);
  box.innerHTML=
    '<div class="acs-errbox">'
    +'<div class="acs-errtitle">'
      +(_degTitle?'⚠ عُرض النموذج ناقصاً — سقط منه جزء'
                 :'✕ وصل النموذج من الخادم ولم يُعرَض')+'</div>'
    +'<div>'+esc(ap.error||(_degTitle?('لم يُبنَ كل ما في النموذج: '
      +((ap.degradation||{}).reasons||[]).join(' · ')):''))+'</div>'
    +'<div class="acs-errbody">'
      +(_degTitle
        ?('الخادم نفّذ التوليد وأجاب بنجاح، والنموذج مبنيّ ومعروض — لكن جزءاً '
          +'منه لم يُبنَ (تخصّصٌ سقط أو حدُّ تعقيدٍ قصّ محتوى). ما تراه ليس '
          +'كامل النموذج. عقد الحدود: <code>'
          +esc(((ap.summary||{}).contract)||'')+'</code>.')
        :('الخادم نفّذ التوليد وأجاب بنجاح — العطل في تحميل النموذج داخل '
          +'المتصفّح، لا في الشبكة ولا في المحرّك. النموذج محفوظ ويمكن تنزيله '
          +'للفحص عبر <code>ACS.captureRenderFailure()</code>.'))+'</div>'
    +'<div class="acs-errhint">'
      +'التصنيف: <code>'+esc(ap.class||'')+'</code>'
      +' · توقّف عند: <code>'+esc(ap.reached||'')+'</code>'
      +(ap.at?(' · <code>'+esc(ap.at)+'</code>'):'')
      +(rid?(' · معرّف الطلب: <code id="acsReqId">'+esc(rid)+'</code>'):'')
      +(bits.length?('<br>'+esc(bits.join(' · '))):'')
    +'</div>'
    +'<div class="acs-errrow">'
      +'<button id="acsRetryBtn" type="button">إعادة التوليد</button>'
      +'<button id="acsLocalBtn" type="button">توليد محلي تقريبي (ليس ناتج المحرّك)</button>'
    +'</div></div>';
  const rb=document.getElementById('acsRetryBtn'); if(rb) rb.onclick=onRetry;
  const lb=document.getElementById('acsLocalBtn'); if(lb) lb.onclick=onLocal;
};

async function acsGenerateFromServer(){
  const txt=document.getElementById('descText').value.trim();
  if(!txt){statusEl.textContent='اكتب وصفاً أولاً.';return;}
  const W=+document.getElementById('siteW').value||30,D=+document.getElementById('siteD').value||25,
        nF=+document.getElementById('nFloors').value||3;
  const localOnDemand=()=>{
    statusEl.textContent='⚠ نموذج محلي تقريبي — ليس ناتج محرّك الفهم.';
    try{ setModel(buildLocal(txt,W,D,nF)); }catch(e){ statusEl.textContent='خطأ: '+e.message; }
  };
  /* KI-25/F-45 · تذكرة الجيل تُسحب قبل النداء. أي نداء يبدأ بعدها يُبطلها،
     فردُّ النداء الأقدم يصل ويُهمَل بدل أن يكتب فوق نموذج أحدث منه. */
  const _seq=acsApplyTicket();
  const big=txt.length>2200||(txt.match(/(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+/g)||[]).length>=12;
  statusEl.textContent='🤖 محرّك الفهم يقرأ وصفك بنداً بنداً ويبني المبنى'
    +(big?' — طلبك كبير، يُبنى على مرحلتين وقد يأخذ عدّة دقائق…':'… لحظات.');
  document.getElementById('reportBox').className='report';

  const res=await __ACS_SHARED.acsFetchJSON('/v1/understand',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt,
      btype:((document.getElementById('bType')||{}).value||'auto'),
      strict:!!(document.getElementById('strictMode')||{}).checked,
      site_w:(+document.getElementById('siteW').value||null),
      site_d:(+document.getElementById('siteD').value||null),
      floors:(+document.getElementById('nFloors').value||null)})}, 900000);

  if(res.status!==ACS_NET.SUCCESS){
    /* لا setModel هنا إطلاقاً: نموذج من رد فاشل ادّعاءُ نجاح. */
    SRV_OK=false;
    srvPill('bad','محرّك الفهم لم يستجب — '+esc(res.status));
    statusEl.textContent='✕ فشل التوليد على الخادم ('+res.status+')'
      +(res.request_id?(' · معرّف الطلب '+res.request_id):'');
    __ACS_SHARED.acsErrorPanel(res, acsGenerateFromServer, localOnDemand);
    acsFail((res.status==='HTTP_4XX'||res.status==='HTTP_5XX'
             ||res.status==='HTTP_429'||res.status==='VALID_API_ERROR')
            ?ACS_FAIL.API_HTTP_ERROR:ACS_FAIL.API_NETWORK_ERROR, res.status);
    console.error('[ACS-API]', res.status, res.code||'', res.request_id||'', res.message);
    return;
  }
  const data=res.body||{};
  if(!data.building){                 /* 200 بلا نموذج = فشل، لا نجاح صامت */
    __ACS_SHARED.acsErrorPanel({status:ACS_NET.INVALID_JSON, http:res.http, request_id:res.request_id,
      message:'ردّ الخادم بنجاح لكن بلا حقل building.'}, acsGenerateFromServer, localOnDemand);
    acsFail(ACS_FAIL.MODEL_VALIDATION_ERROR,'200 without a building field');
    statusEl.textContent='✕ رد غير مكتمل من الخادم.';
    return;
  }
  /* KI-25/F-44: التطبيق يمرّ بالحاجز. الخادم أجاب 200 وأجاب صحيحاً — وما
     يفشل بعد هذه النقطة عطلٌ عندنا، يُصنَّف ويُعرَض ولا يُنسَب إلى الشبكة. */
  const ap=acsApplyBuilding(data.building,{seq:_seq});
  if(ap.stale){
    console.warn('[ACS-APPLY] رد أقدم من الطلب الحالي — أُهمل بلا تطبيق.');
    return;
  }
  if(!ap.ok){
    SRV_OK=true;                       /* الخادم سليم: لا تُطفَأ شارته بعطلنا */
    srvPill('ok','✓ محرّك الفهم متصل');
    acsFail(ap.class, ap.reached+(ap.at?(' @'+ap.at):''));
    statusEl.textContent='✕ وصل النموذج من الخادم ولم يُعرَض — '+ap.class;
    __ACS_SHARED.acsApplyErrorPanel(ap, res, acsGenerateFromServer, localOnDemand);
    console.error('[ACS-APPLY]', ap.class, ap.reached, ap.at||'', ap.error||'',
                  ap.stack||'');
    return;
  }
  SRV_OK=true; srvPill('ok','✓ محرّك الفهم متصل');
  __ACS_SHARED.LAST_REQUEST_TEXT = txt;            // نص العميل الأصلي مرجع التحقّق
  showReport(data.report, txt);       // يُصنَّف حسب المصدر ولا يُرفَع بلا إثبات
  const n=((data.report||{}).requirements||[]).length;
  /* «جارٍ العرض» لا «تمّ»: النجاح لا يُعلَن قبل قياس إطار حقيقيّ. */
  statusEl.textContent='… النموذج مبنيّ — يُنتظَر أوّل إطار مرسوم';
  const _finish=()=>{
    const fr=acsApplyFirstFrame(ap);
    if(!fr.ok){
      acsFail(fr.class, fr.reached);
      statusEl.textContent='✕ بُني النموذج ولم تُرسَم النافذة — '+fr.class;
      __ACS_SHARED.acsApplyErrorPanel(fr, res, acsGenerateFromServer, localOnDemand);
      console.error('[ACS-APPLY]', fr.class, fr.reached, fr.error||'');
      return;
    }
    /* KI-26/F-46: «بُني من وصفك» جملةُ اكتمال. لا تُكتب فوق مبنًى سقط منه
       تخصّصٌ أو قُصّ منه محتوى — يُقال الناقصُ ناقصاً، وتُفتَح لوحة التفصيل. */
    if(fr.degraded){
      acsFail(ACS_FAIL.MODEL_DEGRADED_RENDER,
              ((fr.degradation||{}).reasons||[]).join(',').slice(0,120));
      statusEl.textContent='⚠ عُرض النموذج ناقصاً — لم يُبنَ كل ما في وصفك ('
        +((fr.degradation||{}).reasons||[]).join(' · ')+')';
      __ACS_SHARED.acsApplyErrorPanel(fr, res, acsGenerateFromServer, localOnDemand);
      console.warn('[ACS-APPLY]', ACS_FAIL.MODEL_DEGRADED_RENDER, fr.degradation);
      return;
    }
    statusEl.textContent='✓ بُني من وصفك — '+(data.rooms||'?')+' منطقة · '+(data.levels||'?')+' مستوى'
      +(n?(' · نُفِّذ '+n+' بنداً من طلبك'):'')
      +((data.mode==='deep')?' · (توليد على مرحلتين)':'')
      +(fr.pixels_verified===false?' · (تعذّر قياس البكسلات في هذا العتاد)':'');
  };
  if(typeof requestAnimationFrame==='function')
    requestAnimationFrame(()=>requestAnimationFrame(_finish));
  else _finish();
}
document.getElementById('genLLM').onclick=acsGenerateFromServer;
document.getElementById('loadExample').onclick=()=>{setModel(EXAMPLE);};
document.getElementById('loadWarehouse').onclick=()=>{
  statusEl.textContent='بناء مستودع تجارة إلكترونية 120×80 م…';
  setTimeout(()=>setModel(warehouseModel(120,80,{clear:12})),20);
};

/* لوحة الجوال: زر إظهار/إخفاء */
(function(){
  const t=document.getElementById('panelToggle'), p=document.getElementById('left');
  t.onclick=()=>{ p.classList.toggle('open'); t.textContent=p.classList.contains('open')?'✕':'☰'; };
  // أغلق اللوحة تلقائياً بعد التوليد على الجوال
  window.ACS=window.ACS||{};
  /* ===== تشخيص الواجهة ↔ الخادم — قراءة فقط، بلا أي نداء شبكة =====
     يجيب سؤالاً واحداً بعد أي عطل: أيّ عنوان استُعمل فعلاً، من أين جاء، وكيف
     صُنِّف آخر نداء. لا يُصدِر طلباً ولا يغيّر حالة، ولا يكشف أي سرّ. */
  /* آخر فشل مصنَّف — قراءة فقط. يفصل فشل الشبكة عن فشل العرض صراحةً. */
  window.ACS.lastFailure=()=>ACS_LAST_FAILURE?
    {class:ACS_LAST_FAILURE.class,phase:ACS_LAST_FAILURE.phase,
     detail:ACS_LAST_FAILURE.detail,
     is_transport:ACS_TRANSPORT_CLASSES.indexOf(ACS_LAST_FAILURE.class)>=0}:null;
  window.ACS.failureClasses=()=>Object.keys(ACS_FAIL).map(k=>ACS_FAIL[k]);
  /* KI-26/F-46 · عقد حدود التعقيد معروضٌ للقراءة: أي قصٍّ في المشهد يمكن
     مطابقته بالحدّ الذي سبّبه، بلا قراءة الشيفرة. */
  window.ACS.sceneLimits=()=>Object.assign({},SCENE_LIMITS);
  window.ACS.compileSummary=()=>acsCompileSummary();
  window.ACS.apiDiagnostics=()=>({
    contract:(window.ACS_API||{}).contract||'',
    base:(window.ACS_API&&window.ACS_API.base())||'',
    host:(window.ACS_API&&window.ACS_API.host())||'',
    scheme:(window.ACS_API&&window.ACS_API.scheme())||'',
    source:(window.ACS_API&&window.ACS_API.source())||'',
    configured:(window.ACS_API||{}).configured||'',
    override_present:!!((window.ACS_API||{}).override||''),
    page_origin:(location&&location.origin)||'',
    online:(typeof navigator!=='undefined')?navigator.onLine!==false:null,
    server_ok:SRV_OK,
    classes:Object.keys(ACS_NET).map(k=>ACS_NET[k]),
    last_call:ACS_LAST_CALL?{status:ACS_LAST_CALL.status,code:ACS_LAST_CALL.code||'',
      http:ACS_LAST_CALL.http,path:ACS_LAST_CALL.path,ms:ACS_LAST_CALL.ms,
      request_id:ACS_LAST_CALL.request_id||'',retryable:!!ACS_LAST_CALL.retryable}:null
  });
  /* مفتّش علاقات للمطوّر فقط (Console): ACS.relationships() / ACS.relationshipIssues() */
  window.ACS.relationships=()=>lastBuilding?buildRelationships(lastBuilding,'bld_0'):[];
  window.ACS.relationshipSummary=()=>relationshipSummary(window.ACS.relationships());
  window.ACS.relationshipIssues=()=>lastBuilding?validateRelationships(
      buildRelationships(lastBuilding,'bld_0'),lastBuilding,'bld_0'):[];
  window.ACS.spaceLinks=(sid)=>window.ACS.relationships().filter(e=>e.from===sid||e.to===sid);
  /* التنقّل — للمطوّر فقط (Console) */
  window.ACS.navigationGraph=()=>lastBuilding?buildNavGraph(lastBuilding,window.ACS.relationships(),'bld_0'):null;
  window.ACS.findPath=(a,b,opt)=>lastBuilding?findPath(lastBuilding,window.ACS.relationships(),a,b,'bld_0',!!(opt&&opt.includeUnresolved)):null;
  window.ACS.pathSummary=(a,b)=>pathSummary(window.ACS.findPath(a,b));
  window.ACS.navigationIssues=()=>lastBuilding?navIssues(lastBuilding,window.ACS.relationships(),'bld_0'):null;
  /* المخارج والإخلاء — للمطوّر فقط (Console) */
  window.ACS.exits=()=>lastBuilding?extractExits(lastBuilding,window.ACS.relationships(),'bld_0'):[];
  window.ACS.findEgress=(sid)=>lastBuilding?findEgress(lastBuilding,window.ACS.relationships(),sid,'bld_0'):null;
  window.ACS.egressCandidates=(sid)=>{const r=window.ACS.findEgress(sid);
    return r&&r.status==='FOUND'?[{exit_id:r.exit.id,hops:r.route.hops,primary:true}].concat(r.alternative_exits):[];};
  window.ACS.egressAudit=()=>lastBuilding?auditEgress(lastBuilding,window.ACS.relationships(),'bld_0'):null;
  window.ACS.egressIssues=()=>lastBuilding?validateExits(lastBuilding,window.ACS.exits(),'bld_0'):[];
  window.ACS.egressSummary=(sid)=>egressSummary(window.ACS.findEgress(sid));
  /* قياس المسافة الهندسية — للمطوّر فقط (Console). قياس فقط، بلا أي حكم مطابقة */
  window.ACS.measurePath=(a,b,opt)=>{ if(!lastBuilding) return null;
    const p=window.ACS.findPath(a,b,opt); if(!p) return null;
    return measurePath(lastBuilding,p,'bld_0',opt&&opt.origin,opt&&opt.destination); };
  window.ACS.pathGeometry=(a,b,opt)=>{ const m=window.ACS.measurePath(a,b,opt); if(!m) return null;
    return {segments:m.segments,origin_basis:m.origin_basis,units:m.units,
            measurement_basis:m.measurement_basis,unmeasured_segments:m.unmeasured_segments,
            distance_status:m.distance_status,compliance:m.compliance}; };
  window.ACS.measureEgress=(sid)=>{ const r=window.ACS.findEgress(sid);
    return (r&&r.distance_measurement)?r.distance_measurement:null; };
  window.ACS.distanceIssues=(a,b)=>{ if(!lastBuilding) return [];
    if(a&&b) return validateMeasurement(window.ACS.measurePath(a,b)||{});
    const rels=window.ACS.relationships(), issues=[];
    knownSpaces(lastBuilding,'bld_0').forEach(sid=>{
      const r=findEgress(lastBuilding,rels,sid,'bld_0');
      if(!r||r.status!=='FOUND'||!r.distance_measurement) return;
      validateMeasurement(r.distance_measurement).forEach(i=>issues.push('['+sid+'] '+i)); });
    return issues; };
  window.ACS.distanceSummary=(a,b)=>{ const m=window.ACS.measurePath(a,b);
    return m?distanceSummary(m):null; };
  /* محرّك القواعد — للمطوّر فقط (Console). تقييم فقط: لا تعديل ولا إصلاح تلقائي */
  window.ACS.rules=()=>allRules(__ACS_SHARED.ACS_EXTRA_RULESETS).map(p=>({ruleset_id:p[0].ruleset_id,
    rule_id:p[1].rule_id,regulatory:p[1].regulatory===true,standard:p[1].standard,
    edition:p[1].edition,section:p[1].section,operator:p[1].operator,
    subject_type:p[1].subject_type,enabled:p[1].enabled!==false,
    definition_valid:!validateRule(p[1]).length}));
  window.ACS.ruleSources=()=>ruleSources();
  window.ACS.ruleSets=()=>ruleSets();
  window.ACS.ruleSubject=(sid)=>lastBuilding?resolveSubject(lastBuilding,window.ACS.relationships(),sid,'bld_0',
    occupancyIndex(__ACS_SHARED.ACS_OCCUPANCY_STORE,[sid])):null;
  window.ACS.evaluateRule=(ruleId,subjectId,ctx,ruleSetId)=>{ if(!lastBuilding) return null;
    const hits=ruleMatches(ruleId,__ACS_SHARED.ACS_EXTRA_RULESETS)
      .filter(h=>ruleSetId===undefined||ruleSetId===null||h[0].ruleset_id===ruleSetId);
    if(!hits.length) return {rule_id:ruleId,status:'INVALID_RULE_DEFINITION',reason:'RULE_NOT_FOUND'};
    if(hits.length>1) return {rule_id:ruleId,status:'UNSUPPORTED',
      reason:'AMBIGUOUS_RULE_ID — specify ruleset_id ('+hits.map(h=>h[0].ruleset_id).join(', ')+')'};
    return evaluateRule(hits[0][1],window.ACS.ruleSubject(subjectId),ctx||{},hits[0][0],__ACS_SHARED.ACS_EXTRA_RULESETS); };
  window.ACS.evaluateRuleSet=(ruleSetId,subjectIds,ctx)=>{ if(!lastBuilding) return null;
    const subs=(subjectIds||[]).map(window.ACS.ruleSubject).filter(Boolean);
    return evaluateRuleSet(ruleSetId,subs,ctx||{},__ACS_SHARED.ACS_EXTRA_RULESETS); };
  window.ACS.ruleIssues=()=>ruleIssues(__ACS_SHARED.ACS_EXTRA_RULESETS);
  window.ACS.complianceSummary=(ruleSetId,subjectIds,ctx)=>{
    const run=window.ACS.evaluateRuleSet(ruleSetId,subjectIds,ctx);
    return run?aggregateRuleResults(run.results,ruleSetById(ruleSetId,__ACS_SHARED.ACS_EXTRA_RULESETS)):null; };
  window.ACS.regulatoryRuleCount=()=>regulatoryRuleCount(__ACS_SHARED.ACS_EXTRA_RULESETS);
  /* استيراد المصادر والتحقّق من الحزم — للمطوّر فقط (Console). لا تفعيل ضمني */
  window.ACS.ruleDocuments=()=>__ACS_SHARED.ACS_INGEST_STORE.documents.map(d=>({document_id:d.document_id,
    title:d.title,standard:d.standard,edition:d.edition,official:d.official===true,
    synthetic:d.synthetic===true,sha256:(d.integrity||{}).sha256,
    status:(d.verification||{}).status}));
  window.ACS.ruleFragments=(docId)=>(docId?fragmentsOf(__ACS_SHARED.ACS_INGEST_STORE,docId):__ACS_SHARED.ACS_INGEST_STORE.fragments)
    .map(f=>({fragment_id:f.fragment_id,document_id:f.document_id,section:f.section,
              clause:f.clause,kind:f.kind,status:f.status,text_reference:f.text_reference}));
  window.ACS.ruleCandidates=()=>__ACS_SHARED.ACS_INGEST_STORE.candidates.map(c=>({candidate_id:c.candidate_id,
    status:c.status,assessed:assessCandidate(c,__ACS_SHARED.ACS_INGEST_STORE)[0],
    rule_id:(c.proposed_rule||{}).rule_id,regulatory:(c.proposed_rule||{}).regulatory===true,
    ai_assisted:c.ai_assisted===true,document_id:c.document_id,
    verified:!!c.verification,rule_definition_hash:ruleDefinitionHash(c.proposed_rule)}));
  window.ACS.rulePacks=()=>__ACS_SHARED.ACS_INGEST_STORE.rulepacks.map(p=>({rulepack_id:p.rulepack_id,
    version:p.version,status:(p.verification||{}).status,completeness:p.completeness,
    coverage_scope:(p.coverage_scope||[]).slice(),rules:(p.candidate_ids||[]).length,
    regulatory:p.regulatory===true}));
  window.ACS.ruleSourceIssues=()=>ingestStoreIssues(__ACS_SHARED.ACS_INGEST_STORE);
  window.ACS.verifyCandidate=(cid,opts)=>{ const c=ingCandidate(__ACS_SHARED.ACS_INGEST_STORE,cid);
    if(!c) return {ok:false,reason:'CANDIDATE_NOT_FOUND'};
    opts=opts||{};
    const r=verifyCandidate(c,__ACS_SHARED.ACS_INGEST_STORE,opts.verifier,opts.at,opts.method,opts.notes);
    return {ok:r[0],reason:r[1],record:r[2],status:c.status}; };
  window.ACS.verifyRulePack=(pid,version,opts)=>{ const p=ingRulePack(__ACS_SHARED.ACS_INGEST_STORE,pid,version);
    if(!p) return {ok:false,reason:'RULEPACK_NOT_FOUND'};
    opts=opts||{};
    const r=verifyPack(p,__ACS_SHARED.ACS_INGEST_STORE,opts.to,opts.verifier,opts.at,opts.method,opts.notes);
    return {ok:r[0],reason:r[1],status:(p.verification||{}).status}; };
  const _syncActive=()=>{ const a=resolveActiveRules(ACS_PROJECT_CODE_CONTEXT,__ACS_SHARED.ACS_INGEST_STORE);
    __ACS_SHARED.ACS_EXTRA_RULESETS=a.rulesets; return a; };
  window.ACS.projectCodeContext=()=>JSON.parse(JSON.stringify(ACS_PROJECT_CODE_CONTEXT));
  window.ACS.setJurisdiction=(j)=>{ ACS_PROJECT_CODE_CONTEXT.jurisdiction=j||null;
    return window.ACS.projectCodeContext(); };
  window.ACS.activateRulePack=(pid,version,enabled)=>{
    const refs=ACS_PROJECT_CODE_CONTEXT.rulepacks;
    const i=refs.findIndex(r=>r.rulepack_id===pid&&r.version===version);
    const ref={rulepack_id:pid,version:version,enabled:enabled!==false};
    if(i>=0) refs[i]=ref; else refs.push(ref);
    return _syncActive(); };
  window.ACS.deactivateRulePack=(pid,version)=>{
    ACS_PROJECT_CODE_CONTEXT.rulepacks=ACS_PROJECT_CODE_CONTEXT.rulepacks
      .filter(r=>!(r.rulepack_id===pid&&r.version===version));
    return _syncActive(); };
  window.ACS.activeRulePacks=()=>_syncActive();
  window.ACS.rulePackSummary=(subjectIds,ctx)=>{ if(!lastBuilding) return null;
    _syncActive();
    const subs=(subjectIds||[]).map(window.ACS.ruleSubject).filter(Boolean);
    return evaluateProject(ACS_PROJECT_CODE_CONTEXT,subs,__ACS_SHARED.ACS_INGEST_STORE,ctx||{}).summary; };
  window.ACS.ruleAudit=()=>ingestAuditExport(__ACS_SHARED.ACS_INGEST_STORE,ACS_PROJECT_CODE_CONTEXT);
  /* الإشغال النظامي وسياق الكود — للمطوّر فقط (Console). لا تصنيف تلقائي */
  const _occSubjects=()=>{ if(!lastBuilding) return [];
    const ids=['BUILDING:bld_0'];
    knownSpaces(lastBuilding,'bld_0').forEach(sid=>ids.push('SPACE:'+sid));
    (lastBuilding.levels||[]).forEach(l=>ids.push('LEVEL:bld_0.flr_'+(l.index||0)));
    return ids; };
  window.ACS.classificationPacks=()=>occPacks(__ACS_SHARED.ACS_OCCUPANCY_STORE).map(p=>({pack_id:p.pack_id,
    version:p.version,classification_system:p.classification_system,standard:p.standard,
    edition:p.edition,status:(p.verification||{}).status,regulatory:p.regulatory===true,
    synthetic:p.synthetic===true,classifications:(p.classifications||[]).length}));
  window.ACS.verifyClassificationPack=(id,version,opts)=>{ const p=occPack(__ACS_SHARED.ACS_OCCUPANCY_STORE,id,version);
    if(!p) return {ok:false,reason:'CLASSIFICATION_PACK_NOT_FOUND'};
    opts=opts||{};
    const r=verifyOccupancyPack(p,opts.to,opts.verifier,opts.at,opts.method,opts.notes);
    return {ok:r[0],reason:r[1],status:(p.verification||{}).status}; };
  window.ACS.activateClassificationPack=(id,version,enabled)=>{
    const cc=ACS_PROJECT_CODE_CONTEXT.code_context;
    const i=cc.classification_packs.findIndex(r=>r.pack_id===id&&r.version===version);
    const ref={pack_id:id,version:version,enabled:enabled!==false};
    if(i>=0) cc.classification_packs[i]=ref; else cc.classification_packs.push(ref);
    return activeOccupancyPacks(ACS_PROJECT_CODE_CONTEXT,__ACS_SHARED.ACS_OCCUPANCY_STORE); };
  window.ACS.occupancies=()=>exportOccupancy(__ACS_SHARED.ACS_OCCUPANCY_STORE,ACS_PROJECT_CODE_CONTEXT);
  window.ACS.occupancyFor=(sid)=>resolveOccupancy(sid,__ACS_SHARED.ACS_OCCUPANCY_STORE);
  window.ACS.occupancyCandidates=(sid,subjectType)=>{ if(!lastBuilding) return [];
    const prog=(lastBuilding.meta||{}).type;
    const made=suggestOccupancyFromProgram(sid,subjectType||'BUILDING',prog,
      __ACS_SHARED.ACS_OCCUPANCY_STORE,ACS_PROJECT_CODE_CONTEXT,null);
    made.forEach(c=>addOccupancyClassification(__ACS_SHARED.ACS_OCCUPANCY_STORE,c));
    return made.map(c=>({id:c.id,group:c.group,status:c.status,source:c.source})); };
  window.ACS.declareOccupancy=(sid,group,opts)=>{ opts=opts||{};
    const r=declareOccupancy(sid,opts.subject_type||'BUILDING',group,__ACS_SHARED.ACS_OCCUPANCY_STORE,
      ACS_PROJECT_CODE_CONTEXT,opts.subgroup,opts.declared_by,opts.at,opts.note);
    if(r[0]) addOccupancyClassification(__ACS_SHARED.ACS_OCCUPANCY_STORE,r[0]);
    return {ok:!!r[0],reason:r[1],classification:r[0]}; };
  window.ACS.verifyOccupancy=(cid,opts)=>{ const c=occClassification(__ACS_SHARED.ACS_OCCUPANCY_STORE,cid);
    if(!c) return {ok:false,reason:'CLASSIFICATION_NOT_FOUND'};
    opts=opts||{};
    const r=verifyOccupancy(c,__ACS_SHARED.ACS_OCCUPANCY_STORE,ACS_PROJECT_CODE_CONTEXT,opts.verifier,opts.at,
      opts.method,opts.evidence,opts.notes);
    return {ok:r[0],reason:r[1],record:r[2],status:c.status,source:c.source}; };
  window.ACS.occupancyIssues=()=>occupancyIssues(__ACS_SHARED.ACS_OCCUPANCY_STORE,ACS_PROJECT_CODE_CONTEXT);
  window.ACS.occupancyAudit=()=>auditOccupancy(__ACS_SHARED.ACS_OCCUPANCY_STORE,_occSubjects());
  window.ACS.codeContext=()=>JSON.parse(JSON.stringify(ACS_PROJECT_CODE_CONTEXT));
  /* مراجعة النموذج ونزاهة اللقطات — للمطوّر فقط (Console). لا إعادة تقييم صامتة */
  let ACS_SNAPSHOTS=[];
  window.ACS.modelHash=(scope,bid)=>lastBuilding?modelHash(
    (scope==='project')?toProject(JSON.parse(JSON.stringify(lastBuilding))):lastBuilding,
    scope||'building', bid||'bld_0'):null;
  window.ACS.modelRevision=(scope,bid,at)=>lastBuilding?modelRevision(
    (scope==='project')?toProject(JSON.parse(JSON.stringify(lastBuilding))):lastBuilding,
    scope||'building', bid||'bld_0', at===undefined?null:at):null;
  window.ACS.canonicalModel=(scope,bid)=>lastBuilding?((scope==='project')
    ?canonicalProject(toProject(JSON.parse(JSON.stringify(lastBuilding))))
    :canonicalBuilding(lastBuilding,bid||'bld_0')):null;
  window.ACS.snapshotResult=(ruleId,subjectId,opt)=>{ if(!lastBuilding) return null;
    opt=opt||{};
    const hits=ruleMatches(ruleId,__ACS_SHARED.ACS_EXTRA_RULESETS);
    if(!hits.length) return {error:'RULE_NOT_FOUND'};
    const rs=hits[0][0], rule=hits[0][1];
    const subj=window.ACS.ruleSubject(subjectId);
    const result=evaluateRule(rule,subj,opt.ctx||{},rs,__ACS_SHARED.ACS_EXTRA_RULESETS);
    const snap=snapshotResult({result:result,model:lastBuilding,scope:opt.scope||'building',
      building_id:opt.building_id||'bld_0',rule:rule,ruleset:rs,
      occupancy_store:__ACS_SHARED.ACS_OCCUPANCY_STORE,occupancy_subjects:[subjectId],
      project_ctx:ACS_PROJECT_CODE_CONTEXT,ingest_store:__ACS_SHARED.ACS_INGEST_STORE,
      created_at:(opt.at===undefined?null:opt.at)});
    ACS_SNAPSHOTS.push(snap);            // التاريخ يُحفَظ، ولا يُستبدل
    return snap; };
  window.ACS.resultIntegrity=(snap)=>{ if(!lastBuilding) return null;
    const hits=ruleMatches((snap.integrity||{}).rule_id,__ACS_SHARED.ACS_EXTRA_RULESETS);
    return checkResultIntegrity(snap,{model:lastBuilding,
      rule:hits.length?hits[0][1]:null, ruleset:hits.length?hits[0][0]:null,
      occupancy_store:__ACS_SHARED.ACS_OCCUPANCY_STORE, project_ctx:ACS_PROJECT_CODE_CONTEXT,
      ingest_store:__ACS_SHARED.ACS_INGEST_STORE}); };
  window.ACS.snapshots=()=>ACS_SNAPSHOTS.map(exportSnapshot);
  window.ACS.staleResults=()=>{ if(!lastBuilding) return [];
    return staleResults(ACS_SNAPSHOTS,{model:lastBuilding,
      occupancy_store:__ACS_SHARED.ACS_OCCUPANCY_STORE, project_ctx:ACS_PROJECT_CODE_CONTEXT,
      ingest_store:__ACS_SHARED.ACS_INGEST_STORE}); };
  window.ACS.revisionDiff=(otherModel,scope,bid)=>lastBuilding?
    revisionDiff(lastBuilding,otherModel,scope||'building',bid||'bld_0'):null;
  /* الهندسة المعمارية وغلاف المبنى — للمطوّر فقط (Console). عناصر معمارية بحتة:
     لا إنشاء ولا ميكانيكا ولا حريق ولا مطابقة كود، ولا قيمة افتراضية تُقدَّم
     كقيمة هندسية — الاحتياط يظهر دائماً في render_fallback منفصلاً. */
  const _archOf=(bid,pos,rot)=>lastBuilding?
    compileArchitecture(lastBuilding,bid||'bld_0',pos||null,rot||0):null;
  window.ACS.architecture=(bid,pos,rot)=>_archOf(bid,pos,rot);
  window.ACS.archElements=(bid)=>{ const a=_archOf(bid); if(!a) return null;
    const pick=t=>(a[t]||[]).map(e=>({id:e.id,type:e.type||t,level_id:e.level_id||null}));
    return {levels:a.levels.map(l=>({id:l.id,index:l.index,kind:l.kind,
              elevation_m:l.elevation_m,elevation_source:l.elevation_source})),
      spaces:(a.spaces||[]).map(s=>({id:s.id,space_id:s.space_id,level_id:s.level_id,
              area_m2:s.area_m2,boundary_basis:s.boundary_basis})),
      walls:pick('walls'),openings:pick('openings'),slabs:pick('slabs'),voids:pick('voids'),
      ceilings:pick('ceilings'),roofs:pick('roofs'),cores:pick('cores'),
      envelope:a.envelope?a.envelope.id:null,
      summary:archSummary(a)}; };
  window.ACS.walls=(bid)=>{ const a=_archOf(bid); return a?a.walls.map(w=>({id:w.id,
    level_id:w.level_id,axis:w.axis,length_m:w.length_m,start:w.start,end:w.end,
    height_m:w.height_m,thickness_m:w.thickness_m,spaces:w.spaces,shared:w.shared,
    exposure:w.exposure,exposure_status:w.exposure_status,exposure_basis:w.exposure_basis,
    openings:w.openings})):null; };
  window.ACS.openings=(bid)=>{ const a=_archOf(bid); return a?a.openings.slice():null; };
  window.ACS.envelope=(bid)=>{ const a=_archOf(bid); return a?a.envelope:null; };
  window.ACS.geometryIssues=(bid)=>{ const a=_archOf(bid); return a?a.issues.slice():[]; };
  window.ACS.archApproximations=(bid)=>{ const a=_archOf(bid);
    return a?a.approximations.slice():[]; };
  window.ACS.elementById=(id,bid)=>{ const a=_archOf(bid);
    return a?archElementById(a,id):null; };
  window.ACS.sharedWall=(x,y,bid)=>{ const a=_archOf(bid);
    return a?archSharedWallBetween(a,x,y):null; };
  window.ACS.doorEvidence=(openingRef,bid)=>{ const a=_archOf(bid);
    return a?archDoorConnectsConfirmed(a,openingRef):null; };
  window.ACS.archSummary=(bid)=>{ const a=_archOf(bid); return a?archSummary(a):null; };
  /* النموذج الإنشائي — للمطوّر فقط (Console). تمثيل فقط: لا تصميم ولا أحمال ولا
     تحجيم ولا تسليح ولا مطابقة كود، ولا احتياط عرض يُقدَّم كقياس إنشائي. */
  const _structOf=(bid,pos,rot)=>lastBuilding?
    compileStructure(lastBuilding,bid||'bld_0',pos||null,rot||0):null;
  window.ACS.structuralModel=(bid,pos,rot)=>_structOf(bid,pos,rot);
  window.ACS.structuralElements=(bid)=>{ const st=_structOf(bid); if(!st) return null;
    const pick=k=>(st[k]||[]).map(e=>({id:e.id,type:e.type,source:e.source,
      material_ref:e.material_ref===undefined?null:e.material_ref}));
    return {status:st.status,status_basis:st.status_basis,
      columns:pick('columns'),beams:pick('beams'),slabs:pick('slabs'),walls:pick('walls'),
      cores:pick('cores'),foundations:pick('foundations'),nodes:pick('nodes'),
      materials:(st.materials||[]).map(m=>({id:m.id,material:m.material,source:m.source})),
      relationships:(st.relationships||[]).map(r=>({id:r.id,type:r.type,from:r.from,to:r.to,
        status:r.status})),
      summary:structSummary(st)}; };
  window.ACS.structuralGrid=(bid)=>{ const st=_structOf(bid);
    return st?st.grid_systems.map(gs=>({id:gs.id,label:gs.label,origin:gs.origin,
      rotation_deg:gs.rotation_deg,source:gs.source,
      grids:gs.grids.map(g=>({id:g.id,axis:g.axis,label:g.label,position_m:g.position_m,
        source:g.source,world:structGridToWorld(st,gs,g,100)}))})):null; };
  window.ACS.structuralIssues=(bid)=>{ const st=_structOf(bid); return st?st.issues.slice():[]; };
  window.ACS.structuralElement=(id,bid)=>{ const st=_structOf(bid);
    return st?structElementById(st,id):null; };
  window.ACS.structuralSummary=(bid)=>{ const st=_structOf(bid);
    return st?structSummary(st):null; };
  window.ACS.structuralRenderItems=(bid)=>{ const st=_structOf(bid);
    return st?structRenderItems(st):[]; };
  window.ACS.structuralRuleInputs=(bid)=>{ const st=_structOf(bid);
    return st?structRuleInputs(st):{}; };
  /* اقتراح شبكة: مقترح صريح لا يُكتب في النموذج ولا يُعتمد تلقائياً */
  window.ACS.suggestStructuralGrid=(sx,sz,bid)=>lastBuilding?
    suggestStructuralGrid(lastBuilding,sx===undefined?null:sx,sz===undefined?null:sz,
      bid||'bld_0'):null;
  /* إظهار/إخفاء الطبقة الإنشائية — حالة عرض بحتة لا تدخل بصمة المراجعة */
  window.ACS.structuralLayerVisible=(on)=>{ const r=registry&&registry.STRUCT;
    if(!r) return false;
    if(on!==undefined){ r.visible=!!on; r.meshes.forEach(m=>{m.visible=!!on;}); }
    return !!r.visible; };
  /* أنظمة الكهروميكانيك — للمطوّر فقط (Console). تمثيل فقط: لا تصميم ولا حساب
     أحمال/تدفّق/ضغط ولا تحجيم ولا كفاية خدمة ولا مطابقة كود. */
  const _mepOf=(bid,pos,rot)=>lastBuilding?
    compileMep(lastBuilding,bid||'bld_0',pos||null,rot||0):null;
  window.ACS.mepModel=(bid,pos,rot)=>_mepOf(bid,pos,rot);
  window.ACS.mepSystems=(bid)=>{ const m=_mepOf(bid);
    return m?m.systems.map(s=>({id:s.id,system_type:s.system_type,discipline:s.discipline,
      name:s.name,medium:s.medium,source:s.source})):null; };
  window.ACS.mepElements=(bid)=>{ const m=_mepOf(bid); if(!m) return null;
    const pick=k=>(m[k]||[]).map(e=>({id:e.id,type:e.type,system_id:e.system_id,
      source:e.source}));
    return {status:m.status,status_basis:m.status_basis,
      nodes:pick('nodes'),segments:pick('segments'),equipment:pick('equipment'),
      terminals:pick('terminals'),adapted_terminals:pick('adapted_terminals'),
      risers:pick('risers'),penetrations:pick('penetrations'),
      relationships:(m.relationships||[]).map(r=>({id:r.id,type:r.type,from:r.from,to:r.to,
        status:r.status})),
      summary:mepSummary(m)}; };
  window.ACS.mepSystem=(id,bid)=>{ const m=_mepOf(bid); return m?mepSystemById(m,id):null; };
  window.ACS.mepElement=(id,bid)=>{ const m=_mepOf(bid); return m?mepElementById(m,id):null; };
  window.ACS.mepIssues=(bid)=>{ const m=_mepOf(bid); return m?m.issues.slice():[]; };
  window.ACS.mepInterferences=(bid)=>{ const m=_mepOf(bid); return m?mepInterferences(m):[]; };
  window.ACS.mepSummary=(bid)=>{ const m=_mepOf(bid); return m?mepSummary(m):null; };
  window.ACS.mepRenderItems=(bid)=>{ const m=_mepOf(bid); return m?mepRenderItems(m):[]; };
  window.ACS.mepRuleInputs=(bid)=>{ const m=_mepOf(bid); return m?mepRuleInputs(m):{}; };
  /* إظهار/إخفاء طبقة تخصّص — حالة عرض بحتة لا تدخل بصمة المراجعة */
  window.ACS.mepLayerVisible=(disc,on)=>{ const key='MEP_'+String(disc||'').toUpperCase();
    const r=registry&&registry[key];
    if(!r) return false;
    if(on!==undefined){ r.visible=!!on; r.meshes.forEach(x=>{x.visible=!!on;}); }
    return !!r.visible; };
  /* الحريق وسلامة الأرواح — للمطوّر فقط (Console). تمثيل وطوبولوجيا فقط:
     لا تصميم ولا محاكاة ولا تغطية ولا هيدروليك ولا مطابقة كود، والغياب ليس مخالفة. */
  const _flsOf=(bid,pos,rot)=>lastBuilding?
    compileFls(lastBuilding,bid||'bld_0',pos||null,rot||0):null;
  window.ACS.fireLifeSafety=(bid,pos,rot)=>_flsOf(bid,pos,rot);
  window.ACS.flsDevices=(bid)=>{ const f=_flsOf(bid);
    return f?f.devices.map(d=>({id:d.id,device_type:d.device_type,
      category:d.device_category,origin:d.origin,source:d.source,
      original_source:d.original_source===undefined?null:d.original_source,
      space_id:d.space_id,level_id:d.level_id,references:d.mep_element_id})):null; };
  window.ACS.flsSystems=(bid)=>{ const f=_flsOf(bid);
    return f?f.systems.map(s=>({id:s.id,mep_system_id:s.mep_system_id,
      mep_system_type:s.mep_system_type,role:s.role,origin:s.origin,source:s.source})):null; };
  window.ACS.flsZones=(bid)=>{ const f=_flsOf(bid); return f?f.zones.slice():null; };
  window.ACS.flsBarriers=(bid)=>{ const f=_flsOf(bid); return f?f.barriers.slice():null; };
  window.ACS.flsOpenings=(bid)=>{ const f=_flsOf(bid); return f?f.openings.slice():null; };
  window.ACS.flsExits=(bid)=>{ const f=_flsOf(bid); return f?f.exits.slice():null; };
  window.ACS.flsSigns=(bid)=>{ const f=_flsOf(bid); return f?f.signs.slice():null; };
  window.ACS.flsStairs=(bid)=>{ const f=_flsOf(bid); return f?f.stairs.slice():null; };
  window.ACS.flsIssues=(bid)=>{ const f=_flsOf(bid); return f?f.issues.slice():[]; };
  window.ACS.flsAudit=(bid)=>{ const f=_flsOf(bid); return f?flsAudit(f):null; };
  window.ACS.flsSummary=(bid)=>{ const f=_flsOf(bid); return f?flsSummary(f):null; };
  window.ACS.flsElement=(id,bid)=>{ const f=_flsOf(bid); return f?flsElementById(f,id):null; };
  window.ACS.flsRenderItems=(bid)=>{ const f=_flsOf(bid); return f?flsRenderItems(f):[]; };
  window.ACS.flsRuleInputs=(bid)=>{ const f=_flsOf(bid); return f?flsRuleInputs(f):{}; };
  /* واقعة قياس إخلاء مقتبَسة — بلا أي مقارنة بحدّ ولا حكم مطابقة */
  window.ACS.flsEgressFacts=(spaceId,bid)=>lastBuilding?
    flsEgressFacts(lastBuilding,bid||'bld_0',spaceId):null;
  window.ACS.flsLayerVisible=(layer,on)=>{ const key=String(layer||'').toUpperCase();
    const r=registry&&registry[key.indexOf('FLS_')===0?key:('FLS_'+key)];
    if(!r) return false;
    if(on!==undefined){ r.visible=!!on; r.meshes.forEach(x=>{x.visible=!!on;}); }
    return !!r.visible; };
  /* ---- عرض بصري وتقديم: تصوير يحفظ الهندسة. لا تعديل هندسي إطلاقاً ---- */
  let _visCache=null, _visKey=null;
  const _visOf=(opts)=>{ if(!lastBuilding) return null;
    opts=opts||{};
    const key=JSON.stringify([opts,lastBuilding]);
    if(_visKey===key) return _visCache;
    _visCache=compileVisualScene(lastBuilding,opts.building_id||'bld_0',
      opts.position||null,opts.rotation_deg||0,opts);
    _visKey=key; return _visCache; };
  window.ACS.visualScene=(opts)=>_visOf(opts);
  window.ACS.visualModes=()=>VIS_MODES.slice();
  window.ACS.visualThemes=()=>VIS_THEMES.slice();
  window.ACS.visualMaterials=()=>Object.keys(VIS_MATERIALS).sort()
    .map(k=>visMaterial(k));
  window.ACS.visualSummary=(opts)=>{ const s=_visOf(opts); return s?s.summary:null; };
  window.ACS.visualObjects=(layer,opts)=>{ const s=_visOf(opts);
    return s?(layer?visObjectsByLayer(s,String(layer).toUpperCase()):s.objects.slice()):[]; };
  window.ACS.visualObject=(id,opts)=>{ const s=_visOf(opts);
    return s?visObjectById(s,id):null; };
  window.ACS.visualValidate=(opts)=>{ const s=_visOf(opts);
    return s?visValidateScene(s):[]; };
  window.ACS.visualRuleInputs=(opts)=>{ const s=_visOf(opts);
    return s?visRuleInputs(s):{}; };
  window.ACS.visualLayerVisible=(layer,on,opts)=>{ const s=_visOf(opts);
    if(!s) return [false,'NO_MODEL',null];
    const r=visSetLayerVisible(s,layer,on);
    if(r[0]){ const key=String(layer).toUpperCase();
      const reg=registry&&registry[key==='ARCHITECTURE'?'WALL':key];
      Object.keys(registry||{}).forEach(k=>{ /* حالة عرض فقط */ }); }
    return r; };
  /* المساقط والقطاعات والواجهات — كلّها مشتقّة من الهندسة نفسها */
  window.ACS.floorPlan2D=(levelIndex,style,bid)=>lastBuilding?
    visFloorPlan(compileArchitecture(lastBuilding,bid||'bld_0',null,0),
      (levelIndex===undefined||levelIndex===null)?0:levelIndex,style||null,bid||'bld_0'):null;
  window.ACS.sectionView=(axis,position,bid)=>lastBuilding?
    visSection(compileArchitecture(lastBuilding,bid||'bld_0',null,0),axis||'x',
      (position===undefined)?null:position,bid||'bld_0'):null;
  window.ACS.elevationView=(face,bid)=>lastBuilding?
    visElevation(compileArchitecture(lastBuilding,bid||'bld_0',null,0),face||'NORTH',
      bid||'bld_0'):null;
  /* الكاميرات والأداء */
  window.ACS.cameraPresets=()=>VIS_CAMERA_PRESETS.slice();
  window.ACS.frameCamera=(preset,roomId,opts)=>{ const s=_visOf(opts);
    return s?visFrameCamera(s,preset,(roomId===undefined)?null:roomId):null; };
  window.ACS.visualInstancing=(opts)=>{ const s=_visOf(opts);
    return s?visInstancingPlan(s):null; };
  window.ACS.visualLod=(budget,opts)=>{ const s=_visOf(opts);
    return s?visLodPlan(s,(budget===undefined)?null:budget):null; };
  /* اللقطة وبياناتها — تنفيذ البكسل في المتصفّح، والوصف حتميّ ومتحقَّق منه */
  window.ACS.snapshotRequest=(o,opts)=>{ const s=_visOf(opts);
    return s?visSnapshotRequest(s,o||{}):null; };
  window.ACS.renderMetadata=(req,kind,at,opts)=>{ const s=_visOf(opts);
    return s?visRenderMetadata(s,req||null,kind||'DETERMINISTIC_RENDER',
      (at===undefined)?null:at,null):null; };
  window.ACS.renderCurrency=(meta,bid)=>lastBuilding?
    visCheckRenderCurrency(meta,lastBuilding,bid||'bld_0'):null;
  window.ACS.snapshot=(o,opts)=>{
    const s=_visOf(opts); if(!s) return null;
    const req=visSnapshotRequest(s,o||{});
    const meta=visRenderMetadata(s,req,'DETERMINISTIC_RENDER',null,null);
    let data=null;
    try{
      const prev={w:renderer.domElement.width,h:renderer.domElement.height,
        ratio:renderer.getPixelRatio()};
      renderer.setPixelRatio(1);
      renderer.setSize(req.width,req.height,false);
      if(camera.isPerspectiveCamera){ camera.aspect=req.width/req.height;
        camera.updateProjectionMatrix(); }
      renderer.render(scene,camera);
      data=renderer.domElement.toDataURL(req.format==='JPEG'?'image/jpeg':'image/png',
        req.quality);
      renderer.setPixelRatio(prev.ratio);
      renderer.setSize(innerWidth,innerHeight,false);
      if(camera.isPerspectiveCamera){ camera.aspect=innerWidth/innerHeight;
        camera.updateProjectionMatrix(); }
    }catch(e){ data=null; }
    return {request:req,metadata:meta,data_url:data,
      rendered:!!data,
      note:data?'a deterministic image of the compiled scene at the stated model hash'
                :'NOT VERIFIED — a real WebGL context is required to produce the pixels'}; };
  /* الذكاء الاصطناعي: واجهة فقط. لا مولّد ولا شبكة ولا أي مسار كتابة في النموذج */
  window.ACS.controlBuffers=(kinds,opts)=>{ const s=_visOf(opts);
    return s?visControlBuffers(s,kinds||null):null; };
  window.ACS.geometrySignature=(opts)=>{ const s=_visOf(opts);
    return s?visGeometrySignature(s,lastBuilding?
      compileArchitecture(lastBuilding,'bld_0',null,0):null):null; };
  window.ACS.aiEnhancementRequest=(prompt,buffers,strength,opts)=>{ const s=_visOf(opts);
    return s?visAiEnhancementRequest(s,prompt||null,buffers||null,
      (strength===undefined)?0.35:strength,
      lastBuilding?compileArchitecture(lastBuilding,'bld_0',null,0):null):null; };
  window.ACS.checkVisualConsistency=(req,reported,tol)=>
    visCheckConsistency(req,reported,(tol===undefined)?0.5:tol);
  /* التصدير: الهندسي يبقى بدلالته، والتقديمي منفصل وصريح */
  window.ACS.exportVisualScene=(presentationGlb,opts)=>{ const s=_visOf(opts);
    return s?visExportScene(s,!!presentationGlb):null; };
  window.ACS.presentationBlock=(opts)=>{ const s=_visOf(opts);
    return s?visPresentationBlock(s):null; };
  window.ACS.applyVisualMode=(mode,opts)=>applyVisualMode(mode,opts||{});
  window.ACS.clearVisualMode=()=>clearVisualMode();
  window.ACS.visualState=()=>VIS_STATE;
  window.ACS.visualAssets=()=>visAssetLibrary();
  window.ACS.validateVisualAsset=(a)=>visValidateAsset(a);
  /* ---- تنسيق بين التخصّصات: كشف وتتبّع فقط. لا إصلاح ولا إعادة توجيه ---- */
  let _coordCache=null, _coordKey=null;
  const _coordOf=(bid,pos,rot)=>{ if(!lastBuilding) return null;
    const key=JSON.stringify([bid||'bld_0',pos||null,rot||0,lastBuilding]);
    if(_coordKey===key) return _coordCache;
    _coordCache=compileCoordination(lastBuilding,bid||'bld_0',pos||null,rot||0,
      null,null,null,null,null);
    _coordKey=key; return _coordCache; };
  window.ACS.coordination=(bid,pos,rot)=>_coordOf(bid,pos,rot);
  window.ACS.clashes=(bid)=>{ const s=_coordOf(bid); return s?s.clashes.slice():[]; };
  window.ACS.clash=(id,bid)=>{ const s=_coordOf(bid); return s?coordClashById(s,id):null; };
  window.ACS.clashesByDiscipline=(a,b,bid)=>{ const s=_coordOf(bid);
    return s?coordFilterClashes(s,{discipline_a:a,discipline_b:b}):[]; };
  window.ACS.coordinationIssues=(bid)=>{ const s=_coordOf(bid);
    return s?s.clashes.filter(c=>c.type==='SEMANTIC_CONFLICT'||c.type==='INVALID_REFERENCE'):[]; };
  window.ACS.coordinationSummary=(bid)=>{ const s=_coordOf(bid); return s?s.summary:null; };
  window.ACS.coordinationPenetrations=(bid)=>{ const s=_coordOf(bid);
    return s?s.penetrations.slice():[]; };
  window.ACS.coordinationSuppressed=(bid)=>{ const s=_coordOf(bid);
    return s?s.suppressed.slice():[]; };
  window.ACS.coordinationRuleInputs=(bid)=>{ const s=_coordOf(bid);
    return s?coordRuleInputs(s):{}; };
  /* حالة التعارض تتغيّر بقرار بشري صريح فقط، ولا تُشتقّ من الهندسة */
  window.ACS.setClashStatus=(id,status,by,at,note,bid)=>{ const s=_coordOf(bid);
    return s?coordSetStatus(s,id,status,by,at,note):[false,'NO_MODEL',null]; };
  /* هل اللقطة ما زالت مطابقة للنموذج الحالي؟ القِدَم يُعلَن ولا يُخفى */
  window.ACS.coordinationSnapshotStatus=(snapshot,bid)=>lastBuilding?
    checkCoordSnapshot(snapshot||_coordOf(bid),lastBuilding,bid||'bld_0'):null;
  window.ACS.compareCoordinationRevisions=(a,b)=>coordReconcile(a,b);
  /* تصدير صريح للقطة التنسيق — لا يُدمَج في تصدير النموذج العادي إطلاقاً */
  window.ACS.exportCoordination=(bid)=>{ const s=_coordOf(bid);
    return s?coordExportSnapshot(s):null; };
  /* ---- إبراز للتصحيح: لا يغيّر مظهر النموذج ولا يُخبز في أي تصدير ---- */
  window.ACS.clashDebugView=(id,bid)=>{ const s=_coordOf(bid);
    return s?coordDebugView(s,id):null; };
  window.ACS.highlightClash=(id,bid)=>{
    const s=_coordOf(bid); if(!s) return null;
    const v=coordDebugView(s,id); if(!v) return null;
    _coordClearOverlay();
    const ids={}; v.highlight.forEach(x=>{ids[x]=true;});
    _coordOverlay.targets=[];
    Object.keys(registry).forEach(k=>{ registry[k].meshes.forEach(m=>{
      const u=m.userData||{};
      const eid=(u.struct&&u.struct.id)||(u.mep&&u.mep.id)||(u.fls&&u.fls.id)||u.element_id||
                (m.name||'').split('|').pop();
      if(ids[eid]||ids[m.name]){ _coordOverlay.targets.push({mesh:m,visible:m.visible});
        m.visible=true; } }); });
    if(v.marker&&window.__ACS_ADD_MARKER__) _coordOverlay.marker=window.__ACS_ADD_MARKER__(v.marker);
    _coordOverlay.active=id;
    return {clash_id:id,highlighted:_coordOverlay.targets.length,marker:!!_coordOverlay.marker,
      note:'debug overlay only — the model itself is unchanged and nothing is exported'}; };
  window.ACS.clearClashHighlight=()=>{ _coordClearOverlay(); return true; };
  const _coordOverlay={active:null,targets:[],marker:null};
  function _coordClearOverlay(){
    _coordOverlay.targets.forEach(t=>{ t.mesh.visible=t.visible; });
    _coordOverlay.targets=[];
    if(_coordOverlay.marker&&window.__ACS_DEL_MARKER__) window.__ACS_DEL_MARKER__(_coordOverlay.marker);
    _coordOverlay.marker=null; _coordOverlay.active=null; }
  window.ACS.closePanel=()=>{ if(innerWidth<=820){p.classList.remove('open');t.textContent='☰';} };
})();

/* حفظ رابط الخادم بين الجلسات */
(function(){
  const el=document.getElementById('llmURL');
  try{ const s=localStorage.getItem('acs_llm'); if(s) el.value=s; }catch(e){}
  el.addEventListener('change',()=>{ try{ localStorage.setItem('acs_llm', el.value.trim()); }catch(e){}
    checkServer(); });
  checkServer();                       // فحص تلقائي عند الفتح — بلا تدخّل من الزائر
  setTimeout(()=>{ if(!SRV_OK) checkServer(true); }, 45000);   // الخوادم المجانية تنام؛ نعيد المحاولة
})();

/* جسر مع سكربت الدخول العادي: المحرّك جاهز الآن */
window.ACS = window.ACS || {};
window.ACS.showExample = ()=>setModel(EXAMPLE);
window.ACS.setModel = setModel;
/* F-27: المبنى المعروض حالياً — قراءة فقط. lastBuilding كان محبوساً داخل هذه
   الوحدة، فلم يكن لأي مقطع آخر طريق إلى النموذج النشط، ولهذا لم تكن لوحات
   المراحل ٦…٩٫٢ قابلة للفتح أصلاً (لا مشروع تُبنى عليه). لا نسخة ثانية ولا
   حالة موازية: هذا هو نفس المرجع الذي يعرضه العارض. */
window.ACS.exportModel = ()=>lastBuilding;
window.ACS.ready = true;
if(window.ACS.pending==='example'){ window.ACS.pending=null; setModel(EXAMPLE); }

/* ========================= استيراد: JSON / DXF / صورة / PDF ========================= */
function decorateRoom(r){const [x,z,w,d]=r.rect;
  if(!r.doors)r.doors=[{edge:'N',offset:Math.max(0.6,Math.min(w/2,w-0.6)),width:0.9,height:2.1}];
  if(!r.points)r.points=[{type:'light',x:w/2,z:d/2},{type:'outlet',x:0.8,z:0.3},
    {type:'outlet',x:Math.max(1,w-0.8),z:0.3},{type:'ac',x:w/2,z:0.2},{type:'smoke',x:w/2,z:d/2}];
  return r;}
function wrapBuilding(rooms, W, D, nF){
  const levels=[{index:0,name:'الأرضي',template:'ground'}];
  for(let i=1;i<=nF;i++)levels.push({index:i,name:acsFloorName('F'+i,nF+2),template:'typical'});
  levels.push({index:nF+1,name:'السطح',template:'roof'});
  const ground={rooms:[{id:'lobby',rect:[W/2-4,1,8,7],
    doors:[{edge:'N',offset:4,width:2.5,height:2.5,material:'glass'}],
    points:[{type:'light',x:4,z:3.5},{type:'camera',x:0.3,z:0.3},{type:'tv',x:7.7,z:3.5}],
    furniture:[{name:'reception',x:4,z:3.5,w:2.4,d:0.8,h:1.1,mat:'counter'}]}]};
  const roof={rooms:[{id:'parapet',rect:[0.2,0.2,W-0.4,D-0.4],wall_h:1.4},
    {id:'tanks',rect:[1,1,4,3],furniture:[{name:'tank',x:2,z:1.5,w:1.6,d:1.6,h:2,mat:'furn'}]},
    {id:'solar',rect:[Math.max(1,W-12),Math.max(1,D-8),10,6],furniture:[{name:'panel',x:5,z:3,w:8,d:4,h:0.15,mat:'tv'}]}]};
  return {site:{w:W,d:D},floor_height:3.2,wall_h:3.0,wall_t:0.15,levels,floors:{ground,typical:{rooms},roof}};
}
/* ---- DXF parser: يقرأ LWPOLYLINE/POLYLINE المغلقة كغرف ---- */
function parseDXF(text){
  const L=text.split(/\r?\n/); const pairs=[];
  for(let k=0;k+1<L.length;k+=2)pairs.push([L[k].trim(),L[k+1]]);
  let cur=null; const polys=[];
  for(const [code,val] of pairs){
    if(code==='0'){ if(cur&&cur.pts.length>=3)polys.push(cur);
      const v=(val||'').trim(); cur=(v==='LWPOLYLINE'||v==='POLYLINE')?{pts:[],_x:null}:null; }
    else if(cur){
      if(code==='10')cur._x=parseFloat(val);
      else if(code==='20'){ if(cur._x!=null){cur.pts.push([cur._x,parseFloat(val)]);cur._x=null;} }
    }
  }
  if(cur&&cur.pts.length>=3)polys.push(cur);
  return polys;
}
function dxfToBuilding(text,W,D,nF){
  const polys=parseDXF(text);
  if(!polys.length) throw new Error('لم نجد مضلّعات مغلقة (Polylines) في الملف.');
  let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
  polys.forEach(p=>p.pts.forEach(([x,y])=>{minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}));
  const dw=Math.max(maxX-minX,1e-3), dh=Math.max(maxY-minY,1e-3);
  const scale=Math.min((W-2)/dw,(D-2)/dh);
  const rooms=polys.map((p,idx)=>{
    let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
    p.pts.forEach(([x,y])=>{x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);});
    const rw=(x1-x0)*scale, rd=(y1-y0)*scale;
    return decorateRoom({id:'poly'+(idx+1),rect:[(x0-minX)*scale+1,(y0-minY)*scale+1,rw,rd]});
  }).filter(r=>r.rect[2]>0.8 && r.rect[3]>0.8);
  if(!rooms.length) throw new Error('المضلّعات صغيرة جداً بعد التحجيم.');
  return wrapBuilding(rooms,W,D,nF);
}
/* ---- استقبال الملف ---- */
function fileToImage(f){return new Promise((res,rej)=>{const img=new Image();img.onload=()=>res(img);img.onerror=rej;img.src=URL.createObjectURL(f);});}
async function loadPdfJs(){
  const pdfjs=await import('/vendor/pdfjs@4.0.379/pdf.min.mjs');   // محلي — بلا CDN
  pdfjs.GlobalWorkerOptions.workerSrc='/vendor/pdfjs@4.0.379/pdf.worker.min.mjs';
  return pdfjs;
}
async function pdfFirstPage(f){
  const pdfjs=await loadPdfJs();
  const buf=await f.arrayBuffer(); const pdf=await pdfjs.getDocument({data:buf}).promise; const page=await pdf.getPage(1);
  const vp=page.getViewport({scale:2}); const c=document.createElement('canvas'); c.width=vp.width;c.height=vp.height;
  await page.render({canvasContext:c.getContext('2d'),viewport:vp}).promise;
  const img=new Image(); await new Promise(r=>{img.onload=r;img.src=c.toDataURL('image/png');}); return img;
}
/* استخراج نص الـPDF مع إعادة بناء الأسطر حسب الإحداثي الرأسي */
async function pdfText(f){
  const pdfjs=await loadPdfJs();
  const buf=await f.arrayBuffer(); const pdf=await pdfjs.getDocument({data:buf}).promise; let out='';
  for(let p=1;p<=pdf.numPages;p++){ const page=await pdf.getPage(p); const tc=await page.getTextContent();
    const lines={};
    tc.items.forEach(it=>{ if(!it.str) return; const y=Math.round(it.transform[5]);
      (lines[y]=lines[y]||[]).push([it.transform[4], it.str]); });
    Object.keys(lines).map(Number).sort((a,b)=>b-a).forEach(y=>{
      out += lines[y].sort((a,b)=>a[0]-b[0]).map(o=>o[1]).join(' ') + '\n'; });
    out+='\n';
  }
  return out;
}
/* يرسل صور المخطط لمحرّك الرؤية */
async function planToLLM(blobs, llm, W, D, nF, info){
  const fd=new FormData();
  blobs.forEach((b,i)=>fd.append('files', b, 'plan'+i+'.png'));
  fd.append('site_w', W); fd.append('site_d', D); fd.append('floors', nF);
  const bt=pickedType(document.getElementById('descText').value||'');
  if(bt&&bt!=='auto') fd.append('btype', bt);
  if((document.getElementById('strictMode')||{}).checked) fd.append('strict','1');
  const res=await __ACS_SHARED.acsFetchJSON('/v1/understand/image',{method:'POST',body:fd}, 900000);
  if(res.status!==ACS_NET.SUCCESS||!(res.body&&res.body.building))
    throw new Error(res.message+(res.request_id?(' · معرّف الطلب '+res.request_id):''));
  const data=res.body;
  setModel(data.building);
  if(data.report&&data.report.repair_proposal) showReport(data.report);
  info.textContent='✓ قُرئ المخطط بالرؤية — '+(data.rooms||'?')+' غرفة · '+(data.levels||'?')+' مستوى'
                   +(data.issues?(' · '+data.issues+' ملاحظة'):'');
}
function canvasToBlob(c){return new Promise(res=>c.toBlob(res,'image/png'));}
async function pdfPagesToBlobs(f, maxPages){
  const pdfjs=await loadPdfJs(); const buf=await f.arrayBuffer();
  const pdf=await pdfjs.getDocument({data:buf}).promise; const out=[];
  const n=Math.min(pdf.numPages, maxPages||3);
  for(let p=1;p<=n;p++){ const page=await pdf.getPage(p);
    let sc=2; const vp0=page.getViewport({scale:1});
    sc=Math.min(2.2, 1600/Math.max(vp0.width,vp0.height));      // دقّة كافية للقراءة
    const vp=page.getViewport({scale:Math.max(sc,1)});
    const c=document.createElement('canvas'); c.width=vp.width; c.height=vp.height;
    await page.render({canvasContext:c.getContext('2d'),viewport:vp}).promise;
    out.push(await canvasToBlob(c));
  }
  return out;
}

async function handleImport(f){
  const info=document.getElementById('impInfo'), name=f.name.toLowerCase();
  const W=+document.getElementById('siteW').value||30,
        D=+document.getElementById('siteD').value||25,
        nF=+document.getElementById('nFloors').value||3;
  info.textContent='جارٍ القراءة…';
  try{
    if(name.endsWith('.json')){ const data=JSON.parse(await f.text());
      const b=(data.levels&&data.floors)?data:wrapBuilding((data.rooms||[]).map(decorateRoom),W,D,nF);
      setModel(b); info.textContent='تم استيراد JSON ✓'; }
    else if(name.endsWith('.dxf')){ const b=dxfToBuilding(await f.text(),W,D,nF);
      setModel(b); info.textContent='تم استيراد DXF ✓ ('+b.floors.typical.rooms.length+' غرفة)'; }
    else if(name.endsWith('.pdf')){
      // (أ) الأفضل: أرسل الـPDF نفسه لمحرّك الفهم — استخراج نصّ سليم + مواضع دقيقة
      const llm=srvURL();
      if(llm){
        info.textContent='🤖 إرسال الـPDF لمحرّك الفهم (LLM)… قد يأخذ دقيقة.';
        try{
          const fd=new FormData(); fd.append('file', f);
          const bt0=(document.getElementById('bType')||{}).value||'auto';
          if(bt0!=='auto') fd.append('btype', bt0);
          const res=await __ACS_SHARED.acsFetchJSON('/v1/understand/pdf',{method:'POST',body:fd}, 900000);
          if(res.http===422){                       // PDF بلا نص = مخطط مرسوم → الرؤية
            info.textContent='📐 المخطط مرسوم بلا نص — أقرأه بالرؤية… قد يأخذ دقيقة.';
            const blobs=await pdfPagesToBlobs(f,3);
            await planToLLM(blobs, llm, W, D, nF, info);
            return;
          }
          if(res.status!==ACS_NET.SUCCESS||!(res.body&&res.body.building))
            throw new Error(res.message+(res.request_id?(' · معرّف الطلب '+res.request_id):''));
          const data=res.body;
          setModel(data.building);
          if(data.report&&data.report.repair_proposal) showReport(data.report);
          info.textContent='✓ تولّد بالذكاء من الـPDF — '+(data.rooms||'?')+' غرفة · '+(data.levels||'?')+' مستوى';
          return;
        }catch(e){ info.textContent='تعذّر عبر LLM ('+e.message+') — نجرّب القراءة المحلية…'; }
      }
      // (ب) احتياطي: قراءة محلية بلا خادم
      info.textContent='جارٍ قراءة نص الـPDF محلياً…';
      let txt=''; try{ txt=await pdfText(f); }catch(e){ txt=''; }
      const meta=detectMeta(txt);
      const b=parseDescription(txt, meta.W||W, meta.D||D, meta.nF||nF);
      const nR=b.floors.typical.rooms.length;
      if(nR>=3){ setModel(b);
        info.textContent='✓ تولّد من نص الـPDF — '+nR+' غرفة · أرض '+(meta.W||W)+'×'+(meta.D||D)+' · '+(meta.nF||nF)+' أدوار'; }
      else {
        // مخطط مصوّر بلا نص: اقرأه بالرؤية دائماً — لا نطلب من العميل رسمه يدوياً
        if(llm){
          try{ info.textContent='📐 مخطط مرسوم — أقرأه بالرؤية…';
               const blobs=await pdfPagesToBlobs(f,3);
               await planToLLM(blobs, llm, W, D, nF, info); return; }
          catch(e){}
        }
        offerTracer(await pdfFirstPage(f), info, 'تعذّرت القراءة الآلية للمخطط.');
      }
    }
    else if(f.type.startsWith('image/')||/\.(png|jpe?g|webp)$/.test(name)){
      const llm=srvURL();
      if(llm){
        info.textContent='📐 قراءة المخطط بالرؤية… قد يأخذ دقيقة.';
        try{ await planToLLM([f], llm, W, D, nF, info); return; }
        catch(e){ info.textContent='تعذّرت القراءة بالرؤية ('+e.message+') — افتح محرّر الرسم.'; }
      }
      offerTracer(f, info, !llm ? 'محرّك القراءة غير متاح الآن.' : 'تعذّرت القراءة الآلية.');
    }
    else info.textContent='صيغة غير مدعومة (JSON / DXF / صورة / PDF).';
  }catch(err){ info.textContent='خطأ: '+err.message; console.error(err); }
}
/* محرّر الرسم اليدوي لم يعد يُفتح تلقائياً — يبقى مخرجاً أخيراً باختيار المستخدم */
async function offerTracer(fileOrImg, info, why){
  info.innerHTML = why + ' يمكنك إعادة المحاولة، أو رسم الغرف يدوياً كحلّ أخير.'
    + ' <button class="ghost acs-mt-6" id="trFallback">✏️ رسم يدوي</button>';
  const b=document.getElementById('trFallback');
  if(b) b.onclick=async()=>{
    const img=(fileOrImg instanceof Blob) ? await fileToImage(fileOrImg) : fileOrImg;
    openTracer(img);
  };
}
document.getElementById('impFile').onchange=e=>{ if(e.target.files[0]) handleImport(e.target.files[0]); };

/* ---- محرّر رسم الغرف فوق المخطط ---- */
let trImg=null, trRooms=[], trStart=null, trView=1;
const trCanvas=document.getElementById('trCanvas'), trCtx=trCanvas.getContext('2d');
function openTracer(img){ trImg=img; trRooms=[];
  const maxW=Math.min(innerWidth-30,1500), maxH=innerHeight-100;
  trView=Math.min(maxW/img.naturalWidth, maxH/img.naturalHeight, 1);
  trCanvas.width=Math.round(img.naturalWidth*trView); trCanvas.height=Math.round(img.naturalHeight*trView);
  document.getElementById('tracer').style.display='flex'; drawTracer(); updTrCount(); }
function drawTracer(){ trCtx.clearRect(0,0,trCanvas.width,trCanvas.height);
  trCtx.drawImage(trImg,0,0,trCanvas.width,trCanvas.height);
  trCtx.lineWidth=2; trCtx.font='13px sans-serif';
  trRooms.forEach((r,i)=>{ trCtx.fillStyle='rgba(56,189,248,0.16)'; trCtx.strokeStyle='#38bdf8';
    trCtx.fillRect(r.x*trView,r.y*trView,r.w*trView,r.h*trView);
    trCtx.strokeRect(r.x*trView,r.y*trView,r.w*trView,r.h*trView);
    trCtx.fillStyle='#eaf4ff'; trCtx.fillText('غرفة '+(i+1), r.x*trView+5, r.y*trView+16); }); }
function trPos(e){const rc=trCanvas.getBoundingClientRect(); return [(e.clientX-rc.left)/trView,(e.clientY-rc.top)/trView];}
trCanvas.addEventListener('mousedown',e=>{trStart=trPos(e);});
trCanvas.addEventListener('mousemove',e=>{ if(!trStart)return; const [x,y]=trPos(e); drawTracer();
  trCtx.strokeStyle='#22c55e'; trCtx.setLineDash([6,4]);
  trCtx.strokeRect(trStart[0]*trView,trStart[1]*trView,(x-trStart[0])*trView,(y-trStart[1])*trView); trCtx.setLineDash([]); });
addEventListener('mouseup',e=>{ if(!trStart)return; const [x,y]=trPos(e);
  const rx=Math.min(trStart[0],x),ry=Math.min(trStart[1],y),rw=Math.abs(x-trStart[0]),rh=Math.abs(y-trStart[1]);
  trStart=null; if(rw>8&&rh>8){trRooms.push({x:rx,y:ry,w:rw,h:rh}); drawTracer(); updTrCount();} });
function updTrCount(){document.getElementById('trCount').textContent=trRooms.length+' غرفة';}
document.getElementById('trUndo').onclick=()=>{trRooms.pop();drawTracer();updTrCount();};
document.getElementById('trClear').onclick=()=>{trRooms=[];drawTracer();updTrCount();};
document.getElementById('trClose').onclick=()=>{document.getElementById('tracer').style.display='none';};
document.getElementById('trGen').onclick=()=>{
  if(!trRooms.length){document.getElementById('trCount').textContent='ارسم غرفة أولاً';return;}
  const Wm=+document.getElementById('trW').value||30, mpp=Wm/trImg.naturalWidth, Dm=trImg.naturalHeight*mpp;
  const nF=+document.getElementById('nFloors').value||3;
  const rooms=trRooms.map((r,i)=>decorateRoom({id:'room'+(i+1),
    rect:[+(r.x*mpp).toFixed(2),+(r.y*mpp).toFixed(2),+(r.w*mpp).toFixed(2),+(r.h*mpp).toFixed(2)]}));
  document.getElementById('tracer').style.display='none';
  setModel(wrapBuilding(rooms, Wm, +Dm.toFixed(1), nF));
};

/* ========================= مثال عمارة الرياض (مضمّن) ========================= */
const EXAMPLE = {
  "meta": { "name": "Riyadh Residential 30x25", "city": "Riyadh", "north": "-Z" },
  "site": { "w": 30.0, "d": 25.0 },
  "floor_height": 3.2,
  "wall_h": 3.0,
  "wall_t": 0.15,

  "levels": [
    { "index": 0, "name": "الأرضي",  "template": "ground" },
    { "index": 1, "name": "الأول",   "template": "typical" },
    { "index": 2, "name": "الثاني",  "template": "typical" },
    { "index": 3, "name": "الثالث",  "template": "typical" },
    { "index": 4, "name": "الرابع",  "template": "typical" },
    { "index": 5, "name": "السطح",   "template": "roof" }
  ],

  "floors": {
    "ground": {
      "rooms": [
        {
          "id": "lobby", "rect": [10, 1, 10, 8], "wall_h": 3.0,
          "doors": [
            { "edge": "N", "offset": 5, "width": 2.5, "height": 2.5, "material": "glass" },
            { "edge": "S", "offset": 5, "width": 2.0, "height": 2.1 }
          ],
          "windows": [ { "edge": "N", "offset": 1.5, "width": 2.0, "sill": 1.0, "height": 1.6 } ],
          "points": [
            { "type": "light", "x": 3, "z": 4 }, { "type": "light", "x": 7, "z": 4 },
            { "type": "camera", "x": 0.5, "z": 0.5 }, { "type": "camera", "x": 9.5, "z": 0.5 },
            { "type": "tv", "x": 9.8, "z": 4 }, { "type": "smoke", "x": 5, "z": 4 },
            { "type": "sprinkler", "x": 2.5, "z": 2 }, { "type": "sprinkler", "x": 7.5, "z": 6 },
            { "type": "outlet", "x": 5, "z": 0.2 }, { "type": "ac", "x": 5, "z": 0.2 }
          ],
          "furniture": [
            { "name": "reception", "x": 5, "z": 4, "w": 2.4, "d": 0.8, "h": 1.1, "mat": "counter" },
            { "name": "sofa", "x": 8, "z": 2, "w": 1.8, "d": 0.9, "h": 0.8, "mat": "furn_soft" },
            { "name": "sofa", "x": 8, "z": 6, "w": 1.8, "d": 0.9, "h": 0.8, "mat": "furn_soft" },
            { "name": "coffee", "x": 8, "z": 4, "w": 1.0, "d": 0.6, "h": 0.45, "mat": "furn" }
          ]
        },
        { "id": "elevator1", "rect": [12.5, 9.2, 1.8, 2.0],
          "doors": [ { "edge": "N", "offset": 0.9, "width": 0.9, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 0.9, "z": 1.0 }, { "type": "camera", "x": 0.3, "z": 0.3 } ] },
        { "id": "elevator2", "rect": [15.0, 9.2, 1.8, 2.0],
          "doors": [ { "edge": "N", "offset": 0.9, "width": 0.9, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 0.9, "z": 1.0 }, { "type": "camera", "x": 0.3, "z": 0.3 } ] },
        { "id": "stair1", "rect": [10.0, 9.2, 2.0, 3.0],
          "doors": [ { "edge": "N", "offset": 1.0, "width": 0.95, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.0, "z": 1.5 }, { "type": "exit", "x": 1.0, "z": 0.2 } ] },
        { "id": "stair2", "rect": [18.0, 9.2, 2.0, 3.0],
          "doors": [ { "edge": "N", "offset": 1.0, "width": 0.95, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.0, "z": 1.5 }, { "type": "exit", "x": 1.0, "z": 0.2 } ] },
        { "id": "guard", "rect": [1, 1, 3, 3],
          "doors": [ { "edge": "E", "offset": 1.5, "width": 0.9, "height": 2.1 } ],
          "windows": [ { "edge": "N", "offset": 1.5, "width": 1.2, "sill": 1.0, "height": 1.2 } ],
          "points": [ { "type": "light", "x": 1.5, "z": 1.5 }, { "type": "outlet", "x": 0.3, "z": 1.5 },
                      { "type": "camera", "x": 2.7, "z": 0.3 } ] },
        { "id": "electrical", "rect": [4.2, 1, 3, 3],
          "doors": [ { "edge": "E", "offset": 1.5, "width": 0.9, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.5, "z": 1.5 }, { "type": "smoke", "x": 1.5, "z": 1.5 } ] },
        { "id": "generator", "rect": [1, 21, 4, 3],
          "doors": [ { "edge": "N", "offset": 2.0, "width": 1.1, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 2, "z": 1.5 }, { "type": "smoke", "x": 2, "z": 1.5 } ] },
        { "id": "parking", "rect": [21, 12, 8, 12], "wall_h": 3.0,
          "points": [
            { "type": "light", "x": 2, "z": 3 }, { "type": "light", "x": 6, "z": 3 },
            { "type": "light", "x": 2, "z": 9 }, { "type": "light", "x": 6, "z": 9 },
            { "type": "ev", "x": 7, "z": 11 }, { "type": "camera", "x": 0.3, "z": 0.3 },
            { "type": "camera", "x": 7.7, "z": 11.7 } ],
          "furniture": [
            { "name": "car", "x": 2, "z": 2, "w": 2.0, "d": 4.5, "h": 1.4, "mat": "furn" },
            { "name": "car", "x": 5, "z": 2, "w": 2.0, "d": 4.5, "h": 1.4, "mat": "furn" },
            { "name": "car", "x": 2, "z": 8, "w": 2.0, "d": 4.5, "h": 1.4, "mat": "furn" }
          ] }
      ]
    },

    "typical": {
      "rooms": [
        {
          "id": "corridor", "rect": [13, 2, 2, 21], "wall_h": 3.0,
          "doors": [
            { "edge": "W", "offset": 8, "width": 1.1, "height": 2.1 },
            { "edge": "E", "offset": 8, "width": 1.1, "height": 2.1 }
          ],
          "points": [
            { "type": "spot", "x": 1, "z": 3 }, { "type": "spot", "x": 1, "z": 7 },
            { "type": "spot", "x": 1, "z": 11 }, { "type": "spot", "x": 1, "z": 15 },
            { "type": "spot", "x": 1, "z": 19 },
            { "type": "camera", "x": 0.3, "z": 0.3 }, { "type": "camera", "x": 1.7, "z": 20 },
            { "type": "smoke", "x": 1, "z": 6 }, { "type": "smoke", "x": 1, "z": 15 },
            { "type": "sprinkler", "x": 1, "z": 10 }, { "type": "vent", "x": 1, "z": 4 }
          ]
        },

        {
          "id": "majlis", "rect": [0.5, 0.5, 6, 5], "wall_h": 3.0,
          "doors": [ { "edge": "E", "offset": 2.5, "width": 0.9, "height": 2.1, "material": "oak" } ],
          "windows": [ { "edge": "N", "offset": 3.0, "width": 4.0, "sill": 0.9, "height": 2.0 } ],
          "points": [
            { "type": "light", "x": 3, "z": 2.5 },
            { "type": "tv", "x": 5.8, "z": 2.5 },
            { "type": "outlet", "x": 5.8, "z": 1.9 }, { "type": "outlet", "x": 5.8, "z": 2.3 },
            { "type": "outlet", "x": 5.8, "z": 2.7 }, { "type": "outlet", "x": 5.8, "z": 3.1 },
            { "type": "network", "x": 5.8, "z": 1.5 },
            { "type": "switch", "x": 5.7, "z": 0.6 },
            { "type": "ac", "x": 3, "z": 0.2 },
            { "type": "smoke", "x": 3, "z": 2.5 }, { "type": "sprinkler", "x": 1.5, "z": 3.5 }
          ],
          "furniture": [
            { "name": "sofa", "x": 3, "z": 0.6, "w": 4.0, "d": 0.8, "h": 0.8, "mat": "furn_soft" },
            { "name": "sofa", "x": 0.7, "z": 2.5, "w": 0.8, "d": 3.0, "h": 0.8, "mat": "furn_soft" },
            { "name": "sofa", "x": 3, "z": 4.4, "w": 4.0, "d": 0.8, "h": 0.8, "mat": "furn_soft" },
            { "name": "table", "x": 3, "z": 2.5, "w": 1.4, "d": 0.8, "h": 0.4, "mat": "furn" }
          ]
        },

        {
          "id": "living", "rect": [0.5, 6, 8, 6], "wall_h": 3.0,
          "doors": [ { "edge": "E", "offset": 3.0, "width": 1.0, "height": 2.1 } ],
          "windows": [ { "edge": "S", "offset": 4.0, "width": 3.0, "sill": 0.3, "height": 2.4 } ],
          "points": [
            { "type": "light", "x": 2.5, "z": 3 }, { "type": "light", "x": 5.5, "z": 3 },
            { "type": "tv", "x": 4, "z": 5.8 },
            { "type": "outlet", "x": 1, "z": 0.2 }, { "type": "outlet", "x": 3, "z": 0.2 },
            { "type": "outlet", "x": 5, "z": 0.2 }, { "type": "outlet", "x": 7, "z": 0.2 },
            { "type": "outlet", "x": 0.2, "z": 2 }, { "type": "outlet", "x": 0.2, "z": 4 },
            { "type": "outlet", "x": 7.8, "z": 2 }, { "type": "outlet", "x": 7.8, "z": 4 },
            { "type": "usb", "x": 1.5, "z": 1 }, { "type": "usb", "x": 2.0, "z": 1 },
            { "type": "network", "x": 7.8, "z": 3 },
            { "type": "camera", "x": 0.3, "z": 0.3 },
            { "type": "ac", "x": 4, "z": 5.8 }, { "type": "smoke", "x": 4, "z": 3 }
          ],
          "furniture": [
            { "name": "Lsofa", "x": 2, "z": 1.2, "w": 3.5, "d": 0.9, "h": 0.8, "mat": "furn_soft" },
            { "name": "Lsofa", "x": 0.9, "z": 2.5, "w": 0.9, "d": 2.5, "h": 0.8, "mat": "furn_soft" },
            { "name": "dining", "x": 5.5, "z": 3, "w": 2.2, "d": 1.0, "h": 0.75, "mat": "furn" }
          ]
        },

        {
          "id": "kitchen", "rect": [0.5, 12.5, 5, 4], "wall_h": 3.0,
          "doors": [ { "edge": "N", "offset": 2.5, "width": 1.0, "height": 2.1 } ],
          "windows": [ { "edge": "W", "offset": 2.0, "width": 1.2, "sill": 1.1, "height": 1.2 } ],
          "points": [
            { "type": "light", "x": 2.5, "z": 2 },
            { "type": "outlet", "x": 1, "z": 0.2 }, { "type": "outlet", "x": 2, "z": 0.2 },
            { "type": "outlet", "x": 3, "z": 0.2 }, { "type": "outlet", "x": 4, "z": 0.2 },
            { "type": "network", "x": 0.2, "z": 2 }, { "type": "smoke", "x": 2.5, "z": 2 },
            { "type": "ac", "x": 2.5, "z": 3.8 }
          ],
          "furniture": [
            { "name": "counter", "x": 2.5, "z": 0.4, "w": 4.6, "d": 0.6, "h": 0.9, "mat": "counter" },
            { "name": "island", "x": 2.5, "z": 2.2, "w": 3.0, "d": 0.9, "h": 0.9, "mat": "counter" },
            { "name": "fridge", "x": 0.5, "z": 3.4, "w": 0.8, "d": 0.8, "h": 1.9, "mat": "furn" }
          ]
        },

        {
          "id": "master_bed", "rect": [0.5, 17, 6, 5], "wall_h": 3.0,
          "doors": [ { "edge": "N", "offset": 3.0, "width": 1.0, "height": 2.1 } ],
          "windows": [ { "edge": "S", "offset": 3.0, "width": 3.5, "sill": 0.4, "height": 2.2 } ],
          "points": [
            { "type": "light", "x": 3, "z": 2.5 },
            { "type": "tv", "x": 3, "z": 0.2 },
            { "type": "outlet", "x": 1.5, "z": 4.5 }, { "type": "outlet", "x": 4.5, "z": 4.5 },
            { "type": "usb", "x": 1.7, "z": 4.5 }, { "type": "usb", "x": 4.3, "z": 4.5 },
            { "type": "network", "x": 0.2, "z": 3 },
            { "type": "switch", "x": 3.5, "z": 0.4 }, { "type": "switch", "x": 1.5, "z": 4.3 },
            { "type": "camera", "x": 0.3, "z": 0.3 },
            { "type": "ac", "x": 3, "z": 4.8 }, { "type": "smoke", "x": 3, "z": 2.5 }
          ],
          "furniture": [
            { "name": "kingbed", "x": 3, "z": 3.6, "w": 2.0, "d": 2.1, "h": 0.6, "mat": "furn_soft" },
            { "name": "wardrobe", "x": 0.7, "z": 2, "w": 0.7, "d": 3.5, "h": 2.4, "mat": "furn" },
            { "name": "desk", "x": 5, "z": 4.2, "w": 1.4, "d": 0.7, "h": 0.75, "mat": "furn" }
          ]
        },
        { "id": "closet", "rect": [6.7, 17, 3, 3.5],
          "doors": [ { "edge": "W", "offset": 1.5, "width": 0.8, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.5, "z": 1.7 }, { "type": "switch", "x": 0.4, "z": 1.5 } ],
          "furniture": [ { "name": "island", "x": 1.5, "z": 1.7, "w": 1.5, "d": 0.7, "h": 0.9, "mat": "furn" } ] },
        { "id": "master_bath", "rect": [9.9, 17, 3, 3.5],
          "doors": [ { "edge": "W", "offset": 1.5, "width": 0.8, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.5, "z": 1.7 }, { "type": "outlet", "x": 0.4, "z": 1 },
                      { "type": "vent", "x": 1.5, "z": 1.7 } ] },

        { "id": "bed2", "rect": [7, 0.5, 4.5, 4.5], "wall_h": 3.0,
          "doors": [ { "edge": "S", "offset": 2.2, "width": 0.9, "height": 2.1 } ],
          "windows": [ { "edge": "N", "offset": 2.2, "width": 1.5, "sill": 1.0, "height": 1.5 } ],
          "points": [ { "type": "light", "x": 2.2, "z": 2.2 }, { "type": "tv", "x": 2.2, "z": 0.2 },
                      { "type": "outlet", "x": 1, "z": 4.3 }, { "type": "outlet", "x": 3.5, "z": 4.3 },
                      { "type": "usb", "x": 1.2, "z": 4.3 }, { "type": "network", "x": 0.2, "z": 2 },
                      { "type": "ac", "x": 2.2, "z": 0.2 }, { "type": "smoke", "x": 2.2, "z": 2.2 } ],
          "furniture": [ { "name": "bed", "x": 2.2, "z": 3.2, "w": 1.6, "d": 2.0, "h": 0.6, "mat": "furn_soft" },
                         { "name": "desk", "x": 4, "z": 1, "w": 1.2, "d": 0.6, "h": 0.75, "mat": "furn" } ] },

        { "id": "kids", "rect": [7, 5.2, 4.5, 4], "wall_h": 3.0,
          "doors": [ { "edge": "S", "offset": 2.2, "width": 0.9, "height": 2.1 } ],
          "windows": [ { "edge": "E", "offset": 2.0, "width": 1.4, "sill": 1.0, "height": 1.4 } ],
          "points": [ { "type": "light", "x": 2.2, "z": 2 }, { "type": "outlet", "x": 1, "z": 0.2 },
                      { "type": "outlet", "x": 3.5, "z": 0.2 }, { "type": "smoke", "x": 2.2, "z": 2 },
                      { "type": "ac", "x": 2.2, "z": 0.2 } ],
          "furniture": [ { "name": "bed", "x": 1.2, "z": 3, "w": 1.0, "d": 2.0, "h": 0.6, "mat": "furn_soft" },
                         { "name": "bed", "x": 3.2, "z": 3, "w": 1.0, "d": 2.0, "h": 0.6, "mat": "furn_soft" } ] },

        { "id": "maid", "rect": [7, 10, 3, 3],
          "doors": [ { "edge": "S", "offset": 1.5, "width": 0.8, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.5, "z": 1.5 }, { "type": "outlet", "x": 0.3, "z": 1.5 } ],
          "furniture": [ { "name": "bed", "x": 1, "z": 1.8, "w": 0.9, "d": 1.9, "h": 0.5, "mat": "furn_soft" } ] },
        { "id": "laundry", "rect": [10.2, 10, 2.8, 3],
          "doors": [ { "edge": "S", "offset": 1.4, "width": 0.8, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 1.4, "z": 1.5 }, { "type": "outlet", "x": 0.5, "z": 0.2 } ],
          "furniture": [ { "name": "washer", "x": 0.8, "z": 0.6, "w": 0.7, "d": 0.7, "h": 0.9, "mat": "furn" },
                         { "name": "dryer", "x": 1.7, "z": 0.6, "w": 0.7, "d": 0.7, "h": 0.9, "mat": "furn" } ] },

        { "id": "apt2_living", "rect": [16, 0.5, 6, 6], "wall_h": 3.0,
          "doors": [ { "edge": "W", "offset": 3.0, "width": 1.0, "height": 2.1 } ],
          "windows": [ { "edge": "N", "offset": 3.0, "width": 3.0, "sill": 0.9, "height": 2.0 } ],
          "points": [ { "type": "light", "x": 3, "z": 3 }, { "type": "tv", "x": 5.8, "z": 3 },
                      { "type": "outlet", "x": 2, "z": 0.2 }, { "type": "outlet", "x": 4, "z": 0.2 },
                      { "type": "camera", "x": 0.3, "z": 0.3 }, { "type": "ac", "x": 3, "z": 0.2 } ],
          "furniture": [ { "name": "sofa", "x": 3, "z": 5, "w": 3.0, "d": 0.9, "h": 0.8, "mat": "furn_soft" } ] },
        { "id": "apt2_bed", "rect": [16, 7, 6, 5], "wall_h": 3.0,
          "doors": [ { "edge": "W", "offset": 2.5, "width": 0.9, "height": 2.1 } ],
          "windows": [ { "edge": "E", "offset": 2.5, "width": 2.0, "sill": 0.9, "height": 1.6 } ],
          "points": [ { "type": "light", "x": 3, "z": 2.5 }, { "type": "outlet", "x": 1, "z": 4.5 },
                      { "type": "outlet", "x": 5, "z": 4.5 }, { "type": "ac", "x": 3, "z": 0.2 } ],
          "furniture": [ { "name": "bed", "x": 3, "z": 3.5, "w": 1.8, "d": 2.0, "h": 0.6, "mat": "furn_soft" } ] },
        { "id": "apt2_kitchen", "rect": [16, 12.5, 5, 4],
          "doors": [ { "edge": "N", "offset": 2.5, "width": 1.0, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 2.5, "z": 2 }, { "type": "outlet", "x": 2, "z": 0.2 },
                      { "type": "smoke", "x": 2.5, "z": 2 } ],
          "furniture": [ { "name": "counter", "x": 2.5, "z": 0.4, "w": 4.5, "d": 0.6, "h": 0.9, "mat": "counter" } ] },
        { "id": "apt2_master", "rect": [16, 17, 6, 5],
          "doors": [ { "edge": "N", "offset": 3.0, "width": 1.0, "height": 2.1 } ],
          "windows": [ { "edge": "S", "offset": 3.0, "width": 3.5, "sill": 0.4, "height": 2.2 } ],
          "points": [ { "type": "light", "x": 3, "z": 2.5 }, { "type": "tv", "x": 3, "z": 0.2 },
                      { "type": "outlet", "x": 1.5, "z": 4.5 }, { "type": "outlet", "x": 4.5, "z": 4.5 },
                      { "type": "camera", "x": 5.7, "z": 0.3 }, { "type": "ac", "x": 3, "z": 4.8 } ],
          "furniture": [ { "name": "kingbed", "x": 3, "z": 3.5, "w": 2.0, "d": 2.1, "h": 0.6, "mat": "furn_soft" } ] }
      ]
    },

    "roof": {
      "rooms": [
        { "id": "parapet", "rect": [0.2, 0.2, 29.6, 24.6], "wall_h": 1.5 },
        { "id": "elevator_room", "rect": [12.5, 9, 4.3, 3],
          "doors": [ { "edge": "S", "offset": 2, "width": 0.9, "height": 2.1 } ],
          "points": [ { "type": "light", "x": 2, "z": 1.5 } ] },
        { "id": "ac_equipment", "rect": [1, 1, 5, 4],
          "points": [ { "type": "ac", "x": 2.5, "z": 2, "height": 1.0 } ],
          "furniture": [ { "name": "chiller", "x": 2.5, "z": 2, "w": 3.0, "d": 2.0, "h": 1.4, "mat": "counter" } ] },
        { "id": "water_tanks", "rect": [24, 1, 5, 4],
          "furniture": [ { "name": "tank", "x": 1.5, "z": 2, "w": 1.6, "d": 1.6, "h": 2.0, "mat": "furn" },
                         { "name": "tank", "x": 3.5, "z": 2, "w": 1.6, "d": 1.6, "h": 2.0, "mat": "furn" } ] },
        { "id": "solar", "rect": [8, 16, 14, 7],
          "furniture": [
            { "name": "panel", "x": 3, "z": 2, "w": 5.0, "d": 2.5, "h": 0.15, "mat": "tv" },
            { "name": "panel", "x": 9, "z": 2, "w": 5.0, "d": 2.5, "h": 0.15, "mat": "tv" },
            { "name": "panel", "x": 3, "z": 5, "w": 5.0, "d": 2.5, "h": 0.15, "mat": "tv" },
            { "name": "panel", "x": 9, "z": 5, "w": 5.0, "d": 2.5, "h": 0.15, "mat": "tv" }
          ] },
        { "id": "seating", "rect": [1, 18, 5, 5],
          "points": [ { "type": "camera", "x": 0.3, "z": 0.3 } ],
          "furniture": [ { "name": "bench", "x": 2.5, "z": 1, "w": 2.5, "d": 0.6, "h": 0.45, "mat": "furn" } ] }
      ]
    }
  }
};

/* ═══════════ ربط شريط الأدوات العائم وأدوات المهندس ═══════════
   (يُنفَّذ في نهاية الوحدة بعد تعريف كل الدوال) */
document.querySelectorAll('#camBar button[data-view]').forEach(b=>{
  b.onclick=()=>setMode(b.dataset.view);
});
document.querySelectorAll('#camBar button[data-tool]').forEach(b=>{
  b.onclick=()=>setTool(b.dataset.tool);
});
document.getElementById('cbShot').onclick=()=>document.getElementById('bShot').click();
document.getElementById('cbNote').onclick=()=>{
  document.getElementById('bNoteMode').click();
  document.getElementById('cbNote').classList.toggle('on', noteMode);
};
document.getElementById('cbClip').onclick=()=>{
  const el=document.getElementById('clipBox');
  const show=el.classList.contains('acs-hidden')
    || !(el.style.display&&el.style.display!=='none');
  /* الإخفاء الابتدائي صنفٌ الآن (style-src 'self')، فالإظهار يزيله */
  el.classList.toggle('acs-hidden', !show);
  el.style.display=show?'block':'none';
  const hint=document.getElementById('clipHint'); if(hint) hint.style.display=show?'none':'';
  document.getElementById('cbClip').classList.toggle('on',show);
  if(show){ showTab('model');
    document.querySelectorAll('.tabs button').forEach(b=>
      b.classList.toggle('active', b.dataset.tab==='model'));
  } else resetClip();
};
['x','y','z'].forEach(ax=>{
  const sl=document.getElementById('clip_'+ax);
  if(sl) sl.oninput=()=>setClip(ax, +sl.value);
});
document.getElementById('clipReset').onclick=resetClip;
(function initSun(){
  const h=document.getElementById('sunHour'), d=document.getElementById('sunDay'),
        c=document.getElementById('sunCity');
  if(!h||!d||!c) return;
  const upd=()=>{ sunStudy.hour=+h.value; sunStudy.day=+d.value; sunStudy.lat=+c.value;
                  applySunStudy(); };
  h.oninput=upd; d.oninput=upd; c.onchange=upd; upd();
})();
markView('orbit');

/* ==== ACS RUNTIME RENDER DIAGNOSTICS (F-08 · hand-written, NOT generated) ====
   عقد تشخيص دائم يعمل في الإنتاج: كل قيمة هنا مقيسة فعلاً من المُصيِّر ومن
   المشهد ومن البكسلات، وما لا يمكن قياسه في هذا المتصفّح يُعاد null — لا رقم
   مختلَق أبداً. لا يكتب في النموذج، ولا يرسل شيئاً إلى أي جهة. */
const ACS_DIAG_KEYS=['build_sha','model_hash','revision_id','canvas_size',
  'device_pixel_ratio','webgl_version','renderer','object_count','mesh_count',
  'triangle_count','draw_calls','scene_bounds','camera_position',
  'camera_target','near','far','frustum_intersections',
  'invalid_coordinate_count','max_coordinate_abs','render_mode',
  'postprocessing','xr_state','context_lost','pixel_probe'];

function _acsFin(v){ return (typeof v==='number'&&isFinite(v))?v:null; }

/* بصمة البناء — من window.ACS_BUILD_INFO وحده، وغيابها null لا قيمة بديلة */
function _acsBuildSha(){
  try{ const b=window.ACS_BUILD_INFO;
    return (b&&typeof b.git_sha==='string'&&b.git_sha)?b.git_sha:null;
  }catch(e){ return null; } }

/* اسم المُصيِّر الحقيقي من WebGL — لا سلسلة ثابتة */
function _acsRendererName(gl){
  try{
    const ext=gl.getExtension('WEBGL_debug_renderer_info');
    if(ext){ const s=gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
      if(s) return String(s); }
    const s2=gl.getParameter(gl.RENDERER);
    return s2?String(s2):null;
  }catch(e){ return null; } }

/* مسح فعلي للبكسلات: عدد البكسلات غير الصفرية ومتوسّط النصوع.
   يُقرأ من مخزن الرسم نفسه بـ readPixels؛ وإن تعذّر فمن نسخة مصغَّرة عبر
   getImageData. تعذُّر الاثنين ⇒ كل الأرقام null وسبب معلَن. */
function _acsPixelProbe(){
  const out={method:null,sampled:0,non_zero_pixels:null,non_zero_pct:null,
    luminance_mean:null,max_luminance:null,reason:null};
  let el=null;
  try{ el=renderer.domElement; }catch(e){ el=null; }
  if(!el){ out.reason='NO_CANVAS'; return out; }
  try{
    const gl=renderer.getContext();
    if(gl&&!gl.isContextLost()){
      const w=Math.max(1,Math.min(el.width||1,320));
      const h=Math.max(1,Math.min(el.height||1,180));
      const px=new Uint8Array(w*h*4);
      gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const n=w*h; let nz=0,sum=0,mx=0;
      for(let i=0;i<n;i++){
        const r=px[i*4],g=px[i*4+1],b=px[i*4+2];
        if(r!==0||g!==0||b!==0) nz++;
        const l=0.2126*r+0.7152*g+0.0722*b;
        sum+=l; if(l>mx) mx=l; }
      out.method='READ_PIXELS'; out.sampled=n; out.non_zero_pixels=nz;
      out.non_zero_pct=Math.round((nz/n)*10000)/100;
      out.luminance_mean=Math.round((sum/n)*1000)/1000;
      out.max_luminance=Math.round(mx*1000)/1000;
      return out; }
    out.reason='CONTEXT_LOST';
  }catch(e){ out.reason='READ_PIXELS_FAILED:'+String(e&&e.message||e).slice(0,60); }
  try{
    const w=Math.max(1,Math.min(el.width||1,160));
    const h=Math.max(1,Math.min(el.height||1,90));
    const c=document.createElement('canvas'); c.width=w; c.height=h;
    const cx=c.getContext('2d');
    if(!cx){ out.reason=(out.reason||'')+'|NO_2D_CONTEXT'; return out; }
    cx.drawImage(el,0,0,w,h);
    const d=cx.getImageData(0,0,w,h).data;
    const n=w*h; let nz=0,sum=0,mx=0;
    for(let i=0;i<n;i++){
      const r=d[i*4],g=d[i*4+1],b=d[i*4+2];
      if(r!==0||g!==0||b!==0) nz++;
      const l=0.2126*r+0.7152*g+0.0722*b;
      sum+=l; if(l>mx) mx=l; }
    out.method='GET_IMAGE_DATA'; out.sampled=n; out.non_zero_pixels=nz;
    out.non_zero_pct=Math.round((nz/n)*10000)/100;
    out.luminance_mean=Math.round((sum/n)*1000)/1000;
    out.max_luminance=Math.round(mx*1000)/1000;
    out.reason=out.reason||null;
  }catch(e){
    out.reason=(out.reason?out.reason+'|':'')
      +'GET_IMAGE_DATA_FAILED:'+String(e&&e.message||e).slice(0,60); }
  return out; }

window.ACS.renderDiagnostics=function(){
  const D={}; ACS_DIAG_KEYS.forEach(k=>{ D[k]=null; });
  D.build_sha=_acsBuildSha();
  /* هويّة النموذج المحمَّل — مشتقّة من النموذج القانوني نفسه، لا مخزَّنة */
  try{
    if(lastBuilding){
      const rev=modelRevision(lastBuilding,'building','bld_0',null);
      D.model_hash=rev.model_hash||null;
      D.revision_id=rev.revision_id||null; }
  }catch(e){ D.model_hash=null; D.revision_id=null; }
  let gl=null,el=null;
  try{ el=renderer.domElement; gl=renderer.getContext(); }catch(e){ }
  if(el) D.canvas_size={width:_acsFin(el.width),height:_acsFin(el.height),
    css_width:_acsFin(el.clientWidth),css_height:_acsFin(el.clientHeight)};
  try{ D.device_pixel_ratio=(typeof window.devicePixelRatio==='number')
    ?window.devicePixelRatio:null; }catch(e){ D.device_pixel_ratio=null; }
  try{ D.webgl_version=renderer.capabilities
    ?(renderer.capabilities.isWebGL2?2:1):null; }catch(e){ D.webgl_version=null; }
  D.renderer=gl?_acsRendererName(gl):null;
  try{ D.context_lost=gl?!!gl.isContextLost():null; }catch(e){ D.context_lost=null; }
  /* عدّ حقيقي بمرور على الشجرة، لا رقم مخزَّن */
  try{
    scene.updateMatrixWorld(true);
    let objects=0,meshes=0,bad=0,maxAbs=0,inFrustum=0;
    const box=new THREE.Box3(); let boxed=0;
    let frustum=null;
    try{
      camera.updateMatrixWorld(true);
      const m=new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,
        camera.matrixWorldInverse);
      frustum=new THREE.Frustum().setFromProjectionMatrix(m);
    }catch(e){ frustum=null; }
    const b3=new THREE.Box3(), sp=new THREE.Sphere();
    scene.traverse(o=>{
      objects++;
      if(!o.isMesh) return;
      meshes++;
      let ok=true;
      try{
        b3.setFromObject(o);
        const vs=[b3.min.x,b3.min.y,b3.min.z,b3.max.x,b3.max.y,b3.max.z];
        if(!vs.every(v=>isFinite(v))) ok=false;
        else{
          vs.forEach(v=>{ if(Math.abs(v)>maxAbs) maxAbs=Math.abs(v); });
          if(frustum){ b3.getBoundingSphere(sp);
            if(frustum.intersectsSphere(sp)) inFrustum++; }
          box.union(b3); boxed++; }
      }catch(e){ ok=false; }
      if(!ok) bad++; });
    D.object_count=objects; D.mesh_count=meshes;
    D.invalid_coordinate_count=bad;
    D.max_coordinate_abs=boxed?Math.round(maxAbs*1000)/1000:null;
    D.frustum_intersections=frustum?inFrustum:null;
    if(boxed&&isFinite(box.min.x)){
      const c=box.getCenter(new THREE.Vector3());
      const s=box.getSize(new THREE.Vector3());
      D.scene_bounds={min:[box.min.x,box.min.y,box.min.z],
        max:[box.max.x,box.max.y,box.max.z],
        center:[c.x,c.y,c.z],size:[s.x,s.y,s.z],
        radius:Math.max(s.x,s.y,s.z)/2,measured_meshes:boxed}; }
  }catch(e){ }
  /* أرقام المُصيِّر من renderer.info.render مباشرةً */
  try{
    const inf=renderer.info&&renderer.info.render?renderer.info.render:null;
    D.draw_calls=inf?_acsFin(inf.calls):null;
    D.triangle_count=inf?_acsFin(inf.triangles):null;
  }catch(e){ }
  try{
    D.camera_position=[camera.position.x,camera.position.y,camera.position.z];
    D.near=_acsFin(camera.near); D.far=_acsFin(camera.far);
  }catch(e){ }
  try{
    D.camera_target=(typeof orbit!=='undefined'&&orbit&&orbit.target)
      ?[orbit.target.x,orbit.target.y,orbit.target.z]:null;
  }catch(e){ D.camera_target=null; }
  /* وضع العرض الفعلي المطبَّق — من الحالة المطبَّقة لا من نيّة المستخدم */
  try{
    const pq=(window.__ACS_PQ__&&window.__ACS_PQ__.applied)
      ?window.__ACS_PQ__.applied:null;
    const ad=(window.__ACS_AD__&&window.__ACS_AD__.applied)
      ?window.__ACS_AD__.applied:null;
    const parts=[];
    if(pq) parts.push('PBR:'+JSON.stringify(pq).slice(0,80));
    if(ad) parts.push('AD:'+JSON.stringify(ad).slice(0,80));
    try{ if(renderer.xr&&renderer.xr.isPresenting) parts.push('XR'); }catch(e){}
    D.render_mode=parts.length?parts.join('|'):'BASE';
  }catch(e){ D.render_mode=null; }
  try{
    const comp=(window.__ACS_PQ__||{}).composer||null;
    D.postprocessing={composer_active:!!comp,
      pass_count:(comp&&comp.passes)?comp.passes.length:null,
      fail_open_reason:(window.__ACS_RR__
        &&window.__ACS_RR__.postprocess_fail_open)
        ?window.__ACS_RR__.postprocess_fail_open:null};
  }catch(e){ D.postprocessing=null; }
  try{
    const xr=renderer.xr||null;
    D.xr_state=xr?{enabled:!!xr.enabled,presenting:!!xr.isPresenting,
      session:!!(xr.getSession&&xr.getSession()),
      supported:(typeof navigator!=='undefined'&&navigator.xr)?true:false}
      :null;
  }catch(e){ D.xr_state=null; }
  D.pixel_probe=_acsPixelProbe();
  /* العقد مضبوط المفاتيح: لا مفتاح زائد ولا ناقص */
  const out={}; ACS_DIAG_KEYS.forEach(k=>{ out[k]=(k in D)?D[k]:null; });
  return out; };

/* هل نافذة العرض خالية فعلاً؟ سؤال بكسلات، لا ظنّ. */
window.ACS.viewportBlank=function(){
  const p=_acsPixelProbe();
  if(p.non_zero_pct===null) return {blank:null,probe:p};
  return {blank:p.non_zero_pct<=1.5,probe:p}; };

/* حزمة تشخيص قابلة للتنزيل. لا شبكة إطلاقاً: لا fetch ولا XMLHttpRequest ولا
   sendBeacon ولا أي إرسال — Blob و objectURL ورابط تنزيل محلي فقط. */
window.ACS.captureRenderFailure=function(opts){
  const o=opts||{};
  const rec={contract:'acs-render-failure/1.0.0',
    captured_at_ms:(typeof performance!=='undefined'&&performance.now)
      ?Math.round(performance.now()):null,
    uploaded:false,upload_target:null,transmits_anything:false,
    build_info:null,viewport_blank:null,diagnostics:null,
    camera:null,render_mode:null,building_json:null,
    building_json_included:false,building_json_excluded_reason:null,
    detail:null,download:null,issues:[]};
  try{ rec.build_info=window.ACS_BUILD_INFO||null; }catch(e){ rec.build_info=null; }
  let blank=null;
  try{ const v=window.ACS.viewportBlank(); rec.viewport_blank=v; blank=v.blank; }
  catch(e){ rec.issues.push('VIEWPORT_PROBE_FAILED'); }
  try{ rec.diagnostics=window.ACS.renderDiagnostics(); }
  catch(e){ rec.issues.push('DIAGNOSTICS_FAILED'); }
  try{ rec.detail=(typeof window.ACS.renderDiagnosticsDetail==='function')
    ?window.ACS.renderDiagnosticsDetail():null; }catch(e){ rec.detail=null; }
  try{
    rec.camera={position:(rec.diagnostics||{}).camera_position||null,
      target:(rec.diagnostics||{}).camera_target||null,
      near:(rec.diagnostics||{}).near,far:(rec.diagnostics||{}).far,
      fov:_acsFin(camera.fov),aspect:_acsFin(camera.aspect)};
  }catch(e){ rec.camera=null; }
  rec.render_mode=(rec.diagnostics||{}).render_mode||null;
  /* نموذج المبنى يُرفَق إن كان إرفاقه آمناً: قابل للتسلسل وتحت سقف الحجم */
  try{
    if(!lastBuilding) rec.building_json_excluded_reason='NO_MODEL_LOADED';
    else{
      const s=JSON.stringify(lastBuilding);
      if(s.length>4000000) rec.building_json_excluded_reason='TOO_LARGE';
      else{ rec.building_json=JSON.parse(s); rec.building_json_included=true; } }
  }catch(e){ rec.building_json_excluded_reason='NOT_SERIALISABLE'; }
  rec.blank_detected=blank;
  let text=null;
  try{ text=JSON.stringify(rec,null,2); }
  catch(e){ text=JSON.stringify({contract:rec.contract,
    issues:['REPORT_NOT_SERIALISABLE']},null,2); }
  const name='acs-render-diagnostics-'
    +((rec.diagnostics||{}).build_sha||'unprovenanced')+'.json';
  let url=null;
  try{
    const blob=new Blob([text],{type:'application/json'});
    url=URL.createObjectURL(blob);
    rec.download={filename:name,object_url:url,bytes:text.length,
      revoked:false,uploaded:false};
    if(o.download!==false){
      const a=document.createElement('a');
      a.href=url; a.download=name; a.rel='noopener';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(()=>{ try{ URL.revokeObjectURL(url); }catch(e){} },30000); }
  }catch(e){
    rec.issues.push('BLOB_UNAVAILABLE:'+String(e&&e.message||e).slice(0,60));
    rec.download={filename:name,object_url:null,bytes:text.length,
      revoked:null,uploaded:false}; }
  rec.report_json=text;
  return rec; };

/* زرّ التنزيل ومعرّف البناء المرئي — عناصر مكتوبة يدوياً في DOM الصفحة */
(function(){
  try{
    /* المعالِج الكامل يستبدل الاحتياطي الكلاسيكي الآن وقد أقلع المحرّك */
    const btn=document.getElementById('acsDiagBtn');
    if(btn) btn.onclick=function(){
      const r=window.ACS.captureRenderFailure();
      const st=document.getElementById('acsDiagState');
      if(st) st.textContent='تم تجهيز ملفّ التشخيص ('+((r.download||{}).bytes||0)
        +' بايت) — لم يُرسَل إلى أي جهة.';
    };
    /* معرّف البناء يُرسَم في السكربت الكلاسيكي في <head> حتى يظهر حتى لو مات
       سكربت الوحدة؛ هنا نعيد رسمه فقط إن لم يكن قد رُسم بعد. */
    const b=window.ACS_BUILD_INFO||{};
    const idEl=document.getElementById('acsBuildId');
    if(idEl&&(!idEl.textContent||idEl.textContent==='…')){
      idEl.textContent=b.label||'UNPROVENANCED BUILD';
      if(!b.substituted) idEl.setAttribute('data-unprovenanced','1'); }
  }catch(e){ }
})();
/* ==== END ACS RUNTIME RENDER DIAGNOSTICS ==== */



/* نشر الارتباطات التي يقرأها مقطع أسبق — تُقرأ داخل دوالّ فقط،
   فالنشر عند نهاية تقييم هذه الوحدة يسبق أي قراءة حتماً. */
Object.assign(__ACS_LATE, { camera, lastBuilding, model, orbit, setSun });


export { ACS_APPLY_CONTRACT, ACS_APPLY_MIN_KEPT, floorLabel, ACS_LAST_APPLY, acsApplyBuilding, acsApplyFirstFrame, acsApplyTicket, _acsErrorSite, _acsStackHead, _acsZonesAsked, ACS_CODE_HINT, ACS_DIAG_KEYS, ACS_ERR_HINT, ACS_FAIL, ACS_LAST_CALL, ACS_LAST_FAILURE, ACS_NET, ACS_TRANSPORT_CLASSES, AR_COLORS, COLOR_SWATCH, EXAMPLE, MEAS_MAT, SRV_OK, TOOL, VIEWS, _acsBuildSha, _acsFin, _acsPixelProbe, _acsRendererName, acsFail, acsGenerateFromServer, addMarker, addMeasurePoint, apiURL, applyAllBtn, applyClip, applyDoorTex, applyFinish, applySunStudy, applyWalkCamera, arRestore, arScale, bounds, buildFloors, buildLayers, buildLocal, camWorld, camera, canvasToBlob, checkServer, clearMeasure, clip, decorateRoom, detectColor, detectSurface, dl, doorMeshes, doorTexture, drawTracer, drop, dxfToBuilding, ensureGround, esc, fileToImage, floorSel, floorsFound, flsInfoCard, fly, flyStep, flyTo, fmt, ground, handleImport, headLamp, infoEl, infoQuickColors, isolateTemplate, keys, last, last2, lastBuilding, loadPdfJs, markView, measure, mepInfoCard, meshesOfRoom, mode, model, mouse, noteMarkers, noteModal, noteMode, notePoint, noteTarget, notes, offerTracer, openNote, openTracer, orbit, parseDXF, pdfFirstPage, pdfPagesToBlobs, pdfText, photoApplied, pickedType, planToLLM, player, ray, real, rebuildMarkers, registry, renderNotes, resetClip, roomOfTag, setClip, setMeasureHUD, setMode, setModel, setSun, setTool, shadeBy, showCoverage, showReport, showTab, srvPill, srvURL, startWalk, stopWalk, structInfoCard, sunAngles, sunStudy, tagOf, texRepeatEl, texTargetEl, tourStep, tourT, trCanvas, trCtx, trImg, trPos, trRooms, trStart, trView, updTrCount, updateVis, useDoorImage, viewPose, vr, vrEnter, vrExit, vrRay, vrRotate, vrSetup, vrStep, vrTeleport, walkHUD, walkLook, walkMove, walkState, walkStep, wrapBuilding };
