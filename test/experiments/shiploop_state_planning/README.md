# State-aware initial-planning fixtures

These are three frozen, synthetic repository snapshots for a later fresh-agent
planning pilot. They test plan interpretation only. They contain no production
data, credentials, remote targets, or completed pilot evidence.

| Case | Planning request | Fixture input |
| --- | --- | --- |
| `memory-utility` | Local duration total | One small in-memory CLI |
| `crm-board` | Board-card metadata | A synthetic internal board and access model |
| `import-projection` | Shared import-edit summary | A local import/projection model and rollout notes |

Each case has three distinct inputs:

- `request.md` is the only user request given to the planner.
- `repo/` is the repository snapshot the planner may inspect.
- `frozen-rubric.md` is for the coordinator and independent reviewer only. Do
  not give it to the planner or put its contents into a planning packet.

The files intentionally describe planning inputs, not a result. Do not add an
agent response, a simulated callback, or a pass/fail report here; retain any
later trial material outside this source tree.

## Fresh planning session

Two evidence levels are useful. A **focused interpretation trial** may supply the
catalog's actual `prompt("plan")` text and its reference locators directly to a
fresh reader of a disposable fixture copy. Label it as a prompt-only trial: it
does not execute discovery stages, driver transitions, or Improve. The **runtime
pilot** below follows actual packets through the initial plan's Improve handoff;
stop intentionally at the next `prepare` action and report the bounded endpoint,
not whole-project completion. Never turn a focused trial into a runtime claim.

Use a disposable copy so the source snapshot and its frozen rubric stay intact.
From the source checkout root, select one case and prepare a local Git baseline:

```sh
CASE="$PWD/test/experiments/shiploop_state_planning/memory-utility"
TRIAL_ROOT="$(mktemp -d /tmp/shiploop-state-planning.XXXXXX)"
cp -R "$CASE/repo" "$TRIAL_ROOT/repo"
cp "$CASE/request.md" "$TRIAL_ROOT/request.md"
git -C "$TRIAL_ROOT/repo" init -q
git -C "$TRIAL_ROOT/repo" config user.name "Synthetic Fixture"
git -C "$TRIAL_ROOT/repo" config user.email "fixture@example.invalid"
git -C "$TRIAL_ROOT/repo" add .
git -C "$TRIAL_ROOT/repo" commit -qm "synthetic fixture baseline"
```

Bind `SKILL_ROOT` to the absolute path of the actually selected ShipLoop skill,
then let its CLI emit the current guidance. Do not replace the packet with a
hand-written planning prompt.

```sh
SKILL_ROOT="/absolute/path/to/the/selected/shiploop-skill"
CLI="$SKILL_ROOT/scripts/shiploop"
python3 "$CLI" workspace start \
  --repo "$TRIAL_ROOT/repo" \
  --workspace-root "$TRIAL_ROOT/run" \
  --prompt "$(cat "$TRIAL_ROOT/request.md")"
```

Give a fresh planning agent the original request, the emitted current packet,
and only the disposable worktree/run locations identified by that packet. It
must follow actual packets and callbacks until ShipLoop emits its planning
action; do not seed or skip predecessor results to manufacture that action. At
the planning action, the agent proposes the plan and evidence needed, without
implementing, promoting, granting access, or treating a plan as execution. If a
real prerequisite prevents the plan action, record the actual stop condition;
do not create a replacement packet.

Use a separate fresh reviewer after the planner finishes. Give that reviewer an
immutable copy of the same request and repository inputs, the emitted planning
packet, the planner's plan artifact, and the case's `frozen-rubric.md`. The
reviewer should score each obligation independently as PASS, FAIL, or UNKNOWN,
cite the inspected fixture evidence, and distinguish a planning proposal from
executed or promoted work. The reviewer does not implement or submit callbacks.

No model call, agent response, or report is bundled with these fixtures.

Interpret frozen scores alongside the [documented calibration limits](../../../docs/shiploop-state-data-planning-2026-09-18.md#experiment-findings).
Keep the raw score and its caveat separate; do not alter a frozen rubric to fit a run.
