# Self-test matrix — package-scope RESULT pins

Normative cases the harness self-tests (and operators) must hold:

| Case | Expect |
|---|---|
| Root clean suite | `PASS_CLEAN` |
| Nested package + root dirt, package clean | `PASS_CLEAN_SCOPED` |
| Nested package suite writes product file | `FAIL_SIDE_EFFECTS` |
| fix-loop on clean suite (`--mode fix-loop --max-rounds 1`) | `PASS_*`, worktree removed when clean |
| No `--cmd`, no config, no recognised layout | exit 2, `no_deterministic_candidate` |
| `.test-harness.yml` with a `cmd` beside a Makefile | the config wins (`source=config`) |

Pinned in `scripts/test-harness-tests.sh` (package scope, fix-loop smoke, discovery).

RESULT is **suite hygiene only** (exit + FS/control side effects). Live evals,
model-graded checks, improvement loops and test generation are **not** RESULT.
