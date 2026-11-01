---
Execute: inline
Status: research done; QB1 to QB5 run and scored; the terms-and-references category (K12) built and live-tested on 2026-11-01 (§5.6) and
  released after this entry (its version is in CHANGELOG.md); recommendation in §0 and §8; its send-back excess is being replicated on a new case, R3 (§5.7, registered 2026-11-01)
Opened: 2026-10-31
Consumer: the owner, who asked how harnesses enrich a prompt, whether questions beat statements and cost fewer tokens, and
  whether a question bank belongs in ShipLoop's intake; later, a session that changes intake duty item 9 or adds term and
  conflict handling to intake, which reads §6 for the evidence a change must beat and §7 for the candidate bank and the
  routing rule
Follows: docs/shiploop-planning-pipeline-2026-10-30.md (the study), docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md
  (the verdicts that shipped the catalog), docs/experiments/key-questions-intake-20261030/ (X1 and the earlier framework and
  literature reports)
Evidence: docs/experiments/question-bank-20261031/ (README.md holds the pre-registered rules and the results; scripts, prompts,
  outputs and judge answers beside it); survey notes are quoted below, the full notes were not committed (scratch)
---

# Intake: a question bank, statement wording, and the ask, probe or default rule (2026-10-31)

The owner, 2026-10-31: research how software development harnesses take a prompt and enrich it, do research, or expand it;
look at highly starred repositories and the last six months of articles and forums; ask whether questions could flesh a
prompt out in more detail at a lower token cost, and whether a question bank should replace statements about how to
clarify; when something is conflicting or ambiguous, either experiment to derive the answer from the environment or ask the
user; this belongs to ShipLoop's phase right after the prompt; use side tests on a big prompt if useful; use Codex as the
harness and Terra 6.1 Extra High as the model. Mid-task: the owner's prompts often name installed skills or internet
jargon, which should be resolved by looking before anyone is asked.

## 0. The answer in brief

- **How harnesses enrich a prompt.** Every vendor harness does it with rules about when to ask plus an ask-tool schema: ask only
  for a decision the user should make; for a conventional default or a fact the code shows, take the obvious one, say so and go on.
  The large ones now explore first and then ask about preferences with a recommended default, and their unattended modes pick a
  default and record it; some hosts answer their own unanswered questions after 60 seconds (Codex by default; Claude Code did, and the survey agent reports it
  is now opt-in). The survey found no vendor shipping a question bank for intake. The
  banks that exist are community skills: a prompt-improver hook with a 189-token gate that loads a bank of about 4.5k tokens only for
  vague prompts, and a 308k-star grilling skill that asks the whole frontier of ready questions, each with a recommended answer, and
  sends fact-finding to sub-agents. The survey found no test of question wording against statement wording on intake or clarification guidance; the one
  matched-content comparison, on classification prompts with 2023 models, found questions and orders about equal (§2 to §4).
- **Do questions flesh a prompt out more, at lower token cost? Not by being questions.** On this repository's measure (Codex, Terra
  6.1 xhigh, four vague requests, 38 decisions) what lifted coverage from 0.47 to 0.92-0.96 was an explicit list of items the model
  must answer, however it was worded and whoever wrote the questions. With the content fixed, wording moved nothing on the shipped
  ledger (questions 0.926, statements 0.942; cost ratio 0.995) and, on a fixed bank, traded 3.7 points of coverage and 7 points of
  agreement against 7% of the tokens (§5.1).
- **A fixed bank is not a cheaper ledger in general.** It writes 7% to 14% fewer output tokens than the model-written ledger on a vague
  request, but commits more defaults that conflict with the real request (agreement 0.61 to 0.68 against 0.74) and more noise, and on a
  long request with tools it writes more (4% to 5% above the same ledger with the extra lines). A 12-word cap cut a further 15% and cost 7 to
  11 points of recall. The pre-registered bar for replacing the shipped ledger was missed, so it stays (§5.1, §5.2).
- **The token cost is small and sits elsewhere.** A whole intake is 2k to 4k output tokens; reading the repository costs 26k to 35k
  uncached input tokens. Both are small beside a run. The shipped ledger paid off downstream (0 of 6 proof-order send-backs against 4
  of 6 in its live A/B), which no experiment here re-measures.
- **Skills and jargon (the owner's note).** On a long dictated request, a terms-and-references category with a look-it-up-first
  sentence raised the share of items answered right from 0.56 to 0.73 (the same plus the bank: 0.74 and 0.80; exact p 0.004 to 0.012,
  five outputs each). Installed skills named in the request were tied to the host's list 0.73 to 0.93 of the time instead of 0.33; an unknown
  name was flagged as undefined 0.4 to 0.8 of the time instead of never (the shipped catalog called it context); unflagged assertions
  fell from 1.6 per output to 0 to 0.4. It cost about 12% more output tokens (§5.3). Exploratory: one request, five outputs per arm. On three new requests over three other repositories (QB5, 60
  outputs) the same line plus sentence raised items right from 0.52 to 0.67 (p 0.008, ahead in every request) for 8% more output tokens;
  the fall in silent assertions (0.67 to 0.20 per output) missed the registered p < 0.05 (p 0.115) (§5.5).
- **Conflicts and false premises were already caught.** Every arm found the contradictions in the request and the filter behaviour the
  docs state wrongly, B included, so a conflicts category added nothing here. What every arm missed was what the files show about the
  cost of the change: no template for closed tickets, a dedupe that holds only while a notification is pending, a data file saved on
  every change.
- **Ask, probe or default.** With a person available and a rule to ask only what the repository and the skills cannot settle and where
  two readings lead to different work, intake asked one question per output, the same one every time: which weekly-report window,
  because the request's premise was false and no default is safe. It defaulted and recorded the rest. An explicit look-it-up order made
  the model read more (10 to 14 shell commands against 7.6), while earlier tests found models rarely run a probe merely because it is
  allowed (§5.4).
- **Recommendation and outcome (updated 2026-11-01).** Keep intake item 9 as shipped and do not build the bank, the 12-word cap or a
  rewording of the catalog. The evidence supported one addition, a terms-and-references category (K12) with the look-it-up-first sentence:
  it replicated on three more requests (QB5) on the main measure, one registered condition failed (silent assertions, p 0.115), and the
  owner said "Yes test all this then Commit and merge everything to main and publish". It was built, run live on the Codex harness (19
  runs, all passed, all five registered rules held, one unregistered excess of send-backs did not replicate) and released (§5.6, §8, §9).
  What the live runs do not show is the benefit: their requests are fully specified.

## 1. How I read the request's own terms

The owner's standing note (memory `resolve-user-jargon-before-asking`) applies to this very request, so the readings are
written down with their source and my confidence.

| Term in the request | Reading | Settled by | Confidence |
|---|---|---|---|
| software development harness | the program around a model that runs a coding loop: prompts, tools, permissions, plan modes (Claude Code, Codex CLI and so on) | this repository's own docs call them hosts; the forum survey's glossary: harness engineering is the tools, checks and context around a model | high |
| ship loop; the phase right after the prompt | ShipLoop, the `skill-craft:shiploop` skill, and its first stage `intake` | the session's skill list; docs/shiploop-planning-pipeline-2026-10-30.md §2.1 | high |
| question bank | a fixed, reusable list of questions the model answers about a request, as against guidance written as statements | requirements-engineering usage (context-free questions); the nearest thing in the repository is the K1-K11 catalog of intake item 9, which names categories and has the model write its own questions | medium: it could also mean questions put to the human; QB1 tests the first reading, §7's routing rule covers the second |
| statements about how to clarify a prompt | imperative guidance such as intake duty items 1-8 ("cover each request sentence ...") | skills/shiploop, the X1 prompts | high |
| flushed out | fleshed out | context | high |
| experiment to derive information from the environment | ShipLoop's `inspect`, `research` and `experiment` routes | intake item 9 | high |
| prompt the user | the `person` route; in other harnesses an ask-user tool | item 9; §2 | high |
| Codex as the harness | OpenAI Codex CLI 0.166.0, `codex exec`, run isolated as the E2E harness runs it | `codex --version`; docs/experiments/question-record-20261031/run.py | high |
| Terra 6.1 Extra High | `gpt-6.1-terra` at `model_reasoning_effort=xhigh` | `~/.codex/models_cache.json` lists it with xhigh; a live call answered in 3.4 s; memory `experiments-use-sonnet` | high |

## 2. What other harnesses do

Three survey agents read sources in parallel; I verified every star count and push date below against the GitHub API on
2026-10-31 and checked the existence, title and date of a sample of the issues and posts they cite. The mechanism classes and
wording forms (S for statement, T for tool schema, Q for question) are the agents' readings of each repository's files and are
not independently verified. "Closed" means a product with no source.

| Harness or add-on | Stars (2026-10-31) | Mechanism | Wording | Notes |
|---|---|---|---|---|
| Claude Code (anthropics/claude-code; prompts via Piebald-AI/claude-code-system-prompts, 13,050 stars) | 154,090 | plan mode; an ask tool for decisions the user should make; auto mode that prefers assumptions | S + T | ask only when blocked on a real decision; for conventional defaults or facts the code shows, pick the obvious one, say so and go on (about 60 tokens of guidance) |
| Codex CLI (openai/codex) | 132,491 | plan mode explores first, then asks about preferences with a recommended option; `/goal`; unanswered questions auto-resolve | S + T | asks before exploring only when the prompt contradicts itself |
| Gemini CLI | 108,655 | plan mode, YOLO and headless modes | S + T | evals without published rates |
| OpenCode (anomalyco/opencode) | 223,617 | an ask tool gated by permission; the model decides | S + T | |
| Copilot in VS Code (microsoft/vscode) | 194,427 | Plan agent; Autopilot proceeds on its own | S + T | logs how often the recommended option is accepted; unpublished |
| Cline; Kilo; Roo (archived 2026-05-15) | 71,119; 27,818; 24,254 | plan and act modes, deep planning; an enhance-prompt button that rewrites; an ask-followup tool | S; T | |
| OpenHands, Zed, Crush, Aider | 92,367; 92,465; 28,901; 49,856 | plan modes or ask; Aider's last push 2026-05-22 | S | |
| Devin, Augment, Windsurf, Factory, Replit, v0, Lovable | closed | Devin asks when confidence is low and shows a plan first; Augment rewrites a prompt using repository context; the rest ask mostly in plan modes | S | Devin's own figure (green plans merge about twice as often as red) has no stated sample or method |
| severity1/claude-code-prompt-improver | 1,965 | a hook on every prompt: a cheap gate, research, then 1-6 questions only for vague prompts | Q gate, S, Q bank | about 189 tokens per prompt for the gate; a bank of about 4.5k tokens loaded only for vague prompts |
| mattpocock/skills (grilling, grill-me) | 308,349 | the user invokes it; each round asks the whole frontier of questions whose prerequisites are settled, each with a recommended answer; facts go to fresh sub-agents, decisions to the human | S + T | rejects multiple-choice pickers because they steer; no cap on questions |
| EveryInc/compound-engineering-plugin | 25,798 | brainstorm and plan with research agents; headless runs take a default and record it under Assumptions | S + T | checks terms against a concepts file and verified code |
| addyosmani/agent-skills (interview-me) | 112,249 | asks on an underspecified request; refuses to proceed unattended | T + S | the opposite stance to Compound's |
| google/elephant-goldfish-model | 7,689 | asks, then reviewers in a zero-context session must find the questions answered | Q (a Heilmeier-style set, about 290 tokens), S | |
| humanlayer/humanlayer (research questions) | 12,733 | investigate; the research questions deliberately hide the task from the researcher | Q template | |
| SuperClaude; pm-skills; taches | 23,919; 27,575; 1,986 | ask; assume; ask | Q examples; a four-risk bank; 5W slots | |

What the survey found, with the owner's questions in mind:

- **The survey found every vendor writing rules about when to ask plus a tool schema, and none shipping a question bank for intake.** The banks that exist
  are community skills, loaded on demand or used as an exit test. Nobody has measured question wording against statement
  wording (this matches the earlier eight-framework pass in docs/shiploop-planning-pipeline-2026-10-30.md §5).
- **Two opposite stances on unattended runs.** Claude Code, Codex, Gemini, Copilot and Compound pick a default and record it;
  interview-me refuses and flags a blocker, and the grilling skill calls an unanswered interview the agent's own opinion. ShipLoop's
  S-14 (record defaults; prompt only when nothing can proceed) is the first stance.
- **Some hosts answer their own questions.** Claude Code's ask tool told the model to continue after 60 seconds without an answer
  (anthropics/claude-code issue 73125, 2026-07-02, closed) and Codex auto-resolves questions after 60 seconds (openai/codex issue 28969,
  2026-06-18, open). A host-supplied answer can be a default, not consent. The survey agent reports Claude Code later made the timeout opt-in (a
  setting from version 2.1.200); I did not check that.
- **Vendors are cutting statement guidance.** Anthropic's post of 2026-07-24 says it removed over 80% of Claude Code's system prompt
  for newer models (claude.com/blog, "The new rules of context engineering for Claude 5 generation models"; the survey agent reports
  it also found no measurable loss on coding evals, which I did not check).

Eight ideas the survey rated transferable to an unattended intake (agent's list, my condensation): split facts from preferences and
explore before any question; ask-and-record instead of blocking; hold the values only a person can supply and one-way steps,
finish the rest and raise the held asks in one batch at the end; block only by a rule a script can check (the same blocker three
turns running); sort the request into stated, inferred and out of scope; run a cheap check on every prompt and load the large bank
only when the prompt is vague; ask in dependency order and send fact-finding to fresh-context sub-agents; check contradictions and
jargon against the repository before treating the user's wording as settled.

## 3. What practitioners said in the last six months (2026-05 to 2026-10)

From the forum and blog survey (one agent; Reddit was unreachable). Dates and sources are the agent's; I confirmed the items
marked "checked".

- **Interviewing changed shape.** The grilling skill went from one question at a time to a whole round per pass, each with a
  recommended answer that "yes" accepts (2026-07-16), with no quality data. Anthropic's field guide (Thariq Shihipar, 2026-07-06)
  says interview one question at a time with the architecture-changing question first, and, mid-build, take the conservative option, log
  it and continue.
- **Assume and record is in use.** A small suite asks up to four questions once, then logs its rulings with reasoning and risk
  (contextfirst.blog, 2026-10-18; page checked); "tell, don't ask" in an AGENTS.md (Hacker News 2026-06-21); users want an
  end-of-run list of questions the agent answered itself (Hacker News 2026-07-02).
- **Detail can hurt.** Plans that turned into copy-this-code blocks (Hacker News 2026-10-19); grilled plans becoming over-prescriptive
  (2026-10-27); Superpowers 6 found tests, interfaces and structure carry a plan and implementation bodies add little (2026-06-15).
- **Costs people report.** A vagueness-gate hook costs about 189 tokens a prompt; xhigh costs two to four times medium without reliably
  more passes (SlopCodeBench, 2026-10-15); caps on questions cluster at 3 to 6, while full grilling runs 20 to 60.
- **A questions-before-PR repository** pairs each question with a passing check (NickyHeC/ask-before-you-pr, created 2026-10-22,
  one star; checked); the author reports unmerged PRs fell from 62% to 14%, self-reported.
- **Skill names.** Users report Claude Code loads a slash skill only at the start of a prompt and hides skills marked
  `disable-model-invocation` from the model (anthropics/claude-code issue 92769, 2026-09-08; checked).
- **A ready glossary exists:** mattpocock/dictionary-of-ai-coding (created 2026-05-01, 5,328 stars, last push 2026-09-24; checked), 71
  plain-English entries. The agent's own 25-term glossary (grill-me, frontier, AFK and HITL, Ralph loop, harness engineering, /goal,
  xhigh, slop, caveman and others) is in the scratch notes; its readings are not independently verified.

## 4. What the research says

The earlier graded report (docs/experiments/key-questions-intake-20261030/question-evidence.md) stands: asking helps most when
someone who knows the intent answers; without one the gains are small and models rarely find their own ambiguities; understanding
the request is the largest failure component for autonomous agents. The new pass added the following; I checked each paper's
title, date and abstract on arXiv (all 15 exist), and the numbers beyond the abstracts are the agent's reading of the papers.

- **Wording alone probably matters little.** Leidinger et al. (arXiv 2311.01967) varied mood on matched content: questions and orders
  were about equal and both generally ahead of statements, on models up to 30B and single-word classification tasks; modal verbs
  mattered more. It is the only matched-content comparison found. No one has tested it on intake guidance.
- **What helps is an explicit item the model must answer.** Models recognise ambiguity but rarely ask (Su et al., 2605.25284). A
  fixed ten-question checklist answered before generation raised fidelity from about 55% to about 75% on three model families,
  and review afterwards added nothing (Goel et al., 2610.37830; smart contracts only). A checklist-improved prompt scored 7.50 of 8
  against 5.67 raw and 6.67 for a clarifying-question prompt, with fewer tokens than either (Ghosh et al., 2605.20149; abstract read).
- **Prune a bank by behaviour.** Keep the questions whose answers change what gets built (Fang et al., CONTRA, 2610.01769; Goel et
  al. ranked questions by how much their answers change the result and beat the checklist's own order by 7.8 points).
- **Route each uncertainty to the source that can resolve it.** Ask the user only when readings of intent disagree, otherwise
  verify the world (Li et al., 2609.32255, +4.57 points); weigh each question's value (Nguyen-Hien et al., 2609.37588, five times
  fewer questions).
- **Asking has costs.** Entering a clarification state raised prompt-injection success from 1.8% to 34.0% for one model (Sehwag et
  al., ASPI, 2605.17324; abstract read): an unattended default is safer, and any answer channel is untrusted data. Warnings barely
  deter agents from crossing action boundaries on underspecified instructions (Ji et al., 2607.02294). Early readings harden and
  summaries collapse ambiguity (Lin et al., 2609.25337); models can give the same wrong reading every time, so disagreement
  between samples misses it (Richter et al., 2607.01953).
- **Executable records of the guesses help.** Pinning each underspecified choice as an executable check covered 92.5% of open
  points and was honoured 210 of 210 times, but was no better than prose stating the same scope (Mitsui et al., 2610.03237).
- **Token cost of question against statement wording has not been measured.** Terse notes kept accuracy with a small share of the
  tokens (Chain of Draft, agent-cited); the checklist result above used fewer tokens.

## 5. Experiments

All four ran on Codex `gpt-6.1-terra` at xhigh in the isolated way the E2E harness runs Codex (throwaway `CODEX_HOME`, read-only,
ephemeral), judged blind by Opus with quotes checked by script. Rules were written and committed before any scored call; the
README of docs/experiments/question-bank-20261031/ holds them and the full tables. Commits: QB1 4748ebcd, QB2 ab1e3ebf, QB3 70cbf0d5,
QB4 35bcf78e (the pre-registrations); results and journal in c0dee47b.

### 5.1 QB1: a fixed question bank against the shipped ledger

Question: does a fixed bank of questions the model answers by id cover what a vague request leaves open as well as the shipped
catalog and model-written ledger, at fewer output tokens, and does question wording beat statement wording on the same content?
Setup: X1's four vague requests and their 38 decisions; six arms: the old statements (A), the shipped ledger (B), B with all eleven
catalog lines worded as questions (Bq) or as statements (Bs), and a 20-item bank worded as questions (Qb) or as statements (Sb),
content identical by construction; 32 outputs per arm; every arm graded in the same blind Opus call.

Result (status: firm for these requests and this subject; the judge drifts 2.6 to 4.8 points between batches, so only comparisons
inside one call count):

| Arm | recall | agreement | noise share | output tokens | covered per 1,000 tokens |
|---|---|---|---|---|---|
| A | 0.468 | 0.71 | 0.34 | 636 | 6.98 |
| B | 0.935 | 0.74 | 0.36 | 2,153 | 4.12 |
| Bq | 0.926 | 0.76 | 0.39 | 2,160 | 4.07 |
| Bs | 0.942 | 0.72 | 0.40 | 2,170 | 4.12 |
| Qb | 0.921 | 0.68 | 0.42 | 1,854 | 4.72 |
| Sb | 0.958 | 0.61 | 0.41 | 1,995 | 4.56 |

- Wording on the ledger changed nothing (recall gap 1.7 points, p 0.16; token ratio 0.995). Wording on the bank traded: statements
  covered 3.7 points more (p 0.009) and committed more defaults that conflict with the real request (agreement 0.61 against 0.68), while
  questions cost 7% fewer tokens (p 0.005). Neither gap reached the registered bars (5 points, 15%).
- Replacement of the ledger by the bank (R3) fails: tokens 0.93 (statements) or 0.86 (questions) of B's against the 0.75 needed,
  agreement 6 to 13 points lower, noise share 5.5 to 5.8 points higher.
- Seven of the eleven catalog categories (K3, K4, K6, K8, K5, K2, K7) hold 95% of the coverage the judge credited, and nine to eleven of
  the 20 bank rows; K1, K9, K10 and K11 earned almost nothing on these testable-contract requests. Every wording missed the
  seat-reservation read contract (SR8) in 6 to 7 of 8 outputs.

### 5.2 QB3: a 12-word cap on the answers

Question: is the bank's saving the bank's or the length of its answers? Designed after QB1's token counts and before any judge result
(the order is stated in the pre-registration, 70cbf0d5). Setup: Qt (bank, answers at most 12 words) and Bt (ledger, fields at most 12
words), 16 outputs each, graded with B and Qb in the same calls.

Result (status: firm for these requests, n = 16 per arm): recall B 0.968, Qb 0.974, Qt 0.868, Bt 0.894; output tokens 2,175, 1,880,
1,604, 1,981. The cap saved 15% (bank) and 9% (ledger) and cost 10.6 and 7.4 points of recall, because short answers dropped the
specific value (a port, a code, a name) that made a decision count as covered. R6 and R8 fail. R7 holds: at equal terseness the bank
writes 0.81 of the ledger's tokens (p below 0.001), so part of the bank's saving is the bank's.

### 5.3 QB2: a long, loosely worded request over a real workspace, tools on (exploratory)

Question: on a 281-word dictated request that names installed skills, slang, an unknown name, references to things it does not
state, internal conflicts and a claim the repository contradicts, what do four wordings of intake item 9 do? Setup: the help desk
fixture, 17 items with what a good intake does about each, the host's skill list in the packet, 5 outputs per arm: B (item 9 as
shipped), Bp (B plus catalog lines for terms and references and for conflicts and premises, plus one look-it-up-first line), Qp (a
27-question bank as questions plus the line) and Sp (the same as statements).

Result (status: exploratory, 5 outputs per arm). Every arm covered all 17 items in every output, so coverage cannot separate them.
Correctness does: items right per output 0.56 for B, 0.73 for Bp, 0.74 for Qp and 0.80 for Sp (exact one-sided p between 0.004 and
0.012 for each of the three against B; Sp over Bp 0.024; Qp against Sp 0.115). The gap is in the items the owner's note was about.
Installed skills named in the request were right 0.33 of the time in B and 0.93 in Bp and Sp: B understood "until loop" from general
knowledge and tied it to nothing, while the other arms tied it to the host's skill. The unknown name was right 0.00 in B and 0.40 to
0.80 elsewhere: B and Bp called it context without saying nothing defines it. Silent assertions fell from 1.6 per output in B to
0.4 in Bp and 0 in the bank arms. Conflicts were right in every output of every arm, B included, even the filter behaviour the docs
state wrongly. The wording of the bank mattered little: Qp 0.74, Sp 0.80. The extra lines cost 12% to 18% more output tokens (3,676
to 4,122 to 4,331), 2 to 6 more shell commands and about 3k to 5k more uncached input tokens. What every arm missed was what the files
show about the cost of the requested change: that no template exists for closed tickets, that the outbox key dedupes only while a
notification is pending, and that every change saves the data file.

What it means: a terms-and-references category with a look-it-up-first line is the part that moved resolution of the owner's
jargon; the conflicts category added nothing measurable here because the shipped catalog already surfaced the conflicts when it could
read. It does not show that intake should read the repository (the real stage leaves that to discovery), and it cannot show when
to ask (the frame was unattended; see 5.4). Evidence: README.md QB2 section, scores-qb2.json, qb2/.

### 5.4 QB4: what an attended intake sends to a person (exploratory)

Question: when asking is allowed, what does intake ask? Setup: QB2's request, arms Bp and Qp, the frame changed to say a person can
answer one short batch and the rule to route an item to the person only when the repository and the skills cannot settle it and two
readings lead to different work; 4 outputs per arm; no judge, the person-routed rows were read.

Result (exploratory): 1, 1, 1, 1 rows to a person in the four ledger outputs (of 12 to 14) and 1, 1, 0, 0 in the four bank outputs
(of 27). All six are the same question, the weekly report's window: the request says there is a "usual window", the report has none,
and no default is safe. The unknown name, "right away" against "batch it", the bulk contract and the missing cap were defaulted and
recorded. Predictions: person rows concern decision items (6 of 6, true); no wasted asks (true); the bank asks more (false, 2 against
4). The count is steered by the rule's wording; a looser rule would ask more. Evidence: README.md QB4 section, qb4/.

### 5.5 QB5: the confirmation on three new requests and repositories

Question: does the terms-and-references line, with or without the look-it-up-first sentence, resolve more of a long dictated request on
repositories QB2 was not designed on? Setup (pre-registered in 6f0b7083): three requests over three small fixtures (a user store and
server, an order meter with a hard limit, a text helper), 41 items with expected handling written beforehand and facts verified in the
files, four arms (B as shipped, Bk line and sentence, Bk12 line only, Bsen sentence only), 5 outputs each, 60 intakes on Terra xhigh,
15 blind Opus judge calls.

Result (status: firm on the main measure for these requests; one registered rule missed): items right per output B 0.52, Bk 0.67
(+0.155, p 0.008, ahead in every request: +0.186, +0.186, +0.092), Bk12 0.65, Bsen 0.62; installed skills right 0.20 in B and 0.80 in Bk;
unknown names 0.33 and 0.60; conflicts 0.67 in every arm; output tokens 3,032 and 3,277 (+8%); silent assertions per output 0.67, 0.20,
0.20 and 0.47, the drop for Bk not significant (p 0.115). Rules: C1, C2 and C4 hold, C3 fails. The registration did not say what to do when
only C3 fails; that gap is recorded in the README and not filled in afterwards. The line alone gets +0.126 (p 0.027) and the sentence alone
+0.103 (p 0.069); the data cannot separate their contributions. One intake call stalled for six minutes and was retried by the runner.
Evidence: docs/experiments/terms-line-confirmation-20261031/ (README.md, scores.json, intake/, judge/).

### 5.6 The live A/B of the shipped change (2026-11-01)

Question: does the change as shipped, in the real packet with the host's own skill list (the wording differs from QB5's in two places: "the
skills and commands your host lists" for "the installed skills listed above"), run on a real ShipLoop without harm? Setup (pre-registered in
e48993e307b401a669257e7c699e61a067a3c9d3): origin/main e13af240100c066489e83c028d97339845402b55 (release 2.27.2 / 1.26.2) as arm A against
the same plus the change, 60dc376881d397d770874af16c8a6a8ed60956b2, as arm B; Codex gpt-6.1-terra at high, all tools, hooks on, `--source
checkout`; hello, user-listing and ticket-assignment, 2 runs per arm per case, three lanes; five rules L1 to L5 decided beforehand. Eleven of the
12 runs finished: the twelfth was refused by the harness at launch (a stray listener of another session) and its rerun was then held out for
29 minutes, 78 attempts, by another session's Round 4 on the machine-wide lease of port 4180. After reading the eleven, an excess the rules
did not look at (stage send-backs: A 0 of 6 runs, B 4 of 5) led to a replication R2, registered in 9c2bf16a0264edc7d8b682ded7dc9a8292e8a838
before its runs: hello, 4 more runs per arm, rule R2-1 (B has at least 2 more runs with a send-back than A).

Result (status: firm for these three cases at one subject and effort; the benefit is not measured here): all 19 runs passed; L1 to L5 hold
(every B ledger holds K1-K12, no ledger refusal, refused callbacks per run A 1.00 and B 1.40, tokens within the bar, nobody stopped for a person);
with the missing run counted as a failure L1 and L2 still hold at their thresholds. R2-1 did not replicate: A 0 of 4 runs with a send-back, B 1
of 4. Pooled over all 19 runs (descriptive only) A 0 of 10, B 5 of 9 (test-spec 3, implement 2), hello alone A 0 of 6, B 3 of 6; the cost seen is
small (hello minutes 11.2 against 10.3, tokens 19.5M against 18.4M) and every run passed. K12 was used: 5 of 9 B ledgers mark it "yes", 4 "no"
with a reason, one filed a question under it (inspect: how the repository defines notification and ticket status). Intake seconds and tool calls
did not rise (25.9 and 5.3 against 25.3 and 5.6). Evidence: docs/experiments/terms-line-live-ab-20261101/ (README.md with the rules, the
Results and the limits; scores.json; results-tables.md; e2e_ab.py; lane.sh and lane-r2.sh; b-ticket-s2-refusals/), runs in
~/e2e-runs-tl/20261101/.

### 5.7 R3: do the send-backs repeat on a representative case? (2026-11-01, registered before its runs)

Question: on today's main, does the K12 line make ShipLoop send stages back more often? Round 1's excess (A 0 of 6 runs with a send-back, B 4 of 5)
did not replicate by R2 (A 0 of 4, B 1 of 4) and stayed unexplained. Both ran on release 2.27.2, which lacks three later ShipLoop commits that bear
on the causes seen: b8d320335c81151a99e7d168b684d79fd0e81352 (step-plan refuses a criterion a focused command names without a test ID of its own), 9870c6f68bfbd9375340c0e91ffdf4abfd76bd85 (rule C of the proof-order
refusal) and 4515368495e2b2e50ea07f7599146875188449f9 (the focused-ID wording fix); and hello is a one-step case (mean 10.2 minutes at high), so the owner suggested "a more
complicated test which does a standalone node server with app functionality". Setup (rules and power in
docs/experiments/send-back-replication-r3-20261101/README.md, committed before any scored run): the new case `shared-expenses` (47ed1804d379e1ad58ac5ad081e027dab043f906; a Node
service with six checks calibrated on a reference and nine defects; it leases no port); 10 runs per arm over five lanes on Codex gpt-6.1-terra at high;
arm B = main at 47ed1804d379e1ad58ac5ad081e027dab043f906, arm A = the same with the K12 commit 60dc376881d397d770874af16c8a6a8ed60956b2 reverted (a scratch commit, never merged); rule R3-1: the runs with a send-back, B
higher, exact one-sided p at most 0.05, which a true 40% against 5% reaches 43% of the time at 10 a side. Status: registered; the result is appended
here when it is read.

## 6. What a change to intake has to beat

- **Coverage and cost of the shipped catalog on vague requests** (QB1, Terra xhigh): recall 0.935, agreement 0.74, noise share 0.36,
  2,153 output tokens. Any replacement must hold these inside one judge call; the judge's batch-to-batch drift (2.6 to 4.8 points)
  is as large as a 3-point margin, so such a margin cannot be resolved without sharing a call.
- **On a long dictated request with tools** (QB2): items right 0.56, installed skills tied to the host's list 0.33, an unknown name
  flagged 0.00, 1.6 silent assertions per output, 3,676 output tokens, 7.6 shell commands.
- **The live result that shipped it** (45f9752e): 0 of 6 changed runs lost a loop to the proof-order fault against 4 of 6, hidden
  checks 6 of 6 against 5 of 6. A change to item 9 needs a live check, not only an exercise.
- **The cost scale:** an intake is 2k to 4k output tokens, so a saving of even 25% is a few hundred tokens a run; judge a change by
  what it does downstream before what it saves here.

## 7. The candidate question bank and the routing rule

### 7.1 The bank tested here, and the one addition the evidence supports

`bank.py` holds the 20 questions K1.1 to K11.2, one per clause of the catalog, in question and statement form (for example K3.1: what are
the exact inputs, outputs, commands, endpoints, files or messages, and their names and shapes?); `qb2.py` adds seven for terms and
conflicts. It did not beat the shipped ledger (§5.1). The addition QB2 supports is one catalog line and one sentence:

> K12 Terms and references: the names, skills, commands, products and community phrases in the request, and the phrases that point at
> something it does not state ("the usual", "as before"); what each means here and where that was settled (the installed skills, the
> repository, or a search), else the best reading and how sure it is.
>
> Terms and references: settle each by looking, in this order: the installed skills listed above, the repository and its documents,
> then a search (`research`). When nothing settles it, record the best reading and how sure you are as the `default`; use `person` only
> when two readings remain that lead to different work.

In a real packet "the installed skills listed above" should read "the skills and commands your host lists", because a host lists them in
its own context, not in ShipLoop's packet (QB2 put the list in the packet). The conflicts line (K13) is not supported: every arm found the
conflicts without it. The ledger's shape check (`_check_intake_questions`) names K1 to K11 once each, so a K12 means changing it too.

### 7.2 A candidate bank from requirements-engineering sources (untested)

The paper survey assembled 23 one-line questions with provenance and, for each, who should answer it: R the repository, X a probe
(run something), U the requester (an unattended run records a default instead), "record" a note kept in the run, "self" a check the
model makes of the request's own wording. Source tags: GW Gause and Weinberg's context-free questions, VOL Volere, EARS, ISO
ISO/IEC/IEEE 29148, BKK Berry, Kamsties and Krieger on ambiguity, SC and DP the 2026 checklist and decision-pin papers
(Goel; Mitsui), PROUR Li et al. The classical sources were read from course slides and a secondary paper, not the originals, so the
tags are provenance hints, not citations. Nothing here has been run.

| # | Question | Source | Answered by |
|---|---|---|---|
| 1 | Who asked, and who is affected? | GW, VOL | U |
| 2 | What problem does it solve, and why now? | GW, VOL | U |
| 3 | What observable result means success? | VOL, ISO | U |
| 4 | What is in scope, and what is out? | VOL | U |
| 5 | Which existing code or conventions must it follow? | GW, VOL | R |
| 6 | Where does it run: platform, versions, data size? | GW, VOL | R |
| 7 | Which mandated constraints apply (licence, security)? | VOL | R |
| 8 | What does each jargon term mean here? | VOL, BKK | R |
| 9 | Do words like all, only, and/or, or pronouns allow two readings? | BKK | self |
| 10 | Which vague words need a number? | BKK, ISO | U |
| 11 | Does any requirement contradict another, or the current code? | ISO | X |
| 12 | When does each behaviour apply? | EARS | U |
| 13 | What happens on bad input or failure? | EARS, SC | U |
| 14 | What happens at limits and for each role? | SC | X |
| 15 | What performance or reliability is needed, measurably? | VOL | U |
| 16 | What changes cannot be undone? | VOL, SC | R |
| 17 | Which facts are assumed? | VOL | record |
| 18 | Would two plausible answers behave differently? If not, drop the question. | DP | X |
| 19 | Can the repository or a probe answer this first? | PROUR | R |
| 20 | How do we back out of a wrong default? | VOL | record |
| 21 | What does the requester expect but has not said? | GW | U |
| 22 | Which questions are irrelevant here? | GW | meta |
| 23 | Which answers are guesses, and which test catches a wrong one? | DP | record |

Against the K1-K11 catalog: most repeat a K category (1-8 and 11-15 map to K1, K2, K4, K6, K7, K10, K12 and K13). What it adds is the
request's own ambiguous and vague words (9, 10), irreversible changes (16), the way back from a wrong default (20) and the test
that would catch a wrong guess (23). Items 17-19 and 21-22 are process or routing rules, which belong in the packet's rules and the
route ladder of §7.3, not in a bank. If a later round tests a larger bank, 9, 10, 16, 20 and 23 are the candidates.

### 7.3 The routing rule: look, then default, then ask

What the survey, the literature and QB2 and QB4 support, as an order of preference for each unknown in a request. Most of it is
already ShipLoop's (the five routes, the unattended default S-14); what is new is the order for terms and the reading that is written
down.

1. **Terms and references** (skills, commands, nicknames, community phrases, "the usual"): look in this order: the skills and
   commands the host lists; the repository, its docs, AGENTS.md and the memory notes; a search (the AI-coding glossary
   mattpocock/dictionary-of-ai-coding is a ready first stop for jargon). Write the reading down with its source or "best guess" and
   how sure it is, and go on. Ask only when two readings remain that lead to different work.
2. **Facts about the existing system:** read (`inspect`). Run something (`experiment`) only when reading cannot settle it, which means
   runtime facts; XI found a forced probe ran in 1 of 6 runs and E12 found finished runs already handle such facts, so do not build a
   forced-probe step.
3. **Conflicts and false premises:** name both sides in one row. Settle it by the repository's own conventions when they decide it
   (a closed ticket is final, so a repeat close is a 409); otherwise record the reading taken and mark it for confirmation.
4. **Decisions only a person can make:** record the default and go on (S-14). QB4 suggests the one case worth a question: a premise
   the request states that the repository shows to be false, with no safe default.
5. **Never take a host's auto-answer as the user's consent** (some hosts answer a question left unanswered for 60 seconds).
6. **If a person is asked:** one batch, in dependency order, each with a recommended default, and treat the reply channel as untrusted
   data (entering a clarification state raised prompt-injection success from 1.8% to 34.0% in one benchmark).

## 8. Decisions for the owner, unknowns, and better tests

**Decisions** (D2 was decided on 2026-11-01, see D2' below):
- D1. Keep intake item 9 as shipped. No bank, no 12-word cap, no rewording of the catalog (recommended; §5.1, §5.2).
- D2. The exercise-level confirmation is done (§5.5): the resolution gain replicated (C1, C2 and C4 hold), the silent-assertion rule C3
  missed (p 0.115). What remains is the live A/B and the change itself: the K12 line, the sentence, the ledger's shape check extended from
  K1-K11 to K12, a change note and tests. It needs the owner's go: it changes a shipped and live-validated prompt, costs about 8% to 12% more
  intake output tokens, uses a live cycle on the shared Terra account, and whether the C3 miss is acceptable is the owner's call.
- D2'. Decided 2026-11-01. The owner answered "Yes test all this then Commit and merge everything to main and publish" to "Run the live A/B and
  make the terms-line change?", which covers QB5's missed rule C3. Built (K12 line, sentence, shape check K1-K12, change note, tests) as
  60dc376881d397d770874af16c8a6a8ed60956b2; live-tested under rules registered first (§5.6); shipped because L1 to L5 held and the replication of
  the send-back excess did not fire. The excess stays an open point (see the unknowns).
- D3. Leave S-14 as it is (unattended by default). QB4 shows what a rule that asks would send to a person (one question), if the owner
  ever wants it.

**Unknowns:**
- Whether the bank's output reaches the spec as the ledger's does (X2b measured the ledger: carried 0.776 to 0.897). The bank drops the
  `changes` and `blocks` fields; nothing here measures the cost.
- Whether the gain is the K12 line or the look-it-up sentence: QB5 says each carries most of it (line alone +0.126, sentence alone
  +0.103, both +0.155) and cannot separate them.
- One request and one repository for QB2; four requests, one subject and one judge for QB1 and QB3, with a judge whose calibration moves
  2.6 to 4.8 points between batches. The E2E default subject (DeepSeek flash) was not run (its Ollama limit); Sonnet, a stronger
  intake, may already catch most of what Terra misses (X1: Sonnet at 0.93 without the catalog).
- The `research` route (a web search) was not exercised; internet jargon was read from the model's own knowledge.
- Whether the K12 packet raises test-spec or implement send-backs (2026-11-01): round 1 had A 0 of 6 runs with one against B 4 of 5; the
  replication R2 had A 0 of 4 against B 1 of 4, below its registered bar of a gap of 2. Pooled (biased: round 1 was picked for being odd) A 0 of
  10, B 5 of 9. A moderate real effect (40% against 5%) would fire R2-1 only 46% of the time at 4 runs a side. No mechanism is known.
- The live benefit of K12 on a loosely worded request: all three live cases are fully specified, so K12 had little to settle.
- Real intake leaves repository facts to discovery; QB2 lets it read, which is not what ShipLoop does.
- Host-supplied answers (60-second auto-resolve) and the survey agents' readings of the repositories are not verified beyond the star
  counts, push dates and a sample of cited issues and posts.

**Better tests:** (1) the D2 confirmation, with a held-out set of requests and jargon, K12-only against the sentence-only to separate
them; (2) a bank-to-spec test like X2b before any bank is considered again; (3) a pruned bank (the ten rows that earned the coverage)
on held-out requests, since a bank pruned on these four would overfit them; (4) the attended probe with a looser asking rule and a
simulated answerer, to see what comes after the question.

(5) a hello comparison of about 10 runs a side (about 40 minutes) to settle the send-back question; (6) a live case whose request is dictated
and names skills and slang, graded on what the run does with them, to measure K12's benefit end to end.

## 9. Journal

- 2026-10-31 (session start): read the history of intake, the catalog and the XI and XR route tests (full messages of
  c30e706c, 2ae6200e, 593b4b44, f616aaea, 8e5d6f47, ddd371ea, ffea2956, 7c8ee3d1 as short hashes; the commits that pre-register this
  work cite the full hashes). Saved the standing jargon rule as a memory.
- 2026-10-31: three survey agents launched; QB1 designed from X1-T's saved runs and pre-registered (commit
  4748ebcd), QB2 pre-registered (ab1e3ebf), QB3 pre-registered after QB1's token counts and before any judge result (70cbf0d5), QB4
  registered before its calls (35bcf78e).
- 2026-10-31, runs: QB1 160 intakes (0 failed) then 16 judge calls; QB2 20 tools-on intakes and 5 judge calls; QB3 32 intakes and 8
  judge calls; QB4 8 intakes. A dry run of the scorer on the first returned judge answers found no fault; a calibration check read a
  key the QB3 score file does not hold and was redone from the judge answers (no result affected). Calibration drift between judge
  batches (2.6 to 4.8 points on the same outputs) is recorded as a limit in §6.
- 2026-10-31, verification of the surveys: 15 of 15 cited arXiv papers exist with the stated titles and dates; 23 repository star counts
  and push dates match the GitHub API; 3 cited issues, 1 Hacker News item, 1 repository and 1 blog post exist as described.
- Findings (status in brackets): F21 the explicit item list, not question wording, lifts intake coverage (firm, QB1); F22 a fixed bank
  is not cheaper than the ledger in general and costs agreement (firm for vague requests; exploratory for long ones, QB2); F23 a 12-word
  cap loses 7 to 11 points of recall (firm for these requests, QB3); F24 a terms-and-references category with a look-it-up-first
  sentence raises resolution of skills and unknown names (exploratory, QB2, n = 5); F25 the shipped catalog already finds conflicts and
  false premises when it can read (exploratory, QB2); F26 an attended intake under a restrictive rule asks one question, the false
  premise (exploratory, QB4).
- 2026-10-31, checks on the branch: the release-boundary check passes; the quick test tier ran 59 suites, 58 passed, and the one
  failure (shiploop-e2e-brownfield-tickets, the follow-on regression test, in the multipass chain work of another session) also fails
  on the base commit 84b6bdd2 with none of this branch's commits, so it is not from this work.
- 2026-10-31, corrections after review: four statements went further than the checks behind them and were qualified: that nobody has
  tested question against statement wording (Leidinger et al. did, on classification prompts; what is missing is a test on intake
  guidance); that two hosts answer their own questions after 60 seconds (Codex does by default; Claude Code did and, per the survey
  agent, is now opt-in); that no vendor ships a question bank (one agent's reading, now worded as the survey's finding); and a stale
  pointer to the results commit. No result changed.
- 2026-10-31, QB5: registered (6f0b7083) before any scored call; 60 intakes and 15 judge calls; one intake call stalled and was retried.
  Findings: F27 the terms line replicates on three new repositories (firm on items right, +0.155, p 0.008); F28 its fall in silent
  assertions is not significant at 15 outputs per arm (p 0.115; same direction as QB2); F29 the line and the sentence each carry most of
  the gain and cannot be separated here (exploratory). Landing: the first study was merged into main by merge commits, not a rebase, so the
  hashes this journal cites stand (dbbf945b); this QB5 work is on its own branch.
- 2026-11-01, the owner's go and the build: read first the full messages of ffea29563ecab5415de88e68f9cb9b3e2f0b555f (the ledger),
  e7e0bc3c0e347845e8ee4f99ee318175d280c9db (keep it in the stored result; read the submitted block, not the stored one),
  45f9752eee7d4fe3450b9ac88843cc1da0fbb980 (the live A/B that shipped it, Terra high), c2da4604a0916a21280f3a25aa4c7572f0694ea1 (the stage-prompt round),
  17cbbd9b830e8e95385617f0c1c9fb68dd850546, d9dd7443a210e419a9dbc139cdc929c9f56f3527 and the owner's note on jargon. Built the change
  (commit message 60dc376881d397d770874af16c8a6a8ed60956b2); `origin/main` moved twice during the work (a docs commit, then the Python 3.9 floor release
  e13af240100c066489e83c028d97339845402b55, 46 files including the hook scripts), so the change was rebased once onto the release before anything cited its hash.
  Checks: test/shiploop-callback-contract.test.py 96 tests OK; quick and prompt tiers 38 suites OK in 402 s. Registered the live A/B
  (e48993e307b401a669257e7c699e61a067a3c9d3), ran 11 of its 12 runs, registered R2 (9c2bf16a0264edc7d8b682ded7dc9a8292e8a838) after reading them, ran its 8
  runs, applied the rules, shipped.
- Findings (status in brackets): F30 the shipped K12 wording runs live: 9 of 9 B intakes wrote all 12 categories, none was refused, none used a
  person route, all 19 runs passed (firm for these three cases, one subject and effort); F31 K12 is used: 5 "yes", 4 "no" with a reason, one
  question filed under it, routed to inspect (exploratory: the requests are fully specified); F32 L1 to L5 hold on 11 of 12 round-1 runs and
  also with the missing run counted as a failure (firm); F33 the send-back excess of round 1 (A 0 of 6, B 4 of 5) did not replicate by R2-1 (A 0 of
  4, B 1 of 4) and remains unexplained; pooled A 0 of 10, B 5 of 9 (interim, descriptive, biased toward an effect); F34 token and time
  figures are too unbalanced by case and too spread (ticket-assignment 26M to 67M) to claim a saving or a cost (exploratory); F35 (process) the
  harness refuses a launch while a stray listener of another session's ended case is bound, and a machine-wide lease on a port can hold a
  second session out for hours behind a multi-run round of the first: lane planning for port-leased cases must allow for that.
- 2026-11-01, landing: `origin/main` moved five times during the work (two releases, 2.27.3 and 2.27.4, among them rule C of the proof-order
  refusal); the change was merged, not rebased, so the hashes cited here stand (d2bee85c28219c48fa16afbf9ea270e649f6b38e, a32b4402b74e4002495c8fa182b2653df0ef9b44). Checks on the merged tree:
  quick and prompt tiers 42 suites OK in 473.3 s; one live run each of hello and user-listing on it, both passed with a 12-category ledger. The
  release preflight asked for a learnings entry after the merged-in releases; the entry now carries a merged-tree check. F38: the implement
  send-back for a criterion that needs a test the test stage writes later also appears on the merged tree (user-listing, one run), which
  already has rule C, so that fault family is not specific to arm B (exploratory, n = 1).
- 2026-11-01, R3 registered. The owner answered "Yes" to running about 10 more hello runs a side, then suggested a more complicated standalone Node
  server case as "a more representative test case to repeat on". Added `shared-expenses` (47ed1804d379e1ad58ac5ad081e027dab043f906): no existing case fit (the Node cases lease port 3000
  or 4180, which starved the A/B's twelfth run for 29 minutes; battleship and checkers need a browser; csv-report and seat-reservations are Python).
  Its six checks passed on the reference service and each of nine one-line defects failed the check that reads the sentence it breaks (the
  race-prone service only the concurrency check). Quick and prompt tiers on the change: 69 of 72 suites OK and 3 timing tests failed under a load average of 50 to 190, each
  passing alone. One unscored live smoke run passed all six checks (22.2 minutes, 37.1M tokens, 227 turns). Registered R3 and pushed it before launching any scored run.
  Findings (status in brackets): F39 the case's checks tell a correct service from nine defects, and a model's delivery passed them in the one smoke run
  (firm for the reference and defects; exploratory, n = 1, for models); F40 the smoke run had an implement send-back of round 1's family ("the step proof
  requires node --test to execute TC_1-TC_4, but implement forbids writing tests"), on a tree that already has rule C (exploratory, n = 1; it agrees with F38);
  F41 (process) the A/B base 2.27.2 lacked the three fixes that bear on those send-backs, so no 2.27.2 result says what today's product does and R3 runs on today's
  main (firm: `git merge-base --is-ancestor`).
