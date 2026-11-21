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
5. **The instrument**: four frozen requests, an 89-item checklist, a coverage judge calibrated on two layouts and
   re-read by a second family, a clause audit, a pre-flight that proves what a Codex session is shown, and a leak
   check. Its known faults are recorded where they were found: the judge scores a stated exclusion or an open
   item unevenly, so `covered` rewards deciding; the checklist and the lenses share an author; a subject can
   still reach a judge's folder.

Open and the owner's:
- Whether a specification should decide more of what it reaches. The request that started this asked for a
  verbose, elaborated specification; the released stage's duties tell it to leave some things open and out. The
  lens arms without those duties wrote what the request described. That is a choice about what the stage is for.
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
