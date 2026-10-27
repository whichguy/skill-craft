# Reference code at the recommendation baseline

Revision: `c70a33f46ed71cd2eed537353438cdd61c51a2ba`. Read with `git show`, without checking out or modifying source.
Each excerpt is exact source text; original line ranges and source hashes are in the companion JSON map.
These fragments identify existing behavior and change sites; they are not implemented changes.

## step-plan — DUTIES[step-plan]

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1268–1295 at `c70a33f46ed7`.

```python
4. **`steps`**: every implementation step in order (one is fine); ShipLoop issues one implement packet per step.
   - Size each as one behaviour-level change a named check proves. Split a step with two separately confirmable
     behaviours, one crossing a module or layer boundary (interface first, then each side), joining two outcomes with
     "and", or too large for one review. Fold a step no check confirms alone (half a rename, scaffolding) into the
     first step that uses it. A single bug fix or mechanical rename is one step.
   - Tests are not a step (the test stage writes them after the last implement step); a step changing only test
     files is refused unless the whole item is tests.
   - Each step declares `deps` (earlier step IDs it truly needs, else []; list order is no dependency), the
     `criteria` it satisfies and its `check`; its `task` cites IDs, not their text. Every criterion is satisfied by
     some step. Optional `paths` (inside the item's) serve the parallel chain.
   - `check`: the one command, from the repository root, that proves the step's criteria with only this step and
     accepted earlier ones; ShipLoop runs it at the step's done. It needs no later step, unwritten test or release
     artifact (reuse a recorded command that proves them); skipping a missing file, or asserting only that a file
     exists where behaviour is asked, proves nothing. Remote-only target: the recorded test route only. None runs
     now: change the step boundary.
   - `skills`: reread the host's skills and the repository's skill index (an earlier item may have added one). List
     `{"name", "why", "locator"}` for each with a concrete use in the step, else []. Prefer a repository-local skill
     reused unchanged. `locator`, when given, is an existing SKILL.md or card path.
5. **`test_commands`** (`[{"command", "suite", "ids", "criteria"}]`), run from the repository root; the test and
   verify stages run exactly these.
   - focused: this item's cases with the IDs they carry and a runner flag that prints test names (Jest `--verbose`,
     pytest `-v`, others: GUIDES/platforms/; never dot or junit). """ + ID_WORD_RULE + """ `min_tests`
     where a command must run at least that many. ShipLoop refuses a run that executed no test, so check the filter.
   - regression: the retained suites the changed paths affect.
   - check: the lint, type and build commands HOME/environment.md records for these files, judged by exit code, no
     `ids` or `min_tests`; each safe to repeat locally. None: `check_na` with the reason; no command at all: `test_commands_na`.
     The test and verify stages run these; implement runs only each step's own `check`.
   - Every criterion is named in some command's `criteria`, and a command names only listed criteria.
```

## step-schema — _check_step_sizing

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 2451–2477 at `c70a33f46ed7`.

```python
def _check_step_sizing(result: Mapping[str, Any]) -> None:
    """Refuse a done step plan whose steps are not sized as behaviour-level changes (owner, 2026-10-10).

    Every step names the criteria it satisfies and its ``check``, the command that proves them (implement-step fix
    plan section 4.1); every criterion is satisfied by some step; a step's optional paths are a subset of the item's;
    and no step only changes test files, unless the whole item is tests (the test stage writes the tests after the
    last implement step, so a test-only step would be a no-op).
    """
    steps = result.get("steps") or []
    known = [str(row.get("id")) for row in result.get("criteria") or () if isinstance(row, Mapping)]
    item_paths = list(result.get("paths") or ())
    shape = ('[{"id": "S1", "task": "...", "deps": [], "criteria": ["C1"], "check": "<command that proves C1>"}]')
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        name = str(step.get("id"))
        _need(step.get("check"), "step " + name + " must record its check: the one command, run from the repository "
              "root, that proves the criteria it satisfies using only this step and accepted earlier steps (ShipLoop "
              "runs it when the step reports done). Steps are " + shape)
        if known:
            _need(step.get("criteria"), "step " + name + " must list criteria: the IDs of the criteria it satisfies ("
                  + ", ".join(known) + "). A step no check can confirm on its own belongs in the step it serves.")
            unknown = [c for c in step["criteria"] if c not in known]
            _need(not unknown, "step " + name + " names criteria the result does not list: " + ", ".join(unknown))
        outside = [path for path in step.get("paths") or ()
                   if not any(path == item or fnmatch.fnmatchcase(path, item) for item in item_paths)]
        _need(not outside, "step " + name + " changes paths the item does not declare: " + ", ".join(outside)
```

## stage-proof — implement completion runs

Source: `skills/shiploop/scripts/shiploop_stage_spec.py`, lines 409–426 at `c70a33f46ed7`.

```python
        steps_goal="Make the change of steps {steps} on their paths ({paths}) in WORKTREE; exit codes go to "
                   "RUN/notes/<action>.md, uncovered behaviour to `not_covered`.",
        steps_done_when=(
            "only the paths of steps {steps} ({paths}) changed since the first of them began, and no work outside "
            "those steps is in them",
            STEP_PROOF_CONDITION,
            "after the last edit, the lint gate reports no unwaived new finding on a line these steps changed",
            "the result lists each behaviour the changes added that no test-spec case covers (or none), and whether "
            "each step's skills were used",
        ),
        develop="Make the planned change in the execution checkout, one reviewed step at a time, matching the house style.",
        test="After each meaningful change, run the step's Proof; change the work, never the Proof or what it "
             "expects. Tests are written in the test stage.",
        tools="Run `shiploop lint --action` after each edit; the lint gate runs at complete, on every step.",
        edits=frozenset({"code"}),
        entry_runs=("loop-contract",),
        # step-proof runs on the inline route only: the ask-agent action builds every step and keeps the item's checks.
        complete_runs=("loop-terminal", "lint-gate", "step-proof"),
```

## command-owner — stage_commands

Source: `skills/shiploop/scripts/shiploop_test_loop.py`, lines 284–310 at `c70a33f46ed7`.

```python
def stage_commands(state: Mapping[str, Any], stage: str, work_item: str) -> Tuple[List[Dict[str, Any]], str]:
    """This stage's commands and, when there are none, why.

    The outer stages run what their recording stage recorded (``OUTER_SOURCES``).  An inline implement step and its
    Improve review run only that step's Proof, the step plan's ``check`` for it (``step_command``: the implement-step
    fix plan's section 4.1); the item's commands stay with the test stage and verify.  Every other item stage, and the
    ask-agent route's one implement action for every step, runs every command the latest accepted step plan recorded.
    The base run takes the focused and regression ones (``base_commands``).
    """
    if stage in STEP_PROOF_STAGES:
        step = step_command(state, work_item)
        if step is not None:
            return [step[1]], ""
    if stage in OUTER_SOURCES:
        source, field = OUTER_SOURCES[stage]
        result = _latest_root_result(state, source)
        commands = [dict(row) for row in result.get(field) or ()]
        return commands, ("" if commands else str(result.get(field + "_na") or ""))
    _action, result = _step_plan(state, work_item)
    if "test_commands" not in result:
        return [], ""
    commands = [dict(row) for row in result["test_commands"]]
    if commands:
        return commands, ""
    return [], str(result.get("test_commands_na") or "")
```

## step-receipt — step_proof

Source: `skills/shiploop/scripts/shiploop_test_loop.py`, lines 1357–1385 at `c70a33f46ed7`.

```python
def step_proof(root: Path, state: Mapping[str, Any], work_item: str, action: str, *, count: bool = True,
               phase: str = "complete", runner: Optional[Runner] = None, env: Optional[Mapping[str, str]] = None,
               clock: Optional[Callable[[], float]] = None, command_timeout: float = COMMAND_TIMEOUT_SECONDS,
               budget: float = STAGE_BUDGET_SECONDS) -> Tuple[Dict[str, str], str, List[str]]:
    """Run the inline implement step's Proof on the candidate; return (record writes, refusal body, summary lines).

    The Proof is the step plan's ``check`` for the step (``step_command``), judged as a check (``judge``: exit 0, and a
    runner summary that shows no test ran is no pass), with the test loop's timeout, budget and capture.  Its record
    (``step_proof_path``, or ``step_proof_check_only_path`` for ``count=False``) is bound to the action, the step, the
    command and the candidate: the working trees the run started on and left (``_tree``).  A passed record of this
    action for the same step and command whose trees include today's is taken instead of running again, so an
    unchanged candidate reuses its receipt; at complete that writes a numbered record that says so, and at the Improve
    import (``phase`` "improve-import") nothing is written.  An empty refusal means the Proof passed.  A step with no
    check is refused: the step plan gate requires one, so only a run positioned another way lacks it.
    """
    root = Path(root)
    found = step_command(state, work_item)
    if found is None:
        return {}, ("ShipLoop step proof: the step this action builds records no check (its Proof) in the accepted step "
                    "plan, so ShipLoop cannot confirm it. Report revise so the step plan records one."), []
    step, row = found
    step_id = str(step.get("id"))
    repo = Path(str(state["repo"]))
    tree = _tree(root, repo)
    number = _count(root, action, step_proof_path) + 1
    matched = next(((relative, record) for relative, record in reversed(_proof_records(root, action))
                    if record.get("passed") is True and record.get("step") == step_id
                    and record.get("command") == row["command"] and tree and tree in (record.get("trees") or ())),
                   None) if count else None
```

## step-execute — step_proof execution and evidence

Source: `skills/shiploop/scripts/shiploop_test_loop.py`, lines 1395–1418 at `c70a33f46ed7`.

```python
                  "runs": list(matched[1].get("runs") or ()), "trees": [tree],
                  "reused": {"path": matched[0], "created_at": matched[1].get("created_at"), "tree": tree}}
        return {step_proof_path(action, number): store.dumps(record, "ShipLoop step proof")}, "", [line]
    runner = runner or lint.run_argv
    clock = clock or time.monotonic
    environment = dict(os.environ if env is None else env)
    deadline = clock() + budget
    left = deadline - clock()
    if left <= 1.0:
        run: Dict[str, Any] = _skipped(row, budget)
    else:
        fields, output = _run_command(runner, row["command"], repo, min(command_timeout, left), environment, clock)
        run = {**row, **fields}
        if "status" not in run:
            run.update(judge(row, run["exit"], output))
    disposition = _disposition([run], PASSING)
    record = {"schema": SCHEMA, "kind": "step-proof", "action": action, "stage": STEP_PROOF_STAGES[0],
              "work_item": work_item, "step": step_id, "command": row["command"], "phase": phase,
              "created_at": created, "cwd": str(repo), "passed": disposition == "passed", "disposition": disposition,
              "runs": [run], "trees": [found_tree for found_tree in dict.fromkeys([tree, _tree(root, repo)]) if found_tree]}
    if not count:
        record["counted"] = False
    relative = step_proof_path(action, number) if count else step_proof_check_only_path(action)
    writes = {relative: store.dumps(record, "ShipLoop step proof")}
```

## proof-gate — _step_proof_gate

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 3754–3778 at `c70a33f46ed7`.

```python
def _step_proof_gate(core: Any, root: Path, state: Mapping[str, Any], action_id: str, workitem: str | None,
                     submitted: Any, *, check_only: bool = False) -> list[str]:
    """Accept an inline implement step's done only after ShipLoop runs the step's Proof on the candidate (implement-step
    fix plan section 4.1, unit W2-A); return its ``Gates:`` line.

    The whole-plan ask-agent action is not gated (its chain runs the steps and the item's checks stay its own).  A
    refusal names both routes through the loop with its literal start command: fix the work and report done, or, when
    the Proof cannot assess the step as planned, stop the loop blocked and report revise.  ``check_only`` runs the Proof
    without counting it (``test_loop.step_proof(count=False)``)."""
    if (not isinstance(submitted, Mapping) or submitted.get("outcome") != "done"
            or step_view(state, workitem) is None):
        return []
    writes, refusal, lines = test_loop.step_proof(root, state, workitem or "", action_id, count=not check_only)
    for relative, text in writes.items():
        store.atomic_write_text(root / relative, text)
    if refusal:
        try:
            start = loops.start_command(loops.runtime(state), loops.receipt_path(root, action_id),
                                        root / loops.contract_path(action_id))
        except loops.LoopError:
            start = ""
        route = ("Start the Until Loop again with: " + start + "  (it replaces the receipt), then either "
                 if start else "In the stage's Until Loop, either ")
        raise NavigatorError(refusal + "\n" + route + "fix the work until the Proof passes (never the Proof or what it "
                             "expects) and report done, or, for a Proof that needs a later step, a test the test stage "
```

## improve-reproof — _improve_change_gate

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 3897–3918 at `c70a33f46ed7`.

```python
                             + _callback(core, root, "complete", action=improve_id(state)))
    if child.get("stage") == "implement" and step_view(state, _current_work_item(state)) is not None:
        # The step's Proof passed at implement's done; a review that changed the candidate must pass it again before
        # the step is accepted, and an unchanged candidate reuses that record (implement-step fix plan section 2.1).
        writes, refusal, _lines = test_loop.step_proof(root, state, _current_work_item(state) or "", action_id,
                                                       phase="improve-import")
        for relative, text in writes.items():
            store.atomic_write_text(root / relative, text)
        if refusal:
            message_path = improve_commit_message_path(child)
            raise NavigatorError(
                refusal + "\nFix it within the review's scope, commit the fix (write the message to " + str(message_path)
                + " with a file tool, then run: " + _callback(core, root, "improve-commit", action=improve_id(state),
                                                               message=str(message_path))
                + "), then run the complete command again: " + _callback(core, root, "complete", action=improve_id(state)))
        return
    if child.get("stage") != "carry-forward" or (changes is not None and not changes[0]):
        return
    commands = improve_changes.rerun_commands(state)
    writes, refusal = test_loop.verify(root, state, "", action_id, "end-of-work review", commands=commands)
    for relative, text in writes.items():
        store.atomic_write_text(root / relative, text)
```

## step-block — step_block

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6200–6241 at `c70a33f46ed7`.

```python
def step_block(state: Mapping[str, Any], work_item: str | None) -> list[str]:
    """The one Step block of an inline implement step (implement-step fix plan section 3.1, trimmed to what state holds):
    the task, the criteria it serves by value with their test cases, what it depends on, its Proof, its skills, the
    accepted earlier steps and the later ones by their first sentence.  ``render``, ``packet_head`` and
    ``improve_handoff_text`` print these lines word for word (packet review F15: the head and the Improve hand-off lacked
    them).  No path fence (the fix plan's D3): the item's declared paths bound the change.  [] outside an inline step.
    """
    view = step_view(state, work_item)
    if view is None:
        return []
    step = view.step
    listed = [str(ident) for ident in step.get("criteria") or ()]
    criteria = [(str(row.get("id")), _one_line(row.get("text"))) for row in view.plan.get("criteria") or ()
                if isinstance(row, Mapping) and str(row.get("id")) in listed]
    action = planning_revision.current_actions(state).get((work_item, "test-spec"))
    spec = (state.get("accepted") or {}).get(action) if action else None
    cases = [str(case.get("id")) for case in (spec.get("test_cases") or () if isinstance(spec, Mapping) else ())
             if isinstance(case, Mapping) and str(case.get("criterion")) in listed]
    accepted = {str(earlier.get("id")): row for earlier, row in view.accepted}
    deps = [str(dep) for dep in step.get("deps") or ()]
    check = str(step.get("check") or "").strip()
    lines = [f"Step {step['id']} ({view.number} of {len(view.steps)}), the only work for this packet: "
             + _one_line(step.get("task")),
             *(["  Serves (each criterion this step satisfies, in the step plan's words):",
                *("    " + ident + ": " + text for ident, text in criteria)] if criteria else []),
             *(["  Test cases of these criteria (the test stage writes them later; their oracles: the test-spec result): "
                + ", ".join(cases)] if cases else []),
             "  Depends on: " + ("; ".join(dep + (" (accepted: RUN/results/" + str(accepted[dep]["action"]) + ".md)"
                                                  if dep in accepted else "") for dep in deps) or "none"),
             ("  Proof (ShipLoop runs it from WORKTREE at done; it must exit 0): " + check) if check else
             "  Proof: none recorded in the step plan; report revise so the step plan records the step's check.",
             "  Skills (use each; the summary says whether you did): "
             + (", ".join(str(skill.get("name")) for skill in step.get("skills") or () if isinstance(skill, Mapping))
                or "none")]
    for earlier, row in view.accepted:
        lines.append(f"Accepted step {earlier['id']}: {row['summary']}")
    later = view.steps[view.number:]
    if later:
        lines.append("Later steps (ShipLoop issues each after this one; do not start them): "
                     + "; ".join(str(row.get("id")) + " " + _first_sentence(row.get("task"), 200).rstrip(".")
                                 for row in later))
    return lines + [STEP_FILES_LINE.format(plan=view.plan_action)]
```

## head — packet_head

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 1904–1917 at `c70a33f46ed7`.

```python
def packet_head(core: Any, root: Path, state: Mapping[str, Any], path: Path,
                timeline: Mapping[str, Any] | None = None, *, measure: Callable[[str], int] = len) -> str:
    """The printed part of an active packet longer than ``PRINT_LIMIT``: what to do, in the order a reader cut short needs.

    The blocks of ``_producer_blocks`` in print order: the stage line, the two pointer lines and the callback, goal and
    loop, the status, the duties and rules, the stage's own inputs, the result template; then, while the head fits
    ``HEAD_LIMIT``, the lookups, the chrome and the knowledge files' contents with the hand-offs (the file has them all).
    Owner, 2026-10-16: the head used to leave the duties in the file, so a reader of the printed text alone never saw them
    (measured offline at 2686b427).
    """
    if state.get("active_improve") is not None:
        return improve_packet(core, root, state, timeline) + HEAD_END + "\n"
    blocks = _select_head(_producer_blocks(core, root, state, timeline, path=path), measure)
    return _text_of(blocks, head=True) + "\n" + HEAD_END + "\n"
```

## block-producer — _producer_blocks assignment

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 2045–2053 at `c70a33f46ed7`.

```python
    blocks.append(_Block("goal", P0, _goal_lines(state, stage, root)))
    loop = _loop_lines(root, state, stage, action_id, workitem)
    # An inline implement step's packet puts its Step block right after Done when and ends with its loop, in the file and
    # in the head (implement-step fix plan D4 and section 3.1); every other looped stage keeps its loop here.
    step = _step_lines(state, stage, workitem)
    if step:
        blocks.append(_Block("step", P1, [*step, ""]))
    elif loop:
        blocks.append(_Block("loop", P0, [*loop, ""]))
```

## loop-last — _producer_blocks tail

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 2105–2115 at `c70a33f46ed7`.

```python
    blocks.append(_Block("deltas", FILE_ONLY, [
        *_replan_delta_lines(root, state, stage), *_knowledge_lines(root, state, stage)]))
    blocks.append(_Block("lint-records", FILE_ONLY, _lint_lines(core, root, state, stage, action_id, commands=False)))
    if stage == quality.STAGE:
        blocks.append(_Block("change-inventory", FILE_ONLY, quality.inventory_lines(root, state, workitem or "", action_id)))
    if step and loop:
        blocks.append(_Block("loop", P0, loop))  # its leading blank line parts it from the block before
    return [block._replace(
        lines=_symbolic_lines(block.lines, core, root, state),
        head=None if block.head is None else _symbolic_lines(block.head, core, root, state))
        for block in blocks if block.lines]
```

## handoff — improve_handoff_text

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6402–6418 at `c70a33f46ed7`.

```python
    context = [
        *_goal_lines(state, stage, root),
        *references,
        *([f"Work item: {workitem} — " + str(state["work_items"][state["work_index"]].get("title", "")),
           "Work item context: " + str(state["work_items"][state["work_index"]].get("context", ""))]
          if workitem is not None else []),
        # The step under review: the producer's own Step block, word for word, and the diff base it began from (W2-B).
        *(step_block(state, workitem) if stage == "implement" else []),
        *_review_base_line(root, state, child),
        *_test_context_lines(state, root),
        *_reviewed_input_lines(root, state, stage, workitem),
        # An Improve review never mentions Backchain (owner, 2026-10-11), so its guides are left out here.
        *(label + ": " + str(reference_dir / reference) for label, reference in guidance.STAGE_REFERENCES.get(stage, ())
          if "backchain" not in (label + reference).lower()
          and not (route == guidance.INLINE and label == "Parallel-chain guide")),
        *_run_rules(core, root, state, named),
        *_queue_lines(root, state, stage),
```

## review-base — _review_base_line

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6268–6286 at `c70a33f46ed7`.

```python
def _review_base_line(root: Path, state: Mapping[str, Any], child: Mapping[str, Any]) -> list[str]:
    """The step-entry diff base the step's Improve review starts from: the tree the transition recorded in the action
    record (``_step_entry``) and the tree ShipLoop snapshotted when it bound this review, as one runnable diff."""
    if child.get("stage") != "implement" or step_view(state, _current_work_item(state)) is None:
        return []
    action = current_action(state)
    base = action.get("base") if isinstance(action, Mapping) else None
    bound = None
    try:
        record = store.read_record(Path(root) / improve_changes.bind_path(child["action_id"]))
        bound = record.get("tree") if isinstance(record, Mapping) else None
    except (OSError, store.StorageError):
        bound = None
    if not base or not bound:
        return ["Review base: not recorded when the step began (outside a Git checkout, or its snapshot failed): review "
                "the change the step's result names against the Accepted step lines above."]
    return ["Review base (the step's change since it began, untracked files included): git -C " + str(state["repo"])
            + " diff " + str(base) + " " + str(bound) + " (" + str(base)[:12] + ": the working tree when the step "
            "began; " + str(bound)[:12] + ": when this review was bound; your own edits since then show in git status)."]
```

## result-shape — _canonical_result outcome and evidence_refs

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 910–943 at `c70a33f46ed7`.

```python
        _need(stage == "plan" and set(value) - {"headline"} == {
            "outcome", "summary", "evidence_refs", "reconciliation_target",
        }, "reconcile is allowed only as the exact plan result")
    else:
        _need("reconciliation_target" not in value,
              "reconciliation_target is allowed only with a reconcile result")
    if "headline" in value:
        headline = _text(value["headline"], "result headline")
        _need(headline != HEADLINE_PLACEHOLDER,
              "headline still holds the template placeholder; write one line for the user saying "
              "what this step established")
        _need("\n" not in headline and len(headline.strip()) <= HEADLINE_LIMIT,
              f"headline must be one line of at most {HEADLINE_LIMIT} characters")
    if outcome == "replan":
        _need(stage in guidance.OUTER and "work_items" in value,
              "replan requires corrective work_items at an outer stage")
    if "blocked_by" in value:
        _need(outcome == "blocked" and value["blocked_by"] in BLOCKED_BY,
              "blocked_by is only for a blocked result and must be user, access or external")
    result: dict[str, Any] = {
        "outcome": outcome,
        "summary": _text(value.get("summary"), "result summary"),
    }
    _need(" ".join(result["summary"].split()) not in _summary_placeholders(),
          "summary still holds the template placeholder; write what the placeholder asks for")
    if "headline" in value:
        result["headline"] = value["headline"].strip()
    refs = value.get("evidence_refs", [])
    _need(isinstance(refs, list), "evidence_refs must be a list")
    _need(EVIDENCE_PLACEHOLDER not in refs,
          "evidence_refs still holds the template placeholder; list the absolute path of each "
          "file this stage wrote or of the check output it recorded")
    result["evidence_refs"] = [
        _text(reference, "evidence reference") for reference in refs
```

## scope — _IMPLEMENT_SCOPE_INLINE

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 724–728 at `c70a33f46ed7`.

```python
_IMPLEMENT_SCOPE_INLINE = """\
1. **Scope.** Do only this step: meet its criteria, nothing no criterion asks for, and break none of the item's
   other requirements. Earlier steps are accepted. Write no tests, start no later step, and leave unrelated code as is
   (no reformatting, no reverting). Existing tests, check scripts, golden or fixture files and thresholds are checks:
   change one only when a criterion says to.
```

## procedure — PROCEDURE_WALK and consumers

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 758–779 at `c70a33f46ed7`.

```python
# Procedure validity (implement-step fix plan 2026-10-17 section 4.2, unit W2-C): an ordered procedure can name
# repeatable actions and still be impossible.  A live run's release check asked for one more action after the state
# that allows it had ended, and passed every review handoff on the way.  The walk is worded once: the shared focus item
# below carries it to the spec and test-strategy duties and to every planning review, and test-spec's duty applies it to
# the cases that stage owns.
PROCEDURE_WALK = ("Walk it from its stated start: can the actor reach that start under recorded authority, can each "
                  "action occur in the state the preceding actions leave, can the chosen observer see the expected "
                  "result?")
_PROCEDURE_ITEM = textwrap.fill(
    "an ordered procedure (calls, commands, interactions) that cannot happen as written. " + PROCEDURE_WALK
    + " Use an existing local check where one fits. Record an unreachable start as an open prerequisite, revise an "
    "invalid action or oracle, claim no execution from a plan, and treat an observation made before its setup changed "
    "as stale", width=80, initial_indent="- ", subsequent_indent="  ", break_on_hyphens=False)[2:]
# Test-spec's duty item 4: the walk applied to the cases that stage owns, and where a procedure's locator rides, so the
# stages that quote the case or the open item (implement and its Improve, test, verify, system-test-author, the open
# item's consumer) run that one procedure rather than a copy.
_TEST_SPEC_PROCEDURE = textwrap.fill(
    "4. A case's setup and actions are an ordered procedure. " + PROCEDURE_WALK + " An unreachable start is an open "
    "prerequisite (item 7); an impossible action or unobservable oracle is revised here (a forbidden action is its own "
    "failure case). A procedure another record holds (HOME/architecture.md ## Real-boundary checks): its locator in "
    "`oracle` or the open item's `check`. A plan is not a run; a setup change makes an earlier observation stale.",
    width=117, subsequent_indent="   ", break_on_hyphens=False) + "\n"
```

## planning-focus — _REVIEW_FOCUS_ITEMS

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 785–808 at `c70a33f46ed7`.

```python
_REVIEW_FOCUS_ITEMS = (
    "a step, example or expected result that cannot be replayed exactly: name the\n"
    "  concrete inputs, values, identifiers and sample interactions",
    _PROCEDURE_ITEM,
    "an expected result or check that a weaker stand-in would pass: a hardcoded\n"
    "  value, a missing assertion, a title-only test, or an absent required name",
    "a documented command that does not run what it claims on the target runtime:\n"
    "  run it once and record the exit code and the cases it executes",
    "a required requirement, test ID or case dropped or weakened compared with the\n"
    "  prior accepted version",
    "a claim about what the runtime, platform or a library can do that a decision\n"
    "  depends on, with no primary-documentation source or probe result: check it,\n"
    "  and correct the plan where it is wrong",
)
# One line (the completeness test reads a bullet's first line): the steps condition, with the step check's two faults.
_REVIEW_FOCUS_STEPS = ("a missing prerequisite, wrong order or unowned verification, or a check that needs a later step's "
                       "work or passes by skipping a missing artifact, in the steps")


def _focus_list(items: tuple) -> str:
    return "".join("- " + item + (";" if index < len(items) - 1 else ".") + "\n" for index, item in enumerate(items))


REVIEW_FOCUS_CONDITIONS = _focus_list(_REVIEW_FOCUS_ITEMS + (_REVIEW_FOCUS_STEPS,))
```

## carry-focus — _improve_focus

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6502–6515 at `c70a33f46ed7`.

```python
def _improve_focus(state: Mapping[str, Any], child: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(the review focus, the Code craft rubric) for the reviewed stage; the rubric is [] where the focus has none."""
    stage = child["stage"]
    # The focus is numbered F1..Fn when FOCUS_IDS is on (U19); the Code craft rubric has no bullets, so the ids are the same
    # as ``focus_ids``, which counts the whole focus text.
    if stage in guidance.PLANNING_REVIEW_STAGES:
        return _numbered_focus(guidance.PLANNING_REVIEW_FOCUS.rstrip(), state, child), []
    if stage == "carry-forward":
        return _numbered_focus(guidance.END_REVIEW_FOCUS_HEAD.rstrip(), state, child), [guidance.CODE_CRAFT.rstrip()]
    if stage in stage_spec.with_improve("step"):
        return (_numbered_focus(_several_steps(guidance.IMPLEMENT_STEP_REVIEW_FOCUS_HEAD.rstrip(), state, stage), state,
                                child), [guidance.CODE_CRAFT.rstrip()])
    return [], []
```

## prepare-access — DUTIES[prepare]

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1225–1245 at `c70a33f46ed7`.

```python
    "prepare": """\
1. Prepare or verify the development and test environments the plan's items and HOME/environment.md name
   (Environment preparation guidance), using what the repository declares. Install nothing without authority.
2. Confirm by safe observation: isolation, runtime, configuration and data safety, access, fixture readiness,
   baseline identity (Workspace and return guidance).
3. Start each planned check's runner, the linters and the fixtures in their no-op form (a listing, dry run or help
   that proves it starts, not the suite); save the output and list each file in `evidence_refs`.
4. Baseline blocked by setup or access (Initial repository baseline guide): prepare only the approved prerequisite,
   keep the original observation, and rerun the original initial check on the unchanged product and tests before any
   dependent feature edit. Never replace it with an easier route or call the blocked baseline passed.
5. Recheck discovery's source-return trigger and the authorized delivery and verification route from the execution
   checkout before the first dependent work. If the return must precede a consumer check, record the ordering
   conflict in `summary` as unresolved. Never return early, deploy, or bypass the final-handoff return guard.
6. The consumer's access: name the consumer's account or role, the entry route the plan gives them and what reaching
   it needs (account, role, visibility, permission). Check it read-only, with the probe the target's platform guide
   names where it has one (GUIDES/platforms/), and record each prerequisite under HOME/environment.md ## Access and
   accounts; one still unresolved stays open there with its owner (who can grant it) and the stage that needs it.
   Create no grant; it does not block this stage.
7. Record readiness under HOME/environment.md ## Targets and runtimes and ## Commands: what was prepared, the
   commands that start each runner, the observations. Record not-applicable only when this candidate needs no
   preparation, with what you assessed. Missing required access or setup is blocked, not not-applicable.
```

## person-ask — DUTIES[release-verify]

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1787–1809 at `c70a33f46ed7`.

```python
4. Classify every selected case in `summary` passed, failed, blocked, not-run or justified N/A (Deployment and
   handoff guidance); reconcile each affected requirement clause with its case, required surface and due phase,
   checked surface, candidate, status and evidence. A pass on another surface only supports; source, HTTP or DOM
   structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and
   prerequisites. Check that no clause or case was dropped; claim no requirement met while a required observation
   is unrun.
5. A blocked or unknown check stays incomplete. Keep earlier receipts; do not release again blindly.
6. A case needing a signed-in browser or a person's action this host cannot perform: do not loop on it. Verify every
   other case first and record it as an open item in `assumptions` (who does what, where, and what they report). Only
   when the release cannot be accepted without it, report `blocked`, `awaiting` kind `present`, asked once: step 1
   reaches the consumer entry (menu entry or URL path) and says what to answer if it is missing or hidden; `report`
   is a fill-in list, one yes/no line per case with what to look for (`2. after <action>, <what shows>: yes/no`).
   The run's exclusions bind the run, not the person: ask what they changed. On the reply, recheck only the cases it
   answers, against the same release; an unanswered case is not-run, an open item for handoff quoting the reply, and
   the stage continues. Block again only when it answers none, or a required delivery-contract behavior obligation
   still has no passed observation (ask then only its lines).
7. Isolated run: this stage cannot return (Which checkout release-verify observes). A defect the checks find in the
   delivered result goes through `replan` with one corrective work item; release then returns the fix. Write
   nothing inside the user's checkout (a file there makes the return receipt stale and blocks handoff).
8. Local-only work: verify the current local candidate and its consumer behaviour; external activation N/A does not
   make these checks N/A.
9. A material change to code, tests, fixtures, configuration or target invalidates the observations it affects:
   rerun those, reuse the rest only with identity and relevance stated.
```

## delivery-gate — validate_transition and validate_terminal

Source: `skills/shiploop/scripts/shiploop_consumer_delivery.py`, lines 657–707 at `c70a33f46ed7`.

```python
def validate_transition(
    state: Mapping[str, Any], action_id: str, stage: str, result: Mapping[str, Any]
) -> dict[str, Any]:
    """Reject declared false completion without mutating navigator state."""
    projection = _project_submission(state, action_id, stage, result)
    if result["outcome"] != "done":
        return projection
    if stage == "plan":
        _need(projection["contract"] is not None,
              "delivery contract is required before successful plan")
        _need(projection["replan_required"] is None, projection["replan_required"])
    elif stage == "system-test":
        _need(not _pending(projection, phase="system-test"),
              "required pre-update obligations are not current")
    elif stage in RELEASE_GATED_STAGES:
        if stage != "release-plan":
            _need(projection["replan_required"] is None, projection["replan_required"])
        _require_release_ready(projection)
        if stage == "release":
            _need(not _pending(projection, phase="release"),
                  "required release obligations need effect and identity observations")
        elif stage == "release-verify":
            _need(not _pending(projection, phase="release"),
                  "required release obligations need current effect and identity observations")
            _need(not _pending(projection, phase="release-verify"),
                  "required release-verify behavior obligations are not current")
        elif stage in {"operations", "handoff"}:
            _need(not _pending(projection),
                  "required consumer-delivery obligations remain unfinished")
    return projection


def validate_terminal(state: Mapping[str, Any]) -> None:
    """Reject a structurally complete marked state with declared work still due."""
    if (type(state.get("delivery_contract_version")) is not int
            or state.get("delivery_contract_version") != DELIVERY_CONTRACT_VERSION):
        return
    if state.get("status") != "done":
        return
    projection = project(state)
    contract = projection["contract"]
    _need(isinstance(contract, Mapping),
          "completed consumer-delivery run has no accepted delivery contract")
    _need(projection["replan_required"] is None, projection["replan_required"])
    _need(contract["necessity"] != "unresolved",
          "completed consumer-delivery run has unresolved delivery necessity")
    if contract["necessity"] == "required":
        _need(contract["authority"]["status"] == "approved",
              "completed consumer-delivery run has unresolved delivery authority")
    _need(not _pending(projection),
          "completed consumer-delivery run has unfinished required obligations")
```

## delivery-correction — _requires_user_correction

Source: `skills/shiploop/scripts/shiploop_consumer_delivery.py`, lines 352–367 at `c70a33f46ed7`.

```python
def _requires_user_correction(prior: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    # Candidate changes describe a new artifact under the same requested
    # delivery outcome.  They can demand replanning, but are not themselves a
    # user scope reduction.  All other delivery requirement changes are.
    for key in ("consumer", "target", "behavior", "operation", "necessity", "exclusions", "authority"):
        if prior[key] != current[key]:
            return True
    previous = {row["id"]: row for row in _required_rows(prior)}
    replacement = {row["id"]: row for row in _required_rows(current)}
    for identifier, row in previous.items():
        replacement_row = replacement.get(identifier)
        if replacement_row is None or not _same_obligation(row, replacement_row):
            return True
    # Adding a new required check preserves (and can strengthen) the prior
    # outcome; it does not require the user to re-approve the existing scope.
    return False
```

## correction-project — project contract correction/replan

Source: `skills/shiploop/scripts/shiploop_consumer_delivery.py`, lines 505–527 at `c70a33f46ed7`.

```python
                if previous is None:
                    _need("supersedes" not in assessment and "correction" not in assessment,
                          "initial delivery contract cannot supersede or correct another contract")
                    retained: dict[str, dict[str, Any]] = {}
                else:
                    _need(assessment.get("supersedes") == projection["anchor"],
                          "delivery contract correction must supersede the current contract anchor")
                    if _requires_user_correction(previous, assessment["contract"]):
                        _need("correction" in assessment,
                              "delivery correction needs a user-approved correction source")
                    retained = _preserved_observations(
                        projection["observations"], previous, assessment["contract"]
                    )
                    material_change = _material_post_plan_change(
                        previous, assessment["contract"]
                    )
                    if post_plan_replan_pending and material_change:
                        fresh_system_test_after_replan = False
                    if (release_plan_completed
                            and entry["stage"] in _POST_RELEASE_PLAN_MUTATION_STAGES
                            and material_change):
                        projection["replan_required"] = _REPLAN_MESSAGE
                projection["contract"] = deepcopy(assessment["contract"])
```

## delivery-template — template_assessment authority fill

Source: `skills/shiploop/scripts/shiploop_consumer_delivery.py`, lines 727–751 at `c70a33f46ed7`.

```python
    if contract is None:
        common = {
            "consumer": "...",
            "target": "...",
            "candidate": "...",
        }
        return {
            "kind": "contract",
            "contract": {
                **common,
                "behavior": "...",
                "operation": "...",
                "necessity": "unresolved",
                "basis": "...",
                "exclusions": [],
                # The authority's target and operation are the contract's: ShipLoop fills them in (``_authority``).
                "authority": {
                    "status": "unresolved",
                    "kind": "user-decision",
                    "reference": "...",
                },
                # This is a valid minimal early declaration.  When necessity
                # becomes required, add required effect, identity, and
                # behavior rows as described in the linked reference.
                "obligations": [],
```

## settling-template — _settling_template

Source: `skills/shiploop/scripts/shiploop_consumer_delivery.py`, lines 798–820 at `c70a33f46ed7`.

```python
    contract = projection["contract"]
    authority = {key: value for key, value in contract["authority"].items() if key not in ("target", "operation")}
    if authority["status"] != "approved":
        authority["status"] = SETTLE_STATUS
    correction = {"kind": authority["kind"], "reference": SETTLE_REFERENCE}
    if "approval_ref" in authority:
        correction["approval_ref"] = authority["approval_ref"]
    rows = [dict(row) for row in contract["obligations"]]
    required = {row["kind"] for row in rows if row["required"] is True}
    ids = {row["id"] for row in rows}
    for kind in ("effect", "identity", "behavior"):
        if kind in required:
            continue
        identifier, number = "O-" + kind, 2
        while identifier in ids:
            identifier, number = f"O-{kind}-{number}", number + 1
        ids.add(identifier)
        rows.append({"id": identifier, "consumer": contract["consumer"],
                     "target": contract["target"] if kind != "behavior" else "...", "kind": kind,
                     "phase": _PHASE_FOR_KIND[kind], "expected": "...", "required": True})
    settled = {key: deepcopy(value) for key, value in contract.items() if key not in ("authority", "obligations")}
    return {"kind": "contract", "supersedes": projection["anchor"], "correction": correction,
            "contract": {**settled, "necessity": SETTLE_NECESSITY, "authority": authority, "obligations": rows}}
```

## judge — judge

Source: `skills/shiploop/scripts/shiploop_test_loop.py`, lines 609–633 at `c70a33f46ed7`.

```python
def judge(row: Mapping[str, Any], code: Optional[int], output: str) -> Dict[str, Any]:
    """Classify one finished candidate run from its exit code and its own output.

    ``passed`` needs exit 0, a recognised count of at least ``min_tests`` (1 by default) and every listed ID shown; a
    focused command whose count cannot be read passes only when it lists IDs and all appear.  A regression command
    without ids or min_tests may pass uncounted.  A check is judged by its exit code, but a runner summary in its output
    must show a test ran.
    """
    tally = counts.count(output, code)
    if row.get("suite") == "check":
        # A runner recorded as a check must not pass by running nothing (a release-verify `node --test` did so with
        # counts null).
        if code == 0 and tally is not None and tally["ran"] == 0:
            return {"counts": tally, "ids_missing": [], "status": "no-tests"}
        return {"counts": tally, "ids_missing": [], "status": "passed" if code == 0 else "failed"}
    ids = list(row.get("ids") or ())
    names = counts.named(output, ids) if ids else {"shown": [], "missing": []}
    minimum = int(row.get("min_tests") or 1)
    verdict: Dict[str, Any] = {"counts": tally, "ids_missing": names["missing"]}
    if names.get("inside"):
        verdict["ids_inside"] = names["inside"]
    if code != 0:
        verdict["status"] = "no-tests" if tally is not None and tally["ran"] == 0 else "failed"
    elif tally is not None and tally["ran"] == 0:
        verdict["status"] = "no-tests"
```

## id-outcomes — outcomes

Source: `skills/shiploop/scripts/shiploop_test_counts.py`, lines 268–290 at `c70a33f46ed7`.

```python
def outcomes(output: str, ids: Sequence[str]) -> Dict[str, str]:
    """Per declared ID, what the output says about that one test: ``failed``, ``passed``, ``shown`` or ``missing``.

    Built on ``named``'s line rule: only a non-skip line holding the ID as its own word counts.  ``failed`` when such a
    line carries the runner's failure mark (or follows unittest's ``FAIL:``/``ERROR:`` header), else ``passed`` when one
    carries its pass mark, else ``shown`` (named, but no line says how it ended: a reporter that marks no outcome), and
    ``missing`` when no line names it (it did not run, or the file holding it failed to load).
    """
    lines = [line for line in _plain(output).splitlines() if not _ANNOUNCEMENT.match(line)]
    result: Dict[str, str] = {}
    for test_id in ids:
        pattern = _id_pattern(test_id)
        hits = [index for index, line in enumerate(lines) if pattern.search(line) and not _SKIP_LINE.search(line)]
        if not hits:
            result[test_id] = "missing"
        elif any(_FAIL_LINE.search(lines[index]) or (index and _FAIL_HEADER.match(lines[index - 1]))
                 for index in hits):
            result[test_id] = "failed"
        elif any(_PASS_LINE.search(lines[index]) for index in hits):
            result[test_id] = "passed"
        else:
            result[test_id] = "shown"
    return result
```

## base-order — _test_loop_gate

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 3733–3749 at `c70a33f46ed7`.

```python
        if check_only:
            ok, lines = test_loop.red_check(root, state, workitem or "", action_id, submitted,
                                            base_commit=preparatory_base(root, workitem or ""))
            _need(ok, "\n".join(["ShipLoop check-only: the base run would refuse this result:"] + lines))
            found = [line for line in lines if line.startswith("base: ")]
            found += test_loop.loop_run(root, state, workitem or "", action_id, submitted, count=False)
            found += test_loop.mutation_check(root, state, workitem or "", action_id, submitted, count=False,
                                              base_commit=preparatory_base(root, workitem or ""))
            return ["Gates: " + line for line in found]
        found = test_loop.base_check(root, state, workitem or "", action_id, submitted,
                                     base_commit=preparatory_base(root, workitem or ""))
        found += test_loop.loop_run(root, state, workitem or "", action_id, submitted)
        # On new code the base run can only see a load failure (RED by rule); the mutation check is what proves the
        # tests assert real behaviour (owner decision 2026-10-11).
        found += test_loop.mutation_check(root, state, workitem or "", action_id, submitted,
                                          base_commit=preparatory_base(root, workitem or ""))
        return ["Gates: " + line for line in found]
```

## mutation-restore — _check local finally

Source: `skills/shiploop/scripts/shiploop_mutation.py`, lines 281–310 at `c70a33f46ed7`.

```python
        with tree as cwd:
            record["cwd"] = str(cwd)
            status, by, seconds = _run_focused(runner, commands, cwd, test_loop.COMMAND_TIMEOUT_SECONDS, environment,
                                               clock, deadline)
            record["unmutated"] = {"status": "passed" if status == "survived" else status, "by": by,
                                   "seconds": round(seconds, 3)}
            if status != "survived":
                record["skipped"] = ("the unmutated copy did not pass its focused commands (" + status + ": " + by
                                     + "), so no mutant can be judged there")
                return record
            timeout = min(MUTANT_TIMEOUT_SECONDS, seconds * MUTANT_TIMEOUT_FACTOR + MUTANT_TIMEOUT_SLACK_SECONDS)
            for mutant in chosen:
                target = tree.tree / mutant["file"]
                original = target.read_bytes()
                lines = texts[mutant["file"]].splitlines(keepends=True)
                line = lines[mutant["line"] - 1]
                ending = line[len(line.rstrip("\r\n")):]
                lines[mutant["line"] - 1] = mutant["mutated"] + ending
                try:
                    target.write_bytes("".join(lines).encode("utf-8"))
                    status, by, seconds = _run_focused(runner, commands, cwd, timeout, environment, clock, deadline)
                finally:
                    target.write_bytes(original)
                row = {key: mutant[key] for key in ("file", "line", "column", "operator", "original", "replacement")}
                row["file"] = test_loop._relative(mutant["file"], base)
                row.update(status=status, seconds=round(seconds, 3))
                if by:
                    row["by"] = by
                record["mutants"].append(row)
    except (test_loop.TestLoopError, lint.LintError, OSError) as exc:
```

## mutation-record — mutation_check

Source: `skills/shiploop/scripts/shiploop_mutation.py`, lines 325–358 at `c70a33f46ed7`.

```python
def mutation_check(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
                   result: Optional[Mapping[str, Any]] = None, *, count: bool = True,
                   base_commit: Optional[str] = None, runner: Any = None,
                   env: Optional[Mapping[str, str]] = None, clock: Optional[Callable[[], float]] = None,
                   budget: float = MUTATION_BUDGET_SECONDS, **_options: Any) -> List[str]:
    """The test stage's mutation check, after ``loop_run`` passed; raises ``TestLoopError`` with the refusal.

    Writes ``tests/<action>-mutation<N>.md`` (``count=False``: ``tests/<action>-mutation-check-only.md``, never
    counted) and returns its summary line.  Refused only when at least one mutant ran and none was killed; that
    refusal counts toward ``MAX_REFUSED_RUNS``.  ``result`` is accepted for the gate's uniform call and not read.
    """
    del result
    root = Path(root)
    refused = test_loop.refused_runs(root, action_id)
    if count and refused >= test_loop.MAX_REFUSED_RUNS:
        raise test_loop.TestLoopError(test_loop._cap_refusal(root, test_loop.STAGES[0], refused, str(
            root / mutation_path(action_id, test_loop._mutation_count(root, action_id)))))
    started = time.monotonic()
    record = _check(root, state, work_item, base_commit=base_commit, runner=runner, env=env, clock=clock,
                    budget=budget)
    record["action"] = action_id
    record["seconds"] = round(time.monotonic() - started, 3)
    refuse = bool(record["mutants"]) and record["killed"] == 0 and record["survived"] > 0
    # A check that could not judge anything (no focused command, no item base, no mutant, a copy that was not green)
    # passes, and says ``skipped`` so no reader takes it for a proof; one that refused is ``failed`` as before.
    record.update(passed=not refuse,
                  disposition="failed" if refuse else "skipped" if record.get("skipped") else "passed")
    if count:
        record["attempt"] = test_loop._next_attempt(root, action_id)
        relative = mutation_path(action_id, test_loop._mutation_count(root, action_id) + 1)
    else:
        record["counted"] = False
        relative = test_loop.mutation_check_only_path(action_id)
    store.atomic_write_text(root / relative, store.dumps(record, "ShipLoop test mutation check"))
```

## command-reuse — _reused

Source: `skills/shiploop/scripts/shiploop_test_loop.py`, lines 1082–1107 at `c70a33f46ed7`.

```python
def _reused(root: Path, action: str, stage: str, work_item: str, commands: Sequence[Mapping[str, Any]], repo: Path,
            held: Mapping[str, Mapping[str, Any]]) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """The runs of this action's passed check-only record, held to today's floors, when ``complete`` takes them instead
    of running every command again (owner decision D5, 2026-10-17); else None.

    It takes them when that record passed at this stage and item, lists exactly ``commands``, and the repository's
    working content (``_tree``) is now a tree the check-only run started on or left.  A run the floor now refuses is
    not taken: the commands run again, so a refusal always comes from a run made now.  Returns (runs, the ``reused``
    entry the counted record carries: which check-only record and the tree).
    """
    path = Path(root) / check_only_path(action)
    if not path.is_file():
        return None
    try:
        record = store.read_record(path)
    except (OSError, store.StorageError):
        return None
    if not (isinstance(record, Mapping) and record.get("passed") is True and record.get("stage") == stage
            and record.get("work_item") == work_item and record.get("commands") == list(commands)
            and record.get("trees")):
        return None
    tree = _tree(root, repo)
    if not tree or tree not in record["trees"]:
        return None
    runs: List[Dict[str, Any]] = []
    for run in record.get("runs") or ():
```

## progress — implement_progress

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 2403–2418 at `c70a33f46ed7`.

```python
def implement_progress(state: Mapping[str, Any], work_item: str | None) -> tuple[int, list[dict[str, Any]]]:
    """(accepted implement steps, the item's steps) since its latest accepted step plan.

    Derived from history: a recovered or compacted host gets the same answer
    from the run's durable record, and saved runs need no new field.
    """
    if work_item is None:
        return 0, []
    action, plan = test_loop._step_plan(state, work_item)
    steps = list(plan.get("steps") or ()) if action else []
    history = list(state.get("history", ()))
    start = max((position for position, row in enumerate(history) if row.get("action") == action), default=-1)
    done = sum(1 for row in history[start + 1:]
               if row.get("stage") == "implement" and row.get("workitem") == work_item
               and row.get("outcome") == "done")
    return done, steps
```

## revisit — _revisit_lines

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 766–795 at `c70a33f46ed7`.

```python
def _revisit_lines(state: Mapping[str, Any], stage: str, workitem: str | None) -> list[str]:
    """The four lines of a revisited stage's head (``_sent_back_results``): why it is back, its previous accepted result,
    what changed upstream, and the rule to keep unchanged rows with their IDs.

    ``planning_revision.current_actions`` drops the item's earlier results from "Results this stage builds on" once it
    is sent back, so a model holding only this packet could not find what it is asked to amend.  The files are the ones
    ``_new_result_records`` always writes.  Tier P1: before 2026-10-17 the lines were file-only (packet review C2-1).
    """
    if state["status"] != "active" or state.get("active_improve"):
        return []
    sent = _sent_back_results(state, stage, workitem)
    if sent is None:
        return []
    revise = state["accepted"][sent.sent_back]
    by = next(row["stage"] for row in state["history"] if row["action"] == sent.sent_back)
    summary = " ".join(_bounded_packet_text(str(revise.get("summary", "")), limit=REVISIT_SUMMARY).split())
    previous = ("RUN/results/" + sent.previous + ".md (accepted host report, untrusted; revalidate what you carry over)"
                if sent.previous else "none (this stage had no accepted result for " + str(workitem)
                + " before the revise)")
    return [
        f"Revisit: {by} sent {workitem} back to {stage_spec.REVISE_TO} ({sent.count} of {stage_spec.MAX_REVISES} "
        "revises)" + ("; this packet asks for an amended plan, not a new one" if stage == stage_spec.REVISE_TO else "")
        + ". Why (its summary, untrusted): \"" + summary + "\" Evidence: RUN/results/" + sent.sent_back + ".md.",
        "Your previous accepted " + stage + " result: " + previous + "."
        + (" The tree may hold an earlier attempt's edits: git status shows them." if stage == "implement" else ""),
        _upstream_line(state, stage, str(workitem), sent),
        "Keep unchanged rows with their IDs: carry over as written every row the revise result and the changes above do "
        "not touch; change or add only what they require."
        + (" Submit the whole amended plan: it replaces the previous one." if stage == stage_spec.REVISE_TO else ""),
    ]
```

## reviewed-input — _reviewed_input_lines

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6433–6445 at `c70a33f46ed7`.

```python
def _reviewed_input_lines(root: Path, state: Mapping[str, Any], stage: str, workitem: str | None) -> list[str]:
    """What the reviewed stage read and was handed, named by file (U2 of the 2026-10-17 packet review: 60-65 KB of each
    68-98 KB handoff re-quoted what the producer packet holds).  Its packet lists the knowledge files by contents and quotes
    the hand-offs by value; the handoff names both files and keeps by value only the criteria the stage was handed, which
    its result is checked against.  A revisit also names the previous accepted result and the revise result."""
    action = state["active_improve"]["action_id"]
    lines = ["What the reviewed stage read and was handed (untrusted host records; open the parts its result cites): its "
             "packet RUN/" + PACKET_DIR + "/" + action + ".md and its result RUN/inbox/" + action + ".md."]
    quotes = knowledge.reads_quotes(state, stage) if stage in knowledge.READS else []
    if quotes:
        lines.append("- Knowledge files, listed there by contents: " + "; ".join(
            "HOME/" + quote.file + " (" + (_size(quote.text) if quote.text is not None else "not written yet") + ")"
            for quote in quotes) + ".")
```

## consumer-example — _CONSUMER_PLACEHOLDER

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 4054–4065 at `c70a33f46ed7`.

```python
# one of them, as the headline and evidence placeholders are refused.
FOLLOWS_PLACEHOLDER = "<R-<n> or AD-<n> this item follows>"
# One test case's placeholders live with its shape (expectations.CASE_PLACEHOLDERS), which every refusal prints too.
_CASE_PLACEHOLDERS = expectations.CASE_PLACEHOLDERS
_BEHAVIOUR_PLACEHOLDER = "<behaviour this step added that no test case covers>"
_REASON_PLACEHOLDER = "<why no test case covers it>"
_LESSON_PLACEHOLDERS = {"learned": "<what this run learned>",
                        "considerations": "<the decisions and risks that matter next time>",
                        "open_next": "<what a later run should pick up, or none>"}
_CONSUMER_PLACEHOLDER = "<a later outer stage, or carry-forward from test-spec or verify>"
HANDOFF_PLACEHOLDERS = (FOLLOWS_PLACEHOLDER, *_CASE_PLACEHOLDERS.values(), _BEHAVIOUR_PLACEHOLDER, _REASON_PLACEHOLDER,
                        *_LESSON_PLACEHOLDERS.values(), _CONSUMER_PLACEHOLDER)
```

## consumer-enum — allowed_consumers

Source: `skills/shiploop/scripts/shiploop_assumptions.py`, lines 147–156 at `c70a33f46ed7`.

```python
def allowed_consumers(stage: str) -> Tuple[str, ...]:
    """The consumers an open item at an open-item ``stage`` may name, in graph order.

    A later OUTER stage, or ``carry-forward`` (the same item's) when the producer is test-spec or verify.  Work for a
    later work item goes through carry-forward's work_items, as before (K12).
    """
    order = stage_spec.STAGES
    later = [name for name in stage_spec.OUTER if order.index(name) > order.index(stage)]
    return tuple((["carry-forward"] if stage in CARRY_FORWARD_PRODUCERS else []) + later)
```

## loop-stop-semantics — unchanged review completion gates

Source: `skills/shiploop/scripts/shiploop_standalone_improve.py`, lines 615–637 at `c70a33f46ed7`.

```python
# The runtime's required_trivial_reviews values for "trivial, and the content is unchanged": 2 ends the review on one such
# pass, 3 (code reviews) on the first pass or on two in a row once a pass has changed the content.  Both complete only on
# a pass the runtime measured unchanged, so the terminal check below is the same for both.
_UNCHANGED_GATES = (2, 3)
_PROGRESS_KEYS = {"action_number", "required_trivial_reviews", "last_pass_changed_tree"}
_OLDER_RUNTIME = (
    "Until Loop {kind} packet was written by an older Until Loop (it counts a trivial streak or reports "
    "unchanged_first_pass), which ShipLoop no longer imports: the Improve review now ends on a trivial pass that "
    "leaves the content unchanged (a code review: two in a row once a pass has changed it). Preserve this run; start "
    "new work with init or workspace start in a fresh --run-dir"
)


def _progress(value: Any, kind: str) -> Mapping[str, Any]:
    """The Improve child's progress as the bundled runtime reports it at its unchanged-content gate."""
    _need(isinstance(value, Mapping), f"Until Loop {kind} progress has an invalid schema")
    gate = value.get("required_trivial_reviews")
    # The older runtime counted a streak at this gate and reported unchanged_first_pass; the current one never does.
    _need("unchanged_first_pass" not in value and not ("trivial_streak" in value and gate in _UNCHANGED_GATES),
          _OLDER_RUNTIME.format(kind=kind))
    _need(gate in _UNCHANGED_GATES, f"Until Loop {kind} packet was not run at Improve's unchanged-content review gate")
    _need(set(value) == _PROGRESS_KEYS, f"Until Loop {kind} progress has an invalid schema")
    changed = value["last_pass_changed_tree"]
```

## metrics-reviews — improve_reviews

Source: `test/shiploop_e2e/metrics.py`, lines 605–621 at `c70a33f46ed7`.

```python
def improve_reviews(run_dir: Path | None) -> dict:
    """Review passes per Improve child, from the review notes the run's worktree keeps.

    A child's passes are its review-<n>.md files; seconds is the time between its first and last note, so a long
    child shows where review passes, not stages, spent the run. Used to decide whether repeat passes are wasted.
    """
    root = run_dir.parent / "worktree" / ".shiploop-improve" if run_dir else None
    children = []
    for reviews in sorted(root.glob("*/*/reviews")) if root and root.is_dir() else []:
        notes = sorted(reviews.glob("review-*.md"))
        if notes:
            stamps = [n.stat().st_mtime for n in notes]
            children.append({"child": reviews.parent.name, "passes": len(notes),
                             "seconds": round(max(stamps) - min(stamps), 1),
                             "bytes": sum(n.stat().st_size for n in notes)})
    return {"children": len(children), "passes": sum(c["passes"] for c in children),
            "max_passes": max((c["passes"] for c in children), default=0), "per_child": children}
```

## case-shape — TEST_CASE_KEYS and placeholders

Source: `skills/shiploop/scripts/shiploop_expectations.py`, lines 91–105 at `c70a33f46ed7`.

```python
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
# A test-spec result's cases (consumer contract 3.3, D4: no surface key; the oracle names it).
TEST_CASE_KEYS = ("id", "criterion", "requirement", "oracle", "red", "green")
# What the printed shape holds in each field, and the only values the template and every refusal print: a placeholder,
# never an example ID.  An example ID is accepted wherever such an ID exists, so a copied row mapped a case to the wrong
# requirement silently, and a model copied a refusal's example requirement and wrote a spec entry to match (2026-10-17,
# SPEC-3/X-5).  A row that keeps a placeholder is refused as one (the navigator's HANDOFF_PLACEHOLDERS lists these).
CASE_PLACEHOLDERS = {"id": "<a focused command ID>", "criterion": "<a step-plan criterion id>", "requirement": "R-<n>",
                     "oracle": "<what observes the behaviour, and where>", "red": "<how the case fails before the change>",
                     "green": "<what the case shows once the change works>"}
_TEST_CASE_SHAPE = "test_cases are " + json.dumps([{key: CASE_PLACEHOLDERS[key] for key in TEST_CASE_KEYS}])
# The test-spec template prints at most this many skeleton rows (about 220 characters each); the focused IDs after them are
# named in one line.  A plan with dozens of IDs would otherwise push the head past the host's 20,000-character print, and a
# host that elides the middle of a long print would drop template rows that the gate requires.
SKELETON_ROWS = 12
```

## case-coverage — coverage_notices

Source: `skills/shiploop/scripts/shiploop_expectations.py`, lines 516–534 at `c70a33f46ed7`.

```python
def coverage_notices(state: Mapping[str, Any], result: Mapping[str, Any]) -> List[str]:
    """A counted notice per step-plan criterion that nothing confirms: never a refusal (SPEC-6).

    A criterion is confirmed by a test case naming it, by a recorded command that is not a focused one and lists it in
    ``criteria``, or by an open item of the result that names it.  The plan's exit condition 1 (every criterion has a
    case or a justified not-applicable) is otherwise a clause of the free-text summary.  Reads state only.
    """
    _item, plan = _plan_of(state)
    criteria = [str(row.get("id")) for row in plan.get("criteria") or () if isinstance(row, Mapping) and row.get("id")]
    covered = {str(case.get("criterion")) for case in result.get("test_cases") or () if isinstance(case, Mapping)}
    for row in plan.get("test_commands") or ():
        if isinstance(row, Mapping) and row.get("suite") != "focused":
            covered |= {str(name) for name in row.get("criteria") or ()}
    said = " ".join(str(row.get(key) or "") for row in result.get("assumptions") or () if isinstance(row, Mapping)
                    for key in ("assumption", "check", "reason"))
    return [COVERAGE_PREFIX + "Criterion " + name + " has no test case and no recorded non-focused command lists it in "
            "criteria: add a case, add the command to the step plan, or record an assumptions open item naming the "
            "inspection that confirms it (this result is accepted)."
            for name in criteria if name not in covered and not re.search(r"\b" + re.escape(name) + r"\b", said)]
```

## case-gate — check_test_cases

Source: `skills/shiploop/scripts/shiploop_expectations.py`, lines 555–580 at `c70a33f46ed7`.

```python
    cases = list(result.get("test_cases") or ())
    shape = ('Shape: {"id", "criterion", "requirement", "oracle", "red", "green"}, one per ID this item\'s focused '
             'commands list. The implement, test, verify and system-test-author packets quote them.')
    if not cases:
        if not focused:
            return None
        return ("Add test_cases to {result}", "adds test_cases", [shape, "Focused IDs: " + ", ".join(focused) + "."])
    unlisted = [case["id"] for case in cases if case["id"] not in focused]
    if unlisted:
        return ("Fix the case IDs in {result}", "fixes the case IDs",
                ["Give every case an ID this item's focused commands list, or report revise so the step plan lists it.",
                 "Not listed by a focused command of " + str(work_item) + ": " + ", ".join(unlisted) + "."])
    have = {case["id"] for case in cases}
    missing = [ident for ident in focused if ident not in have]
    if missing:
        return ("Add the missing cases to {result}", "adds the cases",
                ["Add a case to test_cases for every ID this item's focused commands list. " + shape,
                 "Focused IDs with no case: " + ", ".join(missing) + "."])
    criteria = [str(row.get("id")) for row in plan.get("criteria") or () if isinstance(row, Mapping)]
    wrong = [case["id"] + " names " + case["criterion"] for case in cases if case["criterion"] not in criteria]
    if wrong:
        return ("Fix the case criteria in {result}", "fixes the criteria",
                ["Set each case's criterion to a criterion of this item's step plan.",
                 "; ".join(wrong) + "; the criteria are " + (", ".join(criteria) or "none") + "."])
    spec = Path(str(state["repo"])) / knowledge.HOME / "spec.md"
    entries = knowledge.entries(Path(str(state["repo"])), "spec.md")
```

## parent-return — Improve parent-return file

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 7983–7996 at `c70a33f46ed7`.

```python
        "## The parent's return", "",
        "Only after the runtime wrote a complete terminal packet to " + str(receipt) + ", run:",
        _callback(core, root, "complete", action=improve_id(state)),
        "The child never runs the complete command; a stopped or blocked child leaves the Improve stage pending.",
        ""]))
    start = receipt.with_name("start.json")
    store.atomic_write_text(start, loop_contract.dumps(contract))
    state_dir = root / "until-loop"
    state_dir.mkdir(exist_ok=True)
    try:
        done = subprocess.run(
            [sys.executable, "-B", child["skill"]["runtime_cli"], "start", "--directory", str(state_dir),
             "--receipt", str(receipt)],
            input=json.dumps(contract, ensure_ascii=False).encode("utf-8"), capture_output=True, timeout=60,
```

## work-items — Improve outcome guidance

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 6348–6359 at `c70a33f46ed7`.

```python
            described.append("revise (the item's step plan or test spec is wrong or unachievable: it goes "
                             "back to " + stage_spec.REVISE_TO + " with this result as evidence; "
                             + str(left) + " of " + str(stage_spec.MAX_REVISES) + " left for this item)")
        else:
            described.append(outcome)
    outcomes = " | ".join(described)
    lines = ["Allowed outcomes: " + outcomes + "."]
    if stage == "plan":
        lines.append("Optional work_items replaces the whole queue: list every item in order, not a delta.")
    elif stage == "carry-forward":
        lines.append("Optional work_items replaces the queue after this item: list every still-required "
                     "future item in order, not a delta.")
```

## notes-file — Improve parser flags

Source: `skills/shiploop/scripts/shiploop_protocol.py`, lines 620–634 at `c70a33f46ed7`.

```python
            # improve stage takes no result (--final-result is its changed result).
            sub.add_argument("--result", help="the result file; default and only accepted path: RUN/inbox/<action>.md")
        if name == "complete":
            sub.add_argument("--check-only", dest="check_only", action="store_true",
                             help="run this stage's script gates on the result and report, without completing the "
                                  "action (an Until Loop's way to observe its exit conditions before done)")
        if name == "complete":
            sub.add_argument("--notes", metavar="FILE",
                             help="optional: the path of a plain-text file (not the text itself) holding the review's "
                                  "lessons for later steps; the handoff names the file to write")
            sub.add_argument("--final-result", dest="final_result",
                             help="optional step-result record, only when the review changed a decision")
            sub.add_argument("--no-commit", dest="no_commit",
                             help="the user's or repository's instruction not to commit the review's edits")
        if name == "context":
```

## guide-lines — _stage_guide_lines

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 4748–4757 at `c70a33f46ed7`.

```python
def _stage_guide_lines(core: Any, state: Mapping[str, Any], stage: str, named: str | None) -> list[str]:
    """The stage's guides (``STAGE_REFERENCES``), each as ``<label>: <path>``: those whose label the text ``named``
    names, or every one (``named`` None)."""
    reference_dir = _reference_dir(core)
    route = delegation(state)
    return [label + ": " + str(reference_dir / reference)
            for label, reference in guidance.STAGE_REFERENCES.get(stage, ())
            # Inline runs execute reviewed steps directly and never bind a chain.
            if not (route == guidance.INLINE and label == "Parallel-chain guide")
            and (named is None or label in named)]
```

## guide-head — _cited_guides

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 4768–4789 at `c70a33f46ed7`.

```python
def _cited_guides(core: Any, root: Path, state: Mapping[str, Any], stage: str, stage_text: str) -> CitedGuides:
    """What an active producer's guidance cites by label, with the locator, and what only the file keeps.

    A guide or policy the stage text names ("Repeatable test-suite guide", "Interaction design guide") prints with its
    path unless the text already prints that guide's path (a duty that says "Plan record guide (GUIDES/plan-record.md)").
    The Backchain lines print with the paragraph or line that cites them; the loop-resource status only where the text
    names its "Loop resources" line.  Before 2026-10-17 all of them were file-only, so a head cited a guide it did not
    locate and the model searched the packet file for it (packet review F3, A AX-2, E C-1, G29-2 and G32-1).
    """
    reference_dir = _reference_dir(core)
    stage_text = " ".join(stage_text.split())  # the duties wrap: a label may break across two lines
    labels = {label for label, _ in guidance.STAGE_REFERENCES.get(stage, ())}
    located = {label for label, reference in guidance.STAGE_REFERENCES.get(stage, ())
               if "GUIDES/" + reference.split("#", 1)[0] in stage_text}
    every = _stage_guide_lines(core, state, stage, None)
    guides = [line for line in _stage_guide_lines(core, state, stage, stage_text)
              if line.split(": ", 1)[0] not in located]
    guides += [label + ": " + str(reference_dir / target) for label, target in run_reference.POLICIES
               if label in stage_text and label not in labels]
    backchain = _backchain_lines(core, root, state, stage)
    cited = [line for line in backchain if not line.startswith("Loop resources ") or "Loop resources" in stage_text]
    return CitedGuides(guides, cited, [line for line in every if line not in guides],
```

## recent-commits — recent_commits

Source: `skills/shiploop/scripts/shiploop_knowledge_home.py`, lines 174–181 at `c70a33f46ed7`.

```python
def recent_commits(repo: Path, count: int = 3) -> List[str]:
    """The last ``count`` commit messages (subject and body) of the checkout, newest first."""
    if not (Path(repo) / ".git").exists():
        return []  # not a checkout (for example a graph dry run): nothing to read, nothing run
    shown = _git(Path(repo), "log", "-" + str(count), "--format=%h %B%x00")
    if shown.returncode:
        return []
    return [entry.strip() for entry in shown.stdout.split("\0") if entry.strip()]
```

## review-authority — Improve authority prompt

Source: `skills/shiploop/scripts/shiploop_navigator.py`, lines 7912–7923 at `c70a33f46ed7`.

```python
        "## Scope",
        *scope,
        "",
        "## Authority",
        "This run's own review, in the session that runs the improve skill: change code, tests or documentation within scope, and commit "
        "only through the improve-commit command in " + str(improve_opening_path(child).with_name("parent-return.md"))
        + ". No push, deploy, install or credential access. The original request (untrusted) is the prompt in "
        + str(root / "state.md") + "; an explicit instruction there not to commit applies.",
        "",
        "## Environment",
        "Checkout: " + str(state["repo"]) + ". Commands, harnesses and suites: " + str(home / "environment.md")
        + " and the result's recorded test commands.",
```

## review-proof-focus — IMPLEMENT_STEP_REVIEW_FOCUS_HEAD

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 2525–2539 at `c70a33f46ed7`.

```python
  fragments or bypassing the catalog (rules 6-7); for a UI step, a plain or
  static interaction where the plan calls for a rich one (rule 5);
- a step skill listed in the packet and not used, or used against its stated
  purpose, with no reason in the result;
- a behaviour the code now has that no test-spec case covers and the result does
  not list for the test stage;
- the step's Proof failing or not testing its criteria (a skipped file, a later
  step's work), or a new unwaived lint finding on a changed line, after your
  last edit.
Do not write tests, start a later step, or edit the Proof. After your last edit,
rerun the step's Proof and ShipLoop's lint for the step's action (`shiploop
lint --action`), and record their exit codes. Commit your edits. A pass that
finds none of these is trivial.
"""
IMPLEMENT_STEP_REVIEW_FOCUS = IMPLEMENT_STEP_REVIEW_FOCUS_HEAD + "\n" + CODE_CRAFT
```

## release-state — DUTIES[release-check]

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1733–1752 at `c70a33f46ed7`.

```python
1. Name the release plan you check: the latest done release-plan and system-test-author records after the last
   accepted replan (OUTER test-planning handshake); action, result and plan locators in `evidence_refs`. Guess no
   missing plan: recover it, or report `repeat` (`replan` for missing product work).
2. Against the current target, record in `summary` (evidence in `evidence_refs`): candidate identity and that its
   evidence is current, the target and prerequisites, required approvals, rollback readiness, the execution owner's
   readiness, any target concurrency condition (Release operation guidance). Rerun prepare's read-only probe that the
   consumer can reach the entry (HOME/environment.md ## Access and accounts; the target's platform guide names one
   where it has one) and save its output beside the dry run's. A gap this run may not fix stays open there with who
   can grant it, for release-verify's step 1; create no grant.
3. Run the dry-run form of the planned deploy (for example the deploy tool's validate or check-only mode) once; save the output in
   RUN/notes/<action>-release-check.md and cite it in `evidence_refs`.
4. Run each `consumer_checks` post-release confirm command once against the current target; save its "not there yet"
   output in the same file. A confirm command that cannot tell present from absent is fixed now in
   HOME/environment.md ## Commands and rerun.
5. Isolated run only: run the packet's plan-return command, then decide every undecided path with review-return (a
   dry run; decisions are kept for the return at release). Compare review-return's expected return with the
   procedure in HOME/environment.md; if they differ, correct the procedure and rerun plan-return.
6. Keep stale or failed evidence in `evidence_refs` as is; replay or promote nothing for a fresh observation. A
   material change to code, tests, fixtures, configuration or target invalidates the observations it affects: rerun
   those through the planned route, reuse the rest only with identity and relevance stated.
```

## leftovers — commit_leftovers

Source: `skills/shiploop/scripts/shiploop_workspace.py`, lines 1293–1316 at `c70a33f46ed7`.

```python
@_locked_existing_root
def commit_leftovers(workspace_root: Path) -> shiploop_git.Committed:
    """Commit product files still uncommitted in the candidate before the return is planned.

    A file written after the last work item (a system test, a release note) is
    otherwise untracked at return, which forces the working-tree route and keeps
    every run commit off the user's branch.  Committing it here lets the reviewed
    plan fast-forward; a path the review then excludes still falls back to the
    working-tree route.  Run evidence, protected paths and caller exclusions are never committed.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    if _branch(worktree) != manifest["branch"]:
        _fail("workspace branch changed after preparation")
    tracked = [name for name in _git_bytes(worktree, "diff", "--name-only", "-z", "HEAD").decode(
        "utf-8", "surrogateescape").split("\0") if name]
    paths = sorted({*tracked, *(row["path"] for row in _untracked(worktree))})
    chosen = [path for path in paths if not never_committed(path, manifest["excluded"])]
    if not chosen:
        return shiploop_git.Committed("", [])
    try:
        return shiploop_git.commit_paths(worktree, chosen, "chore(shiploop): commit files written after the last "
                                         "work item, before the return")
```

## item-commit — commit_scope

Source: `skills/shiploop/scripts/shiploop_item_scope.py`, lines 220–234 at `c70a33f46ed7`.

```python
def commit_scope(changed: Sequence[str], allowed: Sequence[str],
                 never: Optional[Callable[[str], bool]] = None) -> Tuple[List[str], List[str]]:
    """Split an item's changed paths into (those ShipLoop commits, those it leaves).

    ShipLoop commits the paths the step plan declared (``allowed``), ShipLoop's own knowledge home and any other
    changed file in the ``docs`` path class: the document stage edits documentation, and a README or AGENTS.md it adds
    outside the declared paths was otherwise committed by the model by hand (3 of 16 recorded runs).  A path ``never``
    holds (``withheld``: a worktree run's protected and caller-excluded paths, which ``workspace.commit_leftovers``
    skips too) is never committed.  Every other undeclared file is left: plan-return commits it in a worktree run.
    """
    undeclared = set(outside(changed, allowed))
    left = [path for path in changed
            if (never is not None and never(path)) or (path in undeclared and classify(path) != "docs")]
    return [path for path in changed if path not in left], left
```

## classify — classify and behavioural_paths

Source: `skills/shiploop/scripts/shiploop_item_scope.py`, lines 53–69 at `c70a33f46ed7`.

```python
def classify(path: str, catalog: Optional[Mapping[str, Any]] = None) -> str:
    """The first matching class for a repository-relative path; ``code`` when none matches."""
    catalog = catalog or _catalog()
    for name in catalog["order"]:
        if any(_matches(path, pattern) for pattern in catalog["classes"][name]):
            return name
    return "code"


def behavioural_paths(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> List[str]:
    """The entries of ``paths`` that count as code or test (any class outside ``non_behavioural``)."""
    catalog = catalog or _catalog()
    allowed = set(catalog["non_behavioural"])
    return [path for path in paths if classify(path, catalog) not in allowed]


def behavioural(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> bool:
```

## platform-card — Apex reporter and copy delivery

Source: `skills/shiploop/references/platforms/salesforce.md`, lines 104–113 at `c70a33f46ed7`.

```text
ShipLoop judges a focused Apex test from the runner's own pass or fail mark on
the line that names it, so record the command with a reporter it can read:
`sf apex run test --target-org <alias> --class-names <TestClass> --synchronous
--result-format tap` prints an `ok` or `not ok` line per test, while the default
table and `--result-format human` put the outcome word after the test name,
which ShipLoop does not read, so a focused command that uses them is refused as
unread. An Apex test runs the code already in the org, so on the item's base it
cannot fail unless the command deploys the tree first: name each new org-bound
test in the test result's `red_na` with that reason, and let the candidate run
and the mutation check carry the proof.
```

## harness-grade — grade_shiploop

Source: `test/shiploop_e2e/run.py`, lines 1055–1078 at `c70a33f46ed7`.

```python
def grade_shiploop(out: Path) -> dict:
    """The state of the ShipLoop run this output folder's invocation created (SPEC: a verdict is earned by the run graded).

    The run is the one RUN_IDENTITY records. Until one is recorded it is the only run that was not already there when the
    invocation started, or, among several, the only one the host's ShipLoop commands named; that run is then recorded.
    Several candidates that nothing tells apart are reported as ambiguous and never pass: an unrelated finished run is
    never preferred (2026-10-16 E2E audit, docs/experiments/shiploop-e2e-audit-20261016/grading/).
    """
    runs = shiploop_runs(out)
    if not runs:
        return {"pass": False, "reason": "no ShipLoop state.md under the output directory"}
    identity = run_identity(out)
    before = identity.get("preexisting") if isinstance(identity.get("preexisting"), dict) else {}
    mine = [found for found in runs
            if found["run_dir"] not in before or state_digest(found["run_dir"]) != before[found["run_dir"]]]
    bound = identity.get("run_dir")
    # A recorded run whose state is gone is not a choice any more: the rules below pick again (still never a run that was
    # there before the invocation started) and record what they pick.
    chosen = next((found for found in mine if found["run_dir"] == bound), None) if bound else None
    basis = "recorded"
    if chosen is None and len(mine) == 1:
        chosen, basis = mine[0], "the only run that was not there before the invocation"
    elif chosen is None and len(mine) > 1:
        named = named_run_dirs(out) & {found["run_dir"] for found in mine}
```

## harness-verdict — outcome_class

Source: `test/shiploop_e2e/run.py`, lines 3257–3281 at `c70a33f46ed7`.

```python
def outcome_class(passed: bool, t: dict) -> tuple[str | None, str]:
    """(class, basis): how a run ended, a pure function of ``pass`` and the termination block (SPEC S-14).

    PASS: every verdict passed. BLOCKED: the engine accepted a blocked result, or is paused (it awaits resume the same way);
    the class says what the engine recorded and never that the block was warranted, which is a model judgement S-9 excludes
    as evidence. FAILED: the engine finished or halted without passing, or the host ended on its own with the engine
    unfinished. STOPPED: the harness ended the run (a requested stop, a signal, the deadline, a spent resume budget, or a host
    session that ended on the cap the harness gave it: ``CAP_STOPS``). None:
    unknown, and the basis says why (a regrade that observed no host, or an ending this function does not know). The engine's
    status wins over how the host ended: a stop requested after the engine blocked does not turn the block into a stop.
    A regrade that kept the original ending reads the engine as it is now (the ``*_at_regrade`` fields) and the ending as it
    was recorded.
    """
    if passed:
        return "PASS", "every verdict passed"
    regraded = "engine_status_at_regrade" in t

    def now(key: str):
        return t.get(f"{key}_at_regrade") if regraded else t.get(key)

    engine = now("engine_status") or "unknown"
    stage = now("engine_stage") or "unknown"
    reason = now("engine_status_reason")
    why = f" ({_head(reason)})" if reason else ""
    if engine == "paused":
```

## harness-keep — keep_decision

Source: `test/shiploop_e2e/run.py`, lines 2292–2317 at `c70a33f46ed7`.

```python
def keep_decision(*, keep_checks: tuple | list = (), **ended) -> tuple[str | None, str | None]:
    """How a --keep-platform request ends: (KEPT_FINISHED, None) for a finished delivery (keep_refusal), (KEPT_UNFINISHED, None)
    for a run that did not finish (ShipLoop not done, or the host timed out) whose platform is nevertheless working, or
    (None, why) when it is cleaned. The platform of an unfinished run is working when the case declares ``keep_checks`` (words of
    its own checks, for example `deployed`, `tests`, `rules`) and every one of them ran and passed; a person's stop, a signal, an
    invalid trial and a failed earlier cleanup (keep_blocker) forbid it. The run is then recorded NOT a pass. A run whose ShipLoop
    is done and whose host did not time out is judged as a finished delivery only: a failed check there is a failed delivery."""
    why = keep_refusal(**ended)
    if why is None:
        return KEPT_FINISHED, None
    unfinished = ended["process"].get("status") == "timeout" or ended["engine"].get("status") != "done"
    if not (keep_checks and unfinished) or keep_blocker(process=ended["process"], stop_seen=ended["stop_seen"], stop_file=ended["stop_file"],
                                                         invalid=ended["invalid"], earlier_cleanup=ended.get("earlier_cleanup")):
        return None, why
    unmet = [word for word in keep_checks
             if not any(word in str(check["command"]).split() and check["pass"] for check in ended["checks"])]
    if unmet:
        return None, f"{why}; not kept as an unfinished run either: the keep check(s) {', '.join(unmet)} did not pass"
    return KEPT_UNFINISHED, None


class PlatformGuard:
    """Owns the platform cleanup of one invocation. ``arm`` it once the model may start (or has started); ``finish`` runs the
    cleanup once, from the normal path after grading and again from main's `finally`, which is what covers a crash, a
    KeyboardInterrupt and a SystemExit. Before it acts on the platform it ends this thread's own host and waits for it to be
    gone (HOST_END_WAIT), so a cleanup never runs beside a model that can still deploy. ``keep`` instead leaves a finished
```

## harness-cleanup — PlatformGuard.finish

Source: `test/shiploop_e2e/run.py`, lines 2359–2380 at `c70a33f46ed7`.

```python
    def finish(self) -> dict | None:
        if self.spec is None or self.done:
            return self.record
        self.done = True
        # A Ctrl-C or an exception can arrive while this case's host still works: end it and wait until it is gone, so the
        # cleanup never overlaps a model that can still deploy.
        with contextlib.suppress(KeyboardInterrupt):  # a second Ctrl-C ends the wait, never the cleanup
            end_live_hosts(thread=threading.get_ident(), wait=HOST_END_WAIT)
        command = self.spec.get("cleanup")
        if not command:
            self.record = {"ran": False, "ok": True, "reason": "the case names no cleanup command"}
            return self.record
        try:
            done = run_platform_command(command, self.out, platform_env(dict(os.environ), self.out / "platform"))
            self.record = {"ran": True, "ok": done["ok"], "returncode": done["returncode"], "output": done["output"]}
        except BaseException as exc:  # noqa: BLE001 - the record of a cleanup that could not run is the point
            self.record = {"ran": True, "ok": False, "returncode": None,
                           "output": scrub(f"cleanup could not run: {type(exc).__name__}: {exc}")[-PLATFORM_TAIL:]}
        if not self.record["ok"]:
            print(cleanup_banner(self.out, self.spec, self.record), flush=True)
        write_cleanup_record(self.out, self.record)
        return self.record
```

## loop-start — start_command

Source: `skills/shiploop/scripts/shiploop_loops.py`, lines 529–533 at `c70a33f46ed7`.

```python
def start_command(bound: Mapping[str, str], receipt: Path, contract_file: Path) -> str:
    """The one command that starts a bound loop: the packet prints it, and the refusal for a loop that never ran
    repeats it."""
    return (shlex.join(["python3", bound["runtime_cli"], "start", "--receipt", str(receipt)])
            + " < " + shlex.quote(str(contract_file)))
```

## loop-result — _RESULT_HEAD and result instructions

Source: `skills/shiploop/scripts/shiploop_loops.py`, lines 561–576 at `c70a33f46ed7`.

```python
                    "ShipLoop refuses done without it.")
RESUME_LINE = ("The loop already started: do not start it again (a second start resets it). While the receipt's status "
               "is active, run its next_argv once and follow the packet it prints; when complete or stopped, submit this "
               "stage's result.")
# The runtime's report schema requires all five fields; its enums are printed here so the done report is written once.
REPORT_FIELDS = ("Done-report fields: classification trivial|non-trivial|unresolved, exit_assessment "
                 "satisfied|unsatisfied|unknown, continuation_assessment allowed|blocked|cancelled, plus evidence and "
                 "handoff (nonblank text).")
_RESULT_HEAD = ("Result: when the Receipt says status complete (stopped: report it), keep it in evidence_refs and run "
                "the Callback command above. If that refuses for the loop, ")
RESULT_LINE = (_RESULT_HEAD + "run the start command above again (an active receipt: its next_argv instead), then run "
               "the Callback again. " + REPORT_FIELDS)
# A packet read after the start prints no start command (a second start resets the loop), so its result line names the
# receipt's next_argv alone.
RESUME_RESULT_LINE = (_RESULT_HEAD + "run the receipt's next_argv once and follow the packet it prints, then run the "
                      "Callback again. " + REPORT_FIELDS)
```

## discovery-applicability — DUTIES[discovery] connected services

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 953–977 at `c70a33f46ed7`.

```python
9. Resolve internal terms and background beyond the checkout with Connected knowledge discovery: find the MCP readers
   (Slack or Teams, internal sites, design docs, private Git), search, and follow hits to the content. Record terms
   and conflicting claims with provenance, access and coverage gaps, and safe locators in RUN/notes/discovery.md.
   Keep private queries and content off public surfaces; a reader is no runtime dependency.
10. Establish the current-system account (Current-system baseline guide): read README first, reuse and revalidate an
    adequate account or recover one from docs, code, tests and authorized read-only observation. Write
    RUN/notes/current-system-baseline.md with as-of identity, coverage, conflicts, locators and durable home; cite it
    in `evidence_refs`. A repository without ShipLoop knowledge is not a new system. Keep the incoming change
    separate; consequential gaps leave dependent work unready.
11. For affected flows apply Service discovery guidance; record in RUN/notes/discovery.md:
    - observability: event owners and sinks to reuse;
    - service boundaries: consumer needs traced through business services to the real MCP, API and runtime
      capabilities, identities, schema and state;
    - cache, invalidation and async questions, inventing no infrastructure;
    - unproven access or caching: a safe policy-enforced read route, or a denial (privileged direct access is no
      fallback);
    - schema or projection delta: preserved state and its read-back check;
    - async flow: processor and recovery owner and the acceptance/completion boundary, else unknown (a status poller
      establishes neither); gate only that flow;
    - retained application state: the Runtime state placement section.
    Safe authorized reads may resolve a gap; an unavailable or partial observation is not absence. Turn unknown
    ownership into a scoped probe and a conditional change, gating only dependent work.
12. Establish the current target and effective identity; use it for dependent remote reads. Distinguish discovery
    operator, deployed runtime and end user. Record each unknown role or authority and its consumer under
    ## Access and accounts.
```

## ui-applicability — DUTIES[plan] UI qualification

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1168–1178 at `c70a33f46ed7`.

```python
   state, event and connection agreements with planned recovery checks (including a crash after acknowledgment but
   before processing); deployment fit; source and check locators. UI: component, interaction and skin premises, the
   design guidance locator with identity, version or digest (or the named fallback), each async cue with purpose and
   reduced-motion alternative or an explicit static choice. A human-facing UI takes the ambition the request states
   (a simple one when it asks for simple); one that states none defaults to an ambitious, highly interactive design:
   name the rich interactions planned (direct manipulation, inline editing, live preview, keyboard paths, animated
   transitions) and any scaled back, with the reason. A consequential UI choice gives the
   guide's ambition, the reuse, evolve or upgrade decision, effort and benefit, and the compatibility check.
   Allocate each UI decision to the item that owns it (UI planning ownership guide) and put it, with planned check
   locators, in that item's `context` and `evidence_refs`. Reuse accepted choices for unaffected scope. Start no
   nested review.
```

## module-applicability — DUTIES[plan] module qualification

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1199–1208 at `c70a33f46ed7`.

```python
12. Map accepted service choices to the affected schema and config, query and cache, worker and status, business and
    UI, logging, test and operator files, as needed (Service discovery guidance), ordering prerequisites and checks.
13. Each item's `context` states the loadable seam its tests import, so a test loads before the implementation exists,
    and, where the language has more than one module format (CommonJS or ESM, with or without package.json), the one
    its files use.
14. Before fixing item IDs, check the draft once for coherent increments. Split a deliverable with different
    prerequisites, a useful intermediate contract or artifact, or independent implementation and check; merge
    fragments sharing prerequisites and an implementation boundary with no checkable state of their own. A small
    change may be one item; no minimum, quota or scaffolding item. Preservation and negative requirements are checks
    on the affected item unless they need their own change. Add no item for step planning, validation, build, test,
```

## system-author — DUTIES[system-test-author] command runs

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1596–1615 at `c70a33f46ed7`.

```python
5. Run each system command once now and confirm its discovery and rerun work. A command that cannot pass here is
   changed to observe the same requirement another way, saying what and why in `summary`. Every case ends validated,
   validated another way or unachievable (item 7); a case written but not run has no end state.
6. `system_commands`: one row per runnable command, shaped like test_commands, suite `focused`, `regression` or
   `check`. `focused` and `regression` suit runners whose output ShipLoop can count and carry the case `ids`; a
   non-runner (shell pipeline, grep, curl probe) is `check`, judged by exit code, no ids or min_tests. A row whose
   cases need a host tool (browser, device, account, service) gets `"host_dependent": true`: ShipLoop then also runs
   the regression commands at system-test and refuses if any of that row's ids appears in their output, as the
   default suite must pass without the host tool. No system test applies: empty list with `system_commands_na` and
   the reason.
7. A case that cannot run here (a browser or account this host cannot reach) is unachievable. Leave its command out
   of `system_commands` (ShipLoop reruns every recorded command and refuses unless each passes). Record it as an
   open item in `assumptions`: `assumption` = case ID and the requirement left unverified; `check` = who does what
   and reports what; `owner`; `reason` it cannot run here; `consumer` = the due stage (handoff, or the stage whose
   external effect it gates). Continue with every runnable case. Report blocked only when nothing else can proceed,
   replan when the plan is wrong.
8. The integrated test plan goes in `summary` under the catalog and in HOME/environment.md ## Harnesses and suites
   (OUTER test-planning handshake): candidate and boundaries, selected cases and oracles, commands, lifecycle and
   sharing decisions, cost, prerequisites, execution owners; which checks run now at system-test and which need the
   authorized release first. Cite HOME/environment.md in `evidence_refs`; the decisions and constraints the plan
```

## system-execute — DUTIES[system-test]

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 1619–1637 at `c70a33f46ed7`.

```python
1. Name the plan you run: the latest done system-test-author record after the most recent accepted replan, and its
   integrated test plan in that summary and HOME/environment.md ## Harnesses and suites (OUTER test-planning
   handshake). Before running, revalidate its candidate, case selection, target and fixture assumptions. Its
   locators, and its reuse or the concrete mismatch, go in `evidence_refs`. A required planning gap ends as repeat,
   blocked or replan; never guess a command or drop a required case.
2. Before running check prerequisites, fixtures, execution location, target, identity, authorization, remote
   framework availability, and the deployed or test revision. Add no deploy to unblock a test (a recorded command's
   own deploy step runs as recorded); use production only with authority.
3. Run the due cases on the intended candidate and boundary (System-test placement guidance, Real-boundary test
   guidance). Substitute no planned case or local mock for a required system observation. A local pass replaces no
   blocked or unrun required remote check and establishes no combined full-suite pass; keep that check's owner and
   boundary. Check repeatability when fixtures changed. Never blindly replay an uncertain external effect.
   `evidence_refs`: each command, candidate and target, scope, cleanup outcome and unrun check.
4. A recorded system command that fails here is no open item: ShipLoop refuses done while it fails. Fix the
   candidate, report replan for missing product work, or blocked when nothing else can proceed.
5. After a material change to code, tests, fixtures, configuration or target, rerun the affected observations; reuse
   unaffected evidence only with its identity and relevance stated.
6. Run any open item system-test-author recorded that this stage can now run, reporting each in the summary (not
   recorded evidence: ShipLoop's rerun covers only recorded system commands). Leave the rest listed with their due
```

## craft-producer — _prompt_parts

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 2401–2424 at `c70a33f46ed7`.

```python
def _prompt_parts(stage: str, *, delegation: str, backchain_passes: str, planning_review: str,
                  execution_mode: str | None, one_step_item: str | None = None,
                  interactions: bool = True) -> list[tuple[str, str]]:
    """The producer instruction as ``(kind, text)`` parts in print order; ``prompt`` joins them.

    ``kind`` is ``duty``, ``audit`` (the inline route's short optional audit line), ``backchain`` (the route paragraph of a
    stage that may call Backchain), ``craft`` or ``rules``.
    """
    parts = [("duty", duty(stage, delegation=delegation, planning_review=planning_review,
                           backchain_passes=backchain_passes, execution_mode=execution_mode,
                           one_step_item=one_step_item, interactions=interactions))]
    # The shared blocks (interaction design, planning hand-off, work-item context, test facilities, test decisions,
    # OUTER test plans, selected-case reconciliation) are folded into the duties of the stages they applied to
    # (packet re-cut, 2026-10-11, R2/R3), so none prints here.  The constants stay as the one worded copy.
    if stage in INLINE_AUDIT_STAGES and delegation == INLINE:
        parts.append(("audit", INLINE_BACKCHAIN_AUDIT))
    elif stage in BACKCHAIN_FOLDED_STAGES:
        pass  # the Backchain item is folded into the duty; no loop budget block follows (Until Loop has no size limit)
    elif stage in BACKCHAIN_STAGES:
        parts.append(("backchain", _swapped(_backchain_guidance(stage, backchain_passes=backchain_passes), stage,
                                            planning_review)))
    if stage in IMPLEMENTATION_STAGES:  # implement only: where product code is written (owner, 2026-10-11)
        parts.append(("craft", CODE_CRAFT))
    parts.append(("rules", STAGE_RULES))
```

## craft-end — END_REVIEW_FOCUS

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 2490–2496 at `c70a33f46ed7`.

```python
END_REVIEW_FOCUS_HEAD = """\
End-of-work code review focus. Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input, then review the change against the rubric below. Fix violations within
scope. A pass that finds no material violation is trivial.
"""
END_REVIEW_FOCUS = END_REVIEW_FOCUS_HEAD + "\n" + CODE_CRAFT
```

## craft-step — IMPLEMENT_STEP_REVIEW_FOCUS

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 2531–2539 at `c70a33f46ed7`.

```python
- the step's Proof failing or not testing its criteria (a skipped file, a later
  step's work), or a new unwaived lint finding on a changed line, after your
  last edit.
Do not write tests, start a later step, or edit the Proof. After your last edit,
rerun the step's Proof and ShipLoop's lint for the step's action (`shiploop
lint --action`), and record their exit codes. Commit your edits. A pass that
finds none of these is trivial.
"""
IMPLEMENT_STEP_REVIEW_FOCUS = IMPLEMENT_STEP_REVIEW_FOCUS_HEAD + "\n" + CODE_CRAFT
```

## craft-chain — _planning_worker_instructions

Source: `skills/shiploop/scripts/shiploop_chain.py`, lines 1108–1124 at `c70a33f46ed7`.

```python
def _planning_worker_instructions(packet: dict[str, Any]) -> None:
    """Append worker guidance to the ``instructions`` list of ``packet`` in place and return nothing. It adds the
    implementation-stage reference locators (without the parallel-chain guide), the code-craft prompt, handoff
    and blocking rules, and planning-context rules when ``packet`` has a ``planning_context`` key. Entries
    already present are skipped; ``packet`` must already hold an ``instructions`` list.
    """
    reference_dir = Path(__file__).resolve().parents[1] / "references"
    instructions = [
        f"{label}: {reference_dir / relative}"
        for label, relative in _WORKER_GUIDANCE_ROUTES
    ]
    instructions.append(navigator_prompts.CODE_CRAFT.rstrip())
    instructions.extend((
        "Before scoped edits, select and apply only the relevant practice and platform guidance; consult the accepted planning/context, repository conventions, and applicable baseline.",
        "Return material discoveries, decision rationale, actual checks and their limits, and unresolved uncertainty. Put essential findings and the next action/owner in the manifest summary; use declared files for supporting detail and evidence. If there are no new findings, say so explicitly. Keep this handoff self-contained for a parent or successor without this conversation.",
        "If a required guidance locator is unavailable, mark the step BLOCKED and retain the uncertainty rather than guessing.",
        "These references do not change the task, definition of ready/done, scope, or authority; they do not authorize a nested ShipLoop or Improve cycle or parent callbacks.",
```

## craft-quality — rubric_writes

Source: `skills/shiploop/scripts/shiploop_quality.py`, lines 29–32 at `c70a33f46ed7`.

```python
def rubric_writes() -> dict[str, str]:
    """Run-relative path -> text of the Code craft rubric verify's review applies (written on entry to verify)."""
    return {RUBRIC_PATH: guidance.CODE_CRAFT}
```

## guidance-loader-site — module imports and source-reference responsibility

Source: `skills/shiploop/scripts/shiploop_reference.py`, lines 1–24 at `c70a33f46ed7`.

```python
"""The run reference file, `<run>/reference.md`: run-wide detail a packet names by section instead of reprinting.

Owner, 2026-10-10: a packet holds the key file references, what to do, when it is complete, and what to execute.
Detail a stage seldom needs lives here, in labelled sections. A packet names only the sections its stage uses
(`reference#<anchor>`) and says when to open each one. Grounding never moves here (SPEC S-6): a stage's goal,
operation, Done-when, Checked-by, result contract, recovery command and the rules it can hit stay in its packet.

The file is derived from state.md and the package: `navigator.save()` writes it with every transition (beside
context-index.md, in the same transaction), and `emit` writes it again when it is missing or was written by another
ShipLoop version, so a run that started before this file existed gets it on its next `next`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import shiploop_prompts as guidance

REFERENCE_FILE = "reference.md"
SCRIPTS = Path(__file__).resolve().parent
REFERENCES = SCRIPTS.parent / "references"
VERSION_LINE = "<!-- shiploop-reference: {version} -->"

# (anchor, heading). Packets cite `reference#<anchor>`; tests check every cited anchor exists.
```

## plan-skill-check — check_step_plan

Source: `skills/shiploop/scripts/shiploop_expectations.py`, lines 332–359 at `c70a33f46ed7`.

```python
def check_step_plan(root: Path, state: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    """Refuse a done step-plan result whose expectations, check suite or step skills are incomplete.

    ``root`` is the run directory and ``state`` the run state with this item current (its lint base is recorded at
    step-plan entry).  Refused: a missing or malformed ``expectations``; a check that is not one read-only shell
    command; an expectation naming an unknown step; an existing step path with no works or broken expectation, or a
    new one with no absent expectation; a works or broken path missing on the base, or an absent path present there;
    an open plan assumption whose consumer is this item and that no expectation cites in ``from`` (or a ``from``
    naming none of them); a non-empty ``test_commands`` without a check row or ``check_na`` (or both); a step
    without ``skills``; and a skill locator that does not exist.  Raises ExpectationError.
    """
    if not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    repo = Path(str(state["repo"]))
    work_item, _action = _cursor(state)
    _check_check_suite(result)
    steps = [step for step in result.get("steps") or () if isinstance(step, Mapping)]
    step_ids = {str(step.get("id")) for step in steps}
    for step in steps:
        _need("skills" in step, "step " + str(step.get("id")) + " must list skills (" + _SKILL_SHAPE + "): reread "
              "the host's skills and the repository's skill directory, and name one only for a concrete use")
        for skill in normalise_skills(step["skills"], str(step.get("id"))):
            _need("locator" not in skill or _locator_exists(repo, skill["locator"]),
                  "step " + str(step.get("id")) + " skill " + skill["name"] + ": locator " + skill.get("locator", "")
                  + " does not exist. Give the absolute path of its SKILL.md or card, or drop the locator.")
    _need("expectations" in result,
          "a done step-plan result must list expectations: the facts its steps build on, each with a check "
          "ShipLoop runs at validate-existing before anything changes; " + _SHAPE)
```

## craft-1 — CODE_CRAFT rule 1

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 629–632 at `c70a33f46ed7`.

```python
1. Match the house. The repository's error types, validation helpers, docstring
   style and logging come first; record any justified departure. Add no
   dependency, option or fallback without a present need. An argument that
   lets an existing unit serve this change instead of a copy is a present need.
```

## craft-2 — CODE_CRAFT rule 2

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 633–640 at `c70a33f46ed7`.

```python
2. Fail at the door. A function reachable from outside its module (exported
   API, CLI handler, request or event handler, callback) checks its arguments
   before any effect: required values present, type and shape, range or allowed
   set, and consistency between arguments. Reject with the house error type,
   naming the argument, the constraint and the received value (redacted when
   sensitive). Code called only by validated code may trust its caller; say so
   once where that is not obvious. Never swallow an error or substitute a
   success default; keep the original cause when rethrowing.
```

## craft-3 — CODE_CRAFT rule 3

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 641–645 at `c70a33f46ed7`.

```python
3. State the contract where it lives. A new file opens with one or two lines on
   its purpose. A public function's docstring gives purpose, argument
   constraints, return, errors raised and side effects. In a body, comment only
   what the code cannot say: why this approach, an invariant, a workaround and
   its trigger, a removed approach that must not return.
```

## craft-4 — CODE_CRAFT rule 4

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 646–648 at `c70a33f46ed7`.

```python
4. Spend tokens on information. Delete comments that restate a name, signature
   or the next line. No banners, change history or commented-out code. Prefer a
   precise name to a comment and one authoritative explanation to several.
```

## craft-5 — CODE_CRAFT rule 5

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 649–651 at `c70a33f46ed7`.

```python
5. Small, not thin. KISS and YAGNI limit features and speculative
   abstractions. They never remove an argument check, an error path, a
   contract docstring, or the rich UI interaction the plan calls for.
```

## craft-6 — CODE_CRAFT rule 6

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 652–657 at `c70a33f46ed7`.

```python
6. Make failure diagnosable. Check a response's contract, not only transport
   success. Before mutation or cleanup, keep the context that explains a
   failure: operation, relevant IDs, expected versus observed. Errors name the
   operation and that mismatch. Reuse the existing debug switch for short,
   redacted state summaries at major actions, with no diagnostic work while it
   is off. Keep secrets and duplicate stack traces out of user-facing messages.
```

## craft-7 — CODE_CRAFT rule 7

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 658–663 at `c70a33f46ed7`.

```python
7. Write text that can be translated. User-facing messages go through the
   repository's message catalog or i18n helper when one exists; otherwise keep
   each message one whole sentence with named placeholders, never assembled
   from fragments, so it can be externalized later. Format numbers, dates,
   currency and plurals through locale-aware APIs. Keep log text, error codes
   and machine identifiers stable and untranslated.
```

## craft-8 — CODE_CRAFT rule 8

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 664–669 at `c70a33f46ed7`.

```python
8. Put it where it belongs. New code lives in the namespace the step plan
   chose, with the narrowest visibility a present consumer needs. A new name
   must not collide with or shadow one in the shared space of any runtime it
   runs in (such as globals, an import path, a shell or a platform org) or in a
   library the code uses. No new generic bucket such as `utils`. Stored data
   follows the planned schema and storage policy.
```

## craft-9 — CODE_CRAFT rule 9

Source: `skills/shiploop/scripts/shiploop_prompts.py`, lines 670–677 at `c70a33f46ed7`.

```python
9. Compose before you build. Before writing a new unit, evaluate reusing an
   existing one unchanged, composing existing ones, or augmenting one (a new
   argument, an extension point, or a shared piece extracted from existing
   code) while its current callers keep working. Augment only when the units
   share one meaning, not merely similar code: a near-copy of existing logic
   is a defect, and so is a parameter that fuses two different rules. State
   the option chosen and why in one line.
"""
```

## test-step — test_each_step_packet_carries_its_own_proof_and_no_item_check

Source: `test/shiploop-delegation.test.py`, lines 333–341 at `c70a33f46ed7`.

```python
    def test_each_step_packet_carries_its_own_proof_and_no_item_check(self):
        """Chess run 2026-10-17: S1 was given a grep for files only S3 creates, failed, and the revise merged S1-S3.

        The step Proof replaces 603a709c's interim rule (a check due from the step that finishes its criteria): each step
        packet names the one command its step plan recorded for it, and the item's check rows stay with test and verify.
        """
        steps = [{"id": "S1", "task": "Add the parser.", "criteria": ["C1"], "check": "python3 -B probe_parser.py"},
                 {"id": "S2", "task": "Add the validator.", "criteria": ["C2"], "check": "python3 -B probe_validator.py"},
                 {"id": "S3", "task": "Add the report page.", "criteria": ["C3"], "check": "grep -q report report.html"}]
```

## test-surfaces — test_the_file_the_head_and_the_handoff_print_one_step_block

Source: `test/shiploop-delegation.test.py`, lines 557–565 at `c70a33f46ed7`.

```python
    def test_the_file_the_head_and_the_handoff_print_one_step_block(self):
        """T8: the same Step block (task, criteria by value, dependencies, Proof, later steps) on all three surfaces; the
        hand-off names the step's entry base as a diff command; no surface fences the step to paths."""
        state = self.at_step(1)
        base = nav.current_action(state)["base"]
        texts = self.surfaces(state)
        block = self.step_lines(texts["file"])
        self.assertEqual(block[0], "Step S1 (1 of 3), the only work for this packet: "
                                   "Add the parser. It reads one record per line.")
```

## test-tail — test_the_loop_invocation_closes_the_file_and_the_head_even_when_the_head_is_cut_short

Source: `test/shiploop-delegation.test.py`, lines 595–603 at `c70a33f46ed7`.

```python
    def test_the_loop_invocation_closes_the_file_and_the_head_even_when_the_head_is_cut_short(self):
        """T10: the last block of the packet file and of the printed head is the /until-loop invocation; with a head
        budget too small for any optional block the step block and the loop are still there, the loop last."""
        state = self.at_step(2)
        path = nav.packet_path(self.run, state)

        def last_block(text: str) -> str:
            blocks = [chunk for chunk in re.split(r"\n\s*\n", text.replace(nav.HEAD_END, "").strip()) if chunk.strip()]
            return blocks[-1]
```

## test-exits — test_each_exit_condition_and_recorded_command_appears_once

Source: `test/shiploop-step-packets.test.py`, lines 103–111 at `c70a33f46ed7`.

```python
    def test_each_exit_condition_and_recorded_command_appears_once(self) -> None:
        """Each thing once (owner, 2026-10-11): the /until-loop argument is the one home of the exit conditions and the
        test stage's command list, so no inner producer packet repeats either.

        A condition is counted as its text; a recorded command as its listing ("[<suite>] <command>"), because the
        bare command text can sit inside a rule (the count rule names "node --test" as a runner example).
        """
        for name, found in self.found.items():
            listing = "[focused] " + CASES[name]["checks"][0]
```

## test-craft — test_the_inline_handoff_keeps_the_per_step_wording_byte_for_byte

Source: `test/shiploop-delegation.test.py`, lines 1046–1054 at `c70a33f46ed7`.

```python
    def test_the_inline_handoff_keeps_the_per_step_wording_byte_for_byte(self):
        text = self.handoff(self.at_implement("inline"))
        self.assertIn(prompts.IMPLEMENT_STEP_REVIEW_FOCUS_HEAD.rstrip(), text)    # the focus, then the Code craft rubric
        self.assertIn(prompts.CODE_CRAFT.rstrip(), text)
        row = stage_spec.stage("implement")
        self.assertIn("Goal: " + row.goal[0].upper() + row.goal[1:], text)
        for condition in row.done_when:
            self.assertIn("- " + condition + "\n", text)
        self.assertNotIn("S1 to S2", text)
```

## test-person — test_a_partial_person_reply_closes_no_required_behavior_and_the_ask_again_it_names_is_accepted

Source: `test/shiploop-consumer-delivery.test.py`, lines 1294–1302 at `c70a33f46ed7`.

```python
    def test_a_partial_person_reply_closes_no_required_behavior_and_the_ask_again_it_names_is_accepted(self) -> None:
        """Packet review 2026-10-17 (F X-1): a reply that leaves cases unanswered lets a stage continue with them open,
        but in a marked run it closes no required behavior obligation.  The resumed packet says so; done with the
        obligation unrun is refused by the delivery gate, and the route the line names (ask again, for only the
        unanswered lines) is accepted."""
        state = self.to_release(self.accepted_contract(self.new_state()))
        state = self.advance(state, "release",
                             delivery_assessment=self.observation(state, "update-effect", "update-identity"))
        asked = navigator.current_action(state)["id"]
```

## test-id — test_an_id_that_starts_another_id_is_a_missing_test_not_a_title_to_fix

Source: `test/shiploop-test-loop.test.py`, lines 1357–1365 at `c70a33f46ed7`.

```python
    def test_an_id_that_starts_another_id_is_a_missing_test_not_a_title_to_fix(self):
        """GUARD (kills a raw substring match): `TC-1` listed, `TC-10` and `TC-13` printed.  The test is missing;
        "title each test so its ID stands alone" would send the model to retitle tests that are fine, so the
        select-and-print remedy stays."""
        self.start()
        self.drive_to("test", step_plan=self.id_item(ids=["TC-1", "TC-3"]))
        (self.repo / "retained.txt").write_text("retained\n")
        red = ("failed", 1, "\u2716 TC-1 a\n\u2716 TC-3 b\nRan 2 tests in 0.001s\nFAILED (failures=2)\n".encode(), b"")
        printed = (b"\xe2\x9c\x94 TC-10 a (1ms)\n\xe2\x9c\x94 TC-13 b (1ms)\n\xe2\x9c\x94 TC-2 c (1ms)\n"
```

## test-mutation — test_the_checkout_is_byte_identical_after_the_check

Source: `test/shiploop-test-loop.test.py`, lines 1573–1581 at `c70a33f46ed7`.

```python
    def test_the_checkout_is_byte_identical_after_the_check(self):
        self.calc_item(self.REAL_TEST)
        before = self.tree_bytes()
        lines = test_loop.mutation_check(self.run_dir, self.state(), self.item(), self.action())
        self.assertRegex(lines[0], r"^mutation: [1-9]\d* of \d+ mutants")
        self.assertEqual(self.tree_bytes(), before)
        with self.assertRaises(test_loop.TestLoopError):
            (self.repo / "test_calc.py").write_text(self.EMPTY_TEST)
            before = self.tree_bytes()
```

## test-return — test_files_left_uncommitted_are_committed_before_the_return_so_it_fast_forwards

Source: `test/shiploop-workspace.test.py`, lines 842–850 at `c70a33f46ed7`.

```python
    def test_files_left_uncommitted_are_committed_before_the_return_so_it_fast_forwards(self) -> None:
        record = self._prepare(name="leftover files")
        root = self.base / "leftover files"
        worktree = self._worktree(record)
        (worktree / "app.txt").write_text("work item\n", encoding="utf-8")
        self._commit_all(worktree, "work item")
        (worktree / "system").mkdir()
        (worktree / "system" / "check.js").write_text("late system test\n", encoding="utf-8")
        (worktree / "settings.env").write_text("Authorization: Bearer 0123456789abcdefghij\n", encoding="utf-8")
```

## test-loop — test_the_packet_prints_the_literal_start_command_and_it_starts_the_loop

Source: `test/shiploop-loops.test.py`, lines 339–347 at `c70a33f46ed7`.

```python
    def test_the_packet_prints_the_literal_start_command_and_it_starts_the_loop(self):
        """The printed command is the one that starts the loop, on this action's own contract and receipt."""
        for stage in ("step-plan", "test", "document", "verify"):
            with self.subTest(stage=stage):
                state = self.state_for(stage)
                self.write(state)
                block = self.block(state)
                action = "A-" + stage
                contract_file, receipt = self.root / loops.contract_path(action), loops.receipt_path(self.root, action)
```

## test-keep — test_keep_never_cleans_prints_the_command_and_exits_zero_when_the_checks_pass

Source: `test/shiploop-e2e-chess-salesforce.test.py`, lines 1948–1956 at `c70a33f46ed7`.

```python
    def test_keep_never_cleans_prints_the_command_and_exits_zero_when_the_checks_pass(self) -> None:
        proc = self.run_reference("--keep", "--platform-dir", str(self.tmp / "kept"))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(self.deploys(destructive=True), [])
        self.assertNotIn("cleanup:", proc.stdout.replace("cleanup --org", ""))
        state = self.state()
        self.assertTrue({"SLChessEngine", "SLChessController", "SLChessEngineTest"} <= set(state["apex_classes"]))
        self.assertIn("SLChess_Board", state["types"]["CustomTab"])
        self.assertIn("SLChess", state["types"]["CustomApplication"])
```

