/* حارس الشحن لا يخلط التأجيل المعلن بالغياب.
   نشغّل جناحَي الأمن الحقيقيّين في عمليات معزولة، ثم نكسر مصادر الرسم
   المقروءة عمداً. لا ملفّ إنتاجي يتغيّر ولا فحص أمني يُحذف. */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const ROOT = path.resolve(__dirname, '../..');
let passed = 0;
for (const [phase, module] of [
  ['phase6', 'generated/workspace-ui.js'],
  ['phase7', 'generated/render-engine.js'],
]) {
  for (const [mode, expected] of [
    ['declared-lazy', 0], ['declared-eager', 0],
    ['missing-declaration', 1], ['duplicate-owner', 1],
    ['missing-loader', 1], ['duplicate-loader', 1],
  ]) {
    const code = `
      const A = require('./tests/phase3/lib_app_files.js');
      const target = ${JSON.stringify(module)};
      const mode = ${JSON.stringify(mode)};
      const order = A.order, lazy = A.lazyOrder, mod = A.mod;
      if (mode === 'declared-eager' || mode === 'duplicate-owner')
        A.order = () => order().concat(target);
      if (mode === 'declared-eager' || mode === 'missing-declaration')
        A.lazyOrder = () => lazy().filter(name => name !== target);
      if (mode === 'missing-loader' || mode === 'duplicate-loader') {
        const call = "import('../" + target + "')";
        A.mod = name => name !== 'ui/panels-entry.js' ? mod(name)
          : mode === 'missing-loader' ? mod(name).replace(call, 'Promise.resolve()')
          : mod(name) + '\\n' + call;
      }
      require('./tests/lib/run.js').run('tests/${phase}/test_security.js');
    `;
    const result = spawnSync(process.execPath, ['-e', code], {
      cwd: ROOT, encoding: 'utf8', timeout: 60000,
    });
    assert.equal(result.status, expected,
      phase + '/' + mode + '\n' + result.stdout + result.stderr);
    if (expected) assert.match(result.stdout, /✗ [^\n]*declared eager or lazy path/,
      'mutation must execute the ownership guard, not fail before it');
    console.log('PASS ' + phase + '/' + mode + ' exit=' + result.status);
    passed++;
  }
}
console.log('AUDIT FRONTEND GUARDS: ' + passed + ' passed, 0 failed');
