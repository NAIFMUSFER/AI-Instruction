// Evaluate actual shipped declarations; never reimplement roof geometry here.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(import.meta.url);
const APP=require('../lib/app_source.js'),SEG=require('../lib/js_segment.js');
// Real numeric/hash helpers use the repository's dependency-free source loader.
// Native imports and the full module graph are covered by the browser suite.
const roofSource=APP.nodeBundle(['core/viewer.js','core/standards.js','core/roof.mjs']);
const wiring=APP.stripModuleSyntax(APP.modules()['ui/workspace-ui-wiring.js'],'workspace-ui-wiring.js');
const statements=SEG.topLevelStatements(wiring).map(s=>wiring.slice(s.start,s.end));
const countsDeclaration=statements.find(s=>/^function localModelCounts\(/.test(SEG.head(s)));
if(!countsDeclaration)throw new Error('Actual localModelCounts declaration is missing');
const roof=new Function(roofSource+'\n'+countsDeclaration+
  '\nreturn {addFlatRoofLevel,withDefaultRoof,carryAutoRoof,removeAutoRoof,restoreDefaultRoof,roofRemovedByUser,roofDisclosure,isRoofLevel,hasRoofLevel,localModelCounts,acsRoomRect};')();
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const methods={add:'addFlatRoofLevel',default:'withDefaultRoof',carry:'carryAutoRoof',
  remove:'removeAutoRoof',restore:'restoreDefaultRoof',removed:'roofRemovedByUser',
  disclosure:'roofDisclosure',is_roof:'isRoofLevel',has_roof:'hasRoofLevel'};
function execute(row){
  const args=structuredClone(row.args),before=structuredClone(args);
  let outcome;
  try{
    const fn=roof[methods[row.op]];
    if(typeof fn!=='function')throw new Error('Missing shipped roof export: '+methods[row.op]);
    const value=fn(...args);
    if(value&&typeof value.then==='function')throw new Error('Roof API must be synchronous');
    const model=(row.op==='add'||row.op==='default')?value?.[0]:value;
    outcome={outcome:'return',value,same_input:model===args[0]};
  }catch(error){outcome={outcome:'error',error:error.message};}
  return {id:row.id,...outcome,mutated:!isDeepStrictEqual(args,before)};
}
function samples(){
  const example=statements.find(s=>/^const\s+EXAMPLE\s*=/.test(SEG.head(s)));
  if(!example)throw new Error('Actual residential EXAMPLE declaration is missing');
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'acs-roof-parity-'));
  try{
    const bundle=path.join(folder,'bundle.js');
    execFileSync(process.execPath,['tests/phase3/lib/extract_browser_bundle.js'],
      {cwd:root,env:{...process.env,ACS_BUNDLE:bundle},timeout:90000,stdio:'pipe'});
    return new Function(fs.readFileSync(bundle,'utf8')+'\n'+example+
      '\nreturn {residential:EXAMPLE,warehouse:warehouseModel(120,80,{clear:12})};')();
  }finally{fs.rmSync(folder,{recursive:true,force:true});}
}
process.stdout.write(JSON.stringify(request.samples?samples():request.counts?
  request.counts.map(model=>roof.localModelCounts(model)):request.rendererRects?
  request.rendererRects.map(room=>roof.acsRoomRect(room)):request.cases.map(execute)));
