# Ask Agent managed-workspace live experiment

This is test-only apparatus for a native Ask Agent parent. It does not belong to
the Ask Agent runtime and never launches a model process. The parent must use
its host's native background workers. The fixture makes claims about external
CLI parent launches only when a public host-event export is supplied.

## Prepare

Run from the `skill-craft` repository with a new disposable directory outside
the repository. This copies and freezes the selected Ask Agent package, creates
`primary/` plus a dirty linked `caller/` worktree ahead of main, and records the
parent prompt as JSON outside the caller.

```sh
python3 test/experiments/ask_agent_managed_workspaces/managed_workspaces.py prepare \
  --run /tmp/ask-agent-managed-grok --host grok
```

Use `--skill-root /absolute/path/to/ask-agent` to freeze a different package.
Preparation refuses to run until that package contains
`scripts/ask_agent_workspace.py`; it freezes a complete package-tree digest and
the helper path in `operator/manifest.json`.
The fixture carries staged and unstaged `dual.txt`, a staged addition, unstaged
deletion, untracked `notes.txt`, and `pricing.json`. The only permitted caller
content change is adding `discount_rate: 0.10` to `pricing.json`.

For a strict overlap control, add `--worker-delay-seconds 45` (0–120, default
0). Each real worker sleeps once in its assigned worktree before its task, while
the parent performs its calculation with a native shell tool. This makes the
ordering observable when normal workers finish faster than the parent's public
response. The delay is test instrumentation and is never part of the skill.

Read `operator/parent-prompt.json` and supply its `prompt` string as the fresh
external parent's initial input. It is operator transport only; the parent
must put every worker assignment directly in native launch arguments.

`grok` means the locally installed Grok Build CLI. The qualification targets are
Grok Build, Claude Code, Codex, Cursor, and OpenCode. OpenCode uses its
persistent TUI with its documented background-subagent feature flag. A one-shot
OpenCode process exit is not evidence that an asynchronous Task returned to the
same parent context.

The reusable [cross-harness conformance cases](CONFORMANCE.md) define common
outcomes, host-specific controls, negative cases, and focused/smoke/full-suite
execution. Synthetic event tests cover all five host labels; they do not replace
live native-route qualification.

## Parent launch routes

Use the current local CLI help as authority. For an external disposable parent,
the established JSON/streaming forms are:

```sh
grok --cwd "$CALLER" --always-approve --verbatim --output-format streaming-json --single="$PROMPT" </dev/null
(cd "$CALLER" && claude --dangerously-skip-permissions --print --output-format stream-json --verbose -- "$PROMPT" </dev/null)
codex exec -C "$CALLER" --dangerously-bypass-approvals-and-sandbox --json -- "$PROMPT" </dev/null
cursor-agent --print --output-format stream-json --trust --workspace "$CALLER" -- "$PROMPT" </dev/null
```

Do not add `--no-subagents`: that would invalidate a native-delegation trial.
Close stdin, retain stdout/stderr and process exit as separate operator
evidence, and do not use resume/continue/fork. Cursor readiness is established
separately with `cursor-agent status`; retain that receipt with the trial.
These commands are explicit test harness launches and are not permitted inside
the runtime Ask Agent skill.
Resolve and record the executable path and version immediately before launch.
Pin a versioned executable when a CLI can update its launcher during a run.
For OpenCode, retain its persistent-TUI transcript and the enabled experimental
background-subagent flag as public operator evidence; do not substitute a
one-shot process wrapper or a custom poller.

Before `verify`, the parent/operator must create:

- `operator/public-native-events.json`: a public, sanitized object using
  `ask-agent-managed-workspaces.events.v2`. Its top-level `parent` has the real
  host, parent session ID, and raw-log locator. Every worker event binds
  `worker_id`, `attempt_id`, `role`, `delivery_mode`, and `helper_receipt`.
  Record `native_launch`, `operation`, `native_return`, `parent_acceptance`, and
  `cleanup` in their observed order. A launch/return has a `native` object with
  host, tool, session ID, task ID, locator, terminal state, and
  `cwd_binding: {"mode": "...", "observed": true|false}`. An `operation`
  records actual `cwd`, Git root, and locator. A helper target by itself is not
  operation evidence. `native_return.task_result.status` is separately one of
  `success`, `failed`, `cancelled`, `blocked`, or `unknown`; success requires a
  completed native task and `return_kind` `automatic_notification` or
  `native_join` in the original parent session. Record `after_exit_resume`
  distinctly; it cannot establish an automatic asynchronous return. Grok still
  requires observed native cwd binding at launch.
  A `cancelled` task result requires a `cancelled` native terminal state; a
  parent timeout or a signal request alone is not confirmed cancellation.
  Optionally add a `parent_final` event after the observed worker activity,
  containing `parent: {session_id, locator}`, `status: "completed"`, and a
  nonempty `summary` from the observed reply. Do not create it from process exit.
- `operator/helper-outcomes.json`: schema
  `ask-agent-managed-workspaces.helper-outcomes.v2`. A closed successful worker
  records the canonical identity above plus `inspection`, `delivery`, immutable
  `delivery_evidence`, `close`, and the exact helper `artifacts` rows. The
  verifier loads those records, validates the helper receipt/baseline binding,
  and rehashes each archived report. A failed attempt is `state: "retained"`;
  it has no close outcome and its worktree must still be Git-registered.
- `operator/acceptance.json`: schema
  `ask-agent-managed-workspaces.acceptance.v2`. Its `accepted` entries bind the
  successful worker identities to native launch/return references and the
  per-worker `ask-agent.acceptance.v1` file. Its `integration` evidence declares
  the code delivery mode and the patch or commit locator.

The worker reports must state actual root/cwd, helper receipt, sentinel findings
and contribution. Parent acceptance archives results first, then delegates
eligible close/removal to the frozen package helper; it must preserve every
caller dirty layer except the permitted pricing integration. This dirty fixture
qualifies `patch` delivery for code and `report-only` delivery for the audit
worker. The helper's clean-baseline commit-delivery tests cover `commits`; this
fixture does not silently turn a dirty return into a commit handoff.

## Verify

```sh
python3 test/experiments/ask_agent_managed_workspaces/managed_workspaces.py verify \
  --run /tmp/ask-agent-managed-grok
```

It writes `operator/verification-summary.json` once. `COMPLETE` requires actual
caller sentinel preservation including raw index bytes, non-pricing index and
dirty layers, unchanged caller branch/HEAD and paths, exact unstaged pricing
integration, frozen package/helper integrity, retained reports, helper outcome
receipts, acceptance references, and the normalized two-worker native trace.
The parent work event must follow both initial confirmed launches and precede
either return. A retry must have a new worker ID, attempt ID, and worktree after
the earlier failed return; its failed attempt remains retained. The verifier
reads only the current schemas: a manifest other than
`ask-agent-managed-workspaces.v2`, or one missing a key `prepare` writes, is a
`CONTRACT_ERROR`, and an event trace other than `events.v2` is `UNOBSERVED`,
never `COMPLETE`. Model booleans, file counts, or process exit cannot
independently pass the trial.

The same output exposes `checks.lifecycle_layers`: `native_launch`,
`parent_continuation`, `native_return`, `operation_cwd_root_binding`,
`caller_preservation`, `delivery_acceptance`, and `reports_cleanup`. Each layer
is `PASS`, `FAIL`, or `UNOBSERVED` with its own errors. These diagnose partial
results without relaxing the aggregate verdict: a valid native callback can
pass while actual operation-directory binding fails.

`checks.parent_final_response` independently reports `PASS`, `FAIL`, or
`UNOBSERVED`. It is not a prerequisite for the Task-lifecycle `COMPLETE` verdict:
the parent may stall after both workers returned and were accepted. Report both
outcomes; a complete lifecycle alone never claims a completed parent reply.
Conversely, an observed reply can pass this diagnostic while the task lifecycle
fails or remains unobserved: the reply may truthfully report a blocker. It proves
only that the parent produced its final response, not that workers succeeded.

The v2 normalizer/operator is a trust boundary. The verifier does not parse raw
native launch arguments, authenticate locators, or distinguish a forged native
tool label from a real native call. Before normalizing, retain and inspect raw
public launch inputs/results and child `check-context` tool output. Freshness,
background arguments, native-versus-shell dispatch, and per-call cwd require
that live evidence; worker prose and normalized model booleans cannot supply it.
Keep missing evidence missing. This limitation applies even when the hermetic
five-host event matrix passes.

To preserve an earlier verdict while grading corrected public normalization, use
a new file directly under that run's `operator/` directory:

```sh
python3 test/experiments/ask_agent_managed_workspaces/managed_workspaces.py verify \
  --run /tmp/ask-agent-managed-grok \
  --events /tmp/ask-agent-managed-grok/operator/public-native-events-resume.json \
  --output /tmp/ask-agent-managed-grok/operator/verification-regrade-1.json
```

Outputs are create-only. A resumed parent session is a later collection attempt:
record it as `after_exit_resume` with its own session and raw-log locator. It is
not evidence of uninterrupted automatic callback.
