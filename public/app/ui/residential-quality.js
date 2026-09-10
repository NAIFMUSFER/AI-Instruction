/* ============================================================================
   Residential Quality Pass
   ------------------------
   Presentation only. The canonical Building JSON is never changed here.
   Residential/villa/apartment models get the already-shipped PBR pipeline and
   architectural window detailing automatically after a successful model load.
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

  /* A new model must not inherit the previous model's automatic presentation. */
  acsRestoreOwnedResidentialPresentation();

  const type = acsResidentialType(building);
  if (!acsIsResidential(building)) {
    ACS_RQ_LAST = { applied: false, type, reason: 'not_residential' };
    return ACS_RQ_LAST;
  }

  const A = (typeof window !== 'undefined' && window.ACS) ? window.ACS : {};
  const mobile = (typeof window !== 'undefined' && window.innerWidth <= 820);
  let pbrApplied = false;
  let detailApplied = false;
  const issues = [];

  try {
    if (A.pbr && typeof A.pbr.config === 'function'
        && typeof A.pbrApply === 'function'
        && typeof A.pbrCaps === 'function'
        && typeof A.pbrBounds === 'function') {
      const pbr = A.pbr.config(
        mobile ? 'MEDIUM' : 'HIGH',
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

    /* Frames/reveals are already implemented in the lazy architectural layer.
       Load it through panels-entry's single loader without opening its panel. */
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
          mobile,
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
    mobile,
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

  /* Public setModel stays synchronous and preserves its return value. */
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

  /* Server generation uses the module-local setModel, so observe the generation
     promise itself and enhance only when the active model reference changed. */
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
    restore: acsRestoreOwnedResidentialPresentation,
    state: () => ACS_RQ_LAST ? Object.assign({}, ACS_RQ_LAST) : null,
  };
  return true;
}

acsWireResidentialQuality();
