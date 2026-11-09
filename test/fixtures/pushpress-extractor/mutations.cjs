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
// `cases` (fixture only) lists the fixture cases that exercise the protection, so a control runs a few pages instead of all of them.
const MUTATIONS = [
  { name: 'no-person-scrub', tests: ['fixture', 'property'], cases: ['person/plain'], expect: { property: ['P1 contract'], fixture: ['leak:owner'] },
    from: 'if (!onPerson()) return [];', to: 'return [];' },
  { name: 'fixed-290px-edge', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P2 structure', 'P3 edge'], fixture: ['problem:lacks'] },
    from: 'const sideEdge = () => {', to: 'const sideEdge = () => { return 290;' },
  { name: 'sidebar-not-parked', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P6 sidebar'], fixture: ['problem:did not park'] },
    from: "dumpEl().textContent = '### sidebar\\n' + out.join('\\n');", to: '' },
  { name: 'combobox-values-recorded', tests: ['fixture', 'property'], cases: ['person/plain'], expect: { property: ['P1 contract'], fixture: ['leak:combo'] },
    from: "person && e.getAttribute('role') === 'combobox'", to: "false && e.getAttribute('role') === 'combobox'" },
  { name: 'user-menu-listed', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P6 sidebar'], fixture: ['leak:staff'] },
    from: "if (el.tagName === 'BUTTON' && !names.includes(clean(el.innerText))) return;", to: '' },
  { name: 'headings-cap-removed', tests: ['property'], expect: { property: ['P4 caps'] },
    from: "[role=heading]').map(e => safe(e.innerText))).slice(0, 25),", to: "[role=heading]').map(e => safe(e.innerText)))," },
  { name: 'buttons-cap-removed', tests: ['property'], expect: { property: ['P4 caps'] },
    from: '.filter(b => !isChrome(b)).slice(0, 45),', to: '.filter(b => !isChrome(b)),' },
  { name: 'named-icon-buttons-counted-as-unnamed', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P4 icons'], fixture: ['problem:icon-only'] },
    from: "!clean(b.innerText) && !b.getAttribute('aria-label') && !b.title", to: '!clean(b.innerText) && !b.title' },
  // masks that a third review round showed no generated page exercised: removing each must now be noticed
  { name: 'title-not-scrubbed', tests: ['fixture', 'property'], cases: ['person/titleonly'], expect: { property: ['P1 contract'], fixture: ['leak:owner'] },
    from: "/\\s/.test(title) ? title : ''", to: "''" },
  { name: 'scrub-shortest-first', tests: ['fixture', 'property'], cases: ['person/shared'], expect: { property: ['P1 contract'], fixture: ['leak:guardianA'] },
    from: '.sort((a, b) => b.length - a.length)', to: '.sort((a, b) => a.length - b.length)' },
  { name: 'link-id-seg-unmasked', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "if (ID_SEG.test(p) || PERSON.test(p)) return '<item> -> ' + maskPath(p);", to: "if (PERSON.test(p)) return '<item> -> ' + maskPath(p);" },
  { name: 'link-person-regex-unmasked', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "if (ID_SEG.test(p) || PERSON.test(p)) return '<item> -> ' + maskPath(p);", to: "if (ID_SEG.test(p)) return '<item> -> ' + maskPath(p);" },
  { name: 'maskpath-id-unmasked', tests: ['fixture', 'property'], cases: ['page/plan', 'list/payments'], expect: { property: ['P5 path', 'P1 contract'], fixture: ['leak:plan', 'leak:pay'] },
    from: "p.replace(/\\/([A-Za-z]*[_-])?[0-9a-f]{10,}.*/, '/<id>')", to: "p.replace(/\\/([A-Za-z]*[_-])?[0-9a-f]{999,}.*/, '/<id>')" },
  { name: 'link-query-values-recorded', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "(u.search ? ' [q:' + [...u.searchParams.keys()].join(',') + ']' : '')", to: 'u.search' },
  { name: 'contact-links-unmasked', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "if (isContact(a.getAttribute('href') || '')) return '<item> -> <contact>';", to: '' },
  { name: 'sidebar-contact-unmasked', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P6 sidebar'], fixture: ['leak:staff'] },
    from: "out.push(isContact(href) ? 'LINK  <item>  ->  <contact>'", to: "out.push(false ? 'LINK  <item>  ->  <contact>'" },
  { name: 'th-text-unsafe', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "th: uniq(q('th,[role=columnheader]').map(e => safe(e.innerText)))", to: "th: uniq(q('th,[role=columnheader]').map(e => clean(e.innerText)))" },
  { name: 'tabs-text-unsafe', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "tabs: uniq(q('[role=tab]').map(e => safe(e.innerText)))", to: "tabs: uniq(q('[role=tab]').map(e => clean(e.innerText)))" },
  { name: 'link-text-unsafe', tests: ['fixture', 'property'], cases: ['list/payments'], expect: { property: ['P1 contract'], fixture: ['leak:pay'] },
    from: "return safe(a.innerText).slice(0, 40) + ' -> ' + p;", to: "return clean(a.innerText).slice(0, 40) + ' -> ' + p;" },
  { name: 'sidebar-link-text-unsafe', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P6 sidebar'], fixture: ['leak:staff'] },
    from: ": 'LINK  ' + safe(el.innerText || el.getAttribute('aria-label')).slice(0, 50) + '  ->  ' + p);", to: ": 'LINK  ' + clean(el.innerText || el.getAttribute('aria-label')).slice(0, 50) + '  ->  ' + p);" },
  { name: 'sidebar-id-links-unmasked', tests: ['fixture', 'property'], cases: ['table/class-types'], expect: { property: ['P6 sidebar'], fixture: ['leak:nav'] },
    from: ": (ID_SEG.test(p) || PERSON.test(p)) ? 'LINK  <item>  ->  ' + maskPath(p)", to: ": false ? 'LINK  <item>  ->  ' + maskPath(p)" },
];

function apply(source, mutation) {
  const parts = source.split(mutation.from);
  if (parts.length !== 2) return null;                                       // stale: the text it breaks is gone or no longer unique
  return parts.join(mutation.to);
}

module.exports = { MUTATIONS, apply };
