/* Real report function, with a DOM/download double; no pixel claim. */
const assertRepair = require('assert');
const repairButton = {};
const repairBox = {className:'', innerHTML:'', querySelector:()=>repairButton};
globalThis.document = {getElementById:()=>repairBox};
let repairDownloads = [];
globalThis.dl = (blob, name)=>repairDownloads.push({blob, name});
const repairCandidate = {site:{w:20,d:25}, floors:{g:{rooms:[{id:'room',rect:[0,0,5,5]}]}}};
const repairReport = {requirements:[], repair_proposal:{applied:false,
  requires_confirmation:true, building:repairCandidate,
  engineering_diff:{available:true, changed:[{path:'<unsafe>',before:6,after:5}],
                    added:[],removed:[],total_changes:1,truncated:false}}};
showReport(repairReport, 'غرفة 6×6');
assertRepair.strictEqual(repairBox.className, 'report on');
assertRepair.match(repairBox.innerHTML, /إصلاح مقترح/);
assertRepair.match(repairBox.innerHTML, /لم يُطبّق/);
assertRepair.match(repairBox.innerHTML, /&lt;unsafe&gt;/);
assertRepair(!repairBox.innerHTML.includes('<unsafe>'));
assertRepair.strictEqual(repairDownloads.length, 0, 'no automatic download or application');
assertRepair.strictEqual(typeof repairButton.onclick, 'function');
repairButton.onclick();
assertRepair.strictEqual(repairDownloads.length, 1);
assertRepair.strictEqual(repairDownloads[0].name, 'ACS-repair-proposal.json');
repairDownloads[0].blob.text().then(text=>{
  assertRepair.deepStrictEqual(JSON.parse(text), repairCandidate);
  showReport({requirements:[]}, '');
  assertRepair.strictEqual(repairBox.innerHTML, '');
  console.log('REPAIR REPORT: 11 checks passed');
}).catch(error=>{console.error(error); process.exitCode=1;});
