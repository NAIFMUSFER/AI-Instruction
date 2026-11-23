import fs from 'node:fs';
import {withContextDetails,getActualBounds,listContextDetails} from '../../public/app/core/context-details.mjs';
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(cases.map(c=>{
 const original=JSON.stringify(c.value);
 try{
  const value=c.op==='bounds'?getActualBounds(c.value):c.op==='list'?listContextDetails(c.value):withContextDetails(c.value);
  if(original!==JSON.stringify(c.value))throw new Error('INPUT_MUTATED');
  return {value,same:c.op==='apply'?value[0]===c.value:null};
 }catch(error){return {error:error.message};}
})));
