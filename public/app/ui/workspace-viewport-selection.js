/* ============================================================================
   Canonical viewport selection bridge.

   This file owns NO geometry and NO engineering edit path. It translates an
   already-rendered mesh hit into an identity that the existing Phase 6
   workspace can inspect. Presentation highlighting lives outside BUILDING and
   never enters model hashes, revisions, BIM or exports.
   ========================================================================== */

const OWNER_TYPES = new Set([
  'WALL','FLOOR','ROOF','CEILING','SLAB','RACK','LANE','STATION','CONVEYOR','DOCK'
]);
const OPENING_TYPES = new Set(['DOOR','WINDOW']);

function asId(v) {
  return (typeof v === 'string' && v.length > 0 && v.length <= 240) ? v : null;
}

function levelForToken(building, token) {
  const levels = Array.isArray(building && building.levels) ? building.levels : [];
  const m = /^F(-?\d+)$/.exec(String(token || ''));
  if (m) {
    const idx = Number(m[1]);
    return levels.find(l => Number(l && l.index) === idx) || null;
  }
  return levels.find(l => l && String(l.template) === String(token)) || null;
}

function roomAt(building, template, roomId) {
  const floor = building && building.floors && building.floors[template];
  const rooms = floor && Array.isArray(floor.rooms) ? floor.rooms : [];
  return rooms.find(r => r && asId(r.id) && r.id === roomId) || null;
}

function effectivelyPresentationOnly(mesh) {
  const u = (mesh && mesh.userData) || {};
  return !!(u.presentation_context || u.acs_visual_only || u.visual_only || u.presentation_only);
}

function parseMeshTag(mesh) {
  const name = asId(mesh && mesh.name);
  if (!name || name.indexOf('|') < 0) return null;
  const p = name.split('|');
  if (p.length < 3) return null;
  return {name, hit_kind:String(p[0] || '').toUpperCase(), level_token:p[1], room_id:p[2], tail:p.slice(3)};
}

export function canonicalSelectionForMesh(mesh, building, buildingId='bld_0') {
  if (!mesh || !building || effectivelyPresentationOnly(mesh)) return null;
  const tag = parseMeshTag(mesh);
  if (!tag) return null;
  if (!OWNER_TYPES.has(tag.hit_kind) && !OPENING_TYPES.has(tag.hit_kind)) return null;

  const level = levelForToken(building, tag.level_token);
  if (!level || !asId(level.template)) return null;
  const levelIndex = Number(level.index);
  if (!Number.isSafeInteger(levelIndex)) return null;
  const template = level.template;
  const room = roomAt(building, template, tag.room_id);
  if (!room || !asId(room.id)) return null;
  const bid = asId(buildingId) || 'bld_0';

  if (OPENING_TYPES.has(tag.hit_kind)) {
    if (!tag.tail.length || !/^\d+$/.test(String(tag.tail[0]))) return null;
    const index = Number(tag.tail[0]);
    const key = tag.hit_kind === 'DOOR' ? 'doors' : 'windows';
    const list = Array.isArray(room[key]) ? room[key] : [];
    if (!Number.isSafeInteger(index) || index < 0 || index >= list.length) return null;
    const opening = list[index] || {};
    const fallback = `${bid}.${template}.${room.id}.${tag.hit_kind.toLowerCase()}_${index}`;
    return {
      target_id: asId(opening.id) || fallback,
      target_kind: tag.hit_kind,
      hit_kind: tag.hit_kind,
      identity_strength: 'EXACT',
      level_index: levelIndex,
      template,
      room_id: room.id,
      mesh_name: tag.name,
      writes_to_model: false
    };
  }

  // The current renderer often splits a canonical room boundary into several
  // WALL/FLOOR/ROOF/etc. meshes. Those segments are not independent canonical
  // authoring identities. Selecting one therefore selects only the proven owner
  // SPACE and says so explicitly instead of fabricating a wall/rack/dock id.
  return {
    target_id: `${bid}.${template}.${room.id}`,
    target_kind: 'SPACE',
    hit_kind: tag.hit_kind,
    identity_strength: 'OWNER_SPACE',
    level_index: levelIndex,
    template,
    room_id: room.id,
    mesh_name: tag.name,
    writes_to_model: false
  };
}

export function meshesForCanonicalSelection(meshes, targetId, building, buildingId='bld_0') {
  if (!Array.isArray(meshes) || !asId(targetId)) return [];
  const out = [];
  for (const mesh of meshes) {
    const sel = canonicalSelectionForMesh(mesh, building, buildingId);
    if (sel && sel.target_id === targetId) out.push(mesh);
  }
  return out;
}

function collectMeshes(root) {
  const out = [];
  if (!root) return out;
  if (typeof root.traverse === 'function') {
    root.traverse(o => { if (o && o.isMesh) out.push(o); });
    return out;
  }
  const walk = o => {
    if (!o) return;
    if (o.isMesh) out.push(o);
    if (Array.isArray(o.children)) o.children.forEach(walk);
  };
  walk(root);
  return out;
}

function visibleInHierarchy(obj) {
  let p = obj;
  while (p) { if (p.visible === false) return false; p = p.parent; }
  return true;
}

export function installWorkspaceViewportSelection(deps={}) {
  if (typeof window === 'undefined' || typeof document === 'undefined')
    return {installed:false, reason:'NO_BROWSER'};
  const {THREE, renderer, scene, late, openWorkspace} = deps;
  const canvas = renderer && renderer.domElement;
  if (!THREE || !THREE.Raycaster || !THREE.Vector2 || !canvas || !scene || !late)
    return {installed:false, reason:'MISSING_RENDER_DEPS'};
  if (window.__ACS_VIEWPORT_SELECTION && window.__ACS_VIEWPORT_SELECTION.installed)
    return window.__ACS_VIEWPORT_SELECTION;

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let down = null;
  let helpers = [];
  let destroyed = false;
  const previousSelectHook = window.__ACS_ON_SELECT;

  function clearHighlight() {
    for (const h of helpers) {
      try { scene.remove(h); } catch (e) {}
      try { if (h.geometry && h.geometry.dispose) h.geometry.dispose(); } catch (e) {}
      try { if (h.material && h.material.dispose) h.material.dispose(); } catch (e) {}
    }
    helpers = [];
  }

  function buildingId() {
    const acs = window.ACS;
    try {
      const p = acs && acs.workspace && acs.workspace.project ? acs.workspace.project() : null;
      if (p && asId(p.building_id)) return p.building_id;
    } catch (e) {}
    return 'bld_0';
  }

  function highlightTarget(targetId) {
    clearHighlight();
    const building = late.lastBuilding;
    const root = late.model;
    if (!building || !root || !asId(targetId)) return 0;
    const matches = meshesForCanonicalSelection(collectMeshes(root).filter(visibleInHierarchy),
      targetId, building, buildingId()).slice(0, 96);
    for (const mesh of matches) {
      try {
        const h = new THREE.BoxHelper(mesh, 0x22d3ee);
        h.name = 'ACS_SELECTION_HIGHLIGHT';
        h.userData = h.userData || {};
        h.userData.presentation_context = true;
        h.userData.acs_selection_highlight = true;
        scene.add(h); helpers.push(h);
      } catch (e) {}
    }
    return helpers.length;
  }

  async function selectInWorkspace(selection) {
    if (!selection) return false;
    let acs = window.ACS;
    // Reuse the existing panel entry on every viewport selection when available.
    // If the workspace was already loaded, openWorkspace() re-attaches the current
    // exported canonical project before selection; this prevents a new model from
    // being inspected through a stale previous workspace project.
    if (typeof openWorkspace === 'function') {
      try { await Promise.resolve(openWorkspace()); } catch (e) { return false; }
      acs = window.ACS;
    } else if (acs && acs.workspace) {
      try { if (typeof acs.workspace.open === 'function') acs.workspace.open(); } catch (e) {}
    }
    if (!(acs && acs.workspace && typeof acs.workspace.select === 'function')) return false;
    acs.workspace.select(selection.target_id);
    const live = document.getElementById('acsLiveRegion');
    if (live) {
      const qualifier = selection.identity_strength === 'OWNER_SPACE'
        ? `؛ ${selection.hit_kind} جزء مشتق، فتم تحديد الفراغ المالك` : '';
      live.textContent = `تم تحديد ${selection.target_kind}: ${selection.target_id}${qualifier}`;
    }
    return true;
  }

  async function hitAt(clientX, clientY) {
    const root = late.model, camera = late.camera, building = late.lastBuilding;
    if (!root || !camera || !building) return null;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -(((clientY - rect.top) / rect.height) * 2 - 1);
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObject(root, true) || [];
    for (const hit of hits) {
      if (!hit || !hit.object || !visibleInHierarchy(hit.object)) continue;
      const selection = canonicalSelectionForMesh(hit.object, building, buildingId());
      if (!selection) continue;
      await selectInWorkspace(selection);
      return selection;
    }
    return null;
  }

  function pointerDown(e) {
    if (e && e.isPrimary === false) return;
    if (e && e.button !== undefined && e.button !== 0) return;
    down = {x:Number(e.clientX), y:Number(e.clientY), id:e.pointerId};
  }
  function pointerUp(e) {
    if (!down) return;
    const start = down; down = null;
    if (e && e.pointerId !== undefined && start.id !== undefined && e.pointerId !== start.id) return;
    const dx = Number(e.clientX) - start.x, dy = Number(e.clientY) - start.y;
    if (!Number.isFinite(dx) || !Number.isFinite(dy) || Math.hypot(dx,dy) > 6) return;
    void hitAt(Number(e.clientX), Number(e.clientY));
  }
  function pointerCancel(){ down = null; }

  window.__ACS_ON_SELECT = function(id) {
    if (typeof previousSelectHook === 'function') {
      try { previousSelectHook(id); } catch (e) {}
    }
    highlightTarget(id);
  };

  canvas.addEventListener('pointerdown', pointerDown, {passive:true});
  canvas.addEventListener('pointerup', pointerUp, {passive:true});
  canvas.addEventListener('pointercancel', pointerCancel, {passive:true});

  const api = {
    installed:true,
    hitAt,
    highlightTarget,
    clearHighlight,
    destroy(){
      if (destroyed) return;
      destroyed = true;
      canvas.removeEventListener('pointerdown', pointerDown);
      canvas.removeEventListener('pointerup', pointerUp);
      canvas.removeEventListener('pointercancel', pointerCancel);
      clearHighlight();
      if (window.__ACS_ON_SELECT === api.selectHook) window.__ACS_ON_SELECT = previousSelectHook;
      if (window.__ACS_VIEWPORT_SELECTION === api) delete window.__ACS_VIEWPORT_SELECTION;
    }
  };
  api.selectHook = window.__ACS_ON_SELECT;
  window.__ACS_VIEWPORT_SELECTION = api;
  return api;
}
