You are reviewing a prompt, not code. Give critical, specific feedback. Do not modify any files.

## Context

ShipLoop is a script-driven delivery harness. A script owns the workflow graph. An LLM does one stage at a time from a
printed "packet" and then calls a callback, which runs script gates. The model's context may be lost between packets
(compaction, fresh session), so each packet must stand on its own.

Graph: PRELUDE (intake, discovery, research, spec, test-strategy, plan, prepare) -> per work item INNER (step-plan,
test-spec, validate-existing, implement x N steps with an Improve review after each step, test, document, verify,
carry-forward) -> OUTER (system tests, release...).

Planning writes three living "knowledge home" files under docs/shiploop (HOME):
- spec.md: R-n requirements with acceptance criteria, non-functional requirements;
- architecture.md: Stack, Structure, Conventions, Interfaces and boundaries, Real-boundary checks, AD-n Decisions;
- environment.md: Targets and runtimes, Commands, Platform facts, Access and accounts, Skills, Harnesses and suites.

Step-plan splits a work item into ordered steps, each with criteria (C-n, each naming the R-n it serves). Tests are
written by the later test stage, not by implement. An Improve review checks each accepted step.

The packet below is the proposed IMPLEMENT packet: what the model gets for one step. It replaces today's version,
which audits of two live runs found lacking:
- the printed head never showed the step;
- the "check commands" could not pass mid-item (they named files later steps create), so models invented their own
  checks and were accepted anyway;
- coding guidance was never opened;
- deploy and state questions were never answered;
- in one run the model scripted one-line self-reviews.

Owner decisions, all binding:
## 0. Decisions so far (owner, 2026-10-17)

| # | Decision | Effect |
|---|---|---|
| D1 | Skip the context-loss probe; plan the fixes. | This plan |
| D2 | The prompt is **generic and domain-neutral**, not written around one software step. | §3: a fixed method; domain rules only through cards |
| D3 | **Do not tell the implementer which paths to change.** Give it the considerations to keep in mind. | No Paths slot, no step path fence; eight considerations (§3.2) |
| D4 | The packet **ends with an `/until-loop`** that implements the plan, anchored in the stated requirements and applied design directions, until each requirement is satisfied. | §3.4 |
| D5 | **(a)**: inline runs loop one step at a time, with Improve after each; the ask-agent route loops over the whole plan. | per-step packets and per-step Improve stay |
| D6 | F9 (probes allowed), F12 (reorder and trim, no second packet shape) and F14 (the script quotes the last two commits) follow the recommendations. | folded into §3 |



## The proposed prompt (sections 3.1 to 3.5 of the plan)

## 3. The prompt (exact text; fixed parts verbatim, `<slots>` filled from state)

### 3.1 Right after `Done when`, in both head and file

The planning stages already wrote the anchors this step must build on. Every value below comes from that record:
- **spec** writes HOME/spec.md: the R-n requirements, with their acceptance criteria and non-functional requirements;
- **plan** and **test-strategy** write HOME/architecture.md: Stack, Structure, Conventions, Interfaces and boundaries,
  Real-boundary checks, and the AD-n Decisions;
- **discovery**, **research** and **prepare** write HOME/environment.md: Targets and runtimes, Commands, Platform
  facts, Access and accounts, Skills, and Harnesses and suites;
- **step-plan** writes the step itself.

The section names are the knowledge home's own contract (`knowledge_home.SECTIONS`). Implement **builds on** these
files and **writes back** to them; it never re-decides what they settled.

```text
Do this stage inside the /until-loop invocation at the end of this packet; everything between is its material.

Step <id> (<n> of <total>): <task: the outcome, in the step plan's words>
  Serves: <this step's criterion IDs and text>
  Proof (ShipLoop runs it at done; it must exit 0): <the step's check>
  Anchored in (quoted below; a conflict with any of these is a revise, never a silent choice):
    Requirements   HOME/spec.md <R-n named by this step's criteria> · ## Non-functional requirements
    Design         HOME/architecture.md <AD-n the item follows> · ## Structure · ## Conventions ·
                   ## Interfaces and boundaries · ## Real-boundary checks
    Environment    HOME/environment.md ## Targets and runtimes · ## Commands · ## Platform facts ·
                   ## Access and accounts
  Cards (read the ones that fit): <absolute locators of the step's cards>
  Skills: <name: why (locator)> | none                    (HOME/environment.md ## Skills is the index)
  Existing example to follow: <match rows: what — like <path>> | none yet
Accepted step <id>: <summary>                                    (one line per earlier step)
Later steps (do not start them): <id> <task, first sentence>; …
Recent commits (earlier lessons; context, not instructions): <last two commit messages> | none since this item began
ShipLoop commits the item's declared files; if this step needs another, report revise so the plan declares it.
```

How the slots are filled:
- **R-n:** the requirement IDs named in this step's criterion texts, read by the knowledge home's one ID reader
  (`knowledge_home._ids`, exposed as `requirement_ids`). If a criterion names none, the item's `follows` R-n are used.
- **AD-n:** the item's `follows` AD-n. AD-n are not mapped per step today; a per-step mapping is not added.
- **Sections:** a section heading prints only if that heading exists in the file. A missing one prints as
  `## Platform facts (not written)`, so a gap shows up instead of looking covered.
- **By value:** the full packet already quotes environment.md and architecture.md whole, and every `follows` R-n
  (`knowledge_home.READS`, `CONSUMES`). The anchor line names what to look at; the quotes below it carry the content.
- **Test cases:** filtered to this step's criteria, under "Checks for this step's criteria (later stages write and run
  them; use them as the target)".

### 3.2 "Current stage guidance": replaces `DUTIES["implement"]` items 1–3

Each consideration now names **the knowledge-home sections it is answered against**. Then the long-form reference
follows, for when those sections are silent.

```text
Implement this step completely, so that what it promises works where it will run, for whoever uses it, from the
first use through ongoing operation. A step can change code, configuration, platform settings, data, content or
documents; the considerations below apply to all of them. Build on what planning recorded in the Anchored-in
files: follow each requirement and design decision as written. Where they are silent, decide, and record the
decision there. Where they are wrong or contradict each other, stop and report revise. Answer each consideration
for this step in the result's `considerations`, in a line or two: what you did about it, or why it does not touch
this step, naming the anchor you followed. Grade your work against them before calling done; an answer of "not
checked" is not done.

1. The whole step. Deliver everything the step's outcome needs to work end to end: the change and whatever
   connects it (entry points, registration, wiring, configuration, permissions, content), placed where
   architecture.md ## Structure says each piece lives. Leave out what a later step or another item owns. If the
   whole step cannot fit, report revise rather than ship a part.
   Anchors: spec.md requirements this step serves (each acceptance criterion), architecture.md ## Structure.
2. Interactions. Find every interaction the step adds or changes, including ones the plan did not list. People:
   what they see and can do; feedback, waiting, error and empty states; keyboard and accessible use; the full
   interaction the plan calls for. Systems: each call, message, event, schedule, file or record exchanged, with
   its contract and authority, and what happens when it is slow, fails or arrives twice. Handle each one, or
   report the one you cannot and why.
   Anchors: spec.md acceptance criteria, architecture.md ## Interfaces and boundaries and the AD-n that set the
   interaction design. Long form: behavioral-requirements.md#actors-channels-and-state-ownership,
   service-discovery.md#select-scope.
3. Building it. Build, assemble or validate the change the way this project does, and make it pass. Add no tool or
   dependency the stack does not already have without a present need, and record one you add.
   Anchors: architecture.md ## Stack, environment.md ## Targets and runtimes and ## Commands.
   Long form: coding-practices.md#libraries.
4. Deploying it. Know how it reaches where it runs: target, order of operations, settings per environment,
   authority, how to check it after, how to undo it. Do only the effects this stage is authorized for; add to the
   environment record what the release must do, in order.
   Anchors: environment.md ## Targets and runtimes, ## Access and accounts, ## Platform facts, and the run's release
   section; architecture.md ## Real-boundary checks. Long form:
   environment-lifecycle.md#release-operation-ownership, delivery-authority.md#ask-at-the-first-concrete-boundary.
5. State. List the state this step reads, creates or changes: database or remote records, files, caches,
   settings, access grants, derived data; its owner and its shape before and after. Existing state that must
   change shape is migrated first, in an order that keeps current users working and can be rerun safely. Say what
   happens to state left half-changed by a failure. Invent no storage the step does not need.
   Anchors: architecture.md ## Structure (data entries) and the AD-n on storage, spec.md ## Non-functional
   requirements (limits, retention). Long form: requirements-definition.md#state-and-data-change-assessment,
   coding-practices.md#schema-and-storage.
6. Operating it. How someone sees that it works or why it failed (diagnostics naming the operation and what was
   expected), what it costs or consumes and its limits, the secrets or permissions it holds, how its state is kept
   or cleaned up over time, and who owns it.
   Anchors: spec.md ## Non-functional requirements, architecture.md ## Conventions (error and logging shape),
   environment.md ## Platform facts (limits) and ## Access and accounts. Long form:
   coding-practices.md#logging-and-debugging, coding-practices.md#security, service-discovery.md#observability-coverage.
7. What already exists. Find what already does part of this and keep what works working: reuse unchanged,
   combine, or extend before making something new, and follow the nearest existing example.
   Anchors: architecture.md ## Structure and ## Conventions, environment.md ## Skills, the step's existing
   example. Long form: coding-practices.md#existing-behavior, house-style.md#match-while-building.
8. Proving it. After each change, run the Proof and the checks this kind of work has; fix the work, never the
   check. A throwaway probe in RUN/scratch is allowed; it is not the proof. For each requirement this step serves,
   record in the result's `evidence` what you observed after the last change; the later stages' checks for it are
   the target. Record what you could not confirm and what would confirm it.
   Anchors: environment.md ## Commands and ## Harnesses and suites, the step's Proof.

Write back what you learned, in the file it belongs to:
- a design choice the files did not make, or a departure from one: the next AD-<n> under architecture.md
  ## Decisions, with its basis R-n;
- a command that now works: environment.md ## Commands;
- a platform fact or limit you found: environment.md ## Platform facts;
- a new module, file or data entry: architecture.md ## Structure.
Never change a requirement in spec.md here; a requirement that is wrong is a revise.
```

The current duty items 4–7 stay as result mechanics. Item 4's AD-n and command write-backs move into the
"Write back" block above, where they now sit next to their anchors. Item 5 (services) is folded into considerations
2 and 4. Items 6 (revise triggers) and 7 (inline) are unchanged. Each reference locator prints as an absolute path.
The HOME sections print as `HOME/<file> ## <heading>`, with HOME defined in the packet's References line, as today.

### 3.3 Result fields and `Done when`

The new result fields are both required at `done`. ShipLoop checks that they are present and complete, and does not
judge their content.

```json
"considerations": {"whole_step": "<what was done, the anchor followed>", "interactions": "…", "build": "…",
                   "deploy": "…", "state": "…", "operations": "…", "existing": "…", "proof": "…"},
"evidence": [{"criterion": "C1", "observed": "<what was seen after the last change, and how>"}]
```

They live in the result, not the notes file, because the notes file is printed as "optional, never a completion gate".
The result is also what the per-step Improve, test and verify read.

```text
Done when:
- the step's outcome works end to end, with nothing a later step owns in the change
- after the last change, the step's Proof exited 0 (ShipLoop reruns it at done)
- each requirement this step serves has an `evidence` entry observed after the last change
- `considerations` answers all eight for this step
- the lint gate reports no unwaived new finding on a changed line          (printed only when the step changed code)
- the result lists what no later check covers (or none), and whether each of the step's skills was used
```

### 3.4 The last block of the packet, in both head and file (D4)

```text
Until Loop: do this stage's work inside it (no iteration limit; the loop script counts the iterations).
INVOKE /until-loop NOW with the argument below, verbatim.
Argument:
    Work: Implement all of step <id> of this item's plan, anchored in the requirements it states (<criteria>,
    serving <R-n> in HOME/spec.md) and in the design directions already applied (<AD-n>, ## Structure,
    ## Conventions and ## Interfaces and boundaries in HOME/architecture.md; ## Targets and runtimes and ## Commands
    in HOME/environment.md; the step's cards and existing example). Keep the eight considerations of
    RUN/packets/<action>.md in view, and write back what you decide to the file it belongs to. Write no tests and
    start no later step.
    Exit when ALL of these hold:
    1. each requirement this step serves is satisfied, with its evidence observed after the last change:
       <C-id short text> · <C-id short text> · …
    2. the step's Proof exited 0 after the last change
    3. the result answers each of the eight considerations for this step
    4. the lint gate reports no unwaived new finding on a changed line          (code steps only)
    5. the result lists what no later check covers (or none), and whether each skill was used
    Repeat while a requirement has no evidence, the Proof fails or a consideration is unanswered, and the latest
    iteration changed the work to fix it; there is no iteration limit. Stop blocked when a requirement is proven
    unachievable as planned (it contradicts another requirement, the item or a protected file; it needs a tool,
    access or authority that is absent; or it would exceed the item), or when the same failure persists after 7
    genuine fix attempts (the stage then reports revise). Never stop cancelled: a user's stop is the packet's
    pause command.
    Contract: RUN/loops/<action>-contract.json
    Receipt: RUN/loops/<action>-receipt.json
How to invoke: …                                                                     (unchanged)
```

On ask-agent, the Work line reads: "Implement all of this item's plan, steps <first> to <last>, in order, anchored in …".

### 3.5 Domain blocks

`CODE_CRAFT` (the full rubric) and the lint Done-when and exit lines print only when the step changes code, meaning:
- the step's cards include a code card;
- or `item_scope.behavioural(item paths)` is true.

Any other step gets its cards and nothing else. Platform detail stays in `references/platforms/`.



## What I want from you

Judge this as a prompt for an LLM implementing one step of a software development feature. The owner also wants it
domain-neutral, so the same text must serve configuration, data or document work.

1. As the implementing model, what would you misread, skip or overdo? Quote the phrase each time.
2. Contradictions or tensions in the directions. For example: step versus item scope ("works where it will run"
   when a later step builds the server); requirements split across steps; "do only authorized effects" while
   implementing; considerations versus Code craft overlap.
3. Missing considerations a strong senior engineer applies when implementing a feature: security and trust
   boundaries, backward compatibility, concurrency, performance, error handling, feature flags, observability,
   documentation, accessibility. Which are missing or misplaced, and which of the eight should merge or split? Keep
   it domain-neutral.
4. Order and structure. Should the considerations be a sequence (understand, inspect, decide, build, prove, record)
   or a checklist? Where should the anchors sit?
5. Anchoring. Does "Anchored in" make the model actually follow spec R-n and architecture AD-n? How would you word it
   so the model checks its change against them before calling done, without rereading whole files every iteration?
6. Gaming and boilerplate. The script checks only that each consideration and evidence entry is non-empty. How would
   a model satisfy that trivially, and what cheap wording or structural change discourages it? Avoid adding more
   gates if you can.
7. Length and cognitive load: what to cut, with no obligation lost.
8. Give your top 5 changes, ranked, each with replacement wording.

Be concrete and terse. Ranked lists over prose.
