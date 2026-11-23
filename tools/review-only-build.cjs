'use strict';
// Netlify ignore: exit0 stops a build; exit1 continues normal build selection.
// Limit the owner's no-deploy instruction to this dated review series.
const reviewOnly = [process.env.BRANCH, process.env.HEAD].some(
  ref => /^claude\/acs-[a-z0-9-]+-20261111$/.test(ref || '')
);
if (reviewOnly) console.log('Review-only ACS branch: deployment intentionally skipped.');
process.exitCode = reviewOnly ? 0 : 1;
