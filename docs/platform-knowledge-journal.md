# Platform knowledge journal

How ShipLoop and the Ratchet pilot put a platform's key considerations in front of a model while it plans, and
whether that material should be a card, a wiki or something else. A living record: entries are dated, and a later
entry corrects an earlier one in place, with the date and the reason.

Consumers: any session that changes how ShipLoop loads reference material, and the owner.

Status words used below: **firm** (counted from records and hand-checked), **interim** (my reading of the counts),
**exploratory** (not tested).

## 1. The owner's question (2026-11-22)

First message, in part: "I want to consider a reference file that talks about design principles and considerations
when actually using instances of certain technology aspects. Those can be used as reference material when building
out a plan to build certain types of skills. [...] building out key considerations and thoughts about when building
features that are on a Salesforce platform [...] to just make sure that whatever model we're using doesn't skip over
these key notions. Can you help me understand how we would incorporate this kind of notion into both Ratchet and
Shiploop, and how we could build up that reference file that could be used to help during planning? I don't want to
do something that's overwhelming or polluting the context [...] I don't know if something like a wiki is better".

Second message, whole: "I want to test to see if the cards load it and I wonder if the wiki style would pollute
context less, but requires key identifiers and pointers in order to pick up the other items. I worry the file cannot
be loaded in context but we would need to have a karpathy style wiki skill used by shiploop (and helper scripts to
make it fast)."

How I read two terms (looked up, not asked):

- **Cards** are ShipLoop's platform cards, the files under `skills/shiploop/references/platforms/`.
- **Karpathy style wiki** is the pattern of Andrej Karpathy's "LLM Wiki" note
  (<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>, read 2026-11-22). Its parts: raw sources that
  are never edited; a wiki of small linked Markdown pages that the model writes and keeps up; a schema file that
  says how the wiki is laid out; three operations (ingest a source, answer a query, lint). On finding pages it says
  "When answering a query, the LLM reads the index first to find relevant pages, then drills into them", where
  `index.md` lists every page with a link and a one-line summary. It says the index alone "works surprisingly well
  at moderate scale (~100 sources, ~hundreds of pages)" and names a search tool only beyond that.

## 2. What exists today (read on main at 22e52c0807ca41aa0224dd81f03b84e9bba44e82; no model called)

**In ShipLoop.**

- Eleven platform cards, 9,410 words in all. `salesforce.md` is the longest at 1,989 words; the others run from 222
  (`bash.md`) to 1,000 (`node-express.md`).
- The selector is `references/coding-guidance.md` ("Select guidance" and its "Conditional index" table): the model
  is told to select a platform card after identifying the runtime.
- The discovery stage text (`shiploop_prompts.py`, stage `discovery`, item 3) asks the model to record, in the
  product's `docs/shiploop/environment.md` under `## Targets and runtimes`, "the platform guide each target follows
  (GUIDES/platforms/<name>.md), or none". Added by 6925d45435a2ce83229678a7bb73ad8f5c219795 (2026-10-20), whose
  message says why: "the Salesforce card's testing rules [...] never reached test-strategy, plan or step-plan".
- The script then does one thing with that record. `platform_cards()` in `shiploop_navigator.py` reads the names
  from that section, and `_platform_testing_lines()` prints "Platform testing guide: <card>#testing" at the four
  stages of `PLATFORM_TESTING_STAGES`, for a named card that has a `## Testing` section. Two cards have one
  (`salesforce.md`, `apps-script.md`).
- A second route needs no model: the test loop and the mutation check match a test command against each card's
  `## Remote tests` list (`salesforce.md` is the one card with such a list) and name the card in the skip reason.
- Nothing prints a card's design content at the plan stage. It reaches the plan only if the model opens the file.
- The plan stage already has a gated form for decisions: the concern map (`shiploop_concerns.CONCERNS`, fifteen
  concerns such as `platform-services`, `scale`, `security`, `switchover`). The plan writes one row for each concern
  of each work item, `check_plan` refuses a plan without them, and `packet_lines` carries the applicable rows to the
  stage that owns each. Added by fff7fa13fd537d7152e9d71a476b716e4f5e6839.

**In the Ratchet pilot.** `docs/experiments/ratchet-pilot-20261120/ratchet.py` can add a question or a section to a
stage's text (`--enrich`, `--preserve`, `--rules`). It has nothing about platforms. It is a pilot script, not a skill.

**Earlier measurements that bear on the question.**

| Where | What it measured | Result |
|---|---|---|
| `docs/shiploop-architecture-rubric-results-2026-09-26.md`, "Platform cards on general deployments" | 64 plans on Sonnet over four hosted environments, with the environment's card linked or absent; the card was read in every trial of the card variant | Overall 0.88 without a card, 0.86 with. Host fit 0.59 to 0.91, sharing model 0.90 to 1.00, personal data 0.88 to 0.58, limits 0.68 to 0.54: a card helps what it is specific about and costs what it crowds out. |
| `docs/shiploop-run-insights-plan-2026-10-18.md` | Two whole deliveries read | "The models follow gates, not guides: neither run opened `plan-record.md`, `coding-guidance.md` or `platforms/ui.md`". |
| `docs/spec-elaboration-journal.md` section 38 | Which of the top-level guides 36 real deliveries opened (platform cards were not counted: `guide_reads.py` reads `references/*.md` only) | The main spec guide was opened by 0 of 26 Sol and 0 of 9 Sonnet deliveries; every delivery opens the run's own machinery guides. |
| Same journal, sections 43 and 58 | What a Codex model shows itself of a packet | The instructions arrive nearly whole in the first four stages; the list of references after "Result template:" at a median of 15% of its lines at the spec stage. |
| Same journal, sections 51 and 53; `docs/ratchet-pilot-journal.md` F43 | A question put as a section to fill | Answered every time it was tried (14 of 14), and the specification was no fuller for it. |

**Wiki work that already exists, in other repositories of the owner.** Found by a search of the disk, not known to
me before:

- `claude-craft/plugins/wiki-suite`, version 0.3.1, "Project LLM wiki": skills `wiki-init`, `wiki-ingest`,
  `wiki-process`, `wiki-query`, `wiki-load`, `wiki-lint` and `proactive-research`, with shell handlers and Claude
  Code hooks. Its `wiki-notify` handler tells the model which pages matched the prompt and that it should load
  them; `wiki-load` and `wiki-query` then have the model choose and read whole pages. A memory note of 2026-09-24
  records it as disabled after a hook-cost audit.
  *Corrected 2026-11-22 after the review (section 7):* I first wrote that the handler "puts short previews in front
  of the model". This copy does the opposite on purpose. Its comment reads "Directive only — no page content
  injected. Partial previews cause the LLM to skip /wiki-load (context poison). Force skill invocation instead."
  That is a finding of the owner's own earlier work and it bears on this question: a short excerpt can stop a model
  from fetching the page behind it.
- A Hermes skill `llm-wiki` 2.1.0 ("Karpathy's LLM Wiki: build/query interlinked markdown KB") in two other
  repositories.

Neither is in skill-craft. Both are built for one host.

## 3. Reading R0: do platform cards load in real runs? (2026-11-22, firm for what it counts)

**Question.** In the runs on disk, did a platform card reach the model, and by which step of the route: named at
discovery, linked by the script, opened, shown?

**Tool and inputs.** `docs/experiments/platform-knowledge-20261122/card_reads.py` (no model called; it reuses the
readers of `docs/experiments/spec-elaboration-20261120/guides_test.py` for what a model was given). Run as
`card_reads.py ~/e2e-runs ~/e2e-runs-*`. Output: `evidence/card-reads-all.txt` (every asked run, then the tallies)
and `evidence/card-reads-asked.jsonl` (one row a run).

**What is counted.**

- *asked*: the run printed a discovery packet that asks for "the platform guide each target follows".
- *named*: the delivered `environment.md` names `platforms/<name>.md` under `## Targets and runtimes`; or it
  mentions a platform guide or card there and names none, which is counted as "none"; or it says nothing about a
  platform guide.
- *linked*: the script printed a "Platform testing guide:" line.
- *opened*: a command or file read the builder made names a card file; the stage is the last packet header before.
- *shown*: how many of a card's own lines (20 characters or more, in no other card and no stage text, read from the
  run's own installed copy of the skill) stand in what the model was given. On Codex that is the host's session
  record, because the model there shows itself only part of a command's output; on Claude the tool results; on any
  other host the event stream.

**Result.** 1,354 run folders were read. In 382 the discovery packet asked (ShipLoop 1.8.0 to 2.6.0; 296 on Codex,
60 on Claude, 26 on Grok; 308 finished). 316 of them delivered an `environment.md`.

| Of the 316 | Runs |
|---|---|
| The targets section names a card | 18 |
| It says there is none | 89 |
| It says nothing about a platform guide | 209 |

*Corrected the same day, before this entry was committed:* my first pattern for "none" expected the words in one
order ("Platform guide: none") and counted 26, leaving 63 runs that say it another way ("No platform guide
applies", "No deploy, CI or platform guide") among the silent ones. Of those 63, 53 match a wider pattern of denial
and were not each read; the ten wordings that match neither pattern were read by hand and each denies a guide. The
tool now counts any mention that names no card as "none". That is a count of mentions: it does not show that "none"
was the right answer for the project. No other count moved.

By the family of the model that drove the run (the 316):

| Family | Runs | Named a card | Said none | Said nothing | Opened any card | Given any card line |
|---|---|---|---|---|---|---|
| Terra | 192 | 0 | 60 | 132 | 1 | 2 |
| Sol | 58 | 0 | 0 | 58 | 5 | 5 |
| Sonnet | 40 | 0 | 22 | 18 | 1 | 0 |
| Grok | 17 | 14 | 2 | 1 | 16 | 17 |
| DeepSeek (through the Claude host) | 8 | 4 | 4 | 0 | 4 | 5 |
| Luna | 1 | 0 | 1 | 0 | 1 | 1 |

- **Terra, Sol and Sonnet never named a card: 0 of 290**, in the targets section or anywhere else in the file.
  Grok named one in 14 of 17.
- **Sol did not answer the question at all**: none of its 58 files mentions a platform guide. Terra and Sonnet
  answered "none" in 82 of 232 and were silent in the rest.
- **A named card was always opened, and nearly always given whole.** All 18 runs that named a card opened it. Of
  the 21 named cards, 20 had every own line given and one (DeepSeek, `node-express.md`) 22 of 27.
  *Corrected 2026-11-22 after the review (section 7):* I first wrote "always read, and read whole"; one card was
  not. "Given" means the line stands somewhere in the run's record: 286 of the 382 runs are read from a Codex
  session record, 60 from Claude tool results and 36 from the event stream, and the count keeps no time, so it does
  not show that a line was given before a particular decision.
- **When a card is opened at all, it is at discovery**: 32 of the 44 first opens (a first open is counted once for
  each run and card); the rest are spread over seven other stages, one or two each.
- **The script's link was printed in 4 runs**, each a Salesforce run (three on Grok, one Terra trial). The script
  builds it from the name in the targets section (`platform_cards()`) and prints it in the packet's list of guides,
  which follows the result template. Only one of the four has a saved file that shows the name; the other three
  ended without a delivered `environment.md`.
- Over all 382 asked runs the builder opened any card in 37 and was given any card line in 40 (36 runs are in
  both). 19 of the 37 opened a card without naming one, so a name is not what makes a model read a card.

**Salesforce work.** 13 asked runs are of the four Salesforce cases (`chess-salesforce`, `battleship-salesforce`,
`battleship-salesforce-ui`, `gym-membership-salesforce`): 10 on Terra, 3 on Grok, none on Sol or Sonnet.

- Grok, 3 runs: the card was opened at discovery and given whole in all three.
- Terra, 10 runs (8 finished): the card was given whole in 1 (at the test stage), 10 of its 156 own lines in 1,
  and none of it in 8. **Of the 8 finished deliveries, 6 were built with no line of the Salesforce card in front
  of the model.**
- Two of those Terra runs (`gym-published-baseline-03`, `ui-live-2`) answered the discovery question about the
  product instead of about ShipLoop's cards: "no local examples, conventions, or platform guides observed" and "No
  repository platform guide exists".
- Ten further rows are trials of a Salesforce page task on Terra that stopped early and delivered no
  `environment.md`: one opened the card at discovery (139 of 166 own lines printed), nine did not.

**The few opens on Terra, Sol, Sonnet and Luna** (10 runs opened a card or were given a line of one; the rows
are in the evidence file). I looked at what came before four of them. In each the packet names one place for one
need:

- `gym-published-baseline-03` (Terra): the card is opened with `cat` at the test stage, after a test packet whose
  rule on readable test output ends "a platform's runner: GUIDES/platforms/".
- Two Sol deliveries of `grokbot-local` opened `ui.md`, one at the spec stage and one in a review. The spec
  stage's list of guides names that file and one section of it ("UI visual-direction guide",
  `platforms/ui.md#light-expressive-starting-point`); it is the only card that a stage's list names.
- `sonnet-high-due`: one `grep` of `bash.md` for the format of a hand-written check, at the test stage. No whole
  line of the card was given.

The other six were not looked at: three Sol deliveries of one day that opened `node-express.md` or `python.md` at
step-plan or implement, one Luna delivery, the Terra delivery that was given 10 lines with no call naming the file,
and the Terra trial.

**Hand checks.**

1. Three Sonnet runs counted as "says nothing" (`e2e-runs-sdlc12/20261121/sonnet-high-due`, `sonnet-medium-due`,
   `sonnet-medium-expenses`): the only line of each `environment.md` that holds the word "platform" is the heading
   `## Platform facts`.
2. `e2e-runs/2026-11-04/chess-sf-clean` (Terra, finished, counted as not opened and nothing shown): its event stream
   names `platforms/salesforce.md` 16 times, and all 16 are ShipLoop's own mutation-skip reason ("platforms/
   salesforce.md lists `sf apex run test` under Remote tests"). A sentence only the card holds ("Design
   collection-based entry points") stands 0 times in the event stream and 0 times in the session record. So the
   script knew the card applied, and the card's text never reached the model.
3. `gym-published-baseline-03`: the call is `cat .../references/platforms/salesforce.md` and the count is 148 of 148
   own lines.

**Limits.**

- *Shown* needs a whole card line of 20 characters or more that only that card holds. A fragment read with `grep`
  can be missed (hand check: the one Sonnet `grep`).
- *Opened* needs the file's name in the call. A read through a wildcard or a variable is not counted there; *shown*
  catches it (13 runs were given a line of the Salesforce card with no call that names the file: 10 on Grok, 2
  through the Claude host, 1 on Codex).
- Most asked runs build small local Python or Node programs, where the card that applies is `python.md` or
  `node-express.md`. Whether "none" was the right answer for a plain Node service is a judgment the count does not
  make: Sonnet wrote "none (a plain Node HTTP service)" where Grok named `node-express.md` for the same case.
- Family and host go together here: Grok runs only on its own host, DeepSeek only through the Claude host.
- Each run is read against its own installed copy of the skill, so the count holds across the versions; the stage
  texts differ between 1.8.0 and 2.6.0 and are not compared.
- **Nothing here measures whether a loaded card makes a delivery better.**

## 4. What R0 means for the wiki question (2026-11-22, interim, my reading)

1. Two things can put a card in front of a model today, and both are left to the model: it opens the file itself
   (Grok does, at discovery), or it writes the card's name and the script then lists one section of it among the
   guides. The three families that drive the runs now (Sol, Sonnet, and Terra before them) do neither, with rare
   exceptions. This is the same finding as "gates, not guides", now counted for platform cards.
   *Reworded 2026-11-22 after the review (section 7):* my first wording made the written name the cause of the
   reading. The records show cards opened without a name and do not show the order of the two.
2. Size is not what stops a card: a card that is opened is read whole. What fails is the trigger.
3. So a wiki changes the wrong step if the model still has to follow a pointer to it. The owner's condition ("requires
   key identifiers and pointers in order to pick up the other items") is the hard part, and the record says pointers
   the model must choose to follow are not followed by these families. The exceptions looked at (four opens,
   section 3) are packets that name one place for one need, at the stage that needs it.
4. A wiki is still the right way to *store* the material once it outgrows a card. A full treatment of one large
   platform is tens of pages, which cannot be put whole into a packet; the Karpathy note says an index is enough
   for hundreds of pages.
5. The keys a script could use already exist in ShipLoop: the platform, the stage, the fifteen concern names, and
   which concerns the plan marked as applying to a work item. A lookup by those keys is a table read. It needs no
   search and no decision by the model.

## 5. Candidate design (2026-11-22, exploratory; nothing built)

Storage and delivery are two separate choices.

**Delivery, four ways:**

- D0, today: the model names the card; the model opens it; the script links the testing section of a named card.
- D1, gate the name: discovery is not accepted until each target line says `Platform guide: <card>` or `none`, with
  the cards' one-line descriptions printed in the discovery instructions. The model then reads the card as Grok does.
- D2, script detects and prints by value: a card declares what makes it apply (as `## Remote tests` already
  declares commands); the script matches, and at the plan stage prints the card's line for each concern beside that
  concern's question. A row the plan marks as applying carries the card's lines to the stage that owns it.
- D3, model-pulled wiki: the material is pages with an index; a duty in a packet's instructions tells the model to
  look up the pages for what it is deciding, with one fast command, and the result lists the pages read.

**Storage, two ways:** S1, one file a platform with headed sections; S2, a folder of small pages a platform, each
with keys (platform, concern, stage, when it applies, a one-line summary) and an index compiled from those keys by a
script.

My candidate: D2 with D1's gate as the fallback where there are no files to detect (a new build), S1 until a card
outgrows what one stage can carry, then S2 for that platform. The authoring side of the Karpathy pattern (ingest a
source into pages, lint the pages) is where a separate skill would earn its place, and it can come after delivery is
shown to work.

Not known: whether lines printed beside the concern rows change what the plan decides; what they crowd out; whether
D3 is picked up when it is a duty with a result field instead of a pointer.

## 6. Proposed next step (2026-11-22, not registered, no run started)

A head-to-head of the delivery routes on real ShipLoop runs, stopped at the plan's acceptance, on both current
drivers (Sol at medium, Sonnet at medium): the released stage (D0), lines printed by value beside the concern rows
(D2), and an index with a look-up duty (D3). Read for each run: whether the applicable lines were shown to the model
(this entry's tool), how much platform text was shown in all, the plan's decisions against a checklist written
blind from the card, the generic concern rows (for what is crowded out), and time and tokens. A bench of single
sessions is not used for the pick-up question: the spec study's bench sessions opened the main spec guide in 116
to 120 of 120 sessions, where real Sol and Sonnet deliveries opened it in 0 of 35
(`docs/spec-elaboration-journal.md` section 38).

Before it is registered the design goes to a Sol max review (section 7).

## 7. The Sol max review (2026-11-22, sent 09:45, returned 09:55)

Asked of the latest Sol at max effort, read-only, on a neutral copy of the files (ShipLoop as released, this
journal's first six sections with the tool and its evidence, the earlier measurements it cites, the Ratchet pilot's
loop and the old wiki plugin). Served as asked: `gpt-6.2-sol`, effort `max`, no fallback. Question:
`docs/experiments/platform-knowledge-20261122/review/QUESTION.md`; the answer, word for word:
`review/sol-max-answer.md` (3,789 words). Its paths start `/private/tmp/review-eyzTGR/`, the neutral copy.

**Its verdict, in its words.** "Pilot a small, source-backed planning block for a known target. Keep the released
workflow as the control. The archive shows a gap in getting card text to planners. It leaves open whether that gap
limits deliveries. Have ShipLoop select and print the applicable facts beside the existing planning duty. Defer the
discovery gate. Keep one sectional card per platform and let Ratchet use the same facts through its own runner. A
wiki skill can wait. Ship a change only if both medium-effort drivers make repeatably better decisions and those
decisions survive a downstream check."

**What it corrected in section 3.** Three things, each checked against the evidence file before it was accepted,
and each now corrected in place above: one named card was given 22 of 27 lines, not whole; the 89 "none" are
mentions that name no card, not shown to be correct answers; and the link's dependence on the written name is seen
in one saved file of four. Its figures for the inputs (286 session records, 60 tool-result streams, 36 event
streams; 36 runs in both the opened and the shown counts) reproduce. It also corrected my description of the old
wiki plugin's hook (section 2).

**What it corrected in the candidate (section 5).** Read in the source before it was accepted:

1. *Selecting a card and showing it are two separate failures.* `platform_cards()` takes any `platforms/<name>.md`
   path in the targets section, so a line that denies a card by its path still selects it, and a line that names a
   card without the path selects nothing. A required line would be a new contract and would still allow a wrong
   "none". For a first trial, give the target to every arm the same way and test selection separately.
2. *A plan cannot use its own answers to choose what it is shown.* The rows that say which concerns apply are what
   the plan stage is deciding. So the facts go beside the duty that asks for the rows, once for each target, not
   attached to rows marked as applying. An accepted "does not apply" can itself be the miss under test.
3. *The stage that decides a fact can come before the plan.* `test-strategy` precedes `plan`, and a constraint that
   changes observable behaviour belongs in `spec`. After the plan, the decision should travel in the existing
   records. At `step-plan` the concern rows are printed early (`_stage_input_blocks`); at the other stages they go
   through `_consumer_lines`, after the result template, where a Codex model shows itself little.
4. *Text placed early improves the odds and proves nothing by itself.* The testing link is printed in the list of
   guides (`_Block("guides", LOOKUP, ...)` in the packet assembly), the part least often shown. What each host
   showed the model has to be read from its own record for every sample.

**What it proposed instead of my three-arm test.** One variable at a time: first no model call (find a saved plan
with an applicable fact, a decision that lacks it and a consequence; render the released and the changed packet from
the same records and compare the text); then a screen of four sessions, released against printed, on both drivers,
from one frozen starting state; then the same facts by an exact-section look-up, to compare pulling with printing;
automatic selection as its own test; and a matched pair taken through the downstream check before any default
changes. Fix the rule first: each fact confirmed as shown before the decision, a repeatable gain in a decision
named in advance on each driver, no new critical regression. "A card name, a copied sentence and a completed row
are exposure or compliance signals. A pass requires an actionable choice or check." The checklist must be written
blind to the card.

**Other points taken.**

- *Card or wiki:* keep keyed entries in one file while it is easy to review ("the navigator can extract three
  entries from a 14,000-character file for the same model-facing cost as extracting them from three pages"); split
  when sections have their own owners or when a measured look-up cost falls. Keys for a look-up that needs no
  judgment: platform, the boundary or capability touched, the stage that decides, a version where it matters, a
  stable entry id. From the wiki pattern keep provenance, cited updates, a generated index and a lint.
- *Building the material up:* add an entry only when it can name when the fact applies, what decision it changes
  and what observation could prove the decision wrong; one reviewed source for each entry; an unreviewed page has
  no authority. Three homes that already exist: the card for the portable fact, the project's `environment.md` for
  what was observed about its target, the spec and decisions for what the project chose.
- *A route I had not listed:* put the fact in the project's own `environment.md` and let the released workflow
  carry it. If that closes the gap, no new runtime feature is needed.
- *Ratchet:* it has no discovery and no concern map; the same facts go into its case inputs, a hard constraint into
  the specification text and the design prompts into the plan text. `--spec-from` with `--stop-after plan` gives a
  paired comparison.
- *If storage ever changes,* keep the top-level card file and its `## Testing` and `## Remote tests` headings: the
  script reads them (`_card_bullets` in `shiploop_mutation.py`, `_platform_testing_lines`).

**Not followed, and why.** It suggests the first case be a real one (the Salesforce entry a user cannot open). The
first case here is an invented platform (section 10), because a real platform cannot separate "the route delivered
the fact" from "the model knew it", and a first rung has to be scored by a script. The Salesforce case comes after,
as the realism rung, judged blind as the review asks.

## 8. Two more free readings (2026-11-22, no model called)

**How much of the plan packet does a Codex model show itself?** Already counted by the spec study over 50 Sol
runs (`docs/experiments/spec-elaboration-20261120/evidence/readings/packet-shown.txt`, the `plan` row, 26
packets): every instruction line in 4, four fifths or more in 17, under a third in 4. The list of guides after
the result template: a median of 17% of its lines. So text in the plan stage's instructions usually reaches the
model on Sol and sometimes does not, and text in the list of guides usually does not.

**Did the saved Salesforce deliveries follow the card's rules without the card?** Static counts on the nine
finished deliveries of the Salesforce cases (`salesforce_static.py`; output `evidence/salesforce-static.txt`; the
runs in `evidence/salesforce-static-runs.txt`). Written by a Sonnet subagent to my definitions; I reran it and the
table reproduces; its lint findings were fixed and the output compared byte for byte.

| Rule of the card | What the nine products show |
|---|---|
| A page a user opens needs a tab file | All nine have the component, one tab file that names it and an app file, with or without the card |
| Tool state is git-ignored | Both entries in 4, one in 1, no `.gitignore` in 4; the two runs that were given the whole card: one has both, one has no `.gitignore` |
| Visibility is source (a permission set) | Present in 5, absent in all 4 chess deliveries, the Grok one that read the whole card among them |
| Classes declare sharing | At least one class declares it in each of the eight Terra deliveries (1 of 1, 1 of 2 or 2 of 2); 0 of 2 in the Grok delivery that read the whole card |
| The test command uses the output format ShipLoop can read | 163 of 446 lines that hold the test command in the Grok run that read the card at discovery; 0 to 2 of 37 to 94 lines in each of the eight Terra runs, the one that opened the card at the test stage among them (2 of 58) |

Reading (interim): on what a model already knows about the platform, deliveries that never saw the card do as well
as the one that read it. The one sharp difference is the one rule that exists nowhere but in the card, a fact about
ShipLoop's own reader.
*Qualified 2026-11-22 by section 11:* the difference shows that the run which read the card followed it, not that
following it mattered. Every one of these requests fixes the test command with the other output format, the runs
that used it were not refused, and their outcomes match the card-read run's. That matches the earlier test where a card entry was the only thing that surfaced a hidden
property (0 of 15 to 3 of 3, `docs/shiploop-composition-state-experiments-2026-09-26.md`) and the review's first
answer. Limits: nine runs; counts of lines, not of commands; model, host and ShipLoop version all differ between the
card-read run and the others; the card is the one each run had installed, and every copy holds all the rules counted.

## 9. Where the candidate stands after the review (2026-11-22, exploratory)

- **What to carry:** facts that change a decision or the check that proves it, and that a model cannot be expected
  to know: rules of this tool, of this project's target, and platform defaults that fail silently. Not a
  description of the platform.
- **Delivery, first form:** for a target that is already known, the script prints the card's planning entries by
  value in the plan stage's instructions, beside the duty that asks for the concern rows and before the result
  template, with one sentence asking that they be used in decisions and proving checks the plan already owes. No
  new result field, no refusal, no other stage changed.
- **Selection:** left as it is for now (the name in the project's knowledge home) and tested on its own later.
- **Storage:** one file a platform with a `## Planning` section of keyed entries. A folder of pages is a later
  step, taken when a measured look-up cost says so.
- **The wiki skill:** its authoring half (ingest with sources, a generated index, a lint) is what is worth taking
  from the pattern; its reading half is the script's job here.

## 10. Registered before any run: the plan (2026-11-22)

The owner, 09:48: "Build up a plan you think is best. Execute tests, examine alternative ideas, run side
experiments, run shiploop tests as needed. Try to do progressive validation to get fast results", and a few minutes
later a reminder to use Opus and Sonnet agents, Opus for research.

**The bench.** An invented hosting platform, "Harbor", with five rules written only in its card, a small existing
product on it, one request, and script readings of a plan and of a product. Specified in
`docs/experiments/platform-knowledge-20261122/harbor/SPEC.md` on the candidate branch `pk-candidate-0d73cf` (the
candidate code, the card and the fixture live there and nowhere near `main`). Its product checks are calibrated on
a reference product and six defective copies before any model runs.

**Drivers.** Codex `gpt-6.2-sol` at medium and Claude `claude-sonnet-5-5` at medium, both counted in every rung.
ShipLoop is built from the candidate branch, cut from main at 22e52c0807ca41aa0224dd81f03b84e9bba44e82 (ShipLoop
2.6.0); one module constant, set by an overlay file, chooses the route, so every arm is the same build.

**Arms** (SPEC, "The arms"): R released; I the entries printed by value at the plan stage; L one line that names
the section to read, at the same place with the same sentence; W the whole card printed; K the released build with
the five rules written in the project's `environment.md` and no card named.

**Readings.** *Shown:* of the five entries, how many had all their lines given to the model between the plan
packet's printing and the plan's submission (`plan_exposure.py`; the Codex session record or Claude's tool
results). *Decided:* of the five rules, how many the accepted plan commits to in the platform's own terms
(`plan_score.py`; the token rules are in the SPEC and were fixed before any run; a plan that only names the card
scores 0). *Product:* of six platform checks, how many a delivered product passes under a strict stand-in for the
platform (`harbor_grade.py`), and whether the product's tests pass.

**Rungs, each read before the next is launched.**

| Rung | What runs | Samples | Rule fixed now |
|---|---|---|---|
| 0 | No model: the plan packet rendered under each route from one seeded state, compared | | The added text stands before the result template; route `off` is byte-identical to the released packet |
| 1 | Plan stage only, from one frozen state: R against I | 2 drivers x 2 arms x 2 = 8 | *Leak check first:* if any R sample scores 3 or more decided, the fixture gives the rules away: stop and repair it. I **arrives** on a driver if 4 or more entries are shown in both its samples. I **moves the plan** on a driver if it decides at least 3 more rules than R in both pairs. The screen passes when both hold on both drivers |
| 2 | Same state: L, and K | 2 drivers x 2 arms x 2 = 8 | Each route reported as shown and decided; a route is called different from I only on a gap of 3 rules or more in both samples of a driver |
| 3 | Whole deliveries from the request, the target named in the product's knowledge home: R against the best route of rungs 1 and 2 (I on a tie) | 2 drivers x 2 arms x 2 = 8 | The route **holds downstream** on a driver if its products pass at least 4 more platform checks than R's in both pairs and no existing test fails |
| 4 | A Salesforce planning case: R against the best route; a checklist written blind to the card; two blind judges of different families | registered in an amendment before it runs | Gain in at least one decision named in advance, on each driver, in 2 of 3 samples, with no new critical regression by both judges |
| 5 | The Harbor card grown to wiki size (about 30 entries, the same five apply): entries selected by key and printed, the whole file printed, and a look-up by index | registered in an amendment before it runs | Shown, decided, characters of platform text given, minutes and tokens, side by side |

Rungs 1 and 2 use `test/shiploop_e2e/slice.py` seeded at the plan stage (a seed point the candidate branch adds)
with `--stop-after plan --planning-review none`. The review of a plan is left out of the screen to keep one
variable; that is a limit of rungs 1 and 2.

**Side readings and experiments.** An audit by an Opus agent of the accepted plans in the nine saved Salesforce
deliveries, for three card rules: was the fact missing when the decision was made, and what followed (no model
run). An ingest trial: one Opus session turns the platform faults recorded in the two Salesforce run journals into
entries of the form section 7 asks for, with a source for each, and a lint script checks the form. A Ratchet cell,
if rung 1 passes: the same entries in its plan text with `--spec-from` and `--stop-after plan`.

**Predictions, scored as written.** R decides at most 1 rule of 5 on both drivers. I is shown 5 of 5 on Sonnet and
4 or more on Sol in most samples, and decides 4 or more on both. L is shown on Sonnet; on Sol I do not know. K is
shown less often than I, because the plan packet does not print the project's file by value.

**Stopping.** At each rung's end the journal says whether there is enough to conclude. A fault of the bench is
fixed and the cell rerun, with the faulty sample kept and marked. Every assigned sample stays in the comparison.

**Not decided here.** Any change to ShipLoop as released is the owner's decision; the candidate stays off `main`.

## 11. The plans of the saved Salesforce deliveries: was a card fact missing when it mattered? (2026-11-22)

**Question** (the review's first step, section 7): in the nine finished deliveries of section 8, for three rules of
the card, was the fact missing when the decision was made, and did something go wrong because of it? Rules: A, a
tab is hidden until a permission set or profile grants it, so presence, visibility and access are three things; B,
the test command needs the output format ShipLoop can read; C, the tool's `.sf/` and `.sfdx/` folders must be
git-ignored.

**How.** An Opus research subagent read each run's accepted plan, later stage results, trace and events, and the
two Salesforce run journals; no model run. Its report, as returned:
`docs/experiments/platform-knowledge-20261122/evidence/plan-audit-report.md`. I hand-checked its two main claims
(below); the rest is its reading and is marked so.

**Result.**

1. **The requests carried the facts.** Hand-checked in five saved `prompt.txt` files: they run to 698, 906, 1,023
   and 1,110 words. The Battleship ones name the permission-set file and what it grants and say "A new tab is hidden
   from every user until a permission set or profile grants it, so after you deploy, assign the permission set to
   the logged-in user with `sf org assign permset ...`". The chess ones say "do not change profiles or permission
   sets". All five give the exact test command, with `--result-format human`. None mentions `.sf`.
2. **One fault traced to a missing card fact, and it cost about 40 seconds** (subagent's reading): run `sf-live-2`,
   rule C, the one rule no request states. A step's deploy check failed ("Could not find HEAD") and the model
   repaired the tool's state files; the product shipped with no `.gitignore`.
3. **Where runs did lose time, the card had no line for it** (subagent's reading): two send-backs of one to two and
   a half minutes on "Duplicate PermissionSetAssignment", a fact about the assign command the card does not hold.
4. **The run that read the whole card at discovery (Grok) followed all three rules and ended like the others.**
5. **The card's rule B says something the runs contradict.** It says a focused command in the human format "is
   refused as unread". In all nine runs such commands were marked passed, with no refusal (subagent's reading). The
   current stage text (`COUNT_RULE` in `shiploop_test_loop.py`, hand-checked) asks only that every listed test id be
   in the output, with "a runner flag that prints test names" where the count cannot be read. A lead, not a finding:
   I did not trace the judging code, and the card is not changed here.

**What it means (interim, my reading).**

- In these deliveries the platform knowledge reached the model through the request, written out by whoever wrote
  the case, at 700 to 1,100 words a request. That is the route that works today, and it agrees with the neighbouring
  studies: what moves a build is an answer from the requester. The question for a reference file is therefore not
  "would it rescue these deliveries" (the record says they needed no rescue) but "can it carry what the requester
  now has to write each time, so that a short request does as well as a long one".
- A card earns a line for a fact that no request states and no model knows. Of the twelve platform faults the two
  journals record, the card covers six and half of a seventh; four it does not cover are small facts of exactly
  that kind (a page rejected for its region mode, a log returned HTML-escaped, an exception that cannot be caught
  from anonymous code, the order in which a permission set and its assignment are removed), and the runs add a
  fifth (an assignment that fails when it already exists).
- A card can go stale against the engine it describes (point 5). Whatever stores the material needs a check that a
  claim about ShipLoop's own behaviour still holds.

**Limits.** Nine runs, eight on one model family that is no longer the driver; the subagent's readings of plans and
traces are not all re-checked; nobody verified whether the chess tabs were visible to the user.

## 12. Amendment 1 to the plan, registered before any run (2026-11-22)

Section 11 shows which route is in use today: the facts written into the request. So the bench gets one more arm,
at rung 2, as the mark to measure the others against:

- **Q, in the request:** the released build, the fixture with no card named (the knowledge home of arm K without
  its platform facts), and the request extended by one paragraph that states the five rules in plain sentences.
  2 drivers x 2 samples = 4 more plan-stage runs.
- **Rule fixed now:** a route is **as good as the request** on a driver when it decides within one rule of Q in
  both pairs. Prediction: Q decides 5 of 5 on both drivers; I is as good as Q on both.
- The words a route saves the requester are reported beside it: the paragraph's length in words.

The ingest trial of section 10 takes the five uncovered facts of section 11 as its input.

## 13. Rung 0: the bench calibrated and the plan packet read under each route (2026-11-22, no model; firm)

**Apparatus.** Built by two Opus subagents to the specification, reviewed by me, committed on the candidate branch
as 85d7758dc3603188bfa44d175ee640973f6376de (branch `pk-candidate-0d73cf`, 74 files, off `main`). Every run below
is launched from that commit.

**The bench catches what it should** (`calibrate.py`, rerun by me):

| Product | P-JOB | P-RUN | P-BLOB | P-SCAN | P-SLOT | P-CONFIG | Own tests | Score |
|---|---|---|---|---|---|---|---|---|
| The untouched fixture | fail | fail | fail | fail | fail | fail | pass | 0 of 6 |
| The reference product | pass | pass | pass | pass | pass | pass | pass | 6 of 6 |
| No `max_seconds` | **fail** | pass | pass | pass | pass | pass | pass | 5 |
| Output not named by slot | pass | pass | pass | pass | **fail** | pass | pass | 5 |
| A local file, no blob | pass | pass | **fail** | pass | fail | pass | pass | 4 |
| `blobs.put` without `keep_days` | pass | **fail** | **fail** | fail | fail | fail | pass | 1 |
| `records.list()` | pass | pass | pass | **fail** | pass | pass | pass | 5 |
| The threshold in the code | pass | pass | pass | pass | pass | **fail** | pass | 5 |

Bold marks the check named for the defect. Two defects take other checks down with them (no blob leaves nothing
for the later checks to read; a refused `put` ends the start), so a product score counts consequences, not rules:
rung 3 reports the row, not only the score.

**The fixture gives no rule away by statement.** I read every file. The local stand-in for the SDK shows the call
names (`scan`, a `keep_days` argument, `config`), as an SDK would. What a model can work out from that is what the
released arm measures.

**The plan packet under each route** (`render_plan_packet.py`; the four packets are kept in `harbor/packets/`):

| Route | Characters | Added | Where |
|---|---|---|---|
| off | 27,735 | | byte-identical to the released render |
| inline (arm I) | 29,790 | 2,055 | line 35 of 282, inside duty 3 right after the sentence on the concern rows; "Result template:" is line 176 |
| lookup (arm L) | 28,036 | 301 | one line at line 35 |
| whole (arm W) | 31,194 | 3,459 | line 35 |

The rule of rung 0 holds: the added text stands before the result template and `off` is identical to released.

**The requests.** The request is 57 words. Arm Q's adds a paragraph of 159 words that states the five rules in
plain sentences (`harbor/request-with-notes.txt`). That is what a route has to save the requester.

**Rung 1 launched at 10:38** from the candidate checkout into `~/e2e-runs-pk/20261122/` (allocation
`harbor/runs/rung1.tsv`; sample names are neutral because a session can see its folder's path). Pairs, fixed
before any result: on Codex s01 (R) with s03 (I) and s07 (R) with s05 (I); on Claude s04 (R) with s02 (I) and s06
(R) with s08 (I).

## 14. Rung 1: released against printed, at the plan stage (2026-11-22, 10:38 to 10:50)

Eight plan-stage slices from one seeded state, each ended by the harness at the plan's acceptance (all eight:
`process`, `stopped` and `no_overshoot` true), about five and a half minutes a wave of four. Runs:
`~/e2e-runs-pk/20261122/s01` to `s08`; readings kept in `harbor/readings/` on the candidate branch
(`rung1-plan-exposure.txt`, `rung1-plan-score.txt`, `rung1-second-reading.txt`).

| Sample | Driver | Arm | Entries shown before the plan was submitted | In the packet | The model's own read of the card | Rules decided, registered reading |
|---|---|---|---|---|---|---|
| s01 | Sol medium | R released | 5 of 5 | no | `cat` at 10 s | 1 (SLOT) |
| s07 | Sol medium | R released | 5 of 5 | no | `cat` at 11 s | 2 (JOB, SLOT) |
| s03 | Sol medium | I printed | 5 of 5 | yes | `cat` at 12 s | 0 |
| s05 | Sol medium | I printed | 5 of 5 | yes | `cat` at 11 s | 1 (SLOT) |
| s04 | Sonnet medium | R released | 5 of 5 | no | `cat` at 4 s | 4 (all but CONFIG) |
| s06 | Sonnet medium | R released | 5 of 5 | no | `cat` at 4 s | 3 (JOB, SLOT, SCAN) |
| s02 | Sonnet medium | I printed | 5 of 5 | yes | `cat` at 2 s | 5 |
| s08 | Sonnet medium | I printed | 5 of 5 | yes | `cat` at 4 s | 5 |

**By the rules fixed in section 10.**

- *Leak check:* it fired. Released samples s04 and s06 decide 4 and 3 rules. The rule was written for a fixture
  that gives its rules away. That is not what happened: in every released sample the model opened the card itself
  and was given all of it. The rule as written did not foresee that the released route could deliver. Recorded as
  fired; the fixture is not changed.
- *I arrives:* yes on both drivers (5 of 5 in all four samples). So does R.
- *I moves the plan:* no. Sol: 1 against 0 and 2 against 1 (R ahead by one). Sonnet: 4 against 5 and 3 against 5
  (I ahead by one and two). The bar was three more in both pairs.
- **The screen does not pass. Printing the entries by value changes nothing that these readings can see.**

**Predictions, scored as written.** "R decides at most 1 rule of 5 on both drivers": wrong (1, 2, 4, 3). "I is shown
5 of 5 on Sonnet and 4 or more on Sol": right. "I decides 4 or more on both": right on Sonnet, wrong on Sol by the
registered reading.

**What happened, and it is the finding of this rung (firm for this setting).** With the card named in the
product's `docs/shiploop/environment.md`, **both drivers opened the card on their own within 2 to 12 seconds of
the plan packet and were given every line of it, under released ShipLoop, 4 of 4.** (The released packet also
lists the card's Testing section among its guides, so two pointers were present; which one was followed is not
separated.) This agrees with section 3, where every one of the 18 saved runs that named a card opened it. So
the earlier count is not "models do not follow a pointer to a card". It is narrower: **no Sol, Terra or Sonnet
run ever wrote the name, and once the name is there the card is read.** The broken step is selection.

**The registered reading of "decided" under-reads one driver.** Sol writes its decisions in plain words, and the
detail goes into the knowledge home's `architecture.md`, which `plan_score.py` does not read. Sample s03, which
scores 0, wrote: "AD-2: Declare `jobs.low_stock_report` in the manifest [...] 02:00 UTC and a 60-second run
budget", "AD-3: Declare `low_stock_threshold = 10` in the manifest and read it through Harbor config. Read the
existing Item schema via cursor scan to cover stores beyond the 500-record list cap", "AD-4: Store UTF-8 CSV in the
app's Harbor blobs under `reports/low-stock/<slot>.csv`. A retry writes the same key. Seven-day retention [...]".
That is all five rules decided, by my reading of one sample. A wider pattern reading written after the fact
(`second_reading.py`, exploratory, plan result and `architecture.md` together) gives Sol 5, 3, 3 and 4 and Sonnet 5
in all four, and I can see it still misses decisions in s03. Sonnet uses the platform's own tokens, so both
readings credit it. Lesson, the second of its kind today: a count made from wording patterns under-reads a writer
who restates. The script-run product checks of rung 3 are the reading to trust; no more effort goes into scoring
plan text by pattern.

**Limits.** A slice starts cold at the plan stage, and the first thing each model did was read the product's
knowledge home, where the name is. In a whole delivery the name has to survive, or be written at, discovery.
Two samples a cell. The review of the plan was off (`--planning-review none`).

## 15. Amendment 2, registered before any further run (2026-11-22, 10:55)

Rung 1 moved the question from "is the text shown" to "is the card selected, and does a selected card reach the
product". The later rungs change accordingly.

- **Dropped:** the look-up arm L, and the plan-stage runs of K and Q. A look-up line cannot add to a card that is
  already read in full, and plan text has proved a poor thing to score.
- **Rung 2, now the selection test at the plan stage:** the released build on the fixture whose knowledge home
  says "Platform guide: none" (as 89 of the 316 saved runs said), the plain request; arm **N**. 2 drivers x 2
  samples = 4 slices (`harbor/runs/rung2.tsv`, s09 to s12). Reading: were the card's entries given, and did a
  call open the card. Rule: N **finds the card** on a driver when the entries are given in both samples.
  Prediction: at most 1 of the 4 samples opens the card.
- **Rung 3, now three arms of whole deliveries**, graded by the six product checks:
  **R**, the knowledge home names the card (released build); **F**, a fresh repository with no knowledge home, so
  discovery has to select the card (released build); **Q**, the fresh repository with the five rules written into
  the request. 2 drivers x 3 arms x 2 samples = 12 deliveries, R and F first. The printed arm I is left out: it
  added nothing in rung 1.
  Rules: a route is **as good as the request** on a driver when its products pass within one check of Q's in both
  pairs; R **holds downstream** when it passes at least 4 more checks than F in both pairs with no existing test
  failing. Predictions: Q passes 6 of 6 on both drivers; R at least 5; F at most 2, because discovery does not name
  the card.

## 16. Side trial: building the material up and keeping it true (2026-11-22, no model run)

The owner's first question included "how we could build up that reference file". One Opus subagent did the work
once by hand, as ingester and reviewer both (a weakness it names itself). Its files are in
`docs/experiments/platform-knowledge-20261122/ingest/`. I checked the lint's tests, the probe's output and the two
commits it names; the readings of the journals are its own.

**Ingest: five candidate facts, two entries.** Input: the five facts of section 11 that cost time in real
Salesforce runs and that the card lacks. Rule for an entry (section 7): it names when the fact applies, the
decision it changes and the observation that could prove the decision wrong, and it has a source.
`entries-proposed.md`:

| Fact | Outcome | Why |
|---|---|---|
| A page rejected for its region mode | rejected | a build detail, seen once, in the harness's own probe page; the deploy error explains itself |
| A debug log returned HTML-escaped | rejected | a fact about how the harness read the output, seen once; a later run shows it unescaped |
| An exception from anonymous Apex that cannot be caught | **entry `SF-ANON-AURA`** | seen twice; changes how a check is designed. Its "applies when" is half testable: the code that throws is not written when the plan is made |
| The order of removing a permission set and its assignment | rejected | a cleanup fact of the harness; the platform's own refusal enforces the order |
| An assign command that fails when the assignment exists | **entry `SF-ASSIGN-AGAIN`** | a script can test when it applies; its only source in the repository is the audit report, itself an unreviewed reading |

So most facts taken from a harness's rehearsals describe the harness, and an honest ingest rejects most of what it
is fed.

**Lint.** `entry_lint.py` checks the form of every entry in a card's `## Planning` section: a unique id, concerns
that are among the fifteen, "Decision:" and "Proof:" present; with `--sourced` also "Applies when:", "Source:" and
"Kind:" (hard constraint, evidenced default, or a question that needs an observation), and that a quoted source
phrase occurs in the file it names. 28 unit tests pass; clean on the Harbor card and on the two proposed entries; it
says plainly that the released Salesforce card has no such section.

**A stale claim, traced.** The released Salesforce card says a focused Apex test command in the default or "human"
output format "is refused as unread". `stale-claim-check.md` and a probe that feeds a sample of each format to the
real judging functions (`judge_formats_probe.py`, output `judge-formats-probe.txt`):

| Format | Ids listed, exit 0 | No ids, exit 0 | One test failed, exit 1 | One test failed, exit 0 |
|---|---|---|---|---|
| human | passed | uncounted | failed | **passed** |
| tap | passed | passed | failed | failed |

The sentence was true when c700eb29aae866050bb6d83ab858de33f921e460 added it (2026-10-17). A week later
e074ccd3bcbf081b0591588b9cdab244efe508aa stopped the base run from running a command that tests a deployed
target, which was the only place a result could be "unread". The test that guards the card checks that the words
"refused as unread" are there, so the wording stayed while the behaviour left. The card's advice (use the other
format) is still right, for a reason it does not give: in the human format a failure behind a zero exit is marked
passed. **This is a finding about ShipLoop as released; nothing is changed here. It goes to the owner with the
recommendation.**

**What a trustworthy ingest would need** (the subagent's view after doing it once, which I share): a reviewer who
is not the ingester; the version at which each fact was seen (the entry form has no field for it, and one fact was
already ambiguous a month on); sources checked against raw records, not against reports; acceptance that "applies
when" often depends on code not yet written; and, for any claim about ShipLoop's own behaviour, a test of the
behaviour and not of the wording.

## 17. Rung 2: the knowledge home says "no guide" (2026-11-22, 10:54 to 11:00)

Four plan-stage slices, released build, the fixture whose `environment.md` says "Platform guide: none", the plain
request (`~/e2e-runs-pk/20261122/s09` to `s12`; readings `rung2-*.txt` beside rung 1's).

| Sample | Driver | Entries shown before the plan was submitted | How |
|---|---|---|---|
| s09 | Sol medium | 5 of 5 | `cat platforms/harbor.md` at 22 s |
| s11 | Sol medium | 5 of 5 | `cat .../platforms/harbor.md` with `coding-guidance.md` at 24 s |
| s10 | Sonnet medium | 0 of 5 | no call names the card |
| s12 | Sonnet medium | 5 of 5 | `cat .../platforms/harbor.md` at 13 s, after reading the knowledge home |

**By the rule of section 15:** Sol finds the card (both samples); Sonnet does not (one of two). **Prediction
("at most 1 of the 4 opens the card"): wrong, 3 of 4 did.**

**How they found it.** Each read "Platform guide: none" in the knowledge home and opened `platforms/harbor.md`
anyway, by the platform's name. The packet's list of guides shows another card's path
(`GUIDES/platforms/ui.md#...`), which gives the folder's naming away.

**Reading (interim), and a limit of this bench that I had not seen.** On a platform it does not know, a model goes
looking for the platform's file even when the project says there is none: 11 of the 12 slices of rungs 1 and 2
read the card with nothing printed. The saved runs say the opposite for platforms the models know: a card opened in
1 of 192 Terra runs, 5 of 58 Sol runs and 1 of 40 Sonnet runs (section 3). The reading that fits both: **a model
looks up what it knows it does not know, and does not look up what it believes it knows.** So this bench overstates
how often a card is picked up. What it still measures cleanly is what happens to facts once they are read. The
owner's example is a platform the models know; the facts that matter there are the ones a model does not know it
lacks, and for those the saved runs, not this bench, describe the pick-up.

## 18. Amendment 3, registered before any of its runs: the same question on platforms the models know (2026-11-22, 11:05)

**Hypothesis.** On a familiar platform, a fact in the card that the model does not know it lacks does not reach the
plan under released ShipLoop, and does reach it when the script prints the card's entries or when the request
states it.

**Cases** (being built on the candidate branch by an Opus subagent to my specification; nothing run yet). Two
platforms, Node with Express and Salesforce, each a small existing product with a knowledge home. Each real card
gets a `## Planning` section of three entries for the experiment only: two drawn from what the card already says,
and one hidden fact that nothing in the product or the request shows, carrying a token no model can guess
(`X-Org-Request-Id`, a header this deployment's gateway requires; `SLX_Feature_Access`, the permission set group
through which this org grants a new tab). Each request asks for a small feature that makes the hidden fact matter.

**Arms**, plan-stage slices as in rung 1, both drivers: **named** (released; the knowledge home names the card);
**none** (released; it says "Platform guide: none"); **printed** (named, with the entries printed by the candidate
route); **request** (none, with one sentence in the request that states the fact). One sample a cell first (16
slices), then a second (16).

**Readings, all by script.** Opened: a call names the card file. Shown: every line of the hidden entry was given
to the model before it submitted the plan. Reached the plan: the token is in the accepted plan result or in the
knowledge-home files the plan stage wrote. A token that cannot be guessed is a reading the earlier pattern scores
were not.

**Rule.** A route reaches the plan on a platform and driver when the token is there in both samples.

**Predictions.** none: the token in 0 of 8 samples. named: the card opened in at most 4 of 8. printed: the token in
at least 7 of 8. request: 8 of 8.

**What each outcome would mean.** If the named arm already reaches the plan, selecting the card is the only fix
needed and printing is not. If only the printed arm does, printing is what a familiar platform needs. If the
printed arm is shown the entry and the token still does not reach the plan, showing is not enough and the fact
needs a duty or a check of its own.

**Rung 3 launched at 11:05**, one sample a cell first (`harbor/runs/rung3a.tsv`, runs in
`~/e2e-runs-pk/20261122-d/`): d01 and d02 arm R, d03 and d04 arm F (the fixture with no knowledge home at all), d05
and d06 arm Q, each pair Sol then Sonnet. All six use one build, the candidate with its route off.
A first launch at 11:03 was refused by the harness before any host started: each of the twelve finished slices had
left its progress observer running, and the harness starts no host beside a run "whose harness is not running".
They were my own processes; the harness's own `lifecycle.py cleanup <folder>` stopped all twelve and deleted no
file, and the slice launcher now runs it after each sample. An apparatus lesson, not a ShipLoop one.

## 19. Rung 3, first sample of each cell: whole deliveries on the invented platform (2026-11-22, 11:05 to 11:31)

Six whole deliveries from the request to the end, released behaviour (the candidate build with its route off),
default planning review, each product graded by `harbor_grade.py` under the strict stand-in. Runs:
`~/e2e-runs-pk/20261122-d/d01` to `d06`; readings `harbor/readings/rung3a-grades.txt` and `rung3a-card-reads.txt`
on the candidate branch.

| Sample | Driver | Arm | Platform checks | Own tests | Card read | Name written at discovery | Minutes | Output tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| d01 | Sol medium | R, card named in the knowledge home | 6 of 6 | pass | whole, at discovery | already there | 9.3 | 20,958 | |
| d02 | Sonnet medium | R | 6 of 6 | pass | whole, at intake | already there | 25.9 | 203,977 | $9.48 |
| d03 | Sol medium | F, fresh repository | 6 of 6 | pass | whole, at discovery | **no** | 9.9 | 20,370 | |
| d04 | Sonnet medium | F | 6 of 6 | pass | whole, at discovery | yes | 21.4 | 164,760 | $7.74 |
| d05 | Sol medium | Q, rules in the request | 6 of 6 | pass | not opened | no | 7.9 | 16,805 | |
| d06 | Sonnet medium | Q | 6 of 6 | pass | not opened | no | 16.6 | 125,537 | $5.85 |

**By the rules of section 15** (one pair a driver so far, where the rules ask for two): the named card and the
fresh repository are each **as good as the request** on both drivers (6 against 6). R does **not** hold over F:
the fresh repository reached the same score, because the model found the card by itself.

**Predictions, scored as written.** "Q passes 6 of 6": right. "R at least 5": right. "F at most 2, because
discovery does not name the card": wrong, 6 and 6. Sol did not write the name and read the card anyway; Sonnet
wrote the name.

**What it shows (firm for this bench, one sample a cell).**

- **Once a card's facts are read they reach the product.** Four deliveries read the card and all four products
  follow all five rules, as well as the two whose request stated them. Nothing was lost between reading at
  discovery and the code, on either driver, with released ShipLoop.
- **On a platform it does not know, a model finds the card in a whole delivery too**, from a repository with no
  knowledge home, with no change to ShipLoop.
- **Stating the rules in the request is the cheapest route here**: 7.9 minutes against 9.3 and 9.9 on Sol, 16.6
  against 25.9 and 21.4 on Sonnet, $5.85 against $9.48 and $7.74. One sample a cell, so a lean, not a measure.
- **Sol still does not write the card's name** (d03), as in every saved run, and it cost nothing here.

**Enough to conclude on this bench?** Yes for what it can show: on an unfamiliar platform released ShipLoop needs no
change. The second sample of each cell is not run: six of six at the ceiling leaves no difference for a second
sample to confirm, and the open question is the other kind of platform (section 18). That is a departure from the
two samples registered, made after seeing the first six, and stated as such.

**Limits.** One sample a cell. A small product and one request. The platform is invented, which is exactly what
makes a model look it up.

## 20. Rung 4, first sample of each cell: launched 11:41 (2026-11-22)

The cases of section 18 are built and committed on the candidate branch as
8a703845d2e9c39fa8d078021efad4a3470f999b, and the 16 slices of `familiar/runs/rung4a.tsv` are launched from that
commit into `~/e2e-runs-pk/20261122-f/` (f01 to f16; `familiar/runs/arms.tsv` says which is which).

What was checked without a model before the launch: the two new `## Planning` sections and the four requests, read
by me; neither token is in any fixture or plain request; the plan packet of each "named" case with the route off
is the released packet, and with the route on the three entries stand before the result template (1,595 and 1,667
characters added).

Two things the readings must allow for, both known before any result:

- **The two platforms are not alike in the "named" arm.** The Salesforce card has a `## Testing` section, so the
  released packet already lists that card's file among its guides; the Node card has none, so only the knowledge
  home names it.
- **The hidden entries:** N-GATEWAY, "This deployment's gateway drops any response that lacks the header
  `X-Org-Request-Id`", and S-ACCESS-GROUP, "In this org a new tab or app reaches its users only through the
  permission set group `SLX_Feature_Access`". The Salesforce request asks for a tab for twelve dispatchers only, so
  a plan has to decide how they get access; the Node request asks for a new route.

## 21. Rung 4, first sample of each cell: on platforms the models know, only printing or the request gets the fact in (2026-11-22, 11:41 to 12:02)

Sixteen plan-stage slices (`~/e2e-runs-pk/20261122-f/f01` to `f16`), all ended by the harness at the plan's
acceptance. Read by `familiar/fact_reading.py`; its output is kept in `familiar/readings/rung4a-node.txt` and
`rung4a-sf.txt` on the candidate branch.

| Platform | Arm | Driver | Card opened by the model | Hidden entry shown | Token reached the plan |
|---|---|---|---|---|---|
| Node | none | Sol (f05) | no | no | no |
| Node | none | Sonnet (f02) | no | no | no |
| Node | named, released | Sol (f01) | no | no | no |
| Node | named, released | Sonnet (f14) | no | no | no |
| Node | printed | Sol (f09) | printed | yes | yes (in `architecture.md` and `spec.md`) |
| Node | printed | Sonnet (f06) | printed | yes | yes |
| Node | request | Sol (f13) | no | in the request | yes |
| Node | request | Sonnet (f10) | no | in the request | yes |
| Salesforce | none | Sol (f15) | no | no | no |
| Salesforce | none | Sonnet (f12) | no | no | no |
| Salesforce | named, released | Sol (f11) | no | no | no |
| Salesforce | named, released | Sonnet (f08) | **yes, three reads** | yes | **no** |
| Salesforce | printed | Sol (f03) | printed | yes | yes |
| Salesforce | printed | Sonnet (f16) | printed | yes | yes |
| Salesforce | request | Sol (f07) | no | in the request | yes |
| Salesforce | request | Sonnet (f04) | no | in the request | yes |

| Arm | Token reached the plan |
|---|---|
| The knowledge home says "none" | 0 of 4 |
| The card is named, released ShipLoop | 0 of 4 |
| The card is named and its entries are printed by the script | 4 of 4 |
| The fact is in the request | 4 of 4 |

**What the released plans did instead** (read by hand). f11 (Sol, Salesforce) plans a dedicated permission set
whose assignment the release owner settles: the org's rule is broken without anyone knowing. f14 (Sonnet, Node)
plans the route with no word about a request id. f08 is the instructive one: Sonnet opened the Salesforce card by
itself, saw the entry, and recorded it as an open assumption, "The org may route new tabs only through a permission
set group (platform guide S-ACCESS-GROUP); the group is not in this repo [...] W3 ships the permission set alone;
W4's hand-off asks the service team which route applies". It read the fact and chose not to act on it.

**Reading (interim until the second samples are in).**

- On a platform a model knows, naming the card in the knowledge home is not enough: the card was opened in 1 of 4
  released samples, against 4 of 4 on the invented platform. This is the saved runs' picture, now under control.
- The same entry, printed inside the plan duty with the sentence that asks for it to be used, was used in 4 of 4,
  as often as when the requester wrote the fact into the request.
- Being shown a fact and being asked to use it are different things (f08 against the four printed samples).
- A limit the f08 plan itself points at: both hidden facts are about one deployment ("in this org", "this
  deployment's gateway"), written into a platform card so that no model could guess them. A fact about one
  project's target belongs in that project's `environment.md` (section 7), and a model that doubts such a line in a
  general card is not wrong. The test measures whether a route carries a fact, not where the fact should live.

**Predictions so far** (they are for 8 samples; these are the first 4 of each): none 0 of 4, as predicted; the named
card opened in 1 of 4, within "at most half"; printed 4 of 4 and request 4 of 4, as predicted.

The second sample of every cell (`familiar/runs/rung4b.tsv`, f17 to f32) was launched at 12:03.

## 22. Amendment 4, registered before any of its runs: a look-up line, and the whole chain end to end (2026-11-22, 12:04)

Two questions remain that a model has to answer, and one that a script answers.

**Rung 4L: is a pointer enough when it stands where the printed entries stand?** This is the owner's wiki idea in
its strongest form: no text in the packet, one line in the plan duty that names the card's file and the lines of its
`## Planning` section, with the same sentence. The route exists (`route-lookup.json`); on the invented platform it
could show nothing, because everything was read there anyway. Cases: the two "named" fixtures of rung 4, both
drivers, 2 samples a cell = 8 slices. Readings and rule as in section 18. Predictions: the hidden entry is shown in
at least 6 of 8 and the token reaches the plan in at least 5 of 8. If it does as well as printing, a reference can
grow into pages that a line points into, at the price of one read a section; if it does worse, printing is the
route.

**Rung 6: the whole chain on a familiar platform, with nothing seeded.** Rung 4 put the card's name in the knowledge
home by hand, and no Sol, Terra or Sonnet run has ever written it. So the candidate gets one more piece: a card
declares what makes it apply (a list of files, as a card already declares its remote test commands), and the script
selects a card whose files are in the repository, with no judgment by a model. Whole deliveries from a fresh
repository with no knowledge home, on a small Node service that needs no package installed, the request without
the fact: the released build against the candidate (selection by declared files, entries printed at the plan
stage), both drivers, one sample a cell = 4 deliveries. Reading, by script: is the token in the delivered product's
source, and was the entry in the plan packet. Rule: the chain **holds** on a driver when the candidate's product
holds the token and the released one's does not. Predictions: released 0 of 2; candidate 2 of 2.

**Not run, and why.** Rung 5 (the reference at wiki size): when a script selects entries by key, what the model is
given does not depend on how large the reference is, so there is nothing for a model run to measure; and a
reference the model has to go and search is the route rungs 2 and 4 show working only on a platform the model does
not know. A Ratchet cell: its stage texts are prompts, so entries added to its plan text arrive as the "request"
and "printed" arms arrived here; it is described in the recommendation and marked as not run.

## 23. Rung 4, both samples: the result on familiar platforms (2026-11-22, 11:41 to 12:23; firm)

Thirty-two plan-stage slices (f01 to f32), two samples of each of sixteen cells. Readings:
`familiar/readings/rung4a-*.txt` and `rung4b-*.txt` on the candidate branch.

| Arm | Card opened by the model | Hidden entry shown | Token in the plan (the registered reading) | Fact followed (read by hand) |
|---|---|---|---|---|
| The knowledge home says "none" | 0 of 8 | 0 of 8 | 0 of 8 | 0 of 8 |
| The card is named, released ShipLoop | 3 of 8 | 3 of 8 | 1 of 8 | 0 of 8 |
| The card is named and its entries are printed in the plan duty | (printed) | 8 of 8 | 7 of 8 | 8 of 8 |
| The fact is in the request | 0 of 8 | (in the request) | 8 of 8 | 8 of 8 |

**By the rule of section 18** (the token in both samples of a platform and driver): the request arm reaches the
plan in all four cells; the printed arm in three of four (Sol on Salesforce has it in one sample of two); the named
arm and the "none" arm in none.

**Predictions, all four right this time:** none 0 of 8; the named card opened in at most half (3 of 8); printed at
least 7 of 8 (7); request 8 of 8.

**The hand reading, where it differs from the token.**

- *Named, token present, fact declined* (f25, Sonnet, Salesforce): "The org's permission set group
  SLX_Feature_Access (platform guide S-ACCESS-GROUP) is not evidenced for this org, so the project does not touch
  it; a dedicated permission set is used and assigned to the twelve by the service team". With f08 that is twice
  that Sonnet read the fact in the card by itself and decided against it.
- *Printed, token absent, fact followed* (f22, Sol, Salesforce): the security row's decision reads "Group, custom
  permission, CRUD/FLS and sharing". Sol's short form again, and the reason the registered count is 7 and not 8.
- *Printed, and better than obedient* (f16 and f17, Sonnet, Salesforce): both use the group and open the point the
  entry and the request leave between them, "SLX_Feature_Access is not shared with non-dispatchers [...] service
  team confirms membership". The request asked that only twelve dispatchers get the tab.

**The card was opened only where the packet also listed it.** All three opens in the named arm are on Salesforce,
where the released packet lists the card's Testing section among its guides; on Node, where only the knowledge
home names the card, none of four. And an open is not a use: 3 opens, the fact followed in none.

**What it establishes.**

1. On a platform a model knows, a fact that sits in the card reaches the plan when the script prints it inside the
   duty that needs it, and not when the card is merely named or linked. Printed and request are level; named and
   absent are level.
2. The sentence and the place matter, not only the text: the same entry read in the card was doubted and declined,
   and printed in the duty with "use them in the decisions and proving checks this plan already owes" it was used,
   twice with the right open question attached.
3. This is the mechanism behind section 11: the saved Salesforce deliveries went well because the requester wrote
   the facts into the request. Printing a card's entries does the same work without the requester writing them.

**Limits.** A plan-stage slice with the card's name put in the knowledge home by hand: selection is not tested here
(rung 6 is for that). One hidden fact a platform, about one deployment, in a general card. Two samples a cell. The
plan's review was off. Whether a fact that reaches the plan this way reaches the product on a familiar platform is
shown only for the invented one (section 19) until rung 6 is read.

## 24. Rung 4L: one line that points to the section, in the place of the printed entries (2026-11-22, 12:23 to 12:36)

Eight plan-stage slices on the two "named" fixtures of rung 4 with the look-up route (`~/e2e-runs-pk/20261122-g/g01`
to `g08`, launched from a frozen checkout of the candidate commit so that work on the branch could not reach
them). The packet holds no entry. Inside the plan duty stands one line: "Platform planning facts: read
<the card's file>#planning (lines a-b) before the concern rows; use them in the decisions and proving checks this
plan already owes."

| Platform | Driver | Section read before the plan was submitted | Token in the plan | Fact followed (read by hand) |
|---|---|---|---|---|
| Node | Sol (g01, g05) | yes, yes | yes, yes | yes, yes |
| Node | Sonnet (g04, g08) | yes, yes | yes, yes | yes, yes |
| Salesforce | Sonnet (g02, g06) | yes, yes | yes, yes | yes, yes |
| Salesforce | Sol (g03, g07) | yes, yes | no, no | yes, yes ("restricted group assignment"; "permission-group membership") |

**Predictions:** the entry shown in at least 6 of 8: right (8). The token in at least 5 of 8: right (6; by hand the
fact is followed in all 8, the two without the token being Sol's short form again).

**So a pointer is enough, when the script puts it inside the duty, names the exact section and asks for its use.**
It was followed in 8 of 8, where a card that is only named in the knowledge home was followed in 0 of 8 (section
23). The owner's condition for a wiki ("requires key identifiers and pointers in order to pick up the other items")
is met by a pointer the script chooses and places, and not by one the model has to find.

**What it costs against printing.** Not measured in characters by the reader. From the calls, read again after the
second review: Sonnet read the lines it was pointed to in all four of its samples (`sed -n` with the range, ending
`,40p .../node-express.md` and `108p .../salesforce.md`); Sol read the range in one sample and searched or printed
more of the card in the others. So a pointer costs the packet about 300 characters and the context about what the
printed entries cost, plus one call.
*Corrected 2026-11-22 after the second review (section 29):* I first wrote that Sonnet "read the whole card file in
all four of its samples" and drew from it that a pointer can cost more context than printing. That was read from
call excerpts cut to the end of each command, where the card's path stands; the commands are range reads. The
conclusion I drew from it is withdrawn, and the owner was told.

## 25. Rung 6 launched: the whole chain on a familiar platform, nothing seeded (2026-11-22, 13:01)

The last piece of the candidate is built and committed on the candidate branch as
e1b2ad72284c298cc1254ca2a78b53b6aa580b35: a second switch, `PLATFORM_SELECT_ROUTE`, default "named" (released
behaviour). With "declared", `platform_cards()` also returns every card whose `## Applies when` section lists a
file pattern that matches a file of the product repository, so a card is selected with no model and with no
knowledge home. The Opus subagent that built it reports 8 new contract tests (all erroring before the change), the
navigator contract suite, the domain-words suite and the quick tier (84 suites) passing with both switches at
their defaults; I checked that the prepared builds select as intended (`platform_cards()` returns the Node card for
the fresh repository with the candidate build and nothing with the released one).

The case: `pk-nodeplain`, the parts-catalog service with no installed package and no `docs/shiploop/` at all; the
request of rung 4 unchanged (64 words, no word about a request id). Four whole deliveries in
`~/e2e-runs-pk/20261122-n/`: n01 Sol released, n02 Sonnet candidate, n03 Sol candidate, n04 Sonnet released
(`familiar/runs/rung6.tsv`). Readings, by script: `product_token.py` (the token in the delivered source, tests and
knowledge home; the entry in a plan packet) and `header_check.js`, which starts the delivered service and asks
the new route once validly and once so that it must answer 400; calibrated on a product with the header (passes
both), one without (fails both) and the untouched fixture (route missing).

Known before any result: the experiment's pattern for the Node card is `package.json`, far too wide for real use;
and the printed entries include two real ones (authorization, shared state) that a model may act on in ways the
header check does not expect.

## 26. Rung 6: the whole chain holds on Sonnet and breaks on Sol at one identified step (2026-11-22, 13:01 to 13:17)

Four whole deliveries from the fresh Node repository (`~/e2e-runs-pk/20261122-n/n01` to `n04`), launched from the
candidate commit e1b2ad72284c298cc1254ca2a78b53b6aa580b35. Readings: `product_token.py` and `header_check.js`
(their output is kept as `familiar/readings/rung6-product-token.txt` and `rung6-header-check.txt` on the candidate
branch).

| Sample | Driver | Build | Card selected by the script | Entry in the plan packet | Entry shown to the model at plan | Token in the product (source / tests / knowledge home) | Header check | Minutes | Cost |
|---|---|---|---|---|---|---|---|---|---|
| n01 | Sol medium | released | no | no | no | 0 / 0 / 0 | fails | 10.0 | |
| n04 | Sonnet medium | released | no | no | no | 0 / 0 / 0 | fails | 15.9 | $5.19 |
| n02 | Sonnet medium | candidate | yes | yes | **yes** | 3 / 14 / 12 | **passes** | 16.4 | $5.94 |
| n03 | Sol medium | candidate | yes | yes | **no** | 0 / 0 / 0 | fails | 10.1 | |

**By the rule of section 22:** the chain holds on Sonnet and does not hold on Sol. **Predictions:** "released 0 of
2" right; "candidate 2 of 2" wrong, 1 of 2.

**Selection worked as built, with no model.** In both candidate runs the script selected the Node card from the
repository's files and printed the three entries in the plan packet, although the repository had no knowledge home
and neither model ever named the card (neither delivered `environment.md` names it at the end).

**Where it broke on Sol, read from the Codex session record.** The plan packet of n03 is 284 lines; the block
stands at lines 35 to 52. The model showed itself 42 of the packet's 162 instruction lines (lines 1 to 11, 14, 17
and 18, 24, 28, 55, 63, 66 to 68 and scattered others) and none of the block's 18 lines. So the fact was printed
and never read. This is the behaviour of section 8 (the plan packet shown at under a third in 4 of 26 saved Sol
runs) met in a live run. In the plan-stage slices of rung 4 Sol was shown the block 4 of 4: there the plan packet
was the session's first packet.

**What Sol does read in a whole delivery.** In both Sol runs of this rung the intake packet (77 of 77 instruction
lines) and the discovery packet (93 of 93) were shown whole; research, spec, test-strategy and plan were shown at
34 to 135 lines of 59 to 162, differently in the two runs (n01 was shown 135 of 147 plan lines, n03 42 of 162). In
the 50 saved Sol runs intake was shown whole in 50 and discovery at four fifths or more in 46.

**Cost of the candidate on the driver where it worked:** 16.4 minutes and $5.94 against 15.9 and $5.19 for the
released build, one sample each: no difference this can show.

**Reading (interim).** Printing in the plan packet is the right content in the wrong place for a Codex model in a
whole delivery. Two places are read: the first packets, and a refusal. The first is cheaper to try.

## 27. Amendment 5, registered before its runs: the entries printed at discovery (2026-11-22, 13:19)

**Rung 6b.** The same candidate with one more switch: the entries are printed at the discovery stage as well as at
the plan stage, inside the discovery duty that asks for the knowledge home's record, with the sentence "record each
one that bears on this request under KNOWLEDGE/environment.md ## Platform facts, with its decision and its proof,
so the spec and the plan can use it". That puts the fact in a packet a Codex model reads whole, and writes it into
the project's own knowledge home, the place section 7 names for what is true of one project's target. Selection
stays by the card's declared files. Whole deliveries from the same fresh repository: two on Sol medium, one on
Sonnet medium (n05, n06, n07). Readings as in rung 6.

**Rule.** The chain **holds** on Sol when both Sol products pass the header check. **Predictions:** the entry is
shown to the model at discovery in 3 of 3; the header check passes in at least 2 of 3, both Sol runs among them or
one of them.

If it holds, the place for a card's planning entries is discovery, with the plan stage as a second showing. If the
entry is shown at discovery and the product still lacks the header on Sol, the remaining route is a check: the
script refuses a plan that does not account for each printed entry.

**Rung 6b launched at 13:32.** The switch is built by an Opus subagent and committed on the candidate branch as
2e4aecc1efe0c4a093b6eba80c810b206cab6a0d (6 new contract tests, all erroring before the change; the navigator
contract suite, domain-words and the quick tier for the change pass with every switch at its default). Without a
model: the discovery packet of a fresh run on the prepared repository goes from 17,769 to 19,458 characters; the
block is lines 33 to 47, well before "Result template:" at line 117, and is the only difference. Runs n05 and n06
(Sol medium) and n07 (Sonnet medium) in `~/e2e-runs-pk/20261122-n/`, allocation `familiar/runs/rung6b.tsv`.

## 28. Rung 6b: printed at discovery, the whole chain holds on both drivers (2026-11-22, 13:32 to 13:54)

Three whole deliveries from the fresh Node repository with the candidate at
2e4aecc1efe0c4a093b6eba80c810b206cab6a0d: the card selected by its declared files, its entries printed at
discovery and at plan. Runs n05 to n07 beside rung 6's; readings `familiar/readings/rung6b-product-token.txt` and
`rung6b-header-check.txt` on the candidate branch.

| Sample | Driver | Block shown at discovery | Discovery packet shown | Token in the product (source / tests / knowledge home) | Header check, valid call | Header check, 400 path | Minutes | Cost |
|---|---|---|---|---|---|---|---|---|
| n05 | Sol medium | 15 of 15 lines | 108 of 108 instruction lines | 2 / 8 / 1 | header, id echoed | header | 12.1 | |
| n06 | Sol medium | 15 of 15 | 108 of 108 | 1 / 4 / 2 | header, id echoed | header | 9.5 | |
| n07 | Sonnet medium | 15 of 15 | 108 of 108 | 1 / 18 / 12 | header, id echoed | header | 21.7 | $7.95 |

**By the rule of section 27:** the chain holds on Sol (both Sol products pass) and on Sonnet. **Predictions:** shown
at discovery in 3 of 3: right. The header check passes in at least 2 of 3: right, 3 of 3.

Against rung 6: with the entries at the plan stage only, Sol's product failed the check (0 of 1) and Sonnet's
passed (1 of 1); with the entries at discovery too, 3 of 3 pass; with the released build, 0 of 2.

**What was not asked for and happened anyway.** n06 read the plan packet at 64 of 162 instruction lines, as n03
did, and its product still carries the header.
*Qualified 2026-11-22 after the second review (section 29):* I first added "the fact was already in the session
from discovery". That is one explanation of three. This arm prints at discovery and at plan; n06 also read lines
of the card by a call of its own; and the reader's "given" test is over the whole session. Which showing did the
work is not separated by this rung. And only two
of the three knowledge homes hold the token in `environment.md`, where the lead line asks for it; the third (n05)
carries it in the other knowledge files. The record in the project's own file is therefore likely, not certain.

**Time and cost.** Sol 12.1 and 9.5 minutes against 10.0 released; Sonnet 21.7 minutes and $7.95 against 15.9 and
$5.19 released and 16.4 and $5.94 with the plan-only candidate. One or two samples a cell: no difference this can
show, and the Sonnet figure is one run.

**Limits.** Three deliveries, one small service, one request, one hidden fact. The selecting pattern is
`package.json`, which a real card could not use. The two real entries printed beside the hidden one (authorization,
shared state) were not graded: whether printing them changed those deliveries for better or worse is not read here.

**The owner, about 14:00, after rung 6b:** "I'm looking to optimize for Sol and for Sonnet. I don't need optimization
for Grok." Every live run of this study was on Sol 6.2 medium or Sonnet 5.5 medium; Grok appears only in the count
of saved runs (section 3), as the one family that names and reads cards by itself. The recommendation is therefore
judged on those two drivers alone, and nothing is kept or added for Grok's sake.

## 29. The second Sol max review, on the results and on the change I was about to recommend (2026-11-22, sent 13:56, returned 14:05)

Asked of `gpt-6.2-sol` at max, read-only, on a neutral copy of this journal through section 28, the candidate
applied to ShipLoop with its diff, the benches and every reading. Served as asked, no fallback. Question:
`review/QUESTION-2.md`; answer, word for word: `review/sol-max-answer-2.md` (3,200 words).

**Its verdict, in its words.** "Keep the ShipLoop runtime candidate off `main`. Correct the Salesforce reporter
guidance and test the judge behavior in a separate change. The experiments show that a precise duty can carry a
planted deployment fact into a plan and, on one Node fixture, into a product. Rung 6b makes discovery a promising
delivery point. Cold handoff, correct selection, and decision quality remain open. Run a paired cold-handoff test
against the existing project-knowledge route before deciding whether ShipLoop needs a change."

**Corrections it made, each checked before it was accepted.**

1. *Section 24, the look-up's cost:* my claim that Sonnet read the whole card was wrong. Checked in the runs'
   event streams and corrected in place above.
2. *Section 28:* three routes could explain the three passes; my sentence attributing n06's pass to discovery is
   qualified in place above.
3. *Section 23, the hand reading:* the credits I gave to f22 (and, in section 24, to g03 and g07) rest on the word
   "group" without the group's name. They show a direction, not a commitment to the fact. The registered token
   counts stand as the reading of record: 0, 1, 7 and 8 of 8 for none, named, printed and request, and 6 of 8 for
   the look-up.
4. *What rung 4 isolates:* placement, content and the sentence asking for use were changed together. "Putting the
   same claim inside a duty may give it more weight as well as more visibility." And the Sonnet plan that asked for
   evidence before changing access "was exercising sound judgment". A printed entry is obeyed; so a wrong or stale
   entry would be obeyed too, and section 16 shows a card going stale within a week.

**On the change itself.**

- Selection as built is not fit for a product: it loses which target a card belongs to, a reasoned "none" cannot
  override a file match, it matches untracked files, the same selection also feeds the testing link, and the
  pattern used here selects the Express card for a service that does not use Express. A card should declare
  positive conditions over bounded evidence (a runtime dependency and evidence that the affected service starts
  through it), attached to the package and target they were found in.
- Discovery plus plan is not a design for a host that clears context: spec and test-strategy sit between them,
  nothing hands a discovery fact to spec by value, and "a recorded fact is retrievable; receipt at the next decision
  still needs evidence". Put the fact at the first decision that needs it and then carry the decision, in the
  records ShipLoop already has (a requirement, an architecture decision, a check).
- No result field, no refusal and no new stage: a field rewards copying, a refusal turns uncertain applicability
  into a retry, and a token match would have accepted the plan that named the group only to decline it.
- The stale sentence in the Salesforce card is confirmed from the source and should be corrected on its own, with a
  test of the judging behaviour.

**The experiment it asks for, and the gap in mine that it names.** I registered the project's own knowledge file as
a route (arm K, section 10), dropped it in amendment 2 because on the invented platform every route was read, and
never ran it on the platforms the models know. So the study cannot yet say whether released ShipLoop already
carries a fact that is written in the project's `docs/shiploop/environment.md`. If it does, no runtime change is
needed for facts of that kind.

**Not followed, and why.** It asks for the Ratchet cell to be run; it stays not run today, and the recommendation
will say so. It asks for cold-handoff sessions stage by stage; the first form run here is cheaper (section 30) and
the stage-by-stage form is named as the next step if that leaves the question open.

## 30. Amendment 6, registered before its runs: the project's own knowledge file, on the platforms the models know (2026-11-22, 14:07)

**Rung 7a, plan stage.** Arm K on the two familiar fixtures: the knowledge home says "Platform guide: none" and its
`## Platform facts` section states the hidden fact as a fact observed for this project's target, with where it was
observed; no card entry is printed; released behaviour. Plan-stage slices as in rung 4, both drivers, two samples
a cell = 8. Reading: the token in the accepted plan or in the knowledge files the plan stage wrote (the registered
reading), and by hand whether the fact is followed or declined. Prediction: the token reaches the plan in at least
6 of 8.

**Rung 7b, whole deliveries.** The Node repository of rung 6 with a knowledge home whose `environment.md` holds
the same fact under `## Platform facts`; the released build; two deliveries on Sol medium and one on Sonnet medium.
Reading: the product check, tightened as the review asks (the header on the valid call and on the 400 path, the
sent id echoed, an id generated when none is sent, the existing routes still answering as before). Rule: the
existing route **holds** on Sol when both Sol products pass. Prediction: at least 2 of 3 pass.

**A free reading alongside:** what the candidate's deliveries did beyond the hidden fact (n02, n05, n06, n07
against n01, n04): which files changed, whether the header was put on every route or on the new one, whether
anything was added for the two real entries (authorization, shared state), whether the original tests still pass.

**What each outcome would mean.** If the existing route holds, a fact that belongs to one project needs no change
to ShipLoop: it needs to be written in that project's knowledge file, and the question becomes how a platform's
reusable facts get there. If it fails where the printed arm passed, printing earns its place and the next step is
the stage-by-stage cold test the review describes.

## 31. The free reading of section 30, and rung 7 launched (2026-11-22, 14:23)

Built by an Opus subagent to my brief and committed on the candidate branch as
6c3e9f9f7c9c4d5eb8d7636d4be6bd943c8dfa3e (no file under `skills/` changes): the fixtures of rung 7, each differing
from its base only in the knowledge home; `familiar/contract_check.js`, the tightened product check; and
`familiar/scope_reading.py`. The two readings below are of the seven deliveries of rungs 6 and 6b
(`familiar/readings/contract-rung6.txt` and `scope-rung6.txt`).

**The tightened check agrees with the first one.** Calibration: the reference product with the header passes all
four parts (the sent id echoed; an id generated when none is sent; the 400 path; the 18 requests of the untouched
service answering as before); the reference without it fails the three header parts and passes the fourth; the
untouched service is reported as missing the route.

| Deliveries | Echo | Generated id | 400 path | Existing routes unchanged | Header on the existing routes too |
|---|---|---|---|---|---|
| n01, n04 (released), n03 (Sol, plan-only candidate) | fail | fail | fail | pass | no |
| n05, n06 (Sol, candidate with discovery) | pass | pass | pass | pass | no: the new route only |
| n02, n07 (Sonnet, candidate) | pass | pass | pass | pass | yes: every route |

**What the candidate's deliveries did beyond the hidden fact.** Every one of the seven changed `src/app.js`, added
`src/routes/stock.js` and touched no other existing source file; the service's original seven tests pass against
all seven products; none added authorization or shared-state code. So the two real entries printed beside the
hidden one led to no extra work here. One difference of scope: the entry asks for the header on "every response of
a new or changed route"; Sol put it on the new route, Sonnet on every route of the service. Neither breaks the
check; the wider reading is more than was asked.

**Rung 7 launched at 14:23**: `familiar/runs/rung7a.tsv`, eight plan-stage slices in `~/e2e-runs-pk/20261122-k/`
(k01 to k08), and `familiar/runs/rung7b.tsv`, three whole deliveries in `~/e2e-runs-pk/20261122-n/` (k11 and k12 on
Sol, k13 on Sonnet), all on the released route (the candidate build with every switch at its default), the fact
written in the product's own `docs/shiploop/environment.md` under `## Platform facts`.

## 32. Rung 7a: the fact in the project's own knowledge file reaches the plan with released ShipLoop (2026-11-22, 14:23 to 14:36)

Eight plan-stage slices (`~/e2e-runs-pk/20261122-k/k01` to `k08`), released behaviour: no card named, nothing
printed by the script, the hidden fact written as one bullet under `## Platform facts` in the product's
`docs/shiploop/environment.md`. Readings `familiar/readings/rung7a-node.txt` and `rung7a-sf.txt` on the candidate
branch. The token is in the fixture's `environment.md` by construction, so the reading counts it only in the
accepted plan result and in the `architecture.md` and `spec.md` the plan stage wrote.

| Platform | Driver | Token in the plan, `architecture.md` or `spec.md` | What the plan does with it (read by hand) |
|---|---|---|---|
| Node | Sol (k01, k08) | yes, yes | "Echo or generate X-Org-Request-Id on success and error"; a requirement in the spec |
| Node | Sonnet (k04, k05) | yes, yes | sets the header; one records "gateway not reachable from repo" as a check owed after deploy |
| Salesforce | Sol (k03, k06) | yes, yes | "group-only grant [...] Apply an additive change to the current `SLX_Feature_Access` source only after the admin confirms its effective roster" |
| Salesforce | Sonnet (k02, k07) | yes, yes | k02 uses the group and opens its membership; k07 keeps the org's rule (a group, never a direct assignment) but makes a new group and leaves the named one alone, "rejected until its membership is known", because the request says only twelve dispatchers |

**Prediction ("at least 6 of 8"): right, 8 of 8.**

*Added 2026-11-22 16:17 (the third review, checked in the two readings): the 8 of 8 is the registered union. By
part, the token is in the accepted plan result in 5 of 8, in `architecture.md` in 7 of 8 and in `spec.md` in 1 of 8.*

**This is the route the study had not run where it matters, and it works at the plan stage without any change to
ShipLoop.** Against section 23: the card only named 0 to 1 of 8; the entries printed 7 of 8; the fact in the
request 8 of 8; the fact in the project's knowledge file 8 of 8.

**And the plans are better for it, not only compliant.** Read as the project's own observation, the fact was
neither doubted (as in the card that was merely read, f08 and f25) nor simply obeyed: five of the eight plans say
what has to be confirmed before acting on it, and k07 found the one real conflict the planted fact has with the
request. That is the authority the second review said a printed card entry lacks.

**Limits.** A slice starts cold at the plan stage, and the first thing a model does there is read the knowledge
home; rung 7b asks whether the same holds through a whole delivery. Two samples a cell. The bullet states where
the fact was observed, which a real project's file may not.

## 33. Rung 7b: three whole deliveries with released ShipLoop and the fact in the project's knowledge file: all three products pass (2026-11-22, 14:23 to 14:41)

Runs `~/e2e-runs-pk/20261122-n/k11` and `k12` (Sol medium) and `k13` (Sonnet medium): the Node service of rung 6
with a knowledge home whose `environment.md` states the hidden fact as one bullet under `## Platform facts`; the
released route (the candidate build with every switch at its default); the request of rung 6, which names no
header. Readings on the candidate branch: `familiar/readings/contract-rung7b.txt` (the tightened check of section
31) and `rung7b-product-token.txt`.

| Run | Driver | ShipLoop | Minutes | Output tokens | Sent id echoed | Id generated | 400 path | The 18 existing answers unchanged | Existing routes carrying the header | Plan packet held the entry | Card opened |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k11 | Sol | done | 9.9 | 19,771 | pass | pass | pass | pass | none | no | never |
| k12 | Sol | done | 11.1 | 23,511 | pass | pass | pass | pass | none | no | never |
| k13 | Sonnet | done | 17.4 | 124,662 ($6.83) | pass | pass | pass | pass | all 18 | no | never |

**Rule ("the existing route holds on Sol when both Sol products pass"): it holds. Prediction ("at least 2 of 3
pass"): right, 3 of 3.**

**The whole chain on this service, every arm run today** (products that pass the check, of deliveries run):

| Where the fact is | Sol | Sonnet |
|---|---|---|
| Only in the platform card, released ShipLoop (n01, n04) | 0 of 1 | 0 of 1 |
| The card's entries printed in the plan duty, candidate (n03, n02) | 0 of 1 | 1 of 1 |
| Printed at discovery and at plan, candidate (n05, n06, n07) | 2 of 2 | 1 of 1 |
| In the project's own knowledge file, released ShipLoop (k11, k12, k13) | 2 of 2 | 1 of 1 |

**How the fact travelled, read in the session records.** Each of the three sessions printed `docs/shiploop/*.md`
to itself within twelve seconds of its start (start 22:23:15Z; k13 at 22:23:24Z, k12 at 22:23:26Z, k11 at
22:23:27Z), before its first stage result, and nobody asked it to by name: the knowledge home is where a delivery
begins. Each then wrote the fact into the spec as a requirement (k11: "Every response for GET /stock, including
400 and 500 errors, carries X-Org-Request-Id"; k13: "R-6 Every /stock answer carries X-Org-Request-Id. Basis:
environment.md Platform facts"). From there it was a requirement like any other: a test (TC-3 in both Sol
products), the code, the README. No plan packet held the entry, and no session opened the platform card. This is
what the second review asked a design to do ("put the fact at the first decision that needs it and then carry the
decision in the records ShipLoop already has"), and the released route already does it.

**No extra time shows in three deliveries** (first written as "It costs nothing extra", which three runs cannot
carry; corrected 2026-11-22 16:17). Sol took 9.9 and 11.1 minutes (10.0 and 10.1 in rung 6, 12.1 and 9.5 in rung 6b);
Sonnet 17.4 minutes and $6.83 (16.4 and 15.9 minutes in rung 6, 21.7 in rung 6b).

**Scope, as in section 31.** Sol put the header on the new route only; Sonnet put it on every route, and added a
case to the existing test file for it. The bullet says both things ("the platform team confirms it applies to
every route"; "every response of a new or changed route [...] must carry it"), so each reading has its sentence.
Neither breaks the check.

**The knowledge file is kept up by the deliveries themselves.** k12 and k13 each added a bullet to
`## Platform facts` (who owns the gateway's log; what the service logs and does not), unasked.

**Limits.** One repository, one fact, one Sonnet sample. The knowledge home was written by me, as an earlier
delivery would have left it, and its `## Platform facts` holds four bullets: a platform's key considerations are
dozens (rung 8, section 34, asks about that). And this route presupposes the file: the first delivery in a
repository with no knowledge home has none, and that is the fresh repository of rung 6, 0 of 2. So "how do a
platform's facts get into the project's file" stays open.

## 34. Amendment 7, registered before its runs: a long list against an index with pages (2026-11-22, 14:45)

*Time corrected 2026-11-22: this heading first said 14:50, a guess. The section was written at 14:45 and
committed at 14:47 (fe7be8b19d15059b5401c5fd8d0bc4f9f8da9343), before any of its runs.*

**Why one more rung before concluding.** The route that works has been run with four bullets. The owner's
reference is a platform's key considerations, and his two worries were about size and shape: "I wonder if the wiki
style would pollute context less, but requires key identifiers and pointers in order to pick up the other items. I
worry the file cannot be loaded in context". This is the case most likely to break section 33's reading, so it
runs before the conclusion, and it runs both shapes on the route that works.

**The two shapes**, on the Salesforce plan-stage case of rung 7a (released behaviour, no card named, nothing
printed by the script). Both hold the same facts; an Opus subagent builds them from one source so they cannot
drift, and a script proves the two sets identical:

- **L, the long list.** `## Platform facts` holds the three code bullets and then 36 to 44 real statements of the
  Salesforce card restated as facts of this project's platform (nothing invented, the card not named), with the
  hidden bullet of rung 7a, unchanged, in the middle of them.
- **X, the index with pages.** `## Platform facts` holds the three code bullets and a short index: one sentence
  ("This org's platform facts are kept as pages under docs/shiploop/platform/, one topic a page. Before a decision
  that touches a topic, read its page:") and one line a page saying what the page covers and stating no fact. The
  same facts are on six to eight topic pages; the hidden bullet is in the middle of `access.md`, and its token is
  nowhere else in the repository.

**Baseline:** rung 7a's Salesforce cell, four bullets: 4 of 4.

**Runs.** Eight plan-stage slices, `familiar/runs/rung8.tsv`, in `~/e2e-runs-pk/20261122-m/` (m01 to m08): each
shape twice on Sol medium and twice on Sonnet medium.

**Readings**, by `familiar/knowledge_reading.py`, calibrated on rung 7a's four Salesforce slices before use. Of
record: the token in the accepted plan, or in the `architecture.md` or `spec.md` the plan stage wrote (the reading
of rung 7a, by the same code). Beside it: whether every line of the hidden bullet was given to the model before
the plan was submitted (for Sol, read in the session record, never in the event stream); which pages a command or a
read named; and the characters of knowledge text given (the Platform facts section plus the pages), which is the
context cost this rung compares.

**Rules.** A shape **holds** when the token reaches the plan in at least 3 of its 4 slices; it **holds on a
driver** when it does in both of that driver's slices.

**Predictions.** L: the bullet is given in 4 of 4 and the token reaches the plan in at least 3 of 4. X: `access.md`
is opened in at least 3 of 4 and the token reaches the plan in at least 2 of 4. X gives the model under 60% of the
knowledge characters L gives.

**What each outcome would mean.**

- L holds on both drivers: at this size (about forty facts) one section of the project's knowledge file is enough.
  No wiki, no skill and no script is needed to deliver the facts; the pages are an option when the cost matters,
  with the saving as measured.
- L fails on a driver and X holds on it: the wiki shape earns its place, as an index in the knowledge file with
  pages beside it.
- Both fail on a driver: the list a delivery reads must be short and chosen for the project, and the open question
  is who chooses.

**Limits known before the run.** The plan stage only, started cold; a whole delivery meets the knowledge home in
its first seconds (section 33), not at the plan. One platform, one request, one list, two samples a cell. The
hidden fact is the only one of the list the request cannot be done right without, so this measures finding one
needed fact among many, not using many.

## 35. A free reading, and amendment 8 registered before its runs: a starter file in a brand-new repository (2026-11-22, 14:51)

**The free reading: what a first delivery writes down.** Section 33's route presupposes the knowledge file. The
three deliveries of rung 6b started with none and were shown the card's entries by the candidate at discovery; each
wrote a knowledge home. What its `## Platform facts` says of the hidden fact, read by hand
(`~/e2e-runs-pk/20261122-n/n05` to `n07`, `work/docs/shiploop/environment.md`):

| Run | Driver | What it wrote |
|---|---|---|
| n05 | Sol | "ShipLoop's Node platform guide specifies a gateway request ID for new routes. Implement and test the stock response header locally as specified by AD-2. The deployed gateway configuration remains unverified." The header's name is in `architecture.md`, not here. |
| n06 | Sol | "Match the platform guide's N-GATEWAY requirement with `X-Org-Request-Id` on stock responses, verified by HTTP success and error cases. The production gateway itself remains unobserved." |
| n07 | Sonnet | "**N-GATEWAY** (from the platform guide, not observed in this repository): the guide says this deployment's gateway drops any response lacking `X-Org-Request-Id`. [...] Owner to confirm the gateway rule." |

Two things show. All three kept the provenance honest: from the guide, not observed here. And both Sol deliveries
wrote down their own decision for this piece of work ("for new routes", "on stock responses"), not the platform's
rule; only Sonnet kept the rule. So a first delivery that is shown a card does not reliably leave the card's fact
behind for the next delivery. Not tested: a second delivery on those products. Exploratory: three files, read by
hand.

**Amendment 8, rung 9: the simplest way a platform's facts could reach a new project is to copy them in.** The
starting repository is the fresh one of rung 6 (no knowledge home; the released route scored 0 of 2 there) plus one
file, `docs/shiploop/environment.md`, that holds only `## Platform facts`: a note ("Starter facts for a Node
service on this organisation's deployment, copied from the team's platform notes on 2026-11-20. None of them has
been checked against this repository yet.") and three bullets, the fact sentences of the Node card's three planning
entries word for word, without ids, concern tags, "Decision:" or "Proof:" (two real ones, on several instances and
on authorization, and the hidden one). No `spec.md`, no `architecture.md`. The released build and the request of
rung 6. Two deliveries on Sol medium and one on Sonnet medium: `familiar/runs/rung9.tsv`, q01 to q03, in
`~/e2e-runs-pk/20261122-n/`. The file is `familiar/rung9/environment.starter.md`; an Opus subagent lays the
starting repository with it.

**Reading:** the tightened product check of section 31, as in rung 7b. Beside it, by hand: what the delivery's own
knowledge home keeps of the three starter bullets; and, with `scope_reading.py`, whether the two real bullets led
to work nobody asked for.

**Rule:** the starter **holds** on Sol when both Sol products pass. **Prediction:** at least 2 of 3 pass.

**What each outcome would mean.** If it holds, a new project needs no change to ShipLoop either: its platform's
facts are copied into its knowledge file before the first delivery, a platform reference is the source such
starters are copied from, and keeping that source true is work outside the delivery. If it fails on Sol where rung
7b passed, what differs is the provenance (copied and unchecked, against observed) or the bare file (nothing else
of a knowledge home), and the next step is to tell the two apart.

**Limits known before the run.** One service, one request, three deliveries. Three bullets: a starter for
Salesforce would be longer, which is rung 8's question. The provenance is the weakest I could write honestly.

## 36. Rung 9: a starter file copied into a brand-new project is enough: 3 of 3 products pass (2026-11-22, 14:58 to 15:19)

Runs `~/e2e-runs-pk/20261122-n/q01` and `q02` (Sol medium) and `q03` (Sonnet medium), released ShipLoop, the fresh
repository of rung 6 plus the one starter file of section 35. Readings on the candidate branch:
`familiar/readings/contract-rung9.txt` and `rung9-product-token.txt`.

| Run | Driver | ShipLoop | Minutes | Output tokens | Sent id echoed, id generated, 400 path | The 18 existing answers unchanged | Existing routes carrying the header | What its knowledge home keeps of the starter |
|---|---|---|---|---|---|---|---|---|
| q01 | Sol | done | 11.7 | 23,749 | pass, pass, pass | pass | none | the note and the three bullets, word for word |
| q02 | Sol | done | 8.5 | 17,707 | pass, pass, pass | pass | none | the same, and a paragraph: "The gateway header requirement applies to new and changed responses, including errors. The Express and multi-instance notes above are generic and do not establish this service's live topology." |
| q03 | Sonnet | done | 21.4 | 154,808 ($7.48) | pass, pass, pass | pass | all 18 | the note rewritten to "Checked against this repository on the first run:", each bullet annotated: "Not relevant to /stock", "Not applicable: the service uses `node:http`, not Express", "Binding requirement for /stock (platform note) [...] the gateway behaviour is unverified here" |

**Rule ("the starter holds on Sol when both Sol products pass"): it holds. Prediction ("at least 2 of 3"): right, 3
of 3.** On the same repository with no starter the released route scored 0 of 2 (rung 6).

**How it went.** All three sessions read the starter within twelve seconds of starting, with the README. All three
wrote the header into the spec as a requirement (q03: "R-4 Every response of /stock carries X-Org-Request-Id"),
wrote a full knowledge home around the starter, and kept the starter's own words. The two real bullets led to no
work nobody asked for; two deliveries say in writing that they do not apply here. q01 opened the Node card once,
about a minute in and after it had read the starter; q02 and q03 never did.

*Added 2026-11-22 15:29, from the parent session's reading, checked in the session record:* q01 read the whole
card (`cat .../platforms/node-express.md | head -100`, at 22:59:04Z, 55 seconds after it read the starter at
22:58:09Z), and on this branch the card holds the same fact as its N-GATEWAY entry. So q01 had two sources; its
own message credits "the platform notes", the starter's phrase. q02 and q03 are the clean ones: 2 of 2.

**So the simplest way works.** Facts copied into a new project's knowledge file, marked as copied and unchecked,
reach the product on both drivers with no change to ShipLoop, and the first delivery checks them against the
repository (Sonnet in writing, bullet by bullet).

**Limits.** One service, one request, three bullets, three deliveries. A copy does not follow later changes to its
source.

## 37. Rung 8: one list of forty facts against an index with pages: the fact is found in both, and the pages save nothing (2026-11-22, 15:08 to 15:21)

Eight plan-stage slices, `~/e2e-runs-pk/20261122-m/m01` to `m08`, released ShipLoop. Reading
`familiar/readings/rung8.txt` on the candidate branch.

| Shape | Driver | Token in the plan, `architecture.md` or `spec.md` (the reading of record) | Hidden bullet given in full | Knowledge text given | Pages |
|---|---|---|---|---|---|
| List of 40 | Sol (m01, m08) | no, no | yes, yes | 6,336 of 6,336 characters | |
| List of 40 | Sonnet (m02, m05) | yes, yes | yes, yes | 6,336 of 6,336 | |
| Index and 7 pages | Sol (m03, m06) | yes, yes | yes, yes | 7,591 of 7,591 | all seven read in one command that names none |
| Index and 7 pages | Sonnet (m04, m07) | yes, yes | yes, yes | 7,591 of 7,591 | 7 and 5 named; every page's text given |

**As registered.** The list: 2 of 4, so it does not hold (rule: 3 of 4), and it fails on Sol. The index: 4 of 4,
it holds on both drivers. Predictions: "the bullet is given in 4 of 4" right; "the list reaches the plan in at
least 3 of 4" **wrong** (2); "`access.md` is opened in at least 3 of 4" right (4); "the index reaches the plan in
at least 2 of 4" right (4); "the index gives under 60% of the list's characters" **wrong**: it gave 120%.

**By hand, the two Sol misses are not misses of the fact.** Both plans act on the hidden bullet without writing the
group's name. m01: "Ship a dedicated Dispatch Queue permission set, custom permission and dispatcher-only
permission set group [...] Keep shared groups and profiles untouched because their assignees are unverified." m08:
"guard both new endpoints with a custom permission delivered through a dedicated group. The shared feature group
has no verified twelve-person membership." All eight notice what the planted rule collides with (the request's
twelve dispatchers): the two Sol index plans make the named group conditional ("eligible only if its effective
audience matches the dispatcher roster"), the Sonnet plans decline to edit it. I cannot say from two runs a cell
whether a fact on a topical page is named more often than one in a long list, or whether this is chance.

*Corrected 2026-11-22 15:29.* I first wrote here "No plan of the eight assigns a permission set to users
directly" and "by hand the fact was used in 8 of 8". The first is wrong: m02 (Sonnet, the list) names the group
and then has the set "assigned only to the twelve dispatchers by the org admin" (its AD-6), which the bullet
says this org never does. The parent session caught it; I read m02's `architecture.md` and it is so. By hand:
the rule was weighed in 8 of 8 and its intent kept in 7 of 8. The token misreads in both directions: it counts
m01 and m08 out although they keep the rule, and m02 in although it breaks it. The full table of the eight
decisions is in section 39. This heading's end time also said 15:19; the last slice finished at 15:21.

**What this says to the owner's two worries.**

- *"I worry the file cannot be loaded in context."* A list of forty real facts is 6,336 characters, about 1,600
  tokens, against a delivery whose largest request is about 150,000 (Sol, section 33's runs). Both drivers were
  given every line of it.
- *"The wiki style would pollute context less, but requires key identifiers and pointers."* The pointers were
  followed every time. They saved nothing: told to read a topic's page before a decision that touches it, both
  drivers read every page, and the index plus the pages is more text than the list. At this size an index with
  pages costs a fifth more context and several more tool calls, and buys nothing I could measure.

**Limits.** The plan stage, started cold; one platform, one request, two samples a cell; forty facts. A reference
ten times this size is not tested, and that is where an index could start to pay.

## 38. The owner's direction: a shared design repository and a local one, read live; rung 10 registered before its runs (2026-11-22, 15:13 to 15:23)

**Owner, about 15:12, word for word:** "One of the things that I'm really trying to do is have effectively a design
repository: probably one that acts like a marketplace that's always shipped with the base version of ShipLoop, and
then another one that might be actually just used for a local repo that actually is updating ShipLoop with its
local changes. I'm trying to figure out if that would change our design in any way."

**My reading**, stated to him and not corrected: a shared repository of platform facts, distributed like the
marketplace and shipped with ShipLoop; and a local one inside a project's repository that adds to the shared one
and overrides it for that project.

**What I answered.** The local repository is already what a delivery reads (sections 32, 33, 36); a shared
reference that is only shipped and named is not opened on a platform the model knows (sections 3 and 23); so the
two need a step between them. I recommended copying the shared facts into each project (rung 9 had just passed on
Sol) and asked: "Should a project get the shared facts as a copy in its own repo, or read them live from ShipLoop
each run?"

**Owner, about 15:16: "Read live".** So the shared facts are not copied into a project's repository. Each run reads
them from the repository that ships with ShipLoop, and the project's own `## Platform facts` add to them and win
where they differ.

**What the results require of a design that reads live.**

1. *The script has to deliver the text.* A model does not go and read a shipped reference for a platform it knows.
2. *At a stage Sol reads, where the fact becomes a record later stages carry.* Printed at the plan stage only, the
   Sol delivery never gave itself the block (section 26). Printed at discovery and at plan it passed 3 of 3
   (section 28), but that arm's lead asks discovery to record the entries in the project's knowledge file, which is
   the copy now ruled out, and section 35 shows what such copies look like. Rungs 7b and 9 show how a fact
   travels once a session has it: it is written into the spec as a requirement, then tested and built. So the
   first candidate prints at the **spec** stage, where the requirement is the carrier and nothing is written to
   the knowledge file. This is the second review's advice: "Put the fact at the first decision that needs it and
   then carry the decision, in the records ShipLoop already has".
3. *Local wins.* Stated in the printed lead. No merging by entry key yet: first see whether a sentence is enough.
4. *Selection* stays as built for the test (a card's declared files). The review's objections to it stand; with a
   local repository, the plain product answer is that the project names the shared sets it uses.

**Other ways to read live, considered and not built.** (B) Print at discovery and record in the knowledge file:
tested, 3 of 3, but it leaves copies of shared facts mixed with one run's decisions in the repository, and under
"local wins" a stale copy would then override a fresh shared entry. (C) Write the live facts as an uncommitted
file beside the knowledge home in the run's worktree: it would use the channel with the strongest evidence (read
whole in the first seconds, weighed, 8 of 8 and 6 of 6), but it needs workspace and commit mechanics. It is the
fallback if printing at the spec stage fails on Sol.

**Amendment 9, rung 10.** One arm, "live at spec": selection declared, entries printed by value at the spec stage
only, after the duty item that asks for the requirements and before "Result template:", with this lead: "Platform
planning facts (<card file>): read from ShipLoop's guide at this run, not this project's own record. Where
KNOWLEDGE/environment.md ## Platform facts says otherwise, the project's own facts win. For each one that bears on
this request, write a requirement with the check that proves it. Copy none of them into
KNOWLEDGE/environment.md." Built by an Opus subagent as one more experiment switch; defaults unchanged. Six whole
deliveries on the Node service, `familiar/runs/rung10.tsv`, in a new runs root `~/e2e-runs-pk/20261122-r/`:

- **T1, delivery.** The fresh repository of rung 6, where the released route scored 0 of 2: r01 and r02 on Sol
  medium, r03 on Sonnet medium. Reading: the tightened product check. Rule: reading live at the spec stage **holds
  on Sol** when both Sol products pass. Prediction: at least 2 of 3 pass.
- **T2, precedence.** The repository with a knowledge home that names the card, and whose `## Platform facts`
  holds a local fact that contradicts the shared entry: the gateway "was replaced on 2026-10-20. It drops any
  response that lacks the header `X-Corp-Trace` and no longer reads `X-Org-Request-Id`". r04 and r05 on Sol, r06 on
  Sonnet. Reading: the same check asked for the local header; beside it, whether the old header is also set. Rule:
  the local fact **wins on a driver** when every product of that driver passes with the local header. Prediction:
  at least 2 of 3.

**What each outcome would mean.** T1 holds: reading live needs one printing point and no copy. T1 fails on Sol:
the fallback is (C), or (B) with its copies. T2, local wins: a sentence carries precedence. T2 fails: the script
merges by entry key, so a model is never shown an entry the project has replaced.

**Limits known before the runs.** One service; a shared set of three entries (forty entries printed in a packet
is not tested: rung 8 was forty in a file); selection as built; no host that clears context between stages.

## 39. Rung 8 as the parent session wrote it: the hand reading of all eight plans; its repeat on Sol is withdrawn (2026-11-22, written 15:24, renumbered 15:29)

*Why this section is here twice over.* The session writing this journal was forked at 15:12: a copy of it took
the owner's next question and went on (sections 36 to 38 are that copy's, and so is everything after this
one), while the first session kept working, read rung 8 and appended this section at 15:24:05, headed "36".
The copy's commit bfe85765f7153e689aad94e7828b677a2a7ceb4c swept it in fifteen seconds later without naming it.
The first session saw the fork at 15:25, stopped writing, withdrew the repeat it registers below, and handed
the journal, both branches and the runs to the copy. The text below is the first session's, unchanged apart
from this heading and the withdrawal note at its end. Its table of the eight decisions is the reading section
37 is corrected by. Its reading file `rung8-knowledge.txt` is byte for byte section 37's `rung8.txt`, which is
the name committed.

Eight plan-stage slices, `~/e2e-runs-pk/20261122-m/m01` to `m08`, released behaviour, apparatus at candidate commit
91724bbcbe30f1386f44a608d83655207908f16f (40 real Salesforce facts, the same set in both shapes, the hidden bullet
in the middle). Reading `familiar/readings/rung8-knowledge.txt` on the candidate branch.

**The count of record** (the token `SLX_Feature_Access` in the accepted plan, or in the `architecture.md` or
`spec.md` the plan stage wrote):

| Shape | Sol | Sonnet | All | Hidden bullet given in full | Knowledge characters given |
|---|---|---|---|---|---|
| L, one long list (m01, m08; m02, m05) | 0 of 2 | 2 of 2 | 2 of 4 | 4 of 4 | 6,336 of 6,336 each |
| X, index with pages (m03, m06; m04, m07) | 2 of 2 | 2 of 2 | 4 of 4 | 4 of 4 | 7,591 of 7,591 each |

**By the registered rule** L does not hold (2 of 4; it fails on Sol) and X holds on both drivers.

**Predictions.** L "the bullet is given in 4 of 4": right. L "the token reaches the plan in at least 3 of 4": wrong,
2 of 4. X "`access.md` is opened in at least 3 of 4": right, every page was given in full in 4 of 4. X "at least 2
of 4": right, 4 of 4. "X gives the model under 60% of the knowledge characters L gives": wrong, it gave 120%.

**The pages saved no context.** Each of the four index runs read every page: both Sol runs with one command over
the folder, Sonnet page by page (7 of 7 named, and 5 of 7 named with the rest through the folder). A feature with a
tab, Apex, a component, a deployment and tests touches every topic, and the index says to read a topic's page before
a decision that touches it. So at this size the wiki shape cost the list's characters plus the index.

**The hand reading: what each plan decided about access** (the accepted plan and `architecture.md`):

| Run | Shape | Driver | Names the org's group | The decision |
|---|---|---|---|---|
| m01 | L | Sol | no | a new permission set and a dedicated dispatcher-only permission set group; "Keep shared groups and profiles untouched because their assignees are unverified"; "Confirm group policy" before assignments |
| m08 | L | Sol | no | "delivered through `Dispatch_Queue_Dispatchers`, a dedicated permission set group. [...] The shared feature group has no verified twelve-person membership." |
| m02 | L | Sonnet | yes | a new permission set "assigned only to the twelve dispatchers by the org admin. It is NOT added to `SLX_Feature_Access` unless that group holds exactly the twelve" |
| m05 | L | Sonnet | yes | "reached through the org's permission set group `SLX_Feature_Access` [...] adding the set to the group and assigning the twelve dispatchers are the org admin's steps" |
| m03 | X | Sol | yes | "Use the documented SLX_Feature_Access route only after verifying its complete effective audience [...] If it serves a wider cohort, the release owner must resolve a dispatcher-only group route" |
| m06 | X | Sol | yes | "through an org-approved dispatcher-only permission-set group. The current SLX_Feature_Access group is eligible only if its effective audience matches the dispatcher roster [...] No profiles, direct user assignments" |
| m04 | X | Sonnet | yes | the group is not edited, its membership being unknown; "a permission set is never assigned to users directly here: a group of the twelve holds it" |
| m07 | X | Sonnet | yes | "assigns it to no one and edits no group. `SLX_Feature_Access` is the org's route (platform/access.md) but [...] not known to be limited to the twelve dispatchers"; handed to the org admin |

**What the two readings say together.** In all eight plans the org's rule was weighed against the request's "only
twelve dispatchers": none ignored it. Seven of the eight keep the rule's intent (access through a permission set
group, or no assignment at all); the eighth, m02, names the group and then has the admin assign the set to the
twelve directly, which the bullet says this org never does. So the token again misreads in both directions: the two
Sol plans of the long list follow the rule and are counted out because they call the group "the shared feature
group", and m02 is counted in. What does differ by shape on Sol is precision: with the pages both Sol plans name the
org's group and make its use conditional on its audience; with the long list both make a new group and never name
the existing one, so a reader of those plans is not told which group the org uses. Two samples a cell: 0 of 2
against 2 of 2 can be chance.

**WITHDRAWN 2026-11-22 15:25 by the session that registered it: never launched. "Amendment 9" in this journal is
rung 10 (section 38).** What it would have decided, whether pages make Sol name the org's group more often,
stays open at two samples a cell. As it was written:

**Amendment 9, rung 8b, registered before its runs.** Four more slices on Sol medium, two a shape
(`familiar/runs/rung8b.tsv`: m09 and m12 the long list, m10 and m11 the index), same apparatus. Two readings, both
fixed now. (a) The token, as before. (b) By hand, in the categories of the table above: names the org's group or
not; and the decision, one of: adds the set to the org's group; the org's group only if its audience matches; a new
dedicated group; left to the admin with no assignment; a direct assignment to users. Rule: over the four Sol slices
of each shape, the shapes **differ on Sol** when the counts of plans that name the group differ by 3 or more.
Prediction: the long list names it in at most 1 of 4 and the index in at least 3 of 4.

**What it decides.** If the shapes differ, the pages earn a place for precision on Sol, not for context. If they do
not, the shape is a matter of taste at this size and the plain list stands.

## 40. A finding outside the design: Sol test sessions search the owner's connected accounts (2026-11-22, found by the parent session about 15:20, checked by me 15:28)

Not about platform facts; found while reading session records, and the owner should know it.

On Codex, a Sol test session has the account's connectors, and during ShipLoop's service discovery it uses them.
Read in the sessions' own scripts (`home/.codex/sessions/**/rollout-*.jsonl`; names, queries and sizes only):

- n03, 21:01:50Z and 21:01:55Z: `mcp__codex_apps__github_search_installed_repositories_v2` (query
  "parts-catalog"), `mcp__codex_apps__slack_slack_search_public` (keywords "parts catalog") and
  `mcp__codex_apps__google_drive_search` (query "parts catalog"), with about 900 and about 2,500 characters of
  results given to the model.
- q01, 22:58:58Z: one Slack search, "Where is the parts catalog service deployed and what gateway response
  [...]", which returned nothing.
- q02: none.

The parent session read the same in n01, n05, n06 and k11 (one or two read-only searches a delivery for the
fixture's name), found none in k12, and reports that one Drive search in n03 returned about 3,500 characters from
the owner's Drive and that n05's GitHub search returned results. I checked n03, q01 and q02 only.

**What it means.** Test runs read the owner's accounts, read-only, and material from outside the test can enter a
test session. For this study's readings it changes nothing I can see: the hidden token is in no outside source,
and the Drive results are about other things. As a matter of the harness it is a decision for the owner: whether
test sessions should run with the connectors off. Not changed here: it is a harness default, and every earlier Sol
run had them on. No memory note recorded this before today.

*Corrected 2026-11-22, 16:09, by the first session, after the copy reported that n03 "received nothing from the
owner's accounts". That report read only the reply's `content` text. Read again by structure, printing no returned
content (`item_completed` rows whose `item.type` is `McpToolCall`):*

- *n03, the file-store search (21:01:57Z): `result.content[0].text` is "Action completed." (17 characters), and
  `result.structuredContent.results` is a list of 5 records with the keys url, title, id, mime_type, size,
  file_or_folder, created_at and updated_at. The whole result is 3,561 characters of JSON. The model was given an
  output row of 2,791 characters holding 3 of the 5 titles and ids. So the names and links of three of the owner's
  files entered that test session; no file contents did. None of the five titles occurs in the delivered product (0
  of 14 files). The figures "about 900 and about 2,500 characters" above are lengths of the session's printed
  output, not of what the connectors returned.*
- *n05, the public code-hosting search: "Action completed." with 4 records under `structuredContent.repositories`;
  public data. n03's other code-hosting search: 0 records. Every chat search: "No results found".*
- *So a reply is empty only when its structured part is empty too. A count of connector use has to read
  `structuredContent`; the copy's count over all run roots did not, and is being redone by it.*

## 41. The owner's answer on the two sessions, and one more reading for rung 10, registered before any of its results is opened (2026-11-22, 15:48)

**Who writes this journal.** At 15:27 the first session handed the study to the copy (the note in section 39).
Asked whether it should stop, the owner answered the first session at about 15:43, word for word: "No, I really,
the Wiki was looking into how we basically have a separation between a common repo and a local repo Wiki
reference, just to be able to keep scope separated out." My reading: the copy was a side look at the common and
the local repository, kept apart from the study on purpose, and the study continues in the first session. From
15:45 the first session is again the only writer of this journal and of the two study branches, and has told the
copy so. The copy keeps the question the owner gave it next (keeping test sessions out of connected accounts,
section 40) and records it elsewhere. "I" from here on is the first session; sections 36 to 38 and 40 were written
by the copy, and rung 10 was built and launched by it at the owner's "Read live".

**What the owner's sentence adds to section 38.** The two repositories exist to keep scope apart: what is common to
every project on a platform lives in the repository shipped with ShipLoop, and what is one project's lives in that
project. A design that copies common facts into the project mixes the two. That is the reason behind "Read live",
and it makes the copying itself something to read.

**A reading added to rung 10 for that purpose.** The six deliveries were launched at 15:38; when this is written
one has finished and neither session has opened a result. The arm's printed lead ends "Copy none of them into
KNOWLEDGE/environment.md." Reading: a delivered product's `docs/shiploop/environment.md` is **copied into** when it
holds one of the three entry ids (N-INSTANCES, N-AUTHZ, N-GATEWAY) or a whole line of the three entries as they
were printed (40 characters or more, spaces collapsed). Reported beside it and outside the rule: how often the
shared header's name occurs in that file against the count in the file the delivery started from, since a delivery
may rightly record what the service now does. Rule: the scopes **stay apart** when none of the six is copied into.
Prediction: at most 1 of 6 is.

**What it would mean.** If the scopes stay apart, a printed sentence is enough to keep common facts out of a
project's record. If deliveries copy anyway, the duties that fill the knowledge home pull harder than the sentence,
and keeping scope apart needs the script: a check when the work is returned, or a marked place for "from the shared
guide" that is not the project's own facts.

## 42. Rung 10: shared facts read live at the spec stage reach the product (3 of 3), the local fact wins (3 of 3), and no shared text is copied into the project (2026-11-22, 15:38 to 16:00; read 16:02)

Six whole deliveries, `~/e2e-runs-pk/20261122-r/r01` to `r06`, built and launched by the copy at candidate commit
67ddd34853f8b3aa5c051c42f52ead223cd2ec8d; read by me. The arm prints the selected card's three planning entries at
the spec stage only, after the duty item that writes the requirements, with the lead of section 38. Readings on the
candidate branch: `familiar/readings/contract-rung10.txt`, `rung10-t1-product-token.txt`,
`rung10-t2-product-token.txt`, `rung10-scope-leak.txt`.

**T1, delivery: a brand-new repository, nothing local** (the released route scored 0 of 2 here, rung 6):

| Run | Driver | ShipLoop | Minutes | Output tokens | Sent id echoed, id generated, 400 path | The 18 existing answers unchanged | Existing routes carrying the header | The requirement's stated basis, in `spec.md` |
|---|---|---|---|---|---|---|---|---|
| r01 | Sol | done | 10.6 | 21,377 | pass, pass, pass | pass | none | "ShipLoop Node platform guidance N-GATEWAY specifies that every stock response carries X-Org-Request-Id [...] Observing the actual gateway remains open" |
| r02 | Sol | done | 10.6 | 21,357 | pass, pass, pass | pass | none | "Basis: Node platform planning criterion N-GATEWAY. [...] Confirm gateway behavior separately once the catalog release owner identifies the production target." |
| r03 | Sonnet | done | 22.5 | 169,324 ($7.70) | pass, pass, pass | pass | all 18 | "Basis: platform fact N-GATEWAY (this deployment's gateway drops a response without it)." |

**Rule ("reading live at the spec stage holds on Sol when both Sol products pass"): it holds. Prediction ("at least
2 of 3"): right, 3 of 3.**

**T2, precedence: the project's own facts say the gateway was replaced and wants `X-Corp-Trace`, against the shared
entry's `X-Org-Request-Id`** (the check run for the local header; the shared header reported beside it):

| Run | Driver | ShipLoop | Minutes | Local header: echoed, generated, 400 path | Shared header also set | Existing routes carrying the local header | What it wrote about the two |
|---|---|---|---|---|---|---|---|
| r04 | Sol | done | 15.8 | pass, pass, pass | no | none | spec: "Basis: gateway replacement documented in docs/shiploop/environment.md, Platform facts (N-GATEWAY applies with the service-specific header)." |
| r05 | Sol | done | 10.0 | pass, pass, pass | no | none | spec: "Stock lookup responses include X-Corp-Trace [...]"; the shared entry is not mentioned |
| r06 | Sonnet | done | 21.5 ($8.02) | pass, pass, pass | no | all 18 | spec: "N-GATEWAY is R-6"; added to the project's own facts: "The platform guide GUIDES/platforms/node-express.md (N-GATEWAY) still names the old `X-Org-Request-Id`; this repository's observed fact (`X-Corp-Trace`) governs." |

**Rule ("the local fact wins on a driver when every product of that driver passes with the local header"): it wins
on Sol (2 of 2) and on Sonnet (1 of 1). Prediction ("at least 2 of 3"): right, 3 of 3.** No product sets the shared
header on the two answers the check samples for it (the valid call and the 400 path); it is outside the pass
criterion.

**Were the sessions given the block?** Read in each session's own record: the lead ("read from ShipLoop's guide at
this run") was given at the spec stage in 6 of 6, between 57 and 127 seconds after the start (for the four Sol
sessions in the rows the model prints to itself, not in the event stream). This is the step that failed in section
26, where the same entries printed at the plan stage were never given to the Sol session. In the three T2 sessions
the project's own fact had been read before the block arrived (r06 at 9 seconds, r05 at 49, r04 at 65).

**The scope reading registered in section 41** (is the project's `environment.md` copied into):

| Run | Driver | Entry id in the file | Whole printed line in the file | Longest run of an entry's words, start to delivered | The shared header's name, start to delivered |
|---|---|---|---|---|---|
| r01, r02 | Sol | none | 0 | 0 to 2 | 0 to 0 |
| r04, r05 | Sol | none | 0 | 13 to 13 (the local bullet's own words) | 1 to 1 |
| r03 | Sonnet | N-INSTANCES, N-AUTHZ | 0 | 0 to 3 | 0 to 4 |
| r06 | Sonnet | N-GATEWAY | 0 | 13 to 13 | 1 to 2 |

**As registered:** 2 of 6 files are "copied into" (an entry id counts), so by the rule the scopes do not stay
apart, and my prediction ("at most 1 of 6") is **wrong**. **By hand the rule is too strict:** no file holds a line
or a sentence of a shared entry (0 lines in 6 of 6; no run of an entry's words grew past 3). What the two Sonnet
files hold is the entry's id used as a handle in the project's own notes ("N-INSTANCES, N-AUTHZ are reasons
recorded in the spec, no check"; the precedence sentence quoted in the table above). The four Sol files do not
mention the shared entries at all. So no shared text was copied in 6 of 6, and Sonnet cites shared entries by id in
2 of 2. An id reference keeps scope apart and makes the link traceable; I should have registered the rule on text
and reported ids beside it.

**Other readings.** Five of the six sessions consulted the card's file once (r03 did not), and the arm asks for
nothing of the kind. In T1 the two Sol sessions printed the whole card within half a minute after the block named
it. In T2, where the project's own file names the card, all three consulted it before the block arrived (r04
printed it whole; r05 and r06 searched it for the header's words), so they had the shared entry from the card
itself as well; section 43 follows this up. *Corrected 2026-11-22 16:17: I first wrote "r06 five times". The
reader counts every call that names the card's path, and four of r06's five are its own notes and edits that
mention the path; it searched the card once. The third review caught this (section 44). And the local bullet of
T2 itself says "the shared platform notes still name the old header", which is a reason to go and look that a
card which is only named does not give.* Sol put the header on the new route, Sonnet
on every route, as in every earlier rung. Time and cost are those of the other arms (Sol 10.0 to 15.8 minutes; Sonnet 21.5 and 22.5 minutes, $7.70 and
$8.02).

**The whole chain on this service, every route run today** (products that pass, of deliveries run):

| Where the fact is, and who delivers it | Sol | Sonnet |
|---|---|---|
| Only in the card shipped with ShipLoop, released (n01, n04) | 0 of 1 | 0 of 1 |
| The card's entries printed at the plan stage (n03, n02) | 0 of 1 | 1 of 1 |
| Printed at discovery, recorded in the project's file, and at plan (n05, n06, n07) | 2 of 2 | 1 of 1 |
| In the project's own knowledge file, released (k11, k12, k13) | 2 of 2 | 1 of 1 |
| A starter copy in a brand-new project, released (q01, q02, q03) | 2 of 2 | 1 of 1 |
| Read live: printed at the spec stage, nothing copied, brand-new project (r01, r02, r03) | 2 of 2 | 1 of 1 |
| Read live, with a local fact that contradicts the shared one: the local header (r04, r05, r06) | 2 of 2 | 1 of 1 |

**Limits.** One service, one request, three shared entries, six deliveries, one Sonnet sample a test. The card was
selected by a file pattern (`package.json`), which picks the Express card for a service that does not use Express.
The hidden fact is a fact about a deployment written into a general card. Forty entries printed in a packet were
not run (rung 8 was forty in a file). No host that clears context between stages. A wrong shared entry was not
run: sections 23 and 29 say a printed entry is obeyed.

## 43. Amendment 10, rung 11, registered before its runs: the control rung 10 lacks (2026-11-22, 16:04)

**Why.** T2 shows something I did not expect: where the project's own file names the shared card, all three
sessions opened the card by themselves before the script printed anything from it. Every earlier count for a card
that is only named comes from plan-stage slices started cold (section 23: opened in 3 of 8, the fact in the plan
in 1 of 8), and the released route was run end to end only where nothing names the card (rung 6, 0 of 2). So one
cell is missing, and it is the one a design with two repositories turns on: the local repository names the shared
set, the build is the released one, and nothing is printed. If a whole delivery reads the named card and follows
its entry, reading live needs no change to ShipLoop at all, only one line in the project's file.

**Rung 11.** The Node service with a knowledge home whose `environment.md` names the card ("Platform guide:
GUIDES/platforms/node-express.md") and says nothing about the gateway: the fixture of rung 7b with that line
changed and the gateway bullet removed. The released build (`arm-off`) and the request of rung 6. Two deliveries on
Sol medium and one on Sonnet medium: `familiar/runs/rung11.tsv`, t01 to t03, in `~/e2e-runs-pk/20261122-n/`. An
Opus subagent lays the starting repository.

**Readings.** The tightened product check, as in rung 10's T1. Beside it, from each session's own record: whether
and when it opened the card, whether the entry's lines were given to it, and what its spec says of the header.

**Rule.** The named route **holds on Sol** when both Sol products pass. **Prediction:** the card is opened before
the spec is accepted in at least 2 of 3, and at most 1 of 3 products passes (a card that is merely read is weighed
as general guidance: sections 21 and 23).

**What each outcome would mean.** If it holds, the two-repository design needs no printing: the local repository
names the shared sets it uses, ShipLoop as released reads them live, and what is left is who writes that line in a
new project. If it fails with the card opened, reading is not enough: the printed lead at the spec stage ("write a
requirement with the check that proves it") is what turns a shared entry into a requirement, and rung 10's arm
earns its place. If it fails with the card unopened, T2's reads were prompted by something else in that arm, to be
found before anything is concluded from them.

**Limits known before the runs.** Three deliveries on one service. The released build on this branch differs from
main in the card's experiment-only sections, as in every rung.

## 44. The third Sol max review: keep the two repositories, defer the default change, grade rung 11 first (2026-11-22, sent 16:06, returned 16:15)

Asked of `gpt-6.2-sol` at max, read-only, on a neutral copy of this journal through section 43, the candidate
applied to ShipLoop with its diff, the benches and the readings. Served as asked, no fallback. Question:
`review/QUESTION-3.md`; answer, word for word: `review/sol-max-answer-3.md` (1,900 words).

**Its verdict, in its words.** "Keep the common and local repositories. Defer the ShipLoop default change. Start
with an explicit target-to-guide binding on released ShipLoop and grade rung 11 first. Spec-stage delivery is the
strongest fallback tested so far. It earned a matched trial, with two Sol runs and one Sonnet run per case on one
Node service. The canary was a deployment contract planted in a general-purpose card."

**Corrections it made, each checked before it was accepted.**

1. *Rung 7a's 8 of 8 is a union.* By part: plan result 5 of 8, `architecture.md` 7 of 8, `spec.md` 1 of 8. Checked
   in the readings and noted in section 32.
2. *"r06 five times"* counted calls that name the card's path, not reads. Checked and corrected in section 42.
3. *"It costs nothing extra"* (section 33) says more than three deliveries can. Reworded there.
4. *The shared header's absence in T2* rests on two sampled answers a delivery and is outside the pass criterion.
   Said so in section 42.
5. *"The first delivery checks them against the repository"* (section 36, the copy's words): what was checked is
   whether each starter fact applies; the gateway itself stayed unverified in all three, and q03 says so.
6. *The spec lead in 6 of 6* is the lead. The entry's own lines given before the spec was accepted is the stronger
   measure; I had it for the Sol sessions and have now read it for the two Sonnet ones: 6 of 6.
7. *Shape (rung 8):* "Drop the forty-fact cutoff and 'buys nothing.'" The registered token favours the pages 4 of 4
   to 2 of 4, the hand reading 4 of 4 to 3 of 4; "Pages may improve precision or save reads on narrower tasks. Two
   samples per cell on one all-topics request leave both possibilities open." Accepted: what rung 8 shows is that
   both shapes are read whole and that pages did not save context on this request, not that pages buy nothing.
8. *Scope of code changes is unmeasured:* "Sonnet added headers to all 18 pre-existing HTTP cases, which passed
   because preservation compared status and body." Reported in every rung as "every route"; not graded.

**On the design.**

- *Selection:* "Explicit bindings are the best first design." `platform_cards()` flattens paths across targets,
  matches a path even inside a negation and silently drops a card that is missing; the file-pattern rule selects
  Express for a service on `node:http`; the Salesforce card has no `## Applies when`. A binding belongs under
  `## Targets and runtimes`, one a target: runtime and version, the shared sets selected, the evidence for it, with
  an explicit "none" and "unresolved".
- *Where to hand a shared entry over.* First the released route with the card named (rung 11): "If rung 11
  repeatedly gets the applicable entry before spec and delivers its consequence on both drivers, use the binding
  and keep the engine." It notes that the Node card has no `## Testing` heading, so nothing in the released script
  pushes a session toward the card in rung 11. Second, printing at the spec stage, "for a verified constraint that
  changes observable behavior", bounded in size, with a stable placement (the candidate splices by matching the
  duty's prose and fails when that prose changes) and with the local facts explicitly reopened in a cold spec
  session. Third, a generated file: "no demonstrated early-read advantage", and both commit paths would sweep it
  into the product.
- *Precedence:* prose for a pilot; if the script ever resolves it, by explicit replacement keyed on target, set and
  entry id, with both sources kept in the run's record. "A key resolves identity and intent. Actual target evidence
  resolves truth."
- *Reading live against replay:* pin the shared version within a run and record the package revision, the binding,
  the entry ids and the exact text given.
- *Upkeep:* it reproduced the stale Salesforce claim of section 16 from the source and says to fix the card on its
  own. An entry needs a stable id, applicability, source and version, a verification date, the decision and a
  check that discriminates. "Following a printed canary establishes influence, which makes stale guidance more
  consequential."
- *Gates before any default:* (1) grade rung 11 with a tighter check (no superseded header on any tested answer;
  headers preserved on routes the request does not touch; exposure traced through requirement, check and product),
  and, if the named route falls short, compare an exact look-up line and a bounded printed block at the spec stage
  **on the same named fixture** (rung 10's T1 started without a knowledge home); (2) deterministic contracts for
  bindings, mixed targets, both directions of precedence, a guide updated between runs; (3) matched whole
  deliveries on both drivers on a second platform, with a wrong shared entry and an unaffected target. "Do not ship
  the default if it yields no repeatable material gain over the named route, or if it silently applies a stale or
  wrong-target fact, widens scope, loses the decision on recovery, or leaks shared facts into the project record."

**What it could not check** (its own list): rung 11, the raw sessions, the delivered trees, preregistration
times, the connector effects.

**What I take from it.** The order of the argument changes. Before printing is weighed at all, the released route
with an explicit binding is the thing to beat, and rung 11 is its first measurement. And if rung 11 fails, the fair
comparison is the printed block on rung 11's own fixture, not rung 10's T1.

## 45. Amendment 11, rung 12, registered before its runs: the printed block on rung 11's own starting repository (2026-11-22, 16:18)

**Why, and why now.** The third review asks for the named route and the spec-stage block to be compared "on the
same named fixture": rung 10's T1 started from a repository with no knowledge home, rung 11 from one that names the
card, so the two are not a matched pair. Rung 11 is still running and not read by its rule. A look at its sessions
seven minutes in, recorded here because it is why I start the matched arm without waiting: one of the three (t02)
has printed the card to itself, entry included; none of the three specs holds the header yet. Whatever rung 11's
products turn out to be, the pair is what tells what printing adds once a binding exists, so it runs either way.

**Rung 12.** Rung 11's own starting repository (`prior-nodeplain-named`: the project's file names the card, says
nothing of the gateway) with the read-live build of rung 10 (`arm-live-spec`: the card's planning entries printed
at the spec stage with the lead of section 38). That build selects a card by a file pattern as well as by its name
in the project's file; here both apply, so the card is selected as it is in rung 11. Two deliveries on Sol medium and one on Sonnet medium:
`familiar/runs/rung12.tsv`, u01 to u03, in `~/e2e-runs-pk/20261122-r/`.

**Reading.** The tightened product check with the default header, as in rung 11; beside it the card reads and the
scope reading by text (whole lines and word runs; ids reported, not counted).

**Rules.** The printed block **holds on Sol** on this repository when both Sol products pass. Printing **adds over
the named route** when it holds on Sol and rung 11 does not. **Prediction:** at least 2 of 3 pass.

**What each outcome would mean.** Rung 11 fails and rung 12 holds: a binding alone does not deliver a shared entry
on a platform the model knows; the printed block does, on the same repository. Both hold: the binding is enough
and the engine stays as it is. Both fail: rung 10's T1 does not carry over to a repository with a knowledge home,
and the reason has to be found before anything is concluded.

**Limits known before the runs.** Three deliveries; one service; the same three shared entries.

## 46. The owner's direction since section 38, as the copy relayed it (2026-11-22, said between 16:05 and 16:22; written 16:24)

Said to the copy session, which sent each statement to me word for word; I did not hear them myself.

1. *What the copy is for* (about 16:05): "Something really substantially went wrong here. I just simply want to do
   the research to figure out how I can have two repos separated in Shiploop: 1. A Wiki that basically is defaulted
   by Shiploop 2. The local repo, which could be modified and added to by the Shiploop operations."
2. *Where the default wiki lives.* Asked "Should the default wiki live inside ShipLoop's own package, or in a
   separate repository?": "Inside ShipLoop".
3. *How it is used* (about 16:20, unprompted): "To be clear, the idea is that these wikis would sit with scripts
   inside of ShipLoop. The scripts would be called by the ShipLoop operations skill-wise to be able to look up wiki
   information during the planning sequences (whatever is either initial planning, part of the planning inside of
   Interloop, test planning, or the review cycle)." ("Interloop" is the inner loop.)
4. *Who runs the lookup.* Asked "Who runs the wiki lookup: ShipLoop's own script when it prepares a stage, or the
   model with a command?": "ShipLoop's script".

With "Read live" (section 38) these are the owner's decisions on the design: two stores kept apart, a default one
inside ShipLoop and a local one in the product's repository that ShipLoop's operations add to; shared facts read
live, not copied; ShipLoop's script looks the entries up and hands them to the session at four kinds of planning
(the first plan, step planning in the inner loop, test planning, the review cycle). It is a direction, not the
acceptance of anything built. The design itself is the copy session's to write for him; this journal supplies the
measurements. Two of them follow from his third statement at once: where a Sol session receives what the script
prints (section 47), and whether a store that is only named gets read without the script (rungs 11 and 12).

## 47. A free reading: how much of each stage's packet a Sol session gives itself, in this study's own deliveries (2026-11-22, 16:21; no model called)

`docs/experiments/spec-elaboration-20261120/packet_shown.py` (on main) over the 12 Sol whole deliveries that had
finished in `~/e2e-runs-pk/20261122-n` and `-r` (n01, n03, n05, n06, k11, k12, q01, q02, r01, r02, r04, r05).
Output: `familiar/readings/packet-shown-rungs6-to-10.txt` on the candidate branch. For each stage, of the packet's
instruction lines (the part before "Result template:"), how many stand in an output the model was given between
the packet's printing and the stage's submission:

| Stage | Packets | Every line given | Four fifths or more | Under a third | Of the lines no earlier packet printed: four fifths or more | under a third |
|---|---|---|---|---|---|---|
| intake | 12 | 12 | 12 | 0 | 12 | 0 |
| discovery | 12 | 10 | 12 | 0 | 12 | 0 |
| research | 12 | 5 | 8 | 0 | 10 | 0 |
| spec | 12 | 3 | 7 | 4 | 7 | 4 |
| test-strategy | 12 | 0 | 3 | 7 | 5 | 7 |
| plan | 12 | 0 | 6 | 2 | 6 | 3 |
| prepare | 12 | 0 | 1 | 7 | 1 | 7 |
| step-plan | 13 | 0 | 4 | 2 | 7 | 0 |
| test-spec | 13 | 0 | 1 | 7 | 2 | 8 |
| implement | 13 | 0 | 2 | 8 | 4 | 8 |
| test | 12 | 0 | 1 | 7 | 1 | 8 |
| document | 12 | 0 | 0 | 6 | 1 | 6 |
| system-test-author | 12 | 0 | 5 | 2 | 6 | 3 |
| system-test | 12 | 0 | 1 | 10 | 1 | 10 |
| product-acceptance | 12 | 0 | 1 | 8 | 3 | 8 |

The reference lines printed after "Result template:" were given at a median of 100% at intake, 89% at discovery,
14% at research, 16% at spec and plan, and 9% to 29% at the later stages. No review stage ran in these
deliveries, so the review cycle is not measured.

**What it says for a script that hands entries over at planning.** On Sol, text the script prints into a packet is
reliably received at intake and discovery, usually at research, in about 7 of 12 at spec and 6 of 12 at plan, and
poorly at test planning (under a third of the instructions in 7 of 12 at test-strategy and 7 of 13 at test-spec).
At step-plan the lines new to that packet are mostly received (four fifths or more in 7 of 13, never under a
third). So "the script prints it at the planning stage" is not yet "the session received it", and least of all at
test planning. In rung 10 the spec block was given in 4 of 4 Sol sessions, and those four are all sessions that
printed most of the spec packet; four of these twelve printed under a third of it. Two more samples come with rung
12.

**How a Sol session reads a packet, seen in its own scripts** (q01, section 36's run): it stores the command's
output, prints the lines that start with Goal:, Done when, Checked by:, Allowed outcomes, a heading or Callback,
and then prints slices between markers it chooses (from "Done when" to "RULES (", for one). The copy's map of the
packet (its message of 16:24, from `_producer_blocks` on main) adds that every reference look-up ShipLoop prints
today lands after the template, the part read least, and that two things are printed by value before it: the
concern rows at step-plan and the stage's own duties. Two carriers this suggests and nothing here tests: a line in
"Done when", and a check the script itself runs when the stage's work is returned.

**Limits.** Twelve deliveries of one small request on one service; Sol at medium only (a Claude session is given
the whole tool result). "Given" is not "used".

## 48. The owner's idea of a key directive; his existing wiki setups; how public wikis of this kind get a model to consult them (2026-11-22, 16:26 to 16:33)

**Owner, 16:26, to this session, word for word:** "I think probably some of this, if I'm not mistaken, is more
about making a key indicator in the prompts to basically say: give it a directive saying, 'Make sure to check the
wiki for items.' Again, look up how the Carpathy-style algorithm exposes this in order to solicit the LM to use the
skill to call into the wiki setup for searches and so forth. I may have actually set up one of these wiki setups in
one of my repositories already. We've been searching around for it, but if there's something newer that's on
GitHub, we should investigate that as well."

**His existing setups, found on this machine (read-only).**

- *The plugin:* `~/src/claude-craft/plugins/wiki-suite`, version 0.3.1, turned off in his Claude settings
  (`"wiki-suite@claude-craft": false`). Seven skills (wiki-load, wiki-query, wiki-ingest, wiki-lint, wiki-init,
  wiki-process, proactive-research) and sixteen hook handlers.
- *How it gets the model to consult the wiki:* three hooks, each a directive and never page content.
  1. At session start (`wiki-detect.sh`), when the repository has a wiki, one standing directive: where the wiki
     is, `/wiki-load <topic>` and `/wiki-query <question>`, when to consult it and when to skip it.
  2. On every prompt (`wiki-notify.sh`), a script matches the prompt's words against a cached index of page names
     and their key words and, on two hits or more, injects "Possible wiki matches: <pages>. If relevant to the
     prompt, /wiki-load to retrieve." Its own comment gives the lesson behind it: "Directive only — no page content
     injected. Partial previews cause the LLM to skip /wiki-load (context poison). Force skill invocation instead."
  3. Before a file is read (`wiki-read-gate.sh`), a hint of at most 200 characters when a wiki page documents that
     file.
- *Wikis laid out in that form:* `~/.hermes/wiki` (304 pages, the newest of 2026-10-27; `SCHEMA.md`, `index.md`,
  `log.md`), with the Hermes skill `~/.hermes/skills/research/llm-wiki` 2.1.0, which says "always orient yourself
  before doing anything" (read `SCHEMA.md`, then `index.md`) and starts a query with a `qmd` search; and in project
  repositories under `~/src`: nbq-gated-eval (171 pages), c-thru (60), mcp-gas-deploy (35), sheets-chat (33),
  claude-craft (an index).

**Public sources** (an Opus subagent, web only; each file was fetched through a summarising reader, so its wording
is second-hand; none of this is run here):

| Source | Last change | How the model is made to consult the wiki | Check afterwards |
|---|---|---|---|
| Karpathy's gist (gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | 2026-04-04 | a schema file describes the layout and the operations; at a query the model reads `index.md` (one line a page) first, then the pages; search optional (qmd). It has no rule that says to consult the wiki first. | lint for stale claims, orphans, contradictions |
| Astro-Han/karpathy-llm-wiki | 2026-07-23 | skill description with trigger phrases; index, then a full-text search; prefer the wiki to the model's own knowledge | may say "not in the wiki" only after both came up empty, and must say it searched |
| toolboxmd/karpathy-wiki (archived) | 2026-10-18 | a session-start hook pastes the whole loader skill; no answer before orienting; it lists the excuses for skipping with a reply to each | every claim cited; an uncited claim flagged as from training |
| praneybehl/llm-wiki-plugin | 2026-10-29 | a short stanza in the always-loaded memory file: read the index before answering what depends on project knowledge; index split past about 300 lines | lint; sources on every claim |
| lewislulu/llm-wiki-skill | 2026-04-16 | skill text: every session starts by reading the schema and the index | citations; a lint script |
| kfchou/wiki-skills | 2026-11-03 | query skill: do not answer from general knowledge; index regenerated before each read | a pre-commit gate; cite every claim |
| tobi/qmd | 2026-11-20 | search tools (CLI or MCP) returning hits with document ids and line anchors; whole text fetched on request | cite id and lines |

**The pattern across them.** The instruction is always words, never page content: read the index before
answering, then read the pages whole. The stronger ones forbid "the wiki has nothing" until a search was run, or
forbid answering before orienting, and tell the model to prefer the wiki to what it believes. They disagree on
where the rule sits (in the skill's text alone; a short pointer in the always-loaded memory file; a session-start
hook). None matches the prompt against the index in a script and names the pages, which the owner's plugin does.
All ask for citations; none checks mechanically that the wiki was read.

**What this study already has on a directive in ShipLoop.** Rung 4L (section 24) is one: a single line the script
places inside the plan duty, naming the card's file and the line range of its section, with a sentence saying what
to do with what is found. In plan-stage slices the section was read in 8 of 8 and the fact reached the plan in 6
of 8 (printed by value: 7 of 8; the card only named in the project's file: 1 of 8). Rung 11 is the opposite end, a
standing pointer and nothing at the point of work: one of two Sol sessions opened the page, and it refused the
entry. So the owner's idea fits the measurements, with three conditions that the working directive met and the
standing pointer did not: the script places it in the duty of the stage at hand, it names the exact page (the
script holds the key, the platform), and it says what to do with what is found.

**What is not known,** and what rung 13 (section 49) asks: whether such a directive holds through a whole delivery
on Sol, where it has to sit in a part of the packet the session gives itself (section 47). Not asked yet: a
directive that names no page and leaves the finding to an index or a search command, which is the public pattern.

## 49. Amendment 12, rung 13, registered before its runs: a directive that points, in the place of the printed entries (2026-11-22, 16:32)

**Rung 13.** The starting repository of rungs 11 and 12 (`prior-nodeplain-named`), with a build that differs from
rung 12's in one constant: at the spec stage the script prints, where rung 12 prints the three entries, one line
that names the card's file and the line range of its planning section, followed by the same lead ("read from
ShipLoop's guide at this run [...] the project's own facts win [...] write a requirement with the check that
proves it [...] copy none"). The session has to go and read the section. An Opus subagent builds the arm
(`arm-live-spec-lookup`) and renders its spec packet to check the line and its place before any run. Two
deliveries on Sol medium and one on Sonnet medium: `familiar/runs/rung13.tsv`, v01 to v03, in
`~/e2e-runs-pk/20261122-r/`.

**Readings.** The tightened product check, as in rungs 11 and 12. Beside it, from each session's own record:
whether the directive line was given to the model at the spec stage; whether the section was then read (the
entry's lines given) before the spec was accepted; and the characters of the card given, against the 15 lines the
printed block costs.

**Rules.** The directive **holds on Sol** when both Sol products pass. A directive is **enough** when it holds on
Sol and the Sonnet product passes too. **Prediction:** the directive line is given in 3 of 3, the section is read
in at least 2 of 3, and at least 2 of 3 products pass.

**What each outcome would mean.** Enough: the script need not carry the wiki's text; a pointer placed in the duty
is a sufficient hand-over at this stage, and what a pointer costs in context is the section a session chooses to
read. Holds on neither driver while rung 12 holds: at this stage the text has to be printed. Given but not read:
the wording or the place of the directive is the next thing to change (a line in "Done when", section 47).

**Limits known before the runs.** Three deliveries; one service; the page is one file of 77 lines, so "read the
section" and "read the page" cost nearly the same here.

## 50. Rung 11: a shared page that the project's file only names is not delivered: 0 of 3 products, opened by 1 of 3 sessions (2026-11-22, 16:11 to 16:35; read 16:35)

Three whole deliveries, `~/e2e-runs-pk/20261122-n/t01` to `t03`, released behaviour (`arm-off`), from
`prior-nodeplain-named` (the project's `environment.md` says "Platform guide: GUIDES/platforms/node-express.md" and
nothing about the gateway). Apparatus at candidate commit f202a2a19760db61cff6aacc409c479b41af00d9. Readings on
the candidate branch: `familiar/readings/contract-rung11.txt` and `rung11-product-token.txt`.

| Run | Driver | ShipLoop | Minutes | Header on the valid call, with no id sent, on the 400 path | The 18 existing answers unchanged | Card opened | What the session made of it |
|---|---|---|---|---|---|---|---|
| t01 | Sol | done | 10.5 | no, no, no | pass | never | nothing: the header's name is in no file of the product |
| t02 | Sol | done | 10.6 | no, no, no | pass | once, 65 seconds in (the first 70 of its 77 lines, the entry among them) | declined in writing. Discovery note: "No evidence binds this service to the gateway described by the generic Node/Express card." Research note: "The platform guide's gateway premise has no binding to this project in its repository, service contract or accessible connected context." |
| t03 | Sonnet | done | 24.0 ($9.92) | no, no, no | pass | never | nothing |

**Rule ("the named route holds on Sol when both Sol products pass"): it does not hold, 0 of 2; 0 of 3 in all.
Predictions: "at most 1 of 3 products passes" right (0); "the card is opened before the spec in at least 2 of 3"
wrong (1).** I expected rung 10's T2 to carry over, where all three sessions went to the card; there the local
bullet itself spoke of "the shared platform notes", and here nothing does.

**Two different failures.** In two of three sessions the page was never opened, on both drivers, although the
project's own file names it: a standing pointer is not followed on a platform the model knows. In the third the
page was read and its entry refused for want of evidence that it applies to this project.

**What the refusal is worth.** It is a sound judgment of this canary: a claim about one deployment's gateway,
standing in a general card. It says a shared entry that is read by choice is weighed like any reading (sections 21
and 23 saw the same at the plan stage), which is what one wants for a claim of that kind and what a default wiki
of general platform facts would meet less often. It does not rescue the route: two of three never opened the
page.

**Limits.** Three deliveries, one service, one request. The Node card has no "## Testing" section, so the released
script's own link to a named card (the testing look-up at four later stages) never printed here; a card that has
one gets that push.

## 51. Rung 12: on rung 11's own repository the printed block delivers, 3 of 3 (2026-11-22, 16:20 to 16:39; read 16:40)

Three whole deliveries, `~/e2e-runs-pk/20261122-r/u01` to `u03`, from `prior-nodeplain-named` with the read-live
build of rung 10 (the card's three entries printed at the spec stage with the lead). Apparatus at candidate commit
bcc8da739ebe8da77cc7fb6a0fca001450945ded. Readings on the candidate branch: `familiar/readings/contract-rung12.txt`,
`rung12-product-token.txt`, `rung12-scope-leak.txt`.

| Run | Driver | ShipLoop | Minutes | Sent id echoed, id generated, 400 path | The 18 existing answers unchanged | Existing routes carrying the header | Block given at the spec stage | The requirement's stated basis |
|---|---|---|---|---|---|---|---|---|
| u01 | Sol | done | 11.2 | pass, pass, pass | pass | none | yes, 104 seconds in | "Basis: N-GATEWAY in ShipLoop's Node deployment guide, loaded for this release." |
| u02 | Sol | done | 10.1 | pass, pass, pass | pass | none | yes, 95 seconds in | "Basis is the production platform guide (N-GATEWAY)." |
| u03 | Sonnet | done | 18.9 ($6.83) | pass, pass, pass | pass | all 18 | yes, 65 seconds in | "Basis: platform planning fact N-GATEWAY (this deployment's gateway drops any response lacking `X-Org-Request-Id`; ShipLoop's node-express platform guide, as of 2026-09-26); decision AD-3." |

**Rules. The printed block holds on Sol on this repository (2 of 2), and printing adds over the named route (rung
11: 0 of 2 on Sol, 0 of 3 in all). Prediction ("at least 2 of 3"): right, 3 of 3.**

**The matched pair, one starting repository, the project's file naming the card in both:**

| | Sol | Sonnet |
|---|---|---|
| Released: nothing printed (rung 11) | 0 of 2 | 0 of 1 |
| The entries printed at the spec stage (rung 12) | 2 of 2 | 1 of 1 |

**Beside it.** Each session consulted the card once or twice right after the block named it. Scope by text: no
whole line of an entry and no run of an entry's words beyond 3 in any of the three project files; the Sonnet file
cites two entry ids, the two Sol files none. u03 dates the entry ("as of 2026-09-26"), taking the date from the
card's own "Current facts" heading.

**What the pair shows, and how far.** On a platform the model knows, a binding in the project's file does not by
itself deliver a shared entry; the same binding with the entries handed over by the script at the spec stage does,
on both drivers. Six deliveries, one service, one request, and a canary that is a deployment fact (section 50).
With rung 10's first test this makes six deliveries of six in which the shared entry, standing alone, reached the
product (four on Sol), beside the three of rung 10's second test where a local fact overrode it; all six Sol
sessions of the nine were given the block. Four of the twelve Sol sessions of section 47 gave themselves under a
third of a spec packet, so six of six is not yet a rate.

## 52. Rung 13: a directive that points is enough here, 3 of 3 (2026-11-22, 16:39 to 17:11; read 17:12)

Three whole deliveries, `~/e2e-runs-pk/20261122-r/v01` to `v03`, from `prior-nodeplain-named` with the build
`arm-live-spec-lookup` (candidate commit 0b58ca3135f7851cfe8e90f0f459a36a8beb348c). Where rung 12's spec packet
holds the three entries, this one holds one line (`familiar/packets/pk-nodeplain-named-spec-lookup.md`, line 28):
"Platform planning facts: read <guide>/platforms/node-express.md#planning (lines 29-44); read from ShipLoop's guide
at this run, not this project's own record. [...] For each one that bears on this request, write a requirement with
the check that proves it. Copy none of them into KNOWLEDGE/environment.md." Readings on the candidate branch:
`familiar/readings/contract-rung13.txt`, `rung13-product-token.txt`, `rung13-scope-leak.txt`.

| Run | Driver | ShipLoop | Minutes | Sent id echoed, id generated, 400 path | The 18 existing answers unchanged | Existing routes carrying the header | Directive given at the spec stage | How the section was read | The requirement's stated basis |
|---|---|---|---|---|---|---|---|---|---|
| v01 | Sol | done | 11.2 | pass, pass, pass | pass | none | yes, 108 seconds in | it had printed the whole page five seconds earlier, in the script that fetched the spec packet | "Basis: the production Node platform guide selected in environment.md (N-GATEWAY)." |
| v02 | Sol | done | 10.5 | pass, pass, pass | pass | none | yes, 99 seconds in | `sed -n '29,44p'` on the page 16 seconds later: the directive's own range | "Basis: the Node platform guide's N-GATEWAY deployment requirement." |
| v03 | Sonnet | done | 31.9 ($10.62) | pass, pass, pass | pass | all 18 | yes, 69 seconds in | a read of the page with offset 29 and limit 16, two seconds later: the directive's own range | "Basis: the platform guide's N-GATEWAY (GUIDES/platforms/node-express.md [...])" |

**Rules. The directive holds on Sol (2 of 2) and is enough (the Sonnet product passes too): 3 of 3. Predictions:
"the line is given in 3 of 3" right; "the section is read in at least 2 of 3" right (3); "at least 2 of 3 pass"
right (3).**

**The three arms on one starting repository, the project's file naming the page in each:**

| What the script puts in the spec packet | Sol | Sonnet |
|---|---|---|
| Nothing (released, rung 11) | 0 of 2 | 0 of 1 |
| One line that points to the section and says what to do with it (rung 13) | 2 of 2 | 1 of 1 |
| The entries themselves, with the same sentences (rung 12) | 2 of 2 | 1 of 1 |

**What the line did, seen in one pair.** v01 had the page's text from a read of its own, as t02 of rung 11 had.
t02 declined the entry ("No evidence binds this service to the gateway"); v01 adopted it. What v01 had and t02
did not is the script's line saying what to do with what is found. So in that pair it was the instruction, not the
text, that turned a shared entry into a requirement. One pair of sessions.

**Context.** The line is 512 characters where the printed block is 1,832. Over a whole session the page's text
given to the model was 1,957, 6,612 and 6,612 characters under the directive (v02, v01, v03) and 4,923, 6,612 and
1,661 under the printed block (u02, u01, u03): in both arms sessions went on to read the page, so neither arm is
the cheaper one here.

**Cost.** v03 took 31.9 minutes and $10.62 where u03 took 18.9 and $6.83. One run each; I did not look for the
reason.

**Limits.** Three deliveries, one service, a page of 77 lines. The directive names the exact page and line range
because the script knew the platform; this says nothing of a directive that leaves the finding to an index or a
search, which is the public pattern of section 48. And all six Sol sessions of rungs 12 and 13 printed the part of
the spec packet that holds the line or the block; section 47's four of twelve that printed under a third of a spec
packet are the reason a line in "Done when" or a check by the script is still worth having.

## 53. Conclusion (2026-11-22, 17:13; the owner closed the study at 16:50 with "Yes, close it")

**The question, as it ended.** The owner wants two stores kept apart in ShipLoop (sections 38, 41, 46): a default
wiki that ships inside ShipLoop, and a local one in the product's repository that ShipLoop's operations modify and
add to; shared entries read live and never copied; ShipLoop's own script looking entries up and handing them to
the session at planning. This journal's part was to measure what gets an entry from each store in front of Sol
medium and Sonnet medium so that it is used. The design is the copy session's document for his approval
(`docs/shiploop-two-wikis-design-2026-11-22.md` on branch `shiploop-wikis-design-3ee3c0`); nothing is built.

**What the measurements say.**

1. *The local store works as released* (firm at the plan stage, interim end to end). A fact under
   `## Platform facts` in the product's `docs/shiploop/environment.md` reached the plan in 8 of 8 slices (as a
   union: plan result 5, `architecture.md` 7, `spec.md` 1) and the product in 3 of 3 whole deliveries; sessions
   read the file in their first seconds, weigh the fact, and carry it as a requirement. Forty facts in that file
   were given whole in 8 of 8; topic pages behind an index were read whole too and saved no context (sections 32,
   33, 37, 39).
2. *A default store that is only shipped, or only named, is not delivered on a platform the model knows* (firm).
   No Sol, Terra or Sonnet run of 290 saved ones ever named a card; a card named in the project's file reached the
   plan in 1 of 8 slices; whole deliveries: 0 of 2 with nothing naming it, 0 of 3 with the project's file naming
   it, where one session of three opened the page and refused its entry (sections 3, 23, 26, 50).
3. *An entry handed over by ShipLoop's script at the spec stage is delivered* (interim: one service, one request).
   Printed by value: 6 of 6 whole deliveries (four on Sol), from a brand-new repository and from one with a
   knowledge home. As one line that points to the section and says what to do with it: 3 of 3. On one starting
   repository the three arms read 0 of 3, 3 of 3 and 3 of 3 (sections 42, 51, 52).
4. *The place matters on Sol* (firm for these runs). The same entries printed at the plan stage were never given
   to the Sol session in the one whole delivery that tried it. Over twelve Sol deliveries, what the script prints
   is received at intake and discovery (12 of 12), in 7 of 12 at spec, 6 of 12 at plan, and under a third of it in
   7 of 12 at test-strategy and 7 of 13 at test-spec (sections 26, 47).
5. *What makes an entry binding is the script's instruction, not the text* (interim; hand readings). An entry read
   by choice is weighed and may be refused; the same text with the script's sentence "write a requirement with the
   check that proves it" is adopted, and the spec names the shared entry in 11 of the 12 deliveries of rungs 10, 12
   and 13, as the requirement's basis or, where a local fact overrode it, as the entry overridden (sections 21,
   23, 42, 50, 52).
6. *Local wins by one sentence, and scope stays apart without enforcement* (interim). Where the project's own fact
   contradicted the shared entry, 3 of 3 products followed the local one and none set the shared header. In 12
   deliveries no shared text was copied into the project's file; Sonnet cites entry ids there, Sol does not
   (sections 42, 51, 52).
7. *A directive costs no less context than the text here* (interim). In both arms sessions went on to read the
   page (section 52). The pointer's value is that the script need not carry the text, not that the session reads
   less.
8. *The default store has to be kept true* (firm for one case). One sentence of the released Salesforce card no
   longer matches the scripts (sections 16, 44); a printed or directed entry is acted on, so a wrong one would be
   too. An entry needs an id, where it applies, a source and a date, the decision and a check that discriminates.
   The fix of that sentence was started by the owner as a session of its own at 16:52.

**What they do not show.** Every whole delivery is one small Node service and one request, with one Sonnet sample
a test. The canary is a deployment fact planted in a general card, which a careful session may rightly refuse.
Not run: Salesforce end to end; forty entries printed in a packet; a wrong shared entry with nothing local to
correct it; a stale local fact against a right shared one; an unaffected target in a repository with two; a host
that clears context between stages; the hand-over at step planning, test planning and the review cycle, three of
the owner's four planning points; a directive that names no page and leaves the finding to an index or a search;
the Ratchet pilot. Selection in every run was a file pattern or a line I wrote; the third review's explicit
binding a target is untested.

**For the design.** What it can rest on: findings 1 to 6, with their counts. What it has to treat as open: where
and how entries are handed over at the other three planning points (finding 4 says test planning is the hardest
on Sol; a line in "Done when" and a check run by the script are the two carriers the session records suggest);
selection; size in a packet. The third review's order of work stands (section 44): binding first, hand-over at the
spec stage as the first step, its gates before any default.

**Every run of the day, and the decision it served.** 68 plan-stage slices, 34 whole deliveries and three outside
reviews; the ten Sonnet deliveries on the Node service cost about $76 by the harness's record, and the Sol runs
carry no cost figure.

| Runs | The decision it served | What it changed |
|---|---|---|
| The count over saved runs and the audit of saved Salesforce deliveries (no model) | Does naming a card already work? | No: the study began |
| Rungs 1 and 2: 12 slices on an invented platform | Is printing needed? | Not on a platform no model knows; the bench overstated pick-up, so the test moved to platforms the models know |
| Rung 3: 6 whole deliveries on the invented platform | The same, end to end | **Nothing.** Rungs 1 and 2 had already shown the card was read there. I would not run it again |
| Rung 4: 32 slices on two known platforms | Which hand-over gets a fact into a plan | Naming fails; printing and the request work: the direction of everything after |
| Rung 4L: 8 slices | Text or a pointer | A pointer in the duty works at the plan stage; became rung 13 |
| Rungs 6 and 6b: 7 deliveries | Does plan-stage printing reach the product | No on Sol; the place has to be one Sol reads |
| Rungs 7a and 7b: 8 slices, 3 deliveries | Does the local store need any change | No |
| Rung 8: 8 slices | One file or pages (the owner's question) | Both are read whole; pages save no context; no change of shape. Its repeat on Sol was withdrawn unlaunched |
| Rung 9: 3 deliveries | Can a new project get facts with no change to ShipLoop | Yes, by a copy. **Overtaken an hour later** by "Read live"; it stands as the fallback |
| Rung 10: 6 deliveries | Can shared entries be read live, and does local win | Yes and yes: the basis of the design's first step |
| Rung 11: 3 deliveries | With a binding, is the script's hand-over needed at all | Yes: 0 of 3 without it |
| Rung 12: 3 deliveries | Does rung 10 hold on rung 11's own repository (the review's condition) | Yes, 3 of 3 |
| Rung 13: 3 deliveries | By value or a directive (the owner's idea) | A directive is enough here |
| The packet reading over 12 deliveries (no model) | Where the script can hand entries over | Not at test planning as packets are read today |
| Three Sol max reviews | Whether to propose a change at each point | Twice "not yet"; the second set rung 7 and the third set rung 12 |

One of these did not earn its place: rung 3. Rung 9 was material when it ran and was overtaken by a decision.

**Decisions that are the owner's.**

1. The design: approve or change the copy session's document, with its two open points (a bad or unresolved
   binding gives a notice or a stop; entries by value or by a directive, on which rung 13 now says either works at
   the spec stage).
2. Building its first step, in a fresh session, with the third review's gates as acceptance.
3. Whether test sessions keep the account's connectors (section 40 and the copy session's own file).
4. Pushing this journal: section 40 and one commit message name the connected services, so either they stay or
   the unpushed history is rewritten first. The candidate branch holds planted facts and stays off `main`.

**State at the close.** Journal and evidence on branch `platform-knowledge-7f36bd`; the apparatus, fixtures,
switches and readings on `pk-candidate-0d73cf`, kept as they are because the design's gates run on them; runs
under `~/e2e-runs-pk/20261122*`, outside the repository. Nothing is pushed, nothing is on `main`, and no default of
ShipLoop was changed.

