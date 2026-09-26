---
bump: minor
---
Lint now runs right after implementation and gates it. When `implement` is
submitted as done, ShipLoop lints every file the work item changed and applies
safe fixes on changed lines. It refuses the submission once after an auto-fix,
so the step reruns its checks. It also refuses while a new finding on a line
the item changed remains, unless the result lists it in the new `lint_waivers`
field (`[{"id", "reason"}]`) with the ID the refusal prints. Findings from
before the item, missing tools, tool errors and timeouts never block, and
`lint: off` turns the gate off. The implement packet prints the `lint` command
to run after each step.

Linters are now discovered per changed file type. Besides ruff and shellcheck,
ShipLoop runs the linters a repository configures (eslint, prettier, tsc, mypy,
black, markdownlint-cli2, yamllint, gofmt), actionlint whenever it is on PATH,
and `npm run lint` or `make lint` for changed files no other linter covers.
Repository-configured linters run repository code by design; pre-commit is
still never run, and nothing is ever installed. The lint time limit rises from
20 to 120 seconds (60 per tool). `shiploop lint --show --gate N` reads a gate
record.

`test-green`, `test-refine`, `regression` and `integration-verify` now carry the
same pass-or-stop loop as `implement`: fix the code and rerun until every check
passes, and stop only as `blocked` when a check is proven unachievable or still
fails after 3 genuine fix attempts. A red check never leaves these stages as
done. The navigator guide gains a whole-run map of the prelude, inner and outer
loops.
