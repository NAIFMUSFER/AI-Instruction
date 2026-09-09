import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read=p=>readFile(path.join(root,p),'utf8');
const order=['shared/authoring.js','shared/model.js','shared/building.js','shared/layout-quality.js','shared/ifc.js','shared/geometry.js','src/renderer.js','src/storage.js','shared/render-scene.js','src/render-ui.js','src/plan-inspection.js','src/app.js'];
const modules=new Map();let script="'use strict';\nglobalThis.MASAR_STANDALONE=true;\n";
for(const [i,file] of order.entries()){
 const code=await read(file), moduleName='MASAR_Module_'+i, bindings=[];
 const cleaned=code.replace(/^import\s+\{([^}]+)\}\s+from\s+['"]([^'"]+)['"];\s*$/gm,(_,spec,from)=>{
  const target=path.posix.normalize(path.posix.join(path.posix.dirname(file),from)), mod=modules.get(target);
  if(!mod)throw Error(`Unsupported import order: ${file} -> ${target}`);
  bindings.push(`const {${spec.replace(/\s+as\s+/g,':')}}=${mod};`);return '';
 }).replace(/\bexport\s+(?=(?:async\s+)?(?:const|let|function|class))/g,'');
 if(/^import\s/m.test(cleaned)||/^export\s/m.test(cleaned))throw Error(`Unhandled module syntax: ${file}`);
 const names=[...code.matchAll(/export\s+(?:async\s+)?(?:const|let|function|class)\s+(\w+)/g)].map(m=>m[1]);
 script+=`const ${moduleName}=(()=>{\n${bindings.join('\n')}\n${cleaned}\nreturn {${names.join(',')}};\n})();\n`;
 modules.set(file,moduleName);
}
if(script.includes('</script'))throw Error('Unexpected script terminator');
const style=await read('src/style.css'),favicon=await read('public/favicon.svg');
let html=await read('public/index.html');
html=html.replace('<link rel="manifest" href="/public/manifest.webmanifest">','').replace('<link rel="icon" type="image/svg+xml" href="/public/favicon.svg">',`<link rel="icon" href="data:image/svg+xml;base64,${Buffer.from(favicon).toString('base64')}">`).replace('<link rel="stylesheet" href="/src/style.css">',`<style>${style}</style>`).replace('href="/" aria-label="مسار، الصفحة الرئيسية"','href="#" aria-label="مسار، الصفحة الرئيسية"').replace('<script type="module" src="/src/app.js"></script>',()=>`<script>${script}</script>`);
const hash=createHash('sha256').update(script).digest('base64');
html=html.replace('<meta charset="UTF-8">',`<meta charset="UTF-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-${hash}'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; base-uri 'none'; form-action 'none'">`);
await mkdir(path.join(root,'dist'),{recursive:true});await writeFile(path.join(root,'dist/index.html'),html);await writeFile(path.join(root,'dist/app.bundle.js'),script);
console.log(JSON.stringify({standalone:'dist/index.html',bytes:Buffer.byteLength(html),scriptSha256:hash,externalDependencies:0},null,2));
