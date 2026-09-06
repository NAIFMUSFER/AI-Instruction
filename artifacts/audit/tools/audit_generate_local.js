/* Executes the shipped local generator. DOM controls are explicit test doubles;
   generated model and engineering functions are the repository's actual code. */
const fsA=require('fs'), pathA=require('path');
const rootA=process.argv[2], outA=process.argv[3];
const {execFileSync:execA}=require('child_process');
const bundleA=pathA.join(outA,'local-bundle.js');
fsA.mkdirSync(outA,{recursive:true});
execA(process.execPath,[pathA.join(rootA,'tests/phase3/lib/extract_browser_bundle.js')],
 {cwd:rootA,env:{...process.env,ACS_BUNDLE:bundleA}});
const B_A=require(pathA.join(rootA,'node_modules/playwright/lib/transform/babelBundle.js'));
const uiA=fsA.readFileSync(pathA.join(rootA,'public/app/ui/workspace-ui-wiring.js'),'utf8');
const astA=B_A.babelParse(uiA,'audit_ui.js',false);
function declarationA(name){const n=astA.program.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);
 if(!n)throw Error('source declaration absent: '+name); return uiA.slice(n.start,n.end);}
const srcA=fsA.readFileSync(bundleA,'utf8')+'\n'+
 ['pickedType','buildLocal','parseDXF','dxfToBuilding'].map(declarationA).join('\n');
const genA=new Function('document','showCoverage',srcA+'\nreturn {buildLocal,parseDescription,warehouseFromText,dxfToBuilding};');
const rowsA=JSON.parse(fsA.readFileSync(pathA.join(outA,'../http/requests.json'),'utf8'));
const resultsA=[];
for(const c of rowsA){
 const display=[]; const doc={getElementById(id){return id==='bType'?{value:c.request.btype}:id==='strictMode'?{checked:c.request.strict}:{value:''};}};
 const gen=genA(doc,(...args)=>display.push(args)); const start=performance.now();
 const b=gen.buildLocal(c.request.text,c.request.site_w,c.request.site_d,c.request.floors);
 const ms=performance.now()-start; fsA.writeFileSync(pathA.join(outA,c.name+'.json'),JSON.stringify(b,null,2)+'\n');
 resultsA.push({name:c.name,mode:'shipped_local_generator_with_DOM_controls_stubbed',
   understanding_ms:ms,site:b.site,levels:b.levels.length,rooms:Object.values(b.floors).flatMap(f=>f.rooms||[]).map(r=>({id:r.id,rect:r.rect})),display});
}
// An input containing no recognized industrial zones takes the proven fallback.
const fallbackGenA=genA({getElementById(id){return id==='bType'?{value:'warehouse'}:id==='strictMode'?{checked:true}:{value:''}}},()=>{});
const fallbackA=fallbackGenA.buildLocal('مستودع 20×15 م بدون فرز',20,15,1);
resultsA.push({name:'warehouse_without_sorting_fallback',site:fallbackA.site,levels:fallbackA.levels.length,
 room_ids:Object.values(fallbackA.floors).flatMap(f=>f.rooms||[]).map(r=>r.id),meta:fallbackA.meta});
fsA.writeFileSync(pathA.join(outA,'local-generation-evidence.json'),JSON.stringify(resultsA,null,2)+'\n');
console.log(JSON.stringify(resultsA.map(({display,meta,...r})=>r),null,2));
