# -*- coding: utf-8 -*-
"""خادم ثابت صغير يطبّق سياسة محتوى حقيقية في ترويسة الاستجابة — لقياس CSP.

    python3 tools/csp_static_server.py <port> <dir> <csp-string> [overlay-dir]

لماذا لا يكفي <meta http-equiv>: الإنتاج يسلّم CSP في ترويسة استجابة Netlify،
و`frame-ancestors` و`report-uri` لا تعمل أصلاً في meta. قياس السياسة عبر meta
كان سيقيس سياسة أخرى غير المنشورة. هذا الصنف الفرعي من SimpleHTTPRequestHandler
يضع الترويسة نفسها حرفياً كما تضعها Netlify، فما يُقاس هو ما يُنشر.

<csp-string> فارغة ⇒ لا ترويسة سياسة أصلاً. هذا هو الوضع المستعمل لتشغيل
«الأصل الآخر» (منفذ ثانٍ على 127.0.0.1 = أصل مختلف فعلاً بحكم تعريف الأصل:
scheme+host+port)، فيكون حجب السكربت الخارجي منسوباً إلى CSP وحدها لا إلى فشل
DNS ولا إلى خادم غير موجود.

[overlay-dir] اختياري: جذر يُفتَّش قبل <dir>. يستعمله المسبار لتقديم كعب
Three.js للاختبار فقط (public/vendor فارغ في هذا المستودع ولا شبكة) دون كتابة
بايت واحد داخل public/ — فلا تتسرّب أدوات القياس إلى ما يُنشر.

مساران افتراضيان لا يُكتبان على القرص:
    /__csp_probe__/hostile.js   سكربت خارجي من نفس الأصل ينفّذ صنوف الهجوم
                                الثمانية من داخل سياق الصفحة الحقيقي.
    /__csp_probe__/external.js  الحمولة التي يقدّمها «الأصل الآخر» وحده.

127.0.0.1 فقط: لا يُفتح أي منفذ خارج الجهاز.
"""
import functools
import http.server
import os
import sys

# ───────────────────────────────────────────────────────────────────────────
# سكربت الهجوم: خارجي، من نفس الأصل ('self' تسمح به في السياسة المقيسة).
#
# ‼ منهجية — لماذا يعيش هذا في ملفّ يُحمَّل عبر <script src> ولا في
#   page.evaluate():  page.evaluate() يحقن الشيفرة عبر مصحّح CDP
#   (Runtime.evaluate) وهو مسار لا تحكمه CSP إطلاقاً. قياس eval() من داخل
#   page.evaluate يعيد EXECUTED حتى تحت سياسة تمنع eval منعاً تامّاً — نتيجة
#   سالبة كاذبة. الشيفرة هنا تُجلَب وتُترجَم بآلة السكربتات العادية للصفحة،
#   فتخضع للسياسة كما يخضع لها أي سكربت حقيقي.
#
#   METHODOLOGY (English, deliberately duplicated): this file is fetched by the
#   page as a same-origin <script src>. It is NOT injected with
#   page.evaluate(), because page.evaluate() goes through the CDP debugger,
#   which BYPASSES CSP entirely — eval() measured from inside page.evaluate()
#   reports EXECUTED even under a policy that forbids it. That is a false
#   negative. Do not move these attacks into page.evaluate().
# ───────────────────────────────────────────────────────────────────────────
HOSTILE_JS = r"""
/* ==========================================================================
   CSP probe driver — external, same-origin, NOT part of the application.

   Eight attack classes, each attempted as REAL CODE EXECUTION inside the real
   page, then reported through window.__CSP_PROBE__. Each attack sets a global
   flag; the flag is only true if the browser actually ran the payload.

   WARNING TO FUTURE MAINTAINERS: do not reimplement any of this inside
   page.evaluate(). page.evaluate() reaches the page through the CDP debugger,
   which is exempt from CSP. eval() and new Function() called from there run
   even under `script-src 'self'` and would be recorded as EXECUTED — a false
   negative that makes a strict policy look broken. Everything that must be
   *judged by the policy* has to be compiled by the page itself, i.e. here.
   ========================================================================== */
(function () {
  'use strict';

  var R = {
    done: false,
    attacks: {
      inline_script: 'NOT VERIFIED',
      eval: 'NOT VERIFIED',
      function_constructor: 'NOT VERIFIED',
      javascript_url: 'NOT VERIFIED',
      external_script: 'NOT VERIFIED',
      inline_event_handler: 'NOT VERIFIED',
      data_url_script: 'NOT VERIFIED',
      blob_script: 'NOT VERIFIED'
    },
    style: { cssom_property_write: 'NOT VERIFIED', style_attribute: 'NOT VERIFIED' },
    errors: {},
    notes: {}
  };
  window.__CSP_PROBE__ = R;

  /* أصل السكربت الخارجي يصل عبر استعلام على src هذا الملفّ نفسه — لا متغيّر
     عالميّ يُزرع من خارج الصفحة، فيبقى كل شيء داخل مسار سكربت حقيقي. */
  var ext = '';
  try {
    var src = (document.currentScript && document.currentScript.src) || '';
    var i = src.indexOf('?ext=');
    if (i >= 0) ext = decodeURIComponent(src.slice(i + 5));
  } catch (e) { /* يُسجَّل أدناه بوصفه غياباً */ }
  R.notes.external_origin = ext || '(none supplied)';
  R.notes.self_origin = location.origin;

  function verdict(name, flagName) {
    R.attacks[name] = (window[flagName] === true) ? 'EXECUTED' : 'BLOCKED';
  }
  function err(name, e) {
    R.errors[name] = String((e && e.message) || e).slice(0, 200);
  }

  /* ── 1 · حقن <script> مضمَّن ─────────────────────────────────────────── */
  window.__ACS_ATK_INLINE__ = false;
  try {
    var s1 = document.createElement('script');
    s1.textContent = 'window.__ACS_ATK_INLINE__ = true;';
    document.head.appendChild(s1);
    s1.parentNode.removeChild(s1);
  } catch (e) { err('inline_script', e); }
  verdict('inline_script', '__ACS_ATK_INLINE__');

  /* ── 2 · eval() ─────────────────────────────────────────────────────── */
  window.__ACS_ATK_EVAL__ = false;
  try {
    /* eslint-disable no-eval */
    (0, eval)('window.__ACS_ATK_EVAL__ = true;');
  } catch (e) { err('eval', e); }
  verdict('eval', '__ACS_ATK_EVAL__');

  /* ── 3 · new Function() ─────────────────────────────────────────────── */
  window.__ACS_ATK_FN__ = false;
  try {
    (new Function('window.__ACS_ATK_FN__ = true;'))();
  } catch (e) { err('function_constructor', e); }
  verdict('function_constructor', '__ACS_ATK_FN__');

  /* ── 6 · سمة معالج حدث مضمَّن (onclick=) ────────────────────────────── */
  window.__ACS_ATK_HANDLER__ = false;
  try {
    var b = document.createElement('button');
    b.setAttribute('onclick', 'window.__ACS_ATK_HANDLER__ = true;');
    b.setAttribute('type', 'button');
    document.body.appendChild(b);
    b.click();
    R.notes.inline_handler_compiled = (typeof b.onclick === 'function');
    b.parentNode.removeChild(b);
  } catch (e) { err('inline_event_handler', e); }
  verdict('inline_event_handler', '__ACS_ATK_HANDLER__');

  /* ── الأنماط: CSSOM مقابل سمة style ─────────────────────────────────── */
  try {
    var d1 = document.createElement('div');
    document.body.appendChild(d1);
    d1.style.color = 'rgb(4, 5, 6)';                       /* CSSOM property */
    R.style.cssom_property_write =
      (getComputedStyle(d1).color === 'rgb(4, 5, 6)') ? 'ALLOWED' : 'BLOCKED';
    d1.parentNode.removeChild(d1);

    var d2 = document.createElement('div');
    d2.setAttribute('style', 'color: rgb(7, 8, 9)');       /* style attribute */
    document.body.appendChild(d2);
    R.style.style_attribute =
      (getComputedStyle(d2).color === 'rgb(7, 8, 9)') ? 'ALLOWED' : 'BLOCKED';
    R.notes.style_attribute_survived_in_dom = d2.hasAttribute('style');
    d2.parentNode.removeChild(d2);
  } catch (e) { err('style', e); }

  /* ── 4 · تفعيل رابط javascript: ─────────────────────────────────────── */
  window.__ACS_ATK_JSURL__ = false;
  var jsurlNode = null;
  try {
    var a = document.createElement('a');
    /* التعبير يعيد قيمة غير نصّية عمداً، فلا يستبدل المستند إن نُفِّذ. */
    a.setAttribute('href', 'javascript:void(window.__ACS_ATK_JSURL__ = true)');
    a.textContent = 'probe';
    document.body.appendChild(a);
    a.click();
    jsurlNode = a;                            /* يُزال في مرحلة الاستقرار */
  } catch (e) { err('javascript_url', e); }

  /* ── التحميلات غير المتزامنة: 5 خارجي · 7 data: · 8 blob: ───────────── */
  var pending = 0, settled = false;
  function one(name, src, note) {
    pending++;
    var sc = document.createElement('script');
    var fin = function (how) {
      if (sc.__done) return;
      sc.__done = true;
      R.notes[name + '_load_event'] = how;
      if (--pending === 0) settle();
    };
    sc.onload = function () { fin('load'); };
    sc.onerror = function () { fin('error'); };
    if (note) R.notes[name + '_src'] = note;
    try {
      sc.src = src;
      document.head.appendChild(sc);
    } catch (e) { err(name, e); fin('threw'); }
    /* مهلة صلبة: بعض صور الحجب لا تطلق load ولا error إطلاقاً. */
    setTimeout(function () { fin('timeout'); }, 4000);
  }

  window.__ACS_ATK_EXTERNAL__ = false;
  window.__ACS_ATK_DATA__ = false;
  window.__ACS_ATK_BLOB__ = false;

  if (ext) {
    one('external_script', ext + '/__csp_probe__/external.js',
        ext + '/__csp_probe__/external.js');
  } else {
    R.notes.external_script_reason = 'no second origin was supplied to the probe';
  }

  one('data_url_script',
      'data:text/javascript,' + encodeURIComponent('window.__ACS_ATK_DATA__ = true;'),
      'data:text/javascript,<payload>');

  try {
    var blobUrl = URL.createObjectURL(
      new Blob(['window.__ACS_ATK_BLOB__ = true;'], { type: 'text/javascript' }));
    R.notes.blob_url_created = true;
    one('blob_script', blobUrl, blobUrl.slice(0, 18) + '…');
  } catch (e) {
    err('blob_script', e);
    R.notes.blob_url_created = false;
  }

  function settle() {
    if (settled) return;
    settled = true;
    /* مهلة قصيرة أخيرة: تنفيذ رابط javascript: يجري كمهمّة تنقّل مؤجَّلة. */
    setTimeout(function () {
      if (ext) verdict('external_script', '__ACS_ATK_EXTERNAL__');
      verdict('data_url_script', '__ACS_ATK_DATA__');
      verdict('blob_script', '__ACS_ATK_BLOB__');
      verdict('javascript_url', '__ACS_ATK_JSURL__');
      try {
        if (jsurlNode && jsurlNode.parentNode) {
          jsurlNode.parentNode.removeChild(jsurlNode);
        }
      } catch (e) { /* لا شيء يُدَّعى */ }
      R.done = true;
    }, 600);
  }
  if (pending === 0) settle();
})();
"""

# حمولة «الأصل الآخر». تُقدَّم من منفذ ثانٍ بلا ترويسة CSP إطلاقاً، فإن حُجبت
# فالسبب هو سياسة الصفحة المستقبِلة لا الخادم المقدِّم.
EXTERNAL_JS = "window.__ACS_ATK_EXTERNAL__ = true;\n"


class CSPHandler(http.server.SimpleHTTPRequestHandler):
    csp = ""
    overlay = ""

    def end_headers(self):
        if self.csp:
            self.send_header("Content-Security-Policy", self.csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        http.server.SimpleHTTPRequestHandler.end_headers(self)

    def _send_js(self, text):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _overlay_path(self, url_path):
        """مسار الطبقة العلوية إن وُجد فيها ملفّ يطابق الطلب."""
        if not self.overlay:
            return None
        rel = url_path.split("?")[0].split("#")[0].lstrip("/")
        if not rel:
            return None
        root = os.path.realpath(self.overlay)
        cand = os.path.realpath(os.path.join(root, rel))
        # لا خروج من الجذر عبر ../
        if cand != root and not cand.startswith(root + os.sep):
            return None
        return cand if os.path.isfile(cand) else None

    def do_GET(self):                                             # noqa: N802
        path = self.path.split("?")[0]
        if path == "/__csp_probe__/hostile.js":
            self._send_js(HOSTILE_JS)
            return
        if path == "/__csp_probe__/external.js":
            self._send_js(EXTERNAL_JS)
            return
        over = self._overlay_path(self.path)
        if over:
            try:
                with open(over, "rb") as f:
                    body = f.read()
            except OSError:
                self.send_error(404)
                return
            ctype = self.guess_type(over)
            if over.endswith(".js") or over.endswith(".mjs"):
                ctype = "text/javascript; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        http.server.SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, fmt, *args):                            # صمت
        pass


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    port, root, csp = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    overlay = sys.argv[4] if len(sys.argv) > 4 else ""
    if not os.path.isdir(root):
        print("no such directory: %s" % root)
        return 2
    if overlay and not os.path.isdir(overlay):
        print("no such overlay directory: %s" % overlay)
        return 2
    handler = functools.partial(CSPHandler, directory=root)
    CSPHandler.csp = csp
    CSPHandler.overlay = overlay
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    sys.stderr.write("CSP_SERVER_READY %d\n" % srv.server_address[1])
    sys.stderr.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
