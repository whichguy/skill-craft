# Spec elaboration journal

Living journal of the side experiment on the prompt that turns a small, vague incoming request into a verbose
specification. Apparatus: `docs/experiments/spec-elaboration-20261120/`. Edit entries rather than delete them; a
claim that stops holding is marked superseded with the date and the reason.

## 1. Registration (2026-11-20, before any call)

**Why this exists.** Owner, 2026-11-20: a prompt that takes an incoming vague prompt — an action, maybe
environments — and elaborates it into a verbose specification, recursing to find what the request leaves
implicitly defined and how the interactions work, "iteratively grind[ing] through them, looking for nuance and
detail". The sample request is the owner's: a Grok bot in a Salesforce development org, with the bot's nature, its
operation, its async activities, its interface and its stored schema all to be defined from that one sentence. The
owner asked for Sonnet at high and GPT-6.2 Sol at medium as the drivers, for a few more sample requests beside the
Grok bot, and for test cases and per-iteration results to be retained so the prompt can be iterated repeatedly.
The stated intent is a small side experiment, reincorporated into ShipLoop afterwards.

**Where it sits beside work already running.** The ratchet pilot (branch `ratchet-pilot-b6eab2`, journal
`docs/ratchet-pilot-journal.md`, runs under `/Users/dadleet/e2e-runs/ratchet-pilot-20261120-b6eab2/`) registered
amendment 1 earlier the same day, commit e63747a3d: its spec stage became "a rich enrichment (use cases, implied
requirements)" from the owner's fifth message, which is the same thread of intent. That pilot measures the
enrichment *through the built product* — whether the resulting test suites catch more of 37 calibrated defects —
over four small code cases, and its runs were in flight when this experiment was registered. This experiment
measures the elaboration prompt *directly*, on the specification text, over requests that include a platform-shaped
one the pilot has no case for, at the two drivers the owner named here. They are complementary instruments on one
question; neither replaces the other, and this session did not touch the pilot's branch, worktree or runs.

**What is registered.** `docs/experiments/spec-elaboration-20261120/README.md` holds the design: two arms
(`A-single`, the ratchet enrich text as the control; `B-recursive`, six named passes with a stop rule), four frozen
one-sentence requests, 89 held-out nuances written before any run, the two drivers, the measurement (script counts
plus an Opus coverage verdict per nuance), and the readings R1 to R5 with their thresholds. Registration commit:
this one.

**Known limits of the instrument, stated up front.**
- The 89 held-out nuances are this session's own predictions of what matters, not an external ground truth. They
  are frozen and never edited after an arm's output is read, which keeps them honest, not authoritative.
- One call a cell. Every round-1 number is interim; a difference at R1's threshold needs a replicate.
- Subjects keep their built-in tool set, so a subject may search the web for a platform limit. That is realistic
  for the real stage, and `counts.json` records the tools each call used, so a coverage difference traceable to a
  lookup rather than to the prompt is visible rather than hidden.
- Both arms were written by this session, so the control is as strong as this session could make it (the state of
  the art in the repository), not as weak as it could make it. That is the honest form of the comparison, but it is
  not a blind one.

## 2. The judge is calibrated before its verdicts are used (2026-11-20, round `cal-1`)

The coverage number is only worth what the judge is worth, so the judge was checked against two hand-written
specifications for `grokbot-salesforce` before any round-1 verdict was read. Both are in
`docs/experiments/spec-elaboration-20261120/results/cal-1/`, their verdicts in `grades/cal-1/`.

- `CAL-thin`, four deliberately vacuous clauses ("Errors are handled gracefully", "The bot performs well"):
  **0 of 27 covered**, 2 partial. Neither vacuous clause earned credit for any unhappy-path nuance; the
  performance clause drew a `partial` on N-25 whose `missing` note asked for the numeric bound it lacked.
- `CAL-rich`, eight clauses written to aim at eight named nuances: **7 of those 8 covered**, each verdict naming
  the exact clause written for it. The eighth, N-17, came back `partial` because the clause listed role, text,
  status, timestamp and model but not the token or usage counts the nuance asks for — an omission this session had
  made without noticing, which the judge found. Its six other `partial` verdicts all point at real partial touches
  in the text (a callout cap mentioned in passing, a pending state that half-answers the async-completion nuance),
  not invented credit.

**Reading.** The instrument discriminates: it does not reward length or generality, it finds what is stated in the
specification's own words, and it is strict enough to catch a one-item omission inside a clause that otherwise
matches. `covered` is therefore used as round 1's primary number, with `partial` reported beside it rather than
folded in. Firm for this judge, model and prompt; a change to any of the three needs the calibration re-run.

## 3. Round 1 result: the recursive form earns its minutes on both drivers (2026-11-20)

16 calls, all exit 0, every arm-B call writing both `spec.md` and `passes.md`. Scoreboard
`docs/experiments/spec-elaboration-20261120/evidence/round-1/scoreboard.txt`, the registered readings computed in
`evidence/round-1/readings.txt`, the per-nuance verdicts in `grades/round-1/`.

| arm | driver | covered of 89 | partial | minutes a case | clauses |
| --- | --- | --- | --- | --- | --- |
| A-single | sol-medium | 38 (43%) | 38 | 3.3 | 246 |
| A-single | sonnet-high | 46 (52%) | 33 | 2.0 | 184 |
| B-recursive | sol-medium | 50 (56%) | 33 | 8.4 | 609 |
| B-recursive | sonnet-high | **72 (81%)** | 16 | 8.0 | 412 |

**R1, primary: difference shown on both drivers.** B minus A is **+26 of 89** on the latest Sonnet at high and
**+12 of 89** on GPT-6.2 Sol at medium, against a registered threshold of 8. The two drivers also separate: Sonnet
at high beats Sol at medium on both arms, and gains more from the recursive form than Sol does.

**R2, where the gain sits: in the implicit categories, as registered.** Sonnet A to B by category: unhappy paths
6 to 12, async 4 to 9, permission 4 to 8, operator 2 to 5, data 3 to 6, interaction 7 to 9, edge 8 to 10,
non-functional 4 to 5, platform 3 to 3, preservation 5 to 5 (already saturated under both arms). The gain is not
spread evenly, which is what would have suggested length rather than elaboration.

**R3, cost: earned.** The recursive form costs 4.0x the minutes on Sonnet (2.0 to 8.0 a case) and 2.6x on Sol (3.3
to 8.4). R3 would have refused a gain under threshold at that price; the gain is three times the threshold on
Sonnet. Eight minutes sits far inside the planning alarm at 30 minutes.

**R4, padding guard: passed on Sonnet, flagged on Sol.** Covered per clause falls from 0.25 to 0.17 on Sonnet and
from 0.15 to 0.08 on Sol. A fall is expected against a fixed 89-item ceiling, but Sol's is twice as steep, and the
counts say why: on `csv-user-import` Sol marked **149 of its 161 clauses `choice`** and wrote boundary clauses with
no value in them ("an upload over an effective import limit is refused", "a valid upload exactly at an effective
import limit qualifies"). A builder reading those still does not know the limit. Sonnet instead committed to
figures (4,000-character message, 60 calls an hour, 30-day retention) and marked the ones it could not establish
unconfirmed. So the two drivers inflate differently: Sol adds clauses that carry no decision, Sonnet adds
decisions.

**R5, procedure guard: carried out on both.** Passes recorded per case: Sonnet 8, 9, 7, 9; Sol 9, 10, 10, 9. The
Grokbot Sonnet log shows pass 8 still fixing things a builder would have got wrong (a circular rule between the
status checklist and the cleanup schedule) and pass 9 declared as the stopping pass, read top to bottom, changing
no clause. The stop rule did what it says rather than being announced after one pass.

**What the best cell still does not state, and why it matters.** Of B-recursive + Sonnet's 17 non-covered nuances,
**16 are `partial` and 1 is `absent`**. It almost never misses a topic; it names the dimension and leaves a member
of it undecided — stop conditions without the full list of states, a stored record without its usage counts,
operator controls without the per-case switch, time zones without business hours. Weakest categories: operator
5/9, data 6/10, platform 3/5.

Two readings of that compete and both are probably true: the arm under-elaborates compound dimensions, and the
held-out nuances are themselves compound, so one bundling four members can only be fully covered by a spec that
hits all four. The checklist stays frozen either way (no rescoring), and `partial` is read as what it is: the
dimension was found, its members were not enumerated.

**Apparatus findings worth keeping.**
- Sol used web search (up to 6 times on the Grokbot case); **Sonnet used none in any of its 8 calls**. Sonnet's
  Salesforce figures therefore come from the model, correctly marked unconfirmed where it was unsure, while Sol
  looked things up and still scored lower on the platform category (1/5 against 3/5 under arm B). Searching did not
  substitute for elaborating.
- `grokbot-salesforce__B-recursive__sonnet-high` invented a Source kind, `runtime`, nine times. The form permits
  three; a round-2 arm should not need to forbid a fourth, but the counts now catch it.
- The task wrapper around the judge reported exit 144 while the judge itself kept running and wrote 11 of 16
  verdicts. Resumability made that a non-event: the second invocation skipped the 11 and finished the 5. Keep
  judge and subject runs resumable.

**Decision taken here (routine).** Round 2 runs a third arm, `C-enumerated`, derived from `B-recursive` by exactly
three deltas, each one answering a measured round-1 gap rather than a hunch: (1) a clause naming a dimension lists
its members, and a clause about a bound states the bound's value or marks the figure unconfirmed — aimed at the 16
partials and at Sol's value-free boundaries; (2) the operator gets a pass of its own, promoted out of the
five-item sentence it shared in pass 1 — aimed at the weakest category in every cell; (3) the later passes
renumber accordingly. Arms A and B are not re-run: their verdicts stand as registered.

## 4. Round 2: the enumeration rule lifts the weaker driver by 10 and the stronger one not at all (2026-11-20)

8 calls of `C-enumerated`, all exit 0, all writing both files. Arms A and B were not re-run; their round-1
verdicts stand. Scoreboard `evidence/round-2/scoreboard.txt`, the B-to-C comparison `evidence/round-2/vs-round-1.txt`.

| arm | driver | covered of 89 | partial | clauses | minutes a case |
| --- | --- | --- | --- | --- | --- |
| B-recursive | sonnet-high | 72 (81%) | 16 | 412 | 8.0 |
| C-enumerated | sonnet-high | 74 (83%) | 15 | 535 | 10.4 |
| B-recursive | sol-medium | 50 (56%) | 33 | 609 | 8.4 |
| C-enumerated | sol-medium | **60 (67%)** | 28 | **488** | **7.6** |

**Sol medium: +10, difference shown — and it got cheaper at the same time.** Clauses fell from 609 to 488 and
minutes a case from 8.4 to 7.6 while coverage rose 10 points. This is the padding finding from round 1 closing:
Sol had been spending clauses on value-free boundaries, and a rule that a bound states its value turned that
spending into decisions. Its targeted categories moved most (data 4/10 to 7/10, operator 4/9 to 6/9,
non-functional 1/5 to 3/5).

**Sonnet high: +2, no difference shown, at 30% more minutes and 30% more clauses.** Its targeted categories did
move (data 6/10 to 8/10, async 9/11 to 11/11, operator 5/9 to 6/9) but three others each lost a point
(permission 8/8 to 7/8, platform 3/5 to 2/5, unhappy 12/12 to 11/12). Sonnet was already committing to figures
under arm B, so delta 1 had nothing to fix for it; what the extra instruction bought was length, and something was
displaced. Each regression is one nuance on one call and none is established on its own, but all three pointing the
same way is why this is recorded rather than smoothed over.

**Reading.** The enumeration rule earns a place for a driver that under-commits and is a wash for one that does
not. Since ShipLoop runs on hosts of both kinds, a rule that lifts the weaker by 10 points while costing the
stronger nothing measurable is worth having — but the two deltas are confounded in this round, so neither can be
credited on its own yet.

**Decision taken here (routine).** Round 3 runs `D-enumerated-only`: arm C with the operator pass removed and
B's pass numbering restored, so D differs from B in exactly one region (a diff confirms a single changed block).
D minus B isolates the enumeration rule; C minus D isolates the operator pass. Until that lands, delta 2 is not
folded anywhere.

**Platform is the standing weakness in every arm and every driver** (best 3/5, and arm C made it worse on Sonnet).
No arm in this experiment asks for a *source* for a platform claim — they only allow "unconfirmed" on a figure.
ShipLoop's own spec stage already carries the stricter rule, in the duty-10 review focus conditions: "a claim about
what the runtime, platform or a library can do that a decision depends on, with no primary-documentation source or
probe result: check it". So the platform gap measured here is a gap in these arms, not in ShipLoop, and the
fold-back must keep ShipLoop's existing condition rather than replace it with the weaker wording.

## 5. Round 3, an evaluation of rounds 1 to 3, four corrections, and the queue (2026-11-20)

### Round 3: the enumeration rule carries the gain; the operator pass carries none

8 calls of `D-enumerated-only` (arm B plus the enumeration rule, no operator pass), all exit 0. All arms, one call a
cell (`evidence/round-3/all-arms.txt`):

| arm | Sonnet high: covered of 89 | clauses | min a case | Sol medium: covered of 89 | clauses | min a case |
| --- | --- | --- | --- | --- | --- | --- |
| A-single | 46 | 184 | 2.0 | 38 | 246 | 3.3 |
| B-recursive | 72 | 412 | 8.0 | 50 | 609 | 8.4 |
| C-enumerated (rule + operator pass) | 74 | 535 | 10.4 | 60 | 488 | 7.6 |
| D-enumerated-only (rule alone) | 73 | 413 | 7.0 | 62 | 499 | 7.2 |

- **The enumeration rule alone (D minus B): +12 on Sol, +1 on Sonnet.** It is the delta that carried Sol's round-2
  gain.
- **The operator pass alone (C minus D): -2 on Sol, +1 on Sonnet.** Not shown on either driver, and it is what made
  Sonnet's arm C the longest and slowest (535 clauses, 10.4 minutes against 413 and 7.0 without it). It is dropped.
- **D is the arm carried forward**: highest or equal coverage on both drivers and the cheapest of the recursive arms
  on both.

Status: the ordering D >= C >= B >> A on Sol and (B, C, D) >> A on Sonnet is interim until replicated; see the
noise note next.

### What three rounds show together

- **Sonnet has reached a plateau: 72, 74, 73.** Three different recursive arms, the same pooled number. But case by
  case the same three arms scored 18/18/13 on the CSV case and 14/16/18 on the invoice case. A swing of 5 on one
  case between arms that pool to the same total says a single call is noisy at about the size of every difference
  under 10 in this journal. **No noise floor has been measured**: the band of 4 in R1 was a guess.
- **27 of the 89 nuances are covered by every cell**, single-pass ones included, so they tell arms apart not at
  all; **3 are covered by no recursive cell** and are `partial` everywhere (the waitlist entry "stored or
  derived", "every condition that stops the sequence" with its six states, do-not-contact with the billing
  exemption). Those three are compound or are facts about how it is built, which the arms' own rules keep out of a
  specification. The instrument's working range is about 59 nuances and its ceiling about 86
  (`evidence/round-3/per-nuance.txt`).
- **Where the covering words first existed** (`evidence/round-3/first-draft.txt`, `timeline.py`, 22 of 24
  recursive sessions parsed). Each session's first write of `spec.md` against its kept file:

  | arm, driver | clauses, first draft to kept | covered nuances already worded in the first draft |
  | --- | --- | --- |
  | B, Sol | 90 to 609 | 24% |
  | B, Sonnet | 111 to 412 | 25% |
  | C, Sonnet | 158 to 535 | 39% |
  | D, Sonnet | 287 to 413 | **71%** |
  | C, Sol (3 sessions) | 42 to 376 | 7% |
  | D, Sol (3 sessions) | 47 to 349 | 19% |

  Under arm B about three quarters of what was finally covered arrived after the first draft, so the later work is
  not decoration. But under arm D Sonnet wrote most of the specification in its first write (113 of 120 clauses on
  the Grokbot case, 87 of 95 on the invoice case) and ended at the same coverage. That is one driver, four sessions
  and a lower bound (a clause reworded later counts as added later), and it does not say what a single pass told to
  use every lens would reach. It does say the question is open: **the gain may come from what the instruction makes
  the model consider, not from going round again**, and only an arm that removes the going-round can tell.
- **Minutes follow the length of the specification more than the number of passes**: Sonnet's front-loaded Grokbot
  session still took 7.5 minutes to write 9,657 words; arm A takes 2.0 for about 3,700.
- **Platform facts stated from memory look right where spot-read.** Sonnet's Grokbot specification under arm D
  gives a 120-second ceiling for a callout or continuation, no callout after uncommitted work, a cap on concurrent
  long-running requests ("10 requests running 5 seconds or longer", marked unconfirmed), 5 MB of Developer Edition
  data storage (marked unconfirmed) and a 131,072-character long text field. Read against this session's own
  knowledge only, not against the documentation; exploratory.
- **Spend through round 3**: $15.01 for 16 Sonnet subject calls ($0.25 a single-pass call, about $1.00 a recursive
  one) and $12.15 for 34 Opus judge calls ($0.36 each); the 16 Sol calls are not costed by their CLI.

### Four corrections to what this journal said earlier

1. **The Codex isolation leaked, in every Sol session.** Section 1 and the registration commit said the Codex host
   ran "in a throwaway CODEX_HOME that links only auth.json" and that isolation was verified. It was verified for
   Claude, by reading the smoke session's stream; for Codex only the exit code and the written file were checked.
   The streams show that all 16 Sol sessions of rounds 1 to 3 read a user-level skill from the real HOME:
   `~/.agents/skills/illustrated-authoring/SKILL.md` in 15 of them, across all four arms, and
   `~/.codex/skills/agentic-execution/SKILL.md` in 4, all recursive-form (B twice, C once, D once) and no
   single-pass one. The first is a document-authoring guide ("economical prose"; it also says to "preserve exact
   identifiers, values, units, operational limits", so it does not explain Sol's value-free bounds). The second
   describes orchestrating subagents; no session spawned one.
   - What stands: comparisons between arms on Sol, read as "with that authoring skill loaded in every arm".
   - What does not: any comparison between the drivers. "Sonnet high beats Sol medium on both arms" (section 3)
     compared a clean driver with a contaminated one. **Superseded 2026-11-20** until Sol is re-run clean.
   - The 16 Sonnet sessions are clean: none read outside its own directory, and the one that tried to write
     outside it was refused by the host.
   - Fixed: a Sol call now runs in the E2E harness's own profile (`hosts.CodexHost.env`: a throwaway HOME with its
     own keychain and git identity, kept beside the working directory rather than inside it), which is what the
     harness has always done and what `use-the-codex-harness` already says. A smoke call on the fixed runner read
     nothing outside (`evidence/smoke-iso/leaks.txt`). `grade.py leaks` now checks every stream of every round and
     the queue stops if one leaks.
2. **The arms did not differ only in procedure.** Section 1 and the README said they share their clause rules. Arm
   B paraphrased the control's rules and lost two sentences: "Add no feature the request's intent does not cover",
   and the coverage sentence that ends "every limit, boundary and error case, with its exact number". So (a) the
   recursive arms had no scope guard and nothing here measures how much they ask for beyond the request, and (b)
   round 2's reading that the enumeration rule "fixes a driver that under-commits" is partly the restoring of a
   rule the control always had. The decision to carry the rule forward stands; the credit for it changes.
3. **R5 was read off the model's own account.** "Passes recorded per case: Sonnet 8, 9, 7, 9" counted sections of
   `passes.md`. Sol does write each section as it finishes that pass. Sonnet writes the first, works on as one
   stream of edits and appends, and writes most of the log afterwards (the Grokbot session: one 732-character
   write at the start, a 5,859-character write of the whole log near the end, then one edit adding the stopping
   pass). The work is real: 44 edits and four whole-file re-reads in that session. The count of passes is a
   retelling, so "the stop rule ran rather than being announced" is shown for the last read-throughs, not for the
   numbering.
4. **"Sonnet used none [no web search] in any of its 8 calls"** holds for round 1 (0 of 8) and round 2 (0 of 4);
   one of four round-3 Sonnet sessions searched twice. Sol searched in 9 of its 16 sessions.

### The queue, registered before any of it runs

The README's "Registered follow-ups" holds the readings R6 to R13 and their thresholds; `queue-2.sh` runs them in
order. What each is for:

| step | what runs | the question |
| --- | --- | --- |
| round 4 | A and D again, both drivers, clean Codex isolation: 16 calls | How big is the noise (R6)? Did the leak move Sol (R7)? Does D over A repeat (R1)? |
| round 5 | F-guarded, L-lenses-once, S-sectioned, both drivers: 24 calls | Does the restored scope guard cost coverage (R8)? Is it the iterating or the lenses (R9)? Do sections by dimension lift the weak categories (R11)? |
| judge checks | round 4 judged again by Opus, and by gpt-6.2-astra: 34 calls | How much of the noise is the judge's (R12)? Do the findings hold under a judge of another family (R13)? |
| clause audit | every clause of rounds 4, 5 and 1 classed: 56 calls | How much of a recursive specification is beyond the request, empty or wrong (R10)? |

Two instruments were calibrated before being queued: the fixed isolation (above) and the audit judge, which put 8
of 8 planted clauses in their planted class and flagged 0 of 10 legitimate ones, on labels written before it ran
(`evidence/cal-audit-result.txt`). Its planted extras are blatant (a Slack message, a dashboard); how it draws the
line between a decision a builder had to make and a feature nobody asked for will show in its `why` lines.

Considered and not queued, with the reason:
- **Sol at high effort.** Would say whether Sol's gap is effort or model. The owner named Sol medium; one cell to
  add later if the clean Sol numbers still trail.
- **A case with a real repository.** The four cases have no code, and ShipLoop's spec stage usually has some. The
  ratchet pilot's cases cover that side through the built product; here it belongs to the fold-back check on the
  real stage.
- **Checking platform figures against the documentation.** ShipLoop's duty-10 condition already requires it of the
  real stage; the audit's `wrong` class is a first, undocumented reading.
- **Ablating single passes.** R9 answers the larger question first; if iterating does not earn its place, which
  pass earns it is moot.

## 6. The plan to conclude, revised ten minutes into round 4 (2026-11-20)

**The owner's question.** "What's the status? Should we update the plan on how to conclude?" Status at that moment:
`queue-2.sh` had been running for four minutes, 2 of round 4's 16 subject calls were done, and nothing new had been
measured since section 5.

**Answer: yes, and for a reason that is this session's miss.** Section 5's queue answers eight questions about the
experiment. The conclusion the owner set at the start is narrower: a small side experiment, then reincorporation
into ShipLoop. That is one decision, on what goes into ShipLoop's `spec` stage, and it needs four answers:

| the decision needs | where it comes from | was it in the queue |
| --- | --- | --- |
| Is the gain real beyond noise, on clean isolation? | round 4 (R6, R7, R1) | yes |
| Which form: going round again, or the lenses in one pass? | round 5, F against L (R9) | yes |
| Does it ask for more than the request does? | the clause audit (R10) | yes |
| **Does it add anything to the stage ShipLoop ships?** | nothing | **no** |

The fourth is the miss. Section 1 called arm A "the current state of the art" and made it the control. It is the
ratchet pilot's enrich text, the newest text for this job. It is not ShipLoop's released `spec` stage, whose twelve
duties already ask for async completion and recovery (duty 8), the owner, readers, end and quotas of each piece of
state (duty 9), designed interface states and bounded non-functional requirements (duty 6) and a state and data
assessment (duty 7). Every result in sections 3 to 5 therefore reads "better than the ratchet pilot's single pass",
and none reads "better than ShipLoop". The released stage could already sit near the recursive arms, in which case
the honest conclusion is that nothing should be folded back.

**What changed (routine: this experiment's own runs).**
- Added `P-shiploop-spec`: `shiploop_prompts.prompt("spec")` word for word, in a frame that says what is absent
  when the stage runs alone, with the skill's reference guides to hand as a real run has them. Reading R14 is in
  the README. P is a lower bound on the real stage (no intake, discovery or research ran before it), and it writes
  ShipLoop's R-n form, so the judge was checked on that form before any P call: the calibration specification
  re-laid as eight requirements with acceptance lines scored 7 of 27 covered, as it did in U-n and C-n form, the
  same covered-or-not on 27 of 27 nuances and the same state on 26 (`evidence/cal-rn-result.txt`).
- Withdrew `S-sectioned` before any call of it ran. Its question is the one P answers better, since the released
  stage is already laid out by dimension, and its layout would not carry into a stage that writes R-n requirements.
  The dimensions are the owner's own list, so the arm file stays and one command runs it.
- Withdrew the clause audit of round 1: an old claim, on sessions now known to have leaked.
- `queue-2.sh` was stopped by ending its own shell after round 4's subject calls had started; the calls in flight
  ran on. `queue-3.sh` waits for them, then carries on with round 4's checks, round 5 as F, L and P, the two checks
  of the judge, and the clause audit of the arms that write C-n clauses.

**How it ends** is registered in the README: four answers, one of three outcomes (no fold-back; the lenses as one
pass; the iterating form), a drafted change to the stage's duty text reviewed by Sol at max, the owner's decision
on the trade-off, and only then the change note, the suites, the E2E round and the release. Stop rule: no further
arm; an interim answer gets one more draw of the same arms.

**Whose is what.**
- This session's: rounds 4 and 5, the judge checks, the audit; reading R6 to R14; the draft or the "no change"
  conclusion; the Sol review and an adversarial read of this journal.
- The owner's: whether to fold it in at all once the numbers are in (a product-behaviour trade-off); where it
  lands, the released stage, the ratchet pilot's enrich stage, or both; whether the sections arm should still run;
  whether Sol at high is worth a cell.
- Another session's: the ratchet pilot, which measures the same idea through the built product. If the owner wants
  this text or this instrument there, that session takes it; its branch and runs were not touched.

**Owner's decision, 2026-11-20 (answer to "where should the winning text land once the numbers are in?"):
"Released spec stage."** The fold-back, if the four answers warrant one, is drafted against the released `spec`
stage's duty text in `skills/shiploop/scripts/shiploop_prompts.py` and nowhere else. The ratchet pilot's enrich
stage is not a target of this experiment; nothing is sent to that session unless the owner asks.

## 7. Round 4's leak check stops the queue: Codex shows the user's skills to every session, whatever the profile (2026-11-20)

**What happened.** `queue-3.sh` ran round 4's last subject calls, ran `grade.py leaks round-4`, and stopped: 7 of
the 8 Sol sessions had read `~/.agents/skills/illustrated-authoring/SKILL.md` or
`~/.codex/skills/agentic-execution/SKILL.md`, although every one of them ran in the E2E harness's own throwaway
profile (`hosts.CodexHost.env`), which section 5 had called the fix. The check was written to stop the queue on
exactly this, and it did, before any verdict or any round-5 call was spent on it.

**Superseded, 2026-11-20:** section 5's "Fixed ... A smoke call on the fixed runner read nothing outside." The
smoke call was one session, and one session in sixteen had not opened a skill under the old runner either. A clean
sample of one was read as a proof. It was not one.

**The mechanism, established without a model call.** `codex debug prompt-input` prints what a session's model is
shown. Run under the harness profile it lists three skill roots: `r0 = /Users/dadleet/.codex/skills`,
`r1 = <the throwaway CODEX_HOME>/skills/.system`, `r2 = /Users/dadleet/.agents/skills`, and the ten user-level
skills under r0 and r2 (advisors, agentic-execution, ask, evidence-first-recommendations, illustrated-authoring,
jevify, lennox-s40, smartthings-ops, test-runner, typesafe-ai).
- The environment is not how it knows: with nothing set but `HOME`, `CODEX_HOME` and `PATH`, both pointing at the
  throwaway, the two real-home roots are still listed. Codex 0.171.0 takes the account's home from the system.
- No feature flag tried removes them: `--enable skip_host_skill_discovery`, `--disable skill_search`,
  `--disable plugins`, `--enable omit_skill_descriptions`.
- Turning the skills off one by one does: `-c skills.config=[{path="<SKILL.md>",enabled=false}, ...]` for the 11
  `SKILL.md` files under the two roots (four of the skill folders are symlinks, which a plain recursive search
  skips; the first version of the override missed them and the check caught it). With it the prompt input holds no
  path under the real home at all: 2 roots and 10 skills before, none after, 83,349 characters to 77,049.

**The fix here.** `codex_isolation.py` builds the override and holds `preflight`, which renders the prompt input
for a session's environment and returns whatever it still shows from the real home. `run.py` passes the override on
every Codex call and refuses to start a round unless `preflight` returns nothing; `grade.py` passes it to the Codex
judge; `grade.py leaks` no longer counts a path that does not exist (a session that looks for an `AGENTS.md` above
its directory and finds none read nothing). Firm for Codex 0.171.0; a new CLI version re-runs the check by
construction, since every round starts with it.

**This is wider than this experiment (read-only evidence; nothing of another session's was touched).** The E2E
harness uses the same profile for every Codex session it starts. Its own archived runs show sessions reading the
owner's skills from inside harness throwaway homes: on 2026-11-05 the `review-knowledge` sessions of the chess
improvement runs ran `cat /Users/dadleet/.codex/skills/agentic-execution/SKILL.md` (their rollout logs under
`<run>/review-knowledge-0N/home/.codex/sessions/`). Across four folders sampled (2026-11-02, 2026-11-05,
2026-11-15, the 2026-11-18 closed-loop smoke) there are 159 mentions of `agentic-execution/SKILL.md` and 12 of
`test-runner/SKILL.md`; by folder, files naming a user-level skill path number 119 under 2026-11-01, 76 under
2026-10-31, 75 under 2026-10-30, 68 under 2026-11-02, and fewer back to 2026-10-05. The ratchet pilot's 23 run
folders, searched whole, name none: its sessions were shown the skills and did not open them. So the exposure is
every Codex session of the harness, and the measured effect depends on the task: a session asked to write a
document opens `illustrated-authoring` (21 of the 24 Sol sessions here), one asked for thorough agentic work opens
`agentic-execution` (7 of the 24, every one of them a recursive-form session).
- Not done here: no change to `test/shiploop_e2e/hosts.py`. It is shared apparatus, other sessions run from it,
  and turning the skills off changes what every later Codex E2E run is compared with. That is the owner's call
  (AGENTS.md, Decisions: a default that breaks comparability). It is put to the owner as its own task, with the
  override and the no-model check ready to carry over.

**What round 4 is now.** Its 8 Sonnet sessions are clean: R6 as registered. Its 8 Sol sessions are a second draw of
the leaked condition of rounds 1 to 3, which gives something nobody planned: how far Sol moves between two draws
with the same skills shown. Round 4c runs A and D on Sol with the skills turned off, and R7 reads that clean draw
against both leaked ones. Round 5 (F, L, P), the two checks of the judge and the audits of the clean
specifications follow as registered; `queue-4.sh`.

## 8. Round 4: the noise floor is 6, so the band is 12; the main effect repeats at 2.5 times that (2026-11-20)

Round 4 drew arms A and D a second time. Verdicts `grades/round-4/`, readings `evidence/round-4/readings.txt`.
Recorded while round 4c was running and before any round-5 call, so that round 5 is read against a band fixed
beforehand.

| arm | driver | first draw | second draw | move | per case (csv, grokbot, gym, invoice) |
| --- | --- | --- | --- | --- | --- |
| A-single | Sonnet high, clean both times | 46 | 40 | -6 | -1, -4, +2, -3 |
| D-enumerated-only | Sonnet high, clean both times | 73 | 71 | -2 | +4, +2, -5, -3 |
| A-single | Sol medium, skills shown both times | 38 | 40 | +2 | +2, -2, +2, 0 |
| D-enumerated-only | Sol medium, skills shown both times | 62 | 58 | -4 | 0, -1, -2, -1 |

**R6, the noise floor: 6 of 89.** The same arm, the same driver and the same judge prompt moved by up to 6 pooled
and by up to 5 on a single case. The registered rule applies: the band of 4 was too narrow, and **a difference
between two single draws smaller than 12 is not shown**. Firm as a floor (two arms, one replicate each, so the true
spread may be larger, not smaller).

**R1 again: the main effect holds, comfortably.** Within round 4 alone, D minus A is **+31 on Sonnet and +18 on
Sol**. On the means of two draws it is +29 and +21. The recursive form over the single pass is the one result of
this experiment that is established: about 2.5 times the band on Sonnet, 1.75 times on Sol. Status: firm for
Sonnet; for Sol, firm with the user-level skills shown in every draw, and round 4c will say whether it holds without.

**Superseded 2026-11-20 by this measurement:**
- Sections 4 and 5, "the enumeration rule alone: +12 on Sol", "the delta that carried Sol's gain", "difference
  shown". Against the mean of D's two draws it is +10, under the band. **Not shown.** The rule may help Sol; one
  draw of B and two of D cannot say so.
- Section 5's ordering "D >= C >= B" on Sol. B, C and D are not told apart on either driver: Sonnet 72, 74, 73 and
  71; Sol 50, 60, 62 and 58.
- What stands from sections 4 and 5: the operator pass shows nothing (-2 and +1) and costs Sonnet minutes, so it
  stays dropped; D stays the arm carried forward, as a choice among arms that cannot be told apart, on cost.

**What this does to round 5, fixed here before it runs.** Every reading registered as "8 or more" is read at 12,
which is the rule R6 and R14 already stated and which R8 and R9 are now held to as well:
- **R9.** Iterating earns its place on a driver if F minus L is 12 or more. Under 12 on both drivers, with L at or
  under 60% of F's minutes and of its output tokens, makes the one-pass form the candidate. Between 8 and 11 is
  interim and gets one more draw of F and L.
- **R8.** The guard costs no coverage if F is within 12 of D (the mean of its two draws on Sonnet; the clean draw
  of round 4c on Sol).
- **R14.** The elaboration adds to ShipLoop if the better of F and L is 12 or more above P on a driver.
- **R7.** Clean Sol against the mean of the two draws with the skills shown (A 39, D 60): a move of more than 6
  supersedes the earlier Sol numbers.

**A limit this makes plain.** A band of 12 in 89 means one draw an arm can only show large effects. That suits the
decision at hand, which prefers the cheaper form unless the dearer one is clearly better; it would not suit tuning
the wording of one arm, and section 5's "which pass earns its place" could not be answered at this size.

## 9. Round 4c: Sol with the skills turned off; the leak had been lifting the single pass, not the recursive form (2026-11-20)

8 calls, A-single and D-enumerated-only on Sol, started only after the pre-flight render showed a session none of
the user's skills. **The scan of the streams afterwards: 0 of 8 sessions read anything outside their own directory
and profile** (`evidence/round-4c/leaks.txt`). That is the first check of the override on sessions that ran, and it
agrees with the render. Readings `evidence/round-4c/readings.txt`.

| arm on Sol medium | skills shown, two draws | skills off | move |
| --- | --- | --- | --- |
| A-single | 38 and 40 (mean 39) | **29** | -10 |
| D-enumerated-only | 62 and 58 (mean 60) | **64** | +4 |

**R7.** The single pass moves by 10, more than the 6 registered, so **the A-single Sol numbers of rounds 1 and 4
are superseded: on clean Sol the single pass covers 29 of 89, not 39.** The recursive arm moves by 4, inside 6, so
its earlier draws stand. One clean draw each; the level of the clean single pass is 29 give or take the floor.

**What the leak was doing.** `illustrated-authoring` is a guide to writing documents: check the draft against the
source for prerequisites and failure boundaries, keep exact values and limits. Shown to a session writing a
specification in one pass, it appears to have worked as a second set of instructions and lifted that arm by about
ten nuances. The recursive arm, whose own instructions already ask for all of that, gained nothing measurable from
it. So the leak made the control look better than it is on Sol and **understated** the effect under test there.

**R1 on clean Sol: +35** (D 64 against A 29), where the draws with the skills shown gave +24, +18 and +21 on means.
The recursive form's lead over the single pass is now established on both drivers on clean isolation: about +29 on
Sonnet (means of two draws), +35 on Sol (one draw each). Firm.

**The two drivers, clean against clean.** Single pass: Sonnet 43 (mean of two), Sol 29, a gap of 14, shown at the
band of 12. Recursive: Sonnet 72 (mean of two), Sol 64, a gap of 8, not shown. Section 3's "Sonnet high beats Sol
medium on both arms", superseded in section 5 as a comparison of a clean driver with a leaked one, can now be
restated on clean numbers: **Sonnet leads on the single pass; on the recursive form the two are not told apart.**
The recursive form more than doubles what Sol at medium covers (29 to 64) and brings it to within the band of
Sonnet at high. For a harness that runs on both, that is the more useful half of the result.

Three of the eight clean Sol sessions searched the web, as before.

## 10. Round 5's subject calls; a refused listing stops the queue; the held-out checklist was never reached (2026-11-20)

**Round 5 ran**: 24 calls (F-guarded, L-lenses-once, P-shiploop-spec on both drivers), all exit 0, after a passing
pre-flight. Its leak check then flagged 1 of 24 and stopped the queue a second time.

**What the flag was.** `gym-waitlist__P-shiploop-spec__sonnet-high` issued one shell command that, among other
things, listed its round's folder (`ls ~/e2e-runs/spec-elaboration-20261120/round-5/`). The host refused the whole
command ("requires approval"), so nothing ran and nothing was read. The check had counted any existing path under
the real home, folders included.

**The question it raised is the right one, so it was answered in full before going on.** The judges' working
folders hold `checklist.json`, the held-out nuances of a case, and they live beside the subjects' folders. A
subject that climbed out of its own folder with `../` could have read one, and the check as written resolved only
absolute paths. All 80 subject streams of rounds 1 to 5 were scanned for every tool call that climbs above its
working directory and for any that names the checklist, a verdict, the cases file, or a judge or audit folder:
- 42 tool calls climb. 34 do nothing but look for an `AGENTS.md` in the folders above (none exists). 6 are P-arm
  Sol sessions writing `KNOWLEDGE/spec.md` with links to `../GUIDES/...`, inside their own folder.
  **2 listed the names in their round's folder** (`ls -la ..`:
  round 1 `gym-waitlist__A-single__sol-medium`, round 5 `grokbot-salesforce__L-lenses-once__sol-medium`), which
  shows the names of the other sessions' folders, arm names included, and no file's contents. In both rounds the
  judges had not started, so no judge folder was there to list.
- **No tool call in any session names the checklist, a verdict, the cases file, or a judge or audit folder.** The
  three places those words appear are the sessions' own specification text ("status checklist",
  "audit-retention rules").
- So the statement in section 1, that no subject can read the held-out checklist, was true of what happened in
  all 80 sessions and was never enforced by anything. It is now checked.

**The check, restated and made stricter where it matters.** A leak is a file that exists under the real home
outside the session's own folder and profile, named absolutely, with `~`, or by climbing with `../` (resolved
against the working directory); or any tool call naming the held-out material. A folder named outside and a path
that does not exist are reported and do not count. Re-run on every round: round 1, 8 of 16; round 2, 4 of 8;
round 3, 4 of 8; round 4, 7 of 16 (every one a Sol session reading a user-level skill); **round 4c, 0 of 8;
round 5, 0 of 24**; and no session in any round named the held-out material.
- Loosening a check right after it fires deserves suspicion. What was loosened: a folder's name no longer counts,
  only a file that could be read. What was added: climbs are resolved, and the held-out material is searched for
  by name. The one session it had flagged was refused by the host before anything ran.
- Still open: nothing stops a subject from reading a sibling's folder or a judge's; the check finds it afterwards.
  Subjects of a round all finish before that round's judges start, which is why no judge folder was reachable in
  the round being run, but earlier rounds' judge folders sit two levels up. A round that fails this check is not
  used.

**Round 5's cost, before any verdict** (`evidence/round-5/cost.txt`; clean sessions, per case):

| arm | Sonnet: minutes | output tokens | words | Sol: minutes | output tokens | words |
| --- | --- | --- | --- | --- | --- | --- |
| A-single | 2.1 | 15,317 | 3,508 | 2.9 | 7,951 | 3,537 |
| L-lenses-once | 2.9 | 21,484 | 4,497 | 3.8 | 10,381 | 6,469 |
| P-shiploop-spec (the released stage) | 5.7 | 43,342 | 8,546 | 5.1 | 12,273 | 5,459 |
| D-enumerated-only | 7.3 | 57,787 | 6,817 | 6.6 | 18,039 | 7,311 |
| F-guarded | 5.5 | 43,379 | 5,712 | 7.1 | 18,594 | 8,156 |

- **R9's cost side is met on both drivers**: the one-pass arm takes 52% of the iterating arm's minutes on Sonnet
  (50% of its output tokens) and 54% on Sol (56%). Sonnet's one-pass sessions made 2.0 writes or edits a case
  against 21 for the iterating arm, so they did write once.
- The released stage run alone costs about what the recursive arms cost: 5.7 minutes and 43,000 output tokens a
  case on Sonnet. It opened 4 to 12 of the skill's guides a session, wrote an `architecture.md` beside the
  specification in 5 of 8 sessions, and both Grokbot sessions opened the skill's Salesforce card, which is
  recorded so that their platform score can be read as partly the card's.
