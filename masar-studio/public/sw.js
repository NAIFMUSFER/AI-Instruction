const CACHE='masar-4.1.0-shell-v2';
const SHELL=['/','/src/style.css','/src/app.js','/src/renderer.js','/src/storage.js','/shared/authoring.js','/shared/model.js','/shared/building.js','/shared/ifc.js','/shared/geometry.js','/public/favicon.svg','/public/manifest.webmanifest'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('masar-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 if(e.request.method!=='GET')return;
 const u=new URL(e.request.url);
 // Cache only the public app shell; never API responses, review tokens or account data.
 if(u.origin!==self.location.origin||!SHELL.includes(u.pathname))return;
 const key=u.pathname;
 e.respondWith(fetch(e.request).then(r=>{if(r.ok){const copy=r.clone();e.waitUntil(caches.open(CACHE).then(c=>c.put(key,copy)));}return r;}).catch(async()=>{const hit=await caches.match(key);return hit||new Response('Offline: app asset unavailable',{status:503,headers:{'Content-Type':'text/plain'}});}));
});
