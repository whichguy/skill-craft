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

> **Superseded 2026-11-21** (the Sol review, checked; section 14): 12 is the registered decision threshold and nothing more. It is the largest move seen in two
> replicate pairs on Sonnet; it does not estimate the spread of clean Sol (never replicated), of a mean against a
> single draw, or the shares of subject and judge, which are reported separately (the same judge re-reading fixed
> specifications moved a pooled cell by up to 5). The 89 verdicts are clustered in four requests.

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

> **Superseded 2026-11-21** (the Sol review, checked; section 14): the clean draw justifies replacing the earlier baseline; it does not identify a cause.
> What is measured: clean Sol scored 29 on A and 64 on D, the A score ten below the mean of two draws with the
> skills shown. Half of A's fall is one case (Grokbot, 13 to 8). The runner's context and the draw both changed,
> different skills were opened by different arms (`agentic-execution` in three of round 4's D sessions), and
> sessions searched the web on their own. `illustrated-authoring` is one possible contributor.

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

> **Superseded 2026-11-21** (the Sol review, checked; section 14): read as "no explicit reference to the held-out material was detected in the 80 archived
> streams under this scan". The scan reads the command and path fields of tool calls; it would not see a read made
> through a glob or a variable that never names the file, it ignores paths outside the home, it exempts the whole
> of a round's `.homes` folder, and it does not check which calls succeeded. Nothing makes the held-out files
> unreachable to a subject. `run.py` also skips a kept specification without checking where it came from.

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

> **Superseded 2026-11-21** (the Sol review, checked; section 14): 6 of 8 sessions wrote an `architecture.md` (four Sonnet, two Sol), not 5. "Opened" is
> "named in a tool call": the count is of guide paths mentioned, not of reads known to have succeeded. And
> Sonnet's one-pass sessions averaged 2.0 writes or edits (the Grokbot one: one write and three edits), so "they
> did write once" should read "they wrote once and touched it up".

## 11. Round 5: the lenses in one pass do the work, iterating adds nothing shown, and the released stage is only beaten clearly on Sol (2026-11-20)

24 specifications judged; readings `evidence/round-5/readings.txt`, against the band of 12 fixed in section 8.
Covered of 89, clean sessions only (A and D are the clean references: Sonnet the mean of two draws, Sol round 4c):

| arm | Sonnet high | Sol medium | minutes a case, Sonnet / Sol |
| --- | --- | --- | --- |
| A-single (the ratchet pilot's enrich text) | 43 | 29 | 2.1 / 2.9 |
| **P-shiploop-spec (the released stage, alone)** | **58** | **43** | 5.7 / 5.1 |
| **L-lenses-once** | **64** | **62** | 2.9 / 3.8 |
| F-guarded (iterating) | 68 | 60 | 5.5 / 7.1 |
| D-enumerated-only (iterating, no guard) | 72 | 64 | 7.3 / 6.6 |

**R9, which form: one pass.** F minus L is +4 on Sonnet and -2 on Sol, neither near 12, and L costs 52% and 54% of
F's minutes. By the rule fixed beforehand the one-pass form is the candidate. And the lenses in one pass, against
the single pass without them, are **+21 on Sonnet and +33 on Sol**: that is where the gain of sections 3 to 9
comes from. What this experiment called "the recursive form" earned its numbers through what it told the model to
consider, not through going round again. Section 5's first-draft table had pointed there; this is the arm that
could say so. Status: firm at this size (a real effect of iterating under about 12 cannot be excluded and would
not change the decision at twice the cost).

**R8, the guard: holds.** F is 4 under D on both drivers, inside the band. Putting back "Add no feature the
request's intent does not cover" and the coverage sentence costs no coverage shown. Whether it buys less scope is
the clause audit's question (R10), still running.

**R14, does it add to the stage ShipLoop ships: clearly on Sol, not shown on Sonnet.**
- Sol medium: L is **+19** over P (F +17). Shown.
- Sonnet high: L is +6 over P, not shown; F is +10, in the interim range, and F is not the candidate.
- The released stage itself is +15 and +14 over the ratchet pilot's single pass, so section 6 was right to doubt
  the control: most of what sections 3 to 5 reported as the elaboration's lead on Sonnet (+29) was a lead over a
  text ShipLoop does not ship. Against what it does ship, Sonnet's lead is 6 to 10.
- Where the lenses beat the released stage: on Sonnet almost only the operator's work (2 of 9 for P, 5 for both
  lens arms); on Sol nearly everywhere, most in edges (5 of 12 to 9), unhappy paths (8 to 11), non-functional
  bounds (1 of 5 to 3), platform rules (2 of 5 to 4) and permissions (5 of 8 to 7). The released stage's weakest
  category on both drivers is the operator's work: 2 and 3 of 9.
- P is the stage without the stages that feed it and with every guide to hand; both Grokbot P sessions opened the
  skill's Salesforce card. It is a stand-in for the real stage, not the real stage.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): **R14's "+19 on Sol: shown" does not show that the lenses add to the released stage, and
> the sentences above that say where they "beat" it are withdrawn.**
> - Counting a nuance as *touched* when it is covered or partial: P 87 and 87; L 86 and 89; F 89 and 87; D 89 and
>   86; A 78 and 71. **The released stage already reaches 87 of the 89 nuances on both drivers.** Of the 20 nuances
>   L covers on Sol that P does not, 19 are `partial` under P and 1 is `absent`; on Sonnet all 12 are `partial`
>   under P, and 6 that P covers L does not. The whole difference is in how far a nuance both specifications reach
>   is decided, not in whether it is found.
> - Where P is `partial` it has often decided, by its own duties, to leave the thing out or open: "the spec
>   decides not to persist conversations", "no audit store is added", "production is declared out of scope",
>   "the timeout remains open". Duty 6 says to invent no bound and duty 9 to add no persistence the request does
>   not need.
> - **The judge scored such decisions unevenly.** Sonnet's P, deciding not to persist conversations: `partial` on
>   the stored-shape nuance. Sol's L, "The bot has no bot-managed conversation or result history": `covered` on the
>   same nuance. Sol's L is also `covered` on "cancelling an import that is running" by a clause that declines to
>   add cancellation. The judge prompt never said how to score a stated exclusion or an open item, so a
>   specification that decides more scores higher whether or not deciding was right.
> - The operator's work is the released stage's lowest category on Sonnet (2 of 9); on Sol its lowest share is
>   non-functional (1 of 5), not the operator's work (3 of 9).
> - P is not a guaranteed lower bound on the stage in a real run; it lacks the stages that feed it and has every
>   guide to hand, and which way that nets is unknown.

**What the four answers say** (the third is still running):
1. Real beyond noise: yes for the lens content (+21, +33 in one pass).
2. Which form: one pass.
3. Does it overbuild: pending the clause audit.
4. Does it add to the released stage: yes on Sol at medium (+19); not shown on Sonnet at high (+6).

> **Superseded 2026-11-21** (the Sol review, checked; section 14): 4 is not answered by this instrument. See the note above: both reach the same nuances.

So the outcome the plan to conclude called "fold in the lenses as one pass" is the one the evidence supports, with
its size stated honestly: a large gain for a weaker driver, a small or no gain for a stronger one, at no cost in
coverage either way. And one thing the plan did not foresee: L and P are alternatives here, and the fold-back is
neither. It is P with the lenses added, a text no round has run.

## 12. The judge, checked twice; and the fourth answer: iterating is what adds scope, the one-pass form adds none (2026-11-20)

### The coverage judge (R12, R13), on round 4's 16 specifications

`evidence/round-4/agreement.txt`; the second sets sit beside the registered verdicts in `grades/round-4@r2/` and
`grades/round-4@gpt/` and replace nothing.

- **The other judge is calibrated the same way first.** Codex gpt-6.2-astra at high, with the same prompt, on the
  calibration pair: 0 of 27 on the vacuous specification (Opus 0) and 7 of 27 on the aimed one (Opus 7).
- **R12, the same judge again:** the same covered-or-not on 94% of 356 nuance verdicts, the same state on 92%; per
  specification a mean move of 1.0 and a largest of 5; pooled by cell -1, +2, +5 and 0. So the judge alone moves a
  pooled cell by up to 5, which is most of the floor of 6 measured in section 8: at this size the judge's draw
  matters about as much as the subject's.
- **R13, a judge of another family:** stricter everywhere (39 verdicts go from covered to partial; the pooled
  cells fall by 3 to 12) and agreeing on covered-or-not for 87%. What the registered reading asked:
  - D over A on Sonnet: +31 under Opus, **+26 under astra**. Holds.
  - D over A on Sol: +18 under Opus, +10 under astra. These are round 4's Sol sessions, the ones with the
    user-level skills shown, where section 9 found the single pass inflated; the clean pair of round 4c has not
    been read by astra.
  - Sonnet over Sol on the recursive arm: +13 under Opus, +12 under astra. It does not shrink, so that gap is not
    the judge's family favouring its own.
- Status: the main effect and the ordering of the drivers do not depend on which family judges. The deciding
  round, round 5, has been read by one judge only; that is queued below.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): too strong. Astra read round 4 only: arms A and D. It keeps the large D over A difference on
> Sonnet (+26) and its sign on Sol (+10, which is under the threshold of 12, on the sessions with the skills
> shown). It has read nothing of L, P, Q or clean Sol.

### The clause audit (R10): the fourth answer

One Opus session a specification put every clause in one class. Clean specifications only (round 4 Sonnet,
round 4c Sol, round 5 F and L); no clause left unclassed in any of the 32. `evidence/round-{4,4c,5}/audit.txt`.

| arm | Sonnet: clauses | called extra | Sol: clauses | called extra |
| --- | --- | --- | --- | --- |
| A-single | 181 | 17% | 225 | 17% |
| **L-lenses-once** | **220** | **13%** | **372** | **13%** |
| F-guarded (iterating, guard restored) | 308 | 23% | 527 | 20% |
| D-enumerated-only (iterating, no guard) | 366 | 26% | 478 | 27% |

- **The iterating form adds scope: shown.** D's share of clauses beyond the request is 9 and 10 points above the
  single pass (threshold 5), and in count about three times as many (94 against 30 on Sonnet, 127 against 38 on
  Sol).
- **The guard helps on Sol and is not shown to on Sonnet.** F against D: -7 points on Sol, -3 on Sonnet.
- **The one-pass form does not add scope at all.** L is at 13% on both drivers, below the single pass. Whatever
  makes a specification grow things nobody asked for, it is going round again, not the lenses.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): three things here do not stand as written.
> - **"Does not add scope at all" is wrong in count.** L's *share* of clauses labelled extra fell from 17% to 13%
>   on both drivers. In count it went from 30 to 29 on Sonnet and **from 38 to 48 on Sol** (the CSV case 5 to 13).
>   And the scope of the released stage was never audited, so nothing here compares L, or the draft, with it.
> - **The guard is not shown to help.** By case, D to F, the count labelled extra goes 28 to 41 and 22 to 43 on
>   Grokbot, 23 to 4 and 19 to 14 on the waitlist, 29 to 18 and 37 to 38 on invoices, 14 to 7 and 49 to 11 on CSV
>   (Sonnet then Sol). The pooled shares are sums of opposite moves by single draws.
> - **"It is going round again" is not isolated.** F and L differ as packages: the stop rule, the intermediate
>   writes, the pass log and the builder's read all change together, and L keeps the "each requirement you have
>   written" recursion in its wording. What is measured is that the iterating packages carried more clauses
>   labelled extra, in share and in count, and no more coverage.
- `empty` is 0 to 1% on Sonnet and 3 to 5% on Sol; `wrong` is 1% or less everywhere. Section 3's "Sol adds clauses
  that carry no decision" was a reading of a handful of clauses under an arm that has not been audited; under the
  arms that have, the share is small. That sentence is not supported at the size it was stated.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): the figures by count: `empty` is 1 clause in each Sonnet arm; on Sol 1 of 225 for the single
> pass and 18 of 372 for L (4.8%). `wrong` is at most 3 of 220 (Sonnet's L, 1.4%), not "1% or less everywhere".

### The two instruments pull against each other in one place, and it is the owner's place

The audit reads "beyond the request" strictly: it calls an import audit log, a per-user rate limit, an
administrator's history page extra, because the request works without them. The checklist counts several of those
as things a well-elaborated specification states. `evidence/round-5/coverage-vs-audit.txt` measures the overlap:
a covered nuance "rests on an extra clause" when the clause the coverage judge cites for it is one the audit calls
extra.

| arm | Sonnet: covered | resting on an extra clause | Sol: covered | resting on an extra clause |
| --- | --- | --- | --- | --- |
| A-single | 40 | 2 | 29 | 2 |
| L-lenses-once | 64 | 5 | 62 | 4 |
| F-guarded | 68 | 14 | 60 | 6 |
| D-enumerated-only | 71 | 11 | 64 | 10 |

- **Counting only coverage a strict reader would also accept, the one-pass form is ahead of the iterating one**:
  L 59 and 58, F 54 and 54, D 60 and 54. F minus L goes from +4 and -2 to -5 and -4. Iterating buys nothing a
  strict reader accepts; what it buys is the scope.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): this is "coverage after dropping a verdict whose *first* cited clause was labelled extra",
> and no more than that: it does not show that a kept verdict is sound or that a dropped one depends on extra
> work, and some verdicts cite only a use case. Dropping a verdict when *any* cited clause is extra gives L 58 and
> 56, F 53 and 54, D 53 and 52.
- The one-pass form's lead over the single pass is untouched by the strict reading: +21 and +31 (against round
  4's draw of A on Sonnet, 40; the +21 of section 11 was against the mean of its two draws, 43).
- **Seventy percent of the operator nuances the lens arms cover rest on clauses the audit calls extra** (19 of
  27); no other category is above 19%. The operator's work is where the lenses beat the released stage most on
  Sonnet, and it is exactly where "rigour" and "unrequested scope" are the same clause read two ways. Which
  reading ShipLoop wants there is a product judgement, the owner's own rule being that rigour is standard and only
  unrequested scope is overbuilding.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): the 19 of 27 pools L, F and D and is carried by the iterating arms. For L against P on
> Sonnet the claim is false: its three operator gains are all on Grokbot and cite a use case, a clause the audit
> classed `decision` and one it classed `needed`. None rests on a clause labelled extra.

### The four answers

1. **Real beyond noise?** Yes, for the lens content: +21 on Sonnet and +33 on Sol in one pass, holding under a
   strict reading and, on Sonnet, under a judge of another family.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): the second judge read D against A, not L. And "real" here means against the ratchet
> pilot's single pass, which is not what ShipLoop ships.
2. **Which form?** One pass. Iterating shows no coverage gain, loses on strictly accepted coverage, takes twice
   the time and is where the unrequested scope comes from.
3. **Does it overbuild?** The one-pass form does not (13% of clauses beyond the request, under the single pass's
   17%). The iterating forms do (20 to 27%).
4. **Does it add to the stage ShipLoop ships?** On Sol at medium, clearly (+19). On Sonnet at high, not shown
   (+6), and what it adds there is mostly the operator's work, which a strict reader calls scope.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): not answered. Both reach the same 87 or so nuances; the difference is in how many are
> decided, on a judge that scores stated exclusions unevenly (section 11's note).

## 13. The draft, registered before it runs (2026-11-20)

**The outcome the four answers give** is the second of the plan's three: fold in the lenses as one pass. Its size,
stated as measured: a large gain for Sol at medium (+19 over the released stage), not shown for Sonnet at high
(+6), no added scope, about a minute more than the single pass.

> **Superseded 2026-11-21** (the Sol review, checked; section 14): round 5 made the insertion worth testing, and no more. Whether it should be proposed
> depends on whether it adds grounded, in-scope coverage to the released stage, what accepted behaviour it loses,
> and what work it adds downstream, none of which rounds 1 to 5 measure. The review's verdict on the draft as
> written is "do not put it".

**Why one more arm, against section 6's stop rule.** The rule said no further arm, and the reason for it was to
stop the experiment growing sideways. But no round has run the thing that would be proposed. L is the lenses with
this experiment's own layout and none of the stage's duties; P is the stage with none of the lenses. The fold-back
is P with the lenses set into it, and whether they still do their work there, inside 1,181 words of other duties
and a different layout, is not something L and P can say between them. Asking the owner to decide on that text
unrun, with the instrument standing ready, would be asking for a decision on a guess. So one arm is added, it is
the deliverable itself, and nothing else is.

**The draft** (`arms/Q-shiploop-spec-lenses.insert.txt`): one block of 386 words inserted into duty 2 of the
released stage, after its first paragraph. Choices made in writing it, each for a reason on record:
- **One pass, said so.** "Think through what the request leaves unsaid, in one pass." Section 12: iterating shows
  no gain and is where the scope comes from.
- **Lines to think along, not an instruction to find gaps.** The five lenses are named questions with named
  answers (who meets it and how; what each sentence takes for granted; where the parts meet; the runtime's rules;
  what must hold and what must never be true). The owner's own note on prompts says open-ended "find gaps"
  instructions overbuild and instructions with a standard to check against do not.
- **The scope guard in the stage's own words**, and first: what a line turns up goes "inside the approved scope:
  add no feature the request's intent does not cover". Duty 4 already says "keep approved scope".
- **The people who run it are in the first lens**, since the operator's work is the released stage's weakest
  category on both drivers (2 and 3 of 9). Section 12 found that this is also where a strict reader sees scope;
  the guard sits in the same paragraph for that reason, and where the line falls is the owner's judgement.
- **It defers where the stage already rules.** A platform rule's source is item 10's business (the stage's
  condition is stricter than anything this experiment's arms asked). A limit with no value is "recorded as
  unresolved (item 6)", because duty 6 says to invent no bound; the arms' "state your own decided value" is not
  carried over.
- **A named dimension lists its members.** Kept from arm D. Not shown to help on its own (section 8), not shown to
  hurt, and the partials of section 3 are its reason.
- **Set inside duty 2 instead of as a new duty**, so that no duty is renumbered: the stage's code and the other
  duties refer to duties by number.

**What is registered** (README, "The draft, and the one arm past the stop rule"): round 6 runs Q and a second draw
of P on both drivers; R15 reads Q against the mean of P's two draws at the band of 12, with Q's cost against P's
and Q against L beside it; and the second judge reads rounds 4c, 5 and 6, so that the deciding comparisons have
two families' verdicts. `queue-5.sh`.

## 14. The independent review says "do not put it", and checking it shows it is right (2026-11-21)

**The review.** Before the draft was called ready it went to the latest Sol at maximum effort, as the owner's
standing rule asks: one read-only session over the repository, in the harness profile with the user's skills
turned off (pre-flight passed), 14.5 minutes. It was asked to attack the block as text that will sit in the stage,
to read sections 8 to 13 of this journal against the files they cite, and to say whether it would put the change
to the owner. Prompt and report: `docs/experiments/spec-elaboration-20261120/review/sol-max-prompt.md` and
`sol-max-review.md`; runner `review/run_review.py`.

**Its verdict: do not put it.** 21 findings, seven of them P1.

**Checked before being relayed.** Every claim of fact this session tested against the files held, including
numbers the reviewer had recomputed for itself:
- the audit's counts (finding 5): 30 of 181 to 29 of 220 on Sonnet, 38 of 225 to 48 of 372 on Sol, CSV 5 to 13;
- the make-up of L's lead over P (finding 6): 19 of 20 newly covered nuances on Sol were `partial` under P, all 12
  on Sonnet; and the two verdicts it names, read in the grade files, do credit a clause that declines the thing;
- the operator credits (finding 12): Sonnet L's three over P cite U-8, C-45 (`decision`) and C-7 (`needed`); the
  any-cited-clause variant of the strict filter gives L 58 and 56, F 53 and 54, D 53 and 52, as it says;
- the Grokbot counts labelled extra, D to F (finding 16): 28 to 41 and 22 to 43;
- the details of finding 20: 6 of 8 P sessions wrote an architecture document; Sol P's lowest share is
  non-functional; the `empty` and `wrong` counts;
- the duty and guide text it quotes (findings 2, 3, 9, 10, 11, 21): `plan` maps "every acceptance line to its
  work item", `test-strategy` limits preservation to "each existing behaviour the scoped requirements touch",
  `research` says reaching the ceiling "stops exploration, not the run", the behaviour guide says "avoid an
  unnecessary Cartesian product of all possible system states", and plan duty 7 owns stored-data structure.
Fourteen places in sections 8 to 13 are corrected in place and marked superseded with their reason.

### What the review found in the evidence

1. **The comparison that mattered most did not measure what it was read as measuring.** R14 read "L is +19 over
   the released stage on Sol" as the lenses adding to ShipLoop. Counting a nuance as touched when it is covered or
   partial, the released stage reaches **87 of 89 on both drivers**; the lens arms reach 86 to 89. The lead is
   entirely `partial` turning to `covered`: the lens arm decides more of what both specifications reach.
2. **Deciding more is not the same as specifying better, and the judge could not tell them apart.** Where the
   released stage is `partial` it has often made a decision its own duties ask for: leave a bound unresolved
   (duty 6: invent no bound), add no persistence the request does not need (duty 9), declare production out of
   scope for a development org. The judge prompt said nothing about a stated exclusion or an open item, and scored
   them unevenly: "the spec decides not to persist conversations" is `partial` for one arm, "the bot has no
   bot-managed conversation or result history" is `covered` for another, on the same nuance. A specification that
   decides more scores higher whether or not deciding was right.
3. **The checklist leans the same way as the lenses.** Both were written by this session. Freezing the checklist
   stopped it being edited after the fact; it did not stop it rewarding the edges, operator controls and
   production conditions that its author then wrote into the lenses. Grokbot's N-24 asks for production
   deployment conditions of a request that says development org.
4. **"No added scope" was wrong in count** on Sol, and unmeasured against the released stage (section 12's note).
5. **Several causes were asserted that the data cannot isolate**: iteration as the source of scope, the leaked
   skill as the cause of the single pass's fall on Sol, the guard as helping on Sol.
6. **The isolation claims were stronger than the scan** (section 10's note), and the decision threshold of 12 was
   described as a noise floor (section 8's note).

### What it found in the draft

The block's faults are of one kind: it turns aids to thinking into things to write.
- "What a line turns up **becomes** a requirement, or an acceptance line" is an output mandate, and "add no
  feature" still lets a session add restrictions, controls and test obligations. Every acceptance line is work
  downstream: `test-strategy` plans a check for it and `plan` maps it to a work item.
- "In one pass", "before you write them" and "each requirement you have written" contradict one another, and
  "follow each answer down until it is a fact about the world" has no stop. A session can read it as a
  preparation step or as an inquiry that delays the stage; "one pass" can also be read as waiving duty 10's
  checks.
- The runtime lens asks for what the thing "requires before it ... ships beyond a development environment", which
  can draw a production contract out of a development request, and "with its number" can draw a guessed number
  with a citation added after.
- "Each use, piece of state, outside system and existing feature against the others" invites the cross-product
  the stage's own guide warns against.
- "The fields a record holds" and "lists its members" invite a schema inventory, which duty 3 and plan duty 7
  put in the architecture record.
- "Records it as unresolved (item 6)" sends a behaviour's open bound to the non-functional section; duty 4 owns
  open items under their requirement.
It gives a replacement for each, all of which do the same thing: tie the question to the affected outcome, and
record under duty 4 instead of adding. It agrees that duty 2 is the place for a compact cue.

Two faults it found that are not this experiment's and are worth the owner's knowing:
- `skills/shiploop/references/behavioral-requirements.md` still tells the spec stage to "store the proposed
  product behavior in the result `body`", while the stage's duties write it to `KNOWLEDGE/spec.md`.
- `run.py` here skips a kept specification without checking its provenance, and `grade.py` can publish an
  incomplete verdict set (the saved rounds were complete).

### Where that leaves the experiment's conclusions

| claim | status after the review |
| --- | --- |
| Against the ratchet pilot's single pass, the lens arms cover far more (D over A: +29 Sonnet, +35 clean Sol) | established on these four cases; on Sonnet under two judges |
| The one-pass package costs about half the iterating one, which shows no coverage advantage | established as a comparison of two packages |
| The released stage, run alone, reaches as many of these nuances as any lens arm (87 of 89) | established, and the most useful thing this experiment found about ShipLoop |
| The lenses add to the released stage | **not shown**; the +19 on Sol is decidedness on a judge that scores exclusions unevenly |
| The one-pass form adds no scope | **withdrawn**; lower share, higher count on Sol, and nothing against the released stage |
| Iterating is what adds scope; the leak lifted the single pass; the guard helps on Sol | **not isolated** |
| The draft block should be put to the owner | **no**, not as written |

So of the plan's three outcomes it is the first that the evidence supports: **no fold-back into the released
stage on this evidence.** That is not the same as "the lenses are worthless". Against the text the ratchet pilot
uses they move a great deal, and the owner decided in section 6 that this experiment's target is the released
stage and not that one. And it is not "the released stage is as elaborate as the owner wants": it reaches the
nuances and, by its own rules, leaves many of them open or out; whether a specification should decide more of
what it reaches is a question about what ShipLoop is for, which no checklist of this session's settles.

Round 6 (the block as drafted, inside the stage text, against the stage text) was already running when the review
came back and is left to finish: both of its arms share one layout and one policy, so the uneven scoring of
exclusions bears on them alike, and it will say whether the block moves the stage at all. By the review's own
terms a block rewritten to meet its findings would need its own paired check, so round 6 cannot rescue the draft;
it can only say how much there was to rescue.

## 15. Round 6: the draft inside the stage moves it a little, in two categories, and not enough (2026-11-21)

16 sessions (the draft Q and a second draw of the released stage P, both drivers), all exit 0 after a passing
pre-flight; the leak check found none that read outside or named the held-out material.
`evidence/round-6/readings.txt`.

| | Sonnet high | Sol medium |
| --- | --- | --- |
| P, first draw (round 5) | 58 | 43 |
| P, second draw (round 6) | 60 | 43 |
| **Q, the draft** | **68** | **48** |
| Q minus the mean of P's two draws (R15) | **+9: interim** | **+5: nothing shown** |
| Q minus P in the same round | +8 | +5 |
| cases where Q is above P / below P | 3 / 0 | 2 / 1 |
| minutes a case, P to Q | 6.6 to 5.2 | 4.8 to 4.8 |
| R-n requirements a specification, P to Q | 11.5 to 16.5 | 4.0 to 5.2 |

**R15: not shown on Sol, interim on Sonnet.** Neither driver reaches the threshold of 12 fixed before the round.
By the stricter test the review proposed (both judges, 12 or more on a driver against both the mean and the same
round, gains on several cases after scope and sources are checked) it is further off still.

**What the block does do, consistently:** on both drivers its gains sit in the two things its first lens names
that the released stage's duties do not: the people who run it (operator 3 to 6 on Sonnet, 1 to 3 on Sol) and the
unhappy paths (8 to 11, 7 to 10). Everything else moves by one either way. That is a small, located effect and it
is the one thing in this experiment that points at the released stage's text and not at the instrument.

> **Superseded 2026-11-21** (the saved specifications read item by item; section 19): the gain on the operator
> items does not point at something the released stage's text misses. In all eight of the block's specifications
> it is a requirement for the operator's own controls (a staff roster with a Remove action, a global and a
> per-class switch, an operations surface to pause and roll back) that the released stage leaves out, in places
> saying so. By the owner's rule of 2026-09-27 that is product capability the request did not ask for. On the
> unhappy paths the released stage leaves no item untouched in either draw on Sonnet, and of the block's eight
> gains there on the two categories together, three are the same handling scored differently and two are items
> the released stage covered in its other draw.

**What it costs:** not time or tokens (Sonnet's Q sessions were shorter than its P sessions; Sol's the same), but
obligations: Sonnet's specifications go from 11.5 requirements to 16.5, and each is a check to plan and work to
map in the stages after. Whether those five are wanted is exactly what the review said this experiment had not
measured, and it still has not.

**The lenses lose their standalone lead when set inside the stage.** On Sol, L alone scored 62; the same lenses
inside the stage text score 48. The 14 between them is not lens content, since the content is the same: it is the
stage's own duties telling the session to leave open and leave out what L, with no such duties, decided. That
settles what R14 measured, in the review's favour: two documents with two policies, not a stage with and without
an addition.

> **Superseded 2026-11-21** (the second judge on the same specifications; section 16): "settles" is too strong,
> and the 14 is one judge's. Under gpt-6.2-astra L alone is 45 on Sol and the lenses inside the stage 42, a gap of
> 3. The 62 that Opus gave L on Sol is the largest disagreement between the two judges on any cell (17). What
> both judges agree on is narrower: L over P on Sol is +19 and +14, and the draft over P is +5 and +11.

**The released stage is steady.** Its two draws are 58 and 60 on Sonnet and 43 and 43 on Sol, the same four
per-case numbers both times on Sol.

### Conclusion

Of the three outcomes registered in section 6, the first: **no fold-back into the released `spec` stage on this
evidence.** The draft is not put to the owner: the independent review found its wording would turn aids to
thinking into obligations, and its measured effect inside the stage is interim on one driver and not shown on the
other. Nothing under `skills/` was changed at any point.

What the experiment leaves, in order of how firmly it stands:
1. **The released stage, run alone, already reaches nearly every nuance on the checklist** (87 of 89 on both
   drivers, 83 to 87 across four draws), a checklist written by someone trying to find what it would miss.
2. **Against the ratchet pilot's single-pass enrich text the lens arms cover far more**, on two drivers and, on
   Sonnet, under two judges. That text is another session's.
3. **A one-pass form costs about half an iterating one and shows no loss of coverage.**
4. **The released stage is weakest on the operator's work and on unhappy paths, and a cue naming them moves both
   a little on both drivers.** Interim. If the owner wants that pursued it is a two-sentence cue tied to the
   affected outcome, as the review words it, with its own paired check and an E2E round, not this block.
   > **Superseded 2026-11-21** (section 19): the stage is not weak there in the sense this finding meant. It
   > reaches those items and mostly leaves them out or open on purpose; the cue's movement on the operator's work
   > was added capability. The cue named here is not run. A different two-sentence cue (a set's members, a
   > limit's bound) is registered in its place for rounds 7 and 8.
5. **The instrument**: four frozen requests, an 89-item checklist, a coverage judge calibrated on two layouts and
   re-read by a second family, a clause audit, a pre-flight that proves what a Codex session is shown, and a leak
   check. Its known faults are recorded where they were found: the judge scores a stated exclusion or an open
   item unevenly, so `covered` rewards deciding; the checklist and the lenses share an author; a subject can
   still reach a judge's folder.

Open and the owner's:
- Whether a specification should decide more of what it reaches. The request that started this asked for a
  verbose, elaborated specification; the released stage's duties tell it to leave some things open and out. The
  lens arms without those duties wrote what the request described. That is a choice about what the stage is for.
  > **Answered in part 2026-11-21** (section 19): the owner's rule of 2026-09-27 (commit
  > e18cbce9ec577a61a8cdea353c6794804b09f1d9) already says which way for the part that mattered here: rigour is
  > to be settled even for a small request, and capability the request did not ask for is not to be added.
- Whether finding 4 is worth a second, smaller attempt.
- Whether finding 2 goes to the ratchet pilot's session.
- The E2E harness's Codex sessions being shown the user's own skills (section 7), put up as its own task.
- The stale sentence in `skills/shiploop/references/behavioral-requirements.md` (section 14).

## 16. The second judge on the deciding rounds (2026-11-21)

gpt-6.2-astra at high, calibrated in section 12, read rounds 5, 6 and 4c beside the registered verdicts
(`grades/round-5@gpt/`, `round-6@gpt/`, `round-4c@gpt/`; `evidence/round-6/two-judges.txt`). It is stricter
throughout and agrees with Opus on covered-or-not for 84 to 87% of nuance verdicts.

| comparison (covered of 89) | Sonnet: Opus / astra | Sol: Opus / astra |
| --- | --- | --- |
| D over A, the iterating lenses over the ratchet pilot's single pass | +31 / +26 | +35 / +31 |
| L over A, the one-pass lenses over it | +24 / +22 | +33 / +21 |
| F over L, iterating over one pass (R9) | +4 / 0 | -2 / +4 |
| L over P, the lenses alone over the released stage alone (R14) | +6 / -1 | +19 / +14 |
| **Q over the mean of P's two draws, the draft inside the stage (R15)** | **+9 / +7.5** | **+5 / +11** |
| Q over P in the same round | +8 / +9 | +5 / +11 |

- **What holds under both judges.** The lens arms over the ratchet pilot's single pass, by a wide margin on both
  drivers, one pass or iterating. One pass against iterating: no difference under either. These two are the
  experiment's firm results.
- **The draft against the released stage is positive in all four cells and reaches 12 in none.** +5 to +11
  against the mean, +5 to +11 in the same round. Interim under both judges, and the review's stricter test (12 or
  more under both judges on a driver) is not met. The conclusion of section 15 stands.
- **Touched, under both judges:** the released stage 80 to 87 of 89, the lens arm alone 84 to 89, the draft 86 to
  89, the ratchet pilot's single pass 71 to 82. That the released stage already reaches nearly everything on this
  checklist does not depend on the judge.
- **One cell is the judges' largest disagreement and a claim rested on it.** Opus gave L 62 on Sol; astra gave it
  45. Section 15's "the lenses lose their standalone lead inside the stage" used the 62 (note there).

Status of the experiment: concluded, with what is the owner's listed at the end of section 15.

## 17. Sent, published, and two things learned on the way out (2026-11-21)

**The owner's words:** "Yes, send it and publish", in answer to "should I send the lens result to the ratchet
pilot's session, where it does apply?".

### Sent

The result that holds (the lens arms over the ratchet pilot's single-pass enrich text, under two judges, with its
cautions) went to the session that owns the pilot as a cross-session message. Nothing was asked of it and nothing of
its was touched. Its reply, received and not verified here:
- It recorded the result in `docs/ratchet-pilot-journal.md` section 19 with the cautions.
- Its own reading, which bears on section 14 from the other side: this experiment's measure rewards deciding more,
  and the pilot's built products show that decided clauses are where correct products were rejected and where one
  product was made to fail held-out checks. That is the review's finding 6 seen through a built product: what this
  instrument scored as coverage is, in part, what the pilot's instrument scored as harm. Neither measurement was
  designed to test the other; they point the same way.
- It agrees from its side that iterating gained nothing over one pass.
- On the Codex skills fact of section 7: across its 769 session event files the only mention of a user-level skill
  path is one process listing it had already audited.

### A known load on the minutes

The same reply reports that ten stray test processes from an interrupted script of that session ran at full CPU
from about 22:00 to 02:02 on 2026-11-20 and 21. Rounds 4c, 5 and 6, the judge checks and the audits of this
experiment all ran inside that window; rounds 1 to 3 and round 4's subject calls ran before it.

> **Superseded 2026-11-21:** every statement in sections 10, 11 and 15 that compares *minutes* between a round
> before the window and one inside it. On Sonnet, A and D were timed in round 4 (before) and L, F, P and Q in rounds
> 5 and 6 (inside), so "the released stage run alone costs about what the recursive arms cost" and the Sonnet minutes
> column of section 11 are not comparisons of like with like. What is unaffected: output tokens (Sonnet, a case:
> A 15,317; L 21,484; P 43,342; F 43,379; D 57,787), and comparisons inside one round, which is what the registered
> cost readings used (R9, L against F in round 5: 52% and 54% of the minutes, 50% and 56% of the tokens; R15, Q
> against P in round 6). On tokens the released stage costs what the iterating guarded arm costs and twice what
> the one-pass arm costs.

### Published

- **Scope, the owner's choice.** Thirteen commits of this experiment were unpushed, and three docs-only commits of
  the session running the SDLC-structure study sat between them on the shared local `main`. Asked, the owner chose
  to publish through this experiment's last commit: the thirteen and those three, leaving that session's two newest
  commits for it to push.
- **The remote moved three times while the range was being checked**, each time by the Ratchet session publishing
  its pilot at the owner's word in that session: its merge, then journal and evidence commits. The first guarded
  attempt stopped on its own pre-check and the second was refused by the guard; nothing was pushed either time.
- **A merge, not a rebase**, because this range's commits cite one another by full hash. The merges were made in a
  temporary detached worktree at this experiment's last commit, so the shared checkout was never touched.
- **Checks.** The quick tier, pinned to the base, passed twice: 13 suites on the range alone and 13 on the range
  merged with the remote. The candidate finally pushed differed from that tested tree only in files of the Ratchet
  pilot that the remote had added since, so the tier was not run a third time. The guard then ran its three checks
  (marketplace packages, the release boundary against the base, the test catalogue) and pushed the frozen commit
  without force.
- **No release and no host refresh**: no file under `skills/` or `agents/` changed, and no change note is pending.
- **Left as it is, and said so:** the shared checkout's local `main` is two commits ahead of origin (the other
  session's) and behind it by the merge. It cannot be fast-forwarded and is that session's to reconcile; it was
  told how.

> **Superseded 2026-11-21, minutes later:** "it was told how" was written, and pushed, before the message was sent.
> When it was sent, that session held it: its Claude has not seen it (the usual cause is that the two sessions run
> in different permission modes). As of this note the session whose commits sit on the shared local `main` has not
> been told, and the owner has been, with what the message says: fetch, then merge origin/main into local main, a
> merge and not a rebase if its commits are cited by hash; no conflict is expected. An action is recorded after it
> has happened and been seen to have happened, not before.

> **Seen, 2026-11-21 03:24:** the owner pointed that session at the update in its own conversation, and it
> reconciled. It merged origin/main into the shared checkout's local `main` (f6705923b41c0d8cf05bf4d4f777f13ac89c39d1), a merge and
> not a rebase, with no conflict, and its commit message says the held message never reached it and names what
> the message asked. The first message expired unapproved. A second, sent at the owner's word ("Update the SDLC
> session") through the app's own session route, was reported by the app as not confirmed. So what is seen is that
> the session has the facts and has acted on them, not which channel carried them. The shared checkout is no longer
> behind origin; it is ahead by that session's two commits and its merge, which are its to push.

### The owner's to-do

"Add todo: did we update the prompt templates for Shiploop to improve them?" (2026-11-21). **Not as of this
entry.** Nothing under `skills/shiploop/` was changed by this experiment; the last change to the stage prompt text
is still the fewest-steps commit of ShipLoop 2.4.0. It is open, not decided against. What is on record as a
candidate, and what each would need, is the list at the end of section 15: a short cue in duty 2 naming the people
who run the thing and its unhappy paths (interim evidence; the review's rewording, its own paired check, an E2E
round and the owner's go); the stale sentence in `references/behavioral-requirements.md`; and, under both, whether
the stage should decide more of what it reaches.

> **Updated 2026-11-21** (section 19): still not. The candidate named here, a cue for the people who run the thing
> and its unhappy paths, is withdrawn: read item by item, its measured lift on the operator's work was capability
> the request did not ask for, which the owner's rule of 2026-09-27 calls overbuilding. A different two-sentence
> cue (name a set's members; state a limit's bound) is registered for rounds 7 and 8 against the released stage.
> The to-do stays open until that result is in.

## 18. The lens form goes to a built-product test in the pilot's session, and a reworded arm is drafted for it (2026-11-21)

**Received from the Ratchet session, at the owner's word there** ("We should pick up the elaboration message from the
other chat about a new elaboration of a spec prompt"; "Should you inform Spec elaboration chat about your
findings?"). Recorded as received; two things were read here and found as described, the registration commit and
the port's diff.
- It ported `arms/L-lenses-once.md` into the pilot's enrich stage as a second enrichment text
  (`SPEC_PACKET_LENSES`, flag `--enrich lenses`), keeping that stage's frame and file path, its
  repository-reading step and its `existing` source kind, since its cases have repositories. Registered before
  any run as its amendment 7 (commit 43d5486168448f221763d9413f7ea02878f6d237, branch `ratchet-lens-08805f`).
- Five runs started at 03:22 on Codex gpt-6.2-sol at high: three test-strength cells (enrich with the lens text,
  plan, the correct reference laid in as the build, a test pass by another session, then the frozen suite run
  against the correct reference, a second correct delivery and 37 calibrated defects) and two runs of one case's
  loop to its first test pass, graded with held-out checks.
- Its registered readings are the half this experiment could not reach: whether the lens form avoids a reading of
  one sentence that made two of two earlier builds fail 5 of 8 held-out checks with their own tests green (R8.1);
  the share of clauses whose test fails on a correct product, 11.8% with the pilot's own text (R8.2); calibrated
  defects caught, 37 of 37 before (R8.3); clauses, minutes and tokens (R8.4).
- It says of its own design what should be said here too: this is "deciding more" tested for rightness, one case
  family and one run a cell, so it will give a direction and not a size.

**What this is for this journal.** Sections 14 and 17 ended on a question neither instrument had answered alone:
is what the coverage judge scores as coverage, in part, what a built product scores as harm? The pilot's session is
now running the arm of this experiment through its instrument. Its result, when it comes, is that session's to
report and is recorded here as received.

**A reworded arm, drafted and not run: `arms/R-lenses-reworded.md`.** The pilot's session offered to measure a lens
block reworded to meet the review's findings as a third enrichment text, and said it would put it to the owner
before running. The arm it is running is the one the review faulted, so a reworded one is worth having beside it.
`R-lenses-reworded` is `L-lenses-once` with these changes, each from a finding of section 14's review:

| change | the review's finding |
| --- | --- |
| The lenses are "aids to thinking, to be used once while you draft; they are not a list of things to write". Nothing says an answer becomes a clause. | 2: "becomes" turned an aid into an output mandate |
| "What earns a clause": the request's sentences, then only distinct checkable behaviour the requested outcome needs or that must be preserved where the change touches it. The test for leaving one out is the audit's own: a builder could omit it with nothing missing. | 2, 5 |
| An `Open:` line under a clause, and a rule for it: where the answer would change what the requester gets, write the loosest reading certainly wanted and record what is undecided and who decides. "An open line is a finished piece of work." | 2, 3, 4: record open items instead of settling them |
| "Invent no bound": a value comes from the request, from what exists or from the runtime's documentation, or the bound is an `Open:` line. The earlier "state your own decided value" is gone. | 4 |
| A prerequisite is named "only if its absence or its failure would change that outcome or how it is checked", and followed no further. The recursion sentence is gone. | 3: no stop, and "one pass" contradicted itself |
| The runtime lens is "for the environment the request names, and no further". | 4: a production contract drawn from a development request |
| "Where paths share something" replaces "each ... against the others". | 9: an invitation to the cross-product |
| Sets name "the members or groups that behave differently"; "the fields a record holds" is gone. | 11: a schema inventory |
| The operator's work is in only "where running it or recovering from it is part of what was asked", and "using the controls that already exist". | 8 |
| One check after drafting, which ends on "a clause that a builder could leave out with nothing missing, which should go". | 3: "one pass" must not waive the final check |

It is 1,002 words against 1,219. **No model call has been made with it, here or anywhere**, and nothing is claimed
for it. Two things a reader of any later result has to know:
- **It was drafted after this session had read the pilot session's description of R8.1**, the sentence and how two
  builds misread it. The arm was written from the review's findings, which predate that message, and no sentence
  was added for that case; but the session that wrote it knew the case, so R8.1 is not a blind test of this text
  in the way it is of `L-lenses-once`.
- The `Open:` line is a new line in the specification's form. A stage that reads the specification has to know
  that an open line is not something to build or to write a test from.

**Sent to the pilot's session, with predictions stated before any run of it.** The location of the arm, the list
of changes and the two cautions above went to the Ratchet session, which had offered to put a reworded block to the
owner as a third enrichment text. Three predictions were stated to it so that they are on record first, with no
measurement behind any of them: against `L-lenses-once` on the same case the reworded arm writes fewer clauses,
gets a lower share of clauses whose test fails on a correct product, and loses none of the calibrated defects
caught. Whether it is run is the owner's.

## 19. The smaller attempt is re-aimed before it runs: the lift on operator items was capability nobody asked for (2026-11-21)

The owner said yes on 2026-11-21 to the smaller attempt section 15 left open (its finding 4): a two-sentence cue in
duty 2 naming the people who run the thing and its unhappy paths, with its own paired check. This section records
what was read before that check was designed, the three decisions the reading led to, and the check now registered
in its place. No model was called for any of it; everything below comes from verdicts and specifications already
saved.

### What was read

**The released stage leaves almost none of those items untouched.** The checklist has 21 operator and unhappy-path
items (9 and 12). Covered / partial / absent for the released stage P, under the registered judge and then the
second:

| | Sonnet, round 5 | Sonnet, round 6 | Sol, round 5 | Sol, round 6 |
| --- | --- | --- | --- | --- |
| P, claude-opus-5-5 | 11 / 9 / 1 | 11 / 9 / 1 | 11 / 10 / 0 | 8 / 10 / 3 |
| P, gpt-6.2-astra | 12 / 7 / 2 | 10 / 9 / 2 | 7 / 13 / 1 | 6 / 12 / 3 |
| Q (the earlier block), opus | | 17 / 4 / 0 | | 13 / 8 / 0 |
| Q, astra | | 15 / 6 / 0 | | 12 / 9 / 0 |

A cue can find at most the 0 to 3 a draw leaves absent, and P's own two draws on Sol differ by 3 there. The room
is in the partial column, so the question is what a partial is. Status: firm (four draws, two judges).

**Read in the specifications, a partial on these items is mostly a choice.** Sonnet's round-6 specifications, the
ten items of the 21 not scored covered: the staff view of the waitlist is under "Exclusions (domain rules the
request leaves out, bounding this R)" with a gap asking whether staff need a count; a persistent audit of who asked
the bot what is a "Justified exclusion" with a gap to reopen it; payments at promotion are excluded with "any
existing rule of these kinds still applies"; several billing contacts are folded into an open gap; a per-customer
opt-out is "Left out"; hostile spreadsheet content is stored verbatim with its neutralizing excluded and the
length limit an open gap; cancelling an import is answered by the import being all-or-nothing. Two are mentions
that settle less than the item asks, and one (a switch to turn the waitlist off) is absent. That is the stage
doing what its duties 4 and 9 tell it to. My reading of ten verdicts and the passages they cite; interim.

**The earlier block's gain on these items, item by item** (`evidence/round-6/operator-unhappy-item-by-item.md`;
round 6, Q against P in the same round, with P's round-5 state beside it):

| | Sonnet | Sol |
| --- | --- | --- |
| items Q covers and P does not, registered judge | 8 (and 2 the other way) | 5 (0) |
| the same, second judge | 5 (0) | 6 (0) |
| of the registered judge's: a control or view for the operator that P does not require | 3 | 2 |
| the same handling in both, scored differently | 3 | 0 |
| P covered it in its other draw | 2 | 2 |
| an unhappy path settled that P left open or did not reach | 0 | 1 |

The three on Sonnet: an enable checkbox and a log line per failed request for the bot; a staff roster of the
queue with a Remove action and an event log of who was promoted when; a global waitlist switch with a per-class
override. The two on Sol: starting the bot disabled with a stop for all users, diagnosis by category and a
restore procedure; pausing waitlisting globally or for one occurrence "through an approved operations surface".
The three scored differently are an exclusion in both arms: "Out of scope ... several recipient addresses per
invoice" was scored covered where "Folded into G-1 ... One recipient address per invoice" was scored partial, and
"Not cancellable in this version" covered where "there is no cancel, resume, update or delete event on a committed
import (out of scope)" was partial. The classification is my reading; the passages are quoted in the evidence
file. Interim.

**The titles say the same thing without a judge** (`evidence/round-6/requirement-titles.txt`). Every one of the
block's eight specifications carries a requirement for the operator's own controls: "Operator controls: turn on,
turn off, know it worked", "Audit and observability" and "rollout and rollback" (waitlist, Sonnet); "Operate, pause
and recover waitlisting" (waitlist, Sol); "Turning reminders off, everywhere or for one account" and "Pausing one
invoice" (reminders, Sonnet); "Control automatic reminders" and "Inspect outcomes, contain failures and roll back"
(reminders, Sol); "Administrator configuration and turn-off" and "Operability: enable, observe, undo" (bot,
Sonnet); "Configure, restrict, diagnose and recover the bot" (bot, Sol); "Operator controls" (import, Sonnet);
"Stop further writes and recover operationally" (import, Sol). The released stage's sixteen specifications are in
the same file. They are not empty on the operator's side: the reminder feature's own account switch and its
history (Sonnet, both draws), administrator settings for the bot (Sonnet, both draws), outcome logging or audit
in several, and in one draw a staff view of the waitlist "conditional on G-4". The block's specifications name
where theirs came from: the waitlist's operator requirement gives as its basis the lens "turning it on and
knowing it worked ... turning it off for everyone or for one case ... going back to the version before", adding
"(a run-it reading of a user-facing feature; inside the request's intent, adds no user feature)". Status: the
titles are verbatim; that the block is their cause rests on those basis lines and on one draw a cell.

**The released stage does not hold one line on this either.** Its round-5 waitlist specification on Sonnet has a
requirement "Staff view and management (conditional on G-4)"; its round-6 one excludes the staff view. The stage's
text says nothing about the operator's side, and its draws go both ways.

**Where it does fall short in both draws** (`labels/stable-shortfalls.txt`). On Sonnet P covered 53 items in both
draws, 12 in one of the two and 24 in neither; on Sol 39, 8 and 42; 18 items are covered in neither draw on both
drivers. The earlier block covered 14 of Sonnet's 24 (13 under the second judge) and 7 of Sol's 42 (7), and left
uncovered 6 items P had covered both times on Sonnet (2 on Sol). Among the 24 are items that are not capability
by any reading: the platform's limits named with their numbers, every condition that stops a reminder sequence,
the retry policy and who is told when sending keeps failing, the initial state of a created user, one person
waiting for two overlapping classes. Each of those five is partial in both draws on both drivers under both
judges. Interim: two draws a driver, and a partial is not yet separated into an open item recorded on purpose and
a mention that settles nothing.

### Three decisions, and why

All three are mine to make under AGENTS.md's Decisions (choosing between equivalent ways to do approved work, and
launching verification runs); none changes anything ShipLoop does.

1. **The cue as first described is not run.** Its operator half asks for what the owner's rule calls
   overbuilding. The rule is on record from 2026-09-27, in commit e18cbce9ec577a61a8cdea353c6794804b09f1d9:
   "Engineering rigour in a plan (tests against the real runtime, correct deployment steps, quotas, failure routing
   and ownership, data retention, security checks, marked assumptions) is the expected standard even for a small
   request; only product capability the request does not need (features, stores, services, sign-in, user-facing
   channels) is overbuilding." That commit met the same thing in plan reviews, which added "draw offers,
   resignation and draw adjudication" to a two-person checkers game. Its unhappy-path half has nothing to find: the
   stage's duty 2 already asks for failure and boundary expectations on every acceptance line, and on Sonnet no
   unhappy-path item is untouched in either draw. A version worded to respect the stage's rules (unsettled things
   to open gaps, no new capability) would restate duties 2, 4, 7 and 9. That last sentence is an inference; it was
   not measured.
2. **The owner is not asked again whether the stage should decide more.** Section 15 left that open as "a choice
   about what the stage is for". The rule above already answers the part that bears on this cue: settle what
   rigour requires, add no capability the request did not ask for. What stays open is narrower and is in the list
   at the end of this section.
3. **The check is re-aimed at what the reading found, and registered** (README, "The smaller attempt: re-aimed
   before it ran"). Arm `M-shiploop-spec-members` adds two sentences to duty 2: name the members of a set an
   acceptance line depends on, and state the bound an acceptance line depends on with the behaviour at it,
   recording an unresolved one where duties 4 and 6 put it. The words are the independent review's own replacement
   for the last two sentences of the earlier block (its findings 11 and 4). The earlier arms carried the same idea
   as "the enumeration rule" (arms C, D and F); round 3 found it carried their gain, and section 14's review found
   their wording invited schema inventories and invented numbers.

### How the check differs from round 6's

Round 6 read the block by the whole checklist's covered count, and the review said that count rewards deciding.
This check reads it by sets fixed beforehand by two sorters who are not the author: claude-opus-5-5 and
gpt-6.2-astra label each of the 89 items by kind (a set's members, a limit, neither) and by scope (needed, beyond,
mixed, under the owner's rule quoted above), shown the requests and the items and nothing else. The target is the
set-or-limit items not agreed beyond; the items agreed beyond are read separately, and a gain there counts against
the cue. Bands come from the four clean repeat pairs on record. Rounds 7 and 8 pair M with a fresh P each. The
tests, the decision rule and the one permitted extension are in the README.

A third sentence was considered and left out: for an outcome that runs unattended, who is told and what record
exists when it keeps failing. The owner's rule names "failure routing and ownership" as rigour, and one checklist
item on exactly that stands unsettled in both draws on both drivers. One item is not a case for a sentence. It is
noted here and not run.

### What this changes in earlier sections

- Section 15, "What the block does do, consistently" and its finding 4: superseded there, with the reason.
- Section 15's first open question and section 17's to-do entry: updated there.
- Section 18's reworded arm R is unaffected: it is another session's to run, and its first line of thought still
  names "the operator's work". If that session measures it through built products, the three operator
  requirements above are what to look for in what gets built.

  > **Superseded 2026-11-21, 04:47** (reading arm R again while recording section 21): wrong about R. The
  > unconditional line, "the operator's work (start, stop, configure, observe, recover, ...)", is arm L's, which is
  > the text the pilot's session ran. R already carries the review's rewording: "Where running it or recovering
  > from it is part of what was asked, state how the person who runs it observes it, stops it or recovers it, using
  > the controls that already exist." The advice stands for L and for the earlier block, not for R.

Still open and the owner's: the E2E harness's Codex sessions being shown the user's own skills (section 7); the
stale sentence in `skills/shiploop/references/behavioral-requirements.md` (section 14); and, if rounds 7 and 8
show the cue, whether it goes into duty 2.

## 20. The items are sorted by two models that are not the author; a second wording is added before round 7 (2026-11-21)

Two sessions (claude-opus-5-5 and gpt-6.2-astra, both high) each labelled all 89 items, shown the four requests
and the items and nothing else: no specification, arm or verdict. 89 of 89 from each, none missing, none with an
unknown label. `labels/opus.json`, `labels/astra.json`; prompt in `label.py`. These are the only model calls made
for the check so far.

### What the sorters say

| | same label from both | |
| --- | --- | --- |
| `scope` | 82 of 89 | 74 needed by both, 4 beyond by both, 4 mixed by both |
| `kind` | 74 of 89 | 22 a set or a limit by both (13 limits, 7 sets, 2 both); astra calls 37 one, opus 22 |

**Only four of the 89 items are capability nobody asked for, by both sorters**, all four in the operator category:
a staff view of the waitlist with manual promote and remove; a switch to turn the waitlist off or on per class;
turning reminders off per customer with a preview and a manual resend; cancelling a running import and retrying
failed rows. Of the other five operator items, two are mixed by both and the reasons given are the owner's rule
applied without being asked to quote it ("Seeing failed requests is failure routing (needed); the off switch and
model switching are admin controls (beyond)"), one is needed by both (how a development org differs from
production and how the work is deployed), and they split on two (an audit record).

That corrects section 19 in one direction and confirms it in another. The checklist as a whole is not a list of
optional extras: 74 of its 89 items are needed by both sorters. And the items section 19 picked out by reading
specifications as added controls are the ones two outside sorters picked out from the item text alone.

### The sets and their bands

X1, the target: 22 items both call a set or a limit and neither calls beyond. X2, 53 other items both call
needed. X3, the 4 agreed beyond. Bands from the four clean repeat pairs (`labels/bands.txt`): X1 2 (the repeats
moved it by 0, -1, +1, 0), X2 7 (-7, 0, 0, +1), X3 2 (+1, -2, 0, 0), all 89 items 6. X1's band is the floor of 2
and not a measured maximum; with repeat moves that small, a mean of 2 over two rounds with both rounds above zero
under both judges is a stricter test than the largest move seen.

### Saved rounds read by the sets

Descriptive: these rounds were run and read before the sets existed, so nothing here is a registered reading.
`label.py split`. Covered, registered judge / second judge.

| | X1 (22), Sonnet | X1, Sol | X3 (4), Sonnet | X3, Sol |
| --- | --- | --- | --- | --- |
| P, the released stage, rounds 5 and 6 | 14, 14 / 13, 14 | 6, 7 / 4, 6 | 0, 0 / 0, 0 | 1, 1 / 0, 0 |
| Q, the earlier block inside the stage | 17 / 15 | 7 / 8 | 3 / 2 | 2 / 1 |
| L, the lenses alone, one pass | 15 / 13 | 15 / 13 | 0 / 0 | 1 / 1 |
| F, the lenses alone, iterating | 18 / 16 | 16 / 15 | 1 / 2 | 2 / 1 |

Three things, each one draw a cell except P:

1. **The earlier block's added capability is now counted by people who are not me.** On the four items two
   sorters call beyond, the block took Sonnet from 0 to 3 (2 under the second judge) and Sol from 1 to 2 (0 to 1).
   On Sonnet that is as large as its gain on the 22 target items (+3, and +1 or +2 under the second judge).
2. **Sol inside the released stage leaves sets and limits unsettled, and that is the largest gap on this
   checklist.** 6 or 7 of 22 inside the stage; 15 or 16 from the same model with the lenses alone. Sonnet shows no
   such gap (14 against 15 to 18).
3. **Putting the rule inside the stage did not close it.** Item by item, Sol inside the stage leaves 13 of X1's 15
   limits uncovered in both draws, and 12 of those 13 with the earlier block as well. The block's last sentence
   let a limit be "recorded as unresolved", and leaving a limit to someone else is the route Sol takes inside the
   stage with the block or without it (its released-stage specification for the import: "Runtime owner sets and
   verifies byte, record and field limits").

### The amendment

Arm M's second sentence, taken from the review, ends the same way: "record an unresolved behaviour bound as an open
gap". Point 3 predicts it will not move Sol. The stage's own text pulls two ways on this. Duty 4 says to mark a
user decision as an open gap; the RULES say "Unattended: take the best default and record it as an assumption; a
person-only step is an open item", which is the owner's rule for unattended runs (2026-09-27), and duty 9 says the
same for an open choice. Sonnet mostly follows the second and Sol the first.

So a second cue arm is registered before anything runs: `K-shiploop-spec-default-bounds`, M with its second
sentence changed in one thing. A limit the request leaves to choice is stated as the best default and recorded as
an assumption; a platform limit is stated from its source; "a non-functional bound stays as item 6 has it". Rounds
7 and 8 run M, K and P: 48 sessions. Each cue arm is read against the P of its round by the readings already
registered. Added: for the four non-functional bounds in X1, any a cue arm covers and P does not is quoted and
read, because the stage says "Invent no bound" and a bound with no basis is a defect; and if both arms are shown,
the one with the larger X1 mean under the registered judge is the candidate, M on a tie. README, "Amended before
round 7".

Decision, routine (launching a verification run; choosing between two ways to word approved work): the second arm
costs half as much again and answers the question a null from M alone would leave. What K cannot show is whether
its defaults are good ones; this instrument reads a specification and builds nothing.

Predictions, written before any subject call so they can be held against the result: M moves Sol's X1 by less than
2 and Sonnet's by 1 to 3; K moves Sol's X1 by 4 or more; neither moves X3.

## 21. Received: the pilot's session graded the lens form through built products (2026-11-21, 04:47)

Recorded as received, while rounds 7 and 8 were running. The work, the instruments and the findings are the
Ratchet session's; its record is section 20 of `docs/ratchet-pilot-journal.md` and
`docs/experiments/ratchet-pilot-20261120/evidence/lens-enrichment/`, in commit
58cf265fb3c3a78930f423adc4e701d91483adc4 on its branch `ratchet-lens-08805f`, not on `main` when this was written.
I read that section in the commit and the figures below match it; I did not re-run or re-grade anything.

What it ran: arm L of this experiment (`arms/L-lenses-once.md`) set into its pilot's enrich stage, on Codex
gpt-6.2-sol at high, one run a cell (two for the loop), three Node.js cases that have a repository, against the same
cells run with the pilot's own enrichment text the evening before.

| its reading | lens form | the pilot's own text | its verdict |
| --- | --- | --- | --- |
| clauses whose test fails on a correct product | 47 of 426 (11.0%) | 59 of 499 (11.8%) | no difference shown (bars 7.9% and 15.7%) |
| calibrated defects caught | 36 of 37 | 37 of 37 | kept (bar 35) |
| clauses / use cases written | 426 / 31 | 499 / 44 | 15% and 30% fewer |
| minutes, output tokens (three cells) | 105.9, 270,820 | 112.2, 256,223 | about the same |
| the due-times request, first build, held-out checks | 3 of 8 and 2 of 8 | 3 of 8 | the misreading is not avoided |

Its two findings, in its words: "the lens form changes how much a specification says and not how sound it is ...
Its large gain on the other experiment's checklist does not appear as a gain in anything a built product shows
here" (F23); and the due-times failure "is not a gap in elaboration that a better elaboration closes. The
specification sees the question, decides it, and labels the decision a choice; four times in five it decides
against what the customer meant, and the tests then hold the product to it. A text that tells the writer to decide
where the request is silent will keep producing this" (F24). Its limits, also in its record: one run a cell and no
measure of its own run-to-run spread; three cases of one kind; the comparison cells ran on a busier machine.

**Against this experiment's own count.** With a repository the lens form wrote fewer clauses than the pilot's text,
not more (its record cites this experiment's count on Sol, with no repository, as 372 against 225). 77 of the 86
clauses of difference on the
two ticket cases are restatements of existing behaviour.

> **Corrected 2026-11-21, 05:02** (by the session whose figure it is): 77 counted use cases. By clauses it is 78
> of 86 (132 and 157 `existing` clauses against 101 and 110).

**What it means here.**

1. The lens arms' large gain on this checklist (sections 11 and 16) is now measured against built products once,
   and nothing shows there. That was the limit sections 14 and 15 named; it is no longer only a caution. It does
   not touch the released stage's result, which the pilot did not run.
2. F24 bears directly on the check that is running. Arm K tells the writer to take a default where the request
   leaves a limit to choice; arm M and the released stage's duty 4 tell it to leave the point open. K is the
   stage's own rule for unattended runs and the owner's; F24 is evidence, from five specifications of one request,
   that a decided point is where a correct product gets rejected. The two are not the same kind of point: F24's is
   a behaviour (refuse to start, or prepare the data), K's is a bound. But a covered count will credit K for
   deciding either way, so if K is shown here that is what it shows, and whether its defaults are right needs a
   built product. Written before either round is read.
3. The three predictions of section 18 for arm R stand as registered. The pilot's session has ported R and told
   its later stages what an `Open:` line means; it is not registered or run there, and whether it runs is with
   the owner in that session.

### Its reply (received 05:02): three things that change what is written above

The note put in its inbox at 04:48 was read: that session recorded it and answered. Its record is "After the
result" in section 20 of its journal, commit 0f044772fc0b8664ade3ef25eef86255e6fe7f41 on the same branch, which I
read; no model ran for it, and it marks all of it as read after its result, not registered.

1. **Point 1 above is flatter than its record supports.** Counted by where each clause comes from, the
   existing-behaviour clauses (223 of the lens form's 426, 300 of the pilot text's 499) almost never fail on the
   reference, so they dilute the pooled share. Of the clauses about the change, 43 of 203 fail on a correct product
   with the lens form against 52 of 199 (21.2% and 26.1%), lower with the lens form in all three cases. That is
   inside the bar it registered and one run a cell, so its verdict stays "no difference shown"; "nothing shows
   there" should read "the same direction three times, not shown".
2. **The number behind point 2.** A clause the writer marked as its own choice fails on a correct product two times
   in five (21 of 53 with the lens form, 17 of 48 with the pilot's text), against about one in seven of the
   request's own clauses. A default taken for a limit is a choice. That is the caution arm K carries into any
   reading of rounds 7 and 8.
3. **A limit on section 19 that I had not stated.** The operator requirements the earlier block added were written
   with no repository to show what controls exist. That session read its failing items by hand (one reader, not
   blind, exploratory): with a repository, in three cases, no failing item under either text requires a control the
   request or the repository lacks; what goes beyond the request is documents (10 of 11 such items require a
   runbook or instructions to say something). So the same unconditional line that produced new controls here
   produced decided forms of requested work and required documents there. Section 19's finding holds for a request
   with nothing built yet, which is this experiment's four cases, and is not shown for one with a product already
   in place.

## 22. Rounds 7 and 8: the cue that leaves a limit open moves nothing; the one that takes a recorded default is shown on both drivers (2026-11-21)

48 sessions (arms M, K and P on both drivers, four cases, two rounds), all exit 0 after a passing pre-flight each
round. The leak check found no session in either round that read outside its own directory and profile or named
the held-out material. Both judges read all 48 specifications; none of the four sets of 24 verdict files has a
missing or unknown item.

> **Reworded 2026-11-21, 06:01** (the review; section 24): what the leak check does is scan each session's tool
> calls for named paths and held-out names, and it flagged none. That is narrower than "read nothing outside".
> The Sol sessions also searched the web (seven searches in each released-stage session on the bot), so these
> sessions lacked the stage's usual upstream evidence, not all research.

Ran 04:22 to 05:31. `evidence/round-7/`, `evidence/round-8/`; the tables and tests are in the README, "Result of
rounds 7 and 8".

### The registered readings

Covered on the 22 target items, cue arm against the released stage of the same round, round 7 then round 8, and
the mean of the two differences.

| | Sonnet, opus | Sonnet, astra | Sol, opus | Sol, astra | R16 |
| --- | --- | --- | --- | --- | --- |
| M, the review's wording: an unresolved bound is an open gap | +0, +1: +0.5 | -1, +1: 0.0 | +1, +0: +0.5 | -1, +3: +1.0 | nothing shown |
| K, a limit left to choice is a recorded default | +4, +2: **+3.0** | +4, +2: **+3.0** | +7, +4: **+5.5** | +8, +5: **+6.5** | **shown on both drivers** |

- R17, nothing lost: holds for both arms. K is above the released stage on the other 53 needed items in every cell.
  > **Qualified 2026-11-21, 06:01** (the review, checked; section 24): the guard reads the net count. Item by
  > item, K fails to cover 8 item-cells there that the released stage of its round covered, and 13 under the
  > second judge, against 23 and 25 the other way.
- R18, no capability added: holds for both arms. On the four items both sorters call beyond, K's means are 0.0
  and 0.0 on Sonnet and +0.5 and -0.5 on Sol, and each movement, read in the specification, is a stated exclusion
  scored one way or the other, not a control.
  > **Superseded 2026-11-21, 06:01** (the review, checked; section 24): the guard did not fire, and that is all
  > it shows. One K specification (reminders, Sonnet, round 7) has a requirement "Pause and resume reminders for
  > one invoice", where the released stage of the same round excludes "per-customer or per-invoice switches (the
  > request does not ask for them)". The item that would hold it is a bundle and was scored partial by both judges,
  > so the count never saw it. And the target set itself rewarded three waitlist caps nobody asked for, and in one
  > of those specifications a waitlist cutoff "60 minutes before the class start" recorded as an assumption.
- R19: of the items the released stage covered in neither earlier draw, K covers 7 and 5 of Sonnet's 24 (a fresh
  released stage 1 and 1) and 14 and 14 of Sol's 42 (4 and 8).
- Size, K against the released stage: words 1.03 and 1.17, requirements 1.05 and 1.03, output tokens 1.26 and
  1.19 (Sonnet, Sol).
- The four non-functional bounds, read as registered: no performance target without a stated basis. Details in
  the README.
  > **Superseded 2026-11-21, 06:01** (the review, checked; section 24): too generous. "At most 60 minutes late"
  > is a promise about when work reaches the mail provider, derived from an assumed hourly run with the provider's
  > limits recorded as unknown in the same specification: it is unsupported. The other round's "maximum reminders
  > ... = number of offsets" does not hold if the schedule is edited, which that specification allows. The bot's
  > 30 seconds is when the app stops waiting, not when an answer arrives. The waitlist passage has no number.

**By the decision rule: no change is proposed for M. K goes forward**, to the review at maximum effort and then to
the owner. Nothing under `skills/` has changed.

The predictions of section 20: three of four held. M did less on Sonnet than predicted (I had said 1 to 3; it is
+0.5 and 0.0).

### What the counts do not say

Read after the readings, so descriptive. The kinds are the two sorters'; the reading of passages is mine, and the
passages are in `evidence/round-8/K-target-items-round-7.md`, `-round-8.md` and `K-stable-target-items.md`.

1. **The first sentence of both cues did nothing that can be seen.** On the target set's 7 sets the released stage
   covers 5, 4 on Sonnet and 4, 4 on Sol; M 5, 5 and 5, 5; K 5, 5 and 4, 4. The two sets it leaves unsettled in
   every draw since round 5 (every condition that stops a reminder sequence; an existing do-not-contact state on
   the customer) stay unsettled under both cues, in every round, under both judges. Telling the stage to "name its
   members" did not make it name them where no repository shows what the states are.
2. **All of K's effect is its second sentence.** On the 13 limits: the released stage 7, 6 and 3, 4; M 7, 6 and
   3, 3; K 11, 8 and 9, 7. M and K differ in that sentence only, and in one thing in it: where the request leaves
   a limit to choice, M records an open gap and K takes a default and records it as an assumption.
   > **Qualified 2026-11-21, 06:01** (section 24): M and K share the first sentence and differ in several words
   > of the second, and no arm ran either sentence alone. What the comparison supports is that K's wording of the
   > second sentence outscored M's with the first shared, and that nothing shows the first adds anything.
3. **What K decided, in the 20 times it covered a target item the released stage of its round did not** (3 went
   the other way): 12 are a default for a limit the released stage also says exists and leaves without a value;
   3 are a cap on the waitlist the request never mentioned; 2 are platform limits given their numbers; 1 is a
   set's members named; 2 are no difference in substance. The 12 are what the cue was written for: "A-4 |
   Limits: file at most 1,048,576 bytes (1 MiB); at most 1,000 data rows ... These are product defaults chosen
   for an admin-sized batch, not platform limits; platform limits are gap G-3", beside the released stage's
   "size and row-count limits are configured values ... (G-1: default values unresolved)".
   > **Superseded 2026-11-21, 06:01** (the review's item-by-item reading, which I checked against the same
   > passages; section 24): my five bins were too kind. Of the 20: **9** are a value given to a parameter both
   > arms already name (the import's limits four times, the prompt's maximum twice, the reply deadline twice, the
   > reminder schedule once); **3** are waitlist caps; **1** is platform numbers; **1** is a platform figure whose
   > bearing on the design is doubtful; **2** are a set's members (I had called one of them no difference: K's
   > import names line breaks inside quoted fields and the released stage's did not); and **4** are a change of
   > behaviour, not a default: evicting the oldest turns where the released stage refused, promoting in the same
   > commit as the cancellation where the released stage kept a recoverable pending allocation, and two
   > different rules for reminder timing or volume. The nine are candidate defaults, no more: whether each is
   > needed, and right, is not shown.
4. **The three are the cue over-reaching.** Every K specification of the waitlist request but one gives the
   waitlist a cap (10, 10 and 20), each recorded as an assumption with its reason ("Bounds work per event and a
   member's wait; small gyms rarely queue deeper"). The released stage said "G-3 — waitlist length cap. Assumed
   none" and "No bound is invented ... Treated as unbounded". A file must have some size limit; a waitlist need
   not have a cap. "A limit the request leaves to choice" was read as any limit one could set, and the judge
   scored the cap covered and the decision to have none partial.
5. **The defaults differ between draws**, as defaults will: the import's limits are 1 MiB and 1,000 rows, 2 MiB
   and 5,000, 256 KiB and 500, 1 MiB and 1,000; the prompt's maximum is 2,000 code points in one and 4,000 UTF-16
   units in the other.

### What this is evidence of, and what it is not

**It is evidence that the two drivers resolve the stage's own two instructions differently, and that one sentence
settles it.** Duty 4 says to mark a user decision as an open gap; the RULES say "Unattended: take the best default
and record it as an assumption; a person-only step is an open item". On limits Sol follows the first (3 or 4 of 13
settled) and Sonnet more often the second (6 or 7). K's sentence points both at the second: Sol reaches 7 to 9,
about where Sonnet's released stage is, and Sonnet 8 to 11. That is the stage's existing rule applied where one
host was not applying it, not a new policy.

> **Superseded 2026-11-21, 06:01** (the review, checked; section 24): "Sol follows the first and Sonnet the
> second" is my story and the specifications do not establish it. Both drivers' released-stage specifications
> choose some defaults and leave others open: Sonnet gives the bot 4,000 characters and a 60-second timeout in
> both draws and leaves the import's values unset; Sol in round 7 sets reminders at days 1, 7 and 14 and in round
> 8 defers them. What is shown is narrower: Sonnet's released stage names more of this checklist's bounds in this
> frame, and K's wording raises both. Which instruction, which evidence and which part of the driver's set-up
> accounts for the difference is untested.

**It is not evidence that the defaults are right, or that a product built from them is better.** The count credits
deciding (section 14). Section 21 holds the only built-product evidence there is: in the pilot's three cases a
clause the writer marked as its own choice failed on a correct product two times in five. A default for a limit
is a choice. In a ShipLoop run the same specification is built and tested, so its own gates would pass with a cap
of 10 on the waitlist; whether the owner wanted one is what no gate in that run can show.

**And it is one frame.** These sessions had no repository, no research result and no selected baseline. In a real
run the research stage may already have the platform's limits, and an existing product may already have a file
size limit to read. How much of the gap on Sol remains then is not known.

Limits: two rounds, so two draws an arm; X1's band is the floor of 2 and not a measured maximum; two cue arms were
two chances to pass (K passes on both drivers under both judges in both rounds, which chance does not easily do);
the checklist is the author's, though the sets are not.

> **Corrected 2026-11-21, 06:01** (the review, checked; section 24): "which chance does not easily do" is
> withdrawn. The two contrasts share one control, both judges read the same specifications and round 8 repeats
> round 7's cases, so the agreements are not independent. K's own count on the target moved by 3 between the
> rounds on Sonnet under both judges. With the waitlist cap's item left out, K against the released stage is +3
> and +1 on Sonnet under both judges, a mean of exactly the floor, and K against M there is +3 and 0, +4 and 0;
> on Sol it is still +6, +4 and +7, +5 against the released stage. And the whole checklist: the registration
> gave it a band of 12 for context; `label.py pair` printed its status against 6. Against 12 it is not shown on
> either driver.

### Where it goes

1. The review at maximum effort, on K's text inside duty 2 and on this section, as registered. It is asked two
   things this section raises: whether the first sentence should go, and how to word the second so that it covers
   a limit the requested behaviour cannot work without and not a limit that need not exist.
2. Then the owner, with the review. A change to duty 2 is a ShipLoop product change: the owner's word, the packet
   and guidance suites, a change note, and an E2E round after it.

## 23. Received after the result: an added refusal is where two correct products part ways (2026-11-21, 05:44)

Recorded as received. The count is the Ratchet session's, on its six graded runs; its record is "Received: the
other session's rounds 7 and 8" in section 20 of its journal, commit 1ef1ee5b30d173bf349a882149bf7643404cc2aa on
its branch, which I read. No model ran for it. It had read section 22 here and re-ran nothing of mine.

Its count (its F28; a fixed word list marks a clause whose statement makes the product refuse, fail or require
something; "failing" means the clause's test fails on the correct reference; both of its texts pooled):

| where the clause comes from | it refuses or requires: written, failing | the rest of that kind: written, failing |
| --- | --- | --- |
| the writer's own choice | 27, 18 (67%) | 74, 20 (27%) |
| implied by the request | 19, 10 (53%) | 137, 25 (18%) |
| the request itself | 20, 2 (10%) | 125, 20 (16%) |
| existing behaviour | 85, 1 (1%) | 438, 10 (2%) |

In its words: "A refusal the writer added on its own ... rejects a correct product 28 times in 46; its other
additions 45 times in 211; a refusal the request states or the product already has, 3 times in 105." And on the
question section 22 put to the review: "A cap on a waitlist and a maximum size for a file are both refusals the
request did not state, so this mark does not separate its two kinds. What it supports is narrower: an added
refusal is where two correct products most often part ways, whatever its reason; and a default that must exist ...
is still decided differently by different writers, as its own three draws of the file limits show." Where a writer
there chose no further limit, the clause passed on the reference 5 times in 5.

Its limits, as it states them: one run a cell, three cases, Sol the only writer, a word list as the mark, one
correct reference a case.

**What it means for arm K.** Every one of K's 15 defaults and caps (section 22, the 12 and the 3) is a refusal the
request did not state: a file above the limit is rejected, a prompt past the maximum is refused, the twenty-first
person is told the waitlist is full. On the only built products anyone has graded, that is the kind of clause two
correct builds disagree on two times in three, and "Assumed none", which the released stage wrote for the
waitlist, is the kind that passed every time. It does not say K's limits are wrong: a ShipLoop run builds to its
own specification, and a file must be refused at some size. It says the value is arbitrary between correct
products, which K's own four draws of the import's limits already showed, and that pinning it in a test pins
something the owner never chose.

**A third form that neither arm tested.** The same record notes that in its pilot an `Open:` point is "the default
cue's rule without the test: the build takes a reasonable answer and reports it, and no test pins it". The
released stage on Sonnet already writes something close for the import: "size and row-count limits are configured
values (`max_bytes`, `max_rows` ...); exceeding either rejects the whole file before any user is created (G-1:
default values unresolved)". The behaviour at the limit is specified and testable at whatever value is set; only
the default is missing. Between M (leave it open) and K (decide it and test the number) there is: state the
behaviour at the limit, give the default as a named, changeable setting recorded as an assumption, and test the
behaviour at the configured value and not the number. That is not measured here and is put to the owner as a
question, not a proposal.

## 24. The review says: ask for a trial of a narrower wording in duty 4, and it finds my reading of round 7 and 8 too kind in eight places (2026-11-21, 06:01)

The registered review ran: the latest Sol at maximum effort, read-only over this repository, on the brief in
`review/cue-K-prompt.md`; its report is `review/cue-K-review.md` (18 findings; 05:36 to 05:57). It read sections
19 to 23, the arms, the labels, all four verdict sets and the 48 specifications, ShipLoop's prompts and later
stages, and the pilot's record at 0f044772fc0b8664ade3ef25eef86255e6fe7f41. It ran its own counts and wrote
nothing.

**Its verdict:** "put it to the owner after these changes: correct the evidence claims and qualify the duty 4
replacement in the paired built-product trial. The request to the owner now is for trial authorization." Not arm
K's two sentences in duty 2, and not a change to ship.

### What I checked of it, and found as it says

Each against the saved verdicts or the specification named:

- K fails to cover 8 item-cells on the other needed items that the released stage of its round covered (13 under
  the second judge), against 23 and 25 the other way. The registered guard reads only the net.
- One K specification (reminders, Sonnet, round 7) has "R-9 Pause and resume reminders for one invoice"; the
  released stage of that round excludes "per-customer or per-invoice switches (the request does not ask for
  them)". And one K waitlist specification assumes a cutoff "60 minutes before the class start instant".
- All 20 of K's gains under the registered judge, and all 21 under the second, are a partial become covered: none
  is an item the released stage had not reached.
- Without the waitlist cap's item, K against the released stage is +3 and +1 on Sonnet under both judges; K
  against M on Sonnet is +3, 0 and +4, 0. On Sol K stays +6, +4 and +7, +5.
- K's own count on the target moved by 3 between rounds on Sonnet under both judges; M's by 4 on Sol under the
  second judge. The four repeat pairs behind the band had moved by at most 1.
- The whole checklist's status was printed against a band of 6 where the registration said 12.
- Both drivers' released-stage specifications choose some defaults and leave others open (the bot's 4,000
  characters and 60 seconds on Sonnet in both draws; reminders at days 1, 7 and 14 on Sol in round 7).
- The Sol sessions searched the web: 7 searches in each released-stage session on the bot.
- The target set holds one item the sorters split on (needed and mixed), and 10 items are in none of the three
  sets.

Its reclassification of K's 20 gains (9 values for a parameter already named; 3 waitlist caps; 2 platform
figures, one of doubtful bearing; 2 sets; 4 changes of behaviour) I checked passage by passage for the ones I had
binned differently and accept. Each of these is marked in place in section 22.

Not checked by me: its in-memory render of the proposed text through the packet and guidance suites (it reports
the spec packets growing from 16,999 to 17,695 characters and the existing assertions holding), and its reading
of every later stage's duty.

### What it says about the text

1. **K's phrase is the fault.** "A limit the request leaves to choice" treats silence about whether a limit
   should exist as leave to choose its value. A file's size limit, an input's maximum and a timeout can be
   necessary; a cap on a waitlist needs a basis of its own.
2. **A value in an acceptance line becomes a build and test obligation even when it is labelled an assumption**
   (it names the duties of `test-strategy`, `plan`, `step-plan`, `test-spec` and `implement` that carry it).
   A passing check then shows the product implements the chosen value and says nothing about the choice. For a
   delegated default: test the behaviour below, at and above a limit supplied to the test, and verify the shipped
   default separately. It points at the released stage's own round-7 import specification on Sonnet, which uses
   fixture values of 1,024 bytes and five rows and leaves the shipped defaults unresolved. That is the third form
   section 23 arrived at from the pilot's count.
3. **Not duty 2.** The rule belongs where the open-gap decision is made, in duty 4. Both of K's sentences go; the
   first overlaps what duty 2 and the behaviour guide already ask.
4. **Its text**, to replace duty 4's "Mark each unresolved prerequisite or user decision as an open gap under its
   R-<n> in KNOWLEDGE/spec.md.":

   > Mark unresolved prerequisites and decisions that require the user as open gaps under their R-<n> in
   > KNOWLEDGE/spec.md. Use applicable bounds from the request or preserved contract. Introduce a functional limit
   > the request leaves unstated only where the requested behaviour cannot work correctly or safely without it.
   > When only its value is open, take the best reversible default supported by the available evidence and
   > applicable runtime limits (item 10). If the basis for such a default is missing, keep the bound open under
   > its R-<n>. State the observable behaviour at and beyond the effective bound and label any chosen value as a
   > default in its acceptance line. Record that value, its basis, alternatives and revalidation condition as an
   > assumption for that R-<n> in `summary`.

5. **What a trial would have to be:** full unattended runs from intake to handoff with real discovery and
   research, three matched pairs a case on Sol and the same on Sonnet as a regression check, external oracles
   frozen beforehand, a case with a limit the behaviour needs, a case with an established limit to preserve, and a
   waitlist that must still admit people past 10 and 20. Withdraw the wording "if real context erases the gain, if
   the gain exists only in generated tests or checklist scores, or if it introduces an unjustified refusal".
   Three cases, three pairs, two arms, two hosts: 36 deliveries.

### Where that leaves it

- **Established** (the review's word, and mine): M clears nothing. K is above the released stage in every cell on
  the target under both judges. K makes several open values concrete and adds three waitlist caps nobody asked
  for.
- **Interim:** a default-oriented wording makes these specifications more decided, most usefully on the import's
  limits and on the bot's bounds on Sol. Whether a narrower wording keeps that, whether any of it survives real
  discovery, and what it does to a built product are untested.
- **Unsupported, and withdrawn above:** that K adds no scope and loses nothing; my five bins; that the first
  sentence has no effect; that duty 4 against the RULES explains the difference between the drivers; that the
  result is unlikely by chance.

**One thing the review's text does that I expect to matter, written before any run of it.** Its fifth sentence,
"If the basis for such a default is missing, keep the bound open", is the way out that arm M and the earlier
block both offered, and on Sol both moved nothing. With no repository and no research result the basis is missing
nearly every time. Prediction: on this instrument the review's text behaves like M on Sol (under 2 of the target)
and does not add a waitlist cap on either driver. If so, a 36-delivery trial of it would be testing a sentence
that changes little.

## 25. A filter round for the review's wording, registered before any call (06:05, 2026-11-21)

Decision, routine (launching a verification run on the experiment's own instrument; nothing ShipLoop does
changes): before the owner is asked to authorize 36 deliveries for the review's text, two rounds here ask whether
that text changes what the stage writes at all. About 80 minutes and about what rounds 7 and 8 cost.

Why it is worth asking first. Section 24's last paragraph: the review's fifth sentence gives back the way out that
arm M offered. If the text behaves like M, a trial on built products would be measuring a sentence that changes
little, and the honest answer to the owner's to-do is "no change" without the trial. If it keeps K's gain on the
limits that have to exist and drops the cap on the waitlist, the trial has something to test.

What is registered (README, "A filter round for the review's wording"):

- Arm G: the released stage with one sentence of duty 4 replaced by the review's seven, word for word. Arm H: G
  without its fifth sentence, as a contrast and not a candidate. P as the control of each round.
- A second sort by the same two outside sorters, before any subject call: each of the target's 15 limit items is
  `necessary`, `optional` or `unclear`, by the review's own test ("cannot work correctly or safely without
  it"). N1 and O1 are what both sorters agree on. I sort nothing.
- Bands from every clean repeat pair through round 8, which is more pairs than the four behind rounds 7 and 8 and
  includes K's and M's own two draws.
- R20 on N1; R21 on O1 with the twelve waitlist specifications read for a cap and for a self-set cutoff; R22 the
  other needed items, net and item by item both ways, as the review asked; R23 the capability items with any
  added control named.
- It is a filter: no extension round, and H cannot be proposed from it.

Predictions, on record before the sort: G moves Sol's N1 by less than 2; no G specification caps the waitlist; H
moves Sol's N1 by 3 or more; at most one H specification caps the waitlist.

## 26. Two free readings of deliveries that already ran: what happens to a limit nobody stated, and what the final report shows (07:06, 2026-11-21)

The owner, asked whether there was enough to conclude early, said to conclude and then agreed to two readings that
cost nothing: follow open points through deliveries already run, and check whether the final report shows the
defaults a run chose. No model was called. Tool: `limits_census.py` (it reads each delivery's work tree, its
specification at the spec stage, its tests and its final report). Evidence:
`evidence/readings/limits-census.txt` and `evidence/readings/due-hours-ceiling.txt`.

**The sample.** 31 deliveries on the latest ShipLoop that have a work tree and a final report: 30 from the SDLC
session's study (its runs, read and not touched) and one from the Ratchet session's pilot. By case: 16 ticket due
times, 11 shared expenses, 2 hello, 1 ticket assignment, 1 local chat app. By driver: 26 on Sol 6.2 (medium and
high), 5 on Sonnet high. All four requests are several paragraphs long and precise.

### What the readings found

**1. This experiment's frame is not what the stage does in a real run.** Words in the specification at the spec
stage: Sol a median of 384 (120 to 731), Sonnet 2,207 (1,718 to 2,288). In rounds 5 to 10 here the same stage text
wrote 4,400 to 6,600 words on Sol and 6,000 to 10,000 on Sonnet. And open gaps: none in any of the 26 Sol
specifications, one each in 3 of the 5 Sonnet ones. The open points this experiment kept counting hardly occur in
a real run. Real Sol specifications do not leave a limit open; they do not mention it.

**2. A limit the request does not state still ends up in the product, and on Sol nobody writes it down.**

| | Sonnet high | Sol 6.2 (medium and high) |
| --- | --- | --- |
| ticket due times: the request lets the help desk change the hours and names no upper bound. Products that enforce a ceiling | 4 of 4 | 12 of 12 |
| specifications that state that ceiling | 4 of 4 | 0 of 12 |
| final reports that mention it | 4 of 4 | 0 of 12 |
| the ceilings chosen | 100,000; 87,600; 8,760; 8,760 hours | from 1,000,000 hours up to the largest date JavaScript can hold |
| shared expenses: a JSON service. Products that cap the size of a request | 1 of 1 (1 MiB, answered 413) | 0 of 10 |
| the cap is a requirement with a test | yes: "R-12 Request robustness (extra defaults, assumption A4)", tested either side of 1,048,576 bytes | none to test |

The chat app delivered on Sol at high has nine limits its builder chose (a 64 KB request, 80 characters for a
name, 8,000 for a message, an instruction or a memory, 100 for an identifier, 44 for a title). None is in its
specification, its knowledge files or its README, and a search of its tests finds none that sends an over-long
value or an oversized request.

So on Sol a limit nobody stated is either chosen by the builder without a record, or not built. On Sonnet the
specification states it, a test holds it, and the owner can read it.

**3. The final report shows what a stage wrote down, and only that.** It has sections for open items (each
assumption with how to settle it, why, when and who), unverified request outcomes and follow-on. Sonnet's reports
list a median of 6 assumptions (0 to 10) and show the ceiling in 4 of 4. Sol's list a median of 0 (0 to 2), show
the ceiling in 0 of 12 and none of the chat app's nine limits. The report is not where the gap is: what no stage
writes cannot be shown.

### What it means for this experiment

- **The lever is real in built products, on Sol.** Rounds 7 to 10 found that telling the stage to give a default
  to a limit the behaviour cannot work without changes what Sol writes. These deliveries show the thing it would
  change: limits enforced that the owner never sees, and a network service with no bound on a request. By the
  owner's rule of 2026-09-27 quotas and security checks are rigour, expected even for a small request.
- **And this experiment cannot say what the rule would do in a real run.** Its frame makes the stage write ten
  times as much and leave points open that a real run never raises. Every number in sections 3 to 25 is a number
  about that frame. The token figures (a median of 44,000 output tokens a specification on Sonnet) are the
  frame's too, not the stage's.
- **The next experiment that could matter is small, and its control already exists.** The archive holds 12 Sol
  deliveries of ticket due times and 10 of shared expenses on the latest ShipLoop, with 0 of 12 and 0 of 10 on the
  two counts above. Two or three deliveries a case with the rule in duty 4 would show whether the specification
  starts to state the ceiling and the request limit, whether a test holds them and the report shows them, and
  whether the held-out verdicts move. That is a ShipLoop candidate run and is not started: it is the owner's to
  authorize.

Limits. One study's cases, three kinds of request, all detailed; five Sonnet deliveries. The limit finder is a
pattern match and its candidates were read; "no cap" means no product file the run added holds a 413, a "too
large" refusal or a named maximum, and a service could bound a body some other way that I did not look for. The
deliveries' own verdicts (many of the due-times ones failed) are about other things; nothing here shows a limit
changed a verdict. Whether an unstated ceiling of a million hours is a defect at all is a judgement: the point is
that it was decided and not written.

## 27. Rounds 9 and 10: the review's wording moves nothing and is worse on Sol; without its "keep the bound open" sentence it settles the limits that must exist (07:15, 2026-11-21)

48 sessions (arms G, H and P, both drivers, four cases, two rounds), all exit 0, 06:07 to 07:14, after a passing
pre-flight each round; the scan flagged no session in either round; both judges read all 48 specifications and no
verdict file has a missing or unknown item. `evidence/round-9/`, `evidence/round-10/` (`readings-G.txt`,
`readings-H.txt`, `by-set.txt`, the item-by-item files, `waitlist-cap-and-cutoff-lines.txt`).

Covered, round 9 then round 10, registered judge / second judge:

| | Sonnet | Sol |
| --- | --- | --- |
| **N1, the 6 limits that must exist.** P, the released stage | 3, 3 / 4, 2 | 1, 3 / 1, 3 |
| G, the review's seven sentences in duty 4 | 3, 3 / 3, 3 | 1, 0 / 0, 1 |
| H, G without "If the basis for such a default is missing, keep the bound open" | 4, 4 / 4, 4 | 4, 4 / 5, 5 |
| **O1, the 6 limits that need not exist.** P | 5, 4 / 5, 3 | 0, 0 / 0, 1 |
| G | 3, 3 / 2, 5 | 1, 0 / 0, 0 |
| H | 4, 4 / 4, 4 | 2, 2 / 2, 0 |

**R20, limits that must exist.**
- **G: nothing shown.** Against the P of its round: 0.0 and 0.0 on Sonnet; -1.5 and -1.5 on Sol.
- **H: shown on Sol** (+3, +1 and +4, +2: means +2.0 and +3.0, every round above zero under both judges), interim
  on Sonnet (+1.0 and +1.0).

**R21, limits that need not exist.** Neither arm is shown on O1. H's +2 and +2 on Sol under the registered judge
are a reply timeout given a default (60 seconds) and, on the waitlist, the sentence "There is no feature-specific
numerical list cap", which the judge scored covered where the released stage's "no numeric SLA or waitlist cap"
with the cap left to its owners was partial. **The twelve waitlist specifications, read: none of G's four and none
of H's four gives the waitlist a maximum size, and none sets a cutoff of its own.** Sonnet under G: "No cap on
waitlist length ... A cap is not needed for correct or safe behaviour ... Inventing a number would turn people
away, which the request opposes". Sonnet under H: "No waitlist length
cap and no 'latest promotion time' cutoff". Arm K capped it in three of four.

**R22, the other needed items.** G is below the released stage in every cell: -1.0 and -3.0 on Sonnet, -6.0 and
-6.0 on Sol (band 7). Item by item on Sol it covers 2 or 3 item-cells the released stage does not and fails to
cover 14 or 15 that it does. H: +4.0 and +2.5 on Sonnet, +0.5 and +1.0 on Sol; item by item on Sol 9 or 10 gained
and 8 lost.

**R23, capability not asked for.** Not shown for either. H's +3 in round 9 on Sonnet under the registered judge
is three stated exclusions scored covered ("Staff get no waitlist view and no manual promotion in this change";
"No per-invoice or per-customer pause"; no cancel for a running import); the second judge scored none of them.

**The whole checklist.** G on Sol is **worse**: -12.0 and -10.5, beyond the band of 7 in both rounds under both
judges. H: +6.0 and +4.0 on Sonnet, +1.5 and +2.5 on Sol.

**Size.** Output tokens against the released stage: G 1.03 and 0.98; H 1.18 and 1.23.

**Steady in both rounds:** H settles the import's size and row limit in both rounds on both drivers where the
released stage does in neither (on Sol under both judges), each time labelled a default: "Limits: file 2,097,152
bytes (2 MiB); 5,000 data rows ... Labelled defaults, not requirements"; "Default maximum 65,536 file bytes
inclusive". G has no such item.

### By the registered rule

**The review's text does not go forward.** It is not shown on the limits that must exist on either driver, and on
Sol it is worse than the stage as released. No trial on built products is recommended for it.

**H explains why, and cannot be proposed from these rounds.** The two arms differ by one sentence. With "If the
basis for such a default is missing, keep the bound open", Sol settles 1 and 0 of the 6 limits that must exist;
without it, 4 and 4. In this frame the basis is always missing, so the sentence switches the rule off, and the
six sentences around it then tell the session about open gaps at greater length than the released stage does.

Predictions of section 25: G moves Sol by less than 2: held. No G specification caps the waitlist: held. H moves
Sol by 3 or more: held under the second judge, not under the registered one (+2.0). At most one H specification
caps the waitlist: held (none). Not predicted: that G would make Sol worse.

Limits: six items a set; two rounds; the same frame, which section 26 shows is not the stage's real conditions.
In a real run the basis for a default may not be missing, and G's sentence may then cost nothing.

## 28. Concluded: no template change, one candidate left on the shelf, and what this experiment was worth (07:16, 2026-11-21)

The owner, 2026-11-21, on being told what could and could not be concluded: "Conclude now". Earlier the same
morning: "Yes, plan small experiments before doing larger ones to see if you can get fast iteration. Do we have
sufficient evidence to conclude early?" This section closes the side experiment that began on 2026-11-20 with "a
prompt that will actually help take an incoming, kind of vague prompt ... and ... elaborate into a verbose spec".

### The answer to the owner's to-do

"Did we update the prompt templates for Shiploop to improve them?" **No, and none is proposed.** Nothing under
`skills/` or `agents/` was changed at any point in this experiment.

### What stands, most firmly first

1. **The released spec stage is not missing an elaboration step.** Ten rounds, twelve arms, two drivers, two
   judges. Run alone on a one-sentence request it reaches 80 to 87 of 89 held-out items; in real deliveries it
   writes a short, complete specification (section 26).
2. **Wording that leaves the stage free to keep a point open changes nothing.** The earlier block's enumeration
   sentence (round 6), arm M (rounds 7 and 8) and the review's own text, arm G (rounds 9 and 10, where it was
   worse on Sol).
3. **Wording that tells the stage to take a default changes what it writes, most on Sol.** Arm K (shown on both
   drivers) and arm H (shown on Sol). Worded as "a limit the request leaves to choice" it also invents limits and
   controls nobody asked for (K: a waitlist cap in three of four, a per-invoice pause, a 60-minute cutoff). Worded
   as "only where the requested behaviour cannot work correctly or safely without it" it did not (H: no cap in
   four of four).
4. **In real deliveries on the latest ShipLoop, Sol's products carry limits nobody wrote down, or lack ones a
   careful build includes; Sonnet's specifications state and test them** (section 26: 0 of 12 against 4 of 4 on
   the hours ceiling; 0 of 10 against 1 of 1 on a request-size cap).
5. **The operator and unhappy-path cue was right to withdraw.** Its lift was added operator controls (section 19),
   which the owner's rule of 2026-09-27 calls overbuilding, and two outside sorters picked out the same items.

### What does not stand

- The lens block (section 15), arm K as worded (section 24) and the review's text as worded (section 27).
- Every number here as a statement about the stage in a real run. The frame (one sentence, no repository, the
  submission folded into the specification) makes the stage write ten times as much and leave open what a real
  run never raises (section 26). The numbers compare arms inside that frame and nothing more.
- A covered count as a measure of quality. It credits deciding (sections 14 and 24), and half of K's gain was on
  limits two outside sorters say a correct product could do without (section 25's sort).

### One candidate, on the shelf and not proposed

Arm H's text: in duty 4, the review's rule without its "keep the bound open" sentence
(`arms/H-shiploop-spec-duty4-no-open.insert.txt`). It has two rounds on this bench as a contrast arm, +18 to 23%
output tokens there, and no run of any kind in ShipLoop. If it is ever wanted, the test is small and its control
exists: two or three deliveries a case on Sol of ticket due times and shared expenses, against the 12 and 10
already archived (0 of 12 specifications state the hours ceiling; 0 of 10 products cap a request), read for
whether the specification states the limit, a test holds it, the final report shows it and the held-out verdicts
move. It needs the owner's word, a candidate plugin build and the E2E harness; none of that is started. On Sonnet
the released stage already does this unprompted.

> **Qualified 2026-11-21, 07:26** (section 29, received after this was written): the only built-product evidence
> on the question now favours the opposite design. In the pilot's session a text that leaves such points open, with
> one sentence telling later stages to take a reasonable answer, report it and pin it in no test, passed 8 of 8
> held-out checks twice where every text that decided had passed 2 or 3. H decides in the specification and its
> tests would hold a product to the number. If anything here is taken further it should be read against that
> first.

Also the owner's, unchanged: the E2E harness's Codex sessions being shown the user's own skills (section 7; a
task card was put up for it); the stale sentence in `skills/shiploop/references/behavioral-requirements.md`
(sections 14 and 24: both reviews found it); and the order in which this experiment's commits and another
session's are published from the shared checkout.

### What it cost and what it was worth

Ten rounds of subject sessions, two judges, two reviews at maximum effort, two sorts. It did not improve the
template. It did establish that the stage is not short of elaboration, turn three plausible additions into
recorded negatives before any of them reached a release, find that the E2E harness's Codex sessions are shown the
user's skills, and locate one real difference between the two drivers in built products.

### Lessons for the next experiment, each of which cost something here

1. **Read deliveries that already ran before building a bench.** Section 26 took an hour and no model, and showed
   both the real gap and that this experiment's frame was ten times off. It should have been section 1.
2. **Check a bench against the real thing on a plain measure first** (here, words in the specification). A bench
   that makes the stage write ten times as much is measuring something else.
3. **A count that rewards deciding needs its items sorted by someone else** into what must be settled and what
   need not. Two cheap sorts changed the reading of every round after them.
4. **Write the prediction down before the run.** Eight were registered in sections 20 and 25 and six held; the
   two that missed (how far M would move Sonnet; H under the registered judge) were the informative ones, and so
   was the thing not predicted at all (G making Sol worse).
5. **Decide after the first round.** M and G were visibly doing nothing after one round under one judge, and the
   second judge never reversed a direction on a target set. Dropping each after its first round, and keeping the
   second judge for arms still alive, would have saved 16 of the 96 sessions of rounds 7 to 10 and 48 of their
   192 judge calls. (I told the owner "about a third" before counting; it is a sixth and a quarter.)
6. **Take the review before the write-up goes anywhere, and check it.** Both reviews withdrew claims I had already
   made to the owner; both were right on every fact I checked.
7. **An open route in the wording is the whole wording.** "Or record it as unresolved", "as an open gap", "if the
   basis is missing, keep the bound open": three texts, three nulls.

   > **Qualified 2026-11-21, 07:26** (section 29): that is true of a count over a specification, which is all this
   > bench reads. It is not a verdict on leaving points open. Where the stages after the specification are told
   > what to do with an open point, the pilot's builds did better with it open than decided.

### Closing actions (07:18)

- A note with this conclusion and section 26's two findings was put in the Ratchet session's inbox; whether it
  has been read is not known here.
- Not published. `origin/main` is at 79de0b67d1feec278a90e194ffb7aa628de6dd75. The shared checkout's local main holds this
  experiment's commits after it, interleaved with two of the SDLC session's that are not on origin either. A note
  to that session about the order was held and expired undelivered, because the two sessions run in different
  permission modes. The order is put to the owner.

  > **Published 2026-11-21, 07:40** (written 07:42, after it was seen on the remote). The owner, asked whether to
  > publish the shared main including the SDLC session's commits: "Publish now". One guarded push from a temporary
  > worktree took `origin/main` from 79de0b67d1feec278a90e194ffb7aa628de6dd75 to
  > f671146ad2ad7ce19458786131bc5a2276e4f098: fifteen commits in the order they were made, eleven of this
  > experiment's and four of the SDLC session's, 556 files, all under `docs/`, every commit with its
  > No-Change-Note. Before it: the quick tier on the changed paths (13 suites, passed) and the guard's three
  > checks (marketplace payload, release boundary, test groups: passed). `git ls-remote` then showed the new tip.
  > CI on that commit had started and not finished when this was written. A first attempt stopped itself before
  > doing anything because its own file filter was wrong; nothing was pushed by it. This note and one later
  > commit of the SDLC session's are local and go out with the next push of main.
- No session, monitor or queue of this experiment is running. Raw session folders stay under
  `~/e2e-runs/spec-elaboration-20261120/`.

## 29. Received after the conclusion: the reworded text, through built products, does what its predictions said on the first case and avoids the due-times misreading twice (07:26, 2026-11-21)

Recorded as received. The runs, instruments and findings are the Ratchet session's, made at the owner's word in
that session; its record is section 21 of `docs/ratchet-pilot-journal.md` (amendment 8, rung 1 and rung 2, and
amendment 9) at commit 17ba721c2a043e5884fe30d58dda5334331e374f on its branch `ratchet-lens-08805f`, not on main.
I read both result sections there and the figures below match them; nothing was re-run here.

What ran: `arms/R-lenses-reworded.md` of this experiment (drafted in section 18 from the first review's findings,
never run here), set into that pilot's enrich stage, Codex gpt-6.2-sol at high. Every later stage's frame gained
one paragraph: an open point is not a requirement, the build takes a reasonable answer and reports it, and no test
pins it.

| its reading | reworded text (R) | lens text (L) | the pilot's own text |
| --- | --- | --- | --- |
| clauses the writer marked as its own choice, five specifications | 0, 0, 0, 0, 0 | 14 to 25 | never fewer than 12 |
| refusals the writer added | 0, 1, 0, 0, 0 | 3 to 18 | |
| `Open:` lines | 8, 7, 10, 8, 9 | 0 | 0 |
| clauses written (orders; ticket assignment; due times) | 26; 43; 30 to 34 | 82; 151; 170 to 197 | 69; 192; 238 |
| orders: clauses whose test fails on a correct product | 2 of 27 (7.4%) | 9 of 82 (11.0%) | 9 of 69 (13.0%) |
| orders: planted defects caught | 4 of 4 | 4 of 4 | 4 of 4 |
| due times: held-out checks passed by the first build | 8 of 8 and 8 of 8 | 3 of 8 and 2 of 8 | 3 of 8 |
| minutes from the request to that build | 20.5 and 18.1 | 28.1 and 31.9 | 32.3 |

In its words, on how the due-times builds passed: "Each specification had left the start open and named both
answers ... Each plan then took the same one as its default for the build and said it was a default ... Each build
report lists the answer it took at every open point ... So the same model family that decided for the refusal four
times in five when it wrote a specification chose the other answer two times in two when the point reached it
open, at planning, with both answers in front of it." And the two failing clauses on orders are the request's own
"has tests" clauses, which that case's reference cannot meet.

Its limits, as it states them: two builds, one model family, and "a text whose author knew this case". That author
is this session: section 18 recorded before any run that R is not blind to the due-times reading. The cells where
a short specification is most at risk (the two ticket cases, 27 and 6 planted defects) were still running.

### The three predictions of section 18, held against it

1. R writes fewer clauses than L on the same case: **held**, on all five specifications.
2. A lower share of R's clauses fail on a correct product: **held on the one case graded** (7.4% against 11.0%).
3. No calibrated defect is lost: **held on orders** (4 of 4); not yet measured on the ticket cases, where that
   session expects the risk to be.

### What it changes here

- **The last lesson of section 28 and its shelf candidate are qualified in place.** On this bench every wording
  that let the writer leave a point open scored as a null, and the one that made it decide scored as a gain. On
  built products it is the other way round: the text that decides nothing passed where every text that decided
  failed. Both can be true, because this bench counts what a specification settles and that instrument checks what
  a product does. It is the plainest evidence yet that the count was measuring the wrong thing.
- **The two sessions' findings now meet at one place, and it is not the spec stage.** Section 26 found that in real
  ShipLoop deliveries on Sol the builder chooses limits and nobody records them. That session reports that in its
  runs "the builder still chooses them ... but the build report lists each one under its discoveries because the
  frame tells it to. So what your census found unrecorded is recorded here, by one sentence in the frame, and is
  not pinned by a test." If ShipLoop is to change on this, the evidence points at what the stages after the
  specification do with a point left open (take a reasonable answer, report it, pin it in no test), not at making
  the specification decide. That is a ShipLoop product question and the owner's; the evidence for it is in the
  other session's record, on its instrument and not on ShipLoop.
- Nothing in sections 26 and 27 changes: they are counts of what was run.

## 30. Received: the pooled result for the reworded text; its three predictions held on the count (08:04, 2026-11-21)

Recorded as received. The runs, instruments and findings are the Ratchet session's. Its record is the subsection
"Rung 3, result, and the readings of amendment 8" in section 21 of `docs/ratchet-pilot-journal.md` at commit
b7c30191e368d337c46c3953c07611deef86ba15 on its branch `ratchet-lens-08805f`, not on main. A Sonnet worker of this
session checked the figures below against that record one by one, and they match; I read its report and spot-checked
ten of them in the source myself. Four of them sit outside that subsection, in its section 20 (the
choice-clause counts of 53 and 48, the 52 of 199 for the pilot's own text, and the pilot's 17 on the second
ticket-assignment delivery); the rest are in the subsection or in the "Rung 2" and "larger cases" subsections it
points to. Nothing was re-run here.

The three test-strength cells are orders, ticket assignment and ticket due times, one run each. The three texts are
the reworded text (R, section 18's arm), the lens text (L) and the pilot's own text.

| its reading | reworded text (R) | lens text (L) | the pilot's own text |
| --- | --- | --- | --- |
| clauses tested, three cells | 102 | 426 | 499 |
| clauses the writer marked as its own choice | 0 | 53 | 48 |
| clauses failing on the correct reference | 8 (7.8%) | 47 (11.0%) | 59 (11.8%) |
| calibrated defects caught | 36 of 37 | 36 of 37 | 37 of 37 |
| second correct ticket-assignment delivery: items failing beyond the reference | 3 | 15 | 17 |
| minutes, three cells | 70.4 | 105.9 | 112.2 |
| output tokens, three cells | 168,562 | 270,820 | 256,223 |
| due times: held-out checks passed by the first build | 8 of 8 and 8 of 8 | 3 of 8 and 2 of 8 | 3 of 8 |
| due times: the loop's own gate after its test pass | 41 of 42; 41 of 41 | | |
| due times: minutes to that gate | 39 and 33 | 58 and 62 | |

In that session's words, the eight clauses of R that fail on the correct reference are none of them an addition of
the writer's, because R's writers wrote no choice clause. Four are the request's own clauses about the tests it asks
for. One is the command-line table, which fails with every text. One was added by the plan stage. Two are sentences
of the request tested at an edge where the reference does not do what the sentence says. On open lines: 25 clauses
in the three cells carry one, and 2 of those fail on the reference; neither failure is about its open point. The
plan stage added three clauses and none settles an open point. Seven of seven specifications written with R have no
choice clause, with 5 to 18 open lines each. The larger cases lost nothing at their first build: chess 10 of 10,
Grokbot-local 49 of 49 and 28 of 28 (23 stated, 5 implied). A Sonnet subagent of that session recounted every figure
of its table from the raw files and all matched.

Two things its record says that qualify the table: the minutes are loose, because its machine's load average was 7
to 8 with five or six runs in flight and the comparison cells ran three to four hours earlier; and one held-out
mark, in one loop's test session, was a process listing that showed another session's command line naming the
installed skill, which it noted and counted.

### The three predictions of section 18, pooled

Section 29 held them against the first case only. On the three cells:

1. R writes fewer clauses than L on the same case: **held.** 102 against 426 pooled, and fewer on each of the three
   cells.
2. A lower share of R's clauses fail on a correct product: **held.** 7.8% against 11.0% over all clauses. Among the
   clauses not `existing`, 8 of 64 (12.5%) against L's 43 of 203 (21.2%) and the pilot's 52 of 199 (26.1%). That
   session had registered 14.1% as the bar for "better" and R is under it.
3. No calibrated defect is lost: **held on the count** (36 of 37 for R, the same as for L) and **not item for
   item.** R misses `update-rejects-resolved` on ticket assignment, a defect in existing behaviour that its short
   specification no longer pins. R catches `cli-no-assignee`, which L missed. Section 18 worded this prediction as
   "loses none of the calibrated defects caught", and it was written about the count. The item-level trade is
   recorded here so nobody reads the result as "nothing lost". The pilot's own text caught 37 of 37.

### What it does and does not add here

- Section 29's reading stands, and it now rests on three cells instead of one. Leaving a point open, with the later
  stages told to take a reasonable answer, report it and pin it in no test, did better on built products than
  deciding it in the specification.
- Its limits, as that session states them: one model family (Codex gpt-6.2-sol at high), one run a cell; only one
  case with a consequential thing left unsaid, and the text's author knew that case; whether the defaults the plan
  takes and reports are what a customer wants is not shown; and nothing here is about ShipLoop's released stage.
  The text's author is this session, which wrote it knowing the due-times reading (section 18).
- This experiment's conclusion (section 28) is unchanged. No ShipLoop template was changed and none is proposed
  here. Any change to ShipLoop on this belongs with that session's evidence and is the owner's to decide.
- That session's message says it is now running a further step with Sonnet 5.5 at high as the writer (R first,
  then L), registered as its amendment 10. That is later than the commit read here, which has no amendment 10, so
  it is recorded as said and not as checked. The result will be recorded here as received when it arrives.
