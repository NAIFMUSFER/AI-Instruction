/* يبني صفحة اختبار حقيقية للمتصفّح من نفس مصدر المتصفّح (pure_audit) ونفس ملف
   الاختبار الذي يُشغَّل في Node — بلا نسخة ثانية من المنطق. */
const fs=require('fs'),path=require('path'),os=require('os');
const {execFileSync}=require('child_process');
const suite=process.argv[2];
const HERE=__dirname, REPO=path.resolve(HERE,'..','..','..');

/* مجلّد الجناح يُشتقّ من مسار الملفّ نفسه، كي تعمل أجنحة أي مرحلة لا المرحلة 3 وحدها */
const PHASE=path.isAbsolute(suite)?path.dirname(suite):path.resolve(HERE,'..');
const FIXDIR=path.join(PHASE,'fixtures');

const files={};

const keyPath=(p)=>String(p).split(path.sep).join('/');

/* تجهيزات كل مرحلة تُقدَّم بمسارها الحقيقي وباسمها المجرّد معاً، كي يعمل
   أي اختبار أياً كان المجلّد الذي يقرأ منه */
const TESTS=path.resolve(REPO,'tests');

fs.readdirSync(TESTS).forEach(d=>{
  const fd=path.join(TESTS,d,'fixtures');

  if(!fs.existsSync(fd)) return;

  fs.readdirSync(fd)
    .filter(f=>/\.json$/.test(f))
    .forEach(f=>{
      const t=fs.readFileSync(path.join(fd,f),'utf8');

      files[keyPath(path.join(fd,f))]=t;

      if(!(f in files)){
        files[f]=t;
      }
    });
});

/* صفحة التطبيق نفسها: القشرة — العلامة وخريطة الاستيراد. */
{
  const t=fs.readFileSync(
    path.join(REPO,'public','index.html'),
    'utf8'
  );

  files[keyPath(path.join(REPO,'public','index.html'))]=t;
  files['public/index.html']=t;
}

/* شيفرة التطبيق نفسها: بعد F-09 صارت وحدات ES تحت public/app/.
   كل ملفّ يُقدَّم بمساره المطلق وبمساره النسبي من جذر المستودع. */
(function addAppTree(dir){
  fs.readdirSync(dir)
    .sort()
    .forEach(f=>{
      const p=path.join(dir,f);

      if(fs.statSync(p).isDirectory()){
        return addAppTree(p);
      }

      const t=fs.readFileSync(p,'utf8');

      files[keyPath(p)]=t;
      files[path.relative(REPO,p).split(path.sep).join('/')]=t;
    });
})(
  path.join(REPO,'public','app')
);

/* المواصفات القانونية تُقدَّم بكل صيغة مسار قد يطلبها اختبار. */
fs.readdirSync(REPO)
  .filter(f=>/^acs_.*\.json$/.test(f))
  .forEach(f=>{
    const t=fs.readFileSync(path.join(REPO,f),'utf8');

    files[f]=t;
    files['./'+f]=t;
    files[keyPath(path.join(REPO,f))]=t;
    files[keyPath(path.join(PHASE,'..','..',f))]=t;
  });

/* مصادر بايثون تُقدَّم للصفحة أيضاً. */
fs.readdirSync(REPO)
  .filter(f=>/^acs_.*\.py$/.test(f))
  .forEach(f=>{
    const t=fs.readFileSync(path.join(REPO,f),'utf8');

    files[f]=t;
    files['./'+f]=t;
    files[keyPath(path.join(REPO,f))]=t;
  });

/* وحدات مساعدة داخل المستودع (lib_*.js) تُقدَّم للصفحة كي يعمل require المحلّي */
const mods={};

fs.readdirSync(TESTS).forEach(d=>{
  const dd=path.join(TESTS,d);

  if(!fs.statSync(dd).isDirectory()) return;

  fs.readdirSync(dd)
    .filter(f=>/^lib_.*\.js$/.test(f))
    .forEach(f=>{
      const t=fs.readFileSync(
        path.join(dd,f),
        'utf8'
      );

      mods[path.join(dd,f)]={
        src:t,
        dir:dd
      };

      mods[f]={
        src:t,
        dir:dd
      };
    });
});

const bundlePath=path.join(
  os.tmpdir(),
  'acs_browser_bundle.js'
);

execFileSync(
  process.execPath,
  [
    path.join(HERE,'extract_browser_bundle.js')
  ],
  {
    env:Object.assign(
      {},
      process.env,
      {ACS_BUNDLE:bundlePath}
    ),
    stdio:'pipe'
  }
);

const pure=fs.readFileSync(
  bundlePath,
  'utf8'
);

const testPath=
  path.isAbsolute(suite)
    ? suite
    : path.join(PHASE,suite);

let test=
  fs.readFileSync(
    testPath,
    'utf8'
  )

  /* تعريفات الوحدات تُزال: الصفحة تقدّم fs و path من الغلاف نفسه */
  .replace(
    /^\s*const\s+[A-Za-z_$][\w$]*\s*=\s*require\((['"])[^'"]+\1\)\s*(,\s*[A-Za-z_$][\w$]*\s*=\s*require\((['"])[^'"]+\3\)\s*)*;?\s*$/mg,
    ''
  )

  .replace(
    /^\s*const\s+\{[^}]*\}\s*=\s*require\(['"][^'"]+['"]\)\s*;?\s*$/mg,
    ''
  )

  .replace(
    /^\s*require\(['"][^'"]*\.js['"]\)\s*;?\s*$/mg,
    ''
  )

  .replace(
    /require\(['"]fs['"]\)/g,
    'fs'
  );


const shim=`
const __dirname=${JSON.stringify(PHASE)};
const __filename=${JSON.stringify(testPath)};

const _norm=(s)=>{
  s=String(s).replace(/\\\\/g,'/');

  const drive=/^[A-Za-z]:\\//.test(s);
  const abs=s.charAt(0)==='/'||drive;

  const out=[];

  s.split('/').forEach(seg=>{
    if(!seg||seg==='.') return;

    if(seg==='..'){
      if(
        out.length &&
        out[out.length-1]!=='..'
      ){
        out.pop();
      }else if(!abs){
        out.push('..');
      }

      return;
    }

    out.push(seg);
  });

  return (abs&&!drive?'/':'')+out.join('/');
};

const path={
  resolve:(...p)=>
    _norm(
      p.filter(Boolean).join('/')
    ),

  join:(...p)=>
    _norm(
      p.filter(Boolean).join('/')
    ),

  dirname:(p)=>
    _norm(String(p))
      .split('/')
      .slice(0,-1)
      .join('/')||'/',

  isAbsolute:(p)=>
    String(p).charAt(0)==='/' ||
    /^[A-Za-z]:\\//.test(String(p)),

  basename:(p)=>
    String(p)
      .replace(/\\\\/g,'/')
      .split('/')
      .pop()
};

const __FILES__=${JSON.stringify(files)};

window.__WROTE__={};

const fs={
  readFileSync:(p)=>{
    p=_norm(p);

    if(!(p in __FILES__)){
      throw new Error('ENOENT '+p);
    }

    return __FILES__[p];
  },

  existsSync:(p)=>{
    p=_norm(p);
    return p in __FILES__;
  },

  mkdirSync:(p,_opts)=>{
    p=_norm(p);
    return p;
  },

  writeFileSync:(p,t)=>{
    p=_norm(p);
    window.__WROTE__[String(p)]=String(t);
  }
};

const process={
  exit:()=>{},
  argv:[],
  env:{}
};

const _os={
  tmpdir:()=>'/tmp'
};

const os=_os;
const _np=path;

const __MODS__=${JSON.stringify(mods)};

const __MODCACHE__={};

const require=(m)=>{
  if(m==='fs') return fs;
  if(m==='path') return path;
  if(m==='os') return _os;

  const key=
    (String(m) in __MODS__)
      ? String(m)
      : path.basename(String(m));

  if(key in __MODS__){

    if(!(key in __MODCACHE__)){
      const e=__MODS__[key];

      const module={
        exports:{}
      };

      /*
        لا تُمرَّر fs و path كوسائط:
        الوحدة نفسها قد تعلنهما بـ const
      */
      (
        new Function(
          'module',
          'exports',
          'require',
          '__dirname',
          '__filename',
          e.src
        )
      )(
        module,
        module.exports,
        require,
        e.dir,
        path.join(e.dir,key)
      );

      __MODCACHE__[key]=module.exports;
    }

    return __MODCACHE__[key];
  }

  throw new Error('no module '+m);
};

/* عنصر التقرير الحقيقي في DOM حقيقي */
const __box=
  document.getElementById(
    'reportBox'
  );

window.__LOG__=[];

(function(){
  const o=console.log;

  console.log=function(){
    window.__LOG__.push(
      Array.from(arguments).join(' ')
    );

    o.apply(
      console,
      arguments
    );
  };
})();
`;


/* جسم الاختبار يعمل في نطاقه الخاص */
let body=
  shim+
  '\n'+
  pure+
  '\n(function(){\n'+
  test+
  '\nwindow.__RESULT={'+
    'pass:typeof pass!=="undefined"?pass:null,'+
    'fail:typeof fail!=="undefined"?fail:null'+
  '};\n'+
  '})();\n';


/*
  أي "</script" داخل نصّ أو JSON يقطع الوسم —
  نهرّبه دون تغيير قيمة أي سلسلة.
*/
body=
  body
    .replace(
      /<\/script/gi,
      '<\\/script'
    )
    .replace(
      /<!--/g,
      '<\\!--'
    )
    .replace(
      /\u2028/g,
      '\\u2028'
    )
    .replace(
      /\u2029/g,
      '\\u2029'
    );


/*
  كتل DOM والأنماط تُؤخذ من نفس المصدر المولَّد
  الذي يشحنه التطبيق.
*/
let wsDom='';
let wsCss='';

{
  const shell=
    fs.readFileSync(
      path.join(
        REPO,
        'public',
        'index.html'
      ),
      'utf8'
    );

  const appCss=
    fs.readFileSync(
      path.join(
        REPO,
        'public',
        'app',
        'styles',
        'app.css'
      ),
      'utf8'
    );

  const PANELS=[
    'WORKSPACE',
    'RENDER',
    'BIM',
    'DOCS',
    'PBR',
    'ARCH DETAIL'
  ];

  const cut=(
    src,
    open,
    close,
    where
  )=>{

    const a=
      src.indexOf(open);

    const b=
      src.indexOf(
        close
      );

    if(
      a<0 ||
      b<a
    ){
      throw new Error(
        'generated block missing from '+
        where+
        ': '+
        open
      );
    }

    return src.slice(
      a+open.length,
      b
    );
  };

  PANELS.forEach(name=>{

    wsDom+=
      cut(
        shell,
        '<!-- ===== ACS '+
          name+
          ' DOM (generated) ===== -->',
        '<!-- ===== END ACS '+
          name+
          ' DOM ===== -->',
        'public/index.html'
      );

    wsCss+=
      cut(
        appCss,
        '/* ===== ACS '+
          name+
          ' STYLES (generated) ===== */',
        '/* ===== END ACS '+
          name+
          ' STYLES ===== */',
        'public/app/styles/app.css'
      );
  });
}


/*
  Three.js الحقيقي المورّد محلياً.

  صفحة الاختبار تعمل عبر file:// داخل مجلد TEMP، ولذلك لا يمكن استخدام
  المسار production /vendor/... مباشرة بلا web server.

  نقرأ نفس نسخة Three.js 0.160.0 التي يعلنها public/index.html ونقدّمها
  للـimport map كـ data URL. لا CDN، لا شبكة، ولا stub وهمي.
*/
const THREE_MODULE=fs.readFileSync(
  path.join(
    REPO,
    'public',
    'vendor',
    'three@0.160.0',
    'build',
    'three.module.js'
  ),
  'utf8'
);

const THREE_DATA_URL=
  'data:text/javascript;base64,'+
  Buffer
    .from(THREE_MODULE,'utf8')
    .toString('base64');

const testImportMap=
  '<script type="importmap">'+
  JSON.stringify({
    imports:{
      three:THREE_DATA_URL
    }
  })+
  '<\/script>\n';


const html=
  '<!doctype html>'+
  '<meta charset="utf-8">'+

  '<title>'+
  suite+
  '</title>\n'+

  /* يجب أن تأتي خريطة الاستيراد قبل أي module import */
  testImportMap+

  '<style>\n'+
  wsCss+
  '\n</style>\n'+

  '<body>'+
  '<div id="reportBox"></div>\n'+
  wsDom+

  '\n<script>\n'+
  body+
  '<\/script>\n';


const outHtml=
  path.join(
    os.tmpdir(),
    path.basename(
      suite,
      '.js'
    )+
    '_browser.html'
  );


fs.writeFileSync(
  outHtml,
  html
);


console.log(
  'built',
  outHtml,
  html.length,
  'bytes'
);


module.exports={
  outHtml
};