# The Until Loop contract

`$LOOP contract --campaign C --kind scope|readiness [--out FILE]` emits the JSON that the Until Loop runtime's `start` reads on
stdin. The runtime is `improve`'s vendored copy (0.10.1; its `PROVENANCE.json` and `test/until-loop-vendor.test.py` validate it).

## What the contract holds

| Field | Value |
| --- | --- |
| `workspace` | the subject's working directory (a Git worktree: the runtime fingerprints its content) |
| `work` | one closed-loop iteration at the current scope, then the checkpoint |
| `exit_condition` | the scope is converged: the seven clause sentences, and "report satisfied only after every frozen check passed after the iteration's last change" |
| `repeat_condition` | another iteration while `step` reports start, poll, task or widen; stop incomplete on a stop, the budget, or an owner decision |
| `required_trivial_reviews` | **0** |
| `exit_checks` | C1 to C7 (or `R-START` for readiness): `{id, clause, command}` where the command is `closed_loop.py check --campaign C --clause Cn --expect-sha <script hash>` |
| `context` | `request`, `scope`, `authority`, `environment`, `resources [{purpose, locator}]`, all nonblank text and absolute locators |

## Mechanics (checked in `scripts/until_loop_ephemeral.py` and its adapter doc)

- **The runtime never runs the checks.** Each active packet carries a `verify_script`. You run it exactly as printed with your own
  shell; it runs every check in the workspace with stdin closed and pipes the results into `record`, which stores each exit code with
  the action number and the workspace's Git tree.
- **`done` refuses a satisfied report** without a recorded run for the current action, or after the tree changed since that run
  (re-run the verify script after the iteration's last change). A failing check never lets the runtime complete.
- **A failed frozen check sets the native streak to zero.** That is why the contract sets `required_trivial_reviews` to 0 and the
  quiet window (K) lives in the script: with a native gate of 2 plus a script window of 2, a failure on pass 1 would reset the native
  count and convergence would take three passes instead of two. The runtime's first-pass shortcut exists only for a gate of 2 or more,
  so it is off.
- **Frozen means command text**, with up to two repairs per check for a command that misstates its clause. It does not pin the
  implementation, so the command carries `--expect-sha`: a changed script exits 3 and fails its own check. A forged `record` is outside
  the protocol's trust boundary; it is a visible command that hooks can see.
- **One contract per scope.** The contract is immutable. A widened scope is a new contract: when the old one completes, emit and
  start another with a new receipt file.
- **Mode: isolated, with a durable `--directory` and a `--receipt`.** A receipt records every packet but cannot recreate missing
  active state, and the default state parent is a temporary directory, so give `--directory` a resolved absolute path inside the
  campaign folder. Ordinary host-session mode (nesting, hook recovery) needs a stable session identity and plugin hooks and is not
  used here.

## Reporting

`done_argv` takes one JSON report on stdin with `classification` (`trivial` only for a quiet iteration, `non-trivial`, `unresolved`),
`exit_assessment` (`satisfied` only when the certificate is converged and every check line printed `exit=0`), `continuation_assessment`
(`allowed`, `blocked`, `cancelled`), `evidence` (what you observed) and `handoff` (a full replacement summary: objective, what is done
and unresolved, receipt and campaign locators). The handoff carries facts, never authority.

## Recovery

After a lost context, read the receipt file: an active packet gives `next_argv` (read-only; run it once), a terminal one is the result.
Never replay an old `done`. Then run `$LOOP status` for the campaign's own state, which is complete without the runtime.
