/* ============================================================================
   public/app/boot/style-bridge.js — تطبيق الهندسة الديناميكية تحت
   `style-src 'self'` بلا إضعاف السياسة (F-30 · KI-13).

   المشكلة
   -------
   السياسة الإنتاجية تحوي `style-src 'self'` بلا 'unsafe-inline'. المتصفّح
   يحجب بذلك **سمة** style مهما كان طريق وصولها: مكتوبةً في العلامة، أو
   عبر setAttribute('style',…), أو داخل نصّ يُسنَد إلى innerHTML. الطبقات
   المولَّدة كانت تحقن `style="left:…%;top:…%"` داخل innerHTML، فكانت تُحجَب
   صامتةً: العنصر يظهر في DOM بلا هندسته. أوضح أثر: كل عرض لوحة في التوثيق
   ينهار إلى ‎0×0‎ في الزاوية.

   لماذا CSSOM هو المخرج الصحيح
   ---------------------------
   `style-src` يحكم **سمة** style ولا يحكم واجهة CSSOM. قِيس في هذا المستودع
   في Chromium حقيقيّ بالسياسة الإنتاجية نفسها كرأس استجابة
   (tests/remediation/test_csp_style_architecture.js §١):

     element.style.left = '12.5%'                → طُبِّق  · صفر خرق
     element.style.setProperty('aspect-ratio',…) → طُبِّق  · صفر خرق
     element.setAttribute('style','color:red')   → لم يُطبَّق (محجوب)
     innerHTML يحمل style="…"                    → لم يُطبَّق (محجوب)

   فالحلّ ليس تخفيف السياسة بل نقل القيم الديناميكية من **سمة** إلى **واجهة**.

   العقد
   -----
   العلامة المولَّدة تحمل `data-acs-style="prop:value;prop:value"` بدل
   `style="…"`. بعد أي كتابة إلى innerHTML يُستدعى:

       ACS_STYLE.apply(container)

   فيمرّ على العنصر وذرّيته ويطبّق ما في السمة عبر setProperty.

   لماذا قائمة سماح — وهذه إضافة لم تكن موجودة أصلاً
   -----------------------------------------------
   القيم تأتي من النموذج، والنموذج يأتي من وصف المستخدم أو ملفّ مرفوع. سمة
   style الأصلية كانت تُدرَج بلا أي تحقّق. هنا لا يُطبَّق إلا:
     · اسم خاصيّة من قائمة معلنة صراحةً (أو خاصيّة مخصّصة ‎--acs-*‎)،
     · وقيمة تطابق نمطاً ضيّقاً: عدد بوحدة، أو نسبة a/b، أو لون سداسيّ،
       أو var(--اسم) من مساحة أسماء المشروع، أو كلمة مفتاحية بسيطة.
   ما عدا ذلك يُسقَط ويُعدّ في ACS_STYLE.stats() بدل أن يمرّ صامتاً — فلا
   يصير هذا الجسر ثغرة حقن بديلة عمّا أغلقته السياسة.
   ========================================================================== */
(function () {
  'use strict';

  /* الخصائص المسموح تعيينها. القائمة مقصورة على ما تحتاجه الطبقات فعلاً:
     هندسة وتخطيط وشفافية — لا خصائص تحمّل موارد خارجية ولا سلوكاً. */
  var ALLOWED = {
    'left': 1, 'top': 1, 'right': 1, 'bottom': 1,
    'width': 1, 'height': 1, 'min-width': 1, 'min-height': 1,
    'max-width': 1, 'max-height': 1,
    'aspect-ratio': 1, 'opacity': 1, 'z-index': 1, 'order': 1,
    'margin': 1, 'margin-top': 1, 'margin-bottom': 1,
    'margin-inline-start': 1, 'margin-inline-end': 1,
    'padding': 1, 'padding-top': 1, 'padding-bottom': 1,
    'padding-inline-start': 1, 'padding-inline-end': 1,
    'inset-inline-start': 1, 'inset-inline-end': 1,
    'flex-basis': 1, 'flex-grow': 1, 'grid-column': 1, 'grid-row': 1,
    'transform': 1, 'color': 1, 'background-color': 1, 'border-color': 1,
    'font-size': 1, 'line-height': 1, 'gap': 1
  };

  /* عدد بوحدة (12، 12.5%، -3px، 0)، أو نسبة a/b لِـaspect-ratio. */
  var NUMBER = /^-?\d+(\.\d+)?(px|%|em|rem|vw|vh|vmin|vmax|fr|deg|ch)?$/;
  var RATIO = /^\d+(\.\d+)?\s*\/\s*\d+(\.\d+)?$/;
  var HEXCOL = /^#[0-9a-fA-F]{3,8}$/;
  /* var(--x) و var(--x, fallback-بسيط) — أسماء متغيّرات المشروع وحدها. */
  var VARREF = /^var\(--[a-z0-9-]+(\s*,\s*[-#a-z0-9.%\s]+)?\)$/i;
  var KEYWORD = /^[a-z-]{1,24}$/;
  /* translate/translateX/translateY/scale/rotate بأعداد ووحدات فقط. */
  var TRANSFORM = /^(translate|translateX|translateY|scale|rotate)\(\s*-?\d+(\.\d+)?(px|%|deg)?\s*(,\s*-?\d+(\.\d+)?(px|%|deg)?\s*)?\)$/;

  var dropped = 0, applied = 0;

  function valueOk(prop, value) {
    if (value.length > 64) return false;
    /* لا دوالّ تُحمّل موارد ولا هروب من القيمة إلى تصريح آخر. */
    if (/[;{}<>\\]/.test(value)) return false;
    if (/url\s*\(|expression\s*\(|image-set|@import/i.test(value)) return false;
    if (prop === 'aspect-ratio') return RATIO.test(value) || NUMBER.test(value);
    if (prop === 'transform') return TRANSFORM.test(value);
    /* الخاصيّة المخصّصة تُمرَّر بـprop فارغ لأن اسمها ليس في قائمة السماح، لكنّ
       قيمتها تخضع للقواعد نفسها — ومنها النسبة a/b: `--dc-sheet-ar:420/297`
       هي بالضبط ما تحتاجه لوحة التوثيق. إغفال RATIO هنا كان يُسقط القيمة
       بصمت فتعود اللوحة إلى الاحتياطي — عطلٌ اصطاده اختبار §٧ب بمقارنة
       aspect-ratio المحسوبة بمقاس الورق المعلن. */
    return NUMBER.test(value) || RATIO.test(value) || HEXCOL.test(value)
      || VARREF.test(value) || KEYWORD.test(value);
  }

  /* يطبّق تصريحات على عنصر واحد عبر CSSOM. يعيد عدد ما طُبِّق. */
  function set(el, decls) {
    if (!el || !el.style || !decls) return 0;
    var n = 0;
    var parts = String(decls).split(';');
    for (var i = 0; i < parts.length; i++) {
      var piece = parts[i];
      if (!piece) continue;
      var at = piece.indexOf(':');
      if (at < 0) { dropped++; continue; }
      var prop = piece.slice(0, at).trim().toLowerCase();
      var value = piece.slice(at + 1).trim();
      if (!prop || !value) { dropped++; continue; }
      var custom = prop.indexOf('--acs-') === 0 || prop.indexOf('--ws-') === 0
        || prop.indexOf('--dc-') === 0;
      if (!custom && ALLOWED[prop] !== 1) { dropped++; continue; }
      if (!valueOk(custom ? '' : prop, value)) { dropped++; continue; }
      try { el.style.setProperty(prop, value); n++; applied++; }
      catch (e) { dropped++; }
    }
    return n;
  }

  /* يمرّ على الجذر وذرّيته ويطبّق كل data-acs-style مرّة واحدة.
     السمة تُحذف بعد التطبيق: إعادة استدعاء apply على نفس الشجرة لا تكرّر عملاً،
     ووجود السمة يعني دائماً «لم تُطبَّق بعد» — حالة يفحصها اختبار الانحدار. */
  function apply(root) {
    if (typeof document === 'undefined') return 0;
    var scope = root || document;
    var n = 0;
    if (scope.nodeType === 1 && scope.hasAttribute
        && scope.hasAttribute('data-acs-style')) {
      n += set(scope, scope.getAttribute('data-acs-style'));
      scope.removeAttribute('data-acs-style');
    }
    var list = scope.querySelectorAll
      ? scope.querySelectorAll('[data-acs-style]') : [];
    for (var i = 0; i < list.length; i++) {
      n += set(list[i], list[i].getAttribute('data-acs-style'));
      list[i].removeAttribute('data-acs-style');
    }
    return n;
  }

  /* يكتب innerHTML ثم يطبّق الهندسة فوراً — الاستعمال الموصى به، فلا يمكن
     أن يُنسى النداء الثاني بعد الأوّل. */
  function html(el, markup) {
    if (!el) return 0;
    el.innerHTML = markup;
    return apply(el);
  }

  var API = {
    apply: apply,
    set: set,
    html: html,
    allowed: function () { return Object.keys(ALLOWED).slice(); },
    stats: function () { return { applied: applied, dropped: dropped }; },
    /* عقد مُعلَن يقرؤه اختبار الانحدار بدل أن يعيد كتابته. */
    contract: {
      mechanism: 'CSSOM setProperty',
      governed_by_style_src: false,
      attribute: 'data-acs-style',
      reason: 'style-src governs the style ATTRIBUTE, not the CSSOM interface; '
        + 'measured in real Chromium under the production policy',
      never_uses: ['style attribute in markup', 'setAttribute("style")',
        'unsafe-inline', 'style-src-attr unsafe-inline']
    }
  };

  /* سكربت إقلاع كلاسيكيّ كبقيّة boot/: النشر على window وحده. لا تصدير
     CommonJS — الاسم `module` معرّفٌ حرّ في المتصفّح، ويرفضه بحقّ
     tests/remediation/test_module_graph.js §٤. */
  if (typeof window !== 'undefined') {
    window.ACS_STYLE = API;
    window.ACS = window.ACS || {};
    window.ACS.styleBridge = API;
  }
})();
