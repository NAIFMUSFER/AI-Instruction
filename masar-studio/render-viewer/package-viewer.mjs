// Package the audited wrapper without executing npm/network at application runtime.
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const source=await readFile(path.join(dir,'../src/three-viewer.mjs'),'utf8');
const imports=["import * as THREE from 'three';", "import { OrbitControls } from 'three/addons/controls/OrbitControls.js';", "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';", "import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';"].join('\n');
if(!source.includes(imports))throw Error('Unexpected viewer import contract');
await writeFile(path.join(dir,'../public/render-viewer.js'),source.replace(imports,"import {THREE,OrbitControls,GLTFLoader,GLTFExporter} from './render-engine.js';"));
const files={};for(const name of ['render-engine.js','render-viewer.js']){const data=await readFile(path.join(dir,'../public/'+name));files[name]={bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')};}
await writeFile(path.join(dir,'../public/render-viewer-integrity.json'),JSON.stringify({three:'0.180.0',esbuild:'0.25.10',files},null,2)+'\n');
console.log(JSON.stringify(files));
