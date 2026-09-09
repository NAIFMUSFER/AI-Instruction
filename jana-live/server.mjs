import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {extname,normalize} from 'node:path';
const PORT=Number(process.env.PORT||10000);
const ROOT=new URL('./public/',import.meta.url);
const EDGE=(process.env.JANA_EDGE_BASE||'https://jjdsajiwoqanefmnikls.supabase.co/functions/v1/jana-api').replace(/\/$/,'');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.webmanifest':'application/manifest+json'};
const hop=new Set(['connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailers','transfer-encoding','upgrade','host','content-length']);
async function proxy(req,res,u){
  const edgePath=u.pathname.replace(/^\/api(?=\/|$)/,'')||'/';
  const target=EDGE+edgePath+u.search;
  const headers={}; for(const [k,v] of Object.entries(req.headers)) if(v!==undefined&&!hop.has(k.toLowerCase())) headers[k]=v;
  const chunks=[]; for await(const c of req) chunks.push(c); const body=chunks.length?Buffer.concat(chunks):undefined;
  const r=await fetch(target,{method:req.method,headers,body,redirect:'manual'});
  const out={}; r.headers.forEach((v,k)=>{if(!hop.has(k.toLowerCase())&&k.toLowerCase()!=='set-cookie')out[k]=v;});
  out['cache-control']='no-store';out['x-content-type-options']='nosniff';
  res.writeHead(r.status,out);res.end(Buffer.from(await r.arrayBuffer()));
}
const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');
    if(u.pathname==='/edge-health')return proxy(req,res,new URL('/api/health','http://localhost'));
    if(u.pathname==='/health'){res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'});return res.end(JSON.stringify({ok:true,service:'jana-live'}));}
    if(u.pathname==='/ready'){res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'});return res.end(JSON.stringify({ok:true,service:'jana-live'}));}
    if(u.pathname.startsWith('/api/')) return proxy(req,res,u);
    let path=u.pathname==='/'?'index.html':u.pathname.replace(/^\//,'');
    path=normalize(path).replace(/^\.\.(\/|\\|$)/,'');
    const data=await readFile(new URL(path,ROOT));
    res.writeHead(200,{'content-type':mime[extname(path)]||'application/octet-stream','x-content-type-options':'nosniff','referrer-policy':'strict-origin-when-cross-origin','content-security-policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"});res.end(data);
  }catch(e){console.error('gateway',e?.message||e);res.writeHead(502,{'content-type':'application/json; charset=utf-8','cache-control':'no-store'});res.end(JSON.stringify({error:'gateway_error'}));}
});
server.listen(PORT,'0.0.0.0',async()=>{console.log('JANA live on',PORT);try{const h=await fetch(EDGE+'/health',{cache:'no-store'});const c=await fetch(EDGE+'/config',{cache:'no-store'});const cfg=await c.json();const r=await fetch(EDGE+'/catalog',{cache:'no-store'});const data=await r.json();const s=await fetch(EDGE+'/slots',{cache:'no-store'});const slots=await s.json();console.log('JANA_EDGE_SELFTEST',JSON.stringify({health_status:h.status,config_status:c.status,catalog_status:r.status,slots_status:s.status,brand:cfg.brand||null,catalog_count:Array.isArray(data)?data.length:null,slot_count:Array.isArray(slots)?slots.length:null}));}catch(e){console.error('JANA_EDGE_SELFTEST_FAIL',e?.message||e);}});
