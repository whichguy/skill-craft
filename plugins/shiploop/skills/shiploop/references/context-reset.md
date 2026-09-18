# Recovery from the retired model controller

ShipLoop is a skill plus scripts executed by the invoking conversation. Its
scripts select actions, validate callbacks, and persist the DAG state. They do
not start Grok, Claude, Codex, or other model sessions. The former `drive`
command and host adapters have been removed. An external E2E harness can start
Grok and then invoke ShipLoop inside that conversation.

## Existing runs

A historical `context-host.md` file identifies a controller from an older
version. Preserve it as evidence; it is not authority to start another model.
`state.md` remains the workflow's authority.

Before continuing such a run:

1. Inspect the recorded owner and establish that its process and delegated work
   have stopped. Do not take over a run while that owner can still write to it.
2. Reconcile any running or uncertain tool effects against the actual repository
   and durable evidence. A failed controller or command does not establish that
   an operation had no effect. Do not edit receipts to fabricate completion.
3. Recover the same run from the invoking conversation using its selected CLI:

   ```sh
   python3 "$CLI" next --run-dir "$RUN_DIR"
   ```

4. Follow that packet and its exact callback. Do not reinitialize the request or
   choose a successor from an old controller transcript.

If the prior owner or its effects cannot be settled, leave the run incomplete
and report the unresolved evidence. There is no automatic controller-restart or
ownership-transfer command.

## Host context changes

The invoking host owns its conversation and context management. Retain the
packet's absolute CLI, repository, run-directory, and recovery locators in that
host's durable handoff material. After a context change, read the same run with
`next`; do not copy stage/action/status values into a second source of truth.

`SHIPLOOP_CONTEXT_RESET` does not select a model or change ordinary ShipLoop
execution. Historical context-reset trials are measurements of the removed
controller, not instructions to recreate it inside the skill.
