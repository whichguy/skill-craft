---
bump: patch
---

Polish live planning observability from `codex/gpt-6.2-sol/medium` empirical runs:

- Fall back to `decision.md` (`Q<n>` reference and optional `Plan changed: yes/no`) when a planning experiment sandbox has no `meta.json`, so `intake` experiment questions flip from `pending` to `probing` in live views as soon as findings are recorded.
- Render proposed vertical slices and rolling-wave deferred concerns inside `_planning_panel` while `Plan Improve` is pending (`plan_accepted=False`), and expose active `plan` sandbox and experiment-question counts in `inflight_activity`, single-run progress chips, and Multi-Run Hub cards.
