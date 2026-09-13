import test from 'node:test';
import assert from 'node:assert/strict';

const {
  buildSemanticLockCommand,
  collectSemanticLockTargets,
  selectorKey,
  toggleSemanticSelector,
  semanticWorkspaceChanged,
} = await import('../../public/app/ui/connected-semantic-locks.mjs');

test('native revision and busy transitions refresh locks without observing the lock panel itself', () => {
  assert.equal(semanticWorkspaceChanged([{type:'childList',target:{id:'cwRevision'}}]),true);
  assert.equal(semanticWorkspaceChanged([{type:'attributes',attributeName:'aria-busy',target:{id:'designWorkspace'}}]),true);
  assert.equal(semanticWorkspaceChanged([{type:'childList',target:{id:'cwSemanticLockTarget'}}]),false);
  assert.equal(semanticWorkspaceChanged([{type:'childList',target:{id:'cwSemanticLockStatus'}}]),false);
  assert.equal(semanticWorkspaceChanged([{type:'attributes',attributeName:'aria-current',target:{id:'designWorkspace'}}]),false);
});

const rack = {kind:'element', template:'ground', room_id:'storage', collection:'racks', element_id:'rack_a'};
const dock = {kind:'element', template:'ground', room_id:'receiving', collection:'docks', element_id:'dock_n1'};
const lane = {kind:'element', template:'ground', room_id:'storage', collection:'lanes', element_id:'aisle_main'};
const lift = {kind:'element', template:'ground', room_id:'core', collection:'objects', element_id:'lift_1'};

function packet() {
  const map = [
    {source:{kind:'space', level_index:0, template:'ground', room_id:'storage'}},
    {source:{...rack, level_index:0}},
    {source:{...dock, level_index:0}},
    {source:{...lane, level_index:0}},
    {source:{...lift, level_index:0}},
    {source:{kind:'element', level_index:0, template:'ground', room_id:'storage', collection:'unsupported', element_id:'bad'}},
    {source:{kind:'element', level_index:0, template:'ground', room_id:'storage', collection:'racks', element_id:''}},
  ];
  return {
    projections:[
      {level_index:0, source_map:map},
      // Repeated template on another level must not create a second semantic selector.
      {level_index:1, source_map:map.map(row => ({source:{...row.source, level_index:1}}))},
    ],
    locks:{semantic:[{kind:'site'}, rack]},
  };
}

test('nested lock targets come only from stable canonical provenance identities', () => {
  const targets = collectSemanticLockTargets(packet());
  assert.deepEqual(targets.map(selectorKey), [dock, lane, lift, rack].map(selectorKey).sort());
  assert.ok(targets.every(row => row.kind === 'element'));
  assert.equal(new Set(targets.map(selectorKey)).size, 4);
});

test('selector keys cannot alias two canonical identities that contain delimiters', () => {
  // Server stable ids are bounded strings, not a delimiter-restricted grammar.
  // These are distinct canonical selectors and must remain distinct in the UI Map.
  const first = {kind:'element', template:'ground|west', room_id:'storage', collection:'racks', element_id:'rack_a'};
  const second = {kind:'element', template:'ground', room_id:'west|storage', collection:'racks', element_id:'rack_a'};
  assert.notDeepEqual(first, second);
  assert.notEqual(selectorKey(first), selectorKey(second));

  const targets = collectSemanticLockTargets({
    projections:[{source_map:[{source:first}, {source:second}]}],
    locks:{semantic:[]},
  });
  assert.equal(targets.length, 2);
});

test('UI selector bounds exactly match the server 120-character stable-id contract', () => {
  const tooLong = {
    kind:'element', template:'ground', room_id:'storage', collection:'racks',
    element_id:'r'.repeat(121),
  };
  assert.equal(selectorKey(tooLong), '');
  assert.deepEqual(collectSemanticLockTargets({
    projections:[{source_map:[{source:tooLong}]}], locks:{semantic:[]},
  }), []);
});

test('toggling one nested lock preserves every unrelated server-held selector', () => {
  const current = [{kind:'site'}, {kind:'room', template:'ground', room_id:'office'}, rack, dock];
  const afterAdd = toggleSemanticSelector(current, lane, true);
  assert.deepEqual(afterAdd.map(selectorKey), [...current, lane].map(selectorKey).sort());
  assert.deepEqual(toggleSemanticSelector(afterAdd, lane, true), afterAdd);

  const afterRemove = toggleSemanticSelector(afterAdd, rack, false);
  assert.equal(afterRemove.some(row => selectorKey(row) === selectorKey(rack)), false);
  assert.equal(afterRemove.some(row => selectorKey(row) === selectorKey(dock)), true);
  assert.equal(afterRemove.some(row => selectorKey(row) === selectorKey({kind:'site'})), true);
  assert.equal(afterRemove.some(row => selectorKey(row) === selectorKey({kind:'room', template:'ground', room_id:'office'})), true);
});

test('lock command is stale-head-bound and contains no client authority fields', () => {
  const current = [{kind:'site'}, rack];
  const command = buildSemanticLockCommand({
    currentSelectors: current,
    target: dock,
    locked: true,
    expectedHead: 'rev-head-7',
  });
  assert.deepEqual(Object.keys(command).sort(), ['action','expected_head','note','selectors']);
  assert.equal(command.action, 'replace_semantic_locks');
  assert.equal(command.expected_head, 'rev-head-7');
  assert.equal(command.selectors.some(row => selectorKey(row) === selectorKey(dock)), true);
  assert.match(command.note, /dock_n1/);
  for (const forbidden of ['actor_id','actor_label','project_id','model','building','semantic_lock_manifest']) {
    assert.equal(Object.hasOwn(command, forbidden), false, forbidden);
  }
});
