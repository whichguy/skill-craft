---
bump: patch
---
- For Backchain JSON, the card and protocol now name the shipped exporter: the sibling Backchain skill's `scripts/backchain.py export --run DIR` (the plan a finished run converged on) or `export PLAN.json`. The old pointer named `scripts/export-execution-graph.js`, which no package ships, and told hosts not to resolve an exporter outside this package.
