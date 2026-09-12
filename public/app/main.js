/* ============================================================
   public/app/main.js — نقطة دخول التطبيق.
   ترتيب الاستيراد هو ترتيب المقاطع في الصفحة الأصلية بالضبط، فالتقييم
   يجري بالتتابع نفسه. لا منطق هنا: الوحدات هي المنطق.

   KI-12 (مُغلَق): ستّ وحدات لم تعد هنا — generated/workspace-ui.js و
   generated/render-engine.js و generated/bim.js و generated/docs.js و
   generated/arch-detail.js و generated/arch-detail-bridge.js. هي مُعلَنة في tools/frontend_lazy.txt
   وتُجلَب بنداء import() واحد من ui/panels-entry.js عند أوّل فتح للوحتها.
   ترتيب هذا الملفّ لِما بقي لم يتغيّر بسطر: الوحدات المؤجَّلة كانت في مؤخّرة
   الترتيب ولا يقرأ أحدٌ رموزها، فحذفها من هنا لا يحرّك تقييم أي وحدة أخرى.
   ============================================================ */
import './shared-state.js';
import './late-bindings.js';
import './core/viewer.js';
import './core/standards.js';
import './core/disciplines.js';
import './generated/runtime.js';
import './generated/authoring.js';
import './generated/pbr.js';
import './render/scene.js';
/* Warehouse Pipeline v2 exact sub-element identity contract. The module is
   side-effect free; exact identity is admitted only from explicit canonical ids. */
import './render/warehouse-canonical-identity.js';
import './generated/pbr-bridge.js';
import './ui/workspace-ui-wiring.js';
import './trust/core.js';
import './trust/wiring.js';
/* F-27: مداخل لوحات المراحل ٦…٩٫٢. يأتي أخيراً لأنه يقرأ
   window.ACS.workspace و window.ACS.{render,bim,docs,pbr,archdetail}.panel
   التي تنشرها الوحدات أعلاه، و window.ACS.exportModel التي ينشرها
   ui/workspace-ui-wiring.js. */
import './ui/panels-entry.js';
/* The index guard requires every eager module under /app to be declared directly
   here. This module is side-effect-free; the runtime wrapper below imports the
   same ESM instance and installs it against the live renderer/workspace. */
import './ui/workspace-viewport-selection.js';
/* Viewport selection reuses the existing renderer + lazy Phase 6 workspace.
   It adds presentation-only hit/highlight wiring and never writes model JSON. */
import './ui/workspace-viewport-selection-runtime.js';
/* Residential visual-quality policy. It runs after the panel lazy-loader exists. */
import './ui/residential-quality.js';
/* Recover long generation through short authenticated job requests. */
import './ui/generation-jobs.js';
