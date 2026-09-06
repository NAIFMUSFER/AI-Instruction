/* Read-only C09 witness using the shipped parser; only floor labels are stubbed. */
'use strict';
const fs=require('fs'),path=require('path');
const root=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
fs.mkdirSync(out,{recursive:true});
const file='public/app/ui/workspace-ui-wiring.js';
const source=fs.readFileSync(path.join(root,file),'utf8');
const babel=require(path.join(root,'node_modules/playwright/lib/transform/babelBundle.js'));
const ast=babel.babelParse(source,file,false);
const names=['parseDXF','dxfToBuilding','decorateRoom','wrapBuilding'];
const declarations=names.map(name=>{
  const node=ast.program.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);
  if(!node)throw Error('Missing shipped function '+name);
  return source.slice(node.start,node.end);
});
const run=new Function('acsFloorName',declarations.join('\n')+'\nreturn dxfToBuilding;')(name=>name);
const pts=[[0,0],[6000,0],[6000,2000],[2000,2000],[2000,6000],[0,6000]];
const dxf=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC',
  '0','SECTION','2','ENTITIES','0','LWPOLYLINE','90',String(pts.length),'70','1',
  ...pts.flatMap(([x,y])=>['10',String(x),'20',String(y)]),'0','ENDSEC','0','EOF'].join('\n')+'\n';
fs.writeFileSync(path.join(out,'closed-l-shape-mm.dxf'),dxf);
const building=run(dxf,20,25,3);
fs.writeFileSync(path.join(out,'current-building.json'),JSON.stringify(building,null,2)+'\n');
const result={input:{units:'millimetres',closed:true,vertices_m:pts.map(p=>p.map(x=>x/1000)),
  polygon_area_m2:20,site_m:[20,25],floors_requested:3},
  actual:{rect:building.floors.typical.rooms[0].rect,levels:building.levels.length,
    polygon_preserved:!!building.floors.typical.rooms[0].polygon},
  scope:'actual shipped parsing/wrapping; floor-name formatting stub only; no renderer or live provider'};
fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
