# Fresh-context local-skill trial

Work only in `/Users/dadleet/tmp/shiploop-local-skills-20260918/a02/fixture`. Triage the new bundle from cold context and assess whether the durable local skill already fits.

Read `README.md`, `SHIPLOOP.md`, `docs/lessons.md`, the applicable contract, and
`data/bundle.json`. Read the frozen, actually rendered v3 `skill-assess` packet at
`/Users/dadleet/tmp/shiploop-local-skills-20260918/a02/packets/skill-assess.md` for its current stage guidance. Its transition history is synthetic
packet setup: do not run any callback, do not claim Improve ran, and do not use its
paths as a live run.

Perform bounded local work and local validation only. Write `output/decision.json`
exactly as the applicable contract specifies. Assess reuse before building. If a
repository-local prompt skill is warranted, keep it under `skills/<slug>/SKILL.md`
and index it in `README.md`; it must refer to the authoritative contract instead of
copying contract-specific defaults. Do not install or create global skills, add
dependencies, publish, commit, push, deploy, or create a replacement ShipLoop run.
