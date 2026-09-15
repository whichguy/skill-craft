# Navigator experiments

These opt-in experiments separate graph mechanics, cold prompt interpretation,
and real agent work. They add no runtime gate or new dependency. Results from
September 14, 2026 are summarized in
[the experiment report](../../../docs/shiploop-navigator-experiments-2026-09-14.md).

These historical fixtures remain pinned to navigator protocol 1. The new
`inner_state` trial covers protocol 2.

## Run mechanical coverage

From the repository root:

```sh
python3 -B test/experiments/shiploop_navigator/mechanical.py \
  --seed 20260914 --walks 100 --race-count 5 --timeout-seconds 60 \
  --output /tmp/navigator-mechanical.json
```

The script uses temporary non-Git projects, an independently declared expected
graph, and fresh CLI processes. It checks generated legal/illegal sequences,
cold callbacks, idempotent replay and concurrent duplicate/conflicting results.
The bounded run samples behavior; it is not exhaustive or evidence of delivery.

## Prepare live-agent trials

```sh
python3 -B test/experiments/shiploop_navigator/prepare.py --explicit-boundary
```

The JSON output names six cold-interpretation packets, an isolated Improve
fixture and its current packet, and a matched single-pass control fixture/task.
Packets come from the real CLI `next` command. Earlier graph transitions are
explicitly synthetic setup, not claims that planning or implementation occurred.
The script creates local fixture Git history and does not run an LLM or publish.

Give only the named packet/task and its allowed fixture scope to a fresh agent.
For interpretation cases, prohibit work execution and ask for stage/action,
next actions, required reads, completion conditions, proposed result and limits.
For the Improve trial, execute only its one current action and stop after the
callback returns the next stage. The control performs one engineering pass,
with normal test/debug cycles but no extra clean-review campaign.

Keep the oracle and other trial outputs out of the worker's inputs. Grade each
completed fixture afterward:

```sh
python3 -B test/experiments/shiploop_navigator/oracle.py \
  --fixture /absolute/path/from/manifest/improve-fixture \
  --output /tmp/navigator-improve-grade.json
```

The oracle uses ten explicit cases and 200 seeded grid-union cases. Its expected
boundary interpretation matches `--explicit-boundary`. Omitting that flag
reproduces the original ambiguous specification: adjacency-related mismatches
then indicate a task/oracle ambiguity, not established implementation defects.
Use `--extended` to include six tuple/float/boolean checks added after independent
review. Report those separately from the original 210-case comparison.

Review the actual candidate, test results, preserved specification, Git history,
review notes and navigator state. Two review claims alone do not prove correctness.
Use [preregistration.md](preregistration.md) for the criteria and recorded
amendments. Raw run files live in temporary directories; curated observations
and candidate snapshots are kept under `evidence/`. Paths in archived observations
are normalized for portability and are not executable callbacks.
