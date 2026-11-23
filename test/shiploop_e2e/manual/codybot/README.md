# Codybot in ShipLoop

Prepare an independent build of the [Codybot build brief](Codybot-design-prompt.md)
with Python 3 and Git. Run this from the Skill Craft repository root.

```sh
python3 test/shiploop_e2e/manual/codybot/run.py
```

Each invocation creates a fresh Git repository with the complete brief
committed. The default and the `--prepare-only` alias finish after local
preparation, with zero Codex model usage. Repeat that command to prepare more
independent instances, including from separate terminals. Instances stay
under `~/e2e-runs/codybot` by default. Use `--runs-root /absolute/path` to put
them in another directory outside the Skill Craft checkout.

## Opt in to a build

Launching consumes Codex model usage, even when product work stays local. A
launch requires a working Codex login, the installed `skill-craft@whichguy`
plugin with its ShipLoop hooks trusted, and `shiploop-codex` on `PATH`.
This command prepares a new instance and launches one foreground Codex session.

```sh
python3 test/shiploop_e2e/manual/codybot/run.py --run
```

To launch an already prepared instance, use its saved `launch.txt` as a shell
script. It contains the printed command for that exact project. In Codex
desktop, open that `project/` directory in a fresh session, select the model
shown by `shiploop-codex --model-id` with medium effort, and submit the
`$skill-craft:shiploop …` prompt from the command. If ShipLoop reports
`SHIPLOOP-GRANT-NEEDED`, use its reported grant and exact retry command.

The [prompt audit](PROMPT-AUDIT.md) documents the offline review. Collect
product-build and live release evidence per instance.

## Check the case offline

Run the manual fixture checks with Python and Git. The launcher checks use a
fake `shiploop-codex`. The prompt checks read the transcript and the [Lightning, Apex and provider tool exchange](Codybot-design-prompt.md#model-tool-definitions-and-the-lightning-to-provider-exchange) directly from the Markdown.

```sh
python3 -B -m unittest discover -s test/shiploop_e2e/manual/codybot -p 'test_*.py' -v
```

## Results and recovery

Follow the link in ShipLoop's first packet to `workspace/run/progress.html`.
The instance holds `project/` for the source and returned work,
`workspace/worktree/` for implementation, and `workspace/run/` for packets
and evidence. The CLI appends session events to `events.jsonl` and writes
its final response to `last-message.md` when one is available. The launcher
returns the CLI's exit status. Keep ShipLoop's completion report and verified
return receipt with the instance.

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
