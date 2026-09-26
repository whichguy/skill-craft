# Match the house style

New code should read like the code around it. This guide covers **how the
repository writes code**: its tools, layout habits, names, idioms, error
handling and test shape. What the system *does* belongs to
[current-system recovery](current-system-baseline.md); why an existing choice
was made belongs to the
[Git-history investigation](project-knowledge.md#investigate-git-history-for-planning).
Where a new name or file goes is covered by
[namespaces and placement](coding-practices.md#namespaces-and-placement).

Two findings shape the method. A generated repository overview mostly repeats
what an agent can read for itself and does not make it more successful; short,
non-obvious, actionable rules do. And adherence to up-front rules fades over a
long session, so the rules that matter to one work item travel with that item
and are reread when it is built, not only at discovery.

## Extract the house style

Run this at discovery for any repository with existing code. A genuinely new
repository records that no house style exists yet; the first work items then
set it deliberately, as design decisions with their rationale.

1. **Reuse a sufficient record.** Look for an existing style record: a
   CONTRIBUTING or AGENTS section, a style guide, or the house-style section of
   the repository knowledge index. Reuse a category when the commit it was
   checked at is recorded and nothing in *When to refresh* below has happened
   since. Refresh
   only the affected categories of a stale record; a missing record is
   extracted as described here.
2. **Start from tool configuration.** Read the formatter, linter,
   type-checker and `.editorconfig` settings, CI workflows, manifests and
   lockfiles. These are the house rules a machine already enforces, and the
   versions the code is written against. Record the exact commands the
   repository runs for build, lint and test, confirmed by running them in the
   initial baseline rather than copied from prose.
3. **Sample load-bearing code, not the whole tree.** Choose the hand-written
   files that are most often changed and most often referenced, plus the
   recent history of the area the request touches. For example,
   `git log --format= --name-only -n 300 -- <source and test paths> | sort | uniq -c | sort -rn | head -20`
   lists recently busy files, and a few full recent diffs show which style is
   current. Leave out generated, vendored and release-output files, lockfiles
   and changelogs: they change often but show no one's coding habits. Add the
   files nearest the requested change.
4. **Cover each category that the change can touch:**
   - runtime and language versions, and the library already used for each job
     (HTTP, parsing, CLI, dates, subprocesses, test doubles);
   - layering and allowed dependency direction;
   - naming of files, types, functions, constants, flags and test cases;
   - recurring idioms: construction, configuration access, iteration, early
     returns, data classes versus dictionaries;
   - error handling and failure reporting: raised types, messages, exit codes,
     retries, what is caught and where;
   - logging and diagnostics;
   - comment and docstring density;
   - tests: location, file and case naming, fixtures, doubles, assertion
     style, how slow or external tests are marked;
   - commit and pull-request format, taken from the full messages of recent
     commits;
   - domain terms the code uses for its concepts;
   - security and performance habits (input validation, secret handling,
     caching, batching), which context files usually leave out.
5. **Give every rule its evidence.** Each rule states the convention, cites two
   or three `path:line` examples, and gives its frequency (for example "11 of
   13 handlers"). Mark it **observed** (seen in code), **inferred** (a pattern
   from few examples) or **unknown**, and note when a tool already enforces
   it. Never fill a gap with a generic best practice; an open question goes on
   a short questions list instead.
6. **Settle disagreements by recency.** Where old and new code differ, name
   both, cite each, and say which direction the repository is moving. Newer
   code in the same area normally wins unless a maintained document says
   otherwise. Record the old form as legacy, not as a second convention.
7. **Keep only what helps.** Drop rules a formatter or linter already
   enforces, conventions that are generic to the language, and facts a reader
   finds by opening the obvious file. The result is short, one to two pages,
   so that later stages reread it rather than skim it.

### Where it lives

Keep the record in the repository, where later runs and people find it.
Prefer an existing style section and extend it in place. Otherwise add a
**House style** section to the repository knowledge index (`SHIPLOOP.md`), or
a linked `docs/house-style.md` when the section would crowd the index. Record
the commit each category was last checked at (one commit when all were checked
together). The record describes the repository;
run-specific plans and decisions stay in the run's notes.

### When to refresh

Refresh the affected categories when the formatter, linter, type-checker, CI
or manifest configuration has changed since a category's recorded commit; when
the area the request touches has changed materially since then; or when a work
item finds a rule contradicted by current code. Old records are evidence, not
instructions: recheck a rule before relying on it.

## Write the match contract

At step planning, before any product edit, write a compact **match contract**
into the item's accepted step plan: the plan note its result registers in
`evidence_refs`, named in its `summary`. Every later stage that builds or
checks the item (test authoring, implementation, static checks, verification,
documentation) lists that step-plan result under **Results this stage builds on**, so a fresh
context finds the contract without this conversation. Work-item `context` is
written only at plan and carry-forward; a plan that already knows an item's
exemplars may name them there, and step planning confirms or replaces them.

1. **Name the artifacts.** List the kinds of file the item adds or changes:
   for example a command, handler, module, migration, test, fixture or
   document.
2. **Find the nearest exemplars.** For each kind, find the two or three
   existing files that are closest to the change: the same directory or layer
   first, then the same pattern elsewhere, preferring recently changed files.
   Search sibling names and call sites rather than guessing. Give each
   exemplar's path and the reason it was chosen.
3. **State what to match,** citing exemplar lines: file placement and name;
   the names of new types, functions and tests, mirroring the exemplars'
   vocabulary; imports and the libraries used for each job; the error-handling
   and logging idiom; the test file's name, fixtures and assertion style; and
   the documentation or comment shape.
4. **Resolve conflicts explicitly.** Where an exemplar disagrees with the
   house-style record, say which one this item follows and why; a newer
   exemplar in the same area normally wins.
5. **Name the gaps.** When no exemplar exists, say so and follow the
   house-style record. A pattern the repository does not yet have is a design
   decision with its rationale, not a silent invention. A new dependency needs
   the evidenced reason required by [libraries](coding-practices.md#libraries).

Keep the contract to what this item needs. It is a checklist for the builder
and the verifier, not a copy of the house-style record.

## Match while building

At test authoring and implementation, reopen the match contract in the item's
step-plan result and its exemplars before editing; do not work from a
remembered summary.

- Write new code and tests in the exemplars' shape and vocabulary.
- After a first draft, search again using the draft's own names and calls.
  The draft finds existing helpers, constants and fixtures that the plan's
  wording did not; reuse them instead of adding near-duplicates.
- Leave surrounding code in its existing style. Restyling unrelated code needs
  its own reason and its own change.
- When the item must depart from the contract, record the reason in the
  item's result, so verification can judge it.

## Check the diff against the contract

At verification, compare the item's diff with its match contract and
exemplars: placement, names, imports and libraries, error handling and
logging, test shape, and comment density. Run the repository's own formatter
and linter commands rather than a substitute. Report each difference as fixed
or as a recorded, justified departure. A clean linter run does not show that
names, layering or idioms match; read the diff for those.

## Retain the house style

At carry-forward, update the repository's house-style record when this work
found a convention the record lacked, showed a recorded rule to be wrong or
legacy, or deliberately introduced a new pattern that later work should
follow. Add the citations and move the recorded commit forward only for the
categories actually rechecked. Leave run-specific detail in the run's notes.
