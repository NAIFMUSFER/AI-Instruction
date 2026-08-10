/* ============================================================================
   إقلاع الصفحة في متصفح حقيقي — علاج المرحلة 9.2 الإنتاجي (§8).

   usage:
     node tests/deploy/verify_page_boot.js                 # يخدم public/ محلياً
     node tests/deploy/verify_page_boot.js <https://url>   # ضد النشر الحقيقي

   يتحقق فعلياً — لا فحوص نصية:
     - الصفحة تُحمَّل بلا أخطاء
     - سكربت الوحدة نُفِّذ (THREE استُورد) عبر مصدّرات window.ACS من نطاق الوحدة
     - window.ACS.ready أصبح true (منارة الإقلاع التي يطفئها فشل المحرّك)
     - renderer/scene/camera أُنشئت: كانفس بأبعاد غير صفرية + حدود مشهد منتهية
       من pbrBounds (لا تُحسب إلا من مشهد فيه أطفال)
     - البكسلات ليست سواداً موحّداً (لقطة فعلية تُفحص بالتباين)

   محلياً بلا public/vendor مُعبَّأ: توقف صريح exit 2 —
   NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED. لا نجاح مزيَّف أبداً.
   ========================================================================== */
const fs=require('fs'), path=require('path'), http=require('http');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const PUB=path.join(ROOT,'public');
const TARGET=process.argv[2]||null;
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n))
  :(fail++,console.log('  ✗',n,d===undefined?'':d))};

function serve(){
  const MIME={'.html':'text/html','.js':'text/javascript',
    '.mjs':'text/javascript','.css':'text/css','.json':'application/json',
    '.png':'image/png','.svg':'image/svg+xml'};
  return new Promise(res=>{
    const srv=http.createServer((rq,rs)=>{
      const u=decodeURIComponent(rq.url.split('?')[0]);
      let p=path.normalize(path.join(PUB,u==='/'?'index.html':u));
      if(!p.startsWith(PUB)||!fs.existsSync(p)
         ||fs.statSync(p).isDirectory()){
        rs.writeHead(404); rs.end('not found'); return; }
      rs.writeHead(200,{'Content-Type':
        MIME[path.extname(p)]||'application/octet-stream'});
      fs.createReadStream(p).pipe(rs); });
    srv.listen(0,'127.0.0.1',()=>res(srv)); });
}

(async()=>{
  if(!TARGET){
    const three=path.join(PUB,'vendor','three@0.160.0','build',
      'three.module.js');
    if(!fs.existsSync(three)||fs.statSync(three).size<100000){
      console.log('PAGE BOOT: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
      console.log('  needs: vendored Three.js (sh tools/vendor.sh on a '
        +'networked machine), or pass a deployed URL as the argument.');
      process.exit(2); } }
  let chromium;
  try{ ({chromium}=require('playwright')); }
  catch(e){
    console.log('PAGE BOOT: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
    console.log('  needs: playwright'); process.exit(2); }
  const srv=TARGET?null:await serve();
  const base=TARGET||('http://127.0.0.1:'+srv.address().port+'/index.html');
  const b=await chromium.launch();
  const pg=await b.newPage({viewport:{width:1280,height:800}});
  const errs=[],bad=[];
  pg.on('pageerror',e=>errs.push(String(e.message).slice(0,200)));
  pg.on('response',r=>{ if(r.status()>=400)
    bad.push('HTTP '+r.status()+' '+r.url().slice(0,110)); });
  try{ await pg.goto(base,{waitUntil:'load',timeout:90000}); }
  catch(e){
    console.log('PAGE BOOT: NOT VERIFIED — the target could not be loaded '
      +'from this environment: '+String(e.message).slice(0,150));
    await b.close(); if(srv) srv.close(); process.exit(2); }
  chk('the page loaded', true);
  let ready=false;
  try{ await pg.waitForFunction('window.ACS&&window.ACS.ready===true',
      null,{timeout:30000}); ready=true; }catch(e){}
  chk('the engine boot beacon window.ACS.ready is true (module executed, '
      +'THREE imported)', ready);
  const st=await pg.evaluate(()=>{
    const c=document.querySelector('canvas');
    let bounds=null;
    try{ bounds=(window.ACS&&window.ACS.pbrBounds)
      ?window.ACS.pbrBounds():null; }catch(e){ bounds={err:String(e)}; }
    return {canvas:c?{w:c.width,h:c.height}:null,
      pbr:!!(window.ACS&&window.ACS.pbrApply),
      ad:!!(window.ACS&&window.ACS.adApply),
      warn:(function(){ const w=document.getElementById('engineWarn');
        return w?getComputedStyle(w).display!=='none':null; })(),
      bounds:bounds}; });
  chk('a renderer canvas exists with non-zero size',
      !!st.canvas&&st.canvas.w>0&&st.canvas.h>0,JSON.stringify(st.canvas));
  chk('the 9.1 and 9.2 bridges are live on the page',
      st.pbr&&st.ad);
  chk('the scene has children — finite canonical bounds from pbrBounds',
      !!st.bounds&&typeof st.bounds.radius==='number'
      &&isFinite(st.bounds.radius)&&st.bounds.radius>0,
      JSON.stringify(st.bounds));
  chk('the engine-failure warning is NOT displayed', st.warn===false,
      String(st.warn));
  const shot=await pg.screenshot();
  const png=shot;
  let varied=false;
  /* عيّنة خام كافية: أي أرشيف PNG لمشهد حقيقي يتجاوز حجم لقطة سوداء موحّدة
     بفارق كبير، والتباين يُفحص من حجم الضغط + بايتات متفرقة */
  varied=png.length>25000
    &&new Set(Array.from(png.slice(1000,4000))).size>16;
  chk('the viewport is not a uniform black frame (actual pixels captured)',
      varied,'png '+png.length+' bytes');
  chk('no page errors', errs.length===0, errs.join(' | '));
  chk('no failed asset requests', bad.length===0, bad.slice(0,5).join(' | '));
  await b.close(); if(srv) srv.close();
  console.log('\nPAGE BOOT: '+pass+' passed, '+fail+' failed  ('+base+')');
  process.exit(fail?1:0);
})();
