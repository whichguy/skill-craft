# Native Ask-Agent chain pilot

`native_pilot.py` is a retained, opt-in qualification apparatus for the
per-step ShipLoop chain bridge. It creates a disposable real-Git fixture,
fixture-emulates caller-prepared workspaces with ordinary Git, and drives the
public `shiploop chain` lifecycle. It never launches a model, an agent CLI, a timer,
or a polling service. A native host must launch fresh workers and retain its
own launch/completion trace.

The pilot uses the frozen Ask-Agent 0.4 fixture and Plan Dispatcher v2 fixture.
It is not evidence that Ask-Agent 0.4 is generally qualified until a real
native run has retained both the host trace and the final evidence described
below.

The fixture workspace setup models the caller-worktree contract but does not
prove that the native host followed Ask-Agent's prompt-driven worktree-creation
instructions. A passing native run qualifies bridge adoption of the exact
fixture-prepared workspace, real native worker execution, per-step integration,
and cleanup under this fixture.

## Lifecycle

```mermaid
flowchart LR
  P[Fixture Git emulates caller W preparation] --> S[Bridge adopts W]
  S --> H[Worker commits and writes handoff]
  H --> I[Parent imports to archive]
  I --> G[Prepare candidate I]
  G --> D[Done fast-forwards target]
  D --> C[Accept then remove W]
```

The caller-side fixture preparation creates the exact sibling workspace `W`
with ordinary Git and records it under `workspaces/`. It emulates the Ask-Agent
caller-worktree contract; it is not evidence of prompt-driven Ask-Agent
workspace creation. The bridge only adopts that exact workspace. After native
completion, the parent copies the worker-local handoff into its durable archive, creates the Dispatcher control
receipt, removes the worker-local handoff files, merges the current target into
the stopped worker workspace to form candidate `I`, independently verifies
that candidate, fast-forwards the invoking feature branch, settles the
Dispatcher attempt, then removes `W`.

The worker result is only its commit and declared handoff files. The immutable
Dispatcher receipt, parent report artifact, and report envelope are
parent-controlled control records; workers do not write them. The target
advances after every accepted step. `finish` audits that already-integrated
target; it does not perform a final worker-to-target merge.

## Prepare

Use a fresh absolute directory outside the source checkout.

```sh
SOURCE_ROOT=/Users/dadleet/src/.work-trees/skill-craft/integrate-chain-20260918
PILOT_DIR=/private/tmp/shiploop-native-chain-pilot-$(uuidgen | tr '[:upper:]' '[:lower:]')
PILOT="$SOURCE_ROOT/test/experiments/shiploop_chain/native_pilot.py"
DISPATCHER_SKILL="$SOURCE_ROOT/test/fixtures/plan-dispatcher-v2/SKILL.md"
ASK_AGENT_SKILL="$SOURCE_ROOT/test/fixtures/ask-agent-v04/SKILL.md"

python3 -B "$PILOT" prepare \
  --pilot-dir "$PILOT_DIR" \
  --source-root "$SOURCE_ROOT" \
  --dispatcher-skill "$DISPATCHER_SKILL" \
  --ask-agent-skill "$ASK_AGENT_SKILL" \
  --capacity 2
```

The generated `context.json` freezes the selected cards, oracle, graph,
fixture paths, navigator run, and action. The fixture has four code-producing
steps:

| Step | Dependencies | Worker-owned file | Required behavior |
| --- | --- | --- | --- |
| A | — | `toy/add.py` | `add(2, 3) == 5` and `add(-4, 1) == -3` |
| B | — | `toy/format.py` | normalize trims, lowercases, and collapses spaces |
| C | A | `toy/aggregate.py` | `aggregate([2, 3, -1]) == 4`, using `add` |
| J | B, C | `toy/composed.py` | `composed_output([2, 3]) == "result 5"` |

The external oracle is generated outside all worker worktrees and its digest is
stored in `context.json`. It checks actual code behavior, the exact commit,
scope, cwd, Git root, dependencies, candidate state, and the final integrated
feature branch.

## Start and launch workers

Claim A and B together, then prepare and launch both through the native host.
The driver records a fixture-emulated caller workspace before `start`; this
ordinary Git fixture action models the Ask-Agent caller-worktree path and is
explicitly marked as fixture emulation. It does not establish that the native
host created the workspace by following Ask-Agent instructions. ShipLoop
receives that workspace in `start` and must adopt it rather than allocate
another worktree.

```sh
python3 -B "$PILOT" claim --pilot-dir "$PILOT_DIR" --steps A B

python3 -B "$PILOT" start --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>'
python3 -B "$PILOT" start --pilot-dir "$PILOT_DIR" --step B --attempt '<B_ATTEMPT>'
```

A response with `"action": "launch"` includes
`inline_native_assignment`. Give that exact text directly to a fresh native
worker. A retained JSON packet is audit material only; it is never a worker
prompt transport. Do not create a prompt file.

After the host actually returns a nonempty handle, save it and record it:

```sh
printf '%s\n' '{"handle":{"native_handle":"ACTUAL_HOST_HANDLE"}}' > "$PILOT_DIR/A-handle.json"

python3 -B "$PILOT" launched \
  --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' \
  --handle-file "$PILOT_DIR/A-handle.json"
```

Repeat for B, C, and J. A handle record proves only that the caller recorded
what the host returned. It does not prove native completion.

## Worker handoff contract

The inline assignment directs each worker to commit only its owned file, run
the external oracle, and leave its workspace intact. It must then create exactly:

```text
$WORKSPACE/.shiploop-handoff/<ATTEMPT>/handoff.json
```

The raw manifest has exactly this schema:

```json
{
  "schema": "shiploop-chain-handoff/v1",
  "run_id": "the packet run_id",
  "step": "A",
  "attempt": "the packet attempt",
  "base_commit": "the packet base commit",
  "status": "SUCCEEDED",
  "commit": "the clean worker HEAD",
  "summary": "what changed and checks run",
  "files": [
    {"path": "result.json", "sha256": "sha256 of that file"}
  ]
}
```

`result.json` remains inside that same handoff directory and records the
observed workspace, cwd, Git root, base, commit, checks, and summary. The
worker must not run a Dispatcher report command, write external
artifacts/envelopes, merge into the invoking checkout, settle an attempt,
select successors, remove a worktree, or alter the target.

## Import, prepare, accept, and clean up

Only after the native host has collected and confirmed the worker stopped:

```sh
python3 -B "$PILOT" import-handoff \
  --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' \
  --handoff-manifest '<A_WORKSPACE>/.shiploop-handoff/<A_ATTEMPT>/handoff.json' \
  --confirmed-stopped

python3 -B "$PILOT" prepare-integration \
  --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' --confirmed-stopped

python3 -B "$PILOT" done \
  --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' --confirmed-stopped
```

`import-handoff` verifies the raw manifest and code result while the worker
workspace exists, archives the declared bytes outside that workspace, and
records two distinct digests:

- the immutable worker-handoff receipt, which proves the archive transaction;
- the immutable Dispatcher parent-report receipt, which binds the later
  `done` verification.

`prepare-integration` merges the current target into stopped `W` and returns
one proof with `source_commit`, `expected_target`, `candidate_commit`, and
`workspace`. The pilot runs the independent oracle against that exact
candidate. `done` binds its verification to the Dispatcher parent-report
receipt and the exact proof, fast-forwards the invoking target, accepts the
attempt, and requires a completed cleanup receipt. It then proves `W` is
gone from disk and Git registration while the external archives remain readable.

After A is accepted, claim/start/launch C before B is accepted. Complete B and
C with the same three parent operations, one parent command at a time. Start J
only after B and C are accepted. J writes `toy/composed.py`; it does not
manually merge branches or supplier commits because its adopted base already
contains the accepted code.

The pilot records that A/B handles were registered before either Dispatcher
completion and that C started after A and before B's Dispatcher completion.
Those are lifecycle facts, not proof that B's native process was still running;
the native host trace is required to establish actual concurrent execution.

## Final audit and replay

```sh
python3 -B "$PILOT" finish --pilot-dir "$PILOT_DIR"
python3 -B "$PILOT" show --pilot-dir "$PILOT_DIR"
```

`finish` reruns code, target, primary-worktree, cleanup, and archive checks.
A repeat invocation validates the original immutable finish proof, reruns those
independent checks, replays the public `finish` call with the same proof, and
creates a missing local result receipt only if a prior process stopped after the
public call. It does not replace timestamped proof or duplicate the final
event.

A successful run retains `context.json`, packets, workspace records, native
handle records, import/archive receipts, candidate verification, final audit,
command records, and append-only `events.jsonl`. The optional
`run_native.py` wrapper retains the raw Grok host trace and performs a second
`finish` audit from a fresh process. Treat that trace, the final code behavior,
the integrated target, and worktree cleanup as separate evidence; a green
deterministic lifecycle test or a worker's prose alone does not qualify this
fixture's bridge adoption and native execution result. Neither proves
prompt-driven Ask-Agent workspace creation.

The wrapper also writes `host-events.jsonl`, which records local receipt time
and monotonic order for each raw host line, and
`native-trace-evaluation.json`. The latter is a fail-closed observer: every
A/B/C/J record must have one background `spawn_subagent` receipt with the exact
retained Grok UUID and fixture-prepared workspace, followed by a completed,
zero-exit `get_command_or_subagent_output` result for that same UUID before
`import-handoff`. It rejects malformed or truncated host JSON, prose-only or
forged handles, a cancelled host terminal event, direct parent workspace code
writes, and parent terminal commands other than exact pilot driver commands.
Each retained source must be that step's exact `<STEP>-handle.json` file. A
successful collection cannot hide a contradictory terminal failure for the same
worker, and JSON booleans are not integer exit codes. Legitimate pending
observations and repeated equivalent successful collection remain supported.
Every worker start also needs a preceding successful claim receipt. A successful
`finish` must follow all four completed integrations; a missing, failed or early
finish cannot qualify the run. Identical successful finish replay remains valid.

The observer requires A/B telemetry with compatible sub-second ISO timestamps
or monotonic start/end values and proves strict interval overlap. Missing or
coarse timing fails the native qualification rather than inferring overlap from
dispatch order. It observes typed host events and parent behavior; the external
oracle and Git receipts remain the proof of the resulting code and integrated
target.

## One-command native-host run

The opt-in wrapper prepares a fresh pilot, sends the inline workflow to a Grok
parent, retains the raw host trace, and invokes the pilot's independent
`finish` audit from a fresh process. Its output directory must not already
exist.

```sh
RUN_DIR=/private/tmp/shiploop-native-chain-run-$(uuidgen | tr '[:upper:]' '[:lower:]')
python3 -B "$SOURCE_ROOT/test/experiments/shiploop_chain/run_native.py" \
  --output "$RUN_DIR"
```

Optional `--grok`, `--ask-agent-skill`, `--dispatcher-skill`, and
`--timeout` arguments select the host, frozen cards, and deadline. The
wrapper retains `$RUN_DIR/host.ndjson`, `host.stderr`, `prepare.json`, and
`result.json`, plus `host-events.jsonl` and `native-trace-evaluation.json`; it
passes the worker assignment inline to the native host and
does not turn a saved packet or prompt file into worker transport.
`result.json` records `coverage.workspace_creation: "fixture_emulation"` and
marks prompt-driven Ask-Agent workspace creation as not qualified.

Inspect the raw host trace before qualifying a run: it must show fresh worker
launches, actual completion collection, the recorded handles, A/B dispatch
before either collection, C dispatch after A acceptance and before B
Dispatcher completion, J only after B/C acceptance, and no fabricated
handoffs. The pilot's Git and oracle evidence separately proves the code,
target updates, archive retention, and cleanup.

For a retained completed run, the observer can be rerun without launching a
host:

```sh
python3 -B "$SOURCE_ROOT/test/experiments/shiploop_chain/trace.py" \
  --host-trace "$RUN_DIR/host.ndjson" \
  --pilot-dir "$RUN_DIR/pilot"
```
