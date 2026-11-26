// U8: in upload mode the plot section is hidden and the page says why.
// A plan read from the owner's file is transcribed as drawn; plot rules
// (setbacks, parking) are never applied to it (the engine refuses them too).
import assert from 'node:assert/strict';
import fs from 'node:fs';
const upload = fs.readFileSync(new URL('../../public/app/ui/plan-upload.mjs', import.meta.url), 'utf8');
const plot = fs.readFileSync(new URL('../../public/app/ui/plot-rules.mjs', import.meta.url), 'utf8');
const engine = fs.readFileSync(new URL('../../acs_workspace_service.py', import.meta.url), 'utf8');
assert.match(plot, /section\.hidden = value\('cwType'\) !== 'residential' \|\| value\('cwStartMode'\) === 'upload';/);
assert.match(plot, /'cwBrief','cwStartMode'\]\)/, 'switching start mode refreshes the plot section');
assert.match(upload, /id="cwPlotNote"[^>]*>في وضع رفع المخطط[^<]*أخفينا قسم الأرض والارتدادات والمواقف/);
assert.match(upload, /\$\('cwStartMode'\)\.dispatchEvent\(new Event\('change'\)\)/, 'a restored upload mode hides the plot section too');
assert.match(engine, /بيانات الأرض تُستخدم مع توليد مخطط من الوصف، لا مع قراءة ملف مخطط/);
console.log('upload plot mode: 5 checks passed');
