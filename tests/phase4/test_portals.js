const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_runtime_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const VS=(name,opts)=>compileVisualScene(C(SC.models[name]),'bld_0',null,0,
  Object.assign({mode:'ENGINEERING',at:AT},opts||{}));
const RS=(name,opts,cfg)=>compileRuntimeScene(VS(name,opts),cfg||null);
const codes=r=>r.issues.map(i=>i.code);

/* الكلمات الممنوعة ترد داخل نصوص النفي نفسها، فالفحص يقرأ الحقول لا النصّ الخام */
const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer','derivation',
  'authority','portal_note','connectivity_note','runtime_note','mode_note',
  'layer_note','provenance_note','authority_note','derivation_note','mode_intent',
  'portal_state_note','decoration_note','ephemerality_note','collision_note',
  'walkability_note','vertical_note','spawn_note','forbidden_claims'];
const scanFields=(root,re)=>{ const hits=[];
  const walk=(v,path)=>{ if(Array.isArray(v)) return v.forEach((x,i)=>walk(x,path+'['+i+']'));
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(NOTE_KEYS.indexOf(k)>=0) return;
      if(re.test(k)) hits.push(path+'.'+k);
      if(typeof v[k]==='string'&&re.test(v[k])) hits.push(path+'.'+k+'="'+v[k]+'"');
      walk(v[k],path+'.'+k); }); };
  walk(root,''); return hits; };

const villa=RS('villa'), hotel=RS('hotel'), clinic=RS('clinic');

console.log('\n== PORTALS DERIVE FROM MODELLED DOORS ==');
chk('a portal exists for every modelled door', (function(){
  const vs=VS('villa');
  return villa.walkability.portals.length===vs.objects.filter(o=>o.kind==='DOOR').length; })());
chk('every portal names its source door',
    villa.walkability.portals.every(p=>!!p.source_element_id));
chk('every portal names its host wall and whether it resolved',
    villa.walkability.portals.every(p=>p.host_wall_id!==undefined
      &&typeof p.host_wall_resolved==='boolean'));
chk('portal ids are deterministic and unique',
    new Set(villa.walkability.portals.map(p=>p.portal_id)).size
      ===villa.walkability.portals.length);
chk('the default portal state comes from the specification',
    villa.walkability.portals.every(p=>p.default_state===RT_DEFAULT_PORTAL_STATE));
/* لا حقل تحكّم بالدخول ولا قفل — والفحص يستثني نصوص النفي كي لا تُحسب نفياً إثباتاً */
const ACCESS_RE=/\block(ed|s|ing|able|out)?\b|\baccess\b|badge|keycard|card_reader|credential|authoriz|authoris|\bpermit\b|security_clearance/i;
chk('a portal never carries an access-control or locking field', (function(){
  const hits=villa.walkability.portals.concat(hotel.walkability.portals)
    .concat(clinic.walkability.portals).map(p=>scanFields(p,ACCESS_RE))
    .reduce((a,b)=>a.concat(b),[]);
  if(hits.length) console.log('     hits:',JSON.stringify(hits.slice(0,4)));
  return hits.length===0; })());
chk('the only mention of access control anywhere in a portal is an explicit denial',
    (function(){
  const raw=villa.walkability.portals.concat(hotel.walkability.portals)
    .concat(clinic.walkability.portals)
    .filter(p=>ACCESS_RE.test(JSON.stringify(p)));
  return raw.length===villa.walkability.portals.length
        +hotel.walkability.portals.length+clinic.walkability.portals.length
    &&raw.every(p=>/no access control is implied/.test(String(p.note))); })());
chk('the runtime specification declares no access-control vocabulary', (function(){
  const hits=scanFields(ACS_RUNTIME_SPEC,ACCESS_RE);
  if(hits.length) console.log('     hits:',JSON.stringify(hits.slice(0,4)));
  return hits.length===0; })());
chk('the specification states the denial explicitly instead of staying silent',
    /no access control, security, locking or scheduling behaviour is implied/
      .test(String(ACS_RUNTIME_SPEC.portal_state_note)));
chk('the regular expression is not vacuous — it catches a planted access field',
    scanFields({portal_id:'x',locked:true},ACCESS_RE).length>0
    &&scanFields({portal_id:'x',access_level:'BADGE'},ACCESS_RE).length>0
    &&scanFields({portal_id:'x',blocking:true},ACCESS_RE).length===0);

console.log('\n== CONNECTIVITY IS DERIVED, NEVER FABRICATED ==');
const resolved=villa.walkability.portals.filter(p=>p.connectivity_resolved);
chk('room-to-room connectivity is derived where the model proves it',
    resolved.some(p=>p.connectivity_basis==='two_space_probe'));
chk('a resolved room-to-room portal names two different real spaces',
    resolved.filter(p=>p.connectivity_basis==='two_space_probe').every(p=>
      p.from_space!==p.to_space
      &&villa.rooms.some(r=>r.space_id===p.from_space)
      &&villa.rooms.some(r=>r.space_id===p.to_space)));
chk('a corridor is reachable as an ordinary space',
    resolved.some(p=>String(p.from_space).indexOf('corridor')>=0
      ||String(p.to_space).indexOf('corridor')>=0));
chk('room-to-exterior is derived only on an exterior-exposed host', (function(){
  const ext=villa.walkability.portals.concat(clinic.walkability.portals)
    .filter(p=>p.to_space===RT_EXTERIOR);
  return ext.every(p=>p.connectivity_basis==='one_space_probe_exterior'); })());
chk('unresolved connectivity is reported as unresolved, never invented',
    villa.walkability.portals.filter(p=>!p.connectivity_resolved).every(p=>
      p.connectivity_basis==='unresolved'&&p.to_space===null));
chk('the unresolved count is published',
    typeof villa.counts.portals_unresolved==='number');
chk('a portal never connects a space to itself',
    villa.walkability.portals.filter(p=>p.connectivity_resolved)
      .every(p=>p.from_space!==p.to_space));
chk('a door whose host wall does not exist is reported', (function(){
  const adv=SC.adversarial.filter(a=>a[0]==='door_missing_host')[0][1];
  return codes(compileRuntimeScene(LIB.hydrate(adv)))
    .indexOf('PORTAL_REFERENCE_INVALID')>=0; })());
chk('a duplicate portal id is refused', (function(){
  const vs=VS('villa');
  const d=vs.objects.filter(o=>o.kind==='DOOR')[0];
  const clone=JSON.parse(JSON.stringify(d)); clone.id=d.id+'#copy';
  vs.objects.push(clone);
  return codes(compileRuntimeScene(vs)).indexOf('PORTAL_DUPLICATE')>=0; })());
chk('validation refuses a portal pointing at an unknown space', (function(){
  const s=RS('villa'); const p=s.walkability.portals.filter(x=>x.connectivity_resolved)[0];
  p.to_space='ghost_room';
  return validateRuntimeScene(s).issues
    .some(i=>i.code==='PORTAL_SPACE_REFERENCE_INVALID'); })());
chk('validation refuses a self-looping portal', (function(){
  const s=RS('villa'); const p=s.walkability.portals.filter(x=>x.connectivity_resolved)[0];
  p.to_space=p.from_space;
  return validateRuntimeScene(s).issues
    .some(i=>i.code==='PORTAL_SPACE_REFERENCE_INVALID'); })());
chk('validation refuses an unknown default portal state', (function(){
  const s=RS('villa'); s.walkability.portals[0].default_state='AJAR';
  return validateRuntimeScene(s).issues.some(i=>i.code==='PORTAL_STATE_INVALID'); })());

console.log('\n== ROOM CONNECTIVITY GRAPH ==');
const g=roomConnectivityGraph(villa);
chk('the graph lists spaces and portal edges',
    Array.isArray(g.spaces)&&Array.isArray(g.edges)&&g.edges.length>0);
chk('every edge names a real portal',
    g.edges.every(e=>villa.walkability.portals.some(p=>p.portal_id===e.portal_id)));
chk('every edge endpoint is a listed space',
    g.edges.every(e=>g.spaces.indexOf(e.from)>=0&&g.spaces.indexOf(e.to)>=0));
chk('unresolved portals are listed separately, not as edges',
    g.unresolved.length===villa.counts.portals_unresolved
    &&g.edges.length+g.unresolved.length===villa.counts.portals);
chk('the graph is deterministic',
    JSON.stringify(roomConnectivityGraph(villa))===JSON.stringify(g));
chk('the graph is a foundation and claims no routing',
    /no route planning, evacuation routing or pathfinding/.test(g.note));
chk('the graph contains no path, route or cost field',
    JSON.stringify(g).indexOf('"path"')<0&&JSON.stringify(g).indexOf('"route"')<0
    &&JSON.stringify(g).indexOf('"cost"')<0);

console.log('\n== PORTAL STATE IS EPHEMERAL ==');
const st=createRuntimeState(villa,'WALK');
const pid=villa.walkability.portals[0].portal_id;
chk('a portal state change succeeds and is marked runtime-only', (function(){
  const r=setPortalState(st,villa,pid,'CLOSED');
  return r.valid&&r.state==='CLOSED'&&r.runtime_only===true; })());
chk('the change lands in runtime state only', st.portal_states[pid]==='CLOSED');
chk('the compiled portal still carries its default state',
    villa.walkability.portals[0].default_state==='OPEN');
chk('the runtime scene is unchanged by state transitions', (function(){
  const s=RS('villa'); const before=JSON.stringify(s);
  const t=createRuntimeState(s,'WALK');
  s.walkability.portals.forEach(p=>{ setPortalState(t,s,p.portal_id,'CLOSED');
    setPortalState(t,s,p.portal_id,'OPEN'); });
  return JSON.stringify(s)===before; })());
chk('the door model hash is unchanged across state transitions', (function(){
  const m=C(SC.models.villa);
  const before=JSON.stringify(compileArchitecture(C(m),'bld_0',null,0).openings);
  const s=compileRuntimeScene(compileVisualScene(m,'bld_0',null,0,{mode:'ENGINEERING',at:AT}));
  const t=createRuntimeState(s,'WALK');
  s.walkability.portals.forEach(p=>setPortalState(t,s,p.portal_id,'CLOSED'));
  return JSON.stringify(compileArchitecture(C(m),'bld_0',null,0).openings)===before; })());
chk('an unknown portal state is refused',
    codes(setPortalState(st,villa,pid,'AJAR')).indexOf('PORTAL_STATE_INVALID')>=0);
chk('an unknown portal id is refused',
    codes(setPortalState(st,villa,'portal:ghost','OPEN'))
      .indexOf('PORTAL_REFERENCE_INVALID')>=0);

console.log('\n== TRAVERSAL ==');
function crossing(scene,portal){
  const ap=portal.aperture, thinX=ap.hx<=ap.hz;
  const y=scene.walkability.surfaces.filter(s=>s.level_index===portal.level_index)[0]
    .elevation_m;
  return thinX?[[ap.cx-0.9,y,ap.cz],[ap.cx+0.9,y,ap.cz]]
              :[[ap.cx,y,ap.cz-0.9],[ap.cx,y,ap.cz+0.9]]; }
const trav=villa.walkability.portals.filter(p=>p.connectivity_resolved
  &&villa.walkability.surfaces.some(s=>s.level_index===p.level_index))[0];
chk('a traversable portal exists in the fixture', !!trav);
if(trav){
  const pts=crossing(villa,trav);
  const t=createRuntimeState(villa,'WALK');
  chk('an open portal allows passage through its host wall',
      runtimeMoveQuery(villa,t,pts[0],pts[1]).allowed===true);
  setPortalState(t,villa,trav.portal_id,'CLOSED');
  const blocked=runtimeMoveQuery(villa,t,pts[0],pts[1]);
  chk('a closed portal blocks passage',
      blocked.allowed===false&&blocked.blocked_kind==='WALL');
  chk('the blocking element is the host wall',
      blocked.blocked_by==='obstacle:'+trav.host_wall_id);
  setPortalState(t,villa,trav.portal_id,'OPEN');
  chk('reopening restores passage',
      runtimeMoveQuery(villa,t,pts[0],pts[1]).allowed===true); }

console.log('\n== VERTICAL CONNECTIONS ==');
chk('a modelled stair is recorded as a vertical connection',
    villa.walkability.vertical_connections.length>0
    &&villa.walkability.vertical_connections.every(v=>v.kind==='STAIR'));
chk('every vertical connection names its source element',
    villa.walkability.vertical_connections.every(v=>!!v.source_element_id));
chk('no lift or escalator operation is claimed',
    villa.walkability.vertical_connections.every(v=>/no lift or escalator/.test(v.note))
    &&JSON.stringify(villa.walkability.vertical_connections).indexOf('elevator')<0);
chk('a model with no stair reports none',
    RS('clinic').walkability.vertical_connections.length===0);

console.log('\n──────────────────────────────────────────────');
console.log('PORTALS: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
