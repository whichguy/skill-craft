# ShipLoop run trace: journal

Living record of the run-trace work: the question, the design decisions, the evidence and what is still open. Newest
entries last; superseded claims stay, marked with the date and the reason.

## 2026-10-25: the question

Owner request: the in-progress status should be "a dynamic update to data, so a viewer could see or inspect what's going
on", a data file or JSONL plus a reader, inspectable "both by the LLM and by me visually in a nice HTML artifact". It
must show what steps have been run, what has not been run and is still scheduled, and what prompt messages were
injected. Feedback written during the run is wanted later, not in the first pass.

## 2026-10-25: what already existed, and the gaps (firm)

Read from the canonical checkout at `ef5af728` and the chess E2E run of 2026-10-24
(`~/e2e-runs/20261024/chess-sf-full-12a23d`, ShipLoop 1.9.0, 61 accepted steps, 84 packet files):

| Source | What it gives | Gap for this request |
|---|---|---|
| `state.md` `history` | accepted steps in order (action, stage, work item, outcome) | no refusals, no packets, no hooks; Improve stages are not history entries |
| `timeline.json` | when each step was accepted | nothing else |
| `packets/<action>.md` | the packet in full | rewritten in place by every `next`; a reprint or a paused packet overwrites the earlier text, so "what was injected" is lost |
| `status.md`, `progress.html` | where the run is now, plan outline, recent activity | position, not history; no packet text, no refusals |
| `skill-calls.jsonl` | Skill-tool calls (Claude Code only) | only Skill calls |
| keepalive `decisions.log` | stop decisions | in the keepalive home, not the run; no injected text |
| E2E `flow.py` | packets and host events per action | after the fact, E2E only; packet text is the last copy |

The 2026-10-04 ledger design (memory `jsonl-ledger-consolidation-design-2026-10-04`) proposed one `run/ledger.jsonl`
for engine verb calls and left the writer as an owner decision. This request is that decision.

## 2026-10-25: design (firm, built)

- **One append-only file per run, `RUN/trace.jsonl`; "Markdown decides, JSONL remembers."** `state.md` stays the only
  authority; nothing resumes from the trace.
- **Three writers, one module** (`shiploop_trace.py`): `protocol.main` records every command that names the run, with
  the saved state before the verb and the state read after the lock is released (revision, stage and action before and
  after, the history entries it accepted, the refusal text); `navigator.emit` records every printed packet and keeps its
  text in `packets/sent/<sha16>.md` (content-addressed, so a reprint costs one line, not a file); the keepalive stop hook
  records each decision for a bound run with the text it put into the turn.
- **No lock for appends.** One `os.write` on an `O_APPEND`, `O_NOFOLLOW` descriptor; a hook process and a command can
  append at once. Mode 0600 like `state.md`. A failed append never fails a command. Cap 32 MB.
- **Reads and displays are not activity:** `view`, `hook-status`, `trace` and `graph-dry-run` are not recorded.
- **`--check-only` failures are checks, not refusals** (counted separately), since the verb reports and never completes.
- **Reader = `shiploop trace`**: the digest (the shape a model reads: Now, the plan of every stage as done / current /
  reopened / pending with ×runs, +I and !refusals, steps run, recent events, totals), `--action` for one action,
  `--json` for the whole model, `--html` for the page. Events without their own `--action` are attributed to the action
  current at the time (the last packet's).
- **Page = `RUN/trace.html`**, one template (`shiploop_trace_page.html`) with the model inlined; the packet texts are
  screened line by line with the progress view's credential screen. The progress observer rewrites it when the trace,
  `state.md` or `skill-calls.jsonl` change; an active run's page reloads every 10 s, held while a packet is open or a
  search is typed, and a checkbox turns it off.
- **Old runs still read** from `state.md` and `timeline.json`, and say so.

Rejected: extending `progress.html` (bounded, privacy-checked document previews and 967 lines of Python HTML; the
trace is a different consumer); a separate ledger per writer; storing packet text inline in the JSONL (a chess run's
packets are about 2 MB, the trace stays small and greppable).

## 2026-10-25: evidence

- `test/shiploop-trace.test.py`: 15 tests, 18.6 s locally, all pass. They drive real CLI runs (init, a reprint, a
  refused and an accepted intake, pause, resume, status, a failed `--check-only`), the keepalive stop hook with the
  recorded Claude payload, and navigator-saved states past planning (work-item rows, the current slot, Improve marks), plus
  an untraced run, the symlink refusal, the size cap, redaction in the page and the observer writing the page.
- The reader on the 2026-10-24 chess run (no trace; it predates it) shows the whole plan with reruns (W1 implement ×11,
  step-plan ×2 after the send-backs), 61 steps with durations and headlines, and the note that packets are last copies.
- A demo run with every event kind (refusal, hook continuation with its injected text, a head-printed packet, a failed
  check) rendered in the page at desktop and at 375 px in dark mode with no horizontal scroll.

## 2026-10-25: page review: a pulsing "current" on a finished run (firm, fixed)

Owner, looking at the chess page: "We have a flashing bullet for current at every stage, although it looks like the run
is complete." Checked in the browser on the page itself: all 61 stage chips had state `done` (0 `current`), and the one
animated element was the legend's sample "current" chip. It pulsed whatever the run's state, so a finished run read as
running. A critical pass over the same page found three more misreadings:

| What the page showed | Why it misled | Change |
|---|---|---|
| legend: done, current (pulsing), reopened, pending | states the run never had; the sample animated | the legend names only the states and marks the plan shows; samples never animate (0 animated elements on a done run, measured) |
| `implement ×11` | read as eleven reruns; it was four steps, a send-back, a re-plan, six steps | implement shows its current step plan's steps (`6 steps`), send-backs get `↩N`, `×N` means accepted N times |
| tiles `0` packets, `0` refused, `0` commands on a run before the trace | not measured is not zero | `—` with "not recorded"; the digest says "not recorded" |
| rows had no progress | no at-a-glance count | each row says `N of M done` |

## 2026-10-25: original request beside the expanded request (firm, built)

Owner: "We always want the ability to see what the original prompt was and what the expanded prompt was, based on all
the planning activities." What planning records, read on the chess run: intake's summary maps every request sentence
(`S1 outcome: …`, `S2 boundary: …`; 22 of 22 in that run; superseded 2026-10-25: that is one host's shape, and the
reader built on it missed 11 of 27 real intakes, see "live check on a real host run"); each planning stage has a headline and summary; spec names
the living spec's requirements (17, `### R-n.` headings in `docs/shiploop/spec.md`); plan has the work items and 10
assumptions; each item's step plan has its steps (6, 1, 3); answers the owner gave a waiting run are in `decisions/`.

Built: `request_model` in `shiploop_trace.py` builds both sides from current accepted results only (two earlier
step-plan results replaced after send-backs are counted as superseded, not shown); the digest prints two lines,
`shiploop trace --request` prints it whole, and the page opens with it (original verbatim beside the stage list, then
sentence by sentence, requirements, work items with steps, assumptions, owner answers, planning summaries). Spec text and
answers pass the credential screen.

Evidence: `test/shiploop-trace.test.py` 17 tests pass (18.5 s), including intake's reading split by sentence, the request
of a real CLI run with a living spec, a screened requirement and an owner answer, and work items with steps from saved
state.

Test-suite fallout fixed in the same change (quick tier against origin/main): refused commands on retired or unloadable
runs and argument errors created `trace.jsonl` and broke "no mutation" invariants (shiploop-navigator-contract), so a
command is recorded only once its run loaded as current; the page template moved from `.html` to a Python string module
because every file in `scripts/` must compile (shiploop-package-integrity); the context-index map budget rose 3,700 → 3,850
bytes for its three new entries (shiploop-rehydration); a file-set test now expects `trace.jsonl` and `packets/sent/`
(shiploop-status-display); suite counts 100 → 101 (test-groups).

## 2026-10-25: times in the viewer's zone; is intake flawed? (firm)

Owner: "All times should be relative to local time from the viewer's perspective in the browser." The page now formats
every time with the browser's locale and zone (`toLocaleTimeString`), names the zone in the header, adds the date to each
time when the run crosses a local midnight (the chess run: Oct 24 7:09 PM to Oct 25 9:42 AM PDT), and keeps the UTC stamp
as each time's tooltip. Checked in the browser at PDT: `20:56:25Z` shows as `01:56:25 PM`. The JSONL, `--json` and the
terminal digest stay UTC.

Owner, on the demo page's refused intake callback: "Is there some fundamental flaw in intake itself?" No: the demo run's
refusal was staged (a result with no `shiploop-state` fence, written by the demo script to show a refusal), and ShipLoop
refused it as designed. In the real 2026-10-24 chess run the harness read-first panel counts 0 refusals in the whole run
(`flow.py --read-first`, from `events.jsonl`); intake took 142.5 s, 11 turns, 17 tool calls and was accepted on its first
callback.

## 2026-10-25: quality and concision pass (firm)

Owner: "Quality review changes. Detect if any of the prompt skills could actually be more effective or concise ...
Efficiency." Measured on the 2026-10-24 chess run (837 KB `state.md`, 22-sentence request):

| Item | Before | After | Why |
|---|---|---|---|
| `trace --request` text | 22,507 chars | 17,429 (-23%) | the verbatim block repeated the S1..Sn sentences (joined, they are the request); intake's summary repeated the per-sentence readings |
| status-display "Run trace" section | 5,159 chars | 2,674 (-48%) | append mechanics, cap, observer triggers and the digest's legend (printed by the digest) are not acted on by a reader; they stay in the module docstring and here |
| SKILL.md trace line | "Asked what has run …" (no asker) | "If the user asks …" | names who asks; card 30,488 of 30,500 bytes |
| writer cost per command | 1 state parse (5.9 ms) + 0.13 ms append | read-only verbs skip the parse | `status`, `context`, `report` reuse the state loaded before the verb |
| hook import | page template (29 KB) imported by every command and keepalive hook | imported only to render a page | lazy import in `render_html` |
| credential screen | three copies; hook and refusal text redacted whole | one `_screened` helper, line by line everywhere | consistency with packets |

Page rebuild 14 ms, model build 12 ms on the same run.

## 2026-10-25: independent review (Sol), five findings, all fixed (firm)

Reviewer: gpt-6.1-sol, effort medium, read-only, given the code diff and the invariants (never fail or change a command,
never write into a retired or unloadable run, lock-free appends), not my conclusions. Raw output:
`ask-sol-data.json` in this session's scratchpad (not kept in the repo). Nothing raised on efficiency or complexity.

| # | Finding (Sol's severity) | Fix | Pinned by |
|---|---|---|---|
| 1 | P1: a FIFO named `trace.jsonl` blocks `os.open` forever, hanging every command and the keepalive hook | open with `O_NONBLOCK` and refuse a non-regular file after `fstat` | `test_a_fifo_in_place_of_the_trace_is_refused_not_waited_on` |
| 2 | P2: the stop hook and `trace --html` still wrote into a retired or unloadable run | `current_state` (shared with `protocol`) gates `record_stop`; `--html` into such a run is refused (a PATH outside it is allowed) | `test_nothing_is_written_into_a_run_that_cannot_be_loaded` |
| 3 | P2: a command's after-state was read after the lock was released, so a command that ran next was credited to it | the after-state is captured inside the run lock; a refused command's after is its before | `test_a_command_is_credited_only_with_its_own_transition` (fails with the fix reverted) |
| 4 | P2: a run upgraded mid-flight lost its earlier steps from the page timeline after its first traced command | every history step no traced command accepted becomes a timeline event; actions with no traced packet offer their last copy; digest and page say when the trace began | `test_steps_from_before_the_trace_stay_in_the_timeline` |
| 5 | P2: a prompt with `<!--<script>` breaks the page (escaping only `</` is not enough inside a script element) | every `<` in the inlined JSON becomes `\u003c` | `test_a_prompt_with_script_markup_cannot_break_the_page` (fails with the fix reverted) |

`test/shiploop-trace.test.py`: 22 tests pass (21.4 s).

## 2026-10-25: verification after rebasing on origin/main (firm)

Rebased the branch onto origin/main (22 upstream commits, no conflicts). Quick tier for this change
(`test/run_suites.py --group quick --changed-from origin/main`, 41 suites, `--jobs 8`): PASS, 258.8 s wall. The last
commit (page plurals, page template only) landed while the tier ran; `test/shiploop-trace.test.py` passed on it (22).
Not run: the full tier and a live ShipLoop run on a real host with the trace on; the first released E2E run is the live
check.

## 2026-10-25: the release's full CI found what the quick tier missed (firm, fixed)

Main CI on the feature push (`3c333f04`) passed; it runs the quick checks. The release commit (`5485b896`, shiploop
1.12.0) runs the full shards; six suites in four jobs failed (run 40241413798): `shiploop-cross-run`, `shiploop-chain`,
`shiploop-chain-lifecycle`, `shiploop-chain-planning-context`, `shiploop-backchain-check` and the e2e apparatus's
`test_grok_adapter`. None was in the quick selection for this change.

Cause: those suites pin that read-only views (`chain history`, `chain pending`), record-only checks (`backchain-check`)
and refused operations on a retired chain binding leave the run directory byte-identical. 1.12.0 traced the routed
verbs and wrote a packet line for any `emit()`, so `trace.jsonl` appeared. The Grok adapter pins the CLI's verb list,
which gained `trace`.

Fix (1.12.1): only navigator commands on a current run are traced, and packet lines are written only while such a
command runs (`shiploop_trace.ACTIVE`, set by `protocol.main`); `chain`, `lint`, `red-check` and `backchain-check` are not
traced. The cross-run snapshot excludes `trace.jsonl`/`trace.html` as it excludes `packets/` (evidence, not run state).
The adapter lists `trace`. Two trace tests assumed every packet prints whole; a longer install path pushes discovery's
packet over the print limit, so they now accept a kept head. Evidence: the six suites pass locally on the fix.

Lesson: for a change that writes a new file into every run, select the suites that snapshot run directories (cross-run,
chain*, backchain-check) and the e2e apparatus, not only the suites the changed files reference. Gap: chain commands
(ask-agent runs) are not in the trace.

## 2026-10-25: live check on a real host run, ShipLoop 1.12.0 (interim; superseded by the 1.13.1 rerun below, which is firm)

**Question.** Does the released trace (skill-craft 2.12.0 / ShipLoop 1.12.0, `5485b896`) record and show a real host run:
command, packet and hook lines in order; each packet kept as sent; refusals with their text; keepalive continuations
with their injected text; `trace`, `--action`, `--request`, `--html`; a page with no console errors, a legend that never
animates on a finished run, times in the viewer's zone? And do its counts agree with the harness's
`flow.py --read-first`?

**Case.** `hello` (`run.py --case hello --host claude --source marketplace --timeout 3600 --max-budget-usd 15`),
Claude Sonnet 5.5 (`claude-sonnet-5-5`, host default effort), marketplace preflight `--host all` OK on Claude, Codex
and Grok. Output `~/e2e-runs/20261025/trace-verify-4fd9f1/hello` (not in the repo; product never committed). PASS on
every verdict: done in 1,382 s, $7.65, 1 session, 28 accepted steps including a send-back of W1's implement. Two
other harness runs shared the machine (the harness says so), so its time and cost are not comparable. Evidence,
paths scrubbed to `<OUT>` and `~`: `docs/shiploop-run-trace-evidence/2026-10-25-hello-claude-1.12.0/`.

| Feature | Result on the real run | Evidence |
|---|---|---|
| `trace.jsonl` lines in order | worked: 120 lines (81 command, 38 packet, 1 hook), timestamps monotonic; a packet line precedes the command that printed it | `trace.jsonl` |
| packets kept as sent | worked: 38 packet lines, every `packets/sent/<sha>.md` present and matching its sha; 22 printed as a head, each head kept too (60 files); 0 reprints | `trace.jsonl`, `page-check.json` |
| refusal text | worked for navigator verbs (3 refusals, each with its full text, e.g. the step proof's `grep: invalid option -- P`); **not** for the 2 exit-3 `lint`/`red-check` calls, recorded as refusals with no text | `action-implement.txt`, `digest.txt` |
| failed `--check-only` | worked: 2 counted as checks, not refusals | `digest.txt` |
| keepalive continuation text | **not exercised**: the headless Claude session never ended a turn before the run was done; the one hook line is `allow: run is done` (no text, as designed) | `trace.jsonl` |
| `shiploop trace` digest | worked (stages ✓ with ×2, (1 step), ↩1, +I, !1 marks; 28 steps; totals) | `digest.txt` |
| `--action` | worked with `nav-7d0f97f9`; **refused the bare hex `7d0f97f9`** that a reader copies from the digest's `nav-7d0f97f9…` (fixed) | `action-implement.txt` |
| `--request` | **wrong**: "intake read 0 of 1 sentences" and "→ not read by intake", although intake's summary covered S1 (fixed; see below) | `request-released-reader.txt`, `request-fixed-reader.txt` |
| `--json` | worked: the whole model, counts as the digest | (not exported, 101 KB) |
| `--html` | worked into the run and to a path outside it | `page-check.json` |
| page | worked: 0 console messages; finished run 0 animated elements, 24 chips all done, legend names only done and the marks the run has; times `03:57:11 PM` with the UTC stamp as tooltip and "times in PDT"; no horizontal scroll at 1024 and 375 px; active page mid-run animates only its status dot and offers the live toggle | `page-check.json` |
| `workspace start` | **recorded twice**: `init` and `workspace`, both `[None, 0]` (fixed) | `trace.jsonl` lines 2-3 |

**Counts against `flow.py --read-first` (same run).** Reconciled exactly; every difference is a counting rule, none a
lost event.

| | trace | flow | difference |
|---|---|---|---|
| refusals | 5 refused + 2 failed checks | 6 refusals | 3 in both (step proof, verify loop still active, `improve-pass` on an imported Improve stage); 2 `--check-only` failures are checks in the trace and refusals in flow (any failure line); 1 stale `workspace plan-return` only in flow (it names `--workspace-root`, and the trace records commands that name `--run-dir`); 2 exit-3 `lint`/`red-check` calls only in the trace (run by loop drivers, no failure line for flow to see; 1.12.1 stops tracing those verbs) |
| commands | 81 | 88 invocations | 78 in both (56 `complete`, 16 `improve-pass`, 5 `lint`, 1 `workspace start`); trace +2 `red-check` (loop drivers) +1 `init` (the double-recorded `workspace start`); flow +9 `workspace plan-return`/`review-return`/`return` (untraced, `--workspace-root`) +1 `init` that is a heredoc Python script (a flow parser false positive) |
| packets | 38 | 27 producer rows | 38 = 27 producer packets + 11 Improve packets |
| skill calls | 11 | 11 `skill-craft:improve` | none |

**The request view on real runs.** Intake is asked to cite `S<n>`, one clause each, without a fixed shape. Survey of
every accepted intake under `~/e2e-runs` since 2026-10-15 that cites sentences (27 runs): the released reader mapped
all sentences on 16 (all `S1 outcome: …`, mostly Grok and Haiku) and none on 11 (Claude Sonnet and Codex:
`S1: outcome = …`, `S1: Outcome: …`, `S1: outcome - …`, `S1: outcome is …`, `S1 (paraphrase): Outcome 1: …`,
`S1: Deliver …`, `S1 maps to …`). With none mapped, the terminal request view also hid intake's summary, so Sonnet
runs, the E2E default, showed nothing of intake. Every citation in the 27 starts a clause (summary start, after `. `
or `| `). Evidence: `docs/shiploop-run-trace-evidence/intake-sentence-survey-2026-10-25.json`.

**Fixed in this change** (`changes/shiploop/trace-real-run-fixes.md`, patch):

| Defect | Fix | Pinned by |
|---|---|---|
| sentence readings missed 11 of 27 real intakes | `sentence_readings` takes `S<n>` + `kind:`, `:`, `(paraphrase):` or `maps to`; a kind after the colon (`outcome =`, `Boundary -`, `Outcome 1:`) is read, else `reading`; 27 of 27 map | `test_intakes_reading_is_split_however_the_host_words_the_citation` (fails on the released reader) |
| an unmapped intake vanished from the terminal request view; "not read by intake" was false | intake's summary prints when nothing maps; the wording is "no clause of intake's summary cites it" (digest and page) | `test_an_intake_summary_with_no_cited_sentence_stays_in_the_request_view` (fails on the released reader) |
| `workspace start` recorded as two commands | only the outermost `protocol.main` records (`_DEPTH`), with the run the inner `init` or `next` loaded | `test_workspace_start_is_one_command_though_it_runs_init_or_next` (fails without the fix: 4 lines for 2 commands) |
| `--action` refused the bare hex | an id also matches without its `nav-` prefix | `test_one_action_lists_its_packets_commands_and_files` |
| digest plurals "1 checks failed", "(1 reprints)", "of 1 sentences" | `_count` | two assertions corrected in `test/shiploop-trace.test.py` |

`test/shiploop-trace.test.py`: 25 tests pass. Quick tier (`run-all.sh --group quick --changed-from 5485b896 --jobs 6`):
PASS, 27 suites, 173.3 s wall (before the `--action` change, which touches `find_action` only).

**Status: interim** (superseded 2026-10-25 by the rerun on ShipLoop 1.13.1, which shipped as 1.13.1, not 1.12.1, after 2.13.0). The parent session reported that 1.12.0 failed main's full CI and 1.12.1 follows (navigator
command tracing unchanged; `chain`, `lint`, `red-check`, `backchain-check` no longer traced; packet lines only during a
traced command), so the firm check is the rerun on 1.12.1. Not verified on any real run: a keepalive continuation
with its injected text; a reprinted packet. `workspace plan-return`/`review-return`/`return` are not in the trace by
design (they name `--workspace-root`); whether they should be is open.

## 2026-10-25: rerun on ShipLoop 1.13.1, the release carrying the fixes (firm)

**Question.** The same as the 1.12.0 live check, on the release that carries this branch's fixes (`191f272f`) and the
CI fix (`96f023a2`: only navigator commands on a current run are traced; packet lines only while one runs; `chain`,
`lint`, `red-check`, `backchain-check` untraced): skill-craft 2.13.1 / ShipLoop 1.13.1, release `a677b55d`.

**Case.** `hello`, `run.py --case hello --host claude --source marketplace --timeout 3600 --max-budget-usd 15`, Claude
Sonnet 5.5 at host default effort, after `--preflight-only --host all` (Claude, Codex and Grok all got 2.13.1 / 1.13.1).
Output `~/e2e-runs/20261025/trace-verify-1131-b096ae/hello` (not in the repo). PASS on every verdict: done in 795 s,
$4.39, 1 session, 24 accepted steps, no send-back; the harness reported no other run alive. Evidence:
`docs/shiploop-run-trace-evidence/2026-10-25-hello-claude-1.13.1/`.

| Feature | 1.13.1 result | Evidence |
|---|---|---|
| `trace.jsonl` lines in order | worked: 92 lines (58 command, 33 packet, 1 hook), timestamps monotonic; every packet line is followed by the command that printed it | `trace.jsonl` |
| untraced verbs | worked: no `chain`, `lint`, `red-check` or `backchain-check` line, although the host ran `lint` 4 times (one command also ran `red-check`) | `trace.jsonl`, `flow-read-first.json` |
| `workspace start` once | worked (fix confirmed): one `workspace` line `[None, 0]`, no `init` line; the init's intake packet is kept | `trace.jsonl` lines 1-2 |
| packets kept as sent | worked: 33 packet lines, every `packets/sent/<sha>.md` present and matching its sha; 19 printed as a head, each head kept (52 files); 0 reprints | `trace.jsonl` |
| refusal / check text | worked: the run's one failure, a `--check-only` (`expectation E1.from must be the id of an open plan assumption, such as A3`), is a check with its text in the digest, `--action` and the page; the run had no navigator refusal, so refusal text rests on the 1.12.0 run (same code path) | `action-step-plan-bare-hex.txt`, `page-check.json` |
| keepalive continuation text | **not exercised**: the one hook line is `allow: run is done` (no text, as designed); the headless session never ended a turn early | `trace.jsonl` |
| digest | worked; plurals right ("1 check failed", "of 1 sentence") | `digest.txt` |
| `--action` | worked with the bare hex `bcf73ba9` (fix confirmed) | `action-step-plan-bare-hex.txt` |
| `--request` | worked (fix confirmed): "intake read 1 of 1 sentence", S1 → outcome. Intake wrote `S1: outcome - …`; the 1.12.0 reader maps 0 on this very summary | `request.txt` |
| `--json`, `--html` | worked (into the run and to a path) | `page-check.json` |
| page | worked: 0 console messages, 0 animated elements, 24 chips done, legend only done / I / steps, request card "intake read 1 of 1 sentence" with the reading, local PDT times with UTC tooltips, no live toggle on a done run, no horizontal scroll at 1024 and 375 px | `page-check.json` |

**Counts against `flow.py --read-first` (same run).** Reconciled exactly.

| | trace | flow | difference |
|---|---|---|---|
| refusals | 0 refused + 1 failed check | 1 refusal | the same event: the `--check-only` failure (a check in the trace, a refusal in flow) |
| commands | 58 (1 `workspace`, 41 `complete`, 16 `improve-pass`) | 67 invocations (5 `workspace`, 41 `complete`, 17 `improve-pass`, 4 `lint`) | 4 `workspace plan-return` ×2 / `review-return` / `return` (untraced: `--workspace-root`); 4 `lint` (untraced since 1.13.1); 1 `improve-pass` that never reached ShipLoop (`can't open file`: the model mistyped the CLI path) |
| packets | 33 | 23 producer rows | 33 = 24 producer packets (23 stages + `done`) + 9 Improve. flow lacks W1's step-plan: the model sent the `complete` output carrying that packet to `run/scratch/out.txt` and read it in `grep`/`sed` slices, so its head never reached a tool result whole; the trace recorded the print. On 1.12.0 the two lists matched (27 = 27) |
| skill calls | 9 | 9 `skill-craft:improve` | none |

**Status: firm** for every feature above marked worked, on a real Claude Sonnet run of the released 1.13.1, with
the four 1.12.0 defects confirmed fixed. Not verified on any real run: a keepalive continuation's injected text (a
headless Claude session ends its turn only when the run is done; the hermetic test with a recorded Claude payload
stays the only evidence) and a packet reprint. Open, not changed: `workspace plan-return`/`review-return`/`return` are
not in the trace (they name `--workspace-root`), so a release's return steps and their refusals (one stale
`plan-return` on 1.12.0) are visible only in the host stream.

**Test change after the release (63b0392f, test only).** `test_workspace_start_is_one_command_though_it_runs_init_or_next`
failed in CI's full shard on 2.13.1: GitHub runners set a global git-lfs filter, and `workspace start` refuses custom
filters. The test now runs git and the CLI with `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null`, as
`test/shiploop-workspace.test.py` does; a simulated global lfs filter reproduces the failure without it. No product
change, so neither live run above is affected.

## 2026-10-25: the E2E harness reads the trace (firm, built)

Question: the E2E harness predates the trace and rebuilds ShipLoop's side of a run from the host stream: refusals from
tool results (`metrics.ToolLog`; on Claude a refusal piped through `head` or `tail` shows neither its exit nor its refusal
line), packet texts from `packet-archive/` or the last copy in `run/packets/`, and no keepalive decisions at all. Where a
run has `trace.jsonl`, can the harness take those facts from the trace, keep the stream for what the model did, keep older
runs working, and say which source each figure came from?

Design (built, all in `test/shiploop_e2e/`; no skill file changed, so no change note and no release):

- **One reader, `run_trace.py`**, over `shiploop_trace.build`, so the harness attributes events as `shiploop trace` does.
  It gives `failures` (every traced command that exited non-zero, with the stage the run was in, the action, the refusal
  text screened line by line, its first line), `completes`, `packets` per action (each print as sent, `repeat` for a
  reprint), `hooks` (decision and text), and `covers`.
- **Coverage rule.** The trace covers a run when every step the model accepted was accepted by a traced command and the
  trace is not capped. A step the harness seeded (summary `Synthetic…`) is not the model's: step slices seed with
  `navigator.apply`, outside the trace, and still read as covered. A partial trace leaves every count on the stream and
  says why.
- **What only the stream holds.** The trace records only navigator commands that loaded the run. A command that names no
  run (`workspace plan-return --workspace W`), one that does not parse, and the routed verbs (`chain`, `lint`, `red-check`,
  `backchain-check`) are in the stream only. `metrics.outside_trace` tells such a stream failure: no line of the call runs
  a traced verb with `--run-dir`, or its text is an argparse error. `metrics.traced_failures` adds it to the trace's,
  marked `source: events.jsonl`, ordered by epoch stamps. Workspace refusals were found on the first live traced run
  (below); the first design dropped them. Routed verbs: the session that started this work reported that shiploop 1.12.1
  stops tracing them (1.12.0 traced their exit without text), so `run_trace.read` leaves them out on every release, and
  runs on either side of 1.12.1 count them with one instrument.
- **`metrics.json`**: `shiploop_failures` and `gate_counts` come from the trace when it covers the run; `failures_source`
  names the file (and why not); `run_trace` keeps the trace's counts beside the stream's own (`stream_failures`). The
  item shape stays `{verb, exit, line}`, plus `check_only` on a failed check. A failed `--check-only` stays in the list
  because the stream counted it too ("every command that exited non-zero"); the trace's own `refusals` excludes it.
  The fidelity block's `refusals` reads the same list (one count), with the exact stage instead of a timeline join.
  The Run Review exporter reads both from `metrics.json`, so it follows with no change of its own.
- **`flow.py`**: packets as sent (`packets.emissions` prefers `packets/sent/`; `prints`, `reprints`, `sends` per phase),
  refusals and keepalive decisions as events of kinds `refusal` and `keepalive` merged among the host's events on the
  unrounded epoch stamps (rounded to 0.1 s, a fast refusal tied with the next call and landed after it, seen on the test
  fixture), and `sources` naming each part's file. The Read first panel takes refusals by stage and cause from the trace,
  counts failed checks apart, keeps the stream's count beside it, adds a `trace` block (prints, reprints,
  continuations, stops) and takes producer sizes from the packet as last sent. A run without a trace reports per-phase
  refusals and prints as None, not 0.
- **`arms.py`**: a refusal count from the trace and one from the stream are two instruments, so the refusals gate is
  unmeasured (the decision stays open) unless both arms counted from the same source (`refusals_source`).

Not changed: the stream stays the source of the model's calls, text, turns, tool-call windows (`failure_of` in the
reorientation readers) and retired-term counts (`nomenclature` reads refusal lines the model saw).

What the trace cannot see: a ShipLoop command that never loaded the run. Measured on the 211 recorded runs under
`~/e2e-runs` with a `metrics.json` before 1.12.0: 2 of 316 recorded failures were usage errors (both v1161 Luna,
`unrecognized arguments`). A first design left these out (interim, superseded the same day): the first live traced run
showed a `workspace blocked` refusal at `plan-return` that only the stream had, and such a refusal ends every run that
returns its workspace. They are now merged from the stream by the rule above, which needs no time join to find them (only
to order them). Still missing: such a refusal behind a pipe, and a command on a wrong `--run-dir`.

Live evidence (read-only, `~/e2e-runs/20261025/trace-verify-4fd9f1/hello`, Claude, shiploop 1.12.0, read while the
sibling live-E2E session was still running it). The trace holds 7 failures. Two of them are routed verbs (`lint` and
`red-check`, exit 3, no text), which the harness now leaves out, so 5 remain: 3 refusals and 2 failed checks. The
harness's list has 6: those 5 and the workspace refusal from the stream. The stream also counts 6, and they are the same
failures, so this run's total did not change. The trace corrects three things. It names the step-proof refusal's verb
`complete`, where the stream said `lint` because the command ran `lint` too. It gives the exit for the four the model
piped, which the stream recorded as not shown. It gives the stage the run was in. The two routed exits are in neither
list: the stream's verb pattern does not know `red-check`, and the `lint` result was piped.

`gate_counts` classifies every line `other` on both readings (no signature fires on this run). It catches 5 of 6 by the
trace's accepted `complete`, against 3 of 6 by the stream's. An earlier reading of the same run, before routed verbs were
left out, gave 8 and 6 of 8; it is superseded the same day by the 1.12.1 rule. A second traced run
(`gate-212-8a49cf-grok-hello`, Grok) has no failures. Its `research` packet was printed 3 times (2 reprints), which no
stream reading counted.

Evidence: `test/shiploop-e2e-run-trace.test.py`, 15 tests, 2.1 s. The fixture is a real CLI run in a temporary E2E
folder with a Claude stream written around its calls: a reprinted intake packet, a failed `--check-only` shown to the
stream, a `workspace plan-return --workspace` refusal and a usage error (neither loads the run), a `lint` that could not
run (exit 3), a refusal piped through `| tail -1`, a keepalive continuation, the accepted intake and a reprinted discovery
packet. On it the stream counts 4 failures and misses the refusal; the trace counts 1 refusal, 1 failed check, 4 prints (2 reprints) and 1 continuation;
`shiploop_failures` holds all 5 failures in order (with a `lint` that could not run, read from the stream), and the
refusal's text appears in `flow.json` right after the call that caused it. The same folder without its trace reads exactly as before (stream counts, `retained` packets, None for unrecorded
counts), and a trace stripped of its accepting command reads as partial and falls back with its reason. Checked in the
browser: the viewer shows the refused and check-failed events with their text, the keepalive text, and "printed 2× (1
reprint)" on each phase. The new suite is registered (101 → 102 ShipLoop suites, 156 → 157 in all).

Quick tier (`test/run_suites.py --group quick --changed-from 6b678500`, the merge-base with origin/main, `--jobs 8`).
The first commit's run failed 1 of 37 suites: `shiploop-e2e-slice` pinned the packet report's `emissions_source` as the
archive. Its fake host drives the real CLI, so the run has a trace and the source is now the trace, which is the change
itself; the test now pins that. The final tree (`03ddfe06`, clean) passed all 37 suites in 226.6 s. Not run: the full
tier, and a regrade of a finished traced E2E run through `run.py --resume-run <output> --grade-only` (the two traced runs
of 2026-10-25 belong to the sibling live-E2E session and were only read). The branch is not yet rebased on shiploop 1.12.1,
which had not landed when last fetched.

## Open (exploratory)

- **Owner feedback during a run** (the "nice to have"): a `shiploop note --run-dir RUN --text …` verb that appends a
  `note` event, and the next packet quoting unread notes. Needs a packet change, so it waits for the owner.
- ~~**E2E consumers**: `flow.py` and the Run Review exporter rebuild the sequence from host streams; they can read
  `trace.jsonl` instead for refusals, reprints and hook text once a released run has one.~~ Superseded 2026-10-25: built,
  see "the E2E harness reads the trace" above; the exporter follows through `metrics.json`. The 1.13.1 rerun shows
  the gain: flow missed W1's step-plan packet (redirected to a file, read in slices) that the trace recorded, and
  counted a heredoc script as `init` on 1.12.0.
- **First live check of the harness's trace reading**: no released E2E run with a trace has been regraded through
  `run.py --resume-run <output> --grade-only` yet; the two traced runs of 2026-10-25 under `~/e2e-runs/20261025/` had no
  refusals or hook decisions to compare.
- **Hosts other than Claude Code** record Skill calls nowhere; the trace does not change that.
