---
bump: minor
---

ShipLoop runs unattended by default. An open decision takes a recorded default
(an assumption with its alternatives) and the run continues; a step only a
person can do becomes an open item while every independent stage continues.
The run prompts the user (`blocked` + `awaiting`) only when nothing further can
proceed without them, and a new `awaiting` must carry `no_default`, the reason
no default would do; ShipLoop refuses one without it. Saved runs that are
already waiting load and resume as before. Stage duties, the release-plan and
release-verify guidance, SKILL.md and the delivery references say so, and the
release-verify example is platform-neutral.
