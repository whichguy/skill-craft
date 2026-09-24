# Navigator graph dry runs

The graph driver exercises the actual navigator (protocol 4) and its full
returned packets. Synthetic
declarations stand in for project work; the driver runs no LLM, Git operation,
implementation, test command, or delivery action.

Bind `CLI` from the selected loaded ShipLoop card before running these commands:
`SKILL_ROOT` is the absolute directory containing that card's `SKILL.md`, and
`CLI="$SKILL_ROOT/scripts/shiploop"`. Do not derive it from the caller cwd or a
checkout-relative `skills/shiploop` path. The parent card explains how to obtain
the selected host path; use the resulting absolute `CLI` quoted in each call.

```sh
python3 "$CLI" graph-dry-run
python3 "$CLI" graph-dry-run --list
python3 "$CLI" graph-dry-run --scenario two-work-items --format markdown
python3 "$CLI" graph-dry-run --scenario blocked-resume --format json
python3 "$CLI" graph-dry-run --scenario delivery --delegation ask-agent --format markdown
```

`--delegation inline|ask-agent` selects the simulated run's
[delegation](navigator.md#run-it). It defaults to `inline`, as for a new run;
`ask-agent` renders the opt-in delegated packets.

`--list` prints the scenarios: delivery, two
work items, blocked/resume, a repeat returned through Improve, pause/resume and
halt. The planning stages and the last carry-forward are followed by a synthetic
Improve completion; other producers advance directly. An unknown scenario
name is an input error (exit 2) that lists the available names. Expectations are authored independently of the routing tables. Each trace
contains the effective packet before its synthetic declaration and the resulting
stage, status, owner, and completed-instance IDs. The packet contains the current
action's callback. No entire prompt snapshot is a pass condition.

The two-work-item trace must distinguish W1 from W2: W1 owns its
`carry-forward` callback, then the returned packet is owned by W2 at
`select-work`. The synthetic carry-forward result records W1 as done and causes
W2's execution record to be created in the same simulated transition. In a
persisted run, `next` reports W2's pending effective action; it does not advance
W2 or expose an actionable root `inner-loop` container. Future work items have
no execution record until entered.

The repeated-Improve scenario replaces only the active item's action. It does
not simulate, count, or render the child's internal review cycles: the bound
Improve child owns those under the normal parent binding.

Custom JSON has only `steps` (any other top-level field is refused), each with an effective `at`, `expect`, optional
`status` (default `active`), and either a generic `result` or
`command: pause|resume|halt`. Each planning producer and the last carry-forward
(`command: produce`, optional `result`) is paired with `command: finish-improve`
carrying a synthetic `receipt` and optional `final_result`. The last completion
expects stage/status `done`. Run it with `--script PATH`. The packaged
`graph-dry-run-scenario.json` is an example prefix:

```sh
python3 "$CLI" graph-dry-run \
  --script "$SKILL_ROOT/references/graph-dry-run-scenario.json" --format json
```

Exit 0 means expectations matched, including an intentionally halted or partial
scenario. Exit 1 means an expectation failed; exit 2 means the input could not
be read or named an unknown scenario. Simulation
success never establishes project completion. See the
[navigator guide](navigator.md) for actual execution and Improve ownership.

## Scope

These tools make graph and prompt changes cheap to inspect. They do not bypass
production evidence gates, create a host installation, start a standalone
Improve/Until Loop runtime, or regenerate packages. Synthetic receipts stay in
memory and are never exported as a child receipt or accepted completion record.
