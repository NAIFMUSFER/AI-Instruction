# التحقّق الإنتاجي — آخر تشغيل فعليّ

**الفرع:** `remediation/production-trust` · **HEAD:** `6bc8a88b1871334c1d371d4e5e5da9ad540109ac`
**تاريخ التشغيل:** `2026-08-14T13:45:21Z` · **البيئة:** صندوق البناء الرملي (sandbox)
**الأمر المُشغَّل:** `sh tests/production/run_all.sh`
**رمز الخروج:** `2` — أي **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**

> هذا التقرير يسجّل ما رُصد فعلاً، لا ما يُتوقَّع أن يكون. كل سطر هنا خرج من أمر
> شُغِّل. ولا يوجد في هذا الملفّ مربّع اختيار فارغ واحد: كل بند له حكم صريح
> (**PASS** أو **FAIL** أو **NOT VERIFIED**) وسببه.

---

## 1. الحكم النهائي

| الطبقة | PASS | FAIL | NOT VERIFIED | المجموع | exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| `verify_live.py` — HTTP وأصول الواجهة (A · B · G) | 0 | 0 | 18 | 18 | 2 |
| `verify_live_browser.js` — Chromium (C · D · E · F · G) | 0 | 0 | 29 | 29 | 2 |
| **المجموع** | **0** | **0** | **47** | **47** | **2** |

**لم يُرصد شيء إطلاقاً على النشر الحيّ.** لا فحص واحد يُدَّعى ناجحاً، ولا فحص واحد
يُدَّعى فاشلاً. السبب واحد ومحدَّد، ومكتوب في كل سطر من سجلّ التشغيل:

```
reason: egress proxy refused the CONNECT tunnel (HTTP 403) — this sandbox cannot
        reach arbitrary external hosts: URLError: <urlopen error Tunnel
        connection failed: 403 Forbidden>
```

ومن جهة المتصفّح:

```
reason: the frontend could not be loaded: page.goto:
        net::ERR_TUNNEL_CONNECTION_FAILED at https://sprightly-selkie-d906c3.netlify.app/
```

### تأكيد حاجز الشبكة قبل أي ادّعاء

```
$ curl -sS -m 20 -o /dev/null -w "%{http_code}\n" https://sprightly-selkie-d906c3.netlify.app
curl: (56) CONNECT tunnel failed, response 403

$ curl -sS -m 20 -o /dev/null -w "%{http_code}\n" https://acs-engine.onrender.com/health
curl: (56) CONNECT tunnel failed, response 403

$ python3 -c "import urllib.request; urllib.request.urlopen('https://acs-engine.onrender.com/health')"
ERR URLError <urlopen error Tunnel connection failed: 403 Forbidden>
```

وكيل الخروج (egress proxy) في هذه البيئة يرفض CONNECT لأي مضيف خارجي بـ**403
Forbidden**. كذلك `registry.npmjs.org` و`pypi.org` محجوبان فعلياً (`npm pack
three@0.160.0` ⇒ `npm error 403`، و`pip install fastapi` ⇒ `No matching
distribution found`). لذلك لا Three.js مُعبَّأ محلياً ولا FastAPI هنا، وهو سبب
ثانٍ مستقلّ يمنع تشغيل المجموعتين C وD حتى محلياً.

---

## 2. أهداف النشر — كما يعلنها المستودع نفسه

قُرِئت من الملفّات لا من الذاكرة، ويطبعها السكربت في الخطوة `0`:

| المصدر | المفتاح | القيمة المقروءة |
| --- | --- | --- |
| `netlify.toml` | `[build] publish` | `public` |
| `netlify.toml` | CSP `connect-src` | `'self' https://acs-engine.onrender.com` |
| `netlify.toml` | `[build] command` | `bash tools/netlify-build.sh` |
| `render.yaml` | `ACS_ALLOWED_ORIGINS` | `https://sprightly-selkie-d906c3.netlify.app` |
| `render.yaml` | `healthCheckPath` | `/health` |
| `acs_understand_api.py:112` | `_DEFAULT_ORIGIN` | `https://sprightly-selkie-d906c3.netlify.app` |
| `public/index.html` | `CONFIGURED_BASE` | `https://acs-engine.onrender.com` |

الأربعة الأخيرة تُغلق الحلقة: الخادم يسمح بأصل Netlify افتراضياً، والصفحة تنادي
نطاق Render، والـCSP تسمح بالنطاق نفسه وحده. **الهدفان المُعلنان في المهمّة هما
هدفا النشر الحقيقيان** — هذا استنتاج ساكن من الملفّات، وقد طُبع كاستشهاد، ولم
يُحوَّل إلى PASS.

**ملاحظة تصحيحيّة:** `tools/netlify-build.sh` تُعلن في مصفوفة `must=( … )`
**18** ملفّاً مُعبَّأً (15 من three@0.160.0، وes-module-shims@1.8.2، وملفّا
pdfjs@4.0.379) — لا 21. القائمة الحرِجة في `verify_live.py` تُشتقّ برمجياً من
تلك المصفوفة ومن خريطة الاستيراد في `public/index.html`، فطُبعت `18 file(s)`.
ولو أُضيف ملفّ إلى المصفوفة غداً لالتقطه المِرقاب بلا تعديل.

---

## 3. نتيجة كل فحص — الجدول الكامل

لا يوجد سطر بلا حكم. `NV` هنا تعني حرفياً
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`.

### A · HTTP: الواجهة، والخادم، وعقد الأخطاء، وCORS

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| A1 | جذر الواجهة يردّ 200 (لا 401/403) | **NV** | 403 CONNECT tunnel |
| A1b | جذر الواجهة يُقدَّم كـHTML | **NV** | 403 CONNECT tunnel |
| A2 | `GET /` يردّ 200 بجسد JSON للخدمة | **NV** | 403 CONNECT tunnel |
| A3 | `GET /health` يردّ 200 ويُعلن الضبط | **NV** | 403 CONNECT tunnel |
| A3b | `/health` لا يسرّب أي مادّة اعتماد | **NV** | 403 CONNECT tunnel |
| A4 | `GET /ready` حكم حقيقي (200 ready أو 503 `ACS_NOT_CONFIGURED`) | **NV** | 403 CONNECT tunnel |
| A5 | `GET /version` يطابق عقد `acs_build_info` | **NV** | 403 CONNECT tunnel |
| A6 | مسار غير موجود يردّ مغلّف `acs-error-envelope/1.0.0` لا صفحة HTML | **NV** | 403 CONNECT tunnel |
| A7 | preflight من الأصل المسموح مقبول | **NV** | 403 CONNECT tunnel |
| A8 | preflight من أصل غريب مرفوض | **NV** | 403 CONNECT tunnel |

عقد `/version` المُتحقَّق منه مأخوذ حرفياً من `acs_understand_api.py:387-403`
و`acs_build_info.build_info()`: المفاتيح `service` و`version` و`git_sha`
و`git_sha_short` و`git_branch` و`built_at` و`provenance_verified`
و`schema_versions`، مع ثلاثة شروط اشتقاق: `git_sha_short == git_sha[:12]`،
و`provenance_verified == (git_sha != "unknown" and built_at != "unknown")`،
و`schema_versions.error_contract == "acs-error-envelope/1.0.0"`.

عقد مغلّف الخطأ مأخوذ من `acs_api_errors.py:22` و`acs_api_errors.envelope()`
(السطور 181-201): `ok:false`، و`contract:"acs-error-envelope/1.0.0"`، وحقول
`error` **الخمسة بالضبط** `{code, message, request_id, retryable, upstream}`،
وترويسة `X-Request-ID` في الرد.

### B · أصول الواجهة

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| B1 | كل وحدة JS حرِجة (18 ملفّاً) تردّ 200 وغير فارغة | **NV** | 403 CONNECT tunnel |
| B2 | Three.js المخدوم يُعلن `REVISION = 160` | **NV** | 403 CONNECT tunnel |
| B3 | لا مرجع CDN زمن التشغيل في الصفحة ولا في الوحدات | **NV** | 403 CONNECT tunnel |
| B4 | ترويسة CSP موجودة، تمنع أصول script خارجية، وتسمح بالخادم في `connect-src` | **NV** | 403 CONNECT tunnel |
| B5 | لا 404 غير متوقّع بين الأصول الحرِجة | **NV** | 403 CONNECT tunnel |
| B6 | الصفحة المخدومة تُعلن importmap، وكل specifier فيها يُحلّ إلى وحدة رُدّت 200 | **NV** | 403 CONNECT tunnel |

### C · إقلاع المتصفّح الحقيقي (Chromium عبر Playwright)

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| C1 | لا `pageerror` غير مُلتقَط أثناء الإقلاع | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C2 | نافذة العرض تُهيَّأ (canvas بمقاس backing وCSS غير صفريّ) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C3 | سياق WebGL متاح فعلاً | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C4 | نموذج اختبار يُرسم (شبكات قانونية، draw calls، مثلّثات) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C5 | مخرج البكسلات غير فارغ (RGBA مفكوكة عبر `lib_viewport_pixels.js`) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C6 | انتقالات ENGINEERING / PBR / ARCHITECTURAL تنجح | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C7 | لا طلب أصل فاشل ولا انتهاك CSP أثناء الإقلاع | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| C8 | لا `pageerror` بعد التشغيل كاملاً | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |

محلّل البكسلات المستعمل هو **نفسه** `tests/deploy/lib_viewport_pixels.js` — لم
تُكتب نسخة ثانية، والاستدعاء عبر `PX.analysePageViewport(pg, 'canvas')`.

### D · المرور الوظيفي في المتصفّح

| # | الخطوة | النتيجة | السبب |
| --- | --- | --- | --- |
| D1 | إنشاء/فتح مشروع | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D2 | توليد أو تحميل نموذج عيّنة | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D3 | تحديد عنصر (بلا كتابة في النموذج) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D4 | فحص العنصر في المفتّش | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D5 | دخول وضع التحرير | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D6 | معاينة تغيير بلا مسّ النموذج المودَع | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D7 | إلغاء المعاينة | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D8 | معاينة ثانية بعد الإلغاء | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D9 | الإيداع بزرّ `#wsCommitBtn` نفسه | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D10 | تراجع (undo) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D11 | إعادة (redo) تستعيد hash المودَع تماماً | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D12 | فتح لوحة BIM | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D13 | فتح لوحة التوثيق | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| D14 | تصدير (مركز التصدير + descriptor بالمراجعة وhash النموذج) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |

### E · الاستجابة

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| E1 | لا فيض أفقي عند 375 · 390 · 430 · 768 · 1024 · 1440 · 1920 | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| E2 | عناصر التحكّم الرئيسية التسعة قابلة للوصول عند كل عرض | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |

### F · العربية

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| F1 | المستند يُعلن `lang=ar` و`dir=rtl` | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| F2 | لا نصّ إنجليزي ذو معنى في chrome الواجهة | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| F3 | لا فيض أفقي في تخطيط RTL | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |

### G · أصل النشر (deployment provenance)

| # | الفحص | النتيجة | السبب |
| --- | --- | --- | --- |
| G1 | SHA الخادم وطابعه الزمني من `GET /version` | **NV** | 403 CONNECT tunnel |
| G2 | الصفحة المخدومة تُعلن `window.ACS_BUILD_INFO` بـSHA **مُستبدَل** | **NV** | 403 CONNECT tunnel |
| G3 | الواجهة والخادم يُبلّغان SHA نفسه | **NV** | لم يُرصد أيّ من الاثنين |
| G4 | المراجعة المنشورة تطابق `--expect-sha` | **NV** | لم تُمرَّر مراجعة متوقَّعة في هذا التشغيل |
| G5 | `window.ACS_BUILD_INFO` يحمل SHA مُستبدَلاً وطابعاً زمنياً (متصفّح) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |
| G6 | SHA الواجهة يطابق `--expect-sha` (متصفّح) | **NV** | `ERR_TUNNEL_CONNECTION_FAILED` |

> **تحذير مسبق لمشغّل الشبكة، مبنيّ على قراءة الشجرة وعلى قياس محلّي — لا على
> قياس النشر:** `public/index.html` يُعرّف `window.ACS_BUILD_INFO` (السطور
> 60-88) لكنه يبنيه من رموز نائبة حرفيّة `__ACS_GIT_SHA__` و`__ACS_BUILT_AT__`
> و`__ACS_FRONTEND_VERSION__` يُفترض أن يستبدلها البناء. و`tools/netlify-build.sh`
> **لا يستبدلها ولا ينادي `tools/write_build_info.py`** (تحقُّق: `grep -c
> "__ACS\|write_build_info" tools/netlify-build.sh` ⇒ `0`). لذلك تُقيّم الصفحة
> نفسها `INFO.substituted = false` و`provenance = "UNPROVENANCED"`، وهذا ما رُصد
> فعلاً عند خدمة `public/` محلياً:
>
> ```
> ✗ G2  window.ACS_BUILD_INFO is assigned, but the build identity token is still
>       the literal placeholder — no build step substituted it, so the deployed
>       page is UNPROVENANCED and cannot be tied to a revision
> ✗ G5  window.ACS_BUILD_INFO exists but its identity tokens were never
>       substituted by a build step (provenance=UNPROVENANCED)
> ```
>
> يُتوقَّع خروج **G2** و**G5** بـ**FAIL** عند التشغيل من جهاز متّصل ما لم تُضَف
> خطوة استبدال إلى `tools/netlify-build.sh`. هذا **ليس قياساً للنشر** — هو قياس
> للصفحة المشحونة في الشجرة، ويُعلَن بوصفه كذلك.

---

## 4. مخرَج التشغيل الحقيقي (منسوخ حرفياً)

نهاية `tests/production/outputs/verify_live.log`:

```
──────────────────────────────────────────────────────────────────────
HTTP LAYER: 0 PASS · 0 FAIL · 18 NOT VERIFIED (of 18 checks)
summary: /tmp/acs/tests/production/outputs/verify_live.json
VERDICT: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED — nothing was observed; no check is claimed as passing.
```

نهاية `tests/production/outputs/verify_live_browser.log`:

```
──────────────────────────────────────────────────────────────────────
BROWSER LAYER: 0 PASS · 0 FAIL · 29 NOT VERIFIED (of 29 checks)
summary: /tmp/acs/tests/production/outputs/verify_live_browser.json
VERDICT: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED — no pixel was rendered here and nothing is claimed.
```

نهاية `sh tests/production/run_all.sh`:

```
=== 3 · combined machine-readable summary ===
TOTAL: 0 PASS · 0 FAIL · 47 NOT VERIFIED (of 47 checks)
combined verdict: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED

==============================================
PRODUCTION VERIFICATION: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
  nothing was observed on either target; no check is claimed as passing.
  re-run from a networked machine:
    sh tests/production/run_all.sh --expect-sha $(git rev-parse HEAD)
logs: /tmp/acs/tests/production/outputs
```

الملفّات المكتوبة: `outputs/targets.log` و`outputs/verify_live.log` و
`outputs/verify_live.json` و`outputs/verify_live_browser.log` و
`outputs/verify_live_browser.json` و`outputs/summary.log` و`outputs/summary.json`.

---

## 5. إثبات أن المِرقاب ليس فارغاً (vacuity proofs)

مِرقابٌ يُخرج NOT VERIFIED دائماً لا قيمة له: قد يكون عاجزاً عن الحكم أصلاً.
لذلك شُغِّل على أهداف محلّية (127.0.0.1 **لا يمرّ** عبر الوكيل) لإثبات المسارات
الثلاثة كلّها. الأرقام أدناه حقيقيّة.

| # | الهدف | الغرض | النتيجة الفعليّة | exit |
| --- | --- | --- | --- | ---: |
| P1 | `https://acs-deliberately-dead-host.invalid` | مضيف ميت | 0 PASS · 0 FAIL · **18 NV** — تدهور نظيف بلا انهيار | **2** |
| P2 | `http://127.0.0.1:9` (منفذ مرفوض) | عطل نقل من صنف آخر | 0 PASS · 0 FAIL · **18 NV**، السبب `the connection was refused: [Errno 111]` | **2** |
| P3 | `python3 -m http.server 8901` يخدم صفحة خاطئة فيها CDN | إثبات مسار FAIL | 3 PASS · **14 FAIL** · 3 NV | **1** |
| P4 | stub بعقد صحيح مبنيّ من `acs_api_errors` و`acs_build_info` | إثبات أن فحوص A قابلة للتحقّق أصلاً | **10/10 من مجموعة A بـPASS** (13 PASS إجمالاً) | 1 |
| P5 | `python3 -m http.server 8902` يخدم `public/` الحقيقي | سلوك حقيقي في الاتجاهين | 4 PASS · 2 FAIL · 23 NV (متصفّح) | **1** |
| P6 | خادم يردّ `401` مع `WWW-Authenticate` | إثبات رمز الحجب الحرفي | **FRONTEND_ACCESS_RESTRICTED** في الطبقتين | **1** |

### P3 — الخادم الخاطئ يُعطي FAIL لا PASS

```
$ cd /tmp/acs-fake-deploy && python3 -m http.server 8901 --bind 127.0.0.1 &
$ python3 tests/production/verify_live.py \
    --frontend http://127.0.0.1:8901 --backend http://127.0.0.1:8901 \
    --expect-sha 6bc8a88b1871334c1d371d4e5e5da9ad540109ac

  ✗ A2     GET / answers 200 with the service JSON
  ✗ A3     GET /health answers 200 and declares configuration
  ✗ A4     GET /ready is a real verdict (200 ready or 503 ACS_NOT_CONFIGURED envelope)
  ✗ A5     GET /version matches the acs_build_info contract
  ✗ A6     an invalid route returns the acs-error-envelope/1.0.0 envelope … and NOT an HTML page
           an HTML page was returned instead of the envelope; …; no X-Request-ID response header
  ✗ A7     a CORS preflight from the allowed origin … is accepted
  ✗ B1     every critical JS module returns 200 (18 file(s) fetched)
  ✗ B2     the served Three.js declares REVISION 160          REVISION=None
  ✗ B3     no runtime CDN reference is served                 index.html references cdn.jsdelivr.net
  ✗ B4     the CSP header is present …                        no Content-Security-Policy response header
  ✗ B6     the served page declares an import map …           (0 specifier(s))
  ✗ G1     the backend build SHA … from GET /version
  ✗ G2     the frontend page declares window.ACS_BUILD_INFO with a build SHA
HTTP LAYER: 3 PASS · 14 FAIL · 3 NOT VERIFIED (of 20 checks)
VERDICT: FAIL — at least one check observed wrong behaviour.     exit=1
```

### P4 — العقد الصحيح يُعطي PASS (الفحوص قابلة للإرضاء، ليست مستحيلة)

`stub` صغير بمكتبة قياسية فقط، يبني ردوده من **وحدات المستودع نفسها**
(`acs_api_errors.envelope()` و`acs_build_info.build_info()`):

```
  ✓ A1  ✓ A1b  ✓ A2  ✓ A3  ✓ A3b  ✓ A4  ✓ A5  ✓ A6  ✓ A7  ✓ A8
  ✓ G1  git_sha=6bc8a88b1871334c1d371d4e5e5da9ad540109ac
        git_branch=remediation/production-trust built_at=2026-08-14T13:16:43Z
        provenance_verified=True
  ✓ G4  expected=6bc8a88b1871334c1d371d4e5e5da9ad540109ac
        observed=['6bc8a88b1871334c1d371d4e5e5da9ad540109ac']
HTTP LAYER: 13 PASS · 6 FAIL · 1 NOT VERIFIED (of 20 checks)
```

الستّة الفاشلة كلّها من المجموعة B وG2 لأن الواجهة المخدومة في تلك التجربة هي
`public/` بلا `public/vendor` (غير موجود في هذه البيئة). **هذا stub وليس النشر:
نجاحه يثبت أن الفحوص قابلة للتحقّق وأنها مُحاذية لعقد المستودع الحقيقي، ولا
يثبت شيئاً عن الخادم المنشور.**

### P5 — الصفحة الحقيقية في Chromium: PASS وFAIL في التشغيل نفسه

```
$ (cd public && python3 -m http.server 8902 --bind 127.0.0.1 &)
$ node tests/production/verify_live_browser.js --frontend http://127.0.0.1:8902

  HTTP 200 http://127.0.0.1:8902/
  ✓ C1    no uncaught page error during boot
  ✗ C2    the viewport initialises (window.ACS.ready)
          window.ACS.ready never became true within 45s; failed requests:
          http://127.0.0.1:8902/vendor/three@0.160.0/…/Sky.js — net::ERR_ABORTED …
   375px overflow=0   390px overflow=0   430px overflow=0   768px overflow=0
  1024px overflow=0  1440px overflow=0  1920px overflow=0
  ✓ E1    no horizontal overflow at 375/390/430/768/1024/1440/1920
  ― E2    the primary controls stay reachable at every width
          reason: the workspace toolbar never rendered because the application did not boot
  ✓ F1    the document declares lang=ar and dir=rtl   {"lang":"ar","dir":"rtl","computedDir":"rtl"}
  ✓ F3    no horizontal overflow in the Arabic (RTL) layout
  ✗ G5    window.ACS_BUILD_INFO carries a substituted frontend build SHA …
          … exists but its identity tokens were never substituted by a build step
          (provenance=UNPROVENANCED) — the running page is UNPROVENANCED
BROWSER LAYER: 4 PASS · 2 FAIL · 23 NOT VERIFIED (of 29 checks)     exit=1
```

هذا أنفع دليل في الملفّ: **F1 وF3 وE1 وC1 نجحت على الصفحة الحقيقية المشحونة**،
و**C2 سقطت لأن `public/vendor` غير موجود هنا**، و**G5 سقطت لأن رموز هويّة البناء
لم تُستبدَل**، وكل ما يعتمد على تطبيق مُقلِع أُعلن NOT VERIFIED. الاتجاهان
مُثبَتان بمخرَج واحد.

ونفس الصفحة عبر طبقة HTTP: `4 PASS · 13 FAIL · 3 NOT VERIFIED` (exit 1) — منها
`✓ B3 no runtime CDN reference is served` و`✗ B6 … (12 specifier(s))` بعد أن
حلّت الوحدات الاثنتا عشرة إلى مسارات ردّت 404.

### P6 — رمز الحجب الحرفي

```
  ✗ A1     frontend root answers 200
      FRONTEND_ACCESS_RESTRICTED — HTTP 401 from http://127.0.0.1:8904.
      Authentication configuration found in the repository: NONE — no basic_auth /
      _headers / edge function in the repo, so any password is set in the Netlify
      site dashboard (Site settings ▸ Access control), outside this tree.
      The site is NOT publicly verified.

  ✗ C0    the frontend is publicly reachable
      FRONTEND_ACCESS_RESTRICTED — … answered an authentication challenge that
      Chromium reported as "page.goto: net::ERR_INVALID_AUTH_CREDENTIALS …".
```

الطبقة المتصفّحية كانت تُبلّغ هذه الحالة NOT VERIFIED في أول محاولة، لأن Chromium
يحوّل تحدّي `401 WWW-Authenticate` إلى فشل تنقّل `ERR_INVALID_AUTH_CREDENTIALS`
فلا تصل حالة HTTP إلى الشيفرة. عُولج بتصنيف نصّ الخطأ صراحةً، وأُعيد التشغيل
فخرج FAIL بالرمز المطلوب وexit 1. **لا يوجد في المستودع ضبط حماية بكلمة مرور**
(لا `basic_auth` في `netlify.toml`، ولا `public/_headers`، ولا `_redirects`، ولا
edge function)، فأي حجب يظهر على النشر يكون مضبوطاً في لوحة Netlify خارج الشجرة —
وحينها **لا يجوز وصف الموقع بأنه مُتحقَّق منه علنياً**.

---

## 6. الأوامر التي يجب أن يشغّلها مشغّل على جهاز متّصل بالشبكة

```bash
git clone <repo> && cd acs
git checkout remediation/production-trust
npm ci                                   # playwright 1.62.1
npx playwright install chromium          # أو ثبّت PLAYWRIGHT_BROWSERS_PATH

# الحزمة كاملة، مع تثبيت المراجعة المتوقَّعة (يُفعّل G4 وG6):
sh tests/production/run_all.sh --expect-sha "$(git rev-parse HEAD)"
```

تشغيل كل طبقة وحدها:

```bash
python3 tests/production/verify_live.py \
  --frontend https://sprightly-selkie-d906c3.netlify.app \
  --backend  https://acs-engine.onrender.com \
  --expect-sha "$(git rev-parse HEAD)"

node tests/production/verify_live_browser.js \
  --frontend https://sprightly-selkie-d906c3.netlify.app \
  --expect-sha "$(git rev-parse HEAD)"
```

تجاوز الأهداف عبر البيئة بدل الوسائط:

```bash
ACS_VERIFY_FRONTEND=https://staging.example \
ACS_VERIFY_BACKEND=https://staging-api.example \
  sh tests/production/run_all.sh
```

**قراءة رمز الخروج:**

| exit | المعنى | ما يجب فعله |
| ---: | --- | --- |
| `0` | لا فشل مرصود، ورُصد شيء واحد على الأقل | يمكن اعتماد النشر بحدود ما رُصد |
| `1` | فشل مرصود | افتح `outputs/summary.json` واقرأ كل بند `"status": "FAIL"` |
| `2` | لم يُرصد شيء | شغّلها من شبكة تصل إلى الهدفين — لا تستنتج نجاحاً |

**قبل الاعتماد النهائي، شغّل أيضاً التوليد الحقيقي مرّة واحدة** (يستهلك نداءً
فعلياً للنموذج، ولذلك ليس جزءاً من هذه الحزمة):

```bash
python3 tests/deploy/verify_backend_live.py https://acs-engine.onrender.com --generation
```

---

## 7. ما لم تقُله هذه الحزمة

| البند | الحال |
| --- | --- |
| صحّة النشر الحيّ (frontend أو backend) | **غير معلومة** — 0 قياس، 47 NOT VERIFIED |
| هوية المراجعة المنشورة فعلاً على Netlify أو Render | **غير معلومة** — لم يُقرأ `/version` ولا `ACS_BUILD_INFO` من نشر حقيقي |
| توليد حقيقي عبر النموذج اللغوي (`POST /v1/understand`) | **خارج نطاق هذه الحزمة عمداً** — يستهلك رصيداً؛ استعمل `verify_backend_live.py --generation` |
| ظهور نموذج ثلاثي الأبعاد في نشر حقيقي | **غير معلوم** — لا Three.js مُعبَّأ هنا ولا وصول للنشر |
| هل الموقع محميّ بكلمة مرور؟ | **غير معلوم على النشر**؛ لكن لا ضبط حماية في الشجرة، والمِرقاب يُعلن `FRONTEND_ACCESS_RESTRICTED` إن وُجد |
| هل تُشحن الواجهة بأصل بناء (`window.ACS_BUILD_INFO`)؟ | **تُشحن بنيته، بلا هويّة** — الرموز النائبة لا يستبدلها أي بناء؛ رُصد `UNPROVENANCED` محلياً، ويُتوقَّع FAIL في G2/G5 عند التشغيل المتّصل |

**خلاصة واحدة:** هذه الحزمة نُفِّذت وعملت وأثبتت أنها تُميّز الصحيح من الخاطئ من
غير المرصود، لكنها **لم تقِس النشر الحيّ إطلاقاً**. أي جملة تقول «الإنتاج يعمل»
استناداً إلى هذا الملفّ تكون غير صحيحة.
