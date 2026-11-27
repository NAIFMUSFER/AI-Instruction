// A confirmed program of three or more storeys gets the 12-call ceiling unless
// the owner picked another limit (live jobs 6cd7137f and 1b0eb00e stopped at 8).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const src = readFileSync(new URL('../../public/app/ui/connected-workspace.mjs', import.meta.url), 'utf8');
const body = src.match(/function generationCalls\(program\)\{[\s\S]*?\n\}/);
assert.ok(body, 'generationCalls is defined');
const make = value => new Function('$', body[0] + '\nreturn generationCalls;')(() => ({ value: String(value) }));
const levels = n => ({ levels: Array.from({ length: n }, (_, i) => ({ name: 'L' + i })) });
assert.equal(make(8)(levels(3)), 12, 'three storeys at the default limit get 12');
assert.equal(make(8)(levels(5)), 12);
assert.equal(make(8)(levels(2)), 8, 'two storeys keep the default');
assert.equal(make(8)(undefined), 8, 'no confirmed program keeps the default');
assert.equal(make(6)(levels(3)), 6, 'a limit the owner picked is kept');
assert.equal(make(3)(levels(4)), 3);
assert.ok(src.includes('max_provider_calls:(source.source_id&&planUpload.calls())||generationCalls(reading.program)'),
  'the generate request uses it');
console.log('GENERATION CALLS: 7 passed');
