# Evidence: the pushpress skill leaves skill-craft (2026-11-22)

The measurements behind the removal commit, small enough to read in a minute. Each section names how to re-derive it. Nothing here is
tenant data, and the private repository is named by hash only, as the journal's privacy rule asks (`docs/pushpress-journal.md`).

Base: `2ddacc9ed7317a7576e2cfefd477bf63c3fa4862` (release: skill-craft 4.4.1, shiploop 2.6.1), `origin/main` after a fresh fetch.

## 1. This repository's copy against the private repository's copy

Both trees were exported with `git archive` at each repository's `origin/main` (this one at `007c45d50e16acd856c31646174cc1ee76f1e29c`,
whose pushpress files are identical to the base's by `git diff`; the private one at `94d494f23f57c12361c79e5516ad624a360ac4d4`), then
compared with `diff -rq` and, per file, `diff -U0`.

| file under the skill folder | lines only in this copy | lines only in the private copy |
|---|---|---|
| `SKILL.md` | 9 | 20 |
| `references/app-map.md` | 1 | 3 |
| `references/drift-and-open-questions.md` | 3 | 11 |
| `references/people-and-plans.md` | 7 | 66 |
| `references/settings-and-admin.md` | 3 | 5 |
| the five other references and `scripts/pp-extract.js` | identical | identical |

All 23 lines that exist only in this copy were read next to what replaced them in the private copy. None is information the private
copy lacks; each is a statement the private copy replaced or corrected: the version line (`0.1.1`, `0.1.2`); the sentences that say no
write flow was exercised and that nothing was saved, against the corrected ones that say the document flows were exercised with the
owner's yes; the Waivers and Alerts rows, against rows that carry rule 7 (a new document text needs its own yes before it is published)
and say that *Document Ready to Sign* is addressed to the member; the WRITE-DATA, OUTBOUND and DESTRUCTIVE rows, against the same rows
extended, with two new classes (SIGNING, UNDOCUMENTED); and a route row marked "not captured", against three captured document routes.

Tests, `test/` against the private plugin's `test/`: 3 lines only in this copy (two assertion constants in `pushpress.test.py`, one
`require` in `privacy-fixture.cjs`), 113 lines only in the private copy, and one file only here,
`test/fixtures/pushpress-extractor/browser-tools.cjs` (848 lines, added by `2cd119d1238896e6ea2394018450328ff50f5b9c` on 2026-11-19).
The private copy's `privacy-fixture.cjs` requires a helper path that exists nowhere in its repository: loading the file gives
`MODULE_NOT_FOUND` (checked in an export, run from outside it). `pushpress.test.py` does not load that fixture.

## 2. The suite-inventory digest

`test/test-groups.test.py` freezes a SHA-256 of every suite's catalog record (id, family, path, argv, groups, timeout, hermetic). It was
computed two ways with a short script that loads each catalog file and hashes the records the way the test does:

| catalog | suites (core) | digest |
|---|---|---|
| the base, all rows | 191 (61) | `d88a4f3af888db8ef6e0c4fec2889c3059d254f1878d0afd23cb23e0f8a36c1b`, the value the test froze before this change, so the script reproduces the test's own computation |
| the base without the `pushpress` row | 190 (60) | `54ec6ac8c0ac865e59e16362118ffe89d8dcc8ad1b3702835625db1b03fcf248` |
| the edited catalog | 190 (60) | `54ec6ac8c0ac865e59e16362118ffe89d8dcc8ad1b3702835625db1b03fcf248` |

The last two are equal: the digest changed by the removal of that one row and by nothing else. Ids at the base but not now:
`pushpress`. Ids now but not at the base: none.

## 3. Checks on the removal tree, before the commit

| step | result |
|---|---|
| `test/suite_durations.json` parses | valid JSON, 184 entries |
| the two edited Python files parse (`ast.parse`) | both parsed (a first attempt with `py_compile` that named `/dev/null` as its output file failed on that argument, not on the files, and was redone this way) |
| `python3 test/test-groups.test.py` | Ran 78 tests in 46.318s, OK |
| `node test/skill-frontmatter.test.js` | PASS 24 skills |
| `python3 test/ci-policy.test.py` | Ran 18 tests in 6.610s, OK |
| `python3 test/ci-summary.test.py` | Ran 11 tests in 0.237s, OK |

These are the four suites that the Sport80 removal ran (`4ef10ecc7dd65341c77020905df6a48393cd2181`), because a removal changes what
they pin. The repository's quick tiers run on the release commit as checks of the guarded push, and the full tier runs on that commit in CI.

## 4. Not measured

- The quick and full tiers on the release commit: they follow the cut.
- Whether anything outside this repository still names `skill-craft:pushpress`.
