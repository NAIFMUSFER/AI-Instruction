/* One route owner: private project review does not allocate the legacy GPU scene. */
let loading=null;
/* The awaits below keep evaluation order, but each one also waited for its own
   network fetch: 25 round trips in series (about 14 s of latency alone on a
   slow mobile link). modulepreload fetches and parses every module of the WebGL
   route in parallel up front; evaluation order is unchanged. Same origin only,
   so script-src 'self' already allows it. The list mirrors tools/frontend_local.txt
   (WebGL route only; the software fallback stays on demand). */
const LOCAL_ROUTE=['../core/stairs.mjs','../core/apartment-door-pairs.mjs','../core/context-details.mjs',
  '../core/viewer.js','../core/standards.js','../core/roof.mjs','../core/local-apartment.mjs','../core/disciplines.js',
  '../generated/runtime.js','../generated/authoring.js','../generated/pbr.js','../render/scene.js',
  '../render/warehouse-canonical-identity.js','../render/guest-presentation.mjs','../generated/pbr-bridge.js',
  '../ui/tap-gesture.mjs','../ui/workspace-ui-wiring.js','../trust/core.js','../trust/wiring.js','../ui/panels-entry.js',
  '../ui/workspace-viewport-selection.js','../ui/workspace-viewport-selection-runtime.js',
  '../ui/residential-quality.js','../ui/generation-jobs.js','../ui/guest-floor-plan.mjs','../ui/guest-room-card.mjs',
  '../ui/guest-projects.mjs','../ui/guest-workspace.js'];
const LOCAL_ROUTE_VENDOR=['three/addons/webxr/VRButton.js','three/addons/webxr/ARButton.js',
  'three/addons/exporters/GLTFExporter.js','three/addons/objects/Sky.js'];
function preloadLocalRoute(){
  const urls=LOCAL_ROUTE.map(spec=>new URL(spec,import.meta.url).href);
  for(const spec of LOCAL_ROUTE_VENDOR){try{urls.push(import.meta.resolve(spec));}catch{}}
  for(const href of urls){
    const link=document.createElement('link');link.rel='modulepreload';link.href=href;
    document.head.append(link);
  }
}
function loadLocalStudio(){
  if(loading)return loading;
  preloadLocalRoute();
  loading=(async()=>{
    await import('../core/stairs.mjs');
    await import('../core/apartment-door-pairs.mjs');
    await import('../core/context-details.mjs');
    await import('../core/viewer.js');
    await import('../core/standards.js');
    await import('../core/roof.mjs');
    await import('../core/local-apartment.mjs');
    await import('../core/disciplines.js');
    await import('../generated/runtime.js');
    await import('../generated/authoring.js');
    await import('../generated/pbr.js');
    await import('../render/scene.js');
    await import('../render/warehouse-canonical-identity.js');
    await import('../render/guest-presentation.mjs');
    await import('../generated/pbr-bridge.js');
    await import('../ui/tap-gesture.mjs');
    await import('../ui/workspace-ui-wiring.js');
    await import('../trust/core.js');
    await import('../trust/wiring.js');
    await import('../ui/panels-entry.js');
    await import('../ui/workspace-viewport-selection.js');
    await import('../ui/workspace-viewport-selection-runtime.js');
    await import('../ui/residential-quality.js');
    await import('../ui/generation-jobs.js');
    await import('../ui/guest-floor-plan.mjs');
    await import('../ui/guest-room-card.mjs');
    await import('../ui/guest-projects.mjs');
    await import('../ui/guest-workspace.js');
  })().catch(async error=>{
    if(window.ACS_AUTH?.guestProjectId){
      await import('../trust/guest-draft-store.mjs');
      await import('../render/guest-software-view.mjs');
      const software = await import('../ui/guest-software-studio.mjs');
      return software.openGuestSoftwareStudio();
    }
    window.ACS?.guestBootFailure?.();
    const status=document.getElementById('status');if(status)status.textContent='تعذّر تشغيل المشهد المحلي. أعد المحاولة أو استخدم المخطط البديل.';
    throw error;
  });
  return loading;
}
if(window.ACS?.guest||window.ACS_AUTH?.isLocalTestHost?.())loadLocalStudio().catch(()=>{});
document.addEventListener('acs:guest',()=>loadLocalStudio().catch(()=>{}));
