# Presentation-only view controls

The material viewer previously offered orbiting plus a top-roof cutaway, but no floor selector or named camera views. Its fixed radial fit did not account for portrait horizontal field of view. A separate baseline check of the pinned Three.js bundle also returned two ray hits on an invisible box: invisible meshes must explicitly be excluded from picking, including hidden ancestors.

This release adds a display-only floor selector, six perspective camera presets and reset-to-fit. Individual-floor views hide other floors and all site objects; they do not move a floor down to ground, remove its walls, change canonical coordinates, or create a revision. Full-site/all-floors remains the default. The compass names refer to model axes, not verified survey north or the street direction. The overhead view remains perspective, not an orthographic drawing or construction elevation.

Eight bounding corners are fitted against both horizontal and vertical FOV, with margin. Named views refit for viewport changes; a user's manual orbit/pan ends automatic framing until reset. Hidden roofs/floors/ancestors are excluded from ray picking. PNG captures the selected display and identifies floor number and roof visibility; complete GLB always contains all canonical floors, roofs and original material colours independently of visibility/selection. Changing scene settings disables view controls and downloads until rebuilding the material scene. Reopening starts a new viewer.

The product's canonical model, full brief, history, manual edits, locks and original objects are unchanged by these controls. No AI provider, cloud worker, paid service or durable hosting is enabled. Source JSON remains the editable project backup. Geometry/fit checks are not architectural, access, privacy, fire, MEP or regulatory approval.

Test entry points: npm test; MASAR_BROWSER=chromium python tests/view_controls_browser.py; MASAR_BROWSER=webkit python tests/view_controls_browser.py. MASAR_ACCEPTANCE_URL may point to the published non-account preview. Chromium covers software WebGL display, actual PNG and complete GLB downloads. WebKit covers UI/disabled-state/source/history only; physical iPhone rendering/gestures are not claimed. A separate renderer harness deliberately uses overlapping synthetic boxes solely to prove hidden picking cannot win.

No local browser acceptance is claimed where this environment blocks localhost with ERR_BLOCKED_BY_ADMINISTRATOR. The permitted GitHub CI environment is used for browser acceptance without altering that local policy.
