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

const villa=RS('villa');

console.log('\n== NAVIGATION MODES AND CONTRACTS ==');
RT_NAVIGATION_MODES.forEach(m=>{
  const r=validateRuntimeNavigation(m,null,null);
  chk('mode '+m+' is accepted with a declared contract',
      r.valid&&r.mode===m&&r.contract!==null); });
['TELEPORT_MODE','walk ','', 'GOD', null, undefined, 42].forEach(m=>{
  chk('unknown mode '+JSON.stringify(m)+' fails deterministically',
      codes(validateRuntimeNavigation(m,null,null)).indexOf('NAVIGATION_MODE_INVALID')>=0); });
chk('an unknown mode never silently falls back to a valid one',
    validateRuntimeNavigation('GOD',null,null).mode===null);

console.log('\n== WALK CONTRACT ==');
const walk=RT_NAVIGATION_CONTRACTS.WALK;
chk('WALK declares gravity true', walk.gravity===true);
chk('WALK declares collision true', walk.collision===true);
chk('WALK requires a walkable surface', walk.requires_walkable_surface===true);
chk('WALK requires a capsule', walk.requires_capsule===true);
chk('WALK is not vertically free', walk.vertical_free===false);
chk('WALK takes no orbit target',
    codes(validateRuntimeNavigation('WALK',{kind:'ROOM',id:'x'},villa))
      .indexOf('NAVIGATION_TARGET_INVALID')>=0);

console.log('\n== FLY CONTRACT ==');
const fly=RT_NAVIGATION_CONTRACTS.FLY;
chk('FLY declares gravity false', fly.gravity===false);
chk('FLY allows vertical movement', fly.vertical_free===true);
chk('FLY declares its own collision policy explicitly',
    typeof fly.collision==='boolean');
chk('FLY does not silently inherit WALK behaviour',
    JSON.stringify(fly)!==JSON.stringify(walk)
    &&fly.gravity!==walk.gravity&&fly.requires_walkable_surface!==walk.requires_walkable_surface);
chk('FIRST_PERSON keeps collision but not gravity',
    RT_NAVIGATION_CONTRACTS.FIRST_PERSON.collision===true
    &&RT_NAVIGATION_CONTRACTS.FIRST_PERSON.gravity===false);

console.log('\n== ORBIT TARGETS ==');
chk('ORBIT is targeted', RT_NAVIGATION_CONTRACTS.ORBIT.targeted===true);
chk('BUILDING is a valid orbit target',
    validateRuntimeNavigation('ORBIT',{kind:'BUILDING'},villa).valid);
chk('a real room is a valid orbit target',
    validateRuntimeNavigation('ORBIT',{kind:'ROOM',id:villa.rooms[0].space_id},villa).valid);
chk('a real object is a valid orbit target',
    validateRuntimeNavigation('ORBIT',
      {kind:'OBJECT',id:villa.objects[0].runtime_object_id},villa).valid);
chk('a real floor is a valid orbit target',
    validateRuntimeNavigation('ORBIT',
      {kind:'FLOOR',id:villa.rooms[0].level_index},villa).valid);
chk('an unknown target kind is refused',
    codes(validateRuntimeNavigation('ORBIT',{kind:'GALAXY',id:'x'},villa))
      .indexOf('NAVIGATION_TARGET_INVALID')>=0);
chk('an unknown room id is refused',
    codes(validateRuntimeNavigation('ORBIT',{kind:'ROOM',id:'nope'},villa))
      .indexOf('NAVIGATION_TARGET_INVALID')>=0);
chk('an unknown object id is refused',
    codes(validateRuntimeNavigation('ORBIT',{kind:'OBJECT',id:'nope'},villa))
      .indexOf('NAVIGATION_TARGET_INVALID')>=0);
chk('an unknown floor is refused',
    codes(validateRuntimeNavigation('ORBIT',{kind:'FLOOR',id:99},villa))
      .indexOf('NAVIGATION_TARGET_INVALID')>=0);
chk('PLAN and DOLLHOUSE are targeted modes',
    RT_NAVIGATION_CONTRACTS.PLAN.targeted===true
    &&RT_NAVIGATION_CONTRACTS.DOLLHOUSE.targeted===true);

console.log('\n== NAVIGATION IN RUNTIME STATE ==');
chk('the state records the requested mode',
    createRuntimeState(villa,'FLY').navigation_mode==='FLY');
chk('an invalid mode falls back to the declared default and reports it', (function(){
  const s=createRuntimeState(villa,'GOD');
  return s.navigation_mode===RT_DEFAULT_NAV
    &&s.issues.some(i=>i.code==='NAVIGATION_MODE_INVALID'); })());
chk('the default mode comes from the specification',
    createRuntimeState(villa).navigation_mode===ACS_RUNTIME_SPEC.default_navigation_mode);
chk('changing navigation mode never touches the scene', (function(){
  const s=RS('villa'); const before=JSON.stringify(s);
  RT_NAVIGATION_MODES.forEach(m=>createRuntimeState(s,m));
  return JSON.stringify(s)===before; })());

console.log('\n──────────────────────────────────────────────');
console.log('NAVIGATION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
