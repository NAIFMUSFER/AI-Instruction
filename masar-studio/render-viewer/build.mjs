import {build} from 'esbuild';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
await build({entryPoints:[path.join(dir,'runtime-entry.mjs')],outfile:path.join(dir,'../public/render-engine.js'),bundle:true,minify:true,format:'esm',target:'es2022',legalComments:'eof'});
await writeFile(path.join(dir,'../public/render-viewer-LICENSE.txt'),await readFile(path.join(dir,'node_modules/three/LICENSE')));
await import('./package-viewer.mjs');
