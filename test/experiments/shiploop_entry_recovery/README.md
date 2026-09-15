# ShipLoop entry and recovery trial

This opt-in fixture tests a linked, fresh-context execution segment with an
intentional interruption. It does not launch an LLM or change production state.
Read [preregistration.md](preregistration.md) before conducting or grading it.

From the source checkout:

```sh
python3 -B test/experiments/shiploop_entry_recovery/prepare.py --output /tmp/new-entry-trial
```

The output directory must be new. Preparation checks the bad seed and a separate
reference with the fixed oracle, then traverses the actual CLI using explicitly
synthetic prelude declarations. Give each fresh worker only `handoff.md` and the
specified one-action stop rule. For the first worker, explicitly stop before its
completion callback to simulate an interruption. Preserve the interrupted state
before starting the second worker. The next three fresh workers each recover
from the locator, perform one current action, submit its real callback, and stop.
They are successive owners of the isolated run; they are not workers authorized
to advance any parent delivery run. Do not provide calibration or oracle files.

Afterward, independently grade and run the worker-authored tests:

```sh
python3 -B test/experiments/shiploop_entry_recovery/oracle.py /tmp/new-entry-trial/fixture/lines.py
cd /tmp/new-entry-trial/fixture
python3 -B -m unittest discover -v
```

Also run those same tests against the preserved seed in a separate scratch
folder: they must reject its known defect. Preserve factual responses, packets,
initial/interrupted/final state, accepted results and source/test snapshots.
The final expected cursor is `document`, not whole-run completion.

[Recorded results](../../../docs/shiploop-entry-recovery-results-2026-09-15.md)
separate this bounded trial from hermetic tests and the real implementation run.
