const {chromium}=require('playwright');
const path=require('path'), os=require('os');
const {execFileSync}=require('child_process');
const suite=process.argv[2];
const HERE=__dirname;
execFileSync(process.execPath,[path.join(HERE,'build_browser_page.js'),suite],
  {stdio:'inherit'});
const page=path.join(os.tmpdir(),path.basename(suite,'.js')+'_browser.html');
(async()=>{
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
  const pg=await b.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push(e.message));
  /* الصفحة المولَّدة تجاوزت 9MB بعد إضافة طبقة العرض؛ المهلة تُضبط على مستوى
     الصفحة لأن waitForFunction يأخذ وسيطه الثاني قيمةً تُمرَّر للدالّة لا خيارات */
  const TMO=600000;
  pg.setDefaultTimeout(TMO); pg.setDefaultNavigationTimeout(TMO);
  await pg.goto('file://'+page,{waitUntil:'load'});
  try{ await pg.waitForFunction('window.__RESULT'); }
  catch(e){
    console.log('BROWSER (Chromium) '+path.basename(suite)+': NOT VERIFIED — the page '
      +'never reported a result'+(errs.length?(' — page errors: '+errs.join(' | '))
      :' and raised no page error'));
    await b.close(); process.exit(1); }
  const r=await pg.evaluate('window.__RESULT');
  const bad=await pg.evaluate('(window.__LOG__||[]).filter(l=>/✗/.test(l))');
  if(bad.length) console.log(bad.join('\n'));
  console.log('BROWSER (Chromium) '+path.basename(suite)+':',JSON.stringify(r),
              'page errors:',errs.length?errs.join(' | '):'none');
  await b.close();
  process.exit((r&&r.fail)||errs.length?1:0);
})();
