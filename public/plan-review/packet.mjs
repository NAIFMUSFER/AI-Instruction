// Read-only imported presentation data is never an approval or an API command.
export const MAX_FILE_BYTES = 5 * 1024 * 1024;
const MAX_PAYLOAD_BYTES = 4 * 1024 * 1024;
const utf8 = new TextEncoder();
const obj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const id = v => typeof v === 'string' && v.trim().length > 0 && v.length <= 160;
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const num = v => typeof v === 'number' && Number.isFinite(v);
function require(value, code = 'INVALID_REVIEW_FILE') { if (!value) throw new Error(code); }
function bounded(value) {
  const todo = [[value, 0]]; let nodes = 0;
  while (todo.length) {
    const [v, depth] = todo.pop();
    require(++nodes <= 150000 && depth <= 40, 'REVIEW_FILE_LIMIT');
    if (typeof v === 'number') require(num(v));
    if (v && typeof v === 'object') for (const [k, item] of Object.entries(v)) {
      require(!['__proto__', 'prototype', 'constructor'].includes(k)); todo.push([item, depth + 1]);
    }
  }
}
function refs(items, requirements) {
  require(Array.isArray(items)); const seen = new Set();
  for (const ref of items) {
    require(obj(ref) && id(ref.requirement_id) && !seen.has(ref.requirement_id));
    seen.add(ref.requirement_id); const r = requirements.get(ref.requirement_id);
    require(r && ref.source === r.source && (ref.source_id ?? null) === (r.source_id ?? null), 'PROVENANCE_MISMATCH');
    require(JSON.stringify(ref.source_span ?? null) === JSON.stringify(r.source_span ?? null), 'PROVENANCE_MISMATCH');
  }
}
export function validateView(p) {
  bounded(p);
  require(obj(p) && p.schema === 'acs.plan-review-view/1.0' && p.read_only === true);
  const r = p.revision;
  require(obj(r) && id(r.id) && Number.isSafeInteger(r.version) && r.version > 0 && hash(r.model_hash) && hash(r.content_hash));
  require(obj(p.review) && p.review.revision_id === r.id && p.review.model_hash === r.model_hash && p.review.content_hash === r.content_hash, 'REVISION_MISMATCH');
  require(obj(p.review.scopes) && Array.isArray(p.review.issues) && p.review.issues.every(i => obj(i) && id(i.code)));
  require(Object.values(p.review.scopes).every(v => ['PASS', 'FAIL', 'NOT_VERIFIED'].includes(v)));
  require(obj(p.scorecard) && obj(p.scorecard.metrics));
  require(Array.isArray(p.requirements) && p.requirements.length <= 2000);
  const requirements = new Map();
  for (const req of p.requirements) {
    require(obj(req) && id(req.id) && !requirements.has(req.id) && ['requested', 'inferred', 'unknown'].includes(req.source));
    if ('source_span' in req) {
      const s = req.source_span;
      require(obj(s) && Object.keys(s).length === 2 && Number.isSafeInteger(s.start) && Number.isSafeInteger(s.end) && s.start >= 0 && s.end > s.start);
    }
    requirements.set(req.id, req);
  }
  require(obj(p.locks) && Array.isArray(p.locks.rooms) && Array.isArray(p.locks.semantic));
  require(p.locks.rooms.every(v => Array.isArray(v) && v.length === 2 && v.every(id)));
  require(p.locks.semantic.every(v => obj(v) && ['site', 'room', 'element'].includes(v.kind)));
  require(Array.isArray(p.projections) && p.projections.length > 0 && p.projections.length <= 128);
  const levels = new Set(); let total = 0;
  for (const plan of p.projections) {
    require(obj(plan) && plan.revision_id === r.id && plan.model_hash === r.model_hash, 'REVISION_MISMATCH');
    require(plan.scope === 'SPACE_BOUNDARIES_ONLY' && plan.units === 'm');
    require(Number.isSafeInteger(plan.level_index) && !levels.has(plan.level_index)); levels.add(plan.level_index);
    require(obj(plan.site) && num(plan.site.w) && num(plan.site.d) && plan.site.w > 0 && plan.site.d > 0);
    require(Array.isArray(plan.primitives) && plan.primitives.length > 0 && (total += plan.primitives.length) <= 10000, 'REVIEW_FILE_LIMIT');
    require(Array.isArray(plan.source_map)); const sources = new Map();
    for (const s of plan.source_map) {
      require(obj(s) && id(s.source_id) && !sources.has(s.source_id) && obj(s.source));
      refs(s.requirement_refs, requirements); sources.set(s.source_id, s);
    }
    const seen = new Set();
    for (const item of plan.primitives) {
      require(obj(item) && id(item.source_id) && !seen.has(item.source_id)); seen.add(item.source_id);
      const s = sources.get(item.source_id);
      require(s && JSON.stringify(s.source) === JSON.stringify(item.source) && s.source.kind === 'space'
        && s.source.level_index === plan.level_index && id(s.source.room_id) && id(s.source.template), 'PROVENANCE_MISMATCH');
      refs(item.requirement_refs, requirements);
      require(JSON.stringify(s.requirement_refs) === JSON.stringify(item.requirement_refs), 'PROVENANCE_MISMATCH');
      const rect = item.rect_xz_m;
      require(Array.isArray(rect) && rect.length === 4 && rect.every(num));
      const [x, z, w, d] = rect;
      require(x >= -1e-6 && z >= -1e-6 && w > 0 && d > 0 && x + w <= plan.site.w + 1e-6 && z + d <= plan.site.d + 1e-6);
      require(num(item.space_rect_area_m2) && Math.abs(item.space_rect_area_m2 - w * d) <= 1e-6 * Math.max(1, w * d));
      require(typeof item.label === 'string' && item.label.length <= 2000);
    }
  }
  return p;
}
export async function parseReviewFile(raw) {
  require(typeof raw === 'string' && utf8.encode(raw).length <= MAX_FILE_BYTES, 'REVIEW_FILE_LIMIT');
  const file = JSON.parse(raw);
  require(obj(file) && file.schema === 'acs.plan-review-file/1.0' && typeof file.payload_json === 'string' && hash(file.payload_sha256));
  const bytes = utf8.encode(file.payload_json);
  require(bytes.length <= MAX_PAYLOAD_BYTES, 'REVIEW_FILE_LIMIT');
  require(globalThis.crypto?.subtle, 'SECURE_CONTEXT_REQUIRED');
  const result = await crypto.subtle.digest('SHA-256', bytes);
  const actual = Array.from(new Uint8Array(result), b => b.toString(16).padStart(2, '0')).join('');
  require(actual === file.payload_sha256, 'REVIEW_HASH_MISMATCH');
  return validateView(JSON.parse(file.payload_json));
}
