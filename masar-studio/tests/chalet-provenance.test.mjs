import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {understand,generate} from '../shared/model.js';
const prompt=readFileSync(new URL('./fixtures/chalet-client-20x25.txt',import.meta.url),'utf8');
test('Explicit resort/garden priority wins over incidental privacy word',()=>assert.equal(understand(prompt).priority,'outdoor'));
test('Preserved paragraphs live in redaction-aware requirements, not an unredacted duplicate brief field',()=>{const m=generate(understand(prompt));m.brief.prompt='الوصف الأصلي غير مشمول في رابط المراجعة.';m.requirements=m.requirements.filter(r=>!['custom','unresolved'].includes(r.type));m.brief.unresolved=[];assert.ok(!JSON.stringify(m).includes('Modern Resort Style'));assert.ok(!JSON.stringify(m).includes('بانترى صغير'));});
for(const [text,type] of [['مستودع مع مكتب إداري','warehouse'],['مكاتب مع مستودع ملفات','office'],['متجر مع مخزن خلفي','retail'],['فيلا بنظام شاليه مع مستودع صغير','chalet'],['تصميم فيلا مع مكتب منزلي ومخزن','villa']])test('Main building has priority over contained secondary uses: '+text,()=>assert.equal(understand(text).projectType,type));
