'use strict';
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
// Execute the shipped transport, not a test implementation of its classifier.
function source(text) {
  const s = text || fs.readFileSync(path.join(ROOT, 'public/app/ui/workspace-ui-wiring.js'), 'utf8');
  const start = s.indexOf('const ACS_NET={');
  const end = s.indexOf('\nfunction srvPill(', start);
  if (start < 0 || end < 0) throw new Error('Shipped transport boundaries missing');
  return s.slice(start, end);
}
module.exports = {source, ROOT};
