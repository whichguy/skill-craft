---
bump: patch
---
The last consumer-contract 4c removals, after the renderer swap. The first removals shipped in 1.0.0; these six were
kept for the swap.
- **References block.** It no longer defines a `FEATURE` symbol or lists the old feature folder and the
  `features/README.md` list. It lists the three living files under `HOME`.
- **Step-plan product.** "Results this stage builds on" no longer points at a `FEATURE/plan.md` section. The step-plan
  result is still listed.
- **Knowledge lines.** The plan packet no longer prints the `Spec: docs/shiploop/spec.md @ <sha>` first-line pin, and
  early stages no longer print the "Earlier features" clause. The home line says "spec, environment and architecture".
- **Loop contracts.** The `{feature}` token and its fill are gone. Four Work texts were reworded:
  - step-plan drafts its result only;
  - test-spec writes `test_cases` rows in the result;
  - test covers every test case the packet quotes;
  - carry-forward keeps suites in `environment.md ## Harnesses and suites` and real-boundary checks in
    `architecture.md ## Real-boundary checks`, records open items in `assumptions`, and explains removals in its
    summary.
- **Engine.** `knowledge_home` drops `feature_dir`, `FEATURE_LIST`, `_GROUNDING`, `GROUNDING_LABELS`, `grounding`,
  `earlier_features` and `spec_pin`.
