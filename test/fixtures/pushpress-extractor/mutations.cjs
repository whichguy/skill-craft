'use strict';

// Deliberately broken copies of skills/pushpress/scripts/pp-extract.js, shared by the real-browser fixture and the property test.
// Each removes one protection that the live pass or the harness found necessary; a test that stays green on its copy is blind to
// that protection. `from` must occur exactly once in the extractor: when it does not, the control is stale and the caller must say so.
// `tests` names the tests that must catch it: 'fixture' (privacy-fixture.cjs) and 'property' (test/pushpress-extractor-property.js).
const MUTATIONS = [
  { name: 'no-person-scrub', tests: ['fixture', 'property'], from: 'if (!onPerson()) return [];', to: 'return [];' },
  { name: 'fixed-290px-edge', tests: ['fixture', 'property'], from: 'const sideEdge = () => {', to: 'const sideEdge = () => { return 290;' },
  { name: 'sidebar-not-parked', tests: ['fixture', 'property'], from: "dumpEl().textContent = '### sidebar\\n' + out.join('\\n');", to: '' },
  { name: 'combobox-values-recorded', tests: ['fixture', 'property'], from: "person && e.getAttribute('role') === 'combobox'", to: "false && e.getAttribute('role') === 'combobox'" },
  { name: 'user-menu-listed', tests: ['fixture', 'property'], from: "if (el.tagName === 'BUTTON' && !names.includes(clean(el.innerText))) return;", to: '' },
];

function apply(source, mutation) {
  const parts = source.split(mutation.from);
  if (parts.length !== 2) return null;                                       // stale: the text it breaks is gone or no longer unique
  return parts.join(mutation.to);
}

module.exports = { MUTATIONS, apply };
