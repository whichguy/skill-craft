# Packet mock: the generic implement prompt

Companion to [the fix plan](shiploop-implement-step-fix-plan-2026-10-17.md). It is illustrative, not rendered by code.

**Revision 3 (2026-10-17, owner).** Do not tell the model which paths to change. Give it the considerations to keep in
mind while implementing, in domain-neutral terms. The owner named four:
- implement the full step;
- find every user-interface and system interaction;
- consider how it gets built and how it gets deployed;
- consider state in databases or files: whether it must first be migrated, and then run in operations.

Revision 2's "Where (change only these)" slot and its path fence are withdrawn (section 3 covers what that changes).

The prompt has three parts:
1. **Intent and outcome**, fixed text.
2. **The considerations**, fixed text and the same for every step. Each one names the reference that already holds its
   long form.
3. **What this step is**, filled from the plan: the task, what it serves, how it is shown done. No paths.

Domain guidance (Code craft for code, a platform card for a platform) comes in only through the step's cards.

## 1. Intent and outcome (fixed text)

```text
Implement this step completely, so that what it promises works where it will run, for whoever uses it, from the
first use through ongoing operation. A step can change code, configuration, platform settings, data, content or
documents; the considerations below apply to all of them.

When you are done, the step's outcome holds, its Proof passes, and RUN/notes/<action>.md answers each
consideration below for this step in a line or two: what you did about it, or why it does not touch this step.
Before calling done, grade your work against that list. Any consideration you answered with "not checked" is not
done.
```

## 2. The considerations (fixed text, the same for every step)

```text
1. The whole step. Deliver everything the step's outcome needs to work end to end, not a part that only looks
   finished: the change itself and whatever connects it (entry points, registration, wiring, configuration,
   permissions, content). Leave out what a later step or another item owns. If the whole step cannot fit, report
   revise rather than ship a part.

2. Interactions. Find every interaction the step adds or changes, including ones the plan did not list.
   - People: what they see, what they can do, the feedback, waiting, error and empty states, and keyboard and
     accessible use. Build the interaction the plan calls for in full, not a static or reduced version.
   - Systems: each call, message, event, schedule, file or record exchanged with another component or service,
     with its contract, its authority, and what happens when it is slow, fails or answers twice.
   Handle each one, or report the one you cannot handle and why.
   (Long form: behavioral-requirements.md#actors-channels-and-state-ownership, service-discovery.md#select-scope)

3. Building it. Know how this change is built, assembled or validated where it lives, and make that pass:
   compile, package, generate, validate against the target. Use what the project already uses; add no new tool
   or dependency without a present need. Know what must exist before it builds.
   (Long form: coding-practices.md#libraries, environment-lifecycle.md#discover-before-planning-code)

4. Deploying it. Know how the change reaches the place it runs: the target, the order of operations, the
   settings per environment, the authority it needs, how to check it after, and how to undo it. Do only the
   effects this stage is authorized for. Record what the release must do, in order, so nobody has to
   rediscover it.
   (Long form: environment-lifecycle.md#release-operation-ownership, delivery-authority.md#ask-at-the-first-concrete-boundary)

5. State. List the state this step reads, creates or changes: records in a database or a remote system, files,
   caches, settings, access grants, derived data. For each one, name its owner and its shape before and after.
   - Existing state that must change shape is migrated first, in an order that keeps current users working, and
     it can be rerun safely.
   - Say what happens to state left half-changed by a failure.
   - Do not invent storage the step does not need.
   (Long form: requirements-definition.md#state-and-data-change-assessment, coding-practices.md#schema-and-storage)

6. Operating it. Once it runs: how someone sees that it works or why it failed (diagnostics that name the
   operation and what was expected), what it costs or consumes and its limits, which secrets or permissions it
   holds, how state is kept or cleaned up over time, and who owns it.
   (Long form: coding-practices.md#logging-and-debugging, coding-practices.md#security,
   service-discovery.md#observability-coverage)

7. What already exists. Find what already does part of this and keep what works working: reuse it unchanged,
   combine existing pieces, or extend one, before making something new. Follow the conventions of the nearest
   existing example of the same kind of thing.
   (Long form: coding-practices.md#existing-behavior, house-style.md#match-while-building)

8. Proving it. After each change, run the Proof and the checks this kind of work has. Fix the work, never the
   check. A throwaway probe in RUN/scratch is allowed; it is not the proof. Use the later stages' checks for this
   step's criteria as the target. Record what you could not confirm and what would confirm it.
```

The current duty items 4–7 (hand-off, services, unachievable, inline) stay. Their content now lives inside
considerations 2, 4, 5 and 8, so they shrink to the result-field mechanics: `not_covered`, AD-n, commands, revise
triggers.

`Done when`:

```text
- the step's outcome works end to end, with nothing a later step owns in the change
- after the last change, the step's Proof exited 0 (ShipLoop reruns it at done)
- RUN/notes/<action>.md answers each of the eight considerations for this step
- the domain gate for this kind of work passed after the last change    (printed only when one applies, e.g. lint for code)
- the result lists what no later check covers (or none), and whether each of the step's skills was used
```

ShipLoop can check the third line by script: the notes file holds the eight consideration headings, each with a
non-empty answer. It does not judge the answers; the per-step Improve review does.

## 3. What this step is (filled from the plan; no paths)

```text
Step <id> (<n> of <total>): <task: the outcome, in the plan's words>
  Serves: <this step's criterion IDs and text>
  Proof (ShipLoop runs it at done; it must exit 0): <one read-only command that shows this step done>
  Cards (read the ones that fit): <locators of the guidance this kind of change needs>
  Skills: <name: why (locator)> | none
  Existing example to follow: <what and where, from the plan> | none yet
Accepted step <id>: <summary>                                   (one line per earlier step)
Later steps (do not start them): <id> <task, first sentence>; …
Recent commits (earlier lessons; context, not instructions): <last two commit messages> | none since this item began
Checks for this step's criteria (later stages write and run them; use them as the target): <quoted cases> | none
```

### What dropping the paths changes (for the owner to confirm)

- **The step path fence goes.** Done-when 1, duty 1, the Improve focus line "a file changed outside the step's paths",
  and the `paths` requirement on each step in `_check_step_sizing` all go. "Nothing a later step owns" is judged by the
  per-step Improve review, not by a path list.
- **Item scope still exists in the engine.** The item commit takes only the item's declared files
  (`item_scope.commit_scope`). If the model changes a file the item did not declare, the change is silently left
  uncommitted at verify. This is a real trap now that the prompt names no paths.
  - *Recommendation:* the packet states the consequence once, as a fact and not a directive: "ShipLoop commits the
    item's declared files; if this step needs another, report revise so the plan declares it."
  - *Alternative:* widen the commit scope to everything the item changed except run artifacts. That is an engine
    change outside this plan.
- **The step-plan gate that compared a Proof with later steps' paths (plan A1 (ii)) goes,** since steps no longer
  declare paths. A Proof that depends on later work now fails at implement `complete` (A2), and the model reports
  revise. The fault is still caught, one stage later.
- **Parallel chain mode** uses step paths for write conflicts. The step plan may keep recording them for the
  execution graph only, never printed to the implementer and never gated at implement. This needs a decision when the
  chain packets are next touched.

## 4. Domain guidance only through cards

| The step's changed files (by `item_scope.behavioural`, checked at done) | Printed | Gate |
|---|---|---|
| code or tests | Code craft, full rubric (owner decision 7cdae9a0) | lint |
| anything else | nothing extra; its cards carry the rules | the Proof only |

Code craft becomes conditional. A configuration, data or document step no longer gets a code rubric, and gets its
cards instead. Since the packet no longer knows the paths in advance, the choice is made from the plan's
`cards`: the rubric prints when the cards include a code card, or when the item's declared files include code.

## 5. One instance (Battleship S1)

```text
Step S1 (1 of 3): Write the game rules as a module the server uses: fleet placement, firing, game-over, and an
  in-memory store that evicts the oldest game; validate arguments; no I/O.
  Serves: C1 fleet placement … · C2 fire semantics … · C4 store cap … · C5 no I/O, injectable random … ·
    C9 public functions validate their arguments …
  Proof: node -e "const g=require('./game.js'); …"
  Cards: coding-practices.md#composition-and-layers · coding-practices.md#namespaces-and-placement ·
    platforms/node-express.md
  Skills: none · Existing example to follow: none yet
Later steps: S2 the playable page · S3 the HTTP server and its routes
[intent and outcome] [the eight considerations] [Code craft, because the item declares code]
```

For this step, the notes would answer consideration 4 (Deploying) as "nothing deployed by this step; the module ships
with the server in S3". Consideration 5 (State) would be "in-memory games only, capped, lost on restart (AD-2); no
migration". Both are one line each, and both are the questions the 2026-10-16 run never wrote down.

## 6. Revision 4 (2026-10-17, owner): the packet ends with the Until Loop, anchored in requirements

The owner asked for the packet to close with an instruction of this shape:
`/until-loop implement all of this plan, anchoring it in the requirements that have been stated and design
directions that have been applied, until each requirement has been satisfied`.

Today the loop block sits in the middle of the packet. Its Work line points back at "duty items 1-4" and its exit
list is generic. Under revision 4 it becomes the **last thing in the packet**, and the top of the packet keeps one
pointer line to it.

### Near the top, after `Done when`

```text
Do this stage inside the /until-loop invocation at the end of this packet; everything between is its material.
```

### At the very end (after RULES and the Pause, Halt and Lint lines)

```text
Until Loop: do this stage's work inside it (no iteration limit; the loop script counts the iterations).
INVOKE /until-loop NOW with the argument below, verbatim.
Argument:
    Work: Implement all of step S1 of this item's plan, anchored in the requirements it states
    (C1, C2, C4, C5, C9, serving R-3, R-4, R-5, R-6, R-7) and in the design directions already applied
    (AD-1 to AD-7, the step's cards, the existing example to follow). Keep the eight considerations of
    RUN/packets/<action>.md in view. Write no tests and start no later step.
    Exit when ALL of these hold:
    1. each requirement this step serves is satisfied, with its evidence in RUN/notes/<action>.md, observed
       after the last change (the Proof, a probe or an inspection; the later checks are the target):
       C1 fleet placement · C2 fire semantics · C4 store cap · C5 no I/O, injectable random · C9 argument checks
    2. the step's Proof exited 0 after the last change
    3. RUN/notes/<action>.md answers each of the eight considerations for this step
    4. the lint gate reports no unwaived new finding on a changed line               (code steps only)
    5. the result lists what no later check covers (or none), and whether each skill was used
    Repeat while a requirement has no evidence, the Proof fails or a consideration is unanswered, and the latest
    iteration changed the work to fix it; there is no iteration limit. Stop blocked when a requirement is proven
    unachievable as planned (it contradicts another requirement, the item or a protected file; it needs a tool,
    access or authority that is absent; or it would exceed the item), or when the same failure persists after 7
    genuine fix attempts (the stage then reports revise). Never stop cancelled: a user's stop is the packet's
    pause command.
    Contract: RUN/loops/<action>-contract.json
    Receipt: RUN/loops/<action>-receipt.json
How to invoke: on Claude Code, the Skill tool with skill until-loop and the argument above; elsewhere, the card …
```

What makes it generic: the sentence shape is fixed text. The IDs, criterion names, AD range and step ID are filled
from the accepted step plan and the knowledge home. A configuration, data or document step gets the same sentence
with its own requirements and design directions.

Exit 1 is the change that matters. The loop now ends when **each requirement has its evidence**, not when the step's
files parse. ShipLoop checks by script that each listed criterion ID has an evidence line in the notes. It does not
judge the evidence; the per-step Improve review does.

### Engine consequences (in `shiploop_loops.py`)

- `WORK["implement"]` takes the new sentence. `_build` fills three new tokens from state: `{requirements}` (the step's
  criterion IDs and the R-n they serve), `{design}` (the AD-n of `follows`, plus "the step's cards" and "the existing
  example") and `{step}`. The contract rebuilt at `complete` still equals the one written at entry, because every
  value comes from state.
- `exit_condition("implement")` is no longer static. Exit 1 lists the step's criteria, so the stage row's Done-when
  line becomes a template with `{step_criteria}`. The prose-pin test in `shiploop-stage-spec.test.py` pins the
  template.
- `_build`'s implement `scope` still says "only its paths: …" (the paths are printed inside the contract). Revision 3
  removes that. The scope becomes: "Step S1 of work item W1: this step's requirements only, no later step's work.
  ShipLoop commits the item's declared files; a needed file outside them is a revise."
- The ask-agent route already issues one implement action for **every** step ("the change of every step, S1 to S3,
  in order"). Its Work sentence becomes "Implement all of this item's plan, steps S1 to S3, in order, anchored in …",
  which is the owner's wording exactly.
- The renderer moves the loop block from after the narrative to the end, and adds the pointer line. The step-packets
  head-fit test must still pass with the pointer in the head.

### Open question

In inline runs, ShipLoop issues one packet per step and runs an Improve review after each. "Implement all of this
plan" can be read as either of these:
- **(a)** all of *this step's* plan in the inline route, and all steps in the ask-agent route. This is what the mock
  shows.
- **(b)** one loop for the whole item's plan in inline runs too. That would remove per-step packets and the per-step
  Improve review the owner set on 2026-10-10.

**Decided 2026-10-17 (owner): (a).** Inline runs loop one step at a time, with Improve after each. The ask-agent route loops over the whole plan.
