# Native setup pilot

This test-only corpus contains two synthetic local cases: standard-library API regression coverage and a readiness preview with a service, an explicitly authorized local sandbox, an unavailable grant, and an offline formatter. It makes no real provider, service, account, credential, or org calls. Python 3.9 or newer is required; no packages are needed.

The API oracle runs outside the native case. Calibrate it and the readiness fixture with this no-model check:

    python3 -B test/native-setup-pilot.test.py

The wrapper runs the API oracle's correct, alternative, mutant, invalid-suite, and classification controls; the readiness state/authority calibration; adapter argument-forwarding tests; native CLI help/head checks; and four retained typed-boundary examples against both correct implementations. Calibration receipts are written to temporary directories outside the fixture.

## Retained calibration receipts

After defining PILOT_FIXTURES and choosing a fresh external PILOT_RUN_ROOT as below, invoke the calibrators directly to retain their receipts:

    python3 -B "$PILOT_FIXTURES/api-fixture/oracle/run_fixture.py" \
      --calibrate --output "$PILOT_RUN_ROOT/api-oracle-calibration.json"

    python3 -B "$PILOT_FIXTURES/readiness_calibration.py" \
      --fixture "$PILOT_FIXTURES/readiness-fixture" \
      --seed-state "$PILOT_FIXTURES/readiness-state" \
      --output "$PILOT_RUN_ROOT/readiness-calibration.json"

## Native case qualification

The default API seed was repaired after the original pilot exposed a conflict:
its implement criteria required future authored tests, while implement prohibits
test authoring and the later test stage owns it. The corrected seed gives the
no-op implementation only C0 (preserve the APIs and pass the existing baseline).
The requested R-1 through R-5 coverage, five named cases and final test file remain
mandatory at test-spec/test. One separate baseline run completed this corrected
slice with all five new tests and unchanged production/contract; both correct
implementations passed and all six planted faults were caught on repeat execution.
That is single-run diagnostic qualification, not a prompt comparison or proof of
general test-only workflow behavior. The five focused IDs share C0 metadata;
inspect their actual R-1 through R-5 coverage instead of treating that mapping as
proof. Review of that generated suite found missing invalid-type cases for proposal
record IDs, expected versions, idempotency keys and change objects; catching the
six planted faults did not establish complete contract coverage.

The original bytes are retained in cases-phase-conflict.json as a historical
reproducer. Use that catalog only when deliberately investigating the phase
conflict; do not use it as the default quality benchmark. It can cause implement
send-back and unresolved replanning. Its original four-sample A/B cohort remains
unqualified, including the run that produced no suite; the corrected diagnostic
does not replace or rescore that sample.

## Native runs

CodexHost.install_plugin expects --plugin-dir to name the skill-craft payload at <complete-build-root>/plugins/skill-craft; it finds marketplace catalogs two levels above that path. Keep the complete build-packages.py output intact, including those catalogs and plugins/skill-craft. Never copy or pass only the plugin payload without its build root. The commands below use the slice's --ref route to produce the full build. For A/B overlays, use --ref plus --overlay; if preparing an overlay manually, copy the whole build root, replace its nested plugins/skill-craft, and pass that nested plugin path to --plugin-dir.

The original pilot used b237a3e89147e18a9f8450e63afb0814eeafd9be as its frozen baseline. For a new experiment, choose and record the intended full commit in PILOT_EXPECTED_HEAD; the harness checkout must match that HEAD and be clean. The adapter refuses staged, tracked, or untracked changes before it imports the frozen slice. Keep retained runs outside the checkout and its Git-managed ancestors; the example uses /private/tmp so exported files cannot make a parent Git scan traverse a large unrelated repository. The adapter bounds Git discovery for the exported output under its temporary run root while preserving discovery in explicitly owned fixture repositories. Select and record the model and effort explicitly. The example uses Codex with gpt-6.1-terra at xhigh:

    PILOT_FIXTURES="$PWD/test/fixtures/native-setup-pilot"
    PILOT_FROZEN_CHECKOUT=/absolute/path/to/the/frozen/skill-craft-checkout
    PILOT_EXPECTED_HEAD=b237a3e89147e18a9f8450e63afb0814eeafd9be
    PILOT_RUN_ROOT=/private/tmp/shiploop-native-setup-pilot-runs/run-01
    test "$(git -C "$PILOT_FROZEN_CHECKOUT" rev-parse HEAD)" = "$PILOT_EXPECTED_HEAD"
    test -z "$(git -C "$PILOT_FROZEN_CHECKOUT" status --porcelain --untracked-files=all)"
    mkdir -p "$PILOT_RUN_ROOT"

    python3 -B "$PILOT_FIXTURES/native_slice.py" \
      --harness-root "$PILOT_FROZEN_CHECKOUT" \
      --expected-head "$PILOT_EXPECTED_HEAD" \
      --case-catalog "$PILOT_FIXTURES/cases.json" \
      --fixture-root "$PILOT_FIXTURES" \
      --ref "$PILOT_EXPECTED_HEAD" \
      --case api-regression --seed-at test-spec --stop-after test \
      --host codex --model gpt-6.1-terra --effort xhigh --delegation inline \
      --output "$PILOT_RUN_ROOT/api-regression"

    python3 -B "$PILOT_FIXTURES/native_slice.py" \
      --harness-root "$PILOT_FROZEN_CHECKOUT" \
      --expected-head "$PILOT_EXPECTED_HEAD" \
      --case-catalog "$PILOT_FIXTURES/cases.json" \
      --fixture-root "$PILOT_FIXTURES" \
      --ref "$PILOT_EXPECTED_HEAD" \
      --case readiness-plan --seed-at test-strategy --stop-after plan \
      --host codex --model gpt-6.1-terra --effort xhigh --delegation inline \
      --output "$PILOT_RUN_ROOT/readiness-plan"

Calibrate the oracle independently before scoring generated API tests. After a run, set PILOT_API_WORKTREE from its slice-result.json worktree field, then run:

    PILOT_API_WORKTREE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["worktree"])' "$PILOT_RUN_ROOT/api-regression/slice-result.json")"

    python3 -B "$PILOT_FIXTURES/api-fixture/oracle/run_fixture.py" \
      --tests "$PILOT_API_WORKTREE/test_acceptance.py" \
      --output "$PILOT_RUN_ROOT/api-regression-oracle.json"

The oracle receipt grades behavior against both correct implementations and the six named mutants; a native summary or successful test command alone is not an oracle result. The readiness case's grant remains outside authority and must remain unavailable. Preserve all native outputs, logs, and oracle receipts in the external run root.

## Evidence limits

The readiness calibration validates the local CLI fixture, not a model's plan.
A native slice PASS means its configured boundary and callback checks completed.
Evaluate accepted plans against the task, its authority and concrete evidence;
the retained corpus supplies no qualified automatic planning-quality score.
Earlier seeded stages are synthetic. These stage slices are not a full E2E
campaign and cannot by themselves qualify a prompt for promotion.

The retained experiment journal is [the November 7 native setup pilot](../../../docs/experiments/native-setup-pilot-20261107/README.md).

## Follow-up examples

The separate oracle suite-controls/typed_boundary_examples.py file retains four
executable cases found missing in the diagnostic generated suite: non-string
record IDs, non-integer versions, non-string idempotency keys, and non-dict
change objects. Each checks the typed error and unchanged record. The no-model
wrapper runs them against both correct implementations. These author-written
examples remain outside the subject, historical model outputs, and original
six-mutant score. Their inclusion does not repair or rescore the model's tests.
