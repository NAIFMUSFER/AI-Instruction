/* مشغّل اختبارات المرحلة 3.
   يستخرج شيفرة المتصفّح من public/index.html ثم يشغّل ملفّ الاختبار في نطاق
   واحد معها، مع __dirname الحقيقي لملفّ الاختبار كي تُحلّ تجهيزاته من المستودع
   لا من مجلّد مؤقّت. لا يعتمد على أي ملفّ في /tmp موجود مسبقاً. */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const HERE = __dirname;
const PHASE = path.resolve(HERE, '..');
const ROOT = path.resolve(HERE, '..', '..', '..');

function buildBundle() {
  const out = path.join(os.tmpdir(), 'acs_browser_bundle.js');
  execFileSync(process.execPath, [path.join(HERE, 'extract_browser_bundle.js')],
    { env: Object.assign({}, process.env, { ACS_BUNDLE: out }), stdio: 'pipe' });
  return out;
}

function run(testFile) {
  const abs = path.isAbsolute(testFile) ? testFile : path.join(PHASE, testFile);
  if (!fs.existsSync(abs)) throw new Error('test file not found: ' + abs);
  const bundle = fs.readFileSync(buildBundle(), 'utf8');
  const body = fs.readFileSync(abs, 'utf8');
  const fn = new Function('__dirname', '__filename', 'require', 'process', 'console',
                          'module', 'exports', bundle + '\n;\n' + body);
  fn(path.dirname(abs), abs, require, process, console, { exports: {} }, {});
}

module.exports = { run, buildBundle, ROOT, PHASE };

if (require.main === module) {
  const arg = process.argv[2];
  if (!arg) {
    console.error('usage: node tests/phase3/lib/run.js <test-file.js>');
    process.exit(2);
  }
  run(arg);
}
