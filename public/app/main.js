/* ============================================================
   public/app/main.js — نقطة دخول التطبيق.
   ترتيب الاستيراد هو ترتيب المقاطع في الصفحة الأصلية بالضبط، فالتقييم
   يجري بالتتابع نفسه. لا منطق هنا: الوحدات هي المنطق.
   ============================================================ */
import './core/viewer.js';
import './core/standards.js';
import './core/disciplines.js';
import './generated/runtime.js';
import './generated/authoring.js';
import './generated/workspace-ui.js';
import './generated/render-engine.js';
import './generated/bim.js';
import './generated/docs.js';
import './generated/pbr.js';
import './generated/arch-detail.js';
import './render/scene.js';
import './generated/pbr-bridge.js';
import './generated/arch-detail-bridge.js';
import './ui/workspace-ui-wiring.js';
import './trust/core.js';
import './trust/wiring.js';
