---
bump: patch
---
The last consumer-contract 4c removals, after the renderer swap. The first removals shipped in 1.0.0; these six were
kept for the swap.
- **References block.** It no longer defines a `FEATURE` symbol or lists the old feature folder and the
  `features/README.md` list. Its "Knowledge files" line lists the three living files.
- **Knowledge lines.** The plan packet no longer prints the `Spec: docs/shiploop/spec.md @ <sha>` first-line pin, and
  early stages no longer print the "Earlier features" clause. The home line says "spec, environment and architecture".
- **Loop contracts.** The unused `{feature}` token fill is gone.
- **Engine.** `knowledge_home` drops `feature_dir`, `FEATURE_LIST`, `_GROUNDING`, `GROUNDING_LABELS`, `grounding`,
  `earlier_features` and `spec_pin`.
