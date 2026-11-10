/* ACS entry. Account review is lightweight and owns no legacy WebGL context.
   Local guest/test modules are declared in tools/frontend_local.txt and loaded
   by ui/local-studio-entry.mjs only. Optional local panels remain declared in
   tools/frontend_lazy.txt. Graph guards verify both routes and their ordering. */
import './shared-state.js';
import './late-bindings.js';
/* Register the 2D project lifecycle before legacy WebGL initialization.
   A device without WebGL must retain review, approval and file export. */
import './core/plan-review-packet.mjs';
import './ui/approved-viewer.mjs';
import './generated/requirement-metrics.mjs';
import './core/brief-program.mjs';
import './core/residential-program.mjs';
import './ui/residential-options.mjs';
import './ui/brief-review.mjs';
import './ui/plan-upload.mjs';
import './ui/connected-workspace.mjs';
/* Expose server-held stable nested locks (racks/docks/lanes/cores/etc.) through
   the same single entry; lock authority remains in the canonical command path. */
import './ui/connected-semantic-locks.mjs';
/* Local preview owns the legacy renderer; account entry never initializes it. */
import './ui/local-studio-entry.mjs';
