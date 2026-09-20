# Discovery handoff acceptance samples

See [RESULTS.md](RESULTS.md) for passed mechanics, mixed semantic outcomes and retained failures.

Read [SEMANTIC-PROTOCOL.md](SEMANTIC-PROTOCOL.md) before sampling. This is a
small synthetic acceptance exercise, not an A/B benchmark or a platform test.
The fixture preparer freezes an explicitly supplied ShipLoop package and renders
its actual discovery packets with synthetic predecessor transitions:

```sh
python3 -B test/experiments/shiploop_discovery_handoff/apparatus/prepare.py \
  --source "$PWD/skills/shiploop" \
  --output /absolute/new/external/discovery-sample
```

Give a fresh reader each case's `participant/LAUNCH.md`. The tool does not launch
models. Local source, tests and remote observations are synthetic; receipts log
every probe process, including rejected calls. Required output is the authored
discovery note, baseline evidence and updated project index. Verify all protected
input hashes afterward. Instructional context isolation and time/action bounds
are not a filesystem sandbox or watchdog.

The multi-system fixture explicitly distinguishes operator and runtime principal
permissions; an older study's flat permission response was ambiguous. The CLI
also rejects stale targets for dependent reads and exposes its receipt-log path.
These are apparatus corrections, not evidence that a platform behaves this way.

After discovery, a fresh planner starts with only the project index and a rendered
plan packet. It must find the note and observations through that index; missing
links are retained as failures without coordinator rescue. Both sampling stages
skip actual callback acceptance and Improve execution. Mechanism-level accepted
reference transport is covered separately by the ordinary planning-context tests.

Use `apparatus/prepare_cold.py --source /absolute/sample/source-snapshot/skills/shiploop
--case /absolute/sample/cases/multi --output /absolute/new/external/cold-sample`
in a fresh Python process, then give a fresh reader its `participant/LAUNCH.md`.
It reuses the completed project directory and records its input hashes before the
reader adds only `PLAN.md`; it does not copy or rescue missing note links.
