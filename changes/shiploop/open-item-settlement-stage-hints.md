---
bump: patch
---
- Tailor open-item settlement hints in packets to each stage's actual result fields (`unverified` at `product-acceptance`, `criteria` at `step-plan`, `summary` at other non-`assumptions` stages, preserving `follow_on` at `handoff` and `assumptions` at `assumptions.STAGES`).
