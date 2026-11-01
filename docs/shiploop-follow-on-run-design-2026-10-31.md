---
Status: design proposal, revision 3, 2026-10-31. Nothing is built, adopted or released. Execute: ask. Revision 2 folded in
the multipass work that landed after revision 1 and corrected one stale claim (section 6, the 589bc03e row). Revision 3
brings up to date the multipass facts that moved after revision 2 (a live result, an owner decision, a built test case) and
changes no recommendation. Anything that moves (a queued run, a pending result) is written "as of" a commit and points at the
journal that keeps the live state.
Consumer: the owner, deciding D1 to D4 (section 10). Later: the session that runs the replay (section 7) or builds the follow-on list (section 8).
Journal: docs/shiploop-follow-on-run-journal.md (Rounds 0 to 2).
Evidence: docs/experiments/follow-on-peek-20261031/README.md.
Category: a proposed generic ShipLoop improvement and the exploratory evidence behind it. No E2E apparatus change, no skill change, no release.
Base: df44fd30d19455515cc2434dd21b18520e2a5f48 (origin/main when revision 3 was written). Revision 2 (published as
671873bce787d9e9c25bbbe8ab64e7c7f7061db0) was written at 240594c9922c42ac0a761717671f93f220e31743 and revision 1 (published as
17cb4e4ad859f89bbc578c06abf974e47e0933e3) at 4a75a13d052c994c3e855b9d556637fde05c0b58.
---

# A post-delivery follow-on run for ShipLoop

## 0. The question

Owner, 2026-10-31, dictated, verbatim:

> I was considering if we need almost a replanning-style activity. After everything is done and deployed, we reconsider
> learnings and determine if the feature or spec could be improved in some way. If we do, we almost re-enter the ship loop
> again from the top level with an improvement command, re-entering the graph cycle rather than exiting.
>
> Again, these would be for substantial features which we think haven't concluded. An idea would be maybe this is behind a
> gate of sorts, but we would want to get to the end and ask if there are any key learnings that we understood now about the
> implementation. We would ask if there's a missing set of enhancements that we need to do, which we have now understood and
> learned, which maybe weren't caught in the spec and the step planning and so forth. We want to go all the way back into the
> ship loop again with a prompt, and that would enhance it more and then rerun through everything again. Help me think
> through this.

Three parts: (a) an end-of-run reflection on what building and shipping taught; (b) a decision whether the feature or spec
should improve, behind a gate, for substantial features that have not concluded; (c) re-entry at the top with a prompt, then
the whole loop again.

## 1. Answer in brief

- ShipLoop already writes the reflection and already has two loop-backs. What it lacks is the decision that turns the
  reflection into a run, or into a question for the owner.
- Shape (D1): a follow-on run, which is a new run on the delivered baseline, not an in-run back edge to spec or plan.
- Mechanism (D2, D4): a follow-on list in the handoff result, which is the run's leftovers classified once, each entry citing
  a record. The script checks the citations and routes. The first version recommends only: it prints a ready follow-on
  request and the start command, never starts a run, and never blocks `done`.
- Evidence so far (exploratory, section 5): of 122 archived runs that reached handoff, 3 name a decision a person must make
  about the spec or scope, and none leaves a gap the system could close alone. The outcome for a gap a run notices in-run,
  `add-work`, was used in 3 of 125 runs.
- Revisions 2 and 3: the multipass work of another session, which landed on main after revision 1. It measures a pass started
  by a person on the repository an earlier run left (a pass is one such run). Its findings support the shape: all 8 saved runs
  of four ticket pairs passed, the 4 second passes kept every earlier requirement and decision, and the first live third pass
  (its E1) passed and kept the earlier requirements too. It supplies the chain harness and the readout for the live measurement (section 7). It
  also shows every pass leaking activity into the permanent files, the third pass included. The owner has approved that work's
  fix, which stays off main until an A/B test (its E2) meets its bar; E2 had no result on main as of this revision's base. So
  a chain of follow-on runs waits for E2's result (section 4.7).
- Order: replay the gate with a second reader first (offline, no ShipLoop run); build the recommend-only version only if the
  replay supports it; consider chaining runs only with new evidence and the owner's calls on D2 and D3.

## 2. What ShipLoop already does (read at the base commit)

| Mechanism | Where (symbols) | What it covers | What it leaves for this idea |
|---|---|---|---|
| Reflection | the `release-verify` row of `shiploop_stage_spec` (done-when: the result's lessons hold "what this run learned, the key considerations and what a later run should pick up") | `Learned`, `Key considerations`, `Open for the next run`, always committed as the lessons commit (`shiploop_knowledge_home.LESSON_FIELDS`, `lessons_body`, `LESSONS_SUBJECT`) with a generated block of unsettled open items; required since 2026-09-26 (d39b56af) | free text; no script reads its classes; nothing decides |
| Delivery to the next run | `knowledge_home.last_lessons` (found by subject); intake and discovery quote it; `shiploop_workspace.follow_up_knowledge_return` carries even an empty lessons commit to the source branch; `navigator._handoff_sections` prints the lessons and, after a working-tree return, the exact message to commit | the next run's intake sees the lessons | a pull path: a person starts the next run |
| Outcome challenge before release | `product-acceptance` ("assess the product against the original outcome, not only the spec"); the end-of-work Improve review | request versus spec, before release | no evidence from after release |
| In-run loop-back | `add-work`: `shiploop_stage_spec._finish` gives it to every outer stage, so `product-acceptance`, `release-verify`, `operations` and `handoff` all accept it; `navigator._accepted_done` reopens every outer stage accepted before it; the new items are built and the run resumes at `system-test-author` (c6c82b16, which renamed `replan`) | gaps the run notices, including after release | appends items under the same request; no path to spec or plan |
| Inner loop-back | `send-back` to `step-plan` (`SEND_BACK_TO`); outer `OUTER_SEND_BACK_TO` for `system-test` and `release-verify` | a record an earlier stage wrote is wrong | a stage re-runs; no new request |
| Pre-dispatch edge | the plan Improve "reconcile" to discovery, research, spec or test-strategy (`planning_revision.RECONCILIATION_TARGETS`); `system-test`, `product-acceptance`, `release-verify` and `handoff` carry `blocks={"reconciliation"}` | planning reviews | closed after dispatch |
| Leftovers with owners | `unverified` (`unverified.current_list`, `must_restate`: product-acceptance writes it and the handoff restates it); `assumptions.open_items` | structured, script-read, each with an owner and a due stage | request outcomes only; `open_items` never closes a plan row |
| A new run on a delivered baseline | SKILL.md "for a later feature request"; the knowledge home; the ticket-assignment then ticket-escalation pair (SPEC, brownfield); the next-run probe (a953e68a) | inherits the living spec, architecture and environment; the requirement IDs a run added are derivable with `spec_diff` from the run baseline; there is no per-run feature spec and no retire step since 2026-10-11 (589bc03e) | started by a person with a hand-written request |
| Chains of passes (test apparatus) | `test/shiploop_e2e/chains.py`, `delta.py`, the cases `ticket-comments` and `ticket-sla`, and the [multipass plan](shiploop-multipass-plan-2026-10-31.md) and [journal](shiploop-multipass-journal.md). A link is one case that follows another; the delta ledger is a record kept beside each run of what it changed compared with the run before | eight saved runs (four pairs, a first and a second pass each) read: all passed, and the four second passes kept everything (03d046c6); a no-model probe shows the lessons reach a third pass's first packet (aa601d37); the first live third pass passed and kept every earlier requirement (c55d0bc0); the fourth link, a request that replaces an earlier rule, is built and calibrated on hand-written variants and has not run live (bf68e959) | started by a person; nothing starts a pass from a run's leftovers; every pass leaks activity into the permanent files, the third pass included |
| One request per run | SKILL.md: an `init` retry with a different prompt is refused; `request.md` splits the prompt into S1..Sn; IN1 (70d88d37) | stable anchors for intake, spec, plan and the trace | an in-run "new prompt" has no home |

## 3. Options for the shape

For each: the strongest case for, the strongest case against, a verdict.

### A. An in-run back edge from the outer phase to spec or plan

- For: one run and one report; it is what "re-enter the graph cycle rather than exiting" says; `add-work` and the trace's
  `reopened` slot show the engine can invalidate and rerun stages.
- Against:
  - A run tracks one request. The sentences S1..Sn anchor intake (IN1), the spec's `primary` requirements, `follows` at plan
    and the trace. An enhanced prompt inside the same run changes the anchors under results already accepted.
  - A back edge to spec invalidates every result after it. That is a new run carrying the old run's baggage, and the engine's
    stance for saved runs is that nothing is converted or partly resumed.
  - Delivery authority is per run: a "yes" covers this run only unless the user says "standing" (SKILL.md). A reopened run
    silently extends a grant.
  - `done` stops being final, and handoff has side effects: the return receipt and the knowledge close (commit, follow-up
    return, print). Reopening after them is not defined.
  - It touches `graph`, `_accepted_done`, `planning_revision.current_actions`, the trace, the progress view and keepalive.
- Verdict: no.

### B. A follow-on run (recommended)

- For:
  - It reuses a tested path. The next-run probe found a cold follow-on consuming the living files where expected (a953e68a),
    and the brownfield pair measures that a follow-on keeps what the first run learned.
  - The multipass readings back it: all 8 saved runs (four pairs) passed, and the 4 second passes kept R-1 to R-5 byte for
    byte, touched no earlier test and planned no test case for an old requirement (0 of 19). The first live third pass (E1)
    did the same at the third pass of one lineage: 13 of 13 checks and 14 of 14 inherited hidden checks passed, R-1 to R-7
    were kept byte for byte, no earlier test was touched and 8 planned test cases cite no kept requirement (c55d0bc0). A
    request that is the delta alone is what those cases use (03d046c6).
  - The request is new, so intake, spec, plan and tests anchor to it. The owner's rule that a step's tests follow that step's
    own intention (fdec0f6e) holds unchanged.
  - `done` keeps its meaning: the request was delivered. Authority is asked again. No new edge type.
- Against:
  - A second prelude (discovery, the baseline test run, research, spec, plan) is paid again for even a small delta.
  - The lessons must reach the new run. They do by subject (`last_lessons`), not by position in the last three commits: one
    more closing commit once pushed them out of the window (49c502ea, K13). A no-model probe of four saved second passes
    confirmed the lessons are quoted correctly in a third pass's first packet (aa601d37).
  - Each pass leaks activity into the permanent files (multipass journal F1 to F3). `environment.md` gained 4.5 to 6.4 KiB
    in the second pass, mostly stage reports under headings of their own (32 of 36 stray headings; 4 are the release
    procedure the consumer contract intends). In one of four runs a live decision was filed under `## Superseded`, and the
    engine then labels it superseded. The first live third pass (E1) repeated both: `environment.md` gained 8 stray headings
    (+6.0 KiB, 10,531 to 16,637 bytes), and its new decision AD-4 was filed after `## Superseded`, below the earlier pass's
    still-mislabelled AD-3, so it was born retired (c55d0bc0). Against the four second passes (7, 1, 6 and 4 stray headings;
    4.5 to 6.4 KiB) that is one heading above the highest count and inside the byte range, so the growth per pass looks
    steady and not accelerating, on one run of one lineage; what builds up is the mislabel, under which a later pass files its
    new decision. A packet lists at most 40 headings of a file, so on the observed growth the newest sections are first cut in
    the fifth pass's packet (arithmetic, not seen on a run). A chain of follow-on runs repeats this at machine speed; one
    follow-on run is no worse than the person-started second pass it replaces.
- Verdict: yes for one follow-on run; a chain waits for the multipass fix to meet its A/B test (section 4.7).

### C. Stay manual (today)

- For: no engineering; the archive shows 3 decisions in 122 runs; the report already prints the lessons and the open items
  (8d51a8e9).
- Against: the decision sits as free text inside a commit body (and, after a working-tree return, not on the branch at all);
  nothing classifies it, cites a record for it, or builds the request; the owner asked for the activity.
- Verdict: the baseline to beat, and the right answer until the replay (section 7) supports more.

### D. A model-judged reflection stage with an Improve-style loop ("anything to improve?")

- For: simple to state; a model may notice what the ledgers do not hold.
- Against: end-of-run model-judged checks have refused honest runs (the TS1 replay refused 5 of 8, a6eca10c and 70d88d37);
  the coverage ledger found nothing for an end-of-run step to bind (6c626574); d9fefb11 found no evidence for another final
  stage, a stronger refusal gate or longer loops; "anything to improve?" has no checkable exit, so it invites endless polish
  nobody asked for (gold-plating); a new stage shifts the pinned packet counts.
- Verdict: no.

## 4. The mechanism (option B)

### 4.1 Where, and what absent means

A structured list `follow_on` in the `handoff` done result, following `unverified`. The handoff already reads intake, spec,
plan, product-acceptance, release-verify and operations, so the list can include what operations learned, which the lessons
commit (written at release-verify) cannot. As with `unverified`, an empty list says the run classified its leftovers and found
none to act on; a result without the key says nothing (unmeasured is not zero). The stored shape stays loose and the exact
shape is held at the CLI gate only, so a saved run is not refused for it.

### 4.2 An entry (draft; the shape is fixed at build)

An entry drawn from a real leftover (row 8 of the peek, a csv-report run; the JSON shape is this draft's, not a stored record):

```json
{"id": "F-1", "class": "decision",
 "statement": "Whether exponent notation and a leading + count as numeric, and whether zero arguments exit 1.",
 "source": "lessons.open_next", "evidence_refs": ["RUN/results/<action>.md"], "request_sentence": null,
 "needs": "the requester's answer"}
```

A constructed `gap`, for contrast (the archive has none):

```json
{"id": "F-2", "class": "gap",
 "statement": "The delivered CLI exits 0 on an unreadable file although S2 asks for exit 1.",
 "source": "unverified:R-2", "evidence_refs": ["RUN/checks/<action>.md"], "request_sentence": "S2",
 "needs": "a work item that makes the exit code match"}
```

### 4.3 Classes

From the 25 rows of the peek (section 5):

| Class | Meaning | Routing |
|---|---|---|
| `gap` | a request outcome unmet, or an assumption refuted, that the system could close without a person | the only class that can recommend a run on its own |
| `decision` | a choice or an answer a person must give about the spec or scope | a question in the report, with a ready request |
| `person` | a person must do or confirm something | recorded and shown |
| `capability` | a later run with a capability this run lacked could close it | recorded and shown; only a host that has the capability can act (U5) |
| `extension` | optional or conditional scope beyond the request | recorded; never starts a run |
| `debt` | a small hygiene item inside the request's scope | recorded |
| `note` | knowledge for a later change; nothing is open | recorded |

The vocabulary is generic (S-13): it names no stack, platform or product.

### 4.4 What the script checks (mechanical only)

The same discipline as `unverified`: refuse only mechanical faults, record and print the rest, and state the exit in the
refusal.

- The list is present; each entry has its keys; `class` is in the vocabulary.
- `source` resolves to a record in the run: an unverified row, an assumption id, the lessons text, or a commit that
  `git cat-file` resolves. A hash typed by the model is never trusted.
- A `gap` cites a request sentence S<n> that exists in `request.md`.

It does not judge whether an entry is true or the list complete. A model that files everything under `note` only
under-recommends, which is today's behaviour.

### 4.5 Routing and the request file

The script computes `recommend` as: any `gap` or any `decision`. When it holds, it writes `RUN/follow-on-request.md`:

1. Request: each `gap` statement and each `decision` question, with its evidence references.
2. Preserve: say that everything the project already does keeps working (the multipass cases say the same in their
   delta-only requests), keep the decisions in the living spec and architecture unless a finding says otherwise, and run the
   existing suite first. This restates for a prompt the rule of AGENTS.md: preserve earlier decisions unless new evidence or
   an explicit owner decision warrants changing them.
3. Context: the path of this run's `request.md` and the lessons commit subject, not the verbatim original (U2). The
   multipass runs planned only the delta from a delta-only request (0 of 19 test cases cite a kept requirement), which
   favours this.

The final packet and `report.html` show the list, rendered by the script (S-15), and print the start command:

```sh
python3 "$CLI" workspace start --repo "$REPO" --prompt="$(cat <RUN>/follow-on-request.md)"
```

Command substitution keeps the text out of the shell's re-parsing, so no `--prompt-file` option is needed. A new verb would
cost more: it has to be added to `SHIPLOOP_DIRECT_SUBCOMMANDS` in `skills/shiploop-e2e-audit/harness/grok_adapter.py`, and
the five host fixtures under its `fixtures/host` re-pinned.

### 4.6 What it never does

Block `done`, start a run, ask a question (S-14: a `decision` is an open item in the report), or add a limit. Blocking `done`
is excluded by evidence: an end-of-run gate that refuses has refused honest runs (the TS1 replay, section 6).

### 4.7 A chain, if D2 chooses auto-start

`shiploop-drive`, or the host, starts the next run when `gap` entries exist and the owner's setting allows it. The new run
records which run it follows. The chain ends when a run's list has no `gap`, or when a `gap` returns unchanged (same source
and statement) after a run that claimed to close it: the chain stops and reports (a state-repeat stop, not a count; S-10).
`decision` entries are surfaced, never chained. A dollars or minutes ceiling is the owner's to set (D3).

The engine has no field for which run another follows: `--continue-from` and `follows` belong to the test harness, so a chain
would add one. One third pass has run (E1) and nothing retained was lost, so function is not what holds a chain back; the
leak is. The owner approved the multipass fix for what stages write to the living files (its D2 to D4, 15ef676f). It is built
as a candidate on another session's local branch and stays off main until an A/B test (E2) meets a bar fixed before its first
run. As of this revision's base E2 had no result on main and no fourth pass had run. The multipass work's own replay found a
gap in the candidate: both entries filed as retired when new (AD-3, AD-4) were written by the plan stage, which the
candidate's packet line does not reach (c55d0bc0). So a chain waits for E2's result and no longer for a decision; the
multipass journal (Rounds 2 and 3) holds the live state.

### 4.8 How it sits with the rest

| Existing part | Relation |
|---|---|
| Improve | unchanged. It verifies this run; the follow-on validates the request against what building and shipping taught |
| `add-work` | unchanged. It closes in-run what the run notices; the list holds what remains, so `gap` should be rare (section 5) |
| `send-back`, reconcile | unchanged |
| `unverified`, `open_items`, lessons | their rows are the `source` of entries; none is replaced |
| the lessons commit | unchanged; still the pull path, now with a ready request beside it |

## 5. Evidence so far (exploratory)

Full method, the 25 rows and the limits: [the peek](experiments/follow-on-peek-20261031/README.md). One reader, Claude
Sonnet 5.5; E2E cases only; no model was run.

| Measure | Value |
|---|---|
| runs that reached handoff | 122 of 125 readable |
| `Open for the next run` has text other than "none" | 45 (37%) |
| ... and real content after dropping "None for ..." phrasings | 25 (20%) |
| runs with an add-work / with a send-back | 3 of 125 / 30 of 125 |

Of the 25: person 6, capability 4, extension 4, debt 1, note 7, decision 3, gap 0.

Reading:

- A gate on "something is open" is noise: 20% to 37% of runs, none actionable by the system.
- The three decisions are the owner's scenario in miniature: a spec ambiguity (csv-report), an enhancement the build revealed
  (ticket-assignment: whether `ticket.assigned` gets a real delivery route), and an unresolved assumption (ticket-escalation:
  person-level delivery). Each waits for a person. The useful output is a decision with a ready request, not an automatic loop.
- Gaps the run notices are already built in-run with `add-work`, which `handoff` accepts. What remains in `Open for the next
  run` is what the run chose not to close or could not.
- The archive cannot show the value of the idea. Every completed brownfield run passes its held-out checks (the acceptance
  checks the run never sees; 26 of 26, 593b4b44), so there is no room left to show a gain, and the one case built so that deciding facts only running settles (XI, `ticket-import`) produced no
  completed-but-wrong baseline: 3 of 6 baseline runs passed every check and the other 3 paused at step-plan on an
  open-assumption rule (2ae6200e). A reflection can only list what the run knew it left open.

### What the multipass work adds (revisions 2 and 3)

Read in full after rebasing: its [plan](shiploop-multipass-plan-2026-10-31.md), its
[journal](shiploop-multipass-journal.md) and commits 03d046c6, aa601d37, 84b6bdd2, 1bdeac40 and 737640ca; revision 3 read
15ef676f, c55d0bc0, c981605d, d1e5df37 and bf68e959 the same way (full hashes in section 6). A pass is one run on the
repository an earlier run left; a link is one test case that follows another; the delta ledger is a record kept beside each run
of what it changed compared with the run before; E1, E2 and E3 are the multipass journal's names for its first live third
pass, its A/B test of the fix for the leaks, and the live run of the fourth link. Most of it read eight saved runs and called
no model; E1 is the one live run so far.

- A second pass works: all 8 saved runs (four pairs) passed, and in the 4 second passes R-1 to R-5 were kept byte for byte, no
  earlier test was touched, and 0 of 19 planned test cases cite a requirement the run did not add. This is the best evidence for shape B.
- The lessons reach a third pass: a no-model probe of four saved second passes shows the last three commit messages and the
  newest lessons commit quoted in full in the third pass's first packet.
- A third pass works too. The first live third pass (E1: `ticket-comments` continuing from a saved second pass, ShipLoop
  1.26.0, Codex gpt-6.1-terra at xhigh) passed 13 of 13 checks and 14 of 14 inherited hidden checks, kept R-1 to R-7 byte
  for byte, added R-8 and AD-4, touched no earlier test and planned 8 test cases that cite no kept requirement. Planning did
  not grow: 302 s, against 322 s and 328 s for the two earlier passes of that lineage. Of the six predictions written before
  the run, three held, two missed in the good direction and one missed on a single clause (c55d0bc0). One run, one lineage.
- Passes leak into the permanent files, and the third pass repeated both leaks (section 3.B): 8 stray headings and +6.0 KiB in
  `environment.md`, and a new decision born retired under `## Superseded`.
- A fourth pass has not run. The fourth link, `ticket-sla`, asks a pass to replace an earlier rule ("a ticket is escalated at
  most once" becomes "at most twice, and by priority") and to change the requirement, the decision behind it and the tests that
  state it together. It is built with an acceptance of its own and a ledger that says whether the old requirement and decision
  were changed or left standing; its 11 hand-written variants (a base, a reference, an alternative and eight defects) each
  failed exactly the checks that read what they break (bf68e959). Its live run (E3) waits for E2. Its request is hand-written,
  and none of the peek's three `decision` rows concerns how often a ticket is escalated.
- The ticket chain is at its ceiling too: every pass in it passes (E1 included), so it can show the mechanics of a follow-on
  run, not its value (section 7, M2a and M2b).

## 6. Earlier decisions this design respects

Read in full before writing; hashes resolved with `git log -1 --format=%H`. Revision 2 corrected the `19c25538` row and added
the rows from `589bc03e` on. Revision 3 added the rows from `15ef676f` on.

| Commit | What it decided or measured | Consequence here |
|---|---|---|
| d39b56afba1c8f867028e6feacad03f0103d633c (2026-09-26) | the owner's learnings commit: `Learned`, `Key considerations`, `Open for the next run`, quoted at the next intake; "the script checks the sections exist and are non-empty, not how good" | the pull path is the owner's own decision; the follow-on list adds to it and replaces nothing; the script cannot judge the text, so the class is a recommendation |
| 49c502ea75d41c7541f7e4cedce770b0a04d4ecd (2026-10-11) | `LESSON_FIELDS`, `lessons_body`, `last_lessons`; always commits, empty when the home is unchanged; K13: one more closing commit pushed it out of the last-three window | the follow-on request names the lessons subject; no closing commit may be added after the lessons commit without re-checking the window |
| 5e6643b3525baab5336af01b9fdd3ca580d7f956 (2026-10-11) | the follow-up return carries the empty lessons commit to the source branch (a blocker once) | the new run finds the lessons where the source branch has them |
| 8d51a8e988864479333de044202a20f0e5c481dc (2026-10-11) | the report is the consumer for the person who asked; it shows every hand-off and the exact lessons message after a working-tree return | the follow-on section belongs in `report.html`, script-rendered |
| c6c82b16b8dc57cdb72ea4f43b75cbc1f69ce446 (2026-10-18) | four outcomes; `add-work` (was `replan`): missing product work is built, then the run resumes at `system-test-author`; the old set made the model choose among overlapping names | no fifth outcome; a follow-on is not an outcome |
| 19c255386d11100ac0e8e080a0848632a0f71ede (2026-10-10) | built the handoff retire of the run's feature spec into the living spec (33 of 33 saved runs). Revision 1 cited it as current; it is not | superseded by the next row |
| 589bc03ebe4bb31759a371e10bbc261bb071aab3 (2026-10-11) | the next day removed the feature folder, the handoff retire, `outcome.md` and the feature list: the terminal close is commit, follow-up return, print; added IDs travel by `spec_diff` from the run baseline and the lessons by the lessons commit | at `done` there is no per-run spec to retire; the three living files and the lessons commit carry a run into the next, and a follow-on run needs nothing else |
| a953e68a8c23fb2738e3cfa51ee4304a73d147b8 (2026-10-11) | next-run probe: a cold follow-on consumes the living files where expected and opens the earlier test-spec, system-tests and release-plan as precedent | follow-on runs work; their persistent inputs belong in `environment.md` |
| a6eca10c6cc460047cbd8ec01509509c1d3ceb62, 70d88d379fece7457b9136b39ab8d586fd43cdae (2026-10-26) | an end-of-run coverage check refused 5 of 8 honest runs; the check moved to where the link is made (TS1, IN1) | never gate `done` on the list; check a link where it is made |
| fdec0f6ed642165effd33be640974c9ee25c1561 (2026-10-29) | owner: tests follow that step's own intention; coverage of the request is a property of the plan | the follow-on request must state its own intention; its plan checks coverage |
| d9fefb1144dea7f9a8d85b5897ad1275dbe08a07 (2026-10-31) | no evidence for another final stage, a stronger refusal gate or longer loops; the owner's hold on live E2E cycles | no new stage; the replay is offline; any live case (M2) needs the owner's go |
| 6c6265747116b6ba2ca2a8dd11a2f28bb0551b3b (2026-10-31) | 0 of 331 requirements end untested; an ID-keyed end gate would need a disposition for 25% of rows | no ledger gate; `ledger.find_runs()` is reused as the loader |
| 593b4b44cfc0a166e01fe3a61e301ba85833c8a8 (2026-10-31) | 26 of 26 completed brownfield runs pass every held-out check, so a required step "has nothing to bind"; XI pre-registered | the corpus is saturated (every completed run already passes, so nothing is left to repair): absence of gaps here does not refute the idea; M2 needs a case that can show one |
| 2ae6200e05ef0d95bc05fa592c9ae0cf6ef7d018, c30e706ca8710fa65e74865f54497b032a2ff52c (2026-10-31) | XI: baseline 3 of 6 pass, the 3 failures were step-plan stalls (since changed by fix 1 in 2.27.0), probes ran in 1 of 6; not adopted | no completed-but-wrong baseline exists even in the case built for it; research probes are a separate line |
| 20769530290a7bc4db71cef6b57afe24d0f2c418 (2026-10-31) | a published-skill csv-report run whose existing recovery worked: "do not change effort, review schedule, loop exits or add a final stage from it" | the same stance: no stage, no loop change |
| 8bae4bd6ff87503eb4a7c5bb160a776725354eb9, ea46f9493c4c3fc2d153cfe16563eb7d84324ffd (2026-10-31) | the owner's rule for learning commits and history reads; a rejected candidate leaves an empty commit, not files | this note is a proposal with its investigation, not a candidate; the commit that lands it follows the rule |
| 03d046c64f2edce109394e2cecf3085b3e1c20c2 (2026-10-31) | the multipass harness: `chains.py` (a chain of three links once dropped link 1's checks; fixed), `delta.py`, the case `ticket-comments`; eight saved runs (four pairs) read: all passed, the four second passes kept everything, and every pass leaked activity into the permanent files | the chain harness and the ledger are the fixture and the readout for M2a; the leaks are the cost of a chain |
| aa601d37d2f97434fd51c00e0a05b494c692cb91 (2026-10-31) | a no-model probe pinned what a third pass is shown first: the lessons are quoted correctly; a packet lists at most 40 headings of a file | the lessons commit reaches a follow-on run; the cap does not touch it, because the lessons are quoted whole |
| 84b6bdd247288d3c81b2c717a7dde3bbfef7fc52 (2026-10-31) | cited the pushed commits in the multipass journal after the work landed, and scored predictions written before the live run from the run's own files | the way to cite hashes (a commit cannot cite itself) and a model for M2a's readout |
| 737640caa50ef567d154259b7260c907a6cba5dd (2026-10-31) | corrected its own count: 32 of the 36 stray headings are the defect, 4 are the release procedure the consumer contract intends | cite 32 of 36, not 36 |
| 39bb5d5da1cb1e36716d0ecacabcfc1725fbb3af, 87d3da8e22ee5158a6d3b877752a22eaf3e8e27b (2026-10-31) | the SG2 smoke: nine slices, all correct at implement time, the end-of-item review changed nothing; the owner closed SG2 | the same ceiling seen from the review side: where the producer writes the specified behaviour, a reflection by the same model has little to add (U1) |
| 15ef676f7b20a95d60c8047b0a3fcdac82cb1d3f (2026-10-31) | the owner's "Approve all" to D1 to D5 of the multipass plan; the leak fix (its D2 to D4) is built as one candidate, kept off main and merged only when its A/B test (E2) meets a bar written before the first run; E2 runs three chains on the base and three on the candidate | the fix is decided and waits for a measurement: a chain waits for E2's result and no longer for a decision; unaccepted candidate code stays off main (AGENTS.md, Decisions, 2026-10-30) |
| c55d0bc0ad21a2c477d024067378d0c3b1241959 (2026-10-31) | E1, the first live third pass: 13 of 13 checks and 14 of 14 hidden checks passed, R-1 to R-7 kept, both leaks repeated (8 stray headings, +6.0 KiB, AD-4 born retired); an offline replay found that the candidate's packet line does not reach the plan stage, which wrote both entries filed as retired when new | a third pass works and leaks again; the candidate may not stop the born-retired entry alone (the multipass journal's F10) |
| c981605d36019f0036693883e838207e3edf348d, d1e5df376a2c883263caa81f2e1a53ae7f864d99 (2026-10-31) | the owner chose that another session's two test-writing pilots take the shared port-4180 lane (the machine-wide lease that live runs take one at a time) before E2 continues; E2 was held 41 min 41 s (17:47:28 to 18:29:09), 31 min 21 s of it with nobody holding the lane, and resumed by itself; wall-clock time only, no build, bar or scoring changed | live runs from different sessions queue for one lane in the order the owner sets; M2a waits its turn behind E2 and E3 |
| bf68e9590a009e3087c7acfefa895d158d9b7034 (2026-10-31) | `ticket-sla`, the fourth link, built after E1 passed: a request that replaces an earlier rule, an acceptance of its own, a ledger that says whether the old rule was changed or left standing, and 11 hand-written variants graded; no live run (E3 waits for E2) | the nearest fixture for acting on a `decision` exists but measures nothing yet; M2b still lacks a case that starts from a real leftover |
| df44fd30d19455515cc2434dd21b18520e2a5f48 (2026-10-31) | a candidate for another change failed `shiploop-package-integrity`: it grew the skill card by 700 bytes to 30,655, which is 155 above the 30500-byte bound; the bound is kept, not raised | a build of this design has about 545 bytes for card text (section 8) |

## 7. Measurement plan

### M1. Replay with a second reader (offline, routine)

- Set: the strict rows of `peek.json` at the time, plus any finished runs under the experiment roots the peek skipped
  (`~/e2e-runs-xr`, `-s7`, `-pf`, `-multipass`); whether those roots hold runs that reached handoff has not been checked.
- Readers: the frozen first classification; a second, materially distinct model reader, blind to those labels, given the text
  and the class definitions of `classification.json` and the run's request sentences.
- Measures: agreement on the coarse classes, and on `gap` and `decision` in particular; every disagreement looked at by a third
  reader or the owner.
- Reading, fixed before the replay:
  - If a second reader finds a `gap` that a third look confirms the system could close alone, D2 has a real use. Record the run.
  - If no reader finds a `gap`, the only live class is `decision` (3 of 122 so far). Whether 2% to 3% of runs justify a field,
    an assembler and a SPEC clause is then the owner's call (D4); the recommendation is not to build until runs of the owner's
    own features show more.
  - If readers cannot agree on `decision` versus `extension` (rows 22 and 11 are the test), the class cannot be script-routed.
    Fall back to showing the non-note leftovers unclassified.
- Cost: model calls on a few dozen short texts. No ShipLoop run; the owner's live hold is respected.

### M2. Live measurements (need the owner's go)

Two different questions. The multipass work (section 5) bears on the first only.

M2a. Mechanics: does a run started from a script-built follow-on request plan like one started from a hand-written request?
The fixture and the readout exist. The chain harness (`chains.py`) starts link N+1 from link N's delivery and holds it to every
earlier link's checks; `delta.py` records whether the plan stayed on the delta; the ticket chain (assignment, escalation,
comments, and the modifying link sla) is a base. Build the follow-on request from the leftovers of a saved pass, start the next pass from it, and set it
beside the chain's hand-written delta prompt on the same base. Measures: the earlier checks still pass; the plan stays on the
delta (the multipass journal's F4: no planned test case cites a kept requirement); where the new knowledge lands, as the
ledger reads it. Write the predictions in the journal before the run, as the multipass Round 1 did, and score them from the
run's own files. It shares the machine-wide lease on port 4180 with other sessions' runs, which take it one at a time. E1 has
finished and supplies the hand-written third-pass baseline; E2 and then E3 take the lane next, so M2a queues behind them. The
multipass journal (Rounds 2 and 3) holds the live state; as of this revision's base it last records E2 running and E3 pending.

M2b. Value: does a follow-on run repair a delivery that is wrong? Still no case: every pass in the ticket chain passes (E1 included), and
XI's baseline failures were stalls. Calibrate a brownfield case whose first run completes and fails a held-out check, and in
which the run can know it did not verify the deciding fact (so the fact reaches `unverified` or `Open for the next run`).
Pre-register it: write the case, the arms and the pass rule down in a commit before any scored call. Add a stop-early rule as
XI had: three baseline runs first, and stop if all pass, because the comparison then cannot show a gain. The multipass plan's
modifying link, `ticket-sla` (a request that changes an earlier requirement; built and calibrated on hand-written variants, not
run live: bf68e959), is the nearest existing fixture for the `decision` class. It tests whether a pass changes the
requirement, the decision and the tests together. Its request is hand-written, so it does not test a request made from a real
leftover, and it supplies no delivery that is wrong.

- Arms (the two versions compared): A, ShipLoop as it is. B, the recommend-only list plus a harness that starts the follow-on
  run from the printed request when `recommend` holds.
- Measures, in the owner's order: held-out checks passing after the chain, then tokens, then minutes.
- It can only show value for gaps the run can name. A fact the run missed silently is outside what a reflection reaches; that
  is the research-probe line, which XI did not adopt.

### M3. Watch it on real runs (report only)

If D4 builds the recommend-only version, log the list on the owner's real runs without acting on it, and count how often a
recommended follow-on is started. This measures demand in the population the E2E corpus lacks.

## 8. Build sketch (only if D4 says build)

Touchpoints, by symbol; nothing here is designed in detail.

- `shiploop_stage_spec`: the `handoff` row (done-when and reads).
- `shiploop_prompts`: the handoff duty and its result template.
- A new module `shiploop_follow_on.py`, modelled on `shiploop_unverified`: the shape check, the source resolution, the request
  assembly and the HTML section. It reuses `shiploop_request` for sentences and `shiploop_knowledge_home` for the lessons
  subject (S-12: one implementation of each mechanism).
- `shiploop_navigator`: the check at `complete`, the done packet and `_status_next`, and `_render_report` (a section beside
  `_handoff_sections`).
- `shiploop_progress_data`, `shiploop_context_index`, and the references (glossary term, state-files, navigator row).
- Nomenclature (S-16): "follow-on" is not in the glossary. It is near "follow-up return" (a product fix committed after the
  workspace return) and "follow-on case" (an E2E case that follows another). The glossary entry must say which is which.
  "Improve" is a stage and a skill, so no name here uses it.
- E2E: a SPEC clause and a metric `follow_on` in `metrics.json` beside the `delta` block (unmeasured is not zero). The chain
  harness can start a link from the printed request. Its suites, `suite_catalog.py`, the `test-groups` counts and the SPEC
  table conflict whenever two sessions add to them, so expect to keep both sides.
- Tests: fail first, with the refusal's named exit submitted through the real CLI (not the wording); neutral fixtures (S-13).
- Cost to check: the handoff head's headroom against `test/shiploop_e2e/head_table.json` is unmeasured; the offline render diff
  decides.
- The skill card has a byte bound: `card_max_bytes` is 30500 in `test/fixtures/shiploop-card-ledger.json`, and
  `skills/shiploop/SKILL.md` is 29,955 bytes at this revision's base, so a build has about 545 bytes for card text. Earlier
  designs worked around the bound: one left the card untouched (`docs/shiploop-check-phases-bc-plan-2026-10-28.md`), another
  wrote only a short form of its text there (`docs/shiploop-owed-outcome-journal.md`), and a candidate for another change failed
  `shiploop-package-integrity` by exceeding it on 2026-10-31 (df44fd30). Put the follow-on duty in the packets and a reference
  file, not in the card.

## 9. Change admission, pre-check

The SPEC's change admission asks for an adversarial evaluation before a change is planned. Dispositions are proposals for
the build plan.

| Consequence | Scenario | Disposition |
|---|---|---|
| weakens a clause | S-14: a decision waits on a person | mitigated: it is an open item in the report; nothing prompts |
| weakens a clause | S-10: a chain with no exit | mitigated: exit by an empty `gap` list or a repeated `gap`; no count; no chain without D2 |
| weakens a clause | S-12: a second parser for requests or lessons | mitigated: reuse `shiploop_request` and `shiploop_knowledge_home` |
| other style, host, platform | the printed command breaks under a host's quoting | mitigated: command substitution of a file; test on each host's adapter |
| fails silently | the model files a real gap under `note` | accepted: same as today; M1's second reader measures it |
| passes tests, fails live | a list that validates but never recommends | open: M2 |
| model-written glue, dead ends | a malformed list refuses `complete` with no exit | mitigated: the refusal states the exit and a test submits it through the real CLI |
| enlarges packets | the handoff head grows | open: measure against `head_table.json` |
| leaks, touches user work | the request file quotes result text | mitigated: it is written under `RUN`, outside the repository, through the existing privacy screens |
| breaks saved runs, pins | a required key refuses a saved run at handoff | accepted: the stored shape is loose and the key is checked at the CLI gate only, as for `unverified`; no state version bump is expected |
| costs more than it saves | a second prelude for a 2% case | open: D4; M3 |
| gamed | the model classifies for effect (everything `note`, or `gap` to start runs) | mitigated: citations resolve; `gap` needs an S<n>; the full list is shown; no target metric on the count |
| compounds with the pass number | a chain of follow-on runs adds to the leaks the multipass journal measured (F1 to F3), and the one live third pass repeated them | open: recommend-only is no worse than a person-started pass; a chain waits for the result of the multipass fix's A/B test (E2) |

Anchor: S-14 (a step that needs a person records an open item) and S-11 (the next run builds on retained knowledge); the run
evidence is thin (3 decisions in 122 runs), which is why section 7 comes first. Non-regression: no outcome, stage, loop or
limit changes.

## 10. Decisions for the owner

| | Question | Recommendation |
|---|---|---|
| D1 | Shape: follow-on run, in-run back edge, or stay manual | a follow-on run; stay manual until M1 reports |
| D2 | Recommend-only, or auto-start a chain for `gap` entries | recommend-only; auto-start only after M2b shows a use and the multipass fix for what stages write has met its A/B test (E2) and been merged |
| D3 | A dollars or minutes ceiling on a chain | none proposed; yours if you want one, ending in a report |
| D4 | Build the recommend-only list now, or measure first | measure first (M1), then decide |

Decided here as routine and reversible: the term "follow-on"; the list lives in the handoff result; no new verb or option; the
start command uses command substitution of the request file.

## 11. Unknowns and rejected ideas

- U1. Whether the producing model classifies as a second reader would. M1 measures a second reader on saved text, not the
  producing model at handoff.
- U2. IN1 requires intake to cite every sentence of the request. A follow-on request that quotes the whole original would put
  those sentences under IN1. The draft passes the original by path, not by value; whether intake handles a quoted original
  is untested. The multipass cases pass a delta-only request and their runs planned only the delta (the live third pass too:
  0 kept IDs followed, 8 test cases citing no kept requirement), which favours the path.
- U3. The request file lives under `RUN`, outside the repository and next to the run's workspace; where a later session finds
  it after the run directory is cleaned is unspecified.
- U4. The host's stop hook releases at `done`; a chain needs the host to start the next run in the same turn or the driver to.
  Untested.
- U5. A `capability` entry can be closed only by a host that has the capability. The script cannot know the next host.
- U6. The line between `gap` and `extension` is the one the owner's phrase "which we have now understood and learned" draws:
  a gap cites a request sentence or a refuted assumption; an extension adds scope. No real gap exists in the archive to test it.
- U7. Substantial features that "haven't concluded" are not in the archive (the corpus is small and every completed run already passes, and the only two
  runs of the owner's own features were unfinished).
- U8. Whether `release-verify`, whose lessons are written before `operations`, or `handoff` is the better owner of the list.
  The handoff was chosen because it restates and sees operations.
- U9. Chains past three passes. One third pass has run (multipass E1): it passed and kept every earlier requirement, and the
  permanent-file leaks recurred. A fourth pass has not run. Whether the leaks grow faster than the pass number is not settled:
  the third pass's growth was inside the second passes' range in bytes and one heading above it in count. One run, one lineage.
- U10. A `decision` that changes an earlier requirement is the multipass plan's modifying link, `ticket-sla` (built and
  calibrated on hand-written variants, not run live; its E3 waits for E2). How a pass retires or supersedes an earlier entry in
  the living files is untested on a model, and a follow-on run acting on such a decision depends on it. The failure seen live
  is the reverse: a new decision filed under `## Superseded` and so born retired (E1).

Rejected: a size threshold (a number nobody can know, and big is not unfinished); asking the user at the end (S-14); a
reflection stage with an Improve-style loop (no checkable exit); gating `done` on the list (honest runs would be refused);
reusing the research-probe candidate (XI, not adopted).
