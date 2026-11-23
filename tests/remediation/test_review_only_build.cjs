'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const script = path.resolve(__dirname, '../../tools/review-only-build.cjs');
for (const branch of ['presentation-roof', 'guest-roof', 'physical-stairs', 'model-details', 'materials']) {
  for (const key of ['BRANCH', 'HEAD']) {
    const env = {...process.env, BRANCH: '', HEAD: '', [key]: `claude/acs-${branch}-20261111`};
    assert.equal(spawnSync(process.execPath, [script], {env}).status, 0);
  }
}
for (const branch of ['', 'main', 'codex/acs-safe-release-20261110', 'claude/acs-next-20261112', 'masar']) {
  const env = {...process.env, BRANCH: branch, HEAD: ''};
  assert.equal(spawnSync(process.execPath, [script], {env}).status, 1);
}
console.log('REVIEW ONLY BUILD: 15 passed; dated review branches skip deployment, existing branches retain build behavior.');
