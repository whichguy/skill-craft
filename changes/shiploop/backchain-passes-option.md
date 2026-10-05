---
bump: minor
---
New run option `--backchain-passes one|converge|none` at `init` and `workspace start`, recorded as `backchain_passes` in `state.md` like `--lint` (default `one`). It sets how many passes the Backchain planning child may take: one review/fix/check cycle, two consecutive trivial reviews, or no whole loop at `plan`. A retry of `init` or `workspace start` cannot change it and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. Improve's review loops are not covered by the option.
