# Verification protocol — MASAR 4.1.0

The release job generates reports from the exact committed source. This protocol
must not be substituted for execution evidence.

Gates: JavaScript syntax/served-script policy; deterministic standalone rebuild;
Node model/API/ownership/concurrency/backup suites; standalone browser flows;
real-HTTP browser tests on Chromium/Firefox/WebKit including SQLite, IndexedDB,
review, conflicts and offline PWA; independent IFC4 EXPRESS and geometry matrix;
non-root Docker image + persistent-volume replacement + backup/restore lifecycle.

Known environment distinctions: local standalone tests use real Chromium rendering
with set_content because localhost browser URL navigation is blocked in that
container. Those tests do not prove browser-origin persistence. The HTTP suite runs
in CI on its own disposable local origin and records browser engine/renderer.
External IFC tests use IfcOpenShell 0.8.5, not the app's own parser as an oracle.

A failed test is a failed gate. Test logs include initial failures and corrections;
no run is counted as successful simply because a report was produced. The release
archive and standalone HTML must be derived from the same source, with hashes and
rebuild comparison. Deployed cloud persistence, paid AI, real iPhone hardware and
regulatory approval remain separate evidence requirements.
