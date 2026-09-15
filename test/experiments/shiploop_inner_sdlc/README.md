# Inner-SDLC synthetic pilots

These opt-in, stdlib-only fixtures validate whether a fresh agent can carry out
one current ShipLoop action on an isolated local repository. They do not run a
worker, change production, or estimate model reliability. They are capability
validation, not a matched-prompt causal comparison.

These historical fixtures remain pinned to navigator protocol 1. The new
`inner_state` trial covers protocol 2.

From the source checkout root, prepare a fresh trial directory:

```sh
python3 -B test/experiments/shiploop_inner_sdlc/prepare.py \
  --output /tmp/shiploop-inner-sdlc
```

The manifest contains each packet, fixture, run directory, source base, active
action, and seed baseline. Give a worker only that case's `packet` and
`fixture`; do not provide `manifest.json`, `oracle.py`, `preregistration.md`,
or anything under `calibration/`. The packet authorizes fixture edits and its
current callback only. It prohibits edits to the source checkout and asks the
worker to stop after one successful callback.

After a worker finishes, retain the prep-time `calibration/calibration.json`
as the original before/reference scores and grade the resulting fixture:

```sh
python3 -B test/experiments/shiploop_inner_sdlc/oracle.py \
  --case misleading-green \
  --fixture /tmp/shiploop-inner-sdlc/fixtures/misleading-green \
  --output /tmp/shiploop-inner-sdlc/grades/misleading-green-after.json
```

The fixed-outcome oracle is independent of worker prose. Its auxiliary file
observations help a reviewer locate a changed regression/evidence record; they
do not replace the semantic review in `preregistration.md`. Seeded candidates
must fail and external calibration references must pass before any pilot runs.

## Cold interpretation previews

From the source checkout root, use the existing public-CLI packet helper to
prepare fresh synthetic state. Earlier transitions represent navigation only.

```sh
python3 -B - <<'PYTHON'
from pathlib import Path
import json, sys, tempfile
root = Path.cwd()
sys.path.insert(0, str(root / "test/experiments/shiploop_navigator"))
import prepare
out = Path(tempfile.mkdtemp(prefix="shiploop-inner-preview-")).resolve()
cases = json.loads((root / "test/experiments/shiploop_inner_sdlc/cold-cases.json").read_text())
manifest = [prepare.write_case(out, row["id"], row["goal"], row["stage"]) for row in cases]
print(json.dumps(manifest, indent=2))
PYTHON
```

Give a fresh agent only its selected packet, not the criteria or prior responses.
Request literal `current_node` and `action_id`, intended decisions, evidence
needed, completion eligibility and limits. Require interpretation only: no
implementation, state mutation or callbacks. Grade equivalent sound decisions
against the fixed criteria afterward, and retain disagreements and failed
interpretations before revising prompts. Do not present these previews as
execution evidence or a controlled A/B result.

## Recorded trial

[Results report](../../../docs/shiploop-inner-sdlc-results-2026-09-14.md) describes
the implementation, observed failures and bounded conclusions.
[Cold evidence](evidence/cold/grading.md) preserves five packet previews and their
raw responses. [Live evidence](evidence/live/README.md) preserves actual final
fixtures, reserved outcomes, run receipts, notes and post-run unit checks.
