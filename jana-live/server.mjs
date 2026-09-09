import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {extname,normalize} from 'node:path';
const PORT=Number(process.env.PORT||10000);
const ROOT=new URL('./public/',import.meta.url);
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'};
const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');
    if(u.pathname==='/health'){res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({ok:true,service:'jana-live'}));}
    let path=u.pathname==='/'?'index.html':u.pathname.replace(/^\//,'');
    path=normalize(path).replace(/^\.\.(\/|\\|$)/,'');
    const data=await readFile(new URL(path,ROOT));
    res.writeHead(200,{'content-type':mime[extname(path)]||'application/octet-stream','x-content-type-options':'nosniff','referrer-policy':'strict-origin-when-cross-origin'});res.end(data);
  }catch{res.writeHead(404,{'content-type':'text/plain; charset=utf-8'});res.end('Not found');}
});
server.listen(PORT,'0.0.0.0',()=>console.log('JANA live on',PORT));
