/* Runtime wiring only. Selection/mapping logic stays browser-agnostic in
   workspace-viewport-selection.js so identity contracts can run without WebGL. */
import { THREE } from '../core/viewer.js';
import { __ACS_LATE } from '../late-bindings.js';
import { renderer, scene } from '../render/scene.js';
import { openWorkspace } from './panels-entry.js';
import { installWorkspaceViewportSelection } from './workspace-viewport-selection.js';

installWorkspaceViewportSelection({
  THREE,
  renderer,
  scene,
  late: __ACS_LATE,
  openWorkspace,
});
