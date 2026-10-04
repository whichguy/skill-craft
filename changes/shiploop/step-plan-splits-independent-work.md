---
bump: patch
---
On an Ask-Agent run, step-plan now asks for each change that does not need another to be its own step with `deps: []`, joined by a later step that needs them. Before, a request that did not ask for parallel work got a linear plan (two independent modules in one step), so the default parallel chain had nothing to run at the same time. Inline runs are unchanged.
