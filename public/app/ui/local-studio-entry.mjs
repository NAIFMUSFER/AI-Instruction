/* One route owner: private project review does not allocate the legacy GPU scene. */
let loading=null;
function loadLocalStudio(){
  if(loading)return loading;
  loading=(async()=>{
    await import('../core/stairs.mjs');
    await import('../core/context-details.mjs');
    await import('../core/viewer.js');
    await import('../core/standards.js');
    await import('../core/roof.mjs');
    await import('../core/disciplines.js');
    await import('../generated/runtime.js');
    await import('../generated/authoring.js');
    await import('../generated/pbr.js');
    await import('../render/scene.js');
    await import('../render/warehouse-canonical-identity.js');
    await import('../generated/pbr-bridge.js');
    await import('../ui/workspace-ui-wiring.js');
    await import('../trust/core.js');
    await import('../trust/wiring.js');
    await import('../ui/panels-entry.js');
    await import('../ui/workspace-viewport-selection.js');
    await import('../ui/workspace-viewport-selection-runtime.js');
    await import('../ui/residential-quality.js');
    await import('../ui/generation-jobs.js');
    await import('../ui/guest-workspace.js');
  })().catch(error=>{
    window.ACS?.guestBootFailure?.();
    const status=document.getElementById('status');if(status)status.textContent='تعذّر تشغيل المشهد المحلي. أعد المحاولة أو استخدم المخطط البديل.';
    throw error;
  });
  return loading;
}
if(window.ACS?.guest||window.ACS_AUTH?.isLocalTestHost?.())loadLocalStudio().catch(()=>{});
document.addEventListener('acs:guest',()=>loadLocalStudio().catch(()=>{}));
