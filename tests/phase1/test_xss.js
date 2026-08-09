let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d||''))};
const payload='<script>alert("test")</script>';
// notes sink (mirrors line: esc(n.kind)+esc(n.room)+esc(n.layer)+esc(n.text))
const notesHTML='<b>'+esc(payload)+'</b> — '+esc(payload)+' ('+esc('x')+')<br><span>'+esc(payload)+'</span>';
chk('notes: no raw <script>', !/<script>/.test(notesHTML), notesHTML.slice(0,60));
chk('notes: escaped entity present', notesHTML.includes('&lt;script&gt;'));
// tooltip sink
const t=['LAY',payload,payload,payload];
const tipHTML=`<b>${esc(t[0])}</b><br>الدور: ${esc(t[1])} · الغرفة: ${esc(t[2]||'-')}<br><span>${esc(t[3]||'')}</span>`;
chk('tooltip: no raw <script>', !/<script>/.test(tipHTML));
chk('tooltip: quotes escaped', esc('a"b').includes('&quot;'));
// coverage/report already used esc — sanity
chk('report req escapes', esc('<img src=x onerror=1>').includes('&lt;img'));
// Arabic must pass through intact (no over-escaping)
chk('Arabic intact', esc('مستودع ٦ عمّال')==='مستودع ٦ عمّال');
console.log(`\nXSS: ${pass} passed, ${fail} failed`); process.exit(fail?1:0);
