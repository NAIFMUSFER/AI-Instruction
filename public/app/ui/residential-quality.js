/* ============================================================================
   Residential Quality Pass
   ------------------------
   Presentation remains separate from canonical geometry. Residential models get
   the shipped PBR + architectural detail pipeline, while an explicit audit scores
   model integrity before an engineer can mark a saved version as approved.
   Industrial/warehouse models are deliberately outside this policy.
   ========================================================================= */

const ACS_RESIDENTIAL_TYPES = new Set(['residential', 'villa', 'apartment']);
let ACS_RQ_SEQ = 0;
let ACS_RQ_AUTO_ACTIVE = false;
let ACS_RQ_LAST = null;

function acsResidentialType(building) {
  const meta = (building && building.meta) || {};
  return String(meta.type || '').trim().toLowerCase();
}

function acsIsResidential(building) {
  return ACS_RESIDENTIAL_TYPES.has(acsResidentialType(building));
}

function acsResidentialDeviceProfile() {
  const mobile = (typeof window !== 'undefined' && window.innerWidth <= 820);
  const nav = (typeof navigator !== 'undefined') ? navigator : {};
  const cores = Number(nav.hardwareConcurrency || 0);
  const memory = Number(nav.deviceMemory || 0);
  /* Width alone is not evidence that a modern phone is weak. Safari does not
     expose deviceMemory, so unknown capability keeps HIGH and the existing PBR
     runtime remains free to reduce work if actual rendering limits demand it. */
  const constrained = !!(mobile && ((cores > 0 && cores <= 4) || (memory > 0 && memory <= 4)));
  return { mobile, constrained, cores: cores || null, memory_gb: memory || null };
}

function acsResidentialAudit(building) {
  const type = acsResidentialType(building);
  if (!acsIsResidential(building)) {
    return { applicable: false, type, score: 100, block_approval: false, critical: 0, warnings: 0, issues: [] };
  }
  const issues = [];
  const add = (severity, code, message, where) => issues.push({severity, code, message, where: where || null});
  const site = (building && building.site) || {};
  const sw = Number(site.w), sd = Number(site.d);
  const hasSite = Number.isFinite(sw) && Number.isFinite(sd) && sw > 0 && sd > 0;
  const floors = (building && building.floors) || {};
  const levels = Array.isArray(building && building.levels) ? building.levels : [];
  let roomCount = 0, unresolved = 0;
  const footprintRatios = [];

  Object.keys(floors).forEach((template) => {
    const rooms = Array.isArray(floors[template] && floors[template].rooms) ? floors[template].rooms : [];
    let minX = Infinity, minZ = Infinity, maxX = -Infinity, maxZ = -Infinity;
    rooms.forEach((room, idx) => {
      roomCount += 1;
      if (room && room.acs_unresolved) unresolved += 1;
      const r = room && room.rect;
      const where = template + ':' + String((room && room.id) || idx);
      if (!Array.isArray(r) || r.length !== 4 || !r.every((v) => Number.isFinite(Number(v)))) {
        add('critical', 'RES_BAD_RECT', 'غرفة بإحداثيات غير صالحة.', where); return;
      }
      const x = Number(r[0]), z = Number(r[1]), w = Number(r[2]), d = Number(r[3]);
      if (w <= 0 || d <= 0) { add('critical', 'RES_NONPOSITIVE_ROOM', 'غرفة بعرض أو عمق غير موجب.', where); return; }
      const area = w * d;
      if (area < 1.2) add('critical', 'RES_TINY_ROOM', 'مساحة فراغ أقل من 1.2 م².', where);
      else if (area < 2) add('warning', 'RES_SMALL_ROOM', 'مساحة فراغ صغيرة جدًا وتحتاج مراجعة.', where);
      const ratio = Math.max(w / d, d / w);
      if (ratio > 8) add('warning', 'RES_EXTREME_ASPECT', 'نسبة أبعاد فراغ شديدة الاستطالة.', where);
      if (hasSite && (x < -0.25 || z < -0.25 || x + w > sw + 0.25 || z + d > sd + 0.25)) {
        add('critical', 'RES_OUTSIDE_SITE', 'فراغ يتجاوز حدود قطعة الأرض المدخلة.', where);
      }
      minX = Math.min(minX, x); minZ = Math.min(minZ, z);
      maxX = Math.max(maxX, x + w); maxZ = Math.max(maxZ, z + d);
    });
    if (hasSite && rooms.length && Number.isFinite(minX)) {
      footprintRatios.push(((maxX - minX) * (maxZ - minZ)) / (sw * sd));
    }
  });

  if (!roomCount) add('critical', 'RES_NO_ROOMS', 'النموذج السكني لا يحتوي فراغات قابلة للمراجعة.');
  if (unresolved) add('critical', 'RES_UNRESOLVED_ZONES', 'يوجد ' + unresolved + ' فراغ/فراغات لم يكتمل توليدها.');
  if (!levels.length) add('warning', 'RES_NO_LEVELS', 'لا توجد قائمة أدوار صريحة في النموذج.');
  if ((type === 'villa' || type === 'residential') && footprintRatios.some((v) => v > 0.94)) {
    add('warning', 'RES_PLOT_NEARLY_FILLED', 'بصمة أحد الأدوار تملأ معظم قطعة الأرض؛ راجع الحوش والمداخل والمساحات الخارجية.');
  }

  const diagnostics = (((building || {}).meta || {}).acs_stage_diagnostics || []);
  if (Array.isArray(diagnostics)) {
    const failed = diagnostics.filter((d) => /FAIL|UNRESOLVED|INVALID|TRUNCAT/i.test(String((d || {}).code || '')));
    if (failed.length) add('warning', 'RES_STAGE_DIAGNOSTICS', 'سجل التوليد يحتوي ' + failed.length + ' ملاحظة تحتاج مراجعة.');
  }
  const critical = issues.filter((i) => i.severity === 'critical').length;
  const warnings = issues.length - critical;
  const score = Math.max(0, 100 - critical * 22 - warnings * 6);
  return { applicable: true, type, score, block_approval: critical > 0 || score < 70,
           critical, warnings, room_count: roomCount, unresolved, issues };
}

function acsResidentialAfterPaint(fn) {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(() => requestAnimationFrame(fn));
  } else {
    Promise.resolve().then(fn);
  }
}

function acsRestoreOwnedResidentialPresentation() {
  if (!ACS_RQ_AUTO_ACTIVE || typeof window === 'undefined') return false;
  const A = window.ACS || {};
  try { if (A.adRestore) A.adRestore(); } catch (e) { /* presentation only */ }
  try { if (A.pbrRestore) A.pbrRestore(); } catch (e) { /* presentation only */ }
  ACS_RQ_AUTO_ACTIVE = false;
  return true;
}

async function acsApplyResidentialQuality(building, token) {
  const ownToken = (token === undefined) ? ++ACS_RQ_SEQ : token;
  if (ownToken !== ACS_RQ_SEQ) return { applied: false, stale: true };
  acsRestoreOwnedResidentialPresentation();

  const type = acsResidentialType(building);
  if (!acsIsResidential(building)) {
    ACS_RQ_LAST = { applied: false, type, reason: 'not_residential' };
    return ACS_RQ_LAST;
  }

  const A = (typeof window !== 'undefined' && window.ACS) ? window.ACS : {};
  const device = acsResidentialDeviceProfile();
  const quality = device.constrained ? 'MEDIUM' : 'HIGH';
  let pbrApplied = false;
  let detailApplied = false;
  const issues = [];

  try {
    if (A.pbr && typeof A.pbr.config === 'function'
        && typeof A.pbrApply === 'function'
        && typeof A.pbrCaps === 'function'
        && typeof A.pbrBounds === 'function') {
      const pbr = A.pbr.config(
        quality,
        'CLEAR_NOON',
        'REALISTIC',
        'SKY',
        null,
        null,
        A.pbrCaps(),
        A.pbrBounds(),
      );
      if (pbr && pbr.valid && ownToken === ACS_RQ_SEQ) {
        const result = A.pbrApply(pbr.config);
        pbrApplied = !!(result && result.applied);
        if (pbrApplied && typeof A.pbrCameraPreset === 'function') {
          A.pbrCameraPreset('EXTERIOR_HERO');
        }
      }
    }

    if (typeof A.ensureLayer === 'function' && ownToken === ACS_RQ_SEQ) {
      await A.ensureLayer('archdetail');
      if (ownToken !== ACS_RQ_SEQ) return { applied: false, stale: true };
      if (A.archdetail && typeof A.archdetail.config === 'function'
          && typeof A.adApply === 'function'
          && typeof A.adModelSummary === 'function') {
        const ad = A.archdetail.config(
          'DETAIL_HIGH',
          'REALISTIC',
          'NONE',
          'STAGING_REQUESTED_ONLY',
          'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY',
          null,
          device.constrained,
          [],
          A.adModelSummary(),
        );
        if (ad && ad.valid && ownToken === ACS_RQ_SEQ) {
          const result = A.adApply(ad.config);
          detailApplied = !!(result && result.applied);
        }
      }
    }
  } catch (err) {
    issues.push(String((err && err.message) || err).slice(0, 160));
  }

  ACS_RQ_AUTO_ACTIVE = pbrApplied || detailApplied;
  ACS_RQ_LAST = {
    applied: ACS_RQ_AUTO_ACTIVE,
    type,
    pbr: pbrApplied,
    architectural_detail: detailApplied,
    mobile: device.mobile,
    constrained: device.constrained,
    requested_quality: quality,
    audit: acsResidentialAudit(building),
    issues,
  };
  return ACS_RQ_LAST;
}

function acsScheduleResidentialQuality(building) {
  const token = ++ACS_RQ_SEQ;
  acsResidentialAfterPaint(() => {
    if (token === ACS_RQ_SEQ) acsApplyResidentialQuality(building, token);
  });
  return token;
}

function acsWireResidentialQuality() {
  if (typeof window === 'undefined') return false;
  window.ACS = window.ACS || {};
  const A = window.ACS;

  if (typeof A.setModel === 'function' && !A.setModel.__acsResidentialQuality) {
    const original = A.setModel;
    const wrapped = function residentialSetModel(building) {
      acsRestoreOwnedResidentialPresentation();
      const result = original.apply(this, arguments);
      acsScheduleResidentialQuality(building);
      return result;
    };
    wrapped.__acsResidentialQuality = true;
    wrapped.__acsOriginal = original;
    A.setModel = wrapped;
  }

  const gen = (typeof document !== 'undefined') ? document.getElementById('genLLM') : null;
  if (gen && typeof gen.onclick === 'function' && !gen.__acsResidentialQuality) {
    const originalGenerate = gen.onclick;
    gen.onclick = function residentialGenerateClick(ev) {
      const before = (A.exportModel && A.exportModel()) || null;
      const result = originalGenerate.call(this, ev);
      Promise.resolve(result).then(() => {
        const after = (A.exportModel && A.exportModel()) || null;
        if (after && after !== before) acsScheduleResidentialQuality(after);
      }, () => { /* generation owns its own error UI */ });
      return result;
    };
    gen.__acsResidentialQuality = true;
  }

  A.residentialQuality = {
    isResidential: acsIsResidential,
    apply: (building) => acsApplyResidentialQuality(building),
    audit: acsResidentialAudit,
    deviceProfile: acsResidentialDeviceProfile,
    restore: acsRestoreOwnedResidentialPresentation,
    state: () => ACS_RQ_LAST ? Object.assign({}, ACS_RQ_LAST) : null,
  };
  return true;
}

acsWireResidentialQuality();
