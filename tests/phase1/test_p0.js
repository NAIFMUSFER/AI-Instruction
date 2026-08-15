/* أثر بائد من مستخرج قديم كان يكتب /tmp/pure.js: المشغّل الموحّد
   tests/lib/run.js يقيّم حزمة المتصفّح في النطاق نفسه قبل جسم الاختبار، وصفحة
   اختبار المتصفّح كانت تحذف هذا السطر أصلاً. حذفه يجعل الجناح يعمل في
   البيئتين معاً بدل أن يكون متاحاً في المتصفّح وحده. */
let pass=0, fail=0;
function check(name, cond, detail){ if(cond){pass++; console.log('  ✓',name);} else {fail++; console.log('  ✗',name,'—',detail||'');} }

console.log('\n== TEST 5: object preservation (local fallback) ==');
let txt='مستودع 100×60 فيه ستة عمال وروبوتين AMR ورافعة شوكية';
let r=objectsFromText(txt);
console.log('  objects:', JSON.stringify(r.objects));
const byKind=Object.fromEntries(r.objects.map(o=>[o.kind,o.count]));
check('6 workers preserved', byKind.worker===6, 'got '+byKind.worker);
check('2 AMR robots (merged, not 2+1)', byKind.amr===2 && byKind.robot===undefined, JSON.stringify(byKind));
check('1 forklift preserved', byKind.forklift===1, 'got '+byKind.forklift);
check('nothing silently dropped (3 kinds)', r.objects.length===3, 'kinds='+r.objects.length);

console.log('\n== coverage report is populated (not silent) ==');
let cov=objCoverage(r.objects);
console.log('  coverage:', JSON.stringify(cov));
check('coverage has 3 lines', cov.length===3);
check('coverage labels counts', cov.some(c=>/6 عمّال/.test(c.req)) && cov.some(c=>/2 روبوتات AMR/.test(c.req)), JSON.stringify(cov.map(c=>c.req)));

console.log('\n== TEST 4: negative instruction respected ==');
let n=objectsFromText('مبنى فيه ثلاث سيارات بدون رافعة شوكية');
console.log('  objects:',JSON.stringify(n.objects),' excluded:',JSON.stringify(n.excluded));
const nk=Object.fromEntries(n.objects.map(o=>[o.kind,o.count]));
check('3 cars generated', nk.car===3, 'got '+nk.car);
check('forklift NOT generated', nk.forklift===undefined, 'leaked '+nk.forklift);
check('forklift reported as excluded', n.excluded.some(x=>/رافعة/.test(x)), JSON.stringify(n.excluded));

console.log('\n== attachObjects populates room.objects (renderer contract) ==');
const building={ levels:[{index:0,template:'ops'}], floors:{ops:{rooms:[{id:'hall',rect:[0,0,100,60]}]}} };
attachObjects(building, r.objects);
const host=building.floors.ops.rooms[0];
check('room.objects created', Array.isArray(host.objects)&&host.objects.length===3, 'len='+(host.objects||[]).length);
check('each has kind+count+x+z', host.objects.every(o=>o.kind&&o.count&&o.x!=null&&o.z!=null), JSON.stringify(host.objects));

console.log('\n== dual/number word variety ==');
const cases=[['عاملان','worker',2],['خمسة روبوتات','robot',5],['3 مصاعد','elevator',3],['رافعة','forklift',1]];
for(const [s,k,exp] of cases){ const o=objectsFromText(s).objects.find(x=>x.kind===k); check(`"${s}" → ${k}=${exp}`, o&&o.count===exp, o?('got '+o.count):'missing'); }

console.log('\n== English kinds still work ==');
const e=objectsFromText('warehouse with 4 forklift and 2 amr');
const ek=Object.fromEntries(e.objects.map(o=>[o.kind,o.count]));
check('4 forklift', ek.forklift===4, JSON.stringify(ek));
check('2 amr', ek.amr===2, JSON.stringify(ek));

console.log(`\nRESULT: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
