# A named end-of-inner-loop stage for learnings and re-planning: journal (2026-11-22)

Owner question, 2026-11-22, verbatim, in two messages:

1. "One of the key things that I do want to look into is to determine if, after an inner loop run, we need to go into
   key learnings about what was built and the tests that were created, review and update the specs, and potentially
   update the plan. We would actually have a permanent, iterative updating of the plan as a very specific named stage
   at the end of the inner loop. Can you investigate this and help me understand if this is what we should do?"
2. "updating specs, environment, architecture, plan steps, local skills which could be created to enhance future
   operations (which needs reference in architecture), is what I was thinking"

Later the same evening, two more, verbatim:

3. "I do feel like we should probably have a specific skills directory that gets created in the repo if skills are
   used specifically. We should put them somewhere where we would make them available to the LM, but make it clear
   that maybe it's a named folder that ShipLoop knows about and symlinked into the constituent location that Claude
   or Codex would find the skill. Or, potentially, if there's an ability to use agents.md to specify where the skill
   would reside so it gets picked up, that's fine too. Help me figure out if this is an option, the idea being that I
   want to be clear about the skills that get created on the fly and reused by the inner loop cycles."
4. "We should also be clear that if we do update the spec, we would definitely need to incrementally update the plan
   to accommodate the spec changes."

Method: the owner's rule of the same evening (memory note `sonnet-for-delegated-tasks`): one-shot items whose output
and learnings we want go to an Opus or Sonnet agent by complexity. The census (section 3), the host skill-discovery
research (section 8) and the spec-to-plan route map (section 9) each ran as one Opus agent; the main session checked
a sample of each against the raw files and made the readings.

Consumer: the owner, deciding whether ShipLoop gets a new named stage at the end of its inner loop. Later: anyone who
proposes a knowledge, learnings, re-plan or skills stage for ShipLoop. Read section 2 first: this idea has come up at
least six times since 2026-10-06, and each round's evidence is cited there.

Status: concluded for this round on 2026-11-22; the decisions in section 5 are the owner's. Sections 1, 2, 8 and 9
are firm for what was read in the source and the records; section 3 is firm as counted; section 4 is an independent
review, checked where marked. Nothing in `skills/` changed and no model delivery was run.

Source read: skill-craft `main` at 2ddacc9ed7317a7576e2cfefd477bf63c3fa4862 (skill-craft 4.4.1, ShipLoop 2.6.1).
Evidence for this journal: `docs/experiments/end-of-inner-loop-20261122/` (`census/`, `review/`).

Terms. The *inner loop* is the part of a ShipLoop run that builds one work item: `step-plan`, `test-spec`,
`validate-existing` when an expectation fails, then for each step `implement`, `test`, `document` (with the step's
review and ShipLoop's step commit), and last `carry-forward`. The *knowledge home* is `docs/shiploop/spec.md`,
`environment.md` and `architecture.md` in the product repository, which ShipLoop keeps and commits across runs.

## 1. What ShipLoop already does (firm, from the source)

The stage the owner describes exists by name and by duty. `carry-forward` is the last inner stage of every work item:
"Close the item: update the knowledge home; the future queue in `work_items`; the reusable-skill decision in `skill`"
(`shiploop_stage_spec.py`, the "carry-forward" row; `references/carry-forward.md`). Each step's `document` stage is the
step's reflection on what it showed (the "document" row, its third done-when line).

| The owner's part | Where it happens today | What the script checks |
|---|---|---|
| Key learnings about what was built and tested | implement's `learned` line at every step, the last two shown to the next implement packet (`look_back_lines`); document's `knowledge` record per living file; the step commit's Knowledge home section; carry-forward's summary and run note; release-verify's `lessons`, which become the body of that stage's knowledge commit and are quoted to the next run's intake and discovery (`last_lessons`) | document's `knowledge` record is required |
| Spec | `spec` writes the living spec; each step's `document` adds marked lines inside the requirement (R-n) the step concerns | a living spec that drops an earlier R-n is refused; a step may add only marked lines inside an existing R-n (`step_spec_refusal`, `_step_spec_refusal`) |
| Environment | most stages that find a command, a harness or a platform fact, `document` and `carry-forward` among them (`STAGE_FILES` in `shiploop_knowledge_home.py`) | placement notices at accepted stages (counted, never refusals) |
| Architecture | `plan`, `step-plan` and `implement` may add a decision (AD-n); `document` reflects; `carry-forward` "records the run's decisions and what they superseded" | an architecture that drops an earlier AD-n is refused |
| Plan | `carry-forward` may replace the whole future work-item queue (`work_items`), puts a defect in the item it just finished into a corrective item, and must route every observation that affects later work to an owner; `document` sends work the step plan lacks back to `step-plan`, which since ShipLoop 1.34.0 keeps done steps and amends only what is still to run ("fix forward") | the queue must keep every primary requirement in some item's `follows`; `_fix_forward_refusal` and `_frozen_case_refusal` (in `_check_fix_forward`) refuse an amendment that reopens a done step or its cases |
| Local skills | `carry-forward` records `skill` (none, reuse, update or create) with its reason and repeat evidence; a skill lives in the repository, is named in environment.md `## Skills` and linked from the repository's index (a dedicated index, README or AGENTS.md; the guide also asks for a `SHIPLOOP.md` backlink); `discovery` reads the index and each `step-plan` reopens it and lists a step's helper skills (`references/testing-and-documentation.md`, "Reusable product skills") | for update or create: an existing `SKILL.md` with `name` and `description`, and non-empty evidence; ShipLoop then commits the skill (`_check_skill_decision`). The index links, the trial note and architecture registration are not checked |

Where the owner's wording differs from what exists:

- **Plan steps.** `carry-forward` revises future *items*, not the steps of the item it closes. Within an item the
  remaining steps change only through a send-back (fix forward). Since ShipLoop 2.4.0 (release
  4693c1a307984a71dda367d98568337e663d6e53) a step plan has one step by default, so at the end of an item there is
  usually no step left to re-plan.
- **A reference in architecture.** Skills are indexed from environment.md `## Skills` and the repository's own index,
  not from architecture.md.
- **Spec at the end of the loop.** `document` writes spec.md step by step, under the step spec gate. `carry-forward`
  is also told to: its duty 1 (`DUTIES["carry-forward"]` in `shiploop_prompts.py`) says to write "each R-<n> this item
  satisfied; an open gap under its R-<n>" into spec.md, although `STAGE_FILES` lists only architecture.md and
  environment.md for it, and the step spec gate does not run at carry-forward (section 4). Corrected 2026-11-22 after
  the review: my first draft said carry-forward does not write spec.md.
- **A permanent plan.** The plan lives in the run's state, not in the knowledge home. What outlives a run is the
  knowledge home, the step commits, release-verify's lessons and the handoff's recommend-only `follow_on` list
  (`shiploop_follow_on.py`, ShipLoop 1.29.0).

## 2. Six earlier rounds of the same idea (firm; each cited)

| Date | The question then | What was measured | Outcome |
|---|---|---|---|
| 2026-10-06 | Plan in a rolling wave (plan the next part after each part) | `docs/planning-time-analysis-2026-10-06.md` section 5, option 4: saves 0.3 to 0.6 minutes (estimate); carry-forward is its catching gate | rejected (41cf3cf433c3f1d9ae03578f8c85e290fb21de28) |
| 2026-10-28 | "Do we need to introduce a stage ... after we implement? ... update the architecture, environment or anything we've better understood about the specs? ... any more tasks that should be added?" | option A, a knowledge stage after each step's review, against option C, the reflection folded into `document`; Astra max recommended C; across 13 runs all 20 skill decisions were `none` | the owner chose C ("Go with C"): no knowledge stage (review 7b2d57b7e4d2d40e49a87ef1cbc2944d6acec911, build 7bba525ed74ad436ddbbe526db029714fdec47cb). Key learning in that commit: option A "would add a writer after the review, which nothing then checks" |
| 2026-10-31 | After delivery, reflect on what was learned and re-enter ShipLoop from the top | 122 finished runs: no leftover was a gap the system could close without a person; a replay by four readers found decisions in 1.2% to 1.8% of 166 runs | built as the recommend-only `follow_on` list, never auto-started (release 41ee3d89d580fb715fc90994b2361348550698c7; `docs/shiploop-follow-on-run-journal.md`) |
| 2026-10-31 to 11-01 | Second, third and fourth passes on the same repository | later passes keep every earlier R-n byte for byte and touch no earlier test; lessons reach the third pass; but `environment.md` grew 4.5 to 6.4 KiB of stray headings a pass and a live decision was once filed as retired | the placement fix (9e39b146db427c26f68c0e22d900e70c92be5011, released in 5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a); chain B then ran four of four passes clean. Value was not testable: every pass passed (`docs/shiploop-multipass-journal.md`; follow-on journal F11 to F16) |
| 2026-11-12 | "After each task for inner loop, should we have a step to determine if there are any key learnings that would update the overall pending step plan?" | 300 runs: 8 of 84 send-backs came after a documented step, 7 of them plan-time faults in a later step's proof, none clearly needing knowledge an earlier step revealed; carry-forward replaced the queue 4 times, each only adding a W2 after a single W1, never revising a pending item; Astra max: no new stage | no new stage; fix forward built and released as ShipLoop 1.34.0 (study 3d42222e2e1783e64bf78b2d2760ca7ff92a7538, release f7a1b450b205ae854a60e149328126252bb44005; `docs/experiments/step-boundary-replan-20261112/README.md`). The forward-impact question in `document` was proposed as a pilot and its replay with new-information cases (Q2) is still open |
| 2026-11-20 | Ratchet: one build, then tests, a fix loop and a closing "what did we learn" stage that lengthens the spec | closing looks added requirements that two blind outside judges mostly did not accept (10 of 59); 6 of 9 tested closing-look clauses failed on a correct reference; one made the test session rewrite 21 earlier tests | do not build (merge 1a905ece0384a9eb23a893c52c5ffdc68454c645; `docs/ratchet-pilot-journal.md` sections 10, 13, 14, 17) |
| 2026-11-20 | Track learnings progressively as a run iterates (round 5 of the structure study) | `learned` filled 460 of 460, cited in 28% of steps shown one, no benefit; switching the look-back off changed no hidden check in the short K0 slices; the carry-forward skill decision was `none` in 306 of 306 carry-forward results (282 archived, 24 from slices); 281 of 282 accepted plan results held one work item | track nothing more (2d31558b03027118f0f7bf25ba863f133b6e11ff; `docs/shiploop-sdlc-structure-journal.md` round 5). Its rule: no lessons store or new learning field without new evidence from long runs, a cleared context or a later run |
| 2026-11-22 | A look at the running product built into ShipLoop (product-acceptance) | v1, the builder looks at its own work: found nothing; v2, a fresh worker looks: found real things, but the building session's fix did the least, and audits showed no gain at 1.4 and 2.0 times the minutes | not proposed; branch `shiploop-look-f586c6` kept off main (close 518a1e20363e9560ccd62e9e8326e04e61d84b63; `docs/ratchet-vs-shiploop-journal.md` sections 17 to 21) |

Two more facts bear on the skills and architecture part:

- **A document that is only named is not read.** In the platform-knowledge study a page named in the project's
  knowledge file reached 0 of 3 products; a fact seeded under `## Platform facts` in environment.md reached the
  accepted plan, architecture or spec in 8 of 8 (the plan result alone 5 of 8) and the product 3 of 3; an entry the script hands over inside a stage's duty was delivered 6 of 6 by value and 3 of 3
  by a pointer with an instruction (`docs/platform-knowledge-journal.md` sections 32, 33, 37, 50 to 52; merge
  007c45d50e16acd856c31646174cc1ee76f1e29c). So a skill referenced from architecture.md would, on that evidence, not be
  opened by a later run unless the script hands it to the stage that should use it.
- **The bar for a local skill is rarely met.** carry-forward may create one only for a procedure that ran in two or
  more steps or items of the run, or that a pending item or requirement says will recur. With one item of usually one
  step, nothing repeats inside a run, which matches `none` in 306 of 306 carry-forward results. These `none` results
  say little about skills missed on other kinds of work (Sol, section 4).
- **ShipLoop already has a closing review.** The Improve review that runs after the last item's carry-forward (the
  end-of-work review) changed code or tests in 10% of one-step and 21% of multi-step items in the structure study's
  census (`docs/shiploop-sdlc-structure-journal.md` round 1, R7). Those are edits; their effect on outcomes was not
  measured.
- **Stale statements build up across passes.** The four-pass chain B ended with stale "Planned" statements in every
  final architecture.md (`docs/shiploop-multipass-journal.md` Round 5), even with the placement fix.

## 3. Current-version census: what carry-forward and document do on ShipLoop 2.4.0 and later (firm as counted; 2026-11-22)

One Opus agent read saved delivery folders only (no model, no ShipLoop run; Git limited to log, show and diff with
`GIT_OPTIONAL_LOCKS=0`); last pass 18:47 after the last live run had finished. Script and outputs:
`docs/experiments/end-of-inner-loop-20261122/census/` (`census.py`, `runs.txt`, `census.out` with every table and
listing, `census.json.gz` with 282 run records, `tmp/` the classifier's checks). Checked by me: the skill-decision count
from `census.json` (none 170, reuse 5) and the test-ID rewrites in the 4c listing (for example `e2e-runs-pk/20261122-n/n07`).

Corpus: 282 whole deliveries on ShipLoop 2.4.0 or later; 150 finished (2.4.0 31, 2.4.1 36, 2.5.0 6, 2.6.0 77). Only 49
are exact release builds; 101 are candidate builds, flagged (platform lookups 34, answer route 32, spec-elaboration
defaults 13, structure round 15 14, owner notes 6, other 2). Drivers of the finished runs: Codex Sol 6.2 medium 94,
high 11; Sonnet 5.5 medium 35, high 9; Grok 4.6 xhigh 1. The carry-forward and document contracts are byte-identical
across 2.4.0 to 2.6.1. `agg.py` of the 2026-11-12 study still parses the layout.

| | 2026-11-12 (300 runs, older versions) | now (255 analysable runs) | now, exact release builds (49 finished) |
|---|---|---|---|
| Items | 283 | 177 | 59 |
| Items with more than one step | 90 | 48 | 16 |
| Step-plan versions per item | 1: 214, 2: 57, 3: 12 | 1: 158, 2: 18, 3: 1 | 1: 53, 2: 5, 3: 1 |
| Send-backs | 84 | 21 | 7 |
| Send-backs after a documented step | 8 | 1 (a candidate build) | 0 |
| Carry-forwards done / supplying `work_items` | 214 / 4 | 175 / 9 | 59 / 1 |

**Plans and re-planning.** 145 of 163 accepted plans (89%) held one work item: Codex Sol 109 of 109, Sonnet 35 of 53.
Every carry-forward with work still pending was Sonnet's (20). In 8 of those 20 carry-forward replaced the queue: all 8
edited the pending item's context, 2 its title and 2 its `follows`; 1 added an item (W3 after an owner note, a
candidate build); none removed or reordered one. 175 of 175 carry-forwards were done, none blocked. So where there is a
rest of the plan, carry-forward does update it, by carrying context forward to the next item.

**Skills.** none 170 of 175, reuse 5 (all Codex Sol, all naming the host's Plan Test skill; 7 other carry-forwards cite
the same skill and record none), update 0, create 0. No delivery added a SKILL.md to its product (0 of 282). No
decision filled `path`, `evidence` or `index`. Reasons, by keyword: nothing repeated 99, existing docs or tests cover it
86, no repository skill or index 54, one step or one item 47. environment.md has `## Skills` in 147 of 150 finished
runs.

**Document's knowledge record (224 results).** Steps changed spec.md in 152 of 223 (68%), architecture.md in 77 (35%),
environment.md in 121 (54%). The record agrees with the step's own diff in 207 of 210 firm labels for spec.md (99%),
192 of 205 for architecture.md (94%), 174 of 187 for environment.md (93%); short and formulaic, but truthful. No
automatic not-applicable document appeared.

**Carry-forward's own knowledge commit.** 98 of 175 (56%): environment.md 75, architecture.md 57, spec.md 33. In 126 of
152 runs ShipLoop printed its notice that a command that worked is not named under `## Commands` when carry-forward
was accepted: its duty "every command that worked" mostly goes unmet.

**How carry-forward changed spec.md (33 of 175).** (a) Lines appended inside an existing R-n: 3, all open-gap lines in
candidate builds. (b) An existing R-n line changed: 27, of which 24 only took test IDs out of the step-marked "Met by"
lines that implement or document had written; that was the only change in 19 of the 33. The two stages follow
opposite rules: the step lines name test IDs, and carry-forward's duty says "Test IDs live only in test code: write
none here". Contract text changed in 5: two in exact release builds (`sol-high-due-p2` appended "The original
executable compatibility check is due before local release." to an R-4 acceptance line; `sonnet-medium-due` fixed a
test-file name in R-4) and three in candidate builds (`t03` "Pending:" to "Met by:"; `g2` and `m1`, owner-note
revisions that reworded R-2 and R-3, R-5 and R-6, and in `m1` added W3 to the queue). (c) A new R-n: 0. (d) An R-n
retired: 0. One heading demotion (`h2`, a candidate). So a change to a requirement's meaning at carry-forward appeared
only where an owner note arrived mid-run, in candidate builds.

**Its review and its time.** Carry-forward's Improve review edited something in 27 of 155 (17%): Codex Sol medium 1 of
95, Sol high 1 of 11, Sonnet medium 17 of 37, Sonnet high 7 of 11; 14 of the 27 touched tests and 10 of those code.
Carry-forward takes 1.9% of run time and its review 2.6% (medians 0.23 and 0.22 minutes a run; Sol medium 0.17 and
0.18, Sonnet high 0.80 and 1.13). Document takes 4.8% and its review 4.3%. Median finished run: 15.4 minutes.

**Final knowledge home.** Median bytes (spec, environment, architecture): Sol medium 2,436, 2,768, 1,640; Sonnet medium
9,046, 11,307, 3,496; Sonnet high 17,931, 15,209, 8,596. environment.md carried headings matching no named section in
70 of 150 runs (101 headings; "Release procedure" 38 times, mostly from release-plan; carry-forward introduced 2).

Limits: the exact-release subset is small (Sonnet 14 finished); carry-forward's edits outside `docs/shiploop/` (README,
test docs) are not measured; 27 of the 282 runs had no `results/` folder and are outside `agg.py`'s counts; the set of
run folders on disk was still growing.

## 4. Independent review: Sol at max (firm for what it verified; 2026-11-22, 18:00 to 18:13)

Run: `ask.sh sol --json --effort max --profile consult --model gpt-6.2-sol`, served `gpt-6.2-sol`, effort max, no
fallback, read-only sandbox, exit 0, 13 minutes 24 seconds. Input: a neutral export of `skills/shiploop/` and the
journals of the studies in section 2 at 2ddacc9ed7317a7576e2cfefd477bf63c3fa4862 (account and personal names removed,
grep clean), plus the 2026-10-28 decision commit message. Brief `docs/experiments/end-of-inner-loop-20261122/review/sol-brief.md`;
answer verbatim in `review/sol-review.md` (raw JSON `review/sol-review.json`). The brief asked for its own answer
(Part A) before it checked my claims (Part B). It ran read-only probes of the spec and skill checks and recounted the
exported replay scores; the original model sessions and product repositories it did not see.

Its answer:

- **No new stage.** Keep `carry-forward` as the named end-of-item checkpoint and `document` as each step's reflection.
  "The open design question is whether a separate action would catch consequential evidence that the existing
  checkpoint misses."
- **Spec: change one thing in carry-forward.** Remove its instruction to write satisfaction and gaps straight into
  spec.md. Clarifications go through the guarded step reflection and its review; a gap found at item close becomes an
  obligation or a corrective item; a change in intended behaviour needs an explicit scope decision. Its reason: a
  closing synthesis can find a real gap, but letting it author requirements "risks turning an implementation choice
  into a contract that rejects correct products" (the Ratchet finding).
- **Environment, architecture and plan steps: leave as they are.** For architecture, link a skill's card from the
  AD-n or real-boundary check it implements or revalidates, so the link has a reader; a mandatory architecture entry
  for every skill would duplicate the existing registry and go stale. For plan steps, routine re-planning "can
  unsettle accepted proofs or drop independent work from a replacement queue"; the late cases on record point to
  better first proof selection and fix forward instead.
- **Local skills: leave the conditional duty.** A recurring procedure repays the effort only if a fresh reader finds
  it and succeeds on a later task; use the existing cold-reader trial when a real opportunity appears. "An index
  link and frontmatter establish discoverability only on paper."
- **The cheapest test that could change it** (not run): replay a real item boundary where new evidence from W1
  changes a W2 already in the queue. Freeze the checkout after W1's last reviewed commit. Control: the existing
  carry-forward. Treatment: a separate fresh advisory packet at that boundary, its finding fed through the same
  carry-forward checks. W2 starts cold in both, scored by a hidden check calibrated on a correct and a wrong
  implementation. Register first; one Sol 6.2 medium pair, Sonnet 5.5 medium only after a qualifying Sol result;
  qualify only if the control misses the W2 check, the treatment passes it, inherited checks and W1's records stay
  intact and the checkpoint adds at most 60 seconds. Two qualifying pairs would move it to a targeted advisory
  pilot at consequential boundaries; anything else keeps the current placement. Cost: two to four continuations, no
  rerun of W1. It needs a multi-item case where W1 changes W2, which natural runs rarely have (281 of 282).
- **Something I did not ask:** an open item due at carry-forward counts as settled once that item's later
  carry-forward returns done, with no check that the finding was resolved or mapped to a queue item
  (`_settled` in `shiploop_assumptions.py`). "If a consequential obligation disappears between items, trace that
  transition first."

Its corrections to my claims (Part B): B1, B2 and B5 true; B6 true as reported; B3 overstated (carry-forward's duty
asks it to write spec.md, and the knowledge commit takes all of `docs/shiploop/`); B4 overstated (also a `SHIPLOOP.md`
backlink; no link is validated); B7 overstated in its units (281 of 282 accepted plan results; 306 carry-forward
results; 273 finished runs); B8 true within its scope (the judges jointly accepted 10, jointly rejected 34 and split
on 15; the 6 of 9 came from one medium ticket-assignment run); B9 true on the registered endpoint (8 of 8 is the union
of plan result, architecture and spec; the plan alone 5 of 8); B10 overstated: the platform study did compare the same
base with no starting home against a seeded one and measured a product effect, so what stays open is the value of
knowledge that an earlier delivery captured itself. Sections 1 and 2 were corrected in place for B3, B4, B7 and B9.

Checked by me in the source after the review (firm): duty 1's spec.md line in `DUTIES["carry-forward"]`;
`_step_spec_refusal` is called only for `implement` and `document` done results and at the document review's import
(the inner-gates block and the Improve import in `shiploop_navigator.py`), so at carry-forward only the ID-retention
check (`_knowledge_gate`) applies to spec.md; `_settled` settles by ordering alone. Not checked by me: Sol's mocked
probe itself (it changed R-1's text at carry-forward and the edit passed).

## 5. Reading and recommendation (my judgment, for the owner to decide)

**No new stage.** The stage the owner describes is `carry-forward`, which already closes every inner loop, with
`document` reflecting at every step. A second named stage would duplicate it and, as the 2026-10-28 decision put it,
"add a writer after the review, which nothing then checks". Within one delivery, more reflection has been tried six
ways since 2026-10-06 and none paid (section 2), for three structural reasons:

- There is rarely a rest of the plan to update: 281 of 282 accepted plans held one work item in the older corpus, and
  145 of 163 on ShipLoop 2.4.0 and later (Sol 109 of 109; Sonnet 35 of 53); 129 of 177 items had one step. Where a
  rest of the plan does exist (Sonnet's multi-item plans), carry-forward already updates it: 8 of its 20 mid-run
  passes rewrote the next item's context, and one added an item (section 3).
- The first implementation already passes the hidden checks in the recorded cases (structure study round 4: 83 of 84
  terra runs), so hindsight has little left to correct inside the same delivery.
- Spec text written from hindsight tends to turn the builder's own choices into requirements that reject correct
  products (Ratchet: outside judges jointly accepted 10 of 59 closing-look additions).

**What to change instead, part by part:**

| Part | Recommendation | Why |
|---|---|---|
| Environment | leave as is | facts there reach the next run's plan and product (section 2); the multipass growth was fixed in 2.31.0 |
| Architecture | leave the writers; when a skill implements or revalidates a decision, link it from that AD-n or real-boundary check | gives the reference the owner asked for a reader and a purpose (Sol); a registry copy in architecture.md would go stale |
| Plan steps | leave send-back and fix forward; remove the dead end in section 9 | the late send-backs on record were plan-time faults, not new knowledge |
| Spec | take spec.md out of carry-forward's duty (gaps become open items or corrective items), and make a requirement change re-enter planning by script (section 9's gate) | the owner's rule (message 4) is not true by script today; carry-forward's spec edits are mostly churn (24 of its 27 changed-line cases only remove the test IDs the step lines wrote), and the meaning-changing ones came only with owner notes, in candidate builds (section 3) |
| Local skills | keep the conditional decision; decide the folder now if wanted (section 8), but build nothing until skills are created; for a skill to be reused by later inner loops, ShipLoop's script must hand it to step-plan (option D) | 0 of 175 decisions on current versions created or updated a skill; links and AGENTS.md do not reach the run's own worktree session |

**The spec rule, in the owner's terms.** A requirement's meaning changes after the plan only by an explicit decision
(an owner note or a requester's answer), never by a model's hindsight; a step's marked clarification lines stay
allowed. When a requirement does change, the script makes the plan absorb it: a pending item whose `follows` names it
re-plans it at its step-plan, or a corrective item is added, or `none` is recorded with a reason. Today the first half
is a prompt rule with holes and the second half does not exist. The owner-notes candidate (branch
`shiploop-notes-85299a`, another session's) is the main legitimate source of mid-run requirement change and touches
the same sentences, so the gate should be designed with it, not beside it.

**Fix now, whatever is decided:** these are defects on main, not design choices.

1. carry-forward's duty writes spec.md, against `STAGE_FILES`, with no step gate, and against the step lines' own
   rule on test IDs. One change removes all three: carry-forward writes architecture.md and environment.md only (as
   `STAGE_FILES` already says), and a gap it finds becomes an open item or a corrective item (Sol's recommendation).
   What it would lose on the census: 3 open-gap lines (they would become open items) and nothing document does not
   already write.
2. The send-back dead end: a requirement change found in a step is sent to a step-plan that may not write the spec;
   document and carry-forward route the same finding differently.
3. `_settled` closes an open item without evidence that it was resolved or mapped.

Each is a ShipLoop behaviour change, so it needs the owner's yes, a change note, a Sol max review before the build,
and an E2E round on both drivers.

## 6. The tests that could change the recommendation (none run)

Cheapest first, each with the decision it serves:

1. **Free reading (no model): did the deliveries whose requirement was reworded after the plan still meet the new
   text?** Mostly answered by the census: in exact release builds carry-forward's two rewrites were small (an appended
   due line, a corrected file name); the meaning changes came only with owner notes (`g2`, `m1`, candidate builds of
   another session). What is left: read `g2` and `m1`'s products against their reworded requirements. Decision: how
   the re-plan gate belongs in the owner-notes route, which is where a legitimate mid-run requirement change comes
   from.
2. **The skill-creation count.** Answered (section 3): 0 of 175 on current versions. So building option D or a
   folder delivers nothing until the creation rule or the work changes; the real decision is whether skills should
   be created more often, which has no evidence either way.
3. **Sol's boundary replay** (section 4): a separate advisory packet at an item boundary where W1's evidence changes a
   queued W2, against today's carry-forward. Decision: two qualifying Sol-then-Sonnet pairs would justify a targeted
   advisory pilot at such boundaries. It needs a multi-item fixture built for it, and the occasion is rare in natural
   runs (281 of 282 plans had one item), so it ranks last.

## 7. Unknowns

- Requests larger than one item: the occasion for re-planning a queue barely occurs in the corpus.
- The value, to a later delivery, of knowledge an earlier delivery captured itself (Sol's correction of B10): no run
  withholds it from an otherwise identical follow-on.
- Whether a fresh reader finds and uses a skill ShipLoop made: no recorded run has made one.
- Whether a `.claude/skills/` folder created mid-session is picked up by Claude Code; how Codex behaves mid-session
  (not measured: it needs a model turn).
- The Codex skill-isolation contradiction in section 8.
- Whether the 6 post-plan rewrites left products off their spec (test 1).

## 8. A named skills folder the hosts can find (firm for what was probed or read; 2026-11-22)

Research by one Opus agent: vendor docs read 2026-11-22, the Codex source at tag rust-v0.171.0, and no-model Codex
probes (`codex debug prompt-input`, codex-cli 0.171.0) in throwaway repositories. No model session was started on any
host. Notes, probe script and outputs: `docs/experiments/end-of-inner-loop-20261122/skills-discovery/` (`README.md`,
`probe/probe.sh`, `probe/out/`). Checked by me: the worktree location, the host-matrix sentence, step-plan's skills
instruction, `_skill_commit`, and probe outputs 01, 03, 05 and 06.

**What decides it is where ShipLoop builds.** `workspace start` builds in a sibling worktree,
`<main-checkout-parent>/.shiploop-runs/<repo>-<stamp>/worktree` (`shiploop_workspace.default_root`), and "Worktree
creation is local and does not re-root the host conversation" (`references/host-matrix.md`). The host session keeps
the directory it started in. So no host lists a skill that the run creates in its worktree: Codex did not list one
from the main checkout (probe 05), while a session started in the worktree did (probe 06); Claude Code reads
`.claude/skills/` from its start directory, its parents up to the repository root and folders below it. A named
folder, links into the host folders, or an AGENTS.md pointer help only sessions started later in a checkout that
holds the skill, that is, after the run's return.

| Host | Project skill folders read natively | Links followed | What AGENTS.md can do |
|---|---|---|---|
| Claude Code 2.1.330 | `.claude/skills/` (start directory up to the repository root; nested folders when first touched; `--add-dir` folders); no setting adds one | a per-skill link, yes (docs); a whole linked folder, unknown | read natively when no CLAUDE.md exists, as instructions only; cannot declare a skill folder |
| Codex 0.171.0 | `.agents/skills/` from cwd up to the repository root, and `.codex/skills/` (probe 01; current docs name only `.agents/skills`); not `.claude/skills/` or `skills/`; no config key adds a folder | per-skill and whole-folder links, yes (probes 01, 03) | instructions only; an AGENTS.md naming a folder added no skill (probe 01) |
| Cursor | `.agents/skills/`, `.cursor/skills/`, `.claude/skills/`, `.codex/skills/` (docs) | unknown | not documented |
| OpenCode 1.19.4 | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`; a `skills` array in `opencode.json` adds folders | unknown | not for skills |
| Grok 1.0.92 | `.grok/skills/` (likely `.claude/skills/` too: the harness turns that off) | unknown | instructions only |

No single folder covers both Claude Code and Codex: Claude reads only `.claude/skills/`, Codex `.agents/skills/` (and
`.codex/skills/`).

The owner's options, against his aim ("clear about the skills that get created on the fly and reused by the inner
loop cycles"):

- **A. One named folder plus per-skill links** into `.claude/skills/<name>` and `.agents/skills/<name>`. Later
  sessions list it (Claude documented, Codex measured). Inside the run it does nothing. Costs: a clone with
  `core.symlinks` off (Git for Windows by default) gets a small text file instead of the skill, silently; the links
  must be made, committed and kept in step; and `_skill_commit`, given a path through a link, would commit the link
  and not the skill's files (it commits `path.parent` with `commit_paths`).
- **B. Skills directly in `.agents/skills/`** (read by Codex, Cursor and OpenCode, and the agentskills.io convention),
  plus one Claude link each. The same limit inside the run; less plainly ShipLoop's.
- **C. An AGENTS.md pointer only.** No host loads a skill from it; it has the shape of a page only named in the
  project's files, which reached 0 of 3 products in the platform-knowledge study.
- **D. ShipLoop's script hands each skill over.** The `step-plan` packet prints each skill's name, description and
  SKILL.md path with what to do. This works inside the run on every host, in the worktree, and in later ShipLoop runs
  (the folder comes back with the return). The comparable measurement: entries the script handed over reached the
  product 6 of 6 by value and 3 of 3 by a pointer with an instruction (platform-knowledge sections 50 to 53). Today
  step-plan gets only "reread the host's skills and the repository's skill index" and environment.md's outline, not
  its `## Skills` text; once step-plan picks a skill, the later stages print it by value (`_skills_line`).

The agent's recommendation (weighed in section 5): D, one fixed folder registered in environment.md `## Skills` (it
suggests `docs/shiploop/skills/<name>/`, inside ShipLoop's home and returned normally, with `.agents/skills/` as the
native alternative), and links only at the owner's word, for sessions outside ShipLoop. Its deciding test first: count
how often carry-forward records `create` or `update` and whether a later step-plan lists that skill. If skills are
rarely created, D has little to deliver.

Also found:

- A Claude-only route: `/add-dir <worktree>` once per run makes Claude load and watch that worktree's
  `.claude/skills/` (documented, untested, one user action a run, no Codex equivalent).
- Codex can add folders at runtime only through its app-server API (`skills/extraRoots/set`), not from config,
  AGENTS.md or a model session.
- A contrary lead on Codex skill isolation: with a throwaway HOME and CODEX_HOME, no real-home skill folder was listed
  in 10 renders, against the 2026-11-20 finding that real-home skills are listed whatever HOME says. Not re-run under
  the original conditions; recorded in the memory note `use-the-codex-harness` for a side-by-side check.
- skill-craft has no CLAUDE.md (my brief said a one-line `@AGENTS.md`); Claude Code reads AGENTS.md natively since
  2.1.277 when no CLAUDE.md exists.

## 9. A spec change must re-enter planning for what it affects (firm for the source; counts from saved runs; 2026-11-22)

Research by one Opus agent, read-only: the source at 2ddacc9ed7317a7576e2cfefd477bf63c3fa4862 (ShipLoop 2.6.1) and
three `git log` scans of the product repositories in saved deliveries under `~/e2e-runs*/`. Notes, scripts and outputs:
`docs/experiments/end-of-inner-loop-20261122/spec-to-plan/` (`README.md` sections 1 to 5, the map of 18 routes;
`scan_spec_after_plan.*`, `classify_removed_lines.*`, `engine_split.*`, `gate_firing_estimate.*`). No ShipLoop
command, model or test file was run. Checked by me: `_reconciliation_permitted`, the `shiploop_defaults` docstring,
step-plan duty 10 and the scan outputs.

**The owner's rule is not true by script today.** Once `prepare` has run, no script route sends a spec change back
through planning.

- The only route back into spec, test-strategy and plan is the plan stage's own review (reconcile), and
  `_reconciliation_permitted` refuses it once prepare or any work item has run ("reconciliation is allowed only before
  prepare or work execution").
- Inside a step (implement, test, document, the step review) the spec takes only marked lines inside an existing R-n
  (`step_spec_refusal`); any other edit is refused with "report send-back". A send-back returns the item to step-plan
  (fix forward keeps the done steps); no planning stage reruns.
- Every other stage, an owner note, and a requester's answer: the only check is that no R-n is dropped
  (`shiploop_knowledge_home.check`). Nothing re-plans afterwards. The next item's step-plan sees the spec as a table of
  contents with no diff; completed items, the test strategy, `primary` and `defaults` are not revisited; `add-work`
  only appends corrective items. `shiploop_defaults` says so itself: "no script route replaces an accepted
  specification and what was planned from it".
- The one precedent is the opt-in delivery contract's script-enforced re-planning barrier
  (`shiploop_consumer_delivery`, `replan_required`), which covers that contract's own requirement list, not the living
  spec.

**Two inconsistencies on main today, whatever is decided about a stage:**

1. carry-forward's duty 1 tells it to write spec.md, `STAGE_FILES["carry-forward"]` leaves spec.md out (two tests pin
   that row), and the step spec gate does not run there. A reworded R-n at carry-forward passes with the ID check
   alone, and the knowledge close commits it. The queue stays as it was unless carry-forward replaces it. Later items
   build to the new text (their `follows` quotes it) while their plan-written context describes the old one. The
   completed item's plan, tests and code stay as built.
2. A dead end for a requirement change found in a step. The step refusal says such a change is "the step plan's to
   decide" and names send-back, but step-plan's duty 10 says "Keep every R-<n> and AD-<n>; write nothing else in
   KNOWLEDGE/". Meanwhile `document` routes a changed requirement to send-back and carry-forward routes it to blocked.
   Astra's 2026-11-12 "align them" (section 2) was never done: `git log -S` shows those sentences unchanged since
   2026-10-28 or earlier, and only the unreleased owner-notes candidate (branch `shiploop-notes-85299a`) touches them.

Two more, from the same map: `_settled` closes an open item on order alone (pinned by
`test_each_steps_document_keeps_its_open_items_until_its_items_carry_forward`), the same finding as Sol's in section 4.
And, by the agent's reading, not checked by me: an Improve review's own commit becomes the baseline of the ID check,
so a review could drop an R-n unseen.

**How often requirement text changes after the plan** (released engine, ShipLoop 2.4.0 and later, 58 deliveries with a
plan boundary, `gate_firing_estimate.txt`). A requirement line the plan held was rewritten in 6 of 58. The first
stage to rewrite it was carry-forward in 2 (`sol-high-due-p2`: R-4; `sonnet-medium-due`: R-4 and R-7), handoff in 1,
and other stages in 3. Every change was a rewrite; no requirement was added or retired. The agent read 4 of the 6 as
cosmetic (file names, a fixture path, status lines, wording) and 2 as touching what the plan relied on. In 3 of the 6
the edit was the model's own review, and one of them changed the spec to describe the test it had built. Counting
any line, post-plan spec.md commits that removed or changed one came from carry-forward 128 times, other stages 49,
document 18 and handoff 8, mostly lines added after the plan (step marks, status lines). On candidate branches (78
deliveries) the count was 9 of 78, with step-plan rewriting an R-n in 2 of the 3 owner-notes candidate deliveries.

**The agent's proposal (weighed in section 5):**

- The smallest change that makes the rule true by script is one gate modelled on `shiploop_primary.check_queue`.
  - ShipLoop records the spec's requirement lines when the plan is accepted.
  - A requirement has changed when it loses a line it held at the plan, is new, or is newly retired. Lines added
    later, such as step marks, may be rewritten freely.
  - Each changed requirement needs one routing row: a work item still to run whose `follows` names it (its step plan
    then re-plans it), or `none` with a reason.
  - The affected item's step-plan packet shows the change in one line.
  - The changed-requirement rule is written once and printed everywhere: document, carry-forward, the loop rule,
    step-plan and the references.
  - It would have fired in 6 of the 58 deliveries.
- Its risks:
  - It makes mid-run spec edits legitimate, which is the Ratchet hindsight risk.
  - `none` cannot be checked for truth, and `follows` may be incomplete.
  - An authority guard (a change needs an owner note or a recorded answer) would have refused all 6 firings: an
    option, not the default.
- The simpler alternative: freeze the contract after the plan; a requirement change then means blocked and a new run.
- Its order: decide first whether a run may update its spec, then build the gate or the freeze. Either way, align the
  wording and fix `STAGE_FILES` now.
- The cheapest deciding evidence: the owner-notes candidate's late-note deliveries already on disk
  (`~/e2e-runs/r-20261122-5d2cbc/`, another session's), especially `g2`, where a requirement changed at the last
  carry-forward with no item left to re-plan it. Did that delivery still meet the new requirement?

## 10. Fixing the three defects (2026-11-22; owner: "Yes, fix them"; in progress)

The owner answered "Yes, fix them" to the three defects of section 5, and later asked to check in whatever there was so
far (about 19:15). Design, its outside review and the decisions: `docs/experiments/end-of-inner-loop-20261122/fix-design.md`
(commit bfbd04ff188e2e5acf444de80fa9a203c7cecad3 for the first version).

- **Coordination.** The owner-notes candidate (branch `shiploop-notes-85299a`, another session, "accepted" by the owner at
  18:48 by its account) edits the same sentences of carry-forward's and document's duties. It releases first (about
  20:30); it takes the half of defect 2 that needs an owner note; defect 1 lands after it. It declined to carry the
  three-line change in its own release, because its confirming delivery must speak for its change alone.
- **Outside review of the design** (Sol 6.2 at max, 19:07 to 19:21, `review/sol-fix-review.md`): the one-bullet patch was
  incomplete (the queue refusal's "or write the entry first", the two reference files, and the end-of-work review
  hand-off also invite a spec edit); "each step's document has already marked what it met" was dropped (a step with no
  code or test change has an automatic not-applicable document); no gate on carry-forward's spec edits, agreed; for
  defect 2, blocked with the requirement ID, the conflict and the choices when a step finds that a requirement must
  change and nobody has decided it; the open-item guard is larger than the first design (IDs are unique only inside one
  result).
- **Defect 1, built on a branch, main-compatible part.** `fix/carry-forward-spec-47da85` (base bfbd04ff; built by an Opus
  worker at xhigh from an exact brief, no commit by the worker; diff read by the main session). carry-forward's duty 1,
  the queue refusal at carry-forward, one sentence and one clause in the two references, the end-of-work hand-off, tests
  that fail on the old text, a patch note. The plan's refusal stays byte-identical. Quick tier on the final bytes: 35
  of 35 suites, 1,418 tests; the carry-forward packet grows by 30 characters. No model has run on it. Not on main: the
  owner-note exception must be added after the candidate lands, then an E2E round on Sol 6.2 medium and Sonnet 5.5
  medium (release preflight), then the release.
- **Defect 3, decided by a census, nothing built** (`open-items/`; details in the design): 255 runs, 313 open rows, 312
  settled, 1 not due yet, 0 dropped; the approved guard by item ID would have refused 42 of 68 due-stage results with no
  right catch, because IDs are local to one result. Recorded as a real code gap with no cost on record; the owner can
  overrule.
- **Defect 2, the no-note half:** a product-behaviour choice for the owner, not built: a step finds that a requirement
  itself must change and no owner note covers it. Sol recommends stopping and asking; the strongest case against asking
  is a local correction already dictated by the accepted request.
- **Method notes.** Sol's second review cited candidate runs as `k1` and `g3` (step-plan after a send-back) and `g2`
  (carry-forward), correcting the summary in section 9. The open-items agent's and the build worker's numbers were
  recounted or diffed by the main session before use (total rows, classes, the guard count; the source diff).
