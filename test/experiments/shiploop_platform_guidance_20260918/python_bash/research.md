# Bounded Python and Bash coding-guidance experiments

Status: fixture calibration completed on 2026-09-18. This is evidence for a future guidance-treatment study, not a ShipLoop policy change or a claim about coding-agent performance.

## Study binding and scope

The candidate Core requires independent expected outcomes and preservation of failure causes and required cleanup. [shiploop-coding-guidance-candidate-2026-09-18.md - Core: independent checks and failure/cleanup duty](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-candidate-2026-09-18.md:13)

The candidate State card requires a clear owner and validate-before-irreversible-effect behavior. [shiploop-coding-guidance-candidate-2026-09-18.md - State: authority and invariant duty](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-candidate-2026-09-18.md:57)

The companion plan requires a positive scenario, a control, explicit failure cases, a calibrated reference, and rejected plausible mutants; it expressly permits Python standard-library storage/state fixtures. [shiploop-coding-guidance-experiment-plan-2026-09-18.md - Shared fixture contract: references, mutants, controls, and stdlib scope](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-experiment-plan-2026-09-18.md:69)

This package calibrates exactly four small runtime hypotheses.

| ID | Hypothesis | Reference expectation | Mutants that must differ | Negative control |
| --- | --- | --- | --- | --- |
| P1 | A Python child-process wrapper should pass an argv list, preserve a checked child error, and remove its owned temporary directory. | CalledProcessError, exit 17, exact child stderr, workspace absent. | Swallowed nonzero status, cleanup exception masking the child cause, string shell command broken by a path containing spaces. | All non-string-command variants return child-ok on child success. |
| P2 | Python state belongs to an instance and an invalid transition must leave state unchanged. | A second instance is empty; rejected debit retains the prior snapshot; an 80-step fixed-seed trace has no negative balance or rollback failure. | Class-level shared balances; validate after mutation. | All variants return 7 for one ordinary credit. |
| B1 | Bash must quote its positional-argument vector when preserving argument boundaries. | A NUL-delimited capture exactly preserves whitespace, a glob, an empty argument, and a leading dash. | Unquoted positional expansion splits and expands. | Both variants preserve ordinary nonempty tokens. |
| B2 | Bash needs pipefail, an explicit conditional for an expected pipeline failure, and an EXIT cleanup trap. | Exit 42, handled-pipeline-status=42, workspace absent. | Last-command-only pipeline status; direct errexit without recovery report; missing cleanup trap. | The no-cleanup mutant preserves exit/output, so cleanup must be asserted separately. |

The test code contains the reference and mutants rather than treating prose as evidence. The Python test imports each fixture independently or invokes its driver in a fresh subprocess. The Bash test uses a fresh mktemp worktree and deletes the one intentional leak only after asserting that the leak was observed.

## External research

Primary documentation supports the language semantics used here.

- [Python subprocess.run documentation - check=True error contract](https://docs.python.org/3/library/subprocess.html#subprocess.run) describes the CalledProcessError behavior used by P1.
- [Python TemporaryDirectory documentation - context-managed cleanup](https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory) supports bounded test workspaces. This fixture uses mkdtemp plus a finally block specifically so the test can audit post-error deletion.
- [pytest tmp_path documentation - per-test temporary directory isolation](https://docs.pytest.org/en/stable/how-to/tmp_path.html) describes isolated per-test paths and retention behavior; it informed the isolation goal but the experiment deliberately runs with unittest only.
- [Hypothesis introduction - property-oriented test examples](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html) gives examples of properties such as transaction balance. It supports the shape of P2's invariant, not the choice to add Hypothesis to this fixture.
- [GNU Bash manual - pipeline exit statuses and pipefail](https://www.gnu.org/software/bash/manual/html_node/Pipelines.html) and [GNU Bash manual - errexit exceptions including if conditions](https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html) support B2's expected status handling.

I also inspected concrete GitHub source/examples supplied as relevant prior art. Their selection does not make their style automatically correct for this repository.

- [pytest test_tmpdir.py - tmp_path factory and retention test cases](https://github.com/pytest-dev/pytest/blob/main/testing/test_tmpdir.py) tests custom base-temp removal and per-test temporary path behavior.
- [Hypothesis tests README - separates fast coverage, expensive interaction, and quality tests](https://github.com/HypothesisWorks/hypothesis/blob/master/hypothesis/tests/README.md) is a concrete example of keeping expensive/property-oriented checks explicit.
- [Ruff B018 fixture - static lint fixture, not a runtime behavior oracle](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/resources/test/fixtures/flake8_bugbear/B018.py) confirmed that a linter fixture is useful supplementary evidence but cannot establish P1/P2 semantics.
- [ShellCheck SC2086 implementation - reports globbing and word splitting](https://github.com/koalaman/shellcheck/blob/master/src/ShellCheck/Analytics.hs) contains the quoted-expansion diagnostic exercised below.
- [bats-core README - Bash 3.2 support and errexit-backed assertions](https://github.com/bats-core/bats-core/blob/master/README.md) explains why a Bash-3.2-compatible plain runner is a valid bounded fallback.
- [Google Shell Style Guide - quoted array expansion for argument lists](https://github.com/google/styleguide/blob/gh-pages/shellguide.md) illustrates quoted array expansion and warns against a single string of command arguments or eval.
- [awesome-copilot shell instructions - set -euo pipefail, traps, and mktemp baseline](https://github.com/github/awesome-copilot/blob/main/instructions/shell.instructions.md#L25) is useful baseline advice. The conditional-function fixture qualifies, rather than rejects, that advice: a function used as an if condition can run false and then return success while all three options are enabled.

These URLs were read on 2026-09-18 from moving default branches. They are concrete examples, not pinned dependencies or popularity-based proof.

## Platform and tool inventory

The commands were run from this directory. No package, global tool, production file, secret, or network state was modified.

| Item | Observation |
| --- | --- |
| Python | Python 3.14.7 on macOS-26.6.2-arm64-arm-64bit-Mach-O |
| Bash | /bin/bash: GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25) |
| ShellCheck | /opt/homebrew/bin/shellcheck, 0.11.0 |
| pytest | /opt/homebrew/bin/pytest, 9.1.1 |
| Ruff | /opt/homebrew/bin/ruff, 0.15.22 |
| bats-core | bats was not found on PATH |
| Hypothesis | ModuleNotFoundError: No module named hypothesis |

The Bash suite deliberately runs /bin/bash, not an assumed newer Homebrew Bash. It uses only Bash 3.2-era syntax. The absent Bats and Hypothesis packages were not installed merely to make a test pass.

## Executed calibration and observations

    cd /Users/dadleet/src/skill-craft/test/experiments/shiploop_platform_guidance_20260918/python_bash
    python3 -B -m unittest -v test_python_guidance.py
    /bin/bash ./test_bash_guidance.sh
    python3 -B -m py_compile fixtures/python/*.py test_python_guidance.py
    /bin/bash -n fixtures/bash/*.sh test_bash_guidance.sh
    /opt/homebrew/bin/shellcheck -s bash fixtures/bash/argv_reference.sh fixtures/bash/failing_probe.sh fixtures/bash/pipeline_reference.sh fixtures/bash/conditional_function_errexit_exception.sh test_bash_guidance.sh

All commands above exited 0. The Python suite ran six tests. The Bash suite reported passes=27 failures=0; it separately checked each fixture and the test runner with /bin/bash -n. The explicit py_compile probe created bytecode caches despite the -B process flag, so those generated files were removed from this owned experiment directory before delivery; the reusable test commands are the unittest and Bash commands above.

The reference and static-analysis observations were deliberately asymmetric:

    /opt/homebrew/bin/shellcheck -s bash fixtures/bash/argv_unquoted_mutant.sh

returned 1 and SC2068: Double quote array expansions to avoid re-splitting elements. The reference scripts produced no ShellCheck diagnostic in the reference-only command. That static result is supplementary: runtime B2 still rejects no-pipefail and missing-cleanup mutants that a quoted-arguments rule does not establish.

The conditional-function counterexample ran under set -euo pipefail. Its command false did not terminate the function because the function was evaluated as an if condition; the following command ran, the function returned 0, and stdout was if-branch-success. This does not make set -euo pipefail bad guidance. It means an expected failure must be deliberately captured and asserted when control flow relies on it.

The direct state-driver output was:

    reference: basic_credit_result=7, second_instance_isolated=true, rejected_transition_preserved_state=true, trace_failures=[]
    shared-state mutant: basic_credit_result=7, second_instance_isolated=false, rejected_transition_preserved_state=true, trace_failures=[]
    partial-commit mutant: basic_credit_result=7, second_instance_isolated=true, rejected_transition_preserved_state=false, trace_failure_count=127; first failures: rejected transition changed state; negative balance survived

That result demonstrates why the ordinary-credit control alone is inadequate: all three implementations return 7, while only isolation and invariant assertions distinguish the two faults.

## Decisions

| Choice | Decision | Evidence and boundary |
| --- | --- | --- |
| Adopt | Keep this reference/mutant/negative-control calibration pattern as a fixture acceptance gate. | All four reference fixtures passed and every stated mutant differed under a named assertion. This is a study-fixture decision only. |
| Pilot | Add a compact Python/Bash conditional card only to a future controlled worker treatment. | The card should say to preserve checked subprocess causes through cleanup, assign mutable state an owner and test rejected transitions, quote argument vectors, use pipefail where pipeline failure matters, handle expected failures in an explicit conditional, and assert cleanup. It should also warn that set -euo pipefail does not remove conditional-function semantics. The experiments establish concrete language behavior; they do not yet compare guidance arms or agent outcomes. |
| Defer | Make Hypothesis or bats-core mandatory. | Both are absent here; standard-library unittest and a Bash-3.2 runner already calibrate the targeted behavior. A later pinned environment may add optional property/Bats variants. |
| Reject | Treat Ruff, ShellCheck, a green happy path, or a completion marker as enough evidence of the runtime contract. | ShellCheck catches the unquoted-argument mutant, while runtime checks catch distinct pipeline, recovery, cleanup, shared-state, partial-commit, and conditional-function behavior. Ruff source fixtures are static checks, not a replacement for behavior tests. |

## Evidence limits

These are deterministic local fixtures, not production services. They do not exercise threads, process cancellation, persistence/restart, hostile command injection, signal delivery, or another shell dialect. B2 validates GNU Bash 3.2 semantics on this macOS host and does not generalize to POSIX sh.

Most importantly, no coding agent was given the candidate guidance and asked to implement the references. The evidence validates the fixture/checker discrimination needed before such an arm begins; it does not show that the candidate improves quality, token use, speed, or recovery in ShipLoop.
