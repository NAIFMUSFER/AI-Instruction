/** Exercise the actual vendored parser; this is a Node test, not browser proof. */
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root = new URL('../../', import.meta.url);
const pkg = JSON.parse(await readFile(new URL('package.json', root)));
const version = pkg.dependencies['pdfjs-dist'];
const pdfjs = await import(new URL(`public/vendor/pdfjs@${version}/pdf.min.mjs`, root));
pdfjs.GlobalWorkerOptions.workerSrc = new URL(`public/vendor/pdfjs@${version}/pdf.worker.min.mjs`, root).href;
let passed = 0;
function check(fn) { fn(); passed++; }
check(() => assert.equal(pdfjs.version, version));
const stream = 'BT /F1 12 Tf 30 100 Td (ACS audit) Tj ET';
const objects = [
 '<< /Type /Catalog /Pages 2 0 R >>',
 '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
 '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
 '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
 `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
];
let pdf = '%PDF-1.4\n'; const offsets = [0];
for (const [i,obj] of objects.entries()) { offsets.push(pdf.length); pdf += `${i+1} 0 obj\n${obj}\nendobj\n`; }
const xref = pdf.length;
pdf += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
const doc = await pdfjs.getDocument({data:new TextEncoder().encode(pdf), isEvalSupported:false, useSystemFonts:true}).promise;
check(() => assert.equal(doc.numPages, 1));
const page = await doc.getPage(1);
check(() => assert.equal(page.getViewport({scale:1}).width, 200));
const text = await page.getTextContent();
check(() => assert.equal(text.items.map(i=>i.str).join(''), 'ACS audit'));
await doc.destroy();
await assert.rejects(pdfjs.getDocument({data:new TextEncoder().encode('invalid document'), isEvalSupported:false}).promise, /Invalid PDF/); passed++;
const ui = await readFile(new URL('public/app/ui/workspace-ui-wiring.js', root),'utf8');
const calls = [...ui.matchAll(/pdfjs\.getDocument\((\{[^}]+\})\)/g)];
check(() => assert.equal(calls.length, 3));
check(() => assert.ok(calls.every(c=>c[1].includes('isEvalSupported:false'))));
console.log(`PDF runtime: ${passed} passed, 0 failed (Node; browser NOT VERIFIED)`);
