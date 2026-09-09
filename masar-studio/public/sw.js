const CACHE='masar-4.1.0-shell-v7-plan-inspection';
const SHELL=['/','/src/style.css','/src/app.js','/src/renderer.js','/src/storage.js','/src/render-ui.js','/src/plan-inspection.js','/shared/render-scene.js','/shared/authoring.js','/shared/model.js','/shared/layout-quality.js','/shared/building.js','/shared/ifc.js','/shared/geometry.js','/public/favicon.svg','/public/manifest.webmanifest'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('masar-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 if(e.request.method!=='GET')return;
 const u=new URL(e.request.url);
 // Cache only query-free public shell requests. A cloned Response also retains
 // its original URL; stripping a token from the cache key alone is not sufficient.
 if(u.origin!==self.location.origin||u.search||!SHELL.includes(u.pathname))return;
 const key=u.pathname;
 e.respondWith(fetch(e.request).then(r=>{if(r.ok){const copy=r.clone();e.waitUntil(caches.open(CACHE).then(c=>c.put(key,copy)));}return r;}).catch(async()=>{const hit=await caches.match(key);return hit||new Response('Offline: app asset unavailable',{status:503,headers:{'Content-Type':'text/plain'}});}));
});
