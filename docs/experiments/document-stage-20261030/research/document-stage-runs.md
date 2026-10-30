# What ShipLoop's `document` stage actually produced

Scope: read-only audit of `~/shiploop-e2e-runs/` (16 run directories; 10 reached a `document` action),
`~/e2e-runs/20261029/pilot-terra-*` (the 2026-10-29 per-step pilot, 2 arms with their own per-step
`document` actions and Improve reviews), `docs/experiments/shiploop-per-step-pilot-20261029/`, and
LEARNINGS.md / docs/*journal*.md for prior findings. All run/host/model facts below are read from
`invocation.json`, `metrics.json`, `state.md`, `events.jsonl` and each run's worktree `git log`, not
inferred.

## Finding 0 — host/model coverage is narrow

Every run under `~/shiploop-e2e-runs/` that reaches `document` is `host: claude`, `model:
claude-sonnet-5-5` (`invocation.json` in each of the 10 rows below). The six runs that did **not**
reach `document` are the three `*-interrupt-*` fixtures (stopped at `implement`, by design — they test
interrupt/resume, not documentation) and `chain-seeded-codex-21de3d` (Codex host, stopped at
`test-strategy`). The only non-Claude, non-Sonnet-5.5 evidence of a `document` action is the 2026-10-29
per-step pilot (Codex `gpt-6.1-terra` xhigh), added as rows 11-12 below. There is no Grok or other-host
`document`-stage evidence in either corpus.

## Table — one row per run

Legend: "chore-commit" = the README edit landed inside a non-document-labelled commit (interrupt-safety
net or a single squashed feature commit), so the diff below is extracted by path (`-- README.md`), not
by an isolated commit, and cannot be told apart from other stages' edits by commit boundary alone.

| # | Run | Host/model | Case | Tool calls / seconds (document stage) | Files changed by kind | Knowledge field | Quality notes | Improve review after document |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `b1-unit-converter-a1950c` | claude / sonnet-5.5 | unit-converter | 1 call, 7.0 s (metrics.json; events.jsonl window) | README.md only (+13 lines), commit `032e2c1` "docs: document the unit converter command and tests". No docstring/code/knowledge-home touch. | none (no `knowledge` key in the result) | Table of units+factors, exact CLI example `python3 convert.py 10 km mi` → `6.2137`, exit-2 error text `convert.py: error: ...` matches code (`convert.py:14,52,109,115`). Accurate, no bloat. | No `improve/<action>/receipt.md` for this action — none exists |
| 2 | `b2-unit-converter-1df863` | claude / sonnet-5.5 | unit-converter | 2 calls, 13.4 s | README.md only (+22), commit `69f5d50` "docs: document the unit converter modules and CLI" | none | Same table style; result summary explicitly says the `6.2137` example "was observed from the real command" — verified against actual output. | None |
| 3 | `b2-word-report-b1f521` | claude / sonnet-5.5 | word-report | 2 calls, 10.6 s | README.md only (+19), commit `445c880` "docs: document the word-frequency report" | none | Module table (`tokens.py`, `stopwords.py`, `counts.py`, `filters.py`, `report.py`), usage + ordering rule + exit-2 case. Accurate, concise. | None |
| 4 | `b3-temperature-5c5493` | claude / sonnet-5.5 | temperature-report | 1 call, 6.2 s | README.md only, commit `8b9a422` "Document the temperature tools in README" | none | Three modules, example, exit-code table 0/1/2. | None |
| 5 | `c1-interrupt-temperature-83752d` | claude / sonnet-5.5 | temperature-report (post-interrupt resume) | 3 calls, 19.8 s | README.md (+32) **plus** `test/test_system.py` (+63) bundled into one chore-commit (`5553f44` "commit files written after the last work item, before the return") — cannot cleanly separate document's README delta from the interrupt safety-net's test commit by commit boundary; isolated by path diff instead. | none | README has a full exit-code table (0/1/2 with exact stderr text), argument-constraint line (`bool`/non-number → `TypeError`). Each claim in the result's summary was checked against a real run (`printf '32\n212\n' \| python3 measure.py`, `to_celsius(True)` → TypeError). In-code docstrings (Args/Returns/Raises, module purpose line) exist in `convert.py`/`stats.py`/`measure.py` but were added by the **implement** commits (`78e4082`, `0986e95`, `2601ebf`), not by document — confirmed via `git log -- measure.py`. | None |
| 6 | `c2-interrupt-temperature-f4c40f` | claude / sonnet-5.5 | temperature-report (post-interrupt resume) | 5 calls, 21.0 s | README.md (+29) bundled with `docs/shiploop/environment.md` (+14), a release-plan doc (+47) and two test files, all in one chore-commit `b5fa2c8` — same non-attributable bundling as row 5. | none | README table distinguishes all-numbers/some-bad/none-valid cases with exact stderr text and exit codes; precise ("N is the 1-based physical line number... blank lines count"). No stale statements found. | None |
| 7 | `chain-full-claude-5b2cf8` | claude / sonnet-5.5 | temperature package (chained) | 1 call, 7.5 s | README.md only (new file, +17), commit `bd34ae2` "Document the temperature package" | none | Exit codes and error text (`error: no valid numbers`) verified against `measure.py:45` — exact match. | None |
| 8 | `chain-seeded-claude-e57b4d` | claude / sonnet-5.5 | temperature package (seeded) | 1 call, 7.5 s | README.md only (+17), commit `ebe0a76` "docs: document convert, stats and measure in README" | none | Exit-code table + verified example output in the commit message/code. | None |
| 9 | `p1-temperature-plain-080452` | claude / sonnet-5.5 | temperature-plain | 1 call, 6.0 s | README.md (+15) **squashed into the single `feat:` commit `1a9703f`** that also adds all product/test files — this "plain" commit strategy gives document **no commit of its own at all**; cannot attribute the README delta to document vs. implement by commit boundary. | none | Content equivalent to the other temperature cases; no stale text found. | None |
| 10 | `p1v-temperature-plain-1df460` | claude / sonnet-5.5 | temperature-plain (verified variant) | 1 call, 7.6 s | README.md only (rewritten, +19), commit `e31681a` "docs: document temperature package; ignore bytecode" | none | README says exit 1 is "no numbers (error on stderr, nothing on stdout)" without quoting the exact stderr text; the real message is `error: no numbers on input` (`measure.py:50`) — less precise than rows 1-9, though not wrong. | None |
| 11 | `pilot-terra-ask-agent-32f436` S1 (parser) | **codex / gpt-6.1-terra, xhigh** | stand-in-parser (per-step pilot, ask-agent route) | document stage itself 1 worker thread; its Improve review cost is counted in "document 6.8 min (×2 steps)" at the item level (`run-review-facts.md`) | `docs/shiploop/records.md` (new, 15 lines: purpose, contract, args/errors, verified example+output, test command) + `docs/shiploop/spec.md`, `architecture.md`, `environment.md` entries + (via the review) `src/records.js` error-message rewording and `test/records.test.js` (+37/+23 new test lines) — all later squashed into the step's single commit `8b503a1`, so document's own share of that commit cannot be separated from implement's by commit boundary; only the document **result** and its **Improve review** let you see what it itself did (see below). README explicitly **not** touched — deferred as an open "carry-forward" assumption. | **present**: `{"spec": "...R-1 observation...", "architecture": "No change...", "environment": "Recorded the passing parser syntax check..."}` | `records.md` has a purpose line, full argument/error contract, and a verified example (`node -e "..."` → exact JSON). No docstring restatement, no tombstones. | **Yes** — `.shiploop-improve/document-1cf0275a/reviews/review-1.md`: classification `non-trivial`, found generic error messages concealed failure kind/location vs. R-1's requirement; **fixed** `src/records.js` to distinguish missing-`=`/invalid-key/duplicate-key with line+field, added TC-2(a)/TC-3(a). review-2.md: `trivial`/`satisfied`, no further issue. |
| 12 | `pilot-terra-ask-agent-32f436` S2 (select) | codex / gpt-6.1-terra, xhigh | stand-in-parser (per-step pilot, ask-agent route) | same per-item 6.8 min bucket | `test/records.test.js` (+8: new `TC-5 (b)`) via the Improve review; no product-code change; squashed into step commit `d70c709`/`9207e5b`. README deferred (same open assumption). | **present**: `{"architecture": "AD-1 ... already cover the selector...", "environment": "Updated the stale S1 availability note...", "spec": "...no additional line was needed."}` | Documented identity/order/strict-equality guarantees match code; example command verified. | **Yes** — `document-6762eb32/review-1.md`: `non-trivial`, found the README/`records.md` claim "a new array containing the same record objects" (reference identity) was asserted but **not tested** (only deep-equality `TC-5` existed) — a documentation claim ahead of test coverage; **fixed** by adding `TC-5 (b)` asserting array/record identity, no product-code change. review-2.md: `trivial`/`satisfied`. |

Pilot **inline** route, same case, for contrast: two `document-*` Improve reviews
(`.shiploop-improve/document-eedc0383`, `document-05fa1983` under
`~/e2e-runs/20261029/pilot-terra-inline-32f436/`) were both `trivial`/`satisfied` on the first pass —
"Documentation correctly describes... no material defect was found... Changed: Nothing" — i.e. the
same case's inline document stage wrote docs that needed no review-driven fix, where the ask-agent
(fresh-worker) route's document stage needed two.

## Patterns across runs

1. **The document stage's one deliverable, almost everywhere, is README.md.** In every one of the 10
   `~/shiploop-e2e-runs/` runs, the result's `evidence_refs` array contains exactly one path and it is
   always `.../worktree/README.md` (checked directly in each `results/nav-*.md` file, e.g.
   `~/shiploop-e2e-runs/b1-unit-converter-a1950c/.shiploop-runs/seed/run/results/nav-5c01f8f398e3467a82eec27805568007.md`).
   No run in that corpus touches a docstring, a module header comment, argument-validation code, or
   `docs/shiploop/{spec,architecture,environment}.md` from the document action itself — those files are
   written by other stages (`docs(shiploop): record ... knowledge after <stage>` commits from
   carry-forward/release-plan/release-verify; `environment.md`/`architecture.md` from
   discovery/test-strategy). Where product code shows good contract docstrings (e.g.
   `~/shiploop-e2e-runs/c1-interrupt-temperature-83752d/.shiploop-runs/seed/worktree/measure.py`), `git
   log --follow` on that file shows the docstring was added by the **implement** commit
   (`2601ebf measure: implement Fahrenheit-to-Celsius summary CLI`), not by document.

2. **No `knowledge` field in the older runs; present in the newer per-step pilot.** All 10 older
   results have no `knowledge` key at all. The 2026-10-29 per-step pilot's document results do carry a
   `knowledge` object naming spec/architecture/environment per action (rows 11-12). This matches a
   protocol-version difference (`navigator_protocol_version: 4` in the old runs) and a documented
   architecture change: `docs/experiments/shiploop-per-step-pilot-20261029/README.md` describes a "7-stage
   inner loop: each step built, tested, documented, reviewed and committed" (v6), where the older runs
   use a single document action per work item with no such stage-level knowledge bookkeeping.

3. **Document-stage output is frequently not its own commit, which blocks clean attribution.** 3 of
   10 older runs could not be isolated by commit boundary: the two `*-interrupt-*` resumes bundle the
   README edit into a generic `chore(shiploop): commit files written after the last work item, before
   the return` commit alongside test files and (in one case) `environment.md`
   (`~/shiploop-e2e-runs/c2-interrupt-temperature-f4c40f/.shiploop-runs/seed/worktree`, commit `b5fa2c8`);
   `p1-temperature-plain-080452`'s "plain" commit strategy squashes implement+test+document into one
   `feat:` commit (`1a9703f`) with no separate document commit at all. The per-step pilot (rows 11-12)
   squashes implement+test+document+Improve-review into **one commit per step** by design ("the step's
   iteration commit, made once this review is accepted, commits the review's edits with the step's code,
   tests and docs" — `.shiploop-improve/document-6762eb32/reviews/review-1.md`), so for that corpus the
   only clean signal of what document itself did is the stage's own `results/nav-*.md` / `-final-result.md`
   file and its Improve review text, not the commit diff.

4. **README quality in the older runs is consistently good and self-checked, with one exception.**
   8 of 10 README diffs include an exact, code-verified example command and output (e.g. `printf '32\n212\n'
   \| python3 measure.py` → `{"count": 2, "mean_c": 50.0, "median_c": 50.0}`, verified against
   `measure.py:45` in `~/shiploop-e2e-runs/chain-full-claude-5b2cf8/.shiploop-runs/work-20261003-164113-33616d/worktree/measure.py`)
   and a precise exit-code table with the literal stderr text. No tombstone comments, no restated-code
   comments, no stale statements were found in any of the 10 READMEs checked against their code. The one
   weaker case is `p1v-temperature-plain-1df460` (commit `e31681a`): its exit-1 row says "error on
   stderr" without quoting the literal message, where the actual text (`measure.py:50`, `error: no
   numbers on input`) differs in wording from every sibling case's "no numbers"/"no valid numbers"
   phrasing — a minor precision gap, not a factual error.

5. **No Improve review is tied to the document action in the older (single-document-per-item)
   architecture; the newer per-step architecture does review it, and catches real gaps.** None of the
   10 older runs has an `improve/<action>/receipt.md` keyed to the document action id (checked for all
   10; `improve/` directories in those runs exist only for implement-step actions). In the 2026-10-29
   per-step pilot's **ask-agent** route, both of the two per-step document reviews found a material gap
   on the first pass and fixed it: S1's review found error messages did not distinguish failure
   kind/location as the spec promised, and rewrote `src/records.js` plus added two test cases
   (`.shiploop-improve/document-1cf0275a/reviews/review-1.md`); S2's review found a documented
   reference-identity guarantee ("a new array containing the same record objects") had only
   deep-equality test coverage, not identity coverage, and added `TC-5 (b)` to close the gap
   (`.shiploop-improve/document-6762eb32/reviews/review-1.md`). The same case's **inline** route document
   reviews were both trivial/no-change on the first pass
   (`~/e2e-runs/20261029/pilot-terra-inline-32f436/.shiploop-runs/seed/worktree/.shiploop-improve/document-eedc0383/reviews/review-1.md`,
   `.../document-05fa1983/reviews/review-1.md`). This matches
   `docs/shiploop-sdlc-gates-proposal-2026-10-30.md:99`: "Document-stage reviews | 5, all in the per-step
   pilot. Inline and old route: 3 reviews, one trivial pass each, no file changed. Ask-agent: 2 reviews,
   both changed files (50 and 8 lines)."

6. **README is explicitly out of scope in the newer per-step design, and both reviews flag it as an
   open carry-forward item.** Both pilot document-stage notes
   (`~/e2e-runs/20261029/pilot-terra-ask-agent-32f436/.shiploop-runs/seed/run/notes/nav-9d2b9c6214a740d89e8323421cf0275a.md`)
   record the explicit no-change reason: "README was reviewed and left unchanged because this loop
   explicitly limits edits to step-plan paths and `docs/shiploop/`... a link to the new reference should
   be added when README is in scope." Both per-step document results carry an `assumptions` entry
   (`id: A1`, `due_stage: carry-forward`) asking a later stage to link README to the new
   `docs/shiploop/records.md`. This is the opposite of the older architecture, where README was
   document's *only* output.

7. **Document-stage cost is small but not negligible, and much larger per-worker in the newer
   architecture.** In the 10 older runs, document took 1-5 tool calls and 6.0-21.0 seconds
   (`metrics.json` `stages[].stage=="document"`, cross-checked by counting `tool_use` events between the
   document packet delivery and the next stage's packet in `events.jsonl`). In the per-step pilot's
   ask-agent route (a separate worker thread per stage), the two document actions together cost 6.8
   minutes versus 1.3 minutes inline for the same two steps (`run-review-facts.md` in both pilot
   directories) — a roughly 5x cost increase from giving document stage its own fresh-context worker, in
   line with `docs/shiploop-sdlc-gates-proposal-2026-10-30.md`'s note that "fresh document reviews changed
   files 2 of 2, inline 0 of 3" (candidate 3, same proposal document) — the extra cost buys extra
   recall.

## LEARNINGS.md / journal hits

- `test/shiploop_e2e/LEARNINGS.md:1628` — "Held for a second run: ... plan-document location,
  **document-stage paths**, ..." — an open item from a prior review batch, unresolved as of that entry;
  consistent with finding 3 above (document's file scope/attribution was already flagged as unclear).
- `docs/shiploop-batch-1008a-journal-2026-10-08.md:336` — "...because the document stage is told to
  maintain `AGENTS.md`" — a one-line note that an earlier design iteration had document maintain
  `AGENTS.md` as well as other docs (not observed as an actual AGENTS.md edit in any of the 10 runs
  checked here, which never touch anything but README.md).
- `docs/shiploop-review-after-tests-design-2026-10-27.md:512,528,588,696,827,866,1337` — the design
  document for "a document stage per step," including "it is left out when the step changed no
  behavioural path" and "a review whose document stage records `changed: false` starts no review" —
  this is the design that the 2026-10-29 per-step pilot implements; it predates and specifies rows
  11-12's behaviour (per-step document + per-step Improve review, commit bundling, `changed` signalling).
- `docs/shiploop-sdlc-gates-proposal-2026-10-30.md:99` and candidate 3 (same file) — the base-rate audit
  quoted in pattern 5 and pattern 7 above; this is the closest existing analysis to this report's
  question, but it is a 3-sentence summary without the per-review detail captured here.
- `docs/shiploop-improve-value-journal.md:85-86,171,420-421` — "the other product passes are comment,
  docstring or wrapping edits... (a docstring in `test_hello.py`...)" — these are about Improve reviewing
  **ShipLoop's own** implement-stage code in a different experiment set, not the document stage of a
  product run; included here because they were the nearest "docstring" hits in that journal, not because
  they answer this question.
- No hit in either file for "document-stage README" or "document stage docstring" as a combined phrase;
  the closest prior base-rate ("Document-stage reviews... 5") is the one cited above.

## What was not found / limits

- No run in `~/shiploop-e2e-runs/` shows the document stage editing a knowledge-home file
  (`spec.md`/`architecture.md`/`environment.md`) or any in-code comment/docstring; all such edits in that
  corpus are attributable to other stages by `git log --follow`.
- Three runs' document-stage file changes are **not cleanly separable by commit** from neighboring
  stages (rows 5, 6, 9) — reported as such rather than guessed.
- The two per-step-pilot runs (rows 11-12) are a different host/model/architecture (Codex
  gpt-6.1-terra xhigh, v6 per-step loop) from the 10 Claude/Sonnet-5.5 runs; they are the only
  non-Claude, non-single-pipeline document-stage evidence found, from a 2-arm, 1-case, 1-run-each pilot
  explicitly marked by its own README as indicative, not firm, for cost ratios.
- `fanout-claude-a67220` and `preflight-28c043` have no `state.md` under a real run directory and were
  excluded; `b1-word-report-1c7a7e` stops at `implement` and was excluded for the same reason as the
  `*-interrupt-*` fixtures.
