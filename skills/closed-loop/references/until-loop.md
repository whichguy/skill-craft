# The Until Loop contract

`loop contract --campaign C [--out FILE]` emits the JSON that the Until Loop runtime's `start` reads on stdin. The runtime is
`improve`'s vendored copy (0.10.1; its `PROVENANCE.json` and `test/until-loop-vendor.test.py` validate it). There is one contract
kind: the scope contract. Readiness is a gate you run with `loop readiness`, not a contract, because exit checks only read recorded
evidence and an effectful probe is not a read.

## What the contract holds

| Field | Value |
| --- | --- |
| `workspace` | **the campaign folder**, a small Git repo that holds only campaign state: every recorded fact a check reads lives there, so the runtime's content fingerprint sees every change to it |
| `work` | one closed-loop iteration at the current scope, then the checkpoint |
| `exit_condition` | the scope is converged: the seven clause sentences, and "report satisfied only after every frozen check passed after the iteration's last change" |
| `repeat_condition` | another iteration while `step` reports start, poll, task or widen; stop incomplete on a stop, a block, the budget, or an owner decision |
| `required_trivial_reviews` | **0** |
| `exit_checks` | C1 to C7: `{id, clause, command}` where the command is `closed_loop.py check --campaign C --clause Cn --expect-sha <script hash> --expect-scope <scope> --expect-identity <campaign identity>` |
| `context` | `request`, `scope`, `authority`, `environment`, `resources [{purpose, locator}]`, all nonblank text and absolute locators |

## Mechanics (checked in `scripts/until_loop_ephemeral.py` and its adapter doc)

- **The runtime never runs the checks.** Each active packet carries a `verify_script`. You run it exactly as printed with your own
  shell; it runs every check with stdin closed and pipes the results into `record`, which stores each exit code with the action
  number and the **workspace's Git tree**.
- **`done` refuses a satisfied report** without a recorded run for the current action, or after the tree changed since that run. A
  failing check never lets the runtime complete. Because the workspace is the campaign folder, a change made after the verify run by
  any campaign verb that writes state (`step`, `task`, `unknown`, `approve`, `reopen`, `cleanup`, `cancel`, `report`) is refused
  too: run the verify script again after the last change. Run `report` after the contract completes, not before.
- **What the fingerprint does not see.** The runtime watches the campaign folder and nothing else. A change between the verify
  run and the report to the *subject*, to the *adapter and its pinned files* (the checks refuse a changed boundary the next time they
  run), or to this *script* (its hash is in every check) is outside it, and so is a second writer to the campaign that lands between
  the last check and the runtime's fingerprint. The checks catch the first three the next time they run; nothing catches the last.
  So run the verify script immediately before you report, make no other call in between, and let one session act on a campaign.
- **The fingerprint must be able to see the folder.** It is `git add -A` into a private index, so a Git ignore rule hides a file from
  it, and a Git error makes it unavailable, after which the runtime treats a changed folder as unchanged. `init` therefore writes a
  `.gitignore` of `!*` (a rule in the folder outranks `.git/info/exclude` and the user's global excludes), and every check and
  `contract` first runs `git check-ignore` on the state files and `git add -A -n`: an ignore rule or a Git failure makes the check
  exit 2 and the contract refuse, so the runtime records a failed check instead of a pass on a blind fingerprint.
- **A failed frozen check sets the native streak to zero.** That is why the contract sets `required_trivial_reviews` to 0 and the
  quiet window (K) lives in the script: with a native gate of 2 plus a script window of 2, a failure on pass 1 would reset the native
  count and convergence would take three passes instead of two. The runtime's first-pass shortcut exists only for a gate of 2 or more,
  so it is off.
- **Frozen means command text**, with up to two repairs per check for a command that misstates its clause. It does not pin the
  implementation, so the command carries `--expect-sha`: a changed script exits 3 and fails its own check. A forged `record` is outside
  the protocol's trust boundary; it is a visible command that hooks can see.
- **One contract per scope.** The contract is immutable and its checks carry the scope. A widened scope is a new contract: when the old
  one completes, emit and start another with a new receipt file; an old contract's checks exit 3 at the new scope.
- **Mode: isolated, with a durable `--directory` and a `--receipt`, both in `<campaign>.work`.** A receipt records every packet but
  cannot recreate missing active state, and the default state parent is a temporary directory, so give `--directory` a resolved
  absolute path. Keep the runtime's state, the contract file and the receipts **outside the campaign folder**: recovery rewrites the
  receipt, which would otherwise change the very tree the verify run is bound to. Ordinary host-session mode (nesting, hook recovery)
  needs a stable session identity and plugin hooks and is not used here.

## Reporting

`done_argv` takes one JSON report on stdin with `classification` (`trivial` only for a quiet iteration, `non-trivial`, `unresolved`),
`exit_assessment` (`satisfied` only when the certificate is converged and every check line printed `exit=0`), `continuation_assessment`
(`allowed`, `blocked`, `cancelled`), `evidence` (what you observed) and `handoff` (a full replacement summary: objective, what is done
and unresolved, receipt and campaign locators). The handoff carries facts, never authority.

## Recovery

After a lost context, read the receipt file: an active packet gives `next_argv` (read-only; run it once), a terminal one is the result.
Never replay an old `done`. Then run `loop status` for the campaign's own state, which is complete without the runtime.
