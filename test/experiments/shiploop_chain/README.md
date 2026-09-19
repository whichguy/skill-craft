# Native-agent chain pilot

`native_pilot.py` is a manual qualification apparatus for the optional ShipLoop
parallel-chain bridge. It has only three graph nodes: independent `A` and `B`,
then integration node `J`. It creates a disposable real Git repository with a
linked `native-pilot-feature` worktree, allocates worker worktrees as siblings
under an external `.work-trees/project` container, and retains every packet,
command result, verification record, and bridge result outside the checkouts.

It never launches a model, an agent CLI, a fake worker, a timer, or a polling
service. The parent conversation must use its actual native delegation tool,
retain the handle returned by that tool, collect its actual completion, and
attest stopped status before a bridge settlement. A saved handle, a timeout, or
an output file alone is not evidence that a native worker has stopped.

The initial navigator/Improve actions are deliberately synthetic only to place
this disposable fixture at the current v3 `implement` action. Their record is
`evidence/synthetic-prerequisites.json`. They make no claim that a live full
ShipLoop run or Improve cycle occurred. Every chain operation below uses the
selected ShipLoop public CLI (`shiploop chain ...`).

## Prepare a new pilot

Choose a fresh absolute directory outside this checkout. Do not reuse an old
pilot directory: the harness refuses to overwrite it and does not clean up
unfinished worktrees or receipts.

```sh
SOURCE_ROOT=/Users/dadleet/src/.work-trees/skill-craft/shiploop-dispatcher-20260918
PILOT_DIR=/private/tmp/shiploop-native-chain-pilot-$(uuidgen | tr '[:upper:]' '[:lower:]')
PILOT="$SOURCE_ROOT/test/experiments/shiploop_chain/native_pilot.py"
DISPATCHER_SKILL="$SOURCE_ROOT/test/fixtures/plan-dispatcher-v1/SKILL.md"
ASK_AGENT_SKILL="$SOURCE_ROOT/skills/ask-agent/SKILL.md"

python3 -B "$PILOT" prepare \
  --pilot-dir "$PILOT_DIR" \
  --source-root "$SOURCE_ROOT" \
  --dispatcher-skill "$DISPATCHER_SKILL" \
  --ask-agent-skill "$ASK_AGENT_SKILL" \
  --capacity 2
```

The printed JSON records the exact absolute paths selected for ShipLoop, Plan
Dispatcher, and Ask-Agent; the initiating feature worktree; the external
worker-worktree parent; the action ID; and the first ready nodes. The generated
`context.json` freezes those locators for the manual run. The bridge itself
also freezes its graph/package inputs and blocks later mutation if they drift.

The fixture code is intentionally tiny:

| Node | Worker-owned path | Required behavior |
| --- | --- | --- |
| `A` | `toy/add.py` | `add(2, 3) == 5` and `add(-4, 1) == -3` |
| `B` | `toy/format.py` | trim, lowercase, and collapse whitespace |
| `J` | integration-only merge of both paths | merge exact accepted A/B commits and prove `normalize('Result ' + str(add(2, 3))) == 'result 5'` |

The oracle is generated under `$PILOT_DIR/oracle/verify.py`, outside all worker
worktrees, marked read-only, and SHA-256 recorded in `context.json`. It checks
the clean worker HEAD, required behavior, exact changed paths, and, for `J`,
ancestry of both accepted supplier commits.

## Claim and start ready work

`A` and `B` are eligible independently. The `claim` command uses the real
public bridge `claim` operation. Copy each returned attempt ID exactly into its
matching `start` command.

```sh
python3 -B "$PILOT" claim --pilot-dir "$PILOT_DIR" --steps A B

python3 -B "$PILOT" start --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>'
python3 -B "$PILOT" start --pilot-dir "$PILOT_DIR" --step B --attempt '<B_ATTEMPT>'
```

Each `start` calls the public bridge `start`, writes its returned exact packet
under `$PILOT_DIR/packets/`, and prints its worker workspace, packet path,
result-artifact template, native dispatch brief, and real `report_argv` array.
Only a fresh response with `"action": "launch"` permits the parent to dispatch
a native worker. The harness does not interpret that grant as a launch.

Give the native collaboration agent the printed `*-native-dispatch.md` and
packet. It must work only in the packet's sibling worktree, commit the result,
write the packet-assigned result artifact/envelope, execute its exact
`report_argv`, and return normally through the native host. The result JSON must
include the exact clean worker `commit`, `workspace`, actual `checks`, and a
Git/handoff summary. Copy and fill the generated template so `step` and `attempt`
remain explicit; do not recreate its identity fields from memory. Prose may vary,
but missing or contradictory identity fields fail verification. The parent
retains its own pending-job record and continues
any independent work while native workers run.

## Record the actual native handle

After the native host confirms launch, write the real handle it returned to a
small JSON file. The harness accepts the raw JSON value, or an object with only
`handle`. It does not generate a handle and cannot validate host liveness.

```sh
# Replace this content with the handle returned by the actual native delegation tool.
printf '%s\n' '{"handle":{"native_handle":"REAL_HANDLE_FROM_HOST"}}' > "$PILOT_DIR/A-handle.json"

python3 -B "$PILOT" launched \
  --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' \
  --handle-file "$PILOT_DIR/A-handle.json"
```

Repeat that after `B` launches. `launched` invokes the public bridge operation
and saves the caller-provided handle under `$PILOT_DIR/handles/`; it never
claims the worker has finished.

## Collect, verify, and settle each real worker result

After native collection confirms the worker returned, run `verify`. It invokes
the real public `observe` operation, which requires that the worker actually
published its receipt through the exact `report_argv`. It then checks the
packet-assigned result artifact/envelope, exact clean worktree and HEAD, only
the assigned files, and the external immutable behavior oracle.

```sh
python3 -B "$PILOT" verify --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>'
python3 -B "$PILOT" settle --pilot-dir "$PILOT_DIR" --step A --attempt '<A_ATTEMPT>' --confirmed-stopped

python3 -B "$PILOT" verify --pilot-dir "$PILOT_DIR" --step B --attempt '<B_ATTEMPT>'
python3 -B "$PILOT" settle --pilot-dir "$PILOT_DIR" --step B --attempt '<B_ATTEMPT>' --confirmed-stopped
```

`--confirmed-stopped` is an explicit caller attestation after the host has
confirmed termination. It is not inferred from the receipt, the handle, elapsed
time, or a file. `settle` calls the public bridge operation and retains the
accepted exact commit under `$PILOT_DIR/accepted/`. It should make `J` ready.

## Join, inspect state, and return

```sh
python3 -B "$PILOT" show --pilot-dir "$PILOT_DIR"
python3 -B "$PILOT" claim --pilot-dir "$PILOT_DIR" --steps J
python3 -B "$PILOT" start --pilot-dir "$PILOT_DIR" --step J --attempt '<J_ATTEMPT>'
```

Dispatch `J` natively only after its `start` response says `action=launch` and
record its actual native handle as above. Its packet has
`shiploop_chain.integration: true` and the exact accepted A/B commits in
`shiploop_chain.required_commits`. `J` merges those commits in its own assigned
worktree; it does not update the initiating feature branch.

After collection and stopped-worker confirmation:

```sh
python3 -B "$PILOT" verify --pilot-dir "$PILOT_DIR" --step J --attempt '<J_ATTEMPT>'
python3 -B "$PILOT" settle --pilot-dir "$PILOT_DIR" --step J --attempt '<J_ATTEMPT>' --confirmed-stopped
python3 -B "$PILOT" finish --pilot-dir "$PILOT_DIR"
python3 -B "$PILOT" show --pilot-dir "$PILOT_DIR"
```

`finish` invokes the real public bridge `finish` operation. Before it does so,
the harness reruns the external `J` oracle, proves that the initiating feature
worktree still equals the recorded baseline, and retains `finish.json` evidence.
After the bridge fast-forward it proves that only the initiating feature points
at `J` while the fixture's `main` worktree remains at its original commit.

## Retained evidence and limits

The pilot directory is intentionally retained. `context.json`, `graph.json`,
the immutable oracle, `run/`, `packets/`, `handles/`, `verification/`,
`accepted/`, `commands/`, and append-only `events.jsonl` distinguish actual
commands/results from the synthetic prerequisite setup. The public bridge keeps
its own immutable Markdown event ledger under `run/chains/<action>/events/`.

This pilot qualifies a bounded local path only. It does not establish native
agent behavior from a synthetic harness, cross-session native handle recovery,
power-loss durability, remote publication, deployment, or a full live ShipLoop
execution. Preserve a failed or incomplete pilot for recovery instead of
deleting or recreating its worktrees.
