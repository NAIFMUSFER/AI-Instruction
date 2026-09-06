require('playwright');                    /* وجودُ الحزمة شرطٌ صريح */
const path=require('path'), os=require('os');
const {execFileSync}=require('child_process');
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js):
   النداء المباشر chromium.launch() يطلب البناء الذي تتوقّعه نسخة
   Playwright بالرقم، فينجح حيث جرى `playwright install` ويفشل حيث
   تحمل الصورة بناءً آخر. المُحدِّد يجيب السؤال مرّة واحدة لكل بيئة. */
const PW=require(path.resolve(__dirname,'..','..','..','tools','pw_chromium.js'));

const suite=process.argv[2];
const HERE=__dirname;

execFileSync(
  process.execPath,
  [path.join(HERE,'build_browser_page.js'),suite],
  {stdio:'inherit'}
);

const page=path.join(
  os.tmpdir(),
  path.basename(suite,'.js')+'_browser.html'
);

(async()=>{
  const b=await PW.launch();

  b.on('disconnected',()=>{
    console.log('DIAG: BROWSER DISCONNECTED');
  });

  const pg=await b.newPage();

  const errs=[];
  const consoleErrors=[];
  const consoleLogs=[];

  pg.on('close',()=>{
    console.log('DIAG: PAGE CLOSED');
  });

  pg.on('crash',()=>{
    console.log('DIAG: PAGE CRASHED');
  });

pg.on('pageerror',e=>{
  errs.push(e.message);
  console.log('DIAG: PAGE ERROR:', e.message);
  console.log('DIAG: PAGE ERROR STACK:', e.stack || '(no stack)');
});

  pg.on('console',msg=>{
    const text=msg.text();

    consoleLogs.push(
      '['+msg.type()+'] '+text
    );

    if(
      msg.type()==='error' ||
      msg.type()==='warning'
    ){
      consoleErrors.push(
        '['+msg.type()+'] '+text
      );
    }
  });

  const TMO=600000;

  pg.setDefaultTimeout(TMO);
  pg.setDefaultNavigationTimeout(TMO);

  await pg.goto(
    'file://'+page,
    {waitUntil:'load'}
  );

  console.log(
    'DIAG: page loaded:',
    await pg.evaluate('document.readyState')
  );

  console.log(
    'DIAG: __RESULT type:',
    await pg.evaluate('typeof window.__RESULT')
  );

  console.log(
    'DIAG: __LOG length:',
    await pg.evaluate(
      '(window.__LOG__||[]).length'
    )
  );

  try{
    await pg.waitForFunction(
      'window.__RESULT',
      null,
      {timeout:TMO}
    );
  }
  catch(e){
    let resultType='UNAVAILABLE';
    let resultValue=null;
    let browserLog=[];

    try{
      resultType=
        await pg.evaluate(
          'typeof window.__RESULT'
        );
    }catch(evalErr){
      console.log(
        'DIAG: result type unavailable:',
        evalErr.message
      );
    }

    try{
      resultValue=
        await pg.evaluate(
          'window.__RESULT || null'
        );
    }catch(evalErr){
      console.log(
        'DIAG: result value unavailable:',
        evalErr.message
      );
    }

    try{
      browserLog=
        await pg.evaluate(
          '(window.__LOG__||[]).slice(-100)'
        );
    }catch(evalErr){
      console.log(
        'DIAG: browser log unavailable:',
        evalErr.message
      );
    }

    console.log(
      'BROWSER (Chromium) '+
      path.basename(suite)+
      ': NOT VERIFIED'
    );

    console.log(
      'DIAG: wait error:',
      e.message
    );

    console.log(
      'DIAG: result type:',
      resultType
    );

    console.log(
      'DIAG: result value:',
      JSON.stringify(resultValue)
    );

    console.log(
      'DIAG: page errors:',
      errs.length
        ? errs.join(' | ')
        : 'none'
    );

    console.log(
      'DIAG: console errors/warnings:',
      consoleErrors.length
        ? consoleErrors.slice(-50).join('\n')
        : 'none'
    );

    console.log(
      'DIAG: window.__LOG__ tail:'
    );

    if(browserLog.length){
      console.log(
        browserLog.join('\n')
      );
    }else{
      console.log('(empty)');
    }

    console.log(
      'DIAG: Playwright console tail:'
    );

    if(consoleLogs.length){
      console.log(
        consoleLogs.slice(-100).join('\n')
      );
    }else{
      console.log('(empty)');
    }

    try{
      await b.close();
    }catch(_e){}

    process.exit(1);
  }

  const r=
    await pg.evaluate(
      'window.__RESULT'
    );

  const bad=
    await pg.evaluate(
      '(window.__LOG__||[]).filter(l=>/✗/.test(l))'
    );

  if(bad.length){
    console.log(
      bad.join('\n')
    );
  }

  console.log(
    'BROWSER (Chromium) '+
    path.basename(suite)+
    ':',
    JSON.stringify(r),
    'page errors:',
    errs.length
      ? errs.join(' | ')
      : 'none'
  );

  await b.close();

  process.exit(
    (r&&r.fail)||errs.length
      ? 1
      : 0
  );
})();