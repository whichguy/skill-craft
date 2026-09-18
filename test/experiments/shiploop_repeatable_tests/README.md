# Repeatable test-authoring pilot

This opt-in experiment observes generated test assets, actual Improve review,
and independent reruns. It is a bounded guidance-component comparison, not an
end-to-end ShipLoop run, an installed-package A/B, or a cross-model reliability
claim. Live trials do not run in normal CI. Hermetic apparatus checks are
registered in the normal ShipLoop suite and never launch a model on import.

## Preregistered questions

1. Does the added repeatable-suite reference improve harness revalidation,
   executable discovery and full-suite registration over the prior test-case
   guidance?
2. Do authored tests distinguish stateless behavior from shared infrastructure
   and mutable data, and remain independent across repeat/order changes?
3. Does actual Improve preserve a meaningful expected RED without weakening
   assertions or changing production outside a test-authoring scope?
4. Can a fresh session use the retained instructions and preserve prior cases
   through a subsequent implementation change?
5. Can remote-resident tests be authored and run through an actually available
   remote interface, with revision/result/cleanup evidence and truthful blockers?

## Frozen local comparison

`prompts/baseline.md` contains the prior test-case reference plus identical
test-authoring scope instructions. `prompts/candidate.md` adds only the frozen
repeatable-suite reference. `prompts/provenance.json` records exact source and
hashes. This ablates one guidance component; other current ShipLoop prompt and
runtime changes are intentionally outside the comparison.

Use three fixtures: stateless behavior with stale runner notes, a synthetic
stateful catalog with a simulated expensive startup, and an expected-RED
missing behavior. Each arm receives its own identical initial repository,
the selected guidance, and the same natural request. Grade outcomes against
the public contract; do not require a particular generated filename or prose.
The initial existing tests are negative controls, not adequate references.

Begin with one pair for each fixture. Run up to three independent pairs for
the small fixtures when the first pair passes calibration and the candidate
has no unresolved critical failure. A critical failure stops promotion and
expansion into costly full workflows; preserve that trial, diagnose it, and
retain any repaired candidate as a separately identified trial. No silent
retry, replay-as-live, or post-hoc change of the passing criteria is permitted.

Use a fresh CLI process per trial, the verified configured model and effort pinned explicitly, fixed
1,200-second bound, same command configuration, and alternating arm launch
order. Disable memory and user config for these narrow sessions. Record
observable model identity if supplied by the event stream; otherwise leave it
unavailable. Instructions restrict work to the fixture and explicitly provided
skill resources. This is not a filesystem-read or network isolation proof.

Each arm invokes a frozen snapshot of the real installed Improve skill and its actual runtime after authoring, scoped to
its test assets and instructions. Record the pre/post asset identity and actual
adapter outcome. Keep expected RED distinct from an infrastructure error.
The evaluator sees arm-neutral output labels for semantic review; deterministic
checks do not need a model judge. Review transcripts for unfair grading and
unintended access to evaluator material before interpreting a score.

## Evidence and decision

`fixtures.py` prepares disposable inputs; `grade.py` independently executes
selection, repeatability and single-defect mutation checks on disposable copies.
`run.py` launches an actual opt-in model trial and retains prompt, invocation,
stdout/stderr, before/after hashes, terminal usage when available, and elapsed
time outside the product repository. Existing trial output is never overwritten.
Calibrate the grader against deliberately inadequate seeds and independently
written reference suites before interpreting live trials.

Critical outcomes are unchanged immutable production during test authoring,
meaningful assertions that reject seeded defects, registration reaching every
discovered retained case, cleanup/isolation, honest RED/blocked outcomes, and
observed actual Improve completion. Candidate adoption requires these outcomes
in the exercised cases and no loss relative to the baseline. Three fresh runs
are an initial screen, not a statistical reliability guarantee. Quality takes
precedence over tokens and time; output length is not total agent token usage.

Record mechanical, manual, blocked and unobserved outcomes separately. Report
failure and timeout attempts in the denominator. A cold-context feature trial
only establishes the exercised fixture's lineage; complete ShipLoop delivery
requires the separate one-shot E2E campaign. Remote execution requires its own
actual target results and is never credited from a local mock.

## Local commands

The retained first campaign exposed two preconditions for another comparison:
the SQLite public contract accepts integers larger than its reference can store,
and the workspace-write sandbox prevents Improve's default Git commits. Preserve
those original outcomes. Resolve and separately version the fixture contract or
reference, then give both arms the same explicit commit policy before another
live comparison. A passing seed calibration is only sensitivity to its named
defect, not proof that the reference satisfies the whole public contract.

The final grader reports mechanical observations and unresolved manual checks;
an unexpected failure must be investigated against the public contract before
attributing it to test quality. See `RESULTS.md` for actual outcomes and limits.

Run the apparatus checks without launching a model:

```sh
python3 test/shiploop-repeatable-experiments.test.py
```

An explicit model launch uses a previously prepared isolated repository and
an observer-owned prompt file outside that repository:

To prepare a fresh seed without a model call, run from this experiment directory:

```python
import json
from pathlib import Path
from tempfile import mkdtemp
from fixtures import prepare

study = Path(mkdtemp(prefix="repeatable-test-study-"))
record = prepare("price-format", study)
(study / "observer.json").write_text(json.dumps(record, indent=2) + "\n")
print(record["fixture"], record["job"])
```

`prepare` keeps calibration/reference code outside the worker repository. Before
a comparative launch, freeze the selected guidance and actual Improve runtime,
write the common job plus identical Improve/commit-policy instructions into the
external request, and bind their hashes in observer evidence. Do not launch the
known-invalid comparison contract unchanged; the campaign findings above apply.

```sh
python3 test/experiments/shiploop_repeatable_tests/run.py \
  --repo /absolute/disposable/repo \
  --output /absolute/separate/trial-output \
  --prompt /absolute/separate/request.txt \
  --model YOUR_VERIFIED_MODEL --effort YOUR_VERIFIED_EFFORT \
  --runtime /absolute/frozen/until-loop
```

Retain public fixtures, prompts, grader and sanitized campaign results here.
Keep raw CLI traces, authentication state, project identifiers and remote
service receipts in the private external study directory.
