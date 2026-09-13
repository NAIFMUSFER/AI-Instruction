/* ============================================================================
   ACS Design Pipeline v2 — warehouse rendered-submesh canonical identity

   The current Three.js warehouse renderer expands one canonical rack/dock/lane/
   station record into many meshes whose names contain an ARRAY POSITION.  That
   position is useful as a renderer locator, but it is not engineering identity.

   This module deliberately separates the two:
     mesh-name array position -> locate the canonical record -> require explicit id

   No explicit stable canonical `id` means no exact identity.  We never promote an
   array index, mesh name, geometry, label or plausible source into a canonical id.
   `source_id` and `provenance` are copied through only when the canonical record
   already carries them.  The Canonical ACS Building is read-only here.
   ========================================================================== */

const WAREHOUSE_COLLECTION_KINDS = Object.freeze({
  racks: 'RACK',
  docks: 'DOCK',
  lanes: 'LANE',
  stations: 'STATION',
});

function stableId(value) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
}

function jsonCopy(value) {
  if (value === undefined) return undefined;
  try { return JSON.parse(JSON.stringify(value)); }
  catch (_) { return undefined; }
}

function levelIndexFromKey(value) {
  const m = /^F(\d+)$/.exec(String(value == null ? '' : value));
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isSafeInteger(n) && n >= 0 ? n : null;
}

function suffixLocator(suffix) {
  let m;
  // A rack record fans out to deck/goods/posts/beams.  All carry rack index ri.
  m = /^(?:rack|goods|post|beam)(\d+)(?:r\d+|$)/.exec(suffix);
  if (m) return {collection:'racks', index:Number(m[1])};

  // Dock record: door, leveler and bumpers all carry dock index di.
  m = /^(?:dock|leveler|bump)(\d+)_\d+$/.exec(suffix);
  if (m) return {collection:'docks', index:Number(m[1])};

  // Station record: worktop/legs/screen/printer/specialized accessory share si.
  m = /^(?:st|stleg|stscr|stprn|stvoid|strobot)(\d+)_\d+$/.exec(suffix);
  if (m) return {collection:'stations', index:Number(m[1])};

  // Lane record: paint, edge paint, arrows, conveyor and conveyor accessories.
  m = /^lane(\d+)(?:edge)?$/.exec(suffix);
  if (m) return {collection:'lanes', index:Number(m[1])};
  m = /^arrow(\d+)_\d+$/.exec(suffix);
  if (m) return {collection:'lanes', index:Number(m[1])};
  m = /^(?:conv|convrail)(\d+)$/.exec(suffix);
  if (m) return {collection:'lanes', index:Number(m[1])};
  m = /^convleg(\d+)_\d+$/.exec(suffix);
  if (m) return {collection:'lanes', index:Number(m[1])};
  // Conveyor emergency-stop names contain lane + part index.  A plain `estop0`
  // comes from room.points and must NOT be promoted to a lane.
  m = /^estop(\d+)_\d+$/.exec(suffix);
  if (m) return {collection:'lanes', index:Number(m[1])};

  return null;
}

/** Parse only renderer addresses that are known to come from warehouse expanders. */
function parseWarehouseMeshAddress(meshName) {
  if (typeof meshName !== 'string' || !meshName) return null;
  const parts = meshName.split('|');
  if (parts.length !== 4) return null;
  const [layer, levelKey, roomId, suffix] = parts;
  const levelIndex = levelIndexFromKey(levelKey);
  if (levelIndex === null || !stableId(roomId)) return null;
  const locator = suffixLocator(suffix);
  if (!locator || !Number.isSafeInteger(locator.index) || locator.index < 0) return null;
  return {layer, level_key:levelKey, level_index:levelIndex, room_id:roomId,
          suffix, collection:locator.collection, array_index:locator.index};
}

function uniqueLevel(building, levelIndex) {
  const levels = building && Array.isArray(building.levels) ? building.levels : [];
  const hits = levels.filter(level => level && Number(level.index) === levelIndex
    && Number.isInteger(Number(level.index)));
  if (hits.length !== 1 || !stableId(hits[0].template)) return null;
  return hits[0];
}

function uniqueRoom(building, template, roomId) {
  const floors = building && building.floors;
  const floor = floors && typeof floors === 'object' ? floors[template] : null;
  const rooms = floor && Array.isArray(floor.rooms) ? floor.rooms : [];
  const hits = rooms.filter(room => room && room.id === roomId);
  return hits.length === 1 ? hits[0] : null;
}

function uniqueExplicitElement(items, index) {
  if (!Array.isArray(items) || index < 0 || index >= items.length) return null;
  const item = items[index];
  if (!item || typeof item !== 'object' || !stableId(item.id)) return null;
  // An explicit id is not stable identity if the same collection contains it twice.
  if (items.filter(other => other && other.id === item.id).length !== 1) return null;
  return item;
}

/**
 * Resolve a rendered warehouse submesh to exact canonical identity.
 *
 * Array position is accepted only as a locator into the same canonical collection;
 * the returned identity is the record's explicit stable id.  This is intentionally
 * fail-closed so legacy generated warehouses without nested ids remain owner-space
 * selectable only and cannot masquerade as exact rack/dock/lane/station identity.
 */
function canonicalWarehouseIdentityForMesh(mesh, building, buildingId='bld_0') {
  if (!mesh || typeof mesh !== 'object') return null;
  const ud = mesh.userData && typeof mesh.userData === 'object' ? mesh.userData : {};
  if (ud.acs_visual_only === true || ud.presentation_context === true) return null;

  const address = parseWarehouseMeshAddress(mesh.name);
  if (!address) return null;
  const level = uniqueLevel(building, address.level_index);
  if (!level) return null;
  const room = uniqueRoom(building, level.template, address.room_id);
  if (!room) return null;
  const item = uniqueExplicitElement(room[address.collection], address.array_index);
  if (!item) return null;

  const provenance = jsonCopy(item.provenance);
  const sourceId = stableId(item.source_id) ? item.source_id : null;
  const spaceId = stableId(room.space_id) ? room.space_id : null;
  const targetId = item.id.trim();

  const identity = {
    target_id: targetId,
    target_kind: WAREHOUSE_COLLECTION_KINDS[address.collection],
    identity_strength: 'EXACT_EXPLICIT_ID',
    building_id: stableId(buildingId) ? buildingId : null,
    template: level.template,
    room_id: room.id,
    space_id: spaceId,
    collection: address.collection,
    source_id: sourceId,
    canonical_selector: {
      kind: 'element',
      template: level.template,
      room_id: room.id,
      collection: address.collection,
      element_id: targetId,
    },
    // Diagnostic only.  Never use this field as engineering identity.
    renderer_locator: {
      level_index: address.level_index,
      array_index: address.array_index,
      mesh_name: mesh.name,
    },
  };
  if (provenance !== undefined) identity.provenance = provenance;
  return identity;
}

/** Tag presentation metadata only; never mutates canonical building geometry/data. */
function tagWarehouseRenderedMesh(mesh, building, buildingId='bld_0') {
  if (!mesh || typeof mesh !== 'object') return null;
  if (!mesh.userData || typeof mesh.userData !== 'object') mesh.userData = {};
  const identity = canonicalWarehouseIdentityForMesh(mesh, building, buildingId);
  if (!identity) {
    // A reused Three.js object must not retain a stale exact identity after model swap.
    if (Object.prototype.hasOwnProperty.call(mesh.userData, 'acsCanonicalIdentity'))
      delete mesh.userData.acsCanonicalIdentity;
    return null;
  }
  mesh.userData.acsCanonicalIdentity = jsonCopy(identity);
  return identity;
}

function tagWarehouseRenderedSubtree(root, building, buildingId='bld_0') {
  let visited = 0, tagged = 0;
  const apply = mesh => { visited += 1;
    if (tagWarehouseRenderedMesh(mesh, building, buildingId)) tagged += 1; };
  if (root && typeof root.traverse === 'function') root.traverse(apply);
  else if (Array.isArray(root)) root.forEach(apply);
  else if (root) apply(root);
  return {visited, tagged, unresolved:visited-tagged};
}

function warehouseMeshesForCanonicalId(meshes, targetId, building, buildingId='bld_0') {
  if (!stableId(targetId) || !Array.isArray(meshes)) return [];
  return meshes.filter(mesh => {
    const identity = canonicalWarehouseIdentityForMesh(mesh, building, buildingId);
    return identity && identity.target_id === targetId;
  });
}

export {
  WAREHOUSE_COLLECTION_KINDS,
  canonicalWarehouseIdentityForMesh,
  parseWarehouseMeshAddress,
  stableId,
  tagWarehouseRenderedMesh,
  tagWarehouseRenderedSubtree,
  warehouseMeshesForCanonicalId,
};
