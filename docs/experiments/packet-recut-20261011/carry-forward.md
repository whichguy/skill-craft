# carry-forward: re-cut draft (worker B)

## 1. Goal (R1)

Close the item: update the knowledge home in place, write the future queue in `work_items` when it changes, and
record the reusable-skill decision in `skill`, creating or updating a repository skill under item 3's rule.

## 2. Duty

1. **Knowledge home.** Update in place, and keep completed evidence apart from future plans; never rewrite it:
   - HOME/environment.md ## Commands: every command that worked.
   - HOME/architecture.md ## Decisions: each AD-<n> this item added. A superseded one moves to ## Superseded; never
     delete it.
   - HOME/test-strategy.md ## Harnesses and suites: the suites; focused, smoke and full commands; harness and case
     locators; fixture lifecycle decisions; each test facility's locator, interface, readiness or gap, owner and
     revalidation condition; pending full-suite and real-boundary checks with owner. Keep the originating strategy
     locator beside them.
   - HOME/spec.md: each R-<n> this item satisfied, with its test IDs; an open gap under its R-<n>. Keep unaffected
     clauses.
   - FEATURE/plan.md ## Open: open risks, unresolved dependencies, system-test obligations and release
     prerequisites, each with an owner, and any observation no item owns.
   - Carry the selected prior baseline, incoming delta and updated knowledge locators forward, keeping historical
     snapshots (Current-system baseline guide). Retain the house style (House-style guidance) and the learnings
     the next run needs (Persistent project-knowledge guidance).
   - Do not silently expand scope or turn a tentative idea into adopted policy.
2. **Queue** (Carry-forward mapping guidance). Read RUN/state.md `work_items`, every pending title and context, and
   give every observation that affects later work an owner:
   - A defect in completed work, or a completed prerequisite that new evidence invalidates: a corrective item, with
     revalidation, ahead of its consumers.
   - A needed research or preparation prerequisite: its own item ahead of every consumer.
   - An affected future item: its `context` carries the decision locator, rationale and revalidation condition.
   - A finding incompatible with the approved work (a changed requirement, permission or invocation contract): stop
     the loop and report blocked. It is not a queue edit.

   To change the queue, give `work_items`: the whole future queue, rows `{"id", "title", "context"}` in prerequisite
   order, with no completed or current ID. Keep unrelated pending work that has no consumer. Explain each removal,
   merge or supersession in FEATURE/plan.md ## Open. Omit `work_items` to keep the queue as it is.
3. **Skill decision**, in `skill`:
   1. *Inspect.* Read the repository skill index (the directory HOME/environment.md ## Skills names, or the
      README or AGENTS.md skill links; a missing index is not a blocker), SHIPLOOP.md and the skills your host
      offers. Put what you inspected in evidence_refs.
   2. *Decide*, smallest first (Reuse-before-build guidance, Repository-local skill guidance):
      - `none`: no procedure repeated, or a normal code, test or doc change already captures the learning.
      - `reuse`: an existing skill covers it unchanged. Different data or parameter values alone do not need
        another skill.
      - `update`: a small compatible extension of a repository skill captures a demonstrated lesson. Keep its
        supported inputs, defaults and older examples.
      - `create`: no suitable skill exists, or combining contracts would obscure selection or break a consumer.

      Choose `update` or `create` only when the same procedure ran in two or more steps or items of this run, or a
      pending item or R-<n> says it will recur. Put those step or item IDs, or the R-<n>, in `skill.evidence`.
      Never capture a transcript of this step or a speculative framework.
   3. *Where.* Use the repository's skill directory (HOME/environment.md ## Skills, or the existing layout). When
      there is none, use `skills/<name>/` in WORKTREE and add it under ## Skills. Never edit an installed or shared
      skill, install globally, add a dependency, connector or privilege, or publish. Derived content keeps its
      source, revision and licence.
   4. *Write it deterministic.*
      - `skills/<name>/SKILL.md` opens with `name` and `description` frontmatter. The description says when to use
        it and when not to.
      - The body gives: what it produces and why; each input with its type, whether required, its default and where
        the default comes from; the exact steps; the expected output; failure and recovery; permission boundaries;
        relative links to the code, tests and HOME/spec.md sections it relies on (link requirements, never copy
        them); and what changes require revalidation. No credentials, machine-specific paths or IDs, and no run or
        worktree paths.
      - Every mechanical sequence goes in a script beside it, `skills/<name>/scripts/<verb>`, in a runtime the
        repository already uses. The script takes its inputs as arguments, exits 0 on success and non-zero with a
        named message on each failure, and prints the output SKILL.md describes. SKILL.md runs the script and does
        not restate its logic. A step that needs judgement stays in SKILL.md as a numbered instruction with its
        decision rule.
      - Task-specific values stay in evidence. The skill keeps the rule and its default.
   5. *Prove.* Run the skill once on this run's real procedure. Write the command, its exit code and its output to
      RUN/notes/<action>-skill-trial.md. An update also runs one retained older use. The trial note says whether a
      fresh reader (given only the index, the skill and a new task) tried it, or says "cold-context reuse
      untested". Presence or installation is not proof it runs.
   6. *Register.* Add a line with the skill's path, when to use it and its inputs to the repository skill index and
      HOME/environment.md ## Skills, and link it from SHIPLOOP.md. List any index file outside HOME/ and SHIPLOOP.md
      in `skill.index`.
   7. *Record.* `skill` = `{"decision", "reason", "path", "evidence", "index"}`: `path` is the SKILL.md for
      `update` or `create` (name a reused skill in `reason`). Put the trial note in evidence_refs. On accept,
      ShipLoop commits the skill directory and the `index` files as their own commit.

   Revalidate an earlier skill selection for each new task: a prior selection or passing trial is an input, not
   authority.
4. **Commit nothing.** On accept ShipLoop commits HOME/ and SHIPLOOP.md (and the skill, item 3.7).

## 3. Checked by

- A missing skill decision, or a reason that is empty.
- For `update` or `create`: a `path` that is not an existing SKILL.md with `name` and `description` frontmatter, or
  empty `evidence`.
- `assumptions` missing, or an open item whose consumer is not a later outer stage.

## 4. Guides to keep

Current-system baseline guide; Carry-forward mapping guidance; Persistent project-knowledge guidance; House-style
guidance; Reuse-before-build guidance; Repository-local skill guidance; Backchain planning guide (inline audit) or
the Backchain guidance (ask-agent), unchanged.
Drop: State and data assessment (not cited). **Unsure:** `_improve_prompt` keys its State and data paragraph on this
label; dropping it removes that paragraph from carry-forward's end-of-work Improve.

## 5. Loop Work (shiploop_loops.WORK["carry-forward"])

Today's Work restates items 1-3 (about 1,500 characters). Replace it with:
"Do duty items 1-3 of {run}/packets/{action}.md; write the skill trial to {run}/notes/{action}-skill-trial.md."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| Read RUN/state.md work_items | 2 |
| test-strategy also records harness/case locators, fixture lifecycle, pending full-suite checks, beside strategy locator | 1 |
| plan.md ## Open also records unresolved dependencies | 1 |
| Keep completed evidence apart; never rewrite it | 1 |
| Do not silently expand scope or adopt a tentative idea | 1 |
| Carry baseline, delta, knowledge locators; keep snapshots | 1 |
| Queue: read before revising; keep unrelated pending work | 2 |
| Invalidated completed prerequisite: corrective item with revalidation ahead of consumers | 2 |
| Observation no item owns: plan.md ## Open | 1 |
| Explain supersession, removal, merge there | 2 |
| work_items replaces the whole queue; row shape; order; no completed/current ID | 2 |
| Incompatible finding: stop loop, blocked | 2 |
| Skill: record decision, reason, what inspected, evidence | 3.1, 3.7 |
| Prefer unchanged reuse | 3.2 (smallest first) |
| Link created/updated skill from SHIPLOOP.md and index | 3.6 |
| Update's trial also runs an older use | 3.5 |
| Trial note: fresh reader or "cold-context reuse untested"; presence is not proof | 3.5 |
| Task-specific values in evidence; revalidate earlier selections | 3.4, closing line of 3 |
| ShipLoop commits HOME/, SHIPLOOP.md, skill directory and index; commit nothing yourself | 3.7, 4 |
| End-of-work Improve child; rerun of recorded commands; moves to new last item | CUT: advance Improve mention (R3, R7) |
| Consideration Develop: learnings and conventions; skill only for repeated procedure no skill covers | 1, 3.2 |
| Consideration Test: rerun procedures in repository test documentation | 1 (test-strategy commands) |
| TEST_FACILITY_HANDOFF: reuse before smallest new; never assume skill or MCP | Not this stage's work (carry-forward builds no facility); CUT here |
| TEST_FACILITY_HANDOFF: record locator, interface, readiness, owner, revalidation | 1 (test-strategy line) |
| TEST_FACILITY_HANDOFF: carry locators into item context | 2 (affected item's `context`) |
| TEST_FACILITY_HANDOFF: Improve child notes | CUT (R3) |
| TEST_FACILITY_HANDOFF: owning stage builds; readiness not execution; later test reopens | CUT here: no build at this stage; the shared block keeps it for planning stages |
| WORK_ITEM_CONTEXT: only compact locator, decision, rationale, scope, revalidation in notes and context; sources in evidence_refs; no transcripts, no ledger; summary is not proof | 2 (context contents). **Unsure**: "no transcripts, no decision ledger, a summary is not proof" is not restated; keep WORK_ITEM_CONTEXT printed if the main session wants it (it is shared with plan) |
| Work: environment Commands, architecture Decisions and Superseded, test-strategy, spec R-<n> with tests | 1 |
| Work: plan ## Open with owners | 1 |
| Work: read work_items; map observations; corrective and prerequisite items; explain removals | 2 |
| Work: skill: read index or links (missing not blocker), host skills; none/reuse/update/create | 3.1, 3.2 |
| Work: create/update only on repeat or recurrence, no existing skill | 3.2 |
| Work: keep in repo (## Skills names directory); never install globally, add dependency, publish | 3.3 |
| Work: link from index; run once; output to notes/<action>-skill-trial.md | 3.5, 3.6 |
| testing-and-documentation.md#reusable-product-skills: smallest disposition list | 3.2 |
| same: `skills/<name>/SKILL.md` when no layout; inside the worktree | 3.3 |
| same: copying external skill keeps source, revision, licence | 3.3 |
| same: useful skill documents name, when, why, inputs, procedure, outcomes, failure, permissions, links, revalidation | 3.4 |
| same: link requirements, never copy; no run/worktree paths | 3.4 |
| same: expose through index, README or AGENTS.md; name future consumer | 3.6 |
| same: validate motivating and older use, cold-context trial | 3.5 |
| carry-forward.md: `index` in the skill record | 3.6, 3.7 (**added**: the template and gate message omit it, but `_skill_commit` commits `index` files) |

## 7. Size

- Today: duty 2,506 + TEST_FACILITY_HANDOFF 807 + WORK_ITEM_CONTEXT 327 + considerations 218 + Work 1,535 = 5,393
  characters.
- New: 6,900 characters. It grows because the owner asked for the concrete, deterministic skill procedure
  (item 3 is about 3,900). The Work line drops from 1,535 to about 130.
