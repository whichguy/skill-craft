# Fresh-context local-skill trial

Work only in `/Users/dadleet/tmp/shiploop-local-skills-20260918/b04/fixture`. Triage the incident bundle and assess whether existing local skill work fits or needs a compatible separate path.

Read `README.md`, `SHIPLOOP.md`, `docs/lessons.md`, the applicable contract, and
`data/bundle.json`. Read the frozen, actually rendered v3 `skill-assess` packet at
`/Users/dadleet/tmp/shiploop-local-skills-20260918/b04/packets/skill-assess.md` for its current stage guidance. Its transition history is synthetic
packet setup: do not run any callback, do not claim Improve ran, and do not use its
paths as a live run.

Perform bounded local work and local validation only. Write `output/decision.json`
exactly as the applicable contract specifies. Assess reuse before building. If a
repository-local prompt skill is warranted, keep it under `skills/<slug>/SKILL.md`
and index it in `README.md`; it must refer to the authoritative contract instead of
copying contract-specific defaults. Do not install or create global skills, add
dependencies, publish, commit, push, deploy, or create a replacement ShipLoop run.

Also locally verify v1 remains usable: apply `docs/release-contract.md` to `data/v1-compatibility-bundle.json` and write the exact v1-schema result to `output/v1-compatibility-decision.json`.
