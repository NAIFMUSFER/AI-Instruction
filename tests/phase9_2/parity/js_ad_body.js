/* جانب جافاسكربت من تكافؤ المرحلة 9.2 — يكرّر py_ad.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_AD_JS)
  ||path.join(_tmp,'acs_parity_ad_js.json');

const SURFACES=[
  [{id:'w1',role:'exterior_wall'},{id:'w2',role:'exterior_wall'},
   {id:'p1',role:'parapet'}],
  [{id:'w1',role:'exterior_wall'}],
  [],null];
const BOUNDS=[
  {cx:7,cy:3,cz:6.5,radius:14,min_y:0},
  {cx:20,cy:15,cz:12,radius:60,min_y:0},
  {},null];
const TEXTS=[
  'واجهة حجر طبيعي بيج مع لمسات رمادية وزجاج عاكس',
  'إنارة LED مخفية وبلكونات أكبر ومواقف أمامية وخلفية',
  'حديقة أمامية بها نخيل وشجيرات',
  'مطبخ L أو U حسب الدور',
  'دور إضافي مع كسوة خشب','nothing matches here','',null];

const out={};
out.materials={};
Object.keys(AD_MATERIALS).sort(_scmp).forEach(m=>{ out.materials[m]=adMaterial(m); });
out.material_bad=[adMaterial('nope'),
  adMaterial('stone_beige',JSON.parse('{"__proto__":1}')),
  adMaterial('stone_beige',{roughness:99}),
  adMaterial('stone_beige',{base_color:'beige'}),
  adMaterial('stone_beige',{roughness:0.41,base_color:'#D6C7AB'}),
  adMaterial('led_strip',{emissive_intensity:2.0})];
out.variation=[0,1,2,3,4,5].map(i=>adVariation('h1','e'+i,'stone_beige'))
  .concat([adVariation('h2','e0','wood_accent')]);
out.profiles=[];
['DETAIL_OFF','DETAIL_STANDARD','DETAIL_HIGH','NOPE'].forEach(p=>{
  [false,true].forEach(m=>{ out.profiles.push(adDetailProfile(p,m)); }); });
out.classes=['CANONICAL_GEOMETRY','DERIVED_PRESENTATION_DETAIL',
  'REQUESTED_PRESENTATION_DETAIL','DEFAULT_PRESENTATION_CONTEXT',
  'UNRESOLVED','MADE_UP'].map(adClassifyDetail);
out.authority=[];
[{canonical:true},{requested:true},{context:true},{},null].forEach(o=>{
  [false,true].forEach(c=>{ out.authority.push(adObjectAuthority(o,c)); }); });
out.zoning=[];
SURFACES.forEach(s=>{
  [{primary:'stone_beige',accent:'panel_gray'},{primary:'stone_beige'},
   {accent:'wood_accent'},{primary:'granite'},{},null].forEach(r=>{
    out.zoning.push(adFacadeZoning(s,r)); }); });
out.windows=[];
[{width:1.4,height:1.4,sill:0.9,id:'W1'},{width:0.6,height:0.5},
 {width:4.0,height:2.8},{width:0,height:1},{},null].forEach(o=>{
  [null,'dark','gray','light','gold'].forEach(f=>{
    out.windows.push(adWindowAssembly(o,f)); }); });
out.doors=[{material:'door'},{material:'door_glass'},{material:'dockdoor'},
  {kind:'door',entrance:true},{material:'mystery'},{},null]
  .map(adDoorVisual);
out.balconies=[];
[true,false].forEach(r=>{ [true,false].forEach(q=>{
  out.balconies.push(adBalconyVisual(r,q)); }); });
out.leds=[];
['facade_strip','entrance_wash','disco_ball'].forEach(k=>{
  [{represented:true,id:'WALL|x'},{represented:false},{},null].forEach(h=>{
    out.leds.push(adLed(k,h)); }); });
out.staging=[];
['STAGING_OFF','STAGING_REQUESTED_ONLY','STAGING_PRESENTATION_DEFAULT',
 'STAGING_PARTY'].forEach(m=>{
  [[[{kind:'sofa',id:'o1'}],[{kind:'bed',id:'o2'}]],[[],[]],[null,null]]
    .forEach(rc=>{ out.staging.push(adStagingPlan(m,rc[0],rc[1])); }); });
out.recipes=['car','suv','pickup','van','truck','delivery_truck','bus',
  'forklift','reach_truck','pallet_jack','order_picker','stacker','tree',
  'palm','shrub','hedge','planter','sofa','bed','wardrobe',
  'warehouse_rack','pallet','carton','bollard','wheel_stop','traffic_cone',
  'parking_bay','crane_proxy','dragon']
  .map(k=>adObjectRecipe(k,null,null,null));
out.recipes_dims=[
  adObjectRecipe('car',[2,5,1.5],null,null),
  adObjectRecipe('car',[2,5,1.5],[1.9,4.6,1.5],null),
  adObjectRecipe('car',[2,5,0],null,null),
  adObjectRecipe('forklift',null,null,'REACH_TRUCK'),
  adObjectRecipe('forklift',null,null,'HOVERBOARD')];
out.placements=[{canonical_pos:[1,0,2]},{user_pos:[3.5,0,'4']},
  {zone:{x:0,z:0,w:10,d:5},index:2,of:10},{zone:{x:0,z:0,w:10}},
  {kind:'car'},{},null].map(adPlacement);
const mkBays=n=>{ const a=[]; for(let i=0;i<n;i++) a.push({id:'b'+i});
  return a; };
out.bays=[adVehiclesToBays(10,mkBays(10)),adVehiclesToBays(10,mkBays(6)),
  adVehiclesToBays(0,[]),adVehiclesToBays(3,null),
  adVehiclesToBays('x',[{id:'b0'}])];
out.parking=[];
[true,false].forEach(r=>{ [8,0,null].forEach(c=>{
  out.parking.push(adParking(r,c)); }); });
out.kitchens=[];
[true,null].forEach(t=>{ ['L','U','T',null].forEach(c=>{
  out.kitchens.push(adKitchenLayout(t,c)); }); });
out.environments=['NEUTRAL_STUDIO','CLEAR_SKY','OVERCAST_SKY','SUNSET_SKY',
  'MARS_SKY'].map(adEnvironment);
out.cameras=[];
Object.keys(AD_CAMERAS).sort(_scmp).concat(['EXTERIOR_HERO','NOPE'])
  .forEach(p=>{ BOUNDS.forEach(b=>{ out.cameras.push(adCamera(p,b)); }); });
out.auto=[{type:'warehouse'},{type:'villa'},{type:'clinic'},{type:'hotel'},
  {type:'office'},{type:'spaceship'},{indoor:true},{},null]
  .map(adAutoPresentation);
out.interpret=TEXTS.map(adInterpret);
const _req=adInterpret(TEXTS[0]).intents.concat(adInterpret(TEXTS[1]).intents);
const _ms=[{exterior_walls:4,windows:6,accent_band:1,balcony:true,
    parking_bays:4,kitchen_layout:'L',
    objects:[{kind:'sofa',canonical:true},{kind:'forklift',requested:true},
      {kind:'tree',context:true},{kind:'ghost'}],
    context_enabled:true},
  {exterior_walls:0,windows:0},{},null];
out.diagnostics=_ms.map(m=>adDiagnostic(_req,m));
out.coverage=out.diagnostics.map(adCoverage).concat([adCoverage(null)]);
out.configs=[
  adConfig('DETAIL_HIGH','REQUESTED','SITE','STAGING_REQUESTED_ONLY',
    'EXTERIOR_HERO_FRONT','CLEAR_SKY',null,false,_req,_ms[0]),
  adConfig('DETAIL_STANDARD','REALISTIC','LANDSCAPE',
    'STAGING_PRESENTATION_DEFAULT','WAREHOUSE_AISLE','SUNSET_SKY',
    null,true,[],{}),
  adConfig(null,null,null,null,null,null,null,false,null,null),
  adConfig('DETAIL_MEGA',null,null,null,null,null,null,false,null,null),
  adConfig('DETAIL_OFF','CARTOON',null,null,null,null,null,false,null,null),
  adConfig('DETAIL_OFF',null,'MOON',null,null,null,null,false,null,null)];
const _cfg=out.configs[0].config;
const _pbr=pqConfig('HIGH','CLEAR_NOON','REALISTIC','SKY',1.1,null,
  null,BOUNDS[0]).config;
out.captures=[
  adCaptureMetadata(_pbr,_cfg,'hash_abc',7,1920,1080,null),
  adCaptureMetadata(_pbr,null,'hash_abc',null,800,600,null),
  adCaptureMetadata(null,_cfg,'h',1,320,240,null)];
out.spec_view={schema:ACS_ARCHDETAIL_SPEC.schema,
  version:ACS_ARCHDETAIL_SPEC.version,
  materials:Object.keys(AD_MATERIALS).sort(_scmp),
  cameras:Object.keys(AD_CAMERAS).sort(_scmp),
  classes:Object.keys(ACS_ARCHDETAIL_SPEC.detail_classes).sort(_scmp)};

fs.writeFileSync(OUT,JSON.stringify(out));
console.log('parity written: '+Object.keys(out).length+' groups');
