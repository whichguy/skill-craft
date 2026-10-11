# ShipLoop packet re-cut: every stage, concise, deduplicated, with an action goal (2026-10-11)

Status: **plan**. Execute: inline, with parallel drafting workers. Owner direction, 2026-10-11. The owner asked, while
reading the full packet files of test-spec, implement and carry-forward:

- "We should also look to make the full packet file for each and every iteration more concise and more direct, and
  deduplicated as much as possible ... without losing any fidelity or accuracy."
- "Look at every stage and every full packet file that's produced."
- "Evaluate every prompt that's sent back. Sometimes I don't think we actually have a clear goal stated as an action of
  what to do or where to produce the outcome." Carry-forward is the example: it "needs to be clear about how a
  deterministic reusable skill should probably be created ... how or where to do that."
- Improve: "any time we run improve, it's really just calling the improve skill and then, once complete, invoking the
  done activity ... we really do not need any other detail, nuance, context". And "we don't need to tell any other
  skill about improve ahead of time".

## The rubric each packet must pass

R1. **Action goal.** The goal is one sentence that names the action, its object, and where the outcome is written: a
    file and section, or a result field. Example: "Specify W1's tests: record one case per focused id in `test_cases`
    and write each case's entry under `### <ID>` in FEATURE/test-spec.md."

R2. **One home per fact.** These each appear once:
    - the exit conditions;
    - each refusal (Checked by lists only what the checks refuse beyond the exit conditions);
    - each command (callback, check, recover, pause, halt, lint, until-loop start);
    - the result shape, with its outcome shapes;
    - each location (HOME, FEATURE, RUN, WORKTREE);
    - the last stage's summary, which the status block already prints;
    - the step or work item text.

R3. **Only what applies.** A packet does not carry:
    - another stage's guidance (for example "At plan and step-plan ..." in test-spec);
    - a consideration that repeats the duty;
    - a guide the text never cites;
    - feature files the stage neither reads nor writes;
    - any advance mention of Improve.

R4. **Every instruction says where its output goes.** That is a file and section, a result field, or "nothing written".

R5. **Fidelity.** Every obligation in today's packet maps to the new text or to a named `reference.md` section. A
    drafting worker writes the map, one row per old sentence (old sentence → new home, or the reason it is cut). Pin
    workers report any test whose obligation has no home, instead of re-pointing it.

R6. **The layout every producer packet shares,** in delivery order:
    1. header: stage, item, revision, callback, keepalive;
    2. status block (the hook reads it within 16 KB);
    3. "What to do": the goal (R1) and the numbered duty;
    4. "When it is complete": exit conditions, Checked by, outcomes;
    5. "What to execute": /until-loop, the result template, the outcome shapes, and Check, Recover, Pause and Halt;
    6. "What you work from": the locations on one line, the READS quotes, the hand-offs, earlier results, the work
       item, the request fence, the cited guides, the rules.

R7. **The Improve packet** holds two instructions: invoke the improve skill (ShipLoop supplies the argument path; it
    binds its own card and writes the opening file from state), and run the done command when it completes. Beside
    them stand only the hooks' machine lines: the status block and the keepalive marker.

## Carry-forward's skill decision, made concrete (R1 and R4)

Draft text (worker B refines it against references/carry-forward.md and testing-and-documentation.md#reusable-product-skills):

- **Decide.** Record `skill` as `none`, `reuse`, `update` or `create`. Use create or update only for a procedure this
  run performed at least twice (steps or items), or one that a pending item or R-<n> says will recur.
- **Where.** Use the repository's existing skill directory (named in HOME/environment.md ## Skills or SHIPLOOP.md).
  When there is none, use `skills/<name>/SKILL.md` in WORKTREE. Never a global or host install.
- **What, deterministic.**
  - `SKILL.md` has `name` and `description` frontmatter: when to use it, its inputs, its outputs, and the exact steps.
  - The repeatable part is a script beside it (`skills/<name>/scripts/<verb>`), with a stated command line, an exit
    code and the output it prints. SKILL.md calls the script rather than restating its logic.
  - A short check proves the script runs, and the trial run on this run's case is recorded.
- **Register.** Add a line under HOME/environment.md ## Skills and in SHIPLOOP.md with its path and when to use it.
- **Evidence.** Put the skill's path, the repeat evidence and the trial command with its exit code in the result's
  `skill` and evidence_refs. ShipLoop commits the directory when the stage is accepted.

## Work

1. **Renderer (inline).** The shared layout (R6): one header, sections 3-6, outcome shapes once, commands once, the
   locations on one line, and the status-block summary not repeated. Then the Improve packet (R7), and removing every
   advance Improve mention.
2. **Duties (four parallel drafting workers).** Each worker drafts its stages' goal (R1) and numbered duty (R2-R4),
   with the R5 map, to files under docs/experiments/packet-recut-20261011/. The main session applies them, so no two
   workers edit shiploop_prompts.py.
   - A: intake, discovery, research, spec, test-strategy, plan, prepare.
   - B: step-plan, test-spec, validate-existing, implement, test, document, verify, carry-forward.
   - C: system-test-author, system-test, product-acceptance, release-plan.
   - D: release-check, release, release-verify, operations, handoff.
   The shared texts (STAGE_RULES, CODE_CRAFT, the test hand-offs) go to worker B; CODE_CRAFT keeps its nine rules.
3. **Tests.** Pin workers apply the reporting rule (R5).
4. **Verification.**
   - Offline sizes for all four step cases and the dry-run stages, against today.
   - The 30 packet suites, quick with `--changed-from`, and the full tier.
   - Live slices on all four cases, the S-6 clear probe, and the E2E session's live pair.
   - Then main. The artifact is updated after each step.

## Order with the other work in flight

- The full-tier fixes (8cfae04a, merged with main) push once CI's quick tier passes.
- The renderer swap (0c5521fe) lands next, after the full tier and one live slice; the E2E session's 4b/4c wait on it.
- This re-cut builds on the swap.
