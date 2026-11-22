You are reviewing the DESIGN of a judging instrument before it is used. Be adversarial and concrete. Context: two ways of building software from one request were each run once on four cases (a Node.js expenses service, a chess rules module, a ticket-assignment change to an existing service, a local chat web app). 'ShipLoop' writes a specification of 300 to 800 words and delivers in 10 to 27 minutes. 'Ratchet' writes a specification of 3,000 to 7,000 words that marks points the request leaves open, builds once (its first build costs the same as ShipLoop's whole delivery), then loops (look at the running product, add requirements, rebuild) to 3 to 7 times the cost. Both products pass every held-out check written from the request. The owner asks: is the heavier product a better quality feature, or is the smaller faster one nearly competitive? The products were built by GPT-6.2 Sol at medium effort. Below are sections 9 and 10 of the experiment journal: what was observed, then the design of a deeper judge. Answer in under 900 words: (1) the three weaknesses most likely to make this instrument give a wrong or unfalsifiable answer, each with the specific fix; (2) anything in the readings D1 to D6 or the 'nearly competitive' rule that can be gamed by size alone (a longer specification or more tests scoring higher without being better) and how to close it; (3) whether the instrument check is strong enough, and the cheapest stronger check; (4) one thing to cut because it will cost much and decide little. Do not restate the design.

## 9. Unstated requirements: who finds them (2026-11-22, the owner's second follow-up)

The owner: "I do wonder if [Ratchet] is better about detecting implicit or unidentified requirements or spec
conditions. Is this the case and should we consider that in both the judge and implemention? Shiploop may do better
at re-planning spec requirements after a pass of the build?"

Status: exploratory. Counts read from the eight runs' own files after the fact, plus one probe of one delivered
product. Nothing registered beforehand; no model ran. Sources under the runs root: `LABEL/work/ratchet/spec.md` and
`delta-N.md` (Ratchet), `LABEL/work/docs/shiploop/spec.md` (ShipLoop).

| Case | Specification words: ShipLoop / Ratchet | Ratchet: points marked `Open:` | Ratchet: clauses it labels implied | Ratchet's after-build looks: clauses added | of those, its own product did not meet |
|---|---|---|---|---|---|
| Shared expenses | 486 / 3,759 | 10 | 11 | 8 | 1 |
| Chess | 336 / 3,172 | 4 | 19 | 4 | 1 |
| Ticket assignment | 310 / 3,794 | 5 | 9 | 10 | 5 |
| Grokbot | 785 / 6,996 | 23 | 11 | 15 | 10 |

ShipLoop's four specifications mark no point as open or as its own choice.

- **L7. Ratchet writes down what the request leaves unsaid; ShipLoop decides it in passing.** On ticket assignment
  Ratchet's specification marks five points for the requester. ShipLoop's specification settles four of them inside
  ordinary requirement lines with no mark ("trimmed single-line agent name of up to 64 characters"; "matches an
  explicit name exactly"; a repeat after an intervening change is news; "Raw output appends the assignee column")
  and does not mention the fifth (what a filter value outside the name rules does; the judge notes the filter value
  is unchecked). Two of the five are the choices the blind judge later picked on (how a name is trimmed and
  counted; the raw column).
- **L8. Marking a point did not make the build better.** No one answers an `Open:` line in an unattended run, so
  Ratchet's builder chose as well. On the name rule the judge preferred ShipLoop's unmarked choice (it follows the
  product's own convention for requesters) to Ratchet's (untrimmed, UTF-16 units). The gain from marking is that a
  requester could answer; these runs had no requester.
- **L9. The after-build looks find shortfalls in a product that passes every held-out check.** Of 37 clauses the
  looks added, Ratchet's own product did not meet 17, by the look's own probe of the running product. Several read
  as defects to me (Grokbot: reloading after a send leaves the draft, and sending it starts a second task;
  asking for `ORD-1001A` answers with `ORD-1001`; two processes on one data folder each confirm `ORD-1005` and one
  is lost. Tickets: a body with a malformed UTF-8 byte is saved as a name). Others are finer than a requester may
  care about (a 20,000-letter ID; a move passed as an object with `toString`). This corrects L2's wording: about
  half of what the later cycles added named something the product did not do. Not judged by an outside reader
  here; the pilot's outside judges accepted 10 of 59 additions written under the earlier specification text.
- **L10. The look is cheap; the cycle it starts is not.** The three looks of a run took 4.8 to 11.0 minutes
  together (`seconds_by_role.delta`: 289 to 662 seconds), 1.6 to 3.7 minutes a look. The 29 to 142 minutes after
  the first build went to the rebuilds and the test passes the looks set off.
- **Probe, ShipLoop's delivered ticket product against Ratchet's ticket finds** (a copy in the scratchpad, started
  on a free port, 2026-11-22 13:44 UTC): the detail view shows the current assignee (Ratchet's C-45: ShipLoop
  already right); a clear is logged as `ticket.unassigned` (C-49: already right); a body holding byte `0xFF` in the
  name returns 200 and saves the name with a replacement character (C-50: same gap); `?assignee=Da%FFna` returns
  200 and matches that ticket (C-52: same gap). C-51 (a name containing the handoff separator) was not tried. So of
  four finds tried, ShipLoop's product shares two.

### What this means for the measures

Neither instrument here can see any of this. The held-out checks cover what the request states and sit at the
ceiling; the judge read code and tests and was not asked what the product does where the request is silent, nor
whether a choice was told to anyone. A tool earns nothing for marking a point and loses nothing for choosing
silently. A measure that could see it: per case, a list of conditions the request leaves unsaid, fixed before the
runs from sources independent of both arms, each probed on the running product and scored handled / chosen and
told / chosen silently / not handled. It is scored on the product and on what the requester is told, never on the
length of a specification (the spec-elaboration study's lesson: a count over a specification rewards deciding).
The 42 `Open:` lines and 17 shortfalls above could seed such a list for these four cases only after an outside
reader has kept the ones a requester would care about, since a list written by one arm favours that arm.

### Not shown

Whether a requester would want any of the 17; whether ShipLoop's other three products share Ratchet's finds (one
case probed, four finds); whether one look after ShipLoop's build, reported to the requester and not rebuilt
automatically, finds as much on ShipLoop's products. That last is the cheapest next test: four sessions of a few
minutes on the four delivered ShipLoop products, then two outside judges on the findings.

## 10. The deep judge: design, registered before it reads any product (2026-11-22)

The owner: "Help me do both: improve the judge first to deeply analyze the quality of feature, examining the spec,
tests and build with a lot more finesse to determine if there is a better quality product built or the smaller
faster version is nearly competitive to a lot of specification like ratchet". "Both" is section 9's two offers: a
measure that can see what a product does where the request is silent, then one after-build look on ShipLoop's
products (section 11, to be registered when this judge has been proven).

### Why the first judge is not enough

It read code and tests as text, gave five 1-to-5 scores and a preference, saw no specification and ran nothing.
It could not say what a product does where the request is silent, whether a test pins a requirement, or whether a
defect it suspected is real. It compared final products only, so it could not separate what Ratchet's long
specification buys at ShipLoop's cost from what its later cycles buy.

### What is judged

Three products a case, twelve in all: **S**, ShipLoop's delivery; **F**, Ratchet's first build (the same cost as S,
section 8); **L**, Ratchet's final (3 to 7 times the cost). S against F asks what the long specification buys at
equal cost. F against L asks what the later cycles buy. S against L is the owner's question.

### Steps (apparatus: `deep_judge.py`; every model's answer is a JSON file kept as evidence)

1. **Case inventory, written without seeing any product.** Two listers of different families (Opus; Grok), each
   from the request alone (and the starting files, where the case has them), write (a) the stated requirements as
   separate checkable items and (b) the conditions the request leaves unsaid that a requester, an operator or the
   next maintainer would plausibly care about, each with a way to observe it on a running product. One session
   merges the two lists and a third list, the points the arms themselves raised (Ratchet's `Open:` lines and
   after-build clauses, the first judge's remarks), removing duplicates and recording each item's sources. Then
   both families rate every unstated item without seeing its source: `must`, `should`, `no` (a requester would not
   care, or it is over-engineering). An unstated item is **kept** when both rate it `must` or `should`. Results
   are reported for all kept items and again for the items an independent lister raised, since an item only an
   arm raised may favour that arm.
2. **Product audit, one product at a time.** An auditor (Opus) is given the request, the starting files, the
   inventory and one product under a code name. It is not told another product or any tool exists. It must run the
   product and its tests in its own copy. For each stated item: built (`yes`, `partly`, `no`, `wrong`) with the
   command and output that shows it; whether the product's own specification states it; whether a test pins it
   (`strong`: the named test would fail if the item broke; `weak`; `none`). For each kept unstated item: what the
   product does (observed), how sound that is (`sound`, `acceptable`, `poor`, `unhandled`), whether its
   specification marked the point open, decided it with a mark, decided it without one or is silent, and whether
   the choice is told to a reader of the product's documents. Then findings outside the inventory: defects with an
   exact reproduction, things built beyond the request (`value`, `neutral`, `liability`), tests tied to internals
   or to one product's choices, and what a maintainer would find hardest.
3. **Cross-probe.** Every defect any auditor reports for any product of a case is tried, by its reproduction, on
   the case's other products by a separate session, so a defect counts against every product that has it and not
   only the one where it was noticed. A defect whose reproduction does not reproduce on its own product is dropped.
4. **Verdict.** Two judges of different families (Opus; Grok) get the three audits and the defect table of a case
   with tool names masked and letters assigned by a seeded coin; no times, no token counts. For each pair they
   answer on a five-step scale which is the better feature for someone who will run and maintain it, name each
   advantage with the audit line behind it and whom it matters to (requester, operator, maintainer, no one), and
   answer one fixed question: could one short follow-up task (about an hour of the same builder's work) close what
   the lesser product lacks. A pair is decided only where both judges agree on the side.

### Instrument check, before any of the twelve is audited

The ticket case has a correct reference and 27 calibrated single-edit defects (`grade.build_variant`). The audit of
step 2 is run on the reference and on three defects drawn by a seeded choice
(`random.Random("deep-judge calibration").sample(sorted(defects), 3)`), under code names. **Bar:** the audit marks
no stated item `no` or `wrong` on the reference, and reports the planted defect (as a stated item `no`, `wrong` or
`partly`, or as a defect with a reproduction) in at least two of the three. If the bar is missed the audit text is
revised once, the change is recorded here, and the check is rerun on three newly drawn defects.

### Readings (margins fixed now; "ahead" needs the margin)

| | Measure | Ahead when |
|---|---|---|
| D1 | Stated items built `yes` | 2 items more |
| D2 | Stated items with a `strong` test | 2 items and 10 points more |
| D3 | Kept unstated items handled `sound` or `acceptable` | 2 items and 10 points more |
| D4 | Of the unstated items where the product chose, the share whose choice is told (marked in its specification or stated in its documents) | 2 items and 10 points more |
| D5 | Defects that reproduce, severity high or medium, after the cross-probe | 2 fewer |
| D6 | Verdict of the two judges on the pair | both agree on the side |

Per case and pair, the product ahead in at least two more of D1 to D6 than the other is **the better feature**;
otherwise no difference shown. **Nearly competitive:** S is nearly competitive with L in a case when the pair shows
no difference or S is better, or L is better and both judges answer that one short follow-up task closes the gap.
Things built beyond the request and maintainability notes are reported, not counted (one auditor's opinion).

### Predictions

- Q1. The instrument check meets its bar at the first attempt.
- Q2. D1 is level for every pair in every case (the held-out checks already say so).
- Q3. L is ahead of S on D3 in at least two cases; S is ahead of L on D3 in none.
- Q4. F is level with L on D1 to D3 in at least three cases (what Ratchet has, it has at its first build).
- Q5. Neither arm is ahead on D4 anywhere when "told" means the product's documents; counting marks in the
  specification, F and L are ahead of S in at least three cases.
- Q6. L has fewer reproducing defects than S (D5) in at least two cases.
- Q7. S is nearly competitive with L in at least three of four cases.
- Q8. Of the unstated items only an arm raised, fewer than half are kept by both raters.

### Limits known now

One auditor a product, one family (Opus); an audit is an observation by a model, and only its defects are
re-run by another session. The inventory's unstated list is what two models thought of plus what the arms raised;
it is not what this requester would say. The judges see the audits, not the products. The products were built by
Sol 6.2; the listers, raters, auditors and judges are other families (the pilot's section 13: the author's family
accepts three times what outside judges accept). Still one run a case.
