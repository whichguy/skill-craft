# Codybot in ShipLoop

Run the [original Codybot build brief](Codybot-design-prompt.md) as a standalone,
manual case. Each invocation creates a separate source repository with the
brief committed as its starting input. ShipLoop builds in its own worktree
and returns the work to that instance's project.

## Start a run

Use Python 3 and Git with a working Codex login, the installed
`skill-craft@whichguy` plugin, its ShipLoop hooks trusted, and `shiploop-codex`
on `PATH`. From the Skill Craft repository root, run these commands in
separate terminals to start two independent runs, or run them sequentially
for a repeat.

```sh
python3 test/shiploop_e2e/manual/codybot/run.py
python3 test/shiploop_e2e/manual/codybot/run.py
```

Each launch runs in the foreground. The launcher prints the instance path,
project path, events log and exact CLI command, and saves that command in
`launch.txt`. Codex appends its session events to `events.jsonl`.
Instances stay under `~/e2e-runs/codybot`. Pass `--runs-root /absolute/path`
to keep them under a different directory outside the Skill Craft checkout.

Preparing an instance requires only Python and Git.

```sh
python3 test/shiploop_e2e/manual/codybot/run.py --prepare-only
```

Run the printed command or `sh /path/to/instance/launch.txt` to launch that
exact instance in a terminal. In Codex desktop, open the printed `project/`
directory in a fresh session, select the
model shown by `shiploop-codex --model-id` with medium effort, and submit the
same `$skill-craft:shiploop …` prompt shown in the command. If ShipLoop reports
`SHIPLOOP-GRANT-NEEDED`, use its reported grant and exact retry command.

## Results and recovery

Follow the link in ShipLoop's first packet to `workspace/run/progress.html`.
The instance holds `project/` for the source and returned work,
`workspace/worktree/` for implementation, and `workspace/run/` for packets
and evidence. When the CLI returns a final response, find it in
`last-message.md`. Keep ShipLoop's completion report and verified return
receipt with the instance.

If launch failed before it created `workspace/`, fix the reported cause
and retry the saved command for that instance. If a run started, resume its
exact Codex session using the `thread_id` from the relevant `thread.started`
event and the recorded model and effort. In that session, recover the current
packet with the installed ShipLoop CLI selected by the skill.

```sh
instance=/absolute/path/to/instance
sed -n '/"thread.started"/p' "$instance/events.jsonl"
python3 "$CLI" next --run-dir "$instance/workspace/run"
```

If a failed start left an incomplete workspace without
`workspace/workspace.md`, keep it for diagnosis. Calling `run.py` again starts
another trial.

## Qualify a release

The case starts with local product work, with Codex providing the reasoning
session. Live product verification needs explicitly assigned and authorized
Salesforce test orgs and Codybot runtime service accounts. To assign a live
target, open the prepared project in Codex and add the authorized test org
alias and expected org ID, permitted actions, and credential names to that
instance's request. Keep credential values in the configured connections.
For simultaneous live runs, use separate orgs and compare their resolved
Salesforce org IDs before deploying. Two aliases can point to the same org.

Record the model, effort, package version and target org IDs where applicable
in `result.md` under each instance. Use the brief's
[22 required release scenarios](Codybot-design-prompt.md#required-release-scenarios).
For each scenario, record the result and link to evidence or name the missing
prerequisite. Distinguish local checks from observations on an installed
managed package. Report the Poppy Company design and test plan for v1 and run
its interoperability scenario when the follow-on is implemented.
