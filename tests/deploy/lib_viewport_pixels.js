/* ============================================================================
   تحليل بكسلات نافذة العرض — بديل عن مقياس حجم PNG الزائف.

   المقياس القديم كان يقيس حجم ملف اللقطة وتنوّع بايتاته. شريط أدوات ملوّن
   فوق نافذة عرض سوداء تماماً ينتج ملفاً كبيراً متنوّع البايتات، فيمرّ الفحص
   بينما المستخدم يرى سواداً. هنا تُفكّ بكسلات RGBA الفعلية لمستطيل الكانفس
   وحده — بلا شريط أدوات ولا لوحة جانبية — وتُحسب إحصاءات الإضاءة.

   العتبات ومبرّراتها (لكل قناة 0..255، الإضاءة L = 0.2126R+0.7152G+0.0722B):
     · NEAR_BLACK = 8      — تحت هذا لا يميّز المستخدم شيئاً على شاشة عادية،
                             وهو أدنى من أي لقطة ليلية فيها هندسة مضاءة.
     · BLACK_PCT  = 98.5%  — نافذة عرض حقيقية فيها مبنى تُبقي دائماً أكثر من
                             1.5% من بكسلاتها فوق العتبة (سماء أو مادة أو حافّة).
     · MEAN < 3 مع VARIANCE < 4 — إطار داكن موحّد بلا أي تفصيل: يُرفض حتى لو
                             لم يكن أسود رياضياً تماماً (مثل #010203 موحّد).
     · BUCKETS >= 3        — نافذة فيها هندسة تُنتج ثلاث درجات إضاءة مختلفة
                             على الأقل (16 درجة لكل سطل).
   العرض الليلي المشروع يمرّ لأن هندسته تُنتج تبايناً وسطولاً متعدّدة رغم
   انخفاض المتوسّط.
   ========================================================================== */
const NEAR_BLACK = 8;
const BLACK_PCT = 98.5;
const MEAN_FLOOR = 3;
const VARIANCE_FLOOR = 4;
const MIN_BUCKETS = 3;
const FLAT_DARK_MEAN = 40;   // «مسطّح» لا يُدين إلا إطاراً داكناً
const MIN_SAMPLES = 1024;

/* rgba: Uint8Array/Buffer بطول width*height*4 من مستطيل الكانفس وحده. */
function analyse(rgba, width, height) {
  const n = Math.floor(Math.min(rgba.length / 4, width * height));
  if (!n) {
    return { valid: false, verdict: 'NO_PIXELS', sampled: 0 };
  }
  let sum = 0, sum2 = 0, dark = 0, maxL = 0, minL = 255;
  const buckets = new Set();
  const colours = new Set();
  for (let i = 0; i < n; i++) {
    const r = rgba[i * 4], g = rgba[i * 4 + 1], b = rgba[i * 4 + 2];
    const l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    sum += l; sum2 += l * l;
    if (l < NEAR_BLACK) dark++;
    if (l > maxL) maxL = l;
    if (l < minL) minL = l;
    buckets.add(Math.floor(l / 16));
    if (colours.size < 4096) colours.add((r >> 3) * 1024 + (g >> 3) * 32 + (b >> 3));
  }
  const mean = sum / n;
  const variance = Math.max(0, sum2 / n - mean * mean);
  const darkPct = (dark / n) * 100;
  const reasons = [];
  if (n < MIN_SAMPLES) reasons.push('TOO_FEW_SAMPLES');
  if (darkPct >= BLACK_PCT) reasons.push('NEAR_BLACK_' + darkPct.toFixed(2) + '%');
  if (mean < MEAN_FLOOR && variance < VARIANCE_FLOOR) reasons.push('UNIFORM_DARK');
  /* «مسطّح» علامة سواد فقط حين يكون الإطار داكناً أصلاً: إطار ساطع موحّد
     ليس أسود، ومهمّة هذا الفحص كشف السواد لا الحكم على التأليف. */
  if (buckets.size < MIN_BUCKETS && mean < FLAT_DARK_MEAN)
    reasons.push('FLAT_DARK_' + buckets.size + '_BUCKETS');
  const ok = reasons.length === 0;
  return {
    valid: true,
    verdict: ok ? 'VISIBLE_CONTENT' : 'EFFECTIVELY_BLACK',
    sampled: n,
    luminance_mean: Math.round(mean * 100) / 100,
    luminance_variance: Math.round(variance * 100) / 100,
    luminance_min: Math.round(minL * 100) / 100,
    luminance_max: Math.round(maxL * 100) / 100,
    near_black_pct: Math.round(darkPct * 100) / 100,
    non_background_pct: Math.round((100 - darkPct) * 100) / 100,
    luminance_buckets: buckets.size,
    distinct_colours: colours.size,
    reasons: reasons,
    thresholds: {
      near_black_luminance: NEAR_BLACK, max_near_black_pct: BLACK_PCT,
      mean_floor: MEAN_FLOOR, variance_floor: VARIANCE_FLOOR,
      min_buckets: MIN_BUCKETS, flat_dark_mean: FLAT_DARK_MEAN,
      min_samples: MIN_SAMPLES
    }
  };
}

/* يلتقط مستطيل الكانفس وحده ويفكّ بكسلاته عبر canvas 2D داخل الصفحة —
   لا شريط أدوات ولا متصفّح ولا نص واجهة يدخل العيّنة. */
async function analysePageViewport(pg, selector) {
  const sel = selector || 'canvas';
  const data = await pg.evaluate(async (s) => {
    const c = document.querySelector(s);
    if (!c) return { error: 'NO_CANVAS' };
    const r = c.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) return { error: 'ZERO_RECT' };
    const W = Math.max(1, Math.min(Math.round(r.width), 640));
    const H = Math.max(1, Math.min(Math.round(r.height), 360));
    const off = document.createElement('canvas');
    off.width = W; off.height = H;
    const ctx = off.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(c, 0, 0, W, H);
    const px = ctx.getImageData(0, 0, W, H).data;
    return { w: W, h: H, rect: { width: r.width, height: r.height },
             canvas: { width: c.width, height: c.height },
             bytes: Array.from(px) };
  }, sel);
  if (data.error) return { valid: false, verdict: data.error, sampled: 0 };
  const out = analyse(Uint8Array.from(data.bytes), data.w, data.h);
  out.canvas_rect = data.rect;
  out.canvas_size = data.canvas;
  return out;
}

module.exports = { analyse, analysePageViewport,
  NEAR_BLACK, BLACK_PCT, MEAN_FLOOR, VARIANCE_FLOOR, MIN_BUCKETS,
  FLAT_DARK_MEAN };
