---
Status: design, revision 6, 2026-11-01. The recommend-only list of section 4 is built, on the owner's instruction (D4), and had a live check
(journal Round 5, four Codex runs). As of the commit that holds this revision it is on a branch and not on origin/main, and nothing is released;
the release that ships `changes/shiploop/follow-on-list.md` is the commit to look for. The auto-start chain (4.7) is not built. Execute: ask. Revision 2 folded in
the multipass work that landed after revision 1 and corrected one stale claim (section 6, the 589bc03e row). Revision 3
brought up to date the multipass facts that moved after revision 2 (a live result, an owner decision, a built test case).
Revision 4 folds in the two results that landed after revision 3's base: the A/B test of the multipass fix (E2) met its bar,
and the first live fourth pass (E3) ran. It changes no recommendation. Anything that moves (a queued run, a pending result)
is written "as of" a commit and points at the journal that keeps the live state; revision 3 did that for the headline of a
passage and not for every sentence, and revision 4 does it for each sentence that states one (journal F25). Revision 5 folds in the M1 replay (section 7): three other
readers, blind to the first reader's labels, classified the same rows plus seven new ones. It also moves the multipass facts to
3d5732d0, where the multipass work fixed its fourth experiment (E4) before any run. The replay applies this note's own reading
rule, so D1 to D4 keep their recommendations, now settled where they waited for M1. Revision 6 records what happened next: the owner answered
the D4 question with "Rebase, Merge to main and publish, implement improvements" (2026-11-01), which I read as D4 = build, and the
recommend-only list was built and run live. The replay's advice to wait stands as evidence about demand, not as a rule that was kept.
Consumer: the owner, who settled D4 by asking for the build and still decides D2 and D3 (section 10). Later: the session that builds the chain (4.7), or measures the list
on the owner's own features (sections 7 and 8), or reruns the peek and the replay then.
Journal: docs/shiploop-follow-on-run-journal.md (Rounds 0 to 5).
Evidence: docs/experiments/follow-on-peek-20261031/README.md, docs/experiments/follow-on-replay-20261101/README.md and
docs/experiments/follow-on-build-20261101/README.md.
Category: a generic ShipLoop improvement (built in revision 6) and the evidence behind it. No E2E apparatus change; the skill change is the feature
commit 826c951ccfdecb8f48e406f8fbdacb6a69daabbc; the release is made by `scripts/release.py` after this revision.
Base: 726ef7184a3a2da212b614111af023f64b94b1ff (origin/main when revision 6 was written, merged into the build branch at f1a5868da64587610d6711105650caacb2d557fc). Revision 5
(published as 46f3ac32b65ff2bb2a0ba4425d3445fef0aa642b) was written at 3d5732d017899a6d486b3249915284793af19d3a. Revision 4 (published as
e81fdb55d58bdb0bcc8c1643d93d5973709100e4) was written at e13af240100c066489e83c028d97339845402b55,
revision 3 (published as 7bb1c35683a18d37bd800df12a2f4c45c32ecc77) at df44fd30d19455515cc2434dd21b18520e2a5f48, revision 2 (published as
671873bce787d9e9c25bbbe8ab64e7c7f7061db0) at 240594c9922c42ac0a761717671f93f220e31743 and revision 1 (published as
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

- Built (revision 6; as of the commit that holds it, on a branch and not yet on origin/main): the recommend-only list of option B, on the owner's
  instruction of 2026-11-01. The handoff's done result carries `follow_on`; the script checks the shape and the citations, writes
  `RUN/follow-on-request.md` for a `gap` or a `decision` and prints the start command, and starts nothing and never blocks `done`. Four live Codex runs
  (journal Round 5) all passed, every handoff was accepted on its first try, and the lists held two notes and two empties: the mechanics hold and
  the list had nothing to recommend. The replay's evidence about demand is unchanged.
- ShipLoop already writes the reflection and already has two loop-backs. What it lacks is the decision that turns the
  reflection into a run, or into a question for the owner.
- Shape (D1): a follow-on run, which is a new run on the delivered baseline, not an in-run back edge to spec or plan.
- Mechanism (D2, D4): a follow-on list in the handoff result, which is the run's leftovers classified once, each entry citing
  a record. The script checks the citations and routes. The first version recommends only: it prints a ready follow-on
  request and the start command, never starts a run, and never blocks `done`.
- Evidence so far (exploratory, section 5): of 122 archived runs that reached handoff, 3 name a decision a person must make
  about the spec or scope, and none leaves a gap the system could close alone. The outcome for a gap a run notices in-run,
  `add-work`, was used in 3 of 125 runs. A replay with three other readers (revision 5, section 5) reproduced the classes on 28
  of 32 rows and confirmed no gap; among 166 finished runs it leaves two decisions by majority (1.2%), three by the first reader
  (1.8%).
- Revisions 2 to 5: the multipass work of another session, which landed on main after revision 1. It measures a pass started by
  a person on the repository an earlier run left (a pass is one such run). Its findings support the shape: all 8 saved runs of
  four ticket pairs passed, the 4 second passes kept every earlier requirement and decision, the first live third pass (its E1)
  passed and kept the earlier requirements too, and the first live fourth pass (its E3) delivered what it was asked. It supplies
  the chain harness and the readout for the live measurement (section 7). It also shows every pass leaking activity into the
  permanent files, the third and fourth passes included. The owner approved that work's fix. Its A/B test (E2) met the bar
  written before the first run: 12 of 12 runs passed, and the fix added no stray heading to `environment.md` in six passes
  against 2 to 8 in the control, at no measurable cost. As of 3d5732d0 the fix is not on main: it waits for a quiet-machine tier
  run, a merge and the owner's word on the release. It was tried on passes 1 and 2 only, while both unfixed later passes (E1, E3),
  which continue the one lineage whose second pass made the mislabel, filed their new decision behind it. A fourth experiment (E4:
  the fix on passes 3 and 4, in six runs, each beside a run without the fix on the same prior) was fixed on 2026-11-01 before any run,
  cites this note's U9 as its open question, and had not started. So a chain of follow-on runs still waits for the fix's release,
  and whether it should also wait for E4's result is open (section 4.7).
- Order: the recommend-only list is built and was checked live (revision 6); the replay (revision 5) had advised waiting for runs of the owner's own features,
  and the owner asked for the build. The next measurements are the list on the owner's own features (M3) and a recommended run started from a
  model-written request (M2a); the peek and the replay rerun in minutes. Consider chaining runs only with new evidence, the multipass fix's release
  and the owner's calls on D2 and D3.

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
| Chains of passes (test apparatus) | `test/shiploop_e2e/chains.py`, `delta.py`, the cases `ticket-comments` and `ticket-sla`, and the [multipass plan](shiploop-multipass-plan-2026-10-31.md) and [journal](shiploop-multipass-journal.md). A link is one case that follows another; the delta ledger is a record kept beside each run of what it changed compared with the run before | eight saved runs (four pairs, a first and a second pass each) read: all passed, and the four second passes kept everything (03d046c6); a no-model probe shows the lessons reach a third pass's first packet (aa601d37); the first live third pass passed and kept every earlier requirement (c55d0bc0); the fourth link, a request that replaces an earlier rule, was built and calibrated on hand-written variants (bf68e959) and ran live once, with the right delivery and two wrong words in its case, since fixed (a232cf03, 9d5067f3); a fix for the leaks met its A/B test and, as of 3d5732d0, is not on main (6a6badb3) | started by a person; nothing starts a pass from a run's leftovers; every pass leaks activity into the permanent files, the third and fourth passes included |
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
    were kept byte for byte, no earlier test was touched and 8 planned test cases cite no kept requirement (c55d0bc0). The
    first live fourth pass (E3), whose request replaces an earlier rule, delivered it: all 16 hidden checks passed, all 8
    requirement IDs were kept and the old requirement was changed in place. It is recorded FAILED on one check of the new case
    that was itself wrong, and passes with the check corrected (a232cf03). A request that is the delta alone is what those
    cases use (03d046c6).
  - The request is new, so intake, spec, plan and tests anchor to it. The owner's rule that a step's tests follow that step's
    own intention (fdec0f6e) holds unchanged.
  - `done` keeps its meaning: the request was delivered. Authority is asked again. No new edge type.
- Against:
  - A second prelude (discovery, the baseline test run, research, spec, plan) is paid again for even a small delta.
  - The lessons must reach the new run. They do by subject (`last_lessons`), not by position in the last three commits: one
    more closing commit once pushed them out of the window (49c502ea, K13). A no-model probe of four saved second passes
    confirmed the lessons are quoted correctly in a third pass's first packet (aa601d37).
  - Each pass leaks activity into the permanent files (multipass journal F1 to F3). `environment.md` gained 4.5 to 6.4 KiB in
    the second pass, mostly stage reports under headings of their own (32 of 36 stray headings; 4 are the release procedure the
    consumer contract intends). In one of four runs a live decision was filed under `## Superseded`, and the engine then labels
    it superseded. The first live third pass (E1) repeated both: `environment.md` gained 8 stray headings (+6.0 KiB, 10,531 to
    16,637 bytes), and its new decision AD-4 was filed after `## Superseded`, below the earlier pass's still-mislabelled AD-3,
    so it was born retired (c55d0bc0). The first live fourth pass (E3, published ShipLoop, no fix) repeated both again: 9 stray
    headings (+6.4 KiB, 16,637 to 23,175 bytes) and its new decision AD-5 filed under `## Superseded`, behind AD-3 and AD-4
    (a232cf03). The bytes added per pass stay in one band (second passes 4.5 to 6.4 KiB, third 6.0, fourth 6.4), and the
    stray-heading count has not grown steadily (second passes 7, 1, 6 and 4; the control's passes in E2 7, 7, 2, 6, 5 and 8;
    third 8; fourth 9, the highest seen; one run each). What builds up is the mislabel. One of the four saved second passes made
    it (AD-3, filed under `## Superseded`), none of E2's six control passes did, and both later passes (E1, E3) continued that
    lineage and filed their new decision behind it (exploratory: n=2, one lineage). It needs a `## Superseded` section at the
    end of the file, so once a pass has made the mislabel every later pass in the lineage is exposed to it. The multipass
    journal reads E3 as the mislabel compounding with the pass number; both passes continue one lineage, so the evidence shows
    it persisting once made and not yet that it appears more often with the pass number. A packet lists at most 40 headings of a
    file, and the fourth pass's `environment.md` holds exactly 40 (counted over the saved file by a short script, all levels,
    fenced code skipped), so the fifth pass is the first whose packets cut the newest sections (as of 3d5732d0 the fifth pass
    has not run). A chain of follow-on runs repeats this at machine speed; one follow-on run is no worse than the person-started
    second pass it replaces.
  - A fix for the leaks exists and was tried on passes 1 and 2 only. In its A/B test (E2) it added no stray heading to
    `environment.md` in six passes against 2 to 8 in the control, and its notice caught the mislabel once live, in a file whose
    last section was `Superseded` (6a6badb3). Whether it holds from a prior that already carries the mislabel, as a chain's
    later passes would, is not measured; and it is a bundle whose parts were not separated. E4 (fixed 2026-11-01, not started as
    of 3d5732d0) tests exactly that, with a run without the fix beside each fix run.
- Verdict: yes for one follow-on run; a chain waits for the multipass fix, which has met its A/B test, is not on main as of 3d5732d0
  and was tried on passes 1 and 2 only, with a test on passes 3 and 4 fixed and not started (section 4.7).

### C. Stay manual (today)

- For: no engineering; the archive shows 2 to 3 decisions in 166 finished runs (the replay, section 5); the report already
  prints the lessons and the open items (8d51a8e9).
- Against: the decision sits as free text inside a commit body (and, after a working-tree return, not on the branch at all);
  nothing classifies it, cites a record for it, or builds the request; the owner asked for the activity.
- Verdict: the baseline the list is measured against. It was the right answer until runs of the owner's own features show more, by the replay (section 7, done);
  the owner asked for the list anyway (revision 6). The replay
  found no gap and two decisions in 166 finished runs.

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

### 4.2 An entry (the shape fixed at build, revision 6)

Five texts, all required (`request_sentence` may be empty except for a `gap`). An entry drawn from a real leftover (row 8 of the peek, a
csv-report run):

```json
{"class": "decision",
 "statement": "Whether exponent notation and a leading + count as numeric, and whether zero arguments exit 1.",
 "source": "lessons.open_next", "request_sentence": "",
 "needs": "the requester's answer"}
```

A constructed `gap`, for contrast (the archive has none):

```json
{"class": "gap",
 "statement": "The delivered CLI exits 0 on an unreadable file although S2 asks for exit 1.",
 "source": "unverified:R-2", "request_sentence": "S2",
 "needs": "a work item that makes the exit code match"}
```

Two fields of the draft were not built: `id` (a number nobody needs: the report numbers the rows and a repeated gap is matched by source and
statement) and a per-entry `evidence_refs` (the script resolves the cited record from `source`, so a model cannot cite one it did not read).
A `source` is one of five kinds, each resolved against the run: `unverified:R-<n>` (a row of the unverified list), `assumption:<id>`,
`lessons.<learned|considerations|open_next>`, `result:<stage>` (a stage with an accepted done result; added at build, because the handoff
sees what product-acceptance and operations learned, which the lessons commit written at release-verify cannot hold) and `commit:<hash>`
(Git decides, through `shiploop_git.resolve_commit`; reachable from HEAD of the execution checkout).

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
- `source` resolves to a record in the run: one of the five kinds of 4.2 (an unverified row, an assumption id, a lessons field, a stage's accepted
  done result, or a commit Git resolves). A hash typed by the model is never trusted.
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
would add one. A third and a fourth pass have run (E1, E3) and nothing retained was lost, so function is not what holds a chain
back; the leak is. The owner approved the multipass fix for what stages write to the living files (its D2 to D4, 15ef676f). It
is built as a candidate on another session's local branch (`feat/multipass-placement-725e1a`) and stays off main until it is
released. Its A/B test (E2) met the bar fixed before the first run: 12 of 12 runs passed and the five items of the bar held, one
of them untested because the control never filed an entry as retired in six passes (6a6badb3). The multipass plan on main says,
as of 3d5732d0, that the candidate was rebased onto the 3.9-floor release and waits for a quiet-machine tier run, a merge and
the owner's word on the release; the branch, as read for this revision, holds the candidate rebased onto that plan commit, with
its E2 round entry. What E2 does not show matters for a chain, which reaches the later passes by construction. The fix was tried
on passes 1 and 2 only. The multipass work's own replay found that both entries filed as retired when new (AD-3, AD-4) were
written by the plan stage, which the candidate's packet line does not reach (c55d0bc0); in E2 the notice caught that mislabel
once, in the packet of a stage after `plan`; and E3, which ran without the fix on a prior that already carried the mislabel,
filed its new decision behind it (a232cf03), so what the fix does from such a prior is not measured. So a chain waits for the
release of the fix. Whether it should also wait for the fix to be seen past the second pass is what the multipass work's fourth
experiment (E4) asks: six runs on passes 3 and 4 in three matched pairs, each fix run beside a run without the fix on the same
prior, with the bar (B1 to B4), the control (K) and the predictions fixed on 2026-11-01 before any run; as of 3d5732d0 it had
not started. Its reading rule names the case this note's lineage reading predicts: if the run without the fix does not leak on a
tidy prior, the mislabel reads as bound to a seeded lineage (U9). The multipass journal (Rounds 2 to 4) holds the live state.

### 4.8 How it sits with the rest

| Existing part | Relation |
|---|---|
| Improve | unchanged. It verifies this run; the follow-on validates the request against what building and shipping taught |
| `add-work` | unchanged. It closes in-run what the run notices; the list holds what remains, so `gap` should be rare (section 5) |
| `send-back`, reconcile | unchanged |
| `unverified`, `open_items`, lessons | their rows are the `source` of entries; none is replaced |
| the lessons commit | unchanged; still the pull path, now with a ready request beside it |

## 5. Evidence so far (exploratory)

Full method, the 25 rows and the limits: [the peek](experiments/follow-on-peek-20261031/README.md). The classification is by one
reader, Claude Sonnet 5.5, and was replayed by three other readers (the last subsection below); E2E cases only; no ShipLoop run.

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

### The replay with other readers (revision 5)

M1 of section 7, run on 2026-11-01: [the replay](experiments/follow-on-replay-20261101/README.md) and journal Round 4, whose
plan, rules and five predictions were committed before any reader was called. The rows are the 25 above plus 7 from runs
finished since (44 more runs, so 166 finished runs now). The readers, blind to the first reader's labels, are Sol (GPT-6.1 Sol,
xhigh) twice, the second time with the class definitions in reverse order, and Grok (grok-4.7, no tools) once.

- All four readers give the same class to 28 of the 32 rows. The first reader agrees with Sol's main run on 28 rows (30 on the
  five coarse groups, kappa 0.91), with Sol's retest on 28 (28) and with Grok on 30 (30); the three others agree with one
  another on 30 to 32.
- No gap is confirmed. Sol's retest called two rows gap (F01, N1); Grok did not, and each of those runs records a person as the
  owner of the open item and no authenticated browser as the reason. The line between person, capability and gap moved with the
  order of the definitions.
- `decision` is the only live class: F08 (csv-report numeric forms) and F22 (the delivery route of `ticket.assigned`) for all
  four readers; F23 is `person` for the three others. By majority 2 of 166 finished runs (1.2%); the first reader alone 3
  (1.8%); the snapshot 3 of 122 (2.5%).
- The classes are softest where one text mixes items of different classes (F18, F23); the follow-on list would classify entries,
  not texts (U11).
- Every reader had the first reader's definitions, none of the 32 rows comes from the owner's own features, and the new rows are
  correlated.

### What the multipass work adds (revisions 2 to 6)

Read in full after rebasing: its [plan](shiploop-multipass-plan-2026-10-31.md), its [journal](shiploop-multipass-journal.md) and
commits 03d046c6, aa601d37, 84b6bdd2, 1bdeac40 and 737640ca; revision 3 read 15ef676f, c55d0bc0, c981605d, d1e5df37 and bf68e959
the same way, revision 4 read 6a6badb3, 9d5067f3 and a232cf03, and revision 5 read 3d5732d0 (full hashes in section 6). A pass
is one run on the repository an earlier run left; a link is one test case that follows another; the delta ledger is a record
kept beside each run of what it changed compared with the run before; E1, E2 and E3 are the multipass journal's names for its
first live third pass, its A/B test of the fix for the leaks, and the live run of the fourth link. Most of it read eight saved
runs and called no model; E1, E2 (twelve runs) and E3 are its live runs.

Update, as of d71eaa7198772501b189dff76308d4ee7ac533cb (added to revision 6 before it was committed): the multipass work's E4 reported while this revision was being finished (its journal,
"Result of Round 4"; six runs in three matched pairs, one run per cell, on a machine at load 30 to over 100). With the fix no later pass filed its new decision
under `## Superseded` (0 of 3); the old ShipLoop did in 4 of 5 later passes, and stray headings fell from 8, 1, 0 to 2, 0, 0. Its bar B1 is recorded missed (one
delivery failed one base test once, which it reads as a port collision, the environment) and B2 to B4 held. It reads the data as a per-run chance, high on these
chains, and not as a rule tied to the pass number or the file's shape: R4b0 had a clean prior and still mislabelled, so this note's lineage reading (the mislabel
persists once made) is not needed, and a prior that carries the mislabel did not force it (R4c0). The candidate is still not on main as of that commit and releasing it
stays the owner's word, so D2's condition is unchanged: a chain waits for the fix's release. Cost is not shown to be nil (model calls 1.53 times in the pass-4 pair, one
run per cell). Every statement below that says E4 had not started, or that U9 stays open for lack of it, is as of 3d5732d0 and is superseded by this paragraph; U9's
own question (bound to a lineage, or growing with the pass number) now reads: neither pre-registered reading holds alone (E4, exploratory).

- A second pass works: all 8 saved runs (four pairs) passed, and in the 4 second passes R-1 to R-5 were kept byte for byte, no
  earlier test was touched, and 0 of 19 planned test cases cite a requirement the run did not add. This is the best evidence for shape B.
- The lessons reach a third pass: a no-model probe of four saved second passes shows the last three commit messages and the
  newest lessons commit quoted in full in the third pass's first packet.
- A third pass works too. The first live third pass (E1: `ticket-comments` continuing from a saved second pass, ShipLoop
  1.26.0, Codex gpt-6.1-terra at xhigh) passed 13 of 13 checks and 14 of 14 inherited hidden checks, kept R-1 to R-7 byte
  for byte, added R-8 and AD-4, touched no earlier test and planned 8 test cases that cite no kept requirement. Planning did
  not grow: 302 s, against 322 s and 328 s for the two earlier passes of that lineage. Of the six predictions written before
  the run, three held, two missed in the good direction and one missed on a single clause (c55d0bc0). One run, one lineage.
- Passes leak into the permanent files, and the third and fourth passes repeated both leaks (section 3.B): 8 and 9 stray
  headings and +6.0 and +6.4 KiB in `environment.md`, and a new decision born retired under `## Superseded` in both.
- A fix for the leaks works on the passes it was tried on. The A/B test (E2: three chains of two passes on the base and three on
  the candidate, Codex gpt-6.1-terra at xhigh) passed 12 of 12 runs and met its bar: stray headings added to `environment.md` 0
  in six fix passes and 7, 7, 2, 6, 5 and 8 in six control passes; a pass that added a decision changed a live section of
  `architecture.md` in 6 of 6 fix passes against 3 of 6; second-pass time 1.02 times the control's; tokens 49.1 M a run against
  49.0 M (6a6badb3). Its limits: three chains per arm, one pair of cases, passes 1 and 2 only, a bundle whose parts were not
  separated, and the item that no entry is filed as retired when new held without being tested. As of 3d5732d0 the fix is not on
  main, and a test of it on passes 3 and 4 (E4) is fixed and not started (section 4.7).
- A fourth pass works too, and a link that changes a rule changed it. The fourth link, `ticket-sla`, asks a pass to replace an
  earlier rule ("a ticket is escalated at most once" becomes "at most twice, and by priority") and to change the requirement,
  the decision behind it and the tests that state it together. It was built with an acceptance of its own and a ledger that
  says whether the old requirement and decision were changed or left standing; its 11 hand-written variants (a base, a
  reference, an alternative and eight defects) each failed exactly the checks that read what they break (bf68e959). Its first
  live run (E3: published ShipLoop, continuing from E1's output, Codex gpt-6.1-terra at xhigh, 993 s, 37.0 M tokens)
  delivered the right thing: all 16 hidden checks passed, requirement R-7 was changed in place, all 8 IDs were kept and one
  earlier test file was modified. It is recorded FAILED on 15 of 16 checks because one check of the new case was wrong: it
  looked for a word copied from the previous link, which the prior spec already contained, so the in-place route could not
  pass; with the check corrected after the result was seen it passes (a232cf03, 9d5067f3). A second wrong word, in the
  ledger's pattern for the old rule, was fixed the same way. The calibration had missed the first because its synthetic
  delivery added a requirement, taking the other of the two routes through the check, and the second because the pattern was
  written from the request and not from a real prior. Whether a run retires or supersedes the old decision is not shown: AD-3
  was already filed under `Superseded` when E3 began (the mislabel E1 had inherited), so leaving it standing looks the same
  either way. The request is
  hand-written, and none of the peek's three `decision` rows concerns how often a ticket is escalated.
- The ticket chain is at its ceiling too: every pass in it passes (E1 and E3 included, E3 once its check was corrected), so it
  can show the mechanics of a follow-on run, not its value (section 7, M2a and M2b).

## 6. Earlier decisions this design respects

Read in full before writing; hashes resolved with `git log -1 --format=%H`. Revision 2 corrected the `19c25538` row and added
the rows from `589bc03e` on. Revision 3 added the rows from `15ef676f` on. Revision 4 added the rows from `6a6badb3` on and
brought the `15ef676f`, `c981605d` and `bf68e959` rows up to date. Revision 5 added the row for `3d5732d0` and moved the as-of labels to it. Revision 6 added the rows for `b3a8e3f1` and `d84d30a9` (the unverified list) and `85b788ea`.

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
| 15ef676f7b20a95d60c8047b0a3fcdac82cb1d3f (2026-10-31) | the owner's "Approve all" to D1 to D5 of the multipass plan; the leak fix (its D2 to D4) is built as one candidate, kept off main and merged only when its A/B test (E2) meets a bar written before the first run; E2 runs three chains on the base and three on the candidate | the fix was decided, then measured (E2 met the bar, 6a6badb3); unaccepted candidate code stays off main (AGENTS.md, Decisions, 2026-10-30), so as of 3d5732d0 a chain waits for the fix's release |
| c55d0bc0ad21a2c477d024067378d0c3b1241959 (2026-10-31) | E1, the first live third pass: 13 of 13 checks and 14 of 14 hidden checks passed, R-1 to R-7 kept, both leaks repeated (8 stray headings, +6.0 KiB, AD-4 born retired); an offline replay found that the candidate's packet line does not reach the plan stage, which wrote both entries filed as retired when new | a third pass works and leaks again; the candidate may not stop the born-retired entry alone (the multipass journal's F10) |
| c981605d36019f0036693883e838207e3edf348d, d1e5df376a2c883263caa81f2e1a53ae7f864d99 (2026-10-31) | the owner chose that another session's two test-writing pilots take the shared port-4180 lane (the machine-wide lease that live runs take one at a time) before E2 continues; E2 was held 41 min 41 s (17:47:28 to 18:29:09), 31 min 21 s of it with nobody holding the lane, and resumed by itself; wall-clock time only, no build, bar or scoring changed | live runs from different sessions queue for one lane in the order the owner sets; E2 and E3 have since ended (6a6badb3, a232cf03), and M2a takes its turn behind whatever the owner orders next |
| bf68e9590a009e3087c7acfefa895d158d9b7034 (2026-10-31) | `ticket-sla`, the fourth link, built after E1 passed: a request that replaces an earlier rule, an acceptance of its own, a ledger that says whether the old rule was changed or left standing, and 11 hand-written variants graded; its first live run is E3 (a232cf03) | the nearest fixture for acting on a `decision`; it ran once and shows mechanics, not value; M2b still lacks a case that starts from a real leftover |
| df44fd30d19455515cc2434dd21b18520e2a5f48 (2026-10-31) | a candidate for another change failed `shiploop-package-integrity`: it grew the skill card by 700 bytes to 30,655, which is 155 above the 30500-byte bound; the bound is kept, not raised | a build of this design had about 545 bytes for card text then and has about 489 as of 3d5732d0 (section 8) |
| 6a6badb3e6b8bd858015817c40ee216addf76ba6 (2026-10-31) | E2, the A/B test of the multipass fix: 12 of 12 runs passed and the bar written before the first run held; stray headings added to `environment.md` 0 in six fix passes against 2 to 8 in the control; second-pass time 1.02 times, tokens 49.1 M against 49.0 M; the notice caught the mislabel once live; the fix was tried on passes 1 and 2 only, is a bundle, and the item that no entry is filed as retired when new held untested; the candidate stays on a local branch and the release is the owner's call | a fix for the leaks exists and works where it was tried, so as of 3d5732d0 a chain waits for its release and not for a measurement; the passes it was not tried on are the ones a chain reaches (U9) |
| 9d5067f3d6b38ff0231e3e98835d78fb96e5a37a (2026-10-31) | `ticket-sla`'s first live run was recorded FAILED on a retention word copied from the previous link, and its ledger pattern for the old rule came from the request and not from a real prior pass; the calibration had exercised one of two routes through the check; both fixed, with three tests that fail on the old file | a case's checks are written from a real prior pass and tried on each route; a case built for M2b must be (section 7) |
| a232cf038789b532c8485c7583136177cb6be929 (2026-10-31) | E3, the first live fourth pass, on published ShipLoop with no fix: the delivery was right (16 of 16 hidden checks, R-7 changed in place, 8 IDs kept), recorded FAILED on the wrong check and passing with it corrected; 9 stray headings; AD-5 born retired behind AD-3 and AD-4, already under `Superseded` | the mislabel persists once a lineage has it (n=2, one lineage, exploratory); whether a pass retires the old decision needs a prior without the mislabel; `ticket-sla` supplies mechanics, not value |
| b3a8e3f10e1f43238a2c86700eb6faf3611d2d75 and d84d30a977aa584ecc748fb34982f2bd7add21df (2026-10-08, 2026-10-26) | the `unverified` list: a result key the script gates at the CLI only, stores loose, prints and puts in the report; a later stage restates it, and a fixture without the key is refused | the follow-on list copies the pattern (revision 6); seven suites had to carry `follow_on: []` |
| 85b788eaed0fd575791c4ce31e585f811517be6c (2026-10-26) | a refusal at the handoff named a later stage that cannot exist | the follow-on refusals name only exits that exist (replace the row, or `[]`); each named exit has a test through the real CLI |
| 3d5732d017899a6d486b3249915284793af19d3a (2026-11-01) | E4 fixed before any run: the multipass fix on passes 3 and 4, six runs in three matched pairs (a seeded prior, a tidy prior that ends with `Superseded`, and a pass-4 `ticket-sla` from the tidy one), each fix run beside a run without the fix on the same prior; bar B1 to B4, control K and predictions P1 to P8 written first; it names this note's lineage reading and U9 as its question; not started | U9's question has a pre-registered test: a chain waits for the release, and the owner may want E4's result before deciding D2; E4's reading rule says what each outcome means for the lineage reading |

## 7. Measurement plan

### M1. Replay with a second reader (offline; done 2026-11-01, revision 5)

- Set: the strict rows of `peek.json` at the time, plus any finished runs under the experiment roots the peek skipped
  (`~/e2e-runs-xr`, `-s7`, `-pf`, `-multipass`); checked 2026-11-01: `-xr` holds 17 runs that reached handoff, `-multipass` 14
  and `-pf` 6, `-s7` none; the 7 new rows come from those roots, `-hostonly` and `~/e2e-runs`.
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
- Result (2026-11-01; [the replay](experiments/follow-on-replay-20261101/README.md), journal Round 4; the rules and five
  predictions were committed before any reader was called): 32 rows (the 25 and 7 new); readers Sol twice (the second time with
  the classes in reverse order) and Grok once, all blind to the first reader's labels. All four label 28 of 32 rows alike. No
  gap is confirmed (Sol's retest called two rows gap, Grok did not and each run's own record names a person as owner), so the
  second rule applies: `decision` is the only live class, 2 rows by majority (F08, F22) and 3 by the first reader, out of 166
  finished runs (1.2% to 1.8%), and the recommendation stays not to build until runs of the owner's own features show more. The
  third rule is met by one row: Jaccard 2/3 on the decision rows (F23 is `person` for the three other readers); the test rows
  F22 and F11 agree across all four.

### M2. Live measurements (need the owner's go)

Two different questions. The multipass work (section 5) bears on the first only.

M2a. Mechanics: does a run started from a script-built follow-on request plan like one started from a hand-written request? The
fixture and the readout exist. The chain harness (`chains.py`) starts link N+1 from link N's delivery and holds it to every
earlier link's checks; `delta.py` records whether the plan stayed on the delta; the ticket chain (assignment, escalation,
comments, and the modifying link sla) is a base. Build the follow-on request from the leftovers of a saved pass, start the next
pass from it, and set it beside the chain's hand-written delta prompt on the same base. Measures: the earlier checks still pass;
the plan stays on the delta (the multipass journal's F4: no planned test case cites a kept requirement); where the new knowledge
lands, as the ledger reads it. Write the predictions in the journal before the run, as the multipass Round 1 did, and score them
from the run's own files. It shares the machine-wide lease on port 4180 with other sessions' runs, which take it one at a time.
E1, E2 and E3 have finished (E1 supplies the hand-written third-pass baseline, E3 the fourth). As of 3d5732d0 the multipass plan
has E4 (six runs, about 1 h 45 min of Terra, one at a time on the lane) fixed and not started, then a second chain on a smaller
base, so M2a queues behind them or behind whatever the owner orders next. The multipass journal (Rounds 2 to 4) holds the live
state.

M2b. Value: does a follow-on run repair a delivery that is wrong? Still no case: every pass in the ticket chain passes (E1 and
E3 included), and XI's baseline failures were stalls. Calibrate a brownfield case whose first run completes and fails a held-out
check, and in which the run can know it did not verify the deciding fact (so the fact reaches `unverified` or `Open for the next
run`). Pre-register it: write the case, the arms and the pass rule down in a commit before any scored call. Add a stop-early
rule as XI had: three baseline runs first, and stop if all pass, because the comparison then cannot show a gain. The multipass
plan's modifying link, `ticket-sla` (a request that changes an earlier requirement; built and calibrated on hand-written
variants: bf68e959; run live once, E3: a232cf03), is the nearest existing fixture for the `decision` class. It tests whether a
pass changes the requirement, the decision and the tests together. E3 showed the requirement and a test file changed in place,
and could not show the decision, because the prior already had it mislabelled. Its request is hand-written, so it does not test
a request made from a real leftover, and it supplies no delivery that is wrong. Any case built for M2b should take the lesson of
its first live run: write each check from a real prior pass, and try it on the in-place route as well as the new-ID route (two
wrong words in a case that had passed its calibration, 9d5067f3).

- Arms (the two versions compared): A, ShipLoop as it is. B, the recommend-only list plus a harness that starts the follow-on
  run from the printed request when `recommend` holds.
- Measures, in the owner's order: held-out checks passing after the chain, then tokens, then minutes.
- It can only show value for gaps the run can name. A fact the run missed silently is outside what a reflection reaches; that
  is the research-probe line, which XI did not adopt.

### M3. Watch it on real runs (report only)

D4 built the recommend-only version (revision 6): log the list on the owner's real runs without acting on it, and count how often a
recommended follow-on is started. This measures demand in the population the E2E corpus lacks.

## 8. The build (revision 6), and the sketch it followed

Built on the owner's instruction of 2026-11-01 (D4; journal Round 5). The commits, with the branch `feat/follow-on-list-4f85f3` merged with origin/main at
f1a5868da64587610d6711105650caacb2d557fc: the feature 826c951ccfdecb8f48e406f8fbdacb6a69daabbc (the module, its wiring, 14 hermetic tests written first), the plan of the live round
2da2d4f3d11b0f468c14ff48e6158a7bb334e8ee, the fix ba3297d707329a6500ac036577d3f211b2e6a352 (a missing workspace record), the test-only commit 12d293a83ab2c05d30bb575b3d0c5989604a3601, the evidence
7c2ce6cb9345959292c38688106a4c8d16be865c and the LEARNINGS entry c593e8f27d65d7157438d9b14c2dd7c09f3bbc89. Not built: the auto-start chain (4.7), the E2E SPEC clause and the
`follow_on` metric, an export of the list to the Run Review page, and any change to the skill card (the feature left SKILL.md alone: 30,011 bytes of 30500 when it was written, 30,115 after another session's release 2.29.0).
As of the commit that holds this revision none of these commits is on origin/main. What the build found beyond the sketch: seven suites hand-build a
handoff result and had to carry `follow_on: []` (callback-contract's helper, handoff, full-runtime, navigator-v4; found only by the quick tier, actual-improve-cli; found only by a
sweep of the rest of the family, because the tier selects by changed files, workspace and return-review), the same effect the unverified restate had on a fixture (d84d30a977aa584ecc748fb34982f2bd7add21df); and a path that read an
isolated run's workspace record caught the wrong error class, found by a test written for a gap the feature commit listed.

The sketch, kept as the record of what was planned (touchpoints by symbol):

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
  `skills/shiploop/SKILL.md` is 30,011 bytes as of 3d5732d0 (it was 29,955 at df44fd30 and at 17cbbd9b; release 2.27.2 added one
  sentence naming the Python 3.9 floor, 56 bytes, in 94bccf23, and nothing has changed it since), so a build has about 489 bytes
  for card text. Earlier designs worked around the bound: one left the card untouched
  (`docs/shiploop-check-phases-bc-plan-2026-10-28.md`), another wrote only a short form of its text there
  (`docs/shiploop-owed-outcome-journal.md`), and a candidate for another change failed `shiploop-package-integrity` by exceeding
  it on 2026-10-31 (df44fd30). Put the follow-on duty in the packets and a reference file, not in the card.

## 9. Change admission, pre-check

The SPEC's change admission asks for an adversarial evaluation before a change is planned. Dispositions are proposals for
the build plan.

| Consequence | Scenario | Disposition |
|---|---|---|
| weakens a clause | S-14: a decision waits on a person | mitigated: it is an open item in the report; nothing prompts |
| weakens a clause | S-10: a chain with no exit | mitigated: exit by an empty `gap` list or a repeated `gap`; no count; no chain without D2 |
| weakens a clause | S-12: a second parser for requests or lessons | mitigated: reuse `shiploop_request` and `shiploop_knowledge_home` |
| other style, host, platform | the printed command breaks under a host's quoting | mitigated: command substitution of a file; test on each host's adapter |
| fails silently | the model files a real gap under `note` | accepted: same as today; M1 measured it: all four readers label the same 11 rows `note`, and none of them a gap |
| passes tests, fails live | a list that validates but never recommends | partly measured (revision 6): four live Codex runs were accepted on the first try with real sources and two supported notes; no run reached a recommendation, so the recommended-run path is still unmeasured live (M2a) |
| model-written glue, dead ends | a malformed list refuses `complete` with no exit | mitigated: the refusal states the exit and a test submits it through the real CLI |
| enlarges packets | the handoff head grows | measured (revision 6): +1,475 printed characters in a real hello run (the head printed 16,850 to 17,462 of 20,000 in the four live runs); the handoff is not in `head_table.json` |
| leaks, touches user work | the request file quotes result text | mitigated: it is written under `RUN`, outside the repository, through the existing privacy screens |
| breaks saved runs, pins | a required key refuses a saved run at handoff | accepted: the stored shape is loose and the key is checked at the CLI gate only, as for `unverified`; no state version bump is expected |
| costs more than it saves | a second prelude for a 1% to 2% case (the replay: 2 to 3 decisions in 166 runs) | open: D4; M3 |
| gamed | the model classifies for effect (everything `note`, or `gap` to start runs) | mitigated: citations resolve; `gap` needs an S<n>; the full list is shown; no target metric on the count |
| compounds with the pass number | a chain of follow-on runs adds to the leaks the multipass journal measured (F1 to F3), and the live third and fourth passes repeated them, both filing their new decision as retired | open: recommend-only is no worse than a person-started pass; as of 3d5732d0 a chain waits for the release of the multipass fix, which met its A/B test (E2) and was tried on passes 1 and 2 only; E4 tests passes 3 and 4 and had not started (U9) |

Anchor: S-14 (a step that needs a person records an open item) and S-11 (the next run builds on retained knowledge); the run
evidence is thin (3 decisions in 122 runs), which is why section 7 comes first. Non-regression: no outcome, stage, loop or
limit changes.

## 10. Decisions for the owner

| | Question | Recommendation |
|---|---|---|
| D1 | Shape: follow-on run, in-run back edge, or stay manual | a follow-on run, as built (the list's request starts one; no back edge). Staying manual until runs of the owner's own features show more was the M1 advice and was not kept (M1 reported: no gap, two to three decisions in 166 runs) |
| D2 | Recommend-only, or auto-start a chain for `gap` entries | recommend-only; auto-start only after M2b shows a use and the multipass fix for what stages write has met its A/B test (E2: met) and been merged (as of 3d5732d0: not yet; tried on passes 1 and 2 only, E4 on passes 3 and 4 fixed and not started, U9) |
| D3 | A dollars or minutes ceiling on a chain | none proposed; yours if you want one, ending in a report |
| D4 | Build the recommend-only list now, or measure first | Decided: built, on the owner's "Rebase, Merge to main and publish, implement improvements" (2026-11-01), which I read as D4 = build. M1's advice to wait stands as evidence about demand: rerun the peek and the replay when runs of the owner's own features have finished (minutes, a few model calls) |

Decided here as routine and reversible: the term "follow-on"; the list lives in the handoff result; no new verb or option; the
start command uses command substitution of the request file.

## 11. Unknowns and rejected ideas

- U1. Whether the producing model classifies as a second reader would. M1 measured it on saved text: three other readers reproduce the first reader's classes on 28 of 32 rows.
  The live round (revision 6) measured the producing model at the handoff: four Codex runs filled the list on the first try with real sources, two notes supported by
  the assumption they cite and two empty lists, no gap and no decision. Whether a second reader would class those entries alike is U11, not measured.
- U2. (The request file exists since revision 6; no live run has started from one.) IN1 requires intake to cite every sentence of the request. A follow-on request that quotes the whole original would put
  those sentences under IN1. The draft passes the original by path, not by value; whether intake handles a quoted original
  is untested. The multipass cases pass a delta-only request and their runs planned only the delta (the live third pass too:
  0 kept IDs followed, 8 test cases citing no kept requirement; the fourth pass: 0 kept IDs in test cases and step plans, the
  rule it changed counting as a delta ID), which favours the path.
- U3. The request file lives under `RUN`, outside the repository and next to the run's workspace; where a later session finds
  it after the run directory is cleaned is unspecified.
- U4. The host's stop hook releases at `done`; a chain needs the host to start the next run in the same turn or the driver to.
  Untested.
- U5. A `capability` entry can be closed only by a host that has the capability. The script cannot know the next host.
- U6. The line between `gap` and `extension` is the one the owner's phrase "which we have now understood and learned" draws: a
  gap cites a request sentence or a refuted assumption; an extension adds scope. No real gap exists in the archive to test it:
  the replay's readers found none either (two Sol-retest candidates were not gaps).
- U7. Substantial features that "haven't concluded" are not in the archive (the corpus is small and every completed run already passes, and the only two
  runs of the owner's own features were unfinished).
- U8. Whether `release-verify`, whose lessons are written before `operations`, or `handoff` is the better owner of the list.
  The handoff was chosen because it restates and sees operations.
- U9. Chains past three passes. A third and a fourth pass have run (multipass E1, E3): both delivered what they were asked and
  kept every earlier requirement ID, and the permanent-file leaks recurred in both. Whether the leaks grow faster than the pass
  number is not settled: in bytes the third and fourth passes sit inside the second passes' range (+6.0 and +6.4 KiB against 4.5
  to 6.4), and in stray-heading count they sit at 8 and 9 against 1 to 8; the born-retired decision is what persists (one of the
  four saved second passes made it, none of E2's six control passes did, and both later passes continued that lineage; n=2, one
  lineage). The fix for the leaks was, as of 3d5732d0, tried on passes 1 and 2 only (E2), and a chain reaches the later passes
  by construction. E4 (fixed 2026-11-01, not started) asks the question with a run without the fix beside each fix run: whether
  the mislabel is bound to a seeded lineage or grows with the pass number, a tidy prior that ends with `Superseded` being its
  hard case. One lineage, one run per pass so far.
- U10. A `decision` that changes an earlier requirement is the multipass plan's modifying link, `ticket-sla` (built and
  calibrated on hand-written variants; run live once, E3). E3 changed the requirement in place and kept every ID, but how a
  pass retires or supersedes an earlier decision in the living files is still untested on a model: the old decision was
  already filed under `## Superseded` when E3 began (E1 had inherited the mislabel), so leaving it standing looks the same
  either way. A clean test needs
  a prior made without the mislabel, and a follow-on run acting on such a decision depends on it. The failure seen live is
  the reverse: a new decision filed under `## Superseded` and so born retired (E1, E3).
- U11. The replay classified whole texts, one class each, and the texts that mix items (F18, F23) split the readers. The
  follow-on list classifies entries one by one. Whether readers agree entry by entry is not measured; a replay over entries
  split by hand would measure it.

Rejected: a size threshold (a number nobody can know, and big is not unfinished); asking the user at the end (S-14); a
reflection stage with an Improve-style loop (no checkable exit); gating `done` on the list (honest runs would be refused);
reusing the research-probe candidate (XI, not adopted).
