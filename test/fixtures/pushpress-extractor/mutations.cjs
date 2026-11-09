'use strict';

// Deliberately broken copies of skills/pushpress/scripts/pp-extract.js, shared by the real-browser fixture and the property test.
// Each removes one protection that the live pass or the harness found necessary; a test that stays green on its copy is blind to
// that protection. `from` must occur exactly once in the extractor: when it does not, the control is stale and the caller must say so.
//
// A control counts as caught only when the test fails FOR THE RIGHT REASON: `expect` names what each test must report for this
// mutation (a crash, a syntax error or an unrelated failure must read as an error, never as a catch).
//   property: property tags the test prints (P1 contract, P2 structure, P3 edge, P4 icons, P5 path, P6 sidebar ...)
//   fixture:  'leak:<label prefix>' (a planted value of that kind reached a field) or 'problem:<text>' (a structure or sidebar problem)
// `tests` names the tests that must catch it: 'fixture' (privacy-fixture.cjs) and 'property' (test/pushpress-extractor-property.js).
const MUTATIONS = [
  { name: 'no-person-scrub', tests: ['fixture', 'property'], expect: { property: ['P1 contract'], fixture: ['leak:owner'] },
    from: 'if (!onPerson()) return [];', to: 'return [];' },
  { name: 'fixed-290px-edge', tests: ['fixture', 'property'], expect: { property: ['P2 structure', 'P3 edge'], fixture: ['problem:lacks'] },
    from: 'const sideEdge = () => {', to: 'const sideEdge = () => { return 290;' },
  { name: 'sidebar-not-parked', tests: ['fixture', 'property'], expect: { property: ['P6 sidebar'], fixture: ['problem:did not park'] },
    from: "dumpEl().textContent = '### sidebar\\n' + out.join('\\n');", to: '' },
  { name: 'combobox-values-recorded', tests: ['fixture', 'property'], expect: { property: ['P1 contract'], fixture: ['leak:combo'] },
    from: "person && e.getAttribute('role') === 'combobox'", to: "false && e.getAttribute('role') === 'combobox'" },
  { name: 'user-menu-listed', tests: ['fixture', 'property'], expect: { property: ['P6 sidebar'], fixture: ['leak:staff'] },
    from: "if (el.tagName === 'BUTTON' && !names.includes(clean(el.innerText))) return;", to: '' },
  { name: 'named-icon-buttons-counted-as-unnamed', tests: ['fixture', 'property'], expect: { property: ['P4 icons'], fixture: ['problem:icon-only'] },
    from: "!clean(b.innerText) && !b.getAttribute('aria-label') && !b.title", to: '!clean(b.innerText) && !b.title' },
];

function apply(source, mutation) {
  const parts = source.split(mutation.from);
  if (parts.length !== 2) return null;                                       // stale: the text it breaks is gone or no longer unique
  return parts.join(mutation.to);
}

module.exports = { MUTATIONS, apply };
