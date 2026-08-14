# -*- coding: utf-8 -*-
"""خادم ثابت صغير يطبّق سياسة محتوى حقيقية في ترويسة الاستجابة — لقياس CSP.

    python3 tools/csp_static_server.py <port> <dir> <csp-string>

لماذا لا يكفي <meta http-equiv>: الإنتاج يسلّم CSP في ترويسة استجابة Netlify،
و`frame-ancestors` و`report-uri` لا تعمل أصلاً في meta. قياس السياسة عبر meta
كان سيقيس سياسة أخرى غير المنشورة. هذا الصنف الفرعي من SimpleHTTPRequestHandler
يضع الترويسة نفسها حرفياً كما تضعها Netlify، فما يُقاس هو ما يُنشر.

يخدم أيضاً مساراً واحداً افتراضياً `/__csp_probe__/hostile.js`: سكربت خارجي من
نفس الأصل يجرّب eval()/new Function() ويسجّل النتيجة. وجوده افتراضي عمداً — لا
يُكتب أي ملفّ داخل public/، فلا يتسرّب شيء من أدوات القياس إلى ما يُنشر.

127.0.0.1 فقط: لا يُفتح أي منفذ خارج الجهاز.
"""
import functools
import http.server
import os
import sys

# سكربت خارجي من نفس الأصل ('self' يسمح به في كل السياسات المقيسة). يفصل
# قياس 'unsafe-eval' عن قياس 'unsafe-inline': حين يُحجب المضمَّن، يبقى هذا
# السكربت قابلاً للتحميل، فيُقاس eval() وحده بلا خلط بين السببين.
HOSTILE_JS = """
/* CSP probe — external, same-origin. Not part of the application. */
(function () {
  var out = { external_script_ran: true, eval_ran: null, function_ctor_ran: null,
              eval_error: null, function_ctor_error: null };
  try { eval('window.__CSP_PROBE_EVAL__ = true'); out.eval_ran = (window.__CSP_PROBE_EVAL__ === true); }
  catch (e) { out.eval_ran = false; out.eval_error = String(e && e.message).slice(0, 160); }
  try { (new Function('window.__CSP_PROBE_FN__ = true'))(); out.function_ctor_ran = (window.__CSP_PROBE_FN__ === true); }
  catch (e) { out.function_ctor_ran = false; out.function_ctor_error = String(e && e.message).slice(0, 160); }
  window.__CSP_PROBE_EXTERNAL__ = out;
})();
"""


class CSPHandler(http.server.SimpleHTTPRequestHandler):
    csp = ""

    def end_headers(self):
        if self.csp:
            self.send_header("Content-Security-Policy", self.csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        http.server.SimpleHTTPRequestHandler.end_headers(self)

    def do_GET(self):                                             # noqa: N802
        if self.path.split("?")[0] == "/__csp_probe__/hostile.js":
            body = HOSTILE_JS.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
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
    if not os.path.isdir(root):
        print("no such directory: %s" % root)
        return 2
    handler = functools.partial(CSPHandler, directory=root)
    CSPHandler.csp = csp
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
