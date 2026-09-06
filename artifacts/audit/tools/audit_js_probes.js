'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
const ui=fs.readFileSync(path.join(root,'public/app/ui/workspace-ui-wiring.js'),'utf8');
const B=require(path.join(root,'node_modules/playwright/lib/transform/babelBundle.js'));
const ast=B.babelParse(ui,'audit.js',false);
function decl(name){const n=ast.program.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);if(!n)throw Error(name);return ui.slice(n.start,n.end);}
const bundle=fs.readFileSync(path.resolve(out,'../../baseline/local-models/local-bundle.js'),'utf8');
const parser=new Function(bundle+'\n'+['parseDXF','dxfToBuilding','decorateRoom','wrapBuilding'].map(decl).join('\n')+'\nreturn {parseDXF,dxfToBuilding};')();
const dxf=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES',
 '0','LWPOLYLINE','90','4','70','0','10','0','20','0','10','6000','20','0','10','6000','20','4000','10','0','20','4000','0','ENDSEC','0','EOF'].join('\n');
fs.writeFileSync(path.join(out,'open-polyline-mm.dxf'),dxf+'\n');
const model=parser.dxfToBuilding(dxf,20,25,3);
const rows=[{case:'dxf_millimetres_and_open_polyline',declared_units:'millimetres',declared_closed:false,
 source_dimensions_m:[6,4],parsed_polygons:parser.parseDXF(dxf).length,
 actual_rect:model.floors.typical.rooms[0].rect,actual_levels:model.levels.length}];
const s=ui.indexOf('const ACS_NET={'),e=ui.indexOf('\nfunction srvPill(',s);
function harness(fetcher){let timer,cleared=false;
 const c={Date,AbortController,navigator:{onLine:true},__ACS_SHARED:{},apiURL:p=>'https://example.invalid'+p,
 window:{ACS_API:{base:()=> 'https://example.invalid',host:()=> 'example.invalid'}},fetch:fetcher,
 setTimeout:fn=>{timer=fn;return 1;},clearTimeout:()=>{cleared=true;}};
 vm.runInNewContext(ui.slice(s,e),c);return {call:c.__ACS_SHARED.acsFetchJSON,cleared:()=>cleared};}
async function main(){
 let resolved=false;const h=harness(async()=>({status:200,ok:true,headers:{get:()=>''},text:()=>new Promise(()=>{})}));
 h.call('/v1/understand',{},1000).then(()=>{resolved=true;});
 await new Promise(r=>setImmediate(r));
 rows.push({case:'response_body_deadline_removed',deadline_already_cleared:h.cleared(),call_resolved:resolved,
 scope:'shipped function; controlled timer and body promise; no external network'});
 const g=harness(async()=>({status:200,ok:true,headers:{get:()=>''},text:async()=>{throw new TypeError('terminated');}}));
 rows.push({case:'body_network_failure_misclassified',actual:(await g.call('/test')).status});
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(rows,null,2)+'\n');console.log(JSON.stringify(rows,null,2));
}main().catch(e=>{console.error(e);process.exitCode=1;});
