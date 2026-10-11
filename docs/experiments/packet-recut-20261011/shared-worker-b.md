# Shared texts: re-cut draft (worker B)

## STAGE_RULES (printed last in "What you work from")

```
Rules (long form: reference#rules, #requirements, #progress):
- Do only this stage, then run the callback and follow the packet it returns. ShipLoop owns the graph and the next
  step. Preserve unrelated work.
- Unattended: nothing arrives on standard input. Take the default that best fits the request and the recorded
  knowledge, and record it in the summary as an assumption with the alternatives and why. Record a step only a person
  can do (a sign-in, a grant) as an open item: who does what, and what they report back. Then continue. Report
  blocked only when nothing can proceed without a person. A problem this run can fix, such as a documented command
  that does not run what it claims, is fixed here and rerun.
- Base test, build and release claims on what you observed. Recheck notes, Git history and prior results against
  the repository before relying on them. A missing prerequisite, permission or trustworthy check is unresolved,
  never N/A. A justified N/A says what you assessed and why it does not apply.
- Requirements come from HOME/spec.md. Keep unaffected ones. Never relax one to match code or tests. Current
  explicit user instructions supersede older clauses. Keep each requested runtime and entry point; a local fixture
  cannot stand in for a target capability. Put the requirement sections and test locators you used in
  evidence_refs. Report a missing source instead of inventing one.
- Temporary files go in RUN/scratch, never /tmp. Discover identity or access only with supported non-mutating probes
  and sanitized evidence. Never read, decode, keep or report local authentication, session or credential-store
  contents.
- Run each ShipLoop command in the foreground with unpiped output, and never end the turn while one runs. A
  `complete` that reruns tests can take minutes. If a keepalive hook refuses to end the turn, run the command it
  names.
- Tell the user one line per stage: the item, the stage finished, the stage starting. Paste a ShipLoop narrative as
  its first line says. A question about the run is not a stop. A request to stop, pause or not implement runs Pause.
```

Today 2,251 characters; new about 2,000. Every obligation is kept; the cuts are wording. Map:

| Today's sentence (short) | New home |
|---|---|
| Do only this stage; run callback; follow returned packet; ShipLoop owns graph; preserve unrelated work | Rule 1 |
| Unattended; default + assumption; person-only step as open item; blocked only when nothing proceeds; fix fixable here | Rule 2 |
| Recheck notes, history, results; observed claims; unresolved never N/A; justified N/A | Rule 3 |
| Requirements from spec.md; keep unaffected; never relax; user supersedes; runtime and entry point; evidence_refs; missing source | Rule 4 |
| RUN/scratch not /tmp; non-mutating probes; never credential-store contents | Rule 5 |
| Foreground, unpiped, never end turn; complete takes minutes; keepalive | Rule 6 |
| One line per stage; narrative; question is not a stop; stop/pause runs Pause | Rule 7 |

## Until-loop line (from _LOOP_DUTY; one home in "What to execute" for every inner stage)

Every inner duty today opens with _LOOP_DUTY (302 characters). The drafts drop it from the duties. The renderer
prints it once beside the /until-loop block, merged with the receipt lines it already prints:

```
ShipLoop wrote the loop contract; do not edit it. Call an exit condition satisfied only when a command or file shows
it after your last edit. If ShipLoop refuses done after the loop ends, fix the cause, start the loop again with the
same command, and submit again.
```

## TEST_FACILITY_HANDOFF

Proposal: the stages worker B owns fold it into their duties (test-spec item 5, test item 1, carry-forward items 1
and 2), so `prompt()` skips it for step-plan, test-spec, test and carry-forward, as it already does for step-plan.
It stays printed for plan, test-strategy, system-test-author and release-plan, in this shorter form:

```
Test facilities (Reusable test facilities): reuse, configure or extend the existing frameworks and helpers before
defining the smallest missing facility. Read the selected skill and MCP references first; never assume a named skill
or MCP is available or authorized. Record each facility's definition locator, interface, readiness or gap, owner and
revalidation condition in the repository test documentation and in evidence_refs. A stage that writes work_items
also puts the locator in the affected item's context. The stage that owns missing prerequisite work builds and
validates it, within its scope, before the checks that depend on it. Readiness is not test execution; a later stage
reopens the recorded definition instead of inventing another facility.
```

Today 807 characters; new about 700. The `improves` variant in `prompt()` (which strips the Improve sentence) goes
away: the new text never names Improve.

| Today's sentence (short) | New home |
|---|---|
| Read skill and MCP references; reuse before smallest new; never assume available or authorized | Sentences 1-2 |
| Record locator, interface, readiness, owner, revalidation in evidence_refs and test docs | Sentence 3 |
| Carry locators into item context and the Improve child's notes | Sentence 4 (item context only, for the stages that can write it); Improve CUT (R3) |
| Planning names missing prerequisite work; owning stage builds and validates within scope | Sentence 5 |
| Discovery or readiness is not execution; later test reopens the definition | Sentence 6 |

## TEST_DECISION_HANDOFF

It is printed only for test-spec and test (step-plan already skips it). Both drafts fold it (test-spec item 7, test
item 2), so the proposal is to stop printing it. Keep the "test-decision" block in the stage table: the navigator
uses it to print the run-wide test strategy source. If the main session prefers one shared copy, use:

```
Test decisions: reopen the item's test decision and HOME/test-strategy.md. In the summary, say which decisions you
retain, refine or supersede, and why; put their locators and the step plan's in evidence_refs. Reassess a missing
decision here. A recorded completion does not prove a harness, fixture or target still works.
```

Today 560 characters; new about 330. Cut: "and the coding-guidance sections it used" (neither test-spec nor test selects
coding guidance); "and the test notes" (the summary is the one home).

## CODE_CRAFT

Keep the nine rules unchanged. Print it once, whole, in "What you work from", after the cited guides and before the
rules, for implement, test, document and verify. The duties cite it as "Code craft" (implement item 2, verify items 5
and 7). Today it sits between the duty and STAGE_RULES, which places 3,688 characters of reference text inside "What
to do".

## Gaps found in the shared layout and the source

1. **`skill.index` is unprinted.** `_skill_commit` (shiploop_navigator.py) commits `skill["index"]` files with the
   skill, and carry-forward.md documents `index`, but the result template and the `_check_skill_decision` message
   omit it. An index outside HOME/ and SHIPLOOP.md is never committed. Add `"index": ["<index file outside HOME/ and
   SHIPLOOP.md>"]` to the template.
2. **`follows` has no duty sentence.** The step-plan gate refuses a missing `follows`, but today's duty never asks for
   it. The draft adds step-plan item 8.
3. **step-plan cannot write an item's `context`.** Today's step-plan item 4 says to carry a facility locator "into
   item context", but only plan and carry-forward replace `work_items`. The draft records it in the plan note.
4. **Deterministic skills are not checked.** The gate checks only SKILL.md frontmatter and evidence. If the owner
   wants the script and the trial enforced, `_check_skill_decision` could also require, for update and create,
   `RUN/notes/<action>-skill-trial.md` to exist. A required `scripts/` directory would refuse judgement-only skills,
   so I do not propose that.
5. **Guide labels read by Improve.** `_improve_prompt` adds paragraphs keyed on the labels "State and data
   assessment" and "Release operation guidance", and a Coding decision paragraph by stage name (step-plan,
   implement, verify). Dropping an uncited label from a producer packet silently removes or orphans the Improve
   paragraph. The R7 Improve packet may make this moot. If it does not, keep those labels.
6. **Work lines point at duty items.** Each proposed `WORK[stage]` names "duty items n-m of
   {run}/packets/{action}.md". If the packet's numbering changes, the Work line must change with it. A test can pin
   it: every "duty items n-m" range in WORK must exist in the rendered duty.
