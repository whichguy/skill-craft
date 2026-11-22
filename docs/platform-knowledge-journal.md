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
  Code hooks. One hook (`wiki-notify`) puts short previews in front of the model and `wiki-load` then loads whole
  pages. A memory note of 2026-09-24 records it as disabled after a hook-cost audit.
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
applies", "No deploy, CI or platform guide") among the silent ones. Every wording the pattern missed was read by
hand and each denies a guide, so the tool now counts any mention that names no card as "none". No other count moved.

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
- **A named card was always read, and read whole.** All 18 runs that named a card opened it, and the model was
  given a median of 100% of the card's own lines (81% to 100% over 21 cards).
- **When a card is opened at all, it is at discovery**: 32 of the 44 first opens; the rest are spread over seven
  other stages, one or two each.
- **The script's link fired in 4 runs**, each a Salesforce run (three on Grok, one Terra trial). It depends on the
  name the model never writes.
- Over all 382 asked runs the builder opened any card in 37 and was given any card line in 40.

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

1. The route that loads a card today starts with the model writing the card's name. The three families that drive
   the runs now (Sol, Sonnet, and Terra before them) do not write it, so nothing after it happens. This is the same
   finding as "gates, not guides", now counted for platform cards.
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

## 7. Review of the intention and the design (pending)

Sent to the latest Sol at max on 2026-11-22; question and verbatim answer are kept under
`docs/experiments/platform-knowledge-20261122/review/`. This section is filled when it returns.
