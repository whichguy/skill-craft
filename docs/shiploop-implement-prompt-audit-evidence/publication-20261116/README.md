# R19 and R16 publication — 2026-11-16

R19 and R16 ship in **skill-craft 3.0.1 / ShipLoop 2.0.0**, release
[`b23e0166`](https://github.com/whichguy/skill-craft/commit/b23e0166b8c4dd70bffc08822e246d3cc122cc0f). R19 places backing loop state in the existing
run-owned directory. R16 reports actual release state and qualifies each observation for its own claim, with the full
rule in the shared guide. R15 remains next; R17 is independent. The [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md)
retains the generic before-and-after prompts and acceptance checks.

## What the evidence establishes

| Boundary | Observed result | Limit |
|---|---|---|
| Live checkout round | csv-report, source `d5142e5f`, 5/5 independent case checks | One local package and fresh Sol 6.1 medium context, before the later Python prerequisite change |
| [Candidate full CI](https://github.com/whichguy/skill-craft/actions/runs/43954284626) | 12 jobs; 207 suite executions | Exact release source, including latest-main changes |
| [Published-main full CI](https://github.com/whichguy/skill-craft/actions/runs/43963126308) | 12 jobs; 207 suite executions | Exact pushed release and actual outgoing boundary |
| Fresh remote package and source build | 423 files, 529 entries and four catalogs agree completely | Package integrity; not installed-host or deployed behavior |
| Disposable native Claude install | Published bytes, eight entry modes, installed floor/card, clean CLI/workspace startup and five quiet no-Python hooks | No model call or personal-profile refresh; optional old-interpreter result remains separate |

The published source is `b23e0166b8c4dd70bffc08822e246d3cc122cc0f`; its tree is `3b6c0b79a0c85c9585aff042b3932f10af500cf1`. The release tool generated the package at
`b23e0166b8c4dd70bffc08822e246d3cc122cc0f`; no packaged source change follows that generation. The metadata fixture and timeout-evidence repairs precede it.
Both full runs execute 207 distinct suites
with 0 repeated Python-floor suites. The five hermetic groups and four browser fixtures
retain their receipts. Conditional testcase skips remain explicit; no required suite was omitted. The manual candidate
run has no push range, so its release-boundary job is explicitly not applicable. The actual outgoing range passes the
local check and the main-push check. [Verification](verification.json) records actual counts and identities.

The native install requires Python 3.15 or newer. Its optional real Python 3.7.3 container probe also passes:
the CLI refuses with exit 2 and hooks stay quiet with exit 0. That qualifies refusal of an unsupported interpreter.
The native cache's sole extra `.in_use` marker is recorded separately from the complete 529-entry package payload.

The release carries the owner-approved Backchain retirement and Python 3.15 prerequisite, first published in
3.0.0/ShipLoop 2.0.0. A forward patch adds the Test Harness repair after that main run failed. Versions come from
the release tool and pending notes; no unpublished 2.42.2/ShipLoop 1.37.2 label is reused.
That older generated commit `850aa2d5b93df54711ccbc7f432065b2d8e793e8` stays in history. Only `release.py` writes
release output. [Source continuity](source-continuity.json) preserves the six historical qualification-tree identities.

## Preflight and the live round

The first preflight refused already-published release `084db6aa3336b41cf38dae33d62c93506bcb98d3` because its selected
journal came from older merged history. Replacing the release range with `journal..HEAD` had brought that release back
into the candidate set. The maintainer-tool fix keeps both ancestor exclusions:

```python
# Before: the journal range replaced the release range.
after = f"{journal}..HEAD" if journal else span

# After: the journal exclusion narrows the existing release range.
after = [span, f"^{journal}"] if journal else [span]
```

Two real-entrypoint graph regressions first fail by assertion on unchanged code, then pass; all 24 preflight methods
pass. A genuinely new uncovered change still refuses. Fresh independent Astra/high read-only review approved this
maintainer fix. The requested launch controls are retained; provider-served identities were not separately attested.
The current [e2e_round_missing implementation](https://github.com/whichguy/skill-craft/blob/b23e0166b8c4dd70bffc08822e246d3cc122cc0f/scripts/release.py#L197)
retains both ancestor exclusions.

After main advanced, preflight correctly found the older unpublished generated release `850aa2d5` outside the newer
release's ancestry. All 75 focused methods and 39 zero-model mock checks passed, but those checks were not presented
as a live delivery. The repository's existing full local CSV-tool case then ran from its literal prompt in a disposable
Codex profile. Its receipt pins the actual checkout, package bytes, fresh model/effort flags, returned product and five
independent case checks. The journal records that actual round and its limits. It does not claim to test a remote org,
an installed user host, the later Python change or every R16 observer scenario. Earlier explicit per-commit reasons
and the owner's separate retirement waiver remain literal. No historical trailer or frozen result was rewritten.

The live audit's `host-owner.md` heuristic flag was checked against the source contract and resulting note: it is
the required append-only parent coordination record beside an Improve packet, distinct from engine state and success
receipts. Add/append events corroborate it; the original patch body was not retained. No engine or audit repair follows.

## Failed attempts and fixture corrections

The original [full CI run](https://github.com/whichguy/skill-craft/actions/runs/43895804906) remains **FAIL** at `850aa2d5`:
all 285 executions completed, 280 passed and five failed across three suite IDs. Its thirteen jobs, ten artifacts and
59 conditional testcase skips remain recorded. A later corrected run passed 285/285 at `9b05a94f`, before Backchain's
retirement and the Python change; that success is not relabelled as acceptance of the final release.

Two fixtures silently deleted an existing pending outcome. They now copy the actual prefilled rows, carry or defer the
unobserved outcome, and assert that accepted state retains its key with `settled: []`. The missing-list refusal and
independent knowledge-file refusal remain checked. Their original methods and assertions remain.

The generated-release local bank passes its four release/package/boundary checks, while the broad outgoing whitespace
check remains **FAIL**: 192 findings in 22 frozen evidence files. All 22 match their previously accepted bytes.
A separate exact check passes the other 999 outgoing paths at the generated release. At `3d277e4a`, the test-only repair
passes all 1,000 outgoing paths outside those same 22 files. The later Test Harness patch and final generated release
pass their full outgoing-range whitespace check, with no exclusions. No source file is excluded and no evidence is rewritten.
CI raw-log capture also preserves its original escape refusal and an incorrect flag-position attempt before the scoped
file-only capture succeeds. Those are collection attempts, not rerun tests or erased CI failures.

The progress fixture required immediate confirmation even when startup could leave its one child alive and pending.
A controlled real-child barrier reproduces that assertion failure. The correction requires fresh owned publication
immediately after True; False requires the same live child, then the fixture's existing wait. The delayed same-PID case
passes; abort and premature-success controls remain underlying assertion failures. All 38 methods pass locally on the
two original interpreter entries. The original CI child's timing/error cause remains **UNKNOWN**. Proper Python 3.9
callback qualification is historical evidence from before the minimum changed, not current support for Python 3.9.
No runtime startup-budget or loop change was made for these three fixture repairs.

The next [full candidate run](https://github.com/whichguy/skill-craft/actions/runs/43933567851) remains **FAIL** at
`7eb5998f`: all 207 suites completed, 206 passed, and one of Closed Loop's 165 methods asserted its first-release
version `0.1.0` after the release tool generated `0.1.1`. Only that existing metadata method changes: require a
nonempty current version and match the initial note to it while that note exists. The shared metadata suite still
owns strict SemVer validation. All 165 method names and the other 164 method ASTs are unchanged. The focused check
first fails by assertion, then passes; seven controls cover current and later legal versions, missing or empty
versions, and matching or mismatched initial notes. The complete 165-method suite and the common check of all
25 skill cards pass locally; the current candidate and main CI rows above qualify the repaired source. The generated
3.0.0 package remained byte-for-byte unchanged by that test-only commit. This is fixture maintenance, not a Closed Loop or ShipLoop behavior gain.
The current [metadata method](https://github.com/whichguy/skill-craft/blob/b23e0166b8c4dd70bffc08822e246d3cc122cc0f/test/closed-loop.test.py#L2265)
requires the card's current version instead of permanently pinning its first release.
The repair worker's first brief omitted the evidence path and stopped with zero edits and zero tests; the same
explicit Sol 6.1 medium session resumed with the path supplied. Both attempts remain recorded.

The first published-main [run](https://github.com/whichguy/skill-craft/actions/runs/43944081831) remains **FAIL** at
`3d277e4a`: 207 suites completed, 206 passed, and the Test Harness self-test could not parse its timeout report.
The native 3.0.0 install and package readback remain valid at that source; they do not override the failed main CI.

Two source gaps were then reproduced separately with the actual supervisor, alarm and process groups. The baseline
fails three assertions across cleanup and empty/prefix-write interruptions. Moving the writer alone fixes cleanup
ordering but leaves both interrupted-write controls failing. The repair constructs complete private bytes and publishes
by an atomic link that refuses existing files or symlinks, then records the timeout before deadline-consuming cleanup.
The deadline, alarm, JSON fields and exit status stay unchanged. Six green scenarios also cover an alarm after publication
and raced destination collisions. The original bundled self-test passes 279 recorded markers, including 34 unconditional
markers; that is not 279 independent tests.

Fresh independent review found a defect in the new regression fixture: failure cleanup drained output pipes before
killing the workers holding them. A controlled failed-supervision variant reproduced the hang; the fixture now kills
its owned processes before draining, preserving the original failure. The initial **CHANGES_REQUIRED** review and
11-method local PASS retain their original snapshot. The corrected fixture is requalified separately, and final full CI
runs all 11 wrapper methods. This is a Test Harness source repair and its regression maintenance, separate from R19/R16.
The exact historical CI interruption remains unknown; no test was retried until it happened to pass.

Current repair code and controls: [run-harness-hard-supervisor.py:44 — write_hard_timeout_evidence](../../../skills/test-harness/scripts/run-harness-hard-supervisor.py#L44); [run-harness-hard-supervisor.py:154 — main](../../../skills/test-harness/scripts/run-harness-hard-supervisor.py#L154); [test-harness.test.py:82 — TimeoutEvidence](../../../test/test-harness.test.py#L82). The three anchors are included in the current source map. A hard
alarm may leave a private staging name; no incomplete final report is published by this writer. Filesystem latency can
reduce cleanup grace, and neither blocked-filesystem completion nor power-loss durability is guaranteed.

The first source validation with an author-created Ruff cache remains **INCOMPLETE**, with zero checks run; its four
task-owned cache files were retained externally. A collector briefly wrote an inventory into the canonical workspace
and moved it out; final source identities are clean. A parent metadata error, one fixture-probe setup error and the
multiline-test-description collector failure also remain separate. The successful follow-ups do not erase them.
Later parent evidence checks also corrected a multiline-result parser and an inventory-locator comparison without
rerunning tests; the first main-run lookup used the wrong workflow-name case, then selected the same retained status
response against the actual `ci` declaration. These collection errors did not change source or CI outcomes.
The final main collector also retains a missing-summary environment error and a metadata filename-filter error;
corrected receipt validation does not rerun tests.
[Retained attempts](verification.json) and the [external manifest](external-evidence.json) locate the raw evidence.

## Re-anchoring and remaining scope

The [source map](source-map.json) verifies 244 spans across 52 files, covering all 22 recommendations,
eight considerations, fourteen Code craft rules and T1–T52. The [comparison](anchor-changes.json) accounts for every
old anchor. The shared graph-check instruction survives with a changed format pointer. Additional anchors locate the
retained dependency audit, graph format, checker and retired-option refusal. Latest-main source changes receive renewed interpretation, rather than a line-number
substitution alone. The current map does not overwrite the six earlier qualification records.

Earlier operator mapping drafts were rejected for omitted guide/acceptance content, a wrong AST binding, duplicate
link shifts and a composite excerpt that lost one function. Their original artifacts remain external. The accepted
map checks actual symbol/section ownership, every claimed function and link-to-span membership as well as hashes.

Full CI, package publication and the disposable install do not establish universal model uptake, personal host refresh,
authenticated authority or deployed acceptance. This unit implements no R15/R17 proposal, new runtime format, schema, grant, loop limit, persistent
integration or org deployment. Render inspection status is recorded separately in the documentation audit.

## Document checks

The current audit verifies all 244 source excerpts and hashes, 230 local links including 183 mapped source links, all recommendation/consideration/rule IDs and the T1–T52 crosswalk. The six earlier qualification trees are unchanged. Representative rendered samples cover the plan opening, the R19 and R16 before/after examples, and the publication evidence table at desktop and narrow widths. These samples are readable without clipped prompt text; the entire long plan was not visually inspected. The first anchor-scroll screenshots were blank, so exact Markdown excerpts were rendered separately. The earlier document-check prefix mismatch remains an operator attempt, with no change to the frozen review. [Document validation](document-validation.json) and [render check](render-check.json) retain the checked scope and external image hashes.
