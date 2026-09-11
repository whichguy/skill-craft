---
name: shiploop
description: >-
  Markdown-authoritative session harness: establish an approach and checkable
  spec, make one dependency sequence, then execute one action at a time with
  durable evidence, per-step review/improvement loops, and an outer closure.
  Use when the user says shiploop, ship the project, session harness, or asks
  what the next durable delivery step is.
version: 0.9.0
allowed-tools: all
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - portable-skill
      - multi-host
      - session-sm
---

# ShipLoop

ShipLoop is an action-oriented delivery harness, not a product implementer and
not a substitute for the host's technical judgment. It is designed for a
small LLM context window: the script keeps the durable run state in Markdown
and prints one actionable prompt at a time. Use the returned action rather
than reconstructing progress from chat memory.

At start, read the action-protocol result format and the section for the
printed stage. For a small context, use the packet's bounded context command
to retrieve a current run section on demand; do not load every receipt or the
entire guide. Use [the state-file guide](references/state-files.md) only for
inspection/recovery and [the package guide](README.md) for deeper operation.

## Start or resume

1. Locate the skill root as `$SKILL_ROOT`; use its `scripts/shiploop` command.
2. Select the bound repository and a run directory. A normal fresh run is
   `$REPO/.shiploop`; do not use `--force` to replace an existing run.
3. Start it from the repository, or state both paths explicitly:

   ```sh
   cd "$REPO"
   python3 "$SKILL_ROOT/scripts/shiploop" init \
     --repo "$REPO" --run-dir "$REPO/.shiploop" --prompt "<user request>"
   ```

4. Read the compact stdout packet. It names the action ID, working directory,
   relevant durable files, and only the next activity.
5. Do the activity, write the requested Markdown result with exactly one
   `shiploop-state` JSON fence, and execute the printed `complete` command.
6. After any lost context, use `next --run-dir …`; after a real external
   blocker, use `pause --reason …`, obtain the needed direction, then
   `resume --run-dir …`. `halt` writes an unfinished terminal handoff.

Never use bare `complete`, infer a stage, or resurrect old JSON state. The
0.9 command surface deliberately has no `update`, `complete-step`,
`start-step`, `clear-step`, or `inject-step` shortcut.

Before any step work exists, `revisit --action ID --to survey|spec --reason …`
archives superseded planning inputs and corrects them without erasing history.

## Lifecycle

```mermaid
flowchart LR
  A[Preflight and approach] --> B[Survey, research, spec]
  B --> C[Dependency sequence and prep]
  C --> D[Implement one ready step]
  D --> E[Review, improve, verify, commit]
  E --> F[Final verify, broader-plan review, merge]
  F --> G[Coverage, quality, publish, handoff]
```

The printed stages are:

`preflight → approach → survey → research → spec → sequence → prepare? →
schedule → implement → review → improve-plan → improve-apply → verify →
commit`.

Review through commit repeats until the receipt contains two consecutive
trivial-only iterations. It then requires `final-verify`, `post-inner`, and
`merge` before another ready step can start. Once the DAG drains, the outer
stages are `coverage → quality → publish? → handoff`.

`prepare` is present only when the lifecycle calls for outer-before
preparation. `publish` is a DAG step when lifecycle says `dag`, an outer
stage when it says `outer-loop`, and absent when it says `none`.

## Host responsibilities

- **Preflight and planning:** preserve unrelated dirt; record baseline,
  runtime, likely lint/test commands, credentials availability without secrets,
  and preparation candidates. Create the approach before the spec. Survey
  before research; research before the checkable spec; make a short native
  forward draft and backwards dependency audit before importing the sequence.
- **Survey constraints:** retain the environment writer route, destination
  conventions, reserved/product layout, lint and live identity oracle,
  routing, references, UI/design constraints, and any client–service
  invocation contract. Do not invent a second writer or a fallback when an
  exclusive writer fails.
- **Implementation:** work only in the active per-step worktree. Add or
  expand meaningful tests that map to each exact `produces` value. Run lint
  after every production edit and run the required tests until successful.
  Execute `verify` using an explicit manifest before completing `implement`,
  every Improve verification, final verification, and outer quality.
- **Improve:** at each iteration first retrieve and read current Git history,
  then review code, tests, regressions, and prior learnings; plan fixes; apply
  them; lint and test; and make one verbose primary commit. A material finding
  or application resets the trivial streak. No maximum-cycle condition grants
  success.
- **Learning:** after inner-loop convergence, decide explicitly whether
  broader plan steps, dependencies, preparation, or testing should change.
  Only pending DAG steps may change. Record generic ShipLoop ideas in the
  proposal journal; do not self-modify the harness from that journal.
- **Outer closure:** complete Review Coverage, whole-product quality checks,
  and only the publication the frozen lifecycle names and the user authorized.
  Record delivery evidence and limitations honestly in handoff.

The host owns test meaningfulness, review quality, semantic judgment, and
external publication facts. ShipLoop can reject stale or failed evidence; it
cannot magically prove that an implementation is semantically correct,
published, or accepted by an external system.

## Non-negotiable evidence rules

- Every iteration includes a concrete lint check and at least one test check.
  Tests cover every declared `produces` string. Use suitable linting even for
  small or documentation changes; do not bypass the lint gate.
- Check commands are argument vectors, not opaque shell prose. `verify` saves
  fingerprints and logs and refuses evidence if files change while checks run.
- At Improve review, run `history` for the current action before completing
  the review. Retrieve further pages with `--skip` when needed.
- Each Improve iteration creates a new current-HEAD commit with `Review:`,
  `Changes:`, `Validation:`, and `Key learnings:` sections plus the exact
  `ShipLoop-Iteration:` trailer. An honest allow-empty audit commit is okay.
- Two consecutive trivial-only iterations are necessary but insufficient:
  final verification and broader-plan review still must pass. Failed, stale,
  or changed-tree tests never exit the loop.
- Do not `git add -A`, force-remove a worktree, silently merge unrelated dirt,
  auto-resolve conflicts, or push/publish merely because a local merge worked.

## Durable artifacts

`state.md`, `history.md`, `backchain/plan.md`, receipts, results, check
records, manifests, history pages, and `shiploop-improvements.md` are
Markdown authority. Raw check logs are evidence files, not Markdown authority.
The structured fenced payload is allowed because it lives inside the
authoritative Markdown document. A write-ahead `transaction.md` makes
multi-file updates recoverable; the next locked command rolls it forward.

Legacy runs with only `state.json` require explicit `migrate`. Migration backs
up legacy state and re-establishes evidence gates; it never deletes existing
code, branches, or worktrees. A deleted Markdown authority cannot be replaced
by a forged JSON file.

## References for phase work

- [Survey guide](references/survey.md) and
  [validate-spec activity](references/activities/validate-spec.md): preserve
  writer, routing, reserved-tree, UI, and client–service invocation
  constraints.
- [Planning activity](references/activities/plan.md): make one validated DAG,
  include preparation/deployment placement and testable outputs.
- [Implementation activity](references/activities/implement.md): worktree,
  lint, test, evidence, and commit discipline.
- [Residual activity](references/activities/residual.md): outer coverage,
  quality, authorized publication, and honest handoff.
- [Host matrix](references/host-matrix.md): host-specific invocation
  constraints. It is a reference, not mutable run state.

If the stdout packet and an older document differ, prefer the current script
packet and [action protocol](references/action-protocol.md); record the
documentation mismatch as a generic ShipLoop journal proposal.
