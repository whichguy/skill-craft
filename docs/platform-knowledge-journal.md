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

